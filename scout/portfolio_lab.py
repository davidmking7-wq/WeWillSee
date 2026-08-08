"""Portfolio lab: measures the user's ACTUAL goal — does the PORTFOLIO
make >= +5% per 42-trading-day window, and how consistently?

!! READ THIS BEFORE QUOTING ANY NUMBER FROM HERE !!
Holds are 42 td and scans are 21 td apart, so the non-overlapping run
below samples ONE of six possible entry schedules — and it happens to be
the luckiest one (+4.6%/window here vs +0.4% to +3.5% for the others; see
scout/phase_lab.py and BACKTEST-REPORT.md "Round 2"). Pooled across all
phases the honest figure is ~+2%/window at every book size. This lab is
still the right place to compare strategies against each other on a fixed
schedule, but any number that leaves this file must be pooled first:
    python -m scout.phase_lab --step 7 --sweep 1,2,3,5,8

Two strategy families over the v5 engine's rankings:

A. WINDOW: classic top-N equal-weight, held to the deadline, one window
   at a time (non-overlapping). Variants: N in {1,2,3,5}; bull_only
   (bear windows sit in cash — they count as 0% windows, shown apart).

B. ROLLING: the velocity strategy — N slots; each position sells the
   moment it CLOSES >= +5% over entry (or hits its per-stock disaster
   level, or its 42-td deadline) and the freed slot buys, at the NEXT
   close, the best-ranked name from the latest monthly scan not already
   held. Measures whether recycling fast winners compounds faster than
   holding to deadline.

Metrics are portfolio-level: avg per 42-td period, % of periods >= +5%
(the goal), % positive, worst period, max drawdown, compounded total.
Usage: python -m scout.portfolio_lab [--universe sp1500] [--start/--end]
"""
import argparse
import json
import math

import numpy as np
import pandas as pd

from . import backtest, config, signals

H = config.HORIZON_TDAYS


def collect(mode, start, end, top=15, step=21):
    """Monthly rankings + regime flags + close panel. In pit500 mode each
    date ranks ONLY that day's actual S&P 500 members (same one-row-slice
    technique as backtest.run_engine)."""
    from . import pit
    bars = backtest.load_bars(mode=mode)
    c = bars["close"]
    idx = c.index
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    spy = c["SPY"].dropna()
    bull = (spy > spy.rolling(200).mean()).reindex(idx)
    positions = backtest.positions_for(idx, start, end, step)
    scans = []
    for pos in positions:
        ts = idx[pos]
        if mode == "pit500":
            mem = pit.members(ts)
            cols = [s for s in c.columns if s in mem or s == "SPY"]
            day_frames = {k: f.loc[[ts], cols] for k, f in frames.items()}
            snap = signals.composite_at(day_frames, ts).drop(index=["SPY"],
                                                             errors="ignore")
        else:
            snap = signals.composite_at(frames, ts).drop(index=["SPY"],
                                                         errors="ignore")
        if len(snap) < 50:
            continue
        b = bull.iloc[pos]
        scans.append({"pos": pos,
                      "ranked": list(snap.index[:top]),
                      "sigma42": {s: float(snap.loc[s, "vol"]) * math.sqrt(H / 252)
                                  for s in snap.index[:top]},
                      "bull": bool(b) if not pd.isna(b) else True,
                      # extra ex-ante state used by regime_lab (H5e/H5f/H5g)
                      "pool": int(len(snap)),
                      "top_score": float(snap["score"].iloc[0]),
                      "date": str(ts.date())})
    return c, idx, scans


def metrics(rets, label_extra=""):
    """rets: one return per 42-td period (chronological)."""
    if not rets:
        return None
    curve = np.cumprod([1 + r for r in rets])
    peak = np.maximum.accumulate(curve)
    return {
        "periods": len(rets),
        "avg": round(100 * float(np.mean(rets)), 2),
        "pct_ge5": round(100 * float(np.mean([r >= 0.05 for r in rets])), 1),
        "pct_pos": round(100 * float(np.mean([r > 0 for r in rets])), 1),
        "worst": round(100 * float(min(rets)), 1),
        "max_dd": round(100 * float((curve / peak - 1).min()), 1),
        "compounded": round(100 * float(curve[-1] - 1), 1),
        "note": label_extra,
    }


def window_strategy(c, idx, scans, n, bull_only=False):
    stride = max(1, math.ceil(H / 21))
    rets = []
    cash = 0
    for scan in scans[::stride]:
        pos = scan["pos"]
        if bull_only and not scan["bull"]:
            rets.append(0.0)
            cash += 1
            continue
        basis = c.iloc[pos]
        win = c.iloc[pos + 1: pos + 1 + H]
        ends = []
        for sym in scan["ranked"][:n]:
            if sym not in win.columns or pd.isna(basis.get(sym)):
                continue
            seg = (win[sym] / basis[sym]).dropna()
            if len(seg) >= 5:
                ends.append(float(seg.values[-1] - 1))
        rets.append(float(np.mean(ends)) if ends else 0.0)
    return rets, cash


def rolling_strategy(c, idx, scans, n, bull_only=False):
    """Daily event-driven sim. Sell on close >= +5%, on close <= per-stock
    disaster (2 x sigma42), or at the 42-td deadline; refill next day from
    the latest scan's ranking (skip names already held). Cash earns 0."""
    if not scans:
        return []
    scan_by_pos = {s["pos"]: s for s in scans}
    first = scans[0]["pos"]
    last_exit = min(scans[-1]["pos"] + H + 1, len(idx) - 1)
    positions = {}          # sym -> {entry px, entry_pos, sigma, frac ($ at entry), last_r}
    pending = n             # slots waiting to buy at the next close
    cur = scans[0]
    weight = 1.0 / n
    cash_frac = 1.0         # all values in starting-capital units
    series = []
    for t in range(first, last_exit):
        if t in scan_by_pos:
            cur = scan_by_pos[t]
        row = c.iloc[t]
        # 1) mark to market + exits at today's close
        for sym in list(positions):
            p = positions[sym]
            px = row.get(sym)
            if pd.isna(px):
                if t - p["entry_pos"] > 3:      # delisted: exit at last mark
                    cash_frac += p["frac"] * (1 + p["last_r"])
                    del positions[sym]
                    pending += 1
                continue
            r = px / p["entry"] - 1
            p["last_r"] = r
            hit = r >= config.TARGET_GAIN
            disaster = r <= -config.SELL_DISASTER_SIGMA * p["sigma"]
            deadline = t - p["entry_pos"] >= H
            if hit or disaster or deadline:
                cash_frac += p["frac"] * (1 + r)
                del positions[sym]
                pending += 1
        # 2) portfolio value today
        val = cash_frac
        for sym, p in positions.items():
            px = row.get(sym)
            r = (px / p["entry"] - 1) if not pd.isna(px) else p["last_r"]
            val += p["frac"] * (1 + r)
        series.append(val)
        # 3) fill pending slots at today's close (orders decided yesterday)
        if pending and not (bull_only and not cur["bull"]):
            for sym in cur["ranked"]:
                if pending == 0:
                    break
                if sym in positions:
                    continue
                px = row.get(sym)
                sig = cur["sigma42"].get(sym)
                if pd.isna(px) or not sig:
                    continue
                frac = min(val * weight, cash_frac)
                if frac <= 0:
                    break
                positions[sym] = {"entry": float(px), "entry_pos": t,
                                  "sigma": sig, "frac": frac, "last_r": 0.0}
                cash_frac -= frac
                pending -= 1
    vals = np.array(series)
    rets = []
    for i in range(H, len(vals), H):
        rets.append(float(vals[i] / vals[i - H] - 1))
    return rets


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.portfolio_lab")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    c, idx, scans = collect(args.universe, args.start, args.end)
    span = (str(idx[scans[0]["pos"]].date()), str(idx[scans[-1]["pos"]].date()))
    print(f"{len(scans)} scan dates {span[0]} .. {span[1]} ({args.universe})")
    out = {"span": span, "universe": args.universe, "strategies": {}}
    hdr = (f"{'strategy':<24}{'periods':>8}{'avg%':>7}{'>=+5%':>7}{'pos%':>6}"
           f"{'worst%':>8}{'maxDD%':>8}{'compounded%':>12}")
    print(hdr)
    for n in (1, 2, 3, 5):
        for bull_only in (False, True):
            rets, cash = window_strategy(c, idx, scans, n, bull_only)
            name = f"top{n}" + ("_bullonly" if bull_only else "")
            m = metrics(rets, f"{cash} cash windows" if bull_only else "")
            out["strategies"][name] = m
            print(f"{name:<24}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
                  f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}"
                  f"{m['compounded']:>12}")
    for n in (3, 5):
        for bull_only in (False, True):
            rets = rolling_strategy(c, idx, scans, n, bull_only)
            name = f"roll{n}" + ("_bullonly" if bull_only else "")
            m = metrics(rets)
            if m:
                out["strategies"][name] = m
                print(f"{name:<24}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
                      f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}"
                      f"{m['compounded']:>12}")
    # SPY reference over the same non-overlapping periods
    stride = max(1, math.ceil(H / 21))
    spy_rets = []
    for scan in scans[::stride]:
        pos = scan["pos"]
        win = c.iloc[pos + 1: pos + 1 + H]["SPY"]
        spy_rets.append(float(win.iloc[-1] / c.iloc[pos]["SPY"] - 1))
    m = metrics(spy_rets)
    out["strategies"]["SPY"] = m
    print(f"{'SPY':<24}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
          f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}{m['compounded']:>12}")
    print("\nRESULT_JSON: " + json.dumps(out))


if __name__ == "__main__":
    main()
