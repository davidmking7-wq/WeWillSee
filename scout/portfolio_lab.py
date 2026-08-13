"""Portfolio lab: measures the user's ACTUAL goal — does the PORTFOLIO
make >= +5% per 42-trading-day window, and how consistently?

!! READ THIS BEFORE QUOTING ANY NUMBER FROM HERE !!
The historical figures previously written into this prose predate the
next-open/cost/missing-data corrections and are retracted. Holds are 42 td and
scans are 21 td apart, so a non-overlapping run samples only one of several
possible entry schedules. This lab is still the right place to compare
strategies on a fixed schedule, but a new number may leave this file only after
the corrected run is pooled across every start phase:
    python -m scout.phase_lab --step 7 --sweep 1,2,3,5,8

Two strategy families over the v5 engine's rankings:

A. WINDOW: classic top-N equal-weight, held to the deadline, one window
   at a time (non-overlapping). Variants: N in {1,2,3,5}; bull_only
   (bear windows sit in cash — they count as 0% windows, shown apart).

B. ROLLING: the historical velocity variant — N slots; a qualifying close
   schedules an exit for the NEXT OPEN (target, disaster level, or deadline).
   After that fill, a vacancy can schedule the best-ranked name from the latest
   scan for a later next-open entry. There is no same-close dynamic fill.

Metrics are portfolio-level: avg per 42-td period, % of periods >= +5%
(the goal), % positive, worst period, daily max drawdown, compounded total.
Usage: python -m scout.portfolio_lab [--universe sp1500] [--start/--end]
"""
import argparse
import json
import math

import numpy as np
import pandas as pd

from . import backtest, config, execution, signals

H = config.HORIZON_TDAYS


def collect(mode, start, end, top=15, step=21, return_bars=False):
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
    return (bars, idx, scans) if return_bars else (c, idx, scans)


def metrics(rets, label_extra="", equity_curve=None):
    """Portfolio metrics, using daily equity for drawdown when supplied."""
    if not rets:
        return None
    curve = np.cumprod([1 + r for r in rets])
    dd_curve = list(equity_curve) if equity_curve is not None else curve
    return {
        "periods": len(rets),
        "avg": round(100 * float(np.mean(rets)), 2),
        "pct_ge5": round(100 * float(np.mean([r >= 0.05 for r in rets])), 1),
        "pct_pos": round(100 * float(np.mean([r > 0 for r in rets])), 1),
        "worst": round(100 * float(min(rets)), 1),
        "max_dd": round(100 * execution.max_drawdown(dd_curve), 1),
        "compounded": round(100 * float(curve[-1] - 1), 1),
        "note": label_extra,
        "drawdown_frequency": "daily" if equity_curve is not None else "period_end",
    }


def window_strategy(c, idx, scans, n, bull_only=False, *, open_prices=None,
                    assumptions=None, return_details=False):
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    if open_prices is None:
        if assumptions.entry_timing == "next_open":
            raise ValueError("next_open execution requires open_prices")
        open_prices = c
    stride = max(1, math.ceil(H / 21))
    rets = []
    curves = []
    cash = 0
    missing_entries = []
    partial_legs = []
    for scan in scans[::stride]:
        pos = scan["pos"]
        if bull_only and not scan["bull"]:
            rets.append(0.0)
            curves.append(np.ones(H + 1).tolist())
            cash += 1
            continue
        sim = execution.simulate_window(
            open_prices, c, pos, scan["ranked"][:n], H, assumptions,
        )
        curves.append(sim["equity"])
        rets.append(float(sim["equity"][-1] - 1))
        missing_entries.extend((scan["date"], s) for s in sim["missing_entries"])
        partial_legs.extend((scan["date"], s) for s in sim["partial_legs"])
    details = {
        "equity_curve": execution.stitch_curves(curves),
        "missing_entries": missing_entries,
        "partial_legs": partial_legs,
    }
    return (rets, cash, details) if return_details else (rets, cash)


def rolling_strategy(c, idx, scans, n, bull_only=False, *, open_prices=None,
                     assumptions=None, return_details=False):
    """Daily event-driven simulation with next-session fills and costs.

    Rankings observed at close ``t`` can only create orders for open ``t+1``.
    Positions are marked to their net liquidation value every close. Terminal
    quote disappearance follows the declared missing-leg policy and is logged.
    """
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    if open_prices is None:
        if assumptions.entry_timing == "next_open":
            raise ValueError("next_open execution requires open_prices")
        open_prices = c
    if assumptions.entry_timing != "next_open":
        raise ValueError("rolling_strategy only supports honest next_open fills")
    if not scans:
        return ([], {"equity_curve": [], "missing_entries": [],
                     "partial_legs": []}) if return_details else []

    scan_by_pos = {s["pos"]: s for s in scans}
    first = scans[0]["pos"]
    # Keep one extra session when available so a close-triggered exit can fill
    # at the following open instead of receiving an impossible same-close fill.
    last = min(scans[-1]["pos"] + H + 1, len(idx) - 1)
    side = assumptions.side_cost_rate
    cash = 1.0
    held = {}
    latest = None
    buy_queue = []
    sell_queue = []
    equity = []
    missing_entries = []
    partial_legs = []
    exit_fills = []

    for t in range(first, last + 1):
        # Exit decisions made after yesterday's close fill at today's open.
        # A missing open is treated as a pending order while later data exists;
        # otherwise the declared missing-leg policy resolves the stale holding.
        if sell_queue:
            still_pending = []
            for sym, reason, decision_date in sell_queue:
                if sym not in held:
                    continue
                p = held[sym]
                raw = open_prices.iloc[t].get(sym) if sym in open_prices.columns else np.nan
                if not pd.isna(raw) and raw > 0:
                    cash += p["shares"] * float(raw) * (1 - side)
                    exit_fills.append((decision_date, sym, reason, str(idx[t].date())))
                    del held[sym]
                    continue
                later_open = (
                    open_prices[sym].iloc[t + 1:last + 1]
                    if sym in open_prices.columns else pd.Series(dtype=float)
                )
                later_close = (
                    c[sym].iloc[t:last + 1]
                    if sym in c.columns else pd.Series(dtype=float)
                )
                if later_open.notna().any() or later_close.notna().any():
                    still_pending.append((sym, reason, decision_date))
                    continue
                partial_legs.append((p["signal_date"], sym, str(idx[t].date())))
                if assumptions.missing_leg_policy == "last_print":
                    cash += p["shares"] * p["last_px"] * (1 - side)
                del held[sym]
            sell_queue = still_pending

        # Entry decisions made after yesterday's close fill at today's open.
        if buy_queue:
            prior_equity = equity[-1] if equity else cash
            target = prior_equity / n
            for sym, sigma, signal_date in buy_queue:
                raw = open_prices.iloc[t].get(sym) if sym in open_prices.columns else np.nan
                if pd.isna(raw) or raw <= 0 or cash <= 0:
                    missing_entries.append((signal_date, sym, str(idx[t].date())))
                    continue
                allocation = min(target, cash)
                fill = float(raw) * (1 + side)
                held[sym] = {
                    "shares": allocation / fill, "allocation": allocation,
                    "entry_pos": t, "sigma": sigma, "last_px": float(raw),
                    "signal_date": signal_date,
                }
                cash -= allocation
            buy_queue = []

        row = c.iloc[t]
        pending_symbols = {item[0] for item in sell_queue}
        for sym in list(held):
            p = held[sym]
            px = row.get(sym)
            if pd.isna(px):
                deadline = t - p["entry_pos"] + 1 >= H
                future_close = (
                    c[sym].iloc[t + 1:last + 1]
                    if sym in c.columns else pd.Series(dtype=float)
                )
                future_open = (
                    open_prices[sym].iloc[t + 1:last + 1]
                    if sym in open_prices.columns else pd.Series(dtype=float)
                )
                if not deadline and (future_close.notna().any() or future_open.notna().any()):
                    continue
                partial_legs.append((p["signal_date"], sym, str(idx[t].date())))
                if assumptions.missing_leg_policy == "last_print":
                    cash += p["shares"] * p["last_px"] * (1 - side)
                del held[sym]
                continue
            px = float(px)
            p["last_px"] = px
            liquidation = p["shares"] * px * (1 - side)
            r = liquidation / p["allocation"] - 1
            hit = r >= config.TARGET_GAIN
            disaster = r <= -config.SELL_DISASTER_SIGMA * p["sigma"]
            deadline = t - p["entry_pos"] + 1 >= H
            if sym not in pending_symbols and (hit or disaster or deadline):
                reason = "target" if hit else "disaster" if disaster else "deadline"
                sell_queue.append((sym, reason, str(idx[t].date())))

        val = cash + sum(
            p["shares"] * p["last_px"] * (1 - side) for p in held.values()
        )
        equity.append(float(val))

        if t in scan_by_pos:
            latest = scan_by_pos[t]
        if latest is not None and not (bull_only and not latest["bull"]):
            needed = n - len(held)
            queued = set()
            for sym in latest["ranked"]:
                if needed <= 0:
                    break
                if sym in held or sym in queued:
                    continue
                queued.add(sym)
                buy_queue.append((sym, latest["sigma42"].get(sym) or 0.12,
                                  latest["date"]))
                needed -= 1

    rets = [float(equity[i] / equity[i - H] - 1)
            for i in range(H, len(equity), H)]
    details = {"equity_curve": equity, "missing_entries": missing_entries,
               "partial_legs": partial_legs, "exit_fills": exit_fills,
               "pending_exits": list(sell_queue)}
    return (rets, details) if return_details else rets


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.portfolio_lab")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    execution.add_execution_args(ap)
    args = ap.parse_args()
    assumptions = execution.from_args(args)

    bars, idx, scans = collect(args.universe, args.start, args.end,
                               return_bars=True)
    o, c = bars["open"], bars["close"]
    span = (str(idx[scans[0]["pos"]].date()), str(idx[scans[-1]["pos"]].date()))
    print(f"{len(scans)} scan dates {span[0]} .. {span[1]} ({args.universe})")
    out = {"span": span, "universe": args.universe,
           "execution": assumptions.metadata(), "strategies": {}}
    hdr = (f"{'strategy':<24}{'periods':>8}{'avg%':>7}{'>=+5%':>7}{'pos%':>6}"
           f"{'worst%':>8}{'maxDD%':>8}{'compounded%':>12}")
    print(hdr)
    for n in (1, 2, 3, 5):
        for bull_only in (False, True):
            rets, cash, details = window_strategy(
                c, idx, scans, n, bull_only, open_prices=o,
                assumptions=assumptions, return_details=True,
            )
            name = f"top{n}" + ("_bullonly" if bull_only else "")
            m = metrics(rets, f"{cash} cash windows" if bull_only else "",
                        equity_curve=details["equity_curve"])
            out["strategies"][name] = dict(
                m, missing_entries=len(details["missing_entries"]),
                partial_legs=len(details["partial_legs"]),
            )
            print(f"{name:<24}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
                  f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}"
                  f"{m['compounded']:>12}")
    for n in (3, 5):
        for bull_only in (False, True):
            rets, details = rolling_strategy(
                c, idx, scans, n, bull_only, open_prices=o,
                assumptions=assumptions, return_details=True,
            )
            name = f"roll{n}" + ("_bullonly" if bull_only else "")
            m = metrics(rets, equity_curve=details["equity_curve"])
            if m:
                out["strategies"][name] = dict(
                    m, missing_entries=len(details["missing_entries"]),
                    partial_legs=len(details["partial_legs"]),
                )
                print(f"{name:<24}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
                      f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}"
                      f"{m['compounded']:>12}")
    # SPY reference over the same non-overlapping periods.  Window averages
    # remain apples-to-apples, but the headline compounded path is a genuine
    # one-entry/one-exit buy-and-hold.  Rebuying SPY every 42 days would charge
    # it many artificial round trips and make the strategy comparison easier.
    stride = max(1, math.ceil(H / 21))
    spy_rets, spy_curves = [], []
    reference_scans = scans[::stride]
    for scan in reference_scans:
        pos = scan["pos"]
        sim = execution.simulate_window(o, c, pos, ["SPY"], H, assumptions)
        spy_curves.append(sim["equity"])
        spy_rets.append(float(sim["equity"][-1] - 1))
    reset_curve = execution.stitch_curves(spy_curves)
    first_pos = reference_scans[0]["pos"]
    continuous_horizon = reference_scans[-1]["pos"] + H - first_pos
    continuous = execution.simulate_window(
        o, c, first_pos, ["SPY"], continuous_horizon, assumptions,
    )["equity"]
    m = metrics(
        spy_rets,
        label_extra="window stats; compounding is continuous SPY buy-and-hold",
        equity_curve=continuous,
    )
    m["reset_every_42d_compounded"] = round(100 * (reset_curve[-1] - 1), 1)
    m["reset_every_42d_daily_max_dd"] = round(
        100 * execution.max_drawdown(reset_curve), 1,
    )
    out["strategies"]["SPY_continuous"] = m
    print(f"{'SPY continuous':<24}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
          f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}{m['compounded']:>12}")
    print("\nRESULT_JSON: " + json.dumps(out))


if __name__ == "__main__":
    main()
