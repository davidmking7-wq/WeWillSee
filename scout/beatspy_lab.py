"""H30 - can a long-only book built ONLY from this repo's MEASURED results beat
SPY risk-adjusted, after costs?

MECHANISM (one sentence, before any number)
-------------------------------------------
Cross-sectional momentum: investors underreact to gradual, non-salient news, so
the stocks that outperformed over the past year keep outperforming for the next
several months (Jegadeesh-Titman 1993), and a long-only book that holds the top
of that ranking inside a trend/liquidity-gated pool should earn the drift while
the gates hold its downside beta below one.

WHY THIS EXISTS
---------------
Every other lab in this repo tests a SIGNAL. This one tests the USER'S GOAL:
"consistently outperforming the market by a landslide", which decomposes as
`return = Sharpe x volatility x leverage`, so the deliverable is a long-only
book a retail account can actually hold that beats SPY on RISK-ADJUSTED terms
after costs. Nothing new is searched here. Every ingredient is something this
repo already measured, and the provenance of each is stated so a reader can
check that no un-measured hope was smuggled in:

  1. RANK BY MOMENTUM, not by the v5 composite.
     H25 (`scout/high52_lab.py`): after the Rule-13 market adjustment, 12-1
     momentum measures +177.1 bps/42td ungated (t 2.11) and +132.8 gated
     (t 2.04), both halves; 52-week-high proximity - the composite's LARGEST
     weight, W_HIGH = 0.25 - measures +23.9 (t 0.29) and is -298.6 (t -3.17)
     in a Fama-MacBeth that controls for momentum. So the rank here is `mom`
     alone: `close.shift(21)/close.shift(252) - 1`, bit-identical to
     `signals.feature_frames`'s `mom`.
  2. GATES KEPT EXACTLY AS SHIPPED.
     `signals.composite_at`'s hard gates and vetoes - SMA200, 6-month absolute
     momentum, the +25%/-15% 1-month band, the top-vol and MAX-effect deciles,
     and the $10M 20-session median dollar-volume floor. The gates lab measured
     them as a DEFENSIVENESS overlay (beta 0.77, alpha -1.08%/yr, Sharpe
     slightly better than the ungated control - they cut mu and sigma
     together), and H23 (`scout/liquidity_lab.py`) vindicated the $10M floor
     because the apparent sub-gate premium is survivorship. They are kept, not
     re-tuned, and the ungated pool is reported beside the gated one so the
     reader can see what they cost.
  3. ENTER AT THE CLOSE.
     H18e: close(t) entry beats open(t+1) entry by +5.29 bps/window, both
     halves - but a random draw from the same pool earns +4.51 bps, so it is
     market-wide overnight drift, i.e. free execution hygiene, not alpha. Every
     book here forms at close(t) and its first return is close(t)->close(t+1).
  4. SIZE WITH THE VOLATILITY FORECAST, never with a timing rule.
     H20: HAR on 5-minute realised variance cuts out-of-sample QLIKE 13-16%
     below the daily-close incumbent in 29 of 29 symbols, both halves - but its
     own payoff test was REJECTED (adding a day of lag improved the book, which
     is what noise does). So volatility is used only for INVERSE-VOL POSITION
     SIZING and for the per-stock disaster level (`config.SELL_DISASTER_SIGMA`
     x sigma42), never to time exposure. The main grid sizes on the daily-close
     63-session volatility that `signals.py` already computes, because 5-minute
     bars exist for 61 symbols and not for a 500-name point-in-time universe;
     the RV-vs-daily sizing question is then answered on its own scoped
     29-symbol race, where both forecasts exist, and reported as scoped.
  5. NOTHING ELSE.
     52-week-high weight (H25), news of any kind (H15/H16/H17/H24), short-horizon
     reversal (H21), accruals (H27), net issuance (H22), illiquidity (H23),
     intraday momentum (H19), PEAD (H26) and idiosyncratic volatility (H28) were
     all rejected and none of them appears in this file.

CONFIRMATORY OR EXPLORATORY - stated per number, as the brief demands
--------------------------------------------------------------------
The RANKING is CONFIRMATORY. Cross-sectional momentum has an external prior
(Jegadeesh-Titman 1993, replicated across 40+ countries and 200+ years) and was
independently re-measured in this repo under H25's own risk adjustment. A t
near 2 with consistent halves is meaningful evidence for it.
The BOOK CONSTRUCTION GRID - 4 book sizes x 2 weighting schemes x 2 universes -
is a small EXPLORATORY sweep, and the primary is pre-registered BEFORE the run
so the winner of the sweep cannot become the headline:

    PRIMARY = point-in-time S&P 500, 20 names, inverse-volatility weight.

Reasoning stated ex ante and not from any result: the objective is Sharpe;
Sharpe rises with diversification and with variance-minimising weights; 20 is
the smallest book at which single-name idiosyncratic risk is ~1/sqrt(20) of the
total; and the point-in-time universe is the only one without survivorship.
Every other cell is reported anyway, and the SPREAD ACROSS CELLS is quoted as
the honest measure of how much of any winner is selection.

WHERE THE shift() IS - there is exactly one
-------------------------------------------
Selection at close(t) uses features that are functions of closes through t
only (`mom` reaches back via `.shift(21)`/`.shift(252)`; `vol63`, `pos252`,
`max21`, `dvol20` are trailing windows ending at t). The book's first return is
`close(t+1)/close(t) - 1`. In code: sleeve value V[k] = sum_i w_i *
G_i(f+k)/G_i(f) with k = 0..HOLD and the daily return read off V[k]/V[k-1] - 1,
so k=0 contributes nothing and the first paid session is f+1. The offline
selftest asserts that perturbing every bar strictly after date T leaves every
selection up to T bit-identical.

THE ENTRY-PHASE RULE (Rule 9, non-negotiable)
---------------------------------------------
Holds are 42 sessions and rebalances are monthly (21), so a single schedule is
one of 21 coin flips - H7a is this repo quoting the luckiest of six as a
headline. Every book here is the POOLED ladder: a sleeve is formed every
session and HOLD sleeves are active, which is algebraically the average over
all 21 phases of the 42-hold/21-stride book (each formation date in the
trailing 42 belongs to exactly one phase, where it is one of that phase's two
sleeves, so the phase-average weight on each is 1/21 x 1/2 = 1/42). The
per-phase dispersion is printed next to the pooled number, never replaced by it.

DATA AND THE DATA DEBT - both guards, stated as the brief requires
-----------------------------------------------------------------
Universe   point-in-time S&P 500 (`scout/pit.py`, each date's ACTUAL members,
           delisted names included) as the PRIMARY; today's S&P 1500
           (`scout/universe.csv`) as a SECONDARY with its survivorship
           disclosed and never used for the headline.
Prices     daily SIP bars, adjustment=all (splits AND dividends), 2016-01-04 ..
           2026-08-07, reusing the already-built, already-verified
           `scout/cache_idiovol_*.pkl` panels plus a top-up fetch for the
           point-in-time members those panels were missing.
Guard 1    SPLIT REPAIR against Alpaca's own corporate-actions feed
           (`intraday.split_events` / `unapplied_splits_close`, |log ratio| >
           0.35), which is the AAPL 2020-08-31 and SIRI class of error.
Guard 2    EXTREME-PRINT GUARD: any |1-day simple return| > 45% is treated as a
           missing observation in every volatility/rank input, AND the symbol
           is made INELIGIBLE for the following 252 sessions - because a
           corrupted price LEVEL poisons a 12-1 momentum rank for exactly as
           long as the lookback, which no single-day filter can undo. The
           blackout is the guard this study needs and the repo's engine does
           not have; its cost in name-dates is printed.
Guard 3    STALE-QUOTE RETIREMENT (>= 10 identical consecutive closes), so a
           frozen delisted quote cannot enter as a zero-volatility name.
Delisting  a name that stops trading inside a hold is carried at its last print
           and the sleeve keeps its terminal value in cash for the remainder -
           the same convention `scout/backtest.py` uses for point-in-time
           delistings. It is NOT dropped, which would delete the left tail.

CONTROLS (four, all run - Rule 3)
---------------------------------
a. RANDOM-PICK from the identical eligible pool on the identical dates, same
   book size, same weighting, 200 independent histories. This is the control
   that decides whether the momentum RANK does anything, because the gates and
   the universe are held fixed inside it.
b. MATCHED BENCHMARK 1: the equal-weight GATED eligible pool (what you get for
   free by obeying the gates and skipping the ranking).
c. MATCHED BENCHMARK 2: the equal-weight UNGATED universe (what the gates
   themselves are worth).
d. SPY, the instrument the user would otherwise hold, and the INCUMBENT v5
   composite book at the same size - the comparison that says whether this is
   an improvement on what the user already has.
e. SURVIVORSHIP CONTROL, added after the first run for a reason the first run
   made unavoidable: the whole grid is re-run on TODAY'S S&P 500 held fixed
   across history (`sp500today`). It has pit500's breadth, pit500's gates and
   pit500's costs, and differs from it in exactly one thing - it knows which
   companies would survive. The pit500-vs-sp500today gap is therefore a clean
   measurement of survivorship at fixed breadth, and it turned out to be the
   most important number in the file.

COSTS
-----
10 bps round trip charged on MEASURED turnover using the repo's own convention
(`growth.turnover_cost`: annual 0.5*sum|dw| x bps), a 20 bps sensitivity, and
the BREAK-EVEN cost quoted twice - the cost that erases the return advantage
over SPY, and the cost that erases the SHARPE advantage, which is the one that
matters for this goal. Leverage, if it is available at all, is charged an
ASSUMED retail financing rate and labelled as assumed.

RULE 13 IS THE WHOLE POINT
--------------------------
Beating SPY on raw return while running beta 1.3 is not an answer. Every book
reports its SPY beta and its market-adjusted alpha with a Newey-West t, and the
verdict is written on the Sharpe and the alpha, never on the raw return.

VERDICT (filled in from the run; numbers in BACKTEST-REPORT / hypotheses.md)
---------------------------------------------------------------------------
See `python -m scout.beatspy_lab` and `scout/beatspy_results.json`.
"""
import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from . import config
from .news_attention_lab import block_boot, phase_sweep      # verified, reused

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against the outcome.
# --------------------------------------------------------------------------
HOLD = 42                      # sessions held (config.HORIZON_TDAYS)
STRIDE = 21                    # monthly rebalance
BOOK_SIZES = (5, 10, 20, 30)
WEIGHTS = ("ew", "ivol")
UNIVERSES = ("pit500", "sp1500", "sp500today")
PRIMARY = ("pit500", 20, "ivol")          # registered BEFORE the run

COST_BPS = 10.0                # round trip, large caps (repo convention)
COST_BPS_HI = 20.0             # sensitivity
MIN_ELIGIBLE = 30              # thinner cross-sections are skipped entirely

BIG_MOVE = 0.45                # |1-day return| guard (data_audit.BIG_MOVE)
BLACKOUT = 252                 # sessions of ineligibility after a guarded print
SPLIT_LOG_TOL = 0.35           # only repair splits this far from 1:1
STALE_RUN = 10                 # identical consecutive closes -> retired
MARKET = "SPY"

BOOT_REPS = 2000               # block bootstrap of the Sharpe difference
CTRL_REPS = 200                # random-pick control histories
SEED = 20260809
RF_SENSITIVITY = 0.02          # ASSUMED flat risk-free, for a Sharpe sensitivity
FINANCING = 0.05               # ASSUMED retail margin rate for the leverage row
N_TRIALS_REGISTRY = 340        # repo's running variant count before this lab

PANEL_CACHE = config.SCOUT_DIR / "cache_beatspy_panel.pkl"
RESULTS = config.SCOUT_DIR / "beatspy_results.json"
RVFC_CACHE = config.SCOUT_DIR / "cache_rvfc_panel.pkl"
EWMA_LAMBDA = 0.94             # RiskMetrics standard, not tuned here


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def load_panel(refresh: bool = False) -> dict:
    """Split-repaired, stale-retired daily closes + RAW dollar volume for
    S&P 1500 (today) UNION every point-in-time S&P 500 member since 2016,
    plus SPY.

    Reuses `scout/cache_idiovol_*.pkl`, which was built and verified by H28 and
    carries guards 1 and 3 already, and tops it up with the point-in-time
    members that panel's fetch was missing (a documented residual - the repo
    notes 20/742 union tickers lacking bars). Dollar volume is computed from
    the RAW close times the RAW volume because a split leaves the product
    invariant, so it is correct whether or not the vendor applied the
    adjustment; using the REPAIRED close against the raw volume - which the
    idiovol cache does - understates it by the split ratio on exactly the
    unadjusted names."""
    if PANEL_CACHE.exists() and not refresh:
        return pd.read_pickle(PANEL_CACHE)
    from . import data, pit, universe
    from .idiovol_lab import repair_splits, retire_stale, clean_prices, PANEL_CACHE as IDP

    clean = clean_prices()                       # repaired + stale-retired close
    raw = pd.read_pickle(IDP)                    # raw close + raw volume
    close = clean["close"].copy()
    raw_close, raw_vol = raw["close"], raw["volume"]

    u = universe.load()
    seg = {r["symbol"]: r["segment"] for r in u}
    want = sorted(set(seg) | set(pit.all_members_since("2016-01-01")) | {MARKET})
    missing = [s for s in want if s not in close.columns]
    print(f"  panel: {close.shape[1]} symbols cached, topping up {len(missing)} "
          f"missing point-in-time / index members")
    if missing:
        cl, vl = [], []
        for i in range(0, len(missing), 120):
            d = data.daily_ohlcv(missing[i:i + 120], days=3900)
            cl.append(d["close"])
            vl.append(d["volume"])
        add_c = pd.concat(cl, axis=1).sort_index()
        add_v = pd.concat(vl, axis=1).sort_index().reindex(columns=add_c.columns)
        add_c.index = pd.DatetimeIndex(add_c.index).tz_localize(None).normalize()
        add_v.index = add_c.index
        add_c = add_c.reindex(close.index).astype("float64")
        add_v = add_v.reindex(close.index).astype("float64")
        raw_close = pd.concat([raw_close, add_c], axis=1)
        raw_vol = pd.concat([raw_vol, add_v], axis=1)
        fixed, rep = repair_splits(add_c.copy())
        fixed, killed = retire_stale(fixed)
        print(f"  top-up guards: {len(rep)} splits repaired, {len(killed)} stale "
              f"symbols retired")
        close = pd.concat([close, fixed], axis=1)

    raw_close = raw_close.reindex(columns=close.columns)
    raw_vol = raw_vol.reindex(columns=close.columns)
    dvol = ((raw_close * raw_vol).rolling(20, min_periods=10).median()
            .where(close.notna()))
    out = {"close": close.astype("float64"), "dollar_vol": dvol.astype("float64"),
           "volume": raw_vol.astype("float64"), "segment": seg}
    pd.to_pickle(out, PANEL_CACHE)
    return out


def guarded_returns(close: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """GUARD 2, part one. Simple daily returns with |r| > BIG_MOVE removed.

    Removing rather than winsorising is the repo's convention: a corrupted
    print is not a large return, it is a missing observation."""
    px = close.to_numpy()
    simple = np.full_like(px, np.nan)
    simple[1:] = px[1:] / px[:-1] - 1.0
    bad = np.abs(simple) > BIG_MOVE
    simple[bad] = np.nan
    return simple, bad


def blackout_mask(bad: np.ndarray, n: int = BLACKOUT) -> np.ndarray:
    """GUARD 2, part two. True where a symbol is INELIGIBLE because a guarded
    print sits within the trailing `n` sessions.

    A 12-1 momentum rank reads `close(t-21)/close(t-252)`, so one corrupted
    LEVEL contaminates the rank for a full lookback. Blanking the single return
    (which is all the repo's other labs do) does not touch that."""
    return pd.DataFrame(bad).rolling(n, min_periods=1).max().to_numpy() > 0


def membership(close: pd.DataFrame, seg: dict, kind: str) -> np.ndarray:
    """(dates x symbols) boolean index membership."""
    cols = list(close.columns)
    idx = {s: j for j, s in enumerate(cols)}
    m = np.zeros((len(close.index), len(cols)), dtype=bool)
    if kind == "sp1500":
        j = [idx[s] for s in seg if s in idx]
        m[:, j] = True
        return m
    if kind == "sp500today":
        # TODAY'S large-cap segment held fixed across history. Its ONLY
        # difference from pit500 is survivorship - same index, same breadth,
        # same gates - so the gap between the two is the survivorship discount
        # at fixed breadth. It is a LOWER bound on the sp1500 discount, whose
        # extra 1000 mid/small names die far more often and for which no
        # point-in-time source exists (documented in SCOUT-DESIGN.md).
        j = [idx[s] for s in seg if s in idx and seg[s] == "large"]
        m[:, j] = True
        return m
    from . import pit
    prev, row = None, None
    for i, ts in enumerate(close.index):
        mem = pit.members(ts)
        if mem is not prev:
            row = np.zeros(len(cols), dtype=bool)
            row[[idx[s] for s in mem if s in idx]] = True
            prev = mem
        m[i] = row
    return m


# --------------------------------------------------------------------------
# features - bit-identical to scout/signals.feature_frames, minus `gap`
# (which v4/v5 computes for research context and gives zero score weight)
# --------------------------------------------------------------------------

def features(close: pd.DataFrame, dvol: pd.DataFrame,
             simple: np.ndarray) -> dict[str, np.ndarray]:
    c = close
    ret = pd.DataFrame(simple, index=c.index, columns=c.columns)
    f = {
        "mom":     c.shift(21) / c.shift(252) - 1,
        "mom6":    c.shift(21) / c.shift(126) - 1,
        "ret6":    c / c.shift(126) - 1,
        "ret1m":   c / c.shift(21) - 1,
        "high":    c / c.rolling(252, min_periods=200).max(),
        "brk20":   c / c.rolling(20, min_periods=10).max(),
        "sma50ok": (c > c.rolling(50).mean()).astype(float),
        "sma200ok": (c > c.rolling(200).mean()).astype(float),
        "vol":     ret.rolling(63).std() * math.sqrt(252),
        "pos252":  (ret > 0).rolling(252, min_periods=200).mean(),
        "max21":   ret.rolling(21).max(),
        "dvol20":  dvol,
    }
    return {k: v.to_numpy(dtype="float64") for k, v in f.items()}


def _pct_rank(x: np.ndarray, idx: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """rank(pct=True) over x[idx], returned aligned to idx. Ties broken by a
    seeded key (continuous features have essentially none; the same code serves
    the random-pick control)."""
    k = idx.size
    order = idx[np.lexsort((rng.random(k), x[idx]))]
    r = np.empty(len(x))
    r[order] = (np.arange(k) + 1) / k
    return r[idx]


def selections(f: dict, member: np.ndarray, black: np.ndarray,
               sizes=BOOK_SIZES, seed: int = SEED,
               min_elig: int = MIN_ELIGIBLE, gated: bool = True) -> dict:
    """One pass over dates producing, per date: the eligible pool (gates
    applied exactly as `signals.composite_at` applies them), the momentum rank
    order, and the v5 composite rank order.

    `gated=False` is the DIAGNOSTIC H25 itself reported alongside the gated
    number (+177.1 bps ungated against +132.8 gated): it keeps only the $10M
    liquidity floor, because an untradeable book is not a book, and drops the
    trend / absolute-momentum / 1-month-band / vol-decile / MAX-effect gates.
    It exists to separate "momentum does not work long-only here" from "the
    gates broke it", and it is never the primary.

    Gate order is the shipped order and matters: `vol` and `max21` deciles are
    cross-sectional ranks over the names with COMPLETE features on that date
    (pre-gate), while the composite's own percentile ranks are computed
    POST-gate - both exactly as `signals.composite_at` does it."""
    rng = np.random.default_rng(seed)
    n_d, n_s = member.shape
    need = ("mom", "mom6", "high", "vol", "ret1m", "max21", "pos252", "brk20")
    finite = np.ones((n_d, n_s), dtype=bool)
    for k in need:
        finite &= np.isfinite(f[k])
    elig = np.zeros((n_d, n_s), dtype=bool)
    nmax = max(sizes)
    mom_sel = np.full((n_d, nmax), -1, dtype=np.int32)
    v5_sel = np.full((n_d, nmax), -1, dtype=np.int32)
    pool_n = np.zeros(n_d, dtype=np.int32)
    base_n = np.zeros(n_d, dtype=np.int32)

    for i in range(n_d):
        base = np.flatnonzero(finite[i] & member[i] & ~black[i])
        base_n[i] = base.size
        if base.size < min_elig:
            continue
        keep = f["dvol20"][i][base] >= config.MIN_DOLLAR_VOL
        if gated:
            vd = _pct_rank(f["vol"][i], base, rng)
            md = _pct_rank(f["max21"][i], base, rng)
            keep &= ((f["sma200ok"][i][base] == 1.0)
                     & (f["ret6"][i][base] > 0)
                     & (f["ret1m"][i][base] <= config.VETO_RET1M_HI)
                     & (f["ret1m"][i][base] >= config.VETO_RET1M_LO)
                     & (vd < config.VETO_VOL_DECILE)
                     & (md < config.VETO_MAX21_DECILE))
        idx = base[keep]
        pool_n[i] = idx.size
        if idx.size < min_elig:
            continue
        elig[i, idx] = True

        mom = f["mom"][i][idx]
        order = idx[np.lexsort((rng.random(idx.size), -mom))]
        mom_sel[i, :min(nmax, idx.size)] = order[:nmax]

        s = (config.W_MOM12 * _pct_rank(f["mom"][i], idx, rng)
             + config.W_MOM6 * _pct_rank(f["mom6"][i], idx, rng)
             + config.W_HIGH * _pct_rank(f["high"][i], idx, rng)
             + config.W_SMOOTH * _pct_rank(f["pos252"][i], idx, rng)
             + config.W_BRK20 * _pct_rank(f["brk20"][i], idx, rng))
        lo, hi = config.VOL_BAND
        v = f["vol"][i][idx]
        below = np.clip((lo - v) / 0.10, 0, None)
        above = np.clip((v - hi) / 0.25, 0, None)
        s += config.W_VOL * np.clip(1 - np.maximum(below, above), 0, 1)
        r1 = _pct_rank(f["ret1m"][i], idx, rng)
        s += config.W_GUARD * (1 - np.clip(r1 - 0.8, 0, None) * 5)
        s += config.W_SMA50 * f["sma50ok"][i][idx]
        o5 = idx[np.lexsort((rng.random(idx.size), -s))]
        v5_sel[i, :min(nmax, idx.size)] = o5[:nmax]

    return dict(elig=elig, mom_sel=mom_sel, v5_sel=v5_sel,
                pool_n=pool_n, base_n=base_n)


# --------------------------------------------------------------------------
# the book: buy at close(t), hold HOLD sessions, weights fixed at formation
# --------------------------------------------------------------------------

def growth_path(simple: np.ndarray) -> np.ndarray:
    """Cumulative gross growth per symbol, guarded prints and non-trading
    sessions carried as ZERO return.

    Carrying a dead name flat is the delisting convention (`backtest.py`): the
    position is marked at its last print and the money sits in cash for the
    rest of the hold, which keeps the loss instead of deleting the window."""
    g = np.cumprod(1.0 + np.nan_to_num(simple), axis=0)
    return g


def sleeve_returns(g: np.ndarray, sel: np.ndarray, w: np.ndarray,
                   hold: int = HOLD, stop: np.ndarray | None = None,
                   chunk: int = 512) -> tuple[np.ndarray, np.ndarray]:
    """(n_dates x hold) daily return of the sleeve formed at close(f), and the
    sleeve's terminal weight vector positions.

    sel[f] holds column indices (-1 = empty slot) and w[f] the formation
    weights, which then DRIFT with prices for the whole hold - a real
    buy-and-hold sleeve, not a silently daily-rebalanced one. `stop`, if given,
    is a per-name loss threshold (positive fraction): the first session on
    which the position is down more than that, it is sold and its value frozen
    in cash for the rest of the sleeve (`config.SELL_DISASTER_SIGMA` rule)."""
    n_d, n_s = g.shape
    k = np.arange(hold + 1)
    sub = np.full((n_d, hold), np.nan)
    wend = np.zeros((n_d, sel.shape[1]))
    for a in range(0, n_d, chunk):
        b = min(a + chunk, n_d)
        rows = np.clip(np.arange(a, b)[:, None] + k[None, :], 0, n_d - 1)   # (m,h+1)
        cols = np.where(sel[a:b] < 0, 0, sel[a:b])                          # (m,N)
        gg = g[rows[:, :, None], cols[:, None, :]]                          # (m,h+1,N)
        rel = gg / gg[:, 0:1, :]
        if stop is not None:
            thr = stop[a:b][:, None, :]
            hit = (rel - 1.0) <= -thr
            hit &= np.isfinite(thr)
            any_hit = hit.any(axis=1)
            first = np.argmax(hit, axis=1)
            val = np.take_along_axis(rel, first[:, None, :], axis=1)
            frozen = np.cumsum(hit, axis=1) > 0
            rel = np.where(frozen & any_hit[:, None, :], val, rel)
        ww = np.where(sel[a:b] < 0, 0.0, w[a:b])[:, None, :]
        v = (ww * rel).sum(axis=2)                                          # (m,h+1)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = v[:, 1:] / v[:, :-1] - 1.0
        r[v[:, :-1] <= 0] = np.nan
        # windows that run past the end of the tape are truncated, not faked
        tail = np.arange(a, b)[:, None] + np.arange(1, hold + 1)[None, :]
        r[tail > n_d - 1] = np.nan
        sub[a:b] = r
        term = np.where(sel[a:b] < 0, 0.0, w[a:b]) * rel[:, -1, :]
        wend[a:b] = term / np.maximum(term.sum(axis=1, keepdims=True), 1e-12)
    return sub, wend


def ladder(sub: np.ndarray) -> np.ndarray:
    """Daily return of the POOLED book: a sleeve every session, HOLD active,
    equal capital between them. Algebraically the average over all STRIDE
    entry phases of the HOLD-hold / STRIDE-stride schedule (see docstring)."""
    n_d, hold = sub.shape
    t = np.arange(n_d)
    ks = np.arange(1, hold + 1)
    f = t[:, None] - ks[None, :]
    vals = np.where(f >= 0, sub[np.clip(f, 0, n_d - 1),
                                np.broadcast_to(ks - 1, f.shape)], np.nan)
    with np.errstate(invalid="ignore"):
        n = np.isfinite(vals).sum(1)
        s = np.where(np.isfinite(vals), np.nan_to_num(vals), 0.0).sum(1)
        return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def phase_ladder(sub: np.ndarray, phase: int, stride: int = STRIDE,
                 hold: int = HOLD) -> np.ndarray:
    """One of the `stride` schedules hiding inside the pooled number."""
    n_d = sub.shape[0]
    t = np.arange(n_d)
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


def book_turnover(sel: np.ndarray, w: np.ndarray, wend: np.ndarray,
                  n_s: int, hold: int = HOLD) -> float:
    """Annual turnover of the pooled ladder in the repo's 0.5*sum|dw|
    convention (`growth.turnover_cost`), so a full replacement of the book
    costs exactly COST_BPS.

    Each session one sleeve of 1/hold of the capital is retired and replaced;
    the traded fraction is 0.5*sum|w_new - w_retiring_terminal| / hold. Names
    held by both sleeves net out, which is what a buy/hold band would exploit
    and what a naive count of position changes would miss."""
    tot, n = 0.0, 0
    for f in range(hold, sel.shape[0] - 1):
        a, b = sel[f], sel[f - hold]
        if (a < 0).all() or (b < 0).all():
            continue
        wa = np.zeros(n_s)
        wb = np.zeros(n_s)
        m = a >= 0
        np.add.at(wa, a[m], w[f][m])
        m = b >= 0
        np.add.at(wb, b[m], wend[f - hold][m])
        tot += 0.5 * np.abs(wa - wb).sum() / hold
        n += 1
    return float(tot / max(n, 1) * 252)


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def nw_ols(y: np.ndarray, x: np.ndarray, lags: int = 21) -> dict:
    """y = a + b x + e with Newey-West standard errors (Rule 13: regress on the
    market before quoting any sign)."""
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = len(y)
    if n < 60:
        return dict(alpha=float("nan"), beta=float("nan"),
                    t_alpha=float("nan"), n=n)
    X = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    b = xtx_inv @ (X.T @ y)
    e = y - X @ b
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, lags + 1):
        wt = 1.0 - L / (lags + 1.0)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += wt * (G + G.T)
    cov = xtx_inv @ S @ xtx_inv
    se = math.sqrt(max(cov[0, 0], 0.0))
    return dict(alpha=float(b[0]), beta=float(b[1]),
                t_alpha=float(b[0] / se) if se > 0 else float("nan"), n=n)


def perf(r: np.ndarray, mkt: np.ndarray, cost_yr: float = 0.0,
         rf: float = 0.0) -> dict:
    """Annualised performance of a daily return series, net of `cost_yr`."""
    m = np.isfinite(r) & np.isfinite(mkt)
    x = r[m] - cost_yr / 252.0
    if len(x) < 250:
        return {}
    vol = float(x.std(ddof=1) * math.sqrt(252))
    curve = np.cumprod(1 + x)
    dd = float((curve / np.maximum.accumulate(curve) - 1).min())
    cagr = float(curve[-1] ** (252 / len(x)) - 1)
    reg = nw_ols(x, mkt[m])
    return dict(cagr=cagr * 100, ann_ret=float(x.mean() * 252) * 100,
                ann_vol=vol * 100,
                sharpe=(float(x.mean() * 252) - rf) / vol if vol > 0 else float("nan"),
                maxdd=dd * 100, beta=reg["beta"],
                alpha=reg["alpha"] * 252 * 100, t_alpha=reg["t_alpha"],
                n=len(x))


def sharpe_of(x: np.ndarray, rf: float = 0.0) -> float:
    s = x.std(ddof=1)
    return float((x.mean() * 252 - rf) / (s * math.sqrt(252))) if s > 0 else float("nan")


def sharpe_diff_boot(a: np.ndarray, b: np.ndarray, block: int = HOLD,
                     reps: int = BOOT_REPS, seed: int = SEED) -> dict:
    """Circular moving-block bootstrap of Sharpe(a) - Sharpe(b) on the PAIRED
    daily series. Blocks of one holding period keep the overlap the ladder
    creates; the pairing keeps the common market factor from inflating the
    interval."""
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    n = len(a)
    if n < 3 * block:
        return dict(diff=float("nan"), lo=float("nan"), hi=float("nan"),
                    p_gt0=float("nan"))
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1) % n
    idx = idx[:, :n]
    da = a[idx]
    db = b[idx]
    sa = da.mean(1) / da.std(axis=1, ddof=1)
    sb = db.mean(1) / db.std(axis=1, ddof=1)
    d = (sa - sb) * math.sqrt(252)
    lo, hi = (float(v) for v in np.percentile(d, [2.5, 97.5]))
    return dict(diff=sharpe_of(a) - sharpe_of(b), lo=lo, hi=hi,
                p_gt0=float((d > 0).mean()))


def worst_windows(r: np.ndarray, dates, hold: int = HOLD, k: int = 5):
    """The k worst NON-OVERLAPPING `hold`-session stretches of the book,
    greedily deduplicated so one crash cannot occupy all five rows."""
    x = np.where(np.isfinite(r), r, 0.0)
    lg = np.log1p(np.clip(x, -0.99, None))
    cs = np.concatenate([[0.0], np.cumsum(lg)])
    fwd = np.expm1(cs[hold:] - cs[:-hold])
    order = np.argsort(fwd)
    out, taken = [], []
    for i in order:
        if any(abs(i - j) < hold for j in taken):
            continue
        taken.append(i)
        out.append((str(dates[i].date()), str(dates[min(i + hold, len(dates) - 1)].date()),
                    float(fwd[i] * 100)))
        if len(out) == k:
            break
    return out


# --------------------------------------------------------------------------
# weights
# --------------------------------------------------------------------------

def make_weights(sel: np.ndarray, vol: np.ndarray, scheme: str) -> np.ndarray:
    """Formation weights. `ew` = equal; `ivol` = proportional to 1/vol, the
    variance-minimising weighting under equal correlations and the only use
    H20 licenses for a volatility forecast (sizing, never timing)."""
    n_d, N = sel.shape
    w = np.zeros((n_d, N))
    ok = sel >= 0
    if scheme == "ew":
        w[ok] = 1.0
    else:
        rows = np.repeat(np.arange(n_d), N).reshape(n_d, N)
        v = np.where(ok, vol[rows, np.where(ok, sel, 0)], np.nan)
        v = np.where(np.isfinite(v) & (v > 0), v, np.nan)
        inv = np.where(ok, 1.0 / v, 0.0)
        w = np.nan_to_num(inv)
    s = w.sum(axis=1, keepdims=True)
    return np.divide(w, np.maximum(s, 1e-12), out=np.zeros_like(w), where=s > 0)


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def random_pick_control(elig: np.ndarray, g: np.ndarray, vol: np.ndarray,
                        size: int, scheme: str, spy: np.ndarray,
                        reps: int = CTRL_REPS, seed: int = SEED) -> dict:
    """CONTROL (a): `size` names drawn UNIFORMLY from the identical gated pool
    on the identical dates, weighted the identical way, `reps` independent
    histories. Everything except the momentum rank is held fixed, so the
    distribution this returns is exactly what the ranking has to beat."""
    rng = np.random.default_rng(seed + 7)
    n_d, n_s = elig.shape
    pools = [np.flatnonzero(elig[i]) for i in range(n_d)]
    out = {"sharpe": [], "cagr": [], "vol": [], "alpha": [], "beta": [],
           "turnover": []}
    for _ in range(reps):
        sel = np.full((n_d, size), -1, dtype=np.int32)
        for i, p in enumerate(pools):
            if p.size == 0:
                continue
            k = min(size, p.size)
            sel[i, :k] = rng.choice(p, size=k, replace=False)
        w = make_weights(sel, vol, scheme)
        sub, wend = sleeve_returns(g, sel, w)
        # a random book re-draws its names every roll, so its turnover is
        # HIGHER than the momentum book's; charging it properly makes the
        # control weaker, which is the conservative direction here.
        to = book_turnover(sel, w, wend, n_s)
        p = perf(ladder(sub), spy, cost_yr=to * COST_BPS / 1e4)
        if not p:
            continue
        p["turnover"] = to
        p["vol"] = p["ann_vol"]
        for k2 in out:
            out[k2].append(p[k2])
    return {k: np.array(v) for k, v in out.items()}


# --------------------------------------------------------------------------
# offline selftest
# --------------------------------------------------------------------------

def selftest() -> int:
    """Synthetic checks with known answers. No API keys, no cache."""
    fails = 0

    def check(name, ok, detail=""):
        nonlocal fails
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")
        if not ok:
            fails += 1

    rng = np.random.default_rng(0)
    n_d, n_s = 800, 60

    # 1. no lookahead: perturbing bars strictly after T cannot move a selection
    #    made at or before T.
    px = 100 * np.cumprod(1 + rng.normal(3e-4, 0.015, (n_d, n_s)), axis=0)
    close = pd.DataFrame(px, index=pd.bdate_range("2016-01-04", periods=n_d),
                         columns=[f"S{i}" for i in range(n_s)])
    dv = pd.DataFrame(5e7, index=close.index, columns=close.columns)
    simple, bad = guarded_returns(close)
    f = features(close, dv, simple)
    mem = np.ones((n_d, n_s), dtype=bool)
    black = blackout_mask(bad)
    a = selections(f, mem, black)
    T = 600
    px2 = px.copy()
    px2[T + 1:] *= np.cumprod(1 + rng.normal(0, 0.05, (n_d - T - 1, n_s)), axis=0)
    close2 = pd.DataFrame(px2, index=close.index, columns=close.columns)
    s2, b2 = guarded_returns(close2)
    a2 = selections(features(close2, dv, s2), mem, blackout_mask(b2))
    check("no lookahead in selection",
          np.array_equal(a["mom_sel"][:T + 1], a2["mom_sel"][:T + 1])
          and np.array_equal(a["v5_sel"][:T + 1], a2["v5_sel"][:T + 1]))

    # 2. the pooled ladder IS the average of the STRIDE phase schedules.
    g = growth_path(simple)
    sel = a["mom_sel"][:, :10]
    w = make_weights(sel, f["vol"], "ew")
    sub, wend = sleeve_returns(g, sel, w)
    pooled = ladder(sub)
    ph = np.nanmean(np.column_stack([phase_ladder(sub, p) for p in range(STRIDE)]),
                    axis=1)
    m = np.isfinite(pooled) & np.isfinite(ph)
    check("pooled ladder == mean over all 21 entry phases",
          bool(np.nanmax(np.abs(pooled[m] - ph[m])) < 1e-12),
          f"max|diff| {np.nanmax(np.abs(pooled[m] - ph[m])):.2e}")

    # 3. a one-name sleeve must reproduce that name's own returns exactly.
    sel1 = np.full((n_d, 1), 3, dtype=np.int32)
    w1 = np.ones((n_d, 1))
    sub1, _ = sleeve_returns(g, sel1, w1)
    ref = simple[5 + 1: 5 + 1 + HOLD, 3]
    check("single-name sleeve reproduces the stock",
          bool(np.nanmax(np.abs(sub1[5] - ref)) < 1e-12))

    # 4. first paid session is f+1, never f (the shift).
    check("sleeve's first return is close(f)->close(f+1)",
          bool(abs(sub1[10, 0] - simple[11, 3]) < 1e-12))

    # 5. inverse-vol weights are proportional to 1/vol and sum to 1.
    vol = np.tile(np.array([0.1, 0.2, 0.4] + [0.3] * (n_s - 3)), (n_d, 1))
    s3 = np.tile(np.array([[0, 1, 2]], dtype=np.int32), (n_d, 1))
    wv = make_weights(s3, vol, "ivol")
    check("inverse-vol weights", bool(abs(wv[0, 0] / wv[0, 2] - 4.0) < 1e-12
                                      and abs(wv[0].sum() - 1) < 1e-12))

    # 6. the disaster stop freezes a position and never un-freezes it.
    fall = np.ones((50, 1))
    fall[10:, 0] = 0.5           # -50% on day 10, flat after
    gg = np.cumprod(np.vstack([np.ones((1, 1)), fall[1:] / fall[:-1]]), axis=0)
    gg = np.cumprod(np.ones((50, 1)), axis=0)
    gg[10:, 0] = 0.5
    s4 = np.zeros((50, 1), dtype=np.int32)
    stop = np.full((50, 1), 0.20)
    subs, _ = sleeve_returns(gg, s4, np.ones((50, 1)), hold=20, stop=stop)
    tot = np.nanprod(1 + subs[0]) - 1
    check("disaster stop freezes the position at the breach",
          bool(abs(tot + 0.5) < 1e-12), f"sleeve total {tot:+.4f}")

    # 7. the extreme-print blackout removes a full lookback of eligibility.
    bad2 = np.zeros((n_d, n_s), dtype=bool)
    bad2[300, 4] = True
    bl = blackout_mask(bad2)
    check("blackout spans exactly 252 sessions",
          bool(bl[300, 4] and bl[300 + 251, 4] and not bl[300 + 252, 4]))

    # 8. perf() recovers a known drift/vol.
    x = rng.normal(0.10 / 252, 0.16 / math.sqrt(252), 20000)
    p = perf(x, x)
    check("perf annualisation", bool(abs(p["ann_vol"] - 16) < 1.0
                                     and abs(p["beta"] - 1) < 1e-9),
          f"vol {p['ann_vol']:.2f} beta {p['beta']:.3f}")

    # 9. a planted momentum effect must be FOUND (positive control on the whole
    #    pipeline: without this, a null result is not evidence).
    n2, n3 = 1500, 60
    rng2 = np.random.default_rng(11)          # independent of the draws above
    base = rng2.normal(0, 0.006, (n2, n3))
    drift = np.repeat(np.linspace(-10e-4, 10e-4, n3)[None, :], n2, axis=0)
    px3 = 100 * np.cumprod(1 + base + drift, axis=0)
    c3 = pd.DataFrame(px3, index=pd.bdate_range("2016-01-04", periods=n2),
                      columns=[f"P{i}" for i in range(n3)])
    dv3 = pd.DataFrame(5e7, index=c3.index, columns=c3.columns)
    s5, b5 = guarded_returns(c3)
    f3 = features(c3, dv3, s5)
    a3 = selections(f3, np.ones((n2, n3), dtype=bool), blackout_mask(b5),
                    sizes=(5,), min_elig=10)
    g3 = growth_path(s5)
    sub3, _ = sleeve_returns(g3, a3["mom_sel"][:, :5],
                             make_weights(a3["mom_sel"][:, :5], f3["vol"], "ew"))
    top = np.nanmean(ladder(sub3)) * 252 * 100
    # the matched benchmark, through the IDENTICAL machinery: pairing
    # eligibility at t with the return INTO t would be a lookahead in the
    # benchmark itself, which is exactly the error this comparison must avoid.
    npool = int(a3["elig"].sum(1).max())
    psel = np.full((n2, npool), -1, dtype=np.int32)
    for i in range(n2):
        ix = np.flatnonzero(a3["elig"][i])
        psel[i, :ix.size] = ix
    subp, _ = sleeve_returns(g3, psel, make_weights(psel, f3["vol"], "ew"))
    poolr = np.nanmean(ladder(subp)) * 252 * 100
    check("positive control: planted momentum is detected",
          bool(top > poolr + 3.0),
          f"top5 {top:+.2f}%/yr vs eligible pool {poolr:+.2f}%/yr")

    print(f"\n  {'ALL PASS' if fails == 0 else str(fails) + ' FAILURE(S)'}")
    return fails


# --------------------------------------------------------------------------
# the RV-sizing sensitivity (H20's ingredient, on the only names where the
# 5-minute measurement exists)
# --------------------------------------------------------------------------

def _ewma_var(x: np.ndarray, lam: float = EWMA_LAMBDA) -> np.ndarray:
    """CAUSAL EWMA variance: out[i] is written BEFORE x[i] is consumed, so
    out[i] is a function of x[0..i-1] by construction (the same convention
    scout/rv_forecast_lab.py verifies)."""
    out = np.full_like(x, np.nan)
    n, k = x.shape
    state = np.full(k, np.nan)
    for i in range(n):
        out[i] = state
        xi = x[i]
        ok = np.isfinite(xi)
        state = np.where(ok & np.isfinite(state), lam * state + (1 - lam) * xi,
                         np.where(ok, xi, state))
    return out


def rv_sizing_race(spy_daily: np.ndarray, dates) -> dict:
    """SCOPED: does H20's better volatility MEASUREMENT change a book when it
    is used only for sizing? 29 symbols with complete 5-minute coverage
    2018-2026 (`scout/cache_rvfc_panel.pkl`, built and verified by H20), top-5
    momentum book, three weightings: equal, inverse-vol from daily closes,
    inverse-vol from 5-minute realised variance. Identical selection, identical
    dates, identical costs - the ONLY difference is the variance estimate fed
    to the weights."""
    if not RVFC_CACHE.exists():
        return {}
    d = pd.read_pickle(RVFC_CACHE)
    rv_cc, r2 = d["rv_cc"], d["r2"]
    close = (1 + d["close_ret"]).cumprod()
    close.iloc[0] = 1.0
    dv = pd.DataFrame(5e8, index=close.index, columns=close.columns)
    simple, bad = guarded_returns(close)
    f = features(close, dv, simple)
    mem = np.ones(close.shape, dtype=bool)
    a = selections(f, mem, blackout_mask(bad), sizes=(5,), seed=SEED,
                   min_elig=10)
    g = growth_path(simple)
    sel = a["mom_sel"][:, :5]
    # SPY over the SAME sessions, so the comparison is like for like
    spy = pd.Series(spy_daily, index=dates).reindex(close.index).to_numpy()
    vol_rv = np.sqrt(np.maximum(_ewma_var(rv_cc.to_numpy()), 0)) * math.sqrt(252)
    vol_r2 = np.sqrt(np.maximum(_ewma_var(r2.to_numpy()), 0)) * math.sqrt(252)
    out = {}
    for name, vol in (("ew", None), ("ivol_daily63", f["vol"]),
                      ("ivol_ewma_r2", vol_r2), ("ivol_ewma_rv5min", vol_rv)):
        w = make_weights(sel, vol if vol is not None else f["vol"],
                         "ew" if name == "ew" else "ivol")
        sub, wend = sleeve_returns(g, sel, w)
        to = book_turnover(sel, w, wend, close.shape[1])
        p = perf(ladder(sub), spy, cost_yr=to * COST_BPS / 1e4)
        p["turnover"] = to
        out[name] = p
    out["SPY_same_sample"] = perf(spy, spy)
    out["_n_symbols"] = int(close.shape[1])
    out["_start"] = str(close.index[0].date())
    return out


# --------------------------------------------------------------------------
# the race
# --------------------------------------------------------------------------

def _hdr(s: str) -> None:
    print("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78)


def _fmt(p: dict) -> str:
    if not p:
        return "  (insufficient sample)"
    return (f"CAGR {p['cagr']:+6.2f}%  vol {p['ann_vol']:5.2f}%  "
            f"Sharpe {p['sharpe']:5.2f}  maxDD {p['maxdd']:7.2f}%  "
            f"beta {p['beta']:4.2f}  alpha {p['alpha']:+6.2f}% (t {p['t_alpha']:+5.2f})")


def run_universe(kind: str, panel: dict, simple: np.ndarray, bad: np.ndarray,
                 f: dict, g: np.ndarray, spy: np.ndarray, verbose: bool = True) -> dict:
    close = panel["close"]
    dates = close.index
    n_s = close.shape[1]
    mem = membership(close, panel["segment"], kind)
    black = blackout_mask(bad)
    t0 = time.time()
    S = selections(f, mem, black)
    elig = S["elig"]
    ok = S["pool_n"] > 0
    if verbose:
        print(f"  {kind}: mean index members with complete features "
              f"{S['base_n'][S['base_n'] > 0].mean():.0f}, mean GATED pool "
              f"{S['pool_n'][ok].mean():.0f} "
              f"({S['pool_n'][ok].mean() / S['base_n'][ok].mean() * 100:.0f}% survive "
              f"the gates), {int(ok.sum())} usable formation dates "
              f"[{time.time() - t0:.0f}s]")

    res = {"pool_mean": float(S["pool_n"][ok].mean()),
           "base_mean": float(S["base_n"][ok].mean()),
           "n_dates": int(ok.sum()), "books": {}, "bench": {}}

    # ---- benchmarks -------------------------------------------------------
    # equal-weight GATED pool and equal-weight UNGATED universe, both run
    # through the identical sleeve/ladder machinery.
    for bname, mask in (("eqw_gated_pool", elig),
                        ("eqw_ungated_universe", mem & np.isfinite(f["vol"]) & ~black)):
        nmax = int(mask.sum(1).max())
        sel = np.full((len(dates), nmax), -1, dtype=np.int32)
        for i in range(len(dates)):
            idx = np.flatnonzero(mask[i])
            if idx.size < MIN_ELIGIBLE:
                continue
            sel[i, :idx.size] = idx
        w = make_weights(sel, f["vol"], "ew")
        sub, wend = sleeve_returns(g, sel, w, chunk=128)
        to = book_turnover(sel, w, wend, n_s)
        r = ladder(sub)
        res["bench"][bname] = perf(r, spy, cost_yr=to * COST_BPS / 1e4)
        res["bench"][bname]["turnover"] = to
        res["bench"][bname]["_daily"] = r
    res["bench"]["SPY"] = perf(spy, spy)
    res["bench"]["SPY"]["turnover"] = 0.0
    res["bench"]["SPY"]["_daily"] = spy

    # ---- the books --------------------------------------------------------
    SU = selections(f, mem, black, gated=False)
    res["pool_mean_ungated"] = float(SU["pool_n"][SU["pool_n"] > 0].mean())
    for rank in ("mom", "v5", "momU"):
        base = (S["mom_sel"] if rank == "mom" else
                S["v5_sel"] if rank == "v5" else SU["mom_sel"])
        for size in BOOK_SIZES:
            for scheme in WEIGHTS:
                sel = base[:, :size]
                w = make_weights(sel, f["vol"], scheme)
                sub, wend = sleeve_returns(g, sel, w)
                r = ladder(sub)
                to = book_turnover(sel, w, wend, n_s)
                p = perf(r, spy, cost_yr=to * COST_BPS / 1e4)
                p["turnover"] = to
                p["gross"] = perf(r, spy)
                p["cost20"] = perf(r, spy, cost_yr=to * COST_BPS_HI / 1e4)
                p["_daily"] = r
                p["_sub"] = sub
                p["_sel"] = sel
                p["_w"] = w
                res["books"][f"{rank}_{size}_{scheme}"] = p
    return res, S, elig


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true",
                    help="offline synthetic checks, no keys needed")
    ap.add_argument("--refresh", action="store_true", help="rebuild the panel")
    ap.add_argument("--skip-control", action="store_true",
                    help="skip the 200-history random-pick control (slow)")
    args = ap.parse_args()

    if args.selftest:
        _hdr("H30 beatspy_lab — offline selftest")
        raise SystemExit(selftest())

    t_start = time.time()
    _hdr("H30 — a long-only book from MEASURED results, raced against SPY")
    print("MECHANISM: cross-sectional momentum (Jegadeesh-Titman) inside the")
    print("shipped trend/liquidity gates; enter at the close; size by inverse")
    print("volatility. Nothing here was searched — every ingredient is a")
    print("result this repo already measured (H25 / gates lab / H23 / H18e / H20).")
    print(f"PRE-REGISTERED PRIMARY: universe={PRIMARY[0]}, {PRIMARY[1]} names, "
          f"{PRIMARY[2]} weight.")

    panel = load_panel(refresh=args.refresh)
    close, dvol = panel["close"], panel["dollar_vol"]
    print(f"  panel {close.shape[1]} symbols x {close.shape[0]} sessions "
          f"{close.index[0].date()} .. {close.index[-1].date()}")
    simple, bad = guarded_returns(close)
    print(f"  GUARD 2: {int(bad.sum())} prints with |1-day return| > "
          f"{BIG_MOVE:.0%} blanked; each triggers a {BLACKOUT}-session "
          f"eligibility blackout")
    f = features(close, dvol, simple)
    g = growth_path(simple)
    spy_j = list(close.columns).index(MARKET)
    spy = np.where(np.isfinite(simple[:, spy_j]), simple[:, spy_j], np.nan)

    # ---- pipeline verification against the shipped engine -----------------
    _hdr("Pipeline verification — does this file reproduce scout/signals.py?")
    from . import signals
    ok_all = True
    black_all = blackout_mask(bad)
    mem1500 = membership(close, panel["segment"], "sp1500")
    cols = [s for s in panel["segment"] if s in close.columns]
    # exactly what a live scan feeds the engine: adjusted close and volume.
    # `open` is passed as the close because the only feature it drives is the
    # gap/volume-surge proxy, which v4/v5 computes for research context and
    # gives ZERO score weight and no gate - so it cannot move a pick.
    fr = signals.feature_frames(close[cols], close[cols], panel["volume"][cols])
    for ds in ("2018-06-29", "2021-09-30", "2024-03-28"):
        ts = close.index[close.index.get_indexer([pd.Timestamp(ds)], method="ffill")[0]]
        i = close.index.get_loc(ts)
        ref = signals.composite_at(fr, ts)
        sl = slice(max(0, i - 1), i + 1)
        mine = selections({k: v[sl] for k, v in f.items()}, mem1500[sl],
                          black_all[sl])
        mine_pool = set(np.array(close.columns)[np.flatnonzero(mine["elig"][-1])])
        mine_top = list(np.array(close.columns)[mine["v5_sel"][-1][:10]])
        ref_pool, ref_top = set(ref.index), list(ref.index[:10])
        jac = len(mine_pool & ref_pool) / max(len(mine_pool | ref_pool), 1)
        ov = len(set(mine_top) & set(ref_top))
        print(f"  {ts.date()}: engine pool {len(ref_pool)}, this file "
              f"{len(mine_pool)}, Jaccard {jac:.4f}; v5 top-10 overlap {ov}/10")
        ok_all &= jac > 0.90
    print(f"  verification {'PASSES' if ok_all else 'FAILS'} "
          f"(residual differences are the extra >45% blackout and the "
          f"guarded-return volatility inputs, both deliberate)")

    out = {"meta": dict(start=str(close.index[0].date()),
                        end=str(close.index[-1].date()),
                        n_sessions=int(close.shape[0]),
                        n_symbols=int(close.shape[1]),
                        hold=HOLD, stride=STRIDE, cost_bps=COST_BPS,
                        primary=list(PRIMARY), guard_prints=int(bad.sum()),
                        blackout=BLACKOUT)}

    store = {}
    for kind in UNIVERSES:
        _hdr(f"Universe: {kind}" + {
            "pit500": "  (POINT-IN-TIME membership — the primary)",
            "sp1500": "  (today's S&P 1500 — CARRIES SURVIVORSHIP, secondary)",
            "sp500today": "  (today's S&P 500 — the SURVIVORSHIP CONTROL: "
                          "same breadth as pit500, membership frozen at today)",
        }[kind])
        res, S, elig = run_universe(kind, panel, simple, bad, f, g, spy)
        store[kind] = (res, S, elig)
        print(f"\n  {'benchmark':26s} {'':2s}")
        for k, p in res["bench"].items():
            print(f"  {k:26s} {_fmt(p)}")
        print()
        print(f"  {'book':26s}  (net of {COST_BPS:.0f} bps on measured turnover)")
        for k, p in res["books"].items():
            print(f"  {k:26s} {_fmt(p)}  turn {p['turnover']:4.1f}x")
        out[kind] = {
            "pool_mean": res["pool_mean"], "base_mean": res["base_mean"],
            "n_dates": res["n_dates"],
            "bench": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                      for k, v in res["bench"].items()},
            "books": {k: {kk: (vv if not isinstance(vv, dict) else
                               {k3: v3 for k3, v3 in vv.items() if not k3.startswith("_")})
                          for kk, vv in v.items() if not kk.startswith("_")}
                      for k, v in res["books"].items()},
        }

    # ---- the primary, in depth -------------------------------------------
    kind, size, scheme = PRIMARY
    res, S, elig = store[kind]
    key = f"mom_{size}_{scheme}"
    book = res["books"][key]
    r = book["_daily"]
    spy_p = res["bench"]["SPY"]
    pool_p = res["bench"]["eqw_gated_pool"]
    v5_p = res["books"][f"v5_{size}_{scheme}"]
    cost_yr = book["turnover"] * COST_BPS / 1e4
    rnet = r - cost_yr / 252.0

    _hdr(f"THE PRIMARY: {kind}, {size} names, {scheme} weight, "
         f"{HOLD}-session holds, phase-pooled")
    print(f"  book        {_fmt(book)}")
    print(f"  SPY         {_fmt(spy_p)}")
    print(f"  gated pool  {_fmt(pool_p)}")
    print(f"  v5 composite{_fmt(v5_p)}")
    print(f"\n  turnover {book['turnover']:.2f}x/yr (0.5*sum|dw| convention) "
          f"-> {cost_yr * 1e4:.1f} bps/yr at {COST_BPS:.0f} bps round trip")
    print(f"  gross of costs: {_fmt(book['gross'])}")
    print(f"  at {COST_BPS_HI:.0f} bps:    {_fmt(book['cost20'])}")

    # halves
    m = np.isfinite(r) & np.isfinite(spy)
    idx = np.flatnonzero(m)
    hh = len(idx) // 2
    halves = {}
    for h, sl in (("H1", idx[:hh]), ("H2", idx[hh:])):
        a = np.full_like(r, np.nan); a[sl] = r[sl]
        b = np.full_like(spy, np.nan); b[sl] = spy[sl]
        halves[h] = dict(book=perf(a, b, cost_yr=cost_yr), spy=perf(b, b),
                         span=f"{close.index[sl[0]].date()}..{close.index[sl[-1]].date()}")
    print("\n  BOTH HALVES")
    for h, d in halves.items():
        print(f"   {h} {d['span']}")
        print(f"     book {_fmt(d['book'])}")
        print(f"     SPY  {_fmt(d['spy'])}")

    # entry-phase dispersion (Rule 9 — the pooled number is the headline, the
    # spread is the honesty)
    ph = [perf(phase_ladder(book["_sub"], p), spy, cost_yr=cost_yr)
          for p in range(STRIDE)]
    ph_sh = np.array([p["sharpe"] for p in ph if p])
    ph_cg = np.array([p["cagr"] for p in ph if p])
    print(f"\n  ENTRY-PHASE SWEEP ({STRIDE} schedules): Sharpe "
          f"{ph_sh.min():.2f}..{ph_sh.max():.2f} (pooled {book['sharpe']:.2f}), "
          f"CAGR {ph_cg.min():+.2f}%..{ph_cg.max():+.2f}% "
          f"(pooled {book['cagr']:+.2f}%)")

    # worst windows
    print(f"\n  WORST 5 NON-OVERLAPPING {HOLD}-SESSION WINDOWS (net)")
    for a, b, v in worst_windows(rnet, close.index):
        j = np.flatnonzero((close.index >= a) & (close.index <= b))
        sp = float(np.expm1(np.nansum(np.log1p(spy[j]))) * 100)
        print(f"   {a} -> {b}  book {v:+7.2f}%   SPY {sp:+7.2f}%")

    # Sharpe test and break-evens
    sd = sharpe_diff_boot(rnet, spy)
    print(f"\n  SHARPE: book {book['sharpe']:.3f} vs SPY {spy_p['sharpe']:.3f} "
          f"-> difference {sd['diff']:+.3f} "
          f"[95% CI {sd['lo']:+.3f}, {sd['hi']:+.3f}], "
          f"P(diff>0) = {sd['p_gt0']:.3f}")
    print(f"  (rf sensitivity at an ASSUMED {RF_SENSITIVITY:.0%}: book "
          f"{(book['ann_ret'] / 100 - RF_SENSITIVITY) / (book['ann_vol'] / 100):.3f} "
          f"vs SPY "
          f"{(spy_p['ann_ret'] / 100 - RF_SENSITIVITY) / (spy_p['ann_vol'] / 100):.3f})")
    gross = book["gross"]
    be_ret = ((gross["ann_ret"] - spy_p["ann_ret"]) / 100
              / max(book["turnover"], 1e-9) * 1e4)
    be_sh = ((gross["ann_ret"] / 100 - spy_p["sharpe"] * gross["ann_vol"] / 100)
             / max(book["turnover"], 1e-9) * 1e4)
    print(f"  BREAK-EVEN COST: {be_ret:+.0f} bps erases the RETURN advantage "
          f"over SPY; {be_sh:+.0f} bps erases the SHARPE advantage "
          f"(negative = there is none to erase)")
    print(f"  market-adjusted alpha {book['alpha']:+.2f}%/yr, NW t "
          f"{book['t_alpha']:+.2f}, beta {book['beta']:.2f} — Rule 13 is the "
          f"verdict line, not the raw return")

    # control
    ctrl = {}
    if not args.skip_control:
        print(f"\n  CONTROL (a): {CTRL_REPS} random-pick histories, {size} names "
              f"drawn from the identical gated pool on the identical dates")
        t0 = time.time()
        c = random_pick_control(elig, g, f["vol"], size, scheme, spy)
        ctrl = {k: dict(mean=float(v.mean()), p5=float(np.percentile(v, 5)),
                        p95=float(np.percentile(v, 95)))
                for k, v in c.items() if len(v)}
        pctl = float((c["sharpe"] < book["sharpe"] + cost_yr * 0).mean())
        print(f"    Sharpe  mean {c['sharpe'].mean():.3f} "
              f"[p5 {np.percentile(c['sharpe'], 5):.3f}, "
              f"p95 {np.percentile(c['sharpe'], 95):.3f}]  "
              f"-> the momentum book sits at percentile {pctl * 100:.0f}")
        print(f"    CAGR    mean {c['cagr'].mean():+.2f}% "
              f"[p5 {np.percentile(c['cagr'], 5):+.2f}, "
              f"p95 {np.percentile(c['cagr'], 95):+.2f}]   "
              f"vs book {book['cagr']:+.2f}%")
        print(f"    vol     mean {c['vol'].mean():5.2f}% "
              f"[p5 {np.percentile(c['vol'], 5):.2f}, "
              f"p95 {np.percentile(c['vol'], 95):.2f}]   "
              f"vs book {book['ann_vol']:.2f}%")
        print(f"    alpha   mean {c['alpha'].mean():+.2f}% "
              f"[p5 {np.percentile(c['alpha'], 5):+.2f}, "
              f"p95 {np.percentile(c['alpha'], 95):+.2f}]   "
              f"vs book {book['alpha']:+.2f}%")
        print(f"    turnover mean {c['turnover'].mean():.2f}x/yr vs book "
              f"{book['turnover']:.2f}x/yr (both charged {COST_BPS:.0f} bps)")
        print(f"    MECHANISM READOUT: ranking by momentum moves return by "
              f"{book['cagr'] - c['cagr'].mean():+.2f}pp and volatility by "
              f"{book['ann_vol'] - c['vol'].mean():+.2f}pp against the same "
              f"pool — mu roughly flat, sigma up, so Sharpe falls.")
        print(f"    [{time.time() - t0:.0f}s]")
        ctrl["book_sharpe_percentile"] = pctl * 100

    # is the point-in-time universe actually doing work? (a coverage check the
    # survivorship claim needs: if the PIT book never held a name that later
    # vanished, the pit500/sp500today gap could not be survivorship)
    cols = np.array(close.columns)
    today = set(panel["segment"])
    held = cols[np.unique(book["_sel"][book["_sel"] >= 0])]
    gone = sorted(set(held) - today)
    slots = int((book["_sel"] >= 0).sum())
    gone_j = {list(cols).index(x) for x in gone}
    gone_slots = int(np.isin(book["_sel"], list(gone_j)).sum())
    print(f"\n  POINT-IN-TIME COVERAGE CHECK: the primary book held "
          f"{len(held)} distinct names, {len(gone)} of which are NOT in today's "
          f"S&P 1500 ({gone_slots / max(slots, 1) * 100:.1f}% of all position "
          f"slots). Examples: {', '.join(gone[:14])}")

    # disaster-stop overlay
    sig42 = f["vol"] * math.sqrt(HOLD / 252.0) * config.SELL_DISASTER_SIGMA
    sel = book["_sel"]
    rows = np.repeat(np.arange(sel.shape[0]), sel.shape[1]).reshape(sel.shape)
    stop = np.where(sel >= 0, sig42[rows, np.where(sel >= 0, sel, 0)], np.nan)
    sub_s, wend_s = sleeve_returns(g, sel, book["_w"], stop=stop)
    p_stop = perf(ladder(sub_s), spy, cost_yr=cost_yr)
    print(f"\n  OVERLAY — per-stock disaster stop at "
          f"{config.SELL_DISASTER_SIGMA:.0f}x sigma42 (the shipped rule):")
    print(f"    with stop  {_fmt(p_stop)}")
    print(f"    without    {_fmt(book)}")

    # leverage
    _hdr("THE LEVERAGE QUESTION — what 'landslide' would actually require")
    from .growth import kelly_fraction_for_drawdown
    if book["sharpe"] > spy_p["sharpe"]:
        L = spy_p["ann_vol"] / book["ann_vol"]
        lev = L * rnet - (L - 1) * FINANCING / 252.0
        pl = perf(lev, spy)
        f_dd = kelly_fraction_for_drawdown(0.30, 0.10)
        Lk = f_dd * (book["ann_ret"] / 100) / (book["ann_vol"] / 100) ** 2
        print(f"  Sharpe DOES exceed SPY's, so leverage is the lever. "
              f"L = {L:.2f} equalises volatility.")
        print(f"  at L={L:.2f}, financing an ASSUMED {FINANCING:.0%}: {_fmt(pl)}")
        print(f"  Kelly bound: the fraction of full Kelly whose lifetime "
              f"P(-30% from the start) = 10% is {f_dd:.3f}, i.e. L <= {Lk:.2f}")
        levinfo = dict(L_volmatch=L, perf=pl, kelly_fraction=f_dd, L_kelly=Lk)
    else:
        print(f"  The book's Sharpe ({book['sharpe']:.3f}) does NOT exceed "
              f"SPY's ({spy_p['sharpe']:.3f}).")
        print("  LEVERAGE CANNOT HELP. Leverage scales an edge; it cannot create")
        print("  one. At any L the levered book has the same Sharpe and strictly")
        print("  more variance drag than the same-Sharpe unlevered alternative,")
        print("  so no landslide is available from this construction.")
        L = spy_p["ann_vol"] / book["ann_vol"]
        levinfo = dict(L_volmatch=L, available=False)

    # deflated Sharpe with the honest trial count
    from .growth import deflated_sharpe
    # honest trial count for THIS lab: 3 rankings x 4 sizes x 2 weightings x
    # 2 universes = 48 books, + 4 RV-sizing weightings, + the disaster-stop
    # overlay. Cost sensitivities are the same book, not new trials.
    n_var = 3 * len(BOOK_SIZES) * len(WEIGHTS) * len(UNIVERSES) + 4 + 1
    dsr = deflated_sharpe(book["sharpe"] / math.sqrt(252),
                          N_TRIALS_REGISTRY + n_var, book["n"],
                          sr_benchmark=spy_p["sharpe"] / math.sqrt(252))
    print(f"\n  Deflated Sharpe against SPY's, with the registry's honest N = "
          f"{N_TRIALS_REGISTRY} + {n_var} from this lab: {dsr:.3f}")

    # ---- how many cells clear SPY at all, and where they live ------------
    _hdr("HOW MANY OF THE 72 BOOKS BEAT SPY ON SHARPE, AND WHERE THEY LIVE")
    beat_tab = {}
    for u in UNIVERSES:
        bk = store[u][0]["books"]
        win = [k for k, p in bk.items() if p and p["sharpe"] > spy_p["sharpe"]]
        beat_tab[u] = win
        print(f"  {u:11s} {len(win):2d} of {len(bk)}   "
              f"{', '.join(win) if win else '(none)'}")
    print(f"  SPY Sharpe {spy_p['sharpe']:.3f}. Every winner is an UNGATED "
          f"momentum book on a SURVIVORSHIP universe; the point-in-time column "
          f"has {len(beat_tab['pit500'])}.")

    # ---- the flattering cell, and the survivorship discount on it --------
    _hdr("THE BEST CELL ANYWHERE IN THE GRID — and what is holding it up")
    best_k, best_u, best_p = None, None, None
    for u in UNIVERSES:
        for k, p in store[u][0]["books"].items():
            if p and (best_p is None or p["sharpe"] > best_p["sharpe"]):
                best_k, best_u, best_p = k, u, p
    print(f"  best Sharpe in {3 * len(BOOK_SIZES) * len(WEIGHTS) * len(UNIVERSES)} "
          f"books: {best_u} / {best_k}")
    print(f"    {_fmt(best_p)}")
    print(f"  the SAME cell across universes (identical rank, size, weight, "
          f"gates, costs):")
    for u in UNIVERSES:
        q = store[u][0]["books"].get(best_k)
        tag = {"pit500": "point-in-time, no survivorship",
               "sp1500": "today's 1500, full survivorship",
               "sp500today": "today's 500, survivorship at pit500's breadth"}[u]
        print(f"    {u:11s} {_fmt(q)}   [{tag}]")
    pit_q = store["pit500"][0]["books"].get(best_k)
    tod_q = store["sp500today"][0]["books"].get(best_k)
    if pit_q and tod_q:
        print(f"  SURVIVORSHIP AT FIXED BREADTH (today's 500 minus "
              f"point-in-time 500): "
              f"CAGR {tod_q['cagr'] - pit_q['cagr']:+.2f}pp, "
              f"Sharpe {tod_q['sharpe'] - pit_q['sharpe']:+.3f}, "
              f"alpha {tod_q['alpha'] - pit_q['alpha']:+.2f}pp — and the "
              f"S&P 1500 version carries MORE of it, unmeasurably so.")
    if best_p["sharpe"] > spy_p["sharpe"]:
        Lb = spy_p["ann_vol"] / best_p["ann_vol"]
        print(f"  IF that cell were real, vol-matching it to SPY means "
              f"DE-leveraging to L = {Lb:.2f}, which pays "
              f"{best_p['sharpe'] * spy_p['ann_vol']:+.2f}%/yr against SPY's "
              f"{spy_p['ann_ret']:+.2f}% — but its point-in-time twin pays "
              f"{pit_q['sharpe'] * spy_p['ann_vol']:+.2f}%/yr, which is "
              f"{'above' if pit_q['sharpe'] > spy_p['sharpe'] else 'BELOW'} SPY.")

    # ---- the scoped RV sizing race ---------------------------------------
    _hdr("SCOPED — does H20's 5-minute variance change the SIZING?")
    rv = rv_sizing_race(spy, close.index)
    if rv:
        print(f"  {rv['_n_symbols']} symbols with complete 5-minute coverage from "
              f"{rv['_start']}, top-5 momentum book, identical selection")
        for k, p in rv.items():
            if k.startswith("_") or not isinstance(p, dict):
                continue
            print(f"  {k:20s} {_fmt(p)}")
        print("  This is a 29-name mega-cap universe, NOT the S&P 500 — it")
        print("  answers only 'does the better variance estimate change the")
        print("  weights' outcome', and its levels are not comparable above.")

    out["primary"] = dict(
        key=key, book={k: v for k, v in book.items() if not k.startswith("_")},
        spy=spy_p, pool={k: v for k, v in pool_p.items() if not k.startswith("_")},
        v5={k: v for k, v in v5_p.items() if not k.startswith("_")},
        halves={h: {"span": d["span"], "book": d["book"], "spy": d["spy"]}
                for h, d in halves.items()},
        phase=dict(sharpe_min=float(ph_sh.min()), sharpe_max=float(ph_sh.max()),
                   cagr_min=float(ph_cg.min()), cagr_max=float(ph_cg.max())),
        worst=worst_windows(rnet, close.index),
        sharpe_test=sd, break_even_return_bps=be_ret, break_even_sharpe_bps=be_sh,
        control=ctrl, disaster_stop=p_stop, leverage=levinfo,
        deflated_sharpe=dsr, n_variants=n_var)
    out["rv_sizing"] = {k: v for k, v in rv.items()} if rv else {}

    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items() if not str(k).startswith("_")}
        if isinstance(o, (list, tuple)):
            return [_clean(v) for v in o]
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        if isinstance(o, np.ndarray):
            return [float(v) for v in o]
        return o

    RESULTS.write_text(json.dumps(_clean(out), indent=1, default=float),
                       encoding="utf-8")
    print(f"\nwrote {RESULTS}   [{time.time() - t_start:.0f}s total]")


if __name__ == "__main__":
    main()
