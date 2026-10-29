"""Recalcula previsões sem apagar comentários, com backup e transação única."""

import argparse
import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from backend.classifier import LABELS, ROOT, SentimentClassifier
from backend.database import connect


def snapshot(db):
    mentions = [
        tuple(row)
        for row in db.execute(
            "SELECT id, text, published_at, source, origin_id, sentiment, fingerprint, import_id "
            "FROM mentions ORDER BY id"
        )
    ]
    batches = [
        tuple(row)
        for row in db.execute(
            "SELECT id, filename, file_hash, created_at, model_version, is_demo, total "
            "FROM imports ORDER BY id"
        )
    ]
    return mentions, batches


def default_database() -> Path:
    return Path(os.environ.get("OPINARE_DB", ROOT / "var" / "opinare.sqlite3"))


def reclassify(database: Path, model=None) -> dict:
    if not database.is_file():
        raise ValueError("Banco de dados não encontrado.")
    model = model if model is not None else SentimentClassifier()
    if not model.ready:
        raise ValueError("O classificador não está pronto; nenhum dado foi alterado.")
    with connect(database) as db:
        db.execute("BEGIN")
        mentions, batches = snapshot(db)
    if not mentions:
        return {"total": 0, "changed": 0, "model_version": model.version}
    predictions = model.predict([row[1] for row in mentions])
    if len(predictions) != len(mentions) or any(value not in LABELS for value in predictions):
        raise ValueError("Previsões inválidas; nenhum dado foi alterado.")
    backup_dir = database.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup = (
        backup_dir / f"{database.stem}-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex[:8]}.sqlite3"
    )
    with connect(database) as db:
        with closing(sqlite3.connect(backup)) as destination:
            db.backup(destination)
        with closing(sqlite3.connect(backup.resolve().as_uri() + "?mode=ro", uri=True)) as check:
            if check.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("O backup não passou na verificação; nenhum dado foi alterado.")
            if snapshot(check) != (mentions, batches):
                raise ValueError("A base mudou durante o backup. Atualização cancelada.")
        db.execute("BEGIN IMMEDIATE")
        if snapshot(db) != (mentions, batches):
            raise ValueError(
                "A base mudou durante a análise. Atualização cancelada; tente novamente."
            )
        for row, prediction in zip(mentions, predictions, strict=True):
            db.execute("UPDATE mentions SET sentiment = ? WHERE id = ?", (prediction, row[0]))
        db.execute("UPDATE imports SET model_version = ?", (model.version,))
    result = {
        "total": len(mentions),
        "changed": sum(
            row[5] != prediction for row, prediction in zip(mentions, predictions, strict=True)
        ),
        "model_version": model.version,
        "backup": str(backup),
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=default_database())
    args = parser.parse_args()
    print(json.dumps(reclassify(args.database), ensure_ascii=False, indent=2))
