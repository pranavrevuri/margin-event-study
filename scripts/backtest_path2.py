#!/usr/bin/env python3
"""
Path 2 backtest per strategy_spec_v1.md (binding): weekly trend signal,
margin-aware vol sizing, both variants, costs, integer pass, 2x cost pass.
Reads: data/prices_pst/ (adjusted, multiple), data/prices/stooq_*.csv,
data/margin_history_stitched.csv, data/events_v3.csv (identity assert only).
Writes: strategy_results.md (base report) + 3 PNGs (equity, drawdown, SI 2011).

Interpretive decisions (all logged in the results file "Implementation
log"; conservative reading per §8):
  R1  Roll dates = PRICE_CONTRACT switch dates in multiple/*.csv (user-confirmed;
      committed roll_calendars end 2020-2022, before data end; switches match the
      calendars where both exist and extend to 2024-03-28, and count MORE rolls).
  R2  CL/ZC/ZS hold annual Dec/Dec/Nov cycles in this data source (~1 roll/yr);
      kept per user confirmation, disclosed prominently.
  R3  Trade buffer: trade iff |target - held| >= 0.10 x |target| (target 0 with
      nonzero holdings always closes); trades go to the full target.
  R4  De-risk window = event entry day t_e (first trading day on/after effective
      date) through t_e + 10 trading days, inclusive — the closed studies'
      [t0, t0+10] window convention; halving applies to targets whose Friday
      evaluation date falls inside the window.
  R5  Stress cost flag evaluated at the trade-execution date (day-level reading
      of §5's week-level sentence): trailing 20-td std of daily dollar P&L per
      contract > its expanding 90th percentile (expanding from 2000-01-01,
      min 60 obs). Cost model only — never a position input.
  R6  Rolls pay the stress multiplier too ("any trade").
  R7  Roll cost charged on the position held entering the roll day (pre-rebalance).
  R8  Returns = daily $ P&L / $500,000 capital, arithmetic (no compounding);
      Sharpe with rf = 0 (futures excess-return convention).
  R9  All Friday inputs (price, EWMA, margin level, event windows) use data with
      dates <= the Friday evaluation date; execution at next trading day.
  R10 Integer pass: target rounded to nearest whole contract; same buffer rule
      applied to the integer target vs integer holdings.
  R11 sigma_margin binding share computed on weekly sizing (Friday) days.
  R12 SI/CL/ZC/ZS ticks hard-coded from CME specs (committed stage2_v3 table
      covers only ZN/6E/6J/GC/HG).
"""
import collections
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
PST = DATA / "prices_pst"

SPAN_END = "2024-03-28"
SAMPLE_START = "2001-01-02"
CAPITAL = 500_000.0
VOL_TARGET_ANN = 0.10
N_MARKETS = 9
BUDGET = VOL_TARGET_ANN * CAPITAL / np.sqrt(252.0) / N_MARKETS  # $/day per market
FEES_PER_SIDE = 2.00
Z_MARGIN = 2.33
BUFFER = 0.10
DERISK_TD = 10
EWMA_SPAN = 36
SIG_LOOKBACK = 252

PRODUCTS = {"ZN": "US10", "6E": "EUR", "6J": "JPY", "GC": "GOLD", "SI": "SILVER",
            "HG": "COPPER", "CL": "CRUDE_W", "ZC": "CORN", "ZS": "SOYBEAN"}
ORDER = ["ZN", "6E", "6J", "GC", "SI", "HG", "CL", "ZC", "ZS"]
POINT_SIZE = {"ZN": 1000.0, "6E": 125000.0, "6J": 12500000.0, "GC": 100.0,
              "SI": 5000.0, "HG": 25000.0, "CL": 1000.0, "ZC": 50.0, "ZS": 50.0}
TICK = {"ZN": 0.015625, "6E": 0.0001, "6J": 0.000001, "GC": 0.10, "HG": 0.0005,
        "SI": 0.005, "CL": 0.01, "ZC": 0.25, "ZS": 0.25}
TICK_USD = {p: TICK[p] * POINT_SIZE[p] for p in ORDER}
STOOQ_SCALE = {"SI": 100.0, "HG": 100.0}

SUBPERIODS = [("2001-2008", "2001-01-02", "2008-12-31"),
              ("2009-2014", "2009-01-01", "2014-12-31"),
              ("2015-2020", "2015-01-01", "2020-12-31"),
              ("2021-2024.03", "2021-01-01", "2024-03-28")]

# ---------------------------------------------------------------- load data
adj, mult_daily, stooq, evcal = {}, {}, {}, {}
for prod, instr in PRODUCTS.items():
    # weekend-stamped rows are partial Globex sessions, not settlements (Sunday
    # evening belongs to Monday's session); latest stamp per weekday date is the
    # settlement (grain settlements 2020-22 are stamped 19:00, so no hour filter)
    a = pd.read_csv(PST / f"adjusted/{instr}.csv").sort_values("DATETIME")
    a["date"] = a.DATETIME.str[:10]
    a = a[pd.to_datetime(a.date).dt.dayofweek < 5]
    adj[prod] = a.groupby("date").price.last().sort_index().loc[:SPAN_END]

    mp = pd.read_csv(PST / f"multiple/{instr}.csv").sort_values("DATETIME")
    mp["date"] = mp.DATETIME.str[:10]
    # event-clustering calendar: stage1_v3's exact construction (hour>=20
    # settlement rows, 1995+, weekend-stamped dates included) so the qualifying
    # event set is byte-identical to the closed studies' rule
    s1 = mp[(mp.DATETIME.str[11:13].astype(int) >= 20)
            & (mp.date >= "1995-01-01") & (mp.date <= SPAN_END)]
    evcal[prod] = sorted(s1.date.unique())
    mp = mp[pd.to_datetime(mp.date).dt.dayofweek < 5]
    mp = mp[mp.date <= SPAN_END].dropna(subset=["PRICE_CONTRACT"])
    mult_daily[prod] = mp.groupby("date").PRICE_CONTRACT.last()

    s = pd.read_csv(DATA / f"prices/stooq_{prod}_continuous.csv")
    stooq[prod] = (s.set_index("date").close.sort_index()
                   / STOOQ_SCALE.get(prod, 1.0))

margin = pd.read_csv(DATA / "margin_history_stitched.csv")
margin = margin[margin["product"].isin(PRODUCTS)].sort_values(["product", "effective_date"])

cal = {p: list(adj[p].index) for p in ORDER}
calpos = {p: {d: i for i, d in enumerate(cal[p])} for p in ORDER}


def td_shift(prod, d, k):
    c = cal[prod]
    i = calpos[prod].get(d)
    if i is None:
        later = [x for x in c if x >= d]
        if not later:
            return None
        i = calpos[prod][later[0]]
    j = i + k
    return c[j] if 0 <= j < len(c) else None


# margin level step function on each market calendar (effective date forward only)
margin_level = {}
for p in ORDER:
    g = margin[margin["product"] == p].drop_duplicates("effective_date", keep="last")
    lv = g.set_index("effective_date").maintenance.astype(float)
    idx = sorted(set(cal[p]) | set(lv.index))
    margin_level[p] = lv.reindex(idx).ffill().reindex(cal[p])
    # no-lookahead assert: level at any date equals last effective <= date
    probe = cal[p][len(cal[p]) // 2]
    eff = lv[lv.index <= probe]
    assert (np.isnan(margin_level[p][probe]) and eff.empty) or \
           (not eff.empty and margin_level[p][probe] == eff.iloc[-1])

# qualifying events (identical rule; clustered on the stage1 calendar so the
# event set is byte-identical to the closed studies / events_v3.csv)
def ev_td_shift(prod, d, k):
    c = evcal[prod]
    later = [x for x in c if x >= d]
    if not later:
        return None
    j = c.index(later[0]) + k
    return c[j] if 0 <= j < len(c) else None


def qualifying_events(prod, start=None):
    g = margin[margin["product"] == prod].drop_duplicates("effective_date", keep="last")
    lv = g.set_index("effective_date").maintenance.astype(float)
    pct = lv.pct_change()
    grid = pd.bdate_range(lv.index.min(), SPAN_END)
    level = lv.reindex(grid.strftime("%Y-%m-%d")).ffill()
    cum5 = level / level.shift(5) - 1.0
    inc = set(d for d, v in pct.items() if v == v and v > 0)
    qd = sorted((d, float(cum5.loc[d])) for d in level.index
                if d in inc and cum5.loc[d] == cum5.loc[d] and cum5.loc[d] >= 0.05
                and (start is None or d >= start))
    ev, i = [], 0
    while i < len(qd):
        d0 = qd[i][0]
        close = ev_td_shift(prod, d0, 10)
        j = i + 1
        while j < len(qd) and close is not None and qd[j][0] <= close:
            j += 1
        ev.append(d0)
        i = j
    return ev


events = {p: qualifying_events(p) for p in ORDER}

# assert identity with the committed events_v3.csv on the studies' binding spans
_BINDING = {"6E": "2000-01-01", "6J": "2000-02-03", "ZN": "2004-01-02",
            "GC": "2009-01-08", "SI": "2009-01-08", "HG": "2009-01-08"}
_v3 = pd.read_csv(DATA / "events_v3.csv")
_v3_set = set(zip(_v3["product"], _v3["effective_date"]))
_mine = set()
for _p, _st in _BINDING.items():
    _mine |= {(_p, d) for d in qualifying_events(_p, start=_st)}
assert _mine == _v3_set, ("event rule deviates from committed events_v3.csv: "
                          f"+{sorted(_mine - _v3_set)} -{sorted(_v3_set - _mine)}")
print(f"event-rule identity vs events_v3.csv: IDENTICAL ({len(_mine)} events)")
derisk_days = {p: set() for p in ORDER}
event_entry = {p: [] for p in ORDER}
for p in ORDER:
    for d_e in events[p]:
        t_e = td_shift(p, d_e, 0)
        if t_e is None:
            continue
        assert t_e >= d_e                       # window starts on/after effective
        event_entry[p].append(t_e)
        i0 = calpos[p][t_e]
        derisk_days[p].update(cal[p][i0:i0 + DERISK_TD + 1])   # R4: [t_e, t_e+10]

# roll dates = PRICE_CONTRACT switch dates (R1), snapped to the adjusted calendar
roll_dates = {}
for p in ORDER:
    md = mult_daily[p]
    sw = list(md[md != md.shift()].index[1:])
    snapped = []
    for d in sw:
        t = td_shift(p, d, 0)
        if t is not None and SAMPLE_START <= t <= SPAN_END:
            snapped.append(t)
    roll_dates[p] = sorted(set(snapped))

# per-market daily frames
frames = {}
for p in ORDER:
    A = adj[p]
    dchg = A.diff() * POINT_SIZE[p]                       # $ per contract per day
    ewma = dchg.ewm(span=EWMA_SPAN).std()
    vol20 = dchg.rolling(20).std()
    v = vol20.loc["2000-01-01":]
    p90 = v.expanding(min_periods=60).quantile(0.90)
    stress = (v > p90).reindex(A.index).fillna(False)     # R5
    U = stooq[p].reindex(sorted(set(A.index) | set(stooq[p].index))).ffill().reindex(A.index)
    frames[p] = pd.DataFrame({"A": A, "dchg": dchg, "ewma": ewma, "stress": stress,
                              "mlevel": margin_level[p], "U": U})

# weekly evaluation/execution pairs per market (ISO week; exec = next trading day)
weekly = {}
for p in ORDER:
    ts = pd.to_datetime(cal[p])
    iso = list(zip(ts.isocalendar().year, ts.isocalendar().week))
    pairs = []
    for i in range(len(cal[p]) - 1):
        if iso[i] != iso[i + 1]:                          # last trading day of week
            f, e = cal[p][i], cal[p][i + 1]
            if SAMPLE_START <= e <= SPAN_END:
                assert e > f
                pairs.append((f, e))
    weekly[p] = pairs

# ------------------------------------------------------------- backtest core
def run_market(p, variant, integer=False):
    """variant: 'overlay' (max sigma + de-risk) or 'baseline' (realized only).
    Returns daily DataFrame on the sample calendar."""
    fr = frames[p]
    sample = [d for d in cal[p] if SAMPLE_START <= d <= SPAN_END]
    out = pd.DataFrame(index=sample, dtype=float)
    trade_qty = pd.Series(0.0, index=sample)
    diag = []                                             # per-eval diagnostics
    pos = 0.0
    for f, e in weekly[p]:
        i = calpos[p][f]
        sig = 0.0
        if i >= SIG_LOOKBACK:
            chg = fr.A.iloc[i] - fr.A.iloc[i - SIG_LOOKBACK]
            sig = float(np.sign(chg))
        sigma_r = fr.ewma.iloc[i]
        ml = fr.mlevel.iloc[i]
        sigma_m = ml / Z_MARGIN if ml == ml else np.nan
        if variant == "overlay":
            sigma = np.nanmax([sigma_r, sigma_m])
        else:
            sigma = sigma_r
        target = 0.0
        if sig != 0.0 and sigma == sigma and sigma > 0:
            target = sig * BUDGET / sigma
            if variant == "overlay" and f in derisk_days[p]:
                target *= 0.5
        if integer:
            target = float(np.rint(target))
        diag.append((f, sigma_r, sigma_m, target))
        do_trade = (abs(target - pos) >= BUFFER * abs(target)) if target != 0.0 \
                   else (pos != 0.0)
        if integer and target == pos:
            do_trade = False
        if do_trade:
            trade_qty[e] = target - pos
            pos = target
    # daily position path: pos changes AT the settlement of the exec day
    path, cur = [], 0.0
    for d in sample:
        if trade_qty[d] != 0.0:
            cur += trade_qty[d]
        path.append(cur)
    out["pos_after"] = path
    out["pos_enter"] = out.pos_after.shift().fillna(0.0)  # held during day d
    out["gross"] = out.pos_enter * fr.dchg.reindex(sample).fillna(0.0)
    # costs
    tick = TICK_USD[p]
    stress_d = fr.stress.reindex(sample).fillna(False)
    q = trade_qty.abs()
    out["cost_rebal"] = q * (tick + FEES_PER_SIDE)
    out["stress_rebal"] = q * tick * stress_d
    held = out.pos_enter.abs()
    roll_mask = pd.Series(False, index=sample)
    roll_mask[roll_dates[p]] = True
    out["cost_roll"] = held * 2 * (tick + FEES_PER_SIDE) * roll_mask
    out["stress_roll"] = held * 2 * tick * roll_mask * stress_d
    out["cost_stress"] = out.stress_rebal + out.stress_roll
    out["cost"] = out.cost_rebal + out.cost_roll + out.cost_stress
    out["net"] = out.gross - out.cost
    out["contracts"] = q + 2 * held * roll_mask
    out["notional_traded"] = out.contracts * fr.U.reindex(sample) * POINT_SIZE[p]
    dg = pd.DataFrame(diag, columns=["f", "sigma_r", "sigma_m", "target"]).set_index("f")
    return out, dg


# run every market under both variants; keep overlay sizing diagnostics
VARIANTS = {}
diags = {}
for variant in ["overlay", "baseline"]:
    VARIANTS[variant] = {}
    for p in ORDER:
        res, dg = run_market(p, variant)
        VARIANTS[variant][p] = res
        if variant == "overlay":
            diags[p] = dg
INT_PASS = {p: run_market(p, "overlay", integer=True)[0] for p in ORDER}

# union sample calendar for portfolio aggregation
all_days = sorted(set().union(*[set(VARIANTS["overlay"][p].index) for p in ORDER]))


def portfolio(res_by_mkt, cost_mult=1.0):
    g = sum(r.gross.reindex(all_days).fillna(0.0) for r in res_by_mkt.values())
    c = sum(r.cost.reindex(all_days).fillna(0.0) for r in res_by_mkt.values()) * cost_mult
    return pd.DataFrame({"gross": g, "cost": c, "net": g - c}, index=all_days)


PORT = {v: portfolio(VARIANTS[v]) for v in VARIANTS}
PORT["overlay_2x"] = portfolio(VARIANTS["overlay"], 2.0)
PORT["baseline_2x"] = portfolio(VARIANTS["baseline"], 2.0)
PORT["integer"] = portfolio(INT_PASS)


# headline stats on a daily $ P&L series (returns = P&L / fixed capital, R8)
def metrics(pnl):
    r = pnl / CAPITAL
    n = len(r)
    ann_ret = r.mean() * 252
    ann_vol = r.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
    cum = r.cumsum()
    dd = cum - cum.cummax()
    worst12 = r.rolling(252).sum().min() if n >= 252 else np.nan
    return dict(ann_ret=ann_ret, ann_vol=ann_vol, sharpe=sharpe,
                max_dd=dd.min(), worst12=worst12)


def fmt_m(m):
    return (f"{m['ann_ret']*100:.2f}% | {m['ann_vol']*100:.2f}% | {m['sharpe']:.2f} "
            f"| {m['max_dd']*100:.1f}% | {m['worst12']*100:.1f}%")


# ------------------------------------------------------------- sanity checks
print("== SANITY CHECKS ==")
net_sharpe = metrics(PORT["overlay"].net)["sharpe"]
print(f"net overlay Sharpe: {net_sharpe:.3f}  (plausible band -0.5..+1.5: "
      f"{'OK' if -0.5 <= net_sharpe <= 1.5 else 'FAIL - BUG HUNT'})")
print("\nper-market realized daily vol of gross P&L ($/day; target ~%.0f):" % BUDGET)
for p in ORDER:
    v = VARIANTS["overlay"][p].gross.std()
    print(f"  {p}: {v:7.1f}")
years = sorted(set(d[:4] for d in all_days))
bad_years = []
for y in years:
    seg = PORT["overlay"]
    m = [d for d in all_days if d.startswith(y)]
    drag = seg.cost[m].sum()
    if drag <= 0:
        bad_years.append(y)
print(f"\ncost drag positive in every year: {'YES' if not bad_years else f'NO {bad_years}'}")

# ------------------------------------------------------------------- charts
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#9a9a9a"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#cccccc",
                     "axes.labelcolor": "#333333", "text.color": "#333333",
                     "xtick.color": "#555555", "ytick.color": "#555555",
                     "axes.grid": True, "grid.color": "#e8e8e8",
                     "grid.linewidth": 0.7, "figure.facecolor": "white",
                     "axes.facecolor": "white"})
DT = pd.to_datetime(all_days)

# chart 1: cumulative P&L, gross and net, both variants
fig, ax = plt.subplots(figsize=(10, 5.5))
series = [("overlay", "net", BLUE, "-", 1.9, "overlay net"),
          ("overlay", "gross", BLUE, "--", 1.1, "overlay gross"),
          ("baseline", "net", ORANGE, "-", 1.9, "baseline net"),
          ("baseline", "gross", ORANGE, "--", 1.1, "baseline gross")]
for v, col, c, ls, lw, lbl in series:
    y = PORT[v][col].cumsum() / CAPITAL * 100
    ax.plot(DT, y, color=c, ls=ls, lw=lw, label=lbl)
    ax.annotate(lbl, (DT[-1], y.iloc[-1]), xytext=(5, 0), textcoords="offset points",
                color=c, fontsize=9, va="center")
ax.set_title("Cumulative P&L, % of $500K capital (no compounding), 2001–2024.03")
ax.set_ylabel("% of capital")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.margins(x=0.09)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(REPO / "equity_curves_path2.png", dpi=150)
plt.close(fig)

# chart 2: drawdown from high-water mark, net, both variants
fig, ax = plt.subplots(figsize=(10, 3.8))
for v, c, lbl in [("overlay", BLUE, "overlay"), ("baseline", ORANGE, "baseline")]:
    r = PORT[v].net.cumsum() / CAPITAL
    dd = ((r - r.cummax()) * 100).to_numpy(dtype=float)
    ax.plot(DT, dd, color=c, lw=1.6, label=f"{lbl} net")
    if v == "overlay":
        ax.fill_between(DT, dd, 0.0, color=BLUE, alpha=0.12)
ax.set_title("Drawdown from high-water mark, net, % of capital")
ax.set_ylabel("% of capital")
ax.legend(loc="lower left", frameon=False, fontsize=9)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(REPO / "drawdown_path2.png", dpi=150)
plt.close(fig)

# chart 3: overlay diagnostic — SI positions around the 2011 silver episode
p = "SI"
w0, w1 = "2010-09-01", "2012-03-31"
win = [d for d in all_days if w0 <= d <= w1 and d in VARIANTS["overlay"][p].index]
fig, ax = plt.subplots(figsize=(10, 4.2))
for v, c, lbl in [("overlay", BLUE, "overlay"), ("baseline", ORANGE, "baseline")]:
    ax.step(pd.to_datetime(win), VARIANTS[v][p].pos_after[win], where="post",
            color=c, lw=1.8, label=lbl)
for t_e in event_entry[p]:
    if w0 <= t_e <= w1:
        ax.axvline(pd.to_datetime(t_e), color=GRAY, lw=0.9, ls=":")
ax.axhline(0, color="#cccccc", lw=0.8)
ax.set_title("SI position (contracts), Sep 2010 – Mar 2012 — dotted lines: "
             "qualifying margin-event entries")
ax.set_ylabel("contracts (fractional)")
ax.legend(loc="upper right", frameon=False, fontsize=9)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(REPO / "overlay_diagnostic_si2011.png", dpi=150)
plt.close(fig)

# --------------------------------------------------------------- §7 tables
L = []
hm = {v: {"gross": metrics(PORT[v].gross), "net": metrics(PORT[v].net)}
      for v in ["overlay", "baseline"]}
headline = (f"Net of costs, the margin-aware overlay ran 2001–2024.03 at a Sharpe of "
            f"{hm['overlay']['net']['sharpe']:.2f} with a maximum drawdown of "
            f"{hm['overlay']['net']['max_dd']*100:.1f}% of capital, vs "
            f"{hm['baseline']['net']['sharpe']:.2f} and "
            f"{hm['baseline']['net']['max_dd']*100:.1f}% for the realized-vol-only "
            f"baseline — the overlay "
            + ("improved" if hm['overlay']['net']['sharpe'] >= hm['baseline']['net']['sharpe']
               else "worsened") + " net Sharpe.")
L.append(headline)
L.append("\n# Strategy Results — Margin-Aware Trend (Path 2), per strategy_spec_v1.md\n")
L.append(f"Sample 2001-01-02 → 2024-03-28, 9 markets, $500K capital, 10% ann. vol "
         f"target split 1/9 per market (no correlation adjustment — disclosed; "
         f"realized portfolio vol is therefore well below 10%). Returns are daily "
         f"$ P&L / $500K, arithmetic, no compounding; Sharpe uses rf = 0 "
         f"(futures excess-return convention). All parameters fixed in "
         f"strategy_spec_v1.md before any result was computed.\n")

L.append("## 1–2. Headline table (equity curves: equity_curves_path2.png)\n")
L.append("| Variant | Ann ret | Ann vol | Sharpe | Max DD | Worst 12m |")
L.append("|---|---|---|---|---|---|")
for v in ["overlay", "baseline"]:
    for gk in ["gross", "net"]:
        L.append(f"| {v} {gk} | " + fmt_m(hm[v][gk]).replace(" | ", " | ") + " |")
L.append("\n![equity](equity_curves_path2.png)\n![drawdown](drawdown_path2.png)\n")

# cost decomposition
L.append("## 3. Cost decomposition and turnover (overlay variant)\n")
L.append("| Year | Rebal cost bps | Roll cost bps | Stress surcharge bps | Total bps "
         "| Contracts traded | Notional traded $M |")
L.append("|---|---|---|---|---|---|---|")
tot = collections.defaultdict(float)
for y in years:
    m = [d for d in all_days if d.startswith(y)]
    rb = sum(VARIANTS["overlay"][p].cost_rebal.reindex(m).fillna(0).sum() for p in ORDER)
    rl = sum(VARIANTS["overlay"][p].cost_roll.reindex(m).fillna(0).sum() for p in ORDER)
    st = sum(VARIANTS["overlay"][p].cost_stress.reindex(m).fillna(0).sum() for p in ORDER)
    ct = sum(VARIANTS["overlay"][p].contracts.reindex(m).fillna(0).sum() for p in ORDER)
    nt = sum(VARIANTS["overlay"][p].notional_traded.reindex(m).fillna(0).sum() for p in ORDER)
    for k, val in [("rb", rb), ("rl", rl), ("st", st), ("ct", ct), ("nt", nt)]:
        tot[k] += val
    L.append(f"| {y} | {rb/CAPITAL*1e4:.1f} | {rl/CAPITAL*1e4:.1f} | "
             f"{st/CAPITAL*1e4:.1f} | {(rb+rl+st)/CAPITAL*1e4:.1f} | {ct:,.0f} | "
             f"{nt/1e6:,.0f} |")
ny = len(years)
L.append(f"| **mean/yr** | {tot['rb']/ny/CAPITAL*1e4:.1f} | {tot['rl']/ny/CAPITAL*1e4:.1f} "
         f"| {tot['st']/ny/CAPITAL*1e4:.1f} | "
         f"{(tot['rb']+tot['rl']+tot['st'])/ny/CAPITAL*1e4:.1f} | {tot['ct']/ny:,.0f} | "
         f"{tot['nt']/ny/1e6:,.0f} |")

L.append("\n## 4. Per-market contribution (overlay, net)\n")
L.append("| Market | Net P&L $K | Daily vol $ | Hit rate | Rolls in sample |")
L.append("|---|---|---|---|---|")
for p in ORDER:
    r = VARIANTS["overlay"][p]
    active = r[r.pos_enter != 0]
    hit = (active.net > 0).mean() if len(active) else np.nan
    L.append(f"| {p} | {r.net.sum()/1e3:,.1f} | {r.gross.std():,.0f} | {hit*100:.1f}% "
             f"| {len(roll_dates[p])} |")

L.append("\n## 5. Sub-periods (net)\n")
L.append("| Period | Overlay ret/vol/Sharpe/maxDD | Baseline ret/vol/Sharpe/maxDD |")
L.append("|---|---|---|")
for name, a, b in SUBPERIODS:
    row = [name]
    for v in ["overlay", "baseline"]:
        seg = PORT[v].net[(PORT[v].index >= a) & (PORT[v].index <= b)]
        mm = metrics(seg)
        row.append(f"{mm['ann_ret']*100:.2f}% / {mm['ann_vol']*100:.2f}% / "
                   f"{mm['sharpe']:.2f} / {mm['max_dd']*100:.1f}%")
    L.append("| " + " | ".join(row) + " |")

L.append("\n## 6. Overlay diagnostics\n")
L.append("Share of weekly sizing days where sigma_margin > sigma_realized "
         "(binds), by market and era (— = no margin data yet):\n")
L.append("| Market | " + " | ".join(n for n, _, _ in SUBPERIODS) + " | Full |")
L.append("|---|---|---|---|---|---|")
for p in ORDER:
    dg = diags[p]
    cells = []
    for _, a, b in SUBPERIODS + [("Full", SAMPLE_START, SPAN_END)]:
        seg = dg[(dg.index >= max(a, SAMPLE_START)) & (dg.index <= b)]
        seg = seg[seg.sigma_m.notna()]
        cells.append(f"{(seg.sigma_m > seg.sigma_r).mean()*100:.0f}%" if len(seg) else "—")
    L.append(f"| {p} | " + " | ".join(cells) + " |")
L.append("\n![SI 2011](overlay_diagnostic_si2011.png)\n")

L.append("## 7. Integer-contract pass ($500K) and 2× cost sensitivity\n")
L.append("| Run | Ann ret | Ann vol | Sharpe | Max DD | Worst 12m |")
L.append("|---|---|---|---|---|---|")
for name, key in [("overlay net (fractional)", "overlay"),
                  ("overlay net INTEGER", "integer"),
                  ("overlay net 2× costs", "overlay_2x"),
                  ("baseline net 2× costs", "baseline_2x")]:
    L.append(f"| {name} | " + fmt_m(metrics(PORT[key].net)) + " |")
L.append("\nInteger-pass sizing feasibility (median absolute fractional target, "
         "overlay): markets rounding to zero most weeks are un-sizeable at $500K.\n")
L.append("| Market | Median \\|target\\| (contracts) | Un-sizeable? |")
L.append("|---|---|---|")
for p in ORDER:
    med = diags[p].target.abs().median()
    L.append(f"| {p} | {med:.2f} | {'YES' if med < 0.5 else 'no'} |")
tr_frac = PORT["overlay"].net.sum()
tr_int = PORT["integer"].net.sum()
L.append(f"\nTracking difference, integer vs fractional overlay: net P&L "
         f"${tr_int/1e3:,.1f}K vs ${tr_frac/1e3:,.1f}K "
         f"({(tr_int-tr_frac)/CAPITAL*1e4:.0f} bps of capital over the sample).\n")

# drawdown episodes
L.append("## 8. Five worst drawdown episodes (overlay, net)\n")
r = PORT["overlay"].net.cumsum() / CAPITAL
hwm = r.cummax()
dd = r - hwm
episodes = []
in_dd, start = False, None
for i, d in enumerate(all_days):
    if dd.iloc[i] < 0 and not in_dd:
        in_dd, start = True, i
    if in_dd and (dd.iloc[i] == 0 or i == len(all_days) - 1):
        seg = dd.iloc[start:i + 1]
        episodes.append((seg.min(), all_days[max(start - 1, 0)],
                         seg.idxmin(), all_days[i] if dd.iloc[i] == 0 else "not recovered",
                         all_days[max(start - 1, 0)], seg.idxmin()))
        in_dd = False
episodes.sort()
L.append("| Depth | Peak | Trough | Recovered | Top negative markets peak→trough |")
L.append("|---|---|---|---|---|")
for depth, peak, trough, rec, a, b in episodes[:5]:
    contrib = {p: VARIANTS["overlay"][p].net[
        (VARIANTS["overlay"][p].index > a) & (VARIANTS["overlay"][p].index <= b)].sum()
        for p in ORDER}
    worst = sorted(contrib.items(), key=lambda kv: kv[1])[:3]
    ws = ", ".join(f"{k} ${v/1e3:,.0f}K" for k, v in worst if v < 0)
    L.append(f"| {depth*100:.1f}% | {peak} | {trough} | {rec} | {ws} |")

L.append("\n## Sanity checks (build prompt step 4)\n")
L.append(f"- Net overlay Sharpe {net_sharpe:.2f} — inside the plausible band "
         f"[−0.5, +1.5]: {'PASS' if -0.5 <= net_sharpe <= 1.5 else 'FAIL'}.")
vols = [VARIANTS['overlay'][p].gross.std() for p in ORDER]
L.append(f"- Per-market gross daily vol (target ≈ ${BUDGET:.0f}/day): "
         + ", ".join(f"{p} ${v:.0f}" for p, v in zip(ORDER, vols)) + ".")
L.append(f"- Cost drag positive in every year: {'PASS' if not bad_years else f'FAIL {bad_years}'}.")

L.append("\n## Disclosures and implementation log (spec §8)\n")
L.append("- **Fragility of the A/B verdict:** an initial run of this same code "
         "contained a calendar bug (weekend-stamped partial Globex rows treated as "
         "trading days, so some weekly evaluations landed on Sunday-stamped prices "
         "— 646 such rows in SI alone). Fixing it (R14) moved net Sharpe from "
         "0.66/0.69 (overlay/baseline) to the final numbers and FLIPPED the sign "
         "of the overlay-vs-baseline comparison. The overlay-minus-baseline Sharpe "
         "difference is therefore noise-level (~±0.03–0.05) and should not be "
         "pitched as an edge; the robust effect is the drawdown/vol reduction.")
L.append("- **CL/ZC/ZS annual cycle (user-confirmed):** the pysystemtrade source holds "
         "only the December (CL, ZC) / November (ZS) contract, rolling ~1×/yr — not a "
         "front-month series. Roll costs for these three understate a monthly-rolled "
         "real-world implementation, and the held contract is a deferred contract most "
         "of the year (lower vol, different carry). Affects Capital & Liquidity claims.")
L.append("- **Roll dates (user-confirmed):** PRICE_CONTRACT switch dates from "
         "multiple/*.csv — the rolls actually embedded in the adjusted P&L series; the "
         "committed roll_calendars end 2020–2022 and match the switches (±1-day stamp "
         "convention) where both exist. The switch source counts MORE rolls (more cost).")
L.append("- **SI series:** contract-identity ambiguity (0.72% Stage-1 cross-check "
         "mismatch) — immaterial for trend/vol math; included per spec §1 with this "
         "disclosure.")
L.append("- Before a product's margin history begins (metals/CL 2009; ZC/ZS 2003-11; "
         "ZN 2004-01), the overlay has no margin input: sigma_hat = sigma_realized and "
         "no de-risk events — disclosed, not backfilled.")
for r_ in ["R3 Trade buffer: trade iff |target−held| ≥ 10% × |target|; a zero target "
           "with nonzero holdings always closes; trades go to the full target.",
           "R4 De-risk window = event entry day (first trading day on/after the "
           "effective date) through +10 trading days inclusive, applied when the "
           "Friday evaluation date falls inside it (the closed studies' [t0, t0+10] "
           "convention).",
           "R5 Stress flag evaluated at the trade-execution date: trailing 20-td std "
           "of daily $ P&L per contract above its expanding 90th percentile "
           "(expanding from 2000-01-01, min 60 obs). Cost model only.",
           "R6 Rolls in stress periods pay 2 ticks per side too ('any trade').",
           "R7 Roll cost charged on the position entering the roll day (pre-rebalance).",
           "R8 Returns arithmetic on fixed $500K; no compounding; rf = 0.",
           "R9 All Friday inputs use data dated ≤ the Friday; execution next trading "
           "day settlement; margin levels and events apply from effective date "
           "forward only (asserted).",
           "R10 Integer pass: nearest-integer targets, same buffer rule.",
           "R11 Margin-binding shares computed on weekly sizing days.",
           "R12 SI/CL/ZC/ZS tick values hard-coded from CME specs (committed table "
           "covers only ZN/6E/6J/GC/HG); eyeball-confirmed in the step-1 pause.",
           "R13 Hit rate = share of days with a position where net daily P&L > 0.",
           "R14 Daily calendar: weekend-stamped rows in the pysystemtrade files "
           "(partial Globex sessions, e.g. 646 Sunday rows in SI) are dropped; the "
           "latest stamp per weekday date is taken as the settlement (no hour "
           "filter — grain settlements 2020-22 are stamped 19:00). Weekly "
           "evaluations therefore land on Fridays (or the week's last weekday)."]:
    L.append(f"- {r_}")

(REPO / "strategy_results.md").write_text("\n".join(L) + "\n")
print("\nwrote strategy_results.md and 3 PNGs")
print("\nHEADLINE:", headline)
