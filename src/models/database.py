from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "wiki.db"
sqlite_url = f"sqlite:///{DB_PATH}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def _ensure_file_metadata_columns() -> None:
    columns = {
        "language": "TEXT DEFAULT 'en'",
        "status": "TEXT DEFAULT 'completed'",
        "input_hash": "TEXT",
        "model_provider": "TEXT",
        "error_message": "TEXT",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    }
    with engine.begin() as conn:
        existing = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(file)")).fetchall()
        }
        if not existing:
            return
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE file ADD COLUMN {name} {ddl}"))


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _ensure_file_metadata_columns()
