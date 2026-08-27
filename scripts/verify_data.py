#!/usr/bin/env python3
"""
Path 2 backtest — STEP 1: data verification pass. NO P&L computed.
Reads: data/prices_pst/ (adjusted, multiple, roll_calendars),
data/prices/stooq_*.csv, data/margin_history_stitched.csv, data/events_v3.csv.
Writes: nothing — prints coverage, point/tick tables, roll counts, qualifying
events per market-year, and the events_v3 identity cross-check, then stops.
"""
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
PST = DATA / "prices_pst"

SPAN_END = "2024-03-28"
SAMPLE_START = "2001-01-02"

PRODUCTS = {  # product -> pysystemtrade instrument
    "ZN": "US10", "6E": "EUR", "6J": "JPY", "GC": "GOLD", "SI": "SILVER",
    "HG": "COPPER", "CL": "CRUDE_W", "ZC": "CORN", "ZS": "SOYBEAN",
}
ORDER = ["ZN", "6E", "6J", "GC", "SI", "HG", "CL", "ZC", "ZS"]

# price units of the pysystemtrade adjusted series (verified by level eyeball)
UNITS = {"ZN": "points of 100k face", "6E": "USD/EUR", "6J": "USD/JPY",
         "GC": "USD/oz", "SI": "USD/oz", "HG": "USD/lb", "CL": "USD/bbl",
         "ZC": "cents/bu", "ZS": "cents/bu"}

# dollars per 1.0 price point, in the pst series' units
POINT_SIZE = {"ZN": 1000.0, "6E": 125000.0, "6J": 12500000.0, "GC": 100.0,
              "SI": 5000.0, "HG": 25000.0, "CL": 1000.0, "ZC": 50.0, "ZS": 50.0}

# minimum tick in price units. ZN/6E/6J/GC/HG reused from the committed
# stage2_v3.py cost table; SI/CL/ZC/ZS hard-coded from CME contract specs
# (outright minimum price fluctuation).
TICK = {"ZN": 0.015625, "6E": 0.0001, "6J": 0.000001, "GC": 0.10, "HG": 0.0005,
        "SI": 0.005, "CL": 0.01, "ZC": 0.25, "ZS": 0.25}
TICK_SOURCE = {p: "committed stage2_v3" for p in ["ZN", "6E", "6J", "GC", "HG"]}
TICK_SOURCE.update({p: "CME spec (new)" for p in ["SI", "CL", "ZC", "ZS"]})

STOOQ_SCALE = {"SI": 100.0, "HG": 100.0}  # stooq quotes cents; pst dollars

# expected rolls/yr sanity bands from the build prompt
EXPECT_ROLLS = {"CL": "~12", "ZC": "~5", "ZS": "~5", "SI": "~5", "HG": "~5",
                "6E": "~4", "6J": "~4", "ZN": "~4", "GC": "~6"}

# ---------------- load ----------------
adj, rollcal, stooq, evcal = {}, {}, {}, {}
for prod, instr in PRODUCTS.items():
    # weekend-stamped rows are partial Globex sessions, not settlements; latest
    # stamp per weekday date is the settlement (no hour filter: grain
    # settlements 2020-22 are stamped 19:00)
    a = pd.read_csv(PST / f"adjusted/{instr}.csv").sort_values("DATETIME")
    a["date"] = a.DATETIME.str[:10]
    a = a[pd.to_datetime(a.date).dt.dayofweek < 5]
    adj[prod] = a.groupby("date", as_index=True).price.last().sort_index()
    rc = pd.read_csv(PST / f"roll_calendars/{instr}.csv")
    rc["date"] = rc.DATE_TIME.str[:10]
    rollcal[prod] = rc
    # event-clustering calendar: stage1_v3's exact construction (hour>=20
    # settlement rows, 1995+, weekend-stamped dates included)
    mp = pd.read_csv(PST / f"multiple/{instr}.csv")
    mp["date"] = mp.DATETIME.str[:10]
    s1 = mp[(mp.DATETIME.str[11:13].astype(int) >= 20)
            & (mp.date >= "1995-01-01") & (mp.date <= SPAN_END)]
    evcal[prod] = sorted(s1.date.unique())
    s = pd.read_csv(DATA / f"prices/stooq_{prod}_continuous.csv")
    stooq[prod] = s.set_index("date").close.sort_index()

margin = pd.read_csv(DATA / "margin_history_stitched.csv")
margin = margin[margin["product"].isin(PRODUCTS)].sort_values(["product", "effective_date"])

def td_shift(prod, d, k):
    """trading-day arithmetic on the stage1 event calendar (d snapped forward)"""
    c = evcal[prod]
    later = [x for x in c if x >= d]
    if not later:
        return None
    j = c.index(later[0]) + k
    return c[j] if 0 <= j < len(c) else None


# ---------------- 1. date coverage ----------------
print("## 1. Date coverage vs spec §1 (sample 2001-01-02 -> 2024-03-28)\n")
print(f"{'prod':<5} {'adj first':<11} {'adj last':<11} {'adj rows':>8} "
      f"{'td<2001':>8} {'stooq first':<12} {'stooq last':<11} "
      f"{'margin first':<13} {'margin last':<12}")
for p in ORDER:
    a = adj[p]
    mg = margin[margin["product"] == p]
    n_pre = int((a.index < SAMPLE_START).sum())
    flag = "" if a.index.max() >= SPAN_END and n_pre >= 252 else "  <-- CHECK"
    print(f"{p:<5} {a.index.min():<11} {a.index.max():<11} {len(a):>8} "
          f"{n_pre:>8} {stooq[p].index.min():<12} {stooq[p].index.max():<11} "
          f"{mg.effective_date.min():<13} {mg.effective_date.max():<12}{flag}")
print("\n(td<2001 = adjusted trading days available before sample start; "
      ">=252 needed for the trailing-252-td signal at 2001-01-02.)")

# ---------------- 2. point sizes / tick values ----------------
print("\n## 2. Point sizes and tick values (eyeball check)\n")
print(f"{'prod':<5} {'pst units':<19} {'point $':>11} {'tick':>9} {'tick $':>8} "
      f"{'tick src':<20} {'adj@end':>10} {'stooq@end':>10} {'notional $':>11} "
      f"{'maint $':>8} {'mgn/ntl':>7}")
for p in ORDER:
    a_end = adj[p].loc[:SPAN_END].iloc[-1]
    s = stooq[p].loc[:SPAN_END]
    s_end = s.iloc[-1] / STOOQ_SCALE.get(p, 1.0)
    notional = s_end * POINT_SIZE[p]
    mg = margin[(margin["product"] == p) & (margin.effective_date <= SPAN_END)]
    maint = mg.maintenance.iloc[-1] if len(mg) else np.nan
    tick_usd = TICK[p] * POINT_SIZE[p]
    print(f"{p:<5} {UNITS[p]:<19} {POINT_SIZE[p]:>11,.0f} {TICK[p]:>9g} "
          f"{tick_usd:>8.3f} {TICK_SOURCE[p]:<20} {a_end:>10.4f} {s_end:>10.4f} "
          f"{notional:>11,.0f} {maint:>8,.0f} {maint/notional*100:>6.2f}%")
print("\n(adj@end / stooq@end / notional / maint as of 2024-03-28; stooq SI & HG "
      "divided by 100 — cents->dollars, the verified stage1 convention.)")

# ---------------- 3. roll calendar counts per market-year ----------------
print("\n## 3. Roll-calendar rolls per market per year (2001-2024)\n")
years = list(range(2001, 2025))
counts = {}
for p in ORDER:
    d = rollcal[p]["date"]
    yr = d.str[:4].astype(int)
    counts[p] = yr[(yr >= 2001) & (yr <= 2024)].value_counts()
hdr = "year  " + "".join(f"{p:>5}" for p in ORDER)
print(hdr)
for y in years:
    print(f"{y}  " + "".join(f"{counts[p].get(y, 0):>5}" for p in ORDER))
print("mean  " + "".join(f"{counts[p].reindex(years).fillna(0).mean():>5.1f}" for p in ORDER))
print("expct " + "".join(f"{EXPECT_ROLLS[p]:>5}" for p in ORDER))
for p in ORDER:
    last_roll = rollcal[p]["date"].max()
    if last_roll < "2024-01-01":
        print(f"NOTE: {p} roll calendar ends {last_roll}")

# ---------------- 4. qualifying margin events per market-year ----------------
# identical rule to the closed studies (stage1_v3.py): actual-increase dates
# where the 5-business-day cumulative maintenance change >= 5%, then
# anchor-window clustered at 10 trading days on the product price calendar.
def qualifying_events(prod, start, end):
    g = margin[margin["product"] == prod].sort_values("effective_date")
    dup = g.effective_date.duplicated().sum()
    if dup:
        print(f"NOTE: {prod} has {dup} duplicate effective_date rows; keeping last")
        g = g.drop_duplicates("effective_date", keep="last")
    lv = g.set_index("effective_date").maintenance.astype(float)
    pct = lv.pct_change()
    grid = pd.bdate_range(lv.index.min(), end)
    level = lv.reindex(grid.strftime("%Y-%m-%d")).ffill()
    cum5 = level / level.shift(5) - 1.0
    inc_dates = set(d for d, v in pct.items() if v == v and v > 0)
    qd = sorted((d, float(cum5.loc[d])) for d in level.index
                if d in inc_dates and cum5.loc[d] == cum5.loc[d]
                and cum5.loc[d] >= 0.05 and start <= d <= end)
    events, i = [], 0
    while i < len(qd):
        d0, cum0 = qd[i]
        close = td_shift(prod, d0, 10)
        j = i + 1
        while j < len(qd) and close is not None and qd[j][0] <= close:
            j += 1
        events.append((d0, cum0))
        i = j
    return events


print("\n## 4. Qualifying margin events per market per year (rule: >=5% cum "
      "maintenance increase in 5bd, 10-td anchor-window clustering)\n")
ev_all = {p: qualifying_events(p, margin[margin["product"] == p].effective_date.min(),
                               SPAN_END) for p in ORDER}
print(hdr)
tot = {p: 0 for p in ORDER}
for y in years:
    row = []
    for p in ORDER:
        n = sum(1 for d, _ in ev_all[p] if d.startswith(str(y)))
        tot[p] += n
        row.append(n)
    print(f"{y}  " + "".join(f"{n:>5}" for n in row))
print("tot   " + "".join(f"{tot[p]:>5}" for p in ORDER)
      + f"   grand total {sum(tot.values())}")
pre = {p: sum(1 for d, _ in ev_all[p] if d < "2001-01-01") for p in ORDER}
if any(pre.values()):
    print("pre-2001 (burn year, unused): "
          + ", ".join(f"{p}:{n}" for p, n in pre.items() if n))

# cross-check vs the committed events_v3.csv (6 confirmatory products,
# their binding starts, same rule) — recompute with their start filter
BINDING_START = {"6E": "2000-01-01", "6J": "2000-02-03", "ZN": "2004-01-02",
                 "GC": "2009-01-08", "SI": "2009-01-08", "HG": "2009-01-08"}
v3 = pd.read_csv(DATA / "events_v3.csv")
v3_set = set(zip(v3["product"], v3["effective_date"]))
mine = set()
for p, st in BINDING_START.items():
    mine |= {(p, d) for d, _ in qualifying_events(p, st, SPAN_END)}
if mine == v3_set:
    print(f"\nCross-check vs committed events_v3.csv (6 products, binding "
          f"starts): IDENTICAL ({len(mine)} events)")
else:
    print("\nCross-check vs events_v3.csv: DEVIATION")
    print("  mine-not-v3:", sorted(mine - v3_set))
    print("  v3-not-mine:", sorted(v3_set - mine))
