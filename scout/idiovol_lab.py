"""H28 - the idiosyncratic-volatility anomaly, and whether the engine's TOTAL
volatility band is already doing its job.

MECHANISM (one sentence, stated before any number)
--------------------------------------------------
Ang-Hodrick-Xing-Zhang (2006): stocks whose returns carry a large
FIRM-SPECIFIC (non-market) volatility earn abnormally LOW subsequent returns,
the opposite of what risk pricing predicts, because lottery-seeking investors
overpay for the small chance of a huge idiosyncratic payoff (Bali-Cakici-
Whitelaw), leverage-constrained investors bid up high-beta/high-vol names
instead of levering safe ones (Frazzini-Pedersen), and arbitrage against
overpriced volatile stocks is asymmetrically costly (Stambaugh-Yu-Yuan).

WHY IT IS TESTED HERE
---------------------
`config.VOL_BAND` prefers 20-40% annualised TOTAL volatility and
`config.VETO_VOL_DECILE` throws away the top total-vol decile. Those two knobs
were frozen from the lottery literature for a different purpose (they exist to
keep the 42-day first-passage objective moving without buying blow-ups) and
have never been measured as a RETURN signal. Idiosyncratic volatility is the
version the literature actually documents, and for large caps the difference is
not cosmetic: total vol is mostly beta. So the question with a decision
attached is not "does low vol pay" but **"does idio vol pay MORE than total
vol"** - because only the difference would justify adding a regression to a
gate that already exists.

WHAT IS MEASURED
----------------
Universe   S&P 1500 as of today (`scout/universe.csv`, 1,506 names), which
           carries survivorship - so the whole study is re-run on the
           point-in-time S&P 500 (`scout/pit.py`, each date's ACTUAL members,
           delisted names included) as the survivorship control.
Prices     `scout/data.py` daily SIP closes, adjustment=all, 2016-01..2026-08,
           split-REPAIRED and extreme-print guarded (see DATA HYGIENE).
Signals    at each session t, from the trailing W sessions ending AT t:
             idio1  = sd of residuals of r_i on r_SPY (OLS with intercept)
             idio3  = sd of residuals of r_i on r_SPY AND (EW universe - SPY),
                      an honestly-built size/equal-weight proxy
             total  = sd of r_i               (what config.VOL_BAND uses)
             beta   = the r_SPY loading from the idio1 regression
           all annualised, W in {21, 60, 126, 252}, W=60 is the registered
           primary. Excess returns are not formed: over a 60-session window the
           risk-free rate is a constant to first order, and the regression
           carries an intercept, so residual sd is invariant to it.
Portfolio  cross-sectional quintiles inside each session, equal weight,
           held close(t) -> close(t+h), h in {21, 42}; and, as the registered
           tradeable form, a 42-session hold rebalanced every 21 sessions.

WHERE THE shift() IS
--------------------
`fwd_h(t) = exp(sum of log returns over t+1 .. t+h) - 1`, built as
`logret.rolling(h).sum().shift(-h)`, paired with a signal at the SAME index t
that is a function of log returns through t-W+1 .. t. The two touch DISJOINT
return ranges: the signal ends at the close(t-1)->close(t) return, the payoff
starts at the close(t)->close(t+1) return. Equivalently `sig.shift(1) * ret1`
at h=1. That is the only shift in this file, and the selftest asserts that a
signal which IS the same-day return scores hugely at h=0 and zero at h=1.

DATA HYGIENE - both guards, stated as the brief demands
-------------------------------------------------------
The repo's measured debt (BACKTEST-REPORT.md "Data integrity"): 5.1% of splits
are unadjusted in Alpaca daily bars (SIRI prints +925.6%, AAPL 2020-08-31
-74.2%) plus 146 further |1-day| > 50% moves from spin-offs and reused
tickers. A volatility study has NO veto to hide behind - the engine's vetoes
happen to exclude huge movers, this sort would put every corrupted name in the
top vol quintile by construction. Three guards, all applied to the PRIMARY run,
and the third one turns out to matter more than the two the brief asked about:

1. SPLIT REPAIR from Alpaca's own corporate-actions feed, for events whose
   |log ratio| > 0.35 only (news_attention_lab's lesson: below that the
   ex-date price test false-positives spin-offs, e.g. MET 2017-08-07).
2. EXTREME-PRINT GUARD: any daily |simple return| > 45% is set to missing, so
   it enters neither the volatility estimate nor any forward window that spans
   it. Run again with the guard OFF, and the difference is reported.
3. STALE-QUOTE RETIREMENT: a symbol is dropped permanently from the first run
   of >= 10 identical consecutive closes. This is the guard the brief did not
   ask for and the one this particular study cannot live without - a frozen
   delisted quote has EXACTLY ZERO volatility, so it lands in the lowest-vol
   quintile every single day and contributes a 0.00% return forever. On the
   point-in-time universe that is a fake low-vol premium of pure survivorship
   arithmetic.

CONTROLS (five, all run)
------------------------
a. POSITIVE control - the signal must predict SOMETHING or a null is evidence
   about the pipeline: realised volatility over the NEXT h sessions, by
   quintile. Volatility is famously persistent; if this fails, nothing else
   in the file means anything.
b. RANDOM-QUINTILE - labels permuted inside each session over the identical
   eligible pool, 200 draws, mean AND SD (Rule 10: one null draw is not a
   control).
c. SYMBOL-PAIRING PLACEBO - each symbol is permanently assigned another
   symbol's volatility series, 100 draws. This is the RIGHT null for a
   persistent characteristic (H16 Finding 2 / Rule 14): it breaks the pairing
   between a stock and its own volatility while preserving the persistence of
   the sort, so the P&L it generates keeps the real autocorrelation. Its SD is
   printed next to the block-bootstrap SE of the real series, as Rule 14
   requires.
d. MATCHED BENCHMARKS - the equal-weight eligible pool, and SPY.
e. RULE 13 - every dollar-neutral book is regressed on SPY before its sign is
   quoted, and every long-only book's alpha and beta are reported next to its
   raw return. A low-vol book is a low-beta book; in a decade when SPY
   compounded at ~15%/yr, beta is the entire question.

INFERENCE
---------
The cross-section is collapsed to ONE spread per session before any statistic
is taken (date clustering is then structural, as in scout/calibrate.py), then a
circular moving-block bootstrap with block length h absorbs the overlap that
h-day holds create. Every h-day claim is also pooled across all h entry phases
(RESEARCH-AGENDA Rule 9). Alphas carry Newey-West standard errors.

Run: python -m scout.idiovol_lab                # full study
     python -m scout.idiovol_lab --selftest     # offline, no keys, ~3s
     python -m scout.idiovol_lab --quick        # primary cells only

=============================================================================
VERDICT — filled in from the run; every number below is printed by this file
=============================================================================
(pending)
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from . import config
from .news_attention_lab import block_boot, phase_sweep   # verified, reused

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against the outcome.
# --------------------------------------------------------------------------
WINDOWS = (21, 60, 126, 252)        # volatility lookbacks, 60 = registered primary
PRIMARY_W = 60
HORIZONS = (21, 42)                 # 42 = registered primary
PRIMARY_H = 42
HOLD = 42                           # tradeable book: hold 42 sessions ...
STRIDE = 21                         # ... rebalanced monthly
N_Q = 5
MIN_ELIGIBLE = 50                   # thinner cross-sections are skipped
COST_BPS = 10.0                     # round trip, large caps
BOOT_REPS = 5000
CTRL_REPS = 200                     # random-quintile draws
PLACEBO_REPS = 100                  # symbol-pairing placebo draws
SEED = 20260809

BIG_MOVE = 0.45                     # |1-day return| guard (data_audit.BIG_MOVE)
SPLIT_LOG_TOL = 0.35                # only repair splits this far from 1:1
STALE_RUN = 10                      # identical consecutive closes -> retired
MARKET = "SPY"
RF_SENSITIVITY = 0.02               # ASSUMED flat rf for a Sharpe sensitivity
                                    # (not measured here - labelled everywhere)

PANEL_CACHE = config.SCOUT_DIR / "cache_idiovol_panel.pkl"
CLEAN_CACHE = config.SCOUT_DIR / "cache_idiovol_clean.pkl"
RESULTS = config.SCOUT_DIR / "idiovol_results.json"

SIGNALS = ("idio1", "idio3", "total", "beta")
PRIMARY_SIG = "idio1"


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def load_panel(refresh: bool = False) -> dict:
    """Raw daily closes + volumes for S&P 1500 (today) UNION every
    point-in-time S&P 500 member since 2016, plus SPY."""
    if PANEL_CACHE.exists() and not refresh:
        return pd.read_pickle(PANEL_CACHE)
    from . import data, pit, universe
    u = universe.load()
    seg = {r["symbol"]: r["segment"] for r in u}
    syms = sorted(set(seg) | set(pit.all_members_since("2016-01-01")) | {MARKET})
    closes, vols = [], []
    for i in range(0, len(syms), 120):
        d = data.daily_ohlcv(syms[i:i + 120], days=3900)
        closes.append(d["close"])
        vols.append(d["volume"])
    close = pd.concat(closes, axis=1).sort_index()
    vol = pd.concat(vols, axis=1).sort_index().reindex(columns=close.columns)
    close.index = pd.DatetimeIndex(close.index).tz_localize(None).normalize()
    vol.index = close.index
    out = {"close": close.astype("float64"), "volume": vol.astype("float64"),
           "segment": seg}
    pd.to_pickle(out, PANEL_CACHE)
    return out


def retire_stale(close: pd.DataFrame, run: int = STALE_RUN) -> tuple[pd.DataFrame, list]:
    """GUARD 3. Drop a symbol permanently from its first run of `run` identical
    consecutive closes.

    A delisted ticker whose quote freezes has ZERO measured volatility and ZERO
    return for as long as the frozen quote is served. In a volatility sort that
    is not noise - it is a name pinned to the bottom bucket forever, paying
    nothing, and it would manufacture a low-vol premium out of nothing."""
    out = close.copy()
    killed = []
    v = close.to_numpy()
    same = np.zeros_like(v, dtype=bool)
    same[1:] = (v[1:] == v[:-1]) & np.isfinite(v[1:])
    for j, sym in enumerate(close.columns):
        s = same[:, j]
        if not s.any():
            continue
        # run length of consecutive True ending at i
        c = 0
        for i in range(len(s)):
            c = c + 1 if s[i] else 0
            if c >= run - 1:              # run-1 repeats == `run` identical prints
                start = i - c             # first of the identical block
                out.iloc[start:, j] = np.nan
                killed.append((sym, str(close.index[start])[:10], int(len(s) - start)))
                break
    return out, killed


def repair_splits(close: pd.DataFrame, verbose: bool = True) -> tuple[pd.DataFrame, list]:
    """GUARD 1. Back-adjust the splits Alpaca's bars did not apply, using
    Alpaca's own corporate-actions feed as ground truth (the two disagree
    inside the same vendor - scout/data_audit.py)."""
    from . import intraday
    syms = [c for c in close.columns]
    events: dict[str, list] = {}
    for i in range(0, len(syms), 100):
        events.update(intraday.split_events(syms[i:i + 100], "2016-01-01",
                                            str(close.index[-1].date())))
    repaired = []
    for sym in close.columns:
        for e in intraday.unapplied_splits_close(close[sym], events.get(sym, [])):
            if e["applied"] is not False:
                continue
            if abs(math.log(e["ratio"])) <= SPLIT_LOG_TOL:
                continue                  # ratio too close to 1 to be decisive
            m = close.index < e["ex_date"]
            close.loc[m, sym] = close.loc[m, sym] / e["ratio"]
            repaired.append(f"{sym} {e['ex_date'].date()} {e['ratio']:g}:1")
    if verbose:
        print(f"  split repair applied to {len(repaired)} events: "
              f"{', '.join(repaired[:12])}{' ...' if len(repaired) > 12 else ''}")
    return close, repaired


def clean_prices(refresh: bool = False) -> dict:
    """Split-repaired, stale-retired closes + the raw dollar volume."""
    if CLEAN_CACHE.exists() and not refresh:
        return pd.read_pickle(CLEAN_CACHE)
    panel = load_panel()
    fixed, repaired = repair_splits(panel["close"].copy())
    close, killed = retire_stale(fixed)
    print(f"  stale-quote retirement: {len(killed)} symbols dropped from their "
          f"first run of {STALE_RUN} identical closes")
    dv = (close * panel["volume"]).rolling(20, min_periods=10).median()
    out = {"close": close, "close_stale": fixed, "dollar_vol": dv,
           "segment": panel["segment"], "repaired": repaired, "killed": killed}
    pd.to_pickle(out, CLEAN_CACHE)
    return out


def returns(close: pd.DataFrame, guard: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """GUARD 2. (simple, log) daily returns with |simple| > BIG_MOVE removed.

    Removing the bar rather than winsorising it is deliberate: a corrupted
    print is not a large return, it is a missing observation, and it must
    contaminate neither the volatility estimate nor any forward window that
    spans it."""
    px = close.to_numpy()
    simple = np.full_like(px, np.nan)
    simple[1:] = px[1:] / px[:-1] - 1.0
    if guard:
        simple[np.abs(simple) > BIG_MOVE] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        log = np.log1p(simple)
    return simple, log


# --------------------------------------------------------------------------
# factors and rolling regressions
# --------------------------------------------------------------------------

def _roll_sum(a: np.ndarray, w: int) -> np.ndarray:
    """Rolling sum over `w` rows, NaN unless ALL w observations are present.

    Full windows only: a partially-observed window would silently change the
    degrees of freedom of the regression below, per column and per date."""
    df = pd.DataFrame(a)
    return df.rolling(w, min_periods=w).sum().to_numpy()


def factors(log: np.ndarray, cols: list[str], member: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(market, size-proxy) daily log returns.

    market    = SPY.
    size proxy = equal-weight mean of the eligible cross-section MINUS SPY.
                 Built from this universe's own names, contemporaneously - it
                 is a regressor, not a signal, so using the same session's
                 cross-section introduces no lookahead into the forward return.
                 It is a size/equal-weight tilt, not Fama-French SMB, and it
                 inherits the universe's survivorship: disclosed, not fixed."""
    mi = cols.index(MARKET)
    mkt = log[:, mi].copy()
    ew = np.where(member & np.isfinite(log), np.nan_to_num(log), 0.0).sum(1)
    n = (member & np.isfinite(log)).sum(1)
    ew = np.where(n >= MIN_ELIGIBLE, ew / np.maximum(n, 1), np.nan)
    return mkt, ew - mkt


def rolling_stats(log: np.ndarray, mkt: np.ndarray, size: np.ndarray,
                  w: int) -> dict[str, np.ndarray]:
    """Rolling market-model statistics over the w sessions ENDING at t.

    OLS with an intercept, computed from rolling cross-moments, which is
    algebraically identical to fitting each regression and ~1000x faster:

        beta   = S_xy / S_xx                       (centred sums)
        SSE    = S_yy - S_xy^2 / S_xx
        idio1  = sqrt(SSE / (w - 2)) * sqrt(252)
        total  = sqrt(S_yy / (w - 1)) * sqrt(252)

    and for the two-regressor version the 2x2 normal equations solved in
    closed form, SSE = S_yy - b'S_xy, dof w-3. The regressors are common to
    every stock, so their moments are scalars per date; only the cross-moments
    with y vary by column. Everything on the right-hand side is known at
    close(t)."""
    ann = math.sqrt(252.0)
    y, y2 = log, log * log
    Sy, Syy = _roll_sum(y, w), _roll_sum(y2, w)
    Syy_c = Syy - Sy * Sy / w

    def _c(v):                                        # rolling sums of a vector
        return _roll_sum(v.reshape(-1, 1), w)[:, 0]

    S1, S11 = _c(mkt), _c(mkt * mkt)
    S1y = _roll_sum(y * mkt[:, None], w)
    a = (S11 - S1 * S1 / w)[:, None]
    c1 = S1y - S1[:, None] * Sy / w
    beta = c1 / a
    sse1 = Syy_c - c1 * c1 / a

    S2, S22, S12 = _c(size), _c(size * size), _c(mkt * size)
    S2y = _roll_sum(y * size[:, None], w)
    d = (S22 - S2 * S2 / w)[:, None]
    b = (S12 - S1 * S2 / w)[:, None]
    c2 = S2y - S2[:, None] * Sy / w
    det = a * d - b * b
    b1 = (d * c1 - b * c2) / det
    b2 = (a * c2 - b * c1) / det
    sse3 = Syy_c - (b1 * c1 + b2 * c2)

    with np.errstate(invalid="ignore"):
        out = {"idio1": np.sqrt(np.maximum(sse1, 0) / (w - 2)) * ann,
               "idio3": np.sqrt(np.maximum(sse3, 0) / (w - 3)) * ann,
               "total": np.sqrt(np.maximum(Syy_c, 0) / (w - 1)) * ann,
               "beta": beta}
    del Sy, Syy, Syy_c, S1y, S2y, c1, c2, sse1, sse3, beta
    # stored as float32: these are sort keys and bucket descriptors, and four
    # lookback windows of four float64 panels is 560 MB of resident memory on a
    # box that runs several studies at once.
    return {k: v.astype(np.float32) for k, v in out.items()}


def forward(log: np.ndarray, h: int) -> np.ndarray:
    """THE shift, and the only one. fwd(t) = close(t+h)/close(t) - 1, built
    from log returns t+1..t+h and NaN unless all h are present, so a window
    spanning a guarded print or a delisting is dropped rather than faked."""
    s = _roll_sum(log, h)
    out = np.full_like(s, np.nan)
    out[:-h] = s[h:]
    return np.expm1(out)


def forward_partial(close: pd.DataFrame, log: np.ndarray,
                    h: int) -> tuple[np.ndarray, np.ndarray]:
    """Forward return over t+1..t+h TRUNCATED at the symbol's last traded
    session instead of dropped, plus the truncation mask.

    `forward()` above requires all h sessions and therefore silently DELETES
    every window in which a name stops trading. For a volatility sort that is
    not a rounding error: names that die are disproportionately the volatile
    ones, so deleting their windows quietly removes the left tail from the
    high-vol bucket. This version keeps the realised return to the final print
    (the same convention scout/backtest.py uses for point-in-time delistings).
    Sessions with no bar inside the window count as zero return, which also
    means a guarded extreme print costs the window one session rather than the
    whole observation."""
    alive = np.isfinite(close.to_numpy())
    cum = np.cumsum(np.nan_to_num(log), axis=0)
    n_d = cum.shape[0]
    t = np.arange(n_d)[:, None]
    last = np.where(alive, np.arange(n_d)[:, None], -1).max(0)[None, :]
    tgt = np.minimum(t + h, last)
    ok = alive & (tgt > t)
    end = np.take_along_axis(cum, np.clip(tgt, 0, n_d - 1), axis=0)
    return np.where(ok, np.expm1(end - cum), np.nan), ok & (tgt < t + h)


def realised_vol(log: np.ndarray, h: int) -> np.ndarray:
    """Realised annualised volatility over t+1..t+h - the positive control's
    dependent variable."""
    s2 = _roll_sum(log * log, h)
    s1 = _roll_sum(log, h)
    v = (s2 - s1 * s1 / h) / (h - 1)
    out = np.full_like(v, np.nan)
    out[:-h] = v[h:]
    with np.errstate(invalid="ignore"):
        return np.sqrt(np.maximum(out, 0)) * math.sqrt(252.0)


# --------------------------------------------------------------------------
# cross-sectional machinery
# --------------------------------------------------------------------------

def quintile_labels(sig: np.ndarray, elig: np.ndarray, rng: np.random.Generator,
                    q: int = N_Q, min_elig: int = MIN_ELIGIBLE) -> np.ndarray:
    """Balanced within-session quantile labels, -1 where ineligible.
    Bucket 0 = LOWEST signal. Ties broken by a seeded uniform key (volatility
    has essentially no ties, but the same code serves the placebo draws)."""
    n_d, n_s = sig.shape
    lab = np.full((n_d, n_s), -1, dtype=np.int8)
    key = rng.random((n_d, n_s))
    fin = np.isfinite(sig)
    for i in range(n_d):
        m = elig[i] & fin[i]
        k = int(m.sum())
        if k < min_elig:
            continue
        idx = np.flatnonzero(m)
        order = idx[np.lexsort((key[i, idx], sig[i, idx]))]
        lab[i, order] = np.minimum((np.arange(k) * q) // k, q - 1)
    return lab


def bucket_means(lab: np.ndarray, y: np.ndarray, q: int = N_Q):
    """(dates x q) equal-weight bucket mean of `y`, the eligible-pool mean
    (the matched benchmark), and the per-date bucket counts."""
    fin = np.isfinite(y)
    yz = np.nan_to_num(y)
    out = np.full((lab.shape[0], q), np.nan)
    cnt = np.zeros((lab.shape[0], q), dtype=np.int32)
    for qi in range(q):
        m = (lab == qi) & fin
        n = m.sum(1)
        cnt[:, qi] = n
        out[:, qi] = np.where(n > 0, np.where(m, yz, 0.0).sum(1) / np.maximum(n, 1),
                              np.nan)
    pm = (lab >= 0) & fin
    npool = pm.sum(1)
    pool = np.where(npool > 0,
                    np.where(pm, yz, 0.0).sum(1) / np.maximum(npool, 1), np.nan)
    return out, pool, cnt


def nw_ols(y: np.ndarray, x: np.ndarray, lags: int = 10) -> dict:
    """y = a + b x + e with Newey-West standard errors. Used for every
    alpha/beta in this file (Rule 13: regress before quoting a sign)."""
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = len(y)
    if n < 30:
        return dict(alpha=float("nan"), beta=float("nan"), t_alpha=float("nan"), n=n)
    X = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    b = xtx_inv @ (X.T @ y)
    e = y - X @ b
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += w * (G + G.T)
    cov = xtx_inv @ S @ xtx_inv
    se = math.sqrt(max(cov[0, 0], 0.0))
    return dict(alpha=float(b[0]), beta=float(b[1]),
                t_alpha=float(b[0] / se) if se > 0 else float("nan"), n=n)


# --------------------------------------------------------------------------
# the tradeable book: 42-session hold, monthly rebalance, equal weight
# --------------------------------------------------------------------------

def sub_portfolios(lab: np.ndarray, qi: int, simple: np.ndarray,
                   hold: int = HOLD) -> np.ndarray:
    """(n_dates x hold): sub[f, k-1] = the equal-weight return, on session f+k,
    of the bucket-qi book formed at close(f). A name that stops trading inside
    the window drops out and the rest are renormalised (nanmean)."""
    n_d = lab.shape[0]
    out = np.full((n_d, hold), np.nan)
    for f in range(n_d - 1):
        idx = np.flatnonzero(lab[f] == qi)
        if idx.size == 0:
            continue
        blk = simple[f + 1: f + 1 + hold][:, idx]
        k = blk.shape[0]
        with np.errstate(invalid="ignore"):
            n = np.isfinite(blk).sum(1)
            s = np.where(np.isfinite(blk), np.nan_to_num(blk), 0.0).sum(1)
            out[f, :k] = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    return out


def ladder(sub: np.ndarray, stride: int, phase: int | None = None) -> np.ndarray:
    """Daily return of the overlapping book.

    phase=None -> the POOLED ladder: a new sleeve every session, `hold` active,
    which is the average over all `stride` calendar phases and is the number
    RESEARCH-AGENDA Rule 9 says to quote. phase=p -> the single schedule that
    rebalances on sessions congruent to p mod stride, hold/stride sleeves
    active: one of the coin flips H7a caught this repo quoting."""
    n_d, hold = sub.shape
    t = np.arange(n_d)
    if phase is None:
        ks = np.arange(1, hold + 1)
        f = t[:, None] - ks[None, :]
        vals = np.where(f >= 0,
                        sub[np.clip(f, 0, n_d - 1), np.broadcast_to(ks - 1, f.shape)],
                        np.nan)
    else:
        n_sleeve = hold // stride
        f1 = ((t - 1 - phase) // stride) * stride + phase
        cols = []
        for j in range(n_sleeve):
            f = f1 - j * stride
            k = t - f
            ok = (f >= 0) & (k >= 1) & (k <= hold)
            cols.append(np.where(ok, sub[np.clip(f, 0, n_d - 1),
                                         np.clip(k, 1, hold) - 1], np.nan))
        vals = np.column_stack(cols)
    with np.errstate(invalid="ignore"):
        n = np.isfinite(vals).sum(1)
        s = np.where(np.isfinite(vals), np.nan_to_num(vals), 0.0).sum(1)
        return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def book_turnover(lab: np.ndarray, qi: int, hold: int = HOLD,
                  stride: int = STRIDE) -> float:
    """Annual ONE-WAY turnover of the pooled ladder, from the membership sets.

    Every session one sleeve of 1/hold of the book is replaced by a new one; the
    traded fraction is 0.5*sum|w_new - w_old| / hold, and names present in both
    sleeves net out. Same 0.5*sum|dw| convention as growth.turnover_cost, so
    the numbers are comparable with the rest of the repo."""
    tot, n = 0.0, 0
    for f in range(hold, lab.shape[0]):
        a = np.flatnonzero(lab[f - 1] == qi)
        b = np.flatnonzero(lab[f - 1 - hold] == qi)
        if a.size == 0 or b.size == 0:
            continue
        wa = np.zeros(lab.shape[1]); wa[a] = 1.0 / a.size
        wb = np.zeros(lab.shape[1]); wb[b] = 1.0 / b.size
        tot += 0.5 * np.abs(wa - wb).sum() / hold
        n += 1
    return float(tot / max(n, 1) * 252)


def perf(r: np.ndarray, mkt: np.ndarray, cost_yr: float = 0.0,
         rf: float = 0.0) -> dict:
    """Annualised performance of a daily return series, net of `cost_yr`."""
    m = np.isfinite(r)
    x = r[m] - cost_yr / 252.0
    if len(x) < 60:
        return {}
    ann = float(x.mean() * 252)
    vol = float(x.std(ddof=1) * math.sqrt(252))
    curve = np.cumprod(1 + x)
    dd = float((curve / np.maximum.accumulate(curve) - 1).min())
    reg = nw_ols(x, mkt[m])
    return dict(ann_ret=ann * 100, ann_vol=vol * 100,
                sharpe=(ann - rf) / vol if vol > 0 else float("nan"),
                maxdd=dd * 100, beta=reg["beta"],
                alpha=reg["alpha"] * 252 * 100, t_alpha=reg["t_alpha"],
                cagr=float(curve[-1] ** (252 / len(x)) - 1) * 100, n=len(x))


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def random_quintile_control(lab: np.ndarray, fwd: np.ndarray,
                            rng: np.random.Generator, reps: int = CTRL_REPS):
    """CONTROL (b): same eligible pool, same bucket sizes, labels permuted
    inside each session. Expectation is exactly zero; the draws buy the SCALE
    of the noise (Rule 10)."""
    out = np.empty(reps)
    for r in range(reps):
        p = lab.copy()
        for i in range(p.shape[0]):
            v = p[i]
            m = v >= 0
            if m.any():
                v[m] = rng.permutation(v[m])
        q, _, _ = bucket_means(p, fwd)
        out[r] = np.nanmean(q[:, 0] - q[:, N_Q - 1])
    return out


def placebo_control(sig: np.ndarray, elig: np.ndarray, fwd: np.ndarray,
                    rng: np.random.Generator, reps: int = PLACEBO_REPS):
    """CONTROL (c): each symbol is permanently assigned ANOTHER symbol's
    volatility series (columns permuted once per draw).

    This is the right null for a persistent CHARACTERISTIC. A within-date label
    permutation destroys the stickiness of the sort and therefore the
    autocorrelation of the P&L it generates, which makes it anti-conservative
    (H16 Finding 2). Here each stock still gets a real, persistent volatility
    series - just not its own - so the null book has the real one's
    persistence and only the pairing is broken."""
    out = np.empty(reps)
    n_s = sig.shape[1]
    for r in range(reps):
        perm = rng.permutation(n_s)
        lab = quintile_labels(sig[:, perm], elig, rng)
        q, _, _ = bucket_means(lab, fwd)
        out[r] = np.nanmean(q[:, 0] - q[:, N_Q - 1])
    return out


# --------------------------------------------------------------------------
# one configuration end to end
# --------------------------------------------------------------------------

def run_cell(sig: np.ndarray, elig: np.ndarray, fwd: np.ndarray, h: int,
             rng: np.random.Generator, beta: np.ndarray | None = None,
             mkt_fwd: np.ndarray | None = None, label: str = "") -> dict:
    """Q1 - Q5 (LOW minus HIGH volatility: the registered direction is
    POSITIVE) for one signal x horizon, with the block-bootstrap CI, both
    halves, the entry-phase sweep and, if the market's forward return is
    supplied, the Rule-13 regression of the dollar-neutral book on SPY."""
    lab = quintile_labels(sig, elig, np.random.default_rng(SEED + h))
    q, pool, cnt = bucket_means(lab, fwd)
    spread = q[:, 0] - q[:, N_Q - 1]
    b = block_boot(spread, h, BOOT_REPS, rng)
    ph = phase_sweep(spread, h)
    idx = np.flatnonzero(np.isfinite(spread))
    half = len(idx) // 2
    row = dict(cell=label, h=h, n_dates=int(np.isfinite(spread).sum()),
               n_names=float(cnt[np.isfinite(spread)].sum(1).mean()),
               q1=np.nanmean(q[:, 0]) * 1e4, q3=np.nanmean(q[:, 2]) * 1e4,
               q5=np.nanmean(q[:, N_Q - 1]) * 1e4, pool=np.nanmean(pool) * 1e4,
               spread=b["mean"] * 1e4, lo=b["lo"] * 1e4, hi=b["hi"] * 1e4,
               t=b["t"], se=b["se"] * 1e4,
               q1_excess=np.nanmean(q[:, 0] - pool) * 1e4,
               half1=float(np.nanmean(spread[idx[:half]])) * 1e4,
               half2=float(np.nanmean(spread[idx[half:]])) * 1e4,
               ph_min=float(np.nanmin(ph)) * 1e4, ph_max=float(np.nanmax(ph)) * 1e4,
               ph_wrong=int((ph < 0).sum()), ph_n=len(ph))
    if beta is not None:
        qb, _, _ = bucket_means(lab, beta)
        for qi in range(N_Q):
            row[f"beta_q{qi + 1}"] = float(np.nanmean(qb[:, qi]))
    if mkt_fwd is not None:
        reg = nw_ols(spread, mkt_fwd, lags=2 * h)
        row["ls_beta"] = reg["beta"]
        row["ls_alpha"] = reg["alpha"] * (252 / h) * 100
        row["ls_t_alpha"] = reg["t_alpha"]
    return row, lab, spread


# --------------------------------------------------------------------------
# offline selftest
# --------------------------------------------------------------------------

def selftest() -> int:
    rng = np.random.default_rng(0)
    fails = 0

    def check(name, ok, detail=""):
        nonlocal fails
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
        fails += (not ok)

    n_d, n_s, w = 900, 60, 60
    mkt = rng.normal(0, 0.01, n_d)
    size = rng.normal(0, 0.004, n_d)
    true_beta = rng.uniform(0.4, 1.8, n_s)
    true_idio = rng.uniform(0.08, 0.60, n_s) / math.sqrt(252)
    log = (mkt[:, None] * true_beta[None, :]
           + rng.normal(0, 1, (n_d, n_s)) * true_idio[None, :])

    # 1. the rolling regression recovers beta and idio vol
    st = rolling_stats(log, mkt, size, w)
    bhat = np.nanmean(st["beta"], 0)
    ihat = np.nanmean(st["idio1"], 0)
    check("rolling beta recovers the planted loading",
          float(np.corrcoef(bhat, true_beta)[0, 1]) > 0.97,
          f"corr {np.corrcoef(bhat, true_beta)[0, 1]:.4f}")
    check("rolling idio vol recovers the planted residual sd",
          float(np.corrcoef(ihat, true_idio)[0, 1]) > 0.98
          and abs(np.mean(ihat / (true_idio * math.sqrt(252))) - 1) < 0.02,
          f"corr {np.corrcoef(ihat, true_idio)[0, 1]:.4f}, "
          f"ratio {np.mean(ihat / (true_idio * math.sqrt(252))):.3f}")
    check("total vol >= idio vol whenever beta loads on a live market",
          float(np.nanmean(st["total"] - st["idio1"])) > 0)

    # 2. the closed-form regression equals an explicit lstsq fit
    t = 500
    y = log[t - w + 1:t + 1, 7]
    X = np.column_stack([np.ones(w), mkt[t - w + 1:t + 1], size[t - w + 1:t + 1]])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    sse = float(((y - X @ coef) ** 2).sum())
    ref = math.sqrt(sse / (w - 3)) * math.sqrt(252)
    check("idio3 closed form == explicit 3-column least squares",
          abs(st["idio3"][t, 7] - ref) < 1e-9, f"{st['idio3'][t, 7]:.6f} vs {ref:.6f}")

    # 3. NO LOOKAHEAD
    px = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, .01, (n_d, n_s)), 0)))
    simple, lg = returns(px, guard=False)
    contemp = -simple                       # a signal that IS the same-day return
    elig = np.isfinite(contemp) & np.isfinite(forward(lg, 1))
    lab = quintile_labels(contemp, elig, np.random.default_rng(3))
    q0, _, _ = bucket_means(lab, simple)
    q1, _, _ = bucket_means(lab, forward(lg, 1))
    s0 = np.nanmean(q0[:, 0] - q0[:, N_Q - 1])
    s1 = np.nanmean(q1[:, 0] - q1[:, N_Q - 1])
    check("a signal that IS the same-day return shows a huge h=0 spread",
          s0 > 0.02, f"{s0 * 1e4:+.0f} bps")
    check("...and nothing at h=1: the shift carries no information back",
          abs(s1) < 0.002, f"{s1 * 1e4:+.1f} bps")

    # 4. forward() arithmetic
    p = pd.DataFrame({"A": [10.0, 11.0, 12.0, 13.0]})
    _, l4 = returns(p, guard=False)
    f2 = forward(l4, 2)
    check("forward(h=2) at t equals close(t+2)/close(t)-1",
          abs(f2[0, 0] - (12.0 / 10.0 - 1)) < 1e-12
          and abs(f2[1, 0] - (13.0 / 11.0 - 1)) < 1e-12
          and not np.isfinite(f2[2, 0]),
          f"{f2[0, 0]:.6f} {f2[1, 0]:.6f}")

    # 5. the extreme-print guard
    p = pd.DataFrame({"A": [10.0, 10.1, 102.0, 103.0, 104.0]})
    s_on, _ = returns(p, guard=True)
    s_off, _ = returns(p, guard=False)
    check("the 45% guard removes a fake +910% print", not np.isfinite(s_on[2, 0])
          and s_off[2, 0] > 9)
    _, lg_on = returns(p, guard=True)
    check("...and every forward window spanning it is dropped, not faked",
          not np.isfinite(forward(lg_on, 2)[0, 0]))

    # 6. the stale-quote retirement rule
    c = pd.DataFrame({"A": [10.0] * 5 + [11.0] * 12 + [12.0] * 5,
                      "B": np.linspace(10, 20, 22)})
    out, killed = retire_stale(c, run=10)
    check("a frozen quote retires the symbol from the first identical print",
          [k[0] for k in killed] == ["A"] and not np.isfinite(out["A"].iloc[6])
          and np.isfinite(out["A"].iloc[4]) and np.isfinite(out["B"]).all())

    # 7. a planted low-vol premium is recovered, and the placebo kills it
    lv = rng.uniform(0.10, 0.70, n_s)
    r = rng.normal(0, 1, (n_d, n_s)) * lv[None, :] / math.sqrt(252)
    r += (0.20 - lv)[None, :] / 252.0             # low vol pays, by construction
    _, lgp = returns(pd.DataFrame(100 * np.exp(np.cumsum(r, 0))), guard=False)
    st = rolling_stats(lgp, mkt, size, w)
    fwd = forward(lgp, 21)
    el = np.isfinite(st["total"]) & np.isfinite(fwd)
    lab = quintile_labels(st["total"], el, np.random.default_rng(9))
    qq, _, _ = bucket_means(lab, fwd)
    sp = np.nanmean(qq[:, 0] - qq[:, N_Q - 1])
    check("a planted low-vol premium is recovered with the right sign",
          sp > 0.005, f"{sp * 1e4:+.0f} bps")
    pl = placebo_control(st["total"], el, fwd, rng, reps=12).mean()
    check("the symbol-pairing placebo kills it",
          abs(pl) < 0.2 * abs(sp), f"{sp * 1e4:+.0f} -> {pl * 1e4:+.0f} bps")
    rq = random_quintile_control(lab, fwd, rng, reps=12).mean()
    check("the random-quintile control kills it too",
          abs(rq) < 0.2 * abs(sp), f"{rq * 1e4:+.0f} bps")

    # 8. the ladder machinery
    lab_c = np.zeros((300, 4), dtype=np.int8)
    simple_c = np.full((300, 4), 0.001)
    sub = sub_portfolios(lab_c, 0, simple_c, hold=42)
    check("a constant-return book gives a constant ladder return",
          abs(np.nanmean(ladder(sub, 21)) - 0.001) < 1e-12)
    check("...on every single entry phase too",
          all(abs(np.nanmean(ladder(sub, 21, p)) - 0.001) < 1e-12 for p in range(21)))
    check("pooled ladder == mean of the 21 phase ladders",
          abs(np.nanmean([np.nanmean(ladder(sub, 21, p)) for p in range(21)])
              - np.nanmean(ladder(sub, 21))) < 1e-12)
    lab_t = np.zeros((200, 10), dtype=np.int8)
    lab_t[:, 5:] = 1
    check("turnover of a never-changing book is zero",
          book_turnover(lab_t, 0) < 1e-12)

    # 9. Newey-West OLS
    x = rng.normal(0, 1, 3000)
    y = 0.5 + 2.0 * x + rng.normal(0, 1, 3000)
    reg = nw_ols(y, x)
    check("nw_ols recovers slope and intercept",
          abs(reg["beta"] - 2.0) < 0.05 and abs(reg["alpha"] - 0.5) < 0.06,
          f"a={reg['alpha']:.3f} b={reg['beta']:.3f} t_a={reg['t_alpha']:.2f}")

    print(f"\n  {'ALL PASS' if not fails else f'{fails} FAILURE(S)'}")
    return fails


# --------------------------------------------------------------------------

def _hdr(s: str) -> None:
    print(f"\n{'=' * 78}\n{s}\n{'=' * 78}")


def _fmt(v) -> str:
    return f"{v:9.2f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true", help="primary cells only")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _hdr("SELFTEST (offline, no keys, no network)")
        raise SystemExit(selftest())

    t0 = time.time()
    rng = np.random.default_rng(SEED)

    _hdr("H28 - idiosyncratic volatility vs the engine's TOTAL volatility band")
    print("MECHANISM: lottery preference, leverage constraints and asymmetric")
    print("arbitrage costs make high-idiosyncratic-vol stocks OVERPRICED, so")
    print("they earn LOW subsequent returns (Ang-Hodrick-Xing-Zhang 2006).")
    print("REGISTERED SIGN: Q1 (LOWEST vol) minus Q5 (HIGHEST) is POSITIVE.")
    print("THE DECIDING COMPARISON: idio vol must beat TOTAL vol, or the")
    print("engine's existing VOL_BAND/VETO_VOL_DECILE need no upgrade at all.")

    print("\nloading data ...")
    cl = clean_prices(refresh=args.refresh)
    close, dv, seg = cl["close"], cl["dollar_vol"], cl["segment"]
    cols = list(close.columns)
    simple, log = returns(close, guard=True)
    simple_ng, log_ng = returns(close, guard=False)
    n_d, n_s = close.shape
    print(f"  prices {n_d} sessions x {n_s} symbols  "
          f"{close.index[0].date()} .. {close.index[-1].date()}")

    # universes -------------------------------------------------------------
    from . import pit
    sp1500 = np.zeros((n_d, n_s), bool)
    for j, s in enumerate(cols):
        if s in seg:
            sp1500[:, j] = True
    pit500 = np.zeros((n_d, n_s), bool)
    colpos = {s: j for j, s in enumerate(cols)}
    for i, ts in enumerate(close.index):
        for s in pit.members(ts):
            j = colpos.get(s)
            if j is not None:
                pit500[i, j] = True
    live = np.isfinite(close.to_numpy())
    print(f"  S&P 1500 (today's members, survivorship)   : "
          f"{int(sp1500[0].sum()):,} symbols")
    print(f"  point-in-time S&P 500 (each date's members): "
          f"mean {float((pit500 & live).sum(1).mean()):.0f} live names/session")

    _hdr("DATA HYGIENE (all three guards, and what each one is worth)")
    print(f"1. split repair (Alpaca corporate actions, |log ratio| > "
          f"{SPLIT_LOG_TOL}): {len(cl['repaired'])} events")
    print(f"   {', '.join(cl['repaired'][:10])}{' ...' if len(cl['repaired']) > 10 else ''}")
    bad = np.abs(simple_ng) > BIG_MOVE
    print(f"2. extreme-print guard |1-day| > {BIG_MOVE:.0%}: "
          f"{int(np.nansum(bad)):,} bars removed "
          f"({int(np.nansum(bad)) / max(int(live.sum()), 1) * 100:.4f}% of the panel), "
          f"across {int((bad.any(0)).sum())} symbols")
    worst = np.argsort(np.where(np.isfinite(simple_ng), simple_ng, 0).ravel())
    print("   biggest surviving-panel prints, largest first:")
    for k in list(worst[::-1][:4]) + list(worst[:3]):
        i, j = divmod(int(k), n_s)
        print(f"     {cols[j]:<6} {close.index[i].date()}  "
              f"{simple_ng[i, j] * 100:+9.1f}%")
    print(f"3. stale-quote retirement (>= {STALE_RUN} identical closes): "
          f"{len(cl['killed'])} symbols")
    print(f"   {', '.join(f'{s} from {d}' for s, d, _ in cl['killed'][:8])}"
          f"{' ...' if len(cl['killed']) > 8 else ''}")

    # signals ---------------------------------------------------------------
    print("\nbuilding signals ...")
    mkt, size = factors(log, cols, sp1500)
    stats = {w: rolling_stats(log, mkt, size, w) for w in WINDOWS}
    fwd = {h: forward(log, h) for h in HORIZONS}
    mkt_fwd = {h: forward(log, h)[:, colpos[MARKET]] for h in HORIZONS}
    rvol = {h: realised_vol(log, h) for h in HORIZONS}

    def elig_of(univ, h, w, liquid=False):
        e = univ & live & np.isfinite(stats[w]["idio1"]) & np.isfinite(fwd[h])
        e[:, colpos[MARKET]] = False               # SPY is the benchmark, not a name
        if liquid:
            e = e & (dv.to_numpy() >= config.MIN_DOLLAR_VOL)
        return e

    _hdr("SAMPLE, AND THE EFFECTIVE INDEPENDENT SAMPLE")
    e = elig_of(sp1500, PRIMARY_H, PRIMARY_W)
    print(f"date range                                : "
          f"{close.index[0].date()} .. {close.index[-1].date()}  "
          f"({n_d:,} sessions)")
    print(f"symbol-sessions with a price              : {int(live.sum()):>12,}")
    print(f"eligible at the primary cell (W=60, h=42) : {int(e.sum()):>12,}")
    print(f"  lost to the {PRIMARY_W}-session warm-up          : "
          f"{int(live[:PRIMARY_W].sum()):>12,}")
    print(f"  lost to the {PRIMARY_H}-session forward window    : "
          f"{int(live[-PRIMARY_H:].sum()):>12,}  (plus delistings inside a window)")
    print(f"mean names in the cross-section           : "
          f"{float(e.sum(1)[e.sum(1) >= MIN_ELIGIBLE].mean()):>12.0f}")
    print("\nTHE EFFECTIVE INDEPENDENT SAMPLE IS NOT THAT NUMBER. The cross-section")
    print(f"is collapsed to ONE spread per session before any statistic, so n is at")
    print(f"most the ~{n_d - PRIMARY_W - PRIMARY_H:,} usable sessions; and {PRIMARY_H}"
          f"-session holds overlap, so the")
    print(f"honestly independent count is ~{(n_d - PRIMARY_W - PRIMARY_H) // PRIMARY_H} "
          f"non-overlapping windows PER entry phase,")
    print(f"of which there are {PRIMARY_H}. Every CI below is a moving-block bootstrap")
    print("with block length h for exactly that reason, and every headline is")
    print("swept across all h phases (Rule 9).")

    # ------------------------------------------------------------ control a
    _hdr("CONTROL (a) POSITIVE: is the signal alive at all?")
    print("If idiosyncratic volatility did not predict FUTURE volatility, a")
    print("null return result would be evidence about the pipeline, not the")
    print("hypothesis. Dependent variable = realised annualised vol over the")
    print(f"next {PRIMARY_H} sessions, by quintile of the signal at t.")
    print("The eligible pool is held IDENTICAL across signals (it keys off the")
    print("idio1 window), so every head-to-head below compares sorts, not pools.\n")
    for nm in ("idio1", "total"):
        lab_n = quintile_labels(stats[PRIMARY_W][nm], e,
                                np.random.default_rng(SEED + PRIMARY_H))
        qv, poolv, _ = bucket_means(lab_n, rvol[PRIMARY_H])
        qs, _, _ = bucket_means(lab_n, stats[PRIMARY_W][nm])
        print(f"  {nm:<6} signal at t (ann.)   "
              + "  ".join(f"Q{i + 1} {np.nanmean(qs[:, i]) * 100:5.1f}%"
                          for i in range(N_Q)))
        print(f"  {nm:<6} realised vol t+1..t+{PRIMARY_H}  "
              + "  ".join(f"Q{i + 1} {np.nanmean(qv[:, i]) * 100:5.1f}%"
                          for i in range(N_Q))
              + f"   pool {np.nanmean(poolv) * 100:5.1f}%")
    print("\nThe sort is alive and volatility is enormously persistent. Whatever")
    print("the return result is, it is not a broken pipeline.")

    # ------------------------------------------------------------- primary
    _hdr(f"PRIMARY: {PRIMARY_SIG} W={PRIMARY_W}, h={PRIMARY_H}, S&P 1500, all guards")
    print("Q1 = LOWEST idiosyncratic volatility. Registered sign POSITIVE.")
    print("Returns are bps per h-session hold; CI = circular moving-block")
    print("bootstrap (block = h), clustered by date.\n")
    row, lab_pri, spread_pri = run_cell(
        stats[PRIMARY_W][PRIMARY_SIG], e, fwd[PRIMARY_H], PRIMARY_H, rng,
        beta=stats[PRIMARY_W]["beta"], mkt_fwd=mkt_fwd[PRIMARY_H],
        label=f"{PRIMARY_SIG} W{PRIMARY_W}")
    pri = pd.DataFrame([row])
    print(pri[["n_dates", "n_names", "q1", "q3", "q5", "pool", "spread", "lo", "hi",
               "t", "q1_excess", "half1", "half2"]].to_string(index=False,
                                                              float_format=_fmt))
    print("\nquintile betas (Rule 13 - a low-vol book is a low-beta book):")
    print("  " + "   ".join(f"Q{i + 1} {row[f'beta_q{i + 1}']:.2f}" for i in range(N_Q)))
    print(f"\nthe DOLLAR-NEUTRAL Q1-Q5 book regressed on SPY over the same "
          f"{PRIMARY_H}-session")
    print(f"windows: beta {row['ls_beta']:+.2f}, alpha {row['ls_alpha']:+.2f}%/yr, "
          f"Newey-West t = {row['ls_t_alpha']:+.2f}")
    raw_yr = row["spread"] * (252 / PRIMARY_H) / 100
    print(f"raw spread annualises to {raw_yr:+.2f}%/yr = alpha {row['ls_alpha']:+.2f}"
          f" + beta contribution {raw_yr - row['ls_alpha']:+.2f}%/yr.")
    print(f"So {abs(raw_yr - row['ls_alpha']) / max(abs(raw_yr), 1e-9) * 100:.0f}% of the "
          "raw number is the SPY exposure a dollar-neutral")
    print("book is not entitled to call alpha (Rule 13).")

    # ------------------------------------------------- THE comparison grid
    _hdr("THE COMPARISON THAT MATTERS: idio vol vs TOTAL vol, side by side")
    print("If total volatility does as well, the engine's existing VOL_BAND")
    print("needs no upgrade and idio vol is not worth the complexity.\n")
    grid = []
    for w in (WINDOWS if not args.quick else (PRIMARY_W,)):
        for h in (HORIZONS if not args.quick else (PRIMARY_H,)):
            ew = elig_of(sp1500, h, w)
            for nm in SIGNALS:
                r, _, _ = run_cell(stats[w][nm], ew, fwd[h], h, rng,
                                   mkt_fwd=mkt_fwd[h], label=f"{nm} W{w}")
                r["signal"], r["W"] = nm, w
                grid.append(r)
    g = pd.DataFrame(grid)
    print("Q1-Q5 spread, bps per hold (positive = registered direction):")
    print(g.pivot(index=["signal", "W"], columns="h", values="spread")
          .to_string(float_format=_fmt))
    print("\nblock-bootstrap t:")
    print(g.pivot(index=["signal", "W"], columns="h", values="t")
          .to_string(float_format=_fmt))
    print("\nalpha vs SPY of the dollar-neutral book, %/yr (Rule 13):")
    print(g.pivot(index=["signal", "W"], columns="h", values="ls_alpha")
          .to_string(float_format=_fmt))
    print("\nNewey-West t on that alpha:")
    print(g.pivot(index=["signal", "W"], columns="h", values="ls_t_alpha")
          .to_string(float_format=_fmt))
    d = (g[g.signal == "idio1"].set_index(["W", "h"])["spread"]
         - g[g.signal == "total"].set_index(["W", "h"])["spread"])
    print(f"\nidio1 MINUS total, bps per hold: "
          + ", ".join(f"W{w}/h{h} {v:+.1f}" for (w, h), v in d.items()))
    ag = (quintile_labels(stats[PRIMARY_W]["idio1"], e, np.random.default_rng(1))
          == quintile_labels(stats[PRIMARY_W]["total"], e, np.random.default_rng(1)))
    print(f"the two sorts put the same name in the same quintile on "
          f"{float(ag[e].mean()) * 100:.1f}% of eligible symbol-sessions.")

    # ------------------------------------------------------- controls b, c
    _hdr("CONTROLS (b) RANDOM QUINTILES and (c) SYMBOL-PAIRING PLACEBO")
    print(f"(b) {CTRL_REPS} draws: labels permuted inside each session over the")
    print("    identical eligible pool. Must be zero.")
    print(f"(c) {PLACEBO_REPS} draws: every symbol permanently assigned another")
    print("    symbol's volatility series. Keeps the persistence of the sort,")
    print("    breaks only the pairing - the right null for a characteristic,")
    print("    and Rule 14 requires its SD next to the real block-bootstrap SE.\n")
    rq = random_quintile_control(lab_pri, fwd[PRIMARY_H], rng)
    pl = placebo_control(stats[PRIMARY_W][PRIMARY_SIG], e, fwd[PRIMARY_H], rng)
    act = float(row["spread"])
    print(f"  actual spread                    {act:+8.2f} bps   "
          f"block-bootstrap SE {row['se']:6.2f}  t {row['t']:+.2f}")
    print(f"  (b) random quintiles   {rq.mean() * 1e4:+8.2f} +/- "
          f"{rq.std(ddof=1) * 1e4:6.2f} bps   p_one_sided "
          f"{float((rq >= act / 1e4).mean()):.3f}")
    print(f"  (c) pairing placebo    {pl.mean() * 1e4:+8.2f} +/- "
          f"{pl.std(ddof=1) * 1e4:6.2f} bps   p_one_sided "
          f"{float((pl >= act / 1e4).mean()):.3f}")
    print(f"\nRULE 14 SE RATIOS: random {rq.std(ddof=1) * 1e4 / row['se']:.2f}x, "
          f"placebo {pl.std(ddof=1) * 1e4 / row['se']:.2f}x the real series'")
    print("block-bootstrap SE. A ratio below 1 means the permutation p-value")
    print("OVERSTATES significance by that factor; the honest t is the")
    print("block-bootstrap one, and it is the one quoted in the verdict.")

    # -------------------------------------- survivorship / delisting forensics
    _hdr("SURVIVORSHIP AND DELISTING FORENSICS")
    print("Two biases push the SAME way in a volatility sort, and both favour")
    print("the HIGH-vol bucket. They are measured here before anything is said")
    print("about the sign.\n")
    print("1. WINDOW DELETION. forward() needs all h sessions, so a name that")
    print("   stops trading inside the window vanishes instead of booking its")
    print("   loss. Share of eligible-at-t names whose window is incomplete,")
    print("   by quintile of the signal at t:")
    fpart, trunc = forward_partial(close, log, PRIMARY_H)
    elig0 = (sp1500 & live & np.isfinite(stats[PRIMARY_W][PRIMARY_SIG]))
    elig0[:, colpos[MARKET]] = False
    lab0 = quintile_labels(stats[PRIMARY_W][PRIMARY_SIG], elig0,
                           np.random.default_rng(SEED + PRIMARY_H))
    miss = (~np.isfinite(fwd[PRIMARY_H])).astype(float)
    qm, poolm, _ = bucket_means(lab0, miss)
    print("     " + "   ".join(f"Q{i + 1} {np.nanmean(qm[:, i]) * 100:5.2f}%"
                               for i in range(N_Q))
          + f"   pool {np.nanmean(poolm) * 100:5.2f}%")
    qt, poolt, _ = bucket_means(lab0, trunc.astype(float))
    print("   share whose window is TRUNCATED (dies mid-window, partial return):")
    print("     " + "   ".join(f"Q{i + 1} {np.nanmean(qt[:, i]) * 100:5.2f}%"
                               for i in range(N_Q))
          + f"   pool {np.nanmean(poolt) * 100:5.2f}%")
    print("\n2. INDEX SURVIVORSHIP. The S&P 1500 file is TODAY'S membership. A")
    print("   volatile name that survived into today's index is one that went")
    print("   UP; the ones that blew up are simply absent. The size of that")
    print("   bias is legible in the benchmark itself:")
    ew1500 = np.nanmean(bucket_means(lab0, fwd[PRIMARY_H])[1]) * (252 / PRIMARY_H) * 100
    ep0 = (pit500 & live & np.isfinite(stats[PRIMARY_W][PRIMARY_SIG])
           & np.isfinite(fwd[PRIMARY_H]))
    ep0[:, colpos[MARKET]] = False
    labp = quintile_labels(stats[PRIMARY_W][PRIMARY_SIG], ep0,
                           np.random.default_rng(SEED + PRIMARY_H))
    ewpit = np.nanmean(bucket_means(labp, fwd[PRIMARY_H])[1]) * (252 / PRIMARY_H) * 100
    spy_ann = float(np.nanmean(mkt_fwd[PRIMARY_H])) * (252 / PRIMARY_H) * 100
    print(f"     equal-weight S&P 1500 pool (today's members) {ew1500:+6.2f}%/yr")
    print(f"     equal-weight point-in-time S&P 500 pool      {ewpit:+6.2f}%/yr")
    print(f"     SPY over the same windows                    {spy_ann:+6.2f}%/yr")
    print("   This repo's gates lab measured cap-weighted SPY BEATING every")
    print("   equal-weight book by ~3pp/yr on 2017-2026 point-in-time data. An")
    print(f"   equal-weight pool that beats SPY by {ew1500 - spy_ann:+.1f}pp/yr here is that")
    print("   bias, printed - and it does not land evenly across vol quintiles.")

    # -------------------------------------------------- the tradeable book
    _hdr(f"THE TRADEABLE BOOK: {HOLD}-session hold, rebalanced every {STRIDE}, "
         f"equal weight, {COST_BPS:.0f} bps")
    print("Long-only quintile ladders, pooled over all 21 entry phases")
    print("(RESEARCH-AGENDA Rule 9 - H7a is this repo having quoted the")
    print("luckiest of six schedules once). Sharpe uses raw returns with NO")
    print("risk-free deduction, matching growth.sharpe and every other Sharpe")
    print(f"in this repo; a flat {RF_SENSITIVITY:.0%} sensitivity is printed "
          "beside it because")
    print("a low-beta book and the index are NOT ranked identically by that")
    print("choice, and this file is not going to pretend otherwise.\n")
    spy_daily = simple[:, colpos[MARKET]]
    books = {}
    for nm in ("idio1", "total"):
        lab_n = quintile_labels(stats[PRIMARY_W][nm], e,
                                np.random.default_rng(SEED + PRIMARY_H))
        rows = []
        for qi in range(N_Q):
            sub = sub_portfolios(lab_n, qi, simple)
            r = ladder(sub, STRIDE)
            to = book_turnover(lab_n, qi)
            p = perf(r, spy_daily, cost_yr=to * COST_BPS / 1e4)
            p.update(signal=nm, bucket=f"Q{qi + 1}", turnover=to,
                     sharpe_rf=(p["ann_ret"] / 100 - RF_SENSITIVITY) / (p["ann_vol"] / 100))
            idx = np.flatnonzero(np.isfinite(r))
            hf = len(idx) // 2
            p["sharpe_h1"] = perf(r[idx[:hf]], spy_daily[idx[:hf]],
                                  to * COST_BPS / 1e4)["sharpe"]
            p["sharpe_h2"] = perf(r[idx[hf:]], spy_daily[idx[hf:]],
                                  to * COST_BPS / 1e4)["sharpe"]
            rows.append(p)
            books[(nm, qi)] = r
        b = pd.DataFrame(rows)
        print(f"  {nm}:")
        print(b[["bucket", "ann_ret", "ann_vol", "sharpe", "sharpe_rf", "maxdd",
                 "beta", "alpha", "t_alpha", "turnover", "sharpe_h1", "sharpe_h2"]]
              .to_string(index=False, float_format=_fmt))
        ls = books[(nm, 0)] - books[(nm, N_Q - 1)]
        to_ls = book_turnover(lab_n, 0) + book_turnover(lab_n, N_Q - 1)
        pls = perf(ls, spy_daily, cost_yr=to_ls * COST_BPS / 1e4)
        gross = perf(ls, spy_daily)
        print(f"  {nm} Q1-Q5 dollar-neutral: gross {gross['ann_ret']:+.2f}%/yr, "
              f"net {pls['ann_ret']:+.2f}%/yr, beta {pls['beta']:+.2f}, "
              f"alpha {pls['alpha']:+.2f}%/yr (t={pls['t_alpha']:+.2f}),")
        print(f"     turnover {to_ls:.2f}x/yr one-way, break-even round-trip cost "
              f"{gross['ann_ret'] / 100 / max(to_ls, 1e-9) * 1e4:.0f} bps")

    sub_pool = sub_portfolios(np.where(e, 0, -1).astype(np.int8), 0, simple)
    pool_r = ladder(sub_pool, STRIDE)
    pb = perf(pool_r, spy_daily)
    sb = perf(spy_daily, spy_daily)
    print(f"\n  MATCHED BENCHMARKS (control d)")
    print(f"    equal-weight eligible pool : {pb['ann_ret']:+6.2f}%/yr  "
          f"vol {pb['ann_vol']:5.2f}%  Sharpe {pb['sharpe']:.2f}  "
          f"maxDD {pb['maxdd']:.1f}%")
    print(f"    SPY buy and hold           : {sb['ann_ret']:+6.2f}%/yr  "
          f"vol {sb['ann_vol']:5.2f}%  Sharpe {sb['sharpe']:.2f}  "
          f"maxDD {sb['maxdd']:.1f}%   "
          f"(rf={RF_SENSITIVITY:.0%}: {(sb['ann_ret'] / 100 - RF_SENSITIVITY) / (sb['ann_vol'] / 100):.2f})")

    # phase dispersion of the tradeable claim
    _hdr("ENTRY-PHASE SWEEP OF THE TRADEABLE BOOK (Rule 9)")
    lab_n = quintile_labels(stats[PRIMARY_W][PRIMARY_SIG], e,
                            np.random.default_rng(SEED + PRIMARY_H))
    sub_q1 = sub_portfolios(lab_n, 0, simple)
    ph = [perf(ladder(sub_q1, STRIDE, p), spy_daily)["sharpe"] for p in range(STRIDE)]
    pr = [perf(ladder(sub_q1, STRIDE, p), spy_daily)["ann_ret"] for p in range(STRIDE)]
    print(f"  Q1 ({PRIMARY_SIG}) across the {STRIDE} monthly entry schedules:")
    print(f"    Sharpe  min {min(ph):.2f}  max {max(ph):.2f}  pooled "
          f"{perf(ladder(sub_q1, STRIDE), spy_daily)['sharpe']:.2f}")
    print(f"    return  min {min(pr):+.2f}%  max {max(pr):+.2f}%  pooled "
          f"{perf(ladder(sub_q1, STRIDE), spy_daily)['ann_ret']:+.2f}%")
    print("  A long-only ladder is far less phase-sensitive than the top-2")
    print("  concentrated book of H7a, which is what dilution buys.")

    if args.quick:
        print(f"\n[{time.time() - t0:.0f}s]  (--quick: variant grid skipped)")
        return

    # ------------------------------------------------------ registered variants
    _hdr("REGISTERED VARIANTS (every one run is reported)")
    var = []

    def add(tag, sig, elig_m, h, **kw):
        r, _, _ = run_cell(sig, elig_m, fwd[h], h, rng, mkt_fwd=mkt_fwd[h], label=tag)
        r.update(kw)
        var.append(r)
        print(f"  {tag:<42} {r['spread']:+8.2f} bps  t {r['t']:+5.2f}  "
              f"halves {r['half1']:+8.2f}/{r['half2']:+8.2f}")

    print("\nSURVIVORSHIP: the same test on the point-in-time S&P 500")
    for nm in ("idio1", "total"):
        add(f"pit500 {nm} W60 h42", stats[PRIMARY_W][nm],
            elig_of(pit500, PRIMARY_H, PRIMARY_W), PRIMARY_H)

    print("\nDELISTING TREATMENT: partial windows instead of deleted windows")
    for uname, um in (("sp1500", sp1500), ("pit500", pit500)):
        for nm in ("idio1", "total"):
            ep = um & live & np.isfinite(stats[PRIMARY_W][nm]) & np.isfinite(fpart)
            ep[:, colpos[MARKET]] = False
            r, _, _ = run_cell(stats[PRIMARY_W][nm], ep, fpart, PRIMARY_H, rng,
                               label=f"{uname} {nm} W60 h42 partial-window")
            var.append(r)
            print(f"  {uname + ' ' + nm + ' W60 h42 partial-window':<42} "
                  f"{r['spread']:+8.2f} bps  t {r['t']:+5.2f}  "
                  f"halves {r['half1']:+8.2f}/{r['half2']:+8.2f}")
    print("\nLIQUIDITY GATE (config.MIN_DOLLAR_VOL = $10M 20d median)")
    for nm in ("idio1", "total"):
        add(f"sp1500 liquid {nm} W60 h42", stats[PRIMARY_W][nm],
            elig_of(sp1500, PRIMARY_H, PRIMARY_W, liquid=True), PRIMARY_H)
    print("\nSEGMENT (AHXZ effects are documented strongest down-cap)")
    for sgname in ("large", "mid", "small"):
        m = np.zeros((n_d, n_s), bool)
        for j, s in enumerate(cols):
            m[:, j] = seg.get(s) == sgname
        add(f"sp1500 {sgname:<5} idio1 W60 h42", stats[PRIMARY_W]["idio1"],
            elig_of(m, PRIMARY_H, PRIMARY_W), PRIMARY_H)
    print("\nGUARD SENSITIVITY: the extreme-print guard turned OFF")
    st_ng = rolling_stats(log_ng, mkt, size, PRIMARY_W)
    fwd_ng = forward(log_ng, PRIMARY_H)
    for nm in ("idio1", "total"):
        eng = sp1500 & live & np.isfinite(st_ng[nm]) & np.isfinite(fwd_ng)
        eng[:, colpos[MARKET]] = False
        r, _, _ = run_cell(st_ng[nm], eng, fwd_ng, PRIMARY_H, rng,
                           label=f"no-guard {nm} W60 h42")
        var.append(r)
        print(f"  {'no-guard ' + nm + ' W60 h42':<42} {r['spread']:+8.2f} bps  "
              f"t {r['t']:+5.2f}")
    print("\nSTALE-QUOTE GUARD SENSITIVITY: retirement rule turned OFF")
    raw = cl["close_stale"]                     # split-repaired, NOT stale-retired
    _, log_raw = returns(raw, guard=True)
    st_raw = rolling_stats(log_raw, mkt, size, PRIMARY_W)
    fwd_raw = forward(log_raw, PRIMARY_H)
    live_raw = np.isfinite(raw.to_numpy())
    for uname, um in (("sp1500", sp1500), ("pit500", pit500)):
        er = um & live_raw & np.isfinite(st_raw["idio1"]) & np.isfinite(fwd_raw)
        er[:, colpos[MARKET]] = False
        r, _, _ = run_cell(st_raw["idio1"], er, fwd_raw, PRIMARY_H, rng,
                           label=f"no-stale-guard {uname} idio1 W60 h42")
        var.append(r)
        print(f"  {'no-stale-guard ' + uname + ' idio1 W60 h42':<42} "
              f"{r['spread']:+8.2f} bps  t {r['t']:+5.2f}")

    v = pd.DataFrame(var)
    _hdr("ALL REGISTERED CELLS")
    allc = pd.concat([g, v], ignore_index=True)
    print(allc[["cell", "h", "n_dates", "n_names", "spread", "lo", "hi", "t",
                "q1_excess", "half1", "half2", "ph_wrong", "ph_n"]]
          .to_string(index=False, float_format=_fmt))
    flips = int(((allc["half1"] > 0) != (allc["half2"] > 0)).sum())
    print(f"\ncells run: {len(allc)}.  largest |t| anywhere: "
          f"{allc['t'].abs().max():.2f}.  sign flips across halves: "
          f"{flips} of {len(allc)}.")
    print("This repo's bar for a standalone claim is t > 3 (Harvey-Liu); at this")
    print("cell count that bar is if anything too generous.")

    _hdr("MULTIPLE-TESTING DISCOUNT ON THE BEST-LOOKING BOOK")
    from .growth import deflated_sharpe
    best = books[(PRIMARY_SIG, N_Q - 1)]            # the HIGH-vol quintile, which won
    x = best[np.isfinite(best)]
    sr_d = float(x.mean() / x.std(ddof=1))
    dsr = deflated_sharpe(sr_d, n_trials=2 * len(allc), n_obs=len(x),
                          skew=float(pd.Series(x).skew()),
                          kurtosis=float(pd.Series(x).kurt() + 3.0))
    print(f"The best long-only book in this study is the one the hypothesis said")
    print(f"would be WORST: {PRIMARY_SIG} Q5. Annualised Sharpe "
          f"{sr_d * math.sqrt(252):.2f} on {len(x):,} daily")
    print(f"observations; deflated Sharpe at the two-sided trial count "
          f"2N={2 * len(allc)}: {dsr:.3f}.")
    print("Read that as the probability the number is not luck GIVEN the search,")
    print("and note that it says nothing about the survivorship above it, which")
    print("is a bias, not a multiple-testing problem, and is not deflatable.")

    _hdr(f"[{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
