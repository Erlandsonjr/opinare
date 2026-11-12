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


def test_b2w_reads_only_text_and_rating_and_maps_classes():
    from experiments import data

    payload = (
        "submission_date,review_text,overall_rating,reviewer_gender,reviewer_state\n"
        '2018-01-01,"Produto excelente, chegou rápido",5,F,SP\n'
        "2018-01-02,Veio quebrado e ninguém respondeu,1,M,RJ\n"
        "2018-01-03,É razoável pelo preço pago,3,F,PI\n"
        "2018-01-04,Ok,4,F,PI\n"
        "2018-01-05,Veio quebrado e ninguém respondeu,4,M,RJ\n"
        "2018-01-06,Produto excelente,  chegou rápido,5,F,SP\n"
    ).encode()
    rows, stats = data.read_b2w(payload)
    assert ("É razoável pelo preço pago", "neutro") in rows
    assert ("Produto excelente, chegou rápido", "positivo") in rows
    # Conflicting duplicates are dropped; short texts are discarded.
    assert all("quebrado" not in text for text, _ in rows)
    assert stats["empty_or_short"] == 1
    assert stats["conflicting_duplicate_groups"] == 1
    assert all(isinstance(row, tuple) and len(row) == 2 for row in rows)


def test_b2w_rejects_corrupt_cache(tmp_path, monkeypatch):
    from experiments import data

    target = tmp_path / "B2W-Reviews01.csv"
    target.write_text("alterado", encoding="utf-8")
    monkeypatch.setattr(data, "B2W_RAW", target)
    with pytest.raises(ValueError, match="hash"):
        data.download_b2w()
