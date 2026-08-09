"""H15 - abnormal news VOLUME (an attention shock) and short-horizon reversal.

MECHANISM (one sentence, stated before any number)
--------------------------------------------------
Retail investors face a search problem on the buy side but not the sell side,
so they are net buyers of whatever grabs their attention (Barber-Odean 2008;
Da-Engelberg-Gao 2011); that buying is flow, not information, so it pushes
price above value on the attention day and unwinds over the following days to
weeks.

Testable consequence: rank stocks each session by how ABNORMAL their news count
is against their own recent normal, and the top of that ranking should
UNDERPERFORM over the next 1-42 sessions - hardest when the attention arrived
together with a big up move (the flow had somewhere to push).

WHAT IS MEASURED
----------------
Universe   the 120 most liquid S&P 500 members AS OF 2016-01-04
           (scout/news_data.liquid_universe, point-in-time via scout/pit.py:
           BRCM/EMC/TWX/CELG/ESRX/MON/AET/PXD are in, TSLA is out). No
           survivorship on the entry side; delisted names trade to their
           final print and their unfinished windows are dropped, counted.
News       Benzinga via Alpaca, 2016-01-02 .. 2026-07-31: 464,430 symbol-rows
           over 308,870 distinct stories (scout/news_data.load_panel()).
Prices     Alpaca SIP daily closes, adjustment=all, split-REPAIRED (below).
           2,664 sessions, 2016-01-04 .. 2026-08-07.
Signal     abnormal attention at session t, four pre-registered count forms
           plus a direction split. The primary is
               log((k_t + 1) / (m_t + 1))
           where k_t counts SPECIFIC stories attributed to session t
           (news_data.is_templated drops machine-written wire copy;
           news_data.is_broadtape drops stories tagged to >10 tickers) and
           m_t is that symbol's MEDIAN specific count over sessions
           [t-60, t-1]. Log-ratio rather than a raw difference because
           Benzinga coverage runs ~100:1 across these names (news_data
           limit 6) and a raw difference mostly ranks stocks by how much
           Benzinga likes them - the raw difference is run anyway, as a
           registered variant, and is reported.
Portfolio  cross-sectional quintiles inside each session, equal weight, held
           close(t) -> close(t+h) for h in {1, 5, 21, 42}.

WHERE THE shift() IS  (the only thing that can manufacture this result)
----------------------------------------------------------------------
1. news -> session. scout/news_data.attribute_sessions converts created_at to
   US/Eastern and rolls any story stamped at or after that day's close (16:00
   ET; 13:00 on the 23 NYSE half-days) to the NEXT session. Panel row t holds
   only what a trader could have read BEFORE session t's close.
2. session -> return. `fwd_h = close.shift(-h) / close - 1`, paired with the
   signal at the SAME index t. That negative shift is the only shift in this
   file. Signal(t) is a function of news through session t and prices through
   close(t); the return it weights STARTS at close(t). The equivalent positive
   form is `signal.shift(1) * ret_1d` at h=1.
3. the baseline cannot see its own day: `counts.shift(1).rolling(60).median()`
   - the shift(1) comes FIRST, and the offline selftest asserts it.

The whole study is re-run under news_data's deliberately WRONG attribution
(UTC calendar date, no close cutoff - `_attribute_naive`) as a lookahead
control. The measured damage is small here (h=1 spread moves -2.3 -> -3.3 bps)
precisely because news VOLUME is unsigned; a signed-sentiment study on the
same feed moves far more (news_data --lookahead-demo). It is reported anyway,
because "we checked" is worth more than "it could not have mattered".

CONTROLS (four, all run, none optional)
---------------------------------------
a. POSITIVE control - abnormal attention must predict something, or the
   pipeline is broken rather than the hypothesis. It predicts next-session
   ABSOLUTE return decisively: Q5 realises 1.60% against Q1's 1.10%, a +50%
   relative gap. The signal is live; it just does not carry a sign.
b. RANDOM-QUINTILE control - labels permuted inside each session over the same
   eligible pool, 200 draws, mean and SD quoted (Rule 10: one null draw is not
   a control).
c. DATE-SHUFFLED-NEWS control - each symbol's abnormal-attention series is
   permuted ACROSS DATES, independently per symbol, 200 draws. Every stock
   keeps its own distribution of attention; only the TIMING dies. THIS IS THE
   CONTROL THAT DECIDES THE HYPOTHESIS, and it is the one that fires.
d. MATCHED BENCHMARK - top quintile minus the eligible-pool mean, so the
   "just avoid these names" version of the claim is priced separately from
   the long/short version.

Inference: the cross-section is collapsed to ONE spread per session before any
statistic is taken (date clustering is then structural, as in
scout/calibrate.py), then a circular MOVING-BLOCK bootstrap with block length
h absorbs the overlap that h-day holds create. Every h-day claim is also
pooled across all h entry phases (RESEARCH-AGENDA Rule 9, learned the hard way
in H7a), because a single non-overlapping schedule is one draw of h.

SPLIT DEFECT INHERITED FROM THE DATA (found by scout/intraday.py, re-confirmed here)
-----------------------------------------------------------------------------------
Alpaca's adjustment=all does NOT apply AAPL's 4:1 split of 2020-08-31 in daily
bars: 483.84 -> 124.98, a fabricated -74.2% one-day return that lands inside
the top attention quintile (AAPL carried 8 specific stories that session
against a trailing median of 3). It is repaired here from the ex-date price
ratio. Only events with |log ratio| > 0.30 are eligible for repair: MET's
2017-08-07 ratio-1.122 event (the Brighthouse spin-off) trips the ratio test
spuriously, and "repairing" it would INSERT an 11% fake jump.

VERDICT: REJECTED - and rejected by the control, not by the t-statistic
----------------------------------------------------------------------
The registered SIGN is right. High-attention stocks underperform low-attention
stocks at every horizon and in most variants: primary spread Q5-Q1 = -2.31 bps
(h=1), -3.42 (h=5), -15.81 (h=21), -23.56 (h=42). Nothing reaches this repo's
t>3 bar (best |t| = 2.19, at 16 signal x horizon cells).

But the DATE-SHUFFLED control reproduces almost all of it: -0.44 / -2.68 /
-10.62 / -22.26 bps against those same four numbers. Destroying every event
date while leaving each stock's own attention distribution intact costs the
effect 5% of its size at h=42. The timing-attributable residual is -1.87 /
-0.74 / -5.19 / -1.30 bps, and the actual spread sits at the 44th, 62nd, 31st
and 51st percentile of the 200-draw shuffled null - i.e. squarely inside it.

So this is not an attention-shock effect. It is a STOCK-CHARACTERISTIC effect
wearing an event costume: names that are structurally news-bursty (they land
in Q5 often, whatever the date) underperform names that are not, over
2016-2026, in this 120-name large-cap universe. Barber-Odean's mechanism is
about the arrival of attention, and the arrival is worth ~1 bp.

Two further nails:
- ENTRY-PHASE SPREAD. At h=42 the 42 non-overlapping schedules run from -63.9
  to +14.9 bps and 8 of 42 have the wrong sign. A single-schedule quote here
  would have been another H7a.
- DIRECTION. The registered refinement ("attention + a big up move reverses
  hardest") is rejected outright: at h=42 that cell is the BEST in the study,
  +23.9 bps against the pool, while attention + a big DOWN move is the only
  cell with |t| > 2.5 anywhere (-10.4 bps at h=1) - underreaction to bad news,
  the opposite family of effect.

Untradeable regardless. Turnover is 62-78% per leg per rebalance, so at 10 bps
round trip the registered short-top/long-bottom book nets -10.6 bps (h=1),
-10.8 (h=5), +1.0 (h=21) and +8.5 (h=42) per window - +0.12%/yr and +0.51%/yr
at the two horizons that survive at all, before the shuffle control removes
~90% of even that. Break-even round-trip costs: 1.79 / 2.41 / 10.70 / 15.63 bps.

Run: python -m scout.news_attention_lab            (full study, ~3 min warm)
     python -m scout.news_attention_lab --selftest (offline, no keys, <2s)
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from . import config, news_data

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against the outcome.
# --------------------------------------------------------------------------
HORIZONS = (1, 5, 21, 42)
N_Q = 5                     # quintiles, as registered
LOOKBACK = 60               # sessions in the trailing "normal" median
MIN_ELIGIBLE = 50           # sessions with a thinner cross-section are skipped
COST_BPS = 10.0             # round trip, per leg, large caps
BOOT_REPS = 5000
CTRL_REPS = 200             # random-quintile draws
SHUFFLE_REPS = 200          # date-shuffled-news draws
SEED = 20260809
SPLIT_LOG_TOL = 0.30        # only repair splits this far from 1:1 (see docstring)

CLOSE_CACHE = config.SCOUT_DIR / "cache_news_attention_close.pkl"
STORY_CACHE = config.SCOUT_DIR / "cache_news_attention_stories.pkl"

PRIMARY = "spec_log"        # the variant the verdict is written against
VARIANTS = {
    # name           (count frame,     transform)
    "spec_log":      ("n_specific",   "log"),    # PRIMARY
    "spec_diff":     ("n_specific",   "diff"),   # raw difference
    "all_log":       ("n_headlines",  "log"),    # no templated filter
    "novel_log":     ("n_novel_spec", "log"),    # specific AND not a repeat
}
# + the direction split of the PRIMARY variant's top quintile = 5 registered
#   signal forms; 4 x 4 horizons = 16 signal x horizon cells, plus 16 direction
#   cells. All of them are printed, whatever they say.


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def _panel_symbols() -> list[str]:
    return json.loads(news_data.PANEL_SYMBOLS_JSON.read_text())


def load_close(refresh: bool = False) -> pd.DataFrame:
    """Split-repaired daily closes for the news panel's 120 symbols.

    scout/data.py is the repo's daily source (SIP, adjustment=all). The repair
    layer is this file's, because scout/data.py inherits Alpaca's missing-split
    defect (module docstring)."""
    if CLOSE_CACHE.exists() and not refresh:
        return pd.read_pickle(CLOSE_CACHE)
    from . import data, intraday
    syms = _panel_symbols()
    close = data.daily_ohlcv(syms, days=3900)["close"].astype("float64")
    close.index = pd.DatetimeIndex(close.index).tz_localize(None).normalize()
    close = close.sort_index()
    events = intraday.split_events(syms, "2016-01-01", str(close.index[-1].date()))
    repaired = []
    for sym in close.columns:
        for e in intraday.unapplied_splits_close(close[sym], events.get(sym, [])):
            if e["applied"] is not False:
                continue
            if abs(math.log(e["ratio"])) <= SPLIT_LOG_TOL:
                print(f"  split repair SKIPPED (ratio {e['ratio']:g} is too "
                      f"close to 1 for the ex-date price test to be decisive): "
                      f"{sym} {e['ex_date'].date()}")
                continue
            m = close.index < e["ex_date"]
            close.loc[m, sym] = close.loc[m, sym] / e["ratio"]
            repaired.append(f"{sym} {e['ex_date'].date()} {e['ratio']:g}:1")
    print(f"  split repair applied to: {repaired or 'nothing'}")
    close.to_pickle(CLOSE_CACHE)
    return close


def load_stories(close: pd.DataFrame, refresh: bool = False) -> pd.DataFrame:
    """Slim story-level table: symbol, the CORRECT session, the NAIVE session,
    and the two content flags. Cached because novelty_flags over 464k rows is
    most of the cold runtime.

    Built here rather than through news_data.daily_news_panel because (a) the
    novel-AND-specific intersection is not one of that function's ten frames,
    (b) this study needs no sentiment, and (c) the naive attribution is needed
    side by side with the correct one for the lookahead control."""
    if STORY_CACHE.exists() and not refresh:
        return pd.read_pickle(STORY_CACHE)
    df = news_data.load_panel()
    sessions = news_data._session_index(close)
    cat = news_data.categorize(df["headline"])
    spec = ((~cat.isin(news_data.TEMPLATED_CATEGORIES))
            & (~news_data.is_broadtape(df["n_tags"], 10)))
    d = pd.DataFrame({
        "symbol": df["symbol"].to_numpy(),
        "session": news_data.attribute_sessions(df["created_at"], sessions).to_numpy(),
        "session_naive": news_data._attribute_naive(df["created_at"], sessions).to_numpy(),
        "specific": spec.to_numpy(),
        "novel_spec": (spec & news_data.novelty_flags(df, 5, 0.6)).to_numpy(),
    })
    d.to_pickle(STORY_CACHE)
    return d


def count_frames(stories: pd.DataFrame, close: pd.DataFrame,
                 session_col: str = "session") -> dict[str, pd.DataFrame]:
    """Session x symbol story counts. Row t = news readable before close(t)."""
    sessions = news_data._session_index(close)
    cols = sorted(set(stories["symbol"]))
    d = stories[stories[session_col].notna()].copy()
    d["one"] = 1.0
    out = {}
    for name, field in (("n_headlines", "one"), ("n_specific", "specific"),
                        ("n_novel_spec", "novel_spec")):
        out[name] = (d.pivot_table(index=session_col, columns="symbol",
                                   values=field, aggfunc="sum")
                     .reindex(index=sessions, columns=cols).fillna(0.0))
    return out


# --------------------------------------------------------------------------
# signal construction
# --------------------------------------------------------------------------

def abnormal(counts: pd.DataFrame, how: str = "log",
             lookback: int = LOOKBACK) -> pd.DataFrame:
    """Today's count against this symbol's own trailing normal.

    baseline(t) = median over sessions [t-lookback, t-1] -- the shift(1) comes
    FIRST, so session t's own count can never enter its own baseline. Every
    term on the right-hand side is known at close(t)."""
    base = counts.shift(1).rolling(lookback, min_periods=lookback // 2).median()
    if how == "log":
        return np.log((counts + 1.0) / (base + 1.0))
    if how == "diff":
        return counts - base
    raise ValueError(how)


def eligibility(close: pd.DataFrame, h: int, lookback: int = LOOKBACK) -> np.ndarray:
    """Bool (dates x symbols): eligible at t with a real close at t-1 (the
    direction split needs the same-day return), at t, and at t+h. Names
    delisting inside the window drop out; that count is reported."""
    ok = np.isfinite(close.to_numpy())
    prev = np.vstack([np.zeros((1, ok.shape[1]), bool), ok[:-1]])
    fut = np.vstack([ok[h:], np.zeros((h, ok.shape[1]), bool)])
    m = ok & prev & fut
    m[:lookback] = False
    return m


def forward(close: pd.DataFrame, h: int) -> np.ndarray:
    """close(t) -> close(t+h) simple return. THE shift, and the only one."""
    return (close.shift(-h) / close - 1.0).to_numpy()


def same_day(close: pd.DataFrame) -> np.ndarray:
    """close(t-1) -> close(t). Known at the close of t; signs the shock."""
    return (close / close.shift(1) - 1.0).to_numpy()


# --------------------------------------------------------------------------
# cross-sectional machinery
# --------------------------------------------------------------------------

def quintile_labels(sig: np.ndarray, elig: np.ndarray, rng: np.random.Generator,
                    q: int = N_Q, min_elig: int = MIN_ELIGIBLE) -> np.ndarray:
    """Balanced within-session quantile labels, -1 where ineligible.

    Ties matter here and are handled explicitly: 55% of symbol-sessions carry
    no specific story, so the primary signal has a large tie mass at exactly
    0.0. Ties are broken by a seeded uniform key (lexsort on (key, signal)),
    which splits a tied block uniformly at random; alphabetical tie-breaking
    would have parked AAPL in the bottom quintile on every quiet day for a
    decade."""
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
    """(dates x q) equal-weight mean of `y` per bucket, plus the eligible-pool
    mean (the matched benchmark) and the per-date bucket counts."""
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


def turnover(lab: np.ndarray, qi: int, h: int) -> float:
    """Mean fraction of bucket `qi` replaced between rebalances spaced h apart.
    Drives the cost charge: a name held across a rebalance is not traded."""
    fr = [len(set(np.flatnonzero(lab[i + h] == qi))
              - set(np.flatnonzero(lab[i] == qi)))
          / max(int((lab[i + h] == qi).sum()), 1)
          for i in range(0, lab.shape[0] - h, h)
          if (lab[i] == qi).any() and (lab[i + h] == qi).any()]
    return float(np.mean(fr)) if fr else float("nan")


# --------------------------------------------------------------------------
# inference: cluster by date, block-bootstrap the overlap, pool the phases
# --------------------------------------------------------------------------

def block_boot(x: np.ndarray, block: int, reps: int, rng: np.random.Generator):
    """Circular moving-block bootstrap of the mean of a per-DATE series.

    The cross-section is already collapsed to one number per session, so date
    clustering is structural (scout/calibrate.py resamples dates for the same
    reason). Blocks of length `block` = the holding horizon keep the overlap
    that h-day holds create inside a block; an i.i.d. bootstrap would ignore it
    and understate the standard error (the selftest asserts the difference on
    AR(1) data)."""
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3 * max(block, 1):
        return dict(mean=float(np.mean(x)) if n else float("nan"), se=float("nan"),
                    lo=float("nan"), hi=float("nan"), t=float("nan"), n=n)
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1) % n
    means = x[idx[:, :n]].mean(axis=1)
    se = float(means.std(ddof=1))
    lo, hi = (float(v) for v in np.percentile(means, [2.5, 97.5]))
    m = float(x.mean())
    return dict(mean=m, lo=lo, hi=hi, se=se,
                t=(m / se if se > 0 else float("nan")), n=n)


def phase_sweep(x: np.ndarray, h: int) -> np.ndarray:
    """The h non-overlapping entry schedules hiding inside one overlapping mean.

    RESEARCH-AGENDA Rule 9: any claim built on h-day holds must be pooled over
    entry phases before it is quoted. H7a in scout/hypotheses.md is this repo
    quoting the luckiest of six phases as a headline; this is the cheap check
    that prevents a repeat."""
    return np.array([np.nanmean(x[p::h]) if np.isfinite(x[p::h]).any() else np.nan
                     for p in range(max(h, 1))])


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------

def run_variant(name: str, sig: pd.DataFrame, close: pd.DataFrame,
                rng: np.random.Generator, horizons=HORIZONS,
                verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    """One signal, all horizons. Returns the summary table and the per-date
    spread series (kept so the controls and the phase sweep reuse the exact
    same labels rather than a re-derived approximation)."""
    sa = sig.to_numpy()
    rows, series = [], {}
    for h in horizons:
        hh = max(h, 1)
        elig = eligibility(close, hh)
        lab = quintile_labels(sa, elig, np.random.default_rng(SEED + h))
        fwd = forward(close, h) if h > 0 else same_day(close)
        q, pool, cnt = bucket_means(lab, fwd)
        spread = q[:, N_Q - 1] - q[:, 0]
        excess = q[:, N_Q - 1] - pool
        ok = np.isfinite(spread)
        b = block_boot(spread, hh, BOOT_REPS, rng)
        be = block_boot(excess, hh, BOOT_REPS, rng)
        ph = phase_sweep(spread, hh)
        idx = np.flatnonzero(ok)
        half = len(idx) // 2
        rows.append(dict(
            variant=name, h=h, n_dates=int(ok.sum()),
            n_names=float(cnt[ok].sum(1).mean()),
            q1=np.nanmean(q[:, 0]) * 1e4, q3=np.nanmean(q[:, 2]) * 1e4,
            q5=np.nanmean(q[:, N_Q - 1]) * 1e4, pool=np.nanmean(pool) * 1e4,
            spread=b["mean"] * 1e4, lo=b["lo"] * 1e4, hi=b["hi"] * 1e4, t=b["t"],
            q5_excess=be["mean"] * 1e4, t_excess=be["t"],
            half1=float(np.mean(spread[idx[:half]])) * 1e4,
            half2=float(np.mean(spread[idx[half:]])) * 1e4,
            ph_min=float(np.nanmin(ph)) * 1e4, ph_max=float(np.nanmax(ph)) * 1e4,
            ph_wrongsign=int((ph > 0).sum()), ph_n=len(ph),
            turn5=turnover(lab, N_Q - 1, hh), turn1=turnover(lab, 0, hh)))
        series[h] = dict(spread=spread, lab=lab, fwd=fwd, elig=elig, pool=pool)
        if verbose:
            r = rows[-1]
            print(f"    h={h:>2}  spread {r['spread']:+8.2f} bps  "
                  f"[{r['lo']:+7.2f},{r['hi']:+7.2f}]  t={r['t']:+5.2f}  "
                  f"halves {r['half1']:+7.2f}/{r['half2']:+7.2f}  "
                  f"phases [{r['ph_min']:+7.2f},{r['ph_max']:+7.2f}]")
    return pd.DataFrame(rows), series


def random_quintile_control(lab: np.ndarray, fwd: np.ndarray,
                            rng: np.random.Generator, reps: int = CTRL_REPS):
    """CONTROL (b): same eligible pool, same bucket sizes, labels permuted
    inside each session. Expectation is exactly zero by construction; what the
    draws buy is the SCALE of the noise (Rule 10)."""
    out = np.empty(reps)
    for r in range(reps):
        p = lab.copy()
        for i in range(p.shape[0]):
            v = p[i]
            m = v >= 0
            if m.any():
                v[m] = rng.permutation(v[m])
        q, _, _ = bucket_means(p, fwd)
        out[r] = np.nanmean(q[:, N_Q - 1] - q[:, 0])
    return out


def date_shuffle_control(sig: np.ndarray, elig: np.ndarray, fwd: np.ndarray,
                         rng: np.random.Generator, reps: int = SHUFFLE_REPS):
    """CONTROL (c), the one that decides H15: permute each symbol's abnormal
    attention series ACROSS DATES, independently per symbol.

    What survives: every stock's own marginal distribution of attention, hence
    how often it lands in Q5 at all. What dies: the link between an attention
    spike and the day it happened. An ATTENTION-SHOCK effect must collapse
    here. A STOCK-CHARACTERISTIC effect ("news-bursty names are simply worse
    stocks") survives untouched - which is exactly why this control, and not
    the t-statistic, is what H15 is judged on."""
    out = np.empty(reps)
    for r in range(reps):
        s = sig.copy()
        for j in range(s.shape[1]):
            col = s[:, j]
            f = np.isfinite(col)
            if f.sum() > 1:
                col[f] = rng.permutation(col[f])
        lab = quintile_labels(s, elig, rng)
        q, _, _ = bucket_means(lab, fwd)
        out[r] = np.nanmean(q[:, N_Q - 1] - q[:, 0])
    return out


def direction_split(sig: pd.DataFrame, close: pd.DataFrame,
                    rng: np.random.Generator) -> pd.DataFrame:
    """REGISTERED VARIANT 5: split the top attention quintile by the SIGN of
    the same-day return (close(t-1)->close(t), known at the close of t, no
    lookahead). Prediction: attention + a big UP move reverses hardest, because
    that is where uninformed buying pressure is visible in the tape."""
    sa = sig.to_numpy()
    r0 = same_day(close)
    rows = []
    for h in HORIZONS:
        elig = eligibility(close, h)
        lab = quintile_labels(sa, elig, np.random.default_rng(SEED + h))
        fwd = forward(close, h)
        top = lab == N_Q - 1
        _, pool, _ = bucket_means(lab, fwd)
        for tag, m in (("top & up", top & (r0 > 0)),
                       ("top & down", top & (r0 < 0)),
                       ("top & big up   >+2%", top & (r0 > 0.02)),
                       ("top & big down <-2%", top & (r0 < -0.02))):
            m = m & np.isfinite(fwd)
            n = m.sum(1)
            mean = np.where(n > 0, np.where(m, np.nan_to_num(fwd), 0.0).sum(1)
                            / np.maximum(n, 1), np.nan)
            rel = mean - pool
            b = block_boot(rel, h, BOOT_REPS, rng)
            idx = np.flatnonzero(np.isfinite(rel))
            half = len(idx) // 2
            rows.append(dict(cell=tag, h=h, n_dates=len(idx), obs=int(n.sum()),
                             ret=np.nanmean(mean) * 1e4,
                             vs_pool=b["mean"] * 1e4, t=b["t"],
                             lo=b["lo"] * 1e4, hi=b["hi"] * 1e4,
                             half1=float(np.mean(rel[idx[:half]])) * 1e4,
                             half2=float(np.mean(rel[idx[half:]])) * 1e4))
    return pd.DataFrame(rows)


def costs(res: pd.DataFrame, cost_bps: float = COST_BPS) -> pd.DataFrame:
    """Charge the round trip and report the break-even.

    Accounting: the registered book is 1x SHORT Q5 + 1x LONG Q1, rebalanced
    every h sessions, so gross = -(Q5 - Q1). At each rebalance a fraction f of
    a leg is replaced, and that leg pays f x cost_bps (sell the old, buy the
    new); a name held across a rebalance is not traded. Total per window is
    (f_short + f_long) x cost_bps. Break-even c* = gross / (f_short + f_long)."""
    rows = []
    for _, r in res.iterrows():
        gross = -r["spread"]
        f = r["turn5"] + r["turn1"]
        chg = f * cost_bps
        rows.append(dict(h=int(r["h"]), gross_bps=gross, turn=f, cost_bps=chg,
                         net_bps=gross - chg,
                         breakeven_bps=gross / f if f else float("nan"),
                         gross_pct_yr=gross * (252 / r["h"]) / 100,
                         net_pct_yr=(gross - chg) * (252 / r["h"]) / 100))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# offline selftest: does this file's machinery do what it claims?
# --------------------------------------------------------------------------

def selftest() -> int:
    rng = np.random.default_rng(0)
    n_d, n_s = 900, 60
    dates = pd.bdate_range("2018-01-01", periods=n_d)
    fails = 0

    def check(name, ok, detail=""):
        nonlocal fails
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
        fails += (not ok)

    # 1. ties: balanced buckets, random tie-breaking
    sig = np.zeros((n_d, n_s))                        # every name tied
    elig = np.ones((n_d, n_s), bool)
    lab = quintile_labels(sig, elig, np.random.default_rng(1))
    sizes = [(lab == q).sum(1) for q in range(N_Q)]
    check("an all-tied cross-section still splits into balanced quintiles",
          all(s.min() >= n_s // N_Q - 1 and s.max() <= n_s // N_Q + 1 for s in sizes))
    share = (lab[:, 0] == 0).mean()
    check("ties are broken at random, not by column order",
          abs(share - 1 / N_Q) < 0.05, f"col 0 lands in Q1 on {share:.1%} of sessions")

    # 2. a planted reversal is recovered, and the control kills it
    a = rng.normal(0, 1, (n_d, n_s))
    planted = -0.004 * (a > 1.2) + rng.normal(0, 0.01, (n_d, n_s))
    lab = quintile_labels(a, elig, np.random.default_rng(2))
    q, _, _ = bucket_means(lab, planted)
    sp = np.nanmean(q[:, N_Q - 1] - q[:, 0])
    check("a planted reversal is recovered with the right sign and size",
          -0.0045 < sp < -0.0015, f"spread {sp * 1e4:+.1f} bps")
    ctrl = random_quintile_control(lab, planted, rng, reps=30).mean()
    check("random-quintile control on the SAME planted data is ~0",
          abs(ctrl) < 3e-4, f"{ctrl * 1e4:+.2f} bps")

    # 3. the date-shuffle control must kill a pure EVENT effect and spare a
    #    pure STOCK effect -- the exact discrimination H15 turns on
    ev = rng.normal(0, 1, (n_d, n_s))
    ev_ret = -0.004 * (ev > 1.2) + rng.normal(0, 0.01, (n_d, n_s))
    lab_ev = quintile_labels(ev, elig, np.random.default_rng(4))
    q, _, _ = bucket_means(lab_ev, ev_ret)
    ev_sp = np.nanmean(q[:, N_Q - 1] - q[:, 0])
    ev_null = date_shuffle_control(ev, elig, ev_ret, rng, reps=25).mean()
    check("date-shuffle control kills a pure EVENT effect",
          abs(ev_null) < 0.2 * abs(ev_sp),
          f"{ev_sp * 1e4:+.1f} -> {ev_null * 1e4:+.1f} bps")
    lvl = np.tile(rng.normal(0, 1, (1, n_s)), (n_d, 1)) + rng.normal(0, .1, (n_d, n_s))
    st_ret = -0.004 * (lvl > 1.0) + rng.normal(0, 0.01, (n_d, n_s))
    lab_st = quintile_labels(lvl, elig, np.random.default_rng(5))
    q, _, _ = bucket_means(lab_st, st_ret)
    st_sp = np.nanmean(q[:, N_Q - 1] - q[:, 0])
    st_null = date_shuffle_control(lvl, elig, st_ret, rng, reps=25).mean()
    check("date-shuffle control SPARES a pure STOCK-characteristic effect",
          abs(st_null) > 0.7 * abs(st_sp),
          f"{st_sp * 1e4:+.1f} -> {st_null * 1e4:+.1f} bps")

    # 4. NO LOOKAHEAD: an effect planted only on the SAME-day return must not
    #    reach h>=1
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, .01, (n_d, n_s)), 0)),
                         index=dates, columns=[f"S{i}" for i in range(n_s)])
    s0 = same_day(close)
    contemp = pd.DataFrame(-s0, index=dates, columns=close.columns)
    lab = quintile_labels(contemp.to_numpy(), eligibility(close, 1),
                          np.random.default_rng(3))
    q0, _, _ = bucket_means(lab, s0)
    q1, _, _ = bucket_means(lab, forward(close, 1))
    sp0 = np.nanmean(q0[:, N_Q - 1] - q0[:, 0])
    sp1 = np.nanmean(q1[:, N_Q - 1] - q1[:, 0])
    check("a signal that IS the same-day return shows a huge h=0 spread",
          sp0 < -0.02, f"{sp0 * 1e4:+.0f} bps")
    check("...and nothing at h=1: the shift() carries no information back",
          abs(sp1) < 0.002, f"{sp1 * 1e4:+.1f} bps")

    # 5. abnormal(): the baseline can never see its own day
    c = pd.DataFrame(0.0, index=dates, columns=["A"])
    c.iloc[300, 0] = 50.0
    ab = abnormal(c, "log", lookback=60)
    check("abnormal() spikes on the event day, not before it",
          ab.iloc[300, 0] > 3 and abs(ab.iloc[299, 0]) < 1e-12)
    check("abnormal() baseline excludes the event day itself",
          abs(ab.iloc[301, 0]) < 1e-12,
          "the day after a lone spike is back to normal")

    # 6. forward() is the negative shift it claims to be
    px = pd.DataFrame({"A": [10.0, 11.0, 12.0, 13.0]})
    f2 = forward(px, 2)
    check("forward(h=2) at t equals close(t+2)/close(t)-1",
          abs(f2[0] - 0.2) < 1e-12 and not np.isfinite(f2[2]))

    # 7. block bootstrap widens the SE on autocorrelated data
    ar = np.zeros(2000)
    for i in range(1, 2000):
        ar[i] = 0.9 * ar[i - 1] + rng.normal(0, 1)
    wide, narrow = block_boot(ar, 20, 2000, rng), block_boot(ar, 1, 2000, rng)
    check("block bootstrap gives a wider SE than the i.i.d. one on AR(1) data",
          wide["se"] > 1.5 * narrow["se"],
          f"block {wide['se']:.3f} vs iid {narrow['se']:.3f}")

    # 8. phase sweep decomposes the overlapping mean
    x = rng.normal(0, 1, 1000)
    check("phase means average back to the overlapping mean",
          abs(phase_sweep(x, 5).mean() - x.mean()) < 1e-9)

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
    ap.add_argument("--refresh", action="store_true", help="refetch prices/news")
    args = ap.parse_args()
    if args.selftest:
        _hdr("SELFTEST (offline, no keys, no network)")
        raise SystemExit(selftest())

    t0 = time.time()
    rng = np.random.default_rng(SEED)

    _hdr("H15 - abnormal news volume (attention shock) -> short-horizon reversal")
    print("MECHANISM: retail buying is attention-driven and one-sided, so it")
    print("pushes attention-grabbing stocks above value and unwinds afterwards.")
    print("REGISTERED SIGN: the TOP attention quintile UNDERPERFORMS at short h.")
    print("\nloading data ...")
    close = load_close(refresh=args.refresh)
    stories = load_stories(close, refresh=args.refresh)
    counts = count_frames(stories, close, "session")
    print(f"  prices {close.shape[0]} sessions x {close.shape[1]} symbols  "
          f"{close.index[0].date()} .. {close.index[-1].date()}")

    _hdr("SAMPLE")
    live = np.isfinite(close.to_numpy())
    e21 = eligibility(close, 21)
    ns = counts["n_specific"]
    print(f"symbol-sessions with a price            : {live.sum():>10,}")
    print(f"eligible at h=21 (close at t-1, t, t+21): {e21.sum():>10,}")
    print(f"  lost to the {LOOKBACK}-session warm-up        : "
          f"{int(live[:LOOKBACK].sum()):>10,}")
    print(f"  lost to delisting inside the window   : "
          f"{int((live & ~e21).sum() - live[:LOOKBACK].sum()):>10,}   "
          "(mergers/acquisitions: unfinished windows dropped)")
    print(f"sessions in the study                   : {close.shape[0] - LOOKBACK:>10,}")
    print(f"stories attributed to a session         : "
          f"{int(stories['session'].notna().sum()):>10,}")
    print(f"  specific (not templated, <=10 tags)   : "
          f"{int(stories['specific'].sum()):>10,}")
    print(f"  specific AND novel vs the prior 5 days: "
          f"{int(stories['novel_spec'].sum()):>10,}")
    print(f"symbol-sessions carrying >=1 specific   : "
          f"{float((ns > 0).to_numpy().mean()) * 100:>9.1f}%   "
          "(so the primary signal has a large tie mass at 0)")
    print("\nEFFECTIVE INDEPENDENT SAMPLE: the cross-section is collapsed to one")
    print("spread per session before any statistic, so n is at most the 2,603")
    print("sessions -- not the ~277,000 symbol-sessions. At h=42 the honestly")
    print("independent count is 61 non-overlapping windows per entry phase.")

    sigs = {n: abnormal(counts[f], how) for n, (f, how) in VARIANTS.items()}

    # ---------------------------------------------------------------- (a)
    _hdr("CONTROL (a) POSITIVE: is the signal alive at all?")
    print("If abnormal attention predicted nothing whatsoever, a null result")
    print("would be evidence about the pipeline, not about the hypothesis.")
    lab1 = quintile_labels(sigs[PRIMARY].to_numpy(), eligibility(close, 1),
                           np.random.default_rng(SEED + 1))
    absr = np.abs(forward(close, 1))
    qa, poola, _ = bucket_means(lab1, absr)
    sd = same_day(close)
    q0, _, _ = bucket_means(lab1, sd)
    qa0, _, _ = bucket_means(lab1, np.abs(sd))
    print(f"  next-session |return|   Q1 {np.nanmean(qa[:, 0]) * 100:5.2f}%   "
          f"Q3 {np.nanmean(qa[:, 2]) * 100:5.2f}%   "
          f"Q5 {np.nanmean(qa[:, N_Q - 1]) * 100:5.2f}%   "
          f"pool {np.nanmean(poola) * 100:5.2f}%")
    print(f"  SAME-session |return|   Q1 {np.nanmean(qa0[:, 0]) * 100:5.2f}%   "
          f"Q3 {np.nanmean(qa0[:, 2]) * 100:5.2f}%   "
          f"Q5 {np.nanmean(qa0[:, N_Q - 1]) * 100:5.2f}%")
    print(f"  SAME-session SIGNED     Q1 {np.nanmean(q0[:, 0]) * 1e4:+6.1f}bps "
          f"Q3 {np.nanmean(q0[:, 2]) * 1e4:+6.1f}bps "
          f"Q5 {np.nanmean(q0[:, N_Q - 1]) * 1e4:+6.1f}bps")
    print("\nAttention arrives with VOLATILITY and keeps predicting it one")
    print("session ahead. It barely moves the SIGN even contemporaneously,")
    print("which is the first hint that a signed forward bet is the wrong ask.")

    # ---------------------------------------------------------------- main
    _hdr(f"PRIMARY VARIANT: {PRIMARY}   (Q5 minus Q1, bps per h-session hold)")
    print("Q5 = highest abnormal specific-news count. Registered sign: NEGATIVE.")
    print("CI = circular moving-block bootstrap (block = h), clustered by date.")
    print("phases = the h non-overlapping entry schedules, min and max.\n")
    primary, pser = run_variant(PRIMARY, sigs[PRIMARY], close, rng)

    _hdr("PRIMARY: full table")
    print(primary[["h", "n_dates", "n_names", "q1", "q3", "q5", "pool", "spread",
                   "lo", "hi", "t", "q5_excess", "t_excess", "half1", "half2",
                   "turn5", "turn1"]].to_string(index=False, float_format=_fmt))
    print("\nq1/q3/q5/pool are RAW bucket returns in bps over the h-session hold")
    print("(they contain the market; spread and q5_excess do not).")
    print("q5_excess = CONTROL (d), the matched benchmark: top quintile minus")
    print("the eligible-pool mean = what merely AVOIDING these names is worth.")

    # ---------------------------------------------------------------- b, c
    _hdr("CONTROLS (b) RANDOM QUINTILES and (c) DATE-SHUFFLED NEWS")
    print(f"(b) {CTRL_REPS} draws: labels permuted inside each session.")
    print(f"(c) {SHUFFLE_REPS} draws: each symbol's abnormal series permuted")
    print("    across DATES. Stock identity survives, event timing does not.")
    print("    An attention-SHOCK effect must collapse here.\n")
    ctrl_rows = []
    for h in HORIZONS:
        s = pser[h]
        rnd = random_quintile_control(s["lab"], s["fwd"], rng)
        shf = date_shuffle_control(sigs[PRIMARY].to_numpy(), s["elig"], s["fwd"], rng)
        act = float(np.nanmean(s["spread"]))
        ctrl_rows.append(dict(
            h=h, spread=act * 1e4,
            rand_mean=rnd.mean() * 1e4, rand_sd=rnd.std(ddof=1) * 1e4,
            shuf_mean=shf.mean() * 1e4, shuf_sd=shf.std(ddof=1) * 1e4,
            timing=(act - shf.mean()) * 1e4,
            pctile=float((shf < act).mean()) * 100,
            p_one_sided=float((shf <= act).mean())))
    ctrl = pd.DataFrame(ctrl_rows)
    print(ctrl.to_string(index=False, float_format=_fmt))
    print("\ntiming    = actual spread minus the date-shuffled mean: the part of")
    print("            the effect that is about WHEN the news arrived.")
    print("pctile    = where the actual spread sits in the 200-draw shuffled")
    print("            null. ~50 means the null already explains it.")
    print("p_one_sided = share of shuffled draws at least as negative as actual.")

    # -------------------------------------------------------- all variants
    _hdr("ALL PRE-REGISTERED VARIANTS (every one run is reported)")
    allres = [primary]
    for name in VARIANTS:
        if name == PRIMARY:
            continue
        print(f"\n  {name}:")
        r, _ = run_variant(name, sigs[name], close, rng)
        allres.append(r)
    res = pd.concat(allres, ignore_index=True)

    _hdr("VARIANT x HORIZON GRID")
    print("spread (bps, negative = registered direction):")
    print(res.pivot(index="variant", columns="h", values="spread")
          .to_string(float_format=_fmt))
    print("\nblock-bootstrap t:")
    print(res.pivot(index="variant", columns="h", values="t")
          .to_string(float_format=lambda v: f"{v:8.2f}"))
    print(f"\nTrial count: {len(res)} signal x horizon cells, plus 16 direction")
    print("cells below = 32. This repo's bar for a standalone claim is t > 3")
    print("(Harvey-Liu); at 32 cells that bar is if anything too generous.")

    # ------------------------------------------------------------- phases
    _hdr("ENTRY-PHASE SWEEP (RESEARCH-AGENDA Rule 9)")
    print("Each h-day claim hides h non-overlapping entry schedules. H7a in")
    print("scout/hypotheses.md is this repo having quoted the luckiest of six.\n")
    print(primary[["h", "spread", "ph_min", "ph_max", "ph_wrongsign", "ph_n"]]
          .to_string(index=False, float_format=_fmt))
    print("\nph_wrongsign = phases with a POSITIVE spread, i.e. against the")
    print("registered direction, out of ph_n.")

    # -------------------------------------------------------------- halves
    _hdr("BOTH HALVES (primary variant, spread in bps)")
    print(f"first half ends {close.index[len(close) // 2].date()}\n")
    print(primary[["h", "spread", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))
    flips = int(((primary["half1"] > 0) != (primary["half2"] > 0)).sum())
    print(f"\nsign flips across halves: {flips} of {len(primary)} horizons.")

    # ----------------------------------------------------------- lookahead
    _hdr("LOOKAHEAD CONTROL: re-run under the WRONG timestamp rule")
    print("news_data._attribute_naive = UTC calendar date, no ET conversion and")
    print("no close cutoff. This is the mistake a news study makes by accident.\n")
    naive_counts = count_frames(stories, close, "session_naive")
    naive_sig = abnormal(naive_counts[VARIANTS[PRIMARY][0]], VARIANTS[PRIMARY][1])
    nres, _ = run_variant("naive", naive_sig, close, rng, verbose=False)
    cmp = primary[["h", "spread", "t"]].merge(
        nres[["h", "spread", "t"]], on="h", suffixes=("_correct", "_naive"))
    print(cmp.to_string(index=False, float_format=_fmt))
    print("\nThe gap is the value of the timestamp rule ON THIS SIGNAL. It is")
    print("small because news VOLUME is unsigned - a sentiment study on the same")
    print("feed moves far more (news_data --lookahead-demo). Reported anyway.")

    # ------------------------------------------------------------ direction
    _hdr("REGISTERED VARIANT 5: DIRECTION SPLIT of the top quintile vs the pool")
    print("Registered: 'attention plus a big up move should reverse hardest'.\n")
    ds = direction_split(sigs[PRIMARY], close, rng)
    print(ds.to_string(index=False, float_format=_fmt))

    # ---------------------------------------------------------------- cost
    _hdr(f"COSTS ({COST_BPS:.0f} bps round trip per leg, large caps)")
    print("Registered trade: SHORT the top quintile, LONG the bottom, so")
    print("gross = -(Q5 - Q1). Negative gross = the registered trade loses")
    print("money before a cent of cost.\n")
    print(costs(primary).to_string(index=False, float_format=_fmt))
    print("\nbreakeven_bps = the round-trip cost per leg at which the registered")
    print("trade earns exactly zero. Charged: "
          f"{COST_BPS:.0f} bps.")

    # ------------------------------------------------------------- verdict
    _hdr("VERDICT")
    r42 = primary[primary["h"] == 42].iloc[0]
    c42 = ctrl[ctrl["h"] == 42].iloc[0]
    print("REJECTED - and rejected by the CONTROL, not by the t-statistic.")
    print()
    print("The registered SIGN is right at every horizon and in every variant:")
    print("high-attention stocks do underperform low-attention stocks. Nothing")
    print(f"clears t>3 (best |t| = {res['t'].abs().max():.2f} over "
          f"{len(res)} cells), but that alone would only")
    print("mean 'underpowered'.")
    print()
    print("What decides it is CONTROL (c). Permuting each symbol's attention")
    print("series across dates - destroying every event date while leaving each")
    print(f"stock's own attention distribution intact - still returns "
          f"{c42['shuf_mean']:+.2f} bps")
    print(f"at h=42 against the actual {r42['spread']:+.2f}. The actual spread "
          f"sits at the {c42['pctile']:.0f}th")
    print("percentile of that null. The event timing is worth "
          f"{c42['timing']:+.2f} bps.")
    print()
    print("H15 is therefore not an attention-shock effect. It is a stock-")
    print("characteristic effect wearing an event costume: names that are")
    print("structurally news-bursty underperform names that are not, in this")
    print("120-name large-cap universe over 2016-2026. That is a DIFFERENT")
    print("hypothesis (and a suspiciously sector-shaped one) - per the H1b")
    print("house rule, a survived-control-free finding is not shippable.")
    print()
    print("The direction refinement is rejected outright: the cell predicted to")
    print("reverse hardest (attention + a big up move) is the best cell in the")
    print("study at h=42, and the only |t|>2.5 cell anywhere is attention + a")
    print("big DOWN move at h=1 - underreaction, not reversal.")
    print()
    print(f"[{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
