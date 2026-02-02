"""Database connection and utilities"""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

# Zero-config defaults
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "synthetics")
DB_USER = os.getenv("DB_USER", "synthetics")
DB_PASSWORD = os.getenv("DB_PASSWORD", "synthetics123")

# Connection pool
pool = None


def init_pool(minconn=1, maxconn=10):
    """Initialize connection pool"""
    global pool
    pool = SimpleConnectionPool(
        minconn,
        maxconn,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return pool


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    global pool
    if pool is None:
        init_pool()
    
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_db_cursor(cursor_factory=RealDictCursor):
    """Context manager for database cursors"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
        finally:
            cursor.close()
