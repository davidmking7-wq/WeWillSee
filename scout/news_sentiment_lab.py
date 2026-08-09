"""H16 — does headline sentiment predict drift BEYOND the same-day price move?

MECHANISM (one sentence, before any number): Tetlock (2007) and
Tetlock-Saar-Tsechansky-Macskassy (2008) argue that media tone carries
fundamental information which is incorporated with a lag, because reading and
interpreting text is costly — so pessimistic coverage should predict lower
subsequent returns and optimistic coverage higher ones, over and above what
the same session's price move already reflects.

That last clause is the whole experiment. A news-tone portfolio that is not
tested against the contemporaneous return is usually short-term reversal
wearing a costume: bad headlines arrive on down days, down days bounce, and
the "sentiment effect" is the bounce. This lab runs the naive test AND the
test that separates them, and reports both.

DATA (US equities only; no crypto, options, futures or FX)
  news   scout/news_data.load_panel() — 308,870 Benzinga stories, 464,430
         symbol-rows, 2016-01-02..2026-07-31, over the 120 most liquid S&P 500
         members AS OF 2016-01-04 (scout/pit.py point-in-time membership, so
         BRCM/CELG/EMC/TWX/ESRX/MON/AET/PXD are in and no post-2016 addition
         is — survivorship-free at the cost of no TSLA).
  prices scout/data.py daily SIP closes for the same 121 tickers (+SPY),
         split-repaired against Alpaca's corporate-actions feed via
         scout/intraday.unapplied_splits_close, because adjustment=all misses
         the AAPL 2020-08-31 4:1 split and would otherwise inject a -74.2%
         one-day return into the middle of the sample.

SIGNAL
  net tone_{i,t} = (pos - neg) / (pos + neg + 1), where pos/neg are
  Loughran-McDonald-style word counts summed over every story attributable to
  session t. Attribution is news_data's rule: a story is assigned to session t
  iff it was published before session t's close (ET, DST- and half-day-aware),
  so row t contains only text a trader could have read by the closing bell.
  Ranked cross-sectionally within each date, among liquid names that have news
  that session — the panel's coverage is wildly uneven across names (Benzinga
  writes 18 stories/session about some names and 0.2 about others), so an
  un-normalised cross-sectional tone measure just ranks stocks by how much the
  wire likes them.

NO LOOKAHEAD — WHERE THE SHIFT IS
  Exactly one shift moves information forward in time, in `ls_portfolio`:

      port = (Wbar.shift(1) * ret1).sum(axis=1)

  `Wbar_t` is built from news readable before close t; `ret1_t` is the return
  EARNED on day t (close t-1 -> close t). Shifting the weights by one bar means
  the earliest return any signal can touch is close(t) -> close(t+1). The
  regression side states it the other way round and equivalently:
  fwd_h(t) = close(t+h)/close(t) - 1 is regressed on variables all known at
  close t. `selftest --lookahead` demonstrates the contamination that appears
  when the shift is removed.

CONTROLS (all four run, none optional)
  shuffle  tone permuted across symbols WITHIN each date (200 draws)
  placebo  each symbol permanently assigned another symbol's tone series, so
           every series keeps its own time-series properties and only the
           pairing breaks (200 draws)
  random   random quintile assignment from the identical eligible pool (200)
  bench    equal-weight of the eligible-with-news pool, and SPY

METHOD
  Quintiles formed at the close of session t, held h in {1, 5, 21, 42}
  sessions with h overlapping cohorts (Jegadeesh-Titman), which produces a
  genuine daily P&L series with measured turnover. Costs 10 bps round trip
  charged on that turnover; break-even round-trip cost reported. Both halves
  split at the median date. Moving-block bootstrap by date, block = h, because
  overlapping holds make adjacent days dependent. Fama-MacBeth cross-sectional
  regressions with Newey-West(h) standard errors on the lambda series.

VERDICT (measured 2026-08-09; the numbers this file prints)
  REJECTED. Raw tone has a small positive 1-session tilt, but it is short-term
  reversal, not information: the same-session return alone explains more of the
  forward move, and in the joint Fama-MacBeth regression the tone coefficient
  collapses toward zero at every horizon. The double sort agrees — within a
  same-session-return tercile the tone spread is not reliably positive. Nothing
  here survives 10 bps, and the break-even costs are a fraction of that. Full
  numbers in the __main__ output and in scout/hypotheses.md H16a-H16d.

RUN
  python -m scout.news_sentiment_lab              # everything (~3 min warm)
  python -m scout.news_sentiment_lab --selftest   # offline, synthetic, <5s
  python -m scout.news_sentiment_lab --quick      # h=1,5 only
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, data as daily_data, growth, intraday, news_data

# --------------------------------------------------------------------------
# knobs — all fixed ex ante, none of them tuned on an outcome
# --------------------------------------------------------------------------
HORIZONS = (1, 5, 21, 42)
N_QUANTILES = 5
COST_BPS_ROUND_TRIP = 10.0        # large caps; one-way = half of this
MIN_DOLLAR_VOL = 20e6             # trailing-21-session MEDIAN, computed through t
LIQ_WINDOW = 21
MIN_NAMES = 20                    # smallest cross-section that may be ranked
N_CONTROL_DRAWS = 200
BOOT_REPS = 2000
SEED = 20260809
N_TRIALS_REGISTERED = 14   # H16a(4) + H16b(4) + H16c(4) + H16d(2); controls are nulls

BARS_PICKLE = config.SCOUT_DIR / "cache_news_sent_bars.pkl"
DATASET_PICKLE = config.SCOUT_DIR / "cache_news_sent_dataset.pkl"
SPLIT_AUDIT_JSON = config.SCOUT_DIR / "cache_news_sent_splitaudit.json"
BENCH = "SPY"
TDAYS = 252.0


# --------------------------------------------------------------------------
# small statistics helpers (scipy is not installed in this repo)
# --------------------------------------------------------------------------

def _t_stat(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))


def _nw_t(x: np.ndarray, lags: int) -> float:
    """Newey-West t-statistic for the mean of a serially-correlated series.

    Overlapping h-day holds make adjacent observations dependent by
    construction; an OLS t on that series is inflated by roughly sqrt(h).
    """
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    var = float(e @ e) / n
    for L in range(1, min(lags, n - 1) + 1):
        cov = float(e[L:] @ e[:-L]) / n
        var += 2.0 * (1.0 - L / (lags + 1.0)) * cov
    if var <= 0:
        return float("nan")
    return float(x.mean() / math.sqrt(var / n))


def _block_boot_ci(x: np.ndarray, block: int, reps: int = BOOT_REPS,
                   seed: int = SEED) -> tuple[float, float]:
    """Moving-block bootstrap CI for the mean of a daily series.

    One observation per DATE, so resampling dates IS the date-clustered
    bootstrap this repo uses elsewhere (scout/calibrate.py); the block length
    is what additionally respects the overlapping holding period.
    """
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    off = np.arange(block)
    idx = (starts[:, :, None] + off[None, None, :]).reshape(reps, -1)[:, :n]
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _ann(mean_daily: float) -> float:
    return float(mean_daily * TDAYS)


def _sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 5 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * math.sqrt(TDAYS))


# --------------------------------------------------------------------------
# prices — fetch, split-repair, liquidity-gate
# --------------------------------------------------------------------------

def load_bars(force: bool = False, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Daily SIP closes/volumes for the news panel's universe, split-repaired.

    scout/data.py inherits Alpaca's missing-split defect (documented in
    scout/intraday.py). Ignoring it puts a fabricated -74.2% one-day AAPL
    return in the middle of the sample, which would dominate every mean it
    touches. Repair is anchored on Alpaca's OWN corporate-actions feed, so it
    cannot invent a split that did not happen.
    """
    if BARS_PICKLE.exists() and not force:
        bars = pd.read_pickle(BARS_PICKLE)
    else:
        syms = sorted(set(json.loads(
            news_data.PANEL_SYMBOLS_JSON.read_text())) | {BENCH})
        if verbose:
            print(f"fetching daily bars for {len(syms)} symbols ...")
        bars = daily_data.daily_ohlcv(syms, 3960)
        pd.to_pickle(bars, BARS_PICKLE)
    close, volume = bars["close"].copy(), bars["volume"].copy()
    close, volume, repairs = repair_splits(close, volume, verbose=verbose)
    return {"close": close, "volume": volume, "repairs": repairs}


#: An unapplied-split test can only separate "applied" from "not applied" when
#: the split's log ratio is bigger than twice the classifier tolerance.
#: intraday.unapplied_splits_close uses tol=0.15, so ANY event under
#: exp(0.30) ~= 1.35 is unresolvable and must never be auto-repaired. Measured
#: false positive: MET's 2017-08-07 Brighthouse spin-off is filed as a
#: forward_split of ratio 1.122; the bars ARE adjusted (MET goes 35.48 ->
#: 35.83, +1.0%) yet |log(1.0099) + log(1.122)| = 0.125 < 0.15, so the test
#: flags it. Repairing it would have divided 401 MET closes by 1.122.
MIN_REPAIR_LOG_RATIO = 0.35


def repair_splits(close: pd.DataFrame, volume: pd.DataFrame,
                  verbose: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """Back-adjust any split Alpaca's bar pipeline failed to apply.

    Only unambiguous events are touched — see MIN_REPAIR_LOG_RATIO. Ambiguous
    ones are printed, not silently applied and not silently dropped.
    """
    if SPLIT_AUDIT_JSON.exists():
        events = {k: [{"ex_date": pd.Timestamp(e["ex_date"]),
                       "ratio": e["ratio"], "kind": e["kind"]} for e in v]
                  for k, v in json.loads(SPLIT_AUDIT_JSON.read_text()).items()}
    else:
        events = intraday.split_events(list(close.columns),
                                       close.index.min(), close.index.max())
        SPLIT_AUDIT_JSON.write_text(json.dumps(
            {k: [{"ex_date": str(e["ex_date"].date()), "ratio": e["ratio"],
                  "kind": e["kind"]} for e in v] for k, v in events.items()},
            indent=1))
    repairs, ambiguous = [], []
    for sym, evs in events.items():
        if sym not in close.columns:
            continue
        s = close[sym].dropna()
        s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
        bad = intraday.unapplied_splits_close(s, evs)
        for b in bad:
            if b.get("applied") is not False:
                continue                       # jump not at the split ratio
            if abs(math.log(b["ratio"])) < MIN_REPAIR_LOG_RATIO:
                ambiguous.append({"symbol": sym, "ex_date": str(b["ex_date"].date()),
                                  "ratio": b["ratio"], "jump": b["jump"]})
                continue
            ex = pd.Timestamp(b["ex_date"])
            mask = close.index.tz_localize(None).normalize() < ex
            close.loc[mask, sym] = close.loc[mask, sym] / b["ratio"]
            volume.loc[mask, sym] = volume.loc[mask, sym] * b["ratio"]
            repairs.append({"symbol": sym, "ex_date": str(ex.date()),
                            "ratio": b["ratio"], "n_bars": int(mask.sum())})
    if verbose:
        if repairs:
            for r in repairs:
                print(f"  SPLIT REPAIR {r['symbol']} {r['ex_date']} "
                      f"ratio {r['ratio']:.0f} -> {r['n_bars']:,} bars rescaled")
        else:
            print("  split audit: nothing unapplied")
        for a in ambiguous:
            print(f"  split audit AMBIGUOUS (not repaired): {a['symbol']} "
                  f"{a['ex_date']} filed ratio {a['ratio']:.3f}, observed jump "
                  f"{a['jump']:.4f} — ratio too small for the 0.15 classifier")
    return close, volume, repairs


def liquidity_mask(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """Tradeable-at-10bps gate, computed from data THROUGH t only.

    Doubles as the ticker-reuse guard this universe genuinely needs: MON keeps
    printing a stale 127.95 at zero volume for 695 sessions after Bayer closes
    the acquisition, and the ticker is then reused by an unrelated $10 issuer.
    A dollar-volume floor removes both without a hand-maintained delisting list.
    """
    dv = close * volume
    med = dv.rolling(LIQ_WINDOW, min_periods=LIQ_WINDOW).median()
    return (med >= MIN_DOLLAR_VOL) & close.notna()


# --------------------------------------------------------------------------
# tone frames
# --------------------------------------------------------------------------

def tone_frames(news: pd.DataFrame, sessions: pd.DatetimeIndex,
                max_tags: int = 10) -> dict[str, dict[str, pd.DataFrame]]:
    """{'all'|'specific': {'pos','neg','n','tone'}} as session x symbol frames.

    net tone = (pos - neg) / (pos + neg + 1), the registered definition. The +1
    shrinks symbol-sessions whose stories contain few lexicon words toward
    neutral instead of letting a single word produce +/-1.

    'specific' drops templated wire (movers lists, market wraps) and broadtape
    stories tagged to more than `max_tags` symbols — the structural filter
    news_data recommends, since one 2020-03-16 story is tagged to 2,568 names.
    """
    d = news.copy()
    d["session"] = news_data.attribute_sessions(d["created_at"], sessions)
    d = d[d["session"].notna()].copy()
    sc = news_data.score_headlines(d["headline"])
    d["pos"] = sc["pos"].to_numpy()
    d["neg"] = sc["neg"].to_numpy()
    cat = news_data.categorize(d["headline"])
    d["specific"] = (~cat.isin(news_data.TEMPLATED_CATEGORIES)
                     & ~news_data.is_broadtape(d["n_tags"], max_tags))
    d["one"] = 1.0
    cols = sorted(set(d["symbol"]))
    out = {}
    for name, sub in (("all", d), ("specific", d[d["specific"]])):
        def piv(col, s=sub):
            return (s.pivot_table(index="session", columns="symbol",
                                  values=col, aggfunc="sum")
                    .reindex(index=sessions, columns=cols).fillna(0.0))
        pos, neg, n = piv("pos"), piv("neg"), piv("one")
        tone = (pos - neg) / (pos + neg + 1.0)
        out[name] = {"pos": pos, "neg": neg, "n": n, "tone": tone.where(n > 0)}
    return out


# --------------------------------------------------------------------------
# the dataset
# --------------------------------------------------------------------------

def build_dataset(force: bool = False, verbose: bool = True) -> dict:
    if DATASET_PICKLE.exists() and not force:
        ds = pd.read_pickle(DATASET_PICKLE)
        if ds.get("version") == 2:
            return ds
    t0 = time.time()
    bars = load_bars(verbose=verbose)
    close, volume = bars["close"], bars["volume"]
    sessions = news_data._session_index(close)
    close.index = sessions
    volume.index = sessions
    bench = close[BENCH].copy() if BENCH in close.columns else None
    news = news_data.load_panel()
    if verbose:
        print(f"news: {len(news):,} symbol-rows, "
              f"{news['id'].nunique():,} stories, "
              f"{news['created_at'].min().date()}..{news['created_at'].max().date()}")
    audit = news_data.audit_attribution(news, close)   # asserts 0 violations
    tf = tone_frames(news, sessions)
    cols = [c for c in close.columns if c in tf["all"]["tone"].columns]
    close_u = close[cols]
    liq = liquidity_mask(close_u, volume[cols])
    ret1 = close_u.pct_change()
    ds = {
        "version": 2,
        "sessions": sessions,
        "close": close_u,
        "bench": bench,
        "ret1": ret1,
        "liq": liq,
        "tone": {k: v["tone"].reindex(columns=cols) for k, v in tf.items()},
        "n_stories": {k: v["n"].reindex(columns=cols) for k, v in tf.items()},
        "repairs": bars["repairs"],
        "attribution_audit": audit,
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }
    pd.to_pickle(ds, DATASET_PICKLE)
    if verbose:
        print(f"dataset built in {time.time() - t0:.0f}s -> {DATASET_PICKLE.name}")
    return ds


def eligible_scores(ds: dict, kind: str = "all") -> tuple[pd.DataFrame, pd.DataFrame]:
    """(tone, same-day return) restricted to the eligible-with-news pool.

    Both are known at close t: tone is news readable before close t, and the
    same-day return is close(t-1) -> close(t).
    """
    tone = ds["tone"][kind]
    ok = ds["liq"] & ds["n_stories"][kind].gt(0) & ds["ret1"].notna()
    enough = ok.sum(axis=1).ge(MIN_NAMES)
    ok = ok.mul(enough, axis=0).astype(bool)
    return tone.where(ok), ds["ret1"].where(ok)


def xrank(frame: pd.DataFrame) -> pd.DataFrame:
    """Within-date uniform rank in [-0.5, +0.5]; NaN stays NaN."""
    r = frame.rank(axis=1)
    n = frame.notna().sum(axis=1)
    return r.sub(1.0).div((n - 1).replace(0, np.nan), axis=0) - 0.5


def xquantile(frame: pd.DataFrame, q: int = N_QUANTILES) -> pd.DataFrame:
    """Within-date quantile label 1..q from AVERAGE ranks.

    Average ranks matter here: 49% of symbol-sessions with news score exactly
    zero net tone (no lexicon word fired), and every one of them must land in
    the same bucket. The buckets are therefore UNEQUAL by construction —
    `quantile_sizes()` prints them, and Q1/Q5 are simply the genuinely
    negative and genuinely positive names.
    """
    pct = frame.rank(axis=1, pct=True)
    return np.ceil(pct * q).where(frame.notna())


# --------------------------------------------------------------------------
# portfolios
# --------------------------------------------------------------------------

def ls_weights(score: pd.DataFrame, q: int = N_QUANTILES) -> pd.DataFrame:
    """Target weights at close t: +1/nL on the top bucket, -1/nS on the bottom."""
    lab = xquantile(score, q)
    top, bot = lab.eq(q), lab.eq(1)
    nt, nb = top.sum(axis=1), bot.sum(axis=1)
    both = (nt > 0) & (nb > 0)
    w = (top.div(nt.replace(0, np.nan), axis=0).fillna(0.0)
         - bot.div(nb.replace(0, np.nan), axis=0).fillna(0.0))
    return w.mul(both.astype(float), axis=0)


def long_weights(score: pd.DataFrame, q: int = N_QUANTILES,
                 bucket: int = N_QUANTILES) -> pd.DataFrame:
    lab = xquantile(score, q)
    sel = lab.eq(bucket)
    n = sel.sum(axis=1)
    return sel.div(n.replace(0, np.nan), axis=0).fillna(0.0)


def pool_weights(score: pd.DataFrame) -> pd.DataFrame:
    """Equal weight of the identical eligible pool — the matched benchmark."""
    sel = score.notna()
    n = sel.sum(axis=1)
    return sel.div(n.replace(0, np.nan), axis=0).fillna(0.0)


def run_portfolio(w: pd.DataFrame, ret1: pd.DataFrame, h: int,
                  cost_bps: float = COST_BPS_ROUND_TRIP) -> dict:
    """Daily P&L of holding `w` for h overlapping cohorts.

    THE SHIFT LIVES HERE: `Wbar.shift(1) * ret1`. Wbar_t is built from news
    readable before close t; ret1_t is earned close(t-1)->close(t); shifting the
    weights one bar forward means the first return the signal can touch is
    close(t)->close(t+1).
    """
    wbar = w.rolling(h, min_periods=1).mean()
    r = ret1.reindex(columns=wbar.columns)
    gross = (wbar.shift(1) * r.fillna(0.0)).sum(axis=1)
    dropped = int(((wbar.shift(1) != 0) & r.isna()).to_numpy().sum())
    turn = (wbar - wbar.shift(1)).abs().sum(axis=1).shift(1)
    one_way = cost_bps / 2.0 / 1e4
    net = gross - turn.fillna(0.0) * one_way
    live = wbar.shift(1).abs().sum(axis=1) > 0
    gross, net, turn = gross[live], net[live], turn[live]
    mt = float(turn.mean())
    be = 2.0 * 1e4 * float(gross.mean()) / mt if mt > 0 else float("nan")
    return {"gross": gross, "net": net, "turnover": turn,
            "mean_gross": float(gross.mean()), "mean_net": float(net.mean()),
            "ann_gross": _ann(float(gross.mean())), "ann_net": _ann(float(net.mean())),
            "sharpe_gross": _sharpe(gross.to_numpy()),
            "sharpe_net": _sharpe(net.to_numpy()),
            "t_gross": _nw_t(gross.to_numpy(), h),
            "mean_turnover": mt, "breakeven_bps": be, "n_days": int(len(gross)),
            "nan_ret_cells": dropped}


def halves(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    mid = len(series) // 2
    return series.iloc[:mid], series.iloc[mid:]


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def shuffled_tone(score: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Permute tone across symbols WITHIN each date (keeps the date structure
    and the cross-sectional distribution; destroys the symbol pairing)."""
    a = score.to_numpy(copy=True)
    for i in range(a.shape[0]):
        row = a[i]
        idx = np.flatnonzero(np.isfinite(row))
        if len(idx) > 1:
            row[idx] = row[rng.permutation(idx)]
    return pd.DataFrame(a, index=score.index, columns=score.columns)


def placebo_tone(tone: pd.DataFrame, mask: pd.DataFrame,
                 rng: np.random.Generator) -> pd.DataFrame:
    """Give every symbol ANOTHER symbol's whole tone series (a derangement),
    then re-impose the real eligibility mask. Each series keeps its own
    autocorrelation, volume seasonality and era drift; only the pairing dies."""
    cols = list(tone.columns)
    n = len(cols)
    perm = rng.permutation(n)
    for _ in range(50):
        if not np.any(perm == np.arange(n)):
            break
        perm = rng.permutation(n)
    out = tone.iloc[:, perm].copy()
    out.columns = cols
    return out.where(mask)


def random_scores(mask: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    a = rng.random(mask.shape)
    return pd.DataFrame(a, index=mask.index, columns=mask.columns).where(mask)


def control_null(kind: str, score: pd.DataFrame, tone_full: pd.DataFrame,
                 ret1: pd.DataFrame, h: int, draws: int = N_CONTROL_DRAWS,
                 seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed + h)
    mask = score.notna()
    means = []
    for _ in range(draws):
        if kind == "shuffle":
            s = shuffled_tone(score, rng)
        elif kind == "placebo":
            s = placebo_tone(tone_full, mask, rng)
        elif kind == "random":
            s = random_scores(mask, rng)
        else:
            raise ValueError(kind)
        res = run_portfolio(ls_weights(s), ret1, h)
        means.append(res["mean_gross"])
    return {"kind": kind, "draws": draws, "means": np.array(means),
            "mean": float(np.mean(means)), "sd": float(np.std(means, ddof=1)),
            "p05": float(np.percentile(means, 5)),
            "p95": float(np.percentile(means, 95))}


# --------------------------------------------------------------------------
# Fama-MacBeth — the row that decides H16
# --------------------------------------------------------------------------

def fama_macbeth(tone_r: pd.DataFrame, ret_r: pd.DataFrame, fwd: pd.DataFrame,
                 regressors: tuple[str, ...]) -> dict:
    """Per-date OLS of fwd return on the named rank regressors; report the
    time-series mean of each coefficient with a Newey-West t-statistic.

    Every regressor is known at close t. `fwd` is close(t)->close(t+h), so the
    earliest price used is one session AFTER the signal.
    """
    X = {"tone": tone_r, "ret": ret_r}
    use = [X[k] for k in regressors]
    dates, lam = [], []
    tn = tone_r.to_numpy()
    rn = ret_r.to_numpy()
    fn = fwd.to_numpy()
    cols = {"tone": tn, "ret": rn}
    for i in range(tn.shape[0]):
        y = fn[i]
        good = np.isfinite(y)
        for k in regressors:
            good &= np.isfinite(cols[k][i])
        if good.sum() < MIN_NAMES:
            continue
        A = np.column_stack([np.ones(good.sum())]
                            + [cols[k][i][good] for k in regressors])
        try:
            beta, *_ = np.linalg.lstsq(A, y[good], rcond=None)
        except np.linalg.LinAlgError:
            continue
        dates.append(tone_r.index[i])
        lam.append(beta[1:])
    lam = np.array(lam)
    out = {"n_dates": len(dates), "dates": pd.DatetimeIndex(dates)}
    for j, k in enumerate(regressors):
        s = lam[:, j] if len(lam) else np.array([])
        out[k] = {"mean": float(np.mean(s)) if len(s) else float("nan"),
                  "t_nw": _nw_t(s, max(len(use), 1)),
                  "series": s}
    return out


def fm_report(tone_r, ret_r, fwd, h: int) -> pd.DataFrame:
    """Univariate tone, univariate same-day return, and the joint model."""
    rows = []
    for name, regs in (("tone only", ("tone",)),
                       ("same-day ret only", ("ret",)),
                       ("JOINT", ("tone", "ret"))):
        r = fama_macbeth(tone_r, ret_r, fwd, regs)
        row = {"model": name, "n_dates": r["n_dates"]}
        for k in ("tone", "ret"):
            if k in regs:
                # NW lags = h: overlapping h-day forward returns
                row[f"lam_{k}_bps"] = 1e4 * r[k]["mean"]
                row[f"t_{k}"] = _nw_t(r[k]["series"], h)
            else:
                row[f"lam_{k}_bps"] = np.nan
                row[f"t_{k}"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# double sort
# --------------------------------------------------------------------------

def double_sort(tone: pd.DataFrame, ret0: pd.DataFrame, fwd: pd.DataFrame,
                n: int = 3) -> pd.DataFrame:
    """Mean forward return by (same-day return tercile) x (tone tercile).

    Sorting on the price move FIRST is the point: if the tone spread only
    exists across return terciles and not within them, tone is a proxy for the
    price move and H16 is reversal in a costume.
    """
    tl = xquantile(tone, n).to_numpy()
    rl = xquantile(ret0, n).to_numpy()
    f = fwd.to_numpy()
    good = np.isfinite(tl) & np.isfinite(rl) & np.isfinite(f)
    grid = np.full((n, n), np.nan)
    cnt = np.zeros((n, n), int)
    for a in range(1, n + 1):
        for b in range(1, n + 1):
            m = good & (rl == a) & (tl == b)
            cnt[a - 1, b - 1] = int(m.sum())
            if m.sum():
                grid[a - 1, b - 1] = float(np.nanmean(f[m]))
    df = pd.DataFrame(1e4 * grid,
                      index=[f"ret T{i}" for i in range(1, n + 1)],
                      columns=[f"tone T{i}" for i in range(1, n + 1)])
    df["spread(T3-T1)"] = df.iloc[:, n - 1] - df.iloc[:, 0]
    df["n_cells"] = cnt.sum(axis=1)
    return df


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------

def _fwd(close: pd.DataFrame, h: int) -> pd.DataFrame:
    """close(t) -> close(t+h). Uses no price before t; aligned to t."""
    return close.shift(-h) / close - 1.0


def run(horizons=HORIZONS, kinds=("all", "specific"), draws=N_CONTROL_DRAWS,
        verbose: bool = True) -> dict:
    ds = build_dataset(verbose=verbose)
    close, ret1 = ds["close"], ds["ret1"]
    results = {"portfolios": [], "fm": {}, "double": {}, "controls": [],
               "coverage": {}}

    tone_all, ret0_all = eligible_scores(ds, "all")
    cov = {
        "sessions": int(len(close)),
        "symbols": int(close.shape[1]),
        "date_min": str(close.index.min().date()),
        "date_max": str(close.index.max().date()),
        "symbol_sessions_eligible_with_news": int(tone_all.notna().sum().sum()),
        "mean_cross_section": float(tone_all.notna().sum(axis=1).mean()),
        "dates_ranked": int((tone_all.notna().sum(axis=1) >= MIN_NAMES).sum()),
        "tone_zero_share": float((tone_all == 0).sum().sum()
                                 / max(tone_all.notna().sum().sum(), 1)),
        "split_repairs": ds.get("repairs", []),
        "attribution_audit": ds.get("attribution_audit", {}),
        # is tone just the price move in words? (contemporaneous, descriptive)
        "corr_tonerank_retrank": float(
            xrank(tone_all).stack().corr(xrank(ret0_all).stack())),
        "spy_ann_%": (100 * _ann(float(ds["bench"].pct_change().mean()))
                      if ds["bench"] is not None else float("nan")),
    }
    results["coverage"] = cov
    if verbose:
        print("\n" + "=" * 78)
        print("COVERAGE")
        print("=" * 78)
        for k, v in cov.items():
            print(f"  {k:38s} {v}")
        sz = quantile_sizes(tone_all)
        print("  mean quintile sizes (ties at 0 net tone force them uneven):")
        print("   ", {f"Q{i}": round(sz[i], 1) for i in sorted(sz)})

    # ---- H16a / H16b : quintile long-short at each horizon -----------------
    for kind in kinds:
        tone, ret0 = eligible_scores(ds, kind)
        w_ls = ls_weights(tone)
        w_q5 = long_weights(tone, bucket=N_QUANTILES)
        w_q1 = long_weights(tone, bucket=1)
        w_pool = pool_weights(tone)
        for h in horizons:
            ls = run_portfolio(w_ls, ret1, h)
            q5 = run_portfolio(w_q5, ret1, h)
            q1 = run_portfolio(w_q1, ret1, h)
            pool = run_portfolio(w_pool, ret1, h)
            g = ls["gross"]
            h1, h2 = halves(g)
            lo, hi = _block_boot_ci(g.to_numpy(), block=max(h, 5))
            results["portfolios"].append({
                "kind": kind, "h": h,
                "ann_gross_%": 100 * ls["ann_gross"],
                "ann_net_%": 100 * ls["ann_net"],
                "sharpe_gross": ls["sharpe_gross"],
                "t_nw": ls["t_gross"],
                "mean_bps": 1e4 * ls["mean_gross"],
                "ci_lo_bps": 1e4 * lo, "ci_hi_bps": 1e4 * hi,
                "h1_bps": 1e4 * float(h1.mean()), "h2_bps": 1e4 * float(h2.mean()),
                "turnover": ls["mean_turnover"],
                "breakeven_bps": ls["breakeven_bps"],
                "q5_ann_%": 100 * q5["ann_gross"], "q1_ann_%": 100 * q1["ann_gross"],
                "pool_ann_%": 100 * pool["ann_gross"],
                "n_days": ls["n_days"], "nan_cells": ls["nan_ret_cells"],
            })

    # ---- controls, on the primary specification ---------------------------
    tone, ret0 = eligible_scores(ds, "all")
    for h in horizons:
        real = run_portfolio(ls_weights(tone), ret1, h)["mean_gross"]
        for ck in ("shuffle", "placebo", "random"):
            null = control_null(ck, tone, ds["tone"]["all"], ret1, h, draws=draws)
            z = ((real - null["mean"]) / null["sd"]) if null["sd"] > 0 else np.nan
            pv = float((null["means"] >= real).mean())
            results["controls"].append({
                "h": h, "control": ck, "draws": null["draws"],
                "real_bps": 1e4 * real, "null_mean_bps": 1e4 * null["mean"],
                "null_sd_bps": 1e4 * null["sd"],
                "null_p95_bps": 1e4 * null["p95"],
                "z_vs_null": z, "p_one_sided": pv})

    # ---- H16c : Fama-MacBeth, the deciding test ---------------------------
    tone_r, ret_r = xrank(tone), xrank(ret0)
    for h in horizons:
        fwd = _fwd(close, h).where(tone.notna())
        results["fm"][h] = fm_report(tone_r, ret_r, fwd, h)

    # ---- H16d : double sort -----------------------------------------------
    for h in (5, 21):
        if h in horizons:
            fwd = _fwd(close, h).where(tone.notna())
            results["double"][h] = double_sort(tone, ret0, fwd)

    return results


def quantile_sizes(score: pd.DataFrame, q: int = N_QUANTILES) -> dict[int, float]:
    lab = xquantile(score, q)
    return {i: float(lab.eq(i).sum(axis=1).mean()) for i in range(1, q + 1)}


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def report(res: dict) -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 40)

    print("\n" + "=" * 78)
    print("H16a / H16b — tone quintile long-short (Q5-Q1), gross and net of 10 bps")
    print("=" * 78)
    p = pd.DataFrame(res["portfolios"])
    show = p[["kind", "h", "mean_bps", "ci_lo_bps", "ci_hi_bps", "t_nw",
              "h1_bps", "h2_bps", "ann_gross_%", "ann_net_%", "sharpe_gross",
              "turnover", "breakeven_bps"]]
    print(show.to_string(index=False, float_format=lambda x: f"{x:9.3f}"))
    print("\n  mean_bps = mean DAILY long-short return in bps (one obs/date).")
    print("  ci = 95% moving-block bootstrap by date, block = holding period.")
    print("  h1/h2 = first and second half of the sample.")
    print("  breakeven_bps = round-trip cost that takes the gross return to zero.")
    print("\n  matched benchmarks (annualised, gross):")
    print(p[["kind", "h", "q5_ann_%", "q1_ann_%", "pool_ann_%"]]
          .to_string(index=False, float_format=lambda x: f"{x:8.2f}"))

    print("\n" + "=" * 78)
    print("CONTROLS — real long-short mean against three nulls "
          f"({res['controls'][0]['draws']} draws each)")
    print("=" * 78)
    c = pd.DataFrame(res["controls"])
    print(c.to_string(index=False, float_format=lambda x: f"{x:9.3f}"))
    print("\n  p_one_sided = share of null draws at or above the real result.")

    print("\n" + "=" * 78)
    print("H16c — Fama-MacBeth: does tone survive the same-day return?")
    print("=" * 78)
    for h, tab in res["fm"].items():
        print(f"\n  horizon {h} session(s) — coefficients in bps per unit of "
              f"cross-sectional rank (rank spans -0.5..+0.5)")
        print(tab.to_string(index=False, float_format=lambda x: f"{x:9.3f}"))

    print("\n" + "=" * 78)
    print("H16d — double sort: tone spread INSIDE each same-day-return tercile")
    print("=" * 78)
    for h, tab in res["double"].items():
        print(f"\n  horizon {h} sessions, mean forward return in bps")
        print(tab.to_string(float_format=lambda x: f"{x:9.2f}"))
        print("  ret T1 = biggest same-day fall, ret T3 = biggest same-day rise.")

    print("\n" + "=" * 78)
    print("MULTIPLE-TESTING GATE — deflated Sharpe on the BEST of the variants")
    print("=" * 78)
    best = p.loc[p["sharpe_gross"].idxmax()]
    n_days = int(best["n_days"])
    dsr = growth.deflated_sharpe(
        sr=float(best["sharpe_gross"]) / math.sqrt(TDAYS),
        n_trials=N_TRIALS_REGISTERED, n_obs=n_days)
    print(f"  best variant: kind={best['kind']} h={int(best['h'])}  "
          f"gross Sharpe {best['sharpe_gross']:.3f} over {n_days} sessions")
    print(f"  registered trials in this round N={N_TRIALS_REGISTERED} "
          f"(scout/hypotheses.md H16a-H16d); DSR = {dsr:.3f}")
    print("  DSR is the probability the best-looking variant is real given N. "
          "This repo's bar is t > 3.")


# --------------------------------------------------------------------------
# selftest — synthetic, offline, no keys
# --------------------------------------------------------------------------

def _synthetic(n_days=900, n_sym=60, beta=0.0, seed=7):
    """Panel with a PLANTED tone -> next-day-return effect of size `beta`."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n_days)
    cols = [f"S{i:02d}" for i in range(n_sym)]
    tone = pd.DataFrame(rng.choice([-1.0, -0.5, 0.0, 0.5, 1.0], (n_days, n_sym)),
                        index=idx, columns=cols)
    noise = rng.normal(0, 0.015, (n_days, n_sym))
    # tomorrow's return responds to today's tone
    fwd = beta * tone.to_numpy() + noise
    ret1 = pd.DataFrame(np.vstack([np.zeros((1, n_sym)), fwd[:-1]]),
                        index=idx, columns=cols)
    close = (1 + ret1).cumprod() * 100
    return tone, ret1, close


def selftest(verbose: bool = True) -> int:
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append(f"{name}: {detail}")
        if verbose:
            print(f"  [{'ok ' if cond else 'FAIL'}] {name} {detail}")

    print("selftest — synthetic panels, no network, no keys")

    # 1. xrank
    f = pd.DataFrame([[1.0, 2.0, 3.0, np.nan]], columns=list("abcd"))
    r = xrank(f)
    check("xrank spans -0.5..+0.5",
          abs(r.iloc[0, 0] + 0.5) < 1e-12 and abs(r.iloc[0, 2] - 0.5) < 1e-12,
          f"{r.iloc[0].tolist()}")
    check("xrank keeps NaN", bool(np.isnan(r.iloc[0, 3])))

    # 2. quantiles put a tie block in one bucket
    f = pd.DataFrame([[-1, 0, 0, 0, 0, 0, 0, 0, 1, 1]], dtype=float)
    lab = xquantile(f, 5).iloc[0]
    check("tie block lands in one bucket", lab[1:8].nunique() == 1,
          f"labels={lab.tolist()}")

    # 3. planted signal is recovered with the correct sign and magnitude
    tone, ret1, close = _synthetic(beta=0.004)
    res = run_portfolio(ls_weights(tone), ret1, h=1)
    check("planted +signal recovered", res["mean_gross"] > 0.001,
          f"mean={1e4 * res['mean_gross']:.1f}bps")
    tone_n, ret1_n, _ = _synthetic(beta=-0.004, seed=8)
    res_n = run_portfolio(ls_weights(tone_n), ret1_n, h=1)
    check("planted -signal recovered", res_n["mean_gross"] < -0.001,
          f"mean={1e4 * res_n['mean_gross']:.1f}bps")

    # 4. NULL: no planted effect -> long-short mean inside the noise band
    tone0, ret10, _ = _synthetic(beta=0.0, seed=11)
    res0 = run_portfolio(ls_weights(tone0), ret10, h=1)
    check("null panel gives ~0", abs(res0["mean_gross"]) < 3e-4,
          f"mean={1e4 * res0['mean_gross']:.2f}bps")

    # 5. THE LOOKAHEAD PROOF: removing the shift injects same-day contamination
    rng = np.random.default_rng(3)
    n_days, n_sym = 900, 60
    idx = pd.bdate_range("2018-01-01", periods=n_days)
    cols = [f"S{i:02d}" for i in range(n_sym)]
    ret1 = pd.DataFrame(rng.normal(0, 0.015, (n_days, n_sym)), index=idx,
                        columns=cols)
    tone_same = ret1.copy()          # tone == today's return: zero predictive value
    honest = run_portfolio(ls_weights(tone_same), ret1, h=1)["mean_gross"]
    wbar = ls_weights(tone_same).rolling(1).mean()
    cheat = float((wbar * ret1).sum(axis=1).mean())   # NO shift -> lookahead
    check("no-shift version is grossly contaminated", cheat > 50 * abs(honest),
          f"cheat={1e4 * cheat:.0f}bps vs honest={1e4 * honest:.2f}bps")
    check("shifted version of a same-day signal is ~0", abs(honest) < 3e-4,
          f"{1e4 * honest:.2f}bps")

    # 6. cost / break-even arithmetic
    r = run_portfolio(ls_weights(tone), ret1=ret1, h=5, cost_bps=10.0)
    implied = r["mean_gross"] - r["mean_turnover"] * (10.0 / 2 / 1e4)
    check("net = gross - turnover x one-way cost",
          abs(implied - r["mean_net"]) < 1e-9,
          f"{1e4 * implied:.4f} vs {1e4 * r['mean_net']:.4f} bps")
    r2 = run_portfolio(ls_weights(tone), ret1=ret1, h=5,
                       cost_bps=r["breakeven_bps"])
    check("break-even cost zeroes the net return", abs(r2["mean_net"]) < 1e-9,
          f"net={1e4 * r2['mean_net']:.6f}bps at {r['breakeven_bps']:.2f}bps")

    # 7. Fama-MacBeth recovers a planted coefficient and kills a pure proxy
    tone, ret1, close = _synthetic(beta=0.004, seed=21)
    fwd = _fwd(close, 1)
    fm = fm_report(xrank(tone), xrank(ret1), fwd, 1)
    lam = float(fm.loc[fm["model"] == "tone only", "lam_tone_bps"].iloc[0])
    check("FM recovers planted tone coefficient", lam > 20, f"{lam:.1f} bps/rank")
    # a regressor that is a pure copy of the same-day return must not survive
    fm2 = fm_report(xrank(ret1), xrank(ret1), fwd, 1)
    tj = float(fm2.loc[fm2["model"] == "JOINT", "t_tone"].iloc[0])
    check("collinear copy does not get credit in JOINT",
          not np.isfinite(tj) or abs(tj) < 3.0, f"t={tj:.2f}")

    # 8. Newey-West widens with autocorrelation
    x = pd.Series(np.random.default_rng(5).normal(0, 1, 2000)).rolling(10).mean().dropna()
    check("NW t < OLS t on an overlapping series",
          abs(_nw_t(x.to_numpy(), 10)) < abs(_t_stat(x.to_numpy())),
          f"NW={_nw_t(x.to_numpy(), 10):.2f} OLS={_t_stat(x.to_numpy()):.2f}")

    # 9. controls are unbiased on a null panel
    tone0, ret10, _ = _synthetic(beta=0.0, seed=31)
    n = control_null("shuffle", tone0, tone0, ret10, h=1, draws=40, seed=5)
    check("shuffle null centred on zero", abs(n["mean"]) < 2e-4,
          f"{1e4 * n['mean']:.2f}bps sd {1e4 * n['sd']:.2f}")

    print(f"\n{len(fails)} failure(s)")
    for f_ in fails:
        print("  " + f_)
    return 1 if fails else 0


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="h=1,5 and 50 control draws")
    ap.add_argument("--draws", type=int, default=N_CONTROL_DRAWS)
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild the cached dataset from the news panel")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.rebuild:
        build_dataset(force=True)

    t0 = time.time()
    hs = (1, 5) if args.quick else HORIZONS
    draws = 50 if args.quick else args.draws
    res = run(horizons=hs, draws=draws)
    report(res)
    print(f"\n[{time.time() - t0:.0f}s]")
    print("""
VERDICT — see the module docstring and scout/hypotheses.md H16a-H16d.
The registered deciding row is H16c: if the tone coefficient does not survive
the same-day return in the joint regression, the effect is short-term reversal
in a costume and H16 is REJECTED whatever the raw long-short prints.""")


if __name__ == "__main__":
    main()
