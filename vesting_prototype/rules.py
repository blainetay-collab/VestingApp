"""Award types, what-if events and the plan rules that connect them.

A *rule* answers: "When this event happens to someone, what happens to their unvested award of this type?"
Defaults below are typical market practice, chosen only so the prototype behaves sensibly. Every company can
override any of them, because the real answer lives in each plan document and varies by country.

Overrides are stored sparsely: {scope: {event: {"treatments": {award_type: treatment}, "window_days": n,
"clawback_months": n}}} where scope is "__default__" (all companies) or a company name.
"""
from __future__ import annotations

import copy

DEFAULT_SCOPE = "__default__"

AWARD_TYPES = ["RSU", "PSU", "Restricted Stock", "Stock Option", "SAR (stock-settled)", "SAR (cash-settled)",
               "Phantom Stock", "Performance Cash", "ESPP"]
OPTION_LIKE = {"Stock Option", "SAR (stock-settled)", "SAR (cash-settled)"}   # value = gain over a strike price
PERF_TYPES = {"PSU", "Performance Cash"}                                      # payout scales with performance
CASH_TYPES = {"SAR (cash-settled)", "Phantom Stock", "Performance Cash"}      # paid in cash through payroll

EVENTS = {
    "resign": "Resignation (employee leaves)",
    "term_no_cause": "Termination without cause (layoff)",
    "term_cause": "Termination for cause",
    "retire": "Retirement",
    "death": "Death",
    "disability": "Disability",
    "violation": "Violation (non-compete, confidentiality)",
    "leave": "Leave of absence",
}
EVENT_SHORT = {"resign": "resignation", "term_no_cause": "layoff", "term_cause": "termination for cause",
               "retire": "retirement", "death": "death", "disability": "disability",
               "violation": "violation", "leave": "leave of absence"}

FORFEIT, ACCEL, PRORATA, CONTINUE, PAUSE = "Forfeit", "Accelerate in full", "Pro-rata", "Continue vesting", "Pause vesting"
DEPARTURE_TREATMENTS = [FORFEIT, ACCEL, PRORATA, CONTINUE]
LEAVE_TREATMENTS = [PAUSE, CONTINUE]


def allowed_treatments(event: str, award_type: str) -> list[str]:
    if event == "leave":
        return LEAVE_TREATMENTS
    if award_type == "ESPP":          # an ESPP has no unvested shares to accelerate; participation just ends or continues
        return [FORFEIT, CONTINUE]
    return DEPARTURE_TREATMENTS


def _row(**over) -> dict:
    base = {a: FORFEIT for a in AWARD_TYPES}
    base.update({k.replace("_", " "): v for k, v in over.items()})
    return base


_TIME_BASED = ["RSU", "Restricted Stock", "Stock Option", "SAR (stock-settled)", "SAR (cash-settled)", "Phantom Stock"]

DEFAULT_TREATMENTS = {
    "resign": _row(),
    "term_no_cause": _row(),
    "term_cause": _row(),
    "retire": {**_row(), **{a: CONTINUE for a in _TIME_BASED}, "PSU": PRORATA, "Performance Cash": PRORATA},
    "death": {**{a: ACCEL for a in AWARD_TYPES}, "ESPP": FORFEIT},
    "disability": {**_row(), "RSU": ACCEL, "Restricted Stock": ACCEL, "Phantom Stock": ACCEL,
                   "Stock Option": CONTINUE, "SAR (stock-settled)": CONTINUE, "SAR (cash-settled)": CONTINUE,
                   "PSU": PRORATA, "Performance Cash": PRORATA},
    "violation": _row(),
    "leave": {**{a: PAUSE for a in AWARD_TYPES}},
}
# How long vested options/SARs stay exercisable after the event, in days (0 = they end with the event).
DEFAULT_WINDOW_DAYS = {"resign": 90, "term_no_cause": 90, "term_cause": 0, "retire": 365, "death": 365,
                       "disability": 365, "violation": 0, "leave": 0}
# How far back the company can claw back what was already delivered, in months (0 = no clawback).
DEFAULT_CLAWBACK_MONTHS = {"resign": 0, "term_no_cause": 0, "term_cause": 0, "retire": 0, "death": 0,
                           "disability": 0, "violation": 12, "leave": 0}


def default_rules() -> dict:
    return {ev: {"treatments": dict(DEFAULT_TREATMENTS[ev]), "window_days": DEFAULT_WINDOW_DAYS[ev],
                 "clawback_months": DEFAULT_CLAWBACK_MONTHS[ev]} for ev in EVENTS}


def resolve_rules(overrides: dict | None, company: str | None = None) -> dict:
    """Defaults, then the all-companies overrides, then this company's overrides."""
    rules = default_rules()
    for scope in (DEFAULT_SCOPE, company):
        for ev, o in ((overrides or {}).get(scope) or {}).items():
            if ev not in rules:
                continue
            rules[ev]["treatments"].update({a: t for a, t in (o.get("treatments") or {}).items() if a in AWARD_TYPES})
            for k in ("window_days", "clawback_months"):
                if o.get(k) is not None:
                    rules[ev][k] = int(o[k])
    return rules


def diff_to_overrides(scope_rules: dict, baseline: dict) -> dict:
    """Keep only what differs from the baseline, so overrides stay small and 'customized' is easy to show."""
    out = {}
    for ev, r in scope_rules.items():
        o = {}
        t = {a: v for a, v in r["treatments"].items() if v != baseline[ev]["treatments"].get(a)}
        if t:
            o["treatments"] = t
        for k in ("window_days", "clawback_months"):
            if r[k] != baseline[ev][k]:
                o[k] = r[k]
        if o:
            out[ev] = o
    return out


def clean_overrides(raw: dict) -> dict:
    """Drop anything unknown from uploaded overrides so a bad file cannot break the app."""
    out = {}
    for scope, evs in (raw or {}).items():
        if not isinstance(evs, dict):
            continue
        for ev, o in evs.items():
            if ev not in EVENTS or not isinstance(o, dict):
                continue
            c = {}
            t = {a: v for a, v in (o.get("treatments") or {}).items()
                 if a in AWARD_TYPES and v in allowed_treatments(ev, a)}
            if t:
                c["treatments"] = t
            for k in ("window_days", "clawback_months"):
                if isinstance(o.get(k), (int, float)) and 0 <= o[k] <= 3650:
                    c[k] = int(o[k])
            if c:
                out.setdefault(str(scope), {})[ev] = c
    return out


def count_overrides(overrides: dict, scope: str) -> int:
    return sum(len(o.get("treatments", {})) + sum(k in o for k in ("window_days", "clawback_months"))
               for o in (overrides.get(scope) or {}).values())


def rules_matrix(rules: dict) -> list[dict]:
    """Rows = events, columns = award types, for an at-a-glance table."""
    return [{"Event": EVENTS[ev], **{a: rules[ev]["treatments"][a] for a in AWARD_TYPES}} for ev in EVENTS]


def clone(x):
    return copy.deepcopy(x)
