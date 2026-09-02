#!/usr/bin/env python3
"""
Presentation only — NO change to strategy logic, parameters, or results.
Reads: the committed backtest (rerun unchanged via backtest_path2.py, which
reproduces the committed numbers exactly); drawdown-episode dates are taken
verbatim from, and every factsheet-table value is parsed out of, the committed
strategy_results.md.
Writes: FIG1_equity.png, FIG2_drawdown.png, FIG3_si2011.png, FIG4_annual.png,
FIG_summary_table.png. strategy_results.md is snapshot/restored, not modified.
"""
import re
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.transforms as mtransforms
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "strategy_results.md"

snapshot = RESULTS.read_text()
bt = runpy.run_path(REPO / "scripts/backtest_path2.py")
RESULTS.write_text(snapshot)

CAPITAL = bt["CAPITAL"]
PORT = bt["PORT"]
VARIANTS = bt["VARIANTS"]
all_days = bt["all_days"]
metrics = bt["metrics"]
events = bt["events"]
td_shift = bt["td_shift"]

# ------------------------------------------------------------- shared style
NAVY = "#1b3a6b"          # overlay
GRAY = "#9a9a9a"          # baseline / negatives
INK = "#333333"
FAINT = "#777777"
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.edgecolor": "#cccccc",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": "#666666",
    "ytick.color": "#666666",
    "axes.grid": True,
    "axes.grid.axis": "y",           # light gray horizontal gridlines only
    "grid.color": "#e5e5e5",
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.dpi": 150,
})
# NB: Helvetica lacks the U+2192 arrow glyph — use an en dash in date ranges
SUB_FULL = ("2001-01-02 – 2024-03-28 · 9 CME futures markets · $500K capital · "
            "net of costs, no compounding")


def headed(ax, title, sub):
    ax.set_title(title, loc="left", fontweight="bold", fontsize=12.5, pad=24)
    ax.text(0.0, 1.035, sub, transform=ax.transAxes, fontsize=8.5, color=FAINT)


def date_axis(ax, years=2):
    ax.xaxis.set_major_locator(mdates.YearLocator(years))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


DT = pd.to_datetime(all_days)
m_o = metrics(PORT["overlay"].net)
m_b = metrics(PORT["baseline"].net)

# ---------------------------------------------------- FIG1: cumulative net P&L
fig, ax = plt.subplots(figsize=(10, 5.2))
for key, c, lw, lbl in [("overlay", NAVY, 2.0, "Overlay"),
                        ("baseline", GRAY, 1.6, "Baseline")]:
    y = PORT[key].net.cumsum() / CAPITAL * 100
    ax.plot(DT, y, color=c, lw=lw, label=lbl)
    ax.annotate(lbl, (DT[-1], y.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", color=c, fontsize=9.5,
                fontweight="bold", va="center")
box = (f"{'':<9}{'Sharpe':>7}{'Max DD':>8}\n"
       f"{'Overlay':<9}{m_o['sharpe']:>7.2f}{m_o['max_dd']*100:>7.1f}%\n"
       f"{'Baseline':<9}{m_b['sharpe']:>7.2f}{m_b['max_dd']*100:>7.1f}%")
ax.text(0.025, 0.96, box, transform=ax.transAxes, fontsize=8.5,
        fontfamily="monospace", va="top",
        bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#cccccc", lw=0.8))
headed(ax, "Cumulative net P&L — overlay vs baseline", SUB_FULL)
ax.set_ylabel("% of capital")
date_axis(ax)
ax.margins(x=0.06)
fig.tight_layout()
fig.savefig(REPO / "FIG1_equity.png")
plt.close(fig)

# --------------------------------------------------------- FIG2: drawdown
# five worst overlay episodes, verbatim from strategy_results.md §8
EPISODES = [("1st worst −9.4%", "Jul 2008–Feb 2010", "2008-07-02", "2010-02-05"),
            ("2nd worst −6.8%", "Aug 2011–Jan 2013", "2011-08-31", "2013-01-04"),
            ("3rd worst −5.2%", "Jun 2001–May 2002", "2001-06-25", "2002-05-14"),
            ("4th worst −4.8%", "Apr 2004–Jul 2004", "2004-04-01", "2004-07-27"),
            ("5th worst −4.6%", "Oct 2022–Dec 2023", "2022-10-19", "2023-12-14")]
fig, ax = plt.subplots(figsize=(10, 4.6))
for key, c, lw, lbl in [("baseline", GRAY, 1.3, "Baseline"),
                        ("overlay", NAVY, 1.8, "Overlay")]:
    r = PORT[key].net.cumsum() / CAPITAL
    dd = ((r - r.cummax()) * 100).to_numpy(dtype=float)
    ax.plot(DT, dd, color=c, lw=lw, label=lbl)
for line1, line2, peak, trough in EPISODES:
    t0, t1 = pd.to_datetime(peak), pd.to_datetime(trough)
    ax.axvspan(t0, t1, color=NAVY, alpha=0.08, lw=0)
    # anchor labels at the episode midpoint so adjacent episodes don't collide
    ax.text(t0 + (t1 - t0) / 2, -12.3, f"{line1}\n{line2}",
            ha="center", va="top", fontsize=7.4, color="#555555",
            bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
ax.set_ylim(-14.4, 0.6)
headed(ax, "Drawdown from high-water mark — five worst overlay episodes shaded",
       SUB_FULL)
ax.set_ylabel("% of capital")
# legend in the header band, clear of the episode labels along the bottom
fig.legend(loc="upper right", bbox_to_anchor=(0.97, 0.965), ncol=2,
           frameon=False, fontsize=9)
date_axis(ax)
ax.margins(x=0.02)
fig.tight_layout()
fig.savefig(REPO / "FIG2_drawdown.png")
plt.close(fig)

# ------------------------------------------- FIG3: SI 2011 sizing diagnostic
P, W0, W1 = "SI", "2010-09-01", "2012-03-31"
win = [d for d in all_days if W0 <= d <= W1 and d in VARIANTS["overlay"][P].index]
wdt = pd.to_datetime(win)
fig, ax = plt.subplots(figsize=(10, 4.6))
# 10-trading-day de-risk windows and their margin-hike effective dates
first = True
for d_e in events[P]:
    t_e = td_shift(P, d_e, 0)
    t_end = td_shift(P, t_e, 10) or win[-1]
    if t_e is None or t_end < W0 or t_e > W1:
        continue
    ax.axvspan(pd.to_datetime(t_e), pd.to_datetime(t_end), color=NAVY,
               alpha=0.09, lw=0, label="de-risk window [t0, t0+10]" if first else None)
    ax.axvline(pd.to_datetime(t_e), color=NAVY, lw=0.8, ls=":", alpha=0.65)
    tr = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
    ax.text(pd.to_datetime(t_e), 0.99, f" hike eff. {d_e}", transform=tr,
            rotation=90, va="top", ha="right", fontsize=7.2, color=NAVY)
    first = False
for key, c, lw, lbl in [("baseline", GRAY, 1.5, "Baseline"),
                        ("overlay", NAVY, 1.9, "Overlay")]:
    ax.step(wdt, VARIANTS[key][P].pos_after[win], where="post",
            color=c, lw=lw, label=lbl)
ax.axhline(0, color="#bbbbbb", lw=0.8)
headed(ax, "Margin-based sizing around the 2011 silver margin episode",
       "SI position, contracts (fractional) · Sep 2010 – Mar 2012 · shaded: "
       "10-day de-risk window after each qualifying margin hike")
ax.set_ylabel("contracts")
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax.margins(x=0.02)
fig.tight_layout()
fig.savefig(REPO / "FIG3_si2011.png")
plt.close(fig)

# ------------------------------------------------- FIG4: annual net returns
net = PORT["overlay"].net
years = sorted(set(d[:4] for d in all_days))
ann = [net[[d for d in all_days if d.startswith(y)]].sum() / CAPITAL * 100
       for y in years]
labels = [y if y != "2024" else "2024*" for y in years]
fig, ax = plt.subplots(figsize=(10, 4.4))
ax.bar(labels, ann, color=[NAVY if v >= 0 else GRAY for v in ann],
       width=0.72, zorder=3)
ax.axhline(0, color=INK, lw=1.3, zorder=4)
headed(ax, "Annual net returns — overlay variant",
       "2001–2024 (*2024 through 03-28) · % of $500K capital · net of costs")
ax.set_ylabel("% of capital")
ax.tick_params(axis="x", rotation=60)
fig.tight_layout()
fig.savefig(REPO / "FIG4_annual.png")
plt.close(fig)

# ------------------------------------ FIG_summary_table: factsheet summary
# Every value is parsed from the committed strategy_results.md (the `snapshot`
# text) so the table cannot drift from the report; a format change there
# fails loudly here instead of rendering a stale number.
def md_section(text, heading):
    m = re.search(r"^## " + re.escape(heading) + r".*?$(.*?)(?=^## |\Z)",
                  text, re.M | re.S)
    assert m, f"section not found: {heading}"
    return m.group(1)


def md_row(section, first_cell):
    m = re.search(r"^\| " + re.escape(first_cell) + r" \|(.*)$", section, re.M)
    assert m, f"row not found: {first_cell}"
    return [c.strip() for c in m.group(1).strip().strip("|").split("|")]


def neg(s):                       # typographic minus for display
    return s.replace("-", "−")


head = md_section(snapshot, "1–2. Headline table")
ov_net, ov_gross, bl_net = (md_row(head, k) for k in
                            ("overlay net", "overlay gross", "baseline net"))
cost_mean = md_row(md_section(snapshot, "3. Cost decomposition"), "**mean/yr**")
mkts = md_section(snapshot, "4. Per-market contribution")
pnl = {p: float(md_row(mkts, p)[0])
       for p in ("ZN", "6E", "6J", "GC", "SI", "HG", "CL", "ZC", "ZS")}
subp = md_section(snapshot, "5. Sub-periods")
sub_sharpe = [(lbl, md_row(subp, key)[0].split(" / ")[2]) for lbl, key in
              (("2001–2008", "2001-2008"), ("2009–2014", "2009-2014"),
               ("2015–2020", "2015-2020"), ("2021–2024", "2021-2024.03"))]
sens = md_section(snapshot, "7. Integer-contract pass")
int_sharpe = md_row(sens, "overlay net INTEGER")[2]
x2_sharpe = md_row(sens, "overlay net 2× costs")[2]
beta_spy = float(md_row(md_section(snapshot, "Beta and correlation"),
                        "SPY adj. (Yahoo)")[1])       # full-sample Yahoo SPY

GROUPS = [
    ("Performance", [("Net Return (ann.)", ov_net[0]),
                     ("Net Sharpe", ov_net[2]),
                     ("Gross Sharpe", ov_gross[2]),
                     ("Markets Profitable",
                      f"{sum(v > 0 for v in pnl.values())} of {len(pnl)}")]),
    ("Risk", [("Volatility (ann.)", ov_net[1]),
              ("Maximum Drawdown", neg(ov_net[3])),
              ("Worst 12 Months", neg(ov_net[4])),
              ("Beta to S&P 500", neg(f"{beta_spy:.2f}"))]),
    ("Overlay vs Baseline", [("Overlay Vol", ov_net[1]),
                             ("Baseline Vol", bl_net[1]),
                             ("Overlay Max DD", neg(ov_net[3])),
                             ("Baseline Max DD", neg(bl_net[3]))]),
    ("Costs & Robustness", [("Cost Drag", f"{cost_mean[3]} bps/yr"),
                            ("Sharpe at 2× Costs", x2_sharpe),
                            ("Integer-Contract Sharpe", int_sharpe),
                            ("Turnover", f"~{cost_mean[4]} contracts/yr")]),
]
PNL_COLS = sorted(pnl.items(), key=lambda kv: -kv[1])
CAPTION = ("Figure 1.", " Backtest summary, 2001–2024, $500K, "
           "net of modeled costs.")

# Arial: metrically a Helvetica clone, and the only one of the two with a
# real Bold face installed (matplotlib sees just the regular face inside the
# HelveticaNeue .ttc, so "bold" there silently renders regular).
FONT = "Arial"
# layout in inches from the top-left corner; 150 dpi via rcParams
W, H = 11.0, 4.75
L, R = 0.55, W - 0.55
PAD = 0.22
fig = plt.figure(figsize=(W, H))
X = lambda x: x / W
Y = lambda y: 1 - y / H


def txt(x, y, s, **kw):
    kw.setdefault("fontfamily", FONT)
    return fig.text(X(x), Y(y), s, **kw)


def rule(x0, y0, x1, y1, **kw):
    fig.add_artist(Line2D([X(x0), X(x1)], [Y(y0), Y(y1)],
                          transform=fig.transFigure, **kw))


HEAVY = dict(color=NAVY, lw=1.8, solid_capstyle="butt")
THIN = dict(color="#cccccc", lw=0.8)

# main table: four groups side by side
gw = (R - L) / len(GROUPS)
y_head, y_rule, y_row0, dy = 0.66, 0.80, 1.14, 0.345
y_bot = y_row0 + (len(GROUPS[0][1]) - 1) * dy + 0.20
rule(L, y_rule, R, y_rule, **HEAVY)
for g, (title, rows) in enumerate(GROUPS):
    x0, x1 = L + g * gw, L + (g + 1) * gw
    if g:
        rule(x0, y_head - 0.22, x0, y_bot, **THIN)
    txt(x0 + PAD, y_head, title, fontsize=10.5, fontweight="bold", color=INK,
        va="baseline")
    for i, (name, val) in enumerate(rows):
        y = y_row0 + i * dy
        txt(x0 + PAD, y, name, fontsize=9.5, color=FAINT, va="center")
        txt(x1 - PAD, y, val, fontsize=10, color=INK, fontweight="bold",
            ha="right", va="center")

# two compact sub-tables side by side, same style
y_head2 = y_bot + 0.56
y_rule2 = y_head2 + 0.14
y_lab2, y_val2 = y_rule2 + 0.30, y_rule2 + 0.62
y_bot2 = y_val2 + 0.20
x_split = L + (R - L) * 0.36
rule(L, y_rule2, R, y_rule2, **HEAVY)
rule(x_split, y_head2 - 0.22, x_split, y_bot2, **THIN)
for title, cols, x0, x1 in [
        ("Sub-period net Sharpe", sub_sharpe, L, x_split),
        ("Per-market net P&L ($K)", [(p, f"{v:.1f}") for p, v in PNL_COLS],
         x_split, R)]:
    txt(x0 + PAD, y_head2, title, fontsize=10.5, fontweight="bold", color=INK,
        va="baseline")
    cw = (x1 - x0 - 2 * PAD) / len(cols)
    for j, (lab, val) in enumerate(cols):
        xr = x0 + PAD + (j + 1) * cw
        txt(xr, y_lab2, lab, fontsize=9, color=FAINT, ha="right", va="center")
        txt(xr, y_val2, val, fontsize=10, color=INK, fontweight="bold",
            ha="right", va="center")

# caption: bold figure number, regular text placed flush after it
y_cap = y_bot2 + 0.46
lead = txt(L, y_cap, CAPTION[0], fontsize=9, fontweight="bold", color=INK,
           va="baseline")
fig.canvas.draw()
bb = lead.get_window_extent(fig.canvas.get_renderer())
x_after = fig.transFigure.inverted().transform((bb.x1, 0))[0]
txt(x_after * W, y_cap, CAPTION[1], fontsize=9, color=INK, va="baseline")

fig.savefig(REPO / "FIG_summary_table.png")
plt.close(fig)

print("wrote FIG1_equity, FIG2_drawdown, FIG3_si2011, FIG4_annual, "
      "FIG_summary_table (.png)")
