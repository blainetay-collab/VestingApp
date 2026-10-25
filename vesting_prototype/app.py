"""Streamlit front end for the global equity vesting tracker prototype.

Run from this folder:   streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

import engine
import reports

st.set_page_config(page_title="Equity Vesting Tracker", layout="wide")
DEFAULT_DIR = str(Path(__file__).parent / "data")
HORIZON_DAYS = 1500  # events are computed once out to ~4 years; window and BI slice from this


@st.cache_resource(show_spinner="Loading data...")
def get_data(data_dir: str):
    return engine.load_data(data_dir)


@st.cache_data(show_spinner=False)
def get_findings(data_dir: str):
    return engine.validate(get_data(data_dir))


@st.cache_data(show_spinner="Calculating vesting events...")
def get_horizon_events(data_dir: str, as_of, scenario: str, g_arg, v_arg):
    return engine.upcoming_events(get_data(data_dir), as_of, HORIZON_DAYS, scenario, g_arg, v_arg)


# ------------------------------------------------------------------ sidebar
st.sidebar.title("Settings")
data_dir = st.sidebar.text_input("Data folder", DEFAULT_DIR)
try:
    data = get_data(data_dir)
except Exception as exc:  # missing folder / file
    st.error(f"Could not load data from '{data_dir}': {exc}")
    st.stop()

market = data["market"]
as_of = st.sidebar.date_input("As-of date", value=market["price_date"].max().date())
window_label = st.sidebar.selectbox("Window", ["30 days", "90 days", "180 days", "365 days"], index=1)
window_days = int(window_label.split()[0])

st.sidebar.subheader("Price scenario")
scenario = st.sidebar.selectbox("Scenario", engine.SCENARIOS, index=0)
own = st.sidebar.checkbox("Use each company's own growth / volatility", value=True,
                          disabled=(scenario == "Flat"))
growth = st.sidebar.slider("Annual growth (%)", -20.0, 40.0, 8.0, 0.5,
                           disabled=(scenario == "Flat" or own)) / 100
vol = st.sidebar.slider("Annual volatility (%)", 5.0, 80.0, 35.0, 1.0,
                        disabled=(not scenario.startswith("Range") or own)) / 100
st.sidebar.caption("Projections start from each company's current price and are illustrative, not predictions.")
g_arg, v_arg = (None, None) if (own or scenario == "Flat") else (growth, vol)

# ------------------------------------------------------------------ events (computed once)
horizon_events = get_horizon_events(data_dir, pd.Timestamp(as_of), scenario, g_arg, v_arg)

st.sidebar.subheader("Filters")
companies = st.sidebar.multiselect("Company", sorted(horizon_events["company"].dropna().unique()))
countries = st.sidebar.multiselect("Country", sorted(horizon_events["country"].dropna().unique()))
departments = st.sidebar.multiselect("Department", sorted(horizon_events["department"].dropna().unique()))
search = st.sidebar.text_input("Employee name or ID contains")


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if companies:
        df = df[df["company"].isin(companies)]
    if countries:
        df = df[df["country"].isin(countries)]
    if departments:
        df = df[df["department"].isin(departments)]
    if search.strip():
        q = search.strip().lower()
        df = df[df["full_name"].str.lower().str.contains(q, regex=False)
                | df["employee_id"].str.lower().str.contains(q, regex=False)]
    return df


filter_parts = []
if companies:
    filter_parts.append("Company: " + ", ".join(companies))
if countries:
    filter_parts.append("Country: " + ", ".join(countries))
if departments:
    filter_parts.append("Department: " + ", ".join(departments))
if search.strip():
    filter_parts.append(f"Employee contains '{search.strip()}'")
filters_text = "; ".join(filter_parts) or "None"

window_all = horizon_events[horizon_events["days_until"] <= window_days]
ev = apply_filters(window_all)
summ = engine.summarize(ev)
is_range = scenario.startswith("Range")

# ------------------------------------------------------------------ header + KPIs
st.title("Upcoming Vesting Events")
st.caption(f"Next {window_days} days from {as_of:%Y-%m-%d} | scenario: {scenario} | filters: {filters_text} | "
           "synthetic data")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Vesting events", f"{len(ev):,}")
k2.metric("Shares vesting", f"{ev['shares_vesting'].sum():,.0f}")
k3.metric("Est. value (USD)", f"${ev['est_value_usd'].sum():,.0f}")
k4.metric("Employees", f"{ev['employee_id'].nunique():,}")
k5.metric("Companies", f"{ev['company'].nunique():,}")
if is_range:
    st.caption(f"Range: ${ev['est_value_low'].sum():,.0f} (bear) to ${ev['est_value_high'].sum():,.0f} (bull)")

# report metadata (shared by report + export)
if len(companies) == 1:
    title_company = companies[0]
    price_text = f"{market.loc[market['company'] == companies[0], 'price_usd'].iloc[0]:,.2f}"
else:
    title_company = "All companies" if not companies else "Selected companies"
    price_text = "Varies by company (see market data)"
meta = {
    "company": title_company, "report_date": f"{pd.Timestamp.today():%Y-%m-%d}",
    "price_date": f"{market['price_date'].max():%Y-%m-%d}", "window": f"Next {window_days} days from {as_of:%Y-%m-%d}",
    "price": 0.0, "price_text": price_text, "scenario": scenario, "growth": growth, "vol": vol,
    "growth_text": "Company-specific (from market data)" if g_arg is None else f"{growth:.1%} (all companies)",
    "vol_text": "Company-specific (from market data)" if v_arg is None else f"{vol:.1%} (all companies)",
    "filters": "" if filters_text == "None" else filters_text, "data_note": "Synthetic demonstration data.",
}

tab_events, tab_bi, tab_summary, tab_people, tab_quality, tab_whatif, tab_report = st.tabs(
    ["Events", "BI", "Summary", "By employee", "Data quality", "What-if", "Report"])

# ------------------------------------------------------------------ events
with tab_events:
    st.write(f"**{len(ev):,}** events match the active filters.")
    if ev.empty:
        st.info("No vesting events match. Try widening the window or clearing filters.")
    else:
        e1, e2, _ = st.columns([1, 1, 4])
        e1.download_button("Export CSV", ev.to_csv(index=False).encode("utf-8"),
                           file_name="vesting_events_filtered.csv", mime="text/csv")
        e2.download_button("Export Excel", reports.build_data_workbook(ev, filters_text, meta),
                           file_name="vesting_events_filtered.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.dataframe(
        ev,
        hide_index=True,
        column_config={
            "vest_date": st.column_config.DateColumn("Vest date", format="YYYY-MM-DD"),
            "est_price_usd": st.column_config.NumberColumn("Est. price", format="$%.2f"),
            "est_price_low": st.column_config.NumberColumn("Price low", format="$%.2f"),
            "est_price_high": st.column_config.NumberColumn("Price high", format="$%.2f"),
            "est_value_usd": st.column_config.NumberColumn("Est. value (USD)", format="$%.0f"),
            "est_value_low": st.column_config.NumberColumn("Value low", format="$%.0f"),
            "est_value_high": st.column_config.NumberColumn("Value high", format="$%.0f"),
            "est_value_local": st.column_config.NumberColumn("Est. value (local)", format="%.0f"),
        },
    )
    st.caption("Shares are gross, before tax withholding. Check the flags column for items needing review.")

# ------------------------------------------------------------------ BI
with tab_bi:
    st.write("How much will vest each month. Uses the filters in the sidebar; the window setting does not "
             "apply here, since this view has its own horizon.")
    b1, b2, b3, b4 = st.columns(4)
    horizon_label = b1.selectbox("Horizon", ["12 months", "24 months", "36 months", "48 months"], index=1)
    metric_label = b2.radio("Measure", ["Shares vesting", "Estimated value (USD)"])
    split_label = b3.selectbox("Split lines by", ["None (total)", "Company", "Country", "Department"])
    cumulative = b4.checkbox("Cumulative", value=False)

    months = int(horizon_label.split()[0])
    bi_end = pd.Timestamp(as_of) + pd.DateOffset(months=months)
    bi_events = apply_filters(horizon_events[horizon_events["vest_date"] <= bi_end])
    metric = "shares_vesting" if metric_label.startswith("Shares") else "est_value_usd"
    by = {"None (total)": None, "Company": "company", "Country": "country", "Department": "department"}[split_label]
    series = engine.monthly_series(bi_events, metric, by, cumulative)

    if series.empty:
        st.info("No vesting events match the filters in this horizon.")
    else:
        st.line_chart(series)
        monthly_totals = engine.monthly_series(bi_events, metric)["Total"]
        st.caption(f"Total in horizon: {bi_events[metric].sum():,.0f}"
                   f"{' USD' if metric == 'est_value_usd' else ' shares'} | busiest month: {monthly_totals.idxmax()}"
                   + (" | values use the base price path; low/high are not shown here" if is_range else ""))
        shown = series.round(0).reset_index()
        st.dataframe(shown, hide_index=True)
        st.download_button("Export chart data (CSV)", shown.to_csv(index=False).encode("utf-8"),
                           file_name="monthly_vesting_series.csv", mime="text/csv")

# ------------------------------------------------------------------ summary
with tab_summary:
    if ev.empty:
        st.info("No vesting events in this window.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("By month (USD)")
            st.bar_chart(summ["by_month"].set_index("month")["est_value_usd"])
            st.dataframe(summ["by_month"], hide_index=True)
        with c2:
            st.subheader("By company (USD)")
            st.bar_chart(summ["by_company"].set_index("company")["est_value_usd"])
            st.dataframe(summ["by_company"], hide_index=True)
        st.subheader("By country (USD)")
        st.bar_chart(summ["by_country"].set_index("country")["est_value_usd"])
        st.dataframe(summ["by_country"], hide_index=True)

# ------------------------------------------------------------------ by employee
with tab_people:
    if ev.empty:
        st.info("No vesting events in this window.")
    else:
        st.dataframe(summ["by_employee"], hide_index=True)
        pick = st.selectbox("Employee detail", summ["by_employee"]["employee_id"].head(500))
        emp_grants = data["grants"][data["grants"]["employee_id"] == pick]
        st.write(f"{len(emp_grants)} grant(s), each on its own schedule")
        st.dataframe(emp_grants, hide_index=True)
        st.dataframe(ev[ev["employee_id"] == pick], hide_index=True)

# ------------------------------------------------------------------ data quality
with tab_quality:
    findings = get_findings(data_dir)
    if findings.empty:
        st.success("All checks passed.")
    else:
        st.dataframe(findings, hide_index=True)
    t = data["tranches"]
    st.caption(f"Loaded {len(data['companies'])} companies, {len(data['employees']):,} employees, "
               f"{len(data['grants']):,} grants, {len(t):,} vesting events "
               f"({(t['status'] == 'Unvested').sum():,} unvested, {(t['status'] == 'Forfeited').sum():,} forfeited).")
    if st.button("Run schedule check"):
        rebuilt = engine.regenerate_tranches(data["grants"], data["schedules"])
        stored = t[t["status"] != "Forfeited"].merge(
            rebuilt, on=["grant_id", "vest_date", "shares_vesting"], how="left", indicator=True)
        mismatch = int((stored["_merge"] == "left_only").sum())
        st.write("Stored vesting events match the schedule templates." if mismatch == 0
                 else f"{mismatch} stored events differ from the schedule templates.")

# ------------------------------------------------------------------ what-if
with tab_whatif:
    st.write("See how one employee leaving changes the upcoming events. Nothing is saved.")
    active = data["employees"][data["employees"]["employment_status"] == "Active"]
    if companies:
        cid = data["companies"].loc[data["companies"]["company_name"].isin(companies), "company_id"]
        active = active[active["company_id"].isin(cid)]
    names = dict(zip(active["employee_id"], active["full_name"]))
    who = st.selectbox("Employee", list(names), format_func=lambda i: f"{i} - {names[i]}")
    term_date = st.date_input("Termination date", value=(pd.Timestamp(as_of) + pd.Timedelta(days=30)).date())
    mode = st.radio("Treatment of unvested shares", ["Forfeit (default)", "Accelerate (death / disability)"])
    changed = engine.simulate_termination(data["tranches"], who, term_date, accelerate=mode.startswith("Accel"))
    after = engine.upcoming_events(data, as_of, window_days, scenario, g_arg, v_arg, tranches=changed)
    b_sh, a_sh = window_all["shares_vesting"].sum(), after["shares_vesting"].sum()
    b_v, a_v = window_all["est_value_usd"].sum(), after["est_value_usd"].sum()
    w1, w2 = st.columns(2)
    w1.metric("Shares in window (all companies)", f"{a_sh:,.0f}", f"{a_sh - b_sh:+,.0f}")
    w2.metric("Est. value (USD)", f"${a_v:,.0f}", f"${a_v - b_v:+,.0f}")
    st.dataframe(after[after["employee_id"] == who], hide_index=True)

# ------------------------------------------------------------------ report
with tab_report:
    st.write("Build a client-ready report from the events currently shown (filters apply).")
    include_detail = st.checkbox("Include event detail", value=True)
    show_names = st.checkbox("Show employee names (otherwise IDs only)", value=False)
    if ev.empty:
        st.info("Nothing to report for this window and filters.")
    else:
        d1, d2 = st.columns(2)
        d1.download_button("Download Excel report", reports.build_excel(ev, summ, meta, include_detail, show_names),
                           file_name="upcoming_vesting_report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        d2.download_button("Download PDF report", reports.build_pdf(ev, summ, meta, include_detail, show_names),
                           file_name="upcoming_vesting_report.pdf", mime="application/pdf")
        if include_detail and len(ev) > 400:
            st.caption(f"The PDF will list all {len(ev):,} events and may run long. "
                       "Filter by company or shorten the window for a tighter report.")
