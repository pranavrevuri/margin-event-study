# margin-event-study

A preregistered study of whether CME maintenance-margin increases predict futures returns, followed by a trend-following backtest that uses margin levels only for position sizing.

## What this repo contains

The work has two parts.

**Part 1, the event study.** The hypothesis was that a CME maintenance-margin increase predicts the next ten trading days of returns in that contract. Two directions were tested, a reversal and a continuation, each under a preregistration committed before any return was computed. Both failed their preregistered tests. The failure sentences, fixed in advance, are recorded verbatim in [PILOT_FAIL](PILOT_FAIL) and [H2_FAIL](H2_FAIL).

**Part 2, the backtest.** With the return signal dead, the follow-on question was whether margin levels are useful for risk sizing instead. A weekly trend-following system on nine CME futures was specified in full, costs included, in [strategy_spec_v1.md](strategy_spec_v1.md) and committed before the backtest ran. The results are in [strategy_results.md](strategy_results.md) and the figures in [exhibits.md](exhibits.md). The margin-aware variant is called the overlay and the realized-volatility-only variant is called the baseline. The results file refers to this part as Path 2.

Two rules governed the whole project. Every specification was committed before its results were computed, and every failure is reported in the words fixed in advance. Section 8 of the strategy spec states the reporting rules for the backtest: the result is reported whichever way it comes out, and no parameter, sub-period, market, or cost assumption may change after results are seen.

## Preregistration trail

Read these in order.

1. [prereg_margin_event_study.md](prereg_margin_event_study.md). Version 1. Reversal hypothesis, ten products. Committed before any data was viewed.
2. [data_gate_report.md](data_gate_report.md) and [coverage_report.md](coverage_report.md). What margin data could be obtained, and how the three sources were stitched together. No returns were computed.
3. [prereg_margin_event_study_v2.md](prereg_margin_event_study_v2.md). Version 2. Universe and price source amended to what the data allowed. Each amendment is explained and each was made before any return was computed. Its data-quality gate failed: window completeness was 84.6 percent against a 90 percent floor. The failure is recorded in the amendment log at the top of version 3, rerunning `scripts/stage1_v2.py` reproduces the printout, and the event list it built is [data/events_v2.csv](data/events_v2.csv).
4. [prereg_margin_event_study_v3.md](prereg_margin_event_study_v3.md). Version 3. Amended the data-quality gate and the contract-selection fallback. [LOG.md](LOG.md) records the provenance of this version. The gate passed; the record is [stage1_v3_k0_record.txt](stage1_v3_k0_record.txt) and the event list is [data/events_v3.csv](data/events_v3.csv).
5. Pilot test of the reversal hypothesis on data through 2014: FAILED. [pilot_results_v3.md](pilot_results_v3.md), [PILOT_FAIL](PILOT_FAIL).
6. [prereg_margin_event_study_H2.md](prereg_margin_event_study_H2.md). The continuation hypothesis, tested once on untouched 2015 to 2024 data: FAILED. [h2_results.md](h2_results.md), [h2_run_log.txt](h2_run_log.txt), [H2_FAIL](H2_FAIL).
7. [strategy_spec_v1.md](strategy_spec_v1.md). The backtest specification, committed before the backtest ran. Results: [strategy_results.md](strategy_results.md).

Terms used in those documents:

- Stage 1 builds the event list and checks data quality. Stage 2 computes returns. The Stage 1 checks are called the K0 gates: minimum event counts and a minimum share of events with complete price windows, with thresholds fixed in advance.
- One-shot means the test script ran exactly once and its printout was committed as the verdict.
- The pilot is the Stage 2 test on data through 2014-12-31. The 2015 to 2024 data was held back and touched only by the H2 test.

To verify the ordering yourself:

```bash
git log --format='%h %ad %s' --date=iso -- prereg_margin_event_study*.md stage1_v3_k0_record.txt PILOT_FAIL H2_FAIL strategy_spec_v1.md
```

Each of those files has exactly one commit. The backtest script was edited twice after its results were committed, on 2026-08-27 and 2026-09-02, to change comments and docstrings and remove two unused names. The committed results reproduce byte for byte from the current script.

## Setup

Python 3.12. Install the pinned dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Scripts locate the repository from their own path, so they can be run from any working directory.

## Reproduce

To rebuild `strategy_results.md` from the committed data, run these four scripts in order. Each later script reruns the backtest internally and appends its own section, so the order matters. The four together take about fifteen seconds on a laptop.

```bash
python3 scripts/backtest_path2.py
python3 scripts/monte_carlo_exhibit.py
python3 scripts/exposure_beta_exhibit.py
python3 scripts/packaging_beta_lomo.py
```

Optional, after the four above:

```bash
python3 scripts/verify_data.py
python3 scripts/annual_returns_exhibit.py
python3 scripts/exhibit_restyle.py
```

The first prints data checks and writes nothing. The second writes `annual_returns_path2.png`. The third writes the seven FIG PNGs used in `exhibits.md` and needs the full results file, so run it last.

`scripts/fetch_yahoo_sp500.py` downloads the Yahoo SPY and S&P 500 closes into `data/prices/`. Its output is committed. Rerun it only to refresh, and note that Yahoo rescales SPY's adjusted close after each dividend, so price levels will differ between downloads while daily returns will not.

The closed studies can also be rerun. They regenerate the committed records identically, apart from the timestamp inside the gzip header of the snapshots file:

```bash
python3 scripts/parse_margins.py
python3 scripts/stitch_coverage.py
python3 scripts/stage1_v2.py
python3 scripts/stage1_v3.py
python3 scripts/stage2_v3.py
python3 scripts/h2_oneshot.py
```

Two caveats. `stitch_coverage.py` writes its two data files, then tries to write a summary table to a path outside the repository; on any other machine that final step fails with a file-not-found error after the data files are complete. The two remaining parsers, `parse_wayback_margins.py` and `parse_advisories.py`, need the raw caches described below and are not needed to reproduce anything.

## Data sources

- **CME margin history**, stitched by `scripts/stitch_coverage.py` into `data/margin_history_stitched.csv`. Construction and conflict handling are in [coverage_report.md](coverage_report.md). Three sources:
  - Daily snapshot PDFs from CME's historical margins page, 2020-06 to 2026-06, committed in `data/margin_pdfs/` and parsed by `scripts/parse_margins.py`. Details in [data_gate_report.md](data_gate_report.md).
  - Pre-2020 margin history PDFs recovered from web.archive.org captures, parsed by `scripts/parse_wayback_margins.py`.
  - CME clearing advisories, the performance bond notices, 2016 to 2020, parsed by `scripts/parse_advisories.py`.
- **Futures prices, `data/prices_pst/`.** Per-contract settlements, back-adjusted continuous series, and roll calendars from the pysystemtrade repository, collected from Barchart and Interactive Brokers, ending 2024-03-28. Back-adjusted means earlier prices are shifted by each roll gap so the series has no roll jumps. This is the price source for the studies and the backtest. Provenance and checks in [data/prices_pst/README.md](data/prices_pst/README.md).
- **Futures prices, `data/prices/`.** Stooq continuous front-month series for the same nine products, used to cross-check the pysystemtrade prices and to compute dollar notional, plus Stooq ES, SPY and AGG closes and Yahoo SPY and S&P 500 closes used only for the beta exhibits. Provenance in [data/prices/README.md](data/prices/README.md).

**Raw inputs not in this repository.** The 80 Wayback captures and the 1,918 clearing-notice pages with 827 attachments that feed the two pre-2020 parsers total about 381 MB and are not committed. They are available on request. The parsed outputs they produce are committed in `data/`, so every study and the backtest reproduce without them. To rerun those two parsers, set the `SP` path constant near the top of each script to the directory holding the caches.

**Data license caveat.** Stooq provides data free for personal, non-commercial use and publishes no upstream license for futures data. The pysystemtrade repository is GPL-3.0, but the redistribution rights of the market data it ships are not separately licensed. The CME PDFs and advisories are CME publications. Treat all price and margin data here as reference data for research, not as exchange-official records, and obtain licensed data for any commercial use.
