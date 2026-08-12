"""H37 — THE ZERO-FORECAST GROWTH PORTFOLIO. Minimise variance, forecast nothing.

MECHANISM (one sentence, Rule 1)
--------------------------------
If mu is identical across stocks — which is exactly what six rounds of measured
IC ~ 0 in this repo instruct you to assume — then the growth rate of a
rebalanced long-only portfolio collapses to  g_p = mu - 0.5 * w' Sigma w,  so
growth is maximised by MINIMISING PORTFOLIO VARIANCE, and every basis point of
avoided variance is half a basis point of compounded return, earned without
forecasting anything.

WHY THIS IS A DIFFERENT KIND OF TEST
------------------------------------
Every previous round asked "which stocks will go up?" and measured IC ~ 0.
Grinold: IR = IC * sqrt(BR) * TC; with IC = 0 nothing downstream rescues it.
This lab's expected return contains NO return forecast anywhere. Starting from
Fernholz's decomposition of a rebalanced portfolio's growth,

    g_p = sum_i w_i g_i + gamma*,   gamma* = 0.5 * (sum_i w_i sigma_ii - w'Sigma w)

and substituting g_i = mu - sigma_ii/2, the two sum_i w_i sigma_ii terms cancel
exactly and g_p = mu - 0.5 * w'Sigma w. Sigma is estimable and persistent
(Round 3: volatility IS forecastable, 29/29 symbols, both halves); mu is not.
If a design here needed to predict a stock's direction it would be
mis-implemented.

THE POINT PREDICTION — this is what makes it a test and not a backtest
----------------------------------------------------------------------
On any two long-only fully-invested books over the SAME names, the realised
annualised log-growth difference decomposes EXACTLY (to third order) as

    Delta_g  =  Delta_mu  -  0.5 * Delta_sigma^2

with Delta_mu the difference in ARITHMETIC mean return. The theorem's entire
content is the claim  **Delta_mu = 0**.  So the test is:

    predicted advantage  =  0.5 * (sigma^2_bench - sigma^2_MV)   [from realised variances]
    realised advantage   =  g_MV - g_bench                        [measured]
    residual             =  Delta_mu                              [ = the mu violation ]

  * agree  -> the variance mechanism is doing the work, mu really is flat;
  * MV wins by MORE -> the excess is NOT the theorem, it is the LOW-VOLATILITY
    ANOMALY (a claim about mu) riding along, and this file says so in those words;
  * MV wins by LESS -> the equal-mu assumption is being violated AGAINST us.

Delta_mu carries a Newey-West t at lag 21 (the rebalance interval). That is the
falsifiable number.

THE CEILING WAS MEASURED BEFORE THE LAB WAS WRITTEN, so nothing here is a
rediscovery: annual covariance of the PIT S&P 500 over 2016-2026 gives decade
means of 33.0% single-stock vol, 0.276 pairwise correlation, 16.5% equal-weight
vol, 13.8% inverse-variance vol against SPY's 16.1%, i.e. an UNLEVERED theorem
edge of 0.5*(var_SPY - var_IV) = **+0.34 %/yr**, ranging -0.30 (2020) to +1.54
(2022). A third of a percent a year is real and is not a landslide. The
unlevered comparison is therefore treated here as a DIAGNOSTIC, and the round's
actual question is the levered one: a ~13-14% vol book against SPY's 17.5% is
only ~1.2-1.4x levered — cheap, inside Reg-T, no derivatives — so does the
vol-matched book beat SPY AFTER REAL FINANCING, and at what break-even spread?

PRE-REGISTRATION (fixed before the first backtest number existed)
------------------------------------------------------------------
| #    | hypothesis | pass condition |
|------|-----------|----------------|
| H37a | ENGINE. Out-of-sample realised vol ranks MV < IV < EW over 2016-2026 on the same names, same dates, same guards. | vol(MV) < vol(IV) < vol(EW) |
| H37b | THE THEOREM. The realised annualised log-growth advantage of MV over the equal-weight book equals 0.5*(var_EW - var_MV) within its own standard error, i.e. Delta_mu is statistically zero. | \|t(Delta_mu)\| < 2 |
| H37c | UNLEVERED vs SPY. MV's variance saving vs SPY is worth roughly the pre-measured +0.34 %/yr of log growth, and MV's CAGR does NOT beat SPY's, because SPY's realised mu was higher. | predicted advantage in [0, 1] %/yr |
| H37d | **THE ONE THAT MATTERS.** Vol-matched levered MV, financed at the REAL BIL yield plus a spread, beats SPY's CAGR at a plausible spread. | break-even spread > 100 bps |
| H37e | CONTROL. Random long-only weights on the same eligible pool, matched name count and matched turnover, do NOT reproduce MV's variance reduction. | vol(RAND) - vol(MV) > 2 pp |
| H37f | ATTRIBUTION. MV's alpha over SPY does not survive adding a long-only low-vol proxy (own bottom-100-vol book, and SPLV/USMV as external, tradeable, fee-inclusive instruments). If it DOES survive, the residual is unexplained; if it does not, the result is the low-vol anomaly and must be named as such. | reported either way |
| H37g | RULE 9. No conclusion depends on which day of the month capital rebalances. | across-phase sd small vs the effect |

Failure conditions stated in advance: H37a fails if the vol ordering breaks
(the optimiser would then be adding variance out of sample, which is the normal
fate of an unshrunk inverse covariance); H37b fails if \|t(Delta_mu)\| >= 2 in
EITHER direction, and a positive Delta_mu is a low-vol-anomaly finding, not a
theorem confirmation; **H37d fails — and the round's practical claim dies with
it — if the break-even financing spread is below what a retail margin account
actually pays.** Leverage scales an edge and cannot create one; ALPHA-STACK.md
learned that the expensive way and it is restated here so no reader mistakes
the levered book for a new source of return.

METHOD
------
UNIVERSE    POINT-IN-TIME S&P 500 (`scout/pit.py`), each date's ACTUAL members,
            delisted names included. 742 tickers were members at some point
            since 2016-01-01; ~450-490 clear the data filters on a given date.
            Survivorship inverted H23 and would invert this too: a low-variance
            optimiser run on TODAY's members is handed the ten-year survivors.
SIGMA       Trailing daily simple returns over a window ending at the close of
            day t, Ledoit-Wolf shrunk (`growth.ledoit_wolf_cov`, not
            reimplemented). PRIMARY WINDOW 252 sessions: one year is the
            shortest window that spans a full seasonal/earnings cycle for every
            name and still leaves T > N/2 for a ~480-name cross-section, which
            is where shrinkage stops being cosmetic. 126 is reported alongside.
            The shrinkage intensity delta is recorded at every rebalance.
BOOKS       All over 2016-01-04..2026-08-07, identical dates, identical
            universe, identical cost model:
              SPY   buy-and-hold, total-return-adjusted closes (the benchmark)
              EW    equal weight on the eligible PIT pool
              IV    inverse-variance, w_i ∝ 1/Sigma_ii (uncapped; the ceiling
                    memo's construction) plus a capped variant
              MV    long-only, fully invested, per-name cap — **PRIMARY CAP 2%**
              LOWVOL100  bottom-100 trailing-vol names, equal weight (control c)
            An uncapped min-variance solution concentrates into ~33 names at
            11% each; that is a different claim, so it is reported as a variant
            and never as the headline.
SOLVER      min 0.5 w'Sigma w over the CAPPED SIMPLEX {w>=0, w<=c, sum w = 1},
            by FISTA with adaptive restart and an exact bisection projection
            onto the capped simplex. Warm-started from the previous rebalance.
            `--selftest` checks it against brute-force grid search on 5-asset
            problems and checks that warm and cold starts agree to 1e-9.
REBALANCE   MONTHLY, at the last trading day of each month, executed AT THE
            CLOSE. Between rebalances weights DRIFT with prices (a real book
            does not trade daily) and the drifted weights are what the next
            turnover is measured against.
THE SHIFT   Weights at rebalance t are formed from returns through the close of
            day t inclusive, and earn returns from t+1 onward. There is exactly
            one place in this file where a weight meets a return —
            `_run_book`, `idx = arange(t+1, t_end+1)` — and nowhere else.
            `--selftest` proves it by permuting every return strictly after a
            date D and confirming the book's return series up to D is
            bit-identical.
COSTS       10 bps round trip charged on measured ONE-WAY turnover at each
            rebalance (`growth.turnover_cost`'s convention, identical to
            construction_lab so the numbers are comparable). 0/5/20 bps are the
            sensitivity rows and the break-even cost is solved numerically.
CASH        BIL, the real ETF, from the master cache. There is NO hardcoded
            risk-free rate anywhere in this file — every Sharpe is on returns
            in excess of BIL and every alpha is a Jensen alpha. H32's headline
            died of exactly this omission (+0.049 reported vs +0.006 honest).
LIQUIDATION When a held name's price goes missing or is retired mid-month, its
            position earns BIL until the next rebalance. Proceeds are NOT
            redistributed pro-rata across survivors, which would be a free
            reinvestment at the moment of a delisting.

PRICE-DATA GUARDS — all three documented defects, and this is which
--------------------------------------------------------------------
1. SPLIT REPAIR. Alpaca's corporate-actions feed is pulled for the full 742-name
   PIT union (own cache, `high52_lab._fetch_splits_retry` +
   `data_audit.check_splits`) and every split the bars endpoint failed to apply
   is back-adjusted. 5.1% of splits are unadjusted market-wide; AAPL 2020-08-31
   reads -74.2% raw and would be assigned a colossal variance, which for a
   min-variance optimiser is a SILENT filter, not a visible error.
2. EXTREME-PRINT MASK. After repair, any remaining |1-day return| > 45%
   (`high52_lab.BIG_MOVE`) is a spin-off or a reused ticker (146 market-wide).
   The return is set to zero for that name-day AND the name is made ineligible
   for the whole trailing window that the print corrupts — again because a
   corrupt variance does not error, it just moves a name to the bottom or top
   of the optimiser's ranking.
3. FROZEN QUOTES (`idiovol_lab.retire_stale`, first run of 10 identical closes).
   Unfiltered this manufactured +896 bps of fake drift in H26. It matters MORE
   here than anywhere else in the repo: a frozen quote has EXACTLY ZERO measured
   variance, so an unguarded min-variance optimiser would load the cap into
   every delisted name in the universe. **The guard is applied to STOCKS ONLY:
   BIL has a 53-session run of identical closes and retiring it would delete
   the cash leg.**
`--no-guard` reruns with 2 and 3 off; that is the sensitivity row.

CONTROLS (Rule 3) — all three, because each kills a different alternative
-------------------------------------------------------------------------
(a) RANDOM LONG-ONLY WEIGHTS from the same eligible pool, 20 seeds, in two
    flavours because no single draw can match both quantities at once:
      RAND_k   matched NAME COUNT (k = MV's own non-zero count each month),
               Dirichlet(1) weights projected onto the same capped simplex.
               Its turnover is far higher than MV's, so its cost drag is a
               conservative handicap and is reported.
      RAND_tm  matched TURNOVER **and** matched name count: an equal-weighted
               k-name book that replaces exactly m = round(turnover_MV * k)
               names per rebalance, so one-way turnover matches MV's by
               construction.
    If random weights capture most of the variance reduction, the optimiser is
    not the source.
(b) RULE 13 on the book AND on the difference (MV minus SPY): realised beta and
    market-adjusted alpha, Newey-West at lag 21 = the rebalance interval, with
    the OLS t printed beside it.
(c) LOW-VOL ATTRIBUTION. (r_MV - rf) = a + b1 (SPY - rf) + b2 (LOWVOL - SPY),
    HAC at lag 21, run against the lab's own bottom-100-vol book AND against
    SPLV and USMV — two REAL, TRADEABLE, FEE-INCLUSIVE long-only low-volatility
    ETFs held in the master cache. This is the same class of external check
    that made H31 the most convincing result in the repo (SPY vs RSP), and it
    is the only way to stop the low-vol anomaly masquerading as the theorem.
Both halves AND equal thirds for every headline. Rule 9 phase ladder (5 monthly
entry offsets) for the primary book.

WHAT THIS TEST CANNOT SETTLE
----------------------------
* It cannot separate "low variance" from "low beta" as a REASON for whatever mu
  difference shows up. It can only measure the mu difference and say whether it
  is zero. A non-zero Delta_mu is evidence about mu; attributing it to a
  specific risk story is beyond a ten-year single-market sample.
* Ten years is ONE realisation. The pre-measured annual spread runs from -0.30
  to +1.54 %/yr; a 0.3 %/yr mean over ten years has an enormous standard error
  and the honest statement is that the SIGN of the variance term is reliable
  (variance differences are measured with far more precision than means) while
  the magnitude in any decade is not.
* Financing is modelled as BIL + a constant spread. A real margin account
  reprices, can call, and charges tiered rates; the break-even spread is
  therefore an upper bound on the strategy's tolerance, not a quote.
* The universe is US large cap in a decade when US large-cap growth beat
  everything. The equal-mu premise is most wrong exactly here, and the lab
  reports the direction of that wrongness rather than assuming it away.
* Borrowing capacity, dividend withholding, hard-to-borrow and the tax
  treatment of a monthly-turnover book are all outside this file.

VERDICT
-------
Filled from the run, see `verdict` in scout/zeroforecast_results.json and the
one-line summary printed by `__main__`.
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import time

import numpy as np
import pandas as pd

from . import bars, config, data_audit, growth, pit
from .high52_lab import BIG_MOVE, _fetch_splits_retry
from .idiovol_lab import STALE_RUN, retire_stale
from .stack_lab import nw_mean_t, ols_alpha_beta

RESULTS = config.SCOUT_DIR / "zeroforecast_results.json"
PANEL_CACHE = config.SCOUT_DIR / "cache_zeroforecast_panel{g}.pkl"
SPLITS_CACHE = config.SCOUT_DIR / "cache_zeroforecast_splits.pkl"
WEIGHT_CACHE = config.SCOUT_DIR / "cache_zeroforecast_w_{tag}.pkl"

START, END = "2016-01-01", "2026-08-07"
TD_YEAR = 252
BENCH = "SPY"
CASH = "BIL"
EW_ETF = "RSP"
LOWVOL_ETFS = ("SPLV", "USMV")
ETFS = (BENCH, CASH, EW_ETF) + LOWVOL_ETFS

WINDOWS = (252, 126)
CAPS = (0.02, 0.01, 0.05, 1.0)
PRIMARY_WINDOW = 252
PRIMARY_CAP = 0.02
N_LOWVOL = 100                 # SPLV holds the 100 lowest-vol S&P 500 names
COST_BPS = 10.0                # round trip, charged on one-way turnover
COST_GRID = (0.0, 5.0, 10.0, 20.0)
NW_LAG = 21                    # = the monthly rebalance interval
SPREAD_GRID = (0.0, 0.0050, 0.0100, 0.0150)
MAX_LEV = 2.0                  # Reg-T initial margin on a long equity book
SEED = 20260810
N_RAND = 20
PHASES = 5                     # Rule 9: monthly entry offsets 0,4,8,12,16

# Registry N before this hypothesis. ~800 through Round 4; Round 5 added H31
# (53), H32, H33 (51), H34 (112), H35; overlay_lab records 950 at its start and
# stack_lab's own variants sit on top. 1,000 is the honest running count here.
N_RUNNING_PRIOR = 1000


# ==========================================================================
# 1. Panel: prices, the three guards, returns
# ==========================================================================

def _repair_splits(close: pd.DataFrame, stocks: list[str],
                   no_cache: bool = False) -> tuple[pd.DataFrame, list]:
    """GUARD 1. Back-adjust every split the bars endpoint failed to apply,
    using Alpaca's own corporate-actions feed as ground truth (the two disagree
    inside the same vendor -- scout/data_audit.py). Own cache because this
    universe is the 742-name PIT union, not high52_lab's."""
    if SPLITS_CACHE.exists() and not no_cache:
        with open(SPLITS_CACHE, "rb") as f:
            splits = pickle.load(f)
    else:
        print(f"  fetching corporate actions for {len(stocks)} PIT names...")
        splits = _fetch_splits_retry(stocks)
        with open(SPLITS_CACHE, "wb") as f:
            pickle.dump(splits, f)
    if splits is None or len(splits) == 0:
        return close, []
    checked = data_audit.check_splits(close[stocks], splits)
    bad = checked[checked["unadjusted"]].sort_values("ret_pct")
    out = close.copy()
    for _, row in bad.iterrows():
        sym, factor = row["symbol"], float(row["factor"])
        if sym not in out.columns or not np.isfinite(factor) or factor <= 0:
            continue
        ex = pd.Timestamp(row["ex_date"], tz=out.index.tz)
        out.loc[out.index < ex, sym] = out.loc[out.index < ex, sym] / factor
    return out, bad.to_dict("records")


def build_panel(guards: bool = True, quiet: bool = False) -> dict:
    """PIT S&P 500 union + the ETFs, guarded, as a returns panel.

    Guards 2 and 3 are applied to STOCK columns only. BIL has a 53-session run
    of identical closes -- retiring it would delete the cash leg -- and the
    ETFs never carry an unadjusted split in this cache."""
    path = PANEL_CACHE.with_name(PANEL_CACHE.name.format(g="" if guards else "_ng"))
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)

    stocks = pit.all_members_since(START)
    syms = sorted(set(stocks) | set(ETFS))
    b = bars.get(syms, START, END, verbose=not quiet)
    close = b["close"].copy()
    stocks = [s for s in stocks if s in close.columns]

    close, split_rows = _repair_splits(close, stocks)          # guard 1, always
    stale = []
    if guards:
        sub, stale = retire_stale(close[stocks], run=STALE_RUN)  # guard 3
        close[stocks] = sub

    ret = close.pct_change(fill_method=None)
    big = pd.DataFrame(False, index=ret.index, columns=ret.columns)
    if guards:
        big[stocks] = ret[stocks].abs() > BIG_MOVE               # guard 2
        ret = ret.mask(big, 0.0)

    if not quiet:
        print(f"  panel: {close.shape[0]} dates x {len(stocks)} PIT names + "
              f"{len(ETFS)} ETFs | splits repaired {len(split_rows)} | "
              f"stale retired {len(stale)} | extreme prints masked "
              f"{int(big.to_numpy().sum())}")

    out = {"close": close, "ret": ret, "big": big, "stocks": stocks,
           "split_rows": split_rows, "stale": stale}
    with open(path, "wb") as f:
        pickle.dump(out, f)
    return out


# ==========================================================================
# 2. The solver: long-only capped minimum variance
# ==========================================================================

def proj_capped_simplex(v: np.ndarray, cap: float) -> np.ndarray:
    """Exact Euclidean projection onto {w >= 0, w <= cap, sum w = 1}.

    w(theta) = clip(v - theta, 0, cap) is monotone non-increasing in theta, so
    a bisection on theta hits sum(w) = 1 to machine precision. Bracketed by
    theta = min(v) - cap (all entries at the cap, sum = n*cap >= 1) and
    theta = max(v) (sum = 0)."""
    n = v.size
    if cap * n < 1.0 - 1e-12:
        raise ValueError(f"cap {cap} infeasible for {n} assets")
    lo, hi = float(v.min()) - cap - 1.0, float(v.max())
    for _ in range(80):
        th = 0.5 * (lo + hi)
        if np.clip(v - th, 0.0, cap).sum() > 1.0:
            lo = th
        else:
            hi = th
    w = np.clip(v - 0.5 * (lo + hi), 0.0, cap)
    s = w.sum()
    return w / s if s > 0 else np.full(n, 1.0 / n)


def _power_lipschitz(S: np.ndarray, iters: int = 100) -> float:
    v = np.ones(S.shape[0])
    v /= np.linalg.norm(v)
    for _ in range(iters):
        v = S @ v
        nv = np.linalg.norm(v)
        if nv <= 0:
            return 1e-12
        v /= nv
    return float(v @ (S @ v))


def min_variance(S: np.ndarray, cap: float = 1.0, w0: np.ndarray | None = None,
                 iters: int = 3000, tol: float = 1e-13) -> np.ndarray:
    """argmin w'Sw on the capped simplex, by FISTA with adaptive restart.

    Sigma is PSD after Ledoit-Wolf, so this is a convex QP on a set with a
    closed-form projection; restarted FISTA reaches machine precision on the
    objective in ~2,000 iterations at N ~ 650 (0.3-1.1 s). No scipy in this
    environment, and an unrestarted FISTA does NOT converge here -- the
    condition number of a shrunk equity covariance is ~10^4."""
    n = S.shape[0]
    L = _power_lipschitz(S)
    if not np.isfinite(L) or L <= 0:
        return np.full(n, 1.0 / n)
    w = proj_capped_simplex(np.full(n, 1.0 / n) if w0 is None else np.asarray(w0, float), cap)
    y, tk = w.copy(), 1.0
    for _ in range(iters):
        wn = proj_capped_simplex(y - (S @ y) / L, cap)
        if float((y - wn) @ (wn - w)) > 0:      # adaptive restart
            tk = 1.0
        tn = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * tk * tk))
        y = wn + ((tk - 1.0) / tn) * (wn - w)
        step = float(np.abs(wn - w).sum())
        w, tk = wn, tn
        if step < tol:
            break
    return w


def _cap_normalise(x: np.ndarray, cap: float) -> np.ndarray:
    """Positive weights proportional to x, then iteratively clipped at `cap`
    with the excess redistributed over the uncapped names."""
    w = np.clip(np.asarray(x, float), 0.0, None)
    s = w.sum()
    w = w / s if s > 0 else np.full(w.size, 1.0 / w.size)
    if cap >= 1.0:
        return w
    for _ in range(200):
        over = w > cap + 1e-15
        if not over.any():
            break
        excess = float((w[over] - cap).sum())
        w[over] = cap
        free = ~over & (w > 0)
        if not free.any():
            w[:] = 1.0 / w.size
            break
        w[free] += excess * w[free] / w[free].sum()
    return w / w.sum()


# ==========================================================================
# 3. Eligibility and weights
# ==========================================================================

def rebalance_dates(index: pd.DatetimeIndex, warmup: int,
                    offset: int = 0, monthly: bool = True) -> list[int]:
    """Positional indices of rebalance days. Monthly = last trading day of each
    calendar month; `offset` shifts every date forward by that many sessions
    (Rule 9's entry-phase ladder)."""
    n = len(index)
    if monthly:
        per = pd.Series(np.arange(n), index=index).groupby(
            [index.year, index.month]).max().to_numpy()
    else:
        per = np.arange(0, n, NW_LAG)
    per = per + offset
    return [int(t) for t in per if warmup <= t < n - 1]


def eligible_mask(t: int, window: int, ret_np: np.ndarray, close_np: np.ndarray,
                  big_np: np.ndarray, member_np: np.ndarray) -> np.ndarray:
    """Names tradeable at the close of day t, using data through t ONLY.

    Requires: PIT membership as of t; a finite close at t; a COMPLETE window of
    finite trailing returns (so Ledoit-Wolf sees a balanced panel and no name
    smuggles in a short, artificially low-variance history); and no masked
    extreme print anywhere inside that window."""
    sl = slice(t - window + 1, t + 1)
    ok = member_np[t] & np.isfinite(close_np[t])
    ok &= np.isfinite(ret_np[sl]).all(axis=0)
    ok &= ~big_np[sl].any(axis=0)
    return ok


def build_weights(panel: dict, window: int, caps=CAPS, offset: int = 0,
                  quiet: bool = False) -> dict:
    """All weight schemes at every rebalance date, for one covariance window.

    ONE covariance per rebalance date, shared by every scheme, so the schemes
    differ only in what they do with the SAME Sigma."""
    ret, close, big = panel["ret"], panel["close"], panel["big"]
    cols = list(ret.columns)
    idx = ret.index
    ret_np = ret.to_numpy(float)
    close_np = close.to_numpy(float)
    big_np = big.to_numpy(bool)
    n_sym = len(cols)

    stock_set = set(panel["stocks"])
    member_np = np.zeros((len(idx), n_sym), bool)
    col_pos = {c: j for j, c in enumerate(cols)}
    for i, d in enumerate(idx):
        for s in pit.members(d):
            j = col_pos.get(s)
            if j is not None and s in stock_set:
                member_np[i, j] = True

    ts = rebalance_dates(idx, warmup=window + 5, offset=offset)
    names = ["EW", "IV", "IVC"] + [f"MV{int(c * 10000):05d}" for c in caps] + ["LOWVOL"]
    W = {k: {} for k in names}
    diag_log, delta_log, k_log = [], [], []
    warm: dict[float, np.ndarray] = {}
    t0 = time.time()

    for c, t in enumerate(ts):
        ok = eligible_mask(t, window, ret_np, close_np, big_np, member_np)
        k = int(ok.sum())
        if k < 50:
            continue
        X = ret_np[t - window + 1:t + 1, ok]
        S, delta = growth.ledoit_wolf_cov(X)
        d = np.diag(S).copy()
        d[d <= 0] = np.nanmedian(d[d > 0]) if (d > 0).any() else 1e-8

        def place(w_small):
            w = np.zeros(n_sym)
            w[ok] = w_small
            return w

        W["EW"][t] = place(np.full(k, 1.0 / k))
        W["IV"][t] = place(_cap_normalise(1.0 / d, 1.0))
        W["IVC"][t] = place(_cap_normalise(1.0 / d, PRIMARY_CAP))
        lv = np.zeros(k)
        low = np.argsort(d)[:min(N_LOWVOL, k)]
        lv[low] = 1.0 / len(low)
        W["LOWVOL"][t] = place(lv)
        for cap in caps:
            key = f"MV{int(cap * 10000):05d}"
            w0 = warm.get(cap)
            if w0 is not None and w0.size != k:
                w0 = None
            w = min_variance(S, cap=cap, w0=w0)
            warm[cap] = w
            W[key][t] = place(w)

        diag_log.append(float(np.sqrt(TD_YEAR * d.mean())))
        delta_log.append(float(delta))
        k_log.append(k)
        if not quiet and (c % 25 == 0 or c == len(ts) - 1):
            print(f"    {idx[t].date()}  eligible {k}  delta {delta:.3f}  "
                  f"[{c + 1}/{len(ts)}]  {time.time() - t0:.0f}s")

    meta = {"window": window, "offset": offset, "n_rebal": len(k_log),
            "mean_eligible": round(float(np.mean(k_log)), 1),
            "mean_lw_delta": round(float(np.mean(delta_log)), 4),
            "mean_avg_stock_vol_pct": round(100 * float(np.mean(diag_log)), 2),
            "seconds": round(time.time() - t0, 1)}
    return {"W": W, "meta": meta, "cols": cols, "dates": ts}


# ==========================================================================
# 4. The backtest engine
# ==========================================================================

def _fill_returns(panel: dict) -> np.ndarray:
    """Return matrix with every missing name-day replaced by that day's BIL
    return: a position whose quote disappears (delisting, halt, frozen quote
    retirement) is LIQUIDATED INTO CASH and stays there until the next
    rebalance. Redistributing it across survivors would be a free reinvestment
    granted at exactly the moment a holding fails."""
    ret = panel["ret"]
    R = ret.to_numpy(float).copy()
    bil = ret[CASH].to_numpy(float)
    bil = np.nan_to_num(bil, nan=0.0)
    miss = ~np.isfinite(R)
    R[miss] = np.broadcast_to(bil[:, None], R.shape)[miss]
    return R


def _run_book(wmap: dict, R: np.ndarray, n_days: int,
              cost_bps: float) -> dict:
    """Daily returns of a book that rebalances to `wmap[t]` at the CLOSE of t.

    THE SHIFT LIVES HERE AND ONLY HERE: weights set at t earn returns over
    `idx = arange(t + 1, t_end + 1)`. Day t's own return was earned by the
    previous weights; the rebalance cost is charged to day t, the day the trade
    prints."""
    ts = sorted(wmap)
    port = np.full(n_days, np.nan)
    cost = np.zeros(n_days)
    turn, drift = [], np.zeros(R.shape[1])
    for k, t in enumerate(ts):
        w = wmap[t]
        one_way = 0.5 * float(np.abs(w - drift).sum())
        turn.append(one_way)
        cost[t] += one_way * cost_bps / 10_000.0
        t_end = ts[k + 1] if k + 1 < len(ts) else n_days - 1
        if t_end <= t:
            drift = w
            continue
        idx = np.arange(t + 1, t_end + 1)
        G = np.cumprod(1.0 + R[idx], axis=0)
        P = G @ w
        prev = np.concatenate([[1.0], P[:-1]])
        port[idx] = P / prev - 1.0
        drift = w * G[-1] / max(P[-1], 1e-12)
    return {"gross": port, "cost": cost, "net": port - cost,
            "turnover": np.array(turn), "first": ts[0] + 1, "last": n_days - 1}


def book_series(wmap: dict, R: np.ndarray, index: pd.DatetimeIndex,
                cost_bps: float = COST_BPS) -> tuple[pd.Series, dict]:
    out = _run_book(wmap, R, len(index), cost_bps)
    s = pd.Series(out["net"], index=index).iloc[out["first"]:out["last"] + 1]
    return s.dropna(), out


# ==========================================================================
# 5. Statistics — every risk number in EXCESS of BIL (H32's lesson)
# ==========================================================================

def _cagr(r: pd.Series) -> float:
    r = r.dropna()
    if not len(r):
        return float("nan")
    return float(np.expm1(np.log1p(r).sum() * TD_YEAR / len(r)))


def _maxdd(r: pd.Series) -> float:
    eq = (1 + r.dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


def metrics(r: pd.Series, rf: pd.Series, bench: pd.Series, label: str = "",
            lag: int = NW_LAG) -> dict:
    r = r.dropna()
    rf_a = rf.reindex(r.index).fillna(0.0)
    bm = bench.reindex(r.index)
    ex = (r - rf_a).dropna()
    ab = ols_alpha_beta(ex.to_numpy(), (bm - rf_a).reindex(ex.index).to_numpy(), lag=lag)
    ab0 = ols_alpha_beta(ex.to_numpy(), (bm - rf_a).reindex(ex.index).to_numpy(), lag=0)
    vol = float(r.std(ddof=1)) * math.sqrt(TD_YEAR)
    return {
        "label": label, "n": int(len(r)),
        "cagr_pct": round(100 * _cagr(r), 2),
        "arith_mu_pct": round(100 * float(r.mean()) * TD_YEAR, 3),
        "log_growth_pct": round(100 * float(np.log1p(r).mean()) * TD_YEAR, 3),
        "vol_pct": round(100 * vol, 2),
        "sharpe": round(float(ex.mean()) / float(ex.std(ddof=1)) * math.sqrt(TD_YEAR), 3)
        if float(ex.std(ddof=1)) > 0 else float("nan"),
        "max_dd_pct": round(100 * _maxdd(r), 2),
        "beta": ab["beta"], "alpha_ann_pct": ab["alpha_ann_pct"],
        "t_alpha_nw": ab["t_alpha"], "t_alpha_ols": ab0["t_alpha"],
    }


def diff_report(a: pd.Series, b: pd.Series, rf: pd.Series, bench: pd.Series,
                label: str, lag: int = NW_LAG) -> dict:
    """Rule 13 on a DIFFERENCE of books: the difference is itself a portfolio,
    so it gets a beta and a market-adjusted alpha like everything else."""
    idx = a.dropna().index.intersection(b.dropna().index)
    d = (a.reindex(idx) - b.reindex(idx)).dropna()
    bm = (bench.reindex(d.index) - rf.reindex(d.index).fillna(0.0))
    ab = ols_alpha_beta(d.to_numpy(), bm.to_numpy(), lag=lag)
    ab0 = ols_alpha_beta(d.to_numpy(), bm.to_numpy(), lag=0)
    mu, se, t = nw_mean_t(d.to_numpy(), lag=lag)
    return {"label": label, "n": int(len(d)),
            "ann_diff_pp": round(100 * mu * TD_YEAR, 3),
            "t_diff_nw": round(float(t), 2),
            "beta_of_diff": ab["beta"], "alpha_ann_pct": ab["alpha_ann_pct"],
            "t_alpha_nw": ab["t_alpha"], "t_alpha_ols": ab0["t_alpha"],
            "halves": _splits(d, 2), "thirds": _splits(d, 3)}


def _splits(d: pd.Series, k: int, lag: int = NW_LAG) -> list[dict]:
    d = d.dropna()
    n = len(d)
    edges = [int(round(i * n / k)) for i in range(k + 1)]
    out = []
    for i in range(k):
        seg = d.iloc[edges[i]:edges[i + 1]]
        mu, se, t = nw_mean_t(seg.to_numpy(), lag=lag)
        out.append({"span": f"{seg.index[0].date()}..{seg.index[-1].date()}",
                    "ann_pp": round(100 * mu * TD_YEAR, 2), "t": round(float(t), 2)})
    return out


def theorem_test(mv: pd.Series, bench: pd.Series, label: str,
                 lag: int = NW_LAG) -> dict:
    """THE POINT PREDICTION.

        Delta_g = Delta_mu - 0.5 * Delta_sigma^2  (+ third order)

    The theorem asserts Delta_mu = 0, so the PREDICTED log-growth advantage is
    0.5 * (var_bench - var_MV) computed from REALISED variances, and the
    residual of the realised advantage against it IS Delta_mu -- the amount by
    which the equal-mu assumption failed, signed, with a Newey-West t."""
    idx = mv.dropna().index.intersection(bench.dropna().index)
    a, b = mv.reindex(idx), bench.reindex(idx)
    va = float(a.var(ddof=1)) * TD_YEAR
    vb = float(b.var(ddof=1)) * TD_YEAR
    ga = float(np.log1p(a).mean()) * TD_YEAR
    gb = float(np.log1p(b).mean()) * TD_YEAR
    dmu_series = (a - b)
    mu, se, t = nw_mean_t(dmu_series.to_numpy(), lag=lag)
    predicted = 0.5 * (vb - va)
    realised = ga - gb
    return {"label": label, "n": int(len(idx)),
            "vol_mv_pct": round(100 * math.sqrt(va), 2),
            "vol_bench_pct": round(100 * math.sqrt(vb), 2),
            "predicted_advantage_pct_yr": round(100 * predicted, 3),
            "realised_advantage_pct_yr": round(100 * realised, 3),
            "residual_delta_mu_pct_yr": round(100 * (realised - predicted), 3),
            "delta_mu_measured_pct_yr": round(100 * mu * TD_YEAR, 3),
            "t_delta_mu_nw": round(float(t), 2),
            "third_order_gap_pct_yr": round(100 * ((realised - predicted) - mu * TD_YEAR), 4),
            "halves": _splits(dmu_series, 2), "thirds": _splits(dmu_series, 3)}


# ==========================================================================
# 6. Leverage: turning a lower variance into more return, honestly
# ==========================================================================

def lever(r: pd.Series, rf: pd.Series, L, spread: float) -> pd.Series:
    """L * r  -  (L - 1) * (BIL + spread). L may be a scalar or a daily Series.
    Financing is charged on the BORROWED fraction only, at the REAL bill yield
    plus `spread`. Leverage scales an edge; it cannot create one."""
    Lv = pd.Series(L, index=r.index) if np.isscalar(L) else L.reindex(r.index)
    rf_a = rf.reindex(r.index).fillna(0.0)
    return Lv * r - (Lv - 1.0) * (rf_a + spread / TD_YEAR)


def breakeven_spread(r: pd.Series, rf: pd.Series, L, target_cagr: float) -> float:
    """Spread (annual, decimal) at which the levered book's CAGR equals
    `target_cagr`. Monotone decreasing in the spread, so bisection is exact."""
    lo, hi = -0.05, 1.00
    if _cagr(lever(r, rf, L, lo)) < target_cagr:
        return float("nan")
    if _cagr(lever(r, rf, L, hi)) > target_cagr:
        return float("inf")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _cagr(lever(r, rf, L, mid)) > target_cagr:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def rolling_leverage(r: pd.Series, bench: pd.Series, ts_dates: pd.DatetimeIndex,
                     window: int = TD_YEAR, cap: float = MAX_LEV) -> pd.Series:
    """OUT-OF-SAMPLE vol matching. L is reset only at rebalance dates, from the
    trailing `window` realised vols of the book and of SPY THROUGH the close of
    that day, then held constant until the next rebalance. Nothing here uses a
    full-period statistic, unlike the in-sample scalar which is flagged as such."""
    vb = bench.rolling(window).std(ddof=1)
    vr = r.rolling(window).std(ddof=1)
    raw = (vb / vr).clip(upper=cap).replace([np.inf, -np.inf], np.nan)
    L = pd.Series(np.nan, index=r.index)
    for d in ts_dates:
        if d in raw.index and np.isfinite(raw.loc[d]):
            L.loc[d] = raw.loc[d]
    L = L.ffill()
    return L.fillna(1.0)


# ==========================================================================
# 7. Controls
# ==========================================================================

def random_books(panel: dict, wb: dict, mv_key: str, R: np.ndarray,
                 index: pd.DatetimeIndex, cap: float, n_draws: int = N_RAND,
                 seed: int = SEED) -> dict:
    """CONTROL (a). Random long-only weights on the SAME eligible pool.

    RAND_k  : matched NAME COUNT, Dirichlet(1) weights projected onto the same
              capped simplex. Turnover is ~1.0 per rebalance (far above MV's),
              so its cost drag handicaps it; that is reported, not hidden.
    RAND_tm : matched TURNOVER *and* name count. An equal-weighted k-name book
              that swaps exactly m = round(turnover_MV * k) names per month has
              one-way turnover m/k = turnover_MV by construction."""
    ew_map = wb["W"]["EW"]
    mv_map = wb["W"][mv_key]
    ts = sorted(mv_map)
    n_sym = R.shape[1]
    # MV's own per-rebalance turnover, needed as the matching target
    mv_out = _run_book(mv_map, R, len(index), COST_BPS)
    mv_turn = mv_out["turnover"]

    res = {"RAND_k": [], "RAND_tm": []}
    for s in range(n_draws):
        rng = np.random.default_rng(seed + 1013 * s)
        wk, wtm = {}, {}
        held = None
        for i, t in enumerate(ts):
            pool = np.flatnonzero(ew_map[t] > 0)
            k = int((mv_map[t] > 1e-9).sum())
            k = max(2, min(k, pool.size))
            pick = rng.choice(pool, size=k, replace=False)
            w = np.zeros(n_sym)
            w[pick] = proj_capped_simplex(rng.dirichlet(np.ones(k)), cap)
            wk[t] = w
            if held is None:
                held = set(rng.choice(pool, size=k, replace=False).tolist())
            else:
                m = int(round(float(mv_turn[i]) * k))
                m = max(0, min(m, k))
                cur = np.array(sorted(held))
                cur = cur[np.isin(cur, pool)]
                out_n = rng.choice(cur, size=min(m, cur.size), replace=False) if m and cur.size else np.array([], int)
                keep = [x for x in cur if x not in set(out_n.tolist())]
                avail = np.setdiff1d(pool, np.array(keep, int), assume_unique=False)
                need = k - len(keep)
                add = rng.choice(avail, size=min(need, avail.size), replace=False) if need > 0 else np.array([], int)
                held = set(keep) | set(add.tolist())
            hh = np.array(sorted(held), int)
            w2 = np.zeros(n_sym)
            w2[hh] = 1.0 / len(hh)
            wtm[t] = w2
        for name, wm in (("RAND_k", wk), ("RAND_tm", wtm)):
            sr, out = book_series(wm, R, index)
            res[name].append((sr, float(out["turnover"].mean())))
    return res


# ==========================================================================
# 8. Selftests
# ==========================================================================

def selftest() -> dict:
    rng = np.random.default_rng(3)
    print("SELFTEST 1 — solver vs brute force on 5-asset problems")
    worst = 0.0
    for trial in range(6):
        A = rng.standard_normal((40, 5))
        S = np.cov(A, rowvar=False)
        cap = [1.0, 0.5, 0.35][trial % 3]
        w = min_variance(S, cap=cap)
        # brute force: fine grid over the 4-simplex, capped
        g = 25
        best, bw = np.inf, None
        for a in range(g + 1):
            for b in range(g + 1 - a):
                for c in range(g + 1 - a - b):
                    for d in range(g + 1 - a - b - c):
                        e = g - a - b - c - d
                        v = np.array([a, b, c, d, e], float) / g
                        if v.max() > cap + 1e-12:
                            continue
                        q = float(v @ S @ v)
                        if q < best:
                            best, bw = q, v
        got = float(w @ S @ w)
        gap = (got - best) / max(abs(best), 1e-18)
        worst = max(worst, gap)
        print(f"  trial {trial} cap {cap:.2f}: solver {got:.8e} grid {best:.8e} "
              f"rel gap {gap:+.2e} (solver must be <= grid)")
    assert worst < 1e-6, "solver lost to a coarse grid"

    print("SELFTEST 2 — capped-simplex projection")
    for _ in range(200):
        n = int(rng.integers(3, 300))
        cap = float(max(1.0 / n, rng.uniform(1.0 / n, 1.0)))
        v = rng.standard_normal(n)
        w = proj_capped_simplex(v, cap)
        assert abs(w.sum() - 1) < 1e-9 and w.min() >= -1e-12 and w.max() <= cap + 1e-9
    print("  200 random projections: sum=1, 0<=w<=cap, all pass")

    print("SELFTEST 3 — warm vs cold start")
    A = rng.standard_normal((300, 120)) * 0.02
    S, _ = growth.ledoit_wolf_cov(A)
    wc = min_variance(S, cap=0.05)
    ww = min_variance(S, cap=0.05, w0=np.full(120, 1 / 120) * 0.5 + wc * 0.5)
    print(f"  max |warm - cold| = {np.abs(ww - wc).max():.3e}")
    assert np.abs(ww - wc).max() < 1e-6
    return {"solver_worst_rel_gap": float(worst), "passed": True}


def lookahead_test(panel: dict, window: int = PRIMARY_WINDOW) -> dict:
    """PROOF OF NO LOOKAHEAD. Permute every return STRICTLY AFTER a date D and
    recompute the weights: every weight at every rebalance <= D must be
    bit-identical, because nothing in the weight construction may read past t."""
    ret = panel["ret"]
    cut = len(ret) // 2
    D = ret.index[cut]
    p2 = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in panel.items()}
    rng = np.random.default_rng(99)
    r2 = ret.copy()
    tail = r2.iloc[cut + 1:].to_numpy()
    rng.shuffle(tail)                        # permute rows after D
    r2.iloc[cut + 1:] = tail
    p2["ret"] = r2
    c2 = panel["close"].copy()
    c2.iloc[cut + 1:] = c2.iloc[cut + 1:].to_numpy()[rng.permutation(len(c2) - cut - 1)]
    p2["close"] = c2

    a = build_weights(panel, window, caps=(PRIMARY_CAP,), quiet=True)
    b = build_weights(p2, window, caps=(PRIMARY_CAP,), quiet=True)
    key = f"MV{int(PRIMARY_CAP * 10000):05d}"
    checked, worst = 0, 0.0
    for t in sorted(a["W"][key]):
        if t > cut:
            continue
        worst = max(worst, float(np.abs(a["W"][key][t] - b["W"][key][t]).max()))
        checked += 1
    print(f"SELFTEST 4 — lookahead: {checked} rebalances at or before "
          f"{D.date()} recomputed on a future-permuted panel; "
          f"max weight difference {worst:.3e}")
    assert worst == 0.0, "weights depend on future returns"
    return {"rebalances_checked": checked, "max_weight_diff": worst,
            "cut_date": str(D.date())}


# ==========================================================================
# 9. The experiment
# ==========================================================================

def run(quiet: bool = False, guards: bool = True, do_phases: bool = True) -> dict:
    t_start = time.time()
    panel = build_panel(guards=guards, quiet=quiet)
    ret, index = panel["ret"], panel["ret"].index
    R = _fill_returns(panel)
    rf = ret[CASH].fillna(0.0)
    spy = ret[BENCH]
    variants = []

    out = {"span": [str(index[0].date()), str(index[-1].date())],
           "n_dates": int(len(index)), "n_pit_names": len(panel["stocks"]),
           "guards": {"splits_repaired": len(panel["split_rows"]),
                      "stale_retired": len(panel["stale"]),
                      "extreme_prints_masked": int(panel["big"].to_numpy().sum()),
                      "guards_on": guards,
                      "note": "stale/extreme guards applied to STOCKS only; "
                              "BIL has a 53-session identical-close run"},
           "cost_bps_round_trip": COST_BPS, "nw_lag": NW_LAG}

    # ---------------------------------------------------------------- books
    books: dict[str, pd.Series] = {}
    turnovers: dict[str, float] = {}
    wbs: dict[int, dict] = {}
    for window in WINDOWS:
        if not quiet:
            print(f"\n=== covariance window {window} sessions ===")
        wb = build_weights(panel, window, caps=CAPS, quiet=quiet)
        wbs[window] = wb
        out[f"cov_meta_w{window}"] = wb["meta"]
        for key, wm in wb["W"].items():
            name = f"{key}_w{window}"
            s, o = book_series(wm, R, index)
            books[name] = s
            turnovers[name] = float(o["turnover"].mean())
            variants.append(name)

    first = min(s.index[0] for s in books.values())
    common = index[(index >= first)]
    for k in list(books):
        books[k] = books[k].reindex(common).dropna()
    common = books[f"EW_w{PRIMARY_WINDOW}"].index
    spy_b = spy.reindex(common).dropna()
    common = spy_b.index
    for k in list(books):
        books[k] = books[k].reindex(common)
    books["SPY"] = spy_b
    books[EW_ETF] = ret[EW_ETF].reindex(common)
    for e in LOWVOL_ETFS:
        books[e] = ret[e].reindex(common)
    rf = rf.reindex(common)

    MV = f"MV{int(PRIMARY_CAP * 10000):05d}_w{PRIMARY_WINDOW}"
    out["primary_book"] = MV
    out["mean_one_way_turnover_per_rebal"] = {k: round(v, 4) for k, v in turnovers.items()}

    # ------------------------------------------------------- headline table
    order = ["SPY", EW_ETF] + list(LOWVOL_ETFS) + [
        f"{k}_w{w}" for w in WINDOWS
        for k in ["EW", "IV", "IVC", "LOWVOL"] + [f"MV{int(c * 10000):05d}" for c in CAPS]]
    out["books"] = [metrics(books[k], rf, books["SPY"], k) for k in order if k in books]

    # ------------------------------------------------- H37a: the vol ordering
    m = {b["label"]: b for b in out["books"]}
    out["H37a_vol_ordering"] = {
        "vol_MV_pct": m[MV]["vol_pct"],
        "vol_IV_pct": m[f"IV_w{PRIMARY_WINDOW}"]["vol_pct"],
        "vol_EW_pct": m[f"EW_w{PRIMARY_WINDOW}"]["vol_pct"],
        "vol_SPY_pct": m["SPY"]["vol_pct"],
        "pass": (m[MV]["vol_pct"] < m[f"IV_w{PRIMARY_WINDOW}"]["vol_pct"]
                 < m[f"EW_w{PRIMARY_WINDOW}"]["vol_pct"])}

    # ------------------------------------------- H37b/c: the point prediction
    out["theorem"] = {
        "vs_EW": theorem_test(books[MV], books[f"EW_w{PRIMARY_WINDOW}"], "MV - EW"),
        "vs_SPY": theorem_test(books[MV], books["SPY"], "MV - SPY"),
        "IV_vs_EW": theorem_test(books[f"IV_w{PRIMARY_WINDOW}"],
                                 books[f"EW_w{PRIMARY_WINDOW}"], "IV - EW"),
        "IV_vs_SPY": theorem_test(books[f"IV_w{PRIMARY_WINDOW}"], books["SPY"], "IV - SPY"),
        "MV126_vs_SPY": theorem_test(books[f"MV{int(PRIMARY_CAP * 10000):05d}_w126"],
                                     books["SPY"], "MV(126) - SPY"),
    }

    # ------------------------------------------------------ Rule 13 (b)
    out["differences"] = [
        diff_report(books[MV], books["SPY"], rf, books["SPY"], "MV - SPY"),
        diff_report(books[MV], books[f"EW_w{PRIMARY_WINDOW}"], rf, books["SPY"], "MV - EW"),
        diff_report(books[MV], books[f"IV_w{PRIMARY_WINDOW}"], rf, books["SPY"], "MV - IV"),
        diff_report(books[f"IV_w{PRIMARY_WINDOW}"], books["SPY"], rf, books["SPY"], "IV - SPY"),
        diff_report(books[f"EW_w{PRIMARY_WINDOW}"], books["SPY"], rf, books["SPY"], "EW - SPY"),
        diff_report(books[MV], books["SPLV"], rf, books["SPY"], "MV - SPLV"),
        diff_report(books[MV], books["USMV"], rf, books["SPY"], "MV - USMV"),
    ]

    # ------------------------------------------------------ engine validation
    out["engine_validation"] = {
        "EW_book_vs_RSP": {
            "corr": round(float(books[f"EW_w{PRIMARY_WINDOW}"].corr(books[EW_ETF])), 4),
            "tracking_error_pct_yr": round(
                100 * float((books[f"EW_w{PRIMARY_WINDOW}"] - books[EW_ETF]).std(ddof=1))
                * math.sqrt(TD_YEAR), 2),
            "cagr_book": round(100 * _cagr(books[f"EW_w{PRIMARY_WINDOW}"]), 2),
            "cagr_RSP": round(100 * _cagr(books[EW_ETF]), 2)},
        "MV_book_vs_USMV": {
            "corr": round(float(books[MV].corr(books["USMV"])), 4),
            "tracking_error_pct_yr": round(
                100 * float((books[MV] - books["USMV"]).std(ddof=1)) * math.sqrt(TD_YEAR), 2)},
        "MV_book_vs_SPLV": {
            "corr": round(float(books[MV].corr(books["SPLV"])), 4),
            "tracking_error_pct_yr": round(
                100 * float((books[MV] - books["SPLV"]).std(ddof=1)) * math.sqrt(TD_YEAR), 2)},
    }

    # ------------------------------------------------------ LEVERAGE (H37d)
    mv = books[MV]
    spy_r = books["SPY"]
    L_full = float(spy_r.std(ddof=1) / mv.std(ddof=1))
    ts_dates = common[np.isin(common, index[wbs[PRIMARY_WINDOW]["dates"]])]
    L_roll = rolling_leverage(mv, spy_r, ts_dates)
    spy_cagr = _cagr(spy_r)
    lev = {"target": "SPY full-period realised vol",
           "L_full_period_in_sample": round(L_full, 4),
           "L_rolling_mean": round(float(L_roll.mean()), 4),
           "L_rolling_max": round(float(L_roll.max()), 4),
           "L_rolling_min": round(float(L_roll.min()), 4),
           "reg_t_cap": MAX_LEV,
           "spy_cagr_pct": round(100 * spy_cagr, 3), "grid": [], "grid_rolling": []}
    for sp in SPREAD_GRID:
        for tag, Lx, dest in (("fixed", L_full, lev["grid"]),
                              ("rolling", L_roll, lev["grid_rolling"])):
            lr = lever(mv, rf, Lx, sp)
            mm = metrics(lr, rf, spy_r, f"MVlev_{tag}_{int(sp * 10000)}bp")
            mm["spread_bps"] = int(sp * 10000)
            dest.append(mm)
    lev["breakeven_spread_bps_fixed"] = round(
        10000 * breakeven_spread(mv, rf, L_full, spy_cagr), 1)
    lev["breakeven_spread_bps_rolling"] = round(
        10000 * breakeven_spread(mv, rf, L_roll, spy_cagr), 1)
    lev["diff_vs_spy_at_0bp_fixed"] = diff_report(
        lever(mv, rf, L_full, 0.0), spy_r, rf, spy_r, "MVlev(0bp) - SPY")
    lev["diff_vs_spy_at_100bp_fixed"] = diff_report(
        lever(mv, rf, L_full, 0.01), spy_r, rf, spy_r, "MVlev(100bp) - SPY")
    lev["diff_vs_spy_at_0bp_rolling"] = diff_report(
        lever(mv, rf, L_roll, 0.0), spy_r, rf, spy_r, "MVlev_roll(0bp) - SPY")
    lev["note"] = ("L_full_period uses the WHOLE sample's realised vol and is "
                   "therefore an in-sample scaling constant; the rolling "
                   "version resets L only at rebalance dates from trailing "
                   "252-day vols through that close and is the honest number. "
                   "Leverage scales an edge and cannot create one.")
    out["leverage"] = lev
    variants += [f"lev_{t}_{int(s * 10000)}bp" for s in SPREAD_GRID for t in ("fixed", "rolling")]

    # ------------------------------------------------------ CONTROL (a)
    if not quiet:
        print("\n=== control (a): random long-only weights, 20 draws ===")
    rb = random_books(panel, wbs[PRIMARY_WINDOW], f"MV{int(PRIMARY_CAP * 10000):05d}",
                      R, index, PRIMARY_CAP)
    ctrl = {}
    for name, lst in rb.items():
        vols, cagrs, alphas, turns = [], [], [], []
        for s, tv in lst:
            s = s.reindex(common).dropna()
            mm = metrics(s, rf, spy_r, name)
            vols.append(mm["vol_pct"]); cagrs.append(mm["cagr_pct"])
            alphas.append(mm["alpha_ann_pct"]); turns.append(tv)
        ctrl[name] = {"n_draws": len(lst),
                      "vol_pct_mean": round(float(np.mean(vols)), 2),
                      "vol_pct_sd": round(float(np.std(vols, ddof=1)), 2),
                      "vol_pct_min": round(float(np.min(vols)), 2),
                      "cagr_pct_mean": round(float(np.mean(cagrs)), 2),
                      "cagr_pct_sd": round(float(np.std(cagrs, ddof=1)), 2),
                      "alpha_ann_pct_mean": round(float(np.mean(alphas)), 2),
                      "mean_one_way_turnover": round(float(np.mean(turns)), 4)}
    ctrl["MV_vol_pct"] = m[MV]["vol_pct"]
    ctrl["MV_mean_one_way_turnover"] = round(turnovers[MV], 4)
    ctrl["H37e_pass"] = bool(ctrl["RAND_tm"]["vol_pct_mean"] - m[MV]["vol_pct"] > 2.0)
    out["control_random"] = ctrl
    variants += [f"rand_{k}_{i}" for k in ("k", "tm") for i in range(N_RAND)]

    # ------------------------------------------------------ CONTROL (c)
    def attribute(y: pd.Series, tilt: pd.Series, tag: str) -> dict:
        i2 = y.dropna().index.intersection(tilt.dropna().index)
        yy = (y.reindex(i2) - rf.reindex(i2)).to_numpy()
        x1 = (spy_r.reindex(i2) - rf.reindex(i2)).to_numpy()
        x2 = (tilt.reindex(i2) - spy_r.reindex(i2)).to_numpy()
        X = np.column_stack([np.ones(len(yy)), x1, x2])
        b, *_ = np.linalg.lstsq(X, yy, rcond=None)
        e = yy - X @ b
        XtX = np.linalg.inv(X.T @ X)
        u = X * e[:, None]
        S = u.T @ u
        for L in range(1, NW_LAG + 1):
            G = u[L:].T @ u[:-L]
            S += (1 - L / (NW_LAG + 1)) * (G + G.T)
        se = np.sqrt(np.diag(XtX @ S @ XtX))
        return {"factor": tag, "n": len(yy),
                "alpha_ann_pct": round(100 * float(b[0]) * TD_YEAR, 3),
                "t_alpha_nw": round(float(b[0] / se[0]), 2),
                "beta_mkt": round(float(b[1]), 3),
                "beta_lowvol_tilt": round(float(b[2]), 3),
                "t_beta_lowvol": round(float(b[2] / se[2]), 2)}

    out["control_lowvol_attribution"] = {
        "single_factor_alpha": {"alpha_ann_pct": m[MV]["alpha_ann_pct"],
                                "t_alpha_nw": m[MV]["t_alpha_nw"],
                                "beta": m[MV]["beta"]},
        "two_factor": [attribute(books[MV], books[f"LOWVOL_w{PRIMARY_WINDOW}"], "own LOWVOL100"),
                       attribute(books[MV], books["SPLV"], "SPLV (real ETF)"),
                       attribute(books[MV], books["USMV"], "USMV (real ETF)")],
        "levered_two_factor": [
            attribute(lever(mv, rf, L_full, 0.0), books["SPLV"], "SPLV, levered MV 0bp"),
            attribute(lever(mv, rf, L_roll, 0.0), books["SPLV"], "SPLV, rolling-levered MV 0bp")],
    }

    # ------------------------------------------------------ costs / break-even
    cg = []
    for cb in COST_GRID:
        s, _ = book_series(wbs[PRIMARY_WINDOW]["W"][f"MV{int(PRIMARY_CAP * 10000):05d}"],
                           R, index, cost_bps=cb)
        s = s.reindex(common).dropna()
        d = diff_report(s, spy_r, rf, spy_r, f"MV - SPY @ {cb}bp")
        cg.append({"cost_bps": cb, "cagr_pct": round(100 * _cagr(s), 2),
                   "vol_pct": round(100 * float(s.std(ddof=1)) * math.sqrt(TD_YEAR), 2),
                   "ann_diff_pp_vs_spy": d["ann_diff_pp"], "t": d["t_diff_nw"]})
    tpr = turnovers[MV] * 12.0
    gross_edge = out["theorem"]["vs_SPY"]["realised_advantage_pct_yr"] / 100.0 + \
        COST_BPS / 10000.0 * tpr
    out["costs"] = {"grid": cg, "one_way_turnover_per_year": round(tpr, 3),
                    "breakeven_cost_bps_unlevered_vs_spy": round(
                        10000 * gross_edge / tpr, 1) if tpr > 0 else None,
                    "note": "break-even cost is the one-way bps at which the "
                            "UNLEVERED log-growth advantage over SPY is exactly "
                            "consumed by turnover"}
    variants += [f"cost_{c}" for c in COST_GRID]

    # ------------------------------------------------------ Rule 9 phases
    if do_phases:
        if not quiet:
            print("\n=== Rule 9: monthly entry-phase ladder ===")
        ph = []
        for off in range(0, PHASES * 4, 4):
            wbp = build_weights(panel, PRIMARY_WINDOW, caps=(PRIMARY_CAP,),
                                offset=off, quiet=True)
            s, _ = book_series(wbp["W"][f"MV{int(PRIMARY_CAP * 10000):05d}"], R, index)
            s = s.reindex(common).dropna()
            d = diff_report(s, spy_r, rf, spy_r, f"phase+{off}")
            ph.append({"offset_sessions": off, "cagr_pct": round(100 * _cagr(s), 2),
                       "vol_pct": round(100 * float(s.std(ddof=1)) * math.sqrt(TD_YEAR), 2),
                       "ann_diff_pp_vs_spy": d["ann_diff_pp"], "t": d["t_diff_nw"]})
            variants.append(f"phase_{off}")
        out["rule9_phases"] = {
            "phases": ph,
            "sd_of_ann_diff_pp": round(float(np.std([p["ann_diff_pp_vs_spy"] for p in ph], ddof=1)), 3),
            "sd_of_vol_pct": round(float(np.std([p["vol_pct"] for p in ph], ddof=1)), 3)}

    # ------------------------------------------------------ deflated Sharpe
    exm = (books[MV] - rf).dropna()
    exs = (spy_r - rf).reindex(exm.index)
    dsr_in = (exm - exs).dropna()
    sr_d = float(dsr_in.mean() / dsr_in.std(ddof=1))
    out["deflated_sharpe"] = {
        "series": "MV minus SPY, daily excess",
        "sharpe_ann": round(sr_d * math.sqrt(TD_YEAR), 3),
        "n_trials_running": N_RUNNING_PRIOR + len(variants),
        "n_obs": int(len(dsr_in)),
        "dsr": round(growth.deflated_sharpe(
            sr_d, N_RUNNING_PRIOR + len(variants), len(dsr_in),
            skew=float(pd.Series(dsr_in).skew()),
            kurtosis=float(pd.Series(dsr_in).kurt() + 3.0)), 4)}

    out["variants_tried"] = variants
    out["n_variants_this_lab"] = len(variants)
    out["seconds"] = round(time.time() - t_start, 1)
    return out


def verdict(res: dict) -> dict:
    th = res["theorem"]["vs_SPY"]
    the = res["theorem"]["vs_EW"]
    lv = res["leverage"]
    mv = [b for b in res["books"] if b["label"] == res["primary_book"]][0]
    spy = [b for b in res["books"] if b["label"] == "SPY"][0]
    dmu = the["delta_mu_measured_pct_yr"]
    t = the["t_delta_mu_nw"]
    if abs(t) < 2:
        mech = ("Delta_mu is statistically zero: the equal-mu premise holds and "
                "the whole advantage is the variance term, i.e. the theorem.")
    elif dmu > 0:
        mech = ("Delta_mu is POSITIVE and significant: min-variance wins by MORE "
                "than the variance difference predicts, and the excess is NOT the "
                "theorem — it is the LOW-VOLATILITY ANOMALY (a claim about mu) "
                "riding along.")
    else:
        mech = ("Delta_mu is NEGATIVE and significant: the theorem's assumption "
                "that mu is equal across stocks is being violated AGAINST us — "
                "low-variance names earned a lower arithmetic mean.")
    return {
        "one_line": (f"Unlevered min-variance ({mv['vol_pct']}% vol vs SPY's "
                     f"{spy['vol_pct']}%) earns a variance-term advantage of "
                     f"{th['predicted_advantage_pct_yr']:+.2f}%/yr and a realised "
                     f"log-growth difference of {th['realised_advantage_pct_yr']:+.2f}%/yr "
                     f"vs SPY; vol-matched at {lv['L_full_period_in_sample']:.2f}x the "
                     f"break-even financing spread is "
                     f"{lv['breakeven_spread_bps_fixed']} bps (fixed L) / "
                     f"{lv['breakeven_spread_bps_rolling']} bps (rolling L)."),
        "mechanism_call": mech,
        "H37a_vol_ordering": res["H37a_vol_ordering"]["pass"],
        "H37b_delta_mu_zero_vs_EW": bool(abs(t) < 2),
        "H37c_predicted_advantage_in_0_1_pct": bool(
            0.0 <= th["predicted_advantage_pct_yr"] <= 1.0),
        "H37d_breakeven_above_100bp": bool(
            np.isfinite(lv["breakeven_spread_bps_rolling"])
            and lv["breakeven_spread_bps_rolling"] > 100),
        "H37e_random_control": res["control_random"]["H37e_pass"],
        "regime": {"unlevered_theorem_test": "CONFIRMATORY — pre-registered point "
                                             "prediction, 2 windows x 4 caps, t~2 acceptable",
                   "levered_vs_SPY": "EXPLORATORY — leverage target chosen by the "
                                     "researcher; needs t>3 and a deflated Sharpe "
                                     f"at N={res['deflated_sharpe']['n_trials_running']}"},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-guard", action="store_true")
    ap.add_argument("--no-phases", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        st = selftest()
        panel = build_panel(guards=True, quiet=a.quiet)
        st["lookahead"] = lookahead_test(panel)
        print("\nSELFTESTS PASSED")
        print(json.dumps(st, indent=2, default=str))
        return

    res = run(quiet=a.quiet, guards=not a.no_guard, do_phases=not a.no_phases)
    res["verdict"] = verdict(res)
    path = RESULTS if not a.no_guard else RESULTS.with_name("zeroforecast_results_noguard.json")
    with open(path, "w") as f:
        json.dump(res, f, indent=2, default=str)

    print("\n" + "=" * 78)
    print("H37 — ZERO-FORECAST GROWTH PORTFOLIO")
    print("=" * 78)
    print(f"span {res['span'][0]}..{res['span'][1]}  {res['n_dates']} dates  "
          f"{res['n_pit_names']} PIT names  guards {res['guards']}")
    print(f"\n{'book':<18}{'CAGR%':>8}{'vol%':>8}{'Sharpe':>9}{'beta':>7}"
          f"{'alpha%':>9}{'t_NW':>7}{'maxDD%':>9}")
    for b in res["books"]:
        print(f"{b['label']:<18}{b['cagr_pct']:>8.2f}{b['vol_pct']:>8.2f}"
              f"{b['sharpe']:>9.3f}{b['beta']:>7.2f}{b['alpha_ann_pct']:>9.2f}"
              f"{b['t_alpha_nw']:>7.2f}{b['max_dd_pct']:>9.2f}")
    print("\nTHE POINT PREDICTION (0.5*(var_bench - var_MV) vs realised log-growth gap)")
    print(f"{'pair':<16}{'pred%/yr':>10}{'real%/yr':>10}{'d_mu%/yr':>10}{'t(d_mu)':>9}")
    for k, v in res["theorem"].items():
        print(f"{v['label']:<16}{v['predicted_advantage_pct_yr']:>10.3f}"
              f"{v['realised_advantage_pct_yr']:>10.3f}"
              f"{v['delta_mu_measured_pct_yr']:>10.3f}{v['t_delta_mu_nw']:>9.2f}")
    print("\nRULE 13 — differences")
    for d in res["differences"]:
        print(f"  {d['label']:<14} {d['ann_diff_pp']:>7.2f}pp  t {d['t_diff_nw']:>5.2f}  "
              f"beta {d['beta_of_diff']:>6.3f}  alpha {d['alpha_ann_pct']:>6.2f}%  "
              f"t {d['t_alpha_nw']:>5.2f}  halves "
              f"{[h['ann_pp'] for h in d['halves']]}  thirds "
              f"{[h['ann_pp'] for h in d['thirds']]}")
    lv = res["leverage"]
    print(f"\nLEVERAGE — target {lv['target']}; L_fixed {lv['L_full_period_in_sample']}, "
          f"L_rolling mean {lv['L_rolling_mean']} (max {lv['L_rolling_max']})")
    print(f"{'spread':<10}{'fixed CAGR%':>13}{'rolling CAGR%':>15}   SPY "
          f"{lv['spy_cagr_pct']:.2f}%")
    for gf, gr in zip(lv["grid"], lv["grid_rolling"]):
        print(f"{gf['spread_bps']:>4} bp   {gf['cagr_pct']:>13.2f}{gr['cagr_pct']:>15.2f}")
    print(f"BREAK-EVEN SPREAD: fixed {lv['breakeven_spread_bps_fixed']} bps, "
          f"rolling {lv['breakeven_spread_bps_rolling']} bps")
    print("\nCONTROL (a) random long-only weights")
    print(json.dumps(res["control_random"], indent=2))
    print("\nCONTROL (c) low-vol attribution")
    print(json.dumps(res["control_lowvol_attribution"], indent=2))
    if "rule9_phases" in res:
        print("\nRULE 9 phases:", json.dumps(res["rule9_phases"]))
    print("\nCOSTS:", json.dumps(res["costs"]["grid"]),
          "\nbreak-even one-way bps:", res["costs"]["breakeven_cost_bps_unlevered_vs_spy"])
    print("\nDEFLATED SHARPE:", json.dumps(res["deflated_sharpe"]))
    print(f"\nvariants this lab: {res['n_variants_this_lab']}")
    print("\nVERDICT:", json.dumps(res["verdict"], indent=2))
    print(f"\nwrote {path}  ({res['seconds']}s)")


if __name__ == "__main__":
    main()
