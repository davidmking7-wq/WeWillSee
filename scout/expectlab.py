"""Expectation-based exit lab: sell rules driven by what we EXPECT from
each specific pick — its cell's typical days-to-+5%, typical peak gain —
rather than one-size-fits-all levels. NOT part of the shipped pipeline.

Anti-lookahead design: each pick's expectations come from a stats table
built ONLY from TRAIN-period picks (2017-2021), grouped exactly like the
calibration (score bucket x vol tercile x regime, all entry-time
information). Train evaluation is therefore partly in-sample for the
expectations (disclosed); the HOLDOUT evaluation applies train-frozen
expectations to unseen outcomes — that is the number that counts.
NOTE: the 2022-2026 holdout has been consulted by earlier labs; its
confirmations are weaker than fresh data. Disclosed in the report.

Rule stacks (grids declared ex ante; base "ship" = the currently shipped
discipline: disaster stop at 2 x sigma42 + post-hit breakeven floor):
  none            hold to day 42
  ship            vstop200 + be_hit (control to beat)
  ship+TB{M}      time budget: if NOT yet +5% by ceil(M x expected days
                  to +5%) and below entry -> sell (M = 1.5, 2.0, 3.0).
                  A 12-expected-day stock flat at day 24 is dead money BY
                  ITS OWN standards; an 18-day stock gets more patience.
  ship+TAKE{T}    take-profit at T x expected peak gain (T = 1.00, 1.25):
                  sell on first close >= entry x (1 + T x exp_peak).
  ship+PP         peak-protect: once the pick EXCEEDS its expected peak,
                  sell on a close 0.5 x sigma42 below its best close —
                  it already did what stocks like it do; guard the win.
  ship+TB20+PP    the combined candidate.

Usage: python -m scout.expectlab   (train + holdout tables in one run)
"""
import json
import math

import numpy as np
import pandas as pd

from . import backtest, config, signals
from .calibrate import bucket_of

H = config.HORIZON_TDAYS
TRAIN_END = "2021-12-31"
HOLD_START = "2022-01-01"


def collect(start, end):
    """Picks with entry-time cell keys, sigma42, and full paths."""
    bars = backtest.load_bars()
    c = bars["close"]
    idx = c.index
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    spy = c["SPY"].dropna()
    bull = (spy > spy.rolling(200).mean()).reindex(idx)
    positions = backtest.positions_for(idx, start, end, 21)
    picks = []
    for pos in positions:
        snap = signals.composite_at(frames, idx[pos]).drop(index=["SPY"],
                                                           errors="ignore")
        if len(snap) < 50:
            continue
        pct = snap["score"].rank(pct=True)
        terc = pd.cut(snap["vol"].rank(pct=True), [0, 1 / 3, 2 / 3, 1.01],
                      labels=["lowvol", "midvol", "highvol"])
        regime = "bull" if bool(bull.iloc[pos]) else "bear"
        basis = c.iloc[pos]
        win = c.iloc[pos + 1: pos + 1 + H]
        spy_end = float(win["SPY"].iloc[-1] / basis["SPY"] - 1)
        for sym in list(snap.index[:5]):
            if sym not in win.columns or np.isnan(basis.get(sym, np.nan)):
                continue
            r = (win[sym] / basis[sym]).dropna().values
            if len(r) < H:
                continue
            up = r >= 1.05
            hit = bool(up.any())
            picks.append({
                "pos": pos, "cell": (regime, bucket_of(float(pct[sym])),
                                     str(terc[sym])),
                "sigma42": float(snap.loc[sym, "vol"]) * math.sqrt(H / 252),
                "r": r, "spy": spy_end, "hit": hit,
                "days": int(np.argmax(up)) + 1 if hit else None,
                "max": float(r.max() - 1), "end": float(r[-1] - 1),
            })
    return picks


def build_expectations(train_picks):
    """(regime,bucket,tercile) -> {exp_days, exp_peak}; bucket- and
    global-level fallbacks for thin cells (min 15 picks)."""
    def stats(sub):
        days = [p["days"] for p in sub if p["days"]]
        return {"exp_days": float(np.median(days)) if days else None,
                "exp_peak": float(np.mean([min(p["max"], 0.50) for p in sub]))}

    table, fallback = {}, {}
    groups = {}
    for p in train_picks:
        groups.setdefault(p["cell"], []).append(p)
        groups.setdefault(p["cell"][:2], []).append(p)   # bucket level
    for key, sub in groups.items():
        if len(sub) >= 15:
            table[key] = stats(sub)
    fallback = stats(train_picks)
    return table, fallback


def expect_for(pick, table, fallback):
    e = table.get(pick["cell"]) or table.get(pick["cell"][:2]) or fallback
    if e["exp_days"] is None:
        e = dict(e, exp_days=fallback["exp_days"])
    return e


def simulate(pick, e, tb=None, take=None, pp=False, ship=True):
    """One pick under a rule stack. Sells at the triggering close."""
    r, s42 = pick["r"], pick["sigma42"]
    disaster = 1 - 2.0 * s42
    tb_day = int(math.ceil(tb * e["exp_days"])) if tb else None
    take_lvl = 1 + take * e["exp_peak"] if take else None
    pp_armed = False
    hit = False
    peak = r[0]
    for i in range(len(r)):
        x = r[i]
        peak = max(peak, x)
        if not hit and x >= 1.05:
            hit = True
        if ship and x <= disaster:
            return x - 1                      # per-stock disaster stop
        if take_lvl and x >= take_lvl:
            return x - 1                      # take-profit at T x exp peak
        if pp:
            if not pp_armed and x >= 1 + e["exp_peak"]:
                pp_armed = True
            elif pp_armed and x <= peak - 0.5 * s42:
                return x - 1                  # guard an above-expectation win
        if ship and hit and x <= 1.00:
            return x - 1                      # breakeven floor after +5%
        if tb_day and not hit and i + 1 >= tb_day and x < 1.00:
            return x - 1                      # out of its own time budget
    return r[-1] - 1


STACKS = {
    "none": {"ship": False},
    "ship": {},
    "ship+TB15": {"tb": 1.5},
    "ship+TB20": {"tb": 2.0},
    "ship+TB30": {"tb": 3.0},
    "ship+TAKE100": {"take": 1.00},
    "ship+TAKE125": {"take": 1.25},
    "ship+PP": {"pp": True},
    "ship+TB20+PP": {"tb": 2.0, "pp": True},
}


def evaluate(picks, table, fallback, step=21):
    stride = max(1, math.ceil(H / step))
    out = {}
    for name, kw in STACKS.items():
        by_win = {}
        allr, killed = [], []
        for p in picks:
            x = simulate(p, expect_for(p, table, fallback), **kw)
            by_win.setdefault(p["pos"], []).append(x)
            allr.append(x)
            killed.append(p["hit"] and x < 0)
        per = [float(np.mean(v)) for v in by_win.values()]
        losers = [x for x in allr if x < 0]
        out[name] = {
            "avg_per_window": round(100 * float(np.mean(per)), 2),
            "compounded": round(100 * (float(np.prod([1 + x for x in per[::stride]])) - 1), 1),
            "tail_below_10": round(100 * float(np.mean([x < -0.10 for x in allr])), 1),
            "avg_loser": round(100 * float(np.mean(losers)), 2) if losers else 0,
            "hits_killed": round(100 * float(np.mean(killed)), 1),
            "worst_pick": round(100 * float(min(allr)), 1),
        }
    return out


def main() -> None:
    train = collect(None, TRAIN_END)
    hold = collect(HOLD_START, None)
    table, fallback = build_expectations(train)
    print(f"train {len(train)} picks, holdout {len(hold)} picks, "
          f"{len(table)} expectation cells "
          f"(global exp_days {fallback['exp_days']:.0f}td, "
          f"exp_peak {fallback['exp_peak']:.1%})")
    results = {}
    for label, picks in (("train(exp in-sample)", train),
                         ("HOLDOUT(exp frozen)", hold)):
        res = evaluate(picks, table, fallback)
        results[label] = res
        print(f"\n[{label}]")
        print(f"{'stack':<14}{'avg/win%':>9}{'compounded%':>12}{'tail<-10%':>10}"
              f"{'avg loser%':>11}{'hits killed':>12}{'worst%':>8}")
        for name, a in res.items():
            print(f"{name:<14}{a['avg_per_window']:>9}{a['compounded']:>12}"
                  f"{a['tail_below_10']:>10}{a['avg_loser']:>11}"
                  f"{a['hits_killed']:>12}{a['worst_pick']:>8}")
        spys = {}
        for p in picks:
            spys[p["pos"]] = p["spy"]
        vals = list(spys.values())
        stride = max(1, math.ceil(H / 21))
        print(f"SPY same windows: avg {100*float(np.mean(vals)):+.2f}%/win, "
              f"compounded {100*(float(np.prod([1+x for x in vals[::stride]]))-1):+.1f}%")
    print("\nRESULT_JSON: " + json.dumps(results))


if __name__ == "__main__":
    main()
