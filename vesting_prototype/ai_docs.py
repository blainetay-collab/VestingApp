"""Product documentation for the vesting tool: user flows, technical diagrams and a user guide.

Shown inside the 'How I used AI' section. Like ai_story.py it imports nothing from the engine, so it cannot affect
the vesting numbers. Everything here describes the prototype as built; update it when the app changes.
"""
from __future__ import annotations

import html as _html

import streamlit as st

CSS = """<style>
.fl{display:flex;flex-wrap:wrap;align-items:stretch;gap:.35rem;margin:.4rem 0 .9rem 0}
.fn{border-radius:.7rem;padding:.45rem .65rem;font-size:.84rem;line-height:1.25;max-width:13rem;border:1px solid}
.fn.u{background:rgba(37,99,235,.10);border-color:rgba(37,99,235,.5)}
.fn.a{background:rgba(16,185,129,.10);border-color:rgba(16,185,129,.5)}
.fn.d{background:rgba(245,158,11,.12);border-color:rgba(245,158,11,.75);border-style:dashed}
.fn.s{background:#2563EB;color:#fff;border-color:#2563EB;border-radius:1rem;font-weight:600;align-self:center}
.fa{align-self:center;opacity:.55;font-size:1.05rem}
.ar-v{display:none}
.lg{display:flex;flex-wrap:wrap;gap:.4rem;margin:.2rem 0 .3rem 0;font-size:.74rem}
.lg span{border:1px solid;border-radius:999px;padding:.05rem .55rem}
.lg .u{border-color:rgba(37,99,235,.6);background:rgba(37,99,235,.10)}
.lg .a{border-color:rgba(16,185,129,.6);background:rgba(16,185,129,.10)}
.lg .d{border-color:rgba(245,158,11,.8);background:rgba(245,158,11,.12);border-style:dashed}
.lay{display:grid;grid-template-columns:1fr auto 1fr auto 1fr auto 1fr;gap:.4rem;align-items:start;margin:.4rem 0 .8rem 0}
.lay .fa{align-self:center}
.lh{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;opacity:.7;margin-bottom:.3rem}
.lb{border:1px solid rgba(128,128,128,.35);border-radius:.8rem;padding:.45rem .6rem;margin-bottom:.4rem;font-size:.8rem;
    line-height:1.3;background:rgba(128,128,128,.06)}
.lb b{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.78rem}
.lb.later{border-style:dashed;opacity:.75}
.erg{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:.6rem;margin:.4rem 0}
.tb{border:1px solid rgba(128,128,128,.4);border-radius:.7rem;overflow:hidden;font-size:.78rem}
.tb h5{margin:0;padding:.35rem .6rem;background:#2563EB;color:#fff;font-size:.82rem}
.tb div{padding:.12rem .6rem;border-top:1px solid rgba(128,128,128,.15);font-family:ui-monospace,Menlo,Consolas,monospace}
.tb .k{font-weight:700}
.tb i{font-style:normal;font-size:.62rem;font-weight:700;border-radius:.3rem;padding:0 .3rem;margin-left:.3rem;
      background:rgba(245,158,11,.25)}
.tb i.pk{background:rgba(16,185,129,.28)}
.dg-cap{font-size:.8rem;opacity:.72;margin:.2rem 0 .6rem 0}
.dg-t{width:100%;border-collapse:collapse;font-size:.84rem;margin:.3rem 0 .6rem 0}
.dg-t th,.dg-t td{border:1px solid rgba(128,128,128,.3);padding:.35rem .5rem;text-align:left;vertical-align:top}
.dg-t th{background:rgba(128,128,128,.12);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}
.dg-w{overflow-x:auto}
.stack{display:flex;flex-direction:column;gap:.3rem;margin:.4rem 0 .8rem 0;max-width:34rem}
.stack .lv{border-radius:.7rem;padding:.5rem .7rem;font-size:.85rem;border:1px solid rgba(128,128,128,.4)}
.stack .lv small{display:block;opacity:.75}
.stack .l1{background:rgba(128,128,128,.10)}.stack .l2{background:rgba(37,99,235,.10)}
.stack .l3{background:rgba(245,158,11,.14)}.stack .l4{background:rgba(16,185,129,.14);font-weight:600}
@media (max-width:820px){
 .fl{flex-direction:column;align-items:stretch}.fn{max-width:none}
 .ar-h{display:none}.ar-v{display:inline}.fa{text-align:center}
 .lay{grid-template-columns:1fr}
}
</style>"""


def hx(t) -> str:
    return _html.escape(str(t)).replace("$", "&#36;")


# ------------------------------------------------------------------ building blocks
def flow(nodes: list[tuple[str, str]]) -> str:
    """nodes: (kind, text). kinds: s start/end, u you do, a the app does, d decision or choice."""
    parts = []
    for i, (k, t) in enumerate(nodes):
        if i:
            parts.append('<div class="fa"><span class="ar-h">&rarr;</span><span class="ar-v">&darr;</span></div>')
        parts.append(f'<div class="fn {k}">{hx(t)}</div>')
    return '<div class="fl">' + "".join(parts) + "</div>"


LEGEND = ('<div class="lg"><span class="u">You do</span><span class="a">The app does</span>'
          '<span class="d">Choice</span></div>')


def table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{hx(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{hx(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="dg-w"><table class="dg-t"><tr>{th}</tr>{body}</table></div>'


def cap(t: str) -> str:
    return f'<div class="dg-cap">{hx(t)}</div>'


# ------------------------------------------------------------------ user flows
FLOWS = {
    "See what vests soon": (
        "Answers: what is scheduled to vest, and what is it worth at today's price?",
        [("s", "Open the app"), ("u", "Choose the Current schedule view"), ("u", "Set the As of date and a Window "
         "(30, 90, 180 or 365 days)"), ("d", "Need a subset?"), ("u", "Open Filters: company, country, department, "
         "award type, or search a name"), ("a", "Recalculates every event in the window and values it"),
         ("a", "Shows headline units and value, split into paid in shares and paid in cash"),
         ("u", "Browse Overview, Events or People"), ("s", "Export CSV or Excel")]),
    "Run a what-if": (
        "Answers: what changes if prices move, people leave or performance pays out differently?",
        [("s", "Switch the View to What-if"), ("d", "Quick start or build it?"),
         ("u", "Tap a preset (market down 20%, 15% attrition, PSUs pay 150%) or open the builder tabs"),
         ("u", "Share price: pick a price path or shift today's price"), ("u", "Performance payout: set a payout % per company"),
         ("u", "People and events: add attrition, a departure, death, disability, a violation or a leave"),
         ("a", "Rebuilds the schedule using the plan rules"),
         ("a", "Compares What-if with Current, with a bridge showing what moved the total"),
         ("u", "Open Lapse day to compare one vest date, then Events for timing changes and the side-effects panel"), ("s", "Reset the what-if")]),
    "Dive into one person": (
        "Answers: what does this person hold and when does each piece vest?",
        [("s", "Overview: Up next"), ("u", "Tap Open next to a name (or pick someone in the People tab and tap Open full profile)"),
         ("a", "Opens a full-page profile and keeps your filters and view"),
         ("u", "Move between Schedule, Grants, Events and Details"), ("u", "Open one grant for its timeline and progress"),
         ("u", "Export the person's events as CSV"), ("s", "Tap Back to overview")]),
    "Change the plan rules": (
        "Answers: what happens to each award type when something happens to the person?",
        [("s", "Rules and guide tab"), ("u", "Choose Edit rules"), ("d", "All companies or one company?"),
         ("u", "Pick an event, then set a treatment for each award type, the option window and the clawback look-back"),
         ("a", "Stores only what differs from the defaults, as overrides"),
         ("a", "Uses the rules next time a what-if event is applied"),
         ("u", "Download the rules as a JSON file, or load a saved one"), ("s", "Rules apply per company")]),
    "Produce a report": (
        "Answers: how do I hand the numbers to someone else?",
        [("s", "Reports and data tab"), ("u", "Choose whether to include event detail and employee names"),
         ("u", "Tick Prepare downloads"), ("a", "Builds the Excel and PDF from the active filters"),
         ("u", "Download Excel or PDF"), ("d", "Doubt the data?"), ("u", "Check the validation findings or run the "
         "schedule check"), ("a", "Rebuilds tranches from the schedule templates and compares them"), ("s", "Share")]),
    "Learn as you go": (
        "Answers: what does this award, payout or event mean?",
        [("s", "Rules and guide tab"), ("u", "Choose Learn"), ("u", "Pick a topic: award types, what-if events, "
         "treatments, how the numbers work, glossary"), ("a", "Explains in plain language with a worked example"),
         ("u", "Open one award type to see a real example person"), ("s", "Tap through to that person's profile")]),
}


def out_flows() -> None:
    names = list(FLOWS)
    tabs = st.tabs(names)
    for tb, n in zip(tabs, names):
        with tb:
            goal, nodes = FLOWS[n]
            st.markdown(f"**{goal}**")
            st.markdown(LEGEND + flow(nodes), unsafe_allow_html=True)


# ------------------------------------------------------------------ technical diagrams
def d_architecture() -> None:
    arrow = '<div class="fa"><span class="ar-h">&rarr;</span><span class="ar-v">&darr;</span></div>'

    def col(title, boxes):
        return f'<div><div class="lh">{hx(title)}</div>' + "".join(
            f'<div class="lb{" later" if later else ""}"><b>{hx(n)}</b><br>{hx(t)}</div>' for n, t, later in boxes) + "</div>"
    html = ('<div class="lay">'
            + col("Data", [("CSV files", "companies, employees, grants, tranches, schedules, prices, FX", False),
                           ("generate_data.py", "seeded synthetic data, same every run", False),
                           ("Brokerage import", "later: Excel/CSV from a real platform", True)]) + arrow
            + col("Logic", [("engine.py", "load, validate, expand schedules, value events, apply what-if, side effects", False),
                            ("rules.py", "award types, events, treatments and per-company overrides", False)]) + arrow
            + col("App", [("app.py", "Streamlit: views, filters, builder, profile, rules editor", False),
                          ("learn.py", "guide text for award types, events and terms", False),
                          ("ai_story.py, ai_docs.py", "this section; no link to the engine", False)]) + arrow
            + col("Outputs", [("charts.py", "monthly, bridge, bullet, timeline charts", False),
                              ("reports.py", "Excel and PDF reports", False),
                              ("CSV exports", "events, people, rules (JSON)", False)]) + "</div>")
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(cap("Data flows left to right. The engine is plain Python and pandas with no screen code, so it can be "
                    "tested alone. Dashed: not built yet."), unsafe_allow_html=True)


def d_data_model() -> None:
    def tb(name, rows):
        body = ""
        for f, tag in rows:
            badge = f'<i class="{"pk" if tag == "PK" else ""}">{tag}</i>' if tag else ""
            body += f'<div class="{"k" if tag == "PK" else ""}">{hx(f)}{badge}</div>'
        return f'<div class="tb"><h5>{hx(name)}</h5>{body}</div>'
    html = '<div class="erg">' + "".join([
        tb("companies", [("company_id", "PK"), ("company_name", ""), ("ticker", ""), ("industry", ""), ("hq_country", "")]),
        tb("employees", [("employee_id", "PK"), ("company_id", "FK"), ("full_name", ""), ("department", ""),
                         ("country", ""), ("tax_residency_country", ""), ("hire_date", ""), ("employment_status", "")]),
        tb("grants", [("grant_id", "PK"), ("employee_id", "FK"), ("vesting_schedule_id", "FK"), ("ticker", ""),
                      ("award_type", ""), ("settlement", ""), ("total_shares", ""), ("strike_price", ""),
                      ("grant_date", ""), ("expiry_date", ""), ("perf_metric / perf_max_pct", ""),
                      ("election_83b", ""), ("purchase_discount / lookback", "")]),
        tb("vesting_tranches", [("tranche_id", "PK"), ("grant_id", "FK"), ("employee_id", "FK"), ("vest_date", ""),
                                ("shares_vesting", ""), ("status", ""), ("contribution_usd", ""),
                                ("offering_start_date / price", "")]),
        tb("vesting_schedules", [("vesting_schedule_id", "PK"), ("description", ""), ("total_months", ""),
                                 ("cliff_months", ""), ("interval_months", "")]),
        tb("market_data", [("ticker", "PK"), ("price_usd", ""), ("price_date", ""), ("annual_volatility", ""),
                           ("assumed_annual_growth", "")]),
        tb("price_history", [("ticker", "FK"), ("price_date", ""), ("close_usd", "")]),
        tb("fx_rates", [("currency", "PK"), ("units_per_usd", ""), ("rate_date", ""), ("source", "")]),
    ]) + "</div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(table(["Relationship", "Meaning"],
                      [["company 1 to many employees", "One tool, many companies; the Company filter uses this"],
                       ["employee 1 to many grants", "One person holds several awards"],
                       ["grant 1 to many tranches", "Each grant becomes dated vesting events (separate tables on purpose)"],
                       ["grant many to 1 schedule", "A schedule template such as 4 years, 1-year cliff, monthly"],
                       ["grant / company to market_data by ticker", "Price, volatility and growth for valuation"]]),
                unsafe_allow_html=True)
    st.markdown(cap("PK primary key, FK foreign key. Column names are the ones in the generated CSV files."),
                unsafe_allow_html=True)


def d_value_pipeline() -> None:
    st.markdown(flow([("s", "A vesting tranche (units, date)"), ("a", "Price at the vest date: flat, growth or "
                       "bear/base/bull, plus any price shock"), ("a", "Value by award type (table below)"),
                      ("a", "Split: paid in shares or paid in cash"), ("a", "Convert to USD, add flags (underwater, "
                       "payout, review)"), ("s", "Card, chart or report line")]), unsafe_allow_html=True)
    st.markdown(table(
        ["Award type", "Value at vest", "Paid in"],
        [["RSU, Restricted Stock", "units x price", "Shares"],
         ["PSU", "target units x payout % x price (capped per grant)", "Shares"],
         ["Stock Option", "units x max(price - strike, 0)", "Shares on exercise"],
         ["SAR (stock-settled)", "units x max(price - strike, 0), delivered as shares worth the gain", "Shares"],
         ["SAR (cash-settled)", "units x max(price - strike, 0)", "Cash"],
         ["Phantom Stock", "units x price", "Cash"],
         ["Performance Cash", "units (USD) x payout %", "Cash"],
         ["ESPP", "shares = contribution / ((1 - discount) x lower of start price and purchase price)", "Shares"]]),
        unsafe_allow_html=True)


def d_whatif_order() -> None:
    st.markdown(flow([("s", "Current schedule"), ("a", "1. People events: departures, death, disability, "
                       "violation, leave"), ("a", "2. Attrition: assumed annual %"),
                      ("a", "3. Performance payout per company"), ("a", "4. Share price change today"),
                      ("a", "5. Price path: flat, growth or range"), ("s", "What-if schedule")]), unsafe_allow_html=True)
    st.markdown(cap("Each step is applied on top of the last. The bridge chart shows how much each step moved the "
                    "total, and the steps add up exactly to the full what-if. The order matters: for example, a "
                    "layoff removes units before a price change is valued."), unsafe_allow_html=True)


def d_rules() -> None:
    st.markdown(
        '<div class="stack"><div class="lv l1"><b>1. Built-in defaults</b><small>typical market practice, per '
        'event and award type</small></div>'
        '<div class="lv l2"><b>2. All-companies overrides</b><small>your changes under "All companies"</small></div>'
        '<div class="lv l3"><b>3. Company overrides</b><small>your changes for one company</small></div>'
        '<div class="lv l4">Result used by the what-if: treatment per award type, option window (days), clawback '
        'look-back (months)</div></div>', unsafe_allow_html=True)
    st.markdown(table(
        ["Treatment", "What it does to unvested awards"],
        [["Forfeit", "Unvested units are cancelled"],
         ["Accelerate in full", "Everything vests at the event date (PSUs at target)"],
         ["Pro-rata", "Vest the share earned by time served so far; the rest is cancelled"],
         ["Continue vesting", "The schedule carries on as if the person stayed"],
         ["Pause vesting", "Leave of absence only: vesting stops, then resumes"]]), unsafe_allow_html=True)
    st.markdown(cap("Later layers win over earlier ones. Only differences are stored, so 'customized' is easy to "
                    "show and a rules file stays small."), unsafe_allow_html=True)


def d_deploy() -> None:
    st.markdown(flow([("u", "Edit the code (phone or laptop)"), ("a", "Upload files to the GitHub repository"),
                      ("a", "Streamlit Community Cloud notices the change and redeploys"),
                      ("a", "First visit: generate the demo data once and keep it on the server"),
                      ("s", "Public link anyone can open")]), unsafe_allow_html=True)
    st.markdown(table(
        ["Today (prototype)", "Needed for a real product"],
        [["Free hosting; public repository; app sleeps when idle", "Private hosting and always-on service"],
         ["No login", "User accounts and roles"],
         ["Synthetic CSV data generated in the app", "A database fed by real platform exports"],
         ["Rules kept in the session and downloadable as JSON", "Rules saved per company, with an audit trail"]]),
        unsafe_allow_html=True)


DIAGRAMS = {
    "Architecture": d_architecture,
    "Data model": d_data_model,
    "How a value is calculated": d_value_pipeline,
    "What-if order": d_whatif_order,
    "Plan rules": d_rules,
    "Hosting": d_deploy,
}


def out_diagrams() -> None:
    tabs = st.tabs(list(DIAGRAMS))
    for tb, (n, fn) in zip(tabs, DIAGRAMS.items()):
        with tb:
            fn()


# ------------------------------------------------------------------ user guide
GUIDE = {
    "Getting started": """
**What it is.** A prototype that tracks stock awards for many companies and people, shows what is scheduled to vest,
and lets you test what-if changes. All data is synthetic (8 companies, 980 people).

**The two views** (switch at the top)
- **Current schedule:** everything scheduled to vest, valued at today's share prices.
- **What-if:** change prices, payouts, headcount or leave, and compare with the current schedule.

**The controls**
- **As of** sets today's date. **Window** is how far ahead to look: 30, 90, 180 or 365 days.
- **Filters** (a button; on a phone, tap it) narrows by company, country, department, award type, or a name or ID search.
  Active filters show as chips below. **Clear filters** resets them.

**The six tabs:** Lapse day, Overview, Events, People, Rules and guide, Reports and data.

**L-numbers.** Cards show how far away a vest is as *L-12*: twelve days before the lapse (vest) day. *L-0* is the day itself.
""",
    "Current schedule": """
**Headline.** The top card shows units and estimated value vesting in your window. The cards below split the value
into **paid in shares** and **paid in cash**, and count events, people and companies.

**Lapse day.** Pick one vest date. See value, people, events and how much is paid in shares or cash, a "Ready by L-4"
checklist of what the team confirms beforehand, breakdowns by country, company and award type, and the biggest events.

**Overview**
- A monthly chart of what vests. Choose a horizon (12 to 48 months), measure (estimated value or units),
  an optional split, and whether to show a running total.
- **Up next** cards list the next events. Tap **Open** to see that person's profile.
- Breakdown tables and bullet charts show where value vests.

**Events.** Every event in the window as cards or a table. Show more cards, show all columns, and export CSV or Excel.
Flags on a card explain things like options below their strike price (underwater).

**People.** A table with one row per person in the window. Pick a person and tap **Open full profile**.
""",
    "What-if": """
**Three steps.** 1) Start with a quick scenario. 2) Fine-tune it in the tabs. 3) Read the impact on the **Lapse day** tab. A summary box under the settings shows your changes and what they do to the next lapse day.

**Start fast.** Tap a preset: *Market down 20%*, *Market up 20%*, *15% attrition*, *PSUs pay 50%*, *PSUs pay 150%*.

**Or build your own, in three tabs**
1. **Share price.** Choose a price path (*Flat*, *Growth*, or *Range: bear, base, bull*) and shift today's price by -50% to
   +50%. Optionally use each company's own growth and volatility.
2. **Performance payout.** Set how much PSUs and performance cash pay, per company, or set every company at once (0 to 200%).
3. **People and events.** Set an assumed annual attrition (0 to 30%). Add an event for specific people or everyone in
   your filters: resignation, termination, retirement, death, disability, violation or leave of absence (for a
   leave, choose how many months vesting pauses). Press **Add event**.

**Read the result.** The page compares What-if with Current. A **bridge chart** shows how much each change moved the
total. On the Events tab you can show only timing changes. A side-effects panel shows **clawback exposure** (value
already delivered that could be recovered) and **options that could lapse**.

**Reset** returns to the current schedule.
""",
    "Employee profile": """
Open it from an **Up next** card, from the **People** tab (pick a person, then Open full profile), or from an example in the guide. It keeps your view and
filters, so **Back to overview** returns you where you were.

- **Schedule:** a timeline of when each grant vests, sized by how much of the grant each event is.
- **Grants:** every award the person holds with progress to fully vested. Open one grant for its own timeline.
- **Events:** the person's upcoming events and, in What-if, the timing changes; export them as CSV.
- **Details:** employee ID, email, company, department, work country, tax residency, currency, hire date, tenure and status.

In the What-if view the profile shows the what-if schedule for that person.
""",
    "Rules and guide": """
**Learn.** Pick a topic: the lapse process, award types, what-if events, what happens to an award (treatments), how the numbers are
calculated, or the glossary. Open one award type to see a real example person.

**Edit rules.** For each event (resignation, layoff, for-cause termination, retirement, death, disability, violation,
leave) and each award type, choose what happens: *Forfeit*, *Accelerate in full*, *Pro-rata*, *Continue vesting*, or for
leave *Pause vesting*. Also set how long vested options and SARs stay exercisable (days) and the clawback look-back
(months).

- Choose **All companies** or one company. Company settings win over the all-companies settings.
- **Download my rules (JSON)** saves your changes. **Load rules from a file** brings them back.
- Defaults are typical practice, not legal advice. Real plans differ, which is why every rule is editable.
""",
    "Reports and data": """
**Reports.** Choose whether to include event detail and employee names (otherwise IDs only). Tick **Prepare
downloads** to build the **Excel** and **PDF** reports from your active filters. They are built on demand because they
take a moment.

**Data checks.** The app validates the data (for example missing countries, share totals that do not match tranches,
invalid dates) and lists findings. **Run schedule check** rebuilds the vesting events from the schedule templates and
confirms the stored events match.

**Exports.** Most tables have a CSV export, and Events also exports Excel.
""",
    "FAQ": """
**Is any of this real data?** No. Companies, people, prices and grants are synthetic.

**Is this tax or legal advice?** No. Tax is described in the guide but not calculated, and default rules are typical
practice only.

**Why is an option worth nothing?** Options and SARs are worth the share price minus the strike price, never below
zero. Below the strike they are *underwater* and flagged.

**What is the difference between pausing and continuing during a leave?** Pause stops vesting and resumes later;
Continue keeps the schedule running as normal. Companies differ, so both are choices.

**Why do SARs show shares for some and cash for others?** Stock-settled SARs deliver shares worth the gain; cash-settled
SARs pay that gain in cash. See Rules and guide > Learn.

**My what-if disappeared.** Use the preset or builder again; Reset clears it on purpose.
""",
}


def out_guide() -> None:
    tabs = st.tabs(list(GUIDE))
    for tb, (n, body) in zip(tabs, GUIDE.items()):
        with tb:
            st.markdown(body.replace("$", "\\$"))


# ------------------------------------------------------------------ entry point
def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("These documents describe the prototype as built. I wrote them with the AI, working from the app "
                "itself, and they are the kind of product documentation a team would keep next to a tool like this.")
    with st.expander(f"User flows ({len(FLOWS)})", expanded=True):
        out_flows()
    with st.expander(f"Technical diagrams ({len(DIAGRAMS)})", expanded=False):
        out_diagrams()
    with st.expander(f"User guide ({len(GUIDE)} chapters)", expanded=False):
        out_guide()
