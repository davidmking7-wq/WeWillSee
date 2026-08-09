"""H24 - post-earnings drift measured from the NEWS, not from the price reaction.

MECHANISM (one sentence, before any number)
-------------------------------------------
The market learns how a quarter landed relative to expectations from the
coverage that follows the release - how much gets written and how positive it
reads - so if that text is absorbed more slowly than the price reaction itself
(attention is scarce, reading is costly: Barber-Odean 2008, Tetlock 2007,
Bernard-Thomas 1989), then a news-measured surprise should forecast drift over
the following weeks where the price reaction alone does not.

WHY THIS IS NOT A REPEAT OF H2b, H16 OR H26
-------------------------------------------
- H2b rejected drift sorted on the two-day PRICE REACTION (+5% and -5% reactors
  ended identically, n~6k). The reaction is re-run HERE as control C and it has
  to reproduce that null, or this pipeline disagrees with a settled result.
- H16 rejected headline tone as an UNCONDITIONAL cross-sectional signal, on the
  same news panel. It measured tone on every session of every name, where 49%
  of symbol-sessions score exactly zero net tone because no lexicon word fired.
  This lab measures tone only in the two sessions around an earnings release -
  the one moment when a large cap is guaranteed to be written about. Measured
  here: the announcement window carries a MEDIAN OF 15 STORIES and only 9.6% of
  events score zero tone, against H16's 49%. Same instrument, ~5x the signal
  density, and pointed at the event the literature says it should work on.
- H26 rejected drift sorted on accounting SUE over the S&P 1500. This is a
  different sort variable (rank correlation to the reaction is 0.181 here,
  0.118 there), a different universe, and it needs no fundamental data at all.

The claim under test is specific and falsifiable: A (tone) and/or B (abnormal
coverage volume) drift where C (the price reaction) does not. If all three are
null, that is a clean replication of H2b with two better instruments.

VERDICT: REJECTED - AND THE POSITIVE CONTROL IS WHAT MAKES IT READABLE
----------------------------------------------------------------------
Every number in this docstring is from `python -m scout.news_pead_lab`
(~9 min warm; full output kept in scout/cache_newspead_lastrun.txt).

1. THE INSTRUMENT WORKS. Announcement-window tone sorts the announcement's own
   two-day reaction monotonically across all five quintiles - **-93.0 -33.6
   +25.7 +72.4 +156.4 bps, Q5-Q1 = +249.4 bps at t = +12.36** (event-level SE,
   contemporaneous by construction and therefore NOT tradeable). Abnormal
   coverage volume sorts the ABSOLUTE reaction the same way H15 found for
   attention generally: 3.71% in Q5 against 2.61% in Q1. So a null below is a
   statement about the market, not about a dead signal.

2. AND THE DRIFT IS ZERO. Market-adjusted quintile spreads, entry at
   close(a+1), 3,780 events, 96 firms, 2016-01..2026-05:

       signal                h=21              h=42
       tone (all)        +11.53 bps t+0.27  -20.75 bps t-0.36
       tone (specific)   -46.06 bps t-1.14  -51.85 bps t-0.90
       abn volume (all)   -8.14 bps t-0.21  -46.65 bps t-0.83
       abn volume (spec) -31.68 bps t-0.79  -44.19 bps t-0.72
       reaction (C)      -11.16 bps t-0.28  -18.10 bps t-0.31

   No cell reaches |t| = 1.2 at either registered horizon, every 95% interval
   straddles zero, and the halves disagree in sign in 8 of the 10 registered
   cells. **The control reproduced its null (C is flat, as H2b and H26d say),
   and A and B did not beat it** - which is the pre-registered failure
   condition for H24, stated before the run.

3. THE ONE CELL THAT LOOKS LIKE SOMETHING IS KILLED BY ITS OWN CONTROL, IN
   H15'S EXACT WAY. Specific-story tone at h=63 is -136.55 bps (t = -1.63), the
   biggest |t| in the registered set. The FIRM-LEVEL DATE SHUFFLE - each firm's
   own tone values permuted across that firm's own announcement dates, so which
   firms get written about kindly survives and only the timing dies - returns
   **-100.61 +- 45.61 bps, p = 0.212**. Seventy-four per cent of the effect
   survives destroying its timing entirely. It is a property of WHICH firms get
   positive coverage, not of WHEN.

4. NEWS ADDS NOTHING TO THE PRICE. Double sort, tone quintiles inside reaction
   terciles at h=42: **-97.4 / -37.9 / -35.7 bps** - negative in all three,
   nowhere near the registered positive sign. The rank correlation between tone
   and the reaction is 0.181, so these genuinely are different variables; the
   news variable simply carries no forward information that the price does not.

5. COSTS ARE ACADEMIC HERE BECAUSE THE GROSS SIGN IS WRONG, but they are
   reported: the best long-only cell (tone Q5 minus pool) is +11.62 bps at
   h=42, break-even 11.6 bps against the 10 bps charged, t = +0.42.

WHERE THE shift() IS (the only thing that can manufacture this result)
---------------------------------------------------------------------
`a` = an 8-K Item 2.02 filing date from scout/earnings_history.json (real SEC
dates, not a proxy). e = first session index with session date >= a.

    signals   news attributed by news_data's rule to sessions {e, e+1} -
              i.e. every story a trader could have READ before close(e+1) -
              plus a coverage baseline over sessions [e-63, e-1] only
    ENTRY     close(e + 1)
    fwd_h     close(e + 1 + h) / close(e + 1) - 1

So the earliest return any signal touches is close(e+1) -> close(e+2). The
two-session window is not a convenience: a release before the open on day a
moves session e and a release after the close on day a moves session e+1, and
the 8-K's filing DATE does not say which - so {e, e+1} is the smallest window
that contains the reaction under both conventions, and close(e+1) is the first
price that is after it under both. `main` asserts sessions[e] >= a and
sessions[e+1] > a on the real event table before any number prints, and
`--selftest` proves on synthetic data that a signal built from sessions
{e, e+1} cannot see close(e+2) onward.

The contamination scale is printed on the real data, as H16 requires: tone
sorts the CONTEMPORANEOUS two-day reaction at +249.4 bps and the FORWARD
21-session return at +11.5 bps. A study that entered at close(e-1) - i.e. that
treated the announcement window's coverage as if it were tradeable before the
announcement - would have reported a 22x larger "PEAD" that is entirely the
announcement move.

SIGNALS (all four registered before the run; all four reported)
---------------------------------------------------------------
  A  tone       (pos - neg) / (pos + neg + 1), Loughran-McDonald-style word
                counts summed over every story attributed to sessions e and
                e+1. Two forms: ALL stories, and SPECIFIC only (news_data's
                filter: not templated wire, <= 10 tags).
  B  abn_vol    log( (n_e + n_{e+1} + 1) / (2 * base_e + 1) ) where base_e is
                the median daily story count over sessions [e-63, e-1] for that
                symbol - news_attention_lab's H15 form, applied to the event
                window. Same two story sets.
  C  react2     close(e+1)/close(e-1) - 1, market-adjusted. The control. It has
                to be null (H2b, H26d) or this pipeline is wrong.

Ranked into quintiles against the PREVIOUS 252 sessions of announcements
(Livnat-Mendenhall's trailing-breakpoint rule, min cohort 100), never against
the event's own cohort: earnings arrive in three-week bursts, so a within-date
rank is 25 firms in the third week of January and 2 on a Friday in December,
and it would silently make the Friday firms extreme.

CONTROLS (six, all run, none optional)
--------------------------------------
a. RANDOM-PICK quintiles from the identical eligible pool, 200 draws, mean AND
   sd, with the SE ratio to the block bootstrap printed (Rule 14).
b. FIRM-LEVEL DATE SHUFFLE, 200 draws - the row that decides H24, and the one
   that fires. Each firm keeps its own set of tone/attention values; only which
   announcement they attach to is destroyed.
c. THE PRICE-REACTION SORT (C) - the H2b/H26d replication, in the same cells.
d. MATCHED BENCHMARKS - the equal-weight pool of every eligible event over the
   identical windows, and SPY over each event's identical calendar window.
e. POSITIVE CONTROL - the announcement reaction by news quintile, and the
   ABSOLUTE reaction by attention quintile. Without these a null is unreadable.
f. LATE-WINDOW PLACEBO - sessions +42..+84 on the same signal.

DATA (US equities only; no crypto, options, futures or FX)
----------------------------------------------------------
news    scout/news_data.load_panel() - 308,870 Benzinga stories, 464,430
        symbol-rows, 2016-01-02..2026-07-31, over the 120 most liquid S&P 500
        members AS OF 2016-01-04 (scout/pit.py point-in-time membership, so
        BRCM/CELG/EMC/TWX/ESRX/MON/AET/PXD are in and no post-2016 addition is).
dates   scout/earnings_history.json - 62,822 real 8-K Item 2.02 filing dates.
prices  scout/data.py daily SIP closes via news_sentiment_lab.load_bars(), so
        H16 and H24 cannot disagree about a price. Split-repaired from Alpaca's
        own corporate-actions feed (AAPL 2020-08-31 4:1, 1,173 bars).

DATA DEBT, HANDLED WITH THREE GUARDS AND THE COUNT OF EACH PRINTED
------------------------------------------------------------------
1. Unapplied splits (5.1% of splits; BACKTEST-REPORT.md). Repaired from the
   corporate-actions feed: 1 event here (AAPL). MET's 2017 Brighthouse spin-off
   is correctly left alone - its filed ratio 1.122 is under the classifier's
   resolution and "repairing" it would INSERT an 11% fake jump.
2. Residual |1-day return| > 45% anywhere in an event's widest window: flagged
   per event and the whole study is re-run without them as a registered variant.
3. Frozen quotes (sue_lab's Rule 17). This universe is point-in-time, so it
   contains names that stopped trading: MON prints 127.95 at zero volume for
   695 sessions after Bayer closed, and reused tickers splice a penny quote onto
   an unrelated issuer. Symbols are retired at their first run of 10 identical
   closes and zero-volume sessions are blanked.

KNOWN LIMITS (measured or structural, none of them fixed here)
--------------------------------------------------------------
1. POWER, and it is the binding constraint. 3,780 events sound like a lot but
   they sit on 1,001 distinct entry sessions inside a 2,664-session calendar =
   **63 non-overlapping 42-session windows**. The h=42 interval is about +-115
   bps. This study excludes a news-sorted drift bigger than roughly 1.2% per
   quarter in this cohort; it cannot exclude one of 20-30 bps.
2. SURVIVORSHIP IN THE EVENT LAYER, not the price layer. The price universe is
   point-in-time, but only 96 of the 120 panel names have 8-K dates: the SEC's
   ticker file maps CIK to the CURRENT ticker, so FB, UTX, BRCM, CELG, TWX,
   EMC, MON, AET, PXD, ESRX, ATVI, ALXN, MYL, CBS, WBA, EA and 8 others have no
   earnings history at all. Direction is stateable: the missing names are the
   acquired and the renamed, so the event sample is tilted toward survivors.
   XOM additionally has only one usable 8-K date in the whole file.
3. MEGA CAPS ONLY. These are the 120 most liquid S&P 500 names of 2016 - the
   cohort where PEAD is most thoroughly arbitraged and where H26 also found the
   surprise fully priced by close(a+1). This is not evidence about small caps.
4. THE LEXICON IS CRUDE, and news_data says so: 435 hand-typed words, no
   syntax beyond a 3-token negation flip, "Beats Estimates But Warns On
   Guidance" scores +0.167. The positive control (point 1 above) is what
   establishes it is not merely noise; it does not make it a language model.
5. ONE PUBLISHER. Benzinga is fast and broad but it is not the tape.
6. ONE MACRO ERA, 2016-2026.

Run: python -m scout.news_pead_lab              (full study, ~9 min warm)
     python -m scout.news_pead_lab --selftest    (offline leakage checks, <10s)
     python -m scout.news_pead_lab --fast        (structural smoke run, NOT a result)
     python -m scout.news_pead_lab --no-retire   (what the frozen-quote guard is worth)
"""
from __future__ import annotations

import argparse
import json
import math
import time
import warnings

import numpy as np
import pandas as pd

from . import config, news_data, news_sentiment_lab as nsl
# The cross-sectional estimator is scout/sue_lab's, imported rather than
# copied, so H24 and H26 cannot quietly disagree about what a decile spread,
# a session collapse or a block bootstrap is.
from .sue_lab import _stat, block_boot, random_pick_control, retire_stale, \
    session_sums, trailing_deciles

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against an outcome.
# --------------------------------------------------------------------------
HORIZONS = (5, 21, 42, 63)      # 21 and 42 are the registered headline;
                                # 5 and 63 are shape context, printed always
HEADLINE_H = (21, 42)
N_Q = 5                         # quintiles primary (deciles run as a variant):
                                # ~380 announcements a year over 96 firms means
                                # a trailing-year cohort of ~380, so deciles
                                # would be 38 events per bucket
COHORT_WINDOW = 252             # sessions of PRIOR announcements supplying the
                                # quantile breakpoints (Livnat-Mendenhall)
MIN_COHORT = 100
BASE_LOOKBACK = 63              # sessions of prior coverage for the attention
                                # baseline (news_attention_lab uses 60 daily)
MIN_GAP_DAYS = 45               # two Item-2.02 filings closer than this are one
                                # earnings event; the later one is dropped
COST_BPS = 10.0                 # round trip, per leg
WINSOR_P = 0.01                 # forward returns clipped at their own 1/99th
                                # inside each analysed subsample; the
                                # unwinsorised number is printed beside it
STALE_RUN = 10                  # identical consecutive closes = frozen quote
EXTREME_1D = 0.45               # |1-day return| above this is a presumed defect
BOOT_REPS = 2000
CTRL_REPS = 200
SEED = 20260809
BENCH = "SPY"

DATASET_PKL = config.SCOUT_DIR / "cache_newspead_dataset.pkl"

#: (column, label, needs_news) - every signal that gets a primary row.
SIGNALS = (
    ("tone",       "A tone (all)",       True),
    ("tone_spec",  "A tone (specific)",  True),
    ("abn",        "B abn vol (all)",    False),
    ("abn_spec",   "B abn vol (spec)",   False),
    ("react2",     "C reaction (CTRL)",  False),
)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def build_dataset(force: bool = False, retire: bool = True,
                  verbose: bool = True) -> dict:
    """Split-repaired closes + the news word/count frames, cached.

    Bars come from news_sentiment_lab.load_bars() so this lab and H16 read the
    same prices; word counts come from news_sentiment_lab.tone_frames() so they
    read the same lexicon output. Nothing here is re-implemented.
    """
    if DATASET_PKL.exists() and not force:
        ds = pd.read_pickle(DATASET_PKL)
        if ds.get("version") == 1 and ds.get("retired") == retire:
            return ds
    t0 = time.time()
    bars = nsl.load_bars(verbose=verbose)
    close, volume = bars["close"], bars["volume"]
    sessions = news_data._session_index(close)
    close.index, volume.index = sessions, sessions
    if retire:
        close = retire_stale(close, volume, STALE_RUN, verbose=verbose)
    news = news_data.load_panel()
    if verbose:
        print(f"  news: {len(news):,} symbol-rows, {news['id'].nunique():,} "
              f"stories, {news['created_at'].min().date()}"
              f"..{news['created_at'].max().date()}")
    audit = news_data.audit_attribution(news, close)   # asserts 0 violations
    tf = nsl.tone_frames(news, sessions)
    cols = [c for c in close.columns if c in tf["all"]["n"].columns]
    ds = {
        "version": 1,
        "retired": retire,
        "sessions": sessions,
        "close": close[cols + ([BENCH] if BENCH not in cols else [])],
        "volume": volume.reindex(columns=close.columns),
        "frames": {k: {kk: vv.reindex(columns=cols) for kk, vv in v.items()}
                   for k, v in tf.items()},
        "repairs": bars["repairs"],
        "attribution_audit": audit,
    }
    pd.to_pickle(ds, DATASET_PKL)
    if verbose:
        print(f"  dataset built in {time.time() - t0:.0f}s -> {DATASET_PKL.name}")
    return ds


def announcement_dates(symbols: list[str], sessions: pd.DatetimeIndex,
                       verbose: bool = True) -> pd.DataFrame:
    """Real 8-K Item 2.02 filing dates -> one row per earnings event.

    De-duplication rule, registered: a filing within MIN_GAP_DAYS of the
    previously kept one for the same firm is the SAME earnings event (companies
    file 8-K/A amendments and, in a few cases, monthly operating updates under
    Item 2.02). The earlier filing is the announcement; the later is dropped.
    """
    hist = json.loads((config.SCOUT_DIR / "earnings_history.json")
                      .read_text(encoding="utf-8"))
    lo, hi = str(sessions[0].date()), str(sessions[-1].date())
    rows, dropped, missing = [], 0, []
    for s in symbols:
        ds = sorted(d for d in hist.get(s, []) if lo <= d <= hi)
        if not ds:
            missing.append(s)
            continue
        last = None
        for d in ds:
            t = pd.Timestamp(d)
            if last is not None and (t - last).days < MIN_GAP_DAYS:
                dropped += 1
                continue
            rows.append((s, t))
            last = t
    ev = pd.DataFrame(rows, columns=["ticker", "ann"])
    if verbose:
        print(f"  8-K Item 2.02 dates: {len(ev):,} events over "
              f"{ev['ticker'].nunique()} of {len(symbols)} panel symbols "
              f"({dropped:,} filings dropped as within-{MIN_GAP_DAYS}-day repeats)")
        print(f"  NO EARNINGS HISTORY for {len(missing)} panel symbols "
              f"(SEC ticker file maps CIK -> CURRENT ticker, so the acquired "
              f"and the renamed vanish):")
        print(f"    {' '.join(sorted(missing))}")
    return ev


# --------------------------------------------------------------------------
# events -> signals and returns
# --------------------------------------------------------------------------

def attach(ev: pd.DataFrame, ds: dict, horizons=HORIZONS,
           verbose: bool = True) -> pd.DataFrame:
    """Signals A/B/C, entry index and forward returns for every announcement.

    ENTRY = close(e + 1), where e is the first session at or after the 8-K
    date. Every signal input is read at a session index <= e + 1; every return
    starts at e + 1. That is the whole no-lookahead argument, and `main`
    asserts it on the real table.
    """
    sess = ds["sessions"]
    close, volume = ds["close"], ds["volume"]
    F = ds["frames"]
    n_t = len(sess)
    cl = close.to_numpy()
    col = {s: j for j, s in enumerate(close.columns)}
    spy = cl[:, col[BENCH]]
    ret1 = (close / close.shift(1) - 1.0).to_numpy()
    extreme = np.abs(ret1) > EXTREME_1D
    dvol = (close * volume.reindex(columns=close.columns)) \
        .rolling(20, min_periods=10).median().to_numpy()

    ev = ev[ev["ticker"].isin(col) & ev["ticker"].isin(F["all"]["n"].columns)].copy()
    e = np.searchsorted(sess.to_numpy(), ev["ann"].to_numpy(), side="left")
    ev["e"] = e
    keep = (e >= BASE_LOOKBACK + 1) & (e + 1 + 2 * max(horizons) < n_t)
    n_edge = int((~keep).sum())
    ev = ev[keep].reset_index(drop=True)
    e = ev["e"].to_numpy()
    entry = e + 1
    ev["entry"] = entry

    ncol = {s: j for j, s in enumerate(F["all"]["n"].columns)}
    jn = ev["ticker"].map(ncol).to_numpy()
    jc = ev["ticker"].map(col).to_numpy()

    for kind, suf in (("all", ""), ("specific", "_spec")):
        pos = F[kind]["pos"].to_numpy()
        neg = F[kind]["neg"].to_numpy()
        cnt = F[kind]["n"].to_numpy()
        p = pos[e, jn] + pos[e + 1, jn]
        g = neg[e, jn] + neg[e + 1, jn]
        n_win = cnt[e, jn] + cnt[e + 1, jn]
        # A: net tone over the two-session window. NaN when the window is
        # silent - a quiet announcement has no tone, and calling it neutral
        # would put "nobody wrote about it" in the middle quintile.
        ev["tone" + suf] = np.where(n_win > 0, (p - g) / (p + g + 1.0), np.nan)
        ev["nstory" + suf] = n_win
        # B: abnormal coverage against this symbol's own trailing normal. The
        # shift(1) comes FIRST, so sessions e and e+1 can never enter the
        # baseline they are measured against.
        base = (F[kind]["n"].shift(1)
                .rolling(BASE_LOOKBACK, min_periods=BASE_LOOKBACK // 2)
                .median().to_numpy())[e, jn]
        ev["abn" + suf] = np.log((n_win + 1.0) / (2.0 * base + 1.0))

    # C: the two-session price reaction. close(e-1) -> close(e+1) spans the
    # move whether the release was before the open on day a or after the close.
    ev["react2"] = cl[e + 1, jc] / cl[e - 1, jc] - 1.0
    ev["rmkt2"] = spy[e + 1] / spy[e - 1] - 1.0
    ev["react2_adj"] = ev["react2"] - ev["rmkt2"]
    ev["px_entry"] = cl[entry, jc]
    ev["dvol20"] = dvol[e, jc]

    for h in horizons:
        ev[f"fwd{h}"] = cl[entry + h, jc] / cl[entry, jc] - 1.0
        ev[f"mkt{h}"] = spy[entry + h] / spy[entry] - 1.0
    # LATE-WINDOW PLACEBO: sessions +42..+84 after entry on the same signal.
    lo_i, hi_i = entry + 42, entry + 84
    ev["fwd_late"] = cl[hi_i, jc] / cl[lo_i, jc] - 1.0
    ev["mkt_late"] = spy[hi_i] / spy[lo_i] - 1.0

    # RULE 13 diagnostic: trailing 252-session beta to SPY, ending at e-1.
    ev["beta252"] = _trailing_beta(ret1, e, jc, col[BENCH])

    # data-defect flag over the widest window any cell reads
    ev["defect"] = [bool(extreme[a:b + 1, c].any())
                    for a, b, c in zip(np.maximum(e - 2, 0),
                                       entry + 2 * max(horizons), jc)]
    ev["price_ok"] = np.isfinite(ev[[f"fwd{h}" for h in horizons]]
                                 .to_numpy()).any(axis=1) \
        & np.isfinite(ev["react2"].to_numpy())
    if verbose:
        print(f"  {n_edge:,} events dropped at the sample edges "
              f"(need {BASE_LOOKBACK} sessions of baseline before and "
              f"{2 * max(horizons)} after)")
    return ev


def _trailing_beta(ret1: np.ndarray, e: np.ndarray, j: np.ndarray,
                   jm: int, w: int = 252) -> np.ndarray:
    """Per-event trailing beta to the benchmark over the w sessions ending at
    e-1. Rule 13's diagnostic: H25 was a beta sort wearing a signal's clothes,
    and printing beta by bucket is what would have caught it."""
    out = np.full(len(e), np.nan)
    rows = np.flatnonzero(e >= w)
    for a in range(0, len(rows), 4000):
        blk = rows[a:a + 4000]
        off = e[blk][:, None] - np.arange(w, 0, -1)[None, :]
        ri = ret1[off, j[blk][:, None]]
        rm = ret1[off, jm]
        good = np.isfinite(ri) & np.isfinite(rm)
        ri = np.where(good, ri, np.nan)
        rm = np.where(good, rm, np.nan)
        ci = ri - np.nanmean(ri, axis=1, keepdims=True)
        cm = rm - np.nanmean(rm, axis=1, keepdims=True)
        var = np.nansum(cm * cm, axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[blk] = np.where(var > 0, np.nansum(ci * cm, axis=1) / var, np.nan)
    return out


# --------------------------------------------------------------------------
# one (signal, horizon) cell
# --------------------------------------------------------------------------

def run_sort(ev: pd.DataFrame, sig_col: str, ret_col: str, mkt_col: str,
             h: int, n_t: int, rng: np.random.Generator, n_q: int = N_Q,
             adjust: bool = True, winsor: float = WINSOR_P,
             window: int = COHORT_WINDOW, min_cohort: int = MIN_COHORT) -> dict:
    """Trailing-cohort quantile sort, collapsed to sessions, block-bootstrapped.

    `adjust` subtracts SPY over the event's identical calendar window (Rule 13).
    `winsor` clips the RAW forward return at its own 1st/99th percentile inside
    the analysed subsample, applied identically to every event so it cannot
    favour a bucket; the unwinsorised number is printed beside every headline.
    """
    d = ev[np.isfinite(ev[sig_col]) & np.isfinite(ev[ret_col])]
    if len(d) < 50:
        return {}
    r = d[ret_col].to_numpy()
    if winsor and len(r) > 200:
        r = np.clip(r, *np.nanquantile(r, [winsor, 1 - winsor]))
    entry = d["entry"].to_numpy()
    y = r - (d[mkt_col].to_numpy() if adjust else 0.0)
    lab = trailing_deciles(d[sig_col].to_numpy(), entry, n_q,
                           window=window, min_cohort=min_cohort)
    M = session_sums(entry, lab, y, n_t, n_q - 1, 0)
    out = block_boot(M, h, BOOT_REPS, rng)
    med = int(np.median(entry[lab >= 0])) if (lab >= 0).any() else 0
    for name, m in (("half1", entry < med), ("half2", entry >= med)):
        a, b, _ = _stat(session_sums(entry[m], lab[m], y[m], n_t,
                                     n_q - 1, 0).sum(axis=0))
        out[name] = a - b
    out.update(lab=lab, entry=entry, y=y, sig=d[sig_col].to_numpy(),
               ticker=d["ticker"].to_numpy(), idx=d.index.to_numpy(),
               n_sess=len(np.unique(entry[lab >= 0])),
               bucket_means=[float(np.nanmean(y[lab == k])) if (lab == k).any()
                             else np.nan for k in range(n_q)],
               bucket_n=[int((lab == k).sum()) for k in range(n_q)])
    return out


def firm_date_shuffle(ticker: np.ndarray, sig: np.ndarray, entry: np.ndarray,
                      y: np.ndarray, n_t: int, rng: np.random.Generator,
                      n_q: int = N_Q, reps: int = CTRL_REPS) -> np.ndarray:
    """CONTROL (b), the one that decides H24: permute each FIRM's own signal
    values across that firm's own announcement dates.

    What survives: which firms exist, when they announce, and each firm's whole
    distribution of tone / attention - so "the wire is kind to good stocks"
    survives entirely intact. What dies: which quarter's coverage belongs to
    which announcement. A DRIFT effect must collapse here; a firm CHARACTERISTIC
    will not. This is sue_lab.date_shuffle_control with the cohort window this
    lab's much thinner event flow requires (a trailing 252 sessions rather than
    63), which is why it is written out here instead of imported.
    """
    pos = pd.Series(np.arange(len(ticker)), index=pd.Index(ticker))
    groups = [g.to_numpy() for _, g in pos.groupby(level=0, sort=False) if len(g) > 1]
    out = np.empty(reps)
    for r in range(reps):
        s = sig.copy()
        for g in groups:
            s[g] = rng.permutation(s[g])
        lab = trailing_deciles(s, entry, n_q, window=COHORT_WINDOW,
                               min_cohort=MIN_COHORT)
        a, b, _ = _stat(session_sums(entry, lab, y, n_t, n_q - 1, 0).sum(axis=0))
        out[r] = a - b
    return out


def fmt(res: dict, label: str, n_q: int = N_Q) -> str:
    if not res:
        return f"  {label:<26} (too few events to rank)"
    return (f"  {label:<26} Q{n_q}-Q1 {1e4 * res['spread']:+8.2f} bps  "
            f"[{1e4 * res['lo']:+8.2f},{1e4 * res['hi']:+8.2f}]  "
            f"t={res['t']:+5.2f}  halves {1e4 * res['half1']:+8.2f}/"
            f"{1e4 * res['half2']:+8.2f}  n {int(res['n_top']):>5}/"
            f"{int(res['n_bot']):>5}")


# --------------------------------------------------------------------------
# the study
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.news_pead_lab")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--no-retire", action="store_true",
                    help="skip the frozen-quote retirement (shows its worth)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fast", action="store_true",
                    help="few bootstrap/control draws - a smoke run, NOT a result")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    global BOOT_REPS, CTRL_REPS
    if args.fast:
        BOOT_REPS, CTRL_REPS = 80, 10

    # empty buckets are reported as nan on purpose (see fmt / bucket_means);
    # numpy's warning about them is noise, the nan in the table is the message.
    warnings.filterwarnings("ignore", message="Mean of empty slice")
    warnings.filterwarnings("ignore", message="Degrees of freedom <= 0")

    rng = np.random.default_rng(SEED)
    t0 = time.time()

    print("=== data ===")
    ds = build_dataset(force=args.rebuild or args.no_retire,
                       retire=not args.no_retire)
    sess = ds["sessions"]
    n_t = len(sess)
    print(f"  bars {n_t} sessions x {ds['close'].shape[1]} symbols  "
          f"{sess[0].date()}..{sess[-1].date()}")
    aud = ds["attribution_audit"]
    print(f"  attribution audit: {aud['rows']:,} story-rows, "
          f"{aud['rolled_pct']:.1f}% rolled to a later session, "
          f"{aud['VIOLATIONS_same_session_after_close']} lookahead violations")

    print("\n=== events ===")
    syms = [c for c in ds["frames"]["all"]["n"].columns]
    ev = announcement_dates(syms, sess)
    ev = attach(ev, ds)
    ev = ev[ev["price_ok"]].reset_index(drop=True)

    # POINT-IN-TIME AUDIT on the real table, not a synthetic one.
    assert (sess[ev["e"].to_numpy()] >= ev["ann"]).all(), "event session before the 8-K"
    assert (sess[ev["entry"].to_numpy()] > ev["ann"]).all(), "entry price on the 8-K date"
    assert (ev["entry"].to_numpy() == ev["e"].to_numpy() + 1).all(), "entry is not e+1"
    print(f"  point-in-time audit passed on all {len(ev):,} events: "
          f"session(e) >= 8-K date, entry price = close(e+1) > 8-K date")
    print(f"  usable: {len(ev):,} events, {ev['ticker'].nunique()} firms, "
          f"{ev['entry'].nunique():,} distinct entry sessions, "
          f"{ev['ann'].min().date()}..{ev['ann'].max().date()}")
    print(f"  {100 * ev['defect'].mean():.2f}% of events touch a "
          f"|1-day| > {EXTREME_1D:.0%} move somewhere in their widest window")

    print("\n  INSTRUMENT DENSITY - why this is not H16 again:")
    for kind, suf in (("all stories", ""), ("specific only", "_spec")):
        n = ev["nstory" + suf]
        tone = ev["tone" + suf]
        print(f"    {kind:<14} window story count: median {n.median():.0f}, "
              f"mean {n.mean():.1f}, share with >=1 story "
              f"{100 * (n > 0).mean():.1f}%;  tone exactly 0 on "
              f"{100 * (tone.fillna(0) == 0).mean():.1f}% of events "
              f"(H16's unconditional panel: 49%)")

    # ------------------------------------------------------------- primary
    print(f"\n=== H24 PRIMARY: quintile sorts, entry = close(e+1), "
          f"market-adjusted, {N_Q} buckets ===")
    print("    Registered headline horizons are h=21 and h=42; h=5 and h=63 are "
          "shape context.\n    C (the reaction) is the CONTROL and must "
          "reproduce H2b's null.")
    primary: dict[tuple[str, int], dict] = {}
    for col, label, _ in SIGNALS:
        print(f"\n  --- {label} ---")
        for h in HORIZONS:
            r = run_sort(ev, col, f"fwd{h}", f"mkt{h}", h, n_t, rng)
            primary[(col, h)] = r
            print(fmt(r, f"h={h:>2}"))
            if not r:
                continue
            print("      buckets (bps): " +
                  " ".join(f"{1e4 * m:+7.1f}" for m in r["bucket_means"]) +
                  "   n " + " ".join(f"{k}" for k in r["bucket_n"]))
            print(f"      Q{N_Q}-pool {1e4 * r['excess']:+7.2f} bps  "
                  f"t={r['excess'] / r['se_excess']:+5.2f}   "
                  f"pool {1e4 * r['pool']:+7.2f} bps")
            u = run_sort(ev, col, f"fwd{h}", f"mkt{h}", h, n_t, rng, winsor=0.0)
            print(f"      UNWINSORISED {1e4 * u['spread']:+8.2f} bps "
                  f"t={u['t']:+5.2f}  (the {WINSOR_P:.0%}/{1 - WINSOR_P:.0%} clip "
                  f"is worth {1e4 * (r['spread'] - u['spread']):+.2f} bps)")

    # ------------------------------------------------- the positive control
    print("\n=== POSITIVE CONTROL: do these instruments carry the earnings news "
          "at all? ===")
    print("    Contemporaneous by construction (the reaction spans the same two "
          "sessions the\n    text does) and therefore NOT tradeable. Its only "
          "job is to make a null readable:\n    if tone does not sort the "
          "announcement move, a flat drift says nothing.")
    react = ev["react2_adj"].to_numpy()
    for col, label, _ in SIGNALS[:4]:
        r = primary[(col, 21)]
        lab = r["lab"]
        rr = react[r["idx"]]
        prof = [np.nanmean(rr[lab == k]) if (lab == k).any() else np.nan
                for k in range(N_Q)]
        m5, m1 = lab == N_Q - 1, lab == 0
        diff = np.nanmean(rr[m5]) - np.nanmean(rr[m1])
        se = math.sqrt(np.nanvar(rr[m5], ddof=1) / np.isfinite(rr[m5]).sum()
                       + np.nanvar(rr[m1], ddof=1) / np.isfinite(rr[m1]).sum())
        print(f"  {label:<20} reaction by quintile (bps): " +
              " ".join(f"{1e4 * m:+7.1f}" for m in prof) +
              f"   Q{N_Q}-Q1 {1e4 * diff:+7.1f}  t={diff / se:+6.2f}")
        aprof = [np.nanmean(np.abs(rr[lab == k])) if (lab == k).any() else np.nan
                 for k in range(N_Q)]
        print(f"  {'':<20} |reaction| by quintile (%): " +
              " ".join(f"{100 * m:6.2f}" for m in aprof))
    print("\n    CONTAMINATION SCALE (H16's check, on this panel): tone's "
          f"quintile spread on the\n    CONTEMPORANEOUS reaction is "
          f"{1e4 * (np.nanmean(react[primary[('tone', 21)]['idx']][primary[('tone', 21)]['lab'] == N_Q - 1]) - np.nanmean(react[primary[('tone', 21)]['idx']][primary[('tone', 21)]['lab'] == 0])):+.1f} bps "
          f"against {1e4 * primary[('tone', 21)]['spread']:+.1f} bps on the "
          "FORWARD 21-session\n    return. Entering one session earlier would "
          "have reported the first number as drift.")

    print("\n=== RULE 13: trailing 252-session beta to SPY by quintile ===")
    for col, label, _ in SIGNALS:
        r = primary[(col, 21)]
        bet = ev["beta252"].to_numpy()[r["idx"]]
        print(f"  {label:<20} " +
              " ".join(f"{np.nanmean(bet[r['lab'] == k]):+6.2f}"
                       if (r["lab"] == k).any() else "   nan"
                       for k in range(N_Q)))

    # ------------------------------------------------------------ controls
    print("\n=== CONTROLS (a) random pick and (b) FIRM-LEVEL DATE SHUFFLE ===")
    print("    (b) is the deciding control. It keeps every firm's own set of "
          "tone/attention\n    values and destroys only which announcement each "
          "one belongs to, so a static\n    'which firms get written about "
          "kindly' effect survives it and a timing effect\n    cannot. Rule 14: "
          "each null's SE is printed as a ratio to the block bootstrap's.")
    for col, label, _ in SIGNALS:
        for h in HEADLINE_H + (63,):
            r = primary[(col, h)]
            rp = random_pick_control(r["entry"], r["lab"], r["y"], n_t, h, rng,
                                     n_d=N_Q, reps=CTRL_REPS)
            sh = firm_date_shuffle(r["ticker"], r["sig"], r["entry"], r["y"],
                                   n_t, rng, reps=CTRL_REPS)
            print(f"  {label:<20} h={h:>2}  real {1e4 * r['spread']:+8.2f}  "
                  f"boot SE {1e4 * r['se']:6.2f}")
            print(f"  {'':<20}        random {1e4 * rp.mean():+7.2f} +- "
                  f"{1e4 * rp.std(ddof=1):5.2f} (p={_p(rp, r['spread']):.3f}, "
                  f"SE {rp.std(ddof=1) / r['se']:.2f}x)   "
                  f"date-shuffle {1e4 * sh.mean():+7.2f} +- "
                  f"{1e4 * sh.std(ddof=1):5.2f} (p={_p(sh, r['spread']):.3f}, "
                  f"SE {sh.std(ddof=1) / r['se']:.2f}x)")

    # --------------------------------------------------------- double sort
    print("\n=== THE DECIDING CUT: does the NEWS add anything to the PRICE? ===")
    print("    Tone quintiles inside terciles of the same announcement's price "
          "reaction. If A\n    works where C does not, the tone spread must "
          "survive inside every reaction tercile.")
    for col, label, _ in SIGNALS[:4]:
        rk = ev[[col, "react2_adj"]].dropna()
        print(f"    rank correlation {label} vs reaction: "
              f"{rk[col].rank().corr(rk['react2_adj'].rank()):+.3f}"
              + ("   (SUE vs reaction in H26 was 0.118)" if col == "tone" else ""))
    terc = trailing_deciles(ev["react2_adj"].to_numpy(), ev["entry"].to_numpy(),
                            3, window=COHORT_WINDOW, min_cohort=MIN_COHORT)
    for col, label, _ in SIGNALS[:4]:
        for h in HEADLINE_H:
            cells = []
            for k in range(3):
                r = run_sort(ev[terc == k], col, f"fwd{h}", f"mkt{h}", h, n_t,
                             rng, min_cohort=40)
                cells.append(r.get("spread", np.nan) if r else np.nan)
            print(f"  {label:<20} h={h:>2}  reaction terciles T1/T2/T3: " +
                  " ".join(f"{1e4 * c:+8.2f}" for c in cells))

    # ---------------------------------------------------- H2b reproduction
    print("\n=== CONTROL (c): the H2b cohort test, verbatim ===")
    up = ev[ev["react2"] >= 0.05]
    dn = ev[ev["react2"] <= -0.05]
    print(f"  reaction >= +5%: n={len(up):>5}  avg 42-session end "
          f"{100 * up['fwd42'].mean():+6.2f}%   SPY same windows "
          f"{100 * up['mkt42'].mean():+6.2f}%")
    print(f"  reaction <= -5%: n={len(dn):>5}  avg 42-session end "
          f"{100 * dn['fwd42'].mean():+6.2f}%   SPY same windows "
          f"{100 * dn['mkt42'].mean():+6.2f}%")
    print(f"  difference {100 * (up['fwd42'].mean() - dn['fwd42'].mean()):+6.2f}pp"
          f"   (H2b recorded 'end identically, ~+1.7-2.4% both'; H26d "
          f"reproduced -0.06pp)")

    # ------------------------------------------------------------ placebo
    print("\n=== LATE-WINDOW PLACEBO: sessions +42..+84, same signal ===")
    print("    Drift is a correction and must finish. A spread out here at the "
          "same per-session\n    rate is a firm characteristic, not a "
          "post-announcement correction.")
    for col, label, _ in SIGNALS:
        r = run_sort(ev, col, "fwd_late", "mkt_late", 42, n_t, rng)
        print(fmt(r, f"{label} late"))
        if r:
            print(f"      per-session {1e4 * r['spread'] / 42:+6.2f} bps against "
                  f"the in-window {1e4 * primary[(col, 42)]['spread'] / 42:+6.2f}")

    # ----------------------------------------------------------- variants
    print("\n=== registered variants (every one run is printed, whatever it says) ===")
    print("  -- RAW (not market-adjusted) --")
    for col, label, _ in SIGNALS:
        for h in HEADLINE_H:
            r = run_sort(ev, col, f"fwd{h}", f"mkt{h}", h, n_t, rng, adjust=False)
            print(fmt(r, f"{label} h={h} raw"))
    print("  -- DECILES instead of quintiles --")
    for col, label, _ in SIGNALS:
        for h in HEADLINE_H:
            r = run_sort(ev, col, f"fwd{h}", f"mkt{h}", h, n_t, rng, n_q=10)
            print(fmt(r, f"{label} h={h} D10", n_q=10))
    print(f"  -- excluding events touching a |1-day| > {EXTREME_1D:.0%} move --")
    sub = ev[~ev["defect"]]
    for col, label, _ in SIGNALS:
        for h in HEADLINE_H:
            r = run_sort(sub, col, f"fwd{h}", f"mkt{h}", h, n_t, rng)
            print(fmt(r, f"{label} h={h} clean"))
    print("  -- tone split by session: e alone (the release) vs e+1 alone "
          "(the reaction) --")
    print("     Tone at e+1 is the most contaminated by the price move it is "
          "being compared\n     against - a headline written after the bell "
          "often just reports the move. Tone at\n     e alone is the cleanest "
          "text-only read for a firm that released before the open.")
    F = ds["frames"]
    ncol = {s: j for j, s in enumerate(F["all"]["n"].columns)}
    jn = ev["ticker"].map(ncol).to_numpy()
    for tag, off in (("tone0", 0), ("tone1", 1)):
        idx = ev["e"].to_numpy() + off
        for kind, suf in (("all", ""), ("specific", "_spec")):
            p = F[kind]["pos"].to_numpy()[idx, jn]
            g = F[kind]["neg"].to_numpy()[idx, jn]
            n1 = F[kind]["n"].to_numpy()[idx, jn]
            ev[tag + suf] = np.where(n1 > 0, (p - g) / (p + g + 1.0), np.nan)
    for tag, when in (("tone0", "e  "), ("tone1", "e+1")):
        for suf, kind in (("", "all "), ("_spec", "spec")):
            for h in HEADLINE_H:
                r = run_sort(ev, tag + suf, f"fwd{h}", f"mkt{h}", h, n_t, rng)
                print(fmt(r, f"tone({when}) {kind} h={h}"))
    print("  -- liquidity terciles (20d median $ volume at e), h=21 and h=42 --")
    d = ev[np.isfinite(ev["dvol20"])].copy()
    d["ltile"] = trailing_deciles(d["dvol20"].to_numpy(), d["entry"].to_numpy(),
                                  3, window=COHORT_WINDOW, min_cohort=MIN_COHORT)
    for col, label, _ in SIGNALS[:4]:
        for h in HEADLINE_H:
            cells = [run_sort(d[d["ltile"] == k], col, f"fwd{h}", f"mkt{h}", h,
                              n_t, rng, min_cohort=40) for k in range(3)]
            print(f"  {label:<20} h={h:>2}  LOW/MID/HIGH: " +
                  " ".join(f"{1e4 * c['spread']:+8.2f}" if c else "     n/a"
                           for c in cells))

    # -------------------------------------------------------------- costs
    print("\n=== cost arithmetic (10 bps round trip, charged per leg) ===")
    print(f"  {'signal':<20} {'h':>3} {'Q5-Q1':>9} {'break-even':>11} "
          f"{'net':>9}   {'Q5-pool':>9} {'break-even':>11} {'net':>9} {'ann.net':>8}")
    for col, label, _ in SIGNALS:
        for h in HEADLINE_H:
            r = primary[(col, h)]
            sp, ex = 1e4 * r["spread"], 1e4 * r["excess"]
            print(f"  {label:<20} {h:>3} {sp:>+9.2f} {sp / 2:>11.1f} "
                  f"{sp - 2 * COST_BPS:>+9.2f}   {ex:>+9.2f} {ex:>11.1f} "
                  f"{ex - COST_BPS:>+9.2f} "
                  f"{(ex - COST_BPS) * (252 / h) / 100:>+7.2f}%")

    # --------------------------------------------- effective sample (Rule 16)
    print("\n=== effective independent sample (Rule 16: never quote an n_eff "
          "from a daily series) ===")
    span = n_t
    for h in HORIZONS:
        r = primary[("tone", h)]
        print(f"  h={h:>2}  {int(r['n_pool']):>5,} ranked events on "
              f"{r['n_sess']:,} distinct entry sessions inside a {span:,}-session "
              f"calendar\n        -> {span / h:>5.0f} non-overlapping "
              f"{h}-session windows; {ev['ticker'].nunique()} firms")
    print(f"\ndone in {time.time() - t0:.0f}s")


def _p(null: np.ndarray, real: float) -> float:
    """One-sided p in the direction of the observed effect - so it is never
    flattered by the sign the sample happened to produce."""
    return float((null >= real).mean() if real >= 0 else (null <= real).mean())


# --------------------------------------------------------------------------
# offline self-test: the leakage checks, no API keys needed
# --------------------------------------------------------------------------

def selftest() -> None:
    ok, checks = 0, 0

    def check(name, cond):
        nonlocal ok, checks
        checks += 1
        ok += bool(cond)
        print(f"  [{'ok ' if cond else 'FAIL'}] {name}")

    print("selftest: entry alignment, ranking causality, controls, bootstrap")

    # 1. ENTRY ALIGNMENT on a synthetic frame where every price is known.
    #    close(t) = 100 + t, so any misalignment shows up as an exact integer.
    idx = pd.DatetimeIndex(pd.bdate_range("2018-01-01", periods=600))
    cl = pd.DataFrame({"A": 100.0 + np.arange(600), "SPY": 300.0 + np.arange(600)},
                      index=idx)
    vol = pd.DataFrame(1e7, index=idx, columns=["A", "SPY"])
    zero = pd.DataFrame(0.0, index=idx, columns=["A"])
    ds = {"sessions": idx, "close": cl, "volume": vol,
          "frames": {k: {"pos": zero.copy(), "neg": zero.copy(), "n": zero.copy()}
                     for k in ("all", "specific")}}
    ev0 = pd.DataFrame({"ticker": ["A"], "ann": [idx[300]]})
    got = attach(ev0, ds, horizons=(5,), verbose=False)
    e = int(got["e"].iloc[0])
    check("event session e is the 8-K date itself when it is a session", e == 300)
    check("entry index is e+1", int(got["entry"].iloc[0]) == 301)
    check("fwd5 = close(e+6)/close(e+1) - 1",
          abs(got["fwd5"].iloc[0] - (cl["A"].iloc[306] / cl["A"].iloc[301] - 1)) < 1e-12)
    check("react2 = close(e+1)/close(e-1) - 1",
          abs(got["react2"].iloc[0] - (cl["A"].iloc[301] / cl["A"].iloc[299] - 1)) < 1e-12)

    # 2. THE LOOKAHEAD PROOF. Plant a news frame whose tone at session e+1 IS
    #    the sign of the return the market will earn from close(e+1) onward.
    #    Read correctly that is a real (planted) signal; the point of the check
    #    is the mirror: a frame that only knows returns EARNED BEFORE entry must
    #    score nothing forward. Both directions are asserted.
    rng = np.random.default_rng(11)
    n_t, n_f = 900, 120
    steps = rng.normal(0, 0.01, size=(n_t, n_f))
    px = pd.DataFrame(100 * np.exp(np.cumsum(steps, axis=0)),
                      index=pd.DatetimeIndex(pd.bdate_range("2016-01-04", periods=n_t)),
                      columns=[f"F{i}" for i in range(n_f)])
    px["SPY"] = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, n_t)))
    sess = pd.DatetimeIndex(px.index)
    anns = []
    for i in range(n_f):
        for q in range(4, n_t - 200, 63):
            anns.append((f"F{i}", sess[q]))
    ev_s = pd.DataFrame(anns, columns=["ticker", "ann"])
    for name, use_future in (("future-return tone", True), ("past-return tone", False)):
        pos = pd.DataFrame(0.0, index=sess, columns=px.columns[:-1])
        neg = pos.copy()
        one = pos + 1.0
        e_idx = np.searchsorted(sess.to_numpy(), ev_s["ann"].to_numpy())
        jj = [list(px.columns).index(t) for t in ev_s["ticker"]]
        fut = (px.to_numpy()[np.minimum(e_idx + 22, n_t - 1), jj]
               / px.to_numpy()[e_idx + 1, jj] - 1.0)
        past = (px.to_numpy()[e_idx, jj] / px.to_numpy()[np.maximum(e_idx - 21, 0), jj]
                - 1.0)
        src = fut if use_future else past
        # continuous word counts, so the planted tone spans a real cross-section
        # (a binary +-1 tone has no quintiles to form: the trailing breakpoints
        # all land on the same two values and three buckets come back empty)
        for k, (tk, ei) in enumerate(zip(ev_s["ticker"], e_idx)):
            c = pos.columns.get_loc(tk)
            pos.iloc[ei + 1, c] = 200.0 * max(src[k], 0.0)
            neg.iloc[ei + 1, c] = 200.0 * max(-src[k], 0.0)
        dss = {"sessions": sess, "close": px,
               "volume": pd.DataFrame(1e7, index=sess, columns=px.columns),
               "frames": {k: {"pos": pos, "neg": neg, "n": one}
                          for k in ("all", "specific")}}
        evx = attach(ev_s.copy(), dss, horizons=(21,), verbose=False)
        r = run_sort(evx, "tone", "fwd21", "mkt21", 21, n_t,
                     np.random.default_rng(3), min_cohort=100)
        sp = 1e4 * r["spread"]
        if use_future:
            check(f"{name}: planted forward signal IS recovered ({sp:+.0f} bps)",
                  sp > 200)
        else:
            check(f"{name}: past-only signal scores ~0 forward ({sp:+.0f} bps)",
                  abs(sp) < 120)

    # 3. the trailing quantile labeller cannot see its own session or later.
    entry = np.repeat(np.arange(0, 900, 5), 30)
    sig = np.random.default_rng(5).normal(size=len(entry))
    lab = trailing_deciles(sig, entry, N_Q, window=COHORT_WINDOW,
                           min_cohort=MIN_COHORT)
    bad = sig.copy()
    bad[entry >= 400] += 50.0
    lab2 = trailing_deciles(bad, entry, N_Q, window=COHORT_WINDOW,
                            min_cohort=MIN_COHORT)
    past = entry < 400
    check("quantile labels do not move when FUTURE signal values change",
          (lab[past] == lab2[past]).all())
    check("the first session is unrankable (no prior cohort)",
          (lab[entry == entry.min()] == -1).all())

    # 4. the date shuffle kills an EVENT-timed effect and spares a FIRM effect.
    n_t2, n_f2 = 900, 200
    tick = np.repeat([f"F{i}" for i in range(n_f2)], 12)
    ent = np.tile(np.arange(12) * 63 + 90, n_f2)
    s = np.random.default_rng(7).normal(size=len(tick))
    firm = np.repeat(np.random.default_rng(8).normal(size=n_f2), 12)
    for name, sg, y, must_die in (
            ("event-timed", s, 0.02 * s + 0.01 * np.random.default_rng(9).normal(size=len(s)), True),
            ("firm characteristic", firm, 0.02 * firm + 0.01 * np.random.default_rng(10).normal(size=len(s)), False)):
        lab = trailing_deciles(sg, ent, N_Q, window=COHORT_WINDOW,
                              min_cohort=MIN_COHORT)
        a, b, _ = _stat(session_sums(ent, lab, y, n_t2, N_Q - 1, 0).sum(axis=0))
        real = a - b
        sh = firm_date_shuffle(tick, sg, ent, y, n_t2,
                               np.random.default_rng(12), reps=25)
        if must_die:
            check(f"date shuffle destroys an {name} effect "
                  f"({1e4 * sh.mean():+.0f} vs {1e4 * real:+.0f} bps)",
                  abs(sh.mean()) < 0.2 * abs(real))
        else:
            check(f"date shuffle SPARES a {name} "
                  f"({1e4 * sh.mean():+.0f} vs {1e4 * real:+.0f} bps)",
                  abs(sh.mean()) > 0.5 * abs(real))

    # 5. the block bootstrap widens on autocorrelated data.
    x = np.zeros(1200)
    g = np.random.default_rng(13)
    for i in range(1, 1200):
        x[i] = 0.9 * x[i - 1] + g.normal()
    M = np.column_stack([x, np.ones(1200), np.zeros(1200), np.ones(1200),
                         x, np.ones(1200)])
    b1 = block_boot(M, 1, 400, np.random.default_rng(2))["se"]
    b42 = block_boot(M, 42, 400, np.random.default_rng(2))["se"]
    check(f"block bootstrap absorbs autocorrelation ({b42:.2f} vs {b1:.2f})",
          b42 > 1.5 * b1)

    print(f"selftest: {ok}/{checks} checks passed")
    if ok != checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
