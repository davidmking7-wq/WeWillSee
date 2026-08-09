"""Phase lab: the portfolio backtest has always sampled ONE calendar
phase -- scans exist every 21 trading days and the non-overlapping run
takes every other one. The other phase is an equally valid, fully
independent set of windows that had never been looked at. This lab
(registry H7) runs every phase, then tests the LADDER: capital split
evenly across phases, so a fresh top-2 book starts every `step` trading
days instead of every 42.

Laddering is time diversification, not name dilution -- each sleeve
still holds only the top 2 of its own scan; it just stops mattering
which day of the cycle the account happened to start on. Name dilution
(top-3, top-5) was already tested and hurts.

Every sleeve is marked to market at every scan date, so all strategies
are measured on the SAME index set and the same span. Sleeves are not
rebalanced against each other -- that is what holding both books does.

--step must divide 42 (21 -> 2 phases, 14 -> 3, 7 -> 6).
Usage: python -m scout.phase_lab [--universe sp1500] [--n 2] [--step 21]

Any figures written in older reports are pre-correction artifacts. Re-run this
module with next-open execution and declared costs before citing a number.
"""
import argparse
import json
import math

import numpy as np
import pandas as pd

from . import config, execution, portfolio_lab

H = config.HORIZON_TDAYS


def book_return(o, c, scan, n, offset, assumptions=None):
    """Equal-weight top-n net return ``offset`` trading days after signal."""
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    sim = execution.simulate_window(
        o, c, scan["pos"], scan["ranked"][:n], offset, assumptions,
    )
    return float(sim["equity"][-1] - 1)


def sleeve_curve(o, c, by_pos, grid, n, offset, step, assumptions=None):
    """Daily equity for a sleeve on the shared span.

    The signal at an entry position fills at the next open under the default
    execution assumptions. Missing scans stay cash; missing selected legs keep
    their original weight through the shared execution module.

    Equity on the shared `grid` of trading-day positions for a sleeve
    that enters every 42 td starting at grid[0] + offset.

    Keyed on real trading-day positions, NOT on scan-list indices: the
    collector drops dates whose eligible pool is too thin, which would
    otherwise silently shift a sleeve onto a different phase. A missing
    scan at an entry date means that sleeve sits in cash for that block
    (counted and reported)."""
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    daily = list(range(grid[0], grid[-1] + 1))
    curve = {}
    cum, skipped = 1.0, 0
    first_entry = grid[0] + offset
    for entry in range(first_entry, grid[-1] + 1, H):
        scan = by_pos.get(entry)
        horizon = min(H, grid[-1] - entry)
        if horizon <= 0:
            continue
        if scan is None:
            path = np.ones(horizon + 1)
            skipped += 1
        else:
            path = np.asarray(execution.simulate_window(
                o, c, entry, scan["ranked"][:n], horizon, assumptions,
            )["equity"], dtype=float)
        for day, value in enumerate(path):
            curve[entry + day] = cum * float(value)
        cum *= float(path[-1])
    # Fill cash before the phase starts and any trailing positions not touched
    # by a complete block. A forward fill is safe because those spans are cash.
    last = 1.0
    for t in daily:
        if t in curve:
            last = curve[t]
        else:
            curve[t] = last
    return curve, skipped


def buy_hold_curve(o, c, symbol, signal_pos, end_pos, assumptions=None):
    """Daily net liquidation curve for one buy after ``signal_pos``."""
    assumptions = assumptions or execution.DEFAULT_EXECUTION
    horizon = end_pos - signal_pos
    leg = execution.simulate_leg(
        o, c, signal_pos, symbol, horizon, assumptions,
    )
    return {signal_pos + i: float(v) for i, v in enumerate(leg["path"])}


def sampled(curve, grid, per):
    """Non-overlapping 42-td returns of a curve on a fixed grid."""
    rets = []
    for a, b in zip(grid[:-per:per], grid[per::per]):
        if a in curve and b in curve and curve[a] > 0:
            rets.append(curve[b] / curve[a] - 1)
    return rets


HDR = (f"{'strategy':<30}{'periods':>8}{'avg%':>7}{'>=+5%':>7}{'pos%':>6}"
       f"{'worst%':>8}{'maxDD%':>8}{'compounded%':>12}")


def line(name, m, extra=""):
    return (f"{name:<30}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
            f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}"
            f"{m['compounded']:>12}  {extra}")


def streaks(rets):
    run = worst = 0
    for r in rets:
        run = run + 1 if r < 0.05 else 0
        worst = max(worst, run)
    return worst


def sweep(args, per):
    """H8: compare book sizes POOLED over every entry phase. The old
    top-N comparison used one phase only, which the phase spread shows is
    a coin flip; the pooled number is the one to trust."""
    assumptions = execution.from_args(args)
    bars, idx, scans = portfolio_lab.collect(
        args.universe, args.start, args.end, step=args.step, return_bars=True,
    )
    o, c = bars["open"], bars["close"]
    by_pos = {s["pos"]: s for s in scans}
    grid = list(range(scans[0]["pos"], scans[-1]["pos"] + 1, args.step))
    daily_grid = list(range(grid[0], grid[-1] + 1))
    print(f"\n{len(scans)} scans every {args.step} td, {per} entry phases, "
          f"{str(idx[grid[0]].date())} .. {str(idx[grid[-1]].date())} "
          f"({args.universe})\n")
    print(f"{'book':<8}{'phase avgs% (each an equally valid schedule)':<46}"
          f"{'POOLED avg%':>12}{'spread':>8}{'ladder comp%':>14}"
          f"{'worst%':>8}{'maxDD%':>8}{'>=+5%':>7}")
    out = {"execution": assumptions.metadata()}
    for n in [int(x) for x in args.sweep.split(",")]:
        curves = {p: sleeve_curve(o, c, by_pos, grid, n, p * args.step,
                                  args.step, assumptions)[0] for p in range(per)}
        avgs, comps = [], []
        for p in range(per):
            m = portfolio_lab.metrics(
                sampled(curves[p], grid, per),
                equity_curve=[curves[p][t] for t in daily_grid],
            )
            avgs.append(m["avg"])
            comps.append(m["compounded"])
        ladder = {t: float(np.mean([curves[p][t] for p in range(per)]))
                  for t in daily_grid}
        ml = portfolio_lab.metrics(
            sampled(ladder, grid, per),
            equity_curve=[ladder[t] for t in daily_grid],
        )
        out[f"top{n}"] = {"phase_avgs": avgs, "phase_compounded": comps,
                          "pooled_avg": round(float(np.mean(avgs)), 2),
                          "ladder": ml}
        print(f"top{n:<5}{' '.join(f'{a:>6.2f}' for a in avgs):<46}"
              f"{np.mean(avgs):>12.2f}{max(avgs)-min(avgs):>8.2f}"
              f"{ml['compounded']:>14}{ml['worst']:>8}{ml['max_dd']:>8}"
              f"{ml['pct_ge5']:>7}")
    spy = buy_hold_curve(o, c, "SPY", grid[0], grid[-1], assumptions)
    m = portfolio_lab.metrics(
        sampled(spy, grid, per), equity_curve=[spy[t] for t in daily_grid],
    )
    out["SPY"] = m
    print(f"{'SPY':<8}{'':<46}{m['avg']:>12}{'':>8}{m['compounded']:>14}"
          f"{m['worst']:>8}{m['max_dd']:>8}{m['pct_ge5']:>7}")
    print("\nRESULT_JSON: " + json.dumps(out))


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.phase_lab")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--step", type=int, default=21)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--sweep", default=None,
                    help="comma list of book sizes to compare POOLED across "
                         "phases, e.g. 1,2,3,5 (H8)")
    execution.add_execution_args(ap)
    args = ap.parse_args()
    assumptions = execution.from_args(args)
    if H % args.step:
        raise SystemExit(f"--step must divide {H}")
    per = H // args.step          # scans per holding period = number of phases

    if args.sweep:
        return sweep(args, per)

    bars, idx, scans = portfolio_lab.collect(
        args.universe, args.start, args.end, step=args.step, return_bars=True,
    )
    o, c = bars["open"], bars["close"]
    by_pos = {s["pos"]: s for s in scans}
    # shared time grid: every `step` trading days, whether or not a scan
    # survived the pool filter there
    grid = list(range(scans[0]["pos"], scans[-1]["pos"] + 1, args.step))
    daily_grid = list(range(grid[0], grid[-1] + 1))
    n_missing = sum(1 for t in grid if t not in by_pos)
    print(f"\n{len(scans)} scans every {args.step} td, {scans[0]['date']} .. "
          f"{scans[-1]['date']} ({args.universe}), top-{args.n}, "
          f"{per} phases"
          f"{f'  [{n_missing} grid dates had too thin a pool]' if n_missing else ''}\n")
    dt = {t: str(idx[t].date()) for t in grid}

    curves, skips = {}, {}
    for p in range(per):
        curves[p], skips[p] = sleeve_curve(
            o, c, by_pos, grid, args.n, p * args.step, args.step, assumptions,
        )
    ladder = {t: float(np.mean([curves[p][t] for p in range(per)]))
              for t in daily_grid}

    out = {"universe": args.universe, "n": args.n, "step": args.step,
           "phases": per, "span": [dt[grid[0]], dt[grid[-1]]],
           "execution": assumptions.metadata(),
           "strategies": {}}
    print(f"=== EACH PHASE ALONE vs THE LADDER "
          f"(identical span {out['span'][0]} .. {out['span'][1]}) ===")
    print(HDR)
    comps = []
    for p in range(per):
        r = sampled(curves[p], grid, per)
        m = portfolio_lab.metrics(
            r, equity_curve=[curves[p][t] for t in daily_grid],
        )
        comps.append(m["compounded"])
        out["strategies"][f"phase{p}"] = dict(m, cash_blocks=skips[p])
        print(line(f"phase {p} (entry +{p*args.step}td)", m,
                   f"dry run {streaks(r)}"
                   + (f", {skips[p]} cash blocks" if skips[p] else "")))
    lr = sampled(ladder, grid, per)
    ml = portfolio_lab.metrics(
        lr, equity_curve=[ladder[t] for t in daily_grid],
    )
    out["strategies"]["ladder"] = ml
    print(line(f"LADDER ({per} sleeves)", ml, f"dry run {streaks(lr)}"))
    print(f"\nphase spread on compounded: best {max(comps):.1f}% vs worst "
          f"{min(comps):.1f}%  (spread {max(comps)-min(comps):.1f}pp)"
          f" | mean of phases {np.mean(comps):.1f}%")

    spy = buy_hold_curve(o, c, "SPY", grid[0], grid[-1], assumptions)
    m_spy = portfolio_lab.metrics(
        sampled(spy, grid, per), equity_curve=[spy[t] for t in daily_grid],
    )
    out["strategies"]["SPY"] = m_spy
    print(line("SPY (same span)", m_spy))

    half = len(grid) // 2
    for tag, sl in (("FIRST HALF", slice(0, half + 1)),
                    ("SECOND HALF", slice(half, None))):
        ks = grid[sl]
        print(f"\n=== {tag} ({dt[ks[0]]} .. {dt[ks[-1]]}) ===")
        print(HDR)
        for p in range(per):
            lo, hi = ks[0], ks[-1]
            m = portfolio_lab.metrics(
                sampled(curves[p], ks, per),
                equity_curve=[curves[p][t] for t in range(lo, hi + 1)],
            )
            if m:
                out["strategies"][f"phase{p}"][tag.lower().replace(" ", "_")] = m
                print(line(f"phase {p} (entry +{p*args.step}td)", m))
        m = portfolio_lab.metrics(
            sampled(ladder, ks, per),
            equity_curve=[ladder[t] for t in range(ks[0], ks[-1] + 1)],
        )
        if m:
            out["strategies"]["ladder"][tag.lower().replace(" ", "_")] = m
            print(line(f"LADDER ({per} sleeves)", m))

    print("\nRESULT_JSON: " + json.dumps(out))


if __name__ == "__main__":
    main()
