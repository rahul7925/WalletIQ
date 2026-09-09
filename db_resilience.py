"""
db_resilience.py — Database Resiliency, Connection Pooling & Transaction Engine
Provides:
1. ping_database(): Fast, timed connection liveness verification with latency measurement.
2. safe_commit(): Automatic retry on transient MySQL disconnects and deadlocks with auto-rollback.
3. db_transaction(): Atomic context manager with retry and clean rollback guarantees.
4. db_retry(): Intelligent decorator for database-intensive operations.
5. is_transient_db_error(): Detects recoverable cloud database dropouts.
6. get_connection_pool_stats(): Real-time pool telemetry for production observability.
"""

import time
import random
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Optional, Dict, Any, Callable

from sqlalchemy import text
from sqlalchemy.exc import (
    OperationalError,
    InterfaceError,
    DBAPIError,
    PendingRollbackError,
    ResourceClosedError,
)

log = logging.getLogger('walletiq.db_resilience')

# MySQL error codes considered transient and safe to retry
# 2006: MySQL server has gone away
# 2013: Lost connection to MySQL server during query
# 1205: Lock wait timeout exceeded
# 1213: Deadlock found when trying to get lock
# 1040: Too many connections
# 2003: Can't connect to MySQL server
# 2002: Can't connect through local socket
TRANSIENT_MYSQL_ERRNO = {2006, 2013, 1205, 1213, 1040, 2003, 2002}


def is_transient_db_error(exc: Exception) -> bool:
    """Determine whether an exception is a transient database connection/lock issue."""
    if not isinstance(exc, (OperationalError, InterfaceError, DBAPIError)):
        return False

    # Check inner DBAPI error code if available (e.g. PyMySQL Error.args[0])
    orig = getattr(exc, 'orig', None)
    if orig and hasattr(orig, 'args') and orig.args:
        first_arg = orig.args[0]
        if isinstance(first_arg, int) and first_arg in TRANSIENT_MYSQL_ERRNO:
            return True

    err_str = str(exc).lower()
    transient_indicators = (
        'server has gone away',
        'lost connection',
        'connection reset',
        'deadlock found',
        'lock wait timeout',
        'can\'t connect',
        'connection refused',
        'broken pipe',
        'cannot connect to host',
        'too many connections',
        'timed out',
    )
    return any(indicator in err_str for indicator in transient_indicators)


def ping_database(engine=None, session=None) -> Dict[str, Any]:
    """
    Perform a live, timed query (SELECT 1) against the database.
    Returns diagnostic telemetry including latency in milliseconds, dialect, and pool health.
    """
    # 1. If an explicit engine was passed, ping via engine.connect() directly
    if engine is not None:
        start_time = time.perf_counter()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                is_healthy = result == 1
                dialect_name = engine.dialect.name
                driver_name = engine.dialect.driver
                return {
                    "healthy": is_healthy,
                    "latency_ms": latency_ms,
                    "dialect": f"{dialect_name}+{driver_name}" if driver_name else dialect_name,
                    "pool": get_connection_pool_stats(engine),
                }
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log.warning(f"Database engine ping failed ({latency_ms}ms): {exc}")
            dialect_name = engine.dialect.name if hasattr(engine, 'dialect') else 'unknown'
            return {
                "healthy": False,
                "latency_ms": latency_ms,
                "dialect": dialect_name,
                "error": str(exc),
                "pool": get_connection_pool_stats(engine),
            }

    # 2. Otherwise ping via the active session (respecting session mocks/patches)
    from app import db
    if session is None:
        session = db.session
    engine = getattr(session, 'bind', None) or getattr(db, 'engine', None)

    start_time = time.perf_counter()
    try:
        result = session.execute(text("SELECT 1")).scalar()
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_healthy = result == 1
        dialect_name = engine.dialect.name if engine and hasattr(engine, 'dialect') else 'unknown'
        driver_name = engine.dialect.driver if engine and hasattr(engine, 'dialect') else ''

        return {
            "healthy": is_healthy,
            "latency_ms": latency_ms,
            "dialect": f"{dialect_name}+{driver_name}" if driver_name else dialect_name,
            "pool": get_connection_pool_stats(engine) if engine else {},
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log.warning(f"Database session ping failed ({latency_ms}ms): {exc}")
        dialect_name = engine.dialect.name if engine and hasattr(engine, 'dialect') else 'unknown'
        return {
            "healthy": False,
            "latency_ms": latency_ms,
            "dialect": dialect_name,
            "error": str(exc),
            "pool": get_connection_pool_stats(engine) if engine else {},
        }


def get_connection_pool_stats(engine=None) -> Dict[str, Any]:
    """Retrieve runtime connection pool statistics for monitoring."""
    if engine is None:
        from app import db
        engine = db.engine

    pool = getattr(engine, 'pool', None)
    if not pool:
        return {"status": "no_pool"}

    # Handle StaticPool (SQLite in-memory or fallback)
    pool_class = pool.__class__.__name__
    if pool_class in ('StaticPool', 'NullPool'):
        return {"type": pool_class, "status": "active"}

    try:
        return {
            "type": pool_class,
            "size": pool.size() if hasattr(pool, 'size') else None,
            "checkedin": pool.checkedin() if hasattr(pool, 'checkedin') else None,
            "checkedout": pool.checkedout() if hasattr(pool, 'checkedout') else None,
            "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
        }
    except Exception as exc:
        return {"type": pool_class, "error": str(exc)}


def safe_commit(session=None, max_retries: int = 3, backoff: float = 0.2) -> bool:
    """
    Safely commit the active database session.
    If a transient disconnect or deadlock occurs, it retries with exponential backoff.
    On final failure, it automatically rolls back the session to prevent connection poisoning.
    """
    if session is None:
        from app import db
        session = db.session

    for attempt in range(1, max_retries + 1):
        try:
            session.commit()
            return True
        except Exception as exc:
            if attempt < max_retries and is_transient_db_error(exc):
                jitter = random.uniform(0.05, 0.15)
                sleep_time = (backoff * (2 ** (attempt - 1))) + jitter
                log.warning(
                    f"Transient database error on commit (attempt {attempt}/{max_retries}): {exc}. "
                    f"Retrying in {sleep_time:.2f}s..."
                )
                try:
                    session.rollback()
                except Exception:
                    pass
                time.sleep(sleep_time)
            else:
                log.error(f"Fatal database commit error (attempt {attempt}/{max_retries}): {exc}")
                try:
                    session.rollback()
                except Exception as rb_exc:
                    log.error(f"Rollback failed after fatal commit error: {rb_exc}")
                raise exc

    return False


@contextmanager
def db_transaction(session=None, max_retries: int = 3, backoff: float = 0.2):
    """
    Atomic transaction context manager.
    Automatically commits on block exit, retries on transient errors,
    and rolls back cleanly if any unhandled exception occurs.

    Usage:
        with db_transaction():
            db.session.add(expense)
    """
    if session is None:
        from app import db
        session = db.session

    for attempt in range(1, max_retries + 1):
        try:
            yield session
            safe_commit(session, max_retries=1)
            break
        except Exception as exc:
            try:
                session.rollback()
            except Exception:
                pass

            if attempt < max_retries and is_transient_db_error(exc):
                sleep_time = (backoff * (2 ** (attempt - 1))) + random.uniform(0.05, 0.15)
                log.warning(
                    f"Transient error in db_transaction block (attempt {attempt}/{max_retries}): {exc}. "
                    f"Retrying in {sleep_time:.2f}s..."
                )
                time.sleep(sleep_time)
            else:
                raise exc


def db_retry(max_retries: int = 3, backoff: float = 0.2):
    """Decorator to retry a database read/write function upon transient connection drops."""
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt < max_retries and is_transient_db_error(exc):
                        sleep_time = (backoff * (2 ** (attempt - 1))) + random.uniform(0.05, 0.15)
                        log.warning(
                            f"Transient error in {fn.__name__} (attempt {attempt}/{max_retries}): {exc}. "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        time.sleep(sleep_time)
                    else:
                        raise exc
        return wrapper
    return decorator
