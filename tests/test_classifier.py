import json

import pytest

import backend.classifier as classifier
from backend.transformer import TransformerClassifier


class FakeBaseline:
    ready = True
    version = "baseline-test"
    report = {"model_name": "TF-IDF"}

    def __init__(self, path):
        self.path = path

    def predict(self, texts):
        return ["positivo"] * len(texts)

    def predict_proba(self, texts):
        return [{"negativo": 0.1, "neutro": 0.2, "positivo": 0.7}] * len(texts)


def test_missing_transformer_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(classifier, "BaselineClassifier", FakeBaseline)
    monkeypatch.setattr(classifier, "TRANSFORMER_DIR", tmp_path / "missing")
    model = classifier.SentimentClassifier()
    assert model.active == "baseline"
    assert model.fallback_reason
    assert set(model.predict_proba(["bom"])[0]) == set(classifier.LABELS)


def test_baseline_mode_skips_transformer(monkeypatch):
    monkeypatch.setenv("OPINARE_MODEL", "baseline")
    monkeypatch.setattr(classifier, "BaselineClassifier", FakeBaseline)
    model = classifier.SentimentClassifier()
    assert model.active == "baseline" and model.fallback_reason is None


def test_transformer_load_failure_falls_back(monkeypatch, tmp_path):
    import backend.transformer as transformer

    monkeypatch.setattr(classifier, "BaselineClassifier", FakeBaseline)
    monkeypatch.setattr(classifier, "TRANSFORMER_DIR", tmp_path)

    def fail(_directory):
        raise ImportError("No module named torch")

    monkeypatch.setattr(transformer, "TransformerClassifier", fail)
    model = classifier.SentimentClassifier()
    assert model.active == "baseline" and "PyTorch" in model.fallback_reason


def test_transformer_rejects_hash_mismatch_and_incomplete_reports(tmp_path):
    from backend.transformer import REQUIRED_FILES

    files = dict.fromkeys(REQUIRED_FILES, "bad")
    for name in REQUIRED_FILES:
        (tmp_path / name).write_text("{}", encoding="utf-8")
    report = {"label_order": list(classifier.LABELS), "files": files}
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="inválido"):
        TransformerClassifier(tmp_path)
    report["files"] = {"config.json": "bad"}
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="todos os arquivos"):
        TransformerClassifier(tmp_path)


def test_hash_failure_uses_baseline(monkeypatch, tmp_path):
    import backend.transformer as transformer

    monkeypatch.setattr(classifier, "BaselineClassifier", FakeBaseline)
    monkeypatch.setattr(classifier, "TRANSFORMER_DIR", tmp_path)
    monkeypatch.setattr(
        transformer, "TransformerClassifier", lambda path: (_ for _ in ()).throw(ValueError("hash"))
    )
    model = classifier.SentimentClassifier()
    assert model.active == "baseline"
    assert "inválido" in model.fallback_reason


def test_baseline_probability_order(monkeypatch, tmp_path):
    class Pipeline:
        classes_ = ["positivo", "negativo", "neutro"]

        def predict_proba(self, texts):
            return [[0.7, 0.1, 0.2] for _ in texts]

    path = tmp_path / "baseline.joblib"
    path.touch()
    monkeypatch.setattr(
        classifier.joblib,
        "load",
        lambda _: {"model_id": "id", "pipeline": Pipeline(), "report": {}},
    )
    scores = classifier.BaselineClassifier(path).predict_proba(["bom"])[0]
    assert scores == {"negativo": 0.1, "neutro": 0.2, "positivo": 0.7}
