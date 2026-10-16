"""
audit_logger.py
=================================================================================
Immutable audit trail
Ethical Guideline and Governance Framework for AI Use in Nigerian Tech Startups
=================================================================================

WHY THIS MODULE EXISTS
----------------------
Accountability is one of the eight ethical requirements in this framework, and
an accountability claim that cannot be evidenced is worthless.  Every governance
action in the platform - registering a system, saving an assessment, approving,
returning, rejecting, reporting an incident, changing a user's role - is written
here with:

    * WHO did it          (user_id, resolved to a name)
    * WHAT they did       (action_type)
    * WHICH record        (entity_type + entity_id)
    * WHY / HOW           (details)
    * WHEN                (timestamp, UTC)

The log is append-only: this module deliberately exposes **no update and no
delete function**.  Nothing in the application can rewrite history, which is
what makes the trail usable as compliance evidence under a regulatory audit.

TIMESTAMPS
----------
Everything is stored in UTC (as SQLite's CURRENT_TIMESTAMP) and displayed in
West Africa Time (UTC+1) by the user interface, so an auditor reading a report
sees Nigerian local time while the stored data remains unambiguous.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

import db

# ---------------------------------------------------------------------
# Action vocabulary
# ---------------------------------------------------------------------
#: Using a fixed vocabulary means the audit trail can be filtered and counted
#: reliably, instead of turning into free text that nobody can report on.
ACTION_TYPES: list[str] = [
    "LOGIN",
    "LOGOUT",
    "LOGIN_FAILED",
    "SYSTEM_CREATED",
    "SYSTEM_UPDATED",
    "SYSTEM_SUBMITTED",
    "RISK_ASSESSED",
    "ETHICS_ASSESSED",
    "SYSTEM_APPROVED",
    "SYSTEM_RETURNED",
    "SYSTEM_REJECTED",
    "SYSTEM_DELETED",
    "INCIDENT_REPORTED",
    "INCIDENT_UPDATED",
    "INCIDENT_RESOLVED",
    "USER_CREATED",
    "USER_ACTIVATED",
    "USER_DEACTIVATED",
    "USER_ROLE_CHANGED",
    "PASSWORD_RESET",
    "REPORT_GENERATED",
    "SETTINGS_UPDATED",
    "DATA_SEEDED",
]

#: Colour used when the audit trail is rendered, so a reader can spot the
#: consequential actions (approvals, rejections) at a glance.
ACTION_META: dict[str, dict] = {
    "SYSTEM_APPROVED": {"icon": "✅", "colour": "#2e7d32"},
    "SYSTEM_RETURNED": {"icon": "↩️", "colour": "#ef6c00"},
    "SYSTEM_REJECTED": {"icon": "⛔", "colour": "#c62828"},
    "SYSTEM_CREATED": {"icon": "➕", "colour": "#0b2545"},
    "SYSTEM_SUBMITTED": {"icon": "📤", "colour": "#1b4079"},
    "SYSTEM_DELETED": {"icon": "🗑️", "colour": "#c62828"},
    "RISK_ASSESSED": {"icon": "📊", "colour": "#6a1b9a"},
    "ETHICS_ASSESSED": {"icon": "⚖️", "colour": "#00695c"},
    "INCIDENT_REPORTED": {"icon": "🚨", "colour": "#c62828"},
    "INCIDENT_UPDATED": {"icon": "🔧", "colour": "#ef6c00"},
    "INCIDENT_RESOLVED": {"icon": "🏁", "colour": "#2e7d32"},
    "USER_CREATED": {"icon": "👤", "colour": "#1b4079"},
    "USER_DEACTIVATED": {"icon": "🚫", "colour": "#616161"},
    "USER_ACTIVATED": {"icon": "✔️", "colour": "#2e7d32"},
    "USER_ROLE_CHANGED": {"icon": "🔄", "colour": "#ef6c00"},
    "LOGIN": {"icon": "🔑", "colour": "#546e7a"},
    "LOGOUT": {"icon": "🚪", "colour": "#546e7a"},
    "LOGIN_FAILED": {"icon": "⚠️", "colour": "#c62828"},
    "REPORT_GENERATED": {"icon": "📄", "colour": "#0b2545"},
}

DEFAULT_ACTION_META = {"icon": "•", "colour": "#546e7a"}


# ---------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------
def log_action(
    user_id: Optional[int],
    action_type: str,
    entity_type: str = "",
    entity_id: Optional[int] = None,
    details: str = "",
) -> int:
    """
    Append one entry to the audit trail.

    Parameters
    ----------
    user_id : int | None
        The signed-in user. ``None`` is used for system actions such as seeding.
    action_type : str
        One of :data:`ACTION_TYPES` (a new value is still accepted, so the
        platform cannot fail merely because a new action was introduced).
    entity_type : str
        'ai_system', 'incident', 'user', 'risk_assessment', 'ethics_assessment',
        'approval', 'report' or 'session'.
    entity_id : int | None
        Primary key of the affected record.
    details : str
        Human-readable explanation. Write it for an auditor who was not present.

    Returns
    -------
    int
        The new log_id, or 0 if logging failed.

    Notes
    -----
    Logging failures are swallowed deliberately.  An audit write must never
    break the governance action the officer is performing - a failed approval
    is far worse than a missing log line.  In production this would be paired
    with monitoring on the log table itself.
    """
    try:
        return int(db.execute_query(
            """
            INSERT INTO audit_logs (user_id, action_type, entity_type, entity_id, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, str(action_type)[:64], str(entity_type or "")[:32],
             entity_id, str(details or "")[:1000]),
        ) or 0)
    except Exception:  # noqa: BLE001 - audit logging must never break the action
        return 0


def log_with_actor(action_type: str, entity_type: str = "", entity_id: Optional[int] = None,
                   details: str = "") -> int:
    """
    Convenience wrapper that reads the signed-in user from the Streamlit session.

    Keeps the pages tidy: ``audit_logger.log_with_actor("SYSTEM_CREATED", "ai_system", id, "...")``
    instead of threading the user id through every call.
    """
    try:
        import auth

        return log_action(auth.current_user_id(), action_type, entity_type, entity_id, details)
    except Exception:  # noqa: BLE001
        return log_action(None, action_type, entity_type, entity_id, details)


# ---------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------
def fetch_logs(
    limit: int = 500,
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """
    Query the audit trail with optional filters.

    Returns rows joined to the users table so the reader sees names rather than
    numeric ids.  Ordered newest first.
    """
    clauses: list[str] = []
    params: list[Any] = []

    if user_id is not None:
        clauses.append("l.user_id = ?")
        params.append(int(user_id))
    if action_type:
        clauses.append("l.action_type = ?")
        params.append(action_type)
    if entity_type:
        clauses.append("l.entity_type = ?")
        params.append(entity_type)
    if entity_id is not None:
        clauses.append("l.entity_id = ?")
        params.append(int(entity_id))
    if date_from:
        clauses.append("date(l.timestamp) >= date(?)")
        params.append(date_from)
    if date_to:
        clauses.append("date(l.timestamp) <= date(?)")
        params.append(date_to)
    if search:
        clauses.append("(l.details LIKE ? OR l.action_type LIKE ? OR u.full_name LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))

    try:
        return db.fetch_all(
            f"""
            SELECT l.log_id, l.user_id, l.action_type, l.entity_type, l.entity_id,
                   l.details, l.timestamp,
                   COALESCE(u.full_name, 'System')  AS actor_name,
                   COALESCE(u.role, 'System')       AS actor_role,
                   COALESCE(u.email, '-')           AS actor_email
            FROM audit_logs l
            LEFT JOIN users u ON u.user_id = l.user_id
            {where}
            ORDER BY l.log_id DESC
            LIMIT ?
            """,
            tuple(params),
        )
    except db.DatabaseError:
        return []


def logs_for_entity(entity_type: str, entity_id: int, limit: int = 100) -> list[dict]:
    """Complete history of one record - used in the AI system detail view."""
    return fetch_logs(limit=limit, entity_type=entity_type, entity_id=entity_id)


def recent_activity(limit: int = 8) -> list[dict]:
    """The newest entries, for the dashboard activity feed."""
    return fetch_logs(limit=limit)


def audit_statistics() -> dict:
    """Counts used by the audit page summary cards."""
    try:
        total = int(db.fetch_scalar("SELECT COUNT(*) FROM audit_logs", default=0) or 0)
        actions = int(db.fetch_scalar(
            "SELECT COUNT(DISTINCT action_type) FROM audit_logs", default=0) or 0)
        actors = int(db.fetch_scalar(
            "SELECT COUNT(DISTINCT user_id) FROM audit_logs WHERE user_id IS NOT NULL",
            default=0) or 0)
        today = int(db.fetch_scalar(
            "SELECT COUNT(*) FROM audit_logs WHERE date(timestamp) = date('now')",
            default=0) or 0)
        return {"total": total, "action_types": actions, "actors": actors, "today": today}
    except db.DatabaseError:
        return {"total": 0, "action_types": 0, "actors": 0, "today": 0}


# ---------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------
def action_meta(action_type: str) -> dict:
    """Icon and colour for an action type."""
    return ACTION_META.get(action_type, DEFAULT_ACTION_META)


def format_timestamp(value: Any, with_time: bool = True) -> str:
    """
    Render a stored UTC timestamp in West Africa Time (UTC+1).

    The database stores UTC; Nigerian users read local time.
    """
    if not value:
        return "—"
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            stamp = datetime.strptime(text, fmt) + timedelta(hours=1)
            return stamp.strftime("%d %b %Y, %H:%M WAT" if with_time else "%d %b %Y")
        except ValueError:
            continue
    return text


def relative_time(value: Any) -> str:
    """'just now', '12 min ago', '3 hr ago', '2 day(s) ago'."""
    if not value:
        return ""
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            seconds = int((datetime.utcnow() - datetime.strptime(text, fmt)).total_seconds())
            if seconds < 60:
                return "just now"
            if seconds < 3600:
                return f"{seconds // 60} min ago"
            if seconds < 86400:
                return f"{seconds // 3600} hr ago"
            return f"{seconds // 86400} day(s) ago"
        except ValueError:
            continue
    return ""


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    print(f"{len(ACTION_TYPES)} action types defined")
    print("statistics:", audit_statistics())
