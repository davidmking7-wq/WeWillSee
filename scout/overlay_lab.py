"""H35 — a real return source with a risk rule doing only its own job.

TWO JOBS, STATED BEFORE ANY NUMBER
==================================
RETURN SOURCE: the equity premium, held through SPY. It is the only thing five
rounds of this repo have found that reliably makes money (SPY CAGR 14.99%,
Sharpe 1.004 on this window). No stock is selected and none should be — every
cross-sectional price signal tested here turned out to be beta or survivorship.

RISK RULE: a slow trend filter computed on the INDEX ITSELF. Its job is to be
out of the market during PROLONGED declines, and nothing else. It cannot
predict crashes, it WILL be whipsawed by sharp ones, and in a decade the index
tripled it must cost raw return. Mechanism, one sentence: a market trading
below a long moving average has, empirically, a higher conditional variance and
a fatter left tail than one above it (Faber 2007; Moskowitz-Ooi-Pedersen 2012;
Hurst-Ooi-Pedersen 2017), so leaving it there truncates the left tail at the
cost of some of the right one.

Judged accordingly: the return source on RETURN, the risk rule on DRAWDOWN and
on RISK-ADJUSTED return. A risk rule that costs raw return while cutting
drawdown has not failed; the question is whether the trade is worth it, and
the only honest way to ask "does it beat the market" is to lever its excess
return to the market's own volatility (g = S^2/2) and compare CAGR.

WHY THIS IS NOT A RE-RUN OF H5a/H5b/H5c/H5g
-------------------------------------------
`sma200ok` exists in scout/signals.py only as a CROSS-SECTIONAL stock gate.
H5a-H5d applied regime rules to the concentrated STOCK PICKS and were rejected
on compounded return ("crash windows average +0.52%", "cash there costs
return"). H5g scaled volatility on a stock book, capped at 1x, and was judged
on return. H11/H20 vol-targeted SPY but scored it with no risk-free rate at
all. Nobody has applied a trend rule to the INDEX, funded the cash leg with a
real bill, and judged it on the axis the rule is for. That is the gap.

DATA (US EQUITIES ONLY — ETFs as benchmark / cash leg, per the scope)
---------------------------------------------------------------------
  SPY  the return source and the benchmark   — scout/bars.py master cache
  BIL  SPDR 1-3 Month T-Bill ETF             — THE CASH LEG AND THE RISK-FREE
  IEF  7-10y Treasury, for the 60/40 control
All three are Alpaca SIP daily closes with adjustment=all, i.e. TOTAL return.
BIL/IEF live in scout/sleeve_bars.pkl (the same master pull; this file checks
that its SPY column is bit-identical to the master cache's, and it is).

THE RISK-FREE RATE IS NOT OPTIONAL (this round's non-negotiable #1)
-------------------------------------------------------------------
H32 died partly because `sharpe()` ran on RAW returns and alpha regressed raw
on raw: at beta 0.27 the omitted rf x (1 - beta) term was ~1.75%/yr and turned
alpha +2.39% (t 1.02) into +0.76% (t 0.33). A rule that SITS IN CASH has that
problem at its maximum — this book's beta is ~0.7. So:
  * when out of the market the book EARNS BIL's actual daily total return;
  * every Sharpe and Sortino is computed on returns in EXCESS of BIL;
  * every alpha/beta regresses EXCESS on EXCESS.
`scout/beatspy_lab.py` hard-codes RF_SENSITIVITY = 0.02; that is not used here.
Measured BIL total return by year on this sample: 2017 0.69%, 2018 1.74%,
2019 2.04%, 2020 0.39%, 2021 -0.09%, 2022 1.39%, 2023 4.98%, 2024 5.19%,
2025 4.19% — a real bill curve, not a constant.

EXECUTION — WHERE THE SHIFT IS (this round's non-negotiable #2)
---------------------------------------------------------------
The signal at date t uses closes <= t and NOTHING later.
  SAME-CLOSE (headline): trade at the close of t, so the position held over
      (close t -> close t+1) is sig[t] and it earns r[t+1].
      In code: w = sig.shift(1) aligned to the return date. ONE shift.
      Realistic for a 200-day SMA: the average of the last 200 closes is known
      to 1/200th of the day's move minutes before the bell, so the sign of
      (close - SMA200) is known before the close except in a near-tie.
  NEXT-CLOSE (conservative): trade at the close of t+1, w = sig.shift(2).
Both are reported for every variant. Entries and exits fall on different days;
there is no intraday trading anywhere in this file.

The vol-target arm's forecast fc[t] is the H20 HAR-log 5-minute realised
variance forecast FOR session t built only from sessions <= t-1 — the same
information set as sig[t-1], so it enters the same-close book at the same
place. `--extra-lag` is the next-close convention for it as well.

DATA DEFECTS — WHICH GUARD, AND WHY (all three named in the brief)
------------------------------------------------------------------
 1. UNADJUSTED SPLITS (5.1% of the universe). SPY and BIL have never split on
    this window; the guard is a hard assertion that no |daily return| exceeds
    25% for any of the three ETFs. Measured maxima: SPY 10.78% (2020-03-16),
    BIL 0.077%, IEF 1.9%. Reported, not assumed.
 2. SPIN-OFF / REUSED-TICKER >50% MOVES. Same assertion covers it; none fire.
 3. FROZEN QUOTES. The repo's rule is "retire a symbol at its first run of ~10
    identical closes". That rule MUST NOT be applied to BIL: a 1-3 month bill
    ETF legitimately prints the same close for days (its whole daily range is
    ~1 cent) and retiring it would delete the cash leg. Instead BIL is
    validated on a property a frozen quote cannot fake — its ANNUAL total
    return has to track the actual bill curve, and it does (table above,
    2021 slightly negative, 2023-25 near 5%). SPY is checked for identical-
    close runs directly; the longest is reported.

CONTROLS (the first is decisive)
--------------------------------
 (a) RANDOM TIMING WITH MATCHED TIME-IN-MARKET, 500 draws each, two nulls:
     A1 i.i.d. out-days (same COUNT of days in cash, scattered), and
     A2 BLOCK-MATCHED (the real rule's exact multiset of out-spell lengths,
        placed at random) — A2 is the hard one, because it matches both the
        time in market and the persistence of the exposure.
     If the real rule sits inside these, the "edge" is just reduced exposure
     in a volatile decade and H35 is dead.
 (b) always-invested SPY, and 60/40 SPY/IEF rebalanced monthly.
 (c) both halves AND equal thirds.
 (d) SHUFFLED SIGNAL: circular rotation of the signal series by a random
     offset (500 draws) — preserves the run structure and the time in market
     exactly, destroys only the alignment with the market.

REGISTERED ROWS (scout/hypotheses.md H35a-H35h, written before this ran)
  a  the trend overlay cuts max drawdown materially vs buy-and-hold SPY
  b  it COSTS raw CAGR in this decade  (registered as an EXPECTED cost, not a
     failure — this is the row the reviewer's point is about)
  c  it raises the Sharpe of excess-over-BIL returns
  d  THE DECIDING ROW: levered to SPY's realised vol with a real borrow
     spread, its CAGR beats SPY's
  e  it beats matched-time-in-market random timing (both nulls)
  f  the drawdown gain is consistent across both halves and all three thirds
  g  the 5-minute RV vol-target arm adds to the trend arm
  h  Rule 9: no conclusion depends on the monthly rule's entry phase

Usage:
    python -m scout.overlay_lab                 # full run
    python -m scout.overlay_lab --selftest      # lookahead + machinery proofs
    python -m scout.overlay_lab --draws 500 --seed 20260809
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import bars, config, growth as g

TD_YEAR = 252
SLEEVE_PKL = config.SCOUT_DIR / "sleeve_bars.pkl"
RESULTS = config.SCOUT_DIR / "overlay_results.json"

START = "2016-01-04"
END = "2026-08-07"
MAX_ABS_RET = 0.25          # guard 1+2: no ETF here may move this much in a day

# Costs. A full SPY->BIL switch trades 100% of the book twice (sell one, buy
# the other). SPY quotes ~0.15 bps of spread and BIL ~1 bp; commissions are
# zero at every retail broker. HEADLINE_COST is charged per unit of |dw|, so
# 5 bps is roughly 3x the true half-spread cost of a full switch — deliberately
# generous. 1x and 2x are both reported plus the exact break-even.
HEADLINE_COST = 5.0
COST_GRID = (0.0, 5.0, 10.0, 20.0)

# Financing above the bill rate for the levered comparison. A box spread or an
# ES future finances at ~25-50 bps over bills; a retail margin loan is far
# worse. Headline 50 bps, sensitivity 25/100/200.
BORROW_SPREAD = 0.0050
BORROW_GRID = (0.0025, 0.0050, 0.0100, 0.0200)

MAX_LEV = 2.0
TARGET_VOL = 0.12
SEED = 20260809
BOOT_REPS = 2000
BLOCK = 21
NULL_DRAWS = 500

# Registry N BEFORE this hypothesis: 729 after H31d, plus H32/H33(51)/H34(112).
N_RUNNING_PRIOR = 950

EPISODES = {
    "2018Q4 selloff":   ("2018-09-20", "2018-12-24"),
    "2020 COVID crash": ("2020-02-19", "2020-03-23"),
    "2020 full round":  ("2020-02-19", "2020-08-31"),
    "2022 bear":        ("2022-01-03", "2022-10-12"),
    "2022 full round":  ("2022-01-03", "2024-01-19"),
}


# ==========================================================================
# 1. Data and its guards
# ==========================================================================

def load_prices(quiet: bool = False) -> dict:
    """SPY from the shared master cache; BIL/IEF from sleeve_bars.pkl.

    Both files are the same Alpaca SIP adjustment=all pull — this function
    asserts that by comparing their SPY columns, and refuses to continue if
    they disagree by more than 1e-12 on any overlapping day."""
    px = bars.get(["SPY"], START, END, verbose=not quiet)
    spy = px["close"]["SPY"].dropna()

    with open(SLEEVE_PKL, "rb") as f:
        sl = pickle.load(f)
    for need in ("BIL", "IEF", "SPY"):
        if need not in sl.columns:
            raise RuntimeError(f"{SLEEVE_PKL.name} has no {need} column")
    bil = sl["BIL"].dropna()
    ief = sl["IEF"].dropna()

    both = spy.index.intersection(sl["SPY"].dropna().index)
    dev = float((spy.reindex(both) - sl["SPY"].reindex(both)).abs().max())
    if dev > 1e-9:
        raise RuntimeError(f"SPY disagrees between caches by {dev}")

    frame = pd.DataFrame({"SPY": spy, "BIL": bil, "IEF": ief}).sort_index()
    audit = guard(frame, quiet=quiet)
    return {"px": frame, "audit": audit, "spy_cache_dev": dev}


def guard(frame: pd.DataFrame, quiet: bool = False) -> dict:
    """Defects 1-3. Assertions, not assumptions; every number is reported."""
    rets = frame.pct_change()
    worst = {c: (float(rets[c].abs().max()),
                 str(rets[c].abs().idxmax().date())) for c in frame.columns}
    bad = {c: v for c, (v, _) in worst.items() if v > MAX_ABS_RET}
    if bad:
        raise RuntimeError(f"guard 1/2 fired — implausible daily moves: {bad}")

    # guard 3: identical-close runs. Applied to SPY (a frozen SPY quote would
    # be a real data failure). NOT applied to BIL — see the module docstring.
    def longest_run(s: pd.Series) -> int:
        d = (s.diff() == 0).astype(int)
        best = run = 0
        for v in d.to_numpy():
            run = run + 1 if v else 0
            best = max(best, run)
        return int(best) + 1 if best else 1

    spy_run = longest_run(frame["SPY"])
    bil_run = longest_run(frame["BIL"])
    if spy_run >= 10:
        raise RuntimeError(f"guard 3 fired — SPY has {spy_run} identical closes")

    bilr = frame["BIL"].pct_change().dropna()
    by_year = (bilr.groupby(bilr.index.year)
               .apply(lambda x: float((1 + x).prod() ** (TD_YEAR / len(x)) - 1)))
    out = {"n_dates": int(len(frame)),
           "span": (str(frame.index[0].date()), str(frame.index[-1].date())),
           "max_abs_daily_ret": worst,
           "spy_longest_identical_close_run": spy_run,
           "bil_longest_identical_close_run": bil_run,
           "bil_annualised_by_year_pct": {int(k): round(100 * v, 2)
                                          for k, v in by_year.items()}}
    if not quiet:
        print("  guards: "
              f"max |1d| SPY {100*worst['SPY'][0]:.2f}% ({worst['SPY'][1]}), "
              f"BIL {100*worst['BIL'][0]:.3f}%, IEF {100*worst['IEF'][0]:.2f}%")
        print(f"          longest identical-close run: SPY {spy_run}, "
              f"BIL {bil_run} (BIL exempt by construction)")
    return out


# ==========================================================================
# 2. Signals.  sig[t] in {0,1} (or a leverage in [0, MAX_LEV]) uses closes <= t.
# ==========================================================================

def sig_sma(close: pd.Series, window: int = 200) -> pd.Series:
    """close[t] > mean(close[t-window+1 .. t]).  Uses t, not t+1."""
    sma = close.rolling(window, min_periods=window).mean()
    return (close > sma).astype(float).where(sma.notna())


def sig_sma_monthly(close: pd.Series, months: int = 10,
                    phase: int | None = None) -> pd.Series:
    """Faber's original: compare the month-end close to the 10-MONTH SMA, and
    only ever act at a month end. Held flat between decision dates.

    `phase=None` uses real calendar month ends. `phase=k` (0..20) instead
    decides every 21st trading day starting at offset k — that is Rule 9's
    entry-phase pooling for a monthly rule, and it is the only place in this
    file where a phase exists."""
    if phase is None:
        dec = close.groupby([close.index.year, close.index.month]).tail(1).index
    else:
        pos = np.arange(len(close))
        dec = close.index[(pos % 21) == (phase % 21)]
    m = close.reindex(dec)
    sma = m.rolling(months, min_periods=months).mean()
    s = (m > sma).astype(float).where(sma.notna())
    return s.reindex(close.index).ffill()


def sig_tsmom(close: pd.Series, rf: pd.Series,
              lookback: int = 252, skip: int = 21) -> pd.Series:
    """12-1 TIME-SERIES momentum: the index's own EXCESS return from t-252 to
    t-21 is positive. Excess, because a positive nominal return in a 5% bill
    world is not a positive signal (Moskowitz-Ooi-Pedersen use excess)."""
    lr = np.log1p(close.pct_change())
    lrf = np.log1p(rf)
    ex = (lr - lrf).rolling(lookback - skip, min_periods=lookback - skip).sum()
    ex = ex.shift(skip)                      # skip the most recent month
    return (ex > 0).astype(float).where(ex.notna())


def sig_dual(a: pd.Series, b: pd.Series) -> pd.Series:
    """Both must agree to be invested; either one out puts the book in cash."""
    return (a * b).where(a.notna() & b.notna())


def rv_leverage(quiet: bool = False) -> pd.Series:
    """H20's CONFIRMED forecaster, turned into a leverage.

    fc[t] = HAR on log 5-minute realised close-to-close variance FOR session t,
    fitted walk-forward on rows whose targets were observed by t-2, and
    `.shift(1)`-ed onto t inside `rv_forecast_lab.har_forecast`. So fc[t] is a
    function of sessions <= t-1 and is settable at the close of t-1 — the same
    information set as sig[t-1]. lev[t] = clip(TARGET_VOL / ann_vol_hat, 0, 2).
    """
    from . import rv_forecast_lab as rv
    panel = rv.load_panel(quiet=quiet)
    fc = rv.har_forecast(panel["rv_cc"][["SPY"]], log=True, pooled=False)["SPY"]
    ann = np.sqrt(TD_YEAR * fc.clip(lower=1e-12))
    lev = (TARGET_VOL / ann).clip(0.0, MAX_LEV)
    idx = pd.DatetimeIndex(lev.index)
    lev.index = (idx.tz_localize("US/Eastern") if idx.tz is None
                 else idx.tz_convert("US/Eastern")).normalize()
    return lev.dropna()


# ==========================================================================
# 3. Books
# ==========================================================================

def build_book(weight: pd.Series, r_spy: pd.Series, r_bil: pd.Series,
               lag: int = 1, cost_bps: float = HEADLINE_COST,
               borrow: float = BORROW_SPREAD) -> pd.Series:
    """Total (not excess) daily return of a book that holds `weight` in SPY and
    the remainder in BIL.

    `lag=1` is SAME-CLOSE: the weight decided from closes <= t is the weight
    held over (close t -> close t+1) and earns r[t+1].  `lag=2` is NEXT-CLOSE.
    Weights above 1 borrow at the bill rate plus `borrow` per annum.
    Costs are charged on |dw| at the moment the weight changes.
    """
    w = weight.reindex(r_spy.index).shift(lag)
    w = w.ffill()
    ok = w.notna()
    w = w.fillna(0.0)
    lev_excess = np.maximum(w - 1.0, 0.0) * borrow / TD_YEAR
    gross = w * r_spy + (1.0 - w) * r_bil - lev_excess
    turn = w.diff().abs().fillna(0.0)
    net = gross - turn * cost_bps / 1e4
    return net.where(ok)


def spell_stats(weight: pd.Series, r_spy: pd.Series, r_bil: pd.Series,
                lag: int = 1) -> dict:
    """Time in market, round trips, and WHIPSAWS.

    A whipsaw is a completed out-of-market spell over which SPY beat BIL — the
    rule stepped aside and the market went up. That is the rule failing at its
    own job in the only way it can fail cheaply, and it is counted, priced and
    reported rather than buried."""
    w = weight.reindex(r_spy.index).shift(lag).ffill().dropna()
    inmkt = (w > 0.5).astype(int)
    entries = int(((inmkt.diff() == 1)).sum())
    exits = int(((inmkt.diff() == -1)).sum())
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
        s = float((1 + r_spy.loc[sl]).prod() - 1)
        c = float((1 + r_bil.loc[sl]).prod() - 1)
        lens.append(int(len(r_spy.loc[sl])))
        if s > c:
            whip += 1
            drag += (s - c)
    return {"time_in_market_pct": round(100 * float(inmkt.mean()), 2),
            "entries": entries, "exits": exits,
            "round_trips_per_year": round(entries / yrs, 2),
            "out_spells": len(spells),
            "whipsaws": whip,
            "whipsaw_share_pct": round(100 * whip / max(len(spells), 1), 1),
            "whipsaw_total_drag_pct": round(100 * drag, 2),
            "median_out_spell_days": int(np.median(lens)) if lens else 0,
            "longest_out_spell_days": int(max(lens)) if lens else 0,
            "spell_lengths": lens}


# ==========================================================================
# 4. Metrics — every risk-adjusted number is EXCESS OF BIL
# ==========================================================================

def _cagr(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 2:
        return float("nan")
    return float((1 + r).prod() ** (TD_YEAR / len(r)) - 1)


def _underwater(r: pd.Series) -> tuple[int, str, str]:
    curve = (1 + r.fillna(0.0)).cumprod()
    peak = curve.cummax()
    under = (curve < peak * (1 - 1e-12)).to_numpy()
    if not under.any():
        return 0, "", ""
    # run lengths of True, vectorised: reset the cumulative count at each False
    idx = np.arange(len(under))
    resets = np.maximum.accumulate(np.where(~under, idx, -1))
    run = np.where(under, idx - resets, 0)
    end = int(np.argmax(run))
    best = int(run[end])
    return best, str(r.index[end - best + 1].date()), str(r.index[end].date())


def metrics(r: pd.Series, rf: pd.Series, label: str = "") -> dict:
    r = r.dropna()
    rf = rf.reindex(r.index)
    ex = (r - rf).dropna()
    dn = ex[ex < 0]
    dd_dev = float(np.sqrt((ex.clip(upper=0.0) ** 2).mean())) if len(ex) else np.nan
    roll12 = np.expm1(np.log1p(r).rolling(TD_YEAR).sum())
    uw, uw_a, uw_b = _underwater(r)
    return {
        "label": label,
        "n": int(len(r)),
        "cagr_pct": round(100 * _cagr(r), 2),
        "vol_pct": round(100 * float(r.std(ddof=1)) * math.sqrt(TD_YEAR), 2),
        "sharpe": round(float(ex.mean() / ex.std(ddof=1) * math.sqrt(TD_YEAR)), 3),
        "sortino": round(float(ex.mean() / dd_dev * math.sqrt(TD_YEAR)), 3)
                   if dd_dev and dd_dev > 0 else float("nan"),
        "max_dd_pct": round(100 * g.max_drawdown(r), 2),
        "longest_underwater_td": int(uw),
        "underwater_span": f"{uw_a}..{uw_b}",
        "worst_12m_pct": round(100 * float(roll12.min()), 2)
                         if roll12.notna().any() else float("nan"),
        "ann_excess_pct": round(100 * (float(ex.mean()) * TD_YEAR), 2),
        "downside_days_pct": round(100 * len(dn) / max(len(ex), 1), 1),
        "skew": round(float(ex.skew()), 2),
        "kurtosis": round(float(ex.kurtosis()) + 3.0, 2),
    }


def ols_alpha_beta(y: np.ndarray, x: np.ndarray, lag: int = 21) -> dict:
    """y = a + b x on EXCESS returns, Newey-West at `lag`. Rule 13's engine."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
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
        wgt = 1 - L / (lag + 1)
        G = u[L:].T @ u[:-L]
        S += wgt * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(cov))
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


# ==========================================================================
# 5. Levering to the market's own volatility — the deciding test
# ==========================================================================

def lever_to_spy(r_book: pd.Series, rf: pd.Series, r_spy: pd.Series,
                 borrow: float = BORROW_SPREAD,
                 causal: bool = False, window: int = TD_YEAR) -> dict:
    """Scale the book's EXCESS return to SPY's realised excess volatility and
    charge `borrow` per annum on the borrowed part.

        r_lev[t] = rf[t] + L[t]*(r_book[t] - rf[t]) - max(L[t]-1,0)*borrow/252

    `causal=False` uses ONE full-sample scalar L = sd(spy_ex)/sd(book_ex) —
    in-sample by construction and labelled as such. `causal=True` recomputes L
    from a trailing 252-day window of both volatilities, which is what a real
    account could have done, and is the number to believe."""
    ex_b = (r_book - rf).dropna()
    ex_s = (r_spy - rf).reindex(ex_b.index)
    if causal:
        L = (ex_s.rolling(window, min_periods=window).std()
             / ex_b.rolling(window, min_periods=window).std()).shift(1)
        L = L.clip(0.0, 4.0)
    else:
        L = pd.Series(float(ex_s.std(ddof=1) / ex_b.std(ddof=1)), index=ex_b.index)
    lev_ex = L * ex_b - np.maximum(L - 1.0, 0.0) * borrow / TD_YEAR
    r_lev = (rf.reindex(ex_b.index) + lev_ex).dropna()
    m = metrics(r_lev, rf, "levered")
    m["leverage_mean"] = round(float(L.reindex(r_lev.index).mean()), 3)
    m["leverage_max"] = round(float(L.reindex(r_lev.index).max()), 3)
    m["causal"] = causal
    m["borrow_bps"] = int(round(borrow * 1e4))
    return m


# ==========================================================================
# 6. Controls
# ==========================================================================

def _weight_from_mask(index: pd.DatetimeIndex, out_pos: np.ndarray) -> pd.Series:
    w = np.ones(len(index))
    w[out_pos] = 0.0
    return pd.Series(w, index=index)


def null_iid(sig: pd.Series, rng, draws: int) -> list[pd.Series]:
    s = sig.dropna()
    n, k = len(s), int((s < 0.5).sum())
    return [_weight_from_mask(s.index, rng.choice(n, size=k, replace=False))
            for _ in range(draws)]


def null_block(sig: pd.Series, lengths: list[int], rng, draws: int) -> list[pd.Series]:
    """Place the REAL multiset of out-spell lengths at random, non-overlapping.
    Matches time in market AND the persistence of the exposure."""
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
    with the market destroyed. The shuffled-signal control (d)."""
    s = sig.dropna()
    n = len(s)
    out = []
    for _ in range(draws):
        k = int(rng.integers(TD_YEAR // 4, n - TD_YEAR // 4))
        out.append(pd.Series(np.roll(s.to_numpy(float), k), index=s.index))
    return out


def run_null(weights: list[pd.Series], r_spy, r_bil, rf, lag, cost) -> pd.DataFrame:
    rows = []
    for w in weights:
        r = build_book(w, r_spy, r_bil, lag=lag, cost_bps=cost)
        m = metrics(r, rf)
        rows.append({"cagr": m["cagr_pct"], "sharpe": m["sharpe"],
                     "maxdd": m["max_dd_pct"], "sortino": m["sortino"]})
    return pd.DataFrame(rows)


def pctile(null: pd.Series, value: float) -> float:
    return round(100 * float((null < value).mean()), 1)


# ==========================================================================
# 7. Significance machinery (Rules 14 and 16)
# ==========================================================================

def block_boot_sharpe_diff(a: np.ndarray, b: np.ndarray, rng,
                           reps: int = BOOT_REPS, block: int = BLOCK) -> np.ndarray:
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


def boot_t_with_mc_sd(a: np.ndarray, b: np.ndarray, seeds=(1, 2, 3, 4, 5)) -> dict:
    """Rule 16: re-seed and report the Monte-Carlo sd of the bootstrap t."""
    ts, ds = [], []
    for s in seeds:
        rng = np.random.default_rng(SEED + s)
        d = block_boot_sharpe_diff(a, b, rng)
        point = ((a.mean() / a.std(ddof=1)) - (b.mean() / b.std(ddof=1))) * math.sqrt(TD_YEAR)
        ts.append(point / d.std(ddof=1))
        ds.append(d.std(ddof=1))
    return {"t": round(float(np.mean(ts)), 3),
            "mc_sd_of_t": round(float(np.std(ts, ddof=1)), 3),
            "boot_sd": round(float(np.mean(ds)), 4)}


# ==========================================================================
# 8. Slicing
# ==========================================================================

def split_report(r: pd.Series, rf: pd.Series, bench: pd.Series, k: int) -> list[dict]:
    """Equal-count split into k pieces, book and benchmark on the same rows."""
    r = r.dropna()
    n = len(r)
    edges = [int(round(i * n / k)) for i in range(k + 1)]
    out = []
    for i in range(k):
        sl = r.index[edges[i]:edges[i + 1]]
        mb = metrics(r.reindex(sl), rf, f"part{i+1}")
        ms = metrics(bench.reindex(sl), rf, f"spy_part{i+1}")
        out.append({"span": f"{sl[0].date()}..{sl[-1].date()}",
                    "book_cagr": mb["cagr_pct"], "spy_cagr": ms["cagr_pct"],
                    "book_sharpe": mb["sharpe"], "spy_sharpe": ms["sharpe"],
                    "book_maxdd": mb["max_dd_pct"], "spy_maxdd": ms["max_dd_pct"],
                    "d_sharpe": round(mb["sharpe"] - ms["sharpe"], 3),
                    "d_maxdd": round(mb["max_dd_pct"] - ms["max_dd_pct"], 2)})
    return out


def episode_report(r: pd.Series, rf: pd.Series, bench: pd.Series) -> dict:
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


# ==========================================================================
# 9. Break-even cost
# ==========================================================================

def breakeven_cost(weight, r_spy, r_bil, rf, lag, target_sharpe,
                   lo: float = -50.0, hi: float = 400.0) -> float:
    """Cost in bps per unit |dw| at which the book's Sharpe equals SPY's.
    Negative means it needs a SUBSIDY, i.e. it loses even for free."""
    def f(c):
        r = build_book(weight, r_spy, r_bil, lag=lag, cost_bps=c)
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
# 10. Self-test — the no-lookahead proof
# ==========================================================================

def selftest(quiet: bool = False) -> int:
    fails = []
    idx = pd.bdate_range("2016-01-04", periods=1500, tz="US/Eastern")
    rng = np.random.default_rng(7)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(3e-4, 0.01, len(idx)))), idx)
    rf = pd.Series(np.full(len(idx), 0.02 / TD_YEAR), idx)

    # 1. truncation invariance: a causal signal cannot change when the future
    #    is deleted.
    cut = 1200
    for name, fn in (("sma200", lambda c: sig_sma(c, 200)),
                     ("sma10m", lambda c: sig_sma_monthly(c, 10)),
                     ("tsmom", lambda c: sig_tsmom(c, rf.reindex(c.index)))):
        full = fn(close).iloc[:cut]
        trunc = fn(close.iloc[:cut])
        a, b = full.align(trunc, join="inner")
        if not ((a.isna() & b.isna()) | (a == b)).all():
            fails.append(f"{name}: signal changed when the future was deleted")

    # 2. the shift is where the docstring says it is: a book built on a signal
    #    that is constant-1 must equal SPY minus nothing, and a book on a
    #    signal shifted by hand must equal build_book with lag+1.
    r_spy = close.pct_change()
    r_bil = rf
    ones = pd.Series(1.0, index=idx)
    b1 = build_book(ones, r_spy, r_bil, lag=1, cost_bps=0.0).dropna()
    if abs(float((b1 - r_spy.reindex(b1.index)).abs().max())) > 1e-12:
        fails.append("always-invested book != SPY at zero cost")
    sig = sig_sma(close, 200)
    a = build_book(sig, r_spy, r_bil, lag=2, cost_bps=0.0).dropna()
    b = build_book(sig.shift(1), r_spy, r_bil, lag=1, cost_bps=0.0).dropna()
    j = a.index.intersection(b.index)
    if float((a.reindex(j) - b.reindex(j)).abs().max()) > 1e-12:
        fails.append("lag=2 is not one more shift than lag=1")

    # 3. a LOOKAHEAD signal must be caught by the same machinery — proof the
    #    test can fail. Peeking at tomorrow's return should print a huge Sharpe.
    peek = (r_spy.shift(-1) > 0).astype(float)
    rp = build_book(peek, r_spy, r_bil, lag=1, cost_bps=0.0)
    if metrics(rp, r_bil)["sharpe"] < 5:
        fails.append("lookahead control did not produce an absurd Sharpe")

    # 4. costs only ever reduce return
    hi = build_book(sig, r_spy, r_bil, lag=1, cost_bps=50.0).dropna()
    lo = build_book(sig, r_spy, r_bil, lag=1, cost_bps=0.0).dropna()
    if _cagr(hi) > _cagr(lo):
        fails.append("higher cost produced higher CAGR")

    # 5. levering to the benchmark's vol must reproduce the benchmark's vol
    lv = lever_to_spy(build_book(sig, r_spy, r_bil, 1, 0.0).dropna(), rf, r_spy)
    if abs(lv["vol_pct"] - metrics(r_spy.dropna(), rf)["vol_pct"]) > 0.6:
        fails.append(f"levered vol {lv['vol_pct']} != SPY vol")

    # 6. matched-time-in-market nulls really are matched
    rngx = np.random.default_rng(1)
    real_tim = float((sig.dropna() > 0.5).mean())
    for nm, ws in (("iid", null_iid(sig, rngx, 5)),
                   ("block", null_block(sig, spell_stats(sig, r_spy, r_bil)["spell_lengths"], rngx, 5)),
                   ("rotate", null_rotate(sig, rngx, 5))):
        tims = [float((w > 0.5).mean()) for w in ws]
        if max(abs(t - real_tim) for t in tims) > 0.03:
            fails.append(f"null {nm} time-in-market not matched "
                         f"({real_tim:.3f} vs {tims})")

    if not quiet:
        print(f"selftest: {6 - len(set(f.split(':')[0] for f in fails))}/6 groups ok")
        for f in fails:
            print(f"  FAIL {f}")
        if not fails:
            print("  all checks passed")
    return 1 if fails else 0


# ==========================================================================
# 11. The run
# ==========================================================================

def _tab(rows: list[dict], cols: list[str], title: str) -> None:
    print(f"\n{title}")
    w = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  " + "  ".join(c.rjust(w[c]) for c in cols))
    print("  " + "  ".join("-" * w[c] for c in cols))
    for r in rows:
        print("  " + "  ".join(str(r.get(c, "")).rjust(w[c]) for c in cols))


def run(args) -> dict:
    rng = np.random.default_rng(args.seed)
    out: dict = {"generated": datetime.now(timezone.utc).isoformat(),
                 "seed": args.seed}

    print("=" * 78)
    print("H35 — trend overlay on the INDEX, with a real bill as the cash leg")
    print("=" * 78)
    print("\nJOB SEPARATION, before any number:")
    print("  RETURN SOURCE = the equity premium (SPY). Judged on RETURN.")
    print("  RISK RULE     = a slow trend filter on SPY itself. Judged on")
    print("                  DRAWDOWN and on RISK-ADJUSTED return.")
    print("  CASH LEG      = BIL, earning the actual bill rate when out.\n")

    d = load_prices()
    px, audit = d["px"], d["audit"]
    out["audit"] = audit
    print(f"  prices: {audit['n_dates']} sessions {audit['span'][0]}..{audit['span'][1]}"
          f"  (SPY master-vs-sleeve max deviation {d['spy_cache_dev']:.1e})")

    close = px["SPY"]
    r_spy = close.pct_change()
    r_bil = px["BIL"].pct_change()
    r_ief = px["IEF"].pct_change()
    rf = r_bil

    # ---------------------------------------------------------------- signals
    sigs = {
        "SMA200":        sig_sma(close, 200),
        "SMA10M":        sig_sma_monthly(close, 10),
        "TSMOM12_1":     sig_tsmom(close, rf, 252, 21),
    }
    sigs["DUAL"] = sig_dual(sigs["SMA200"], sigs["TSMOM12_1"])

    # common sample: every arm decides on the same days (Rule 17)
    valid = None
    for s in sigs.values():
        v = s.dropna().index
        valid = v if valid is None else valid.intersection(v)
    valid = valid[valid >= pd.Timestamp("2016-01-04", tz="US/Eastern")]
    sample = r_spy.index[(r_spy.index > valid[0]) & r_spy.notna() & r_bil.notna()]
    print(f"  common decision sample: {valid[0].date()}..{valid[-1].date()}"
          f"  ({len(sample)} return days, {len(sample)/TD_YEAR:.2f} years)")
    out["sample"] = {"first_decision": str(valid[0].date()),
                     "last_decision": str(valid[-1].date()),
                     "return_days": int(len(sample)),
                     "years": round(len(sample) / TD_YEAR, 2)}

    r_spy_s = r_spy.reindex(sample)
    r_bil_s = r_bil.reindex(sample)
    r_ief_s = r_ief.reindex(sample)
    rf_s = r_bil_s

    # ------------------------------------------------------------ benchmarks
    ones = pd.Series(1.0, index=close.index)
    books: dict[str, pd.Series] = {}
    weights: dict[str, pd.Series] = {}

    books["SPY buy&hold"] = build_book(ones, r_spy_s, r_bil_s, 1, 0.0)
    weights["SPY buy&hold"] = ones

    # 60/40 SPY/IEF, rebalanced on the last trading day of each month
    m_ends = set(pd.Series(sample, index=sample)
                 .groupby([sample.year, sample.month]).tail(1))
    ws, wi = 0.6, 0.4
    rows6040 = []
    for dt in sample:
        rs = r_spy_s.get(dt, 0.0)
        ri = r_ief_s.get(dt, 0.0)
        rs = 0.0 if not np.isfinite(rs) else rs
        ri = 0.0 if not np.isfinite(ri) else ri
        tot = ws * (1 + rs) + wi * (1 + ri)
        rows6040.append(tot - 1)
        ws, wi = ws * (1 + rs) / tot, wi * (1 + ri) / tot
        if dt in m_ends:
            ws, wi = 0.6, 0.4
    books["60/40 SPY/IEF"] = pd.Series(rows6040, index=sample)

    # ------------------------------------------------------------ trend books
    variants = 0
    for name, s in sigs.items():
        for lag, tag in ((1, "same-close"), (2, "next-close")):
            key = f"{name} [{tag}]"
            books[key] = build_book(s, r_spy_s, r_bil_s, lag=lag,
                                    cost_bps=args.cost)
            weights[key] = s
            variants += 1

    hdr = ["label", "cagr_pct", "vol_pct", "sharpe", "sortino", "max_dd_pct",
           "longest_underwater_td", "worst_12m_pct"]
    rows = []
    allm = {}
    for k, r in books.items():
        m = metrics(r, rf_s, k)
        allm[k] = m
        rows.append(m)
    _tab(rows, hdr, f"MAIN PANEL — costs {args.cost:.0f} bps per unit |dw|, "
                    f"Sharpe/Sortino EXCESS OF BIL")
    out["main_panel"] = allm

    spy_m = allm["SPY buy&hold"]
    ex_spy = (books["SPY buy&hold"] - rf_s).dropna()

    # --------------------------------------------------- Rule 13: beta/alpha
    ab_rows = []
    for k, r in books.items():
        ex_b = (r - rf_s).reindex(ex_spy.index)
        ab = ols_alpha_beta(ex_b.to_numpy(), ex_spy.to_numpy())
        diff = (ex_b - ex_spy)
        abd = ols_alpha_beta(diff.to_numpy(), ex_spy.to_numpy())
        mu, se, t = nw_mean_t(diff.dropna().to_numpy())
        ab_rows.append({"label": k, "beta": ab["beta"], "alpha_pct": ab["alpha_ann_pct"],
                        "t_alpha": ab["t_alpha"], "r2": ab["r2"],
                        "diff_beta": abd["beta"], "diff_alpha_pct": abd["alpha_ann_pct"],
                        "t_diff_alpha": abd["t_alpha"],
                        "diff_ann_pct": round(100 * mu * TD_YEAR, 2),
                        "t_diff_NW21": round(t, 2)})
    _tab(ab_rows, ["label", "beta", "alpha_pct", "t_alpha", "r2",
                   "diff_beta", "diff_alpha_pct", "t_diff_alpha",
                   "diff_ann_pct", "t_diff_NW21"],
         "RULE 13 — beta and market-adjusted alpha on EXCESS-OF-BIL returns, "
         "for every book AND every difference (book - SPY)")
    out["rule13"] = ab_rows

    # ------------------------------------------------------- exposure stats
    ex_rows = []
    for name, s in sigs.items():
        st = spell_stats(s, r_spy_s, r_bil_s, lag=1)
        st = {kk: vv for kk, vv in st.items() if kk != "spell_lengths"}
        st["label"] = name
        ex_rows.append(st)
    _tab(ex_rows, ["label", "time_in_market_pct", "round_trips_per_year",
                   "out_spells", "whipsaws", "whipsaw_share_pct",
                   "whipsaw_total_drag_pct", "median_out_spell_days",
                   "longest_out_spell_days"],
         "EXPOSURE — what the risk rule actually did")
    out["exposure"] = ex_rows

    # ------------------------------------------------------------- episodes
    print("\nEPISODES — the declines the rule exists for")
    ep_all = {}
    for name in list(sigs) :
        key = f"{name} [same-close]"
        ep = episode_report(books[key], rf_s, books["SPY buy&hold"])
        ep_all[key] = ep
    eprows = []
    for epname in EPISODES:
        row = {"episode": epname}
        any_ = False
        for name in sigs:
            key = f"{name} [same-close]"
            if epname in ep_all[key]:
                row[name] = ep_all[key][epname]["book_ret_pct"]
                row["SPY"] = ep_all[key][epname]["spy_ret_pct"]
                row[f"{name}_dd"] = ep_all[key][epname]["book_maxdd_pct"]
                row["SPY_dd"] = ep_all[key][epname]["spy_maxdd_pct"]
                any_ = True
        if any_:
            eprows.append(row)
    _tab(eprows, ["episode", "SPY", "SMA200", "SMA10M", "TSMOM12_1",
                  "SPY_dd", "SMA200_dd", "SMA10M_dd", "TSMOM12_1_dd"],
         "  total return % over the window, then max drawdown % inside it")
    out["episodes"] = ep_all

    # --------------------------------------------- halves and equal thirds
    print("\nHALVES AND EQUAL THIRDS (rule 4 — the check that killed H22)")
    out["splits"] = {}
    for name in list(sigs) + ["60/40 SPY/IEF"]:
        key = f"{name} [same-close]" if name in sigs else name
        for k, tag in ((2, "halves"), (3, "thirds")):
            rr = split_report(books[key], rf_s, books["SPY buy&hold"], k)
            out["splits"][f"{key}|{tag}"] = rr
            _tab(rr, ["span", "book_cagr", "spy_cagr", "book_sharpe",
                      "spy_sharpe", "d_sharpe", "book_maxdd", "spy_maxdd",
                      "d_maxdd"], f"  {key} — {tag}")

    # ---------------------------------------------------------- cost ladder
    print("\nCOSTS — every variant at 0 / 1x / 2x / 4x, and the break-even")
    crows = []
    for name, s in sigs.items():
        row = {"label": name}
        for c in COST_GRID:
            r = build_book(s, r_spy_s, r_bil_s, 1, c)
            m = metrics(r, rf_s)
            row[f"S@{c:.0f}"] = m["sharpe"]
            row[f"CAGR@{c:.0f}"] = m["cagr_pct"]
        row["breakeven_bps_vs_SPY_sharpe"] = breakeven_cost(
            s, r_spy_s, r_bil_s, rf_s, 1, spy_m["sharpe"])
        crows.append(row)
    _tab(crows, ["label"] + [f"S@{c:.0f}" for c in COST_GRID]
         + [f"CAGR@{c:.0f}" for c in COST_GRID] + ["breakeven_bps_vs_SPY_sharpe"],
         "  Sharpe and CAGR by cost, then the cost at which Sharpe = SPY's")
    out["costs"] = crows
    variants += len(sigs) * len(COST_GRID)

    # ------------------------------------------------- THE DECIDING SECTION
    print("\n" + "=" * 78)
    print("THE DECIDING TEST — lever the EXCESS return to SPY's own realised")
    print("volatility, charge borrowing above 1x, compare CAGR to SPY's.")
    print("=" * 78)
    lev_rows = []
    for name in sigs:
        key = f"{name} [same-close]"
        for causal in (False, True):
            lv = lever_to_spy(books[key].dropna(), rf_s, books["SPY buy&hold"],
                              borrow=args.borrow, causal=causal)
            lev_rows.append({"label": f"{name} {'trailing-252 L' if causal else 'full-sample L'}",
                             "L_mean": lv["leverage_mean"], "L_max": lv["leverage_max"],
                             "cagr_pct": lv["cagr_pct"], "vol_pct": lv["vol_pct"],
                             "sharpe": lv["sharpe"], "max_dd_pct": lv["max_dd_pct"],
                             "vs_SPY_cagr": round(lv["cagr_pct"] - spy_m["cagr_pct"], 2)})
            variants += 1
    lev_rows.append({"label": "SPY buy&hold", "L_mean": 1.0, "L_max": 1.0,
                     "cagr_pct": spy_m["cagr_pct"], "vol_pct": spy_m["vol_pct"],
                     "sharpe": spy_m["sharpe"], "max_dd_pct": spy_m["max_dd_pct"],
                     "vs_SPY_cagr": 0.0})
    _tab(lev_rows, ["label", "L_mean", "L_max", "cagr_pct", "vol_pct", "sharpe",
                    "max_dd_pct", "vs_SPY_cagr"],
         f"  borrow spread {args.borrow*1e4:.0f} bps/yr over the bill rate")
    out["levered"] = lev_rows

    brows = []
    for name in sigs:
        key = f"{name} [same-close]"
        row = {"label": name}
        for bsp in BORROW_GRID:
            lv = lever_to_spy(books[key].dropna(), rf_s, books["SPY buy&hold"],
                              borrow=bsp, causal=True)
            row[f"{int(bsp*1e4)}bps"] = round(lv["cagr_pct"] - spy_m["cagr_pct"], 2)
        brows.append(row)
        variants += len(BORROW_GRID)
    _tab(brows, ["label"] + [f"{int(b*1e4)}bps" for b in BORROW_GRID],
         "  levered CAGR minus SPY's, by borrowing spread (trailing-252 L)")
    out["borrow_sensitivity"] = brows

    # --------------------------------------------------------- CONTROL (a)
    print("\n" + "=" * 78)
    print("CONTROL (a) — RANDOM TIMING WITH MATCHED TIME IN MARKET.")
    print("If the real rule sits inside this null, the 'edge' is just reduced")
    print("exposure in a volatile decade and H35 is dead.")
    print("=" * 78)
    null_rows = []
    out["nulls"] = {}
    for name, s in sigs.items():
        key = f"{name} [same-close]"
        real = allm[key]
        lens = spell_stats(s, r_spy_s, r_bil_s, 1)["spell_lengths"]
        for nm, mk in (("A1 iid", lambda: null_iid(s, np.random.default_rng(args.seed + 11), args.draws)),
                       ("A2 block", lambda: null_block(s, lens, np.random.default_rng(args.seed + 22), args.draws)),
                       ("D rotate", lambda: null_rotate(s, np.random.default_rng(args.seed + 33), args.draws))):
            nulldf = run_null(mk(), r_spy_s, r_bil_s, rf_s, 1, args.cost)
            rec = {"label": f"{name} vs {nm}",
                   "real_sharpe": real["sharpe"],
                   "null_sharpe_mean": round(float(nulldf["sharpe"].mean()), 3),
                   "null_sharpe_sd": round(float(nulldf["sharpe"].std(ddof=1)), 3),
                   "pctile_sharpe": pctile(nulldf["sharpe"], real["sharpe"]),
                   "real_maxdd": real["max_dd_pct"],
                   "null_maxdd_mean": round(float(nulldf["maxdd"].mean()), 2),
                   "pctile_maxdd": pctile(nulldf["maxdd"], real["max_dd_pct"]),
                   "real_cagr": real["cagr_pct"],
                   "null_cagr_mean": round(float(nulldf["cagr"].mean()), 2),
                   "pctile_cagr": pctile(nulldf["cagr"], real["cagr_pct"]),
                   "z_sharpe": round((real["sharpe"] - float(nulldf["sharpe"].mean()))
                                     / max(float(nulldf["sharpe"].std(ddof=1)), 1e-9), 2)}
            null_rows.append(rec)
            out["nulls"][rec["label"]] = rec
            variants += 1
    _tab(null_rows, ["label", "real_sharpe", "null_sharpe_mean", "null_sharpe_sd",
                     "z_sharpe", "pctile_sharpe", "real_maxdd", "null_maxdd_mean",
                     "pctile_maxdd", "real_cagr", "null_cagr_mean", "pctile_cagr"],
         f"  {args.draws} draws each. pctile = the real rule's rank inside the null "
         f"(higher is better for Sharpe/CAGR; for maxdd higher = shallower).")

    # ------------------------------------------------- Rules 14 and 16
    print("\nRULE 14 / RULE 16 — the SE of the Sharpe difference, three ways")
    sig_rows = []
    for name in sigs:
        key = f"{name} [same-close]"
        a = (books[key] - rf_s).dropna()
        b = ex_spy.reindex(a.index)
        bt = boot_t_with_mc_sd(a.to_numpy(), b.to_numpy())
        d = (a - b).to_numpy()
        mu, se_nw, t_nw = nw_mean_t(d)
        rot = run_null(null_rotate(sigs[name], np.random.default_rng(args.seed + 55), args.draws),
                       r_spy_s, r_bil_s, rf_s, 1, args.cost)
        perm_sd = float(rot["sharpe"].std(ddof=1))
        sig_rows.append({"label": name,
                         "d_sharpe": round(allm[key]["sharpe"] - spy_m["sharpe"], 3),
                         "boot_t": bt["t"], "mc_sd_of_t": bt["mc_sd_of_t"],
                         "boot_sd": bt["boot_sd"],
                         "rotation_sd": round(perm_sd, 4),
                         "ratio_rot_over_boot": round(perm_sd / max(bt["boot_sd"], 1e-9), 2),
                         "d_ann_ret_pct": round(100 * mu * TD_YEAR, 2),
                         "t_ret_NW21": round(t_nw, 2)})
    _tab(sig_rows, ["label", "d_sharpe", "boot_t", "mc_sd_of_t", "boot_sd",
                    "rotation_sd", "ratio_rot_over_boot", "d_ann_ret_pct",
                    "t_ret_NW21"],
         "  boot_t = Sharpe(book)-Sharpe(SPY) over its block-bootstrap sd, "
         "5 seeds; rotation_sd is the shuffled-signal SE (Rule 14's ratio)")
    out["significance"] = sig_rows

    # ------------------------------------------------- Rule 9: entry phases
    print("\nRULE 9 — entry phases. The only phase-dependent rule here is the")
    print("MONTHLY one; all 21 offsets are pooled.")
    ph = []
    for k in range(21):
        s = sig_sma_monthly(close, 10, phase=k)
        r = build_book(s, r_spy_s, r_bil_s, 1, args.cost)
        m = metrics(r, rf_s)
        ph.append({"phase": k, "cagr": m["cagr_pct"], "sharpe": m["sharpe"],
                   "maxdd": m["max_dd_pct"]})
        variants += 1
    pdf = pd.DataFrame(ph)
    out["phases"] = {"rows": ph,
                     "sharpe_mean": round(float(pdf["sharpe"].mean()), 3),
                     "sharpe_sd": round(float(pdf["sharpe"].std(ddof=1)), 3),
                     "sharpe_min": float(pdf["sharpe"].min()),
                     "sharpe_max": float(pdf["sharpe"].max()),
                     "cagr_mean": round(float(pdf["cagr"].mean()), 2),
                     "cagr_sd": round(float(pdf["cagr"].std(ddof=1)), 2),
                     "maxdd_mean": round(float(pdf["maxdd"].mean()), 2),
                     "maxdd_sd": round(float(pdf["maxdd"].std(ddof=1)), 2),
                     "pct_phases_beating_spy_sharpe":
                         round(100 * float((pdf["sharpe"] > spy_m["sharpe"]).mean()), 1)}
    print(f"  SMA10M over 21 phases: Sharpe {out['phases']['sharpe_mean']} "
          f"+- {out['phases']['sharpe_sd']} "
          f"[{out['phases']['sharpe_min']}, {out['phases']['sharpe_max']}], "
          f"CAGR {out['phases']['cagr_mean']} +- {out['phases']['cagr_sd']}%, "
          f"maxDD {out['phases']['maxdd_mean']} +- {out['phases']['maxdd_sd']}%")
    print(f"  phases beating SPY's Sharpe ({spy_m['sharpe']}): "
          f"{out['phases']['pct_phases_beating_spy_sharpe']}%")

    # --------------------------------------------- SMA-length sensitivity
    print("\nSENSITIVITY (labelled as such — this IS a sweep, so it is "
          "exploratory)")
    srows = []
    for wdw in (100, 125, 150, 200, 250, 300):
        s = sig_sma(close, wdw)
        r = build_book(s, r_spy_s, r_bil_s, 1, args.cost)
        m = metrics(r, rf_s)
        srows.append({"sma": wdw, "cagr_pct": m["cagr_pct"], "sharpe": m["sharpe"],
                      "max_dd_pct": m["max_dd_pct"],
                      "time_in_mkt": spell_stats(s, r_spy_s, r_bil_s, 1)["time_in_market_pct"]})
        variants += 1
    _tab(srows, ["sma", "cagr_pct", "sharpe", "max_dd_pct", "time_in_mkt"],
         "  SMA length sweep")
    out["sma_sweep"] = srows

    # ------------------------------------------------ the vol-target arm
    print("\n" + "=" * 78)
    print("H35g — the 5-minute realised-variance arm (H20's CONFIRMED forecaster)")
    print("Its own window (the 5-min cache starts 2018-01-02 and HAR needs a")
    print("year of pairs), so EVERY arm below is recomputed on that window.")
    print("=" * 78)
    try:
        lev = rv_leverage(quiet=True)
        rv_sample = sample.intersection(lev.dropna().index)
        rv_sample = rv_sample[rv_sample >= lev.dropna().index[0]]
        rs2, rb2 = r_spy.reindex(rv_sample), r_bil.reindex(rv_sample)
        rf2 = rb2
        rv_books = {"SPY buy&hold": build_book(ones, rs2, rb2, 1, 0.0)}
        rv_books["SMA200"] = build_book(sigs["SMA200"], rs2, rb2, 1, args.cost)
        rv_books["VOLTGT_RV"] = build_book(lev, rs2, rb2, 1, args.cost,
                                           borrow=args.borrow)
        rv_books["SMA200 x VOLTGT_RV"] = build_book(
            (sigs["SMA200"].reindex(lev.index).ffill() * lev).dropna(),
            rs2, rb2, 1, args.cost, borrow=args.borrow)
        rv_books["VOLTGT_RV [next-close]"] = build_book(lev, rs2, rb2, 2, args.cost,
                                                        borrow=args.borrow)
        variants += 4
        rvrows = [metrics(r, rf2, k) for k, r in rv_books.items()]
        _tab(rvrows, hdr, "  2018-2026 sub-window, vol target "
                          f"{TARGET_VOL:.0%}, cap {MAX_LEV}x")
        # levered comparison on this window too
        spy2 = metrics(rv_books["SPY buy&hold"], rf2)
        lrows = []
        for k in ("SMA200", "VOLTGT_RV", "SMA200 x VOLTGT_RV"):
            lv = lever_to_spy(rv_books[k].dropna(), rf2, rv_books["SPY buy&hold"],
                              borrow=args.borrow, causal=True)
            lrows.append({"label": k, "L_mean": lv["leverage_mean"],
                          "cagr_pct": lv["cagr_pct"], "vol_pct": lv["vol_pct"],
                          "sharpe": lv["sharpe"], "max_dd_pct": lv["max_dd_pct"],
                          "vs_SPY_cagr": round(lv["cagr_pct"] - spy2["cagr_pct"], 2)})
            variants += 1
        lrows.append({"label": "SPY buy&hold", "L_mean": 1.0,
                      "cagr_pct": spy2["cagr_pct"], "vol_pct": spy2["vol_pct"],
                      "sharpe": spy2["sharpe"], "max_dd_pct": spy2["max_dd_pct"],
                      "vs_SPY_cagr": 0.0})
        _tab(lrows, ["label", "L_mean", "cagr_pct", "vol_pct", "sharpe",
                     "max_dd_pct", "vs_SPY_cagr"],
             "  levered to SPY's vol on the 2018-2026 window (trailing-252 L)")
        rvsp = {}
        for k in ("SMA200", "VOLTGT_RV", "SMA200 x VOLTGT_RV"):
            rvsp[k] = {"halves": split_report(rv_books[k], rf2, rv_books["SPY buy&hold"], 2),
                       "thirds": split_report(rv_books[k], rf2, rv_books["SPY buy&hold"], 3)}
            _tab(rvsp[k]["halves"], ["span", "book_sharpe", "spy_sharpe", "d_sharpe",
                                     "book_maxdd", "spy_maxdd", "d_maxdd"],
                 f"  {k} — halves (2018-2026 window)")
            _tab(rvsp[k]["thirds"], ["span", "book_sharpe", "spy_sharpe", "d_sharpe",
                                     "book_maxdd", "spy_maxdd", "d_maxdd"],
                 f"  {k} — thirds (2018-2026 window)")
        out["rv_arm"] = {"panel": rvrows, "levered": lrows, "splits": rvsp,
                         "span": (str(rv_sample[0].date()), str(rv_sample[-1].date())),
                         "n": int(len(rv_sample))}
    except Exception as e:
        print(f"  RV arm unavailable: {type(e).__name__}: {e}")
        out["rv_arm"] = {"error": f"{type(e).__name__}: {e}"}

    # ---------------------------------------------------- deflated Sharpe
    n_total = N_RUNNING_PRIOR + variants
    ds = {}
    for name in sigs:
        key = f"{name} [same-close]"
        m = allm[key]
        ex_b = (books[key] - rf_s).dropna()
        ds[name] = {
            "sharpe": m["sharpe"],
            "dsr_vs_zero": round(g.deflated_sharpe(
                m["sharpe"] / math.sqrt(TD_YEAR), n_total, len(ex_b),
                skew=float(ex_b.skew()), kurtosis=float(ex_b.kurtosis()) + 3.0), 4),
            "dsr_vs_SPY": round(g.deflated_sharpe(
                m["sharpe"] / math.sqrt(TD_YEAR), n_total, len(ex_b),
                skew=float(ex_b.skew()), kurtosis=float(ex_b.kurtosis()) + 3.0,
                sr_benchmark=spy_m["sharpe"] / math.sqrt(TD_YEAR)), 4)}
    out["deflated_sharpe"] = {"n_trials_used": n_total,
                              "n_prior": N_RUNNING_PRIOR,
                              "variants_this_lab": variants, "rows": ds}
    print(f"\nDEFLATED SHARPE at the registry's running N = {n_total} "
          f"({N_RUNNING_PRIOR} prior + {variants} here)")
    for k, v in ds.items():
        print(f"  {k:12s} Sharpe {v['sharpe']:.3f}  DSR vs 0 = {v['dsr_vs_zero']:.4f}"
              f"   DSR vs SPY's Sharpe = {v['dsr_vs_SPY']:.4f}")

    out["variants_run"] = variants
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nwrote {RESULTS}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.overlay_lab")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--draws", type=int, default=NULL_DRAWS)
    ap.add_argument("--cost", type=float, default=HEADLINE_COST)
    ap.add_argument("--borrow", type=float, default=BORROW_SPREAD)
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    run(args)


if __name__ == "__main__":
    main()
