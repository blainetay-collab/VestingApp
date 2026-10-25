"""Vesting engine for the global equity vesting tracker prototype.

Pure pandas, no UI code, so it can be tested on its own or pointed at a
different data source (for example a brokerage export) later.

Main entry points
-----------------
load_data(data_dir)                      -> dict of DataFrames
validate(data)                           -> DataFrame of data-quality findings
regenerate_tranches(grants, schedules)   -> vesting events rebuilt from schedule templates
upcoming_events(data, ...)               -> upcoming vesting events with price/value estimates
summarize(events)                        -> by-month / by-company / by-country / by-employee tables
monthly_series(events, ...)              -> month-by-month series for the BI line chart
simulate_termination(tranches, ...)      -> what-if: forfeit or accelerate an employee's unvested shares
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SCENARIOS = ["Flat", "Growth", "Range (bear / base / bull)"]
UPCOMING_STATUSES = ("Unvested", "Accelerated")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def load_data(data_dir: str | Path = "data") -> dict[str, pd.DataFrame]:
    """Read the CSV tables from data_dir."""
    d = Path(data_dir)
    return {
        "companies": pd.read_csv(d / "companies.csv"),
        "employees": pd.read_csv(d / "employees.csv", parse_dates=["hire_date", "termination_date"]),
        "grants": pd.read_csv(d / "grants.csv", parse_dates=["grant_date", "vesting_start_date"]),
        "tranches": pd.read_csv(d / "vesting_tranches.csv", parse_dates=["vest_date"]),
        "schedules": pd.read_csv(d / "vesting_schedules.csv"),
        "market": pd.read_csv(d / "market_data.csv", parse_dates=["price_date"]),
        "history": pd.read_csv(d / "price_history.csv", parse_dates=["price_date"]),
        "fx": pd.read_csv(d / "fx_rates.csv", parse_dates=["rate_date"]),
    }


# --------------------------------------------------------------------------
# Vesting schedule expansion
# --------------------------------------------------------------------------
def _expand_schedule(total: int, start: pd.Timestamp, total_months: int, cliff: int, interval: int):
    """Cliff tranche (cliff/total of shares), then equal tranches every `interval` months."""
    months = [cliff] + list(range(cliff + interval, total_months + 1, interval))
    first = int(total * cliff / total_months)
    rest = total - first
    n = len(months) - 1
    base = rest // n if n else 0
    shares = [first] + [base] * n
    shares[-1] += total - sum(shares)         # rounding remainder goes on the last tranche
    return [(start + pd.DateOffset(months=m), s) for m, s in zip(months, shares)]


def regenerate_tranches(grants: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    """Rebuild every grant's vesting events from its schedule template."""
    sched = schedules.set_index("vesting_schedule_id")
    rows = []
    for g in grants.itertuples():
        if g.vesting_schedule_id not in sched.index:
            continue
        s = sched.loc[g.vesting_schedule_id]
        for vest_date, shares in _expand_schedule(
            int(g.total_shares), g.vesting_start_date,
            int(s.total_months), int(s.cliff_months), int(s.interval_months),
        ):
            rows.append({"grant_id": g.grant_id, "employee_id": g.employee_id,
                         "vest_date": vest_date, "shares_vesting": shares})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return data-quality findings: severity, check, count, examples."""
    emp, gr, tr = data["employees"], data["grants"], data["tranches"]
    sched, fx = data["schedules"], data["fx"]
    findings = []

    def add(severity, check, ids):
        ids = list(pd.unique(pd.Series(ids)))
        if ids:
            findings.append({"severity": severity, "check": check, "count": len(ids),
                             "examples": ", ".join(map(str, ids[:5]))})

    add("Error", "Employee missing country", emp.loc[emp["country"].isna() | (emp["country"] == ""), "employee_id"])
    add("Error", "Employee missing local currency", emp.loc[emp["local_currency"].isna(), "employee_id"])
    add("Error", "Employee references unknown company", emp.loc[~emp["company_id"].isin(data["companies"]["company_id"]), "employee_id"])
    add("Error", "Grant ticker has no market data", gr.loc[~gr["ticker"].isin(data["market"]["ticker"]), "grant_id"])
    add("Error", "Grant references unknown employee", gr.loc[~gr["employee_id"].isin(emp["employee_id"]), "grant_id"])
    add("Error", "Grant references unknown vesting schedule",
        gr.loc[~gr["vesting_schedule_id"].isin(sched["vesting_schedule_id"]), "grant_id"])
    add("Error", "Grant has no vesting events", gr.loc[~gr["grant_id"].isin(tr["grant_id"]), "grant_id"])

    sums = tr.groupby("grant_id")["shares_vesting"].sum()
    merged = gr.set_index("grant_id")["total_shares"].to_frame().join(sums, how="inner")
    add("Error", "Vesting events do not add up to grant total",
        merged.index[merged["total_shares"] != merged["shares_vesting"]])

    tg = tr.merge(gr[["grant_id", "grant_date"]], on="grant_id")
    add("Error", "Vest date earlier than grant date", tg.loc[tg["vest_date"] < tg["grant_date"], "grant_id"])

    missing_ccy = set(emp["local_currency"].dropna()) - set(fx["currency"])
    add("Error", "Currency has no FX rate", sorted(missing_ccy))

    te = tr.merge(emp[["employee_id", "employment_status", "termination_date"]], on="employee_id")
    add("Warning", "Terminated employee still has unvested events after termination date",
        te.loc[(te["employment_status"] == "Terminated") & (te["status"] == "Unvested")
               & (te["vest_date"] > te["termination_date"]), "employee_id"])
    add("Warning", "Active employee has forfeited events",
        te.loc[(te["employment_status"] == "Active") & (te["status"] == "Forfeited"), "employee_id"])
    add("Info", "Tax residency differs from country of employment",
        emp.loc[emp["tax_residency_country"] != emp["country"], "employee_id"])

    cols = ["severity", "check", "count", "examples"]
    return pd.DataFrame(findings, columns=cols)


# --------------------------------------------------------------------------
# Price projection
# --------------------------------------------------------------------------
def project_price(price0, years, scenario: str, annual_growth=0.0, annual_vol=0.0):
    """Return (low, base, high) projected prices. Inputs may be scalars or numpy arrays.

    Flat    : current price held constant.
    Growth  : price compounded at annual_growth.
    Range   : base = growth path; low/high = base -/+ one standard deviation
              of a lognormal move (annual_vol * sqrt(years)). Illustrative only.
    """
    price0 = np.asarray(price0, dtype=float)
    years = np.asarray(years, dtype=float)
    if scenario == "Flat":
        base = price0 + 0 * years
        return base, base, base
    base = price0 * (1 + np.asarray(annual_growth, dtype=float)) ** years
    if scenario == "Growth":
        return base, base, base
    spread = np.asarray(annual_vol, dtype=float) * np.sqrt(years)
    return base * np.exp(-spread), base, base * np.exp(spread)


# --------------------------------------------------------------------------
# Upcoming events
# --------------------------------------------------------------------------
EVENT_COLUMNS = ["vest_date", "days_until", "month", "company", "ticker", "employee_id", "full_name",
                 "department", "country", "tax_residency_country", "grant_id", "award_type",
                 "vesting_schedule_id", "shares_vesting", "est_price_usd", "est_price_low", "est_price_high",
                 "est_value_usd", "est_value_low", "est_value_high", "local_currency", "est_value_local",
                 "status", "flags"]


def upcoming_events(data: dict[str, pd.DataFrame], as_of, window_days: int = 90,
                    scenario: str = "Flat", annual_growth: float | None = None,
                    annual_vol: float | None = None, tranches: pd.DataFrame | None = None) -> pd.DataFrame:
    """Every vesting event in (as_of, as_of + window_days] with estimated price and value.

    annual_growth / annual_vol: pass numbers to override every company, or leave as
    None to use each company's own assumptions from market_data.csv.
    Pass `tranches` to override the stored vesting events (used by the what-if).
    """
    as_of = pd.Timestamp(as_of)
    end = as_of + pd.Timedelta(days=int(window_days))
    tr = data["tranches"] if tranches is None else tranches
    ev = tr[tr["status"].isin(UPCOMING_STATUSES) & (tr["vest_date"] > as_of) & (tr["vest_date"] <= end)].copy()
    if ev.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    ev = ev.merge(data["grants"][["grant_id", "grant_date", "award_type", "ticker", "vesting_schedule_id"]],
                  on="grant_id", how="left")
    ev = ev.merge(data["employees"][["employee_id", "company_id", "full_name", "department", "country",
                                     "tax_residency_country", "local_currency"]], on="employee_id", how="left")
    ev = ev.merge(data["companies"][["company_id", "company_name"]].rename(columns={"company_name": "company"}),
                  on="company_id", how="left")
    ev = ev.merge(data["market"][["ticker", "price_usd", "price_date", "annual_volatility",
                                  "assumed_annual_growth"]], on="ticker", how="left")
    ev = ev.merge(data["fx"][["currency", "units_per_usd"]], left_on="local_currency",
                  right_on="currency", how="left").drop(columns="currency")

    years = (ev["vest_date"] - ev["price_date"]).dt.days.clip(lower=0).to_numpy() / 365.25
    g = ev["assumed_annual_growth"].to_numpy() if annual_growth is None else annual_growth
    v = ev["annual_volatility"].to_numpy() if annual_vol is None else annual_vol
    lo, ba, hi = project_price(ev["price_usd"].to_numpy(), years, scenario, g, v)
    ev["est_price_usd"], ev["est_price_low"], ev["est_price_high"] = np.round(ba, 2), np.round(lo, 2), np.round(hi, 2)
    ev["est_value_usd"] = (ev["shares_vesting"] * ev["est_price_usd"]).round(2)
    ev["est_value_low"] = (ev["shares_vesting"] * ev["est_price_low"]).round(2)
    ev["est_value_high"] = (ev["shares_vesting"] * ev["est_price_high"]).round(2)
    ev["est_value_local"] = (ev["est_value_usd"] * ev["units_per_usd"]).round(2)
    ev["days_until"] = (ev["vest_date"] - as_of).dt.days
    ev["month"] = ev["vest_date"].dt.to_period("M").astype(str)
    ev["flags"] = _flags_vectorized(ev)
    return ev[EVENT_COLUMNS].sort_values(["vest_date", "company", "employee_id"]).reset_index(drop=True)


def _flags_vectorized(ev: pd.DataFrame) -> pd.Series:
    parts = pd.DataFrame({
        "a": np.where(ev["tax_residency_country"] != ev["country"], "Tax residency differs from work country - review", ""),
        "b": np.where(ev["vest_date"].dt.weekday >= 5, "Vest date is a weekend - settlement may shift", ""),
        "c": np.where(ev["status"] == "Accelerated", "Accelerated vest", ""),
    })
    return parts.apply(lambda r: "; ".join(x for x in r if x), axis=1)


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------
def summarize(events: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Roll events up by month, country and employee."""
    agg = {"events": ("grant_id", "count"), "shares": ("shares_vesting", "sum"),
           "est_value_usd": ("est_value_usd", "sum"), "est_value_low": ("est_value_low", "sum"),
           "est_value_high": ("est_value_high", "sum")}
    if events.empty:
        empty = pd.DataFrame(columns=["events", "shares", "est_value_usd", "est_value_low", "est_value_high"])
        return {"by_month": empty.assign(month=[]), "by_company": empty.assign(company=[]),
                "by_country": empty.assign(country=[]),
                "by_employee": empty.assign(employee_id=[], full_name=[], country=[])}
    return {
        "by_month": events.groupby("month", as_index=False).agg(**agg),
        "by_company": events.groupby("company", as_index=False).agg(**agg)
                            .sort_values("est_value_usd", ascending=False).reset_index(drop=True),
        "by_country": events.groupby("country", as_index=False).agg(**agg)
                            .sort_values("est_value_usd", ascending=False).reset_index(drop=True),
        "by_employee": events.groupby(["employee_id", "full_name", "company", "country"], as_index=False).agg(**agg)
                             .sort_values("est_value_usd", ascending=False).reset_index(drop=True),
    }


def monthly_series(events: pd.DataFrame, metric: str = "shares_vesting", by: str | None = None,
                   cumulative: bool = False) -> pd.DataFrame:
    """Month-by-month totals for the BI line chart.

    metric: "shares_vesting" or "est_value_usd". by: None for one total line, or a column
    such as "company", "country" or "department" for one line per group. Months with no
    vesting are filled with 0 so the line is continuous.
    """
    if events.empty:
        return pd.DataFrame()
    key = by if by else "Total"
    df = events.assign(Total="Total")
    pivot = df.pivot_table(index="month", columns=key, values=metric, aggfunc="sum", fill_value=0)
    full = pd.period_range(pivot.index.min(), pivot.index.max(), freq="M").astype(str)
    pivot = pivot.reindex(full, fill_value=0)
    pivot.index.name = "month"
    pivot.columns.name = None
    return pivot.cumsum() if cumulative else pivot


# --------------------------------------------------------------------------
# What-if: termination / acceleration
# --------------------------------------------------------------------------
def simulate_termination(tranches: pd.DataFrame, employee_id: str, termination_date,
                         accelerate: bool = False) -> pd.DataFrame:
    """Return a copy of tranches with the employee's unvested events after
    termination_date either forfeited or accelerated (vesting on that date).
    Death / disability are the typical acceleration cases; everything else
    normally forfeits. Change-in-control is out of scope for phase 1."""
    t = tranches.copy()
    td = pd.Timestamp(termination_date)
    mask = (t["employee_id"] == employee_id) & (t["status"] == "Unvested") & (t["vest_date"] > td)
    if accelerate:
        t.loc[mask, "vest_date"] = td
        t.loc[mask, "status"] = "Accelerated"
    else:
        t.loc[mask, "status"] = "Forfeited"
    return t
