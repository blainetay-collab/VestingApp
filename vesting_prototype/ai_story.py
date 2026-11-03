"""'How I used AI for the product work' - a self-contained section, separate from the vesting tool.

It imports nothing from the engine, so it cannot affect the vesting numbers. The content is a record of how the
product work actually went: what was asked, what the AI did, and what the human decided. Edit the lists below to
keep it accurate; nothing here is computed.
"""
from __future__ import annotations

import html as _html

import streamlit as st

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
</style>"""


def hx(t) -> str:
    return _html.escape(str(t)).replace("$", "&#36;")


# Each step: title, my prompt (lightly cleaned up from what I actually typed), what the AI did,
# what I decided or contributed, and what came out of it.
STEPS = [
    {"title": "Frame the problem and write the PRD",
     "me": "I'm applying for a job helping build a new stock plan process. Today it is very manual. I want to build a "
           "prototype start to finish to show I want the job. First a PRD. Start with a source of data: employees "
           "across countries, their unvested stock, and when each segment vests. Then list upcoming vesting events "
           "with a predicted market value, and produce reports for clients.",
     "ai": ["Turned a loose idea into a structured PRD: problem, users, scope, data model, functional requirements, "
            "open questions.",
            "Split the work into stages (data, engine, reports) so each could be built and checked on its own."],
     "dec": ["Chose the end-to-end goal and the audience for the demo (the interviewers).",
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
     "dec": ["The L-4 / L-0 framing came from my own understanding of the job, not from the AI.",
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
     "I set the goal (a prototype that shows I want the job), the audience and what to leave out. The AI proposed; I chose."),
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
    "Default plan rules are typical practice chosen so the demo behaves sensibly. They are not legal or tax advice, "
    "and a real implementation would load each company's plan documents.",
    "Research was done through AI-assisted web research. Anything that would drive a real decision needs checking "
    "against primary sources, such as plan documents, counsel and the brokerage's own specifications.",
    "I did not interview stakeholders or run user tests. The product decisions came from my own reading of the problem, "
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


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="ai-hero"><h2>How I used AI for the product work</h2>'
        "<p>This page is separate from the vesting tool. It shows how I worked with AI on the product itself: "
        "learning the domain, researching, writing the requirements, and deciding what to build. The app is one result.</p>"
        "<p>Each step shows what I asked, what the AI did, and what I decided.</p></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="ai-stats">'
        f'<div class="ai-stat"><b>{len(STEPS)}</b><span>stages of product work</span></div>'
        '<div class="ai-stat"><b>1</b><span>PRD with research and assumptions</span></div>'
        '<div class="ai-stat"><b>9</b><span>award types modeled</span></div>'
        '<div class="ai-stat"><b>8</b><span>companies in the demo data</span></div></div>', unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["The story", "My judgment calls", "Limits", "Artifacts and method"])
    with t1:
        for i, s in enumerate(STEPS, 1):
            st.markdown(_step_html(i, s), unsafe_allow_html=True)
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
