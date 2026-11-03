"""'How I used AI for the product work' - a self-contained section, separate from the vesting tool.

It imports nothing from the engine, so it cannot affect the vesting numbers. The content is a record of how the
product work actually went: what was asked, what the AI did, and what the human decided. Edit the lists below to
keep it accurate; nothing here is computed.
"""
from __future__ import annotations

import html as _html
from pathlib import Path

import streamlit as st

import rules as R

CSS = """<style>
.ai-hero{border:1px solid rgba(128,128,128,.3);border-radius:1rem;padding:1.1rem 1.2rem;margin:.4rem 0 1rem 0;
         background:linear-gradient(135deg,rgba(37,99,235,.10),rgba(37,99,235,.02))}
.ai-hero h2{margin:0 0 .35rem 0;font-size:1.45rem;line-height:1.25}
.ai-hero p{margin:.2rem 0;opacity:.85}
.ai-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.6rem;margin:.6rem 0 1rem 0}
.ai-stat{border:1px solid rgba(128,128,128,.25);border-radius:.8rem;padding:.65rem .8rem}
.ai-stat b{display:block;font-size:1.35rem}
.ai-stat span{font-size:.78rem;opacity:.7}
.ai-step{border:1px solid rgba(128,128,128,.28);border-radius:1rem;padding:.9rem 1rem;margin:.2rem 0 .9rem 0}
.ai-step-h{display:flex;gap:.6rem;align-items:center;margin-bottom:.5rem}
.ai-num{flex:0 0 auto;width:1.9rem;height:1.9rem;border-radius:999px;background:#2563EB;color:#fff;font-weight:700;
        display:flex;align-items:center;justify-content:center;font-size:.9rem}
.ai-step-t{font-weight:700;font-size:1.05rem;line-height:1.25}
.ai-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem}
@media (max-width:820px){.ai-grid{grid-template-columns:1fr}}
.ai-col{border-radius:.7rem;padding:.6rem .75rem;background:rgba(128,128,128,.08);font-size:.92rem}
.ai-col h4{margin:0 0 .3rem 0;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;opacity:.65}
.ai-col.me{background:rgba(37,99,235,.10)}
.ai-col.ai{background:rgba(16,185,129,.10)}
.ai-col.dec{background:rgba(245,158,11,.12)}
.ai-col ul{margin:.1rem 0 0 1.1rem;padding:0}
.ai-q{font-style:italic}
.ai-out{margin-top:.6rem;font-size:.85rem;opacity:.8}
.ai-pill{display:inline-block;font-size:.72rem;border:1px solid rgba(128,128,128,.4);border-radius:999px;
         padding:.1rem .55rem;margin:.1rem .25rem .1rem 0}
.ai-note{border-left:4px solid #F59E0B;padding:.5rem .8rem;margin:.6rem 0;background:rgba(245,158,11,.08);
         border-radius:0 .6rem .6rem 0;font-size:.92rem}

.ai-dl{border:1px solid rgba(37,99,235,.35);border-radius:1rem;padding:.8rem 1rem;margin:.2rem 0 1rem 0;background:rgba(37,99,235,.06)}
.ai-dl b{font-size:1.02rem}
.ai-dl p{margin:.25rem 0 0 0;font-size:.88rem;opacity:.8}
.ai-tbl{width:100%;border-collapse:collapse;font-size:.86rem;margin:.2rem 0 .6rem 0}
.ai-tbl th,.ai-tbl td{border:1px solid rgba(128,128,128,.3);padding:.35rem .5rem;text-align:left;vertical-align:top}
.ai-tbl th{background:rgba(128,128,128,.12);font-size:.74rem;text-transform:uppercase;letter-spacing:.04em}
.ai-tblwrap{overflow-x:auto}
.ai-cap{font-size:.8rem;opacity:.7;margin:.2rem 0 .5rem 0}
.mm{display:grid;grid-template-columns:1fr auto 1fr;gap:0 .3rem;align-items:center;margin:.4rem 0}
.mm-col{display:flex;flex-direction:column;gap:.7rem}
.mm-h{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700;opacity:.8}
.mm-col.l .mm-h{text-align:right}
.mm-b{display:flex;align-items:center;gap:.45rem}
.mm-b.l{justify-content:flex-end}
.mm-b.r{justify-content:flex-start}
.mm-bn{position:relative;font-weight:700;font-size:.86rem;border-radius:.7rem;padding:.45rem .6rem;max-width:8.5rem;text-align:center;line-height:1.2}
.mm-leaves{display:flex;flex-direction:column;gap:.22rem}
.mm-leaf{font-size:.78rem;border-radius:.5rem;padding:.2rem .5rem;line-height:1.25}
.mm-col.l .mm-bn{background:rgba(16,185,129,.22);border:1px solid rgba(16,185,129,.7)}
.mm-col.l .mm-leaf{background:rgba(16,185,129,.09);border:1px solid rgba(16,185,129,.35)}
.mm-col.r .mm-bn{background:rgba(245,158,11,.22);border:1px solid rgba(245,158,11,.8)}
.mm-col.r .mm-leaf{background:rgba(245,158,11,.10);border:1px dashed rgba(245,158,11,.7)}
.mm-col.l .mm-bn::after{content:"";position:absolute;right:-.9rem;top:50%;width:.9rem;border-top:2px solid rgba(16,185,129,.7)}
.mm-col.r .mm-bn::before{content:"";position:absolute;left:-.9rem;top:50%;width:.9rem;border-top:2px dashed rgba(245,158,11,.8)}
.mm-col.l .mm-leaves{text-align:right}
.mm-core{background:#2563EB;color:#fff;border-radius:1rem;padding:.9rem 1rem;font-weight:700;text-align:center;
         width:8.5rem;margin:0 .9rem;line-height:1.25}
.mm-core small{display:block;font-weight:400;opacity:.85;margin-top:.25rem;font-size:.72rem}
@media (max-width:820px){
 .mm{display:flex;flex-direction:column}.mm-core{order:-1;width:auto;margin:.4rem 0 .2rem 0}
 .mm-col{margin-top:.9rem}.mm-col.l .mm-h{text-align:left}
 .mm-b.l,.mm-b.r{flex-direction:column;align-items:stretch}
 .mm-b.l{flex-direction:column-reverse}
 .mm-bn{max-width:none;text-align:left}.mm-bn::before,.mm-bn::after{display:none}
 .mm-col.l .mm-leaves{text-align:left}
}
</style>"""


def hx(t) -> str:
    return _html.escape(str(t)).replace("$", "&#36;")


# Each step: title, my prompt (lightly cleaned up from what I actually typed), what the AI did,
# what I decided or contributed, and what came out of it.
STEPS = [
    {"title": "Frame the problem and write the PRD",
     "me": "I want to learn how stock plan vesting works. Today the process is very manual. I want to build a "
           "prototype start to finish to build my own knowledge and skills. First a PRD. Start with a source of data: employees "
           "across countries, their unvested stock, and when each segment vests. Then list upcoming vesting events "
           "with a predicted market value, and produce reports for clients.",
     "ai": ["Turned a loose idea into a structured PRD: problem, users, scope, data model, functional requirements, "
            "open questions.",
            "Split the work into stages (data, engine, reports) so each could be built and checked on its own."],
     "dec": ["Chose the end-to-end goal: learn the domain by building something real, start to finish.",
             "Kept the scope to vesting events and reports, not tax filing or trading."],
     "out": "PRD document"},
    {"title": "Learn the domain: how brokerages and stock plans work",
     "me": "Can you help me do some research for point 13? I don't know how this all works.",
     "ai": ["Researched how stock plan brokerages and administrators work and what data they export.",
            "Wrote it up as Section 13 of the PRD so the learning became part of the product document."],
     "dec": ["Said plainly that I did not know the domain, so the research started from the right level.",
             "Asked for it to be written into the PRD, not left in chat."],
     "out": "PRD Section 13 (brokerage research)"},
    {"title": "Close the open questions, and assume what cannot be known",
     "me": "Can you do more research on the open questions? Which award types, which brokerage, internal or external "
           "audience, reporting currency, how to handle forfeitures and acceleration, preferred stack.",
     "ai": ["Researched each question and laid out the common answers and trade-offs.",
            "Flagged which questions only the employer can answer."],
     "dec": ["For the two that cannot be answered without inside information, I said: let's make assumptions, "
             "it doesn't have to be perfect for a prototype.",
             "Picked the prototype stack."],
     "out": "PRD Section 14 (assumptions)"},
    {"title": "Use AI as a tutor on the instrument itself",
     "me": "Tell me more about RSUs. Explain tranches vs grants.",
     "ai": ["Explained RSUs, grants, tranches and vesting in plain language with examples."],
     "dec": ["Used the explanation to check the data model matched how the real thing works: one grant, many tranches."],
     "out": "Shared vocabulary for the data and the app"},
    {"title": "Generate a realistic data source",
     "me": "Can you generate a data source to hook up to my prototype? I want people across the globe, and each person "
           "can have multiple segments of stock vesting at different times.",
     "ai": ["Wrote a seeded generator (same data every run) with employees, grants, vesting schedules and tranches.",
            "Checked that tranches add up to each grant."],
     "dec": ["Asked for global coverage and multiple tranches per person.",
             "Later asked for many more people and many companies, so filters would matter."],
     "out": "Synthetic dataset: 8 companies, 980 people, about 3,300 grants, about 48,000 tranches"},
    {"title": "Build, look at it, change it",
     "me": "Build me a prototype engine I can run on my computer. Then: add many more recipients and companies, "
           "filters per company, export based on the active filters, and a chart of what vests by month.",
     "ai": ["Built the vesting engine and a Streamlit app with an upcoming-events list, valuation at a projected price "
            "and reports.",
            "Added company, country and department filters, filtered export and a monthly chart."],
     "dec": ["Ran it myself and reported what I saw (for example, not seeing the new tab), so fixes were based on the "
             "real thing.",
             "Pushed it to GitHub and hosted it so anyone can open it."],
     "out": "Working, hosted prototype"},
    {"title": "Bring in the real operational problem: pre-lapse and leave of absence",
     "me": "Look into leave of absence and how it impacts grants and taxes. The biggest challenge with the lapse process "
           "is the time it takes. They want pre-lapse processing: what information is needed L-4 that will not change "
           "day to day, like mobility and jurisdiction, down to the person, so on L-0 we only process the lapse.",
     "ai": ["Researched leave of absence practice. Survey data cited in the research: more than 90% of companies do "
            "not adjust vesting for statutory or paid leave, and about 83% do not for unpaid non-statutory leave.",
            "Translated my L-4 / L-0 framing into a list of data that is stable ahead of time versus data that only "
            "settles on lapse day."],
     "dec": ["The L-4 / L-0 framing came from my own understanding of how lapse processing works, not from the AI.",
             "Decided leave of absence belongs in the what-if as a pause or continue choice."],
     "out": "Leave of absence what-if; pre-lapse readiness is a planned feature"},
    {"title": "Make the product usable: UI review",
     "me": "The filter tab on mobile isn't very visible. The tool is really designed to have a what-if scenario and what "
           "is currently available. I don't like the current UI. Make it better looking on mobile and desktop. "
           "Give me recommendations.",
     "ai": ["Reviewed the UI and proposed changes: two clear views, cards on phones, a filters popover, a summary band.",
            "Rebuilt the layout for phone and desktop."],
     "dec": ["Defined the product's purpose: a current view and a what-if view.",
             "Said 'make all those changes', accepting the recommendations as a set.",
             "Reported a desktop bug (header covering the title), which was then fixed."],
     "out": "Redesigned mobile and desktop UI"},
    {"title": "Go deeper on one person: employee drill-down",
     "me": "I want to click on the employees in the Up next section and see everything about that person, with BI tools "
           "to see each grant and when it vests, and a back button.",
     "ai": ["Designed a profile page: summary, per-grant timeline, vesting stack and progress charts, back navigation."],
     "dec": ["Specified the interaction I wanted from a user's point of view."],
     "out": "Employee profile page"},
    {"title": "Expand what-if to real equity programs",
     "me": "Enhance the what-if significantly: all performance-related payouts including SARs and phantom stock. "
           "Scenarios for termination, death, disability, canceling vesting for violations of non-competes. "
           "Add a rules editor, PSU payout per company, ESPP and restricted stock. The app should explain each type, "
           "payout and what-if so a user can learn as they go.",
     "ai": ["Modeled nine award types, eight events and five treatments, with value rules for each award type.",
            "Built a plan-rules editor with per-company overrides and a PSU payout per company.",
            "Wrote the in-app guide and a Learn section; added clawback and option-lapse exposure."],
     "dec": ["Decided rules should be editable and set per company, because real plans differ.",
             "Insisted the app teach as it goes.",
             "Asked probing questions (why pause? are dividends included? how do SARs settle in stock and cash?) and "
             "used the answers to decide what to build now and what to defer."],
     "out": "Nine award types, rules editor, guide"},
]

JUDGMENT = [
    ("Scope",
     "I set the goal (learn stock vesting by building a prototype end to end) and what to leave out. The AI proposed; I chose."),
    ("Assumptions over perfection",
     "Where the answer depends on the employer's internal facts, I chose to state an assumption and label it, instead of "
     "pretending to know."),
    ("Domain framing",
     "The pre-lapse idea (what do we need at L-4 so L-0 is only processing) came from my understanding of the work."),
    ("Rules are editable",
     "Real plan documents vary by company and country, so rules are defaults that I can override per company."),
    ("Deferred on purpose",
     "I asked about dividends and wanted to understand them first. I chose not to change the app until I decided it "
     "was worth it."),
    ("Teach the user",
     "I asked for explanations inside the app so a user learns what an award, payout or event means as they use it."),
    ("Test by using it",
     "I ran the app, found what was wrong (stale files, a header overlapping the title, missing tab) and reported it."),
]

LIMITS = [
    "All data is synthetic. No real employee, company or brokerage data was used.",
    "Default plan rules are typical practice chosen so the prototype behaves sensibly. They are not legal or tax advice, "
    "and a real implementation would load each company's plan documents.",
    "Research was done through AI-assisted web research. Anything that would drive a real decision needs checking "
    "against primary sources, such as plan documents, counsel and the brokerage's own specifications.",
    "I did not hold stakeholder conversations or run user tests. The product decisions came from my own reading of the problem, "
    "AI research and iterating on the working app.",
    "Pre-lapse readiness (an L-4 snapshot per person with ready / needs review / blocked status) is researched and "
    "designed but not built yet.",
    "Tax treatment is described in the guide but not calculated.",
]

WORKFLOW = [
    ("Ask the AI to explain before building", "Learn the domain first, then decide."),
    ("Put findings into a document", "Research lives in the PRD, not in chat history."),
    ("Make assumptions explicit", "Every gap I could not fill is written down as an assumption."),
    ("Build small, look, correct", "Each change was tried on the real app before the next."),
    ("Keep a human decision at every fork", "The AI proposed options; I picked and said why."),
]

ARTIFACTS = [
    ("PRD", "Product requirements, with brokerage research (Section 13) and assumptions (Section 14)."),
    ("Synthetic data generator", "Seeded, so every run produces the same global dataset."),
    ("Vesting engine", "Valuation by award type, rules, what-if actions and side effects."),
    ("Streamlit app", "Current schedule and what-if views, employee profile, rules editor, guide, reports."),
    ("Reports", "Excel and PDF built from the active filters."),
    ("Hosted app", "Deployed from GitHub so it can be opened from a link."),
]


def _step_html(i: int, s: dict) -> str:
    ai = "".join(f"<li>{hx(x)}</li>" for x in s["ai"])
    dec = "".join(f"<li>{hx(x)}</li>" for x in s["dec"])
    return (
        f'<div class="ai-step"><div class="ai-step-h"><span class="ai-num">{i}</span>'
        f'<span class="ai-step-t">{hx(s["title"])}</span></div>'
        f'<div class="ai-grid">'
        f'<div class="ai-col me"><h4>What I asked</h4><div class="ai-q">&ldquo;{hx(s["me"])}&rdquo;</div></div>'
        f'<div class="ai-col ai"><h4>What the AI did</h4><ul>{ai}</ul></div>'
        f'<div class="ai-col dec"><h4>What I decided</h4><ul>{dec}</ul></div></div>'
        f'<div class="ai-out">Output: <span class="ai-pill">{hx(s["out"])}</span></div></div>')


PRD_MD = Path(__file__).parent / "prd.md"


def _table_html(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{hx(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{hx(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="ai-tblwrap"><table class="ai-tbl"><tr>{th}</tr>{body}</table></div>'


# ---------------------------------------------------------------- PRD download
@st.cache_data(show_spinner=False)
def _prd_pdf(md_text: str) -> bytes:
    """Render the PRD markdown (headings, bullets, numbered lists, tables, bold, links) to a simple PDF."""
    import io
    import re

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
    cell = ParagraphStyle("c", parent=body, fontSize=8, leading=10)
    cellh = ParagraphStyle("ch", parent=cell, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=17, leading=21)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, leading=16, spaceBefore=10)

    def inline(t: str) -> str:
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\\*", "*")
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        return re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" color="#1d4ed8">\1</a>', t)

    flow, lines, i = [], md_text.split("\n"), 0
    width = letter[0] - 1.4 * inch
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln:
            i += 1
        elif ln.startswith("# "):
            flow.append(Paragraph(inline(ln[2:]), h1)); i += 1
        elif ln.startswith("## "):
            flow.append(Paragraph(inline(ln[3:]), h2)); i += 1
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            n = len(rows[0])
            lens = [max(8, min(60, max(len(r[j]) for r in rows if j < len(r)))) for j in range(n)]
            ws = [width * x / sum(lens) for x in lens]
            data = [[Paragraph(inline(c), cellh if r == 0 else cell) for c in row] + [""] * (n - len(row))
                    for r, row in enumerate(rows)]
            t = Table(data, colWidths=ws, repeatRows=1)
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.grey),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            flow += [t, Spacer(1, 6)]
        elif ln.startswith("- "):
            flow.append(Paragraph(inline(ln[2:]), body, bulletText="•")); i += 1
        elif re.match(r"\d+\. ", ln):
            num, rest = ln.split(". ", 1)
            flow.append(Paragraph(inline(rest), body, bulletText=f"{num}.")); i += 1
        else:
            flow.append(Paragraph(inline(ln), body)); i += 1
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=letter, leftMargin=.7 * inch, rightMargin=.7 * inch, topMargin=.7 * inch,
                      bottomMargin=.7 * inch, title="PRD: Global Equity Vesting Tracker").build(flow)
    return buf.getvalue()


def _prd_card() -> None:
    if not PRD_MD.exists():
        return
    md_text = PRD_MD.read_text(encoding="utf-8")
    st.markdown(
        '<div class="ai-dl"><b>The PRD</b><p>The product requirements document I wrote with the AI: problem, goals, '
        "data model, requirements, brokerage research (Section 13) and assumptions (Section 14). It is version 0.1, my "
        "starting point, so it still says RSUs only; the app has since grown to nine award types and an editable rules "
        "engine.</p></div>", unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 1.4])
    try:
        c1.download_button("Download PRD (PDF)", _prd_pdf(md_text), file_name="PRD_Equity_Vesting_Tracker.pdf",
                           mime="application/pdf", key="prd_pdf", use_container_width=True)
    except Exception:   # never let a PDF problem hide the markdown download
        pass
    c2.download_button("Download PRD (Markdown)", md_text, file_name="PRD_Equity_Vesting_Tracker.md",
                       mime="text/markdown", key="prd_md", use_container_width=True)


# ---------------------------------------------------------------- step outputs
# Left = what step 2 researched (PRD Section 13). Right = what the PRD lists as still to research or confirm
# (Sections 9 and 13).
MIND_DONE = [
    ("Who does what", ["Plan sponsor (the company)", "Platform / recordkeeper", "Broker", "Payroll, HR, Tax, Legal"]),
    ("Platforms", ["Morgan Stanley at Work (Shareworks, E*TRADE)", "Carta", "Fidelity Stock Plan Services",
                   "Others: Computershare, Schwab, Empower, Ledgy"]),
    ("Reports and the gap", ["Reports download as Excel or CSV", "Vendors offer scheduled, ad-hoc reports",
                             "Gap: cross-vendor reports with forecasts"]),
    ("Takeaways for the design", ["Start with file imports", "Track country by vesting period",
                                  "Flag, don't calculate, country tax rules"]),
]
MIND_TODO = [
    ("This company's setup", ["Which platform and broker?", "Public or private stock?",
                              "Who gets reports, and what hurts?"]),
    ("Vendor facts to verify", ["Shareworks: does an API exist?", "Carta: current API status",
                                "Fidelity: export formats, scheduling"]),
    ("Global rules", ["Tax timing by country", "Foreign plan filings and approvals", "Data privacy (GDPR and local)"]),
    ("Money and dates", ["FX rate source and timing", "Holiday and business-day rules", "Employees who move mid-vest"]),
]


def mindmap_html() -> str:
    def col(cls, title, data):
        side = "l" if cls == "l" else "r"
        out = [f'<div class="mm-col {cls}"><div class="mm-h">{hx(title)}</div>']
        for name, leaves in data:
            lv = '<div class="mm-leaves">' + "".join(f'<div class="mm-leaf">{hx(x)}</div>' for x in leaves) + "</div>"
            bn = f'<div class="mm-bn">{hx(name)}</div>'
            out.append(f'<div class="mm-b {side}">{lv + bn if side == "l" else bn + lv}</div>')
        return "".join(out) + "</div>"
    return ('<div class="mm">' + col("l", "Researched", MIND_DONE)
            + '<div class="mm-core">Stock plan vesting<small>research map</small></div>'
            + col("r", "Still to research", MIND_TODO) + "</div>")


def out_prd_outline() -> None:
    st.markdown(_table_html(
        ["Section", "What it holds"],
        [["1-4", "Problem, goals and non-goals, personas, prototype scope"],
         ["5", "Data requirements: employee, grant, tranche, market data"],
         ["6-8", "Functional requirements F1-F12 with priority, valuation approach, report contents"],
         ["9-11", "Global considerations, non-functional requirements, success metrics"],
         ["12", "Build plan in seven phases"],
         ["13-14", "Brokerage research and assumptions (added in the next two steps)"]]), unsafe_allow_html=True)


def out_mindmap() -> None:
    st.markdown(mindmap_html(), unsafe_allow_html=True)
    st.markdown(
        '<div class="ai-cap">Green: researched, written up in PRD Section 13. Amber (dashed): listed in the PRD as still '
        "to research or confirm (Sections 9 and 13). The research came from AI-assisted web search of vendor, "
        "review-site and job-posting pages in October 2026, so each vendor claim still needs checking with the "
        "vendor.</div>", unsafe_allow_html=True)


def out_assumptions() -> None:
    st.markdown(_table_html(
        ["Question", "Assumption I made", "What happened later"],
        [["Which award types?", "RSUs only in phase 1; award type stays a field",
          "Expanded to nine award types"],
         ["Which brokerage, what export?", "A generic broker with an Excel/CSV export, one row per grant",
          "Still an assumption; synthetic data mirrors that layout"],
         ["Internal or external audience?", "External clients: summary by country and month, detail for admins",
          "Reports built to that shape"],
         ["Reporting currency?", "USD with a local-currency column; keep original currency, FX rate and date",
          "Still an assumption"],
         ["Forfeiture, termination, acceleration?", "Unvested forfeits on termination; vests on death or disability",
          "Replaced by an editable rules engine, per company"],
         ["Stack?", "Python, pandas and Streamlit; Excel and PDF export", "Built and hosted"]]),
        unsafe_allow_html=True)
    st.markdown('<div class="ai-cap">From PRD Section 14. The last column shows how each assumption held up.</div>',
                unsafe_allow_html=True)


def out_grant_example() -> None:
    rows = [["Month 12 (cliff)", "1,200", "1,200"], ["Months 13 to 48 (36 monthly vests)", "100 each", "4,800"]]
    st.markdown(_table_html(["When", "Shares vesting", "Total vested after"], rows), unsafe_allow_html=True)
    st.markdown('<div class="ai-cap">Example of one grant (4,800 RSUs, 4 years, 1-year cliff, then monthly) becoming '
                "37 tranches. This is why Grant and Tranche are separate tables in the data model.</div>",
                unsafe_allow_html=True)


def out_data_facts() -> None:
    st.markdown(_table_html(
        ["Table", "What is in it"],
        [["Companies", "8 (the filter that lets one tool cover many clients)"],
         ["Employees", "980 across the globe"],
         ["Grants", "About 3,300, up to several per person"],
         ["Tranches", "About 48,000 dated vesting events"],
         ["Award types", "9, including cash-settled awards in India, Brazil, Poland and Japan"]]), unsafe_allow_html=True)
    st.markdown('<div class="ai-cap">Seeded generator: every run produces the same synthetic data.</div>',
                unsafe_allow_html=True)


def out_lapse_readiness() -> None:
    st.markdown(_table_html(
        ["Known at L-4 (rarely changes day to day)", "Only settles at L-0 (lapse day)"],
        [["Country of residence and tax residency", "Share price on the lapse date"],
         ["Mobility and work-location history", "FX rate on the lapse date"],
         ["Employment and leave status", "Final headcount: anyone who left in the last days"],
         ["Award type, schedule and settlement (shares or cash)", "Performance payout, once certified"],
         ["Plan rules that apply to the person", "Withholding amounts that depend on the price"]]),
        unsafe_allow_html=True)
    st.markdown('<div class="ai-cap">A working list to validate with someone who runs lapses today. The first two '
                "items on the left are from my own framing; the rest is a draft. Not built into the app yet.</div>",
                unsafe_allow_html=True)


def out_rules_defaults() -> None:
    cols = ["RSU", "Stock Option", "PSU", "ESPP"]
    rows = [[R.EVENTS[ev]] + [R.DEFAULT_TREATMENTS[ev][a] for a in cols] for ev in
            ("resign", "term_cause", "retire", "death", "disability", "leave")]
    st.markdown(_table_html(["Event"] + cols, rows), unsafe_allow_html=True)
    st.markdown('<div class="ai-cap">Default treatments in the app (a sample of 6 events and 4 award types). They are '
                "typical practice I chose so the prototype behaves sensibly, and each can be overridden per company.</div>",
                unsafe_allow_html=True)


def out_ship_chips(items: list[str]) -> None:
    st.markdown("".join(f'<span class="ai-pill">{hx(x)}</span>' for x in items), unsafe_allow_html=True)


# index (1-based step number) -> (expander label, expanded by default, renderer)
OUTPUTS = {
    1: ("Output: what the PRD contains", False, out_prd_outline),
    2: ("Output: research mind map", True, out_mindmap),
    3: ("Output: assumptions and how they held up", False, out_assumptions),
    4: ("Output: one grant becomes tranches", False, out_grant_example),
    5: ("Output: the synthetic dataset", False, out_data_facts),
    6: ("Output: what shipped", False, lambda: out_ship_chips(
        ["Current schedule view", "What-if view", "Company, country, department filters", "Export of filtered data",
         "Vesting by month chart", "Hosted on GitHub + Streamlit"])),
    7: ("Output: L-4 readiness, working draft", False, out_lapse_readiness),
    8: ("Output: what changed", False, lambda: out_ship_chips(
        ["Two clear views", "Cards on phones", "Filters popover", "Summary band", "Header fix on desktop"])),
    10: ("Output: default rules in the app", False, out_rules_defaults),
}


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="ai-hero"><h2>How I used AI for the product work</h2>'
        "<p>This page is separate from the vesting tool. It shows how I worked with AI on the product itself: "
        "teaching myself stock vesting, researching, writing the requirements, and deciding what to build. I did this "
        "to build my own knowledge and skills; the app is one result.</p>"
        "<p>Each step shows what I asked, what the AI did, and what I decided, with the output where there is one.</p>"
        "</div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="ai-stats">'
        f'<div class="ai-stat"><b>{len(STEPS)}</b><span>stages of product work</span></div>'
        '<div class="ai-stat"><b>1</b><span>PRD with research and assumptions</span></div>'
        '<div class="ai-stat"><b>9</b><span>award types modeled</span></div>'
        '<div class="ai-stat"><b>8</b><span>companies in the sample data</span></div></div>', unsafe_allow_html=True)
    _prd_card()

    t1, t2, t3, t4 = st.tabs(["The story", "My judgment calls", "Limits", "Artifacts and method"])
    with t1:
        for i, s in enumerate(STEPS, 1):
            st.markdown(_step_html(i, s), unsafe_allow_html=True)
            if i in OUTPUTS:
                label, opened, fn = OUTPUTS[i]
                with st.expander(label, expanded=opened):
                    fn()
    with t2:
        st.markdown("The AI did a lot of the drafting and research. These are the calls that were mine.")
        for h, t in JUDGMENT:
            with st.expander(h, expanded=False):
                st.write(t)
    with t3:
        st.markdown('<div class="ai-note">What this work is and is not. Being clear about this is part of using AI '
                    "well.</div>", unsafe_allow_html=True)
        for x in LIMITS:
            st.markdown("- " + x.replace("$", "\\$"))
    with t4:
        st.markdown("**What came out of it**")
        for h, t in ARTIFACTS:
            st.markdown(f"- **{h}.** {t}")
        st.markdown("**How I worked**")
        for h, t in WORKFLOW:
            st.markdown(f"- **{h}.** {t}")
