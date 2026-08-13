"""Insider-buying lab (registry H1/H1b). Research harness, not pipeline.

For every historical top-3 pick (v5, S&P 1500 scans), fetch the REAL SEC
Form 4 filings of the issuer in the 45 calendar days before entry and
classify: opportunistic open-market BUYS (transaction code P, >= $10k,
officer/director, non-10b5-1-plan) and non-plan SELLS (code S). Then
compare pick outcomes by cohort:
  any_buy / cluster_buy (>=2 distinct buyers) / heavy_sell (>=3 distinct
  sellers, no buys) / quiet.

Point-in-time hygiene: filings are matched on their EDGAR filingDate
(public knowledge by entry). XMLs cached to scout/form4_cache/ so reruns
are cheap. SEC rate limit respected (~6 req/s).

Usage: python -m scout.insider_lab   (first run fetches; takes ~10 min)
"""
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import backtest, config, signals

H = config.HORIZON_TDAYS
CACHE_DIR = config.SCOUT_DIR / "form4_cache"
_HEADERS = {"User-Agent": "research scout@example.com"}
SLEEP = 0.15


def _get(url, is_json=True):
    for attempt in range(3):
        r = requests.get(url, headers=_HEADERS, timeout=30)
        if r.status_code in (403, 429) and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        time.sleep(SLEEP)
        return r.json() if is_json else r.text


def form4_index(sym, cik):
    """[(filingDate, accession, primaryDocument)] for all Form 4s, all
    pages. Disk-cached so interrupted runs resume instead of refetching."""
    cached = CACHE_DIR / f"index_{sym.replace('.', '-')}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    out = []
    j = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    blocks = [j["filings"]["recent"]]
    extra = j["filings"].get("files", [])
    for f in extra:
        try:
            blocks.append(_get("https://data.sec.gov/submissions/" + f["name"]))
        except Exception:
            continue
    for b in blocks:
        for i in range(len(b["form"])):
            if b["form"][i] in ("4", "4/A"):
                out.append((b["filingDate"][i], b["accessionNumber"][i],
                            b["primaryDocument"][i]))
    cached.write_text(json.dumps(out))
    return out


def fetch_form4(cik, accession, primary):
    """Parse one Form 4 XML -> list of (owner, code, dollars, is_off_dir,
    plan_flag). Cached to disk."""
    key = accession.replace("-", "")
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    # primaryDocument often points at the XSL-RENDERED view
    # ("xslF345X06/form4.xml"); the raw XML is the bare filename
    primary = primary.split("/")[-1]
    url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/{key}/{primary}")
    try:
        xml = _get(url, is_json=False)
    except Exception:
        cached.write_text("[]")
        return []
    owner = ";".join(re.findall(r"<rptOwnerCik>(\d+)</rptOwnerCik>", xml)) or "?"
    off_dir = bool(re.search(r"<isOfficer>(1|true)</isOfficer>", xml)
                   or re.search(r"<isDirector>(1|true)</isDirector>", xml))
    plan = bool(re.search(r"<aff10b5One>(1|true)</aff10b5One>", xml))
    rows = []
    for m in re.finditer(r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>",
                         xml, re.S):
        t = m.group(1)
        code = re.search(r"<transactionCode>(\w)</transactionCode>", t)
        sh = re.search(r"<transactionShares>.*?<value>([\d.]+)</value>", t, re.S)
        px = re.search(r"<transactionPricePerShare>.*?<value>([\d.]+)</value>", t, re.S)
        if not code:
            continue
        dollars = (float(sh.group(1)) * float(px.group(1))) if sh and px else 0.0
        rows.append([owner, code.group(1), dollars, off_dir, plan])
    cached.write_text(json.dumps(rows))
    return rows


def main() -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    bars = backtest.load_bars(mode="sp1500")
    c = bars["close"]
    idx = c.index
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    positions = backtest.positions_for(idx, None, None, 21)

    picks = []
    for pos in positions:
        snap = signals.composite_at(frames, idx[pos]).drop(index=["SPY"],
                                                           errors="ignore")
        if len(snap) < 50:
            continue
        basis = c.iloc[pos]
        for sym in list(snap.index[:3]):
            if sym not in c.columns or pd.isna(basis.get(sym)):
                continue
            fwd = (c.iloc[pos + 1: pos + 1 + H][sym] / basis[sym]).dropna()
            if len(fwd) < H:
                continue
            r = fwd.values
            picks.append({"sym": sym, "pos": pos,
                          "date": str(idx[pos].date()),
                          "hit": bool((r >= 1.05).any()),
                          "end": float(r[-1] - 1)})
    syms = sorted({p["sym"] for p in picks})
    print(f"{len(picks)} pick-windows across {len(syms)} unique symbols")

    ciks = {v["ticker"]: v["cik_str"]
            for v in _get("https://www.sec.gov/files/company_tickers.json").values()}
    f4 = {}
    for i, sym in enumerate(syms):
        cik = ciks.get(sym.replace(".", "-"))
        if not cik:
            continue
        try:
            f4[sym] = (cik, form4_index(sym, cik))
        except Exception:
            continue
        if (i + 1) % 40 == 0:
            print(f"  form-4 indexes: {i + 1}/{len(syms)}")

    n_xml = 0
    for p in picks:
        got = f4.get(p["sym"])
        p["buyers"], p["sellers"] = set(), set()
        if not got:
            p["cov"] = False
            continue
        cik, filings = got
        p["cov"] = True
        lo = str((idx[p["pos"]] - pd.Timedelta(days=45)).date())
        hi = p["date"]
        for fdate, acc, prim in filings:
            if not (lo <= fdate <= hi):
                continue
            n_xml += 1
            for owner, code, dollars, off_dir, plan in fetch_form4(cik, acc, prim):
                if code == "P" and dollars >= 10000 and off_dir and not plan:
                    p["buyers"].add(owner)
                elif code == "S" and dollars >= 10000 and not plan:
                    p["sellers"].add(owner)
    print(f"parsed {n_xml} Form 4 filings "
          f"({sum(1 for p in picks if p['cov'])} covered picks)")

    def agg(rows, label):
        if not rows:
            return f"{label:<28} n=0"
        hits = np.mean([r["hit"] for r in rows])
        return (f"{label:<28} n={len(rows):>4}  hit {100*hits:5.1f}%  "
                f"avg end {100*np.mean([r['end'] for r in rows]):+6.2f}%  "
                f"tail<-10% {100*np.mean([r['end'] < -0.10 for r in rows]):4.1f}%")

    halves = (("TRAIN <=2021", lambda p: p["date"] <= "2021-12-31"),
              ("HOLDOUT 2022+", lambda p: p["date"] > "2021-12-31"),
              ("ALL", lambda p: True))
    for label, sel in halves:
        sub = [p for p in picks if p["cov"] and sel(p)]
        print(f"\n[{label}]")
        print(" " + agg([p for p in sub if len(p['buyers']) >= 1], "any opportunistic buy"))
        print(" " + agg([p for p in sub if len(p['buyers']) >= 2], "cluster buy (2+ buyers)"))
        print(" " + agg([p for p in sub if len(p['sellers']) >= 3
                         and not p['buyers']], "heavy sell (3+, no buys)"))
        print(" " + agg([p for p in sub if not p['buyers']
                         and len(p['sellers']) < 3], "quiet"))


if __name__ == "__main__":
    main()
