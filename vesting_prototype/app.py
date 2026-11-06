"""Streamlit front end for the global equity vesting tracker prototype.

Two views over the same data:
  Current schedule - what is scheduled to vest, valued at today's share prices.
  What-if          - change prices, headcount or leave and compare with the current schedule.

Run from this folder:   streamlit run app.py
"""
import html as _html
import json
from pathlib import Path

import pandas as pd
import streamlit as st

import charts
import ai_story
import engine
import learn
import reports
import rules as R

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
    import re
    here = Path(__file__).parent
    # the as-of date the generator is set to; a data folder is only reused if it was built for that date
    m = re.search(r"AS_OF = date\((\d+), (\d+), (\d+)\)", (here / "generate_data.py").read_text())
    stamp = f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}" if m else ""
    for d in (here / "data", here):
        # skip a data folder that predates the award-type update (no 'settlement' column) or an older as-of date
        if ((d / "companies.csv").exists() and "settlement" in (d / "grants.csv").read_text().split("\n", 1)[0]
                and stamp in (d / "market_data.csv").read_text()):
            return str(d)
    gen = Path(tempfile.gettempdir()) / f"vesting_demo_data_{stamp or 'v3'}"
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
    [data-testid="stMainBlockContainer"],.block-container{max-width:1200px;padding-top:4.5rem}
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
    .vgrid.one{grid-template-columns:1fr;margin-bottom:.15rem}
    .tag{font-size:.68rem;font-weight:600;padding:.05rem .45rem;border-radius:.35rem;background:rgba(37,99,235,.14);
         color:var(--text-color);margin-right:.3rem;white-space:nowrap}
    .tag.cash{background:rgba(13,148,136,.2)}
    .tags{margin-top:.25rem}
    .explain{border-left:4px solid #2563EB;background:var(--secondary-background-color);border-radius:.5rem;
             padding:.6rem .85rem;margin:.4rem 0 .8rem 0;font-size:.92rem}
    .explain b{font-weight:650}
    .tabnote{font-size:.88rem;opacity:.8;margin:.1rem 0 .7rem 0}
    .scen{border:1px solid rgba(37,99,235,.45);background:rgba(37,99,235,.08);border-radius:.6rem;
          padding:.55rem .85rem;margin:.2rem 0 .7rem 0;font-size:.92rem}
    .scen .sk{font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;opacity:.65}
    .steps{display:flex;gap:.4rem;flex-wrap:wrap;margin:.1rem 0 .5rem 0}
    .steps span{font-size:.8rem;background:var(--secondary-background-color);border-radius:.4rem;padding:.15rem .55rem}
    .ck{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.5rem;margin:.3rem 0 .8rem 0}
    .ck>div{background:var(--secondary-background-color);border-radius:.6rem;padding:.55rem .75rem;font-size:.88rem}
    .ck b{display:block;font-size:1.05rem}
    .kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:.5rem .9rem;margin:.3rem 0 .8rem 0}
    .kv-i{border-bottom:1px solid rgba(128,128,128,.25);padding:.25rem 0}
    .kv-k{font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;opacity:.6}
    .kv-v{font-size:.95rem;font-weight:550;word-break:break-word}
    /* keep the 2 x 2 preset buttons side by side on phones */
    .st-key-presets [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:.5rem}
    .st-key-presets [data-testid="stColumn"]{min-width:0 !important;width:auto !important;flex:1 1 0 !important}
    @media (max-width:640px){
      [data-testid="stMainBlockContainer"],.block-container{padding-left:.8rem;padding-right:.8rem;padding-top:4rem}
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
# ------------------------------------------------------------------ top-level section switch
SEC_APP, SEC_AI = "Vesting tool", "How I used AI"
st.session_state.setdefault("section", SEC_APP)
if hasattr(st, "segmented_control"):
    _sec = st.segmented_control("Section", [SEC_APP, SEC_AI], key="section", label_visibility="collapsed") or SEC_APP
else:
    _sec = st.radio("Section", [SEC_APP, SEC_AI], horizontal=True, key="section", label_visibility="collapsed")
if _sec == SEC_AI:
    # keep the vesting tool's widget state while its widgets are not drawn (Streamlit drops it otherwise)
    # Only these keys: re-saving a button or download button key makes Streamlit raise an error later.
    for _k in ("mode", "f_company", "f_country", "f_dept", "f_award", "f_search", "ev_layout", "data_dir", "r_view",
               "r_scope", "r_event", "g_topic", "g_award", "g_event", "o_horizon", "o_split", "o_measure", "o_cumul",
               "w_scenario", "w_shock", "w_own", "w_growth", "w_vol", "w_attr", "w_pay_all", "w_who", "w_kind", "w_ids",
               "w_date", "w_months"):
        if _k in st.session_state:
            try:
                st.session_state[_k] = st.session_state[_k]
            except Exception:
                pass
    ai_story.render()
    st.stop()


def md(text: str) -> str:
    """Escape $ so Streamlit does not read dollar amounts as math."""
    return text.replace("$", "\\$")


def hx(text) -> str:
    """Make text safe inside our own HTML, including dollar signs."""
    return _html.escape(str(text)).replace("$", "&#36;")


def money(x: float) -> str:
    return f"${x:,.0f}"


def price(x: float) -> str:
    """Share prices and strikes need cents; totals do not."""
    return f"${x:,.2f}"


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


UNKNOWN_AWARD = {"name": "Unrecognized award type", "tagline": "", "what": "This award type is not in the guide.",
                 "value": "Units \u00d7 share price."}


def unit_text(r, decimals: int = 0) -> str:
    """How many units, in words that fit the award type."""
    if r.award_type == "Performance Cash":
        return f"{money(r.shares_vesting)} target &times; {r.payout_pct:.0f}%".replace("$", "&#36;") \
            if r.payout_pct != 100 else f"{money(r.shares_vesting)} cash".replace("$", "&#36;")
    word = {"Stock Option": "options", "SAR (stock-settled)": "SARs", "SAR (cash-settled)": "SARs",
            "Phantom Stock": "phantom units", "ESPP": "shares bought"}.get(r.award_type, "shares")
    extra = f" &middot; strike {price(r.strike_price)}".replace("$", "&#36;") if r.award_type in R.OPTION_LIKE else ""
    return f"{r.shares_vesting:,.{decimals}f} {word}{extra}"


def cards_html(df: pd.DataFrame, share_decimals: int = 0, single: bool = False) -> str:
    """One card per vesting event; wraps into a grid on desktop and a single column on a phone."""
    out = ['<div class="vgrid one">' if single else '<div class="vgrid">']
    for r in df.itertuples():
        when = f"{r.vest_date:%b %d, %Y}"
        days = ('<b title="Lapse day: the vest date">L-0 &middot; today</b>' if r.days_until <= 0 else
                f'<b title="{r.days_until} days before the lapse (vest) day">L-{r.days_until}</b>')
        flag = f'<div class="vc-flag">{hx(r.flags)}</div>' if r.flags else ""
        out.append(
            f'<div class="vc"><div class="vc-top"><span>{when}</span><span>{days}</span></div>'
            f'<div class="vc-name">{hx(r.full_name)}</div>'
            f'<div class="vc-sub">{hx(r.company)} &middot; {hx(r.country)}</div>'
            f'<div class="tags"><span class="tag" title="{hx(learn.AWARDS.get(r.award_type, UNKNOWN_AWARD)["tagline"])}">{hx(r.award_type)}</span>'
            f'<span class="tag{" cash" if r.settlement == "Cash" else ""}">Paid in {hx(r.settlement.lower())}</span></div>'
            f'<div class="vc-row"><span>{unit_text(r, share_decimals)}</span>'
            f'<span class="vc-val">{hx(money(r.est_value_usd))}</span></div>{flag}</div>')
    out.append("</div>")
    return "".join(out)


def kv_html(pairs) -> str:
    return '<div class="kv">' + "".join(
        f'<div class="kv-i"><div class="kv-k">{hx(k)}</div><div class="kv-v">{hx(v)}</div></div>'
        for k, v in pairs) + "</div>"


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
def get_whatif_events(data_dir: str, as_of, scenario, growth, vol, shock, attrition, actions_key, rules_json,
                      payout_json):
    data = get_data(data_dir)
    actions = [{"kind": k, "employee_ids": list(ids), "date": d, "months": m} for k, ids, d, m in actions_key]
    tr = engine.apply_actions(data["tranches"], actions, data, json.loads(rules_json)) if actions else None
    return engine.upcoming_events(data, as_of, HORIZON_DAYS, scenario, growth, vol, tr, shock, attrition,
                                  json.loads(payout_json) or None)


@st.cache_data(show_spinner=False)
def get_whatif_tranches(data_dir: str, actions_key, rules_json, emp_id):
    """One person's stored vests after the what-if people events (so forfeited vests show as forfeited)."""
    data = get_data(data_dir)
    actions = [{"kind": k, "employee_ids": list(ids), "date": d, "months": m} for k, ids, d, m in actions_key]
    tr = engine.apply_actions(data["tranches"], actions, data, json.loads(rules_json))
    return tr[tr["employee_id"] == emp_id].copy()


@st.cache_data(show_spinner="Working out what changed...")
def get_bridge(data_dir: str, as_of, scenario, growth, vol, shock, attrition, actions_key, rules_json, payout_json):
    """Events after each what-if lever is applied in turn, trimmed to the columns the bridge needs."""
    data = get_data(data_dir)
    actions = [{"kind": k, "employee_ids": list(ids), "date": d, "months": m} for k, ids, d, m in actions_key]
    tr = engine.apply_actions(data["tranches"], actions, data, json.loads(rules_json)) if actions else None
    keep = ["days_until", "company", "country", "department", "employee_id", "full_name", "award_type", "est_value_usd"]
    return [(label, ev[keep]) for label, ev in
            engine.whatif_steps(data, as_of, 365, scenario, growth, vol, tr, shock, attrition,
                                json.loads(payout_json) or None)]


@st.cache_data(show_spinner=False)
def get_side_effects(data_dir: str, as_of, actions_key, rules_json, shock):
    data = get_data(data_dir)
    actions = [{"kind": k, "employee_ids": list(ids), "date": d, "months": m} for k, ids, d, m in actions_key]
    return engine.side_effects(data, actions, json.loads(rules_json), as_of, shock)


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
ss.setdefault("rules", {})        # plan-rule overrides, see rules.py
ss.setdefault("payout", {})       # PSU / performance cash payout % by company (missing = 100)
ss.setdefault("rules_ver", 0)
ss.setdefault("payout_ver", 0)
SCOPE_ALL = "All companies (defaults)"
# Starting values are set here, not with widget defaults, so they survive the profile round trip (see below).
for _k, _v in {"mode": MODE_CUR, "ev_layout": "Cards", "r_view": "Learn", "o_horizon": "24 months",
               "o_split": "None (total)", "o_measure": "Estimated value (USD)", "o_cumul": False,
               "g_topic": "Award types", "g_award": "RSU", "g_event": "resign", "r_scope": SCOPE_ALL,
               "r_event": "resign", "data_dir": DEFAULT_DIR}.items():
    ss.setdefault(_k, _v)
data_dir = ss.get("data_dir", DEFAULT_DIR)
try:
    data = get_data(data_dir)
except Exception as exc:  # missing folder / file
    st.error(f"Could not load data from '{data_dir}': {exc}")
    st.text_input("Data folder", key="data_dir")
    st.stop()
market = data["market"]
emp_lookup = data["employees"].set_index("employee_id")


def open_emp(emp):
    ss["emp_view"] = emp


def close_emp():
    ss["emp_view"] = None


# Widgets that are not drawn on a given run lose their saved value. These live on screens that are hidden while
# an employee profile is open, so re-save them to keep the user's choices when they come back.
for _k in ("o_horizon", "o_split", "o_measure", "o_cumul", "ev_layout", "data_dir", "r_view", "r_scope", "r_event",
           "g_topic", "g_award", "g_event"):
    if _k in ss:
        ss[_k] = ss[_k]


def cards_with_open(df: pd.DataFrame, prefix: str, share_decimals: int = 0):
    """Cards in two columns (one on a phone), each with a button that opens that person's profile."""
    rows = list(df.itertuples())
    for i in range(0, len(rows), 2):
        for col, r in zip(st.columns(2), rows[i:i + 2]):
            with col:
                st.markdown(cards_html(df.loc[[r.Index]], share_decimals, single=True), unsafe_allow_html=True)
                st.button(f"Open {r.full_name}", key=f"{prefix}_{r.tranche_id}", on_click=open_emp,
                          kwargs={"emp": r.employee_id}, use_container_width=True)


def clear_filters():
    ss["f_company"], ss["f_country"], ss["f_dept"], ss["f_search"], ss["f_award"] = [], [], [], "", []


def reset_whatif():
    ss["w_scenario"], ss["w_shock"], ss["w_attr"], ss["w_own"] = "Flat", 0, 0.0, True
    ss["w_growth"], ss["w_vol"], ss["actions"] = 8.0, 35.0, []
    ss["payout"], ss["w_pay_all"] = {}, 100
    ss["payout_ver"] += 1


def preset(shock=None, attr=None, pay=None):
    reset_whatif()
    if shock is not None:
        ss["w_shock"] = shock
    if attr is not None:
        ss["w_attr"] = attr
    if pay is not None:
        ss["payout"] = {c: float(pay) for c in data["companies"]["company_name"]}
        ss["w_pay_all"] = pay


# ------------------------------------------------------------------ header + controls
st.markdown('<div class="hdr"><span class="hdr-t">Equity Vesting Tracker</span>'
            '<span class="badge">Synthetic data</span></div>', unsafe_allow_html=True)

c_mode, c_asof, c_win, c_filt = st.columns([2.2, 1, 1, 1])
with c_mode:
    if hasattr(st, "segmented_control"):
        mode = st.segmented_control("View", [MODE_CUR, MODE_WI], key="mode") or MODE_CUR
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
        awards = st.multiselect("Award type", R.AWARD_TYPES, key="f_award")
        search = st.text_input("Employee name or ID contains", key="f_search")
        st.button("Clear filters", on_click=clear_filters, use_container_width=True)

filter_parts = []
if companies:
    filter_parts.append("Company: " + ", ".join(companies))
if countries:
    filter_parts.append("Country: " + ", ".join(countries))
if departments:
    filter_parts.append("Department: " + ", ".join(departments))
if awards:
    filter_parts.append("Award: " + ", ".join(awards))
if search.strip():
    filter_parts.append(f"Employee contains '{search.strip()}'")
filters_text = "; ".join(filter_parts) or "None"
if not ss.get("emp_view"):
    st.markdown(chips_html(filter_parts), unsafe_allow_html=True)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if companies:
        df = df[df["company"].isin(companies)]
    if countries:
        df = df[df["country"].isin(countries)]
    if departments:
        df = df[df["department"].isin(departments)]
    if awards:
        df = df[df["award_type"].isin(awards)]
    if search.strip():
        q = search.strip().lower()
        df = df[df["full_name"].str.lower().str.contains(q, regex=False)
                | df["employee_id"].str.lower().str.contains(q, regex=False)]
    return df


as_of_ts = pd.Timestamp(as_of)
cur_all = get_current_events(data_dir, as_of_ts)

# ------------------------------------------------------------------ what-if builder
def explain_box(html_text: str):
    st.markdown(f'<div class="explain">{html_text}</div>', unsafe_allow_html=True)


def set_all_payout(pct):
    ss["payout"] = {c: float(pct) for c in data["companies"]["company_name"]} if pct != 100 else {}
    ss["payout_ver"] += 1


scenario, g_arg, v_arg, shock, attr = "Flat", None, None, 0.0, 0.0
if is_whatif:
    with (st.expander("What-if settings", expanded=False) if ss.get("emp_view") else st.container(border=True)):
        st.markdown("**Build your what-if**  \nAsk \"what happens to the lapse if...?\" Nothing is saved, and every "
                    "change is compared with the current schedule.")
        st.markdown('<div class="steps"><span><b>1</b> Start with a quick scenario</span>'
                    '<span><b>2</b> Fine-tune it below</span>'
                    '<span><b>3</b> Read the impact on the <b>Lapse day</b> tab</span></div>',
                    unsafe_allow_html=True)
        st.caption("Quick scenarios")
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
            p4.button("PSUs pay 50%", on_click=preset, kwargs={"pay": 50}, use_container_width=True)
            p5, p6 = st.columns(2)
            p5.button("PSUs pay 150%", on_click=preset, kwargs={"pay": 150}, use_container_width=True)
            p6.button("Reset", on_click=reset_whatif, use_container_width=True)

        st.caption("Fine-tune: each tab changes one kind of input.")
        t_price, t_pay, t_people = st.tabs(["Share price", "Performance payout", "People and events"])
        with t_price:
            explain_box("<b>Share price.</b> Changes the dollar value of every vest, not who vests or when. "
                        "Every value is shares &times; a projected share price. "
                        "<b>Flat</b> holds today's price. <b>Growth</b> compounds it each year. <b>Range</b> adds a "
                        "bear and a bull case from each company's volatility. The slider below first moves "
                        "today's price up or down.")
            scenario = st.selectbox("Price path", engine.SCENARIOS, key="w_scenario")
            shock = st.slider("Change today's share prices by (%)", -50, 50, 0, 1, key="w_shock") / 100
            if scenario != "Flat":
                own = st.checkbox("Use each company's own growth and volatility", value=True, key="w_own")
                gcol, vcol = st.columns(2)
                growth = gcol.slider("Annual growth (%)", -20.0, 40.0, 8.0, 0.5, key="w_growth", disabled=own) / 100
                vol = vcol.slider("Annual volatility (%)", 5.0, 80.0, 35.0, 1.0, key="w_vol",
                                  disabled=own or not scenario.startswith("Range")) / 100
                g_arg, v_arg = (None, None) if own else (growth, vol)

        with t_pay:
            explain_box("<b>Performance payout.</b> Changes how much performance awards pay on the lapse day. PSUs and performance cash pay a percentage of their target, "
                        "decided by results. 100% means target. Set it per company: for example a company that "
                        "is missing its goals might pay 50%, one that beats them 150%. Each grant also has its own "
                        "maximum, so entries above it are capped. Other award types are not affected.")
            pa, pb = st.columns([3, 1])
            all_pct = pa.slider("Set every company to (%)", 0, 200, 100, 5, key="w_pay_all")
            pb.markdown('<div style="height:1.7rem"></div>', unsafe_allow_html=True)
            pb.button("Apply", key="pay_apply", on_click=set_all_payout, kwargs={"pct": all_pct},
                      use_container_width=True)
            pay_df = pd.DataFrame({"Company": sorted(data["companies"]["company_name"])})
            pay_df["Payout % of target"] = [float(ss["payout"].get(c, 100.0)) for c in pay_df["Company"]]
            edited = st.data_editor(
                pay_df, hide_index=True, disabled=["Company"], use_container_width=True,
                key=f"payout_ed_{ss['payout_ver']}",
                column_config={"Payout % of target": st.column_config.NumberColumn(
                    min_value=0, max_value=200, step=5, format="%d%%",
                    help="Percent of target paid out. 100 = target.")})
            ss["payout"] = {r["Company"]: float(r["Payout % of target"]) for _, r in edited.iterrows()
                            if abs(float(r["Payout % of target"]) - 100.0) > 1e-9}
            n_perf = int(cur_all[cur_all["award_type"].isin(R.PERF_TYPES)].shape[0])
            st.caption(f"{n_perf:,} PSU and performance cash payouts are scheduled in the next four years across all "
                       "companies. Pro-rata or accelerated payouts after a people event follow the rules instead.")

        with t_people:
            explain_box("<b>People and events.</b> Changes who vests and when: leavers forfeit, leave pauses, "
                        "and so on. <b>Attrition</b> assumes a share of staff leave each year and "
                        "forfeit what is unvested. <b>Events</b> are specific things that happen to specific people. "
                        "What each event does to each award type comes from the plan rules, which you can view and "
                        "change per company on the <i>Rules and guide</i> tab.")
            attr = st.slider("Assumed annual attrition (%)", 0.0, 30.0, 0.0, 0.5, key="w_attr") / 100
            st.caption("Attrition scales unvested units by the chance each person is still employed at the vest "
                       "date. It is an expected value, so units can be fractional.")
            st.markdown("**Add an event for specific people**")
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
            kind = e1.selectbox("What happens", list(R.EVENTS), format_func=R.EVENTS.get, key="w_kind")
            ev_date = e2.date_input("From", value=(as_of_ts + pd.Timedelta(days=30)).date(), key="w_date")
            months = e3.number_input("Pause (months)", 1, 24, 3, key="w_months", disabled=(kind != "leave"))
            st.caption("The event takes effect on the 'From' date. Vests on or before that date still happen; "
                       "later ones follow the plan rules (for example, unvested awards are forfeited on a resignation).")
            info = learn.EVENTS[kind]
            explain_box(f"<b>{hx(R.EVENTS[kind])}.</b> {hx(info['what'])}<br><b>Typically:</b> {hx(info['typical'])}"
                        f"<br><b>Why it matters:</b> {hx(info['matters'])}")
            who_cos = [c for c in pd.Series([emp_lookup.loc[i, 'company_id'] for i in ids]).map(
                data["companies"].set_index("company_id")["company_name"]).value_counts().index] if ids else []
            with st.expander("What happens to each award type under the current rules?"):
                shown_co = who_cos[0] if who_cos else None
                rr = R.resolve_rules(ss["rules"], shown_co)[kind]
                st.dataframe(pd.DataFrame({"Award type": R.AWARD_TYPES,
                                           "What happens": [rr["treatments"][a] for a in R.AWARD_TYPES]}),
                             hide_index=True, use_container_width=True)
                if len(who_cos) > 1:
                    st.caption(f"These people work at {len(who_cos)} companies and rules can differ by company. "
                               f"Showing {shown_co}.")
                elif shown_co:
                    st.caption(f"Rules for {shown_co}.")
                else:
                    st.caption("Pick people to see the rules for their company. Showing the defaults.")
                if kind != "leave":
                    st.caption(f"Vested options and SARs stay exercisable for {rr['window_days']} days. "
                               + (f"Anything delivered in the last {rr['clawback_months']} months counts as clawback exposure."
                                  if rr["clawback_months"] else "No clawback applies."))
                st.caption("Change these on the Rules and guide tab.")
            if st.button("Add event"):
                if not ids:
                    st.warning("Pick at least one employee, or loosen the filters.")
                else:
                    label = (f"{len(ids)} people" if len(ids) > 1
                             else f"{ids[0]} ({emp_lookup.loc[ids[0], 'full_name']})")
                    ss["actions"].append({"kind": kind, "employee_ids": tuple(ids), "date": str(ev_date),
                                          "months": int(months) if kind == "leave" else 0, "label": label})
            if ss["actions"]:
                st.dataframe(pd.DataFrame([{"Event": R.EVENTS[a["kind"]], "People": a["label"],
                                            "From": a["date"], "Pause (months)": a["months"] or None}
                                           for a in ss["actions"]]), hide_index=True)
                r1, r2, _ = st.columns([1, 1, 3])
                if r1.button("Remove last"):
                    ss["actions"].pop()
                    st.rerun()
                if r2.button("Clear events"):
                    ss["actions"] = []
                    st.rerun()

        n_active = (scenario != "Flat") + bool(shock) + bool(attr) + bool(ss["payout"]) + len(ss["actions"])
        st.caption(f"{n_active} change{'s' if n_active != 1 else ''} active. Results update as you go; "
                   "see the summary below the settings." if n_active else
                   "No changes yet. Pick a quick scenario or move a setting.")

actions_key = tuple((a["kind"], tuple(a["employee_ids"]), a["date"], a["months"]) for a in ss["actions"])
rules_json = json.dumps(ss["rules"], sort_keys=True)
payout_json = json.dumps({k: v for k, v in ss["payout"].items() if v != 100}, sort_keys=True)
neutral = scenario == "Flat" and not shock and not attr and not ss["actions"] and payout_json == "{}"


def describe_levers() -> str:
    parts = []
    if scenario != "Flat":
        parts.append(f"{scenario.split(' (')[0].lower()} price path "
                     f"({'company assumptions' if g_arg is None else f'{g_arg:.1%} growth'})")
    if shock:
        parts.append(f"share prices {shock:+.0%} today")
    if attr:
        parts.append(f"{attr:.1%} annual attrition")
    if payout_json != "{}":
        pay = ss["payout"]
        items = [f"{c} {v:.0f}%" for c, v in list(pay.items())[:3]]
        parts.append("PSU / performance cash payout at " + ", ".join(items)
                     + (f" and {len(pay) - 3} more" if len(pay) > 3 else "") + " of target")
    for a in ss["actions"]:
        txt = f"{R.EVENT_SHORT[a['kind']]} for {a['label']} from {a['date']}"
        parts.append(txt + (f", vesting paused {a['months']} months" if a["kind"] == "leave" else ""))
    custom = sum(R.count_overrides(ss["rules"], sc) for sc in ss["rules"])
    if custom and ss["actions"]:
        parts.append(f"{custom} customized plan rule(s) in effect")
    return "; ".join(parts) or "no changes yet"


wi_all = (get_whatif_events(data_dir, as_of_ts, scenario, g_arg, v_arg, shock, attr, actions_key, rules_json,
                            payout_json) if is_whatif else None)


def prep(df: pd.DataFrame) -> pd.DataFrame:
    return apply_filters(df[df["days_until"] <= window_days])


cur_ev = prep(cur_all)
wi_ev = prep(wi_all) if is_whatif else None
ev = wi_ev if is_whatif else cur_ev
levers = describe_levers() if is_whatif else ""
summ = engine.summarize(ev)
is_range = scenario.startswith("Range") and is_whatif

def example_text(r) -> str:
    """The arithmetic behind one vesting event, with the real numbers filled in (r is an events row)."""
    aw, u, p, val = r["award_type"], r["shares_vesting"], r["est_price_usd"], r["est_value_usd"]
    k = r["strike_price"]
    if aw in R.OPTION_LIKE:
        if p > k:
            return f"{u:,.0f} units \u00d7 (price {price(p)} \u2212 strike {price(k)}) = {money(val)}"
        return f"Price {price(p)} is at or below the strike {price(k)}, so the gain is $0 (underwater)."
    if aw == "PSU":
        return f"{r['target_units']:,.0f} target units \u00d7 {r['payout_pct']:.0f}% payout \u00d7 price {price(p)} = {money(val)}"
    if aw == "Performance Cash":
        return f"{money(r['target_units'])} target \u00d7 {r['payout_pct']:.0f}% payout = {money(val)}"
    if aw == "ESPP":
        return (f"Savings buy {u:,.1f} shares at a discount \u00d7 price {price(p)} = {money(val)} "
                "(the number of shares depends on the price)")
    return f"{u:,.0f} units \u00d7 price {price(p)} = {money(val)}"


# ------------------------------------------------------------------ employee profile
def render_profile(emp_id: str):
    """Everything about one person: header, key numbers, per-grant charts, grant table, events and raw fields."""
    e = emp_lookup.loc[emp_id]
    company_name = data["companies"].set_index("company_id")["company_name"].get(e["company_id"], e["company_id"])
    base_ev = wi_all if is_whatif else cur_all
    pe = base_ev[base_ev["employee_id"] == emp_id]
    ce = cur_all[cur_all["employee_id"] == emp_id]
    changed = is_whatif and not neutral
    tr_w = get_whatif_tranches(data_dir, actions_key, rules_json, emp_id) if (is_whatif and ss["actions"]) else None
    gs = engine.grant_summary(data, emp_id, base_ev, tr_w)
    sched = engine.employee_schedule(data, emp_id, base_ev, tr_w)

    st.button("← Back to overview", key="back_top", on_click=close_emp)
    st.markdown(f'<div class="hdr"><span class="hdr-t">{hx(e["full_name"])}</span>'
                f'<span class="badge">{hx(e["employment_status"])}</span>'
                + ('<span class="badge">What-if view</span>' if is_whatif else "") + "</div>", unsafe_allow_html=True)
    st.markdown(chips_html([emp_id, company_name, str(e["department"]), str(e["country"]),
                            f"Hired {pd.Timestamp(e['hire_date']):%b %Y}"]), unsafe_allow_html=True)

    if e["employment_status"] == "Terminated":
        td = e["termination_date"]
        st.warning(f"Terminated{'' if pd.isna(td) else f' on {pd.Timestamp(td):%b %d, %Y}'}. "
                   "Unvested shares normally forfeit; check how this person's plan treats them.")
    if e["tax_residency_country"] != e["country"]:
        st.warning(f"Tax residency ({e['tax_residency_country']}) differs from work country ({e['country']}). "
                   "Review withholding before the next vest.")

    # key numbers
    up_sh, up_val = pe["share_units"].sum(), pe["est_value_usd"].sum()
    nxt = pe.sort_values("vest_date").head(1)
    nxt_txt = "None scheduled" if nxt.empty else f"{nxt['vest_date'].iloc[0]:%b %d, %Y}"
    nxt_sub = "" if nxt.empty else (f"{nxt['award_type'].iloc[0]}, "
                                    f"{charts.short_money(nxt['est_value_usd'].iloc[0])}")
    st.markdown(kpi_html([
        ("Upcoming units", charts.short_num(up_sh),
         delta_text(up_sh, ce["share_units"].sum()) if changed else None, "excludes performance cash"),
        ("Est. value of upcoming", charts.short_money(up_val),
         delta_text(up_val, ce["est_value_usd"].sum(), True) if changed else None, None),
        ("Next vest", nxt_txt, None, nxt_sub),
        ("Already vested", charts.short_num(gs["vested_shares"].sum()), None, None),
        ("Forfeited", charts.short_num(gs["forfeited_shares"].sum()), None, None),
        ("Grants", f"{len(gs)}", None, None),
    ]), unsafe_allow_html=True)
    if changed:
        st.caption(md(f"Showing this person under your what-if: {levers}."))
        mine = [x for x in ss["actions"] if emp_id in x["employee_ids"]]
        if mine:
            gone = ce[~ce["tranche_id"].isin(pe["tranche_id"])]
            moved = engine.diff_events(ce, pe)
            lines = ", ".join(f"{R.EVENT_SHORT[x['kind']]} from {x['date']}" for x in mine)
            st.markdown(
                f'<div class="scen"><span class="sk">Event applied to this person</span><br>{hx(lines)}.<br>'
                f'{len(gone):,} upcoming vest{"s" if len(gone) != 1 else ""} no longer pay out '
                f'({hx(money(gone["est_value_usd"].sum()))} in the current schedule). '
                f'{len(pe):,} remain, worth {hx(money(pe["est_value_usd"].sum()))}.</div>'.replace("$", "&#36;"),
                unsafe_allow_html=True)

    # dive-in tools
    all_grants = list(gs["grant_id"])
    f1, f2, f3 = st.columns([2, 1.3, 1.3])
    sel = f1.multiselect("Grants", all_grants, default=all_grants, key=f"p_grants_{emp_id}")
    status_pick = f2.selectbox("Show", ["All", "Upcoming", "Vested", "Forfeited"], key="p_status")
    measure = f3.radio("Measure", ["Units", "Est. value"], horizontal=True, key="p_measure")
    sd = sched[sched["grant_id"].isin(sel)]
    if status_pick != "All":
        sd = sd[sd["status"] == status_pick]
    gs_sel = gs[gs["grant_id"].isin(sel)]

    t_sched, t_grants, t_events, t_details = st.tabs(["Schedule", "Grants", "Events", "Details"])

    with t_sched:
        if sd.empty:
            st.info("Nothing to show for these choices. Try another grant or status.")
        else:
            st.markdown("**Each grant on a timeline**")
            tdf, tspec = charts.grant_timeline(sd, as_of_ts)
            st.vega_lite_chart(tdf, tspec, use_container_width=True)
            st.caption("Grey dots have vested, blue dots are upcoming, orange dots were forfeited. "
                       "Bigger dots are bigger vests. The dashed line is the as-of date.")
        up_sd = sd[sd["status"] == "Upcoming"]
        if not up_sd.empty:
            is_val = measure.startswith("Est")
            st.markdown("**Upcoming vests by month**")
            vdf, vspec = charts.vest_stack(
                up_sd.assign(value=up_sd["est_value_usd"] if is_val else
                             up_sd["shares_vesting"].where(up_sd["award_type"] != "Performance Cash", 0.0)), is_val)
            st.vega_lite_chart(vdf, vspec, use_container_width=True)
        if not gs_sel.empty:
            st.markdown("**How far along each grant is**")
            pdf, pspec = charts.grant_progress(gs_sel)
            st.vega_lite_chart(pdf, pspec, use_container_width=True)

    with t_grants:
        if gs_sel.empty:
            st.info("No grants selected.")
        else:
            show = gs_sel.rename(columns={
                "grant_id": "Grant", "award_type": "Type", "settlement": "Paid in", "ticker": "Ticker",
                "grant_date": "Granted", "strike_price": "Strike", "expiry_date": "Expires",
                "vesting_schedule_id": "Schedule", "total_shares": "Total units", "vested_shares": "Vested",
                "forfeited_shares": "Forfeited", "upcoming_shares": "Upcoming", "upcoming_value_usd": "Upcoming value",
                "upcoming_events": "Events left", "next_vest_date": "Next vest", "next_vest_shares": "Next shares",
                "pct_vested": "% vested"})
            show["% vested"] = show["% vested"] * 100
            st.dataframe(show, hide_index=True, column_config={
                "Granted": st.column_config.DateColumn(format="YYYY-MM-DD"),
                "Next vest": st.column_config.DateColumn(format="YYYY-MM-DD"),
                "Expires": st.column_config.DateColumn(format="YYYY-MM-DD"),
                "Strike": st.column_config.NumberColumn(format="$%.2f"),
                "Total units": st.column_config.NumberColumn(format="%.0f"),
                "Vested": st.column_config.NumberColumn(format="%.0f"),
                "Forfeited": st.column_config.NumberColumn(format="%.0f"),
                "Upcoming": st.column_config.NumberColumn(format="%.0f"),
                "Upcoming value": st.column_config.NumberColumn(format="$%.0f"),
                "Next shares": st.column_config.NumberColumn("Next units", format="%.0f"),
                "% vested": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100)
                if hasattr(st.column_config, "ProgressColumn") else st.column_config.NumberColumn(format="%.0f"),
            })
            pick_g = st.selectbox("Open one grant", all_grants, key=f"p_grant_{emp_id}")
            g = data["grants"].set_index("grant_id").loc[pick_g]
            info = learn.AWARDS.get(g["award_type"], UNKNOWN_AWARD)
            pairs = [("Grant", pick_g), ("Type", info["name"]), ("Paid in", g["settlement"]), ("Ticker", g["ticker"]),
                     ("Granted", f"{pd.Timestamp(g['grant_date']):%b %d, %Y}"),
                     ("Vesting starts", f"{pd.Timestamp(g['vesting_start_date']):%b %d, %Y}"),
                     ("Schedule", g["vesting_schedule_id"]),
                     ("Total units" + (" (USD)" if g["award_type"] == "Performance Cash" else ""),
                      f"{g['total_shares']:,.0f}"),
                     ("Status", g["grant_status"])]
            if g["award_type"] in R.OPTION_LIKE:
                pairs += [("Strike price", money(g["strike_price"])), ("Expires", f"{pd.Timestamp(g['expiry_date']):%b %d, %Y}")]
            if g["award_type"] in R.PERF_TYPES:
                pairs += [("Performance metric", g["perf_metric"]), ("Maximum payout", f"{g['perf_max_pct']:.0f}% of target")]
            if g["award_type"] == "Restricted Stock":
                pairs.append(("83(b) election", "Yes" if g["election_83b"] else "No"))
            if g["award_type"] == "ESPP":
                pairs += [("Discount", f"{g['purchase_discount']:.0%}"), ("Lookback", "Yes" if g["lookback"] else "No")]
            st.markdown(kv_html(pairs), unsafe_allow_html=True)
            nxt_g = pe[pe["grant_id"] == pick_g].sort_values("vest_date").head(1)
            ex = f"<br><b>Next vest, worked out:</b> {hx(example_text(nxt_g.iloc[0]))}" if not nxt_g.empty else ""
            explain_box(f"<b>{hx(info['tagline'])}</b> {hx(info['what'])}<br><b>Value:</b> {hx(info['value'])}{ex}")
            gd = sched[sched["grant_id"] == pick_g].rename(columns={
                "vest_date": "Vest date", "shares_vesting": "Shares", "status": "Status", "est_price_usd": "Est. price",
                "est_value_usd": "Est. value", "flags": "Notes", "tranche_id": "Tranche"}).drop(columns="grant_id")
            st.dataframe(gd, hide_index=True, column_config={
                "Vest date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                "Shares": st.column_config.NumberColumn("Units", format="%.1f" if attr else "%.0f"),
                "Est. price": st.column_config.NumberColumn(format="$%.2f"),
                "Est. value": st.column_config.NumberColumn(format="$%.0f")})
            st.caption("Past vests show units only. Prices and values are estimates for upcoming vests.")

    with t_events:
        if pe.empty:
            st.info("This person has no upcoming vesting events.")
        else:
            st.write(f"**{len(pe):,}** upcoming events, soonest first.")
            st.download_button("Export this person's events (CSV)", pe.to_csv(index=False).encode("utf-8"),
                               file_name=f"{emp_id}_upcoming_events.csv", mime="text/csv", use_container_width=True)
            st.dataframe(pe[["vest_date", "days_until", "grant_id", "award_type", "settlement", "shares_vesting",
                             "est_price_usd", "est_value_usd", "est_value_local", "local_currency", "flags"]],
                         hide_index=True, column_config={
                "vest_date": st.column_config.DateColumn("Vest date", format="YYYY-MM-DD"),
                "days_until": st.column_config.NumberColumn("Days", format="%d"),
                "award_type": "Type", "settlement": "Paid in",
                "shares_vesting": st.column_config.NumberColumn("Units", format="%.1f" if attr else "%.0f"),
                "est_price_usd": st.column_config.NumberColumn("Share price", format="$%.2f"),
                "est_value_usd": st.column_config.NumberColumn("Est. value (USD)", format="$%.0f"),
                "est_value_local": st.column_config.NumberColumn("Est. value (local)", format="%.0f")})
            st.caption("Units are gross, before tax withholding. Performance cash units are US dollars.")
        if changed:
            diff = engine.diff_events(ce, pe)
            st.markdown("**Timing changes caused by your what-if**")
            if diff.empty:
                st.caption("No timing changes for this person. Price and attrition assumptions are not listed here.")
            else:
                st.dataframe(diff, hide_index=True)

    with t_details:
        tenure = (as_of_ts - pd.Timestamp(e["hire_date"])).days / 365.25
        st.markdown(kv_html([
            ("Employee ID", emp_id), ("Email", e["email"]), ("Company", company_name),
            ("Department", e["department"]), ("Work country", f"{e['country']} ({e['country_code']})"),
            ("Tax residency", e["tax_residency_country"]), ("Local currency", e["local_currency"]),
            ("Hire date", f"{pd.Timestamp(e['hire_date']):%b %d, %Y}"), ("Tenure", f"{tenure:.1f} years"),
            ("Employment status", e["employment_status"]),
            ("Termination date", "" if pd.isna(e["termination_date"]) else f"{pd.Timestamp(e['termination_date']):%b %d, %Y}")
        ]), unsafe_allow_html=True)
        tick = data["grants"].loc[data["grants"]["employee_id"] == emp_id, "ticker"].unique()
        mk = market[market["ticker"].isin(tick)].copy()
        fx = data["fx"][data["fx"]["currency"] == e["local_currency"]]
        st.markdown("**Prices used**")
        st.dataframe(mk.rename(columns={"ticker": "Ticker", "price_usd": "Price (USD)", "price_date": "As of",
                                        "annual_volatility": "Volatility", "assumed_annual_growth": "Assumed growth"})
                     .drop(columns="company"), hide_index=True)
        if not fx.empty:
            st.caption(f"FX: 1 USD = {fx['units_per_usd'].iloc[0]:,.4f} {e['local_currency']} (illustrative).")
        st.download_button("Export full schedule (CSV)", sched.to_csv(index=False).encode("utf-8"),
                           file_name=f"{emp_id}_full_schedule.csv", mime="text/csv", use_container_width=True)


if ss.get("emp_view"):
    if ss["emp_view"] in emp_lookup.index:
        render_profile(ss["emp_view"])
        st.stop()
    ss["emp_view"] = None

# ------------------------------------------------------------------ headline + summary cards
if is_whatif:
    if neutral:
        st.info("No changes yet. Pick a preset above, move a slider, or add a people event to see the impact.")
    else:
        _nx = wi_ev["vest_date"].min() if not wi_ev.empty else None
        _nx_txt = ""
        if _nx is not None:
            _c = cur_ev[cur_ev["vest_date"] == _nx]["est_value_usd"].sum()
            _w = wi_ev[wi_ev["vest_date"] == _nx]["est_value_usd"].sum()
            _nx_txt = (f"<br><span class='sk'>Next lapse day</span> {_nx:%b %d} "
                       f"(L-{max((_nx - as_of_ts).days, 0)}): {charts.short_money(_c)} now, "
                       f"{charts.short_money(_w)} in your what-if ({delta_text(_w, _c, True)})")
        st.markdown(f'<div class="scen"><span class="sk">Your what-if</span><br>{hx(levers)}.{_nx_txt}</div>'
                    .replace("$", "&#36;"), unsafe_allow_html=True)

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

def settle_value(df: pd.DataFrame, how: str) -> float:
    return float(df.loc[df["settlement"] == how, "est_value_usd"].sum())


cmp_on = is_whatif and not neutral
st.markdown(kpi_html([
    ("Units vesting", charts.short_num(ev["share_units"].sum()),
     delta_text(ev["share_units"].sum(), cur_ev["share_units"].sum()) if cmp_on else None,
     "shares, options, SARs, phantom units"),
    ("Paid in shares", charts.short_money(settle_value(ev, "Shares")),
     delta_text(settle_value(ev, "Shares"), settle_value(cur_ev, "Shares"), True) if cmp_on else None, "value delivered as stock"),
    ("Paid in cash", charts.short_money(settle_value(ev, "Cash")),
     delta_text(settle_value(ev, "Cash"), settle_value(cur_ev, "Cash"), True) if cmp_on else None, "payroll must fund this"),
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
    "payout_text": ("100% of target for every company" if payout_json == "{}" or not is_whatif else
                    ", ".join(f"{c} {v:.0f}%" for c, v in ss["payout"].items()) + " of target; others 100%"),
    "rules_text": ("Typical defaults" if not any(R.count_overrides(ss["rules"], sc) for sc in ss["rules"]) else
                   "Customized: " + ", ".join(f"{('all companies' if sc == R.DEFAULT_SCOPE else sc)} "
                                              f"({R.count_overrides(ss['rules'], sc)} changes)" for sc in ss["rules"]
                                              if R.count_overrides(ss["rules"], sc))),
    "award_note": "Value depends on award type: shares x price; options and SARs the gain over the strike; "
                  "performance cash dollars x payout %. Units for performance cash are US dollars.",
}

tab_lapse, tab_over, tab_events, tab_people, tab_rules, tab_report = st.tabs(
    ["Lapse day", "Overview", "Events", "People", "Rules and guide", "Reports and data"])


def tab_note(text: str):
    st.markdown(f'<div class="tabnote">{text}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ lapse day
with tab_lapse:
    tab_note("<b>One lapse day at a time.</b> Pick a vest date to see who vests, how much, how it is paid, and what "
             "has to be ready by <b>L-4</b>. "
             + ("With a what-if on, every number shows the current schedule next to your scenario." if is_whatif
                else "Switch to What-if at the top to see how a scenario changes the day."))
    d_cur = cur_ev["vest_date"].dt.normalize()
    d_wi = wi_ev["vest_date"].dt.normalize() if is_whatif else d_cur.iloc[0:0]
    all_days = sorted(set(d_cur.unique()) | set(d_wi.unique()))
    if not all_days:
        st.info("No lapse days in this window with these filters. Try a longer window or clear the filters.")
    else:
        day_n = pd.concat([d_cur, d_wi]).value_counts() if is_whatif else d_cur.value_counts()

        def _day_label(d):
            d = pd.Timestamp(d)
            return f"{d:%a %b %d, %Y}  -  L-{max((d - as_of_ts).days, 0)}  -  {int(day_n.get(d, 0))} events"

        pick_day = pd.Timestamp(st.selectbox("Lapse date", all_days, format_func=_day_label, key="l_date"))
        cur_d = cur_ev[d_cur == pick_day]
        wi_d = wi_ev[d_wi == pick_day] if is_whatif else None
        shown = wi_d if is_whatif else cur_d
        cmp_d = is_whatif and not neutral
        days_to = max((pick_day - as_of_ts).days, 0)
        pre = pick_day - pd.Timedelta(days=4)
        pre_txt = ("L-4 was " if pre < as_of_ts else "L-4 is ") + f"{pre:%b %d}"
        st.markdown(f"### {pick_day:%A, %B %d, %Y}")
        st.caption(f"L-{days_to} (lapse day). Pre-lapse checks: {pre_txt}.")

        def _sv(df, how):
            return float(df.loc[df["settlement"] == how, "est_value_usd"].sum())

        st.markdown(kpi_html([
            ("Value vesting", charts.short_money(shown["est_value_usd"].sum()),
             delta_text(shown["est_value_usd"].sum(), cur_d["est_value_usd"].sum(), True) if cmp_d else None,
             "gross, before tax"),
            ("People", f"{shown['employee_id'].nunique():,}",
             delta_text(shown["employee_id"].nunique(), cur_d["employee_id"].nunique()) if cmp_d else None, None),
            ("Events", f"{len(shown):,}", delta_text(len(shown), len(cur_d)) if cmp_d else None, None),
            ("Paid in shares", charts.short_money(_sv(shown, "Shares")),
             delta_text(_sv(shown, "Shares"), _sv(cur_d, "Shares"), True) if cmp_d else None, "delivered to brokerage"),
            ("Paid in cash", charts.short_money(_sv(shown, "Cash")),
             delta_text(_sv(shown, "Cash"), _sv(cur_d, "Cash"), True) if cmp_d else None, "payroll funds this"),
        ]), unsafe_allow_html=True)

        st.markdown("**Ready by L-4**")
        tab_note("What the team confirms before the lapse. Counts come from this day's events. The details that are "
                 "not in a regular feed (see <i>Rules and guide &rarr; The lapse process</i>) are listed so you know "
                 "what to chase.")
        n_cty = shown["country"].nunique()
        n_flag = int((shown["flags"].astype(str).str.len() > 0).sum())
        n_opt = int(shown["award_type"].isin(R.OPTION_LIKE).sum())
        n_perf = int(shown["award_type"].isin(R.PERF_TYPES).sum())
        cash_ppl = shown.loc[shown["settlement"] == "Cash", "employee_id"].nunique()
        st.markdown(
            '<div class="ck">'
            f'<div><b>{shown["employee_id"].nunique():,} people</b>Brokerage account open and unrestricted '
            '(needed to receive shares or proceeds)</div>'
            f'<div><b>{n_cty} tax jurisdiction{"s" if n_cty != 1 else ""}</b>Where each person lives and works; '
            'check for moves (mobility)</div>'
            f'<div><b>{n_flag:,} flagged event{"s" if n_flag != 1 else ""}</b>Items marked for review, such as leave '
            'of absence or missing data</div>'
            f'<div><b>{cash_ppl:,} paid in cash</b>Payroll provider funds and holds year-to-date earnings for '
            'tax caps</div>'
            f'<div><b>{n_perf:,} performance payout{"s" if n_perf != 1 else ""}</b>Results must be approved before '
            'the amount is known</div>'
            f'<div><b>{n_opt:,} option / SAR event{"s" if n_opt != 1 else ""}</b>Value depends on the share price '
            'against the strike</div>'
            '</div>', unsafe_allow_html=True)

        st.markdown("**Who and where**")
        for key, title in (("country", "By country"), ("company", "By company"), ("award_type", "By award type")):
            if is_whatif:
                t = compare_table(cur_d, wi_d, key, "est_value_usd").sort_values("What-if", ascending=False)
            else:
                t = cur_d.groupby(key)["est_value_usd"].sum().sort_values(ascending=False).to_frame("Current")
            with st.expander(title, expanded=(key == "country")):
                st.dataframe(t.round(0).reset_index(), hide_index=True, use_container_width=True,
                             column_config={c: st.column_config.NumberColumn(format="$%.0f") for c in t.columns})

        if cmp_d:
            diff_d = engine.diff_events(cur_d, wi_d)
            if not diff_d.empty:
                with st.expander(f"{len(diff_d):,} events moved, forfeited or accelerated on or from this day"):
                    st.dataframe(diff_d, hide_index=True)
        st.markdown("**Biggest events on this day**")
        if shown.empty:
            st.info("Nothing vests on this day in your what-if. It may have been moved or forfeited.")
        else:
            cards_with_open(shown.sort_values("est_value_usd", ascending=False).head(6), "ld", 1 if attr else 0)

# ------------------------------------------------------------------ overview
with tab_over:
    tab_note("<b>The big picture.</b> How much vests month by month, what changed in your what-if, and where it vests.")
    st.markdown("**Vesting by month**")
    with st.expander("Chart options"):
        b1, b2 = st.columns(2)
        horizon_label = b1.selectbox("Horizon", ["12 months", "24 months", "36 months", "48 months"],
                                     key="o_horizon")
        split_label = b2.selectbox("Split lines by", ["None (total)", "Company", "Country", "Department", "Award type"],
                                   key="o_split")
        b3, b4 = st.columns(2)
        metric_label = b3.radio("Measure", ["Estimated value (USD)", "Units vesting"], key="o_measure")
        cumulative = b4.checkbox("Cumulative", key="o_cumul")
    bi_end = as_of_ts + pd.DateOffset(months=int(horizon_label.split()[0]))
    metric = "share_units" if metric_label.startswith("Units") else "est_value_usd"
    is_money = metric == "est_value_usd"
    by = {"None (total)": None, "Company": "company", "Country": "country", "Department": "department",
          "Award type": "award_type"}[split_label]
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
        total_txt = charts.short_money(shown_df[metric].sum()) if is_money else f"{shown_df[metric].sum():,.0f} units"
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
        bridge = get_bridge(data_dir, as_of_ts, scenario, g_arg, v_arg, shock, attr, actions_key, rules_json, payout_json)
        totals = [(label, apply_filters(e[e["days_until"] <= window_days])["est_value_usd"].sum())
                  for label, e in bridge]
        if len(totals) > 1 and any(t for _, t in totals):
            bdf, bspec = charts.bridge_chart(totals)
            st.vega_lite_chart(bdf, bspec, use_container_width=True)
            st.caption("Each bar applies one change on top of the one before it, in this order: people events, "
                       "attrition, performance payout, share price change, price path. A different order would "
                       "split the effect slightly differently, but the start and end always match the cards above.")
        with st.expander("Impact by award type"):
            t_aw = compare_table(cur_ev, wi_ev, "award_type", "est_value_usd").sort_values("What-if", ascending=False)
            st.dataframe(t_aw.round(0).reset_index().rename(columns={"award_type": "Award type"}), hide_index=True,
                         column_config={c: st.column_config.NumberColumn(format="$%.0f")
                                        for c in ("Current", "What-if", "Change")})
            st.caption("Estimated value in the window, before and after your what-if, for each kind of award.")

    # consequences of people events that are not upcoming vests
    if is_whatif and any(a["kind"] != "leave" for a in ss["actions"]):
        fx_ = get_side_effects(data_dir, as_of_ts, actions_key, rules_json, shock)
        claw, lapse = fx_["clawback"], fx_["lapse"]
        if not claw.empty or not lapse.empty:
            st.markdown("**Also at stake**")
            explain_box("These are consequences of your events that are <b>not</b> in the vesting totals above. "
                        "<b>Clawback exposure</b> is value already delivered inside the lookback window that the plan "
                        "could ask to take back. It is an amount at risk, not money recovered. "
                        "<b>Options that could lapse</b> are vested options and SARs that stay usable only for a limited "
                        "window after the event. The data has no exercise records, so this assumes none were exercised.")
            st.markdown(kpi_html([
                ("Clawback exposure", charts.short_money(claw["value_at_risk_usd"].sum()), None,
                 f"{len(claw):,} delivered vests in the lookback"),
                ("Options that could lapse", charts.short_money(lapse["gain_at_today_usd"].sum()), None,
                 f"{len(lapse):,} vested lots, gain at today's price")]), unsafe_allow_html=True)
            if not claw.empty:
                with st.expander("Clawback exposure detail"):
                    st.dataframe(claw, hide_index=True, column_config={
                        "vest_date": st.column_config.DateColumn("Vested", format="YYYY-MM-DD"),
                        "value_at_risk_usd": st.column_config.NumberColumn("At risk (USD)", format="$%.0f")})
            if not lapse.empty:
                with st.expander("Options that could lapse, detail"):
                    st.dataframe(lapse, hide_index=True, column_config={
                        "exercisable_until": st.column_config.DateColumn("Exercisable until", format="YYYY-MM-DD"),
                        "gain_at_today_usd": st.column_config.NumberColumn("Gain today (USD)", format="$%.0f")})

    # up next
    if not ev.empty:
        st.markdown("**Up next**")
        cards_with_open(ev.sort_values(["vest_date", "est_value_usd"], ascending=[True, False]).head(10),
                        "up", 1 if attr else 0)

        # where it vests
        dims = [("company", "By company"), ("country", "By country"), ("award_type", "By award type")]
        if n_cos == 1:
            dims = [("country", "By country"), ("department", "By department"), ("award_type", "By award type")]
        st.markdown("**Where it vests**")
        bm = "est_value_usd"
        cols = st.columns(3)
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
            m_label = st.radio("Measure ", ["Estimated value (USD)", "Units vesting"], horizontal=True)
            tm = "est_value_usd" if m_label.startswith("Estimated") else "share_units"
            for key, title in (("month", "By month"), ("company", "By company"), ("country", "By country"),
                               ("award_type", "By award type")):
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
    tab_note("<b>Every vesting event</b> (one tranche of one grant) in the window, soonest lapse first. Use it to "
             "export or check individual lines." + (" Choose 'Timing changes only' to see just what your what-if moved."
                                                    if is_whatif else ""))
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
            layout = (st.segmented_control("Layout", ["Cards", "Table"], key="ev_layout")
                      if hasattr(st, "segmented_control")
                      else st.radio("Layout", ["Cards", "Table"], horizontal=True, key="ev_layout")) or "Cards"
            if layout == "Cards":
                n = min(ss["card_n"], len(ev))
                cards_with_open(ev.head(n), "ev", 1 if attr else 0)
                if n < len(ev):
                    st.caption(f"Showing {n:,} of {len(ev):,}, soonest first.")
                    if st.button(f"Show {min(CARD_PAGE, len(ev) - n)} more", use_container_width=True):
                        ss["card_n"] = n + CARD_PAGE
                        st.rerun()
            else:
                all_cols = st.checkbox("Show all columns", value=False)
                compact = ["vest_date", "company", "full_name", "award_type", "settlement", "shares_vesting", "est_price_usd",
                           "est_value_usd", "flags"]
                share_fmt = "%.1f" if attr else "%.0f"
                st.dataframe(
                    ev, hide_index=True, column_order=None if all_cols else compact,
                    column_config={
                        "vest_date": st.column_config.DateColumn("Vest date", format="YYYY-MM-DD"),
                        "award_type": "Type", "settlement": "Paid in",
                        "shares_vesting": st.column_config.NumberColumn("Units", format=share_fmt),
                        "strike_price": st.column_config.NumberColumn("Strike", format="$%.2f"),
                        "est_unit_value_usd": st.column_config.NumberColumn("Value per unit", format="$%.2f"),
                        "payout_pct": st.column_config.NumberColumn("Payout %", format="%.0f"),
                        "est_price_usd": st.column_config.NumberColumn("Share price", format="$%.2f"),
                        "est_price_low": st.column_config.NumberColumn("Price low", format="$%.2f"),
                        "est_price_high": st.column_config.NumberColumn("Price high", format="$%.2f"),
                        "est_value_usd": st.column_config.NumberColumn("Est. value (USD)", format="$%.0f"),
                        "est_value_low": st.column_config.NumberColumn("Value low", format="$%.0f"),
                        "est_value_high": st.column_config.NumberColumn("Value high", format="$%.0f"),
                        "est_value_local": st.column_config.NumberColumn("Est. value (local)", format="%.0f"),
                    })
            st.caption("Units are gross, before tax withholding. Options and SARs show the gain over the strike. Orange notes mark items needing review.")

# ------------------------------------------------------------------ people
with tab_people:
    tab_note("<b>Who is vesting.</b> One row per person for the window. Open a person to see every grant and the "
             "full schedule behind it.")
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
        st.button("Open full profile", key="open_pick", on_click=open_emp, kwargs={"emp": pick},
                  use_container_width=True)
        emp_grants = data["grants"][data["grants"]["employee_id"] == pick]
        st.write(f"{len(emp_grants)} grant(s), each on its own schedule"
                 + (" (upcoming amounts reflect your what-if)" if is_whatif else ""))
        st.dataframe(engine.grant_summary(
            data, pick, wi_all if is_whatif else cur_all,
            get_whatif_tranches(data_dir, actions_key, rules_json, pick) if (is_whatif and ss["actions"]) else None),
            hide_index=True)
        st.dataframe(ev[ev["employee_id"] == pick], hide_index=True)

# ------------------------------------------------------------------ rules and guide
def bump_rules():
    ss["rules_ver"] += 1


def reset_all_rules():
    ss["rules"] = {}
    ss["rules_ver"] += 1


def reset_event_rules(scope_key, event):
    ss["rules"].get(scope_key, {}).pop(event, None)
    ss["rules_ver"] += 1


with tab_rules:
    r_view = (st.segmented_control("Section", ["Learn", "Edit rules"], key="r_view")
              if hasattr(st, "segmented_control")
              else st.radio("Section", ["Learn", "Edit rules"], horizontal=True, key="r_view")) or "Learn"

    if r_view == "Learn":
        topic = st.selectbox("What do you want to learn about?",
                             ["The lapse process", "Award types", "What-if events",
                              "What happens to an award (treatments)",
                              "How the numbers are calculated", "Glossary"], key="g_topic")
        if topic == "The lapse process":
            explain_box("<b>The lapse</b> is the vest day. This is a plain-language outline of how the work around it "
                        "runs. It is general, not any one company's process.")
            for title, text in learn.LAPSE_PROCESS:
                with st.expander(title, expanded=title.startswith("What a lapse")):
                    st.markdown(md(text), unsafe_allow_html=True)
        elif topic == "Award types":
            st.markdown("**At a glance**")
            st.dataframe(pd.DataFrame(
                [{"Award type": a, "Paid in": v[0], "Value in this app": v[1], "Depends on performance": v[2],
                  "Has a strike price": v[3]} for a, v in learn.SUMMARY.items()]), hide_index=True,
                use_container_width=True)
            aw = st.selectbox("Open one award type", R.AWARD_TYPES, key="g_award")
            info = learn.AWARDS[aw]
            st.markdown(f"### {info['name']}")
            st.markdown(f"*{info['tagline']}*")
            explain_box(f"<b>What it is.</b> {hx(info['what'])}<br><b>What the holder gets.</b> {hx(info['pays'])}"
                        f"<br><b>How this app values it.</b> {hx(info['value'])}")
            st.markdown("**Watch out for**")
            for w in info["watch"]:
                st.markdown("- " + md(w))
            exs = cur_all[(cur_all["award_type"] == aw) & (cur_all["est_value_usd"] > 0)].sort_values("vest_date").head(1)
            if not exs.empty:
                x = exs.iloc[0]
                explain_box(f"<b>Example from the data.</b> {hx(x['full_name'])} at {hx(x['company'])}, vesting "
                            f"{x['vest_date']:%b %d, %Y}:<br>{hx(example_text(x))}")
                st.button(f"Open {x['full_name']}'s profile", key=f"g_open_{aw}", on_click=open_emp,
                          kwargs={"emp": x["employee_id"]})
        elif topic == "What-if events":
            ev_key = st.selectbox("Event", list(R.EVENTS), format_func=R.EVENTS.get, key="g_event")
            info = learn.EVENTS[ev_key]
            st.markdown(f"### {R.EVENTS[ev_key]}")
            explain_box(f"<b>What it is.</b> {hx(info['what'])}<br><b>What typically happens.</b> {hx(info['typical'])}"
                        f"<br><b>Why it matters.</b> {hx(info['matters'])}")
            st.markdown("**What this app does by default, by award type**")
            st.dataframe(pd.DataFrame({"Award type": R.AWARD_TYPES,
                                       "Default treatment": [R.DEFAULT_TREATMENTS[ev_key][a] for a in R.AWARD_TYPES]}),
                         hide_index=True, use_container_width=True)
            if ev_key != "leave":
                st.caption(f"Vested options and SARs stay exercisable for {R.DEFAULT_WINDOW_DAYS[ev_key]} days by default"
                           + (f"; the clawback lookback is {R.DEFAULT_CLAWBACK_MONTHS[ev_key]} months."
                              if R.DEFAULT_CLAWBACK_MONTHS[ev_key] else "; no clawback."))
            st.caption("These defaults are examples of typical practice. Change them under Edit rules.")
        elif topic.startswith("What happens"):
            for name, text in learn.TREATMENTS.items():
                st.markdown(f"**{name}.** {md(text)}")
        elif topic.startswith("How the numbers"):
            for title, text in learn.HOW_NUMBERS_WORK:
                with st.expander(title):
                    st.markdown(md(text))
        else:
            for term, text in learn.GLOSSARY.items():
                with st.expander(term):
                    st.markdown(md(text))
        st.caption(learn.NOTE)

    else:
        explain_box("<b>Plan rules</b> decide what happens to each award type when something happens to a person. "
                    "The starting values are typical practice, not your company's actual plan. Change them for all "
                    "companies, or for one company, to match the plan documents. Changes apply to what-if events "
                    "straight away, and last for this visit only, so download them to keep a copy.")
        companies_all = sorted(data["companies"]["company_name"])
        s1, s2 = st.columns(2)
        scope_label = s1.selectbox("Applies to", [SCOPE_ALL] + companies_all, key="r_scope")
        ev_key = s2.selectbox("Event", list(R.EVENTS), format_func=R.EVENTS.get, key="r_event")
        scope_key = R.DEFAULT_SCOPE if scope_label == SCOPE_ALL else scope_label
        company_arg = None if scope_key == R.DEFAULT_SCOPE else scope_key
        base_rules = (R.default_rules() if company_arg is None
                      else R.resolve_rules({R.DEFAULT_SCOPE: ss["rules"].get(R.DEFAULT_SCOPE, {})}, None))
        cur_rules = R.resolve_rules(ss["rules"], company_arg)
        info = learn.EVENTS[ev_key]
        st.caption(f"{info['what']} {info['typical']}")

        opts = R.LEAVE_TREATMENTS if ev_key == "leave" else R.DEPARTURE_TREATMENTS
        tbl = pd.DataFrame({"Award type": R.AWARD_TYPES,
                            "What happens": [cur_rules[ev_key]["treatments"][a] for a in R.AWARD_TYPES],
                            "Starting value": [base_rules[ev_key]["treatments"][a] for a in R.AWARD_TYPES]})
        edited = st.data_editor(
            tbl, hide_index=True, use_container_width=True, disabled=["Award type", "Starting value"],
            key=f"rules_ed_{ss['rules_ver']}_{scope_key}_{ev_key}",
            column_config={"What happens": st.column_config.SelectboxColumn("What happens", options=opts, required=True)})
        new_tr, bad = {}, []
        for _, row in edited.iterrows():
            ok = row["What happens"] in R.allowed_treatments(ev_key, row["Award type"])
            new_tr[row["Award type"]] = row["What happens"] if ok else base_rules[ev_key]["treatments"][row["Award type"]]
            if not ok:
                bad.append(row["Award type"])
        if bad:
            st.warning(f"{', '.join(bad)}: that choice is not available for this award, so the starting value was kept. "
                       "An ESPP can only be forfeited or continue, because it has no unvested shares to accelerate.")
        new_rule = {"treatments": new_tr, "window_days": cur_rules[ev_key]["window_days"],
                    "clawback_months": cur_rules[ev_key]["clawback_months"]}
        if ev_key != "leave":
            n1, n2 = st.columns(2)
            new_rule["window_days"] = int(n1.number_input(
                "Vested options and SARs stay exercisable for (days)", 0, 3650, cur_rules[ev_key]["window_days"], 15,
                key=f"r_win_{ss['rules_ver']}_{scope_key}_{ev_key}",
                help="After this many days, vested options and SARs that were not exercised lapse."))
            new_rule["clawback_months"] = int(n2.number_input(
                "Clawback lookback (months, 0 = none)", 0, 120, cur_rules[ev_key]["clawback_months"], 1,
                key=f"r_claw_{ss['rules_ver']}_{scope_key}_{ev_key}",
                help="Value delivered in this many months before the event is shown as clawback exposure."))
        new_ov = R.diff_to_overrides({ev_key: new_rule}, {ev_key: base_rules[ev_key]})
        scope_ov = dict(ss["rules"].get(scope_key, {}))
        if ev_key in new_ov:
            scope_ov[ev_key] = new_ov[ev_key]
        else:
            scope_ov.pop(ev_key, None)
        updated = {**{k: v for k, v in ss["rules"].items() if k != scope_key}, **({scope_key: scope_ov} if scope_ov else {})}
        if json.dumps(updated, sort_keys=True) != rules_json:
            ss["rules"] = updated
            st.rerun()

        n_custom = R.count_overrides(ss["rules"], scope_key)
        st.caption(f"{n_custom} customized setting(s) for {scope_label.lower() if scope_key == R.DEFAULT_SCOPE else scope_label}."
                   if n_custom else "Nothing customized here: using the starting values.")
        b1, b2 = st.columns(2)
        b1.button("Reset this event", on_click=reset_event_rules, kwargs={"scope_key": scope_key, "event": ev_key},
                  use_container_width=True)
        b2.button("Reset all rules", on_click=reset_all_rules, use_container_width=True)
        with st.expander("All events at a glance"):
            st.dataframe(pd.DataFrame(R.rules_matrix(cur_rules)), hide_index=True)
            st.caption("Rows are events, columns are award types. Shows the rules for "
                       f"{'all companies' if company_arg is None else company_arg}.")
        with st.expander("Save or load my rules"):
            st.download_button("Download my rules (JSON)", json.dumps(ss["rules"], indent=2, sort_keys=True).encode("utf-8"),
                               file_name="plan_rules.json", mime="application/json", use_container_width=True)
            up = st.file_uploader("Load rules from a file", type=["json"], key=f"r_upload_{ss['rules_ver']}")
            if up is not None:
                try:
                    loaded = R.clean_overrides(json.loads(up.getvalue().decode("utf-8")))
                except (ValueError, UnicodeDecodeError):
                    st.error("That file is not valid rules JSON.")
                else:
                    ss["rules"] = loaded
                    ss["rules_ver"] += 1
                    st.rerun()
        st.caption("PSU and performance cash payouts are set per company in the what-if builder, on the "
                   "Performance payout tab.")

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
        st.text_input("Data folder", key="data_dir")
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
