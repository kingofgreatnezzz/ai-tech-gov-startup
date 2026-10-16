"""
auth.py
=================================================================================
Authentication, roles and permissions
Ethical Guideline and Governance Framework for AI Use in Nigerian Tech Startups
=================================================================================

FIVE ROLES
----------
The framework implements separation of duties, which is the central control in
any governance system: the person who BUILDS an AI system must not be the person
who APPROVES it.

    Developer          registers AI systems and completes assessments
    GovernanceOfficer  reviews, approves, returns or rejects submissions
    Admin              full control, user management, high-risk approvals
    Auditor            read-only access to everything, including audit trails
    Reporter           any employee; may raise AI incidents

Permissions are declared as data (``ROLE_PERMISSIONS``) rather than scattered
through the code as ``if role == ...`` tests.  Every page asks
``has_permission("...")``, so a change to the policy happens in exactly one place
and can be audited.

SECURITY
--------
Passwords are hashed with PBKDF2-HMAC-SHA256 using a unique 16-byte random salt
and 120 000 iterations, and verified with a constant-time comparison.  The
plaintext password is never stored anywhere.
"""

from __future__ import annotations

import binascii
import hashlib
import hmac
import os
import re
from typing import Optional

import db

# ---------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------
ROLE_ADMIN = "Admin"
ROLE_GOVERNANCE = "GovernanceOfficer"
ROLE_DEVELOPER = "Developer"
ROLE_AUDITOR = "Auditor"
ROLE_REPORTER = "Reporter"

ROLES: list[str] = [ROLE_ADMIN, ROLE_GOVERNANCE, ROLE_DEVELOPER, ROLE_AUDITOR, ROLE_REPORTER]

ROLE_LABELS: dict[str, str] = {
    ROLE_ADMIN: "Administrator",
    ROLE_GOVERNANCE: "AI Governance Officer",
    ROLE_DEVELOPER: "Startup Developer / Project Owner",
    ROLE_AUDITOR: "Auditor (read-only)",
    ROLE_REPORTER: "Reporter (any employee)",
}

ROLE_ICONS: dict[str, str] = {
    ROLE_ADMIN: "🛡️",
    ROLE_GOVERNANCE: "⚖️",
    ROLE_DEVELOPER: "👨‍💻",
    ROLE_AUDITOR: "🔍",
    ROLE_REPORTER: "📣",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    ROLE_ADMIN: "Full access. Manages users, organisations, settings and audit logs, "
                "and can approve high-risk AI systems.",
    ROLE_GOVERNANCE: "Reviews AI registrations, risk and ethical assessments. Approves, "
                     "returns or rejects systems, and manages incidents.",
    ROLE_DEVELOPER: "Registers AI systems for their organisation and completes the risk "
                    "and ethical assessments. Cannot approve its own submissions.",
    ROLE_AUDITOR: "Read-only access to all governance records and audit trails. Can "
                  "generate compliance reports but cannot change anything.",
    ROLE_REPORTER: "Any employee. Can raise AI-related incidents and track only the "
                   "incidents they reported.",
}

# ---------------------------------------------------------------------
# Permissions (declared as data so the policy is auditable in one place)
# ---------------------------------------------------------------------
ALL_PERMISSIONS: set[str] = {
    "view_dashboard",
    "view_own_systems",
    "view_all_systems",
    "register_system",
    "edit_system",
    "delete_system",
    "assess_risk",
    "assess_ethics",
    "submit_system",
    "review_submissions",
    "decide_system",
    "approve_high_risk",
    "report_incident",
    "view_own_incidents",
    "view_all_incidents",
    "manage_incidents",
    "view_audit",
    "generate_reports",
    "manage_users",
    "manage_organisations",
    "view_settings",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_DEVELOPER: {
        "view_dashboard",
        "view_own_systems",
        "register_system",
        "edit_system",
        "delete_system",
        "assess_risk",
        "assess_ethics",
        "submit_system",
        "report_incident",
        "view_own_incidents",
        "generate_reports",
    },
    ROLE_GOVERNANCE: {
        "view_dashboard",
        "view_all_systems",
        "review_submissions",
        "decide_system",
        "report_incident",
        "view_all_incidents",
        "manage_incidents",
        "generate_reports",
    },
    ROLE_ADMIN: set(ALL_PERMISSIONS),
    ROLE_AUDITOR: {
        "view_dashboard",
        "view_all_systems",
        "view_all_incidents",
        "view_audit",
        "generate_reports",
        "report_incident",
    },
    ROLE_REPORTER: {
        "report_incident",
        "view_own_incidents",
    },
}

# Human-readable permission descriptions for the Readiness / settings page.
PERMISSION_LABELS: dict[str, str] = {
    "view_dashboard": "View the compliance dashboard",
    "view_own_systems": "View own AI systems",
    "view_all_systems": "View every AI system in the organisation",
    "register_system": "Register a new AI system",
    "edit_system": "Edit AI system details",
    "delete_system": "Delete an AI system from the register",
    "assess_risk": "Complete risk assessments",
    "assess_ethics": "Complete ethical impact assessments",
    "submit_system": "Submit a system for governance review",
    "review_submissions": "Review submitted AI systems",
    "decide_system": "Approve, return or reject AI systems",
    "approve_high_risk": "Approve High and Critical risk systems",
    "report_incident": "Report an AI-related incident",
    "view_own_incidents": "Track incidents you reported",
    "view_all_incidents": "View all incidents",
    "manage_incidents": "Update incident status and corrective actions",
    "view_audit": "View the audit trail",
    "generate_reports": "Generate governance reports",
    "manage_users": "Create and manage user accounts",
    "manage_organisations": "Manage organisations",
    "view_settings": "View and change system settings",
}

# ---------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------
PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 120_000
SALT_BYTES = 16

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """
    Hash a plain-text password.

    Format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``
    """
    if not password:
        raise ValueError("Password must not be empty.")

    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt, iterations)
    return "{}${}${}${}".format(
        PBKDF2_ALGORITHM, iterations,
        binascii.hexlify(salt).decode("ascii"),
        binascii.hexlify(digest).decode("ascii"),
    )


def check_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plain-text password against a stored hash.

    Uses a constant-time comparison and never raises on malformed input.
    """
    if not password or not stored_hash:
        return False

    try:
        parts = str(stored_hash).split("$")

        if len(parts) == 4 and parts[0] == PBKDF2_ALGORITHM:
            _, iterations_text, salt_hex, expected_hex = parts
            salt = binascii.unhexlify(salt_hex.encode("ascii"))
            digest = hashlib.pbkdf2_hmac(
                "sha256", str(password).encode("utf-8"), salt, int(iterations_text)
            )
            return hmac.compare_digest(binascii.hexlify(digest).decode("ascii"), expected_hex)

        # Legacy: sha256$salt$hash
        if len(parts) == 3 and parts[0] == "sha256":
            _, salt, expected = parts
            digest = hashlib.sha256((salt + str(password)).encode("utf-8")).hexdigest()
            return hmac.compare_digest(digest, expected)

        # Legacy: bare sha256
        if len(parts) == 1 and len(parts[0]) == 64:
            digest = hashlib.sha256(str(password).encode("utf-8")).hexdigest()
            return hmac.compare_digest(digest, parts[0])

    except (ValueError, TypeError, binascii.Error):
        return False

    return False


def password_strength(password: str) -> tuple[int, str]:
    """Simple strength meter: returns ``(score 0-4, label)``."""
    if not password:
        return 0, "Empty"
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Za-z]", password) and re.search(r"\d", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1
    labels = {0: "Very weak", 1: "Weak", 2: "Fair", 3: "Strong", 4: "Very strong"}
    return score, labels[score]


# ---------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------
def login_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by email and password.

    Returns a dictionary with ``user_id``, ``email``, ``full_name``, ``role``,
    ``organization`` and ``is_active`` - never the password hash.
    Returns ``None`` when the credentials are wrong, the account does not exist,
    or the account has been deactivated.
    """
    if not email or not password:
        return None

    try:
        record = db.fetch_one(
            """
            SELECT user_id, email, password_hash, full_name, role,
                   organization, is_active, created_at
            FROM users
            WHERE email = ? COLLATE NOCASE
            """,
            (str(email).strip(),),
        )
    except db.DatabaseError:
        return None

    if not record:
        return None
    if not check_password(password, record.get("password_hash", "")):
        return None
    if not int(record.get("is_active", 1)):
        return None

    return {
        "user_id": record["user_id"],
        "email": record["email"],
        "full_name": record["full_name"],
        "role": record["role"],
        "organization": record.get("organization"),
        "created_at": record.get("created_at"),
    }


def authenticate(email: str, password: str) -> tuple[bool, str, Optional[dict]]:
    """
    Wrapper around :func:`login_user` returning ``(success, message, user)``.

    Distinguishes a wrong password from a deactivated account, so a disabled
    user is told the truth rather than being left guessing.
    """
    email = (email or "").strip()
    if not email or not password:
        return False, "Please enter both your email address and password.", None

    try:
        record = db.fetch_one(
            "SELECT is_active FROM users WHERE email = ? COLLATE NOCASE", (email,)
        )
    except db.DatabaseError as exc:
        return False, f"Database unavailable: {exc}", None

    if not record:
        return False, "Invalid email address or password.", None

    if not int(record.get("is_active", 1)):
        return False, ("This account has been deactivated. Please contact the "
                       "platform administrator."), None

    user = login_user(email, password)
    if user is None:
        return False, "Invalid email address or password.", None

    return True, f"Welcome, {user['full_name']}.", user


# ---------------------------------------------------------------------
# Streamlit session helpers
# ---------------------------------------------------------------------
def get_current_user() -> Optional[dict]:
    """The signed-in user from ``st.session_state``, or None."""
    try:
        import streamlit as st

        user = st.session_state.get("user")
        if isinstance(user, dict) and user.get("email"):
            return user
        return None
    except Exception:  # pragma: no cover - outside Streamlit
        return None


def current_user_id() -> Optional[int]:
    user = get_current_user()
    return user.get("user_id") if user else None


def current_user_name() -> str:
    user = get_current_user()
    return user.get("full_name", "system") if user else "system"


def current_role() -> Optional[str]:
    user = get_current_user()
    return user.get("role") if user else None


def is_authenticated() -> bool:
    return get_current_user() is not None


def has_permission(permission: str) -> bool:
    """
    The single authorisation gate used by every page and every action button.

    Defaults to **deny** when the role is unknown, which is the safe failure
    mode for a governance system.
    """
    role = current_role()
    if not role:
        return False
    return permission in ROLE_PERMISSIONS.get(role, set())


def has_any_permission(*permissions: str) -> bool:
    return any(has_permission(p) for p in permissions)


def require_permission(permission: str, message: Optional[str] = None) -> bool:
    """
    Show a refusal message and return False when the permission is missing.

    Usage::

        if not require_permission("manage_users"):
            return
    """
    if has_permission(permission):
        return True
    try:
        import streamlit as st

        st.error(message or "🔒 Your role does not permit this action.")
    except Exception:  # pragma: no cover
        pass
    return False


def logout_user() -> None:
    """Clear the authentication state."""
    try:
        import streamlit as st

        st.session_state["user"] = None
        st.session_state.pop("page", None)
        st.session_state.pop("nav_radio", None)
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------
# User administration
# ---------------------------------------------------------------------
def create_user(email: str, password: str, full_name: str, role: str,
                organization: str = "") -> tuple[bool, str]:
    """Register a new account. Returns ``(success, message)``."""
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    organization = (organization or "").strip()

    if not EMAIL_PATTERN.match(email):
        return False, "Please enter a valid email address (e.g. name@startup.ng)."
    if not full_name or len(full_name) < 3:
        return False, "Please enter the person's full name."
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if role not in ROLES:
        return False, f"Invalid role. Choose one of: {', '.join(ROLE_LABELS[r] for r in ROLES)}."

    try:
        existing = db.fetch_one(
            "SELECT user_id FROM users WHERE email = ? COLLATE NOCASE", (email,)
        )
        if existing:
            return False, "That email address is already registered."

        user_id = db.execute_query(
            """
            INSERT INTO users (email, password_hash, full_name, role, organization, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (email, hash_password(password), full_name, role, organization),
        )
        return True, f"Account created for {full_name} ({ROLE_LABELS.get(role, role)})."
    except db.DatabaseError as exc:
        return False, str(exc)
    except ValueError as exc:
        return False, str(exc)


def set_user_active(user_id: int, active: bool) -> tuple[bool, str]:
    """
    Activate or deactivate an account.

    Accounts are never deleted: the audit trail references user IDs, and
    deleting a user would destroy the traceability that makes the framework
    auditable.
    """
    try:
        target = db.fetch_one(
            "SELECT full_name, role, is_active FROM users WHERE user_id = ?", (int(user_id),)
        )
        if not target:
            return False, "User not found."

        current = get_current_user()
        if current and int(current.get("user_id", -1)) == int(user_id) and not active:
            return False, "You cannot deactivate the account you are signed in with."

        if not active and target["role"] == ROLE_ADMIN:
            remaining = db.fetch_scalar(
                "SELECT COUNT(*) FROM users WHERE role = 'Admin' AND is_active = 1 "
                "AND user_id <> ?", (int(user_id),), default=0
            )
            if int(remaining) == 0:
                return False, ("Cannot deactivate the last active administrator - "
                               "the platform would become unmanageable.")

        db.execute_query("UPDATE users SET is_active = ? WHERE user_id = ?",
                         (1 if active else 0, int(user_id)))
        verb = "activated" if active else "deactivated"
        return True, f"{target['full_name']} has been {verb}."
    except db.DatabaseError as exc:
        return False, str(exc)


def change_role(user_id: int, role: str) -> tuple[bool, str]:
    """Change a user's role. Logged by the caller to the audit trail."""
    if role not in ROLES:
        return False, "Invalid role."
    try:
        target = db.fetch_one("SELECT full_name, role FROM users WHERE user_id = ?",
                              (int(user_id),))
        if not target:
            return False, "User not found."

        db.execute_query("UPDATE users SET role = ? WHERE user_id = ?", (role, int(user_id)))
        return True, (f"{target['full_name']} changed from "
                      f"{ROLE_LABELS.get(target['role'], target['role'])} to "
                      f"{ROLE_LABELS.get(role, role)}.")
    except db.DatabaseError as exc:
        return False, str(exc)


def reset_password(user_id: int, new_password: str) -> tuple[bool, str]:
    """Reset another user's password."""
    if not new_password or len(new_password) < 6:
        return False, "Password must be at least 6 characters long."
    try:
        affected = db.execute_query(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hash_password(new_password), int(user_id)),
        )
        if affected == 0:
            return False, "User not found."
        return True, "Password updated successfully."
    except db.DatabaseError as exc:
        return False, str(exc)


def list_users(active_only: bool = False) -> list[dict]:
    """All accounts with their system counts, for the User Management page."""
    try:
        where = "WHERE u.is_active = 1" if active_only else ""
        return db.fetch_all(
            f"""
            SELECT u.user_id, u.email, u.full_name, u.role, u.organization,
                   u.is_active, u.created_at,
                   (SELECT COUNT(*) FROM ai_systems s WHERE s.owner_id = u.user_id)
                       AS system_count
            FROM users u
            {where}
            ORDER BY u.role, u.full_name
            """
        )
    except db.DatabaseError:
        return []


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    sample = hash_password("admin123")
    print("hash      :", sample[:48], "...")
    print("verify ok :", check_password("admin123", sample))
    print("verify bad:", check_password("wrong", sample))
    print()
    for role in ROLES:
        granted = ROLE_PERMISSIONS[role]
        print(f"{role:<18} {len(granted):>2} permission(s)")
