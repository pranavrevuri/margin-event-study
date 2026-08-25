# pysystemtrade Futures Data — Provenance and Assessment

Downloaded 2026-08-25 from github.com/robcarver17/pysystemtrade (master branch,
`data/futures/`), free and keyless. **STATUS: candidate primary source for 6 of 9
products, pending user decision. No return calculations performed.**

## Files

- `multiple/<INSTR>.csv` — per date: PRICE / FORWARD / CARRY, each an **actual
  unadjusted price of an explicitly identified contract** (YYYYMM00 ids). This is
  genuine per-contract settlement data, limited to the 2–3 contracts of the
  repo's roll cycle at each date. Later years include a few intraday timestamps;
  the last row per date (23:00) is the daily close/settlement row.
- `adjusted/<INSTR>.csv` — continuous **back-adjusted (panama / points-shift)**
  series (documented default; early values go negative, confirming points method).
- `roll_calendars/<INSTR>.csv` — explicit roll dates with current/next/carry
  contract ids. Rolls are therefore fully identifiable, unlike Stooq.
- `instrumentconfig.csv` reference is in the repo; LICENSE (GPL-3.0) and
  docs_data.md (data documentation) are included here.

## Instrument mapping (verified via pointsize/description)

| ours | pysystemtrade | pointsize check | contract months held |
|---|---|---|---|
| ZN | US10 | $1,000/pt ✓ | H,M,U,Z (complete cycle) |
| 6E | EUR | 125,000 ✓ | H,M,U,Z (complete) |
| 6J | JPY | 12,500,000 ✓ | H,M,U,Z (complete) |
| GC | GOLD | 100 oz ✓ | G,J,M,Q,V,Z (complete) |
| SI | SILVER | pointsize 1000 (⚠ SI full-size is 5,000 oz — config suggests a 1,000-oz contract; prices are $/oz either way) | H,K,N,U,Z (complete) |
| HG | COPPER | 25,000 lb ✓ | H,N,U,Z (**missing K/May**) |
| CL | CRUDE_W | $1,000/pt ✓ | **Z only** ("Crude Winter": December contracts) |
| ZC | CORN | $50/cent ✓ | **Z only** (December) |
| ZS | SOYBEAN | $50/cent ✓ | **X only** (November) |

## Coverage and freshness

All 9 instruments: data begins well before every margin-data start (earliest:
SILVER 1970, latest-starting: EUR 1999-06-15) and **ends 2024-03-28** — the shipped
snapshot is ~29 months stale. Documented extension processes exist (Barchart
Premier + bc-utils, ~250 downloads/day, paid; or an Interactive Brokers account
via the repo's update scripts) — neither is free/keyless.

## Source and license

Prices were collected by the repo author from **Barchart and Interactive Brokers**
(historically Quandl); per-row provenance is not stated. Repo license: **GPL-3.0**
(code and shipped data alike); the underlying market data's redistribution rights
are not separately licensed — treat as research-grade, non-redistributable.

## Cross-check vs Stooq continuous (data/prices/), 3 dates per product

Compared Stooq close vs pst multiple-prices PRICE (both unadjusted):

- **ZN**: 0.02%/0.00%/0.00% — settlement-exact (to the 1/64th) on matching quarters.
- **6J**: 0.12%/0.05%/0.03% ✓; **6E**: 0.01%/−0.06% on matching contracts (−0.82%
  on 2010-06-15 is a roll-timing artifact: pst still held the expiring June).
- **GC**: −0.11%/−0.13%/−0.22% — different delivery months (calendar spread), consistent.
- **SI/HG**: values differ by exactly 100× — **quote convention** (Stooq cents/oz
  and cents/lb vs pst dollars); after scaling, differences are calendar spreads.
- **CL**: +3.4%/+16.4%/+11.6%; **ZC** up to +6.2%; **ZS** up to −3.2% — pst holds
  only December (CL, ZC) / November (ZS) contracts, so gaps vs Stooq's front month
  are contango/backwardation, not data error.

Conclusion: both sources are settlement-based; agreement is exact where the same
contract is compared.

## Fit against prereg A2 (facts, decision pending)

A2 wants the nearest-to-expiry contract with ≥15 trading days to expiry.
- **ZN, 6E, 6J, GC, SI (and HG minus May)**: the pst PRICE/FORWARD contracts are the
  real front/second contracts of each product's actual cycle, with explicit roll
  dates → close to A2-usable per-contract data through 2024-03-28. Caveats: only
  2–3 contracts per date exist (if the prereg rule selects a contract outside the
  held pair near rolls, that event's contract is missing); HG lacks May contracts.
- **CL, ZC, ZS**: one contract per year (Dec/Nov) — cannot implement
  nearest-to-expiry at all. Not A2-usable.
- All products need a 2024-04 → present extension from another source.
