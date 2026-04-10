"""Oracle connection pool using python-oracledb."""
from contextlib import contextmanager
from typing import Generator

import oracledb

from config import settings

_pool: oracledb.ConnectionPool | None = None


def get_pool() -> oracledb.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=settings.oracle_user,
            password=settings.oracle_password,
            dsn=settings.oracle_dsn,
            min=1,
            max=10,
            increment=1,
        )
    return _pool


@contextmanager
def get_connection() -> Generator[oracledb.Connection, None, None]:
    pool = get_pool()
    conn = pool.acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.release(conn)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
