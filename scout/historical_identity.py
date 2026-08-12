"""Historical PIT ticker <-> CIK identity map (handoff section 8.2).

THE HOLE, MEASURED FIRST
------------------------
SEC's `company_tickers.json` maps CURRENT tickers only. Of the 742 point-in-time
S&P 500 members 2016-2026, **141 (19%) do not resolve through it** — acquired
(AET, CELG, ATVI...), renamed (BK -> BNY), or delisted. Restricting any filing-
based study to today's map silently deletes one PIT member in five, and they are
not a random fifth: they are disproportionately the acquired, i.e. exactly the
outcomes several vNext mechanisms are about. This is survivorship through
identifier resolution, and the handoff forbids it. Our own `sec_bulk` facts
store inherits the hole, because its ticker column was joined from the current
map at build time (H31i measured the resulting coverage gradient: 74% of index
members in 2017 rising to 98% in 2026).

THE HISTORICAL SOURCE
---------------------
Each quarterly DERA financial-statement dataset carries `sub.txt`, one row per
submission, including `instance` — the XBRL instance filename, e.g.
`aet-20171231.xml`. Its prefix is the ticker THE COMPANY ITSELF USED AT FILING
TIME. Harvesting (prefix -> cik, name, first_filed, last_filed) across all
quarters yields a point-in-time ticker map with no survivorship: a company that
filed while it existed is in it forever.

The prefix is the filer's choice, not a guaranteed ticker (a few use e.g.
`brka`, digits, or the company name). So every resolution is TAGGED with its
source and the ambiguous cases are listed, not guessed:
  source = "current"    company_tickers.json, still listed today
  source = "instance"   unique historical prefix match
  source = "conflict"   prefix maps to >1 CIK — listed with all candidates
  source = "UNRESOLVED" nothing matched — listed explicitly, per the handoff

Run:
  python -m scout.historical_identity --build     # ~42 quarterly sub.txt passes
  python -m scout.historical_identity --resolve   # writes identity_map.json
  python -m scout.historical_identity --selftest
"""
from __future__ import annotations

import argparse
import io
import json
import zipfile

import pandas as pd
import requests

from . import config, pit, sec_bulk

UA = {"User-Agent": "WeWillSee research davidmking7@gmail.com"}
BASE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
CACHE = config.SCOUT_DIR / "cache_secbulk"
INSTANCE_MAP = CACHE / "instance_map.pkl"
IDENTITY_JSON = config.SCOUT_DIR / "identity_map.json"

START_Y, END_Y = 2016, 2026


def _quarters():
    for y in range(START_Y, END_Y + 1):
        for q in (1, 2, 3, 4):
            yield y, q


def build(verbose: bool = True) -> pd.DataFrame:
    """Harvest (instance-prefix, cik, name, filed-range) from every sub.txt.

    Downloads each ~124 MB quarterly zip, reads ONLY sub.txt, keeps four
    columns, and discards the zip — nothing large lands on disk."""
    rows = []
    for y, q in _quarters():
        url = f"{BASE}/{y}q{q}.zip"
        try:
            r = requests.get(url, headers=UA, timeout=300)
            if r.status_code != 200:
                if verbose:
                    print(f"  {y}q{q}: HTTP {r.status_code} (future quarter?) — skip")
                continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open("sub.txt") as f:
                    sub = pd.read_csv(f, sep="\t", dtype=str,
                                      usecols=["cik", "name", "instance", "filed"])
        except Exception as e:
            if verbose:
                print(f"  {y}q{q}: {type(e).__name__} — skip")
            continue
        sub = sub.dropna(subset=["instance"])
        # `aet-20171231.xml` -> `aet`; tolerate `_htm.xml` and no-dash names
        pfx = (sub["instance"].str.lower()
               .str.replace(r"\.(xml|htm)$", "", regex=True)
               .str.split("-").str[0].str.strip())
        keep = pfx.str.fullmatch(r"[a-z]{1,6}")          # ticker-shaped only
        out = pd.DataFrame({"prefix": pfx[keep],
                            "cik": sub.loc[keep, "cik"].astype(int),
                            "name": sub.loc[keep, "name"],
                            "filed": sub.loc[keep, "filed"]})
        rows.append(out)
        if verbose:
            print(f"  {y}q{q}: {len(out)} ticker-shaped instances "
                  f"({len(sub) - keep.sum()} skipped)")
    df = pd.concat(rows, ignore_index=True)
    agg = (df.groupby(["prefix", "cik"])
             .agg(name=("name", "last"), n_filings=("filed", "size"),
                  first_filed=("filed", "min"), last_filed=("filed", "max"))
             .reset_index())
    agg.to_pickle(INSTANCE_MAP)
    if verbose:
        print(f"instance map: {len(agg)} (prefix, cik) pairs, "
              f"{agg['prefix'].nunique()} distinct prefixes -> {INSTANCE_MAP.name}")
    return agg


def resolve(verbose: bool = True) -> dict:
    """PIT union -> identity rows, every one tagged with its source."""
    union = pit.all_members_since("2016-01-04")
    cur = sec_bulk.ticker_map()
    cur_by_tkr = {}
    for _, r in cur.iterrows():
        cur_by_tkr.setdefault(r["ticker"].replace("-", "."), []).append(
            {"cik": int(r["cik"]), "name": r["name"]})

    inst = pd.read_pickle(INSTANCE_MAP) if INSTANCE_MAP.exists() else None
    inst_by_pfx: dict[str, list] = {}
    if inst is not None:
        for _, r in inst.iterrows():
            inst_by_pfx.setdefault(r["prefix"], []).append(r)

    out, unresolved, conflicts = [], [], []
    for t in union:
        row = {"ticker": t}
        cands = cur_by_tkr.get(t) or cur_by_tkr.get(t.replace(".", "-"))
        if cands:
            row |= {"cik": cands[0]["cik"], "name": cands[0]["name"],
                    "source": "current"}
            out.append(row)
            continue
        pfx = t.lower().replace(".", "")
        hits = inst_by_pfx.get(pfx, [])
        # a prefix used by several CIKs: prefer the one with the most filings,
        # but only when it dominates (>= 80%); otherwise it is a CONFLICT
        if len({h["cik"] for h in hits}) == 1:
            h = hits[0]
            row |= {"cik": int(h["cik"]), "name": h["name"], "source": "instance",
                    "first_filed": h["first_filed"], "last_filed": h["last_filed"],
                    "n_filings": int(h["n_filings"])}
            out.append(row)
        elif hits:
            tot = sum(h["n_filings"] for h in hits)
            best = max(hits, key=lambda h: h["n_filings"])
            if best["n_filings"] / tot >= 0.8:
                row |= {"cik": int(best["cik"]), "name": best["name"],
                        "source": "instance",
                        "note": f"dominant of {len(hits)} candidates "
                                f"({best['n_filings']}/{tot} filings)"}
                out.append(row)
            else:
                # two CIKs sharing a prefix with DISJOINT filing spans is a
                # rename/re-incorporation, not an ambiguity: both really were
                # this ticker, at different times. Downstream studies resolve
                # by the filing date they care about, so ship the spans.
                cands = sorted((dict(cik=int(h["cik"]), name=h["name"],
                                     n_filings=int(h["n_filings"]),
                                     first_filed=str(h["first_filed"]),
                                     last_filed=str(h["last_filed"]))
                                for h in hits), key=lambda c: c["first_filed"])
                spans_disjoint = all(cands[i]["last_filed"] <= cands[i + 1]["first_filed"]
                                     for i in range(len(cands) - 1))
                row |= {"source": "conflict_date_resolvable" if spans_disjoint
                        else "conflict", "candidates": cands}
                conflicts.append(row)
        else:
            row |= {"source": "UNRESOLVED"}
            unresolved.append(row)

    report = {
        "pit_union": len(union),
        "resolved_current": sum(1 for r in out if r["source"] == "current"),
        "resolved_instance": sum(1 for r in out if r["source"] == "instance"),
        "conflicts": len(conflicts),
        "unresolved": len(unresolved),
        "unresolved_tickers": [r["ticker"] for r in unresolved],
        "conflict_tickers": [r["ticker"] for r in conflicts],
        "rows": out + conflicts + unresolved,
    }
    IDENTITY_JSON.write_text(json.dumps(report, indent=1, default=str))
    if verbose:
        print(f"identity: {report['resolved_current']} current + "
              f"{report['resolved_instance']} instance / {len(union)} PIT union; "
              f"{report['conflicts']} conflicts, {report['unresolved']} unresolved")
        if unresolved:
            print("UNRESOLVED:", [r["ticker"] for r in unresolved])
    return report


def _selftest() -> int:
    """Known acquisitions must resolve via the instance map with the right CIK."""
    known = {"AET": 1122304, "CELG": 816284, "ATVI": 718877, "MON": 1110783}
    rep = json.loads(IDENTITY_JSON.read_text())
    by_tkr = {r["ticker"]: r for r in rep["rows"]}
    ok = True
    for t, cik in known.items():
        r = by_tkr.get(t, {})
        good = r.get("cik") == cik
        print(f"  {'PASS' if good else 'FAIL'}  {t} -> {r.get('cik')} "
              f"({r.get('source')}), expected {cik}")
        ok &= good
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.historical_identity")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.build:
        build()
    if args.resolve:
        resolve()
    if args.selftest:
        raise SystemExit(_selftest())


if __name__ == "__main__":
    main()
