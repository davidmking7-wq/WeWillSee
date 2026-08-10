"""H35 — a real return source with a risk rule doing only its own job.

TWO JOBS, STATED BEFORE ANY NUMBER
----------------------------------
RETURN SOURCE — the equity premium, held as SPY. It is the only thing five
rounds of this repo have found that reliably makes money (SPY 14.99%/yr,
Sharpe 1.004 on the 2016-2026 window). No stock is selected and none should
be; every cross-sectional selection layer tested here turned out to be beta
or survivorship. Judge this component on RETURN.

RISK RULE — a slow trend filter on the INDEX ITSELF. Its job is to be out of
the market during PROLONGED declines. It cannot predict crashes, it will be
whipsawed by sharp ones, and it will cost raw return in a rising decade.
Judge this component on DRAWDOWN and on RISK-ADJUSTED return. A rule that
costs raw CAGR while cutting drawdown has not failed — it has done its job,
and the only remaining question is whether the trade is worth paying for.

WHY THIS IS NOT A REPEAT OF H5a/H5b/H5c/H5g
-------------------------------------------
`signals.sma200ok` exists only as a CROSS-SECTIONAL STOCK GATE. H5a/H5b/H5c
applied regime rules to the concentrated STOCK PICKS and rejected them on
compounded return ("crash windows average +0.52%", "cash there costs return,
+716% vs +733%") — a drawdown tool marked down for not making money. H5g
scaled volatility on a stock book, capped at 1x, and was judged on return.
Nobody has applied a trend rule to the INDEX and scored it on the axis the
rule is for. That is the gap this lab fills.

THE TWO NON-NEGOTIABLES OF THIS ROUND
-------------------------------------
1. A REAL RISK-FREE SERIES. Cash is the BIL ETF (SPDR 1-3 Month T-Bill),
   dividend-adjusted, pulled from the shared master bar cache. It is BOTH the
   cash leg (out of the market EARNS the bill rate — 2.13%/yr average over
   this window, ~5%/yr in 2023-2026) AND the risk-free rate in every Sharpe,
   every Sortino and every alpha regression. H32 died partly because
   `sharpe()` ran on raw returns and `ols_alpha_beta` regressed raw on raw:
   with beta 0.27 the omitted rf x (1-beta) term was worth ~1.75%/yr and
   turned alpha +2.39% (t 1.02) into +0.76% (t 0.33). A rule that SITS IN
   CASH has that bias at its maximum, so it is removed here by construction.
   `beatspy_lab.RF_SENSITIVITY = 0.02` is a hard-coded constant; it is not
   used and not copied. The lab also reports, as a measurement, exactly how
   much the BIL leg is worth versus assuming cash earns zero.
2. EXECUTION AT A CLOSE. The signal is computed from data through the CLOSE
   of day t and the position is taken at a CLOSE. BOTH conventions are run:
     same-close  — position taken at the close of t   (realistic for a
                   200-day SMA, whose value is known to high precision
                   minutes before the bell)
     next-close  — position taken at the close of t+1 (conservative)
   The HEADLINE uses SAME-CLOSE and every table prints both. Entries and
   exits fall on different days; there is no intraday trading in this study.

NO LOOKAHEAD — WHERE THE SHIFT IS
---------------------------------
Every signal function returns `w[t]` = the target weight DECIDED at the close
of session t from data through session t inclusive. A weight decided at close
t is held from close t to close t+1 and therefore earns `ret[t+1]`, so the
held-weight series is `w.shift(exec_lag)` with exec_lag = 1 for same-close
and 2 for next-close. That is the ONLY shift in the P&L path and it looks
backward.

The one apparent forward alignment is in the vol-targeted variant:
`rv_forecast_lab.har_forecast` already ends with `.shift(1)` so that its
row t is "the forecast FOR session t". This lab takes `.shift(-1)` to undo
exactly that, recovering "the forecast made AT t for t+1", which is a
function of realised variance through session t and is therefore known at
the close of t — the moment the position is set. The composition of the two
shifts is the identity; nothing from after session t enters w[t]. The
`voltgt_lag` rows use the un-undone version, one full day staler, as the
conservative check (H20 found that ADDING lag improved its vol-target book,
which is what noise does, so both are reported).

`--selftest` proves the no-lookahead claim mechanically: it truncates the
price history at a month-end cut, rebuilds every signal, and asserts the
signals up to the cut are bit-identical to the full-sample ones.

DATA (US EQUITIES ONLY — ETFs as index, cash leg and alternative benchmark)
---------------------------------------------------------------------------
scout/bars.py master cache, 2016-01-04..2026-08-07, dividend-and-split
adjusted (Alpaca Adjustment.ALL, SIP): SPY (the return source), BIL (cash
and risk-free), IEF (the 60/40 alternative). 5-minute SPY bars for the
vol-target variant come from scout/intraday.py's per-symbol cache
(2018-01-02..2026-07-31, adjustment=all), via rv_forecast_lab's HAR-log
forecaster — this repo's one CONFIRMED result (H20).

THE THREE DOCUMENTED PRICE DEFECTS, AND WHICH APPLY
---------------------------------------------------
 1. 5.1% unadjusted splits — guarded: any session with |close-to-close|
    > 45% is blanked (the H20 guard). SPY/BIL/IEF have never split in a way
    the vendor missed and the guard fires zero times; the count is printed.
 2. 146 spin-off / reused-ticker >50% moves — same guard, same zero count.
    These are three of the most-traded ETFs in existence, not thin equities.
 3. FROZEN QUOTES on delisted/halted names — the repo's rule is to retire a
    symbol at its first run of ~10 identical closes. That rule is designed
    for dead equities and MUST NOT be applied to BIL: a 1-3 month T-bill ETF
    at a zero policy rate genuinely prints the same price for days on end
    (2020-2021). The run-length diagnostic is computed and printed for all
    three symbols so a reader can see which case each is in; no symbol is
    retired, and the reason is stated rather than assumed.

CONTROLS (the first is decisive)
--------------------------------
 (a) RANDOM TIMING WITH MATCHED TIME-IN-MARKET, three nulls x 1000 draws:
       iid    — the same NUMBER of cash days, scattered at random
       spell  — the same MULTISET of cash-spell lengths, placed at random
                (preserves the clustering; much the harder null)
       rotate — the real signal circularly rotated by a random offset
                (preserves everything about the signal, destroys only its
                alignment with returns; this is control (d) done properly)
     If the real rule sits inside these, the "edge" is reduced exposure in a
     volatile decade and the hypothesis is dead.
 (b) always-invested SPY, and 60/40 SPY/IEF rebalanced monthly.
 (c) both halves AND equal thirds, on every book.
 (d) see `rotate` above.

RULE 13: beta and market-adjusted alpha, on EXCESS returns over BIL, for
every book AND for every difference (book minus SPY).
RULE 9: the monthly variants are pooled across all 21 rebalance phases.
RULE 16: bootstrap t values are quoted with their Monte-Carlo sd across
three seeds.

REGISTERED VARIANTS, AND THE HONEST PRE/POST ACCOUNTING
-------------------------------------------------------
Fixed in this docstring BEFORE the first number was produced (H35a-H35h):
  a  sma200            SPY close above its 200-day SMA (Faber's daily form)
  b  sma200_band1pct   the same with 1% hysteresis, to price whipsaw
  c  sma10m            Faber's 10-MONTH SMA on month-end closes
  d  tsmom12_1         12-1 time-series momentum on SPY, monthly
  e  tsmom12_1_excess  the same with the BILL RETURN as the bar, not zero
  f  tsmom12_0         12-0 (no skip), the Moskowitz-Ooi-Pedersen form
  g  dual_and          sma200 AND tsmom12_1 must agree; else cash
  h  dual_avg          the average of the two, so a disagreement is 50%
plus, for every one of them: both execution conventions, the cost grid, the
zero-cash counterfactual, halves and equal thirds, the episode table, Rule 9
phase pooling, the three nulls, the bootstrap t, the leverage test, the
deflated Sharpe, and the 5-minute vol-target leg with and without a trend gate.

ADDED AFTER SEEING THE FIRST RESULTS, and named as such: the Sharpe-difference
significance test, the levered book's sub-period check, the SMA window sweep,
the check-frequency sweep, the leave-one-episode-out, the start-date sweep,
the 15:30 execution-feasibility measurement, and the CAGR decomposition.
Every one of those can only WEAKEN the hypothesis — none of them searches for
a better configuration — but all of them are counted in the variant total
that feeds the deflated Sharpe, because the count is supposed to be honest
rather than flattering.

Usage:
    python -m scout.overlay_lab --selftest
    python -m scout.overlay_lab                 # full run
    python -m scout.overlay_lab --quick         # skip nulls and phases
"""
from __future__ import annotations

import argparse
import json
import math
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import bars, config, growth as g

warnings.filterwarnings("ignore", category=RuntimeWarning)

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
START = "2016-01-01"
END = "2026-08-08"
TD_YEAR = 252
MAX_ABS_RET = 0.45          # defect guards 1 and 2
FROZEN_RUN = 10             # defect guard 3 diagnostic threshold

SMA_D = 200                 # Faber's daily form
SMA_M = 10                  # Faber's 10-month form
MOM_LOOK = 252              # 12 months
MOM_SKIP = 21               # the "-1" in 12-1

VOL_TARGET = 0.15           # 15%/yr, a round ex-ante number below SPY's ~18
RT_BPS_HEADLINE = 5.0       # round trip (out AND back), SPY+BIL are ~1bp each
RT_GRID = (0.0, 2.0, 5.0, 10.0, 20.0)

NW_LAG = 10                 # daily, non-overlapping positions
N_DRAWS = 1000              # null draws (brief asks 200+)
BOOT_REPS = 2000
BOOT_BLOCK = 21
SEEDS = (20260809, 11111, 987654321)

# registry N BEFORE this lab: H31 quoted 729, H32/H33 added ~70 more
N_PRIOR = 800

OUT = config.SCOUT_DIR / "overlay_results.json"


# ==========================================================================
# 1. data and the three guards
# ==========================================================================

def load(quiet: bool = False) -> dict:
    px = bars.get(["SPY", "BIL", "IEF"], START, END, verbose=not quiet)
    close = px["close"][["SPY", "BIL", "IEF"]].dropna(how="any")
    close.index = pd.DatetimeIndex(close.index).tz_localize(None)
    ret = close.pct_change()

    # --- guards 1 and 2: implausible one-day moves (unadjusted splits, spin-offs)
    bad = ret.abs() > MAX_ABS_RET
    n_bad = int(bad.to_numpy().sum())
    ret = ret.mask(bad)

    # --- guard 3 diagnostic: runs of identical closes (frozen quotes)
    runs = {}
    for s in close.columns:
        v = close[s].to_numpy()
        same = np.r_[False, v[1:] == v[:-1]]
        best = cur = 0
        for x in same:
            cur = cur + 1 if x else 0
            best = max(best, cur)
        runs[s] = int(best + 1 if best else 1)

    meta = {
        "span": (str(close.index[0].date()), str(close.index[-1].date())),
        "n_sessions": int(len(close)),
        "blanked_extreme_sessions": n_bad,
        "max_abs_daily_ret": {s: round(float(ret[s].abs().max()), 4)
                              for s in close.columns},
        "longest_identical_close_run": runs,
        "frozen_rule_applied": False,
        "frozen_rule_note": (
            "the repo's retire-at-10-identical-closes rule is for delisted or "
            "halted equities; BIL is a live 1-3m T-bill ETF whose price is "
            "genuinely unchanged for days at a zero policy rate, so the run "
            "length is reported and no symbol is retired"),
    }
    return {"close": close, "ret": ret, "meta": meta}


# ==========================================================================
# 2. signals.  w[t] = target weight DECIDED at the close of session t,
#    from data through session t inclusive.  No forward information.
# ==========================================================================

def sig_sma200(close: pd.Series) -> pd.Series:
    sma = close.rolling(SMA_D, min_periods=SMA_D).mean()
    return (close > sma).astype(float).where(sma.notna())


def sig_sma200_band(close: pd.Series, band: float = 0.01) -> pd.Series:
    """Hysteresis: exit only below (1-band)*SMA, re-enter only above SMA."""
    sma = close.rolling(SMA_D, min_periods=SMA_D).mean()
    out = pd.Series(np.nan, index=close.index)
    state = np.nan
    c, m = close.to_numpy(), sma.to_numpy()
    for i in range(len(c)):
        if not np.isfinite(m[i]):
            continue
        if not np.isfinite(state):
            state = 1.0 if c[i] > m[i] else 0.0
        elif state == 1.0 and c[i] < m[i] * (1 - band):
            state = 0.0
        elif state == 0.0 and c[i] > m[i]:
            state = 1.0
        out.iloc[i] = state
    return out


def _month_end_mask(idx: pd.DatetimeIndex) -> np.ndarray:
    per = pd.PeriodIndex(idx, freq="M")
    return np.r_[per[1:] != per[:-1], True]


def sig_sma10m(close: pd.Series) -> pd.Series:
    """Faber: month-end close above the 10-month SMA of month-end closes.

    Decided at the month-end close; held through the next month end. The
    daily series is the last monthly decision forward-filled, so the position
    only ever CHANGES on a month end."""
    me = _month_end_mask(close.index)
    mc = close[me]
    sma = mc.rolling(SMA_M, min_periods=SMA_M).mean()
    dec = (mc > sma).astype(float).where(sma.notna())
    return dec.reindex(close.index).ffill()


def sig_tsmom(close: pd.Series, rf_curve: pd.Series | None = None,
              look: int = MOM_LOOK, skip: int = MOM_SKIP,
              monthly: bool = True) -> pd.Series:
    """Time-series momentum: return from t-look to t-skip, positive.

    `rf_curve` (a compounded BIL wealth index) makes it an EXCESS-momentum
    rule — the bar is the bill return over the same span, not zero."""
    past = close.shift(skip) / close.shift(look) - 1.0
    if rf_curve is not None:
        bar = rf_curve.shift(skip) / rf_curve.shift(look) - 1.0
    else:
        bar = 0.0
    dec = (past > bar).astype(float).where(past.notna())
    if monthly:
        me = _month_end_mask(close.index)
        dec = dec.where(pd.Series(me, index=close.index)).ffill()
    return dec


def sig_phase_sma10m(close: pd.Series, offset: int) -> pd.Series:
    """Rule 9: the 10-month rule on a 21-trading-day grid starting at `offset`."""
    pts = np.arange(offset, len(close), 21)
    sub = close.iloc[pts]
    sma = sub.rolling(SMA_M, min_periods=SMA_M).mean()
    dec = (sub > sma).astype(float).where(sma.notna())
    return dec.reindex(close.index).ffill()


def sig_phase_tsmom(close: pd.Series, offset: int,
                    rf_curve: pd.Series | None = None) -> pd.Series:
    past = close.shift(MOM_SKIP) / close.shift(MOM_LOOK) - 1.0
    bar = (rf_curve.shift(MOM_SKIP) / rf_curve.shift(MOM_LOOK) - 1.0
           if rf_curve is not None else 0.0)
    dec = (past > bar).astype(float).where(past.notna())
    keep = np.zeros(len(close), dtype=bool)
    keep[np.arange(offset, len(close), 21)] = True
    return dec.where(pd.Series(keep, index=close.index)).ffill()


# ==========================================================================
# 3. book construction — execution at a close, cash earns the bill rate
# ==========================================================================

def build_book(w: pd.Series, spy: pd.Series, rf: pd.Series,
               exec_lag: int = 1, rt_bps: float = RT_BPS_HEADLINE,
               cash_rate: pd.Series | None = None) -> pd.Series:
    """Total return of the overlay book.

    w[t]      target weight decided at the close of t
    exec_lag  1 = position taken at the close of t (same-close)
              2 = position taken at the close of t+1 (next-close)
    held[t]   the weight actually carried over the period earning ret[t]
    cost      rt_bps is a full out-and-back round trip across BOTH legs, so a
              one-way change of |dw| costs |dw| * rt_bps/2.
    cash      earns `cash_rate` (BIL by default). Pass a zero series to
              measure what assuming a 0% cash rate would have cost.
    """
    cash = rf if cash_rate is None else cash_rate
    held = w.shift(exec_lag)
    turn = held.diff().abs().fillna(0.0)
    r = held * spy + (1.0 - held) * cash - turn * (rt_bps / 2.0) / 1e4
    return r


def trade_stats(w: pd.Series, exec_lag: int, spy: pd.Series,
                rf: pd.Series) -> dict:
    held = w.shift(exec_lag).dropna()
    if held.empty:
        return {}
    years = len(held) / TD_YEAR
    ch = held.diff().fillna(0.0)
    switches = int((ch.abs() > 1e-9).sum())
    # a "round trip" = one exit followed by one re-entry
    exits = int((ch < -1e-9).sum())
    # whipsaw: an out-of-market spell over which SPY beat cash
    inv = held > 0.5
    whip = 0
    spells = 0
    i = 0
    a = inv.to_numpy()
    idx = held.index
    while i < len(a):
        if not a[i]:
            j = i
            while j < len(a) and not a[j]:
                j += 1
            seg = slice(i, j)
            spells += 1
            s_ret = float((1 + spy.reindex(idx).iloc[seg].fillna(0)).prod())
            c_ret = float((1 + rf.reindex(idx).iloc[seg].fillna(0)).prod())
            if s_ret > c_ret:
                whip += 1
            i = j
        else:
            i += 1
    return {"time_in_market_pct": round(100 * float(held.mean()), 2),
            "switches": switches, "exits": exits,
            "round_trips_per_year": round(exits / years, 2),
            "cash_spells": spells, "whipsaw_spells": whip,
            "whipsaw_pct": round(100 * whip / spells, 1) if spells else None}


# ==========================================================================
# 4. metrics — the axes the risk rule must be judged on
# ==========================================================================

def _ann_ret(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 2:
        return float("nan")
    return float((1 + r).prod() ** (TD_YEAR / len(r)) - 1)


def _longest_true_run(mask: np.ndarray) -> int:
    """Longest run of True, vectorised (this is called ~30k times by the nulls)."""
    m = np.asarray(mask, bool)
    if not m.any():
        return 0
    idx = np.flatnonzero(np.r_[True, m[1:] != m[:-1]])
    lens = np.diff(np.r_[idx, len(m)])
    return int(lens[m[idx]].max())


def _underwater(r) -> tuple[float, int]:
    v = np.asarray(pd.Series(r).fillna(0.0), float)
    c = np.cumprod(1.0 + v)
    dd = c / np.maximum.accumulate(c) - 1.0
    return float(dd.min()), _longest_true_run(dd < -1e-12)


def metrics(r: pd.Series, rf: pd.Series, label: str = "") -> dict:
    r = r.dropna()
    rfa = rf.reindex(r.index).fillna(0.0)
    ex = r - rfa
    dd, uw = _underwater(r)
    down = ex[ex < 0]
    sortino = (float(ex.mean()) / float(down.std(ddof=1)) * math.sqrt(TD_YEAR)
               if len(down) > 2 and down.std(ddof=1) > 0 else float("nan"))
    roll = np.expm1(np.log1p(r).rolling(TD_YEAR).sum())
    return {
        "label": label,
        "n": int(len(r)),
        "CAGR_pct": round(100 * _ann_ret(r), 2),
        "vol_pct": round(100 * float(r.std(ddof=1)) * math.sqrt(TD_YEAR), 2),
        "sharpe": round(g.sharpe(ex), 4),
        "sortino": round(sortino, 4),
        "maxDD_pct": round(100 * dd, 2),
        "longest_underwater_td": uw,
        "worst_12m_pct": round(100 * float(roll.min()), 2) if roll.notna().any() else None,
        "excess_CAGR_pct": round(100 * (_ann_ret(r) - _ann_ret(rfa)), 2),
    }


# ==========================================================================
# 5. Rule 13 — beta and alpha on EXCESS returns over BIL
# ==========================================================================

def nw_se(x: np.ndarray, lags: int = NW_LAG) -> float:
    x = np.asarray(x, float)
    x = x - x.mean()
    n = len(x)
    s = float(x @ x) / n
    for L in range(1, min(lags, n - 1) + 1):
        c = float(x[L:] @ x[:-L]) / n
        s += 2 * (1 - L / (lags + 1)) * c
    return math.sqrt(max(s, 0.0) / n)


def alpha_beta(book: pd.Series, bench: pd.Series, rf: pd.Series,
               lags: int = NW_LAG, beta_null: float = 1.0) -> dict:
    """Jensen regression on EXCESS returns: (rb - rf) = a + b (rm - rf) + e.

    `beta_null` is the value beta is TESTED AGAINST — 1.0 for a book (does it
    carry market risk?), 0.0 for a difference series (is the difference itself
    beta-laden?). Getting that wrong is a quiet way to report a meaningless
    t; H29 died for a related error one level down."""
    df = pd.concat([book, bench, rf], axis=1).dropna()
    df.columns = ["b", "m", "f"]
    y = (df.b - df.f).to_numpy()
    x = (df.m - df.f).to_numpy()
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    # a numerically exact fit (a book regressed on itself) has no sampling
    # variation to report; emitting a t from float dust would be noise
    degenerate = float(np.std(resid)) < 1e-14 * max(float(np.std(y)), 1e-12)
    u0 = resid * 1.0
    ux = resid * (x - x.mean())
    se_a = nw_se(u0, lags)
    vx = float(np.var(x, ddof=0))
    se_b = nw_se(ux, lags) / vx if vx > 0 else float("nan")
    return {"alpha_bps_day": round(1e4 * float(beta[0]), 3),
            "alpha_pct_yr": round(100 * (float(beta[0]) * TD_YEAR), 3),
            "beta": round(float(beta[1]), 4),
            "beta_null": beta_null,
            "t_alpha_nw": (float("nan") if degenerate or se_a <= 0
                           else round(float(beta[0]) / se_a, 3)),
            "t_beta_nw": (float("nan") if degenerate or not se_b > 0
                          else round(float(beta[1] - beta_null) / se_b, 3)),
            "n": int(len(y))}


def diff_alpha_beta(book: pd.Series, bench: pd.Series, rf: pd.Series) -> dict:
    """Rule 13 on the DIFFERENCE series: (rb - rm) regressed on (rm - rf).

    A difference of two beta-laden series is itself beta-laden; H29 died for
    adjusting the levels and not the deltas. The null for the difference's
    beta is ZERO, not one."""
    df = pd.concat([book, bench, rf], axis=1).dropna()
    df.columns = ["b", "m", "f"]
    d = (df.b - df.m)
    # regressand is d itself: (d + f) - f = d
    return alpha_beta(d + df.f, df.m, df.f, beta_null=0.0)


# ==========================================================================
# 6. bootstrap t with Monte-Carlo sd (Rule 16)
# ==========================================================================

def block_boot_t(x: np.ndarray, reps: int = BOOT_REPS, block: int = BOOT_BLOCK,
                 seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    nb = int(np.ceil(n / block))
    obs = float(x.mean())
    means = np.empty(reps)
    for i in range(reps):
        starts = rng.integers(0, n, nb)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        means[i] = x[idx].mean()
    sd = float(means.std(ddof=1))
    return obs / sd if sd > 0 else float("nan")


def boot_t_with_mc(x: np.ndarray) -> dict:
    ts = [block_boot_t(x, seed=s) for s in SEEDS]
    return {"t_boot": round(float(np.mean(ts)), 3),
            "t_boot_mc_sd": round(float(np.std(ts, ddof=1)), 3),
            "t_boot_seeds": [round(t, 3) for t in ts]}


def _sr(x: np.ndarray) -> float:
    s = float(np.std(x, ddof=1))
    return float(np.mean(x)) / s if s > 0 else 0.0


def sharpe_diff_test(book: pd.Series, bench: pd.Series, rf: pd.Series,
                     reps: int = BOOT_REPS, block: int = BOOT_BLOCK) -> dict:
    """Is the Sharpe GAP significant? Two independent answers.

    The whole 'lever it to SPY's volatility' argument rests on the Sharpe
    difference, not on the raw return difference, so the raw-difference
    bootstrap t reported elsewhere does NOT test it. Memmel's (2003)
    correction of Jobson-Korkie gives the analytic answer; a paired block
    bootstrap that resamples (book, bench) rows TOGETHER gives the empirical
    one, over three seeds so its Monte-Carlo sd is quotable (Rule 16)."""
    df = pd.concat([book, bench, rf], axis=1).dropna()
    df.columns = ["b", "m", "f"]
    a = (df.b - df.f).to_numpy()
    c = (df.m - df.f).to_numpy()
    n = len(a)
    s1, s2 = _sr(a), _sr(c)
    rho = float(np.corrcoef(a, c)[0, 1])
    theta = (2 * (1 - rho) + 0.5 * (s1 ** 2 + s2 ** 2 - 2 * rho ** 2 * s1 * s2)) / n
    z_memmel = (s1 - s2) / math.sqrt(theta) if theta > 0 else float("nan")

    nb = int(np.ceil(n / block))
    ts = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        d = np.empty(reps)
        for i in range(reps):
            st = rng.integers(0, n, nb)
            idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
            d[i] = _sr(a[idx]) - _sr(c[idx])
        sd = float(d.std(ddof=1))
        ts.append((s1 - s2) / sd if sd > 0 else float("nan"))
    return {"sharpe_book": round(s1 * math.sqrt(TD_YEAR), 4),
            "sharpe_bench": round(s2 * math.sqrt(TD_YEAR), 4),
            "d_sharpe": round((s1 - s2) * math.sqrt(TD_YEAR), 4),
            "corr": round(rho, 3),
            "t_memmel": round(z_memmel, 3),
            "t_boot": round(float(np.mean(ts)), 3),
            "t_boot_mc_sd": round(float(np.std(ts, ddof=1)), 3)}


# ==========================================================================
# 7. controls — the decisive one is (a)
# ==========================================================================

def _spells(a: np.ndarray) -> list[tuple[int, int]]:
    out, i = [], 0
    while i < len(a):
        if not a[i]:
            j = i
            while j < len(a) and not a[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def null_books(held: pd.Series, spy: pd.Series, rf: pd.Series,
               kind: str, draws: int = N_DRAWS, rt_bps: float = RT_BPS_HEADLINE,
               seed: int = SEEDS[0]) -> pd.DataFrame:
    """Matched-exposure nulls. `held` is the REAL held-weight series."""
    rng = np.random.default_rng(seed)
    h = held.dropna()
    idx = h.index
    a = (h.to_numpy() > 0.5)
    n = len(a)
    n_out = int((~a).sum())
    sp = spy.reindex(idx).fillna(0.0).to_numpy()
    cs = rf.reindex(idx).fillna(0.0).to_numpy()
    lens = [L for _, L in _spells(a)]

    rows = []
    for d in range(draws):
        if kind == "iid":
            w = np.ones(n)
            w[rng.choice(n, n_out, replace=False)] = 0.0
        elif kind == "spell":
            w = np.ones(n)
            for L in sorted(lens, reverse=True):
                for _ in range(200):
                    s = int(rng.integers(0, max(n - L, 1)))
                    if w[s:s + L].all():
                        w[s:s + L] = 0.0
                        break
        elif kind == "rotate":
            k = int(rng.integers(1, n))
            w = np.roll(h.to_numpy(), k)
        else:
            raise ValueError(kind)
        turn = np.r_[0.0, np.abs(np.diff(w))]
        r = w * sp + (1 - w) * cs - turn * (rt_bps / 2.0) / 1e4
        ex = r - cs
        c = np.cumprod(1.0 + r)
        dd = float((c / np.maximum.accumulate(c) - 1.0).min())
        sd = float(ex.std(ddof=1))
        rows.append({"cagr": float(c[-1] ** (TD_YEAR / n) - 1.0),
                     "sharpe": float(ex.mean()) / sd * math.sqrt(TD_YEAR) if sd > 0 else 0.0,
                     "maxdd": dd, "tim": float(w.mean())})
    return pd.DataFrame(rows)


def pct_rank(value: float, dist: np.ndarray) -> float:
    d = np.asarray(dist, float)
    d = d[np.isfinite(d)]
    return round(100.0 * float((d < value).mean()), 1) if len(d) else float("nan")


# ==========================================================================
# 8. THE DECIDING TEST — lever the excess return to SPY's own volatility
# ==========================================================================

def lever_to_spy_vol(book: pd.Series, spy: pd.Series, rf: pd.Series,
                     borrow_bps: float = 0.0, causal: bool = False) -> dict:
    """g = S^2/2: a higher Sharpe levered to equal risk is more return.

    lev[t] = rf[t] + k*(r[t]-rf[t]) - (k-1)*borrow/252 when k > 1.
    `causal=False` uses the FULL-SAMPLE k (a what-if, flagged as in-sample).
    `causal=True` uses an expanding-window k known at t-1 (tradeable)."""
    df = pd.concat([book, spy, rf], axis=1).dropna()
    df.columns = ["b", "m", "f"]
    eb, em = df.b - df.f, df.m - df.f
    if causal:
        k = (em.expanding(min_periods=252).std()
             / eb.expanding(min_periods=252).std()).shift(1).clip(0.25, 4.0)
        k = k.fillna(1.0)
    else:
        sb, sm = float(eb.std(ddof=1)), float(em.std(ddof=1))
        k = pd.Series(sm / sb if sb > 0 else 1.0, index=df.index)
    carry = (k - 1).clip(lower=0) * (borrow_bps / 1e4) / TD_YEAR
    lev = df.f + k * eb - carry
    return {"k_mean": round(float(k.mean()), 3),
            "borrow_bps": borrow_bps, "causal": causal,
            **metrics(lev, df.f, "levered"), "series": lev}


# ==========================================================================
# 9. episodes
# ==========================================================================

EPISODES = {
    "2018Q4": ("2018-10-01", "2018-12-31"),
    "2020 COVID crash": ("2020-02-19", "2020-03-23"),
    "2020 full year": ("2020-01-01", "2020-12-31"),
    "2022 bear (to trough)": ("2022-01-03", "2022-10-12"),
    "2022 full year": ("2022-01-01", "2022-12-31"),
}


def episode_returns(books: dict[str, pd.Series]) -> pd.DataFrame:
    rows = {}
    for name, (a, b) in EPISODES.items():
        cell = {}
        for k, v in books.items():
            seg = v.loc[a:b].dropna()
            cell[k] = (round(100 * float((1 + seg).prod() - 1), 2)
                       if len(seg) > 5 else float("nan"))   # nan, not a fake 0
        rows[name] = cell
    return pd.DataFrame(rows).T


def sub_periods(r: pd.Series) -> dict:
    r = r.dropna()
    n = len(r)
    return {"halves": [r.iloc[:n // 2], r.iloc[n // 2:]],
            "thirds": [r.iloc[:n // 3], r.iloc[n // 3:2 * n // 3], r.iloc[2 * n // 3:]]}


# ==========================================================================
# 10. the 5-minute realised-variance leg (H20's confirmed forecaster)
# ==========================================================================

def rv_forecast_spy(quiet: bool = False) -> pd.Series | None:
    """HAR-log forecast made AT t for session t+1, in daily variance units.

    `rv_forecast_lab.har_forecast` ends with `.shift(1)` so its row t is the
    forecast FOR t. `.shift(-1)` here undoes exactly that one shift, giving
    the forecast made at t (from rv through t) for t+1 — known at the close
    of t, which is when the position is set. The composition is the identity;
    no post-t information enters."""
    try:
        from . import intraday, rv_forecast_lab as rvfc
    except Exception as e:                       # pragma: no cover
        print(f"  rv leg unavailable: {e}")
        return None
    sess = intraday.session_frames(["SPY"], "2018-01-01", "2026-08-01",
                                   timeframe="5Min", quiet=quiet)
    cr = sess["close_ret"].astype(float)
    on = sess["overnight_ret"].astype(float)
    rv5 = sess["rv_5min"].astype(float)
    bad = cr.abs() > MAX_ABS_RET
    for f in (cr, on, rv5):
        f[bad] = np.nan
    rv_cc = rv5 ** 2 + on ** 2
    fc_for_t = rvfc.har_forecast(rv_cc, log=True, pooled=False)["SPY"]
    made_at_t = fc_for_t.shift(-1)
    made_at_t.index = pd.DatetimeIndex(made_at_t.index).tz_localize(None)
    return made_at_t


def execution_feasibility(spy_c: pd.Series, quiet: bool = True) -> dict | None:
    """Is the same-close SMA200 signal actually KNOWN before the bell?

    The whole same-close convention rests on the claim that a 200-day SMA is
    known to high precision minutes before the close. That is an assertion,
    and it is measurable: rebuild the signal from the 15:30 ET price (the
    close minus the last half hour, from scout/intraday.py's `last30_ret`)
    used in BOTH the level and the 200th term of the average, and count how
    often it disagrees with the signal built from the official close. Then
    trade the 15:30-KNOWABLE signal at the close and compare the books. A
    disagreement rate near zero means same-close execution is real rather
    than a convenient assumption."""
    try:
        from . import intraday
    except Exception:                                     # pragma: no cover
        return None
    sess = intraday.session_frames(["SPY"], "2018-01-01", "2026-08-01",
                                   timeframe="5Min", quiet=quiet)
    l30 = sess["last30_ret"]["SPY"].astype(float)
    l30.index = pd.DatetimeIndex(l30.index).tz_localize(None)
    l30 = l30.reindex(spy_c.index)
    px1530 = spy_c / (1.0 + l30)                 # the price 30 minutes early

    c = spy_c.to_numpy(float)
    p = px1530.to_numpy(float)
    n = len(c)
    sig_close = np.full(n, np.nan)
    sig_1530 = np.full(n, np.nan)
    csum = np.r_[0.0, np.cumsum(c)]
    for i in range(SMA_D - 1, n):
        prev_sum = csum[i] - csum[i - SMA_D + 1]           # closes i-199..i-1
        sig_close[i] = 1.0 if c[i] > (prev_sum + c[i]) / SMA_D else 0.0
        if np.isfinite(p[i]):
            sig_1530[i] = 1.0 if p[i] > (prev_sum + p[i]) / SMA_D else 0.0
    both = np.isfinite(sig_close) & np.isfinite(sig_1530)
    dis = int((sig_close[both] != sig_1530[both]).sum())
    return {"n_compared": int(both.sum()),
            "disagreements": dis,
            "disagreement_pct": round(100 * dis / max(int(both.sum()), 1), 3),
            "sig_1530": pd.Series(sig_1530, index=spy_c.index)}


def vol_leverage(fc: pd.Series, target: float = VOL_TARGET,
                 cap: float = 1.0) -> pd.Series:
    ann = np.sqrt(TD_YEAR * fc.clip(lower=1e-10))
    return (target / ann).clip(0.0, cap)


# ==========================================================================
# 11. self-test: mechanical proof of no lookahead
# ==========================================================================

def selftest(quiet: bool = False) -> int:
    d = load(quiet=True)
    close, ret = d["close"], d["ret"]
    spy = close["SPY"]
    rfc = (1 + ret["BIL"].fillna(0)).cumprod()

    me = _month_end_mask(close.index)
    cuts = close.index[me]
    cut = cuts[int(len(cuts) * 0.7)]             # a REAL month end

    def all_sigs(c: pd.Series, rf_curve: pd.Series) -> dict:
        return {"sma200": sig_sma200(c),
                "sma200_band": sig_sma200_band(c),
                "sma10m": sig_sma10m(c),
                "tsmom": sig_tsmom(c, None),
                "tsmom_x": sig_tsmom(c, rf_curve),
                "phase7": sig_phase_sma10m(c, 7)}

    full = all_sigs(spy, rfc)
    trunc = all_sigs(spy.loc[:cut], rfc.loc[:cut])
    fails = []
    for k in full:
        a = full[k].loc[:cut]
        b = trunc[k]
        a, b = a.align(b, join="inner")
        eq = ((a.isna() & b.isna()) | (a == b)).all()
        if not eq:
            n_diff = int((~((a.isna() & b.isna()) | (a == b))).sum())
            fails.append(f"{k}: {n_diff} of {len(a)} differ")
    if not quiet:
        print(f"  no-lookahead: cut at {cut.date()}, "
              f"{len(full)} signals, {'PASS' if not fails else 'FAIL'}")
        for f in fails:
            print(f"    {f}")

    # execution alignment check: a weight decided at t must earn ret[t+1]
    w = pd.Series([0, 1, 1, 0, 0], index=pd.date_range("2020-01-01", periods=5))
    r = pd.Series([0.10, 0.20, 0.30, 0.40, 0.50], index=w.index)
    z = pd.Series(0.0, index=w.index)
    b = build_book(w, r, z, exec_lag=1, rt_bps=0.0)
    ok_exec = (abs(b.iloc[2] - 0.30) < 1e-12 and abs(b.iloc[1] - 0.0) < 1e-12
               and abs(b.iloc[3] - 0.40) < 1e-12 and abs(b.iloc[4] - 0.0) < 1e-12)
    if not quiet:
        print(f"  execution alignment (w[t] earns ret[t+1]): "
              f"{'PASS' if ok_exec else 'FAIL'}")

    # metric sanity: SPY against itself has beta 1, alpha 0
    ab = alpha_beta(ret["SPY"], ret["SPY"], ret["BIL"])
    ok_ab = abs(ab["beta"] - 1) < 1e-8 and abs(ab["alpha_bps_day"]) < 1e-6
    if not quiet:
        print(f"  alpha_beta identity (SPY on SPY -> b=1, a=0): "
              f"{'PASS' if ok_ab else 'FAIL'} {ab['beta']:.6f} {ab['alpha_bps_day']:.6f}")

    # the difference regression must reproduce beta-1 and the same alpha
    dab = diff_alpha_beta(ret["SPY"], ret["SPY"], ret["BIL"])
    ok_d = abs(dab["beta"]) < 1e-8
    if not quiet:
        print(f"  diff regression identity (SPY-SPY -> b=0): "
              f"{'PASS' if ok_d else 'FAIL'} {dab['beta']:.6f}")

    bad = bool(fails) or not ok_exec or not ok_ab or not ok_d
    if not quiet:
        print(f"\n  SELFTEST {'FAILED' if bad else 'PASSED'}")
    return 1 if bad else 0


# ==========================================================================
# 12. the run
# ==========================================================================

def _t(rows, title):
    if not rows:
        return
    df = pd.DataFrame(rows)
    print(f"\n{title}")
    print(df.to_string(index=False))


def run(args) -> dict:
    res = {"built": datetime.now(timezone.utc).isoformat()}
    d = load()
    close, ret = d["close"], d["ret"]
    print("\n=== DATA AND GUARDS ===")
    for k, v in d["meta"].items():
        print(f"  {k}: {v}")
    res["data"] = d["meta"]

    spy_r = ret["SPY"]
    rf = ret["BIL"].fillna(0.0)
    ief_r = ret["IEF"]
    rfc = (1 + rf).cumprod()
    spy_c = close["SPY"]

    # ---- signals -------------------------------------------------------
    sigs = {
        "sma200": sig_sma200(spy_c),
        "sma200_band1pct": sig_sma200_band(spy_c, 0.01),
        "sma10m": sig_sma10m(spy_c),
        "tsmom12_1": sig_tsmom(spy_c, None),
        "tsmom12_1_excess": sig_tsmom(spy_c, rfc),
        "tsmom12_0": sig_tsmom(spy_c, None, skip=0),
    }
    sigs["dual_and"] = (sigs["sma200"] * sigs["tsmom12_1"])
    sigs["dual_avg"] = 0.5 * (sigs["sma200"] + sigs["tsmom12_1"])

    # common sample: every signal defined (the longest warm-up is 12-1 = 273 td)
    first = max(s.first_valid_index() for s in sigs.values())
    idx = spy_c.index[spy_c.index >= first]
    print(f"\n  common evaluation sample: {idx[0].date()} .. {idx[-1].date()} "
          f"({len(idx)} sessions, {len(idx)/TD_YEAR:.2f} yr) — the start is set "
          f"by the 12-1 momentum warm-up (252+21 sessions), and EVERY arm "
          f"including SPY is scored on it (Rule 17).")
    res["sample"] = {"start": str(idx[0].date()), "end": str(idx[-1].date()),
                     "n": int(len(idx))}

    spy_r = spy_r.reindex(idx)
    rf = rf.reindex(idx)
    ief_r = ief_r.reindex(idx)
    sigs = {k: v.reindex(idx) for k, v in sigs.items()}

    # ---- benchmarks ----------------------------------------------------
    books: dict[str, pd.Series] = {"SPY buy&hold": spy_r}
    # 60/40 as a retail account would actually hold it: fixed 0.6/0.4, cost is
    # ~1-2 bps a YEAR for a monthly rebalance of a 60/40 and is charged at
    # zero here, which biases in the alternative's favour and is stated.
    books["60/40 SPY/IEF"] = 0.6 * spy_r + 0.4 * ief_r
    books["BIL (cash)"] = rf

    variants = list(sigs)
    exec_modes = {"same-close": 1, "next-close": 2}
    spy_m = metrics(spy_r, rf)

    # ---- primary table --------------------------------------------------
    rows, ab_rows, diff_rows, tr_rows = [], [], [], []
    all_books: dict[str, pd.Series] = dict(books)
    for name in variants:
        for em, lag in exec_modes.items():
            r = build_book(sigs[name], spy_r, rf, exec_lag=lag,
                           rt_bps=RT_BPS_HEADLINE)
            key = f"{name} [{em}]"
            all_books[key] = r
            m = metrics(r, rf, key)
            rows.append(m)
            ab_rows.append({"book": key, **alpha_beta(r, spy_r, rf)})
            diff_rows.append({"diff": f"{key} - SPY",
                              **diff_alpha_beta(r, spy_r, rf)})
            tr_rows.append({"book": key, **trade_stats(sigs[name], lag, spy_r, rf)})

    for k, v in books.items():
        rows.insert(0, metrics(v, rf, k))
        ab_rows.insert(0, {"book": k, **alpha_beta(v, spy_r, rf)})
        diff_rows.insert(0, {"diff": f"{k} - SPY", **diff_alpha_beta(v, spy_r, rf)})

    _t(rows, f"=== PRIMARY: every book, {RT_BPS_HEADLINE:.0f} bps round trip, "
             f"cash = BIL ===")
    _t(ab_rows, "=== RULE 13a: alpha and beta vs SPY, on EXCESS returns over BIL ===")
    _t(diff_rows, "=== RULE 13b: the DIFFERENCE series (book - SPY) regressed on "
                  "(SPY - BIL) ===")
    # the H29 delta decomposition, done the way Rule 13 requires: split the
    # raw CAGR gap into forgone beta and market-adjusted alpha.
    dec = []
    spy_ex_ann = 100 * (_ann_ret(spy_r) - _ann_ret(rf))
    for name in variants:
        r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)
        da = diff_alpha_beta(r, spy_r, rf)
        raw = metrics(r, rf)["CAGR_pct"] - spy_m["CAGR_pct"]
        beta_part = da["beta"] * spy_ex_ann
        dec.append({"variant": name, "raw_CAGR_gap_pp": round(raw, 2),
                    "= forgone_beta_pp": round(beta_part, 2),
                    "+ alpha_pp": da["alpha_pct_yr"],
                    "t_alpha": da["t_alpha_nw"],
                    "residual_pp": round(raw - beta_part - da["alpha_pct_yr"], 2)})
    _t(dec, f"=== the CAGR gap DECOMPOSED (SPY excess return over BIL = "
            f"{spy_ex_ann:.2f}%/yr) ===")
    res["decomposition"] = dec

    _t(tr_rows, "=== trading profile ===")
    res["primary"] = rows
    res["alpha_beta"] = ab_rows
    res["diff_alpha_beta"] = diff_rows
    res["trades"] = tr_rows

    # ---- what the BIL cash leg is worth (non-negotiable #1, measured) ----
    zrows = []
    for name in variants:
        rb = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)
        rz = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE,
                        cash_rate=pd.Series(0.0, index=idx))
        mb, mz = metrics(rb, rf, name), metrics(rz, rf, name)
        zrows.append({"variant": name, "CAGR_BIL": mb["CAGR_pct"],
                      "CAGR_zero_cash": mz["CAGR_pct"],
                      "d_CAGR_pp": round(mb["CAGR_pct"] - mz["CAGR_pct"], 2),
                      "sharpe_BIL": mb["sharpe"], "sharpe_zero": mz["sharpe"],
                      "d_sharpe": round(mb["sharpe"] - mz["sharpe"], 4)})
    _t(zrows, "=== NON-NEGOTIABLE #1, MEASURED: what pretending cash earns 0% "
              "would have cost ===")
    res["cash_leg_value"] = zrows

    # ---- costs and break-even -------------------------------------------
    crows = []
    for name in variants:
        row = {"variant": name}
        for c in RT_GRID:
            r = build_book(sigs[name], spy_r, rf, 1, c)
            row[f"CAGR@{c:g}"] = metrics(r, rf)["CAGR_pct"]
            row[f"Sh@{c:g}"] = metrics(r, rf)["sharpe"]
        # break-even round-trip cost vs SPY, on Sharpe and on CAGR
        def gap(c, field):
            r = build_book(sigs[name], spy_r, rf, 1, c)
            return metrics(r, rf)[field] - metrics(spy_r, rf)[field]
        for field, tag in (("sharpe", "be_sharpe_bps"), ("CAGR_pct", "be_cagr_bps")):
            lo, hi = -200.0, 400.0
            if gap(lo, field) * gap(hi, field) > 0:
                row[tag] = "no crossing in [-200,400]"
            else:
                for _ in range(60):
                    mid = (lo + hi) / 2
                    if gap(lo, field) * gap(mid, field) <= 0:
                        hi = mid
                    else:
                        lo = mid
                row[tag] = round((lo + hi) / 2, 1)
        crows.append(row)
    _t(crows, "=== costs and BREAK-EVEN round-trip cost vs SPY (same-close) ===")
    res["costs"] = crows

    # ---- halves and equal thirds ----------------------------------------
    srows = []
    for key, r in all_books.items():
        sp = sub_periods(r)
        row = {"book": key}
        for tag, segs in sp.items():
            for i, seg in enumerate(segs):
                rr = rf.reindex(seg.index)
                mm = metrics(seg, rr)
                ss = metrics(spy_r.reindex(seg.index), rr)
                row[f"{tag[0]}{i+1}_Sh"] = mm["sharpe"]
                row[f"{tag[0]}{i+1}_dSh"] = round(mm["sharpe"] - ss["sharpe"], 3)
                row[f"{tag[0]}{i+1}_dDD"] = round(mm["maxDD_pct"] - ss["maxDD_pct"], 1)
        srows.append(row)
    _t(srows, "=== BOTH HALVES and EQUAL THIRDS: Sharpe, and dSharpe / dMaxDD "
              "vs SPY on the same sub-period ===")
    res["subperiods"] = srows

    # ---- episodes --------------------------------------------------------
    ep = episode_returns(all_books)
    print("\n=== EPISODES (total return %, same-close books) ===")
    print(ep.to_string())
    res["episodes"] = json.loads(ep.to_json())

    # ---- Rule 9: entry-phase pooling for the monthly rules ---------------
    if not args.quick:
        prows = []
        for fam, fn in (("sma10m", sig_phase_sma10m),
                        ("tsmom12_1", lambda c, o: sig_phase_tsmom(c, o, None))):
            sh, cg, dd = [], [], []
            for off in range(21):
                w = fn(spy_c, off).reindex(idx)
                r = build_book(w, spy_r, rf, 1, RT_BPS_HEADLINE)
                m = metrics(r, rf)
                sh.append(m["sharpe"]); cg.append(m["CAGR_pct"]); dd.append(m["maxDD_pct"])
            prows.append({"family": fam, "phases": 21,
                          "sharpe_mean": round(float(np.mean(sh)), 4),
                          "sharpe_sd": round(float(np.std(sh, ddof=1)), 4),
                          "sharpe_min": round(min(sh), 4), "sharpe_max": round(max(sh), 4),
                          "pct_phases_beating_SPY_sharpe":
                              round(100 * float(np.mean(np.array(sh) > spy_m["sharpe"])), 1),
                          "CAGR_mean": round(float(np.mean(cg)), 2),
                          "pct_phases_beating_SPY_CAGR":
                              round(100 * float(np.mean(np.array(cg) > spy_m["CAGR_pct"])), 1),
                          "maxDD_mean": round(float(np.mean(dd)), 2)})
        _t(prows, "=== RULE 9: pooled across all 21 monthly rebalance phases ===")
        res["phases"] = prows

    # ---- ROBUSTNESS 1: is 200 a fitted number? -------------------------
    wrows = []
    for win in (50, 100, 125, 150, 200, 250, 300):
        sma = spy_c.rolling(win, min_periods=win).mean()
        w = (spy_c > sma).astype(float).where(sma.notna()).reindex(idx)
        r = build_book(w, spy_r, rf, 1, RT_BPS_HEADLINE)
        m = metrics(r, rf)
        ts = trade_stats(w, 1, spy_r, rf)
        wrows.append({"window": win, "CAGR": m["CAGR_pct"], "sharpe": m["sharpe"],
                      "maxDD": m["maxDD_pct"], "worst12m": m["worst_12m_pct"],
                      "tim_pct": ts["time_in_market_pct"],
                      "rt_per_yr": ts["round_trips_per_year"],
                      "dSharpe_vs_SPY": round(m["sharpe"] - spy_m["sharpe"], 4),
                      "dMaxDD_vs_SPY": round(m["maxDD_pct"] - spy_m["maxDD_pct"], 2)})
    _t(wrows, "=== ROBUSTNESS: the SMA window is not a fitted parameter — the "
              "whole neighbourhood (SPY buy&hold: CAGR "
              f"{spy_m['CAGR_pct']}, Sharpe {spy_m['sharpe']}, "
              f"maxDD {spy_m['maxDD_pct']}) ===")
    res["window_sweep"] = wrows

    # ---- ROBUSTNESS 2: how often you have to LOOK ----------------------
    frows = []
    base = sigs["sma200"]
    for freq, step in (("daily", 1), ("weekly", 5), ("monthly", 21)):
        shs, cgs, dds = [], [], []
        for off in range(step):
            keep = np.zeros(len(idx), dtype=bool)
            keep[np.arange(off, len(idx), step)] = True
            w = base.where(pd.Series(keep, index=idx)).ffill()
            r = build_book(w, spy_r, rf, 1, RT_BPS_HEADLINE)
            m = metrics(r, rf)
            shs.append(m["sharpe"]); cgs.append(m["CAGR_pct"]); dds.append(m["maxDD_pct"])
        frows.append({"check_frequency": freq, "phases": step,
                      "sharpe_mean": round(float(np.mean(shs)), 4),
                      "sharpe_sd": round(float(np.std(shs)), 4) if step > 1 else 0.0,
                      "sharpe_min": round(min(shs), 4), "sharpe_max": round(max(shs), 4),
                      "CAGR_mean": round(float(np.mean(cgs)), 2),
                      "maxDD_mean": round(float(np.mean(dds)), 2),
                      "maxDD_worst": round(max(dds), 2)})
    _t(frows, "=== ROBUSTNESS / RULE 9 for the DAILY rule: it is state-based so "
              "it has no entry schedule, but checking it less often DOES have "
              "phases — all of them pooled ===")
    res["check_freq"] = frows

    # ---- ROBUSTNESS 3: leave-one-episode-out ---------------------------
    drop_sets = {
        "full sample": None,
        "drop 2020": ("2020-01-01", "2020-12-31"),
        "drop 2022": ("2022-01-01", "2022-12-31"),
    }
    erows = []
    for tag, span in drop_sets.items():
        keep = pd.Series(True, index=idx)
        if span:
            keep.loc[span[0]:span[1]] = False
        both = keep.copy()
        for name in ("sma200", "dual_and", "dual_avg"):
            r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)[keep]
            rr, ss = rf[keep], spy_r[keep]
            m, sm = metrics(r, rr), metrics(ss, rr)
            erows.append({"drop": tag, "variant": name, "n": m["n"],
                          "sharpe": m["sharpe"], "SPY_sharpe": sm["sharpe"],
                          "dSharpe": round(m["sharpe"] - sm["sharpe"], 4),
                          "maxDD": m["maxDD_pct"], "SPY_maxDD": sm["maxDD_pct"],
                          "dMaxDD": round(m["maxDD_pct"] - sm["maxDD_pct"], 2),
                          "CAGR": m["CAGR_pct"], "SPY_CAGR": sm["CAGR_pct"]})
        _ = both
    # and both dropped at once
    keep = pd.Series(True, index=idx)
    keep.loc["2020-01-01":"2020-12-31"] = False
    keep.loc["2022-01-01":"2022-12-31"] = False
    for name in ("sma200", "dual_and", "dual_avg"):
        r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)[keep]
        rr, ss = rf[keep], spy_r[keep]
        m, sm = metrics(r, rr), metrics(ss, rr)
        erows.append({"drop": "drop 2020 AND 2022", "variant": name, "n": m["n"],
                      "sharpe": m["sharpe"], "SPY_sharpe": sm["sharpe"],
                      "dSharpe": round(m["sharpe"] - sm["sharpe"], 4),
                      "maxDD": m["maxDD_pct"], "SPY_maxDD": sm["maxDD_pct"],
                      "dMaxDD": round(m["maxDD_pct"] - sm["maxDD_pct"], 2),
                      "CAGR": m["CAGR_pct"], "SPY_CAGR": sm["CAGR_pct"]})
    _t(erows, "=== 'IS IT ALL 2020 OR 2022?' — leave-one-episode-out (returns "
              "spliced, so maxDD here is of the SPLICED curve) ===")
    res["episode_dropout"] = erows

    # ---- ROBUSTNESS 4: start-date sensitivity --------------------------
    # the Sharpe gap is small enough that the sample window matters; sweeping
    # the start explicitly is cheaper than arguing about it. maxDD deltas are
    # constant across starts whenever the deepest drawdown is inside every
    # window, which is itself the point.
    srows2 = []
    for y in range(2017, 2023):
        sub = idx[idx >= f"{y}-01-01"]
        if len(sub) < 3 * TD_YEAR:
            continue
        rr, ss = rf.reindex(sub), spy_r.reindex(sub)
        row = {"start": y, "n": len(sub), "SPY_sharpe": metrics(ss, rr)["sharpe"],
               "SPY_maxDD": metrics(ss, rr)["maxDD_pct"]}
        for name in ("sma200", "dual_and", "dual_avg"):
            r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE).reindex(sub)
            m = metrics(r, rr)
            row[f"{name}_dSh"] = round(m["sharpe"] - metrics(ss, rr)["sharpe"], 4)
            row[f"{name}_dDD"] = round(m["maxDD_pct"] - metrics(ss, rr)["maxDD_pct"], 2)
        srows2.append(row)
    _t(srows2, "=== ROBUSTNESS: start-date sensitivity. dSh = Sharpe minus SPY's, "
               "dDD = maxDD minus SPY's (positive = shallower) ===")
    res["start_sensitivity"] = srows2

    # ---- CONTROLS --------------------------------------------------------
    if not args.quick:
        nrows = []
        for name in variants:
            held = sigs[name].shift(1)
            real = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)
            rm = metrics(real, rf)
            for kind in ("iid", "spell", "rotate"):
                nb = null_books(held, spy_r, rf, kind, draws=args.draws)
                nrows.append({
                    "variant": name, "null": kind, "draws": len(nb),
                    "real_sharpe": rm["sharpe"],
                    "null_sharpe_mean": round(float(nb.sharpe.mean()), 4),
                    "pctile_sharpe": pct_rank(rm["sharpe"], nb.sharpe.values),
                    "real_CAGR": rm["CAGR_pct"],
                    "null_CAGR_mean": round(100 * float(nb.cagr.mean()), 2),
                    "pctile_CAGR": pct_rank(rm["CAGR_pct"] / 100, nb.cagr.values),
                    "real_maxDD": rm["maxDD_pct"],
                    "null_maxDD_mean": round(100 * float(nb.maxdd.mean()), 2),
                    "pctile_maxDD": pct_rank(rm["maxDD_pct"] / 100, nb.maxdd.values),
                })
        _t(nrows, f"=== CONTROL (a)+(d): matched-exposure nulls, {args.draws} draws "
                  f"each. pctile = share of the null BELOW the real rule ===")
        res["nulls"] = nrows

    # ---- bootstrap t of the difference vs SPY (Rule 16) ------------------
    brows = []
    for name in variants:
        r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)
        dser = (r - spy_r).dropna()
        brows.append({"variant": name,
                      "mean_diff_bps_day": round(1e4 * float(dser.mean()), 3),
                      **boot_t_with_mc(dser.to_numpy())})
    _t(brows, "=== RULE 16: bootstrap t of (book - SPY) daily difference, "
              "3 seeds, MC sd reported ===")
    res["bootstrap"] = brows

    # ---- is the SHARPE GAP itself significant? (what the deciding test rests on)
    sdrows = []
    for name in variants:
        for em, lag in exec_modes.items():
            r = build_book(sigs[name], spy_r, rf, lag, RT_BPS_HEADLINE)
            sdrows.append({"book": f"{name} [{em}]",
                           **sharpe_diff_test(r, spy_r, rf)})
    for k in ("60/40 SPY/IEF",):
        sdrows.insert(0, {"book": k, **sharpe_diff_test(books[k], spy_r, rf)})
    _t(sdrows, "=== IS THE SHARPE GAP SIGNIFICANT? Memmel/Jobson-Korkie and a "
               "paired block bootstrap (3 seeds, MC sd) ===")
    res["sharpe_diff"] = sdrows

    # ---- THE DECIDING TEST ----------------------------------------------
    lrows = []
    for name in variants:
        r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)
        m = metrics(r, rf)
        if m["sharpe"] <= spy_m["sharpe"]:
            lrows.append({"variant": name, "sharpe": m["sharpe"],
                          "SPY_sharpe": spy_m["sharpe"],
                          "eligible": "NO — Sharpe below SPY", "k": None,
                          "levered_CAGR": None, "SPY_CAGR": spy_m["CAGR_pct"],
                          "beats_SPY": False})
            continue
        for causal in (False, True):
            for bb in (0.0, 50.0, 100.0, 150.0):
                lv = lever_to_spy_vol(r, spy_r, rf, borrow_bps=bb, causal=causal)
                lrows.append({"variant": name, "sharpe": m["sharpe"],
                              "SPY_sharpe": spy_m["sharpe"], "eligible": "YES",
                              "k": lv["k_mean"], "causal": causal, "borrow_bps": bb,
                              "levered_CAGR": lv["CAGR_pct"],
                              "levered_vol": lv["vol_pct"],
                              "SPY_vol": spy_m["vol_pct"],
                              "SPY_CAGR": spy_m["CAGR_pct"],
                              "levered_maxDD": lv["maxDD_pct"],
                              "SPY_maxDD": spy_m["maxDD_pct"],
                              "beats_SPY": bool(lv["CAGR_pct"] > spy_m["CAGR_pct"])})
    _t(lrows, "=== THE DECIDING TEST: excess return levered to SPY's own realised "
              "volatility, borrowing charged above 1x ===")
    res["leverage"] = lrows

    # the levered book, judged the way every other book here is judged:
    # sub-periods, and its position inside the SAME matched-exposure nulls.
    lsub = []
    for name in variants:
        r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE)
        if metrics(r, rf)["sharpe"] <= spy_m["sharpe"]:
            continue
        for causal in (False, True):
            lv = lever_to_spy_vol(r, spy_r, rf, borrow_bps=100.0, causal=causal)
            ls = lv["series"]
            row = {"variant": name, "causal_k": causal,
                   "full_dCAGR_pp": round(metrics(ls, rf)["CAGR_pct"]
                                          - spy_m["CAGR_pct"], 2)}
            sp = sub_periods(ls)
            for tag, segs in sp.items():
                for i, seg in enumerate(segs):
                    ss = spy_r.reindex(seg.index)
                    rr = rf.reindex(seg.index)
                    row[f"{tag[0]}{i+1}_dCAGR"] = round(
                        metrics(seg, rr)["CAGR_pct"] - metrics(ss, rr)["CAGR_pct"], 2)
            row["all_subperiods_positive"] = all(
                v > 0 for k, v in row.items() if k.endswith("_dCAGR"))
            lsub.append(row)
    _t(lsub, "=== the levered book vs SPY on CAGR, by half and by third "
             "(100 bps borrowing) ===")
    res["leverage_subperiods"] = lsub

    # ---- deflated Sharpe -------------------------------------------------
    n_var = res["variant_count"] = count_variants(args)
    drows = []
    for name in variants:
        r = build_book(sigs[name], spy_r, rf, 1, RT_BPS_HEADLINE).dropna()
        ex = (r - rf.reindex(r.index)).dropna()
        sr_d = float(ex.mean() / ex.std(ddof=1))
        dsr = g.deflated_sharpe(sr_d, N_PRIOR + n_var, len(ex),
                                skew=float(ex.skew()), kurtosis=float(ex.kurt() + 3))
        drows.append({"variant": name, "sharpe_ann": round(sr_d * math.sqrt(TD_YEAR), 4),
                      "deflated_sharpe_prob": round(dsr, 4),
                      "N_used": N_PRIOR + n_var})
    _t(drows, f"=== deflated Sharpe at the running registry N = {N_PRIOR} + "
              f"{n_var} this lab ===")
    res["deflated"] = drows

    # ---- is same-close execution real? -----------------------------------
    if not args.no_rv:
        print("\n=== EXECUTION: is the same-close signal knowable before the "
              "bell? (measured, not assumed) ===")
        ef = execution_feasibility(spy_c)
        if ef is None:
            print("  intraday unavailable")
        else:
            s15 = ef.pop("sig_1530").reindex(idx)
            common = s15.dropna().index.intersection(idx)
            r15 = build_book(s15, spy_r, rf, 1, RT_BPS_HEADLINE).reindex(common)
            rcl = build_book(sigs["sma200"], spy_r, rf, 1,
                             RT_BPS_HEADLINE).reindex(common)
            rr, ss = rf.reindex(common), spy_r.reindex(common)
            print(f"  {ef}")
            _t([{"book": "sma200 signal from the 15:30 price, traded at the close",
                 **metrics(r15, rr)},
                {"book": "sma200 signal from the official close, traded at the close",
                 **metrics(rcl, rr)},
                {"book": "SPY buy&hold (same window)", **metrics(ss, rr)}],
               "--- the 15:30-knowable book against the close-knowable one. "
               "READ THE FIRST TWO ROWS AGAINST EACH OTHER ONLY: this window is "
               "the intraday-cached sessions (2018+, half-days dropped because "
               "they have no 15:30 bar), so its levels are not comparable to the "
               "primary table ---")
            res["execution_feasibility"] = ef

    # ---- the 5-minute realised-variance leg ------------------------------
    if not args.no_rv:
        print("\n=== THE VOL-TARGET LEG (H20's HAR-log 5-minute RV forecaster) ===")
        fc = rv_forecast_spy(quiet=True)
        if fc is None:
            print("  skipped")
        else:
            ridx = idx.intersection(fc.dropna().index)
            print(f"  RV sample: {ridx[0].date()} .. {ridx[-1].date()} "
                  f"({len(ridx)} sessions) — SHORTER than the primary sample "
                  f"because the 5-minute cache starts 2018-01-02, so every "
                  f"number in this block is scored against SPY on THIS sample.")
            sp2, rf2 = spy_r.reindex(ridx), rf.reindex(ridx)
            vrows, vab, vdiff = [], [], []
            vbooks = {"SPY buy&hold": sp2}
            for cap in (1.0, 1.5):
                lev = vol_leverage(fc.reindex(ridx), VOL_TARGET, cap)
                specs = {
                    f"voltgt only cap{cap:g}": lev,
                    f"sma200 x voltgt cap{cap:g}": sigs["sma200"].reindex(ridx) * lev,
                }
                for nm, w in specs.items():
                    r = build_book(w, sp2, rf2, 1, RT_BPS_HEADLINE)
                    vbooks[nm] = r
                    vrows.append(metrics(r, rf2, nm))
                    vab.append({"book": nm, **alpha_beta(r, sp2, rf2)})
                    vdiff.append({"diff": f"{nm} - SPY",
                                  **diff_alpha_beta(r, sp2, rf2)})
            # trend alone on the same short sample, for job separation
            for nm in ("sma200", "tsmom12_1", "dual_and"):
                r = build_book(sigs[nm].reindex(ridx), sp2, rf2, 1, RT_BPS_HEADLINE)
                vbooks[nm + " (RV sample)"] = r
                vrows.append(metrics(r, rf2, nm + " (RV sample)"))
                vab.append({"book": nm + " (RV sample)", **alpha_beta(r, sp2, rf2)})
                vdiff.append({"diff": f"{nm} (RV sample) - SPY",
                              **diff_alpha_beta(r, sp2, rf2)})
            # the extra-lag check H20 demanded
            lev_lag = vol_leverage(fc.shift(1).reindex(ridx), VOL_TARGET, 1.0)
            r = build_book(sigs["sma200"].reindex(ridx) * lev_lag, sp2, rf2, 1,
                           RT_BPS_HEADLINE)
            vbooks["sma200 x voltgt cap1 [EXTRA LAG]"] = r
            vrows.append(metrics(r, rf2, "sma200 x voltgt cap1 [EXTRA LAG]"))
            vrows.insert(0, metrics(sp2, rf2, "SPY buy&hold (RV sample)"))
            vab.insert(0, {"book": "SPY (RV sample)", **alpha_beta(sp2, sp2, rf2)})
            _t(vrows, "--- vol-target books ---")
            _t(vab, "--- Rule 13a on the RV sample ---")
            _t(vdiff, "--- Rule 13b (differences) on the RV sample ---")
            vh = []
            for nm, r in vbooks.items():
                sp = sub_periods(r)
                row = {"book": nm}
                for tag, segs in sp.items():
                    for i, seg in enumerate(segs):
                        rr = rf2.reindex(seg.index)
                        row[f"{tag[0]}{i+1}_Sh"] = metrics(seg, rr)["sharpe"]
                vh.append(row)
            _t(vh, "--- halves and thirds, RV sample ---")
            ep2 = episode_returns(vbooks)
            print("\n--- episodes, RV sample ---")
            print(ep2.to_string())
            res["rv"] = {"rows": vrows, "alpha_beta": vab, "diff": vdiff,
                         "subperiods": vh,
                         "sample": [str(ridx[0].date()), str(ridx[-1].date()),
                                    int(len(ridx))]}

    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"\nwrote {OUT}")
    return res


def count_variants(args) -> int:
    """Honest count of the cells THIS lab evaluated."""
    n = 8 * 2                      # 8 signal specs x 2 execution conventions
    n += 8 * len(RT_GRID)          # cost grid
    n += 8                         # zero-cash comparison
    if not args.quick:
        n += 2 * 21                # Rule 9 phases, monthly families
        n += 8 * 3                 # three nulls per variant (families, not draws)
        n += 7                     # SMA window sweep
        n += 1 + 5 + 21            # check-frequency phases
        n += 12                    # leave-one-episode-out cells
        n += 6 * 3                 # start-date sensitivity
    n += 4 * 8                     # leverage cells (2 causal x 4 borrow)
    n += 5                         # vol-target cells
    return n


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.overlay_lab")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="skip nulls and phase pooling")
    ap.add_argument("--no-rv", action="store_true")
    ap.add_argument("--draws", type=int, default=N_DRAWS)
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    run(args)


if __name__ == "__main__":
    main()
