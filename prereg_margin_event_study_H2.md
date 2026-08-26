# Preregistration H2 v1.0 — Margin-Increase Continuation Study (One-Shot)

**This is a NEW study, not an amendment of the margin-reversal study, which is closed. Commit this file BEFORE running Part B. This study permits ZERO amendments: whatever the single run prints is final.**

## H0. Genealogy — full disclosure, in the record forever

The predecessor study (prereg v1.0–v3.0, this repo) hypothesized post-margin-hike REVERSAL and died by its own preregistered criteria on its pilot (start→2014): D = −17.1 bps vs. a +15 threshold, G = +3.1 bps vs. +10 (commit ebda726; verbatim failure sentences in pilot_results_v3.md). Its NEGATIVE differential — post-hike returns CONTINUED the trailing move ~17 bps more than volatility-matched controls — motivates this study's opposite hypothesis. That motivating evidence is weak: wide CI [−75.8, +39.3], heavily influenced by HG (−358 bps on 7 events), and drawn from 2000–2014, a different regime than this study's sample. The reversal hypothesis may NOT be re-tested on any data; the pilot data (pre-2015) is burned for confirmatory purposes and is used here only as disclosed motivation.

**This study is legitimate for exactly one reason: its sample (2015-01-01 → 2024-03-28) has never been loaded, summarized, plotted, or viewed in any form.** Stage 2's containment log confirms this. It will be loaded once, for this test, and never again for hypothesis generation.

## H1. Hypothesis (fixed)

Following a qualifying maintenance-margin increase, forced deleveraging by margin-called traders positioned against the trailing move AMPLIFIES that move over the following 10 trading days (margin-spiral continuation, per Brunnermeier–Pedersen and the funding-shock evidence in Hedegaard).

**Direction: position = +sign(trailing 20-trading-day return) at entry.** Fixed. A wrong sign is a failure, not a flip; there is no third hypothesis after this one.

**Null:** post-hike returns do not continue more than on volatility-matched days without margin changes.

## H2. Design (inherited verbatim from prereg v3.0 unless stated)

- **Universe:** ZN, 6E, 6J, GC, HG (SI remains conduct-excluded; CL/ZC/ZS remain out — no clean per-contract prices).
- **Sample:** events in `events_v3.csv` with entry dates 2015-01-01 → 2024-03-28, surviving the committed A4 window-completeness rule. No new event construction; the event set is already frozen at commit c8c5099, built before any return existed.
- **Trade:** entry at first settlement on/after effective date; direction +sign(trailing 20-td return); exit at settlement t0+10; no stops; returns in bps of notional on the selected contract.
- **Controls:** A5 verbatim — same-product days with no margin change of any size/direction within ±15 trading days, vol ratio [0.80, 1.25] (one widening to [0.70, 1.43]), same trailing-return sign, k=10 nearest by |log vol ratio|, candidate days restricted to 2015-01-01 → 2024-03-28. Control pseudo-trades use THIS study's direction rule.
- **Statistics:** D (event minus matched-control mean, bps), G (gross event mean, bps), 95% monthly-block bootstrap (10,000 draws, seed 42), unmatched %, per-product table, cost table per A6, event-time plot −15 to +15.

## H3. Kill criteria — all numeric, all fixed now, ALL must pass

- **C1 (vol test):** D < +15 bps → dead.
- **C2 (cost test):** G < +10 bps → dead.
- **C3 (decay test):** split at 2021-01-01. D(2021–2024.03) < +10 bps, OR < 40% of D(2015–2020) → dead (edge must exist in the most recent, most competed segment).
- **C4 (concentration floor, new — because the motivating evidence was HG-heavy):** recompute D excluding the single product with the largest absolute contribution. If that D < +5 bps → dead. A result owned entirely by one market is not a multi-market strategy.
- **Fragility flags (reported, non-fatal):** unmatched > 20%; leave-one-crisis-out (drop 2020; drop 2022) sign flips.

## H4. No-amendments clause (binding, absolute)

There is no v1.1. No threshold, rule, window, universe, matching parameter, or definition may change for any reason, including discovered implementation ambiguity — ambiguities are resolved by the strictest available reading and logged. If the run fails any criterion, the study is dead, the failure sentence below is used verbatim as the first sentence of the record, and no margin-based strategy of any kind will be pitched. The pre-2015 burned data may never launder a third hypothesis.

## H5. Failure sentence (verbatim, first sentence of the record on ANY criterion failure)

"The continuation strategy failed its preregistered one-shot test on previously untouched 2015–2024 data ([failed criterion]: [measured value] vs. [threshold]); combined with the reversal hypothesis's earlier preregistered failure, margin-increase events show no exploitable multi-day return signal in either direction, and no margin-based strategy will be pitched."

(That sentence, if it fires, is itself a real finding: two-sided, preregistered evidence that CME margin events carry no tradeable multi-day signal beyond volatility — reported as such.)

## PART B — PROMPT (single stage, single run)

Read prereg_margin_event_study_H2.md (this file), prereg_margin_event_study_v3.md, and prereg_margin_event_study_v2.md. This is a ONE-SHOT confirmatory run under H2–H3; the no-amendments clause H4 is absolute. Where anything is ambiguous, choose the strictest reading, log it, and proceed — do not stop to optimize and do not ask to relax anything.

1. Load `events_v3.csv`; select events with entry 2015-01-01 → 2024-03-28 that survived the committed A4 rule. Report the count and per-product breakdown BEFORE computing any return. If total < 40, print the H5 sentence with "sample floor: [n] vs 40" and stop (preregistered power floor).
2. Reuse the committed Stage-2 machinery (`scripts/stage2_v3.py` selection/matching logic) with the H2 direction rule and 2015–2024 control window. Assert every event's contract selection and trailing fields match `events_v3.csv` exactly.
3. Compute D, G, bootstrap CI, unmatched %, per-product table, cost table, the 2015–2020 / 2021–2024.03 split, the C4 concentration recomputation, leave-one-crisis-out, and the event-time plot.
4. Print the verdict against C1, C2, C3, C4 in order, each with measured value vs. threshold, PASS/FAIL. Any FAIL → write H2_FAIL and put the H5 sentence (values filled) as the first line of `h2_results.md`. All PASS → first line: "The continuation strategy passed all four preregistered criteria on previously untouched 2015–2024 data: D=[..], G=[..], D_recent=[..], D_ex-top=[..]."
5. Write `h2_results.md` with every table and the plot, commit everything with message "H2 one-shot: [PASS/FAIL]", and stop. No exploratory runs of any kind in this session.
