#!/usr/bin/env python3
"""
Presentation only — NO change to strategy logic, parameters, or results.
Reads: the committed backtest (rerun unchanged via backtest_path2.py, which
reproduces the committed numbers exactly); drawdown-episode dates are taken
verbatim from, and every summary-table value is parsed out of, the committed
strategy_results.md; the two code exhibits are excerpts of backtest_path2.py
itself, read from disk at render time (never retyped).
Writes seven exhibit PNGs at 150 dpi — white background, a restrained palette
(navy overlay, gray baseline, muted red for losing years, muted syntax colors
in the code exhibits), serif type, each with its caption rendered beneath in
italic:
  FIG1_summary.png, FIG2_equity.png, FIG3_drawdown.png, FIG4_si2011.png,
  FIG5_annual.png, FIG6_sizing_code.png, FIG7_event_code.png
strategy_results.md is snapshot/restored, not modified. Needs pygments for the
code exhibits' tokenization.
"""
import re
import runpy
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.transforms as mtransforms
from matplotlib.lines import Line2D
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token

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
# restrained palette: navy overlay, gray baseline, muted red for losing years
NAVY = "#1b3a6b"          # overlay series, positive bars, event markers, headers
GRAY = "#8c8c8c"          # baseline series
RED = "#a94442"           # negative bars
LABEL = "#555555"         # drawdown episode labels
SHADE = dict(color=NAVY, alpha=0.08, lw=0)   # light navy-tinted bands
BLACK = "#000000"
INK = "#333333"
FAINT = "#777777"
SERIF = ["Times New Roman", "Times", "DejaVu Serif"]   # Regular/Bold/Italic installed
MONO = "Courier New"                                    # Regular/Bold/Italic installed
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": SERIF,
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
SUB_FULL = ("2001-01-02 – 2024-03-28 · 9 CME futures markets · $500K capital · "
            "net of costs, no compounding")

# captions, rendered beneath every exhibit in italic serif
CAPTIONS = {
    1: "Figure 1. Backtest summary.",
    2: "Figure 2. Cumulative net P&L, overlay vs baseline.",
    3: "Figure 3. Drawdown from high-water mark.",
    4: "Figure 4. Margin-based sizing, 2011 silver episode.",
    5: "Figure 5. Net return by calendar year.",
    6: "Figure 6. Position sizing implementation.",
    7: "Figure 7. Margin event detection.",
}
CAP_FS = 9.5
CAP_STRIP = 0.42      # inches reserved beneath a chart for its caption
CAP_BASE = 0.16       # caption baseline above the figure's bottom edge, inches


def headed(ax, title, sub):
    ax.set_title(title, loc="left", fontweight="bold", fontsize=12.5, pad=24)
    ax.text(0.0, 1.035, sub, transform=ax.transAxes, fontsize=8.5, color=FAINT)


def date_axis(ax, years=2):
    ax.xaxis.set_major_locator(mdates.YearLocator(years))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def chart(w, h):
    """A chart figure at its native size plus the caption strip."""
    return plt.subplots(figsize=(w, h + CAP_STRIP))


def finish(fig, ax, n):
    """tight_layout above the caption strip, then the caption aligned with the
    axes' left edge (as on the summary table)."""
    H = fig.get_figheight()
    fig.tight_layout(rect=(0, CAP_STRIP / H, 1, 1))
    fig.text(ax.get_position().x0, CAP_BASE / H, CAPTIONS[n], fontsize=CAP_FS,
             fontstyle="italic", color=BLACK, va="baseline")
    return fig


DT = pd.to_datetime(all_days)


# ---------------------------------------------------- FIG2: cumulative net P&L
def fig_equity():
    fig, ax = chart(10, 5.2)
    for key, c, lw, lbl in [("overlay", NAVY, 2.0, "Overlay"),
                            ("baseline", GRAY, 1.6, "Baseline")]:
        y = PORT[key].net.cumsum() / CAPITAL * 100
        ax.plot(DT, y, color=c, lw=lw, label=lbl)
        ax.annotate(lbl, (DT[-1], y.iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", color=c, fontsize=9.5,
                    fontweight="bold", va="center")
    headed(ax, "Cumulative net P&L, overlay vs baseline", SUB_FULL)
    ax.set_ylabel("% of capital")
    date_axis(ax)
    ax.margins(x=0.06)
    return finish(fig, ax, 2)


# --------------------------------------------------------- FIG3: drawdown
# five worst overlay episodes, verbatim from strategy_results.md §8
EPISODES = [("1st worst −9.4%", "Jul 2008–Feb 2010", "2008-07-02", "2010-02-05"),
            ("2nd worst −6.8%", "Aug 2011–Jan 2013", "2011-08-31", "2013-01-04"),
            ("3rd worst −5.2%", "Jun 2001–May 2002", "2001-06-25", "2002-05-14"),
            ("4th worst −4.8%", "Apr 2004–Jul 2004", "2004-04-01", "2004-07-27"),
            ("5th worst −4.6%", "Oct 2022–Dec 2023", "2022-10-19", "2023-12-14")]


def fig_drawdown():
    fig, ax = chart(10, 4.6)
    for key, c, lw, lbl in [("baseline", GRAY, 1.3, "Baseline"),
                            ("overlay", NAVY, 1.8, "Overlay")]:
        r = PORT[key].net.cumsum() / CAPITAL
        dd = ((r - r.cummax()) * 100).to_numpy(dtype=float)
        ax.plot(DT, dd, color=c, lw=lw, label=lbl)
    for line1, line2, peak, trough in EPISODES:
        t0, t1 = pd.to_datetime(peak), pd.to_datetime(trough)
        ax.axvspan(t0, t1, **SHADE)
        # labels at the episode midpoint, in the band below the deepest drawdown
        ax.text(t0 + (t1 - t0) / 2, -12.3, f"{line1}\n{line2}",
                ha="center", va="top", fontsize=7.4, color=LABEL)
    ax.set_ylim(-14.4, 0.6)
    headed(ax, "Drawdown from high-water mark, five worst overlay episodes shaded",
           SUB_FULL)
    ax.set_ylabel("% of capital")
    # legend in the header band, clear of the episode labels along the bottom
    fig.legend(loc="upper right", bbox_to_anchor=(0.97, 0.965), ncol=2,
               frameon=False, fontsize=9)
    date_axis(ax)
    ax.margins(x=0.02)
    return finish(fig, ax, 3)


# ------------------------------------------- FIG4: SI 2011 sizing diagnostic
def fig_si2011():
    P, W0, W1 = "SI", "2010-09-01", "2012-03-31"
    win = [d for d in all_days if W0 <= d <= W1 and d in VARIANTS["overlay"][P].index]
    wdt = pd.to_datetime(win)
    fig, ax = chart(10, 4.6)
    # 10-trading-day de-risk windows and their margin-hike effective dates
    first = True
    for d_e in events[P]:
        t_e = td_shift(P, d_e, 0)
        t_end = td_shift(P, t_e, 10) or win[-1]
        if t_e is None or t_end < W0 or t_e > W1:
            continue
        ax.axvspan(pd.to_datetime(t_e), pd.to_datetime(t_end), **SHADE,
                   label="de-risk window [t0, t0+10]" if first else None)
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
    return finish(fig, ax, 4)


# ------------------------------------------------- FIG5: annual net returns
def fig_annual():
    net = PORT["overlay"].net
    years = sorted(set(d[:4] for d in all_days))
    ann = [net[[d for d in all_days if d.startswith(y)]].sum() / CAPITAL * 100
           for y in years]
    labels = [y if y != "2024" else "2024*" for y in years]
    fig, ax = chart(10, 4.4)
    ax.bar(labels, ann, color=[NAVY if v >= 0 else RED for v in ann],
           width=0.72, zorder=3)
    ax.axhline(0, color=INK, lw=1.3, zorder=4)
    headed(ax, "Annual net returns, overlay variant",
           "2001–2024 (*2024 through 03-28) · % of $500K capital · net of costs")
    ax.set_ylabel("% of capital")
    ax.tick_params(axis="x", rotation=60)
    return finish(fig, ax, 5)


# ------------------------------------------------ FIG1: factsheet summary table
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

# Printed-table styling: serif, black on white only, booktabs-style three rules
# (above the header, below it, below the body) plus thin separators between the
# four column groups; the two sub-tables get the same three-rule treatment as
# independent tables. Layout in inches from the top-left corner.
OUTER, INNER = 0.8, 0.5           # rule weights (pt): top/bottom vs mid/vertical
FS_H, FS_B = 10, 9.5              # header / body point sizes
ROW = 0.225                       # body row pitch


def fig_summary_table():
    W = 9.4
    L, R = 0.45, W - 0.45
    PAD = 0.10
    gw = (R - L) / len(GROUPS)
    y_top = 0.28
    y_head = y_top + 0.15             # header row centre
    y_mid = y_head + 0.15
    y_row0 = y_mid + 0.15
    y_bot = y_row0 + (len(GROUPS[0][1]) - 1) * ROW + 0.14
    y_top2 = y_bot + 0.26             # sub-tables
    y_head2 = y_top2 + 0.15
    y_mid2 = y_head2 + 0.15
    y_lab2 = y_mid2 + 0.15
    y_val2 = y_lab2 + ROW
    y_bot2 = y_val2 + 0.14
    GAP = 0.35
    x_split = L + (R - L - GAP) * 0.46       # room for the 2021–2024.03 label
    y_cap = y_bot2 + 0.30
    H = round(y_cap + 0.28, 4)

    fig = plt.figure(figsize=(W, H))
    X = lambda x: x / W
    Y = lambda y: 1 - y / H

    def txt(x, y, s, **kw):
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
        txt(x0 + PAD, y_head, title, fontsize=FS_H, fontweight="bold", color=NAVY,
            va="center")
        for i, (name, val) in enumerate(rows):
            y = y_row0 + i * ROW
            txt(x0 + PAD, y, name, fontsize=FS_B, va="center")
            txt(x1 - PAD, y, val, fontsize=FS_B, fontweight="bold", ha="right",
                va="center")
    for title, cols, x0, x1 in [
            ("Sub-period net Sharpe", sub_sharpe, L, x_split),
            ("Per-market net P&L ($K)", [(p, f"{v:.1f}") for p, v in PNL_COLS],
             x_split + GAP, R)]:
        rule(x0, y_top2, x1, y_top2, OUTER)
        rule(x0, y_mid2, x1, y_mid2, INNER)
        rule(x0, y_bot2, x1, y_bot2, OUTER)
        txt(x0 + PAD, y_head2, title, fontsize=FS_H, fontweight="bold", color=NAVY,
            va="center")
        cw = (x1 - x0 - 2 * PAD) / len(cols)
        for j, (lab, val) in enumerate(cols):
            xr = x0 + PAD + (j + 1) * cw
            txt(xr, y_lab2, lab, fontsize=FS_B, ha="right", va="center")
            txt(xr, y_val2, val, fontsize=FS_B, fontweight="bold", ha="right",
                va="center")
    txt(L, y_cap, CAPTIONS[1], fontsize=CAP_FS, fontstyle="italic", va="baseline")
    return fig


# ------------------------------------------------ FIG6 / FIG7: code excerpts
# Verbatim lines of the committed script, dedented for display and tokenized
# with pygments; muted syntax colors.
CODE_FS = 9
CODE_STYLE = [
    (Token.Keyword, dict(fontweight="bold", color=NAVY)),
    (Token.Operator.Word, dict(fontweight="bold", color=NAVY)),   # and, or, not, in, is
    (Token.Comment, dict(fontstyle="italic", color=FAINT)),
    (Token.Literal.String, dict(color="#2e6b3f")),
    (Token.Literal.Number, dict(color=RED)),
]


def token_style(ttype):
    for t, st in CODE_STYLE:
        if ttype in t:
            return st
    return dict(color="#1a1a1a")


def find_block(rel_path, first_marker, last_marker):
    """Line range of the excerpt: from the line containing first_marker to the
    next line whose stripped text equals last_marker."""
    lines = (REPO / rel_path).read_text().splitlines()
    first = next(i for i, l in enumerate(lines, 1) if first_marker in l)
    last = next(i for i, l in enumerate(lines, 1) if i >= first and l.strip() == last_marker)
    return rel_path, first, last


def fig_code(n, rel_path, first, last):
    lines = (REPO / rel_path).read_text().splitlines()[first - 1:last]
    lines = textwrap.dedent("\n".join(lines)).split("\n")
    # monospace advance, measured
    probe = plt.figure(figsize=(1, 1))
    t = probe.text(0, 0, "M" * 20, fontfamily=MONO, fontsize=CODE_FS)
    cw = t.get_window_extent(probe.canvas.get_renderer()).width / 20 / probe.dpi
    plt.close(probe)
    LH = CODE_FS * 1.45 / 72                 # line pitch, inches
    ML, MT, GUT = 0.35, 0.30, 5               # margins (in) and gutter (chars)
    W = max(6.5, 2 * ML + (GUT + max(map(len, lines))) * cw)
    y0 = MT + 0.30                            # first code baseline
    H = round(y0 + (len(lines) - 1) * LH + 0.10 + CAP_STRIP, 3)
    fig = plt.figure(figsize=(W, H))
    X = lambda x: x / W
    Y = lambda y: 1 - y / H
    fig.text(X(ML), Y(MT), f"{rel_path}, lines {first}–{last}", fontsize=8.5,
             fontstyle="italic", color=FAINT, va="baseline")
    for k, line in enumerate(lines):
        y = y0 + k * LH
        fig.text(X(ML + (GUT - 1.5) * cw), Y(y), str(first + k), fontfamily=MONO,
                 fontsize=CODE_FS, color="#999999", ha="right", va="baseline")
        col = 0
        for ttype, text in lex(line, PythonLexer()):
            text = text.rstrip("\n")
            if text.strip():
                fig.text(X(ML + (GUT + col) * cw), Y(y), text, fontfamily=MONO,
                         fontsize=CODE_FS, va="baseline", **token_style(ttype))
            col += len(text)
    fig.text(X(ML), CAP_BASE / H, CAPTIONS[n], fontsize=CAP_FS, fontstyle="italic",
             color=BLACK, va="baseline")
    return fig


# sigma = max(realized, margin-implied) -> contract target, de-risk halving,
# integer rounding (inside run_market's weekly loop)
FIG6_SRC = find_block("scripts/backtest_path2.py",
                      "# realized vol and margin-implied vol",
                      "target = float(np.rint(target))")
# maintenance level on a business-day grid, the >=5% five-day cumulative
# increase test, and the 10-trading-day anchor clustering (qualifying_events)
FIG7_SRC = find_block("scripts/backtest_path2.py",
                      "# maintenance margin level by effective date", "i = j")

if __name__ == "__main__":
    for make, name in ((fig_summary_table, "FIG1_summary.png"),
                       (fig_equity, "FIG2_equity.png"),
                       (fig_drawdown, "FIG3_drawdown.png"),
                       (fig_si2011, "FIG4_si2011.png"),
                       (fig_annual, "FIG5_annual.png"),
                       (lambda: fig_code(6, *FIG6_SRC), "FIG6_sizing_code.png"),
                       (lambda: fig_code(7, *FIG7_SRC), "FIG7_event_code.png")):
        fig = make()
        fig.savefig(REPO / name)
        plt.close(fig)
    print("wrote FIG1_summary, FIG2_equity, FIG3_drawdown, FIG4_si2011, "
          "FIG5_annual, FIG6_sizing_code, FIG7_event_code (.png)")
    print(f"FIG6 excerpt: {FIG6_SRC[0]} lines {FIG6_SRC[1]}-{FIG6_SRC[2]} | "
          f"FIG7 excerpt: {FIG7_SRC[0]} lines {FIG7_SRC[1]}-{FIG7_SRC[2]}")
