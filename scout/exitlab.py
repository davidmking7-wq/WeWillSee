"""Exit-rule lab: test sell rules over the v4 engine's picks, train/holdout.
NOT part of the shipped pipeline — a research harness like labtest.py.

Motivation (measured, train 2017-2021): misses average -6.2% because broken
momentum has no floor — 23% of misses end below -10%, 10% below -15%; and a
pick still down >5% at day 21 recovers to a hit only 25% of the time. But a
tight stop kills winners: 20% of eventual hits closed <=-5% before hitting.
The lab asks which sell rule cuts the loss tail without killing the runs.

All rules use CLOSES only (consistent with every other number in this
project) and sell AT the breaching close — no pretending you got out at the
stop level when the stock gapped through it. Day 42 is always the final exit.

Rule families (defined ex ante; levels vs the entry close):
  none          hold to day 42 (control)
  stopS         hard stop: first close <= entry*(1-S/100), S in 8/10/12/15/18
  timeD / timeD_L  time stop: at day D, sell if below entry (or entry*(1-L/100))
  combo         stop10 + time21
  2phase        pre-hit stop10; post-hit trail 5% below running peak close
  trailT        post-hit only: trail T% below running peak close (8/10)
  be_hit        post-hit only: breakeven floor — after touching +5%, sell on
                first close at/below entry (kills round-trippers)
  event7        sell on first single-day close-to-close drop <= -7% (crash exit)
  sma50         trend break: sell on first close below the stock's 50d SMA

Usage: python -m scout.exitlab [--start ...] [--end ...] [--picks 5 --step 21]
Prints a table + machine-readable RESULT_JSON line.
"""
import argparse
import json
import math

import numpy as np

from . import backtest, config, signals


def simulate(r: np.ndarray, rule: str, below_sma: np.ndarray | None = None,
             sigma42: float | None = None) -> float:
    """Realized return of one pick path under a rule. r = win/entry closes.
    sigma42 = the stock's own expected 42-day return volatility at entry
    (annualized 63d vol * sqrt(42/252)) — used by the vol-scaled rules."""
    n = len(r)
    if rule == "none":
        return r[-1] - 1

    if rule.startswith("vstop"):        # per-stock disaster stop: K x sigma42
        k = float(rule[5:]) / 100
        lvl = 1 - k * (sigma42 or 0.12)
        hitmask = r <= lvl
        return (r[np.argmax(hitmask)] if hitmask.any() else r[-1]) - 1

    if rule.startswith("vprot"):        # post-hit protect, trail J x sigma42
        j = float(rule[5:]) / 100
        trail = max(0.03, min(0.15, j * (sigma42 or 0.12)))
        hit, peak = False, r[0]
        for i in range(n):
            peak = max(peak, r[i])
            if not hit and r[i] >= 1.05:
                hit = True
            elif hit and r[i] <= max(1.00, peak * (1 - trail)):
                return r[i] - 1
        return r[-1] - 1

    if rule.startswith("stop"):
        lvl = 1 - int(rule[4:]) / 100
        hitmask = r <= lvl
        return (r[np.argmax(hitmask)] if hitmask.any() else r[-1]) - 1

    if rule.startswith("time"):
        # time21 -> day 21, below entry; time21_5 -> day 21, below entry*0.95
        parts = rule[4:].split("_")
        day = min(int(parts[0]), n) - 1
        lvl = 1 - (int(parts[1]) / 100 if len(parts) > 1 else 0)
        return (r[day] if r[day] < lvl else r[-1]) - 1

    if rule == "combo":
        day = min(21, n) - 1
        for i in range(n):
            if r[i] <= 0.90 or (i == day and r[i] < 1.00):
                return r[i] - 1
        return r[-1] - 1

    if rule == "2phase":
        hit, peak = False, r[0]
        for i in range(n):
            peak = max(peak, r[i])
            if not hit and r[i] >= 1.05:
                hit = True
            if not hit and r[i] <= 0.90:
                return r[i] - 1
            if hit and r[i] <= peak * 0.95:
                return r[i] - 1
        return r[-1] - 1

    if rule.startswith("trail"):
        t = 1 - int(rule[5:]) / 100
        hit, peak = False, r[0]
        for i in range(n):
            peak = max(peak, r[i])
            if not hit and r[i] >= 1.05:
                hit = True
            if hit and r[i] <= peak * t:
                return r[i] - 1
        return r[-1] - 1

    if rule == "be_hit":
        hit = False
        for i in range(n):
            if not hit and r[i] >= 1.05:
                hit = True
            elif hit and r[i] <= 1.00:
                return r[i] - 1
        return r[-1] - 1

    if rule == "protect":
        # combo of the two post-hit winners: after touching +5%, sell on the
        # first close at/below max(breakeven, peak - 8%)
        hit, peak = False, r[0]
        for i in range(n):
            peak = max(peak, r[i])
            if not hit and r[i] >= 1.05:
                hit = True
            elif hit and r[i] <= max(1.00, peak * 0.92):
                return r[i] - 1
        return r[-1] - 1

    if rule == "event7":
        prev = 1.0
        for i in range(n):
            if r[i] / prev - 1 <= -0.07:
                return r[i] - 1
            prev = r[i]
        return r[-1] - 1

    if rule == "sma50":
        if below_sma is None:
            return r[-1] - 1
        breach = np.argmax(below_sma) if below_sma.any() else None
        return (r[breach] if breach is not None else r[-1]) - 1

    raise ValueError(rule)


RULES = ("none", "stop8", "stop10", "stop12", "stop15", "stop18",
         "time21", "time21_5", "time21_8", "time30",
         "combo", "2phase", "trail8", "trail10", "be_hit", "protect",
         "event7", "sma50",
         # per-stock volatility-scaled levels (sigma42 = the stock's own
         # expected 42-day move): disaster stop at K x sigma42 below entry,
         # post-hit protect trailing J x sigma42 (breakeven floor, 3-15% clamp)
         "vstop100", "vstop125", "vstop150", "vstop200",
         "vprot40", "vprot60", "vprot80")


def collect_windows(picks: int, step: int, start, end, mode="sp500"):
    """One engine pass -> [(paths, smas, sigmas, spy_end)] per window."""
    bars = backtest.load_bars(mode=mode)
    c = bars["close"]
    idx = c.index
    h = config.HORIZON_TDAYS
    positions = backtest.positions_for(idx, start, end, step)
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    sma50 = c.rolling(50).mean()

    windows = []
    for pos in positions:
        snap = signals.composite_at(frames, idx[pos]).drop(index=["SPY"],
                                                           errors="ignore")
        if len(snap) < 50:
            continue
        basis = c.iloc[pos]
        win = c.iloc[pos + 1: pos + 1 + h]
        win_sma = sma50.iloc[pos + 1: pos + 1 + h]
        paths, smas, sigmas = [], [], []
        for sym in list(snap.index[:picks]):
            if sym not in win.columns or np.isnan(basis.get(sym, np.nan)):
                continue
            seg = (win[sym] / basis[sym]).dropna()
            if len(seg) < h:
                continue
            paths.append(seg.values)
            smas.append((win[sym] < win_sma[sym]).reindex(seg.index).fillna(False).values)
            ann_vol = float(frames["vol"].iloc[pos].get(sym, np.nan))
            sigmas.append(ann_vol * math.sqrt(h / 252) if np.isfinite(ann_vol) else None)
        spy = float(win["SPY"].iloc[-1] / basis["SPY"] - 1)
        if paths:
            windows.append((paths, smas, sigmas, spy))
    span = (str(idx[positions[0]].date()), str(idx[positions[-1]].date()))
    return windows, span


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.exitlab")
    ap.add_argument("--picks", type=int, default=5)
    ap.add_argument("--step", type=int, default=21)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--universe", default="sp500",
                    choices=["sp500", "pit500", "sp1500"])
    args = ap.parse_args()

    windows, span = collect_windows(args.picks, args.step, args.start,
                                    args.end, args.universe)
    n_picks = sum(len(p) for p, _, _, _ in windows)
    print(f"{len(windows)} windows, {n_picks} picks, {span[0]} .. {span[1]}")
    stride = max(1, math.ceil(config.HORIZON_TDAYS / args.step))
    out = {}
    hdr = (f"{'rule':<10}{'avg/win%':>9}{'compounded%':>12}{'tail<-10%':>10}"
           f"{'avg loser%':>11}{'hits killed':>12}{'worst pick%':>12}")
    print(hdr)
    for rule in RULES:
        per_win, allr = [], []
        killed = []
        for paths, smas, sigmas, _ in windows:
            rets = [simulate(r, rule, s, sig)
                    for r, s, sig in zip(paths, smas, sigmas)]
            per_win.append(float(np.mean(rets)))
            allr.extend(rets)
            killed.extend((r >= 1.05).any() and x < 0.0
                          for r, x in zip(paths, rets))
        losers = [x for x in allr if x < 0]
        comp = float(np.prod([1 + x for x in per_win[::stride]]) - 1)
        row = {"avg_per_window": round(100 * float(np.mean(per_win)), 2),
               "compounded": round(100 * comp, 1),
               "tail_below_10": round(100 * float(np.mean([x < -0.10 for x in allr])), 1),
               "avg_loser": round(100 * float(np.mean(losers)), 2) if losers else 0,
               "hits_killed": round(100 * float(np.mean(killed)), 1),
               "worst_pick": round(100 * float(min(allr)), 1)}
        out[rule] = row
        print(f"{rule:<10}{row['avg_per_window']:>9}{row['compounded']:>12}"
              f"{row['tail_below_10']:>10}{row['avg_loser']:>11}"
              f"{row['hits_killed']:>12}{row['worst_pick']:>12}")
    spys = [s for _, _, _, s in windows]
    spy_comp = float(np.prod([1 + s for s in spys[::stride]]) - 1)
    print(f"SPY same windows: avg {100*float(np.mean(spys)):+.2f}%/win, "
          f"compounded {100*spy_comp:+.1f}%")
    print("\nRESULT_JSON: " + json.dumps({"span": span, "rules": out}))


if __name__ == "__main__":
    main()
