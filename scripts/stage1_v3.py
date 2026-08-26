#!/usr/bin/env python3
"""
Preregistration v3.0 — PART B, Stage 1 ONLY.
Events + hygiene + K0 gates. NO post-entry return calculations of any kind.
(trailing_return / trailing_vol are pre-entry conditioning fields required by
the Stage-1 events_v3.csv schema and A4; nothing after entry is computed.)

v3 amendments implemented here (see prereg A0):
  1. A4 completeness fallback: PRICE-selected contract with an incomplete
     [entry-21, entry+11] window falls back to the entry-date FORWARD contract
     iff the FORWARD window is complete; no fallback when the roll-imminent
     rule already selected FORWARD. Flagged per event, counted per product.
  2. A8 Gate 3 computed over products remaining after the conduct-rule
     exclusion; conduct-excluded completeness reported separately. Floors
     (>=90%, <70% drop, >=5 products, >=150 events) unchanged.
  3. A3 dating pinned to threshold-crossing date (matches v2 implementation;
     event set checked for identity against events_v2.csv and any deviation
     printed).
"""
import math
import random
import collections
from datetime import date
from pathlib import Path

import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
PST = DATA / "prices_pst"

PRODUCTS = {"ZN": "US10", "6E": "EUR", "6J": "JPY", "GC": "GOLD", "SI": "SILVER", "HG": "COPPER"}
BINDING_START = {"6E": "2000-01-01", "6J": "2000-02-03", "ZN": "2004-01-02",
                 "GC": "2009-01-08", "SI": "2009-01-08", "HG": "2009-01-08"}
SPAN_END = "2024-03-28"
STOOQ_SCALE = {"SI": 100.0, "HG": 100.0}   # stooq quotes cents; pst dollars (verified convention)

random.seed(42)

# ---------------- load prices ----------------
def load_pst(instr):
    mp = pd.read_csv(PST / f"multiple/{instr}.csv")
    mp["date"] = mp.DATETIME.str[:10]
    # settlement rows only: end-of-day stamps are >= 20:00; earlier timestamps are
    # intraday quote samples (e.g. US-holiday Globex sessions with no settlement)
    mp = mp[mp.DATETIME.str[11:13].astype(int) >= 20]
    # daily selection frame: last non-NaN per column per day (later years mix
    # sparse intraday rows with the 23:00 close row)
    daily = mp.groupby("date").agg(lambda s: s.dropna().iloc[-1] if s.dropna().size else np.nan).reset_index()
    rc = pd.read_csv(PST / f"roll_calendars/{instr}.csv")
    rc["date"] = rc.DATE_TIME.str[:10]
    return mp, daily, rc


def contract_price_series(mp):
    """per-contract price dict: contract -> {date: price}, collected across
    PRICE/FORWARD/CARRY appearances (settlement rows; last non-NaN of day)"""
    out = collections.defaultdict(dict)
    for col, ccol in [("PRICE", "PRICE_CONTRACT"), ("FORWARD", "FORWARD_CONTRACT"), ("CARRY", "CARRY_CONTRACT")]:
        sub = mp[["date", "DATETIME", col, ccol]].dropna(subset=[col, ccol]).sort_values("DATETIME")
        for d, _, pval, c in sub.itertuples(index=False):
            out[str(int(c))[:6]][d] = float(pval)   # later timestamps overwrite
    return out


prices, rolls, cseries, cal = {}, {}, {}, {}
for prod, instr in PRODUCTS.items():
    mp, daily, rc = load_pst(instr)
    mp = mp[(mp.date >= "1995-01-01") & (mp.date <= SPAN_END)]
    daily = daily[(daily.date >= "1995-01-01") & (daily.date <= SPAN_END)]
    prices[prod] = daily.set_index("date")
    rolls[prod] = rc
    cseries[prod] = contract_price_series(mp)
    cal[prod] = sorted(daily.date.unique())

calpos = {p: {d: i for i, d in enumerate(cal[p])} for p in PRODUCTS}


def td_shift(prod, d, k):
    """trading-day arithmetic on the product's price calendar; d snapped forward"""
    c = cal[prod]
    if d in calpos[prod]:
        i = calpos[prod][d]
    else:
        later = [x for x in c if x >= d]
        if not later:
            return None
        i = calpos[prod][later[0]]
    j = i + k
    if 0 <= j < len(c):
        return c[j]
    return None


# ---------------- margin events (A3; dating pinned to threshold-crossing date) ----------------
m = pd.read_csv(DATA / "margin_history_stitched.csv")
m = m[m["product"].isin(PRODUCTS)].sort_values(["product", "effective_date"])

flags_200 = []
qual = {}
for prod, g in m.groupby("product"):
    g = g.sort_values("effective_date")
    lv = g.set_index("effective_date").maintenance.astype(float)
    # >200% jump conduct flag
    pct = lv.pct_change()
    for d, v in pct.items():
        if v == v and v > 2.0:
            flags_200.append((prod, d, v))
    # weekday grid level series (ffill), 5-business-day cumulative change
    grid = pd.bdate_range(lv.index.min(), SPAN_END)
    level = lv.reindex(grid.strftime("%Y-%m-%d")).ffill()
    lvl5 = level.shift(5)
    cum5 = level / lvl5 - 1.0
    inc_dates = set(d for d, v in pct.items() if v == v and v > 0)
    qdates = [(d, float(cum5.loc[d])) for d in level.index
              if d in inc_dates and cum5.loc[d] == cum5.loc[d] and cum5.loc[d] >= 0.05
              and BINDING_START[prod] <= d <= SPAN_END]
    qual[prod] = qdates

# anchor-window clustering, 10 trading days on the product price calendar
events = []
for prod, qd in qual.items():
    qd.sort()
    i = 0
    while i < len(qd):
        d0, cum0 = qd[i]
        close = td_shift(prod, d0, 10)
        j = i + 1
        while j < len(qd) and close is not None and qd[j][0] <= close:
            j += 1
        events.append(dict(product=prod, effective_date=d0, cum_increase_pct=cum0))
        i = j

# A3 identity check vs the committed v2 event set (Part B step 1)
v2 = pd.read_csv(DATA / "events_v2.csv")
v2_set = set(zip(v2["product"], v2["effective_date"]))
v3_set = set((e["product"], e["effective_date"]) for e in events)
if v2_set == v3_set:
    print(f"A3 event-set identity check vs events_v2.csv: IDENTICAL ({len(v3_set)} events)")
else:
    print("A3 event-set identity check vs events_v2.csv: DEVIATION")
    print("  in v3 not v2:", sorted(v3_set - v2_set))
    print("  in v2 not v3:", sorted(v2_set - v3_set))

# ---------------- contract selection & window completeness (A4, amended) ----------------
rows = []
hg_may_count = 0
for ev in sorted(events, key=lambda e: (e["product"], e["effective_date"])):
    prod = ev["product"]
    d0 = ev["effective_date"]
    entry = td_shift(prod, d0, 0)   # first settlement on/after effective date
    rec = dict(product=prod, effective_date=d0, entry_date=entry, selected_contract="",
               cum_increase_pct=ev["cum_increase_pct"], trailing_return="", trailing_vol="",
               cluster_week="", completeness_fallback=False, included_flag=False, exclusion_reason="")
    iso = date.fromisoformat(d0).isocalendar()
    rec["cluster_week"] = f"{iso[0]}-W{iso[1]:02d}"
    if entry is None:
        rec["exclusion_reason"] = "no settlement on/after effective date within span"
        rows.append(rec); continue
    prow = prices[prod].loc[entry]
    if prow.PRICE_CONTRACT != prow.PRICE_CONTRACT:
        rec["exclusion_reason"] = "no PRICE contract at entry"
        rows.append(rec); continue
    sel = str(int(prow.PRICE_CONTRACT))[:6]
    fwd = str(int(prow.FORWARD_CONTRACT))[:6] if prow.FORWARD_CONTRACT == prow.FORWARD_CONTRACT else None
    # roll within 11 trading days after entry -> FORWARD (no completeness fallback in that case)
    end11 = td_shift(prod, entry, 11)
    rcp = rolls[prod]
    roll_soon = ((rcp.date > entry) & (rcp.date <= (end11 or "9999"))).any()
    fallback_allowed = not roll_soon
    if roll_soon:
        if fwd is not None:
            sel = fwd
        else:
            rec["exclusion_reason"] = "roll imminent but no FORWARD contract available"
            rows.append(rec); continue
    # window completeness [entry-21, entry+11] on the product's trading calendar
    lo = td_shift(prod, entry, -21)
    hi = end11
    if lo is None or hi is None:
        rec["exclusion_reason"] = "window extends beyond price data span"
        rows.append(rec); continue
    win = [d for d in cal[prod] if lo <= d <= hi]
    series = cseries[prod].get(sel, {})
    missing = [d for d in win if d not in series]
    if missing and fallback_allowed and fwd is not None and fwd != sel:
        fwd_series = cseries[prod].get(fwd, {})
        fwd_missing = [d for d in win if d not in fwd_series]
        if not fwd_missing:
            sel, series, missing = fwd, fwd_series, []
            rec["completeness_fallback"] = True
    if prod == "HG" and sel[4:6] == "05":
        hg_may_count += 1  # per A4: next cycle contract (cannot occur with PRICE/FORWARD selection; counted)
    rec["selected_contract"] = sel
    if missing:
        rec["exclusion_reason"] = (f"selected contract missing {len(missing)} of {len(win)} window days"
                                   + ("" if not fallback_allowed or fwd is None or fwd == sel
                                      else " (FORWARD fallback also incomplete)"))
        rows.append(rec); continue
    # trailing 20-td log return and vol at entry (pre-entry only)
    idx = win.index(entry)
    p_entry = series[entry]
    p_lag = series[win[idx - 20]]
    logrets = [math.log(series[win[k]] / series[win[k - 1]]) for k in range(idx - 19, idx + 1)]
    rec["trailing_return"] = math.log(p_entry / p_lag)
    rec["trailing_vol"] = float(np.std(logrets, ddof=1) * math.sqrt(252))
    if rec["trailing_return"] == 0.0:
        rec["exclusion_reason"] = "trailing return exactly zero (v1 A4 exclusion)"
        rows.append(rec); continue
    rec["included_flag"] = True
    rows.append(rec)

ev_df = pd.DataFrame(rows)
ev_df.to_csv(DATA / "events_v3.csv", index=False)

# ---------------- hygiene (Stage 1 step 3; v2 verbatim + fallback counts) ----------------
print("=" * 78)
print("STAGE 1 v3 HYGIENE [analysis span: per-product binding start -> 2024-03-28]")
stooq = {p: pd.read_csv(DATA / f"prices/stooq_{p}_continuous.csv", index_col=0) for p in PRODUCTS}

# (a) SILVER / COPPER scale verification (and SILVER contract-size resolution)
for prod in ["SI", "HG"]:
    scale = STOOQ_SCALE[prod]
    diffs = []
    for d in random.sample(cal[prod][2000:-100], 200):
        if d in stooq[prod].index:
            st = float(stooq[prod].loc[d, "close"]) / scale
            pp = float(prices[prod].loc[d, "PRICE"])
            diffs.append(abs(pp - st) / st)
    diffs = sorted(diffs)
    med = diffs[len(diffs) // 2]
    print(f"  scale check {prod}: stooq/100 vs pst, median |diff| = {med*100:.3f}% over {len(diffs)} days "
          f"({'PASS: same price level, 100x convention confirmed' if med < 0.02 else 'REVIEW'})")

# SILVER contract-size resolution (5,000 oz SI vs 1,000 oz series), three tests:
#  (i)  history begins decades before the 1,000-oz contract's 2013 launch;
#  (ii) exact settlement matches to stooq SI.F (COMEX SI) exist on same-contract days;
#  (iii) SI's stooq-mismatch pattern matches GOLD's (an unambiguous full-size series),
#        i.e. explained by stooq's serial-month front months, not a size/price offset.
def _postroll_diffs(prod):
    diffs = []
    for rd in rolls[prod].date.tolist():
        d = td_shift(prod, rd, 5)
        if d and d in stooq[prod].index and d >= "2009-01-01":
            st = float(stooq[prod].loc[d, "close"]) / STOOQ_SCALE.get(prod, 1.0)
            pv = prices[prod].loc[d, "PRICE"]
            if pv == pv:
                diffs.append(abs(float(pv) - st) / st)
    return sorted(diffs)

si_start = pd.read_csv(PST / "multiple/SILVER.csv", nrows=1).DATETIME.iloc[0][:10]
d_si = _postroll_diffs("SI")
d_gc = _postroll_diffs("GC")
si_exact = sum(1 for x in d_si if x < 0.0005)
med_si = d_si[len(d_si) // 2] if d_si else float("nan")
med_gc = d_gc[len(d_gc) // 2] if d_gc else float("nan")
t1 = si_start < "2013-01-01"
t2 = si_exact >= 3
t3 = med_si <= 2 * med_gc
si_resolved = t1 and t2 and t3
print(f"  SILVER contract-size resolution:")
print(f"    (i)  series starts {si_start} — decades before the 1,000-oz contract's 2013 launch: {'PASS' if t1 else 'FAIL'}")
print(f"    (ii) exact settlement matches to stooq SI.F (COMEX 5,000 oz SI) on same-contract days: {si_exact} found: {'PASS' if t2 else 'FAIL'}")
print(f"    (iii) mismatch pattern vs GOLD benchmark (serial-month interposition on stooq side): "
      f"median |diff| SI {med_si*100:.2f}% vs GC {med_gc*100:.2f}%: {'PASS' if t3 else 'FAIL'}")
print(f"    -> {'RESOLVED: pst SILVER prices the COMEX 5,000 oz SI contract' if si_resolved else 'UNRESOLVED -> per conduct rule, SI excluded under the K0 product-drop rule'}")

# (b) 20 random selected-contract settlements per product vs stooq where same contract is front
print("  per-product settlement cross-check (dates 5-30 td after a pst roll, front-aligned):")
for prod in PRODUCTS:
    cands = []
    for rd in rolls[prod].date.tolist():
        for k in (5, 15, 25):
            d = td_shift(prod, rd, k)
            if d and d in stooq[prod].index and BINDING_START[prod] <= d <= SPAN_END:
                cands.append(d)
    sample = random.sample(cands, min(20, len(cands)))
    scale = STOOQ_SCALE.get(prod, 1.0)
    flagged = 0
    for d in sample:
        st = float(stooq[prod].loc[d, "close"]) / scale
        pp = float(prices[prod].loc[d, "PRICE"])
        if abs(pp - st) / st > 0.001:
            flagged += 1
    print(f"    {prod}: {20 - flagged if len(sample)==20 else len(sample)-flagged}/{len(sample)} within 0.1%; {flagged} flagged (>0.1%, incl. contract-mismatch days)")

# (c) window holes and fallback accounting: all exclusions explicit in events_v3.csv
n_holes = (ev_df.exclusion_reason.str.contains("missing", na=False)).sum()
print(f"  window-hole check: {n_holes} events excluded for in-window missing prices (explicit, logged); none silent")
fb = ev_df[ev_df.completeness_fallback]
fb_counts = fb.groupby("product").size().to_dict()
print(f"  A4 completeness-fallback selections (genuine FORWARD settlements, no imputation): "
      f"{len(fb)} total; per product: {fb_counts if fb_counts else 'none'}")
print(f"  >200% margin-jump conduct flags within event inputs: {len(flags_200)}", flags_200 if flags_200 else "")
print(f"  HG May-contract substitutions (A4): {hg_may_count}")

# ---------------- K0 gates (A8, Gate 3 per A0.2) ----------------
print("=" * 78)
print("K0 GATES [6 declared products; spans: binding start -> 2024-03-28]")
total_events = len(ev_df)
per_prod = ev_df.groupby("product").agg(events=("effective_date", "count"),
                                        included=("included_flag", "sum"))
per_prod["survival"] = per_prod.included / per_prod.events
print("\nper-product qualifying clustered events / window-completeness survival:")
for prod in ["ZN", "6E", "6J", "GC", "SI", "HG"]:
    if prod in per_prod.index:
        r = per_prod.loc[prod]
        print(f"  {prod}: {int(r.events):3d} events, {int(r.included):3d} survive ({r.survival*100:.1f}%)")
    else:
        print(f"  {prod}:   0 events")

pilot_end = "2014-12-31"
pilot_events = ev_df[ev_df.effective_date <= pilot_end]
n_pilot = len(pilot_events)

# Gate 3 (A0.2): conduct-rule exclusion first; overall survival over remaining universe
conduct_excluded = [] if si_resolved else ["SI"]
in_universe = [p for p in per_prod.index if p not in conduct_excluded]
universe_ev = ev_df[ev_df["product"].isin(in_universe)]
overall_survival = universe_ev.included_flag.mean()
dropped = [p for p in in_universe if per_prod.loc[p, "survival"] < 0.70]
remaining = [p for p in in_universe if p not in dropped]
remaining_events = int(per_prod.loc[remaining].included.sum()) if remaining else 0

g1 = total_events >= 180
g2 = n_pilot >= 50
g3 = (overall_survival >= 0.90) and (len(remaining) >= 5) and (remaining_events >= 150)

if conduct_excluded:
    for p in conduct_excluded:
        r = per_prod.loc[p]
        print(f"\nconduct-rule exclusion: {p} (price-series identity unresolved); its completeness, "
              f"reported separately per A0.2: {int(r.included)}/{int(r.events)} ({r.survival*100:.1f}%)")

print(f"\nGATE 1  total qualifying clustered events (full span, 6 declared products): {total_events}  vs >= 180  -> {'PASS' if g1 else 'FAIL'}")
print(f"GATE 2  pilot qualifying clustered events (binding start -> 2014-12-31): {n_pilot}  vs >= 50  -> {'PASS' if g2 else 'FAIL'}")
print(f"GATE 3  window-completeness survival over post-conduct-exclusion universe "
      f"({'/'.join(sorted(in_universe))}): {overall_survival*100:.1f}% vs >= 90%;"
      f" products <70% dropped: {dropped if dropped else 'none'};"
      f" remaining products: {len(remaining)} (>=5), surviving events: {remaining_events} (>=150)"
      f"  -> {'PASS' if g3 else 'FAIL'}")

if g1 and g2 and g3:
    print("\nK0: ALL GATES PASS. Stage 1 complete; stopping before any Stage 2 computation.")
    print("Per Part B step 4: HARD STOP — commit the Stage-1 record; Stage 2 (pilot) runs only on explicit human trigger.")
else:
    fails = []
    if not g1: fails.append(f"total qualifying clustered events, {total_events} vs. 180")
    if not g2: fails.append(f"pilot qualifying clustered events, {n_pilot} vs. 50")
    if not g3: fails.append(f"window-completeness gate, {overall_survival*100:.1f}%/{len(remaining)} products/{remaining_events} events vs. 90%/5/150")
    for f_ in fails:
        print(f'\n"The strategy could not be tested: the data gate failed ({f_} preregistered minimum), '
              f'so no backtest was run and no claim about the strategy\'s profitability is made."')
