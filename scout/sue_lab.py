"""H26 - post-earnings drift sorted on the EARNINGS SURPRISE (SUE), not the price reaction.

MECHANISM (one sentence, before any number)
-------------------------------------------
Investors do not fully appreciate the autocorrelation in quarterly earnings
changes (Bernard-Thomas 1989, 1990), so a firm whose earnings surprise the
seasonal random walk keeps having that surprise priced in for weeks after it is
announced - the drift is the market finishing a job it started too slowly.

Testable consequence: rank announcements by standardised unexpected earnings and
the top decile must out-drift the bottom decile over the following 5-63 sessions,
in the SAME direction as the surprise, and by more than the announcement-day
price reaction alone explains.

WHY THIS IS NOT A REPEAT OF H2b
-------------------------------
scout/hypotheses.md H2b rejected drift sorted on the two-day PRICE REACTION
(+5% and -5% reactors ended identically, n~6k). That is a different sort
variable, and the literature's variable has always been the surprise. The repo
had no fundamental data when H2b ran; it does now (scout/sec_bulk.py). The
price-reaction sort is re-run HERE as a control that must reproduce H2b's null,
and it does (below).

WHAT IS MEASURED
----------------
Universe   the 1,507 current S&P 1500 members (scout/universe.py) - SURVIVORSHIP
           ON THE ENTRY SIDE, see LIMITS. 1,390 of them produce at least one
           usable SUE.
Earnings   scout/sec_bulk.py XBRL facts, tag NetIncomeLoss, consolidated rows
           only (segments and coreg both null), uom USD, first-filing-wins on
           every (ticker, period, qtrs) cell. Fiscal Q4 is usually not filed as
           a qtrs=1 fact, so 7,842 Q4 quarters are DERIVED as annual minus the
           three filed quarters of the same fiscal year, and carry the max of
           the four filing dates. After that 98.9% of consecutive period-end
           gaps are one quarter.
Dates      scout/earnings_history.json, 21k real SEC 8-K Item 2.02 filing dates.
           98.4% of events matched an 8-K in (period end, filing date + 3d].
Prices     Alpaca SIP daily closes, adjustment=all, split-REPAIRED (below).
           2,664 sessions, 2016-01-04..2026-08-07.
Sample     42,740 SUE events, 40,747 of them usable at h=21 after 2017-01-01,
           1,390 firms, 2,410 distinct entry sessions.

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
four and would manufacture a -75% "surprise"). The per-share version is run as
a registered variant anyway, using NI / split-adjusted shares outstanding
(sec_bulk.shares_panel, keyed on each fact's FILING date), and it agrees.

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
the last input fact became public. Concretely, in DataFrame terms the return is
`close.shift(-h) / close - 1` read at index e+1, and every fact entering SUE has
`filed <= date(e)`. The trailing 8 seasonal differences are each checked
individually: a difference is admitted only if max(filed_j, filed_{j-4}) is
strictly before the event's own filing date. The decile breakpoints are taken
from events with entry session in [e-63, e-1] - the previous calendar quarter of
announcements, never the current one (Livnat-Mendenhall's own breakpoint rule,
and the reason a same-quarter cross-sectional rank is not used).

Measured cost of that discipline: median(filed - ann) = 1 day, p75 = 8, p90 =
17. The point-in-time rule is nearly free here, which is worth saying because it
is usually not.

CONTROLS (four, all run, none optional)
---------------------------------------
a. RANDOM-PICK from the identical eligible pool - decile labels drawn uniformly
   at random per event, 200 draws, mean AND SD (Rule 10). Expectation zero by
   construction; what it buys is the noise scale. Its SD is printed next to the
   block-bootstrap SE as Rule 14 demands, and it is 2-3x too tight - the same
   anti-conservatism H16 documented.
b. FIRM-LEVEL DATE SHUFFLE - each firm's own SUE values permuted across its own
   announcement dates, 200 draws. Every firm keeps its own SUE distribution and
   its own event dates; only the pairing of surprise to quarter dies. A DRIFT
   effect must collapse here. A "high-SUE firms are simply better stocks" effect
   survives untouched. This is the control that decides H26.
c. PRICE-REACTION SORT - the H2b replication. Deciles of the 2-day announcement
   reaction close(a-1) -> close(a+1) through the identical pipeline, plus H2b's
   own +-5% mid/small-cap cohort test.
d. MATCHED BENCHMARKS - the equal-weight mean of every eligible event in the
   same window (the "pool"), and SPY over each event's identical calendar
   window (the market-adjusted column).

VERDICT: CONFIRMED at the surprise level, UNTRADEABLE at large-cap costs
------------------------------------------------------------------------
1. THE DRIFT IS THERE AND IT IS THE SURPRISE, NOT THE REACTION. Decile 10 minus
   decile 1, market-adjusted, entry one session after the later of the 8-K and
   the 10-Q:

       h= 5   +25.7 bps   t=+4.60   halves +26.0 / +25.5
       h=21   +58.7 bps   t=+4.42   halves +65.1 / +52.5
       h=42   +81.4 bps   t=+3.94   halves +85.4 / +77.5
       h=63  +100.4 bps   t=+3.70   halves +85.6 / +115.0

   Same sign in both halves at every horizon, monotone in the horizon, and the
   two shorter horizons clear this repo's t>3 bar. The decile profile is
   monotone-ish rather than a knife edge: D1 -37.5 bps and D10 +43.9 bps at
   h=21, with D5 at -6.0.

2. THE DATE-SHUFFLE CONTROL KILLS IT, WHICH IS WHAT IT IS SUPPOSED TO DO HERE.
   Permuting each firm's SUE across its own announcements takes the h=21 spread
   from +58.7 bps to +0.2 +- 9.5 bps (p=0.000) and h=63 from +100.4 to
   -0.1 +- 16.2. Unlike H15 - where the shuffle reproduced the effect and
   therefore destroyed it - here the effect is entirely in the TIMING of the
   surprise, which is exactly what Bernard-Thomas claims. The random-pick null
   lands at 0.0 +- 4.3 bps (h=21) against the block bootstrap's 13.3, i.e. 3.1x
   too tight; the shuffle null at 9.5 is 1.4x too tight and is the one quoted.

3. THE PRICE-REACTION CONTROL REPRODUCES H2b'S NULL, so the pipeline agrees with
   the established repo result. Reaction deciles D10-D1, market-adjusted:
   +6.3 bps (h=5, t=+0.86), -3.8 (h=21, t=-0.22), -22.7 (h=42, t=-0.95),
   -37.9 (h=63, t=-1.32) - no drift, and the sign turns negative exactly where
   H2b found the two cohorts ending identically. H2b's own test on this
   pipeline: mid/small +5% reactors end +2.09% at 42 sessions, -5% reactors
   +2.29%, difference -0.20pp. H2b said "+5% reactors and -5% reactors end
   identically (~+1.7-2.4% both)". Reproduced.

4. IT IS DOWN-CAP, AS DOCUMENTED - AND THAT IS WHERE IT CANNOT BE TRADED.
   h=21 market-adjusted D10-D1 by liquidity tercile of 20-day median dollar
   volume at entry: LOW +91.4 bps, MID +55.9, HIGH +34.8. By S&P segment:
   small +76.4, mid +59.3, large +33.7. The ordering is monotone in both cuts
   and both halves agree. The effect is roughly 2.7x larger in the least-liquid
   third of the S&P 1500 than in the most-liquid third - and the least-liquid
   third of the S&P 1500 is where the 10 bps cost assumption stops being true.

5. COSTS DECIDE IT, AND THEY DECIDE AGAINST. A D10-D1 book pays a round trip on
   each leg, so break-even round-trip cost is HALF the spread: 12.8 bps (h=5),
   29.4 (h=21), 40.7 (h=42), 50.2 (h=63). At the 10 bps charged for large caps
   the h=21 book nets +38.7 bps per 21-session hold = +4.7%/yr GROSS OF BORROW,
   before market impact, on a book that must be shorted. The long-only form -
   which is the only form this user can trade - is D10 minus the eligible pool:
   +21.2 bps at h=21 (t=+3.19), break-even 21.2 bps, netting +11.2 bps per hold
   = +1.4%/yr against SPY's +15.8%/yr over the same decade. Real, honest, and
   not a business.

6. WHAT THE H2b/H26 PAIR ACTUALLY MEANS. The 2-day price reaction and SUE
   correlate at only rank 0.183 in this sample. The market reacts to something
   other than the seasonal-random-walk surprise on the day (guidance, revenue
   mix, the analyst consensus this repo has no data for), and it is the
   accounting surprise - not the reaction - that keeps paying. That is the
   Bernard-Thomas claim stated precisely, and it is why sorting on the reaction
   found nothing while sorting on the surprise found this.

KNOWN LIMITS (measured or structural, none of them fixed here)
--------------------------------------------------------------
1. SURVIVORSHIP ON THE ENTRY SIDE. The universe is TODAY'S S&P 1500 and the
   8-K date file covers exactly those 1,498 names; scout/pit.py's 154 delisted
   S&P 500 members have neither 8-K dates nor a ticker in the SEC map (the map
   is current registrants only). The bias direction is stateable: firms that
   were delisted for failure disproportionately posted negative surprises, and
   their absence removes bad outcomes from the LOW-SUE bucket, which SHRINKS
   the measured spread. So this limitation works against the result rather than
   for it - but it is not quantified, and the down-cap cells are the ones it
   touches most.
2. NO MICRO CAPS. The S&P 600 smallest tercile here is ~$1-3bn, not the
   sub-$300m decile where the published PEAD is loudest. A large effect at the
   bottom of THIS universe is a lower bound on the published one, and says
   nothing about whether the published one is still there.
3. GAAP NET INCOME ONLY, NO ANALYST CONSENSUS. The seasonal-random-walk SUE is
   the mechanical surprise, not the surprise-versus-expectations that actually
   moves prices. Livnat-Mendenhall found the analyst-based SUE produces a LARGER
   drift; this repo has no analyst data, so the number here is the weaker of the
   two definitions.
4. NET INCOME IS DIRTY. Impairments, tax-reform one-offs (2017 Q4 is visible in
   the tails) and discontinued operations all enter. Winsorising SUE at +-8
   changes the h=21 spread from +58.7 to +57.2 bps, so the tails are not driving
   it, but a cleaner operating-earnings tag would be a better signal.
5. COSTS ARE MODELLED, NOT MEASURED. 10 bps round trip per leg, no borrow, no
   impact, no shorting constraint, and the effect is concentrated exactly where
   all four of those get worse.
6. ONE MACRO ERA. 2017-2026: one long bull market, one crash, one inflation
   shock.

Run: python -m scout.sue_lab              (full study, ~4 min warm)
     python -m scout.sue_lab --selftest   (offline shift/leakage checks, <5s)
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import time

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
    close = close.copy()
    vals = close.to_numpy()
    vol = volume.reindex_like(close).to_numpy()
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
    for h in horizons:
        ea = np.where(a_ok, e_ann + 1, 0)
        ev[f"afwd{h}"] = np.where(a_ok, cl[ea + h, j] / cl[ea, j] - 1.0, np.nan)
        ev[f"amkt{h}"] = np.where(a_ok, spy[ea + h] / spy[ea] - 1.0, np.nan)
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


def date_shuffle_control(d: pd.DataFrame, sig_col: str, entry_col: str,
                         y: np.ndarray, n_t: int, h: int, rng,
                         n_d=N_D, reps=CTRL_REPS):
    """CONTROL (b), the one that decides H26: permute each FIRM's SUE values
    across that firm's own announcement dates.

    What survives: which firms exist, when they announce, and each firm's own
    distribution of surprises - so "high-SUE firms are simply better stocks"
    survives untouched. What dies: which quarter's surprise belongs to which
    announcement. A drift effect must collapse here."""
    entry = d[entry_col].to_numpy()
    sig = d[sig_col].to_numpy()
    groups = [np.asarray(g) for g in d.groupby("ticker", sort=False).indices.values()]
    out = np.empty(reps)
    for r in range(reps):
        s = sig.copy()
        for g in groups:
            if len(g) > 1:
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
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    rng = np.random.default_rng(SEED)
    t0 = time.time()

    print("=== data ===")
    bars = load_bars(args.refresh_bars)
    close, volume = bars["close"], bars["volume"]
    if not args.no_repair:
        close = repair_splits(close)
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

    print("\n=== registered variant: RAW (not market-adjusted) ===")
    for h in HORIZONS:
        r = run_sort(ev, "sue", f"fwd{h}", f"mkt{h}", "e_evt", h, n_t, rng, adjust=False)
        print(fmt(r, f"h={h:>2} raw"))

    print("\n=== registered variant: announcement-anchored (entry = close(8-K+1)) ===")
    print("    uses the surprise from the 10-Q, which the press release almost "
          "certainly\n    contained but this pipeline cannot verify - "
          "optimistic by the filing gap.")
    for h in HORIZONS:
        r = run_sort(ev, "sue", f"afwd{h}", f"amkt{h}", "entry_ann", h, n_t, rng)
        print(fmt(r, f"h={h:>2} ann-anchored"))

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
        d = ev[(ev["e_evt"] >= 0) & np.isfinite(ev["sue"]) & np.isfinite(ev[f"fwd{h}"])]
        y = d[f"fwd{h}"].to_numpy() - d[f"mkt{h}"].to_numpy()
        ds = date_shuffle_control(d, "sue", "e_evt", y, n_t, h, rng)
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
        sh = date_shuffle_control(d, "sue", "e_evt", y, n_t, 21,
                                  np.random.default_rng(1), reps=30)
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
