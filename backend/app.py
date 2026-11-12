import hashlib
import json
import logging
import math
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.classifier import LABELS, ROOT, ModelUnavailable, SentimentClassifier
from backend.database import connect, initialize
from backend.imports import MAX_BYTES, MAX_TEXT, InvalidCSV, parse_csv

logger = logging.getLogger(__name__)
DEMO_PATH = ROOT / "data" / "examples" / "comentarios_demo.csv"
COMPARISON_PATH = ROOT / "reports" / "comparacao_modelos.json"


def create_app(db_path: Path | None = None, classifier=None, frontend_dir: Path | None = None):
    database = db_path or Path(os.environ.get("OPINARE_DB", ROOT / "var" / "opinare.sqlite3"))
    model = classifier if classifier is not None else SentimentClassifier()

    @asynccontextmanager
    async def lifespan(_app):
        initialize(database)
        yield

    app = FastAPI(title="Opinare", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    @app.middleware("http")
    async def local_origin_only(request: Request, call_next):
        # Local demo has no accounts; reject mutations initiated by arbitrary websites.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin not in {
                "http://127.0.0.1:8000",
                "http://localhost:8000",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            }:
                return JSONResponse(status_code=403, content={"detail": "Origem não autorizada."})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "model_ready": model.ready,
            "model_version": model.version,
            "active_model": getattr(model, "active", "indisponível"),
        }

    @app.get("/api/model")
    def model_info():
        try:
            comparison = json.loads(COMPARISON_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            comparison = None
        baseline = getattr(model, "baseline", None)
        return {
            "ready": model.ready,
            "version": model.version,
            "report": getattr(model, "report", None),
            "active_model": getattr(model, "active", "indisponível"),
            "active_name": getattr(model, "active_name", "Indisponível"),
            "fallback_reason": getattr(model, "fallback_reason", None),
            "baseline_version": baseline.version if baseline and baseline.ready else None,
            "comparison": comparison,
        }

    def analyze_text(text: str):
        if not model.ready:
            raise HTTPException(503, "O modelo não está disponível.")

        def result(classifier, active: str, name: str):
            try:
                scores = None
                if hasattr(classifier, "predict_proba"):
                    rows = classifier.predict_proba([text])
                    if (
                        len(rows) != 1
                        or set(rows[0]) != set(LABELS)
                        or any(not math.isfinite(rows[0][label]) for label in LABELS)
                    ):
                        raise ModelUnavailable("Pontuações inválidas do modelo.")
                    scores = rows[0]
                    label = max(LABELS, key=scores.get)
                else:
                    labels = classifier.predict([text])
                    if len(labels) != 1 or labels[0] not in LABELS:
                        raise ModelUnavailable("Resposta inválida do modelo.")
                    label = labels[0]
                return {
                    "model": active,
                    "name": name,
                    "version": classifier.version,
                    "label": label,
                    "scores": scores,
                }
            except Exception as exc:
                logger.exception("Falha na análise da frase")
                raise HTTPException(503, "Falha ao analisar a frase. Tente novamente.") from exc

        active = result(
            model,
            getattr(model, "active", "indisponível"),
            getattr(model, "active_name", "Modelo ativo"),
        )
        baseline = getattr(model, "baseline", None)
        baseline_result = (
            result(
                baseline,
                "baseline",
                (getattr(baseline, "report", None) or {}).get("model_name") or "Baseline TF-IDF",
            )
            if baseline and baseline.ready
            else None
        )
        return {"active": active, "baseline": baseline_result, "persisted": False}

    @app.post("/api/analyze")
    async def analyze(request: Request):
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(422, "Envie uma frase para analisar.") from exc
        text = body.get("text") if isinstance(body, dict) else None
        if not isinstance(text, str):
            raise HTTPException(422, "Envie uma frase para analisar.")
        text = text.strip()
        if not text:
            raise HTTPException(422, "Digite uma frase para analisar.")
        if len(text) > MAX_TEXT:
            raise HTTPException(422, "A frase pode ter até 5.000 caracteres.")
        return await run_in_threadpool(analyze_text, text)

    def import_content(content: bytes, filename: str, is_demo: bool = False):
        try:
            records, duplicates = parse_csv(content)
        except InvalidCSV as exc:
            raise HTTPException(422, {"message": exc.message, "issues": exc.issues}) from exc
        file_hash = hashlib.sha256(content).hexdigest()
        try:
            with connect(database) as db:
                if db.execute(
                    "SELECT id FROM imports WHERE file_hash = ?", (file_hash,)
                ).fetchone():
                    raise HTTPException(
                        409, "Este arquivo já foi importado. Os dados foram preservados."
                    )
        except sqlite3.Error as exc:
            raise HTTPException(503, "Falha ao consultar os dados. Tente novamente.") from exc
        try:
            predictions = model.predict([record["text"] for record in records])
            if len(predictions) != len(records) or any(
                label not in LABELS for label in predictions
            ):
                raise ModelUnavailable("Resposta inválida do modelo.")
        except ModelUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        except Exception as exc:
            logger.exception("Falha na classificação do lote")
            raise HTTPException(503, "Falha ao classificar. Nenhum dado foi salvo.") from exc
        try:
            with connect(database) as db:
                db.execute("BEGIN IMMEDIATE")
                cursor = db.execute(
                    "INSERT INTO imports(filename, file_hash, created_at, model_version, is_demo) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        filename[:200],
                        file_hash,
                        datetime.now(UTC).isoformat(),
                        model.version,
                        int(is_demo),
                    ),
                )
                import_id = cursor.lastrowid
                inserted = 0
                for record, sentiment in zip(records, predictions, strict=True):
                    cursor = db.execute(
                        "INSERT INTO mentions(import_id,text,published_at,source,origin_id,"
                        "sentiment,fingerprint) VALUES (?,?,?,?,?,?,?) "
                        "ON CONFLICT(fingerprint) DO NOTHING",
                        (
                            import_id,
                            record["text"],
                            record["published_at"],
                            record["source"],
                            record["origin_id"],
                            sentiment,
                            record["fingerprint"],
                        ),
                    )
                    inserted += cursor.rowcount
                if not inserted:
                    raise HTTPException(409, "Todos os comentários desse arquivo já estão na base.")
                db.execute("UPDATE imports SET total = ? WHERE id = ?", (inserted, import_id))
        except sqlite3.IntegrityError as exc:
            if str(exc) == "UNIQUE constraint failed: imports.file_hash":
                raise HTTPException(409, "Este arquivo já foi importado.") from exc
            logger.exception("Falha de integridade ao salvar o lote")
            raise HTTPException(503, "Falha ao salvar. Nenhum dado foi salvo.") from exc
        except sqlite3.Error as exc:
            logger.exception("Falha no armazenamento do lote")
            raise HTTPException(503, "Falha ao salvar. Nenhum dado foi salvo.") from exc
        return {
            "import_id": import_id,
            "inserted": inserted,
            "duplicates": duplicates + len(records) - inserted,
            "is_demo": is_demo,
            "model_version": model.version,
        }

    @app.post("/api/imports", status_code=201)
    async def upload(file: Annotated[UploadFile, File()]):
        try:
            content = await file.read(MAX_BYTES + 1)
        finally:
            await file.close()
        # No user-supplied paths are opened; only bytes are parsed as UTF-8 CSV.
        return await run_in_threadpool(import_content, content, file.filename or "importacao.csv")

    @app.post("/api/demo", status_code=201)
    def demo():
        return import_content(DEMO_PATH.read_bytes(), "Demonstração · Café Aurora", True)

    @app.get("/api/example.csv")
    def example():
        return FileResponse(
            ROOT / "data" / "examples" / "modelo.csv",
            media_type="text/csv",
            filename="modelo_opinare.csv",
        )

    @app.get("/api/dashboard")
    def dashboard(
        sentiment: Literal["positivo", "negativo", "neutro"] | None = None,
        source: Annotated[str | None, Query(max_length=100)] = None,
        start: date | None = None,
        end: date | None = None,
        import_id: Annotated[int | None, Query(ge=1)] = None,
        q: Annotated[str, Query(max_length=200)] = "",
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    ):
        if start and end and start > end:
            raise HTTPException(422, "A data inicial deve ser anterior ou igual à final.")
        clauses, params = [], []
        for column, value, operator in [
            ("sentiment", sentiment, "="),
            ("source", source, "="),
            ("published_at", start.isoformat() if start else None, ">="),
            ("published_at", end.isoformat() if end else None, "<="),
            ("import_id", import_id, "="),
        ]:
            if value is not None:
                clauses.append(f"m.{column} {operator} ?")
                params.append(value)
        if q.strip():
            clauses.append("instr(lower(m.text), lower(?)) > 0")
            params.append(q.strip())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with connect(database) as db:
            # All indicators and rows in this response must see the same committed snapshot.
            db.execute("BEGIN")
            total_all = db.execute("SELECT COUNT(*) FROM mentions").fetchone()[0]
            counts = dict.fromkeys(LABELS, 0)
            for row in db.execute(
                "SELECT sentiment, COUNT(*) n FROM mentions m" + where + " GROUP BY sentiment",
                params,
            ):
                counts[row["sentiment"]] = row["n"]
            total = sum(counts.values())
            pages = max(1, math.ceil(total / page_size))
            current_page = min(page, pages)
            mentions = [
                dict(row)
                for row in db.execute(
                    "SELECT m.id, m.text, m.published_at, m.source, m.sentiment, m.import_id, "
                    "i.is_demo FROM mentions m JOIN imports i ON i.id=m.import_id"
                    + where
                    + " ORDER BY m.published_at DESC, m.id DESC LIMIT ? OFFSET ?",
                    [*params, page_size, (current_page - 1) * page_size],
                )
            ]
            timeline_rows = db.execute(
                "SELECT published_at, sentiment, COUNT(*) n FROM mentions m"
                + where
                + (" AND " if where else " WHERE ")
                + "published_at IS NOT NULL "
                "GROUP BY published_at, sentiment ORDER BY published_at",
                params,
            ).fetchall()
            timeline = {}
            for row in timeline_rows:
                item = timeline.setdefault(
                    row["published_at"],
                    {
                        "date": row["published_at"],
                        **dict.fromkeys(LABELS, 0),
                    },
                )
                item[row["sentiment"]] = row["n"]
            dated = sum(sum(item[label] for label in LABELS) for item in timeline.values())
            sources = [
                row[0] for row in db.execute("SELECT DISTINCT source FROM mentions ORDER BY source")
            ]
            batches = [dict(row) for row in db.execute("SELECT * FROM imports ORDER BY id DESC")]
            demo_count = db.execute(
                "SELECT COUNT(*) FROM mentions m JOIN imports i ON i.id=m.import_id"
                + where
                + (" AND " if where else " WHERE ")
                + "i.is_demo = 1",
                params,
            ).fetchone()[0]
        return {
            "total": total,
            "total_all": total_all,
            "counts": counts,
            "undated": total - dated,
            "demo_count": demo_count,
            "timeline": list(timeline.values()),
            "mentions": mentions,
            "sources": sources,
            "imports": batches,
            "pagination": {"page": current_page, "pages": pages, "page_size": page_size},
        }

    dist = frontend_dir if frontend_dir is not None else ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
