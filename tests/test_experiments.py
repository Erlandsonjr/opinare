import pytest

from backend.classifier import prepare_text
from experiments import train


def test_corrupt_cached_dataset_is_rejected_before_training(tmp_path, monkeypatch):
    monkeypatch.setattr(train, "RAW", tmp_path)
    (tmp_path / "train_text.txt").write_text("alteração local", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        train.download_dataset()


def test_deduplication_drops_conflicting_labels_and_normalizes_mentions(tmp_path, monkeypatch):
    monkeypatch.setattr(train, "RAW", tmp_path)
    (tmp_path / "train_text.txt").write_text(
        "Adorei @ana\nAdorei @bia\nRuim\nRuim\nHorário às oito\n", encoding="utf-8"
    )
    (tmp_path / "train_labels.txt").write_text("2\n2\n0\n2\n1\n", encoding="utf-8")
    rows, removed = train.read_split("train")
    assert rows == [("Adorei @ana", "positivo"), ("Horário às oito", "neutro")]
    assert removed == 3
    assert prepare_text("Não   gostei! 😢 https://exemplo.org @ana") == "Não gostei! 😢 URL USUARIO"
