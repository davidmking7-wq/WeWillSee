"""H26 - post-earnings drift sorted on the EARNINGS SURPRISE (SUE), not the price reaction.

MECHANISM (one sentence, before any number)
-------------------------------------------
Investors do not fully appreciate the autocorrelation in quarterly earnings
changes (Bernard-Thomas 1989, 1990), so a firm whose earnings surprise the
seasonal random walk keeps having that surprise priced in for weeks after it is
announced - the drift is the market finishing a job it started too slowly.

Testable consequence: rank announcements by standardised unexpected earnings and
the top decile must out-drift the bottom decile over the following 5-63 sessions,
in the SAME direction as the surprise.

WHY THIS IS NOT A REPEAT OF H2b
-------------------------------
scout/hypotheses.md H2b rejected drift sorted on the two-day PRICE REACTION
(+5% and -5% reactors ended identically, n~6k). That is a different sort
variable, and the literature's variable has always been the surprise. The repo
had no fundamental data when H2b ran; it does now (scout/sec_bulk.py). The
price-reaction sort is re-run HERE as a control that must reproduce H2b's null,
and it does.

VERDICT: REJECTED - the surprise is real, large, and PRICED ON THE ANNOUNCEMENT
-------------------------------------------------------------------------------
Every number below is from `python -m scout.sue_lab`, 431 s, output kept in
scout/cache_sue_lastrun.txt. Deciles, equal weight per event, market-adjusted
against SPY over each event's identical calendar window, forward returns
winsorised at their own 1%/99% (the unwinsorised number is printed beside every
headline), circular moving-block bootstrap over SESSIONS with block = holding
period, 2,000 draws. n = 41,378 ranked events at h=21 out of 42,119 usable, on
2,026 distinct entry sessions, 1,389 firms, 2017-01..2026-05.

1. THE SIGNAL IS NOT BROKEN - THE POSITIVE CONTROL IS EMPHATIC. Mean two-day
   announcement reaction by SUE decile, in bps:

       D1     D2     D3     D4     D5     D6     D7     D8     D9    D10
     -117.0  -89.4  -24.3  +10.4  +42.8  +92.1  +91.6 +117.7 +143.3 +186.1

   monotone but for one adjacent pair, D10-D1 = +303.1 bps at t = +15.43. A
   seasonal-random-walk surprise computed from GAAP net income sorts the
   announcement-day move about as cleanly as anything in this repo sorts
   anything. Any rejection below is a statement about the market, not about a
   dead signal - which is the only thing that makes a null worth reading.

2. AND THE MARKET PAYS IT ALL AT ONCE. Event-time CAR from close(a-1),
   market-adjusted, deciles formed the literature's way:

       decile   (-1,+1)   (-1,+5)  (-1,+21)  (-1,+42)  (-1,+63)
       D10       +179.1    +175.6    +217.1    +145.9    +187.8
       D1        -134.1    -126.2    -134.4    -189.9    -164.3
       D10-D1    +313.2    +301.8    +351.5    +335.8    +352.1

   **89% of the entire 63-session D10-D1 spread is already paid by close(a+1).**
   The remaining ~39 bps over three months is the drift Bernard-Thomas
   predicts, and it is inside every error bar in this file. That table is the
   whole result.

3. THE STRICT POINT-IN-TIME SORT MEASURES NOTHING. Entry = close of the session
   AFTER the later of the 8-K and the 10-Q, D10-D1 market-adjusted:

       h= 5   +11.11 bps  [ -18.11,  +38.39]  t=+0.77  halves +24.23/ -1.67
       h=21    -2.46 bps  [ -74.66,  +65.34]  t=-0.07  halves -34.07/+28.64
       h=42   +21.19 bps  [ -70.71, +113.04]  t=+0.45  halves -19.06/+61.09
       h=63    -1.58 bps  [-115.57, +106.85]  t=-0.03  halves -73.55/+69.58

   No horizon reaches |t| = 1, the sign flips across halves at three of four
   horizons, and the decile profile is not monotone at any of them (at h=21 the
   worst decile is D5 at -31.2 and D1 is the second BEST at +7.3). Unwinsorised:
   +8.81 / -16.59 / +17.45 / -3.16. Not market-adjusted: +8.47 / -22.84 / +4.49
   / -17.43. Rule 13 finds nothing to strip - trailing 252-session beta is
   1.04-1.10 across all ten deciles, so the market adjustment moves the answer
   by a few bps and cannot be hiding anything.

4. THE ONE CELL WITH THE REGISTERED SIGN IS INSIDE ITS OWN NULL. Entering right
   after the 8-K instead (the literature-faithful specification, which assumes
   the press release carried the net income the 10-Q later tagged - median 1
   session earlier, p75 8, p90 17) gives -7.00 / +51.36 / +27.66 / +27.12 bps,
   and the h=21 cell is the only one in the study that is positive in both
   halves (+44.20/+57.84) at a t worth reading (+1.57). The firm-level
   date-shuffle - each firm's own SUEs permuted across that firm's own
   announcement dates, so every firm keeps its own surprise distribution and
   only the pairing of surprise to quarter dies - returns **+27.88 +- 17.40 bps,
   p = 0.085**. Fifty-four percent of the one positive cell survives destroying
   its timing entirely. At h=63 the shuffle returns **+81.16** against a real
   +27.12: the static "which firms have big surprises" component is three times
   the timed effect. Same shape on the strict spec (h=63 real -1.58, shuffle
   +79.49 +- 33.23, p = 0.995). This is H15's failure mode reached through
   accounting data.

5. THE H2b CONTROL REPRODUCES H2b EXACTLY, so the pipeline agrees with the
   established repo result before it is allowed to disagree with anything.
   Mid/small caps, 42 sessions, raw end return: reaction >= +5% ends +1.88%
   (n=6,483), reaction <= -5% ends +1.94% (n=5,725), difference -0.06pp; H2b
   recorded "end identically, ~+1.7-2.4% both". Reaction deciles D10-D1 are
   -11.34 / +45.23 / +80.12 / +41.60 bps, |t| <= 1.82. And SUE correlates with
   the two-day reaction at rank 0.118 - the two sorts really are different
   variables, which is what made this test worth running.

6. IT IS NOT DOWN-CAP HERE, WHICH IS THE OPPOSITE OF THE DOCUMENTED PATTERN.
   Strict spec, h=21 by liquidity tercile of 20-day median dollar volume: LOW
   -15.78, MID -13.99, HIGH +14.22; at h=63: LOW -76.91, MID +3.65, HIGH
   +153.41 (t=+1.73). By segment at h=63: small -25.77, mid -96.91, large
   +114.59. The ann-anchored spec orders the same way (h=63 liquidity HIGH
   +181.48, t=+2.33; LOW -76.74). Livnat-Mendenhall put PEAD in the smallest,
   least-liquid names; in this universe the only cells with the registered sign
   are the largest and most liquid, which is what a multiple-comparison artefact
   looks like and not what the mechanism predicts. Twelve such cells were cut;
   two clear |t| = 2.

7. THE LATE-WINDOW PLACEBO SAYS THERE IS NO DRIFT CLOCK. Sessions +63..+126
   after the same surprise earn +18.72 bps, +0.30 bps per session, against the
   in-window -0.03. Drift that is finished after 60 sessions should give ~0 out
   here; it gives marginally more than the in-window number, because both are
   zero.

8. COSTS, ALTHOUGH BY NOW THEY ARE ACADEMIC. Break-even round-trip cost for the
   two-legged D10-D1 book is 5.6 / -1.2 / 10.6 / -0.8 bps at h=5/21/42/63
   against 10 charged. The long-only D10-minus-pool form - the only shape this
   user could trade - is +0.21 / +15.92 / +8.55 / +10.92 bps with t = +0.02 /
   +0.86 / +0.29 / +0.33, break-even 0.2 / 15.9 / 8.5 / 10.9 bps, netting
   +0.71%/yr at best against SPY's ~+15.8%/yr over the same decade.

WHAT IS MEASURED
----------------
Universe   the 1,507 current S&P 1500 members (scout/universe.py) - SURVIVORSHIP
           ON THE ENTRY SIDE, see LIMITS. 1,390 of them produce at least one
           usable SUE.
Earnings   scout/sec_bulk.py XBRL facts, tag NetIncomeLoss, consolidated rows
           only (segments and coreg both null), uom USD, first-filing-wins on
           every (ticker, period, qtrs) cell. Fiscal Q4 is usually not filed as
           a qtrs=1 fact, so Q4 quarters are DERIVED as annual minus the three
           filed quarters of the same fiscal year, and carry the max of the four
           filing dates.
Dates      scout/earnings_history.json, 21k real SEC 8-K Item 2.02 filing dates.
           98.4% of events matched an 8-K in (period end, filing date + 3d].
Prices     Alpaca SIP daily closes, adjustment=all, split-REPAIRED and
           frozen-quote-retired (below). 2,664 sessions, 2016-01-04..2026-08-07.
Sample     42,740 SUE events built; 42,119 usable after 2017-01-01; 41,378
           ranked at h=21; 2,026 entry sessions; 1,389 firms.
Effective independent sample   the cross-section is collapsed to one row per
           SESSION before any statistic, and holds overlap, so the honest count
           is 2,026 sessions = 96 non-overlapping 21-session holds and 32
           non-overlapping 63-session holds. That, not 41,378, is why the h=63
           confidence interval is +-110 bps wide.

THE SIGNAL
----------
    SUE_q = (NI_q - NI_{q-4}) / sd(NI_j - NI_{j-4}, j = q-8 .. q-1)

the seasonal-random-walk definition (Foster-Olsen-Shevlin; Livnat-Mendenhall
2006), requiring at least 6 of the 8 trailing seasonal differences - LM's own
rule, not a tuned one.

IT IS COMPUTED ON NET INCOME LEVELS, NOT PER SHARE, AND THAT IS DELIBERATE.
The scaling cancels: dividing numerator and denominator by the same share count
leaves SUE unchanged, so a levels SUE equals the per-share SUE up to slow drift
in the share count - and it is immune to the split-adjustment problem that
sec_bulk.adjust_facts_for_splits exists to solve (a 4:1 split divides EPS by
four and would manufacture a -75% "surprise"). The price-scaled variant
(NI change over market value) is run as a registered variant and agrees:
+3.69 bps at h=21, +68.71 at h=63 (t=+1.10).

WHERE THE shift() IS (the only thing that can manufacture this result)
---------------------------------------------------------------------
Every event carries two candidate dates: `ann` (the 8-K Item 2.02 filing date -
the press release) and `filed` (the 10-Q/10-K filing date, which is where THIS
pipeline can first read the number). The primary run uses WHICHEVER IS LATER,
per the brief:

    e   = first session index >= max(ann, filed)
    ENTRY = close(e + 1)                      <- one full session of buffer,
                                                 because SEC filings are
                                                 routinely stamped after 16:00
    fwd_h(event) = close(e + 1 + h) / close(e + 1) - 1

so the return the signal weights starts at the close AFTER the session in which
the last input fact became public. In DataFrame terms the return is
`close.shift(-h) / close - 1` read at index e+1, and every fact entering SUE has
`filed <= date(e)`. The trailing 8 seasonal differences are each checked
individually: a difference is admitted only if max(filed_j, filed_{j-4}) is
strictly before the event's own filing date. The decile breakpoints are taken
from events with entry session in [e-63, e-1] - the previous quarter of
announcements, never the current one (Livnat-Mendenhall's own breakpoint rule,
and the reason a same-date cross-sectional rank is not used: earnings arrive in
three-week bursts, so a same-date rank is 40 firms on a Tuesday and 2 on a
Friday). `main` asserts all three properties on the real 42,119-event table
before any number is printed, and `--selftest` proves the labeller cannot see
its own session on synthetic data.

Measured cost of that discipline: median(filed - ann) = 1 day, p75 = 8, p90 =
17. The point-in-time rule is nearly free here, which is worth saying because it
is usually not.

DATA HYGIENE - AND THE DEFECT THAT MATTERED WAS NOT THE ONE IN THE BRIEF
-------------------------------------------------------------------------
The brief warned about the 5.1% unapplied-split debt. This lab repairs it from
Alpaca's own corporate-actions feed (5 events: AAPL 2020-08-31 4:1, SIRI
2024-09-10 1:10, ROL twice, DEA; 12 more too close to 1:1 for the ex-date test
to classify, printed and left alone) and flags every residual |1-day return| >
45% (0.27% of events touch one; excluding them moves h=21 from -2.46 to -0.87).

The defect that actually moved numbers is the FROZEN QUOTE. Alpaca keeps
printing a delisted ticker at its last trade, and when the ticker is reissued
after a Chapter 11 the splice manufactures an enormous return: GPOR, VAL, DBD,
BTU, CRC, EXE all carry the old equity's penny quote spliced onto the
reorganised company's $30-70 price, on real 10-Q filing dates. 23 symbols are
retired at their first run of 10 identical closes (scout/reversal_lab.py's rule)
and 377 further zero-volume sessions are blanked.

`--no-retire` measures what that is worth, and it is the largest number in this
file. Without the retirement rule the UNWINSORISED h=63 D10-D1 spread is
**+896.68 bps, halves +2053.15 / -274.01**, against the clean run's -3.16; at
h=5/21/42 it is -174.51 / -188.99 / -153.52 against +8.81 / -16.59 / +17.45.
A dozen bankrupt-ticker splices - which land in the LOW-SUE decile by
construction, because a company about to reorganise reports terrible earnings -
are worth thirty times any effect this study is trying to measure, and they
carry whichever sign the splice happens to have. The 1%/99% winsorisation
independently removes almost all of it (unretired but winsorised: +6.14 bps at
h=63 against the clean -1.58), so the two guards are belt and braces and the
conclusion does not rest on either one alone. A version of this lab with
neither guard would have reported a large, monotone, half-sample-unstable
"PEAD" that is entirely delisting artefact.

CONTROLS (six, all run, none optional)
--------------------------------------
a. RANDOM-PICK from the identical eligible pool - decile labels drawn uniformly
   per event, 200 draws, mean AND SD (Rule 10). Its SD is printed next to the
   block-bootstrap SE (Rule 14) and is 0.51-0.67x of it, i.e. anti-conservative
   by about half, the same direction H16/H25 documented.
b. FIRM-LEVEL DATE SHUFFLE, 200 draws - THE ROW THAT DECIDES H26, and the one
   that fires.
c. PRICE-REACTION SORT - the H2b replication, deciles and H2b's own +-5%
   mid/small cohort test.
d. MATCHED BENCHMARKS - the equal-weight mean of every eligible event in the
   same window (the pool), and SPY over each event's identical window.
e. POSITIVE CONTROL - the announcement reaction by SUE decile. Without it a null
   here would be unreadable.
f. LATE-WINDOW PLACEBO - sessions +63..+126 on the same surprise.

KNOWN LIMITS (measured or structural, none of them fixed here)
--------------------------------------------------------------
1. POWER. The h=21 spread's 95% interval is +-70 bps and the h=63 interval
   +-110 bps, on 96 and 32 non-overlapping holds. This study excludes a drift
   larger than roughly 0.7% per quarter in this universe; it cannot exclude one
   of 20-30 bps. The published large-sample PEAD, which is several times that
   in the smallest CRSP deciles, IS excluded here.
2. SURVIVORSHIP ON THE ENTRY SIDE. The universe is TODAY'S S&P 1500 and the 8-K
   file covers those names; scout/pit.py's delisted members have no ticker in
   the SEC map (current registrants only). Direction is stateable: firms
   delisted for failure disproportionately posted negative surprises, and their
   absence removes bad outcomes from the LOW-SUE bucket, which SHRINKS the
   measured spread. So the bias works against the registered sign - but it is
   not quantified, and it lands hardest on exactly the down-cap cells that were
   supposed to carry the effect.
3. NO MICRO CAPS. The S&P 600 floor is ~$1bn, not the sub-$300m decile where
   published PEAD is loudest. This is evidence about the S&P 1500, not about
   the anomaly's home.
4. GAAP NET INCOME, NO ANALYST CONSENSUS. The seasonal random walk is the
   mechanical surprise, not surprise-versus-expectations. Livnat-Mendenhall
   find the analyst-based SUE drifts MORE; this repo has no analyst data, so
   this is the weaker of the two definitions - and note that the weaker one
   still sorts the announcement-day move at t=+15.4.
5. NET INCOME IS DIRTY. Impairments, the 2017 tax act and discontinued
   operations all enter. The registered "winsorise SUE at +-8" robustness check
   turns out to be a NO-OP BY CONSTRUCTION and is reported as such: clipping a
   variable that is only ever used through a rank cannot move a decile
   boundary, and it moves h=21 and h=63 by exactly 0.00 bps. The check that
   does bite is the price-scaled surprise (NI change over market value), a
   genuinely different variable: +3.69 bps at h=21, +68.71 at h=63 (t=+1.10).
6. ONE MACRO ERA, 2017-2026, and post-publication decay is exactly what a
   1989-2006 literature should show by now (McLean-Pontiff).

Run: python -m scout.sue_lab                (full study, ~7 min warm)
     python -m scout.sue_lab --selftest     (offline shift/leakage checks, <5s)
     python -m scout.sue_lab --fast         (structural smoke run, NOT a result)
     python -m scout.sue_lab --no-retire    (what the frozen-quote defect is worth)
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import time
import warnings

import numpy as np
import pandas as pd

from . import config, universe

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against the outcome.
# --------------------------------------------------------------------------
HORIZONS = (5, 21, 42, 63)
N_D = 10                    # deciles, as registered
MIN_TRAIL = 6               # >=6 of the trailing 8 seasonal diffs (Livnat-Mendenhall)
MAX_FILING_LAG = 120        # days; a fact filed later than this is a comparative,
                            # usable as HISTORY but never as an EVENT
COHORT_SESSIONS = 63        # trailing window supplying the decile breakpoints
MIN_COHORT = 200            # thinner cohorts do not get ranked
START = "2017-01-01"        # SUE needs ~12 quarters of history; 2016 is warm-up
COST_BPS = 10.0             # round trip, per leg
BOOT_REPS = 2000
CTRL_REPS = 200
SEED = 20260809
WINSOR_P = 0.01             # forward returns clipped at their own 1st/99th pct
                            # inside each analysed subsample - Livnat-Mendenhall's
                            # own treatment. Applied to EVERY event identically,
                            # so it cannot favour a decile; the unwinsorised
                            # number is printed next to every headline.
STALE_RUN = 10              # identical consecutive closes = a frozen quote
SPLIT_LOG_TOL = 0.30        # only repair splits this far from 1:1 (news_attention_lab
                            # limit: the ex-date price test cannot classify smaller ones)
EXTREME_1D = 0.45           # |1-day return| above this is presumed a data defect

BARS_CACHE = config.SCOUT_DIR / "cache_sue_bars.pkl"
EVENT_CACHE = config.SCOUT_DIR / "cache_sue_events.pkl"


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def load_bars(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Split-repaired daily SIP bars for the S&P 1500 plus SPY.

    scout/data.py is the repo's daily source; the repair layer is this file's,
    because scout/data.py inherits Alpaca's missing-split defect (5.1% of splits
    unapplied, BACKTEST-REPORT.md). Only |log ratio| > SPLIT_LOG_TOL events are
    repaired - the ex-date price test cannot decide smaller ones and "repairing"
    MET's 2017 Brighthouse spin-off would INSERT an 11% fake jump."""
    if BARS_CACHE.exists() and not refresh:
        bars = pickle.load(open(BARS_CACHE, "rb"))
    else:
        from . import data
        syms = sorted({u["symbol"] for u in universe.load()} | {"SPY"})
        print(f"fetching daily SIP bars for {len(syms)} symbols (a few minutes)...")
        out: dict[str, list[pd.DataFrame]] = {"open": [], "close": [], "volume": []}
        for i in range(0, len(syms), 250):
            b = data.daily_ohlcv(syms[i:i + 250], 3900)
            for f in out:
                out[f].append(b[f].astype("float64"))
        bars = {f: pd.concat(v, axis=1).sort_index() for f, v in out.items()}
        pickle.dump(bars, open(BARS_CACHE, "wb"))
    for f in bars:
        bars[f].index = pd.DatetimeIndex(bars[f].index).tz_localize(None).normalize()
    return bars


def repair_splits(close: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Divide pre-ex-date closes by the split ratio wherever the bars missed it."""
    from . import intraday
    syms = sorted(close.columns)
    events: dict[str, list[dict]] = {}
    for i in range(0, len(syms), 200):
        events.update(intraday.split_events(syms[i:i + 200], "2016-01-01",
                                            str(close.index[-1].date())))
    close = close.copy()
    done, skipped, unknown = [], [], []
    for sym in close.columns:
        for e in intraday.unapplied_splits_close(close[sym], events.get(sym, [])):
            tag = f"{sym} {e['ex_date'].date()} ratio {e['ratio']:g} jump {e['jump']:.3f}"
            if e["applied"] is None:
                unknown.append(tag)
                continue
            if abs(math.log(e["ratio"])) <= SPLIT_LOG_TOL:
                skipped.append(tag)
                continue
            close.loc[close.index < e["ex_date"], sym] /= e["ratio"]
            done.append(tag)
    if verbose:
        print(f"  splits: {sum(len(v) for v in events.values())} events, "
              f"{len(done)} repaired, {len(skipped)} too close to 1:1 to decide, "
              f"{len(unknown)} moved but not at the split ratio")
        for t in done:
            print(f"    REPAIRED {t}")
        for t in skipped:
            print(f"    skipped  {t}")
    return close


def retire_stale(close: pd.DataFrame, volume: pd.DataFrame, run: int = 10,
                 verbose: bool = True) -> pd.DataFrame:
    """Retire a symbol permanently at its first run of `run` identical closes,
    and blank any session that printed zero volume.

    THIS IS THE DEFECT THAT ACTUALLY MATTERED HERE, and it is not the one the
    brief warned about. Six Chapter-11 tickers in the S&P 1500 - GPOR, VAL, DBD,
    BTU, CRC, EXE - carry the OLD equity's frozen penny quote (0.14, 0.33, 0.25,
    zero volume, the same close for weeks) spliced directly onto the
    REORGANISED company's $30-70 price when the ticker was reissued. Alpaca's
    corporate-actions feed knows nothing about it because it is not a split.
    Unfiltered, GPOR alone prints a +49,466% 63-session return on a real 10-Q
    filing date, and one such observation moves an equal-weight decile mean of
    4,166 events by 1,187 bps - which is roughly ten times the entire effect
    this study is trying to measure.

    The rule is the one scout/reversal_lab.py registered: >= `run` identical
    consecutive closes is how a frozen quote and a reused-ticker splice both
    present, and no genuinely traded S&P 1500 name does it."""
    vals = np.array(close.to_numpy(), dtype=float)      # to_numpy() can be a view
    vol = np.asarray(volume.reindex_like(close).to_numpy(), dtype=float)
    retired = []
    for j, sym in enumerate(close.columns):
        col = vals[:, j]
        same = np.zeros(len(col), dtype=bool)
        same[1:] = np.isfinite(col[1:]) & (col[1:] == col[:-1])
        c = 0
        for i in range(len(col)):
            c = c + 1 if same[i] else 0
            if c >= run - 1:
                start = i - c
                vals[start:, j] = np.nan
                retired.append((sym, close.index[start].date()))
                break
    n_zero = int(((vol == 0) & np.isfinite(vals)).sum())
    vals[(vol == 0)] = np.nan
    if verbose:
        print(f"  stale-quote retirement: {len(retired)} symbols retired at their "
              f"first run of {run} identical closes; {n_zero:,} further "
              f"zero-volume sessions blanked")
        for sym, d in retired[:12]:
            print(f"    RETIRED {sym} from {d}")
        if len(retired) > 12:
            print(f"    ... and {len(retired) - 12} more")
    return pd.DataFrame(vals, index=close.index, columns=close.columns)


# --------------------------------------------------------------------------
# the surprise
# --------------------------------------------------------------------------

def quarterly_net_income(tickers: list[str]) -> pd.DataFrame:
    """One row per (ticker, fiscal quarter): net income, and when it was filed.

    Point-in-time disciplines, in order of how much damage they do when missed:
      1. consolidated rows only (segments and coreg null) - sec_bulk.pit_panel's
         docstring explains why this one silently destroys a share-based signal;
         it does the same to a segment-reported income line.
      2. first filing of each (ticker, period, qtrs) wins - restatements are
         lookahead wearing an accountant's hat.
      3. fiscal Q4 derived as annual minus the three filed quarters, carrying the
         LATEST of the four filing dates, because that is when the difference
         became computable."""
    from . import sec_bulk
    ni = sec_bulk.load_tags(["NetIncomeLoss"])
    ni = ni[ni["ticker"].isin(tickers) & ni["segments"].isna() & ni["coreg"].isna()
            & ni["uom"].eq("USD") & ni["qtrs"].isin([1, 4])
            & ni["ddate"].between("2012-01-01", "2027-01-01")]
    ni = (ni.sort_values("filed")
            .drop_duplicates(subset=["ticker", "ddate", "qtrs"], keep="first"))
    q1 = ni[ni["qtrs"] == 1][["ticker", "ddate", "filed", "value"]].copy()
    q1["src"] = "filed"
    q4 = ni[ni["qtrs"] == 4][["ticker", "ddate", "filed", "value"]]

    by_ticker = {tk: g.set_index("ddate") for tk, g in q1.groupby("ticker")}
    derived = []
    for tk, g in q4.groupby("ticker"):
        have = by_ticker.get(tk)
        if have is None:
            continue
        dd = have.index
        for D, fa, A in zip(g["ddate"], g["filed"], g["value"]):
            if D in have.index:
                continue
            prior = dd[(dd > D - pd.Timedelta(days=340)) & (dd < D - pd.Timedelta(days=30))]
            if len(prior) != 3:
                continue
            gaps = sorted((D - prior).days)
            if not (60 <= gaps[0] <= 120 and 150 <= gaps[1] <= 210
                    and 240 <= gaps[2] <= 300):
                continue
            sub = have.loc[prior]
            derived.append({"ticker": tk, "ddate": D,
                            "filed": max(fa, sub["filed"].max()),
                            "value": A - sub["value"].sum(), "src": "derived_q4"})
    q = pd.concat([q1, pd.DataFrame(derived)], ignore_index=True)
    return q.sort_values(["ticker", "ddate"]).reset_index(drop=True)


def build_events(q: pd.DataFrame, ann_map: dict[str, list[str]]) -> pd.DataFrame:
    """SUE per announcement, with both candidate event dates attached.

    The trailing-8 window is filtered fact by fact: a seasonal difference enters
    the standard deviation only if BOTH of its net-income facts were filed
    strictly before this event's own filing date. Skipping that check is the
    quiet way a restated comparative from next year's 10-K ends up in a
    denominator it could not have been in."""
    rows = []
    for tk, g in q.groupby("ticker", sort=False):
        g = g.sort_values("ddate")
        dd = g["ddate"].to_numpy()
        v = g["value"].to_numpy()
        fl = g["filed"].to_numpy()
        n = len(g)
        diff = np.full(n, np.nan)
        dfiled = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
        for i in range(4, n):
            gap = (dd[i] - dd[i - 4]).astype("timedelta64[D]").astype(int)
            if 330 <= gap <= 400:                      # same quarter, one year back
                diff[i] = v[i] - v[i - 4]
                dfiled[i] = max(fl[i], fl[i - 4])
        for i in range(n):
            if not np.isfinite(diff[i]):
                continue
            lag = (fl[i] - dd[i]).astype("timedelta64[D]").astype(int)
            if not (0 < lag <= MAX_FILING_LAG):
                continue                                # a comparative, not an event
            w = [diff[j] for j in range(max(0, i - 8), i)
                 if np.isfinite(diff[j]) and dfiled[j] < fl[i]]
            if len(w) < MIN_TRAIL:
                continue
            sd = float(np.std(w, ddof=1))
            if not sd > 0:
                continue
            rows.append({"ticker": tk, "ddate": dd[i], "filed": fl[i],
                         "ni": v[i], "diff": diff[i], "sd": sd,
                         "sue": diff[i] / sd, "n_trail": len(w)})
    ev = pd.DataFrame(rows)
    ev["ddate"] = pd.to_datetime(ev["ddate"])
    ev["filed"] = pd.to_datetime(ev["filed"])

    ann = np.full(len(ev), np.datetime64("NaT"), dtype="datetime64[ns]")
    for tk, g in ev.groupby("ticker", sort=False):
        ds = np.array(sorted(pd.to_datetime(d) for d in ann_map.get(tk, [])))
        if not len(ds):
            continue
        for pos, (lo, fld, dda) in zip(g.index, zip(g["ddate"], g["filed"], g["ddate"])):
            hi = min(fld + pd.Timedelta(days=3), dda + pd.Timedelta(days=MAX_FILING_LAG))
            c = ds[(ds > lo) & (ds <= hi)]
            if len(c):
                ann[pos] = c[-1]
    ev["ann"] = ann
    ev["event"] = ev[["filed", "ann"]].max(axis=1)     # WHICHEVER IS LATER
    return ev


def load_events(refresh: bool = False) -> pd.DataFrame:
    if EVENT_CACHE.exists() and not refresh:
        return pd.read_pickle(EVENT_CACHE)
    tickers = sorted({u["symbol"] for u in universe.load()})
    t0 = time.time()
    q = quarterly_net_income(tickers)
    ann_map = json.loads((config.SCOUT_DIR / "earnings_history.json")
                         .read_text(encoding="utf-8"))
    ev = build_events(q, ann_map)
    ev.to_pickle(EVENT_CACHE)
    print(f"  built {len(ev):,} SUE events from {len(q):,} quarterly facts "
          f"in {time.time() - t0:.0f}s")
    return ev


# --------------------------------------------------------------------------
# events -> returns
# --------------------------------------------------------------------------

def attach_returns(ev: pd.DataFrame, close: pd.DataFrame, volume: pd.DataFrame,
                   horizons=HORIZONS) -> pd.DataFrame:
    """Entry index, forward returns, market return, liquidity, data-defect flags.

    ENTRY = close(e + 1) where e is the first session at or after the event date.
    The +1 is the buffer: SEC filings are routinely stamped after 16:00 ET, so a
    close(e) entry would occasionally be a price that no longer existed when the
    document appeared."""
    sess = close.index
    n_t = len(sess)
    cl = close.to_numpy()
    col = {s: j for j, s in enumerate(close.columns)}
    dvol = (close * volume).rolling(20, min_periods=10).median().to_numpy()
    ret1 = (close / close.shift(1) - 1.0).to_numpy()
    extreme = np.abs(ret1) > EXTREME_1D
    spy = cl[:, col["SPY"]]

    ev = ev[ev["ticker"].isin(col)].copy()
    e_evt = np.searchsorted(sess.to_numpy(), ev["event"].to_numpy(), side="left")
    e_ann = np.searchsorted(sess.to_numpy(), ev["ann"].to_numpy(), side="left")
    j = ev["ticker"].map(col).to_numpy()

    ev["e_evt"] = e_evt
    ev["e_ann"] = np.where(ev["ann"].isna().to_numpy(), -1, e_ann)
    ok = (e_evt + 1 + max(horizons) < n_t) & (e_evt >= 21)
    ev = ev[ok].copy()
    e_evt, e_ann, j = e_evt[ok], ev["e_ann"].to_numpy(), j[ok]
    entry = e_evt + 1

    ev["px_entry"] = cl[entry, j]
    ev["dvol20"] = dvol[e_evt, j]
    for h in horizons:
        ev[f"fwd{h}"] = cl[entry + h, j] / cl[entry, j] - 1.0
        ev[f"mkt{h}"] = spy[entry + h] / spy[entry] - 1.0
    # entry at close(e_ann + 1), the H2b convention, for the reaction control
    a_ok = (e_ann > 0) & (e_ann + 1 + max(horizons) < n_t)
    ev["entry_ann"] = np.where(a_ok, e_ann + 1, -1)
    ev["react2"] = np.where(a_ok, cl[np.where(a_ok, e_ann + 1, 0), j]
                            / cl[np.where(a_ok, e_ann - 1, 0), j] - 1.0, np.nan)
    ev["rmkt2"] = np.where(a_ok, spy[np.where(a_ok, e_ann + 1, 0)]
                           / spy[np.where(a_ok, e_ann - 1, 0)] - 1.0, np.nan)
    for h in horizons:
        ea = np.where(a_ok, e_ann + 1, 0)
        ev[f"afwd{h}"] = np.where(a_ok, cl[ea + h, j] / cl[ea, j] - 1.0, np.nan)
        ev[f"amkt{h}"] = np.where(a_ok, spy[ea + h] / spy[ea] - 1.0, np.nan)
    # RULE 13 diagnostic: each event's trailing 252-session beta to SPY, so the
    # decile profile of BETA can be printed next to the decile profile of
    # return. H25 was a beta sort that looked like a signal; this is the check
    # that would have caught it.
    beta = np.full(len(ev), np.nan)
    w = 252
    have = e_evt >= w
    rows = np.flatnonzero(have)
    warnings.filterwarnings("ignore", message="Mean of empty slice")
    for a in range(0, len(rows), 5000):
        blk = rows[a:a + 5000]
        off = (e_evt[blk][:, None] - np.arange(w, 0, -1)[None, :])
        ri = ret1[off, j[blk][:, None]]
        rm = ret1[off, col["SPY"]]
        ri = np.where(np.isfinite(ri) & np.isfinite(rm), ri, np.nan)
        rm = np.where(np.isfinite(ri), rm, np.nan)
        ci = ri - np.nanmean(ri, axis=1, keepdims=True)
        cm = rm - np.nanmean(rm, axis=1, keepdims=True)
        var = np.nansum(cm * cm, axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            beta[blk] = np.where(var > 0, np.nansum(ci * cm, axis=1) / var, np.nan)
    ev["beta252"] = beta
    # LATE-WINDOW PLACEBO: sessions 63..126 after entry, sorted on the SAME
    # surprise. Bernard-Thomas drift is over inside ~60 sessions, so a spread
    # that keeps accruing at the same rate out here is a firm characteristic
    # (this universe is TODAY's S&P 1500 - growth firms that survived), not a
    # post-announcement correction.
    lo_i = np.minimum(entry + max(horizons), n_t - 1)
    hi_i = np.minimum(entry + 2 * max(horizons), n_t - 1)
    ok_late = entry + 2 * max(horizons) < n_t
    ev["fwd_late"] = np.where(ok_late, cl[hi_i, j] / cl[lo_i, j] - 1.0, np.nan)
    ev["mkt_late"] = np.where(ok_late, spy[hi_i] / spy[lo_i] - 1.0, np.nan)
    # data-defect flag: any |1-day| > 45% anywhere in the widest window used
    lo = np.maximum(e_evt - 2, 0)
    hi = entry + max(horizons)
    ev["defect"] = [bool(extreme[a:b + 1, c].any()) for a, b, c in zip(lo, hi, j)]
    return ev


# --------------------------------------------------------------------------
# cross-sectional machinery
# --------------------------------------------------------------------------

def trailing_deciles(sig: np.ndarray, entry: np.ndarray, n_d: int = N_D,
                     window: int = COHORT_SESSIONS,
                     min_cohort: int = MIN_COHORT) -> np.ndarray:
    """Decile label from the PREVIOUS quarter's announcements, -1 if unrankable.

    Livnat-Mendenhall's breakpoint rule, and the reason this study does not rank
    within the event date: earnings arrive in three-week bursts, so a same-date
    cross-section is 40 firms on a Tuesday and 2 on a Friday, and a within-date
    rank silently makes the Friday firms extreme. Using the prior 63 sessions of
    events gives every event the same ~1,000-name yardstick and cannot see its
    own cohort."""
    order = np.argsort(entry, kind="stable")
    s_sig, s_entry = sig[order], entry[order]
    lab = np.full(len(sig), -1, dtype=np.int8)
    uniq = np.unique(s_entry)
    for e in uniq:
        lo = np.searchsorted(s_entry, e - window, side="left")
        hi = np.searchsorted(s_entry, e, side="left")          # strictly before e
        pool = s_sig[lo:hi]
        pool = pool[np.isfinite(pool)]
        if len(pool) < min_cohort:
            continue
        edges = np.quantile(pool, np.arange(1, n_d) / n_d)
        m = np.searchsorted(s_entry, e, side="left"), np.searchsorted(s_entry, e, side="right")
        idx = order[m[0]:m[1]]
        vals = sig[idx]
        d = np.searchsorted(edges, vals, side="right").astype(np.int8)
        d[~np.isfinite(vals)] = -1
        lab[idx] = d
    return lab


def session_sums(entry: np.ndarray, lab: np.ndarray, y: np.ndarray, n_t: int,
                 hi: int, lo: int) -> np.ndarray:
    """Per-session (sum, count) for the top bucket, the bottom bucket and the
    whole eligible pool. Collapsing to one row per SESSION before any statistic
    is taken is what makes date clustering structural, exactly as
    scout/calibrate.py does it."""
    m = np.isfinite(y) & (lab >= 0)
    e, l, v = entry[m], lab[m], y[m]
    out = np.zeros((n_t, 6))
    np.add.at(out, (e[l == hi], 0), v[l == hi])
    np.add.at(out, (e[l == hi], 1), 1.0)
    np.add.at(out, (e[l == lo], 2), v[l == lo])
    np.add.at(out, (e[l == lo], 3), 1.0)
    np.add.at(out, (e, 4), v)
    np.add.at(out, (e, 5), 1.0)
    return out


def _stat(tot: np.ndarray) -> tuple[float, float, float]:
    """(top mean, bottom mean, pool mean) from summed (sum, count) columns."""
    def r(a, b):
        return np.divide(a, b, out=np.full(np.shape(a), np.nan, dtype=float),
                         where=np.asarray(b) > 0)
    return (r(tot[..., 0], tot[..., 1]), r(tot[..., 2], tot[..., 3]),
            r(tot[..., 4], tot[..., 5]))


def block_boot(M: np.ndarray, block: int, reps: int, rng: np.random.Generator,
               chunk: int = 250) -> dict:
    """Circular moving-block bootstrap over SESSIONS of the per-session sums.

    Blocks of length h keep the overlap that h-session holds create inside a
    block; an i.i.d. bootstrap would ignore it and understate the standard error.
    Sessions with no events contribute zeros to both sum and count, which is
    correct: resampling a quiet Friday should shrink the sample, not the mean."""
    n_t = M.shape[0]
    nb = int(math.ceil(n_t / block))
    sp, hi, lo, po = [], [], [], []
    for start in range(0, reps, chunk):
        k = min(chunk, reps - start)
        st = rng.integers(0, n_t, size=(k, nb))
        idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(k, -1)[:, :n_t] % n_t
        tot = M[idx].sum(axis=1)
        a, b, p = _stat(tot)
        sp.append(a - b); hi.append(a); lo.append(b); po.append(a - p)
    sp = np.concatenate(sp)
    tot = M.sum(axis=0)
    a, b, p = (float(v) for v in _stat(tot))
    se = float(np.nanstd(sp, ddof=1))
    return dict(spread=a - b, top=a, bot=b, pool=p, excess=a - p,
                se=se, t=(a - b) / se if se > 0 else np.nan,
                lo=float(np.nanpercentile(sp, 2.5)), hi=float(np.nanpercentile(sp, 97.5)),
                se_excess=float(np.nanstd(np.concatenate(po), ddof=1)),
                n_top=tot[1], n_bot=tot[3], n_pool=tot[5])


def run_sort(ev: pd.DataFrame, sig_col: str, ret_col: str, mkt_col: str,
             entry_col: str, h: int, n_t: int, rng: np.random.Generator,
             n_d: int = N_D, adjust: bool = True, winsor: float = WINSOR_P) -> dict:
    """One (signal, horizon) cell end to end.

    `adjust` subtracts SPY over the event's identical calendar window (Rule 13:
    a dollar-neutral book is not a market-neutral book, so the market-adjusted
    number is the one quoted).

    `winsor` clips the RAW forward return at its own 1st/99th percentile inside
    the analysed subsample before the market is subtracted - Livnat-Mendenhall's
    own treatment, and unavoidable here: even after the data-hygiene layer this
    universe contains genuine +300% 63-session small-cap moves, and one of them
    is worth 7 bps of a decile mean. The unwinsorised number is printed beside
    every headline so the reader can see exactly what the clip is worth."""
    d = ev[ev[entry_col] >= 0]
    d = d[np.isfinite(d[sig_col]) & np.isfinite(d[ret_col])]
    r = d[ret_col].to_numpy()
    if winsor and len(r) > 200:
        lo_c, hi_c = np.nanquantile(r, [winsor, 1 - winsor])
        r = np.clip(r, lo_c, hi_c)
    entry = d[entry_col].to_numpy()
    y = r - (d[mkt_col].to_numpy() if adjust else 0.0)
    lab = trailing_deciles(d[sig_col].to_numpy(), entry, n_d)
    M = session_sums(entry, lab, y, n_t, n_d - 1, 0)
    out = block_boot(M, h, BOOT_REPS, rng)
    # both halves, split at the median entry session
    med = int(np.median(entry[lab >= 0]))
    for name, m in (("half1", entry < med), ("half2", entry >= med)):
        t = session_sums(entry[m], lab[m], y[m], n_t, n_d - 1, 0).sum(axis=0)
        a, b, _ = _stat(t)
        out[name] = a - b
    out["lab"] = lab
    out["entry"] = entry
    out["y"] = y
    out["sig"] = d[sig_col].to_numpy()
    out["ticker"] = d["ticker"].to_numpy()
    out["idx"] = d.index.to_numpy()
    out["decile_means"] = [
        (np.nanmean(y[lab == k]) if (lab == k).any() else np.nan) for k in range(n_d)]
    return out


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def random_pick_control(entry, lab, y, n_t, h, rng, n_d=N_D, reps=CTRL_REPS):
    """CONTROL (a): decile labels drawn uniformly at random per event from the
    identical eligible pool. Expectation is exactly zero; the draws buy the
    noise SCALE (Rule 10), and the SE ratio is printed (Rule 14)."""
    m = lab >= 0
    e, yy = entry[m], y[m]
    out = np.empty(reps)
    for r in range(reps):
        l = rng.integers(0, n_d, size=len(e)).astype(np.int8)
        t = session_sums(e, l, yy, n_t, n_d - 1, 0).sum(axis=0)
        a, b, _ = _stat(t)
        out[r] = a - b
    return out


def date_shuffle_control(ticker: np.ndarray, sig: np.ndarray, entry: np.ndarray,
                         y: np.ndarray, n_t: int, rng,
                         n_d=N_D, reps=CTRL_REPS):
    """CONTROL (b), the one that decides H26: permute each FIRM's SUE values
    across that firm's own announcement dates.

    What survives: which firms exist, when they announce, and each firm's own
    distribution of surprises - so "high-SUE firms are simply better stocks"
    survives untouched. What dies: which quarter's surprise belongs to which
    announcement. A drift effect must collapse here.

    It is handed the PRIMARY's own arrays (same rows, same winsorisation, same
    market adjustment), so the null and the real number differ in exactly one
    thing."""
    pos = pd.Series(np.arange(len(ticker)), index=pd.Index(ticker))
    groups = [g.to_numpy() for _, g in pos.groupby(level=0, sort=False) if len(g) > 1]
    out = np.empty(reps)
    for r in range(reps):
        s = sig.copy()
        for g in groups:
            s[g] = rng.permutation(s[g])
        lab = trailing_deciles(s, entry, n_d)
        t = session_sums(entry, lab, y, n_t, n_d - 1, 0).sum(axis=0)
        a, b, _ = _stat(t)
        out[r] = a - b
    return out


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def fmt(res: dict, label: str) -> str:
    return (f"  {label:<26} D{N_D}-D1 {1e4 * res['spread']:+8.2f} bps  "
            f"[{1e4 * res['lo']:+8.2f},{1e4 * res['hi']:+8.2f}]  t={res['t']:+5.2f}  "
            f"halves {1e4 * res['half1']:+8.2f}/{1e4 * res['half2']:+8.2f}  "
            f"n {int(res['n_top']):>5}/{int(res['n_bot']):>5}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.sue_lab")
    ap.add_argument("--refresh-bars", action="store_true")
    ap.add_argument("--refresh-events", action="store_true")
    ap.add_argument("--no-repair", action="store_true",
                    help="skip the split repair (shows what the defect is worth)")
    ap.add_argument("--no-retire", action="store_true",
                    help="skip the stale-quote retirement (ditto, and it is the "
                         "one that matters here)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fast", action="store_true",
                    help="few bootstrap/control draws - a structural smoke run, "
                         "NOT a result")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.fast:
        global BOOT_REPS, CTRL_REPS
        BOOT_REPS, CTRL_REPS = 60, 8

    rng = np.random.default_rng(SEED)
    t0 = time.time()

    print("=== data ===")
    bars = load_bars(args.refresh_bars)
    close, volume = bars["close"], bars["volume"]
    if not args.no_repair:
        close = repair_splits(close)
    if not args.no_retire:
        close = retire_stale(close, volume, STALE_RUN)
    print(f"  bars {close.shape[0]} sessions x {close.shape[1]} symbols  "
          f"{close.index[0].date()}..{close.index[-1].date()}")

    ev = load_events(args.refresh_events)
    print(f"  {len(ev):,} SUE events, {ev['ticker'].nunique():,} firms, "
          f"{ev['event'].min().date()}..{ev['event'].max().date()}")
    gap = (ev["filed"] - ev["ann"]).dt.days
    print(f"  8-K matched on {100 * ev['ann'].notna().mean():.1f}% of events; "
          f"filed-minus-announced days: median {gap.median():.0f}, "
          f"p75 {gap.quantile(.75):.0f}, p90 {gap.quantile(.90):.0f} "
          f"-> point-in-time costs almost nothing here")

    ev = attach_returns(ev, close, volume)
    ev = ev[ev["event"] >= START].reset_index(drop=True)
    n_t = len(close)
    # POINT-IN-TIME AUDIT on the real table, not a synthetic one: the session
    # the entry price comes from must be strictly after the session in which
    # the last input fact became public.
    sess = close.index
    assert (sess[ev["e_evt"].to_numpy()] >= ev["event"]).all(), "entry session before the event"
    assert (sess[ev["e_evt"].to_numpy() + 1] > ev["event"]).all(), "entry price on the event day"
    assert (ev["filed"] <= sess[ev["e_evt"].to_numpy()]).all(), "a fact filed after its own entry"
    print(f"  point-in-time audit: entry session > event date on all "
          f"{len(ev):,} events")
    print(f"  usable after {START}: {len(ev):,} events, "
          f"{ev['e_evt'].nunique():,} distinct entry sessions, "
          f"{100 * ev['defect'].mean():.2f}% touch a |1-day| > {EXTREME_1D:.0%} move")

    seg = {u["symbol"]: u.get("segment", "large") for u in universe.load()}
    ev["segment"] = ev["ticker"].map(seg)

    # ---------------------------------------------------------------- primary
    print(f"\n=== H26 PRIMARY: SUE deciles, entry = close(session after "
          f"max(8-K, 10-Q)), market-adjusted ===")
    primary = {}
    for h in HORIZONS:
        r = run_sort(ev, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng)
        primary[h] = r
        print(fmt(r, f"h={h:>2}"))
        print(f"      deciles (bps): " +
              " ".join(f"{1e4 * m:+7.1f}" for m in r["decile_means"]))
        print(f"      D{N_D}-pool {1e4 * r['excess']:+7.2f} bps  "
              f"t={r['excess'] / r['se_excess']:+5.2f}   "
              f"pool {1e4 * r['pool']:+7.2f}  "
              f"break-even round-trip {1e4 * r['spread'] / 2:5.1f} bps "
              f"(two legs) / {1e4 * r['excess']:5.1f} bps (long-only)")
        u = run_sort(ev, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng, winsor=0.0)
        print(f"      UNWINSORISED {1e4 * u['spread']:+8.2f} bps  t={u['t']:+5.2f}  "
              f"halves {1e4 * u['half1']:+8.2f}/{1e4 * u['half2']:+8.2f}  "
              f"(the {WINSOR_P:.0%}/{1 - WINSOR_P:.0%} clip is worth "
              f"{1e4 * (r['spread'] - u['spread']):+.2f} bps)")

    print("\n=== POSITIVE CONTROL: does the SUE measure carry any earnings news "
          "at all? ===")
    print("    (mean 2-day announcement reaction by SUE decile. If this is flat "
          "the study\n     measures a broken signal, not a market fact - a "
          "rejection would be meaningless.)")
    r21 = primary[21]
    react = ev["react2"].to_numpy()[r21["idx"]]
    lab = r21["lab"]
    prof = [np.nanmean(react[lab == k]) if (lab == k).any() else np.nan
            for k in range(N_D)]
    print("      reaction by SUE decile (bps): " +
          " ".join(f"{1e4 * m:+7.1f}" for m in prof))
    m10, m1 = lab == N_D - 1, lab == 0
    diff = np.nanmean(react[m10]) - np.nanmean(react[m1])
    se = math.sqrt(np.nanvar(react[m10], ddof=1) / np.isfinite(react[m10]).sum()
                   + np.nanvar(react[m1], ddof=1) / np.isfinite(react[m1]).sum())
    print(f"      D{N_D}-D1 announcement reaction {1e4 * diff:+7.1f} bps  "
          f"t={diff / se:+5.2f}  (event-level SE; the news IS in the surprise)")

    print("\n=== RULE 13: trailing 252-session beta to SPY by SUE decile ===")
    bet = ev["beta252"].to_numpy()[r21["idx"]]
    print("      beta by SUE decile: " +
          " ".join(f"{np.nanmean(bet[lab == k]):+6.2f}" if (lab == k).any()
                   else "   nan" for k in range(N_D)))

    print("\n=== DECAY PROFILE: bps per session (drift must decay, a "
          "characteristic does not) ===")
    print("  " + "  ".join(f"h={h}: {1e4 * primary[h]['spread'] / h:+6.2f}"
                           for h in HORIZONS))

    print("\n=== LATE-WINDOW PLACEBO: sessions +63..+126, same surprise ===")
    print("    Bernard-Thomas drift is finished by ~60 sessions. A spread out "
          "here at the\n    same per-session rate is a firm characteristic, not "
          "a correction.")
    rl = run_sort(ev, "sue", "fwd_late", "mkt_late", "e_evt", max(HORIZONS),
                  n_t, rng)
    print(fmt(rl, "late +63..+126"))
    print(f"      per-session {1e4 * rl['spread'] / max(HORIZONS):+6.2f} bps "
          f"against the in-window {1e4 * primary[63]['spread'] / 63:+6.2f}")

    print("\n=== registered variant: RAW (not market-adjusted) ===")
    for h in HORIZONS:
        r = run_sort(ev, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng, adjust=False)
        print(fmt(r, f"h={h:>2} raw"))

    print("\n=== registered variant: announcement-anchored (entry = close(8-K+1)) ===")
    print("    THE LITERATURE-FAITHFUL SPECIFICATION, and the one that needs an "
          "assumption:\n    the 8-K Item 2.02 press release states the quarter's "
          "net income, so SUE is\n    knowable at the announcement in the real "
          "world - but the XBRL fact this lab\n    reads is stamped with the "
          "10-Q/10-K date, median 1 session later (p75 8,\n    p90 17). Entering "
          "here therefore assumes the release carried the number.")
    ann_res = {}
    for h in HORIZONS:
        r = run_sort(ev, "sue", f"afwd{h}", f"amkt{h}", "entry_ann", h, n_t, rng)
        ann_res[h] = r
        print(fmt(r, f"h={h:>2} ann-anchored"))
        print(f"      deciles (bps): " +
              " ".join(f"{1e4 * m:+7.1f}" for m in r["decile_means"]))
        print(f"      D{N_D}-pool {1e4 * r['excess']:+7.2f} bps  "
              f"t={r['excess'] / r['se_excess']:+5.2f}   "
              f"pool {1e4 * r['pool']:+7.2f}")
    print("\n    EVENT-TIME CAR (market-adjusted, from close(a-1)) - the classic "
          "PEAD picture:")
    ra = ann_res[21]
    lb, ix = ra["lab"], ra["idx"]
    car0 = (ev["react2"] - ev["rmkt2"]).to_numpy()[ix]
    print(f"      {'decile':<8}{'(-1,+1)':>10}" +
          "".join(f"{f'(-1,+{h})':>10}" for h in HORIZONS))
    for k, name in ((N_D - 1, f"D{N_D}"), (0, "D1")):
        m = lb == k
        cells = [np.nanmean(car0[m])]
        for h in HORIZONS:
            fh = (ev[f"afwd{h}"] - ev[f"amkt{h}"]).to_numpy()[ix]
            cells.append(np.nanmean(car0[m] + fh[m]))
        print(f"      {name:<8}" + "".join(f"{1e4 * c:>+10.1f}" for c in cells))
    m10, m1 = lb == N_D - 1, lb == 0
    cells = [np.nanmean(car0[m10]) - np.nanmean(car0[m1])]
    for h in HORIZONS:
        fh = (ev[f"afwd{h}"] - ev[f"amkt{h}"]).to_numpy()[ix]
        cells.append(np.nanmean(car0[m10] + fh[m10]) - np.nanmean(car0[m1] + fh[m1]))
    print(f"      {'D10-D1':<8}" + "".join(f"{1e4 * c:>+10.1f}" for c in cells))
    print(f"      of the D{N_D}-D1 total at (-1,+63), "
          f"{100 * cells[0] / cells[-1]:.0f}% is already paid by close(a+1).")

    print("    controls on the ann-anchored spec (the only cell with the "
          "registered sign):")
    for h in (21, 63):
        r = ann_res[h]
        rp = random_pick_control(r["entry"], r["lab"], r["y"], n_t, h, rng)
        ds = date_shuffle_control(r["ticker"], r["sig"], r["entry"], r["y"], n_t, rng)
        print(f"      h={h:>2}  real {1e4 * r['spread']:+8.2f}   "
              f"random-pick {1e4 * rp.mean():+7.2f} +- {1e4 * rp.std(ddof=1):5.2f} "
              f"(p={float((rp >= r['spread']).mean()):.3f})   "
              f"date-shuffle {1e4 * ds.mean():+7.2f} +- {1e4 * ds.std(ddof=1):5.2f} "
              f"(p={float((ds >= r['spread']).mean()):.3f})")
    print("    ann-anchored by liquidity tercile and segment (h=21, h=63):")
    for h in (21, 63):
        d = ev[np.isfinite(ev["dvol20"])].copy()
        d["ltile"] = d.groupby("e_ann")["dvol20"].transform(
            lambda s: pd.qcut(s.rank(method="first"), 3, labels=False)
            if s.notna().sum() >= 6 else np.nan)
        for k, name in enumerate(("LOW", "MID", "HIGH")):
            r = run_sort(d[d["ltile"] == k], "sue", f"afwd{h}", f"amkt{h}",
                         "entry_ann", h, n_t, rng)
            print(fmt(r, f"h={h:>2} ann liquidity {name}"))
        for s in ("small", "mid", "large"):
            r = run_sort(ev[ev["segment"] == s], "sue", f"afwd{h}", f"amkt{h}",
                         "entry_ann", h, n_t, rng)
            print(fmt(r, f"h={h:>2} ann {s:<5}"))

    print("\n=== CONTROL (c): the H2b replication - sort on the 2-DAY PRICE REACTION ===")
    for h in HORIZONS:
        r = run_sort(ev, "react2", f"afwd{h}", f"amkt{h}", "entry_ann", h, n_t, rng)
        print(fmt(r, f"h={h:>2} reaction"))
    mids = ev[(ev["segment"] != "large") & (ev["entry_ann"] >= 0)
              & np.isfinite(ev["react2"]) & np.isfinite(ev["afwd42"])]
    up, dn = mids[mids["react2"] >= 0.05], mids[mids["react2"] <= -0.05]
    print(f"    H2b's own cohort test, mid/small caps, h=42 raw end return:")
    print(f"      reaction >= +5%: n={len(up):>5}  avg end {100 * up['afwd42'].mean():+6.2f}%"
          f"   SPY same windows {100 * up['amkt42'].mean():+6.2f}%")
    print(f"      reaction <= -5%: n={len(dn):>5}  avg end {100 * dn['afwd42'].mean():+6.2f}%"
          f"   SPY same windows {100 * dn['amkt42'].mean():+6.2f}%")
    print(f"      difference {100 * (up['afwd42'].mean() - dn['afwd42'].mean()):+6.2f}pp   "
          f"(H2b: 'end identically, ~+1.7-2.4% both')")
    rk = ev[["sue", "react2"]].dropna()
    print(f"    rank correlation between SUE and the 2-day reaction: "
          f"{rk['sue'].rank().corr(rk['react2'].rank()):.3f}")

    # ---------------------------------------------------------------- controls
    print("\n=== CONTROLS (a) random pick and (b) firm-level date shuffle ===")
    for h in (5, 21, 63):
        r = primary[h]
        rp = random_pick_control(r["entry"], r["lab"], r["y"], n_t, h, rng)
        ds = date_shuffle_control(r["ticker"], r["sig"], r["entry"], r["y"],
                                  n_t, rng)
        p_rp = float((rp >= r["spread"]).mean())
        p_ds = float((ds >= r["spread"]).mean())
        print(f"  h={h:>2}  real {1e4 * r['spread']:+8.2f} bps   block-boot SE "
              f"{1e4 * r['se']:6.2f}")
        print(f"        random-pick   {1e4 * rp.mean():+7.2f} +- {1e4 * rp.std(ddof=1):5.2f}  "
              f"p={p_rp:.3f}   SE ratio to block bootstrap "
              f"{rp.std(ddof=1) / r['se']:.2f}x")
        print(f"        date-shuffle  {1e4 * ds.mean():+7.2f} +- {1e4 * ds.std(ddof=1):5.2f}  "
              f"p={p_ds:.3f}   SE ratio to block bootstrap "
              f"{ds.std(ddof=1) / r['se']:.2f}x")

    # ---------------------------------------------------------------- cuts
    print("\n=== where it lives: liquidity tercile (20d median $ volume at entry) ===")
    for h in (21, 63):
        d = ev[np.isfinite(ev["dvol20"])].copy()
        d["ltile"] = d.groupby("e_evt")["dvol20"].transform(
            lambda s: pd.qcut(s.rank(method="first"), 3, labels=False)
            if s.notna().sum() >= 6 else np.nan)
        for k, name in enumerate(("LOW", "MID", "HIGH")):
            sub = d[d["ltile"] == k]
            r = run_sort(sub, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng)
            print(fmt(r, f"h={h:>2} liquidity {name}"))
    print("\n=== where it lives: S&P segment (TODAY's segment - disclosed) ===")
    for h in (21, 63):
        for s in ("small", "mid", "large"):
            sub = ev[ev["segment"] == s]
            r = run_sort(sub, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng)
            print(fmt(r, f"h={h:>2} {s:<5}"))

    print("\n=== robustness (every variant run is printed, whatever it says) ===")
    for h in (21, 63):
        sub = ev[~ev["defect"]]
        r = run_sort(sub, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng)
        print(fmt(r, f"h={h:>2} ex |1d|>{EXTREME_1D:.0%}"))
        w = ev.copy()
        w["sue"] = w["sue"].clip(-8, 8)
        r = run_sort(w, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng)
        print(fmt(r, f"h={h:>2} SUE winsorised +-8"))
        r = run_sort(ev, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng, n_d=5)
        print(fmt(r, f"h={h:>2} QUINTILES"))
        ps = ev.assign(sue_p=ev["diff"] / (ev["px_entry"] * 1e6))
        r = run_sort(ps, "sue_p", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng)
        print(fmt(r, f"h={h:>2} price-scaled SUE"))

    print(f"\n=== cost arithmetic (round trip charged per leg) ===")
    print(f"  {'h':>3} {'D10-D1':>9} {'break-even':>11} {'net@10bps':>10} "
          f"{'ann.net':>8}   {'D10-pool':>9} {'break-even':>11} {'net@10bps':>10} {'ann.net':>8}")
    for h in HORIZONS:
        r = primary[h]
        sp, ex = 1e4 * r["spread"], 1e4 * r["excess"]
        per_yr = 252 / h
        print(f"  {h:>3} {sp:>+9.2f} {sp / 2:>11.1f} {sp - 2 * COST_BPS:>+10.2f} "
              f"{(sp - 2 * COST_BPS) * per_yr / 100:>+7.2f}%   "
              f"{ex:>+9.2f} {ex:>11.1f} {ex - COST_BPS:>+10.2f} "
              f"{(ex - COST_BPS) * per_yr / 100:>+7.2f}%")

    print(f"\n=== effective independent sample ===")
    for h in HORIZONS:
        r = primary[h]
        n_sess = len(np.unique(r["entry"][r["lab"] >= 0]))
        print(f"  h={h:>2}  {int(r['n_pool']):>6,} ranked events on {n_sess:,} sessions; "
              f"{n_sess / h:>6.0f} non-overlapping holds; "
              f"{ev['ticker'].nunique():,} firms")
    print(f"\ndone in {time.time() - t0:.0f}s")


# --------------------------------------------------------------------------
# offline self-test: the leakage checks, no API keys needed
# --------------------------------------------------------------------------

def selftest() -> None:
    ok = 0

    # 1. trailing_deciles cannot see its own session, nor any later one. The
    #    direct test: corrupt the signal at one session and assert that no label
    #    at that session or earlier moves.
    rng = np.random.default_rng(0)
    entry = np.repeat(np.arange(0, 400, 5), 60)
    sig = rng.normal(size=len(entry))
    lab = trailing_deciles(sig, entry, 10, window=63, min_cohort=200)
    assert (lab[entry == entry.min()] == -1).all(), "ranked the very first session"
    bad = sig.copy()
    bad[entry >= 200] += 50.0
    lab2 = trailing_deciles(bad, entry, 10, window=63, min_cohort=200)
    past = entry < 200
    assert (lab[past] == lab2[past]).all(), "a label moved when FUTURE data changed"
    ok += 1

    # 2. a planted PURE-EVENT effect is killed by the date shuffle, and a planted
    #    PURE-FIRM effect is not. This is the assertion the verdict rests on.
    n_t = 500
    n_f = 200
    tick = np.repeat([f"F{i}" for i in range(n_f)], 20)
    ent = np.tile(np.arange(20) * 21 + 80, n_f)
    s = rng.normal(size=len(tick))
    y_evt = 0.02 * s + 0.01 * rng.normal(size=len(s))          # event-timed
    firm_q = np.repeat(rng.normal(size=n_f), 20)
    y_firm = 0.02 * firm_q + 0.01 * rng.normal(size=len(s))    # firm characteristic
    for name, y, must_die in (("event", y_evt, True), ("firm", y_firm, False)):
        d = pd.DataFrame({"ticker": tick, "sue": s if name == "event" else firm_q,
                          "e_evt": ent})
        lab = trailing_deciles(d["sue"].to_numpy(), ent, 10)
        real = _stat(session_sums(ent, lab, y, n_t, 9, 0).sum(0))
        real = real[0] - real[1]
        sh = date_shuffle_control(d["ticker"].to_numpy(), d["sue"].to_numpy(),
                                  ent, y, n_t, np.random.default_rng(1), reps=30)
        if must_die:
            assert abs(sh.mean()) < 0.2 * abs(real), f"{name}: shuffle did not kill it"
        else:
            assert abs(sh.mean()) > 0.5 * abs(real), f"{name}: shuffle killed a firm effect"
        ok += 1

    # 3. block bootstrap widens on autocorrelated data (an i.i.d. one would not)
    x = np.zeros(1000)
    for i in range(1, 1000):
        x[i] = 0.9 * x[i - 1] + rng.normal()
    M = np.column_stack([x, np.ones(1000), np.zeros(1000), np.ones(1000),
                         x, np.ones(1000)])
    b1 = block_boot(M, 1, 500, np.random.default_rng(2))["se"]
    b21 = block_boot(M, 21, 500, np.random.default_rng(2))["se"]
    assert b21 > 1.5 * b1, f"block bootstrap not absorbing autocorrelation ({b21:.3f} vs {b1:.3f})"
    ok += 1

    # 4. the entry index is strictly after the event session
    idx = pd.DatetimeIndex(pd.bdate_range("2020-01-01", periods=200))
    cl = pd.DataFrame({"A": np.arange(200, dtype=float) + 100.0,
                       "SPY": np.arange(200, dtype=float) + 300.0}, index=idx)
    vol = pd.DataFrame(1e6, index=idx, columns=["A", "SPY"])
    e = pd.DataFrame({"ticker": ["A"], "ddate": [idx[50]], "filed": [idx[90]],
                      "ann": [idx[88]], "event": [idx[90]], "sue": [1.0],
                      "diff": [1.0], "sd": [1.0], "ni": [1.0], "n_trail": [8]})
    got = attach_returns(e, cl, vol, horizons=(5,))
    assert int(got["e_evt"].iloc[0]) == 90 and \
        abs(got["fwd5"].iloc[0] - (cl["A"].iloc[96] / cl["A"].iloc[91] - 1)) < 1e-12, \
        "entry is not close(e+1)"
    ok += 1

    print(f"selftest: {ok}/5 checks passed")


if __name__ == "__main__":
    main()
