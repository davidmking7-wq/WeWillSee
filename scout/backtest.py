"""Historical validation harness: replay signal engines on daily SIP bars
data and benchmark them against BOTH the equal-weight same-universe market
and the actual S&P 500 (SPY) over identical windows.

Signals are formed with a completed daily close.  The honest default enters at
the following day's open; same-close entry is exposed only as an audit
comparison.  An entry is taken every month, with the exact net HIT rule (max
liquidation value within 42 trading days >= starting capital * 1.05),
outcomes measured per pick. +5% is the MINIMUM bar, so the report also
tracks how far picks actually ran: mean/median max gain, P(+10%), P(+15%).

The v1 engine is frozen inline below (weights and gates as literals) so it
stays comparable forever, independent of whatever config/signals evolve into.

Run:  python -m scout.backtest                        (uses/saves a bar cache)
      python -m scout.backtest --start 2022-01-01     (holdout slice)
      python -m scout.backtest --no-cache             (force fresh data fetch)

Statistical honesty: monthly windows overlap (each is 2 months), so the
effective independent sample is roughly half the date count — the report
also prints the strictly non-overlapping subset and compounds a sequential
"followed it" growth number ONLY on that subset. Universe is today's
constituents applied historically (survivorship): compare engines against
each other and the same-universe benchmarks; don't quote raw hit rates as
forward probabilities.
"""
import argparse
import hashlib
import json
import math
import pickle
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, data, execution, pit, signals, universe

REGIME_SYM = "SPY"
CACHE = config.SCOUT_DIR / "backtest_cache.pkl"
CACHE_PIT = config.SCOUT_DIR / "backtest_cache_pit.pkl"
CACHE_1500 = config.SCOUT_DIR / "backtest_cache_1500.pkl"
RESULTS = config.SCOUT_DIR / "backtest_results.json"
WARMUP = 270                 # bars before the first entry (feature lookbacks)


# ---------------------------------------------------------------- v1 engine
# Frozen copy of the original signals.py (pre-v3). Do not edit.

def _v1_feature_frames(o, c, v):
    mom = c.shift(21) / c.shift(252) - 1
    ret1m = c / c.shift(21) - 1
    high_prox = c / c.rolling(252, min_periods=200).max()
    sma50ok = (c > c.rolling(50).mean()).astype(float)
    sma200ok = (c > c.rolling(200).mean()).astype(float)
    vol63 = c.pct_change().rolling(63).std() * np.sqrt(252)
    gap_ret = o / c.shift(1) - 1
    vol_med = v.rolling(20, min_periods=10).median()
    surge = (gap_ret >= 0.03) & (v >= 2 * vol_med)
    gapmag = gap_ret.where(surge, 0.0)
    gap = gapmag.rolling(20, min_periods=1).max().clip(0, 0.06) / 0.06
    return {"mom": mom, "ret1m": ret1m, "high": high_prox, "sma50ok": sma50ok,
            "sma200ok": sma200ok, "vol": vol63, "gap": gap}


def _v1_composite_at(frames, ts):
    row = {k: f.loc[ts] for k, f in frames.items()}
    df = pd.DataFrame(row).dropna(subset=["mom", "high", "vol", "ret1m"])
    if df.empty:
        return df
    vol_decile = df["vol"].rank(pct=True)
    keep = ((df["sma200ok"] == 1.0)
            & (df["ret1m"] <= 0.25) & (df["ret1m"] >= -0.15)
            & (vol_decile < 0.90))
    df = df[keep]
    if df.empty:
        return df
    mom_pct = df["mom"].rank(pct=True)
    high_pct = df["high"].rank(pct=True)
    below = ((0.20 - df["vol"]) / 0.10).clip(lower=0)
    above = ((df["vol"] - 0.40) / 0.25).clip(lower=0)
    vol_band = (1 - pd.concat([below, above], axis=1).max(axis=1)).clip(0, 1)
    r1_pct = df["ret1m"].rank(pct=True)
    guard = 1 - ((r1_pct - 0.8).clip(lower=0) * 5)
    df["score"] = 100 * (0.35 * mom_pct + 0.25 * high_pct + 0.15 * df["gap"]
                         + 0.10 * vol_band + 0.10 * guard
                         + 0.05 * df["sma50ok"])
    return df.sort_values("score", ascending=False)


# ---------------------------------------------------------------- v3 engine
# Frozen copy of the v3 composite (pre-v4). v3's features are a subset of
# v4's frames, so it reuses signals.feature_frames. Do not edit.

def _v3_composite_at(frames, ts):
    row = {k: f.loc[ts] for k, f in frames.items()}
    df = pd.DataFrame(row).dropna(subset=["mom", "mom6", "high", "vol",
                                          "ret1m", "max21", "pos252", "brk20"])
    if df.empty:
        return df
    vol_decile = df["vol"].rank(pct=True)
    max_decile = df["max21"].rank(pct=True)
    keep = ((df["sma200ok"] == 1.0)
            & (df["ret6"] > 0)
            & (df["ret1m"] <= 0.25) & (df["ret1m"] >= -0.15)
            & (vol_decile < 0.90) & (max_decile < 0.90))
    df = df[keep]
    if df.empty:
        return df
    mom_pct = df["mom"].rank(pct=True)
    mom6_pct = df["mom6"].rank(pct=True)
    high_pct = df["high"].rank(pct=True)
    smooth_pct = df["pos252"].rank(pct=True)
    brk_pct = df["brk20"].rank(pct=True)
    below = ((0.20 - df["vol"]) / 0.10).clip(lower=0)
    above = ((df["vol"] - 0.40) / 0.25).clip(lower=0)
    vol_band = (1 - pd.concat([below, above], axis=1).max(axis=1)).clip(0, 1)
    r1_pct = df["ret1m"].rank(pct=True)
    guard = 1 - ((r1_pct - 0.8).clip(lower=0) * 5)
    df["score"] = 100 * (0.20 * mom_pct + 0.15 * mom6_pct + 0.25 * high_pct
                         + 0.05 * df["gap"] + 0.10 * smooth_pct
                         + 0.07 * brk_pct + 0.10 * vol_band
                         + 0.05 * guard + 0.03 * df["sma50ok"])
    df["mom_pct"] = mom_pct
    return df.sort_values("score", ascending=False)


ENGINES = {
    "v1": (_v1_feature_frames, _v1_composite_at),
    "v3": (signals.feature_frames, _v3_composite_at),
    # live signals module. v5 = v4 + tradeable-liquidity gate; on large-cap
    # universes the gate is a near-no-op, so this row is comparable to the
    # historical v4 numbers there.
    "v5": (signals.feature_frames, signals.composite_at),
}


# ---------------------------------------------------------------- harness

def universe_symbols(mode: str) -> list[str]:
    """Symbol list for a backtest universe mode.
    sp500  — current large-cap segment (the original test universe)
    pit500 — every ACTUAL S&P 500 member at any point since 2016,
             including later-delisted ones (point-in-time)
    sp1500 — current S&P 1500 (large+mid+small; live-pipeline universe)"""
    if mode == "pit500":
        return sorted(set(pit.all_members_since("2016-01-01")) | {REGIME_SYM})
    uni = universe.load()
    if mode == "sp500":
        uni = [u for u in uni if u.get("segment", "large") == "large"]
    return sorted({u["symbol"] for u in uni} | {REGIME_SYM})


def _validate_bar_frames(bars: dict) -> None:
    for field in ("open", "close", "volume"):
        frame = bars.get(field)
        if not isinstance(frame, pd.DataFrame):
            raise RuntimeError(f"market-data bundle is missing the {field!r} frame")
        if any(not pd.api.types.is_numeric_dtype(dtype) for dtype in frame.dtypes):
            raise RuntimeError(f"market-data {field!r} frame contains non-numeric data")
    if not bars["open"].index.equals(bars["close"].index):
        raise RuntimeError("market-data open/close indexes do not match")
    if not bars["volume"].index.equals(bars["close"].index):
        raise RuntimeError("market-data volume/close indexes do not match")
    if not bars["open"].columns.equals(bars["close"].columns):
        raise RuntimeError("market-data open/close symbol columns do not match")
    if not bars["volume"].columns.equals(bars["close"].columns):
        raise RuntimeError("market-data volume/close symbol columns do not match")


def _validate_confirmatory_coverage(
    bars: dict, mode: str, expected_symbols: list[str], source: str,
) -> None:
    """Reject legacy or partial data rather than silently treating it as complete."""
    _validate_bar_frames(bars)
    meta = bars.get("metadata")
    required = {
        "coverage_schema_version", "status", "requested_symbols",
        "requested_symbol_count", "returned_symbols", "returned_symbol_count",
        "missing_symbols", "missing_symbol_count", "missing_symbol_fraction",
        "declared_threshold", "threshold_passed", "observed_start", "observed_end",
        "universe_mode", "chunks",
    }
    if not isinstance(meta, dict):
        raise RuntimeError(
            f"{source} is a legacy cache without coverage metadata; rerun with "
            "--no-cache before using it for confirmatory research"
        )
    absent = sorted(required - set(meta))
    if absent:
        raise RuntimeError(
            f"{source} has incomplete coverage metadata ({', '.join(absent)}); "
            "rerun with --no-cache"
        )
    threshold = meta.get("declared_threshold") or {}
    declared = threshold.get("max_missing_symbol_fraction")
    expected_threshold = config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION
    problems = []
    if meta.get("status") != "complete":
        problems.append(f"status={meta.get('status')!r}")
    if meta.get("threshold_passed") is not True:
        problems.append("declared coverage threshold did not pass")
    if threshold.get("name") != "BACKTEST_MAX_MISSING_SYMBOL_FRACTION":
        problems.append("missing-threshold label is absent or different")
    if declared != expected_threshold:
        problems.append(
            f"missing threshold {declared!r} != configured {expected_threshold!r}"
        )
    declared_fraction = meta.get("missing_symbol_fraction")
    if not isinstance(declared_fraction, (int, float)):
        problems.append("missing-symbol fraction is absent or not numeric")
    elif float(declared_fraction) > expected_threshold:
        problems.append("missing-symbol fraction exceeds the configured threshold")
    if meta.get("universe_mode") != mode:
        problems.append(
            f"universe_mode={meta.get('universe_mode')!r}, expected {mode!r}"
        )
    if set(meta.get("requested_symbols", [])) != set(expected_symbols):
        problems.append("requested symbol set differs from the current universe")
    if meta.get("requested_symbol_count") != len(meta.get("requested_symbols", [])):
        problems.append("requested symbol count is inconsistent")
    if meta.get("returned_symbol_count") != len(meta.get("returned_symbols", [])):
        problems.append("returned symbol count is inconsistent")
    if meta.get("missing_symbol_count") != len(meta.get("missing_symbols", [])):
        problems.append("missing symbol count is inconsistent")
    chunks = meta.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        problems.append("chunk-attempt metadata is absent")
    elif any(not isinstance(chunk, dict) or chunk.get("completed") is not True
             for chunk in chunks):
        problems.append("one or more chunks did not complete")
    if set(meta.get("requested_symbols", [])) != (
        set(meta.get("returned_symbols", [])) | set(meta.get("missing_symbols", []))
    ):
        problems.append("returned and missing symbols do not partition the request")
    observed_close_symbols = set(
        bars["close"].columns[bars["close"].notna().any(axis=0)]
    )
    if set(meta.get("returned_symbols", [])) != observed_close_symbols:
        problems.append("declared returned symbols differ from observed close columns")
    if problems:
        raise RuntimeError(
            f"{source} is not valid confirmatory data: " + "; ".join(problems)
        )


def load_bars(no_cache: bool = False, mode: str = "sp500") -> dict:
    cache = {"sp500": CACHE, "pit500": CACHE_PIT, "sp1500": CACHE_1500}[mode]
    syms = universe_symbols(mode)
    if cache.exists() and not no_cache:
        with open(cache, "rb") as f:
            bars = pickle.load(f)
        _validate_confirmatory_coverage(bars, mode, syms, cache.name)
        print(f"bars from cache: {bars['close'].shape[0]} days x "
              f"{bars['close'].shape[1]} symbols (delete {cache.name} to refetch)")
        return bars
    print(f"fetching {config.CALIB_YEARS}y of SIP bars for {len(syms)} symbols "
          f"({mode}; a few minutes)...")
    bars = data.daily_ohlcv(syms, config.CALIB_YEARS * 365 + 60)
    bars["metadata"] = dict(bars["metadata"])
    bars["metadata"]["universe_mode"] = mode
    bars["metadata"]["cache_schema_version"] = 1
    _validate_confirmatory_coverage(bars, mode, syms, "fresh fetch")
    with open(cache, "wb") as f:
        pickle.dump(bars, f)
    return bars


def window_outcomes(c, pos, syms, h, allow_partial=False, *, open_prices=None,
                    assumptions=None):
    """Per-symbol net outcomes without silently deleting selected slots.

    ``allow_partial`` is retained for older lab callers. It now selects the
    explicit ``last_print`` sensitivity policy instead of changing whether a
    symbol disappears from the result. Honest next-open execution requires an
    open-price frame; callers must provide it rather than silently falling back
    to the signal close.
    """
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    if allow_partial and assumptions.missing_leg_policy == "total_loss":
        assumptions = execution.ExecutionAssumptions(
            entry_timing=assumptions.entry_timing,
            spread_bps=assumptions.spread_bps,
            slippage_bps=assumptions.slippage_bps,
            commission_bps=assumptions.commission_bps,
            missing_leg_policy="last_print",
        )
    if open_prices is None:
        if assumptions.entry_timing == "next_open":
            raise ValueError("next_open execution requires open_prices")
        open_prices = c
    return execution.simulate_window(
        open_prices, c, pos, syms, h, assumptions,
    )["outcomes"]


def agg(windows):
    """Aggregate a list of per-date window dicts into one summary row."""
    if not windows:
        return None
    picks = [p for w in windows for p in w["picks"]]
    if not picks:
        return None
    hits = [p for p in picks if p["hit"]]
    days = [p["days"] for p in hits]
    beat_mkt = [w for w in windows if w["avg_end"] > w["mkt_end"]]
    beat_spy = [w for w in windows if w["avg_end"] > w["spy_end"]]
    missing_entries = sum(len(w.get("missing_entries", [])) for w in windows)
    partial_legs = sum(len(w.get("partial_legs", [])) for w in windows)
    data_quality_legs = sum(len(w.get("data_quality_legs", [])) for w in windows)
    selected_legs = sum(len(w.get("symbols", [])) for w in windows)
    benchmark_membership = sum(w.get("benchmark_membership_count", 0) for w in windows)
    benchmark_eligible = sum(w.get("benchmark_eligible_count", 0) for w in windows)
    benchmark_excluded = sum(
        w.get("benchmark_excluded_no_signal_close_count", 0) for w in windows
    )
    benchmark_missing = sum(
        len(w.get("benchmark_missing_entries", [])) for w in windows
    )
    benchmark_partial = sum(
        len(w.get("benchmark_partial_legs", [])) for w in windows
    )
    benchmark_data_quality = sum(
        len(w.get("benchmark_data_quality_legs", [])) for w in windows
    )
    return {
        "dates": len(windows), "picks": len(picks),
        "selected_legs": selected_legs,
        "missing_entries": missing_entries,
        "partial_legs": partial_legs,
        "data_quality_legs": data_quality_legs,
        "missing_or_partial_pct": round(
            100 * (missing_entries + partial_legs) / selected_legs, 2
        ) if selected_legs else 0.0,
        "benchmark_membership_legs": benchmark_membership,
        "benchmark_eligible_signal_close_legs": benchmark_eligible,
        "benchmark_excluded_no_signal_close_legs": benchmark_excluded,
        "benchmark_signal_close_coverage_pct": round(
            100 * benchmark_eligible / benchmark_membership, 4
        ) if benchmark_membership else 0.0,
        "benchmark_missing_entries": benchmark_missing,
        "benchmark_partial_legs": benchmark_partial,
        "benchmark_data_quality_legs": benchmark_data_quality,
        "hit_rate": round(100 * len(hits) / len(picks), 1),
        "p10_rate": round(100 * float(np.mean([p["hit10"] for p in picks])), 1),
        "p15_rate": round(100 * float(np.mean([p["hit15"] for p in picks])), 1),
        # per-date mean of the picks' average — weight-consistent with the
        # per-date mkt/spy benchmarks it is compared against
        "avg_end_ret": round(100 * float(np.mean([w["avg_end"] for w in windows])), 2),
        "med_max_gain": round(100 * float(np.median([p["max"] for p in picks])), 2),
        "mean_max_gain": round(100 * float(np.mean([min(p["max"], 0.50) for p in picks])), 2),
        "med_days_to_hit": float(np.median(days)) if days else None,
        "dip_first_rate": round(100 * float(np.mean([p["dip_first"] for p in picks])), 1),
        "beat_market": f"{len(beat_mkt)}/{len(windows)}",
        "beat_market_pct": round(100 * len(beat_mkt) / len(windows), 1),
        "beat_spy": f"{len(beat_spy)}/{len(windows)}",
        "beat_spy_pct": round(100 * len(beat_spy) / len(windows), 1),
        "avg_mkt_end_ret": round(100 * float(np.mean([w["mkt_end"] for w in windows])), 2),
        "avg_spy_end_ret": round(100 * float(np.mean([w["spy_end"] for w in windows])), 2),
        "avg_window_daily_max_dd": round(100 * float(np.mean([
            execution.max_drawdown(w["strategy_equity"]) for w in windows
        ])), 2),
    }


def compound(windows):
    """Compound strategy/reset windows and headline continuous SPY buy-and-hold."""
    if not windows:
        return None
    strat_curve = execution.stitch_curves(w["strategy_equity"] for w in windows)
    spy_curve = execution.stitch_curves(w["spy_equity"] for w in windows)
    mkt_curve = execution.stitch_curves(w["mkt_equity"] for w in windows)
    strat, spy, mkt = strat_curve[-1], spy_curve[-1], mkt_curve[-1]
    first, last = windows[0], windows[-1]
    spy_entry = first.get("spy_buy_hold_entry_price_fill")
    spy_exit_raw = last.get("spy_buy_hold_exit_price_raw")
    spy_exit_side = last.get("spy_buy_hold_side_cost_rate")
    continuous_spy = None
    if (spy_entry is not None and spy_entry > 0 and spy_exit_raw is not None
            and spy_exit_raw > 0 and spy_exit_side is not None):
        continuous_spy = spy_exit_raw * (1 - spy_exit_side) / spy_entry
    return {"windows": len(windows),
            "headline_benchmark": "SPY buy-and-hold: one entry, one final exit",
            "strategy_growth_pct": round(100 * (strat - 1), 6),
            "spy_buy_and_hold_growth_pct": (
                round(100 * (continuous_spy - 1), 6)
                if continuous_spy is not None else None
            ),
            "spy_buy_and_hold_entry_date": first.get("spy_buy_hold_entry_date"),
            "spy_buy_and_hold_exit_date": last.get("spy_buy_hold_exit_date"),
            "spy_buy_and_hold_round_trips": 1 if continuous_spy is not None else 0,
            "spy_window_reset_growth_pct": round(100 * (spy - 1), 6),
            "spy_window_reset_round_trips": len(windows),
            "eqw_market_window_reset_growth_pct": round(100 * (mkt - 1), 6),
            "eqw_market_window_reset_round_trips": len(windows),
            "strategy_daily_max_drawdown_pct": round(
                100 * execution.max_drawdown(strat_curve), 2),
            "spy_window_reset_daily_max_drawdown_pct": round(
                100 * execution.max_drawdown(spy_curve), 2),
            "eqw_market_window_reset_daily_max_drawdown_pct": round(
                100 * execution.max_drawdown(mkt_curve), 2),
            "daily_observations": len(strat_curve),
            "strategy_daily_equity": [round(x, 8) for x in strat_curve]}


def run_engine(name, ff, comp, bars, positions, n_picks, min_pool=50,
               pit_mode=False, assumptions=None):
    """Replay one engine over the given entry positions. Returns window list.
    pit_mode restricts each date's candidate pool AND benchmark to the
    stocks that were actually in the S&P 500 that day. Every selected slot is
    retained and terminally missing quotes follow the explicit policy."""
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    o = bars["open"]
    c = bars["close"]
    idx = c.index
    h = config.HORIZON_TDAYS
    spy = c[REGIME_SYM]
    bull = (spy.dropna() > spy.dropna().rolling(200).mean()).reindex(idx)
    spy_vol21 = (spy.pct_change().rolling(21).std() * math.sqrt(252)).reindex(idx)
    # expanding quantile: the crash threshold at each date uses only history
    # up to that date (a full-sample quantile would leak the future)
    vol_q80 = spy_vol21.expanding(min_periods=252).quantile(0.80)

    frames = ff(bars["open"], c, bars["volume"])
    windows = []
    for pos in positions:
        ts = idx[pos]
        if pit_mode:
            mem = pit.members(ts)
            cols = [s for s in c.columns if s in mem or s == REGIME_SYM]
            # one-row slices so the cross-sectional ranks see ONLY that
            # day's actual members (cheap: 1 x ~500 per frame)
            day_frames = {k: f.loc[[ts], cols] for k, f in frames.items()}
            snap = comp(day_frames, ts).drop(index=[REGIME_SYM], errors="ignore")
            benchmark_members = [s for s in cols if s != REGIME_SYM]
        else:
            snap = comp(frames, ts).drop(index=[REGIME_SYM], errors="ignore")
            benchmark_members = [s for s in c.columns if s != REGIME_SYM]
        # Benchmark membership is decided using information available at the
        # signal close only.  This removes pre-listing/no-close columns without
        # peeking at whether a next-day open happens to exist.
        signal_close = c.iloc[pos]
        mkt_syms = [
            symbol for symbol in benchmark_members
            if pd.notna(signal_close.get(symbol))
        ]
        benchmark_excluded = [
            symbol for symbol in benchmark_members
            if pd.isna(signal_close.get(symbol))
        ]
        if len(snap) < min_pool:
            continue
        top = list(snap.index[:n_picks])
        pick_sim = execution.simulate_window(o, c, pos, top, h, assumptions)
        picks = [pick_sim["outcomes"][s] for s in top]
        mkt_sim = execution.simulate_window(o, c, pos, mkt_syms, h, assumptions)
        spy_sim = execution.simulate_window(o, c, pos, [REGIME_SYM], h, assumptions)
        mkt = mkt_sim["outcomes"]
        spy_out = spy_sim["outcomes"]
        b = bull.iloc[pos]
        if pd.isna(b):
            continue
        regime = "bull" if bool(b) else "bear"
        sv, q = spy_vol21.iloc[pos], vol_q80.iloc[pos]
        crash = (regime == "bear" and not pd.isna(sv) and not pd.isna(q)
                 and float(sv) > float(q))
        windows.append({
            "date": str(ts.date()), "pos": pos, "regime": regime,
            "crash": crash, "picks": picks, "symbols": top,
            "avg_end": float(pick_sim["equity"][-1] - 1),
            "mkt_end": float(mkt_sim["equity"][-1] - 1),
            "spy_end": float(spy_sim["equity"][-1] - 1),
            "strategy_equity": pick_sim["equity"],
            "mkt_equity": mkt_sim["equity"],
            "spy_equity": spy_sim["equity"],
            "missing_entries": pick_sim["missing_entries"],
            "partial_legs": pick_sim["partial_legs"],
            "data_quality_legs": pick_sim.get("data_quality_legs", []),
            "benchmark_membership_count": len(benchmark_members),
            "benchmark_eligible_count": len(mkt_syms),
            "benchmark_excluded_no_signal_close_count": len(benchmark_excluded),
            "benchmark_excluded_no_signal_close": benchmark_excluded,
            "benchmark_missing_entries": mkt_sim["missing_entries"],
            "benchmark_partial_legs": mkt_sim["partial_legs"],
            "benchmark_data_quality_legs": mkt_sim.get("data_quality_legs", []),
            "spy_buy_hold_entry_price_fill": spy_out[REGIME_SYM]["entry_price_fill"],
            "spy_buy_hold_entry_date": spy_out[REGIME_SYM]["entry_date"],
            "spy_buy_hold_exit_price_raw": spy_out[REGIME_SYM]["exit_price_raw"],
            "spy_buy_hold_exit_date": str(idx[pos + h].date()),
            "spy_buy_hold_side_cost_rate": assumptions.side_cost_rate,
        })
    return windows


def summarize(windows, step):
    h = config.HORIZON_TDAYS
    stride = max(1, math.ceil(h / step))   # ceil: never let subset windows overlap
    nonoverlap = windows[::stride]
    return {
        "all": agg(windows),
        "non_crash": agg([w for w in windows if not w["crash"]]),
        "bull": agg([w for w in windows if w["regime"] == "bull"]),
        "bear": agg([w for w in windows if w["regime"] == "bear"]),
        "non_overlapping": agg(nonoverlap),
        "compounded_non_overlapping": compound(nonoverlap),
        "crash_dates_flagged": sum(1 for w in windows if w["crash"]),
    }


def positions_for(idx, start, end, step):
    h = config.HORIZON_TDAYS
    # ``simulate_leg`` permits pos + horizon == len(idx) - 1.  The range stop
    # is exclusive, so len(idx) - horizon includes that final valid signal.
    pos_all = range(WARMUP, len(idx) - h, step)
    lo = pd.Timestamp(start) if start else None
    hi = pd.Timestamp(end) if end else None
    out = []
    for pos in pos_all:
        ts = idx[pos].tz_localize(None)
        if lo is not None and ts < lo:
            continue
        if hi is not None and ts > hi:
            continue
        out.append(pos)
    return out


def _data_fingerprint(bars: dict) -> str:
    """Full SHA-256 over every OHLCV value, label, index, and dtype."""
    _validate_bar_frames(bars)
    digest = hashlib.sha256()
    for field in ("open", "close", "volume"):
        frame = bars[field]
        digest.update(field.encode("utf-8"))
        digest.update(json.dumps(list(frame.shape)).encode("utf-8"))
        digest.update(str(frame.index.dtype).encode("utf-8"))
        digest.update(json.dumps(list(map(str, frame.dtypes))).encode("utf-8"))
        digest.update(json.dumps(list(map(str, frame.index))).encode("utf-8"))
        digest.update(json.dumps(list(map(str, frame.columns))).encode("utf-8"))
        values = np.asarray(
            frame.to_numpy(dtype=np.float64, na_value=np.nan),
            dtype="<f8", order="C",
        )
        # Normalize every NaN payload before hashing so equivalent missing
        # values have one canonical byte representation.
        if np.isnan(values).any():
            values = values.copy()
            values[np.isnan(values)] = np.nan
        digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def _hash_scout_sources(items) -> str:
    """Hash ``(repo-relative path, bytes)`` pairs independent of CRLF checkout."""
    digest = hashlib.sha256()
    for rel, content in sorted(items, key=lambda item: item[0]):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _scout_source_hash() -> str:
    """Deterministic SHA-256 of all Python source that can drive the scanner."""
    items = [
        (path.relative_to(config.ROOT).as_posix(), path.read_bytes())
        for path in config.SCOUT_DIR.rglob("*.py")
    ]
    return _hash_scout_sources(items)


def _git_scout_source_hash(commit: str) -> str | None:
    """Hash committed scout sources without checking out or changing the worktree."""
    try:
        listing = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", commit, "--", "scout"],
            cwd=config.ROOT, capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        paths = sorted(path for path in listing if path.endswith(".py"))
        if not paths:
            return None
        items = []
        for rel in paths:
            content = subprocess.run(
                ["git", "show", f"{commit}:{rel}"], cwd=config.ROOT,
                capture_output=True, check=True,
            ).stdout
            items.append((rel.replace("\\", "/"), content))
        return _hash_scout_sources(items)
    except (OSError, subprocess.SubprocessError):
        return None


def _git_state() -> dict:
    """Record commit and actual worktree dirtiness; never infer clean state."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=config.ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=config.ROOT, capture_output=True, text=True, check=True,
        ).stdout
        return {"commit": commit, "dirty": bool(status.strip())}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def _git_commit() -> str | None:
    """Compatibility helper for older callers."""
    return _git_state()["commit"]


def _data_coverage(bars: dict, mode: str) -> dict:
    """JSON-safe fetch coverage plus independently observed frame coverage."""
    _validate_bar_frames(bars)
    fetch = bars.get("metadata")
    if isinstance(fetch, dict):
        fetch = json.loads(json.dumps(fetch, sort_keys=True, default=str))
    else:
        fetch = {
            "status": "legacy_or_in_memory_without_fetch_metadata",
            "threshold_passed": False,
            "declared_threshold": {
                "name": "BACKTEST_MAX_MISSING_SYMBOL_FRACTION",
                "max_missing_symbol_fraction":
                    config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION,
            },
        }
    fields = {}
    for field in ("open", "close", "volume"):
        frame = bars[field]
        fields[field] = {
            "rows": int(frame.shape[0]),
            "columns": int(frame.shape[1]),
            "symbols_with_any_value": int(frame.notna().any(axis=0).sum()),
            "non_null_values": int(frame.notna().sum().sum()),
        }
    close = bars["close"]
    data_span = [
        str(pd.Timestamp(close.index.min()).date()),
        str(pd.Timestamp(close.index.max()).date()),
    ] if len(close.index) else [None, None]
    return {
        "status": fetch.get("status"),
        "universe_mode": mode,
        "configured_max_missing_symbol_fraction":
            config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION,
        "fetch": fetch,
        "observed_data_span": data_span,
        "fields": fields,
    }


def run(n_picks: int, step: int, no_cache: bool, start=None, end=None,
        engines=None, out_path=RESULTS, mode: str = "sp500",
        assumptions=None) -> dict:
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    bars = load_bars(no_cache, mode)
    idx = bars["close"].index
    positions = positions_for(idx, start, end, step)
    if not positions:
        raise SystemExit("no entry dates in the requested range")
    pit_mode = mode == "pit500"
    if out_path is RESULTS and mode != "sp500":
        out_path = config.SCOUT_DIR / f"backtest_results_{mode}.json"
    print(f"{len(positions)} entry dates, {idx[positions[0]].date()} .. "
          f"{idx[positions[-1]].date()}, {n_picks} picks/date, "
          f"horizon {config.HORIZON_TDAYS} td, universe {mode}")

    results = {}
    for name, (ff, comp) in (engines or ENGINES).items():
        windows = run_engine(name, ff, comp, bars, positions, n_picks,
                             pit_mode=pit_mode, assumptions=assumptions)
        results[name] = summarize(windows, step)

    signal_span = [str(idx[positions[0]].date()), str(idx[positions[-1]].date())]
    close = bars["close"]
    data_span = [str(pd.Timestamp(close.index.min()).date()),
                 str(pd.Timestamp(close.index.max()).date())]
    git_state = _git_state()
    coverage = _data_coverage(bars, mode)

    UNIVERSE_NOTES = {
        "sp500": "today's S&P 500 applied historically (survivorship)",
        "pit500": "POINT-IN-TIME S&P 500: each date's actual members "
                  "(fja05680 dataset); missing/delisted paths follow the "
                  "declared missing-leg policy without reweighting",
        "sp1500": "today's S&P 1500 applied historically (survivorship — "
                  "STRONGER for mid/small caps; no free point-in-time source)",
    }
    out = {"span": signal_span,
           "picks_per_date": n_picks, "step_tdays": step,
           "horizon_tdays": config.HORIZON_TDAYS, "target": config.TARGET_GAIN,
           "label": f"NET HIT = max close liquidation value over next "
                    f"{config.HORIZON_TDAYS} trading days >= starting capital * "
                    f"{1 + config.TARGET_GAIN:.4g}, after declared costs",
           "artifact": {
               "provenance_schema_version": 2,
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "git_commit": git_state["commit"],
               "git_dirty": git_state["dirty"],
               "scout_source_hash": _scout_source_hash(),
               "engine_config": config.ENGINE,
               "data_fingerprint": _data_fingerprint(bars),
               "universe_mode": mode,
               "signal_span": signal_span,
               "data_span": data_span,
               "data_coverage": coverage,
               "entry_timing": assumptions.entry_timing,
               "execution": assumptions.metadata(),
               "missing_leg_policy": assumptions.missing_leg_policy,
           },
           "universe": UNIVERSE_NOTES[mode],
           "benchmarks": "mkt = equal-weight same universe; spy = S&P 500 ETF "
                         "(SPY), identical windows",
           "note": (
               "monthly windows overlap (~2x); see non_overlapping for the "
               "independent subset; every selected slot retains its original "
               "weight; missing entries stay cash and terminal disappearances "
               "follow artifact.missing_leg_policy; daily drawdown is marked "
               "from every close, not only 42-day checkpoints"
           ),
           "engines": results}
    if out_path:
        out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")

    hdr = (f"{'engine':<9}{'dates':>6}{'hit%':>6}{'+10%':>6}{'+15%':>6}"
           f"{'end%':>7}{'mmax%':>7}{'days':>6}{'dip%':>6}"
           f"{'>mkt':>8}{'>spy':>8}{'mkt%':>6}{'spy%':>6}")
    for section in ("all", "non_crash", "non_overlapping", "bull", "bear"):
        print(f"\n[{section}]")
        print(hdr)
        for name in (engines or ENGINES):
            a = results[name][section]
            if not a:
                print(f"{name:<9}{'-':>6}")
                continue
            print(f"{name:<9}{a['dates']:>6}{a['hit_rate']:>6}{a['p10_rate']:>6}"
                  f"{a['p15_rate']:>6}{a['avg_end_ret']:>7}{a['mean_max_gain']:>7}"
                  f"{str(a['med_days_to_hit']):>6}{a['dip_first_rate']:>6}"
                  f"{a['beat_market']:>8}{a['beat_spy']:>8}"
                  f"{a['avg_mkt_end_ret']:>6}{a['avg_spy_end_ret']:>6}")
    for name in (engines or ENGINES):
        cg = results[name]["compounded_non_overlapping"]
        if cg:
            spy_buy_hold = cg["spy_buy_and_hold_growth_pct"]
            spy_buy_hold_text = (
                f"{spy_buy_hold:+.1f}%" if spy_buy_hold is not None else "UNAVAILABLE"
            )
            print(f"\n{name} compounded (non-overlapping, "
                  f"{assumptions.estimated_round_trip_bps:.1f} bps est. round trip): "
                  f"strategy {cg['strategy_growth_pct']:+.1f}% | "
                  f"SPY buy/hold (1 entry/exit) "
                  f"{spy_buy_hold_text} | "
                  f"SPY reset each window {cg['spy_window_reset_growth_pct']:+.1f}% | "
                  f"eq-w market reset each window "
                  f"{cg['eqw_market_window_reset_growth_pct']:+.1f}% | "
                  f"daily maxDD {cg['strategy_daily_max_drawdown_pct']:+.1f}%")
    if out_path:
        print(f"\nwrote {out_path}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.backtest")
    ap.add_argument("--picks", type=int, default=5, help="picks per entry date")
    ap.add_argument("--step", type=int, default=21, help="trading days between entries")
    ap.add_argument("--start", default=None, help="first entry date (YYYY-MM-DD)")
    ap.add_argument("--end", default=None, help="last entry date (YYYY-MM-DD)")
    ap.add_argument("--no-cache", action="store_true", help="refetch bars")
    ap.add_argument("--universe", default="sp500",
                    choices=["sp500", "pit500", "sp1500"],
                    help="sp500 = current large caps; pit500 = each date's "
                         "ACTUAL S&P 500 members (point-in-time); sp1500 = "
                         "current S&P 1500 incl. mid/small")
    execution.add_execution_args(ap)
    args = ap.parse_args()
    assumptions = execution.from_args(args)
    run(args.picks, args.step, args.no_cache, args.start, args.end,
        mode=args.universe, assumptions=assumptions)


if __name__ == "__main__":
    main()
