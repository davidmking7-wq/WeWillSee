"""Liquid US universe: the S&P 1500 — large caps (500) plus the MidCap 400
and SmallCap 600, where under-the-radar candidates live. Cached to CSV with
a `segment` column (large/mid/small); refreshed from Wikipedia when stale.

Survivorship caveat: TODAY'S constituents applied historically overstate
hit rates (worst for small caps, whose failures leave the index faster).
The point-in-time S&P 500 backtest (scout/pit.py + backtest --universe
pit500) quantifies that bias for the large-cap segment; mid/small have no
free point-in-time source — rely on lift over the same-universe base rate.
"""
import csv
import io
import time
from datetime import datetime

import requests

from . import config

WIKI = {
    "large": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "mid": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "small": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}
EXPECTED = {"large": 500, "mid": 400, "small": 600}
_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"}
FIELDS = ["symbol", "name", "sector", "segment"]


def load(refresh: bool = False) -> list[dict]:
    """Return [{'symbol','name','sector','segment'}, ...]; refresh if stale.
    Old caches without a segment column are treated as all-large."""
    path = config.UNIVERSE_CSV
    stale = (not path.exists() or
             (time.time() - path.stat().st_mtime) > config.UNIVERSE_STALE_DAYS * 86400)
    if refresh or stale:
        try:
            _refresh()
        except Exception as e:  # keep working off the cache if the fetch fails
            if not path.exists():
                raise
            print(f"universe refresh failed ({e}); using cached list "
                  f"from {datetime.fromtimestamp(path.stat().st_mtime):%Y-%m-%d}")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row.setdefault("segment", "large")
        if not row["segment"]:
            row["segment"] = "large"
    return rows


def _constituent_table(html: str):
    """Pick the constituents table by its columns, not position."""
    import pandas as pd
    for t in pd.read_html(io.StringIO(html)):
        cols = [str(c) for c in t.columns]
        if {"Symbol", "Security", "GICS Sector"} <= set(cols):
            return t
    raise ValueError("constituents table not found on page")


def _refresh() -> None:
    out, seen = [], set()
    with requests.Session() as s:
        s.headers.update(_HEADERS)
        for segment, url in WIKI.items():
            r = s.get(url, timeout=30)
            r.raise_for_status()
            df = _constituent_table(r.text)
            expected = EXPECTED[segment]
            if not expected * 0.9 <= len(df) <= expected * 1.1:
                raise ValueError(f"{segment}: got {len(df)} rows, "
                                 f"expected ~{expected}")
            for _, row in df.iterrows():
                sym = str(row["Symbol"]).strip()
                if not sym or sym in seen:      # dupes keep the larger segment
                    continue
                seen.add(sym)
                out.append({"symbol": sym,
                            "name": str(row["Security"]).strip(),
                            "sector": str(row["GICS Sector"]).strip(),
                            "segment": segment})
    if len(out) < 1200:
        raise ValueError(f"combined universe looks wrong ({len(out)} rows)")
    with open(config.UNIVERSE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"universe refreshed: {len(out)} symbols "
          f"({sum(1 for r in out if r['segment'] == 'large')} large / "
          f"{sum(1 for r in out if r['segment'] == 'mid')} mid / "
          f"{sum(1 for r in out if r['segment'] == 'small')} small)")
