"""Database engine, session factory and the Base class for all tables."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


database_url = get_settings().database_url

if database_url.startswith("postgresql"):
    connect_args = {"prepare_threshold": None}  # Neon's pooler endpoint doesn't support prepared statements
else:
    connect_args = {"check_same_thread": False}  # SQLite fallback when no DATABASE_URL is set

engine = create_engine(
    database_url,
    pool_pre_ping=True,  # Neon closes idle connections; check before reuse
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    with SessionLocal() as db:
        yield db
