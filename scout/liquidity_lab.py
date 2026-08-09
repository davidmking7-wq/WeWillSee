"""H23 - illiquidity as a PRICED characteristic, and whether config.MIN_DOLLAR_VOL
gates away the compensation.

(docstring completed after the run - see VERDICT at the bottom)
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from . import config
from .news_attention_lab import block_boot, phase_sweep      # verified, reused
from .idiovol_lab import (retire_stale, returns, forward, forward_partial,
                          quintile_labels, bucket_means, nw_ols,
                          sub_portfolios, ladder, book_turnover, perf,
                          _roll_sum)

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against the outcome.
# --------------------------------------------------------------------------
WINDOWS = (21, 63)                  # formation lookbacks; 21 = registered primary
PRIMARY_W = 21
HORIZONS = (21, 42)                 # 42 = registered primary (the repo's horizon)
PRIMARY_H = 42
HOLD = 42                           # tradeable book: hold 42 sessions ...
STRIDE = 21                         # ... rebalanced monthly
N_Q = 5
MIN_ELIGIBLE = 50                   # thinner cross-sections are skipped
MIN_OBS = 15                        # valid sessions needed inside a 21d window
COST_BPS = 10.0                     # flat round trip, for the comparison only
BOOT_REPS = 5000
CTRL_REPS = 200                     # random-quintile draws
PLACEBO_REPS = 100                  # symbol-pairing placebo draws
SEED = 20260809

BIG_MOVE = 0.45                     # |1-day return| guard (data_audit.BIG_MOVE)
SPLIT_LOG_TOL = 0.35                # only repair splits this far from 1:1
STALE_RUN = 10                      # identical consecutive closes -> retired
MARKET = "SPY"
RF_SENSITIVITY = 0.02               # ASSUMED flat rf for a Sharpe sensitivity

BARS_CACHE = config.SCOUT_DIR / "cache_liquidity_bars.pkl"
CLEAN_CACHE = config.SCOUT_DIR / "cache_liquidity_clean.pkl"
SPLIT_JSON = config.SCOUT_DIR / "cache_liquidity_splits.json"
RESULTS = config.SCOUT_DIR / "liquidity_results.json"

FIELDS = ("open", "high", "low", "close", "volume")
SIGNALS = ("amihud", "cs", "invdv")
PRIMARY_SIG = "amihud"
CS_K = 3.0 - 2.0 * math.sqrt(2.0)   # Corwin-Schultz constant


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def _fetch_ohlcv(symbols: list[str], days: int = 3900) -> dict[str, pd.DataFrame]:
    """`scout/data.daily_ohlcv` with the HIGH and LOW columns kept.

    data.py returns open/close/volume only, and the Corwin-Schultz estimator is
    a pure function of the daily RANGE, so this lab needs two more fields off
    the same request. Same client, same SIP feed, same adjustment=all, same
    pivot and the same US/Eastern normalisation - the only difference is the
    field list, so the closes are bit-identical to data.daily_ohlcv's."""
    from datetime import datetime, timedelta, timezone

    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    from . import data as daily_data

    client = StockHistoricalDataClient(config.ALPACA_API_KEY,
                                       config.ALPACA_SECRET_KEY)
    now = datetime.now(timezone.utc)
    frames = []
    for i in range(0, len(symbols), daily_data.CHUNK):
        chunk = symbols[i:i + daily_data.CHUNK]
        try:
            req = StockBarsRequest(symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                                   start=now - timedelta(days=days),
                                   end=now - timedelta(minutes=20),
                                   adjustment=Adjustment.ALL, feed=DataFeed.SIP)
            df = client.get_stock_bars(req).df
            if not df.empty:
                frames.append(df.reset_index()[["symbol", "timestamp", *FIELDS]])
        except Exception as e:
            print(f"  bars chunk {i // daily_data.CHUNK + 1} "
                  f"({len(chunk)} syms) failed: {e}")
    if not frames:
        raise RuntimeError("no market data returned at all")
    allb = pd.concat(frames, ignore_index=True)
    allb["timestamp"] = (pd.to_datetime(allb["timestamp"])
                         .dt.tz_convert("US/Eastern").dt.normalize())
    return {f: (allb.pivot_table(index="timestamp", columns="symbol", values=f,
                                 aggfunc="last").sort_index())
            for f in FIELDS}


def load_panel(refresh: bool = False) -> dict:
    """Raw daily OHLCV for the S&P 1500 (today's members) UNION every
    point-in-time S&P 500 member since 2016, plus SPY.

    The union is deliberate: today's S&P 1500 is the live engine's universe and
    carries survivorship, and the point-in-time S&P 500 is the survivorship
    control this repo's own H28 showed to be decisive. An illiquidity study
    needs that control more than any other study in the repo, because the names
    that die are the illiquid ones."""
    if BARS_CACHE.exists() and not refresh:
        return pd.read_pickle(BARS_CACHE)
    from . import pit, universe
    u = universe.load()
    seg = {r["symbol"]: r["segment"] for r in u}
    syms = sorted(set(seg) | set(pit.all_members_since("2016-01-01")) | {MARKET})
    print(f"fetching 10.7y of daily SIP bars (OHLCV) for {len(syms)} symbols ...")
    t0 = time.time()
    bars = {}
    for i in range(0, len(syms), 120):
        part = _fetch_ohlcv(syms[i:i + 120])
        for f in FIELDS:
            bars.setdefault(f, []).append(part[f])
        print(f"  {min(i + 120, len(syms)):>5}/{len(syms)} symbols "
              f"({time.time() - t0:.0f}s)")
    out = {}
    for f in FIELDS:
        df = pd.concat(bars[f], axis=1).sort_index()
        df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
        out[f] = df.astype("float64")
    cols = out["close"].columns
    out = {f: out[f].reindex(columns=cols) for f in FIELDS}
    out["segment"] = seg
    pd.to_pickle(out, BARS_CACHE)
    print(f"  panel {out['close'].shape[0]} sessions x {out['close'].shape[1]} "
          f"symbols cached ({time.time() - t0:.0f}s)")
    return out


def _split_events(symbols, start, end) -> dict:
    """Alpaca's own corporate-actions feed, cached to disk (same list every run,
    and the endpoint is rate-limited alongside the bar fetch)."""
    if SPLIT_JSON.exists():
        raw = json.loads(SPLIT_JSON.read_text())
        return {k: [{"ex_date": pd.Timestamp(e["ex_date"]), "ratio": e["ratio"],
                     "kind": e["kind"]} for e in v] for k, v in raw.items()}
    from . import intraday
    ev: dict = {}
    for i in range(0, len(symbols), 100):
        ev.update(intraday.split_events(list(symbols[i:i + 100]), start, end))
    SPLIT_JSON.write_text(json.dumps(
        {k: [{"ex_date": str(e["ex_date"].date()), "ratio": e["ratio"],
              "kind": e["kind"]} for e in v] for k, v in ev.items()}, indent=1))
    return ev


def repair_splits(bars: dict, verbose: bool = True) -> tuple[dict, list]:
    """GUARD 1. Back-adjust every split Alpaca's bar pipeline failed to apply -
    OPEN, HIGH, LOW, CLOSE and VOLUME together.

    Detection is on the CLOSE (intraday.unapplied_splits_close), the diagnostic
    that classifier was built against. All four price fields are divided by the
    ratio before the ex-date and volume is multiplied by it, so DOLLAR volume -
    the denominator of Amihud - is left invariant, which is the correct
    behaviour: a split changes neither the dollars traded nor the spread.
    Repairing the close alone (as a close-only study may) would leave the
    high/low range corrupted at exactly the dates the return series is fixed."""
    from . import intraday
    close = bars["close"]
    events = _split_events(list(close.columns), "2016-01-01",
                           str(close.index[-1].date()))
    repaired = []
    for sym in close.columns:
        for e in intraday.unapplied_splits_close(close[sym], events.get(sym, [])):
            if e["applied"] is not False:
                continue
            if abs(math.log(e["ratio"])) <= SPLIT_LOG_TOL:
                continue                  # ratio too close to 1 to be decisive
            m = close.index < e["ex_date"]
            for f in ("open", "high", "low", "close"):
                bars[f].loc[m, sym] = bars[f].loc[m, sym] / e["ratio"]
            bars["volume"].loc[m, sym] = bars["volume"].loc[m, sym] * e["ratio"]
            repaired.append(f"{sym} {e['ex_date'].date()} {e['ratio']:g}:1")
    if verbose:
        print(f"  split repair applied to {len(repaired)} events: "
              f"{', '.join(repaired[:12])}{' ...' if len(repaired) > 12 else ''}")
    return bars, repaired


def clean_bars(refresh: bool = False) -> dict:
    """Split-repaired, stale-retired OHLCV.

    GUARD 3 (stale-quote retirement) matters more here than anywhere else in
    the repo and in a direction that would have FAVOURED the hypothesis. A
    frozen delisted quote has |return| = 0, so its Amihud illiquidity is
    exactly 0 and its Corwin-Schultz spread is exactly 0 (high == low): it is
    pinned to the MOST LIQUID quintile forever, paying 0.00% forever. Leaving
    it in would depress the liquid leg and manufacture an illiquidity premium
    out of dead tickers."""
    if CLEAN_CACHE.exists() and not refresh:
        return pd.read_pickle(CLEAN_CACHE)
    bars = load_panel()
    seg = bars.pop("segment")
    bars = {f: bars[f].copy() for f in FIELDS}
    bars, repaired = repair_splits(bars)
    kept_close = bars["close"].copy()
    close, killed = retire_stale(bars["close"], run=STALE_RUN)
    dead = close.isna() & kept_close.notna()
    for f in FIELDS:
        bars[f] = bars[f].mask(dead)
    bars["close"] = close
    print(f"  stale-quote retirement: {len(killed)} symbols dropped from their "
          f"first run of {STALE_RUN} identical closes")
    out = {**bars, "close_stale": kept_close, "segment": seg,
           "repaired": repaired, "killed": killed}
    pd.to_pickle(out, CLEAN_CACHE)
    return out


def main() -> None:                                       # replaced below
    load_panel()


if __name__ == "__main__":
    main()
