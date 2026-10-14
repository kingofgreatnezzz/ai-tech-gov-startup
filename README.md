# ⚖️ AI Governance and Ethics Platform

### Ethical Guideline and Governance Framework for Artificial Intelligence Use in Nigerian Tech Startups

A complete, offline, role-based governance platform that lets a Nigerian tech startup
**register its AI systems, score their risk, assess their ethical impact, route them
through a formal approval workflow, capture AI incidents, and keep an immutable audit
trail** — aligned with the **Nigeria Data Protection Act 2023**, NITDA guidelines and
the **National AI Strategy**.

> **100% local.** No cloud service, no paid API, no external dependency. One Python
> process, one SQLite file, one laptop.

---

## 1. Project Folder Structure

```
aigovtech/                        <- project root
│
├── app.py                     ★ THE APPLICATION - all five roles, all pages
├── setup_db.py                ★ Creates and seeds the SQLite database
├── setup_and_start.bat        ★ One-click Windows launcher
├── run_server.bat               Starts the server (called by the launcher)
├── requirements.txt           ★ Dependencies (streamlit, pandas, plotly)
├── README.md                    This file
├── DEMO_SCRIPT.txt            ★ Defence-day runbook - print this
├── DEPLOYMENT_GUIDE.md          GitHub + Streamlit Cloud deployment
│
├── auth.py                      Roles, permissions, PBKDF2 password hashing
├── db.py                        SQLite helpers, WAL, safe concurrent writes
├── risk_calculator.py         ★ The weighted risk model + ethical scoring
├── audit_logger.py            ★ Append-only audit trail
├── reports.py                   Governance report generator (HTML)
│
├── tests/
│   ├── functional_test.py       Formula, permissions, workflow, constraints
│   └── ui_smoke_test.py         All five roles, every page, full workflow
│
├── .gitignore
├── .streamlit/
│   └── config.toml              Theme and server settings
│
└── data/                        Created automatically by setup_db.py
    └── aigovtech.db           ★ THE DATABASE (SQLite)
```

---

## 2. Quick Start (Windows)

### Option A — one click

1. Double-click **`setup_and_start.bat`**
2. It chooses your Python environment, installs anything missing, builds and seeds the
   database, starts the server and opens your browser
3. Sign in at **http://localhost:8501**

```bat
setup_and_start.bat reset    REM wipe and re-seed the demo data
setup_and_start.bat fresh    REM ignore ..\myenv and build a clean local venv
```

The launcher prefers, in order: an activated virtual environment → `..\myenv` →
`.\venv` → creates a new `.\venv`.

### Option B — manual

```bat
cd C:\path\to\aigovtech
C:\path\to\myenv\Scripts\activate
pip install -r requirements.txt
python setup_db.py
streamlit run app.py
```

---

## 3. The Five Roles

| Email | Password | Role | What they can do |
|---|---|---|---|
| `admin@startup.ng` | `admin123` | **Administrator** | Everything: users, settings, audit logs, and **approval of High/Critical risk systems** |
| `governance@startup.ng` | `gov123` | **AI Governance Officer** | Review submissions, **approve / return / reject**, manage incidents, generate reports |
| `dev@startup.ng` | `dev123` | **Startup Developer** | Register AI systems, complete risk and ethical assessments, submit for review |
| `auditor@startup.ng` | `audit123` | **Auditor** | Read-only access to everything including the audit trail |
| `reporter@startup.ng` | `rep123` | **Reporter** | Any employee — file AI incidents and track only their own reports |

### Separation of duties

The developer who **builds** an AI system can never **approve** it:

```
Developer  ──registers──►  assessments  ──submits──►  GovernanceOfficer
                                                          │
                                     ┌────────────────────┼────────────────────┐
                                     ▼                    ▼                    ▼
                                  Approve              Return               Reject
                                                                  (High/Critical risk
                                                                   needs an Admin)
```

Every decision is written to the audit trail with the reviewer's identity and reason.
A **High or Critical** risk system is blocked from approval unless the user holds the
`approve_high_risk` permission — and the blocked attempt is itself logged.

### Permission matrix (abridged)

| Permission | Admin | Governance | Developer | Auditor | Reporter |
|---|:--:|:--:|:--:|:--:|:--:|
| View compliance dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| View all AI systems | ✅ | ✅ | — | ✅ | — |
| View own AI systems | ✅ | — | ✅ | — | — |
| Register / edit AI systems | ✅ | — | ✅ | — | — |
| Complete risk assessment | ✅ | — | ✅ | — | — |
| Complete ethical assessment | ✅ | — | ✅ | — | — |
| Review submissions | ✅ | ✅ | — | — | — |
| Approve / return / reject | ✅ | ✅ | — | — | — |
| Approve High/Critical risk | ✅ | — | — | — | — |
| Report an incident | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage incidents | ✅ | ✅ | — | — | — |
| View audit trail | ✅ | — | — | ✅ | — |
| Generate compliance reports | ✅ | ✅ | ✅ | ✅ | — |
| Manage users | ✅ | — | — | — | — |

---

## 4. The Risk Model

```
Risk Score = 0.30 × Impact
           + 0.20 × Likelihood
           + 0.15 × Privacy Sensitivity
           + 0.15 × Fairness / Bias Concern
           + 0.10 × Security Exposure
           + 0.10 × Autonomy / Decision Impact
```

All six inputs are 0–100. The weights **sum to exactly 1.00**, so the score stays on the
same 0–100 scale and is directly comparable between systems.

| Dimension | Weight | Why this weight |
|---|---|---|
| Impact / Severity of Harm | 0.30 | Governance is ultimately about severity of harm to people |
| Likelihood of Harm | 0.20 | A severe but improbable failure is less urgent than a frequent moderate one |
| Privacy Sensitivity | 0.15 | The NDPA 2023 focuses on unlawful processing of personal data |
| Fairness / Bias | 0.15 | Automated discrimination is the harm most often cited in AI regulation |
| Security Exposure | 0.10 | Modifies exposure rather than creating harm directly |
| Autonomy / Decision Impact | 0.10 | The less human review, the higher the residual risk |

**Risk bands**

| Band | Score | Governance expectation |
|---|---|---|
| 🟢 **Low** | 0 – 20 | Normal monitoring |
| 🟡 **Moderate** | 21 – 40 | Standard governance review before deployment |
| 🟠 **High** | 41 – 70 | Senior review; mitigation plan and human oversight must be evidenced |
| 🔴 **Critical** | 71 – 100 | Deployment halted pending remediation and executive sign-off |

**Worked example** (the demonstration values):

```
Impact 70    × 0.30 = 21.00
Likelihood 40× 0.20 =  8.00
Privacy 80   × 0.15 = 12.00
Fairness 30  × 0.15 =  4.50
Security 60  × 0.10 =  6.00
Autonomy 50  × 0.10 =  5.00
                     ------
                      56.50  →  HIGH
```

---

## 5. The Ethical Assessment

Eight requirements, each answered **Yes / Partial / No / Not Applicable**:

| Requirement | Classification |
|---|---|
| Fairness | 🔴 Critical |
| Privacy | 🔴 Critical |
| Accountability | 🔴 Critical |
| Human Oversight | 🔴 Critical |
| Transparency | Standard |
| Security | Standard |
| Explainability | Standard |
| Accessibility | Standard |

**Scoring:** Yes = 1.0 · Partial = 0.5 · No = 0.0 · *Not Applicable* is removed from the
denominator entirely.

**Decision rules:**

1. **Two or more critical "No"** → **Rejected**
2. **One critical "No"** → capped at **Needs Improvement**
3. Otherwise: **≥ 85 %** → Approved · **55–84 %** → Needs Improvement · **< 55 %** → Rejected

---

## 6. Database Schema

```
users(user_id PK, email UNIQUE, password_hash, full_name, role CHECK(Admin|
      GovernanceOfficer|Developer|Auditor|Reporter), organization, is_active, created_at)

ai_systems(system_id PK, system_name, purpose, technology_type, data_sources,
      affected_users, owner_id FK→users, deployment_status CHECK(Development|
      Testing|Production|Retired), governance_status CHECK(Draft|Submitted|
      UnderReview|Approved|Returned|Rejected), created_at, updated_at)

risk_assessments(assessment_id PK, system_id FK→ai_systems ON DELETE CASCADE,
      impact_score, likelihood_score, privacy_score, fairness_score, security_score,
      autonomy_score, total_risk_score, risk_level CHECK(Low|Moderate|High|Critical),
      assessed_by FK→users, assessment_date)

ethical_assessments(ethics_id PK, system_id FK→ai_systems ON DELETE CASCADE,
      fairness_response … accessibility_response, recommendation CHECK(Approved|
      NeedsImprovement|Rejected), assessed_by FK→users, assessment_date)

approvals(approval_id PK, system_id FK→ai_systems ON DELETE CASCADE,
      decision CHECK(Approved|Returned|Rejected), comments, reviewer_id FK→users,
      decision_date)

incidents(incident_id PK, system_id FK→ai_systems ON DELETE CASCADE, incident_type,
      severity CHECK(Low|Medium|High|Critical), description, affected_parties,
      status CHECK(Reported|UnderInvestigation|Resolved|Closed), corrective_action,
      reported_by FK→users, reported_at, resolved_at)

audit_logs(log_id PK, user_id FK→users, action_type, entity_type, entity_id,
      details, timestamp)
```

**Controls enforced by the database engine itself:**

* `PRAGMA foreign_keys = ON` on every connection, with `ON DELETE CASCADE` from
  assessments/approvals/incidents to their AI system
* `CHECK` constraints on every enumerated column — an invalid role, severity, status or
  risk level is rejected by SQLite, not merely by the interface
* `UNIQUE` on `users.email`
* **WAL journal mode** with an 8-second busy timeout and automatic retries, so two
  sessions writing at the same moment cannot lock each other out
* 13 indexes covering the queries the dashboard actually runs

---

## 7. Features

### 📊 Compliance Dashboard
Five headline metrics (systems registered · approved · pending review · open incidents ·
high/critical risk), a colour-coded risk-band strip, four interactive **Plotly** charts
(risk pie, incidents by type, registrations over time, deployment pipeline), and a
filterable, exportable AI register.

### 🗂️ AI Inventory
Searchable register with risk badges, status pills and incident counts. Open any system
for its **complete governance record**: registration, risk assessment with breakdown,
ethical assessment, decision history, incidents and its own audit trail.

### 📝 Risk Assessment
Six sliders with **live recalculation**, a full contribution breakdown table and chart,
and an explainability sentence naming the top drivers.

### ⚖️ Ethical Assessment
Eight questions with a **live recommendation** and the reasoning behind it.

### ✅ Review Submissions
One screen per submission showing registration, risk and ethics together. Approve,
Return or Reject with mandatory reasoning. Blocks High/Critical approval without the
Admin permission — and logs the attempt.

### 🚨 Incident Management
Any employee can file an incident. Scoping is enforced at the data layer: a Reporter
sees only their own reports; a Developer sees incidents on their own systems; governance
roles see everything and can update status and corrective actions.

### 🕵️ Audit Trail
Filter by user, action type, entity, date range and free text. Export to CSV. **No update
or delete function exists anywhere in the codebase.**

### 👥 User Management
Create accounts, assign roles, activate/deactivate. **Accounts are never deleted** — the
audit trail references user IDs, so deletion would destroy traceability.

### 📄 Report Generation
Three print-ready HTML documents with letterhead, timestamps and signature blocks:
AI System Governance Report · Compliance Summary Report · Incident Report.

### 📱 Responsive design
Mobile-first media queries stack the columns into a single readable column below 820 px,
enlarge touch targets and make buttons full width, so the platform is usable on a phone
as well as on a projector.

---

## 8. Automated Tests

```bat
python tests\functional_test.py     REM formula, permissions, workflow, constraints
python tests\ui_smoke_test.py       REM all five roles, every page, full workflow
```

| Suite | What it proves |
|---|---|
| `tests/functional_test.py` | The risk formula against **12 worked cases** including all six single-dimension cases; band boundaries at 20/40/70; input validation; breakdown sums; the ethical recommendation rules; PBKDF2 hashing; all five roles authenticate with the right permissions; **no non-Admin role can both register and approve**; the full register → assess → return workflow; CHECK, UNIQUE and foreign-key enforcement; the audit trail; all three report generators; and **24 simultaneous inserts with zero lock errors** |
| `tests/ui_smoke_test.py` | Every role sees **exactly** the pages its permissions allow and nothing more; every page renders with zero exceptions on every role; and the complete defence-day workflow driven through the real interface — register a system, score it, assess it ethically, have it returned by the officer, file an incident as the reporter, then read all of it back in the auditor's audit trail |

Both suites currently pass with **0 failures**.

---

## 9. Troubleshooting

| Problem | Solution |
|---|---|
| `python` not recognised | Install Python 3.10+ and tick **Add python.exe to PATH** |
| `pip install` fails | Check your internet connection or proxy |
| "database could not be initialised" | Run `python setup_db.py --reset` |
| Port 8501 in use | The launcher switches to 8502 automatically |
| Charts slow on first load | Plotly initialises on first render; click another page and return |
| Demo data messy after experiments | `setup_and_start.bat reset`, or ⚙️ Settings → Rebuild demonstration data |
| Forgot which account is active | The sidebar always shows the name and role badge |

---

## 10. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.10+ | Standard for academic prototypes |
| Web UI | Streamlit | Professional multi-page dashboards without HTML/JS |
| Database | SQLite (built into Python) | ACID, zero-configuration, fully offline |
| Data tables | Pandas | Filtering, aggregation, CSV export |
| Charts | Plotly | Interactive, responsive visualisations |
| Security | `hashlib` PBKDF2-HMAC-SHA256 | 120 000 iterations, unique salt, constant-time compare |
| Reports | HTML with inline CSS | Self-contained, printable to PDF, no paid library |

---

*Demonstration prototype. The organisation (PayLink Nigeria Ltd) and its AI systems are
fictional. All data is held in a single local SQLite file.*
#   a i - t e c h - g o v - s t a r t u p  
 