"""Weekly loss forensics: WHY does a 5-day hold of good rankings lose?

weekly_lab.py established that it does (BACKTEST-REPORT.md, "Weekly holds").
This module answers the follow-up: the signals are real and validated, so
where does the money actually go? Three decompositions, in the order they
matter.

1. GEOMETRIC vs ARITHMETIC — how much is pure variance drain.
   A book can have a positive average week and still compound to a loss:
   geometric ~= arithmetic - sigma^2/2. Concentrated weekly books run a
   large sigma, so the drag is large. This separates "bad picks" from
   "fine picks, ruinous position sizing".

2. CAPM vs SPY — beta and alpha per week.
   If the book is high-beta and merely earns its beta, it is a leveraged
   index fund with extra steps. If alpha is negative, the selection itself
   is destroying value. These have completely different fixes.

3. DECILE MONOTONICITY AT BOTH HORIZONS — the decisive test.
   Split each week's eligible pool into deciles by composite rank and
   measure forward returns at 5 td AND 42 td from the same scan dates, the
   same universe, the same gates. If the ranking is monotone at 42 td and
   flat (or inverted) at 5 td, then nothing is wrong with the signals —
   they are being read at a horizon they do not speak to. That is a
   horizon-mismatch finding, not a broken-engine finding, and it is the
   difference between "throw this away" and "stop holding it for a week".

Note on overlap: the 42-td column is computed from weekly scan dates, so
those windows overlap ~8x. Overlap leaves the MEAN unbiased and inflates
only its precision, and the comparison here is between deciles measured
the same way — but do not quote a t-stat off the 42-td column.

Usage: python -m scout.weekly_forensics [--universe sp1500] [--entry open]
"""
from __future__ import annotations

import argparse
import json
import math
import pickle

import numpy as np
import pandas as pd

from . import backtest, config, weekly_lab

CACHE = config.SCOUT_DIR / "weekly_ranks_{}.pkl"


def load_weeks(universe: str, no_cache: bool = False):
    """Ranked weeks, cached — rank_weeks is the expensive step."""
    path = pd.io.common.Path(str(CACHE).format(universe))
    if path.exists() and not no_cache:
        with open(path, "rb") as f:
            weeks = pickle.load(f)
        print(f"ranked weeks from cache: {len(weeks)}")
        return weeks
    bars = backtest.load_bars(False, universe)
    slots = weekly_lab.week_slots(bars["close"].index)
    print(f"scoring {len(slots)} weeks (cached after this run)...")
    weeks = weekly_lab.rank_weeks(bars, slots, universe, top=25)
    with open(path, "wb") as f:
        pickle.dump(weeks, f)
    return weeks


def decompose(rets, spy):
    """Arithmetic vs geometric, and CAPM against SPY."""
    r = np.asarray(rets, dtype=float)
    s = np.asarray(spy, dtype=float)
    arith = float(r.mean())
    geo = float(np.exp(np.mean(np.log1p(r))) - 1)
    sd = float(r.std(ddof=1))
    beta = float(np.cov(r, s, ddof=1)[0, 1] / np.var(s, ddof=1))
    alpha = arith - beta * float(s.mean())
    resid = r - (alpha + beta * s)
    se_a = float(resid.std(ddof=2)) / math.sqrt(len(r))
    return {
        "arith_pct": round(100 * arith, 3),
        "geo_pct": round(100 * geo, 3),
        "drag_pct": round(100 * (arith - geo), 3),
        "sd_pct": round(100 * sd, 2),
        "beta": round(beta, 2),
        "alpha_pct": round(100 * alpha, 3),
        "t_alpha": round(alpha / se_a, 2) if se_a else 0.0,
        "ann_alpha_pct": round(100 * alpha * 52, 1),
    }


def decile_curves(bars, weeks, entry_basis, n_dec=10):
    """Forward return by composite-rank decile at 5 td and 42 td.

    `eligible` is already in descending score order, so decile 1 is the
    engine's best-ranked tenth of the surviving pool and decile 10 its worst.
    Both horizons start from the same entry bar, so the only difference
    between the columns is how long the position is held.
    """
    close = bars["close"]
    entry_frame = bars["open"] if entry_basis == "open" else close
    H = config.HORIZON_TDAYS
    acc = {d: {"wk": [], "h42": []} for d in range(1, n_dec + 1)}

    for wk in weeks:
        elig = wk["eligible"]
        if len(elig) < n_dec * 5:
            continue
        e_pos = wk["entry_pos"] if entry_basis == "open" else wk["scan_pos"]
        entry_row = entry_frame.iloc[e_pos]
        wk_row = close.iloc[wk["exit_pos"]]
        far = e_pos + H
        far_row = close.iloc[far] if far < len(close) else None

        bounds = np.array_split(np.arange(len(elig)), n_dec)
        for d, ix in enumerate(bounds, start=1):
            syms = [elig[i] for i in ix]
            e = entry_row.reindex(syms).astype(float)
            valid = e.notna() & (e > 0)
            if not valid.any():
                continue
            w = wk_row.reindex(syms).astype(float)
            acc[d]["wk"].append(float((w[valid] / e[valid] - 1).mean()))
            if far_row is not None:
                f = far_row.reindex(syms).astype(float)
                ok = valid & f.notna()
                if ok.any():
                    acc[d]["h42"].append(float((f[ok] / e[ok] - 1).mean()))
    return acc


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.weekly_forensics")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--entry", default="open", choices=["open", "close"])
    ap.add_argument("--cost-bps", type=float, default=10.0)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    bars = backtest.load_bars(False, args.universe)
    weeks = load_weeks(args.universe, args.no_cache)
    series, spy = weekly_lab.strategies(weeks, bars, args.entry, args.cost_bps)
    out = {"universe": args.universe, "entry": args.entry,
           "weeks": len(weeks), "decomposition": {}, "deciles": {}}

    print(f"\n{len(weeks)} weeks | universe {args.universe} | entry {args.entry}"
          f" | cost {args.cost_bps}bps\n")

    print("1. WHERE THE COMPOUNDING GOES (per week, %)")
    hdr = (f"{'strategy':<14}{'arith':>8}{'geo':>8}{'drag':>8}{'sd':>7}"
           f"{'beta':>7}{'alpha':>8}{'t(a)':>7}{'ann.alpha':>11}")
    print(hdr); print("-" * len(hdr))
    for name in ("top1", "top2", "top3", "top5", "top10", "voltilt3",
                 "random3", "eqw_eligible", "SPY"):
        if name not in series:
            continue
        d = decompose(series[name], spy)
        out["decomposition"][name] = d
        print(f"{name:<14}{d['arith_pct']:>8}{d['geo_pct']:>8}{d['drag_pct']:>8}"
              f"{d['sd_pct']:>7}{d['beta']:>7}{d['alpha_pct']:>8}"
              f"{d['t_alpha']:>7}{d['ann_alpha_pct']:>11}")

    print("\n2. DOES THE RANKING PREDICT? forward return by composite decile")
    print("   (decile 1 = engine's best-ranked tenth; same entry bar both cols)")
    acc = decile_curves(bars, weeks, args.entry)
    hdr = (f"{'decile':<9}{'5td fwd %':>12}{'42td fwd %':>13}"
           f"{'5td/day bp':>13}{'42td/day bp':>13}{'n':>7}")
    print(hdr); print("-" * len(hdr))
    for d in range(1, 11):
        wk = acc[d]["wk"]; h42 = acc[d]["h42"]
        if not wk:
            continue
        m_wk, m_42 = 100 * float(np.mean(wk)), 100 * float(np.mean(h42))
        out["deciles"][d] = {"wk_pct": round(m_wk, 3), "h42_pct": round(m_42, 3),
                             "n": len(wk)}
        print(f"{d:<9}{m_wk:>12.3f}{m_42:>13.3f}"
              f"{1e4 * m_wk / 100 / 5:>13.2f}{1e4 * m_42 / 100 / 42:>13.2f}"
              f"{len(wk):>7}")

    d1, d10 = out["deciles"].get(1), out["deciles"].get(10)
    if d1 and d10:
        print(f"\n   top-minus-bottom decile:  5td {d1['wk_pct'] - d10['wk_pct']:+.3f}%"
              f"   |   42td {d1['h42_pct'] - d10['h42_pct']:+.3f}%")
        print("   (a ranking that works shows a clear positive spread; one that")
        print("    is being read at the wrong horizon shows ~0 or negative)")

    path = config.SCOUT_DIR / f"weekly_forensics_{args.universe}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {path.name}")


if __name__ == "__main__":
    main()
