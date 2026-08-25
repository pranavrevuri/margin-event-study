# Preregistration v2.0 and Prompt — Margin-Increase Event Study

**Supersedes v1.0. Commit this file BEFORE running any stage of Part B. v1.0 remains in the repo untouched as the record of the original design.**
**Binding rule unchanged: nothing in Part A may be edited after any result it governs has been viewed. Amendments require a new version committed before the amended analysis runs.**

---

## A0. Amendment log — every change from v1.0, and why each is outcome-blind

**Status at amendment time: margin-event availability and price-data availability have been examined. ZERO return calculations of any kind have been run or viewed. The git history proves the ordering.**

1. **Universe: 10 products → 6 confirmatory (ZN, 6E, 6J, GC, SI, HG) + 3 exploratory (CL, ZC, ZS) + ES dropped.** Reasons: ES has margin history only 2016–2020 (advisories), too short for the panel. CL/ZC/ZS have margin history but NO free per-contract price source: pysystemtrade holds only their December/November contracts, and the Stooq continuous series is an unadjusted splice with early, unpublished rolls — for CL's monthly cycle, effectively every event window would contain a splice jump. Rather than contaminate the test or silently shrink it, these three move to a clearly-labeled exploratory appendix (A12). Data-availability decision; no returns seen.
2. **Event variable: initial margin → maintenance margin.** The recovered Wayback histories retroactively recompute initial margins; maintenance is the only trustworthy contemporaneous long series, and CME's own advisories state initial = 110% of maintenance for speculators, so change dates — all the event study uses — are identical.
3. **Event definition: any increase → cumulative maintenance increase ≥ 5% within 5 business days.** Required to handle SPAN2 daily-float regimes uniformly; a margin drifting 0.4%/day forces no one and is not the hypothesized mechanism. Note the confirmatory sample (ending 2024-03-28, see #6) predates the metals SPAN2 migration (Jan 2026) entirely, so this rule mainly disciplines the exploratory appendix and any future extension.
4. **Clustering ambiguity resolved: anchor-window reading.** The first qualifying increase opens a 10-trading-day window; increases inside it merge; the next increase after it closes starts a new event.
5. **Windows moved.** v1's pilot (2003–2008) is impossible: CL/GC/SI/HG margin history begins Jan 2009. New windows in A7. The pilot deliberately contains 2011 (the marquee silver margin episode) and the GFC for the three long-history products; the decay split moves from 2015 to 2021 with identical intent (the edge must exist in the most recent, most competed segment).
6. **Price source: per-contract settlements from the pysystemtrade repository (GPL-3.0, data collected from Barchart/IB), which ships unadjusted per-contract prices (`multiple_prices`) and explicit roll calendars for the 6 confirmatory products, 1970s/80s/90s → 2024-03-28.** Cross-checked settlement-exact against Stooq on overlapping dates (SI/HG differ by a 100× cents/dollars convention only). **The confirmatory sample therefore ends 2024-03-28** — a data-provenance endpoint chosen before any returns were computed, not a performance-chosen one. A Stooq-bridged extension to 2026 appears only in the exploratory appendix.
7. **Entry timing: first settlement on/after the effective date, for all events.** Notice dates were recovered for only 334 rows (mostly 2016+); a uniform, conservative rule beats a mixed one. The +1-trading-day-lag rerun remains as robustness.
8. **K0 gates restated for the new universe (A8).** v1's "400 raw increases / 50 pilot events" was calibrated to 10 products over 23 years; v2 gates are calibrated to 6 products over their actual spans.

Everything not listed above (hypothesis, direction, horizon, matching construction, statistics, thresholds K1/K2, verbatim-failure-sentence discipline, lock clause) carries over from v1.0 unchanged.

## A1. Hypothesis (unchanged)

**H1:** Following a qualifying increase in CME maintenance margin for a futures contract, the contract's price partially reverses its trailing move over the next 10 trading days, because margin-called traders positioned against the trailing move are forced to liquidate, pushing price beyond fundamentals before liquidity providers restore it.

**Preregistered direction:** position = **opposite the sign of the trailing 20-trading-day return** at entry. Fixed. A wrong sign is a failure of H1, not an invitation to flip.

**Null:** post-increase returns are indistinguishable from volatility-matched days with no margin change.

## A2. Universe and data (frozen)

- **Confirmatory products (6):** ZN, 6E, 6J, GC, SI, HG. pysystemtrade instruments: US10, EUR, JPY, GOLD, SILVER, COPPER.
- **Margin events:** `data/margin_history_stitched.csv` (the rescued union: Wayback rolling-PDF captures + clearing-advisory attachments; 2,289 rows, 47% multi-route-confirmed, conflicts dispositioned in the logged conflict file). Maintenance margin, front/outright, per A0.2.
- **Prices:** `data/prices_pst/` `multiple_prices` per-contract unadjusted settlements with contract identifiers, plus `roll_calendars`. Stooq continuous series retained for cross-validation only.
- **Analysis span per product:** max(margin start, price start) → **2024-03-28**. Binding starts: 6E 2000-01-01, 6J 2000-02-03, ZN 2004-01-02, GC/SI 2009-01-08, HG 2009-01-08.

## A3. Event definition and clustering (frozen)

- **Qualifying event:** cumulative maintenance-margin increase ≥ 5% within any 5-business-day span for a confirmatory product.
- **Clustering:** anchor-window. First qualifying increase opens a 10-trading-day window; increases within it merge into that event, dated at the first effective date; the next qualifying increase after the window closes starts a new event.
- **Cross-product:** same-calendar-week events share a `cluster_week` id, reported everywhere; inference per A6.
- **Entry:** first settlement on/after the (first) effective date. Robustness rerun (exploratory, never for selection): entry +1 trading day.

## A4. Trade and contract selection (frozen)

- **Contract selection:** the contract labeled PRICE in `multiple_prices` at the entry date, unless the roll calendar shows a roll within 11 trading days after entry, in which case the FORWARD contract. For HG events where the selected contract would be the May contract (absent from the source's cycle), the next available cycle contract is used; count reported.
- **Window completeness:** the selected contract must have prices for the full [entry − 21, entry + 11] trading-day window in `multiple_prices` (across its PRICE/FORWARD/CARRY appearances). Missing days → event excluded and logged; per-product attrition reported.
- Entry at settlement t0; direction −sign(trailing 20-td log return of the selected contract); exit at settlement t0 + 10 trading days; one unit notional; no stops.
- Primary outcome: 10-day log return in bps of notional. Secondary (reported only): vol-standardized return.

## A5. Volatility-matched control construction (unchanged from v1, restated operationally)

- Vol measure: std of daily log settlement returns of the selected-contract series over trailing 20 trading days, annualized √252.
- Candidate control days d for event (product i, t0): same product; d not within ±15 trading days of ANY margin change (increase or decrease, any size) for i; vol ratio to t0 in [0.80, 1.25]; same trailing-20-td return sign; a selectable contract with a complete window exists at d; d within the product's analysis span.
- k = 10 nearest by |log vol ratio|; ties to earlier dates; controls reusable across events.
- No-match protocol: <5 matches → widen caliper once to [0.70, 1.43]; still <5 → drop event from matched comparison, log as unmatched. >20% unmatched → prominent fragility flag that cannot be removed by re-matching.
- Control pseudo-trades follow A4 identically.

## A6. Statistics (unchanged)

- **D:** mean over events of (event return − mean of its matched-control returns), bps.
- **G:** mean event return, bps.
- 95% interval on D via block bootstrap, monthly blocks, 10,000 draws. Decisions use thresholds, not p-values.
- **Costs:** 2 × (1 tick half-spread + 0.2 bps fees) per round trip, entry side +1 tick stress penalty; tick specs hard-coded per product.

## A7. Windows, pilot protocol, and lock

- **Pilot:** each product's binding start → **2014-12-31**.
- **Holdout:** **2015-01-01 → 2024-03-28**, untouched until the pilot verdict is committed. Preregistered decay split at **2021-01-01**: segments 2015–2020 and 2021–2024.03.
- **LOCK CLAUSE (binding, unchanged):** the pilot answers go/no-go only. If it passes, the holdout runs on the byte-identical specification. Any post-pilot change converts the study to exploratory and forfeits the preregistration claim. No tweak path exists.

## A8. Kill criteria — numbers fixed now

- **K0 (gates, checked in Stage 1 before any returns):**
  - Total qualifying clustered events across the 6 products, full span: **≥ 180**, else dead for power.
  - Pilot qualifying clustered events: **≥ 50**, else dead for power.
  - Events surviving window-completeness: **≥ 90%** overall; any single product < 70% is dropped with disclosure, and if that leaves < 5 products or < 150 events, dead.
- **K1 (vol test):** pilot **D < +15 bps** → dead. (Rationale unchanged: ~2–3× worst-case stress-adjusted round-trip cost. 0 < D < 15 is a kill, not a tuning zone.)
- **K2 (cost test):** pilot **G < +10 bps** → dead even if K1 passes.
- **K3 (decay test):** holdout **D(2021–2024.03) < +10 bps**, OR < **40% of D(2015–2020)** → edge decayed; not pitchable as live.
- All of K1, K2, K3 must pass to pitch the strategy as live.

## A9. Reporting commitment (unchanged, restated for v2 windows)

Pilot, pooled holdout, both holdout segments, per-product means, unmatched and attrition counts, and leave-one-crisis-out (drop 2011; drop 2020; drop 2022) are all computed and reported in the pitch regardless of what they show. No result produced under this preregistration may be omitted.

## A10. Failure sentences — verbatim, first sentence of the report

- **K0:** "The strategy could not be tested: the data gate failed ([gate], [value] vs. the preregistered minimum), so no backtest was run and no claim about the strategy's profitability is made."
- **K1:** "The strategy failed its preregistered test: after matching on volatility, margin increases contained no exploitable information — the event-minus-control differential was [D] bps against a preregistered threshold of +15 bps, meaning what looked like a margin effect is ordinary post-volatility behavior, and the strategy is dead."
- **K2:** "The strategy failed its preregistered cost test: the gross post-event return was [G] bps against a preregistered threshold of +10 bps, which cannot clear transaction costs, and the strategy is dead."
- **K3:** "The strategy failed its preregistered decay test: the 2021–2024 event-minus-control differential was [D_recent] bps (versus [D_2015_2020] bps in 2015–2020) against preregistered minima of +10 bps and 40% retention, meaning any edge that once existed has been competed away, and the strategy is not pitchable as live."

## A11. What I am giving up (unchanged)

Fishing across horizons, calipers, signs, subsamples, or universes; promoting exploratory runs; presenting pilot-only or pre-2021-only results as the headline; un-flagging fragility by re-matching. Signed by committing this file.

## A12. Exploratory appendix (declared now, run only after Stage 3, never confirmatory)

- **CL, ZC, ZS:** the identical event pipeline on their margin histories, with returns measured on pysystemtrade's December (CL, ZC) / November (ZS) contracts — clean per-contract prices but a deferred-contract instrument mapping, stated as such. Labeled EXPLORATORY in every table.
- **2024-04 → 2026-06-30 extension:** confirmatory products on the Stooq continuous series, excluding any event whose [−21, +11] window overlaps a conservative roll window (25 trading days before each front contract's expiry, from the exchange contract calendar). Labeled EXPLORATORY.
- Horizon (5/15-day) and +1-day-lag reruns as in v1. None of these enter K1/K2/K3.

---

## PART B — PROMPT (paste into Claude Code; stages gated as before)

You are implementing preregistration v2.0 (`prereg_margin_event_study_v2.md`). It is binding; where ambiguous, STOP and ask. Where this prompt and Part A conflict, Part A wins.

**Stage 1 — events and gates (no return calculations):**
1. From `data/margin_history_stitched.csv`, construct qualifying events for ZN, 6E, 6J, GC, SI, HG per A3 (≥5% cumulative maintenance increase within 5 business days; anchor-window clustering at 10 trading days), within each product's analysis span (A2).
2. Apply contract selection and window-completeness per A4 using `data/prices_pst/` multiple_prices and roll calendars. Output `events_v2.csv`: product, effective_date, entry_date, selected_contract, cum_increase_pct, trailing_return, trailing_vol, cluster_week, included_flag, exclusion_reason.
3. Data hygiene before gating: verify SILVER and COPPER price scales against Stooq (known 100× convention); cross-check 20 random selected-contract settlements per product against Stooq where the same contract is front (flag >0.1% discrepancies); confirm no event's window crosses a missing-data hole silently.
4. Print the three K0 gates from A8 with measured numbers and PASS/FAIL each. **If any fails, print the A10 K0 sentence with values and stop entirely.**

**Stage 2 — PILOT ONLY (binding start → 2014-12-31):**
5. Build vol-matched controls per A5, compute D, G, bootstrap interval, unmatched %, per-product table, cost table, and the event-time plot (−15 to +15, events vs controls) — pilot events only.
6. Print the pilot verdict against K1 (D ≥ +15 bps) and K2 (G ≥ +10 bps). On any failure: print the verbatim sentence, write `PILOT_FAIL`, stop.
7. **Hard stop.** Write `pilot_results_v2.md` and halt. Do not load, filter, summarize, or plot any event dated after 2014-12-31 in this session. The holdout runs only in a later session, after the human confirms the pilot verdict is committed to git, on this identical specification.

**Stage 3 — HOLDOUT (separate session, human-triggered, spec-identical):**
8. Rerun on 2015-01-01 → 2024-03-28. Report pooled D and G; D(2015–2020) and D(2021–2024.03); the K3 verdict; leave-one-crisis-out (drop 2020; drop 2022); unmatched/attrition tables. Both segments reported regardless, per A9.
9. Write `final_results_v2.md`, first sentence = pass summary or the applicable verbatim failure sentence.

**Stage 4 — EXPLORATORY APPENDIX (only after Stage 3 is committed):**
10. Run A12 items, every table stamped EXPLORATORY.

**Conduct rules:** never impute missing settlements (exclude and log); never silently drop a product; flag anomalous margin rows (>200% jumps) for human review; round nothing until display; every table states its sample window; the SILVER contract-size question (5,000 oz vs 1,000 oz series) must be resolved by the Stage 1 cross-check before any event uses SILVER prices — if unresolved, exclude SI and report under the K0 product-drop rule.
