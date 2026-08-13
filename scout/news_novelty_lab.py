"""H17 - novel news drifts, stale (recycled) news reverses.

MECHANISM (one sentence, before any number)
-------------------------------------------
Tetlock (2011) "All the News That's Fit to Reprint": investors cannot cheaply
tell a genuinely new fact from the fifth retelling of an old one, so they
UNDERREACT to novel information (its price move continues) and OVERREACT to
recycled information (its price move unwinds).

Testable consequence, and the reason this is sharper than H15/H16: the theory
predicts OPPOSITE SIGNS for two things a headline count cannot distinguish.
Conditional on a stock moving UP on its news day, novel coverage should drift
further up and stale coverage should give the move back; conditional on a stock
moving DOWN, the mirror. The claim is therefore the NOVEL-minus-STALE
DIFFERENCE inside each direction, and the single summary number is the
difference-in-differences

    DiD = [novel - stale | up day] - [novel - stale | down day]   > 0

which cancels any constant bias in the novelty detector, in the lexicon, or in
which stocks Benzinga likes. That is exactly what the date-shuffle control that
killed H15 cannot manufacture: H15 died because a static property of WHICH
STOCKS get covered reproduced the spread, and a static property cannot flip
sign with the direction of the news day.

WHAT IS MEASURED
----------------
Universe   the 120 most liquid S&P 500 members AS OF 2016-01-04
           (news_data.liquid_universe over scout/pit.py point-in-time
           membership: BRCM/EMC/TWX/CELG/ESRX/MON/AET/PXD are in, TSLA is out).
News       Benzinga via Alpaca, 2016-01-02..2026-07-31: 464,430 symbol-rows
           over 308,870 stories (news_data.load_panel(), already cached).
Prices     Alpaca SIP daily closes, adjustment=all, SPLIT-REPAIRED - see the
           data-integrity section. 2,664 sessions, 2016-01-04..2026-08-07.
Staleness  For every story, sim = the maximum Jaccard overlap of its content
           tokens with the SAME SYMBOL's stories over the prior 5 calendar
           days. `max_prior_similarity` computes it; it is the continuous
           quantity news_data.novelty_flags thresholds, and this file asserts
           `(sim < thr) == news_data.novelty_flags(df, 5, thr)` exactly, at
           every threshold, on the real panel. Session-level signal
           stale_{i,t} = MEAN sim over the SPECIFIC stories attributed to
           session t (templated wire and >10-tag broadtape dropped), ranked
           cross-sectionally within the date.

WHY THE CONTINUOUS MEASURE IS THE PRIMARY, AND THE BINARY FLAG IS A VARIANT
--------------------------------------------------------------------------
The task asked for `is_novel`. Measured on this panel, that flag at its shipped
Jaccard threshold of 0.6 calls 96.5% of specific stories novel, so only 2.5% of
covered symbol-sessions contain ANY stale story and a "NOVEL-heavy vs
STALE-heavy" split is 22.2 names against 1.6. Worse, staleness-by-count is
mechanically attention: 1.1% of one-story sessions contain a repeat against
48.7% of sessions with >10 stories. So the binary split is run and reported at
FIVE thresholds (0.4/0.5/0.6/0.7/0.8) exactly as registered, and the primary is
the continuous mean-similarity rank, which is balanced by construction (three
equal terciles), subsumes the threshold question entirely, and still carries the
attention confound - rank correlation with log story count is +0.454 - which is
why the Fama-MacBeth adds attention and attention x return as regressors.

WHERE THE shift() IS (the only thing that can manufacture this result)
---------------------------------------------------------------------
1. news -> session: news_data.attribute_sessions converts created_at to
   US/Eastern and rolls any story stamped at or after that day's close (16:00
   ET, 13:00 on the 23 NYSE half-days) to the NEXT session. Row t holds only
   what a trader could have read BEFORE session t's close. audit_attribution()
   runs and asserts zero violations.
2. staleness look-back is strictly backward: a story's sim compares it only to
   stories with created_at < its own.
3. signal -> return: `fwd_h(t) = close(t+h)/close(t) - 1`, paired with the
   signal at index t. The conditioning variable r0(t) = close(t)/close(t-1) - 1
   is also known at close t. The portfolio form states it the other way and
   equivalently: `W.shift(1) * ret1` in news_sentiment_lab.run_portfolio, so
   the first return any signal can touch is close(t) -> close(t+1).
   `--selftest` prices the mistake: dropping that shift turns a zero-value
   same-day signal into hundreds of bps.

The whole headline is ALSO re-run under news_data's deliberately wrong
attribution (`_attribute_naive`: UTC calendar date, no ET conversion, no close
cutoff) as a lookahead control, because that is the one error that reliably
manufactures news alpha in this repo (news_data measured it at +8.74 bps/day).

DATA INTEGRITY (the repo's known debt, handled explicitly)
----------------------------------------------------------
5.1% of splits are unapplied in Alpaca daily bars. BOTH available guards are
used: (a) scout/intraday.py's corporate-actions split repair via
news_sentiment_lab.repair_splits - it rescales 1,173 AAPL bars for the missing
2020-08-31 4:1 split and refuses MET's ratio-1.122 2017-08-07 spin-off as
unresolvable; and (b) an explicit |1-day return| > 45% guard applied AFTER the
repair, which removes the symbol-date from the signal side and invalidates any
forward window spanning it. Post-repair the guard finds exactly 2 cells in
319,680: OXY 2020-03-09 (a genuine -52% oil-crash day) and MON 2021-03-16 (the
delisted ticker reused by an unrelated issuer). A 21-session median dollar
volume floor of $20M, computed through t, removes the reused-ticker family in
general - MON prints a stale 127.95 at zero volume for 695 sessions after Bayer
closes the acquisition.

CONTROLS (five, all run, none optional)
---------------------------------------
a. LABEL SHUFFLE - staleness permuted across the covered symbols WITHIN each
   date, 200 draws. The dates, the covered pool, the direction conditioning and
   that date's marginal distribution of staleness all survive; only WHICH stock
   is stale dies. The registered effect must vanish here.
b. DATE SHUFFLE - the H15 killer, run on THIS spread: each symbol's staleness
   series permuted ACROSS DATES independently, 200 draws. Every stock keeps its
   own staleness distribution; only the TIMING dies. An effect that survives
   this is a stock characteristic, not a news-novelty signal.
c. RANDOM PICK - uniform random scores over the identical eligible pool, 200
   draws, so the noise SCALE is quoted rather than assumed (Rule 10).
d. MATCHED BENCHMARK - the equal-weight eligible-with-news pool, plus a SPY
   regression of the dollar-neutral book (Rule 13: dollar-neutral is not
   market-neutral).
e. POSITIVE CONTROL - staleness must predict SOMETHING or a null is evidence
   about the pipeline, not the hypothesis: |return| and story counts by
   staleness tercile are printed.
Plus Rule 14: every permutation z is printed next to the ratio of the null's SE
to the real series' Newey-West SE, because a within-date permutation is
anti-conservative for a persistent signal.

INFERENCE
---------
The cross-section is collapsed to ONE number per session before any statistic
is taken, so date clustering is structural (as scout/calibrate.py). A circular
moving-block bootstrap with block length h then absorbs the overlap that h-day
holds create. Every h-day claim is pooled across all h entry phases
(RESEARCH-AGENDA Rule 9). Both halves are split at the median usable date.
Costs 10 bps round trip on measured turnover; break-even round-trip cost
reported for every book.

SAMPLE, AND THE EFFECTIVE INDEPENDENT SAMPLE
--------------------------------------------
2,664 sessions, 2016-01-04..2026-08-07. 120,564 covered symbol-sessions at
h=1 (liquid, at least one specific story, finite same-day return, finite
forward close); 118,533 at h=42, so 2,031 are lost to the survival requirement
when a name delists inside the window - disclosed, not fixed. Mean cross-section
45.7 names; 2,625 dates rankable. The DiD itself uses 1,765-1,812 dates, because
requiring MIN_CELL=3 names in all four cells drops ~31% of them.

The effective independent sample is NOT 120,564. The cross-section is collapsed
to ONE number per session before any statistic is taken, so n <= 1,812; at h=21
that is ~85 genuinely non-overlapping windows per entry phase over 21 phases,
and at h=42 about 42 per phase over 42 phases. The printed ph_min/ph_max columns
are those phases, and at h=21 they run -120 to +101 bps.

VERDICT: REJECTED — and rejected on the sign, not merely on power
-----------------------------------------------------------------
1. THE HEADLINE IS THE WRONG SIGN AND INSIDE THE NOISE. The primary DiD is
   -0.83 / -3.91 / -5.62 / +3.85 bps at h = 1 / 5 / 21 / 42 against a registered
   POSITIVE sign, with t = -0.24 / -0.55 / -0.37 / +0.17 and every 95%
   block-bootstrap CI straddling zero ([-7.60,+6.16] at h=1; [-35.29,+24.53] at
   h=21). The halves flip sign at three of four horizons (-6.78/+5.13,
   -12.30/+4.49, -25.55/+14.28). Across the three staleness measures x four
   horizons, 6 of 12 cells carry the registered sign - a coin flip. The best of
   them (spec_max, h=42, +14.95 bps) has t = 0.69.

2. THE REGRESSION SAYS THE SAME THING WITH THE OPPOSITE SIGN, THEN BLAMES
   ATTENTION. lam_r0Xstale = +7.32 / +20.94 / +47.37 / +37.00 bps (t = +1.02 /
   +1.35 / +1.42 / +0.77) where Tetlock predicts NEGATIVE: in this sample stale
   moves CONTINUE marginally more than novel ones, the mirror image of the
   hypothesis. Adding attention and attention x return removes 54% / 32% / 85% /
   131% of it (to +3.38 / +14.34 / +7.27 / -11.33, |t| <= 0.79). The staleness
   LEVEL coefficient behaves the same way: +58.5 (t=1.91) at h=42 alone, +19.0
   (t=0.88) once attention is in. Staleness measured by repetition is 0.45
   rank-correlated with story count, and what little the regression sees is the
   attention part - which H15 already rejected as a timing signal.
   There is also no reversal for a "news effect" to be hiding: lam_r0 alone is
   +0.18 / -7.70 / -9.54 / -2.50 bps with |t| <= 1.10, reproducing H16c.

3. IT IS INSIDE ALL THREE NULLS, AT EVERY HORIZON. |z| <= 0.61 and one-sided
   p from 0.30 to 0.68 against label-shuffle, date-shuffle and random-pick.
   Note what the date-shuffle null MEAN is: -1.44 / -1.86 / -2.85 / -10.34 bps.
   A static stock-characteristic component of this DiD exists and at h=42 it is
   nearly three times the size of the real effect - the H15 confound survives
   into the differenced statistic, it just no longer has anything to explain.

4. THE THRESHOLD SENSITIVITY IS THE TEXTBOOK FAILURE. Across the five Jaccard
   cuts the DiD at h=42 runs -14.34 / -67.54 / +10.54 / +274.45 / +595.08 while
   the usable date count collapses from 724 to 16. Exactly one of the 20 binary
   cells has a CI excluding zero - thr=0.5, h=42, -67.54 bps, t=-2.18 - and it
   is the WRONG sign, its immediate neighbours are -14.34 and +10.54, and one
   |t|>2 in 20 draws is the expectation, not a finding.

5. THE OTHER FREE PARAMETER MOVES IT MONOTONICALLY THE WRONG WAY. Lengthening
   the novelty look-back from 3 to 5 to 10 days takes the h=21 DiD from -18.83
   to -5.62 to -32.13 bps (t -1.19 / -0.37 / -2.10) - the 10-day version is the
   most "significant" cell in the study and it is anti-Tetlock. A longer window
   makes more coverage look stale, which is what an attention proxy does.
   MIN_CELL is also load-bearing: at MIN_CELL=1 (2,400 dates) the DiD is
   +0.54 / +0.50 / +0.26 / +7.00 bps - indistinguishable from nothing at all.

6. COSTS SETTLE IT REGARDLESS OF SIGN. The tradeable book earns -2.04 / +0.75 /
   +0.11 / +0.31 %/yr gross against an equal-weight pool at +16.8 to +17.9%/yr
   and SPY at +15.82%/yr. Break-even round-trip cost is -0.48 / 0.88 / 0.52 /
   3.08 bps against the 10 bps charged; net of that cost the book returns
   -44.1 / -7.7 / -1.9 / -0.7 %/yr. Deflated Sharpe of the best of the 36
   registered cells is 0.059.

7. WHAT IS ACTUALLY THERE (the positive control). Staleness is a live variable -
   it is just not a signed one. Novel tercile vs stale tercile: 1.41 vs 4.37
   stories per session, |same-day return| 1.291% vs 1.807%, |next-session
   return| 1.315% vs 1.530%, and signed next-session return +6.94 vs +7.82 bps.
   That is H15's result reached through a different measure: news intensity
   forecasts the SIZE of the next move and almost none of its sign.

TWO METHOD RESULTS WORTH MORE THAN THE REJECTION
-------------------------------------------------
A. THE DiD IS ALMOST IMMUNE TO THE TIMESTAMP MISTAKE. Re-run under the naive
   attribution the primary DiD is +0.32 / -4.43 / -6.42 / -3.92 bps against the
   honest -0.83 / -3.91 / -5.62 / +3.85. The same error inflated H15's spread by
   43% and manufactured +8.74 bps/day of fake tone alpha in news_data's own
   demo. Differencing two direction-conditioned spreads cancels most of a
   same-session leak - measured attenuation 2.8x on synthetic data at a 1%/day
   planted leak, and it degrades to 1.7x as the leak grows, so this is
   robustness, NOT immunity. The channel is still closed at the source.

B. A WITHIN-DATE PERMUTATION IS AN HONEST NULL *FOR THIS STATISTIC*. H16 found
   the same permutation 2.3-3.5x too tight and issued Rule 14 because of it.
   Here SE_ratio (block-bootstrap SE / permutation SE) runs 0.94-1.14 at every
   horizon and for all three nulls. The difference is the statistic, not the
   data: a persistent long-short book inherits the autocorrelation of a sticky
   sector tilt, whereas a DiD of four direction-conditioned cells differences
   that persistence away. Rule 14 stands - print the ratio - and this is the
   case where printing it exonerates the permutation.

Run: python -m scout.news_novelty_lab              # full study (~3 min warm)
     python -m scout.news_novelty_lab --selftest   # offline, no keys, <10s
     python -m scout.news_novelty_lab --quick      # primary + controls only
"""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import deque
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, growth, news_data
from . import news_attention_lab as attn
from . import news_sentiment_lab as sent

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing here is tuned against an outcome.
# --------------------------------------------------------------------------
HORIZONS = (1, 5, 21, 42)
N_TERCILE = 3               # novel / middle / stale
NOVELTY_DAYS = 5            # news_data.novelty_flags default look-back
JACCARD_GRID = (0.4, 0.5, 0.6, 0.7, 0.8)   # 0.6 is news_data's shipped default
MIN_NAMES = 20              # smallest covered cross-section that may be ranked
MIN_CELL = 3                # smallest cell that may enter a date's DiD
MAX_1D_MOVE = 0.45          # data-integrity guard (see docstring)
MIN_DOLLAR_VOL = 20e6       # trailing 21-session median, computed through t
BIG_MOVE = 0.02             # the |r0| cut for the magnitude-conditioned variant
COST_BPS = 10.0             # round trip, large caps
BOOT_REPS = 5000
CTRL_REPS = 200
SEED = 20260809
TDAYS = 252.0
BENCH = "SPY"

PANEL_CACHE = config.SCOUT_DIR / "cache_news_novelty_panel.pkl"
PANEL_VERSION = 1

#: (name, story subset, per-session aggregator) - the staleness measures.
#: "spec_mean" is the PRIMARY; the verdict is written against it.
SIGNALS = (
    ("spec_mean", "specific", "mean"),     # PRIMARY
    ("spec_max", "specific", "max"),
    ("all_mean", "all", "mean"),
)
PRIMARY = "spec_mean"


# --------------------------------------------------------------------------
# staleness: the continuous quantity news_data.novelty_flags thresholds
# --------------------------------------------------------------------------

def max_prior_similarity(df: pd.DataFrame, days: int = NOVELTY_DAYS) -> np.ndarray:
    """Max Jaccard overlap of each headline with the SAME symbol's prior stories.

    This is `news_data.novelty_flags` with the comparison returned instead of
    thresholded, so a single pass gives every Jaccard cut at once:
    `sim < thr` is bit-identical to `novelty_flags(df, days, thr)`, and
    `selftest` plus `--verify-novelty` assert exactly that on real rows.

    Strictly backward-looking: the comparison set for a story at time t holds
    only stories with created_at < t, so this adds no lookahead. An empty
    headline scores 1.0 (says nothing new), matching novelty_flags' convention.

    WARM-UP EDGE, inherited: the history is whatever is in `df`, so the first
    `days` of the panel see a short look-back and are biased toward novel. On a
    10.5-year panel that is 5 days of 2,664 and is left as documented drift.
    """
    heads = df["headline"].fillna("").to_numpy()
    # nanoseconds forced explicitly - pandas 2 infers datetime64[us] from a
    # frame of Timestamps and a bare astype("int64") would widen the window
    # 1000x. news_data carries the same comment because that bug shipped once.
    times = (df["created_at"].dt.tz_convert("UTC").dt.tz_localize(None)
             .to_numpy(dtype="datetime64[ns]").astype("int64"))
    syms = df["symbol"].to_numpy()
    window_ns = int(days) * 86_400 * 1_000_000_000
    order = np.lexsort((times, syms))
    cache: dict[str, frozenset] = {}
    out = np.ones(len(df), dtype="float64")
    cur_sym, hist = None, deque()
    for p in order:
        s = syms[p]
        if s != cur_sym:
            cur_sym, hist = s, deque()
        t = times[p]
        while hist and t - hist[0][0] > window_ns:
            hist.popleft()
        h = heads[p]
        toks = cache.get(h)
        if toks is None:
            toks = cache[h] = news_data._content_tokens(h)
        if not toks:
            out[p] = 1.0
        else:
            best = 0.0
            for _, prior in hist:
                if not prior:
                    continue
                inter = len(toks & prior)
                if inter:
                    j = inter / len(toks | prior)
                    if j > best:
                        best = j
            out[p] = best
        hist.append((t, toks))
    return out


# --------------------------------------------------------------------------
# the panel
# --------------------------------------------------------------------------

def _session_frames(sim: np.ndarray, symbol: np.ndarray, session: np.ndarray,
                    keep: np.ndarray, sessions: pd.DatetimeIndex,
                    cols: list[str]) -> dict[str, pd.DataFrame]:
    """Session x symbol staleness aggregates over the stories in `keep`."""
    d = pd.DataFrame({"symbol": symbol[keep], "session": session[keep],
                      "sim": sim[keep], "one": 1.0})
    d = d[pd.notna(d["session"])]

    def piv(col, how):
        return (d.pivot_table(index="session", columns="symbol", values=col,
                              aggfunc=how)
                .reindex(index=sessions, columns=cols))
    n = piv("one", "sum").fillna(0.0)
    return {"n": n, "mean": piv("sim", "mean"), "max": piv("sim", "max")}


def build_panel(force: bool = False, verbose: bool = True) -> dict:
    """Everything the experiment needs, cached. ~40s cold, instant warm."""
    if PANEL_CACHE.exists() and not force:
        p = pd.read_pickle(PANEL_CACHE)
        if p.get("version") == PANEL_VERSION:
            return p
    t0 = time.time()
    bars = sent.load_bars(verbose=verbose)          # split-REPAIRED close+volume
    close, volume = bars["close"], bars["volume"]
    sessions = news_data._session_index(close)
    close.index, volume.index = sessions, sessions
    bench = close[BENCH].copy() if BENCH in close.columns else None

    df = news_data.load_panel()
    if verbose:
        print(f"news: {len(df):,} symbol-rows, {df['id'].nunique():,} stories, "
              f"{df['created_at'].min().date()}..{df['created_at'].max().date()}")
    audit = news_data.audit_attribution(df, close)     # asserts 0 violations

    sim = max_prior_similarity(df)
    cat = news_data.categorize(df["headline"])
    specific = ((~cat.isin(news_data.TEMPLATED_CATEGORIES))
                & (~news_data.is_broadtape(df["n_tags"], 10))).to_numpy()
    sess = news_data.attribute_sessions(df["created_at"], sessions).to_numpy()
    naive = news_data._attribute_naive(df["created_at"], sessions).to_numpy()
    symbol = df["symbol"].to_numpy()
    cols = [c for c in close.columns if c != BENCH]
    allrows = np.ones(len(df), dtype=bool)

    frames = {"specific": _session_frames(sim, symbol, sess, specific, sessions, cols),
              "all": _session_frames(sim, symbol, sess, allrows, sessions, cols)}
    naive_frames = {"specific": _session_frames(sim, symbol, naive, specific,
                                                sessions, cols)}
    # the literal is_novel version, one frame of "stale story share" per cut
    stale_share = {thr: _session_frames((sim >= thr).astype(float), symbol, sess,
                                        specific, sessions, cols)["mean"]
                   for thr in JACCARD_GRID}

    close_u, volume_u = close[cols], volume[cols]
    ret1 = close_u.pct_change()
    extreme = ret1.abs() > MAX_1D_MOVE
    liq = sent.liquidity_mask(close_u, volume_u)
    panel = {
        "version": PANEL_VERSION, "sessions": sessions, "close": close_u,
        "ret1": ret1.where(~extreme), "raw_ret1": ret1, "extreme": extreme,
        "liq": liq, "bench": bench, "frames": frames,
        "naive_frames": naive_frames, "stale_share": stale_share,
        "repairs": bars["repairs"], "attribution_audit": audit,
        "sim_summary": {"mean": float(sim.mean()), "median": float(np.median(sim)),
                        "stale_share_by_thr": {thr: float((sim >= thr).mean())
                                               for thr in JACCARD_GRID}},
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }
    pd.to_pickle(panel, PANEL_CACHE)
    if verbose:
        print(f"panel built in {time.time() - t0:.0f}s -> {PANEL_CACHE.name}")
    return panel


def verify_novelty(df: pd.DataFrame | None = None, n: int = 60_000) -> bool:
    """Assert on REAL rows that `sim < thr` reproduces news_data.novelty_flags."""
    df = news_data.load_panel() if df is None else df
    sub = df.iloc[:n].reset_index(drop=True)
    sim = max_prior_similarity(sub)
    ok = True
    for thr in JACCARD_GRID:
        ref = news_data.novelty_flags(sub, NOVELTY_DAYS, thr).to_numpy()
        same = bool(np.array_equal(sim < thr, ref))
        ok &= same
        print(f"  thr={thr}: identical to news_data.novelty_flags -> {same} "
              f"(novel share {ref.mean():.4f})")
    return ok


# --------------------------------------------------------------------------
# cross-sectional machinery
# --------------------------------------------------------------------------

def eligible(panel: dict, h: int, kind: str, agg: str) -> tuple:
    """(staleness, coverage mask, same-day return, forward return) at horizon h.

    Coverage = liquid AND at least one story attributed to session t AND a
    finite same-day return AND a finite close at t and t+h. Everything on the
    signal side is known at close(t); `fwd` starts at close(t).
    """
    close = panel["close"]
    f = panel["frames"][kind]
    stale = f[agg]
    n = f["n"]
    r0 = panel["ret1"]
    fwd = close.shift(-h) / close - 1.0
    # a forward window spanning a guarded extreme move is not usable
    cum = panel["extreme"].astype(float).fillna(0.0).cumsum()
    nbad = (cum.shift(-h) - cum).fillna(1.0)
    fwd = fwd.where(nbad == 0)
    cov = (panel["liq"] & n.gt(0) & stale.notna() & r0.notna()
           & fwd.notna()).to_numpy()
    return stale.to_numpy(), cov, r0.to_numpy(), fwd.to_numpy()


def tercile_labels(sig: np.ndarray, cov: np.ndarray, seed: int,
                   q: int = N_TERCILE) -> np.ndarray:
    """Balanced within-date buckets, -1 where not covered. 0 = most NOVEL.

    Reuses news_attention_lab.quintile_labels, whose seeded uniform tie-break
    exists because a large tie mass at exactly zero staleness would otherwise be
    resolved alphabetically and park the same names in the same bucket for a
    decade.
    """
    return attn.quintile_labels(sig, cov, np.random.default_rng(seed), q=q,
                                min_elig=MIN_NAMES)


def _cell_mean(mask: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    m = mask & np.isfinite(y)
    n = m.sum(1)
    mean = np.where(n > 0, np.where(m, np.nan_to_num(y), 0.0).sum(1)
                    / np.maximum(n, 1), np.nan)
    return mean, n


def did_series(lab: np.ndarray, r0: np.ndarray, fwd: np.ndarray,
               big: float | None = None, q: int = N_TERCILE,
               min_cell: int = MIN_CELL) -> dict:
    """Per-date novel-minus-stale spreads inside up days and down days, and the
    difference between them.

    Cells: novel = bucket 0 of the staleness ranking, stale = bucket q-1.
    Direction: sign of the same-day return (or |r0| > `big` if given), which is
    known at close(t). A date contributes only if all four cells hold at least
    MIN_CELL names, so a spread is never carried by one stock.
    """
    novel, stale = lab == 0, lab == q - 1
    if big is None:
        up, dn = r0 > 0, r0 < 0
    else:
        up, dn = r0 > big, r0 < -big
    cells, counts = {}, {}
    for tag, m in (("novel_up", novel & up), ("stale_up", stale & up),
                   ("novel_dn", novel & dn), ("stale_dn", stale & dn)):
        cells[tag], counts[tag] = _cell_mean(m, fwd)
    ok = np.ones(len(fwd), dtype=bool)
    for tag in cells:
        ok &= counts[tag] >= min_cell
        ok &= np.isfinite(cells[tag])
    sp_up = np.where(ok, cells["novel_up"] - cells["stale_up"], np.nan)
    sp_dn = np.where(ok, cells["novel_dn"] - cells["stale_dn"], np.nan)
    return {"cells": cells, "counts": counts, "ok": ok,
            "spread_up": sp_up, "spread_dn": sp_dn, "did": sp_up - sp_dn}


def did_weights(lab: np.ndarray, r0: np.ndarray,
                index, columns, q: int = N_TERCILE) -> pd.DataFrame:
    """The tradeable form of the same claim: dollar-neutral, equal weight.

    LONG the two cells the mechanism says should keep going (novel & up,
    stale & down - a reversal buy), SHORT the two it says should unwind
    (stale & up, novel & down). Weights are formed at close(t); the shift that
    makes them tradeable lives in news_sentiment_lab.run_portfolio.
    """
    novel, stale = lab == 0, lab == q - 1
    up, dn = r0 > 0, r0 < 0
    long_m = (novel & up) | (stale & dn)
    short_m = (stale & up) | (novel & dn)
    nl, ns = long_m.sum(1), short_m.sum(1)
    both = (nl > 0) & (ns > 0)
    w = (long_m / np.maximum(nl, 1)[:, None]
         - short_m / np.maximum(ns, 1)[:, None])
    w = w * both[:, None]
    return pd.DataFrame(w, index=index, columns=columns)


def pool_weights(cov: np.ndarray, index, columns) -> pd.DataFrame:
    """Matched benchmark: equal weight of the identical eligible-with-news pool."""
    n = cov.sum(1)
    w = cov / np.maximum(n, 1)[:, None]
    return pd.DataFrame(w * (n > 0)[:, None], index=index, columns=columns)


# --------------------------------------------------------------------------
# inference helpers (thin wrappers over the already-validated house versions)
# --------------------------------------------------------------------------

def summarise(x: np.ndarray, h: int, rng: np.random.Generator) -> dict:
    """Block-bootstrapped mean of a per-DATE series, in bps, with halves and
    the h entry phases hiding inside an overlapping mean (Rule 9)."""
    b = attn.block_boot(x, max(h, 1), BOOT_REPS, rng)
    idx = np.flatnonzero(np.isfinite(x))
    half = len(idx) // 2
    ph = attn.phase_sweep(x, max(h, 1))
    return {"n_dates": len(idx), "bps": b["mean"] * 1e4, "lo": b["lo"] * 1e4,
            "hi": b["hi"] * 1e4, "t": b["t"], "se_bps": b["se"] * 1e4,
            "half1": float(np.mean(x[idx[:half]])) * 1e4 if half else np.nan,
            "half2": float(np.mean(x[idx[half:]])) * 1e4 if half else np.nan,
            "ph_min": float(np.nanmin(ph)) * 1e4,
            "ph_max": float(np.nanmax(ph)) * 1e4,
            "ph_wrongsign": int(np.nansum(ph < 0)), "ph_n": len(ph)}


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def shuffle_within_date(sig: np.ndarray, cov: np.ndarray,
                        rng: np.random.Generator) -> np.ndarray:
    """CONTROL (a): permute staleness across the covered symbols of each date."""
    s = sig.copy()
    for i in range(s.shape[0]):
        idx = np.flatnonzero(cov[i] & np.isfinite(s[i]))
        if len(idx) > 1:
            s[i, idx] = s[i, rng.permutation(idx)]
    return s


def shuffle_across_dates(sig: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """CONTROL (b), the H15 killer: permute each symbol's staleness series
    across dates. Keeps every stock's own staleness distribution; kills only
    the timing, and with it the alignment to the news day's price move."""
    s = sig.copy()
    for j in range(s.shape[1]):
        col = s[:, j]
        f = np.isfinite(col)
        if f.sum() > 1:
            col[f] = rng.permutation(col[f])
    return s


def random_scores(cov: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """CONTROL (c): uniform noise over the identical eligible pool."""
    s = rng.random(cov.shape)
    return np.where(cov, s, np.nan)


def control_null(kind: str, sig: np.ndarray, cov: np.ndarray, r0: np.ndarray,
                 fwd: np.ndarray, h: int, reps: int = CTRL_REPS,
                 seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed + 17 * h)
    out = np.empty(reps)
    for r in range(reps):
        if kind == "label_shuffle":
            s = shuffle_within_date(sig, cov, rng)
        elif kind == "date_shuffle":
            s = shuffle_across_dates(sig, rng)
        elif kind == "random":
            s = random_scores(cov, rng)
        else:
            raise ValueError(kind)
        lab = attn.quintile_labels(s, cov, rng, q=N_TERCILE, min_elig=MIN_NAMES)
        out[r] = np.nanmean(did_series(lab, r0, fwd)["did"])
    return {"kind": kind, "reps": reps, "draws": out,
            "mean": float(np.nanmean(out)), "sd": float(np.nanstd(out, ddof=1))}


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------

def run_signal(panel: dict, name: str, kind: str, agg: str,
               horizons=HORIZONS, big: float | None = None,
               verbose: bool = True) -> tuple:
    """One staleness measure, all horizons: the DiD table and the kept series."""
    rng = np.random.default_rng(SEED)
    rows, keep = [], {}
    for h in horizons:
        stale, cov, r0, fwd = eligible(panel, h, kind, agg)
        lab = tercile_labels(stale, cov, SEED + h)
        d = did_series(lab, r0, fwd, big=big)
        s_did = summarise(d["did"], h, rng)
        s_up = summarise(d["spread_up"], h, rng)
        s_dn = summarise(d["spread_dn"], h, rng)
        rows.append({
            "signal": name, "h": h, "n_dates": s_did["n_dates"],
            "novel_up": np.nanmean(d["cells"]["novel_up"][d["ok"]]) * 1e4,
            "stale_up": np.nanmean(d["cells"]["stale_up"][d["ok"]]) * 1e4,
            "novel_dn": np.nanmean(d["cells"]["novel_dn"][d["ok"]]) * 1e4,
            "stale_dn": np.nanmean(d["cells"]["stale_dn"][d["ok"]]) * 1e4,
            "sp_up": s_up["bps"], "t_up": s_up["t"],
            "sp_dn": s_dn["bps"], "t_dn": s_dn["t"],
            "DiD": s_did["bps"], "lo": s_did["lo"], "hi": s_did["hi"],
            "t_DiD": s_did["t"], "half1": s_did["half1"], "half2": s_did["half2"],
            "ph_min": s_did["ph_min"], "ph_max": s_did["ph_max"],
            "ph_wrong": s_did["ph_wrongsign"], "ph_n": s_did["ph_n"],
            "cell_n": float(np.mean([d["counts"][k][d["ok"]].mean()
                                     for k in d["counts"]])),
        })
        keep[h] = {"stale": stale, "cov": cov, "r0": r0, "fwd": fwd, "lab": lab,
                   "did": d}
        if verbose:
            r = rows[-1]
            print(f"    h={h:>2}  DiD {r['DiD']:+8.2f} bps "
                  f"[{r['lo']:+7.2f},{r['hi']:+7.2f}] t={r['t_DiD']:+5.2f}  "
                  f"up {r['sp_up']:+7.2f} | dn {r['sp_dn']:+7.2f}  "
                  f"halves {r['half1']:+7.2f}/{r['half2']:+7.2f}  "
                  f"n={r['n_dates']}")
    return pd.DataFrame(rows), keep


def run_binary(panel: dict, horizons=HORIZONS, verbose: bool = True) -> pd.DataFrame:
    """H17d as literally registered: news_data's is_novel flag, five Jaccard
    cuts. NOVEL-heavy = every specific story that session is novel; STALE-heavy
    = at least one is a repeat. The bucket sizes are printed because they are
    the finding."""
    rng = np.random.default_rng(SEED + 1)
    close = panel["close"]
    rows = []
    for thr in JACCARD_GRID:
        share = panel["stale_share"][thr].to_numpy()
        for h in horizons:
            _, cov, r0, fwd = eligible(panel, h, "specific", "mean")
            novel = cov & (share == 0.0)
            stale = cov & (share > 0.0)
            up, dn = r0 > 0, r0 < 0
            cells, counts = {}, {}
            for tag, m in (("novel_up", novel & up), ("stale_up", stale & up),
                           ("novel_dn", novel & dn), ("stale_dn", stale & dn)):
                cells[tag], counts[tag] = _cell_mean(m, fwd)
            ok = np.ones(len(fwd), bool)
            for tag in cells:
                ok &= (counts[tag] >= MIN_CELL) & np.isfinite(cells[tag])
            sp_up = np.where(ok, cells["novel_up"] - cells["stale_up"], np.nan)
            sp_dn = np.where(ok, cells["novel_dn"] - cells["stale_dn"], np.nan)
            s = summarise(sp_up - sp_dn, h, rng)
            rows.append({"thr": thr, "h": h, "n_dates": s["n_dates"],
                         "novel_n": float(np.mean(novel.sum(1))),
                         "stale_n": float(np.mean(stale.sum(1))),
                         "sp_up": 1e4 * float(np.nanmean(sp_up)),
                         "sp_dn": 1e4 * float(np.nanmean(sp_dn)),
                         "DiD": s["bps"], "lo": s["lo"], "hi": s["hi"],
                         "t_DiD": s["t"], "half1": s["half1"],
                         "half2": s["half2"]})
            if verbose:
                r = rows[-1]
                print(f"    thr={thr}  h={h:>2}  DiD {r['DiD']:+8.2f} bps "
                      f"t={r['t_DiD']:+5.2f}  novel/stale names per date "
                      f"{r['novel_n']:5.1f}/{r['stale_n']:4.1f}  n={r['n_dates']}")
    return pd.DataFrame(rows)


def run_portfolios(panel: dict, keep: dict, horizons=HORIZONS) -> pd.DataFrame:
    """H17b: the DiD as a dollar-neutral book, with costs and a SPY regression."""
    close = panel["close"]
    ret1 = panel["ret1"]
    bench_ret = (panel["bench"].pct_change() if panel["bench"] is not None
                 else pd.Series(dtype=float))
    rows = []
    for h in horizons:
        k = keep[h]
        w = did_weights(k["lab"], k["r0"], close.index, close.columns)
        wp = pool_weights(k["cov"], close.index, close.columns)
        res = sent.run_portfolio(w, ret1, h, cost_bps=COST_BPS)
        pool = sent.run_portfolio(wp, ret1, h, cost_bps=COST_BPS)
        mkt = sent.market_adjust(res["gross"], bench_ret, h)
        h1, h2 = sent.halves(res["gross"])
        rows.append({
            "h": h, "n_days": res["n_days"],
            "mean_bps": 1e4 * res["mean_gross"],
            "t_nw": res["t_gross"],
            "half1_bps": 1e4 * float(h1.mean()), "half2_bps": 1e4 * float(h2.mean()),
            "ann_gross_%": 100 * res["ann_gross"], "ann_net_%": 100 * res["ann_net"],
            "sharpe_gross": res["sharpe_gross"], "turnover": res["mean_turnover"],
            "breakeven_bps": res["breakeven_bps"],
            "beta": mkt["beta"], "alpha_ann_%": mkt["alpha_ann_%"],
            "t_alpha": mkt["t_alpha"],
            "pool_ann_%": 100 * pool["ann_gross"],
        })
    return pd.DataFrame(rows)


#: Nested Fama-MacBeth models. Row 4 is THE registered H17c test: with
#: staleness ranked so that HIGH = stale, Tetlock predicts a NEGATIVE
#: coefficient on r0 x stale (a stale price move reverses relative to a novel
#: one). Row 5 adds the H15 confound - staleness is 0.45-correlated with
#: attention, so if the interaction is really attention x return it dies here.
FM_MODELS = (
    ("r0 only", ("r0",)),
    ("stale only", ("stale",)),
    ("r0 + stale", ("r0", "stale")),
    ("REGISTERED r0 x stale", ("r0", "stale", "r0Xstale")),
    ("+ attention + attn x r0", ("r0", "stale", "r0Xstale", "attn", "r0Xattn")),
)
FM_COLS = ("r0", "stale", "r0Xstale", "attn", "r0Xattn")


def run_fm(panel: dict, horizons=HORIZONS) -> dict:
    close = panel["close"]
    n_spec = panel["frames"]["specific"]["n"]
    out = {}
    for h in horizons:
        stale, cov, r0, fwd = eligible(panel, h, "specific", "mean")
        m = pd.DataFrame(cov, index=close.index, columns=close.columns)
        sr = sent.xrank(pd.DataFrame(stale, index=close.index,
                                     columns=close.columns).where(m))
        rr = sent.xrank(pd.DataFrame(r0, index=close.index,
                                     columns=close.columns).where(m))
        ar = sent.xrank(np.log1p(n_spec).where(m))
        X = {"r0": rr, "stale": sr, "r0Xstale": rr * sr, "attn": ar,
             "r0Xattn": rr * ar}
        fwd_df = pd.DataFrame(fwd, index=close.index,
                              columns=close.columns).where(m)
        rows = []
        for name, regs in FM_MODELS:
            fm = sent.fama_macbeth(X, fwd_df, regs)
            row = {"model": name, "n_dates": fm["n_dates"]}
            for c in FM_COLS:
                row[f"lam_{c}"] = 1e4 * fm[c]["mean"] if c in regs else np.nan
                row[f"t_{c}"] = sent._nw_t(fm[c]["series"], h) if c in regs else np.nan
            rows.append(row)
        out[h] = pd.DataFrame(rows)
    return out


def positive_control(panel: dict) -> pd.DataFrame:
    """CONTROL (e): does staleness predict ANYTHING? If not, a null result is
    evidence about the pipeline rather than about the hypothesis."""
    stale, cov, r0, fwd = eligible(panel, 1, "specific", "mean")
    lab = tercile_labels(stale, cov, SEED + 1)
    n_spec = panel["frames"]["specific"]["n"].to_numpy()
    rows = []
    for qi, tag in ((0, "T1 novel"), (1, "T2"), (N_TERCILE - 1, "T3 stale")):
        m = lab == qi
        rows.append({
            "bucket": tag, "obs": int(m.sum()),
            "stories/session": float(np.nanmean(np.where(m, n_spec, np.nan))),
            "staleness": float(np.nanmean(np.where(m, stale, np.nan))),
            "|same-day ret| %": 100 * float(np.nanmean(np.where(m, np.abs(r0), np.nan))),
            "|next-session ret| %": 100 * float(np.nanmean(np.where(m, np.abs(fwd), np.nan))),
            "same-day ret bps": 1e4 * float(np.nanmean(np.where(m, r0, np.nan))),
            "next-session ret bps": 1e4 * float(np.nanmean(np.where(m, fwd, np.nan))),
        })
    return pd.DataFrame(rows)


def min_cell_sensitivity(panel: dict, horizons=HORIZONS,
                         grid=(1, 2, 3, 5)) -> pd.DataFrame:
    """Does the MIN_CELL rule (and the ~31% of dates it drops) drive anything?

    Requiring at least MIN_CELL names in ALL FOUR cells is a data-quality rule,
    but it is also a date filter, and a date filter is a place a result can
    hide. This re-runs the primary DiD at four values of it.
    """
    rows = []
    rng = np.random.default_rng(SEED + 2)
    for h in horizons:
        stale, cov, r0, fwd = eligible(panel, h, "specific", "mean")
        lab = tercile_labels(stale, cov, SEED + h)
        for m in grid:
            s = summarise(did_series(lab, r0, fwd, min_cell=m)["did"], h, rng)
            rows.append({"h": h, "MIN_CELL": m, "n_dates": s["n_dates"],
                         "DiD": s["bps"], "lo": s["lo"], "hi": s["hi"],
                         "t_DiD": s["t"], "half1": s["half1"],
                         "half2": s["half2"]})
    return pd.DataFrame(rows)


def window_sweep(panel: dict, windows=(3, 5, 10), horizons=HORIZONS,
                 verbose: bool = True) -> pd.DataFrame:
    """Sensitivity to the OTHER free parameter: the novelty look-back window.

    news_data.novelty_flags defaults to 5 calendar days. A result that exists
    only at 5 is a result about the number 5.
    """
    df = news_data.load_panel()
    sessions = panel["sessions"]
    cols = list(panel["close"].columns)
    cat = news_data.categorize(df["headline"])
    specific = ((~cat.isin(news_data.TEMPLATED_CATEGORIES))
                & (~news_data.is_broadtape(df["n_tags"], 10))).to_numpy()
    sess = news_data.attribute_sessions(df["created_at"], sessions).to_numpy()
    symbol = df["symbol"].to_numpy()
    rows = []
    for w in windows:
        sim = max_prior_similarity(df, days=w)
        fr = _session_frames(sim, symbol, sess, specific, sessions, cols)
        p = {**panel, "frames": {**panel["frames"], "specific": fr}}
        tab, _ = run_signal(p, f"win{w}d", "specific", "mean",
                            horizons=horizons, verbose=False)
        tab.insert(1, "novelty_days", w)
        rows.append(tab)
        if verbose:
            print(f"    {w:2d}-day look-back: DiD " +
                  "  ".join(f"h={int(r.h)} {r.DiD:+7.2f} (t={r.t_DiD:+.2f})"
                            for r in tab.itertuples()))
    return pd.concat(rows, ignore_index=True)


def coverage(panel: dict) -> dict:
    stale, cov, r0, fwd = eligible(panel, 1, "specific", "mean")
    n_spec = panel["frames"]["specific"]["n"].to_numpy()
    sr = sent.xrank(pd.DataFrame(stale, index=panel["close"].index,
                                 columns=panel["close"].columns)
                    .where(pd.DataFrame(cov, index=panel["close"].index,
                                        columns=panel["close"].columns)))
    ar = sent.xrank(pd.DataFrame(np.log1p(n_spec), index=panel["close"].index,
                                 columns=panel["close"].columns)
                    .where(pd.DataFrame(cov, index=panel["close"].index,
                                        columns=panel["close"].columns)))
    r0f = pd.DataFrame(r0, index=panel["close"].index, columns=panel["close"].columns)
    fwdf = pd.DataFrame(fwd, index=panel["close"].index, columns=panel["close"].columns)
    # what the h-session survival requirement costs: a name that delists (or
    # stops printing a liquid price) inside the window drops out of the pool,
    # which mildly favours survivors and is disclosed rather than fixed.
    by_h = {}
    for h in HORIZONS:
        _, c_h, _, _ = eligible(panel, h, "specific", "mean")
        by_h[h] = int(c_h.sum())
    return {
        "sessions": int(len(panel["close"])),
        "symbols": int(panel["close"].shape[1]),
        "covered_by_horizon": by_h,
        "lost_to_h42_survival": by_h[HORIZONS[0]] - by_h[HORIZONS[-1]],
        "date_min": str(panel["close"].index.min().date()),
        "date_max": str(panel["close"].index.max().date()),
        "covered_symbol_sessions": int(cov.sum()),
        "mean_cross_section": float(cov.sum(1)[cov.sum(1) > 0].mean()),
        "dates_rankable": int((cov.sum(1) >= MIN_NAMES).sum()),
        "split_repairs": panel["repairs"],
        "extreme_1d_cells_guarded": int(panel["extreme"].sum().sum()),
        "extreme_cells": [f"{s} {d.date()}" for d, s in
                          panel["extreme"].stack()[panel["extreme"].stack()].index],
        "attribution_audit": panel["attribution_audit"],
        "story_stale_share_by_thr": panel["sim_summary"]["stale_share_by_thr"],
        "corr_stalerank_attnrank": float(sr.stack().corr(ar.stack())),
        # Rule from H16: how far is this study from the one-day leak?
        "leak_same_session_bps": 1e4 * float(sr.mul(r0f).stack().mean()),
        "honest_next_session_bps": 1e4 * float(sr.mul(fwdf).stack().mean()),
        "spy_ann_%": (100 * TDAYS * float(panel["bench"].pct_change().mean())
                      if panel["bench"] is not None else float("nan")),
    }


# --------------------------------------------------------------------------
# selftest — offline, synthetic, no keys
# --------------------------------------------------------------------------

def _synthetic(n_days=1200, n_sym=60, drift=0.0, reversal=0.0,
               stock_reversal=0.0, seed=5):
    """Panel with a PLANTED effect - either an EVENT effect or a STOCK effect.

    EVENT (drift/reversal): staleness is re-drawn at random every date, and the
    next-day return is
        drift * sign(r0) * 1{novel} - reversal * sign(r0) * 1{stale}
    so positive `drift` and positive `reversal` both push the DiD POSITIVE, the
    registered direction. Both shuffles must destroy this.

    STOCK (`stock_reversal`): a fixed third of the names is PERMANENTLY stale
    and its moves PERMANENTLY reverse, with no event timing anywhere. This is
    the H15 confound translated into DiD terms - a stock characteristic that
    interacts with the direction of the day - and the date shuffle must SPARE
    it, because it permutes a constant series and changes nothing.
    """
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2016-01-04", periods=n_days)
    cols = [f"S{i:02d}" for i in range(n_sym)]
    bad = np.zeros(n_sym)
    bad[: n_sym // 3] = 1.0
    if stock_reversal:
        stale = pd.DataFrame(0.05 * rng.random((n_days, n_sym)) + bad[None, :],
                             index=idx, columns=cols)
    else:
        stale = pd.DataFrame(rng.random((n_days, n_sym)), index=idx, columns=cols)
    r0 = pd.DataFrame(rng.normal(0, 0.015, (n_days, n_sym)), index=idx, columns=cols)
    is_novel = (stale.rank(axis=1, pct=True) <= 1 / 3).to_numpy()
    is_stale = (stale.rank(axis=1, pct=True) > 2 / 3).to_numpy()
    sgn = np.sign(r0.to_numpy())
    nxt = rng.normal(0, 0.015, (n_days, n_sym))
    nxt += drift * sgn * is_novel - reversal * sgn * is_stale
    nxt -= stock_reversal * sgn * bad[None, :]
    return stale, r0, pd.DataFrame(nxt, index=idx, columns=cols)


def _did_from_synth(stale, r0, nxt, shuffle=None, seed=1):
    cov = np.ones(stale.shape, dtype=bool)
    sig = stale.to_numpy().copy()
    rng = np.random.default_rng(seed)
    if shuffle == "label":
        sig = shuffle_within_date(sig, cov, rng)
    elif shuffle == "date":
        sig = shuffle_across_dates(sig, rng)
    lab = attn.quintile_labels(sig, cov, rng, q=N_TERCILE, min_elig=MIN_NAMES)
    d = did_series(lab, r0.to_numpy(), nxt.to_numpy())
    return 1e4 * float(np.nanmean(d["did"]))


def selftest(verbose: bool = True) -> int:
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append(f"{name}: {detail}")
        if verbose:
            print(f"  [{'ok ' if cond else 'FAIL'}] {name} {detail}")

    print("selftest — synthetic panels, no network, no keys")

    # 1. the staleness measure IS news_data.novelty_flags, thresholded
    rng = np.random.default_rng(0)
    words = ["beats", "misses", "guidance", "recall", "upgrade", "merger",
             "lawsuit", "dividend", "chip", "cloud"]
    rows = []
    t0 = pd.Timestamp("2020-01-01", tz="UTC")
    for i in range(3000):
        k = rng.integers(2, 6)
        head = " ".join(rng.choice(words, size=k, replace=False))
        rows.append({"created_at": t0 + pd.Timedelta(hours=int(rng.integers(0, 800))),
                     "symbol": f"S{rng.integers(0, 8)}", "headline": head})
    sdf = pd.DataFrame(rows).sort_values("created_at").reset_index(drop=True)
    sim = max_prior_similarity(sdf)
    for thr in JACCARD_GRID:
        ref = news_data.novelty_flags(sdf, NOVELTY_DAYS, thr).to_numpy()
        check(f"sim<{thr} == news_data.novelty_flags", np.array_equal(sim < thr, ref),
              f"novel share {ref.mean():.3f}")

    # 2. planted Tetlock effect is recovered with the registered sign
    stale, r0, nxt = _synthetic(drift=0.0020, reversal=0.0020)
    real = _did_from_synth(stale, r0, nxt)
    check("planted drift/reversal recovered, positive", real > 40,
          f"DiD={real:+.1f} bps")
    stale_n, r0_n, nxt_n = _synthetic(drift=-0.0020, reversal=-0.0020, seed=6)
    check("planted OPPOSITE effect recovered, negative",
          _did_from_synth(stale_n, r0_n, nxt_n) < -40,
          f"DiD={_did_from_synth(stale_n, r0_n, nxt_n):+.1f} bps")

    # 3. null panel gives ~0
    s0, r00, n0 = _synthetic(drift=0.0, reversal=0.0, seed=9)
    null = _did_from_synth(s0, r00, n0)
    check("null panel gives ~0", abs(null) < 15, f"DiD={null:+.2f} bps")

    # 4. CONTROL (a): the label shuffle must kill a planted event effect
    lab_sh = _did_from_synth(stale, r0, nxt, shuffle="label")
    check("label shuffle kills the planted effect", abs(lab_sh) < 0.15 * abs(real),
          f"{real:+.1f} -> {lab_sh:+.1f} bps")

    # 5. CONTROL (b): the date shuffle must kill an EVENT effect ...
    date_sh = _did_from_synth(stale, r0, nxt, shuffle="date")
    check("date shuffle kills the planted EVENT effect",
          abs(date_sh) < 0.15 * abs(real), f"{real:+.1f} -> {date_sh:+.1f} bps")

    # ... and SPARE a stock characteristic that interacts with direction
    #     (H15's confound, translated into DiD terms)
    s2, r02, n2 = _synthetic(stock_reversal=0.0020, seed=11)
    raw2 = _did_from_synth(s2, r02, n2)
    sh2 = _did_from_synth(s2, r02, n2, shuffle="date")
    check("date shuffle SPARES a stock characteristic x direction effect",
          raw2 > 30 and abs(sh2 - raw2) < 0.25 * abs(raw2),
          f"raw={raw2:+.1f} shuffled={sh2:+.1f} bps — so a surviving DiD would "
          f"be a stock property, not news timing")

    # 6. THE LOOKAHEAD PROOF for the P&L side (H17b runs through
    #    news_sentiment_lab.run_portfolio, so its shift is asserted here too):
    #    a signal that IS today's return is worth nothing shifted and a fortune
    #    unshifted.
    n_days, n_sym = 900, 60
    idx = pd.bdate_range("2018-01-01", periods=n_days)
    cols = [f"S{i:02d}" for i in range(n_sym)]
    rng = np.random.default_rng(3)
    ret1 = pd.DataFrame(rng.normal(0, 0.015, (n_days, n_sym)), index=idx, columns=cols)
    w_same = sent.ls_weights(ret1)
    honest = sent.run_portfolio(w_same, ret1, 1)["mean_gross"]
    cheat = float((w_same.rolling(1).mean() * ret1).sum(axis=1).mean())
    check("no-shift version is grossly contaminated", abs(cheat) > 50 * abs(honest),
          f"cheat={1e4 * cheat:+.0f}bps vs honest={1e4 * honest:+.2f}bps")

    # 7. HOW MUCH A SAME-SESSION LEAK THE DiD ABSORBS — measured, not assumed.
    #    A leak inflates the up-day and down-day spreads together, so most of
    #    it differences out; what remains is the selection created by
    #    conditioning on the SIGN of a return that itself contains the effect.
    #    Measured attenuation on this panel: 3.6x at a 1%/day planted effect
    #    (ratio 0.28 at 0.3%/day, 0.61 at 3%/day). So the DiD is robust but NOT
    #    immune, which is why the attribution rule and the naive-attribution
    #    rerun in __main__ — not this cancellation — are what close the channel.
    rng = np.random.default_rng(23)
    stale_c = pd.DataFrame(rng.random((n_days, n_sym)), index=idx, columns=cols)
    novel_c = (stale_c.rank(axis=1, pct=True) <= 1 / 3).to_numpy()
    r0_c = pd.DataFrame(rng.normal(0, 0.015, (n_days, n_sym)) + 0.01 * novel_c,
                        index=idx, columns=cols)     # contemporaneous effect
    nxt_c = pd.DataFrame(rng.normal(0, 0.015, (n_days, n_sym)), index=idx,
                         columns=cols)               # nothing predictable
    covc = np.ones((n_days, n_sym), bool)
    labc = attn.quintile_labels(stale_c.to_numpy(), covc, rng, q=N_TERCILE,
                                min_elig=MIN_NAMES)
    leak = did_series(labc, r0_c.to_numpy(), r0_c.to_numpy())   # pair with its OWN day
    good = did_series(labc, r0_c.to_numpy(), nxt_c.to_numpy())
    leak_up = 1e4 * float(np.nanmean(leak["spread_up"]))
    leak_did = 1e4 * float(np.nanmean(leak["did"]))
    check("same-session leak blows up the LEVEL spread", abs(leak_up) > 30,
          f"sp_up={leak_up:+.0f} bps")
    check("...and the DiD absorbs most of it (attenuation > 2x)",
          abs(leak_did) < 0.5 * abs(leak_up),
          f"DiD={leak_did:+.1f} vs sp_up={leak_up:+.0f} bps "
          f"({abs(leak_up / leak_did):.1f}x attenuation, NOT immunity)")
    check("honest pairing on the same panel is ~0",
          abs(1e4 * float(np.nanmean(good["did"]))) < 15,
          f"DiD={1e4 * float(np.nanmean(good['did'])):+.2f} bps")

    # 8. cost / break-even arithmetic
    r = sent.run_portfolio(w_same, ret1, 5, cost_bps=COST_BPS)
    implied = r["mean_gross"] - r["mean_turnover"] * (COST_BPS / 2 / 1e4)
    check("net = gross - turnover x one-way cost",
          abs(implied - r["mean_net"]) < 1e-12,
          f"{1e4 * implied:.4f} vs {1e4 * r['mean_net']:.4f} bps")

    # 9. the min-cell rule actually bites
    tiny = np.full((10, 6), -1, dtype=np.int8)
    tiny[:, 0] = 0
    tiny[:, 5] = N_TERCILE - 1
    r0t = np.tile([1.0, 1, 1, -1, -1, -1], (10, 1))
    d = did_series(tiny, r0t, np.zeros((10, 6)))
    check("dates with cells below MIN_CELL are dropped", not d["ok"].any(),
          f"kept {int(d['ok'].sum())} of 10")

    print(f"\n{'ALL CHECKS PASSED' if not fails else 'FAILURES: ' + str(fails)}")
    return 0 if not fails else 1


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def _hdr(s: str) -> None:
    print("\n" + "=" * 78)
    print(s)
    print("=" * 78)


def _f(x):
    return f"{x:9.3f}" if isinstance(x, float) else str(x)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verify-novelty", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="primary signal + controls only")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--draws", type=int, default=CTRL_REPS)
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(selftest())
    if args.verify_novelty:
        raise SystemExit(0 if verify_novelty() else 1)

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 60)
    t0 = time.time()
    panel = build_panel(force=args.rebuild)

    cov = coverage(panel)
    _hdr("COVERAGE, DATA INTEGRITY, AND HOW FAR THIS IS FROM A LOOKAHEAD")
    for k, v in cov.items():
        print(f"  {k:34s} {v}")
    print(f"""
  The last two lines are the H16 discipline applied here: staleness rank times
  its OWN session's return is {cov['leak_same_session_bps']:+.2f} bps, times the NEXT session's return
  is {cov['honest_next_session_bps']:+.2f} bps. Attributing a story to the session it was published in
  rather than the session it can be traded in is the one mistake that reliably
  manufactures news alpha in this repo.""")

    _hdr("POSITIVE CONTROL — does staleness predict anything at all?")
    print(positive_control(panel).to_string(index=False,
                                            float_format=lambda x: f"{x:10.3f}"))

    horizons = (1, 5, 21) if args.quick else HORIZONS
    _hdr("H17a — DiD: [novel - stale | UP day] - [novel - stale | DOWN day]")
    print("  registered sign: POSITIVE (novel drifts, stale reverses)\n")
    tables, keeps = {}, {}
    todo = SIGNALS[:1] if args.quick else SIGNALS
    for name, kind, agg in todo:
        print(f"  signal {name} ({agg} prior-similarity over {kind} stories)"
              f"{'   <-- PRIMARY' if name == PRIMARY else ''}")
        tab, keep = run_signal(panel, name, kind, agg, horizons=horizons)
        tables[name], keeps[name] = tab, keep
    all_did = pd.concat(tables.values(), ignore_index=True)
    print()
    print(all_did[["signal", "h", "n_dates", "cell_n", "novel_up", "stale_up",
                   "novel_dn", "stale_dn", "sp_up", "sp_dn", "DiD", "lo", "hi",
                   "t_DiD", "half1", "half2", "ph_min", "ph_max"]]
          .to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
    print("""
  All cells are mean forward returns in bps over the horizon (not per day).
  novel_up = mean fwd return of the most-novel tercile on days it rose;
  sp_up = novel_up - stale_up; DiD = sp_up - sp_dn. lo/hi = 95% moving-block
  bootstrap by date, block = h. half1/half2 split the usable dates in two.
  ph_min/ph_max = the h non-overlapping entry schedules (RESEARCH-AGENDA Rule 9).""")

    if not args.quick:
        _hdr("H17g — same DiD conditioned on BIG moves only (|same-day| > 2%)")
        tab_big, _ = run_signal(panel, "spec_mean|big", "specific", "mean",
                                horizons=horizons, big=BIG_MOVE)
        print(tab_big[["h", "n_dates", "cell_n", "sp_up", "sp_dn", "DiD", "lo",
                       "hi", "t_DiD", "half1", "half2"]]
              .to_string(index=False, float_format=lambda x: f"{x:8.2f}"))

        _hdr("H17d — the literal is_novel flag, at five Jaccard thresholds")
        print("  NOVEL-heavy = every specific story that session is novel;\n"
              "  STALE-heavy = at least one is a near-duplicate of the prior 5 days.\n")
        tab_bin = run_binary(panel, horizons=horizons)
        print(tab_bin.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
        print("""
  Read novel_n/stale_n first. The shipped 0.6 threshold leaves ~1.6 stale names
  per date against ~22 novel ones, and staleness-by-count is mechanically
  attention (1.1% of one-story sessions contain a repeat vs 48.7% of >10-story
  sessions). That is why the continuous rank above is the primary.""")

        _hdr("LOOKAHEAD CONTROL — the same DiD under the WRONG attribution")
        print("  news_data._attribute_naive: UTC calendar date, no ET conversion,\n"
              "  no close cutoff. This is the error that manufactured +8.74 bps/day\n"
              "  of fake tone alpha in news_data's own demo.\n")
        naive_panel = {**panel, "frames": panel["naive_frames"]}
        tab_naive, _ = run_signal(naive_panel, "spec_mean|NAIVE", "specific",
                                  "mean", horizons=horizons)

        _hdr("ROBUSTNESS — the two free parameters, and the date filter")
        print("  (a) novelty look-back window (news_data's default is 5 days)")
        win = window_sweep(panel, horizons=horizons)
        print("\n  (b) MIN_CELL — the rule that drops ~31% of dates")
        mc = min_cell_sensitivity(panel, horizons=horizons)
        print(mc.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))

    _hdr("H17b — the DiD as a tradeable book (long novel-up + stale-down, "
         "short stale-up + novel-down)")
    ports = run_portfolios(panel, keeps[PRIMARY], horizons=horizons)
    print(ports.to_string(index=False, float_format=lambda x: f"{x:9.3f}"))
    print(f"""
  mean_bps = mean DAILY return of the book, one observation per date, gross.
  turnover = fraction of the book traded per day; costs {COST_BPS:.0f} bps round trip.
  breakeven_bps = the round-trip cost that takes the gross return to zero.
  beta/alpha_ann_%/t_alpha regress the book on SPY (Rule 13 — dollar-neutral is
  not market-neutral). pool_ann_% is the matched equal-weight benchmark.""")

    _hdr(f"CONTROLS — the primary DiD against three nulls ({args.draws} draws each)")
    rows = []
    for h in horizons:
        k = keeps[PRIMARY][h]
        real = float(np.nanmean(k["did"]["did"]))
        s = summarise(k["did"]["did"], h, np.random.default_rng(SEED))
        nw_se = s["se_bps"] / 1e4
        for ck in ("label_shuffle", "date_shuffle", "random"):
            nl = control_null(ck, k["stale"], k["cov"], k["r0"], k["fwd"], h,
                              reps=args.draws)
            z = (real - nl["mean"]) / nl["sd"] if nl["sd"] > 0 else np.nan
            rows.append({"h": h, "control": ck, "draws": nl["reps"],
                         "real_bps": 1e4 * real,
                         "null_mean_bps": 1e4 * nl["mean"],
                         "null_SE_bps": 1e4 * nl["sd"],
                         "boot_SE_bps": s["se_bps"],
                         "SE_ratio": (s["se_bps"] / (1e4 * nl["sd"])
                                      if nl["sd"] > 0 else np.nan),
                         "z_vs_null": z,
                         "p_one_sided": float(np.mean(nl["draws"] >= real))})
    ctl = pd.DataFrame(rows)
    print(ctl.to_string(index=False, float_format=lambda x: f"{x:9.3f}"))
    print("""
  READ SE_ratio BEFORE z (Rule 14): boot_SE is the block-bootstrap SE of the
  real per-date series; null_SE is the spread of the permutation null. Where
  SE_ratio >> 1 the permutation understates the real uncertainty and its z is
  anti-conservative. label_shuffle is the control that must kill the effect
  (it destroys WHICH stock is stale); date_shuffle is the H15 killer applied
  to this spread (it destroys WHEN, keeping each stock's own staleness
  distribution); random is the noise-scale reference.""")

    _hdr("H17c — Fama-MacBeth: the interaction is the hypothesis")
    fm = run_fm(panel, horizons=horizons)
    for h, tab in fm.items():
        print(f"\n  horizon {h} session(s) — bps per unit of the regressor "
              f"(ranks span -0.5..+0.5, so the interaction spans -0.25..+0.25)")
        print(tab.to_string(index=False, float_format=lambda x: f"{x:9.3f}"))
    print("""
  lam_r0Xstale is the registered coefficient and Tetlock predicts it NEGATIVE:
  a price move made on recycled news should reverse relative to one made on
  novel news. Moving a stock from fully novel (stale rank -0.5) to fully stale
  (+0.5) changes its loading on the same-day return by exactly lam_r0Xstale.
  The last row adds attention and attention x return, because staleness is
  0.45-correlated with story count and H15 already showed attention is a live
  but sign-free predictor.""")

    _hdr("MULTIPLE TESTING")
    n_trials = len(all_did) + (0 if args.quick else len(tab_big) + len(tab_bin))
    best = ports.loc[ports["sharpe_gross"].abs().idxmax()]
    dsr = growth.deflated_sharpe(sr=abs(float(best["sharpe_gross"])) / math.sqrt(TDAYS),
                                 n_trials=n_trials, n_obs=int(best["n_days"]))
    print(f"  registered (signal x horizon) cells run this round: N = {n_trials}")
    print(f"  best book by |gross Sharpe|: h={int(best['h'])}  "
          f"Sharpe {best['sharpe_gross']:+.3f} over {int(best['n_days'])} sessions, "
          f"break-even {best['breakeven_bps']:.2f} bps")
    print(f"  deflated Sharpe at N={n_trials}: {dsr:.3f}   "
          f"(this repo's standalone bar is t > 3)")
    print(f"\ndone in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
