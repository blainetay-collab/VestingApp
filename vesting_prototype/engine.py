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
apply_actions(tranches, actions, data, overrides) -> apply what-if people events using the plan rules
side_effects(data, actions, overrides, as_of)     -> clawback exposure and options that could lapse
diff_events(current, whatif)             -> which vesting events were forfeited, added or moved
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import rules as R

SCENARIOS = ["Flat", "Growth", "Range (bear / base / bull)"]
UPCOMING_STATUSES = ("Unvested", "Accelerated")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def load_data(data_dir: str | Path = "data") -> dict[str, pd.DataFrame]:
    """Read the CSV tables from data_dir."""
    d = Path(data_dir)
    grants = pd.read_csv(d / "grants.csv", parse_dates=["grant_date", "vesting_start_date"])
    tranches = pd.read_csv(d / "vesting_tranches.csv", parse_dates=["vest_date"])
    # Older data files lack the newer award-type columns; fill them so everything is treated as a plain RSU.
    for col, default in (("settlement", "Shares"), ("strike_price", np.nan), ("expiry_date", pd.NaT),
                         ("perf_metric", None), ("perf_max_pct", np.nan), ("election_83b", None),
                         ("purchase_discount", np.nan), ("lookback", None)):
        if col not in grants:
            grants[col] = default
    for col in ("expiry_date",):
        grants[col] = pd.to_datetime(grants[col])
    for col, default in (("contribution_usd", np.nan), ("offering_start_date", pd.NaT), ("offering_start_price", np.nan)):
        if col not in tranches:
            tranches[col] = default
    tranches["offering_start_date"] = pd.to_datetime(tranches["offering_start_date"])
    return {
        "companies": pd.read_csv(d / "companies.csv"),
        "employees": pd.read_csv(d / "employees.csv", parse_dates=["hire_date", "termination_date"]),
        "grants": grants,
        "tranches": tranches,
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
        if g.vesting_schedule_id not in sched.index or g.award_type == "ESPP":   # ESPP purchases are not template-based
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
        merged.index[(merged["total_shares"] - merged["shares_vesting"]).abs() > 0.05])
    add("Error", "Unknown award type", gr.loc[~gr["award_type"].isin(R.AWARD_TYPES), "grant_id"])
    add("Error", "Option or SAR has no strike price",
        gr.loc[gr["award_type"].isin(R.OPTION_LIKE) & gr["strike_price"].isna(), "grant_id"])
    add("Warning", "Performance award has no payout cap (perf_max_pct)",
        gr.loc[gr["award_type"].isin(R.PERF_TYPES) & gr["perf_max_pct"].isna(), "grant_id"])
    esp = tr.merge(gr[["grant_id", "award_type"]], on="grant_id")
    add("Error", "ESPP purchase has no contribution amount",
        esp.loc[(esp["award_type"] == "ESPP") & esp["contribution_usd"].isna(), "grant_id"])

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
                 "department", "country", "tax_residency_country", "tranche_id", "grant_id", "award_type",
                 "settlement", "vesting_schedule_id", "strike_price", "target_units", "payout_pct", "shares_vesting",
                 "share_units", "est_price_usd", "est_price_low", "est_price_high", "est_unit_value_usd",
                 "est_value_usd", "est_value_low", "est_value_high", "local_currency", "est_value_local",
                 "status", "flags"]


def upcoming_events(data: dict[str, pd.DataFrame], as_of, window_days: int = 90,
                    scenario: str = "Flat", annual_growth: float | None = None,
                    annual_vol: float | None = None, tranches: pd.DataFrame | None = None,
                    price_shock: float = 0.0, attrition: float = 0.0,
                    payout: dict | None = None) -> pd.DataFrame:
    """Every vesting event in (as_of, as_of + window_days] with estimated price and value.

    annual_growth / annual_vol: pass numbers to override every company, or leave as
    None to use each company's own assumptions from market_data.csv.
    tranches   : override the stored vesting events (used by the what-if).
    price_shock: one-off change to every starting price, e.g. -0.10 for 10% lower.
    attrition  : assumed annual share of staff who leave, e.g. 0.08. Unvested units are
                 scaled by the chance the person is still employed at each vest date
                 (an expected value, so units can be fractional). Accelerated events are not scaled.
    payout     : {company name: percent of target}, for PSUs and performance cash only (default 100).
                 Capped at each grant's own maximum. Accelerated events pay at target.

    What "value" means depends on the award type:
      RSU, PSU, Restricted Stock, Phantom Stock, ESPP : units x share price
      Stock Option, SARs                              : units x max(price - strike, 0)   (the gain)
      Performance Cash                                : dollars x payout %
      ESPP units are bought at a discount, so the unit count itself depends on the price.
    """
    as_of = pd.Timestamp(as_of)
    end = as_of + pd.Timedelta(days=int(window_days))
    tr = data["tranches"] if tranches is None else tranches
    ev = tr[tr["status"].isin(UPCOMING_STATUSES) & (tr["vest_date"] > as_of) & (tr["vest_date"] <= end)].copy()
    if ev.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    ev = ev.merge(data["grants"][["grant_id", "grant_date", "award_type", "ticker", "vesting_schedule_id", "settlement",
                                  "strike_price", "perf_max_pct", "purchase_discount", "lookback"]],
                  on="grant_id", how="left")
    ev = ev.merge(data["employees"][["employee_id", "company_id", "full_name", "department", "country",
                                     "tax_residency_country", "local_currency"]], on="employee_id", how="left")
    ev = ev.merge(data["companies"][["company_id", "company_name"]].rename(columns={"company_name": "company"}),
                  on="company_id", how="left")
    ev = ev.merge(data["market"][["ticker", "price_usd", "price_date", "annual_volatility",
                                  "assumed_annual_growth"]], on="ticker", how="left")
    ev = ev.merge(data["fx"][["currency", "units_per_usd"]], left_on="local_currency",
                  right_on="currency", how="left").drop(columns="currency")

    ev["days_until"] = (ev["vest_date"] - as_of).dt.days
    is_acc = (ev["status"] == "Accelerated").to_numpy()
    ev["target_units"] = ev["shares_vesting"]
    survive = np.ones(len(ev))
    if attrition:
        yrs_out = ev["days_until"].clip(lower=0).to_numpy() / 365.25
        survive = np.where(is_acc, 1.0, (1 - attrition) ** yrs_out)
        ev["shares_vesting"] = ev["shares_vesting"] * survive
    perf = ev["award_type"].isin(R.PERF_TYPES).to_numpy()
    pct = np.full(len(ev), 100.0)
    if payout:
        wanted = ev["company"].map(payout).fillna(100.0).to_numpy(dtype=float)
        cap = ev["perf_max_pct"].fillna(200.0).to_numpy(dtype=float)
        pct = np.where(perf & ~is_acc, np.clip(wanted, 0.0, cap), 100.0)
    ev["payout_pct"] = pct
    ev["shares_vesting"] = ev["shares_vesting"] * np.where(perf, pct / 100.0, 1.0)
    if price_shock:
        ev["price_usd"] = ev["price_usd"] * (1 + price_shock)

    years = (ev["vest_date"] - ev["price_date"]).dt.days.clip(lower=0).to_numpy() / 365.25
    g = ev["assumed_annual_growth"].to_numpy() if annual_growth is None else annual_growth
    v = ev["annual_volatility"].to_numpy() if annual_vol is None else annual_vol
    lo, ba, hi = project_price(ev["price_usd"].to_numpy(), years, scenario, g, v)

    # ESPP: the number of shares bought depends on the (discounted, possibly look-back) purchase price
    espp = (ev["award_type"] == "ESPP").to_numpy()
    if espp.any():
        start_dt = ev["offering_start_date"].fillna(ev["vest_date"])
        yrs_start = (start_dt - ev["price_date"]).dt.days.clip(lower=0).to_numpy() / 365.25
        _, ba_start, _ = project_price(ev["price_usd"].to_numpy(), yrs_start, scenario, g, v)
        p_start = ev["offering_start_price"].to_numpy(dtype=float)
        p_start = np.where(np.isnan(p_start), ba_start, p_start)
        disc = ev["purchase_discount"].fillna(0.15).to_numpy(dtype=float)
        look = ev["lookback"].fillna(True).astype(bool).to_numpy()
        buy = (1 - disc) * np.where(look, np.minimum(p_start, ba), ba)
        espp_target = ev["contribution_usd"].to_numpy(dtype=float) / np.where(buy > 0, buy, np.nan)
        ev["target_units"] = np.where(espp, espp_target, ev["target_units"])
        ev["shares_vesting"] = np.where(espp, espp_target * survive, ev["shares_vesting"])

    strike = ev["strike_price"].fillna(0.0).to_numpy(dtype=float)
    opt = ev["award_type"].isin(R.OPTION_LIKE).to_numpy()
    cash_unit = (ev["award_type"] == "Performance Cash").to_numpy()

    def unit_value(price):
        return np.where(opt, np.maximum(price - strike, 0.0), np.where(cash_unit, 1.0, price))

    ev["est_price_usd"], ev["est_price_low"], ev["est_price_high"] = np.round(ba, 2), np.round(lo, 2), np.round(hi, 2)
    ev["est_unit_value_usd"] = np.round(unit_value(ba), 4)
    ev["est_value_usd"] = (ev["shares_vesting"] * unit_value(ba)).round(2)
    ev["est_value_low"] = (ev["shares_vesting"] * unit_value(lo)).round(2)
    ev["est_value_high"] = (ev["shares_vesting"] * unit_value(hi)).round(2)
    ev["share_units"] = np.where(cash_unit, 0.0, ev["shares_vesting"])
    ev["est_value_local"] = (ev["est_value_usd"] * ev["units_per_usd"]).round(2)
    ev["month"] = ev["vest_date"].dt.to_period("M").astype(str)
    ev["flags"] = _flags_vectorized(ev)
    return ev[EVENT_COLUMNS].sort_values(["vest_date", "company", "employee_id"]).reset_index(drop=True)


def _flags_vectorized(ev: pd.DataFrame) -> pd.Series:
    underwater = ev["award_type"].isin(R.OPTION_LIKE) & (ev["est_price_usd"] <= ev["strike_price"].fillna(0))
    parts = pd.DataFrame({
        "a": np.where(ev["tax_residency_country"] != ev["country"], "Tax residency differs from work country - review", ""),
        "b": np.where(ev["vest_date"].dt.weekday >= 5, "Vest date is a weekend - settlement may shift", ""),
        "c": np.where(ev["status"] == "Accelerated", "Accelerated vest", ""),
        "d": np.where(underwater, "Underwater: price is at or below the strike, so no gain at this price", ""),
        "e": np.where(ev["award_type"].isin(R.PERF_TYPES) & (ev["status"] != "Accelerated") & (ev["payout_pct"] != 100),
                      "Payout assumed at " + ev["payout_pct"].round(0).astype(int).astype(str) + "% of target", ""),
    })
    return parts.apply(lambda r: "; ".join(x for x in r if x), axis=1)


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------
def summarize(events: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Roll events up by month, country and employee."""
    agg = {"events": ("grant_id", "count"), "shares": ("share_units", "sum"),
           "est_value_usd": ("est_value_usd", "sum"), "est_value_low": ("est_value_low", "sum"),
           "est_value_high": ("est_value_high", "sum")}
    if events.empty:
        empty = pd.DataFrame(columns=["events", "shares", "est_value_usd", "est_value_low", "est_value_high"])
        return {"by_month": empty.assign(month=[]), "by_company": empty.assign(company=[]),
                "by_country": empty.assign(country=[]), "by_award": empty.assign(award_type=[]),
                "by_employee": empty.assign(employee_id=[], full_name=[], country=[])}
    return {
        "by_month": events.groupby("month", as_index=False).agg(**agg),
        "by_company": events.groupby("company", as_index=False).agg(**agg)
                            .sort_values("est_value_usd", ascending=False).reset_index(drop=True),
        "by_country": events.groupby("country", as_index=False).agg(**agg)
                            .sort_values("est_value_usd", ascending=False).reset_index(drop=True),
        "by_award": events.groupby("award_type", as_index=False).agg(**agg)
                          .sort_values("est_value_usd", ascending=False).reset_index(drop=True),
        "by_employee": events.groupby(["employee_id", "full_name", "company", "country"], as_index=False).agg(**agg)
                             .sort_values("est_value_usd", ascending=False).reset_index(drop=True),
    }


def monthly_series(events: pd.DataFrame, metric: str = "shares_vesting", by: str | None = None,
                   cumulative: bool = False) -> pd.DataFrame:
    """Month-by-month totals for the BI line chart.

    metric: "share_units" (or "shares_vesting") or "est_value_usd". by: None for one total line, or a column
    such as "company", "country" or "department" for one line per group. Months with no
    vesting are filled with 0 so the line is continuous.
    """
    if events.empty:
        return pd.DataFrame()
    key = by if by else "Total"
    if metric == "shares_vesting":
        metric = "share_units"          # performance cash is counted in dollars, so it stays out of unit counts
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
def _ids(employee_ids) -> list:
    return [employee_ids] if isinstance(employee_ids, str) else list(employee_ids)


class _Context:
    """Lookups the event rules need, built once per what-if from the stored data."""

    def __init__(self, data: dict[str, pd.DataFrame], overrides: dict | None):
        emp = data["employees"].merge(data["companies"][["company_id", "company_name"]], on="company_id", how="left")
        self.company = emp.set_index("employee_id")["company_name"]
        g = data["grants"].set_index("grant_id")
        self.award = g["award_type"]
        self.total = g["total_shares"]
        self.start = g["vesting_start_date"]
        self.strike = g["strike_price"]
        self.expiry = g["expiry_date"]
        base = data["tranches"]
        self.last_vest = base.groupby("grant_id")["vest_date"].max()
        self.vested = base[base["status"] == "Vested"].groupby("grant_id")["shares_vesting"].sum()
        self.overrides = overrides or {}
        self._rules: dict = {}

    def rules_for(self, company) -> dict:
        if company not in self._rules:
            self._rules[company] = R.resolve_rules(self.overrides, company)
        return self._rules[company]


def _apply_event(t: pd.DataFrame, a: dict, ctx: _Context) -> pd.DataFrame:
    """Apply one what-if event. Each affected unvested vest is forfeited, accelerated, kept pro-rata,
    left alone, or paused, according to the plan rule for that company, event and award type."""
    kind, date = a["kind"], pd.Timestamp(a["date"])
    ids = _ids(a["employee_ids"])
    m = t["employee_id"].isin(ids) & (t["status"] == "Unvested") & (t["vest_date"] > date)
    if not m.any() or kind not in R.EVENTS:
        return t
    t = t.copy()
    sub = t.loc[m, ["grant_id", "employee_id", "vest_date", "shares_vesting"]].copy()
    sub["award"] = sub["grant_id"].map(ctx.award)
    sub["company"] = sub["employee_id"].map(ctx.company)
    sub["treatment"] = [ctx.rules_for(c)[kind]["treatments"].get(aw, R.FORFEIT) if
                        ctx.rules_for(c)[kind]["treatments"].get(aw, R.FORFEIT) in R.allowed_treatments(kind, aw)
                        else R.FORFEIT for c, aw in zip(sub["company"], sub["award"])]

    t.loc[sub.index[sub["treatment"] == R.FORFEIT], "status"] = "Forfeited"
    acc = sub.index[sub["treatment"] == R.ACCEL]
    t.loc[acc, "vest_date"] = date
    t.loc[acc, "status"] = "Accelerated"
    pause = sub.index[sub["treatment"] == R.PAUSE]
    if len(pause):
        t.loc[pause, "vest_date"] = t.loc[pause, "vest_date"] + pd.DateOffset(months=int(a.get("months", 3)))

    pr = sub[sub["treatment"] == R.PRORATA].sort_values(["grant_id", "vest_date"])
    if not pr.empty:
        gid = pr["grant_id"]
        span = (gid.map(ctx.last_vest) - gid.map(ctx.start)).dt.days.clip(lower=1)
        frac = ((date - gid.map(ctx.start)).dt.days / span).clip(0, 1)
        allowed = (gid.map(ctx.total) * frac - gid.map(ctx.vested).fillna(0)).clip(lower=0)
        before = pr.groupby("grant_id")["shares_vesting"].cumsum() - pr["shares_vesting"]
        kept = (allowed - before).clip(lower=0).clip(upper=pr["shares_vesting"])
        gone = kept <= 1e-9
        t.loc[kept.index[gone], "status"] = "Forfeited"
        keep_idx = kept.index[~gone]
        t.loc[keep_idx, "shares_vesting"] = kept[~gone]
        # time-based awards pay out at the event; performance awards stay on their original date and payout
        timed = [i for i in keep_idx if ctx.award[t.at[i, "grant_id"]] not in R.PERF_TYPES]
        t.loc[timed, "vest_date"] = date
        t.loc[timed, "status"] = "Accelerated"
    return t


def apply_actions(tranches: pd.DataFrame, actions, data: dict[str, pd.DataFrame],
                  overrides: dict | None = None) -> pd.DataFrame:
    """Apply what-if people events in order. Each action is a dict with kind (a key of rules.EVENTS),
    employee_ids, date, and months (for a leave). The plan rules (defaults plus any company overrides)
    decide what each event does to each award type."""
    ctx = _Context(data, overrides)
    t = tranches
    for a in actions:
        t = _apply_event(t, a, ctx)
    return t


def side_effects(data: dict[str, pd.DataFrame], actions, overrides: dict | None, as_of,
                 price_shock: float = 0.0) -> dict[str, pd.DataFrame]:
    """Consequences of the events that do not show up as upcoming vests.

    clawback: what was already delivered inside the lookback window and could be taken back, valued at today's
              price. This is exposure, not money recovered: collecting it is a legal and practical matter.
    lapse   : vested options and SARs that stay exercisable only for a limited window after the event, assuming
              none have been exercised (exercise records are not in the data).
    """
    ctx = _Context(data, overrides)
    tr, gr, mk = data["tranches"], data["grants"].set_index("grant_id"), data["market"].set_index("ticker")
    emp = data["employees"].set_index("employee_id")
    price = lambda ticker: float(mk.loc[ticker, "price_usd"]) * (1 + price_shock)   # noqa: E731
    claw, lapse = [], []
    for a in actions:
        kind, date = a["kind"], pd.Timestamp(a["date"])
        if kind == "leave" or kind not in R.EVENTS:
            continue
        for emp_id in _ids(a["employee_ids"]):
            if emp_id not in emp.index:
                continue
            company = ctx.company.get(emp_id)
            rule = ctx.rules_for(company)[kind]
            vested = tr[(tr["employee_id"] == emp_id) & (tr["status"] == "Vested")]
            for r in vested.itertuples():
                award, ticker = ctx.award[r.grant_id], gr.loc[r.grant_id, "ticker"]
                p = price(ticker)
                strike = gr.loc[r.grant_id, "strike_price"]
                unit = max(p - strike, 0.0) if award in R.OPTION_LIKE else (1.0 if award == "Performance Cash" else p)
                value = r.shares_vesting * unit
                if rule["clawback_months"] > 0 and date - pd.DateOffset(months=rule["clawback_months"]) < r.vest_date <= date:
                    claw.append({"employee_id": emp_id, "full_name": emp.loc[emp_id, "full_name"], "company": company,
                                 "grant_id": r.grant_id, "award_type": award, "vest_date": r.vest_date,
                                 "units": r.shares_vesting, "value_at_risk_usd": round(value, 2),
                                 "lookback_months": rule["clawback_months"], "event": R.EVENTS[kind]})
                if (award in R.OPTION_LIKE and value > 0
                        and rule["treatments"].get(award) != R.CONTINUE):
                    ends = date + pd.Timedelta(days=rule["window_days"])
                    exp = ctx.expiry.get(r.grant_id)
                    if pd.notna(exp):
                        ends = min(ends, exp)
                    lapse.append({"employee_id": emp_id, "full_name": emp.loc[emp_id, "full_name"], "company": company,
                                  "grant_id": r.grant_id, "award_type": award, "vested_units": r.shares_vesting,
                                  "gain_at_today_usd": round(value, 2), "exercisable_until": ends,
                                  "event": R.EVENTS[kind]})
    cc = ["employee_id", "full_name", "company", "grant_id", "award_type", "vest_date", "units", "value_at_risk_usd",
          "lookback_months", "event"]
    lc = ["employee_id", "full_name", "company", "grant_id", "award_type", "vested_units", "gain_at_today_usd",
          "exercisable_until", "event"]
    return {"clawback": pd.DataFrame(claw, columns=cc), "lapse": pd.DataFrame(lapse, columns=lc)}


def diff_events(current: pd.DataFrame, whatif: pd.DataFrame) -> pd.DataFrame:
    """Vesting events whose timing or size changed because of a people event: Removed (forfeited or pushed out
    of range), Added (accelerated or pushed in), Moved (new date) or Reduced (pro-rata cut-back, same date).
    Changes caused only by price, payout or attrition assumptions are not listed here."""
    cols = ["tranche_id", "employee_id", "full_name", "company", "country", "grant_id", "award_type"]
    c = current[cols + ["vest_date", "shares_vesting", "target_units", "est_value_usd"]].rename(columns={
        "vest_date": "current_date", "shares_vesting": "current_shares", "target_units": "current_target",
        "est_value_usd": "current_value"})
    w = whatif[["tranche_id", "vest_date", "shares_vesting", "target_units", "est_value_usd"]].rename(columns={
        "vest_date": "whatif_date", "shares_vesting": "whatif_shares", "target_units": "whatif_target",
        "est_value_usd": "whatif_value"})
    m = c.merge(w, on="tranche_id", how="outer", indicator=True)
    # events only in the what-if still need their identity columns
    extra = whatif[cols].set_index("tranche_id")
    for col in cols[1:]:
        m[col] = m[col].where(m[col].notna(), m["tranche_id"].map(extra[col]))
    shrunk = (m["award_type"] != "ESPP") & (m["whatif_target"] < m["current_target"] - 1e-6)
    m["change"] = np.select(
        [m["_merge"] == "left_only", m["_merge"] == "right_only", m["current_date"] != m["whatif_date"], shrunk],
        ["Removed", "Added", "Moved", "Reduced"], default="Unchanged")
    m = m[m["change"] != "Unchanged"].copy()
    m["value_change"] = m["whatif_value"].fillna(0) - m["current_value"].fillna(0)
    out = ["change", "full_name", "employee_id", "company", "country", "grant_id", "award_type", "current_date",
           "whatif_date", "current_shares", "whatif_shares", "value_change"]
    return m[out].sort_values("value_change", key=lambda x: x.abs(), ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
def whatif_steps(data: dict[str, pd.DataFrame], as_of, window_days: int, scenario: str = "Flat",
                 annual_growth: float | None = None, annual_vol: float | None = None,
                 tranches: pd.DataFrame | None = None, price_shock: float = 0.0,
                 attrition: float = 0.0, payout: dict | None = None) -> list[tuple[str, pd.DataFrame]]:
    """Apply the what-if levers one at a time, in a fixed order, and return the events after each step.

    Order: people events -> attrition -> performance payout -> share price change -> price path. The first
    item is always the current schedule and the last item equals the full what-if, so the steps add up exactly.
    Only levers that are switched on produce a step. Because the levers are applied in sequence, each step's
    size depends on that order.
    """
    def run(**kw):
        return upcoming_events(data, as_of, window_days, **kw)

    pay = {k: v for k, v in (payout or {}).items() if v != 100} or None
    steps = [("Current schedule", run())]
    if tranches is not None:
        steps.append(("People events", run(tranches=tranches)))
    if attrition:
        steps.append(("Attrition", run(tranches=tranches, attrition=attrition)))
    if pay:
        steps.append(("Performance payout", run(tranches=tranches, attrition=attrition, payout=pay)))
    if price_shock:
        steps.append(("Share price change", run(tranches=tranches, attrition=attrition, payout=pay,
                                                price_shock=price_shock)))
    if scenario != "Flat":
        steps.append(("Price path", run(scenario=scenario, annual_growth=annual_growth, annual_vol=annual_vol,
                                         tranches=tranches, attrition=attrition, payout=pay, price_shock=price_shock)))
    return steps


# --------------------------------------------------------------------------
# One employee: grant-by-grant view
# --------------------------------------------------------------------------
def grant_summary(data: dict[str, pd.DataFrame], employee_id: str, events: pd.DataFrame) -> pd.DataFrame:
    """One row per grant for one person: how much has vested, is still to come, or was forfeited,
    plus the next vest. `events` is the upcoming-events table for the view being shown
    (current schedule or what-if); vested and forfeited history always comes from the stored data."""
    g = data["grants"][data["grants"]["employee_id"] == employee_id]
    t = data["tranches"][data["tranches"]["employee_id"] == employee_id]
    out = g[["grant_id", "award_type", "settlement", "ticker", "grant_date", "vesting_schedule_id", "total_shares",
             "strike_price", "expiry_date"]].copy().set_index("grant_id")
    for status, col in (("Vested", "vested_shares"), ("Forfeited", "forfeited_shares")):
        out[col] = t[t["status"] == status].groupby("grant_id")["shares_vesting"].sum()
    e = events[events["employee_id"] == employee_id].sort_values("vest_date")
    if e.empty:
        out["upcoming_shares"], out["upcoming_value_usd"], out["upcoming_events"] = 0.0, 0.0, 0
        out["next_vest_date"], out["next_vest_shares"] = pd.NaT, 0.0
    else:
        agg = e.groupby("grant_id").agg(upcoming_shares=("shares_vesting", "sum"),
                                        upcoming_value_usd=("est_value_usd", "sum"),
                                        upcoming_events=("tranche_id", "count"))
        first = e.groupby("grant_id").first()[["vest_date", "shares_vesting"]] \
            .rename(columns={"vest_date": "next_vest_date", "shares_vesting": "next_vest_shares"})
        out = out.join(agg).join(first)
    for col in ("vested_shares", "forfeited_shares", "upcoming_shares", "upcoming_value_usd",
                "upcoming_events", "next_vest_shares"):
        out[col] = out[col].fillna(0)
    out["pct_vested"] = (out["vested_shares"] / out["total_shares"]).where(out["total_shares"] > 0, 0)
    return out.reset_index().sort_values("grant_date").reset_index(drop=True)


def employee_schedule(data: dict[str, pd.DataFrame], employee_id: str, events: pd.DataFrame) -> pd.DataFrame:
    """Every vesting event for one person on one timeline: past (Vested, Forfeited) from the stored data,
    upcoming from `events`. Status is Vested, Upcoming or Forfeited."""
    t = data["tranches"]
    past = t[(t["employee_id"] == employee_id) & t["status"].isin(["Vested", "Forfeited"])][
        ["tranche_id", "grant_id", "vest_date", "shares_vesting", "status"]].copy()
    up = events[events["employee_id"] == employee_id][
        ["tranche_id", "grant_id", "vest_date", "shares_vesting", "est_price_usd", "est_value_usd", "flags"]].copy()
    up["status"] = "Upcoming"
    out = pd.concat([past, up], ignore_index=True)
    out["flags"] = out["flags"].fillna("")
    out["award_type"] = out["grant_id"].map(data["grants"].set_index("grant_id")["award_type"])
    total = out.groupby("grant_id")["shares_vesting"].transform("sum")
    out["share_of_grant"] = (out["shares_vesting"] / total).where(total > 0, 0.0)
    return out.sort_values(["vest_date", "grant_id"]).reset_index(drop=True)
