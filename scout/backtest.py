"""Out-of-sample validation harness: replay v1 and v3 on 2016-2026 SIP data.

This is the test the v3 report could not run itself — its 2014-2017 census
both selected the components and scored them, so only a different decade on
a different pipeline (dividend-adjusted SIP bars, this exact codebase) can
validate the engine switch. Method mirrors the census: an entry every month,
top picks per date, the exact HIT rule, equal-weight market benchmark over
identical windows.

The v1 engine is frozen inline below (weights and gates as literals) so it
stays comparable forever, independent of whatever config/signals evolve into.

Run:  python -m scout.backtest             (uses/saves a local bar cache)
      python -m scout.backtest --no-cache  (force fresh data fetch)

Statistical honesty: monthly windows overlap (each is 2 months), so the
effective independent sample is roughly half the date count — the report
also prints the strictly non-overlapping subset. Universe is today's
constituents applied historically (survivorship): compare engines against
each other and the same-universe market benchmark, don't quote the raw hit
rates as forward probabilities.
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


ENGINES = {
    "v1": (_v1_feature_frames, _v1_composite_at),
    "v3": (signals.feature_frames, signals.composite_at),
}


# ---------------------------------------------------------------- harness

def _load_bars(no_cache: bool) -> dict:
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


def _window_outcomes(c, pos, syms, h):
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
                    "days": first_up + 1 if hit else None,
                    "dip_first": bool(dn.any() and first_dn < first_up)}
    return out


def _agg(windows):
    """Aggregate a list of per-date dicts into one summary row."""
    if not windows:
        return None
    picks = [p for w in windows for p in w["picks"]]
    hits = [p for p in picks if p["hit"]]
    days = [p["days"] for p in hits]
    beat = [w for w in windows if w["avg_end"] > w["mkt_end"]]
    return {
        "dates": len(windows), "picks": len(picks),
        "hit_rate": round(100 * len(hits) / len(picks), 1) if picks else None,
        "avg_end_ret": round(100 * float(np.mean([p["end"] for p in picks])), 2),
        "med_max_gain": round(100 * float(np.median([p["max"] for p in picks])), 2),
        "med_days_to_hit": float(np.median(days)) if days else None,
        "dip_first_rate": round(100 * float(np.mean([p["dip_first"] for p in picks])), 1),
        "beat_market": f"{len(beat)}/{len(windows)}",
        "beat_market_pct": round(100 * len(beat) / len(windows), 1),
        "avg_mkt_end_ret": round(100 * float(np.mean([w["mkt_end"] for w in windows])), 2),
    }


def run(n_picks: int, step: int, no_cache: bool) -> dict:
    bars = _load_bars(no_cache)
    c = bars["close"]
    idx = c.index
    h = config.HORIZON_TDAYS

    spy = c[REGIME_SYM].dropna()
    bull = (spy > spy.rolling(200).mean()).reindex(idx)
    spy_vol21 = (spy.pct_change().rolling(21).std() * math.sqrt(252)).reindex(idx)
    vol_q80 = float(spy_vol21.quantile(0.80))

    all_frames = {name: eng[0](bars["open"], c, bars["volume"])
                  for name, eng in ENGINES.items()}
    positions = list(range(WARMUP, len(idx) - h - 1, step))
    print(f"{len(positions)} monthly entry dates, {idx[WARMUP].date()} .. "
          f"{idx[positions[-1]].date()}, {n_picks} picks/date, horizon {h} td")

    results = {}
    for name, (ff, comp) in ENGINES.items():
        frames = all_frames[name]
        windows = []
        for pos in positions:
            ts = idx[pos]
            snap = comp(frames, ts).drop(index=[REGIME_SYM], errors="ignore")
            if len(snap) < 50:
                continue
            top = list(snap.index[:n_picks])
            outcomes = _window_outcomes(c, pos, top, h)
            picks = [outcomes[s] for s in top if s in outcomes]
            if not picks:
                continue
            # equal-weight market over the identical window (full universe)
            mkt = _window_outcomes(c, pos, [s for s in c.columns
                                            if s != REGIME_SYM], h)
            if not mkt:
                continue
            regime = "bull" if bool(bull.iloc[pos]) else "bear"
            crash = regime == "bear" and float(spy_vol21.iloc[pos] or 0) > vol_q80
            windows.append({
                "date": str(ts.date()), "pos": pos, "regime": regime,
                "crash": crash, "picks": picks,
                "avg_end": float(np.mean([p["end"] for p in picks])),
                "mkt_end": float(np.mean([m["end"] for m in mkt.values()])),
            })
        nonoverlap = [w for i, w in enumerate(windows)
                      if i % max(1, round(h / step)) == 0]
        results[name] = {
            "all": _agg(windows),
            "non_crash": _agg([w for w in windows if not w["crash"]]),
            "bull": _agg([w for w in windows if w["regime"] == "bull"]),
            "bear": _agg([w for w in windows if w["regime"] == "bear"]),
            "non_overlapping": _agg(nonoverlap),
            "crash_dates_skipped_by_rule": sum(1 for w in windows if w["crash"]),
        }

    out = {"span": [str(idx[WARMUP].date()), str(idx[positions[-1]].date())],
           "picks_per_date": n_picks, "step_tdays": step,
           "horizon_tdays": h, "target": config.TARGET_GAIN,
           "label": "HIT = max close over next 42 trading days >= entry close * 1.05",
           "universe": "today's S&P 500 applied historically (survivorship)",
           "note": "monthly windows overlap (~2x); see non_overlapping for the "
                   "independent subset; compare engines to each other and to "
                   "avg_mkt_end_ret, not raw rates to the future",
           "engines": results}
    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")

    hdr = (f"{'engine':<8}{'dates':>6}{'hit%':>7}{'avg end%':>9}{'med peak%':>10}"
           f"{'med days':>9}{'dip%':>6}{'beat mkt':>10}{'mkt end%':>9}")
    for section in ("all", "non_crash", "non_overlapping", "bull", "bear"):
        print(f"\n[{section}]")
        print(hdr)
        for name in ENGINES:
            a = results[name][section]
            if not a:
                print(f"{name:<8}{'-':>6}")
                continue
            print(f"{name:<8}{a['dates']:>6}{a['hit_rate']:>7}{a['avg_end_ret']:>9}"
                  f"{a['med_max_gain']:>10}{str(a['med_days_to_hit']):>9}"
                  f"{a['dip_first_rate']:>6}{a['beat_market']:>10}"
                  f"{a['avg_mkt_end_ret']:>9}")
    print(f"\nwrote {RESULTS}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.backtest")
    ap.add_argument("--picks", type=int, default=5, help="picks per entry date")
    ap.add_argument("--step", type=int, default=21, help="trading days between entries")
    ap.add_argument("--no-cache", action="store_true", help="refetch bars")
    args = ap.parse_args()
    run(args.picks, args.step, args.no_cache)


if __name__ == "__main__":
    main()
