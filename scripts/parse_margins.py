#!/usr/bin/env python3
"""
Prompt 1 (data gate) — parse CME historical margin PDFs into change-level tables.

Source PDFs: https://www.cmegroup.com/solutions/risk-management/margin-services/historical-margins.html
downloaded into data/margin_pdfs/. Files are daily snapshots titled "Minimum
Performance Bond Requirements": one row per (business date, contract tier),
with a single "Margin" column (SPAN era) or "Margin Long"/"Margin Short"
(SPAN2 era, CL from 2023-10-20).

Faithful-parse principles (per prereg conduct rules):
  - no imputation; unparseable lines go to the exceptions file, never guessed;
  - no silent filtering; suspicious changes are FLAGGED, not dropped;
  - initial_margin is left blank: the PDFs publish only the minimum
    performance bond (maintenance) level, not the initial/maintenance pair;
  - effective_date is DERIVED: the first business date on which a new value
    appears in the snapshots (the PDFs contain no advisory/notice dates).
"""
import pymupdf
import re
import csv
import gzip
import collections
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PDF_DIR = REPO / "data" / "margin_pdfs"
DATA = REPO / "data"

# product symbol (user universe) -> (pdf files, expected tier prefix, expected description substrings)
PRODUCTS = {
    "ZC": (["C-2020-to-present.pdf"], "C"),
    "ZS": (["S-2020-to-present.pdf"], "S"),
    "ZN": (["21-2020-to-present.pdf"], "21"),
    "6E": (["EC-2020-to-present.pdf"], "EC"),
    "6J": (["JY-2020-to-present.pdf"], "JY"),
    "GC": (["GC-2020-to-present.pdf"], "GC"),
    "SI": (["SI-2020-to-present.pdf"], "SI"),
    "HG": (["HG-2020-to-present.pdf"], "HG"),
    "CL": (["CL-2020-to-2023-10-19.pdf", "CL-2023-to-present.pdf"], "CL"),
}
# ES has no PDF on the CME historical-margins page (only full-size SP): recorded as a
# missing-product exception below, NOT silently substituted.

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUM_RE = re.compile(r"^[\d,]+(?:\.\d+)?$")
TIER_RE = re.compile(r"^([A-Z0-9]{1,4})-(\d+)$")
EXCHANGES = {"CBT", "CME", "CMX", "NYM"}
HEADER_TOKENS = {
    "Minimum Performance Bond Requirements", "Business Date", "Description",
    "Exchange", "Margin", "Margin Long", "Margin Short", "Roll Product Code",
}

exceptions = []   # dicts: source_file, page, row_type, raw, reason
snapshots = []    # dicts: product, business_date, tier_prefix, tier_idx, margin, margin_long, margin_short, source_file


def parse_pdf(product, fname):
    doc = pymupdf.open(PDF_DIR / fname)
    n_rows = 0
    for pno, page in enumerate(doc, start=1):
        tokens = [t.strip() for t in page.get_text().split("\n") if t.strip()]
        tokens = [t for t in tokens if t not in HEADER_TOKENS]
        # group into records: each record starts at a date token
        rec = []
        records = []
        for t in tokens:
            if DATE_RE.match(t):
                if rec:
                    records.append(rec)
                rec = [t]
            else:
                if rec:
                    rec.append(t)
                else:
                    exceptions.append(dict(source_file=fname, page=pno, row_type="orphan_token",
                                           raw=t, reason="token before first date on page"))
        if rec:
            records.append(rec)
        for r in records:
            ok, parsed, reason = parse_record(r)
            if not ok:
                exceptions.append(dict(source_file=fname, page=pno, row_type="unparseable_row",
                                       raw=" | ".join(r), reason=reason))
                continue
            date, desc, exch, nums, tier_prefix, tier_idx = parsed
            snapshots.append(dict(product=product, business_date=date,
                                  tier_prefix=tier_prefix, tier_idx=tier_idx,
                                  margin=nums[0],
                                  margin_long=nums[0] if len(nums) == 2 else "",
                                  margin_short=nums[1] if len(nums) == 2 else "",
                                  description=desc, exchange=exch, source_file=fname))
            n_rows += 1
    doc.close()
    return n_rows


def parse_record(r):
    # expected: [date, desc..., exchange, num, (num), tiercode]
    if len(r) < 5:
        return False, None, f"too few tokens ({len(r)})"
    date = r[0]
    m = TIER_RE.match(r[-1])
    if not m:
        return False, None, f"last token not a tier code: {r[-1]!r}"
    tier_prefix, tier_idx = m.group(1), int(m.group(2))
    exch_idx = None
    for i, t in enumerate(r):
        if t in EXCHANGES:
            exch_idx = i
            break
    if exch_idx is None:
        return False, None, "no exchange token found"
    desc = " ".join(r[1:exch_idx])
    num_tokens = r[exch_idx + 1:-1]
    if len(num_tokens) not in (1, 2) or not all(NUM_RE.match(t) for t in num_tokens):
        return False, None, f"margin tokens not 1-2 numerics: {num_tokens!r}"
    nums = [float(t.replace(",", "")) for t in num_tokens]
    return True, (date, desc, exch_idx and " ".join([r[exch_idx]]), nums, tier_prefix, tier_idx), ""


def main():
    for product, (files, prefix) in PRODUCTS.items():
        for f in files:
            n = parse_pdf(product, f)
            print(f"parsed {f}: {n} rows")
    exceptions.append(dict(source_file="(none)", page="", row_type="missing_product",
                           raw="ES", reason="No E-mini S&P 500 PDF exists on the CME historical-margins page; "
                                            "only full-size SP is offered. Not substituted."))

    # tier-prefix sanity: rows whose prefix doesn't match the file's product go to exceptions
    expected = {p: pre for p, (fs, pre) in PRODUCTS.items()}
    clean = []
    for s in snapshots:
        if s["tier_prefix"] != expected[s["product"]]:
            exceptions.append(dict(source_file=s["source_file"], page="", row_type="unexpected_tier_prefix",
                                   raw=f"{s['business_date']} {s['tier_prefix']}-{s['tier_idx']} {s['margin']}",
                                   reason=f"tier prefix {s['tier_prefix']} != expected {expected[s['product']]}"))
        else:
            clean.append(s)

    # duplicate (product, date, tier) checks
    seen = {}
    dedup = []
    for s in clean:
        key = (s["product"], s["business_date"], s["tier_idx"], s["source_file"])
        if key in seen:
            if (seen[key]["margin"], seen[key]["margin_short"]) != (s["margin"], s["margin_short"]):
                exceptions.append(dict(source_file=s["source_file"], page="", row_type="conflicting_duplicate",
                                       raw=str(key), reason=f"values {seen[key]['margin']} vs {s['margin']}"))
            # exact duplicates silently collapse (none expected)
        else:
            seen[key] = s
            dedup.append(s)

    # CL appears in two files; check the overlap boundary
    cl_files = collections.defaultdict(set)
    for s in dedup:
        if s["product"] == "CL":
            cl_files[s["source_file"]].add(s["business_date"])
    if len(cl_files) == 2:
        f1, f2 = sorted(cl_files)
        overlap = cl_files[f1] & cl_files[f2]
        if overlap:
            exceptions.append(dict(source_file=f"{f1}+{f2}", page="", row_type="file_overlap",
                                   raw=f"{len(overlap)} overlapping business dates",
                                   reason="same dates present in both CL files; second file's rows kept separately"))

    # write faithful snapshot table
    snap_path = DATA / "margin_daily_snapshots.csv.gz"
    cols = ["product", "business_date", "tier_prefix", "tier_idx", "margin",
            "margin_long", "margin_short", "description", "exchange", "source_file"]
    with gzip.open(snap_path, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for s in sorted(dedup, key=lambda x: (x["product"], x["business_date"], x["tier_idx"])):
            w.writerow(s)
    print(f"wrote {snap_path} ({len(dedup)} rows)")

    # ---------- derive change events on the front (tier-1) series ----------
    # union trading calendar from observed business dates
    all_dates = sorted({s["business_date"] for s in dedup})
    date_pos = {d: i for i, d in enumerate(all_dates)}

    # per product: date -> {tier_idx: (margin, margin_short_or_None)}
    grids = collections.defaultdict(lambda: collections.defaultdict(dict))
    src_of = {}
    for s in dedup:
        grids[s["product"]][s["business_date"]][s["tier_idx"]] = (
            s["margin"], s["margin_short"] if s["margin_short"] != "" else None)
        src_of[(s["product"], s["business_date"])] = s["source_file"]

    events = []
    coverage = {}
    for product in PRODUCTS:
        dates = sorted(grids[product])
        coverage[product] = (dates[0], dates[-1], len(dates))
        # missing-date check vs union calendar
        missing = [d for d in all_dates if dates[0] <= d <= dates[-1] and d not in grids[product]]
        for d in missing:
            exceptions.append(dict(source_file="", page="", row_type="missing_business_date",
                                   raw=f"{product} {d}", reason="date present for other products but absent here"))
        prev_d = None
        for d in dates:
            tiers = grids[product][d]
            t1 = min(tiers)
            if prev_d is not None:
                ptiers = grids[product][prev_d]
                pt1 = min(ptiers)
                cur, cur_s = tiers[t1]
                prv, prv_s = ptiers[pt1]
                changed = (cur != prv) or (cur_s != prv_s)
                if changed:
                    # roll-shift heuristic: does today's vector equal yesterday's shifted by one tier?
                    common_shift = [(i, i + 1) for i in tiers if (i + 1) in ptiers]
                    common_same = [i for i in tiers if i in ptiers]
                    frac_shift = (sum(1 for i, j in common_shift if tiers[i][0] == ptiers[j][0]) / len(common_shift)) if common_shift else 0.0
                    frac_same = (sum(1 for i in common_same if tiers[i][0] == ptiers[i][0]) / len(common_same)) if common_same else 0.0
                    n_chg = sum(1 for i in common_same if tiers[i][0] != ptiers[i][0])
                    likely_roll = frac_shift >= 0.6 and frac_shift > frac_same
                    src1, src2 = src_of[(product, prev_d)], src_of[(product, d)]
                    transition = src1 != src2
                    pct = (cur / prv - 1.0) if prv else None
                    events.append(dict(
                        product=product, effective_date=d, notice_date="",
                        initial_margin="",           # not published in these PDFs
                        maintenance_margin=cur,      # published minimum performance bond level (long side in SPAN2 files)
                        source_file=src2,
                        prev_maintenance_margin=prv, prev_business_date=prev_d,
                        margin_short=cur_s if cur_s is not None else "",
                        prev_margin_short=prv_s if prv_s is not None else "",
                        pct_change=pct,
                        direction="increase" if cur > prv else ("decrease" if cur < prv else
                                  ("short_side_only_change" if cur_s != prv_s else "none")),
                        tier_code=f"{expected[product]}-{t1}",
                        n_tiers_changed=n_chg, n_tiers_total=len(common_same),
                        frac_tiers_shift_match=round(frac_shift, 3),
                        likely_roll_shift=likely_roll,
                        methodology_transition=transition,
                        is_series_start=False,
                    ))
            else:
                cur, cur_s = tiers[t1]
                events.append(dict(
                    product=product, effective_date=d, notice_date="",
                    initial_margin="", maintenance_margin=cur,
                    source_file=src_of[(product, d)],
                    prev_maintenance_margin="", prev_business_date="",
                    margin_short=cur_s if cur_s is not None else "", prev_margin_short="",
                    pct_change="", direction="series_start",
                    tier_code=f"{expected[product]}-{t1}",
                    n_tiers_changed="", n_tiers_total=len(tiers),
                    frac_tiers_shift_match="", likely_roll_shift="",
                    methodology_transition=False, is_series_start=True,
                ))
            prev_d = d

    hist_cols = ["product", "effective_date", "notice_date", "initial_margin", "maintenance_margin",
                 "source_file", "prev_maintenance_margin", "prev_business_date",
                 "margin_short", "prev_margin_short", "pct_change", "direction", "tier_code",
                 "n_tiers_changed", "n_tiers_total", "frac_tiers_shift_match",
                 "likely_roll_shift", "methodology_transition", "is_series_start"]
    hist_path = DATA / "margin_history.csv"
    with open(hist_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hist_cols)
        w.writeheader()
        for e in sorted(events, key=lambda x: (x["product"], x["effective_date"])):
            w.writerow(e)
    print(f"wrote {hist_path} ({len(events)} rows incl. series-start anchors)")

    # flags: any parsed change larger than +200% (and methodology transitions, for review)
    flags = [e for e in events if not e["is_series_start"] and
             ((e["pct_change"] not in ("", None) and e["pct_change"] > 2.0) or e["methodology_transition"])]
    flag_path = DATA / "margin_flags.csv"
    with open(flag_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hist_cols + ["flag_reason"])
        w.writeheader()
        for e in flags:
            e2 = dict(e)
            e2["flag_reason"] = "; ".join(
                (["pct_change > +200%"] if (e["pct_change"] not in ("", None) and e["pct_change"] > 2.0) else []) +
                (["SPAN->SPAN2 file boundary"] if e["methodology_transition"] else []))
            w.writerow(e2)
    print(f"wrote {flag_path} ({len(flags)} rows)")

    exc_path = DATA / "margin_history_exceptions.csv"
    with open(exc_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_file", "page", "row_type", "raw", "reason"])
        w.writeheader()
        for e in exceptions:
            w.writerow(e)
    print(f"wrote {exc_path} ({len(exceptions)} rows)")

    print("\ncoverage per product:")
    for p, (d0, d1, n) in coverage.items():
        print(f"  {p}: {d0} -> {d1} ({n} business dates)")


if __name__ == "__main__":
    main()
