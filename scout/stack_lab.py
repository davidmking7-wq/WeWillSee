"""H36 — only what survived verification, assembled: cap-weighted core + risk
rule + measured volatility sizing, raced against SPY.

WHAT THIS IS, STATED FIRST SO IT CANNOT BE OVERSOLD
====================================================
Nothing is discovered here. This is an ALLOCATION test of parts that already
survived adversarial verification in five rounds. If it works it is because
those parts work; if it fails it tells us the parts do not compose. Either way
it is a confirmatory assembly, not a search, and the variant count is small and
listed at the bottom of `run()`.

THE JOBS. Each component is judged ONLY on the axis its job is defined on.
--------------------------------------------------------------------------
  RETURN SOURCE   cap-weighted equity.  Judged on RETURN.
        Provenance: H31 (CONFIRMED) — cap-weighting the SAME holdings is worth
        +0.150 Sharpe and +3.48 pp/yr, difference beta 0.077, positive in both
        halves and all three thirds of both universes, externally confirmed by
        SPY - RSP (+0.180 Sharpe, +3.43 pp/yr, beta 0.043).
        Two candidate cores are raced: SPY itself, and H31's `full universe
        cap` book (every priced point-in-time S&P 500 member with a known
        share count, cap-weighted, 42-session ladder). "Own more of the
        market" is treated as the null it probably is.

  RISK RULE       a slow trend filter on the INDEX.  Judged on DRAWDOWN and on
        RISK-ADJUSTED return, never on raw return.
        Mechanism, one sentence: an index trading below a long moving average
        has empirically higher conditional variance and a fatter left tail
        than one above it (Faber 2007; Moskowitz-Ooi-Pedersen 2012), so
        standing aside there truncates the left tail at the cost of some of
        the right one.
        PROVENANCE CAVEAT, and it is the honest one: H35 (`scout/overlay_lab.py`)
        is the hypothesis that owns this rule, and NO `overlay_results.json`
        existed on disk when this lab ran — H35's verdict was not available.
        Rather than substitute an unverified rule silently, this lab (a) runs
        the whole assembly WITH and WITHOUT the overlay so the no-overlay
        answer is always visible, and (b) subjects the overlay to H35's own
        registered decisive control — MATCHED-TIME-IN-MARKET random timing,
        plus a rotated-signal null — inside this file. The overlay's status is
        therefore "verified here, on this book, against those controls", and
        the headline is reported both ways.

  SIZING          the H20 5-minute realised-variance forecaster.  Judged on
        RISK-ADJUSTED return.
        Provenance: H20 (CONFIRMED, 2 of 3 verifiers) — 13-16% better QLIKE
        than daily closes, 29/29 symbols, both halves. Used for POSITION SIZE
        ONLY: its own market-timing payoff was REJECTED and adding lag
        IMPROVED it, so no timing content is assumed here.

  EXECUTION       enter at a CLOSE.  H4/H18e: +5.29 bps/window, both halves —
        but a random pick earns +4.51, so it is free hygiene, not alpha.

  CASH            BIL (SPDR 1-3 Month T-Bill ETF). A real bill, not zero.

EXPLICITLY EXCLUDED (all rejected in earlier rounds, adding any is a new
hypothesis): every news signal, reversal, accruals, net issuance, illiquidity,
intraday momentum, PEAD, idiosyncratic vol, 52-week-high weight, merger
arbitrage, the multi-asset trend sleeves.

NON-NEGOTIABLE #1 — A REAL RISK-FREE SERIES
--------------------------------------------
H32 died partly because `sharpe()` ran on RAW returns and alpha regressed raw
on raw: at beta 0.27 the omitted rf x (1 - beta) term was ~1.75%/yr and turned
alpha +2.39% (t 1.02) into +0.76% (t 0.33). A book that SITS IN CASH has that
problem at its maximum. Therefore, everywhere in this file:
  * out of the market the book EARNS BIL's actual daily total return;
  * every Sharpe / Sortino is computed on returns in EXCESS OF BIL;
  * every alpha and beta regresses EXCESS on EXCESS.
`scout/beatspy_lab.py` hard-codes RF_SENSITIVITY = 0.02; it is not used here.

NON-NEGOTIABLE #2 — WHERE THE SHIFT IS
---------------------------------------
The overlay signal at date t uses closes <= t and nothing later.
  SAME-CLOSE (headline): the weight decided at the close of t is held over
      (close t -> close t+1) and earns r[t+1].  In code: `weight.shift(1)`.
      Realistic for a 200-day SMA: the mean of the last 200 closes is known to
      1/200th of the day's move minutes before the bell.
  NEXT-CLOSE (conservative): `weight.shift(2)`. Reported for every book.
The CORE book carries its own shift inside `construction_lab.book`: weights are
formed from row t and earn R[t+1 : t_next+1]. That is the same convention.
The RV forecast fc[t] is `har_forecast`'s walk-forward prediction for session t,
already `.shift(1)`-ed there, so it is a function of sessions <= t-1 and is
settable at the close of t-1 — one day MORE conservative than the trend signal.
Entries and exits fall on different days; there is no intraday trading anywhere.

DATA DEFECTS — WHICH GUARD WAS USED, ALL THREE NAMED
-----------------------------------------------------
 1. UNADJUSTED SPLITS (5.1% of the universe).
    ETF leg: SPY/BIL/IEF have never split on this window; `overlay_lab.guard`
    asserts no |daily return| > 25% for any of them and reports the maxima.
    CORE leg: `construction_lab` runs `high52_lab.repair_splits` over the whole
    panel before anything else, and the cap series is repaired at the fact
    level too (an unapplied split corrupts market cap twice over).
 2. SPIN-OFF / REUSED-TICKER >50% MOVES. CORE leg: `construction_lab` masks
    days with |return| > BIG_MOVE and quarantines the LOOKBACK window after
    them. ETF leg: covered by the same 25% assertion.
 3. FROZEN QUOTES. CORE leg: `idiovol_lab.retire_stale` retires a symbol at its
    first run of STALE_RUN identical closes. ETF leg: SPY is checked for
    identical-close runs directly and the longest is reported; the rule is NOT
    applied to BIL, because a 1-3 month bill ETF legitimately prints the same
    close for days and retiring it would delete the cash leg — BIL is instead
    validated on a property a frozen quote cannot fake, its annual total return
    tracking the actual bill curve.

CONTROLS
--------
 (a) MATCHED-TIME-IN-MARKET random timing, two nulls x 500 draws:
     iid out-days (same COUNT in cash) and BLOCK-MATCHED (the real rule's exact
     multiset of out-spell lengths placed at random). If the real rule sits
     inside these, the "edge" is reduced exposure in a volatile decade.
 (b) ROTATED SIGNAL (500 draws): identical runs, identical time in market,
     alignment with the market destroyed.
 (c) MATCHED BENCHMARKS: SPY buy-and-hold, RSP (the equal-weight ETF), 60/40
     SPY/IEF rebalanced monthly, and BIL alone.
 (d) The core's own contrast: the SAME holdings equal-weighted (H31's control).
 (e) A cap-coverage diagnostic: the core's edge over SPY is re-measured in the
     thirds where cap coverage is 74% and where it is 97%, because a coverage
     hole is a candidate survivorship tilt.

MANDATORY SLICES: both halves AND equal thirds, for every book AND every
difference; entry-phase pooling (Rule 9) is built into the core (42 phases) and
run explicitly for the monthly overlay variant; Rule 13 beta and alpha on
excess returns for every book AND every difference; Rule 16 Monte-Carlo sd of
every bootstrap t.

Usage:
    python -m scout.stack_lab                 # full run
    python -m scout.stack_lab --selftest      # lookahead + machinery proofs
    python -m scout.stack_lab --draws 500 --seed 20260809
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import bars, config, construction_lab as cl, growth as g

# SELF-CONTAINED BY DESIGN. An earlier draft imported `overlay_lab`'s helpers
# to guarantee Rule 17 (identical machinery on every arm). That file was being
# rewritten by H35 while this lab ran and its API changed underneath — so every
# statistic below is implemented here instead, and this module depends only on
# `bars`, `construction_lab`, `rv_forecast_lab` and `growth`, none of which
# moved. The formulas are the repo's standard ones and are stated in the
# docstrings so they can be checked against any other lab by eye.

TD_YEAR = 252
RESULTS = config.SCOUT_DIR / "stack_results.json"

HEADLINE_COST = 5.0                    # bps per unit traded
COST_GRID = (0.0, 5.0, 10.0, 20.0)
BORROW_SPREAD = 0.0050                 # over bills, for any leverage > 1
BORROW_GRID = (0.0025, 0.0050, 0.0100, 0.0200)
MAX_LEV = 2.0
TARGET_VOL = 0.12
NW_LAG = 21
SEED = 20260809
NULL_DRAWS = 500

# Registry N before this hypothesis. ~800 through Round 4, then H31 (53),
# H32, H33 (51), H34 (112), H35 — `overlay_lab` records 950 as the running
# count at its own start. This lab's own variants are added on top in `run()`.
N_RUNNING_PRIOR = 950


# ==========================================================================
# 0. Data, guards, signals and statistics — all local, see the note above
# ==========================================================================

START, END = "2016-01-04", "2026-08-07"
MAX_ABS_RET = 0.25          # guard 1+2: no ETF here may move this much in a day
ETFS = ("SPY", "BIL", "IEF")


def load_prices(quiet: bool = False) -> dict:
    """SPY / BIL / IEF total-return closes from the shared master cache.

    BIL is the cash leg AND the risk-free rate (non-negotiable #1). If the
    older `sleeve_bars.pkl` pull is on disk its BIL column is cross-checked
    against the master cache, so the two data paths cannot silently disagree.
    """
    px = bars.get(list(ETFS), START, END, verbose=not quiet)["close"]
    frame = px[list(ETFS)].dropna(how="any").sort_index()
    dev = None
    sleeve = config.SCOUT_DIR / "sleeve_bars.pkl"
    if sleeve.exists():
        try:
            sl = pd.read_pickle(sleeve)
            if "BIL" in sl.columns:
                idx = pd.DatetimeIndex(sl.index)
                idx = (idx.tz_localize("US/Eastern") if idx.tz is None
                       else idx.tz_convert("US/Eastern")).normalize()
                b = pd.Series(sl["BIL"].to_numpy(), index=idx).dropna()
                both = frame.index.intersection(b.index)
                dev = float((frame["BIL"].reindex(both) - b.reindex(both)).abs().max())
        except Exception:
            dev = None
    audit = guard(frame, quiet=quiet)
    audit["bil_cross_check_max_dev"] = dev
    return {"px": frame, "audit": audit}


def guard(frame: pd.DataFrame, quiet: bool = False) -> dict:
    """Data defects 1-3 on the ETF leg. Assertions, not assumptions."""
    rets = frame.pct_change()
    worst = {c: (float(rets[c].abs().max()), str(rets[c].abs().idxmax().date()))
             for c in frame.columns}
    bad = {c: v for c, (v, _) in worst.items() if v > MAX_ABS_RET}
    if bad:
        raise RuntimeError(f"guards 1/2 fired — implausible daily moves: {bad}")

    def longest_run(s: pd.Series) -> int:
        d = (s.diff() == 0).astype(int).to_numpy()
        best = run = 0
        for v in d:
            run = run + 1 if v else 0
            best = max(best, run)
        return best + 1 if best else 1

    spy_run, bil_run = longest_run(frame["SPY"]), longest_run(frame["BIL"])
    if spy_run >= 10:
        raise RuntimeError(f"guard 3 fired — SPY has {spy_run} identical closes")
    bilr = frame["BIL"].pct_change().dropna()
    by_year = bilr.groupby(bilr.index.year).apply(
        lambda x: float((1 + x).prod() ** (TD_YEAR / len(x)) - 1))
    out = {"n_dates": int(len(frame)),
           "span": (str(frame.index[0].date()), str(frame.index[-1].date())),
           "max_abs_daily_ret": worst,
           "spy_longest_identical_close_run": int(spy_run),
           "bil_longest_identical_close_run": int(bil_run),
           "bil_annualised_by_year_pct": {int(k): round(100 * v, 2)
                                          for k, v in by_year.items()}}
    if not quiet:
        print(f"  guards: max |1d| SPY {100*worst['SPY'][0]:.2f}% "
              f"({worst['SPY'][1]}), BIL {100*worst['BIL'][0]:.3f}%, "
              f"IEF {100*worst['IEF'][0]:.2f}%")
        print(f"          longest identical-close run: SPY {spy_run}, "
              f"BIL {bil_run} (BIL exempt by construction — a 1-3 month bill "
              f"ETF legitimately prints the same close)")
    return out


# ------------------------------------------------------------- the risk rule
def sig_sma(close: pd.Series, window: int = 200) -> pd.Series:
    """close[t] > mean(close[t-window+1 .. t]). Uses t, never t+1."""
    sma = close.rolling(window, min_periods=window).mean()
    return (close > sma).astype(float).where(sma.notna())


def sig_sma_monthly(close: pd.Series, months: int = 10,
                    phase: int | None = None) -> pd.Series:
    """Faber's original: month-end close vs the 10-MONTH SMA, acting only at
    decision dates and held flat in between. `phase=k` decides every 21st
    trading day from offset k — Rule 9's entry-phase pooling for a monthly
    rule."""
    if phase is None:
        dec = close.groupby([close.index.year, close.index.month]).tail(1).index
    else:
        pos = np.arange(len(close))
        dec = close.index[(pos % 21) == (phase % 21)]
    m = close.reindex(dec)
    sma = m.rolling(months, min_periods=months).mean()
    s = (m > sma).astype(float).where(sma.notna())
    return s.reindex(close.index).ffill()


# -------------------------------------------------------------- the sizing
def rv_leverage(cap: float = 1.0, quiet: bool = True) -> pd.Series:
    """H20's CONFIRMED forecaster turned into a position SIZE (not a timing
    signal). fc[t] is `rv_forecast_lab.har_forecast`'s walk-forward HAR-on-log
    5-minute realised variance prediction for session t, already `.shift(1)`-ed
    there, so it is a function of sessions <= t-1 and is settable at the close
    of t-1 — one day MORE conservative than the trend signal.
        lev[t] = clip(TARGET_VOL / sqrt(252 * fc[t]), 0, cap)
    """
    from . import rv_forecast_lab as rv
    panel = rv.load_panel(quiet=quiet)
    fc = rv.har_forecast(panel["rv_cc"][["SPY"]], log=True, pooled=False)["SPY"]
    ann = np.sqrt(TD_YEAR * fc.clip(lower=1e-12))
    lev = (TARGET_VOL / ann).clip(0.0, cap)
    idx = pd.DatetimeIndex(lev.index)
    lev.index = (idx.tz_localize("US/Eastern") if idx.tz is None
                 else idx.tz_convert("US/Eastern")).normalize()
    return lev.dropna()


# ------------------------------------------------------------- statistics
def _cagr(r: pd.Series) -> float:
    r = r.dropna()
    return float((1 + r).prod() ** (TD_YEAR / len(r)) - 1) if len(r) > 1 else np.nan


def _underwater(r: pd.Series) -> tuple[int, str, str]:
    curve = (1 + r.fillna(0.0)).cumprod()
    under = (curve < curve.cummax() * (1 - 1e-12)).to_numpy()
    if not under.any():
        return 0, "", ""
    i = np.arange(len(under))
    resets = np.maximum.accumulate(np.where(~under, i, -1))
    run = np.where(under, i - resets, 0)
    end = int(np.argmax(run))
    best = int(run[end])
    return best, str(r.index[end - best + 1].date()), str(r.index[end].date())


def metrics(r: pd.Series, rf: pd.Series, label: str = "") -> dict:
    """EVERY risk-adjusted number here is computed on returns in EXCESS OF
    BIL — the exact discipline whose absence killed H32."""
    r = r.dropna()
    rf = rf.reindex(r.index)
    ex = (r - rf).dropna()
    dd_dev = float(np.sqrt((ex.clip(upper=0.0) ** 2).mean())) if len(ex) else np.nan
    roll12 = np.expm1(np.log1p(r).rolling(TD_YEAR).sum())
    uw, uw_a, uw_b = _underwater(r)
    return {
        "label": label, "n": int(len(r)),
        "cagr_pct": round(100 * _cagr(r), 2),
        "vol_pct": round(100 * float(r.std(ddof=1)) * math.sqrt(TD_YEAR), 2),
        "sharpe": round(float(ex.mean() / ex.std(ddof=1) * math.sqrt(TD_YEAR)), 3),
        "sortino": round(float(ex.mean() / dd_dev * math.sqrt(TD_YEAR)), 3)
                   if dd_dev and dd_dev > 0 else float("nan"),
        "max_dd_pct": round(100 * g.max_drawdown(r), 2),
        "longest_underwater_td": int(uw), "underwater_span": f"{uw_a}..{uw_b}",
        "worst_12m_pct": round(100 * float(roll12.min()), 2)
                         if roll12.notna().any() else float("nan"),
        "ann_excess_pct": round(100 * float(ex.mean()) * TD_YEAR, 2),
        "skew": round(float(ex.skew()), 2),
        "kurtosis": round(float(ex.kurtosis()) + 3.0, 2),
    }


def ols_alpha_beta(y: np.ndarray, x: np.ndarray, lag: int = 21) -> dict:
    """y = a + b x on EXCESS returns, Newey-West at `lag`. Rule 13's engine."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    n = len(y)
    if n < 30:
        return {"alpha_ann_pct": np.nan, "beta": np.nan, "t_alpha": np.nan,
                "t_beta": np.nan, "r2": np.nan, "n": n}
    X = np.column_stack([np.ones(n), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    XtX_inv = np.linalg.inv(X.T @ X)
    u = X * resid[:, None]
    S = u.T @ u
    for L in range(1, min(lag, n - 1) + 1):
        G = u[L:].T @ u[:-L]
        S += (1 - L / (lag + 1)) * (G + G.T)
    se = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv))
    return {"alpha_ann_pct": round(100 * float(b[0]) * TD_YEAR, 2),
            "beta": round(float(b[1]), 3),
            "t_alpha": round(float(b[0] / se[0]), 2) if se[0] > 0 else np.nan,
            "t_beta": round(float(b[1] / se[1]), 2) if se[1] > 0 else np.nan,
            "r2": round(float(1 - resid.var() / y.var()), 3) if y.var() > 0 else np.nan,
            "n": n}


def nw_mean_t(x: np.ndarray, lag: int = 21) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    mu = float(x.mean())
    e = x - mu
    s = float(e @ e) / n
    for L in range(1, min(lag, n - 1) + 1):
        s += 2 * (1 - L / (lag + 1)) * float(e[L:] @ e[:-L]) / n
    se = math.sqrt(max(s, 1e-24) / n)
    return mu, se, mu / se


def split_report(r: pd.Series, rf: pd.Series, bench: pd.Series, k: int) -> list[dict]:
    """Equal-COUNT split into k pieces, book and benchmark on the same rows."""
    r = r.dropna()
    n = len(r)
    edges = [int(round(i * n / k)) for i in range(k + 1)]
    out = []
    for i in range(k):
        sl = r.index[edges[i]:edges[i + 1]]
        mb, ms = metrics(r.reindex(sl), rf), metrics(bench.reindex(sl), rf)
        out.append({"span": f"{sl[0].date()}..{sl[-1].date()}",
                    "book_cagr": mb["cagr_pct"], "spy_cagr": ms["cagr_pct"],
                    "book_sharpe": mb["sharpe"], "spy_sharpe": ms["sharpe"],
                    "book_maxdd": mb["max_dd_pct"], "spy_maxdd": ms["max_dd_pct"],
                    "d_sharpe": round(mb["sharpe"] - ms["sharpe"], 3),
                    "d_maxdd": round(mb["max_dd_pct"] - ms["max_dd_pct"], 2)})
    return out


EPISODES = {
    "2018Q4 selloff":   ("2018-09-20", "2018-12-24"),
    "2020 COVID crash": ("2020-02-19", "2020-03-23"),
    "2020 full round":  ("2020-02-19", "2020-08-31"),
    "2022 bear":        ("2022-01-03", "2022-10-12"),
    "2022 full round":  ("2022-01-03", "2024-01-19"),
}


def episode_report(r: pd.Series, bench: pd.Series) -> dict:
    out = {}
    for name, (a, b) in EPISODES.items():
        sl = r.loc[(r.index >= pd.Timestamp(a, tz="US/Eastern")) &
                   (r.index <= pd.Timestamp(b, tz="US/Eastern"))].index
        if len(sl) < 5:
            continue
        rb, rs = r.reindex(sl), bench.reindex(sl)
        out[name] = {"days": int(len(sl)),
                     "book_ret_pct": round(100 * float((1 + rb).prod() - 1), 2),
                     "spy_ret_pct": round(100 * float((1 + rs).prod() - 1), 2),
                     "book_maxdd_pct": round(100 * g.max_drawdown(rb), 2),
                     "spy_maxdd_pct": round(100 * g.max_drawdown(rs), 2)}
    return out


def spell_stats(weight: pd.Series, r_risky: pd.Series, r_bil: pd.Series,
                lag: int = 1) -> dict:
    """Time in market, round trips and WHIPSAWS. A whipsaw is a completed
    out-of-market spell over which the risky asset beat the bill — the rule
    stepping aside while the market went up. That is the rule failing at its
    own job in the only way it can fail cheaply; it is counted and priced."""
    w = weight.reindex(r_risky.index).shift(lag).ffill().dropna()
    inmkt = (w > 0.5).astype(int)
    entries = int((inmkt.diff() == 1).sum())
    yrs = len(w) / TD_YEAR
    spells, cur = [], None
    for dt, v in inmkt.items():
        if v == 0 and cur is None:
            cur = [dt, dt]
        elif v == 0:
            cur[1] = dt
        elif cur is not None:
            spells.append(tuple(cur))
            cur = None
    if cur is not None:
        spells.append(tuple(cur))
    whip, drag, lens = 0, 0.0, []
    for a, b in spells:
        sl = slice(a, b)
        s = float((1 + r_risky.loc[sl]).prod() - 1)
        c = float((1 + r_bil.loc[sl]).prod() - 1)
        lens.append(int(len(r_risky.loc[sl])))
        if s > c:
            whip += 1
            drag += (s - c)
    return {"time_in_market_pct": round(100 * float(inmkt.mean()), 2),
            "entries": entries,
            "round_trips_per_year": round(entries / yrs, 2),
            "out_spells": len(spells), "whipsaws": whip,
            "whipsaw_share_pct": round(100 * whip / max(len(spells), 1), 1),
            "whipsaw_total_drag_pct": round(100 * drag, 2),
            "median_out_spell_days": int(np.median(lens)) if lens else 0,
            "longest_out_spell_days": int(max(lens)) if lens else 0,
            "spell_lengths": lens}


def _weight_from_mask(index, out_pos) -> pd.Series:
    w = np.ones(len(index))
    w[out_pos] = 0.0
    return pd.Series(w, index=index)


def null_iid(sig: pd.Series, rng, draws: int) -> list[pd.Series]:
    """Same COUNT of days in cash, scattered at random."""
    s = sig.dropna()
    n, k = len(s), int((s < 0.5).sum())
    return [_weight_from_mask(s.index, rng.choice(n, size=k, replace=False))
            for _ in range(draws)]


def null_block(sig: pd.Series, lengths, rng, draws: int) -> list[pd.Series]:
    """The REAL multiset of out-spell lengths placed at random, non-overlapping
    — matches time in market AND the persistence of the exposure. The hard one."""
    s = sig.dropna()
    n = len(s)
    out = []
    for _ in range(draws):
        occ = np.zeros(n, dtype=bool)
        for L in sorted(lengths, reverse=True):
            for _try in range(200):
                st = int(rng.integers(0, max(n - L, 1)))
                if not occ[st:st + L].any():
                    occ[st:st + L] = True
                    break
        out.append(_weight_from_mask(s.index, np.where(occ)[0]))
    return out


def null_rotate(sig: pd.Series, rng, draws: int) -> list[pd.Series]:
    """Circular rotation: identical runs, identical time in market, alignment
    with the market destroyed."""
    s = sig.dropna()
    n = len(s)
    return [pd.Series(np.roll(s.to_numpy(float),
                              int(rng.integers(TD_YEAR // 4, n - TD_YEAR // 4))),
                      index=s.index) for _ in range(draws)]


def pctile(dist: pd.Series, value: float) -> float:
    return round(100 * float((dist < value).mean()), 1)


def block_boot_sharpe_diff(a, b, rng, reps: int = 2000, block: int = 21):
    """Circular block bootstrap of Sharpe(a) - Sharpe(b) on PAIRED series."""
    n = len(a)
    nb = int(np.ceil(n / block))
    out = np.empty(reps)
    for i in range(reps):
        starts = rng.integers(0, n, size=nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        x, y = a[idx], b[idx]
        sx = x.mean() / x.std(ddof=1) if x.std(ddof=1) > 0 else 0.0
        sy = y.mean() / y.std(ddof=1) if y.std(ddof=1) > 0 else 0.0
        out[i] = (sx - sy) * math.sqrt(TD_YEAR)
    return out


def boot_t_with_mc_sd(a, b, seeds=(1, 2, 3, 4, 5)) -> dict:
    """Rule 16: re-seed and report the Monte-Carlo sd of the bootstrap t."""
    ts, ds = [], []
    point = ((a.mean() / a.std(ddof=1)) - (b.mean() / b.std(ddof=1))) * math.sqrt(TD_YEAR)
    for s in seeds:
        d = block_boot_sharpe_diff(a, b, np.random.default_rng(SEED + s))
        ts.append(point / d.std(ddof=1))
        ds.append(d.std(ddof=1))
    return {"point_sharpe_diff": round(float(point), 3),
            "t": round(float(np.mean(ts)), 3),
            "mc_sd_of_t": round(float(np.std(ts, ddof=1)), 3),
            "boot_sd": round(float(np.mean(ds)), 4)}


# ==========================================================================
# 1. The core (return source)
# ==========================================================================

def load_core(mode: str, kind: str, scheme: str, index_needed=None,
              verbose: bool = True) -> dict:
    """One core book as a daily total-return series plus its turnover schedule.

    Reuses `construction_lab.book` unchanged (Rule 17: the same machinery that
    produced H31's confirmed number). 42 entry phases are averaged inside it,
    so Rule 9 is satisfied for the core by construction.
    """
    p = cl.build_panel(mode, guard=True, use_cache=True, verbose=verbose)
    b = cl.book(p, kind, scheme)
    idx = pd.DatetimeIndex(p["index"])
    gross = pd.Series(b["gross"], index=idx).dropna()
    turn = pd.Series(b["turn_day"], index=idx).reindex(gross.index).fillna(0.0)
    return {"label": f"{mode}:{kind}/{scheme}", "ret": gross, "turn": turn,
            "turnover_oneway_per_yr": float(np.nansum(b["turn_day"]))
            / (len(gross) / TD_YEAR),
            "cap_coverage_by_year": p.get("cap_coverage_by_year", {}),
            "n_split_repairs": p.get("n_split_repairs"),
            "n_stale_killed": p.get("n_stale_killed"),
            "n_day_dirty": p.get("n_day_dirty"),
            "n_symbols": len(p["cols"])}


# ==========================================================================
# 2. The assembly
# ==========================================================================

def build_stack(weight: pd.Series, r_core: pd.Series, r_bil: pd.Series,
                core_turn: pd.Series | None = None, lag: int = 1,
                cost_bps: float = HEADLINE_COST,
                borrow: float = BORROW_SPREAD) -> pd.Series:
    """Daily TOTAL return of: `weight` in the core, the remainder in BIL.

    `lag=1` is SAME-CLOSE (the weight set at the close of t earns r[t+1]);
    `lag=2` is NEXT-CLOSE. Weight above 1 borrows at the bill rate + `borrow`.
    Costs are charged on |dw| (the overlay's own trading) plus w * core_turn
    (the core's rebalancing, which is only paid while the book is held).

    With weight == 1 everywhere and core_turn = None this returns the core
    itself; with weight == 0 it returns BIL. `selftest` asserts both.
    """
    w = weight.reindex(r_core.index).shift(lag).ffill()
    ok = w.notna()
    w = w.fillna(0.0)
    lev_excess = np.maximum(w - 1.0, 0.0) * borrow / TD_YEAR
    gross = w * r_core + (1.0 - w) * r_bil.reindex(r_core.index) - lev_excess
    traded = w.diff().abs().fillna(0.0)
    if core_turn is not None:
        traded = traded + w * core_turn.reindex(r_core.index).fillna(0.0)
    net = gross - traded * cost_bps / 1e4
    return net.where(ok)


def _mix_monthly(a: pd.Series, b: pd.Series, wa: float = 0.6) -> pd.Series:
    """A two-asset book rebalanced to `wa` at each month end and left to drift
    in between — the honest 60/40 control, not a daily-rebalanced idealisation."""
    idx = a.index
    is_end = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).transform("max")
    is_end = (pd.Series(idx, index=idx) == is_end)
    w = wa
    out = np.empty(len(idx))
    for i, dt in enumerate(idx):
        ra, rb = float(a.iloc[i]), float(b.iloc[i])
        out[i] = w * ra + (1 - w) * rb
        va, vb = w * (1 + ra), (1 - w) * (1 + rb)
        w = va / (va + vb) if (va + vb) > 0 else wa
        if bool(is_end.iloc[i]):
            w = wa
    return pd.Series(out, index=idx)


def traded_per_year(weight: pd.Series, r_core: pd.Series,
                    core_turn: pd.Series | None, lag: int = 1) -> float:
    w = weight.reindex(r_core.index).shift(lag).ffill().fillna(0.0)
    traded = w.diff().abs().fillna(0.0)
    if core_turn is not None:
        traded = traded + w * core_turn.reindex(r_core.index).fillna(0.0)
    return float(traded.sum()) / (len(r_core) / TD_YEAR)


# ==========================================================================
# 3. Reporting — every risk number is EXCESS OF BIL (non-negotiable #1)
# ==========================================================================

def diff_report(r: pd.Series, bench: pd.Series, rf: pd.Series,
                lag: int = NW_LAG) -> dict:
    """Rule 13 on the DIFFERENCE, which is where H29 went wrong.

    d = r_book - r_bench is already an excess-of-excess quantity (the rf terms
    cancel), so regressing it on the benchmark's EXCESS return gives
    alpha_d = alpha_book - alpha_bench and beta_d = beta_book - beta_bench.
    """
    d = (r - bench).dropna()
    ex_b = (bench - rf).reindex(d.index)
    ab = ols_alpha_beta(d.to_numpy(), ex_b.to_numpy(), lag=lag)
    mu, se, t = nw_mean_t(d.to_numpy(), lag=lag)
    n = len(d)
    thirds, halves = [], []
    for k, store in ((3, thirds), (2, halves)):
        edges = [int(round(i * n / k)) for i in range(k + 1)]
        for i in range(k):
            seg = d.iloc[edges[i]:edges[i + 1]]
            m2, s2, t2 = nw_mean_t(seg.to_numpy(), lag=lag)
            store.append({"span": f"{seg.index[0].date()}..{seg.index[-1].date()}",
                          "ann_pct": round(100 * m2 * TD_YEAR, 2),
                          "t": round(t2, 2)})
    return {"ann_diff_pct": round(100 * mu * TD_YEAR, 2), "t_nw": round(t, 2),
            "alpha_ann_pct": ab["alpha_ann_pct"], "t_alpha": ab["t_alpha"],
            "beta": ab["beta"], "t_beta": ab["t_beta"],
            "halves": halves, "thirds": thirds}


def report(r: pd.Series, rf: pd.Series, spy: pd.Series, label: str,
           n_trials: int = 1) -> dict:
    """Full card for one book: levels, slices, Rule 13, deflated Sharpe."""
    r = r.dropna()
    common = r.index.intersection(spy.dropna().index).intersection(rf.dropna().index)
    r, s, f = r.reindex(common), spy.reindex(common), rf.reindex(common)
    m = metrics(r, f, label)
    ab = ols_alpha_beta((r - f).to_numpy(), (s - f).to_numpy(), lag=NW_LAG)
    m["alpha_ann_pct"] = ab["alpha_ann_pct"]
    m["t_alpha"] = ab["t_alpha"]
    m["beta"] = ab["beta"]
    m["t_beta"] = ab["t_beta"]
    m["r2_vs_spy"] = ab["r2"]
    m["halves"] = split_report(r, f, s, 2)
    m["thirds"] = split_report(r, f, s, 3)
    m["vs_spy"] = diff_report(r, s, f)
    ex = (r - f)
    sr_daily = float(ex.mean() / ex.std(ddof=1)) if ex.std(ddof=1) > 0 else 0.0
    m["deflated_sharpe_p"] = round(g.deflated_sharpe(
        sr_daily, n_trials=max(n_trials, 1), n_obs=len(ex),
        skew=float(ex.skew()), kurtosis=float(ex.kurtosis()) + 3.0), 4)
    m["n_trials_used"] = int(n_trials)
    return m


def lever_to(r_book: pd.Series, rf: pd.Series, bench: pd.Series,
             borrow: float = BORROW_SPREAD, causal: bool = False,
             window: int = TD_YEAR) -> dict:
    """Scale the book's EXCESS return to the benchmark's realised excess vol
    and charge `borrow` on the borrowed part. `causal=False` uses one
    full-sample scalar (in-sample by construction, and labelled so);
    `causal=True` recomputes it from a trailing window, which is the number a
    real account could have had."""
    ex_b = (r_book - rf).dropna()
    ex_s = (bench - rf).reindex(ex_b.index).dropna()
    ex_b = ex_b.reindex(ex_s.index)
    if causal:
        L = (ex_s.rolling(window, min_periods=window).std()
             / ex_b.rolling(window, min_periods=window).std()).shift(1).clip(0.0, 4.0)
    else:
        L = pd.Series(float(ex_s.std(ddof=1) / ex_b.std(ddof=1)), index=ex_b.index)
    lev_ex = L * ex_b - np.maximum(L - 1.0, 0.0) * borrow / TD_YEAR
    r_lev = (rf.reindex(ex_b.index) + lev_ex).dropna()
    m = metrics(r_lev, rf, "levered")
    m["leverage_mean"] = round(float(L.reindex(r_lev.index).mean()), 3)
    m["leverage_max"] = round(float(L.reindex(r_lev.index).max()), 3)
    m["causal"] = causal
    m["borrow_bps"] = int(round(borrow * 1e4))
    # The benchmark measured on EXACTLY the same rows. The trailing-window
    # version starts 252 sessions late, so comparing it against a full-window
    # SPY number would be an apples-to-oranges win handed out for free.
    mb = metrics(bench.reindex(r_lev.index), rf, "bench_same_rows")
    m["bench_cagr_same_rows"] = mb["cagr_pct"]
    m["bench_sharpe_same_rows"] = mb["sharpe"]
    m["bench_maxdd_same_rows"] = mb["max_dd_pct"]
    return m


def breakeven_cost(weight, r_core, r_bil, core_turn, rf, lag, target_sharpe,
                   lo: float = -100.0, hi: float = 500.0) -> float:
    """Cost in bps per unit traded at which the book's Sharpe equals the
    target. Negative means it needs a SUBSIDY — it loses even for free."""
    def f(c):
        r = build_stack(weight, r_core, r_bil, core_turn, lag=lag, cost_bps=c)
        return metrics(r, rf)["sharpe"] - target_sharpe
    if f(lo) < 0:
        return float("nan")
    if f(hi) > 0:
        return float("inf")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return round(0.5 * (lo + hi), 1)


# ==========================================================================
# 4. Nulls (control (a), (b)) — run on the SAME core, so only the timing of
#    the exposure differs between the real rule and the null.
# ==========================================================================

def run_null(weights: list[pd.Series], r_core, r_bil, core_turn, rf,
             lag: int, cost: float) -> pd.DataFrame:
    rows = []
    for w in weights:
        r = build_stack(w, r_core, r_bil, core_turn, lag=lag, cost_bps=cost)
        m = metrics(r, rf)
        rows.append({"cagr": m["cagr_pct"], "sharpe": m["sharpe"],
                     "maxdd": m["max_dd_pct"], "sortino": m["sortino"]})
    return pd.DataFrame(rows)


def null_matched_exposure(weight: pd.Series, r_core, r_bil, core_turn, rf,
                          lag: int, cost: float) -> dict:
    """THE decisive control for a SIZING rule, the exact analogue of
    matched-time-in-market for a timing rule: hold a CONSTANT weight equal to
    the rule's own average exposure. Volatility scaling reduces average
    exposure; if a constant weight at that same average does just as well, the
    forecast contributed nothing and the gain was de-levering, not timing."""
    w = weight.reindex(r_core.index).shift(lag).ffill()
    avg = float(w.mean())
    flat = pd.Series(avg, index=r_core.index)
    r_flat = build_stack(flat, r_core, r_bil, core_turn, lag=lag, cost_bps=cost)
    m = metrics(r_flat.dropna(), rf)
    m["constant_weight"] = round(avg, 4)
    return m


def null_rotate_weight(weight: pd.Series, r_core, r_bil, core_turn, rf,
                       lag: int, cost: float, draws: int, rng) -> pd.DataFrame:
    """Rotate a CONTINUOUS weight series circularly: identical distribution of
    exposures, identical average exposure, alignment with the market destroyed."""
    s = weight.reindex(r_core.index).ffill().dropna()
    n = len(s)
    rows = []
    for _ in range(draws):
        k = int(rng.integers(TD_YEAR // 4, n - TD_YEAR // 4))
        w = pd.Series(np.roll(s.to_numpy(float), k), index=s.index)
        m = metrics(build_stack(w, r_core, r_bil, core_turn, lag=lag,
                                cost_bps=cost).dropna(), rf)
        rows.append({"cagr": m["cagr_pct"], "sharpe": m["sharpe"],
                     "maxdd": m["max_dd_pct"]})
    return pd.DataFrame(rows)


def null_block_from_series(r_book, r_core, r_bil, core_turn, rf, sig,
                           lengths, lag, cost, draws, rng) -> dict:
    """The decisive control: matched time-in-market, three ways."""
    real = metrics(r_book, rf)
    out = {}
    for name, ws in (
            ("iid_matched_TIM", null_iid(sig, rng, draws)),
            ("block_matched_spells", null_block(sig, lengths, rng, draws)),
            ("rotated_signal", null_rotate(sig, rng, draws))):
        nn = run_null(ws, r_core, r_bil, core_turn, rf, lag, cost)
        out[name] = {
            "draws": int(len(nn)),
            "sharpe_mean": round(float(nn["sharpe"].mean()), 3),
            "sharpe_p95": round(float(nn["sharpe"].quantile(0.95)), 3),
            "real_sharpe": real["sharpe"],
            "sharpe_pctile": pctile(nn["sharpe"], real["sharpe"]),
            "maxdd_mean": round(float(nn["maxdd"].mean()), 2),
            "maxdd_p05": round(float(nn["maxdd"].quantile(0.05)), 2),
            "real_maxdd": real["max_dd_pct"],
            "maxdd_pctile": pctile(nn["maxdd"], real["max_dd_pct"]),
            "cagr_mean": round(float(nn["cagr"].mean()), 2),
            "real_cagr": real["cagr_pct"],
            "cagr_pctile": pctile(nn["cagr"], real["cagr_pct"]),
        }
    return out


# ==========================================================================
# 5. Self-test — the no-lookahead and machinery proofs
# ==========================================================================

def _check(fails: list, name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def selftest(quiet: bool = False) -> int:
    fails: list[str] = []
    print("stack_lab selftest")

    px = load_prices(quiet=True)["px"]
    spy = px["SPY"].pct_change().dropna()
    bil = px["BIL"].pct_change().reindex(spy.index).fillna(0.0)
    close = px["SPY"]

    # 1. the assembly identities: always-in is the core, always-out is BIL ---
    sig = sig_sma(close, 200)
    ones = pd.Series(1.0, index=spy.index)
    zeros = pd.Series(0.0, index=spy.index)
    d_in = float((build_stack(ones, spy, bil, None, 1, 0.0) - spy).abs().max())
    d_out = float((build_stack(zeros, spy, bil, None, 1, 0.0) - bil).abs().max())
    _check(fails, "weight 1 reproduces the core exactly", d_in < 1e-15,
           f"max dev {d_in:.2e}")
    _check(fails, "weight 0 reproduces BIL exactly (cash EARNS the bill rate)",
           d_out < 1e-15, f"max dev {d_out:.2e}")

    # 1b. the shift is where the docstring says it is, checked by hand -------
    w = sig.copy()
    k = 900
    hand = (float(w.iloc[k - 1]) * float(spy.iloc[k])
            + (1 - float(w.iloc[k - 1])) * float(bil.iloc[k]))
    got = float(build_stack(w, spy, bil, None, lag=1, cost_bps=0.0).iloc[k])
    _check(fails, "same-close: the weight set at close t-1 earns r[t]",
           abs(hand - got) < 1e-15, f"hand {hand:.8f} vs book {got:.8f}")

    # 2. truncation invariance: a causal signal cannot change when the future
    #    is deleted.
    cut = 1500
    full = sig_sma(close, 200).iloc[:cut]
    trunc = sig_sma(close.iloc[:cut], 200)
    x, y = full.align(trunc, join="inner")
    _check(fails, "sma200 unchanged when the future is deleted",
           bool(((x.isna() & y.isna()) | (x == y)).all()))

    # 3. the harness WOULD catch lookahead if it existed --------------------
    cheat = (spy.shift(-1) > 0).astype(float)          # tomorrow's sign, today
    r_cheat = build_stack(cheat, spy, bil, None, lag=1, cost_bps=0.0)
    s_cheat = metrics(r_cheat, bil)["sharpe"]
    _check(fails, "a deliberately clairvoyant signal scores absurdly",
           s_cheat > 5.0, f"sharpe {s_cheat:.2f}")

    # 4. no cliff between same-close and next-close for the REAL signal.
    #    A big drop from lag 1 to lag 2 is the signature of leaked information.
    s1 = metrics(build_stack(sig, spy, bil, None, 1, 0.0), bil)["sharpe"]
    s2 = metrics(build_stack(sig, spy, bil, None, 2, 0.0), bil)["sharpe"]
    _check(fails, "no same-close / next-close cliff on the real signal",
           abs(s1 - s2) < 0.25, f"lag1 {s1:.3f} lag2 {s2:.3f}")

    # 5. rf discipline: BIL measured against itself must have Sharpe 0 -------
    ex_cash = float((bil - bil).abs().max())
    _check(fails, "the cash leg has identically zero excess return over itself",
           ex_cash < 1e-18, f"max |excess| {ex_cash:.2e}")

    # 6. and the SAME series measured with no rf must NOT be 0 — the exact
    #    bias that killed H32.
    zero = pd.Series(0.0, index=bil.index)
    z0 = metrics(bil, zero)["sharpe"]
    _check(fails, "the missing-rf bias is real and would have shown up here",
           z0 > 1.0, f"raw-return Sharpe of pure cash {z0:.2f}")

    # 7. costs are monotone ------------------------------------------------
    srs = [metrics(build_stack(sig, spy, bil, None, 1, c), bil)["sharpe"]
           for c in (0.0, 5.0, 20.0, 100.0)]
    _check(fails, "Sharpe is monotone decreasing in cost",
           all(srs[i] >= srs[i + 1] for i in range(len(srs) - 1)), str(srs))

    # 8. the core book's shift: its return on the first live date must not be
    #    computable before the warmup ends.
    core = load_core("pit500", "full", "cap", verbose=False)
    _check(fails, "core book starts after the panel warmup",
           core["ret"].index[0] > px.index[200],
           f"first live core date {core['ret'].index[0].date()}")

    # 9. the RV forecast is settable one day early (H20's shift) ------------
    lev = rv_leverage(cap=MAX_LEV, quiet=True)
    _check(fails, "rv leverage is finite, in [0, MAX_LEV], and starts 2019",
           bool(lev.notna().all() and (lev >= 0).all() and (lev <= MAX_LEV + 1e-9).all()
                and lev.index[0].year == 2019),
           f"{lev.index[0].date()}..{lev.index[-1].date()} "
           f"mean {float(lev.mean()):.3f}")

    print(f"selftest: {len(fails)} failure(s)" + (f" -> {fails}" if fails else ""))
    return len(fails)


# ==========================================================================
# 6. The run
# ==========================================================================

def _tab(rows: list[dict], cols: list[str], title: str) -> None:
    print(f"\n{title}")
    w = {c: max(len(c), *(len(f"{r.get(c, '')}") for r in rows)) for c in cols}
    print("  " + "  ".join(c.rjust(w[c]) for c in cols))
    for r in rows:
        print("  " + "  ".join(f"{r.get(c, '')}".rjust(w[c]) for c in cols))


def run(args) -> dict:
    t_start = datetime.now(timezone.utc)
    rng = np.random.default_rng(args.seed)
    print("=" * 78)
    print("H36 — assembling only what survived verification")
    print("=" * 78)

    # ---------------------------------------------------------------- data
    lp = load_prices(quiet=False)
    px = lp["px"]
    spy = px["SPY"].pct_change().dropna()
    bil = px["BIL"].pct_change().reindex(spy.index).fillna(0.0)
    ief = px["IEF"].pct_change().reindex(spy.index).fillna(0.0)
    close = px["SPY"]
    rf = bil                                    # THE risk-free rate, everywhere
    print(f"  BIL annualised by year: {lp['audit']['bil_annualised_by_year_pct']}")

    # ---------------------------------------------------------------- cores
    print("\ncores (the return source):")
    cores = {}
    for key, (mode, kind, scheme) in {
            "CAP500": ("pit500", "full", "cap"),
            "EQ500": ("pit500", "full", "equal"),
            "CAP1500": ("sp1500", "full", "cap")}.items():
        c = load_core(mode, kind, scheme, verbose=False)
        cores[key] = c
        print(f"  {key:8s} {c['label']:22s} {len(c['ret'])} days, "
              f"{c['n_symbols']} symbols, turnover {c['turnover_oneway_per_yr']:.3f}/yr")
    print(f"  cap coverage by year (CAP500): {cores['CAP500']['cap_coverage_by_year']}")
    print(f"  guards on the core panel: splits repaired "
          f"{cores['CAP500']['n_split_repairs']}, stale symbols retired "
          f"{cores['CAP500']['n_stale_killed']}, dirty days "
          f"{cores['CAP500']['n_day_dirty']}")

    # The common window: every arm of every comparison is measured on the SAME
    # rows (Rule 17). The cores start after a 270-bar warmup.
    idx_full = spy.index
    for c in cores.values():
        idx_full = idx_full.intersection(c["ret"].index)
    print(f"\ncommon full window: {idx_full[0].date()}..{idx_full[-1].date()} "
          f"({len(idx_full)} sessions)")

    # ------------------------------------------------------------- signals
    sigs = {"sma200": sig_sma(close, 200),
            "sma150": sig_sma(close, 150),
            "sma250": sig_sma(close, 250),
            "sma10m": sig_sma_monthly(close, 10)}
    lev_rv = rv_leverage(cap=MAX_LEV, quiet=True)
    lev_rv1 = lev_rv.clip(0.0, 1.0)                 # de-risking only
    lev_rv2 = lev_rv                                # with leverage + borrow
    lev_rv1_lag = lev_rv1.shift(1)                  # H20's "extra lag" check
    print(f"\nrv sizing: {lev_rv.index[0].date()}..{lev_rv.index[-1].date()}, "
          f"mean lev {float(lev_rv.mean()):.2f} (capped 1.0: "
          f"{float(lev_rv1.mean()):.2f}), target vol {TARGET_VOL:.0%}")

    # ------------------------------------------------- the books to measure
    ones = pd.Series(1.0, index=spy.index)

    def core_series(key):
        if key == "SPY":
            return spy, None
        return cores[key]["ret"], cores[key]["turn"]

    # (core, overlay signal or None, sizing series or None, label)
    specs = [
        ("SPY", None, None, "SPY buy-and-hold"),
        ("CAP500", None, None, "CAP500 core"),
        ("EQ500", None, None, "EQ500 core (H31 control)"),
        ("CAP1500", None, None, "CAP1500 core"),
        ("SPY", "sma200", None, "SPY + trend"),
        ("CAP500", "sma200", None, "CAP500 + trend"),
        ("CAP1500", "sma200", None, "CAP1500 + trend"),
        ("SPY", "sma150", None, "SPY + trend150"),
        ("SPY", "sma250", None, "SPY + trend250"),
        ("SPY", "sma10m", None, "SPY + trend10m"),
        ("CAP500", "sma150", None, "CAP500 + trend150"),
        ("CAP500", "sma250", None, "CAP500 + trend250"),
        ("CAP500", "sma10m", None, "CAP500 + trend10m"),
    ]
    variants = 0
    books, cards = {}, {}
    for core_key, sig_key, _size, label in specs:
        r_core, turn = core_series(core_key)
        w = (ones if sig_key is None else sigs[sig_key]).reindex(spy.index).ffill()
        # A book with no overlay never trades on a signal, so the same-close /
        # next-close distinction does not exist for it — only the overlaid
        # books get both execution conventions.
        lags = (1,) if sig_key is None else (1, 2)
        for lag in lags:
            name = label if sig_key is None else \
                f"{label} [{'same' if lag == 1 else 'next'}-close]"
            r = build_stack(w, r_core, bil, turn, lag=lag,
                            cost_bps=HEADLINE_COST)
            books[name] = r.reindex(idx_full).dropna()
            variants += 1

    # THE FULL STACK over the WHOLE window. The RV forecaster only exists from
    # 2019-03 (it needs 5-minute bars and a walk-forward HAR warmup), so the
    # RV-window tables above cannot see COVID in their trailing-leverage
    # comparison — the 252-day warmup lands them at the March 2020 bottom.
    # This book sizes at 1.0 while the forecast is absent and at the H20
    # forecast once it exists, so the assembly can be measured over the full
    # 2017-2026 sample including both crashes. It is labelled as a splice.
    rv_or_one = lev_rv1.reindex(spy.index).ffill().fillna(1.0)
    for core_key, label in (("SPY", "SPY + trend + rv (spliced)"),
                            ("CAP500", "CAP500 + trend + rv (spliced)")):
        r_core, turn = core_series(core_key)
        w = rv_or_one * sigs["sma200"].reindex(spy.index).ffill()
        books[label] = build_stack(w, r_core, bil, turn, lag=1,
                                   cost_bps=HEADLINE_COST).reindex(idx_full).dropna()
        variants += 1

    # controls: 60/40 rebalanced monthly, and BIL alone
    books["60/40 SPY/IEF (monthly)"] = _mix_monthly(spy, ief, 0.6).reindex(idx_full)
    books["BIL (cash only)"] = bil.reindex(idx_full)
    variants += 2

    # ---- the RV-sizing arm lives on a shorter window (H20 starts 2019-03) --
    idx_rv = idx_full.intersection(
        pd.DatetimeIndex(lev_rv.index).intersection(idx_full))
    idx_rv = idx_rv[idx_rv >= lev_rv.index[0]]
    rv_specs = [
        ("SPY", None, lev_rv1, "SPY + rv1.0"),
        ("SPY", "sma200", lev_rv1, "SPY + trend + rv1.0"),
        ("CAP500", "sma200", lev_rv1, "CAP500 + trend + rv1.0"),
        ("SPY", "sma200", lev_rv2, "SPY + trend + rv2.0"),
        ("SPY", "sma200", lev_rv1_lag, "SPY + trend + rv1.0 lagged"),
        ("CAP500", None, lev_rv1, "CAP500 + rv1.0"),
    ]
    rv_books = {}
    for core_key, sig_key, size, label in rv_specs:
        r_core, turn = core_series(core_key)
        w = size.reindex(spy.index).ffill()
        if sig_key is not None:
            w = w * sigs[sig_key].reindex(spy.index).ffill()
        r = build_stack(w, r_core, bil, turn, lag=1, cost_bps=HEADLINE_COST)
        rv_books[label] = r.reindex(idx_rv).dropna()
        variants += 1
    # the same-window comparators, so the RV table compares like with like
    for base in ("SPY buy-and-hold", "CAP500 core", "SPY + trend [same-close]",
                 "CAP500 + trend [same-close]"):
        rv_books[base + " (rv window)"] = books[base].reindex(idx_rv).dropna()

    # ------------------------------------------------------------- reports
    n_trials = N_RUNNING_PRIOR + variants
    spy_full = books["SPY buy-and-hold"]
    for name, r in books.items():
        cards[name] = report(r, rf, spy_full, name, n_trials=n_trials)
    spy_rv = rv_books["SPY buy-and-hold (rv window)"]
    rv_cards = {n: report(r, rf, spy_rv, n, n_trials=n_trials)
                for n, r in rv_books.items()}

    order = list(books)
    _tab([{"book": n,
           "CAGR%": cards[n]["cagr_pct"], "vol%": cards[n]["vol_pct"],
           "Sharpe": cards[n]["sharpe"], "Sortino": cards[n]["sortino"],
           "maxDD%": cards[n]["max_dd_pct"],
           "beta": cards[n]["beta"], "alpha%": cards[n]["alpha_ann_pct"],
           "t_a": cards[n]["t_alpha"],
           "dSh": round(cards[n]["sharpe"] - cards["SPY buy-and-hold"]["sharpe"], 3),
           "dDD": round(cards[n]["max_dd_pct"]
                        - cards["SPY buy-and-hold"]["max_dd_pct"], 2)}
          for n in order],
         ["book", "CAGR%", "vol%", "Sharpe", "Sortino", "maxDD%", "beta",
          "alpha%", "t_a", "dSh", "dDD"],
         f"FULL WINDOW {idx_full[0].date()}..{idx_full[-1].date()} "
         f"({len(idx_full)} sessions), cost {HEADLINE_COST:.0f} bps, "
         "excess of BIL")

    _tab([{"book": n,
           "CAGR%": rv_cards[n]["cagr_pct"], "vol%": rv_cards[n]["vol_pct"],
           "Sharpe": rv_cards[n]["sharpe"], "maxDD%": rv_cards[n]["max_dd_pct"],
           "beta": rv_cards[n]["beta"], "alpha%": rv_cards[n]["alpha_ann_pct"],
           "t_a": rv_cards[n]["t_alpha"],
           "dSh": round(rv_cards[n]["sharpe"] - rv_cards[
               "SPY buy-and-hold (rv window)"]["sharpe"], 3)}
          for n in rv_books],
         ["book", "CAGR%", "vol%", "Sharpe", "maxDD%", "beta", "alpha%",
          "t_a", "dSh"],
         f"RV-SIZING WINDOW {idx_rv[0].date()}..{idx_rv[-1].date()} "
         f"({len(idx_rv)} sessions), cost {HEADLINE_COST:.0f} bps")

    # ------------------------------------- halves, thirds for the headliners
    headline = ["SPY buy-and-hold", "CAP500 core", "SPY + trend [same-close]",
                "CAP500 + trend [same-close]", "SPY + trend [next-close]",
                "CAP500 + trend [next-close]", "SPY + trend + rv (spliced)",
                "CAP500 + trend + rv (spliced)"]
    for n in headline:
        c = cards[n]
        print(f"\n{n}")
        for tag, rows in (("halves", c["halves"]), ("thirds", c["thirds"])):
            for i, s in enumerate(rows):
                print(f"    {tag[:-1]} {i+1} {s['span']}: "
                      f"CAGR {s['book_cagr']:>7.2f} vs SPY {s['spy_cagr']:>7.2f} | "
                      f"Sharpe {s['book_sharpe']:>6.3f} vs {s['spy_sharpe']:>6.3f} "
                      f"(d {s['d_sharpe']:+.3f}) | maxDD {s['book_maxdd']:>7.2f} "
                      f"vs {s['spy_maxdd']:>7.2f} (d {s['d_maxdd']:+.2f})")
        d = c["vs_spy"]
        print(f"    vs SPY: {d['ann_diff_pct']:+.2f} pp/yr (t {d['t_nw']}), "
              f"alpha {d['alpha_ann_pct']:+.2f}% (t {d['t_alpha']}), "
              f"beta {d['beta']:+.3f}")
        print(f"      diff halves: "
              f"{[(x['ann_pct'], x['t']) for x in d['halves']]}")
        print(f"      diff thirds: "
              f"{[(x['ann_pct'], x['t']) for x in d['thirds']]}")

    # ------------------------------------------------ spells and whipsaws
    spells = {}
    for sig_key in ("sma200", "sma150", "sma250", "sma10m"):
        s = spell_stats(sigs[sig_key].reindex(idx_full).ffill(),
                           spy.reindex(idx_full), bil.reindex(idx_full), lag=1)
        s.pop("spell_lengths")
        spells[sig_key] = s
    _tab([dict(rule=k, **v) for k, v in spells.items()],
         ["rule", "time_in_market_pct", "round_trips_per_year", "out_spells",
          "whipsaws", "whipsaw_share_pct", "whipsaw_total_drag_pct",
          "median_out_spell_days", "longest_out_spell_days"],
         "THE RISK RULE'S OWN BEHAVIOUR (same-close)")

    # ------------------------------------------------------------- controls
    print("\nCONTROL (a)+(b): matched time-in-market and rotated signal, "
          f"{args.draws} draws each")
    sig200 = sigs["sma200"].reindex(idx_full).ffill().dropna()
    lengths = spell_stats(sig200, spy.reindex(idx_full),
                             bil.reindex(idx_full), lag=1)["spell_lengths"]
    nulls = {}
    for core_key, label in (("SPY", "SPY + trend [same-close]"),
                            ("CAP500", "CAP500 + trend [same-close]")):
        r_core, turn = core_series(core_key)
        nulls[label] = null_block_from_series(
            books[label], r_core.reindex(idx_full), bil.reindex(idx_full),
            None if turn is None else turn.reindex(idx_full),
            rf.reindex(idx_full), sig200, lengths, 1, HEADLINE_COST,
            args.draws, np.random.default_rng(args.seed))
        for nm, v in nulls[label].items():
            print(f"  {label:32s} {nm:22s} "
                  f"Sharpe real {v['real_sharpe']:.3f} vs null mean "
                  f"{v['sharpe_mean']:.3f} p95 {v['sharpe_p95']:.3f} "
                  f"-> pctile {v['sharpe_pctile']:.1f} | "
                  f"maxDD real {v['real_maxdd']:.2f} vs null mean "
                  f"{v['maxdd_mean']:.2f} -> pctile {v['maxdd_pctile']:.1f}")

    # ---- the SIZING rule's own decisive control: matched AVERAGE EXPOSURE --
    print("\nCONTROL: matched AVERAGE EXPOSURE (the sizing analogue of matched "
          "time-in-market) and rotated forecast")
    size_nulls = {}
    for core_key, sig_key, size, label in rv_specs:
        r_core, turn = core_series(core_key)
        r_core = r_core.reindex(idx_rv)
        turn = None if turn is None else turn.reindex(idx_rv)
        w = size.reindex(spy.index).ffill()
        if sig_key is not None:
            w = w * sigs[sig_key].reindex(spy.index).ffill()
        w = w.reindex(idx_rv)
        flat = null_matched_exposure(w, r_core, bil.reindex(idx_rv), turn,
                                     rf.reindex(idx_rv), 1, HEADLINE_COST)
        rot = null_rotate_weight(w, r_core, bil.reindex(idx_rv), turn,
                                 rf.reindex(idx_rv), 1, HEADLINE_COST,
                                 args.draws, np.random.default_rng(args.seed))
        real = rv_cards[label]
        size_nulls[label] = {
            "real_sharpe": real["sharpe"], "real_maxdd": real["max_dd_pct"],
            "real_cagr": real["cagr_pct"],
            "flat_weight": flat["constant_weight"],
            "flat_sharpe": flat["sharpe"], "flat_maxdd": flat["max_dd_pct"],
            "flat_cagr": flat["cagr_pct"],
            "rot_sharpe_mean": round(float(rot["sharpe"].mean()), 3),
            "rot_sharpe_p95": round(float(rot["sharpe"].quantile(0.95)), 3),
            "sharpe_pctile_vs_rot": pctile(rot["sharpe"], real["sharpe"]),
            "rot_maxdd_mean": round(float(rot["maxdd"].mean()), 2),
            "maxdd_pctile_vs_rot": pctile(rot["maxdd"], real["max_dd_pct"]),
        }
        v = size_nulls[label]
        print(f"  {label:28s} real Sharpe {v['real_sharpe']:.3f} | flat "
              f"w={v['flat_weight']:.3f} Sharpe {v['flat_sharpe']:.3f} "
              f"maxDD {v['flat_maxdd']:.2f} | rotated mean {v['rot_sharpe_mean']:.3f} "
              f"p95 {v['rot_sharpe_p95']:.3f} -> pctile {v['sharpe_pctile_vs_rot']:.1f}"
              f" | maxDD real {v['real_maxdd']:.2f} vs rot mean "
              f"{v['rot_maxdd_mean']:.2f} -> pctile {v['maxdd_pctile_vs_rot']:.1f}")

    # the same control for the TREND arm, which also reduces average exposure
    for core_key, label in (("SPY", "SPY + trend [same-close]"),
                            ("CAP500", "CAP500 + trend [same-close]")):
        r_core, turn = core_series(core_key)
        flat = null_matched_exposure(
            sigs["sma200"].reindex(spy.index).ffill().reindex(idx_full),
            r_core.reindex(idx_full), bil.reindex(idx_full),
            None if turn is None else turn.reindex(idx_full),
            rf.reindex(idx_full), 1, HEADLINE_COST)
        nulls[label]["matched_average_exposure"] = {
            "constant_weight": flat["constant_weight"],
            "flat_sharpe": flat["sharpe"], "flat_cagr": flat["cagr_pct"],
            "flat_maxdd": flat["max_dd_pct"],
            "real_sharpe": cards[label]["sharpe"],
            "real_cagr": cards[label]["cagr_pct"],
            "real_maxdd": cards[label]["max_dd_pct"]}
        f = nulls[label]["matched_average_exposure"]
        print(f"  {label:28s} real Sharpe {f['real_sharpe']:.3f} CAGR "
              f"{f['real_cagr']:.2f} maxDD {f['real_maxdd']:.2f} | flat "
              f"w={f['constant_weight']:.3f} Sharpe {f['flat_sharpe']:.3f} CAGR "
              f"{f['flat_cagr']:.2f} maxDD {f['flat_maxdd']:.2f}")

    # --------------------------------------- the cap-coverage diagnostic (e)
    cov = cores["CAP500"]["cap_coverage_by_year"]
    d_cap = (books["CAP500 core"] - spy_full).dropna()
    n = len(d_cap)
    cov_rows = []
    for i in range(3):
        seg = d_cap.iloc[int(round(i * n / 3)):int(round((i + 1) * n / 3))]
        yrs = sorted({int(y) for y in seg.index.year})
        cvals = [cov.get(y, np.nan) for y in yrs if y in cov]
        mu, se, t = nw_mean_t(seg.to_numpy(), lag=NW_LAG)
        cov_rows.append({"third": i + 1,
                         "span": f"{seg.index[0].date()}..{seg.index[-1].date()}",
                         "mean_cap_coverage": round(float(np.mean(cvals)), 3),
                         "CAP500_minus_SPY_pp_yr": round(100 * mu * TD_YEAR, 2),
                         "t": round(t, 2)})
    # and the same difference restricted to the HIGH-COVERAGE era, where the
    # core really is the whole index rather than the part of it whose share
    # count SEC XBRL could resolve.
    hi_from = pd.Timestamp("2022-01-03", tz="US/Eastern")
    seg = d_cap.loc[d_cap.index >= hi_from]
    mu_h, se_h, t_h = nw_mean_t(seg.to_numpy(), lag=NW_LAG)
    ab_h = ols_alpha_beta(seg.to_numpy(),
                          (spy_full - rf).reindex(seg.index).to_numpy(), lag=NW_LAG)
    cov_hi = {"span": f"{seg.index[0].date()}..{seg.index[-1].date()}",
              "n": int(len(seg)),
              "mean_cap_coverage": round(float(np.mean(
                  [cov[y] for y in cov if y >= 2022])), 3),
              "CAP500_minus_SPY_pp_yr": round(100 * mu_h * TD_YEAR, 2),
              "t_nw": round(t_h, 2),
              "alpha_ann_pct": ab_h["alpha_ann_pct"], "t_alpha": ab_h["t_alpha"],
              "beta": ab_h["beta"]}
    _tab(cov_rows, ["third", "span", "mean_cap_coverage",
                    "CAP500_minus_SPY_pp_yr", "t"],
         "CONTROL (e): is the core's edge concentrated where cap coverage is worst?")
    print(f"  high-coverage era only ({cov_hi['span']}, coverage "
          f"{cov_hi['mean_cap_coverage']:.3f}, n={cov_hi['n']}): "
          f"{cov_hi['CAP500_minus_SPY_pp_yr']:+.2f} pp/yr (t {cov_hi['t_nw']}), "
          f"alpha {cov_hi['alpha_ann_pct']:+.2f}% (t {cov_hi['t_alpha']}), "
          f"beta {cov_hi['beta']:+.3f}")

    # ------------------------------------------------------- levered to SPY
    print("\nTHE DECIDING TEST — lever each book's EXCESS return to SPY's own "
          "realised excess volatility")
    lev_rows = []
    for n_ in headline + ["60/40 SPY/IEF (monthly)"]:
        for causal in (False, True):
            m = lever_to(books[n_], rf, spy_full, borrow=BORROW_SPREAD,
                         causal=causal)
            lev_rows.append({"book": n_, "L": "trailing" if causal else "fullsample",
                             "mean_L": m["leverage_mean"],
                             "CAGR%": m["cagr_pct"], "vol%": m["vol_pct"],
                             "Sharpe": m["sharpe"], "maxDD%": m["max_dd_pct"],
                             "SPY CAGR (same rows)": m["bench_cagr_same_rows"],
                             "SPY maxDD (same rows)": m["bench_maxdd_same_rows"],
                             "vs SPY CAGR": round(m["cagr_pct"]
                                                  - m["bench_cagr_same_rows"], 2)})
    _tab(lev_rows, ["book", "L", "mean_L", "CAGR%", "vol%", "Sharpe", "maxDD%",
                    "SPY CAGR (same rows)", "SPY maxDD (same rows)",
                    "vs SPY CAGR"],
         f"levered, borrow = bills + {int(BORROW_SPREAD*1e4)} bps")

    # the SAME deciding test for the full stack, on the RV window, against SPY
    # measured on those same rows
    lev_rv_rows = []
    for n_ in ["SPY buy-and-hold (rv window)", "CAP500 core (rv window)",
               "SPY + trend [same-close] (rv window)", "SPY + rv1.0",
               "SPY + trend + rv1.0", "CAP500 + trend + rv1.0"]:
        for causal in (False, True):
            m = lever_to(rv_books[n_], rf, spy_rv, borrow=BORROW_SPREAD,
                         causal=causal)
            lev_rv_rows.append({"book": n_, "L": "trailing" if causal else "fullsample",
                                "mean_L": m["leverage_mean"],
                                "CAGR%": m["cagr_pct"], "vol%": m["vol_pct"],
                                "Sharpe": m["sharpe"], "maxDD%": m["max_dd_pct"],
                                "SPY CAGR (same rows)": m["bench_cagr_same_rows"],
                                "SPY maxDD (same rows)": m["bench_maxdd_same_rows"],
                                "vs SPY CAGR": round(m["cagr_pct"]
                                                     - m["bench_cagr_same_rows"], 2)})
    _tab(lev_rv_rows, ["book", "L", "mean_L", "CAGR%", "vol%", "Sharpe",
                       "maxDD%", "SPY CAGR (same rows)", "SPY maxDD (same rows)",
                       "vs SPY CAGR"],
         "the same deciding test for the FULL STACK, on the RV window")

    borrow_sens = {}
    for bs in BORROW_GRID:
        m = lever_to(books["SPY + trend [same-close]"], rf, spy_full,
                     borrow=bs, causal=True)
        borrow_sens[int(bs * 1e4)] = {"cagr_pct": m["cagr_pct"],
                                      "sharpe": m["sharpe"],
                                      "maxdd_pct": m["max_dd_pct"]}
    print(f"  borrow sensitivity (SPY+trend, trailing L): {borrow_sens}")

    # ------------------------------------------------------------ costs
    print("\nCOSTS")
    cost_rows = []
    for core_key, sig_key, label in (("SPY", "sma200", "SPY + trend"),
                                     ("CAP500", "sma200", "CAP500 + trend"),
                                     ("CAP500", None, "CAP500 core")):
        r_core, turn = core_series(core_key)
        w = ones if sig_key is None else sigs[sig_key]
        row = {"book": label,
               "traded/yr": round(traded_per_year(
                   w.reindex(spy.index).ffill(), r_core.reindex(idx_full),
                   None if turn is None else turn.reindex(idx_full)), 3)}
        for c in COST_GRID:
            r = build_stack(w.reindex(spy.index).ffill(),
                            r_core.reindex(idx_full), bil.reindex(idx_full),
                            None if turn is None else turn.reindex(idx_full),
                            lag=1, cost_bps=c).dropna()
            m = metrics(r, rf)
            row[f"S@{int(c)}"] = m["sharpe"]
            row[f"C@{int(c)}"] = m["cagr_pct"]
        row["breakeven_bps_vs_SPY_sharpe"] = breakeven_cost(
            w.reindex(spy.index).ffill(), r_core.reindex(idx_full),
            bil.reindex(idx_full),
            None if turn is None else turn.reindex(idx_full),
            rf, 1, cards["SPY buy-and-hold"]["sharpe"])
        cost_rows.append(row)
    _tab(cost_rows, ["book", "traded/yr"] + [f"S@{int(c)}" for c in COST_GRID]
         + [f"C@{int(c)}" for c in COST_GRID] + ["breakeven_bps_vs_SPY_sharpe"],
         "Sharpe and CAGR at 0/5/10/20 bps per unit traded, and the break-even")

    # ------------------------------------------- Rule 16 bootstrap with MC sd
    print("\nRule 14/16: Sharpe differences vs SPY, block bootstrap, re-seeded")
    boots = {}
    for n_ in headline[1:]:
        a = (books[n_] - rf.reindex(books[n_].index)).dropna()
        b = (spy_full - rf.reindex(spy_full.index)).reindex(a.index)
        boots[n_] = boot_t_with_mc_sd(a.to_numpy(), b.to_numpy())
        print(f"  {n_:34s} t {boots[n_]['t']:+.3f}  MC sd {boots[n_]['mc_sd_of_t']:.3f}")

    # ------------------------------------------------------------- episodes
    print("\nEPISODES (the risk rule's job, measured where it matters)")
    eps = {}
    for n_ in headline:
        eps[n_] = episode_report(books[n_], spy_full)
    for name in EPISODES:
        line = []
        for n_ in headline:
            e = eps[n_].get(name)
            if e:
                line.append(f"{n_.split(' [')[0][:14]:>14s} {e['book_ret_pct']:+7.2f}%")
        print(f"  {name:20s} " + " | ".join(line))

    # -------------------------------------- Rule 9 for the monthly variant
    print("\nRule 9: entry-phase pooling for the MONTHLY overlay variant")
    phase_rows = []
    for ph in range(21):
        s = sig_sma_monthly(close, 10, phase=ph)
        r = build_stack(s.reindex(spy.index).ffill(), spy.reindex(idx_full),
                        bil.reindex(idx_full), None, lag=1,
                        cost_bps=HEADLINE_COST).dropna()
        m = metrics(r, rf)
        phase_rows.append({"phase": ph, "CAGR%": m["cagr_pct"],
                           "Sharpe": m["sharpe"], "maxDD%": m["max_dd_pct"]})
    pdf = pd.DataFrame(phase_rows)
    print(f"  21 phases: Sharpe {pdf['Sharpe'].mean():.3f} "
          f"[{pdf['Sharpe'].min():.3f}, {pdf['Sharpe'].max():.3f}] sd "
          f"{pdf['Sharpe'].std(ddof=1):.3f}; CAGR {pdf['CAGR%'].mean():.2f}% "
          f"[{pdf['CAGR%'].min():.2f}, {pdf['CAGR%'].max():.2f}]; "
          f"maxDD {pdf['maxDD%'].mean():.2f}% "
          f"[{pdf['maxDD%'].min():.2f}, {pdf['maxDD%'].max():.2f}]")
    print(f"  calendar-month-end version: Sharpe "
          f"{cards['SPY + trend10m [same-close]']['sharpe']}, "
          f"maxDD {cards['SPY + trend10m [same-close]']['max_dd_pct']}%")

    out = {
        "hypothesis": "H36",
        "run_utc": t_start.isoformat(),
        "window": {"full": [str(idx_full[0].date()), str(idx_full[-1].date()),
                            len(idx_full)],
                   "rv": [str(idx_rv[0].date()), str(idx_rv[-1].date()),
                          len(idx_rv)]},
        "audit": lp["audit"],
        "core_meta": {k: {kk: v[kk] for kk in
                          ("label", "turnover_oneway_per_yr",
                           "cap_coverage_by_year", "n_split_repairs",
                           "n_stale_killed", "n_day_dirty", "n_symbols")}
                      for k, v in cores.items()},
        "cards": cards,
        "rv_cards": rv_cards,
        "spells": spells,
        "nulls": nulls,
        "size_nulls": size_nulls,
        "cap_coverage_diagnostic": cov_rows,
        "levered": lev_rows,
        "levered_rv_window": lev_rv_rows,
        "cap_coverage_high_era": cov_hi,
        "borrow_sensitivity": borrow_sens,
        "costs": cost_rows,
        "bootstrap": boots,
        "episodes": eps,
        "monthly_phases": phase_rows,
        "variants_run": variants,
        "n_trials_for_deflation": n_trials,
        "headline_cost_bps": HEADLINE_COST,
        "seed": args.seed,
        "draws": args.draws,
    }
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nvariants run: {variants};  deflation N = {n_trials}")
    print(f"written: {RESULTS}")
    print(f"elapsed: {(datetime.now(timezone.utc) - t_start).total_seconds():.0f}s")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--draws", type=int, default=NULL_DRAWS)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    run(args)


if __name__ == "__main__":
    main()
