#!/usr/bin/env python3
"""
Packaging only — assembles the five exhibits on one US Letter portrait page
(EXHIBITS_PAGE.png, 1275 x 1650 px at 150 dpi, ~0.75 in margins) for pasting
into a document. No strategy logic, no data changes.

Each exhibit is RE-RENDERED at its slot size by the figure functions in
scripts/exhibit_restyle.py (which reruns the committed backtest unchanged and
writes no PNGs when loaded this way), so text keeps its designed point size
instead of being downscaled with the image. The only per-figure adaptations
are the fitting hooks those functions expose: legend placement, tick spacing,
header size, episode-label de-collision, and the table's type size/margins.
Captions for Figures 2-5 are read from exhibits.md and set like the summary
table's caption (Times New Roman italic); Figure 1 carries its own.

A legibility audit runs on every rendered figure — minimum font size, text
clipped at the image edge, overlapping text — and is printed; the exit status
is 1 if it fails, so a bad page never passes silently.

Usage: exhibits_page.py [--layout SPEC] [--out PATH]
  --layout  rows top to bottom, "/" between rows, "," for side by side, e.g.
            "1/2/3,4/5". Default "1/2/3/5": Figure 4 (the SI-2011 diagnostic)
            is left off because beside Figure 3 at half width both charts fail
            the audit, and five full-width rows leave every chart too short.
"""
import argparse
import io
import re
import runpy
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import IdentityTransform

REPO = Path(__file__).resolve().parent.parent
DPI = 150
PAGE_W, PAGE_H = 1275, 1650             # US Letter portrait at 150 dpi
MARGIN = 112                            # ~0.75 in
CONTENT_W, CONTENT_H = PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN
ROW_GAP, COL_GAP = 20, 30               # px between rows / between side-by-side slots
SERIF, FS_CAP = "Times New Roman", 9.5  # caption face and size, as in the summary table
LINE_H, CAP_GAP = 25, 8                 # caption line pitch / gap above a caption, px
MIN_PT = 7.0                            # legibility floor for any text on the page
LAYOUT = "1/2/3/5"                      # see the docstring for why Figure 4 is off
WEIGHT = {2: 0.9, 3: 1.05, 4: 1.05, 5: 0.95}   # relative slot heights for the chart
# rows: the drawdown chart carries a label band inside the axes and the bar
# chart carries rotated year labels, so both need more height than the equity curve

ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("--layout", default=LAYOUT, help='e.g. "1/2/3,4/5" (Figures 3 and 4 side by side)')
ap.add_argument("--out", default=str(REPO / "EXHIBITS_PAGE.png"))
args = ap.parse_args()
layout = [[int(f) for f in row.split(",")] for row in args.layout.split("/")]

# figure functions (+ the backtest rerun they need); __name__ != "__main__"
# inside run_path, so the standard PNGs are not rewritten
EX = runpy.run_path(str(REPO / "scripts/exhibit_restyle.py"))

# chart captions come from exhibits.md; Figure 1 carries its own caption
md = (REPO / "exhibits.md").read_text()
CAPTIONS = {int(n): " ".join(body.split()) for n, body in
            re.findall(r"^\*\*Figure (\d+)\.\*\* (.+?)(?=\n\n|\Z)", md, re.M | re.S)}


def render(fid, w_px, h_px=None):
    """Re-render exhibit `fid` for a w_px x h_px slot (the table sets its own height)."""
    w_in = w_px / DPI
    narrow = w_px < 0.6 * CONTENT_W                # a half-width slot
    if fid == 1:
        return EX["fig_summary_table"](width=w_in, margin=0.02, fs_h=9, fs_b=8.5,
                                       fs_cap=FS_CAP, y_top=0.04, pad_bottom=0.06)
    size = (w_in, h_px / DPI)
    if fid == 2:
        return EX["fig_equity"](figsize=size)
    if fid == 3:
        return EX["fig_drawdown"](figsize=size, legend="subtitle", title_fs=11)
    if fid == 4:
        return EX["fig_si2011"](figsize=size, month_step=6 if narrow else 3, title_fs=11)
    if fid == 5:
        return EX["fig_annual"](figsize=size)
    raise ValueError(fid)


def tick_texts(axis):
    lo, hi = sorted(axis.get_view_interval())
    return [t.label1 for t in axis.get_major_ticks()
            if lo <= t.get_loc() <= hi and t.label1.get_text()]


def oriented_rect(t, bb, shrink=1.0):
    """(centre, half-extents, angle) of a text's glyph rectangle. Rotated text
    is tested as the rotated rectangle itself, not its axis-aligned envelope
    (which is what get_window_extent returns), so tightly spaced rotated tick
    labels are not reported as overlapping when their glyphs are clear. The
    rectangle is shrunk by `shrink` px per side so touching edges don't count."""
    th = np.deg2rad(t.get_rotation() % 180)
    c, s_ = abs(np.cos(th)), abs(np.sin(th))
    W, H = bb.width, bb.height
    det = c * c - s_ * s_
    if abs(det) < 1e-6:                          # 45 degrees: fall back to the envelope
        w, h, th = W, H, 0.0
    else:
        w, h = (W * c - H * s_) / det, (H * c - W * s_) / det
    return (np.array([(bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2]),
            np.array([max(w / 2 - shrink, 0.1), max(h / 2 - shrink, 0.1)]), th)


def rects_overlap(a, b):
    """Separating-axis test for two oriented rectangles."""
    (ca, ha, ta), (cb, hb, tb) = a, b
    axes = [np.array([np.cos(t), np.sin(t)]) for t in (ta, ta + np.pi / 2, tb, tb + np.pi / 2)]
    d = cb - ca
    for ax_ in axes:
        ra = ha[0] * abs(ax_ @ np.array([np.cos(ta), np.sin(ta)])) + \
             ha[1] * abs(ax_ @ np.array([-np.sin(ta), np.cos(ta)]))
        rb = hb[0] * abs(ax_ @ np.array([np.cos(tb), np.sin(tb)])) + \
             hb[1] * abs(ax_ @ np.array([-np.sin(tb), np.cos(tb)]))
        if abs(ax_ @ d) > ra + rb:
            return False
    return True


def audit(fig, name):
    """Legibility problems in a rendered figure: type below MIN_PT, text
    clipped at the image edge, text overlapping other text."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.bbox.width, fig.bbox.height
    texts = list(fig.texts)
    for leg in fig.legends:
        texts += leg.get_texts()
    for ax in fig.axes:
        texts += list(ax.texts) + [ax.title, ax.xaxis.label, ax.yaxis.label]
        texts += tick_texts(ax.xaxis) + tick_texts(ax.yaxis)
        if ax.get_legend():
            texts += ax.get_legend().get_texts()
    out, boxes = [], []
    for t in texts:
        s = t.get_text().strip()
        if not s or not t.get_visible():
            continue
        bb = t.get_window_extent(r)
        if bb.width <= 0 or bb.height <= 0:
            continue
        short = s.replace("\n", " / ")[:42]
        if t.get_fontsize() < MIN_PT:
            out.append(f"{name}: '{short}' is {t.get_fontsize()}pt (< {MIN_PT}pt)")
        if bb.x0 < -0.5 or bb.y0 < -0.5 or bb.x1 > W + 0.5 or bb.y1 > H + 0.5:
            out.append(f"{name}: '{short}' is clipped at the image edge")
        boxes.append((short, oriented_rect(t, bb)))
    for (sa, a), (sb, b) in combinations(boxes, 2):
        if rects_overlap(a, b):
            out.append(f"{name}: '{sa}' overlaps '{sb}'")
    return out


def to_array(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI)
    buf.seek(0)
    return plt.imread(buf)


page = plt.figure(figsize=(PAGE_W / DPI, PAGE_H / DPI), dpi=DPI)
renderer = page.canvas.get_renderer()
CAP_KW = dict(transform=IdentityTransform(), fontfamily=SERIF, fontsize=FS_CAP,
              fontstyle="italic", color="black", va="baseline")   # italic serif throughout


def text_w(s, **kw):
    t = page.text(0, 0, s, **CAP_KW, **kw)
    w = t.get_window_extent(renderer).width
    t.remove()
    return w


SPACE_W = text_w("x x") - text_w("xx")


def wrap(fid, width_px):
    """Greedy word wrap of a chart caption to its slot width; the first line
    starts after the 'Figure N.' label."""
    label = f"Figure {fid}."
    avail = width_px - text_w(label) - SPACE_W
    lines, cur = [], ""
    for word in CAPTIONS[fid].split():
        trial = f"{cur} {word}".strip()
        if text_w(trial) <= avail:
            cur = trial
        else:
            lines.append(cur)
            cur, avail = word, width_px
    lines.append(cur)
    return label, lines


def draw_caption(x, y_top, label, lines):
    y = PAGE_H - (y_top + 20)            # first baseline; display origin is bottom-left
    page.text(x, y, label, **CAP_KW)
    page.text(x + text_w(label) + SPACE_W, y, lines[0], **CAP_KW)
    for i, ln in enumerate(lines[1:], 1):
        page.text(x, y - i * LINE_H, ln, **CAP_KW)


# --- vertical budget: the table takes its natural height, chart rows share
# what is left in proportion to WEIGHT, after captions and gaps are set aside
slots = {}
for row in layout:
    w = (CONTENT_W - COL_GAP * (len(row) - 1)) // len(row)
    for j, fid in enumerate(row):
        slots[fid] = (MARGIN + j * (w + COL_GAP), w)
table_fig = render(1, slots[1][1]) if 1 in slots else None
table_h = int(round(table_fig.get_figheight() * DPI)) if table_fig else 0
caps = {fid: wrap(fid, slots[fid][1]) for fid in slots if fid != 1}
row_cap = [max((CAP_GAP + LINE_H * len(caps[f][1])) if f != 1 else 0 for f in row)
           for row in layout]
avail = CONTENT_H - table_h - sum(row_cap) - ROW_GAP * (len(layout) - 1)
wsum = sum(max(WEIGHT[f] for f in row) for row in layout if 1 not in row)
row_h = [table_h if 1 in row else int(avail * max(WEIGHT[f] for f in row) / wsum)
         for row in layout]
if avail <= 0:
    sys.exit(f"no vertical room left for the charts ({avail} px)")

# --- compose, top to bottom
problems = []
y = MARGIN
for row, h, cap_h in zip(layout, row_h, row_cap):
    for fid in row:
        x, w = slots[fid]
        fig = table_fig if fid == 1 else render(fid, w, h)
        problems += audit(fig, f"Figure {fid}")
        arr = to_array(fig)
        plt.close(fig)
        ah, aw = arr.shape[:2]
        page.figimage(arr, xo=x, yo=PAGE_H - (y + ah), origin="upper")
        if fid != 1:
            draw_caption(x, y + ah, *caps[fid])
        print(f"Figure {fid}: {aw}x{ah} px at ({x}, {y})"
              + (f", caption {len(caps[fid][1])} line(s)" if fid != 1 else ""))
    y += h + cap_h + ROW_GAP

out = Path(args.out)
page.savefig(out, dpi=DPI, facecolor="white")
print(f"wrote {out} ({PAGE_W}x{PAGE_H} px, layout {layout})")
if problems:
    print(f"LEGIBILITY: FAIL — {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("LEGIBILITY: PASS (no text below "
      f"{MIN_PT}pt, nothing clipped, nothing overlapping)")
