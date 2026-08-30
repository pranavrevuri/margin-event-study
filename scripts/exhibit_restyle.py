#!/usr/bin/env python3
"""
Presentation only — NO change to strategy logic, parameters, or results.
Reads: the committed backtest (rerun unchanged via backtest_path2.py, which
reproduces the committed numbers exactly); episode dates, beta, and factsheet
values are taken verbatim from the committed strategy_results.md.
Writes: FIG1_equity.png, FIG2_drawdown.png, FIG3_si2011.png, FIG4_annual.png,
TABLE1_summary.png. strategy_results.md is snapshot/restored, not modified.
"""
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.transforms as mtransforms

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

# ------------------------------------------ TABLE1: factsheet summary image
# values verbatim from the committed strategy_results.md
LEFT = [("Net return / yr", "2.21%"),
        ("Volatility (ann.)", "3.32%"),
        ("Sharpe (gross / net / 2× costs)", "0.73 / 0.67 / 0.60"),
        ("Max drawdown", "−9.4%"),
        ("Worst 12 months", "−8.1%")]
RIGHT = [("Beta to S&P 500 (SE)", "−0.021  (0.002)"),
         ("Correlation to S&P 500", "−0.13"),
         ("Avg cost / turnover per yr", "20.8 bps · 58 contracts"),
         ("Total net P&L", "$261.8K  (52.4% of capital)"),
         ("Sample", "2001-01 – 2024-03 · 9 mkts")]
fig = plt.figure(figsize=(8.6, 4.0))
ax = fig.add_axes([0, 0, 1, 1])
ax.axis("off")
fig.text(0.055, 0.895, "Margin-Aware Trend (Path 2) — overlay summary",
         fontsize=14, fontweight="bold", color=INK)
fig.text(0.055, 0.825, SUB_FULL, fontsize=9, color=FAINT)
ax.plot([0.055, 0.945], [0.775, 0.775], color=NAVY, lw=2.2,
        transform=fig.transFigure, clip_on=False)
y0, dy = 0.685, 0.112
for col, x_name, x_val in [(LEFT, 0.055, 0.475), (RIGHT, 0.525, 0.945)]:
    for i, (name, val) in enumerate(col):
        y = y0 - i * dy
        fig.text(x_name, y, name, fontsize=9.5, color=FAINT, va="center")
        fig.text(x_val, y, val, fontsize=10, color=INK, fontweight="bold",
                 ha="right", va="center")
        ax.plot([x_name, x_val], [y - dy * 0.42] * 2, color="#e5e5e5",
                lw=0.8, transform=fig.transFigure, clip_on=False)
fig.text(0.055, 0.075, "Overlay variant, fractional contracts, net of costs "
         "unless noted. Beta vs SPY (Stooq, 2005-02+). "
         "Values from strategy_results.md.", fontsize=7.8, color=FAINT)
fig.savefig(REPO / "TABLE1_summary.png")
plt.close(fig)

print("wrote FIG1_equity, FIG2_drawdown, FIG3_si2011, FIG4_annual, "
      "TABLE1_summary (.png)")
