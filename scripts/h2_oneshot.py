#!/usr/bin/env python3
"""
Preregistration H2 v1.0 — PART B: ONE-SHOT confirmatory run (single stage, single run).

Machinery: copied from the committed scripts/stage2_v3.py (itself logic-identical
to the committed stage1_v3.py A4 selection), with exactly the H2-prescribed
modifications and nothing else:
  - Direction rule (H1): position = +sign(trailing 20-td return) — continuation.
    Applied identically to events AND control pseudo-trades (H2 A2 "Trade"/"Controls").
  - Sample: events_v3.csv included events with entry_date in [2015-01-01, 2024-03-28],
    5-product universe (ZN, 6E, 6J, GC, HG; SI conduct-excluded per the committed
    Stage-1 record — SILVER prices never load).
  - Control candidate days restricted to [2015-01-01, 2024-03-28] (H2 A2 "Controls").
  - Verdict: C1/C2/C3/C4 per H2 H3, in order; any FAIL -> H2_FAIL + H5 sentence
    as the FIRST LINE of h2_results.md.

Strictest-reading log (H4: ambiguities resolved by the strictest available
reading, logged; no amendment of any kind):
  R1. Step-1 sample floor (>= 40) counts INCLUDED (A4-surviving) events in the
      5-product universe — the events actually analyzed. Universe counts and SI
      attrition are reported alongside, before any return is computed.
  R2. Window membership is by entry_date (H2 A2 says "entry dates"); the
      entry-vs-effective boundary coincidence is checked and reported.
  R3. Price load span 2014-10-01 -> 2024-03-28: the minimum covering the
      [entry-21, entry+11] windows and -15..+15 plot lags of early-2015 entries
      and the +/-15-td margin-change exclusion look-back at the 2015-01-01
      boundary. Pre-2015 days are never events and never control candidates
      (burned pilot data enters only as trailing context required by A4/A5).
  R4. "Assert ... match events_v3.csv exactly" is implemented with the committed
      Stage-2 assertion machinery verbatim: exact equality for selected contract
      and fallback flag; |diff| < 1e-9 for trailing return/vol (CSV float
      round-trip).
  R5. C3 segments split by entry_date at 2021-01-01; segment D over matched
      events; an empty segment fails C3 (strictest). Both sub-conditions must
      hold: D_recent >= +10 AND D_recent >= 0.4 * D_early.
  R6. C4 "largest absolute contribution": additive share, contribution_p =
      sum of (event - control-mean) diffs over product p's matched events
      (= n_p * D_p; D = sum_p contribution_p / N_matched). The product with
      max |contribution_p| is excluded; a tie (float-improbable) breaks toward
      the exclusion yielding the LOWER recomputed D (strictest). An empty
      post-exclusion set fails C4 (strictest).
  R7. Tick specs: the committed stage2_v3.py hard-coded values are reused
      verbatim (labeled pilot-era there). For 2015-2024 they are conservative
      (older, larger ticks). The cost table is context; C2 is fixed at +10 bps
      gross and does not rescale.
  R8. H5 "[failed criterion]": every failing criterion is listed inside the
      parenthetical, each with measured value vs. threshold.
  R9. Leave-one-crisis-out drops matched events by entry-date calendar year
      (2020; 2022); sign flips vs. full-sample D are reported as non-fatal
      fragility flags per H3.
  R10. G is the mean over ALL included events (unmatched events remain in G;
      they drop only from the matched comparison) — committed Stage-2 reading.
  R11. Bootstrap: monthly blocks over matched events' entry months, 10,000
      draws, numpy seed 42 — committed Stage-2 machinery verbatim.
  R12. On a sample-floor failure the H5 sentence is also written as the first
      line of h2_results.md and H2_FAIL is written (the record must exist and
      carry the verbatim sentence per H4/H5).

Containment: this session loads the 2015-01-01 -> 2024-03-28 sample for the
first time ever, computes exactly the outputs prescribed by Part B step 3, and
nothing else. One run; whatever it prints is final.
"""
import math
import sys
import collections
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
PST = DATA / "prices_pst"

# SI is conduct-excluded per the committed Stage-1 record (SILVER never loaded here)
PRODUCTS = {"ZN": "US10", "6E": "EUR", "6J": "JPY", "GC": "GOLD", "HG": "COPPER"}
H2_START = "2015-01-01"
H2_END = "2024-03-28"
SPLIT = "2021-01-01"
PRICE_LOAD_START = "2014-10-01"   # R3: minimum trailing/exclusion context before 2015-01-01
PRICE_LOAD_END = "2024-03-28"     # end of the committed price data

# A6 cost model tick specs — committed stage2_v3.py values reused verbatim (R7)
TICK = {"ZN": 0.015625, "6E": 0.0001, "6J": 0.000001, "GC": 0.10, "HG": 0.0005}
FEES_BPS_PER_SIDE = 0.2

RNG = np.random.default_rng(42)

H5_TEMPLATE = ('"The continuation strategy failed its preregistered one-shot test on previously '
               'untouched 2015–2024 data ({fails}); combined with the reversal hypothesis\'s earlier '
               'preregistered failure, margin-increase events show no exploitable multi-day return '
               'signal in either direction, and no margin-based strategy will be pitched."')

# ============ PART B STEP 1 — sample selection and floor, BEFORE any return ============
ev_all = pd.read_csv(DATA / "events_v3.csv", dtype={"selected_contract": str})
in_window = ev_all.entry_date.notna() & (ev_all.entry_date >= H2_START) & (ev_all.entry_date <= H2_END)
si_h2 = ev_all[(ev_all["product"] == "SI") & in_window]                    # attrition reporting only
h2 = ev_all[ev_all["product"].isin(PRODUCTS) & in_window].copy()           # 5-product universe
h2_inc = h2[h2.included_flag].copy()

# R2 boundary coincidence: entry-date vs effective-date window definitions
eff_window = ev_all.effective_date.notna() & (ev_all.effective_date >= H2_START) & (ev_all.effective_date <= H2_END)
straddlers = ev_all[(in_window != eff_window) & ev_all["product"].isin(PRODUCTS)]

print("=" * 78)
print(f"H2 SAMPLE [entry dates {H2_START} -> {H2_END}; committed events_v3.csv; no new construction]")
print(f"{'product':8s} {'in window':>9s} {'included':>9s} {'excluded':>9s}")
count_rows = []
for prod in sorted(PRODUCTS):
    pw = h2[h2["product"] == prod]
    pi = pw[pw.included_flag]
    count_rows.append(dict(product=prod, in_window=len(pw), included=len(pi), excluded=len(pw) - len(pi)))
    print(f"{prod:8s} {len(pw):9d} {len(pi):9d} {len(pw) - len(pi):9d}")
print(f"{'TOTAL':8s} {len(h2):9d} {len(h2_inc):9d} {len(h2) - len(h2_inc):9d}")
print(f"SI (conduct-excluded, attrition only): {len(si_h2)} events in window, "
      f"{int(si_h2.included_flag.sum())} with complete windows — no SILVER price loads, no SI return computed")
print(f"entry-vs-effective window-membership deviations (R2): {len(straddlers)}")
excl_reasons = h2[~h2.included_flag].groupby("exclusion_reason").size().to_dict()
print(f"excluded-event reasons (5-product universe): {excl_reasons if excl_reasons else 'none'}")
print(f"A4 completeness-fallback events in sample: {int(h2_inc.completeness_fallback.sum())}")
n_sample = len(h2_inc)
print(f"\nSAMPLE FLOOR: {n_sample} included events vs preregistered minimum 40 -> "
      f"{'PASS' if n_sample >= 40 else 'FAIL'}")

if n_sample < 40:
    sent = H5_TEMPLATE.format(fails=f"sample floor: {n_sample} vs 40")
    print(sent)
    (REPO / "H2_FAIL").write_text(sent + "\n")
    lines = [sent, "", "# H2 Results — Preregistration H2 v1.0 (one-shot)", "",
             f"Sample floor failed before any return was computed: {n_sample} included events "
             f"(5-product universe, entry {H2_START} -> {H2_END}) vs preregistered minimum 40. "
             "No returns, controls, or statistics were computed (Part B step 1)."]
    (REPO / "h2_results.md").write_text("\n".join(lines) + "\n")
    sys.exit(0)

# ============ load prices (committed stage2_v3.py loader; H2 span per R3) ============
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


prices, rolls, cseries, cal, roll_dates = {}, {}, {}, {}, {}
for prod, instr in PRODUCTS.items():
    mp, daily, rc = load_pst(instr)
    mp = mp[(mp.date >= PRICE_LOAD_START) & (mp.date <= PRICE_LOAD_END)]
    daily = daily[(daily.date >= PRICE_LOAD_START) & (daily.date <= PRICE_LOAD_END)]
    prices[prod] = daily.set_index("date")
    rolls[prod] = rc
    roll_dates[prod] = rc.date.values
    cseries[prod] = contract_price_series(mp)
    cal[prod] = sorted(daily.date.unique())

calpos = {p: {d: i for i, d in enumerate(cal[p])} for p in PRODUCTS}


# ---------------- amended A4 selection at a trading day (committed logic) ----------------
def a4_at(prod, d):
    """Returns (dict(sel, series, win, fallback), None) or (None, reason).
    win = the 33 trading days [d-21, d+11]; d sits at index 21."""
    i = calpos[prod].get(d)
    if i is None:
        return None, "not a trading day"
    prow = prices[prod].loc[d]
    if prow.PRICE_CONTRACT != prow.PRICE_CONTRACT:
        return None, "no PRICE contract"
    sel = str(int(prow.PRICE_CONTRACT))[:6]
    fwd = str(int(prow.FORWARD_CONTRACT))[:6] if prow.FORWARD_CONTRACT == prow.FORWARD_CONTRACT else None
    if i - 21 < 0 or i + 11 >= len(cal[prod]):
        return None, "window extends beyond price data span"
    win = cal[prod][i - 21:i + 12]
    end11 = win[-1]
    roll_soon = ((roll_dates[prod] > d) & (roll_dates[prod] <= end11)).any()
    fallback = False
    if roll_soon:
        if fwd is None:
            return None, "roll imminent but no FORWARD contract available"
        sel = fwd
    series = cseries[prod].get(sel, {})
    missing = [x for x in win if x not in series]
    if missing and (not roll_soon) and fwd is not None and fwd != sel:
        fseries = cseries[prod].get(fwd, {})
        if all(x in fseries for x in win):
            sel, series, missing, fallback = fwd, fseries, [], True
    if missing:
        return None, "incomplete window"
    if prod == "HG" and sel[4:6] == "05":
        return None, "HG May contract (A4 substitution rule; cannot occur from PRICE/FORWARD)"
    return dict(sel=sel, series=series, win=win, fallback=fallback), None


def trailing_fields(series, win):
    """trailing 20-td log return and annualized vol at win[21] (committed formulas)"""
    idx = 21
    p_entry = series[win[idx]]
    p_lag = series[win[idx - 20]]
    logrets = [math.log(series[win[k]] / series[win[k - 1]]) for k in range(idx - 19, idx + 1)]
    tr = math.log(p_entry / p_lag)
    tv = float(np.std(logrets, ddof=1) * math.sqrt(252))
    return tr, tv


def trade_return_bps(series, win, direction):
    """A4 pseudo-trade: entry at settlement win[21], exit at win[31] (t0+10 td),
    one unit notional, no stops; 10-day log return in bps, direction-adjusted"""
    return direction * math.log(series[win[31]] / series[win[21]]) * 1e4


# ============ PART B STEP 2 — reproduce Stage-1 selection; assert vs committed record ============
events = []
for r in h2_inc.itertuples(index=False):
    selres, reason = a4_at(r.product, r.entry_date)
    assert selres is not None, f"{r.product} {r.entry_date}: selection failed in H2 run ({reason})"
    assert selres["sel"] == r.selected_contract, \
        f"{r.product} {r.entry_date}: contract {selres['sel']} != committed {r.selected_contract}"
    assert bool(selres["fallback"]) == bool(r.completeness_fallback), \
        f"{r.product} {r.entry_date}: fallback flag mismatch"
    tr, tv = trailing_fields(selres["series"], selres["win"])
    assert abs(tr - float(r.trailing_return)) < 1e-9 and abs(tv - float(r.trailing_vol)) < 1e-9, \
        f"{r.product} {r.entry_date}: trailing fields deviate from committed record"
    assert tr != 0.0
    direction = 1.0 if tr > 0 else -1.0        # H2 direction rule: +sign(trailing)
    events.append(dict(product=r.product, entry=r.entry_date, effective=r.effective_date,
                       contract=selres["sel"], series=selres["series"], win=selres["win"],
                       trailing=tr, vol=tv, direction=direction,
                       ret_bps=trade_return_bps(selres["series"], selres["win"], direction),
                       entry_price=selres["series"][r.entry_date],
                       cluster_week=r.cluster_week))
print(f"Stage-1 reproduction check: all {len(events)} H2 events match the committed "
      f"events_v3.csv (contract, fallback flag, trailing return, trailing vol)")

# ============ A5 candidate control days (H2 window) ============
m = pd.read_csv(DATA / "margin_history_stitched.csv")
m = m[m["product"].isin(PRODUCTS)].sort_values(["product", "effective_date"])

def margin_excluded_days(prod):
    """trading days within +/-15 trading days of ANY margin change (any direction,
    any size); change date snapped to first trading day on/after it"""
    g = m[m["product"] == prod].sort_values("effective_date")
    lv = g.maintenance.astype(float)
    chg = [d for d, v in zip(g.effective_date, lv.pct_change()) if v == v and v != 0.0]
    c_ = cal[prod]
    excl = set()
    for cdate in chg:
        later = [x for x in c_ if x >= cdate]      # changes after the price calendar end cannot
        if not later:                              # be within 15 td of a sample day; skip
            continue
        i = calpos[prod][later[0]]
        for j in range(i - 15, i + 16):
            if 0 <= j < len(c_):
                excl.add(c_[j])
    return excl


cands = {}
pool_stats = {}
for prod in sorted(PRODUCTS):
    excl = margin_excluded_days(prod)
    days_in_window = [d for d in cal[prod] if H2_START <= d <= H2_END]
    rows, n_excl, n_nosel, n_zerotrail, n_fb = [], 0, 0, 0, 0
    for d in days_in_window:
        if d in excl:
            n_excl += 1
            continue
        selres, _ = a4_at(prod, d)
        if selres is None:
            n_nosel += 1
            continue
        tr, tv = trailing_fields(selres["series"], selres["win"])
        if tr == 0.0:
            n_zerotrail += 1
            continue
        direction = 1.0 if tr > 0 else -1.0    # H2 direction rule for control pseudo-trades
        n_fb += selres["fallback"]
        rows.append((d, tv, 1.0 if tr > 0 else -1.0,
                     trade_return_bps(selres["series"], selres["win"], direction)))
    cands[prod] = pd.DataFrame(rows, columns=["date", "vol", "trail_sign", "ret_bps"])
    pool_stats[prod] = dict(window_days=len(days_in_window), margin_excluded=n_excl,
                            unselectable=n_nosel, zero_trailing=n_zerotrail,
                            candidates=len(rows), fallback_selections=n_fb)
    print(f"  control pool {prod} [{H2_START} -> {H2_END}]: {len(days_in_window)} trading days, "
          f"{n_excl} within +/-15 td of a margin change, {n_nosel} unselectable/incomplete, "
          f"{n_zerotrail} zero-trailing -> {len(rows)} candidates ({n_fb} via completeness fallback)")

ev_entries = {(e["product"], e["entry"]) for e in events}
for prod in sorted(PRODUCTS):
    overlap = [d for d in cands[prod].date if (prod, d) in ev_entries]
    assert not overlap, f"candidate day coincides with an event entry: {prod} {overlap}"

# ---------------- A5 matching: k=10 nearest by |log vol ratio|, ties to earlier dates ----------------
n_widened = 0
for e in events:
    c = cands[e["product"]]
    sign = 1.0 if e["trailing"] > 0 else -1.0
    same = c[c.trail_sign == sign]
    ratio = same.vol / e["vol"]
    sel = same[(ratio >= 0.80) & (ratio <= 1.25)]
    e["widened"] = False
    if len(sel) < 5:
        sel = same[(ratio >= 0.70) & (ratio <= 1.43)]
        e["widened"] = True
        n_widened += 1
    if len(sel) < 5:
        e["controls"] = None      # unmatched: dropped from matched comparison, stays in G
        continue
    key = sel.assign(alr=(np.log(sel.vol / e["vol"])).abs()).sort_values(["alr", "date"])
    e["controls"] = key.head(10)

matched = [e for e in events if e["controls"] is not None]
unmatched = [e for e in events if e["controls"] is None]
unmatched_pct = 100.0 * len(unmatched) / len(events)

# ============ PART B STEP 3 — statistics ============
G = float(np.mean([e["ret_bps"] for e in events]))
for e in matched:
    e["ctrl_mean"] = float(e["controls"].ret_bps.mean())
    e["diff"] = e["ret_bps"] - e["ctrl_mean"]
D = float(np.mean([e["diff"] for e in matched]))

# monthly-block bootstrap on D, 10,000 draws, seed 42
months = sorted({e["entry"][:7] for e in matched})
by_month = {mo: np.array([e["diff"] for e in matched if e["entry"][:7] == mo]) for mo in months}
month_arrays = [by_month[mo] for mo in months]
M = len(month_arrays)
boot = np.empty(10000)
for b in range(10000):
    pick = RNG.integers(0, M, M)
    boot[b] = float(np.concatenate([month_arrays[j] for j in pick]).mean())
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])

# secondary (reported only): vol-standardized return
for e in events:
    e["z"] = (e["ret_bps"] / 1e4) / (e["vol"] * math.sqrt(10 / 252))
Gz = float(np.mean([e["z"] for e in events]))
Dz = float(np.mean([(e["ret_bps"] - e["ctrl_mean"]) / 1e4 / (e["vol"] * math.sqrt(10 / 252))
                    for e in matched]))

# C3 decay split (R5): matched events by entry_date at 2021-01-01
m_early = [e for e in matched if e["entry"] < SPLIT]
m_recent = [e for e in matched if e["entry"] >= SPLIT]
D_early = float(np.mean([e["diff"] for e in m_early])) if m_early else float("nan")
D_recent = float(np.mean([e["diff"] for e in m_recent])) if m_recent else float("nan")

# C4 concentration floor (R6): additive per-product contributions to D
contrib = {p: float(np.sum([e["diff"] for e in matched if e["product"] == p])) for p in sorted(PRODUCTS)}
max_abs = max(abs(v) for v in contrib.values())
tied = [p for p, v in contrib.items() if abs(v) == max_abs]
def _d_excl(p):
    rest = [e["diff"] for e in matched if e["product"] != p]
    return float(np.mean(rest)) if rest else float("nan")
top_prod = min(tied, key=lambda p: (_d_excl(p) if _d_excl(p) == _d_excl(p) else float("-inf")))
D_ex = _d_excl(top_prod)
n_ex = len([e for e in matched if e["product"] != top_prod])

# leave-one-crisis-out (fragility, non-fatal; R9)
loco = {}
for yr in ("2020", "2022"):
    rest = [e["diff"] for e in matched if e["entry"][:4] != yr]
    loco[yr] = dict(D=float(np.mean(rest)) if rest else float("nan"),
                    n=len(rest), dropped=len(matched) - len(rest))
    loco[yr]["sign_flip"] = (loco[yr]["D"] * D < 0) if rest and D == D else False

# ---------------- per-product table ----------------
prod_rows = []
for prod in sorted(PRODUCTS):
    pe = [e for e in events if e["product"] == prod]
    pm = [e for e in pe if e["controls"] is not None]
    prod_rows.append(dict(
        product=prod, events=len(pe), matched=len(pm), unmatched=len(pe) - len(pm),
        widened=sum(e["widened"] for e in pe),
        G_bps=float(np.mean([e["ret_bps"] for e in pe])) if pe else float("nan"),
        ctrl_bps=float(np.mean([e["ctrl_mean"] for e in pm])) if pm else float("nan"),
        D_bps=float(np.mean([e["diff"] for e in pm])) if pm else float("nan")))

# ---------------- cost table ----------------
cost_rows = []
for prod in sorted(PRODUCTS):
    pe = [e for e in events if e["product"] == prod]
    med_px = float(np.median([e["entry_price"] for e in pe]))
    tick_bps = TICK[prod] / med_px * 1e4
    rt = 2 * (tick_bps + FEES_BPS_PER_SIDE)
    stress = rt + tick_bps
    cost_rows.append(dict(product=prod, tick=TICK[prod], median_entry_price=med_px,
                          tick_bps=tick_bps, rt_bps=rt, stress_bps=stress,
                          G_bps=float(np.mean([e["ret_bps"] for e in pe])),
                          G_net_stress=float(np.mean([e["ret_bps"] for e in pe])) - stress))
ev_costs = [3 * (TICK[e["product"]] / e["entry_price"] * 1e4) + 2 * FEES_BPS_PER_SIDE for e in events]
pooled_stress = float(np.mean(ev_costs))

# ---------------- event-time plot (-15..+15, events vs matched controls) ----------------
def path(prod, series, day, direction):
    i = calpos[prod][day]
    p0 = series[day]
    out = np.full(31, np.nan)
    for k, lag in enumerate(range(-15, 16)):
        j = i + lag
        if 0 <= j < len(cal[prod]):
            d = cal[prod][j]
            if d in series:
                out[k] = direction * math.log(series[d] / p0) * 1e4
    return out

ev_paths = np.array([path(e["product"], e["series"], e["entry"], e["direction"]) for e in events])
ctrl_paths = []
for e in matched:
    for d in e["controls"].date:
        selres, _ = a4_at(e["product"], d)
        tr, _ = trailing_fields(selres["series"], selres["win"])
        direction = 1.0 if tr > 0 else -1.0    # H2 direction rule
        ctrl_paths.append(path(e["product"], selres["series"], d, direction))
ctrl_paths = np.array(ctrl_paths)

lags = np.arange(-15, 16)
ev_mean = np.nanmean(ev_paths, axis=0)
ct_mean = np.nanmean(ctrl_paths, axis=0)
ev_n = np.sum(~np.isnan(ev_paths), axis=0)
ct_n = np.sum(~np.isnan(ctrl_paths), axis=0)

fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
ax.axhline(0, color="#c9c8c0", lw=1)
ax.axvline(0, color="#c9c8c0", lw=1, ls="--")
ax.axvline(10, color="#c9c8c0", lw=0.8, ls=":")
ax.plot(lags, ev_mean, color="#2a78d6", lw=2, label=f"events (n={len(events)})")
ax.plot(lags, ct_mean, color="#eb6834", lw=2, label=f"matched control pseudo-trades (n={len(ctrl_paths)})")
ax.annotate("events", (lags[-1], ev_mean[-1]), xytext=(4, 0), textcoords="offset points",
            color="#2a78d6", fontsize=9, va="center")
ax.annotate("controls", (lags[-1], ct_mean[-1]), xytext=(4, 0), textcoords="offset points",
            color="#eb6834", fontsize=9, va="center")
ax.annotate("entry", (0, ax.get_ylim()[1]), xytext=(3, -12), textcoords="offset points",
            color="#8a8a82", fontsize=8)
ax.annotate("exit (+10)", (10, ax.get_ylim()[1]), xytext=(3, -12), textcoords="offset points",
            color="#8a8a82", fontsize=8)
ax.set_xlabel("trading days relative to entry")
ax.set_ylabel("mean direction-adjusted cumulative log return (bps)")
ax.set_title("H2 one-shot event-time paths — events vs vol-matched controls\n"
             f"window: {H2_START} → {H2_END} (5-product universe, SI conduct-excluded); "
             "direction = +sign(trailing 20-td return)",
             fontsize=10)
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)
for s in ["left", "bottom"]:
    ax.spines[s].set_color("#c9c8c0")
ax.tick_params(colors="#55554f")
ax.grid(axis="y", color="#eceae2", lw=0.7)
ax.set_axisbelow(True)
fig.text(0.01, 0.01,
         f"direction = +sign(trailing 20-td return); paths normalized to 0 at entry; "
         f"A4 window completeness guarantees lags −15..+11; coverage at +15: "
         f"events {ev_n[-1]}/{len(events)}, controls {ct_n[-1]}/{len(ctrl_paths)}",
         fontsize=7, color="#8a8a82")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(REPO / "h2_event_time.png", facecolor="#fcfcfb")
plt.close(fig)

# ============ PART B STEP 4 — verdict against C1, C2, C3, C4 in order ============
c1 = D >= 15.0
c2 = G >= 10.0
c3 = (len(m_early) > 0 and len(m_recent) > 0
      and D_recent >= 10.0 and D_recent >= 0.4 * D_early)
c4 = (n_ex > 0) and (D_ex >= 5.0)

print("=" * 78)
print(f"H2 ONE-SHOT VERDICT [entry {H2_START} -> {H2_END}; 5-product universe]")
print(f"  events: {len(events)} included; matched: {len(matched)}; unmatched: {len(unmatched)} "
      f"({unmatched_pct:.1f}%){' — FRAGILITY FLAG (>20% unmatched)' if unmatched_pct > 20 else ''}")
print(f"  D (event minus matched-control mean) = {D:.2f} bps; 95% bootstrap CI [{ci_lo:.2f}, {ci_hi:.2f}] "
      f"(monthly blocks, {M} months, 10,000 draws)")
print(f"  G (mean event return)               = {G:.2f} bps")
print(f"  split: D(2015–2020) = {D_early:.2f} bps over {len(m_early)} matched; "
      f"D(2021–2024.03) = {D_recent:.2f} bps over {len(m_recent)} matched")
print(f"  concentration: per-product contribution to D (sum of diffs, bps): "
      + ", ".join(f"{p}={v:.1f}" for p, v in contrib.items()))
print(f"  largest |contribution|: {top_prod}; D excluding {top_prod} = {D_ex:.2f} bps over {n_ex} matched")
print(f"  C1 (vol test):            D = {D:.2f} bps vs >= +15 bps -> {'PASS' if c1 else 'FAIL'}")
print(f"  C2 (cost test):           G = {G:.2f} bps vs >= +10 bps -> {'PASS' if c2 else 'FAIL'}")
print(f"  C3 (decay test):          D(2021–2024.03) = {D_recent:.2f} bps vs >= +10 bps AND "
      f">= 40% of D(2015–2020) (= {0.4 * D_early:.2f} bps) -> {'PASS' if c3 else 'FAIL'}")
print(f"  C4 (concentration floor): D excluding {top_prod} = {D_ex:.2f} bps vs >= +5 bps -> "
      f"{'PASS' if c4 else 'FAIL'}")
for yr in ("2020", "2022"):
    print(f"  fragility (non-fatal): drop {yr} -> D = {loco[yr]['D']:.2f} bps "
          f"({loco[yr]['dropped']} events dropped){' — SIGN FLIP' if loco[yr]['sign_flip'] else ''}")

fail_clauses = []
if not c1:
    fail_clauses.append(f"C1 vol test: D = {D:.1f} bps vs. +15 bps")
if not c2:
    fail_clauses.append(f"C2 cost test: G = {G:.1f} bps vs. +10 bps")
if not c3:
    fail_clauses.append(f"C3 decay test: D(2021–2024.03) = {D_recent:.1f} bps vs. +10 bps and "
                        f"40% of D(2015–2020) = {0.4 * D_early:.1f} bps")
if not c4:
    fail_clauses.append(f"C4 concentration floor: D excluding {top_prod} = {D_ex:.1f} bps vs. +5 bps")

all_pass = not fail_clauses
if all_pass:
    first = (f"The continuation strategy passed all four preregistered criteria on previously untouched "
             f"2015–2024 data: D={D:.1f} bps, G={G:.1f} bps, D_recent={D_recent:.1f} bps, "
             f"D_ex-top={D_ex:.1f} bps.")
else:
    first = H5_TEMPLATE.format(fails="; ".join(fail_clauses))
    (REPO / "H2_FAIL").write_text(first + "\n")
    print("H2_FAIL written.")
print(first)

# ============ PART B STEP 5 — h2_results.md ============
def fmt(x, nd=1):
    return f"{x:.{nd}f}"

lines = []
lines.append(first)
lines.append("")
lines.append("# H2 Results — Preregistration H2 v1.0, One-Shot Continuation Test")
lines.append("")
lines.append("Sample window (every table below unless stated): entry dates 2015-01-01 → 2024-03-28, "
             "committed events_v3.csv, 5-product universe ZN, 6E, 6J, GC, HG (SI conduct-excluded per "
             "the Stage-1 record; attrition only). Direction: +sign(trailing 20-td return) — continuation. "
             "This sample had never been loaded, summarized, plotted, or viewed before this run; this was "
             "its single, final use (H0/H4). No amendments were made; ambiguities were resolved by the "
             "strictest reading and are logged below and in scripts/h2_oneshot.py.")
lines.append("")
lines.append("## Verdict against preregistered kill criteria (H3, in order)")
lines.append("")
lines.append("| Criterion | Preregistered threshold | Measured | Verdict |")
lines.append("|---|---|---|---|")
lines.append(f"| C1: D (event − matched-control mean) | ≥ +15 bps | {fmt(D,2)} bps | {'PASS' if c1 else 'FAIL'} |")
lines.append(f"| C2: G (mean event return, gross) | ≥ +10 bps | {fmt(G,2)} bps | {'PASS' if c2 else 'FAIL'} |")
lines.append(f"| C3: D(2021–2024.03) | ≥ +10 bps AND ≥ 40% of D(2015–2020) (= {fmt(0.4*D_early,2)} bps) | "
             f"{fmt(D_recent,2)} bps | {'PASS' if c3 else 'FAIL'} |")
lines.append(f"| C4: D excluding {top_prod} (largest \\|contribution\\|) | ≥ +5 bps | {fmt(D_ex,2)} bps | "
             f"{'PASS' if c4 else 'FAIL'} |")
lines.append("")
lines.append(f"- **D = {fmt(D,2)} bps**, 95% interval **[{fmt(ci_lo,2)}, {fmt(ci_hi,2)}] bps** "
             f"(monthly-block bootstrap, {M} blocks, 10,000 draws, seed 42).")
lines.append(f"- **G = {fmt(G,2)} bps** over all {len(events)} included events "
             f"(unmatched events remain in G; they are dropped only from the matched comparison).")
lines.append(f"- Unmatched: **{len(unmatched)}/{len(events)} ({fmt(unmatched_pct)}%)**"
             + (" — **FRAGILITY FLAG: >20% unmatched (A5); this flag cannot be removed by re-matching.**"
                if unmatched_pct > 20 else " (no A5 fragility flag; threshold 20%)."))
lines.append(f"- Caliper widened once to [0.70, 1.43] for {n_widened} events (A5 no-match protocol).")
lines.append(f"- Secondary, reported only: vol-standardized mean event return {fmt(Gz,3)}; "
             f"vol-standardized matched differential {fmt(Dz,3)} "
             f"(10-day log return ÷ trailing vol·√(10/252)).")
lines.append("")
lines.append("## C3 decay split (entry-date split at 2021-01-01)")
lines.append("")
lines.append("| Segment | Matched events | D (bps) |")
lines.append("|---|---|---|")
lines.append(f"| 2015-01-01 → 2020-12-31 | {len(m_early)} | {fmt(D_early,2)} |")
lines.append(f"| 2021-01-01 → 2024-03-28 | {len(m_recent)} | {fmt(D_recent,2)} |")
lines.append("")
lines.append(f"Retention: D_recent / D_early = "
             + (f"{fmt(100*D_recent/D_early)}%" if D_early == D_early and D_early != 0 else "n/a")
             + f"; thresholds: D_recent ≥ +10 bps and ≥ 40% of D_early.")
lines.append("")
lines.append("## C4 concentration floor")
lines.append("")
lines.append("Contribution of product p to D = Σ over p's matched events of (event − control-mean), "
             "i.e. n_p·D_p; D = Σ_p contribution_p / N_matched (strictest-reading log R6).")
lines.append("")
lines.append("| Product | Matched events | D_p (bps) | Contribution Σdiff (bps) |")
lines.append("|---|---|---|---|")
for p in sorted(PRODUCTS):
    pm = [e for e in matched if e["product"] == p]
    dp = float(np.mean([e['diff'] for e in pm])) if pm else float("nan")
    lines.append(f"| {p} | {len(pm)} | {fmt(dp,2) if pm else 'n/a'} | {fmt(contrib[p],1)} |")
lines.append("")
lines.append(f"Largest absolute contribution: **{top_prod}**. D excluding {top_prod}: "
             f"**{fmt(D_ex,2)} bps** over {n_ex} matched events (threshold ≥ +5 bps).")
lines.append("")
lines.append("## Leave-one-crisis-out (fragility, non-fatal per H3)")
lines.append("")
lines.append("| Dropped year (entry dates) | Events dropped | D (bps) | Sign flip vs full D |")
lines.append("|---|---|---|---|")
for yr in ("2020", "2022"):
    lines.append(f"| {yr} | {loco[yr]['dropped']} | {fmt(loco[yr]['D'],2)} | "
                 f"{'YES — FRAGILITY FLAG' if loco[yr]['sign_flip'] else 'no'} |")
lines.append("")
lines.append("## Per-product table")
lines.append("")
lines.append("| Product | Events | Matched | Unmatched | Caliper widened | G (bps) | Control mean (bps) | D (bps) |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in prod_rows:
    lines.append(f"| {r['product']} | {r['events']} | {r['matched']} | {r['unmatched']} | {r['widened']} | "
                 f"{fmt(r['G_bps'])} | {fmt(r['ctrl_bps'])} | {fmt(r['D_bps'])} |")
lines.append(f"| **All** | {len(events)} | {len(matched)} | {len(unmatched)} | {n_widened} | "
             f"{fmt(G)} | {fmt(float(np.mean([e['ctrl_mean'] for e in matched])))} | {fmt(D)} |")
lines.append("")
lines.append("## Cost table (A6 model)")
lines.append("")
lines.append("Model: 2 × (1 tick half-spread + 0.2 bps fees) per round trip; entry side +1 tick stress "
             "penalty. Tick specs are the committed stage2_v3.py hard-coded values (conservative for "
             "2015–2024; log R7). Tick bps at the median sample entry price. Context only; C2's threshold "
             "is fixed at +10 bps gross.")
lines.append("")
lines.append("| Product | Tick (price units) | Median entry price | 1 tick (bps) | Round trip (bps) | "
             "Stress-adjusted (bps) | G (bps) | G − stress cost (bps) |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in cost_rows:
    lines.append(f"| {r['product']} | {r['tick']:g} | {r['median_entry_price']:g} | {fmt(r['tick_bps'],2)} | "
                 f"{fmt(r['rt_bps'],2)} | {fmt(r['stress_bps'],2)} | {fmt(r['G_bps'])} | {fmt(r['G_net_stress'])} |")
lines.append(f"\nEvent-weighted pooled stress-adjusted round-trip cost (each event at its own entry price): "
             f"**{fmt(pooled_stress,2)} bps**.")
lines.append("")
lines.append("## Event-time plot")
lines.append("")
lines.append("![H2 event-time paths](h2_event_time.png)")
lines.append("")
lines.append(f"Mean direction-adjusted cumulative log return (bps), lags −15..+15 trading days, normalized "
             f"to 0 at entry; {len(events)} events vs {len(ctrl_paths)} matched control pseudo-trades "
             f"(pooled over event–control pairs, controls reusable per A5). A4 completeness guarantees "
             f"lags −15..+11; beyond +11 coverage declines (at +15: events {ev_n[-1]}/{len(events)}, "
             f"controls {ct_n[-1]}/{len(ctrl_paths)}); no imputation — per-lag available means.")
lines.append("")
lines.append("## Sample, attrition, and matching diagnostics")
lines.append("")
lines.append("Reported before any return was computed (Part B step 1):")
lines.append("")
lines.append("| Product | Events in window | Included (A4 survivors) | Excluded |")
lines.append("|---|---|---|---|")
for r in count_rows:
    lines.append(f"| {r['product']} | {r['in_window']} | {r['included']} | {r['excluded']} |")
lines.append(f"| **Total (5-product)** | {len(h2)} | {len(h2_inc)} | {len(h2) - len(h2_inc)} |")
lines.append("")
lines.append(f"- Sample floor: {n_sample} included events vs preregistered minimum 40 — PASS.")
lines.append(f"- SI (conduct-excluded in Stage 1, price-series identity unresolved): {len(si_h2)} events in "
             f"window, {int(si_h2.included_flag.sum())} with complete windows — attrition only; no SILVER "
             f"price was loaded and no SI return was computed in this session.")
lines.append(f"- Excluded-event reasons (5-product universe): {excl_reasons if excl_reasons else 'none'}.")
lines.append(f"- A4 completeness-fallback events in sample: {int(h2_inc.completeness_fallback.sum())}.")
lines.append(f"- Entry-vs-effective window-membership deviations (log R2): {len(straddlers)}.")
lines.append("- Control-day pools (A5, under the amended A4 selection including the completeness fallback):")
lines.append("")
lines.append("| Product | Trading days in window | ±15 td of a margin change | Unselectable/incomplete | "
             "Zero trailing | Candidates | Fallback selections |")
lines.append("|---|---|---|---|---|---|---|")
for prod in sorted(PRODUCTS):
    s = pool_stats[prod]
    lines.append(f"| {prod} | {s['window_days']} | {s['margin_excluded']} | {s['unselectable']} | "
                 f"{s['zero_trailing']} | {s['candidates']} | {s['fallback_selections']} |")
lines.append("")
n_ctrl_counts = collections.Counter(len(e["controls"]) for e in matched)
lines.append(f"- Matched controls per event: {dict(sorted(n_ctrl_counts.items(), reverse=True))} "
             f"(k = 10 nearest by |log vol ratio|, ties to earlier dates; controls reusable).")
uniq_ctrl = len({(e['product'], d) for e in matched for d in e['controls'].date})
lines.append(f"- Distinct control days used: {uniq_ctrl} across {sum(len(e['controls']) for e in matched)} "
             f"event–control pairs.")
lines.append(f"- Stage-1 reproduction: every event's selected contract, fallback flag, trailing return, and "
             f"trailing vol asserted equal to the committed events_v3.csv (log R4).")
lines.append("")
lines.append("## Strictest-reading log and containment (H4)")
lines.append("")
lines.append("1. **One run.** This script ran once; its printout is final. No exploratory computation of "
             "any kind was performed in this session.")
lines.append("2. **Containment.** The 2015-01-01 → 2024-03-28 sample was loaded for the first time ever in "
             "this run. Prices loaded 2014-10-01 → 2024-03-28 — the minimum covering [entry−21, entry+11] "
             "windows and −15..+15 plot lags of early-2015 entries and the ±15-td margin-change exclusion "
             "look-back at the boundary (log R3). Pre-2015 days are never events and never control "
             "candidates; burned pilot data entered only as A4/A5-required trailing context.")
lines.append("3. **Sample floor** counted included (A4-surviving) events in the 5-product universe — the "
             "events actually analyzed (log R1).")
lines.append("4. **C3** split by entry_date at 2021-01-01; both sub-conditions required; an empty segment "
             "would have failed C3 (log R5).")
lines.append("5. **C4 contribution** = additive share Σdiff (= n_p·D_p); ties (none occurred) would break "
             "toward the lower recomputed D (log R6).")
lines.append("6. **Ticks** reused from the committed stage2_v3.py hard-coding — conservative for this era "
             "(log R7). **G** includes unmatched events (log R10). **Bootstrap** monthly blocks, seed 42, "
             "10,000 draws (log R11). **LOCO** by entry-date calendar year (log R9).")
lines.append("7. **H5 sentence** lists every failed criterion with measured value vs. threshold (log R8).")
lines.append("8. **Margin-change exclusion**: changes of any size and either direction; change dates snapped "
             "to the first trading day on/after the effective date. Changes before the price-calendar start "
             "cannot reach the candidate window (calendar begins 2014-10-01; candidates begin 2015-01-01).")
lines.append("")
lines.append("## Genealogy and closure (H0/H4/H5)")
lines.append("")
lines.append("This study's motivation was the preregistered FAILURE of the reversal hypothesis on 2000–2014 "
             "pilot data (commit ebda726: D = −17.1 bps vs +15, G = +3.1 bps vs +10). The pre-2015 data is "
             "burned; the reversal hypothesis may not be re-tested on any data. "
             + ("All four criteria passed on this study's one-shot run; the H2 record stands as printed. "
                "Per H4, no threshold, rule, window, universe, matching parameter, or definition was changed "
                "at any point."
                if all_pass else
                "This one-shot run failed; per H4 there is no v1.1, no re-test, and no third hypothesis: "
                "no margin-based strategy of any kind will be pitched. The two-sided preregistered result — "
                "reversal dead on 2000–2014, continuation dead on 2015–2024 — is itself the finding: CME "
                "margin-increase events carry no exploitable multi-day return signal in either direction "
                "beyond volatility."))
lines.append("")

(REPO / "h2_results.md").write_text("\n".join(lines))
print("h2_results.md written. H2 one-shot complete — no further runs of any kind in this session.")
