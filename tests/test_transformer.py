import json

import pytest

from backend.classifier import MODEL_PATH, ROOT, SentimentClassifier
from backend.transformer import (
    REPORT_PATH,
    model_version,
    prepare_portuguese_text,
    sha256_file,
    token_windows,
    verify_assets,
)


def test_all_long_text_tokens_are_kept_in_windows():
    original = list(range(700))
    windows = token_windows(original, 126)
    assert [token for window in windows for token in window] == original
    assert max(map(len, windows)) <= 126
    assert token_windows([], 126) == [[]]
    with pytest.raises(ValueError):
        token_windows([1], 0)


def test_portuguese_preprocessing_handles_composed_emoji_handles_urls_and_laughter():
    result = prepare_portuguese_text("Amei ❤️ 👍🏽 @loja https://exemplo.com kkkkk #MuitoBom")
    assert "❤️" not in result and "👍🏽" not in result
    assert "coração" in result and "polegar" in result and "emoji" in result
    assert "@USER" in result and "@loja" not in result
    assert "HTTPURL" in result and "https://exemplo.com" not in result
    assert "kkkkk" not in result and "kk" in result
    assert "hashtag muito bom" in result


def test_tampered_or_missing_checkpoint_is_rejected(tmp_path):
    (tmp_path / "config.json").write_text("alterado", encoding="utf-8")
    with pytest.raises(ValueError, match="diferente"):
        verify_assets(tmp_path)


def test_selected_transformer_fails_closed_without_silent_baseline_fallback(tmp_path, monkeypatch):
    import backend.classifier as classifier
    import backend.transformer as transformer

    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "transformer_functional_check.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(classifier, "ROOT", tmp_path)

    def fail():
        raise ValueError("Checkpoint inválido")

    monkeypatch.setattr(transformer, "load_transformer_bundle", fail)
    assert not SentimentClassifier().ready
    assert SentimentClassifier(MODEL_PATH).ready


def test_active_transformer_fixes_clear_polarity_and_neutral_examples():
    model = SentimentClassifier()
    assert model.ready
    assert model.report["model_kind"] == "pretrained_transformer"
    assert model.version == model_version()
    assert model.predict(
        [
            "Que experiência ruim. A comida estava horrível.",
            "A loja fica ao lado da biblioteca.",
            "Fui atendida com muita atenção. Adorei!",
            "O número do pedido está no comprovante enviado por e-mail.",
        ]
    ) == ["negativo", "neutro", "positivo", "neutro"]


def test_comparison_uses_same_frozen_synthetic_sample_without_claiming_real_accuracy():
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(
        (ROOT / "data/evaluation/checagem_sentimentos.json").read_text(encoding="utf-8")
    )
    baseline = SentimentClassifier(MODEL_PATH)
    assert baseline.ready
    assert baseline.version == report["baseline_model_id"]
    assert report["evaluation_split"] == "synthetic_functional_check"
    assert report["samples"]["train"] is None
    assert report["samples"]["validation"] == len(fixture["examples"]) == 30
    assert sha256_file(ROOT / "data/evaluation/checagem_sentimentos.json") == report["check_sha256"]
    assert report["metrics"]["f1_macro"] > report["baseline_metrics_same_sample"]["f1_macro"]
    from experiments.train import evaluate

    examples = [(row["text"], row["label"]) for row in fixture["examples"]]
    candidate = SentimentClassifier()
    assert (
        evaluate(candidate, examples)["confusion_matrix"] == report["metrics"]["confusion_matrix"]
    )
    assert (
        evaluate(baseline, examples)["confusion_matrix"]
        == report["baseline_metrics_same_sample"]["confusion_matrix"]
    )
    assert report["check_authorship"]["human_reviewed"] is False
    assert report["test_evaluated"] is False
    assert not (ROOT / "reports/baseline_test.json").exists()
