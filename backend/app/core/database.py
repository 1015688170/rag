from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
DATABASE_PATH = STORAGE_DIR / "rag.db"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app.models import knowledge  # noqa: F401

    Base.metadata.create_all(bind=engine)
    migrate_sqlite_documents_permissions()


def migrate_sqlite_documents_permissions() -> None:
    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(documents)")).mappings().all()
        columns = {row["name"] for row in rows}
        migrations = [
            ("visibility", "ALTER TABLE documents ADD COLUMN visibility VARCHAR NOT NULL DEFAULT 'public'"),
            ("owner_id", "ALTER TABLE documents ADD COLUMN owner_id VARCHAR"),
            ("allowed_departments", "ALTER TABLE documents ADD COLUMN allowed_departments TEXT NOT NULL DEFAULT '[]'"),
            ("allowed_roles", "ALTER TABLE documents ADD COLUMN allowed_roles TEXT NOT NULL DEFAULT '[]'"),
        ]
        for column_name, statement in migrations:
            if column_name not in columns:
                connection.execute(text(statement))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
