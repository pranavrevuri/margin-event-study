# Coverage Report — Pre-2020 CME Margin History Rescue

Run date: 2026-08-25 (single session, per time-box). **No return calculations of any kind were performed.**
Union window of all tables: earliest recoverable date per product → 2026-06-30.

## 1. Verdict

The pre-2020 gap is closed for 9 of the 10 universe products. Recovered, stitched, and cross-validated
front-month **maintenance**-margin change history now covers:

| product | recoverable segments | gaps | change rows in union |
|---|---|---|---|
| 6E | 2000-01-01 → 2026-06-30 | — | 105 |
| 6J | 2000-02-03 → 2026-06-30 | — | 116 |
| ZC | 2003-11-24 → 2026-06-30 | — | 148 |
| ZS | 2003-11-24 → 2026-06-30 | — | 147 |
| ZN | 2004-01-02 → 2026-06-30 | — | 90 |
| CL | 2009-01-12 → 2026-06-30 | — | 819 |
| GC | 2009-01-08 → 2026-06-30 | — | 227 |
| SI | 2009-01-08 → 2026-06-30 | — | 235 |
| HG | 2009-01-08 → 2026-06-30 | — | 103 |
| **ES** | **2016-01-01 → 2020-12-31 only** | pre-2016; 2021→present | 27 |
| (SP full-size, side dataset for the ES decision) | 2001-03-01 → 2016-08-15, 2020-06-24 → 2025-09-26 | 2016-08-15 → 2020-06-24 | 272 |

Prereg implications (facts only, decisions remain yours):
- **Pilot window 2003-01-01 → 2008-12-31**: covered for 6E, 6J (from 2000), ZC, ZS (from 2003-11-24), ZN (from 2004-01-02).
  **Not covered** for CL, GC, SI, HG (NYMEX/COMEX pre-2009 history is not on any cmegroup.com source; see §6) or ES.
  The 2003-01-01 → 2003-11-23 sliver for CBOT products predates CME Clearing's takeover of CBOT clearing and appears unrecoverable from CME sources.
- ES margin history exists **only** via clearing advisories (2016–2020 recovered this session; 2008–2015 advisories are indexed but unfetched, see §5; 2021+ advisories exist on the live site but were outside this rescue's scope).

## 2. Routes and stitched union

Four independent routes, merged into `data/margin_history_stitched.csv` (2,289 deduplicated change rows; one row per product × effective date, front-month maintenance level):

| route | what it is | coverage contribution |
|---|---|---|
| `wayback-history` | Wayback captures of CME "Performance Bond History" PDFs (change-level, Spec+Hedge, initial+maintenance) | 2000/2003/2004/2009 → 2015/2016 |
| `snapshot-wayback` | Wayback captures of daily-snapshot PDFs incl. zip archives (front-tier margin per business date) | 2009→2013, 2014→2017-11, 2019/2020→2025 |
| `advisory` | CME clearing PB advisories (stub pages + PDF/XLSX attachments): notice_date, effective date, Current/New Initial+Maintenance | 2016-01-01 → 2020-12-31 (certified ≥95% complete per year) |
| `snapshot-live` | The live-site snapshot parse from the previous session (`data/margin_history.csv`) | 2020-06-30 → 2026-06-30 |

Full per-product route windows are in §8. Effective dates for snapshot routes are derived (first business date a new value appears); advisory rows carry true effective dates and notice dates.

**Cross-validation:** 1,075 of 2,289 union rows (47%) are independently confirmed by 2+ routes; where routes overlap, maintenance values agree on all but the 19 dispositioned cases in §4. Notice dates present on 334 rows (all advisory-sourced; advisories publish 1 business day before effectiveness in 87% of rows, 2–4 days otherwise).

## 3. Changes per product per year (stitched union, deduplicated)

| | 2000 | 2001 | 2002 | 2003 | 2004 | 2005 | 2006 | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6E | 8 | 8 | 7 | 6 | 4 | 4 | 1 | 3 | 10 | 3 | 3 | 2 | 3 | 4 |
| 6J | 6 | 5 | 4 | 3 | 6 | 7 | 3 | 5 | 10 | 1 | 4 | 8 | 3 | 6 |
| CL | – | – | – | – | – | – | – | – | – | 17 | 2 | 7 | 4 | 4 |
| ES | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| GC | – | – | – | – | – | – | – | – | – | 4 | 5 | 6 | 3 | 5 |
| HG | – | – | – | – | – | – | – | – | – | 3 | 4 | 5 | 3 | 5 |
| SI | – | – | – | – | – | – | – | – | – | 6 | 8 | 9 | 4 | 4 |
| ZC | – | – | – | 1 | 8 | 7 | 8 | 3 | 8 | 5 | 6 | 3 | 1 | 4 |
| ZN | – | – | – | – | 7 | 2 | 4 | 6 | 8 | 3 | 4 | 4 | 2 | 2 |
| ZS | – | – | – | 1 | 11 | 6 | 3 | 5 | 7 | 2 | 5 | 4 | 2 | 4 |

| | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6E | 5 | 7 | 4 | 4 | 0 | 0 | 4 | 2 | 2 | 2 | 3 | 5 | 1 |
| 6J | 3 | 5 | 4 | 7 | 1 | 0 | 4 | 6 | 3 | 3 | 4 | 4 | 1 |
| CL | 8 | 4 | 10 | 8 | 27 | 14 | 23 | 7 | 15 | 54 | 247 | 246 | 122 |
| ES | 0 | 0 | 4 | 5 | 8 | 3 | 7 | – | – | – | – | – | – |
| GC | 6 | 1 | 9 | 11 | 6 | 6 | 14 | 5 | 7 | 6 | 6 | 11 | 116 |
| HG | 4 | 2 | 8 | 7 | 9 | 7 | 9 | 9 | 6 | 5 | 8 | 8 | 1 |
| SI | 6 | 5 | 7 | 6 | 2 | 5 | 22 | 6 | 4 | 4 | 11 | 10 | 116 |
| ZC | 3 | 2 | 7 | 7 | 7 | 20 | 7 | 15 | 9 | 11 | 4 | 1 | 1 |
| ZN | 2 | 1 | 3 | 3 | 4 | 6 | 10 | 5 | 5 | 5 | 3 | 1 | 0 |
| ZS | 3 | 4 | 11 | 9 | 9 | 6 | 11 | 14 | 10 | 13 | 4 | 2 | 1 |

"–" = outside recoverable coverage; "0" = covered, no change observed. The CL surge from 2023-10-20 and the GC/SI surge from Jan 2026 are SPAN2 daily-floating regimes (methodology change, not policy activism) — the same caveat flagged in `data_gate_report.md`.

## 4. Conflict resolution (per this session's instruction)

All cross-source disagreements were resolved by **cross-route confirmation against the daily-snapshot level at the effective date** (±5-day window for the effective-after-close offset; lookup never extrapolates across snapshot coverage gaps). Disposition of all 19 conflicts (`data/margin_history_stitched_conflicts.csv`):

- **17 rows EXCLUDED as demonstrably non-front-leg** (16 ZC, 1 CL): different Wayback renders of the same corn history label the crop legs inconsistently — a render's "Spec All Months" can be the *new-crop* (deferred-month) rate, and one render carries "Spec Mnth 19-28" as its only row on a date. Where the row's value contradicts the snapshot-confirmed front-month level, the row is excluded from the front-month union and logged. Nothing was guessed; every exclusion is in the conflicts file with both values.
- **1 conflict resolved by snapshot confirmation** (ZC: conflicting renders, snapshot picked the front value).
- **1 UNRESOLVED, kept and flagged** (CL 2011-05-10, a back-tier regrouping disagreement between the 2015-05 and 2015-09 renders; no snapshot coverage at that date). It remains in the union flagged `maintenance_conflict_across_routes=True`.

Additionally, 349 cross-capture **initial-margin restatements** were detected in wayback-history files (see §6, caveat 1); the earliest capture's initial is kept and the row flagged `initial_restated` in `data/margin_history_wayback.csv`.

## 5. Advisory (Route 2) completeness

The live CME notices index was enumerated for 2007–2020 (15,026 notices; 6,065 clearing). All 1,918 clearing stubs for 2016–2020 were fetched; 850 are Performance Bond advisories. Attachment recovery: 827 of 850 (23 attachments no longer resolvable on the live site); of those, 761 parsed to rate rows and 60 were verified to contain no outright-rate content (spread/credit-only advisories), leaving **6 attachments with unrecognized formats** (logged).

Per-year handled rate (basis for certifying advisory coverage windows; gate = 95%):

| year | PB advisories | handled | rate |
|---|---|---|---|
| 2016 | 138 | 134 | 97.1% |
| 2017 | 172 | 164 | 95.3% |
| 2018 | 207 | 202 | 97.6% |
| 2019 | 179 | 174 | 97.2% |
| 2020 | 148 | 147 | 99.3% |

(Six advisories with stray effective years 2011/2012/2015 in the index results are logged and unhandled; they do not affect the 2016–2020 windows.) Advisory rows recovered for the universe: 12,570 (all tiers), including **ES with true contemporaneous initial margins (1.10× maintenance) and notice dates**.

**2008–2015 advisories are indexed (≈4,025 clearing stubs enumerated, zero fetched)** — this is the path to recovering notice dates for 2008–2015 and ES back to 2008. Those older stubs carry the full advisory text *inline* (verified on Chadv08-273: complete rate tables with Current/New Initial+Maintenance in the stub HTML), so a follow-up harvest needs no attachment downloads. Not executed this session (time-box; CME rate limiting is the binding constraint — see §7).

## 6. Data-quality caveats (all flagged in-data, nothing silently filtered)

1. **Initial margins in wayback-history files are retroactively re-rendered.** The same 2008 change shows Spec initial = 1.35× maintenance in a 2012 render but 1.10× in a 2015 render — those files recompute initial with the multiplier in force *at render time*. Maintenance is byte-stable across captures. Only advisory-sourced initials (`initial_reliable=True`, 2016+) are contemporaneous. The union's canonical series is therefore **maintenance**; prereg A2's initial-margin target needs either the advisory route extended backward or an explicit maintenance-based amendment.
2. **XLSX-era advisories state**: "All margin rates are maintenance margin rates in this advisory. All initial margin rates are 110% of these levels" (CME's own text) — direct confirmation of the 1.10× multiplier for that era; initials were left blank in xlsx rows rather than imputed.
3. **Corn (and grain) crop-split labels collide across renders** (§4). 17 demonstrably non-front rows excluded with logging; the front-month series prefers explicitly-labeled front rows (`Spec`/`Mnth 1`), then snapshot confirmation.
4. **CL-2019-10-11-to-2023-10-19.pdf is truncated at exactly 1 MB in the Wayback archive itself** (re-downloaded twice, byte-identical); only its 2023-07→2023-10 pages are extractable. CL coverage over 2017-11→2020-06 rests on advisories (certified) instead.
5. **SPAN2 regimes** (CL from 2023-10-20; COMEX metals from ~Jan 2026) float margins near-daily; "change event" counts in those windows are not comparable to the discrete-advisory era. Same caveat as the prior data-gate report; the prereg event definition still needs your ruling there.
6. **Pre-2009 NYMEX/COMEX (CL, GC, SI, HG)**: no change-history exists on cmegroup.com or its Wayback captures (files begin 2009-01). The old nymex.com site (Wayback) has per-product *current-rates* pages (`lsco/gol/sil/cop_fut_margin.jsp/.aspx`, ~250 margin-related URLs, 2002–2009) — capture-date diffing could bound pre-2009 changes but cannot give exact effective dates; documented as an option, not executed.
7. **Snapshot effective-date semantics**: snapshot-derived dates are "first business date the new value appears," which is the advisory effective date's next settlement in ~87% of cross-checked cases (advisories publish 1 day ahead, effective after close). A ±1-day tolerance is advisable when joining margin events to prices.
8. Coverage start dates reflect **source system starts**, not product history: CBOT products begin 2003-11-24/2004-01-02 (CME Clearing's CBOT takeover); FX begins 2000 (earliest render window).

## 7. Acquisition notes (for reproduction)

- cmegroup.com blocks non-browser TLS (Akamai); `curl_cffi` Chrome impersonation works, but sustained fetching triggers rate limiting and, past a threshold, a full IP block (~30 min penalty; bursts re-trip it instantly). The final attachment harvest ran single-threaded at ~1 request/3.5 s with automatic 10-minute back-offs.
- web.archive.org: all 80 distinct captures of CME margin-history files were downloaded (some required multiple retries; one capture is truncated server-side, §6.4).
- Everything is re-runnable: `scripts/parse_margins.py` (live snapshots), `scripts/parse_wayback_margins.py` (wayback captures), `scripts/parse_advisories.py` (advisories), `scripts/stitch_coverage.py` (union + coverage + conflict resolution).

## 8. Route windows per product

| product | route | windows |
|---|---|---|
| 6E | wayback-history | 2000-01-01..2016-08-15 |
| 6E | advisory | 2016-01-01..2020-12-31 |
| 6E | snapshot-wayback | 2020-06-24..2025-06-24 |
| 6E | snapshot-live | 2020-06-30..2026-06-30 |
| 6J | wayback-history | 2000-02-03..2015-02-24 |
| 6J | snapshot-wayback | 2014-01-02..2017-11-07, 2020-06-24..2025-06-24 |
| 6J | advisory | 2016-01-01..2020-12-31 |
| 6J | snapshot-live | 2020-06-30..2026-06-30 |
| CL | wayback-history | 2009-01-12..2015-02-24 |
| CL | snapshot-wayback | 2014-01-02..2017-11-07, 2020-06-24..2026-06-30 |
| CL | advisory | 2016-01-01..2020-12-31 |
| CL | snapshot-live | 2020-06-30..2026-06-30 |
| ES | advisory | 2016-01-01..2020-12-31 |
| GC | wayback-history | 2009-01-08..2016-08-15 |
| GC | advisory | 2016-01-01..2020-12-31 |
| GC | snapshot-wayback | 2020-06-24..2025-06-24 |
| GC | snapshot-live | 2020-06-30..2026-06-30 |
| HG | wayback-history | 2009-01-08..2016-08-15 |
| HG | advisory | 2016-01-01..2020-12-31 |
| HG | snapshot-wayback | 2020-06-24..2025-06-24 |
| HG | snapshot-live | 2020-06-30..2026-06-30 |
| SI | wayback-history | 2009-01-08..2016-08-16 |
| SI | snapshot-wayback | 2014-01-02..2017-11-07, 2020-06-24..2025-06-24 |
| SI | advisory | 2016-01-01..2020-12-31 |
| SI | snapshot-live | 2020-06-30..2026-06-30 |
| ZC | wayback-history | 2003-11-24..2015-02-24 |
| ZC | snapshot-wayback | 2009-01-02..2017-11-07, 2020-06-24..2025-06-24 |
| ZC | advisory | 2016-01-01..2020-12-31 |
| ZC | snapshot-live | 2020-06-30..2026-06-30 |
| ZN | wayback-history | 2004-01-02..2015-02-24 |
| ZN | snapshot-wayback | 2014-01-02..2017-11-07, 2019-06-28..2025-06-24 |
| ZN | advisory | 2016-01-01..2020-12-31 |
| ZN | snapshot-live | 2020-06-30..2026-06-30 |
| ZS | wayback-history | 2003-11-24..2015-02-24 |
| ZS | snapshot-wayback | 2009-01-02..2017-11-07, 2020-06-24..2026-06-30 |
| ZS | advisory | 2016-01-01..2020-12-31 |
| ZS | snapshot-live | 2020-06-30..2026-06-30 |
| SP_fullsize | wayback-history | 2001-03-01..2016-08-15 |
| SP_fullsize | snapshot-wayback | 2009-01-02..2013-12-31, 2020-06-24..2025-09-26 |

## 9. File inventory

Parsed data (in `data/`):
- `margin_history_stitched.csv` — **the deliverable union**: 2,289 rows (product, effective_date, maintenance, initial + reliability flag, notice_date, rate_label, routes, source, conflict flags).
- `margin_history_stitched_conflicts.csv` — all 19 conflicts with resolution disposition.
- `margin_history_wayback.csv` (3,428 change rows, all rate types/tiers) + `_exceptions.csv` (49) + `margin_wayback_sources.csv` (per-capture windows/row counts).
- `margin_history_wayback_snapshots.csv` — 1,373 front-tier events derived from 848,747 wayback snapshot rows.
- `margin_advisories.csv` (12,570 universe rows incl. ES, notice dates, contemporaneous initials) + `_exceptions.csv` + `_completeness.csv`.
- Previous session's live-site outputs unchanged: `margin_history.csv`, `margin_daily_snapshots.csv.gz`, `margin_flags.csv`.

Raw source caches (in repo, not committed; ~350 MB total — consider .gitignore/git-lfs):
- `data/raw_wayback/` — all 80 Wayback captures.
- `data/raw_advisories/stubs/` — 1,918 clearing-notice stub JSONs.
- `data/raw_advisories/attachments/` — 827 PB advisory attachments (.pdf/.xlsx).

Note added 2026-09-03: the three directories above are listed in `.gitignore` and are not in the public repository. They total about 381 MB and are available on request. Every parsed output they feed is committed in `data/`, so the studies and the backtest reproduce without them. `scripts/parse_wayback_margins.py` and `scripts/parse_advisories.py` read their inputs through a path constant named `SP` near the top of each script, which must be pointed at the directory holding the caches before either is rerun.

## 10. What remains open (for a future session, before any analysis)

1. 2008–2015 advisory stubs (indexed, inline-format, ~4,025 pages) → notice dates 2008–2015 + ES 2008–2015.
2. ES 2021→present: advisories continue on the live site (out of rescue scope).
3. Pre-2009 NYMEX/COMEX: nymex.com Wayback page-diffing (bounded dates only) or CME DataMine.
4. The prereg stop-and-ask items from `data_gate_report.md` §7 remain: ES universe decision, initial-vs-maintenance event definition, SPAN2 event semantics — all now with much better data to decide on.
