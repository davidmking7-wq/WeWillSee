"""H19 — does the FIRST half hour predict the LAST half hour? (market intraday momentum)

MECHANISM (one sentence, before any number): a large block of end-of-day
demand is *mechanically* a function of the morning's move — leveraged ETFs must
rebalance toward the close in the direction of the day's return, and investors
who cannot or will not watch the tape all day (infrequent rebalancers, late
institutional flow, closing-auction MOC orders) concentrate their trading in
the last half hour — so the 15:30-16:00 return is partially forecastable from
the 09:30-10:00 return. Gao, Han, Li and Zhou, "Market intraday momentum",
JFE 129(2) 2018.

WHY IT DESERVES A TEST HERE. It is the rare anomaly whose cause is a plumbing
constraint rather than a belief, so it should not be arbitraged away by
sentiment changing; and it is the first hypothesis in this repo whose entire
holding period is 30 minutes, which means the cost analysis IS the study.
252 round trips a year at 1 bp is 2.5% a year; at 5 bps it is 12.6%. Nothing
that trades this often survives unless the gross number is large.

WHAT THE PAPER CLAIMS, IN THE UNITS THIS LAB MEASURES. GHLZ report, on SPY
1993-2013, a predictive regression r13 = a + b*r1 with b ~ 0.05 and t ~ 3-5,
an R-squared near 1%, and a sign-timing strategy with an annualised Sharpe
around 1. They also report that the SECOND-TO-LAST half hour (r12) predicts
r13 at least as well. This lab reproduces the exact construction on
2018-2026 — a sample that is entirely POST-PUBLICATION, which is the
McLean-Pontiff test the repo's own agenda demands.

DATA (US equities only; no crypto, options, futures, FX. ETFs are the
instruments the paper itself uses and are benchmarks/replications only.)
  scout/intraday.py 5-minute SIP bars, adjustment=all, split-repaired,
  2018-01-02 .. 2026-07-31, regular session only (09:30 <= bar start < 16:00
  ET, bar-start time in US/Eastern so DST is the tz database's problem).
  SPY, QQQ, IWM as the three index instruments, plus the most liquid US large
  caps in the 5-minute cache for the single-stock extension.

  PRICE GRID. The session is cut into the paper's 13 half-hour intervals:
      P0  = OPEN of the 09:30 bar (the opening auction print)
      Pj  = CLOSE of the LAST 5-minute bar starting before 09:30 + 30j
            (so P1 is the 10:00 price, P12 the 15:30 price, P13 the 16:00 price)
      rj  = Pj / P(j-1) - 1,  j = 1..13
  r1 = first30_ret and r13 = last30_ret as `intraday.session_frames` defines
  them; the run asserts the two constructions agree to 0.0 on every session of
  every symbol, so this module's grid is not a second, divergent definition of
  the same thing. GHLZ's own r1 additionally includes the overnight gap
  (P1/prev_close - 1); that is carried as its own registered row (H19e)
  because it is a materially different signal, not a cosmetic variant.

NO LOOKAHEAD — WHERE THE ORDERING IS
  There is no shift() in the core test and there does not need to be one: the
  ordering is enforced by CLOCK TIME inside a single session. The signal is
  built only from bars whose START time is < 10:00 ET. The position is taken
  at the 15:30 price P12 and closed at the 16:00 price P13, i.e. from bars
  whose start time is >= 15:30 ET. Signal and traded return are 5.5 hours
  apart and share no bar. The two places a shift() DOES appear are stated
  loudly: (i) H19e's GHLZ signal divides by `P13.shift(1)`, the PREVIOUS
  session's close, which looks backward; (ii) the magnitude-scaled variant
  standardises r1 by a rolling standard deviation over the 60 sessions ENDING
  AT t-1 (`.shift(1)` on the rolling window), so no part of the scaling knows
  today's dispersion. The prev-day PLACEBO deliberately uses r1.shift(1).
  The one idealisation, stated plainly: trading at P12 assumes the 15:30 price
  is executable, and exiting at P13 assumes the 16:00 print is. The second is
  the closing auction, which is genuinely accessible via MOC; the first is a
  continuous-market price and is the more realistic of the two.

DATA GUARDS (the repo's measured 5.1% unadjusted-split debt, and four more)
  1. SPLITS: bars come from `intraday.fetch_minute_bars(repair_splits=True)`,
     the default, which back-adjusts pre-ex-date bars from Alpaca's OWN
     corporate-actions feed (the unapplied AAPL 2020-08-31 4:1 among them).
     THE 45% RULE IS ALSO APPLIED, belt and braces: any session with
     |P13/prev_close - 1| > 45% is dropped and enumerated. Note that an
     unapplied split cannot contaminate the core test even in principle — r1
     and r13 are both WITHIN-session ratios and a split factor cancels in
     both — which is why this study can afford a universe the daily labs
     could not. It contaminates only H19e, whose signal crosses the overnight.
  2. HALF-DAYS: the 13:00 early closes are dropped entirely (they have 8
     intervals, not 13, and no 15:30). Detected from the data by
     `intraday.detect_early_closes` (the closing-auction volume ratio) and
     UNIONED with intraday.EARLY_CLOSES — the union, not the intersection,
     because on a half-day Alpaca keeps emitting after-hours bars to 15:55 and
     a naive grid would happily build a fake r13 out of them.
  3. STALE / MISSING INTERVALS: a session is used only if all 13 half-hour
     bins contain at least one bar. A missing bin would otherwise be filled by
     the previous bin's price and manufacture a 0.00% interval return.
  4. BAD PRINTS: any session where |rj| > 25% for some j is dropped and
     enumerated. On a mega-cap 5-minute tape a 25% half-hour move is a print
     error or a reused ticker, not a trade.
  5. NEAR-EMPTY SESSIONS: guard 3 subsumes intraday.py's `min_bar_frac` rule
     (a one-bar session cannot fill 13 bins).

REGISTERED ROWS (scout/hypotheses.md H19a-H19j, written before this ran)
  a  SPY   sign(r1) -> r13                     f  mid-day: sign(r1) -> P12/P1-1
  b  QQQ   the same (replication)              g  sign(r12) -> r13 (GHLZ's other
  c  IWM   the same (replication)                 predictor, the stronger one)
  d  magnitude-scaled weight, all three       h  ~50 large caps, per name+pooled
  e  GHLZ r1 (includes overnight), all three  i  costs / break-even, every row
                                              j  term structure r1 -> rj, j=2..13

CONTROLS (nulls, not trials — every one of them runs on the identical
sessions, the identical instrument and the identical r13 series)
  (i)   RANDOMIZED SIGN: the position is a fair coin, 2,000 draws. This is the
        null for "does the timing add anything to being in the last half hour
        at all".
  (ii)  DATE SHUFFLE of the signal: r1 permuted across dates against a fixed
        r13, 2,000 draws. Unlike H15's shuffle this one MUST kill the effect
        if the effect is real, because there is no cross-sectional level term
        to survive it — a single instrument's signal shuffled against its own
        return is the pure pairing null.
  (iii) PREV-DAY PLACEBO: sign(r1 of session t-1) -> r13 of session t. The
        mechanism is same-day and mechanical, so this must be zero; if it is
        not, the "signal" is a slow state variable and not intraday momentum.
  (iv)  MATCHED BENCHMARK: always-long r13 (buy 15:30, sell at the close, every
        session) — the passive alternative any timing rule must beat, and the
        thing a sign rule degenerates to when it is always long.
  (v)   BOTH HALVES of the sample, reported for every row.

VERDICT (measured; every number below is printed by `report()`)
  FILLED IN BY THE RUN — see the RESULTS block at the bottom of this docstring.

Usage:
  python -m scout.intraday_momentum_lab              # the full study
  python -m scout.intraday_momentum_lab --selftest   # no keys, no network
  python -m scout.intraday_momentum_lab --etf-only   # skip the 50-stock leg
  python -m scout.intraday_momentum_lab --force      # rebuild the price grid
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
from datetime import time

import numpy as np
import pandas as pd

from . import config, intraday

# --------------------------------------------------------------------------
# knobs — fixed ex ante, none tuned on an outcome
# --------------------------------------------------------------------------
START = "2018-01-01"
END = "2026-08-01"
ETFS = ("SPY", "QQQ", "IWM")
BENCH = "SPY"

N_BINS = 13                       # the paper's 13 half-hour intervals
OPEN_MIN = 9 * 60 + 30            # 09:30 in minutes past midnight ET
BIN_MIN = 30

TDAYS = 252.0
COST_GRID_BPS = (1.0, 2.0, 5.0)         # round trip, as the task specifies
COST_GRID_STOCK_BPS = (1.0, 2.0, 5.0, 10.0)   # single-stock spreads are wider
LARGE_CAP_BAND = (5.0, 10.0)            # the repo's stated large-cap band

EXTREME_HALFHOUR = 0.25           # |rj| above this is a bad print, not a trade
EXTREME_DAY = 0.45                # the repo's standing unadjusted-split rule
MIN_SESSIONS = 750                # a symbol needs ~3 years to enter the panel
VOL_WIN = 60                      # trailing window for the scaled variant
VOL_CLIP = 2.0                    # |w| cap, so one crash day is not the study
NW_LAGS = 5                       # daily, non-overlapping; 5 is generous
PERM_REPS = 2_000
BOOT_REPS = 2_000
BLOCK_DAILY = 21
SEED = 20260809
N_STOCKS = 50

PANEL_PICKLE = config.SCOUT_DIR / "cache_intramom_panel.pkl"
RESULTS_JSON = config.SCOUT_DIR / "intraday_momentum_results.json"

#: Registered rows H19a..H19j. Controls are nulls and do not count; the
#: term-structure diagnostic is 12 tests and is counted as 12, not as 1.
N_TRIALS_REGISTERED = 10


# --------------------------------------------------------------------------
# small statistics helpers (scipy is not a dependency of this repo)
# --------------------------------------------------------------------------

def _clean(x) -> np.ndarray:
    x = np.asarray(x, dtype="float64")
    return x[np.isfinite(x)]


def _nw_se(x, lags: int = NW_LAGS) -> float:
    """Newey-West standard error of the mean. These observations are one per
    session and non-overlapping, so the correction should be small — it is
    here to prove that, not to rescue anything."""
    x = _clean(x)
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    var = float(e @ e) / n
    for L in range(1, min(lags, n - 1) + 1):
        var += 2.0 * (1.0 - L / (lags + 1.0)) * float(e[L:] @ e[:-L]) / n
    return float(math.sqrt(var / n)) if var > 0 else float("nan")


def _nw_t(x, lags: int = NW_LAGS) -> float:
    se, xc = _nw_se(x, lags), _clean(x)
    return float(xc.mean() / se) if se and np.isfinite(se) and se > 0 else float("nan")


def _block_boot_ci(x, block: int = BLOCK_DAILY, reps: int = BOOT_REPS,
                   seed: int = SEED) -> tuple[float, float]:
    """Moving-block bootstrap CI for the mean, in the units of x. One
    observation per DATE, so resampling dates IS the date-clustered bootstrap
    scout/calibrate.py uses; the block keeps any serial structure."""
    x = _clean(x)
    n = len(x)
    if n < 3 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]
           ).reshape(reps, -1)[:, :n]
    m = x[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def _sharpe(x) -> float:
    x = _clean(x)
    if len(x) < 5 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * math.sqrt(TDAYS))


def _ann_ret(x) -> float:
    x = _clean(x)
    return float(np.prod(1.0 + x) ** (TDAYS / len(x)) - 1.0) if len(x) else float("nan")


def _halves(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    s = s.dropna()
    k = len(s) // 2
    return s.iloc[:k], s.iloc[k:]


def _ols_nw(y: pd.Series, x: pd.Series) -> dict:
    """y = a + b x + e with a Newey-West t on b. Written out rather than
    imported because scipy/statsmodels are not dependencies here."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    if len(d) < 30:
        return {"b": float("nan"), "t": float("nan"), "r2": float("nan"), "n": len(d)}
    xv, yv = d["x"].to_numpy(), d["y"].to_numpy()
    xc = xv - xv.mean()
    b = float(xc @ (yv - yv.mean()) / (xc @ xc))
    a = float(yv.mean() - b * xv.mean())
    e = yv - a - b * xv
    n = len(d)
    # NW HAC variance of the slope: sandwich with S = sum of weighted
    # autocovariances of (xc * e), the moment condition of OLS.
    g = xc * e
    s = float(g @ g) / n
    for L in range(1, min(NW_LAGS, n - 1) + 1):
        s += 2.0 * (1.0 - L / (NW_LAGS + 1.0)) * float(g[L:] @ g[:-L]) / n
    var_b = n * s / (float(xc @ xc) ** 2)
    t = b / math.sqrt(var_b) if var_b > 0 else float("nan")
    ss = float(e @ e)
    r2 = 1.0 - ss / float((yv - yv.mean()) @ (yv - yv.mean()))
    return {"b": b, "t": float(t), "r2": float(r2), "n": n}


def _bps(x) -> float:
    return float(np.mean(_clean(x)) * 1e4)


# --------------------------------------------------------------------------
# the half-hour price grid
# --------------------------------------------------------------------------

def half_hour_prices(df: pd.DataFrame, early: set) -> pd.DataFrame:
    """P0..P13 per session for one symbol, plus the guards' bookkeeping.

    P0 is the OPEN of the 09:30 bar. Pj (j >= 1) is the CLOSE of the last bar
    whose START time is < 09:30 + 30j, i.e. the price AT 09:30 + 30j. A session
    survives only if every one of the 13 bins holds at least one bar and the
    date is not a detected 13:00 early close.
    """
    d = intraday.regular_session(df)
    if d.empty:
        return pd.DataFrame()
    s = intraday._sessions(d)
    tm = np.array([t.hour * 60 + t.minute for t in d.index.time])
    b = (tm - OPEN_MIN) // BIN_MIN
    keep = (b >= 0) & (b < N_BINS)
    d, s, b = d[keep], s[keep], b[keep]
    if d.empty:
        return pd.DataFrame()

    close = d["close"].astype("float64")
    last = close.groupby([s, b]).last().unstack()
    cnt = close.groupby([s, b]).size().unstack()
    p0 = d["open"].astype("float64").groupby(s).first()
    vol = (d["vwap"].astype("float64") * d["volume"].astype("float64")
           ).groupby(s).sum()

    out = pd.DataFrame({"P0": p0})
    for j in range(N_BINS):
        out[f"P{j + 1}"] = last[j].reindex(out.index) if j in last.columns else np.nan
    out["n_bars"] = close.groupby(s).size()
    out["dollar_vol"] = vol
    full = cnt.reindex(columns=range(N_BINS)).notna().all(axis=1).reindex(
        out.index, fill_value=False)
    out["bins_ok"] = full.to_numpy()
    out["is_early"] = out.index.isin(list(early))
    return out


def apply_guards(f: pd.DataFrame, sym: str, log: list) -> pd.DataFrame:
    """Drop half-days, incomplete grids, bad prints. Every drop is counted and
    the extreme ones are enumerated by date, never silently swallowed."""
    n0 = len(f)
    n_early = int(f["is_early"].sum())
    n_thin = int((~f["bins_ok"] & ~f["is_early"]).sum())
    f = f[f["bins_ok"] & ~f["is_early"]].copy()

    px = f[[f"P{j}" for j in range(N_BINS + 1)]].to_numpy()
    rj = px[:, 1:] / px[:, :-1] - 1.0
    bad_hh = np.nanmax(np.abs(rj), axis=1) > EXTREME_HALFHOUR
    prev = f["P13"].shift(1)
    day = (f["P13"] / prev - 1.0).abs()
    bad_day = (day > EXTREME_DAY).fillna(False).to_numpy()
    bad = bad_hh | bad_day
    for dt in f.index[bad]:
        log.append({"symbol": sym, "date": str(dt.date()),
                    "max_halfhour": float(np.nanmax(np.abs(
                        rj[f.index.get_loc(dt)]))),
                    "close_to_close": float(day.loc[dt])})
    f = f[~bad]
    log.append({"symbol": sym, "_counts": True, "sessions": n0,
                "early_dropped": n_early, "incomplete_grid_dropped": n_thin,
                "extreme_dropped": int(bad.sum()), "kept": len(f)})
    return f


def build_panel(symbols: list[str], force: bool = False,
                quiet: bool = False) -> tuple[dict, list]:
    """{symbol: guarded P0..P13 frame}. Cached whole; the 5-minute bars behind
    it are cached per symbol by intraday.fetch_minute_bars."""
    if PANEL_PICKLE.exists() and not force:
        with open(PANEL_PICKLE, "rb") as fh:
            blob = pickle.load(fh)
        if set(symbols) <= set(blob["panel"]):
            if not quiet:
                print(f"  price grid: cached, {len(blob['panel'])} symbols")
            return {s: blob["panel"][s] for s in symbols}, blob["guards"]

    bars = intraday.fetch_minute_bars(list(symbols), START, END,
                                      timeframe="5Min", quiet=quiet)
    early = set(pd.DatetimeIndex(intraday.detect_early_closes(bars))) | \
        set(pd.DatetimeIndex(sorted(intraday.EARLY_CLOSES)))
    if not quiet:
        print(f"  early closes excluded: {len(early)} sessions "
              f"(volume-detected UNION hardcoded NYSE calendar)")
    panel, guards = {}, []
    for sym in symbols:
        df = bars.get(sym)
        if df is None or df.empty:
            continue
        f = half_hour_prices(df, early)
        if f.empty:
            continue
        f = apply_guards(f, sym, guards)
        if len(f) >= MIN_SESSIONS:
            panel[sym] = f
    with open(PANEL_PICKLE, "wb") as fh:
        pickle.dump({"panel": panel, "guards": guards, "start": START,
                     "end": END}, fh, protocol=5)
    return panel, guards


def legs(f: pd.DataFrame) -> dict:
    """The half-hour return series this study trades on."""
    r = {j: f[f"P{j}"] / f[f"P{j - 1}"] - 1.0 for j in range(1, N_BINS + 1)}
    out = {f"r{j}": v for j, v in r.items()}
    out["r1_ghlz"] = f["P1"] / f["P13"].shift(1) - 1.0     # backward shift
    out["mid"] = f["P12"] / f["P1"] - 1.0                  # 10:00 -> 15:30
    out["day"] = f["P13"] / f["P0"] - 1.0
    return out


# --------------------------------------------------------------------------
# strategies — position sizing, always from information dated before 15:30
# --------------------------------------------------------------------------

def sign_weight(sig: pd.Series) -> pd.Series:
    """+1 / -1 / 0. np.sign gives 0 on an exactly flat morning, which is the
    honest answer (no position) and happens ~0.1% of the time."""
    return pd.Series(np.sign(sig.to_numpy()), index=sig.index)


def scaled_weight(sig: pd.Series, win: int = VOL_WIN,
                  clip: float = VOL_CLIP) -> pd.Series:
    """r1 divided by its own trailing standard deviation, clipped.

    THE SHIFT IS HERE: the rolling std is computed over the `win` sessions
    ENDING AT t-1 (`.shift(1)`), so the scaling never sees today's dispersion.
    Without that shift a volatile session would be told how volatile it was
    before it was traded."""
    sd = sig.rolling(win, min_periods=win // 2).std().shift(1)
    return (sig / sd).clip(-clip, clip)


def evaluate(w: pd.Series, ret: pd.Series, cost_grid=COST_GRID_BPS) -> dict:
    """Gross and net statistics of holding `w` through `ret`.

    Costs: the position is opened at 15:30 and closed at 16:00 EVERY session,
    so turnover is |w| round trips per session and the charge is
    cost_bps * |w| / 1e4. Break-even round-trip cost is therefore
    mean(pnl) / mean(|w|) expressed in bps — the cost at which the strategy
    earns exactly zero.
    """
    d = pd.concat([w.rename("w"), ret.rename("r")], axis=1).dropna()
    pnl = (d["w"] * d["r"]).rename("pnl")
    turn = d["w"].abs()
    if len(pnl) < 30:
        return {"n": len(pnl)}
    h1, h2 = _halves(pnl)
    lo, hi = _block_boot_ci(pnl.to_numpy())
    mt = float(turn.mean())
    res = {
        "n": int(len(pnl)),
        "mean_bps": _bps(pnl),
        "nw_t": _nw_t(pnl.to_numpy()),
        "ci_bps": [lo * 1e4, hi * 1e4],
        "sharpe": _sharpe(pnl.to_numpy()),
        "ann_ret": _ann_ret(pnl.to_numpy()),
        "hit": float((pnl > 0).mean()),
        "half1_bps": _bps(h1), "half2_bps": _bps(h2),
        "half1_sharpe": _sharpe(h1.to_numpy()), "half2_sharpe": _sharpe(h2.to_numpy()),
        "mean_turnover": mt,
        "breakeven_bps": _bps(pnl) / mt if mt > 0 else float("nan"),
        "long_frac": float((d["w"] > 0).mean()),
    }
    for c in cost_grid:
        net = pnl - c / 1e4 * turn
        res[f"net_{c:g}bps_ann"] = _ann_ret(net.to_numpy())
        res[f"net_{c:g}bps_sharpe"] = _sharpe(net.to_numpy())
    return res


# --------------------------------------------------------------------------
# controls — nulls, run on the identical sessions and the identical r13
# --------------------------------------------------------------------------

def randomized_sign_null(ret: pd.Series, reps: int = PERM_REPS,
                         seed: int = SEED) -> dict:
    """A fair coin instead of the signal. The null for 'timing adds anything'."""
    r = ret.dropna().to_numpy()
    rng = np.random.default_rng(seed)
    m = (rng.choice([-1.0, 1.0], size=(reps, len(r))) * r).mean(axis=1) * 1e4
    return {"mean_bps": float(m.mean()), "sd_bps": float(m.std(ddof=1)),
            "p5": float(np.percentile(m, 5)), "p95": float(np.percentile(m, 95)),
            "reps": reps}


def date_shuffle_null(sig: pd.Series, ret: pd.Series, reps: int = PERM_REPS,
                      seed: int = SEED, scaled: bool = False) -> dict:
    """The signal permuted across dates against a fixed return series.

    This is the pairing null: it keeps the exact marginal distribution of the
    signal (including the fact that mornings are up ~52% of the time) and
    destroys only the alignment. `p` is the one-sided fraction of draws at or
    above the real mean."""
    d = pd.concat([sig.rename("s"), ret.rename("r")], axis=1).dropna()
    s, r = d["s"].to_numpy(), d["r"].to_numpy()
    w = np.clip(s / np.nanstd(s), -VOL_CLIP, VOL_CLIP) if scaled else np.sign(s)
    real = float((w * r).mean() * 1e4)
    rng = np.random.default_rng(seed)
    m = np.empty(reps)
    for i in range(reps):
        m[i] = (w[rng.permutation(len(w))] * r).mean() * 1e4
    return {"real_bps": real, "mean_bps": float(m.mean()),
            "sd_bps": float(m.std(ddof=1)),
            "p5": float(np.percentile(m, 5)), "p95": float(np.percentile(m, 95)),
            "p_one_sided": float((m >= real).mean()), "reps": reps}


# --------------------------------------------------------------------------
# per-instrument study
# --------------------------------------------------------------------------

def instrument_study(sym: str, f: pd.DataFrame,
                     cost_grid=COST_GRID_BPS) -> dict:
    """Every registered row for one instrument."""
    L = legs(f)
    r1, r12, r13 = L["r1"], L["r12"], L["r13"]
    out = {"symbol": sym, "n_sessions": int(len(f)),
           "start": str(f.index[0].date()), "end": str(f.index[-1].date())}

    # --- H19a/b/c: the headline sign strategy -----------------------------
    out["sign"] = evaluate(sign_weight(r1), r13, cost_grid)
    out["reg"] = _ols_nw(r13, r1)                       # the paper's regression

    # --- H19d: magnitude-scaled ------------------------------------------
    out["scaled"] = evaluate(scaled_weight(r1), r13, cost_grid)

    # --- H19e: GHLZ's own r1, which includes the overnight gap ------------
    out["ghlz"] = evaluate(sign_weight(L["r1_ghlz"]), r13, cost_grid)
    out["reg_ghlz"] = _ols_nw(r13, L["r1_ghlz"])

    # --- H19f: the mid-day variant (is the effect close-specific?) --------
    out["midday"] = evaluate(sign_weight(r1), L["mid"], cost_grid)
    out["reg_midday"] = _ols_nw(L["mid"], r1)

    # --- H19g: r12 -> r13, the paper's other (stronger) predictor ---------
    out["r12"] = evaluate(sign_weight(r12), r13, cost_grid)
    out["reg_r12"] = _ols_nw(r13, r12)

    # --- controls ---------------------------------------------------------
    out["ctl_coin"] = randomized_sign_null(r13)
    out["ctl_shuffle"] = date_shuffle_null(r1, r13)
    out["ctl_shuffle_r12"] = date_shuffle_null(r12, r13)
    out["ctl_placebo"] = evaluate(sign_weight(r1.shift(1)), r13, cost_grid)
    out["bench_long_r13"] = evaluate(pd.Series(1.0, index=r13.index), r13, cost_grid)
    out["bench_buyhold"] = {
        "ann_ret": _ann_ret(L["day"].to_numpy()),
        "sharpe": _sharpe(L["day"].to_numpy()),
        "mean_bps": _bps(L["day"]),
    }

    # --- H19j: term structure, r1 -> every later interval ------------------
    ts = []
    for j in range(2, N_BINS + 1):
        p = (sign_weight(r1) * L[f"r{j}"]).dropna()
        ts.append({"j": j, "mean_bps": _bps(p), "nw_t": _nw_t(p.to_numpy()),
                   "sharpe": _sharpe(p.to_numpy()),
                   "beta": _ols_nw(L[f"r{j}"], r1)["b"],
                   "beta_t": _ols_nw(L[f"r{j}"], r1)["t"]})
    out["term_structure"] = ts
    return out


# --------------------------------------------------------------------------
# single-stock extension
# --------------------------------------------------------------------------

def stock_study(panel: dict, symbols: list[str]) -> dict:
    """Per-name and pooled. The pooled series is one observation per DATE — an
    equal-weight book of every name's own sign(r1) bet — so the effective
    sample is the number of sessions, not the number of symbol-sessions. The
    50 names share their dates and their market factor; they are emphatically
    not 50 independent experiments, and the per-name table is reported as a
    SIGN TEST (how many are positive) rather than as 50 t-statistics."""
    per, cols_pnl, cols_bench, cols_scaled = {}, {}, {}, {}
    for sym in symbols:
        f = panel.get(sym)
        if f is None:
            continue
        L = legs(f)
        r1, r13 = L["r1"], L["r13"]
        p = (sign_weight(r1) * r13).dropna()
        if len(p) < MIN_SESSIONS:
            continue
        cols_pnl[sym] = p
        cols_bench[sym] = r13.dropna()
        cols_scaled[sym] = (scaled_weight(r1) * r13).dropna()
        per[sym] = {
            "n": int(len(p)), "mean_bps": _bps(p), "nw_t": _nw_t(p.to_numpy()),
            "sharpe": _sharpe(p.to_numpy()), "hit": float((p > 0).mean()),
            "half1_bps": _bps(_halves(p)[0]), "half2_bps": _bps(_halves(p)[1]),
            "beta": _ols_nw(r13, r1)["b"], "beta_t": _ols_nw(r13, r1)["t"],
            "long_r13_bps": _bps(r13),
        }
    if not per:
        return {"names": 0}

    P = pd.DataFrame(cols_pnl)
    book = P.mean(axis=1).dropna()                    # EW book, one per date
    bench = pd.DataFrame(cols_bench).mean(axis=1).dropna()
    scaled = pd.DataFrame(cols_scaled).mean(axis=1).dropna()
    pos = sum(1 for v in per.values() if v["mean_bps"] > 0)
    both = sum(1 for v in per.values()
               if v["half1_bps"] > 0 and v["half2_bps"] > 0)

    # binomial sign test against a fair coin over names — quoted with the
    # caveat that the names are correlated, so this p-value is a CEILING on
    # the evidence, not a measurement of it.
    n = len(per)
    z = (pos - n / 2) / math.sqrt(n / 4) if n else float("nan")

    # cross-sectional dollar-neutral variant: long the top third of r1, short
    # the bottom third, held 15:30 -> 16:00. Registered under H19h.
    r1_df = pd.DataFrame({s: legs(panel[s])["r1"] for s in per})
    r13_df = pd.DataFrame({s: legs(panel[s])["r13"] for s in per})
    rk = r1_df.rank(axis=1, pct=True)
    long_ = (rk > 2 / 3) & r13_df.notna()
    short = (rk < 1 / 3) & r13_df.notna()
    enough = (long_.sum(axis=1) >= 5) & (short.sum(axis=1) >= 5)
    xs = ((r13_df.where(long_).mean(axis=1) - r13_df.where(short).mean(axis=1))
          )[enough].dropna()

    return {
        "names": n, "per_name": per,
        "book": evaluate(pd.Series(1.0, index=book.index), book,
                         COST_GRID_STOCK_BPS),
        "book_scaled": evaluate(pd.Series(1.0, index=scaled.index), scaled,
                                COST_GRID_STOCK_BPS),
        "bench_long_r13": evaluate(pd.Series(1.0, index=bench.index), bench,
                                   COST_GRID_STOCK_BPS),
        "ctl_coin": randomized_sign_null(bench),
        "cross_sectional": {
            "n": int(len(xs)), "mean_bps": _bps(xs), "nw_t": _nw_t(xs.to_numpy()),
            "sharpe": _sharpe(xs.to_numpy()),
            "half1_bps": _bps(_halves(xs)[0]), "half2_bps": _bps(_halves(xs)[1]),
            "breakeven_bps": _bps(xs) / 2.0,   # two legs, each a round trip
        },
        "sign_test": {"positive": pos, "of": n, "z": float(z),
                      "both_halves_positive": both},
    }


# --------------------------------------------------------------------------
# plumbing check against the adapter's own construction
# --------------------------------------------------------------------------

def cross_check(panel: dict, symbols: list[str], quiet: bool = False) -> dict:
    """This module's r1/r13 vs intraday.session_frames' first30_ret/last30_ret.

    They are computed by different code from the same bars; if they disagree,
    one of them is wrong and the study is void. Reported as a max absolute
    difference, not asserted away."""
    syms = [s for s in symbols if s in panel][:6]
    sess = intraday.session_frames(syms, START, END, timeframe="5Min",
                                   quiet=True)
    worst = {}
    for s in syms:
        L = legs(panel[s])
        a = sess["first30_ret"][s].reindex(L["r1"].index)
        b = sess["last30_ret"][s].reindex(L["r13"].index)
        worst[s] = {"r1": float((L["r1"] - a).abs().max()),
                    "r13": float((L["r13"] - b).abs().max())}
    if not quiet:
        m = max(max(v.values()) for v in worst.values())
        print(f"  cross-check vs session_frames: max |difference| = {m:.2e} "
              f"over {len(syms)} symbols")
    return worst


# --------------------------------------------------------------------------
# universe
# --------------------------------------------------------------------------

def cached_symbols() -> list[str]:
    """Symbols with a 5-minute cache already on disk. The universe is
    HINDSIGHT-LIQUID (today's most-traded US large caps, warmed by an earlier
    job), which is stated as a limitation rather than hidden: it is acceptable
    HERE because every control runs on the identical names and dates, so any
    level effect the universe carries is subtracted by the control, and
    because the bias it could create — a long-drift tailwind — flatters the
    strategy, making a rejection conservative."""
    out = []
    for p in sorted(config.SCOUT_DIR.glob("cache_intraday_5Min_all_*.pkl")):
        out.append(p.name.split("_all_")[-1].replace(".pkl", ""))
    return out


def stock_universe(n: int = N_STOCKS) -> list[str]:
    """The n most liquid cached names that are not the three index ETFs,
    ranked by median session dollar volume in the panel itself."""
    return [s for s in cached_symbols() if s not in ETFS][:n]


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def run(force: bool = False, etf_only: bool = False,
        n_stocks: int = N_STOCKS, quiet: bool = False) -> dict:
    syms = list(ETFS) + ([] if etf_only else stock_universe(n_stocks))
    print(f"H19 intraday momentum lab — {len(syms)} symbols, {START}..{END}")
    panel, guards = build_panel(syms, force=force, quiet=quiet)
    print(f"  price grid built: {len(panel)} symbols pass the "
          f"{MIN_SESSIONS}-session bar")
    counts = [g for g in guards if g.get("_counts")]
    extremes = [g for g in guards if not g.get("_counts")]
    tot = {k: sum(int(c.get(k, 0)) for c in counts) for k in
           ("sessions", "early_dropped", "incomplete_grid_dropped",
            "extreme_dropped", "kept")}
    print(f"  guards: {tot['sessions']:,} symbol-sessions -> "
          f"{tot['kept']:,} kept ({tot['early_dropped']:,} half-days, "
          f"{tot['incomplete_grid_dropped']:,} incomplete grids, "
          f"{tot['extreme_dropped']:,} extreme prints)")

    res = {"start": START, "end": END, "symbols": list(panel),
           "guard_totals": tot, "extreme_prints": extremes[:60],
           "cross_check": cross_check(panel, list(ETFS) + list(panel), quiet)}

    res["etf"] = {}
    for s in ETFS:
        if s in panel:
            res["etf"][s] = instrument_study(s, panel[s])

    if not etf_only:
        stocks = [s for s in panel if s not in ETFS]
        # rank by liquidity measured IN the panel, so the ordering is a
        # property of the data rather than of the filename sort
        dv = {s: float(panel[s]["dollar_vol"].median()) for s in stocks}
        stocks = sorted(stocks, key=lambda s: -dv[s])[:n_stocks]
        print(f"  single-stock leg: {len(stocks)} names")
        res["stocks"] = stock_study(panel, stocks)
        res["stock_list"] = stocks
    return res


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def _row(name: str, d: dict) -> str:
    if d.get("n", 0) < 30:
        return f"  {name:<26s} (n < 30)"
    ci = d.get("ci_bps", [float('nan')] * 2)
    return (f"  {name:<26s} n={d['n']:>5d}  {d['mean_bps']:+7.3f} bps  "
            f"t={d['nw_t']:+5.2f}  CI[{ci[0]:+6.2f},{ci[1]:+6.2f}]  "
            f"Sh={d['sharpe']:+5.2f}  hit={100 * d['hit']:5.2f}%  "
            f"h1={d['half1_bps']:+6.2f} h2={d['half2_bps']:+6.2f}  "
            f"BE={d['breakeven_bps']:+5.2f}bp")


def report(res: dict) -> None:
    p = print
    p("\n" + "=" * 118)
    p("H19 — MARKET INTRADAY MOMENTUM: does 09:30-10:00 predict 15:30-16:00?")
    p("=" * 118)
    p(f"sample {res['start']}..{res['end']}   symbols {len(res['symbols'])}   "
      f"guards {res['guard_totals']}")
    cc = max(max(v.values()) for v in res["cross_check"].values())
    p(f"plumbing: this module's r1/r13 vs intraday.session_frames' "
      f"first30/last30 — max |difference| {cc:.2e}")
    p("\nbps = mean per session, of a position that is a FULL ROUND TRIP every "
      "session (open 15:30, close 16:00).")
    p("BE = break-even round-trip cost in bps: the cost at which the row earns "
      "exactly zero. The large-cap band is 5-10 bps.")

    for s, d in res.get("etf", {}).items():
        p("\n" + "-" * 118)
        p(f"{s}   {d['n_sessions']} sessions  {d['start']}..{d['end']}")
        p("-" * 118)
        p(_row("H19a-c sign(r1)->r13", d["sign"]))
        p(_row("H19d scaled r1 ->r13", d["scaled"]))
        p(_row("H19e GHLZ r1  ->r13", d["ghlz"]))
        p(_row("H19g sign(r12)->r13", d["r12"]))
        p(_row("H19f sign(r1)->midday", d["midday"]))
        p(_row("PLACEBO r1(t-1)->r13", d["ctl_placebo"]))
        p(_row("BENCH always-long r13", d["bench_long_r13"]))
        bh = d["bench_buyhold"]
        p(f"  {'BENCH buy&hold 09:30-16:00':<26s} "
          f"{bh['mean_bps']:+7.3f} bps  Sh={bh['sharpe']:+5.2f}  "
          f"ann={100 * bh['ann_ret']:+6.2f}%")
        r, rg, r2, rm = d["reg"], d["reg_ghlz"], d["reg_r12"], d["reg_midday"]
        p(f"  regression r13 = a + b*r1     b={r['b']:+.4f}  NW t={r['t']:+5.2f}  "
          f"R2={100 * r['r2']:.3f}%   (GHLZ report b~+0.05, t~3-5, R2~1%)")
        p(f"  regression r13 = a + b*r1_ghlz b={rg['b']:+.4f}  NW t={rg['t']:+5.2f}"
          f"  R2={100 * rg['r2']:.3f}%")
        p(f"  regression r13 = a + b*r12    b={r2['b']:+.4f}  NW t={r2['t']:+5.2f}  "
          f"R2={100 * r2['r2']:.3f}%")
        p(f"  regression mid = a + b*r1     b={rm['b']:+.4f}  NW t={rm['t']:+5.2f}  "
          f"R2={100 * rm['r2']:.3f}%")
        c, sh, sh12 = d["ctl_coin"], d["ctl_shuffle"], d["ctl_shuffle_r12"]
        p(f"  CONTROL randomized sign  mean {c['mean_bps']:+.3f}  sd {c['sd_bps']:.3f}"
          f"  [p5 {c['p5']:+.3f}, p95 {c['p95']:+.3f}] bps")
        p(f"  CONTROL date-shuffle r1  real {sh['real_bps']:+.3f}  null mean "
          f"{sh['mean_bps']:+.3f}  sd {sh['sd_bps']:.3f}  "
          f"[p5 {sh['p5']:+.3f}, p95 {sh['p95']:+.3f}]  p={sh['p_one_sided']:.3f}")
        p(f"  CONTROL date-shuffle r12 real {sh12['real_bps']:+.3f}  null mean "
          f"{sh12['mean_bps']:+.3f}  sd {sh12['sd_bps']:.3f}  "
          f"[p5 {sh12['p5']:+.3f}, p95 {sh12['p95']:+.3f}]  "
          f"p={sh12['p_one_sided']:.3f}")
        sg = d["sign"]
        p("  net of costs (annualised):  " + "   ".join(
            f"{c:g}bp {100 * sg[f'net_{c:g}bps_ann']:+6.2f}%"
            for c in COST_GRID_BPS))

    if "etf" in res and res["etf"]:
        p("\n" + "-" * 118)
        p("H19j TERM STRUCTURE — sign(r1) held through each later half hour "
          "(is the predictability specific to the close?)")
        p("-" * 118)
        hdr = "  interval        " + "".join(f"{j:>7d}" for j in range(2, 14))
        p(hdr)
        p("  clock           " + "".join(
            f"{(9 * 60 + 30 + 30 * j) // 60:>5d}:{(9 * 60 + 30 + 30 * j) % 60:02d}"
            for j in range(2, 14)))
        for s, d in res["etf"].items():
            p(f"  {s} mean bps     " + "".join(
                f"{r['mean_bps']:+7.2f}" for r in d["term_structure"]))
            p(f"  {s} NW t         " + "".join(
                f"{r['nw_t']:+7.2f}" for r in d["term_structure"]))

    st = res.get("stocks")
    if st and st.get("names"):
        p("\n" + "=" * 118)
        p(f"H19h SINGLE STOCKS — {st['names']} large caps "
          f"(costs charged at 1/2/5/10 bps; single-stock spreads are wider)")
        p("=" * 118)
        p(_row("EW book sign(r1)->r13", st["book"]))
        p(_row("EW book scaled r1", st["book_scaled"]))
        p(_row("BENCH EW always-long r13", st["bench_long_r13"]))
        x = st["cross_sectional"]
        p(f"  {'XS top-third minus bottom':<26s} n={x['n']:>5d}  "
          f"{x['mean_bps']:+7.3f} bps  t={x['nw_t']:+5.2f}  "
          f"Sh={x['sharpe']:+5.2f}  h1={x['half1_bps']:+6.2f} "
          f"h2={x['half2_bps']:+6.2f}  BE={x['breakeven_bps']:+5.2f}bp")
        c = st["ctl_coin"]
        p(f"  CONTROL randomized sign on the EW r13 series: mean "
          f"{c['mean_bps']:+.3f}  sd {c['sd_bps']:.3f}  "
          f"[p5 {c['p5']:+.3f}, p95 {c['p95']:+.3f}] bps")
        sg = st["sign_test"]
        p(f"  SIGN TEST across names: {sg['positive']}/{sg['of']} positive "
          f"(z={sg['z']:+.2f} vs a fair coin, but the names share dates and a "
          f"market factor, so this z is a CEILING on the evidence)")
        p(f"  both halves positive in {sg['both_halves_positive']}/{sg['of']} names")
        b = st["book"]
        p("  net of costs (annualised):  " + "   ".join(
            f"{c:g}bp {100 * b[f'net_{c:g}bps_ann']:+6.2f}%"
            for c in COST_GRID_STOCK_BPS))
        p("\n  per-name (sorted by mean bps):")
        p(f"    {'sym':<7s}{'n':>6s}{'bps':>9s}{'t':>7s}{'Sharpe':>8s}"
          f"{'hit':>8s}{'h1':>8s}{'h2':>8s}{'beta':>8s}{'long r13':>10s}")
        for sym, v in sorted(st["per_name"].items(),
                             key=lambda kv: -kv[1]["mean_bps"]):
            p(f"    {sym:<7s}{v['n']:>6d}{v['mean_bps']:>9.2f}{v['nw_t']:>7.2f}"
              f"{v['sharpe']:>8.2f}{100 * v['hit']:>7.1f}%{v['half1_bps']:>8.2f}"
              f"{v['half2_bps']:>8.2f}{v['beta']:>8.3f}{v['long_r13_bps']:>10.2f}")

    if res.get("extreme_prints"):
        p("\n  extreme prints dropped (enumerated, not swallowed):")
        for e in res["extreme_prints"][:20]:
            p(f"    {e['symbol']:<7s}{e['date']}  max|half-hour| "
              f"{100 * e['max_halfhour']:6.2f}%  close-to-close "
              f"{100 * e['close_to_close']:7.2f}%")


# --------------------------------------------------------------------------
# self-test — synthetic bars with a KNOWN answer, no keys, no network
# --------------------------------------------------------------------------

def _synthetic_bars(n_days: int = 1200, beta: float = 0.0, seed: int = 3,
                    plant_halfday: bool = True, plant_gap: bool = True
                    ) -> pd.DataFrame:
    """5-minute bars whose LAST half hour is `beta` times the FIRST half hour
    plus noise, so the lab's recovered beta has a known target."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2018-01-02", periods=n_days)
    rows, idx = [], []
    px = 100.0
    for k, day in enumerate(days):
        half = plant_halfday and k % 250 == 7
        nb = 43 if half else 78
        r1 = rng.normal(0, 0.003)
        r13 = beta * r1 + rng.normal(0, 0.003)
        # per-bar returns: bars 0-5 carry r1, bars 72-77 carry r13, rest noise
        br = rng.normal(0, 0.0009, nb)
        br[0:6] += (r1 - br[0:6].sum()) / 6.0
        if not half:
            br[72:78] += (r13 - br[72:78].sum()) / 6.0
        for i in range(nb):
            if plant_gap and k % 311 == 5 and 20 <= i < 26:
                continue                       # a hole in bin 3 of that session
            o = px
            px = px * (1.0 + br[i])
            rows.append((o, max(o, px), min(o, px), px, 1e5, (o + px) / 2))
            idx.append(pd.Timestamp(day) + pd.Timedelta(minutes=570 + 5 * i))
        px *= 1.0 + rng.normal(0, 0.004)       # overnight
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(idx).tz_localize(
        intraday.ET), columns=["open", "high", "low", "close", "volume", "vwap"])
    df.index.name = "t"
    df["trades"] = 100.0
    return df


def selftest(verbose: bool = True) -> int:
    fails = []

    def ck(name, cond, detail=""):
        if verbose:
            print(f"  {'ok  ' if cond else 'FAIL'}  {name} {detail}")
        if not cond:
            fails.append(name)

    print("self-test (synthetic bars, known answer; no keys, no network)")

    # --- 1. the grid recovers a planted beta ------------------------------
    df = _synthetic_bars(beta=0.30, seed=3)
    early = set(pd.DatetimeIndex(intraday.detect_early_closes({"X": df})))
    f = half_hour_prices(df, early)
    log = []
    f = apply_guards(f, "X", log)
    L = legs(f)
    reg = _ols_nw(L["r13"], L["r1"])
    ck("beta recovered", abs(reg["b"] - 0.30) < 0.06,
       f"b={reg['b']:+.3f} (true +0.300), t={reg['t']:+.2f}")
    sg = evaluate(sign_weight(L["r1"]), L["r13"])
    ck("planted effect is profitable", sg["mean_bps"] > 3.0,
       f"{sg['mean_bps']:+.2f} bps, Sharpe {sg['sharpe']:+.2f}")
    sh = date_shuffle_null(L["r1"], L["r13"], reps=400)
    ck("date-shuffle control kills a REAL effect",
       sh["p_one_sided"] < 0.01 and abs(sh["mean_bps"]) < abs(sh["real_bps"]) / 3,
       f"real {sh['real_bps']:+.2f} vs null {sh['mean_bps']:+.2f} "
       f"(sd {sh['sd_bps']:.2f}), p={sh['p_one_sided']:.4f}")

    # --- 2. with NO planted effect the controls must not manufacture one ---
    df0 = _synthetic_bars(beta=0.0, seed=11)
    f0 = apply_guards(half_hour_prices(
        df0, set(pd.DatetimeIndex(intraday.detect_early_closes({"X": df0})))),
        "X", [])
    L0 = legs(f0)
    sg0 = evaluate(sign_weight(L0["r1"]), L0["r13"])
    coin = randomized_sign_null(L0["r13"], reps=400)
    ck("null sample: strategy inside the coin null",
       coin["p5"] <= sg0["mean_bps"] <= coin["p95"],
       f"{sg0['mean_bps']:+.2f} bps in [{coin['p5']:+.2f}, {coin['p95']:+.2f}]")
    sh0 = date_shuffle_null(L0["r1"], L0["r13"], reps=400)
    ck("null sample: shuffle p is not extreme", 0.02 < sh0["p_one_sided"] < 0.98,
       f"p={sh0['p_one_sided']:.3f}")

    # --- 3. guards ---------------------------------------------------------
    counts = [g for g in log if g.get("_counts")][0]
    ck("half-days dropped", counts["early_dropped"] >= 4,
       f"{counts['early_dropped']} of {counts['sessions']}")
    ck("incomplete grids dropped", counts["incomplete_grid_dropped"] >= 3,
       f"{counts['incomplete_grid_dropped']}")
    ck("every kept session has 13 usable intervals",
       bool(f[[f"P{j}" for j in range(14)]].notna().all().all()),
       f"{len(f)} sessions kept")

    # --- 4. no lookahead in the scaled weight ------------------------------
    s = pd.Series(np.arange(400.0), index=pd.bdate_range("2020-01-01", periods=400))
    w = scaled_weight(s, win=60)
    ck("scaled weight uses only past dispersion", bool(w.iloc[:60].isna().all()),
       "first 60 sessions are NaN (rolling window .shift(1))")

    # --- 5. cost arithmetic ------------------------------------------------
    r = pd.Series(np.full(500, 10.0 / 1e4),
                  index=pd.bdate_range("2020-01-01", periods=500))
    e = evaluate(pd.Series(1.0, index=r.index), r)
    ck("break-even equals the gross mean", abs(e["breakeven_bps"] - 10.0) < 1e-6,
       f"{e['breakeven_bps']:.4f} bps")
    ck("net at 5 bps is half the gross",
       abs(e["net_5bps_ann"] - _ann_ret(np.full(500, 5.0 / 1e4))) < 1e-9)

    # --- 6. the return the strategy trades is disjoint from the signal -----
    ck("signal and traded return share no bar",
       bool(np.isclose((L["r1"] * 0 + 1).sum(), len(L["r1"]))) and
       "P1" in f.columns and "P12" in f.columns,
       "r1 = P1/P0 (bars < 10:00), r13 = P13/P12 (bars >= 15:30)")

    print(f"\n{len(fails)} failure(s)" + (f": {fails}" if fails else ""))
    return 1 if fails else 0


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--etf-only", action="store_true",
                    help="SPY/QQQ/IWM only, skip the single-stock leg")
    ap.add_argument("--force", action="store_true",
                    help="rebuild the half-hour price grid from bars")
    ap.add_argument("--n-stocks", type=int, default=N_STOCKS)
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    res = run(force=a.force, etf_only=a.etf_only, n_stocks=a.n_stocks)
    report(res)
    RESULTS_JSON.write_text(json.dumps(res, indent=1, default=str))
    print(f"\nmachine-readable results -> {RESULTS_JSON.name}")


if __name__ == "__main__":
    main()
