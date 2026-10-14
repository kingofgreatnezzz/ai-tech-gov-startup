"""
setup_db.py
=================================================================================
Database creation and seeding
Ethical Guideline and Governance Framework for AI Use in Nigerian Tech Startups
=================================================================================

Run once before starting the application:

    python setup_db.py            create tables, seed only if empty
    python setup_db.py --reset    drop everything and rebuild with fresh demo data
    python setup_db.py --no-seed  create empty tables only

It is safe to re-run: seeding only happens when a table is empty, so live
governance records are never overwritten by the demonstration data.

TABLES
------
    users                 accounts, roles and organisations
    ai_systems            the AI inventory
    risk_assessments      weighted risk scores (see risk_calculator.py)
    ethical_assessments   the eight ethical requirements
    approvals             governance decisions
    incidents             AI-related incident reports
    audit_logs            append-only trail of every governance action

DEMONSTRATION DATA
------------------
The seed data describes a fictional Nigerian fintech startup, **PayLink Nigeria
Ltd**, which operates three AI systems.  The scenarios are drawn from the kinds
of AI governance questions that Nigerian startups actually face under the
Nigeria Data Protection Act 2023 and the National AI Strategy: a customer-facing
chatbot, an automated credit decisioning model, and an HR analytics tool.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

import auth
import db
import risk_calculator as rc

# ---------------------------------------------------------------------
# The organisation used throughout the demonstration
# ---------------------------------------------------------------------
DEMO_ORGANISATION = "PayLink Nigeria Ltd"

# ---------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------
SCHEMA_SQL = """
-- ==================================================================
-- 1. USERS
--    Accounts are deactivated rather than deleted, because the audit
--    trail references user_id and deleting a user would destroy the
--    traceability that makes the framework auditable.
-- ==================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN
                      ('Admin', 'GovernanceOfficer', 'Developer', 'Auditor', 'Reporter')),
    organization  TEXT,
    is_active     BOOLEAN DEFAULT 1,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================================
-- 2. AI SYSTEMS  (the AI inventory / register)
-- ==================================================================
CREATE TABLE IF NOT EXISTS ai_systems (
    system_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    system_name       TEXT NOT NULL,
    purpose           TEXT,
    technology_type   TEXT,
    data_sources      TEXT,
    affected_users    TEXT,
    owner_id          INTEGER REFERENCES users (user_id),
    deployment_status TEXT CHECK (deployment_status IN
                          ('Development', 'Testing', 'Production', 'Retired')),
    governance_status TEXT CHECK (governance_status IN
                          ('Draft', 'Submitted', 'UnderReview', 'Approved',
                           'Returned', 'Rejected')),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================================
-- 3. RISK ASSESSMENTS
--    total_risk_score is computed by risk_calculator.calculate_risk_score()
--    so that the stored value can never drift from the published formula.
-- ==================================================================
CREATE TABLE IF NOT EXISTS risk_assessments (
    assessment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id        INTEGER REFERENCES ai_systems (system_id) ON DELETE CASCADE,
    impact_score     REAL NOT NULL,
    likelihood_score REAL NOT NULL,
    privacy_score    REAL NOT NULL,
    fairness_score   REAL NOT NULL,
    security_score   REAL NOT NULL,
    autonomy_score   REAL NOT NULL,
    total_risk_score REAL NOT NULL,
    risk_level       TEXT NOT NULL CHECK (risk_level IN
                         ('Low', 'Moderate', 'High', 'Critical')),
    assessed_by      INTEGER REFERENCES users (user_id),
    assessment_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================================
-- 4. ETHICAL IMPACT ASSESSMENTS  (the eight ethical requirements)
-- ==================================================================
CREATE TABLE IF NOT EXISTS ethical_assessments (
    ethics_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id                INTEGER REFERENCES ai_systems (system_id) ON DELETE CASCADE,
    fairness_response        TEXT,
    privacy_response         TEXT,
    transparency_response    TEXT,
    accountability_response  TEXT,
    oversight_response       TEXT,
    security_response        TEXT,
    explainability_response  TEXT,
    accessibility_response   TEXT,
    recommendation           TEXT CHECK (recommendation IN
                                 ('Approved', 'NeedsImprovement', 'Rejected')),
    assessed_by              INTEGER REFERENCES users (user_id),
    assessment_date          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================================
-- 5. APPROVALS  (governance decisions - the separation-of-duties record)
-- ==================================================================
CREATE TABLE IF NOT EXISTS approvals (
    approval_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id     INTEGER REFERENCES ai_systems (system_id) ON DELETE CASCADE,
    decision      TEXT CHECK (decision IN ('Approved', 'Returned', 'Rejected')),
    comments      TEXT,
    reviewer_id   INTEGER REFERENCES users (user_id),
    decision_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================================
-- 6. INCIDENTS
-- ==================================================================
CREATE TABLE IF NOT EXISTS incidents (
    incident_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id         INTEGER REFERENCES ai_systems (system_id) ON DELETE CASCADE,
    incident_type     TEXT,
    severity          TEXT CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
    description       TEXT,
    affected_parties  TEXT,
    status            TEXT CHECK (status IN
                          ('Reported', 'UnderInvestigation', 'Resolved', 'Closed')),
    corrective_action TEXT,
    reported_by       INTEGER REFERENCES users (user_id),
    reported_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at       TIMESTAMP
);

-- ==================================================================
-- 7. AUDIT LOGS  (append-only; no update or delete is ever issued)
-- ==================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users (user_id),
    action_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id   INTEGER,
    details     TEXT,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================================================================
-- Indexes for the queries the dashboard and the pages perform most
-- ==================================================================
CREATE INDEX IF NOT EXISTS idx_systems_owner      ON ai_systems (owner_id);
CREATE INDEX IF NOT EXISTS idx_systems_govstatus  ON ai_systems (governance_status);
CREATE INDEX IF NOT EXISTS idx_systems_deploy     ON ai_systems (deployment_status);
CREATE INDEX IF NOT EXISTS idx_systems_created    ON ai_systems (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_system        ON risk_assessments (system_id);
CREATE INDEX IF NOT EXISTS idx_ethics_system      ON ethical_assessments (system_id);
CREATE INDEX IF NOT EXISTS idx_approvals_system   ON approvals (system_id);
CREATE INDEX IF NOT EXISTS idx_incidents_system   ON incidents (system_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status   ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_reporter ON incidents (reported_by);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp    ON audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user         ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity       ON audit_logs (entity_type, entity_id);
"""


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ts(days: float = 0, minutes: float = 0) -> str:
    """UTC timestamp string, offset backwards from now."""
    return (_utc_now() - timedelta(days=days, minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")


def _table_count(table: str) -> int:
    try:
        return int(db.fetch_scalar(f"SELECT COUNT(*) FROM {table}", default=0) or 0)
    except db.DatabaseError:
        return 0


# ---------------------------------------------------------------------
# Seeding - users
# ---------------------------------------------------------------------
SEED_USERS = [
    ("admin@startup.ng", "admin123", "Ngozi Adeyemi", auth.ROLE_ADMIN,
     "Chief Technology Officer"),
    ("governance@startup.ng", "gov123", "Ibrahim Musa", auth.ROLE_GOVERNANCE,
     "Head of Compliance and AI Governance"),
    ("dev@startup.ng", "dev123", "Chinedu Okafor", auth.ROLE_DEVELOPER,
     "Machine Learning Engineer"),
    ("auditor@startup.ng", "audit123", "Fatima Bello", auth.ROLE_AUDITOR,
     "Internal Audit"),
    ("reporter@startup.ng", "rep123", "Tunde Balogun", auth.ROLE_REPORTER,
     "Customer Support Officer"),
]


def seed_users(force: bool = False) -> None:
    """Create the five role accounts used by the demonstration."""
    if _table_count("users") > 0 and not force:
        print("  [--] users already populated - skipped.")
        return

    for index, (email, password, full_name, role, organization) in enumerate(SEED_USERS):
        db.execute_query(
            """
            INSERT OR IGNORE INTO users
                (email, password_hash, full_name, role, organization, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (email, auth.hash_password(password), full_name, role,
             organization, _ts(days=90 - index)),
        )

    print(f"  [OK] Seeded {len(SEED_USERS)} user accounts (one per role).")
    for email, password, full_name, role, _org in SEED_USERS:
        print(f"        {email:<26} {password:<10} {auth.ROLE_LABELS[role]}")


# ---------------------------------------------------------------------
# Seeding - AI systems
# ---------------------------------------------------------------------
#: (name, purpose, technology, data sources, affected users, deployment status,
#:  governance status, age in days)
SEED_SYSTEMS = [
    (
        "Customer Support Chatbot",
        "An NLP assistant on the website and WhatsApp that answers customer "
        "questions about balances, transaction charges and how to reset a "
        "password. It deflects routine enquiries away from the support queue.",
        "Natural Language Processing",
        "Personal Data; Conversation Logs; Transaction Metadata",
        "Customers; Support Agents",
        "Production",
        "Approved",
        62,
    ),
    (
        "Loan Approval Algorithm",
        "A machine learning model that scores loan applications and recommends "
        "approve, decline or manual review. It influences whether a customer "
        "receives credit and on what terms.",
        "Machine Learning",
        "Financial Data; Personal Data; Credit History; Alternative Data",
        "Customers; Loan Applicants; General Public",
        "Testing",
        "UnderReview",
        40,
    ),
    (
        "Employee Performance Analyzer",
        "An HR analytics tool that scores staff productivity from system logs, "
        "ticket resolution times and peer feedback, and flags employees for "
        "performance improvement plans.",
        "Machine Learning; Data Analytics",
        "Employee Data; Productivity Metrics; Peer Feedback",
        "Employees",
        "Development",
        "Submitted",
        18,
    ),
]


def seed_systems(force: bool = False) -> None:
    """Register the three demonstration AI systems."""
    if _table_count("ai_systems") > 0 and not force:
        print("  [--] ai_systems already populated - skipped.")
        return

    developer = db.fetch_one("SELECT user_id FROM users WHERE email = ?",
                             ("dev@startup.ng",))
    owner_id = developer["user_id"] if developer else None

    for (name, purpose, technology, data_sources, affected_users,
         deployment, governance, age_days) in SEED_SYSTEMS:
        db.execute_query(
            """
            INSERT INTO ai_systems
                (system_name, purpose, technology_type, data_sources, affected_users,
                 owner_id, deployment_status, governance_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, purpose, technology, data_sources, affected_users, owner_id,
             deployment, governance, _ts(days=age_days), _ts(days=max(0, age_days - 4))),
        )

    print(f"  [OK] Seeded {len(SEED_SYSTEMS)} AI systems.")


# ---------------------------------------------------------------------
# Seeding - risk assessments
# ---------------------------------------------------------------------
#: (system name, impact, likelihood, privacy, fairness, security, autonomy,
#:  days ago)  -- the total and the band are computed, never hard-coded.
SEED_RISK = [
    ("Customer Support Chatbot", 15, 20, 25, 15, 20, 10, 60),
    ("Loan Approval Algorithm", 75, 50, 65, 60, 55, 70, 36),
]


def seed_risk_assessments(force: bool = False) -> None:
    """
    Complete two risk assessments.

    The score and band are produced by :mod:`risk_calculator`, so the seeded
    data is guaranteed to be consistent with the published formula.
    """
    if _table_count("risk_assessments") > 0 and not force:
        print("  [--] risk_assessments already populated - skipped.")
        return

    developer = db.fetch_one("SELECT user_id FROM users WHERE email = ?", ("dev@startup.ng",))
    assessed_by = developer["user_id"] if developer else None

    for (system_name, impact, likelihood, privacy, fairness, security,
         autonomy, days_ago) in SEED_RISK:
        system = db.fetch_one("SELECT system_id FROM ai_systems WHERE system_name = ?",
                              (system_name,))
        if not system:
            continue

        total = rc.calculate_risk_score(impact, likelihood, privacy,
                                        fairness, security, autonomy)
        level = rc.determine_risk_level(total)

        db.execute_query(
            """
            INSERT INTO risk_assessments
                (system_id, impact_score, likelihood_score, privacy_score,
                 fairness_score, security_score, autonomy_score,
                 total_risk_score, risk_level, assessed_by, assessment_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (system["system_id"], impact, likelihood, privacy, fairness, security,
             autonomy, total, level, assessed_by, _ts(days=days_ago)),
        )
        print(f"        {system_name:<30} score {total:>5.1f}  [{level}]")

    print(f"  [OK] Seeded {len(SEED_RISK)} risk assessments.")


# ---------------------------------------------------------------------
# Seeding - ethical assessments
# ---------------------------------------------------------------------
#: (system name, responses dict, days ago)
SEED_ETHICS = [
    (
        "Customer Support Chatbot",
        {
            "fairness_response": "Yes",
            "privacy_response": "Yes",
            "transparency_response": "Yes",
            "accountability_response": "Yes",
            "oversight_response": "Yes",
            "security_response": "Yes",
            "explainability_response": "Yes",
            "accessibility_response": "Partial",
        },
        58,
    ),
    (
        "Loan Approval Algorithm",
        {
            "fairness_response": "Partial",
            "privacy_response": "Yes",
            "transparency_response": "No",
            "accountability_response": "Yes",
            "oversight_response": "Partial",
            "security_response": "Yes",
            "explainability_response": "Partial",
            "accessibility_response": "Not Applicable",
        },
        34,
    ),
]


def seed_ethical_assessments(force: bool = False) -> None:
    """Complete two ethical impact assessments."""
    if _table_count("ethical_assessments") > 0 and not force:
        print("  [--] ethical_assessments already populated - skipped.")
        return

    developer = db.fetch_one("SELECT user_id FROM users WHERE email = ?", ("dev@startup.ng",))
    assessed_by = developer["user_id"] if developer else None

    for system_name, responses, days_ago in SEED_ETHICS:
        system = db.fetch_one("SELECT system_id FROM ai_systems WHERE system_name = ?",
                              (system_name,))
        if not system:
            continue

        recommendation, reasoning = rc.determine_ethical_recommendation(responses)
        score, earned, possible = rc.calculate_ethics_score(responses)

        db.execute_query(
            """
            INSERT INTO ethical_assessments
                (system_id, fairness_response, privacy_response, transparency_response,
                 accountability_response, oversight_response, security_response,
                 explainability_response, accessibility_response, recommendation,
                 assessed_by, assessment_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (system["system_id"], responses["fairness_response"],
             responses["privacy_response"], responses["transparency_response"],
             responses["accountability_response"], responses["oversight_response"],
             responses["security_response"], responses["explainability_response"],
             responses["accessibility_response"], recommendation,
             assessed_by, _ts(days=days_ago)),
        )
        print(f"        {system_name:<30} {recommendation} "
              f"({score * 100:.0f}% compliance)")

    print(f"  [OK] Seeded {len(SEED_ETHICS)} ethical assessments.")


# ---------------------------------------------------------------------
# Seeding - approval decisions
# ---------------------------------------------------------------------
def seed_approvals(force: bool = False) -> None:
    """Record the governance decision on the chatbot."""
    if _table_count("approvals") > 0 and not force:
        print("  [--] approvals already populated - skipped.")
        return

    reviewer = db.fetch_one("SELECT user_id FROM users WHERE email = ?",
                            ("governance@startup.ng",))
    reviewer_id = reviewer["user_id"] if reviewer else None
    system = db.fetch_one("SELECT system_id FROM ai_systems WHERE system_name = ?",
                          ("Customer Support Chatbot",))
    if not system:
        print("  [--] chatbot not found - approvals skipped.")
        return

    db.execute_query(
        """
        INSERT INTO approvals (system_id, decision, comments, reviewer_id, decision_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            system["system_id"],
            "Approved",
            "Approved. The system operates in a low-risk advisory capacity, it does not "
            "make binding decisions about customers, personal data is minimised, and a "
            "human agent can take over any conversation. The accessibility gap identified "
            "during assessment (Partially met) should be closed within 90 days. "
            "Conditions: publish a clear AI disclosure on the chat widget, and retain "
            "conversation logs for no longer than 12 months in line with NDPA 2023.",
            reviewer_id,
            _ts(days=52),
        ),
    )
    print("  [OK] Seeded 1 approval decision (Customer Support Chatbot - Approved).")


# ---------------------------------------------------------------------
# Seeding - incidents
# ---------------------------------------------------------------------
#: (system name, type, severity, description, affected parties, status,
#:  corrective action, reporter email, days ago)
SEED_INCIDENTS = [
    (
        "Loan Approval Algorithm",
        "Bias/Discrimination",
        "High",
        "Analysis of the last quarter's decisions showed that applicants whose "
        "address fell within three northern states were declined at 2.4 times the "
        "rate of applicants with comparable income and credit history. The model "
        "appears to be using address as a proxy for other characteristics.",
        "Loan applicants from three northern states; affected communities",
        "UnderInvestigation",
        "Model retrained without the address feature. Independent fairness audit "
        "commissioned. All affected applicants from the period are being reviewed "
        "manually and a remediation plan is with the Governance Officer.",
        "reporter@startup.ng",
        16,
    ),
    (
        "Customer Support Chatbot",
        "Data Breach",
        "Critical",
        "A misconfigured log export placed 4 812 chat transcripts in a publicly "
        "readable cloud bucket for approximately nine hours. Some transcripts "
        "contained account numbers and partial card details quoted by customers.",
        "4 812 customers; the organisation",
        "UnderInvestigation",
        "Bucket access revoked within 20 minutes of detection. Affected customers "
        "notified. Nigeria Data Protection Commission being notified as required. "
        "Full forensic review of logging configuration in progress.",
        "reporter@startup.ng",
        6,
    ),
]


def seed_incidents(force: bool = False) -> None:
    """Report two realistic AI incidents."""
    if _table_count("incidents") > 0 and not force:
        print("  [--] incidents already populated - skipped.")
        return

    for (system_name, incident_type, severity, description, affected_parties,
         status, corrective_action, reporter_email, days_ago) in SEED_INCIDENTS:
        system = db.fetch_one("SELECT system_id FROM ai_systems WHERE system_name = ?",
                              (system_name,))
        reporter = db.fetch_one("SELECT user_id FROM users WHERE email = ?",
                                (reporter_email,))
        db.execute_query(
            """
            INSERT INTO incidents
                (system_id, incident_type, severity, description, affected_parties,
                 status, corrective_action, reported_by, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (system["system_id"] if system else None, incident_type, severity,
             description, affected_parties, status, corrective_action,
             reporter["user_id"] if reporter else None, _ts(days=days_ago)),
        )

    print(f"  [OK] Seeded {len(SEED_INCIDENTS)} incidents.")


# ---------------------------------------------------------------------
# Seeding - audit trail
# ---------------------------------------------------------------------
def seed_audit_logs(force: bool = False) -> None:
    """
    Build a coherent audit trail that matches the seeded records.

    The entries are written in chronological order so that the timestamps read
    as a story: systems registered, assessments completed, the chatbot approved,
    and the two incidents reported.
    """
    if _table_count("audit_logs") > 0 and not force:
        print("  [--] audit_logs already populated - skipped.")
        return

    users = {row["email"]: row["user_id"]
             for row in db.fetch_all("SELECT user_id, email FROM users")}
    systems = {row["system_name"]: row["system_id"]
               for row in db.fetch_all("SELECT system_id, system_name FROM ai_systems")}

    dev = users.get("dev@startup.ng")
    gov = users.get("governance@startup.ng")
    adm = users.get("admin@startup.ng")
    rep = users.get("reporter@startup.ng")
    aud = users.get("auditor@startup.ng")

    chatbot = systems.get("Customer Support Chatbot")
    loan = systems.get("Loan Approval Algorithm")
    hr = systems.get("Employee Performance Analyzer")

    # (user_id, action, entity_type, entity_id, details, days_ago)
    entries = [
        (adm, "DATA_SEEDED", "platform", None,
         "Governance platform initialised for PayLink Nigeria Ltd. Framework aligned "
         "to the Nigeria Data Protection Act 2023 and the National AI Strategy.", 91),
        (adm, "USER_CREATED", "user", users.get("governance@startup.ng"),
         "Created governance account for Ibrahim Musa (AI Governance Officer).", 90),
        (adm, "USER_CREATED", "user", dev,
         "Created developer account for Chinedu Okafor (Machine Learning Engineer).", 90),
        (dev, "SYSTEM_CREATED", "ai_system", chatbot,
         "Registered 'Customer Support Chatbot' (Natural Language Processing). "
         "Deployment status: Production.", 62),
        (dev, "RISK_ASSESSED", "ai_system", chatbot,
         "Risk assessment completed. Weighted score 17.5 - Low risk.", 60),
        (dev, "ETHICS_ASSESSED", "ai_system", chatbot,
         "Ethical impact assessment completed. Recommendation: Approved.", 58),
        (dev, "SYSTEM_SUBMITTED", "ai_system", chatbot,
         "Submitted Customer Support Chatbot for governance review.", 57),
        (gov, "SYSTEM_APPROVED", "ai_system", chatbot,
         "Approved with conditions: publish an AI disclosure on the chat widget and "
         "retain conversation logs for no more than 12 months (NDPA 2023).", 52),
        (dev, "SYSTEM_CREATED", "ai_system", loan,
         "Registered 'Loan Approval Algorithm' (Machine Learning). Deployment status: "
         "Testing.", 40),
        (dev, "RISK_ASSESSED", "ai_system", loan,
         "Risk assessment completed. Weighted score 63.8 - High risk. Main drivers: "
         "impact of harm and fairness/bias concern.", 36),
        (dev, "ETHICS_ASSESSED", "ai_system", loan,
         "Ethical impact assessment completed. Recommendation: Needs Improvement "
         "(transparency requirement not met).", 34),
        (dev, "SYSTEM_SUBMITTED", "ai_system", loan,
         "Submitted Loan Approval Algorithm for governance review.", 33),
        (rep, "INCIDENT_REPORTED", "incident", 1,
         "Bias/Discrimination incident reported against the Loan Approval Algorithm: "
         "geographic disparity in decline rates. Severity: High.", 16),
        (dev, "SYSTEM_CREATED", "ai_system", hr,
         "Registered 'Employee Performance Analyzer' (Machine Learning) for HR "
         "analytics. Deployment status: Development.", 18),
        (dev, "SYSTEM_SUBMITTED", "ai_system", hr,
         "Submitted Employee Performance Analyzer for governance review. Risk and "
         "ethical assessments still outstanding.", 15),
        (rep, "INCIDENT_REPORTED", "incident", 2,
         "Data Breach incident reported against the Customer Support Chatbot: 4 812 "
         "chat transcripts exposed. Severity: Critical.", 6),
        (gov, "INCIDENT_UPDATED", "incident", 2,
         "Incident moved to Under Investigation. Cloud access revoked, affected "
         "customers notified, NDPC notification in progress.", 5),
        (aud, "REPORT_GENERATED", "report", None,
         "Compliance summary report generated for internal audit review.", 3),
    ]

    for user_id, action, entity_type, entity_id, details, days_ago in entries:
        db.execute_query(
            """
            INSERT INTO audit_logs (user_id, action_type, entity_type, entity_id,
                                    details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, action, entity_type, entity_id, details, _ts(days=days_ago)),
        )

    print(f"  [OK] Seeded {len(entries)} audit trail entries.")


# ---------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------
def create_tables() -> None:
    """Create every table, index and constraint (idempotent)."""
    db.execute_script(SCHEMA_SQL)
    print("  [OK] Tables, indexes and constraints created / verified.")


def drop_tables() -> None:
    """Drop every application table (used by --reset)."""
    db.execute_script(
        """
        PRAGMA foreign_keys = OFF;
        DROP TABLE IF EXISTS audit_logs;
        DROP TABLE IF EXISTS incidents;
        DROP TABLE IF EXISTS approvals;
        DROP TABLE IF EXISTS ethical_assessments;
        DROP TABLE IF EXISTS risk_assessments;
        DROP TABLE IF EXISTS ai_systems;
        DROP TABLE IF EXISTS users;
        PRAGMA foreign_keys = ON;
        """
    )
    print("  [OK] Existing tables dropped.")


def print_summary() -> None:
    """Verification report printed after setup."""
    counts = db.table_counts()
    print("\n  Database summary")
    print("  " + "-" * 50)
    labels = {
        "users": "Users",
        "ai_systems": "AI systems registered",
        "risk_assessments": "Risk assessments",
        "ethical_assessments": "Ethical assessments",
        "approvals": "Governance decisions",
        "incidents": "Incidents",
        "audit_logs": "Audit trail entries",
    }
    for table, label in labels.items():
        print(f"  {label:<26}: {counts.get(table, 0):>4}")

    if counts.get("ai_systems"):
        print("\n  AI systems and their governance status")
        print("  " + "-" * 50)
        rows = db.fetch_all(
            """
            SELECT s.system_name, s.governance_status, s.deployment_status,
                   r.total_risk_score, r.risk_level
            FROM ai_systems s
            LEFT JOIN risk_assessments r
                   ON r.assessment_id = (SELECT MAX(assessment_id)
                                         FROM risk_assessments
                                         WHERE system_id = s.system_id)
            ORDER BY s.system_id
            """
        )
        for row in rows:
            score = (f"{row['total_risk_score']:.1f} {row['risk_level']}"
                     if row["total_risk_score"] is not None else "not assessed")
            print(f"  {row['system_name']:<30} {row['governance_status']:<12} "
                  f"{row['deployment_status']:<12} {score}")

    print(f"\n  Database file             : {db.DB_PATH}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create and seed the AI governance platform database."
    )
    parser.add_argument("--reset", action="store_true",
                        help="Drop all tables and rebuild from scratch.")
    parser.add_argument("--no-seed", action="store_true",
                        help="Create empty tables without demonstration data.")
    args = parser.parse_args(argv)

    print("=" * 70)
    print(" AI GOVERNANCE AND ETHICS PLATFORM")
    print(" Ethical Guideline and Governance Framework for Nigerian Tech Startups")
    print("=" * 70)
    print(f" Target: {db.DB_PATH}\n")

    try:
        if args.reset:
            print(" Resetting database ...")
            drop_tables()

        print(" Creating schema ...")
        create_tables()

        if args.no_seed:
            print("\n  [--] Seeding skipped (--no-seed).")
        else:
            print("\n Seeding demonstration data ...")
            seed_users()
            seed_systems()
            seed_risk_assessments()
            seed_ethical_assessments()
            seed_approvals()
            seed_incidents()
            seed_audit_logs()

        print_summary()
        print("\n Setup completed successfully.")
        print(" Next step:  streamlit run app.py")
        print("=" * 70)
        return 0

    except db.DatabaseError as exc:
        print(f"\n[ERROR] Database failure: {exc}", file=sys.stderr)
        return 1
    except rc.RiskInputError as exc:
        print(f"\n[ERROR] Risk calculation failure: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - top-level guard
        print(f"\n[ERROR] Unexpected failure: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close_connection()


if __name__ == "__main__":
    raise SystemExit(main())
