from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.classifier import MODEL_PATH, ModelUnavailable, SentimentClassifier
from backend.database import connect


class FakeClassifier:
    ready = True
    version = "test-model"

    def predict(self, texts):
        return ["positivo" if "bom" in text.lower() else "negativo" for text in texts]


@pytest.fixture
def database(tmp_path):
    return tmp_path / "test.sqlite3"


@pytest.fixture
def client(database):
    with TestClient(create_app(database, FakeClassifier())) as test_client:
        yield test_client


def upload(client, content, filename="exemplo.csv"):
    return client.post("/api/imports", files={"file": (filename, content, "text/csv")})


def test_import_filter_timeline_and_persistence(client, database):
    content = "texto,data,fonte\nMuito bom,2026-10-27,Loja\nRuim,2026-10-28,Loja\nBom,,Site\n"
    response = upload(client, content.encode())
    assert response.status_code == 201
    assert response.json()["inserted"] == 3
    data = client.get("/api/dashboard").json()
    assert data["counts"] == {"positivo": 2, "neutro": 0, "negativo": 1}
    assert data["undated"] == 1
    assert sum(sum(row[key] for key in data["counts"]) for row in data["timeline"]) == 2
    assert client.get("/api/dashboard?sentiment=positivo").json()["total"] == 2
    assert client.get("/api/dashboard?source=Site").json()["total"] == 1
    assert client.get("/api/dashboard?start=2026-10-28&end=2026-10-28").json()["total"] == 1
    assert client.get("/api/dashboard?q=Ruim").json()["total"] == 1
    assert client.get("/api/dashboard?q=%25").json()["total"] == 0
    assert client.get("/api/dashboard?source=%27%20OR%201%3D1--").json()["total"] == 0
    assert client.get("/api/dashboard?start=2026-10-29&end=2026-10-28").status_code == 422
    assert client.get("/api/dashboard?sentiment=inexistente").status_code == 422
    with TestClient(create_app(database, FakeClassifier())) as restarted:
        assert restarted.get("/api/dashboard").json()["total"] == 3


def test_invalid_batch_is_atomic(client, database):
    response = upload(client, b"texto,data\nBom,2026-10-28\nRuim,invalida\n")
    assert response.status_code == 422
    assert response.json()["detail"]["issues"][0]["line"] == 3
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM mentions").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM imports").fetchone()[0] == 0


def test_duplicate_file_rows_and_cross_batch_identity(client, database):
    content = b"texto\nBom\nBom\n"
    result = upload(client, content).json()
    assert result["inserted"] == 1 and result["duplicates"] == 1
    assert upload(client, content).status_code == 409
    # Different bytes and filename do not create duplicate rows or empty batches.
    assert upload(client, b"texto\nBom\n", "outro.csv").status_code == 409
    result = upload(client, b"texto\nBom\nRuim\n").json()
    assert result["inserted"] == 1 and result["duplicates"] == 1
    with connect(database) as db:
        assert db.execute("SELECT SUM(total) FROM imports").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM imports").fetchone()[0] == 2


def test_concurrent_duplicate_import_is_atomic(client):
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: upload(client, b"texto\nBom\n"), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert client.get("/api/dashboard").json()["total"] == 1


def test_demo_labels_are_explicit_and_reimport_is_safe(client):
    assert client.post("/api/demo").status_code == 201
    data = client.get("/api/dashboard").json()
    assert data["total"] == data["demo_count"] == 30
    assert data["undated"] == 2
    assert all(row["is_demo"] for row in data["mentions"])
    assert client.post("/api/demo").status_code == 409
    example = client.get("/api/example.csv")
    assert example.status_code == 200
    assert "text/csv" in example.headers["content-type"]


@pytest.mark.parametrize("mode", ["unavailable", "exception", "wrong-length", "wrong-label"])
def test_classifier_failures_never_save_or_become_neutral(database, mode):
    class Broken(FakeClassifier):
        def predict(self, texts):
            if mode == "unavailable":
                raise ModelUnavailable("Modelo indisponível")
            if mode == "exception":
                raise RuntimeError("Falha inesperada")
            return [] if mode == "wrong-length" else ["desconhecido"]

    with TestClient(create_app(database, Broken())) as client:
        assert upload(client, b"texto\nBom\n").status_code == 503
        assert client.get("/api/dashboard").json()["total"] == 0


def test_database_failure_rolls_back_entire_batch(client, database):
    with connect(database) as db:
        db.execute("""CREATE TRIGGER reject_second BEFORE INSERT ON mentions
            WHEN NEW.text = 'Ruim' BEGIN SELECT RAISE(ABORT, 'forced failure'); END""")
    assert upload(client, b"texto\nBom\nRuim\n").status_code == 503
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM imports").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM mentions").fetchone()[0] == 0


def test_pagination_is_bounded_and_options_survive_empty_filter(client):
    upload(client, b"texto\nBom\nRuim\n")
    data = client.get("/api/dashboard?page=100&page_size=1").json()
    assert data["pagination"]["page"] == 2
    assert len(data["mentions"]) == 1
    assert client.get("/api/dashboard?page_size=101").status_code == 422
    empty = client.get("/api/dashboard?q=naoexiste").json()
    assert empty["total"] == 0 and empty["total_all"] == 2
    assert empty["sources"] and empty["imports"]


def test_local_origin_and_host_boundaries(client):
    assert client.post("/api/demo", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/dashboard", headers={"Host": "evil.example"}).status_code == 400
    assert client.get("/api/health").json()["model_ready"] is True


def test_missing_model_is_readable_but_cannot_import(database, tmp_path):
    missing = SentimentClassifier(tmp_path / "missing.joblib")
    with TestClient(create_app(database, missing)) as client:
        assert client.get("/api/health").json()["model_ready"] is False
        assert client.get("/api/dashboard").json()["total"] == 0
        assert upload(client, b"texto\nBom\n").status_code == 503


def test_real_trained_model_has_three_classes_and_handles_demo():
    classifier = SentimentClassifier(path=MODEL_PATH)
    assert classifier.ready, "Prepare o modelo com python -m experiments.train antes deste teste."
    assert set(classifier.bundle["pipeline"].classes_) == {"positivo", "negativo", "neutro"}
    predictions = classifier.predict(
        [
            "Adorei! Muito bom, maravilhoso!",
            "Péssimo, horrível! Não gostei.",
            "O programa começa às oito horas.",
        ]
    )
    assert len(predictions) == 3
    assert all(value in {"positivo", "negativo", "neutro"} for value in predictions)
    assert classifier.report["model_id"] == classifier.version


def test_analyze_returns_scores_and_does_not_persist(database):
    class Scored(FakeClassifier):
        active = "bertimbau"
        active_name = "BERTimbau"
        baseline = FakeClassifier()

        def predict_proba(self, texts):
            return [{"negativo": 0.1, "neutro": 0.2, "positivo": 0.7}]

    with TestClient(create_app(database, Scored())) as client:
        response = client.post("/api/analyze", json={"text": "Muito bom"})
        assert response.status_code == 200
        assert response.json()["active"]["scores"]["positivo"] == 0.7
        assert response.json()["baseline"]["scores"] is None
        assert response.json()["persisted"] is False
        assert client.get("/api/dashboard").json()["total_all"] == 0


def test_analyze_validation_and_origin(client):
    assert client.post("/api/analyze", json={}).status_code == 422
    assert (
        client.post("/api/analyze", json={"text": " "}).json()["detail"]
        == "Digite uma frase para analisar."
    )
    assert client.post("/api/analyze", json={"text": "a" * 5001}).status_code == 422
    assert (
        client.post(
            "/api/analyze", json={"text": "bom"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_analyze_unavailable(database):
    class Broken(FakeClassifier):
        ready = False

    with TestClient(create_app(database, Broken())) as client:
        assert client.post("/api/analyze", json={"text": "bom"}).status_code == 503


def test_download_template_contains_no_fictitious_comments(client):
    template = client.get("/api/example.csv")
    assert template.content.decode("utf-8").strip() == "texto,data,fonte,id_origem"
    assert client.post("/api/demo").status_code == 201
    assert client.get("/api/dashboard").json()["demo_count"] == 30


def test_concurrent_dashboard_reads_keep_totals_rows_and_dates_consistent(client):
    def writer():
        for i in range(12):
            content = f"texto,data\nBom {i},2026-10-28\nRuim {i},2026-10-28\n".encode()
            assert upload(client, content).status_code == 201

    def reader():
        for _ in range(20):
            result = client.get("/api/dashboard").json()
            assert result["total"] == sum(result["counts"].values())
            assert result["undated"] == 0
            assert len(result["mentions"]) == min(10, result["total"])
            assert (
                sum(
                    sum(row[label] for label in ("positivo", "negativo", "neutro"))
                    for row in result["timeline"]
                )
                == result["total"]
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(writer), pool.submit(reader)]
        for future in futures:
            future.result()
