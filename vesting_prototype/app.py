"""Streamlit front end for the global equity vesting tracker prototype.

Two views over the same data:
  Current schedule - what is scheduled to vest, valued at today's share prices.
  What-if          - change prices, headcount or leave and compare with the current schedule.

Run from this folder:   streamlit run app.py
"""
import html as _html
from pathlib import Path

import pandas as pd
import streamlit as st

import charts
import engine
import reports

st.set_page_config(page_title="Equity Vesting Tracker", page_icon="📈", layout="wide",
                   initial_sidebar_state="collapsed")


def find_data_dir() -> str:
    """Use data/ next to this file, else CSVs sitting beside app.py, else generate the demo data once.

    This lets the app run even if only the code files were uploaded (for example from a phone, where
    folders cannot be created). The generated data is identical every time (fixed seed).
    """
    import os
    import runpy
    import tempfile
    here = Path(__file__).parent
    for d in (here / "data", here):
        if (d / "companies.csv").exists():
            return str(d)
    gen = Path(tempfile.gettempdir()) / "vesting_demo_data"
    if not (gen / "companies.csv").exists():
        with st.spinner("Generating the demo data (first load only, a few seconds)..."):
            os.environ["VESTING_DATA_DIR"] = str(gen)
            runpy.run_path(str(here / "generate_data.py"))
    return str(gen)


DEFAULT_DIR = find_data_dir()
HORIZON_DAYS = 1500  # events are computed once out to ~4 years; the window and chart slice from this
MODE_CUR, MODE_WI = "Current schedule", "What-if"
CARD_PAGE = 24

st.markdown(
    """<style>
    /* layout */
    [data-testid="stMainBlockContainer"],.block-container{max-width:1200px;padding-top:1.6rem}
    .hdr{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;margin:0 0 .15rem 0}
    .hdr-t{font-size:1.65rem;font-weight:700;letter-spacing:-.01em;line-height:1.2}
    .badge{font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;padding:.15rem .5rem;
           border-radius:999px;border:1px solid rgba(128,128,128,.4);opacity:.8}
    /* headline */
    .hero{background:linear-gradient(135deg,#1E3A8A 0%,#2563EB 100%);color:#fff;border-radius:.9rem;
          padding:1.1rem 1.3rem;margin:.6rem 0 .7rem 0}
    .hero-k{font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;opacity:.8}
    .hero-v{font-size:2.6rem;font-weight:700;line-height:1.15;letter-spacing:-.02em}
    .hero-s{font-size:.95rem;opacity:.92}
    .hero-d{font-size:.9rem;margin-top:.35rem;font-weight:600;background:rgba(255,255,255,.16);
            display:inline-block;padding:.1rem .55rem;border-radius:.4rem}
    .hero-r{font-size:.8rem;opacity:.8;margin-top:.25rem}
    /* small stat cards */
    .kpi-wrap{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.6rem;margin:0 0 .9rem 0}
    .kpi{background:var(--secondary-background-color);border-radius:.7rem;padding:.6rem .85rem}
    .kpi-l{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;opacity:.65}
    .kpi-v{font-size:1.4rem;font-weight:650;line-height:1.3}
    .kpi-d{font-size:.78rem;opacity:.85}
    .kpi-s{font-size:.72rem;opacity:.65}
    /* filter chips */
    .chips{display:flex;gap:.4rem;flex-wrap:wrap;margin:.2rem 0 .6rem 0;font-size:.82rem}
    .chip{background:var(--secondary-background-color);border-radius:999px;padding:.12rem .65rem}
    .chips-none{opacity:.6;font-size:.82rem;margin:.2rem 0 .6rem 0}
    /* vest cards */
    .vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:.6rem;margin:.3rem 0 .6rem 0}
    .vc{background:var(--secondary-background-color);border-radius:.7rem;padding:.7rem .85rem;
        border-left:4px solid #2563EB}
    .vc-top{display:flex;justify-content:space-between;font-size:.78rem;opacity:.75}
    .vc-name{font-weight:650;font-size:1rem;margin-top:.15rem}
    .vc-sub{font-size:.8rem;opacity:.7}
    .vc-row{display:flex;justify-content:space-between;align-items:baseline;margin-top:.35rem}
    .vc-val{font-size:1.15rem;font-weight:700}
    .vc-flag{font-size:.72rem;margin-top:.3rem;color:#EA580C}
    /* keep the 2 x 2 preset buttons side by side on phones */
    .st-key-presets [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:.5rem}
    .st-key-presets [data-testid="stColumn"]{min-width:0 !important;width:auto !important;flex:1 1 0 !important}
    @media (max-width:640px){
      [data-testid="stMainBlockContainer"],.block-container{padding-left:.8rem;padding-right:.8rem;padding-top:1rem}
      .hdr-t{font-size:1.35rem}
      .hero{padding:.9rem 1rem}
      .hero-v{font-size:2.2rem}
      .kpi-v{font-size:1.2rem}
      .vgrid{grid-template-columns:1fr}
    }
    </style>""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ helpers
def md(text: str) -> str:
    """Escape $ so Streamlit does not read dollar amounts as math."""
    return text.replace("$", "\\$")


def hx(text) -> str:
    """Make text safe inside our own HTML, including dollar signs."""
    return _html.escape(str(text)).replace("$", "&#36;")


def money(x: float) -> str:
    return f"${x:,.0f}"


def delta_text(new: float, old: float, as_money: bool = False) -> str:
    diff = new - old
    if abs(diff) < 0.5:
        return "no change"
    arrow = "&#9650;" if diff > 0 else "&#9660;"
    amt = charts.short_money(abs(diff)) if as_money else charts.short_num(abs(diff))
    pct = f" ({diff / old * 100:+.1f}%)" if old else ""
    return f"{arrow} {amt}{pct}".replace("$", "&#36;")


def kpi_html(cards) -> str:
    parts = ['<div class="kpi-wrap">']
    for label, value, delta, sub in cards:
        d = f'<div class="kpi-d">{delta}</div>' if delta else ""
        s = f'<div class="kpi-s">{hx(sub)}</div>' if sub else ""
        parts.append(f'<div class="kpi"><div class="kpi-l">{hx(label)}</div>'
                     f'<div class="kpi-v">{hx(value)}</div>{d}{s}</div>')
    parts.append("</div>")
    return "".join(parts)


def hero_html(kicker: str, value: str, sub: str, delta: str | None, rng: str | None) -> str:
    d = f'<div class="hero-d">{delta}</div>' if delta else ""
    r = f'<div class="hero-r">{hx(rng)}</div>' if rng else ""
    return (f'<div class="hero"><div class="hero-k">{hx(kicker)}</div><div class="hero-v">{hx(value)}</div>'
            f'<div class="hero-s">{hx(sub)}</div>{d}{r}</div>')


def cards_html(df: pd.DataFrame, share_decimals: int = 0) -> str:
    """One card per vesting event; wraps into a grid on desktop and a single column on a phone."""
    out = ['<div class="vgrid">']
    for r in df.itertuples():
        when = f"{r.vest_date:%b %d, %Y}"
        days = "today" if r.days_until <= 0 else f"in {r.days_until} day{'s' if r.days_until != 1 else ''}"
        flag = f'<div class="vc-flag">{hx(r.flags)}</div>' if r.flags else ""
        out.append(
            f'<div class="vc"><div class="vc-top"><span>{when}</span><span>{days}</span></div>'
            f'<div class="vc-name">{hx(r.full_name)}</div>'
            f'<div class="vc-sub">{hx(r.company)} &middot; {hx(r.country)}</div>'
            f'<div class="vc-row"><span>{r.shares_vesting:,.{share_decimals}f} shares</span>'
            f'<span class="vc-val">{hx(money(r.est_value_usd))}</span></div>{flag}</div>')
    out.append("</div>")
    return "".join(out)


def chips_html(parts: list[str]) -> str:
    if not parts:
        return '<div class="chips-none">No filters applied. Showing every company and country.</div>'
    return '<div class="chips">' + "".join(f'<span class="chip">{hx(p)}</span>' for p in parts) + "</div>"


def combine_series(cur_s: pd.DataFrame, wi_s: pd.DataFrame) -> pd.DataFrame:
    parts = {}
    if not cur_s.empty:
        parts["Current"] = cur_s["Total"]
    if not wi_s.empty:
        parts["What-if"] = wi_s["Total"]
    if not parts:
        return pd.DataFrame()
    idx = sorted(set().union(*[set(p.index) for p in parts.values()]))
    full = pd.period_range(idx[0], idx[-1], freq="M").astype(str)
    out = pd.DataFrame(parts).reindex(full).fillna(0)
    out.index.name = "month"
    return out


def compare_table(cur: pd.DataFrame, wi: pd.DataFrame, key: str, metric: str) -> pd.DataFrame:
    a = cur.groupby(key)[metric].sum().rename("Current")
    b = wi.groupby(key)[metric].sum().rename("What-if")
    t = pd.concat([a, b], axis=1).fillna(0)
    t["Change"] = t["What-if"] - t["Current"]
    return t


def top_n_split(series: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    """Keep the n biggest lines and fold the rest into 'Other' so the chart stays readable."""
    if series.shape[1] <= n:
        return series
    order = series.sum().sort_values(ascending=False).index
    out = series[list(order[:n])].copy()
    out["Other"] = series[list(order[n:])].sum(axis=1)
    return out


# ------------------------------------------------------------------ cached work
@st.cache_resource(show_spinner="Loading data...")
def get_data(data_dir: str):
    return engine.load_data(data_dir)


@st.cache_data(show_spinner=False)
def get_findings(data_dir: str):
    return engine.validate(get_data(data_dir))


@st.cache_data(show_spinner="Calculating the current schedule...")
def get_current_events(data_dir: str, as_of):
    return engine.upcoming_events(get_data(data_dir), as_of, HORIZON_DAYS, "Flat")


@st.cache_data(show_spinner="Calculating your what-if...")
def get_whatif_events(data_dir: str, as_of, scenario, growth, vol, shock, attrition, actions_key):
    data = get_data(data_dir)
    actions = [{"kind": k, "employee_ids": list(ids), "date": d, "months": m} for k, ids, d, m in actions_key]
    tr = engine.apply_actions(data["tranches"], actions) if actions else None
    return engine.upcoming_events(data, as_of, HORIZON_DAYS, scenario, growth, vol, tr, shock, attrition)


@st.cache_data(show_spinner="Working out what changed...")
def get_bridge(data_dir: str, as_of, scenario, growth, vol, shock, attrition, actions_key):
    """Events after each what-if lever is applied in turn, trimmed to the columns the bridge needs."""
    data = get_data(data_dir)
    actions = [{"kind": k, "employee_ids": list(ids), "date": d, "months": m} for k, ids, d, m in actions_key]
    tr = engine.apply_actions(data["tranches"], actions) if actions else None
    keep = ["days_until", "company", "country", "department", "employee_id", "full_name", "est_value_usd"]
    return [(label, ev[keep]) for label, ev in
            engine.whatif_steps(data, as_of, 365, scenario, growth, vol, tr, shock, attrition)]


@st.cache_data(show_spinner=False)
def events_xlsx(ev, filters_text, meta):
    return reports.build_data_workbook(ev, filters_text, meta)


@st.cache_data(show_spinner="Building the report...")
def report_xlsx(ev, summ, meta, include_detail, show_names):
    return reports.build_excel(ev, summ, meta, include_detail, show_names)


@st.cache_data(show_spinner="Building the PDF...")
def report_pdf(ev, summ, meta, include_detail, show_names):
    return reports.build_pdf(ev, summ, meta, include_detail, show_names)


# ------------------------------------------------------------------ state + data
ss = st.session_state
ss.setdefault("actions", [])
ss.setdefault("card_n", CARD_PAGE)
data_dir = ss.get("data_dir", DEFAULT_DIR)
try:
    data = get_data(data_dir)
except Exception as exc:  # missing folder / file
    st.error(f"Could not load data from '{data_dir}': {exc}")
    st.text_input("Data folder", value=DEFAULT_DIR, key="data_dir")
    st.stop()
market = data["market"]
emp_lookup = data["employees"].set_index("employee_id")


def clear_filters():
    ss["f_company"], ss["f_country"], ss["f_dept"], ss["f_search"] = [], [], [], ""


def reset_whatif():
    ss["w_scenario"], ss["w_shock"], ss["w_attr"], ss["w_own"] = "Flat", 0, 0.0, True
    ss["w_growth"], ss["w_vol"], ss["actions"] = 8.0, 35.0, []


def preset(shock=None, attr=None):
    reset_whatif()
    if shock is not None:
        ss["w_shock"] = shock
    if attr is not None:
        ss["w_attr"] = attr


# ------------------------------------------------------------------ header + controls
st.markdown('<div class="hdr"><span class="hdr-t">Equity Vesting Tracker</span>'
            '<span class="badge">Synthetic data</span></div>', unsafe_allow_html=True)

c_mode, c_asof, c_win, c_filt = st.columns([2.2, 1, 1, 1])
with c_mode:
    if hasattr(st, "segmented_control"):
        mode = st.segmented_control("View", [MODE_CUR, MODE_WI], default=MODE_CUR, key="mode") or MODE_CUR
    else:
        mode = st.radio("View", [MODE_CUR, MODE_WI], horizontal=True, key="mode")
as_of = c_asof.date_input("As of", value=market["price_date"].max().date())
window_label = c_win.selectbox("Window", ["30 days", "90 days", "180 days", "365 days"], index=1)
window_days = int(window_label.split()[0])
is_whatif = mode == MODE_WI

with c_filt:
    st.markdown('<div style="height:1.7rem"></div>', unsafe_allow_html=True)
    with st.popover("Filters", use_container_width=True):
        companies = st.multiselect("Company", sorted(data["companies"]["company_name"]), key="f_company")
        countries = st.multiselect("Country", sorted(data["employees"]["country"].dropna().unique()), key="f_country")
        departments = st.multiselect("Department", sorted(data["employees"]["department"].dropna().unique()),
                                     key="f_dept")
        search = st.text_input("Employee name or ID contains", key="f_search")
        st.button("Clear filters", on_click=clear_filters, use_container_width=True)

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
st.markdown(chips_html(filter_parts), unsafe_allow_html=True)


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


as_of_ts = pd.Timestamp(as_of)
cur_all = get_current_events(data_dir, as_of_ts)

# ------------------------------------------------------------------ what-if builder
scenario, g_arg, v_arg, shock, attr = "Flat", None, None, 0.0, 0.0
if is_whatif:
    with st.container(border=True):
        st.markdown("**Build your what-if**  \nNothing is saved. Changes are compared with the current schedule.")
        try:
            pbox = st.container(key="presets")
        except TypeError:  # older Streamlit without container keys
            pbox = st.container()
        with pbox:
            p1, p2 = st.columns(2)
            p1.button("Market down 20%", on_click=preset, kwargs={"shock": -20}, use_container_width=True)
            p2.button("Market up 20%", on_click=preset, kwargs={"shock": 20}, use_container_width=True)
            p3, p4 = st.columns(2)
            p3.button("15% attrition", on_click=preset, kwargs={"attr": 15.0}, use_container_width=True)
            p4.button("Reset", on_click=reset_whatif, use_container_width=True)

        t_price, t_people = st.tabs(["Prices", "People and leave"])
        with t_price:
            scenario = st.selectbox("Price path", engine.SCENARIOS, key="w_scenario")
            shock = st.slider("Change today's share prices by (%)", -50, 50, 0, 1, key="w_shock") / 100
            if scenario != "Flat":
                own = st.checkbox("Use each company's own growth and volatility", value=True, key="w_own")
                gcol, vcol = st.columns(2)
                growth = gcol.slider("Annual growth (%)", -20.0, 40.0, 8.0, 0.5, key="w_growth", disabled=own) / 100
                vol = vcol.slider("Annual volatility (%)", 5.0, 80.0, 35.0, 1.0, key="w_vol",
                                  disabled=own or not scenario.startswith("Range")) / 100
                g_arg, v_arg = (None, None) if own else (growth, vol)

        with t_people:
            attr = st.slider("Assumed annual attrition (%)", 0.0, 30.0, 0.0, 0.5, key="w_attr") / 100
            st.caption("Attrition scales unvested shares by the chance each person is still employed at the vest "
                       "date. It is an expected value, so shares can be fractional.")
            st.markdown("**Add a people event**")
            who_mode = st.radio("Who", ["Specific employees", "Everyone in the filters"], horizontal=True,
                                key="w_who")
            cand = sorted(apply_filters(cur_all)["employee_id"].unique())
            if who_mode == "Specific employees":
                ids = st.multiselect(
                    "Employees", cand, key="w_ids",
                    format_func=lambda i: f"{i} - {emp_lookup.loc[i, 'full_name']} ({emp_lookup.loc[i, 'country']})")
            else:
                ids = cand
                st.caption(f"{len(ids):,} people with upcoming vesting match the filters.")
            e1, e2, e3 = st.columns([3, 1, 1])
            kind = e1.selectbox("What happens", list(engine.ACTION_KINDS), format_func=engine.ACTION_KINDS.get,
                                key="w_kind")
            ev_date = e2.date_input("From", value=(as_of_ts + pd.Timedelta(days=30)).date(), key="w_date")
            months = e3.number_input("Pause (months)", 1, 24, 3, key="w_months", disabled=(kind != "leave"))
            if st.button("Add event"):
                if not ids:
                    st.warning("Pick at least one employee, or loosen the filters.")
                else:
                    label = (f"{len(ids)} people" if len(ids) > 1
                             else f"{ids[0]} ({emp_lookup.loc[ids[0], 'full_name']})")
                    ss["actions"].append({"kind": kind, "employee_ids": tuple(ids), "date": str(ev_date),
                                          "months": int(months) if kind == "leave" else 0, "label": label})
            if ss["actions"]:
                st.dataframe(pd.DataFrame([{"Event": engine.ACTION_KINDS[a["kind"]], "People": a["label"],
                                            "From": a["date"], "Pause (months)": a["months"] or None}
                                           for a in ss["actions"]]), hide_index=True)
                r1, r2, _ = st.columns([1, 1, 3])
                if r1.button("Remove last"):
                    ss["actions"].pop()
                    st.rerun()
                if r2.button("Clear events"):
                    ss["actions"] = []
                    st.rerun()

actions_key = tuple((a["kind"], tuple(a["employee_ids"]), a["date"], a["months"]) for a in ss["actions"])
neutral = scenario == "Flat" and not shock and not attr and not ss["actions"]


def describe_levers() -> str:
    parts = []
    if scenario != "Flat":
        parts.append(f"{scenario.split(' (')[0].lower()} price path "
                     f"({'company assumptions' if g_arg is None else f'{g_arg:.1%} growth'})")
    if shock:
        parts.append(f"share prices {shock:+.0%} today")
    if attr:
        parts.append(f"{attr:.1%} annual attrition")
    short = {"terminate_forfeit": "departure (unvested shares forfeit)",
             "terminate_accelerate": "departure (unvested shares accelerate)",
             "leave": "leave of absence"}
    for a in ss["actions"]:
        txt = f"{short[a['kind']]} for {a['label']} from {a['date']}"
        parts.append(txt + (f", vesting paused {a['months']} months" if a["kind"] == "leave" else ""))
    return "; ".join(parts) or "no changes yet"


wi_all = (get_whatif_events(data_dir, as_of_ts, scenario, g_arg, v_arg, shock, attr, actions_key)
          if is_whatif else None)


def prep(df: pd.DataFrame) -> pd.DataFrame:
    return apply_filters(df[df["days_until"] <= window_days])


cur_ev = prep(cur_all)
wi_ev = prep(wi_all) if is_whatif else None
ev = wi_ev if is_whatif else cur_ev
levers = describe_levers() if is_whatif else ""
summ = engine.summarize(ev)
is_range = scenario.startswith("Range") and is_whatif

# ------------------------------------------------------------------ headline + summary cards
if is_whatif:
    if neutral:
        st.info("No changes yet. Pick a preset above, move a slider, or add a people event to see the impact.")
    else:
        st.caption(md(f"What-if: {levers}."))

total_val = ev["est_value_usd"].sum()
n_people, n_cos = ev["employee_id"].nunique(), ev["company"].nunique()
hero_delta = None
if is_whatif and not neutral:
    hero_delta = delta_text(total_val, cur_ev["est_value_usd"].sum(), True) + " vs current schedule"
st.markdown(hero_html(
    f"{'What-if' if is_whatif else 'Estimated'} value vesting in the next {window_days} days",
    charts.short_money(total_val),
    f"{len(ev):,} vesting events across {n_people:,} people at {n_cos:,} "
    f"{'company' if n_cos == 1 else 'companies'}",
    hero_delta,
    f"Range {charts.short_money(ev['est_value_low'].sum())} to {charts.short_money(ev['est_value_high'].sum())}"
    if is_range else None), unsafe_allow_html=True)

st.markdown(kpi_html([
    ("Shares vesting", charts.short_num(ev["shares_vesting"].sum()),
     delta_text(ev["shares_vesting"].sum(), cur_ev["shares_vesting"].sum()) if is_whatif and not neutral else None, None),
    ("Vesting events", f"{len(ev):,}",
     delta_text(len(ev), len(cur_ev)) if is_whatif and not neutral else None, None),
    ("People", f"{n_people:,}",
     delta_text(n_people, cur_ev["employee_id"].nunique()) if is_whatif and not neutral else None, None),
    ("Companies", f"{n_cos:,}", None, None),
]), unsafe_allow_html=True)

if ev.empty:
    st.info("No vesting events match this window and these filters. Try a longer window or clear the filters.")

if len(companies) == 1:
    title_company = companies[0]
    price_text = f"{market.loc[market['company'] == companies[0], 'price_usd'].iloc[0]:,.2f}"
else:
    title_company = "All companies" if not companies else "Selected companies"
    price_text = "Varies by company (see market data)"
if shock and price_text[0].isdigit():
    price_text += f" before a {shock:+.0%} what-if change"
meta = {
    "company": title_company, "report_date": f"{pd.Timestamp.today():%Y-%m-%d}",
    "price_date": f"{market['price_date'].max():%Y-%m-%d}",
    "window": f"Next {window_days} days from {as_of:%Y-%m-%d}",
    "price": 0.0, "price_text": price_text, "scenario": scenario, "growth": 0.0, "vol": 0.0,
    "growth_text": "Company-specific (from market data)" if g_arg is None else f"{g_arg:.1%} (all companies)",
    "vol_text": "Company-specific (from market data)" if v_arg is None else f"{v_arg:.1%} (all companies)",
    "filters": "" if filters_text == "None" else filters_text, "data_note": "Synthetic demonstration data.",
    "view": "What-if scenario (hypothetical)" if is_whatif else "Current schedule", "levers": levers,
}

tab_over, tab_events, tab_people, tab_report = st.tabs(["Overview", "Events", "People", "Reports and data"])

# ------------------------------------------------------------------ overview
with tab_over:
    st.markdown("**Vesting by month**")
    with st.expander("Chart options"):
        b1, b2 = st.columns(2)
        horizon_label = b1.selectbox("Horizon", ["12 months", "24 months", "36 months", "48 months"], index=1)
        split_label = b2.selectbox("Split lines by", ["None (total)", "Company", "Country", "Department"])
        b3, b4 = st.columns(2)
        metric_label = b3.radio("Measure", ["Estimated value (USD)", "Shares vesting"])
        cumulative = b4.checkbox("Cumulative", value=False)
    bi_end = as_of_ts + pd.DateOffset(months=int(horizon_label.split()[0]))
    metric = "shares_vesting" if metric_label.startswith("Shares") else "est_value_usd"
    is_money = metric == "est_value_usd"
    by = {"None (total)": None, "Company": "company", "Country": "country", "Department": "department"}[split_label]
    cur_bi = apply_filters(cur_all[cur_all["vest_date"] <= bi_end])
    wi_bi = apply_filters(wi_all[wi_all["vest_date"] <= bi_end]) if is_whatif else None

    compare = False
    if is_whatif and by is None:
        series = combine_series(engine.monthly_series(cur_bi, metric, None, cumulative),
                                engine.monthly_series(wi_bi, metric, None, cumulative))
        compare = {"Current", "What-if"} <= set(series.columns)
    elif is_whatif:
        series = top_n_split(engine.monthly_series(wi_bi, metric, by, cumulative))
        st.caption("Split view shows the what-if only. Set 'Split lines by' to None to compare with current.")
    else:
        series = top_n_split(engine.monthly_series(cur_bi, metric, by, cumulative))

    if series.empty:
        st.info("No vesting events match the filters in this horizon.")
    else:
        long_df, spec = charts.monthly_chart(series, is_money, compare)
        st.vega_lite_chart(long_df, spec, use_container_width=True)
        shown_df = wi_bi if is_whatif else cur_bi
        peak = engine.monthly_series(shown_df, metric)["Total"].idxmax()
        total_txt = charts.short_money(shown_df[metric].sum()) if is_money else f"{shown_df[metric].sum():,.0f} shares"
        st.caption(md(f"{'What-if' if is_whatif else 'Current'} total in horizon: {total_txt}. "
                      f"Busiest month: {pd.Period(peak).strftime('%b %Y')}."))
        with st.expander("Show chart data"):
            table = series.round(0)
            if compare:
                table["Change"] = table["What-if"] - table["Current"]
            table = table.reset_index()
            st.dataframe(table, hide_index=True)
            st.download_button("Export chart data (CSV)", table.to_csv(index=False).encode("utf-8"),
                               file_name="monthly_vesting_series.csv", mime="text/csv")

    # what changed (bridge)
    if is_whatif and not neutral:
        st.markdown(f"**What changed** (next {window_days} days)")
        bridge = get_bridge(data_dir, as_of_ts, scenario, g_arg, v_arg, shock, attr, actions_key)
        totals = [(label, apply_filters(e[e["days_until"] <= window_days])["est_value_usd"].sum())
                  for label, e in bridge]
        if len(totals) > 1 and any(t for _, t in totals):
            bdf, bspec = charts.bridge_chart(totals)
            st.vega_lite_chart(bdf, bspec, use_container_width=True)
            st.caption("Each bar applies one change on top of the one before it, in this order: people events, "
                       "attrition, share price change, price path. A different order would split the effect "
                       "slightly differently, but the start and end always match the cards above.")

    # up next
    if not ev.empty:
        st.markdown("**Up next**")
        st.markdown(cards_html(ev.sort_values(["vest_date", "est_value_usd"], ascending=[True, False]).head(10),
                               1 if attr else 0), unsafe_allow_html=True)

        # where it vests
        dims = [("company", "By company"), ("country", "By country")]
        if n_cos == 1:
            dims = [("country", "By country"), ("department", "By department")]
        st.markdown("**Where it vests**")
        bm = "est_value_usd"
        cols = st.columns(2)
        for col, (key, title) in zip(cols, dims):
            with col:
                st.caption(title + (" (grey tick = current schedule)" if is_whatif and not neutral else ""))
                if is_whatif:
                    t = compare_table(cur_ev, wi_ev, key, bm).sort_values("What-if", ascending=False).head(8)
                    shown, base = t["What-if"], (t["Current"] if not neutral else None)
                else:
                    t = cur_ev.groupby(key)[bm].sum().sort_values(ascending=False).head(8).to_frame("Current")
                    shown, base = t["Current"], None
                bdf, bspec = charts.bullet_chart(t.index, shown, base, True)
                st.vega_lite_chart(bdf, bspec, use_container_width=True)
        with st.expander("Show breakdown tables"):
            m_label = st.radio("Measure ", ["Estimated value (USD)", "Shares vesting"], horizontal=True)
            tm = "est_value_usd" if m_label.startswith("Estimated") else "shares_vesting"
            for key, title in (("month", "By month"), ("company", "By company"), ("country", "By country")):
                st.markdown(f"**{title}**")
                if is_whatif:
                    t = compare_table(cur_ev, wi_ev, key, tm)
                else:
                    t = cur_ev.groupby(key)[tm].sum().rename("Current").to_frame()
                if key != "month":
                    t = t.sort_values(t.columns[1] if is_whatif else "Current", ascending=False)
                st.dataframe(t.round(0).reset_index(), hide_index=True)

# ------------------------------------------------------------------ events
with tab_events:
    show_changes = False
    if is_whatif:
        show_changes = st.radio("Show", ["All what-if events", "Timing changes only"], horizontal=True) \
            == "Timing changes only"
    if show_changes:
        diff = engine.diff_events(cur_ev, wi_ev)
        st.write(f"**{len(diff):,}** events were forfeited, accelerated, delayed or moved. "
                 "Price and attrition assumptions are not listed here.")
        if diff.empty:
            st.info("No timing changes. Add a leave or termination event to see them here.")
        else:
            st.download_button("Export CSV", diff.to_csv(index=False).encode("utf-8"),
                               file_name="what_if_timing_changes.csv", mime="text/csv")
            st.dataframe(diff, hide_index=True, column_config={
                "current_date": st.column_config.DateColumn("Current date", format="YYYY-MM-DD"),
                "whatif_date": st.column_config.DateColumn("What-if date", format="YYYY-MM-DD"),
                "value_change": st.column_config.NumberColumn("Value change (USD)", format="$%.0f")})
    else:
        st.write(f"**{len(ev):,}** events match the active filters.")
        if ev.empty:
            st.info("No vesting events match. Try widening the window or clearing filters.")
        else:
            x1, x2 = st.columns(2)
            x1.download_button("Export CSV", ev.to_csv(index=False).encode("utf-8"),
                               file_name="vesting_events_filtered.csv", mime="text/csv", use_container_width=True)
            x2.download_button("Export Excel", events_xlsx(ev, filters_text, meta),
                               file_name="vesting_events_filtered.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
            layout = (st.segmented_control("Layout", ["Cards", "Table"], default="Cards", key="ev_layout")
                      if hasattr(st, "segmented_control")
                      else st.radio("Layout", ["Cards", "Table"], horizontal=True, key="ev_layout")) or "Cards"
            if layout == "Cards":
                n = min(ss["card_n"], len(ev))
                st.markdown(cards_html(ev.head(n), 1 if attr else 0), unsafe_allow_html=True)
                if n < len(ev):
                    st.caption(f"Showing {n:,} of {len(ev):,}, soonest first.")
                    if st.button(f"Show {min(CARD_PAGE, len(ev) - n)} more", use_container_width=True):
                        ss["card_n"] = n + CARD_PAGE
                        st.rerun()
            else:
                all_cols = st.checkbox("Show all columns", value=False)
                compact = ["vest_date", "company", "full_name", "country", "shares_vesting", "est_price_usd",
                           "est_value_usd", "flags"]
                share_fmt = "%.1f" if attr else "%.0f"
                st.dataframe(
                    ev, hide_index=True, column_order=None if all_cols else compact,
                    column_config={
                        "vest_date": st.column_config.DateColumn("Vest date", format="YYYY-MM-DD"),
                        "shares_vesting": st.column_config.NumberColumn("Shares", format=share_fmt),
                        "est_price_usd": st.column_config.NumberColumn("Est. price", format="$%.2f"),
                        "est_price_low": st.column_config.NumberColumn("Price low", format="$%.2f"),
                        "est_price_high": st.column_config.NumberColumn("Price high", format="$%.2f"),
                        "est_value_usd": st.column_config.NumberColumn("Est. value (USD)", format="$%.0f"),
                        "est_value_low": st.column_config.NumberColumn("Value low", format="$%.0f"),
                        "est_value_high": st.column_config.NumberColumn("Value high", format="$%.0f"),
                        "est_value_local": st.column_config.NumberColumn("Est. value (local)", format="%.0f"),
                    })
            st.caption("Shares are gross, before tax withholding. Orange notes mark items needing review.")

# ------------------------------------------------------------------ people
with tab_people:
    if ev.empty:
        st.info("No vesting events in this window.")
    else:
        by_emp = summ["by_employee"].copy()
        if is_whatif:
            cur_emp = cur_ev.groupby("employee_id")["est_value_usd"].sum()
            by_emp["value_change"] = by_emp["employee_id"].map(cur_emp).fillna(0)
            by_emp["value_change"] = by_emp["est_value_usd"] - by_emp["value_change"]
        st.dataframe(by_emp.head(1000), hide_index=True)
        pick = st.selectbox("Employee detail", by_emp["employee_id"].head(500))
        emp_grants = data["grants"][data["grants"]["employee_id"] == pick]
        st.write(f"{len(emp_grants)} grant(s), each on its own schedule")
        st.dataframe(emp_grants, hide_index=True)
        st.dataframe(ev[ev["employee_id"] == pick], hide_index=True)

# ------------------------------------------------------------------ reports and data
with tab_report:
    st.markdown("**Client report**")
    st.write("Build a client-ready report from the events currently shown. The active view and filters apply"
             + (", and the report is labeled as a hypothetical what-if." if is_whatif else "."))
    include_detail = st.checkbox("Include event detail", value=True)
    show_names = st.checkbox("Show employee names (otherwise IDs only)", value=False)
    if ev.empty:
        st.info("Nothing to report for this window and filters.")
    else:
        prepare = st.checkbox("Prepare downloads", value=False,
                              help="Building the Excel and PDF takes a few seconds, so it only runs when ticked.")
        if prepare:
            d1, d2 = st.columns(2)
            d1.download_button("Download Excel report", report_xlsx(ev, summ, meta, include_detail, show_names),
                               file_name="upcoming_vesting_report.xlsx", use_container_width=True,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            d2.download_button("Download PDF report", report_pdf(ev, summ, meta, include_detail, show_names),
                               file_name="upcoming_vesting_report.pdf", mime="application/pdf",
                               use_container_width=True)
            if include_detail and len(ev) > 400:
                st.caption(f"The PDF lists all {len(ev):,} events and may run long. "
                           "Filter by company or shorten the window for a tighter report.")

    st.divider()
    st.markdown("**Data**")
    with st.expander("Data source"):
        st.text_input("Data folder", value=DEFAULT_DIR, key="data_dir")
    findings = get_findings(data_dir)
    if findings.empty:
        st.success("All data checks passed.")
    else:
        st.dataframe(findings, hide_index=True)
    t = data["tranches"]
    st.caption(f"Loaded {len(data['companies'])} companies, {len(data['employees']):,} employees, "
               f"{len(data['grants']):,} grants, {len(t):,} vesting events "
               f"({(t['status'] == 'Unvested').sum():,} unvested, {(t['status'] == 'Forfeited').sum():,} forfeited). "
               "Synthetic demonstration data.")
    if st.button("Run schedule check"):
        rebuilt = engine.regenerate_tranches(data["grants"], data["schedules"])
        stored = t[t["status"] != "Forfeited"].merge(
            rebuilt, on=["grant_id", "vest_date", "shares_vesting"], how="left", indicator=True)
        mismatch = int((stored["_merge"] == "left_only").sum())
        st.write("Stored vesting events match the schedule templates." if mismatch == 0
                 else f"{mismatch} stored events differ from the schedule templates.")
