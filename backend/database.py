import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(path: Path):
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                model_version TEXT NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS mentions (
                id INTEGER PRIMARY KEY,
                import_id INTEGER NOT NULL REFERENCES imports(id),
                text TEXT NOT NULL,
                published_at TEXT,
                source TEXT NOT NULL,
                origin_id TEXT NOT NULL,
                sentiment TEXT NOT NULL CHECK(sentiment IN ('positivo', 'negativo', 'neutro')),
                fingerprint TEXT NOT NULL UNIQUE
            );
            CREATE INDEX IF NOT EXISTS mentions_date ON mentions(published_at);
            CREATE INDEX IF NOT EXISTS mentions_import ON mentions(import_id);
        """)
