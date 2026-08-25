# Data Gate Report — CME Historical Margin Acquisition & Parse (Prompt 1)

Run date: 2026-08-25. No return calculations of any kind were performed in this run.
Sample window of ALL tables below: **2020-06-30 → 2026-06-30** (the full extent of the source PDFs; see Limitations).

## 1. What was acquired

Source page: https://www.cmegroup.com/solutions/risk-management/margin-services/historical-margins.html
(Automated download initially blocked by Akamai; succeeded via Chrome-TLS-impersonated requests. Files in `data/margin_pdfs/`.)

| Product | CME clearing code | File(s) |
|---|---|---|
| ZC | C  | C-2020-to-present.pdf |
| ZS | S  | S-2020-to-present.pdf |
| ZN | 21 | 21-2020-to-present.pdf |
| 6E | EC | EC-2020-to-present.pdf |
| 6J | JY | JY-2020-to-present.pdf |
| GC | GC | GC-2020-to-present.pdf |
| SI | SI | SI-2020-to-present.pdf |
| HG | HG | HG-2020-to-present.pdf |
| CL | CL | CL-2020-to-2023-10-19.pdf, CL-2023-to-present.pdf |
| **ES** | — | **No PDF exists on the CME page.** Only full-size S&P 500 (SP) is offered (SP-2020-to-2024-10-17.pdf, SP-2024-to-present.pdf). Not substituted — a substitution would amend the frozen A2 universe. |

Download URLs are `https://www.cmegroup.com/clearing/risk-management/files/<FILENAME>`.

## 2. Limitations of this source (material to the prereg)

1. **Coverage begins 2020-06-30, not 2003.** Despite the "2020-to-present" filenames, all files start 2020-06-30 and end 2026-06-30. The CME page states pre-2020 history is available only via **CME DataMine** (paid, CSV) or by request to clearing.riskmanagement@cmegroup.com. 2003–mid-2020 — including the entire 2003–2008 pilot window — is absent.
2. **These are daily snapshots, not advisories.** One row per (business date, contract tier) titled "Minimum Performance Bond Requirements". There are **no notice/advisory dates** and **no explicit effective dates**; `effective_date` in `margin_history.csv` is *derived* — the first business date on which a new value appears.
3. **Only one margin level is published** (the minimum performance bond, i.e., the maintenance-level requirement). The prereg (A2) wants (initial, maintenance) pairs and defines events on *initial* margin increases. `initial_margin` is left **blank** rather than guessed. The increase-event set from maintenance changes equals that from initial changes only if the initial/maintenance multiplier is constant — an assumption you must ratify or replace with better data.
4. **SPAN2 changes what a "margin change" is.** CL from 2023-10-20 (and COMEX metals from ~Jan 2026) show near-daily floating margins (CL: ~250 changes/yr) plus directional long/short values. The prereg's event concept (discrete advisory-driven increases) does not map cleanly onto this regime. For SPAN2 rows the long-side value is used as the primary series; short-side-only changes are recorded separately (10 rows for CL, of which 5 are short-side increases; not counted in headline totals).

## 3. Parse quality

- 461,913 snapshot rows parsed across 10 PDFs; **0 unparseable rows**.
- All 9 products share an identical 1,562-business-date calendar; no missing dates, no conflicting duplicates, no overlap at the CL file boundary.
- 3 randomly chosen derived events verified against the raw PDF text (GC, ZN, 6E) — all exact matches.
- Exceptions file contains a single row: the missing ES product.

## 4. Outputs

- `data/margin_history.csv` — 1,224 rows: 1,215 derived change events + 9 series-start level anchors (`is_series_start=True`, not changes). Requested columns first (`product, effective_date, notice_date, initial_margin, maintenance_margin, source_file`), then documented extras (previous values, pct_change, direction, tier, roll/methodology flags).
- `data/margin_daily_snapshots.csv.gz` — full faithful extraction (audit trail for every derived event).
- `data/margin_history_exceptions.csv` — 1 row (ES missing).
- `data/margin_flags.csv` — flags for review, see §6.

Events are defined on the front tier (tier 1: e.g., GC-01, 21-1, CL-001) as "the outright contract". A roll-shift heuristic (`likely_roll_shift`) marks changes where the tier ladder pattern indicates a contract-month roll rather than a margin action: only 2 of 1,215 events flagged — flagged, not filtered.

## 5. Results

### (a) Margin changes per product per year — INCREASES [2020-06-30 → 2026-06-30; 2020 and 2026 are partial years]

| product | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| 6E | 2 | 1 | 2 | 0 | 2 | 3 | 0 |
| 6J | 1 | 2 | 3 | 0 | 3 | 2 | 0 |
| CL | 0 | 4 | 8 | 26 | 157 | 138 | 66 |
| GC | 4 | 1 | 3 | 5 | 6 | 11 | 57 |
| HG | 3 | 6 | 3 | 2 | 6 | 6 | 1 |
| SI | 6 | 1 | 1 | 2 | 8 | 10 | 58 |
| ZC | 0 | 11 | 6 | 3 | 0 | 0 | 1 |
| ZN | 0 | 3 | 5 | 2 | 1 | 0 | 0 |
| ZS | 4 | 9 | 7 | 5 | 0 | 1 | 1 |

### (a) DECREASES [same window]

| product | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| 6E | 2 | 1 | 0 | 2 | 1 | 2 | 1 |
| 6J | 2 | 4 | 0 | 3 | 1 | 2 | 1 |
| CL | 5 | 3 | 7 | 28 | 90 | 108 | 56 |
| GC | 1 | 4 | 4 | 1 | 0 | 0 | 59 |
| HG | 0 | 3 | 3 | 3 | 2 | 2 | 0 |
| SI | 2 | 5 | 3 | 2 | 3 | 0 | 58 |
| ZC | 1 | 4 | 3 | 8 | 4 | 1 | 0 |
| ZN | 2 | 2 | 0 | 3 | 2 | 1 | 0 |
| ZS | 0 | 5 | 3 | 8 | 4 | 1 | 0 |

The CL explosion from late 2023 and the GC/SI explosion from Jan 2026 are the SPAN2 daily-floating regimes, not a change in CME margin policy activism.

### (b) K0 gate: raw increases 2003–2026 vs 400 → **PASS (on a lower bound; see caveats)**

- Measured raw increases on available data (2020-06-30 → 2026-06-30, 9 of 10 products): **679**.
- Since more data can only add events, the 2003–2026 count is ≥ 679 ≥ 400 → the count gate passes as literally written.
- **Caveats:** 385 of 679 are CL in its SPAN2 era; GC+SI 2026 contribute another 115 near-daily-float increases. Excluding all SPAN2-regime increases leaves **179** discrete "SPAN-era" increases in ~6 years — the composition, not just the count, is your call before this PASS is leaned on. And the preregistered universe (10 products incl. ES) and window (2003–2026) were not actually measured.

### (c) K0 gate: clustered increases 2003–2008 (A3 rule) vs 50 → **FAIL**

- Clustered pilot events in 2003-01-01 → 2008-12-31: **0** (the source contains no data before 2020-06-30).
- Verbatim A10 sentence: **"The strategy could not be tested: the data gate failed (clustered pilot-event gate for 2003–2008, 0 events vs. the preregistered minimum of 50), so no backtest was run and no claim about the strategy's profitability is made."**
- This is a data-availability failure, not evidence about margin-event frequency in 2003–2008. The gate becomes measurable only with DataMine (or equivalent) pre-2020 data.
- Context, full observed window (A3 within-product 10-trading-day clustering, trading days = observed business-date calendar): 679 raw increases collapse to **205** clusters under an anchor-window reading of A3 ("within 10 td of the cluster's first date") or **118** under a chain reading ("within 10 td of the previous increase"). A3's wording ("within 10 trading days of each other") does not distinguish these; both are reported, neither was chosen. The pilot-gate verdict is unaffected (0 either way).

### (d) notice_date coverage → **0 of 1,224 rows (0%)**

The PDFs contain no advisory/notice dates at all. Prereg A3's entry rule (first settlement on/after effective date) remains executable since it keys off effective dates, but the claim that "advisories publish 1–2 business days before effectiveness" is unverifiable from this source, and any entry-timing analysis needing notice dates requires the advisory notices themselves (CME clearing notices archive).

## 6. Flags for review (flagged, never filtered)

- **Changes > +200%: none.** Largest parsed changes: CL 2026-03-02 +44.0% (4508→6490), SI 2026-02-02 +33.7%, CL 2026-03-09 +31.7%, SI 2026-01-30 −31.3%, GC 2026-02-02 +30.7%. The early-2026 metals oscillations are large but consistent with the SPAN2 daily-float regime during a volatile period.
- `data/margin_flags.csv` contains 1 row: the CL SPAN→SPAN2 file boundary (2023-10-19 → 2023-10-20, +4.3%), flagged `methodology_transition` so it is not mistaken for a margin action.
- 2 events flagged `likely_roll_shift` (tier-ladder shift pattern).

## 7. Decisions needed before anything downstream (prereg: stop-and-ask items)

1. **Pre-2020 data:** acquire CME DataMine margin history (or email CME clearing risk management) — without it, K0 fails and the study is dead as preregistered.
2. **ES:** no ES margin PDF exists on this page. Substituting SP (or sourcing ES from DataMine) amends the frozen A2 universe → requires a prereg version bump before any analysis.
3. **Initial vs maintenance:** events must be defined on the published maintenance-level series or better data acquired; either way, ratify explicitly.
4. **SPAN2 regime:** decide how the daily-floating era maps onto the prereg's event definition (affects the holdout far more than the pilot). Amending now, before any pilot result exists, is still clean under the prereg's versioning rule.
