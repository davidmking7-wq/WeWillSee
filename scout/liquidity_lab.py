"""H23 - illiquidity as a PRICED characteristic, and whether the engine's
$10M dollar-volume gate throws the compensation away.

MECHANISM (one sentence, stated before any number)
--------------------------------------------------
Amihud (2002): an investor who buys a stock that cannot be sold without moving
its price has bought an unhedgeable cost of exit, and in equilibrium must be
paid for it, so expected return rises with the price impact per dollar traded.

WHY THIS SPECIFIC TEST
----------------------
`config.MIN_DOLLAR_VOL = 10_000_000` is a HARD GATE in `signals.composite_at`:
any name whose 20-session median dollar volume sits below $10M is deleted from
the cross-section before a single score is computed. It was adopted as a
tradeability rule, never measured as a signal. If illiquidity is priced, the
gate is throwing away the one premium a small retail account is structurally
positioned to collect - capacity binds every institution and does not bind
this user. That makes the gate the decision attached to the hypothesis, and
the honest test is not "is there an illiquidity premium" but **"is there one
left after paying the spread that creates it"**.

WHAT IS MEASURED
----------------
Universe   S&P 1500 as of today (`scout/universe.csv`), which carries
           survivorship, re-run on the point-in-time S&P 500 (`scout/pit.py`,
           each date's ACTUAL members, delisted names included). An
           illiquidity study needs that control more than any other study in
           this repo, because the names that die are the illiquid ones.
Prices     daily SIP bars, adjustment=all, 2016-01..2026-08, fetched with
           HIGH and LOW kept (`scout/data.py` returns open/close/volume only;
           same client, same feed, same pivot - only the field list differs),
           split-REPAIRED, extreme-print guarded, stale-quote retired.
Signals    at each session t, from the trailing W sessions ending AT t:
             amihud = mean of |r| / (dollar volume / 1e6)   [Amihud 2002]
             cs     = mean of the Corwin-Schultz two-day high-low effective
                      spread, negatives set to zero        [Corwin-Schultz 2012]
             invdv  = minus the 20-session median dollar volume - i.e. the
                      GATE VARIABLE ITSELF, sorted rather than thresholded
           W in {21, 63}, W=21 the registered primary.
Portfolio  cross-sectional quintiles inside each session, equal weight, held
           close(t) -> close(t+h), h in {21, 42}; and the tradeable form, a
           42-session hold rebalanced every 21 sessions, pooled over all entry
           phases.
Direction  REGISTERED SIGN: Q5 (most ILLIQUID) minus Q1 (most liquid) is
           POSITIVE. Q5-Q1 is quoted everywhere; a negative number is the
           registered sign being wrong.

THE TWO MEASURES ARE A MUTUAL IMPLEMENTATION CHECK
--------------------------------------------------
Amihud is built from returns and dollar volume; Corwin-Schultz is built from
the high-low range and touches neither. They estimate the same latent
quantity by disjoint arithmetic, so a high cross-sectional rank correlation is
evidence that both are coded correctly, and a low one would be evidence that
at least one is not. The number is printed before any return result, and the
offline selftest additionally plants a known spread in a simulated tape and
requires Corwin-Schultz to recover it.

WHERE THE shift() IS
--------------------
`fwd_h(t) = exp(sum of log returns over t+1 .. t+h) - 1`, built as
`logret.rolling(h).sum().shift(-h)`, paired with a signal at the SAME index t
that is a function of bars through t-W+1 .. t. The two touch DISJOINT return
ranges: the signal's last input is the close(t-1)->close(t) session, the
payoff's first is close(t)->close(t+1). The Corwin-Schultz pair indexed at t
uses sessions t-1 and t and nothing later. That is the only shift in this
file; the selftest asserts that perturbing every bar after date T leaves every
signal value up to T bit-identical.

DATA HYGIENE - the brief demands this be stated, and the answer is REPAIR
------------------------------------------------------------------------
This study has no veto to hide behind, and its exposure to the repo's measured
data debt is asymmetric in the direction that would FAVOUR the hypothesis.
Three guards, all applied to the primary run, each turned off once to measure
what it is worth:

1. SPLIT REPAIR from Alpaca's own corporate-actions feed for events whose
   |log ratio| > 0.35, applied to OPEN, HIGH, LOW, CLOSE and VOLUME together
   so that dollar volume - Amihud's denominator - stays invariant. Repairing
   the close alone would leave the RANGE corrupted on exactly the dates the
   return series is fixed, which is the Corwin-Schultz input.
2. EXTREME-PRINT GUARD: |1-day simple return| > 45% sets the bar missing, so
   it enters neither signal nor any forward window that spans it.
3. STALE-QUOTE RETIREMENT (>= 10 identical consecutive closes). Decisive here:
   a frozen delisted quote has |return| = 0, so its Amihud illiquidity is
   exactly 0, and high == low, so its Corwin-Schultz spread is exactly 0. It
   is pinned to the MOST LIQUID quintile forever, paying 0.00% forever, which
   would depress the liquid leg and manufacture an illiquidity premium out of
   dead tickers.

CONTROLS (six, all run)
-----------------------
a. POSITIVE control - illiquidity at t must forecast illiquidity over t+1..t+h
   by quintile, or a null return result is evidence about the pipeline.
b. RANDOM-QUINTILE - labels permuted inside each session over the identical
   eligible pool, 200 draws, mean AND SD (Rule 10).
c. SYMBOL-PAIRING PLACEBO - each symbol permanently assigned another symbol's
   illiquidity series, 100 draws. The right null for a persistent
   characteristic (Rule 14): it preserves the persistence of the sort and
   therefore the autocorrelation of the P&L, and its SD is quoted against the
   block-bootstrap SE.
d. MATCHED BENCHMARKS - the equal-weight eligible pool, and SPY.
e. RULE 13 - every bucket's SPY beta and every book's market-adjusted alpha
   (Newey-West) printed next to its raw return. Illiquid stocks are small
   stocks; the decade's equity premium priced by beta is the standing
   explanation for any monotone profile in this repo (H25, H28).
f. SURVIVORSHIP - the whole grid re-run on point-in-time S&P 500 membership.

COSTS - THE PART THAT DECIDES IT, AND IT IS NOT A FLAT 10 bps
-------------------------------------------------------------
Charging large-cap costs to an illiquidity strategy is the error that makes
the premium look free. Every book here is charged its own MEASURED
Corwin-Schultz spread per name per round trip, bucket by bucket, multiplied by
that bucket's measured turnover. The flat 10 bps number is printed beside it
purely to show how large the error would have been. A half-spread sensitivity
(price improvement on small retail orders) is printed too, because the entire
"structural advantage for a small account" claim lives in that factor.

INFERENCE
---------
The cross-section is collapsed to ONE spread per session before any statistic
(date clustering then structural, as in scout/calibrate.py), then a circular
moving-block bootstrap with block length h absorbs the overlap h-day holds
create. Every h-day claim is pooled across all h entry phases (Rule 9).
Alphas carry Newey-West standard errors.

Run: python -m scout.liquidity_lab                # full study
     python -m scout.liquidity_lab --selftest     # offline, no keys, ~5s
     python -m scout.liquidity_lab --quick        # primary cells only

=============================================================================
VERDICT - filled in from the run; every number below is printed by this file
=============================================================================
REJECTED - but NOT for the reason the brief expected, and the difference
matters. The classic finding is that the illiquidity premium is eaten by the
cost of accessing it. That is NOT what this sample shows. Costs turn out to be
almost irrelevant here, because illiquidity is so persistent that the book
barely trades. What kills it is survivorship: the premium is large, monotone,
control-surviving and present in both halves on TODAY'S S&P 1500, and it
INVERTS on point-in-time membership. And the gate the study was aimed at turns
out to be very nearly a no-op.

1. THE REGISTERED SIGN IS RIGHT, LARGE, AND NOT A CONTROL ARTIFACT - ON THE
   SURVIVORSHIP UNIVERSE. Primary (Amihud, W=21, h=42, S&P 1500, all guards):
   Q5 - Q1 = +198.39 bps per 42-session hold, 95% moving-block CI
   [+105.63, +295.45], t = +4.09. Positive in all 12 S&P 1500 cells, positive
   in both halves (+241.52 / +155.28), positive on all 42 entry phases
   (ph_wrong = 0). Controls behave: random quintiles -0.11 +/- 2.39 bps and
   the symbol-pairing placebo -0.17 +/- 18.16 bps against +198.39. Positive
   control passes enormously - signal quintiles 0.38 / 1.36 / 3.62 / 9.23 /
   98.20 bps of price per $M traded map onto realised next-42-session
   0.41 / 1.44 / 3.97 / 9.59 / 91.61.
   AND, unlike H25 and H28, IT IS NOT A BETA SORT (Rule 13): quintile SPY
   betas 0.96 / 1.03 / 1.09 / 1.14 / 1.12, the dollar-neutral book's beta is
   +0.13 and its market-adjusted alpha +8.55%/yr at Newey-West t = +2.31. The
   standing explanation for every monotone profile in this repo does not apply
   to this one.

2. AND IT INVERTS ON POINT-IN-TIME MEMBERSHIP. Same code, same dates, each
   date's ACTUAL S&P 500 members with delisted names included: Amihud h=42
   goes +198.39 -> -42.68 bps (t -0.85, CI [-139.61, +57.08]), and the
   dollar-volume sort - the gate variable itself - goes +150.97 -> -86.16
   (t -2.14, CI [-163.54, -7.66]), i.e. mildly WRONG-signed. The tradeable
   book says the same thing in return space: on today's S&P 1500 the illiquid
   quintile earns +28.31%/yr at Sharpe 1.13 with alpha +9.29%/yr (t +2.15);
   on point-in-time membership it earns +14.71%/yr at Sharpe 0.59 with alpha
   -4.20%/yr (t -1.06), LOSING to its own liquid quintile (+16.35%, Sharpe
   0.94) and to SPY (+15.82%, Sharpe 0.90) in both halves (0.73/0.43 against
   1.03/0.83). Even the pools disagree by the size of the whole effect: the
   equal-weight S&P 1500 pool returns +19.61%/yr against the point-in-time
   pool's +15.00%.
   The segment gradient is the same story ordered by how much survivorship
   each segment carries: large +138.89, mid +450.21, small +479.09 bps, and
   the sub-$10M slice - the most contaminated cohort available - prints
   +439.47 at t = 9.78. A monotone relationship between "how much hindsight is
   in this bucket" and "how big the premium is" is not a premium.

3. COSTS DO NOT DECIDE IT, AND THE CLASSIC FINDING DOES NOT REPRODUCE. This
   was the part the brief expected to be fatal, so it is worth being exact.
   Illiquidity is the most persistent characteristic in this repo, so the book
   hardly trades: one-way turnover 0.85x/yr for Q5 and 0.65x/yr for Q1, 1.51x
   for the pair. Charging each leg its OWN measured Corwin-Schultz round trip
   (58.30 bps on Q1, 92.62 on Q5) takes the long-short from +11.92%/yr gross
   to +10.75%/yr net, and the long-only Q5 book from +28.31% to +27.52%. The
   BREAK-EVEN round-trip cost is 790.6 bps for the long-short and 1,463 bps
   for Q5 against SPY. At h=21 costs DO bite - the same spread is paid twice
   as often and every S&P 1500 net spread turns negative (-50.38 bps for the
   primary signal) - which is the one place the classic mechanism shows up.
   At the repo's 42-session horizon it does not.

4. THE COST ESTIMATOR IS THE WEAKEST LINK, AND IT IS DISCLOSED, NOT HIDDEN.
   Corwin-Schultz says SPY costs 28.4 bps round trip and AAPL/MSFT/JPM/XOM
   49.0 bps, against this repo's own 5-10 bps large-cap standard and SPY's
   real sub-1 bp spread; and it discriminates only 1.59x across a sort whose
   dollar volume ranges 53x. Censoring negative two-day estimates at zero is a
   one-sided bias, and daily-range noise survives the differencing. Two
   consequences, both stated as results: (a) the cost numbers above are
   PUNITIVE, so the cost conclusion in point 3 is conservative and safe; (b)
   Corwin-Schultz is NOT usable as a stand-alone liquidity SORT here - with
   negatives left uncensored the cs sort collapses from +257.43 to +16.43 bps
   (t +0.60). The two measures agree only 0.385 in within-date rank, while
   Amihud correlates 0.972 with minus dollar volume: in this universe Amihud
   is a dollar-volume sort wearing a different name, which is exactly why the
   invdv row tracks it and why the gate variable is the honest object of study.

5. THE GATE, WHICH WAS THE POINT: IT BARELY BINDS, AND WHAT MOVEMENT THERE IS
   FAVOURS KEEPING IT. Replaying the shipped v5 engine with the gate at $10M,
   $1M and $0, 112 monthly entries, 5 picks, per-pick Corwin-Schultz costs:
   net +1.97% / +1.82% / +1.77% per 42-session window against SPY's +2.57%.
   Removing the gate widens the post-veto pool from 537 to 631 names and
   raises the small-cap share of picks from 23.9% to 28.9%, but the median
   pick still trades $75M a day and only 8.6% of picks fall below $10M -
   because momentum, the 52-week high and the volatility band already select
   liquid names. Ranking ONLY inside the discarded pool (the names the gate
   deletes) gives net +1.74%/window against SPY's +1.72% in those windows,
   with a median pick trading $6.3M/day - and that is measured on the MOST
   survivorship-contaminated cohort in the panel, i.e. under conditions
   maximally favourable to the no-gate case. **The gate is neither protective
   nor restrictive. It is close to a no-op, and there is no case for removing
   it.** Halves disagree on the sign of the difference (h1 favours the gate
   +2.27 vs +1.68 gross, h2 favours no gate +3.10 vs +3.30), which is what
   noise looks like.

6. THE CAPACITY ASYMMETRY IS REAL - IT JUST HAS NOTHING TO BUY. The most
   illiquid quintile of the S&P 1500 still trades $5.92M a day at the median;
   a $10,000 order is 0.169% of that, and 76.7% of the bucket sits below the
   $10M gate. So the structural claim in the hypothesis is correct: capacity
   binds institutions here and does not bind this user. That is why this was
   worth testing, and it is not sufficient - the compensation it was supposed
   to unlock is not there once the universe stops knowing the future.

7. THE GUARDS, MEASURED. Split repair: 5 events (AAPL 2020-08-31 4:1, SIRI
   2024-09-10 0.1:1, ROL x2, DEA), the names this repo's audit found by hand.
   Extreme-print guard: 250 bars over 149 symbols, 0.0064% of the panel, and
   turning it off moves the primary by 0.01 bps - nil. Stale-quote retirement:
   40 symbols, and turning it off moves the primary from +198.39 to +205.42,
   i.e. 3.5% MORE positive, exactly the direction predicted in advance (a
   frozen quote scores as the most liquid stock in the market and pays
   nothing). The pre-registered worry was right about the sign and wrong about
   the size; none of the three guards decides this study, and the universe
   does.

8. WHAT WOULD FALSIFY THIS REJECTION. A delisting-complete S&P 1500 - the
   data debt RESEARCH-AGENDA already flags. The point-in-time control
   available here is the S&P 500, whose least-liquid quintile still trades
   tens of millions a day, so it CANNOT test the premium where Amihud's
   mechanism is strongest. The honest statement of this sample is therefore
   two-sided and both sides should be quoted: (a) in survivorship-clean US
   large caps, 2016-2026, there is no illiquidity premium and if anything a
   small negative one; (b) in genuinely illiquid US small caps the question
   remains OPEN, because every dataset in this repo that reaches down there
   also knows which of those companies survived. Deflated Sharpe of the
   headline long-only book, at this repo's running trial count N=400, is
   0.770 - which does not clear a 0.95 bar even before the survivorship
   correction that removes the return.

TRIAL COUNT: 46 registered cells and variants (24 universe x signal x window
x horizon cells, 7 robustness variants, 4 engine gate configurations, 3 cost
models, 2 point-in-time book cells, 2 guard-sensitivity runs, 2 positive
controls, 2 null controls), all reported above and in liquidity_results.json.
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd

from . import config
from .news_attention_lab import block_boot, phase_sweep      # verified, reused
from .idiovol_lab import (retire_stale, returns, forward, forward_partial,
                          quintile_labels, bucket_means, nw_ols,
                          sub_portfolios, ladder, book_turnover, perf)

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against the outcome.
# --------------------------------------------------------------------------
WINDOWS = (21, 63)                  # formation lookbacks; 21 = registered primary
PRIMARY_W = 21
HORIZONS = (21, 42)                 # 42 = registered primary (the repo's horizon)
PRIMARY_H = 42
HOLD = 42                           # tradeable book: hold 42 sessions ...
STRIDE = 21                         # ... rebalanced monthly
N_Q = 5
MIN_ELIGIBLE = 50                   # thinner cross-sections are skipped
MIN_OBS = 15                        # valid sessions needed inside a 21d window
COST_BPS = 10.0                     # flat round trip, for the comparison only
BOOT_REPS = 5000
CTRL_REPS = 200                     # random-quintile draws
PLACEBO_REPS = 100                  # symbol-pairing placebo draws
SEED = 20260809

BIG_MOVE = 0.45                     # |1-day return| guard (data_audit.BIG_MOVE)
SPLIT_LOG_TOL = 0.35                # only repair splits this far from 1:1
STALE_RUN = 10                      # identical consecutive closes -> retired
MARKET = "SPY"
RF_SENSITIVITY = 0.02               # ASSUMED flat rf for a Sharpe sensitivity
GATES = (10e6, 1e6, 0.0, -10e6)     # engine dollar-volume gates under test;
                                    # 10e6 = shipped, negative = the DISCARDED
                                    # pool only (names the shipped gate deletes)
N_PICKS = 5                         # backtest.py's book size, kept identical
N_TRIALS = 400                      # the repo's running registry count (~340
                                    # after Round 3) plus this lab's own cells
                                    # -- deflated Sharpe uses it (Rule 3)

BARS_CACHE = config.SCOUT_DIR / "cache_liquidity_bars.pkl"
CLEAN_CACHE = config.SCOUT_DIR / "cache_liquidity_clean.pkl"
SPLIT_JSON = config.SCOUT_DIR / "cache_liquidity_splits.json"
RESULTS = config.SCOUT_DIR / "liquidity_results.json"

FIELDS = ("open", "high", "low", "close", "volume")
SIGNALS = ("amihud", "cs", "invdv")
PRIMARY_SIG = "amihud"
CS_K = 3.0 - 2.0 * math.sqrt(2.0)   # Corwin-Schultz constant, 3 - 2*sqrt(2)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def _fetch_ohlcv(symbols: list[str], days: int = 3900) -> dict[str, pd.DataFrame]:
    """`scout/data.daily_ohlcv` with the HIGH and LOW columns kept.

    data.py returns open/close/volume only, and the Corwin-Schultz estimator is
    a pure function of the daily RANGE, so this lab needs two more fields off
    the same request. Same client, same SIP feed, same adjustment=all, same
    pivot and the same US/Eastern normalisation - the only difference is the
    field list, so the closes are bit-identical to data.daily_ohlcv's."""
    from datetime import datetime, timedelta, timezone

    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    from . import data as daily_data

    client = StockHistoricalDataClient(config.ALPACA_API_KEY,
                                       config.ALPACA_SECRET_KEY)
    now = datetime.now(timezone.utc)
    frames = []
    for i in range(0, len(symbols), daily_data.CHUNK):
        chunk = symbols[i:i + daily_data.CHUNK]
        try:
            req = StockBarsRequest(symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                                   start=now - timedelta(days=days),
                                   end=now - timedelta(minutes=20),
                                   adjustment=Adjustment.ALL, feed=DataFeed.SIP)
            df = client.get_stock_bars(req).df
            if not df.empty:
                frames.append(df.reset_index()[["symbol", "timestamp", *FIELDS]])
        except Exception as e:
            print(f"  bars chunk {i // daily_data.CHUNK + 1} "
                  f"({len(chunk)} syms) failed: {e}")
    if not frames:
        raise RuntimeError("no market data returned at all")
    allb = pd.concat(frames, ignore_index=True)
    allb["timestamp"] = (pd.to_datetime(allb["timestamp"])
                         .dt.tz_convert("US/Eastern").dt.normalize())
    return {f: (allb.pivot_table(index="timestamp", columns="symbol", values=f,
                                 aggfunc="last").sort_index())
            for f in FIELDS}


def load_panel(refresh: bool = False) -> dict:
    """Raw daily OHLCV for the S&P 1500 (today's members) UNION every
    point-in-time S&P 500 member since 2016, plus SPY."""
    if BARS_CACHE.exists() and not refresh:
        return pd.read_pickle(BARS_CACHE)
    from . import pit, universe
    u = universe.load()
    seg = {r["symbol"]: r["segment"] for r in u}
    syms = sorted(set(seg) | set(pit.all_members_since("2016-01-01")) | {MARKET})
    print(f"fetching 10.7y of daily SIP bars (OHLCV) for {len(syms)} symbols ...")
    t0 = time.time()
    bars: dict[str, list] = {}
    for i in range(0, len(syms), 120):
        part = _fetch_ohlcv(syms[i:i + 120])
        for f in FIELDS:
            bars.setdefault(f, []).append(part[f])
        print(f"  {min(i + 120, len(syms)):>5}/{len(syms)} symbols "
              f"({time.time() - t0:.0f}s)")
    out = {}
    for f in FIELDS:
        df = pd.concat(bars[f], axis=1).sort_index()
        df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
        out[f] = df.astype("float64")
    cols = out["close"].columns
    out = {f: out[f].reindex(columns=cols) for f in FIELDS}
    out["segment"] = seg
    pd.to_pickle(out, BARS_CACHE)
    print(f"  panel {out['close'].shape[0]} sessions x {out['close'].shape[1]} "
          f"symbols cached ({time.time() - t0:.0f}s)")
    return out


def _split_events(symbols, start, end) -> dict:
    """Alpaca's own corporate-actions feed, cached to disk (same list every run,
    and the endpoint is rate-limited alongside the bar fetch)."""
    if SPLIT_JSON.exists():
        raw = json.loads(SPLIT_JSON.read_text())
        return {k: [{"ex_date": pd.Timestamp(e["ex_date"]), "ratio": e["ratio"],
                     "kind": e["kind"]} for e in v] for k, v in raw.items()}
    from . import intraday
    ev: dict = {}
    for i in range(0, len(symbols), 100):
        ev.update(intraday.split_events(list(symbols[i:i + 100]), start, end))
    SPLIT_JSON.write_text(json.dumps(
        {k: [{"ex_date": str(e["ex_date"].date()), "ratio": e["ratio"],
              "kind": e["kind"]} for e in v] for k, v in ev.items()}, indent=1))
    return ev


def repair_splits(bars: dict, verbose: bool = True) -> tuple[dict, list]:
    """GUARD 1. Back-adjust every split Alpaca's bar pipeline failed to apply -
    OPEN, HIGH, LOW, CLOSE and VOLUME together.

    Detection is on the CLOSE (intraday.unapplied_splits_close), the diagnostic
    that classifier was built against. All four price fields are divided by the
    ratio before the ex-date and volume is multiplied by it, so DOLLAR volume -
    the denominator of Amihud - is left invariant, which is the correct
    behaviour: a split changes neither the dollars traded nor the spread.
    Repairing the close alone would leave the high/low range corrupted at
    exactly the dates the return series is fixed."""
    from . import intraday
    close = bars["close"]
    events = _split_events(list(close.columns), "2016-01-01",
                           str(close.index[-1].date()))
    repaired = []
    for sym in close.columns:
        for e in intraday.unapplied_splits_close(close[sym], events.get(sym, [])):
            if e["applied"] is not False:
                continue
            if abs(math.log(e["ratio"])) <= SPLIT_LOG_TOL:
                continue                  # ratio too close to 1 to be decisive
            m = close.index < e["ex_date"]
            for f in ("open", "high", "low", "close"):
                bars[f].loc[m, sym] = bars[f].loc[m, sym] / e["ratio"]
            bars["volume"].loc[m, sym] = bars["volume"].loc[m, sym] * e["ratio"]
            repaired.append(f"{sym} {e['ex_date'].date()} {e['ratio']:g}:1")
    if verbose:
        print(f"  split repair applied to {len(repaired)} events: "
              f"{', '.join(repaired[:12])}{' ...' if len(repaired) > 12 else ''}")
    return bars, repaired


def clean_bars(refresh: bool = False) -> dict:
    """Split-repaired, stale-retired OHLCV.

    GUARD 3 matters more here than anywhere else in the repo, and in the
    direction that would have FAVOURED the hypothesis: a frozen delisted quote
    has |return| = 0 (Amihud illiquidity exactly 0) and high == low
    (Corwin-Schultz spread exactly 0), so it is pinned to the MOST LIQUID
    quintile forever, paying 0.00% forever."""
    if CLEAN_CACHE.exists() and not refresh:
        return pd.read_pickle(CLEAN_CACHE)
    bars = load_panel()
    seg = bars.pop("segment")
    bars = {f: bars[f].copy() for f in FIELDS}
    bars, repaired = repair_splits(bars)
    kept_close = bars["close"].copy()
    kept_volume = bars["volume"].copy()
    close, killed = retire_stale(bars["close"], run=STALE_RUN)
    dead = close.isna() & kept_close.notna()
    for f in FIELDS:
        bars[f] = bars[f].mask(dead)
    bars["close"] = close
    print(f"  stale-quote retirement: {len(killed)} symbols dropped from their "
          f"first run of {STALE_RUN} identical closes")
    # close_stale/volume_stale are kept UNMASKED so the guard-sensitivity run
    # can genuinely turn guard 3 off. Masking volume too (as the primary panel
    # does) would leave the frozen names with a NaN dollar volume and therefore
    # no Amihud value, i.e. the guard would still be on under another name.
    out = {**bars, "close_stale": kept_close, "volume_stale": kept_volume,
           "segment": seg, "repaired": repaired, "killed": killed}
    pd.to_pickle(out, CLEAN_CACHE)
    return out


# --------------------------------------------------------------------------
# the two liquidity measures
# --------------------------------------------------------------------------

def dollar_volume(close: pd.DataFrame, volume: pd.DataFrame) -> np.ndarray:
    """Daily close x volume. Split-invariant after repair_splits (price / r,
    volume * r). Dividend adjustment scales price without scaling volume, so
    historical dollar volume is understated by the cumulative dividend factor -
    a few percent over a decade, monotone in time and common across the
    cross-section, therefore harmless to a within-date rank."""
    return (close * volume).to_numpy()


def amihud_illiq(simple: np.ndarray, dvol: np.ndarray, w: int,
                 min_obs: int = MIN_OBS) -> np.ndarray:
    """Amihud (2002) ILLIQ: mean over the w sessions ENDING at t of
    |return| / (dollar volume in $M) - the price move bought by a million
    dollars of trading.

    Zero-volume sessions are dropped rather than treated as infinitely
    illiquid (an untraded session is a missing observation, not an infinite
    impact), and a window needs `min_obs` valid sessions to produce a value."""
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.abs(simple) / (dvol / 1e6)
    ratio[~np.isfinite(ratio)] = np.nan
    m = pd.DataFrame(ratio).rolling(w, min_periods=min(min_obs, w)).mean()
    return m.to_numpy().astype(np.float32)


def cs_daily(high: np.ndarray, low: np.ndarray,
             close: np.ndarray) -> np.ndarray:
    """Corwin-Schultz (2012) two-day high-low effective spread, indexed at the
    SECOND day of each pair (so the value at t uses sessions t-1 and t only).

        beta  = ln(H_t-1/L_t-1)^2 + ln(H_t/L_t)^2
        gamma = ln(max(H_t-1,H_t) / min(L_t-1,L_t))^2
        alpha = (sqrt(2 beta) - sqrt(beta)) / (3 - 2 sqrt 2)
                - sqrt(gamma / (3 - 2 sqrt 2))
        S     = 2 (e^alpha - 1) / (1 + e^alpha)

    The identifying idea: the two-day RANGE is proportional to two days of
    volatility plus ONE spread, while the sum of the single-day ranges is
    proportional to two days of volatility plus TWO spreads, so differencing
    them isolates the spread without ever seeing a quote.

    Corwin-Schultz's overnight adjustment is applied: when close(t-1) lies
    outside [L_t, H_t] the move is assumed to have happened overnight and day
    t's high and low are shifted by the gap, which stops an overnight jump
    being read as an enormous spread. That adjustment also absorbs most of the
    ex-dividend discontinuity that adjustment=all prices carry inside a two-day
    window."""
    prev_c = np.vstack([np.full((1, close.shape[1]), np.nan), close[:-1]])
    with np.errstate(invalid="ignore"):
        gap = (np.maximum(prev_c - high, 0.0) + np.minimum(prev_c - low, 0.0))
    h2, l2 = high + gap, low + gap
    h1 = np.vstack([np.full((1, high.shape[1]), np.nan), high[:-1]])
    l1 = np.vstack([np.full((1, low.shape[1]), np.nan), low[:-1]])
    bad = ~(np.isfinite(h1) & np.isfinite(l1) & np.isfinite(h2) & np.isfinite(l2))
    bad |= (h1 <= 0) | (l1 <= 0) | (h2 <= 0) | (l2 <= 0) | (h1 < l1) | (h2 < l2)
    with np.errstate(invalid="ignore", divide="ignore"):
        b = np.log(h1 / l1) ** 2 + np.log(h2 / l2) ** 2
        g = np.log(np.maximum(h1, h2) / np.minimum(l1, l2)) ** 2
        alpha = (np.sqrt(2.0 * b) - np.sqrt(b)) / CS_K - np.sqrt(g / CS_K)
        s = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
    s[bad] = np.nan
    return s.astype("float64")


def cs_spread(high: np.ndarray, low: np.ndarray, close: np.ndarray, w: int,
              zero_negatives: bool = True,
              min_obs: int = MIN_OBS) -> np.ndarray:
    """Rolling mean of the two-day estimates over the w sessions ending at t.

    Corwin-Schultz recommend setting negative two-day estimates to zero before
    averaging (a negative spread is an estimation error, and averaging the
    errors in biases the mean down). `zero_negatives=False` is the registered
    robustness variant."""
    s = cs_daily(high, low, close)
    if zero_negatives:
        s = np.maximum(s, 0.0)
    m = pd.DataFrame(s).rolling(w, min_periods=min(min_obs, w)).mean()
    return m.to_numpy().astype(np.float32)


def median_dollar_vol(close: pd.DataFrame, volume: pd.DataFrame,
                      w: int = 20) -> np.ndarray:
    """The gate variable, bit-identical to signals.feature_frames()['dvol20']:
    20-session MEDIAN of close x volume, min_periods 10."""
    return ((close * volume).rolling(w, min_periods=w // 2)
            .median().to_numpy())


def forward_mean(x: np.ndarray, h: int) -> np.ndarray:
    """Mean of x over t+1 .. t+h - the positive control's dependent variable."""
    m = pd.DataFrame(x).rolling(h, min_periods=max(1, h // 2)).mean().to_numpy()
    out = np.full_like(m, np.nan)
    out[:-h] = m[h:]
    return out


# --------------------------------------------------------------------------
# cross-sectional machinery (sign convention: spread = Q5 - Q1)
# --------------------------------------------------------------------------

def spread_of(q: np.ndarray) -> np.ndarray:
    """The registered direction: most illiquid MINUS most liquid."""
    return q[:, N_Q - 1] - q[:, 0]


def hold_turnover(lab: np.ndarray, qi: int, hold: int = HOLD) -> float:
    """Mean 0.5*sum|w_new - w_old| between formations `hold` sessions apart -
    the fraction of the bucket that needs a round trip each hold. Same
    convention as growth.turnover_cost and idiovol_lab.book_turnover."""
    tot, n = 0.0, 0
    n_s = lab.shape[1]
    for f in range(hold, lab.shape[0]):
        a = np.flatnonzero(lab[f] == qi)
        b = np.flatnonzero(lab[f - hold] == qi)
        if a.size == 0 or b.size == 0:
            continue
        wa = np.zeros(n_s); wa[a] = 1.0 / a.size
        wb = np.zeros(n_s); wb[b] = 1.0 / b.size
        tot += 0.5 * np.abs(wa - wb).sum()
        n += 1
    return float(tot / max(n, 1))


def run_cell(sig: np.ndarray, elig: np.ndarray, fwd: np.ndarray, h: int,
             rng: np.random.Generator, beta: np.ndarray | None = None,
             mkt_fwd: np.ndarray | None = None, cost: np.ndarray | None = None,
             label: str = "") -> tuple[dict, np.ndarray, np.ndarray]:
    """Q5 - Q1 (ILLIQUID minus LIQUID: the registered direction is POSITIVE)
    for one signal x horizon, with the block-bootstrap CI, both halves, the
    entry-phase sweep, the Rule-13 regression on SPY, and - if a per-name cost
    panel is supplied - the same spread net of each leg's own measured
    round-trip spread."""
    lab = quintile_labels(sig, elig, np.random.default_rng(SEED + h),
                          min_elig=MIN_ELIGIBLE)
    q, pool, cnt = bucket_means(lab, fwd)
    spread = spread_of(q)
    b = block_boot(spread, h, BOOT_REPS, rng)
    ph = phase_sweep(spread, h)
    idx = np.flatnonzero(np.isfinite(spread))
    half = len(idx) // 2
    row = dict(cell=label, h=h, n_dates=int(np.isfinite(spread).sum()),
               n_names=float(cnt[np.isfinite(spread)].sum(1).mean()),
               q1=np.nanmean(q[:, 0]) * 1e4, q3=np.nanmean(q[:, 2]) * 1e4,
               q5=np.nanmean(q[:, N_Q - 1]) * 1e4, pool=np.nanmean(pool) * 1e4,
               spread=b["mean"] * 1e4, lo=b["lo"] * 1e4, hi=b["hi"] * 1e4,
               t=b["t"], se=b["se"] * 1e4,
               q5_excess=np.nanmean(q[:, N_Q - 1] - pool) * 1e4,
               half1=float(np.nanmean(spread[idx[:half]])) * 1e4,
               half2=float(np.nanmean(spread[idx[half:]])) * 1e4,
               ph_min=float(np.nanmin(ph)) * 1e4, ph_max=float(np.nanmax(ph)) * 1e4,
               ph_wrong=int((ph < 0).sum()), ph_n=len(ph))
    if beta is not None:
        qb, _, _ = bucket_means(lab, beta)
        for qi in range(N_Q):
            row[f"beta_q{qi + 1}"] = float(np.nanmean(qb[:, qi]))
    if mkt_fwd is not None:
        reg = nw_ols(spread, mkt_fwd, lags=2 * h)
        row["ls_beta"] = reg["beta"]
        row["ls_alpha"] = reg["alpha"] * (252 / h) * 100
        row["ls_t_alpha"] = reg["t_alpha"]
    if cost is not None:
        qc, _, _ = bucket_means(lab, cost)
        row["cost_q1"] = float(np.nanmean(qc[:, 0])) * 1e4
        row["cost_q5"] = float(np.nanmean(qc[:, N_Q - 1])) * 1e4
        row["spread_net"] = row["spread"] - row["cost_q1"] - row["cost_q5"]
    return row, lab, spread


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def random_quintile_control(lab: np.ndarray, fwd: np.ndarray,
                            rng: np.random.Generator, reps: int = CTRL_REPS):
    """CONTROL (b): same eligible pool, same bucket sizes, labels permuted
    inside each session. Expectation exactly zero; the draws buy the SCALE of
    the noise (Rule 10)."""
    out = np.empty(reps)
    for r in range(reps):
        p = lab.copy()
        for i in range(p.shape[0]):
            v = p[i]
            m = v >= 0
            if m.any():
                v[m] = rng.permutation(v[m])
        q, _, _ = bucket_means(p, fwd)
        out[r] = np.nanmean(spread_of(q))
    return out


def placebo_control(sig: np.ndarray, elig: np.ndarray, fwd: np.ndarray,
                    rng: np.random.Generator, reps: int = PLACEBO_REPS):
    """CONTROL (c): each symbol permanently assigned ANOTHER symbol's
    illiquidity series. The right null for a persistent characteristic - the
    null book keeps the real one's autocorrelation and only the stock-to-signal
    pairing is broken (Rule 14)."""
    out = np.empty(reps)
    n_s = sig.shape[1]
    for r in range(reps):
        perm = rng.permutation(n_s)
        lab = quintile_labels(sig[:, perm], elig, rng, min_elig=MIN_ELIGIBLE)
        q, _, _ = bucket_means(lab, fwd)
        out[r] = np.nanmean(spread_of(q))
    return out


# --------------------------------------------------------------------------
# the engine, with and without its own gate
# --------------------------------------------------------------------------

def engine_gate_test(bars: dict, cs_panel: np.ndarray, dv20: np.ndarray,
                     cols: list[str], keep: list[str], gates=GATES,
                     n_picks: int = N_PICKS, step: int = STRIDE) -> list[dict]:
    """Replay the SHIPPED v5 engine at several values of config.MIN_DOLLAR_VOL.

    `signals.composite_at` reads config.MIN_DOLLAR_VOL at call time, so the
    gate is swapped by setting that module-level constant and restoring it -
    the pipeline stays bit-identical to the live scan and to
    scout/backtest.py's v5 row, which is the whole point: a re-implementation
    would answer a different question.

    Costs are charged per pick as its OWN Corwin-Schultz spread at the entry
    date (one round trip), not a flat rate."""
    from . import backtest, signals
    o = bars["open"][keep]
    c = bars["close"][keep]
    v = bars["volume"][keep]
    idx = c.index
    h = config.HORIZON_TDAYS
    frames = signals.feature_frames(o, c, v)
    colpos = {s: j for j, s in enumerate(cols)}
    positions = list(range(270, len(idx) - h - 1, step))
    spy = c[MARKET]
    out = []
    saved = config.MIN_DOLLAR_VOL
    try:
        for gate in gates:
            # gate < 0 is the DISCARDED POOL: the engine's own score, ranked
            # with the gate off, then restricted to the names the shipped gate
            # deletes. Not bit-identical (the cross-sectional percentiles are
            # taken over the full pool, as the live engine takes them), which
            # is the point: it asks what the engine would have bought inside
            # the set it currently refuses to look at.
            config.MIN_DOLLAR_VOL = 0.0 if gate < 0 else gate
            rows = []
            for pos in positions:
                ts = idx[pos]
                snap = signals.composite_at(frames, ts).drop(index=[MARKET],
                                                             errors="ignore")
                if gate < 0:
                    snap = snap[snap["dvol20"] < -gate]
                if len(snap) < MIN_ELIGIBLE:
                    continue
                top = list(snap.index[:n_picks])
                oc = backtest.window_outcomes(c, pos, top, h)
                picks = [(s, oc[s]) for s in top if s in oc]
                if not picks:
                    continue
                spy_r = float(spy.iloc[pos + h] / spy.iloc[pos] - 1) \
                    if pos + h < len(idx) else np.nan
                for s, p in picks:
                    j = colpos[s]
                    rows.append(dict(
                        gate=gate, pos=pos, date=str(ts.date()), sym=s,
                        pool=len(snap), end=p["end"], mx=p["max"], hit=p["hit"],
                        hit10=p["hit10"], dip=p["dip_first"],
                        cs=float(cs_panel[pos, j]), dv=float(dv20[pos, j]),
                        spy=spy_r))
            out.extend(rows)
    finally:
        config.MIN_DOLLAR_VOL = saved
    return out


def summarise_gate(rows: pd.DataFrame, gate: float, seg: dict,
                   half: str = "all") -> dict:
    r = rows[rows["gate"] == gate]
    if half != "all":
        ds = sorted(r["pos"].unique())
        cut = ds[len(ds) // 2]
        r = r[r["pos"] < cut] if half == "h1" else r[r["pos"] >= cut]
    if r.empty:
        return {}
    per_date = r.groupby("pos").agg(end=("end", "mean"), cs=("cs", "mean"),
                                    spy=("spy", "mean"))
    net = per_date["end"] - per_date["cs"]
    return dict(
        gate_musd=gate / 1e6, half=half, dates=int(r["pos"].nunique()),
        picks=int(len(r)), pool=float(r["pool"].mean()),
        below_10m_pct=100 * float((r["dv"] < 10e6).mean()),
        hit_pct=100 * float(r["hit"].mean()),
        p10_pct=100 * float(r["hit10"].mean()),
        dip_pct=100 * float(r["dip"].mean()),
        mean_peak_pct=100 * float(np.minimum(r["mx"], 0.50).mean()),
        med_dv_musd=float(r["dv"].median()) / 1e6,
        med_cs_bps=1e4 * float(r["cs"].median()),
        gross_pct=100 * float(per_date["end"].mean()),
        cost_pct=100 * float(per_date["cs"].mean()),
        net_pct=100 * float(net.mean()),
        spy_pct=100 * float(per_date["spy"].mean()),
        beat_spy_pct=100 * float((per_date["end"] > per_date["spy"]).mean()),
        small_share_pct=100 * float(
            r["sym"].map(lambda s: seg.get(s, "large") == "small").mean()),
        mid_share_pct=100 * float(
            r["sym"].map(lambda s: seg.get(s, "large") == "mid").mean()))


# --------------------------------------------------------------------------
# offline selftest
# --------------------------------------------------------------------------

def selftest() -> int:
    rng = np.random.default_rng(0)
    fails = 0

    def check(name, ok, detail=""):
        nonlocal fails
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
        if not ok:
            fails += 1

    # 1. Corwin-Schultz recovers a PLANTED spread from a simulated tape ------
    n_d, n_s, planted = 4000, 40, 0.01
    sig_d = 0.02
    mid = 100 * np.exp(np.cumsum(rng.normal(0, sig_d, size=(n_d, n_s)), axis=0))
    # 200 trades a day at the plated half-spread, high/low of the traded prices
    hi = np.empty((n_d, n_s)); lo = np.empty((n_d, n_s)); cl = np.empty((n_d, n_s))
    for i in range(n_d):
        # within-day random walk of 40 steps around the day's midpoint level
        steps = rng.normal(0, sig_d / math.sqrt(40), size=(40, n_s))
        path = mid[i] * np.exp(np.cumsum(steps, axis=0))
        side = rng.choice([-1.0, 1.0], size=(40, n_s))
        traded = path * (1 + side * planted / 2)
        hi[i], lo[i], cl[i] = traded.max(0), traded.min(0), traded[-1]
    est = np.nanmean(cs_daily(hi, lo, cl))
    check("Corwin-Schultz recovers a planted 100 bps spread",
          0.6 * planted < est < 1.6 * planted, f"estimate {est * 1e4:.1f} bps")

    zero = cs_daily(np.full((50, 2), 10.0), np.full((50, 2), 10.0),
                    np.full((50, 2), 10.0))
    check("frozen quote (high == low) gives a ZERO spread, not a NaN",
          np.nanmax(np.abs(zero[1:])) < 1e-12)

    # 2. Amihud responds to dollar volume, not to the return alone ----------
    simple = np.tile(np.array([[0.01, 0.01]]), (60, 1))
    dv = np.tile(np.array([[1e6, 1e8]]), (60, 1))
    a = amihud_illiq(simple, dv, 21)
    check("Amihud is 100x larger for 100x less dollar volume",
          abs(a[-1, 0] / a[-1, 1] - 100) < 1e-3, f"ratio {a[-1, 0] / a[-1, 1]:.2f}")
    check("Amihud units are return per $M",
          abs(a[-1, 0] - 0.01 / 1.0) < 1e-6, f"{a[-1, 0]:.4f}")

    # 3. NO LOOKAHEAD: perturbing the future cannot move a past signal ------
    n_d, n_s = 400, 12
    px = 50 * np.exp(np.cumsum(rng.normal(0, 0.02, size=(n_d, n_s)), axis=0))
    h_, l_ = px * 1.01, px * 0.99
    vol = np.full((n_d, n_s), 1e6)
    smp = np.vstack([np.full((1, n_s), np.nan), px[1:] / px[:-1] - 1])
    T = 300
    px2, h2, l2, smp2 = px.copy(), h_.copy(), l_.copy(), smp.copy()
    px2[T + 1:] *= 3.0; h2[T + 1:] *= 3.0; l2[T + 1:] *= 3.0
    smp2[T + 1:] = 0.5
    a1 = amihud_illiq(smp, px * vol, 21)[:T + 1]
    a2 = amihud_illiq(smp2, px2 * vol, 21)[:T + 1]
    c1 = cs_spread(h_, l_, px, 21)[:T + 1]
    c2 = cs_spread(h2, l2, px2, 21)[:T + 1]
    check("Amihud through t is untouched by every bar after t",
          np.allclose(np.nan_to_num(a1), np.nan_to_num(a2)))
    check("Corwin-Schultz through t is untouched by every bar after t",
          np.allclose(np.nan_to_num(c1), np.nan_to_num(c2)))

    # 4. the forward shift is the shift it claims to be ---------------------
    log = np.log(px[1:] / px[:-1])
    log = np.vstack([np.full((1, n_s), np.nan), log])
    f = forward(log, 5)
    want = px[5 + 3] / px[3] - 1
    check("forward(log,5)[t] == close(t+5)/close(t) - 1",
          abs(f[3, 0] - want[0]) < 1e-10)

    # 5. the pipeline finds a PLANTED illiquidity premium, the control kills it
    n_d, n_s = 900, 200
    # a PERSISTENT characteristic, like real illiquidity - not iid noise, or
    # the placebo/permutation controls would be testing the wrong null
    sig = np.cumsum(rng.normal(0, .02, (n_d, n_s)), 0).astype(np.float32)
    elig = np.ones((n_d, n_s), bool)
    rank = pd.DataFrame(sig).rank(axis=1, pct=True).to_numpy()
    fwd = rng.normal(0, 0.05, (n_d, n_s)) + 0.02 * (rank > 0.8)
    lab = quintile_labels(sig, elig, np.random.default_rng(1), min_elig=10)
    q, _, _ = bucket_means(lab, fwd)
    got = np.nanmean(spread_of(q)) * 1e4
    check("planted +200 bps illiquidity premium is recovered",
          150 < got < 250, f"{got:.0f} bps")
    ctrl = random_quintile_control(lab, fwd, np.random.default_rng(2), reps=30)
    check("random-quintile control destroys it",
          abs(ctrl.mean() * 1e4) < 25, f"null {ctrl.mean() * 1e4:+.1f} bps")

    # 6. cost accounting: charging the gross spread nets to zero ------------
    cost = np.where(rank > 0.8, 0.02, 0.0)
    qc, _, _ = bucket_means(lab, cost)
    net = np.nanmean(spread_of(q)) - (np.nanmean(qc[:, 0]) + np.nanmean(qc[:, 4]))
    check("charging each leg its own measured spread nets the planted premium out",
          abs(net) * 1e4 < 25, f"net {net * 1e4:+.1f} bps")

    # 7. quintile labels are balanced and never look outside the pool -------
    lab2 = quintile_labels(sig, elig, np.random.default_rng(3), min_elig=10)
    cnt = np.array([(lab2 == k).sum(1) for k in range(N_Q)])
    check("quintiles are balanced within each session",
          int(cnt.max() - cnt.min()) <= 1)
    e2 = elig.copy(); e2[:, :100] = False
    lab3 = quintile_labels(sig, e2, np.random.default_rng(3), min_elig=10)
    check("ineligible names never receive a bucket", (lab3[:, :100] == -1).all())

    print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
    return 1 if fails else 0


# --------------------------------------------------------------------------

def _hdr(s: str) -> None:
    print(f"\n{'=' * 78}\n{s}\n{'=' * 78}")


def _fmt(v) -> str:
    return f"{v:9.2f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true", help="primary cells only")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _hdr("SELFTEST (offline, no keys, no network)")
        raise SystemExit(selftest())

    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res: dict = {"params": dict(windows=list(WINDOWS), horizons=list(HORIZONS),
                                hold=HOLD, stride=STRIDE, n_q=N_Q,
                                flat_cost_bps=COST_BPS, big_move=BIG_MOVE,
                                stale_run=STALE_RUN, min_obs=MIN_OBS,
                                gates=list(GATES), seed=SEED)}

    _hdr("H23 - is illiquidity priced, and does config.MIN_DOLLAR_VOL gate it away?")
    print("MECHANISM: an investor who cannot exit without moving the price has")
    print("bought an unhedgeable cost, and must be paid for it (Amihud 2002).")
    print("REGISTERED SIGN: Q5 (most ILLIQUID) minus Q1 (most liquid) POSITIVE.")
    print("THE DECIDING TEST: costs charged at each stock's OWN measured")
    print("Corwin-Schultz spread, never a flat 10 bps.")

    print("\nloading data ...")
    cb = clean_bars(refresh=args.refresh)
    close, high, low = cb["close"], cb["high"], cb["low"]
    volume, seg = cb["volume"], cb["segment"]
    cols = list(close.columns)
    colpos = {s: j for j, s in enumerate(cols)}
    n_d, n_s = close.shape
    simple, log = returns(close, guard=True)
    simple_ng, _ = returns(close, guard=False)
    print(f"  prices {n_d} sessions x {n_s} symbols  "
          f"{close.index[0].date()} .. {close.index[-1].date()}")

    # the extreme-print guard must reach the RANGE too, or a corrupted bar
    # survives in high/low after being removed from the return series
    bad_bar = np.abs(simple_ng) > BIG_MOVE
    hi_a, lo_a = high.to_numpy().copy(), low.to_numpy().copy()
    hi_a[bad_bar] = np.nan
    lo_a[bad_bar] = np.nan

    dvol_d = dollar_volume(close, volume)
    dv20 = median_dollar_vol(close, volume)
    live = np.isfinite(close.to_numpy())

    # universes -------------------------------------------------------------
    from . import pit
    sp1500 = np.zeros((n_d, n_s), bool)
    for j, s in enumerate(cols):
        if s in seg:
            sp1500[:, j] = True
    pit500 = np.zeros((n_d, n_s), bool)
    for i, ts in enumerate(close.index):
        for s in pit.members(ts):
            j = colpos.get(s)
            if j is not None:
                pit500[i, j] = True
    segarr = np.array([seg.get(s, "") for s in cols])
    print(f"  S&P 1500 (today's members, survivorship)   : "
          f"{int(sp1500[0].sum()):,} symbols")
    print(f"  point-in-time S&P 500 (each date's members): "
          f"mean {float((pit500 & live).sum(1).mean()):.0f} live names/session")

    _hdr("DATA HYGIENE (three guards, and what each one is worth here)")
    print(f"1. split repair (Alpaca corporate actions, |log ratio| > "
          f"{SPLIT_LOG_TOL}), applied to OPEN/HIGH/LOW/CLOSE and VOLUME:")
    print(f"   {len(cb['repaired'])} events - "
          f"{', '.join(cb['repaired'][:10])}{' ...' if len(cb['repaired']) > 10 else ''}")
    print(f"2. extreme-print guard |1-day| > {BIG_MOVE:.0%}: "
          f"{int(np.nansum(bad_bar)):,} bars removed from the return series AND "
          f"from the range,")
    print(f"   {int(bad_bar.any(0).sum())} symbols, "
          f"{int(np.nansum(bad_bar)) / max(int(live.sum()), 1) * 100:.4f}% "
          f"of the panel")
    print(f"3. stale-quote retirement (>= {STALE_RUN} identical closes): "
          f"{len(cb['killed'])} symbols")
    print(f"   {', '.join(f'{s} from {d}' for s, d, _ in cb['killed'][:8])}"
          f"{' ...' if len(cb['killed']) > 8 else ''}")
    print("   THIS ONE IS NOT COSMETIC HERE: a frozen quote has |r| = 0 and")
    print("   high == low, so Amihud AND Corwin-Schultz both score it as the")
    print("   most liquid stock in the market, paying 0.00% forever.")
    res["data"] = dict(
        start=str(close.index[0].date()), end=str(close.index[-1].date()),
        n_sessions=int(n_d), n_symbols=int(n_s),
        live_symbol_sessions=int(live.sum()),
        splits_repaired=cb["repaired"],
        extreme_bars_removed=int(np.nansum(bad_bar)),
        stale_retired=[[s, d] for s, d, _ in cb["killed"]],
        sp1500_symbols=int(sp1500[0].sum()),
        pit500_mean_live=float((pit500 & live).sum(1).mean()))

    # signals ---------------------------------------------------------------
    print("\nbuilding signals ...")
    sig: dict[tuple[str, int], np.ndarray] = {}
    for w in WINDOWS:
        sig[("amihud", w)] = amihud_illiq(simple, dvol_d, w)
        sig[("cs", w)] = cs_spread(hi_a, lo_a, close.to_numpy(), w)
        sig[("invdv", w)] = (-pd.DataFrame(dvol_d).rolling(w, min_periods=MIN_OBS)
                             .median().to_numpy()).astype(np.float32)
    cs_cost = sig[("cs", PRIMARY_W)].astype("float64")   # per-name round trip
    cs_neg = cs_spread(hi_a, lo_a, close.to_numpy(), PRIMARY_W,
                       zero_negatives=False)
    fwd = {h: forward(log, h) for h in HORIZONS}
    fwd_part = {h: forward_partial(close, log, h)[0] for h in HORIZONS}
    mkt_fwd = {h: fwd[h][:, colpos[MARKET]] for h in HORIZONS}
    beta21 = None
    # rolling 252-session SPY beta, for Rule 13's quintile beta profile
    mkt_log = log[:, colpos[MARKET]]
    w_b = 252
    Sy = pd.DataFrame(log).rolling(w_b, min_periods=w_b).sum().to_numpy()
    Sx = pd.Series(mkt_log).rolling(w_b, min_periods=w_b).sum().to_numpy()[:, None]
    Sxx = pd.Series(mkt_log * mkt_log).rolling(w_b, min_periods=w_b).sum().to_numpy()[:, None]
    Sxy = pd.DataFrame(log * mkt_log[:, None]).rolling(w_b, min_periods=w_b).sum().to_numpy()
    with np.errstate(invalid="ignore"):
        beta21 = ((Sxy - Sx * Sy / w_b) / (Sxx - Sx * Sx / w_b)).astype(np.float32)

    def elig_of(univ, h, w, s="amihud", liquid=None, illiquid_only=False):
        e = (univ & live & np.isfinite(sig[(s, w)]) & np.isfinite(sig[("cs", w)])
             & np.isfinite(fwd[h]) & np.isfinite(dv20))
        e[:, colpos[MARKET]] = False               # SPY is a benchmark, not a name
        if liquid is not None:
            e = e & ((dv20 >= liquid) if not illiquid_only else (dv20 < liquid))
        return e

    _hdr("SAMPLE, AND THE EFFECTIVE INDEPENDENT SAMPLE")
    e = elig_of(sp1500, PRIMARY_H, PRIMARY_W)
    print(f"date range                                : "
          f"{close.index[0].date()} .. {close.index[-1].date()}  ({n_d:,} sessions)")
    print(f"symbol-sessions with a price              : {int(live.sum()):>12,}")
    print(f"eligible at the primary cell (W=21, h=42) : {int(e.sum()):>12,}")
    print(f"mean names in the cross-section           : "
          f"{float(e.sum(1)[e.sum(1) >= MIN_ELIGIBLE].mean()):>12.0f}")
    print(f"\nTHE EFFECTIVE INDEPENDENT SAMPLE IS NOT THAT NUMBER. The cross-section")
    print(f"is collapsed to ONE spread per session before any statistic, so n is at")
    print(f"most the ~{n_d - PRIMARY_W - PRIMARY_H:,} usable sessions; {PRIMARY_H}"
          f"-session holds overlap, so the honestly")
    print(f"independent count is ~{(n_d - PRIMARY_W - PRIMARY_H) // PRIMARY_H} "
          f"non-overlapping windows PER entry phase, of which there")
    print(f"are {PRIMARY_H}. Every CI below is a moving-block bootstrap with block "
          f"length h,")
    print("and every headline is swept across all h phases (Rule 9).")

    # ------------------------------------------- the mutual implementation check
    _hdr("DO THE TWO MEASURES AGREE? (the implementation check, before any return)")
    print("Amihud uses returns and dollar volume; Corwin-Schultz uses the daily")
    print("range and neither. Disjoint arithmetic on the same latent quantity.\n")
    a_p, c_p = sig[("amihud", PRIMARY_W)], sig[("cs", PRIMARY_W)]
    ra = pd.DataFrame(np.where(e, a_p, np.nan)).rank(axis=1, pct=True)
    rc = pd.DataFrame(np.where(e, c_p, np.nan)).rank(axis=1, pct=True)
    rd = pd.DataFrame(np.where(e, -dv20, np.nan)).rank(axis=1, pct=True)
    rows = np.flatnonzero(e.sum(1) >= MIN_ELIGIBLE)
    def _xcorr(x, y):
        v = [np.corrcoef(x.iloc[i].dropna(),
                         y.iloc[i].reindex(x.iloc[i].dropna().index))[0, 1]
             for i in rows[::21]]
        return float(np.nanmean(v))
    rho_ac = _xcorr(ra, rc)
    rho_ad = _xcorr(ra, rd)
    rho_cd = _xcorr(rc, rd)
    print(f"  mean within-date SPEARMAN rank correlation, {len(rows[::21])} dates:")
    print(f"    Amihud vs Corwin-Schultz spread : {rho_ac:+.3f}")
    print(f"    Amihud vs -dollar volume        : {rho_ad:+.3f}")
    print(f"    Corwin-Schultz vs -dollar volume: {rho_cd:+.3f}")
    lev = float(np.nanmedian(np.where(e, c_p, np.nan))) * 1e4
    lev5 = [float(np.nanmedian(np.where(e & (rd.to_numpy() > k / 5)
                                        & (rd.to_numpy() <= (k + 1) / 5),
                                        c_p, np.nan))) * 1e4 for k in range(5)]
    print(f"\n  median Corwin-Schultz spread across the pool: {lev:.1f} bps")
    print("  by dollar-volume quintile (Q1 = most liquid): "
          + "  ".join(f"Q{k + 1} {v:.0f}" for k, v in enumerate(lev5)) + " bps")
    res["measures"] = dict(rho_amihud_cs=rho_ac, rho_amihud_dv=rho_ad,
                           rho_cs_dv=rho_cd, median_cs_bps=lev,
                           cs_bps_by_dv_quintile=lev5)

    # ------------------------------------------------------------ control a
    _hdr("CONTROL (a) POSITIVE: is the sort alive at all?")
    print("If today's illiquidity did not forecast the next 42 sessions'")
    print("illiquidity, a null return result would be evidence about the")
    print("pipeline, not about the hypothesis.\n")
    res["positive_control"] = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        illiq_d = np.abs(simple) / (dvol_d / 1e6)
    illiq_d[~np.isfinite(illiq_d)] = np.nan
    cs_d_raw = cs_daily(hi_a, lo_a, close.to_numpy())
    fwd_illiq = forward_mean(illiq_d, PRIMARY_H)
    fwd_cs = forward_mean(np.maximum(cs_d_raw, 0.0), PRIMARY_H)
    for nm, dep in (("amihud", fwd_illiq), ("cs", fwd_cs)):
        lab_n = quintile_labels(sig[(nm, PRIMARY_W)], e,
                                np.random.default_rng(SEED + PRIMARY_H),
                                min_elig=MIN_ELIGIBLE)
        qs, _, _ = bucket_means(lab_n, sig[(nm, PRIMARY_W)])
        qv, poolv, _ = bucket_means(lab_n, dep)
        unit = "bps of price per $M traded" if nm == "amihud" else "bps"
        print(f"  {nm:<7} signal at t          "
              + "  ".join(f"Q{i + 1} {np.nanmean(qs[:, i]) * 1e4:8.2f}"
                          for i in range(N_Q)))
        print(f"  {nm:<7} realised t+1..t+{PRIMARY_H}  "
              + "  ".join(f"Q{i + 1} {np.nanmean(qv[:, i]) * 1e4:8.2f}"
                          for i in range(N_Q))
              + f"  ({unit})")
        res["positive_control"][nm] = dict(
            signal=[float(np.nanmean(qs[:, i]) * 1e4) for i in range(N_Q)],
            forward=[float(np.nanmean(qv[:, i]) * 1e4) for i in range(N_Q)],
            pool_forward=float(np.nanmean(poolv) * 1e4))
    print("\n  Both sorts forecast their own future values monotonically, so the")
    print("  pipeline is alive. Note the LEVEL of the Corwin-Schultz estimate")
    print("  below - it is the thing the cost model has to lean on.")

    # ------------------------------------------------------------- primary
    _hdr(f"PRIMARY: {PRIMARY_SIG} W={PRIMARY_W}, h={PRIMARY_H}, S&P 1500, all guards")
    print("Q5 = MOST ILLIQUID. Registered sign POSITIVE. Returns are bps per")
    print("42-session hold; CI = circular moving-block bootstrap (block = h),")
    print("clustered by date. cost_q* = that bucket's own measured round-trip")
    print("Corwin-Schultz spread; spread_net charges BOTH legs theirs.\n")
    row, lab_pri, spread_pri = run_cell(
        sig[(PRIMARY_SIG, PRIMARY_W)], e, fwd[PRIMARY_H], PRIMARY_H, rng,
        beta=beta21, mkt_fwd=mkt_fwd[PRIMARY_H], cost=cs_cost,
        label=f"{PRIMARY_SIG} W{PRIMARY_W}")
    pri = pd.DataFrame([row])
    print(pri[["n_dates", "n_names", "q1", "q3", "q5", "pool", "spread", "lo",
               "hi", "t", "half1", "half2"]].to_string(index=False,
                                                       float_format=_fmt))
    print(pri[["cost_q1", "cost_q5", "spread_net", "q5_excess", "ph_min",
               "ph_max", "ph_wrong", "ph_n"]].to_string(index=False,
                                                        float_format=_fmt))
    print("\nquintile SPY betas (Rule 13 - illiquid means small means high beta?):")
    print("  " + "   ".join(f"Q{i + 1} {row[f'beta_q{i + 1}']:.2f}" for i in range(N_Q)))
    print(f"\nthe DOLLAR-NEUTRAL Q5-Q1 book on SPY over the same {PRIMARY_H}-session")
    print(f"windows: beta {row['ls_beta']:+.2f}, alpha {row['ls_alpha']:+.2f}%/yr, "
          f"Newey-West t = {row['ls_t_alpha']:+.2f}")
    res["primary"] = row

    # -------------------------------- what the buckets ARE, and what CS is worth
    _hdr("WHAT IS ACTUALLY IN THE BUCKETS - capacity, and the cost estimator")
    qdv, _, _ = bucket_means(lab_pri, dv20)
    qcs_b, _, _ = bucket_means(lab_pri, cs_cost)
    qgate, _, _ = bucket_means(lab_pri, (dv20 < config.MIN_DOLLAR_VOL).astype(float))
    med_dv = [float(np.nanmedian(np.where(lab_pri == k, dv20, np.nan))) / 1e6
              for k in range(N_Q)]
    print("  by Amihud quintile (Q5 = most illiquid), medians over the panel:")
    print("    20d median dollar volume ($M) "
          + "  ".join(f"Q{k + 1} {v:9.2f}" for k, v in enumerate(med_dv)))
    print("    Corwin-Schultz spread (bps)   "
          + "  ".join(f"Q{k + 1} {np.nanmean(qcs_b[:, k]) * 1e4:9.2f}"
                      for k in range(N_Q)))
    print("    share BELOW the $10M gate (%) "
          + "  ".join(f"Q{k + 1} {np.nanmean(qgate[:, k]) * 100:9.1f}"
                      for k in range(N_Q)))
    print("    a $10,000 position is this %  "
          + "  ".join(f"Q{k + 1} {1e4 / (v * 1e6) * 100:9.3f}"
                      for k, v in enumerate(med_dv)))
    print("    of the median name's DAILY dollar volume.")
    print(f"\n  THE CAPACITY POINT, MEASURED: the most illiquid quintile of the")
    print(f"  S&P 1500 still trades ${med_dv[N_Q - 1]:.1f}M a day at the median. A "
          f"$10k order is")
    print(f"  {1e4 / (med_dv[N_Q - 1] * 1e6) * 100:.3f}% of that. Capacity is not "
          f"this user's binding constraint;")
    print(f"  it is every institution's, which is the asymmetry the hypothesis rests on.")

    print(f"\n  THE COST ESTIMATOR'S CREDIBILITY, stated before it is used:")
    dv_range = med_dv[N_Q - 1] / max(med_dv[0], 1e-9)
    cs_range = float(np.nanmean(qcs_b[:, N_Q - 1]) / np.nanmean(qcs_b[:, 0]))
    spy_cs = float(np.nanmean(sig[("cs", PRIMARY_W)][:, colpos[MARKET]]
                              [np.isfinite(sig[("cs", PRIMARY_W)][:, colpos[MARKET]])]))
    mega = [s for s in ("AAPL", "MSFT", "JPM", "XOM") if s in colpos]
    mega_cs = float(np.nanmean([np.nanmean(sig[("cs", PRIMARY_W)][:, colpos[s]])
                                for s in mega]))
    print(f"    dollar volume ranges {1 / dv_range:.0f}x across the sort "
          f"(Q1/Q5), Corwin-Schultz only {cs_range:.2f}x.")
    print(f"    Corwin-Schultz says SPY costs {spy_cs * 1e4:.1f} bps and "
          f"{'/'.join(mega)} {mega_cs * 1e4:.1f} bps,")
    print(f"    against this repo's own 5-10 bps large-cap standard and SPY's "
          f"real sub-1 bp spread.")
    print("    So the estimator's LEVEL is inflated (censoring negative two-day")
    print("    estimates at zero is a one-sided bias, and daily-range noise")
    print("    survives the differencing) and its cross-sectional DISCRIMINATION")
    print("    is far too narrow. Charging it as the cost is therefore PUNITIVE")
    print("    on the liquid leg and probably too GENEROUS on the illiquid one.")
    print("    That is why the break-even cost below, not the net spread, is the")
    print("    number to carry away.")
    res["buckets"] = dict(
        med_dollar_vol_musd=med_dv,
        cs_bps=[float(np.nanmean(qcs_b[:, k]) * 1e4) for k in range(N_Q)],
        below_gate_pct=[float(np.nanmean(qgate[:, k]) * 100) for k in range(N_Q)],
        dv_range_q1_over_q5=float(1 / dv_range), cs_range_q5_over_q1=cs_range,
        cs_spy_bps=spy_cs * 1e4, cs_megacap_bps=mega_cs * 1e4)

    # ------------------------------------------------------ controls b, c
    _hdr("CONTROLS (b) RANDOM QUINTILE and (c) SYMBOL-PAIRING PLACEBO")
    ctrl = random_quintile_control(lab_pri, fwd[PRIMARY_H], rng, CTRL_REPS)
    plac = placebo_control(sig[(PRIMARY_SIG, PRIMARY_W)], e, fwd[PRIMARY_H],
                           rng, PLACEBO_REPS)
    print(f"  real Q5-Q1                          {row['spread']:+9.2f} bps  "
          f"(block-bootstrap SE {row['se']:.2f})")
    print(f"  random quintiles ({CTRL_REPS} draws)          "
          f"{ctrl.mean() * 1e4:+9.2f} +/- {ctrl.std() * 1e4:.2f} bps")
    print(f"  symbol-pairing placebo ({PLACEBO_REPS} draws)   "
          f"{plac.mean() * 1e4:+9.2f} +/- {plac.std() * 1e4:.2f} bps")
    se_ratio = (plac.std() * 1e4) / max(row["se"], 1e-9)
    print(f"\n  Rule 14 check - placebo SD / block-bootstrap SE = {se_ratio:.2f}.")
    print("  A ratio far below 1 means a permutation p-value would be")
    print("  anti-conservative and must not be quoted on its own.")
    res["controls"] = dict(
        random_mean_bps=float(ctrl.mean() * 1e4),
        random_sd_bps=float(ctrl.std() * 1e4),
        placebo_mean_bps=float(plac.mean() * 1e4),
        placebo_sd_bps=float(plac.std() * 1e4),
        placebo_se_ratio=float(se_ratio))

    # ------------------------------------------------- all registered cells
    _hdr("ALL REGISTERED CELLS")
    print("universe x signal x lookback x horizon. Spread = Q5 - Q1 in bps per")
    print("hold; spread_net charges each leg its own Corwin-Schultz spread.\n")
    cells = []
    universes = [("sp1500", sp1500), ("pit500", pit500)]
    if args.quick:
        universes = universes[:1]
    for uname, umask in universes:
        for s in SIGNALS:
            for w in (WINDOWS if not args.quick else (PRIMARY_W,)):
                for h in (HORIZONS if not args.quick else (PRIMARY_H,)):
                    ee = elig_of(umask, h, w, s)
                    if ee.sum() == 0:
                        continue
                    r, _, _ = run_cell(sig[(s, w)], ee, fwd[h], h, rng,
                                       beta=beta21, mkt_fwd=mkt_fwd[h],
                                       cost=cs_cost,
                                       label=f"{uname} {s} W{w}")
                    r["universe"], r["signal"], r["w"] = uname, s, w
                    cells.append(r)
    cdf = pd.DataFrame(cells)
    print(cdf[["universe", "signal", "w", "h", "n_dates", "n_names", "q1", "q5",
               "spread", "lo", "hi", "t", "spread_net", "half1", "half2",
               "ls_beta", "ls_alpha", "ls_t_alpha"]]
          .to_string(index=False, float_format=_fmt))
    wrong = int((cdf["spread"] < 0).sum())
    flips = int(((cdf["half1"] > 0) != (cdf["half2"] > 0)).sum())
    print(f"\n  cells with the registered sign WRONG : {wrong}/{len(cdf)}")
    print(f"  cells whose two halves DISAGREE      : {flips}/{len(cdf)}")
    print(f"  cells still positive after per-stock costs: "
          f"{int((cdf['spread_net'] > 0).sum())}/{len(cdf)}")
    res["cells"] = cdf.to_dict("records")

    # ------------------------------------------------- robustness variants
    _hdr("REGISTERED ROBUSTNESS VARIANTS")
    var = []
    ee = elig_of(sp1500, PRIMARY_H, PRIMARY_W)
    for nm, s_arr, el in (
            ("cs, negatives NOT zeroed", cs_neg, ee),
            ("delisting-truncated forward return", sig[(PRIMARY_SIG, PRIMARY_W)], ee),
            ("inside the $10M gate only", sig[(PRIMARY_SIG, PRIMARY_W)],
             elig_of(sp1500, PRIMARY_H, PRIMARY_W, liquid=config.MIN_DOLLAR_VOL)),
            ("below the $10M gate only", sig[(PRIMARY_SIG, PRIMARY_W)],
             elig_of(sp1500, PRIMARY_H, PRIMARY_W, liquid=config.MIN_DOLLAR_VOL,
                     illiquid_only=True)),
            ("large segment only", sig[(PRIMARY_SIG, PRIMARY_W)],
             ee & (segarr == "large")[None, :]),
            ("mid segment only", sig[(PRIMARY_SIG, PRIMARY_W)],
             ee & (segarr == "mid")[None, :]),
            ("small segment only", sig[(PRIMARY_SIG, PRIMARY_W)],
             ee & (segarr == "small")[None, :]),
    ):
        f_use = fwd_part[PRIMARY_H] if nm.startswith("delisting") else fwd[PRIMARY_H]
        if el.sum() == 0:
            continue
        r, _, _ = run_cell(s_arr, el, f_use, PRIMARY_H, rng, beta=beta21,
                           mkt_fwd=mkt_fwd[PRIMARY_H], cost=cs_cost, label=nm)
        var.append(r)
    vdf = pd.DataFrame(var)
    print(vdf[["cell", "n_dates", "n_names", "q1", "q5", "spread", "lo", "hi",
               "t", "spread_net", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))
    res["variants"] = vdf.to_dict("records")

    # guard sensitivity: what each hygiene rule is worth ---------------------
    _hdr("WHAT EACH DATA GUARD IS WORTH (each turned off once)")
    guard_rows = []
    close_stale = cb["close_stale"]
    smp_s, log_s = returns(close_stale, guard=True)
    dv_s = dollar_volume(close_stale, cb["volume_stale"])
    a_stale = amihud_illiq(smp_s, dv_s, PRIMARY_W)
    live_s = np.isfinite(close_stale.to_numpy())
    f_stale = forward(log_s, PRIMARY_H)
    e_stale = (sp1500 & live_s & np.isfinite(a_stale) & np.isfinite(f_stale))
    e_stale[:, colpos[MARKET]] = False
    r_s, _, _ = run_cell(a_stale, e_stale, f_stale, PRIMARY_H, rng,
                         label="stale-quote retirement OFF")
    guard_rows.append(r_s)
    a_ng = amihud_illiq(simple_ng, dvol_d, PRIMARY_W)
    e_ng = elig_of(sp1500, PRIMARY_H, PRIMARY_W)
    r_n, _, _ = run_cell(a_ng, e_ng, fwd[PRIMARY_H], PRIMARY_H, rng,
                         label="extreme-print guard OFF")
    guard_rows.append(r_n)
    gdf = pd.DataFrame(guard_rows)
    print(f"  primary (all guards on)          {row['spread']:+9.2f} bps  "
          f"t {row['t']:+.2f}")
    for _, g in gdf.iterrows():
        print(f"  {g['cell']:<32} {g['spread']:+9.2f} bps  t {g['t']:+.2f}")
    res["guards"] = gdf.to_dict("records")

    # ---------------------------------------------------- the tradeable book
    _hdr("THE TRADEABLE BOOK: 42-session hold, monthly rebalance, equal weight")
    print("Pooled over all 21 entry phases (Rule 9). Costs are charged three")
    print("ways: FLAT 10 bps (what a large-cap study would charge and the")
    print("error this lab exists to avoid), each bucket's OWN measured")
    print("Corwin-Schultz round trip, and half of it (retail price")
    print("improvement on a small order).\n")
    spy_daily = simple[:, colpos[MARKET]]
    sb = perf(spy_daily, spy_daily)
    books = {}
    rows_b = []
    lab_n = quintile_labels(sig[(PRIMARY_SIG, PRIMARY_W)], e,
                            np.random.default_rng(SEED + PRIMARY_H),
                            min_elig=MIN_ELIGIBLE)
    qcs, _, _ = bucket_means(lab_n, cs_cost)
    for qi in range(N_Q):
        r = ladder(sub_portfolios(lab_n, qi, simple), STRIDE)
        to = book_turnover(lab_n, qi)
        own = float(np.nanmean(qcs[:, qi]))
        gross = perf(r, spy_daily)
        net_flat = perf(r, spy_daily, cost_yr=to * COST_BPS / 1e4)
        net_own = perf(r, spy_daily, cost_yr=to * own)
        net_half = perf(r, spy_daily, cost_yr=to * own / 2)
        idxr = np.flatnonzero(np.isfinite(r))
        hf = len(idxr) // 2
        rows_b.append(dict(
            bucket=f"Q{qi + 1}", cs_bps=own * 1e4, turnover=to,
            gross=gross["ann_ret"], net_flat=net_flat["ann_ret"],
            net_own=net_own["ann_ret"], net_half=net_half["ann_ret"],
            vol=gross["ann_vol"], sharpe_own=net_own["sharpe"],
            maxdd=gross["maxdd"], beta=gross["beta"],
            alpha_own=net_own["alpha"], t_alpha=net_own["t_alpha"],
            sh_h1=perf(r[idxr[:hf]], spy_daily[idxr[:hf]], to * own)["sharpe"],
            sh_h2=perf(r[idxr[hf:]], spy_daily[idxr[hf:]], to * own)["sharpe"]))
        books[qi] = r
    bdf = pd.DataFrame(rows_b)
    print(bdf.to_string(index=False, float_format=_fmt))
    ls = books[N_Q - 1] - books[0]
    to_ls = book_turnover(lab_n, N_Q - 1) + book_turnover(lab_n, 0)
    own_ls = (float(np.nanmean(qcs[:, N_Q - 1])) * book_turnover(lab_n, N_Q - 1)
              + float(np.nanmean(qcs[:, 0])) * book_turnover(lab_n, 0))
    g_ls = perf(ls, spy_daily)
    n_ls = perf(ls, spy_daily, cost_yr=own_ls)
    be = g_ls["ann_ret"] / 100 / max(to_ls, 1e-9) * 1e4
    print(f"\n  Q5-Q1 dollar-neutral: gross {g_ls['ann_ret']:+.2f}%/yr, "
          f"net of measured spreads {n_ls['ann_ret']:+.2f}%/yr,")
    print(f"     beta {g_ls['beta']:+.2f}, alpha {n_ls['alpha']:+.2f}%/yr "
          f"(NW t {n_ls['t_alpha']:+.2f}), turnover {to_ls:.2f}x/yr one-way")
    print(f"     BREAK-EVEN round-trip cost {be:.1f} bps against a MEASURED "
          f"{(own_ls / max(to_ls, 1e-9)) * 1e4:.1f} bps")
    print(f"\n  BREAK-EVEN, the number to carry away (it needs no view on the")
    print(f"  Corwin-Schultz level). The Q5-Q1 spread of "
          f"{row['spread']:.1f} bps per {PRIMARY_H}-session hold")
    print(f"  survives any per-leg round-trip cost below "
          f"{row['spread'] / 2:.1f} bps if both legs turn over")
    print(f"  completely each hold, and below {row['spread'] / (2 * to_ls / (252 / PRIMARY_H)):.1f}"
          f" bps at the MEASURED turnover of "
          f"{to_ls / (252 / PRIMARY_H):.2f} legs/hold.")
    print(f"  The long-only Q5 book alone: {bdf.loc[N_Q - 1, 'gross']:+.2f}%/yr gross, "
          f"turnover {bdf.loc[N_Q - 1, 'turnover']:.2f}x/yr one-way, so it")
    print(f"  break-evens against SPY's {sb['ann_ret']:+.2f}%/yr at "
          f"{max(bdf.loc[N_Q - 1, 'gross'] - sb['ann_ret'], 0) / 100 / max(bdf.loc[N_Q - 1, 'turnover'], 1e-9) * 1e4:.0f}"
          f" bps of round-trip cost.")
    res["books"] = dict(quintiles=bdf.to_dict("records"),
                        ls_gross_yr=float(g_ls["ann_ret"]),
                        ls_net_yr=float(n_ls["ann_ret"]),
                        ls_beta=float(g_ls["beta"]),
                        ls_alpha_yr=float(n_ls["alpha"]),
                        ls_t_alpha=float(n_ls["t_alpha"]),
                        ls_turnover=float(to_ls),
                        ls_breakeven_bps=float(be),
                        ls_measured_cost_bps=float(own_ls / max(to_ls, 1e-9) * 1e4))

    # the same book on point-in-time membership: the number the study turns on
    e_pit = elig_of(pit500, PRIMARY_H, PRIMARY_W)
    lab_pit = quintile_labels(sig[(PRIMARY_SIG, PRIMARY_W)], e_pit,
                              np.random.default_rng(SEED + PRIMARY_H),
                              min_elig=MIN_ELIGIBLE)
    qcs_p, _, _ = bucket_means(lab_pit, cs_cost)
    pit_rows = []
    for qi in (0, N_Q - 1):
        rp = ladder(sub_portfolios(lab_pit, qi, simple), STRIDE)
        top_ = book_turnover(lab_pit, qi)
        ownp = float(np.nanmean(qcs_p[:, qi]))
        gp = perf(rp, spy_daily)
        npf = perf(rp, spy_daily, cost_yr=top_ * ownp)
        ix = np.flatnonzero(np.isfinite(rp))
        hf2 = len(ix) // 2
        pit_rows.append(dict(
            bucket=f"pit Q{qi + 1}", cs_bps=ownp * 1e4, turnover=top_,
            gross=gp["ann_ret"], net_own=npf["ann_ret"], vol=gp["ann_vol"],
            sharpe_own=npf["sharpe"], maxdd=gp["maxdd"], beta=gp["beta"],
            alpha_own=npf["alpha"], t_alpha=npf["t_alpha"],
            sh_h1=perf(rp[ix[:hf2]], spy_daily[ix[:hf2]], top_ * ownp)["sharpe"],
            sh_h2=perf(rp[ix[hf2:]], spy_daily[ix[hf2:]], top_ * ownp)["sharpe"]))
    pdf = pd.DataFrame(pit_rows)
    print("\n  THE SAME BOOK ON POINT-IN-TIME S&P 500 MEMBERSHIP (control f):")
    print(pdf.to_string(index=False, float_format=_fmt))
    res["books_pit500"] = pdf.to_dict("records")

    sub_pool = sub_portfolios(np.where(e, 0, -1).astype(np.int8), 0, simple)
    pb = perf(ladder(sub_pool, STRIDE), spy_daily)
    sub_pool_p = sub_portfolios(np.where(e_pit, 0, -1).astype(np.int8), 0, simple)
    pbp = perf(ladder(sub_pool_p, STRIDE), spy_daily)
    print("\n  MATCHED BENCHMARKS (control d)")
    print(f"    equal-weight eligible pool : {pb['ann_ret']:+6.2f}%/yr  "
          f"vol {pb['ann_vol']:5.2f}%  Sharpe {pb['sharpe']:.2f}  "
          f"maxDD {pb['maxdd']:.1f}%")
    print(f"    same pool, point-in-time   : {pbp['ann_ret']:+6.2f}%/yr  "
          f"vol {pbp['ann_vol']:5.2f}%  Sharpe {pbp['sharpe']:.2f}  "
          f"maxDD {pbp['maxdd']:.1f}%")
    print(f"    SPY buy and hold           : {sb['ann_ret']:+6.2f}%/yr  "
          f"vol {sb['ann_vol']:5.2f}%  Sharpe {sb['sharpe']:.2f}  "
          f"maxDD {sb['maxdd']:.1f}%   "
          f"(rf={RF_SENSITIVITY:.0%}: "
          f"{(sb['ann_ret'] / 100 - RF_SENSITIVITY) / (sb['ann_vol'] / 100):.2f})")
    res["benchmarks"] = dict(equal_weight_pool=pb, equal_weight_pool_pit=pbp,
                             spy=sb)

    sub_q5 = sub_portfolios(lab_n, N_Q - 1, simple)
    ph_r = [perf(ladder(sub_q5, STRIDE, p), spy_daily) for p in range(STRIDE)]
    print(f"\n  LONG-ONLY Q5 across the {STRIDE} monthly entry schedules (Rule 9):")
    print(f"    return  min {min(x['ann_ret'] for x in ph_r):+.2f}%  "
          f"max {max(x['ann_ret'] for x in ph_r):+.2f}%  "
          f"pooled {bdf.loc[N_Q - 1, 'gross']:+.2f}%")
    print(f"    Sharpe  min {min(x['sharpe'] for x in ph_r):.2f}  "
          f"max {max(x['sharpe'] for x in ph_r):.2f}")
    from .growth import deflated_sharpe
    q5r = books[N_Q - 1]
    q5x = q5r[np.isfinite(q5r)] - (bdf.loc[N_Q - 1, "turnover"]
                                   * float(np.nanmean(qcs[:, N_Q - 1])) / 252)
    dsr = deflated_sharpe(float(q5x.mean() / q5x.std(ddof=1)), N_TRIALS,
                          len(q5x), skew=float(pd.Series(q5x).skew()),
                          kurtosis=float(pd.Series(q5x).kurt() + 3.0),
                          sr_benchmark=float(np.nanmean(spy_daily)
                                             / np.nanstd(spy_daily)))
    print(f"\n  DEFLATED SHARPE of the long-only Q5 book against SPY's own Sharpe,")
    print(f"  at this repo's running trial count N={N_TRIALS} "
          f"(RESEARCH-AGENDA rule 3): {dsr:.3f}")
    res["deflated_sharpe_q5"] = float(dsr)
    res["phase_sweep_q5"] = dict(
        ret_min=float(min(x["ann_ret"] for x in ph_r)),
        ret_max=float(max(x["ann_ret"] for x in ph_r)),
        sharpe_min=float(min(x["sharpe"] for x in ph_r)),
        sharpe_max=float(max(x["sharpe"] for x in ph_r)))

    # ------------------------------------------------ the gate, as a gate
    _hdr("THE DECISION: what would the ENGINE have earned WITHOUT the $10M gate?")
    print("The shipped v5 pipeline (signals.composite_at), replayed at four")
    print("settings of config.MIN_DOLLAR_VOL, monthly entries, 5 picks,")
    print("42-session hold - bit-identical to the live scan apart from the gate.")
    print("Costs are each pick's OWN Corwin-Schultz round trip at entry.\n")
    keep = [s for s in cols if s in seg or s == MARKET]
    grows = pd.DataFrame(engine_gate_test(cb, cs_cost, dv20, cols, keep))
    gsum = pd.DataFrame([summarise_gate(grows, g, seg, hf)
                         for g in GATES for hf in ("all", "h1", "h2")])
    gsum = gsum[gsum["dates"].notna()] if "dates" in gsum else gsum
    print("gate_musd 10 = shipped, 0 = no gate, -10 = ONLY the names the")
    print("shipped gate deletes. All returns are per 42-session window.\n")
    print(gsum[["gate_musd", "half", "dates", "picks", "pool", "med_dv_musd",
                "below_10m_pct", "med_cs_bps", "hit_pct", "gross_pct",
                "cost_pct", "net_pct", "spy_pct", "beat_spy_pct",
                "mean_peak_pct", "small_share_pct"]]
          .to_string(index=False, float_format=_fmt))
    res["gate_test"] = gsum.to_dict("records")

    RESULTS.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {RESULTS.name}   ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
