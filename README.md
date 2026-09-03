# margin-event-study

A preregistered study of whether CME maintenance-margin increases predict
futures returns (they don't — both directions failed their one-shot tests),
followed by "Path 2": a margin-aware trend-following backtest that uses margin
levels only for risk sizing, never as a return signal. Everything was specified
and committed before results were computed; the honesty rules in
[strategy_spec_v1.md](strategy_spec_v1.md) §8 and the preregistrations are
binding, and failures are reported verbatim.

## Where the preregistrations live

- [prereg_margin_event_study.md](prereg_margin_event_study.md) → v1 (reversal hypothesis)
- [prereg_margin_event_study_v2.md](prereg_margin_event_study_v2.md), [prereg_margin_event_study_v3.md](prereg_margin_event_study_v3.md) → amended universe/data; pilot FAILED ([PILOT_FAIL](PILOT_FAIL), [pilot_results_v3.md](pilot_results_v3.md))
- [prereg_margin_event_study_H2.md](prereg_margin_event_study_H2.md) → continuation hypothesis on untouched 2015–2024 data; FAILED ([H2_FAIL](H2_FAIL), [h2_results.md](h2_results.md))
- [strategy_spec_v1.md](strategy_spec_v1.md) → Path 2 backtest spec, committed before the backtest ran; results in [strategy_results.md](strategy_results.md)

## Script run order

Closed studies (committed artifacts of the preregistered runs; kept verbatim,
do not edit):

1. `scripts/parse_margins.py`, `scripts/parse_advisories.py`,
   `scripts/parse_wayback_margins.py` — parse the three margin-history sources
2. `scripts/stitch_coverage.py` — union them into `data/margin_history_stitched.csv`
3. `scripts/stage1_v2.py` / `scripts/stage1_v3.py` — events + K0 gates (no returns)
4. `scripts/stage2_v3.py` — pilot one-shot (FAIL); `scripts/h2_oneshot.py` — H2 one-shot (FAIL)

Path 2 backtest (rerunnable end to end; each later script reruns the backtest
internally and preserves the report sections already appended):

1. `scripts/verify_data.py` — step-1 data verification tables (no P&L)
2. `scripts/backtest_path2.py` — the backtest; writes `strategy_results.md` + 3 PNGs
3. `scripts/monte_carlo_exhibit.py` — bootstrap exhibit (appends section + PNG)
4. `scripts/annual_returns_exhibit.py` — annual-returns bar chart PNG
5. `scripts/exposure_beta_exhibit.py` — time-in-market and equity/bond beta sections
6. `scripts/fetch_yahoo_sp500.py` — Yahoo SPY/^GSPC closes for the full-sample
   S&P 500 beta (output committed under `data/prices/`; rerun only to refresh)
7. `scripts/packaging_beta_lomo.py` — beta/correlation vs the S&P 500 over the
   full sample and the leave-one-market-out table
8. `scripts/exhibit_restyle.py` — FIG1–FIG4 and FIG_summary_table PNGs assembled in
   [exhibits.md](exhibits.md)
9. `scripts/exhibits_page.py` — exhibits re-rendered at slot size on one US Letter
   page (EXHIBITS_PAGE.png; Figures 1, 2, 3, 5 by default), with a legibility audit

## Where the data comes from

- `data/prices_pst/` — pysystemtrade repository (GPL-3.0; Barchart/IB-collected)
  per-contract settlements, panama-adjusted series, roll calendars; ends 2024-03-28.
- `data/prices/` — Stooq continuous futures (research-grade, cross-validation +
  notional convention), the auxiliary Stooq ES/SPY/AGG closes and the Yahoo
  SPY/^GSPC closes for the beta exhibits; provenance and caveats in
  [data/prices/README.md](data/prices/README.md).
- `data/margin_history_stitched.csv` — CME maintenance margins stitched from
  Wayback-archived history PDFs, clearing advisories, and daily snapshots;
  construction and conflict handling in `scripts/stitch_coverage.py` and
  `coverage_report.md`.
