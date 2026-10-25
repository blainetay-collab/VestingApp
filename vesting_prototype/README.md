# Equity Vesting Tracker (prototype)

Reads RSU grant data for many companies, finds every upcoming vesting event, estimates the
share price and value at each vest date, charts vesting by month, and produces client-ready
Excel / PDF reports. All data is synthetic.

## Run it
    pip install -r requirements.txt
    streamlit run app.py
(On Windows: `py -m pip install -r requirements.txt` then `py -m streamlit run app.py`)

## What's in the app
- Sidebar filters: company, country, department, employee name/ID. Every tab and every export follows them.
- Events: filtered event table with Export CSV / Export Excel (matches the active filters).
- BI: line chart of shares or estimated value vesting per month (12-48 months), split by
  company / country / department, optional cumulative view.
- Summary, By employee, Data quality, What-if (termination / acceleration), Report (Excel + PDF).

## Files
    app.py             Streamlit screen
    engine.py          vesting + price-scenario logic, validation, summaries, monthly series (no UI code)
    reports.py         Excel and PDF report builders, filtered data export
    generate_data.py   regenerates the synthetic dataset (fixed seed); edit COMPANIES to resize it
    data/              companies, employees, grants, vesting_tranches, vesting_schedules,
                       market_data, price_history, fx_rates (CSV)

## Dataset
8 fictional companies, ~980 employees in 14 countries, ~3,100 grants, ~52,000 vesting tranches.

## Assumptions (from the PRD)
- RSUs only; reporting currency USD with a local-currency column.
- Unvested shares forfeit on termination; death / disability can accelerate (What-if tab).
- Price scenarios are illustrative: Flat, Growth, or Range (growth path +/- one standard deviation
  of annual volatility), using each company's own assumptions unless overridden. Not predictions.
- Share counts are gross, before tax withholding.

## Swapping in a real export
engine.load_data() is the only place that reads files. Replace it (or add an adapter) to map a
brokerage export onto the same column names.

## Publishing
Push this folder to a public GitHub repo, then deploy at share.streamlit.io with app.py as the main file.
