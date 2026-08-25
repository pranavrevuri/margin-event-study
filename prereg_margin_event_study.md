# Preregistration and Prompt 3 — Margin-Increase Event Study

**Version 1.0 — commit this file to git with a timestamp BEFORE running Part B.**
**Rule for this document: nothing in Part A may be edited after any result has been viewed. Any amendment requires a new version number, committed before the amended analysis runs, with the reason stated. If results relevant to a section have already been seen, that section may not be amended at all.**

---

## PART A — PREREGISTRATION

### A1. Hypothesis (fixed now; the pilot does not choose it)

**H1:** Following an increase in CME initial margin requirements for a futures contract, the contract's price partially reverses its trailing move over the next 10 trading days, because margin-called traders positioned against the trailing move are forced to liquidate, pushing price beyond fundamentals before liquidity providers restore it.

**Preregistered direction:** position = **opposite the sign of the trailing 20-trading-day return** at entry. This sign is fixed here, in advance. If the data shows the opposite sign, that is a **failure of H1**, not an invitation to flip the rule. A flipped-sign analysis may be run afterward for curiosity but is exploratory, uses burned data, and may not be pitched as confirmatory. (This supersedes the earlier working sketch in which the pilot chose the sign.)

**Null (H0):** Post-increase returns are indistinguishable from returns on volatility-matched days with no margin change. Under H0, margin events are a costume on ordinary post-volatility-spike behavior.

### A2. Universe and data (frozen)

- Products (10, fixed): ES, ZN, 6E, 6J, GC, SI, HG, CL, ZC, ZS.
- Margin data: CME historical margin PDFs (2003–present), parsed to (product, effective_date, initial_margin, maintenance_margin). Advisory/notice publication date captured where present in the PDF.
- Prices: daily **exchange settlement prices of individual contracts** (not a back-adjusted continuous series). Source per Prompt 2's verification. Returns within an event window are computed on a single contract; no rolls occur inside any window.
- Contract selection per event: the nearest-to-expiry contract with **≥ 15 trading days remaining to expiry** at the entry date. If none exists for that product on that date, the event is excluded and counted in the exclusions table.

### A3. Event definition and clustering (frozen)

- **Raw event:** any increase in initial margin for the outright contract of a universe product.
- **Clustering within product:** margin increases for the same product with effective dates within 10 trading days of each other collapse into one event, dated at the first effective date.
- **Cross-product clustering:** events in different products within the same calendar week are separate trades but share a `cluster_week` id, reported in all tables; dependence is handled in inference (A6).
- **Entry timing:** entry at the first settlement **on or after the effective date**. (Advisories publish 1–2 business days before effectiveness, so this is conservative and immune to publication-lag lookahead.) Robustness (exploratory, reported but not used for selection): entry lagged one additional day.

### A4. Trade specification (frozen)

- Entry: settlement price at entry date t0 (per A3).
- Direction: −sign(trailing 20-trading-day log return of the selected contract as of t0). If the trailing return is exactly zero, exclude the event (report count).
- Exit: settlement at t0 + 10 trading days. No stops, no scaling, one unit notional per event.
- Primary outcome per event: 10-day log return of the position, in basis points of notional.
- Secondary outcome (reported, not decisive): the same return divided by trailing 20-day daily volatility (vol-standardized units).

### A5. Volatility-matched control construction (locked)

This section is the manufacturing floor for accidental results, so it is fully specified and no discretion remains.

- **Volatility measure:** realized volatility = standard deviation of daily log settlement returns over the trailing 20 trading days, on the same contract-selection rule as A2, annualized by √252.
- **Candidate control days** for an event (product i, entry date t0): all trading days d for the same product i in 2003–2026 such that:
  1. d is not within ±15 trading days of ANY margin change (increase or decrease) for product i;
  2. trailing 20-day realized vol at d, divided by trailing vol at t0, lies in **[0.80, 1.25]**;
  3. sign(trailing 20-day return at d) = sign(trailing 20-day return at t0) — required because the trade conditions on this sign;
  4. a valid contract with ≥ 15 trading days to expiry exists at d.
- **Selection:** the **k = 10** candidates nearest in |log(vol ratio)|. Ties broken by earlier calendar date. Controls may be reused across events and may overlap each other in time; this dependence is acknowledged and addressed in A6.
- **Control pseudo-trade:** identical rule to A4 applied at d (direction from d's own trailing return, 10-day hold).
- **No-match protocol (fixed):** if fewer than 5 candidates satisfy the caliper, widen the vol-ratio caliper once to [0.70, 1.43]. If still fewer than 5, the event is dropped from the matched comparison and logged as unmatched. If more than 20% of events end up unmatched, that fact is reported prominently and the matched-comparison result is flagged as fragile — this flag cannot be removed by re-matching under different rules.

### A6. Statistics (frozen)

- **Primary statistic D:** for each event, (event 10-day return) − (mean of its ≤10 matched-control 10-day returns); D = the average of this differential across events, in bps.
- **Gross statistic G:** mean event 10-day return across events, in bps.
- **Uncertainty:** 95% interval on D via block bootstrap, blocks = calendar months, 10,000 resamples. Reported always; **decisions use the numeric thresholds in A8, not p-values.**
- **Cost model (fixed):** per round trip, 2 × (1 tick half-spread + exchange/broker fees of 0.2 bps), with the entry side charged an additional 1 tick as an event-stress penalty. Tick values and contract sizes hard-coded per product from CME specs. Costs cancel in D (controls trade identically) but G must clear them.

### A7. Pilot protocol and specification lock

- **Pilot sample:** all events with entry dates from 2003-01-01 through 2008-12-31.
- **Confirmatory (holdout) sample:** all events from 2009-01-01 through 2026-08-25 — never touched, never plotted, never summarized until the pilot verdict is committed to git.
- **LOCK CLAUSE (binding):** The pilot exists solely to answer go/no-go under the kill criteria in A8. **If the pilot passes, the holdout runs on the byte-identical specification in A1–A6: same sign rule, same horizon, same caliper, same k, same clustering, same thresholds. No parameter, filter, product list, window, or matching rule may be changed between pilot and holdout. Any change after viewing pilot results converts the entire study to exploratory, and I forfeit the right to present it as a preregistered test. There is no "the pilot suggested a tweak" path: a tweak means killing this study and preregistering a new one, which then has no clean data to run on.**
- The pilot period deliberately contains 2008. This is accepted and disclosed: if H1 is a crisis-only phenomenon, the holdout (which contains 2011, 2020, 2022 but also long calm stretches) is where that will show.

### A8. Kill criteria — numbers fixed before anything runs

- **K0 (data gates, from Prompts 1–2, restated):**
  - Fewer than **400 raw margin-increase events** across the 10 products over 2003–2026 → dead.
  - Fewer than **50 clustered pilot events** in 2003–2008 → dead for power; do not run the pilot statistics.
  - No settlement-price source covering ≥ 15 years with per-contract data → dead.
- **K1 (vol test — "adds nothing beyond volatility"):** pilot **D < +15 bps** per event over 10 days → dead. Rationale for the number: ~2–3× the worst-case round-trip cost in the basket (~5–8 bps with the stress penalty), i.e., the smallest effect that could survive real frictions with room to decay. A D between 0 and +15 bps is a kill, not a "promising, let's tune" zone.
- **K2 (cost test):** pilot **G < +10 bps** per event → dead, even if K1 passes (an edge that exists only relative to controls but can't clear its own costs is untradeable).
- **K3 (post-2015 residual — "the pros already ate it"):** in the holdout, computed on the preregistered split (A9): **D(2015–2026) < +10 bps**, OR D(2015–2026) < **40% of D(2009–2014)** → the edge has decayed; the strategy fails as a live pitch regardless of how good the early sample looks.
- All three of K1, K2, K3 must pass for the strategy to be pitched as live. Partial passes are reported as failures with the failure sentences in A10.

### A9. Preregistered sample split and reporting commitment

The holdout is split at **2015-01-01** into 2009–2014 and 2015–2026. **Both halves are computed and reported in the pitch document regardless of what they show**, alongside the pooled holdout, the pilot, per-product means, the unmatched-event count, and the leave-one-crisis-out table (drop 2008; drop 2020; drop 2022 — each recomputed on whichever sample contains it). No result produced under this preregistration may be omitted from the writeup.

### A10. Failure sentences — to be used verbatim, first sentence of the report

Placeholders in brackets are filled with the measured numbers only; no other edits permitted.

- **If K0 fails:** "The strategy could not be tested: the data gate failed ([which gate], [measured value] vs. the preregistered minimum), so no backtest was run and no claim about the strategy's profitability is made."
- **If K1 fails:** "The strategy failed its preregistered test: after matching on volatility, margin increases contained no exploitable information — the event-minus-control differential was [D] bps against a preregistered threshold of +15 bps, meaning what looked like a margin effect is ordinary post-volatility behavior, and the strategy is dead."
- **If K2 fails:** "The strategy failed its preregistered cost test: the gross post-event return was [G] bps against a preregistered threshold of +10 bps, which cannot clear transaction costs, and the strategy is dead."
- **If K3 fails:** "The strategy failed its preregistered decay test: the post-2015 event-minus-control differential was [D_post2015] bps (versus [D_2009_2014] bps in 2009–2014) against preregistered minima of +10 bps and 40% retention, meaning any edge that once existed has been competed away, and the strategy is not pitchable as live."

### A11. What I am explicitly giving up by signing this

Fishing across horizons, calipers, signs, and subsamples; promoting the 5- or 15-day exploratory horizons if the 10-day fails; re-matching until D clears +15; presenting a pilot-only or pre-2015-only result as the headline. Signed by committing this file.

---

## PART B — PROMPT 3 (paste into Claude Code after Prompts 1–2 pass K0)

You are implementing a preregistered event study. The file `prereg_margin_event_study.md` (Part A) is the specification and it is binding. Where this prompt and Part A conflict, Part A wins. Where the spec is ambiguous, STOP and ask; do not resolve ambiguity by choosing.

**Stage 1 — build (no statistics yet):**
1. Load the parsed margin-change table from Prompt 1 and the per-contract settlement data from Prompt 2 for the 10 products: ES, ZN, 6E, 6J, GC, SI, HG, CL, ZC, ZS.
2. Construct raw increase events; apply within-product 10-trading-day clustering (A3); assign `cluster_week` ids; apply the contract-selection rule (A2) and exclusions. Output `events.csv` with one row per clustered event: product, effective_date, entry_date, contract, trailing_20d_return, trailing_20d_vol, cluster_week, excluded_flag, exclusion_reason.
3. Print the K0 gate check: raw increase count (2003–2026) vs. 400; clustered pilot event count (2003–2008) vs. 50. **If either fails, stop entirely and print the K0 failure sentence from A10 with the measured numbers.**

**Stage 2 — PILOT ONLY (2003-01-01 to 2008-12-31):**
4. For each pilot event, build the vol-matched control set exactly per A5: candidate filter (no margin change of either sign within ±15 trading days; vol ratio in [0.80, 1.25]; same trailing-return sign; valid contract), k=10 nearest by |log vol ratio|, ties to earlier dates, single caliper widening to [0.70, 1.43] if <5 matches, drop-and-log if still <5.
5. Compute per A4/A6: event returns, control pseudo-trade returns, differential D, gross G, block-bootstrap 95% interval (monthly blocks, 10,000 draws), unmatched-event percentage, per-product table, and the event-time plot: average cumulative return from day −15 to +15 around entry, events vs. matched controls, with the entry and exit dates marked.
6. Compute the cost table per A6 (hard-coded tick sizes/values and contract sizes per product; show the numbers used).
7. Print the pilot verdict against K1 (D ≥ +15 bps) and K2 (G ≥ +10 bps). If either fails, print the corresponding verbatim failure sentence with measured values, write `PILOT_FAIL` to disk, and **do not compute anything on 2009+ data.**
8. **Hard stop.** Write `pilot_results.md` and halt. Do not load, filter, summarize, or plot any post-2008 event under any circumstances in this run. The holdout runs only in a later session, only after the human confirms the pilot verdict has been committed to git, and only on this identical specification.

**Stage 3 — HOLDOUT (separate session, human-triggered, spec-identical):**
9. Rerun steps 4–6 on 2009-01-01 to 2026-08-25 with zero specification changes. Report pooled holdout D and G; the preregistered split D(2009–2014) and D(2015–2026); the K3 verdict (D_post2015 ≥ +10 bps AND ≥ 40% of D_2009_2014); leave-one-crisis-out (drop 2020, drop 2022); the +1-day-entry-lag and 5/15-day-horizon runs, each labeled EXPLORATORY in the output; and both halves regardless of result, per A9.
10. Assemble `final_results.md` containing every table and plot named above, the unmatched percentages, and — as its first sentence — either the pass summary or the applicable verbatim failure sentence from A10.

**Conduct rules for you, the implementation model:** never impute missing settlements (exclude and log); never silently drop a product; if a PDF's parsed margin change looks anomalous (>200% jump), flag it for human review rather than filtering it; round nothing until display; every table in the output must state its sample window in the header.
