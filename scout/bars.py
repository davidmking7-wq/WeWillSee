"""One shared daily-bar cache, so a lab never downloads what a sibling already has.

THE PROBLEM THIS SOLVES, measured
---------------------------------
Round 3 ran fourteen labs. Seven of them independently downloaded overlapping
slices of the same S&P 1500 daily history and wrote them to private caches:

    cache_high52_bars.pkl      1,649 symbols x 2,594 dates
    cache_accruals_bars.pkl    1,651 symbols x 2,664 dates
    cache_sue_bars.pkl         1,507 symbols x 2,664 dates
    cache_liquidity_bars.pkl, cache_idiovol_clean.pkl,
    cache_beatspy_panel.pkl, cache_fundlab_dataset.pkl

1.5 GB on disk, and roughly ten minutes of wall clock per lab spent re-fetching
bars that were already sitting in the directory. With a concurrency cap of two
agents, that is ten minutes of the critical path each time, for nothing.

`scout/data.py` is a fetcher, not a cache: every call goes to the network.
`scout/backtest.py` has a private pickle, but nothing else uses it. This module
is the missing layer.

HOW IT WORKS
------------
One master store, `scout/cache_bars_master.pkl`, holding open/high/low/close/
volume as time x symbol frames. `get()` returns the requested slice from the
master and fetches ONLY the symbols or dates that are genuinely absent, merging
them back so the next caller pays nothing.

`absorb()` reads the existing per-lab caches and folds them into the master
without touching the network at all — the data is already on disk, it was just
filed under seven different names.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not clean, repair or guard. Three price defects are documented in
BACKTEST-REPORT.md (5.1% unadjusted splits, 146 spin-off/reused-ticker moves,
frozen quotes on delisted names) and each study needs different treatment: a
52-week-high study must repair splits before computing a rolling max, while an
event study may prefer to drop the symbol-date entirely. Baking one policy into
the shared cache would silently impose it on every future lab. The cache stores
what the vendor sent; guards stay in the labs, where they can be stated.

Usage:
    from scout import bars
    px = bars.get(symbols, "2016-01-01", "2026-08-01")   # dict of frames
    px["close"], px["volume"], ...

    python -m scout.bars --absorb     # fold existing lab caches in, no network
    python -m scout.bars --status     # what is covered
"""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import pandas as pd

from . import config

MASTER = config.SCOUT_DIR / "cache_bars_master.pkl"
FIELDS = ("open", "high", "low", "close", "volume")
TZ = "US/Eastern"          # scout/data.py's convention; everything is coerced to it


def _norm_index(frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce a frame's index to tz-aware US/Eastern midnight.

    Labs pickle their caches with whatever tz-awareness they happened to have:
    scout/data.py returns tz-aware US/Eastern, several labs strip it, and one
    stores naive UTC. Unioning a naive index with an aware one raises
    "Cannot compare tz-naive and tz-aware timestamps, sort order is undefined"
    and yields an unsorted object index — which then silently fails every
    subsequent date comparison, so `_missing` reports that nothing is cached
    and the whole point of the cache is lost. That is exactly what the first
    absorb did: it folded in 1,649 symbols and then refetched all 1,506."""
    idx = pd.DatetimeIndex(frame.index)
    idx = idx.tz_localize(TZ) if idx.tz is None else idx.tz_convert(TZ)
    out = frame.copy()
    out.index = idx.normalize()
    return out[~out.index.duplicated(keep="first")].sort_index()


def _load() -> dict[str, pd.DataFrame]:
    if MASTER.exists():
        with open(MASTER, "rb") as f:
            return pickle.load(f)
    return {}


def _save(store: dict[str, pd.DataFrame]) -> None:
    tmp = MASTER.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(store, f, protocol=4)
    tmp.replace(MASTER)          # atomic: concurrent labs never see a half file


def _merge(store: dict[str, pd.DataFrame],
           new: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Union new frames into the store, preferring EXISTING values on overlap.

    Preferring existing is the safe direction: adjusted prices drift as
    dividends accrue, so a fresh pull disagrees slightly with an older one for
    the same date. Letting the newest write win would silently re-adjust
    history under a lab that had already read it and make two studies
    irreproducible against each other. First value wins; a caller who needs
    today's adjustment calls with use_cache=False."""
    out = dict(store)
    for field, frame in new.items():
        if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        frame = _norm_index(frame)
        if field not in out:
            out[field] = frame
            continue
        cur = _norm_index(out[field])
        idx = cur.index.union(frame.index)
        cols = cur.columns.union(frame.columns)
        cur = cur.reindex(index=idx, columns=cols)
        add = frame.reindex(index=idx, columns=cols)
        out[field] = cur.where(cur.notna(), add)
    return out


def coverage(store: dict[str, pd.DataFrame] | None = None) -> dict:
    store = _load() if store is None else store
    c = store.get("close")
    if c is None or c.empty:
        return {"symbols": 0, "dates": 0, "start": None, "end": None}
    return {"symbols": int(c.shape[1]), "dates": int(c.shape[0]),
            "start": str(c.index[0].date()), "end": str(c.index[-1].date()),
            "fields": sorted(store), "density_pct": round(100 * float(c.notna().mean().mean()), 1)}


def _missing(store, symbols, start, end) -> list[str]:
    """Symbols with no usable data inside the requested span.

    A symbol is 'covered' if it has any non-null close inside the window — not
    if it merely appears as a column. A column of NaNs is what a failed fetch
    leaves behind, and treating that as covered is how a gap becomes permanent."""
    c = store.get("close")
    if c is None or c.empty:
        return list(symbols)
    c = _norm_index(c)
    lo = pd.Timestamp(start).tz_localize(TZ)
    hi = pd.Timestamp(end).tz_localize(TZ)
    win = c.loc[(c.index >= lo) & (c.index <= hi)]
    have = set(win.columns[win.notna().any()]) if not win.empty else set()
    return [s for s in symbols if s not in have]


def get(symbols, start, end, use_cache: bool = True,
        verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Daily bars for `symbols` over [start, end], fetching only what is absent."""
    symbols = sorted(set(symbols))
    store = _load() if use_cache else {}
    need = _missing(store, symbols, start, end) if use_cache else symbols

    if need:
        from . import data
        days = int((pd.Timestamp(end) - pd.Timestamp(start)).days) + 45
        if verbose:
            print(f"  bars: {len(symbols) - len(need)} cached, fetching {len(need)}")
        fresh = data.daily_ohlcv(need, days=days)
        store = _merge(store, fresh)
        _save(store)
    elif verbose:
        print(f"  bars: all {len(symbols)} symbols served from cache")

    a = pd.Timestamp(start).tz_localize(TZ)
    b = pd.Timestamp(end).tz_localize(TZ)
    out = {}
    for field, frame in store.items():
        frame = _norm_index(frame)
        cols = [s for s in symbols if s in frame.columns]
        out[field] = frame.loc[(frame.index >= a) & (frame.index <= b), cols]
    return out


# ------------------------------------------------------------------ absorbing

def _frames_from(obj) -> dict[str, pd.DataFrame]:
    """Pull OHLCV frames out of whatever shape a lab happened to pickle.

    The seven Round-3 caches use at least three layouts: a dict keyed
    open/close/volume, a bare close DataFrame, and a dict with the frames
    nested under another key. Rather than encode each lab's private convention,
    recognise a time x symbol frame by its index type and take it."""
    found: dict[str, pd.DataFrame] = {}

    def visit(o, hint=None, depth=0):
        if depth > 3:
            return
        if isinstance(o, pd.DataFrame):
            if isinstance(o.index, pd.DatetimeIndex) and o.shape[1] > 5:
                name = hint if hint in FIELDS else "close"
                if name not in found or o.shape[1] > found[name].shape[1]:
                    found[name] = o
        elif isinstance(o, dict):
            for k, v in o.items():
                visit(v, hint=str(k).lower(), depth=depth + 1)

    visit(obj)
    return found


def absorb(verbose: bool = True) -> dict:
    """Fold every existing per-lab cache into the master. No network."""
    store = _load()
    before = coverage(store)
    for path in sorted(config.SCOUT_DIR.glob("cache_*.pkl")):
        if path.name == MASTER.name:
            continue
        try:
            with open(path, "rb") as f:
                obj = pickle.load(f)
        except Exception as e:
            if verbose:
                print(f"  skip {path.name}: {type(e).__name__}")
            continue
        frames = _frames_from(obj)
        if not frames:
            continue
        store = _merge(store, frames)
        if verbose:
            shp = {k: v.shape for k, v in frames.items()}
            print(f"  absorbed {path.name}: {shp}")
    _save(store)
    after = coverage(store)
    if verbose:
        print(f"\nbefore: {before}\nafter:  {after}")
    return after


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.bars")
    ap.add_argument("--absorb", action="store_true",
                    help="fold existing per-lab caches into the master (no network)")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    if args.absorb:
        absorb()
    else:
        print(coverage())
        if not MASTER.exists():
            print("no master cache yet — run --absorb")


if __name__ == "__main__":
    main()
