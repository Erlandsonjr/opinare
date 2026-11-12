import json
from pathlib import Path

import pytest

from backend.database import connect, initialize
from experiments.reclassify import default_database, reclassify, snapshot


class Model:
    ready = True
    version = "new-model"

    def predict(self, texts):
        return ["positivo" if "Bom" in text else "negativo" for text in texts]


@pytest.fixture
def populated_db(tmp_path):
    path = tmp_path / "test.sqlite3"
    initialize(path)
    with connect(path) as db:
        db.execute(
            "INSERT INTO imports VALUES (1, 'exemplo.csv', 'file-1', '2026-10-29', 'old', 1, 2)"
        )
        db.execute(
            "INSERT INTO mentions VALUES (1,1,'Bom','2026-10-28','Fonte','a','neutro','fp-a')"
        )
        db.execute("INSERT INTO mentions VALUES (2,1,'Ruim',NULL,'Fonte','b','neutro','fp-b')")
    return path


def read(path):
    with connect(path) as db:
        return snapshot(db)


def test_reclassify_backs_up_and_preserves_all_original_fields(populated_db):
    before_mentions, before_batches = read(populated_db)
    result = reclassify(populated_db, Model())
    assert result["total"] == result["changed"] == 2
    assert read(Path(result["backup"])) == (before_mentions, before_batches)
    mentions, batches = read(populated_db)
    assert [row[5] for row in mentions] == ["positivo", "negativo"]
    assert batches[0][4] == "new-model"
    for before, after in zip(before_mentions, mentions, strict=True):
        assert before[:5] + before[6:] == after[:5] + after[6:]
    assert before_batches[0][:4] + before_batches[0][5:] == batches[0][:4] + batches[0][5:]


def test_reclassification_rolls_back_all_rows_on_database_error(populated_db):
    before = read(populated_db)
    with connect(populated_db) as db:
        db.execute("""CREATE TRIGGER fail_second BEFORE UPDATE ON mentions
            WHEN NEW.id=2 BEGIN SELECT RAISE(ABORT,'forced failure'); END""")
    with pytest.raises(Exception, match="forced failure"):
        reclassify(populated_db, Model())
    assert read(populated_db) == before
    assert len(list((populated_db.parent / "backups").glob("*.sqlite3"))) == 1


@pytest.mark.parametrize("failure", ["exception", "length", "label"])
def test_invalid_predictions_never_change_saved_data(populated_db, failure):
    before = read(populated_db)

    class Broken(Model):
        def predict(self, texts):
            if failure == "exception":
                raise RuntimeError("failed")
            return [] if failure == "length" else ["errado"] * len(texts)

    with pytest.raises((RuntimeError, ValueError)):
        reclassify(populated_db, Broken())
    assert read(populated_db) == before


def test_concurrent_change_is_preserved_and_reclassification_cancelled(populated_db):
    class Concurrent(Model):
        def predict(self, texts):
            with connect(populated_db) as db:
                db.execute("UPDATE mentions SET text='Comentário editado' WHERE id=1")
            return super().predict(texts)

    with pytest.raises(ValueError, match="base mudou"):
        reclassify(populated_db, Concurrent())
    mentions, batches = read(populated_db)
    assert mentions[0][1] == "Comentário editado"
    assert [row[5] for row in mentions] == ["neutro", "neutro"]
    assert batches[0][4] == "old"


def test_empty_database_is_not_modified(tmp_path):
    path = tmp_path / "empty.sqlite3"
    initialize(path)
    assert reclassify(path, Model())["total"] == 0
    assert len(list((path.parent / "backups").glob("*.sqlite3"))) == 1
    assert (
        json.loads((path.parent / "last_reclassification.json").read_text(encoding="utf-8"))[
            "total"
        ]
        == 0
    )


def test_cli_default_database_matches_app_environment(tmp_path, monkeypatch):
    target = tmp_path / "custom.sqlite3"
    monkeypatch.setenv("OPINARE_DB", str(target))
    assert default_database() == target


def test_backup_verification_failure_cancels_before_any_update(populated_db, monkeypatch):
    import sqlite3

    before = read(populated_db)
    real_connect = sqlite3.connect

    class CorruptResult:
        def fetchall(self):
            return [("simulated corruption",)]

    class BackupCheck:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, query):
            if query == "PRAGMA integrity_check":
                return CorruptResult()
            return self.connection.execute(query)

        def close(self):
            self.connection.close()

    def patched_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        return BackupCheck(connection) if kwargs.get("uri") else connection

    monkeypatch.setattr(sqlite3, "connect", patched_connect)
    with pytest.raises(ValueError, match="backup não passou"):
        reclassify(populated_db, Model())
    assert read(populated_db) == before
