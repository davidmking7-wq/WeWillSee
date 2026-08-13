"""Earnings-timing labs (registry H2a, H2b). Research harness, not pipeline.

H2a — pre-earnings timing: does restricting the top-3 to candidates whose
NEXT real earnings date is 5-15 trading days ahead beat the standard
top-3? (Mechanism: the catalyst premium concentrates into the front half
of the window.) Caveat: uses realized announcement dates as the schedule;
dates that moved late create mild foresight — disclosed.

H2b — announcement-reaction drift (small/mid caps): after a 2-day
announcement reaction >= +5%, does the stock keep drifting over the next
42 td? (Mechanism: underreaction where algos don't price it instantly.)
Entry at the close of day e+1; liquidity-gated; negative-reaction cohort
reported as the mechanism's mirror. Segments are TODAY'S (disclosed).

Usage: python -m scout.pead_lab
"""
import json
import math

import numpy as np
import pandas as pd

from . import backtest, config, signals, universe

H = config.HORIZON_TDAYS


def earnings_positions(idx):
    emap = json.load(open(config.SCOUT_DIR / "earnings_history.json"))
    dates_np = np.array([str(d.date()) for d in idx.tz_localize(None)])
    ep = {}
    for sym, ds in emap.items():
        p = np.searchsorted(dates_np, np.array(sorted(ds)))
        ep[sym] = p[p < len(dates_np)]
    return ep


def wilson(p, n):
    if n == 0:
        return (0.0, 1.0)
    z = 1.96
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - s) / d, (c + s) / d)


def agg(rows, label):
    if not rows:
        return f"{label:<26} n=0"
    hits = np.mean([r["hit"] for r in rows])
    lo, hi = wilson(hits, len(rows))
    return (f"{label:<26} n={len(rows):>4}  hit {100*hits:5.1f}% "
            f"[{100*lo:.0f},{100*hi:.0f}]  avg end {100*np.mean([r['end'] for r in rows]):+6.2f}%  "
            f"tail<-10% {100*np.mean([r['end'] < -0.10 for r in rows]):4.1f}%")


def main() -> None:
    bars = backtest.load_bars(mode="sp1500")
    c = bars["close"]
    idx = c.index
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    ep = earnings_positions(idx)
    seg = {u["symbol"]: u.get("segment", "large") for u in universe.load()}
    halves = (("TRAIN 2017-2021", None, "2021-12-31"),
              ("HOLDOUT 2022-2026", "2022-01-01", None))

    print("=== H2a: top-3 timed to earnings 5-15 td ahead vs standard top-3 ===")
    for label, start, end in halves:
        positions = backtest.positions_for(idx, start, end, 21)
        std, timed = [], []
        for pos in positions:
            snap = signals.composite_at(frames, idx[pos]).drop(index=["SPY"],
                                                               errors="ignore")
            if len(snap) < 50:
                continue

            def outcome(sym):
                basis = c.iloc[pos]
                seg_p = (c.iloc[pos + 1: pos + 1 + H][sym] / basis[sym]).dropna()
                if len(seg_p) < H or pd.isna(basis.get(sym)):
                    return None
                r = seg_p.values
                return {"hit": bool((r >= 1.05).any()), "end": float(r[-1] - 1)}

            got = 0
            for sym in snap.index:
                o = outcome(sym) if sym in c.columns else None
                if o:
                    std.append(o)
                    got += 1
                if got == 3:
                    break
            got = 0
            for sym in snap.index:
                evs = ep.get(sym)
                if evs is None or not len(evs):
                    continue
                nxt = evs[(evs > pos)]
                if not len(nxt) or not (pos + 5 <= nxt[0] <= pos + 15):
                    continue
                o = outcome(sym) if sym in c.columns else None
                if o:
                    timed.append(o)
                    got += 1
                if got == 3:
                    break
        print(f"[{label}]")
        print(" " + agg(std, "standard top-3"))
        print(" " + agg(timed, "earnings-timed top-3"))

    print("\n=== H2b: announcement-reaction drift, mid/small caps ===")
    dvol = frames["dvol20"]
    for label, start, end in halves:
        lo_p = 0 if start is None else int(np.searchsorted(
            np.array([str(d.date()) for d in idx.tz_localize(None)]), start))
        hi_p = len(idx) if end is None else int(np.searchsorted(
            np.array([str(d.date()) for d in idx.tz_localize(None)]), end))
        pos_cohort, neg_cohort, spy_ref = [], [], []
        for sym, evs in ep.items():
            if seg.get(sym, "large") == "large" or sym not in c.columns:
                continue
            s = c[sym]
            for e in evs:
                e = int(e)
                if not (max(lo_p, 270) <= e < min(hi_p, len(idx) - H - 3)):
                    continue
                p_pre, p_post = s.iloc[e - 1], s.iloc[e + 1]
                dv = dvol.iloc[e][sym] if sym in dvol.columns else np.nan
                if any(pd.isna(x) for x in (p_pre, p_post)) or pd.isna(dv) \
                        or dv < config.MIN_DOLLAR_VOL:
                    continue
                react = p_post / p_pre - 1
                entry = s.iloc[e + 1]
                fwd = (s.iloc[e + 2: e + 2 + H] / entry).dropna()
                if len(fwd) < H:
                    continue
                r = fwd.values
                row = {"hit": bool((r >= 1.05).any()), "end": float(r[-1] - 1)}
                if react >= 0.05:
                    pos_cohort.append(row)
                    spy_ref.append(float(c["SPY"].iloc[e + 1 + H] / c["SPY"].iloc[e + 1] - 1))
                elif react <= -0.05:
                    neg_cohort.append(row)
        print(f"[{label}]")
        print(" " + agg(pos_cohort, "reaction >= +5% (buy)"))
        print(" " + agg(neg_cohort, "reaction <= -5% (mirror)"))
        if spy_ref:
            print(f" {'SPY same windows':<26} avg {100*np.mean(spy_ref):+6.2f}%")


if __name__ == "__main__":
    main()
