"""H22 — net share issuance and gross profitability: do the two strongest free
NON-price signals sort returns where this repo's momentum composite does not?

MECHANISM (one sentence each, before any number)
  1. NET SHARE ISSUANCE — Pontiff-Woodgate (2008), Daniel-Titman (2006):
     managers issue equity when they believe the stock is overpriced and
     repurchase when they believe it is underpriced, so the twelve-month change
     in shares outstanding is a free quarterly read on the best-informed
     insider's valuation of the stock.
  2. GROSS PROFITABILITY — Novy-Marx (2013): gross profit over total assets
     measures productive capacity at the point in the income statement least
     contaminated by accounting discretion (depreciation policy, capitalisation,
     writedowns and R&D expensing all sit BELOW it), so it sorts returns where
     bottom-line earnings do not.

WHY THIS REPO CARES. Every signal it has ever ranked on is a function of past
prices, and its own gates lab measured the price composite sorting nothing
(decile 1 minus decile 10 = -0.099% at 5 td, -0.257% at 42 td). So the question
that decides whether either signal is worth building is NOT "does it sort" but
"does it sort ORTHOGONALLY to the momentum this engine already owns" — H22c
below, and the reason the double sort and the rank correlations are printed
before the P&L tables.

DATA (US equities only; no crypto, options, futures or FX)
  prices  scout/data.py daily SIP bars, split+dividend adjusted, for the 742
          tickers that were S&P 500 members at any point since 2016-01-01
          (scout/pit.py). 729 have bars. Membership is applied PER DATE, so a
          name only ranks on days it was actually in the index and delisted
          names stay in until their final print — no survivorship in the price
          universe.
  facts   scout/sec_bulk.py, the SEC's own bulk XBRL sets: 23.4M facts, 12,246
          companies, 2016-2026. pit_panel()/shares_panel()/net_issuance()
          enforce filing-date (not period-end) point-in-time discipline,
          first-filing-wins on restatements, split adjustment keyed on each
          fact's FILING date, and a consolidated-row (share-class) filter.
  bench   SPY, benchmark only.

NO LOOKAHEAD — WHERE THE SHIFT IS
  Two disciplines, both explicit.
  (a) FUNDAMENTAL point-in-time: a fact enters the panel on its SEC FILING date,
      never its period end, and when a period is filed twice the FIRST filing
      wins (sec_bulk.pit_panel). The measured reporting delay on this panel is
      a median of 37 days from period end, which is exactly the lookahead a
      backtest grants itself by conditioning on `ddate`.
  (b) PRICE: quintile weights are formed from data known at close t, and every
      portfolio applies `wbar.shift(1) * ret1` in `run_portfolio` — the one and
      only shift — so the earliest return a signal can touch is
      close(t) -> close(t+1). `--selftest` prices the mistake: the same-day
      return fed in as a signal scores ~0 bps through the shift and ~+400 bps
      without it.
  A third guard is needed because a forward-filled fundamental panel never
  expires: a fact is dropped once it is more than MAX_STALE_DAYS old, so a
  company that stopped filing stops having a signal instead of carrying its last
  10-K forever.

DATA DEBT, HANDLED EXPLICITLY (BACKTEST-REPORT.md: 5.1% of splits are unapplied
in Alpaca daily bars; SIRI prints a fake +925% one-day return, AAPL 2020-08-31 a
fake -74.2%). This lab does BOTH available guards and prints the count of each:
  1. repairs unapplied splits from Alpaca's OWN corporate-actions feed, only for
     events whose log ratio exceeds 0.35 (below that the 0.15 classifier cannot
     separate "adjusted" from "not adjusted" — it false-positived MET's 2017
     Brighthouse spin-off), and
  2. masks any residual |1-day return| > 45% out of both eligibility and the
     P&L, which catches spin-offs and reused tickers that no split feed knows
     about. Neither guard is optional and the masked cells are listed.

METHOD
  Quintiles formed cross-sectionally within each date among that date's eligible
  pool (point-in-time member, 21-session median dollar volume >= $10M, signal
  present and not stale). Equal weight. Held 42 sessions as 42 overlapping
  cohorts, which is simultaneously the repo's horizon and the phase-pooled
  estimator Rule 9 demands — a 21-td rebalance is run separately as H22g, with
  all 21 entry phases swept so the phase spread is visible rather than assumed.
  Costs 10 bps round trip on MEASURED turnover; break-even round-trip cost
  reported. Both halves split at the median date. Moving-block bootstrap by
  date, block = holding period (cluster-by-date, as scout/calibrate.py, plus the
  block that overlapping holds require). Newey-West(h) t-statistics. Every
  dollar-neutral book is regressed on SPY before its sign is quoted (Rule 13).

CONTROLS (four, none optional)
  random   random quintile assignment from the IDENTICAL eligible pool, 200
           draws — what separates "buyback names went up" from "S&P 500 names
           went up"
  placebo  each symbol permanently assigned another symbol's whole signal
           series, so every series keeps its own persistence and only the
           pairing breaks, 200 draws — H16 Finding 2 established this is the
           only honest null for a persistent signal
  shuffle  within-date permutation, 200 draws, reported WITH the SE ratio Rule
           14 requires so its anti-conservatism is visible
  bench    equal weight of the eligible pool, and SPY

VERDICT (measured 2026-08-09; every number here is printed by __main__)
  2,664 sessions, 2016-01-04 .. 2026-08-07, mean 490 eligible names per date.

  H22b/H22d/H22e/H22f REJECTED. H22c CONFIRMED. H22a NOT PROVEN — and the
  reason is sample size, not sign.

  H22a  net repurchase, h=42: +1.748 bps/day, block-bootstrap CI [-0.151,
        +3.720], NW t = 1.81. Both halves agree (+2.009 / +1.488), the sign is
        monotone in horizon (+1.631 / +1.748 / +1.819 at 21/42/126), Rule 13
        finds no beta (-0.001, alpha 4.42%/yr), the PLACEBO null is cleared
        (real +1.748 vs -0.050 +/- 0.643, z = 2.80), turnover is 0.013x/day so
        the break-even round-trip cost is 267 bps against the 10 bps charged,
        and Q5/Q1/pool annualise at 17.21 / 12.81 / 14.36%. Everything about it
        is right EXCEPT that it is not distinguishable from zero: on the honest
        effective sample — 56 NON-OVERLAPPING 42-session windows — it earns
        +0.685% per window at t = 1.59, positive in 57% of them. The repo's
        standalone bar is t > 3. DSR with the registry's N=14 is 0.470.
  H22b  GP/AT, h=42: -0.412 bps, WRONG SIGN, CI [-3.079, +2.099], and the
        halves flip (+0.984 / -1.807). Inside the placebo null (z = -0.40,
        p = 0.67). Rejected on its own pre-registered failure condition.
  H22c  THE DECIDING ROW, and the one durable result. Spearman to 12-1
        momentum is -0.015 (net repurchase) and +0.047 (GP/AT); to the GATED v5
        composite, computed with signals.composite_at exactly as the scan
        computes it, +0.010 and +0.042. These are ORTHOGONAL to everything this
        repo owns — the first signal here that is not a function of past prices.
        But read the double sort before celebrating: the net-repurchase spread
        is +94.4 / +88.2 / +13.0 bps across momentum terciles T1/T2/T3. It is
        real where momentum is weak and GONE where momentum is strong — which
        is precisely the region the v5 gates (SMA200, positive 6-month return)
        confine the engine to. Orthogonal and inaccessible at the same time.
  H22d  combo +1.272 < net repurchase alone +1.748. Fails.
  H22e  Q5 net 17.12%/yr at Sharpe 0.819 vs SPY 15.82% at Sharpe 0.884. Beats
        SPY on RETURN, loses on Sharpe. Fails as pre-registered.
  H22f  derived-GP and direct-tag GP agree (-0.412 vs -0.306), so the
        Revenue-minus-COGS derivation is not what killed H22b.
  H22g  21 monthly phases: mean +1.756, sd 0.049, min +1.655, max +1.846
        against a phase-pooled +1.748. Phase choice is worth 2.8% of the
        effect; Rule 9 is satisfied and the estimator is not a lucky schedule.

  METHOD NOTE worth more than the verdict. `n_eff` computed from the daily
  series reports 3,220 at h=42 against n_days = 2,664 — MORE independent
  observations than there are days. That is not a bug, it is what happens when
  a long-short book's daily returns are serially uncorrelated while its
  POSITIONS turn over quarterly. Any lab here that quotes a daily-series n_eff
  for a slow signal is flattering itself by ~50x. The number to read is
  n_indep: 56 windows.

RUN
  python -m scout.fundamental_lab              # everything (~6 min warm)
  python -m scout.fundamental_lab --selftest   # offline, synthetic, no keys
  python -m scout.fundamental_lab --quick      # h=42 only, 50 control draws
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

from . import config, data as daily_data, growth, intraday, pit, sec_bulk, signals

# --------------------------------------------------------------------------
# knobs — all fixed ex ante, none tuned on an outcome
# --------------------------------------------------------------------------
HORIZONS = (21, 42, 126)          # 42 is the registered headline (repo horizon)
PRIMARY_H = 42
N_QUANTILES = 5
COST_BPS_ROUND_TRIP = 10.0        # large caps; one-way = half of this
MIN_DOLLAR_VOL = config.MIN_DOLLAR_VOL     # $10M, the engine's own gate
LIQ_WINDOW = 21
MIN_NAMES = 50                    # smallest cross-section that may be quintiled
MAX_STALE_DAYS = 400              # a fact older than this is not information
EXTREME_RET = 0.45                # |1-day return| guard (split/spin-off debt)
MIN_REPAIR_LOG_RATIO = 0.35       # below this the split classifier cannot decide
ISSUANCE_LOOKBACK = 252           # 12-month change in shares
MAX_LOG_SHARE_CHANGE = 1.0        # residual data guard, not a signal knob:
                                  # the honest signal's 1st/99th percentiles are
                                  # -0.37/+0.17, so |log change| > 1 (a factor of
                                  # e in a year) is a filing artifact, not a
                                  # capital-structure decision
REBAL_STRIDE = 21                 # "monthly" variant (H22g)
N_CONTROL_DRAWS = 200
BOOT_REPS = 2000
SEED = 20260809
#: H22a 3 + H22b 3 + H22c 2 + H22d 1 + H22e 2 + H22f 1 + H22g 2
N_TRIALS_REGISTERED = 14

BARS_PICKLE = config.SCOUT_DIR / "cache_fundlab_bars.pkl"
FACTS_PICKLE = config.SCOUT_DIR / "cache_fundlab_facts.pkl"
DATASET_PICKLE = config.SCOUT_DIR / "cache_fundlab_dataset.pkl"
SPLIT_AUDIT_JSON = config.SCOUT_DIR / "cache_fundlab_splitaudit.json"
BENCH = "SPY"
TDAYS = 252.0

REVENUE_TAGS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues")
COGS_TAGS = ("CostOfGoodsAndServicesSold", "CostOfRevenue")
FACT_TAGS = ("GrossProfit", "Assets", "StockholdersEquity",
             *REVENUE_TAGS, *COGS_TAGS, *[t for t, _ in sec_bulk.SHARE_TAGS])


# --------------------------------------------------------------------------
# small statistics helpers (scipy is not installed in this repo)
# --------------------------------------------------------------------------

def _nw_t(x: np.ndarray, lags: int) -> float:
    """Newey-West t for the mean of a serially-correlated series. Overlapping
    h-day holds make adjacent observations dependent by construction; an OLS t
    on that series is inflated by roughly sqrt(h)."""
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
    """Moving-block bootstrap CI for the mean. One observation per DATE, so
    resampling dates IS the cluster-by-date bootstrap scout/calibrate.py uses;
    the block additionally respects the overlapping holding period."""
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


def _sharpe(x) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 5 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * math.sqrt(TDAYS))


def _n_eff(x: np.ndarray, block: int) -> float:
    """Effective independent sample: the block bootstrap's variance against the
    iid variance. Overlapping windows are not independent and this repo says so
    everywhere; this is the number that says by how much."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3 * block or x.std(ddof=1) == 0:
        return float("nan")
    nw = _nw_t(x, block)
    if not np.isfinite(nw) or nw == 0:
        return float("nan")
    se_nw = abs(x.mean() / nw)
    se_iid = x.std(ddof=1) / math.sqrt(n)
    return float(n * (se_iid / se_nw) ** 2)


def nonoverlap_blocks(x: pd.Series, h: int) -> dict:
    """Cumulate a daily P&L into NON-OVERLAPPING h-session windows.

    This is the effective independent sample the repo's standards ask for, and
    for a slow signal it is the honest one. `n_eff` computed from the daily
    series comes out at or above n_days because a long-short book's DAILY
    returns are close to serially uncorrelated even when its WEIGHTS barely
    move — which flatters the sample size enormously. Ten years of daily P&L
    driven by quarterly filings and a 42-session hold contains about 63
    independent windows, not 2,600 independent days, and that is the number a
    t-statistic here should be read against."""
    v = x.dropna().to_numpy()
    n = (len(v) // h) * h
    if n < 2 * h:
        return {"n_blocks": 0, "mean_%": float("nan"), "t": float("nan"),
                "share_positive": float("nan")}
    b = v[:n].reshape(-1, h).sum(axis=1)
    t = (float(b.mean() / (b.std(ddof=1) / math.sqrt(len(b))))
         if b.std(ddof=1) > 0 else float("nan"))
    return {"n_blocks": int(len(b)), "mean_%": 100 * float(b.mean()), "t": t,
            "share_positive": float((b > 0).mean())}


def xrank(frame: pd.DataFrame) -> pd.DataFrame:
    """Within-date uniform rank in [-0.5, +0.5]; NaN stays NaN."""
    r = frame.rank(axis=1)
    n = frame.notna().sum(axis=1)
    return r.sub(1.0).div((n - 1).replace(0, np.nan), axis=0) - 0.5


def xquantile(frame: pd.DataFrame, q: int = N_QUANTILES) -> pd.DataFrame:
    """Within-date quantile label 1..q from average ranks (ties share a bucket)."""
    pct = frame.rank(axis=1, pct=True)
    return np.ceil(pct * q).where(frame.notna())


def _spearman(a: pd.Series, b: pd.Series) -> float:
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 5:
        return float("nan")
    return float(d["a"].rank().corr(d["b"].rank()))


# --------------------------------------------------------------------------
# prices — fetch, split-repair, extreme-return guard, liquidity, membership
# --------------------------------------------------------------------------

def load_bars(force: bool = False, verbose: bool = True) -> dict:
    """Daily SIP bars for the point-in-time S&P 500 union, split-repaired."""
    if BARS_PICKLE.exists() and not force:
        bars = pd.read_pickle(BARS_PICKLE)
    else:
        syms = sorted(set(pit.all_members_since("2016-01-01")) | {BENCH})
        if verbose:
            print(f"fetching daily bars for {len(syms)} symbols ...")
        bars = daily_data.daily_ohlcv(syms, 3960)
        pd.to_pickle(bars, BARS_PICKLE)
    o, c, v = bars["open"].copy(), bars["close"].copy(), bars["volume"].copy()
    c, v, o, repairs, ambiguous, events = repair_splits(c, v, o, verbose=verbose)
    return {"open": o, "close": c, "volume": v, "events": events,
            "repairs": repairs, "ambiguous": ambiguous}


def split_factor_map(events: dict) -> dict[str, list[tuple[pd.Timestamp, float]]]:
    """intraday.split_events() -> the {symbol: [(ex_date, factor)]} shape
    sec_bulk.shares_panel wants.

    Sourced from intraday rather than sec_bulk.split_factors because the latter
    goes through data_audit.fetch_splits, which prints and continues on an HTTP
    429: at 729 symbols one throttled chunk silently returned no splits at all
    for ~30 names, leaving their share counts unadjusted. intraday._get retries
    429s with backoff, so the map is complete or it raises."""
    out: dict[str, list[tuple[pd.Timestamp, float]]] = {}
    for sym, evs in events.items():
        for e in evs:
            f = float(e["ratio"])
            if f > 0 and abs(f - 1.0) > 1e-9:
                out.setdefault(sym, []).append((pd.Timestamp(e["ex_date"]), f))
    for k in out:
        out[k].sort()
    return out


def repair_splits(close: pd.DataFrame, volume: pd.DataFrame, open_: pd.DataFrame,
                  verbose: bool = True):
    """Back-adjust splits Alpaca's bar pipeline failed to apply.

    Anchored on Alpaca's own corporate-actions feed, so it cannot invent a split
    that did not happen. Only unambiguous events are touched (see
    MIN_REPAIR_LOG_RATIO); ambiguous ones are printed, not silently applied and
    not silently dropped."""
    if SPLIT_AUDIT_JSON.exists():
        events = {k: [{"ex_date": pd.Timestamp(e["ex_date"]), "ratio": e["ratio"],
                       "kind": e["kind"]} for e in v]
                  for k, v in json.loads(SPLIT_AUDIT_JSON.read_text()).items()}
    else:
        events = intraday.split_events(list(close.columns),
                                       close.index.min(), close.index.max())
        SPLIT_AUDIT_JSON.write_text(json.dumps(
            {k: [{"ex_date": str(e["ex_date"].date()), "ratio": e["ratio"],
                  "kind": e["kind"]} for e in v] for k, v in events.items()}, indent=1))
    repairs, ambiguous = [], []
    for sym, evs in events.items():
        if sym not in close.columns:
            continue
        s = close[sym].dropna()
        s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
        for b in intraday.unapplied_splits_close(s, evs):
            if b.get("applied") is not False:
                continue                          # jump not at the split ratio
            if abs(math.log(b["ratio"])) < MIN_REPAIR_LOG_RATIO:
                ambiguous.append({"symbol": sym, "ex_date": str(b["ex_date"].date()),
                                  "ratio": b["ratio"], "jump": b["jump"]})
                continue
            ex = pd.Timestamp(b["ex_date"])
            mask = close.index.tz_localize(None).normalize() < ex
            close.loc[mask, sym] = close.loc[mask, sym] / b["ratio"]
            open_.loc[mask, sym] = open_.loc[mask, sym] / b["ratio"]
            volume.loc[mask, sym] = volume.loc[mask, sym] * b["ratio"]
            repairs.append({"symbol": sym, "ex_date": str(ex.date()),
                            "ratio": b["ratio"], "n_bars": int(mask.sum())})
    if verbose:
        for r in repairs:
            print(f"  SPLIT REPAIR {r['symbol']} {r['ex_date']} ratio "
                  f"{r['ratio']:.3g} -> {r['n_bars']:,} bars rescaled")
        if not repairs:
            print("  split audit: nothing unapplied")
        for a in ambiguous[:10]:
            print(f"  split audit AMBIGUOUS (not repaired, left to the 45% mask): "
                  f"{a['symbol']} {a['ex_date']} filed ratio {a['ratio']:.3f}, "
                  f"observed jump {a['jump']:.4f}")
        if len(ambiguous) > 10:
            print(f"  ... and {len(ambiguous) - 10} more ambiguous events")
    return close, volume, open_, repairs, ambiguous, events


def extreme_mask(ret1: pd.DataFrame, thresh: float = EXTREME_RET) -> pd.DataFrame:
    """True where |1-day return| exceeds `thresh` — the residual split /
    spin-off / reused-ticker debt no corporate-actions feed covers. These cells
    are removed from BOTH eligibility and the P&L: we do not know the true
    return, so neutralising it is the honest choice, not keeping a number the
    audit says is fabricated."""
    return ret1.abs() > thresh


def membership_mask(dates: pd.DatetimeIndex, cols: list[str]) -> pd.DataFrame:
    """Point-in-time S&P 500 membership: True where the name was ACTUALLY in
    the index that day. This is what kills survivorship in the price universe —
    it is not the same as (and does not fix) the ticker-map survivorship in the
    SEC data, which is reported separately in the coverage block."""
    idx = {c: i for i, c in enumerate(cols)}
    a = np.zeros((len(dates), len(cols)), dtype=bool)
    prev_key, prev_row = None, None
    for r, d in enumerate(dates):
        key = d.date()
        if key != prev_key:
            row = np.zeros(len(cols), dtype=bool)
            for t in pit.members(key):
                j = idx.get(t)
                if j is not None:
                    row[j] = True
            prev_key, prev_row = key, row
        a[r] = prev_row
    return pd.DataFrame(a, index=dates, columns=cols)


def liquidity_mask(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """Tradeable-at-10bps gate from data THROUGH t only. Doubles as the
    ticker-reuse and stale-print guard: a delisted name whose last close keeps
    printing at zero volume fails the dollar-volume floor immediately."""
    med = (close * volume).rolling(LIQ_WINDOW, min_periods=LIQ_WINDOW).median()
    return (med >= MIN_DOLLAR_VOL) & close.notna()


# --------------------------------------------------------------------------
# fundamentals
# --------------------------------------------------------------------------

def normalize_share_units(sh: pd.DataFrame, verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    """Undo the UNITS switches the SEC bulk share counts carry between filings.

    A defect found here, not previously documented, and fatal to this signal if
    left alone. Filers tag share counts in units, thousands or millions and
    change scale from one filing to the next. Measured on this panel:

        MCD   WeightedAverageDiluted, q4:  ... 7.413e8 (2023-02) then 732.3 (2024-02)
        COP   WeightedAverageDiluted, q4:  1.246e6 (2016) ... then 1.278e9 (2023)
        GRMN  CommonStockSharesOutstanding: alternates 1.9e5 and 1.9e8 EVERY YEAR
              (the 10-K reports thousands, the 10-Qs report units)
        PCAR  WeightedAverageDiluted, q4:  527.7 sitting between two 5.2e8s

    sec_bulk._despike catches only the third of those — an isolated single value
    between two neighbours that agree. A permanent scale change (MCD, COP) looks
    exactly like a corporate event, and an alternating one (GRMN) has no
    agreeing neighbours to compare against. Left in, MCD reads as a 99.9999%
    buyback and COP as a 100,000% issuance, and both land in the extreme
    quintile of every sort. 0.53% of this panel's 12-month changes exceeded a
    factor of e before this repair; the 1st and 99th percentiles of the honest
    signal are -37% and +17%.

    The repair needs no threshold to tune, because filers only ever use powers
    of one thousand: each observation is divided by 10^(3k) where k is its
    log10 distance from the ticker's own median scale, rounded to the nearest
    multiple of 3. An observation has to be more than ~31x from the ticker's
    usual magnitude before k is non-zero, and no S&P 500 company changes its
    share count by 31x in a year, so this can undo a units switch and cannot
    erase an issuance. The absolute level afterwards may be in thousands or in
    units depending on which scale the ticker used more often — irrelevant,
    because the signal is a LOG CHANGE and is scale-invariant once consistent."""
    out = sh.copy()
    fixed: dict[str, int] = {}
    for c in sh.columns:
        v = sh[c].dropna()
        v = v[v > 0]
        if len(v) < 2:
            continue
        distinct = v[v != v.shift()]
        lg = np.log10(distinct)
        k = np.round((np.log10(v) - float(lg.median())) / 3.0)
        bad = k != 0
        if bad.any():
            out.loc[v.index[bad], c] = v[bad] / (10.0 ** (3 * k[bad]))
            fixed[c] = int(bad.sum())
    meta = {"tickers_repaired": len(fixed), "cells_repaired": int(sum(fixed.values())),
            "worst": dict(sorted(fixed.items(), key=lambda kv: -kv[1])[:12])}
    if verbose:
        print(f"  share-count UNIT repair: {meta['cells_repaired']:,} daily cells "
              f"over {meta['tickers_repaired']} tickers rescaled by a power of 1000")
        print(f"    worst offenders: {meta['worst']}")
    return out, meta


def load_facts(tickers: list[str], verbose: bool = True) -> pd.DataFrame:
    """The SEC bulk facts, filtered once to this universe and these tags.

    facts.pkl is 23.4M rows / 2.1 GB; the subset is 2.1M rows / 223 MB, which is
    the difference between a lab that reloads in 2 seconds and one that does not
    fit in memory next to a price panel."""
    if FACTS_PICKLE.exists():
        return pd.read_pickle(FACTS_PICKLE)
    if verbose:
        print("building the fundamental subset from scout/cache_secbulk/facts.pkl ...")
    facts = sec_bulk.load()
    sub = facts[facts["ticker"].isin(set(tickers))
                & facts["tag"].isin(set(FACT_TAGS))].copy()
    sub.to_pickle(FACTS_PICKLE)
    return sub


def staleness_days(facts: pd.DataFrame, tickers: list[str],
                   dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Days since the ticker's most recent SEC filing, as of each date.

    A forward-filled fundamental panel never expires on its own: a company that
    stops filing keeps its last 10-K forever and quietly stays in the
    cross-section for years. This is the expiry."""
    last = (facts.groupby(["ticker", "filed"]).size().reset_index()[["ticker", "filed"]])
    out = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    tz = dates.tz
    naive = dates.tz_localize(None) if tz is not None else dates
    for tk, g in last.groupby("ticker"):
        if tk not in out.columns:
            continue
        f = pd.Series(g["filed"].to_numpy(), index=g["filed"].to_numpy()).sort_index()
        f = f[~f.index.duplicated(keep="last")]
        aligned = f.reindex(f.index.union(naive)).ffill().reindex(naive)
        out[tk] = (naive - pd.DatetimeIndex(aligned.to_numpy())).days
    return out


def _pick_tag(df: pd.DataFrame, preference: tuple[str, ...]) -> pd.DataFrame:
    """One row per (ticker, adsh, ddate), taking the preferred tag when a filing
    carries several. Revenue moved from `Revenues` to
    `RevenueFromContractWithCustomerExcludingAssessedTax` at ASC 606, so both
    must be accepted; taking them WITHIN a filing (not across time) is what stops
    the tag switch from manufacturing a jump."""
    order = {t: i for i, t in enumerate(preference)}
    d = df[df["tag"].isin(preference)].copy()
    d["_pref"] = d["tag"].map(order)
    d = d.sort_values(["ticker", "adsh", "ddate", "_pref"])
    return d.drop_duplicates(subset=["ticker", "adsh", "ddate"], keep="first")


def gross_profitability_facts(facts: pd.DataFrame, verbose: bool = True
                              ) -> tuple[pd.DataFrame, dict]:
    """Annual GP / total assets, assembled at the FACT level so the numerator
    and denominator come from the same fiscal period and the same filing.

    Two things this gets right that a panel-level division does not:
      - GP and Assets are joined on (ticker, ddate), so the ratio is never
        annual profit over a random later quarter's balance sheet;
      - `filed` is the LATER of the two components' filing dates, so the ratio
        becomes visible only when both halves of it were public.

    Only 237 of the 593 mapped tickers tag `GrossProfit` directly. The rest use
    Revenue minus cost of revenue from the same filing. The choice is made ONCE
    per ticker and held — switching source mid-series manufactures a jump, which
    is the same failure sec_bulk.shares_panel guards against for share counts.
    Financials genuinely have no gross profit; Novy-Marx excludes them, and here
    they simply drop out of the panel."""
    cons = facts[facts["segments"].isna() & facts["coreg"].isna()]
    ann = cons[cons["qtrs"] == 4]

    real = ann[ann["tag"] == "GrossProfit"][["ticker", "adsh", "ddate", "value", "filed"]]
    real_tickers = set(real["ticker"].unique())

    rev = _pick_tag(ann, REVENUE_TAGS)[["ticker", "adsh", "ddate", "value", "filed"]]
    cogs = _pick_tag(ann, COGS_TAGS)[["ticker", "adsh", "ddate", "value", "filed"]]
    derived = rev.merge(cogs, on=["ticker", "adsh", "ddate"], suffixes=("_r", "_c"))
    derived["value"] = derived["value_r"] - derived["value_c"]
    derived["filed"] = derived[["filed_r", "filed_c"]].max(axis=1)
    derived = derived[["ticker", "adsh", "ddate", "value", "filed"]]
    derived = derived[~derived["ticker"].isin(real_tickers)]

    gp = pd.concat([real, derived], ignore_index=True)
    source = ({t: "GrossProfit" for t in real_tickers}
              | {t: "Revenue-COGS" for t in set(derived["ticker"].unique())})

    assets = (cons[(cons["tag"] == "Assets") & (cons["qtrs"] == 0) & (cons["value"] > 0)]
              [["ticker", "ddate", "value", "filed"]]
              .sort_values("filed")
              .drop_duplicates(subset=["ticker", "ddate"], keep="first"))

    m = gp.merge(assets, on=["ticker", "ddate"], suffixes=("_gp", "_at"))
    m["value"] = m["value_gp"] / m["value_at"]
    m["filed"] = m[["filed_gp", "filed_at"]].max(axis=1)
    m = m[np.isfinite(m["value"])]
    out = m[["ticker", "ddate", "value", "filed"]].copy()
    out["tag"] = "GPOA"
    out["qtrs"] = 4
    out["segments"] = np.nan
    out["coreg"] = np.nan
    meta = {"source": source,
            "n_real": int(len(real_tickers)),
            "n_derived": int(len(set(derived["ticker"].unique()))),
            "n_rows": int(len(out)),
            "tickers": int(out["ticker"].nunique())}
    if verbose:
        print(f"  GP/AT: {meta['n_rows']:,} annual observations over "
              f"{meta['tickers']} tickers "
              f"({meta['n_real']} tag GrossProfit directly, "
              f"{meta['n_derived']} use Revenue-COGS)")
    return out, meta


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
    o, c, v = bars["open"], bars["close"], bars["volume"]
    dates = c.index
    bench = c[BENCH].copy() if BENCH in c.columns else None
    cols = [s for s in c.columns if s != BENCH]

    ret1_all = c.pct_change()
    ext = extreme_mask(ret1_all)
    ret1 = ret1_all.mask(ext)
    if verbose:
        top = (ret1_all.where(ext).stack().abs().sort_values(ascending=False).head(8))
        print(f"  extreme-return mask: {int(ext.to_numpy().sum())} cells with "
              f"|1d return| > {EXTREME_RET:.0%} removed from eligibility AND P&L")
        for (d, s), val in top.items():
            print(f"    {s:6s} {str(d.date())}  "
                  f"{100 * ret1_all.loc[d, s]:+9.1f}%")

    tickers = list(cols)
    facts = load_facts(tickers, verbose=verbose)
    if verbose:
        print(f"  facts subset: {len(facts):,} rows, "
              f"{facts['ticker'].nunique()} of {len(tickers)} tickers mapped")

    # signal 1 — 12-month log change in split-adjusted shares outstanding.
    # NEGATIVE = buyback, so the tradeable score is its negation ("net
    # repurchase"), which keeps every table's Q5 the side the mechanism favours.
    # sec_bulk.shares_panel carries the four disciplines that were bugs before
    # they were fixed (consolidated/share-class filter, first-filing-wins,
    # split adjustment keyed on FILING date, one tag chosen per ticker and
    # held). The unit repair is layered on top of its output; the 252-session
    # log change is then taken here, which is exactly what net_issuance() does.
    factors = split_factor_map(bars["events"])
    shares_raw = sec_bulk.shares_panel(facts, tickers, dates, factors=factors)
    shares, unit_meta = normalize_share_units(shares_raw, verbose=verbose)
    iss = np.log(shares / shares.shift(ISSUANCE_LOOKBACK))
    iss = iss.where(np.isfinite(iss))
    implausible = iss.abs() > MAX_LOG_SHARE_CHANGE
    n_implausible = int(implausible.to_numpy().sum())
    iss = iss.mask(implausible)
    if verbose:
        print(f"  residual implausible issuance cells dropped "
              f"(|12m log share change| > {MAX_LOG_SHARE_CHANGE}): {n_implausible:,}")
    repurch = -iss

    # signal 2 — gross profit / total assets, point-in-time
    gpoa_facts, gp_meta = gross_profitability_facts(facts, verbose=verbose)
    gpoa = sec_bulk.pit_panel(gpoa_facts, "GPOA", tickers, dates, qtrs=4)
    real_only = [t for t, s in gp_meta["source"].items() if s == "GrossProfit"]
    gpoa_real = gpoa.reindex(columns=tickers)
    gpoa_real = gpoa_real.where(
        pd.DataFrame(np.tile([t in set(real_only) for t in tickers], (len(dates), 1)),
                     index=dates, columns=tickers))

    stale = staleness_days(facts, tickers, dates)
    fresh = stale.le(MAX_STALE_DAYS).fillna(False)

    # price features — the momentum this repo already owns
    frames = signals.feature_frames(o[cols], c[cols], v[cols])
    mom12 = frames["mom"]

    mem = membership_mask(dates, tickers)
    liq = liquidity_mask(c[cols], v[cols])
    ok = mem & liq & ret1[cols].notna() & ~ext[cols]

    ds = {
        "version": 2,
        "dates": dates, "close": c[cols], "ret1": ret1[cols], "bench": bench,
        "eligible": ok, "membership": mem, "liquidity": liq, "fresh": fresh,
        "repurchase": repurch.reindex(columns=tickers),
        "issuance_raw": iss.reindex(columns=tickers),
        "gpoa": gpoa.reindex(columns=tickers),
        "gpoa_real": gpoa_real,
        "mom12": mom12.reindex(columns=tickers),
        "frames": {k: f for k, f in frames.items()},
        "gp_meta": gp_meta, "unit_meta": unit_meta,
        "n_implausible_issuance": n_implausible,
        "repairs": bars["repairs"], "ambiguous": bars["ambiguous"],
        "n_extreme": int(ext.to_numpy().sum()),
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }
    pd.to_pickle(ds, DATASET_PICKLE)
    if verbose:
        print(f"dataset built in {time.time() - t0:.0f}s -> {DATASET_PICKLE.name}")
    return ds


def eligible_signal(ds: dict, name: str) -> pd.DataFrame:
    """The named signal restricted to the eligible pool, with dates that cannot
    support a quintile sort dropped entirely."""
    sig = ds[name]
    ok = ds["eligible"] & ds["fresh"] & sig.notna()
    enough = ok.sum(axis=1).ge(MIN_NAMES)
    ok = ok.mul(enough, axis=0).astype(bool)
    return sig.where(ok)


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
    """Equal weight of the IDENTICAL eligible pool — the matched benchmark."""
    sel = score.notna()
    n = sel.sum(axis=1)
    return sel.div(n.replace(0, np.nan), axis=0).fillna(0.0)


def cohort_weights(w: pd.DataFrame, h: int,
                   reb: pd.Series | None = None) -> pd.DataFrame:
    """Average of the cohorts still alive: each formation date starts a book
    held h sessions, and the portfolio is the equal-weighted average of the
    books currently open.

    With `reb=None` every session is a formation date, which is the
    phase-pooled estimator Rule 9 requires (it averages all h possible entry
    schedules instead of picking one). With `reb` a 21-td stride it is the
    literal monthly rebalance, and `phase_sweep` then reports what the choice
    of phase was worth."""
    if reb is None:
        return w.rolling(h, min_periods=1).mean()
    wsig = w.mul(reb.astype(float), axis=0)
    num = wsig.fillna(0.0).rolling(h, min_periods=1).sum()
    den = reb.astype(float).rolling(h, min_periods=1).sum()
    return num.div(den.replace(0, np.nan), axis=0)


def run_portfolio(wbar: pd.DataFrame, ret1: pd.DataFrame, h: int,
                  cost_bps: float = COST_BPS_ROUND_TRIP) -> dict:
    """Daily P&L of an already-cohort-averaged weight frame.

    THE SHIFT LIVES HERE: `wbar.shift(1) * ret1`. wbar_t is built from
    information known at close t; ret1_t is earned close(t-1)->close(t); shifting
    the weights one bar forward means the first return the signal can touch is
    close(t)->close(t+1)."""
    r = ret1.reindex(columns=wbar.columns)
    gross = (wbar.shift(1) * r.fillna(0.0)).sum(axis=1)
    dropped = int(((wbar.shift(1).fillna(0.0) != 0) & r.isna()).to_numpy().sum())
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
            "sharpe_gross": _sharpe(gross), "sharpe_net": _sharpe(net),
            "t_gross": _nw_t(gross.to_numpy(), h),
            "mean_turnover": mt, "breakeven_bps": be, "n_days": int(len(gross)),
            "nan_ret_cells": dropped}


def halves(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    mid = len(series) // 2
    return series.iloc[:mid], series.iloc[mid:]


def market_adjust(port: pd.Series, bench_ret: pd.Series, h: int) -> dict:
    """Rule 13: regress every dollar-neutral book on SPY before quoting its sign.
    A dollar-neutral quintile spread is not market-neutral, and in a decade when
    SPY compounded near 16%/yr a 0.15 unintended beta is worth 2.4%/yr."""
    df = pd.DataFrame({"p": port, "m": bench_ret.reindex(port.index)}).dropna()
    if len(df) < 50:
        return {"beta": np.nan, "alpha_ann_%": np.nan, "t_alpha": np.nan}
    m = df["m"].to_numpy()
    A = np.column_stack([np.ones(len(m)), m])
    beta, *_ = np.linalg.lstsq(A, df["p"].to_numpy(), rcond=None)
    resid = df["p"].to_numpy() - A @ beta
    return {"beta": float(beta[1]), "alpha_ann_%": 100 * _ann(float(beta[0])),
            "t_alpha": _nw_t(resid + beta[0], h)}


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def shuffled(score: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Permute the signal across symbols WITHIN each date."""
    a = score.to_numpy(copy=True)
    for i in range(a.shape[0]):
        row = a[i]
        idx = np.flatnonzero(np.isfinite(row))
        if len(idx) > 1:
            row[idx] = row[rng.permutation(idx)]
    return pd.DataFrame(a, index=score.index, columns=score.columns)


def placebo(full: pd.DataFrame, mask: pd.DataFrame,
            rng: np.random.Generator) -> pd.DataFrame:
    """Give every symbol ANOTHER symbol's whole signal series (a derangement),
    then re-impose the real eligibility mask. Each series keeps its own
    persistence, era drift and reporting cadence; only the pairing dies. H16
    Finding 2: this is the null that reproduces the real series' width, while
    within-date permutation is 2-3x too tight."""
    cols = list(full.columns)
    n = len(cols)
    perm = rng.permutation(n)
    for _ in range(50):
        if not np.any(perm == np.arange(n)):
            break
        perm = rng.permutation(n)
    out = full.iloc[:, perm].copy()
    out.columns = cols
    return out.where(mask)


def random_scores(mask: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    a = rng.random(mask.shape)
    return pd.DataFrame(a, index=mask.index, columns=mask.columns).where(mask)


def control_null(kind: str, score: pd.DataFrame, full: pd.DataFrame,
                 ret1: pd.DataFrame, h: int, draws: int = N_CONTROL_DRAWS,
                 seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed + h)
    mask = score.notna()
    means = []
    for _ in range(draws):
        if kind == "shuffle":
            s = shuffled(score, rng)
        elif kind == "placebo":
            s = placebo(full, mask, rng)
        elif kind == "random":
            s = random_scores(mask, rng)
        else:
            raise ValueError(kind)
        means.append(run_portfolio(cohort_weights(ls_weights(s), h), ret1, h)["mean_gross"])
    means = np.array(means)
    return {"kind": kind, "draws": draws, "means": means,
            "mean": float(means.mean()), "sd": float(means.std(ddof=1))}


# --------------------------------------------------------------------------
# H22c — the deciding row: is any of this just momentum?
# --------------------------------------------------------------------------

def rank_correlations(ds: dict, sig: pd.DataFrame, reb_dates: pd.DatetimeIndex,
                      cols: list[str]) -> dict:
    """Cross-sectional Spearman of the signal against (a) raw 12-1 momentum over
    the same eligible pool and (b) the repo's gated v5 composite score, computed
    date by date and summarised over dates.

    (b) is the number that matters commercially: the composite is what the
    engine actually ranks on, and it is computed here EXACTLY as scan and
    calibration compute it — same gates, same vetoes, same weights — restricted
    to that date's point-in-time members."""
    frames = ds["frames"]
    rho_mom, rho_comp, n_comp, overlap = [], [], [], []
    for ts in reb_dates:
        s = sig.loc[ts].dropna()
        if len(s) < MIN_NAMES:
            continue
        m = ds["mom12"].loc[ts].reindex(s.index)
        rho_mom.append(_spearman(s, m))
        mem = [c for c in cols if ds["membership"].loc[ts, c]]
        sub = {k: f.loc[[ts], mem] for k, f in frames.items()}
        try:
            comp = signals.composite_at(sub, ts)
        except Exception:
            continue
        if comp.empty:
            continue
        common = s.index.intersection(comp.index)
        n_comp.append(len(comp))
        overlap.append(len(common))
        if len(common) >= 20:
            rho_comp.append(_spearman(s.reindex(common), comp["score"].reindex(common)))
    f = lambda a: (float(np.nanmean(a)) if len(a) else float("nan"),
                   float(np.nanstd(a, ddof=1)) if len(a) > 1 else float("nan"))
    mm, ms = f(rho_mom)
    cm, cs = f(rho_comp)
    return {"rho_mom12_mean": mm, "rho_mom12_sd": ms, "n_dates_mom": len(rho_mom),
            "rho_composite_mean": cm, "rho_composite_sd": cs,
            "n_dates_comp": len(rho_comp),
            "gated_pool_mean": float(np.mean(n_comp)) if n_comp else float("nan"),
            "overlap_mean": float(np.mean(overlap)) if overlap else float("nan")}


def double_sort(sig: pd.DataFrame, mom: pd.DataFrame, fwd: pd.DataFrame,
                n: int = 3) -> pd.DataFrame:
    """Mean forward return by (momentum tercile) x (signal tercile).

    Momentum is sorted FIRST on purpose: if the fundamental spread only exists
    across momentum terciles and not within them, the signal is momentum in an
    accountant's costume and adds nothing to an engine that already ranks on
    momentum."""
    sl = xquantile(sig, n).to_numpy()
    ml = xquantile(mom.where(sig.notna()), n).to_numpy()
    f = fwd.to_numpy()
    good = np.isfinite(sl) & np.isfinite(ml) & np.isfinite(f)
    grid = np.full((n, n), np.nan)
    cnt = np.zeros((n, n), int)
    for a in range(1, n + 1):
        for b in range(1, n + 1):
            m = good & (ml == a) & (sl == b)
            cnt[a - 1, b - 1] = int(m.sum())
            if m.sum():
                grid[a - 1, b - 1] = float(np.nanmean(f[m]))
    df = pd.DataFrame(1e4 * grid, index=[f"mom T{i}" for i in range(1, n + 1)],
                      columns=[f"sig T{i}" for i in range(1, n + 1)])
    df["spread(T3-T1)"] = df.iloc[:, n - 1] - df.iloc[:, 0]
    df["n_obs"] = cnt.sum(axis=1)
    return df


def phase_sweep(sig: pd.DataFrame, ret1: pd.DataFrame, h: int,
                stride: int = REBAL_STRIDE) -> pd.DataFrame:
    """Rule 9: every one of the `stride` possible monthly entry schedules, not
    the one that happens to start on day zero. H7a showed the repo had been
    quoting the luckiest of six such schedules."""
    w = ls_weights(sig)
    rows = []
    for off in range(stride):
        reb = pd.Series(False, index=sig.index)
        reb.iloc[off::stride] = True
        res = run_portfolio(cohort_weights(w, h, reb), ret1, h)
        rows.append({"phase": off, "mean_bps": 1e4 * res["mean_gross"],
                     "ann_gross_%": 100 * res["ann_gross"],
                     "turnover": res["mean_turnover"],
                     "sharpe": res["sharpe_gross"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------

SIGNALS = (("repurchase", "H22a  net repurchase = -1 x 12m log change in shares"),
           ("gpoa", "H22b  gross profit / total assets"),
           ("combo", "H22d  equal-weight average of the two ranks"),
           ("gpoa_real", "H22f  GP/AT, tickers that tag GrossProfit directly"))


def _fwd(close: pd.DataFrame, h: int) -> pd.DataFrame:
    """close(t) -> close(t+h). Uses no price before t; aligned to t."""
    return close.shift(-h) / close - 1.0


def run(horizons=HORIZONS, draws=N_CONTROL_DRAWS, verbose: bool = True) -> dict:
    ds = build_dataset(verbose=verbose)
    close, ret1 = ds["close"], ds["ret1"]
    cols = list(close.columns)
    bench_ret = ds["bench"].pct_change() if ds["bench"] is not None else pd.Series(dtype=float)

    sigs = {"repurchase": eligible_signal(ds, "repurchase"),
            "gpoa": eligible_signal(ds, "gpoa"),
            "gpoa_real": eligible_signal(ds, "gpoa_real")}
    # H22d — the combination, on the intersection where BOTH are observable
    both = sigs["repurchase"].notna() & sigs["gpoa"].notna()
    sigs["combo"] = ((xrank(sigs["repurchase"].where(both))
                      + xrank(sigs["gpoa"].where(both))) / 2.0)

    res = {"portfolios": [], "controls": [], "double": {}, "rho": {},
           "phase": {}, "coverage": {}, "longonly": []}

    # ---------------- coverage, printed BEFORE any return number -------------
    cov = {
        "sessions": int(len(close)),
        "date_min": str(close.index.min().date()),
        "date_max": str(close.index.max().date()),
        "pit_union_tickers": len(pit.all_members_since("2016-01-01")),
        "tickers_with_bars": len(cols),
        "mean_members_per_date": float(ds["membership"].sum(axis=1).mean()),
        "mean_eligible_per_date": float(ds["eligible"].sum(axis=1).mean()),
        "split_repairs": ds["repairs"],
        "n_ambiguous_split_events": len(ds["ambiguous"]),
        "n_extreme_return_cells_masked": ds["n_extreme"],
        "share_unit_repair": {k: ds["unit_meta"][k]
                              for k in ("tickers_repaired", "cells_repaired")},
        "n_implausible_issuance_dropped": ds["n_implausible_issuance"],
        "gp_source": {k: ds["gp_meta"][k] for k in ("n_real", "n_derived", "tickers")},
    }
    for k, s in sigs.items():
        cov[f"{k}_names_per_date"] = float(s.notna().sum(axis=1).mean())
        cov[f"{k}_dates_ranked"] = int((s.notna().sum(axis=1) >= MIN_NAMES).sum())
        cov[f"{k}_coverage_of_members"] = float(
            (s.notna().sum(axis=1) / ds["membership"].sum(axis=1).replace(0, np.nan))
            .mean())
    cov["spy_ann_%"] = (100 * _ann(float(bench_ret.mean()))
                        if len(bench_ret) else float("nan"))
    # The one-day contamination scale, measured on THIS panel: signal rank times
    # its own session's return (illegal) against the next session's (legal).
    rr = xrank(sigs["repurchase"])
    cov["leak_same_session_bps"] = 1e4 * float(rr.mul(ret1).stack().mean())
    cov["honest_next_session_bps"] = 1e4 * float(rr.mul(ret1.shift(-1)).stack().mean())
    res["coverage"] = cov

    if verbose:
        print("\n" + "=" * 78)
        print("COVERAGE — the binding constraint, before any return number")
        print("=" * 78)
        for k, val in cov.items():
            print(f"  {k:34s} {val}")

    # ---------------- H22a / H22b / H22d / H22f : quintile spreads ----------
    for key, label in SIGNALS:
        s = sigs[key]
        w_ls, w_q5, w_q1, w_pool = (ls_weights(s), long_weights(s, bucket=N_QUANTILES),
                                    long_weights(s, bucket=1), pool_weights(s))
        for h in horizons:
            ls = run_portfolio(cohort_weights(w_ls, h), ret1, h)
            q5 = run_portfolio(cohort_weights(w_q5, h), ret1, h)
            q1 = run_portfolio(cohort_weights(w_q1, h), ret1, h)
            pool = run_portfolio(cohort_weights(w_pool, h), ret1, h)
            g = ls["gross"]
            h1, h2 = halves(g)
            lo, hi = _block_boot_ci(g.to_numpy(), block=max(h, 5))
            mkt = market_adjust(g, bench_ret, h)
            # The HONEST effective sample. _n_eff on the daily series comes out
            # at or ABOVE n_days here (3,220 vs 2,664 at h=42) because a
            # long-short book's daily returns are near-serially-uncorrelated
            # even when its WEIGHTS barely move — quarterly filings and a
            # 42-session hold do not make 2,664 independent observations.
            # nonoverlap_blocks says what the t-statistic should be read
            # against: ~63 independent windows, not thousands of days.
            nb = nonoverlap_blocks(g, h)
            res["portfolios"].append({
                "signal": key, "h": h,
                "mean_bps": 1e4 * ls["mean_gross"],
                "ci_lo_bps": 1e4 * lo, "ci_hi_bps": 1e4 * hi,
                "t_nw": ls["t_gross"],
                "n_eff": _n_eff(g.to_numpy(), max(h, 5)),
                "n_indep": nb["n_blocks"], "blk_mean_%": nb["mean_%"],
                "blk_t": nb["t"], "blk_win_rate": nb["share_positive"],
                "h1_bps": 1e4 * float(h1.mean()), "h2_bps": 1e4 * float(h2.mean()),
                "ann_gross_%": 100 * ls["ann_gross"], "ann_net_%": 100 * ls["ann_net"],
                "sharpe_gross": ls["sharpe_gross"],
                "turnover": ls["mean_turnover"], "breakeven_bps": ls["breakeven_bps"],
                **{k: mkt[k] for k in ("beta", "alpha_ann_%", "t_alpha")},
                "q5_ann_%": 100 * q5["ann_gross"], "q1_ann_%": 100 * q1["ann_gross"],
                "pool_ann_%": 100 * pool["ann_gross"],
                "n_days": ls["n_days"], "nan_cells": ls["nan_ret_cells"]})
            if h == PRIMARY_H:
                # H22e — the only form this repo could actually trade
                q5h1, q5h2 = halves(q5["net"])
                res["longonly"].append({
                    "signal": key, "h": h,
                    "q5_ann_net_%": 100 * q5["ann_net"],
                    "q5_sharpe_net": q5["sharpe_net"],
                    "pool_ann_%": 100 * pool["ann_gross"],
                    "pool_sharpe": pool["sharpe_gross"],
                    "spy_ann_%": cov["spy_ann_%"],
                    "spy_sharpe": _sharpe(bench_ret.reindex(q5["net"].index)),
                    "q5_minus_pool_bps": 1e4 * (q5["mean_net"] - pool["mean_gross"]),
                    "h1_bps": 1e4 * float(q5h1.mean()),
                    "h2_bps": 1e4 * float(q5h2.mean()),
                    "turnover": q5["mean_turnover"]})

    # ---------------- controls, on the primary specification ----------------
    for key in ("repurchase", "gpoa"):
        s = sigs[key]
        real_res = run_portfolio(cohort_weights(ls_weights(s), PRIMARY_H), ret1, PRIMARY_H)
        real = real_res["mean_gross"]
        nw_se = abs(real / real_res["t_gross"]) if real_res["t_gross"] else np.nan
        for ck in ("random", "placebo", "shuffle"):
            null = control_null(ck, s, ds[key], ret1, PRIMARY_H, draws=draws)
            z = (real - null["mean"]) / null["sd"] if null["sd"] > 0 else np.nan
            res["controls"].append({
                "signal": key, "h": PRIMARY_H, "control": ck, "draws": null["draws"],
                "real_bps": 1e4 * real, "null_mean_bps": 1e4 * null["mean"],
                "null_SE_bps": 1e4 * null["sd"], "nw_SE_bps": 1e4 * nw_se,
                "SE_ratio": float(nw_se / null["sd"]) if null["sd"] > 0 else np.nan,
                "z_vs_null": z,
                "p_one_sided": float((null["means"] >= real).mean())})

    # ---------------- H22c — the deciding row -------------------------------
    reb_dates = close.index[::REBAL_STRIDE]
    for key in ("repurchase", "gpoa", "combo"):
        res["rho"][key] = rank_correlations(ds, sigs[key], reb_dates, cols)
        fwd = _fwd(close, PRIMARY_H).where(sigs[key].notna())
        res["double"][key] = double_sort(sigs[key], ds["mom12"], fwd)

    # ---------------- H22g — monthly rebalance and its 21 phases ------------
    for key in ("repurchase", "gpoa"):
        res["phase"][key] = phase_sweep(sigs[key], ret1, PRIMARY_H)

    return res


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def report(res: dict) -> None:
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 40)
    fmt = lambda x: f"{x:9.3f}"
    p = pd.DataFrame(res["portfolios"])
    cov = res["coverage"]

    print("\n" + "=" * 78)
    print("H22a/H22b/H22d/H22f — quintile long-short (Q5-Q1), gross and net of "
          "10 bps")
    print("=" * 78)
    for key, label in SIGNALS:
        print(f"\n  {label}")
        sub = p[p["signal"] == key][
            ["h", "mean_bps", "ci_lo_bps", "ci_hi_bps", "t_nw", "n_eff",
             "h1_bps", "h2_bps", "ann_gross_%", "ann_net_%", "sharpe_gross",
             "turnover", "breakeven_bps", "beta", "alpha_ann_%", "t_alpha"]]
        print(sub.to_string(index=False, float_format=fmt))
    print("""
  mean_bps  mean DAILY long-short return in bps, one observation per date
  ci        95% moving-block bootstrap by date, block = holding period
  n_eff     effective INDEPENDENT sample: overlapping holds are not independent
  h1/h2     first and second half of the sample (a sign flip is noise)
  t_nw      Newey-West(h); this repo's standalone bar is t > 3, not 2
  beta/alpha_ann_%/t_alpha  Rule 13 — the book regressed on SPY. A
            dollar-neutral spread is NOT market-neutral; read alpha, not gross.""")

    print("\n  EFFECTIVE INDEPENDENT SAMPLE — read the t-stats against THIS, "
          "not against n_days:")
    print(p[["signal", "h", "n_days", "n_eff", "n_indep", "blk_mean_%",
             "blk_t", "blk_win_rate"]]
          .to_string(index=False, float_format=lambda x: f"{x:9.3f}"))
    print("""  n_eff     from the daily series. It comes out AT OR ABOVE n_days, which is
            exactly the flattery nonoverlap_blocks' docstring warns about: a
            long-short book's DAILY returns are near-serially-uncorrelated even
            when its WEIGHTS barely move, so the daily series looks independent
            while the POSITIONS are quarterly.
  n_indep   NON-OVERLAPPING h-session windows — the honest count. Ten years of
            P&L driven by quarterly filings at a 42-session hold is ~63
            independent windows, not 2,664 days.
  blk_t     t on those windows. This is the number that decides the hypothesis.""")

    print("\n  matched benchmarks (annualised, gross):")
    print(p[["signal", "h", "q5_ann_%", "q1_ann_%", "pool_ann_%"]]
          .to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
    print("  pool_ann_% is equal weight of the IDENTICAL eligible pool — the "
          "matched\n  benchmark that says how much of Q5 is just 'S&P 500 names "
          "went up'.")

    print("\n" + "=" * 78)
    print(f"CONTROLS — real spread against three nulls at h={PRIMARY_H} "
          f"({res['controls'][0]['draws']} draws each)")
    print("=" * 78)
    print(pd.DataFrame(res["controls"]).to_string(index=False, float_format=fmt))
    print("""
  READ SE_ratio BEFORE z. nw_SE is the Newey-West standard error of the real
  series; null_SE is the spread of the permutation null. Where SE_ratio >> 1 the
  permutation understates the real uncertainty because permuting labels destroys
  the persistence of the signal and so the autocorrelation of its P&L (H16
  Finding 2, Rule 14). The PLACEBO null — each symbol keeps its own signal
  series, only the pairing breaks — is the honest one here.""")

    print("\n" + "=" * 78)
    print("H22c — THE DECIDING ROW: is any of this just momentum?")
    print("=" * 78)
    print("\n  (i) cross-sectional rank correlation, averaged over "
          f"{len(res['rho']['repurchase'])and ''}monthly dates")
    print(pd.DataFrame(res["rho"]).T.to_string(float_format=lambda x: f"{x:9.3f}"))
    print("""  rho_mom12      Spearman vs raw 12-1 momentum over the same eligible pool
  rho_composite  Spearman vs the repo's GATED v5 composite score, computed with
                 signals.composite_at exactly as scan and calibration compute it
  gated_pool     names surviving the v5 gates on an average date
  overlap        names in both the fundamental pool and the gated pool""")

    for key in res["double"]:
        print(f"\n  (ii) double sort — {key}: mean {PRIMARY_H}-session forward "
              f"return in bps")
        print(res["double"][key].to_string(float_format=lambda x: f"{x:9.1f}"))
    print("""
  mom T1 = weakest 12-1 momentum, mom T3 = strongest. The row that decides H22c
  is spread(T3-T1): if the fundamental spread survives INSIDE every momentum
  tercile it is orthogonal information; if it only exists across them it is
  momentum in an accountant's costume and this repo already owns it.""")

    print("\n" + "=" * 78)
    print("H22e — LONG-ONLY TOP QUINTILE (the only form this repo would trade)")
    print("=" * 78)
    print(pd.DataFrame(res["longonly"]).to_string(index=False, float_format=fmt))
    print("  q5_ann_net_% is AFTER 10 bps round trip on measured turnover.\n"
          "  q5_minus_pool_bps is the daily excess over the equal-weight "
          "eligible pool.")

    print("\n" + "=" * 78)
    print(f"H22g — RULE 9: all {REBAL_STRIDE} monthly entry phases, h={PRIMARY_H}")
    print("=" * 78)
    for key, tab in res["phase"].items():
        daily = p[(p["signal"] == key) & (p["h"] == PRIMARY_H)]["mean_bps"].iloc[0]
        print(f"\n  {key}: phase-pooled daily-formation estimator = {daily:+.3f} bps")
        print(f"    21 monthly phases: mean {tab['mean_bps'].mean():+.3f} bps, "
              f"sd {tab['mean_bps'].std(ddof=1):.3f}, "
              f"min {tab['mean_bps'].min():+.3f}, max {tab['mean_bps'].max():+.3f}")
        print(f"    turnover {tab['turnover'].mean():.4f}x/day vs "
              f"{p[(p['signal'] == key) & (p['h'] == PRIMARY_H)]['turnover'].iloc[0]:.4f}x "
              f"for daily formation")

    print("\n" + "=" * 78)
    print("MULTIPLE-TESTING GATE")
    print("=" * 78)
    reg = p[p["signal"].isin(("repurchase", "gpoa", "combo", "gpoa_real"))]
    best = reg.loc[reg["sharpe_gross"].idxmax()]
    dsr = growth.deflated_sharpe(sr=float(best["sharpe_gross"]) / math.sqrt(TDAYS),
                                 n_trials=N_TRIALS_REGISTERED,
                                 n_obs=int(best["n_days"]))
    print(f"  best variant in the REGISTERED direction: signal={best['signal']} "
          f"h={int(best['h'])}  gross Sharpe {best['sharpe_gross']:.3f}, "
          f"NW t {best['t_nw']:+.2f}")
    print(f"  trials this round N={N_TRIALS_REGISTERED} "
          f"(scout/hypotheses.md H22a-H22g); DSR = {dsr:.3f}")
    print(f"  SPY over the same sessions: {cov['spy_ann_%']:.2f}%/yr")

    print("\n" + "=" * 78)
    print("LOOKAHEAD AUDIT")
    print("=" * 78)
    print(f"  signal rank x its OWN session's return   {cov['leak_same_session_bps']:+8.3f} bps"
          f"   (illegal — not used)")
    print(f"  signal rank x the NEXT session's return  {cov['honest_next_session_bps']:+8.3f} bps"
          f"   (what every table above uses)")
    print("  Fundamental point-in-time is enforced upstream by sec_bulk.pit_panel:\n"
          "  facts enter on their SEC FILING date, first filing wins on restatements,\n"
          "  and a fact older than "
          f"{MAX_STALE_DAYS} days is dropped so a company that stops\n  filing stops "
          "having a signal.")


# --------------------------------------------------------------------------
# selftest — synthetic, offline, no keys, no network
# --------------------------------------------------------------------------

def _synthetic(n_days=1200, n_sym=120, beta=0.0, seed=7):
    """Panel with a PLANTED slow signal -> forward-return effect of size `beta`.
    The signal is deliberately PERSISTENT (step changes a few times a year, like
    a real quarterly fundamental) so the control machinery is exercised on the
    kind of series it will actually meet."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n_days)
    cols = [f"S{i:03d}" for i in range(n_sym)]
    steps = rng.normal(0, 1, (n_days // 63 + 1, n_sym))
    sig = pd.DataFrame(np.repeat(steps, 63, axis=0)[:n_days], index=idx, columns=cols)
    noise = rng.normal(0, 0.015, (n_days, n_sym))
    fwd = beta * sig.to_numpy() + noise
    ret1 = pd.DataFrame(np.vstack([np.zeros((1, n_sym)), fwd[:-1]]),
                        index=idx, columns=cols)
    close = (1 + ret1).cumprod() * 100
    return sig, ret1, close


def selftest(verbose: bool = True) -> int:
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append(f"{name}: {detail}")
        if verbose:
            print(f"  [{'ok ' if cond else 'FAIL'}] {name} {detail}")

    print("selftest — synthetic panels, no network, no keys")

    # 1. rank / quantile primitives
    f = pd.DataFrame([[1.0, 2.0, 3.0, np.nan]], columns=list("abcd"))
    r = xrank(f)
    check("xrank spans -0.5..+0.5",
          abs(r.iloc[0, 0] + 0.5) < 1e-12 and abs(r.iloc[0, 2] - 0.5) < 1e-12,
          f"{r.iloc[0].tolist()}")
    check("xrank keeps NaN", bool(np.isnan(r.iloc[0, 3])))
    lab = xquantile(pd.DataFrame([[1, 1, 1, 1, 2, 2, 3, 3, 4, 5]], dtype=float), 5).iloc[0]
    check("tie block lands in one bucket", lab[:4].nunique() == 1, f"{lab.tolist()}")

    # 2. planted signal recovered with the right sign, at the right size
    sig, ret1, close = _synthetic(beta=0.004)
    res = run_portfolio(cohort_weights(ls_weights(sig), 42), ret1, 42)
    check("planted +signal recovered", res["mean_gross"] > 0.001,
          f"{1e4 * res['mean_gross']:.1f} bps")
    sig_n, ret1_n, _ = _synthetic(beta=-0.004, seed=8)
    res_n = run_portfolio(cohort_weights(ls_weights(sig_n), 42), ret1_n, 42)
    check("planted -signal recovered", res_n["mean_gross"] < -0.001,
          f"{1e4 * res_n['mean_gross']:.1f} bps")

    # 3. NULL panel gives ~0
    sig0, ret10, _ = _synthetic(beta=0.0, seed=11)
    res0 = run_portfolio(cohort_weights(ls_weights(sig0), 42), ret10, 42)
    check("null panel gives ~0", abs(res0["mean_gross"]) < 3e-4,
          f"{1e4 * res0['mean_gross']:.2f} bps")

    # 4. THE LOOKAHEAD PROOF
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2018-01-01", periods=1200)
    cols = [f"S{i:03d}" for i in range(120)]
    ret1 = pd.DataFrame(rng.normal(0, 0.015, (1200, 120)), index=idx, columns=cols)
    same = ret1.copy()                  # signal == today's return: no forecast value
    wb = cohort_weights(ls_weights(same), 1)
    honest = run_portfolio(wb, ret1, 1)["mean_gross"]
    cheat = float((wb * ret1).sum(axis=1).mean())      # NO shift -> lookahead
    check("no-shift version is grossly contaminated", cheat > 50 * abs(honest),
          f"cheat={1e4 * cheat:.0f} bps vs honest={1e4 * honest:.2f} bps")
    check("shifted same-day signal is ~0", abs(honest) < 3e-4, f"{1e4 * honest:.2f} bps")

    # 5. cohort machinery: monthly stride with h=stride equals a plain hold
    w = ls_weights(sig)
    reb = pd.Series(False, index=sig.index)
    reb.iloc[::21] = True
    cw = cohort_weights(w, 21, reb)
    check("21-td stride with h=21 holds exactly one cohort",
          bool(np.isclose(cw.abs().sum(axis=1).dropna().max(), 2.0, atol=1e-9)),
          f"max gross exposure {cw.abs().sum(axis=1).max():.4f}")
    cw42 = cohort_weights(w, 42, reb)
    check("21-td stride with h=42 averages two cohorts",
          bool(cw42.abs().sum(axis=1).max() <= 2.0 + 1e-9
               and (cw42 != cw).to_numpy().any()),
          f"max gross exposure {cw42.abs().sum(axis=1).max():.4f}")
    check("daily formation = rolling mean of daily books",
          bool(np.allclose(cohort_weights(w, 42).fillna(0).to_numpy(),
                           w.rolling(42, min_periods=1).mean().fillna(0).to_numpy())))

    # 6. cost / break-even arithmetic
    r = run_portfolio(cohort_weights(w, 42), ret1=ret1, h=42, cost_bps=10.0)
    implied = r["mean_gross"] - r["mean_turnover"] * (10.0 / 2 / 1e4)
    check("net = gross - turnover x one-way cost", abs(implied - r["mean_net"]) < 1e-12,
          f"{1e4 * implied:.5f} vs {1e4 * r['mean_net']:.5f} bps")
    r2 = run_portfolio(cohort_weights(w, 42), ret1=ret1, h=42,
                       cost_bps=r["breakeven_bps"])
    check("break-even cost zeroes the net return", abs(r2["mean_net"]) < 1e-12,
          f"net={1e4 * r2['mean_net']:.8f} bps at {r['breakeven_bps']:.2f} bps")

    # 7. extreme-return guard actually removes a planted fake split
    ret_bad = ret1.copy()
    ret_bad.iloc[500, 0] = -0.742                      # the AAPL 2020-08-31 signature
    em = extreme_mask(ret_bad)
    check("45% guard catches a fabricated split return",
          bool(em.iloc[500, 0]) and int(em.to_numpy().sum()) == 1,
          f"{int(em.to_numpy().sum())} cell(s) flagged")

    # 8. controls unbiased on a null panel, and the placebo is wider
    n_rand = control_null("random", sig0, sig0, ret10, 42, draws=40, seed=5)
    n_plac = control_null("placebo", sig0, sig0, ret10, 42, draws=40, seed=5)
    check("random null centred on zero", abs(n_rand["mean"]) < 3e-4,
          f"{1e4 * n_rand['mean']:.2f} bps sd {1e4 * n_rand['sd']:.2f}")
    check("placebo null centred on zero", abs(n_plac["mean"]) < 3e-4,
          f"{1e4 * n_plac['mean']:.2f} bps sd {1e4 * n_plac['sd']:.2f}")

    # 9. Newey-West widens with autocorrelation; n_eff falls below n
    x = pd.Series(np.random.default_rng(5).normal(0, 1, 3000)).rolling(42).mean().dropna()
    ne = _n_eff(x.to_numpy(), 42)
    check("n_eff < n on an overlapping series", ne < 0.5 * len(x),
          f"n_eff={ne:.0f} of n={len(x)}")

    # 10. point-in-time discipline: a fact is invisible before it is FILED
    facts = pd.DataFrame({
        "ticker": ["AAA", "AAA"], "tag": ["GPOA", "GPOA"],
        "ddate": pd.to_datetime(["2020-12-31", "2020-12-31"]),
        "qtrs": [4, 4], "value": [0.5, 0.9],
        "filed": pd.to_datetime(["2021-02-15", "2021-11-01"]),   # restatement
        "segments": [np.nan, np.nan], "coreg": [np.nan, np.nan]})
    dts = pd.DatetimeIndex(pd.bdate_range("2021-01-01", "2021-12-31"))
    pan = sec_bulk.pit_panel(facts, "GPOA", ["AAA"], dts, qtrs=4)
    check("fact invisible before its filing date",
          bool(pan.loc[pd.Timestamp("2021-02-01"), "AAA"] != pan.loc[
              pd.Timestamp("2021-02-01"), "AAA"]),
          "NaN at 2021-02-01")
    check("first filing wins on a restatement",
          abs(float(pan.loc[pd.Timestamp("2021-12-01"), "AAA"]) - 0.5) < 1e-12,
          f"{float(pan.loc[pd.Timestamp('2021-12-01'), 'AAA']):.3f} (0.9 = lookahead)")

    # 11. gross_profitability_facts joins the same period and the later filing
    gf = pd.DataFrame({
        "ticker": ["BBB"] * 3, "adsh": ["x", "x", "x"],
        "tag": ["Revenues", "CostOfGoodsAndServicesSold", "Assets"],
        "ddate": pd.to_datetime(["2020-12-31"] * 3), "qtrs": [4, 4, 0],
        "value": [1000.0, 600.0, 2000.0],
        "filed": pd.to_datetime(["2021-02-15", "2021-02-15", "2021-03-01"]),
        "segments": [np.nan] * 3, "coreg": [np.nan] * 3})
    out, meta = gross_profitability_facts(gf, verbose=False)
    check("GP/AT derived correctly", len(out) == 1
          and abs(float(out["value"].iloc[0]) - 0.2) < 1e-12,
          f"{out['value'].tolist()}")
    check("GP/AT filed = LATER of the two components",
          out["filed"].iloc[0] == pd.Timestamp("2021-03-01"),
          str(out["filed"].iloc[0].date()))

    # 12. share-count UNIT repair — the defect that would otherwise make MCD a
    #     99.9999% buyback and COP a 100,000% issuance
    idx = pd.DatetimeIndex(pd.bdate_range("2016-01-01", periods=1600))
    mcd = pd.Series(7.4e8, index=idx); mcd.iloc[1200:] = 732.3      # units -> millions
    grmn = pd.Series(1.9e8, index=idx); grmn.iloc[::2] = 1.9e5      # alternating
    real = pd.Series(np.linspace(1.0e9, 0.85e9, len(idx)), index=idx)  # a true buyback
    sh = pd.DataFrame({"MCD": mcd, "GRMN": grmn, "REAL": real})
    fx, meta = normalize_share_units(sh, verbose=False)
    lc = np.log(fx / fx.shift(252)).abs()
    # 7.4e8 -> 732.3 is 1.0105e6, so the honest residual after the repair is a
    # real -1.05% change; the fabricated number it replaces is 13.8 in logs.
    check("unit repair kills the fabricated MCD step",
          float(lc["MCD"].max()) < 0.05,
          f"max |12m log change| {float(lc['MCD'].max()):.4f} "
          f"(was {abs(math.log(732.3 / 7.4e8)):.1f})")
    check("unit repair kills the alternating GRMN scale",
          float(lc["GRMN"].max()) < 0.01, f"{float(lc['GRMN'].max()):.4f}")
    check("unit repair leaves a REAL 15% buyback untouched",
          meta["worst"].get("REAL") is None
          and abs(float(lc["REAL"].dropna().iloc[-1]) - abs(math.log(0.85 / 1.0))
                  * (252 / (len(idx) - 1))) < 0.02,
          f"12m log change {float(lc['REAL'].dropna().iloc[-1]):.4f}")

    # 13. staleness expiry
    sf = pd.DataFrame({"ticker": ["CCC"], "filed": pd.to_datetime(["2020-01-15"])})
    st = staleness_days(sf, ["CCC"], pd.DatetimeIndex(
        pd.bdate_range("2020-01-01", "2021-12-31")))
    check("staleness grows and crosses the expiry",
          bool(st.loc[pd.Timestamp("2020-02-03"), "CCC"] < MAX_STALE_DAYS
               and st.loc[pd.Timestamp("2021-06-01"), "CCC"] > MAX_STALE_DAYS),
          f"{st.loc[pd.Timestamp('2021-06-01'), 'CCC']:.0f} days by 2021-06")

    print(f"\n{len(fails)} failure(s)")
    for f_ in fails:
        print("  " + f_)
    return 1 if fails else 0


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help=f"h={PRIMARY_H} only and 50 control draws")
    ap.add_argument("--draws", type=int, default=N_CONTROL_DRAWS)
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild the cached dataset from bars + SEC facts")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.rebuild:
        build_dataset(force=True)

    t0 = time.time()
    hs = (PRIMARY_H,) if args.quick else HORIZONS
    res = run(horizons=hs, draws=50 if args.quick else args.draws)
    report(res)
    print(f"\n[{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
