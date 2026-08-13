"""The universal data-integrity layer for the vNext program (handoff section 5).

WHY ONE MODULE
--------------
Rule 18 removed the old alpha vetoes, and some of those vetoes were accidentally
blocking corrupt bars (the huge-move veto hid most unadjusted splits from the
old engine). Under Rule 18 every mechanism sees raw prices, so the cleaning has
to happen ONCE, before any mechanism looks, with the same policy for every
sleeve — otherwise five labs re-implement five slightly different guards and
their results stop being comparable. Rounds 5-7 already built and validated
every individual piece; this module only composes them and gives the
composition a self-test. Nothing here invents a threshold: every rule and
number below is the one already registered in BACKTEST-REPORT.md.

WHAT IT DOES, IN ORDER
----------------------
1.  SPLIT REPAIR — `high52_lab.repair_splits`, Alpaca corporate actions as
    ground truth (data_audit measured 5.1% of splits unadjusted in the bars
    endpoint; SIRI prints a fake +925.6% without this).
2.  FROZEN-QUOTE RETIREMENT — a symbol is PERMANENTLY retired at the first run
    of >= 10 identical closes (frozen delisted quotes manufactured +896 bps of
    fake drift in H26). Retirement is forever: later prints under the same
    ticker are a different company (reused tickers) or a resumed halt, and
    neither may be spliced onto the old series.
3.  EXTREME-PRINT FLAGGING — any residual |1-day| move > 45% after split repair
    is masked in the RETURNS and counted. The raw price series is not edited
    (handoff 5.4: genuine large moves stay visible in prices); the mask means
    an event window that crosses one cannot be counted as clean confirmatory
    evidence, and callers get the mask to report exclusions.
4.  NO SILENT FILL — returns are pct_change(fill_method=None). A missing quote
    yields a missing return, never a fabricated zero (handoff 5.5).
5.  PIT COVERAGE, FAIL CLOSED — membership from scout/pit.py; the panel refuses
    to build if less than MIN_COVERAGE of the requested PIT union has usable
    bars in the window (handoff 5.1).

USAGE
-----
    from scout.price_integrity import build_panel
    P = build_panel("2016-01-04", "2026-08-07")   # PIT S&P 500 by default
    P.ret          # guarded daily returns, tz-aware index, NaN where unknown
    P.close        # split-repaired closes (prices NOT masked, per 5.4)
    P.live         # bool frame: PIT member AND not retired
    P.extreme_mask # bool frame: returns masked by guard 3 (report exclusions)
    P.report       # dict, ready for the reproducibility header

    python -m scout.price_integrity --report     # build + print the audit
    python -m scout.price_integrity --selftest   # planted-defect checks
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import bars, config, pit

MIN_COVERAGE = 0.90          # fail closed below this fraction of the PIT union
FROZEN_RUN = 10              # identical closes that retire a symbol, registered
EXTREME_PCT = 0.45           # |1d| return flagged after split repair, registered
REPORT_PATH = config.SCOUT_DIR / "integrity_report.json"

# ETFs used as benchmarks/cash legs: exempt from the frozen-quote retirement
# (BIL runs 53 identical closes at a zero policy rate on 1.2M shares/day —
# that is a T-bill fund doing its job, not a dead quote; flow_lab documented
# the override) but NOT exempt from the other guards.
ETF_EXEMPT_FROZEN = frozenset({"BIL", "SHV", "SGOV"})


@dataclass
class Panel:
    close: pd.DataFrame
    volume: pd.DataFrame
    ret: pd.DataFrame
    live: pd.DataFrame
    extreme_mask: pd.DataFrame
    retired_at: dict[str, pd.Timestamp]
    report: dict = field(default_factory=dict)


def _frozen_retirements(close: pd.DataFrame) -> dict[str, pd.Timestamp]:
    """First timestamp of each symbol's first >= FROZEN_RUN identical-close run."""
    out: dict[str, pd.Timestamp] = {}
    runlen = close.eq(close.shift(1)).rolling(FROZEN_RUN - 1).sum()
    hit = runlen >= (FROZEN_RUN - 1)
    for sym in close.columns:
        h = hit[sym]
        if h.any():
            # retire at the START of the run, not its end — every print inside
            # the run is already untrustworthy
            end = h.idxmax()
            loc = close.index.get_loc(end)
            out[sym] = close.index[max(0, loc - (FROZEN_RUN - 1))]
    return out


def build_panel(start: str, end: str, symbols: list[str] | None = None,
                extra: tuple[str, ...] = ("SPY", "BIL"),
                min_coverage: float = MIN_COVERAGE,
                verbose: bool = True) -> Panel:
    """The guarded panel every vNext mechanism reads. Fails closed on coverage."""
    from .high52_lab import repair_splits

    union = symbols if symbols is not None else pit.all_members_since(start)
    want = sorted(set(union) | set(extra))
    raw = bars.get(want, start, end, verbose=verbose)
    repaired, split_rows = repair_splits(raw)
    close, volume = repaired["close"], repaired.get("volume")

    # coverage, fail closed (handoff 5.1)
    have = [s for s in union if s in close.columns and close[s].notna().sum() > 20]
    coverage = len(have) / max(1, len(union))
    if coverage < min_coverage:
        missing = sorted(set(union) - set(have))
        raise RuntimeError(
            f"PIT coverage {coverage:.1%} is below the fail-closed floor "
            f"{min_coverage:.0%}: {len(missing)} of {len(union)} PIT members have "
            f"no usable bars (first 20: {missing[:20]}). Refusing to build a "
            f"panel that silently excludes them.")

    # frozen retirement (guard 2)
    retired = _frozen_retirements(close.drop(columns=[c for c in ETF_EXEMPT_FROZEN
                                                      if c in close.columns],
                                             errors="ignore"))
    live_cols = {}
    for sym in close.columns:
        alive = close[sym].notna()
        if sym in retired:
            alive &= close.index < retired[sym]
        live_cols[sym] = alive
    alive_frame = pd.DataFrame(live_cols, index=close.index)

    # membership: PIT member on each date AND alive
    memb = pd.DataFrame(False, index=close.index, columns=close.columns)
    snap_dates = sorted({d for d in close.index})
    cur = None
    for d in snap_dates:
        m = pit.members(d)
        if m is not cur:
            cur = m
        cols = [s for s in cur if s in memb.columns]
        memb.loc[d, cols] = True
    for e in extra:
        if e in memb.columns:
            memb[e] = True                # benchmarks are always "in"
    live = memb & alive_frame

    # returns: no silent fill (guard 5), then extreme mask (guard 3)
    ret = close.pct_change(fill_method=None)
    ret = ret.where(alive_frame)          # no returns past retirement
    extreme = ret.abs() > EXTREME_PCT
    n_extreme = int(extreme.sum().sum())
    ret = ret.where(~extreme)

    rep = {
        "span": [str(close.index[0].date()), str(close.index[-1].date())],
        "dates": int(len(close.index)),
        "pit_union": len(union),
        "pit_covered": len(have),
        "coverage_pct": round(100 * coverage, 2),
        "fail_closed_floor_pct": round(100 * min_coverage, 1),
        "splits_repaired": len(split_rows),
        "split_examples": [
            {"symbol": r.get("symbol"), "ex_date": str(r.get("ex_date"))}
            for r in split_rows[:5]],
        "frozen_retired": len(retired),
        "frozen_run_threshold": FROZEN_RUN,
        "frozen_etf_exemptions": sorted(ETF_EXEMPT_FROZEN & set(close.columns)),
        "extreme_prints_masked": n_extreme,
        "extreme_threshold_pct": 100 * EXTREME_PCT,
        "return_fill_policy": "pct_change(fill_method=None); no forward fill",
        "density_pct": round(100 * float(ret.notna().mean().mean()), 1),
    }
    if verbose:
        print(f"  integrity panel: {rep['dates']} dates x {len(close.columns)} "
              f"symbols | coverage {rep['coverage_pct']}% | splits repaired "
              f"{rep['splits_repaired']} | retired {rep['frozen_retired']} | "
              f"extreme masked {rep['extreme_prints_masked']}")
    return Panel(close=close, volume=volume, ret=ret, live=live,
                 extreme_mask=extreme, retired_at=retired, report=rep)


# --------------------------------------------------------------- self-test

def _selftest() -> int:
    """Planted-defect checks: every guard must catch its plant, and only its plant."""
    idx = pd.date_range("2020-01-01", periods=120, freq="B", tz="US/Eastern")
    rng = np.random.default_rng(7)
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok &= bool(cond)

    # frozen: symbol F freezes at session 60 for 15 sessions
    px = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, .01, (120, 3)), axis=0)),
                      index=idx, columns=["A", "B", "F"])
    px.iloc[60:75, 2] = px.iloc[60, 2]
    r = _frozen_retirements(px)
    check("frozen guard catches the planted 15-run", "F" in r)
    check("frozen guard retires at the run's START",
          "F" in r and r["F"] <= idx[61])
    check("frozen guard leaves clean symbols alone", "A" not in r and "B" not in r)

    # frozen: a 5-run must NOT retire
    px2 = px.copy()
    px2.iloc[20:25, 0] = px2.iloc[20, 0]
    check("a 5-identical-close run does not retire", "A" not in _frozen_retirements(px2))

    # extreme mask: plant a +60% print, confirm masked in returns not prices
    px3 = px.copy()
    px3.iloc[40, 1] *= 1.60
    ret = px3.pct_change(fill_method=None)
    m = ret.abs() > EXTREME_PCT
    check("extreme guard flags the planted +60%", bool(m.iloc[40, 1]))
    check("extreme guard flags nothing else", int(m.sum().sum()) == 1)

    # no-fill: a NaN close must give NaN returns on BOTH sides, never 0
    px4 = px.copy()
    px4.iloc[50, 0] = np.nan
    r4 = px4.pct_change(fill_method=None)["A"]
    check("missing close -> missing return, both sides",
          np.isnan(r4.iloc[50]) and np.isnan(r4.iloc[51]))

    # coverage fail-closed: ask for symbols that cannot exist
    try:
        build_panel("2016-01-04", "2016-03-01",
                    symbols=["ZZZZ1", "ZZZZ2", "SPY"], extra=(), verbose=False)
        check("coverage floor fails closed", False)
    except RuntimeError:
        check("coverage floor fails closed", True)

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.price_integrity")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--start", default="2016-01-04")
    ap.add_argument("--end", default="2026-08-07")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    P = build_panel(args.start, args.end)
    REPORT_PATH.write_text(json.dumps(P.report, indent=1))
    print(json.dumps(P.report, indent=1))
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
