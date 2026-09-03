#!/usr/bin/env python3
"""
Presentation only — NO change to strategy logic, parameters, or results.
Reads: the committed backtest (rerun unchanged via backtest_path2.py, which
reproduces the committed numbers exactly); drawdown-episode dates are taken
verbatim from, and every factsheet-table value is parsed out of, the committed
strategy_results.md.
Writes (when run as a script): FIG1_equity.png, FIG2_drawdown.png,
FIG3_si2011.png, FIG4_annual.png, FIG_summary_table.png at their standard
sizes. strategy_results.md is snapshot/restored, not modified.

Each exhibit is a function returning a matplotlib Figure so that
scripts/exhibits_page.py can re-render it at a page-slot size instead of
downscaling the PNG. Every parameter defaults to the standard exhibit; the only
extras are fitting hooks (legend placement, tick spacing, header size, label
de-collision) that change nothing at the defaults.
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
events = bt["events"]
td_shift = bt["td_shift"]

# ------------------------------------------------------------- shared style
# grayscale only: near-black overlay, medium-gray baseline, light-gray bands
OVERLAY = "#1a1a1a"       # overlay series, positive bars
BASELINE = "#8c8c8c"      # baseline series, negative bars
MARK = "#555555"          # event markers and their labels
SHADE = dict(color="#000000", alpha=0.08, lw=0)   # light gray shaded bands
INK = "#333333"
FAINT = "#777777"
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica Neue", "Helvetica", "DejaVu Sans"],
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
# Arial: metrically a Helvetica clone with a real Bold face installed —
# matplotlib sees only the regular face inside the HelveticaNeue .ttc, so bold
# titles/values there rendered regular. Date ranges use an en dash, not U+2192.
SUB_FULL = ("2001-01-02 – 2024-03-28 · 9 CME futures markets · $500K capital · "
            "net of costs, no compounding")


def headed(ax, title, sub, title_fs=12.5, pad=24):
    ax.set_title(title, loc="left", fontweight="bold", fontsize=title_fs, pad=pad)
    ax.text(0.0, 1.035, sub, transform=ax.transAxes, fontsize=8.5, color=FAINT)


def date_axis(ax, years=2):
    ax.xaxis.set_major_locator(mdates.YearLocator(years))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


DT = pd.to_datetime(all_days)


# ---------------------------------------------------- FIG1: cumulative net P&L
def fig_equity(figsize=(10, 5.2)):
    fig, ax = plt.subplots(figsize=figsize)
    for key, c, lw, lbl in [("overlay", OVERLAY, 2.0, "Overlay"),
                            ("baseline", BASELINE, 1.6, "Baseline")]:
        y = PORT[key].net.cumsum() / CAPITAL * 100
        ax.plot(DT, y, color=c, lw=lw, label=lbl)
        ax.annotate(lbl, (DT[-1], y.iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", color=c, fontsize=9.5,
                    fontweight="bold", va="center")
    # Sharpe and max drawdown per variant are stated in the caption (exhibits.md)
    headed(ax, "Cumulative net P&L — overlay vs baseline", SUB_FULL)
    ax.set_ylabel("% of capital")
    date_axis(ax)
    ax.margins(x=0.06)
    fig.tight_layout()
    return fig


# --------------------------------------------------------- FIG2: drawdown
# five worst overlay episodes, verbatim from strategy_results.md §8
EPISODES = [("1st worst −9.4%", "Jul 2008–Feb 2010", "2008-07-02", "2010-02-05"),
            ("2nd worst −6.8%", "Aug 2011–Jan 2013", "2011-08-31", "2013-01-04"),
            ("3rd worst −5.2%", "Jun 2001–May 2002", "2001-06-25", "2002-05-14"),
            ("4th worst −4.8%", "Apr 2004–Jul 2004", "2004-04-01", "2004-07-27"),
            ("5th worst −4.6%", "Oct 2022–Dec 2023", "2022-10-19", "2023-12-14")]


def decollide(fig, ax, labels, gap_px=4):
    """Sweep the episode labels left to right and push any label that runs
    into the previous one's box to its right. A no-op at the standard size,
    where the labels already clear each other; only narrow renders move."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    prev = None
    for t in sorted(labels, key=lambda t: t.get_position()[0]):
        bb = t.get_window_extent(r)
        if prev is not None and bb.x0 < prev.x1 + gap_px:
            x_px = (bb.x0 + bb.x1) / 2 + (prev.x1 + gap_px - bb.x0)
            t.set_x(ax.transData.inverted().transform((x_px, bb.y0))[0])
            bb = t.get_window_extent(r)
        prev = bb


def fig_drawdown(figsize=(10, 4.6), legend="header", title_fs=12.5):
    fig, ax = plt.subplots(figsize=figsize)
    for key, c, lw, lbl in [("baseline", BASELINE, 1.3, "Baseline"),
                            ("overlay", OVERLAY, 1.8, "Overlay")]:
        r = PORT[key].net.cumsum() / CAPITAL
        dd = ((r - r.cummax()) * 100).to_numpy(dtype=float)
        ax.plot(DT, dd, color=c, lw=lw, label=lbl)
    labels = []
    for line1, line2, peak, trough in EPISODES:
        t0, t1 = pd.to_datetime(peak), pd.to_datetime(trough)
        ax.axvspan(t0, t1, **SHADE)
        # anchor labels at the episode midpoint so adjacent episodes don't collide
        labels.append(ax.text(t0 + (t1 - t0) / 2, -12.3, f"{line1}\n{line2}",
                              ha="center", va="top", fontsize=7.4, color="#555555",
                              bbox=dict(fc="white", ec="none", alpha=0.8, pad=1)))
    ax.set_ylim(-14.4, 0.6)
    headed(ax, "Drawdown from high-water mark — five worst overlay episodes shaded",
           SUB_FULL, title_fs=title_fs, pad=24 if legend == "header" else 28)
    ax.set_ylabel("% of capital")
    if legend == "header":
        # legend in the header band, clear of the episode labels along the bottom
        fig.legend(loc="upper right", bbox_to_anchor=(0.97, 0.965), ncol=2,
                   frameon=False, fontsize=9)
    else:
        # narrow renders: no room beside the title, so stack the legend on the
        # subtitle line, flush right above the axes
        ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=1,
                  frameon=False, fontsize=9, borderaxespad=0, labelspacing=0.15)
    date_axis(ax)
    ax.margins(x=0.02)
    fig.tight_layout()
    decollide(fig, ax, labels)
    # keep the label band inside the axes at any height: if the two-line
    # labels would run past the axes bottom, extend the y-range downward
    # (never above the standard -14.4, so the standard figure is unchanged)
    r = fig.canvas.get_renderer()
    need_px = max(t.get_window_extent(r).height for t in labels) + 6
    ymin = -14.4
    for _ in range(3):
        px_per_unit = ax.bbox.height / (0.6 - ymin)
        ymin = min(-14.4, -12.3 - need_px / px_per_unit)
    ax.set_ylim(ymin, 0.6)
    return fig


# ------------------------------------------- FIG3: SI 2011 sizing diagnostic
def fig_si2011(figsize=(10, 4.6), month_step=3, title_fs=12.5):
    P, W0, W1 = "SI", "2010-09-01", "2012-03-31"
    win = [d for d in all_days if W0 <= d <= W1 and d in VARIANTS["overlay"][P].index]
    wdt = pd.to_datetime(win)
    fig, ax = plt.subplots(figsize=figsize)
    # 10-trading-day de-risk windows and their margin-hike effective dates
    first = True
    for d_e in events[P]:
        t_e = td_shift(P, d_e, 0)
        t_end = td_shift(P, t_e, 10) or win[-1]
        if t_e is None or t_end < W0 or t_e > W1:
            continue
        ax.axvspan(pd.to_datetime(t_e), pd.to_datetime(t_end), **SHADE,
                   label="de-risk window [t0, t0+10]" if first else None)
        ax.axvline(pd.to_datetime(t_e), color=MARK, lw=0.8, ls=":", alpha=0.65)
        tr = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
        ax.text(pd.to_datetime(t_e), 0.99, f" hike eff. {d_e}", transform=tr,
                rotation=90, va="top", ha="right", fontsize=7.2, color=MARK)
        first = False
    for key, c, lw, lbl in [("baseline", BASELINE, 1.5, "Baseline"),
                            ("overlay", OVERLAY, 1.9, "Overlay")]:
        ax.step(wdt, VARIANTS[key][P].pos_after[win], where="post",
                color=c, lw=lw, label=lbl)
    ax.axhline(0, color="#bbbbbb", lw=0.8)
    headed(ax, "Margin-based sizing around the 2011 silver margin episode",
           "SI position, contracts (fractional) · Sep 2010 – Mar 2012 · shaded: "
           "10-day de-risk window after each qualifying margin hike",
           title_fs=title_fs)
    ax.set_ylabel("contracts")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=month_step))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.margins(x=0.02)
    fig.tight_layout()
    return fig


# ------------------------------------------------- FIG4: annual net returns
def fig_annual(figsize=(10, 4.4)):
    net = PORT["overlay"].net
    years = sorted(set(d[:4] for d in all_days))
    ann = [net[[d for d in all_days if d.startswith(y)]].sum() / CAPITAL * 100
           for y in years]
    labels = [y if y != "2024" else "2024*" for y in years]
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(labels, ann, color=[OVERLAY if v >= 0 else BASELINE for v in ann],
           width=0.72, zorder=3)
    ax.axhline(0, color=INK, lw=1.3, zorder=4)
    headed(ax, "Annual net returns — overlay variant",
           "2001–2024 (*2024 through 03-28) · % of $500K capital · net of costs")
    ax.set_ylabel("% of capital")
    ax.tick_params(axis="x", rotation=60)
    fig.tight_layout()
    return fig


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
               ("2015–2020", "2015-2020"), ("2021–2024.03", "2021-2024.03"))]
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

# Printed-table styling: serif (the report body face), black on white only,
# booktabs-style three rules (above the header, below it, below the body) plus
# thin separators between the four column groups; the two sub-tables get the
# same three-rule treatment as independent tables. Layout in inches from the
# top-left corner; 150 dpi via rcParams.
FONT = "Times New Roman"          # Regular, Bold and Italic faces installed
BLACK = "#000000"
OUTER, INNER = 0.8, 0.5           # rule weights (pt): top/bottom vs mid/vertical
ROW = 0.225                       # body row pitch


def fig_summary_table(width=9.4, margin=0.45, fs_h=10, fs_b=9.5, fs_cap=9.5,
                      y_top=0.28, pad_bottom=0.28):
    """The figure's height follows from its content; width/margins/type sizes
    are parameters so the page assembly can set it in a narrower slot."""
    W = width
    L, R = margin, W - margin
    PAD = 0.10

    # main table: four groups side by side
    gw = (R - L) / len(GROUPS)
    y_head = y_top + 0.15             # header row centre
    y_mid = y_head + 0.15
    y_row0 = y_mid + 0.15
    y_bot = y_row0 + (len(GROUPS[0][1]) - 1) * ROW + 0.14
    # two compact sub-tables side by side, each its own three-rule table
    y_top2 = y_bot + 0.26
    y_head2 = y_top2 + 0.15
    y_mid2 = y_head2 + 0.15
    y_lab2 = y_mid2 + 0.15
    y_val2 = y_lab2 + ROW
    y_bot2 = y_val2 + 0.14
    GAP = 0.35
    x_split = L + (R - L - GAP) * 0.46       # room for the 2021–2024.03 label
    y_cap = y_bot2 + 0.30
    H = round(y_cap + pad_bottom, 4)

    fig = plt.figure(figsize=(W, H))
    X = lambda x: x / W
    Y = lambda y: 1 - y / H

    def txt(x, y, s, **kw):
        kw.setdefault("fontfamily", FONT)
        kw.setdefault("color", BLACK)
        return fig.text(X(x), Y(y), s, **kw)

    def rule(x0, y0, x1, y1, lw):
        fig.add_artist(Line2D([X(x0), X(x1)], [Y(y0), Y(y1)], color=BLACK, lw=lw,
                              solid_capstyle="butt", transform=fig.transFigure))

    rule(L, y_top, R, y_top, OUTER)
    rule(L, y_mid, R, y_mid, INNER)
    rule(L, y_bot, R, y_bot, OUTER)
    for g, (title, rows) in enumerate(GROUPS):
        x0, x1 = L + g * gw, L + (g + 1) * gw
        if g:
            rule(x0, y_top, x0, y_bot, INNER)
        txt(x0 + PAD, y_head, title, fontsize=fs_h, fontweight="bold", va="center")
        for i, (name, val) in enumerate(rows):
            y = y_row0 + i * ROW
            txt(x0 + PAD, y, name, fontsize=fs_b, va="center")
            txt(x1 - PAD, y, val, fontsize=fs_b, fontweight="bold", ha="right",
                va="center")

    for title, cols, x0, x1 in [
            ("Sub-period net Sharpe", sub_sharpe, L, x_split),
            ("Per-market net P&L ($K)", [(p, f"{v:.1f}") for p, v in PNL_COLS],
             x_split + GAP, R)]:
        rule(x0, y_top2, x1, y_top2, OUTER)
        rule(x0, y_mid2, x1, y_mid2, INNER)
        rule(x0, y_bot2, x1, y_bot2, OUTER)
        txt(x0 + PAD, y_head2, title, fontsize=fs_h, fontweight="bold", va="center")
        cw = (x1 - x0 - 2 * PAD) / len(cols)
        for j, (lab, val) in enumerate(cols):
            xr = x0 + PAD + (j + 1) * cw
            txt(xr, y_lab2, lab, fontsize=fs_b, ha="right", va="center")
            txt(xr, y_val2, val, fontsize=fs_b, fontweight="bold", ha="right",
                va="center")

    # caption: italic serif throughout, label then text, left-aligned
    lead = txt(L, y_cap, CAPTION[0], fontsize=fs_cap, fontstyle="italic",
               va="baseline")
    fig.canvas.draw()
    bb = lead.get_window_extent(fig.canvas.get_renderer())
    x_after = fig.transFigure.inverted().transform((bb.x1, 0))[0]
    txt(x_after * W, y_cap, CAPTION[1], fontsize=fs_cap, fontstyle="italic",
        va="baseline")
    return fig


if __name__ == "__main__":
    for make, name in ((fig_equity, "FIG1_equity.png"),
                       (fig_drawdown, "FIG2_drawdown.png"),
                       (fig_si2011, "FIG3_si2011.png"),
                       (fig_annual, "FIG4_annual.png"),
                       (fig_summary_table, "FIG_summary_table.png")):
        fig = make()
        fig.savefig(REPO / name)
        plt.close(fig)
    print("wrote FIG1_equity, FIG2_drawdown, FIG3_si2011, FIG4_annual, "
          "FIG_summary_table (.png)")
