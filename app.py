"""
app.py
=================================================================================
AI GOVERNANCE AND ETHICS PLATFORM
Ethical Guideline and Governance Framework for Artificial Intelligence Use in
Nigerian Tech Startups
---------------------------------------------------------------------------------
A role-based governance platform that lets a Nigerian tech startup register its
AI systems, assess their risk and ethical impact, route them through a formal
approval workflow, manage AI-related incidents, and keep an immutable audit
trail - all aligned with the Nigeria Data Protection Act 2023 and the National
AI Strategy.

FIVE ROLES, FIVE VIEWS
    Developer          registers systems and completes assessments
    GovernanceOfficer  reviews, approves, returns or rejects
    Admin              full control, users, high-risk approvals, audit logs
    Auditor            read-only, including the audit trail
    Reporter           any employee; reports AI incidents

The separation between Developer and GovernanceOfficer is deliberate: the person
who builds an AI system must never be the person who approves it.

RUN
    python setup_db.py
    streamlit run app.py

TECH STACK
    Python 3.10+ | Streamlit | SQLite | Pandas | Plotly   (100% local, no cloud)
=================================================================================
"""

from __future__ import annotations

import html as html_lib
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import audit_logger
import auth
import db
import reports
import risk_calculator as rc

# =================================================================================
# 1. PAGE CONFIGURATION  (must be the first Streamlit call)
# =================================================================================
st.set_page_config(
    page_title="AI Governance & Ethics Platform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =================================================================================
# 2. CONSTANTS
# =================================================================================
PLATFORM_NAME = "AI Governance and Ethics Platform"
PLATFORM_SHORT = "AI Governance"
FRAMEWORK_LINE = ("Ethical Guideline and Governance Framework for AI Use in "
                  "Nigerian Tech Startups")
REGULATORY_LINE = ("Aligned with the Nigeria Data Protection Act 2023, NITDA "
                   "guidelines and the National AI Strategy")
APP_VERSION = "1.0.0"

TECHNOLOGY_TYPES = [
    "Machine Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Generative AI",
    "Robotics",
    "Expert System",
    "Speech Recognition",
    "Recommendation System",
    "Data Analytics",
    "Other",
]

DATA_SOURCE_OPTIONS = [
    "Personal Data",
    "Financial Data",
    "Health Data",
    "Biometric Data",
    "Location Data",
    "Employee Data",
    "Public Data",
    "Third-Party Data",
    "Conversation Logs",
    "Transaction Metadata",
    "Credit History",
    "Alternative Data",
]

AFFECTED_USER_OPTIONS = [
    "Customers",
    "Employees",
    "Job Applicants",
    "Loan Applicants",
    "Students",
    "Patients",
    "General Public",
    "Minors / Children",
    "Vulnerable Groups",
    "Business Partners",
]

DEPLOYMENT_STATUSES = ["Development", "Testing", "Production", "Retired"]
GOVERNANCE_STATUSES = ["Draft", "Submitted", "UnderReview", "Approved",
                       "Returned", "Rejected"]

INCIDENT_TYPES = [
    "Bias/Discrimination",
    "Data Breach",
    "Incorrect Decision",
    "Security Incident",
    "System Failure",
    "Privacy Violation",
    "Lack of Transparency",
    "Other",
]

INCIDENT_SEVERITIES = ["Low", "Medium", "High", "Critical"]
INCIDENT_STATUSES = ["Reported", "UnderInvestigation", "Resolved", "Closed"]

STATUS_META = {
    "Draft":       {"colour": "#616161", "bg": "#f5f5f5", "icon": "📝"},
    "Submitted":   {"colour": "#1b4079", "bg": "#e8eef7", "icon": "📤"},
    "UnderReview": {"colour": "#ef6c00", "bg": "#fff3e0", "icon": "🔍"},
    "Approved":    {"colour": "#2e7d32", "bg": "#e8f5e9", "icon": "✅"},
    "Returned":    {"colour": "#f9a825", "bg": "#fffde7", "icon": "↩️"},
    "Rejected":    {"colour": "#c62828", "bg": "#ffebee", "icon": "⛔"},
}

SEVERITY_META = {
    "Low":      {"colour": "#2e7d32", "icon": "🟢"},
    "Medium":   {"colour": "#f9a825", "icon": "🟡"},
    "High":     {"colour": "#ef6c00", "icon": "🟠"},
    "Critical": {"colour": "#c62828", "icon": "🔴"},
}

INCIDENT_STATUS_META = {
    "Reported":           {"colour": "#1b4079", "icon": "📣"},
    "UnderInvestigation": {"colour": "#ef6c00", "icon": "🔍"},
    "Resolved":           {"colour": "#2e7d32", "icon": "🏁"},
    "Closed":             {"colour": "#616161", "icon": "🔒"},
}

DEPLOYMENT_META = {
    "Development": "#6a1b9a",
    "Testing": "#ef6c00",
    "Production": "#2e7d32",
    "Retired": "#616161",
}


# ---------------------------------------------------------------------------------
# Streamlit API compatibility shim
# ---------------------------------------------------------------------------------
def _supports_stretch_width() -> bool:
    """True when this Streamlit build accepts width='stretch'."""
    try:
        major, minor = str(st.__version__).split(".")[:2]
        return (int(major), int(minor)) >= (1, 49)
    except (ValueError, AttributeError, TypeError):
        return False


if _supports_stretch_width():
    FULL_WIDTH: dict = {"width": "stretch"}
else:  # pragma: no cover - older Streamlit builds
    FULL_WIDTH = {"use_container_width": True}


# =================================================================================
# 3. STYLING  (responsive: desktop dashboard AND mobile phone)
# =================================================================================
CUSTOM_CSS = """
<style>
    /* ---------- global ---------- */
    .block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1500px; }
    html, body, [class*="css"] {
        font-family: "Segoe UI", "Inter", Arial, sans-serif;
    }

    /* ---------- platform header ---------- */
    .ag-header {
        background: linear-gradient(120deg, #0b2545 0%, #13315c 55%, #1b4079 100%);
        border-radius: 12px; padding: 16px 24px; margin-bottom: 16px;
        border-left: 6px solid #12b886;
        box-shadow: 0 6px 18px rgba(11,37,69,.26);
    }
    .ag-header h1 { color: #ffffff; font-size: 22px; font-weight: 700; margin: 0; }
    .ag-header p { color: #b8c7dc; margin: 5px 0 0 0; font-size: 12.5px; letter-spacing: .3px; }
    .ag-header .badge {
        display: inline-block; background: #12b886; color: #04231a;
        font-size: 10.5px; font-weight: 800; padding: 2px 10px; border-radius: 10px;
        margin-left: 10px; letter-spacing: .7px; vertical-align: middle;
    }

    /* ---------- metric cards ---------- */
    div[data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #dde3ea; border-radius: 12px;
        padding: 13px 15px 11px 15px; box-shadow: 0 2px 8px rgba(16,39,57,.07);
        border-top: 4px solid #0b2545;
    }
    div[data-testid="stMetricLabel"] > div {
        font-size: 12.5px !important; color: #546e7a !important; font-weight: 600;
    }
    div[data-testid="stMetricValue"] { font-size: 26px !important; color: #102027; font-weight: 700; }

    /* ---------- section titles ---------- */
    .ag-section {
        font-size: 14.5px; font-weight: 700; color: #0b2545; margin: 8px 0 10px 0;
        padding-left: 10px; border-left: 4px solid #12b886; letter-spacing: .2px;
    }

    /* ---------- pills ---------- */
    .pill {
        display: inline-block; padding: 3px 11px; border-radius: 11px;
        font-size: 11px; font-weight: 700; letter-spacing: .35px; white-space: nowrap;
    }

    /* ---------- info cards ---------- */
    .ag-card {
        background: #ffffff; border: 1px solid #dde3ea; border-left: 5px solid #0b2545;
        border-radius: 10px; padding: 13px 16px; margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(16,39,57,.06);
    }
    .ag-card .title { font-size: 15.5px; font-weight: 700; color: #102027; }
    .ag-card .sub { font-size: 12.5px; color: #546e7a; margin-top: 3px; }
    .ag-card .body { font-size: 13px; color: #263238; margin-top: 8px; line-height: 1.6; }

    /* ---------- risk banner ---------- */
    .risk-banner {
        border-radius: 12px; padding: 16px 20px; margin: 6px 0 14px 0; color: #fff;
        box-shadow: 0 6px 20px rgba(0,0,0,.18);
    }
    .risk-banner .score { font-size: 34px; font-weight: 900; line-height: 1; }
    .risk-banner .band { font-size: 13px; font-weight: 800; letter-spacing: 2px; margin-top: 6px; }
    .risk-banner .formula { font-size: 11.5px; margin-top: 10px; opacity: .92;
                            font-family: Consolas, monospace; }

    /* ---------- login ---------- */
    .login-hero {
        background: linear-gradient(150deg, #0b2545 0%, #13315c 60%, #1b4079 100%);
        border-radius: 14px; padding: 30px 28px; color: #fff; height: 100%;
        box-shadow: 0 8px 26px rgba(11,37,69,.3);
    }
    .login-hero h2 { color: #fff; font-size: 20px; margin: 0 0 6px 0; }
    .login-hero .sub { color: #b8c7dc; font-size: 12.5px; letter-spacing: .4px; line-height: 1.6; }
    .login-hero ul { margin-top: 16px; padding-left: 18px; color: #dbe6f3;
                     font-size: 13px; line-height: 1.9; }

    /* ---------- misc ---------- */
    .small-note { font-size: 11.5px; color: #78909c; }
    .feed-item { border-left: 3px solid #cfd8dc; padding: 6px 0 6px 12px;
                 margin-bottom: 5px; font-size: 12.5px; color: #263238; }
    .feed-item .meta { font-size: 11px; color: #78909c; margin-top: 2px; }
    div[data-testid="stDataFrame"] { border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] {
        background: #f1f5f9; border-radius: 8px 8px 0 0; padding: 6px 13px;
        font-weight: 600; font-size: 13px;
    }
    .stTabs [aria-selected="true"] { background: #0b2545 !important; color: #fff !important; }
    footer, #MainMenu { visibility: hidden; }

    /* ============================================================
       RESPONSIVE - phones and small tablets
       Streamlit keeps columns side by side by default, which is
       unusable on a phone. These rules stack them.
       ============================================================ */
    @media (max-width: 820px) {
        .block-container { padding: 0.6rem 0.75rem 2rem 0.75rem !important; }
        div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: .4rem !important; }
        div[data-testid="column"] {
            flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important;
        }
        .ag-header { padding: 13px 15px; border-radius: 10px; }
        .ag-header h1 { font-size: 17px; }
        .ag-header p { font-size: 11.5px; }
        div[data-testid="stMetricValue"] { font-size: 22px !important; }
        .risk-banner .score { font-size: 27px; }
        .stButton > button, .stDownloadButton > button { width: 100% !important; }
        .stTabs [data-baseweb="tab"] { padding: 6px 9px; font-size: 12px; }
        .ag-card { padding: 11px 13px; }
    }
</style>
"""


# =================================================================================
# 4. GENERAL HELPERS
# =================================================================================
def platform_header(title: str, subtitle: str, badge: str = "") -> None:
    """The navy header shown at the top of every signed-in page."""
    badge_html = f'<span class="badge">{html_lib.escape(badge)}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="ag-header">
            <h1>{html_lib.escape(title)}{badge_html}</h1>
            <p>{html_lib.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(text: str) -> None:
    st.markdown(f'<div class="ag-section">{html_lib.escape(text)}</div>',
                unsafe_allow_html=True)


def status_pill(status: str) -> str:
    """Coloured pill for a governance status."""
    meta = STATUS_META.get(status, {"colour": "#616161", "bg": "#f5f5f5", "icon": "•"})
    return (f'<span class="pill" style="background:{meta["bg"]};color:{meta["colour"]};'
            f'border:1px solid {meta["colour"]}55;">{meta["icon"]} '
            f'{html_lib.escape(str(status)).upper()}</span>')


def risk_pill(score: Optional[float], level: Optional[str]) -> str:
    """Coloured pill for a risk score and band."""
    if score is None:
        return ('<span class="pill" style="background:#f5f5f5;color:#78909c;'
                'border:1px solid #cfd8dc;">NOT ASSESSED</span>')
    meta = rc.risk_level_meta(level or rc.determine_risk_level(score))
    return (f'<span class="pill" style="background:{meta["bg"]};color:{meta["colour"]};'
            f'border:1px solid {meta["colour"]}55;">{meta["icon"]} '
            f'{score:.1f} {html_lib.escape(str(level or ""))}</span>')


def severity_pill(severity: str) -> str:
    meta = SEVERITY_META.get(severity, {"colour": "#616161", "icon": "•"})
    return (f'<span class="pill" style="background:{meta["colour"]}1a;color:{meta["colour"]};'
            f'border:1px solid {meta["colour"]}55;">{meta["icon"]} '
            f'{html_lib.escape(str(severity)).upper()}</span>')


def incident_status_pill(status: str) -> str:
    meta = INCIDENT_STATUS_META.get(status, {"colour": "#616161", "icon": "•"})
    return (f'<span class="pill" style="background:{meta["colour"]}1a;color:{meta["colour"]};'
            f'border:1px solid {meta["colour"]}55;">{meta["icon"]} '
            f'{html_lib.escape(str(status)).upper()}</span>')


def deployment_pill(status: str) -> str:
    colour = DEPLOYMENT_META.get(status, "#616161")
    return (f'<span class="pill" style="background:{colour}1a;color:{colour};'
            f'border:1px solid {colour}55;">{html_lib.escape(str(status)).upper()}</span>')


def notify(kind: str, message: str) -> None:
    """Queue a toast that survives the st.rerun() after a write."""
    st.session_state.setdefault("pending_toasts", []).append((kind, message))


def flush_toasts() -> None:
    for kind, message in st.session_state.get("pending_toasts", []):
        try:
            icon = {"success": "✅", "error": "⛔", "warning": "⚠️"}.get(kind, "ℹ️")
            st.toast(message, icon=icon)
        except Exception:  # pragma: no cover
            st.success(message)
    st.session_state["pending_toasts"] = []


def goto(page: str) -> None:
    """Navigate to another page from inside a page body."""
    st.session_state["page"] = page
    st.session_state["_nav_request"] = page
    st.rerun()


def nav_callback(page: str, updates: Optional[dict] = None) -> None:
    """on_click callback: change page (and optional state) before the rerun."""
    if updates:
        for key, value in updates.items():
            st.session_state[key] = value
    st.session_state["page"] = page
    st.session_state["nav_radio"] = page


def safe_fetch_all(query: str, params=(), context: str = "records") -> list[dict]:
    try:
        return db.fetch_all(query, params)
    except db.DatabaseError as exc:
        st.error(f"Unable to load {context}. {exc}")
        return []


def safe_fetch_one(query: str, params=(), context: str = "the record"):
    try:
        return db.fetch_one(query, params)
    except db.DatabaseError as exc:
        st.error(f"Unable to load {context}. {exc}")
        return None


def plotly_chart(fig: go.Figure, height: int = 320) -> None:
    """
    Render a Plotly chart responsively.

    ``responsive: True`` lets the chart resize with the browser, which is what
    makes the analytics usable on a phone as well as on the projector.
    """
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=48, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#263238"),
        title_font=dict(size=14, color="#0b2545"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, x=0),
    )
    st.plotly_chart(
        fig, config={"responsive": True, "displayModeBar": False},
        **FULL_WIDTH,
    )


# =================================================================================
# 5. DATA ACCESS LAYER
# =================================================================================
def load_systems(owner_id: Optional[int] = None) -> list[dict]:
    """
    AI systems with their latest risk assessment attached.

    ``owner_id`` restricts the result to one owner - this is what enforces the
    Developer's "I can only see my own systems" rule.
    """
    where = "WHERE s.owner_id = ?" if owner_id is not None else ""
    params: tuple = (int(owner_id),) if owner_id is not None else ()
    return safe_fetch_all(
        f"""
        SELECT s.*, u.full_name AS owner_name, u.email AS owner_email,
               r.total_risk_score, r.risk_level,
               (SELECT COUNT(*) FROM ethical_assessments e WHERE e.system_id = s.system_id)
                   AS ethics_count,
               (SELECT COUNT(*) FROM incidents i WHERE i.system_id = s.system_id)
                   AS incident_count,
               (SELECT COUNT(*) FROM approvals a WHERE a.system_id = s.system_id)
                   AS approval_count
        FROM ai_systems s
        LEFT JOIN users u ON u.user_id = s.owner_id
        LEFT JOIN risk_assessments r
               ON r.assessment_id = (SELECT MAX(assessment_id) FROM risk_assessments
                                     WHERE system_id = s.system_id)
        {where}
        ORDER BY s.system_id DESC
        """,
        params,
        "AI systems",
    )


def load_system(system_id: int) -> Optional[dict]:
    return safe_fetch_one(
        """
        SELECT s.*, u.full_name AS owner_name, u.email AS owner_email,
               u.organization AS owner_organization
        FROM ai_systems s LEFT JOIN users u ON u.user_id = s.owner_id
        WHERE s.system_id = ?
        """,
        (int(system_id),),
        "the AI system",
    )


def load_risk(system_id: int) -> Optional[dict]:
    return safe_fetch_one(
        """
        SELECT r.*, u.full_name AS assessor_name
        FROM risk_assessments r LEFT JOIN users u ON u.user_id = r.assessed_by
        WHERE r.system_id = ? ORDER BY r.assessment_id DESC LIMIT 1
        """,
        (int(system_id),),
        "the risk assessment",
    )


def load_ethics(system_id: int) -> Optional[dict]:
    return safe_fetch_one(
        """
        SELECT e.*, u.full_name AS assessor_name
        FROM ethical_assessments e LEFT JOIN users u ON u.user_id = e.assessed_by
        WHERE e.system_id = ? ORDER BY e.ethics_id DESC LIMIT 1
        """,
        (int(system_id),),
        "the ethical assessment",
    )


def load_approvals(system_id: int) -> list[dict]:
    return safe_fetch_all(
        """
        SELECT a.*, u.full_name AS reviewer_name
        FROM approvals a LEFT JOIN users u ON u.user_id = a.reviewer_id
        WHERE a.system_id = ? ORDER BY a.approval_id DESC
        """,
        (int(system_id),),
        "approvals",
    )


def load_incidents(reported_by: Optional[int] = None,
                   system_ids: Optional[list[int]] = None) -> list[dict]:
    """
    Incidents, optionally scoped.

    Used to enforce the rule that a Reporter sees only their own reports, while
    a Developer sees incidents touching their own systems as well as anything
    they reported themselves.
    """
    clauses: list[str] = []
    params: list[Any] = []

    if reported_by is not None and system_ids:
        placeholders = ",".join("?" for _ in system_ids)
        clauses.append(f"(i.reported_by = ? OR i.system_id IN ({placeholders}))")
        params.append(int(reported_by))
        params.extend(int(s) for s in system_ids)
    elif reported_by is not None:
        clauses.append("i.reported_by = ?")
        params.append(int(reported_by))
    elif system_ids:
        placeholders = ",".join("?" for _ in system_ids)
        clauses.append(f"i.system_id IN ({placeholders})")
        params.extend(int(s) for s in system_ids)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return safe_fetch_all(
        f"""
        SELECT i.*, s.system_name, s.technology_type,
               u.full_name AS reporter_name, u.email AS reporter_email
        FROM incidents i
        LEFT JOIN ai_systems s ON s.system_id = i.system_id
        LEFT JOIN users u ON u.user_id = i.reported_by
        {where}
        ORDER BY i.incident_id DESC
        """,
        tuple(params),
        "incidents",
    )


def scope_systems_for_user() -> Optional[list[dict]]:
    """
    Return the systems the signed-in user may see, or None to mean "all".

    * Admin, Governance Officer and Auditor see every system.
    * Developer sees only the systems they own.
    * Reporter sees none (they only file incidents).
    """
    if auth.has_permission("view_all_systems"):
        return None
    if auth.has_permission("view_own_systems"):
        return load_systems(owner_id=auth.current_user_id())
    return []


def visible_system_ids() -> Optional[list[int]]:
    """IDs of the systems the signed-in user may see, or None for all."""
    systems = scope_systems_for_user()
    if systems is None:
        return None
    return [int(s["system_id"]) for s in systems]


def dashboard_metrics() -> dict:
    """Headline numbers for the compliance dashboard."""
    systems = load_systems()
    incidents = load_incidents()

    by_level = {level: 0 for level in rc.RISK_LEVELS}
    not_assessed = 0
    for system in systems:
        if system.get("risk_level"):
            by_level[system["risk_level"]] = by_level.get(system["risk_level"], 0) + 1
        else:
            not_assessed += 1

    total = len(systems)
    approved = len([s for s in systems if s["governance_status"] == "Approved"])
    pending = len([s for s in systems
                   if s["governance_status"] in ("Submitted", "UnderReview")])

    return {
        "total_systems": total,
        "by_level": by_level,
        "not_assessed": not_assessed,
        "approved": approved,
        "pending": pending,
        "returned": len([s for s in systems if s["governance_status"] == "Returned"]),
        "rejected": len([s for s in systems if s["governance_status"] == "Rejected"]),
        "compliance_rate": (approved / total * 100.0) if total else 0.0,
        "open_incidents": len([i for i in incidents
                               if i["status"] in ("Reported", "UnderInvestigation")]),
        "total_incidents": len(incidents),
        "high_risk": by_level.get("High", 0) + by_level.get("Critical", 0),
    }


# =================================================================================
# 6. LOGIN PAGE
# =================================================================================
def render_login() -> None:
    """Split-screen sign-in page that also explains the five roles."""
    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.markdown(
            f"""
            <div class="login-hero">
                <div style="font-size:38px;line-height:1">⚖️</div>
                <h2>{html_lib.escape(PLATFORM_NAME)}</h2>
                <div class="sub">{html_lib.escape(FRAMEWORK_LINE)}</div>
                <div class="sub" style="margin-top:10px;color:#8fa8c4">
                    {html_lib.escape(REGULATORY_LINE)}
                </div>
                <ul>
                    <li>Register and classify every AI system in the organisation</li>
                    <li>Weighted risk scoring across six dimensions</li>
                    <li>Ethical impact assessment against eight requirements</li>
                    <li>Formal approval workflow with separation of duties</li>
                    <li>Incident management and an immutable audit trail</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        with st.expander("🔑 Demonstration accounts (all five roles)"):
            st.markdown(
                """
| Email | Password | Role |
|---|---|---|
| `admin@startup.ng` | `admin123` | Administrator |
| `governance@startup.ng` | `gov123` | AI Governance Officer |
| `dev@startup.ng` | `dev123` | Startup Developer |
| `auditor@startup.ng` | `audit123` | Auditor (read-only) |
| `reporter@startup.ng` | `rep123` | Reporter (any employee) |
                """
            )
            st.caption(
                "The organisation in the demonstration data is **PayLink Nigeria Ltd**, "
                "a fictional Nigerian fintech startup operating three AI systems."
            )

    with right:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("### Sign in")
        st.caption("Authorised users of the AI governance platform.")

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email address", placeholder="you@startup.ng",
                                  autocomplete="username")
            password = st.text_input("Password", type="password", placeholder="••••••••",
                                     autocomplete="current-password")
            submitted = st.form_submit_button("Sign in", type="primary", **FULL_WIDTH)

        if submitted:
            success, message, user = auth.authenticate(email, password)
            if success and user:
                st.session_state["user"] = user
                st.session_state.pop("page", None)
                st.session_state.pop("nav_radio", None)
                audit_logger.log_action(
                    user["user_id"], "LOGIN", "session", None,
                    f"{user['full_name']} signed in as "
                    f"{auth.ROLE_LABELS.get(user['role'], user['role'])}.",
                )
                st.rerun()
            else:
                audit_logger.log_action(None, "LOGIN_FAILED", "session", None,
                                        f"Failed sign-in attempt for '{email}'.")
                st.error(f"⛔ {message}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.expander("ℹ️ About this platform"):
            st.markdown(
                f"""
                **{PLATFORM_NAME}** — version {APP_VERSION}

                A local, offline governance platform. There is no cloud service, no
                paid API and no external dependency: all data is held in a single
                SQLite database file on this machine.

                The platform implements **separation of duties**: the developer who
                registers an AI system cannot approve it, and the governance officer
                who approves it cannot edit the developer's assessments.
                """
            )

    st.markdown(
        f"<div class='small-note' style='text-align:center;margin-top:24px'>"
        f"{html_lib.escape(REGULATORY_LINE)} · v{APP_VERSION}</div>",
        unsafe_allow_html=True,
    )


# =================================================================================
# 7. NAVIGATION
# =================================================================================
#: page label -> (page function, permissions that make it visible)
#:
#: The mapping is declared as DATA rather than as if/else tests scattered through
#: the code. A page becomes visible when the signed-in role holds ANY of the
#: listed permissions, which is what makes the five roles behave differently
#: without duplicating the navigation logic five times.
#:
#: NOTE: the registry itself is populated at the very bottom of this file, once
#: every page function has been defined.
PAGE_REGISTRY: dict[str, tuple[Callable[[], None], tuple[str, ...]]] = {}


def visible_pages() -> list[str]:
    """The pages this role may open, in registry order."""
    return [page for page, (_fn, permissions) in PAGE_REGISTRY.items()
            if auth.has_any_permission(*permissions)]


def render_sidebar() -> str:
    """Role-aware sidebar navigation. Returns the selected page."""
    user = auth.get_current_user() or {}
    role = user.get("role", "")
    pages = visible_pages()

    with st.sidebar:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#0b2545,#1b4079);border-radius:10px;
                        padding:13px 15px;color:#fff;margin-bottom:11px">
                <div style="font-size:19px">⚖️</div>
                <div style="font-weight:700;font-size:14px;line-height:1.25;margin-top:4px">
                    AI Governance Platform</div>
                <div style="font-size:10.5px;color:#b8c7dc;margin-top:3px">
                    Nigerian Tech Startups</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        role_icon = auth.ROLE_ICONS.get(role, "👤")
        st.markdown(
            f"""
            <div style="border:1px solid #dde3ea;border-radius:10px;padding:10px 12px;
                        margin-bottom:11px;background:#ffffff">
                <div style="font-size:13px;font-weight:700;color:#102027">
                    {role_icon} {html_lib.escape(str(user.get('full_name', '')))}</div>
                <div style="font-size:11px;color:#78909c;margin-top:2px">
                    {html_lib.escape(str(user.get('organization') or ''))}</div>
                <div style="margin-top:6px">
                    <span style="background:#0b2545;color:#fff;font-size:10px;
                                 font-weight:700;padding:2px 9px;border-radius:9px;
                                 letter-spacing:.4px">
                        {html_lib.escape(auth.ROLE_LABELS.get(role, role).upper())}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Apply a pending programmatic navigation before the radio is created.
        pending = st.session_state.pop("_nav_request", None)
        if pending and pending in pages:
            st.session_state.pop("nav_radio", None)
            st.session_state["page"] = pending

        if st.session_state.get("page") not in pages:
            st.session_state["page"] = pages[0]
            st.session_state.pop("nav_radio", None)

        st.caption("NAVIGATION")
        selected = st.radio("Navigation", pages,
                            index=pages.index(st.session_state["page"]),
                            label_visibility="collapsed", key="nav_radio")
        st.session_state["page"] = selected

        st.divider()

        # ---- role-specific context in the sidebar ------------------------
        try:
            metrics = dashboard_metrics()
            if auth.has_permission("view_dashboard"):
                st.markdown(
                    f"""
                    <div style="font-size:12px;color:#37474f;line-height:1.9">
                        <span style="color:#0b2545;font-weight:700">● {metrics['total_systems']}</span>
                        AI system(s) registered<br>
                        <span style="color:#ef6c00;font-weight:700">● {metrics['pending']}</span>
                        awaiting review<br>
                        <span style="color:#c62828;font-weight:700">● {metrics['open_incidents']}</span>
                        open incident(s)
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception:  # pragma: no cover
            pass

        st.divider()
        if st.button("🚪 Sign out", **FULL_WIDTH):
            audit_logger.log_action(auth.current_user_id(), "LOGOUT", "session", None,
                                    f"{user.get('full_name', '')} signed out.")
            auth.logout_user()
            st.rerun()

        st.markdown(
            f"<div style='font-size:10px;color:#90a4ae;margin-top:10px'>"
            f"v{APP_VERSION} · SQLite + Streamlit + Plotly · offline</div>",
            unsafe_allow_html=True,
        )

    return selected


# =================================================================================
# 8. PAGE - COMPLIANCE DASHBOARD
# =================================================================================
def page_dashboard() -> None:
    """Role-aware landing page. The compliance dashboard for governance roles."""
    role = auth.current_role()

    if not auth.has_permission("view_dashboard"):
        _dashboard_personal(role)
        return

    platform_header(
        "Compliance Dashboard",
        f"{FRAMEWORK_LINE} · {REGULATORY_LINE}",
        badge="LIVE GOVERNANCE VIEW",
    )

    metrics = dashboard_metrics()

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        st.metric("AI Systems Registered", metrics["total_systems"],
                  help="All AI systems on the governance register.")
    with c2:
        st.metric("Approved", metrics["approved"],
                  delta=f"{metrics['compliance_rate']:.0f}% compliance rate",
                  delta_color="off")
    with c3:
        st.metric("Pending Review", metrics["pending"],
                  help="Systems submitted or under review by the Governance Officer.")
    with c4:
        st.metric("Open Incidents", metrics["open_incidents"],
                  delta=f"{metrics['total_incidents']} total", delta_color="off")
    with c5:
        st.metric("High / Critical Risk", metrics["high_risk"],
                  help="Systems in the High or Critical risk band.")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ---- risk band strip --------------------------------------------------
    cols = st.columns(5, gap="small")
    band_info = [
        ("Low", metrics["by_level"].get("Low", 0)),
        ("Moderate", metrics["by_level"].get("Moderate", 0)),
        ("High", metrics["by_level"].get("High", 0)),
        ("Critical", metrics["by_level"].get("Critical", 0)),
    ]
    for index, (level, count) in enumerate(band_info):
        meta = rc.risk_level_meta(level)
        with cols[index]:
            st.markdown(
                f"""
                <div style="border:1px solid {meta['colour']}44;background:{meta['bg']};
                            border-radius:10px;padding:10px 13px;text-align:center">
                    <div style="font-size:11px;font-weight:800;color:{meta['colour']};
                                letter-spacing:1px">{meta['icon']} {level.upper()}</div>
                    <div style="font-size:23px;font-weight:800;color:{meta['colour']};
                                margin-top:3px">{count}</div>
                    <div style="font-size:10.5px;color:#78909c">{meta['range']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with cols[4]:
        st.markdown(
            f"""
            <div style="border:1px solid #cfd8dc;background:#fafafa;border-radius:10px;
                        padding:10px 13px;text-align:center">
                <div style="font-size:11px;font-weight:800;color:#78909c;letter-spacing:1px">
                    ⚪ NOT ASSESSED</div>
                <div style="font-size:23px;font-weight:800;color:#546e7a;margin-top:3px">
                    {metrics['not_assessed']}</div>
                <div style="font-size:10.5px;color:#90a4ae">awaiting assessment</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _dashboard_charts()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    _dashboard_register_table()


def _dashboard_charts() -> None:
    """The four interactive Plotly charts."""
    systems = load_systems()
    incidents = load_incidents()

    row1_left, row1_right = st.columns(2, gap="medium")

    # ---- 1. pie: AI systems by risk level ---------------------------------
    with row1_left:
        section("🥧 AI Systems by Risk Level")
        counts = {level: 0 for level in rc.RISK_LEVELS}
        for system in systems:
            if system.get("risk_level"):
                counts[system["risk_level"]] = counts.get(system["risk_level"], 0) + 1
        if systems and any(counts.values()):
            frame = pd.DataFrame(
                {"Risk level": list(counts.keys()), "Systems": list(counts.values())}
            )
            fig = px.pie(
                frame, names="Risk level", values="Systems", hole=0.45,
                color="Risk level",
                color_discrete_map={level: rc.risk_level_meta(level)["colour"]
                                    for level in rc.RISK_LEVELS},
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            plotly_chart(fig, height=310)
        else:
            st.info("No risk assessments have been completed yet.")

    # ---- 2. bar: incidents by type ----------------------------------------
    with row1_right:
        section("📊 Incidents by Type")
        if incidents:
            frame = (pd.Series([i["incident_type"] or "Unclassified" for i in incidents],
                               name="Incidents")
                     .value_counts().rename_axis("Incident type").reset_index())
            fig = px.bar(frame, x="Incidents", y="Incident type", orientation="h",
                         color="Incidents",
                         color_continuous_scale=["#ffe0b2", "#c62828"])
            fig.update_layout(coloraxis_showscale=False, yaxis_title="")
            fig.update_traces(marker_line_width=0)
            plotly_chart(fig, height=310)
        else:
            st.info("No incidents have been reported.")

    row2_left, row2_right = st.columns(2, gap="medium")

    # ---- 3. line: AI registrations over time ------------------------------
    with row2_left:
        section("📈 AI Registrations Over Time")
        if systems:
            frame = pd.DataFrame(
                {"Date": [str(s["created_at"])[:10] for s in systems]}
            ).sort_values("Date")
            frame["Cumulative systems"] = range(1, len(frame) + 1)
            fig = px.line(frame, x="Date", y="Cumulative systems", markers=True)
            fig.update_traces(line=dict(width=3, color="#0b2545"),
                              marker=dict(size=9, color="#12b886"))
            fig.update_layout(yaxis_title="Cumulative AI systems", xaxis_title="")
            plotly_chart(fig, height=310)
        else:
            st.info("No AI systems registered yet.")

    # ---- 4. stacked bar: systems by deployment status ---------------------
    with row2_right:
        section("🚀 Systems by Deployment Status")
        if systems:
            frame = pd.DataFrame(
                [{"Status": s["governance_status"], "Deployment": s["deployment_status"]}
                 for s in systems]
            )
            grouped = (frame.groupby(["Deployment", "Status"]).size()
                       .reset_index(name="Systems"))
            fig = px.bar(
                grouped, x="Deployment", y="Systems", color="Status", barmode="stack",
                color_discrete_map={s: STATUS_META.get(s, {}).get("colour", "#616161")
                                    for s in GOVERNANCE_STATUSES},
                category_orders={"Deployment": DEPLOYMENT_STATUSES},
            )
            fig.update_layout(xaxis_title="", legend_title="")
            plotly_chart(fig, height=310)
        else:
            st.info("No AI systems registered yet.")


def _dashboard_register_table() -> None:
    """Filterable AI register with status badges."""
    section("🗂️ AI System Register")
    systems = load_systems()

    f1, f2, f3 = st.columns([1, 1, 2], gap="small")
    with f1:
        status_filter = st.multiselect("Governance status", GOVERNANCE_STATUSES, default=[])
    with f2:
        level_filter = st.multiselect("Risk level",
                                      rc.RISK_LEVELS + ["Not assessed"], default=[])
    with f3:
        search = st.text_input("Search", placeholder="system name, owner or technology")

    filtered = systems
    if status_filter:
        filtered = [s for s in filtered if s["governance_status"] in status_filter]
    if level_filter:
        filtered = [
            s for s in filtered
            if (s.get("risk_level") or "Not assessed") in level_filter
        ]
    if search.strip():
        needle = search.strip().lower()
        filtered = [
            s for s in filtered
            if needle in str(s["system_name"]).lower()
            or needle in str(s.get("owner_name") or "").lower()
            or needle in str(s.get("technology_type") or "").lower()
        ]

    if not filtered:
        st.info("No AI systems match the current filters.")
        return

    frame = pd.DataFrame([
        {
            "Ref": f"AIS-{int(s['system_id']):04d}",
            "AI System": s["system_name"],
            "Technology": s.get("technology_type") or "—",
            "Owner": s.get("owner_name") or "—",
            "Deployment": s.get("deployment_status") or "—",
            "Governance": s["governance_status"],
            "Risk Score": (round(float(s["total_risk_score"]), 1)
                           if s.get("total_risk_score") is not None else None),
            "Risk Level": s.get("risk_level") or "Not assessed",
            "Incidents": int(s.get("incident_count") or 0),
        }
        for s in filtered
    ])
    st.dataframe(frame, hide_index=True, height=300, **FULL_WIDTH)

    csv = frame.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export register as CSV", data=csv,
                       file_name="ai_system_register.csv", mime="text/csv")


def _dashboard_personal(role: str) -> None:
    """Landing page for roles without the portfolio dashboard (Developer, Reporter)."""
    user = auth.get_current_user() or {}

    if auth.has_permission("view_own_systems"):
        platform_header("My AI Systems",
                        f"{user.get('organization', '')} · developer workspace",
                        badge="DEVELOPER")
        systems = load_systems(owner_id=auth.current_user_id())

        if not systems:
            st.info("You have not registered any AI systems yet. "
                    "Use ➕ Register AI System to add your first one.")
            st.button("➕ Register an AI system", type="primary",
                      on_click=nav_callback, args=("➕ Register AI System",))
            return

        assessed = len([s for s in systems if s.get("total_risk_score") is not None])
        ethical = len([s for s in systems if s.get("ethics_count")])
        approved = len([s for s in systems if s["governance_status"] == "Approved"])
        action_needed = [
            s for s in systems
            if s.get("total_risk_score") is None
            or not s.get("ethics_count")
            or s["governance_status"] in ("Returned", "Draft")
        ]

        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric("My AI Systems", len(systems))
        c2.metric("Risk Assessed", f"{assessed}/{len(systems)}")
        c3.metric("Ethics Assessed", f"{ethical}/{len(systems)}")
        c4.metric("Approved", approved)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if action_needed:
            section("⚠️ Action required on your systems")
            for system in action_needed:
                gaps = []
                if system.get("total_risk_score") is None:
                    gaps.append("risk assessment outstanding")
                if not system.get("ethics_count"):
                    gaps.append("ethical assessment outstanding")
                if system["governance_status"] == "Returned":
                    gaps.append("returned by the Governance Officer - changes required")
                elif system["governance_status"] == "Draft":
                    gaps.append("not yet submitted for review")
                gaps_text = " · ".join(gaps)
                st.markdown(
                    f"""
                    <div class="ag-card" style="border-left-color:#ef6c00">
                        <div class="title">{html_lib.escape(system['system_name'])}
                            {status_pill(system['governance_status'])}</div>
                        <div class="sub">AIS-{int(system['system_id']):04d} ·
                            {html_lib.escape(gaps_text)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ All of your AI systems have complete assessments.")

        section("My AI systems")
        frame = pd.DataFrame([
            {
                "Ref": f"AIS-{int(s['system_id']):04d}",
                "System": s["system_name"],
                "Deployment": s.get("deployment_status"),
                "Governance": s["governance_status"],
                "Risk Score": (round(float(s["total_risk_score"]), 1)
                               if s.get("total_risk_score") is not None else None),
                "Risk Level": s.get("risk_level") or "Not assessed",
            }
            for s in systems
        ])
        st.dataframe(frame, hide_index=True, **FULL_WIDTH)
        return

    # ---- Reporter ---------------------------------------------------------
    platform_header("My Incident Reports",
                    "Report an AI-related concern and track how it is handled",
                    badge="REPORTER")
    incidents = load_incidents(reported_by=auth.current_user_id())

    c1, c2, c3 = st.columns(3, gap="small")
    c1.metric("Reports I have filed", len(incidents))
    c2.metric("Still open", len([i for i in incidents
                                 if i["status"] in ("Reported", "UnderInvestigation")]))
    c3.metric("Resolved or closed", len([i for i in incidents
                                         if i["status"] in ("Resolved", "Closed")]))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.info("Use the **🚨 Incidents** page in the sidebar to report a new AI-related "
            "incident. You will only ever see the reports you filed yourself.")

    if incidents:
        section("My reports")
        for incident in incidents:
            st.markdown(
                f"""
                <div class="ag-card">
                    <div class="title">INC-{int(incident['incident_id']):04d} ·
                        {html_lib.escape(str(incident['incident_type']))}
                        {severity_pill(incident['severity'])}
                        {incident_status_pill(incident['status'])}</div>
                    <div class="sub">{html_lib.escape(str(incident.get('system_name') or '—'))} ·
                        reported {html_lib.escape(audit_logger.format_timestamp(incident['reported_at']))}</div>
                    <div class="body">{html_lib.escape(str(incident['description'])[:240])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("You have not filed any incident reports yet.")


# =================================================================================
# 9. PAGE - AI INVENTORY
# =================================================================================
def page_inventory() -> None:
    platform_header(
        "AI System Inventory",
        "Every AI system on the governance register, with its current status",
        badge="REGISTER",
    )

    owner_scope = None if auth.has_permission("view_all_systems") else auth.current_user_id()
    systems = load_systems(owner_id=owner_scope)

    if not systems:
        st.info("No AI systems are registered yet.")
        if auth.has_permission("register_system"):
            st.button("➕ Register the first AI system", type="primary",
                      on_click=nav_callback, args=("➕ Register AI System",))
        return

    search_col, tech_col, status_col = st.columns([2, 1, 1], gap="small")
    with search_col:
        search = st.text_input("🔍 Search", placeholder="system name, purpose or owner")
    with tech_col:
        tech_filter = st.multiselect("Technology", sorted(
            {s.get("technology_type") or "—" for s in systems}), default=[])
    with status_col:
        status_filter = st.multiselect("Status", GOVERNANCE_STATUSES, default=[])

    filtered = systems
    if search.strip():
        needle = search.strip().lower()
        filtered = [
            s for s in filtered
            if needle in str(s["system_name"]).lower()
            or needle in str(s.get("purpose") or "").lower()
            or needle in str(s.get("owner_name") or "").lower()
        ]
    if tech_filter:
        filtered = [s for s in filtered if (s.get("technology_type") or "—") in tech_filter]
    if status_filter:
        filtered = [s for s in filtered if s["governance_status"] in status_filter]

    section(f"📋 {len(filtered)} AI system(s)")

    # ---- summary cards (mobile friendly: they stack) ----------------------
    for system in filtered:
        risk_html = risk_pill(system.get("total_risk_score"), system.get("risk_level"))
        st.markdown(
            f"""
            <div class="ag-card">
                <div class="title">🗂️ {html_lib.escape(system['system_name'])}
                    &nbsp;{status_pill(system['governance_status'])}</div>
                <div class="sub">
                    AIS-{int(system['system_id']):04d} ·
                    {html_lib.escape(str(system.get('technology_type') or '—'))} ·
                    {deployment_pill(system.get('deployment_status') or '—')} ·
                    owner {html_lib.escape(str(system.get('owner_name') or '—'))}
                </div>
                <div class="body">
                    {html_lib.escape(str(system.get('purpose') or 'No purpose recorded.')[:260])}
                </div>
                <div style="margin-top:8px">
                    {risk_html}
                    &nbsp;<span class="pill" style="background:#e8eef7;color:#1b4079;">
                        🚨 {int(system.get('incident_count') or 0)} incident(s)</span>
                    &nbsp;<span class="pill" style="background:#e8f5e9;color:#2e7d32;">
                        ✅ {int(system.get('approval_count') or 0)} decision(s)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- open a full record ----------------------------------------------
    section("🔎 Open a full system record")
    options = {f"AIS-{int(s['system_id']):04d} · {s['system_name']}": int(s["system_id"])
               for s in filtered}
    picked = st.selectbox("Select an AI system", list(options.keys()))
    if picked:
        _render_system_detail(options[picked])


def _render_system_detail(system_id: int) -> None:
    """The complete governance record for one AI system."""
    system = load_system(system_id)
    if not system:
        st.error("That AI system could not be loaded.")
        return

    risk = load_risk(system_id)
    ethics = load_ethics(system_id)
    approvals = load_approvals(system_id)
    incidents = safe_fetch_all(
        "SELECT * FROM incidents WHERE system_id = ? ORDER BY incident_id DESC",
        (int(system_id),), "incidents",
    )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown(f"#### 🗂️ {system['system_name']}")

    info_left, info_right = st.columns(2, gap="medium")
    with info_left:
        st.markdown(
            f"""
            <div class="ag-card">
                <div class="sub">
                    <b>Reference:</b> AIS-{int(system['system_id']):04d}<br>
                    <b>Technology:</b> {html_lib.escape(str(system.get('technology_type') or '—'))}<br>
                    <b>Data sources:</b> {html_lib.escape(str(system.get('data_sources') or '—'))}<br>
                    <b>Affected parties:</b> {html_lib.escape(str(system.get('affected_users') or '—'))}<br>
                    <b>Owner:</b> {html_lib.escape(str(system.get('owner_name') or '—'))}
                    ({html_lib.escape(str(system.get('owner_email') or '—'))})<br>
                    <b>Registered:</b> {html_lib.escape(audit_logger.format_timestamp(system['created_at']))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with info_right:
        st.markdown(
            f"""
            <div class="ag-card">
                <div class="sub">
                    <b>Governance status:</b> {status_pill(system['governance_status'])}<br>
                    <b>Deployment status:</b> {deployment_pill(system.get('deployment_status') or '—')}<br>
                    <b>Risk rating:</b> {risk_pill(risk['total_risk_score'] if risk else None,
                                                    risk['risk_level'] if risk else None)}<br>
                    <b>Ethical recommendation:</b>
                    {'<span class="pill" style="background:#e8f5e9;color:#2e7d32;">'
                     + html_lib.escape(str(ethics['recommendation'])) + '</span>'
                     if ethics else '<span class="pill" style="background:#f5f5f5;color:#78909c;">NOT ASSESSED</span>'}<br>
                    <b>Last updated:</b> {html_lib.escape(audit_logger.format_timestamp(system.get('updated_at')))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("📄 Purpose of the system", expanded=True):
        st.write(system.get("purpose") or "No purpose recorded.")

    tabs = st.tabs(["📊 Risk assessment", "⚖️ Ethical assessment",
                    "✅ Decision history", "🚨 Incidents", "🕵️ Audit trail"])

    with tabs[0]:
        if risk:
            _render_risk_detail(risk)
        else:
            st.info("No risk assessment has been completed for this system.")

    with tabs[1]:
        if ethics:
            _render_ethics_detail(ethics)
        else:
            st.info("No ethical impact assessment has been completed for this system.")

    with tabs[2]:
        if approvals:
            for approval in approvals:
                st.markdown(
                    f"""
                    <div class="ag-card">
                        <div class="title">{status_pill(approval['decision'])}</div>
                        <div class="sub">{html_lib.escape(str(approval.get('reviewer_name') or '—'))} ·
                            {html_lib.escape(audit_logger.format_timestamp(approval['decision_date']))}</div>
                        <div class="body">{html_lib.escape(str(approval.get('comments') or ''))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No governance decision has been recorded for this system yet.")

    with tabs[3]:
        if incidents:
            for incident in incidents:
                st.markdown(
                    f"""
                    <div class="ag-card">
                        <div class="title">INC-{int(incident['incident_id']):04d} ·
                            {html_lib.escape(str(incident['incident_type']))}
                            {severity_pill(incident['severity'])}
                            {incident_status_pill(incident['status'])}</div>
                        <div class="body">{html_lib.escape(str(incident['description'])[:300])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("No incidents have been reported against this system.")

    with tabs[4]:
        logs = audit_logger.logs_for_entity("ai_system", int(system_id), limit=50)
        if logs:
            st.dataframe(
                pd.DataFrame([
                    {"Timestamp (WAT)": audit_logger.format_timestamp(l["timestamp"]),
                     "User": l["actor_name"], "Action": l["action_type"],
                     "Details": l["details"]}
                    for l in logs
                ]),
                hide_index=True, height=280, **FULL_WIDTH,
            )
        else:
            st.caption("No audit entries for this system.")


def _render_risk_detail(risk: dict) -> None:
    """Show a saved risk assessment with its full breakdown."""
    breakdown = rc.risk_breakdown(
        risk["impact_score"], risk["likelihood_score"], risk["privacy_score"],
        risk["fairness_score"], risk["security_score"], risk["autonomy_score"],
    )
    meta = rc.risk_level_meta(risk["risk_level"])

    st.markdown(
        f"""
        <div class="risk-banner" style="background:linear-gradient(120deg,
             {meta['colour']} 0%, {meta['colour']}cc 100%)">
            <div class="score">{risk['total_risk_score']:.1f} / 100</div>
            <div class="band">{meta['icon']} {html_lib.escape(risk['risk_level']).upper()} RISK
                · score band {html_lib.escape(meta['range'])}</div>
            <div class="formula">{html_lib.escape(rc.formula_text())}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(f"Assessed by {risk.get('assessor_name') or '—'} on "
               f"{audit_logger.format_timestamp(risk['assessment_date'])}")

    chart_col, table_col = st.columns([1, 1], gap="medium")
    with chart_col:
        frame = pd.DataFrame([
            {"Dimension": row["label"], "Contribution": row["contribution"]}
            for row in breakdown
        ])
        fig = px.bar(frame, x="Contribution", y="Dimension", orientation="h",
                     color="Contribution",
                     color_continuous_scale=["#c8e6c9", "#c62828"])
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", height=290,
                          margin=dict(l=10, r=10, t=30, b=10))
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, config={"responsive": True, "displayModeBar": False},
                        **FULL_WIDTH)
    with table_col:
        st.dataframe(
            pd.DataFrame([
                {"Risk dimension": row["label"], "Score": row["raw_score"],
                 "Weight": f"{row['weight']:.2f}", "Contribution": row["contribution"],
                 "Share": f"{row['share_pct']:.1f}%"}
                for row in breakdown
            ]),
            hide_index=True, height=290, **FULL_WIDTH,
        )

    st.info(rc.risk_summary_sentence(risk["total_risk_score"], breakdown))


def _render_ethics_detail(ethics: dict) -> None:
    """Show a saved ethical impact assessment."""
    responses = {q["key"]: ethics.get(q["key"]) for q in rc.ETHICS_QUESTIONS}
    score, _earned, _possible = rc.calculate_ethics_score(responses)
    recommendation, reasoning = rc.determine_ethical_recommendation(responses)
    meta = rc.recommendation_meta(recommendation)

    st.markdown(
        f"""
        <div class="ag-card" style="border-left-color:{meta['colour']}">
            <div class="title">{meta['icon']} Recommendation:
                {html_lib.escape(str(ethics['recommendation']))}</div>
            <div class="sub">Ethical compliance {score * 100:.0f}% ·
                assessed by {html_lib.escape(str(ethics.get('assessor_name') or '—'))} on
                {html_lib.escape(audit_logger.format_timestamp(ethics['assessment_date']))}</div>
            <div class="body">{html_lib.escape(reasoning)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    frames = []
    for question in rc.ETHICS_QUESTIONS:
        answer = str(ethics.get(question["key"]) or "—")
        icon = {"Yes": "✅", "Partial": "🟡", "No": "⛔"}.get(answer, "➖")
        frames.append({
            "Ethical requirement": question["label"],
            "Response": f"{icon} {answer}",
            "Classification": "Critical" if question["critical"] else "Standard",
        })
    st.dataframe(pd.DataFrame(frames), hide_index=True, **FULL_WIDTH)


# =================================================================================
# 10. PAGE - REGISTER AI SYSTEM  (Developer)
# =================================================================================
def page_register_system() -> None:
    platform_header(
        "Register a New AI System",
        "Add an AI system to the governance register so it can be assessed and reviewed",
        badge="DEVELOPER",
    )

    if not auth.require_permission("register_system"):
        return

    user = auth.get_current_user() or {}

    with st.form("register_system_form", clear_on_submit=False):
        st.markdown("##### 1. What the system is")
        name = st.text_input("AI system name *",
                             placeholder="e.g. Fraud Detection System")
        purpose = st.text_area(
            "Purpose and description *", height=110,
            placeholder="Explain in plain language what the AI does, what decisions it "
                        "influences, and who is affected.",
        )
        technology = st.selectbox("AI technology type *", TECHNOLOGY_TYPES)

        st.markdown("##### 2. What data it uses and who it affects")
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            data_sources = st.multiselect("Data sources used *", DATA_SOURCE_OPTIONS)
        with col_b:
            affected = st.multiselect("Affected parties *", AFFECTED_USER_OPTIONS)

        st.markdown("##### 3. Where it is deployed")
        deployment = st.selectbox("Deployment status *", DEPLOYMENT_STATUSES, index=0)

        st.caption(
            f"System owner will be recorded as **{user.get('full_name', '')}** "
            f"({user.get('organization') or 'no organisation set'})."
        )

        submitted = st.form_submit_button("🗂️ Register AI system", type="primary",
                                          **FULL_WIDTH)

    if submitted:
        errors: list[str] = []
        if not name.strip():
            errors.append("Please enter the AI system name.")
        elif len(name.strip()) < 3:
            errors.append("The AI system name is too short.")
        if not purpose.strip():
            errors.append("Please describe what the system does.")
        elif len(purpose.strip()) < 20:
            errors.append("Please describe the purpose in at least 20 characters - an "
                          "assessor needs to understand what the system actually does.")
        if not data_sources:
            errors.append("Select at least one data source.")
        if not affected:
            errors.append("Select at least one affected party.")

        if errors:
            for error in errors:
                st.error(f"⛔ {error}")
        else:
            try:
                system_id = db.execute_query(
                    """
                    INSERT INTO ai_systems
                        (system_name, purpose, technology_type, data_sources,
                         affected_users, owner_id, deployment_status, governance_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Draft')
                    """,
                    (name.strip(), purpose.strip(), technology,
                     "; ".join(data_sources), "; ".join(affected),
                     auth.current_user_id(), deployment),
                )
                audit_logger.log_action(
                    auth.current_user_id(), "SYSTEM_CREATED", "ai_system", system_id,
                    f"Registered '{name.strip()}' ({technology}). "
                    f"Deployment status: {deployment}. "
                    f"Data sources: {', '.join(data_sources)}. "
                    f"Affected parties: {', '.join(affected)}.",
                )
                notify("success", f"'{name.strip()}' registered as AIS-{system_id:04d}. "
                                   f"Next step: complete the risk assessment.")
                st.session_state["selected_system_id"] = system_id
                st.rerun()
            except db.DatabaseError as exc:
                st.error(f"⛔ {exc}")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.expander("ℹ️ Why the register matters"):
        st.markdown(
            """
            An AI inventory is the foundation of every credible governance framework.
            An organisation cannot govern what it has not recorded, and a regulator
            cannot audit a system that does not appear on any register.

            Once a system is registered it moves through the governance workflow:

            `Draft → Submitted → Under Review → Approved / Returned / Rejected`

            A system cannot be approved until both a risk assessment and an ethical
            impact assessment are on record.
            """
        )


# =================================================================================
# 11. PAGE - RISK ASSESSMENT  (Developer)
# =================================================================================
def page_risk_assessment() -> None:
    platform_header(
        "Risk Assessment",
        "Score the AI system across six weighted risk dimensions",
        badge="DEVELOPER",
    )

    if not auth.require_permission("assess_risk"):
        return

    systems = scope_systems_for_user() or []
    if not systems:
        st.info("You have no AI systems to assess. Register a system first.")
        return

    options = {f"AIS-{int(s['system_id']):04d} · {s['system_name']}": int(s["system_id"])
               for s in systems}
    preset = st.session_state.get("selected_system_id")
    default_index = 0
    if preset:
        for index, value in enumerate(options.values()):
            if value == preset:
                default_index = index
                break

    picked = st.selectbox("Select the AI system to assess", list(options.keys()),
                          index=default_index)
    system_id = options[picked]
    st.session_state["selected_system_id"] = system_id

    existing = load_risk(system_id)
    if existing:
        st.info(
            f"ℹ️ This system already has a risk assessment from "
            f"{audit_logger.format_timestamp(existing['assessment_date'])} "
            f"(score {existing['total_risk_score']:.1f}, {existing['risk_level']}). "
            f"Saving below will record a NEW assessment, and the latest one is the one "
            f"the Governance Officer will see."
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    section("Rate each dimension from 0 (no risk) to 100 (extreme risk)")

    slider_defaults = 50
    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        impact = st.slider(
            "Impact / Severity of Harm", 0, 100, slider_defaults, step=5,
            help=rc.DIMENSION_HELP["impact"])
        privacy = st.slider(
            "Privacy Sensitivity", 0, 100, slider_defaults, step=5,
            help=rc.DIMENSION_HELP["privacy"])
        security = st.slider(
            "Security Exposure", 0, 100, slider_defaults, step=5,
            help=rc.DIMENSION_HELP["security"])
    with col_right:
        likelihood = st.slider(
            "Likelihood of Harm", 0, 100, slider_defaults, step=5,
            help=rc.DIMENSION_HELP["likelihood"])
        fairness = st.slider(
            "Fairness / Bias Concern", 0, 100, slider_defaults, step=5,
            help=rc.DIMENSION_HELP["fairness"])
        autonomy = st.slider(
            "Autonomy / Decision Impact", 0, 100, slider_defaults, step=5,
            help=rc.DIMENSION_HELP["autonomy"])

    # ---- LIVE CALCULATION -------------------------------------------------
    score = rc.calculate_risk_score(impact, likelihood, privacy, fairness,
                                    security, autonomy)
    level = rc.determine_risk_level(score)
    meta = rc.risk_level_meta(level)
    breakdown = rc.risk_breakdown(impact, likelihood, privacy, fairness,
                                  security, autonomy)

    st.markdown(
        f"""
        <div class="risk-banner" style="background:linear-gradient(120deg,
             {meta['colour']} 0%, {meta['colour']}cc 100%)">
            <div class="score">{score:.1f} / 100</div>
            <div class="band">{meta['icon']} {html_lib.escape(level).upper()} RISK
                · score band {html_lib.escape(meta['range'])}</div>
            <div class="formula">{html_lib.escape(rc.formula_text())}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(rc.risk_summary_sentence(score, breakdown))

    chart_col, table_col = st.columns([1, 1], gap="medium")
    with chart_col:
        frame = pd.DataFrame([
            {"Dimension": row["label"], "Contribution": row["contribution"]}
            for row in breakdown
        ])
        fig = px.bar(frame, x="Contribution", y="Dimension", orientation="h",
                     color="Contribution",
                     color_continuous_scale=["#c8e6c9", "#c62828"])
        fig.update_layout(coloraxis_showscale=False, yaxis_title="", height=300,
                          margin=dict(l=10, r=10, t=30, b=10))
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, config={"responsive": True, "displayModeBar": False},
                        **FULL_WIDTH)
    with table_col:
        st.dataframe(
            pd.DataFrame([
                {"Risk dimension": row["label"], "Score": row["raw_score"],
                 "Weight": f"{row['weight']:.2f}",
                 "Contribution": row["contribution"],
                 "Share of total": f"{row['share_pct']:.1f}%"}
                for row in breakdown
            ]),
            hide_index=True, height=300, **FULL_WIDTH,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("💾 Save this risk assessment", type="primary", **FULL_WIDTH):
        try:
            db.execute_query(
                """
                INSERT INTO risk_assessments
                    (system_id, impact_score, likelihood_score, privacy_score,
                     fairness_score, security_score, autonomy_score,
                     total_risk_score, risk_level, assessed_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (system_id, impact, likelihood, privacy, fairness, security, autonomy,
                 score, level, auth.current_user_id()),
            )
            db.execute_query("UPDATE ai_systems SET updated_at = CURRENT_TIMESTAMP "
                             "WHERE system_id = ?", (system_id,))

            drivers = " and ".join(d["label"] for d in rc.top_drivers(breakdown, 2))
            audit_logger.log_action(
                auth.current_user_id(), "RISK_ASSESSED", "ai_system", system_id,
                f"Risk assessment saved for '{picked.split('· ')[-1]}'. "
                f"Impact {impact}, Likelihood {likelihood}, Privacy {privacy}, "
                f"Fairness {fairness}, Security {security}, Autonomy {autonomy}. "
                f"Weighted score {score} - {level} risk. "
                f"Main drivers: {drivers}.",
            )
            notify("success", f"Risk assessment saved: {score:.1f} ({level}).")
            st.rerun()
        except db.DatabaseError as exc:
            st.error(f"⛔ {exc}")

    with st.expander("ℹ️ How the risk score is calculated"):
        st.markdown(
            f"""
            **{rc.formula_text()}**

            The weights sum to exactly 1.00, so the result stays on the same 0-100
            scale as the six inputs and is directly comparable between systems.

            | Dimension | Weight | Why |
            |---|---|---|
            | Impact / Severity of Harm | 0.30 | Governance is ultimately about the severity of harm to people |
            | Likelihood of Harm | 0.20 | A severe but improbable failure is less urgent than a frequent moderate one |
            | Privacy Sensitivity | 0.15 | The NDPA 2023 focuses on unlawful processing of personal data |
            | Fairness / Bias | 0.15 | Automated discrimination is the harm most often cited in AI regulation |
            | Security Exposure | 0.10 | Modifies exposure rather than creating harm directly |
            | Autonomy / Decision Impact | 0.10 | The less human review, the higher the residual risk |

            **Risk bands:** 0-20 Low · 21-40 Moderate · 41-70 High · 71-100 Critical.

            A score is arithmetic, not a judgement: the Governance Officer still reviews
            the evidence and makes the decision.
            """
        )


# =================================================================================
# 12. PAGE - ETHICAL IMPACT ASSESSMENT  (Developer)
# =================================================================================
def page_ethical_assessment() -> None:
    platform_header(
        "Ethical Impact Assessment",
        "Evaluate the system against the eight ethical requirements of the framework",
        badge="DEVELOPER",
    )

    if not auth.require_permission("assess_ethics"):
        return

    systems = scope_systems_for_user() or []
    if not systems:
        st.info("You have no AI systems to assess. Register a system first.")
        return

    options = {f"AIS-{int(s['system_id']):04d} · {s['system_name']}": int(s["system_id"])
               for s in systems}
    preset = st.session_state.get("selected_system_id")
    default_index = 0
    if preset:
        for index, value in enumerate(options.values()):
            if value == preset:
                default_index = index
                break

    picked = st.selectbox("Select the AI system to assess", list(options.keys()),
                          index=default_index)
    system_id = options[picked]
    st.session_state["selected_system_id"] = system_id

    existing = load_ethics(system_id)
    if existing:
        st.info(f"ℹ️ An ethical assessment already exists for this system "
                f"({existing['recommendation']}, saved "
                f"{audit_logger.format_timestamp(existing['assessment_date'])}). "
                f"Saving will record a new assessment.")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    section("Answer all eight questions")

    responses: dict[str, str] = {}
    left, right = st.columns(2, gap="medium")
    for index, question in enumerate(rc.ETHICS_QUESTIONS):
        target = left if index % 2 == 0 else right
        with target:
            marker = "🔴 Critical" if question["critical"] else "Standard"
            responses[question["key"]] = st.radio(
                f"{question['label']}  ({marker})",
                rc.RESPONSE_OPTIONS, index=0, key=f"eth_{system_id}_{question['key']}",
                help=question["question"],
            )

    # ---- LIVE RECOMMENDATION ---------------------------------------------
    score, earned, possible = rc.calculate_ethics_score(responses)
    recommendation, reasoning = rc.determine_ethical_recommendation(responses)
    meta = rc.recommendation_meta(recommendation)

    st.markdown(
        f"""
        <div class="ag-card" style="border-left-color:{meta['colour']};background:{meta['bg']}">
            <div class="title">{meta['icon']} Live recommendation:
                {html_lib.escape(recommendation)}</div>
            <div class="sub">Ethical compliance {score * 100:.0f}%
                ({earned} of {possible} applicable points)</div>
            <div class="body">{html_lib.escape(reasoning)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("💾 Save this ethical assessment", type="primary", **FULL_WIDTH):
        try:
            db.execute_query(
                """
                INSERT INTO ethical_assessments
                    (system_id, fairness_response, privacy_response,
                     transparency_response, accountability_response, oversight_response,
                     security_response, explainability_response, accessibility_response,
                     recommendation, assessed_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (system_id, responses["fairness_response"], responses["privacy_response"],
                 responses["transparency_response"], responses["accountability_response"],
                 responses["oversight_response"], responses["security_response"],
                 responses["explainability_response"], responses["accessibility_response"],
                 recommendation, auth.current_user_id()),
            )
            db.execute_query("UPDATE ai_systems SET updated_at = CURRENT_TIMESTAMP "
                             "WHERE system_id = ?", (system_id,))

            answers = ", ".join(f"{q['label']}={responses[q['key']]}"
                                for q in rc.ETHICS_QUESTIONS)
            audit_logger.log_action(
                auth.current_user_id(), "ETHICS_ASSESSED", "ai_system", system_id,
                f"Ethical impact assessment saved. Recommendation: {recommendation} "
                f"({score * 100:.0f}% compliance). Responses: {answers}.",
            )
            notify("success", f"Ethical assessment saved: {recommendation}.")
            st.rerun()
        except db.DatabaseError as exc:
            st.error(f"⛔ {exc}")

    with st.expander("ℹ️ How the recommendation is decided"):
        st.markdown(
            """
            Each question scores **Yes = 1.0**, **Partial = 0.5**, **No = 0.0**.
            *Not Applicable* is removed from the calculation entirely, so genuinely
            irrelevant questions neither help nor harm the result.

            Four questions are **critical**: Fairness, Privacy, Accountability and
            Human Oversight. The decision rules are:

            1. **Two or more critical questions answered "No"** → *Rejected*.
               A system failing more than one of fairness, privacy, accountability and
               oversight cannot be deployed responsibly.
            2. **One critical "No"** → at best *Needs Improvement*.
            3. Otherwise, by overall compliance:
               * **≥ 85%** → *Approved*
               * **55–84%** → *Needs Improvement*
               * **< 55%** → *Rejected*

            The recommendation is advisory evidence for the Governance Officer, who
            makes the formal decision.
            """
        )


# =================================================================================
# 13. PAGE - REVIEW SUBMISSIONS  (Governance Officer)
# =================================================================================
def page_review() -> None:
    platform_header(
        "Review Submissions",
        "Assess submitted AI systems and record a formal governance decision",
        badge="GOVERNANCE OFFICER",
    )

    if not auth.require_permission("review_submissions"):
        return

    systems = load_systems()
    queue = [s for s in systems if s["governance_status"] in ("Submitted", "UnderReview")]
    decided = [s for s in systems
               if s["governance_status"] in ("Approved", "Returned", "Rejected")]

    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Awaiting review", len(queue))
    c2.metric("Approved", len([s for s in decided if s["governance_status"] == "Approved"]))
    c3.metric("Returned", len([s for s in decided if s["governance_status"] == "Returned"]))
    c4.metric("Rejected", len([s for s in decided if s["governance_status"] == "Rejected"]))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section("📥 Review queue")

    if not queue:
        st.success("✅ There are no AI systems awaiting review.")
    else:
        for system in queue:
            risk = load_risk(system["system_id"])
            ethics = load_ethics(system["system_id"])
            missing = []
            if not risk:
                missing.append("risk assessment")
            if not ethics:
                missing.append("ethical assessment")

            st.markdown(
                f"""
                <div class="ag-card">
                    <div class="title">🗂️ {html_lib.escape(system['system_name'])}
                        {status_pill(system['governance_status'])}</div>
                    <div class="sub">
                        AIS-{int(system['system_id']):04d} ·
                        {html_lib.escape(str(system.get('technology_type') or '—'))} ·
                        {deployment_pill(system.get('deployment_status') or '—')} ·
                        owner {html_lib.escape(str(system.get('owner_name') or '—'))}
                    </div>
                    <div style="margin-top:8px">
                        {risk_pill(risk['total_risk_score'] if risk else None,
                                   risk['risk_level'] if risk else None)}
                        &nbsp;<span class="pill" style="background:#e8eef7;color:#1b4079;">
                            ⚖️ {html_lib.escape(str(ethics['recommendation'])) if ethics else 'NO ETHICS ASSESSMENT'}</span>
                        {'&nbsp;<span class="pill" style="background:#ffebee;color:#c62828;">⚠️ missing: '
                         + html_lib.escape(', '.join(missing)) + '</span>' if missing else ''}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        section("Make a decision")
        options = {f"AIS-{int(s['system_id']):04d} · {s['system_name']}": int(s["system_id"])
                   for s in queue}
        picked = st.selectbox("Select a submission to review", list(options.keys()))
        system_id = options[picked]

        _render_system_detail(system_id)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        section("⚖️ Governance decision")

        risk = load_risk(system_id)
        ethics = load_ethics(system_id)
        risk_level = risk["risk_level"] if risk else None
        high_risk = risk_level in ("High", "Critical")

        blockers: list[str] = []
        if not risk:
            blockers.append("A risk assessment has not been completed.")
        if not ethics:
            blockers.append("An ethical impact assessment has not been completed.")

        if blockers:
            for blocker in blockers:
                st.warning(f"⚠️ {blocker}")

        if high_risk:
            st.error(
                f"🔴 This system is rated **{risk_level} risk** "
                f"(score {risk['total_risk_score']:.1f}). Under the framework, High and "
                f"Critical risk systems require **Administrator** approval."
            )

        comments = st.text_area(
            "Decision comments (recorded permanently in the audit trail) *", height=110,
            placeholder="Explain the reasoning, any conditions attached to approval, or "
                        "exactly what the developer must change before resubmission.",
        )

        b1, b2, b3 = st.columns(3, gap="small")
        with b1:
            approve_clicked = st.button("✅ Approve", type="primary", **FULL_WIDTH,
                                        disabled=bool(blockers))
        with b2:
            return_clicked = st.button("↩️ Return for changes", **FULL_WIDTH,
                                       disabled=bool(blockers))
        with b3:
            reject_clicked = st.button("⛔ Reject", **FULL_WIDTH, disabled=bool(blockers))

        decision: Optional[str] = None
        if approve_clicked:
            decision = "Approved"
        elif return_clicked:
            decision = "Returned"
        elif reject_clicked:
            decision = "Rejected"

        if decision:
            if len(comments.strip()) < 10:
                st.error("⛔ Please record the reasoning for the decision (at least 10 "
                         "characters). A governance decision without a recorded reason "
                         "cannot be audited.")
            elif decision == "Approved" and high_risk and not auth.has_permission("approve_high_risk"):
                st.error(
                    f"⛔ Approval blocked. A {risk_level} risk system requires an "
                    f"Administrator. You may Return it for remediation or ask an "
                    f"Administrator to approve it."
                )
                audit_logger.log_action(
                    auth.current_user_id(), "SYSTEM_UPDATED", "ai_system", system_id,
                    f"Attempted to approve a {risk_level} risk system; blocked because "
                    f"the framework requires Administrator approval for high-risk AI.",
                )
            else:
                try:
                    db.execute_query(
                        """
                        INSERT INTO approvals (system_id, decision, comments, reviewer_id)
                        VALUES (?, ?, ?, ?)
                        """,
                        (system_id, decision, comments.strip(), auth.current_user_id()),
                    )
                    db.execute_query(
                        "UPDATE ai_systems SET governance_status = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE system_id = ?",
                        (decision, system_id),
                    )
                    action = {"Approved": "SYSTEM_APPROVED",
                              "Returned": "SYSTEM_RETURNED",
                              "Rejected": "SYSTEM_REJECTED"}[decision]
                    audit_logger.log_action(
                        auth.current_user_id(), action, "ai_system", system_id,
                        f"Governance decision: {decision} for '{picked.split('· ')[-1]}' "
                        f"(risk {risk['total_risk_score']:.1f} {risk_level}). "
                        f"Reason: {comments.strip()}",
                    )
                    notify("success", f"Decision recorded: {decision}.")
                    st.rerun()
                except db.DatabaseError as exc:
                    st.error(f"⛔ {exc}")

    # ---- decided systems --------------------------------------------------
    if decided:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        section("📜 Previously decided systems")
        frame = pd.DataFrame([
            {
                "Ref": f"AIS-{int(s['system_id']):04d}",
                "System": s["system_name"],
                "Decision": s["governance_status"],
                "Risk": (f"{s['total_risk_score']:.1f} {s['risk_level']}"
                         if s.get("total_risk_score") is not None else "Not assessed"),
                "Owner": s.get("owner_name") or "—",
            }
            for s in decided
        ])
        st.dataframe(frame, hide_index=True, **FULL_WIDTH)


# =================================================================================
# 14. PAGE - INCIDENTS
# =================================================================================
def page_incidents() -> None:
    platform_header(
        "AI Incident Management",
        "Report, investigate and resolve AI-related incidents",
        badge="ALL STAFF",
    )

    user_id = auth.current_user_id()
    system_ids = visible_system_ids()

    if auth.has_permission("view_all_incidents"):
        incidents = load_incidents()
        scope_note = "You can see every incident reported in the organisation."
    elif system_ids:
        incidents = load_incidents(reported_by=user_id, system_ids=system_ids)
        scope_note = ("You can see incidents affecting your own AI systems, and any "
                      "incident you reported yourself.")
    else:
        incidents = load_incidents(reported_by=user_id)
        scope_note = "You can see only the incidents you reported yourself."

    can_manage = auth.has_permission("manage_incidents")

    tab_report, tab_track = st.tabs(["📣 Report an incident", "📋 Track incidents"])

    # ---------------- report ----------------------------------------------
    with tab_report:
        st.caption(scope_note)

        all_systems = load_systems()
        if not all_systems:
            st.warning("No AI systems are registered yet, so an incident cannot be "
                       "linked to a system.")
            system_options: dict[str, Optional[int]] = {"Not linked to a specific system": None}
        else:
            system_options = {
                f"AIS-{int(s['system_id']):04d} · {s['system_name']}": int(s["system_id"])
                for s in all_systems
            }

        with st.form("report_incident_form", clear_on_submit=False):
            system_choice = st.selectbox("AI system involved *", list(system_options.keys()))
            col_a, col_b = st.columns(2, gap="medium")
            with col_a:
                incident_type = st.selectbox("Incident type *", INCIDENT_TYPES)
            with col_b:
                severity = st.selectbox("Severity *", INCIDENT_SEVERITIES, index=1)

            description = st.text_area(
                "What happened? *", height=130,
                placeholder="Describe what you observed, when it happened, and who was "
                            "affected. Be specific - this record may be used in a "
                            "regulatory notification.",
            )
            affected_parties = st.text_input(
                "Affected parties", placeholder="e.g. 4 812 customers in Enugu and Anambra")

            submitted = st.form_submit_button("📣 Submit incident report", type="primary",
                                              **FULL_WIDTH)

        if submitted:
            errors = []
            if len(description.strip()) < 20:
                errors.append("Please describe the incident in at least 20 characters.")
            if errors:
                for error in errors:
                    st.error(f"⛔ {error}")
            else:
                try:
                    incident_id = db.execute_query(
                        """
                        INSERT INTO incidents
                            (system_id, incident_type, severity, description,
                             affected_parties, status, reported_by)
                        VALUES (?, ?, ?, ?, ?, 'Reported', ?)
                        """,
                        (system_options[system_choice], incident_type, severity,
                         description.strip(), affected_parties.strip(), user_id),
                    )
                    audit_logger.log_action(
                        user_id, "INCIDENT_REPORTED", "incident", incident_id,
                        f"{incident_type} incident reported against "
                        f"'{system_choice.split('· ')[-1]}'. Severity: {severity}. "
                        f"Affected parties: {affected_parties.strip() or 'not specified'}. "
                        f"Description: {description.strip()[:400]}",
                    )
                    notify("success",
                           f"Incident INC-{incident_id:04d} reported. The Governance "
                           f"Officer has been notified.")
                    st.rerun()
                except db.DatabaseError as exc:
                    st.error(f"⛔ {exc}")

        with st.expander("ℹ️ What should be reported?"):
            st.markdown(
                """
                Report any AI-related harm, near-miss or concern, including:

                * **Bias or discrimination** — the system treats a group unfairly
                * **Data breach** — personal data exposed or misused
                * **Incorrect decision** — the AI produced a wrong or unjust outcome
                * **Security incident** — the system was attacked or manipulated
                * **System failure** — the AI stopped working or behaved unpredictably
                * **Privacy violation** — data used beyond what the user was told
                * **Lack of transparency** — users were not told they were dealing with AI

                Reporting is not an admission of fault. Under the Nigeria Data Protection
                Act 2023, incidents involving personal data may require notification to
                the Nigeria Data Protection Commission, so early reporting is a legal
                necessity, not an option.
                """
            )

    # ---------------- track ------------------------------------------------
    with tab_track:
        if not incidents:
            st.info("No incidents to display.")
            return

        open_count = len([i for i in incidents
                          if i["status"] in ("Reported", "UnderInvestigation")])
        critical_count = len([i for i in incidents if i["severity"] == "Critical"])

        m1, m2, m3 = st.columns(3, gap="small")
        m1.metric("Incidents in view", len(incidents))
        m2.metric("Open", open_count)
        m3.metric("Critical", critical_count)

        f1, f2, f3 = st.columns(3, gap="small")
        with f1:
            status_filter = st.multiselect("Status", INCIDENT_STATUSES, default=[])
        with f2:
            severity_filter = st.multiselect("Severity", INCIDENT_SEVERITIES, default=[])
        with f3:
            type_filter = st.multiselect("Type", INCIDENT_TYPES, default=[])

        filtered = incidents
        if status_filter:
            filtered = [i for i in filtered if i["status"] in status_filter]
        if severity_filter:
            filtered = [i for i in filtered if i["severity"] in severity_filter]
        if type_filter:
            filtered = [i for i in filtered if i["incident_type"] in type_filter]

        section(f"📋 {len(filtered)} incident(s)")
        for incident in filtered:
            st.markdown(
                f"""
                <div class="ag-card" style="border-left-color:
                     {SEVERITY_META.get(incident['severity'], {}).get('colour', '#616161')}">
                    <div class="title">INC-{int(incident['incident_id']):04d} ·
                        {html_lib.escape(str(incident['incident_type']))}
                        {severity_pill(incident['severity'])}
                        {incident_status_pill(incident['status'])}</div>
                    <div class="sub">
                        {html_lib.escape(str(incident.get('system_name') or 'Not linked'))} ·
                        reported by {html_lib.escape(str(incident.get('reporter_name') or '—'))} ·
                        {html_lib.escape(audit_logger.format_timestamp(incident['reported_at']))}
                    </div>
                    <div class="body">{html_lib.escape(str(incident['description'])[:400])}</div>
                    {f'<div class="body"><b>Corrective action:</b> '
                       + html_lib.escape(str(incident["corrective_action"])[:300]) + '</div>'
                       if incident.get('corrective_action') else ''}
                    {f'<div class="sub">Affected: '
                       + html_lib.escape(str(incident["affected_parties"])) + '</div>'
                       if incident.get('affected_parties') else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---- manage (governance / admin only) ----------------------------
        if can_manage:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            section("🔧 Update an incident")
            manage_options = {
                f"INC-{int(i['incident_id']):04d} · {i['incident_type']} "
                f"[{i['status']}]": int(i["incident_id"])
                for i in filtered
            }
            picked = st.selectbox("Select an incident", list(manage_options.keys()))
            incident_id = manage_options[picked]
            incident = safe_fetch_one("SELECT * FROM incidents WHERE incident_id = ?",
                                      (incident_id,), "the incident")
            if incident:
                new_status = st.selectbox(
                    "Status", INCIDENT_STATUSES,
                    index=INCIDENT_STATUSES.index(incident["status"]),
                )
                corrective = st.text_area(
                    "Corrective action taken", height=100,
                    value=str(incident.get("corrective_action") or ""),
                    placeholder="Describe what was done to contain and remedy the incident.",
                )
                if st.button("💾 Save incident update", type="primary", **FULL_WIDTH):
                    try:
                        resolved_at_clause = ""
                        params: list[Any] = [new_status, corrective.strip()]
                        if new_status in ("Resolved", "Closed"):
                            resolved_at_clause = ", resolved_at = CURRENT_TIMESTAMP"
                        params.append(incident_id)
                        db.execute_query(
                            f"UPDATE incidents SET status = ?, corrective_action = ? "
                            f"{resolved_at_clause} WHERE incident_id = ?",
                            tuple(params),
                        )
                        action = ("INCIDENT_RESOLVED"
                                  if new_status in ("Resolved", "Closed")
                                  else "INCIDENT_UPDATED")
                        audit_logger.log_action(
                            auth.current_user_id(), action, "incident", incident_id,
                            f"Incident INC-{incident_id:04d} updated: status "
                            f"{incident['status']} -> {new_status}. "
                            f"Corrective action: {corrective.strip()[:400] or 'none recorded'}",
                        )
                        notify("success", f"INC-{incident_id:04d} updated to {new_status}.")
                        st.rerun()
                    except db.DatabaseError as exc:
                        st.error(f"⛔ {exc}")
        else:
            st.caption("🔒 Only the AI Governance Officer and the Administrator can "
                       "update incident status and corrective actions.")


# =================================================================================
# 15. PAGE - AUDIT TRAIL
# =================================================================================
def page_audit() -> None:
    platform_header(
        "Audit Trail",
        "Append-only record of every governance action taken in the platform",
        badge="READ-ONLY EVIDENCE",
    )

    if not auth.require_permission("view_audit"):
        return

    stats = audit_logger.audit_statistics()
    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Audit entries", stats["total"])
    c2.metric("Distinct action types", stats["action_types"])
    c3.metric("Users who acted", stats["actors"])
    c4.metric("Entries today", stats["today"])

    st.info(
        "🔒 The audit trail is **append-only**. There is no code path in this platform "
        "that can update or delete an audit entry, which is what makes it usable as "
        "compliance evidence under a regulatory audit."
    )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    section("🔎 Filter the trail")

    users = auth.list_users()
    f1, f2, f3 = st.columns(3, gap="small")
    with f1:
        user_options = {"All users": None}
        user_options.update({f"{u['full_name']} ({auth.ROLE_LABELS.get(u['role'], u['role'])})":
                             int(u["user_id"]) for u in users})
        user_pick = st.selectbox("User", list(user_options.keys()))
    with f2:
        action_pick = st.selectbox("Action type", ["All actions"] + audit_logger.ACTION_TYPES)
    with f3:
        entity_pick = st.selectbox("Entity type", ["All entities", "ai_system", "incident",
                                                   "user", "session", "report", "platform"])

    f4, f5, f6 = st.columns(3, gap="small")
    with f4:
        date_from = st.date_input("From date", value=datetime.utcnow().date() - timedelta(days=120))
    with f5:
        date_to = st.date_input("To date", value=datetime.utcnow().date() + timedelta(days=1))
    with f6:
        search = st.text_input("Search details", placeholder="keyword in the details field")

    logs = audit_logger.fetch_logs(
        limit=2000,
        user_id=user_options[user_pick],
        action_type=None if action_pick == "All actions" else action_pick,
        entity_type=None if entity_pick == "All entities" else entity_pick,
        date_from=str(date_from),
        date_to=str(date_to),
        search=search.strip() or None,
    )

    section(f"📜 {len(logs)} audit entr{'y' if len(logs) == 1 else 'ies'}")

    if not logs:
        st.info("No audit entries match these filters.")
        return

    frame = pd.DataFrame([
        {
            "Timestamp (WAT)": audit_logger.format_timestamp(log["timestamp"]),
            "User": log["actor_name"],
            "Role": auth.ROLE_LABELS.get(log["actor_role"], log["actor_role"]),
            "Action": log["action_type"],
            "Entity": f"{log['entity_type'] or '—'}"
                      + (f" #{int(log['entity_id'])}" if log["entity_id"] else ""),
            "Details": log["details"],
        }
        for log in logs
    ])
    st.dataframe(frame, hide_index=True, height=440, **FULL_WIDTH)

    export_col, note_col = st.columns([1, 2], gap="medium")
    with export_col:
        st.download_button(
            "⬇️ Export audit trail as CSV",
            data=frame.to_csv(index=False).encode("utf-8"),
            file_name=f"audit_trail_{datetime.utcnow().strftime('%Y-%m-%d')}.csv",
            mime="text/csv", **FULL_WIDTH,
        )
    with note_col:
        st.caption("Export this file for the external auditor. It contains every action "
                   "in the filtered range with the responsible user and timestamp.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section("📊 Activity by action type")
    counts = frame["Action"].value_counts().head(12).reset_index()
    counts.columns = ["Action", "Count"]
    fig = px.bar(counts, x="Count", y="Action", orientation="h",
                 color="Count", color_continuous_scale=["#c8e6c9", "#0b2545"])
    fig.update_layout(coloraxis_showscale=False, yaxis_title="", height=340,
                      margin=dict(l=10, r=10, t=20, b=10))
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, config={"responsive": True, "displayModeBar": False},
                    **FULL_WIDTH)


# =================================================================================
# 16. PAGE - REPORTS
# =================================================================================
def page_reports() -> None:
    platform_header(
        "Governance Reports",
        "Generate print-ready compliance documents for management, auditors and regulators",
        badge="EXPORT",
    )

    if not auth.require_permission("generate_reports"):
        return

    catalogue = reports.report_index()

    tab_system, tab_compliance, tab_incident = st.tabs(
        ["🗂️ AI System Governance Report",
         "📊 Compliance Summary Report",
         "🚨 Incident Report"]
    )

    # ---------------- system report ---------------------------------------
    with tab_system:
        st.markdown(f"**{catalogue[0]['description']}**")
        st.caption(f"Typical audience: {catalogue[0]['audience']}")

        systems = reports.selectable_systems()
        owner_scope = None if auth.has_permission("view_all_systems") else auth.current_user_id()
        if owner_scope is not None:
            allowed = {int(s["system_id"]) for s in load_systems(owner_id=owner_scope)}
            systems = [s for s in systems if int(s["system_id"]) in allowed]

        if not systems:
            st.info("No AI systems are available to report on.")
        else:
            options = {f"AIS-{int(s['system_id']):04d} · {s['system_name']}": int(s["system_id"])
                       for s in systems}
            picked = st.selectbox("Select an AI system", list(options.keys()),
                                  key="report_system_pick")
            if st.button("📄 Generate AI System Governance Report", type="primary",
                         **FULL_WIDTH):
                try:
                    html_doc, filename = reports.generate_system_report(options[picked])
                    st.session_state["report_html"] = html_doc
                    st.session_state["report_filename"] = filename
                    audit_logger.log_action(
                        auth.current_user_id(), "REPORT_GENERATED", "ai_system",
                        options[picked],
                        f"AI System Governance Report generated for "
                        f"'{picked.split('· ')[-1]}'.",
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"⛔ Could not generate the report: {exc}")

    # ---------------- compliance report ------------------------------------
    with tab_compliance:
        st.markdown(f"**{catalogue[1]['description']}**")
        st.caption(f"Typical audience: {catalogue[1]['audience']}")
        if st.button("📊 Generate Compliance Summary Report", type="primary", **FULL_WIDTH,
                     disabled=not auth.has_permission("view_all_systems")):
            try:
                html_doc, filename = reports.generate_compliance_report()
                st.session_state["report_html"] = html_doc
                st.session_state["report_filename"] = filename
                audit_logger.log_action(
                    auth.current_user_id(), "REPORT_GENERATED", "report", None,
                    "Compliance Summary Report generated.",
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"⛔ Could not generate the report: {exc}")

        if not auth.has_permission("view_all_systems"):
            st.warning("⚠️ The compliance summary covers the whole organisation, so it is "
                       "available only to the Governance Officer, Administrator and Auditor.")

    # ---------------- incident report --------------------------------------
    with tab_incident:
        st.markdown(f"**{catalogue[2]['description']}**")
        st.caption(f"Typical audience: {catalogue[2]['audience']}")

        if auth.has_permission("view_all_incidents"):
            incidents = reports.selectable_incidents()
        else:
            mine = load_incidents(reported_by=auth.current_user_id())
            incidents = [
                {"incident_id": i["incident_id"], "incident_type": i["incident_type"],
                 "severity": i["severity"], "status": i["status"],
                 "system_name": i.get("system_name") or "—"}
                for i in mine
            ]

        if not incidents:
            st.info("No incidents are available to report on.")
        else:
            options = {
                f"INC-{int(i['incident_id']):04d} · {i['incident_type']} "
                f"[{i['severity']}]": int(i["incident_id"])
                for i in incidents
            }
            picked = st.selectbox("Select an incident", list(options.keys()),
                                  key="report_incident_pick")
            if st.button("🚨 Generate Incident Report", type="primary", **FULL_WIDTH):
                try:
                    html_doc, filename = reports.generate_incident_report(options[picked])
                    st.session_state["report_html"] = html_doc
                    st.session_state["report_filename"] = filename
                    audit_logger.log_action(
                        auth.current_user_id(), "REPORT_GENERATED", "incident",
                        options[picked],
                        f"Incident Report generated for INC-{options[picked]:04d}.",
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"⛔ Could not generate the report: {exc}")

    # ---------------- preview + download -----------------------------------
    if st.session_state.get("report_html"):
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        section("🖨️ Report preview")

        html_doc = st.session_state["report_html"]
        filename = st.session_state.get("report_filename", "governance_report.html")

        d1, d2 = st.columns([1, 3], gap="medium")
        with d1:
            st.download_button("⬇️ Download report (HTML)", data=html_doc.encode("utf-8"),
                               file_name=filename, mime="text/html",
                               type="primary", **FULL_WIDTH)
        with d2:
            st.caption("Open the downloaded file in any browser and press **Ctrl + P** to "
                       "print it or save it as PDF. The document is fully self-contained "
                       "and carries signature blocks for the developer, the Governance "
                       "Officer and the Administrator.")

        components.html(html_doc, height=760, scrolling=True)


# =================================================================================
# 17. PAGE - USER MANAGEMENT  (Admin)
# =================================================================================
def page_users() -> None:
    platform_header(
        "User and Role Management",
        "Create accounts, assign roles and manage access to the platform",
        badge="ADMINISTRATOR",
    )

    if not auth.require_permission("manage_users"):
        return

    users = auth.list_users()
    active = len([u for u in users if int(u["is_active"])])
    by_role: dict[str, int] = {}
    for user in users:
        by_role[user["role"]] = by_role.get(user["role"], 0) + 1

    c1, c2, c3 = st.columns(3, gap="small")
    c1.metric("Total accounts", len(users))
    c2.metric("Active", active)
    c3.metric("Deactivated", len(users) - active)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    tab_list, tab_create, tab_manage = st.tabs(
        ["👥 All accounts", "➕ Create account", "🔧 Manage access"]
    )

    # ---------------- list -------------------------------------------------
    with tab_list:
        frame = pd.DataFrame([
            {
                "User ID": int(u["user_id"]),
                "Full name": u["full_name"],
                "Email": u["email"],
                "Role": auth.ROLE_LABELS.get(u["role"], u["role"]),
                "Responsibility": u.get("organization") or "—",
                "AI systems": int(u.get("system_count") or 0),
                "Status": "Active" if int(u["is_active"]) else "Deactivated",
                "Created": audit_logger.format_timestamp(u["created_at"]),
            }
            for u in users
        ])
        st.dataframe(frame, hide_index=True, **FULL_WIDTH)
        st.download_button("⬇️ Export user list as CSV",
                           data=frame.to_csv(index=False).encode("utf-8"),
                           file_name="platform_users.csv", mime="text/csv")

    # ---------------- create -----------------------------------------------
    with tab_create:
        with st.form("create_user_form", clear_on_submit=True):
            col_a, col_b = st.columns(2, gap="medium")
            with col_a:
                full_name = st.text_input("Full name *", placeholder="e.g. Amina Yusuf")
                email = st.text_input("Email address *", placeholder="amina@startup.ng")
            with col_b:
                role = st.selectbox("Role *", auth.ROLES,
                                    format_func=lambda r: auth.ROLE_LABELS.get(r, r))
                organization = st.text_input("Responsibility / department",
                                             placeholder="e.g. Data Science")
            password = st.text_input("Temporary password *", type="password",
                                     help="At least 6 characters. The user should change "
                                          "this after first sign-in.")
            if st.form_submit_button("👤 Create account", type="primary", **FULL_WIDTH):
                ok, message = auth.create_user(email, password, full_name, role,
                                               organization)
                if ok:
                    new_user = db.fetch_one("SELECT user_id FROM users WHERE email = ?",
                                            (email.strip().lower(),))
                    audit_logger.log_action(
                        auth.current_user_id(), "USER_CREATED", "user",
                        new_user["user_id"] if new_user else None,
                        f"Created account for {full_name} ({email}) with role "
                        f"{auth.ROLE_LABELS.get(role, role)}.",
                    )
                notify("success" if ok else "error", message)
                st.rerun()

        if password:
            score, label = auth.password_strength(password)
            st.progress(score / 4, text=f"Password strength: {label}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.caption("The role determines exactly which pages and actions the user can "
                   "reach. See the permission matrix on the ⚙️ Settings page.")

    # ---------------- manage -----------------------------------------------
    with tab_manage:
        if not users:
            st.info("No accounts to manage.")
            return

        options = {f"{u['full_name']} · {u['email']}": int(u["user_id"]) for u in users}
        picked = st.selectbox("Select an account", list(options.keys()))
        user_id = options[picked]
        target = safe_fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,),
                                "the account")
        if not target:
            return

        info_col, action_col = st.columns([1, 1], gap="medium")
        with info_col:
            st.markdown(
                f"""
                <div class="ag-card">
                    <div class="title">{html_lib.escape(target['full_name'])}</div>
                    <div class="sub">
                        {html_lib.escape(target['email'])}<br>
                        Role: {html_lib.escape(auth.ROLE_LABELS.get(target['role'], target['role']))}<br>
                        Responsibility: {html_lib.escape(str(target.get('organization') or '—'))}<br>
                        Status: {'✅ Active' if int(target['is_active']) else '🚫 Deactivated'}<br>
                        Created: {html_lib.escape(audit_logger.format_timestamp(target['created_at']))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with action_col:
            new_role = st.selectbox(
                "Change role", auth.ROLES,
                index=auth.ROLES.index(target["role"]),
                format_func=lambda r: auth.ROLE_LABELS.get(r, r),
                key=f"role_{user_id}",
            )
            if st.button("🔄 Apply role change", **FULL_WIDTH):
                ok, message = auth.change_role(user_id, new_role)
                if ok:
                    audit_logger.log_action(
                        auth.current_user_id(), "USER_ROLE_CHANGED", "user", user_id,
                        message,
                    )
                notify("success" if ok else "error", message)
                st.rerun()

            is_active = bool(int(target["is_active"]))
            label = "🚫 Deactivate account" if is_active else "✔️ Activate account"
            if st.button(label, **FULL_WIDTH):
                ok, message = auth.set_user_active(user_id, not is_active)
                if ok:
                    audit_logger.log_action(
                        auth.current_user_id(),
                        "USER_ACTIVATED" if not is_active else "USER_DEACTIVATED",
                        "user", user_id, message,
                    )
                notify("success" if ok else "error", message)
                st.rerun()

            new_password = st.text_input("Reset password to", type="password",
                                         key=f"pwd_{user_id}")
            if st.button("🔑 Reset password", **FULL_WIDTH, disabled=not new_password):
                ok, message = auth.reset_password(user_id, new_password)
                if ok:
                    audit_logger.log_action(
                        auth.current_user_id(), "PASSWORD_RESET", "user", user_id,
                        f"Password reset for {target['full_name']}.",
                    )
                notify("success" if ok else "error", message)
                st.rerun()

        st.warning(
            "⚠️ Accounts are **deactivated, never deleted**. The audit trail references "
            "user IDs, so deleting a user would destroy the traceability that makes the "
            "framework auditable. This is a deliberate control."
        )


# =================================================================================
# 18. PAGE - SETTINGS  (Admin)
# =================================================================================
def page_settings() -> None:
    platform_header(
        "Platform Settings",
        "Framework configuration, role permissions and database health",
        badge="ADMINISTRATOR",
    )

    if not auth.require_permission("view_settings"):
        return

    tab_framework, tab_roles, tab_health = st.tabs(
        ["📐 Framework configuration", "🔐 Role permissions", "🩺 Database health"]
    )

    # ---------------- framework --------------------------------------------
    with tab_framework:
        section("📐 Risk scoring model")
        st.markdown(f"**{rc.formula_text()}**")
        st.dataframe(
            pd.DataFrame([
                {"Risk dimension": rc.DIMENSION_LABELS[key],
                 "Weight": f"{value:.2f}",
                 "Weight %": f"{value * 100:.0f}%",
                 "What it measures": rc.DIMENSION_HELP[key]}
                for key, value in rc.WEIGHTS.items()
            ]),
            hide_index=True, **FULL_WIDTH,
        )
        st.caption(f"Total of all weights = {sum(rc.WEIGHTS.values()):.2f}. The weights "
                   f"sum to exactly 1.00, so a risk score is always on the same 0–100 "
                   f"scale as its inputs.")

        section("🚦 Risk bands")
        st.dataframe(
            pd.DataFrame([
                {"Risk band": level, "Score range": rc.risk_level_meta(level)["range"],
                 "Governance expectation": rc.risk_level_meta(level)["advice"]}
                for level in rc.RISK_LEVELS
            ]),
            hide_index=True, **FULL_WIDTH,
        )

        section("⚖️ Ethical requirements")
        st.dataframe(
            pd.DataFrame([
                {"Requirement": q["label"],
                 "Classification": "Critical" if q["critical"] else "Standard",
                 "Question": q["question"]}
                for q in rc.ETHICS_QUESTIONS
            ]),
            hide_index=True, **FULL_WIDTH,
        )
        st.caption("Yes = 1.0 · Partial = 0.5 · No = 0.0 · Not Applicable is excluded. "
                   "Two or more critical failures force a Rejected recommendation; one "
                   "critical failure caps the outcome at Needs Improvement. "
                   "≥ 85% compliance is required for an Approved recommendation.")

        section("📜 Regulatory alignment")
        st.markdown(
            f"""
            * **{REGULATORY_LINE}**
            * The framework requires a **named accountable person** for every AI system
              (accountability requirement).
            * Personal data must be **minimised, purpose-limited and protected**, in line
              with the Nigeria Data Protection Act 2023 (privacy requirement).
            * Decisions affecting individuals must be **explainable and open to human
              review** (explainability and human oversight requirements).
            * Every governance action is **logged immutably** so it can be produced as
              evidence to a regulator or an internal auditor.
            """
        )

    # ---------------- roles -------------------------------------------------
    with tab_roles:
        section("🔐 Permission matrix")
        rows: list[dict] = []
        for permission in sorted(auth.ALL_PERMISSIONS):
            row = {"Permission": auth.PERMISSION_LABELS.get(permission, permission)}
            for role in auth.ROLES:
                row[auth.ROLE_LABELS[role].split(" (")[0]] = (
                    "✅" if permission in auth.ROLE_PERMISSIONS[role] else "—"
                )
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), hide_index=True, height=560, **FULL_WIDTH)

        section("👥 Role descriptions")
        for role in auth.ROLES:
            st.markdown(
                f"""
                <div class="ag-card">
                    <div class="title">{auth.ROLE_ICONS.get(role, '👤')}
                        {html_lib.escape(auth.ROLE_LABELS[role])}</div>
                    <div class="body">{html_lib.escape(auth.ROLE_DESCRIPTIONS[role])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.info("**Separation of duties.** A Developer can register systems and complete "
                "assessments but carries no approval permission. A Governance Officer can "
                "approve, return or reject but cannot edit a developer's assessments. Only "
                "an Administrator can approve High and Critical risk systems. No single "
                "role can both create and approve the same AI system.")

    # ---------------- health ------------------------------------------------
    with tab_health:
        counts = db.table_counts()
        section("🩺 Database health")
        c1, c2, c3 = st.columns(3, gap="small")
        c1.metric("Database file", db.DB_FILENAME)
        try:
            size_kb = db.DB_PATH.stat().st_size / 1024.0
        except OSError:
            size_kb = 0.0
        c2.metric("Size on disk", f"{size_kb:,.0f} kB")
        c3.metric("Total records", f"{sum(counts.values()):,}")

        st.dataframe(
            pd.DataFrame([{"Table": table, "Rows": count}
                          for table, count in counts.items()]),
            hide_index=True, **FULL_WIDTH,
        )

        pragmas = []
        for pragma, label in (("journal_mode", "Journal mode (WAL = safe concurrent access)"),
                              ("foreign_keys", "Foreign key enforcement"),
                              ("busy_timeout", "Write-lock wait (ms)")):
            try:
                value = db.fetch_scalar(f"PRAGMA {pragma}", default="—")
            except db.DatabaseError:
                value = "—"
            pragmas.append({"Setting": label, "Value": str(value)})
        st.dataframe(pd.DataFrame(pragmas), hide_index=True, **FULL_WIDTH)

        st.caption(f"Database location: `{db.DB_PATH}` — a single local SQLite file. "
                   f"No cloud service or paid API is used anywhere in this platform.")

        section("🧪 Demonstration data")
        st.warning("⚠️ Rebuilding the demonstration data will **delete all governance "
                   "records** and restore the seeded example organisation "
                   "(PayLink Nigeria Ltd). Use this only to reset the demonstration.")
        confirm = st.checkbox("I understand that this deletes all current records")
        if st.button("♻️ Rebuild demonstration data", disabled=not confirm):
            try:
                import setup_db

                setup_db.drop_tables()
                setup_db.create_tables()
                setup_db.seed_users()
                setup_db.seed_systems()
                setup_db.seed_risk_assessments()
                setup_db.seed_ethical_assessments()
                setup_db.seed_approvals()
                setup_db.seed_incidents()
                setup_db.seed_audit_logs()
                audit_logger.log_action(
                    auth.current_user_id(), "DATA_SEEDED", "platform", None,
                    "Demonstration data rebuilt by the Administrator.",
                )
                notify("success", "Demonstration data rebuilt successfully.")
                auth.logout_user()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"⛔ Could not rebuild the data: {exc}")


# =================================================================================
# 19. APPLICATION ENTRY POINT
# =================================================================================
# The page registry is filled here, after every page function has been defined.
PAGE_REGISTRY.update({
    "📊 Compliance Dashboard": (page_dashboard,
                                ("view_dashboard", "view_own_systems", "report_incident")),
    "🗂️ AI Inventory": (page_inventory, ("view_own_systems", "view_all_systems")),
    "➕ Register AI System": (page_register_system, ("register_system",)),
    "📝 Risk Assessment": (page_risk_assessment, ("assess_risk",)),
    "⚖️ Ethical Assessment": (page_ethical_assessment, ("assess_ethics",)),
    "✅ Review Submissions": (page_review, ("review_submissions",)),
    "🚨 Incidents": (page_incidents, ("report_incident",)),
    "📄 Reports": (page_reports, ("generate_reports",)),
    "🕵️ Audit Trail": (page_audit, ("view_audit",)),
    "👥 User Management": (page_users, ("manage_users",)),
    "⚙️ Settings": (page_settings, ("view_settings",)),
})


def ensure_database() -> bool:
    """
    Guarantee that the database exists before the UI is drawn.

    On a fresh machine or a fresh clone the schema is created and seeded
    automatically, so the demonstration never fails to start.
    """
    try:
        if not db.database_exists():
            import setup_db

            setup_db.create_tables()
            setup_db.seed_users()
            setup_db.seed_systems()
            setup_db.seed_risk_assessments()
            setup_db.seed_ethical_assessments()
            setup_db.seed_approvals()
            setup_db.seed_incidents()
            setup_db.seed_audit_logs()
        return True
    except Exception as exc:  # noqa: BLE001 - report and continue
        st.error(
            "⛔ The governance database could not be initialised.\n\n"
            f"Reason: {exc}\n\n"
            "Run `python setup_db.py` in the project folder, then reload this page."
        )
        return False


def render_shell() -> None:
    """Signed-in shell: sidebar, page dispatch and error handling."""
    flush_toasts()
    selected = render_sidebar()
    page_function = PAGE_REGISTRY.get(selected, (None, ()))[0]
    if page_function is None:  # pragma: no cover - defensive
        st.error("That page is not available.")
        return

    try:
        page_function()
    except db.DatabaseError as exc:
        st.error(f"⛔ Database error on this page. {exc}")
        st.caption("If the problem persists, an Administrator can rebuild the "
                   "demonstration data from ⚙️ Settings.")
    except Exception as exc:  # noqa: BLE001 - keep the platform alive
        st.error(f"⛔ An unexpected error occurred while rendering '{selected}'.")
        with st.expander("Technical details (for troubleshooting)"):
            import traceback

            st.code(traceback.format_exc(), language="text")
        st.caption(f"Error summary: {exc}")

    st.markdown(
        f"""
        <div style="text-align:center;color:#90a4ae;font-size:11px;margin-top:24px;
                    border-top:1px solid #eceff1;padding-top:11px">
            {html_lib.escape(PLATFORM_NAME)} · v{APP_VERSION}<br>
            {html_lib.escape(REGULATORY_LINE)}<br>
            Demonstration prototype — the seeded organisation and its AI systems are
            fictional.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Application entry point."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    if not ensure_database():
        return

    if not auth.is_authenticated():
        render_login()
        return

    # Safe re-authentication: if the account was deactivated while a session was
    # open, the session is ended rather than continuing with stale authority.
    fresh = db.fetch_one("SELECT is_active, role, full_name FROM users WHERE user_id = ?",
                         (auth.current_user_id(),))
    if not fresh or not int(fresh.get("is_active", 0)):
        auth.logout_user()
        st.warning("⚠️ Your session has ended because the account was deactivated.")
        render_login()
        return

    render_shell()


if __name__ == "__main__":
    main()
