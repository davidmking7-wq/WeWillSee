"""H21 - short-horizon reversal as a LIQUIDITY premium, conditioned on news.

MECHANISM (one sentence, stated before any number)
--------------------------------------------------
A one-week price move produced by uninformed liquidity DEMAND has to be paid
for, so it reverses - the reversal return IS the fee earned by whoever absorbed
the order flow (Campbell-Grossman-Wang 1993; Nagel RFS 2012 "Evaporating
Liquidity") - while a move produced by INFORMATION does not reverse, because it
is the new price.

Testable consequence, and it is a CONDITIONING claim rather than a signal
claim: rank stocks by their prior 5-session return, buy the losers and sell the
winners, and the trade should work among stocks that had NO news in the
formation week and fail among stocks that did. The difference between those two
legs is the hypothesis; either leg on its own is not.

WHY THIS ROW EXISTS
-------------------
This repo has tested momentum four times and measured it sorting nothing
(decile 1 minus decile 10 = -0.26% at 42 td over ten years). Short-horizon
REVERSAL is the opposite sign at the opposite horizon and had never been tested
here once. H15 and H16 rejected news as a SIGNAL; H21 uses news only as a
CONDITIONER on a price signal, which is a different claim and survives their
rejection.

WHAT IS MEASURED
----------------
Universe   the 120 most liquid S&P 500 members AS OF 2016-01-04
           (scout/news_data.liquid_universe, point-in-time via scout/pit.py:
           BRCM/EMC/TWX/CELG/ESRX/MON/AET/PXD are in, TSLA is out), 2016-01-04
           .. 2026-08-07, 2,664 sessions.
Prices     Alpaca SIP daily closes, adjustment=all, SPLIT-REPAIRED by
           scout/news_attention_lab.load_close (reused, not reimplemented),
           then stale-quote retired (below).
News       Benzinga via Alpaca, the cached 120-name panel, 464,430 attributed
           symbol-rows (scout/news_data.load_panel()).
Signal     sig(t) = close(t-1)/close(t-6) - 1, the 5-session return ending at
           close(t-1). Session t is SKIPPED: a one-day gap is what kills
           bid-ask bounce, the classic fake reversal, and the no-skip version
           is run as a registered variant so the reader can see what the gap
           is worth.
Book       cross-sectional quintiles of sig inside each session, equal weight,
           LONG Q1 (the losers) and SHORT Q5 (the winners), held close(t) ->
           close(t+h), h in {1, 5, 10, 21}, primary h=5.
Groups     within each session the eligible names are split by whether they
           carried any SPECIFIC story (news_data.is_templated drops machine
           wire copy, is_broadtape drops >10-tag stories) in sessions t-5..t-1
           - the same five sessions the formation return spans.

WHERE THE shift() IS (the only thing that can manufacture this result)
----------------------------------------------------------------------
1. news -> session. news_data.attribute_sessions converts created_at to
   US/Eastern and rolls any story stamped at or after that day's close (16:00
   ET; 13:00 on NYSE half-days) to the NEXT session, so row t holds only what
   a trader could have read BEFORE close(t). The formation-week count is
   `counts.shift(1).rolling(5).sum()` - the shift(1) comes FIRST, so session
   t's own news can never enter it.
2. price -> signal. `sig = close.shift(1) / close.shift(6) - 1`.
3. signal -> return. `fwd_h = close.shift(-h) / close - 1`, paired at the SAME
   index t. Signal and return touch DISJOINT prices: the signal reads closes at
   t-6 and t-1, the return reads closes at t and t+h. Nothing else in this file
   shifts anything.
4. the abnormal-news baseline cannot see its own formation window:
   `k.shift(5).rolling(60).median()`, so the baseline ends at t-6.
5. the liquidity rank is `(close*volume).rolling(60).mean().shift(1)`, known
   at close(t-1).

CONTROLS (four, all run, none optional)
---------------------------------------
a. POSITIVE control - the conditioning variable must be alive. It is: names
   with news in the formation week move 3.22% over that week against 2.67% for
   the quiet names, and 1.36% vs 1.29% on the next session. News marks bigger
   moves, which is the premise the split needs.
b. RANDOM-PICK control - quintile labels permuted inside each session over the
   identical eligible pool, 200 draws, mean AND SD quoted (Rule 10: one null
   draw is not a control).
c. DATE-SHUFFLE of the signal - each symbol's formation return permuted across
   dates, 200 draws. Unlike H15 this control is DISCRIMINATING rather than
   merely null: reversal is a timing claim by construction, so it MUST die
   here, and if it does not, the "reversal" was a stock characteristic.
d. NEWS-LABEL SHUFFLE - the news/no-news assignment permuted across symbols
   within each date preserving the per-date group sizes, 200 draws. THIS IS
   THE NULL FOR THE DIFFERENCE and it is what decides H21b.
e. MATCHED BENCHMARKS - the equal-weight eligible pool (for the long-only leg)
   and SPY (for Rule 13's beta regression).
Every permutation p-value is printed next to the ratio of the null's SD to the
real series' block-bootstrap SE, as Rule 14 requires.

DATA HYGIENE - the repo's 5.1% unadjusted-split debt, and something worse
-------------------------------------------------------------------------
Closes are the split-repaired series (AAPL's missing 2020-08-31 4:1 among
them). On top of that this file retires a symbol permanently from its first run
of >=10 IDENTICAL consecutive closes, which is how a delisted ticker's frozen
quote and a reused-ticker splice both present. That rule fires on exactly two
names and it matters enormously HERE:

  EMC  frozen at one price from 2016-09-06 (Dell closed the acquisition; the
       ticker kept printing) - 2,494 sessions dropped
  MON  frozen from 2018-06-06 (Bayer closed the acquisition), then a DIFFERENT
       company reuses the ticker on 2021-03-16 at 9.79 against the stale
       127.95, a fabricated -92.4% one-day return - 1,148 sessions dropped

Left in, those two contribute 2,577 of the panel's 4,288 EXACTLY-ZERO one-day
returns, and they carry no news by construction - i.e. permanent members of the
no-news group with a guaranteed-zero forward return, sitting on the exact leg
this study is trying to measure. After the retirement the only remaining
|1-day return| > 45% in the whole panel is OXY 2020-03-09 at -52.0%, which is
REAL (the Saudi price war plus the dividend cut), and the study is rerun with
its windows excluded anyway as a registered variant - it moves the h=5 spread
from +6.95 to +7.21 bps and the difference from +11.69 to +11.12.

SAMPLE, AND THE EFFECTIVE INDEPENDENT SAMPLE
--------------------------------------------
2,664 sessions, 2016-01-04 .. 2026-08-07, 120 symbols, 280,359 symbol-sessions
with a usable price and 272,653 eligible at h=5. 17.1% of those carry NO
specific story in the formation week and 82.9% do; the quiet cross-section
averages 17.9 names a day and THINS from ~26 in 2018 to ~12 by 2024 as Benzinga
coverage roughly doubles.

The effective independent sample is NOT the symbol-session count: the
cross-section is collapsed to ONE spread per session before any statistic is
taken (date clustering is then structural, as in scout/calibrate.py), so n is
at most 2,664 dates; at h=5 that is ~532 non-overlapping weekly windows per
entry phase with 5 phases. The DIFFERENCE is thinner still - the quiet leg
needs MIN_CELL=2 names in both extreme quintiles, which it has on 1,488 dates,
i.e. ~297 independent weekly windows.

VERDICT: REJECTED - twice over, and neither failure is about statistical power
-----------------------------------------------------------------------------
1. THERE IS NO UNCONDITIONAL REVERSAL HERE TO CONDITION. Losers minus winners
   earns +1.44 / +6.95 / -0.41 / +19.64 bps at h = 1 / 5 / 10 / 21, with
   block-bootstrap t = +0.54 / +0.69 / -0.03 / +0.94 and a 95% CI at the
   registered h=5 of [-12.32, +26.70]. Both halves agree in sign at h=5
   (+7.31 / +6.59) and the sign is right at three of four horizons, so this is
   a weak positive rather than a wrong sign - but it is 7 bps a week against a
   3.2% weekly cross-sectional dispersion.

2. RULE 13 TAKES EVEN THAT AWAY. The dollar-neutral book runs beta +0.29 /
   +0.33 / +0.24 / +0.15 to SPY: buying losers and shorting winners is a
   long-beta position, because a stock that just fell five days is
   temporarily the high-beta one. Market-adjusted, the h=5 spread is
   -3.35 bps (t=-0.35) and the h=10 spread -15.30 (t=-1.07). In a decade when
   SPY compounded at ~15.8%/yr, the whole gross spread is that beta.

3. THE CONDITIONING - THE ACTUAL HYPOTHESIS - DOES NOT FIRE. On the 1,488
   common dates the quiet leg earns +9.70 bps and the news leg -2.00, a
   DIFFERENCE of +11.69 bps [-12.71, +36.08], t = +0.94. It fails BOTH
   pre-registered failure conditions: the halves are -10.23 then +33.61 (a
   sign flip, which this house calls noise and says so), and the difference
   sits inside the news-label-shuffle null at the 94th percentile, p = 0.12.
   At h=1 the difference is -6.29 bps with the WRONG sign in both halves.

4. THE SHARPER CONDITIONER IS FLAT, NOT MONOTONE. Abnormal news volume in
   terciles gives +8.58 / +3.03 / +8.37 bps - a U, not a slope. Low minus high
   is +0.05 bps, t = +0.01, on 2,566 dates. H21c is the cleanest rejection in
   the file because it has none of the coverage problems: ~38 names a tercile.

5. THE ONE |t| > 2 CELL IS A COVERAGE ARTEFACT, AND THE FILE SAYS SO RATHER
   THAN QUOTING IT. In the top-liquidity half the difference reads +71.19 bps
   with t = 2.54 and p = 0.000 against its own null. It is measured on 159
   dates - 31 independent weekly windows - because the quiet group inside the
   50 most liquid names almost never has two members in both extreme
   quintiles (2.55 on a scorable date). 158 of those 159 dates fall in
   2016-2021 and none in 2024-2025, so the "both halves" of that series are
   both inside the first six years. Relaxing MIN_CELL to 1 puts it at +39.75
   on 910 dates. This is exactly the shape of H7a: a real-looking number that
   is one lucky slice of the calendar.

6. COSTS FINISH IT (H21f). Break-even round-trip cost is 4.44 bps for the
   long/short book on all names, 5.18 quiet, 2.98 news, against the 10 bps
   charged for large caps - so the trade loses 4.4%/yr net at h=5 on measured
   turnover of 1.57x gross per rebalance. The long-only losers book pays one
   leg instead of two and breaks even at 8.45 bps (all) / 17.47 (quiet) /
   5.96 (news). The single cell that clears cost is long-only-quiet at
   +3.52%/yr net - and it is the cell whose halves are -1.14 then +33.79.

WHAT THE STUDY DOES ESTABLISH (so the null is about the world, not the code)
---------------------------------------------------------------------------
- The conditioner is alive: news-week names move 3.22% over the formation
  week against 2.67% for quiet ones, and 1.36% vs 1.29% the next session.
- The date-shuffle control BEHAVES: it takes +6.95 bps to -2.73 +/- 2.56, so
  the little that is there is timing-attributable rather than a stock
  characteristic. That is the opposite of what happened to H15, and it means
  the pipeline can tell the two apart.
- The offline selftest plants a quiet-group-only reversal and recovers it
  (+185.7 quiet vs -1.2 news), then kills it with the news-label shuffle
  (+1.7) and with a ONE-SESSION misalignment of the conditioner (+6.9). The
  machinery would have found this effect had it been there.
- Rule 14 fires hard: the within-date permutation nulls are 4.2x and 3.9x
  TIGHTER than the block-bootstrap SE, so their p = 0.000 is an artefact of
  the null. Quoting them would have "confirmed" a t = 0.69 result.
- The one-day skip is worth nothing in this cohort: no-skip earns +7.31 bps
  against skip-1's +6.95. Bid-ask bounce is not measurable in 120 mega-caps at
  daily closes, which is itself a reason the classic effect is absent.

SCOPE OF THE REJECTION (what it is NOT evidence about)
------------------------------------------------------
1. LARGE CAPS ONLY, and the liquidity-provision premium is documented down-cap
   and in microstructure time. The bottom liquidity tercile HERE is still a
   top-500 US name with a ~$500M daily tape.
2. NO POST-2016 NAMES. The point-in-time universe buys survivorship-freedom by
   excluding every index addition after 2016-01-04.
3. ONE PUBLISHER. Absence of a Benzinga headline is not absence of news.
4. NOT TESTED, AND DELIBERATELY NOT ADDED AFTER SEEING THIS NULL: Nagel's
   central conditioning is on the PRICE of liquidity - reversal pays most when
   VIX is high and market makers are constrained. Running it now would be
   hunting a variant after a null result, so it is left as a registry row for
   a future lab rather than a table in this one.

Run: python -m scout.reversal_lab             (full study, ~1 min warm)
     python -m scout.reversal_lab --selftest  (offline, no keys, <5s)
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
FORM = 5                    # formation-window length, sessions
SKIP = 1                    # sessions skipped between formation and formation
HORIZONS = (1, 5, 10, 21)
H_PRIMARY = 5               # the registered hold: one week
N_Q = 5                     # cross-sectional quintiles (common breakpoints)
N_T = 3                     # within-group terciles (variant) + abnormal terciles
MIN_POOL = 50               # sessions with a thinner cross-section are skipped
MIN_CELL = 2                # names needed in a cell for that date to score
MIN_GROUP = 12              # names needed for a within-group ranking
LOOKBACK = 60               # trailing sessions for the news/liquidity baselines
COST_BPS = 10.0             # round trip, per leg, large caps
BOOT_REPS = 5000
CTRL_REPS = 200             # permutation draws, every control
SEED = 20260809
STALE_RUN = 10              # identical consecutive closes that retire a ticker
EXTREME_1D = 0.45           # |1-day return| flagged as a possible bad print

BARS_CACHE = config.SCOUT_DIR / "cache_reversal_bars.pkl"


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def retire_stale(close: pd.DataFrame, run: int = STALE_RUN):
    """Drop each symbol permanently from its first run of `run` identical
    consecutive closes.

    A frozen quote is not a price. Alpaca keeps printing a delisted ticker at
    its last trade, and when the ticker is later REUSED the splice manufactures
    a >90% one-day return. Both present as an unbroken run of identical closes,
    which no genuinely traded large cap produces. Returns (masked close, log)."""
    out = close.copy()
    log = []
    for c in close.columns:
        v = close[c].to_numpy()
        eq = np.zeros(len(v), bool)
        eq[1:] = (v[1:] == v[:-1]) & np.isfinite(v[1:]) & np.isfinite(v[:-1])
        i, n, start = 0, len(eq), None
        while i < n:
            if not eq[i]:
                i += 1
                continue
            j = i
            while j < n and eq[j]:
                j += 1
            if j - i >= run:
                start = i - 1           # the first bar of the frozen block
                break
            i = j
        if start is not None:
            out.iloc[start:, out.columns.get_loc(c)] = np.nan
            log.append(dict(symbol=c, frozen_from=close.index[start].date(),
                            sessions_dropped=int(np.isfinite(v[start:]).sum())))
    return out, log


def endgame_mask(close: pd.DataFrame, sessions: int = 126) -> np.ndarray:
    """The last `sessions` prints of any symbol that stops trading before the
    panel ends - i.e. a name being acquired.

    This is not cosmetic. A stock under an agreed all-cash bid is pinned near
    the deal price, moves almost not at all, and STOPS BEING WRITTEN ABOUT: it
    is news-free dead money by construction, so it accumulates in the quiet
    group precisely where this study reads its answer. The panel contains
    TWX/AET/ESRX/CELG/AGN/MYL/ALXN/ATVI/PXD/MRO/WBA on that path."""
    ok = np.isfinite(close.to_numpy())
    out = np.zeros_like(ok)
    end = ok.shape[0] - 1
    for j in range(ok.shape[1]):
        idx = np.flatnonzero(ok[:, j])
        if len(idx) and idx[-1] < end - 21:
            out[idx[-sessions:], j] = True
    return out


def extreme_prints(close: pd.DataFrame, tol: float = EXTREME_1D) -> pd.DataFrame:
    """Every remaining |1-day return| > tol, enumerated so each can be judged
    individually rather than filtered blind (BACKTEST-REPORT's split debt)."""
    r1 = (close / close.shift(1) - 1.0).to_numpy()
    rows = []
    for i, j in np.argwhere(np.abs(r1) > tol):
        rows.append(dict(symbol=close.columns[j], date=close.index[i].date(),
                         ret=float(r1[i, j])))
    return pd.DataFrame(rows)


def load_bars(refresh: bool = False) -> dict:
    """Split-repaired closes for the 120-name news panel, their dollar volume,
    and SPY as a benchmark only.

    The repaired closes are REUSED from scout/news_attention_lab.load_close
    rather than reimplemented - it is the verified artefact, and duplicating a
    split-repair is how two files quietly disagree about a price."""
    if BARS_CACHE.exists() and not refresh:
        return pd.read_pickle(BARS_CACHE)
    from . import data, news_attention_lab as attn
    close = attn.load_close(refresh=refresh)
    syms = list(close.columns)
    # small batches with backoff: the shared Alpaca key is rate-limited when
    # several labs in this repo warm their caches at once.
    parts = []
    todo = syms + ["SPY"]
    for i in range(0, len(todo), 25):
        batch = todo[i:i + 25]
        for attempt in range(8):
            try:
                parts.append(data.daily_ohlcv(batch, days=3900))
                break
            except Exception as e:
                if attempt == 7:
                    raise
                print(f"  batch {i // 25 + 1} retry {attempt + 1}: {e}")
                time.sleep(5 * (attempt + 1))
    vol = pd.concat([p["volume"] for p in parts], axis=1).astype("float64")
    vol.index = pd.DatetimeIndex(vol.index).tz_localize(None).normalize()
    spy = pd.concat([p["close"] for p in parts], axis=1)["SPY"].astype("float64")
    spy.index = pd.DatetimeIndex(spy.index).tz_localize(None).normalize()
    out = dict(close=close,
               volume=vol.reindex(index=close.index, columns=syms),
               spy=spy.reindex(close.index))
    pd.to_pickle(out, BARS_CACHE)
    return out


def news_count_frame(close: pd.DataFrame) -> pd.DataFrame:
    """Specific-story counts, sessions x symbols, row t = news readable before
    close(t). Built from news_attention_lab's cached story table, which already
    holds the expensive attribution and templated-content pass."""
    from . import news_attention_lab as attn
    stories = attn.load_stories(close)
    sessions = news_data._session_index(close)
    d = stories[stories["session"].notna() & stories["specific"]].copy()
    d["one"] = 1.0
    return (d.pivot_table(index="session", columns="symbol", values="one",
                          aggfunc="sum")
            .reindex(index=sessions, columns=list(close.columns)).fillna(0.0))


# --------------------------------------------------------------------------
# signal, conditioner, eligibility - every shift is here and nowhere else
# --------------------------------------------------------------------------

def formation_return(close: pd.DataFrame, form: int = FORM,
                     skip: int = SKIP) -> pd.DataFrame:
    """The signal: the `form`-session return ending `skip` sessions before t.

    skip=1 leaves session t out of the formation window entirely, so the last
    price in the signal is close(t-1) and the first price in the return is
    close(t). Bid-ask bounce lives in exactly that one session."""
    return close.shift(skip) / close.shift(skip + form) - 1.0


def forward(close: pd.DataFrame, h: int) -> np.ndarray:
    """close(t) -> close(t+h) simple return. THE forward shift, and the only one."""
    return (close.shift(-h) / close - 1.0).to_numpy()


def formation_news(counts: pd.DataFrame, form: int = FORM,
                   skip: int = SKIP) -> pd.DataFrame:
    """Specific stories over the same sessions the formation return spans."""
    return counts.shift(skip).rolling(form).sum()


def abnormal_news(k: pd.DataFrame, form: int = FORM,
                  lookback: int = LOOKBACK) -> pd.DataFrame:
    """log((k+1)/(baseline+1)) where the baseline is this symbol's own median
    formation-week count over the `lookback` sessions ENDING BEFORE the
    formation window - k.shift(form) makes the two windows disjoint."""
    base = k.shift(form).rolling(lookback, min_periods=lookback // 2).median()
    return np.log((k + 1.0) / (base + 1.0))


def dollar_volume_rank(close: pd.DataFrame, volume: pd.DataFrame,
                       lookback: int = LOOKBACK) -> pd.DataFrame:
    """Trailing mean dollar volume, known at close(t-1)."""
    return (close * volume).rolling(lookback, min_periods=lookback // 2).mean().shift(1)


def eligibility(close: pd.DataFrame, h: int, form: int = FORM,
                skip: int = SKIP, lookback: int = LOOKBACK) -> np.ndarray:
    """Bool (dates x symbols): a real close at t-(skip+form), at t-skip, at t
    and at t+h. Names delisting inside the hold drop out; that count is
    reported rather than patched."""
    ok = np.isfinite(close.to_numpy())
    n_d, n_s = ok.shape

    def back(n):
        return np.vstack([np.zeros((n, n_s), bool), ok[:n_d - n]])

    fut = np.vstack([ok[h:], np.zeros((h, n_s), bool)])
    m = ok & back(skip) & back(skip + form) & fut
    m[:lookback] = False
    return m


# --------------------------------------------------------------------------
# cross-sectional machinery
# --------------------------------------------------------------------------

def quantile_labels(sig: np.ndarray, elig: np.ndarray, rng: np.random.Generator,
                    q: int = N_Q, min_pool: int = MIN_POOL) -> np.ndarray:
    """Balanced within-session quantile labels, -1 where ineligible.

    Label 0 = the LOWEST signal = the biggest losers = the long leg. Ties are
    broken by a seeded uniform key rather than by column order; a 5-session
    return has few exact ties, but the same routine is used for the news
    conditioner, which has a large tie mass at zero."""
    n_d, n_s = sig.shape
    lab = np.full((n_d, n_s), -1, dtype=np.int8)
    key = rng.random((n_d, n_s))
    fin = np.isfinite(sig)
    for i in range(n_d):
        m = elig[i] & fin[i]
        k = int(m.sum())
        if k < min_pool:
            continue
        idx = np.flatnonzero(m)
        order = idx[np.lexsort((key[i, idx], sig[i, idx]))]
        lab[i, order] = np.minimum((np.arange(k) * q) // k, q - 1)
    return lab


def group_labels(sig: np.ndarray, elig: np.ndarray, grp: np.ndarray, g: int,
                 rng: np.random.Generator, q: int = N_T,
                 min_group: int = MIN_GROUP) -> np.ndarray:
    """Quantile labels computed INSIDE one conditioning group (the variant).

    Each group gets its own breakpoints, so both legs have equal-count tails -
    at the price of comparing a mild loser in the quiet group with a violent
    one in the news group. The common-breakpoint version is the primary for
    exactly that reason; both are reported."""
    return quantile_labels(np.where(grp == g, sig, np.nan), elig & (grp == g),
                           rng, q=q, min_pool=min_group)


def cell_means(lab: np.ndarray, y: np.ndarray, q: int,
               sub: np.ndarray | None = None):
    """(dates x q) equal-weight mean of `y` per label bucket, restricted to
    `sub` if given, plus the restricted eligible-pool mean and bucket counts."""
    fin = np.isfinite(y)
    yz = np.nan_to_num(y)
    keep = fin if sub is None else (fin & sub)
    out = np.full((lab.shape[0], q), np.nan)
    cnt = np.zeros((lab.shape[0], q), dtype=np.int32)
    for qi in range(q):
        m = (lab == qi) & keep
        n = m.sum(1)
        cnt[:, qi] = n
        out[:, qi] = np.where(n > 0,
                              np.where(m, yz, 0.0).sum(1) / np.maximum(n, 1), np.nan)
    pm = (lab >= 0) & keep
    npool = pm.sum(1)
    pool = np.where(npool > 0,
                    np.where(pm, yz, 0.0).sum(1) / np.maximum(npool, 1), np.nan)
    return out, pool, cnt


def _nanmean(a) -> float:
    """np.nanmean without the all-NaN warning: an empty cell is a real state
    here (a liquidity subset can be too thin to rank on some dates)."""
    a = np.asarray(a, dtype=float)
    m = np.isfinite(a)
    return float(a[m].mean()) if m.any() else float("nan")


def rev_spread(cells: np.ndarray, cnt: np.ndarray, q: int,
               min_cell: int = MIN_CELL) -> np.ndarray:
    """LOSERS minus WINNERS, per date. Positive = reversal (registered sign)."""
    ok = (cnt[:, 0] >= min_cell) & (cnt[:, q - 1] >= min_cell)
    return np.where(ok, cells[:, 0] - cells[:, q - 1], np.nan)


def turnover(lab: np.ndarray, qi: int, h: int, sub: np.ndarray | None = None) -> float:
    """Mean fraction of a leg replaced between rebalances spaced h apart. A name
    held across a rebalance is not traded, so this is what the cost charge
    multiplies."""
    memb = (lab == qi) if sub is None else ((lab == qi) & sub)
    fr = []
    for i in range(0, lab.shape[0] - h, h):
        a, b = set(np.flatnonzero(memb[i])), set(np.flatnonzero(memb[i + h]))
        if a and b:
            fr.append(len(b - a) / len(b))
    return float(np.mean(fr)) if fr else float("nan")


# --------------------------------------------------------------------------
# inference: cluster by date, block-bootstrap the overlap, pool the phases
# --------------------------------------------------------------------------

def block_boot(x: np.ndarray, block: int, reps: int, rng: np.random.Generator):
    """Circular moving-block bootstrap of the mean of a per-DATE series.

    The cross-section is collapsed to one number per session before this runs,
    so date clustering is structural (scout/calibrate.py resamples dates for
    the same reason). Blocks of length h keep the overlap that h-day holds
    create inside a block; an i.i.d. bootstrap would understate the SE."""
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3 * max(block, 1):
        return dict(mean=float(np.mean(x)) if n else float("nan"),
                    se=float("nan"), lo=float("nan"), hi=float("nan"),
                    t=float("nan"), n=n)
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
    """The h non-overlapping entry schedules hiding inside one overlapping mean
    (RESEARCH-AGENDA Rule 9; H7a is this repo quoting the luckiest of six)."""
    return np.array([np.nanmean(x[p::h]) if np.isfinite(x[p::h]).any() else np.nan
                     for p in range(max(h, 1))])


def split_date(x: np.ndarray, index: pd.DatetimeIndex):
    """The date the both-halves split falls on FOR THIS SERIES. A thin group is
    defined on fewer dates than a thick one, so its halves are not the calendar
    halves and quoting them without the date is misleading."""
    idx = np.flatnonzero(np.isfinite(x))
    return index[idx[len(idx) // 2]].date() if len(idx) else None


def halves(x: np.ndarray):
    idx = np.flatnonzero(np.isfinite(x))
    k = len(idx) // 2
    return (float(np.mean(x[idx[:k]])), float(np.mean(x[idx[k:]]))) if k else (
        float("nan"), float("nan"))


def summarize(x: np.ndarray, block: int, rng: np.random.Generator, **extra) -> dict:
    h = max(block, 1)
    b = block_boot(x, h, BOOT_REPS, rng)
    h1, h2 = halves(x)
    ph = phase_sweep(x, h)
    row = dict(h=block, n_dates=b["n"], mean=b["mean"] * 1e4, lo=b["lo"] * 1e4,
               hi=b["hi"] * 1e4, se=b["se"] * 1e4, t=b["t"],
               half1=h1 * 1e4, half2=h2 * 1e4,
               ph_min=(float(ph[np.isfinite(ph)].min()) * 1e4
                       if np.isfinite(ph).any() else float("nan")),
               ph_max=(float(ph[np.isfinite(ph)].max()) * 1e4
                       if np.isfinite(ph).any() else float("nan")),
               ph_wrong=int((ph < 0).sum()), ph_n=len(ph))
    row.update(extra)
    return row


def beta_alpha(x: np.ndarray, mkt: np.ndarray, h: int,
               rng: np.random.Generator) -> dict:
    """Rule 13: regress every dollar-neutral book on the benchmark before
    quoting its sign. A dollar-neutral spread is not risk-neutral - H16 found
    half of its raw spread was a -0.15 beta."""
    m = np.isfinite(x) & np.isfinite(mkt)
    if m.sum() < 50 or np.var(mkt[m], ddof=1) <= 0:
        return dict(beta=float("nan"), alpha=float("nan"), t_alpha=float("nan"),
                    alpha_pct_yr=float("nan"))
    xs, ms = x[m], mkt[m]
    beta = float(np.cov(xs, ms, ddof=1)[0, 1] / np.var(ms, ddof=1))
    resid = np.full_like(x, np.nan)
    resid[m] = xs - beta * ms
    b = block_boot(resid, max(h, 1), BOOT_REPS, rng)
    return dict(beta=beta, alpha=b["mean"] * 1e4, t_alpha=b["t"],
                alpha_pct_yr=b["mean"] * (252 / max(h, 1)) * 100)


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------

def unconditional(sig: pd.DataFrame, close: pd.DataFrame, spy: pd.Series,
                  rng: np.random.Generator, horizons=HORIZONS,
                  sub_daily: np.ndarray | None = None,
                  label: str = "all",
                  min_pool: int = MIN_POOL) -> tuple[pd.DataFrame, dict]:
    """H21a: reversal with no conditioning at all, at every horizon."""
    sa = sig.to_numpy()
    rows, keep = [], {}
    for h in horizons:
        elig = eligibility(close, h)
        if sub_daily is not None:
            elig = elig & sub_daily
        lab = quantile_labels(sa, elig, np.random.default_rng(SEED + h),
                              min_pool=min_pool)
        fwd = forward(close, h)
        cells, pool, cnt = cell_means(lab, fwd, N_Q)
        sp = rev_spread(cells, cnt, N_Q)
        spym = (spy.shift(-h) / spy - 1.0).to_numpy()
        ba = beta_alpha(sp, spym, h, rng)
        row = summarize(sp, h, rng, variant=label, h=h,
                        n_names=_nanmean(cnt.sum(1)[np.isfinite(sp)].astype(float)),
                        losers=_nanmean(cells[:, 0]) * 1e4,
                        winners=_nanmean(cells[:, N_Q - 1]) * 1e4,
                        pool=_nanmean(pool) * 1e4,
                        long_only=_nanmean(cells[:, 0] - pool) * 1e4,
                        turn_l=turnover(lab, 0, h), turn_s=turnover(lab, N_Q - 1, h))
        row.update(ba)
        rows.append(row)
        keep[h] = dict(lab=lab, fwd=fwd, elig=elig, spread=sp, pool=pool,
                       cells=cells, cnt=cnt, spy=spym)
    return pd.DataFrame(rows), keep


def conditional(sig: pd.DataFrame, close: pd.DataFrame, grp: np.ndarray,
                names: list[str], rng: np.random.Generator, h: int = H_PRIMARY,
                sub_daily: np.ndarray | None = None, within: bool = False,
                spy: pd.Series | None = None, min_pool: int = MIN_POOL):
    """H21b/H21c: the same signal, split by the conditioner.

    within=False (PRIMARY): ONE cross-sectional ranking over the whole eligible
    pool, then each group's Q1 and Q5 members are averaged separately. A
    "loser" is the same size of loser in both groups, which is what the
    mechanism is about.
    within=True (VARIANT): each group ranked on its own breakpoints."""
    sa = sig.to_numpy()
    elig = eligibility(close, h)
    if sub_daily is not None:
        elig = elig & sub_daily
    fwd = forward(close, h)
    fret = sig.to_numpy()
    q = N_T if within else N_Q
    rows, spreads = [], {}
    lab_common = quantile_labels(sa, elig, np.random.default_rng(SEED + h),
                                 min_pool=min_pool)
    for g, nm in enumerate(names):
        if within:
            lab = group_labels(sa, elig, grp, g, np.random.default_rng(SEED + h + g))
            sub = None
        else:
            lab, sub = lab_common, (grp == g)
        cells, pool, cnt = cell_means(lab, fwd, q, sub)
        fcells, _, _ = cell_means(lab, fret, q, sub)
        sp = rev_spread(cells, cnt, q)
        spreads[nm] = sp
        row = summarize(sp, h, rng, group=nm, h=h,
                        n_lose=_nanmean(cnt[:, 0][np.isfinite(sp)].astype(float)),
                        n_win=_nanmean(cnt[:, q - 1][np.isfinite(sp)].astype(float)),
                        form_lose=_nanmean(fcells[:, 0]) * 100,
                        form_win=_nanmean(fcells[:, q - 1]) * 100,
                        losers=_nanmean(cells[:, 0]) * 1e4,
                        winners=_nanmean(cells[:, q - 1]) * 1e4,
                        pool=_nanmean(pool) * 1e4,
                        long_only=_nanmean(cells[:, 0] - pool) * 1e4,
                        turn_l=turnover(lab, 0, h, sub),
                        turn_s=turnover(lab, q - 1, h, sub))
        if spy is not None:
            row.update(beta_alpha(sp, (spy.shift(-h) / spy - 1.0).to_numpy(), h, rng))
        rows.append(row)
    return pd.DataFrame(rows), spreads, dict(lab=lab_common, fwd=fwd, elig=elig)


def difference(spreads: dict, a: str, b: str, h: int,
               rng: np.random.Generator) -> dict:
    """spread(a) - spread(b) on the dates where BOTH are defined. The CI on
    this series is the hypothesis; two separately-significant legs are not.

    The two legs are also re-averaged over exactly those COMMON dates. A thin
    group is defined on fewer dates than a thick one (the quiet group needs
    MIN_CELL names in both extreme buckets), so the standalone leg means are
    computed on different samples and must not be subtracted by eye."""
    d = spreads[a] - spreads[b]
    both = np.isfinite(spreads[a]) & np.isfinite(spreads[b])
    return summarize(d, h, rng, contrast=f"{a} - {b}", h=h,
                     mean_a=float(np.mean(spreads[a][both])) * 1e4 if both.any()
                     else float("nan"),
                     mean_b=float(np.mean(spreads[b][both])) * 1e4 if both.any()
                     else float("nan"),
                     n_a=int(np.isfinite(spreads[a]).sum()),
                     n_b=int(np.isfinite(spreads[b]).sum()))


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def random_pick_control(lab: np.ndarray, fwd: np.ndarray, q: int,
                        rng: np.random.Generator, sub: np.ndarray | None = None,
                        reps: int = CTRL_REPS) -> np.ndarray:
    """CONTROL (b): labels permuted inside each session over the identical
    eligible pool. Expectation is exactly zero; the draws buy the noise SCALE."""
    out = np.empty(reps)
    for r in range(reps):
        p = lab.copy()
        for i in range(p.shape[0]):
            v = p[i]
            m = v >= 0
            if m.any():
                v[m] = rng.permutation(v[m])
        cells, _, cnt = cell_means(p, fwd, q, sub)
        out[r] = _nanmean(rev_spread(cells, cnt, q))
    return out


def date_shuffle_control(sig: np.ndarray, elig: np.ndarray, fwd: np.ndarray,
                         q: int, rng: np.random.Generator,
                         sub: np.ndarray | None = None,
                         reps: int = CTRL_REPS) -> np.ndarray:
    """CONTROL (c): each symbol's formation return permuted ACROSS DATES.

    Every stock keeps its own distribution of 5-session moves; only the link
    between a move and the day it happened dies. Reversal is a timing claim, so
    this control MUST kill it - if the shuffled null reproduces the spread, the
    "reversal" was a stock characteristic, which is precisely how H15 died."""
    out = np.empty(reps)
    for r in range(reps):
        s = sig.copy()
        for j in range(s.shape[1]):
            col = s[:, j]
            f = np.isfinite(col)
            if f.sum() > 1:
                col[f] = rng.permutation(col[f])
        lab = quantile_labels(s, elig, rng, q=q)
        cells, _, cnt = cell_means(lab, fwd, q, sub)
        out[r] = _nanmean(rev_spread(cells, cnt, q))
    return out


def news_shuffle_control(lab: np.ndarray, fwd: np.ndarray, grp: np.ndarray,
                         q: int, rng: np.random.Generator,
                         reps: int = CTRL_REPS) -> np.ndarray:
    """CONTROL (d), the one that decides H21b: the news/no-news assignment
    permuted across symbols WITHIN each date, preserving the per-date group
    sizes exactly. Every date keeps the same number of quiet names and the same
    price ranking; only WHICH names were quiet dies. If the real difference sits
    inside this null, the conditioning is decoration."""
    out = np.empty(reps)
    for r in range(reps):
        g = grp.copy()
        for i in range(g.shape[0]):
            v = g[i]
            m = v >= 0
            if m.any():
                v[m] = rng.permutation(v[m])
        d = []
        for gi in (0, 1):
            cells, _, cnt = cell_means(lab, fwd, q, g == gi)
            d.append(rev_spread(cells, cnt, q))
        out[r] = _nanmean(d[0] - d[1])
    return out


def news_shuffle_longonly(lab: np.ndarray, fwd: np.ndarray, grp: np.ndarray,
                          g: int, q: int, rng: np.random.Generator,
                          reps: int = CTRL_REPS) -> np.ndarray:
    """CONTROL (d) applied to the LONG-ONLY leg: the same within-date
    permutation of the group labels, scoring losers-minus-pool instead of the
    long/short spread. Same control, different book - not a new test."""
    out = np.empty(reps)
    for r in range(reps):
        gg = grp.copy()
        for i in range(gg.shape[0]):
            v = gg[i]
            m = v >= 0
            if m.any():
                v[m] = rng.permutation(v[m])
        cells, pool, cnt = cell_means(lab, fwd, q, gg == g)
        out[r] = _nanmean(np.where(cnt[:, 0] >= MIN_CELL, cells[:, 0] - pool, np.nan))
    return out


def costs(gross_bps: float, turn_l: float, turn_s: float,
          h: int, cost_bps: float = COST_BPS) -> dict:
    """Charge the round trip and report the break-even.

    Accounting: 1x LONG the losers + 1x SHORT the winners, rebalanced every h
    sessions. At each rebalance a fraction f of a leg is replaced and pays
    f x cost_bps (sell the old, buy the new). Total per window is
    (f_long + f_short) x cost_bps; break-even c* = gross / (f_long + f_short)."""
    f = turn_l + turn_s
    chg = f * cost_bps
    return dict(gross_bps=gross_bps, turn=f, cost_bps=chg, net_bps=gross_bps - chg,
                breakeven_bps=gross_bps / f if f else float("nan"),
                gross_pct_yr=gross_bps * (252 / max(h, 1)) / 100,
                net_pct_yr=(gross_bps - chg) * (252 / max(h, 1)) / 100)


# --------------------------------------------------------------------------
# offline selftest: does this file's machinery do what it claims?
# --------------------------------------------------------------------------

def selftest() -> int:
    rng = np.random.default_rng(0)
    fails = 0

    def check(name, ok, detail=""):
        nonlocal fails
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
        fails += (not ok)

    # 1. the shift. Signal at t must use ONLY closes at t-1 and t-6.
    n_d, n_s = 400, 40
    idx = pd.bdate_range("2018-01-01", periods=n_d)
    px = pd.DataFrame(100.0, index=idx, columns=[f"S{i}" for i in range(n_s)])
    px.iloc[200:, 0] *= 2.0                      # a single step at row 200
    sig = formation_return(px)
    col = sig.iloc[:, 0].to_numpy()
    moved = np.flatnonzero(np.abs(np.nan_to_num(col)) > 1e-9)
    # a step at row 200 makes close(t-1)/close(t-6) differ exactly when t-1>=200
    # and t-6<200, i.e. rows 201..205 - five rows, the formation length.
    check("signal(t) reads close(t-1)..close(t-6) only",
          moved.min() == 201 and moved.max() == 205 and len(moved) == FORM,
          f"nonzero rows {moved.min()}..{moved.max()} for a step at row 200")
    check("signal at the step row itself is exactly 0 (session t is skipped)",
          abs(col[200]) < 1e-12)

    # 2. forward return pairs with the SAME index and starts at close(t).
    f1 = forward(px, 1)
    check("forward(t) reads close(t)->close(t+h)",
          abs(f1[199, 0] - 1.0) < 1e-12 and abs(f1[200, 0]) < 1e-12,
          "the +100% lands on row 199, the row whose close(t+1) jumped")

    # 3. planted reversal is recovered with the registered sign.
    rng2 = np.random.default_rng(7)
    n_d, n_s = 900, 60
    idx = pd.bdate_range("2016-01-01", periods=n_d)
    noise = rng2.normal(0, 0.012, (n_d, n_s))
    r = noise.copy()
    for t in range(FORM + SKIP + 1, n_d):
        prior = noise[t - FORM - SKIP:t - SKIP, :].sum(0)
        r[t] += -0.20 * prior                    # 20% of the move gives back
    px = pd.DataFrame(100 * np.exp(np.cumsum(r, 0)), index=idx,
                      columns=[f"S{i}" for i in range(n_s)])
    sig = formation_return(px)
    res, keep = unconditional(sig, px, pd.Series(100.0, index=idx), rng, (1,))
    check("planted reversal recovered, positive spread",
          res.iloc[0]["mean"] > 20, f"spread {res.iloc[0]['mean']:+.1f} bps")

    # 4. the date-shuffle control kills a planted TIMING effect.
    shuf = date_shuffle_control(sig.to_numpy(), keep[1]["elig"], keep[1]["fwd"],
                                N_Q, rng, reps=25)
    check("date-shuffle control destroys planted reversal",
          abs(shuf.mean()) < 0.15 * res.iloc[0]["mean"] / 1e4,
          f"shuffled {shuf.mean() * 1e4:+.1f} bps vs actual "
          f"{res.iloc[0]['mean']:+.1f}")

    # 5. random-pick control is centred on zero.
    rnd = random_pick_control(keep[1]["lab"], keep[1]["fwd"], N_Q, rng, reps=25)
    check("random-pick control is centred on zero",
          abs(rnd.mean() * 1e4) < 3.0, f"{rnd.mean() * 1e4:+.2f} bps")

    # 6. a planted NO-NEWS-ONLY reversal produces a positive difference, and
    #    the news-label shuffle kills that difference.
    # alignment: at h=1 the group at row t governs the return r[t+1], because
    # fwd(t) = close(t+1)/close(t) - 1. Planting it on quiet[t] instead of
    # quiet[t-1] is a one-session misalignment, and check 6c shows it is fatal.
    quiet = rng2.random((n_d, n_s)) < 0.4
    r = noise.copy()
    for t in range(FORM + SKIP + 1, n_d):
        prior = noise[t - FORM - SKIP:t - SKIP, :].sum(0)
        r[t] += np.where(quiet[t - 1], -0.30 * prior, 0.0)
    px2 = pd.DataFrame(100 * np.exp(np.cumsum(r, 0)), index=idx,
                       columns=[f"S{i}" for i in range(n_s)])
    sig2 = formation_return(px2)
    grp = np.where(quiet, 0, 1).astype(np.int8)
    res2, spreads2, aux = conditional(sig2, px2, grp, ["quiet", "news"], rng, h=1)
    d = difference(spreads2, "quiet", "news", 1, rng)
    check("planted quiet-only reversal shows up in the quiet leg",
          res2.iloc[0]["mean"] > res2.iloc[1]["mean"] + 20,
          f"quiet {res2.iloc[0]['mean']:+.1f} vs news {res2.iloc[1]['mean']:+.1f} bps")
    ns = news_shuffle_control(aux["lab"], aux["fwd"], grp, N_Q, rng, reps=25)
    check("news-label shuffle destroys the difference",
          abs(ns.mean() * 1e4) < 0.3 * d["mean"],
          f"shuffled {ns.mean() * 1e4:+.1f} vs actual {d['mean']:+.1f} bps")
    grp_bad = np.vstack([grp[1:], grp[-1:]])         # conditioner off by one
    _, sbad, _ = conditional(sig2, px2, grp_bad, ["quiet", "news"], rng, h=1)
    dbad = difference(sbad, "quiet", "news", 1, rng)
    check("a one-session misaligned conditioner kills the difference",
          abs(dbad["mean"]) < 0.3 * d["mean"],
          f"misaligned {dbad['mean']:+.1f} vs aligned {d['mean']:+.1f} bps")

    # 7. stale-quote retirement.
    px3 = px.copy()
    px3.iloc[500:, 3] = px3.iloc[500, 3]
    masked, log = retire_stale(px3)
    check("stale-quote rule retires a frozen ticker",
          len(log) == 1 and log[0]["symbol"] == "S3"
          and not np.isfinite(masked.iloc[600, 3]),
          f"log={log}")
    check("stale-quote rule leaves live tickers alone",
          np.isfinite(masked.iloc[600, 4]))

    # 8. block bootstrap widens against i.i.d. on autocorrelated data.
    ar = np.zeros(3000)
    for i in range(1, 3000):
        ar[i] = 0.8 * ar[i - 1] + rng.normal(0, 1)
    wide = block_boot(ar, 20, 2000, rng)["se"]
    thin = block_boot(ar, 1, 2000, rng)["se"]
    check("block bootstrap SE > i.i.d. SE on AR(1)", wide > 1.5 * thin,
          f"block {wide:.3f} vs iid {thin:.3f}")

    # 9. phase sweep partitions the sample.
    x = np.arange(100, dtype=float)
    ph = phase_sweep(x, 5)
    check("phase sweep returns h disjoint schedules",
          len(ph) == 5 and abs(np.mean(ph) - np.nanmean(x)) < 1e-9)

    # 10. cost arithmetic and break-even.
    c = costs(20.0, 0.9, 0.9, 5)
    check("break-even = gross / summed turnover",
          abs(c["breakeven_bps"] - 20.0 / 1.8) < 1e-9
          and abs(c["net_bps"] - (20.0 - 18.0)) < 1e-9)

    print(f"\n{'ALL CHECKS PASSED' if not fails else f'{fails} CHECK(S) FAILED'}")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def _hdr(s: str) -> None:
    print(f"\n{'=' * 78}\n{s}\n{'=' * 78}")


def _fmt(v) -> str:
    return f"{v:9.2f}"


SUMMARY_COLS = ["n_dates", "mean", "lo", "hi", "t", "half1", "half2",
                "ph_min", "ph_max", "ph_wrong"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="refetch prices")
    args = ap.parse_args()
    if args.selftest:
        _hdr("SELFTEST (offline, no keys, no network)")
        raise SystemExit(selftest())

    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out: dict = {}

    _hdr("H21 - short-horizon reversal as a LIQUIDITY premium, split by news")
    print("MECHANISM: a week's move caused by uninformed liquidity DEMAND must")
    print("be paid for, so it reverses; a move caused by INFORMATION does not,")
    print("because it is the new price.")
    print("REGISTERED SIGN: losers minus winners is POSITIVE, and LARGER among")
    print("stocks that had NO news during the formation week.")
    print("\nloading data ...")
    bars = load_bars(refresh=args.refresh)
    close_raw, volume, spy = bars["close"], bars["volume"], bars["spy"]

    # ------------------------------------------------------------ hygiene
    _hdr("DATA HYGIENE (the repo's 5.1% unadjusted-split debt, and worse)")
    print("Closes are news_attention_lab's SPLIT-REPAIRED series (AAPL's missing")
    print("2020-08-31 4:1 among them), reused rather than reimplemented.\n")
    pre = extreme_prints(close_raw)
    print(f"|1-day return| > {EXTREME_1D:.0%} BEFORE stale-quote retirement: "
          f"{len(pre)}")
    for _, r in pre.iterrows():
        print(f"    {r['symbol']:<6} {r['date']}  {r['ret']:+.3f}")
    close, stale = retire_stale(close_raw)
    print(f"\nstale-quote retirement ({STALE_RUN}+ identical consecutive closes):")
    for r in stale:
        print(f"    {r['symbol']:<6} frozen from {r['frozen_from']}, "
              f"{r['sessions_dropped']:,} sessions dropped")
    post = extreme_prints(close)
    print(f"\n|1-day return| > {EXTREME_1D:.0%} AFTER retirement: {len(post)}")
    for _, r in post.iterrows():
        print(f"    {r['symbol']:<6} {r['date']}  {r['ret']:+.3f}   "
              "<- judged REAL (see module docstring)")
    zr = ((close_raw / close_raw.shift(1) - 1.0).abs() < 1e-12).sum().sum()
    zr2 = ((close / close.shift(1) - 1.0).abs() < 1e-12).sum().sum()
    print(f"\nexactly-zero one-day returns: {int(zr):,} before, {int(zr2):,} after.")
    print("Those are the frozen quotes, and they were all in the NO-NEWS group")
    print("with a guaranteed-zero forward return - on the exact leg this study")
    print("is trying to measure.")
    out["stale"] = stale
    out["extreme_after"] = post.to_dict("records")

    # -------------------------------------------------------------- panel
    sig = formation_return(close)
    counts = news_count_frame(close)
    k = formation_news(counts)
    abn = abnormal_news(k)
    adv = dollar_volume_rank(close, volume)

    # The group mask is anchored to h=5 eligibility for EVERY horizon, so the
    # two legs are always defined on the same population; at h=1 that discards
    # a few names that would have been eligible, which costs coverage and
    # cannot bias the contrast, since both groups lose them together.
    elig5 = eligibility(close, H_PRIMARY)
    kk = k.to_numpy()
    grp_news = np.where(~elig5, -1, np.where(np.nan_to_num(kk, nan=-1) == 0, 0, 1)
                        ).astype(np.int8)
    grp_news[np.isnan(kk)] = -1

    _hdr("SAMPLE")
    live = np.isfinite(close.to_numpy())
    print(f"sessions                                 : {close.shape[0]:>10,}  "
          f"{close.index[0].date()} .. {close.index[-1].date()}")
    print(f"symbols                                  : {close.shape[1]:>10,}")
    print(f"symbol-sessions with a usable price      : {int(live.sum()):>10,}")
    print(f"eligible at h={H_PRIMARY} (t-6, t-1, t, t+{H_PRIMARY} all present)  : "
          f"{int(elig5.sum()):>10,}")
    nn = int((grp_news == 0).sum())
    nw = int((grp_news == 1).sum())
    print(f"  NO specific news in sessions t-5..t-1  : {nn:>10,}  "
          f"({nn / max(nn + nw, 1):.1%})")
    print(f"  had specific news                      : {nw:>10,}  "
          f"({nw / max(nn + nw, 1):.1%})")
    pd_no = (grp_news == 0).sum(1)
    pd_ne = (grp_news == 1).sum(1)
    livedate = elig5.any(1)
    print(f"per-date group sizes: quiet mean {pd_no[livedate].mean():.1f} "
          f"(min {pd_no[livedate].min()}, max {pd_no[livedate].max()}), "
          f"news mean {pd_ne[livedate].mean():.1f}")
    yr = pd.Series(pd_no, index=close.index).groupby(close.index.year).mean()
    print("quiet-group size by year: "
          + "  ".join(f"{y}:{v:.0f}" for y, v in yr.items()))
    print("Benzinga coverage roughly doubles over the decade, so the quiet")
    print("group THINS from ~27 names in 2018 to ~12 by 2024. Any statistic")
    print("that needs a populated quiet tail is therefore weighted to the")
    print("early sample - which is disclosed below as a date-coverage number,")
    print("not corrected.")
    print("\nEFFECTIVE INDEPENDENT SAMPLE: the cross-section is collapsed to ONE")
    print(f"spread per session before any statistic, so n is at most the "
          f"{close.shape[0]:,} sessions,")
    print(f"not the {int(elig5.sum()):,} symbol-sessions. At h={H_PRIMARY} the honestly "
          "independent count is")
    print(f"~{close.shape[0] // H_PRIMARY:,} non-overlapping windows per entry "
          f"phase, and there are {H_PRIMARY} phases.")

    # ------------------------------------------------------- control (a)
    _hdr("CONTROL (a) POSITIVE: is the CONDITIONING VARIABLE alive?")
    print("If the news flag marked nothing, a null difference would be evidence")
    print("about the flag, not about the hypothesis.\n")
    r1 = (close / close.shift(1) - 1.0).to_numpy()
    fwd1 = forward(close, 1)
    fwd5 = forward(close, H_PRIMARY)
    sa = sig.to_numpy()
    for gi, nm in ((0, "quiet (no news)"), (1, "had news       ")):
        gm = (grp_news == gi)
        print(f"  {nm}  formation |ret| {np.nanmean(np.abs(sa[gm])) * 100:5.2f}%   "
              f"next-session |ret| {np.nanmean(np.abs(fwd1[gm])) * 100:5.2f}%   "
              f"next-5 |ret| {np.nanmean(np.abs(fwd5[gm])) * 100:5.2f}%   "
              f"formation ret {np.nanmean(sa[gm]) * 100:+5.2f}%")
    print("\nNews marks bigger moves in both directions. That is the premise the")
    print("split needs: the two groups are not the same population.")

    # -------------------------------------------------- H21a unconditional
    _hdr("H21a UNCONDITIONAL REVERSAL (losers minus winners, bps per hold)")
    print("Q1 = lowest 5-session return ending at close(t-1) = the LONG leg.")
    print("Registered sign POSITIVE. CI = circular moving-block bootstrap")
    print("(block = h), clustered by date. ph_wrong = entry phases with the")
    print("WRONG sign, of ph_n.\n")
    uncond, ukeep = unconditional(sig, close, spy, rng)
    print(uncond[["variant", "h", "n_dates", "n_names", "losers", "winners",
                  "pool", "mean", "lo", "hi", "t", "half1", "half2",
                  "ph_min", "ph_max", "ph_wrong"]]
          .to_string(index=False, float_format=_fmt))
    print("\nlosers/winners/pool are RAW bucket returns in bps over the h-session")
    print("hold (they contain the market); mean is the spread and does not.")
    print("\nRule 13 - the dollar-neutral book regressed on SPY BEFORE its sign")
    print("is quoted (H16 found half of its raw spread was a -0.15 beta):")
    print(uncond[["h", "mean", "beta", "alpha", "t_alpha", "alpha_pct_yr"]]
          .to_string(index=False, float_format=_fmt))
    out["unconditional"] = uncond.to_dict("records")

    # ------------------------------------------------------- H21b the split
    _hdr(f"H21b THE DECIDING ROW: the same signal split by news, h={H_PRIMARY}")
    print("PRIMARY = COMMON breakpoints: one cross-sectional quintile ranking")
    print("over the whole eligible pool, then each group's Q1 and Q5 members")
    print("averaged separately - so a 'loser' is the same size of loser in both")
    print("groups, which is what the mechanism is about. form_lose/form_win are")
    print("the mean FORMATION returns of those cells, printed so the reader can")
    print("check that.\n")
    cond, spreads, aux = conditional(sig, close, grp_news, ["quiet", "news"],
                                     rng, h=H_PRIMARY, spy=spy)
    print(cond[["group", "n_dates", "n_lose", "n_win", "form_lose", "form_win",
                "losers", "winners", "mean", "lo", "hi", "t", "half1", "half2",
                "beta", "alpha", "t_alpha"]]
          .to_string(index=False, float_format=_fmt))
    diff = difference(spreads, "quiet", "news", H_PRIMARY, rng)
    print("\nTHE HYPOTHESIS IS THIS ROW - the DIFFERENCE, with its own")
    print("date-clustered block-bootstrap CI. Two separately-signed legs are not")
    print("a result; the contrast is:")
    print(pd.DataFrame([diff])[["contrast", "n_dates", "n_a", "n_b", "mean_a",
                                "mean_b", "mean", "lo", "hi", "t",
                                "half1", "half2", "ph_min", "ph_max"]]
          .to_string(index=False, float_format=_fmt))
    print(f"\nboth-halves split date: quiet leg "
          f"{split_date(spreads['quiet'], close.index)}, news leg "
          f"{split_date(spreads['news'], close.index)}, difference "
          f"{split_date(spreads['quiet'] - spreads['news'], close.index)}.")
    print("The two legs are defined on different date sets, so their halves are")
    print("NOT the calendar halves - the split date is printed for each series.")
    print(f"\nDATE COVERAGE, and it matters: the quiet leg needs {MIN_CELL} names in")
    print(f"BOTH extreme quintiles, which it has on only {diff['n_a']:,} of the "
          f"{diff['n_b']:,} dates")
    print("the news leg covers. mean_a/mean_b are the two legs re-averaged over")
    print("exactly the common dates, so they subtract to the difference; the")
    print("standalone table above averages each leg over its own sample.")
    cov = pd.Series(np.isfinite(spreads["quiet"]), index=close.index)
    print("share of sessions with a scorable quiet leg, by year: "
          + "  ".join(f"{y}:{v:.0%}" for y, v in
                      cov.groupby(close.index.year).mean().items()))
    print("\nMIN_CELL sensitivity (a coverage knob, reported in full, not searched):")
    sens = []
    for mc in (1, 2, 3, 4):
        sp2 = {}
        for gi, nm in ((0, "quiet"), (1, "news")):
            cells, _, cnt = cell_means(aux["lab"], aux["fwd"], N_Q, grp_news == gi)
            sp2[nm] = rev_spread(cells, cnt, N_Q, min_cell=mc)
        d2 = difference(sp2, "quiet", "news", H_PRIMARY, rng)
        sens.append(dict(min_cell=mc, n_dates=d2["n_dates"], quiet=d2["mean_a"],
                         news=d2["mean_b"], diff=d2["mean"], lo=d2["lo"],
                         hi=d2["hi"], t=d2["t"], half1=d2["half1"],
                         half2=d2["half2"]))
    print(pd.DataFrame(sens).to_string(index=False, float_format=_fmt))
    out["conditional"] = cond.to_dict("records")
    out["difference"] = diff

    # horizons around the primary
    _hdr("H21b at the other registered horizons (reported whatever they say)")
    rows = []
    for h in HORIZONS:
        c, s, _ = conditional(sig, close, grp_news, ["quiet", "news"], rng, h=h)
        d = difference(s, "quiet", "news", h, rng)
        rows.append(dict(h=h, n_dates=d["n_dates"], quiet=d["mean_a"],
                         news=d["mean_b"], diff=d["mean"], lo=d["lo"],
                         hi=d["hi"], t=d["t"], half1=d["half1"],
                         half2=d["half2"]))
    hgrid = pd.DataFrame(rows)
    print(hgrid.to_string(index=False, float_format=_fmt))
    out["horizon_grid"] = hgrid.to_dict("records")

    # ------------------------------------------ what IS the quiet group?
    _hdr("WHAT THE QUIET GROUP IS MADE OF (descriptive, and a confound)")
    endg = endgame_mask(close)
    q_all = (grp_news == 0)
    n_all = (grp_news == 1)
    print(f"quiet symbol-sessions inside a name's last 126 prints before it")
    print(f"stops trading (agreed-bid dead money): "
          f"{float(endg[q_all].mean()) * 100:.1f}%   "
          f"vs {float(endg[n_all].mean()) * 100:.1f}% of news sessions.")
    lose_q = (aux["lab"] == 0) & q_all
    share = pd.Series(lose_q.sum(0), index=close.columns).sort_values(ascending=False)
    tot = max(int(lose_q.sum()), 1)
    print(f"\nquiet-group LOSER-cell observations: {tot:,}. Concentration by name:")
    print("  top 10 = " + ", ".join(f"{s} {v / tot:.1%}" for s, v in share[:10].items()))
    print(f"  top 10 carry {share[:10].sum() / tot:.0%} of the cell; "
          f"{int((share > 0).sum())} of {close.shape[1]} names ever appear in it.")
    sp_ne = {}
    for gi, gname in ((0, "quiet"), (1, "news")):
        cells, _, cnt = cell_means(aux["lab"], aux["fwd"], N_Q,
                                   (grp_news == gi) & ~endg)
        sp_ne[gname] = rev_spread(cells, cnt, N_Q)
    d_ne = difference(sp_ne, "quiet", "news", H_PRIMARY, rng)
    print(f"\nexcluding those endgame sessions from BOTH groups: quiet "
          f"{d_ne['mean_a']:+.2f}, news {d_ne['mean_b']:+.2f}, difference "
          f"{d_ne['mean']:+.2f} bps [{d_ne['lo']:+.2f}, {d_ne['hi']:+.2f}], "
          f"t={d_ne['t']:+.2f}, n={d_ne['n_dates']:,}")
    out["endgame_difference"] = d_ne

    # ----------------------------------------------- H21b variant: within
    _hdr("H21b VARIANT: WITHIN-GROUP terciles (each group ranked on its own)")
    print("Equal-count tails inside each group, at the price of comparing a")
    print("mild loser in the quiet group with a violent one in the news group.")
    print(f"Terciles because the quiet group averages "
          f"{pd_no[livedate].mean():.0f} names.\n")
    condw, spreadsw, _ = conditional(sig, close, grp_news, ["quiet", "news"],
                                     rng, h=H_PRIMARY, within=True)
    print(condw[["group", "n_dates", "n_lose", "n_win", "form_lose", "form_win",
                 "mean", "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))
    dw = difference(spreadsw, "quiet", "news", H_PRIMARY, rng)
    print(pd.DataFrame([dw])[["contrast", "n_dates", "mean_a", "mean_b", "mean",
                              "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))
    out["within_group"] = condw.to_dict("records")
    out["within_difference"] = dw

    # --------------------------------------------------------------- H21c
    _hdr("H21c ABNORMAL NEWS VOLUME terciles (the sharper conditioner)")
    print("log((k+1)/(median k over the 60 sessions ending at t-6 +1)), k =")
    print("specific stories in t-5..t-1. Registered: the spread falls")
    print("monotonically from the LOW-attention to the HIGH-attention tercile.\n")
    lab_abn = quantile_labels(abn.to_numpy(), elig5, np.random.default_rng(SEED + 99),
                              q=N_T, min_pool=MIN_POOL)
    grp_abn = lab_abn.astype(np.int8)
    conda, spreadsa, _ = conditional(sig, close, grp_abn,
                                     ["abn_low", "abn_mid", "abn_high"],
                                     rng, h=H_PRIMARY)
    print(conda[["group", "n_dates", "n_lose", "n_win", "form_lose", "form_win",
                 "mean", "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))
    da = difference(spreadsa, "abn_low", "abn_high", H_PRIMARY, rng)
    print(pd.DataFrame([da])[["contrast", "n_dates", "mean_a", "mean_b", "mean",
                              "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))
    out["abnormal"] = conda.to_dict("records")
    out["abnormal_difference"] = da

    # --------------------------------------------------------------- H21d
    _hdr("H21d LONG-ONLY (buy the losers, no shorts - the tradeable form)")
    print("Measured against the MATCHED BENCHMARK, control (e): the equal-weight")
    print("mean of the identical eligible pool. Raw bucket returns contain the")
    print("market and are shown for scale only.\n")
    lo_rows, lo_ex = [], {}
    for gi, nm in ((None, "all"), (0, "quiet"), (1, "news")):
        sub = None if gi is None else (grp_news == gi)
        cells, pool, cnt = cell_means(aux["lab"], aux["fwd"], N_Q, sub)
        ex = np.where(cnt[:, 0] >= MIN_CELL, cells[:, 0] - pool, np.nan)
        lo_ex[nm] = ex
        r = summarize(ex, H_PRIMARY, rng, group=nm,
                      raw=_nanmean(cells[:, 0]) * 1e4,
                      pool=_nanmean(pool) * 1e4,
                      split=str(split_date(ex, close.index)),
                      turn=turnover(aux["lab"], 0, H_PRIMARY, sub))
        lo_rows.append(r)
    lo = pd.DataFrame(lo_rows)
    print(lo[["group", "n_dates", "raw", "pool", "mean", "lo", "hi", "t",
              "half1", "half2", "split", "turn"]]
          .to_string(index=False, float_format=_fmt))
    print("\nmean = losers minus the eligible-pool equal weight, in bps per")
    print(f"{H_PRIMARY}-session hold. Long-only pays HALF the round trips of the")
    print("long/short book (one leg, not two), which is priced in the cost block.")
    print("split = the date the both-halves split falls on FOR THAT SERIES.")
    lo_ctrl = news_shuffle_longonly(aux["lab"], aux["fwd"], grp_news, 0, N_Q, rng)
    act_lo = float(lo.set_index("group").loc["quiet", "mean"]) / 1e4
    se_lo = float(lo.set_index("group").loc["quiet", "se"]) / 1e4
    print(f"\ncontrol (d) on the quiet long-only leg: actual "
          f"{act_lo * 1e4:+.2f} bps, null {lo_ctrl.mean() * 1e4:+.2f} +/- "
          f"{lo_ctrl.std(ddof=1) * 1e4:.2f}, SE ratio "
          f"{lo_ctrl.std(ddof=1) / se_lo:.2f}, p2 "
          f"{2 * min((lo_ctrl >= act_lo).mean(), (lo_ctrl <= act_lo).mean()):.3f}")
    out["long_only"] = lo.to_dict("records")
    out["long_only_control"] = dict(
        actual=act_lo * 1e4, null_mean=float(lo_ctrl.mean() * 1e4),
        null_sd=float(lo_ctrl.std(ddof=1) * 1e4),
        se_ratio=float(lo_ctrl.std(ddof=1) / se_lo),
        p_two=float(2 * min((lo_ctrl >= act_lo).mean(), (lo_ctrl <= act_lo).mean())))

    # --------------------------------------------------- H21e liquidity
    _hdr("H21e LIQUIDITY SUBSETS (reversal classically lives where you cannot trade)")
    print("Trailing 60-session mean dollar volume, ranked within each date,")
    print("known at close(t-1). Registered as the expected-NEGATIVE row.\n")
    print(f"A subset of ~35-70 names cannot clear MIN_POOL={MIN_POOL}, so this")
    print("block uses a pool floor of 25 for ALL FOUR rows, including the")
    print("all-names row, which is therefore directly comparable (the full pool")
    print("averages 105 names, so the floor never binds there).\n")
    advr = adv.rank(axis=1, pct=True).to_numpy()
    liq_rows, liq_keep = [], {}
    for nm, mask in (("all names", None),
                     ("top-liquidity half", advr >= 0.5),
                     ("ex bottom tercile", advr >= 1 / 3),
                     ("bottom tercile only", advr < 1 / 3)):
        sub_daily = None if mask is None else np.nan_to_num(mask, nan=0.0).astype(bool)
        u, uk = unconditional(sig, close, spy, rng, (H_PRIMARY,),
                              sub_daily=sub_daily, label=nm, min_pool=25)
        c, s, ax = conditional(sig, close, grp_news, ["quiet", "news"], rng,
                               h=H_PRIMARY, sub_daily=sub_daily, min_pool=25)
        d = difference(s, "quiet", "news", H_PRIMARY, rng)
        s1 = {}
        for gi, gname in ((0, "quiet"), (1, "news")):
            cells, _, cnt = cell_means(ax["lab"], ax["fwd"], N_Q, grp_news == gi)
            s1[gname] = rev_spread(cells, cnt, N_Q, min_cell=1)
        d1 = difference(s1, "quiet", "news", H_PRIMARY, rng)
        liq_rows.append(dict(subset=nm, n_names=u.iloc[0]["n_names"],
                             uncond=u.iloc[0]["mean"], u_t=u.iloc[0]["t"],
                             n_dates=d["n_dates"], eff_win=d["n_dates"] // H_PRIMARY,
                             n_lose=c.iloc[0]["n_lose"],
                             quiet=d["mean_a"], news=d["mean_b"],
                             diff=d["mean"], d_lo=d["lo"], d_hi=d["hi"],
                             d_t=d["t"], half1=d["half1"], half2=d["half2"],
                             n1=d1["n_dates"], diff1=d1["mean"], t1=d1["t"]))
        liq_keep[nm] = (ax, d, s)
    liq = pd.DataFrame(liq_rows)
    print(liq.to_string(index=False, float_format=_fmt))
    print("\nn_lose  = names in the quiet group's LOSER cell on a scorable date.")
    print("n_dates = dates on which BOTH legs are scorable, i.e. the sample the")
    print(f"          difference is actually measured on; eff_win = n_dates/{H_PRIMARY},")
    print("          the honestly independent count of weekly windows.")
    print(f"n1/diff1/t1 = the same contrast at MIN_CELL=1 instead of {MIN_CELL},")
    print("          which is the coverage knob, NOT a variant: it says whether")
    print("          a subset's number depends on the dates the rule kept.")
    cov_top = pd.Series(np.isfinite(liq_keep["top-liquidity half"][2]["quiet"]),
                        index=close.index)
    print("\ntop-liquidity-half scorable dates by year: "
          + "  ".join(f"{y}:{int(v)}" for y, v in
                      cov_top.groupby(close.index.year).sum().items()))

    top_ax, top_d, _ = liq_keep["top-liquidity half"]
    print("\nThe top-liquidity half is the only cell in this study with |t| > 2,")
    print("so the pre-registered control (d) is run on it as well - applying an")
    print("existing control to a registered variant, not hunting a new one.")
    nsh_top = news_shuffle_control(top_ax["lab"], top_ax["fwd"], grp_news, N_Q, rng)
    se_top = top_d["se"] / 1e4
    act_top = top_d["mean"] / 1e4
    print(f"  actual {top_d['mean']:+.2f} bps   news-label-shuffle null "
          f"{nsh_top.mean() * 1e4:+.2f} +/- {nsh_top.std(ddof=1) * 1e4:.2f} bps"
          f"   SE ratio {nsh_top.std(ddof=1) / se_top:.2f}"
          f"   pctile {float((nsh_top < act_top).mean()) * 100:.0f}"
          f"   p2 {2 * min((nsh_top >= act_top).mean(), (nsh_top <= act_top).mean()):.3f}")
    out["liquidity"] = liq.to_dict("records")
    out["liquidity_top_control"] = dict(
        actual=top_d["mean"], null_mean=float(nsh_top.mean() * 1e4),
        null_sd=float(nsh_top.std(ddof=1) * 1e4),
        se_ratio=float(nsh_top.std(ddof=1) / se_top),
        p_two=float(2 * min((nsh_top >= act_top).mean(),
                            (nsh_top <= act_top).mean())))

    # ------------------------------------------------- registered variants
    _hdr("REGISTERED VARIANTS: the one-day gap, and the news window")
    print("NO-SKIP uses close(t)/close(t-5)-1, i.e. the formation window ends at")
    print("the SAME close the position is opened at. That is the classic fake")
    print("reversal: half of it is the bid-ask bounce of session t.\n")
    sig_ns = formation_return(close, FORM, 0)
    uns, _ = unconditional(sig_ns, close, spy, rng, (H_PRIMARY,), label="no-skip")
    cns, sns, _ = conditional(sig_ns, close, grp_news, ["quiet", "news"], rng,
                              h=H_PRIMARY)
    dns = difference(sns, "quiet", "news", H_PRIMARY, rng)
    print(f"  no-skip   unconditional {uns.iloc[0]['mean']:+8.2f} bps "
          f"(t={uns.iloc[0]['t']:+.2f})   quiet {cns.iloc[0]['mean']:+8.2f}   "
          f"news {cns.iloc[1]['mean']:+8.2f}   diff {dns['mean']:+8.2f}")
    print(f"  skip=1    unconditional "
          f"{uncond.set_index('h').loc[H_PRIMARY, 'mean']:+8.2f} bps "
          f"(t={uncond.set_index('h').loc[H_PRIMARY, 't']:+.2f})   "
          f"quiet {cond.iloc[0]['mean']:+8.2f}   news {cond.iloc[1]['mean']:+8.2f}"
          f"   diff {diff['mean']:+8.2f}")

    k6 = formation_news(counts, FORM + 1, 0)     # t-5..t inclusive
    g6 = np.where(~elig5, -1,
                  np.where(np.nan_to_num(k6.to_numpy(), nan=-1) == 0, 0, 1)
                  ).astype(np.int8)
    g6[np.isnan(k6.to_numpy())] = -1
    c6, s6, _ = conditional(sig, close, g6, ["quiet", "news"], rng, h=H_PRIMARY)
    d6 = difference(s6, "quiet", "news", H_PRIMARY, rng)
    print(f"\n  news counted t-5..t-1 (registered) : quiet {cond.iloc[0]['mean']:+8.2f}"
          f"   news {cond.iloc[1]['mean']:+8.2f}   diff {diff['mean']:+8.2f}")
    print(f"  news counted t-5..t   (variant)    : quiet {c6.iloc[0]['mean']:+8.2f}"
          f"   news {c6.iloc[1]['mean']:+8.2f}   diff {d6['mean']:+8.2f}")
    print("  (session t's news is readable before close(t), so both are legal;")
    print("   the second also conditions on the skipped session's own news.)")

    # extreme-print filtered rerun
    bad = (np.abs(r1) > EXTREME_1D)
    badwin = np.zeros_like(bad)
    for lag in range(-H_PRIMARY, FORM + SKIP + 1):
        badwin |= np.roll(bad, lag, axis=0)
    ok_daily = ~badwin
    uf, _ = unconditional(sig, close, spy, rng, (H_PRIMARY,),
                          sub_daily=ok_daily, label="ex-extreme")
    cf, sf, _ = conditional(sig, close, grp_news, ["quiet", "news"], rng,
                            h=H_PRIMARY, sub_daily=ok_daily)
    df_ = difference(sf, "quiet", "news", H_PRIMARY, rng)
    print(f"\n  with the surviving >{EXTREME_1D:.0%} print (OXY 2020-03-09) IN  : "
          f"uncond {uncond.set_index('h').loc[H_PRIMARY, 'mean']:+8.2f}   "
          f"quiet {cond.iloc[0]['mean']:+8.2f}   news {cond.iloc[1]['mean']:+8.2f}"
          f"   diff {diff['mean']:+8.2f}")
    print(f"  with every window containing it EXCLUDED       : "
          f"uncond {uf.iloc[0]['mean']:+8.2f}   quiet {cf.iloc[0]['mean']:+8.2f}   "
          f"news {cf.iloc[1]['mean']:+8.2f}   diff {df_['mean']:+8.2f}")
    out["variants"] = dict(no_skip=dict(uncond=float(uns.iloc[0]["mean"]),
                                        diff=float(dns["mean"])),
                           news_t5_t=dict(diff=float(d6["mean"])),
                           ex_extreme=dict(uncond=float(uf.iloc[0]["mean"]),
                                           diff=float(df_["mean"])))

    # ----------------------------------------------------------- controls
    _hdr("CONTROLS (b) RANDOM PICK, (c) DATE SHUFFLE, (d) NEWS-LABEL SHUFFLE")
    print(f"{CTRL_REPS} draws each. Rule 10: mean AND SD, never one draw.")
    print("Rule 14: every null's SD is printed next to the ratio against the")
    print("real series' block-bootstrap SE - a within-date permutation is")
    print("anti-conservative for a persistent signal (H16 Finding 2).\n")
    lab5, fwd5s, elig5s = aux["lab"], aux["fwd"], aux["elig"]
    act_all = _nanmean(ukeep[H_PRIMARY]["spread"])
    se_all = uncond.set_index("h").loc[H_PRIMARY, "se"] / 1e4

    rnd = random_pick_control(lab5, fwd5s, N_Q, rng)
    shf = date_shuffle_control(sa, elig5s, fwd5s, N_Q, rng)
    ctrl = pd.DataFrame([
        dict(control="(b) random pick", target="unconditional spread",
             actual=act_all * 1e4, null_mean=rnd.mean() * 1e4,
             null_sd=rnd.std(ddof=1) * 1e4, se_ratio=rnd.std(ddof=1) / se_all,
             pctile=float((rnd < act_all).mean()) * 100,
             p_two=float(2 * min((rnd >= act_all).mean(), (rnd <= act_all).mean()))),
        dict(control="(c) date shuffle", target="unconditional spread",
             actual=act_all * 1e4, null_mean=shf.mean() * 1e4,
             null_sd=shf.std(ddof=1) * 1e4, se_ratio=shf.std(ddof=1) / se_all,
             pctile=float((shf < act_all).mean()) * 100,
             p_two=float(2 * min((shf >= act_all).mean(), (shf <= act_all).mean()))),
    ])
    act_d = diff["mean"] / 1e4
    se_d = diff["se"] / 1e4
    nsh = news_shuffle_control(lab5, fwd5s, grp_news, N_Q, rng)
    ctrl = pd.concat([ctrl, pd.DataFrame([
        dict(control="(d) news-label shuffle", target="quiet - news DIFFERENCE",
             actual=act_d * 1e4, null_mean=nsh.mean() * 1e4,
             null_sd=nsh.std(ddof=1) * 1e4, se_ratio=nsh.std(ddof=1) / se_d,
             pctile=float((nsh < act_d).mean()) * 100,
             p_two=float(2 * min((nsh >= act_d).mean(), (nsh <= act_d).mean())))
    ])], ignore_index=True)
    print(ctrl.to_string(index=False, float_format=_fmt))
    print("\n(b) must be centred on zero - it is the noise scale, not a test.")
    print("(c) must DESTROY the effect if reversal is a timing claim. It is the")
    print("    control that killed H15, and here it is discriminating: a spread")
    print("    that survives a date shuffle is a stock characteristic.")
    print("(d) is the null for H21b. If the real difference sits inside it, the")
    print("    news conditioning is decoration.")
    print("\nRULE 14 IN ACTION, and it decides how to read the p-values above:")
    print(f"    the within-date permutation nulls (b) and (c) are "
          f"{1 / ctrl.iloc[0]['se_ratio']:.1f}x and "
          f"{1 / ctrl.iloc[1]['se_ratio']:.1f}x")
    print("    TIGHTER than the block-bootstrap SE of the real series, so their")
    print("    p=0.00 is an artefact of the null, not evidence. Permuting labels")
    print("    inside a date destroys the persistence of the P&L a sticky")
    print("    cross-sectional tilt generates. The honest statistic is the block")
    print(f"    bootstrap: t = {uncond.set_index('h').loc[H_PRIMARY, 't']:+.2f}. "
          "Control (d)'s null is only")
    print(f"    {1 / ctrl.iloc[2]['se_ratio']:.1f}x tighter and still does not "
          "reject the difference.")
    out["controls"] = ctrl.to_dict("records")

    # -------------------------------------------------------------- costs
    _hdr(f"H21f COSTS ({COST_BPS:.0f} bps round trip per leg, large caps)")
    crows = []
    u5 = uncond.set_index("h").loc[H_PRIMARY]
    crows.append(dict(book="long/short, all names", **costs(
        float(u5["mean"]), float(u5["turn_l"]), float(u5["turn_s"]), H_PRIMARY)))
    for _, r in cond.iterrows():
        crows.append(dict(book=f"long/short, {r['group']}", **costs(
            float(r["mean"]), float(r["turn_l"]), float(r["turn_s"]), H_PRIMARY)))
    for _, r in lo.iterrows():
        crows.append(dict(book=f"LONG-ONLY losers, {r['group']}", **costs(
            float(r["mean"]), float(r["turn"]), 0.0, H_PRIMARY)))
    cost = pd.DataFrame(crows)
    print(cost.to_string(index=False, float_format=_fmt))
    print("\nturn = summed leg turnover per rebalance; break-even c* = gross /")
    print("turn is the round-trip cost at which the book earns exactly zero.")
    print("No borrow cost on the short leg, no impact, no shorting constraint -")
    print("all three push the same way.")
    out["costs"] = cost.to_dict("records")

    # ------------------------------------------------------------- verdict
    _hdr("VERDICT")
    q, nws = cond.iloc[0], cond.iloc[1]
    print(f"H21a unconditional reversal at h={H_PRIMARY}: {u5['mean']:+.2f} bps "
          f"[{u5['lo']:+.2f}, {u5['hi']:+.2f}], t={u5['t']:+.2f}, "
          f"halves {u5['half1']:+.2f}/{u5['half2']:+.2f}")
    print(f"H21b (common dates) quiet {diff['mean_a']:+.2f} vs news "
          f"{diff['mean_b']:+.2f}; standalone {q['mean']:+.2f} / {nws['mean']:+.2f}; "
          f"DIFFERENCE {diff['mean']:+.2f} bps "
          f"[{diff['lo']:+.2f}, {diff['hi']:+.2f}], t={diff['t']:+.2f}, "
          f"halves {diff['half1']:+.2f}/{diff['half2']:+.2f}")
    print(f"H21c abnormal-news terciles: "
          + " -> ".join(f"{v:+.2f}" for v in conda['mean']))
    print(f"H21d long-only losers vs pool: "
          + "  ".join(f"{r['group']} {r['mean']:+.2f}" for _, r in lo.iterrows()))
    print(f"H21e top-liquidity half: uncond "
          f"{liq.set_index('subset').loc['top-liquidity half', 'uncond']:+.2f}, "
          f"diff {liq.set_index('subset').loc['top-liquidity half', 'diff']:+.2f}")
    print(f"H21f break-even round trip, long/short all names: "
          f"{cost.iloc[0]['breakeven_bps']:.2f} bps against {COST_BPS:.0f} charged")
    print("\nRegistered failure conditions: H21b fails if the difference sits")
    print("inside the news-label-shuffle null or flips sign across halves;")
    print("H21f fails if break-even is under 10 bps. Read them off the tables.")
    print("\nTRIAL COUNT: 16 pre-registered variants (4 unconditional horizons,")
    print("4 news-conditioned horizons, within-group terciles, abnormal-news")
    print("terciles, long-only, 2 liquidity subsets + the bottom tercile,")
    print("no-skip, the t-5..t news window, the extreme-print rerun). Controls")
    print("are nulls and do not count. The MIN_CELL grid is a coverage")
    print("diagnostic reported in full, not a search. Best |t| anywhere is 2.54,")
    print("in the cell that is measured on 31 independent windows; this repo's")
    print("standalone bar is t > 3 (Harvey-Liu) and at 16 trials that is if")
    print("anything generous.")

    (config.SCOUT_DIR / "reversal_results.json").write_text(
        json.dumps(out, indent=1, default=str))
    print(f"\nwrote scout/reversal_results.json   ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
