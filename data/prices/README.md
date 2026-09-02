# Price Data — Provenance and Status

Downloaded 2026-08-25. **STATUS: DEGRADED OPTION, PENDING USER DECISION.**
Prereg A2 requires daily settlement prices of INDIVIDUAL contracts; these files are
continuous front-month series — the best available FREE, KEYLESS data, but they do
NOT satisfy A2 as written. No analysis may treat them as the preregistered price
source without an explicit prereg amendment.

## Files

`stooq_<PRODUCT>_continuous.csv` for ZN, 6E, 6J, GC, SI, HG, CL, ZC, ZS.
Columns: date, open, high, low, close. Rows: 1999-01-04 → 2026-08-24 (~6,950-7,000
rows each; source history extends decades earlier — deliberately trimmed to 1999+,
one year before the earliest margin-data start, to bound the download).

## Source

- Stooq (stooq.com), symbols CL.F, GC.F, SI.F, HG.F, ZC.F, ZS.F, ZN.F, E6.F (Euro FX), J6.F (Japanese Yen).
- Retrieved via the site's HTML5-chart data endpoint (`/q/a2/d/?s=<sym>&i=d`, paged
  backward with `&f=<date>`), fetched from a real browser session because the CSV
  export endpoint (`/q/d/l/`) now requires a login and the chart endpoint validates
  browser session cookies. The bulk-database page is gated behind a code-entry
  authorization and was not used.
- License/terms: Stooq provides data free for personal, non-commercial use; it is a
  data AGGREGATOR and publishes no upstream license for futures data. Treat as
  research-grade reference data, not redistributable, and not exchange-official.

## Series construction (empirically determined)

- **Continuous front-month splice, NOT back-adjusted** (raw prices concatenated):
  price jumps occur at rolls.
- **Roll dates are NOT published** and rolls happen EARLY (before contract expiry):
  on 2020-04-20, CL.F shows 20.43 — the settlement of the June-2020 contract (CLM20)
  — while the still-active May contract (CLK20) settled at −37.63. The series had
  already rolled ≥2 sessions before CLK20's last trade date. Roll timing is
  therefore only inferable (e.g., volume/price-jump heuristics), not documented.
- **Close = exchange settlement of the then-front contract**, verified exactly on
  CL for 2020-04-20 (20.43) and 2020-04-21 (11.57), both matching CME's published
  CLM20 settlements; ZN prices are decimalized 32nds consistent with CBOT
  settlement conventions. Verification is spot-check level, not row-by-row.
- Volume/open-interest are not provided by this endpoint.
- Rows dated before each product's futures existence (deep history on the source)
  are spliced cash/spot data upstream; irrelevant here since files start 1999.
- The last row on download day was an unsettled LIVE quote (and J6.F's showed a
  100× vendor scale glitch that day); all 2026-08-25 rows were removed. Files end
  at the last completed settlement, 2026-08-24.

## Why individual contracts are not here

No free, keyless source of historical per-contract daily settlements exists for
these products (2026-08 survey):
- **Stooq**: continuous only — individual contract symbols (e.g. clk20.f, clz25.f) do not exist.
- **Yahoo Finance**: per-contract data exists for ACTIVE contracts only (with full
  life history, e.g. CLZ26 back to 2017); expired contracts are purged ("No data
  found"). Useless for the past; viable only as a forward-archiving strategy.
- **CME official**: free settlement files cover only the current/most recent
  session; history is CME DataMine (paid).
- **Quandl/Nasdaq Data Link**: the free per-contract CME database was removed
  years ago; no maintained public mirror found.
- **Barchart/Databento/PortaraCQG/FirstRate**: paid and/or API-key products.

## Impact on the study design (for the amendment decision)

The prereg computes event returns on a single contract inside ±15-day windows with
no rolls. An unadjusted continuous series violates this when a roll lands inside a
window: the splice jump (contango/backwardation gap) contaminates the return. Roll
frequency: monthly for CL, bimonthly GC, ~5/yr ZC/ZS/SI/HG, quarterly ZN/6E/6J —
so a nontrivial fraction of windows WILL contain a roll, and roll dates are not
published for this series. This is why substitution requires an explicit decision,
not a silent swap.

## Auxiliary series for the Path 2 beta/correlation exhibit (added 2026-08-26)

`stooq_ES_continuous_close.csv`, `stooq_SPY_adjusted_close.csv`,
`stooq_AGG_adjusted_close.csv` — date,close only. Same Stooq chart endpoint
(`/q/a2/d/?s=<sym>&i=d`, paged backward with `&f=`, real browser session),
symbols es.f, spy.us, agg.us. Used ONLY by scripts/exposure_beta_exhibit.py
(equity beta / bond correlation of the finished backtest); never a strategy
input. Notes: es.f is an unadjusted front-month splice (quarterly roll jumps);
spy.us/agg.us are dividend-adjusted closes and Stooq's free US-ETF depth stops
at 2005-02-25; Stooq's cash S&P 500 symbol (^SPX) was renamed ^USLC and its
free daily history now starts 2013, hence the futures series for the full
sample.

## Full-sample S&P 500 series for the packaging beta (added 2026-09-02)

`yahoo_SPY_daily_close.csv` (date, close, adj_close) and
`yahoo_GSPC_daily_close.csv` (date, close) — written by
`scripts/fetch_yahoo_sp500.py`: Yahoo Finance daily history via yfinance 1.5.2
(free, keyless; the library performs Yahoo's cookie/crumb handshake — a bare
curl of the same v8 chart endpoint is answered with HTTP 429), symbols SPY and
^GSPC, 2000-12-01 → 2024-03-28, 5,866 rows each. Used ONLY by
`scripts/packaging_beta_lomo.py` for the full-sample beta/correlation of the
finished backtest; never a strategy input. Notes: `adj_close` is Yahoo's
dividend-adjusted SPY close — Yahoo rescales the whole adjusted history each
time a new dividend is paid, so absolute levels differ between downloads while
daily returns do not; ^GSPC is the cash index price level (no dividends). Vendor
check against `stooq_SPY_adjusted_close.csv` on the 2005-02-28+ overlap:
daily-return correlation 0.9989; 36 of 4,803 days differ by more than 10 bp.
The largest (2015-03-12/13, ~2%) is a displaced Stooq print — Yahoo's raw and
adjusted closes agree with each other there — and the two vendors agree on the
2015-03-20 ex-dividend day, so the rest are rounding and adjustment-timing
noise; none moves the regression (see strategy_results.md).
