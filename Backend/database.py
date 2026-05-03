import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection


def load_local_env_file() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env_file()


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


@contextmanager
def get_transaction_connection() -> Iterator[Connection]:
    with engine.begin() as connection:
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
