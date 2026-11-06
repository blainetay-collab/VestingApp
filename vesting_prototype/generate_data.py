"""Generate a synthetic multi-company global equity dataset (9 award types) for the vesting-tracker prototype.

All companies, people, emails, prices and FX rates are fictional / illustrative.
Run:  python generate_data.py     (writes CSVs into ./data, or into $VESTING_DATA_DIR if set)
Edit COMPANIES below (the employee count column) to make the dataset bigger or smaller.
"""
import os
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dateutil.relativedelta import relativedelta

SEED = 42
AS_OF = date(2026, 11, 6)
OUT = Path(os.environ.get("VESTING_DATA_DIR") or Path(__file__).parent / "data")
OUT.mkdir(exist_ok=True)
random.seed(SEED)

# company_id, name, ticker, industry, hq_code, employees, price_usd, volatility, growth
COMPANIES = [
    ("C001", "Acme Global Inc.", "ACME", "Technology", "US", 180, 86.15, 0.35, 0.08),
    ("C002", "Northwind Robotics", "NWRB", "Industrial Tech", "DE", 150, 39.85, 0.42, 0.10),
    ("C003", "Helios Energy", "HLOS", "Energy", "GB", 140, 23.40, 0.38, 0.05),
    ("C004", "Bluepeak Software", "BPKS", "Software", "US", 130, 162.10, 0.45, 0.12),
    ("C005", "Meridian Health", "MRDH", "Healthcare", "CA", 110, 64.75, 0.28, 0.07),
    ("C006", "Orbit Logistics", "ORBT", "Logistics", "SG", 100, 18.35, 0.33, 0.06),
    ("C007", "Cobalt Financial", "CBFT", "Financial Services", "IE", 90, 114.20, 0.25, 0.06),
    ("C008", "Verdant Foods", "VRDF", "Consumer", "AU", 80, 37.90, 0.22, 0.04),
]

# country, code, currency, FX (units per 1 USD, illustrative), base weight
COUNTRIES = [
    ("United States", "US", "USD", 1.00, 14), ("United Kingdom", "GB", "GBP", 0.78, 7),
    ("Germany", "DE", "EUR", 0.91, 6), ("France", "FR", "EUR", 0.91, 4),
    ("Ireland", "IE", "EUR", 0.91, 3), ("Netherlands", "NL", "EUR", 0.91, 3),
    ("Canada", "CA", "CAD", 1.39, 5), ("India", "IN", "INR", 84.10, 6),
    ("Singapore", "SG", "SGD", 1.33, 3), ("Australia", "AU", "AUD", 1.53, 3),
    ("Japan", "JP", "JPY", 152.40, 3), ("Brazil", "BR", "BRL", 5.12, 3),
    ("Israel", "IL", "ILS", 3.64, 3), ("Poland", "PL", "PLN", 4.05, 2),
]
NAMES = {
    "US": (["James", "Maria", "Chris", "Aisha", "Daniel", "Emily", "Marcus", "Hannah"], ["Carter", "Nguyen", "Brooks", "Hughes", "Patel", "Reed", "Foster", "Gray"]),
    "GB": (["Oliver", "Amelia", "Harry", "Priya", "George", "Chloe", "Freddie", "Poppy"], ["Wright", "Khan", "Taylor", "Evans", "Hall", "Walker", "Cooper", "Ward"]),
    "DE": (["Lukas", "Anna", "Felix", "Lena", "Jonas", "Mia", "Paul", "Clara"], ["Schmidt", "Weber", "Fischer", "Becker", "Koch", "Wolf", "Richter", "Klein"]),
    "FR": (["Hugo", "Camille", "Louis", "Manon", "Jules", "Chloé", "Arthur", "Léa"], ["Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Roux", "Petit", "Girard"]),
    "IE": (["Cian", "Aoife", "Conor", "Niamh", "Sean", "Orla", "Darragh", "Saoirse"], ["Murphy", "Kelly", "O'Brien", "Walsh", "Byrne", "Ryan", "Doyle", "Quinn"]),
    "NL": (["Daan", "Sanne", "Bram", "Eva", "Thijs", "Lotte", "Finn", "Noor"], ["de Vries", "Jansen", "Bakker", "Visser", "Smit", "Mulder", "Dekker", "Brouwer"]),
    "CA": (["Liam", "Emma", "Noah", "Sophie", "Ethan", "Chloe", "Logan", "Ava"], ["Tremblay", "Roy", "Campbell", "Singh", "MacDonald", "Gagnon", "Bouchard", "Morin"]),
    "IN": (["Arjun", "Ananya", "Rohan", "Diya", "Vikram", "Sneha", "Kabir", "Meera"], ["Sharma", "Iyer", "Reddy", "Gupta", "Nair", "Mehta", "Kapoor", "Joshi"]),
    "SG": (["Wei", "Mei", "Jun", "Hui", "Kai", "Li", "Jia", "Zhi"], ["Tan", "Lim", "Ng", "Goh", "Chua", "Ong", "Teo", "Koh"]),
    "AU": (["Jack", "Isla", "Lachlan", "Ruby", "Mitchell", "Zoe", "Hunter", "Matilda"], ["Smith", "Jones", "Nguyen", "Brown", "Wilson", "Clarke", "Murray", "Hayes"]),
    "JP": (["Haruto", "Yui", "Ren", "Sakura", "Takumi", "Aoi", "Sota", "Hina"], ["Sato", "Suzuki", "Takahashi", "Tanaka", "Ito", "Watanabe", "Kobayashi", "Yamada"]),
    "BR": (["Pedro", "Beatriz", "Lucas", "Larissa", "Gabriel", "Julia", "Mateus", "Livia"], ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira", "Rocha"]),
    "IL": (["Noam", "Maya", "Eitan", "Tamar", "Yoav", "Shira", "Itai", "Noa"], ["Cohen", "Levi", "Mizrahi", "Peretz", "Katz", "Friedman", "Avraham", "Dahan"]),
    "PL": (["Jakub", "Zofia", "Mateusz", "Julia", "Piotr", "Anna", "Kacper", "Maja"], ["Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski", "Zieliński", "Szymański"]),
}
DEPARTMENTS = ["Engineering", "Sales", "Product", "Finance", "Marketing", "Operations", "Legal", "People"]

SCHEDULES = [
    ("4Y_1Y_CLIFF_QTR", "4 years, 1-year cliff, then quarterly", 48, 12, 3),
    ("4Y_1Y_CLIFF_MONTHLY", "4 years, 1-year cliff, then monthly", 48, 12, 1),
    ("3Y_1Y_CLIFF_ANNUAL", "3 years, 1-year cliff, then annually", 36, 12, 12),
    ("4Y_ANNUAL", "4 years, annual vesting (25% per year)", 48, 12, 12),
    ("3Y_CLIFF_PERF", "3-year performance period, pays once at the end", 36, 36, 36),
    ("ESPP_6M", "ESPP: a purchase every 6 months", 24, 6, 6),
]
SCHED = {s[0]: s for s in SCHEDULES}
SIZES = [200, 400, 600, 800, 1000, 1200, 1600, 2000, 2400, 3200, 4000]
TIME_SCHEDULES = [x[0] for x in SCHEDULES[:4]]
CASH_COUNTRIES = {"IN", "BR", "PL", "JP"}          # share issuance is hard here, so cash-settled awards are common
ESPP_COUNTRIES = {"US", "GB", "IE", "DE", "FR", "NL", "CA", "SG", "AU", "JP"}
CASH_AWARDS = {"SAR (cash-settled)", "Phantom Stock", "Performance Cash"}
OPTION_LIKE = {"Stock Option", "SAR (stock-settled)", "SAR (cash-settled)"}
PERF_METRICS = ["Relative TSR", "Revenue growth", "EBITDA margin", "Earnings per share"]


def pick_award(code):
    if code in CASH_COUNTRIES:
        return random.choices(["Phantom Stock", "SAR (cash-settled)", "RSU"], weights=[40, 25, 35])[0]
    return random.choices(["RSU", "PSU", "Restricted Stock", "Stock Option", "SAR (stock-settled)",
                           "Phantom Stock", "Performance Cash"], weights=[58, 11, 5, 13, 5, 3, 5])[0]


def gen_tranches(total, sched_id, start):
    _, _, T, C, I = SCHED[sched_id]
    months = [C] + list(range(C + I, T + 1, I))
    first = int(total * C / T)
    rest = total - first
    n = len(months) - 1
    base = rest // n if n else 0
    shares = [first] + [base] * n
    shares[-1] += total - sum(shares)
    return [(start + relativedelta(months=m), s) for m, s in zip(months, shares)]


# ---------- Employees ----------
employees = []
n = 0
for cid, cname, ticker, industry, hq, count, *_ in COMPANIES:
    weights = [c[4] * (4 if c[1] == hq else 1) for c in COUNTRIES]
    for _ in range(count):
        n += 1
        c = random.choices(COUNTRIES, weights=weights)[0]
        first, last = random.choice(NAMES[c[1]][0]), random.choice(NAMES[c[1]][1])
        hire = date(2019, 1, 1) + timedelta(days=random.randint(0, (date(2026, 8, 31) - date(2019, 1, 1)).days))
        employees.append({
            "employee_id": f"E{n:05d}", "company_id": cid, "full_name": f"{first} {last}",
            "email": f"{first}.{last}".lower().replace(" ", "").replace("'", "") + f"{n}@example.com",
            "department": random.choice(DEPARTMENTS), "country": c[0], "country_code": c[1],
            "tax_residency_country": c[0], "local_currency": c[2], "hire_date": hire,
            "employment_status": "Active", "termination_date": None,
        })

eligible = [e for e in employees if e["hire_date"] <= date(2025, 4, 1)]
for e in random.sample(eligible, int(len(employees) * 0.04)):
    e["employment_status"] = "Terminated"
    td = AS_OF - timedelta(days=random.randint(30, 300))
    e["termination_date"] = max(td, e["hire_date"] + timedelta(days=400))
for e in random.sample([x for x in employees if x["employment_status"] == "Active"], int(len(employees) * 0.05)):
    e["tax_residency_country"] = random.choice([c for c in COUNTRIES if c[1] != e["country_code"]])[0]

# ---------- Price history (also used for ESPP offering prices) ----------
hist_rows = []
for c in COMPANIES:
    prices = [c[6]]
    for _ in range(23):
        prices.append(prices[-1] / (1 + random.gauss(0.01, 0.07)))
    prices = prices[::-1]
    for i, p in enumerate(prices):
        d = AS_OF if i == 23 else AS_OF.replace(day=1) - relativedelta(months=23 - i)
        hist_rows.append({"ticker": c[2], "price_date": d, "close_usd": round(p, 2)})
HIST = {}
for r in hist_rows:
    HIST.setdefault(r["ticker"], []).append((r["price_date"], r["close_usd"]))


def px(ticker, d):
    """Closing price on or before d (earliest price if d is before the history starts)."""
    best = HIST[ticker][0][1]
    for pd_, p in HIST[ticker]:
        if pd_ <= d:
            best = p
    return best


# ---------- Grants & tranches ----------
def next_business_day(d):
    """Vest dates never fall on a weekend: a Saturday or Sunday moves to the following Monday."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d



ticker_of = {c[0]: c[2] for c in COMPANIES}
price_of = {c[0]: c[6] for c in COMPANIES}
grants, tranches = [], []
g = t = 0
for e in employees:
    hire = e["hire_date"]
    end = e["termination_date"] or AS_OF
    dates = [hire]
    nxt = hire + relativedelta(years=1, days=random.randint(30, 120))
    while nxt <= end and len(dates) < 4:
        dates.append(nxt)
        nxt = nxt + relativedelta(years=1, days=random.randint(-30, 45))
    for gd in dates:
        g += 1
        award = pick_award(e["country_code"])
        perf = award in ("PSU", "Performance Cash")
        sched = "3Y_CLIFF_PERF" if perf else random.choices(TIME_SCHEDULES, weights=[5, 3, 1, 2])[0]
        total = random.choice([10000, 20000, 30000, 50000]) if award == "Performance Cash" else random.choice(SIZES)
        gid = f"G{g:06d}"
        forfeited = False
        for vd, sh in gen_tranches(total, sched, gd):
            vd = next_business_day(vd)
            t += 1
            if e["termination_date"] and vd > e["termination_date"]:
                status, forfeited = "Forfeited", True
            elif vd <= AS_OF:
                status = "Vested"
            else:
                status = "Unvested"
            tranches.append({"tranche_id": f"T{t:07d}", "grant_id": gid, "employee_id": e["employee_id"],
                             "vest_date": vd, "shares_vesting": sh, "status": status,
                             "contribution_usd": None, "offering_start_date": None, "offering_start_price": None})
        grants.append({
            "grant_id": gid, "employee_id": e["employee_id"], "grant_date": gd, "award_type": award,
            "ticker": ticker_of[e["company_id"]], "total_shares": total, "vesting_start_date": gd,
            "vesting_schedule_id": sched, "grant_currency": "USD",
            "strike_price": round(price_of[e["company_id"]] * random.uniform(0.5, 1.2), 2) if award in OPTION_LIKE else None,
            "grant_status": "Cancelled (termination)" if forfeited else "Active",
            "settlement": "Cash" if award in CASH_AWARDS else "Shares",
            "expiry_date": gd + relativedelta(years=10) if award in OPTION_LIKE else None,
            "perf_metric": random.choice(PERF_METRICS) if perf else None,
            "perf_max_pct": (200 if award == "PSU" else 150) if perf else None,
            "election_83b": (random.random() < 0.5) if award == "Restricted Stock" else None,
            "purchase_discount": None, "lookback": None,
        })

# ---------- ESPP: purchases every 6 months through payroll deductions ----------
OFFERINGS = []                                   # (offering start, purchase date)
d0 = date(2024, 10, 1)
while True:
    pdate = (d0 + relativedelta(months=6)) - timedelta(days=1)
    if pdate > date(2028, 3, 31):
        break
    OFFERINGS.append((d0, next_business_day(pdate)))
    d0 = d0 + relativedelta(months=6)
for e in employees:
    if (e["employment_status"] != "Active" or e["country_code"] not in ESPP_COUNTRIES
            or e["hire_date"] > AS_OF - timedelta(days=270) or random.random() > 0.28):
        continue
    mine = [o for o in OFFERINGS if o[0] >= e["hire_date"] + timedelta(days=60)]
    if not mine:
        continue
    g += 1
    gid, tick = f"G{g:06d}", ticker_of[e["company_id"]]
    contrib = random.choice([1500, 2000, 2500, 3000, 4000, 5000, 6000])
    total = 0.0
    for start, pdate in mine:
        t += 1
        if pdate <= AS_OF:
            sp, bp = px(tick, start), px(tick, pdate)
            sh, status, start_price = round(contrib / (0.85 * min(sp, bp)), 2), "Vested", sp
        else:
            start_price = px(tick, start) if start <= AS_OF else None
            sh, status = round(contrib / (0.85 * px(tick, AS_OF)), 2), "Unvested"
        total += sh
        tranches.append({"tranche_id": f"T{t:07d}", "grant_id": gid, "employee_id": e["employee_id"],
                         "vest_date": pdate, "shares_vesting": sh, "status": status, "contribution_usd": contrib,
                         "offering_start_date": start, "offering_start_price": start_price})
    grants.append({
        "grant_id": gid, "employee_id": e["employee_id"], "grant_date": mine[0][0], "award_type": "ESPP",
        "ticker": tick, "total_shares": round(total, 2), "vesting_start_date": mine[0][0],
        "vesting_schedule_id": "ESPP_6M", "grant_currency": "USD", "strike_price": None, "grant_status": "Active",
        "settlement": "Shares", "expiry_date": None, "perf_metric": None, "perf_max_pct": None,
        "election_83b": None, "purchase_discount": 0.15, "lookback": True,
    })

# ---------- Reference tables ----------
companies = pd.DataFrame([{"company_id": c[0], "company_name": c[1], "ticker": c[2], "industry": c[3],
                           "hq_country": next(k[0] for k in COUNTRIES if k[1] == c[4])} for c in COMPANIES])
market = pd.DataFrame([{"ticker": c[2], "company": c[1], "price_usd": c[6], "price_date": AS_OF,
                        "annual_volatility": c[7], "assumed_annual_growth": c[8]} for c in COMPANIES])
fx = pd.DataFrame([{"currency": cur, "units_per_usd": rate, "rate_date": AS_OF, "source": "Illustrative (synthetic)"}
                   for cur, rate in sorted({(c[2], c[3]) for c in COUNTRIES})])

tables = {
    "companies": companies, "employees": pd.DataFrame(employees), "grants": pd.DataFrame(grants),
    "vesting_tranches": pd.DataFrame(tranches),
    "vesting_schedules": pd.DataFrame(SCHEDULES, columns=["vesting_schedule_id", "description", "total_months",
                                                          "cliff_months", "interval_months"]),
    "market_data": market, "price_history": pd.DataFrame(hist_rows), "fx_rates": fx,
}
for name, df in tables.items():
    df.to_csv(OUT / f"{name}.csv", index=False)
print({k: len(v) for k, v in tables.items()})
