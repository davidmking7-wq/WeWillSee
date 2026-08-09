"""H34 - the Partnership structure: a cap-weighted CORE plus an uncorrelated
SLEEVE, levered by the drawdown-constrained Kelly fraction.

MECHANISM (one sentence, before any number)
-------------------------------------------
Log growth is g = mu - sigma^2/2, maximised at L* = mu/sigma^2 where
g* = S^2/2, so growth is QUADRATIC in Sharpe and Sharpe is bought by adding a
weakly-correlated sleeve (S_p = w'S / sqrt(w'Cw)) rather than by forecasting
better - therefore a cap-weighted core plus a genuinely uncorrelated sleeve,
levered to an explicit drawdown budget, is the only construction this repo's
own mathematics permits to beat SPY by a wide margin.

THIS IS AN ALLOCATION STUDY, NOT A NEW SIGNAL.
Nothing here is searched for. Every ingredient is a component this repo already
measured, and each one's provenance is named so a reader can check that no
un-measured hope was smuggled in.

WHAT THE BRIEF ASKED FOR, AND WHAT WAS ACTUALLY AVAILABLE
--------------------------------------------------------
  1. CORE = SPY, unless a sibling lab (H31) produces an equity book that beats
     SPY on Sharpe. No H31 artifact exists in this repo (`git log`, no
     `*_results.json` for it). Its measured predecessor H30
     (`scout/beatspy_lab.py`, `beatspy_results.json`) answered the identical
     question: its pre-registered primary book returns CAGR 11.21%,
     Sharpe 0.613, alpha -2.71%/yr at t -0.80, and **0 of 24 point-in-time
     books beat SPY**. This lab RE-READS that file rather than trusting the
     prose, and falls back to SPY. The momentum book is rebuilt here anyway,
     because it is the raw material for the only sleeve this repo can make.
  2. SLEEVE = the H32 "workout" sleeve, if and only if H32 returns a positive,
     near-zero-beta result. **No H32 artifact exists either, and the sleeve it
     describes CANNOT be built from this repo's data.** Buffett's workouts were
     announced mergers, tenders, liquidations and spin-offs; pricing them needs
     a deal table (announcement date, terms, expected close). This repo holds
     daily bars (`bars.py`), XBRL financial facts (`sec_bulk.py`, 23.4M facts -
     financial statement line items, no deal terms), Benzinga headlines for 120
     names, 21k 8-K earnings dates and 5-minute bars. There is no deal
     universe, and reconstructing one from "which tickers stopped printing"
     is knowing the outcome in advance. So the brief's stated fallback is the
     path this lab takes:
        report what Sharpe an uncorrelated sleeve WOULD have needed, at what
        weight, to move the combined book to a given target - i.e. quantify
        the size of the thing we do not have -
     and, going one step further than the brief requires, MEASURE every
     near-zero-beta sleeve this repo's own measured findings CAN support, so
     the gap is quoted against real candidates and not only against zero.
  3. RISK LAYER = volatility targeting off the 5-minute realised-variance
     forecaster (H20: log-HAR on 5-min RV, 13-16% better QLIKE than daily
     closes after the verifiers' correction, 29/29 symbols, both halves), for
     SIZING ONLY. H20's own timing payoff was REJECTED and adding a day of lag
     improved it, so this lab reports the vol-targeted book beside the untargeted
     one and treats any gain as unproven by construction.
  4. LEVERAGE = `growth.kelly_fraction_for_drawdown` at an explicit budget,
     with the realised peak-to-trough printed next to the budget, because the
     bound is start-relative and `growth_selftest` measured peak-to-trough at
     ~1.5x it.

THE SLEEVE INVENTORY (all near-zero-beta by construction, all from measured parts)
---------------------------------------------------------------------------------
  mom_hedged  : the H25/H30 momentum book (12-1 momentum inside the shipped
                gates, point-in-time S&P 500, 20 names, inverse-vol weight,
                laddered across all 42 entry offsets) MINUS a causal trailing
                beta of SPY. This is the market-neutral form of the repo's one
                confirmatory signal.
  v5_hedged   : the same, ranked by the shipped v5 composite.
  ew_minus_spy: the equal-weight gated pool minus SPY - the sleeve form of
                Round 4's structural finding (-0.216 Sharpe before selection).
  overnight   : SPY close->open only, beta-hedged (H18: the premium accrues
                overnight; H18's verdict was "real and not tradeable").
  cash        : the honest zero-beta zero-Sharpe sleeve. Included because it is
                what "uncorrelated" is worth when its Sharpe is zero, and every
                frontier row should be read against it.
  CONTROLS    : `shuffled` (block-shuffled mom_hedged: timing destroyed,
                distribution kept) and `random_hedged` (uniform draws from the
                identical gated pool on the identical dates, identically
                weighted, identically hedged).

DATA DEFECTS - which guards were used (all three, stated as the brief demands)
-----------------------------------------------------------------------------
  GUARD 1 (5.1% unadjusted splits): the panel comes from
     `beatspy_lab.load_panel()` -> `idiovol_lab.clean_prices()`, which applies
     `repair_splits` (log-ratio tolerance 0.35).
  GUARD 2 (146 spin-off / reused-ticker >50% moves): `guarded_returns` blanks
     any |1-day return| > 0.45, and `blackout_mask` makes the symbol INELIGIBLE
     for 252 sessions after a guarded print, because a 12-1 rank reads a level
     252 sessions back. 251 guarded prints in this panel.
  GUARD 3 (frozen quotes on delisted/halted names, +896 bps of fake drift in
     H26): `retire_stale` inside `clean_prices` retires a symbol at its first
     run of 10 identical closes.
  Membership is POINT-IN-TIME S&P 500 (`scout/pit.py`) for the primary, so no
  survivorship is in the pool either.

NO LOOKAHEAD - every shift, named
---------------------------------
  * ranks read `close.shift(21)/close.shift(252)`; the book forms at close(t)
    and its first return is close(t)->close(t+1) (`sleeve_returns` indexes
    g[t+1]/g[t]).
  * the hedge ratio at t is the OLS beta over the 252 sessions ENDING t-1
    (`.shift(1)` on the rolling cov/var).
  * the sleeve's vol scalar at t uses the 252-session realised vol ending t-1
    (`.shift(1)`).
  * the vol-target scalar at t uses `har_forecast`'s prediction for t, which
    that function already `.shift(1)`-ed and whose coefficients come from a fit
    ending two sessions earlier.
  * the CAUSAL Kelly variant estimates mu and sigma on an expanding window
    ending t-1. The full-sample Kelly number is reported too and is explicitly
    labelled IN-SAMPLE, because it is the number the brief asks for and it is
    not tradeable.

CONFIRMATORY OR EXPLORATORY
---------------------------
The ALLOCATION ARITHMETIC is deterministic algebra, not a test - it has no
t-statistic and needs none. The SLEEVE MEASUREMENTS are CONFIRMATORY re-reads
of already-registered results (H25 momentum, H18 overnight, Round 4's
equal-weight decomposition), each with a strong prior and one specification.
The COMBINATION GRID (5 sleeves x 5 overlay weights x 3 risk layers) is a small
EXPLORATORY sweep and the primary is pre-registered BEFORE the run:

    PRIMARY = SPY core + mom_hedged sleeve at overlay k = 0.50,
              no vol targeting, unlevered, 10 bps round trip.

Chosen ex ante, not from any result: mom_hedged is the market-neutral form of
the only signal in this repo with an external prior AND a positive in-repo
market-adjusted measurement; k = 0.50 puts roughly a quarter of the book's
risk in the sleeve, which is the weight at which a sleeve has to be real to
matter and small enough that a retail account can carry the short leg.

Usage:
    python -m scout.partnership_lab --selftest    # offline, no keys
    python -m scout.partnership_lab               # the experiment
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from . import config, growth as G
from . import beatspy_lab as B

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against an outcome.
# --------------------------------------------------------------------------
UNIVERSE = "pit500"            # point-in-time S&P 500: no survivorship
BOOK_SIZE = 20                 # H30's pre-registered primary book size
WEIGHT = "ivol"                # H30's pre-registered weighting
HOLD = B.HOLD                  # 42
STRIDE = B.STRIDE              # 21
COST_BPS = 10.0                # round trip, large caps (repo convention)
COST_BPS_HI = 20.0             # sensitivity
HEDGE_WIN = 252                # trailing window for the causal hedge beta
VOL_WIN = 252                  # trailing window for the sleeve's vol scalar
SLEEVE_TARGET_VOL = 0.10       # each sleeve normalised to 10% ann vol
OVERLAY_K = (0.0, 0.25, 0.50, 1.00, 1.50)
PRIMARY_K = 0.50
DD_BUDGET = 0.30               # explicit drawdown budget for the Kelly fraction
DD_PROB = 0.10                 # ... at this probability of ever breaching it
FINANCING = 0.05               # ASSUMED retail margin rate (beatspy convention)
MAX_LEV = 3.0                  # hard cap on any leverage number quoted
SEED = 20260809
BOOT_SEEDS = (20260809, 20260810, 20260811)   # Rule 16: MC sd of the bootstrap
N_TRIALS_REGISTRY = 420        # repo's running variant count BEFORE this lab
RESULTS = config.SCOUT_DIR / "partnership_results.json"
RVFC_CACHE = config.SCOUT_DIR / "cache_rvfc_panel.pkl"
BEATSPY_RESULTS = config.SCOUT_DIR / "beatspy_results.json"
TD = 252


# --------------------------------------------------------------------------
# small statistics helpers (Rule 17: every arm gets the same machinery)
# --------------------------------------------------------------------------

def ann(r: np.ndarray) -> float:
    return float(np.nanmean(r) * TD)


def vol(r: np.ndarray) -> float:
    return float(np.nanstd(r, ddof=1) * math.sqrt(TD))


def sharpe(r: np.ndarray, rf: float = 0.0) -> float:
    s = vol(r)
    return (ann(r) - rf) / s if s > 0 else float("nan")


def maxdd(r: np.ndarray) -> float:
    x = np.where(np.isfinite(r), r, 0.0)
    c = np.cumprod(1 + x)
    return float((c / np.maximum.accumulate(c) - 1).min() * 100)


def describe(r: np.ndarray, mkt: np.ndarray, cost_yr: float = 0.0) -> dict:
    """CAGR / vol / Sharpe / maxDD / beta / market-adjusted alpha, net of a
    flat annual cost. `B.perf` is reused verbatim so this lab's numbers are
    comparable with H30's line for line (Rule 17)."""
    p = B.perf(r, mkt, cost_yr=cost_yr)
    if p:
        p["cost_yr_pct"] = cost_yr * 100
    return p


def halves(r: np.ndarray, mkt: np.ndarray, cost_yr: float = 0.0) -> dict:
    m = np.isfinite(r) & np.isfinite(mkt)
    idx = np.flatnonzero(m)
    h = len(idx) // 2
    out = {}
    for name, sl in (("H1", idx[:h]), ("H2", idx[h:])):
        rr = np.full_like(r, np.nan)
        mm = np.full_like(mkt, np.nan)
        rr[sl] = r[sl]
        mm[sl] = mkt[sl]
        out[name] = describe(rr, mm, cost_yr)
    return out


def thirds(r: np.ndarray, mkt: np.ndarray, cost_yr: float = 0.0) -> dict:
    """EQUAL THIRDS. This is the check that killed H22: a median split can
    bisect a hot regime and hide that one era carried everything."""
    m = np.isfinite(r) & np.isfinite(mkt)
    idx = np.flatnonzero(m)
    n = len(idx)
    out = {}
    for j, sl in enumerate((idx[:n // 3], idx[n // 3: 2 * n // 3],
                            idx[2 * n // 3:])):
        rr = np.full_like(r, np.nan)
        mm = np.full_like(mkt, np.nan)
        rr[sl] = r[sl]
        mm[sl] = mkt[sl]
        d = describe(rr, mm, cost_yr)
        d["span"] = (int(sl[0]), int(sl[-1]))
        out[f"T{j + 1}"] = d
    return out


def diff_vs_market(a: np.ndarray, b: np.ndarray, mkt: np.ndarray) -> dict:
    """RULE 13, the version H29 failed: market-adjust the DIFFERENCE, not just
    the levels. A delta of two beta-laden books is itself beta-laden."""
    d = a - b
    reg = B.nw_ols(d, mkt, lags=HOLD - 1)
    m = np.isfinite(d) & np.isfinite(mkt)
    return dict(mean_ann=float(np.nanmean(d[m]) * TD * 100),
                beta=reg["beta"], alpha=reg["alpha"] * TD * 100,
                t_alpha=reg["t_alpha"], n=reg["n"])


def break_even_cost_bps(r_gross: np.ndarray, bench: np.ndarray,
                        turnover: float) -> dict:
    """Round-trip cost at which the book stops beating the benchmark.
    Net return is linear in cost: mu_net = mu_gross - turnover * c/1e4, and
    volatility is unchanged by a constant drift, so both roots are closed form."""
    m = np.isfinite(r_gross) & np.isfinite(bench)
    mu_g, sd = float(np.nanmean(r_gross[m]) * TD), vol(r_gross[m])
    mu_b, sd_b = float(np.nanmean(bench[m]) * TD), vol(bench[m])
    if turnover <= 0:
        return dict(ret=float("inf"), sharpe=float("inf"))
    c_ret = (mu_g - mu_b) / turnover * 1e4
    c_shp = (mu_g - sd / sd_b * mu_b) / turnover * 1e4 if sd_b > 0 else float("nan")
    return dict(ret=float(c_ret), sharpe=float(c_shp))


def rolling_beta(y: pd.Series, x: pd.Series, win: int = HEDGE_WIN) -> pd.Series:
    """CAUSAL hedge ratio: OLS beta over the `win` sessions ENDING t-1.
    The `.shift(1)` at the end is the whole no-lookahead claim for the hedge."""
    cov = y.rolling(win, min_periods=win // 2).cov(x)
    var = x.rolling(win, min_periods=win // 2).var()
    return (cov / var).shift(1)


def causal_vol(r: pd.Series, win: int = VOL_WIN) -> pd.Series:
    """Annualised realised vol over the `win` sessions ENDING t-1."""
    return (r.rolling(win, min_periods=win // 2).std(ddof=1)
            * math.sqrt(TD)).shift(1)


# --------------------------------------------------------------------------
# 1. the core, and the check that it should be SPY
# --------------------------------------------------------------------------

def core_decision() -> dict:
    """Re-read H30's artifact rather than trusting the prose. If any measured
    point-in-time book beat SPY on Sharpe, the core would be that book."""
    out = {"h31_artifact": False, "h32_artifact": False}
    if not BEATSPY_RESULTS.exists():
        out["h30_artifact"] = False
        out["core"] = "SPY"
        out["reason"] = "no measured equity book available; SPY by default"
        return out
    d = json.loads(BEATSPY_RESULTS.read_text())
    out["h30_artifact"] = True
    spy_sh = d["pit500"]["bench"]["SPY"]["sharpe"]
    beat = []
    for uni in ("pit500", "sp1500", "sp500today"):
        ref = d[uni]["bench"]["SPY"]["sharpe"]
        for k, v in d[uni]["books"].items():
            s = v.get("sharpe")
            if s is not None and np.isfinite(s) and s > ref:
                beat.append((uni, k, s))
    out["books_checked"] = sum(len(d[u]["books"]) for u in
                               ("pit500", "sp1500", "sp500today"))
    out["books_beating_spy_on_sharpe"] = beat
    out["pit500_spy_sharpe"] = spy_sh
    out["h30_primary"] = {k: d["primary"]["book"][k]
                          for k in ("cagr", "sharpe", "beta", "alpha", "t_alpha")}
    out["core"] = "SPY" if not any(b[0] == "pit500" for b in beat) else beat[0][1]
    out["reason"] = ("no point-in-time book beats SPY on Sharpe in H30's grid; "
                     "core = SPY as the brief instructs")
    return out


# --------------------------------------------------------------------------
# 2. the books, and the sleeves made from them
# --------------------------------------------------------------------------

def build_books(verbose: bool = True) -> dict:
    """Point-in-time S&P 500, all three guards, momentum / v5 / equal-weight
    pool books laddered across every entry offset (Rule 9 by construction)."""
    t0 = time.time()
    panel = B.load_panel()
    close = panel["close"]
    dates = close.index
    simple, bad = B.guarded_returns(close)
    black = B.blackout_mask(bad)
    f = B.features(close, panel["dollar_vol"], simple)
    g = B.growth_path(simple)
    mem = B.membership(close, panel["segment"], UNIVERSE)
    a = B.selections(f, mem, black, sizes=(BOOK_SIZE,), seed=SEED)
    spy = simple[:, list(close.columns).index(B.MARKET)]

    n_s = close.shape[1]
    books = {}
    for name, sel_key in (("mom", "mom_sel"), ("v5", "v5_sel")):
        sel = a[sel_key][:, :BOOK_SIZE]
        w = B.make_weights(sel, f["vol"], WEIGHT)
        sub, wend = B.sleeve_returns(g, sel, w)
        to = B.book_turnover(sel, w, wend, n_s)
        books[name] = dict(r=B.ladder(sub), turnover=to, sub=sub, sel=sel, w=w)

    # the equal-weight GATED POOL: Round 4's structural finding, as a book.
    elig = a["elig"]
    pool_r = np.full(len(dates), np.nan)
    ok = elig.sum(1) > 0
    sm = np.where(np.isfinite(simple), simple, np.nan)
    for i in range(1, len(dates)):
        j = np.flatnonzero(elig[i - 1])          # weights set at close(t-1)
        if j.size == 0:
            continue
        v = sm[i, j]
        v = v[np.isfinite(v)]
        if v.size:
            pool_r[i] = v.mean()
    books["pool"] = dict(r=pool_r, turnover=float(np.nan), sub=None,
                         sel=None, w=None)

    if verbose:
        print(f"  books built in {time.time() - t0:.1f}s  "
              f"pool mean {a['pool_n'].mean():.0f} names, "
              f"{int(bad.sum())} guarded prints")
    return dict(panel=panel, dates=dates, simple=simple, bad=bad, black=black,
                f=f, g=g, elig=elig, spy=spy, books=books,
                pool_n=a["pool_n"], base_n=a["base_n"], n_s=n_s)


def overnight_leg(dates) -> np.ndarray:
    """SPY close(t-1) -> open(t), from the shared bar cache. H18's leg."""
    from . import bars
    px = bars.get([B.MARKET], str(dates[0].date()), str(dates[-1].date()))

    def norm(fr):
        s = fr[B.MARKET].copy()
        idx = pd.DatetimeIndex(s.index)
        if idx.tz is not None:                 # bars.get returns US/Eastern
            idx = idx.tz_localize(None)
        s.index = idx.normalize()
        return s.reindex(dates)

    o = norm(px["open"])
    c = norm(px["close"])
    r = np.array((o / c.shift(1) - 1.0).to_numpy(), dtype=float, copy=True)
    r[np.abs(r) > B.BIG_MOVE] = np.nan        # GUARD 2 on the ETF too
    return r


def make_sleeves(D: dict, verbose: bool = True) -> dict:
    """Every near-zero-beta sleeve this repo's measured findings can support.

    Each sleeve is `book - h_t * SPY` with h_t the CAUSAL trailing beta, so its
    ex-post beta is near zero by construction and its Sharpe is the honest
    market-neutral answer, not a beta in costume."""
    dates, spy = D["dates"], D["spy"]
    spy_s = pd.Series(spy, index=dates)
    out = {}

    def hedge(r: np.ndarray, turnover: float, label: str,
              extra_legs: float = 1.0) -> dict:
        rs = pd.Series(r, index=dates)
        h = rolling_beta(rs, spy_s).clip(-2.0, 3.0)
        sl = (rs - h * spy_s).to_numpy()
        # cost: the book's own turnover plus the hedge leg's rebalancing.
        # |dh| per session is a SPY trade of that size; charged at the same
        # round-trip rate, which is conservative for an ETF.
        hedge_to = float(np.nansum(np.abs(h.diff().to_numpy())) / max(
            np.isfinite(h).sum(), 1) * TD)
        tot_to = (0.0 if not np.isfinite(turnover) else turnover) + hedge_to
        return dict(r=sl, raw=r, h=h.to_numpy(), turnover=tot_to,
                    book_turnover=turnover, hedge_turnover=hedge_to,
                    label=label, legs=extra_legs)

    out["mom_hedged"] = hedge(D["books"]["mom"]["r"],
                              D["books"]["mom"]["turnover"],
                              "12-1 momentum book, beta-hedged (H25/H30)")
    out["v5_hedged"] = hedge(D["books"]["v5"]["r"],
                             D["books"]["v5"]["turnover"],
                             "v5 composite book, beta-hedged")
    # the equal-weight pool rebalances daily by construction; its turnover is
    # dominated by the daily re-equalisation, measured directly below.
    ew_to = ew_pool_turnover(D)
    out["ew_minus_spy"] = hedge(D["books"]["pool"]["r"], ew_to,
                                "equal-weight gated pool, beta-hedged "
                                "(Round 4's structural finding)")
    on = overnight_leg(dates)
    # The overnight leg is in at the close and out at the open, i.e. one full
    # round trip a session. In the repo's 0.5*sum|dw| convention that is
    # 0.5*|1-0| + 0.5*|0-1| = 1.0 per session, so 252x/yr - NOT 504. A round
    # trip is charged once, at COST_BPS.
    out["overnight"] = hedge(on, 1.0 * TD,
                             "SPY close->open only, beta-hedged (H18)")
    out["cash"] = dict(r=np.where(np.isfinite(spy), 0.0, np.nan), raw=None,
                       h=np.zeros(len(dates)), turnover=0.0,
                       book_turnover=0.0, hedge_turnover=0.0,
                       label="cash: the honest zero-beta zero-Sharpe sleeve",
                       legs=0.0)

    # ---- CONTROLS -------------------------------------------------------
    rng = np.random.default_rng(SEED + 31)
    base = out["mom_hedged"]["r"]
    m = np.isfinite(base)
    idx = np.flatnonzero(m)
    blk = HOLD
    nb = int(math.ceil(len(idx) / blk))
    starts = rng.integers(0, len(idx), size=nb)
    take = (starts[:, None] + np.arange(blk)[None, :]).reshape(-1) % len(idx)
    shuf = np.full_like(base, np.nan)
    shuf[idx] = base[idx][take[:len(idx)]]
    out["shuffled"] = dict(r=shuf, raw=None, h=None,
                           turnover=out["mom_hedged"]["turnover"],
                           book_turnover=out["mom_hedged"]["book_turnover"],
                           hedge_turnover=out["mom_hedged"]["hedge_turnover"],
                           label="CONTROL: block-shuffled mom_hedged "
                                 "(timing destroyed, distribution kept)",
                           legs=1.0)
    if verbose:
        for k, v in out.items():
            print(f"    sleeve {k:14s} turnover {v['turnover']:6.2f}x/yr  "
                  f"{v['label']}")
    return out


def ew_pool_turnover(D: dict) -> float:
    """Annual turnover of a DAILY-rebalanced equal-weight book over a pool
    whose membership changes: 0.5*sum|w_t - w_{t-1}^drifted|, the repo's
    convention (`growth.turnover_cost`)."""
    elig, simple = D["elig"], D["simple"]
    n_d = elig.shape[0]
    prev = None
    tot, n = 0.0, 0
    for i in range(1, n_d):
        j = np.flatnonzero(elig[i])
        if j.size == 0:
            prev = None
            continue
        w = np.zeros(elig.shape[1])
        w[j] = 1.0 / j.size
        if prev is not None:
            drift = prev * (1 + np.nan_to_num(simple[i]))
            s = drift.sum()
            if s > 0:
                drift = drift / s
                tot += 0.5 * float(np.abs(w - drift).sum())
                n += 1
        prev = w
    return float(tot / max(n, 1) * TD)


def random_hedged_control(D: dict, reps: int = 60) -> dict:
    """CONTROL (b): uniform draws from the IDENTICAL gated pool on the
    IDENTICAL dates, weighted the identical way, hedged the identical way.
    Everything except the momentum rank is held fixed."""
    rng = np.random.default_rng(SEED + 7)
    elig, g, f, spy = D["elig"], D["g"], D["f"], D["spy"]
    dates = D["dates"]
    spy_s = pd.Series(spy, index=dates)
    n_d = elig.shape[0]
    pools = [np.flatnonzero(elig[i]) for i in range(n_d)]
    sh, al, be, cagr = [], [], [], []
    for _ in range(reps):
        sel = np.full((n_d, BOOK_SIZE), -1, dtype=np.int32)
        for i, p in enumerate(pools):
            if p.size == 0:
                continue
            k = min(BOOK_SIZE, p.size)
            sel[i, :k] = rng.choice(p, size=k, replace=False)
        w = B.make_weights(sel, f["vol"], WEIGHT)
        sub, wend = B.sleeve_returns(g, sel, w)
        to = B.book_turnover(sel, w, wend, D["n_s"])
        r = B.ladder(sub)
        rs = pd.Series(r, index=dates)
        h = rolling_beta(rs, spy_s).clip(-2.0, 3.0)
        sl = (rs - h * spy_s).to_numpy()
        hedge_to = float(np.nansum(np.abs(h.diff().to_numpy())) /
                         max(np.isfinite(h).sum(), 1) * TD)
        cy = (to + hedge_to) * COST_BPS / 1e4
        p = describe(sl, spy, cost_yr=cy)
        if not p:
            continue
        sh.append(p["sharpe"]); al.append(p["alpha"])
        be.append(p["beta"]); cagr.append(p["cagr"])
    return dict(n=len(sh), sharpe=np.array(sh), alpha=np.array(al),
                beta=np.array(be), cagr=np.array(cagr))


# --------------------------------------------------------------------------
# 3. the combination
# --------------------------------------------------------------------------

def scaled_sleeve(sleeve_r: np.ndarray, dates, target: float = SLEEVE_TARGET_VOL,
                  cap: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Sleeve scaled to a constant EX-ANTE volatility using the trailing
    252-session realised vol ending t-1. Returns (scaled series, scalar)."""
    s = pd.Series(sleeve_r, index=dates)
    v = causal_vol(s)
    k = (target / v).clip(upper=cap).fillna(0.0)
    return (k * s).to_numpy(), k.to_numpy()


def combine(core: np.ndarray, sleeve: np.ndarray, k: float) -> np.ndarray:
    """The overlay form: hold the core at 1.0 and carry the dollar-neutral
    sleeve on top at k units of its 10%-vol scaling. This is what a partnership
    with a workouts bucket actually holds; it needs margin and stock borrow,
    which is stated in the caveats and is NOT free.

    NaN propagates from the sleeve ON PURPOSE, including at k = 0: every arm of
    the comparison must live on the SAME sessions (Rule 17), and the sleeve's
    252-session vol warm-up is what sets the common sample."""
    ok = np.isfinite(core) & np.isfinite(sleeve)
    return np.where(ok, core + k * np.nan_to_num(sleeve), np.nan)


def eff_bets(core: np.ndarray, sleeve: np.ndarray, k: float) -> dict:
    m = np.isfinite(core) & np.isfinite(sleeve)
    X = np.column_stack([core[m], sleeve[m]])
    cov = np.cov(X, rowvar=False) * TD
    corr = np.corrcoef(X, rowvar=False)
    w = np.array([1.0, k])
    w = w / w.sum() if w.sum() > 0 else w
    return dict(effective_bets=G.effective_bets(w, cov),
                corr=float(corr[0, 1]),
                cov=cov.tolist(), weights=w.tolist())


# --------------------------------------------------------------------------
# 4. the risk layer - H20's forecaster, for SIZING only
# --------------------------------------------------------------------------

def rv_leverage(dates, target_vol: float, cap: float = 2.0) -> dict:
    """Vol-target scalars for SPY from three variance forecasts, aligned to
    `dates`. All three are causal: the daily-close and EWMA-RV filters are
    written before the session they price, and `har_forecast` already
    `.shift(1)`-s its prediction onto the session it forecasts.

    SIZING ONLY. H20's timing payoff was rejected and adding lag improved it;
    nothing here times exposure on a return forecast."""
    if not RVFC_CACHE.exists():
        return {}
    from .rv_forecast_lab import har_forecast, ewma_var
    d = pd.read_pickle(RVFC_CACHE)
    rv_cc = d["rv_cc"][[B.MARKET]]
    r2 = d["r2"][[B.MARKET]]
    fc = {
        "daily_ewma": ewma_var(r2[B.MARKET], 0.94),
        "rv_ewma": ewma_var(rv_cc[B.MARKET], 0.94),
        "har_log_rv": har_forecast(rv_cc, log=True, pooled=False)[B.MARKET],
    }
    out = {}
    for name, v in fc.items():
        sd = (np.sqrt(np.maximum(v.astype(float), 0.0)) * math.sqrt(TD))
        lev = (target_vol / sd.replace(0.0, np.nan)).clip(upper=cap).clip(lower=0.0)
        out[name] = lev.reindex(dates).to_numpy()
        # SELF-TARGETED variant: the target is the CAUSAL expanding mean of the
        # forecaster's own volatility (through t-1), so the scalar averages ~1
        # by construction and the comparison is not secretly a de-levering.
        # Without this the whole book can be scaled down for the entire sample
        # merely because the fixed target was set from a calmer era.
        tgt = sd.expanding(252).mean().shift(1)
        lev2 = (tgt / sd.replace(0.0, np.nan)).clip(upper=cap).clip(lower=0.0)
        out[name + "_selftarget"] = lev2.reindex(dates).to_numpy()
    out["_span"] = (str(rv_cc.index[0].date()), str(rv_cc.index[-1].date()))
    return out


# --------------------------------------------------------------------------
# 5. leverage - the drawdown-constrained Kelly fraction
# --------------------------------------------------------------------------

def kelly_block(r: np.ndarray, mkt: np.ndarray, dd: float = DD_BUDGET,
                prob: float = DD_PROB, financing: float = FINANCING) -> dict:
    """Full-sample (IN-SAMPLE, and labelled so) Kelly, the drawdown-constrained
    fraction, the resulting leverage, and the REALISED peak-to-trough of the
    levered path net of financing on the borrowed part."""
    m = np.isfinite(r) & np.isfinite(mkt)
    x = r[m]
    mu, sd = float(x.mean() * TD), vol(x)
    if sd <= 0:
        return {}
    L_full = G.optimal_leverage(mu, sd)
    frac = G.kelly_fraction_for_drawdown(dd, prob)
    L = min(frac * L_full, MAX_LEV)
    lev_r = L * x - max(L - 1.0, 0.0) * financing / TD
    out = dict(mu=mu * 100, sigma=sd * 100, sharpe=mu / sd,
               kelly_full=L_full, fraction=frac, leverage=L,
               leverage_uncapped=frac * L_full, capped=bool(frac * L_full > MAX_LEV),
               dd_budget=dd * 100, dd_prob=prob,
               realised_maxdd=maxdd(lev_r),
               growth_unlevered=G.growth_rate(mu, sd) * 100,
               growth_levered=G.growth_at_leverage(mu, sd, L) * 100,
               financing=financing * 100)
    out["dd_breach_ratio"] = abs(out["realised_maxdd"]) / (dd * 100)
    out["levered_perf"] = describe(
        np.where(m, np.nan_to_num(r) * L - max(L - 1.0, 0.0) * financing / TD,
                 np.nan), mkt)
    return out


def kelly_causal(r: np.ndarray, mkt: np.ndarray, dd: float = DD_BUDGET,
                 prob: float = DD_PROB, financing: float = FINANCING,
                 min_obs: int = 504) -> dict:
    """The TRADEABLE version: mu and sigma from an expanding window ENDING
    t-1, so the leverage carried on day t was knowable on day t-1."""
    s = pd.Series(r)
    mu = (s.expanding(min_obs).mean() * TD).shift(1)
    sd = (s.expanding(min_obs).std(ddof=1) * math.sqrt(TD)).shift(1)
    frac = G.kelly_fraction_for_drawdown(dd, prob)
    L = (frac * mu / (sd ** 2)).clip(lower=0.0, upper=MAX_LEV).fillna(0.0)
    lev = (L * s - (L - 1.0).clip(lower=0.0) * financing / TD).to_numpy()
    lev = np.where(np.isfinite(r), lev, np.nan)
    d = describe(lev, mkt)
    d.update(mean_leverage=float(L[L > 0].mean()) if (L > 0).any() else 0.0,
             max_leverage=float(L.max()), fraction=frac,
             realised_maxdd=maxdd(lev), dd_budget=dd * 100)
    d["dd_breach_ratio"] = abs(d["realised_maxdd"]) / (dd * 100)
    return d


# --------------------------------------------------------------------------
# 6. THE FRONTIER - what we would have needed, since we do not have it
# --------------------------------------------------------------------------

def required_sleeve_sharpe(S_core: float, S_target: float, w_s: float,
                           rho: float) -> float:
    """Invert S_p = (w_c S_c + w_s S_s)/sqrt(w_c^2 + w_s^2 + 2 w_c w_s rho)
    for S_s, with risk weights on unit-volatility sleeves (w_c = 1 - w_s).

    This is `growth.combine_sharpe` solved backwards, and it is the whole
    negative result: it prices the sleeve we do not have."""
    w_c = 1.0 - w_s
    if w_s <= 0:
        return float("inf")
    d = math.sqrt(max(w_c ** 2 + w_s ** 2 + 2 * w_c * w_s * rho, 1e-12))
    return (S_target * d - w_c * S_core) / w_s


def frontier(S_core: float) -> dict:
    """The table the brief asks for when the sleeve does not exist: what Sharpe
    an uncorrelated sleeve would have needed, at what weight, to hit a target -
    plus the growth translation, because g* = S^2/2 is why anyone cares."""
    targets = {
        "SPY+0.25": S_core + 0.25,
        "SPY+0.50": S_core + 0.50,
        "2x Kelly growth (S x sqrt2)": S_core * math.sqrt(2),
        "landslide: 4x Kelly growth (S x 2)": S_core * 2.0,
    }
    rows = []
    for tname, S_t in targets.items():
        for rho in (-0.20, 0.0, 0.20, 0.40):
            for w_s in (0.10, 0.20, 0.30, 0.50):
                S_s = required_sleeve_sharpe(S_core, S_t, w_s, rho)
                rows.append(dict(target=tname, S_target=S_t, rho=rho,
                                 w_sleeve=w_s, required_sleeve_sharpe=S_s,
                                 required_ann_ret_at_10pct_vol=S_s * 10.0,
                                 feasible=bool(S_s < 3.0)))
    # how many INDEPENDENT sleeves, each at a given Sharpe, alongside the core
    n_needed = {}
    for S_s in (0.25, 0.50, 0.75, 1.00):
        for tname, S_t in targets.items():
            n = None
            for k in range(1, 51):
                # core + k identical sleeves, all mutually uncorrelated,
                # equal risk weights (growth.equal_weight_sharpe's setting)
                S_p = G.combine_sharpe([S_core] + [S_s] * k,
                                       np.eye(k + 1))
                if S_p >= S_t:
                    n = k
                    break
            n_needed[f"S_sleeve={S_s:.2f} -> {tname}"] = n
    return dict(S_core=S_core, targets=targets, rows=rows,
                n_uncorrelated_sleeves_needed=n_needed)


# --------------------------------------------------------------------------
# 7. offline selftest (no keys, no cache, known answers)
# --------------------------------------------------------------------------

def selftest(quiet: bool = False) -> int:
    fails = []

    def chk(name, cond, detail=""):
        if not cond:
            fails.append(f"{name}: {detail}")
        elif not quiet:
            print(f"  ok  {name}")

    # -- the frontier algebra inverts combine_sharpe exactly
    for S_c in (0.5, 1.0):
        for w in (0.1, 0.3, 0.5):
            for rho in (-0.2, 0.0, 0.4):
                S_t = S_c + 0.3
                S_s = required_sleeve_sharpe(S_c, S_t, w, rho)
                C = np.array([[1.0, rho], [rho, 1.0]])
                got = G.combine_sharpe([S_c, S_s], C, [1 - w, w])
                chk(f"frontier inverts combine_sharpe S_c={S_c} w={w} rho={rho}",
                    abs(got - S_t) < 1e-9, f"{got} vs {S_t}")

    # -- an uncorrelated sleeve with ZERO Sharpe cannot raise the combination
    chk("zero-Sharpe uncorrelated sleeve lowers portfolio Sharpe",
        G.combine_sharpe([1.0, 0.0], np.eye(2), [0.8, 0.2]) < 1.0)

    # -- growth identity: g* = S^2/2
    mu, sd = 0.08, 0.16
    chk("g* = S^2/2", abs(G.growth_at_leverage(mu, sd, G.optimal_leverage(mu, sd))
                          - (mu / sd) ** 2 / 2) < 1e-12)

    # -- rolling_beta is causal: a beta computed with future data would see it
    rng = np.random.default_rng(1)
    n = 800
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    x = pd.Series(rng.normal(0, 0.01, n), index=idx)
    y = 1.5 * x + pd.Series(rng.normal(0, 0.002, n), index=idx)
    b = rolling_beta(y, x, 252)
    chk("rolling_beta recovers the true beta", abs(np.nanmean(b) - 1.5) < 0.05,
        f"{np.nanmean(b)}")
    y2 = y.copy()
    y2.iloc[-1] = 99.0                      # corrupt only the LAST session
    b2 = rolling_beta(y2, x, 252)
    chk("rolling_beta cannot see session t (no lookahead)",
        np.allclose(np.nan_to_num(b.to_numpy()), np.nan_to_num(b2.to_numpy())))

    # -- causal_vol likewise
    v = causal_vol(y)
    y3 = y.copy(); y3.iloc[-1] = 99.0
    chk("causal_vol cannot see session t",
        np.allclose(np.nan_to_num(causal_vol(y3).to_numpy()),
                    np.nan_to_num(v.to_numpy())))

    # -- hedging a pure-beta series to zero leaves ~zero
    core = pd.Series(rng.normal(0.0004, 0.011, n), index=idx)
    lev = 1.3 * core
    h = rolling_beta(lev, core, 252)
    resid = (lev - h * core).dropna()
    chk("beta-hedge annihilates a pure beta book",
        abs(float(resid.std())) < 1e-12, f"{float(resid.std())}")

    # -- kelly_fraction_for_drawdown: the documented closed form
    f30 = G.kelly_fraction_for_drawdown(0.30, 0.10)
    lq = math.log(0.70)
    chk("kelly_fraction_for_drawdown matches its closed form",
        abs(f30 - 2 * lq / (lq + math.log(0.10))) < 1e-12)
    chk("full Kelly => 50% chance of halving",
        abs(G.kelly_fraction_for_drawdown(0.5, 0.5) - 1.0) < 1e-9)

    # -- break-even cost is the root of the linear net-return equation
    a = rng.normal(0.0006, 0.01, 2000)
    bmk = rng.normal(0.0004, 0.01, 2000)
    be = break_even_cost_bps(a, bmk, turnover=2.0)
    net = a - 2.0 * be["ret"] / 1e4 / TD
    chk("break-even (return) zeroes the return gap",
        abs(np.mean(net) - np.mean(bmk)) < 1e-12)

    # -- thirds partition exactly and do not overlap
    r = np.concatenate([np.full(10, np.nan), rng.normal(0, 0.01, 900)])
    mk = np.concatenate([np.full(10, np.nan), rng.normal(0, 0.01, 900)])
    t = thirds(r, mk)
    spans = [t[k]["span"] for k in ("T1", "T2", "T3")]
    chk("equal thirds partition the finite sample",
        spans[0][1] < spans[1][0] and spans[1][1] < spans[2][0], str(spans))

    # -- effective bets: two uncorrelated equal-risk sleeves = 2 bets
    cov2 = np.eye(2) * 0.01
    chk("effective_bets = 2 for two orthogonal equal sleeves",
        abs(G.effective_bets([0.5, 0.5], cov2) - 2.0) < 1e-9)
    cov1 = np.array([[0.01, 0.00999], [0.00999, 0.01]])
    chk("effective_bets ~ 1 for two near-identical sleeves",
        G.effective_bets([0.5, 0.5], cov1) < 1.15)

    if fails:
        print("\nFAILED:")
        for f in fails:
            print("  " + f)
        return 1
    if not quiet:
        print(f"\nselftest: all checks passed")
    return 0


# --------------------------------------------------------------------------
# 8. the run
# --------------------------------------------------------------------------

def _hdr(s: str) -> None:
    print("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78)


def _fmt(p: dict) -> str:
    if not p:
        return "  (insufficient sample)"
    return (f"CAGR {p['cagr']:+6.2f}%  vol {p['ann_vol']:5.2f}%  "
            f"Sharpe {p['sharpe']:+5.2f}  maxDD {p['maxdd']:7.2f}%  "
            f"beta {p['beta']:+5.2f}  alpha {p['alpha']:+6.2f}%/yr "
            f"(t {p['t_alpha']:+5.2f})")


def run(args) -> dict:
    res = {"meta": {}, "variants": []}
    t_start = time.time()

    _hdr("H34 - the Partnership structure.  ALLOCATION STUDY, NOT A SIGNAL.")
    print("Mechanism: g* = S^2/2, so growth is quadratic in Sharpe and Sharpe is")
    print("bought by adding a weakly-correlated sleeve, not by forecasting better.")

    # ---- 1. the core -----------------------------------------------------
    _hdr("1. CORE - is there an equity book that should displace SPY?")
    cd = core_decision()
    res["core_decision"] = cd
    print(f"  H31 artifact present: {cd['h31_artifact']}   "
          f"H32 artifact present: {cd['h32_artifact']}")
    if cd.get("h30_artifact"):
        print(f"  H30's grid: {cd['books_checked']} books measured; "
              f"{len(cd['books_beating_spy_on_sharpe'])} beat SPY on Sharpe")
        print(f"  H30 primary book: CAGR {cd['h30_primary']['cagr']:.2f}%  "
              f"Sharpe {cd['h30_primary']['sharpe']:.3f}  "
              f"beta {cd['h30_primary']['beta']:.2f}  "
              f"alpha {cd['h30_primary']['alpha']:+.2f}%/yr "
              f"(t {cd['h30_primary']['t_alpha']:+.2f})")
    print(f"  => CORE = {cd['core']}  ({cd['reason']})")
    print("  H32 (workouts) CANNOT be built here: pricing an announced merger,")
    print("  tender or liquidation needs a deal table (announcement date, terms,")
    print("  expected close). This repo has daily bars, XBRL statement facts,")
    print("  Benzinga headlines for 120 names and 5-minute bars - no deal")
    print("  universe. Reconstructing one from 'which tickers stopped printing'")
    print("  is knowing the outcome in advance. So the sleeve is measured from")
    print("  what exists, and the frontier prices what does not.")

    # ---- 2. the books and the sleeves ------------------------------------
    _hdr("2. BOOKS and SLEEVES  (point-in-time S&P 500, all three guards)")
    D = build_books()
    spy = D["spy"]
    dates = D["dates"]
    res["meta"].update(
        start=str(dates[0].date()), end=str(dates[-1].date()),
        n_sessions=int(len(dates)), n_symbols=int(D["n_s"]),
        universe=UNIVERSE, book_size=BOOK_SIZE, weight=WEIGHT,
        hold=HOLD, cost_bps=COST_BPS, guards="1 split-repair, "
        "2 big-move blank + 252d blackout, 3 stale-quote retirement",
        guarded_prints=int(D["bad"].sum()),
        pool_mean=float(D["pool_n"].mean()))

    spy_perf = describe(spy, spy)
    # regressing SPY on itself yields alpha = 0 by construction; its t is a
    # floating-point artifact and is blanked rather than printed as evidence.
    spy_perf["alpha"] = 0.0
    spy_perf["t_alpha"] = 0.0
    print(f"\n  SPY (the core)          {_fmt(spy_perf)}")
    spy_h, spy_t = halves(spy, spy), thirds(spy, spy)
    print(f"  {'':24s}   halves Sharpe {spy_h['H1']['sharpe']:+.2f}/"
          f"{spy_h['H2']['sharpe']:+.2f}   thirds "
          f"{spy_t['T1']['sharpe']:+.2f}/{spy_t['T2']['sharpe']:+.2f}/"
          f"{spy_t['T3']['sharpe']:+.2f}")
    res["spy"] = spy_perf
    res["spy_halves"], res["spy_thirds"] = spy_h, spy_t
    S_core = spy_perf["sharpe"]

    sleeves = make_sleeves(D)
    res["sleeves"] = {}
    print("\n  each sleeve = book - h_t*SPY, h_t = trailing 252d beta ending t-1")
    print("  (net of costs at 10 bps round trip on book turnover + hedge leg)\n")
    for name, s in sleeves.items():
        cy = s["turnover"] * COST_BPS / 1e4
        p_net = describe(s["r"], spy, cost_yr=cy)
        p_gross = describe(s["r"], spy, cost_yr=0.0)
        if not p_net:
            print(f"  {name:14s} (insufficient sample - skipped)")
            continue
        if not np.isfinite(p_net["ann_vol"]) or p_net["ann_vol"] == 0.0:
            # the cash sleeve: zero vol, so Sharpe is 0/0. It is exactly zero.
            for d_ in (p_net, p_gross):
                d_["sharpe"] = 0.0
                d_["beta"] = 0.0
                d_["alpha"] = 0.0
                d_["t_alpha"] = 0.0
        with np.errstate(invalid="ignore", divide="ignore"):
            corr = float(pd.Series(s["r"]).corr(pd.Series(spy)))
        if not np.isfinite(corr):
            corr = 0.0
        be = break_even_cost_bps(s["r"], np.zeros_like(spy), s["turnover"])
        rec = dict(net=p_net, gross=p_gross, corr_spy=corr,
                   turnover=s["turnover"], book_turnover=s["book_turnover"],
                   hedge_turnover=s["hedge_turnover"],
                   break_even_cost_bps=be["ret"], label=s["label"],
                   halves=halves(s["r"], spy, cy),
                   thirds=thirds(s["r"], spy, cy),
                   halves_gross=halves(s["r"], spy, 0.0),
                   thirds_gross=thirds(s["r"], spy, 0.0),
                   cost20=describe(s["r"], spy, cost_yr=s["turnover"] * COST_BPS_HI / 1e4))
        res["sleeves"][name] = rec
        res["variants"].append(f"sleeve:{name}")
        print(f"  {name:14s} NET   {_fmt(p_net)}")
        print(f"  {'':14s} GROSS {_fmt(p_gross)}")
        print(f"  {'':14s}   corr(SPY) {corr:+.3f}  turnover {s['turnover']:6.1f}x/yr  "
              f"break-even {be['ret']:+8.2f} bps round trip")
        print(f"  {'':14s}   GROSS halves Sharpe "
              f"{rec['halves_gross']['H1']['sharpe']:+.2f}/"
              f"{rec['halves_gross']['H2']['sharpe']:+.2f}   thirds "
              f"{rec['thirds_gross']['T1']['sharpe']:+.2f}/"
              f"{rec['thirds_gross']['T2']['sharpe']:+.2f}/"
              f"{rec['thirds_gross']['T3']['sharpe']:+.2f}")

    # ---- 3. controls -----------------------------------------------------
    _hdr("3. CONTROLS")
    ctrl = random_hedged_control(D, reps=args.ctrl_reps)
    res["control_random_hedged"] = {
        k: (float(np.mean(v)) if isinstance(v, np.ndarray) else v)
        for k, v in ctrl.items()}
    if ctrl["n"]:
        res["control_random_hedged"].update(
            sharpe_p05=float(np.percentile(ctrl["sharpe"], 5)),
            sharpe_p50=float(np.percentile(ctrl["sharpe"], 50)),
            sharpe_p95=float(np.percentile(ctrl["sharpe"], 95)))
        mh = res["sleeves"]["mom_hedged"]["net"]["sharpe"]
        pct = float((ctrl["sharpe"] < mh).mean() * 100)
        res["control_random_hedged"]["mom_hedged_percentile"] = pct
        print(f"  random-pick hedged control ({ctrl['n']} histories): "
              f"Sharpe p05 {np.percentile(ctrl['sharpe'], 5):+.3f}  "
              f"median {np.percentile(ctrl['sharpe'], 50):+.3f}  "
              f"p95 {np.percentile(ctrl['sharpe'], 95):+.3f}")
        print(f"  mom_hedged Sharpe {mh:+.3f} sits at the {pct:.0f}th percentile "
              f"of the control")
    sh = res["sleeves"].get("shuffled", {}).get("net", {})
    if sh:
        print(f"  block-shuffled mom_hedged: Sharpe {sh['sharpe']:+.3f} "
              f"alpha {sh['alpha']:+.2f}%/yr (t {sh['t_alpha']:+.2f})")
    res["variants"] += ["control:random_hedged", "control:block_shuffle"]

    # ---- 4. the combination ---------------------------------------------
    _hdr("4. COMBINATION - SPY core + sleeve overlay")
    print("  overlay k units of a sleeve scaled to 10% ex-ante vol (trailing")
    print("  252d realised vol ending t-1). Core held at 1.0 throughout.\n")
    def spy_on(r: np.ndarray) -> float:
        """SPY's Sharpe on exactly the sessions `r` is defined (Rule 17: every
        arm of a comparison gets the same sample as well as the same code)."""
        p = describe(np.where(np.isfinite(r), spy, np.nan), spy)
        return float(p["sharpe"]) if p else float("nan")

    combos = {}
    for name, s in sleeves.items():
        if name in ("cash",):
            continue
        scal, kser = scaled_sleeve(s["r"], dates)
        cy_sleeve = s["turnover"] * COST_BPS / 1e4
        for k in OVERLAY_K:
            r = combine(spy, scal, k)
            # cost of the overlay scales with the exposure actually carried
            avg_k = float(np.nanmean(np.abs(kser)) * k)
            cy = cy_sleeve * avg_k
            p = describe(r, spy, cost_yr=cy)
            if not p:
                continue
            key = f"{name}@k{k:.2f}"
            eb = eff_bets(spy, scal, k)
            dv = diff_vs_market(r - cy / TD, spy, spy)
            combos[key] = dict(perf=p, eff=eb, diff_vs_spy=dv,
                               cost_yr=cy * 100, avg_exposure=avg_k,
                               spy_same_sample=spy_on(r))
            res["variants"].append(f"combo:{key}")
        # print only the primary weight per sleeve, and the best
        kk = f"{name}@k{PRIMARY_K:.2f}"
        if kk in combos:
            c = combos[kk]
            print(f"  {kk:22s} {_fmt(c['perf'])}")
            print(f"  {'':22s}   corr(core,sleeve) {c['eff']['corr']:+.3f}  "
                  f"effective bets {c['eff']['effective_bets']:.2f} of 2  "
                  f"diff-vs-SPY alpha {c['diff_vs_spy']['alpha']:+.2f}%/yr "
                  f"(t {c['diff_vs_spy']['t_alpha']:+.2f}, "
                  f"beta {c['diff_vs_spy']['beta']:+.3f})")
    res["combos"] = combos

    # Does ANY cell beat SPY on Sharpe? Each cell is compared with SPY on that
    # cell's OWN sessions - a k=0 cell IS SPY and is excluded, since a "win"
    # there would only be a different sample.
    beats, sh_all = [], []
    for key, c in combos.items():
        if key.endswith("k0.00"):
            continue
        sh_all.append(c["perf"]["sharpe"])
        if c["perf"]["sharpe"] > c["spy_same_sample"]:
            beats.append((key, c["perf"]["sharpe"], c["spy_same_sample"]))
    res["cells_beating_spy_same_sample"] = beats
    print(f"\n  cells in the grid (k>0): {len(sh_all)};  beating SPY on the "
          f"cell's own sessions: {len(beats)}"
          + (f"  -> {beats}" if beats else ""))
    print(f"  spread across cells: Sharpe {min(sh_all):+.3f} .. {max(sh_all):+.3f} "
          f"(the honest measure of how much of any winner is selection)")
    res["cell_sharpe_spread"] = [float(min(sh_all)), float(max(sh_all))]

    # ---- the diagnostic the alpha stack failed: 1.02 effective bets of 4 ---
    names = [n for n in ("mom_hedged", "v5_hedged", "ew_minus_spy", "overnight")
             if n in sleeves]
    cols = {"SPY": spy}
    for n in names:
        sc, _ = scaled_sleeve(sleeves[n]["r"], dates)
        cols[n] = np.where(np.isfinite(sleeves[n]["r"]), sc, np.nan)
    M = pd.DataFrame(cols)
    Mc = M.dropna()
    corr_mat = Mc.corr()
    cov_all = np.cov(Mc.to_numpy(), rowvar=False) * TD
    # equal RISK weights: each column already carries ~10% vol except SPY, so
    # scale to a common vol first, which is what "risk weight" means.
    sd_all = np.sqrt(np.diag(cov_all))
    w_rp = (1.0 / sd_all) / np.sum(1.0 / sd_all)
    eb_rp = G.effective_bets(w_rp, cov_all)
    eb_actual = G.effective_bets(
        np.array([1.0] + [PRIMARY_K] * len(names)) /
        (1.0 + PRIMARY_K * len(names)), cov_all)
    sh_all_sleeves = []
    for c in Mc.columns:
        to = 0.0 if c == "SPY" else sleeves[c]["turnover"]
        sh_all_sleeves.append(sharpe(Mc[c].to_numpy() - to * COST_BPS / 1e4 / TD))
    # Best LONG-ONLY risk-weighted Sharpe from SPY plus ONE sleeve, solved
    # exactly on the simplex for each pair. (`best_long_only_sharpe` with >2
    # inputs falls back to equal weights, which would misprice a set where
    # most components are negative - the optimiser's answer there is simply
    # "hold the core", and this loop says so explicitly.)
    pair_best = {}
    for j, cname in enumerate(Mc.columns):
        if cname == "SPY":
            continue
        cc = np.array([[1.0, corr_mat.iloc[0, j]], [corr_mat.iloc[0, j], 1.0]])
        pair_best[cname] = G.best_long_only_sharpe(
            [sh_all_sleeves[0], sh_all_sleeves[j]], cc)
    best_lo = max(pair_best.values())
    # eigen decomposition of the risk, so "1.39 of 5" is auditable
    _vals, _vecs = np.linalg.eigh(cov_all)
    _contrib = (_vecs.T @ w_rp) ** 2 * np.clip(_vals, 0, None)
    risk_shares = (_contrib / _contrib.sum()).round(4).tolist()
    res["correlation_matrix"] = dict(
        labels=list(Mc.columns), matrix=corr_mat.round(4).values.tolist(),
        n=int(len(Mc)),
        effective_bets_equal_risk=eb_rp,
        effective_bets_overlay=eb_actual,
        n_sleeves=len(names) + 1,
        component_sharpes_net10=sh_all_sleeves,
        best_long_only_sharpe_pairs=pair_best,
        best_long_only_sharpe=best_lo,
        risk_shares_by_pc=risk_shares,
        component_vols=(sd_all * 100).round(2).tolist(),
        risk_parity_weights=w_rp.tolist())
    print("\n  SLEEVE CORRELATION MATRIX (each sleeve at 10% ex-ante vol, "
          f"n = {len(Mc)} common sessions)")
    print("  " + " " * 14 + " ".join(f"{c:>13s}" for c in Mc.columns))
    for i, c in enumerate(Mc.columns):
        print(f"  {c:14s} " + " ".join(f"{corr_mat.iloc[i, j]:13.3f}"
                                       for j in range(len(Mc.columns))))
    print(f"  component vols: " + ", ".join(
        f"{c} {v:.1f}%" for c, v in zip(Mc.columns, sd_all * 100)))
    print(f"  component Sharpes net of 10 bps: " + ", ".join(
        f"{c} {s:+.2f}" for c, s in zip(Mc.columns, sh_all_sleeves)))
    print(f"  effective bets, EQUAL RISK weights: {eb_rp:.2f} of "
          f"{len(names) + 1}   (the alpha stack's failure was 1.02 of 4)")
    print(f"  risk shares by principal component (ascending eigenvalue): "
          f"{risk_shares}")
    print(f"  effective bets, the overlay's actual weights: {eb_actual:.2f}")
    print(f"  best LONG-ONLY risk-weighted Sharpe, SPY + ONE sleeve: "
          + ", ".join(f"{k} {v:+.3f}" for k, v in pair_best.items()))
    print(f"  => best {best_lo:+.3f} vs SPY alone {sh_all_sleeves[0]:+.3f} "
          f"(same sessions)")
    res["variants"].append("diagnostic:correlation_matrix")

    # COST SWEEP for every sleeve: the round-trip cost is the only free
    # parameter here, so the whole grid is re-priced across it rather than
    # quoted at one convenient number.
    sweep = {}
    for name, s in sleeves.items():
        if name == "cash":
            continue
        scal, kser = scaled_sleeve(s["r"], dates)
        avg_k = float(np.nanmean(np.abs(kser)) * PRIMARY_K)
        row = {}
        for c_bps in (0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0):
            rc = combine(spy, scal, PRIMARY_K)
            p_sl = describe(s["r"], spy, cost_yr=s["turnover"] * c_bps / 1e4)
            p_cb = describe(rc, spy, cost_yr=s["turnover"] * c_bps / 1e4 * avg_k)
            row[f"{c_bps:g}bps"] = dict(
                sleeve_sharpe=p_sl["sharpe"] if p_sl else float("nan"),
                combined_sharpe=p_cb["sharpe"] if p_cb else float("nan"),
                spy_same_sample=spy_on(rc))
            res["variants"].append(f"costsweep:{name}@{c_bps:g}bps")
        sweep[name] = row
    res["cost_sweep"] = sweep
    print("\n  COST SWEEP (round-trip bps -> sleeve Sharpe / combined Sharpe at "
          f"k={PRIMARY_K}):")
    print(f"  {'sleeve':14s} " + " ".join(f"{c:>15s}" for c in
                                          ("0bps", "1bps", "2bps", "5bps",
                                           "10bps", "20bps")))
    for name, row in sweep.items():
        cells = " ".join(f"{row[c]['sleeve_sharpe']:+6.2f}/"
                         f"{row[c]['combined_sharpe']:+6.2f} "
                         for c in ("0bps", "1bps", "2bps", "5bps", "10bps", "20bps"))
        print(f"  {name:14s} {cells}")

    # BEST CASE: give the sleeve its GROSS (pre-cost) return and re-combine.
    # If the book still loses to SPY gross, costs are not what killed it.
    gross = {}
    for name, s in sleeves.items():
        if name in ("cash",):
            continue
        scal, kser = scaled_sleeve(s["r"], dates)
        for k in (PRIMARY_K, 1.00):
            p = describe(combine(spy, scal, k), spy, cost_yr=0.0)
            if p:
                gross[f"{name}@k{k:.2f}"] = p
                res["variants"].append(f"combo_gross:{name}@k{k:.2f}")
    res["combos_gross"] = gross
    print("  GROSS (zero cost) best case, primary sleeve at k=0.50/1.00: "
          f"Sharpe {gross.get('mom_hedged@k0.50', {}).get('sharpe', float('nan')):+.3f} / "
          f"{gross.get('mom_hedged@k1.00', {}).get('sharpe', float('nan')):+.3f}"
          f"  vs SPY {spy_perf['sharpe']:+.3f}")

    # the pre-registered PRIMARY
    prim_key = f"mom_hedged@k{PRIMARY_K:.2f}"
    prim = combos.get(prim_key)
    res["primary_key"] = prim_key
    if prim:
        scal, kser = scaled_sleeve(sleeves["mom_hedged"]["r"], dates)
        r_prim = combine(spy, scal, PRIMARY_K)
        cy = sleeves["mom_hedged"]["turnover"] * COST_BPS / 1e4 * prim["avg_exposure"]
        res["primary"] = dict(
            perf=prim["perf"], eff=prim["eff"], diff_vs_spy=prim["diff_vs_spy"],
            halves=halves(r_prim, spy, cy), thirds=thirds(r_prim, spy, cy),
            cost20=describe(r_prim, spy,
                            cost_yr=sleeves["mom_hedged"]["turnover"]
                            * COST_BPS_HI / 1e4 * prim["avg_exposure"]),
            break_even=break_even_cost_bps(r_prim, spy,
                                           sleeves["mom_hedged"]["turnover"]
                                           * prim["avg_exposure"]))
        spy_scoped = describe(np.where(np.isfinite(r_prim), spy, np.nan), spy)
        spy_scoped["alpha"] = 0.0            # SPY on SPY: alpha is 0 by
        spy_scoped["t_alpha"] = 0.0          # construction, its t is FP noise
        res["primary"]["spy_same_sample"] = spy_scoped
        res["S_core_same_sample"] = spy_scoped["sharpe"]
        S_core = spy_scoped["sharpe"]        # frontier prices the SAME sample
        _hdr(f"4b. PRIMARY (pre-registered): {prim_key}")
        print(f"  combined  {_fmt(prim['perf'])}")
        print(f"  SPY (same sessions) {_fmt(spy_scoped)}")
        print(f"  SPY (full tape)     {_fmt(spy_perf)}")
        print(f"  halves Sharpe {res['primary']['halves']['H1']['sharpe']:+.3f} / "
              f"{res['primary']['halves']['H2']['sharpe']:+.3f}")
        print(f"  thirds Sharpe {res['primary']['thirds']['T1']['sharpe']:+.3f} / "
              f"{res['primary']['thirds']['T2']['sharpe']:+.3f} / "
              f"{res['primary']['thirds']['T3']['sharpe']:+.3f}")
        print(f"  RULE 13 on the DIFFERENCE (combined - SPY): "
              f"beta {prim['diff_vs_spy']['beta']:+.4f}  "
              f"alpha {prim['diff_vs_spy']['alpha']:+.3f}%/yr  "
              f"t {prim['diff_vs_spy']['t_alpha']:+.2f}")
        print(f"  break-even cost: {res['primary']['break_even']['ret']:+.1f} bps "
              f"(return) / {res['primary']['break_even']['sharpe']:+.1f} bps (Sharpe)")

        # Rule 16: bootstrap the Sharpe difference at several seeds
        boots = []
        for sd_ in BOOT_SEEDS:
            boots.append(B.sharpe_diff_boot(r_prim - cy / TD, spy, seed=sd_))
        res["primary"]["sharpe_test"] = dict(
            diff=boots[0]["diff"],
            p_gt0=[b["p_gt0"] for b in boots],
            lo=[b["lo"] for b in boots], hi=[b["hi"] for b in boots],
            mc_sd_p=float(np.std([b["p_gt0"] for b in boots], ddof=1)),
            mc_sd_lo=float(np.std([b["lo"] for b in boots], ddof=1)))
        print(f"  Sharpe(combined) - Sharpe(SPY) = "
              f"{boots[0]['diff']:+.4f}; block bootstrap P(>0) = "
              f"{[round(b['p_gt0'], 3) for b in boots]}  "
              f"(Rule 16 MC sd {res['primary']['sharpe_test']['mc_sd_p']:.4f})")
        res["primary"]["deflated_sharpe"] = G.deflated_sharpe(
            prim["perf"]["sharpe"] / math.sqrt(TD),
            n_trials=N_TRIALS_REGISTRY + len(res["variants"]),
            n_obs=int(prim["perf"]["n"]))
        print(f"  deflated Sharpe at N = {N_TRIALS_REGISTRY} + "
              f"{len(res['variants'])} trials: "
              f"{res['primary']['deflated_sharpe']:.3f}")

        # RULE 9: pool across ALL entry phases. `ladder` already averages the
        # 42 offsets, but the individual schedules are what Rule 9 asks for.
        sub = D["books"]["mom"]["sub"]
        ph = []
        for phase in range(STRIDE):
            rp = B.phase_ladder(sub, phase)
            rps = pd.Series(rp, index=dates)
            h = rolling_beta(rps, pd.Series(spy, index=dates)).clip(-2.0, 3.0)
            sl = (rps - h * pd.Series(spy, index=dates)).to_numpy()
            sc, _ = scaled_sleeve(sl, dates)
            pp = describe(combine(spy, sc, PRIMARY_K), spy, cost_yr=cy)
            if pp:
                ph.append(pp["sharpe"])
        res["primary"]["phase_sharpe"] = dict(
            n=len(ph), lo=float(min(ph)), hi=float(max(ph)),
            median=float(np.median(ph)),
            n_beating_spy=int(sum(1 for v in ph if v > spy_scoped["sharpe"])))
        print(f"  RULE 9, all {len(ph)} entry schedules: combined Sharpe "
              f"{min(ph):+.3f} .. {max(ph):+.3f} (median {np.median(ph):+.3f}); "
              f"{res['primary']['phase_sharpe']['n_beating_spy']} of {len(ph)} "
              f"beat SPY's {spy_scoped['sharpe']:+.3f}")
        res["variants"] += [f"phase:{i}" for i in range(len(ph))]

    # ---- 4c. the one cell that wins, attacked ----------------------------
    # The cost sweep shows exactly one construction beating SPY: the overnight
    # sleeve at ZERO cost. That is the cell a verifier will attack, so it is
    # attacked here first, at its most favourable setting.
    if "overnight" in sleeves:
        _hdr("4c. THE ONE CELL THAT WINS, ATTACKED: overnight sleeve at "
             "ZERO cost")
        on_raw = sleeves["overnight"]["raw"]
        hh = sleeves["overnight"]["h"]
        sc, _ = scaled_sleeve(sleeves["overnight"]["r"], dates)
        r0 = combine(spy, sc, PRIMARY_K)
        m0 = np.isfinite(r0)
        spy0 = np.where(m0, spy, np.nan)
        boots0 = [B.sharpe_diff_boot(r0, spy0, seed=s)
                  for s in BOOT_SEEDS + (20260812, 20260813)]
        att = dict(
            raw_overnight_ann_ret=ann(on_raw) * 100,
            raw_overnight_sharpe=sharpe(on_raw),
            h18_reported_ann_ret=9.54, h18_reported_sharpe=0.86,
            mean_hedge_ratio=float(np.nanmean(hh)),
            hedged_ann_ret=ann(sleeves["overnight"]["r"]) * 100,
            combined_sharpe=sharpe(r0[m0]), spy_same_sample=sharpe(spy0[m0]),
            sharpe_diff=boots0[0]["diff"],
            boot_p_gt0=[b["p_gt0"] for b in boots0],
            boot_ci=[[b["lo"], b["hi"]] for b in boots0],
            mc_sd_p=float(np.std([b["p_gt0"] for b in boots0], ddof=1)),
            deflated_sharpe=G.deflated_sharpe(
                sharpe(r0[m0]) / math.sqrt(TD),
                n_trials=N_TRIALS_REGISTRY + len(res["variants"]),
                n_obs=int(m0.sum())),
            combined_halves=halves(r0, spy0), combined_thirds=thirds(r0, spy0),
            sleeve_thirds=thirds(sleeves["overnight"]["r"], spy),
            break_even_cost_bps=res["sleeves"]["overnight"]["break_even_cost_bps"])
        res["overnight_attack"] = att
        res["variants"].append("attack:overnight_zero_cost")
        print(f"  CROSS-CHECK against H18, which measured this leg independently")
        print(f"    raw SPY overnight: {att['raw_overnight_ann_ret']:+.2f}%/yr, "
              f"Sharpe {att['raw_overnight_sharpe']:.3f}   "
              f"H18 reported +9.54%/yr, Sharpe 0.86")
        print(f"    mean hedge ratio h = {att['mean_hedge_ratio']:.4f}; hedging "
              f"away the beta cuts the return to "
              f"{att['hedged_ann_ret']:+.2f}%/yr")
        print(f"  AT ZERO COST: combined Sharpe {att['combined_sharpe']:.4f} vs "
              f"SPY {att['spy_same_sample']:.4f}  (diff {att['sharpe_diff']:+.4f})")
        print(f"    block bootstrap P(diff>0) = "
              f"{[round(p, 3) for p in att['boot_p_gt0']]}  "
              f"(Rule 16 MC sd {att['mc_sd_p']:.4f}); 95% CI "
              f"[{boots0[0]['lo']:+.3f}, {boots0[0]['hi']:+.3f}] STRADDLES ZERO")
        print(f"    deflated Sharpe: {att['deflated_sharpe']:.3f}")
        print(f"    sleeve equal THIRDS: "
              f"{att['sleeve_thirds']['T1']['ann_ret']:+.2f} / "
              f"{att['sleeve_thirds']['T2']['ann_ret']:+.2f} / "
              f"{att['sleeve_thirds']['T3']['ann_ret']:+.2f} %/yr "
              f"(t {att['sleeve_thirds']['T1']['t_alpha']:+.2f} / "
              f"{att['sleeve_thirds']['T2']['t_alpha']:+.2f} / "
              f"{att['sleeve_thirds']['T3']['t_alpha']:+.2f}) "
              f"- the MIDDLE third is negative")
        print(f"    break-even cost {att['break_even_cost_bps']:+.2f} bps round "
              f"trip, against this repo's 5-10 bps large-cap band and H18's own "
              f"3.88 bps unhedged measurement.")

    # ---- 5. the risk layer ----------------------------------------------
    _hdr("5. RISK LAYER - vol targeting off H20's 5-minute RV forecaster "
         "(SIZING ONLY)")
    riskl = {}
    lev = rv_leverage(dates, target_vol=float(spy_perf["ann_vol"]) / 100.0)
    if lev:
        span = lev.pop("_span")
        print(f"  5-minute RV panel spans {span[0]} .. {span[1]} "
              f"(SCOPED: the RV forecast does not exist before 2018)")
        base_r = spy if prim is None else r_prim
        base_cy = 0.0 if prim is None else cy
        for src, L in lev.items():
            m = np.isfinite(L) & np.isfinite(base_r)
            if m.sum() < 500:
                continue
            rl = np.where(m, L * base_r, np.nan)
            rs = np.where(m, L * spy, np.nan)          # same layer on the core
            # turnover of the vol-target overlay itself
            to_l = float(np.nansum(np.abs(np.diff(L[m]))) / m.sum() * TD)
            p = describe(rl, spy, cost_yr=base_cy + to_l * COST_BPS / 1e4)
            p_spy_scoped = describe(np.where(m, spy, np.nan), spy)
            p_base_scoped = describe(np.where(m, base_r, np.nan), spy,
                                     cost_yr=base_cy)
            p_spy_lev = describe(rs, spy, cost_yr=to_l * COST_BPS / 1e4)
            riskl[src] = dict(book=p, spy_scoped=p_spy_scoped,
                              base_scoped=p_base_scoped, spy_voltgt=p_spy_lev,
                              lev_turnover=to_l,
                              halves=halves(rl, spy, base_cy + to_l * COST_BPS / 1e4),
                              thirds=thirds(rl, spy, base_cy + to_l * COST_BPS / 1e4),
                              mean_leverage=float(np.nanmean(L[m])))
            res["variants"].append(f"voltarget:{src}")
            print(f"  {src:22s} book {_fmt(p)}")
            print(f"  {'':22s} mean leverage {np.nanmean(L[m]):.2f}x;  "
                  f"SPY vol-targeted with the same forecast: "
                  f"Sharpe {p_spy_lev['sharpe']:+.3f} "
                  f"(untargeted SPY, same sessions {p_spy_scoped['sharpe']:+.3f}; "
                  f"untargeted book {p_base_scoped['sharpe']:+.3f})")
        # the lag test H20 required of itself
        L = lev["har_log_rv"]
        Ll = np.concatenate([[np.nan], L[:-1]])
        m = np.isfinite(Ll) & np.isfinite(base_r)
        p_lag = describe(np.where(m, Ll * base_r, np.nan), spy, cost_yr=base_cy)
        riskl["har_log_rv_LAGGED"] = dict(book=p_lag)
        res["variants"].append("voltarget:har_log_rv_lagged")
        print(f"  H20's own tell - add ONE day of lag: Sharpe "
              f"{p_lag['sharpe']:+.3f} vs {riskl['har_log_rv']['book']['sharpe']:+.3f}"
              f"  (if lag IMPROVES it, the gain was noise)")
    else:
        print("  5-minute RV panel not present; risk layer skipped.")
    res["risk_layer"] = riskl

    # ---- 6. leverage -----------------------------------------------------
    _hdr(f"6. LEVERAGE - drawdown-constrained Kelly at a {DD_BUDGET:.0%} budget, "
         f"P(breach) = {DD_PROB:.0%}")
    res["leverage"] = {}
    for label, series, cyy in (("SPY", spy, 0.0),
                               ("primary combined", r_prim if prim else None, cy if prim else 0.0)):
        if series is None:
            continue
        kb = kelly_block(series - cyy / TD, spy)
        kc = kelly_causal(series - cyy / TD, spy)
        res["leverage"][label] = dict(in_sample=kb, causal=kc)
        res["variants"] += [f"kelly_insample:{label}", f"kelly_causal:{label}"]
        print(f"\n  {label}")
        print(f"    mu {kb['mu']:+.2f}%  sigma {kb['sigma']:.2f}%  "
              f"Sharpe {kb['sharpe']:+.3f}")
        print(f"    full Kelly L* = {kb['kelly_full']:.2f}x;  "
              f"drawdown-constrained fraction f = {kb['fraction']:.3f}  "
              f"=> L = {kb['leverage_uncapped']:.2f}x"
              f"{' (CAPPED at %.1fx)' % MAX_LEV if kb['capped'] else ''}")
        print(f"    IN-SAMPLE levered: realised peak-to-trough "
              f"{kb['realised_maxdd']:.2f}% against a {kb['dd_budget']:.0f}% "
              f"budget -> breach ratio {kb['dd_breach_ratio']:.2f}x")
        print(f"    CAUSAL (expanding mu,sigma ending t-1): "
              f"{_fmt(kc)}")
        print(f"      mean leverage {kc['mean_leverage']:.2f}x, "
              f"realised peak-to-trough {kc['realised_maxdd']:.2f}% "
              f"(breach ratio {kc['dd_breach_ratio']:.2f}x)")

    # ---- 7. the frontier -------------------------------------------------
    _hdr("7. THE FRONTIER - the size of the thing we do not have")
    fr = frontier(S_core)
    res["frontier"] = fr
    ranked_net, ranked_gross = [], []
    for name, rec in res["sleeves"].items():
        if name in ("shuffled", "cash"):     # a control and a tautology
            continue
        if np.isfinite(rec["net"]["sharpe"]):
            ranked_net.append((name, rec["net"]["sharpe"]))
        if np.isfinite(rec["gross"]["sharpe"]):
            ranked_gross.append((name, rec["gross"]["sharpe"],
                                 rec["gross"]["t_alpha"],
                                 rec["break_even_cost_bps"]))
    ranked_net.sort(key=lambda x: -x[1])
    ranked_gross.sort(key=lambda x: -x[1])
    res["sleeves_ranked_net"] = ranked_net
    res["sleeves_ranked_gross"] = ranked_gross
    print(f"  core Sharpe (SPY, net, same sample as the primary) = {S_core:.3f}")
    print(f"  MEASURED near-zero-beta sleeves, NET of 10 bps: "
          + ", ".join(f"{n} {s:+.3f}" for n, s in ranked_net))
    print(f"  ... and GROSS (alpha t, break-even bps): "
          + ", ".join(f"{n} {s:+.3f} (t {t:+.2f}, {b:+.2f}bps)"
                      for n, s, t, b in ranked_gross))
    print()
    print(f"  {'target':34s} {'rho':>6s} {'w_sleeve':>9s} "
          f"{'required sleeve Sharpe':>23s} {'= ann ret @10% vol':>19s}")
    for row in fr["rows"]:
        if row["rho"] != 0.0 or row["w_sleeve"] not in (0.20, 0.50):
            continue
        print(f"  {row['target']:34s} {row['rho']:+6.2f} {row['w_sleeve']:9.2f} "
              f"{row['required_sleeve_sharpe']:23.2f} "
              f"{row['required_ann_ret_at_10pct_vol']:18.1f}%")
    print("\n  how many MUTUALLY UNCORRELATED sleeves alongside the core:")
    for k, v in fr["n_uncorrelated_sleeves_needed"].items():
        print(f"    {k:52s} {v if v is not None else '>50'}")

    res["meta"]["n_variants"] = len(res["variants"])
    res["meta"]["runtime_s"] = round(time.time() - t_start, 1)
    res["meta"]["n_trials_registry_before"] = N_TRIALS_REGISTRY
    RESULTS.write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {RESULTS}   ({len(res['variants'])} variants, "
          f"{res['meta']['runtime_s']}s)")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ctrl-reps", type=int, default=60)
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    run(args)


if __name__ == "__main__":
    main()
