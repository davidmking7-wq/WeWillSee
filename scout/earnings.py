"""Best-effort next-earnings-date lookup for scan candidates.

A quarterly report inside the 42-day window is a binary event that can wreck
a good pattern overnight — the scan flags it and auto-downgrades the grade
one notch; the research phase then confirms rather than discovers.

Strictly best-effort: sources are free/unofficial and any of them may be
blocked or flaky in a given environment. Failure NEVER breaks the scan —
symbols just come back with no date and the skill's web-research phase
covers them (as it always did). Results are cached a few days.

Sources for the NEXT date:
1. Yahoo Finance quoteSummary calendarEvents (plain requests with the
   fc.yahoo.com cookie + getcrumb handshake) — one session for all symbols.
2. yfinance's Ticker.calendar, per symbol (works on most home networks).
3. NASDAQ's public API with a browser User-Agent, per symbol.

Historical/most-recent dates come from SEC EDGAR (8-K Item 2.02 filing
dates — the day companies announce results), kept in
scout/earnings_history.json and refreshed per symbol when stale. The
real-dates lab (BACKTEST-REPORT.md) found freshly-reported stocks are the
engine's weakest cohort, so the scan needs "did it JUST report?".
"""
import json
import time
from datetime import date, datetime, timedelta

import requests

from . import config

CACHE_PATH = config.SCOUT_DIR / "earnings_cache.json"
HISTORY_PATH = config.SCOUT_DIR / "earnings_history.json"
CACHE_DAYS = 3
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_SEC_HEADERS = {"User-Agent": "stock-scout research (contact: repo owner)"}


def _parse_date(v) -> str | None:
    """Normalize assorted date shapes to 'YYYY-MM-DD' (future dates only)."""
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    if hasattr(v, "date"):
        v = v.date()
    if isinstance(v, date):
        d = v
    else:
        s = str(v).strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y", "%d-%b-%Y"):
            try:
                d = datetime.strptime(s[:20].split("T")[0], fmt).date()
                break
            except ValueError:
                continue
        else:
            return None
    return str(d) if d >= date.today() else None


def _yahoo_batch(symbols: list[str]) -> dict[str, str | None]:
    """All symbols through one authenticated Yahoo session. Raises if the
    cookie/crumb handshake fails; per-symbol errors just yield None."""
    s = requests.Session()
    s.headers["User-Agent"] = _UA
    try:
        s.get("https://fc.yahoo.com", timeout=10)   # sets the auth cookie;
    except requests.RequestException:               # its error page is fine
        pass
    crumb = s.get("https://query2.finance.yahoo.com/v1/test/getcrumb",
                  timeout=15).text.strip()
    if not crumb or "<" in crumb:
        raise RuntimeError("no yahoo crumb")
    out = {}
    for sym in symbols:
        try:
            r = s.get("https://query2.finance.yahoo.com/v10/finance/"
                      f"quoteSummary/{sym}",
                      params={"modules": "calendarEvents", "crumb": crumb},
                      timeout=15)
            r.raise_for_status()
            dates = (r.json()["quoteSummary"]["result"][0]
                     ["calendarEvents"]["earnings"].get("earningsDate") or [])
            # earningsDate may hold a 1-2 entry range; earliest = next expected
            out[sym] = _parse_date(min(d["fmt"] for d in dates)) if dates else None
        except Exception:
            out[sym] = None
        time.sleep(0.15)
    return out


def _from_yfinance(sym: str) -> str | None:
    import yfinance as yf
    cal = yf.Ticker(sym).calendar
    if isinstance(cal, dict):
        return _parse_date(cal.get("Earnings Date"))
    return None


def _from_nasdaq(sym: str) -> str | None:
    r = requests.get(f"https://api.nasdaq.com/api/analyst/{sym}/earnings-date",
                     headers={"User-Agent": _UA, "Accept": "application/json"},
                     timeout=10)
    r.raise_for_status()
    msg = ((r.json().get("data") or {}).get("announcement") or "")
    # e.g. "Earnings announcement for AAPL: Oct 30, 2025"
    if ":" in msg:
        return _parse_date(msg.rsplit(":", 1)[1])
    return None


_FALLBACKS = (("yfinance", _from_yfinance), ("nasdaq", _from_nasdaq))


def _edgar_dates(sym: str, cik: int) -> list[str] | None:
    """All 8-K Item 2.02 filing dates for one company from EDGAR's recent
    block (~last 1000 filings — plenty to refresh the newest quarters)."""
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json",
                     headers=_SEC_HEADERS, timeout=20)
    r.raise_for_status()
    rec = r.json()["filings"]["recent"]
    out = [rec["filingDate"][i] for i in range(len(rec["form"]))
           if rec["form"][i] in ("8-K", "8-K/A")
           and rec["items"][i] and "2.02" in rec["items"][i].split(",")]
    time.sleep(0.15)
    return sorted(set(out))


def recent_earnings(symbols: list[str], asof: str,
                    within_days: int = 15) -> dict[str, str | None]:
    """{sym: last earnings ISO date within `within_days` calendar days
    (~10 trading days) before `asof`, else None}. Backed by the EDGAR
    history file; symbols whose stored history looks stale (last date
    >120d before asof) are refreshed live. Never raises."""
    try:
        hist = json.loads(HISTORY_PATH.read_text(encoding="utf-8")) \
            if HISTORY_PATH.exists() else {}
    except (json.JSONDecodeError, OSError):
        hist = {}
    asof_d = date.fromisoformat(asof[:10])
    stale = [s for s in symbols
             if not hist.get(s)
             or date.fromisoformat(max(hist[s])) < asof_d - timedelta(days=120)]
    if stale:
        try:
            r = requests.get("https://www.sec.gov/files/company_tickers.json",
                             headers=_SEC_HEADERS, timeout=20)
            r.raise_for_status()
            ciks = {v["ticker"]: v["cik_str"] for v in r.json().values()}
            for s in stale:
                cik = ciks.get(s.replace(".", "-"))
                if not cik:
                    continue
                try:
                    ds = _edgar_dates(s, cik)
                    hist[s] = sorted(set(hist.get(s, [])) | set(ds))
                except Exception:
                    continue
            HISTORY_PATH.write_text(json.dumps(hist, indent=0),
                                    encoding="utf-8")
        except Exception:
            pass
    lo = str(asof_d - timedelta(days=within_days))
    out = {}
    for s in symbols:
        past = [d for d in hist.get(s, []) if lo <= d <= asof]
        out[s] = max(past) if past else None
    return out


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def next_earnings(symbols: list[str]) -> dict[str, str | None]:
    """{symbol: 'YYYY-MM-DD' or None}. Never raises."""
    cache = _load_cache()
    today = str(date.today())
    out = {}
    todo = []
    for sym in symbols:
        hit = cache.get(sym)
        if hit and (date.today() - date.fromisoformat(hit["fetched"])).days <= CACHE_DAYS:
            out[sym] = hit["date"]
        else:
            todo.append(sym)

    if todo:
        try:
            out.update(_yahoo_batch(todo))
        except Exception:
            pass
        fails = {name: 0 for name, _ in _FALLBACKS}  # 3 straight errors = down
        for sym in todo:
            if out.get(sym):
                continue
            for name, fn in _FALLBACKS:
                if fails[name] >= 3:
                    continue
                try:
                    found = fn(sym)
                    fails[name] = 0
                    if found:
                        out[sym] = found
                        break
                except Exception:
                    fails[name] += 1
            out.setdefault(sym, None)
            time.sleep(0.15)
        for sym in todo:
            cache[sym] = {"date": out[sym], "fetched": today}
        try:
            CACHE_PATH.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        except OSError:
            pass
    return out
