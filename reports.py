"""
reports.py
=================================================================================
Governance report generator
Ethical Guideline and Governance Framework for AI Use in Nigerian Tech Startups
=================================================================================

Produces three self-contained, print-ready HTML documents:

    1. AI System Governance Report  - the complete compliance record for ONE
                                      AI system: registration, risk assessment,
                                      ethical assessment, decision history,
                                      incidents and audit trail.
    2. Compliance Summary Report    - the portfolio view for management and the
                                      board: how many systems, at what risk,
                                      how many approved, what is outstanding.
    3. Incident Report              - the full details of one AI incident.

Each document is a complete HTML page with inline CSS and no external assets, so
it opens in any browser, prints cleanly to paper (Ctrl+P), and can be filed or
e-mailed as evidence to a regulator such as the Nigeria Data Protection
Commission without any dependency on this application still existing.
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta
from typing import Any, Optional

import audit_logger
import db
import risk_calculator as rc

# ---------------------------------------------------------------------
# Identity printed on every report
# ---------------------------------------------------------------------
PLATFORM_NAME = "AI GOVERNANCE AND ETHICS PLATFORM"
PLATFORM_TAGLINE = ("Ethical Guideline and Governance Framework for "
                    "Artificial Intelligence Use in Nigerian Tech Startups")
FRAMEWORK_REFERENCE = ("Aligned with the Nigeria Data Protection Act 2023, "
                       "NITDA Guidelines and the National AI Strategy")

STATUS_COLOURS = {
    "Draft": "#616161",
    "Submitted": "#1b4079",
    "UnderReview": "#ef6c00",
    "Approved": "#2e7d32",
    "Returned": "#f9a825",
    "Rejected": "#c62828",
}


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _wat(value: Any, with_time: bool = True) -> str:
    """Stored UTC timestamp rendered in West Africa Time (UTC+1)."""
    return audit_logger.format_timestamp(value, with_time=with_time)


# ---------------------------------------------------------------------
# Shared document shell
# ---------------------------------------------------------------------
def _document(title: str, subtitle: str, body: str, footer_note: str = "") -> str:
    """
    Wrap report content in the corporate document shell.

    All CSS is inline so the file is completely self-contained.
    """
    generated = _wat(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{_esc(title)}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    background: #eef1f5; margin: 0; padding: 20px; color: #16212b;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }}
  .sheet {{
    max-width: 900px; margin: 0 auto; background: #fff;
    border: 1px solid #c8d3de; border-radius: 8px; overflow: hidden;
    box-shadow: 0 8px 24px rgba(16,39,57,.14);
  }}
  .letterhead {{ background: linear-gradient(120deg,#0b2545 0%,#13315c 55%,#1b4079 100%);
                 color: #fff; padding: 20px 26px; border-bottom: 5px solid #ffd54f; }}
  .letterhead .platform {{ font-size: 20px; font-weight: 800; letter-spacing: 1.4px; }}
  .letterhead .tagline {{ font-size: 11.5px; color: #b8c7dc; margin-top: 4px; line-height: 1.5; }}
  .letterhead .doctype {{ font-size: 15px; font-weight: 700; margin-top: 14px; padding-top: 10px;
                          border-top: 1px solid rgba(255,255,255,.3); letter-spacing: .5px; }}
  .letterhead .org {{ font-size: 12.5px; color: #ffd54f; margin-top: 4px; font-weight: 600; }}
  .band {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between;
           background: #f4f7fa; border-bottom: 1px solid #dbe3ea; padding: 9px 26px;
           font-size: 12px; color: #455a64; }}
  .section {{ background: #0b2545; color: #fff; font-size: 12px; font-weight: 700;
              letter-spacing: 1.3px; padding: 8px 26px; text-transform: uppercase;
              margin-top: 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td, th {{ padding: 9px 26px; font-size: 12.5px; vertical-align: top;
            border-bottom: 1px solid #edf1f5; text-align: left; }}
  th {{ background: #f7f9fc; font-weight: 700; color: #37474f; font-size: 11.5px;
        letter-spacing: .4px; text-transform: uppercase; }}
  td.label {{ width: 30%; color: #546e7a; font-weight: 600; }}
  .mono {{ font-family: Consolas, "Courier New", monospace; }}
  .prose {{ padding: 12px 26px 16px 26px; font-size: 12.5px; line-height: 1.65; color: #263238; }}
  .pill {{ display: inline-block; padding: 2px 11px; border-radius: 11px; font-size: 11px;
           font-weight: 700; color: #fff; letter-spacing: .4px; }}
  .metric-row {{ display: flex; flex-wrap: wrap; gap: 12px; padding: 14px 26px; }}
  .metric {{ flex: 1 1 130px; border: 1px solid #dbe3ea; border-radius: 8px; padding: 11px 13px;
             background: #fafcfe; border-top: 3px solid #0b2545; }}
  .metric .k {{ font-size: 10.5px; color: #607d8b; text-transform: uppercase;
                letter-spacing: .7px; font-weight: 700; }}
  .metric .v {{ font-size: 21px; font-weight: 800; color: #102027; margin-top: 3px; }}
  .note {{ background: #fffde7; border-left: 4px solid #ffd54f; padding: 10px 16px;
           margin: 12px 26px; font-size: 12px; color: #5d4037; line-height: 1.6; }}
  .signatures {{ display: flex; flex-wrap: wrap; gap: 40px; padding: 22px 26px 8px 26px; }}
  .sig {{ flex: 1 1 240px; }}
  .sig .line {{ border-bottom: 1px dotted #90a4ae; height: 34px; }}
  .sig .who {{ font-size: 11px; color: #546e7a; margin-top: 5px; }}
  .footer {{ background: #f4f7fa; border-top: 2px solid #0b2545; padding: 12px 26px;
             font-size: 10.5px; color: #546e7a; line-height: 1.6; }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .sheet {{ border: none; box-shadow: none; max-width: 100%; }}
    .signatures {{ page-break-inside: avoid; }}
  }}
  @media (max-width: 640px) {{
    body {{ padding: 8px; }}
    td, th {{ padding: 7px 12px; font-size: 12px; }}
    .letterhead, .band, .section, .prose, .footer {{ padding-left: 14px; padding-right: 14px; }}
    .metric-row {{ padding: 10px 14px; }}
  }}
</style>
</head>
<body>
<div class="sheet">
  <div class="letterhead">
    <div class="platform">{_esc(PLATFORM_NAME)}</div>
    <div class="tagline">{_esc(PLATFORM_TAGLINE)}</div>
    <div class="doctype">{_esc(title)}</div>
    <div class="org">{_esc(subtitle)}</div>
  </div>
  <div class="band">
    <span><strong>Generated:</strong> {_esc(generated)}</span>
    <span><strong>Framework:</strong> {_esc(FRAMEWORK_REFERENCE)}</span>
  </div>
  {body}
  <div class="signatures">
    <div class="sig"><div class="line"></div>
      <div class="who">Prepared by (System Owner / Developer)</div></div>
    <div class="sig"><div class="line"></div>
      <div class="who">Reviewed by (AI Governance Officer)</div></div>
    <div class="sig"><div class="line"></div>
      <div class="who">Approved by (Administrator / Executive)</div></div>
  </div>
  <div class="footer">
    {_esc(footer_note or "This report is generated from the AI governance register. "
                         "Every action recorded in it is written to an append-only audit trail.")}<br>
    Report generated automatically by the AI Governance and Ethics Platform on
    {_esc(generated)}. Unauthorised alteration of this document invalidates it as
    compliance evidence.
  </div>
</div>
</body>
</html>"""


def _pill(text: str, colour: str) -> str:
    return f'<span class="pill" style="background:{colour}">{_esc(text)}</span>'


def _status_pill(status: str) -> str:
    return _pill(status, STATUS_COLOURS.get(status, "#616161"))


def _risk_pill(score: Optional[float], level: Optional[str]) -> str:
    if score is None:
        return _pill("Not assessed", "#78909c")
    meta = rc.risk_level_meta(level or rc.determine_risk_level(score))
    return _pill(f"{score:.1f} — {level or ''}", meta["colour"])


# ---------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------
def get_system(system_id: int) -> Optional[dict]:
    """One AI system with its owner's details and its latest assessments."""
    return db.fetch_one(
        """
        SELECT s.*, u.full_name AS owner_name, u.email AS owner_email,
               u.organization AS owner_organization,
               r.assessment_id, r.impact_score, r.likelihood_score, r.privacy_score,
               r.fairness_score, r.security_score, r.autonomy_score,
               r.total_risk_score, r.risk_level, r.assessment_date,
               e.ethics_id, e.fairness_response, e.privacy_response,
               e.transparency_response, e.accountability_response,
               e.oversight_response, e.security_response, e.explainability_response,
               e.accessibility_response, e.recommendation, e.assessment_date AS ethics_date
        FROM ai_systems s
        LEFT JOIN users u ON u.user_id = s.owner_id
        LEFT JOIN risk_assessments r
               ON r.assessment_id = (SELECT MAX(assessment_id) FROM risk_assessments
                                     WHERE system_id = s.system_id)
        LEFT JOIN ethical_assessments e
               ON e.ethics_id = (SELECT MAX(ethics_id) FROM ethical_assessments
                                 WHERE system_id = s.system_id)
        WHERE s.system_id = ?
        """,
        (int(system_id),),
    )


def selectable_systems() -> list[dict]:
    """All AI systems, newest first, for the report pickers."""
    return db.fetch_all(
        """
        SELECT system_id, system_name, governance_status, deployment_status
        FROM ai_systems ORDER BY system_id DESC
        """
    )


def selectable_incidents() -> list[dict]:
    """All incidents, newest first, for the report pickers."""
    return db.fetch_all(
        """
        SELECT i.incident_id, i.incident_type, i.severity, i.status,
               COALESCE(s.system_name, 'Unknown system') AS system_name
        FROM incidents i
        LEFT JOIN ai_systems s ON s.system_id = i.system_id
        ORDER BY i.incident_id DESC
        """
    )


# =====================================================================
# REPORT 1 - AI System Governance Report
# =====================================================================
def generate_system_report(system_id: int) -> tuple[str, str]:
    """
    Build the complete governance report for one AI system.

    Returns ``(html_document, suggested_filename)``.
    """
    system = get_system(system_id)
    if not system:
        raise ValueError(f"AI system #{system_id} was not found in the register.")

    name = system["system_name"]
    title = f"AI SYSTEM GOVERNANCE REPORT — {name}"
    subtitle = system.get("owner_organization") or "Registered AI System"

    # ---- registration -------------------------------------------------
    registration = f"""
    <div class="section">1. Registration details</div>
    <table>
      <tr><td class="label">System ID</td><td class="mono">AIS-{int(system['system_id']):04d}</td>
          <td class="label">Registered on</td><td>{_esc(_wat(system['created_at']))}</td></tr>
      <tr><td class="label">System name</td><td><strong>{_esc(name)}</strong></td>
          <td class="label">Last updated</td><td>{_esc(_wat(system.get('updated_at')))}</td></tr>
      <tr><td class="label">Technology type</td><td>{_esc(system.get('technology_type'))}</td>
          <td class="label">Deployment status</td><td>{_esc(system.get('deployment_status'))}</td></tr>
      <tr><td class="label">System owner</td><td>{_esc(system.get('owner_name'))}</td>
          <td class="label">Owner email</td><td class="mono">{_esc(system.get('owner_email'))}</td></tr>
      <tr><td class="label">Data sources</td><td>{_esc(system.get('data_sources'))}</td>
          <td class="label">Affected parties</td><td>{_esc(system.get('affected_users'))}</td></tr>
      <tr><td class="label">Governance status</td>
          <td colspan="3">{_status_pill(system.get('governance_status') or 'Draft')}</td></tr>
    </table>
    <div class="section">2. Purpose of the system</div>
    <div class="prose">{_esc(system.get('purpose') or 'No purpose recorded.')}</div>
    """

    # ---- risk assessment ----------------------------------------------
    if system.get("assessment_id"):
        breakdown = rc.risk_breakdown(
            system["impact_score"], system["likelihood_score"], system["privacy_score"],
            system["fairness_score"], system["security_score"], system["autonomy_score"],
        )
        rows = "".join(
            f"<tr><td>{_esc(row['label'])}</td>"
            f"<td class='mono'>{row['raw_score']:.1f}</td>"
            f"<td class='mono'>{row['weight']:.2f}</td>"
            f"<td class='mono'>{row['contribution']:.2f}</td>"
            f"<td class='mono'>{row['share_pct']:.1f}%</td></tr>"
            for row in breakdown
        )
        risk_section = f"""
        <div class="section">3. Risk assessment</div>
        <div class="metric-row">
          <div class="metric"><div class="k">Weighted risk score</div>
            <div class="v">{system['total_risk_score']:.1f}</div></div>
          <div class="metric"><div class="k">Risk band</div>
            <div class="v" style="color:{rc.risk_level_meta(system['risk_level'])['colour']}">
              {_esc(system['risk_level'])}</div></div>
          <div class="metric"><div class="k">Assessed on</div>
            <div class="v" style="font-size:13px">{_esc(_wat(system['assessment_date'], False))}</div></div>
          <div class="metric"><div class="k">Highest driver</div>
            <div class="v" style="font-size:13px">{_esc(breakdown[0]['label'])}</div></div>
        </div>
        <div class="prose" style="padding-top:0">
          <strong>Formula in force:</strong>
          <span class="mono">{_esc(rc.formula_text())}</span><br><br>
          {_esc(rc.risk_summary_sentence(system['total_risk_score'], breakdown))}
        </div>
        <table>
          <tr><th>Risk dimension</th><th>Score /100</th><th>Weight</th>
              <th>Contribution</th><th>Share of total</th></tr>
          {rows}
        </table>
        """
    else:
        risk_section = """
        <div class="section">3. Risk assessment</div>
        <div class="note">No risk assessment has been completed for this AI system.
        A system cannot be approved for production until a risk assessment is on
        record.</div>
        """

    # ---- ethical assessment -------------------------------------------
    if system.get("ethics_id"):
        responses = {
            "fairness_response": system["fairness_response"],
            "privacy_response": system["privacy_response"],
            "transparency_response": system["transparency_response"],
            "accountability_response": system["accountability_response"],
            "oversight_response": system["oversight_response"],
            "security_response": system["security_response"],
            "explainability_response": system["explainability_response"],
            "accessibility_response": system["accessibility_response"],
        }
        score, earned, possible = rc.calculate_ethics_score(responses)
        _rec, reasoning = rc.determine_ethical_recommendation(responses)
        meta = rc.recommendation_meta(system["recommendation"])

        rows = "".join(
            f"<tr><td>{_esc(q['label'])}</td>"
            f"<td>{_esc(responses.get(q['key'], ''))}</td>"
            f"<td>{'Critical' if q['critical'] else 'Standard'}</td></tr>"
            for q in rc.ETHICS_QUESTIONS
        )
        ethics_section = f"""
        <div class="section">4. Ethical impact assessment</div>
        <div class="metric-row">
          <div class="metric"><div class="k">Recommendation</div>
            <div class="v" style="font-size:16px;color:{meta['colour']}">
              {meta['icon']} {_esc(system['recommendation'])}</div></div>
          <div class="metric"><div class="k">Ethical compliance</div>
            <div class="v">{score * 100:.0f}%</div></div>
          <div class="metric"><div class="k">Assessed on</div>
            <div class="v" style="font-size:13px">{_esc(_wat(system['ethics_date'], False))}</div></div>
        </div>
        <div class="prose" style="padding-top:0">{_esc(reasoning)}</div>
        <table>
          <tr><th>Ethical requirement</th><th>Response</th><th>Classification</th></tr>
          {rows}
        </table>
        """
    else:
        ethics_section = """
        <div class="section">4. Ethical impact assessment</div>
        <div class="note">No ethical impact assessment has been completed for this
        AI system.</div>
        """

    # ---- decision history ---------------------------------------------
    approvals = db.fetch_all(
        """
        SELECT a.decision, a.comments, a.decision_date, u.full_name AS reviewer_name
        FROM approvals a LEFT JOIN users u ON u.user_id = a.reviewer_id
        WHERE a.system_id = ? ORDER BY a.approval_id DESC
        """,
        (int(system_id),),
    )
    if approvals:
        rows = "".join(
            f"<tr><td>{_esc(_wat(a['decision_date']))}</td>"
            f"<td>{_status_pill(a['decision'])}</td>"
            f"<td>{_esc(a['reviewer_name'])}</td>"
            f"<td>{_esc(a['comments'])}</td></tr>"
            for a in approvals
        )
        decisions_section = f"""
        <div class="section">5. Governance decision history</div>
        <table>
          <tr><th>Date</th><th>Decision</th><th>Reviewer</th><th>Comments and conditions</th></tr>
          {rows}
        </table>
        """
    else:
        decisions_section = """
        <div class="section">5. Governance decision history</div>
        <div class="note">No governance decision has been recorded for this system yet.
        It is awaiting review.</div>
        """

    # ---- incidents -----------------------------------------------------
    incidents = db.fetch_all(
        """
        SELECT i.incident_id, i.incident_type, i.severity, i.status, i.description,
               i.corrective_action, i.reported_at, u.full_name AS reporter_name
        FROM incidents i LEFT JOIN users u ON u.user_id = i.reported_by
        WHERE i.system_id = ? ORDER BY i.incident_id DESC
        """,
        (int(system_id),),
    )
    if incidents:
        rows = "".join(
            f"<tr><td class='mono'>INC-{int(i['incident_id']):04d}</td>"
            f"<td>{_esc(i['incident_type'])}<br><span style='color:#78909c;font-size:11px'>"
            f"{_esc(i['severity'])} severity</span></td>"
            f"<td>{_status_pill(i['status'])}</td>"
            f"<td>{_esc(i['description'])}</td>"
            f"<td>{_esc(i['corrective_action'] or 'None recorded')}</td></tr>"
            for i in incidents
        )
        incidents_section = f"""
        <div class="section">6. Incidents recorded against this system</div>
        <table>
          <tr><th>Ref</th><th>Type</th><th>Status</th><th>Description</th>
              <th>Corrective action</th></tr>
          {rows}
        </table>
        """
    else:
        incidents_section = """
        <div class="section">6. Incidents recorded against this system</div>
        <div class="prose">No incidents have been reported against this AI system.</div>
        """

    # ---- audit trail for this system ------------------------------------
    logs = audit_logger.logs_for_entity("ai_system", int(system_id), limit=60)
    if logs:
        rows = "".join(
            f"<tr><td>{_esc(_wat(l['timestamp']))}</td>"
            f"<td>{_esc(l['actor_name'])}</td>"
            f"<td class='mono'>{_esc(l['action_type'])}</td>"
            f"<td>{_esc(l['details'])}</td></tr>"
            for l in logs
        )
        audit_section = f"""
        <div class="section">7. Audit trail for this system</div>
        <table>
          <tr><th>Timestamp (WAT)</th><th>User</th><th>Action</th><th>Details</th></tr>
          {rows}
        </table>
        """
    else:
        audit_section = """
        <div class="section">7. Audit trail for this system</div>
        <div class="prose">No audit entries recorded against this system.</div>
        """

    body = (registration + risk_section + ethics_section
            + decisions_section + incidents_section + audit_section)

    filename = (f"AISystem_Governance_Report_{int(system_id):04d}_"
                f"{name.replace(' ', '_')[:40]}.html")
    return _document(title, subtitle, body), filename


# =====================================================================
# REPORT 2 - Compliance Summary Report
# =====================================================================
def generate_compliance_report() -> tuple[str, str]:
    """
    Portfolio-level compliance summary for management and the board.

    Returns ``(html_document, suggested_filename)``.
    """
    systems = db.fetch_all(
        """
        SELECT s.system_id, s.system_name, s.technology_type, s.deployment_status,
               s.governance_status, s.created_at,
               r.total_risk_score, r.risk_level
        FROM ai_systems s
        LEFT JOIN risk_assessments r
               ON r.assessment_id = (SELECT MAX(assessment_id) FROM risk_assessments
                                     WHERE system_id = s.system_id)
        ORDER BY s.system_id DESC
        """
    )
    incidents = db.fetch_all("SELECT severity, status, incident_type FROM incidents")

    total = len(systems)
    by_level = {level: 0 for level in rc.RISK_LEVELS}
    not_assessed = 0
    for row in systems:
        if row["risk_level"]:
            by_level[row["risk_level"]] = by_level.get(row["risk_level"], 0) + 1
        else:
            not_assessed += 1

    approved = len([s for s in systems if s["governance_status"] == "Approved"])
    pending = len([s for s in systems if s["governance_status"] in
                   ("Submitted", "UnderReview")])
    compliance_rate = (approved / total * 100.0) if total else 0.0
    open_incidents = len([i for i in incidents
                          if i["status"] in ("Reported", "UnderInvestigation")])

    title = "AI COMPLIANCE SUMMARY REPORT"
    subtitle = "Portfolio position for management review"

    metrics = f"""
    <div class="metric-row">
      <div class="metric"><div class="k">AI systems registered</div>
        <div class="v">{total}</div></div>
      <div class="metric"><div class="k">Approved</div>
        <div class="v" style="color:#2e7d32">{approved}</div></div>
      <div class="metric"><div class="k">Pending review</div>
        <div class="v" style="color:#ef6c00">{pending}</div></div>
      <div class="metric"><div class="k">Compliance rate</div>
        <div class="v">{compliance_rate:.0f}%</div></div>
      <div class="metric"><div class="k">Open incidents</div>
        <div class="v" style="color:#c62828">{open_incidents}</div></div>
    </div>
    """

    risk_rows = "".join(
        f"<tr><td>{rc.risk_level_meta(level)['icon']} {_esc(level)}</td>"
        f"<td class='mono'>{by_level.get(level, 0)}</td>"
        f"<td>{_esc(rc.risk_level_meta(level)['range'])}</td>"
        f"<td>{_esc(rc.risk_level_meta(level)['advice'])}</td></tr>"
        for level in rc.RISK_LEVELS
    )
    if not_assessed:
        risk_rows += (f"<tr><td>⚪ Not assessed</td><td class='mono'>{not_assessed}</td>"
                      f"<td>—</td><td>An assessment is required before this system can "
                      f"be reviewed for approval.</td></tr>")

    system_rows = "".join(
        f"<tr><td class='mono'>AIS-{int(s['system_id']):04d}</td>"
        f"<td>{_esc(s['system_name'])}</td>"
        f"<td>{_esc(s['technology_type'])}</td>"
        f"<td>{_esc(s['deployment_status'])}</td>"
        f"<td>{_status_pill(s['governance_status'])}</td>"
        f"<td>{_risk_pill(s['total_risk_score'], s['risk_level'])}</td></tr>"
        for s in systems
    ) or "<tr><td colspan='6'>No AI systems registered.</td></tr>"

    incident_types: dict[str, int] = {}
    for incident in incidents:
        key = incident["incident_type"] or "Unclassified"
        incident_types[key] = incident_types.get(key, 0) + 1
    incident_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td class='mono'>{v}</td></tr>"
        for k, v in sorted(incident_types.items(), key=lambda x: -x[1])
    ) or "<tr><td colspan='2'>No incidents recorded.</td></tr>"

    body = f"""
    <div class="section">1. Executive summary</div>
    <div class="metric-row">
      <div class="metric"><div class="k">Total AI systems</div><div class="v">{total}</div></div>
      <div class="metric"><div class="k">Compliance rate</div>
        <div class="v">{compliance_rate:.0f}%</div></div>
      <div class="metric"><div class="k">Open incidents</div>
        <div class="v">{open_incidents}</div></div>
      <div class="metric"><div class="k">High + Critical risk</div>
        <div class="v">{by_level.get('High', 0) + by_level.get('Critical', 0)}</div></div>
    </div>
    <div class="prose">
      This organisation has <strong>{total}</strong> artificial intelligence
      system(s) on the governance register, of which <strong>{approved}</strong>
      ({compliance_rate:.0f}%) have completed the full governance process and are
      approved for their current deployment. <strong>{pending}</strong> system(s)
      are awaiting governance review and <strong>{not_assessed}</strong> have not yet
      completed a risk assessment.
      There are <strong>{open_incidents}</strong> incident(s) still open.
      The framework applied is the {_esc(FRAMEWORK_REFERENCE)}.
    </div>
    {metrics if False else ""}
    <div class="section">2. Risk distribution</div>
    <table>
      <tr><th>Risk band</th><th>Systems</th><th>Score range</th><th>Governance expectation</th></tr>
      {risk_rows}
    </table>
    <div class="section">3. AI system register</div>
    <table>
      <tr><th>Ref</th><th>System</th><th>Technology</th><th>Deployment</th>
          <th>Governance status</th><th>Risk</th></tr>
      {system_rows}
    </table>
    <div class="section">4. Incidents by type</div>
    <table>
      <tr><th>Incident type</th><th>Count</th></tr>
      {incident_rows}
    </table>
    <div class="note">
      <strong>Compliance rate</strong> is the proportion of registered AI systems that
      have completed registration, risk assessment, ethical assessment and governance
      approval. Systems that are still in Draft, Submitted, Under Review, Returned or
      Rejected are not counted as compliant.
    </div>
    """

    filename = (f"AI_Compliance_Summary_Report_"
                f"{datetime.utcnow().strftime('%Y-%m-%d')}.html")
    return _document(title, subtitle, body), filename


# =====================================================================
# REPORT 3 - Incident Report
# =====================================================================
def generate_incident_report(incident_id: int) -> tuple[str, str]:
    """
    Build the full report for one incident.

    Returns ``(html_document, suggested_filename)``.
    """
    incident = db.fetch_one(
        """
        SELECT i.*, s.system_name, s.technology_type, s.deployment_status,
               s.governance_status, r.risk_level, r.total_risk_score,
               u.full_name AS reporter_name, u.email AS reporter_email,
               u.organization AS reporter_organization
        FROM incidents i
        LEFT JOIN ai_systems s ON s.system_id = i.system_id
        LEFT JOIN users u ON u.user_id = i.reported_by
        LEFT JOIN risk_assessments r
               ON r.assessment_id = (SELECT MAX(assessment_id) FROM risk_assessments
                                     WHERE system_id = i.system_id)
        WHERE i.incident_id = ?
        """,
        (int(incident_id),),
    )
    if not incident:
        raise ValueError(f"Incident #{incident_id} was not found.")

    severity_colours = {"Low": "#2e7d32", "Medium": "#f9a825",
                        "High": "#ef6c00", "Critical": "#c62828"}
    severity_colour = severity_colours.get(incident["severity"], "#616161")

    title = f"AI INCIDENT REPORT — INC-{int(incident['incident_id']):04d}"
    subtitle = incident.get("system_name") or "Unspecified AI system"

    body = f"""
    <div class="section">1. Incident particulars</div>
    <div class="metric-row">
      <div class="metric"><div class="k">Severity</div>
        <div class="v" style="color:{severity_colour};font-size:17px">
          {_esc(incident['severity'])}</div></div>
      <div class="metric"><div class="k">Status</div>
        <div class="v" style="font-size:15px">{_esc(incident['status'])}</div></div>
      <div class="metric"><div class="k">Type</div>
        <div class="v" style="font-size:15px">{_esc(incident['incident_type'])}</div></div>
      <div class="metric"><div class="k">Reported</div>
        <div class="v" style="font-size:13px">{_esc(_wat(incident['reported_at'], False))}</div></div>
    </div>
    <table>
      <tr><td class="label">Incident reference</td>
          <td class="mono">INC-{int(incident['incident_id']):04d}</td>
          <td class="label">Reported by</td><td>{_esc(incident['reporter_name'])}</td></tr>
      <tr><td class="label">AI system involved</td>
          <td>{_esc(incident.get('system_name') or 'Not specified')}</td>
          <td class="label">Reporter email</td>
          <td class="mono">{_esc(incident['reporter_email'])}</td></tr>
      <tr><td class="label">Technology type</td>
          <td>{_esc(incident.get('technology_type') or '—')}</td>
          <td class="label">Deployment status at time of report</td>
          <td>{_esc(incident.get('deployment_status') or '—')}</td></tr>
      <tr><td class="label">System governance status</td>
          <td>{_status_pill(incident.get('governance_status') or 'Unknown')}</td>
          <td class="label">System risk rating</td>
          <td>{_risk_pill(incident.get('total_risk_score'), incident.get('risk_level'))}</td></tr>
      <tr><td class="label">Affected parties</td>
          <td colspan="3">{_esc(incident.get('affected_parties') or 'Not specified')}</td></tr>
    </table>
    <div class="section">2. Description of the incident</div>
    <div class="prose">{_esc(incident.get('description') or 'No description recorded.')}</div>
    <div class="section">3. Corrective action taken</div>
    <div class="prose">{_esc(incident.get('corrective_action') or 'No corrective action recorded yet.')}</div>
    """

    logs = audit_logger.logs_for_entity("incident", int(incident_id), limit=40)
    if logs:
        rows = "".join(
            f"<tr><td>{_esc(_wat(l['timestamp']))}</td><td>{_esc(l['actor_name'])}</td>"
            f"<td class='mono'>{_esc(l['action_type'])}</td><td>{_esc(l['details'])}</td></tr>"
            for l in logs
        )
        body += f"""
        <div class="section">4. Audit trail for this incident</div>
        <table>
          <tr><th>Timestamp (WAT)</th><th>User</th><th>Action</th><th>Details</th></tr>
          {rows}
        </table>
        """

    body += f"""
    <div class="note">
      <strong>Regulatory note.</strong> Incidents involving personal data may require
      notification to the Nigeria Data Protection Commission under the Nigeria Data
      Protection Act 2023. Incidents affecting the safety or fundamental rights of
      individuals should also be escalated to the AI Governance Officer and recorded
      in the AI system's governance file.
      {f"<br><br><strong>Resolved on:</strong> {_esc(_wat(incident['resolved_at']))}"
       if incident.get('resolved_at') else ""}
    </div>
    """

    filename = (f"AI_Incident_Report_INC-{int(incident_id):04d}_"
                f"{datetime.utcnow().strftime('%Y-%m-%d')}.html")
    return _document(title, subtitle, body), filename


# ---------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------
def report_index() -> list[dict]:
    """The catalogue of reports this platform can generate, for the Reports page."""
    return [
        {
            "key": "system",
            "name": "AI System Governance Report",
            "icon": "🗂️",
            "description": "The complete compliance record for one AI system: "
                           "registration, risk assessment, ethical assessment, "
                           "decision history, incidents and audit trail.",
            "audience": "Internal audit, regulator, board",
        },
        {
            "key": "compliance",
            "name": "Compliance Summary Report",
            "icon": "📊",
            "description": "Portfolio position for management: how many systems are "
                           "registered, their risk distribution, the compliance rate "
                           "and outstanding items.",
            "audience": "Management, board, investors",
        },
        {
            "key": "incident",
            "name": "AI Incident Report",
            "icon": "🚨",
            "description": "Full details of one incident: particulars, affected "
                           "parties, corrective action and audit trail.",
            "audience": "Governance Officer, NDPC notification, legal",
        },
    ]


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    try:
        html_doc, filename = generate_compliance_report()
        print(f"compliance report : {len(html_doc):,} chars -> {filename}")
    except Exception as exc:  # noqa: BLE001
        print("Run setup_db.py first:", exc)
