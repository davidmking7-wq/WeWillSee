"""Weekly lab: does the v5 ranking survive a FIVE-DAY hold?

User directive (2026-08-08): "do a test for every week at the weekend —
choose what to invest in at the start of the new week and sell at the end."

That is a different question from everything else in this repo. The engine
was fitted and validated for a 42-trading-day first-passage-to-+5% objective;
its documented edge is "first-passage odds, speed and path safety" over two
months. Nothing says that edge survives being cut to one week, and the
horizon is short enough that the answer could easily be "no". This lab asks
it directly, before any of it is wired to an account.

TIMING (the part that decides whether the number is real)
-------------------------------------------------------
  scan  = last trading day of week W-1   (the weekend scan sees this close)
  entry = first trading day of week W, at the OPEN
  exit  = last trading day of week W, at the CLOSE

Entry is the Monday OPEN, not the Friday close. A weekend scan cannot
capture the weekend gap, and momentum names do a lot of their moving in
exactly that gap — basing entry on Friday's close would book a return no
tradeable schedule could have earned. `--entry close` reproduces the
optimistic close-to-close convention used elsewhere in the repo so the gap's
contribution is measurable rather than assumed.

WHAT THIS LAB GETS FOR FREE (and portfolio_lab did not)
------------------------------------------------------
Weekly holds tile the calendar exactly: consecutive, non-overlapping, every
week used. There is no entry-schedule phase to sample and therefore no
phase-luck problem — the failure mode that made portfolio_lab's headline
+733% collapse to ~+2%/window once phase_lab pooled the other schedules.
Whatever this lab reports is already pooled over every available week.

COSTS ARE NOT OPTIONAL HERE
---------------------------
This schedule turns the book over ~52x a year against the pipeline's ~6x.
A cost that rounds to nothing at 42 days is roughly eight times heavier at
5 days, so every table is printed at several round-trip costs and the
break-even cost is reported. Default 10 bps round-trip is a reasonable
retail estimate for gated (>= $10M/day) S&P 1500 names; it is an estimate,
not a measurement.

Usage:
  python -m scout.weekly_lab [--universe sp1500] [--entry open|close]
                             [--cost-bps 10] [--start ...] [--end ...]
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np
import pandas as pd

from . import backtest, config, signals

# The user's stated bar for a "good week" (2026-08-08 conversation), kept
# beside the repo's standing +5% goal so neither is privileged.
WEEK_BAR = 0.03
REPO_BAR = config.TARGET_GAIN

# Train/holdout boundary matching the rest of the repo. NOTE: SCOUT-DESIGN
# records the 2022-2026 holdout as RETIRED — it has been used to adjudicate
# earlier ship decisions. The split is printed here for structure and to
# expose era-instability, NOT as a clean out-of-sample test. Treat a
# holdout win here as "not yet contradicted", never as confirmation.
HOLDOUT_START = "2022-01-01"


def week_slots(idx, start=None, end=None, warmup=backtest.WARMUP):
    """[(scan_pos, entry_pos, exit_pos)] — one slot per calendar week.

    Grouping is by ISO week over actual trading days, so holiday-shortened
    weeks resolve on their own: entry is simply the week's first traded
    session and exit its last. A week with a single session becomes a
    same-day open->close hold, which is the honest execution of the rule
    rather than a reason to drop the week.
    """
    iso = idx.isocalendar()
    keys = list(zip(iso["year"], iso["week"]))
    groups: dict[tuple, list[int]] = {}
    for pos, key in enumerate(keys):
        groups.setdefault(key, []).append(pos)
    ordered = [groups[k] for k in sorted(groups)]

    lo = pd.Timestamp(start) if start else None
    hi = pd.Timestamp(end) if end else None
    slots = []
    for i in range(1, len(ordered)):
        scan_pos = ordered[i - 1][-1]
        entry_pos, exit_pos = ordered[i][0], ordered[i][-1]
        if scan_pos < warmup or entry_pos <= scan_pos:
            continue
        ts = idx[scan_pos].tz_localize(None)
        if lo is not None and ts < lo:
            continue
        if hi is not None and ts > hi:
            continue
        slots.append((scan_pos, entry_pos, exit_pos))
    return slots


def rank_weeks(bars, slots, mode, top=25):
    """Score the universe at each scan date. Returns one dict per week.

    pit500 ranks only that date's actual members (same one-row-slice
    technique as backtest.run_engine / portfolio_lab.collect).
    """
    from . import pit
    c = bars["close"]
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    spy = c[backtest.REGIME_SYM].dropna()
    bull_series = (spy > spy.rolling(200).mean()).reindex(c.index)

    out = []
    for scan_pos, entry_pos, exit_pos in slots:
        ts = c.index[scan_pos]
        if mode == "pit500":
            mem = pit.members(ts)
            cols = [s for s in c.columns if s in mem or s == backtest.REGIME_SYM]
            day = {k: f.loc[[ts], cols] for k, f in frames.items()}
            snap = signals.composite_at(day, ts)
        else:
            snap = signals.composite_at(frames, ts)
        snap = snap.drop(index=[backtest.REGIME_SYM], errors="ignore")
        if len(snap) < 50:
            continue
        b = bull_series.iloc[scan_pos]
        out.append({
            "scan_pos": scan_pos, "entry_pos": entry_pos, "exit_pos": exit_pos,
            "date": str(ts.date()),
            "ranked": list(snap.index[:top]),
            "vol": {s: float(snap.loc[s, "vol"]) for s in snap.index[:top]},
            "eligible": list(snap.index),
            "bull": bool(b) if not pd.isna(b) else True,
        })
    return out


def _leg_prices(bars, week, entry_basis):
    entry_frame = bars["open"] if entry_basis == "open" else bars["close"]
    entry_pos = week["entry_pos"] if entry_basis == "open" else week["scan_pos"]
    return entry_frame.iloc[entry_pos], bars["close"].iloc[week["exit_pos"]]


def book_return(bars, week, syms, entry_basis, cost_bps):
    """Equal-weight return of `syms` for one week, net of round-trip cost."""
    entry_row, exit_row = _leg_prices(bars, week, entry_basis)
    legs = []
    for sym in syms:
        e, x = entry_row.get(sym), exit_row.get(sym)
        if pd.isna(e) or pd.isna(x) or e <= 0:
            continue
        legs.append(float(x / e - 1))
    if not legs:
        return None
    return float(np.mean(legs)) - cost_bps / 10_000.0


def metrics(rets, beats=None, note=""):
    if not rets:
        return None
    curve = np.cumprod([1 + r for r in rets])
    peak = np.maximum.accumulate(curve)
    m = {
        "weeks": len(rets),
        "avg": round(100 * float(np.mean(rets)), 3),
        "median": round(100 * float(np.median(rets)), 3),
        "pct_ge3": round(100 * float(np.mean([r >= WEEK_BAR for r in rets])), 1),
        "pct_ge5": round(100 * float(np.mean([r >= REPO_BAR for r in rets])), 1),
        "pct_pos": round(100 * float(np.mean([r > 0 for r in rets])), 1),
        "worst": round(100 * float(min(rets)), 1),
        "max_dd": round(100 * float((curve / peak - 1).min()), 1),
        "compounded": round(100 * float(curve[-1] - 1), 1),
        "note": note,
    }
    if beats is not None and beats:
        m["beat_spy_pct"] = round(100 * float(np.mean(beats)), 1)
    # Cluster-free t-stat on the weekly mean: weeks are non-overlapping, so
    # the usual same-date correlation caveat does not apply across weeks.
    # It still assumes i.i.d. weeks, which market regimes violate.
    sd = float(np.std(rets, ddof=1)) if len(rets) > 1 else 0.0
    m["t_stat"] = round(float(np.mean(rets)) / (sd / math.sqrt(len(rets))), 2) if sd else 0.0
    return m


def strategies(weeks, bars, entry_basis, cost_bps, seed=7):
    """All strategy variants -> {name: [weekly returns]} plus SPY per week."""
    rng = np.random.default_rng(seed)
    series: dict[str, list[float]] = {}
    spy_rets: list[float] = []

    for wk in weeks:
        entry_row, exit_row = _leg_prices(bars, wk, entry_basis)
        se, sx = entry_row.get(backtest.REGIME_SYM), exit_row.get(backtest.REGIME_SYM)
        spy_r = float(sx / se - 1) if not (pd.isna(se) or pd.isna(sx)) else 0.0
        spy_rets.append(spy_r)

        def put(name, syms, cost=cost_bps):
            r = book_return(bars, wk, syms, entry_basis, cost)
            series.setdefault(name, []).append(r if r is not None else 0.0)

        for n in (1, 2, 3, 5, 10):
            put(f"top{n}", wk["ranked"][:n])

        # Hypothesis carried over from SCOUT-DESIGN: reaching a % bar inside
        # a short window NEEDS movement, which is why dividing momentum by
        # vol was rejected at 42 days. At 5 days the pressure is stronger,
        # so tilt the other way: highest-vol names among the top of the book.
        for n in (3, 5):
            pool = wk["ranked"][:15]
            hi_vol = sorted(pool, key=lambda s: wk["vol"].get(s, 0.0), reverse=True)
            put(f"voltilt{n}", hi_vol[:n])

        # Controls: equal-weight eligible pool (the honest market after the
        # engine's gates), and random draws of the same book size — the
        # noise band a 3-name book has to clear to mean anything.
        put("eqw_eligible", wk["eligible"], cost=0.0)
        pick = rng.choice(wk["eligible"], size=min(3, len(wk["eligible"])),
                          replace=False)
        put("random3", list(pick))

    series["SPY"] = spy_rets
    return series, spy_rets


def report(series, spy_rets, label, out):
    hdr = (f"{label:<18}{'weeks':>6}{'avg%':>8}{'med%':>8}{'>=3%':>7}{'>=5%':>7}"
           f"{'pos%':>7}{'worst%':>8}{'maxDD%':>8}{'compnd%':>10}{'t':>7}{'>SPY%':>7}")
    print(hdr)
    print("-" * len(hdr))
    order = ["top1", "top2", "top3", "top5", "top10", "voltilt3", "voltilt5",
             "random3", "eqw_eligible", "SPY"]
    for name in order:
        rets = series.get(name)
        if not rets:
            continue
        beats = [r > s for r, s in zip(rets, spy_rets)] if name != "SPY" else None
        m = metrics(rets, beats)
        out[name] = m
        print(f"{name:<18}{m['weeks']:>6}{m['avg']:>8}{m['median']:>8}"
              f"{m['pct_ge3']:>7}{m['pct_ge5']:>7}{m['pct_pos']:>7}"
              f"{m['worst']:>8}{m['max_dd']:>8}{m['compounded']:>10}"
              f"{m['t_stat']:>7}{m.get('beat_spy_pct', ''):>7}")


def breakeven_bps(rets_gross, spy_rets):
    """Round-trip cost (bps) at which the book's weekly mean falls to SPY's."""
    edge = float(np.mean(rets_gross) - np.mean(spy_rets))
    return round(edge * 10_000.0, 1)


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.weekly_lab")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--entry", default="open", choices=["open", "close"],
                    help="open = Monday open (honest); close = Friday close "
                         "(optimistic, repo convention, includes weekend gap)")
    ap.add_argument("--cost-bps", type=float, default=10.0,
                    help="round-trip transaction cost in basis points")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    bars = backtest.load_bars(args.no_cache, args.universe)
    idx = bars["close"].index
    slots = week_slots(idx, args.start, args.end)
    print(f"{len(slots)} candidate weeks; scoring universe at each scan date...")
    weeks = rank_weeks(bars, slots, args.universe)
    span = (weeks[0]["date"], weeks[-1]["date"])
    print(f"{len(weeks)} scored weeks {span[0]} .. {span[1]} "
          f"({args.universe}, entry={args.entry}, cost={args.cost_bps}bps)\n")

    out = {"span": span, "universe": args.universe, "entry": args.entry,
           "cost_bps": args.cost_bps, "engine": config.ENGINE, "tables": {}}

    series, spy = strategies(weeks, bars, args.entry, args.cost_bps)
    out["tables"]["full"] = {}
    report(series, spy, "FULL SPAN", out["tables"]["full"])

    # Era split. Printed for instability, not as a clean holdout (see above).
    cut = pd.Timestamp(HOLDOUT_START)
    early = [i for i, w in enumerate(weeks) if pd.Timestamp(w["date"]) < cut]
    late = [i for i, w in enumerate(weeks) if pd.Timestamp(w["date"]) >= cut]
    for name, sel in (("2016-2021", early), (f"{HOLDOUT_START[:4]}-2026", late)):
        if len(sel) < 30:
            continue
        sub = {k: [v[i] for i in sel] for k, v in series.items()}
        print()
        out["tables"][name] = {}
        report(sub, [spy[i] for i in sel], name, out["tables"][name])

    # Cost sensitivity for the headline book sizes, plus break-even.
    print("\ncost sensitivity (avg % per week, net):")
    print(f"{'strategy':<14}" + "".join(f"{b:>10}bps" for b in (0, 5, 10, 20, 40)))
    gross_ref, _ = strategies(weeks, bars, args.entry, 0.0)
    out["cost_sensitivity"] = {}
    for name in ("top2", "top3", "top5", "voltilt3"):
        row = []
        for b in (0, 5, 10, 20, 40):
            avg = float(np.mean(gross_ref[name])) - b / 10_000.0
            row.append(round(100 * avg, 3))
        out["cost_sensitivity"][name] = row
        out["cost_sensitivity"][f"{name}_breakeven_vs_spy_bps"] = \
            breakeven_bps(gross_ref[name], spy)
        print(f"{name:<14}" + "".join(f"{v:>13}" for v in row))
    print("\nbreak-even round-trip cost vs SPY (bps; negative = no edge "
          "even at zero cost):")
    for name in ("top2", "top3", "top5", "voltilt3"):
        print(f"  {name:<12}{out['cost_sensitivity'][f'{name}_breakeven_vs_spy_bps']:>8}")

    path = config.SCOUT_DIR / f"weekly_results_{args.universe}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {path.name}")
    print("RESULT_JSON: " + json.dumps(out["tables"]["full"]))


if __name__ == "__main__":
    main()
