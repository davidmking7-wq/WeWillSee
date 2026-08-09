"""H20 — does 5-minute realized variance forecast next-day risk better than daily closes?

MECHANISM (one sentence, before any number): the variance of a day's return is
a SUM over the day, so adding up 78 squared 5-minute returns estimates it with
roughly 1/78th the estimator variance of the single squared daily return —
one draw of a random variable is a terrible estimate of its second moment, and
the intraday tape hands you 78 (Andersen-Bollerslev 1998; Corsi 2009 for the
HAR form; Patton 2011 for the loss functions used to score it).

WHY IT MATTERS HERE. Volatility targeting (H11) is the one thing in this
repo's alpha stack that half-worked: on SPY it cut maxDD from -34.0% to -27.3%
at matched vol, but the Sharpe uplift flipped across halves (1.03 vs 0.92,
then 0.56 vs 0.63) and it was NOT shipped. H11 was fed `growth.blended_vol`,
which sees only daily closes. If the FORECAST is the binding constraint, a
better one fixes it. If it is not, this lab closes the question on a
measurement instead of a hunch. This is the first row in the repo that scores
a RISK model rather than a return signal, so its primary loss is a forecast
loss, not a P&L.

DATA (US equities only — no crypto, options, futures, FX; SPY/QQQ/IWM would be
benchmarks only and the two index ETFs are not even used)
  scout/intraday.py 5-minute bars, regular session 09:30-16:00 ET (13:00 on
  detected half days), adjustment=all, per-symbol disk cache. Universe = every
  symbol in the pre-warmed cache with COMPLETE 2018-01-02..2026-07-31 coverage:
  28 US large caps plus SPY. GOOG dropped as a GOOGL dual-class duplicate;
  QQQ/IWM dropped as ETFs. The cache starts 2018-01-02, so this is 8.6 years
  against H11's 2016-2026 — LEVELS here are not comparable to the H11 table,
  only the differences between forecasters on this common sample are.

SPLIT / BAD-PRINT GUARD (the repo's documented 5.1% unadjusted-split debt)
  Two independent layers, both counted in the report:
   (1) `intraday.fetch_minute_bars(repair_splits=True)` back-adjusts every
       split Alpaca failed to apply, detected against Alpaca's own
       corporate-actions feed (this is the AAPL 2020-08-31 4:1 repair).
   (2) an explicit blank of any session with |close-to-close| > 45%, which is
       the guard this brief demanded for studies with no move veto. A variance
       study is the worst possible place for a fake -74% print: it would enter
       both the predictor and the target and manufacture "forecastability".
  The largest surviving |close_ret| and the largest surviving rv_5min are
  printed with their dates so a reader can check them by eye.

THE REALIZED MEASURES
  rv_oc[t] = rv_5min[t]^2                     open-to-close realized variance
  rv_cc[t] = rv_oc[t] + overnight_ret[t]^2    Hansen-Lunde (2005) naive sum
  r2[t]    = close_ret[t]^2                   the 1-observation daily proxy
  The target is CLOSE-TO-CLOSE variance because that is what a daily-rebalanced
  book actually bears, so `rv_cc` is the primary proxy and `r2` the second.
  Both are conditionally unbiased, and Patton (2011) proves QLIKE and MSE rank
  forecasts consistently under either — so a disagreement between them is
  itself a finding, which is why H20d is registered.

NO LOOKAHEAD — WHERE THE SHIFT IS
  Every forecaster returns `fc[t]` = the variance forecast FOR session t built
  only from sessions <= t-1:
    * the EWMA recursions write out[i] BEFORE consuming x[i], so out[i] is a
      function of x[0..i-1] by construction;
    * `blended_vol` is causal in `growth.py` already (its EWMA leg writes the
      forecast before the update and its rolling leg is `.shift(1)`-ed);
    * HAR builds features at t, targets `rv.shift(-1)`, and the prediction is
      `.shift(1)`-ed onto t+1 — THAT is the only forward alignment in this
      file. Its coefficients at t are fitted on pairs whose TARGET is already
      observed at t-1 (rows <= t-2), never on the row being predicted.
  Losses compare `fc[t]` against the proxy realized ON t. The vol-target book
  earns `L[t] * close_ret[t]` with `L[t] = clip(target/sqrt(252*fc[t]), 0, 2)`,
  settable at the close of t-1. `--extra-lag` reruns the whole payoff section
  with H11/`sleeve_lab`'s further `.shift(1)`, one day more conservative, so
  the two conventions can be compared.
  `--selftest` proves the no-lookahead claim mechanically: it truncates the
  input at a cut date, rebuilds every forecaster, and asserts the forecasts up
  to the cut are BIT-IDENTICAL to the full-sample ones. A forecaster that
  peeked would change.

REGISTERED ROWS (scout/hypotheses.md H20a-H20g, written before this ran)
  a  EWMA on 5-minute RV beats the incumbent `blended_vol` on QLIKE
  b  HAR beats EWMA-RV
  c  THE MECHANISM ROW: EWMA-RV beats EWMA on daily r^2 at the SAME lambda —
     without it, any RV win is just "a different estimator"
  d  the QLIKE ranking is proxy-invariant (Patton robustness)
  e  THE PAYOFF ROW: the better forecast makes SPY vol targeting work in BOTH
     halves — the condition H11 failed
  f  the matched-vol drawdown benefit survives the forecast swap
  g  costs: break-even round-trip must clear the 5-10 bps large-cap band

CONTROLS (nulls and benchmarks, not trials)
  (i)   DATE-SHUFFLE: rv_cc permuted across dates within each symbol, run
        through the identical EWMA. Skill must collapse to the unconditional
        benchmark. This is H15's lesson applied to a risk model.
  (ii)  NAIVE BENCHMARKS: `uncond` (expanding sample mean) and `rw_rv`
        (yesterday's RV). A model that cannot beat the expanding mean has
        measured nothing.
  (iii) CONSTANT-LEVERAGE control for the payoff row: the same book run at the
        CAUSAL expanding mean of the forecast's own leverage. It strips out
        timing and leaves average exposure. If it matches the targeted book,
        the forecast contributed nothing and only the leverage level did.
  (iv)  SHUFFLED-LEVERAGE null, 200 draws, mean AND SD quoted (Rule 10).
  (v)   MATCHED BENCHMARK: SPY buy-and-hold, plus a single-constant rescale of
        every levered series to SPY's realized vol before drawdowns are
        compared (Sharpe is invariant to that constant; drawdown is not).

STATISTICS. Losses are averaged across symbols WITHIN each date, so the unit
of observation is a DATE: symbols share days and their variances are one
common factor plus noise, and a row bootstrap would claim ~29x more
independence than exists. Newey-West t on the date series, a moving-block
bootstrap by date, the ratio of bootstrap SE to NW SE printed next to every
interval (Rule 14), n_eff from the variance ratio (as `calibrate.py` does),
and both halves for every row.

VERDICT (measured 2019-03-07..2026-07-31, 1,861 dates, 52,453 symbol-sessions;
every number below is reproduced by `python -m scout.rv_forecast_lab`)

  **THE FORECAST IS MUCH BETTER. THE PAYOFF DOES NOT FOLLOW.**

  H20a CONFIRMED. EWMA on 5-minute RV beats the incumbent `blended_vol` by
       -0.0424 QLIKE (NW t = -3.90, CI [-0.0735, -0.0224]), negative in both
       halves (-0.0627 / -0.0221), and it wins in 29 of 29 symbols.
  H20b CONFIRMED, and it is the largest effect in the file. HAR beats RV-EWMA
       by -0.0585 (t = -7.86, CI [-0.0758, -0.0430], both halves). Best model
       (`har_log`) against the incumbent: 0.3971 vs 0.4980 = **-20.3% of
       QLIKE, t = -6.46**, 29/29 symbols, and the MSE ordering agrees.
  H20c CONFIRMED — the mechanism is the MEASUREMENT, not the estimator.
       Identical EWMA at identical lambda: -0.0401 on RV versus daily r^2
       (t = -6.83, halves -0.0386 / -0.0415, n_eff 1192 of 1861 dates).
       The daily-r^2 EWMA beats the incumbent in only 17 of 29 names; the
       RV-fed one does in 29 of 29.
  H20d CONFIRMED. Spearman rank correlation between the two proxies'
       orderings = 1.000, same winner under both. Patton's robustness holds.
  CONTROL BEHAVES. Date-shuffled RV is WORSE than the expanding sample mean
       (+0.0583, t = +4.42) and loses to the real thing by -0.2395 (t = -3.28):
       destroying the timing destroys the skill, which is what H15 could not
       say about attention.

  H20e **REJECTED on SPY — the registered failure condition fires, exactly as
       it did for H11.** Best forecast: Sharpe 0.959 against buy-and-hold's
       0.863, but by halves **0.811 vs 0.601 then 1.109 vs 1.322** — better in
       the turbulent half, WORSE in the calm one, the same shape H11 recorded
       with the crude forecast. Every Sharpe difference against buy-and-hold
       (+0.023 / +0.063 / +0.096 / +0.098 across the four forecasts) has a
       bootstrap CI straddling zero, the widest [-0.285, +0.475], P(>0) = 0.53
       to 0.66, and every one sits inside the shuffled-leverage null (76th to
       90th percentile). A 20% better variance forecast bought a Sharpe
       difference that cannot be distinguished from permuted leverage.
       On the 28-name per-asset book the condition IS met — all four overlays
       beat the unlevered book in both halves — but it is met by the INCUMBENT
       too, and the BEST forecast makes the WORST book (har_log 1.432 against
       ewma_rv's 1.493 and blended's 1.444). The payoff is not ordered by
       forecast quality, which is the finding.
  H20f **HALF-CONFIRMED, SECOND CLAUSE REJECTED.** The matched-vol drawdown
       benefit on SPY is real and present under every forecast (-33.8% ->
       -25.2 / -27.7 / -26.7 / -27.0), and it is the only payoff quantity that
       clears its null (4th-12th percentile of the shuffled-leverage draws).
       But it does NOT get bigger with a better forecast — the crude daily
       incumbent produces the DEEPEST drawdown cut of the four, and on the
       per-asset book every overlay's matched drawdown is WORSE than the
       unlevered book's. Drawdown control comes from de-levering at all, not
       from de-levering accurately.
  H20g **FAILS FOR THE WINNER, PASSES FOR THE RUNNER-UP.** HAR re-levers
       constantly: 33.3x annual one-way turnover against EWMA-RV's 4.4x, for
       a break-even round-trip cost of **7.0 bps against the 10 bps bar**. At
       10 bps HAR's Sharpe falls to 0.823, BELOW buy-and-hold's 0.863, while
       cheap EWMA-RV holds 0.908 (break-even 34.5 bps). The best QLIKE model
       is the worst net-of-cost book — the exact trade-off this study was
       asked to check.

  THE TELL THAT SETTLES IT. Rerunning the payoff with H11's extra `.shift(1)`
  — one MORE day of staleness — RAISES the best book's Sharpe from 0.959 to
  1.044 and its second half from 1.109 to 1.249. A real timing edge degrades
  when you lag it. This one improves, which is what noise does.

  WHY THE GAIN IS BOUNDED. Only **59.9%** of close-to-close variance in this
  panel is open-to-close; the other 40% is the overnight gap, which no
  intraday tape can measure and which stays a one-observation-per-day estimate
  no matter how fine the bars are. That ceiling is measured, not assumed, and
  it is the honest reason a 78x better measurement of part of the problem buys
  20% of the loss rather than most of it.

RUN
  python -m scout.rv_forecast_lab                 # the full study
  python -m scout.rv_forecast_lab --selftest      # lookahead audit + positive control
  python -m scout.rv_forecast_lab --extra-lag     # H11/sleeve_lab timing convention
  python -m scout.rv_forecast_lab --official-close  # splice in auction closes (API)
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, growth as g, intraday

TD_YEAR = 252
CACHE = config.SCOUT_DIR / "cache_rvfc_panel.pkl"
RESULTS = config.SCOUT_DIR / "rv_forecast_results.json"

START = "2018-01-01"
END = "2026-08-01"

# Universe rule, stated as a rule so it cannot be a cherry-pick: every symbol
# in the pre-warmed 5-minute cache whose bars span the whole 2018-2026 window.
# GOOG is a GOOGL dual-class duplicate (same firm, same variance) and QQQ/IWM
# are ETFs, which this brief allows only as benchmarks — none are used.
STOCKS = ["AAPL", "AMAT", "AMD", "AMZN", "AVGO", "BRK.B", "COST", "CRM",
          "GOOGL", "INTC", "JNJ", "JPM", "LITE", "LLY", "LRCX", "META",
          "MSFT", "MU", "NFLX", "NVDA", "ORCL", "PG", "TSLA", "UNH", "V",
          "WDC", "WMT", "XOM"]
BENCH = "SPY"
SYMBOLS = [BENCH] + STOCKS

MAX_ABS_RET = 0.45      # the brief's explicit bad-print guard
WARMUP = 280            # positions dropped so every forecaster is warm
HAR_MIN_OBS = 252       # 1 year of pairs before HAR is allowed to speak
HAR_REFIT = 21          # walk-forward refit cadence, in sessions
LAMBDAS = (0.90, 0.94, 0.97)
TARGET_VOL = 0.12       # sleeve_lab's default, so the payoff row is comparable
ASSET_VOL = 0.30        # per-NAME target: near the median large-cap vol here,
                        # chosen so mean leverage sits near 1 and the cap can
                        # actually bind. Sharpe is invariant to this choice.
MAX_LEV = 2.0           # ALPHA-STACK's cap; the binding fraction is reported
BOOT_REPS = 1000
BLOCK = 21
NULL_DRAWS = 200
SEED = 20260809


# ==========================================================================
# 1. Panel
# ==========================================================================

def load_panel(use_cache: bool = True, official_close: bool = False,
               quiet: bool = False) -> dict:
    """Session-level frames for SYMBOLS, split-repaired and bad-print guarded.

    Returns {'close_ret', 'rv_oc', 'rv_cc', 'r2', 'overnight_ret', 'meta'}.
    Cached whole, because the 5-minute cache is 300MB and re-aggregating it
    costs a couple of minutes for a number that never changes.
    """
    key = f"{START}|{END}|{official_close}|{','.join(SYMBOLS)}|{MAX_ABS_RET}"
    if use_cache and CACHE.exists():
        try:
            with open(CACHE, "rb") as f:
                blob = pickle.load(f)
            if blob.get("key") == key:
                if not quiet:
                    print(f"  panel: cached ({blob['meta']['n_dates']} dates, "
                          f"{blob['meta']['n_symbols']} symbols)")
                return blob
        except Exception:
            pass

    sess = intraday.session_frames(SYMBOLS, START, END, timeframe="5Min",
                                   official_close=official_close, quiet=quiet)
    close_ret = sess["close_ret"].astype(float)
    on_ret = sess["overnight_ret"].astype(float)
    rv5 = sess["rv_5min"].astype(float)

    # ---- guard layer 2: blank any session with an implausible daily move.
    # Layer 1 (intraday.apply_split_repair) already ran inside session_frames.
    bad = close_ret.abs() > MAX_ABS_RET
    ri, ci = np.where(bad.to_numpy())
    bad_list = [(str(close_ret.index[i].date()), close_ret.columns[j],
                 round(float(close_ret.iat[i, j]), 4)) for i, j in zip(ri, ci)]
    for f in (close_ret, on_ret, rv5):
        f[bad] = np.nan
    # a blanked close also poisons the NEXT session's close-to-close return
    close_ret[bad.shift(1, fill_value=False)] = np.nan

    rv_oc = rv5 ** 2
    rv_cc = rv_oc + on_ret ** 2
    r2 = close_ret ** 2

    ext = (close_ret.abs().stack().sort_values(ascending=False).head(8)
           .rename("close_ret").reset_index())
    ext.columns = ["date", "symbol", "abs_close_ret"]
    rvx = (rv5.stack().sort_values(ascending=False).head(8)
           .rename("rv_5min").reset_index())
    rvx.columns = ["date", "symbol", "rv_5min"]

    meta = {"n_dates": int(len(close_ret)), "n_symbols": int(close_ret.shape[1]),
            "span": (str(close_ret.index[0].date()), str(close_ret.index[-1].date())),
            "blanked_extreme_sessions": int(bad.to_numpy().sum()),
            "blanked_list": bad_list,
            "largest_abs_close_ret": ext.to_dict("records"),
            "largest_rv_5min": rvx.to_dict("records"),
            "mean_rv_oc_over_rv_cc": float(
                (rv_oc.stack().mean()) / (rv_cc.stack().mean())),
            "built": datetime.now(timezone.utc).isoformat()}

    blob = {"key": key, "close_ret": close_ret, "overnight_ret": on_ret,
            "rv_oc": rv_oc, "rv_cc": rv_cc, "r2": r2, "meta": meta}
    if use_cache:
        with open(CACHE, "wb") as f:
            pickle.dump(blob, f, protocol=5)
    return blob


# ==========================================================================
# 2. Forecasters.  Every one returns fc[t] = variance forecast FOR session t,
#    built from sessions <= t-1.  Daily variance units (decimal^2).
# ==========================================================================

def ewma_var(x: pd.Series, lam: float, seed_n: int = 20) -> pd.Series:
    """sigma^2_t = lam*sigma^2_{t-1} + (1-lam)*x_{t-1}, seeded on the mean of
    the first `seed_n` finite observations.

    CAUSAL BY CONSTRUCTION: out[i] is written BEFORE x[i] is consumed, so
    out[i] is a function of x[0..i-1] only. Same shape as growth.ewma_vol,
    but it takes a VARIANCE observation (rv or r^2) rather than a return, so
    5-minute RV and daily r^2 can be run through identical machinery — which
    is what H20c needs to separate the measurement from the estimator.
    """
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan)
    run, buf = None, []
    for i in range(len(v)):
        if run is not None:
            out[i] = run
        xi = v[i]
        if not np.isfinite(xi):
            continue
        if run is None:
            buf.append(xi)
            if len(buf) >= seed_n:
                run = float(np.mean(buf))
        else:
            run = lam * run + (1.0 - lam) * xi
    return pd.Series(out, index=x.index)


def har_forecast(rv: pd.DataFrame, log: bool = False, pooled: bool = False,
                 min_obs: int = HAR_MIN_OBS, refit: int = HAR_REFIT) -> pd.DataFrame:
    """Corsi (2009) HAR, fitted WALK-FORWARD ONLY.

        rv[t+1] = b0 + b_d*rv[t] + b_w*mean(rv[t-4..t]) + b_m*mean(rv[t-21..t])

    Mechanism of the model itself: traders act on daily, weekly and monthly
    horizons, and their superimposed persistence reproduces the long memory of
    volatility with three parameters instead of a fractionally integrated one.

    TIMING. The prediction made at t is for t+1 and is `.shift(1)`-ed onto
    t+1 — the only forward alignment in this file. Coefficients used for the
    forecast at position i come from a fit on rows <= k-2 for the refit
    position k <= i, so every target in the fit (rv[t+1], t <= k-2) was already
    observed at i-1. Nothing in the fit or the features touches session i.

    `log=True` fits log-variance and undoes it with the exact lognormal
    correction exp(mu + s^2/2); `pooled=True` fits ONE panel-wide coefficient
    vector per refit (more observations, no per-symbol tailoring).
    """
    idx, cols = rv.index, list(rv.columns)
    n = len(idx)
    d = rv
    w = rv.rolling(5, min_periods=5).mean()
    m = rv.rolling(22, min_periods=22).mean()
    y = rv.shift(-1)

    def design(sym):
        a = np.column_stack([np.ones(n), d[sym].to_numpy(float),
                             w[sym].to_numpy(float), m[sym].to_numpy(float)])
        t = y[sym].to_numpy(float)
        if log:
            with np.errstate(divide="ignore", invalid="ignore"):
                a[:, 1:] = np.log(np.where(a[:, 1:] > 0, a[:, 1:], np.nan))
                t = np.log(np.where(t > 0, t, np.nan))
        return a, t

    X = {s: design(s) for s in cols}
    pred = np.full((n, len(cols)), np.nan)

    starts = list(range(0, n, refit))
    for k in starts:
        hi = min(k + refit, n)
        if pooled:
            As, ts = [], []
            for s in cols:
                a, t = X[s]
                sl = slice(0, max(k - 1, 0))
                ok = np.isfinite(a[sl]).all(1) & np.isfinite(t[sl])
                As.append(a[sl][ok])
                ts.append(t[sl][ok])
            A = np.vstack(As) if As else np.empty((0, 4))
            T = np.concatenate(ts) if ts else np.empty(0)
            fits = {s: (A, T) for s in cols}
        else:
            fits = {}
            for s in cols:
                a, t = X[s]
                sl = slice(0, max(k - 1, 0))
                ok = np.isfinite(a[sl]).all(1) & np.isfinite(t[sl])
                fits[s] = (a[sl][ok], t[sl][ok])
        for j, s in enumerate(cols):
            A, T = fits[s]
            if len(T) < min_obs:
                continue
            beta, *_ = np.linalg.lstsq(A, T, rcond=None)
            s2 = float(np.mean((T - A @ beta) ** 2)) if log else 0.0
            a, _ = X[s]
            rows = np.arange(k, hi)
            feats = a[rows]
            ok = np.isfinite(feats).all(1)
            p = np.full(len(rows), np.nan)
            p[ok] = feats[ok] @ beta
            if log:
                p = np.exp(p + 0.5 * s2)
            pred[rows, j] = p
    out = pd.DataFrame(pred, index=idx, columns=cols)
    return out.shift(1)          # <<< the only forward alignment in this file


def build_forecasts(panel: dict, seed: int = SEED,
                    quiet: bool = False) -> dict[str, pd.DataFrame]:
    """The 11 registered forecasters (10 + the date-shuffle control)."""
    close_ret, rv_cc, r2 = panel["close_ret"], panel["rv_cc"], panel["r2"]
    cols = list(close_ret.columns)
    rng = np.random.default_rng(seed)
    fc: dict[str, pd.DataFrame] = {}

    # the incumbent: growth.blended_vol on daily closes, annualised -> daily var
    fc["blended_daily"] = close_ret.apply(
        lambda c: (g.blended_vol(c) ** 2) / TD_YEAR)

    fc["ewma_daily_094"] = r2.apply(lambda c: ewma_var(c, 0.94))
    for lam in LAMBDAS:
        fc[f"ewma_rv_{int(lam * 100):03d}"] = rv_cc.apply(lambda c: ewma_var(c, lam))

    # POST-HOC variant, registered in hypotheses.md AFTER the panel showed the
    # open-to-close leg is only ~60% of close-to-close variance: filter the two
    # components SEPARATELY because they do not share a persistence — intraday
    # RV is smooth and long-memoried (slow lambda), overnight variance is a
    # spike process around scheduled events (fast lambda). Both values frozen
    # by that argument, not fitted.
    # NOTE the equal-lambda version of this is an exact identity (EWMA is a
    # linear filter, so ewma(a) + ewma(b) = ewma(a+b)); `run()` prints that
    # identity as a machinery check. Only DIFFERENT lambdas can add anything.
    fc["ewma_split"] = (panel["rv_oc"].apply(lambda c: ewma_var(c, 0.97))
                        + (panel["overnight_ret"] ** 2).apply(
                            lambda c: ewma_var(c, 0.80)))

    fc["rw_rv"] = rv_cc.shift(1)
    fc["uncond"] = rv_cc.expanding(min_periods=20).mean().shift(1)

    fc["har_rv"] = har_forecast(rv_cc, log=False, pooled=False)
    fc["har_log"] = har_forecast(rv_cc, log=True, pooled=False)
    fc["har_log_pool"] = har_forecast(rv_cc, log=True, pooled=True)

    # CONTROL: destroy the timing, keep the distribution, identical estimator.
    shuf = rv_cc.copy()
    for s in cols:
        v = np.array(shuf[s].to_numpy(float), copy=True)
        ok = np.isfinite(v)
        v[ok] = rng.permutation(v[ok])
        shuf[s] = v
    fc["ewma_rv_shuf"] = shuf.apply(lambda c: ewma_var(c, 0.94))

    if not quiet:
        print(f"  forecasters built: {len(fc)}")
    return fc


# ==========================================================================
# 3. Losses and their sampling distribution
# ==========================================================================

def qlike(proxy: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Patton (2011) QLIKE: proxy/h - log(proxy/h) - 1, minimised at h=proxy.

    Chosen over MSE as the headline because it is scale-free in the forecast
    and, unlike MSE, is not dominated by the handful of March-2020 days —
    and because it is the loss that penalises UNDER-forecasting risk harder
    than over-forecasting it, which is the asymmetry a risk manager wants.
    """
    r = proxy / h
    return r - np.log(r) - 1.0


def loss_by_date(fc: dict[str, pd.DataFrame], proxy: pd.DataFrame,
                 mask: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Per-symbol QLIKE and MSE on the common mask, then averaged per DATE.

    Variance is expressed in (daily return in %)^2 so MSE is readable: a 1.2%
    day is 1.44 in these units, and MSE comes out O(1-100) instead of O(1e-8).
    """
    p = (proxy * 1e4).where(mask)
    out = {}
    for name, f in fc.items():
        h = (f * 1e4).where(mask)
        pv, hv = p.to_numpy(float), h.to_numpy(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            q = qlike(pv, hv)
            e = (pv - hv) ** 2
        q[~np.isfinite(q)] = np.nan
        out[name] = {
            "qlike": pd.DataFrame(q, index=p.index, columns=p.columns),
            "mse": pd.DataFrame(e, index=p.index, columns=p.columns)}
    return out


def nw_se(x: np.ndarray, lags: int | None = None) -> float:
    """Newey-West standard error of a mean, Bartlett kernel."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    if lags is None:
        lags = int(math.ceil(4 * (n / 100.0) ** (2.0 / 9.0)))
    e = x - x.mean()
    s = float(e @ e) / n
    for l in range(1, min(lags, n - 1) + 1):
        c = float(e[l:] @ e[:-l]) / n
        s += 2.0 * (1.0 - l / (lags + 1.0)) * c
    return math.sqrt(max(s, 0.0) / n)


def block_boot(x: np.ndarray, reps: int = BOOT_REPS, block: int = BLOCK,
               rng: np.random.Generator | None = None) -> np.ndarray:
    """Moving-block bootstrap of a mean. Blocks, not rows: loss differentials
    are persistent (a badly specified model is wrong for weeks at a time), and
    an iid bootstrap would understate the SE exactly the way Rule 14 warns."""
    rng = rng or np.random.default_rng(SEED)
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < block * 3:
        return np.array([np.nan])
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n]
    return x[idx].mean(axis=1)


def compare(a: pd.Series, b: pd.Series, label_a: str, label_b: str,
            rng: np.random.Generator) -> dict:
    """Diebold-Mariano on the date-level loss differential d = L_a - L_b.

    Negative d means `a` is the better forecast. The unit of observation is a
    DATE, because the ~29 symbols share every session and their variances are
    one common factor plus noise."""
    d = (a - b).dropna()
    v = d.to_numpy(float)
    se = nw_se(v)
    bs = block_boot(v, rng=rng)
    n = len(v)
    se_iid = float(np.std(v, ddof=1) / math.sqrt(n)) if n > 2 else float("nan")
    se_boot = float(np.nanstd(bs, ddof=1))
    mid = d.index[n // 2]
    h1, h2 = v[d.index < mid], v[d.index >= mid]
    return {"a": label_a, "b": label_b, "n_dates": n,
            "mean": float(v.mean()),
            "nw_t": float(v.mean() / se) if se and np.isfinite(se) else float("nan"),
            "ci95": [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))],
            "se_boot_over_nw": float(se_boot / se) if se else float("nan"),
            "n_eff": float(min(n, n * (se_iid / se_boot) ** 2)) if se_boot > 0 else float("nan"),
            "half1": float(np.nanmean(h1)), "half2": float(np.nanmean(h2)),
            "both_halves_agree": bool(np.sign(np.nanmean(h1)) == np.sign(np.nanmean(h2)))}


# ==========================================================================
# 4. The payoff test: does a better forecast make vol targeting work?
# ==========================================================================

def ann_ret(r: pd.Series) -> float:
    r = pd.Series(r).dropna()
    if not len(r):
        return float("nan")
    return float((1 + r).prod() ** (TD_YEAR / len(r)) - 1)


def describe_book(r: pd.Series, bench: pd.Series, label: str = "",
                  dl: pd.Series | None = None, mean_lev: float = 1.0,
                  costs=(0.0, 5.0, 10.0)) -> dict:
    """CAGR / vol / Sharpe / maxDD / matched-vol CAGR and maxDD / turnover /
    net Sharpe at each cost in `costs`.

    THE MATCHED-VOL COLUMNS rescale the whole series by ONE constant k so its
    full-sample volatility equals the benchmark's. Volatility targeting is a
    RISK overlay: it does not claim to raise the mean, it claims to spend risk
    better, so comparing its raw CAGR or drawdown against a book running a
    different volatility answers no question at all. Sharpe is invariant to k;
    CAGR and drawdown are not, which is exactly why both are shown. k is a
    full-sample constant — stated here rather than hidden, and identical in
    construction to the H11 table's "rescaled to SPY's vol" row.

    `dl` is the book's ONE-WAY turnover per session (|dL| for a single stream,
    mean_i |dL_i| for a multi-name book — offsetting per-name changes must NOT
    be allowed to cancel). The cost charged is growth.turnover_cost's
    convention, 0.5*dl * cost_bps/1e4, i.e. cost_bps is a ROUND TRIP."""
    r = pd.Series(r).dropna()
    b = pd.Series(bench).reindex(r.index).dropna()
    r = r.reindex(b.index)
    vol = float(r.std(ddof=1) * math.sqrt(TD_YEAR))
    bvol = float(b.std(ddof=1) * math.sqrt(TD_YEAR))
    k = bvol / vol if vol > 0 else 1.0
    mid = r.index[len(r) // 2]
    dl = (dl.reindex(r.index).fillna(0.0) if dl is not None
          else pd.Series(0.0, index=r.index))
    out = {"book": label, "cagr": ann_ret(r) * 100, "vol": vol * 100,
           "sharpe": g.sharpe(r),
           "sharpe_h1": g.sharpe(r[r.index < mid]),
           "sharpe_h2": g.sharpe(r[r.index >= mid]),
           "maxdd": g.max_drawdown(r) * 100,
           "cagr_matched": ann_ret(r * k) * 100,
           "maxdd_matched": g.max_drawdown(r * k) * 100,
           "maxdd_matched_h1": g.max_drawdown((r * k)[r.index < mid]) * 100,
           "maxdd_matched_h2": g.max_drawdown((r * k)[r.index >= mid]) * 100,
           "turnover_ann": float(dl.mean()) * TD_YEAR,
           "mean_lev": float(mean_lev)}
    for c in costs:
        out[f"sharpe_{c:g}bps"] = g.sharpe(r - 0.5 * dl * c / 1e4)
    out["_ret"] = r
    out["_turn_daily"] = float(dl.mean())
    return out


def breakeven_bps(book: dict, bench: dict) -> float:
    """Round-trip cost at which the overlay's SHARPE falls to buy-and-hold's.

    Defined on Sharpe, not CAGR, because a vol overlay deliberately runs a
    different volatility: the CAGR comparison would just be measuring the
    leverage level. Costs shift the mean and leave the standard deviation
    essentially untouched, so
        c* = (mean(r) - sd(r)*Sharpe_bench/sqrt(252)) / (0.5*turnover) * 1e4.
    Negative means the overlay is behind on risk-adjusted terms before it pays
    a single basis point."""
    r = book["_ret"]
    mu, sd = float(r.mean()), float(r.std(ddof=1))
    t = book["_turn_daily"]
    if t <= 0:
        return float("nan")
    return float((mu - sd * bench["sharpe"] / math.sqrt(TD_YEAR)) / (0.5 * t) * 1e4)


def payoff(r: pd.Series, lev_src: pd.DataFrame, books: list[str],
           cost_bps: float, target: float, max_lev: float, extra_lag: bool,
           rng: np.random.Generator) -> dict:
    """Volatility-target one return stream under each forecast.

    `lev_src[name]` is the VARIANCE FORECAST OF THE STREAM BEING TRADED — for
    SPY that is SPY's own forecast; for a multi-name book each name is scaled
    by ITS OWN forecast before the book is formed (see `per_asset_book`),
    because the average of 28 single-name variances is NOT the variance of an
    equal-weight book of them and using it would target the wrong quantity.
    """
    bh = describe_book(r, r, "buy_and_hold")
    rows = [bh]
    levs: dict[str, pd.Series] = {}
    for name in books:
        v = np.sqrt(lev_src[name] * TD_YEAR)
        lev = g.vol_target_scalar(v, target_vol=target, max_leverage=max_lev)
        if extra_lag:
            lev = lev.shift(1)
        lev = lev.reindex(r.index)
        levs[name] = lev
        row = describe_book((lev * r).dropna(), r, f"voltgt_{name}",
                            dl=lev.diff().abs(), mean_lev=float(lev.mean()))
        row["cap_pct"] = float((lev >= max_lev - 1e-9).mean() * 100)
        row["real/tgt"] = float((lev * r).std(ddof=1) * math.sqrt(TD_YEAR) / target)
        rows.append(row)

    # CONTROL 1: exposure that moves but carries NO conditional information —
    # the causal expanding mean of the base forecast's own leverage. NOTE a
    # LITERALLY constant leverage has Sharpe and matched-vol drawdown IDENTICAL
    # to buy-and-hold by construction, so buy-and-hold IS the constant-leverage
    # control; this row adds the "slow drift, no timing" case between them.
    base = books[0]
    const = levs[base].expanding(min_periods=20).mean().shift(1)
    rows.append(describe_book((const * r).dropna(), r, f"driftlev_noinfo[{base}]",
                              dl=const.diff().abs(), mean_lev=float(const.mean())))

    # CONTROL 2: shuffled leverage — identical marginal distribution of
    # exposure, timing destroyed. 200 draws, mean AND sd AND the real value's
    # percentile inside the null (Rule 10).
    nulls = {}
    for name in books:
        sh, dd = [], []
        lv = np.array(levs[name].to_numpy(float), copy=True)
        ok = np.isfinite(lv)
        for _ in range(NULL_DRAWS):
            p = lv.copy()
            p[ok] = rng.permutation(p[ok])
            s = (pd.Series(p, index=levs[name].index) * r).dropna()
            sh.append(g.sharpe(s))
            dd.append(g.max_drawdown(s * (r.std(ddof=1) / s.std(ddof=1))) * 100)
        real = next(x for x in rows if x["book"] == f"voltgt_{name}")
        nulls[name] = {
            "draws": NULL_DRAWS,
            "sharpe_mean": float(np.mean(sh)), "sharpe_sd": float(np.std(sh, ddof=1)),
            "sharpe_pctile": float((np.array(sh) < real["sharpe"]).mean() * 100),
            "maxdd_mean": float(np.mean(dd)), "maxdd_sd": float(np.std(dd, ddof=1)),
            "maxdd_pctile": float((np.array(dd) > real["maxdd_matched"]).mean() * 100)}

    # paired moving-block bootstrap on the Sharpe DIFFERENCES that decide H20e
    diffs = {}
    for name in books:
        a = (levs[name] * r).dropna()
        for other, lab in ((r, "minus_buyhold"),
                           ((levs[base] * r).dropna(), f"minus_voltgt_{base}")):
            if name == base and lab.startswith("minus_voltgt"):
                continue
            j = a.index.intersection(pd.Series(other).index)
            x, y = a.reindex(j).to_numpy(float), pd.Series(other).reindex(j).to_numpy(float)
            n = len(j)
            nb = int(math.ceil(n / BLOCK))
            st = rng.integers(0, n - BLOCK + 1, size=(BOOT_REPS, nb))
            ix = (st[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(BOOT_REPS, -1)[:, :n]
            xb, yb = x[ix], y[ix]
            sd_x = xb.std(axis=1, ddof=1)
            sd_y = yb.std(axis=1, ddof=1)
            d = (xb.mean(axis=1) / sd_x - yb.mean(axis=1) / sd_y) * math.sqrt(TD_YEAR)
            diffs[f"{name}_{lab}"] = {
                "point": float((x.mean() / x.std(ddof=1) - y.mean() / y.std(ddof=1))
                               * math.sqrt(TD_YEAR)),
                "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                "p_gt_0": float((d > 0).mean())}

    for row in rows:
        row["breakeven_bps"] = (breakeven_bps(row, bh)
                                if row["book"] != "buy_and_hold" else float("nan"))
    return {"rows": rows, "shuffled_lev_null": nulls, "sharpe_diffs": diffs,
            "levs": levs}


def per_asset_book(panel: dict, fc: dict[str, pd.DataFrame], names: list[str],
                   dates: pd.DatetimeIndex, target: float, max_lev: float,
                   extra_lag: bool) -> tuple:
    """Equal-weight book of `STOCKS` where EACH name is scaled by ITS OWN
    variance forecast, then the scaled streams are averaged.

    This is the correct multi-name use of a per-symbol variance forecast and
    the same construction `sleeve_lab._risk_scaled` uses. The alternative that
    a first draft of this file used — averaging the 28 single-name variance
    forecasts and treating the result as the book's variance — is simply wrong:
    the constituents are far from perfectly correlated, so the book's variance
    is roughly half the average constituent's, and the overlay would have been
    solving for the wrong quantity. Reported here so nobody repeats it.
    """
    r = panel["close_ret"][STOCKS].reindex(dates)
    unlev = r.mean(axis=1).dropna()
    out, turn, mlev = {}, {}, {}
    for name in names:
        v = np.sqrt(fc[name][STOCKS].reindex(dates) * TD_YEAR)
        lev = v.apply(lambda c: g.vol_target_scalar(c, target_vol=target,
                                                    max_leverage=max_lev))
        if extra_lag:
            lev = lev.shift(1)
        out[name] = (lev * r).mean(axis=1)
        # one-way turnover of the BOOK: average |dL_i| across names, so that
        # one name de-levering while another levers up still costs money.
        turn[name] = lev.diff().abs().mean(axis=1)
        mlev[name] = float(lev.mean(axis=1).mean())
    return unlev, pd.DataFrame(out), pd.DataFrame(turn), mlev


# ==========================================================================
# 5. Self-test: the lookahead audit and a positive control
# ==========================================================================

def selftest(quiet: bool = False) -> int:
    """Two things a forecast lab must prove about itself before it is believed.

    (A) LOOKAHEAD AUDIT — mechanical, not argued. Truncate the input at a cut
        date, rebuild every forecaster, and require the forecasts up to the cut
        to be BIT-IDENTICAL to the full-sample ones. Anything that peeks at a
        future observation changes when the future is deleted.
    (B) POSITIVE CONTROL — a synthetic series whose true variance is known and
        whose RV is a low-noise measurement of it. The RV-fed models MUST beat
        the daily-r^2-fed ones there. If they do not, the pipeline is broken
        and no verdict on real data means anything.
    """
    fails = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
        if not cond:
            fails.append(name)

    rng = np.random.default_rng(7)
    n, m = 1600, 6
    # (B) synthetic: log-AR(1) variance, 78 intraday increments a day.
    lv = np.zeros((n, m))
    for i in range(1, n):
        lv[i] = 0.985 * lv[i - 1] + 0.14 * rng.standard_normal(m)
    # Mirrors the real panel's structure: 60% of daily variance accrues
    # intraday over 78 increments (measurable), 40% arrives as ONE overnight
    # jump (never measurable with more than one observation). That split is
    # what makes this a fair positive control rather than a rigged one.
    true_var = 1.2e-4 * np.exp(lv)                      # daily variance
    var_oc, var_on = 0.6 * true_var, 0.4 * true_var
    intr = rng.standard_normal((n, m, 78)) * np.sqrt(var_oc / 78)[:, :, None]
    r_on = rng.standard_normal((n, m)) * np.sqrt(var_on)
    r_day = intr.sum(axis=2) + r_on
    rv_oc = (intr ** 2).sum(axis=2)
    idx = pd.bdate_range("2016-01-04", periods=n)
    cols = [f"S{i}" for i in range(m)]
    mk = lambda a: pd.DataFrame(a, index=idx, columns=cols)
    rd, on = mk(r_day), mk(r_on)
    tv = mk(true_var)

    syn = {"close_ret": rd, "rv_oc": mk(rv_oc), "overnight_ret": on,
           "rv_cc": mk(rv_oc) + on ** 2, "r2": rd ** 2}
    f = build_forecasts(syn, quiet=True)

    # (A) lookahead audit on the synthetic panel (same code path as real data)
    cut = 1200
    tr = {k: v.iloc[:cut] for k, v in syn.items()}
    ft = build_forecasts(tr, quiet=True)
    worst = 0.0
    for k in ft:
        if k == "ewma_rv_shuf":
            continue                       # the control permutes; not comparable
        a = f[k].iloc[:cut].to_numpy(float)
        b = ft[k].to_numpy(float)
        both = np.isfinite(a) & np.isfinite(b)
        if both.any():
            worst = max(worst, float(np.nanmax(np.abs(a[both] - b[both]))))
    check("no lookahead: truncating the input leaves every forecast unchanged",
          worst < 1e-12, f"max |diff| = {worst:.3e}")

    # (B) positive control, scored against the KNOWN true variance
    mask = pd.DataFrame(True, index=idx, columns=cols)
    mask.iloc[:300] = False
    L = loss_by_date(f, tv, mask)
    q = {k: float(np.nanmean(v["qlike"].to_numpy())) for k, v in L.items()}
    for k in sorted(q, key=q.get):
        print(f"      {k:<16} QLIKE {q[k]:.5f}")
    check("positive control: EWMA on RV beats EWMA on daily r^2",
          q["ewma_rv_094"] < q["ewma_daily_094"],
          f"{q['ewma_rv_094']:.5f} < {q['ewma_daily_094']:.5f}")
    check("positive control: HAR on RV beats the daily incumbent",
          q["har_log"] < q["blended_daily"],
          f"{q['har_log']:.5f} < {q['blended_daily']:.5f}")
    # NOTE (Rule 15 — a control can leak too): permuting dates moves FUTURE
    # observations into the past, so the shuffled EWMA is an estimate of the
    # FULL-SAMPLE unconditional level and can beat a live expanding mean. That
    # makes it a CONSERVATIVE null — harder to beat than an honest constant —
    # so the requirement is only that destroying the timing destroys the skill.
    check("control behaves: destroying the timing destroys most of the skill",
          q["ewma_rv_shuf"] > 3 * q["ewma_rv_094"],
          f"shuf {q['ewma_rv_shuf']:.5f} vs real {q['ewma_rv_094']:.5f} "
          f"(uncond {q['uncond']:.5f})")
    check("QLIKE is minimised at h = proxy",
          abs(float(qlike(np.array([2.0]), np.array([2.0]))[0])) < 1e-12)
    check("QLIKE penalises under-forecasting harder than over-forecasting",
          float(qlike(np.array([2.0]), np.array([1.0]))[0])
          > float(qlike(np.array([2.0]), np.array([4.0]))[0]))

    # timing sanity on the leverage map
    fcx = pd.DataFrame({"X": pd.Series([np.nan, 4e-4, 1e-4], index=idx[:3])})
    lev = g.vol_target_scalar(np.sqrt(fcx["X"] * TD_YEAR), 0.12, max_leverage=2.0)
    check("leverage falls when forecast variance rises",
          bool(lev.iloc[1] < lev.iloc[2]),
          f"{lev.iloc[1]:.3f} < {lev.iloc[2]:.3f}")

    print(f"\n  {len(fails)} failure(s)" if fails else "\n  all checks passed")
    return 1 if fails else 0


# ==========================================================================
# 6. Report
# ==========================================================================

def _t(rows, cols, title):
    print(f"\n{title}")
    w = [max(len(str(c)), *(len(f"{r[c]:.4g}" if isinstance(r[c], float)
                            else str(r[c])) for r in rows)) for c in cols]
    print("  " + "  ".join(str(c).ljust(w[i]) for i, c in enumerate(cols)))
    print("  " + "  ".join("-" * w[i] for i in range(len(cols))))
    for r in rows:
        print("  " + "  ".join(
            (f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c])).ljust(w[i])
            for i, c in enumerate(cols)))


def run(args) -> dict:
    rng = np.random.default_rng(SEED)
    panel = load_panel(use_cache=not args.no_cache,
                       official_close=args.official_close)
    meta = panel["meta"]
    print(f"\nPANEL  {meta['span'][0]} .. {meta['span'][1]}   "
          f"{meta['n_dates']:,} sessions x {meta['n_symbols']} symbols")
    print(f"  split repair: intraday.apply_split_repair ran inside "
          f"session_frames (layer 1)")
    print(f"  |close_ret| > {MAX_ABS_RET:.0%} blanked: "
          f"{meta['blanked_extreme_sessions']} symbol-sessions (layer 2)"
          + (f" -> {meta['blanked_list']}" if meta["blanked_list"] else ""))
    print("  largest surviving |close_ret|: " + ", ".join(
        f"{r['symbol']} {r['date'].date()} {r['abs_close_ret']:.1%}"
        for r in meta["largest_abs_close_ret"][:4]))
    print(f"  open-to-close share of close-to-close variance: "
          f"{meta['mean_rv_oc_over_rv_cc']:.1%}  "
          f"(the rest is the overnight gap, which no intraday tape can measure)")

    fc = build_forecasts(panel)
    names = list(fc)

    # machinery check: EWMA is a linear filter, so splitting the two variance
    # legs and filtering each at the SAME lambda must reproduce the single
    # filter exactly. If this drifts, the recursion is not doing what the
    # docstring says it does.
    ident = ((panel["rv_oc"].apply(lambda c: ewma_var(c, 0.94))
              + (panel["overnight_ret"] ** 2).apply(lambda c: ewma_var(c, 0.94)))
             - fc["ewma_rv_094"]).abs().to_numpy()
    print(f"  linearity check: max |ewma(oc)+ewma(on) - ewma(oc+on)| = "
          f"{np.nanmax(ident):.2e} (seeding only; the equal-lambda split is an "
          f"identity)")

    # common scoring sample: every forecaster finite and positive, proxy finite
    idx = panel["close_ret"].index
    mask = pd.DataFrame(True, index=idx, columns=panel["close_ret"].columns)
    for f in fc.values():
        mask &= f.notna() & (f > 0)
    mask &= panel["rv_cc"].notna() & (panel["rv_cc"] > 0)
    mask &= panel["r2"].notna() & (panel["r2"] > 0)
    mask.iloc[:WARMUP] = False
    live = mask.any(axis=1)
    dates = idx[live]
    print(f"\nSCORING SAMPLE  {dates[0].date()} .. {dates[-1].date()}   "
          f"{len(dates):,} dates, {int(mask.to_numpy().sum()):,} symbol-sessions"
          f"  (first {WARMUP} sessions dropped as warm-up; every forecaster "
          f"scored on the IDENTICAL cells)")

    out = {"meta": meta, "scoring": {"n_dates": int(len(dates)),
                                     "n_obs": int(mask.to_numpy().sum()),
                                     "span": (str(dates[0].date()), str(dates[-1].date()))}}

    # ---------------------------------------------------------------- losses
    for pname, proxy in (("rv_cc", panel["rv_cc"]), ("r2", panel["r2"])):
        L = loss_by_date(fc, proxy, mask)
        qd = pd.DataFrame({k: v["qlike"].mean(axis=1) for k, v in L.items()}).loc[dates]
        md = pd.DataFrame({k: v["mse"].mean(axis=1) for k, v in L.items()}).loc[dates]
        mid = dates[len(dates) // 2]
        rows = []
        for k in names:
            per = L[k]["qlike"].mean(axis=0)
            rows.append({"forecaster": k,
                         "QLIKE": float(qd[k].mean()),
                         "QLIKE_h1": float(qd[k][qd.index < mid].mean()),
                         "QLIKE_h2": float(qd[k][qd.index >= mid].mean()),
                         "MSE": float(md[k].mean()),
                         "best_in_syms": 0})
        # Replication breadth, the H18b-style control: a pooled QLIKE gap that
        # comes from 3 of 29 names is not the same claim as one that comes from
        # 28 of 29. `beats_incumbent` counts symbols, not dates.
        persym = pd.DataFrame({k: L[k]["qlike"].mean(axis=0) for k in names})
        winner = persym.idxmin(axis=1)
        nsym = int(persym["blended_daily"].notna().sum())
        for r in rows:
            k = r["forecaster"]
            r["best_in_syms"] = int((winner == k).sum())
            r["beats_incumbent"] = f"{int((persym[k] < persym['blended_daily']).sum())}/{nsym}"
        rows.sort(key=lambda r: r["QLIKE"])
        _t(rows, ["forecaster", "QLIKE", "QLIKE_h1", "QLIKE_h2", "MSE",
                  "best_in_syms", "beats_incumbent"],
           f"OUT-OF-SAMPLE FORECAST LOSS  (proxy = {pname}; lower is better; "
           f"variance in (daily %)^2; {len(dates):,} dates)")
        out[f"loss_{pname}"] = rows

        if pname == "rv_cc":
            pairs = [("ewma_rv_094", "blended_daily", "H20a  RV-EWMA vs the incumbent"),
                     ("har_log", "ewma_rv_094", "H20b  HAR vs RV-EWMA"),
                     ("har_log_pool", "ewma_rv_094", "H20b' pooled HAR vs RV-EWMA"),
                     ("ewma_rv_094", "ewma_daily_094", "H20c  SAME estimator, RV vs daily r^2"),
                     ("ewma_split", "ewma_rv_094", "      POST-HOC: split oc/overnight legs"),
                     ("ewma_rv_094", "uncond", "      RV-EWMA vs the expanding mean"),
                     ("ewma_rv_shuf", "uncond", "      CONTROL: date-shuffled RV vs the mean"),
                     ("ewma_rv_094", "ewma_rv_shuf", "      CONTROL: real vs date-shuffled RV"),
                     ("har_log", "blended_daily", "      best RV model vs the incumbent")]
            crows = []
            for a, b, lab in pairs:
                c = compare(qd[a], qd[b], a, b, rng)
                crows.append({"row": lab, "dQLIKE": c["mean"], "NW_t": c["nw_t"],
                              "ci_lo": c["ci95"][0], "ci_hi": c["ci95"][1],
                              "half1": c["half1"], "half2": c["half2"],
                              "agree": "yes" if c["both_halves_agree"] else "NO",
                              "n_eff": c["n_eff"], "seB/seNW": c["se_boot_over_nw"]})
            _t(crows, ["row", "dQLIKE", "NW_t", "ci_lo", "ci_hi", "half1",
                       "half2", "agree", "n_eff", "seB/seNW"],
               "DIEBOLD-MARIANO on the DATE-level QLIKE differential "
               "(negative = the first model is better)")
            out["dm"] = crows

    # H20d: is the ranking proxy-invariant?
    r1 = [r["forecaster"] for r in out["loss_rv_cc"]]
    r2_ = [r["forecaster"] for r in out["loss_r2"]]
    # Spearman by hand (no scipy in this venv): both lists are permutations of
    # the same names, so the rank vectors align on the name index.
    a = pd.Series(range(len(r1)), index=r1, dtype=float)
    b = pd.Series(range(len(r2_)), index=r2_, dtype=float).reindex(a.index)
    rho = float(np.corrcoef(a.to_numpy(), b.to_numpy())[0, 1])
    out["h20d"] = {"rank_corr": rho, "top_rv_cc": r1[0], "top_r2": r2_[0],
                   "identical": r1 == r2_}
    print(f"\nH20d  proxy invariance: Spearman rank correlation between the two "
          f"proxies' orderings = {rho:.3f}"
          f"  (best under rv_cc: {r1[0]}; best under r^2: {r2_[0]})")

    # ---------------------------------------------------------------- payoff
    books = ["blended_daily", "ewma_rv_094", "har_log", "har_log_pool"]
    COLS = ["book", "cagr", "vol", "sharpe", "sharpe_h1", "sharpe_h2", "maxdd",
            "cagr_matched", "maxdd_matched", "turnover_ann", "mean_lev",
            "sharpe_0bps", "sharpe_5bps", "sharpe_10bps", "breakeven_bps"]
    lag_note = ("H11/sleeve_lab extra shift(1)" if args.extra_lag
                else "L[t] from data <= t-1 applied to r[t]")

    # --- (1) SPY: one asset, its own forecast. The H11 comparison, rerun.
    spy = panel["close_ret"][BENCH].reindex(dates).dropna()
    hsplit = spy.index[len(spy) // 2]
    out["half_split"] = str(hsplit.date())
    print(f"\nHALVES split at {hsplit.date()}.  What each half actually is, "
          f"because it explains the payoff rows:")
    for lab, s in (("half 1", spy[spy.index < hsplit]), ("half 2", spy[spy.index >= hsplit])):
        print(f"    SPY {lab} {s.index[0].date()}..{s.index[-1].date()}: "
              f"return {ann_ret(s) * 100:+.1f}%/yr, vol "
              f"{s.std(ddof=1) * math.sqrt(TD_YEAR) * 100:.1f}%, "
              f"Sharpe {g.sharpe(s):.3f}, worst day {s.min() * 100:.1f}%, "
              f"maxDD {g.max_drawdown(s) * 100:.1f}%")
    p = payoff(spy, pd.DataFrame({k: v[BENCH] for k, v in fc.items()}), books,
               args.cost_bps, args.target_vol, args.max_lev, args.extra_lag, rng)
    _t(p["rows"], COLS,
       f"H20e/f/g  VOLATILITY TARGETING — SPY  (target {args.target_vol:.0%}, "
       f"cap {args.max_lev:g}x, rf = 0, {lag_note})")
    for name, n in p["shuffled_lev_null"].items():
        real = next(x for x in p["rows"] if x["book"] == f"voltgt_{name}")
        print(f"  CONTROL shuffled leverage [{name}] {n['draws']} draws: "
              f"Sharpe null {n['sharpe_mean']:.3f} +/- {n['sharpe_sd']:.3f} "
              f"-> real {real['sharpe']:.3f} at the {n['sharpe_pctile']:.0f}th pct; "
              f"matched maxDD null {n['maxdd_mean']:.1f} +/- {n['maxdd_sd']:.1f} "
              f"-> real {real['maxdd_matched']:.1f} at the {n['maxdd_pctile']:.0f}th pct")
    print("\n  SHARPE DIFFERENCES (paired moving-block bootstrap, "
          f"{BOOT_REPS} draws, block {BLOCK}):")
    for k, d in p["sharpe_diffs"].items():
        print(f"    {k:<38} {d['point']:+.3f}  CI [{d['ci95'][0]:+.3f}, "
              f"{d['ci95'][1]:+.3f}]  P(>0) = {d['p_gt_0']:.3f}")
    out["payoff_SPY"] = {k: v for k, v in p.items() if k != "levs"}
    for r in out["payoff_SPY"]["rows"]:
        r.pop("_ret", None)

    # --- (2) the 28 single names, each scaled by ITS OWN forecast
    unlev, blev, turn, mlev = per_asset_book(panel, fc, books, dates,
                                             args.asset_vol, args.max_lev,
                                             args.extra_lag)
    rows = [describe_book(unlev, unlev, "equal_weight_unlevered")]
    for name in books:
        rows.append(describe_book(blev[name].dropna(), unlev,
                                  f"per_asset_voltgt_{name}",
                                  dl=turn[name], mean_lev=mlev[name]))
    bh = rows[0]
    for r in rows[1:]:
        r["breakeven_bps"] = breakeven_bps(r, bh)
    bh["breakeven_bps"] = float("nan")
    _t(rows, COLS,
       f"H20e/f/g  PER-ASSET VOLATILITY TARGETING — 28 large caps, equal "
       f"weight  (per-name target {args.asset_vol:.0%}, cap {args.max_lev:g}x, "
       f"rf = 0, {lag_note})")
    print("  NOTE the book's realised vol lands well under the per-name target "
          "because the names are imperfectly correlated — that is\n       "
          "diversification, not a targeting error, and it is why Sharpe and "
          "MATCHED-vol drawdown are the columns to read.")
    for r in rows:
        r.pop("_ret", None)
    out["payoff_per_asset"] = rows

    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nwrote {RESULTS}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true",
                    help="lookahead audit + synthetic positive control, no API")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--official-close", action="store_true",
                    help="splice scout/data.py auction closes into close_px")
    ap.add_argument("--extra-lag", action="store_true",
                    help="H11/sleeve_lab timing: one further shift(1) on leverage")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--target-vol", type=float, default=TARGET_VOL)
    ap.add_argument("--asset-vol", type=float, default=ASSET_VOL,
                    help="per-name target for the 28-stock risk-scaled book")
    ap.add_argument("--max-lev", type=float, default=MAX_LEV)
    args = ap.parse_args()

    if args.selftest:
        print("=== rv_forecast_lab self-test "
              "(lookahead audit + positive control) ===")
        raise SystemExit(selftest())
    run(args)


if __name__ == "__main__":
    main()
