#!/usr/bin/env python3
"""
Stitch all recovered margin-change sources into one deduplicated union and
compute per-product coverage segments + gaps.

Sources (route column):
  wayback-history   OLD-A/OLD-B change-history PDFs from web.archive.org
                    (spec front-tier maintenance; initial unreliable: restated)
  advisory          CME clearing PB advisories (notice_date + contemporaneous
                    initial+maintenance; front tier)
  snapshot-wayback  Wayback captures of daily-snapshot PDFs (front tier)
  snapshot-live     data/margin_history.csv from the live 2020->2026 snapshots

Outputs:
  data/margin_history_stitched.csv           union of change rows, deduped
  data/margin_history_stitched_conflicts.csv cross-route disagreements
  stdout: per-product coverage segments and gaps (feeds coverage_report.md)
"""
import csv
import collections
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

SNAPSHOT_LIVE_START, SNAPSHOT_LIVE_END = "2020-06-30", "2026-06-30"
ADVISORY_YEARS_COMPLETE = None  # set in main() from the harvest state file, if present


def load_rows():
    """one candidate change-row per (product, date, route): maintenance level"""
    out = []

    w = pd.read_csv(DATA / "margin_history_wayback.csv")
    spec = w[w.base_label.str.startswith(("spec", "speculative"), na=False)]
    # front row per (product, date, source): plain 'spec' tier 1 if present, else
    # first spec-family row in document order (crop/all variants), label carried.
    def crop_rank(b):
        # the outright/front series: plain spec, then all-months, then old crop
        # (nearby contracts), then new-crop variants (deferred months)
        if b == "spec":
            return 0
        if "all" in b:
            return 1
        if "old crop" in b:
            return 2
        if "2nd new" in b:
            return 3
        if "new crop" in b:
            return 4
        return 5

    spec = spec.assign(_rank=spec.base_label.map(crop_rank))
    for (prod, d, src), g in spec.groupby(["product", "effective_date", "source_file"]):
        r = g.sort_values(["_rank", "tier_seq"], kind="stable").iloc[0]
        out.append(dict(product=prod, effective_date=d, maintenance=r.maintenance,
                        initial=r.initial, initial_reliable=False, notice_date="",
                        rate_label=r.rate_label, route="wayback-history",
                        source=f"{src}@{r.capture_ts}",
                        conflict_note="maintenance_conflict" if str(r.conflict_flag).startswith("maintenance_front") else ""))

    p = DATA / "margin_advisories.csv"
    if p.exists():
        a = pd.read_csv(p)
        a = a[a.rate_type.isin(["Spec", "Maintenance"])]
        tl = a.tier.fillna("").str.replace(" ", "", regex=False).str.lower()
        front = a[(tl == "") | tl.isin(["mnth1", "mnths1", "mth1", "mths1", "month1", "allmonths", "all"]) |
                  tl.str.startswith("period1(")]
        for (prod, d), g in front.groupby(["product", "effective_date"]):
            r = g.iloc[0]
            out.append(dict(product=prod, effective_date=d, maintenance=r.new_maintenance,
                            initial=r.new_initial, initial_reliable=True,
                            notice_date=r.notice_date, rate_label=f"Spec {r.tier or ''}".strip(),
                            route="advisory", source=r.source, conflict_note=""))

    p = DATA / "margin_history_wayback_snapshots.csv"
    if p.exists():
        s = pd.read_csv(p)
        s = s[s.direction.isin(["increase", "decrease"])]
        for _, r in s.iterrows():
            out.append(dict(product=r["product"], effective_date=r.effective_date,
                            maintenance=r.maintenance, initial="", initial_reliable=False,
                            notice_date="", rate_label="front-tier snapshot",
                            route="snapshot-wayback", source=f"{r.source_file}@{r.capture_ts}",
                            conflict_note=""))

    h = pd.read_csv(DATA / "margin_history.csv")
    h = h[h.direction.isin(["increase", "decrease"])]
    for _, r in h.iterrows():
        out.append(dict(product=r["product"], effective_date=r.effective_date,
                        maintenance=r.maintenance_margin, initial="", initial_reliable=False,
                        notice_date="", rate_label="front-tier snapshot",
                        route="snapshot-live", source=r.source_file, conflict_note=""))
    return out


def _snapshot_levels():
    """per product: (sorted [(date, maintenance)], covered intervals) from
    daily-snapshot events, for level-at-date lookup that never extrapolates
    across coverage gaps"""
    lv = collections.defaultdict(list)
    p = DATA / "margin_history_wayback_snapshots.csv"
    if p.exists():
        s = pd.read_csv(p)
        for _, r in s.iterrows():
            lv[r["product"]].append((r.effective_date, float(r.maintenance)))
    h = pd.read_csv(DATA / "margin_history.csv")
    for _, r in h.iterrows():
        lv[r["product"]].append((r.effective_date, float(r.maintenance_margin)))
    for k in lv:
        lv[k].sort()
    cov = collections.defaultdict(list)
    src_ = pd.read_csv(DATA / "margin_wayback_sources.csv")
    for _, r in src_.iterrows():
        if r.fmt == "NEW" and isinstance(r.first_row_date, str) and r.first_row_date:
            cov[r["product"]].append((r.first_row_date, r.last_row_date))
    for prod in pd.read_csv(DATA / "margin_history.csv")["product"].unique():
        cov[prod].append((SNAPSHOT_LIVE_START, SNAPSHOT_LIVE_END))
    for k in cov:
        cov[k] = merge_intervals(cov[k], tol_days=7)
    return lv, cov


def _levels_window(lvcov, product, date):
    """set of maintenance levels in force from `date` through date+5 calendar days
    (absorbs the effective-after-close -> next-settlement offset); None if the
    date is not inside actual snapshot coverage"""
    lv, cov = lvcov
    if not any(s <= date <= e for s, e in cov.get(product, [])):
        return None
    seq = lv.get(product, [])
    if not seq or date < seq[0][0] or date > seq[-1][0]:
        return None
    from datetime import date as _d, timedelta as _td
    hi = (_d.fromisoformat(date) + _td(days=5)).isoformat()
    vals = set()
    cur = None
    for d, m in seq:
        if d <= date:
            cur = m
        elif d <= hi:
            vals.add(m)
        else:
            break
    if cur is not None:
        vals.add(cur)
    return vals or None


def dedupe(rows):
    """collapse per (product, date); agreeing routes merge; disagreements are
    resolved by cross-route snapshot confirmation where possible, else flagged."""
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["product"], r["effective_date"])].append(r)
    lv = _snapshot_levels()
    merged, conflicts = [], []
    route_rank = {"advisory": 0, "wayback-history": 1, "snapshot-wayback": 2, "snapshot-live": 3}
    for (prod, d), grp in sorted(by.items()):
        vals = {round(float(g["maintenance"]), 2) for g in grp}
        grp.sort(key=lambda g: route_rank[g["route"]])
        base = dict(grp[0])
        resolution = ""
        snaps = _levels_window(lv, prod, d)
        if len(vals) > 1:
            match = [g for g in grp if snaps is not None and float(g["maintenance"]) in snaps]
            if match:
                base = dict(sorted(match, key=lambda g: route_rank[g["route"]])[0])
                resolution = "snapshot-confirmed"
            else:
                resolution = "UNRESOLVED"
            conflicts.append(dict(product=prod, effective_date=d, resolution=resolution,
                                  detail="; ".join(f"{g['route']}={g['maintenance']} ({g['source']}|{g['rate_label']})" for g in grp)))
        elif snaps is not None and base["route"] not in ("snapshot-wayback", "snapshot-live") \
                and float(base["maintenance"]) not in snaps:
            # demonstrably not the front-month rate (e.g. a crop/back-tier leg
            # rendered without its label): exclude from the front-month union, log
            conflicts.append(dict(product=prod, effective_date=d, resolution="EXCLUDED-non-front-leg",
                                  detail=f"{base['route']}={base['maintenance']} ({base['source']}|{base['rate_label']}) vs snapshot levels {sorted(snaps)}"))
            continue
        base["routes"] = "+".join(sorted({g["route"] for g in grp}, key=lambda x: route_rank[x]))
        nd = [g["notice_date"] for g in grp if g["notice_date"]]
        base["notice_date"] = nd[0] if nd else ""
        base["maintenance_conflict_across_routes"] = resolution in ("UNRESOLVED", "SNAPSHOT-MISMATCH")
        base["conflict_resolution"] = resolution
        merged.append(base)
    return merged, conflicts


def coverage_windows():
    """[start, end] intervals per product per route"""
    win = collections.defaultdict(list)

    src = pd.read_csv(DATA / "margin_wayback_sources.csv")
    for _, r in src.iterrows():
        if r.n_rows == 0 or not isinstance(r.first_row_date, str) or not r.first_row_date:
            continue
        f = r.source_file
        start = r.first_row_date
        end = r.last_row_date
        if "prior_to_2009" in f:
            end = "2008-12-31"
        elif "2009_to_2013" in f:
            start, end = max(start, "2009-01-01"), "2013-12-31"
        elif "_to_present" in f or "-to-present" in f or "to-2023" in f or "to-2024" in f:
            we = r.window_end if isinstance(r.window_end, str) and r.window_end else end
            end = max(end, we)
        if r.fmt in ("OLD-A", "OLD-B"):
            win[(r["product"], "wayback-history")].append((start, end))
        elif r.fmt == "NEW":
            win[(r["product"], "snapshot-wayback")].append((start, end))

    # advisory coverage windows only for years whose PB-advisory parse is ~complete;
    # a partially-parsed year cannot certify "no change happened", so it is rows-only.
    p = DATA / "margin_advisories_completeness.csv"
    pa = pd.read_csv(DATA / "margin_advisories.csv") if (DATA / "margin_advisories.csv").exists() else None
    if p.exists() and pa is not None and len(pa):
        comp = pd.read_csv(p)
        full_years = sorted(int(y) for y in comp[comp.parse_rate >= 0.95].year
                            if str(y).isdigit() and comp[comp.year == y].pb_advisories.iloc[0] >= 50)
        products = set(pa["product"].unique()) | {"ES"}
        for y in full_years:
            for prod in products:
                win[(prod, "advisory")].append((f"{y}-01-01", f"{y}-12-31"))

    h = pd.read_csv(DATA / "margin_history.csv")
    for prod in h["product"].unique():
        win[(prod, "snapshot-live")].append((SNAPSHOT_LIVE_START, SNAPSHOT_LIVE_END))
    return win


def merge_intervals(iv, tol_days=45):
    """merge; a change-level series stays valid between sparse changes, so allow
    small joins only via tol for abutting windows (e.g., prior_to_2009 -> 2008 file)"""
    iv = sorted(iv)
    out = []
    for s, e in iv:
        if out and s <= (date.fromisoformat(out[-1][1]) + timedelta(days=tol_days)).isoformat():
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def main():
    rows = load_rows()
    merged, conflicts = dedupe(rows)
    cols = ["product", "effective_date", "maintenance", "initial", "initial_reliable",
            "notice_date", "rate_label", "routes", "source",
            "maintenance_conflict_across_routes", "conflict_resolution"]
    with open(DATA / "margin_history_stitched.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged)
    with open(DATA / "margin_history_stitched_conflicts.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["product", "effective_date", "resolution", "detail"])
        w.writeheader()
        w.writerows(conflicts)
    print(f"stitched union rows: {len(merged)} | cross-route maintenance conflicts: {len(conflicts)}")

    win = coverage_windows()
    products = sorted({p for p, _ in win})
    md = ["| product | recoverable segments | gaps | rows in union |", "|---|---|---|---|"]
    dfm = pd.DataFrame(merged)
    print("\n=== per-product coverage (merged across routes; tol 45d) ===")
    for prod in products:
        allw = []
        for (pp, route), ivs in win.items():
            if pp == prod:
                allw += ivs
        seg = merge_intervals(allw)
        segs = ", ".join(f"{s}..{e}" for s, e in seg)
        gaps = []
        for i in range(1, len(seg)):
            gaps.append(f"{seg[i-1][1]}..{seg[i][0]}")
        n = (dfm["product"] == prod).sum()
        print(f"{prod}: {segs}")
        if gaps:
            print(f"    GAPS: {'; '.join(gaps)}")
        md.append(f"| {prod} | {segs} | {'; '.join(gaps) if gaps else '—'} | {n} |")
    print("\n=== route detail ===")
    md2 = ["| product | route | windows |", "|---|---|---|"]
    for (prod, route), ivs in sorted(win.items()):
        wtxt = ", ".join(f"{s}..{e}" for s, e in merge_intervals(ivs))
        print(f"{prod:12s} {route:16s} {wtxt}")
        md2.append(f"| {prod} | {route} | {wtxt} |")
    outp = Path("/private/tmp/claude-501/-Users-nav-Desktop-margin-event-study/f85c660f-ac16-4ed2-9659-3eebf5c848a1/scratchpad/coverage_tables.md")
    outp.write_text("\n".join(md) + "\n\n" + "\n".join(md2) + "\n")
    print(f"\nwrote {outp}")


if __name__ == "__main__":
    main()
