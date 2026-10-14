"""
db.py
=================================================================================
Database helper module
Ethical Guideline and Governance Framework for AI Use in Nigerian Tech Startups
=================================================================================

This is the ONLY module that talks directly to SQLite.  Every other module and
the Streamlit app use these four helpers:

    get_connection()                -> raw sqlite3 connection
    execute_query(query, params)    -> write  (INSERT / UPDATE / DELETE)
    fetch_all(query, params)        -> list[dict]
    fetch_one(query, params)        -> dict | None

Design notes
------------
* Connections are cached per thread, because Streamlit runs each browser
  session in its own ScriptRunner thread and a sqlite3 connection may not be
  shared across threads.
* SQLite runs in WAL mode with a busy timeout and automatic retries, so a
  developer saving an assessment cannot be locked out by a governance officer
  reading the audit trail at the same moment.
* ``PRAGMA foreign_keys = ON`` is set on every connection, so the relationships
  between AI systems, assessments, approvals, incidents and audit records are
  genuinely enforced by the database engine rather than merely documented.
* The database is 100% local.  No cloud service, no paid API, no network.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"

DB_FILENAME: str = "aigovtech.db"
DB_PATH: Path = DATA_DIR / DB_FILENAME

# Concurrency tuning
BUSY_TIMEOUT_MS: int = 8000
MAX_RETRIES: int = 5
RETRY_DELAY_SECONDS: float = 0.15

_local = threading.local()


class DatabaseError(Exception):
    """Raised when a database operation fails, with a friendly message."""


# ---------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Return the thread-local SQLite connection, creating it on first use."""
    conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)

    if conn is not None:
        try:
            conn.execute("SELECT 1")  # cheap liveness probe
            return conn
        except sqlite3.Error:
            _local.conn = None

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=15.0,
        check_same_thread=False,
        isolation_level=None,  # autocommit
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS};")
    _local.conn = conn
    return conn


def close_connection() -> None:
    """Close the connection held by the current thread (used by tests)."""
    conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except sqlite3.Error:
            pass
        _local.conn = None


def _is_locked_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "locked" in text or "busy" in text


def _run_with_retry(operation: Callable[[], Any]) -> Any:
    """Retry briefly when another session holds the write lock."""
    last_error: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if not _is_locked_error(exc):
                raise
            last_error = exc
            time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
    raise DatabaseError(
        "The database is busy (another session is writing at the same moment). "
        "Please try that action again."
    ) from last_error


# ---------------------------------------------------------------------
# Public query helpers
# ---------------------------------------------------------------------
def execute_query(query: str, params: Sequence[Any] = ()) -> int:
    """
    Run an INSERT / UPDATE / DELETE.

    Returns the new ``lastrowid`` for an INSERT, otherwise the number of rows
    affected.
    """
    def operation() -> int:
        conn = get_connection()
        cur = conn.execute(query, tuple(params))
        try:
            if query.lstrip().upper().startswith("INSERT"):
                return int(cur.lastrowid or 0)
            return int(cur.rowcount)
        finally:
            try:
                cur.close()
            except Exception:  # pragma: no cover
                pass

    try:
        return _run_with_retry(operation)
    except DatabaseError:
        raise
    except sqlite3.IntegrityError as exc:
        raise DatabaseError(_friendly_integrity_error(exc)) from exc
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc


def execute_many(query: str, param_list: Iterable[Sequence[Any]]) -> int:
    """Run the same statement for many parameter sets."""
    params = [tuple(p) for p in param_list]

    def operation() -> int:
        conn = get_connection()
        cur = conn.executemany(query, params)
        try:
            return int(cur.rowcount)
        finally:
            try:
                cur.close()
            except Exception:  # pragma: no cover
                pass

    try:
        return _run_with_retry(operation)
    except DatabaseError:
        raise
    except sqlite3.IntegrityError as exc:
        raise DatabaseError(_friendly_integrity_error(exc)) from exc
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc


def fetch_all(query: str, params: Sequence[Any] = ()) -> list[dict]:
    """Run a SELECT and return every row as a plain dictionary."""
    def operation() -> list[dict]:
        conn = get_connection()
        cur = conn.execute(query, tuple(params))
        try:
            return [dict(row) for row in cur.fetchall()]
        finally:
            try:
                cur.close()
            except Exception:  # pragma: no cover
                pass

    try:
        return _run_with_retry(operation)
    except DatabaseError:
        raise
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc


def fetch_one(query: str, params: Sequence[Any] = ()) -> Optional[dict]:
    """Run a SELECT and return the first row as a dictionary (or None)."""
    def operation() -> Optional[dict]:
        conn = get_connection()
        cur = conn.execute(query, tuple(params))
        try:
            row = cur.fetchone()
            return dict(row) if row is not None else None
        finally:
            try:
                cur.close()
            except Exception:  # pragma: no cover
                pass

    try:
        return _run_with_retry(operation)
    except DatabaseError:
        raise
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc


def fetch_scalar(query: str, params: Sequence[Any] = (), default: Any = None) -> Any:
    """Run a SELECT and return the first column of the first row."""
    row = fetch_one(query, params)
    if row is None:
        return default
    value = next(iter(row.values()))
    return default if value is None else value


def execute_script(script: str) -> None:
    """Execute a multi-statement SQL script (used by setup_db.py)."""
    conn = get_connection()
    try:
        conn.executescript(script)
    except sqlite3.Error as exc:
        raise DatabaseError(f"Database error: {exc}") from exc


def database_exists() -> bool:
    """True when the database file exists and has the expected tables."""
    if not DB_PATH.exists():
        return False
    try:
        row = fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_systems'"
        )
        return row is not None
    except DatabaseError:
        return False


def table_counts() -> dict:
    """Row counts for the summary printed by setup_db.py."""
    counts: dict[str, int] = {}
    for table in ("users", "ai_systems", "risk_assessments", "ethical_assessments",
                  "approvals", "incidents", "audit_logs"):
        try:
            counts[table] = int(fetch_scalar(f"SELECT COUNT(*) FROM {table}", default=0) or 0)
        except DatabaseError:
            counts[table] = 0
    return counts


# ---------------------------------------------------------------------
# Friendly error translation
# ---------------------------------------------------------------------
def _friendly_integrity_error(exc: sqlite3.IntegrityError) -> str:
    """Turn raw SQLite constraint errors into something a user can act on."""
    text = str(exc)
    lowered = text.lower()

    if "foreign key" in lowered:
        return ("Operation rejected: the related record no longer exists "
                "(foreign key constraint).")
    if "unique" in lowered and "email" in lowered:
        return "That email address is already registered. Please use another one."
    if "check" in lowered and "role" in lowered:
        return ("Invalid role. Allowed roles are Administrator, Governance Officer, "
                "Developer, Auditor and Reporter.")
    if "check" in lowered and "deployment_status" in lowered:
        return "Invalid deployment status. Use Development, Testing, Production or Retired."
    if "check" in lowered and "governance_status" in lowered:
        return "Invalid governance status."
    if "check" in lowered and "risk_level" in lowered:
        return "Invalid risk level."
    if "check" in lowered and "severity" in lowered:
        return "Invalid severity. Use Low, Medium, High or Critical."
    if "check" in lowered and "status" in lowered:
        return "Invalid status value supplied for this record."
    if "not null" in lowered:
        return "A required field was left empty. Please complete all mandatory fields."
    return f"Data integrity error: {text}"


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    print(f"Database file : {DB_PATH}")
    print(f"Exists        : {database_exists()}")
    if database_exists():
        for table, count in table_counts().items():
            print(f"  {table:<22}: {count} row(s)")
