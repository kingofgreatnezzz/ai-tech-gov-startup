"""
risk_calculator.py
=================================================================================
Weighted AI Risk Scoring Engine
Ethical Guideline and Governance Framework for AI Use in Nigerian Tech Startups
=================================================================================

THE RISK MODEL
--------------
Each AI system is scored on six risk dimensions, each on a 0-100 scale.  The
overall risk score is a **weighted average** of those six dimensions:

    Risk Score = 0.30 x Impact
               + 0.20 x Likelihood
               + 0.15 x Privacy Sensitivity
               + 0.15 x Fairness Concern
               + 0.10 x Security Exposure
               + 0.10 x Autonomy / Decision Impact

The weights sum to exactly 1.00, which means the result is always on the same
0-100 scale as the inputs and is directly comparable between systems.

WHY THESE WEIGHTS?
------------------
The weighting reflects the risk philosophy of the Nigerian Data Protection Act
2023 and the draft National AI Strategy, in which **harm to people dominates**:

* Impact (0.30) carries the largest weight because AI governance is ultimately
  about the severity of harm when a system fails.
* Likelihood (0.20) is next: a severe but practically impossible failure is
  less urgent than a moderate failure that happens often.
* Privacy and Fairness (0.15 each) are weighted equally and heavily because
  these are the two harms the NDPA 2023 and Nigerian anti-discrimination
  expectations focus on - unlawful processing of personal data, and automated
  decisions that disadvantage protected groups.
* Security and Autonomy (0.10 each) are essential but, on their own, support
  the two dimensions above; they modify exposure rather than create harm
  directly.

RISK BANDS
----------
    0 - 20    Low        (green)  - normal monitoring
    21 - 40    Moderate   (yellow) - standard governance review
    41 - 70    High       (orange) - senior review before deployment
    71 - 100   Critical   (red)    - deployment should be halted pending
                                      remediation and executive sign-off
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------
# The risk dimensions and their weights
# ---------------------------------------------------------------------
WEIGHTS: dict[str, float] = {
    "impact": 0.30,
    "likelihood": 0.20,
    "privacy": 0.15,
    "fairness": 0.15,
    "security": 0.10,
    "autonomy": 0.10,
}

#: Human-readable labels used in the UI, the reports and the breakdown table.
DIMENSION_LABELS: dict[str, str] = {
    "impact": "Impact / Severity of Harm",
    "likelihood": "Likelihood of Harm",
    "privacy": "Privacy Sensitivity",
    "fairness": "Fairness / Bias Concern",
    "security": "Security Exposure",
    "autonomy": "Autonomy / Decision Impact",
}

#: What each dimension means, shown to the assessor as guidance.
DIMENSION_HELP: dict[str, str] = {
    "impact": "How severe would the harm be to people if this system failed or "
              "produced a wrong outcome?",
    "likelihood": "How likely is it that the system will actually cause harm in "
                  "normal operation?",
    "privacy": "How sensitive is the personal data the system processes, and how "
               "intrusive is the processing under the NDPA 2023?",
    "fairness": "What is the risk that the system produces biased or "
                "discriminatory outcomes for particular groups?",
    "security": "How exposed is the system to attack, misuse or data breach?",
    "autonomy": "How much does the system decide on its own, without a human "
                "reviewing the decision?",
}

RISK_LEVELS = ["Low", "Moderate", "High", "Critical"]

RISK_LEVEL_META: dict[str, dict] = {
    "Low": {
        "colour": "#2e7d32", "bg": "#e8f5e9", "icon": "🟢",
        "range": "0 – 20",
        "advice": "Normal monitoring. Standard governance record-keeping applies.",
    },
    "Moderate": {
        "colour": "#f9a825", "bg": "#fffde7", "icon": "🟡",
        "range": "21 – 40",
        "advice": "Standard governance review before deployment. Document the "
                  "controls in place.",
    },
    "High": {
        "colour": "#ef6c00", "bg": "#fff3e0", "icon": "🟠",
        "range": "41 – 70",
        "advice": "Senior review required before deployment. Mitigation plan and "
                  "human oversight must be evidenced.",
    },
    "Critical": {
        "colour": "#c62828", "bg": "#ffebee", "icon": "🔴",
        "range": "71 – 100",
        "advice": "Deployment should be halted pending remediation. Executive "
                  "sign-off and a full ethical review are required.",
    },
}


class RiskInputError(ValueError):
    """Raised when a risk dimension is missing or out of range."""


# ---------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------
def _validate(name: str, value: object) -> float:
    """
    Coerce one dimension to a float in the range 0-100.

    Raises RiskInputError rather than silently accepting bad data, because an
    incorrect risk score could lead to a harmful AI system being deployed.
    """
    if value is None:
        raise RiskInputError(f"'{DIMENSION_LABELS.get(name, name)}' was not supplied.")

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RiskInputError(
            f"'{DIMENSION_LABELS.get(name, name)}' must be a number between 0 and 100."
        ) from exc

    if number != number:  # NaN check without importing math
        raise RiskInputError(f"'{DIMENSION_LABELS.get(name, name)}' is not a valid number.")

    if not (0.0 <= number <= 100.0):
        raise RiskInputError(
            f"'{DIMENSION_LABELS.get(name, name)}' must be between 0 and 100 "
            f"(received {number})."
        )
    return number


# ---------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------
def calculate_risk_score(
    impact: float,
    likelihood: float,
    privacy: float,
    fairness: float,
    security: float,
    autonomy: float,
) -> float:
    """
    Compute the weighted AI risk score.

    Formula
    -------
        Risk = 0.30*Impact + 0.20*Likelihood + 0.15*Privacy
             + 0.15*Fairness + 0.10*Security + 0.10*Autonomy

    All six inputs are on a 0-100 scale, so the weighted average is also on a
    0-100 scale.  The result is rounded to one decimal place, which is the
    precision at which it is displayed, stored and reported.

    Raises
    ------
    RiskInputError
        If any dimension is missing, non-numeric or outside 0-100.

    Examples
    --------
    >>> calculate_risk_score(70, 40, 80, 30, 60, 50)
    56.5
    """
    values = {
        "impact": _validate("impact", impact),
        "likelihood": _validate("likelihood", likelihood),
        "privacy": _validate("privacy", privacy),
        "fairness": _validate("fairness", fairness),
        "security": _validate("security", security),
        "autonomy": _validate("autonomy", autonomy),
    }

    total = 0.0
    for dimension, weight in WEIGHTS.items():
        total += weight * values[dimension]

    # Guard against floating point drift and keep the score inside 0-100.
    return round(min(100.0, max(0.0, total)), 1)


def determine_risk_level(score: float) -> str:
    """
    Map a numeric risk score to its governance band.

        0 - 20    Low
        21 - 40   Moderate
        41 - 70   High
        71 - 100  Critical
    """
    try:
        number = float(score)
    except (TypeError, ValueError):
        return "Critical"  # unknown risk must never be treated as safe

    if number != number:
        return "Critical"

    if number <= 20.0:
        return "Low"
    if number <= 40.0:
        return "Moderate"
    if number <= 70.0:
        return "High"
    return "Critical"


def risk_level_meta(level: str) -> dict:
    """Colour, icon, range and advice for a risk level."""
    return RISK_LEVEL_META.get(level, {
        "colour": "#616161", "bg": "#f5f5f5", "icon": "⚪",
        "range": "unknown", "advice": "Risk level not recognised.",
    })


# ---------------------------------------------------------------------
# Explainability - which factors drove the score
# ---------------------------------------------------------------------
def risk_breakdown(
    impact: float,
    likelihood: float,
    privacy: float,
    fairness: float,
    security: float,
    autonomy: float,
) -> list[dict]:
    """
    Show the contribution each dimension made to the final score.

    This is the "explainability" requirement of the framework: an officer must
    be able to see not only that a system scored 63.8, but *why* it scored that
    and which dimension is doing the most work.

    Returns a list of dictionaries sorted by contribution (largest first), each
    containing the raw score, the weight, the weighted contribution and the
    percentage share of the total.
    """
    raw = {
        "impact": _validate("impact", impact),
        "likelihood": _validate("likelihood", likelihood),
        "privacy": _validate("privacy", privacy),
        "fairness": _validate("fairness", fairness),
        "security": _validate("security", security),
        "autonomy": _validate("autonomy", autonomy),
    }

    total = sum(WEIGHTS[d] * raw[d] for d in WEIGHTS) or 1.0

    rows: list[dict] = []
    for dimension, weight in WEIGHTS.items():
        contribution = weight * raw[dimension]
        rows.append({
            "dimension": dimension,
            "label": DIMENSION_LABELS[dimension],
            "raw_score": round(raw[dimension], 1),
            "weight": weight,
            "weight_pct": round(weight * 100),
            "contribution": round(contribution, 2),
            "share_pct": round(contribution / total * 100.0, 1),
        })

    rows.sort(key=lambda item: item["contribution"], reverse=True)
    return rows


def top_drivers(breakdown: list[dict], count: int = 3) -> list[dict]:
    """The ``count`` dimensions contributing most to the risk score."""
    return list(breakdown[:count])


def risk_summary_sentence(score: float, breakdown: Optional[list[dict]] = None) -> str:
    """One-paragraph plain-English explanation of a risk score."""
    level = determine_risk_level(score)
    meta = risk_level_meta(level)

    sentence = (
        f"The weighted risk score is {score:.1f} out of 100, which places this AI "
        f"system in the {level.upper()} risk band ({meta['range']}). {meta['advice']}"
    )

    if breakdown:
        drivers = top_drivers(breakdown, 2)
        if drivers:
            names = " and ".join(
                f"{d['label'].lower()} ({d['raw_score']:.0f}/100)" for d in drivers
            )
            sentence += f" The main contributors are {names}."
    return sentence


def formula_text() -> str:
    """The formula as a printable string, used in the UI and the reports."""
    return (
        "Risk Score = 0.30 x Impact + 0.20 x Likelihood + 0.15 x Privacy "
        "+ 0.15 x Fairness + 0.10 x Security + 0.10 x Autonomy"
    )


# ---------------------------------------------------------------------
# Ethical assessment scoring
# ---------------------------------------------------------------------
ETHICS_QUESTIONS: list[dict] = [
    {
        "key": "fairness_response",
        "field": "fairness",
        "label": "Fairness",
        "question": "Does the system treat all groups of people equitably, without "
                    "disadvantaging any group?",
        "critical": True,
    },
    {
        "key": "privacy_response",
        "field": "privacy",
        "label": "Privacy",
        "question": "Is personal data protected, minimised and used only for the "
                    "purpose the user was told about (NDPA 2023)?",
        "critical": True,
    },
    {
        "key": "transparency_response",
        "field": "transparency",
        "label": "Transparency",
        "question": "Are users told clearly that they are dealing with an AI system "
                    "and how it makes its decisions?",
        "critical": False,
    },
    {
        "key": "accountability_response",
        "field": "accountability",
        "label": "Accountability",
        "question": "Is there a named person accountable for the system's outcomes?",
        "critical": True,
    },
    {
        "key": "oversight_response",
        "field": "oversight",
        "label": "Human Oversight",
        "question": "Can a human review, override or stop the AI's decisions?",
        "critical": True,
    },
    {
        "key": "security_response",
        "field": "security",
        "label": "Security",
        "question": "Is the system protected against misuse, tampering and unauthorised "
                    "access?",
        "critical": False,
    },
    {
        "key": "explainability_response",
        "field": "explainability",
        "label": "Explainability",
        "question": "Can the system's decisions be explained in plain language to the "
                    "person affected?",
        "critical": False,
    },
    {
        "key": "accessibility_response",
        "field": "accessibility",
        "label": "Accessibility",
        "question": "Is the system usable by people with disabilities and by people "
                    "with low digital literacy?",
        "critical": False,
    },
]

RESPONSE_OPTIONS = ["Yes", "Partial", "No", "Not Applicable"]

#: Score awarded for each answer. "Not Applicable" is excluded from the
#: denominator entirely, so an irrelevant question neither helps nor harms.
RESPONSE_SCORES = {"Yes": 1.0, "Partial": 0.5, "No": 0.0}

ETHICS_RECOMMENDATIONS = ["Approved", "NeedsImprovement", "Rejected"]

RECOMMENDATION_META = {
    "Approved": {"colour": "#2e7d32", "bg": "#e8f5e9", "icon": "✅"},
    "NeedsImprovement": {"colour": "#ef6c00", "bg": "#fff3e0", "icon": "⚠️"},
    "Rejected": {"colour": "#c62828", "bg": "#ffebee", "icon": "⛔"},
}


def calculate_ethics_score(responses: dict) -> tuple[float, int, int]:
    """
    Score the eight ethical questions.

    Parameters
    ----------
    responses : dict
        Maps the question key (e.g. ``fairness_response``) to one of
        ``RESPONSE_OPTIONS``.

    Returns
    -------
    (score, points_earned, points_possible)
        ``score`` is a 0.0-1.0 compliance ratio over the applicable questions only.

    Logic
    -----
    * Yes = 1.0, Partial = 0.5, No = 0.0
    * "Not Applicable" is removed from both the numerator and the denominator,
      so a genuinely irrelevant question does not distort the result.
    * If **every** question is Not Applicable the score is 0.0, which forces a
      human to look at the submission rather than have it auto-approve.
    """
    earned = 0.0
    possible = 0.0

    for question in ETHICS_QUESTIONS:
        answer = str(responses.get(question["key"], "")).strip()
        if answer not in RESPONSE_OPTIONS:
            raise RiskInputError(
                f"Please answer the '{question['label']}' question before saving."
            )
        if answer == "Not Applicable":
            continue
        earned += RESPONSE_SCORES[answer]
        possible += 1.0

    if possible == 0:
        return 0.0, 0, 0

    return round(earned / possible, 4), int(earned * 2), int(possible * 2)


def determine_ethical_recommendation(responses: dict) -> tuple[str, str]:
    """
    Turn the eight answers into a governance recommendation.

    Returns ``(recommendation, reasoning)``.

    Decision rules (deliberately simple and auditable):

    1. Two or more CRITICAL questions answered "No"  -> Rejected.
       (Critical questions: Fairness, Privacy, Accountability, Human Oversight.)
    2. Any single critical question answered "No"    -> at best NeedsImprovement.
    3. Otherwise, by compliance ratio:
           >= 0.85  -> Approved
           >= 0.55  -> NeedsImprovement
           <  0.55  -> Rejected
    """
    score, _earned, _possible = calculate_ethics_score(responses)

    critical_no = [
        q["label"] for q in ETHICS_QUESTIONS
        if q["critical"] and str(responses.get(q["key"], "")).strip() == "No"
    ]
    all_no = [
        q["label"] for q in ETHICS_QUESTIONS
        if str(responses.get(q["key"], "")).strip() == "No"
    ]

    if len(critical_no) >= 2:
        return "Rejected", (
            f"Rejected: {len(critical_no)} critical ethical requirements were not met "
            f"({', '.join(critical_no)}). A system that fails two or more of fairness, "
            f"privacy, accountability and human oversight cannot be deployed responsibly."
        )

    if critical_no:
        return "NeedsImprovement", (
            f"Needs improvement: the critical requirement '{critical_no[0]}' was not met. "
            f"Overall ethical compliance is {score * 100:.0f}%. This must be remediated "
            f"and re-assessed before approval."
        )

    if score >= 0.85:
        return "Approved", (
            f"Approved: ethical compliance is {score * 100:.0f}% across all applicable "
            f"requirements. All critical requirements (fairness, privacy, accountability "
            f"and human oversight) were satisfied."
        )

    if score >= 0.55:
        detail = f" Unmet requirements: {', '.join(all_no)}." if all_no else ""
        return "NeedsImprovement", (
            f"Needs improvement: ethical compliance is {score * 100:.0f}%, below the "
            f"85% threshold for approval.{detail}"
        )

    return "Rejected", (
        f"Rejected: ethical compliance is only {score * 100:.0f}%. The system does not "
        f"meet the minimum ethical standard for deployment."
    )


def recommendation_meta(recommendation: str) -> dict:
    """Colour and icon for an ethical recommendation."""
    return RECOMMENDATION_META.get(recommendation, {
        "colour": "#616161", "bg": "#f5f5f5", "icon": "⚪",
    })


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    print(formula_text())
    print()
    demo = calculate_risk_score(70, 40, 80, 30, 60, 50)
    print(f"Demo scores (70, 40, 80, 30, 60, 50) -> {demo}  [{determine_risk_level(demo)}]")
    for row in risk_breakdown(70, 40, 80, 30, 60, 50):
        print(f"  {row['label']:<28} {row['raw_score']:>6.1f} x {row['weight']:.2f} "
              f"= {row['contribution']:>6.2f}  ({row['share_pct']:>4.1f}% of total)")
    print()
    print(risk_summary_sentence(demo, risk_breakdown(70, 40, 80, 30, 60, 50)))
