"""Coreshift's fit-scoring rules. Edit weights here to retune.

Score starts at 50 and is adjusted by keyword matches against the tender
title (the GETS scraper does not return descriptions). Final score clamped
to 0-100. Value-band scoring from the brief was dropped: the Apify actor
returns contractValue=0 for every listing, so the field carries no signal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BASELINE = 50


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern[str]
    weight: int
    why: str


def _r(p: str, w: int, why: str) -> Rule:
    return Rule(re.compile(p, re.IGNORECASE), w, why)


PLUS: list[Rule] = [
    _r(r"\b(mvp|prototype|proof of concept|poc|discovery)\b", 22,
       "Prototype / discovery / MVP framing"),
    _r(r"\b(ai|machine learning|llm|generative)\b", 18,
       "AI / ML scope"),
    _r(r"\b(custom build|custom development|bespoke|agile)\b", 15,
       "Custom / agile build language"),
    _r(r"\b(modernisation|modernization|replace.*legacy|legacy.*replace)\b", 12,
       "Legacy modernisation"),
    _r(r"\b(automation|automated|automate)\b", 12,
       "Automation scope"),
    _r(r"\b(dashboard|visualisation|visualization|data viz)\b", 10,
       "Dashboard / data viz"),
    _r(r"\b(web app|web platform|web-based|portal|microsite)\b", 10,
       "Web app / portal build"),
    _r(r"\b(internal tool|internal tooling|internal workflow)\b", 10,
       "Internal tooling build"),
    _r(r"\b(integration|api|integrate with)\b", 5,
       "Integration work in scope"),
]

MINUS: list[Rule] = [
    _r(r"\b(turnkey|turn-key)\b.*\b(saas|product|solution|platform)\b", -45,
       "Turnkey SaaS product procurement"),
    _r(r"\bexisting (productised|product|saas|solution|platform)\b", -45,
       "Requires existing productised solution"),
    _r(r"\b(panel agreement|panel of (approved )?suppliers|panel refresh|"
       r"(contractor|supplier|professional services|digital) panel)\b", -40,
       "Panel procurement (multi-supplier)"),
    _r(r"\b(hardware|supply of|manufacture|peripherals|workstation refresh)\b", -40,
       "Hardware / physical goods"),
    _r(r"\bdeployed in (at least )?\d+ (comparable )?(international )?"
       r"(law enforcement |health |government )?agenc(y|ies)\b", -35,
       "Reference-customer threshold"),
    _r(r"\bvendor[- ]managed (saas|service)\b", -30,
       "Vendor-managed SaaS required"),
    _r(r"\b(security clearance|top secret|secret clearance)\b", -25,
       "Security clearance required"),
    _r(r"\bmanaged service\b", -15,
       "Managed-service framing"),
    _r(r"\bitil\b", -10,
       "ITIL framing — ops/support contract"),
    _r(r"\b(iso/?iec )?27001\b.*\bcertif", -10,
       "Demands existing ISO 27001 cert"),
]


def score_text(text: str) -> tuple[int, list[dict]]:
    """Return (clamped_score, reasons)."""
    s = BASELINE
    reasons: list[dict] = []
    for r in PLUS:
        if r.pattern.search(text):
            s += r.weight
            reasons.append({"kind": "plus", "text": r.why})
    for r in MINUS:
        if r.pattern.search(text):
            s += r.weight
            reasons.append({"kind": "minus", "text": r.why})
    return max(0, min(100, s)), reasons
