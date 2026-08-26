#!/usr/bin/env python3
"""
Rescue parse: Wayback-archived CME margin history PDFs (pre-2020 formats).

Three source formats:
  OLD-A  "Performance Bond History ... Outright Rates": change-level rows,
         per effective date: Spec and Hedge/Member (initial, maintenance).
  OLD-B  "RateTypeDescr" (the *_prior_to_2009 files): change-level rows with
         labeled rate types (Spec, Hedge/Member, Speculative - Old/New Crop, ...).
  NEW    daily snapshot format (parsed by scripts/parse_margins.py, not here).

Faithful-parse rules: unparseable lines -> exceptions list; no imputation;
conflicting duplicate values across captures -> exceptions, never averaged.
Output: one row per (product, effective_date, rate_label) with initial and
maintenance, plus source file and capture timestamp.
"""
import pymupdf
import re
import csv
import sys
import zipfile
import tempfile
import collections
from pathlib import Path

SP = Path("/private/tmp/claude-501/-Users-nav-Desktop-margin-event-study/f85c660f-ac16-4ed2-9659-3eebf5c848a1/scratchpad")
WB = SP / "wb_pdfs"
REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

# filename prefix -> product symbol (user universe). SP kept separate (ES decision pending).
PREFIX_MAP = {"C": "ZC", "S": "ZS", "21": "ZN", "EC": "6E", "JY": "6J",
              "GC": "GC", "SI": "SI", "HG": "HG", "CL": "CL", "SP": "SP_fullsize"}

DATE_A = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
NUM = re.compile(r"^\$?\s*[\d,]+(?:\.\d+)?$")
FURNITURE = (
    "Minimum Performance Bond Requirements", "Outright Rates",
    "20 South Wacker Drive", "cmegroup.com",
)

rows = []       # product, effective_date, rate_label, initial, maintenance, currency, source_file, capture_ts, fmt
exceptions = []
file_meta = []  # source_file, capture_ts, product, fmt, header_window, n_pages


def num(tok):
    return float(tok.replace("$", "").replace(",", "").strip())


def iso_date(mdY):
    m, d, y = mdY.split("/")
    return f"{y}-{int(m):02d}-{int(d):02d}"




def base_label(label):
    """canonical rate-type label with month/tier suffixes stripped; crop qualifiers kept"""
    b = re.sub(r"\s*(mn?ths?|months?|tier)\.?\s*\d.*$", "", label, flags=re.I).strip()
    b = re.sub(r"\s*(mn?ths?|months?)\s*$", "", b, flags=re.I).strip()
    return b.lower()

def classify(doc):
    t = doc[0].get_text()
    if "Performance Bond History for:" in t:
        return "OLD-A"
    if "RateTypeDescr" in t:
        return "OLD-B"
    if "Business Date" in t:
        return "NEW"
    return None


def is_furniture(ln):
    return (ln in ("ISO", "Initial", "Maintenance", "Maint.", "RateTypeDescr") or
            any(ln.startswith(f) for f in FURNITURE) or
            ln.startswith("Performance Bond History for:") or
            re.match(r"^Page \d+ of \d+$", ln))


def page_tokens(doc):
    """tokens across pages with per-page header/footer furniture stripped, so
    rate rows split across page boundaries reunite."""
    out = []
    for p in doc:
        toks = [l.strip() for l in p.get_text().split("\n") if l.strip()]
        # footer blocks (address / site / page number) can be emitted mid-stream by
        # the text extractor; drop them anywhere, and drop a print-date token only
        # when adjacent to such a footer anchor (data dates elsewhere are preserved).
        anchor = [bool(t.startswith(("20 South Wacker", "cmegroup.com")) or
                       re.match(r"^Page \d+ of \d+$", t)) for t in toks]
        keep = []
        for i, t in enumerate(toks):
            if anchor[i]:
                continue
            if DATE_A.match(t) and ((i > 0 and anchor[i - 1]) or (i + 1 < len(toks) and anchor[i + 1])):
                continue
            keep.append(t)
        out += keep
    return out


CUR_RE = re.compile(r"^[A-Z]{3}$")


def _is_label_tok(t):
    return not NUM.match(t) and not CUR_RE.match(t) and not DATE_A.match(t) and not is_furniture(t)


def detect_order(toks):
    """OLD-A renders permute record columns; vote per file."""
    v = {"L1": 0, "L2": 0, "L3": 0}
    for i in range(len(toks) - 3):
        a, b, c, d = toks[i:i + 4]
        if NUM.match(a) and NUM.match(b) and CUR_RE.match(c) and _is_label_tok(d):
            v["L1"] += 1          # [init, maint, CUR, label]
        if NUM.match(a) and NUM.match(b) and _is_label_tok(c) and CUR_RE.match(d):
            v["L2"] += 1          # [init, maint, label, CUR]
        if _is_label_tok(a) and CUR_RE.match(b) and NUM.match(c) and NUM.match(d):
            v["L3"] += 1          # [label, CUR, init, maint]
    return max(v, key=v.get), v


def parse_old_a(doc, product, src, ts):
    """change-history 'Outright Rates' format; column order varies by render."""
    seq_counter = {}
    toks = page_tokens(doc)
    order, votes = detect_order(toks)
    cur_date = None
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if is_furniture(t):
            i += 1
            continue
        if DATE_A.match(t):
            cur_date = iso_date(t)
            i += 1
            continue
        rec = None
        if i + 3 < n:
            a, b, c, d = toks[i:i + 4]
            if order == "L1" and NUM.match(a) and NUM.match(b) and CUR_RE.match(c) and _is_label_tok(d):
                rec = (num(a), num(b), c, d)
            elif order == "L2" and NUM.match(a) and NUM.match(b) and _is_label_tok(c) and CUR_RE.match(d):
                rec = (num(a), num(b), d, c)
            elif order == "L3" and _is_label_tok(a) and CUR_RE.match(b) and NUM.match(c) and NUM.match(d):
                rec = (num(c), num(d), b, a)
        if rec is not None:
            init_v, maint_v, curncy, label = rec
            label = re.sub(r"\s+", " ", label.replace("...", " ").strip().rstrip(".").strip())
            if cur_date is None:
                exceptions.append((src, "OLD-A", " | ".join(toks[i:i + 4]), "rate row before any date"))
            elif maint_v <= 0 or init_v < 0:
                exceptions.append((src, "OLD-A", " | ".join(toks[i:i + 4]), "non-positive margin; parse artifact, excluded"))
            else:
                bl = base_label(label)
                seq_counter[(cur_date, bl)] = seq_counter.get((cur_date, bl), 0) + 1
                rows.append(dict(product=product, effective_date=cur_date, rate_label=label,
                                 base_label=bl, tier_seq=seq_counter[(cur_date, bl)],
                                 initial=init_v, maintenance=maint_v, currency=curncy,
                                 source_file=src, capture_ts=ts, fmt="OLD-A"))
            i += 4
            continue
        if NUM.match(t) or _is_label_tok(t):
            exceptions.append((src, "OLD-A", " | ".join(toks[i:i + 4]),
                               f"token run not matching record order {order}"))
        i += 1


def parse_old_b(doc, product, src, ts):
    """product title; date; then repeating [label, $init, $maint]."""
    seq_counter = {}
    toks = page_tokens(doc)
    cur_date = None
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if is_furniture(t) or re.match(r".+\(.+\)\s*\(\w+\)$", t):
            i += 1
            continue
        if t in ("Futures Opening Day:", "Options Opening Day:"):
            i += 2  # skip label and its date
            continue
        if DATE_A.match(t) or re.match(r"^\d{2}/\d{2}/\d{4}$", t):
            nxt = toks[i + 1] if i + 1 < n else ""
            if not DATE_A.match(nxt) and not nxt.startswith(("Futures", "Options")):
                cur_date = iso_date(t)
            i += 1
            continue
        # label followed by two $ numbers
        if i + 2 < n and NUM.match(toks[i + 1]) and NUM.match(toks[i + 2]) and not NUM.match(t):
            if cur_date is None:
                exceptions.append((src, "OLD-B", " | ".join(toks[i:i + 3]), "rate row before any date"))
            else:
                bl = base_label(t)
                seq_counter[(cur_date, bl)] = seq_counter.get((cur_date, bl), 0) + 1
                rows.append(dict(product=product, effective_date=cur_date, rate_label=t,
                                 base_label=bl, tier_seq=seq_counter[(cur_date, bl)],
                                 initial=num(toks[i + 1]), maintenance=num(toks[i + 2]), currency="USD",
                                 source_file=src, capture_ts=ts, fmt="OLD-B"))
            i += 3
            continue
        if NUM.match(t):
            exceptions.append((src, "OLD-B", " | ".join(toks[max(0, i - 2):i + 3]), "orphan numeric token"))
        i += 1


def product_of(fname):
    m = re.match(r"^([A-Z0-9]+)[_-]", fname)
    if not m:
        return None
    return PREFIX_MAP.get(m.group(1))


# ---------------- NEW snapshot-format captures ----------------
DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_US_TIME = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})\s+0:00$")
NUM_PLAIN = re.compile(r"^[\d,]+(?:\.\d+)?$")
TIER = re.compile(r"^([A-Z0-9]{1,4})-(\d+)$")
EXCHANGES = {"CBT", "CME", "CMX", "NYM"}
HEADER_TOKENS = {
    "Minimum Performance Bond Requirements", "Business Date", "Description",
    "Exchange", "Margin", "Margin Long", "Margin Short", "Roll Product Code",
    "Exchange Margin",
}


def new_date(tok):
    """snapshot business-date token -> ISO, accepting '2020-06-30' and '11/7/2017 0:00'"""
    if DATE_ISO.match(tok):
        return tok
    m = DATE_US_TIME.match(tok)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None

snapshot_rows = []  # product, business_date, tier_idx, margin, margin_short, source_file, capture_ts


def parse_new_snapshot(doc, product, src, ts):
    for pno, page in enumerate(doc, start=1):
        toks = [t.strip() for t in page.get_text().split("\n") if t.strip()]
        toks = [t for t in toks if t not in HEADER_TOKENS]
        rec = []
        recs = []
        for t in toks:
            nd = new_date(t)
            if nd is not None:
                if rec:
                    recs.append(rec)
                rec = [nd]
            elif rec:
                rec.append(t)
        if rec:
            recs.append(rec)
        for r in recs:
            if len(r) < 5:
                exceptions.append((src, "NEW", " | ".join(r), "too few tokens"))
                continue
            mt = TIER.match(r[-1])
            exch_i = next((i for i, t in enumerate(r) if t in EXCHANGES), None)
            if not mt or exch_i is None:
                exceptions.append((src, "NEW", " | ".join(r), "no tier code or exchange"))
                continue
            nums = r[exch_i + 1:-1]
            if len(nums) not in (1, 2) or not all(NUM_PLAIN.match(x) for x in nums):
                exceptions.append((src, "NEW", " | ".join(r), "margin tokens not 1-2 numerics"))
                continue
            margin_val = float(nums[0].replace(",", ""))
            if margin_val <= 0:
                exceptions.append((src, "NEW", " | ".join(r), "non-positive margin value; parse artifact, excluded"))
                continue
            snapshot_rows.append(dict(
                product=product, business_date=r[0], tier_idx=int(mt.group(2)),
                margin=margin_val,
                margin_short=float(nums[1].replace(",", "")) if len(nums) == 2 else None,
                source_file=src, capture_ts=ts))


def snapshot_events():
    """front-tier change events from wayback NEW-format snapshot captures"""
    grids = collections.defaultdict(lambda: collections.defaultdict(dict))
    src_of = {}
    for s in snapshot_rows:
        grids[s["product"]][s["business_date"]][s["tier_idx"]] = (s["margin"], s["margin_short"])
        src_of[(s["product"], s["business_date"])] = (s["source_file"], s["capture_ts"])
    ev = []
    for product, dates_map in grids.items():
        dates = sorted(dates_map)
        prev_d = None
        for d in dates:
            t1 = min(dates_map[d])
            cur, cur_s = dates_map[d][t1]
            if prev_d is None:
                ev.append(dict(product=product, effective_date=d, maintenance=cur,
                               margin_short=cur_s, prev_maintenance=None, direction="series_start",
                               source_file=src_of[(product, d)][0], capture_ts=src_of[(product, d)][1]))
            else:
                pt1 = min(dates_map[prev_d])
                prv, prv_s = dates_map[prev_d][pt1]
                if cur != prv or cur_s != prv_s:
                    ev.append(dict(product=product, effective_date=d, maintenance=cur,
                                   margin_short=cur_s, prev_maintenance=prv,
                                   direction="increase" if cur > prv else ("decrease" if cur < prv else "short_side_only"),
                                   source_file=src_of[(product, d)][0], capture_ts=src_of[(product, d)][1]))
            prev_d = d
    return ev


def handle_pdf(path, fname, ts):
    product = product_of(fname)
    if product is None:
        exceptions.append((fname, "", "", "filename prefix not in product map"))
        return
    try:
        doc = pymupdf.open(str(path))
    except Exception as e:
        exceptions.append((fname, "", "", f"unreadable pdf: {e}"))
        return
    fmt = classify(doc)
    hdr = re.search(r"Performance Bond History for: (\d+/\d+/\d+) - (\d+/\d+/\d+)", doc[0].get_text())
    file_meta.append(dict(source_file=fname, capture_ts=ts, product=product, fmt=fmt,
                          window_start=iso_date(hdr.group(1)) if hdr else "",
                          window_end=iso_date(hdr.group(2)) if hdr else "",
                          n_pages=len(doc)))
    if fmt == "OLD-A":
        parse_old_a(doc, product, fname, ts)
    elif fmt == "OLD-B":
        parse_old_b(doc, product, fname, ts)
    elif fmt == "NEW":
        parse_new_snapshot(doc, product, fname, ts)
    else:
        exceptions.append((fname, "?", doc[0].get_text()[:80], "unrecognized format"))
    doc.close()


def main():
    files = sorted(WB.iterdir())
    for f in files:
        if f.stat().st_size == 0:
            exceptions.append((f.name, "", "", "empty download"))
            continue
        ts, _, fname = f.name.partition("__")
        if fname.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(f) as z:
                    for member in z.namelist():
                        if member.lower().endswith(".pdf"):
                            with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                                tmp.write(z.read(member))
                                tmp.flush()
                                handle_pdf(tmp.name, Path(member).name, ts)
                        else:
                            exceptions.append((f.name, "", member, "non-pdf zip member"))
            except zipfile.BadZipFile:
                exceptions.append((f.name, "", "", "bad zip"))
        elif fname.lower().endswith(".pdf"):
            head = open(f, "rb").read(5)
            if head != b"%PDF-":
                exceptions.append((f.name, "", head.decode("latin1"), "not a pdf"))
                continue
            handle_pdf(f, fname, ts)

    # -------- dedupe across captures --------
    # identical (product, date, label, initial, maint) rows from different captures collapse;
    # conflicting values for the same key -> exception, keep all rows flagged.
    bykey = collections.defaultdict(set)
    for r in rows:
        bykey[(r["product"], r["effective_date"], r["base_label"], r["tier_seq"])].add((r["initial"], r["maintenance"]))
    # initial-only conflicts: maintenance agrees across captures but initial differs.
    # Cause: these rendered histories recompute initial = maint x multiplier in force
    # AT RENDER TIME, so initial is not a reliable historical series in Route 1.
    conf_maint = {k for k, v in bykey.items() if len({m for _, m in v}) > 1}
    conf_init = {k for k, v in bykey.items() if len(v) > 1 and k not in conf_maint}
    seen = set()
    out = []
    for r in sorted(rows, key=lambda r: (r["product"], r["effective_date"], r["base_label"], r["tier_seq"], r["capture_ts"])):
        k = (r["product"], r["effective_date"], r["base_label"], r["tier_seq"])
        kk = k + (r["maintenance"],)
        if k in conf_init:
            # keep the earliest capture's initial (closest to contemporaneous multiplier)
            if kk in seen:
                continue
            seen.add(kk)
        else:
            if kk + (r["initial"],) in seen:
                continue
            seen.add(kk + (r["initial"],))
        if k in conf_maint:
            r["conflict_flag"] = "maintenance_front_tier" if r["tier_seq"] == 1 else "maintenance_back_tier_regroup"
        elif k in conf_init:
            r["conflict_flag"] = "initial_restated"
        else:
            r["conflict_flag"] = ""
        out.append(r)
    conflicts = conf_maint
    for k in sorted(conf_maint):
        sev = "FRONT-TIER" if k[3] == 1 else "back-tier-regroup"
        exceptions.append(("(multiple)", "", str(k), f"MAINTENANCE conflict ({sev}) across captures: {sorted(bykey[k])}"))
    print(f"initial-only restatement conflicts (kept earliest capture's initial): {len(conf_init)}")

    cols = ["product", "effective_date", "rate_label", "base_label", "tier_seq",
            "initial", "maintenance", "currency", "source_file", "capture_ts", "fmt", "conflict_flag"]
    with open(DATA / "margin_history_wayback.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    with open(DATA / "margin_history_wayback_exceptions.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "fmt", "raw", "reason"])
        w.writerows(exceptions)

    # -------- wayback NEW-format snapshot events --------
    sev = snapshot_events()
    scols = ["product", "effective_date", "maintenance", "margin_short", "prev_maintenance",
             "direction", "source_file", "capture_ts"]
    with open(DATA / "margin_history_wayback_snapshots.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=scols)
        w.writeheader()
        w.writerows(sorted(sev, key=lambda r: (r["product"], r["effective_date"])))
    print(f"wayback NEW-format snapshot rows: {len(snapshot_rows)}; derived change events: {len(sev)}")

    # per-source-file summary with observed row ranges
    import itertools
    obs = collections.defaultdict(lambda: [None, None, 0])
    for r in rows:
        k = (r["source_file"], r["capture_ts"])
        o = obs[k]
        o[0] = r["effective_date"] if o[0] is None else min(o[0], r["effective_date"])
        o[1] = r["effective_date"] if o[1] is None else max(o[1], r["effective_date"])
        o[2] += 1
    for s in snapshot_rows:
        k = (s["source_file"], s["capture_ts"])
        o = obs[k]
        o[0] = s["business_date"] if o[0] is None else min(o[0], s["business_date"])
        o[1] = s["business_date"] if o[1] is None else max(o[1], s["business_date"])
        o[2] += 1
    # truncation check: NEW snapshot files should yield ~35+ rows/page
    for fm in file_meta:
        if fm["fmt"] == "NEW":
            o = obs.get((fm["source_file"], fm["capture_ts"]), [None, None, 0])
            if fm["n_pages"] and o[2] / fm["n_pages"] < 15:
                exceptions.append((f"{fm['source_file']}@{fm['capture_ts']}", "NEW",
                                   f"{o[2]} rows from {fm['n_pages']} pages",
                                   "LIKELY TRUNCATED/CORRUPT capture: row density too low"))
    with open(DATA / "margin_wayback_sources.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_file", "capture_ts", "product", "fmt",
                                           "window_start", "window_end", "n_pages",
                                           "first_row_date", "last_row_date", "n_rows"])
        w.writeheader()
        for fm in sorted(file_meta, key=lambda x: (x["product"], x["source_file"], x["capture_ts"])):
            o = obs.get((fm["source_file"], fm["capture_ts"]), [None, None, 0])
            fm2 = dict(fm)
            fm2.update(first_row_date=o[0] or "", last_row_date=o[1] or "", n_rows=o[2])
            w.writerow(fm2)
    print(f"rows: {len(out)} (from {len(rows)} pre-dedupe), conflicts: {len(conflicts)}, exceptions: {len(exceptions)}")
    per = collections.defaultdict(lambda: [None, None, 0])
    for r in out:
        p = per[r["product"]]
        p[0] = r["effective_date"] if p[0] is None else min(p[0], r["effective_date"])
        p[1] = r["effective_date"] if p[1] is None else max(p[1], r["effective_date"])
        p[2] += 1
    for prod, (d0, d1, n) in sorted(per.items()):
        print(f"  {prod}: {d0} -> {d1}  ({n} rows)")


if __name__ == "__main__":
    main()
