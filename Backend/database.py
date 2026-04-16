import os
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection


DATABASE_URL = os.getenv(
    "RIDESMART_DATABASE_URL",
    "postgresql+psycopg2://postgres:5120@localhost:5432/postgres",
)

# The tables live under the `ridesmart` schema instead of `public`.
engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args={"options": "-csearch_path=ridesmart,public"},
)


@contextmanager
def get_connection() -> Iterator[Connection]:
    with engine.connect() as connection:
        yield connection


def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(text(query), params or {}).mappings().first()
        return dict(row) if row else None


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(text(query), params or {}).mappings().all()
        return [dict(row) for row in rows]


def fetch_scalar(query: str, params: dict[str, Any] | None = None) -> Any:
    with get_connection() as connection:
        return connection.execute(text(query), params or {}).scalar()
