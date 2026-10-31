from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> Engine:
    kwargs: dict[str, object] = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            # A shared in-memory database needs a single connection across sessions.
            kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **kwargs)


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


engine = build_engine(get_settings().database_url)
SessionLocal = build_session_factory(engine)
