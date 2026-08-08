"""Live insider-buying check for scan candidates (registry H1: promising,
unproven — 13 occurrences in ten years, 69% hit / +6.9% avg / zero tail
losses, too rare to trade mechanically but always worth SEEING).

At scan time, each pool candidate's recent SEC Form 4 filings (last 45
calendar days, the issuer's own EDGAR feed) are checked for opportunistic
open-market BUYS: transaction code P, officer or director, >= $10k, not a
pre-arranged 10b5-1 plan trade. Purely informational: shown in the scan's
signals text and the workbook's "Insider Buys" column; never reorders or
upgrades anything. Strictly best-effort — any failure returns quietly.
Filing XMLs are cached (immutable) in scout/form4_cache/.
"""
import json
import re
import time
from datetime import date, timedelta

import requests

from . import config

CACHE_DIR = config.SCOUT_DIR / "form4_cache"
_HEADERS = {"User-Agent": "research scout@example.com"}
SLEEP = 0.15


def _get(url, is_json=True):
    for attempt in range(3):
        r = requests.get(url, headers=_HEADERS, timeout=20)
        if r.status_code in (403, 429) and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        time.sleep(SLEEP)
        return r.json() if is_json else r.text


def _parse_form4(cik, accession, primary):
    key = accession.replace("-", "")
    cached = CACHE_DIR / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    primary = primary.split("/")[-1]     # strip the XSL-rendered prefix
    try:
        xml = _get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{key}/"
                   f"{primary}", is_json=False)
    except Exception:
        return []
    owner = ";".join(re.findall(r"<rptOwnerCik>(\d+)</rptOwnerCik>", xml)) or "?"
    off_dir = bool(re.search(r"<isOfficer>(1|true)</isOfficer>", xml)
                   or re.search(r"<isDirector>(1|true)</isDirector>", xml))
    plan = bool(re.search(r"<aff10b5One>(1|true)</aff10b5One>", xml))
    rows = []
    for m in re.finditer(r"<nonDerivativeTransaction>(.*?)"
                         r"</nonDerivativeTransaction>", xml, re.S):
        t = m.group(1)
        code = re.search(r"<transactionCode>(\w)</transactionCode>", t)
        sh = re.search(r"<transactionShares>.*?<value>([\d.]+)</value>", t, re.S)
        px = re.search(r"<transactionPricePerShare>.*?<value>([\d.]+)</value>",
                       t, re.S)
        if not code:
            continue
        dollars = (float(sh.group(1)) * float(px.group(1))) if sh and px else 0.0
        rows.append([owner, code.group(1), dollars, off_dir, plan])
    cached.write_text(json.dumps(rows))
    return rows


def recent_buys(symbols: list[str], asof: str,
                lookback_days: int = 45) -> dict[str, dict]:
    """{sym: {"buyers": n_distinct, "dollars": total}} for qualifying
    opportunistic buys in the lookback. Never raises; {} on total failure."""
    out = {}
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        ciks = {v["ticker"]: v["cik_str"]
                for v in _get("https://www.sec.gov/files/"
                              "company_tickers.json").values()}
    except Exception:
        return out
    lo = str(date.fromisoformat(asof[:10]) - timedelta(days=lookback_days))
    for sym in symbols:
        cik = ciks.get(sym.replace(".", "-"))
        if not cik:
            continue
        try:
            j = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
            rec = j["filings"]["recent"]
        except Exception:
            continue
        buyers, dollars = set(), 0.0
        for i in range(len(rec["form"])):
            if rec["form"][i] not in ("4", "4/A"):
                continue
            fdate = rec["filingDate"][i]
            if not (lo <= fdate <= asof):
                continue
            for owner, code, dol, off_dir, plan in _parse_form4(
                    cik, rec["accessionNumber"][i], rec["primaryDocument"][i]):
                if code == "P" and dol >= 10000 and off_dir and not plan:
                    buyers.add(owner)
                    dollars += dol
        if buyers:
            out[sym] = {"buyers": len(buyers), "dollars": round(dollars)}
    return out
