"""H18 — does the equity premium accrue overnight, and does the SHIPPED H4 rule survive?

MECHANISM (one sentence, before any number): the overnight window is a closed
market where inventory cannot be hedged and information accrues with no
continuous price, so whoever carries the position demands compensation and is
paid in the opening gap, while the intraday window is a continuous competitive
auction that pays for providing liquidity rather than for bearing risk —
Lou-Polk-Skouras (JFE 2019), Cliff-Cooper-Gulen (2008),
Hendershott-Livdan-Roesch (2020).

WHY IT MATTERS HERE. `scout/hypotheses.md` H4 — "enter at/near the CLOSE, never
the open" — is the only shipped rule in this repo with NO local test. It was
adopted from this literature on 2026-08-08 and shipped as a banner in
picks.xlsx. H18e/H18f below are its first honest test, and they are decisive
in a way the market-level rows are not: the close-vs-open entry difference on
identical picks is EXACTLY the first overnight return those picks earn, so the
rule lives or dies on whether momentum picks gap up more than the pool they
were drawn from.

DATA (US equities only; no crypto, options, futures, FX. SPY is a benchmark.)
  prices  scout/data.py daily SIP bars, adjustment=all, OPEN and CLOSE, for the
          120 most liquid S&P 500 members AS OF 2016-01-04 (the point-in-time
          panel scout/news_data.liquid_universe built; BRCM/CELG/EMC/TWX/ESRX/
          MON/AET/PXD are in, no post-2016 addition is) plus SPY.
          2016-01-04 .. 2026-08-07, 2664 sessions.
  price-only rerun with adjustment=split, to size how much of any overnight
          premium is simply the dividend — which lands in the overnight leg by
          construction, since the price drops on the ex-date open.

  Are these daily bars really the auction prints? Checked, not assumed:
  against scout/intraday.py's 5-minute session frames (regular session only,
  09:30-16:00 ET, split-repaired) over 2018-2026 the daily OPEN matches the
  first regular-session print to a median |log difference| of 3e-8 for
  SPY/JPM/XOM/PG and 1e-4 for MSFT, and the daily CLOSE sits ~1e-4 from the
  last continuous print, which is the closing auction — exactly the gap
  intraday.official_closes exists to explain. The daily tape is therefore the
  right instrument for this question, and it reaches back to 2016 where the
  minute cache starts in 2018. `--check-open` reruns that comparison.

SPLIT REPAIR IS ACTIVE AND IT MATTERS MORE HERE THAN ANYWHERE ELSE IN THE REPO
  An unapplied split is a fabricated -75% OVERNIGHT return: prev_close is
  pre-split, the ex-date open is post-split, so the entire error lands in the
  leg being measured. Alpaca's adjustment=all misses AAPL's 2020-08-31 4:1
  (484.24 -> 123.56 open), and this lab repairs it from Alpaca's OWN
  corporate-actions feed via intraday.unapplied_splits_close, back-adjusting
  OPEN, CLOSE and VOLUME before the ex-date. Ratios under exp(0.35) are printed
  and NOT repaired (the 0.15 classifier cannot resolve them — MET's 2017
  Brighthouse spin-off is the known false positive).
  Three further guards, all reported as counts: a trailing-21-session $20M
  median dollar-volume gate (which is also the ticker-reuse guard — MON prints
  a stale 127.95 at zero volume for 695 sessions and the ticker is then reused
  by a $9.80 issuer, a fake -92% overnight); a hard |leg| > 45% blank on top of
  everything; and the exact identity (1+overnight)(1+intraday) = 1+close_ret,
  whose max residual is printed.

NO LOOKAHEAD — WHERE THE SHIFT IS
  Legs are built with exactly one BACKWARD shift, `close.shift(1)` -> prev:
      overnight(t) = open(t)  / prev_close(t) - 1
      intraday(t)  = close(t) / open(t)       - 1
  Every portfolio applies `sel.shift(1)` — selection dated by the session whose
  CLOSE produced it, so the earliest return it can touch is the close(t) ->
  open(t+1) gap. The swing test states it the other way round and equivalently:
  a pick made from data through close(t) is entered at close(t) or at
  open(t+1), and both are exited at close(t+42).
  The one idealisation, stated plainly: trading AT close(t) on a signal that
  uses close(t) assumes the closing auction can be met. The repo's whole
  pipeline assumes this (HIT is defined off the scan-date close) and the 12-1
  momentum signal is 21 days stale, so it is immaterial here — but it is an
  assumption, not a measurement.

REGISTERED ROWS (scout/hypotheses.md H18a-H18g, all written before this ran)
  a  SPY overnight vs intraday          e  close(t) vs open(t+1) entry, book 2
  b  cross-section, 120 names           f  the same at book 5
  c  12-1 WML momentum legs             g  overnight-only strategy after costs
  d  the repo's own gated composite book

CONTROLS (nulls, not trials)
  (i)   within-date leg-label sign-flip permutation, 10,000 draws, printing the
        ratio of the null's SE to the real series' Newey-West SE — Rule 14,
        because H16 caught a permutation null running 2-3x too tight.
  (ii)  moving-block bootstrap by date.
  (iii) RANDOM-PICK control for H18e/f: the same number of names drawn from the
        identical eligible pool on the identical dates, 200 draws. This is the
        control that separates "our picks gap up" from "everything gaps up",
        and it is the one that decides H4.
  (iv)  matched benchmarks: buy-and-hold close-to-close, the eligible pool's
        own equal-weight overnight return, and SPY.

VERDICT (measured 2016-01-04..2026-08-07, 2,664 sessions, 121 symbols, 280,106
eligible symbol-sessions; every number below is reproduced by the report block)
  H18a  SPY: DIRECTION RIGHT, EFFECT NOT ESTABLISHED. Overnight +9.54%/yr
        (Sharpe 0.86) against intraday +5.97%/yr (0.50) and buy-and-hold
        +16.08% (0.94). The famous form of this result has intraday at or below
        ZERO; here it is solidly positive, and the +1.22 bps/session gap sits at
        permutation p = 0.56 with a block-bootstrap CI of [-3.46, +5.41] bps.
        The pre-registered failure condition "the gap is inside the permutation
        null" FIRES.
  H18b  Cross-section: PERVASIVE, NOT SEPARABLE. The equal-weight 120-name book
        earns +12.73%/yr overnight (Sharpe 1.06) against +4.44%/yr intraday
        (0.39), and overnight beats intraday in 83 of 114 names — 73%, clearing
        the pre-registered 2/3 replication bar. The market-level gap is
        nonetheless inside its own null (p = 0.17, CI [-1.15, +6.87]): the
        pattern is broad enough to be nearly everywhere and small enough to be
        unprovable at n = 2,643. It also decays exactly as McLean-Pontiff
        predicts for a 2019 paper on pre-2014 data — overnight/intraday runs
        +17.4/+2.3 %/yr in the first half and +8.3/+6.7 in the second.
  H18c  WML: SIGN AS PREDICTED, STABILITY NOT. 12-1 winner-minus-loser earns
        +4.88%/yr overnight and -5.20%/yr intraday, which is LPS's sign exactly,
        so the registered failure condition (intraday leg not negative) does NOT
        fire. But the overnight leg flips sign across halves (-5.4%/yr then
        +16.3%/yr), p = 0.24, and the "spread" is a difference of two large
        POSITIVE overnight returns (winners +8.25 bps/session, losers +5.89):
        everything is paid overnight, winners only marginally more.
  H18d  The repo's own book: TRUE AS WRITTEN, EMPTY AS A CLAIM ABOUT THE BOOK.
        The gated top-quintile composite earns +14.00%/yr overnight against
        -3.58%/yr intraday — gap +6.41 bps, p = 0.007, z = +3.03, the only row
        in this round that reaches the repo's t > 3 bar. Then the control that
        was added BECAUSE the number looked good: the eligible pool the book is
        drawn from earns +12.38%/yr overnight and +0.97%/yr intraday by itself.
        Q5-minus-pool is +1.43%/yr overnight, sign-flipped across halves (+3.06
        then -0.18) at p = 0.06, on an excess book that loses 3.04%/yr outright.
        The overnight tilt belongs to the universe, not to the selection.
        Unchanged by a monthly rebalance (+15.01 vs -3.14 %/yr, name churn
        17.5%/session -> 2.3%), so it is not a daily-churn artifact either.
  H18e/f  **THE H4 VERDICT: THE RULE SURVIVES, ITS RATIONALE DOES NOT.**
        On identical picks, entering at close(t) beats entering at open(t+1) by
        +5.29 bps per 42-session window at the shipped book size 2 (95% CI
        [+0.39, +10.73], NW t = +2.07, positive in BOTH halves +7.87/+2.72), and
        by +6.18 bps at book 5. Hit rate 64.24% vs 63.81% (+0.43pp) and 64.02%
        vs 63.64% (+0.38pp). Both entries turn over identically and exit at the
        same price on the same day, so costs cancel exactly: those are net
        numbers, not gross ones.
        AND IT IS NOT A PROPERTY OF THE PICKS. Drawing 2 random names from the
        identical eligible pool on the identical dates earns +4.51 bps
        [p5 +2.45, p95 +6.79] — the measured +5.29 sits inside it. The picks'
        own first-night gap is +5.13 bps against the pool's +4.45 and SPY's
        +4.51, an edge of +0.68 bps with a CI of [-2.68, +4.27] and NW t = 0.44.
        The pre-registered failure condition "statistically indistinguishable
        from the random-pick control" FIRES at book 2; book 5's +6.18 clears its
        control's p95 by a whisker, which is what a sensitivity row is for.
        So: keep buying at the close. It is free, its sign is right in both
        halves and at both book sizes, and the CI on the raw advantage excludes
        zero. But it is worth ~+5 bps a window — about +0.3%/yr at six windows a
        year — and it is the MARKET's overnight drift, not an edge in the names.
        RESEARCH-AGENDA.md's "+0.5-1%/yr" for this rule overstates the half that
        can be measured by roughly 2-3x. The other half (the opening auction's
        wider spread) gets no test here because bars carry no quotes, and it is
        probably the larger half.
  H18g  REJECTED. Break-even round-trip cost is 3.88 bps on SPY, 5.05 bps on the
        EW-120 book and 5.39 bps on the composite Q5 book, against a 5-10 bps
        large-cap band — SPY fails the registered 5 bps bar outright and the two
        books scrape past its letter while failing its substance: at 5 bps they
        return -3.43% / -0.61% / +0.51% a year against buy-and-hold's +16.08% /
        +17.67% / +9.81%. The strongest of them has a gross Sharpe of 1.39, a
        NET Sharpe of 0.10, and a deflated Sharpe of 0.140 at N = 7 trials.
        RESEARCH-AGENDA.md already lists overnight-only trading as dead; this is
        the local confirmation, and it agrees with scout/intraday.py's
        independent 2018-2026 minute-bar run (break-even 4.20 bps on SPY).
  Diagnostic: the dividend is +1.67pp of SPY's +9.54%/yr overnight leg and
  +2.24pp of the EW-120's +12.73%/yr. It lands there by construction — the
  price drops at the ex-date open — so a price-only overnight premium is
  smaller than the headline by that much.

Usage:
  python -m scout.overnight_lab                # the full run (~3 min warm)
  python -m scout.overnight_lab --selftest     # synthetic, no keys, no network
  python -m scout.overnight_lab --check-open   # daily-vs-minute open/close audit
  python -m scout.overnight_lab --force        # refetch the daily bars
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import config, data as daily_data, intraday, news_data, signals

# --------------------------------------------------------------------------
# knobs — fixed ex ante, none tuned on an outcome
# --------------------------------------------------------------------------
BENCH = "SPY"
TDAYS = 252.0
COST_GRID_BPS = (0.0, 5.0, 10.0)     # round trip, large-cap band
MIN_DOLLAR_VOL = 20e6                # trailing-21-session MEDIAN through t
LIQ_WINDOW = 21
MIN_NAMES = 20                       # smallest cross-section worth ranking
EXTREME_LEG = 0.45                   # residual bad-print guard on any one leg
HORIZON = config.HORIZON_TDAYS       # 42 trading sessions, the shipped window
TARGET = config.TARGET_GAIN          # +5%, the shipped HIT bar
BOOK_SIZES = (2, 5)                  # H18e (shipped size) and H18f
N_QUANTILES = 5
N_RANDOM_DRAWS = 200
PERM_REPS = 10_000
BOOT_REPS = 2_000
BLOCK_DAILY = 21                     # moving-block length for daily leg series
SEED = 20260809
WARMUP = 270                         # bars before the first composite (252d+)
N_TRIALS_REGISTERED = 7              # H18a..H18g; controls are nulls, not trials

BARS_PICKLE = config.SCOUT_DIR / "cache_overnight_bars_all.pkl"
BARS_SPLIT_PICKLE = config.SCOUT_DIR / "cache_overnight_bars_split.pkl"
SPLIT_AUDIT_JSON = config.SCOUT_DIR / "cache_overnight_splitaudit.json"
RESULTS_JSON = config.SCOUT_DIR / "overnight_results.json"

#: An unapplied-split test can only separate "applied" from "not applied" when
#: the split's log ratio exceeds twice the classifier tolerance.
#: intraday.unapplied_splits_close uses tol=0.15, so anything under exp(0.30)
#: is unresolvable. Same constant, same reason, as news_sentiment_lab.
MIN_REPAIR_LOG_RATIO = 0.35


# --------------------------------------------------------------------------
# small statistics helpers (scipy is not a dependency of this repo)
# --------------------------------------------------------------------------

def _clean(x) -> np.ndarray:
    x = np.asarray(x, float)
    return x[np.isfinite(x)]


def _t_stat(x) -> float:
    x = _clean(x)
    if len(x) < 3 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))


def _nw_se(x, lags: int) -> float:
    """Newey-West standard error of the mean of a serially-correlated series.

    Overlapping holds make adjacent observations dependent by construction; an
    OLS SE on that series is too tight by roughly sqrt(h).
    """
    x = _clean(x)
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    var = float(e @ e) / n
    for L in range(1, min(lags, n - 1) + 1):
        cov = float(e[L:] @ e[:-L]) / n
        var += 2.0 * (1.0 - L / (lags + 1.0)) * cov
    return float(math.sqrt(var / n)) if var > 0 else float("nan")


def _nw_t(x, lags: int) -> float:
    se = _nw_se(x, lags)
    xc = _clean(x)
    return float(xc.mean() / se) if se and np.isfinite(se) and se > 0 else float("nan")


def _block_boot_ci(x, block: int, reps: int = BOOT_REPS,
                   seed: int = SEED) -> tuple[float, float]:
    """Moving-block bootstrap CI for the mean. One observation per DATE, so
    resampling dates IS the date-clustered bootstrap the repo uses elsewhere
    (scout/calibrate.py); the block additionally respects the overlap."""
    x = _clean(x)
    n = len(x)
    if n < 3 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]
           ).reshape(reps, -1)[:, :n]
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _ann(mean_daily: float) -> float:
    return float(mean_daily * TDAYS)


def _cum(x) -> float:
    return float(np.prod(1.0 + _clean(x)) - 1.0)


def _ann_ret(x) -> float:
    x = _clean(x)
    return float(np.prod(1.0 + x) ** (TDAYS / len(x)) - 1.0) if len(x) else float("nan")


def _sharpe(x) -> float:
    x = _clean(x)
    if len(x) < 5 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * math.sqrt(TDAYS))


def _halves(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    s = s.dropna()
    k = len(s) // 2
    return s.iloc[:k], s.iloc[k:]


def _pct(x) -> str:
    return "   n/a" if x is None or not np.isfinite(x) else f"{100 * x:+6.2f}%"


# --------------------------------------------------------------------------
# prices — fetch, split-repair (OPEN as well as CLOSE), guard
# --------------------------------------------------------------------------

def panel_symbols() -> list[str]:
    """The point-in-time liquid-120 panel + SPY. Read from the cached list the
    news labs already derived, so all three labs share one universe."""
    syms = json.loads(news_data.PANEL_SYMBOLS_JSON.read_text())
    return sorted(set(syms) | {BENCH})


def _fetch(symbols: list[str], adjustment: str) -> dict[str, pd.DataFrame]:
    """scout/data.daily_ohlcv, but with the adjustment parameterised — that
    module hardcodes adjustment=all and the registered price-only diagnostic
    needs adjustment=split. Same client, same feed, same pivot."""
    if adjustment == "all":
        return daily_data.daily_ohlcv(symbols, 3960)
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY)
    now = datetime.now(timezone.utc)
    frames = []
    for i in range(0, len(symbols), daily_data.CHUNK):
        req = StockBarsRequest(symbol_or_symbols=symbols[i:i + daily_data.CHUNK],
                               timeframe=TimeFrame.Day,
                               start=now - timedelta(days=3960),
                               end=now - timedelta(minutes=20),
                               adjustment=Adjustment(adjustment), feed=DataFeed.SIP)
        df = client.get_stock_bars(req).df
        if not df.empty:
            frames.append(df.reset_index())
    allb = pd.concat(frames, ignore_index=True)
    allb["timestamp"] = (pd.to_datetime(allb["timestamp"])
                         .dt.tz_convert("US/Eastern").dt.normalize())
    return {f: (allb.pivot_table(index="timestamp", columns="symbol", values=f,
                                 aggfunc="last").sort_index())
            for f in ("open", "close", "volume")}


def _split_events(symbols, start, end) -> dict:
    """Alpaca's own corporate-actions feed, cached to disk (it is the same list
    every run and the endpoint is rate-limited alongside the bar fetch)."""
    if SPLIT_AUDIT_JSON.exists():
        raw = json.loads(SPLIT_AUDIT_JSON.read_text())
        return {k: [{"ex_date": pd.Timestamp(e["ex_date"]), "ratio": e["ratio"],
                     "kind": e["kind"]} for e in v] for k, v in raw.items()}
    ev = intraday.split_events(list(symbols), start, end)
    SPLIT_AUDIT_JSON.write_text(json.dumps(
        {k: [{"ex_date": str(e["ex_date"].date()), "ratio": e["ratio"],
              "kind": e["kind"]} for e in v] for k, v in ev.items()}, indent=1))
    return ev


def repair_splits(o: pd.DataFrame, c: pd.DataFrame, v: pd.DataFrame,
                  events: dict | None = None, verbose: bool = True,
                  ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list, list]:
    """Back-adjust every split Alpaca's bar pipeline failed to apply — OPEN,
    CLOSE and VOLUME together, or the repair would itself fabricate a gap.

    Detection is on the CLOSE series (intraday.unapplied_splits_close), because
    the ex-date close/prev-close ratio is the diagnostic the classifier was
    built and validated against. Only unambiguous events are touched.
    """
    if events is None:
        events = _split_events(list(c.columns), c.index.min(), c.index.max())
    repairs, ambiguous = [], []
    for sym, evs in events.items():
        if sym not in c.columns:
            continue
        for b in intraday.unapplied_splits_close(c[sym].dropna(), evs):
            if b.get("applied") is not False:
                continue                     # jump is not at the split ratio
            if abs(math.log(b["ratio"])) < MIN_REPAIR_LOG_RATIO:
                ambiguous.append({"symbol": sym, "ex_date": str(b["ex_date"].date()),
                                  "ratio": b["ratio"], "jump": b["jump"]})
                continue
            m = c.index < pd.Timestamp(b["ex_date"])
            o.loc[m, sym] = o.loc[m, sym] / b["ratio"]
            c.loc[m, sym] = c.loc[m, sym] / b["ratio"]
            v.loc[m, sym] = v.loc[m, sym] * b["ratio"]
            repairs.append({"symbol": sym, "ex_date": str(b["ex_date"].date()),
                            "ratio": b["ratio"], "n_bars": int(m.sum()),
                            "fake_overnight": b["jump"] - 1.0})
    if verbose:
        for r in repairs:
            print(f"  SPLIT REPAIR {r['symbol']} {r['ex_date']} ratio "
                  f"{r['ratio']:.0f} -> {r['n_bars']:,} sessions rescaled "
                  f"(removed a fabricated {100 * r['fake_overnight']:+.1f}% "
                  f"OVERNIGHT return)")
        if not repairs:
            print("  split audit: nothing unapplied")
        for a in ambiguous:
            print(f"  split audit AMBIGUOUS (not repaired): {a['symbol']} "
                  f"{a['ex_date']} filed ratio {a['ratio']:.3f}, observed jump "
                  f"{a['jump']:.4f} — under the 0.15 classifier's resolution")
    return o, c, v, repairs, ambiguous


def load_bars(adjustment: str = "all", force: bool = False,
              verbose: bool = True) -> dict:
    """Daily SIP open/close/volume for the panel, split-repaired."""
    path = BARS_PICKLE if adjustment == "all" else BARS_SPLIT_PICKLE
    if path.exists() and not force:
        bars = pd.read_pickle(path)
    else:
        syms = panel_symbols()
        if verbose:
            print(f"fetching daily bars (adjustment={adjustment}) for "
                  f"{len(syms)} symbols ...")
        bars = _fetch(syms, adjustment)
        pd.to_pickle(bars, path)
    o, c, v = (bars[f].copy().astype("float64") for f in ("open", "close", "volume"))
    for f in (o, c, v):
        f.index = pd.DatetimeIndex(f.index).tz_localize(None).normalize()
    o, c, v, repairs, ambiguous = repair_splits(o, c, v, verbose=verbose)
    return {"open": o, "close": c, "volume": v,
            "repairs": repairs, "ambiguous": ambiguous, "adjustment": adjustment}


def liquidity_mask(c: pd.DataFrame, v: pd.DataFrame) -> pd.DataFrame:
    """Tradeable-at-10bps gate from data THROUGH t only. Doubles as the
    ticker-reuse guard: MON keeps printing a stale 127.95 at ~zero volume for
    695 sessions after the Bayer acquisition closes and the ticker is then
    reused by an unrelated $9.80 issuer — a fabricated -92% overnight return
    that no split feed can catch."""
    med = (c * v).rolling(LIQ_WINDOW, min_periods=LIQ_WINDOW).median()
    return (med >= MIN_DOLLAR_VOL) & c.notna()


def leg_frames(bars: dict, verbose: bool = True, guard: bool = True) -> dict:
    """The decomposition. ONE backward shift: prev = close.shift(1).

      overnight(t) = open(t)  / prev_close(t) - 1
      intraday(t)  = close(t) / open(t)       - 1
      close_ret(t) = close(t) / prev_close(t) - 1
      (1 + overnight)(1 + intraday) == 1 + close_ret, exactly.

    Eligibility for the legs of session t is the liquidity gate as it stood at
    close(t-1) — `mask.shift(1)` — because that is when the position would have
    to be opened.
    """
    o, c, v = bars["open"], bars["close"], bars["volume"]
    prev = c.shift(1)                                   # <<< the only shift
    on = o / prev - 1.0
    idr = c / o - 1.0
    cr = c / prev - 1.0

    mask = liquidity_mask(c, v)
    ok = mask.shift(1).fillna(False) & on.notna() & idr.notna() & cr.notna()

    extreme = ((on.abs() > EXTREME_LEG) | (idr.abs() > EXTREME_LEG)
               | (cr.abs() > EXTREME_LEG)) & ok
    if not guard:
        extreme = extreme & False
    n_extreme = int(extreme.to_numpy().sum())
    if n_extreme and verbose:
        ii, jj = np.where(extreme.to_numpy())
        rows = [f"{extreme.index[i].date()} {extreme.columns[j]}"
                for i, j in zip(ii, jj)]
        print(f"  EXTREME-LEG GUARD blanked {n_extreme} symbol-sessions "
              f"(|leg| > {EXTREME_LEG:.0%}): {', '.join(rows[:6])}")
    elif verbose:
        print(f"  extreme-leg guard (|leg| > {EXTREME_LEG:.0%}): 0 survivors "
              "after split repair + liquidity gate")
    ok &= ~extreme

    on, idr, cr = on.where(ok), idr.where(ok), cr.where(ok)
    resid = float((((1 + on) * (1 + idr)) - (1 + cr)).abs().max().max())
    if verbose:
        print(f"  identity (1+on)(1+id) = 1+cc: max residual {resid:.2e}")
        print(f"  eligible symbol-sessions: {int(ok.to_numpy().sum()):,} over "
              f"{len(c):,} dates x {c.shape[1]} symbols")
    return {"overnight": on, "intraday": idr, "close_ret": cr, "eligible": ok,
            "identity_residual": resid, "n_extreme": n_extreme,
            "open": o, "close": c, "volume": v}


# --------------------------------------------------------------------------
# decomposition + its controls
# --------------------------------------------------------------------------

def decompose(on: pd.Series, idr: pd.Series, cr: pd.Series | None = None,
              label: str = "") -> dict:
    """Cumulative / annualised / Sharpe for both legs, plus both halves."""
    if cr is None:
        cr = (1 + on) * (1 + idr) - 1
    df = pd.concat({"on": on, "id": idr, "cc": cr}, axis=1).dropna()
    a, b, t = df["on"], df["id"], df["cc"]
    h1a, h2a = _halves(a)
    h1b, h2b = _halves(b)
    return {"label": label, "n": len(df),
            "start": str(df.index[0].date()), "end": str(df.index[-1].date()),
            "cum_on": _cum(a), "cum_id": _cum(b), "cum_cc": _cum(t),
            "ann_on": _ann_ret(a), "ann_id": _ann_ret(b), "ann_cc": _ann_ret(t),
            "sharpe_on": _sharpe(a), "sharpe_id": _sharpe(b), "sharpe_cc": _sharpe(t),
            "bps_on": float(a.mean() * 1e4), "bps_id": float(b.mean() * 1e4),
            "gap_bps": float((a.mean() - b.mean()) * 1e4),
            "h1_bps_on": float(h1a.mean() * 1e4), "h1_bps_id": float(h1b.mean() * 1e4),
            "h2_bps_on": float(h2a.mean() * 1e4), "h2_bps_id": float(h2b.mean() * 1e4),
            "h1_ann_on": _ann_ret(h1a), "h1_ann_id": _ann_ret(h1b),
            "h2_ann_on": _ann_ret(h2a), "h2_ann_id": _ann_ret(h2b)}


def leg_permutation(on: pd.Series, idr: pd.Series, reps: int = PERM_REPS,
                    seed: int = SEED) -> dict:
    """CONTROL. Null: within a DATE the overnight/intraday label carries no
    information, so the two legs are exchangeable. Flip the labels independently
    on each date and rebuild the mean gap.

    Rule 14 (from H16): a permutation p-value is quoted ONLY next to the ratio
    of the null's standard error to the real series' Newey-West SE. A null that
    destroys the persistence of the real series runs too tight and manufactures
    significance; here the statistic is a per-date difference with little
    autocorrelation, so the ratio should come out near 1 — and it is printed so
    a reader can see that rather than take it on trust.
    """
    df = pd.concat({"on": on, "id": idr}, axis=1).dropna()
    a, b = df["on"].values, df["id"].values
    obs = (a.mean() - b.mean()) * 1e4
    rng = np.random.default_rng(seed)
    flips = rng.random((reps, len(a))) < 0.5
    x = np.where(flips, b, a)
    y = np.where(flips, a, b)
    draws = (x.mean(axis=1) - y.mean(axis=1)) * 1e4
    real_nw_se = _nw_se((a - b) * 1e4, lags=5)
    return {"observed_gap_bps": float(obs),
            "p_two_sided": float((np.abs(draws) >= abs(obs)).sum() + 1) / (reps + 1),
            "null_se_bps": float(draws.std(ddof=1)),
            "real_nw_se_bps": float(real_nw_se),
            "se_ratio_null_over_real": float(draws.std(ddof=1) / real_nw_se)
            if np.isfinite(real_nw_se) and real_nw_se > 0 else float("nan"),
            "z_vs_real_se": float(obs / real_nw_se)
            if np.isfinite(real_nw_se) and real_nw_se > 0 else float("nan"),
            "reps": reps, "n_dates": len(a)}


def cost_table(on: pd.Series, idr: pd.Series, cr: pd.Series,
               bps_list=COST_GRID_BPS) -> dict:
    """Overnight-only and intraday-only each need ONE round trip per session
    (252/yr). Buy-and-hold needs none, which is the entire point."""
    rows = []
    for bps in bps_list:
        cst = bps / 1e4
        rows.append({"round_trip_bps": bps,
                     "overnight_ann": _ann_ret(on - cst),
                     "overnight_sharpe": _sharpe(on - cst),
                     "intraday_ann": _ann_ret(idr - cst),
                     "buyhold_ann": _ann_ret(cr)})
    return {"rows": rows,
            "breakeven_overnight_bps": float(on.dropna().mean() * 1e4),
            "breakeven_intraday_bps": float(idr.dropna().mean() * 1e4)}


# --------------------------------------------------------------------------
# books: equal-weight over a boolean selection, with the one shift
# --------------------------------------------------------------------------

def _prev(sel: pd.DataFrame) -> pd.DataFrame:
    """`sel` as it stood on the previous session, still boolean. THE ONE SHIFT.

    The astype(bool) is load-bearing: DataFrame.shift on a bool frame upcasts to
    OBJECT, and `~` on an object frame calls Python's int-valued `~True == -2`,
    which is truthy — so `sel & ~sel.shift(1)` silently reports 100% turnover
    for a book that never changes. It did, until the self-test caught it."""
    return sel.shift(1).fillna(False).astype(bool)


def ew_leg(sel: pd.DataFrame, leg: pd.DataFrame) -> pd.Series:
    """Equal-weight return of `leg` over the names selected on the PREVIOUS
    session. `sel` is dated by the session whose close produced the selection;
    `_prev(sel)` is the holding during session t, so the earliest return the
    selection can touch is close(t) -> open(t+1)."""
    held = _prev(sel) & leg.notna()
    n = held.sum(axis=1)
    tot = leg.where(held).sum(axis=1)
    return (tot / n.replace(0, np.nan)).rename("ew")


def freeze(sel: pd.DataFrame, k: int) -> pd.DataFrame:
    """Hold the selection made on every k-th session, so daily selection churn
    cannot be what produces a leg result. k=21 is a monthly rebalance."""
    keep = pd.Series(False, index=sel.index)
    keep.iloc[::k] = True
    return sel.where(keep, other=np.nan, axis=0).ffill().fillna(False).astype(bool)


def churn(sel: pd.DataFrame) -> float:
    """Mean one-way name turnover per session: the share of the book replaced.
    Sessions with no book yesterday are skipped — the first purchase is not
    turnover."""
    prev = _prev(sel)
    n = sel.sum(axis=1)
    live = prev.any(axis=1) & (n > 0)
    changed = (sel & ~prev).sum(axis=1)
    return float((changed[live] / n[live]).mean())


def quantile_sel(score: pd.DataFrame, q: int, which: str) -> pd.DataFrame:
    """Top ('hi') or bottom ('lo') 1/q of each date's cross-section."""
    r = score.rank(axis=1, pct=True, na_option="keep")
    n = score.notna().sum(axis=1)
    live = (n >= MIN_NAMES)
    sel = (r >= 1 - 1 / q) if which == "hi" else (r <= 1 / q)
    return sel.where(live, False).fillna(False)


def topn_sel(score: pd.DataFrame, n: int) -> pd.DataFrame:
    """The n highest-scoring names each date (the shipped book construction)."""
    r = score.rank(axis=1, ascending=False, method="first", na_option="keep")
    return (r <= n).fillna(False)


# --------------------------------------------------------------------------
# signals used by H18c / H18d / H18e
# --------------------------------------------------------------------------

def momentum_score(c: pd.DataFrame, eligible: pd.DataFrame) -> pd.DataFrame:
    """Classic 12-1 momentum: close(t-21)/close(t-252) - 1, so the signal on
    date t uses no price after close(t) and skips the reversal month. Ranked
    only among names tradeable at t (the liquidity gate at t)."""
    mom = c.shift(21) / c.shift(252) - 1.0
    return mom.where(eligible)


def composite_scores(bars: dict, eligible: pd.DataFrame,
                     verbose: bool = True) -> pd.DataFrame:
    """The repo's OWN engine (signals.composite_at, config.ENGINE) evaluated on
    every session — gates, vetoes and all. Names failing a gate get no score,
    exactly as in a live scan, so the eligible pool here IS the scan's pool."""
    frames = signals.feature_frames(bars["open"], bars["close"], bars["volume"])
    idx = bars["close"].index
    rows = {}
    for ts in idx[WARMUP:]:
        snap = signals.composite_at(frames, ts).drop(index=[BENCH], errors="ignore")
        if len(snap) >= MIN_NAMES:
            rows[ts] = snap["score"]
    score = pd.DataFrame(rows).T.reindex(index=idx, columns=bars["close"].columns)
    score = score.where(eligible)
    if verbose:
        n = score.notna().sum(axis=1)
        print(f"  composite ({config.ENGINE}) scored {int((n > 0).sum()):,} dates, "
              f"median eligible pool {n[n > 0].median():.0f} names")
    return score


# --------------------------------------------------------------------------
# H18e/f — THE DECIDING TEST: close(t) entry vs open(t+1) entry
# --------------------------------------------------------------------------

def swing_entry_test(score: pd.DataFrame, legs: dict, n_book: int,
                     rng: np.random.Generator, draws: int = N_RANDOM_DRAWS) -> dict:
    """The repo's 42-session swing trade on IDENTICAL picks, entered two ways.

      picks(t)     = the n_book highest composite scores using data through close(t)
      close-entry  = close(t+42) / close(t)   - 1     [the shipped rule]
      open-entry   = close(t+42) / open(t+1)  - 1
      HIT          = max close over t+1..t+42 >= entry_price * 1.05

    The identity behind the whole test, which is why it is decisive:
        (1 + R_close) / (1 + R_open) = open(t+1) / close(t) = 1 + overnight(t+1)
    so the close-entry advantage IS the picks' first overnight return, and the
    only question that matters is whether the picks' gap exceeds the gap of the
    pool they were drawn from. Both entries exit at the same price on the same
    day and turn over identically, so trading costs cancel in the difference —
    every number below is a gross difference AND a net difference.

    Entry on EVERY session (windows overlap by construction), which pools all
    42 entry phases and so cannot repeat H7's single-phase artifact; the price
    is dependence, handled with a block bootstrap at the holding length and
    Newey-West at 42 lags. Effective independent sample ~ n_dates / 42.
    """
    c, o = legs["close"], legs["open"]
    on = legs["overnight"]
    idx = c.index
    h = HORIZON
    exit_px = c.shift(-h)                       # close(t+42), the common exit
    open_next = o.shift(-1)                     # open(t+1), the alternative entry
    # forward max close over t+1 .. t+42, for the HIT label
    fwdmax = c.iloc[::-1].rolling(h, min_periods=h).max().iloc[::-1].shift(-1)

    r_close = exit_px / c - 1.0
    r_open = exit_px / open_next - 1.0
    hit_close = ((fwdmax / c - 1.0) >= TARGET).astype(float)
    hit_open = ((fwdmax / open_next - 1.0) >= TARGET).astype(float)
    valid = exit_px.notna() & open_next.notna() & c.notna() & fwdmax.notna()

    sel = topn_sel(score, n_book) & valid & score.notna()
    live = sel.sum(axis=1) == n_book
    pool = score.notna() & valid                     # the identical eligible pool

    def _book(s: pd.DataFrame) -> pd.DataFrame:
        k = s.sum(axis=1).replace(0, np.nan)
        return pd.DataFrame({
            "r_close": r_close.where(s).sum(axis=1) / k,
            "r_open": r_open.where(s).sum(axis=1) / k,
            "hit_close": hit_close.where(s).sum(axis=1) / k,
            "hit_open": hit_open.where(s).sum(axis=1) / k,
            "first_on": on.shift(-1).where(s).sum(axis=1) / k,
        })

    book = _book(sel)[live]
    poolbook = _book(pool).reindex(book.index)
    diff = (book["r_close"] - book["r_open"]).dropna()
    hitdiff = (book["hit_close"] - book["hit_open"]).dropna()
    on_pick = book["first_on"].dropna()
    on_pool = poolbook["first_on"].dropna()
    on_edge = (book["first_on"] - poolbook["first_on"]).dropna()
    spy_on = on[BENCH].shift(-1).reindex(book.index).dropna()

    h1, h2 = _halves(diff)
    hh1, hh2 = _halves(hitdiff)
    e1, e2 = _halves(on_edge)

    # ---- random-pick control: same count, same pool, same dates -------------
    poolarr = pool.reindex(book.index).to_numpy()
    ron = on.shift(-1).reindex(book.index).to_numpy()
    rrc = r_close.reindex(book.index).to_numpy()
    rro = r_open.reindex(book.index).to_numpy()
    rhc = hit_close.reindex(book.index).to_numpy()
    rho_ = hit_open.reindex(book.index).to_numpy()
    usable = poolarr.sum(axis=1) >= n_book
    rows = np.flatnonzero(usable)
    ctrl_diff, ctrl_on, ctrl_hit = [], [], []
    for _ in range(draws):
        # random n_book names per date, drawn ONLY from that date's pool:
        # push non-pool names to +inf and take the n_book smallest random keys
        keys = rng.random(poolarr.shape)
        keys[~poolarr] = np.inf
        pick = np.argpartition(keys, n_book - 1, axis=1)[:, :n_book][rows]
        take = lambda M: np.take_along_axis(M[rows], pick, axis=1)
        ctrl_diff.append(np.nanmean(np.nanmean(take(rrc) - take(rro), axis=1)))
        ctrl_on.append(np.nanmean(np.nanmean(take(ron), axis=1)))
        ctrl_hit.append(np.nanmean(np.nanmean(take(rhc) - take(rho_), axis=1)))
    ctrl_diff = np.array(ctrl_diff)
    ctrl_on = np.array(ctrl_on)
    ctrl_hit = np.array(ctrl_hit)

    lo, hi = _block_boot_ci(diff.values * 1e4, block=h)
    elo, ehi = _block_boot_ci(on_edge.values * 1e4, block=h)
    return {
        "n_book": n_book, "n_dates": len(diff),
        "n_eff_independent": len(diff) / h,
        "span": [str(diff.index[0].date()), str(diff.index[-1].date())],
        "mean_r_close": float(book["r_close"].mean()),
        "mean_r_open": float(book["r_open"].mean()),
        "diff_bps": float(diff.mean() * 1e4),
        "diff_bps_ci": [lo, hi],
        "diff_t_nw42": _nw_t(diff.values, lags=h),
        "diff_h1_bps": float(h1.mean() * 1e4), "diff_h2_bps": float(h2.mean() * 1e4),
        "hit_close": float(book["hit_close"].mean()),
        "hit_open": float(book["hit_open"].mean()),
        "hit_diff_pp": float(hitdiff.mean() * 100),
        "hit_diff_h1_pp": float(hh1.mean() * 100),
        "hit_diff_h2_pp": float(hh2.mean() * 100),
        "first_on_pick_bps": float(on_pick.mean() * 1e4),
        "first_on_pool_bps": float(on_pool.mean() * 1e4),
        "first_on_spy_bps": float(spy_on.mean() * 1e4),
        "on_edge_bps": float(on_edge.mean() * 1e4),
        "on_edge_ci": [elo, ehi],
        "on_edge_t_nw": _nw_t(on_edge.values, lags=5),
        "on_edge_h1_bps": float(e1.mean() * 1e4),
        "on_edge_h2_bps": float(e2.mean() * 1e4),
        "ctrl_diff_bps_mean": float(ctrl_diff.mean()) * 1e4,
        "ctrl_diff_bps_p5": float(np.percentile(ctrl_diff, 5)) * 1e4,
        "ctrl_diff_bps_p95": float(np.percentile(ctrl_diff, 95)) * 1e4,
        "ctrl_on_bps_mean": float(ctrl_on.mean()) * 1e4,
        "ctrl_hit_pp_mean": float(ctrl_hit.mean()) * 100,
        "ctrl_draws": draws,
    }


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def run(force: bool = False, price_only: bool = True, verbose: bool = True) -> dict:
    rng = np.random.default_rng(SEED)
    print("=" * 78)
    print("H18 — the overnight/intraday decomposition, and the H4 close-entry rule")
    print("=" * 78)
    bars = load_bars("all", force=force, verbose=verbose)
    legs = leg_frames(bars, verbose=verbose)
    on, idr, cr = legs["overnight"], legs["intraday"], legs["close_ret"]
    elig = legs["eligible"]
    res: dict = {"engine": config.ENGINE, "generated": datetime.now(timezone.utc).isoformat(),
                 "span": [str(cr.index[0].date()), str(cr.index[-1].date())],
                 "n_sessions": int(len(cr)), "n_symbols": int(cr.shape[1]),
                 "repairs": bars["repairs"], "ambiguous": bars["ambiguous"],
                 "identity_residual": legs["identity_residual"],
                 "n_extreme_blanked": legs["n_extreme"]}

    # ---------------- H18a: SPY -------------------------------------------
    print("\n[H18a] SPY, the market-level decomposition")
    spy = decompose(on[BENCH], idr[BENCH], cr[BENCH], label="SPY")
    res["H18a"] = {"decomp": spy,
                   "perm": leg_permutation(on[BENCH], idr[BENCH]),
                   "boot_gap_ci_bps": _block_boot_ci(
                       ((on[BENCH] - idr[BENCH]).dropna().values) * 1e4,
                       block=BLOCK_DAILY),
                   "costs": cost_table(on[BENCH].dropna(), idr[BENCH].dropna(),
                                       cr[BENCH].dropna())}

    # ---------------- H18b: the cross-section ------------------------------
    print("[H18b] equal-weight 120-name book + per-name replication")
    names = [s for s in cr.columns if s != BENCH]
    ew_on = on[names].mean(axis=1)
    ew_id = idr[names].mean(axis=1)
    ew_cc = cr[names].mean(axis=1)
    per = []
    for s in names:
        d = pd.concat({"on": on[s], "id": idr[s]}, axis=1).dropna()
        if len(d) < 250:
            continue
        per.append({"symbol": s, "n": len(d),
                    "ann_on": _ann_ret(d["on"]), "ann_id": _ann_ret(d["id"]),
                    "bps_on": float(d["on"].mean() * 1e4),
                    "bps_id": float(d["id"].mean() * 1e4)})
    perdf = pd.DataFrame(per)
    agree = int((perdf["bps_on"] > perdf["bps_id"]).sum())
    res["H18b"] = {"decomp": decompose(ew_on, ew_id, ew_cc, label="EW-120"),
                   "perm": leg_permutation(ew_on, ew_id),
                   "boot_gap_ci_bps": _block_boot_ci(
                       ((ew_on - ew_id).dropna().values) * 1e4, block=BLOCK_DAILY),
                   "costs": cost_table(ew_on.dropna(), ew_id.dropna(), ew_cc.dropna()),
                   "n_names": int(len(perdf)), "n_overnight_wins": agree,
                   "frac_overnight_wins": agree / len(perdf),
                   "per_symbol": perdf.sort_values("bps_on").to_dict("records")}

    # ---------------- H18c: 12-1 WML ---------------------------------------
    print("[H18c] 12-1 winner-minus-loser momentum legs")
    mom = momentum_score(legs["close"].drop(columns=[BENCH], errors="ignore"),
                         elig.drop(columns=[BENCH], errors="ignore"))
    hi = quantile_sel(mom, N_QUANTILES, "hi")
    lo = quantile_sel(mom, N_QUANTILES, "lo")
    wml_on = ew_leg(hi, on) - ew_leg(lo, on)
    wml_id = ew_leg(hi, idr) - ew_leg(lo, idr)
    wml_cc = ew_leg(hi, cr) - ew_leg(lo, cr)
    res["H18c"] = {"decomp": decompose(wml_on, wml_id, wml_cc, label="WML 12-1"),
                   "perm": leg_permutation(wml_on, wml_id),
                   "long_leg": decompose(ew_leg(hi, on), ew_leg(hi, idr),
                                         ew_leg(hi, cr), label="winners"),
                   "short_leg": decompose(ew_leg(lo, on), ew_leg(lo, idr),
                                          ew_leg(lo, cr), label="losers")}

    # ---------------- H18d: the repo's own book ----------------------------
    print("[H18d] the repo's gated composite book")
    score = composite_scores(bars, elig.drop(columns=[BENCH], errors="ignore"),
                             verbose=verbose)
    top = quantile_sel(score, N_QUANTILES, "hi")
    pool = score.notna()
    b_on, b_id, b_cc = ew_leg(top, on), ew_leg(top, idr), ew_leg(top, cr)
    p_on, p_id, p_cc = ew_leg(pool, on), ew_leg(pool, idr), ew_leg(pool, cr)
    # THE CONTROL H18d actually needs: the eligible pool ALSO earns overnight,
    # so "our book earns its premium overnight" is only a statement about the
    # book if it survives subtracting the pool it was drawn from.
    mon = freeze(top, 21)
    res["H18d"] = {"decomp": decompose(b_on, b_id, b_cc, label="composite Q5"),
                   "perm": leg_permutation(b_on, b_id),
                   "costs": cost_table(b_on.dropna(), b_id.dropna(), b_cc.dropna()),
                   "pool": decompose(p_on, p_id, p_cc, label="eligible pool"),
                   "excess": decompose(b_on - p_on, b_id - p_id, b_cc - p_cc,
                                       label="Q5 minus pool"),
                   "excess_perm": leg_permutation(b_on - p_on, b_id - p_id),
                   "monthly": decompose(ew_leg(mon, on), ew_leg(mon, idr),
                                        ew_leg(mon, cr), label="Q5, monthly reb."),
                   "churn_daily": churn(top), "churn_monthly": churn(mon)}

    # ---------------- H18e/f: THE DECIDING TEST ----------------------------
    for n_book, tag in zip(BOOK_SIZES, ("H18e", "H18f")):
        print(f"[{tag}] 42-session swing trade, close(t) vs open(t+1), book {n_book}"
              f" ({N_RANDOM_DRAWS} random-pick control draws)")
        res[tag] = swing_entry_test(score, legs, n_book, rng)

    # -------- what the extreme-leg guard costs (it can blank a REAL crash) --
    ng = leg_frames(bars, verbose=False, guard=False)
    ng_names = [s for s in ng["close_ret"].columns if s != BENCH]
    res["guard_sensitivity"] = {
        "blanked": legs["n_extreme"],
        "ew_bps_on_guarded": float(on[names].mean(axis=1).mean() * 1e4),
        "ew_bps_on_unguarded": float(ng["overnight"][ng_names].mean(axis=1).mean() * 1e4),
        "ew_bps_id_guarded": float(idr[names].mean(axis=1).mean() * 1e4),
        "ew_bps_id_unguarded": float(ng["intraday"][ng_names].mean(axis=1).mean() * 1e4)}

    # ---------------- H18g: overnight-only after costs ---------------------
    print("[H18g] overnight-only strategy, cost grid")
    res["H18g"] = {"spy": res["H18a"]["costs"], "ew120": res["H18b"]["costs"],
                   "composite_q5": res["H18d"]["costs"]}
    # The strongest overnight book, priced honestly: deflated Sharpe of its
    # NET series at the bottom of the large-cap cost band. Deflating a GROSS
    # Sharpe on a strategy that cannot be traded gross would be theatre.
    from . import growth
    net = (b_on - 5.0 / 1e4).dropna()
    res["H18g"]["best_net"] = {
        "book": "composite Q5 overnight-only @ 5 bps round trip",
        "sharpe_gross": _sharpe(b_on), "sharpe_net": _sharpe(net),
        "n_obs": int(len(net)), "n_trials": N_TRIALS_REGISTERED,
        "deflated_sharpe": float(growth.deflated_sharpe(
            float(net.mean() / net.std(ddof=1)), n_trials=N_TRIALS_REGISTERED,
            n_obs=len(net), skew=float(net.skew()),
            kurtosis=float(net.kurtosis() + 3.0)))}

    # ---------------- registered diagnostic: price-only --------------------
    if price_only:
        print("[diag] price-only rerun (adjustment=split): how much of the "
              "overnight leg is the dividend?")
        try:
            pbars = load_bars("split", force=force, verbose=verbose)
            plegs = leg_frames(pbars, verbose=False)
            pnames = [s for s in plegs["close_ret"].columns if s != BENCH]
            res["price_only"] = {
                "spy": decompose(plegs["overnight"][BENCH], plegs["intraday"][BENCH],
                                 plegs["close_ret"][BENCH], label="SPY price-only"),
                "ew120": decompose(plegs["overnight"][pnames].mean(axis=1),
                                   plegs["intraday"][pnames].mean(axis=1),
                                   plegs["close_ret"][pnames].mean(axis=1),
                                   label="EW-120 price-only")}
        except Exception as e:                      # network/plan hiccup only
            print(f"  price-only diagnostic unavailable: {e}")
            res["price_only"] = {"error": str(e)}
    return res


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def _decomp_block(d: dict) -> None:
    print(f"  {d['label']:<16} n={d['n']:,}  {d['start']} .. {d['end']}")
    print(f"    {'':<12}{'overnight':>12}{'intraday':>12}{'buy&hold':>12}")
    print(f"    {'cumulative':<12}{_pct(d['cum_on']):>12}{_pct(d['cum_id']):>12}"
          f"{_pct(d['cum_cc']):>12}")
    print(f"    {'annualised':<12}{_pct(d['ann_on']):>12}{_pct(d['ann_id']):>12}"
          f"{_pct(d['ann_cc']):>12}")
    print(f"    {'ann Sharpe':<12}{d['sharpe_on']:>12.2f}{d['sharpe_id']:>12.2f}"
          f"{d['sharpe_cc']:>12.2f}")
    print(f"    {'bps/session':<12}{d['bps_on']:>12.2f}{d['bps_id']:>12.2f}"
          f"{d['bps_on'] + d['bps_id']:>12.2f}")
    print(f"    half 1 ann   {_pct(d['h1_ann_on']):>12}{_pct(d['h1_ann_id']):>12}")
    print(f"    half 2 ann   {_pct(d['h2_ann_on']):>12}{_pct(d['h2_ann_id']):>12}")


def _perm_block(p: dict) -> None:
    print(f"    CONTROL leg-label permutation ({p['reps']:,} draws, date-clustered):"
          f" gap {p['observed_gap_bps']:+.2f} bps, p = {p['p_two_sided']:.3f}")
    print(f"      Rule 14: null SE {p['null_se_bps']:.2f} bps vs real "
          f"Newey-West SE {p['real_nw_se_bps']:.2f} bps "
          f"(ratio {p['se_ratio_null_over_real']:.2f}); z vs real SE "
          f"{p['z_vs_real_se']:+.2f}")


def _cost_block(c: dict, name: str) -> None:
    print(f"    {name}: break-even round trip {c['breakeven_overnight_bps']:.2f} bps"
          f" (overnight) / {c['breakeven_intraday_bps']:.2f} bps (intraday)")
    for r in c["rows"]:
        print(f"      {r['round_trip_bps']:>4.0f} bps -> overnight "
              f"{_pct(r['overnight_ann'])}/yr (Sharpe {r['overnight_sharpe']:+.2f})"
              f", intraday {_pct(r['intraday_ann'])}/yr, "
              f"buy&hold {_pct(r['buyhold_ann'])}/yr")


def report(res: dict) -> None:
    print("\n" + "=" * 78)
    print(f"RESULTS — {res['span'][0]} .. {res['span'][1]}, "
          f"{res['n_sessions']:,} sessions, {res['n_symbols']} symbols "
          f"(engine {res['engine']})")
    print("=" * 78)
    print(f"data integrity: {len(res['repairs'])} split(s) repaired, "
          f"{len(res['ambiguous'])} ambiguous left alone, "
          f"{res['n_extreme_blanked']} extreme legs blanked, "
          f"identity residual {res['identity_residual']:.1e}")
    g = res.get("guard_sensitivity")
    if g:
        print(f"  the |leg|>45% guard is a two-sided risk — it can blank a REAL "
              f"crash. Cost of switching it off entirely: EW-120 overnight "
              f"{g['ew_bps_on_guarded']:.3f} -> {g['ew_bps_on_unguarded']:.3f} bps, "
              f"intraday {g['ew_bps_id_guarded']:.3f} -> "
              f"{g['ew_bps_id_unguarded']:.3f} bps")

    print("\n--- H18a  SPY: does the premium accrue overnight? ---")
    _decomp_block(res["H18a"]["decomp"])
    _perm_block(res["H18a"]["perm"])
    lo, hi = res["H18a"]["boot_gap_ci_bps"]
    print(f"    block bootstrap 95% CI on the gap: [{lo:+.2f}, {hi:+.2f}] bps")

    print("\n--- H18b  the cross-section (120 point-in-time names) ---")
    _decomp_block(res["H18b"]["decomp"])
    _perm_block(res["H18b"]["perm"])
    lo, hi = res["H18b"]["boot_gap_ci_bps"]
    print(f"    block bootstrap 95% CI on the gap: [{lo:+.2f}, {hi:+.2f}] bps")
    print(f"    REPLICATION: overnight beats intraday in "
          f"{res['H18b']['n_overnight_wins']} of {res['H18b']['n_names']} names "
          f"({100 * res['H18b']['frac_overnight_wins']:.0f}%; pre-registered bar 67%)")
    worst = res["H18b"]["per_symbol"][:4]
    best = res["H18b"]["per_symbol"][-4:]
    print("    most intraday-driven: "
          + ", ".join(f"{r['symbol']} ({r['bps_on']:+.1f} vs {r['bps_id']:+.1f})"
                      for r in worst))
    print("    most overnight-driven: "
          + ", ".join(f"{r['symbol']} ({r['bps_on']:+.1f} vs {r['bps_id']:+.1f})"
                      for r in reversed(best)))

    print("\n--- H18c  12-1 WML momentum: LPS's actual factor claim ---")
    _decomp_block(res["H18c"]["decomp"])
    _perm_block(res["H18c"]["perm"])
    print(f"    winners  overnight {res['H18c']['long_leg']['bps_on']:+.2f} / "
          f"intraday {res['H18c']['long_leg']['bps_id']:+.2f} bps")
    print(f"    losers   overnight {res['H18c']['short_leg']['bps_on']:+.2f} / "
          f"intraday {res['H18c']['short_leg']['bps_id']:+.2f} bps")

    print("\n--- H18d  the repo's own gated composite book (top quintile) ---")
    _decomp_block(res["H18d"]["decomp"])
    _perm_block(res["H18d"]["perm"])
    print(f"    name churn {100 * res['H18d']['churn_daily']:.1f}%/session daily, "
          f"{100 * res['H18d']['churn_monthly']:.1f}%/session at a monthly rebalance")
    _decomp_block(res["H18d"]["monthly"])
    print("\n    CONTROL — the same book minus the eligible pool it was drawn from:")
    _decomp_block(res["H18d"]["pool"])
    _decomp_block(res["H18d"]["excess"])
    _perm_block(res["H18d"]["excess_perm"])

    print("\n" + "=" * 78)
    print("H18e/H18f — THE DECIDING TEST FOR THE SHIPPED H4 RULE")
    print("=" * 78)
    for tag in ("H18e", "H18f"):
        e = res[tag]
        print(f"\n  book of {e['n_book']}  |  {e['n_dates']:,} entry dates "
              f"{e['span'][0]}..{e['span'][1]}  |  effective independent windows "
              f"~{e['n_eff_independent']:.0f}")
        print(f"    mean 42-session outcome   close(t) entry {_pct(e['mean_r_close'])}"
              f"   open(t+1) entry {_pct(e['mean_r_open'])}")
        print(f"    ADVANTAGE OF BUYING THE CLOSE: {e['diff_bps']:+.2f} bps/window "
              f"(95% CI [{e['diff_bps_ci'][0]:+.2f}, {e['diff_bps_ci'][1]:+.2f}], "
              f"NW t = {e['diff_t_nw42']:+.2f})")
        print(f"      both halves: {e['diff_h1_bps']:+.2f} / {e['diff_h2_bps']:+.2f} bps")
        print(f"    hit rate (max close >= entry x 1.05): close {100 * e['hit_close']:.2f}%"
              f" vs open {100 * e['hit_open']:.2f}%  "
              f"({e['hit_diff_pp']:+.2f}pp; halves {e['hit_diff_h1_pp']:+.2f} / "
              f"{e['hit_diff_h2_pp']:+.2f})")
        print(f"    RANDOM-PICK CONTROL ({e['ctrl_draws']} draws, same pool, same "
              f"dates): {e['ctrl_diff_bps_mean']:+.2f} bps "
              f"[p5 {e['ctrl_diff_bps_p5']:+.2f}, p95 {e['ctrl_diff_bps_p95']:+.2f}], "
              f"hit {e['ctrl_hit_pp_mean']:+.2f}pp")
        print(f"    first-night gap: picks {e['first_on_pick_bps']:+.2f} bps | "
              f"eligible pool {e['first_on_pool_bps']:+.2f} | SPY "
              f"{e['first_on_spy_bps']:+.2f}")
        print(f"      pick-minus-pool edge {e['on_edge_bps']:+.2f} bps "
              f"(95% CI [{e['on_edge_ci'][0]:+.2f}, {e['on_edge_ci'][1]:+.2f}], "
              f"NW t = {e['on_edge_t_nw']:+.2f}; halves {e['on_edge_h1_bps']:+.2f} / "
              f"{e['on_edge_h2_bps']:+.2f})")
        print("    costs cancel: both entries turn over identically and exit at the "
              "same price, so the difference is gross AND net.")

    print("\n--- H18g  overnight-only after costs (252 round trips a year) ---")
    _cost_block(res["H18g"]["spy"], "SPY")
    _cost_block(res["H18g"]["ew120"], "EW-120")
    _cost_block(res["H18g"]["composite_q5"], "composite Q5")
    bn = res["H18g"]["best_net"]
    print(f"    strongest overnight book, priced honestly — {bn['book']}: gross "
          f"Sharpe {bn['sharpe_gross']:+.2f} -> net {bn['sharpe_net']:+.2f}; "
          f"deflated Sharpe at N={bn['n_trials']} trials, {bn['n_obs']:,} obs: "
          f"{bn['deflated_sharpe']:.3f}")

    po = res.get("price_only") or {}
    if "spy" in po:
        print("\n--- diagnostic: how much of the overnight leg is the dividend? ---")
        for k in ("spy", "ew120"):
            d, tr = po[k], (res["H18a"] if k == "spy" else res["H18b"])["decomp"]
            print(f"    {k:<6} total-return overnight {_pct(tr['ann_on'])}/yr vs "
                  f"price-only {_pct(d['ann_on'])}/yr  -> dividend contributes "
                  f"{100 * (tr['ann_on'] - d['ann_on']):+.2f}pp of it")

    print("\n" + "-" * 78)
    print("CAVEATS")
    print("-" * 78)
    for c in [
        "Universe is the point-in-time liquid-120 S&P 500 panel as of 2016-01-04: "
        "survivorship-free, but it contains no post-2016 index addition (no TSLA, "
        "no NVDA-as-megacap). Every verdict is scoped to that cohort.",
        "Entry dates in H18e/f overlap (42-session holds entered daily), so the "
        "effective independent sample is ~1/42 of the date count; all CIs are "
        "moving-block bootstraps at the holding length and t-stats are Newey-West.",
        "Trading AT close(t) on a signal that uses close(t) assumes the closing "
        "auction can be met. So does the rest of the repo (HIT is defined off the "
        "scan-date close); it is an assumption, not a measurement.",
        "H4's other half — that the opening auction charges a wider spread than the "
        "closing one — is NOT tested here. Bars carry no quotes. That half is the "
        "one most likely to be worth more than the drift measured above.",
        "The dividend lands in the overnight leg by construction (the price drops "
        "at the ex-date open), which is why the price-only diagnostic is reported "
        "rather than assumed away.",
        f"Trial count: {N_TRIALS_REGISTERED} registered rows this round plus 3 "
        "post-hoc diagnostics (pool-relative legs, monthly rebalance, guard "
        "sensitivity); control draws are nulls and do not count. Exactly one "
        "row reaches the repo's t>3 bar (H18d, z=+3.03) and its own control "
        "then empties it, which is why the control was run.",
    ]:
        print(f"  - {c}")


# --------------------------------------------------------------------------
# audits and self-test
# --------------------------------------------------------------------------

def check_open(symbols=("SPY", "AAPL", "MSFT", "JPM", "XOM", "PG"),
               start: str = "2018-01-01") -> None:
    """Is the daily bar's OPEN the regular-session opening print, and its CLOSE
    the closing auction? Compared against scout/intraday.py's 5-minute session
    frames, which handle extended hours and half-days explicitly."""
    sess = intraday.session_frames(list(symbols), start, "2026-08-01",
                                   timeframe="5Min", quiet=False)
    bars = load_bars("all", verbose=False)
    print(f"\n  {'sym':<6}{'n':>6}{'open med|dlog|':>16}{'open p99':>12}"
          f"{'close med|dlog|':>17}{'close p99':>12}")
    for s in symbols:
        if s not in bars["open"].columns:
            continue
        for field, mine, theirs in (("open", sess["open_px"][s], bars["open"][s]),
                                    ("close", sess["close_px"][s], bars["close"][s])):
            a, b = mine.dropna(), theirs.dropna()
            i = a.index.intersection(b.index)
            d = np.log(a.loc[i] / b.loc[i]).abs().dropna()
            if field == "open":
                row = f"  {s:<6}{len(d):>6}{d.median():>16.2e}{d.quantile(.99):>12.2e}"
            else:
                row += f"{d.median():>17.2e}{d.quantile(.99):>12.2e}"
        print(row)
    print("\n  (the ~1e-4 close residual IS the closing auction — see "
          "intraday.official_closes; the open agrees to machine precision on the "
          "names whose first print is the auction.)")


def _synthetic(n_days: int = 1500, n_sym: int = 30, on_bps: float = 4.0,
               id_bps: float = 0.0, seed: int = 7) -> dict:
    """Bars with a KNOWN answer: `on_bps` of drift per session in the overnight
    leg, `id_bps` in the intraday leg, and no cross-sectional signal at all."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2016-01-04", periods=n_days)
    syms = [f"S{i:02d}" for i in range(n_sym)] + [BENCH]
    on = rng.normal(on_bps / 1e4, 0.006, (n_days, len(syms)))
    idr = rng.normal(id_bps / 1e4, 0.011, (n_days, len(syms)))
    close = np.empty((n_days, len(syms)))
    open_ = np.empty_like(close)
    px = np.full(len(syms), 100.0)
    for t in range(n_days):
        open_[t] = px * (1 + on[t])
        px = open_[t] * (1 + idr[t])
        close[t] = px
    o = pd.DataFrame(open_, index=idx, columns=syms)
    c = pd.DataFrame(close, index=idx, columns=syms)
    v = pd.DataFrame(1e9 / c.values, index=idx, columns=syms)
    return {"open": o, "close": c, "volume": v, "repairs": [], "ambiguous": []}


def selftest(verbose: bool = True) -> int:
    """No keys, no network. Every assertion has a known answer."""
    fails = []

    def ck(name, cond, detail=""):
        (print(f"  {'ok  ' if cond else 'FAIL'}  {name} {detail}")
         if verbose else None)
        if not cond:
            fails.append(name)

    print("self-test (synthetic bars, known answer)")
    bars = _synthetic(on_bps=4.0, id_bps=0.0)
    legs = leg_frames(bars, verbose=False)
    on, idr = legs["overnight"], legs["intraday"]
    ck("identity (1+on)(1+id)=1+cc", legs["identity_residual"] < 1e-12,
       f"residual {legs['identity_residual']:.1e}")
    m_on = float(on.stack().mean() * 1e4)
    m_id = float(idr.stack().mean() * 1e4)
    ck("overnight drift recovered", abs(m_on - 4.0) < 0.7, f"{m_on:.2f} bps (true 4.0)")
    ck("intraday drift recovered", abs(m_id) < 0.7, f"{m_id:.2f} bps (true 0.0)")

    d = decompose(on[BENCH], idr[BENCH], legs["close_ret"][BENCH])
    ck("decompose sees the right leg", d["ann_on"] > d["ann_id"],
       f"{100 * d['ann_on']:.2f}%/yr vs {100 * d['ann_id']:.2f}%/yr")

    p = leg_permutation(on[BENCH], idr[BENCH], reps=2000)
    ck("permutation rejects a REAL gap", p["p_two_sided"] < 0.05,
       f"p={p['p_two_sided']:.4f}")
    flat = _synthetic(on_bps=0.0, id_bps=0.0, seed=11)
    fl = leg_frames(flat, verbose=False)
    p0 = leg_permutation(fl["overnight"][BENCH], fl["intraday"][BENCH], reps=2000)
    ck("permutation accepts NO gap", p0["p_two_sided"] > 0.05,
       f"p={p0['p_two_sided']:.4f}")

    # the shift: selecting on a leg and earning THAT SAME leg is the classic
    # fabrication; ew_leg's shift(1) is the only thing standing between them.
    leg = legs["overnight"]
    cheat = leg.rank(axis=1, ascending=False) <= 3          # today's own winners
    peeking = (leg.where(cheat).sum(axis=1) / 3)            # no shift: pure lookahead
    honest = ew_leg(cheat, leg)                             # shift(1): yesterday's
    ck("ew_leg's shift is load-bearing",
       float(peeking.mean()) > 20 * abs(float(honest.mean())),
       f"peeking {1e4 * peeking.mean():.1f} bps vs shifted "
       f"{1e4 * honest.mean():.1f} bps")

    # split repair: inject an unapplied 4:1 and check the damage and the guard
    bad = {k: v.copy() for k, v in bars.items()}
    ex = bad["close"].index[800]
    pre = bad["close"].index < ex
    for f in ("open", "close"):
        bad[f].loc[pre, "S01"] = bad[f].loc[pre, "S01"] * 4.0
    raw_on = float(bad["open"].loc[ex, "S01"] / bad["close"].shift(1).loc[ex, "S01"] - 1)
    ck("unrepaired split IS a fake overnight crash", raw_on < -0.70,
       f"{100 * raw_on:.1f}% overnight")
    fake = leg_frames(bad, verbose=False)
    ck("the extreme-leg guard blanks it",
       fake["n_extreme"] >= 1 and not np.isfinite(fake["overnight"].loc[ex, "S01"]),
       f"{fake['n_extreme']} blanked")
    ev = [{"ex_date": ex, "ratio": 4.0, "kind": "forward_split"}]
    flagged = intraday.unapplied_splits_close(bad["close"]["S01"], ev)
    ck("the split classifier flags it",
       bool(flagged) and flagged[0]["applied"] is False)
    fixed_o, fixed_c, _, reps, _ = repair_splits(
        bad["open"].copy(), bad["close"].copy(), bad["volume"].copy(),
        events={"S01": ev}, verbose=False)
    ck("repair_splits removes it",
       len(reps) == 1 and abs(float(fixed_o.loc[ex, "S01"]
                                    / fixed_c.shift(1).loc[ex, "S01"] - 1)) < 0.05,
       f"{len(reps)} repaired")

    # top-n selection and quantiles
    sc = pd.DataFrame(np.tile(np.arange(5.0), (10, 1)),
                      index=pd.bdate_range("2020-01-01", periods=10),
                      columns=list("abcde"))
    ck("topn_sel picks the top 2", list(topn_sel(sc, 2).iloc[0].values) ==
       [False, False, False, True, True])
    ck("quantile_sel respects MIN_NAMES",
       not quantile_sel(sc, 5, "hi").to_numpy().any())
    static = pd.DataFrame(False, index=pd.bdate_range("2020-01-01", periods=40),
                          columns=list("abcde"))
    static.iloc[:, :2] = True
    alt = static.copy()
    alt.iloc[1::2] = ~alt.iloc[1::2].to_numpy()
    ck("churn is 0 on a static book and 1 on an alternating one",
       churn(static) < 1e-12 and abs(churn(alt) - 1.0) < 1e-9,
       f"static {churn(static):.3f}, alternating {churn(alt):.3f}")
    ck("freeze cuts churn", churn(freeze(alt, 21)) < churn(alt),
       f"{churn(freeze(alt, 21)):.3f} vs {churn(alt):.3f}")

    # the close-vs-open identity that H18e rests on
    o_, c_ = bars["open"], bars["close"]
    t = 900
    rc = float(c_.iloc[t + 42]["S02"] / c_.iloc[t]["S02"] - 1)
    ro = float(c_.iloc[t + 42]["S02"] / o_.iloc[t + 1]["S02"] - 1)
    onn = float(o_.iloc[t + 1]["S02"] / c_.iloc[t]["S02"] - 1)
    ck("(1+Rclose)/(1+Ropen) = 1+overnight", abs((1 + rc) / (1 + ro) - (1 + onn)) < 1e-12)

    n_checks = 16
    print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)} "
          f"({n_checks - len(fails)}/{n_checks})")
    return 1 if fails else 0


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check-open", action="store_true",
                    help="daily bars vs 5-minute session frames")
    ap.add_argument("--force", action="store_true", help="refetch daily bars")
    ap.add_argument("--no-price-only", action="store_true",
                    help="skip the adjustment=split diagnostic")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    if a.check_open:
        check_open()
        return
    res = run(force=a.force, price_only=not a.no_price_only)
    report(res)
    RESULTS_JSON.write_text(json.dumps(res, indent=1, default=str))
    print(f"\nmachine-readable results -> {RESULTS_JSON.name}")


if __name__ == "__main__":
    main()
