#!/usr/bin/env python3
"""
Packaging only — stacks the exhibits full width, in order, on a US Letter-width
page (8.5 in wide, 150 dpi, ~0.75 in margins) for pasting into a document. No
strategy logic, no data changes.

Each exhibit is RE-RENDERED at the content width and at its native aspect
ratio by the figure functions in scripts/exhibit_restyle.py (which reruns the
committed backtest unchanged and writes no PNGs when loaded this way), so text
keeps its designed point size instead of being downscaled with the image. The
only per-figure adaptations are the fitting hooks those functions expose:
legend placement and header size for the drawdown chart, its episode-label
de-collision, and the table's type size and margins. Captions for Figures 2-5
come from exhibits.md and are set like the summary table's caption (Times New
Roman italic); Figure 1 carries its own.

The page runs as tall as the content needs (default), or --pages auto splits
it into US Letter pages without breaking a figure across pages. A legibility
audit (minimum font size, text clipped at the image edge, overlapping text)
runs on every rendered figure and the exit status is 1 if it fails.

Usage: exhibits_page.py [--layout SPEC] [--pages 1|auto] [--out PATH]
  --layout  rows top to bottom, "/" between rows, "," for side by side
            (default "1/2/3/4/5": everything full width, in order)
  --pages   1 = one page as tall as needed (default); auto = US Letter pages,
            written as <out>_1.png, <out>_2.png, ... when more than one
"""
import argparse
import inspect
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
PAGE_W, LETTER_H = 1275, 1650           # US Letter portrait at 150 dpi
MARGIN = 112                            # ~0.75 in
CONTENT_W = PAGE_W - 2 * MARGIN
LETTER_CONTENT_H = LETTER_H - 2 * MARGIN
ROW_GAP, COL_GAP = 20, 30               # px between rows / between side-by-side slots
SERIF, FS_CAP = "Times New Roman", 9.5  # caption face and size, as in the summary table
LINE_H, CAP_GAP = 25, 8                 # caption line pitch / gap above a caption, px
MIN_PT = 7.0                            # legibility floor for any text on the page
LAYOUT = "1/2/3/4/5"
FUNC = {2: "fig_equity", 3: "fig_drawdown", 4: "fig_si2011", 5: "fig_annual"}

ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("--layout", default=LAYOUT, help='e.g. "1/2/3,4/5" (Figures 3 and 4 side by side)')
ap.add_argument("--pages", default="1", choices=["1", "auto"])
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


def native_size(fid):
    """The standard exhibit's figsize, read off the function's default."""
    return inspect.signature(EX[FUNC[fid]]).parameters["figsize"].default


def render(fid, w_px):
    """Re-render exhibit `fid` at w_px wide: the table at its natural height,
    the charts at their native aspect ratio."""
    w_in = w_px / DPI
    if fid == 1:
        return EX["fig_summary_table"](width=w_in, margin=0.02, fs_h=9, fs_b=8.5,
                                       fs_cap=FS_CAP, y_top=0.04, pad_bottom=0.06)
    nw, nh = native_size(fid)
    kw = {}
    if fid == 3 and w_in < 9:
        # below ~9 in the header band cannot hold title and legend side by side
        kw = dict(legend="subtitle", title_fs=11)
    return EX[FUNC[fid]](figsize=(w_in, w_in * nh / nw), **kw)


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


# --- caption typesetting (measured on a scratch canvas at page dpi)
meas = plt.figure(figsize=(1, 1), dpi=DPI)
renderer = meas.canvas.get_renderer()
CAP_KW = dict(transform=IdentityTransform(), fontfamily=SERIF, fontsize=FS_CAP,
              fontstyle="italic", color="black", va="baseline")   # italic serif throughout


def text_w(s):
    t = meas.text(0, 0, s, **CAP_KW)
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


def draw_caption(page, page_h, x, y_top, label, lines):
    y = page_h - (y_top + 20)            # first baseline; display origin is bottom-left
    page.text(x, y, label, **CAP_KW)
    page.text(x + text_w(label) + SPACE_W, y, lines[0], **CAP_KW)
    for i, ln in enumerate(lines[1:], 1):
        page.text(x, y - i * LINE_H, ln, **CAP_KW)


# --- render every row: images at native aspect, captions wrapped to slot width
problems, rows = [], []
for row in layout:
    w = (CONTENT_W - COL_GAP * (len(row) - 1)) // len(row)
    imgs, caps = [], []
    for j, fid in enumerate(row):
        x = MARGIN + j * (w + COL_GAP)
        fig = render(fid, w)
        problems += audit(fig, f"Figure {fid}")
        arr = to_array(fig)
        plt.close(fig)
        imgs.append((fid, x, arr))
        if fid != 1:
            caps.append((fid, x, *wrap(fid, w)))
        print(f"Figure {fid}: {arr.shape[1]}x{arr.shape[0]} px"
              + (f", caption {len(caps[-1][3])} line(s)" if fid != 1 else ""))
    rows.append(dict(imgs=imgs, caps=caps,
                     h=max(a.shape[0] for _, _, a in imgs),
                     cap_h=max([CAP_GAP + LINE_H * len(lines) for *_, lines in caps], default=0)))


def paginate(rows, limit):
    """Greedy fill of Letter pages; a row is never split across pages."""
    pages, cur, y = [], [], 0
    for r in rows:
        block = r["h"] + r["cap_h"]
        if cur and y + ROW_GAP + block > limit:
            pages.append(cur)
            cur, y = [], 0
        y += (ROW_GAP if cur else 0) + block
        cur.append(r)
    pages.append(cur)
    return pages


pages = paginate(rows, LETTER_CONTENT_H) if args.pages == "auto" else [rows]
out = Path(args.out)
names = ([out] if len(pages) == 1 else
         [out.with_name(f"{out.stem}_{i + 1}{out.suffix}") for i in range(len(pages))])
for rows_on_page, name in zip(pages, names):
    content_h = sum(r["h"] + r["cap_h"] for r in rows_on_page) + ROW_GAP * (len(rows_on_page) - 1)
    page_h = LETTER_H if args.pages == "auto" else max(LETTER_H, content_h + 2 * MARGIN)
    page = plt.figure(figsize=((PAGE_W + 0.01) / DPI, (page_h + 0.01) / DPI), dpi=DPI)
    y = MARGIN
    for r in rows_on_page:
        for fid, x, arr in r["imgs"]:
            page.figimage(arr, xo=x, yo=page_h - (y + arr.shape[0]), origin="upper")
        for fid, x, label, lines in r["caps"]:
            draw_caption(page, page_h, x, y + r["h"], label, lines)
        y += r["h"] + r["cap_h"] + ROW_GAP
    page.savefig(name, dpi=DPI, facecolor="white")
    plt.close(page)
    figs = [f for r in rows_on_page for f, _, _ in r["imgs"]]
    print(f"wrote {name} ({PAGE_W}x{page_h} px = {PAGE_W / DPI:.1f}x{page_h / DPI:.2f} in; "
          f"figures {figs})")

if problems:
    print(f"LEGIBILITY: FAIL — {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print(f"LEGIBILITY: PASS (no text below {MIN_PT}pt, nothing clipped, nothing overlapping)")
