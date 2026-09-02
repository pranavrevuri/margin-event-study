#!/usr/bin/env python3
"""
Data fetch for the packaging beta exhibit — NO strategy input, no strategy logic.
Downloads SPY (dividend-adjusted and unadjusted close) and ^GSPC (S&P 500 cash
index close) daily history from Yahoo Finance via yfinance (free, keyless; the
library performs Yahoo's cookie/crumb handshake — a bare curl of the same chart
endpoint is rate-limited with HTTP 429). Writes date-indexed CSVs to
data/prices/ covering 2000-12-01 → 2024-03-28 so the first strategy day
(2001-01-02) has a prior close. Read only by scripts/packaging_beta_lomo.py.
Note: Yahoo rescales SPY's adjusted close every time a new dividend is paid, so
absolute adj_close levels drift between downloads; daily returns do not.
"""
from pathlib import Path

import yfinance as yf

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data/prices"
START, END_EXCL = "2000-12-01", "2024-03-29"      # yfinance end is exclusive


def fetch(sym):
    h = yf.Ticker(sym).history(start=START, end=END_EXCL, interval="1d",
                               auto_adjust=False, actions=False)
    h.index = h.index.tz_localize(None).strftime("%Y-%m-%d")
    h.index.name = "date"
    return h


spy = fetch("SPY")[["Close", "Adj Close"]].rename(columns={"Close": "close", "Adj Close": "adj_close"})
spy.to_csv(OUT / "yahoo_SPY_daily_close.csv", float_format="%.6f")
gspc = fetch("^GSPC")[["Close"]].rename(columns={"Close": "close"})
gspc.to_csv(OUT / "yahoo_GSPC_daily_close.csv", float_format="%.6f")
for name, df in (("SPY", spy), ("^GSPC", gspc)):
    print(f"{name}: {len(df):,} rows {df.index[0]} → {df.index[-1]}")
