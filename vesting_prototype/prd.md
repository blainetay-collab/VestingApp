# PRD: Global Equity Vesting Tracker & Reporting (Prototype)

Status: Draft v0.1 | Purpose: Replace a manual stock plan administration process with a data-driven tool that forecasts vesting events and generates client-ready reports.

## 1. Problem Statement

Stock plan administration is currently manual. Grant data lives in spreadsheets and brokerage exports, vesting dates are tracked by hand, and reports for clients are assembled one at a time. This is slow and error-prone, and it does not scale across a global workforce where each employee may hold several grants with different vesting schedules and different local rules.

## 2. Goals and Non-Goals

**Goals**

- Establish a single, structured source of truth for employee equity data.
- Automatically calculate every upcoming vesting event for every employee.
- Estimate the market value of each event at its vest date using transparent, adjustable assumptions.
- Generate consistent, client-ready reports with one click.
- Support employees across many countries, with country-aware data from day one.

**Non-Goals (for the prototype)**

- Executing trades, sales, or share transfers.
- Calculating final tax withholding or filing obligations.
- Live brokerage integration (design for it, mock it in the prototype).
- Providing investment advice or a true price forecast.

## 3. Users and Personas

- **Equity Administrator (primary):** runs the tool, reviews upcoming events, generates and sends reports.
- **Client / Stakeholder (report recipient):** HR, Finance, or the company that needs visibility into upcoming vesting and its estimated value.
- **Finance / Payroll (secondary):** uses the event list to plan for withholding, cash needs, and expense recognition.

## 4. Scope of the Prototype

1. **Data layer:** a structured dataset of employees, grants, and vesting tranches.
2. **Vesting engine:** expands each grant into dated vesting events.
3. **Valuation estimator:** projects stock price at each vest date under selectable scenarios.
4. **Reporting:** a filterable upcoming-events view plus exportable reports (PDF and Excel/CSV).

## 5. Data Requirements

**Employee**

- Employee ID, name, email (synthetic data in the prototype)
- Country of residence, tax residency country
- Local currency, hire date, employment status

**Grant** (an employee can have many)

- Grant ID, employee ID, grant date
- Award type: RSU, stock option, ESPP, other
- Total shares, strike price (for options), currency
- Vesting schedule template (for example 4 years with a 1-year cliff, then monthly or quarterly)

**Vesting Tranche / Event** (a grant produces many)

- Tranche ID, grant ID, vest date, shares vesting
- Status: unvested, vested, forfeited, accelerated

**Market Data**

- Ticker, current price, price date, currency
- FX rates for converting to local and reporting currency

**Key modeling point:** keep Grant and Tranche as separate tables. One person with three grants on different schedules is the normal case, not the exception.

## 6. Functional Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| F1 | Load employee and grant data from CSV/Excel or a database | Must |
| F2 | Validate data (missing country, share totals not matching tranches, invalid dates) and surface errors | Must |
| F3 | Generate vesting events from schedule templates (cliff, monthly, quarterly, annual, custom) | Must |
| F4 | List all upcoming vesting events within a selectable window (30, 90, 180, 365 days) | Must |
| F5 | Filter and group by country, employee, grant, month, award type | Must |
| F6 | Estimate price at each vest date under scenarios: flat, growth rate, bear/base/bull | Must |
| F7 | Show estimated value in USD and local currency with stated FX assumptions | Should |
| F8 | Export a client-ready report (PDF and Excel) with summary totals and event detail | Must |
| F9 | Flag country-specific considerations on events (for example tax or regulatory review needed) | Should |
| F10 | Audit trail: record which data version, assumptions, and date produced each report | Should |
| F11 | Scheduled report generation and email delivery | Could |
| F12 | Brokerage API/file integration for live grant and price data | Future |

## 7. Valuation Approach

The estimated price is an **illustrative projection, not a prediction**. The tool should say so on every report.

- **Flat:** current price held constant (default, most defensible).
- **Growth:** apply an annual growth rate, compounded to each vest date.
- **Range:** bear / base / bull scenarios, optionally from a simple volatility model.
- Assumptions (price date, rate, FX) are printed on the report and editable by the administrator.

## 8. Reporting Requirements

Each report should contain:

- Header: company, report date, data as-of date, scenario used
- Summary: total shares vesting and total estimated value in the window, by month and by country
- Detail table: employee, country, grant, vest date, shares, estimated price, estimated value
- Assumptions and disclaimer section
- Optional: one report per client or per country

## 9. Global Considerations (to research)

These drive data fields and flags, even though the prototype will not compute final tax.

- Tax treatment of RSUs and options varies by country (timing of taxable event, social charges, withholding at vest).
- Some countries restrict foreign share plans or require securities filings, exemptions, or approved plan documents.
- Data privacy rules (GDPR and local equivalents) apply to employee data; the prototype should use synthetic data only.
- Multi-currency reporting and FX rate sourcing and timing.
- Local holiday and business-day conventions for vest dates.
- Cross-border moves, where an employee changes country mid-vesting, require tracking country history per period.

## 10. Non-Functional Requirements

- Accuracy: vesting calculations must be reproducible and testable against known examples.
- Transparency: every number traceable to a grant, a schedule, and an assumption.
- Security: role-based access in production; synthetic data only in the prototype.
- Scalability: handle thousands of employees and tens of thousands of tranches.
- Maintainability: schedule templates configurable without code changes.

## 11. Success Metrics

- Time to produce a full upcoming-events report: from hours or days to under one minute.
- Zero calculation discrepancies against a manually verified sample.
- Report generated for 100% of countries in the dataset.
- Qualitative: stakeholder feedback on clarity of the report.

## 12. Prototype Build Plan

| Phase | Deliverable |
| --- | --- |
| 1 | PRD and data model finalized |
| 2 | Synthetic dataset: about 50 to 100 employees across 10 to 15 countries, 1 to 4 grants each |
| 3 | Vesting engine and validation checks |
| 4 | Valuation scenarios and FX handling |
| 5 | Dashboard / upcoming events view |
| 6 | PDF and Excel report export |
| 7 | Walkthrough: manual process vs. new process |

## 13. Brokerage Landscape (to research)

The prototype fits in the reporting gap between vendors: platforms hold the grant records, but cross-vendor, forecast-driven client reports are still built by hand in Excel. Findings below are from desktop research in October 2026 and come from vendor, review-site and job-posting search results, so verify each against the vendor before relying on it.

**Who does what in stock plan administration**

- **Plan sponsor (the company):** designs the plan and awards grants.
- **Platform / recordkeeper:** holds the official grant and vesting records and produces reports (Shareworks, Carta, Fidelity).
- **Broker:** holds participant accounts for selling, sell-to-cover and exercises (for example E\*TRADE).
- **Payroll, HR, Tax, Legal:** supply employee data and handle withholding and compliance. A [public equity plan administrator job posting](https://jobicy.com/jobs/155278-equity-plan-administrator.md) lists advanced Excel and data reconciliation as core skills, which matches the manual process described in this PRD.

**Platform comparison**

| Platform | Positioning | Reporting and export | To verify |
| --- | --- | --- | --- |
| [Morgan Stanley at Work (Shareworks, E\*TRADE)](https://morganstanley.com/atwork/financial-reporting-solutions) | Private and public companies; Shareworks, StockPlan Connect and E\*TRADE stock plan accounts are being rebranded under one name | ASC 718 and IFRS reporting, expense modeling, forecasting scenarios ([GetApp](https://www.getapp.com/equity-management-software/a/shareworks)) | Whether an API exists; one review site says no, unconfirmed |
| [Carta](https://www.getapp.co.nz/software/117139/carta) | Strongest in private and growth-stage companies; also an SEC-acknowledged transfer agent for public companies | Option vesting and grant overview reports in Excel ([Carta Europe](https://support.europe.carta.com/hc/en-gb/articles/26292011466257-Option-Grant-Reports-Overview)); custom Excel reports ([Carta](https://carta.com/product-updates/custom-reports-cap-table-plugin/)) | Current API status; it was a [beta in 2023](https://www.charthop.com/resource/announcing-charthops-partnership-with-carta) |
| [Fidelity Stock Plan Services](https://www.globalequity.org/events/pere-2026/sponsors) | About 860 clients and 2.8 million participants; full to partial outsourcing | Plan Sponsor Workstation reporting ([job listing](https://www.themuse.com/jobs/fidelityinvestments/financial-reporting-manager-stock-plan-services)); [mobility tracking](https://www.plansponsor.com/?p=15794) | Export formats and scheduling |
| Others | Computershare, Schwab, Empower (formerly OptionTrax), Ledgy | Ledgy has a [vesting tranches report by work location](https://help.ledgy.com/en/articles/129465-operational-reports) | Which are in use at the target company |

**Implications for the prototype**

- **Start with file imports:** vesting reports are commonly downloaded as Excel or CSV, so the data layer should accept those first and treat APIs as a later phase.
- **Track country history per vesting period:** global mobility is a recognized pain point; Fidelity and Ledgy both report vesting by work location.
- **Position as a unifying layer:** vendors already offer scheduled and ad-hoc reports; the gap is combining vendors and countries with forecasts and client-ready formatting.
- **Flag, don't calculate, country rules:** Fidelity publishes a [global tax guide](https://www.plansponsor.com/fidelity-introduces-global-stock-plan-solution/) covering more than 30 countries, so the tool should point to experts rather than replace them.

**Still to confirm with the plan administrator**

- Which platform and broker the company uses, and what it can export
- Whether the stock is public or private
- Who receives the reports and what they complain about today

## 14. Open Questions

The company's real answers are unknown, so the prototype proceeds on the assumptions below; each is easy to change once the real details are known.

| Question | Prototype assumption | Basis |
| --- | --- | --- |
| Which award types are in scope? | RSUs only in phase 1; award type stays a field so options and ESPP can be added later | RSUs are the most common award at public companies |
| Which brokerage, and what export formats? | A generic broker providing an Excel/CSV export with one row per grant and its schedule fields; synthetic data mirrors that layout; vendor adapters come later | Vesting reports are commonly Excel or CSV downloads |
| Internal or external report audience? | External clients: a summary by country and month, plus a detailed view for administrators | Original brief says reports are sent to clients |
| What reporting currency? | USD, with a local-currency column; each estimate stores the original currency, FX rate and rate date | Stock assumed to trade in USD |
| How are forfeitures, terminations and acceleration handled? | Each grant has a status (active, forfeited, accelerated); unvested shares forfeit on termination and fully vest on death or disability; change in control is out of scope for phase 1 | Common terms in RSU agreements |
| What is the prototype stack? | Python with pandas and Streamlit, exporting Excel and PDF | Fastest path to a working prototype |
