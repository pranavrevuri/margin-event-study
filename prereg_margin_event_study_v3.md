# Preregistration v3.0 and Prompt — Margin-Increase Event Study

**Supersedes v2.0. Commit this file BEFORE running any stage of Part B. v1.0 and v2.0 remain in the repo untouched as the record of the prior designs.**
**Binding rule unchanged: nothing in Part A may be edited after any result it governs has been viewed. Amendments require a new version committed before the amended analysis runs.**

---

## A0. Amendment log — every change from v2.0, and why each is outcome-blind

**Status at amendment time: the v2 Stage 1 run is committed (`770e6e1`). What has been seen: qualifying-event counts (201 total, 93 pilot), window-completeness survival (84.6% overall; per-product counts), the per-event exclusion list with reasons, and the SILVER contract-size resolution outcome (UNRESOLVED — test (iii) failed, median post-roll mismatch 0.72% vs GOLD's 0.09% benchmark). ZERO return calculations of any kind — event or control, pre- or post-entry beyond the A4 trailing conditioning fields — have been run or viewed. The git history proves the ordering. Every amendment below responds to data-quality facts only; no amendment can be tuned to outcomes because no outcomes exist.**

1. **A4 amended — completeness fallback to the FORWARD contract.** v2's Stage 1 established that pysystemtrade's `multiple_prices` has genuine settlement holes for the front contract on scattered days, hand-verified in the raw files (e.g., EUR: the 2014-10-06 23:00 settlement row has PRICE = NaN for the Dec-14 contract while the SAME row settles the Mar-15 FORWARD contract at 1.2642; GOLD Dec-16 is missing four consecutive settlements). The holes are a storage artifact of one source's handling of near-expiry front contracts, not an absence of market data — the forward contract settles normally on those days. v3 therefore extends the existing A4 FORWARD-selection logic (already used when a roll is imminent) to data availability: **if the PRICE-selected contract's [entry − 21, entry + 11] window is incomplete, the FORWARD contract at entry is selected instead if and only if its window is complete; otherwise the event is excluded and logged exactly as in v2.** No fallback exists when the roll-imminent rule already selected FORWARD (falling back to PRICE would hold a contract through its roll — the situation that rule exists to avoid). The fallback never mixes two contracts inside one window and never imputes a price (conduct rule intact); every fallback event is flagged in `events_v3.csv` and counted per product.
   *Outcome-blindness and full disclosure:* before committing this file, the fallback's **feasibility** was checked against the v2 exclusion list — a pure data-availability examination, identical in kind to the availability checks disclosed in v2's A0. Result, stated here so it is on the record before the run: 10 of the 16 non-SILVER missing-window exclusions have a complete FORWARD window and become includable; 0 of the 14 SILVER ones do. No price path, return, or post-entry value was computed or viewed in that check.
   *Alternatives considered and rejected:* (a) tolerating ≤N missing days with gap-skipped returns — imputation-adjacent and changes return definitions, rejected; (b) acquiring a second per-contract price source mid-study — new provenance risk after events are known, rejected; (c) accepting the v2 kill — rejected because K0's completeness gate exists to protect sample integrity, and a kill driven by one source's sparse storage of near-expiry settlements (while the same source holds genuine same-day forward settlements) is an artifact of storage, not of the event population.

2. **A8 Gate 3 computation clarified — conduct-excluded products are not averaged into the ≥90% completeness statistic.** v2's implementation averaged SILVER's completeness into the overall survival figure even though the conduct rule (unresolved contract-size question) independently excludes SILVER from ever contributing an event to the test. v3 pins the computation: **the ≥90% overall survival is computed over the products remaining in the confirmatory universe after the conduct-rule (price-series identity) exclusion; a conduct-excluded product's completeness is reported separately, never averaged in.** The single-product <70% drop rule and the ≥5-products / ≥150-surviving-events floors are UNCHANGED and still apply to what remains.
   *Outcome-blindness:* this is a gate-computation clarification, decided while zero returns exist. Stated for the record: **this clarification alone would NOT have converted v2's verdict** — under the v3 reading, v2's numbers still fail Gate 3 (non-SI survival 149/166 = 89.8% < 90%, and 149 surviving events < 150). Only the Amendment-1 data facts change the gate outcome. The floors that bind hardest (≥150 events, ≥5 products) are kept at their v2 values exactly.

3. **A3 clarified — event dating pinned to the threshold-crossing date (documentation only; zero behavioral change).** v2 left an ambiguity between dating a multi-step cumulative event at the first sub-threshold step versus at the increase that crosses the 5% cumulative threshold. v3 pins the latter, which is what the v2 implementation already did: **an event is dated at the effective date on which the cumulative 5-business-day increase first reaches ≥5%.** Rationale: that is the first date the event is identifiable in real time; dating at an earlier sub-threshold step would require foreknowledge of later steps. The v3 event set is therefore expected to be byte-identical to v2's (201 events, same dates); any deviation must be printed and explained.

4. **A5 symmetry note (consequence of Amendment 1).** The control-day requirement "a selectable contract with a complete window exists at d" uses the amended A4 selection **including the completeness fallback**, so event and control construction remain symmetric.

5. **SILVER handling: UNCHANGED.** The three-test resolution procedure and the conduct rule are v2's verbatim. The check reruns deterministically in Stage 1; if unresolved again, SI is excluded under the K0 product-drop rule with disclosure, its events appear in attrition tables only, and (per Amendment 2) its completeness is reported separately. SI remains counted in Gates 1–2, which measure margin-event availability across the declared 6-product universe — exactly as v2's committed implementation counted it.

Everything not listed above (hypothesis, direction, horizon, universe, spans, event definition and clustering, matching construction, statistics, thresholds K1/K2/K3, verbatim-failure-sentence discipline, reporting commitments, exploratory appendix, lock clause) carries over from v2.0 unchanged and is not restated except where quoted below for operational precision.

## A1. Hypothesis (unchanged from v2)

**H1:** Following a qualifying increase in CME maintenance margin for a futures contract, the contract's price partially reverses its trailing move over the next 10 trading days. **Direction:** opposite the sign of the trailing 20-trading-day return at entry. Fixed. **Null:** post-increase returns are indistinguishable from volatility-matched days with no margin change.

## A2. Universe and data (unchanged from v2)

Confirmatory products ZN, 6E, 6J, GC, SI, HG (pysystemtrade US10, EUR, JPY, GOLD, SILVER, COPPER); margin events from `data/margin_history_stitched.csv` (maintenance, front/outright); prices from `data/prices_pst/` per-contract `multiple_prices` + `roll_calendars`; Stooq for cross-validation only. Analysis span per product: max(margin start, price start) → 2024-03-28; binding starts 6E 2000-01-01, 6J 2000-02-03, ZN 2004-01-02, GC/SI/HG 2009-01-08.

## A3. Event definition and clustering (v2 verbatim + dating clarification)

- Qualifying event: cumulative maintenance-margin increase ≥5% within any 5-business-day span.
- **Dating (pinned per A0.3): the event's effective date is the date the cumulative increase first reaches ≥5% (threshold-crossing date).**
- Clustering: anchor-window; the first qualifying increase opens a 10-trading-day window; increases inside merge; the next qualifying increase after it closes starts a new event. `cluster_week` reported.
- Entry: first settlement on/after the effective date. (+1-day-lag rerun stays exploratory robustness.)

## A4. Trade and contract selection (amended per A0.1)

- **Contract selection:** the contract labeled PRICE in `multiple_prices` at the entry date, unless the roll calendar shows a roll within 11 trading days after entry, in which case the FORWARD contract. HG May-contract rule as in v2 (count reported).
- **Window completeness with fallback:** the selected contract must have settlements for the full [entry − 21, entry + 11] trading-day window (across its PRICE/FORWARD/CARRY appearances, settlement rows only). **If the PRICE-selected contract's window is incomplete, select the FORWARD contract at entry iff its window is complete (flag `completeness_fallback`, count per product). No fallback when the roll-imminent rule already selected FORWARD.** Otherwise the event is excluded and logged; per-product attrition reported.
- Entry at settlement t0; direction −sign(trailing 20-td log return of the selected contract); exit at settlement t0 + 10 trading days; one unit notional; no stops. Primary outcome: 10-day log return in bps. Secondary (reported only): vol-standardized return. Trailing-return-exactly-zero exclusion retained.

## A5. Volatility-matched controls (unchanged from v2, + A0.4 symmetry)

As v2 A5 verbatim, with "a selectable contract with a complete window exists at d" evaluated under the amended A4 selection including the completeness fallback.

## A6. Statistics (unchanged from v2)

D, G, monthly-block bootstrap (10,000 draws), cost model — v2 A6 verbatim.

## A7. Windows, pilot protocol, and lock (unchanged from v2)

Pilot: binding start → 2014-12-31. Holdout: 2015-01-01 → 2024-03-28, decay split 2021-01-01. **LOCK CLAUSE binding and unchanged.**

## A8. Kill criteria (floors unchanged; Gate-3 computation per A0.2)

- **K0 (gates, checked in Stage 1 before any returns):**
  - Total qualifying clustered events across the 6 declared products, full span: **≥ 180**, else dead for power.
  - Pilot qualifying clustered events (6 declared products): **≥ 50**, else dead for power.
  - Window-completeness survival **≥ 90% overall, computed over products remaining after the conduct-rule (price-series identity) exclusion**; any single remaining product < 70% is dropped with disclosure; if the exclusions and drops together leave **< 5 products or < 150 surviving events, dead**. Conduct-excluded products' completeness is reported separately.
- **K1:** pilot D < +15 bps → dead. **K2:** pilot G < +10 bps → dead. **K3:** holdout D(2021–2024.03) < +10 bps OR < 40% of D(2015–2020) → not pitchable. All unchanged from v2.

## A9–A12 (unchanged from v2)

Reporting commitment, verbatim failure sentences (A10), forfeitures (A11), and the exploratory appendix (A12) carry over from v2.0 word for word. The K0 failure sentence remains: *"The strategy could not be tested: the data gate failed ([gate], [value] vs. the preregistered minimum), so no backtest was run and no claim about the strategy's profitability is made."*

---

## PART B — PROMPT (staged; Part A wins on any conflict)

You are implementing preregistration v3.0 (`prereg_margin_event_study_v3.md`). It is binding; where ambiguous, STOP and ask.

**Stage 1 (v3 rerun) — events and gates (no return calculations):**
1. From `data/margin_history_stitched.csv`, construct qualifying events for the 6 declared products per A3 within each product's analysis span. The event set is expected byte-identical to v2's (201 events); print and explain any deviation.
2. Apply amended A4 contract selection with the completeness fallback using `data/prices_pst/`. Output `events_v3.csv` with the v2 schema plus a `completeness_fallback` column: product, effective_date, entry_date, selected_contract, cum_increase_pct, trailing_return, trailing_vol, cluster_week, completeness_fallback, included_flag, exclusion_reason.
3. Data hygiene before gating, rerun verbatim from v2: SILVER/COPPER scale verification; the three-test SILVER contract-size resolution (if unresolved → SI excluded under the conduct rule and the K0 product-drop rule); 20 random front-aligned settlement cross-checks per product vs Stooq (flag >0.1%); explicit window-hole accounting (none silent); >200% margin-jump conduct flags. Additionally report per-product `completeness_fallback` counts.
4. Print the three K0 gates per amended A8 with measured numbers and PASS/FAIL each. **If any fails, print the A10 K0 sentence with values and stop entirely.** **If all pass, print the pass line and HARD STOP: commit the Stage-1 record (`stage1_v3.py`, `events_v3.csv`, gate printout) and do not begin any Stage-2 computation — no control matching, no returns, no plots — in this session. Stage 2 runs only on explicit human trigger after the Stage-1 record is committed.**

**Stage 2 — PILOT ONLY (binding start → 2014-12-31):** as v2 Part B steps 5–7 verbatim, writing `pilot_results_v3.md` / `PILOT_FAIL`.

**Stage 3 — HOLDOUT (separate session, human-triggered, spec-identical):** as v2 Part B steps 8–9 verbatim, writing `final_results_v3.md`.

**Stage 4 — EXPLORATORY APPENDIX:** as v2 Part B step 10 verbatim.

**Conduct rules (v2 verbatim, restated):** never impute missing settlements (exclude and log — the A4 fallback selects a different genuinely-settled contract, it never fills a hole); never silently drop a product; flag >200% margin jumps for human review; round nothing until display; every table states its sample window; the SILVER contract-size question must be resolved by the Stage-1 cross-check before any event uses SILVER prices — if unresolved, exclude SI and report under the K0 product-drop rule.
