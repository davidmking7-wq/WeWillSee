"""H38 — the rebalancing premium, ISOLATED: same names, same start, same end,
the only difference is whether the book is rebalanced.

MECHANISM (one sentence, Rule 1)
--------------------------------
A continuously rebalanced long-only portfolio's log growth exceeds the weighted
average of its own constituents' log growth rates by Fernholz's excess growth
rate gamma* = 0.5 * (sum_i w_i sigma_ii - w' Sigma w), which is strictly
positive for any diversified long-only book — return manufactured out of
volatility and imperfect correlation, containing no forecast of any kind.

THE CORRECTION THAT IS THE WHOLE SUBTLETY, AND THE REASON THIS LAB EXISTS
------------------------------------------------------------------------
gamma* is the excess growth of the rebalanced portfolio over **the weighted
average of its constituents' LOG growth rates**. That quantity is NOT a
tradeable portfolio: nobody can buy "the average of the log growth rates".
The tradeable alternative is BUY-AND-HOLD, and buy-and-hold ALSO exceeds the
weighted average of log growth rates, by Jensen, because it drifts into the
winners — the terminal basket value is a weighted average of gross returns and
the log of an average exceeds the average of the logs.

    ln(sum_i w_i P_i(T)/P_i(0))  >=  sum_i w_i ln(P_i(T)/P_i(0))

So **"gamma* > 0" does NOT imply "rebalancing beats buy-and-hold"**, and the
popular claim that volatility harvesting is free money rests on exactly that
confusion. Writing J(T) for the buy-and-hold Jensen term, the tradeable
quantity is

    A - B  =  gamma*        -  J(T)/T
           = (rebal premium) - (buy-and-hold's drift-into-winners bonus)

and which arm wins depends on gamma* against the realised dispersion of
constituent growth. Both of the facts this repo already measured are true at
once and for this reason: the analytic gamma* of an equal-weighted PIT S&P 500
averages **+4.12 %/yr** (H31f measured +3.89 %/yr on the same panel), yet RSP
returned 12.53 %/yr against SPY's 15.34 %/yr. gamma* was paid in full. It was
paid against the WRONG benchmark.

METHOD
------
UNIVERSE   point-in-time S&P 500 (`scout/pit.py`), each formation date's ACTUAL
           members, delisted names included. 742 union symbols, 745 with the
           three benchmarks, all served from `bars.py`'s master cache.
SPAN       2016-01-04 .. 2026-08-07 (the full cached span). The first 252
           sessions are covariance warm-up, so formations run 2017-01-31 ..
           2026-07-31.
THE ARMS   At each formation date t0, from a basket of n PIT members:
             ARM A  equal weight at t0, rebalanced back to equal weight at
                    every month-end strictly inside (t0, t1], at the CLOSE.
             ARM B  THE IDENTICAL STOCKS, THE IDENTICAL WEIGHTS AT t0, NEVER
                    REBALANCED — it drifts for the full hold.
           Same names, same start, same end, same delisting policy, same
           cost model. A - B is the rebalancing premium with selection,
           survivorship and forecasting differenced out.
THE SHIFT  Weights and the covariance matrix at t0 are formed from closes
           through the CLOSE of t0 (trailing 252 sessions, inclusive of t0).
           The book is executed at the close of t0 and earns returns from the
           close of t0+1 onward: the simulator's loop runs over rows
           `t0+1 .. t1` and never touches row t0's return. That is the only
           place in this file where a weight meets a return, and it is why
           there is no same-bar look-ahead. Positions are held close-to-close
           throughout; no open prices, no intraday fills.
DRIFT      D in {1, 3, 12, 60} months, rolling monthly formations, PLUS a
HORIZON    full-horizon arm (12 monthly-offset formations through 2017, each
           held to 2026-08-07, ~8.6-9.5 years). This is the axis the earlier
           quick test could not see: it re-formed BOTH arms every month, so
           arm B only ever drifted for one month and the two arms had no time
           to diverge.
THIRD ARM  Every basket also carries U_i, the constituent's own buy-and-hold
           value, so the decomposition A - W and B - W is measured directly,
           where W = sum_i w_i ln(U_i(T)) is the weighted average constituent
           LOG growth. A - W is the REALISED gamma*; B - W is the Jensen term.
           This is what turns "the premium is ten times smaller than gamma*"
           from a puzzle into an arithmetic identity.
COSTS      one-way turnover x cost_bps/1e4 (growth.turnover_cost's convention,
           cost_bps quoted ROUND TRIP), charged identically in both arms.
           Headline 5 bps; 0 and 10 bps reported. Arm B's only turnover is the
           delisting redistribution, which arm A pays too.
BENCHMARK  SPY total-return-adjusted daily closes from the master cache, buy
           and hold. BIL is the cash leg and the risk-free rate — measured,
           2.13 %/yr over the span, never hardcoded.
STATS      Overlapping formations are NOT independent: a moving-block bootstrap
           over formation-date means with block length = the hold length in
           months (scout/calibrate.py's date-clustering plus high52_lab's block
           length). Effective independent sample = span_months / D is reported
           beside the raw basket count. Rule 16: the MC sd of every bootstrap t
           is reported from 8 re-seeds.

DATA DEFECTS GUARDED — all three, and this is which
---------------------------------------------------
1. SPLIT REPAIR (`high52_lab.repair_splits`, Alpaca corporate actions as ground
   truth). 7 unadjusted splits repaired on this panel. NOT optional: an
   unrepaired split is a -50% print that arm B holds forever.
2. EXTREME-PRINT MASK. After repair, any remaining |1-day return| > 45% is a
   spin-off or a reused ticker; the RETURN is set to zero for that name-day.
3. FROZEN QUOTES (`idiovol_lab.retire_stale`, run of 10 identical closes) —
   the defect that manufactured +896 bps of fake drift in H26 and the one that
   is lethal HERE, because arm B holds a dead name for the whole horizon while
   arm A would keep buying it back to 1/n. 24 symbols retired.
   **The benchmarks are excluded from guard 3**: BIL's closes are genuinely
   flat and retire_stale kills it on 2016-08-03 if you let it.
DELISTING POLICY, ONE SENTENCE, IDENTICAL IN BOTH ARMS: a name is retired at
its first frozen-quote run or its last valid close, its position is liquidated
at that last close and the proceeds are redistributed PRO RATA across the
still-live holdings of the SAME arm (so arm B's relative weights are untouched
— a pro-rata redistribution is not a rebalance) with the resulting turnover
charged in both arms; the `--cash-on-death` sensitivity parks the proceeds in
BIL instead, in both arms.

CONTROLS (Rule 3)
-----------------
(i)  POSITIVE CONTROL, MANDATORY AND RUN FIRST (`--synthetic`): iid lognormal
     returns with a KNOWN sigma and rho pushed through the SAME simulator.
     The measured A - W must land on the theoretical
     gamma* = 0.5 sigma^2 (1-rho) (1-1/n). If the machinery cannot recover a
     known answer, no number on real data means anything.
(ii) The synthetic world is also the NULL for A - B: with identical true mu
     across names there is no forecastable growth dispersion, so it tells us
     what A - B is worth when the theorem is exactly true and nothing else is.
(iii) RANDOM BASKETS (rand30, 40 draws per formation date) — the selection-free
     basket, and the sample that carries the gamma* sort.
(iv) MATCHED BENCHMARK: SPY on identical days, Rule 13 on the book AND on the
     A - B difference series.

PRE-REGISTRATION (written before the first real-data number)
------------------------------------------------------------
| #    | hypothesis | pass condition |
|------|------------|----------------|
| H38a | POSITIVE CONTROL. On iid lognormal synthetic data the measured A - W recovers the analytic gamma* = 0.5 s^2 (1-rho)(1-1/n). | |measured/analytic - 1| < 0.05 |
| H38b | DECOMPOSITION. On real PIT S&P 500 baskets, realised A - W tracks the covariance-predicted gamma* one-for-one. | OLS slope of realised on predicted in [0.7, 1.3] |
| H38c | **THE GAP.** The reason realised A - B is ~10x smaller than gamma* is the buy-and-hold Jensen term B - W, not a failure of the theorem. | B - W accounts for >70% of gamma* at D = 12m |
| H38d | **THE SCALING TEST.** A - B rises with arm B's drift horizon and approaches gamma* as D grows, because J(T)/T decays while gamma* does not. | A - B monotone increasing in D in {1,3,12,60,full} |
| H38e | FALSIFIABLE PREDICTION. Baskets with high predicted gamma* deliver high realised A - B: gamma* is forecastable AND monetisable. | within-date Q5-Q1 of A-B by predicted gamma* > 0, t > 2 |
| H38f | COSTS. The premium survives 5 bps round trip at monthly rebalance. | break-even cost > 5 bps |
| H38g | RULE 13. A - B is not beta. | |beta of the A-B difference series on SPY| < 0.15 |
| H38h | A rebalanced equal-weight book beats SPY on SHARPE, not merely on CAGR. | Sharpe(A) > Sharpe(SPY) |

Failure conditions stated in advance: H38a fails and the lab is void if the
control misses; H38d fails — and the theorem's application here is broken, not
merely mis-specified — if lengthening arm B's drift does not raise A - B;
H38e fails if the gamma* sort is flat, which would make gamma* a description
rather than a signal.

VERDICT (2026-08-10, filled in from the run this file reproduces)
-----------------------------------------------------------------
See `scout/rebalance_results.json` and the printed report. Summary in the
module's `VERDICT` constant, which is written from measured values only.

WHAT THIS TEST CANNOT SETTLE
----------------------------
- Ten years is one macro regime. 2016-2026 is the most concentration-driven
  decade on record: the cross-sectional dispersion of realised constituent
  growth (which is what feeds the Jensen term and therefore hurts arm A) was
  exceptionally large. A decade in which the mega-caps mean-revert would move
  A - B up mechanically, and this lab cannot tell you whether that happens.
  This is the `needs_refresh` tag, not `watch_only`.
- The universe is large-cap. gamma* scales with s^2 (1-rho); a mid- or
  small-cap basket has a materially larger gamma* AND a materially larger
  growth dispersion, and this panel cannot say which grows faster because
  `pit.py` is S&P 500 only and `universe.csv` is survivorship-biased.
- Costs are modelled as a linear bps charge on turnover. It is a good model at
  S&P 500 liquidity and a bad one for a book that must trade 500 names in a
  crisis, which is exactly when the rebalance turnover is largest.
- A - B is a difference of two long books. It says nothing about whether
  either book should be owned; H38h is the only cell that asks that, and Rule
  13 is why it is asked on Sharpe rather than on CAGR.

Run:
    python -m scout.rebalance_lab --synthetic     # the positive control alone
    python -m scout.rebalance_lab                 # everything (~4 min)
    python -m scout.rebalance_lab --no-guard      # guards 2 and 3 off
    python -m scout.rebalance_lab --cash-on-death # delisting-policy sensitivity
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from . import bars, config, growth, pit
from .high52_lab import nw_se, repair_splits
from .idiovol_lab import retire_stale

RESULTS = config.SCOUT_DIR / "rebalance_results.json"

START = "2016-01-01"
END = "2026-08-07"
BENCHES = ("SPY", "BIL", "RSP")
WARMUP = 252              # trailing sessions for the covariance / eligibility
BIG_MOVE = 0.45           # guard 2
STALE_RUN = 10            # guard 3
TD_YEAR = 252
COST_BPS = 5.0            # headline round-trip cost, large caps
SEED = 20260810
BOOT = 4000
MC_SEEDS = 8              # Rule 16: MC sd of the bootstrap t
RAND_DRAWS = 40           # random baskets per formation date
NW_LAG = 10               # daily series, no mechanical overlap

# Registry: the running trial count before this lab (BACKTEST-REPORT.md H31d
# quotes N = 729) plus the variants this file registers.
N_PRIOR = 729

VARIANTS: list[str] = []


def _v(name: str) -> str:
    VARIANTS.append(name)
    return name


# ---------------------------------------------------------------- statistics

def ann_from_log(g: float, days: int) -> float:
    """Annualised continuously-compounded rate from a log growth over `days`."""
    return g * TD_YEAR / max(days, 1)


def cagr(daily: np.ndarray) -> float:
    r = np.asarray(daily, float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 0.0
    return float(np.exp(np.log1p(r).sum() * TD_YEAR / len(r)) - 1.0)


def ann_vol(daily: np.ndarray) -> float:
    r = np.asarray(daily, float)
    r = r[np.isfinite(r)]
    return float(np.std(r, ddof=1) * math.sqrt(TD_YEAR)) if len(r) > 2 else 0.0


def sharpe_excess(daily: np.ndarray, rf: np.ndarray) -> float:
    x = np.asarray(daily, float) - np.asarray(rf, float)
    x = x[np.isfinite(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return 0.0
    return float(x.mean() / x.std(ddof=1) * math.sqrt(TD_YEAR))


def max_dd(daily: np.ndarray) -> float:
    r = np.nan_to_num(np.asarray(daily, float))
    curve = np.cumprod(1.0 + r)
    return float((curve / np.maximum.accumulate(curve) - 1.0).min()) if len(curve) else 0.0


def ols_alpha_beta(y: np.ndarray, x: np.ndarray, lag: int = NW_LAG) -> dict:
    """Rule 13. y and x are DAILY EXCESS returns (rf already removed, or a
    zero-cost difference for which rf is irrelevant). Returns annualised alpha,
    beta, and a FULL Newey-West HAC sandwich t on the intercept — not
    nw_se(resid), which assumes the regressor is mean-zero. The H29 kill in
    this repo was a hard-coded NW lag; this one is stated and it is 10, which
    is right for a DAILY series with no mechanical overlap."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = len(y)
    if n < 30:
        return {"alpha_ann": 0.0, "beta": 0.0, "t_alpha": 0.0, "n": int(n)}
    X = np.column_stack([np.ones(n), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    XtX_inv = np.linalg.pinv(X.T @ X)
    u = resid[:, None] * X                      # (n, 2) score contributions
    S = u.T @ u
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        G = u[l:].T @ u[:-l]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = math.sqrt(max(float(V[0, 0]), 1e-300))
    a = float(coef[0])
    return {"alpha_ann": float(a * TD_YEAR), "beta": float(coef[1]),
            "t_alpha": float(a / se) if se > 0 else 0.0, "n": int(n)}


def block_boot(x: np.ndarray, block: int, reps: int = BOOT, seed: int = SEED) -> dict:
    """Moving-block bootstrap of the mean of a per-formation-date series.
    One observation per FORMATION DATE (date clustering, calibrate.py's
    discipline); block length = the hold length in months, which is what
    additionally respects the overlap of the holds themselves."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {"mean": float(x.mean()) if n else 0.0, "se": float("nan"),
                "t": 0.0, "n": n, "lo": float("nan"), "hi": float("nan")}
    block = max(1, min(int(block), max(1, n // 3)))
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n]
    draws = x[idx].mean(1)
    se = float(draws.std(ddof=1))
    lo, hi = (float(v) for v in np.percentile(draws, [2.5, 97.5]))
    return {"mean": float(x.mean()), "se": se,
            "t": float(x.mean() / se) if se > 0 else 0.0,
            "n": n, "lo": lo, "hi": hi, "block": block}


def boot_t_mc_sd(x: np.ndarray, block: int) -> float:
    """Rule 16: the Monte-Carlo sd of the bootstrap t across re-seeds."""
    ts = [block_boot(x, block, reps=BOOT, seed=SEED + 977 * k)["t"]
          for k in range(MC_SEEDS)]
    return float(np.std(ts, ddof=1))


def halves_thirds(x: np.ndarray) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 6:
        return {"halves": [], "thirds": []}
    h = n // 2
    t = n // 3
    return {"halves": [float(x[:h].mean()), float(x[h:].mean())],
            "thirds": [float(x[:t].mean()), float(x[t:2 * t].mean()),
                       float(x[2 * t:].mean())]}


# ------------------------------------------------------------- panel assembly

class Panel:
    """Guarded daily return panel, plus liveness, benchmarks and calendars."""

    def __init__(self, guard: bool = True, verbose: bool = True):
        syms = pit.all_members_since(START)
        raw = bars.get(sorted(set(syms) | set(BENCHES)), START, END, verbose=verbose)
        repaired, split_rows = repair_splits(raw)
        close = repaired["close"]
        vol = repaired["volume"]

        eq = [s for s in close.columns if s not in BENCHES]
        eq_close = close[eq]

        killed: list = []
        if guard:
            eq_close, killed = retire_stale(eq_close, run=STALE_RUN)

        ret = eq_close.pct_change()
        n_extreme = int((ret.abs() > BIG_MOVE).sum().sum())
        if guard:
            ret = ret.mask(ret.abs() > BIG_MOVE, 0.0)

        # liveness: between the first and last finite close AFTER guard 3
        finite = eq_close.notna()
        first = finite.values.argmax(0)
        anyf = finite.values.any(0)
        last = len(finite) - 1 - finite.values[::-1].argmax(0)
        rows = np.arange(len(finite))[:, None]
        live = (rows >= first[None, :]) & (rows <= last[None, :]) & anyf[None, :]

        self.dates = close.index
        self.symbols = list(eq_close.columns)
        self.sym_ix = {s: i for i, s in enumerate(self.symbols)}
        self.live = live
        self.ret = np.nan_to_num(ret.to_numpy(), nan=0.0) * live
        self.dollar_vol = np.nan_to_num(
            (eq_close * vol[eq]).to_numpy(), nan=0.0) * live
        self.spy = np.nan_to_num(close["SPY"].pct_change().to_numpy(), nan=0.0)
        self.bil = np.nan_to_num(close["BIL"].pct_change().to_numpy(), nan=0.0)
        self.rsp = np.nan_to_num(close["RSP"].pct_change().to_numpy(), nan=0.0)
        self.guard = guard
        self.diag = {
            "symbols": len(self.symbols),
            "dates": len(self.dates),
            "splits_repaired": len(split_rows),
            "frozen_quote_retirements": len(killed),
            "extreme_prints_masked": n_extreme if guard else 0,
            "density": float(finite.mean().mean()),
            "guards_2_3": bool(guard),
        }
        # month-end trading rows
        me = pd.Series(np.arange(len(self.dates)), index=self.dates)
        # np.sort returns a fresh writable array; .to_numpy() can hand back a
        # read-only view whose in-place .sort() raises ValueError
        self.month_end = np.sort(
            me.groupby([self.dates.year, self.dates.month]).max().to_numpy())

    # -------------------------------------------------------- basket builders

    def eligible(self, t0: int) -> np.ndarray:
        """Column indices of PIT members live at t0 with >= WARMUP sessions of
        history AND live through the whole warm-up window (so the covariance
        matrix is a real one, not a padded one)."""
        if t0 < WARMUP:
            return np.array([], int)
        members = pit.members(self.dates[t0].date())
        cand = [self.sym_ix[s] for s in members if s in self.sym_ix]
        if not cand:
            return np.array([], int)
        cand = np.array(sorted(cand))
        ok = self.live[t0 - WARMUP + 1:t0 + 1, cand].all(0)
        return cand[ok]


# --------------------------------------------------------------- the two arms

def run_formation(P: Panel, t0: int, t1: int, cols: np.ndarray,
                  rebal_rows: set[int], cost_bps: float,
                  cash_on_death: bool = False,
                  keep_paths: bool = False) -> dict:
    """Run ARM A (rebalanced) and ARM B (never rebalanced) on the SAME cols.

    cols is (K, n) column indices — K baskets sharing one window. Returns log
    growths, turnover and (optionally) the daily return paths.

    THE SHIFT: the loop runs over rows t0+1 .. t1 inclusive. Row t0's return is
    never touched, so the weights formed at the close of t0 earn only returns
    realised after t0. There is no other place in this file where a weight
    meets a return.
    """
    K, n = cols.shape
    cost = cost_bps / 10_000.0
    VA = np.full((K, n), 1.0 / n)
    VB = VA.copy()
    U = np.ones((K, n))              # each constituent's own buy-and-hold value
    held = np.ones((K, n), bool)
    cashA = np.zeros(K)
    cashB = np.zeros(K)
    turnA = np.zeros(K)
    turnB = np.zeros(K)
    T = t1 - t0
    pathA = np.zeros((T, K)) if keep_paths else None
    pathB = np.zeros((T, K)) if keep_paths else None

    for k, t in enumerate(range(t0 + 1, t1 + 1)):
        prevA = VA.sum(1) + cashA
        prevB = VB.sum(1) + cashB
        r = P.ret[t][cols]
        held_prev = held.copy()
        VA *= (1.0 + r) * held
        VB *= (1.0 + r) * held
        if cash_on_death:
            cashA *= (1.0 + P.bil[t])
            cashB *= (1.0 + P.bil[t])
        gA = (VA.sum(1) + cashA) / np.maximum(prevA, 1e-300)

        # ---- delisting, IDENTICAL POLICY IN BOTH ARMS -------------------
        liv = P.live[t][cols]
        dead_now = held & (~liv)
        if dead_now.any():
            freedA = (VA * dead_now).sum(1)
            freedB = (VB * dead_now).sum(1)
            VA = np.where(dead_now, 0.0, VA)
            VB = np.where(dead_now, 0.0, VB)
            held = held & liv
            if cash_on_death:
                cashA += freedA
                cashB += freedB
            else:
                baseA = VA.sum(1)
                baseB = VB.sum(1)
                okA = baseA > 0
                okB = baseB > 0
                VA[okA] += freedA[okA, None] * VA[okA] / baseA[okA, None]
                VB[okB] += freedB[okB, None] * VB[okB] / baseB[okB, None]
                cashA[~okA] += freedA[~okA]
                cashB[~okB] += freedB[~okB]
            totA = VA.sum(1) + cashA
            totB = VB.sum(1) + cashB
            tA = freedA / np.maximum(totA, 1e-300)
            tB = freedB / np.maximum(totB, 1e-300)
            VA *= (1.0 - tA * cost)[:, None]
            VB *= (1.0 - tB * cost)[:, None]
            cashA *= (1.0 - tA * cost)
            cashB *= (1.0 - tB * cost)
            turnA += tA
            turnB += tB

        # ---- the constituent tracker (arm W): own return while alive, then
        #      the surviving equal-weight basket, so W is always defined ----
        U = np.where(held_prev, U * (1.0 + r), U * gA[:, None])

        # ---- ARM A ONLY: back to equal weight, at the CLOSE ---------------
        if t in rebal_rows:
            tot = VA.sum(1) + cashA
            nh = held.sum(1)
            good = (nh > 0) & (tot > 0)
            if good.any():
                target = np.where(held, (tot / np.maximum(nh, 1))[:, None], 0.0)
                turn = 0.5 * (np.abs(target - VA).sum(1) + cashA) / np.maximum(tot, 1e-300)
                scale = 1.0 - turn * cost
                VA = np.where(good[:, None], target * scale[:, None], VA)
                cashA = np.where(good, 0.0, cashA)
                turnA += np.where(good, turn, 0.0)

        if keep_paths:
            pathA[k] = (VA.sum(1) + cashA) / np.maximum(prevA, 1e-300) - 1.0
            pathB[k] = (VB.sum(1) + cashB) / np.maximum(prevB, 1e-300) - 1.0

    endA = VA.sum(1) + cashA
    endB = VB.sum(1) + cashB
    gA_log = np.log(np.maximum(endA, 1e-300))
    gB_log = np.log(np.maximum(endB, 1e-300))
    gW_log = np.log(np.maximum(U, 1e-300)).mean(1)      # equal weights at t0
    out = {"gA": gA_log, "gB": gB_log, "gW": gW_log, "days": T,
           "turnA": turnA, "turnB": turnB, "deaths": int((~held).sum())}
    if keep_paths:
        out["pathA"] = pathA
        out["pathB"] = pathB
    return out


_GAMMA_MEMO: dict = {}


def predicted_gamma(P: Panel, t0: int, cols: np.ndarray) -> np.ndarray:
    """Annualised Fernholz gamma* for each basket from the TRAILING 252-session
    covariance matrix ending at the CLOSE of t0 (inclusive; no future data).
    w = 1/n. Rank-deficiency is irrelevant here: gamma* needs only the average
    own-variance and the portfolio variance, both well-estimated at 252 obs."""
    key = (t0, cols.shape, hash(cols.tobytes()))
    hit = _GAMMA_MEMO.get(key)
    if hit is not None:
        return hit
    K, n = cols.shape
    win = P.ret[t0 - WARMUP + 1:t0 + 1]
    out = np.empty(K)
    w = np.full(n, 1.0 / n)
    for k in range(K):
        X = win[:, cols[k]]
        S = np.cov(X, rowvar=False) * TD_YEAR
        out[k] = growth.excess_growth_rate(w, S)
    _GAMMA_MEMO[key] = out
    return out


# ------------------------------------------------------- basket constructors

def basket_all(P: Panel, t0: int, rng) -> np.ndarray:
    el = P.eligible(t0)
    return el[None, :] if len(el) >= 20 else np.zeros((0, 0), int)


def basket_topdv(P: Panel, t0: int, rng, n: int) -> np.ndarray:
    el = P.eligible(t0)
    if len(el) < n:
        return np.zeros((0, 0), int)
    dv = np.median(P.dollar_vol[t0 - 60 + 1:t0 + 1, el], axis=0)
    order = np.argsort(-dv)[:n]
    return np.sort(el[order])[None, :]


def basket_rand(P: Panel, t0: int, rng, n: int, draws: int) -> np.ndarray:
    el = P.eligible(t0)
    if len(el) < n:
        return np.zeros((0, 0), int)
    return np.array([rng.choice(el, size=n, replace=False) for _ in range(draws)])


def basket_voltier(P: Panel, t0: int, rng, n: int, high: bool) -> np.ndarray:
    el = P.eligible(t0)
    if len(el) < n:
        return np.zeros((0, 0), int)
    sd = P.ret[t0 - WARMUP + 1:t0 + 1, el].std(0)
    order = np.argsort(-sd if high else sd)[:n]
    return np.sort(el[order])[None, :]


BASKETS = {
    "pit_all": lambda P, t, g: basket_all(P, t, g),
    "top50dv": lambda P, t, g: basket_topdv(P, t, g, 50),
    "top100dv": lambda P, t, g: basket_topdv(P, t, g, 100),
    "top200dv": lambda P, t, g: basket_topdv(P, t, g, 200),
    "rand30": lambda P, t, g: basket_rand(P, t, g, 30, RAND_DRAWS),
    "rand100": lambda P, t, g: basket_rand(P, t, g, 100, 10),
    "hivol30": lambda P, t, g: basket_voltier(P, t, g, 30, True),
    "lovol30": lambda P, t, g: basket_voltier(P, t, g, 30, False),
}


# --------------------------------------------------------------- experiments

def formation_rows(P: Panel, hold_months: int) -> list[int]:
    me = [int(x) for x in P.month_end if x >= WARMUP]
    return me[: max(0, len(me) - hold_months)]


def rebal_set(P: Panel, t0: int, t1: int, every_months: int) -> set[int]:
    """Arm A's rebalance calendar. every_months == 0 means DAILY (the theorem's
    continuous-rebalancing limit); < 0 means never (arm A collapses onto arm B).
    The final row t1 is excluded because the book is measured there, not traded.

    NOTE, AND IT IS THE MIS-SPECIFICATION THE EARLIER QUICK TEST SUFFERED: at a
    1-month hold with MONTHLY rebalancing this set is EMPTY, so arm A is
    literally arm B and the premium is identically zero. A drift-horizon axis
    only has content when arm A rebalances more often than arm B drifts."""
    if every_months == 0:
        return set(range(t0 + 1, t1))
    if every_months < 0:
        return set()
    inside = [int(x) for x in P.month_end if t0 < x <= t1]
    return set(inside[every_months - 1::every_months]) - {t1} if inside else set()


def experiment(P: Panel, basket: str, hold_months: int, rebal_months: int = 1,
               cost_bps: float = COST_BPS, cash_on_death: bool = False,
               keep_paths: bool = False, verbose: bool = False) -> dict:
    """One (basket x drift horizon x rebalance frequency x cost) cell."""
    rng = np.random.default_rng(SEED + 13 * hold_months + len(basket))
    rows = formation_rows(P, hold_months)
    per_date, recs, paths = [], [], []
    for t0 in rows:
        me_after = [int(x) for x in P.month_end if x > t0]
        if len(me_after) < hold_months:
            continue
        t1 = me_after[hold_months - 1]
        cols = BASKETS[basket](P, t0, rng)
        if cols.size == 0:
            continue
        rb = rebal_set(P, t0, t1, rebal_months)
        res = run_formation(P, t0, t1, cols, rb, cost_bps,
                            cash_on_death=cash_on_death, keep_paths=keep_paths)
        d = res["days"]
        prem = ann_from_log(res["gA"] - res["gB"], d)
        gam_r = ann_from_log(res["gA"] - res["gW"], d)
        jen = ann_from_log(res["gB"] - res["gW"], d)
        gam_p = predicted_gamma(P, t0, cols)
        per_date.append(float(prem.mean()))
        for k in range(cols.shape[0]):
            recs.append({"t0": t0, "n": int(cols.shape[1]),
                         "prem": float(prem[k]), "gamma_real": float(gam_r[k]),
                         "jensen": float(jen[k]), "gamma_pred": float(gam_p[k]),
                         "turnA": float(res["turnA"][k] * TD_YEAR / d),
                         "turnB": float(res["turnB"][k] * TD_YEAR / d)})
        if keep_paths:
            paths.append((t0, t1, res["pathA"][:, 0], res["pathB"][:, 0]))
    if not recs:
        return {}
    df = pd.DataFrame(recs)
    x = np.array(per_date)
    bb = block_boot(x, block=hold_months)
    ht = halves_thirds(x)
    span_months = len(formation_rows(P, 1))
    out = {
        "basket": basket, "hold_months": hold_months,
        "rebal_months": rebal_months, "cost_bps": cost_bps,
        "n_baskets": int(len(df)), "n_formations": int(len(x)),
        "n_names_median": float(df["n"].median()),
        "eff_independent": round(span_months / max(hold_months, 1), 1),
        "premium_ann": round(float(df["prem"].mean()) * 100, 4),
        "premium_t": round(bb["t"], 3),
        "premium_se": round(bb["se"] * 100, 4),
        "premium_ci": [round(bb["lo"] * 100, 4), round(bb["hi"] * 100, 4)],
        "boot_block_months": bb["block"],
        "gamma_predicted_ann": round(float(df["gamma_pred"].mean()) * 100, 4),
        "gamma_realised_ann": round(float(df["gamma_real"].mean()) * 100, 4),
        "jensen_ann": round(float(df["jensen"].mean()) * 100, 4),
        "jensen_share_of_gamma": round(float(df["jensen"].mean() /
                                             max(df["gamma_pred"].mean(), 1e-9)), 4),
        "turnover_A_ann": round(float(df["turnA"].mean()), 4),
        "turnover_B_ann": round(float(df["turnB"].mean()), 4),
        "halves": [round(v * 100, 4) for v in ht["halves"]],
        "thirds": [round(v * 100, 4) for v in ht["thirds"]],
        "frac_formations_positive": round(float((x > 0).mean()), 4),
    }
    # break-even cost: the round-trip bps at which the premium is zero.
    gross = experiment_gross_cache.get((basket, hold_months, rebal_months, cash_on_death))
    if gross is None:
        out["breakeven_bps"] = None
    else:
        dturn = out["turnover_A_ann"] - out["turnover_B_ann"]
        out["breakeven_bps"] = round(gross / max(dturn, 1e-9) * 10_000, 2) if dturn > 0 else None
    if keep_paths:
        out["_paths"] = paths
    out["_df"] = df
    return out


experiment_gross_cache: dict = {}


# ------------------------------------------------------ the pooled daily book

def ladder(P: Panel, basket: str, hold_months: int, rebal_months: int,
           cost_bps: float) -> dict:
    """Rule 9 pooling: one sleeve per formation month, all running concurrently;
    the book's daily return is the mean of the live sleeves. Gives a genuine
    daily series for Rule 13 on the book AND on the A - B difference."""
    cell = experiment(P, basket, hold_months, rebal_months, cost_bps,
                      keep_paths=True)
    if not cell:
        return {}
    T = len(P.dates)
    accA = np.zeros(T)
    accB = np.zeros(T)
    cnt = np.zeros(T)
    for t0, t1, pa, pb in cell["_paths"]:
        sl = slice(t0 + 1, t1 + 1)
        accA[sl] += pa
        accB[sl] += pb
        cnt[sl] += 1
    live = cnt > 0
    rA = np.where(live, accA / np.maximum(cnt, 1), np.nan)
    rB = np.where(live, accB / np.maximum(cnt, 1), np.nan)
    idx = np.where(live)[0]
    spy = P.spy[idx]
    bil = P.bil[idx]
    a, b = rA[idx], rB[idx]
    diff = a - b
    out = {
        "basket": basket, "hold_months": hold_months,
        "rebal_months": rebal_months, "cost_bps": cost_bps,
        "days": int(len(idx)), "sleeves_max": int(cnt.max()),
        "A": {"cagr": round(cagr(a) * 100, 3), "vol": round(ann_vol(a) * 100, 3),
              "sharpe": round(sharpe_excess(a, bil), 4),
              "maxdd": round(max_dd(a) * 100, 2)},
        "B": {"cagr": round(cagr(b) * 100, 3), "vol": round(ann_vol(b) * 100, 3),
              "sharpe": round(sharpe_excess(b, bil), 4),
              "maxdd": round(max_dd(b) * 100, 2)},
        "SPY": {"cagr": round(cagr(spy) * 100, 3), "vol": round(ann_vol(spy) * 100, 3),
                "sharpe": round(sharpe_excess(spy, bil), 4),
                "maxdd": round(max_dd(spy) * 100, 2)},
        "rf_ann_pct": round(cagr(bil) * 100, 3),
    }
    out["A_vs_SPY"] = {k: round(v, 4) for k, v in
                       ols_alpha_beta(a - bil, spy - bil).items()}
    out["B_vs_SPY"] = {k: round(v, 4) for k, v in
                       ols_alpha_beta(b - bil, spy - bil).items()}
    out["AminusB_vs_SPY"] = {k: round(v, 4) for k, v in
                             ols_alpha_beta(diff, spy - bil).items()}
    h = len(diff) // 2
    th = len(diff) // 3
    out["diff_cagr_halves"] = [round((np.exp(np.log1p(diff[:h] + 1e-12).sum()
                                             * TD_YEAR / h) - 1) * 100, 4),
                               round((np.exp(np.log1p(diff[h:] + 1e-12).sum()
                                             * TD_YEAR / (len(diff) - h)) - 1) * 100, 4)]
    out["diff_mean_ann_halves"] = [round(float(diff[:h].mean()) * TD_YEAR * 100, 4),
                                   round(float(diff[h:].mean()) * TD_YEAR * 100, 4)]
    out["diff_mean_ann_thirds"] = [round(float(diff[i * th:(i + 1) * th].mean())
                                         * TD_YEAR * 100, 4) for i in range(3)]
    out["A_sharpe_minus_SPY"] = round(out["A"]["sharpe"] - out["SPY"]["sharpe"], 4)
    return out


# ------------------------------------------------------ the positive control

def synthetic(sigma: float, rho: float, n: int, months: int, paths: int,
              rebal_months: int = 1, seed: int = SEED,
              mu_disp: float = 0.0) -> dict:
    """POSITIVE CONTROL. iid lognormal returns with a KNOWN sigma and rho pushed
    through the SAME `run_formation` simulator as the real data.

    mu_disp > 0 gives the names genuinely different true growth rates (sd of
    the annual drift across names), which is the world in which buy-and-hold
    SHOULD win — the diagnostic for what real data is doing.
    """
    rng = np.random.default_rng(seed)
    days = int(round(months * TD_YEAR / 12))
    sd = sigma / math.sqrt(TD_YEAR)
    # one synthetic "panel" per path, laid out as paths x names columns
    S = paths * n
    zc = rng.standard_normal((days, paths))
    lr = rng.standard_normal((days, paths, n))
    lr *= math.sqrt(1.0 - rho)
    lr += math.sqrt(rho) * zc[:, :, None]
    lr *= sd
    lr -= 0.5 * sd * sd
    if mu_disp > 0:
        lr += (rng.standard_normal((paths, n)) * mu_disp / TD_YEAR)[None, :, :]
    np.exp(lr, out=lr)
    lr -= 1.0
    ret = lr.reshape(days, S)

    class Fake:
        pass
    F = Fake()
    F.ret = np.vstack([np.zeros((1, S)), ret])
    F.live = np.ones((days + 1, S), bool)
    F.bil = np.zeros(days + 1)
    cols = np.arange(S).reshape(paths, n)
    if rebal_months == 0:
        rb = set(range(1, days))                     # DAILY
    else:
        step = max(1, int(round(rebal_months * TD_YEAR / 12)))
        rb = set(range(step, days, step))
    res = run_formation(F, 0, days, cols, rb, cost_bps=0.0)
    gam_real = ann_from_log(res["gA"] - res["gW"], days)
    jens = ann_from_log(res["gB"] - res["gW"], days)
    prem = ann_from_log(res["gA"] - res["gB"], days)
    analytic = 0.5 * sigma * sigma * (1 - rho) * (1 - 1.0 / n)
    return {
        "sigma": sigma, "rho": rho, "n": n, "months": months, "paths": paths,
        "mu_disp": mu_disp, "rebal_months": rebal_months,
        "gamma_analytic_pct": round(analytic * 100, 4),
        "gamma_measured_pct": round(float(gam_real.mean()) * 100, 4),
        "gamma_recovery_ratio": round(float(gam_real.mean()) / analytic, 4),
        "gamma_se_pct": round(float(gam_real.std(ddof=1) / math.sqrt(paths)) * 100, 4),
        "jensen_pct": round(float(jens.mean()) * 100, 4),
        "jensen_share": round(float(jens.mean()) / analytic, 4),
        "premium_AminusB_pct": round(float(prem.mean()) * 100, 4),
        "premium_se_pct": round(float(prem.std(ddof=1) / math.sqrt(paths)) * 100, 4),
        "premium_t": round(float(prem.mean() / (prem.std(ddof=1) / math.sqrt(paths))), 2),
        "frac_paths_A_beats_B": round(float((prem > 0).mean()), 4),
    }


def run_synthetic_suite() -> dict:
    out = {"cells": [], "note": (
        "Same simulator as the real data. mu identical across names unless "
        "mu_disp>0. rebal_months=0 is DAILY rebalancing, the theorem's "
        "continuous limit and therefore the cell H38a is judged on.")}
    # (a) THE RECOVERY TEST — daily rebalancing, four (sigma, rho, n) corners
    for s, r, n, m, p in [(0.35, 0.30, 30, 12, 1200), (0.20, 0.10, 30, 12, 1200),
                          (0.50, 0.60, 30, 12, 1200), (0.35, 0.30, 100, 12, 400),
                          (0.25, 0.50, 100, 12, 400)]:
        _v(f"synthetic-daily s{s}_r{r}_n{n}_{m}m")
        out["cells"].append(synthetic(s, r, n, m, p, rebal_months=0))
    # (b) THE SCALING TEST — monthly rebalancing, drift horizon 1..120 months
    for s, r, n, m, p in [(0.35, 0.30, 30, 1, 1500), (0.35, 0.30, 30, 3, 1500),
                          (0.35, 0.30, 30, 12, 1200), (0.35, 0.30, 30, 60, 400),
                          (0.35, 0.30, 30, 120, 250),
                          (0.35, 0.30, 100, 12, 400), (0.35, 0.30, 100, 120, 80),
                          (0.35, 0.30, 500, 12, 40)]:
        _v(f"synthetic-monthly s{s}_r{r}_n{n}_{m}m")
        out["cells"].append(synthetic(s, r, n, m, p, rebal_months=1))
    # (c) THE DIAGNOSTIC — genuine cross-sectional dispersion of TRUE growth
    #     rates, i.e. the world in which buy-and-hold SHOULD win.
    for md in (0.0, 0.10, 0.20, 0.40):
        _v(f"synthetic mu_disp {md}")
        out["cells"].append(synthetic(0.35, 0.30, 30, 60, 400,
                                      rebal_months=1, mu_disp=md))
    return out


# ------------------------------------------------------ the gamma* sort test

def gamma_sort(df: pd.DataFrame, q: int = 5) -> dict:
    """H38e. Sort baskets by PREDICTED gamma* WITHIN each formation date (so the
    sort cannot pick up a time effect), then read the realised premium."""
    d = df.copy()
    d["q"] = d.groupby("t0")["gamma_pred"].transform(
        lambda s: pd.qcut(s.rank(method="first"), q, labels=False)
        if s.nunique() >= q else np.nan)
    d = d.dropna(subset=["q"])
    if d.empty:
        return {}
    rows = []
    for k in range(q):
        sub = d[d["q"] == k]
        rows.append({"q": k + 1,
                     "gamma_pred": round(float(sub["gamma_pred"].mean()) * 100, 4),
                     "gamma_real": round(float(sub["gamma_real"].mean()) * 100, 4),
                     "jensen": round(float(sub["jensen"].mean()) * 100, 4),
                     "premium": round(float(sub["prem"].mean()) * 100, 4),
                     "n": int(len(sub))})
    # date-clustered spread series
    piv = d.pivot_table(index="t0", columns="q", values="prem", aggfunc="mean")
    if q - 1 not in piv.columns or 0 not in piv.columns:
        return {"quintiles": rows}
    spread = (piv[q - 1] - piv[0]).dropna().to_numpy()
    bb = block_boot(spread, block=12)
    ht = halves_thirds(spread)
    # does predicted gamma* forecast REALISED gamma*? (the theorem's own test)
    m = np.isfinite(d["gamma_pred"]) & np.isfinite(d["gamma_real"])
    X = np.column_stack([np.ones(m.sum()), d.loc[m, "gamma_pred"].to_numpy()])
    coef, *_ = np.linalg.lstsq(X, d.loc[m, "gamma_real"].to_numpy(), rcond=None)
    yhat = X @ coef
    ss = float(((d.loc[m, "gamma_real"].to_numpy() - yhat) ** 2).sum())
    tot = float(((d.loc[m, "gamma_real"].to_numpy()
                  - d.loc[m, "gamma_real"].mean()) ** 2).sum())
    return {
        "quintiles": rows,
        "Q5_minus_Q1_premium_pct": round(bb["mean"] * 100, 4),
        "Q5_minus_Q1_t": round(bb["t"], 3),
        "Q5_minus_Q1_t_mc_sd": round(boot_t_mc_sd(spread, 12), 3),
        "Q5_minus_Q1_halves": [round(v * 100, 4) for v in ht["halves"]],
        "Q5_minus_Q1_thirds": [round(v * 100, 4) for v in ht["thirds"]],
        "realised_on_predicted_slope": round(float(coef[1]), 4),
        "realised_on_predicted_intercept_pct": round(float(coef[0]) * 100, 4),
        "realised_on_predicted_r2": round(1 - ss / tot, 4) if tot > 0 else None,
        "n_dates": int(len(spread)),
    }


# --------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true",
                    help="run only the positive control")
    ap.add_argument("--no-guard", action="store_true",
                    help="guards 2 and 3 off (sensitivity row)")
    ap.add_argument("--cash-on-death", action="store_true",
                    help="delisting proceeds to BIL instead of pro rata")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    t_start = time.time()
    R: dict = {"hypothesis": "H38", "run_utc": pd.Timestamp.utcnow().isoformat(),
               "span": [START, END], "cost_bps_headline": COST_BPS,
               "guards_2_3": not args.no_guard,
               "delisting_policy": "pro_rata_to_survivors" if not args.cash_on_death
               else "BIL_cash"}

    print("=" * 78)
    print("H38 — THE REBALANCING PREMIUM, ISOLATED")
    print("=" * 78)

    # ---------------------------------------------------- 1. positive control
    print("\n[1] POSITIVE CONTROL — synthetic iid lognormal, KNOWN sigma/rho")
    R["synthetic"] = run_synthetic_suite()
    print(f"{'sigma':>6}{'rho':>6}{'n':>5}{'mo':>5}{'reb':>5}{'muD':>6}"
          f"{'gamma*(an)':>12}{'gamma*(meas)':>14}{'ratio':>8}"
          f"{'Jensen':>9}{'A-B':>9}{'t':>7}{'P(A>B)':>8}")
    for c in R["synthetic"]["cells"]:
        print(f"{c['sigma']:>6.2f}{c['rho']:>6.2f}{c['n']:>5d}{c['months']:>5d}"
              f"{('day' if c['rebal_months'] == 0 else str(c['rebal_months']) + 'm'):>5}"
              f"{c['mu_disp']:>6.2f}{c['gamma_analytic_pct']:>12.3f}"
              f"{c['gamma_measured_pct']:>14.3f}{c['gamma_recovery_ratio']:>8.3f}"
              f"{c['jensen_pct']:>9.3f}{c['premium_AminusB_pct']:>9.3f}"
              f"{c['premium_t']:>7.1f}{c['frac_paths_A_beats_B']:>8.2f}")
    base = [c for c in R["synthetic"]["cells"]
            if c["rebal_months"] == 0 and c["months"] == 12 and c["n"] == 30
            and c["sigma"] == 0.35][0]
    R["synthetic_recovery_ratios_daily"] = [
        c["gamma_recovery_ratio"] for c in R["synthetic"]["cells"]
        if c["rebal_months"] == 0]
    R["H38a"] = {"pass": abs(base["gamma_recovery_ratio"] - 1) < 0.05,
                 "recovery_ratio": base["gamma_recovery_ratio"],
                 "analytic_pct": base["gamma_analytic_pct"],
                 "measured_pct": base["gamma_measured_pct"]}
    print(f"\n  H38a positive control: recovery ratio {base['gamma_recovery_ratio']:.4f} "
          f"-> {'PASS' if R['H38a']['pass'] else 'FAIL'}")
    if args.synthetic:
        RESULTS.write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")
        print(f"\nwrote {RESULTS}")
        return

    # ------------------------------------------------------------- 2. panel
    print("\n[2] PANEL — point-in-time S&P 500, guarded")
    P = Panel(guard=not args.no_guard)
    print("   ", json.dumps(P.diag))
    R["panel"] = P.diag

    holds = [1, 3, 12, 60] if not args.quick else [1, 12]
    baskets = (["pit_all", "top50dv", "top100dv", "top200dv",
                "rand30", "rand100", "hivol30", "lovol30"]
               if not args.quick else ["pit_all", "rand30"])

    # gross (zero-cost) cells first, so break-even costs can be solved
    print("\n[3] GROSS (0 bps) — arm A minus arm B by drift horizon")
    gross_tab = []
    for b in baskets:
        for h in holds:
            _v(f"gross {b} D{h}m reb1m 0bps")
            c = experiment(P, b, h, 1, 0.0, cash_on_death=args.cash_on_death)
            if not c:
                continue
            experiment_gross_cache[(b, h, 1, args.cash_on_death)] = c["premium_ann"] / 100.0
            c.pop("_df", None)
            gross_tab.append(c)
    R["gross_by_horizon"] = gross_tab

    # ------------------------------------------------- 4. the headline table
    print("\n[4] NET OF 5 bps ROUND TRIP — the headline")
    print(f"{'basket':>9}{'D(m)':>6}{'n':>5}{'gamma*p':>9}{'gamma*r':>9}"
          f"{'Jensen':>8}{'A-B':>8}{'t':>7}{'halves':>18}{'turnA':>7}{'BE bps':>8}")
    net_tab = []
    dfs: dict = {}
    for b in baskets:
        for h in holds:
            _v(f"net {b} D{h}m reb1m {COST_BPS}bps")
            c = experiment(P, b, h, 1, COST_BPS, cash_on_death=args.cash_on_death)
            if not c:
                continue
            dfs[(b, h)] = c.pop("_df")
            net_tab.append(c)
            hv = c["halves"]
            print(f"{b:>9}{h:>6}{c['n_names_median']:>5.0f}"
                  f"{c['gamma_predicted_ann']:>9.2f}{c['gamma_realised_ann']:>9.2f}"
                  f"{c['jensen_ann']:>8.2f}{c['premium_ann']:>8.2f}{c['premium_t']:>7.2f}"
                  f"{f'{hv[0]:+.2f}/{hv[1]:+.2f}':>18}"
                  f"{c['turnover_A_ann']:>7.2f}"
                  f"{(c['breakeven_bps'] if c['breakeven_bps'] is not None else float('nan')):>8.1f}")
    R["net_headline"] = net_tab

    # ---------------------------------------------- 5. full-horizon drift arm
    print("\n[5] FULL-HORIZON DRIFT — 12 monthly-offset formations in 2017, "
          "held to 2026-08-07")
    full = []
    for b in ["pit_all", "top100dv", "rand30"]:
        _v(f"full-horizon {b}")
        me = [int(x) for x in P.month_end if x >= WARMUP]
        starts = me[:12]
        t1 = len(P.dates) - 1
        prem, gam_r, gam_p, jen, yrs = [], [], [], [], []
        rng = np.random.default_rng(SEED)
        for t0 in starts:
            cols = BASKETS[b](P, t0, rng)
            if cols.size == 0:
                continue
            rb = rebal_set(P, t0, t1, 1)
            res = run_formation(P, t0, t1, cols, rb, COST_BPS,
                                cash_on_death=args.cash_on_death)
            d = res["days"]
            prem.append(float(ann_from_log(res["gA"] - res["gB"], d).mean()))
            gam_r.append(float(ann_from_log(res["gA"] - res["gW"], d).mean()))
            jen.append(float(ann_from_log(res["gB"] - res["gW"], d).mean()))
            gam_p.append(float(predicted_gamma(P, t0, cols).mean()))
            yrs.append(d / TD_YEAR)
        row = {"basket": b, "n_phases": len(prem),
               "years": round(float(np.mean(yrs)), 2),
               "premium_ann_pct": round(float(np.mean(prem)) * 100, 4),
               "premium_phase_sd_pct": round(float(np.std(prem, ddof=1)) * 100, 4),
               "premium_min_pct": round(float(np.min(prem)) * 100, 4),
               "premium_max_pct": round(float(np.max(prem)) * 100, 4),
               "gamma_pred_pct": round(float(np.mean(gam_p)) * 100, 4),
               "gamma_real_pct": round(float(np.mean(gam_r)) * 100, 4),
               "jensen_pct": round(float(np.mean(jen)) * 100, 4),
               "eff_independent": 1.0}
        full.append(row)
        print(f"   {b:>9}  {row['years']:.1f}y  A-B {row['premium_ann_pct']:+.3f}%"
              f"  (phase sd {row['premium_phase_sd_pct']:.3f}, "
              f"range {row['premium_min_pct']:+.3f}..{row['premium_max_pct']:+.3f})"
              f"  gamma*p {row['gamma_pred_pct']:.2f}  Jensen {row['jensen_pct']:.2f}")
    R["full_horizon"] = full

    # --------------------------------------------- 6. the scaling of A-B in D
    scal = {}
    for b in baskets:
        pts = [(c["hold_months"], c["premium_ann"]) for c in net_tab
               if c["basket"] == b]
        pts.sort()
        fh = [f for f in full if f["basket"] == b]
        if fh:
            pts.append((int(round(fh[0]["years"] * 12)), fh[0]["premium_ann_pct"]))
        vals = [v for _, v in pts]
        scal[b] = {"points": pts,
                   "monotone_increasing": all(vals[i] <= vals[i + 1] + 1e-9
                                              for i in range(len(vals) - 1)),
                   "rises_from_1m_to_longest": bool(vals[-1] > vals[0])}
    R["scaling_in_drift_horizon"] = scal
    R["H38d"] = {"monotone_any": any(v["monotone_increasing"] for v in scal.values()),
                 "rises_all": all(v["rises_from_1m_to_longest"] for v in scal.values())}

    # -------------------------------------------- 7. rebalance-frequency sweep
    print("\n[6] REBALANCE FREQUENCY (arm A), D = 60 months")
    freq = []
    for b in ["pit_all", "rand30"]:
        for rm in (1, 3, 12):
            _v(f"freq {b} D60m reb{rm}m {COST_BPS}bps")
            c = experiment(P, b, 60, rm, COST_BPS, cash_on_death=args.cash_on_death)
            if not c:
                continue
            c.pop("_df", None)
            freq.append(c)
            print(f"   {b:>9} reb {rm:>2}m  A-B {c['premium_ann']:+.3f}%  "
                  f"t {c['premium_t']:+.2f}  turnA {c['turnover_A_ann']:.2f}/yr  "
                  f"BE {c['breakeven_bps']}")
    R["rebalance_frequency"] = freq

    # ------------------------------------------------------ 8. cost ladder
    print("\n[7] COST LADDER (pit_all, D = 60m, monthly rebalance)")
    costs = []
    for cb in (0.0, 5.0, 10.0):
        _v(f"cost {cb}bps pit_all D60m")
        c = experiment(P, "pit_all", 60, 1, cb, cash_on_death=args.cash_on_death)
        c.pop("_df", None)
        costs.append({"cost_bps": cb, "premium_ann": c["premium_ann"],
                      "t": c["premium_t"], "turnover_A_ann": c["turnover_A_ann"],
                      "turnover_B_ann": c["turnover_B_ann"]})
        print(f"   {cb:>4.0f} bps -> A-B {c['premium_ann']:+.3f}%  t {c['premium_t']:+.2f}")
    R["cost_ladder"] = costs
    g = costs[0]["premium_ann"] / 100.0
    dturn = costs[0]["turnover_A_ann"] - costs[0]["turnover_B_ann"]
    R["breakeven_bps_pit_all_D60"] = round(g / max(dturn, 1e-9) * 10_000, 2)
    R["H38f"] = {"breakeven_bps": R["breakeven_bps_pit_all_D60"],
                 "pass": R["breakeven_bps_pit_all_D60"] > COST_BPS}

    # ------------------------------------------- 9. the falsifiable prediction
    print("\n[8] H38e — SORT BASKETS BY PREDICTED gamma* (within date)")
    sorts = {}
    for key in [("rand30", 12), ("rand30", 60)]:
        if key not in dfs:
            continue
        _v(f"gamma-sort {key[0]} D{key[1]}m")
        s = gamma_sort(dfs[key])
        sorts[f"{key[0]}_D{key[1]}m"] = s
        print(f"   {key[0]} D{key[1]}m: "
              f"slope(realised gamma* on predicted) {s.get('realised_on_predicted_slope')}"
              f"  R2 {s.get('realised_on_predicted_r2')}")
        for row in s.get("quintiles", []):
            print(f"      Q{row['q']}  gamma*pred {row['gamma_pred']:>6.2f}"
                  f"  gamma*real {row['gamma_real']:>6.2f}"
                  f"  Jensen {row['jensen']:>6.2f}  A-B {row['premium']:>+7.3f}"
                  f"  (n {row['n']})")
        print(f"      Q5-Q1 A-B {s.get('Q5_minus_Q1_premium_pct'):+.3f}%  "
              f"t {s.get('Q5_minus_Q1_t')}  (MC sd {s.get('Q5_minus_Q1_t_mc_sd')})  "
              f"halves {s.get('Q5_minus_Q1_halves')}")
    R["gamma_sort"] = sorts
    # pooled cross-basket sort (all baskets, D=12) — the wider gamma* range
    pool = pd.concat([dfs[k] for k in dfs if k[1] == 12], ignore_index=True) \
        if any(k[1] == 12 for k in dfs) else pd.DataFrame()
    if not pool.empty:
        _v("gamma-sort pooled-all-baskets D12m")
        R["gamma_sort"]["pooled_all_baskets_D12m"] = gamma_sort(pool)
    k = "rand30_D60m" if "rand30_D60m" in sorts else next(iter(sorts), None)
    if k:
        R["H38e"] = {"Q5_minus_Q1_pct": sorts[k]["Q5_minus_Q1_premium_pct"],
                     "t": sorts[k]["Q5_minus_Q1_t"],
                     "pass": sorts[k]["Q5_minus_Q1_premium_pct"] > 0
                     and sorts[k]["Q5_minus_Q1_t"] > 2}

    # ------------------------------------------ 10. Rule 13 on the daily books
    print("\n[9] RULE 13 — pooled daily ladder, book AND difference")
    lads = []
    for b in ["pit_all", "top50dv", "top100dv", "top200dv"]:
        _v(f"ladder {b} D12m reb1m {COST_BPS}bps")
        L = ladder(P, b, 12, 1, COST_BPS)
        if not L:
            continue
        lads.append(L)
        print(f"   {b:>9}  A: CAGR {L['A']['cagr']:>6.2f} vol {L['A']['vol']:>5.2f} "
              f"Sharpe {L['A']['sharpe']:.3f} beta {L['A_vs_SPY']['beta']:.2f} | "
              f"B: CAGR {L['B']['cagr']:>6.2f} Sharpe {L['B']['sharpe']:.3f} | "
              f"SPY: CAGR {L['SPY']['cagr']:.2f} Sharpe {L['SPY']['sharpe']:.3f}")
        print(f"              A-B diff: beta {L['AminusB_vs_SPY']['beta']:+.3f} "
              f"alpha {L['AminusB_vs_SPY']['alpha_ann'] * 100:+.3f}%/yr "
              f"t {L['AminusB_vs_SPY']['t_alpha']:+.2f} | "
              f"halves {L['diff_mean_ann_halves']} thirds {L['diff_mean_ann_thirds']}")
    R["ladders"] = lads
    if lads:
        L0 = [x for x in lads if x["basket"] == "pit_all"][0]
        R["H38g"] = {"beta_of_difference": L0["AminusB_vs_SPY"]["beta"],
                     "pass": abs(L0["AminusB_vs_SPY"]["beta"]) < 0.15}
        R["H38h"] = {"sharpe_A": L0["A"]["sharpe"], "sharpe_SPY": L0["SPY"]["sharpe"],
                     "pass": L0["A"]["sharpe"] > L0["SPY"]["sharpe"],
                     "note": "Rule 13: a higher CAGR at higher vol is not an edge."}

    # ------------------------------------------------- 11. decomposition (c/b)
    d12 = [c for c in net_tab if c["hold_months"] == 12]
    if d12:
        R["H38c"] = {
            "jensen_share_of_predicted_gamma_D12m": {
                c["basket"]: c["jensen_share_of_gamma"] for c in d12},
            "pass": float(np.mean([c["jensen_share_of_gamma"] for c in d12])) > 0.70,
        }
    slopes = [s.get("realised_on_predicted_slope") for s in sorts.values()
              if s.get("realised_on_predicted_slope") is not None]
    if slopes:
        R["H38b"] = {"slopes": slopes,
                     "pass": all(0.7 <= s <= 1.3 for s in slopes)}

    # ---------------------------------------------------------- 12. registry
    R["variants_tried"] = list(VARIANTS)
    R["n_variants"] = len(VARIANTS)
    R["registry_N"] = N_PRIOR + len(VARIANTS)
    if lads:
        L0 = [x for x in lads if x["basket"] == "pit_all"][0]
        n_obs = L0["days"]
        sr_d = L0["A"]["sharpe"] / math.sqrt(TD_YEAR)
        R["deflated_sharpe_armA_pit_all"] = round(
            growth.deflated_sharpe(sr_d, R["registry_N"], n_obs), 4)

    R["runtime_sec"] = round(time.time() - t_start, 1)
    RESULTS.write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")

    print("\n" + "=" * 78)
    print("PRE-REGISTERED CELLS")
    for k in ("H38a", "H38b", "H38c", "H38d", "H38e", "H38f", "H38g", "H38h"):
        if k in R:
            print(f"  {k}: {json.dumps(R[k], default=str)}")
    print(f"\nvariants run: {len(VARIANTS)}   registry N: {R['registry_N']}")
    print(f"wrote {RESULTS}   ({R['runtime_sec']} s)")


if __name__ == "__main__":
    main()
