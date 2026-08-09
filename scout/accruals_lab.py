"""H27 - the accruals anomaly: earnings that are not cash do not persist.

MECHANISM (one sentence, stated before any number)
--------------------------------------------------
Sloan (1996): the accrual component of earnings is less persistent than the
cash component, and investors fixate on the headline earnings number without
decomposing it, so firms whose profits are mostly accruals are systematically
over-valued and underperform as the accruals fail to convert into cash.

Testable consequence: rank firms each month by
    accruals = (net income - cash flow from operations) / average total assets
and the LOW-accrual quintile should beat the HIGH-accrual quintile.

Prior, stated before the run so the result cannot be re-framed afterwards.
Sloan's original 1962-1991 spread was ~10%/yr on all NYSE/AMEX names.
Green-Hand-Soliman (2011) and Richardson-Tuna-Wysocki document its decay to
statistical insignificance in large caps after ~2003; McLean-Pontiff's
post-publication haircut is ~58%. Sloan's own hedge portfolio is dominated by
microcaps. This lab tests it on index members over 2016-2026, which is the
hardest possible cohort for it: **a null here is the modal expected outcome
and is weak evidence about the anomaly in the small-cap tape where it lives.**

WHAT IS MEASURED
----------------
Universe   TWO, both run, both reported.
           U1 `sp1500` (PRIMARY) - today's S&P 1500 members (large 500 /
              mid 400 / small 600 from scout/universe.csv). Survivorship on
              the entry side, disclosed; chosen as primary because the
              anomaly is a down-cap effect and this is the only universe here
              that contains mid and small caps.
           U2 `pit500` (SURVIVORSHIP CONTROL) - each date's ACTUAL S&P 500
              membership via scout/pit.py, delisted names included.
Fundamentals scout/sec_bulk.py, the DERA bulk financial-statement data set:
           NetIncomeLoss (qtrs=4), NetCashProvidedByUsedInOperatingActivities
           (qtrs=4), Assets (qtrs=0). Consolidated rows only (no `segments`,
           no `coreg`), first filing of a period wins.
Prices     Alpaca SIP daily closes, adjustment=all, 2016-01 .. 2026-08.
Portfolio  cross-sectional quintiles at each month end, equal weight, held
           close(t) -> close(t+h) for h in {21, 42, 126, 252}. h=42 is the
           repo's own horizon and is the row the verdict is written against;
           the others exist because Sloan's is an ANNUAL effect and measuring
           it at two months would otherwise confound "absent" with "early".

PERIOD LENGTHS - the documented trap, handled explicitly
-------------------------------------------------------
`qtrs` is the period length in quarters: 0 = instantaneous (balance sheet),
1 = one quarter, 4 = annual. Both flows are taken at qtrs=4 and the two are
INNER-JOINED ON (ticker, ddate), so net income and operating cash flow always
cover the SAME fiscal year - not merely the latest of each, which is what a
naive two-panel forward-fill produces and which desynchronises whenever one
tag is restated or filed in a different document. Assets are taken at qtrs=0
(a stock, not a flow) at the fiscal year end and one year earlier, matched by
`merge_asof` with a 10-day / 45-day tolerance so 52/53-week fiscal calendars
still line up. Average assets = (beginning + ending) / 2, as in Sloan.

WHERE THE shift() IS  (the only thing that can manufacture this result)
----------------------------------------------------------------------
1. FILING DATE, NEVER PERIOD END. A record enters the panel at
   `filed = max(filed of its four component facts)`, which is `sec_bulk`'s
   whole reason to exist. Conditioning on `ddate` instead would grant a
   median 55 days and a p99 of 790 days of lookahead.
2. MONOTONE BY FILING. Within a ticker, sorted by filing date, a record is
   kept only if its fiscal year is newer than every earlier-filed record's -
   so the comparative years that every 10-K re-reports can never overwrite a
   fresher number.
3. ONE EXTRA SESSION OF SLACK. The panel is then `shift(1)`ed: a filing dated
   t is used from t+1 onward, because filings land after the close.
4. RETURNS. `fwd_h(t) = close.shift(-h) / close - 1`, paired with the signal
   at the SAME index t. That negative shift is the only shift on the price
   side. Signal(t) is a function of filings through t-1 and nothing else;
   the return it weights STARTS at close(t).
5. STALENESS CAP. A record is usable only while `t - ddate <= 550 days`. The
   DERA data set starts 2016q1, so early filings re-report fiscal 2013-2015;
   without the cap the first months of the sample would rank stocks on
   three-year-old accruals.

CONTROLS (five, all run, none optional)
---------------------------------------
a. RANDOM-PICK - quintile labels permuted inside each formation date over the
   identical eligible pool, 200 draws, mean AND SD quoted (Rule 10).
b. PLACEBO PAIRING - each symbol is permanently assigned another symbol's
   accrual history, 200 draws. This is the right null for a PERSISTENT firm
   characteristic: it keeps every accrual series' own time-series properties
   and its sector/size tilt and breaks only the pairing to the firm. A
   within-date shuffle (control a) destroys that persistence and is
   anti-conservative for exactly the reason H16's Finding 2 documents.
c. DATE SHUFFLE - each symbol's OWN accrual history permuted across formation
   dates, 200 draws. Firm identity and its accrual distribution survive; only
   the YEAR dies. Sloan's mechanism is a claim about WHICH YEAR a firm
   accrued, so a genuine effect must collapse here. THIS IS THE DECIDING
   CONTROL, and it is the one that killed H15 after every t-test passed.
d. MATCHED BENCHMARK - equal weight of the eligible pool, so "just avoid the
   high-accrual names" is priced separately from the long/short claim.
e. RULE 13 - the dollar-neutral spread is regressed on SPY before its sign is
   quoted; dollar-neutral is not risk-neutral.

DATA DEBT (BACKTEST-REPORT.md: 5.1% of splits are unadjusted in Alpaca bars)
---------------------------------------------------------------------------
This study has NO veto that would exclude a name that just printed +925%, so
the guard is explicit: every `|1-day return| > 45%` is flagged, and a
(symbol, formation date) leg is DROPPED if such a print falls inside its
holding window. The whole study is re-run with the guard OFF to price it.
A stale-quote rule retires a symbol permanently from its first run of >= 10
identical consecutive closes (how a delisted ticker's frozen quote and a
reused-ticker splice present).

Run: python -m scout.accruals_lab              (full study)
     python -m scout.accruals_lab --selftest   (offline, no keys, no network)
"""
from __future__ import annotations

import argparse
import gc
import math
import time

import numpy as np
import pandas as pd

from . import config

# --------------------------------------------------------------------------
# pre-registered parameters. Nothing below is tuned against the outcome.
# --------------------------------------------------------------------------
HORIZONS = (21, 42, 126, 252)
PRIMARY_H = 42                 # the repo's own holding period
N_Q = 5                        # quintiles, as registered
COST_BPS = 10.0                # round trip per leg, large caps
MIN_ELIGIBLE = 40              # formation dates with a thinner pool are skipped
STALE_DAYS = 550               # a fiscal year older than this is unusable
BIG_MOVE = 0.45                # |1-day return| beyond which a bar is implausible
STALE_QUOTE_RUN = 10           # identical consecutive closes -> retire the symbol
MAX_ABS_ACCRUAL = 1.5          # |accruals / avg assets| above this is a unit error
BOOT_REPS = 5000
CTRL_REPS = 200
SEED = 20260809

BARS_CACHE = config.SCOUT_DIR / "cache_accruals_bars.pkl"
RECORDS_CACHE = config.SCOUT_DIR / "cache_accruals_records.pkl"

NI_TAG = "NetIncomeLoss"
CF_TAG = "NetCashProvidedByUsedInOperatingActivities"
AT_TAG = "Assets"


# --------------------------------------------------------------------------
# fundamentals
# --------------------------------------------------------------------------

def _tag_frame(tickers: set[str], tag: str, qtrs: int) -> pd.DataFrame:
    """Consolidated facts for one tag at one period length, first filing wins.

    Loaded one tag at a time and released: `facts.pkl` is 2 GB and three
    studies loading it at once will exhaust the box (sec_bulk.split_by_tag
    exists for this reason)."""
    from . import sec_bulk
    df = pd.read_pickle(sec_bulk.TAG_DIR / f"{tag}.pkl")
    d = df[(df["qtrs"] == qtrs) & df["segments"].isna() & df["coreg"].isna()
           & df["ticker"].isin(tickers) & df["value"].notna()]
    d = (d.sort_values("filed")
           .drop_duplicates(subset=["ticker", "ddate"], keep="first")
           [["ticker", "ddate", "filed", "value"]]).reset_index(drop=True)
    del df
    gc.collect()
    return d


def annual_records(tickers, refresh: bool = False, verbose: bool = True) -> pd.DataFrame:
    """One row per (ticker, fiscal year) with PERIOD-MATCHED NI, CFO and assets.

    The inner join on (ticker, ddate) is the point: it refuses to build an
    accrual out of one year's earnings and another year's cash flow, which is
    what forward-filling two independent panels quietly does."""
    if RECORDS_CACHE.exists() and not refresh:
        return pd.read_pickle(RECORDS_CACHE)
    tk = set(tickers)
    ni = _tag_frame(tk, NI_TAG, 4)
    cf = _tag_frame(tk, CF_TAG, 4)
    at = _tag_frame(tk, AT_TAG, 0)
    if verbose:
        print(f"  {NI_TAG:<45} {len(ni):>7,} annual facts  "
              f"{ni['ticker'].nunique():>5} tickers")
        print(f"  {CF_TAG:<45} {len(cf):>7,} annual facts  "
              f"{cf['ticker'].nunique():>5} tickers")
        print(f"  {AT_TAG:<45} {len(at):>7,} instant facts {at['ticker'].nunique():>5} tickers")

    m = ni.merge(cf, on=["ticker", "ddate"], suffixes=("_ni", "_cf"))
    if verbose:
        print(f"  period-MATCHED (same ticker, same fiscal year end): "
              f"{len(m):>6,} records, {m['ticker'].nunique()} tickers")

    at = at.sort_values("ddate")
    m = m.sort_values("ddate")
    end = pd.merge_asof(
        m, at.rename(columns={"ddate": "d_end", "value": "assets_end",
                              "filed": "filed_end"}),
        left_on="ddate", right_on="d_end", by="ticker",
        direction="nearest", tolerance=pd.Timedelta("10D"))
    end["ddate_beg"] = end["ddate"] - pd.Timedelta(days=365)
    end = end.sort_values("ddate_beg")
    full = pd.merge_asof(
        end, at.rename(columns={"ddate": "d_beg", "value": "assets_beg",
                                "filed": "filed_beg"}),
        left_on="ddate_beg", right_on="d_beg", by="ticker",
        direction="nearest", tolerance=pd.Timedelta("45D"))

    full["filed"] = full[["filed_ni", "filed_cf", "filed_end", "filed_beg"]].max(axis=1)
    full["avg_assets"] = (full["assets_end"] + full["assets_beg"]) / 2.0
    full["accrual"] = (full["value_ni"] - full["value_cf"]) / full["avg_assets"]
    n_all = len(full)
    full = full[full["avg_assets"] > 0].dropna(subset=["accrual"])
    n_assets = len(full)

    # unit-scale guard. FTI's fiscal-2016 filing tags net income in thousands
    # and operating cash flow in units, which prints an accrual of -6664; a
    # real firm's annual earnings or cash flow cannot exceed 150% of its total
    # assets, so both ratios are bounded rather than the difference alone.
    scale_ok = ((full["value_ni"].abs() / full["avg_assets"] <= MAX_ABS_ACCRUAL)
                & (full["value_cf"].abs() / full["avg_assets"] <= MAX_ABS_ACCRUAL)
                & (full["accrual"].abs() <= MAX_ABS_ACCRUAL))
    if verbose:
        print(f"  lost to a missing beginning/ending balance sheet: "
              f"{n_all - n_assets:>5,}")
        print(f"  lost to the unit-scale guard (|x| > {MAX_ABS_ACCRUAL} x assets): "
              f"{int((~scale_ok).sum()):>5,}   "
              f"({', '.join(sorted(set(full.loc[~scale_ok, 'ticker']))[:8])})")
    full = full[scale_ok]

    # MONOTONE BY FILING: a later filing may only introduce a NEWER fiscal
    # year. Every 10-K re-reports two or three comparative years and those
    # must never overwrite a fresher number.
    full = full.sort_values(["ticker", "filed", "ddate"])
    keep = full.groupby("ticker")["ddate"].cummax() == full["ddate"]
    if verbose:
        print(f"  dropped as comparative years inside a later filing: "
              f"{int((~keep).sum()):>5,}")
    full = full[keep].reset_index(drop=True)
    out = full[["ticker", "ddate", "filed", "value_ni", "value_cf",
                "assets_beg", "assets_end", "avg_assets", "accrual"]]
    out.to_pickle(RECORDS_CACHE)
    return out


def accrual_panel(records: pd.DataFrame, dates: pd.DatetimeIndex,
                  tickers: list[str], stale_days: int = STALE_DAYS
                  ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(accruals, fiscal-year-end) as of each date, filing-date point-in-time.

    Returns two aligned frames so the caller can enforce the staleness cap and
    report how much of the panel it costs."""
    r = records[records["ticker"].isin(tickers)].sort_values(["filed", "ddate"]).copy()
    # the fiscal year end travels as nanoseconds so a forward-filled panel with
    # gaps stays numeric; a datetime64 column with NaN holes becomes object.
    epoch = pd.Timestamp("1970-01-01")
    r["ddate_day"] = (r["ddate"] - epoch).dt.days.astype("float64")
    acc = (r.pivot_table(index="filed", columns="ticker", values="accrual",
                         aggfunc="last").sort_index())
    dd = (r.pivot_table(index="filed", columns="ticker", values="ddate_day",
                        aggfunc="last").sort_index())
    idx = acc.index.union(dates)
    acc = acc.reindex(idx).ffill().reindex(dates).reindex(columns=tickers)
    dd = dd.reindex(idx).ffill().reindex(dates).reindex(columns=tickers)
    # SHIFT (3): a filing dated t is usable from t+1 onward.
    acc, dd = acc.shift(1), dd.shift(1)
    days = ((dates - (epoch.tz_localize(dates.tz) if dates.tz else epoch))
            .days.to_numpy().astype("float64")[:, None])
    age = pd.DataFrame(days - dd.to_numpy(), index=dates, columns=tickers)
    acc = acc.where(age <= stale_days)
    return acc.astype("float64"), age


# --------------------------------------------------------------------------
# prices
# --------------------------------------------------------------------------

def load_bars(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Daily SIP bars for the union of both universes plus SPY."""
    if BARS_CACHE.exists() and not refresh:
        return pd.read_pickle(BARS_CACHE)
    from . import data, pit
    cur = pd.read_csv(config.UNIVERSE_CSV)
    syms = sorted(set(cur["symbol"]) | set(pit.all_members_since("2016-01-01"))
                  | {"SPY"})
    out = data.daily_ohlcv(syms, days=3900)
    pd.to_pickle(out, BARS_CACHE)
    return out


def retire_stale_quotes(close: pd.DataFrame, run: int = STALE_QUOTE_RUN
                        ) -> tuple[pd.DataFrame, int]:
    """Drop a symbol permanently from its first run of `run` identical closes.

    A delisted ticker whose last quote is repeated forward, and a reused
    ticker splicing two companies, both present this way. Returns the cleaned
    frame and the number of symbols retired."""
    out = close.copy()
    n = 0
    for sym in out.columns:
        c = out[sym]
        same = (c == c.shift(1)) & c.notna()
        grp = (~same).cumsum()
        runs = same.groupby(grp).cumsum()
        hit = runs[runs >= run - 1]
        if len(hit):
            first = hit.index[0]
            out.loc[out.index >= first, sym] = np.nan
            n += 1
    return out, n


def bad_print_mask(close: pd.DataFrame, thresh: float = BIG_MOVE) -> np.ndarray:
    """Bool (dates x symbols): session t carries an implausible 1-day return.

    This repo's measured data debt (BACKTEST-REPORT.md): 10 of 198 checkable
    splits are UNADJUSTED in Alpaca's daily bars (SIRI +925.6%, AAPL 2020-08-31
    -74.2%), plus 146 further >50% moves from spin-offs and reused tickers.
    The signal engine's vetoes block those by accident; this study has no such
    veto, so the exclusion is explicit."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    return np.isfinite(r) & (np.abs(r) > thresh)


def window_contaminated(bad: np.ndarray, h: int) -> np.ndarray:
    """Bool (dates x symbols): a bad print falls in the window (t, t+h]."""
    cs = np.cumsum(np.vstack([np.zeros((1, bad.shape[1])), bad.astype(float)]), 0)
    n = bad.shape[0]
    out = np.zeros_like(bad)
    hh = min(h, n - 1)
    out[:n - hh] = (cs[1 + hh:n + 1] - cs[1:n - hh + 1]) > 0
    return out


# --------------------------------------------------------------------------
# cross-sectional machinery
# --------------------------------------------------------------------------

def quantile_labels(sig: np.ndarray, elig: np.ndarray, rng: np.random.Generator,
                    q: int = N_Q, min_elig: int = MIN_ELIGIBLE) -> np.ndarray:
    """Balanced within-date quantile labels, -1 where ineligible. Label 0 is
    the LOWEST accrual bucket (the registered long leg). Ties are broken by a
    seeded uniform key; accruals are continuous so ties are rare, but the
    machinery is shared with the placebo control where they are not."""
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
    """(dates x q) equal-weight bucket means, the eligible-pool mean (the
    matched benchmark) and the per-date bucket counts."""
    fin = np.isfinite(y)
    yz = np.nan_to_num(y)
    out = np.full((lab.shape[0], q), np.nan)
    cnt = np.zeros((lab.shape[0], q), dtype=np.int32)
    for qi in range(q):
        m = (lab == qi) & fin
        n = m.sum(1)
        cnt[:, qi] = n
        out[:, qi] = np.where(n > 0,
                              np.where(m, yz, 0.0).sum(1) / np.maximum(n, 1), np.nan)
    pm = (lab >= 0) & fin
    npool = pm.sum(1)
    pool = np.where(npool > 0,
                    np.where(pm, yz, 0.0).sum(1) / np.maximum(npool, 1), np.nan)
    return out, pool, cnt


def turnover(lab: np.ndarray, qi: int, stride: int) -> float:
    """Mean fraction of bucket `qi` replaced between rebalances `stride`
    formation dates apart. A name held across a rebalance is not traded."""
    fr = []
    for i in range(0, lab.shape[0] - stride, stride):
        a, b = set(np.flatnonzero(lab[i] == qi)), set(np.flatnonzero(lab[i + stride] == qi))
        if a and b:
            fr.append(len(b - a) / len(b))
    return float(np.mean(fr)) if fr else float("nan")


# --------------------------------------------------------------------------
# inference: cluster by formation date, block-bootstrap the overlap
# --------------------------------------------------------------------------

def block_boot(x: np.ndarray, block: int, reps: int, rng: np.random.Generator):
    """Circular moving-block bootstrap of the mean of a per-DATE series.

    The cross-section is collapsed to one number per formation date before any
    statistic, so date clustering is structural (scout/calibrate.py resamples
    dates for the same reason). Monthly formation with an h-session hold means
    consecutive dates overlap; the block length is the number of formation
    dates an h-session window spans."""
    x = x[np.isfinite(x)]
    n = len(x)
    block = max(int(block), 1)
    if n < 3 * block:
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


def phase_sweep(x: np.ndarray, stride: int) -> np.ndarray:
    """The `stride` non-overlapping entry schedules hiding inside one
    overlapping mean (RESEARCH-AGENDA Rule 9; H7a is this repo having quoted
    the luckiest of six such schedules as a headline)."""
    stride = max(int(stride), 1)
    return np.array([np.nanmean(x[p::stride]) if np.isfinite(x[p::stride]).any()
                     else np.nan for p in range(stride)])


def ols_beta(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float]:
    """alpha, beta, t(alpha) of y on x. Rule 13: a dollar-neutral book is not
    risk-neutral, and a 0.15 beta was worth 2.4%/yr in this sample."""
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    if len(y) < 10:
        return float("nan"), float("nan"), float("nan")
    X = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    s2 = resid @ resid / (len(y) - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    se_a = math.sqrt(cov[0, 0])
    return float(coef[0]), float(coef[1]), float(coef[0] / se_a) if se_a > 0 else float("nan")


# --------------------------------------------------------------------------
# the experiment
# --------------------------------------------------------------------------

def month_end_index(close: pd.DataFrame) -> pd.DatetimeIndex:
    """Last trading session of each calendar month."""
    s = pd.Series(close.index, index=close.index)
    return pd.DatetimeIndex(s.groupby([close.index.year, close.index.month]).last())


def build_eligibility(close_f: pd.DataFrame, acc: pd.DataFrame,
                      member: np.ndarray | None, fwd: np.ndarray,
                      contaminated: np.ndarray | None) -> np.ndarray:
    ok = np.isfinite(close_f.to_numpy()) & np.isfinite(acc.to_numpy()) & np.isfinite(fwd)
    if member is not None:
        ok &= member
    if contaminated is not None:
        ok &= ~contaminated
    return ok


def run_universe(name: str, acc: pd.DataFrame, close: pd.DataFrame,
                 form: pd.DatetimeIndex, member: np.ndarray | None,
                 bad: np.ndarray, rng: np.random.Generator,
                 horizons=HORIZONS, guard: bool = True, verbose: bool = True):
    """One universe, all horizons. Returns the summary table and, for each
    horizon, the machinery the controls reuse (identical labels, not a
    re-derived approximation)."""
    pos = close.index.get_indexer(form)
    rows, keep = [], {}
    for h in horizons:
        fwd_full = (close.shift(-h) / close - 1.0).to_numpy()
        cont_full = window_contaminated(bad, h) if guard else None
        fwd = fwd_full[pos]
        cont = cont_full[pos] if cont_full is not None else None
        elig = build_eligibility(close.loc[form], acc, member, fwd, cont)
        lab = quantile_labels(acc.to_numpy(), elig, np.random.default_rng(SEED + h))
        q, pool, cnt = bucket_means(lab, fwd)
        spread = q[:, 0] - q[:, N_Q - 1]          # LOW minus HIGH, registered +
        excess = q[:, 0] - pool
        stride = max(int(round(h / 21)), 1)
        b = block_boot(spread, stride, BOOT_REPS, rng)
        be = block_boot(excess, stride, BOOT_REPS, rng)
        ph = phase_sweep(spread, stride)
        ok = np.isfinite(spread)
        idx = np.flatnonzero(ok)
        half = len(idx) // 2
        rows.append(dict(
            universe=name, h=h, n_dates=int(ok.sum()),
            n_names=float(cnt[ok].sum(1).mean()),
            q1=np.nanmean(q[:, 0]) * 100, q3=np.nanmean(q[:, 2]) * 100,
            q5=np.nanmean(q[:, N_Q - 1]) * 100, pool=np.nanmean(pool) * 100,
            spread=b["mean"] * 100, lo=b["lo"] * 100, hi=b["hi"] * 100, t=b["t"],
            q1_excess=be["mean"] * 100, t_excess=be["t"],
            half1=float(np.mean(spread[idx[:half]])) * 100,
            half2=float(np.mean(spread[idx[half:]])) * 100,
            ph_min=float(np.nanmin(ph)) * 100, ph_max=float(np.nanmax(ph)) * 100,
            ph_wrong=int((ph < 0).sum()), ph_n=len(ph),
            turn_lo=turnover(lab, 0, stride), turn_hi=turnover(lab, N_Q - 1, stride)))
        keep[h] = dict(spread=spread, excess=excess, lab=lab, fwd=fwd, elig=elig,
                       pool=pool, q=q, stride=stride)
        if verbose:
            r = rows[-1]
            print(f"    h={h:>3}  Q1-Q5 {r['spread']:+7.2f}%  "
                  f"[{r['lo']:+6.2f},{r['hi']:+6.2f}]  t={r['t']:+5.2f}  "
                  f"halves {r['half1']:+6.2f}/{r['half2']:+6.2f}  "
                  f"n={r['n_dates']:>3} dates, {r['n_names']:.0f} names")
    return pd.DataFrame(rows), keep


def random_pick_control(lab: np.ndarray, fwd: np.ndarray,
                        rng: np.random.Generator, reps: int = CTRL_REPS):
    """CONTROL (a): identical pool, identical bucket sizes, labels permuted
    inside each formation date. Expectation is exactly zero by construction;
    what the draws buy is the SCALE of the noise (Rule 10)."""
    out = np.empty(reps)
    for r in range(reps):
        p = lab.copy()
        for i in range(p.shape[0]):
            v = p[i]
            m = v >= 0
            if m.any():
                v[m] = rng.permutation(v[m])
        q, _, _ = bucket_means(p, fwd)
        out[r] = np.nanmean(q[:, 0] - q[:, N_Q - 1])
    return out


def date_shuffle_control(acc: np.ndarray, elig: np.ndarray, fwd: np.ndarray,
                         rng: np.random.Generator, reps: int = CTRL_REPS):
    """CONTROL (c), THE DECIDING ONE: permute each symbol's accrual history
    ACROSS FORMATION DATES, independently per symbol.

    What survives: every firm's own distribution of accruals, hence how often
    it lands in the low-accrual quintile at all. What dies: the link between a
    fiscal year's accruals and the months that followed it.

    Sloan's mechanism is about WHICH YEAR a firm accrued - low persistence of
    THIS year's accrual component showing up in NEXT year's earnings - so a
    genuine accruals anomaly must lose most of its spread here. A spread that
    survives is a STATIC firm characteristic ("software companies with
    deferred revenue outperformed in 2016-2026"), which needs no accounting
    story and no filing date. H15 in scout/hypotheses.md was rejected by
    exactly this control after passing every t-test."""
    out = np.empty(reps)
    for r in range(reps):
        s = acc.copy()
        for j in range(s.shape[1]):
            col = s[:, j]
            f = np.isfinite(col)
            if f.sum() > 1:
                col[f] = rng.permutation(col[f])
        lab = quantile_labels(s, elig, rng)
        q, _, _ = bucket_means(lab, fwd)
        out[r] = np.nanmean(q[:, 0] - q[:, N_Q - 1])
    return out


def placebo_control(acc: np.ndarray, elig: np.ndarray, fwd: np.ndarray,
                    rng: np.random.Generator, reps: int = CTRL_REPS):
    """CONTROL (b), the one this hypothesis turns on: each symbol keeps an
    ENTIRE accrual history, but somebody else's.

    Accruals are a slow-moving firm characteristic, so a within-date shuffle
    (control a) destroys a persistence the real book has and understates the
    null's spread - H16 Finding 2 measured that error at 2-3x. Permuting the
    COLUMN ASSIGNMENT preserves each series' autocorrelation, its level and
    its sector/size profile, and breaks only the pairing between a firm's
    accruals and that firm's returns."""
    out = np.empty(reps)
    n_s = acc.shape[1]
    for r in range(reps):
        perm = rng.permutation(n_s)
        lab = quantile_labels(acc[:, perm], elig, rng)
        q, _, _ = bucket_means(lab, fwd)
        out[r] = np.nanmean(q[:, 0] - q[:, N_Q - 1])
    return out


def costs(res: pd.DataFrame, cost_bps: float = COST_BPS) -> pd.DataFrame:
    """Charge the round trip and report the break-even.

    The registered book is 1x LONG the low-accrual quintile + 1x SHORT the
    high-accrual quintile, rebalanced every `stride` formation dates (so the
    hold matches h). At each rebalance a fraction f of a leg is replaced and
    pays f x cost_bps; total per window is (f_lo + f_hi) x cost_bps.
    Break-even c* = gross / (f_lo + f_hi)."""
    rows = []
    for _, r in res.iterrows():
        gross = r["spread"] * 100.0                        # % -> bps
        f = r["turn_lo"] + r["turn_hi"]
        chg = f * cost_bps
        per_yr = 252.0 / r["h"]
        rows.append(dict(universe=r["universe"], h=int(r["h"]), gross_bps=gross,
                         turn=f, cost_bps=chg, net_bps=gross - chg,
                         breakeven_bps=gross / f if f else float("nan"),
                         gross_pct_yr=gross * per_yr / 100,
                         net_pct_yr=(gross - chg) * per_yr / 100))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# INDEPENDENCE: is this the repo's momentum composite, or net issuance, again?
# --------------------------------------------------------------------------

def momentum_scores(bars: dict, form: pd.DatetimeIndex,
                    tickers: list[str]) -> pd.DataFrame:
    """The repo's own v5 composite (scout/signals.composite_at) at each
    formation date, as a (dates x tickers) frame. Gated names are NaN, which
    is what the engine actually does - it drops them."""
    from . import signals
    o, c, v = (bars[k].reindex(columns=tickers) for k in ("open", "close", "volume"))
    frames = signals.feature_frames(o, c, v)
    out = pd.DataFrame(index=form, columns=tickers, dtype=float)
    for ts in form:
        try:
            df = signals.composite_at(frames, ts)
        except KeyError:
            continue
        if len(df):
            out.loc[ts, df.index] = df["score"].to_numpy()
    return out


def gross_profitability(tickers, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Novy-Marx gross profitability = annual GrossProfit / total assets, on
    the same filing-date point-in-time machinery as the accrual panel.

    Exists only as a CONTROL: the leading alternative reading of any
    low-accrual premium in 2016-2026 is that it proxies for quality, which
    this decade paid for handsomely."""
    tk = set(tickers)
    gp = _tag_frame(tk, "GrossProfit", 4)
    at = _tag_frame(tk, AT_TAG, 0)
    m = gp.merge(at, on=["ticker", "ddate"], suffixes=("_gp", "_at"))
    m = m[m["value_at"] > 0]
    m["accrual"] = m["value_gp"] / m["value_at"]        # reuse accrual_panel
    m["filed"] = m[["filed_gp", "filed_at"]].max(axis=1)
    m = m.sort_values(["ticker", "filed", "ddate"])
    m = m[m.groupby("ticker")["ddate"].cummax() == m["ddate"]]
    out, _ = accrual_panel(m[["ticker", "ddate", "filed", "accrual"]], dates,
                           list(tickers))
    return out


def monthly_shares(tickers: list[str], form: pd.DatetimeIndex) -> pd.DataFrame:
    """Split-adjusted shares outstanding on the formation grid
    (scout/sec_bulk.shares_panel: point-in-time, share-class filtered, splits
    applied at each fact's FILING date). Serves both the net-issuance
    independence test and the market-cap diagnostic."""
    from . import sec_bulk
    facts = sec_bulk.load_tags(sorted({t for t, _ in sec_bulk.SHARE_TAGS}))
    sh = sec_bulk.shares_panel(facts, tickers, form)
    del facts
    gc.collect()
    return sh


def issuance_scores(shares: pd.DataFrame) -> pd.DataFrame:
    """12-month log change in split-adjusted shares outstanding - exactly
    scout/sec_bulk.net_issuance's definition, evaluated on the monthly
    formation grid with a 12-observation lookback rather than a 252-session
    one. Same quantity, ~40x cheaper, and the study only reads it at
    formation dates."""
    return np.log(shares / shares.shift(12)).replace([np.inf, -np.inf], np.nan)


def rank_corr_by_date(a: pd.DataFrame, b: pd.DataFrame, elig: np.ndarray
                      ) -> np.ndarray:
    """Cross-sectional Spearman between two signals, one value per date."""
    av, bv = a.to_numpy(), b.to_numpy()
    out = np.full(av.shape[0], np.nan)
    for i in range(av.shape[0]):
        m = elig[i] & np.isfinite(av[i]) & np.isfinite(bv[i])
        if m.sum() < 20:
            continue
        x = pd.Series(av[i, m]).rank().to_numpy()
        y = pd.Series(bv[i, m]).rank().to_numpy()
        if x.std() == 0 or y.std() == 0:
            continue
        out[i] = float(np.corrcoef(x, y)[0, 1])
    return out


def spread_series(sig: pd.DataFrame, elig: np.ndarray, fwd: np.ndarray,
                  rng: np.random.Generator, low_minus_high: bool) -> np.ndarray:
    """Quintile spread of an arbitrary signal on the same pool and horizon, so
    two strategies' RETURN correlation can be measured (which is the question
    'should this repo build one signal or two' actually asks)."""
    lab = quantile_labels(sig.to_numpy(), elig, rng)
    q, _, _ = bucket_means(lab, fwd)
    return (q[:, 0] - q[:, N_Q - 1]) if low_minus_high else (q[:, N_Q - 1] - q[:, 0])


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

    n_d, n_s = 400, 80
    dates = pd.bdate_range("2016-01-01", periods=n_d)
    cols = [f"S{i}" for i in range(n_s)]

    # 1. quantile labels: balanced, low bucket is bucket 0
    sig = np.tile(np.arange(n_s, dtype=float), (n_d, 1))
    elig = np.ones((n_d, n_s), bool)
    lab = quantile_labels(sig, elig, np.random.default_rng(1))
    check("bucket 0 holds the LOWEST signal values (the registered long leg)",
          lab[0, 0] == 0 and lab[0, -1] == N_Q - 1)
    sizes = [(lab == q).sum(1) for q in range(N_Q)]
    check("quintiles are balanced",
          all(s.min() >= n_s // N_Q - 1 and s.max() <= n_s // N_Q + 1 for s in sizes))

    # 2. a planted low-accrual premium is recovered with the right sign
    a = rng.normal(0, 0.05, (n_d, n_s))
    planted = -0.5 * a + rng.normal(0, 0.02, (n_d, n_s))
    lab = quantile_labels(a, elig, np.random.default_rng(2))
    q, _, _ = bucket_means(lab, planted)
    sp = np.nanmean(q[:, 0] - q[:, N_Q - 1])
    check("a planted LOW-accrual premium comes out POSITIVE", sp > 0.02,
          f"spread {sp * 100:+.2f}%")
    ctrl = random_pick_control(lab, planted, rng, reps=30).mean()
    check("random-pick control on the SAME planted data is ~0", abs(ctrl) < 0.005,
          f"{ctrl * 100:+.3f}%")

    # 3. the placebo control must kill a real pairing and SPARE a pure
    #    stock-level effect that has nothing to do with the pairing
    perm_null = placebo_control(a, elig, planted, rng, reps=30).mean()
    check("placebo (permuted symbol pairing) kills a genuine firm-level effect",
          abs(perm_null) < 0.2 * abs(sp), f"{sp * 100:+.2f}% -> {perm_null * 100:+.2f}%")

    # 4. NO LOOKAHEAD: a signal that IS the forward return must not survive a
    #    correctly-built pipeline once it is shifted out of reach
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, .01, (n_d, n_s)), 0)),
                         index=dates, columns=cols)
    fwd1 = (close.shift(-1) / close - 1.0).to_numpy()
    peek = pd.DataFrame(-fwd1, index=dates, columns=cols)      # perfect foresight
    lab = quantile_labels(peek.to_numpy(), np.isfinite(fwd1), np.random.default_rng(3))
    q0, _, _ = bucket_means(lab, fwd1)
    lagged = quantile_labels(peek.shift(2).to_numpy(), np.isfinite(fwd1),
                             np.random.default_rng(3))
    q2, _, _ = bucket_means(lagged, fwd1)
    check("a peeking signal shows a huge spread (the detector works)",
          np.nanmean(q0[:, 0] - q0[:, N_Q - 1]) > 0.01)
    check("...and shifting it out of reach kills it",
          abs(np.nanmean(q2[:, 0] - q2[:, N_Q - 1])) < 0.002)

    # 5. accrual_panel: filing date, not period end; staleness cap bites
    rec = pd.DataFrame({
        "ticker": ["A", "A", "B"],
        "ddate": pd.to_datetime(["2019-12-31", "2020-12-31", "2019-12-31"]),
        "filed": pd.to_datetime(["2020-02-20", "2021-02-20", "2020-02-20"]),
        "accrual": [0.10, -0.10, 0.05]})
    d = pd.bdate_range("2020-01-01", "2021-12-31")
    acc, age = accrual_panel(rec, d, ["A", "B"])
    check("nothing is known before the filing date",
          not np.isfinite(acc.loc[pd.Timestamp("2020-02-19"), "A"]))
    check("the fact appears the session AFTER its filing (shift(1))",
          not np.isfinite(acc.loc[pd.Timestamp("2020-02-20"), "A"])
          and acc.loc[pd.Timestamp("2020-02-21"), "A"] == 0.10)
    check("a newer filing replaces the older one",
          acc.loc[pd.Timestamp("2021-03-01"), "A"] == -0.10)
    # B never files again, so its fiscal 2019 record ages out 550 days after
    # 2019-12-31 (= 2021-07-03) even though it stays forward-filled.
    check("the staleness cap retires a fiscal year older than 550 days",
          np.isfinite(acc.loc[pd.Timestamp("2021-06-01"), "B"])
          and not np.isfinite(acc.loc[pd.Timestamp("2021-12-01"), "B"]))

    # 6. data-debt guard
    c = pd.DataFrame({"A": [10.0] * 10, "B": [10.0] * 10})
    c.loc[5, "A"] = 100.0
    b1 = bad_print_mask(c)
    check("a +900% print is flagged (and so is the -90% snap back)",
          bool(b1[5, 0]) and bool(b1[6, 0]) and not b1[:, 1].any())
    lone = np.zeros((10, 2), bool)
    lone[5, 0] = True
    cont = window_contaminated(lone, 3)
    check("the contaminated-window mask covers (t, t+h] and not t itself",
          bool(cont[2, 0]) and bool(cont[4, 0]) and not bool(cont[5, 0])
          and not bool(cont[1, 0]) and not cont[:, 1].any())

    # 7. stale-quote retirement
    c2 = pd.DataFrame({"A": [1.0, 2.0, 3.0] + [3.0] * 12, "B": np.arange(15.0) + 1})
    cleaned, n = retire_stale_quotes(c2, run=10)
    check("a frozen quote retires its symbol and spares the others",
          n == 1 and cleaned["A"].isna().sum() > 0 and cleaned["B"].notna().all())

    # 8. block bootstrap widens the SE on autocorrelated data
    ar = np.zeros(1500)
    for i in range(1, 1500):
        ar[i] = 0.85 * ar[i - 1] + rng.normal(0, 1)
    wide, narrow = block_boot(ar, 12, 2000, rng), block_boot(ar, 1, 2000, rng)
    check("block bootstrap gives a wider SE than the i.i.d. one on AR(1) data",
          wide["se"] > 1.5 * narrow["se"],
          f"block {wide['se']:.3f} vs iid {narrow['se']:.3f}")

    # 9. phase sweep decomposes the overlapping mean
    x = rng.normal(0, 1, 600)
    check("phase means average back to the overlapping mean",
          abs(phase_sweep(x, 6).mean() - x.mean()) < 1e-9)

    # 10. ols_beta recovers a planted beta
    xm = rng.normal(0, .01, 800)
    ym = 0.4 * xm + 0.001 + rng.normal(0, .002, 800)
    al, be, ta = ols_beta(ym, xm)
    check("ols_beta recovers a planted beta and alpha",
          abs(be - 0.4) < 0.05 and abs(al - 0.001) < 0.0004, f"beta {be:.3f}")

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
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="fewer control draws (diagnostics, not for quoting)")
    args = ap.parse_args()
    if args.selftest:
        _hdr("SELFTEST (offline, no keys, no network)")
        raise SystemExit(selftest())

    global CTRL_REPS
    if args.quick:
        CTRL_REPS = 30

    t0 = time.time()
    rng = np.random.default_rng(SEED)
    from . import pit

    _hdr("H27 - the accruals anomaly (Sloan 1996) on 2016-2026 index members")
    print("MECHANISM: the accrual part of earnings is less persistent than the")
    print("cash part, and investors do not decompose the headline number, so")
    print("high-accrual firms are over-valued and underperform.")
    print("REGISTERED SIGN: LOW accruals MINUS HIGH accruals is POSITIVE.")
    print("PRIOR: this is the hardest cohort for it (large/mid caps, post-2003,")
    print("post-publication). A null is the modal expected outcome.")

    # ---------------------------------------------------------------- data
    print("\nloading prices ...")
    bars = load_bars(refresh=args.refresh)
    # normalise every frame's index together: a tz-aware volume frame silently
    # reindexes to all-NaN against a tz-naive close and takes a whole variant
    # down with no error message.
    bars = {k: v.astype("float64").set_axis(
        pd.DatetimeIndex(v.index).tz_localize(None).normalize()).sort_index()
        for k, v in bars.items()}
    close = bars["close"]
    close, n_retired = retire_stale_quotes(close)
    print(f"  {close.shape[0]} sessions x {close.shape[1]} symbols  "
          f"{close.index[0].date()} .. {close.index[-1].date()}")
    print(f"  symbols retired at a frozen-quote run of >={STALE_QUOTE_RUN}: {n_retired}")

    cur = pd.read_csv(config.UNIVERSE_CSV)
    sp1500 = sorted(set(cur["symbol"]) & set(close.columns))
    pit_union = sorted(set(pit.all_members_since("2016-01-01")) & set(close.columns))
    tickers = sorted(set(sp1500) | set(pit_union))

    print("\nloading fundamentals (sec_bulk per-tag files) ...")
    rec = annual_records(tickers, refresh=args.refresh)
    print(f"  usable annual accrual records: {len(rec):,} over "
          f"{rec['ticker'].nunique()} tickers")

    form = month_end_index(close)
    # built on the DAILY index so shift(1) really is one session, then read at
    # the month ends. Building it on the monthly grid would silently make the
    # "one session of slack" a whole month.
    acc_daily, _ = accrual_panel(rec, close.index, tickers)
    acc_all = acc_daily.loc[form]

    # ------------------------------------------------------------ coverage
    _hdr("XBRL COVERAGE - the binding constraint, reported before any result")
    seg = cur.set_index("symbol")["segment"].to_dict()
    have = set(rec["ticker"])
    for nm, u in (("S&P 1500 (today's members)", sp1500),
                  ("point-in-time S&P 500 union since 2016", pit_union)):
        k = len([s for s in u if s in have])
        print(f"  {nm:<42} {k:>5} / {len(u):<5} have a matched-period "
              f"NI+CFO+assets record ({100 * k / len(u):.1f}%)")
    for sg in ("large", "mid", "small"):
        u = [s for s in sp1500 if seg.get(s) == sg]
        k = len([s for s in u if s in have])
        print(f"    of which {sg:<6} {k:>5} / {len(u):<5} ({100 * k / max(len(u), 1):.1f}%)")
    miss = sorted(set(sp1500) - have)
    print(f"\n  S&P 1500 names with NO usable record ({len(miss)}): "
          f"{', '.join(miss[:18])}{' ...' if len(miss) > 18 else ''}")
    print("  These are overwhelmingly firms that tag consolidated earnings as")
    print("  `ProfitLoss` (income including non-controlling interests) rather")
    print("  than `NetIncomeLoss`. `ProfitLoss` is not in sec_bulk's tag set, so")
    print("  the exclusion is SYSTEMATIC (utilities, firms with minority")
    print("  interests), not random. It is a bias of unknown sign, not noise.")
    print(f"\n  point-in-time universe: {100 * len([s for s in pit_union if s in have]) / len(pit_union):.0f}% "
          "coverage, and the missing names are the")
    print("  DELISTED ones - the SEC's company_tickers.json maps only CURRENT")
    print("  registrants, so an acquired company's CIK has no ticker and its")
    print("  facts are unreachable. The survivorship-free universe is therefore")
    print("  survivorship-CONTAMINATED on the fundamental side. Said plainly")
    print("  because it bounds what the pit500 rows below can prove.")

    cov = acc_all.notna().sum(axis=1)
    print("\n  eligible names per formation date (accrual known, not stale):")
    for y in range(2016, 2027):
        m = cov.index.year == y
        if m.any():
            print(f"    {y}   mean {cov[m].mean():6.0f}   min {cov[m].min():4.0f}   "
                  f"max {cov[m].max():4.0f}")

    # first formation date with a usable cross-section
    start = form[cov.to_numpy() >= 100]
    form = form[(form >= start[0]) if len(start) else slice(None)]
    acc_all = acc_all.loc[form]
    print(f"\n  study starts at the first month end with >=100 eligible names: "
          f"{form[0].date()}")
    print(f"  formation dates: {len(form)} month ends, "
          f"{form[0].date()} .. {form[-1].date()}")

    # -------------------------------------------------------- data hygiene
    _hdr("DATA-DEBT GUARD (BACKTEST-REPORT.md: 5.1% of splits are unadjusted)")
    bad = bad_print_mask(close)
    r = (close / close.shift(1) - 1.0).to_numpy()
    n_bad = int(bad.sum())
    worst = np.dstack(np.unravel_index(np.argsort(-np.abs(np.where(bad, r, 0)), axis=None)[:8],
                                       r.shape))[0]
    print(f"  |1-day return| > {BIG_MOVE:.0%}: {n_bad} prints over "
          f"{int((bad.any(0)).sum())} symbols")
    for i, j in worst:
        print(f"    {close.columns[j]:<6} {close.index[i].date()}  "
              f"{r[i, j] * 100:+9.1f}%")
    print("\n  A (symbol, formation date) leg is DROPPED when such a print falls")
    print(f"  inside its holding window. The whole study is re-run with the guard")
    print("  OFF below, so the choice is priced rather than asserted.")

    accs = acc_all.reindex(columns=tickers)
    closef = close.reindex(columns=tickers)
    badf = bad[:, [close.columns.get_loc(t) for t in tickers]]

    member_sp1500 = np.array([[t in set(sp1500) for t in tickers]] * len(form))
    member_pit = np.array([[t in pit.members(d) for t in tickers] for d in form])
    print(f"\n  pit500 membership at formation dates: mean "
          f"{member_pit.sum(1).mean():.0f} names of {len(tickers)} in the frame")

    # ------------------------------------------------------------- primary
    _hdr(f"PRIMARY: U1 sp1500, Q1(low accruals) minus Q5(high accruals), % per hold")
    print("CI = circular moving-block bootstrap over formation dates, block =")
    print("the number of month ends an h-session window spans. Registered sign +.\n")
    res1, ser1 = run_universe("sp1500", accs, closef, form, member_sp1500,
                              badf, rng)
    _hdr("PRIMARY: full table")
    print(res1[["h", "n_dates", "n_names", "q1", "q3", "q5", "pool", "spread",
                "lo", "hi", "t", "q1_excess", "t_excess", "half1", "half2",
                "turn_lo", "turn_hi"]].to_string(index=False, float_format=_fmt))
    print("\nq1/q3/q5/pool are RAW bucket returns in % over the h-session hold")
    print("(they contain the market; spread and q1_excess do not).")
    print("q1_excess = CONTROL (c), the matched benchmark: the LOW-accrual")
    print("quintile minus the eligible-pool mean = the long-only claim.")

    _hdr("U2 pit500 (survivorship control on membership)")
    res2, ser2 = run_universe("pit500", accs, closef, form, member_pit, badf, rng)

    # ------------------------------------------------------------ controls
    _hdr("CONTROLS (a) RANDOM PICK, (b) PLACEBO PAIRING, (c) DATE SHUFFLE")
    print(f"(a) {CTRL_REPS} draws: labels permuted inside each formation date.")
    print(f"(b) {CTRL_REPS} draws: every symbol keeps a whole accrual history,")
    print("    but somebody else's - the null for a PERSISTENT characteristic.")
    print(f"(c) {CTRL_REPS} draws: each symbol's OWN accrual history permuted")
    print("    across formation dates. Firm identity and its accrual")
    print("    distribution survive; only the YEAR dies. Sloan's mechanism is")
    print("    about which year a firm accrued, so it must collapse here.")
    print("    THIS IS THE CONTROL THE HYPOTHESIS TURNS ON.\n")
    crows = []
    for h in HORIZONS:
        s = ser1[h]
        r1 = res1[res1["h"] == h].iloc[0]
        real_se = abs(r1["spread"] / r1["t"]) if r1["t"] else float("nan")
        rnd = random_pick_control(s["lab"], s["fwd"], rng) * 100
        plc = placebo_control(accs.to_numpy(), s["elig"], s["fwd"], rng) * 100
        shf = date_shuffle_control(accs.to_numpy(), s["elig"], s["fwd"], rng) * 100
        act = float(np.nanmean(s["spread"])) * 100
        crows.append(dict(h=h, spread=act,
                          rand_mean=rnd.mean(), rand_sd=rnd.std(ddof=1),
                          plac_mean=plc.mean(), plac_sd=plc.std(ddof=1),
                          shuf_mean=shf.mean(), shuf_sd=shf.std(ddof=1),
                          timing=act - shf.mean(),
                          se_ratio_rand=rnd.std(ddof=1) / real_se,
                          se_ratio_plac=plc.std(ddof=1) / real_se,
                          p_shuffle=float((shf >= act).mean())))
    ctrl = pd.DataFrame(crows)
    print(ctrl.to_string(index=False, float_format=_fmt))
    print("\ntiming        = actual spread minus the date-shuffled mean: the part")
    print("                of the effect that is about WHICH YEAR the firm accrued.")
    print("p_shuffle     = share of date-shuffled draws at least as positive as")
    print("                actual. Near 0.5 means the null already explains it.")
    print("se_ratio_*    = each null's SD over the real series' block-bootstrap SE")
    print("                (Rule 14). Below 1 means that null is anti-conservative.")

    # -------------------------------------------------------------- Rule 13
    _hdr("RULE 13: the dollar-neutral book regressed on SPY")
    spy = close["SPY"] if "SPY" in close.columns else None
    brows = []
    for h in HORIZONS:
        sp_fwd = ((spy.shift(-h) / spy - 1.0).reindex(form).to_numpy()
                  if spy is not None else np.full(len(form), np.nan))
        for nm, ser in (("sp1500", ser1), ("pit500", ser2)):
            a, b, ta = ols_beta(ser[h]["spread"], sp_fwd)
            al, bl, tal = ols_beta(ser[h]["excess"], sp_fwd)
            brows.append(dict(universe=nm, h=h, ls_alpha=a * 100, ls_beta=b,
                              ls_t_alpha=ta, lo_alpha=al * 100, lo_beta=bl,
                              lo_t_alpha=tal))
    print(pd.DataFrame(brows).to_string(index=False, float_format=_fmt))
    print("\nls_ = the long/short quintile spread; lo_ = the long-only low-accrual")
    print("quintile minus the eligible pool. alpha is per h-session hold, in %.")

    # ------------------------------------------------------ long-only vs SPY
    _hdr("LONG-ONLY: the bottom (LOW-accrual) quintile against SPY and the pool")
    lrows = []
    for h in HORIZONS:
        sp_fwd = ((spy.shift(-h) / spy - 1.0).reindex(form).to_numpy()
                  if spy is not None else np.full(len(form), np.nan))
        for nm, ser in (("sp1500", ser1), ("pit500", ser2)):
            q1 = ser[h]["q"][:, 0]
            vs_spy = q1 - sp_fwd
            stride = ser[h]["stride"]
            b = block_boot(vs_spy, stride, BOOT_REPS, rng)
            bp = block_boot(ser[h]["excess"], stride, BOOT_REPS, rng)
            idx = np.flatnonzero(np.isfinite(vs_spy))
            half = len(idx) // 2
            lrows.append(dict(universe=nm, h=h, q1=np.nanmean(q1) * 100,
                              spy=np.nanmean(sp_fwd) * 100, pool=np.nanmean(ser[h]["pool"]) * 100,
                              vs_spy=b["mean"] * 100, t_spy=b["t"],
                              lo=b["lo"] * 100, hi=b["hi"] * 100,
                              vs_pool=bp["mean"] * 100, t_pool=bp["t"],
                              half1=float(np.mean(vs_spy[idx[:half]])) * 100,
                              half2=float(np.mean(vs_spy[idx[half:]])) * 100))
    print(pd.DataFrame(lrows).to_string(index=False, float_format=_fmt))

    # ------------------------------------------------------------- variants
    _hdr("REGISTERED VARIANTS (every one run is reported)")

    print("\n1. GUARD OFF - the same study without the bad-print exclusion:")
    resg, _ = run_universe("sp1500 no-guard", accs, closef, form, member_sp1500,
                           badf, rng, guard=False, verbose=False)
    cmpg = res1[["h", "spread", "t"]].merge(resg[["h", "spread", "t"]], on="h",
                                            suffixes=("_guard", "_raw"))
    print(cmpg.to_string(index=False, float_format=_fmt))

    print("\n2. SIZE SEGMENTS - the anomaly is documented as a down-cap effect:")
    seg_rows = []
    for sg in ("large", "mid", "small"):
        mem = np.array([[seg.get(t) == sg for t in tickers]] * len(form))
        r, _ = run_universe(sg, accs, closef, form, mem, badf, rng, verbose=False)
        seg_rows.append(r)
    print(pd.concat(seg_rows)[["universe", "h", "n_dates", "n_names", "spread",
                               "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))

    print("\n3. SECTOR-NEUTRAL RANKS - accruals differ structurally by industry,")
    print("   so the raw sort may be a sector bet:")
    sec = cur.set_index("symbol")["sector"].to_dict()
    sec_arr = np.array([sec.get(t, "?") for t in tickers])
    acc_sn = pd.DataFrame(np.nan, index=accs.index, columns=accs.columns)
    for s in sorted(set(sec_arr)):
        cols = np.flatnonzero(sec_arr == s)
        if len(cols) < 10:
            continue                                  # too thin to rank within
        acc_sn.iloc[:, cols] = accs.iloc[:, cols].rank(axis=1, pct=True).to_numpy()
    rsn, _ = run_universe("sector-neutral", acc_sn, closef, form, member_sp1500,
                          badf, rng, verbose=False)
    print(rsn[["h", "n_dates", "n_names", "spread", "lo", "hi", "t",
               "half1", "half2"]].to_string(index=False, float_format=_fmt))

    print("\n4. DECILES instead of quintiles (D1 minus D10, more extreme sort):")
    drows = []
    for h in HORIZONS:
        fwd = ((closef.shift(-h) / closef - 1.0).to_numpy()
               [close.index.get_indexer(form)])
        cont = window_contaminated(badf, h)[close.index.get_indexer(form)]
        elig = build_eligibility(closef.loc[form], accs, member_sp1500, fwd, cont)
        lab = quantile_labels(accs.to_numpy(), elig, np.random.default_rng(SEED + h), q=10)
        q, pool, cnt = bucket_means(lab, fwd, q=10)
        sp = q[:, 0] - q[:, 9]
        stride = max(int(round(h / 21)), 1)
        b = block_boot(sp, stride, BOOT_REPS, rng)
        idx = np.flatnonzero(np.isfinite(sp))
        half = len(idx) // 2
        drows.append(dict(h=h, n_dates=int(np.isfinite(sp).sum()),
                          n_names=float(cnt[np.isfinite(sp)].sum(1).mean()),
                          spread=b["mean"] * 100, lo=b["lo"] * 100, hi=b["hi"] * 100,
                          t=b["t"], half1=float(np.mean(sp[idx[:half]])) * 100,
                          half2=float(np.mean(sp[idx[half:]])) * 100))
    print(pd.DataFrame(drows).to_string(index=False, float_format=_fmt))

    print("\n5. SCALED BY ENDING ASSETS instead of average assets:")
    rec2 = rec.copy()
    rec2["accrual"] = (rec2["value_ni"] - rec2["value_cf"]) / rec2["assets_end"]
    rec2 = rec2[rec2["accrual"].abs() <= MAX_ABS_ACCRUAL]
    acc2, _ = accrual_panel(rec2, close.index, tickers)
    r5, _ = run_universe("end-assets", acc2.loc[form].reindex(columns=tickers),
                         closef, form, member_sp1500, badf, rng, verbose=False)
    print(r5[["h", "n_dates", "spread", "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))

    print("\n6. DELIBERATELY STALE - the accrual known 12 MONTHS AGO instead of")
    print("   the freshest one. A mispricing that corrects as accruals fail to")
    print("   convert should weaken; a static style tilt will not notice:")
    r7, _ = run_universe("stale-12m", accs.shift(12), closef, form, member_sp1500,
                         badf, rng, verbose=False)
    print(r7[["h", "n_dates", "n_names", "spread", "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))

    print("\n7. EX-FINANCIALS AND EX-REAL-ESTATE - Sloan's own design excludes")
    print("   financial firms, and for a good reason: a bank's operating cash")
    print("   flow is dominated by loan and trading-book flows, so NI - CFO is")
    print("   not an accrual in any accounting sense there. The sector table")
    print("   printed further down shows how far the quintiles tilt that way:")
    nonfin = np.array([[seg.get(t) is not None
                        and sec.get(t) not in ("Financials", "Real Estate")
                        for t in tickers]] * len(form))
    r7b, ser7b = run_universe("ex-fin/RE", accs, closef, form,
                              nonfin & member_sp1500, badf, rng, verbose=False)
    print(r7b[["h", "n_dates", "n_names", "spread", "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))

    print("\n8. LOOKAHEAD DIAGNOSTIC (not a strategy) - the accrual that will")
    print("   only be FILED 12 months from now. If this is not much larger than")
    print("   the honest signal, the honest signal is not sorting on accounting")
    print("   news at all:")
    r8, _ = run_universe("peek+12m", accs.shift(-12), closef, form, member_sp1500,
                         badf, rng, verbose=False)
    print(r8[["h", "n_dates", "n_names", "spread", "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))

    print("\n9. LIQUIDITY GATE (20d median dollar volume >= $10M, the engine's")
    print("   own tradeability floor) - the classic accrual spread lives in")
    print("   names too small to trade:")
    dvol = ((close * bars["volume"].reindex(columns=close.columns))
            .rolling(20, min_periods=10).median().reindex(columns=tickers))
    liq = (dvol.loc[form].to_numpy() >= config.MIN_DOLLAR_VOL) & member_sp1500
    r9, _ = run_universe("liquid", accs, closef, form, liq, badf, rng, verbose=False)
    print(r9[["h", "n_dates", "n_names", "spread", "lo", "hi", "t", "half1", "half2"]]
          .to_string(index=False, float_format=_fmt))

    print("\n10. GROSS PROFITABILITY CONTROL - the leading alternative story is")
    print("    that low accruals proxy for QUALITY, which this decade paid for")
    print("    (Novy-Marx gross profitability = GrossProfit / Assets, the same")
    print("    point-in-time machinery). Spread inside each profitability")
    print("    tercile; if it is a quality bet it should vanish within terciles:")
    gp = gross_profitability(tickers, close.index).loc[form].reindex(columns=tickers)
    cov_gp = np.isfinite(gp.to_numpy()) & ser1[PRIMARY_H]["elig"]
    print(f"    GrossProfit coverage on eligible legs at h={PRIMARY_H}: "
          f"{100 * cov_gp.sum() / max(ser1[PRIMARY_H]['elig'].sum(), 1):.1f}% "
          f"({int(np.isfinite(gp.to_numpy()).any(0).sum())} tickers ever)")
    gprows = []
    gpr = gp.rank(axis=1, pct=True).to_numpy()
    for h in (PRIMARY_H, 252):
        s = ser1[h]
        for k, (lo_b, hi_b) in enumerate(((0.0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.01))):
            m = s["elig"] & (gpr > lo_b) & (gpr <= hi_b)
            lab = quantile_labels(accs.to_numpy(), m, np.random.default_rng(SEED + h))
            q, _, cnt = bucket_means(lab, s["fwd"])
            sp = q[:, 0] - q[:, N_Q - 1]
            b = block_boot(sp, s["stride"], BOOT_REPS, rng)
            gprows.append(dict(h=h, gp_tercile=["low", "mid", "high"][k],
                               n_dates=int(np.isfinite(sp).sum()),
                               n_names=float(cnt[np.isfinite(sp)].sum(1).mean()),
                               spread=b["mean"] * 100, lo=b["lo"] * 100,
                               hi=b["hi"] * 100, t=b["t"]))
    print(pd.DataFrame(gprows).to_string(index=False, float_format=_fmt))

    # ------------------------------------------------- what is in the buckets
    print("\nloading split-adjusted share counts (sec_bulk.shares_panel) ...")
    shares = monthly_shares(tickers, form)

    _hdr("WHAT IS ACTUALLY IN THE LOW-ACCRUAL QUINTILE")
    print("DESCRIPTIVE. If the spread is a sector or size bet, this is where it")
    print("shows, and a sector bet needs no accounting mechanism.\n")
    lab42 = ser1[PRIMARY_H]["lab"]
    comp = []
    for s in sorted(set(sec_arr)):
        if s == "?":
            continue
        colm = (sec_arr == s)
        tot = (lab42 >= 0) & colm[None, :]
        if tot.sum() < 200:
            continue
        comp.append(dict(sector=s,
                         pool_share=100 * tot.sum() / max((lab42 >= 0).sum(), 1),
                         q1_share=100 * ((lab42 == 0) & colm[None, :]).sum()
                         / max((lab42 == 0).sum(), 1),
                         q5_share=100 * ((lab42 == N_Q - 1) & colm[None, :]).sum()
                         / max((lab42 == N_Q - 1).sum(), 1)))
    cdf = pd.DataFrame(comp)
    cdf["q1_minus_q5"] = cdf["q1_share"] - cdf["q5_share"]
    print(cdf.sort_values("q1_minus_q5", ascending=False)
          .to_string(index=False, float_format=_fmt))
    print("\nshares are % of all symbol-date slots in that bucket, h=42, sp1500.")

    mcap = shares.reindex(index=form, columns=tickers) * closef.loc[form]
    lm = np.log(mcap.to_numpy())
    print("\nmedian log market cap by bucket (a size bet would show here):")
    for qi in range(N_Q):
        v = lm[(lab42 == qi) & np.isfinite(lm)]
        print(f"  Q{qi + 1}  median ${math.exp(np.median(v)) / 1e9:8.2f}bn   "
              f"n={len(v):,}")

    # --------------------------------------------------------- independence
    _hdr("INDEPENDENCE - is this the momentum composite or net issuance again?")
    print("If accruals rank stocks the same way something this repo already")
    print("computes, it should build one signal, not two (Pontiff-Woodgate note")
    print("that net issuance and accruals are related by construction: the same")
    print("firms that accrue also issue).\n")
    mom = momentum_scores(bars, form, tickers)
    iss = issuance_scores(shares).reindex(columns=tickers)
    e42 = ser1[PRIMARY_H]["elig"]
    rc_mom = rank_corr_by_date(accs, mom, e42)
    rc_iss = rank_corr_by_date(accs, iss, e42)
    print(f"  cross-sectional Spearman(accrual rank, v5 composite score): "
          f"mean {np.nanmean(rc_mom):+.3f}  sd {np.nanstd(rc_mom):.3f}  "
          f"n={int(np.isfinite(rc_mom).sum())} dates")
    print(f"  cross-sectional Spearman(accrual rank, 12m net issuance)  : "
          f"mean {np.nanmean(rc_iss):+.3f}  sd {np.nanstd(rc_iss):.3f}  "
          f"n={int(np.isfinite(rc_iss).sum())} dates")

    fwd42 = ser1[PRIMARY_H]["fwd"]
    s_acc = ser1[PRIMARY_H]["spread"]
    s_mom = spread_series(mom, e42, fwd42, np.random.default_rng(SEED + 1),
                          low_minus_high=False)      # momentum: HIGH minus LOW
    s_iss = spread_series(iss, e42, fwd42,
                          np.random.default_rng(SEED + 2), low_minus_high=True)
    ret_rho = {}
    for nm, s in (("v5 momentum composite (Q5-Q1)", s_mom),
                  ("net issuance (Q1-Q5, low issuance long)", s_iss)):
        m = np.isfinite(s_acc) & np.isfinite(s)
        rho = float(np.corrcoef(s_acc[m], s[m])[0, 1]) if m.sum() > 10 else float("nan")
        ret_rho[nm] = dict(rho=rho, own_mean_pct=float(np.nanmean(s) * 100))
        print(f"  return correlation, accrual spread vs {nm:<40} "
              f"{rho:+.3f}   (its own mean {np.nanmean(s) * 100:+.2f}%/hold)")
    print("\nThe rank correlation answers 'do they sort the same names'; the")
    print("return correlation answers 'do they make the same money'. The second")
    print("is the one that decides whether to build two signals or one.")

    # ---------------------------------------------------------------- costs
    _hdr(f"COSTS ({COST_BPS:.0f} bps round trip per leg)")
    print("Registered book: LONG the low-accrual quintile, SHORT the high one,")
    print("rebalanced every `stride` month ends so the hold matches h.\n")
    print(pd.concat([costs(res1), costs(res2)]).to_string(index=False,
                                                          float_format=_fmt))
    print("\nbreakeven_bps = the round-trip cost per leg at which the registered")
    print(f"trade earns exactly zero. Charged: {COST_BPS:.0f} bps (more down-cap).")

    # ----------------------------------------------------------- effective n
    _hdr("SAMPLE AND THE EFFECTIVE INDEPENDENT SAMPLE")
    n_legs = int((ser1[PRIMARY_H]["lab"] >= 0).sum())
    print(f"symbol-formation-date legs at h={PRIMARY_H} (sp1500): {n_legs:,}")
    print(f"formation dates                                   : {len(form)}")
    print(f"EFFECTIVE INDEPENDENT SAMPLE at h={PRIMARY_H}: the cross-section is")
    print("collapsed to one spread per formation date before any statistic, so n")
    print(f"is at most {len(form)} - not {n_legs:,}. Monthly formation with a")
    print(f"{PRIMARY_H}-session hold overlaps two months, so the honestly")
    print(f"independent count is ~{len(form) // 2} non-overlapping windows per entry")
    print(f"phase, and there are 2 such phases. At h=252 it is ~{len(form) // 12}.")

    # ---------------------------------------------------------- machine-readable
    out = dict(
        generated=pd.Timestamp.utcnow().isoformat(),
        registered_sign="LOW accruals minus HIGH accruals is POSITIVE",
        primary_h=PRIMARY_H, cost_bps=COST_BPS,
        form_start=str(form[0].date()), form_end=str(form[-1].date()),
        n_form_dates=len(form), n_annual_records=int(len(rec)),
        n_tickers_with_records=int(rec["ticker"].nunique()),
        primary_sp1500=res1.to_dict("records"),
        pit500=res2.to_dict("records"),
        controls=ctrl.to_dict("records"),
        spy_regression=brows,
        long_only=lrows,
        v_guard_off=resg.to_dict("records"),
        v_segments=pd.concat(seg_rows).to_dict("records"),
        v_sector_neutral=rsn.to_dict("records"),
        v_deciles=drows,
        v_end_assets=r5.to_dict("records"),
        v_stale_12m=r7.to_dict("records"),
        v_ex_financials=r7b.to_dict("records"),
        v_peek_12m=r8.to_dict("records"),
        v_liquid=r9.to_dict("records"),
        v_gross_profitability_terciles=gprows,
        sector_composition=cdf.to_dict("records"),
        independence=dict(
            rank_corr_momentum=float(np.nanmean(rc_mom)),
            rank_corr_momentum_sd=float(np.nanstd(rc_mom)),
            rank_corr_issuance=float(np.nanmean(rc_iss)),
            rank_corr_issuance_sd=float(np.nanstd(rc_iss)),
            return_corr=ret_rho),
        costs=pd.concat([costs(res1), costs(res2)]).to_dict("records"))
    path = config.SCOUT_DIR / "accruals_results.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"\nwrote {path.name}")

    print(f"\n[{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
