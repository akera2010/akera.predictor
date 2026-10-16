"""Database access (SQLAlchemy 2). DATABASE_URL selects the backend; default is
SQLite in backend/data/akeraten.db. Postgres: postgresql+psycopg://user:pw@host/db"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import database_url
from .models import Base, ExpertPrediction, Match, OddsSnapshot, Prediction, Setting, ValueBet

log = logging.getLogger("akeraten.db")
_engine = None
_Session = None
_lock = threading.Lock()


def init_db(url: str | None = None):
    global _engine, _Session
    with _lock:
        url = url or database_url()
        kw = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kw["connect_args"] = {"check_same_thread": False, "timeout": 30}
        _engine = create_engine(url, **kw)
        Base.metadata.create_all(_engine)
        _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


@contextmanager
def session() -> Session:
    if _Session is None:
        init_db()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def safe(fn):
    """Decorator: DB problems must never crash the live loop."""
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa: BLE001
            log.warning("db op %s failed: %s", fn.__name__, e)
            return None
    wrapper.__name__ = fn.__name__
    return wrapper


__all__ = ["init_db", "session", "safe", "Match", "OddsSnapshot", "Prediction", "ExpertPrediction", "ValueBet",
           "Setting", "Base"]
