# Strategy Spec v1.0 — Margin-Aware Trend (Path 2 build)

**Commit this file BEFORE the backtest runs. This is not a hypothesis test like the margin studies — it is an implementation of a documented premium plus a risk overlay — but the same discipline applies in one specific form: every parameter below is fixed now, no parameter will be searched or tuned against results, and every output listed in §7 is reported regardless of what it shows. The only comparison run is with-overlay vs. without-overlay.**

## 1. Universe, data, sample

- **Markets (9):** ZN, 6E, 6J, GC, SI, HG, CL, ZC, ZS. pysystemtrade instruments US10, EUR, JPY, GOLD, SILVER, COPPER, CRUDE_W, CORN, SOYBEAN.
- **Signal & P&L prices:** `data/prices_pst/` back-adjusted (panama) daily series. Because panama shifts price levels, ALL return math is done in **price points × point size = dollars per contract**, never in percent of the adjusted level. (Early negative adjusted levels are expected and harmless under this convention.)
- **Notional & margin ratio:** current unadjusted front price from the Stooq series (`data/prices/`) × point size. SI note: the SILVER series' contract-identity ambiguity (0.72% cross-check mismatch, logged in Stage 1) is immaterial for percent-vol and trend math; included with disclosure.
- **Margin events:** `data/margin_history_stitched.csv`, all 9 products, maintenance margin. Qualifying event = cumulative increase ≥5% within 5 business days, anchor-window clustered at 10 trading days (identical rule to the closed studies; only event DATES are used here — no post-event return is ever a signal).
- **Sample:** 2001-01-02 → 2024-03-28 (first year burned for lookbacks; endpoint = price-provenance end). Margin data begins later for some products (metals/CL 2009); before a product's margin start, the overlay simply has no margin input for it (realized vol only) — disclosed, not backfilled.

## 2. Signal (fixed)

- Trend measure per market: **sign of the trailing 252-trading-day change** in the adjusted price. Positive → long, negative → short, zero → flat.
- Evaluated at each Friday settlement (or last trading day of the week); positions executed at the **next trading day's settlement**. No intra-week trading except rolls.

## 3. Sizing (fixed — this is the contribution)

- **Portfolio vol target:** 10% annualized on $500,000 notional capital. Risk budget split equally: each market targets 1/9 of portfolio risk, no cross-correlation adjustment (disclosed simplification).
- **Per-market vol estimate (dollars/day):** sigma_hat = max(sigma_realized, sigma_margin), where:
  - sigma_realized = EWMA (36-day span) of daily dollar P&L per contract (point changes × point size);
  - sigma_margin = (maintenance margin per contract) / 2.33 — the exchange's margin as an implied 99% one-day move (z = 2.33), a first-principles constant, not fitted.
- **Contracts held** = (weekly risk budget in $/day) / sigma_hat, recomputed weekly; trades only when the target differs from holdings by ≥ 10% (buffer to suppress churn).
- **Post-hike de-risk:** for 10 trading days after a qualifying margin event in a market, that market's position target is halved. Rationale: the closed studies showed post-hike returns carry no direction but elevated noise; the exchange has certified a risk state.
- **Baseline (comparison) variant:** identical in every respect except sigma_hat = sigma_realized and no de-risk rule. This is the only A/B in the study.

## 4. Rolls

- Roll dates per market from `data/prices_pst/roll_calendars/`. After the calendars end (they end with the data), no extrapolation is needed (sample ends there too).
- Each roll: the full held position pays one round trip of costs (§5). Rolls do not change signal or size.

## 5. Costs (fixed)

- Per contract per side: **1 tick half-spread + $2.00 fees**; tick values hard-coded per product from CME specs (reuse the committed cost table).
- **Stress multiplier:** any trade executed in a week where that market's trailing 20-day realized vol is above its expanding-window 90th percentile pays **2 ticks** per side instead of 1.
- Charged on every contract traded: signal flips, size adjustments, and rolls, separately tallied.
- **Sensitivity rerun:** the full backtest repeated at 2× all costs. Reported regardless.

## 6. Integer-contract reality check

The primary backtest allows fractional contracts (research convention, stated). A second pass runs the with-overlay variant with positions rounded to whole contracts at $500K, reporting the tracking difference and which markets are un-sizeable — this feeds the Capital & Liquidity section.

## 7. Outputs — all reported, none optional

1. Equity curves, gross and net, overlay vs. baseline, 2001–2024.
2. Headline table: annualized return, vol, Sharpe, max drawdown, worst 12 months — gross and net, both variants.
3. Cost decomposition: bps/year from rebalancing vs. rolls vs. stress surcharges; annual turnover (contracts and notional).
4. Per-market contribution table (net P&L, vol, hit rate).
5. Sub-period table: 2001–2008, 2009–2014, 2015–2020, 2021–2024.03 — both variants (trend's weak decade must be visible, not smoothed).
6. Overlay diagnostics: % of days sigma_margin binds (by market and era); position-size time series for one illustrative market around a major margin episode (2011 SI or 2020).
7. Integer-contract results at $500K and the 2× cost sensitivity.
8. Drawdown table of the 5 worst episodes with dates and which markets drove them.

## 8. Honesty rules

If the overlay worsens net Sharpe, that is the reported result and the pitch says so. No sub-period, market exclusion, parameter, or cost assumption may be changed after results are seen. Any implementation ambiguity: resolve by the more conservative reading, log it in the results file.

---

## BUILD PROMPT (paste into a fresh Claude Code session)

Read strategy_spec_v1.md (this file) in the repo root; it is binding. Read prereg_margin_event_study_v2.md §A0 and h2_results.md only for context on data provenance — no logic from the closed studies' hypotheses may be reused as a signal. Stop-and-ask applies to genuine ambiguity; otherwise proceed.

1. **Data verification pass (no P&L yet):** load the 9 adjusted series, roll calendars, Stooq unadjusted series, and the stitched margin history. Verify: date coverage per market vs. §1; point sizes and tick values printed as a table for eyeball check; roll calendar counts per market per year (sane: ~12/yr CL, ~5/yr grains/metals, ~4/yr FX/ZN, ~6/yr GC); qualifying margin events per market per year for all 9 products. Print and pause for my confirmation.
2. **Build the backtest** exactly per §2–§6. Assert no lookahead: signals from data through Friday, execution at next settlement; margin events applied from their effective date forward only.
3. **Run** both variants, the integer-contract pass, and the 2× cost pass. Produce every §7 output as tables in `strategy_results.md` plus PNG charts (equity curves, drawdown chart, the overlay diagnostic).
4. Sanity checks before writing the report: net Sharpe must lie in a plausible band (−0.5 to +1.5) — anything outside means a bug hunt, not a celebration; per-market vol contributions roughly equal by construction; cost drag positive in every year.
5. Write `strategy_results.md` (first line: one-sentence headline, net overlay Sharpe and max DD), commit everything with "Path 2 backtest per strategy_spec_v1", and stop.
