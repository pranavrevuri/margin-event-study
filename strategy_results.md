Net of costs, the margin-aware overlay ran 2001–2024.03 at a Sharpe of 0.67 with a maximum drawdown of -9.4% of capital, vs 0.64 and -11.4% for the realized-vol-only baseline — the overlay improved net Sharpe.

# Strategy Results — Margin-Aware Trend (Path 2), per strategy_spec_v1.md

Sample 2001-01-02 → 2024-03-28, 9 markets, $500K capital, 10% ann. vol target split 1/9 per market (no correlation adjustment — disclosed; realized portfolio vol is therefore well below 10%). Returns are daily $ P&L / $500K, arithmetic, no compounding; Sharpe uses rf = 0 (futures excess-return convention). All parameters fixed in strategy_spec_v1.md before any result was computed.

## 1–2. Headline table (equity curves: equity_curves_path2.png)

| Variant | Ann ret | Ann vol | Sharpe | Max DD | Worst 12m |
|---|---|---|---|---|---|
| overlay gross | 2.42% | 3.32% | 0.73 | -9.2% | -8.0% |
| overlay net | 2.21% | 3.32% | 0.67 | -9.4% | -8.1% |
| baseline gross | 3.13% | 4.46% | 0.70 | -11.3% | -9.6% |
| baseline net | 2.85% | 4.46% | 0.64 | -11.4% | -9.8% |

![equity](equity_curves_path2.png)
![drawdown](drawdown_path2.png)

## 3. Cost decomposition and turnover (overlay variant)

| Year | Rebal cost bps | Roll cost bps | Stress surcharge bps | Total bps | Contracts traded | Notional traded $M |
|---|---|---|---|---|---|---|
| 2001 | 26.6 | 24.1 | 7.1 | 57.7 | 156 | 5 |
| 2002 | 39.0 | 20.9 | 4.5 | 64.3 | 183 | 6 |
| 2003 | 26.8 | 18.4 | 7.3 | 52.5 | 132 | 5 |
| 2004 | 9.6 | 12.3 | 6.7 | 28.6 | 69 | 4 |
| 2005 | 19.7 | 14.7 | 3.3 | 37.7 | 106 | 7 |
| 2006 | 18.4 | 9.8 | 4.4 | 32.5 | 90 | 6 |
| 2007 | 17.0 | 9.4 | 4.5 | 30.9 | 80 | 7 |
| 2008 | 5.7 | 5.4 | 7.0 | 18.1 | 35 | 3 |
| 2009 | 4.3 | 4.7 | 1.9 | 10.9 | 29 | 3 |
| 2010 | 8.2 | 4.9 | 1.6 | 14.8 | 42 | 4 |
| 2011 | 3.3 | 3.8 | 2.2 | 9.4 | 23 | 3 |
| 2012 | 5.5 | 4.8 | 0.8 | 11.2 | 34 | 4 |
| 2013 | 3.5 | 5.0 | 0.5 | 9.1 | 28 | 3 |
| 2014 | 5.7 | 5.5 | 0.1 | 11.3 | 36 | 4 |
| 2015 | 3.1 | 5.1 | 0.0 | 8.3 | 27 | 2 |
| 2016 | 9.2 | 5.3 | 0.1 | 14.6 | 46 | 4 |
| 2017 | 8.3 | 6.2 | 0.0 | 14.5 | 48 | 4 |
| 2018 | 8.8 | 7.5 | 0.0 | 16.4 | 52 | 5 |
| 2019 | 7.6 | 6.8 | 0.0 | 14.4 | 46 | 4 |
| 2020 | 6.0 | 5.2 | 1.4 | 12.6 | 36 | 4 |
| 2021 | 3.6 | 4.2 | 0.5 | 8.4 | 25 | 3 |
| 2022 | 3.0 | 4.0 | 1.4 | 8.4 | 22 | 3 |
| 2023 | 4.5 | 4.0 | 0.8 | 9.3 | 27 | 3 |
| 2024 | 1.8 | 0.9 | 0.0 | 2.7 | 9 | 1 |
| **mean/yr** | 10.4 | 8.0 | 2.3 | 20.8 | 58 | 4 |

## 4. Per-market contribution (overlay, net)

| Market | Net P&L $K | Daily vol $ | Hit rate | Rolls in sample |
|---|---|---|---|---|
| ZN | 43.3 | 273 | 51.1% | 93 |
| 6E | 14.3 | 266 | 48.7% | 93 |
| 6J | 33.1 | 228 | 51.3% | 93 |
| GC | 29.4 | 276 | 51.4% | 140 |
| SI | 25.0 | 281 | 51.6% | 116 |
| HG | 50.5 | 287 | 50.3% | 93 |
| CL | 42.4 | 277 | 51.0% | 23 |
| ZC | 5.5 | 258 | 48.9% | 23 |
| ZS | 18.2 | 247 | 50.2% | 23 |

## 5. Sub-periods (net)

| Period | Overlay ret/vol/Sharpe/maxDD | Baseline ret/vol/Sharpe/maxDD |
|---|---|---|
| 2001-2008 | 4.54% / 4.49% / 1.01 / -7.5% | 4.70% / 4.79% / 0.98 / -8.0% |
| 2009-2014 | 1.15% / 2.83% / 0.41 / -6.8% | 2.46% / 4.24% / 0.58 / -10.9% |
| 2015-2020 | 0.71% / 2.22% / 0.32 / -3.8% | 0.69% / 4.14% / 0.17 / -10.5% |
| 2021-2024.03 | 1.28% / 2.36% / 0.54 / -4.6% | 3.11% / 4.61% / 0.67 / -7.9% |

## 6. Overlay diagnostics

Share of weekly sizing days where sigma_margin > sigma_realized (binds), by market and era (— = no margin data yet):

| Market | 2001-2008 | 2009-2014 | 2015-2020 | 2021-2024.03 | Full |
|---|---|---|---|---|---|
| ZN | 57% | 93% | 98% | 100% | 87% |
| 6E | 50% | 92% | 97% | 99% | 80% |
| 6J | 81% | 96% | 98% | 100% | 92% |
| GC | — | 93% | 100% | 100% | 97% |
| SI | — | 89% | 100% | 100% | 96% |
| HG | — | 94% | 99% | 99% | 97% |
| CL | — | 95% | 99% | 100% | 98% |
| ZC | 62% | 93% | 99% | 100% | 88% |
| ZS | 66% | 99% | 100% | 100% | 91% |

![SI 2011](overlay_diagnostic_si2011.png)

## 7. Integer-contract pass ($500K) and 2× cost sensitivity

| Run | Ann ret | Ann vol | Sharpe | Max DD | Worst 12m |
|---|---|---|---|---|---|
| overlay net (fractional) | 2.21% | 3.32% | 0.67 | -9.4% | -8.1% |
| overlay net INTEGER | 1.74% | 2.54% | 0.68 | -5.8% | -5.5% |
| overlay net 2× costs | 2.00% | 3.32% | 0.60 | -9.6% | -8.2% |
| baseline net 2× costs | 2.57% | 4.46% | 0.58 | -11.6% | -9.9% |

Integer-pass sizing feasibility (median absolute fractional target, overlay): markets rounding to zero most weeks are un-sizeable at $500K.

| Market | Median \|target\| (contracts) | Un-sizeable? |
|---|---|---|
| ZN | 0.63 | no |
| 6E | 0.35 | YES |
| 6J | 0.33 | YES |
| GC | 0.20 | YES |
| SI | 0.15 | YES |
| HG | 0.25 | YES |
| CL | 0.22 | YES |
| ZC | 0.82 | no |
| ZS | 0.34 | YES |

Tracking difference, integer vs fractional overlay: net P&L $206.2K vs $261.8K (-1111 bps of capital over the sample).

## 8. Five worst drawdown episodes (overlay, net)

| Depth | Peak | Trough | Recovered | Top negative markets peak→trough |
|---|---|---|---|---|
| -9.4% | 2008-07-02 | 2010-02-05 | 2011-08-30 | 6E $-13K, CL $-11K, SI $-8K |
| -6.8% | 2011-08-31 | 2013-01-04 | 2014-11-03 | ZS $-11K, GC $-7K, HG $-6K |
| -5.2% | 2001-06-25 | 2002-05-14 | 2003-01-08 | CL $-9K, ZS $-8K, SI $-4K |
| -4.8% | 2004-04-01 | 2004-07-27 | 2004-11-24 | ZN $-7K, ZC $-5K, SI $-5K |
| -4.6% | 2022-10-19 | 2023-12-14 | not recovered | 6E $-8K, GC $-5K, SI $-4K |

## Sanity checks (build prompt step 4)

- Net overlay Sharpe 0.67 — inside the plausible band [−0.5, +1.5]: PASS.
- Per-market gross daily vol (target ≈ $350/day): ZN $273, 6E $266, 6J $228, GC $276, SI $281, HG $287, CL $277, ZC $258, ZS $247.
- Cost drag positive in every year: PASS.

## Disclosures and implementation log (spec §8)

- **Fragility of the A/B verdict:** an initial run of this same code contained a calendar bug (weekend-stamped partial Globex rows treated as trading days, so some weekly evaluations landed on Sunday-stamped prices — 646 such rows in SI alone). Fixing it (R14) moved net Sharpe from 0.66/0.69 (overlay/baseline) to the final numbers and FLIPPED the sign of the overlay-vs-baseline comparison. The overlay-minus-baseline Sharpe difference is therefore noise-level (~±0.03–0.05) and should not be pitched as an edge; the robust effect is the drawdown/vol reduction.
- **CL/ZC/ZS annual cycle (user-confirmed):** the pysystemtrade source holds only the December (CL, ZC) / November (ZS) contract, rolling ~1×/yr — not a front-month series. Roll costs for these three understate a monthly-rolled real-world implementation, and the held contract is a deferred contract most of the year (lower vol, different carry). Affects Capital & Liquidity claims.
- **Roll dates (user-confirmed):** PRICE_CONTRACT switch dates from multiple/*.csv — the rolls actually embedded in the adjusted P&L series; the committed roll_calendars end 2020–2022 and match the switches (±1-day stamp convention) where both exist. The switch source counts MORE rolls (more cost).
- **SI series:** contract-identity ambiguity (0.72% Stage-1 cross-check mismatch) — immaterial for trend/vol math; included per spec §1 with this disclosure.
- Before a product's margin history begins (metals/CL 2009; ZC/ZS 2003-11; ZN 2004-01), the overlay has no margin input: sigma_hat = sigma_realized and no de-risk events — disclosed, not backfilled.
- R3 Trade buffer: trade iff |target−held| ≥ 10% × |target|; a zero target with nonzero holdings always closes; trades go to the full target.
- R4 De-risk window = event entry day (first trading day on/after the effective date) through +10 trading days inclusive, applied when the Friday evaluation date falls inside it (the closed studies' [t0, t0+10] convention).
- R5 Stress flag evaluated at the trade-execution date: trailing 20-td std of daily $ P&L per contract above its expanding 90th percentile (expanding from 2000-01-01, min 60 obs). Cost model only.
- R6 Rolls in stress periods pay 2 ticks per side too ('any trade').
- R7 Roll cost charged on the position entering the roll day (pre-rebalance).
- R8 Returns arithmetic on fixed $500K; no compounding; rf = 0.
- R9 All Friday inputs use data dated ≤ the Friday; execution next trading day settlement; margin levels and events apply from effective date forward only (asserted).
- R10 Integer pass: nearest-integer targets, same buffer rule.
- R11 Margin-binding shares computed on weekly sizing days.
- R12 SI/CL/ZC/ZS tick values hard-coded from CME specs (committed table covers only ZN/6E/6J/GC/HG); eyeball-confirmed in the step-1 pause.
- R13 Hit rate = share of days with a position where net daily P&L > 0.
- R14 Daily calendar: weekend-stamped rows in the pysystemtrade files (partial Globex sessions, e.g. 646 Sunday rows in SI) are dropped; the latest stamp per weekday date is taken as the settlement (no hour filter — grain settlements 2020-22 are stamped 19:00). Weekly evaluations therefore land on Fridays (or the week's last weekday).

## Add-on exhibit: block-bootstrap Monte Carlo

Generated by scripts/monte_carlo_exhibit.py after the main report (rerunning it
re-appends this section); no strategy logic touched. The overlay variant's net
daily returns were resampled into 1,000 alternative equity curves with a
stationary block bootstrap (geometric block lengths, mean 21 trading
days, wrap-around, seed 42). Because every path is drawn from the same realized
return distribution, this is a path-luck exhibit — how much of the terminal
outcome is sequencing — not an independent test of the strategy.

- Actual terminal net P&L: 52.4% of capital — the
  **54th percentile** of the simulated terminal distribution.
- Simulated terminal P&L percentiles: 5th 24.1%, median 50.8%,
  95th 79.1% of capital.

![Monte Carlo](monte_carlo_exhibit.png)

## Add-on exhibit: time in market and capital utilization

Generated by scripts/exposure_beta_exhibit.py from the committed backtest rerun
unchanged (overlay variant, fractional contracts). Notional = unadjusted Stooq
front price × point size (the spec §1 convention); margin = maintenance level
in effect that day.

| Measure | Full sample | 2009-01-12+ (all 9 margined) |
|---|---|---|
| Trading days with any position (portfolio) | 100.0% | — |
| Average gross exposure / capital | 55% | 48% |
| Average maintenance margin posted / capital | 1.10% | 1.37% |

Per-market share of days with a position: ZN 100.0%, 6E 100.0%, 6J 100.0%, GC 100.0%, SI 100.0%, HG 100.0%, CL 100.0%, ZC 99.9%, ZS 99.9%

**Idle capital, stated plainly:** the portfolio holds positions on
100.0% of days and runs ≈55% of capital in gross
futures notional, but the cash actually consumed as maintenance margin averages
only 1.1% of the $500K (1.4% once all
nine markets have margin data; CME speculative initial margin ≈ 110% of
maintenance, so ≈1.5% at initiation). Roughly
98% of capital sits in cash at all times — an
opportunity cost if left unremunerated, or T-bill yield if swept, which this
backtest does not credit (returns are excess-return-style, rf = 0, per R8).
Pre-2009 the margin-usage figure is understated because metals/CL margin
history has not started (disclosed, not backfilled).

## Add-on exhibit: beta to equities and bonds

Equity series: **Stooq es.f** — E-mini S&P 500 continuous futures front-month
splice (same free source family as the committed futures data; unadjusted
splice, ~4 small quarterly roll jumps/yr add noise but no directional bias).
Chosen because Stooq's free ETF depth stops at 2005-02 and its cash-index
series (^SPX, renamed ^USLC) only reaches back to 2013. Cross-checks: ES vs
SPY daily-return correlation on 2005+ overlap = 0.982; overlay-vs-SPY
full-overlap beta = -0.0207 (vs ES-based
-0.0209 on
the same window). Bond series: **Stooq agg.us** — iShares Core U.S. Aggregate
Bond ETF, adjusted close, 2005-02-25 → 2024-03-28 (83% of sample). OLS of
daily overlay net returns on market daily returns; 95% CI = ±1.96 classical SE.

| Window | Beta vs ES | 95% CI | R² | Corr | Days |
|---|---|---|---|---|---|
| Full 2001–2024.03 | -0.0234 | [-0.0277, -0.0190] | 1.86% | -0.136 | 5,889 |
| 2001-2008 | -0.0306 | [-0.0396, -0.0217] | 2.20% | -0.148 | 2,003 |
| 2009-2014 | -0.0168 | [-0.0245, -0.0091] | 1.18% | -0.109 | 1,545 |
| 2015-2020 | -0.0179 | [-0.0239, -0.0119] | 2.16% | -0.147 | 1,527 |
| 2021-2024.03 | -0.0194 | [-0.0289, -0.0100] | 1.96% | -0.140 | 814 |
| Full, baseline variant | -0.0300 | [-0.0358, -0.0242] | 1.69% | -0.130 | 5,889 |

Bond correlation (overlay net vs AGG): full overlap corr = -0.035
(beta -0.0201, R² 0.12%); by sub-period: 2001-2008 +0.022, 2009-2014 +0.129, 2015-2020 +0.010, 2021-2024.03 -0.458

**Stated plainly:** the strategy is effectively equity-market-neutral — a PM
would book it as such — with a small but statistically significant NEGATIVE
equity beta (-0.023, CI excludes zero, stable in sign across all
four sub-periods): equity direction explains under
2.2% of daily variance in every window, and
what dependence exists makes it a mild diversifier, not a hidden long. Bond
neutrality holds on the full sample (corr -0.04) but NOT
period-by-period: in 2021–2024.03 the correlation to AGG was
-0.46, because the trend overlay was short fixed income
through the 2022 hiking cycle — a real, if episodic, bond-direction exposure.

## Beta and correlation

OLS of overlay net daily returns on S&P 500 daily returns over the full
backtest sample, 2001-01-02 → 2024-03-28 (generated by
scripts/packaging_beta_lomo.py from the committed backtest rerun unchanged).
Primary series: **SPY dividend-adjusted close from Yahoo Finance** (free,
keyless, fetched by scripts/fetch_yahoo_sp500.py); the S&P 500 cash index
(^GSPC, same source) is the robustness row. The Stooq SPY row is the earlier
2005-02-28+ figure (Stooq's free ETF depth starts there) and the ES continuous
futures row is the regression already reported in the equity/bond beta exhibit
above. SE = classical OLS; NW SE = Newey-West with 21 lags. Strategy days
with no equity print (137 US equity holidays on which CME traded) are
dropped; no equity days lack a strategy return. Vendor check: Yahoo vs Stooq
SPY daily-return correlation on the overlap = 0.9989, and the Yahoo
series gives beta -0.0209 on Stooq's window vs Stooq's
-0.0207.

| Market series | Window | Beta | SE | NW SE | Corr | R² | Days |
|---|---|---|---|---|---|---|---|
| SPY adj. (Yahoo) | 2001-01-02 → 2024-03-28 | -0.0237 | 0.0022 | 0.0039 | -0.137 | 1.87% | 5,846 |
| ^GSPC (Yahoo) | 2001-01-02 → 2024-03-28 | -0.0248 | 0.0022 | 0.0038 | -0.144 | 2.06% | 5,846 |
| SPY adj. (Stooq) | 2005-02-28 → 2024-03-28 | -0.0207 | 0.0023 | 0.0042 | -0.131 | 1.70% | 4,803 |
| ES cont. futures (Stooq) | 2001-01-02 → 2024-03-28 | -0.0234 | 0.0022 | 0.0037 | -0.136 | 1.86% | 5,889 |

Beta to the S&P 500 over the full sample is -0.02 (SE
0.0022; Newey-West SE 0.0039, about
6 robust SEs below zero), correlation -0.14:
economically negligible and slightly negative, and the same to three decimals
whether the index is measured by SPY, the cash index, or ES futures.

## Leave-one-market-out (overlay net)

Overlay net Sharpe recomputed nine times, each time excluding one market
(portfolio P&L minus that market's P&L — exact, since sizing is per-market
independent). Full 9-market overlay net Sharpe: 0.67.

| Excluded market | Sharpe | Δ vs full | Ann ret | Ann vol | Max DD |
|---|---|---|---|---|---|
| ZN | 0.59 | -0.07 | 1.84% | 3.12% | -10.4% |
| 6E | 0.69 | +0.03 | 2.08% | 3.02% | -7.6% |
| 6J | 0.62 | -0.05 | 1.93% | 3.13% | -10.4% |
| GC | 0.68 | +0.01 | 1.96% | 2.90% | -8.4% |
| SI | 0.67 | +0.01 | 1.99% | 2.96% | -7.9% |
| HG | 0.59 | -0.07 | 1.78% | 3.00% | -8.9% |
| CL | 0.61 | -0.06 | 1.85% | 3.05% | -7.7% |
| ZC | 0.69 | +0.03 | 2.16% | 3.11% | -8.3% |
| ZS | 0.66 | -0.00 | 2.05% | 3.10% | -7.9% |

Sharpe stays in [0.59, 0.69] whichever market is dropped —
no single market carries the result.
