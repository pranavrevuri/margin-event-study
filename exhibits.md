# Exhibits — Margin-Aware Trend (Path 2)

Sample 2001-01-02 → 2024-03-28, 9 CME markets, $500K capital, 10% ann. vol
target split 1/9 per market. Net = after rebalance, roll, and stress costs.
All numbers from strategy_results.md (spec: strategy_spec_v1.md).

![Figure 1](equity_curves_path2.png)
**Figure 1.** Cumulative net P&L, overlay vs baseline, 2001–2024, $500K.

![Figure 2](drawdown_path2.png)
**Figure 2.** Drawdown from high-water mark, net. The overlay's maximum
drawdown is −9.4% of capital vs −11.4% for the realized-vol-only baseline.

![Figure 3](overlay_diagnostic_si2011.png)
**Figure 3.** Margin-based sizing around the 2011 silver margin episode.

![Figure 4](annual_returns_path2.png)
**Figure 4.** Net return by calendar year, overlay variant (2024 through
03-28). Era dependence is visible: the strong years cluster in 2001–2008,
with thinner returns after.

**Table 1.** Headline statistics, 2001–2024.03.

| Run | Ann ret | Ann vol | Sharpe | Max DD | Worst 12m |
|---|---|---|---|---|---|
| overlay gross | 2.42% | 3.32% | 0.73 | −9.2% | −8.0% |
| overlay net | 2.21% | 3.32% | 0.67 | −9.4% | −8.1% |
| baseline gross | 3.13% | 4.46% | 0.70 | −11.3% | −9.6% |
| baseline net | 2.85% | 4.46% | 0.64 | −11.4% | −9.8% |
| overlay net, integer contracts | 1.74% | 2.54% | 0.68 | −5.8% | −5.5% |
| overlay net, 2× costs | 2.00% | 3.32% | 0.60 | −9.6% | −8.2% |
| baseline net, 2× costs | 2.57% | 4.46% | 0.58 | −11.6% | −9.9% |

**Table 2.** Sub-periods, net (ann ret / ann vol / Sharpe / max DD).

| Period | Overlay | Baseline |
|---|---|---|
| 2001–2008 | 4.54% / 4.49% / 1.01 / −7.5% | 4.70% / 4.79% / 0.98 / −8.0% |
| 2009–2014 | 1.15% / 2.83% / 0.41 / −6.8% | 2.46% / 4.24% / 0.58 / −10.9% |
| 2015–2020 | 0.71% / 2.22% / 0.32 / −3.8% | 0.69% / 4.14% / 0.17 / −10.5% |
| 2021–2024.03 | 1.28% / 2.36% / 0.54 / −4.6% | 3.11% / 4.61% / 0.67 / −7.9% |

**Table 3.** Cost decomposition, overlay variant (bps of capital per year;
sample years shown).

| Year | Rebal bps | Roll bps | Stress bps | Total bps | Contracts | Notional $M |
|---|---|---|---|---|---|---|
| 2001 | 26.6 | 24.1 | 7.1 | 57.7 | 156 | 5 |
| 2008 | 5.7 | 5.4 | 7.0 | 18.1 | 35 | 3 |
| 2020 | 6.0 | 5.2 | 1.4 | 12.6 | 36 | 4 |
| 2023 | 4.5 | 4.0 | 0.8 | 9.3 | 27 | 3 |
| **mean/yr** | 10.4 | 8.0 | 2.3 | 20.8 | 58 | 4 |
