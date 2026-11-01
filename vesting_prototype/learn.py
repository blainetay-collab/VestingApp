"""Plain-English explanations shown in the app, so a new user can learn as they go.

General education only. Real treatment depends on each plan document, the grant agreement and local law
(tax, securities, employment). Nothing here is tax or legal advice.
"""

NOTE = ("General education, not tax or legal advice. What really happens depends on the plan document, the grant "
        "agreement and the law in each country.")

AWARDS = {
    "RSU": {
        "name": "Restricted Stock Unit (RSU)",
        "tagline": "A promise of shares, delivered when you have stayed long enough.",
        "what": "The company promises to deliver one share for each unit once the vesting conditions are met. "
                "Usually the condition is time, such as 25% a year for four years, often after a one-year cliff.",
        "pays": "Shares are delivered on the vest date. Many companies sell or withhold some of them to pay tax.",
        "value": "Units × share price on the vest date. The employee pays nothing to receive them.",
        "watch": ["In many countries the value of the shares is taxed as income when they vest.",
                  "Private companies often use 'double-trigger' RSUs that also need a sale or IPO.",
                  "This is the most common award, so it is the baseline for the other types."],
    },
    "PSU": {
        "name": "Performance Stock Unit (PSU)",
        "tagline": "Like an RSU, but how many shares you get depends on results.",
        "what": "A target number of units is granted. After a performance period (often 1 to 3 years) the company "
                "measures results against goals such as revenue, earnings or total shareholder return, and a "
                "payout percentage is set, commonly between 0% and 200% of target.",
        "pays": "Shares, after the compensation committee confirms the results. Target × payout % = shares earned.",
        "value": "Target units × payout % × share price on the vest date.",
        "watch": ["The payout is not known until the end, so this app lets you set an assumed payout per company.",
                  "Each grant has its own maximum payout (often 200%). The app never goes above it.",
                  "Treatment when someone leaves early varies a lot: forfeit, pro-rata on actual results, or at target."],
    },
    "Restricted Stock": {
        "name": "Restricted Stock Award (RSA)",
        "tagline": "Real shares issued on day one, but you can lose them until the restrictions lift.",
        "what": "The employee is issued actual shares at grant. The shares are 'restricted': the company can take "
                "them back if the person leaves before they vest. The employee may have voting and dividend rights.",
        "pays": "Nothing new is delivered at vest; the restriction simply lifts.",
        "value": "Shares × share price on the vest date (when the restriction lifts).",
        "watch": ["In the US, an '83(b) election' made within 30 days of the grant can move the tax to the grant date.",
                  "Without an election, tax is usually due when the restriction lifts, on the value then."],
    },
    "Stock Option": {
        "name": "Stock Option (ISO or NSO)",
        "tagline": "The right to buy shares at a fixed price. Only worth something if the price goes up.",
        "what": "The employee may buy shares at the 'strike price' set on the grant date. Vesting makes the options "
                "exercisable. They expire, often after 10 years, and usually only stay exercisable for a short time "
                "after someone leaves (commonly around 90 days).",
        "pays": "The employee chooses when to exercise and pays the strike price. The gain is the price above the strike.",
        "value": "Units × (share price − strike price), never below zero. This is the 'intrinsic value' if exercised "
                 "at that price. The app shows the gain, not the full share value.",
        "watch": ["'Underwater' means the price is at or below the strike, so there is no gain.",
                  "Incentive stock options (ISOs, US only) and non-qualified options (NSOs) are taxed differently.",
                  "Vested options that are not exercised in time can lapse, which is why exit windows matter."],
    },
    "SAR (stock-settled)": {
        "name": "Stock Appreciation Right, settled in shares",
        "tagline": "Paid the gain, in shares, with nothing to buy.",
        "what": "Works like an option but the employee never pays the strike. They receive the increase in value "
                "since the grant date.",
        "pays": "Shares worth the gain. If the gain is $1,000 and the price is $50, that is 20 shares.",
        "value": "Units × (share price − strike price), never below zero.",
        "watch": ["Same expiry and exit-window ideas as options.",
                  "Fewer shares are issued than with an option of the same size, which can help with dilution."],
    },
    "SAR (cash-settled)": {
        "name": "Stock Appreciation Right, settled in cash",
        "tagline": "The same gain, paid as cash through payroll.",
        "what": "Same economics as a stock-settled SAR, but the company pays cash. Often used where issuing shares "
                "to local employees is difficult because of securities or exchange-control rules.",
        "pays": "Cash through payroll, with local tax withheld.",
        "value": "Units × (share price − strike price), never below zero.",
        "watch": ["The company needs the cash on the payment date, so this adds to the 'paid in cash' total.",
                  "The cost moves with the share price until it is paid."],
    },
    "Phantom Stock": {
        "name": "Phantom Stock (cash-settled units)",
        "tagline": "Pretend shares that pay out like real ones, in cash.",
        "what": "Units track the share price but no shares are ever issued. Used by private companies and where "
                "share ownership is awkward. It may also pay amounts equal to dividends.",
        "pays": "Cash through payroll on the payment date.",
        "value": "Units × share price on the vest date.",
        "watch": ["Payment dates are often fixed in advance because of tax-timing rules (for example 409A in the US).",
                  "A cash-settled RSU is essentially the same thing."],
    },
    "Performance Cash": {
        "name": "Performance Cash (long-term incentive)",
        "tagline": "A cash bonus earned over several years if goals are met.",
        "what": "A target dollar amount is set. After the performance period, results decide the payout percentage "
                "(for example 0% to 150% of target). It does not depend on the share price unless the plan adds that.",
        "pays": "Cash through payroll.",
        "value": "Target dollars × payout %. In this app the 'units' for this award are US dollars, not shares.",
        "watch": ["Share counts in the app leave these out, because dollars are not shares.",
                  "Set the assumed payout per company, the same way as for PSUs."],
    },
    "ESPP": {
        "name": "Employee Stock Purchase Plan (ESPP)",
        "tagline": "Employees buy shares through payroll, at a discount.",
        "what": "Employees put aside part of their pay during an offering period (here, six months). On the purchase "
                "date the savings buy shares at a discount, commonly 15%. Many plans use a 'lookback': the discount "
                "applies to the lower of the price at the start of the period or on the purchase date.",
        "pays": "Shares bought on the purchase date. There is no 'vesting', just a purchase.",
        "value": "Shares bought × market price. The number of shares is contribution ÷ discounted purchase price, "
                 "so it rises when the price falls. The value includes the employee's own money.",
        "watch": ["In US qualified plans, the discount is capped at 15% and purchases at $25,000 of value a year.",
                  "When someone leaves, participation ends and the savings are normally refunded."],
    },
}

EVENTS = {
    "resign": {
        "what": "The employee chooses to leave.",
        "typical": "Unvested awards are forfeited. Vested options and SARs usually stay exercisable for a short window "
                   "(often 90 days), then lapse. ESPP participation ends and savings are refunded.",
        "matters": "This is the most common departure, so it drives how much unvested value never gets delivered.",
    },
    "term_no_cause": {
        "what": "The company ends employment without any misconduct, for example in a layoff or restructuring.",
        "typical": "Often the same as resignation. Some companies or severance deals add partial acceleration. In many "
                   "countries a notice period applies and vesting can continue until it ends.",
        "matters": "Large layoffs can move a lot of value at once, and local notice rules can change the exact date.",
    },
    "term_cause": {
        "what": "The company ends employment for serious misconduct as defined in the plan or contract.",
        "typical": "Unvested awards are forfeited. Many plans also cancel vested options that were not yet exercised "
                   "and may allow the company to recover recent gains.",
        "matters": "'Cause' has a specific legal definition, so someone in HR or legal decides if it applies.",
    },
    "retire": {
        "what": "The employee retires and meets the plan's age and service rules (for example age plus years of "
                "service of 70 or more).",
        "typical": "Time-based awards often keep vesting on the original schedule. Performance awards are usually "
                   "paid pro-rata on actual results after the period ends.",
        "matters": "Retirement can leave unvested value outstanding for years, so it still counts in forecasts.",
    },
    "death": {
        "what": "The employee dies.",
        "typical": "Plans often accelerate vesting in full. Performance awards may pay at target or on actual results. "
                   "The estate normally gets a longer window, often a year, to exercise options.",
        "matters": "Vesting is brought forward to the date of death, which changes cash and tax timing.",
    },
    "disability": {
        "what": "The employee leaves because of a qualifying long-term disability, as defined in the plan.",
        "typical": "Practice varies: full acceleration, continued vesting while disabled, or pro-rata for performance awards.",
        "matters": "The plan's definition of disability decides whether this applies at all.",
    },
    "violation": {
        "what": "The employee breaks a restrictive covenant such as a non-compete, non-solicit or confidentiality duty.",
        "typical": "Plans may cancel unvested awards and allow a 'clawback': recovering shares or proceeds that were "
                   "delivered within a lookback period (often 12 months or more).",
        "matters": "Whether non-competes can be enforced varies widely by country and US state. The app shows the "
                   "amount at risk, not what would actually be recovered, because collecting it is a legal question.",
    },
    "leave": {
        "what": "The employee takes an approved leave of absence, such as parental or medical leave.",
        "typical": "Surveys of US companies found most do not adjust vesting for statutory or paid leave, but some "
                   "pause or extend vesting for long unpaid leave. Local law can require vesting to continue.",
        "matters": "Pausing pushes vests later, so value moves out of the window even though nobody has left.",
    },
}

TREATMENTS = {
    "Forfeit": "Unvested awards are cancelled. The value never reaches the employee.",
    "Accelerate in full": "All remaining unvested awards vest on the event date. Performance awards pay at target.",
    "Pro-rata": "Only the part earned so far vests: grant size × share of the vesting period served − what has already "
                "vested. Time-based awards pay on the event date. Performance awards pay on their original date at the "
                "company's assumed payout.",
    "Continue vesting": "Nothing changes. The awards keep vesting on their original schedule.",
    "Pause vesting": "Remaining vests move later by the number of months of the leave.",
}

GLOSSARY = {
    "Grant vs vesting event": "A grant is the award as a whole. Each date it pays out is a vesting event (also called a "
                              "tranche). One grant has many events.",
    "Vest / lapse / L-0": "The day the restriction ends and the award pays out. Equity teams also call it the lapse date, "
                          "and 'L-4' means four days before.",
    "Settlement": "How the award is delivered: in shares or in cash. Cash awards need payroll funding on the payment date.",
    "Cliff": "A waiting period before anything vests. A one-year cliff means nothing vests in the first year, then a "
             "block vests on the first anniversary.",
    "Strike price": "The fixed price on an option or SAR. Only the part of the share price above it has value.",
    "Intrinsic value": "What an option or SAR is worth right now if exercised: price minus strike, never below zero.",
    "Underwater": "An option or SAR whose strike is at or above the share price, so it has no gain.",
    "Target vs actual payout": "For performance awards, the target is the number granted. The payout percentage turns "
                               "it into what is actually earned.",
    "Exercise window": "How long vested options and SARs stay usable after someone leaves. After that they lapse.",
    "Lookback (ESPP)": "The purchase price uses the lower of the start-of-period price and the purchase-date price.",
    "Clawback": "A plan term letting the company recover shares or proceeds already delivered, for example after a violation.",
    "Gross vs net shares": "Gross is before tax withholding. Net is what the employee keeps after shares are sold or "
                           "withheld to cover tax. This app shows gross.",
    "Expected value (attrition)": "Instead of guessing who leaves, each unvested vest is scaled by the chance the person "
                                  "is still employed that day. Results can be fractional shares.",
}

HOW_NUMBERS_WORK = [
    ("Share price on each vest date",
     "Starts from today's price. 'Flat' keeps it there, 'Growth' compounds it at an annual rate, and 'Range' adds a "
     "bear and bull case using volatility. A 'share price change' moves today's price first."),
    ("Value of each vest",
     "Depends on the award type (see the Award types guide): shares × price, or the gain over the strike for options "
     "and SARs, or dollars × payout % for performance cash."),
    ("Performance payout",
     "Applies only to PSUs and performance cash, as a percentage of target set per company, capped at each grant's maximum."),
    ("Attrition",
     "Scales unvested vests by the chance the person is still employed. It assumes leavers forfeit what is unvested."),
    ("People events",
     "Apply the plan rules for the person's company to each unvested vest. The rules table shows exactly what happens."),
    ("The 'What changed' chart",
     "Applies one change at a time, in this order: people events, attrition, performance payout, share price change, "
     "price path. A different order would split the effect a little differently, but the start and end always match."),
]

# One-line summary per award type, for the side-by-side comparison table.
SUMMARY = {
    "RSU": ("Shares", "Units × share price", "No", "No"),
    "PSU": ("Shares", "Target × payout % × share price", "Yes", "No"),
    "Restricted Stock": ("Shares", "Shares × share price at restriction lift", "No", "No"),
    "Stock Option": ("Shares (employee buys)", "Units × (price − strike), min 0", "No", "Yes"),
    "SAR (stock-settled)": ("Shares", "Units × (price − strike), min 0", "No", "Yes"),
    "SAR (cash-settled)": ("Cash", "Units × (price − strike), min 0", "No", "Yes"),
    "Phantom Stock": ("Cash", "Units × share price", "No", "No"),
    "Performance Cash": ("Cash", "Target dollars × payout %", "Yes", "No"),
    "ESPP": ("Shares (employee buys)", "Shares bought × market price", "No", "No"),
}
