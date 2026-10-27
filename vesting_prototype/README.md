# Equity Vesting Tracker (prototype)

Reads RSU grant data for many companies, finds every upcoming vesting event, values it at each vest
date, charts vesting by month, and produces client-ready Excel / PDF reports. All data is synthetic.

## Run it
    pip install -r requirements.txt
    streamlit run app.py
(On Windows: `py -m pip install -r requirements.txt` then `py -m streamlit run app.py`)

## Two views
- **Current schedule**: what is scheduled to vest, valued at today's share prices.
- **What-if**: change things and compare against the current schedule. Levers:
  - Prices: a price path (flat / growth / bear-base-bull range) and a one-off change to today's prices.
  - Attrition: an assumed annual rate, applied as an expected value to unvested shares.
  - People events: leaves (shares forfeit or accelerate) and leave of absence (vesting paused for N months),
    for specific employees or everyone matching the filters.
  - One-click presets: market down 20%, market up 20%, 15% attrition.
  Summary cards show the change against current, and the BI chart plots both lines.

## Layout
Filters sit in the page (not a sidebar), so they are visible on a phone. Every tab and every
export follows them. Tabs: BI, Events, Breakdown, People, Report, Data.

## Files
    app.py             Streamlit screen
    engine.py          vesting + price logic, what-if levers, validation, summaries, monthly series (no UI code)
    reports.py         Excel and PDF report builders, filtered data export
    generate_data.py   regenerates the synthetic dataset (fixed seed); edit COMPANIES to resize it
    data/              companies, employees, grants, vesting_tranches, vesting_schedules,
                       market_data, price_history, fx_rates (CSV)

## Dataset
8 fictional companies, ~980 employees in 14 countries, ~3,100 grants, ~52,000 vesting tranches.

## Assumptions
- RSUs only; reporting currency USD with a local-currency column. Share counts are gross, before tax withholding.
- Price scenarios and attrition are illustrative, not predictions.
- Pausing vesting during leave is a what-if. Whether a real plan pauses vesting varies by plan and country.
- Reports exported from the What-if view are labeled as hypothetical.

## Swapping in a real export
engine.load_data() is the only place that reads files. Replace it (or add an adapter) to map a
brokerage export onto the same column names.

## Data folder is optional
If `data/` is missing (for example when uploading from a phone, where folders can't be created), the app
looks for the CSVs next to app.py, and otherwise generates the same demo data on first load.
Only app.py, engine.py, reports.py, generate_data.py and requirements.txt are required.

## Publishing
Push this folder to a public GitHub repo, then deploy at share.streamlit.io with app.py as the main file.


## Look and feel

The accent color, font and rounded corners come from `.streamlit/config.toml`. Charts are defined in `charts.py` and drawn with Streamlit's built-in Vega-Lite support, so no extra packages are needed. The layout works on phones and desktops, and follows the device's light or dark setting.
