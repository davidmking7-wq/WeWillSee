"""Walk-forward calibration: what actually happened, over 10 years, to stocks
that looked like today's candidates — how often they gained 5%+ (the user's
minimum bar), how MUCH they typically grew, how FAST, and how often they
dropped -5% first.

Tracking label (verbatim, used everywhere): HIT = max close over the next 42
trading days >= entry close * 1.05, entry = close on the signal date, window
starts the next trading day (first-passage definition).

Cells: score bucket × volatility tercile × regime. Volatility conditioning is
principled, not snooping: how far and how fast a stock can travel in 2 months
is mechanically driven by its volatility, so first-passage stats differ by
vol group even at the same score. Cells thinner than MIN_NEFF fall back to
bucket-level stats; still thinner -> no probability is quoted.

The calibration is tied to the signal engine that produced it: the cache
carries config.ENGINE and is discarded on mismatch, so swapping signals.py
can never silently reuse probability tables fitted to the old ranking.

Statistical honesty (see SCOUT-DESIGN.md): non-overlapping 42-day windows;
cluster bootstrap by DATE for CIs and n_eff; P(5%+) shrunk toward the regime
base rate; survivorship + single-era caveats stamped into the output.
"""
import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, data, signals, universe

REGIME_SYM = "SPY"



def bucket_of(rank_pct: float) -> str:
    if rank_pct >= 0.90:
        return "top10"
    if rank_pct >= 0.75:
        return "q4"
    if rank_pct >= 0.50:
        return "q3"
    if rank_pct >= 0.25:
        return "q2"
    return "q1"


def _cell_stats(bb: pd.DataFrame, base: float, rng) -> dict:
    """Aggregate one (regime, bucket[, tercile]) cell of outcome rows."""
    n = len(bb)
    p5_raw = float(bb["hit"].mean())
    g = bb.groupby("date_i")["hit"]
    hits_d, cnt_d = g.sum().values.astype(float), g.count().values.astype(float)
    nd = len(hits_d)
    if nd >= 2:
        pick = rng.integers(0, nd, size=(config.BOOT_REPS, nd))
        ps = hits_d[pick].sum(1) / cnt_d[pick].sum(1)
        lo, hi = (float(x) for x in np.percentile(ps, [2.5, 97.5]))
        se = float(ps.std())
    else:
        lo, hi, se = 0.0, 1.0, 0.5
    n_eff = min(float(n), p5_raw * (1 - p5_raw) / se**2) if se > 0 else n / 2
    p5 = (p5_raw * n_eff + base * config.SHRINK_K) / (n_eff + config.SHRINK_K)
    days = bb.loc[bb["hit"], "days_to_hit"]
    return {
        "p5_raw": round(p5_raw, 4), "p5": round(p5, 4),
        "p10": round(float(bb["hit10"].mean()), 4),
        "p15": round(float(bb["hit15"].mean()), 4),
        "pend5": round(float((bb["end_ret"] >= config.TARGET_GAIN).mean()), 4),
        "n": n, "n_eff": round(n_eff, 1), "n_dates": nd,
        "lo": round(lo, 4), "hi": round(hi, 4),
        "lift": round(p5 / base, 3) if base else None,
        "p_drop_first": round(float(bb["drop_first"].mean()), 4),
        "med_end_ret": round(float(bb["end_ret"].median()), 4),
        "med_max_gain": round(float(bb["max_ret"].median()), 4),
        # mean rewards fat right tails (5% is the minimum, not the goal);
        # winsorized at +50% so one moonshot can't own a thin cell
        "mean_max_gain": round(float(bb["max_ret"].clip(upper=0.50).mean()), 4),
        "p5_end_ret": round(float(bb["end_ret"].quantile(0.05)), 4),
        "med_days_to_hit": round(float(days.median()), 1) if len(days) else None,
    }


def run(force: bool = False) -> dict:
    path = config.CALIBRATION_JSON
    if path.exists() and not force:
        cal = json.loads(path.read_text(encoding="utf-8"))
        if cal.get("method") == "v3" and cal.get("engine") == config.ENGINE:
            age = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(cal["generated"])).days
            if age <= config.CALIB_STALE_DAYS:
                return cal
            print(f"calibration is {age} days old — refreshing...")
        else:
            print(f"cached calibration is for engine "
                  f"{cal.get('engine', 'v1')!r}, current is {config.ENGINE!r} "
                  "— rebuilding from scratch (old tables are invalid)...")

    from . import backtest      # local import: backtest shares the bar cache
    uni = universe.load()
    syms = sorted({u["symbol"] for u in uni} | {REGIME_SYM})
    print(f"calibrating: {config.CALIB_YEARS}y of SIP bars for {len(syms)} symbols "
          f"(takes a few minutes)...")
    bars = backtest.load_bars(mode="sp1500")
    c = bars["close"]
    frames = signals.feature_frames(bars["open"], c, bars["volume"])

    spy = c[REGIME_SYM].dropna()
    bull_series = spy > spy.rolling(200).mean()
    spy_vol21 = spy.pct_change().rolling(21).std() * math.sqrt(252)
    spy_vol_q80 = float(spy_vol21.quantile(0.80))

    h = config.HORIZON_TDAYS
    idx = c.index
    fwdmax = c.iloc[::-1].rolling(h, min_periods=h).max().iloc[::-1].shift(-1)
    hit_all = (fwdmax / c - 1) >= config.TARGET_GAIN
    valid_all = fwdmax.notna() & c.notna()

    records = []
    records_all = []
    date_i = -1
    for pos in range(270, len(idx) - h - 1, h):     # non-overlapping windows
        ts = idx[pos]
        if ts not in bull_series.index:
            continue
        snap = signals.composite_at(frames, ts).drop(index=[REGIME_SYM], errors="ignore")
        if len(snap) < 100:
            continue
        date_i += 1
        pct = snap["score"].rank(pct=True)
        terc = pd.cut(snap["vol"].rank(pct=True), [0, 1 / 3, 2 / 3, 1.01],
                      labels=["lowvol", "midvol", "highvol"])
        regime = "bull" if bool(bull_series.loc[ts]) else "bear"
        vmask = valid_all.loc[ts].drop(labels=[REGIME_SYM], errors="ignore")
        records_all.append((regime, int(hit_all.loc[ts][vmask.index][vmask].sum()),
                            int(vmask.sum())))
        basis = c.loc[ts]
        win = c.iloc[pos + 1: pos + 1 + h]
        for sym in snap.index:
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
            records.append((date_i, regime, bucket_of(float(pct[sym])),
                            str(terc[sym]), hit,
                            bool((r >= 1.10).any()),
                            bool((r >= 1.15).any()),
                            bool(dn.any() and first_dn < first_up),
                            float(r[-1] - 1), float(r.max() - 1),
                            first_up + 1 if hit else np.nan))

    df = pd.DataFrame(records, columns=["date_i", "regime", "bucket", "tercile",
                                        "hit", "hit10", "hit15", "drop_first",
                                        "end_ret", "max_ret", "days_to_hit"])
    if df.empty:
        raise RuntimeError("calibration produced no samples — check data fetch")

    rng = np.random.default_rng(42)
    regimes = {}
    for regime, sub in df.groupby("regime"):
        base = float(sub["hit"].mean())
        buckets = {}
        for b, bb in sub.groupby("bucket"):
            cell = _cell_stats(bb, base, rng)
            cell["terciles"] = {t: _cell_stats(tt, base, rng)
                                for t, tt in bb.groupby("tercile", observed=True)}
            buckets[b] = cell
        mkt = [(hits, cnt) for r, hits, cnt in records_all if r == regime]
        mkt_base = (sum(x for x, _ in mkt) / sum(x for _, x in mkt)) if mkt else None
        regimes[regime] = {"base_rate": round(base, 4),
                           "market_base_rate": round(mkt_base, 4) if mkt_base else None,
                           "n": len(sub),
                           "n_dates": int(sub["date_i"].nunique()), "buckets": buckets}

    cal = {"method": "v3", "engine": config.ENGINE,
           "generated": datetime.now(timezone.utc).isoformat(),
           "years": config.CALIB_YEARS, "n_dates": int(df["date_i"].nunique()),
           "span": [str(idx[270].date()), str(idx[len(idx) - h - 1].date())],
           "target": config.TARGET_GAIN, "horizon_tdays": h,
           "universe_size": len(syms) - 1,
           "spy_vol_q80": round(spy_vol_q80, 4),
           "label": "HIT = max close over next 42 trading days >= entry close * 1.05",
           "opp_score": "OppScore = 1000 * P(+5%) * MEAN max gain (winsorized "
                        "+50%) * (42 / median days to +5%) * (1 - P(-5% first)) "
                        "— assurance x profit x speed x safety, all empirical; "
                        "mean (not median) max gain because +5% is the minimum "
                        "bar and fat right tails deserve rank",
           "caveats": [
               "Calibrated on 2016-2026: a single macro era; bear-regime numbers "
               "rest on a handful of episodes (2018Q4, 2020, 2022) — treat them "
               "as rough context, not probabilities.",
               "Universe is today's S&P 500 applied historically (survivorship): "
               "raw P runs a few pp optimistic; rely on lift over base rate.",
               "Touching +5% at some point is not expected profit — see "
               "P(-5% first), P(end>=5%) and median day-42 growth.",
               "v3 engine gates (absolute momentum, lottery-spike veto) thin the "
               "bear-regime pool; expect more cells that refuse to quote a number.",
           ],
           "regimes": regimes}
    path.write_text(json.dumps(cal, indent=1), encoding="utf-8")
    print(f"calibration saved: {cal['n_dates']} non-overlapping dates, "
          f"{len(df)} stock-outcomes (engine {config.ENGINE})")
    return cal
