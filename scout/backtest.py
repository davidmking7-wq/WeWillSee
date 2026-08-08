"""Out-of-sample validation harness: replay signal engines on 2016-2026 SIP
data and benchmark them against BOTH the equal-weight same-universe market
and the actual S&P 500 (SPY) over identical windows.

Method mirrors the v3 report's census: an entry every month, top picks per
date, the exact HIT rule (max close within 42 trading days >= entry * 1.05),
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
import json
import math
import pickle

import numpy as np
import pandas as pd

from . import config, data, signals, universe

REGIME_SYM = "SPY"
CACHE = config.SCOUT_DIR / "backtest_cache.pkl"
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
    "v4": (signals.feature_frames, signals.composite_at),
}


# ---------------------------------------------------------------- harness

def load_bars(no_cache: bool = False) -> dict:
    if CACHE.exists() and not no_cache:
        with open(CACHE, "rb") as f:
            bars = pickle.load(f)
        print(f"bars from cache: {bars['close'].shape[0]} days x "
              f"{bars['close'].shape[1]} symbols (delete {CACHE.name} to refetch)")
        return bars
    uni = universe.load()
    syms = sorted({u["symbol"] for u in uni} | {REGIME_SYM})
    print(f"fetching {config.CALIB_YEARS}y of SIP bars for {len(syms)} symbols "
          "(a few minutes)...")
    bars = data.daily_ohlcv(syms, config.CALIB_YEARS * 365 + 60)
    with open(CACHE, "wb") as f:
        pickle.dump(bars, f)
    return bars


def window_outcomes(c, pos, syms, h):
    """Per-symbol outcome dicts for the window starting the day after pos."""
    basis = c.iloc[pos]
    win = c.iloc[pos + 1: pos + 1 + h]
    out = {}
    for sym in syms:
        if sym not in win.columns or pd.isna(basis.get(sym)):
            continue
        r = (win[sym] / basis[sym]).dropna().values
        if len(r) < h:
            continue
        up = r >= 1 + config.TARGET_GAIN
        dn = r <= 1 + config.DROP_GAIN
        hit = bool(up.any())
        first_up = int(np.argmax(up)) if hit else h + 1
        first_dn = int(np.argmax(dn)) if dn.any() else h + 1
        out[sym] = {"hit": hit, "end": float(r[-1] - 1), "max": float(r.max() - 1),
                    "hit10": bool((r >= 1.10).any()),
                    "hit15": bool((r >= 1.15).any()),
                    "days": first_up + 1 if hit else None,
                    "dip_first": bool(dn.any() and first_dn < first_up)}
    return out


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
    return {
        "dates": len(windows), "picks": len(picks),
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
    }


def compound(windows):
    """Sequentially compound non-overlapping windows: strategy vs benchmarks.
    No costs/slippage; equal-weight picks held to day 42, then roll."""
    if not windows:
        return None
    strat = float(np.prod([1 + w["avg_end"] for w in windows]))
    spy = float(np.prod([1 + w["spy_end"] for w in windows]))
    mkt = float(np.prod([1 + w["mkt_end"] for w in windows]))
    return {"windows": len(windows),
            "strategy_growth_pct": round(100 * (strat - 1), 1),
            "spy_growth_pct": round(100 * (spy - 1), 1),
            "eqw_market_growth_pct": round(100 * (mkt - 1), 1)}


def run_engine(name, ff, comp, bars, positions, n_picks, min_pool=50):
    """Replay one engine over the given entry positions. Returns window list."""
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
    mkt_syms = [s for s in c.columns if s != REGIME_SYM]
    windows = []
    for pos in positions:
        ts = idx[pos]
        snap = comp(frames, ts).drop(index=[REGIME_SYM], errors="ignore")
        if len(snap) < min_pool:
            continue
        top = list(snap.index[:n_picks])
        outcomes = window_outcomes(c, pos, top, h)
        picks = [outcomes[s] for s in top if s in outcomes]
        if not picks:
            continue
        mkt = window_outcomes(c, pos, mkt_syms, h)
        spy_out = window_outcomes(c, pos, [REGIME_SYM], h)
        if not mkt or REGIME_SYM not in spy_out:
            continue
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
            "avg_end": float(np.mean([p["end"] for p in picks])),
            "mkt_end": float(np.mean([m["end"] for m in mkt.values()])),
            "spy_end": spy_out[REGIME_SYM]["end"],
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
    pos_all = range(WARMUP, len(idx) - h - 1, step)
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


def run(n_picks: int, step: int, no_cache: bool, start=None, end=None,
        engines=None, out_path=RESULTS) -> dict:
    bars = load_bars(no_cache)
    idx = bars["close"].index
    positions = positions_for(idx, start, end, step)
    if not positions:
        raise SystemExit("no entry dates in the requested range")
    print(f"{len(positions)} entry dates, {idx[positions[0]].date()} .. "
          f"{idx[positions[-1]].date()}, {n_picks} picks/date, "
          f"horizon {config.HORIZON_TDAYS} td")

    results = {}
    for name, (ff, comp) in (engines or ENGINES).items():
        windows = run_engine(name, ff, comp, bars, positions, n_picks)
        results[name] = summarize(windows, step)

    out = {"span": [str(idx[positions[0]].date()), str(idx[positions[-1]].date())],
           "picks_per_date": n_picks, "step_tdays": step,
           "horizon_tdays": config.HORIZON_TDAYS, "target": config.TARGET_GAIN,
           "label": "HIT = max close over next 42 trading days >= entry close * 1.05",
           "universe": "today's S&P 500 applied historically (survivorship)",
           "benchmarks": "mkt = equal-weight same universe; spy = S&P 500 ETF "
                         "(SPY), identical windows",
           "note": "monthly windows overlap (~2x); see non_overlapping for the "
                   "independent subset; +5% is the minimum bar — see p10/p15 "
                   "and mean/med max gain (mean winsorized at +50%) for how far "
                   "picks actually run; symbols delisted mid-window are dropped "
                   "from both picks and benchmarks (within-window survivorship)",
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
            print(f"\n{name} compounded (non-overlapping, no costs): "
                  f"strategy {cg['strategy_growth_pct']:+.1f}% | "
                  f"SPY {cg['spy_growth_pct']:+.1f}% | "
                  f"eq-w market {cg['eqw_market_growth_pct']:+.1f}%")
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
    args = ap.parse_args()
    run(args.picks, args.step, args.no_cache, args.start, args.end)


if __name__ == "__main__":
    main()
