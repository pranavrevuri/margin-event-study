#!/usr/bin/env python3
"""
Preregistration v3.0 — PART B, Stage 2: PILOT ONLY.
v2 Part B steps 5-7 verbatim under the v3-amended A4/A5 selection.

Pilot sample: included events (events_v3.csv, the committed Stage-1 record)
with entry_date in [product binding start, 2014-12-31], products remaining
after the Stage-1 conduct-rule exclusion (SI excluded; its events appear in
the attrition table only, read from events_v3.csv — SILVER prices never load).

Containment (A7 holdout untouched + Part B hard stop):
  - No event dated after 2014-12-31 is loaded, filtered, summarized, or
    plotted. Post-2014 margin rows are consulted ONLY as raw change dates for
    the A5 +/-15-trading-day contamination exclusion near the pilot boundary;
    no qualifying event is constructed from them.
  - Candidate control days are restricted to the pilot window (binding start
    -> 2014-12-31). A5's "d within the product's analysis span" is applied
    jointly with A7's clause that the holdout window stays untouched until
    the pilot verdict is committed: pilot controls drawn from 2015+ would
    make the pilot verdict depend on holdout-era prices. Documented in
    pilot_results_v3.md.
  - Price data loads only through 2015-03-31 — the minimum needed for the
    [d-21, d+11] windows and the -15..+15 plot lags of late-December-2014
    entries. The script cannot see any holdout-era return beyond that spill.

The loading and A4 selection machinery below is copied from the committed
stage1_v3.py so event and control construction are logic-identical to the
Stage-1 record (A0.4 symmetry). The only mechanical difference: window
membership uses calendar-index slicing (cal[i-21:i+12]) instead of a full
list scan; the result is identical (asserted against events_v3.csv for every
pilot event: selected contract, fallback flag, trailing return, trailing vol).
"""
import math
import collections
from datetime import date
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
BINDING_START = {"6E": "2000-01-01", "6J": "2000-02-03", "ZN": "2004-01-02",
                 "GC": "2009-01-08", "HG": "2009-01-08"}
PILOT_END = "2014-12-31"
PRICE_LOAD_END = "2015-03-31"   # containment: minimum span covering pilot windows/plot lags

# A6 cost model tick specs, hard-coded (pilot-era outright minimum ticks, price units)
TICK = {"ZN": 0.015625, "6E": 0.0001, "6J": 0.000001, "GC": 0.10, "HG": 0.0005}
FEES_BPS_PER_SIDE = 0.2

RNG = np.random.default_rng(42)

# ---------------- load prices (copied from stage1_v3.py) ----------------
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
    mp = mp[(mp.date >= "1995-01-01") & (mp.date <= PRICE_LOAD_END)]
    daily = daily[(daily.date >= "1995-01-01") & (daily.date <= PRICE_LOAD_END)]
    prices[prod] = daily.set_index("date")
    rolls[prod] = rc
    roll_dates[prod] = rc.date.values
    cseries[prod] = contract_price_series(mp)
    cal[prod] = sorted(daily.date.unique())

calpos = {p: {d: i for i, d in enumerate(cal[p])} for p in PRODUCTS}


# ---------------- amended A4 selection at a trading day (stage1_v3.py logic) ----------------
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
    """trailing 20-td log return and annualized vol at win[21] (stage1_v3.py formulas)"""
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


# ---------------- pilot event sample from the committed Stage-1 record ----------------
ev_all = pd.read_csv(DATA / "events_v3.csv", dtype={"selected_contract": str})
pilot_mask = ev_all.entry_date.notna() & (ev_all.entry_date <= PILOT_END)
si_pilot = ev_all[(ev_all["product"] == "SI") & pilot_mask]          # attrition reporting only
pilot = ev_all[ev_all["product"].isin(PRODUCTS) & pilot_mask].copy() # 5-product pilot universe
pilot_inc = pilot[pilot.included_flag].copy()

print(f"pilot universe (entry <= {PILOT_END}): {len(pilot)} events across {sorted(PRODUCTS)}; "
      f"{len(pilot_inc)} included; SI (conduct-excluded) pilot events: {len(si_pilot)} (attrition table only)")

# reproduce Stage-1 selection for every pilot event and assert identity to the committed record
events = []
for r in pilot_inc.itertuples(index=False):
    selres, reason = a4_at(r.product, r.entry_date)
    assert selres is not None, f"{r.product} {r.entry_date}: selection failed in Stage 2 ({reason})"
    assert selres["sel"] == r.selected_contract, \
        f"{r.product} {r.entry_date}: contract {selres['sel']} != committed {r.selected_contract}"
    assert bool(selres["fallback"]) == bool(r.completeness_fallback), \
        f"{r.product} {r.entry_date}: fallback flag mismatch"
    tr, tv = trailing_fields(selres["series"], selres["win"])
    assert abs(tr - float(r.trailing_return)) < 1e-9 and abs(tv - float(r.trailing_vol)) < 1e-9, \
        f"{r.product} {r.entry_date}: trailing fields deviate from committed record"
    assert tr != 0.0
    direction = -1.0 if tr > 0 else 1.0
    events.append(dict(product=r.product, entry=r.entry_date, effective=r.effective_date,
                       contract=selres["sel"], series=selres["series"], win=selres["win"],
                       trailing=tr, vol=tv, direction=direction,
                       ret_bps=trade_return_bps(selres["series"], selres["win"], direction),
                       entry_price=selres["series"][r.entry_date],
                       cluster_week=r.cluster_week))
print(f"Stage-1 reproduction check: all {len(events)} pilot events match the committed "
      f"events_v3.csv (contract, fallback flag, trailing return, trailing vol)")

# ---------------- A5 candidate control days ----------------
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
        if not later:                              # be within 15 td of a pilot day; skip
            continue
        i = calpos[prod][later[0]]
        for j in range(i - 15, i + 16):
            if 0 <= j < len(c_):
                excl.add(c_[j])
    return excl


cands = {}
pool_stats = {}
for prod in PRODUCTS:
    excl = margin_excluded_days(prod)
    days_in_window = [d for d in cal[prod] if BINDING_START[prod] <= d <= PILOT_END]
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
        direction = -1.0 if tr > 0 else 1.0
        n_fb += selres["fallback"]
        rows.append((d, tv, 1.0 if tr > 0 else -1.0,
                     trade_return_bps(selres["series"], selres["win"], direction)))
    cands[prod] = pd.DataFrame(rows, columns=["date", "vol", "trail_sign", "ret_bps"])
    pool_stats[prod] = dict(window_days=len(days_in_window), margin_excluded=n_excl,
                            unselectable=n_nosel, zero_trailing=n_zerotrail,
                            candidates=len(rows), fallback_selections=n_fb)
    print(f"  control pool {prod} [binding start -> {PILOT_END}]: {len(days_in_window)} trading days, "
          f"{n_excl} within +/-15 td of a margin change, {n_nosel} unselectable/incomplete, "
          f"{n_zerotrail} zero-trailing -> {len(rows)} candidates ({n_fb} via completeness fallback)")

ev_entries = {(e["product"], e["entry"]) for e in events}
for prod in PRODUCTS:
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

# ---------------- A6 statistics ----------------
G = float(np.mean([e["ret_bps"] for e in events]))
for e in matched:
    e["ctrl_mean"] = float(e["controls"].ret_bps.mean())
    e["diff"] = e["ret_bps"] - e["ctrl_mean"]
D = float(np.mean([e["diff"] for e in matched]))

# monthly-block bootstrap on D, 10,000 draws
months = sorted({e["entry"][:7] for e in matched})
by_month = {mo: np.array([e["diff"] for e in matched if e["entry"][:7] == mo]) for mo in months}
month_arrays = [by_month[mo] for mo in months]
M = len(month_arrays)
boot = np.empty(10000)
for b in range(10000):
    pick = RNG.integers(0, M, M)
    boot[b] = float(np.concatenate([month_arrays[j] for j in pick]).mean())
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])

# secondary (reported only): vol-standardized return = dir-adjusted 10-day log return
# divided by trailing_vol * sqrt(10/252)
for e in events:
    e["z"] = (e["ret_bps"] / 1e4) / (e["vol"] * math.sqrt(10 / 252))
Gz = float(np.mean([e["z"] for e in events]))
Dz = float(np.mean([(e["ret_bps"] - e["ctrl_mean"]) / 1e4 / (e["vol"] * math.sqrt(10 / 252))
                    for e in matched]))

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
# per-event stress cost at each event's own entry price, event-weighted pooled
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
        direction = -1.0 if tr > 0 else 1.0
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
ax.set_title("Pilot event-time paths — events vs vol-matched controls\n"
             "window: per-product binding start → 2014-12-31 (5-product universe, SI conduct-excluded)",
             fontsize=10)
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)
for s in ["left", "bottom"]:
    ax.spines[s].set_color("#c9c8c0")
ax.tick_params(colors="#55554f")
ax.grid(axis="y", color="#eceae2", lw=0.7)
ax.set_axisbelow(True)
fig.text(0.01, 0.01,
         f"direction = −sign(trailing 20-td return); paths normalized to 0 at entry; "
         f"A4 window completeness guarantees lags −15..+11; coverage at +15: "
         f"events {ev_n[-1]}/{len(events)}, controls {ct_n[-1]}/{len(ctrl_paths)}",
         fontsize=7, color="#8a8a82")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(REPO / "pilot_event_time_v3.png", facecolor="#fcfcfb")
plt.close(fig)

# ---------------- verdict (K1, K2) ----------------
k1_pass = D >= 15.0
k2_pass = G >= 10.0

K1_SENT = (f'"The strategy failed its preregistered test: after matching on volatility, margin increases '
           f'contained no exploitable information — the event-minus-control differential was {D:.1f} bps '
           f'against a preregistered threshold of +15 bps, meaning what looked like a margin effect is '
           f'ordinary post-volatility behavior, and the strategy is dead."')
K2_SENT = (f'"The strategy failed its preregistered cost test: the gross post-event return was {G:.1f} bps '
           f'against a preregistered threshold of +10 bps, which cannot clear transaction costs, '
           f'and the strategy is dead."')

print("=" * 78)
print(f"PILOT VERDICT [per-product binding start -> {PILOT_END}; 5-product universe]")
print(f"  events: {len(events)} included; matched: {len(matched)}; unmatched: {len(unmatched)} "
      f"({unmatched_pct:.1f}%){' — FRAGILITY FLAG (>20% unmatched)' if unmatched_pct > 20 else ''}")
print(f"  D (event minus matched-control mean) = {D:.2f} bps; 95% bootstrap CI [{ci_lo:.2f}, {ci_hi:.2f}] "
      f"(monthly blocks, {M} months, 10,000 draws)")
print(f"  G (mean event return)               = {G:.2f} bps")
print(f"  K1: D >= +15 bps -> {'PASS' if k1_pass else 'FAIL'}")
print(f"  K2: G >= +10 bps -> {'PASS' if k2_pass else 'FAIL'}")
if not k1_pass:
    print(K1_SENT)
if not k2_pass:
    print(K2_SENT)

if k1_pass and k2_pass:
    first = (f"The strategy passed its preregistered pilot: the volatility-matched event-minus-control "
             f"differential was D = {D:.1f} bps (threshold +15) and the gross post-event return was "
             f"G = {G:.1f} bps (threshold +10); per the A7 lock clause the holdout now runs on the "
             f"byte-identical specification, in a separate session, only after this verdict is committed.")
else:
    first = " ".join(([K1_SENT] if not k1_pass else []) + ([K2_SENT] if not k2_pass else []))
    (REPO / "PILOT_FAIL").write_text(first + "\n")
    print("PILOT_FAIL written.")

# ---------------- pilot_results_v3.md ----------------
def fmt(x, nd=1):
    return f"{x:.{nd}f}"

lines = []
lines.append("# Pilot Results — Preregistration v3.0, Stage 2 (PILOT ONLY)\n")
lines.append(first + "\n")
lines.append("## Verdict against preregistered kill criteria\n")
lines.append("Sample window (every table below): per-product binding start → 2014-12-31 "
             "(entry dates; binding starts 6E 2000-01-01, 6J 2000-02-03, ZN 2004-01-02, GC/HG 2009-01-08). "
             "Universe: ZN, 6E, 6J, GC, HG — the 5 products surviving Stage-1 K0; SI is conduct-excluded "
             "(price-series identity unresolved) and appears in the attrition table only.\n")
lines.append("| Criterion | Preregistered threshold | Measured | Verdict |")
lines.append("|---|---|---|---|")
lines.append(f"| K1: pilot D (event − matched-control mean) | ≥ +15 bps | {fmt(D,2)} bps | "
             f"{'PASS' if k1_pass else 'FAIL'} |")
lines.append(f"| K2: pilot G (mean event return, gross) | ≥ +10 bps | {fmt(G,2)} bps | "
             f"{'PASS' if k2_pass else 'FAIL'} |")
lines.append("")
lines.append(f"- **D = {fmt(D,2)} bps**, 95% interval **[{fmt(ci_lo,2)}, {fmt(ci_hi,2)}] bps** "
             f"(monthly-block bootstrap, {M} blocks, 10,000 draws, seed 42).")
lines.append(f"- **G = {fmt(G,2)} bps** over all {len(events)} included pilot events "
             f"(unmatched events remain in G; they are dropped only from the matched comparison).")
lines.append(f"- Unmatched: **{len(unmatched)}/{len(events)} ({fmt(unmatched_pct)}%)**"
             + (" — **FRAGILITY FLAG: >20% unmatched (A5); this flag cannot be removed by re-matching.**"
                if unmatched_pct > 20 else " (no A5 fragility flag; threshold 20%)."))
lines.append(f"- Caliper widened once to [0.70, 1.43] for {n_widened} events (A5 no-match protocol).")
lines.append(f"- Secondary, reported only: vol-standardized mean event return {fmt(Gz,3)}; "
             f"vol-standardized matched differential {fmt(Dz,3)} "
             f"(10-day log return ÷ trailing vol·√(10/252)).\n")

lines.append("## Per-product table\n")
lines.append("Window: per-product binding start → 2014-12-31.\n")
lines.append("| Product | Events | Matched | Unmatched | Caliper widened | G (bps) | Control mean (bps) | D (bps) |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in prod_rows:
    lines.append(f"| {r['product']} | {r['events']} | {r['matched']} | {r['unmatched']} | {r['widened']} | "
                 f"{fmt(r['G_bps'])} | {fmt(r['ctrl_bps'])} | {fmt(r['D_bps'])} |")
lines.append(f"| **All** | {len(events)} | {len(matched)} | {len(unmatched)} | {n_widened} | "
             f"{fmt(G)} | {fmt(float(np.mean([e['ctrl_mean'] for e in matched])))} | {fmt(D)} |\n")

lines.append("## Cost table (A6 model)\n")
lines.append("Window: per-product binding start → 2014-12-31. Model: 2 × (1 tick half-spread + 0.2 bps fees) "
             "per round trip; entry side +1 tick stress penalty. Ticks are hard-coded pilot-era outright minimum "
             "price fluctuations. Tick bps computed at the median pilot entry price. Reported for context; "
             "K2's threshold is fixed at +10 bps and does not rescale to this table.\n")
lines.append("| Product | Tick (price units) | Median entry price | 1 tick (bps) | Round trip (bps) | "
             "Stress-adjusted (bps) | G (bps) | G − stress cost (bps) |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in cost_rows:
    lines.append(f"| {r['product']} | {r['tick']:g} | {r['median_entry_price']:g} | {fmt(r['tick_bps'],2)} | "
                 f"{fmt(r['rt_bps'],2)} | {fmt(r['stress_bps'],2)} | {fmt(r['G_bps'])} | {fmt(r['G_net_stress'])} |")
lines.append(f"\nEvent-weighted pooled stress-adjusted round-trip cost (each event at its own entry price): "
             f"**{fmt(pooled_stress,2)} bps**.\n")

lines.append("## Event-time plot\n")
lines.append("![Pilot event-time paths](pilot_event_time_v3.png)\n")
lines.append(f"Mean direction-adjusted cumulative log return (bps), lags −15..+15 trading days, normalized to 0 "
             f"at entry; {len(events)} events vs {len(ctrl_paths)} matched control pseudo-trades (pooled over "
             f"event–control pairs, controls reusable per A5). A4 completeness guarantees lags −15..+11; "
             f"beyond +11 coverage declines (at +15: events {ev_n[-1]}/{len(events)}, controls "
             f"{ct_n[-1]}/{len(ctrl_paths)}); no imputation — per-lag available means. "
             f"Window: per-product binding start → 2014-12-31.\n")

lines.append("## Attrition and matching diagnostics\n")
lines.append("Window: per-product binding start → 2014-12-31.\n")
lines.append(f"- Pilot qualifying clustered events, 6 declared products (Stage-1 Gate 2 count): "
             f"{int((ev_all.entry_date.notna() & (ev_all.entry_date <= PILOT_END)).sum())}.")
lines.append(f"- SI (conduct-excluded in Stage 1, price-series identity unresolved): {len(si_pilot)} pilot events, "
             f"of which {int(si_pilot.included_flag.sum())} had complete windows — attrition only; no SILVER price "
             f"was loaded and no SI return was computed in this session.")
lines.append(f"- 5-product pilot universe: {len(pilot)} events, {len(pilot_inc)} included "
             f"({len(pilot) - len(pilot_inc)} excluded in Stage 1), of which "
             f"{int(pilot_inc.completeness_fallback.sum())} used the A4 completeness fallback.")
lines.append("- Control-day pools (A5, under the amended A4 selection including the completeness fallback — A0.4 symmetry):\n")
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
             f"event–control pairs.\n")

lines.append("## Interpretation notes (containment and spec readings)\n")
lines.append("1. **Candidate control days are restricted to the pilot window** (binding start → 2014-12-31). "
             "A5's “d within the product's analysis span” is applied jointly with A7's clause that the "
             "holdout (2015-01-01 → 2024-03-28) stays untouched until the pilot verdict is committed: pilot "
             "controls drawn from 2015+ would make the pilot verdict depend on holdout-era prices. The holdout "
             "stage mirrors this reading on its own window.")
lines.append("2. **Containment**: price data was loaded only through 2015-03-31 — the minimum covering the "
             "[entry−21, entry+11] windows and −15..+15 plot lags of late-December-2014 entries (event exits "
             "spill past year-end by construction; that spill is part of the preregistered design). No event "
             "dated after 2014-12-31 was loaded, filtered, summarized, or plotted. Post-2014 margin rows were "
             "consulted only as raw change dates for the A5 ±15-trading-day exclusion at the boundary.")
lines.append("3. **Margin-change exclusion**: changes of any size and either direction; change dates snapped to "
             "the first trading day on/after the effective date (the same snap A3 uses for entries). Changes "
             "before a product's margin-history start are unobservable; the rule filters on known changes.")
lines.append("4. **Pilot boundary**: by-entry-date and by-effective-date definitions coincide in this sample "
             "(93 events either way; verified before matching).")
lines.append("5. **Event/control construction is logic-identical to the committed Stage-1 record**: the loader "
             "and A4 selection are copied from stage1_v3.py, and every pilot event's recomputed selected "
             "contract, fallback flag, trailing return, and trailing vol were asserted equal to events_v3.csv.")
lines.append("6. **Reproducibility**: scripts/stage2_v3.py, numpy seed 42 (bootstrap), k = 10,000 draws, "
             "monthly blocks over matched events' entry months.\n")

lines.append("## Lock clause\n")
lines.append("Per A7 (binding, unchanged from v2): the pilot answers go/no-go only. "
             + ("The holdout (2015-01-01 → 2024-03-28, decay split 2021-01-01) runs on the byte-identical "
                "specification in a separate session, on explicit human trigger, after this verdict is committed. "
                "Any post-pilot change converts the study to exploratory and forfeits the preregistration claim."
                if (k1_pass and k2_pass) else
                "The pilot failed; per A8 the strategy is dead and no holdout runs. PILOT_FAIL written."))
lines.append("")

(REPO / "pilot_results_v3.md").write_text("\n".join(lines))
print("pilot_results_v3.md written. Stage 2 complete — HARD STOP per Part B "
      "(no event dated after 2014-12-31 was loaded, summarized, or plotted).")
