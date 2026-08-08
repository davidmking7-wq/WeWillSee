"""Gates lab: is the VALUE in the gates rather than the ranking?

weekly_forensics established two things: the eligible pool carries roughly
market-like alpha (-1.5%/yr) while the ranking inside it carries about
-10%/yr, and the composite's decile 1 is the WORST-performing tenth at both
5 td and 42 td. That is the v2 finding ("composite rank shows ~no lift over
the gated base rate") confirmed on ten years. It leaves one question the
repo has never isolated:

    Hold everything that passes the gates, equal-weighted, for a long
    horizon. Does THAT beat SPY?

THE CONTROL THAT DECIDES IT
---------------------------
`ungated_eqw` — equal-weight the entire universe, no gates at all. Without
it the lab is uninterpretable, because equal-weighting the S&P 1500 is
itself a size/mid-cap tilt, and that tilt has its own well-documented
premium. If gated_eqw beats SPY but ungated_eqw beats SPY by the same
amount, the gates contributed NOTHING and the result is the size factor
wearing a costume. The comparison that matters is gated vs ungated, not
gated vs SPY.

WHICH GATE, IF ANY, EARNS ITS PLACE
-----------------------------------
Leave-one-out ablation: rerun with each gate removed in turn. A gate that
matters shows a WORSE portfolio when dropped. A gate whose removal changes
nothing is decoration, and a gate whose removal IMPROVES things is a cost.
The gates are sma200, absolute momentum (ret6>0), the 1-month extremes
veto, the top-vol-decile veto, the lottery-spike (max21) veto, and the
liquidity floor.

COSTS ARE TURNOVER-BASED, NOT A FLAT CHARGE
-------------------------------------------
Long-horizon equal weight has far lower turnover than the weekly rotation,
and charging both the same flat fee would be dishonest in this lab's
favour. Actual name-level turnover between consecutive rebalances is
measured and charged at --cost-bps per unit turned over.

Usage:
  python -m scout.gates_lab [--universe sp1500|pit500] [--rebal 21,42,63,126]
                            [--cost-bps 10]
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np
import pandas as pd

from . import backtest, config, signals

TD_YEAR = 252

# Every hard gate in signals.composite_at, individually droppable.
GATES = ("sma200", "absmom", "ret1m_hi", "ret1m_lo", "vol_decile",
         "max21_decile", "liquidity")


def gate_mask(frames, ts, drop: str | None = None, cols=None) -> list[str]:
    """Symbols passing the engine's hard gates at `ts`, optionally with one
    gate dropped. Mirrors signals.composite_at's `keep` expression exactly —
    if that changes, this must change with it (and config.ENGINE bumps)."""
    row = {k: f.loc[ts] for k, f in frames.items()}
    df = pd.DataFrame(row)
    if cols is not None:
        df = df.loc[df.index.intersection(cols)]
    df = df.dropna(subset=["mom", "mom6", "high", "vol", "ret1m", "max21",
                           "pos252", "brk20"])
    if df.empty:
        return []

    vol_decile = df["vol"].rank(pct=True)
    max_decile = df["max21"].rank(pct=True)
    checks = {
        "sma200": df["sma200ok"] == 1.0,
        "absmom": df["ret6"] > 0,
        "ret1m_hi": df["ret1m"] <= config.VETO_RET1M_HI,
        "ret1m_lo": df["ret1m"] >= config.VETO_RET1M_LO,
        "vol_decile": vol_decile < config.VETO_VOL_DECILE,
        "max21_decile": max_decile < config.VETO_MAX21_DECILE,
        "liquidity": df["dvol20"] >= config.MIN_DOLLAR_VOL,
    }
    keep = pd.Series(True, index=df.index)
    for name, cond in checks.items():
        if name != drop:
            keep &= cond
    return list(df.index[keep])


def period_return(close, t0, t1, syms):
    """Equal-weight return t0 -> t1, plus the per-name returns.

    A name that stops printing exits at its last available bar (delisting:
    the collapse or the buyout is already in the final prints) rather than
    being silently dropped, which would quietly delete failures."""
    if not syms:
        return None, [], {}
    entry = close.iloc[t0].reindex(syms).astype(float)
    win = close.iloc[t0 + 1: t1 + 1].reindex(columns=syms)
    if win.empty:
        return None, [], {}
    last = win.ffill().iloc[-1]
    ok = entry.notna() & (entry > 0) & last.notna()
    if not ok.any():
        return None, [], {}
    held = [s for s in syms if bool(ok.get(s, False))]
    legs = (last[ok] / entry[ok] - 1)
    return float(legs.mean()), held, {s: float(legs[s]) for s in held}


def rebalance_turnover(prev_held, prev_legs, cur_held) -> float:
    """TWO-WAY turnover to move a drifted equal-weight book onto the new
    equal-weight target: 0.5 * sum |w_target - w_drifted|.

    Measuring only newly-entering names (the obvious shortcut) reports ~1%
    for a book whose membership barely changes, and thereby charges almost
    no cost for restoring equal weights across ~1500 drifted positions —
    which flatters exactly the strategy this lab is trying to control for.
    """
    if not prev_held:
        return 1.0
    w_prev = {s: (1.0 + prev_legs.get(s, 0.0)) / len(prev_held) for s in prev_held}
    tot = sum(w_prev.values())
    if tot <= 0:
        return 1.0
    w_prev = {s: w / tot for s, w in w_prev.items()}
    w_tgt = 1.0 / max(len(cur_held), 1)
    names = set(w_prev) | set(cur_held)
    diff = sum(abs((w_tgt if s in cur_held else 0.0) - w_prev.get(s, 0.0))
               for s in names)
    return 0.5 * diff


def run_strategy(close, frames, points, drop=None, gated=True, cost_bps=10.0,
                 pit_cols=None):
    """Compound one strategy across the rebalance points.

    Returns (rets, turns, used) where `used` are the indices into `points`
    that actually produced a return. Callers MUST align the benchmark to
    `used` — skipped periods would otherwise shift the two series against
    each other and compare returns from different dates.
    """
    rets, turns, used = [], [], []
    prev_held, prev_legs = [], {}
    for i, (t0, t1) in enumerate(points):
        ts = close.index[t0]
        cols = pit_cols(ts) if pit_cols else None
        if gated:
            syms = gate_mask(frames, ts, drop=drop, cols=cols)
        else:
            row = close.iloc[t0]
            syms = list(row[row.notna()].index)
            if cols is not None:
                syms = [s for s in syms if s in cols]
        syms = [s for s in syms if s != backtest.REGIME_SYM]
        if len(syms) < 20:
            continue
        r, held, legs = period_return(close, t0, t1, syms)
        if r is None:
            continue
        tv = rebalance_turnover(prev_held, prev_legs, held)
        turns.append(tv)
        rets.append(r - tv * cost_bps / 10_000.0)
        used.append(i)
        prev_held, prev_legs = held, legs
    return rets, turns, used


def stats(rets, spy_rets, periods_per_year):
    """`spy_rets` MUST already be aligned to the same periods as `rets`
    (see run_strategy's `used`). Truncating instead of aligning is how a
    skipped period silently offsets the two series."""
    if not rets:
        return None
    r = np.asarray(rets, float)
    s = np.asarray(spy_rets, float)
    if len(s) != len(r):
        raise ValueError(f"benchmark misaligned: {len(r)} strategy periods "
                         f"vs {len(s)} benchmark periods")
    curve = np.cumprod(1 + r)
    peak = np.maximum.accumulate(curve)
    years = len(r) / periods_per_year
    cagr = float(curve[-1] ** (1 / years) - 1)
    vol = float(r.std(ddof=1) * math.sqrt(periods_per_year))
    beta = float(np.cov(r, s, ddof=1)[0, 1] / np.var(s, ddof=1))
    alpha_p = float(r.mean() - beta * s.mean())
    return {
        "periods": len(r),
        "cagr_pct": round(100 * cagr, 2),
        "vol_pct": round(100 * vol, 2),
        "sharpe": round(cagr / vol, 2) if vol else 0.0,
        "max_dd_pct": round(100 * float((curve / peak - 1).min()), 1),
        "beta": round(beta, 2),
        "ann_alpha_pct": round(100 * alpha_p * periods_per_year, 2),
        "beat_spy_pct": round(100 * float(np.mean(r > s)), 1),
        "total_pct": round(100 * float(curve[-1] - 1), 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.gates_lab")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--rebal", default="21,42,63,126",
                    help="comma-separated rebalance intervals in trading days")
    ap.add_argument("--cost-bps", type=float, default=10.0)
    args = ap.parse_args()

    bars = backtest.load_bars(False, args.universe)
    close = bars["close"]
    frames = signals.feature_frames(bars["open"], close, bars["volume"])
    idx = close.index

    pit_cols = None
    if args.universe == "pit500":
        from . import pit
        pit_cols = lambda ts: set(pit.members(ts)) | {backtest.REGIME_SYM}

    out = {"universe": args.universe, "cost_bps": args.cost_bps,
           "engine": config.ENGINE, "by_rebal": {}}

    for step in [int(x) for x in args.rebal.split(",")]:
        pts = [(t, min(t + step, len(idx) - 1))
               for t in range(backtest.WARMUP, len(idx) - step - 1, step)]
        if len(pts) < 12:
            continue
        ppy = TD_YEAR / step
        spy_rets = [float(close.iloc[t1][backtest.REGIME_SYM]
                          / close.iloc[t0][backtest.REGIME_SYM] - 1)
                    for t0, t1 in pts]

        print(f"\n=== rebalance every {step} td "
              f"({len(pts)} periods, {idx[pts[0][0]].date()} .. "
              f"{idx[pts[-1][1]].date()}) ===")
        hdr = (f"{'strategy':<20}{'CAGR%':>8}{'vol%':>7}{'Sharpe':>8}"
               f"{'maxDD%':>8}{'beta':>6}{'annAlpha%':>11}{'>SPY%':>7}"
               f"{'total%':>9}{'turn%':>7}")
        print(hdr); print("-" * len(hdr))
        table = {}

        runs = [("gated_eqw", True, None), ("ungated_eqw", False, None)]
        runs += [(f"gated_no_{g}", True, g) for g in GATES]

        for name, gated, drop in runs:
            rets, turns, used = run_strategy(close, frames, pts, drop=drop,
                                             gated=gated, cost_bps=args.cost_bps,
                                             pit_cols=pit_cols)
            st = stats(rets, [spy_rets[i] for i in used], ppy)
            if st is None:
                continue
            st["avg_turnover_pct"] = round(100 * float(np.mean(turns)), 1)
            table[name] = st
            print(f"{name:<20}{st['cagr_pct']:>8}{st['vol_pct']:>7}"
                  f"{st['sharpe']:>8}{st['max_dd_pct']:>8}{st['beta']:>6}"
                  f"{st['ann_alpha_pct']:>11}{st['beat_spy_pct']:>7}"
                  f"{st['total_pct']:>9}{st['avg_turnover_pct']:>7}")

        spy_st = stats(spy_rets, spy_rets, ppy)
        spy_st["avg_turnover_pct"] = 0.0
        table["SPY"] = spy_st
        print(f"{'SPY':<20}{spy_st['cagr_pct']:>8}{spy_st['vol_pct']:>7}"
              f"{spy_st['sharpe']:>8}{spy_st['max_dd_pct']:>8}"
              f"{spy_st['beta']:>6}{spy_st['ann_alpha_pct']:>11}"
              f"{'':>7}{spy_st['total_pct']:>9}{0.0:>7}")

        g, u = table.get("gated_eqw"), table.get("ungated_eqw")
        if g and u:
            print(f"\n  GATES vs CONTROL: CAGR {g['cagr_pct']:.2f}% gated "
                  f"vs {u['cagr_pct']:.2f}% ungated "
                  f"({g['cagr_pct'] - u['cagr_pct']:+.2f}pp), "
                  f"Sharpe {g['sharpe']} vs {u['sharpe']}")
            print("  (gated must beat the UNGATED control, not just SPY — "
                  "equal-weighting alone is a size tilt)")
        out["by_rebal"][step] = table

    path = config.SCOUT_DIR / f"gates_results_{args.universe}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {path.name}")


if __name__ == "__main__":
    main()
