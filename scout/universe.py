"""Liquid US universe: current S&P 500 constituents, cached to CSV.

Survivorship caveat: using TODAY'S constituents for historical calibration
overstates hit rates a little. calibrate.py therefore reports *lift over the
same universe's base rate*, which mostly cancels the bias, rather than leaning
on raw probabilities alone.
"""
import csv
import io
import time
from datetime import datetime

import requests

from . import config


def load(refresh: bool = False) -> list[dict]:
    """Return [{'symbol','name','sector'}, ...]; refresh cache if stale."""
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
        return list(csv.DictReader(f))


def _refresh() -> None:
    r = requests.get(config.UNIVERSE_URL, timeout=30)
    r.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r.text)))
    if len(rows) < 400:
        raise ValueError(f"constituents file looks wrong ({len(rows)} rows)")
    cols = {k.lower().strip(): k for k in rows[0]}
    sym = cols.get("symbol")
    name = cols.get("security") or cols.get("name")
    sector = cols.get("gics sector") or cols.get("sector")
    if not sym:
        raise ValueError(f"no symbol column in {list(rows[0])}")
    out = [{"symbol": row[sym].strip(),
            "name": (row.get(name) or "").strip() if name else "",
            "sector": (row.get(sector) or "").strip() if sector else ""}
           for row in rows if row.get(sym, "").strip()]
    with open(config.UNIVERSE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "name", "sector"])
        w.writeheader()
        w.writerows(out)
    print(f"universe refreshed: {len(out)} symbols")
