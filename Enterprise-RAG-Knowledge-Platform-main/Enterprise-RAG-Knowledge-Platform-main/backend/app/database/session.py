"""
Database engine + session factory.

Uses synchronous SQLAlchemy 2.0. FastAPI runs sync route/dependency
functions in a threadpool automatically, so this scales fine for a
day-1 build while keeping the code simple to read and extend. Swapping
to `asyncpg` + async sessions later only touches this file and the
`get_db` dependency.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config.settings import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """FastAPI dependency that yields a DB session and guarantees closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
