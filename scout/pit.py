"""Point-in-time S&P 500 membership (fja05680/sp500, MIT license):
snapshot rows of the ACTUAL constituents on each change date, 1996-present.
Used by the backtest (--universe pit500) so every historical entry date
competes among the stocks that were really in the index THAT day —
including later-delisted ones (Alpaca still serves their bars through
their final print; verified incl. SIVB/FRC).

Cached to scout/sp500_pit.csv (committed). The upstream file is refreshed
by its author every 1-3 months; refresh() pulls the latest.
"""
import csv
import io
from bisect import bisect_right
from datetime import date
from urllib.parse import quote

import requests

from . import config

PIT_CSV = config.SCOUT_DIR / "sp500_pit.csv"
RAW_URL = ("https://raw.githubusercontent.com/fja05680/sp500/master/"
           + quote("S&P 500 Historical Components & Changes (Updated).csv"))

_snapshots: dict[date, frozenset] | None = None
_dates: list[date] = []


def refresh() -> None:
    r = requests.get(RAW_URL, timeout=60)
    r.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r.text)))
    if len(rows) < 2000 or "tickers" not in rows[0]:
        raise ValueError("point-in-time file looks wrong")
    PIT_CSV.write_text(r.text, encoding="utf-8")
    global _snapshots
    _snapshots = None
    print(f"point-in-time membership refreshed: {len(rows)} snapshots, "
          f"last {rows[-1]['date']}")


def _load() -> None:
    global _snapshots, _dates
    if _snapshots is not None:
        return
    if not PIT_CSV.exists():
        refresh()
    snaps = {}
    with open(PIT_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = date.fromisoformat(row["date"])
            snaps[d] = frozenset(t.strip() for t in row["tickers"].split(",")
                                 if t.strip())
    _snapshots = snaps
    _dates = sorted(snaps)


def members(asof) -> frozenset:
    """Actual S&P 500 membership on `asof` (latest snapshot <= asof)."""
    _load()
    if hasattr(asof, "date"):
        asof = asof.date()
    elif isinstance(asof, str):
        asof = date.fromisoformat(asof[:10])
    i = bisect_right(_dates, asof) - 1
    if i < 0:
        raise ValueError(f"{asof} predates the dataset ({_dates[0]})")
    return _snapshots[_dates[i]]


def all_members_since(start: str) -> list[str]:
    """Every ticker that was a member at any point since `start`: the
    snapshot in force at `start` plus every later snapshot."""
    _load()
    lo = date.fromisoformat(start[:10])
    out = set()
    i = max(0, bisect_right(_dates, lo) - 1)
    for d in _dates[i:]:
        out |= _snapshots[d]
    return sorted(out)


def last_snapshot_date() -> date:
    _load()
    return _dates[-1]
