#!/usr/bin/env python3
"""
Add-on exhibit — NO change to strategy logic. Bar chart of calendar-year net
returns (% of $500K capital) for the overlay variant, from the committed
backtest_path2.py rerun unchanged. Saves annual_returns_path2.png.
"""
import runpy
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
bt = runpy.run_path(REPO / "scripts/backtest_path2.py")
net = bt["PORT"]["overlay"].net
CAPITAL = bt["CAPITAL"]

years = sorted(set(d[:4] for d in net.index))
ann = {y: net[[d for d in net.index if d.startswith(y)]].sum() / CAPITAL * 100
       for y in years}
labels = [y if y != "2024" else "2024*" for y in years]

BLUE = "#2a78d6"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#cccccc",
                     "axes.labelcolor": "#333333", "text.color": "#333333",
                     "xtick.color": "#555555", "ytick.color": "#555555",
                     "axes.grid": True, "grid.color": "#e8e8e8",
                     "grid.linewidth": 0.7, "figure.facecolor": "white",
                     "axes.facecolor": "white"})
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.bar(labels, [ann[y] for y in years], color=BLUE, width=0.72, zorder=3)
ax.axhline(0, color="#999999", lw=1.0, zorder=4)
ax.set_title("Overlay variant — net return by calendar year, % of $500K capital "
             "(*2024 through 03-28)")
ax.set_ylabel("% of capital")
ax.grid(axis="x", visible=False)
ax.tick_params(axis="x", rotation=60)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(REPO / "annual_returns_path2.png", dpi=150)
plt.close(fig)
neg = [y for y in years if ann[y] < 0]
print("annual net returns (% capital):",
      {y: round(ann[y], 2) for y in years})
print(f"negative years: {len(neg)}/{len(years)} -> {neg}")
print("wrote annual_returns_path2.png")
