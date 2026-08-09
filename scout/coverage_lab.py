"""H33 — Lynch's neglect premium: is the LEVEL of analyst/media coverage priced?

MECHANISM (one sentence, before any number)
-------------------------------------------
A stock nobody researches has a staler price and a smaller investor base, so
information is incorporated more slowly and holders demand a higher expected
return for bearing the extra idiosyncratic risk they cannot share (Merton 1987's
investor-recognition hypothesis; Peter Lynch used "no analyst coverage" as an
explicit BUYING criterion at Magellan; Hong-Lim-Stein 2000 add the interaction
test — momentum should be STRONGEST where news travels slowest, i.e. among the
least-covered names).

WHY THIS IS NOT H15 AGAIN
-------------------------
H15 tested the CHANGE in coverage (an attention shock) and was killed by its own
date-shuffle control: destroying the timing barely dented the spread, which
proved the effect was a static property of WHICH stocks are covered rather than
of WHEN.  That killed finding is this lab's PREMISE.  Here the static
characteristic itself is the signal, so the date-shuffle control cannot kill it
-- it is expected to REPRODUCE the spread, and that is a consistency check, not
a refutation.  (Measured below: rank autocorrelation of trailing coverage at a
252-session lag is 0.92.  The characteristic is as persistent as claimed.)

THE HONEST LIMIT, STATED UP FRONT AND REPEATED IN THE VERDICT
------------------------------------------------------------
The cached news panel is 120 LARGE, LIQUID names -- the point-in-time 120 most
liquid S&P 500 members as of 2016-01-04.  These are the LEAST neglected stocks
in the US market.  Whatever this lab measures is a within-mega-cap coverage
gradient, not the neglect premium of the micro-cap tail Lynch was fishing in.
A null here is weak evidence about the neglect premium generally and the verdict
says so.  What IS testable here is the dispersion: the trailing-252 story count
runs about 6x-12x from the 10th to the 90th percentile inside this panel, and
after liquidity normalisation still about 4x, so the sort is not degenerate.

DATA DEFECTS GUARDED (all three from BACKTEST-REPORT.md, and which one bites)
----------------------------------------------------------------------------
G1  unadjusted splits (5.1%).  Any |1-day close move| > 45% marks that session
    dirty; a formation is dropped for a symbol whose forward window contains a
    dirty session, and momentum is dropped if its trailing window does.
    NOTE the size proxy is deliberately DOLLAR VOLUME: an unapplied split
    multiplies price and divides volume by the same factor, so price x volume
    is invariant to the defect.  A market-cap proxy is NOT (SEC shares are
    split-adjusted while these closes sometimes are not -- AAPL pre-2020-08-31
    would read 4x).  Market cap is therefore only a robustness variant.
G2  spin-offs / reused tickers (146 events).  Same >45% mask, PLUS a gap rule:
    >= 10 consecutive missing sessions inside a symbol's history retires it
    from the gap onward.  This is load-bearing here -- FB (last honest print
    2022-06-08) and APC (2019-08-08) both come back to life in this cache under
    a different issuer while their Benzinga coverage stays near zero, i.e. they
    would sit in the "most neglected" bucket with a fabricated price path.
G3  frozen quotes.  A symbol is retired at the first run of >= 10 identical
    closes (catches EMC from 2016-09-07, MON from 2018-06-07).  Unfiltered
    these manufactured +896 bps of fake drift in H26, and they are precisely
    the acquired names whose news coverage goes to zero -- the exact shape that
    would fake a neglect premium.
G4 (this lab's own, not in the repo list) TAGGING ARTIFACTS.  Benzinga tags
    Berkshire under a ticker this panel does not carry (BRK.B: 14 stories in
    ten years) and tags Priceline under PCLN before the 2018 rename (BKNG: 0
    stories in year one).  A mega-cap with structurally untagged news is not a
    neglected stock; it is a join failure.  Reported both ways -- with the
    floor and without -- and the bottom bucket's composition is printed.

THE SHIFT, EXACTLY ONE PLACE
----------------------------
`build_panel()`.  The coverage frames from scout/news_data.py already hold, in
row t, only stories publishable BEFORE session t's close.  This lab lags them
one further full session anyway (`.shift(1)`): the signal at formation date t is
the 252-session sum ending at t-1, and the return window is close(t) ->
close(t+42).  Nothing else in the file touches a future bar.

SIGN CONVENTION
---------------
NEGLECT = LOW coverage.  Every "spread" in this file is LOW-minus-HIGH, so a
POSITIVE number supports the hypothesis.  Stated again in every table header.

Usage:
    python -m scout.coverage_lab              # the full study
    python -m scout.coverage_lab --selftest   # machinery checks, no verdict
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import bars, config, news_data

# ------------------------------------------------------------------ constants

H = 42                    # hold, sessions (config.HORIZON_TDAYS)
LOOKBACK = 252            # trailing window for the coverage LEVEL
MOM_LOOK = 252            # 12-1 momentum lookback
MOM_SKIP = 21             # ... skipping the last month
BIG_MOVE = 0.45           # |1-day| beyond which a bar is presumed corrupt (G1/G2)
FROZEN_RUN = 10           # identical closes that retire a symbol (G3)
GAP_RUN = 10              # missing sessions that retire a symbol (G2)
MIN_POOL = 30             # dates with a thinner eligible cross-section are skipped
COST_BPS = 10.0           # round-trip, large caps
BOOT_REPS = 2000
BOOT_SEEDS = (20260809, 777, 31337, 90210, 4242)   # Rule 16: MC sd of the boot t
DRAWS = 200               # control draws
SEED = 20260809
BENCH = "SPY"
STALE = LOOKBACK          # date-shuffle donors must be >= 1 year in the past

CACHE = config.SCOUT_DIR / "cache_coverage_lab.pkl"
RESULTS = config.SCOUT_DIR / "coverage_results.json"

# every variant this lab runs, named, so the count in the verdict is honest
VARIANTS: list[str] = []


def _reg(name: str) -> str:
    if name not in VARIANTS:
        VARIANTS.append(name)
    return name


# ------------------------------------------------------------------ data layer

def _panel_symbols() -> list[str]:
    p = config.SCOUT_DIR / "cache_news_liquid120_symbols.json"
    return json.loads(p.read_text())


def load_raw(refresh: bool = False) -> dict:
    """Bars + news frames for the cached liquid-120 panel.  Uses the SHARED
    master bar cache (scout/bars.py) and the SHARED news panel
    (cache_news_liquid120.pkl); nothing is downloaded that a sibling lab
    already has."""
    if CACHE.exists() and not refresh:
        with open(CACHE, "rb") as f:
            d = pickle.load(f)
        print(f"cache: {d['close'].shape[0]} sessions x {d['close'].shape[1]} symbols")
        return d
    syms = _panel_symbols()
    px = bars.get(syms + [BENCH], "2016-01-01", "2026-08-07", verbose=True)
    close = px["close"].copy()
    volume = px["volume"].copy()
    close.index = close.index.tz_localize(None)
    volume.index = volume.index.tz_localize(None)
    stories = news_data.load_panel()
    frames = news_data.daily_news_panel(stories, close.index, verbose=True)
    d = {"close": close, "volume": volume,
         "n_specific": frames["n_specific"].astype(float),
         "n_headlines": frames["n_headlines"].astype(float),
         "n_novel": frames["n_novel"].astype(float),
         "symbols": syms}
    with open(CACHE, "wb") as f:
        pickle.dump(d, f)
    return d


# ---------------------------------------------------------------- price guards

def _first_frozen(v: np.ndarray) -> int | None:
    """Index of the START of the first run of FROZEN_RUN identical closes."""
    ok = np.isfinite(v)
    same = np.zeros(len(v), bool)
    same[1:] = ok[1:] & ok[:-1] & (v[1:] == v[:-1])
    run = 0
    for i in range(len(v)):
        run = run + 1 if same[i] else 0
        if run >= FROZEN_RUN - 1:
            # `run` equalities ending at i cover run+1 identical values, so the
            # first of them sits at i - run.
            return i - run
    return None


def _first_gap(v: np.ndarray) -> int | None:
    """Index of the START of the first interior run of GAP_RUN missing closes
    (a reused ticker: the series dies, then a different issuer revives it)."""
    ok = np.isfinite(v)
    if ok.sum() == 0:
        return None
    first, last = int(np.argmax(ok)), len(ok) - 1 - int(np.argmax(ok[::-1]))
    run, start = 0, None
    for i in range(first, last + 1):
        if not ok[i]:
            if run == 0:
                start = i
            run += 1
            if run >= GAP_RUN:
                return start
        else:
            run = 0
    return None


def apply_guards(close: pd.DataFrame, verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    """G2/G3: retire a symbol at the first frozen run or the first interior gap.
    Returns a cleaned close frame plus a report of what was retired and why."""
    out = close.copy()
    log = []
    for s in out.columns:
        v = out[s].to_numpy().copy()      # copy: the frame is mutated below
        fz, gp = _first_frozen(v), _first_gap(v)
        cuts = [(i, why) for i, why in ((fz, "frozen"), (gp, "gap")) if i is not None]
        if not cuts:
            continue
        i, why = min(cuts)
        out.iloc[i:, out.columns.get_loc(s)] = np.nan
        log.append({"symbol": s, "reason": why, "from": str(out.index[i].date()),
                    "sessions_dropped": int(np.isfinite(v[i:]).sum())})
    if verbose and log:
        print(f"  guards G2/G3 retired {len(log)} symbols "
              f"({sum(r['sessions_dropped'] for r in log):,} symbol-sessions):")
        for r in sorted(log, key=lambda r: -r["sessions_dropped"])[:12]:
            print(f"    {r['symbol']:<6} {r['reason']:<7} from {r['from']}"
                  f"  ({r['sessions_dropped']} sessions dropped)")
    return out, {"retired": log}


# ------------------------------------------------------------- panel assembly

def _rank_pct(x: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank of the finite entries; NaN elsewhere."""
    out = np.full(len(x), np.nan)
    ok = np.isfinite(x)
    n = int(ok.sum())
    if n == 0:
        return out
    order = np.argsort(np.argsort(x[ok], kind="stable"), kind="stable")
    out[ok] = (order + 1) / n
    return out


def _xs_residual(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Cross-sectional OLS residual of y on [1, x] (NaN-safe, per date)."""
    out = np.full(len(y), np.nan)
    ok = np.isfinite(y) & np.isfinite(x)
    if ok.sum() < 10:
        return out
    X = np.column_stack([np.ones(ok.sum()), x[ok]])
    b = np.linalg.lstsq(X, y[ok], rcond=None)[0]
    out[ok] = y[ok] - X @ b
    return out


def build_panel(raw: dict, guard: bool = True, news_floor: float = 0.0,
                count_field: str = "n_specific", lookback: int = LOOKBACK,
                horizon: int = H, step: int = 1) -> dict:
    """Formation-date arrays.  THE SHIFT LIVES HERE.

    Coverage row t is the sum over news sessions [t-lookback .. t-1] (one full
    session of extra lag on top of news_data's own before-the-close
    attribution).  The return window is close(t) -> close(t+horizon).
    """
    close_raw, volume = raw["close"], raw["volume"]
    close, guard_log = (apply_guards(close_raw) if guard
                        else (close_raw.copy(), {"retired": []}))

    syms = [s for s in close.columns if s != BENCH]
    C = close[syms]
    V = volume[syms].reindex(columns=syms)
    ret1 = C.pct_change()
    dirty = (ret1.abs() > BIG_MOVE).fillna(False)          # G1 / G2

    # ---- signal inputs, all trailing and all lagged one session
    counts = raw[count_field][syms].reindex(index=C.index).fillna(0.0)
    cov = counts.rolling(lookback, min_periods=int(0.8 * lookback)).sum().shift(1)
    dv = (C * V)
    adv = dv.rolling(lookback, min_periods=int(0.8 * lookback)).mean().shift(1)
    # 12-1 momentum, and its own contamination mask
    mom = (C.shift(MOM_SKIP) / C.shift(MOM_LOOK) - 1.0)
    mom_dirty = dirty.rolling(MOM_LOOK, min_periods=1).max().fillna(0.0) > 0

    Cn, COV, ADV, MOM = C.to_numpy(), cov.to_numpy(), adv.to_numpy(), mom.to_numpy()
    MOMD = mom_dirty.to_numpy()
    D = dirty.to_numpy()
    n_t, n_s = Cn.shape

    lo = max(lookback + MOM_LOOK + 1, 260)
    dates_i = list(range(lo, n_t - horizon, step))

    FWD = np.full((len(dates_i), n_s), np.nan)
    OPEN = np.zeros((len(dates_i), n_s), bool)
    SIG_RAW = np.full((len(dates_i), n_s), np.nan)
    SIG_RATIO = np.full((len(dates_i), n_s), np.nan)
    SIG_RESID = np.full((len(dates_i), n_s), np.nan)
    SZ = np.full((len(dates_i), n_s), np.nan)
    MM = np.full((len(dates_i), n_s), np.nan)
    dropped_dirty = 0

    for k, t in enumerate(dates_i):
        c0, c1 = Cn[t], Cn[t + horizon]
        path_bad = D[t + 1:t + horizon + 1].any(axis=0)
        dropped_dirty += int((np.isfinite(c0) & np.isfinite(c1) & path_bad).sum())
        f = np.where(np.isfinite(c0) & np.isfinite(c1) & (c0 > 0) & ~path_bad,
                     c1 / c0 - 1.0, np.nan)
        cv, av = COV[t], ADV[t]
        okc = np.isfinite(cv) & np.isfinite(av) & (av > 0) & (cv >= news_floor)
        lcov = np.where(okc, np.log1p(np.where(okc, cv, 0.0)), np.nan)
        ladv = np.where(okc, np.log(np.where(okc & (av > 0), av, 1.0)), np.nan)
        elig = okc & np.isfinite(f)
        FWD[k] = f
        SIG_RAW[k] = np.where(elig, lcov, np.nan)
        SIG_RATIO[k] = np.where(elig, lcov - ladv, np.nan)
        SIG_RESID[k] = _xs_residual(np.where(elig, lcov, np.nan),
                                    np.where(elig, ladv, np.nan))
        SZ[k] = np.where(elig, ladv, np.nan)
        m = np.where(np.isfinite(MOM[t]) & ~MOMD[t], MOM[t], np.nan)
        MM[k] = np.where(elig, m, np.nan)
        OPEN[k] = elig & np.isfinite(SIG_RESID[k])

    dates = C.index[dates_i]
    bench = close[BENCH]
    bfwd = np.array([bench.iloc[t + horizon] / bench.iloc[t] - 1.0
                     if np.isfinite(bench.iloc[t]) and np.isfinite(bench.iloc[t + horizon])
                     else np.nan for t in dates_i])

    return {"dates": dates, "cols": syms, "FWD": FWD, "OPEN": OPEN,
            "RAW": SIG_RAW, "RATIO": SIG_RATIO, "RESID": SIG_RESID,
            "SIZE": SZ, "MOM": MM, "BENCH": bfwd, "horizon": horizon,
            "step": step, "guard_log": guard_log,
            "dropped_dirty_paths": dropped_dirty,
            "lag": max(int(math.ceil(horizon / step)) - 1, 0)}


# ------------------------------------------------------------------ estimators

def nw_se(x: np.ndarray, lag: int) -> float:
    """Newey-West SE of the mean of an OVERLAPPING series.

    The lag is a PARAMETER and every caller passes the one its own design
    implies (`panel['lag'] = ceil(horizon/step) - 1`).  A hard-coded lag 1 in a
    daily-formation study is the exact defect that killed H29: with step=1 and
    h=42 the correct lag is 41 and lag 1 inflates every t by roughly 3x."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    lag = min(int(lag), max(n - 2, 1))
    e = x - x.mean()
    s = float(e @ e) / n
    for l in range(1, lag + 1):
        s += 2.0 * (1 - l / (lag + 1)) * float(e[l:] @ e[:-l]) / n
    return math.sqrt(max(s, 1e-18) / n)


def block_boot_t(x: np.ndarray, block: int, reps: int = BOOT_REPS,
                 seeds=BOOT_SEEDS) -> dict:
    """Moving-block bootstrap of the mean, run under several seeds.

    Rule 16: report the Monte-Carlo sd of the bootstrap t, not just the t."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3 * block:
        return {}
    ts, los, his = [], [], []
    for sd in seeds:
        rng = np.random.default_rng(sd)
        nb = int(np.ceil(n / block))
        starts = rng.integers(0, n - block + 1, size=(reps, nb))
        idx = (starts[:, :, None] + np.arange(block)[None, None, :]
               ).reshape(reps, -1)[:, :n]
        means = x[idx].mean(axis=1)
        se = float(means.std(ddof=1))
        ts.append(float(x.mean()) / se if se > 0 else float("nan"))
        los.append(float(np.percentile(means, 2.5)))
        his.append(float(np.percentile(means, 97.5)))
    return {"boot_t": round(float(np.mean(ts)), 2),
            "boot_t_mc_sd": round(float(np.std(ts, ddof=1)), 3),
            "ci_lo_bps": round(1e4 * float(np.mean(los)), 1),
            "ci_hi_bps": round(1e4 * float(np.mean(his)), 1)}


def thirds(x: np.ndarray) -> list[float]:
    """RESEARCH-AGENDA rule 4: the equal-thirds era split that killed H22."""
    v = np.asarray(x, float)
    n = len(v)
    out = []
    for k in range(3):
        seg = v[k * n // 3:(k + 1) * n // 3]
        seg = seg[np.isfinite(seg)]
        out.append(round(1e4 * float(seg.mean()), 1) if len(seg) else float("nan"))
    return out


def stats(x: np.ndarray, lag: int, block: int | None = None,
          boot: bool = True) -> dict:
    v = np.asarray(x, float)
    fin = v[np.isfinite(v)]
    if len(fin) < 5:
        return {"n": int(len(fin)), "mean_bps": None}
    se = nw_se(fin, lag)
    half = len(fin) // 2
    out = {"n": int(len(fin)),
           "mean_bps": round(1e4 * float(fin.mean()), 1),
           "sd_bps": round(1e4 * float(fin.std(ddof=1)), 1),
           "nw_t": round(float(fin.mean()) / se, 2) if se > 0 else None,
           "h1_bps": round(1e4 * float(fin[:half].mean()), 1),
           "h2_bps": round(1e4 * float(fin[half:].mean()), 1),
           "thirds_bps": thirds(v),
           "pos_frac": round(float((fin > 0).mean()), 3)}
    if boot:
        out.update(block_boot_t(v, block or (lag + 1)))
    return out


def beta_alpha(x: np.ndarray, bench: np.ndarray, lag: int) -> tuple[dict, np.ndarray]:
    """Rule 13, applied to LEVELS *and* DIFFERENCES.

    H29's kill was that its lab market-adjusted every leg and never the spread;
    a difference of two beta-laden sorts is itself beta-laden.  Everything in
    this file that quotes a spread runs the spread series through here."""
    ok = np.isfinite(x) & np.isfinite(bench)
    if ok.sum() < 20:
        return {}, np.full(len(x), np.nan)
    X = np.column_stack([np.ones(ok.sum()), bench[ok]])
    b, *_ = np.linalg.lstsq(X, x[ok], rcond=None)
    resid = x[ok] - X @ b
    se = nw_se(resid, lag) * math.sqrt(len(resid) / max(len(resid) - 2, 1))
    adj = np.full(len(x), np.nan)
    adj[ok] = b[0] + resid
    a = adj[ok]
    half = len(a) // 2
    return ({"alpha_bps": round(1e4 * float(b[0]), 1),
             "beta": round(float(b[1]), 3),
             "alpha_t": round(float(b[0]) / se, 2) if se > 0 else None,
             "alpha_h1_bps": round(1e4 * float(a[:half].mean()), 1),
             "alpha_h2_bps": round(1e4 * float(a[half:].mean()), 1),
             "alpha_thirds_bps": thirds(adj)}, adj)


# --------------------------------------------------------------- bucket engine

def _weights(kind: str, size_log: np.ndarray) -> np.ndarray:
    if kind == "ew":
        return np.ones(len(size_log))
    w = np.exp(size_log)                      # back to dollars from log ADV
    w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
    return w


def bucket_series(panel: dict, col: str, nq: int, weight: str = "ew",
                  sub: np.ndarray | None = None) -> dict:
    """Per-formation-date bucket means, low->high on `col`, plus the pool mean.

    `sub` optionally restricts the eligible pool (used for within-size-tercile
    and interaction runs).  Weight 'ew' = equal, 'dv' = dollar-volume (the
    cap-weight proxy; see the module docstring for why cap itself is unsafe on
    this cache)."""
    n_d = len(panel["dates"])
    B = np.full((n_d, nq), np.nan)
    pool = np.full(n_d, np.nan)
    size = np.zeros(n_d, int)
    members = [[None] * nq for _ in range(n_d)]
    for i in range(n_d):
        m = panel["OPEN"][i] if sub is None else (panel["OPEN"][i] & sub[i])
        if m.sum() < max(MIN_POOL, nq * 3):
            continue
        s = panel[col][i][m]
        f = panel["FWD"][i][m]
        w = _weights(weight, panel["SIZE"][i][m])
        idx = np.where(m)[0]
        order = np.argsort(s, kind="stable")
        n = len(order)
        edges = (np.arange(nq + 1) * n) // nq
        for k in range(nq):
            sel = order[edges[k]:edges[k + 1]]
            ww = w[sel]
            B[i, k] = (f[sel] @ ww / ww.sum()) if ww.sum() > 0 else np.nan
            members[i][k] = idx[sel]
        wp = w
        pool[i] = f @ wp / wp.sum() if wp.sum() > 0 else np.nan
        size[i] = n
    # sign convention: NEGLECT = LOW coverage, so spread = LOW - HIGH
    return {"buckets": B, "spread": B[:, 0] - B[:, -1], "pool": pool,
            "size": size, "nq": nq, "members": members}


def turnover(bs: dict, k: int, horizon: int, step: int) -> float:
    """Fraction of bucket k's names that change between rebalances `horizon`
    sessions apart (the natural frequency for a `horizon`-session hold)."""
    lagn = max(int(round(horizon / step)), 1)
    vals = []
    for i in range(lagn, len(bs["members"])):
        a, b = bs["members"][i][k], bs["members"][i - lagn][k]
        if a is None or b is None or len(a) == 0:
            continue
        vals.append(1.0 - len(np.intersect1d(a, b)) / len(a))
    return float(np.mean(vals)) if vals else float("nan")


# ------------------------------------------------------------------- controls

def null_random_bucket(panel: dict, nq: int, draws: int = DRAWS,
                       seed: int = SEED) -> dict:
    """Control 1: random assignment to buckets from the IDENTICAL eligible pool
    on the identical dates.  Answers 'is any spread of this size free?'"""
    rng = np.random.default_rng(seed)
    n_d = len(panel["dates"])
    means = np.empty(draws)
    for d in range(draws):
        sp = np.full(n_d, np.nan)
        for i in range(n_d):
            m = panel["OPEN"][i]
            if m.sum() < max(MIN_POOL, nq * 3):
                continue
            f = rng.permutation(panel["FWD"][i][m])
            e = (np.arange(nq + 1) * len(f)) // nq
            sp[i] = f[:e[1]].mean() - f[e[nq - 1]:].mean()
        means[d] = np.nanmean(sp)
    return {"draws": draws, "mean_bps": round(1e4 * float(means.mean()), 2),
            "sd_bps": round(1e4 * float(means.std(ddof=1)), 2),
            "lo_bps": round(1e4 * float(np.percentile(means, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(means, 97.5)), 1)}


def null_shuffle_signal(panel: dict, col: str, nq: int, draws: int = DRAWS,
                        seed: int = SEED) -> dict:
    """Control 2: permute the coverage vector ACROSS symbols within each date.
    Keeps the marginal distribution of the signal, destroys the pairing."""
    rng = np.random.default_rng(seed + 1)
    n_d = len(panel["dates"])
    means = np.empty(draws)
    for d in range(draws):
        sp = np.full(n_d, np.nan)
        for i in range(n_d):
            m = panel["OPEN"][i]
            if m.sum() < max(MIN_POOL, nq * 3):
                continue
            s = rng.permutation(panel[col][i][m])
            f = panel["FWD"][i][m]
            order = np.argsort(s, kind="stable")
            e = (np.arange(nq + 1) * len(order)) // nq
            sp[i] = f[order[:e[1]]].mean() - f[order[e[nq - 1]:]].mean()
        means[d] = np.nanmean(sp)
    return {"draws": draws, "mean_bps": round(1e4 * float(means.mean()), 2),
            "sd_bps": round(1e4 * float(means.std(ddof=1)), 2),
            "lo_bps": round(1e4 * float(np.percentile(means, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(means, 97.5)), 1)}


def null_stale_signal(panel: dict, col: str, nq: int, draws: int = DRAWS,
                      seed: int = SEED) -> dict:
    """Control 3 (H15's killer, run here as a CONSISTENCY check, not a kill).

    Score each date with a coverage snapshot at least STALE sessions in the
    PAST -- never the future, which is the Rule 15 leak H25 had to fix.  For a
    persistent CHARACTERISTIC the stale snapshot SHOULD reproduce the spread;
    that is the premise, not a refutation.  What would be damning is the
    reverse: the stale snapshot reproducing it while the live one adds nothing
    beyond a size sort -- so this is read alongside the size-neutral rows."""
    rng = np.random.default_rng(seed + 2)
    n_d = len(panel["dates"])
    stale_steps = max(int(round(STALE / max(panel["step"], 1))), 1)
    means = np.empty(draws)
    for d in range(draws):
        sp = np.full(n_d, np.nan)
        for i in range(n_d):
            if i < stale_steps:
                continue
            j = int(rng.integers(0, i - stale_steps + 1))
            m = panel["OPEN"][i] & np.isfinite(panel[col][j])
            if m.sum() < max(MIN_POOL, nq * 3):
                continue
            s = panel[col][j][m]
            f = panel["FWD"][i][m]
            order = np.argsort(s, kind="stable")
            e = (np.arange(nq + 1) * len(order)) // nq
            sp[i] = f[order[:e[1]]].mean() - f[order[e[nq - 1]:]].mean()
        means[d] = np.nanmean(sp)
    return {"draws": draws, "mean_bps": round(1e4 * float(means.mean()), 2),
            "sd_bps": round(1e4 * float(means.std(ddof=1)), 2),
            "lo_bps": round(1e4 * float(np.percentile(means, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(means, 97.5)), 1)}


# ---------------------------------------------------------- neutralisation etc.

def tercile_masks(panel: dict, col: str, nq: int = 3) -> list[np.ndarray]:
    """Boolean masks selecting each tercile of `col` within the eligible pool."""
    n_d, n_s = panel["FWD"].shape
    out = [np.zeros((n_d, n_s), bool) for _ in range(nq)]
    for i in range(n_d):
        m = panel["OPEN"][i]
        if m.sum() < max(MIN_POOL, nq * 3):
            continue
        idx = np.where(m)[0]
        order = idx[np.argsort(panel[col][i][m], kind="stable")]
        e = (np.arange(nq + 1) * len(order)) // nq
        for k in range(nq):
            out[k][i, order[e[k]:e[k + 1]]] = True
    return out


def double_sort(panel: dict, ctrl: str, sig: str, nq: int = 3) -> np.ndarray:
    """nq x nq mean forward return, rows = ctrl terciles, cols = sig terciles."""
    n_d = len(panel["dates"])
    cells = np.full((n_d, nq, nq), np.nan)
    for i in range(n_d):
        m = panel["OPEN"][i]
        if m.sum() < max(MIN_POOL, nq * nq * 3):
            continue
        idx = np.where(m)[0]
        c_order = idx[np.argsort(panel[ctrl][i][m], kind="stable")]
        e = (np.arange(nq + 1) * len(c_order)) // nq
        for r in range(nq):
            grp = c_order[e[r]:e[r + 1]]
            if len(grp) < nq * 2:
                continue
            s_order = grp[np.argsort(panel[sig][i][grp], kind="stable")]
            e2 = (np.arange(nq + 1) * len(s_order)) // nq
            for c in range(nq):
                sel = s_order[e2[c]:e2[c + 1]]
                cells[i, r, c] = panel["FWD"][i][sel].mean()
    return cells


def fama_macbeth(panel: dict, cols: list[str]) -> dict:
    """Per-date cross-sectional OLS of FWD on rank-transformed regressors; the
    coefficient is the top-minus-bottom rank difference, in bps."""
    n_d = len(panel["dates"])
    coefs = np.full((n_d, len(cols) + 1), np.nan)
    for i in range(n_d):
        m = panel["OPEN"][i]
        if m.sum() < max(MIN_POOL, 20):
            continue
        y = panel["FWD"][i][m]
        Xs = [np.ones(m.sum())]
        ok = np.isfinite(y)
        for c in cols:
            r = _rank_pct(panel[c][i][m])
            Xs.append(r)
            ok &= np.isfinite(r)
        if ok.sum() < 20:
            continue
        X = np.column_stack(Xs)[ok]
        b, *_ = np.linalg.lstsq(X, y[ok], rcond=None)
        coefs[i, :] = b
    lag = panel["lag"]
    out = {}
    for j, c in enumerate(["const"] + cols):
        v = coefs[:, j]
        v = v[np.isfinite(v)]
        if len(v) < 5:
            continue
        se = nw_se(v, lag)
        out[c] = {"coef_bps": round(1e4 * float(v.mean()), 1),
                  "t": round(float(v.mean()) / se, 2) if se > 0 else None,
                  "n": int(len(v))}
    return out


def phase_sweep(x: np.ndarray, phases: int) -> list[dict]:
    """Rule 9.  With step=1 the primary series ALREADY pools every entry phase;
    this decomposes it into the `phases` non-overlapping calendars so a result
    that lives in one of them cannot hide."""
    out = []
    for p in range(phases):
        v = x[p::phases]
        v = v[np.isfinite(v)]
        if len(v) < 5:
            out.append({"phase": p, "n": int(len(v)), "mean_bps": None})
            continue
        se = nw_se(v, 0)          # this subset does not overlap
        out.append({"phase": p, "n": int(len(v)),
                    "mean_bps": round(1e4 * float(v.mean()), 1),
                    "t": round(float(v.mean()) / se, 2) if se > 0 else None})
    return out


# ---------------------------------------------------------------- diagnostics

def dispersion_report(panel: dict) -> dict:
    """Is there anything to sort?  The DATA_UNUSABLE gate, decided on numbers."""
    rows = []
    for i in range(0, len(panel["dates"]), 63):
        m = panel["OPEN"][i]
        if m.sum() < MIN_POOL:
            continue
        raw = np.expm1(panel["RAW"][i][m])
        res = panel["RESID"][i][m]
        p = np.percentile(raw, [10, 50, 90])
        rows.append({"p10": p[0], "p50": p[1], "p90": p[2],
                     "ratio": p[2] / max(p[0], 1e-9),
                     "resid_sd": float(np.std(res)),
                     "n": int(m.sum())})
    d = pd.DataFrame(rows)
    return {"dates_sampled": len(d),
            "median_p10": round(float(d["p10"].median()), 1),
            "median_p50": round(float(d["p50"].median()), 1),
            "median_p90": round(float(d["p90"].median()), 1),
            "median_p90_over_p10": round(float(d["ratio"].median()), 2),
            "median_resid_sd_logstories": round(float(d["resid_sd"].median()), 3),
            "median_pool": int(d["n"].median())}


def persistence(panel: dict, col: str) -> dict:
    """How static is the characteristic?  (H15 said very; check it here.)"""
    out = {}
    for lag_sessions in (21, 63, 252):
        L = max(int(round(lag_sessions / max(panel["step"], 1))), 1)
        a, b = [], []
        for i in range(L, len(panel["dates"]), max(21 // max(panel["step"], 1), 1)):
            m = panel["OPEN"][i] & panel["OPEN"][i - L]
            if m.sum() < MIN_POOL:
                continue
            a.append(_rank_pct(panel[col][i][m]))
            b.append(_rank_pct(panel[col][i - L][m]))
        if not a:
            continue
        a, b = np.concatenate(a), np.concatenate(b)
        ok = np.isfinite(a) & np.isfinite(b)
        out[f"rank_autocorr_{lag_sessions}td"] = round(
            float(np.corrcoef(a[ok], b[ok])[0, 1]), 3)
    return out


def bottom_bucket_composition(panel: dict, col: str, nq: int = 3,
                              top: int = 12) -> dict:
    """WHO is in the neglected bucket?  A neglect study on mega-caps has to
    show its bottom bucket is companies, not join failures."""
    bs = bucket_series(panel, col, nq)
    cnt = {}
    tot = 0
    for i in range(len(panel["dates"])):
        sel = bs["members"][i][0]
        if sel is None:
            continue
        for j in sel:
            cnt[panel["cols"][j]] = cnt.get(panel["cols"][j], 0) + 1
            tot += 1
    share = {k: round(v / max(tot, 1), 4)
             for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])[:top]}
    return {"name_dates": tot, "top_share": share}


# ----------------------------------------- the Hong-Lim-Stein interaction study

def momentum_spread(panel: dict, sub: np.ndarray, nq: int = 3,
                    fwd: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Per-date (winners - losers) inside `sub`, and that group's cross-sectional
    sd of the forward return on the same date.

    The sd is returned because a group with wider return dispersion produces a
    wider spread MECHANICALLY.  H21g's mandatory diagnostic, applied here: if
    the raw ordering appears and the dispersion-normalised ordering does not,
    the result is volatility scaling, not a mechanism."""
    F = panel["FWD"] if fwd is None else fwd
    n_d = len(panel["dates"])
    sp = np.full(n_d, np.nan)
    disp = np.full(n_d, np.nan)
    for i in range(n_d):
        m = panel["OPEN"][i] & sub[i] & np.isfinite(panel["MOM"][i]) & np.isfinite(F[i])
        if m.sum() < nq * 3:
            continue
        s, f = panel["MOM"][i][m], F[i][m]
        order = np.argsort(s, kind="stable")
        e = (np.arange(nq + 1) * len(order)) // nq
        sp[i] = f[order[e[nq - 1]:]].mean() - f[order[:e[1]]].mean()
        disp[i] = float(np.std(f, ddof=1))
    return sp, disp


def _terciles_from(sig: np.ndarray, open_: np.ndarray, nq: int = 3
                   ) -> list[np.ndarray]:
    n_d, n_s = sig.shape
    out = [np.zeros((n_d, n_s), bool) for _ in range(nq)]
    for i in range(n_d):
        m = open_[i] & np.isfinite(sig[i])
        if m.sum() < max(MIN_POOL, nq * 3):
            continue
        idx = np.where(m)[0]
        order = idx[np.argsort(sig[i][m], kind="stable")]
        e = (np.arange(nq + 1) * len(order)) // nq
        for k in range(nq):
            out[k][i, order[e[k]:e[k + 1]]] = True
    return out


def interaction_nulls(panel: dict, col: str, draws: int, seed: int = SEED,
                      persistent: bool = True) -> dict:
    """The control the interaction lives or dies by.

    `persistent=True` applies ONE symbol permutation across ALL dates, so each
    symbol keeps a real symbol's coverage TRAJECTORY -- the null therefore has
    the same persistence structure as the real characteristic (rank
    autocorrelation 0.91 at a year) and differs only in WHICH symbol it is
    attached to.  A per-date shuffle (persistent=False) destroys persistence
    too and is the weaker, more easily beaten null; both are reported."""
    rng = np.random.default_rng(seed + 7)
    n_s = panel["FWD"].shape[1]
    vals = np.empty(draws)
    for d in range(draws):
        if persistent:
            perm = rng.permutation(n_s)
            sig = panel[col][:, perm]
        else:
            sig = np.empty_like(panel[col])
            for i in range(sig.shape[0]):
                sig[i] = panel[col][i][rng.permutation(n_s)]
        tm = _terciles_from(sig, panel["OPEN"])
        lo, _ = momentum_spread(panel, tm[0])
        hi, _ = momentum_spread(panel, tm[2])
        vals[d] = np.nanmean(lo - hi)
    return {"draws": draws, "mean_bps": round(1e4 * float(vals.mean()), 1),
            "sd_bps": round(1e4 * float(vals.std(ddof=1)), 1),
            "lo_bps": round(1e4 * float(np.percentile(vals, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(vals, 97.5)), 1),
            "p975_bps": round(1e4 * float(np.percentile(vals, 97.5)), 1)}


def null_persistent_level(panel: dict, col: str, nq: int, draws: int,
                          seed: int = SEED, what: str = "spread") -> dict:
    """THE null this lab turns out to need, for the LEVEL sorts too.

    The random-bucket and per-date-shuffle controls destroy PERSISTENCE, so
    they measure the noise of a characteristic that is re-drawn every day --
    a much smaller number than the noise of a characteristic that is fixed for
    a decade.  Coverage IS fixed for a decade (rank autocorrelation 0.91 at a
    year), so the honest question is: how big a spread does a persistent but
    MEANINGLESS labelling of these 120 names produce?  One permutation of the
    symbol axis, applied at every date, answers it.  This is Rule 14 with the
    right null: the permutation SE here is far LARGER than the Newey-West SE,
    which makes the NW t anti-conservative rather than conservative.

    `what`: 'spread' = low-minus-high, 'low_vs_bench' = the long-only leg.
    """
    rng = np.random.default_rng(seed + 11)
    n_s = panel["FWD"].shape[1]
    vals = np.empty(draws)
    for d in range(draws):
        sig = panel[col][:, rng.permutation(n_s)]
        tm = _terciles_from(sig, panel["OPEN"], nq)
        b0 = np.full(len(panel["dates"]), np.nan)
        b1 = np.full(len(panel["dates"]), np.nan)
        for i in range(len(panel["dates"])):
            for arr, msk in ((b0, tm[0][i]), (b1, tm[nq - 1][i])):
                m = msk & np.isfinite(panel["FWD"][i])
                if m.sum() >= 3:
                    arr[i] = panel["FWD"][i][m].mean()
        vals[d] = (np.nanmean(b0 - b1) if what == "spread"
                   else np.nanmean(b0 - panel["BENCH"]))
    return {"draws": draws, "mean_bps": round(1e4 * float(vals.mean()), 1),
            "sd_bps": round(1e4 * float(vals.std(ddof=1)), 1),
            "lo_bps": round(1e4 * float(np.percentile(vals, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(vals, 97.5)), 1)}


def null_persistent_longonly(panel: dict, col: str, draws: int,
                             seed: int = SEED) -> dict:
    """Persistent-shuffle null for the tradeable form: momentum WINNERS inside
    the bottom-`col` tercile, minus SPY."""
    rng = np.random.default_rng(seed + 13)
    n_s = panel["FWD"].shape[1]
    vals = np.empty(draws)
    for d in range(draws):
        sig = panel[col][:, rng.permutation(n_s)]
        tm = _terciles_from(sig, panel["OPEN"])
        bs = bucket_series(panel, "MOM", 3, "ew", tm[0])
        vals[d] = np.nanmean(bs["buckets"][:, 2] - panel["BENCH"])
    return {"draws": draws, "mean_bps": round(1e4 * float(vals.mean()), 1),
            "sd_bps": round(1e4 * float(vals.std(ddof=1)), 1),
            "lo_bps": round(1e4 * float(np.percentile(vals, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(vals, 97.5)), 1)}


def sector_demeaned(panel: dict) -> np.ndarray:
    """FWD with each date's sector mean removed, so a sector tilt cannot carry
    a spread.  Sectors come from scout/universe.py (current GICS labels — a
    known, small point-in-time imperfection, stated rather than hidden)."""
    from . import universe
    sec = {u["symbol"]: u["sector"] for u in universe.load()}
    labels = np.array([sec.get(s, "?") for s in panel["cols"]])
    uniq = sorted(set(labels))
    out = panel["FWD"].copy()
    for i in range(out.shape[0]):
        m = panel["OPEN"][i] & np.isfinite(out[i])
        if m.sum() < MIN_POOL:
            continue
        for u in uniq:
            sel = m & (labels == u)
            if sel.sum() >= 3:
                out[i, sel] -= out[i, sel].mean()
            elif sel.sum() > 0:
                out[i, sel] = np.nan          # too thin to demean honestly
    return out


def interaction_study(panel: dict, draws: int = DRAWS) -> dict:
    """Everything the interaction has to survive."""
    lag, h, step = panel["lag"], panel["horizon"], panel["step"]
    bench = panel["BENCH"]
    res: dict = {}
    cm = tercile_masks(panel, "RESID", 3)
    names = ["LOW coverage", "mid coverage", "HIGH coverage"]

    legs, disp = {}, {}
    for k, nm in enumerate(names):
        sp, dp = momentum_spread(panel, cm[k])
        legs[nm], disp[nm] = sp, dp
    full = np.ones_like(panel["OPEN"])
    sp_all, _ = momentum_spread(panel, full)
    res["momentum_full_pool"] = {**stats(sp_all, lag, block=h, boot=False),
                                 **beta_alpha(sp_all, bench, lag)[0]}
    _reg("momentum spread, full 120-name pool (reference)")

    inter = legs["LOW coverage"] - legs["HIGH coverage"]
    res["interaction"] = stats(inter, lag, block=h, boot=True)
    res["interaction_beta_alpha"] = beta_alpha(inter, bench, lag)[0]

    # 1. dispersion normalisation (H21g's mandatory diagnostic)
    res["dispersion_by_tercile_bps"] = {
        nm: round(1e4 * float(np.nanmean(disp[nm])), 1) for nm in names}
    norm = {nm: legs[nm] / disp[nm] for nm in names}
    ni = norm["LOW coverage"] - norm["HIGH coverage"]
    st = stats(ni, lag, block=h, boot=False)
    res["interaction_dispersion_normalised"] = {
        "mean": None if st.get("mean_bps") is None else round(st["mean_bps"] / 1e4, 4),
        "nw_t": st.get("nw_t"), "h1": None if st.get("h1_bps") is None
        else round(st["h1_bps"] / 1e4, 4),
        "h2": None if st.get("h2_bps") is None else round(st["h2_bps"] / 1e4, 4),
        "thirds": [None if x is None or not np.isfinite(x) else round(x / 1e4, 4)
                   for x in (st.get("thirds_bps") or [])]}
    _reg("interaction, dispersion-normalised")

    # 2. nulls
    res["null_persistent_shuffle"] = interaction_nulls(panel, "RESID", draws, persistent=True)
    res["null_perdate_shuffle"] = interaction_nulls(panel, "RESID", max(draws // 4, 25),
                                                    persistent=False)
    _reg("control: interaction under a PERSISTENT symbol shuffle")
    _reg("control: interaction under a per-date signal shuffle")
    # Rule 14: permutation SE against the Newey-West SE
    nw = nw_se(inter[np.isfinite(inter)], lag)
    res["rule14_se_ratio"] = round(
        (res["null_persistent_shuffle"]["sd_bps"] / 1e4) / nw, 2) if nw > 0 else None

    # 3. sector demeaning
    fwd_sd = sector_demeaned(panel)
    sec_legs = {nm: momentum_spread(panel, cm[k], fwd=fwd_sd)[0]
                for k, nm in enumerate(names)}
    si = sec_legs["LOW coverage"] - sec_legs["HIGH coverage"]
    res["interaction_sector_neutral"] = stats(si, lag, block=h, boot=False)
    res["interaction_sector_neutral_beta_alpha"] = beta_alpha(si, bench, lag)[0]
    _reg("interaction, sector-demeaned returns")

    # 4. the same interaction cut on LIQUIDITY instead of coverage
    sm = tercile_masks(panel, "SIZE", 3)
    lo_s, _ = momentum_spread(panel, sm[0])
    hi_s, _ = momentum_spread(panel, sm[2])
    res["interaction_on_liquidity"] = stats(lo_s - hi_s, lag, block=h, boot=False)
    _reg("interaction cut on ADV instead of coverage (is it a size effect?)")

    # 5. the same interaction cut on the RAW count
    rm = tercile_masks(panel, "RAW", 3)
    lo_r, _ = momentum_spread(panel, rm[0])
    hi_r, _ = momentum_spread(panel, rm[2])
    res["interaction_on_raw_count"] = stats(lo_r - hi_r, lag, block=h, boot=False)
    res["interaction_on_raw_count_beta_alpha"] = beta_alpha(lo_r - hi_r, bench, lag)[0]
    _reg("interaction cut on the RAW story count")

    # 6. Rule 9 — entry-phase decomposition
    ph = phase_sweep(inter, h)
    ok = [p for p in ph if p["mean_bps"] is not None]
    res["phase_sweep"] = {"n": len(ok), "positive": sum(1 for p in ok if p["mean_bps"] > 0),
                          "min": min(p["mean_bps"] for p in ok),
                          "median": float(np.median([p["mean_bps"] for p in ok])),
                          "max": max(p["mean_bps"] for p in ok)}
    _reg("interaction, Rule 9 entry-phase decomposition")

    # 7. per-year
    yr = pd.Series(inter, index=panel["dates"])
    res["by_year_bps"] = {int(y): round(1e4 * float(v.mean()), 1)
                          for y, v in yr.groupby(yr.index.year) if np.isfinite(v.mean())}

    # 8. leave-one-symbol-out jackknife
    jk = {}
    for j, s in enumerate(panel["cols"]):
        keep = np.ones(panel["FWD"].shape[1], bool)
        keep[j] = False
        opn = panel["OPEN"] & keep[None, :]
        p2 = dict(panel, OPEN=opn)
        cm2 = tercile_masks(p2, "RESID", 3)
        a, _ = momentum_spread(p2, cm2[0])
        b, _ = momentum_spread(p2, cm2[2])
        jk[s] = 1e4 * float(np.nanmean(a - b))
    ser = pd.Series(jk).sort_values()
    res["jackknife"] = {"min_symbol": ser.index[0], "min_bps": round(float(ser.iloc[0]), 1),
                        "max_symbol": ser.index[-1], "max_bps": round(float(ser.iloc[-1]), 1),
                        "median_bps": round(float(ser.median()), 1)}
    _reg("interaction, leave-one-symbol-out jackknife")

    # 9. costs — the four legs of the interaction book
    bs_lo = bucket_series(panel, "MOM", 3, "ew", cm[0])
    bs_hi = bucket_series(panel, "MOM", 3, "ew", cm[2])
    to = sum(turnover(b, k, h, step) for b in (bs_lo, bs_hi) for k in (0, 2))
    m = res["interaction"].get("mean_bps")
    res["costs"] = {"total_leg_turnover": round(float(to), 3),
                    "net_bps_at_10": None if m is None else round(m - to * COST_BPS, 1),
                    "breakeven_cost_bps": None if (m is None or to <= 0)
                    else round(m / to, 2)}

    # 10. the LONG-ONLY tradeable form: low-coverage winners vs SPY
    lonly = bs_lo["buckets"][:, 2]
    res["long_only_low_cov_winners"] = {
        **stats(lonly - bench, lag, block=h, boot=False),
        **beta_alpha(lonly, bench, lag)[0]}
    _reg("long-only: winners inside the LOW-coverage tercile vs SPY")

    # 10b. and the persistent-shuffle null for that tradeable form
    res["null_persistent_longonly"] = null_persistent_longonly(panel, "RESID", draws)
    _reg("control: long-only form under a PERSISTENT symbol shuffle")

    # 10c. z-scores against the RIGHT null, side by side with the NW t
    n1 = res["null_persistent_shuffle"]
    def _z(x, nul):
        return (None if x is None else
                round((x - nul["mean_bps"]) / max(nul["sd_bps"], 1e-9), 2))
    res["z_against_persistent_null"] = {
        "interaction": _z(res["interaction"].get("mean_bps"), n1),
        "interaction_sector_neutral": _z(
            res["interaction_sector_neutral"].get("mean_bps"), n1),
        "long_only": _z(res["long_only_low_cov_winners"].get("mean_bps"),
                        res["null_persistent_longonly"])}

    # 11. deflated Sharpe of the interaction book at the repo's running N
    from . import growth
    r = inter[np.isfinite(inter)]
    per_year = 252 / h
    sr_ann = growth.sharpe(r / 1.0, periods_per_year=per_year)
    res["sharpe_ann"] = round(float(sr_ann), 3)
    res["deflated_sharpe"] = round(float(growth.deflated_sharpe(
        sr_ann / math.sqrt(per_year), n_trials=RUNNING_N, n_obs=len(r) / h,
        skew=float(pd.Series(r).skew()), kurtosis=float(pd.Series(r).kurt() + 3.0))), 3)
    return res, legs


RUNNING_N = 740      # repo trial count past Round 4 (~700) plus this lab's variants


# ----------------------------------------------------------------- one variant

def run_sort(panel: dict, col: str, nq: int, weight: str, label: str,
             sub: np.ndarray | None = None, boot: bool = True) -> dict:
    """A full Rule-13-compliant readout of one sort.  Legs AND the difference."""
    _reg(label)
    lag, step, h = panel["lag"], panel["step"], panel["horizon"]
    bs = bucket_series(panel, col, nq, weight, sub)
    bench = panel["BENCH"]
    out = {"label": label, "col": col, "nq": nq, "weight": weight,
           "median_pool": int(np.median(bs["size"][bs["size"] > 0]))
           if (bs["size"] > 0).any() else 0}
    legs = {}
    for k in range(nq):
        s = stats(bs["buckets"][:, k], lag, block=max(h // max(step, 1), 1), boot=False)
        ba, _ = beta_alpha(bs["buckets"][:, k], bench, lag)
        legs[f"q{k+1}"] = {**s, **ba}
    out["legs"] = legs
    out["pool"] = {**stats(bs["pool"], lag, block=max(h // max(step, 1), 1), boot=False),
                   **beta_alpha(bs["pool"], bench, lag)[0]}
    out["bench"] = stats(bench, lag, block=max(h // max(step, 1), 1), boot=False)
    sp = bs["spread"]
    out["spread"] = stats(sp, lag, block=max(h // max(step, 1), 1), boot=boot)
    ba, adj = beta_alpha(sp, bench, lag)
    out["spread_beta_alpha"] = ba
    # the long-only tradeable form: neglected leg minus the benchmark
    lo_minus_spy = bs["buckets"][:, 0] - bench
    out["low_minus_spy"] = {**stats(lo_minus_spy, lag,
                                    block=max(h // max(step, 1), 1), boot=False),
                            **beta_alpha(bs["buckets"][:, 0], bench, lag)[0]}
    # the pool-matched control: neglected leg minus the equal-weight pool
    out["low_minus_pool"] = stats(bs["buckets"][:, 0] - bs["pool"], lag,
                                  block=max(h // max(step, 1), 1), boot=False)
    to_lo = turnover(bs, 0, h, step)
    to_hi = turnover(bs, nq - 1, h, step)
    out["turnover"] = {"low_leg": round(to_lo, 3), "high_leg": round(to_hi, 3)}
    m = out["spread"]["mean_bps"]
    if m is not None and np.isfinite(to_lo + to_hi) and (to_lo + to_hi) > 0:
        out["net_bps"] = round(m - (to_lo + to_hi) * COST_BPS, 1)
        out["breakeven_cost_bps"] = round(m / (to_lo + to_hi), 2)
    return out, bs, adj


# ------------------------------------------------------------------- reporting

def _f(v, w=9, p=1):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return f"{'-':>{w}}"
    return f"{v:>{w}.{p}f}" if isinstance(v, float) else f"{v:>{w}}"


def print_sort(r: dict) -> None:
    print(f"\n  {r['label']}   [{r['col']}, {r['nq']} buckets, {r['weight']} weight, "
          f"median pool {r['median_pool']}]")
    print(f"    {'bucket':<10}{'raw bps':>9}{'beta':>8}{'alpha bps':>11}{'a_t':>7}"
          f"{'a_h1':>9}{'a_h2':>9}{'a_thirds':>26}")
    for k in range(r["nq"]):
        L = r["legs"][f"q{k+1}"]
        tag = "q1 LOW cov" if k == 0 else (f"q{r['nq']} HIGH cov" if k == r["nq"] - 1
                                           else f"q{k+1}")
        th = L.get("alpha_thirds_bps") or [None] * 3
        print(f"    {tag:<10}{_f(L.get('mean_bps'))}{_f(L.get('beta'),8,2)}"
              f"{_f(L.get('alpha_bps'),11)}{_f(L.get('alpha_t'),7,2)}"
              f"{_f(L.get('alpha_h1_bps'),9)}{_f(L.get('alpha_h2_bps'),9)}"
              f"   {str([x for x in th]):>22}")
    p, b = r["pool"], r["bench"]
    print(f"    {'POOL ew':<10}{_f(p.get('mean_bps'))}{_f(p.get('beta'),8,2)}"
          f"{_f(p.get('alpha_bps'),11)}{_f(p.get('alpha_t'),7,2)}")
    print(f"    {'SPY':<10}{_f(b.get('mean_bps'))}")
    s, ba = r["spread"], r["spread_beta_alpha"]
    print(f"    SPREAD (LOW-HIGH, positive = neglect premium):")
    print(f"      raw   {_f(s.get('mean_bps'))} bps  NW t {_f(s.get('nw_t'),6,2)}"
          f"  boot t {_f(s.get('boot_t'),6,2)} (MC sd {s.get('boot_t_mc_sd')})"
          f"  CI [{_f(s.get('ci_lo_bps'),1)}, {_f(s.get('ci_hi_bps'),1)}]")
    print(f"      halves {_f(s.get('h1_bps'),8)} / {_f(s.get('h2_bps'),8)}"
          f"    thirds {s.get('thirds_bps')}   pos {s.get('pos_frac')}  n={s.get('n')}")
    print(f"      RULE 13 on the DIFFERENCE: beta {_f(ba.get('beta'),6,3)}"
          f"  alpha {_f(ba.get('alpha_bps'),8)} bps  t {_f(ba.get('alpha_t'),6,2)}"
          f"  halves {_f(ba.get('alpha_h1_bps'),7)}/{_f(ba.get('alpha_h2_bps'),7)}"
          f"  thirds {ba.get('alpha_thirds_bps')}")
    lms = r["low_minus_spy"]
    print(f"      LOW leg vs SPY: raw {_f(lms.get('mean_bps'),8)} bps"
          f"  beta {_f(lms.get('beta'),6,2)}  alpha {_f(lms.get('alpha_bps'),8)}"
          f"  t {_f(lms.get('alpha_t'),6,2)}")
    lmp = r["low_minus_pool"]
    print(f"      LOW leg vs the equal-weight POOL (matched control):"
          f" {_f(lmp.get('mean_bps'),8)} bps  t {_f(lmp.get('nw_t'),6,2)}")
    if "breakeven_cost_bps" in r:
        print(f"      turnover {r['turnover']}  net@{COST_BPS:.0f}bps "
              f"{r['net_bps']} bps  BREAK-EVEN {r['breakeven_cost_bps']} bps")


def hdr(s: str) -> None:
    print("\n" + "=" * 78)
    print(s)
    print("=" * 78)


# ------------------------------------------------------------------- the study

def run(refresh: bool = False, draws: int = DRAWS) -> dict:
    t0 = time.time()
    res: dict = {"config": {"H": H, "LOOKBACK": LOOKBACK, "COST_BPS": COST_BPS,
                            "universe": "point-in-time liquid-120 S&P 500 as of "
                                        "2016-01-04 (scout/news_data.py panel)"}}
    raw = load_raw(refresh)

    hdr("H33 — coverage LEVEL as a neglect premium.  Universe: 120 mega-caps.")
    print("SIGN CONVENTION: every spread is LOW coverage minus HIGH coverage,")
    print("so POSITIVE supports the hypothesis.  Neglect = low coverage.")
    print("SHIFT: signal = trailing 252-session story count ending at t-1;")
    print("       return = close(t) -> close(t+42).  Nothing reads a future bar.")

    panel = build_panel(raw, guard=True)
    res["guards"] = panel["guard_log"]
    res["dropped_dirty_paths"] = panel["dropped_dirty_paths"]
    print(f"\n  formations: {len(panel['dates'])} (daily, step=1 -> ALL {H} entry "
          f"phases pooled by construction; NW lag {panel['lag']})")
    print(f"  {panel['dates'][0].date()} .. {panel['dates'][-1].date()}")
    print(f"  G1 dropped {panel['dropped_dirty_paths']:,} symbol-formations whose "
          f"42-session path contained a >|45%| one-day move")

    hdr("0. IS THERE ANYTHING TO SORT?  (the DATA_UNUSABLE gate)")
    disp = dispersion_report(panel)
    res["dispersion"] = disp
    print(f"  trailing-252 non-templated story count, median across dates:")
    print(f"    p10 {disp['median_p10']}   p50 {disp['median_p50']}   "
          f"p90 {disp['median_p90']}   p90/p10 = {disp['median_p90_over_p10']}x")
    print(f"  liquidity-residual sd: {disp['median_resid_sd_logstories']} log-stories")
    print(f"  median eligible pool: {disp['median_pool']} names")
    pers = persistence(panel, "RAW")
    res["persistence"] = pers
    print(f"  persistence of the characteristic (rank autocorrelation): {pers}")
    comp = bottom_bucket_composition(panel, "RESID")
    res["bottom_bucket"] = comp
    print(f"  most frequent occupants of the NEGLECTED (liquidity-residual) "
          f"tercile:\n    {comp['top_share']}")

    hdr("1. THE RAW COUNT SORT (mostly a size sort — reported as its own thing)")
    r_raw3, bs_raw3, _ = run_sort(panel, "RAW", 3, "ew", "raw-count terciles EW")
    print_sort(r_raw3)
    r_raw5, _, _ = run_sort(panel, "RAW", 5, "ew", "raw-count quintiles EW")
    print_sort(r_raw5)
    r_raw3d, _, _ = run_sort(panel, "RAW", 3, "dv", "raw-count terciles DV-weight")
    print_sort(r_raw3d)
    res["raw"] = {"t3_ew": r_raw3, "q5_ew": r_raw5, "t3_dv": r_raw3d}

    hdr("2. THE SIZE-NORMALISED SORTS (the actual neglect hypothesis)")
    print("  RATIO  = log1p(stories) - log(ADV$)   ;  mechanical, over-corrects")
    print("  RESID  = cross-sectional OLS residual of log1p(stories) on log ADV$")
    print("           -> orthogonal to liquidity BY CONSTRUCTION.  This is primary.")
    out = {}
    for col in ("RATIO", "RESID"):
        for nq in (3, 5):
            for w in ("ew", "dv"):
                r, _, _ = run_sort(panel, col, nq, w,
                                   f"{col} {nq}-bucket {w}",
                                   boot=(nq == 3 and w == "ew"))
                print_sort(r)
                out[f"{col}_{nq}_{w}"] = r
    res["normalised"] = out
    primary = out["RESID_3_ew"]
    res["primary"] = primary["label"]

    hdr("3. CONTROLS")
    c1 = null_random_bucket(panel, 3, draws)
    _reg("control: random bucket assignment")
    print(f"  random-bucket from the identical pool ({draws} draws): "
          f"{c1['mean_bps']} bps  sd {c1['sd_bps']}  95% [{c1['lo_bps']}, {c1['hi_bps']}]")
    c2 = null_shuffle_signal(panel, "RESID", 3, draws)
    _reg("control: signal shuffled across symbols")
    print(f"  signal shuffled across symbols within date:                 "
          f"{c2['mean_bps']} bps  sd {c2['sd_bps']}  95% [{c2['lo_bps']}, {c2['hi_bps']}]")
    c3 = null_stale_signal(panel, "RESID", 3, min(draws, 60))
    _reg("control: >=1yr stale coverage snapshot (H15's date shuffle)")
    # Rule 17: the stale control can only score dates that HAVE a >=1yr-old
    # donor, so the live spread is re-measured on exactly that subset before
    # the two are compared.
    stale_steps = max(int(round(STALE / max(panel["step"], 1))), 1)
    _, bs_live, _ = run_sort(panel, "RESID", 3, "ew", "RESID 3-bucket ew", boot=False)
    live_sub = float(np.nanmean(bs_live["spread"][stale_steps:])) * 1e4
    print(f"  >= 1-year-STALE coverage snapshot (H15's control):          "
          f"{c3['mean_bps']} bps  sd {c3['sd_bps']}  95% [{c3['lo_bps']}, {c3['hi_bps']}]")
    print(f"  the LIVE signal on the same date subset (Rule 17, same machinery): "
          f"{live_sub:.1f} bps")
    print("  (a stale snapshot REPRODUCING the spread is this hypothesis's premise,")
    print("   not its refutation — the claim is about a static characteristic.")
    print("   Both are small and both sit inside the sampling noise of a null sort.)")
    c4 = null_persistent_level(panel, "RESID", 3, draws)
    _reg("control: PERSISTENT symbol shuffle of the level sort")
    c5 = null_persistent_level(panel, "RESID", 3, draws, what="low_vs_bench")
    _reg("control: PERSISTENT symbol shuffle, LOW leg vs SPY")
    print(f"\n  PERSISTENT symbol shuffle (one permutation held at every date, so the")
    print(f"  fake characteristic is as sticky as the real one — rank autocorr 0.91):")
    print(f"    low-minus-high spread: {c4['mean_bps']} bps  sd {c4['sd_bps']}"
          f"  95% [{c4['lo_bps']}, {c4['hi_bps']}]")
    print(f"    LOW leg minus SPY:     {c5['mean_bps']} bps  sd {c5['sd_bps']}"
          f"  95% [{c5['lo_bps']}, {c5['hi_bps']}]")
    prim_sp = primary["spread"]["mean_bps"]
    prim_lo = primary["low_minus_spy"]["mean_bps"]
    zs = round((prim_sp - c4["mean_bps"]) / max(c4["sd_bps"], 1e-9), 2)
    zl = round((prim_lo - c5["mean_bps"]) / max(c5["sd_bps"], 1e-9), 2)
    print(f"  *** the primary spread {prim_sp} bps -> z = {zs} against this null"
          f"  (its NW t was {primary['spread']['nw_t']})")
    print(f"      the LOW leg vs SPY {prim_lo} bps -> z = {zl}")
    print(f"  POWER, stated honestly: at 2 sd this design could only have detected an")
    print(f"  effect of about {2 * c4['sd_bps']:.0f} bps per 42-session window "
          f"({2 * c4['sd_bps'] * 252 / H / 100:.1f}%/yr).  Anything smaller than that")
    print(f"  is invisible here, so this null is a bound, not a refutation.")
    res["controls"] = {"random_bucket": c1, "shuffled_signal": c2, "stale_signal": c3,
                       "live_on_stale_subset_bps": round(live_sub, 1),
                       "persistent_shuffle_spread": c4,
                       "persistent_shuffle_low_vs_spy": c5,
                       "z_spread_vs_persistent_null": zs,
                       "z_low_leg_vs_persistent_null": zl,
                       "min_detectable_bps_at_2sd": round(2 * c4["sd_bps"], 1)}

    hdr("4. SIZE / LIQUIDITY NEUTRALISATION — 'is neglect just small-cap?'")
    smasks = tercile_masks(panel, "SIZE", 3)
    within = {}
    for k, nm in enumerate(["small ADV", "mid ADV", "large ADV"]):
        r, _, _ = run_sort(panel, "RESID", 3, "ew",
                           f"RESID terciles within {nm}", sub=smasks[k], boot=False)
        s, ba = r["spread"], r["spread_beta_alpha"]
        print(f"  {nm:<10} spread {_f(s.get('mean_bps'),8)} bps  NW t "
              f"{_f(s.get('nw_t'),6,2)}   beta {_f(ba.get('beta'),6,3)}  alpha "
              f"{_f(ba.get('alpha_bps'),8)}  t {_f(ba.get('alpha_t'),6,2)}"
              f"   halves {_f(s.get('h1_bps'),7)}/{_f(s.get('h2_bps'),7)}")
        within[nm] = r
    res["within_size"] = within
    # also the raw-count sort inside size terciles, to show what it is made of
    within_raw = {}
    for k, nm in enumerate(["small ADV", "mid ADV", "large ADV"]):
        r, _, _ = run_sort(panel, "RAW", 3, "ew",
                           f"RAW terciles within {nm}", sub=smasks[k], boot=False)
        s = r["spread"]
        print(f"  [raw count] {nm:<10} spread {_f(s.get('mean_bps'),8)} bps  "
              f"NW t {_f(s.get('nw_t'),6,2)}  alpha "
              f"{_f(r['spread_beta_alpha'].get('alpha_bps'),8)}")
        within_raw[nm] = r
    res["within_size_raw"] = within_raw

    ds = double_sort(panel, "SIZE", "RESID", 3)
    lag = panel["lag"]
    cells = np.nanmean(ds, axis=0) * 1e4
    print("\n  double sort, rows = ADV tercile, cols = coverage-residual tercile "
          "(bps/window):")
    print(f"    {'':<12}{'lowCov':>10}{'midCov':>10}{'highCov':>10}{'low-high':>11}"
          f"{'t':>7}")
    dbl = {}
    for r_i, nm in enumerate(["small ADV", "mid ADV", "large ADV"]):
        diff = ds[:, r_i, 0] - ds[:, r_i, 2]
        st = stats(diff, lag, block=H, boot=False)
        print(f"    {nm:<12}{cells[r_i,0]:>10.1f}{cells[r_i,1]:>10.1f}"
              f"{cells[r_i,2]:>10.1f}{_f(st.get('mean_bps'),11)}"
              f"{_f(st.get('nw_t'),7,2)}")
        dbl[nm] = st
    pooled = np.nanmean(np.stack([ds[:, i, 0] - ds[:, i, 2] for i in range(3)]), axis=0)
    stp = stats(pooled, lag, block=H, boot=True)
    bap, _ = beta_alpha(pooled, panel["BENCH"], lag)
    _reg("size-neutral double-sorted spread (average of within-ADV-tercile spreads)")
    print(f"    {'POOLED (size-neutral)':<12} spread {_f(stp.get('mean_bps'),8)} bps"
          f"  NW t {_f(stp.get('nw_t'),6,2)}  boot t {_f(stp.get('boot_t'),6,2)}"
          f" (MC sd {stp.get('boot_t_mc_sd')})")
    print(f"      halves {_f(stp.get('h1_bps'),7)}/{_f(stp.get('h2_bps'),7)}"
          f"   thirds {stp.get('thirds_bps')}")
    print(f"      RULE 13 on the DIFFERENCE: beta {_f(bap.get('beta'),6,3)}"
          f"  alpha {_f(bap.get('alpha_bps'),8)}  t {_f(bap.get('alpha_t'),6,2)}"
          f"  thirds {bap.get('alpha_thirds_bps')}")
    res["double_sort"] = {"cells_bps": cells.round(1).tolist(), "by_row": dbl,
                          "pooled": stp, "pooled_beta_alpha": bap}

    hdr("5. FAMA-MACBETH (top-minus-bottom rank differences, bps/window)")
    fm = {}
    for cols in (["RAW"], ["RESID"], ["RAW", "SIZE"], ["RESID", "MOM"],
                 ["RAW", "SIZE", "MOM"]):
        k = "+".join(cols)
        fm[k] = fama_macbeth(panel, cols)
        _reg(f"Fama-MacBeth {k}")
        line = "  ".join(f"{c}: {fm[k][c]['coef_bps']:>8.1f} (t {fm[k][c]['t']:>5.2f})"
                         for c in cols if c in fm[k])
        print(f"  {k:<20} {line}")
    res["fama_macbeth"] = fm

    hdr("6. THE HONG-LIM-STEIN INTERACTION — is momentum stronger where "
        "coverage is LOW?")
    print("  (this is the mechanism test: news travels slowest among neglected")
    print("   names, so under-reaction and therefore momentum should be largest")
    print("   in the low-coverage tercile.)")
    cmasks = tercile_masks(panel, "RESID", 3)
    inter = {}
    for k, nm in enumerate(["LOW coverage", "mid coverage", "HIGH coverage"]):
        bs = bucket_series(panel, "MOM", 3, "ew", cmasks[k])
        # MOM sort: bucket 0 = losers, bucket 2 = winners; momentum = win - lose
        momsp = bs["buckets"][:, 2] - bs["buckets"][:, 0]
        st = stats(momsp, lag, block=H, boot=False)
        ba, _ = beta_alpha(momsp, panel["BENCH"], lag)
        _reg(f"momentum spread within {nm} tercile")
        print(f"  {nm:<15} momentum(win-lose) {_f(st.get('mean_bps'),8)} bps"
              f"  NW t {_f(st.get('nw_t'),6,2)}   beta {_f(ba.get('beta'),6,3)}"
              f"  alpha {_f(ba.get('alpha_bps'),8)}  t {_f(ba.get('alpha_t'),6,2)}")
        print(f"  {'':<15}   halves {_f(st.get('h1_bps'),7)}/{_f(st.get('h2_bps'),7)}"
              f"   thirds {st.get('thirds_bps')}")
        inter[nm] = {"raw": st, "beta_alpha": ba, "series": momsp}
    diff = inter["LOW coverage"]["series"] - inter["HIGH coverage"]["series"]
    stq = stats(diff, lag, block=H, boot=True)
    baq, _ = beta_alpha(diff, panel["BENCH"], lag)
    _reg("HLS interaction: momentum(LOW cov) - momentum(HIGH cov)")
    print(f"\n  INTERACTION  momentum(LOW) - momentum(HIGH): "
          f"{_f(stq.get('mean_bps'),8)} bps  NW t {_f(stq.get('nw_t'),6,2)}"
          f"  boot t {_f(stq.get('boot_t'),6,2)} (MC sd {stq.get('boot_t_mc_sd')})")
    print(f"      halves {_f(stq.get('h1_bps'),7)}/{_f(stq.get('h2_bps'),7)}"
          f"   thirds {stq.get('thirds_bps')}")
    print(f"      RULE 13 on the DIFFERENCE-OF-DIFFERENCES: beta "
          f"{_f(baq.get('beta'),6,3)}  alpha {_f(baq.get('alpha_bps'),8)}"
          f"  t {_f(baq.get('alpha_t'),6,2)}")
    res["interaction"] = {k: {"raw": v["raw"], "beta_alpha": v["beta_alpha"]}
                          for k, v in inter.items()}
    res["interaction"]["low_minus_high"] = {"raw": stq, "beta_alpha": baq}

    hdr("6b. THE INTERACTION UNDER ATTACK — the only non-null cell in the lab")
    ia, _ = interaction_study(panel, draws)
    res["interaction_attack"] = ia
    ref = ia["momentum_full_pool"]
    print(f"  reference: momentum(win-lose) in the FULL 120-name pool "
          f"{_f(ref.get('mean_bps'),8)} bps  NW t {_f(ref.get('nw_t'),6,2)}"
          f"  alpha {_f(ref.get('alpha_bps'),8)} (t {_f(ref.get('alpha_t'),5,2)})")
    print(f"\n  MECHANICAL-BIAS CHECK (H21g's diagnostic).  Mean cross-sectional sd of")
    print(f"  the 42-session return inside each coverage tercile: "
          f"{ia['dispersion_by_tercile_bps']}")
    print("  A tercile with wider dispersion produces a wider spread for free.")
    dn = ia["interaction_dispersion_normalised"]
    print(f"  dispersion-NORMALISED interaction: {dn['mean']} sd-units  "
          f"NW t {dn['nw_t']}  halves {dn['h1']}/{dn['h2']}  thirds {dn['thirds']}")
    n1, n2 = ia["null_persistent_shuffle"], ia["null_perdate_shuffle"]
    print(f"\n  NULL 1 — PERSISTENT symbol shuffle ({n1['draws']} draws): keeps every")
    print(f"    symbol's real coverage TRAJECTORY, reattaches it to another symbol.")
    print(f"    {n1['mean_bps']} bps, sd {n1['sd_bps']}, 95% [{n1['lo_bps']}, {n1['hi_bps']}]")
    print(f"  NULL 2 — per-date shuffle ({n2['draws']} draws): "
          f"{n2['mean_bps']} bps, sd {n2['sd_bps']}, "
          f"95% [{n2['lo_bps']}, {n2['hi_bps']}]")
    print(f"  Rule 14 — permutation SE / Newey-West SE = {ia['rule14_se_ratio']}"
          f"  (a ratio far below 1 makes any permutation z anti-conservative)")
    sn, sba = ia["interaction_sector_neutral"], ia["interaction_sector_neutral_beta_alpha"]
    print(f"\n  sector-demeaned returns: {_f(sn.get('mean_bps'),8)} bps  NW t "
          f"{_f(sn.get('nw_t'),6,2)}  alpha {_f(sba.get('alpha_bps'),8)} "
          f"(t {_f(sba.get('alpha_t'),5,2)})  halves "
          f"{_f(sn.get('h1_bps'),7)}/{_f(sn.get('h2_bps'),7)}  thirds {sn.get('thirds_bps')}")
    il = ia["interaction_on_liquidity"]
    print(f"  the SAME cut made on ADV instead of coverage: {_f(il.get('mean_bps'),8)}"
          f" bps  NW t {_f(il.get('nw_t'),6,2)}   <- if this is as big, it is a size"
          f" effect")
    ir = ia["interaction_on_raw_count"]
    print(f"  the same cut on the RAW story count:          {_f(ir.get('mean_bps'),8)}"
          f" bps  NW t {_f(ir.get('nw_t'),6,2)}  alpha "
          f"{_f(ia['interaction_on_raw_count_beta_alpha'].get('alpha_bps'),8)}")
    p = ia["phase_sweep"]
    print(f"\n  Rule 9: {p['positive']}/{p['n']} non-overlapping entry calendars "
          f"positive; min {p['min']}, median {p['median']:.1f}, max {p['max']} bps")
    print(f"  by year: {ia['by_year_bps']}")
    j = ia["jackknife"]
    print(f"  leave-one-symbol-out: median {j['median_bps']}, worst "
          f"{j['min_bps']} (drop {j['min_symbol']}), best {j['max_bps']} "
          f"(drop {j['max_symbol']})")
    c = ia["costs"]
    print(f"  costs: total leg turnover {c['total_leg_turnover']} per rebalance -> "
          f"net@{COST_BPS:.0f}bps {c['net_bps_at_10']} bps, "
          f"BREAK-EVEN {c['breakeven_cost_bps']} bps")
    lo = ia["long_only_low_cov_winners"]
    nlo = ia["null_persistent_longonly"]
    print(f"  LONG-ONLY form (winners inside the LOW-coverage tercile) minus SPY: "
          f"{_f(lo.get('mean_bps'),8)} bps  NW t {_f(lo.get('nw_t'),6,2)}"
          f"   beta {_f(lo.get('beta'),6,2)}  alpha {_f(lo.get('alpha_bps'),8)}"
          f" (t {_f(lo.get('alpha_t'),5,2)})")
    print(f"    its persistent-shuffle null: {nlo['mean_bps']} bps, sd {nlo['sd_bps']},"
          f" 95% [{nlo['lo_bps']}, {nlo['hi_bps']}]")
    z = ia["z_against_persistent_null"]
    print(f"\n  *** z AGAINST THE PERSISTENT-SHUFFLE NULL (the honest one) ***")
    print(f"      interaction              z = {z['interaction']}"
          f"   (its Newey-West t was {ia['interaction'].get('nw_t')},"
          f" its market-adjusted t {ia['interaction_beta_alpha'].get('alpha_t')})")
    print(f"      sector-neutral version   z = {z['interaction_sector_neutral']}")
    print(f"      long-only tradeable form z = {z['long_only']}")
    print(f"  annualised Sharpe of the interaction book {ia['sharpe_ann']}; "
          f"DEFLATED Sharpe at N={RUNNING_N}: {ia['deflated_sharpe']}")

    hdr("7. ROBUSTNESS VARIANTS")
    rob = {}
    # (a) entry-phase decomposition of the primary spread (Rule 9)
    _, bsp, _ = run_sort(panel, "RESID", 3, "ew", "RESID 3-bucket ew", boot=False)
    ph = phase_sweep(bsp["spread"], H)
    ok = [p for p in ph if p["mean_bps"] is not None]
    pos = sum(1 for p in ok if p["mean_bps"] > 0)
    print(f"  Rule 9 — the primary series pools all {H} entry phases; decomposed,")
    print(f"    {pos}/{len(ok)} non-overlapping calendars are positive;"
          f" min {min(p['mean_bps'] for p in ok)}, "
          f"median {np.median([p['mean_bps'] for p in ok]):.1f}, "
          f"max {max(p['mean_bps'] for p in ok)} bps")
    rob["phase_sweep"] = {"n": len(ok), "positive": pos,
                          "min": min(p["mean_bps"] for p in ok),
                          "median": float(np.median([p["mean_bps"] for p in ok])),
                          "max": max(p["mean_bps"] for p in ok)}
    _reg("Rule 9 entry-phase decomposition")

    # (b) monthly formation (STEP=21, lag 1) — the design most labs here use
    pm = build_panel(raw, guard=True, step=21)
    rm, _, _ = run_sort(pm, "RESID", 3, "ew", "RESID terciles EW, MONTHLY formation")
    print_sort(rm)
    rob["monthly"] = rm

    # (c) headline count instead of the non-templated subset
    ph_ = build_panel(raw, guard=True, count_field="n_headlines")
    rh, _, _ = run_sort(ph_, "RESID", 3, "ew",
                        "RESID terciles EW, ALL headlines (no templated filter)",
                        boot=False)
    print_sort(rh)
    rob["all_headlines"] = rh

    # (d) 126-session coverage lookback
    p126 = build_panel(raw, guard=True, lookback=126)
    r126, _, _ = run_sort(p126, "RESID", 3, "ew",
                          "RESID terciles EW, 126-session coverage window",
                          boot=False)
    print_sort(r126)
    rob["lookback126"] = r126

    # (e) 21-session hold
    p21 = build_panel(raw, guard=True, horizon=21)
    r21, _, _ = run_sort(p21, "RESID", 3, "ew",
                         "RESID terciles EW, 21-session hold", boot=False)
    print_sort(r21)
    rob["hold21"] = r21

    # (f) news floor: drop structurally untagged mega-caps (BRK.B, pre-2018 BKNG)
    pf = build_panel(raw, guard=True, news_floor=12.0)
    rf, _, _ = run_sort(pf, "RESID", 3, "ew",
                        "RESID terciles EW, >=12 stories/yr floor (G4)", boot=False)
    print_sort(rf)
    rob["news_floor12"] = rf

    # (g) guards OFF — measures what the three data defects are worth here
    pg = build_panel(raw, guard=False)
    rg, _, _ = run_sort(pg, "RESID", 3, "ew",
                        "RESID terciles EW, GUARDS G2/G3 OFF (defect audit)",
                        boot=False)
    print(f"\n  guards OFF: spread {rg['spread']['mean_bps']} bps "
          f"(t {rg['spread']['nw_t']}) vs guarded "
          f"{primary['spread']['mean_bps']} bps (t {primary['spread']['nw_t']}) "
          f"-> the frozen-quote / reused-ticker defects are worth "
          f"{round((rg['spread']['mean_bps'] or 0) - (primary['spread']['mean_bps'] or 0), 1)} bps here")
    rob["guards_off"] = rg
    res["robustness"] = rob

    res["variants"] = list(VARIANTS)
    res["n_variants"] = len(VARIANTS)
    res["runtime_min"] = round((time.time() - t0) / 60, 1)

    hdr("8. SUMMARY")
    print(f"  variants run in this lab: {len(VARIANTS)}")
    for v in VARIANTS:
        print(f"    - {v}")
    RESULTS.write_text(json.dumps(_jsonable(res), indent=1))
    print(f"\n  results -> {RESULTS}   [{res['runtime_min']} min]")
    return res


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items() if k != "series"}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(float(o)) else round(float(o), 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, pd.Timestamp):
        return str(o.date())
    return o


# ------------------------------------------------------------------- selftest

def selftest() -> int:
    """Machinery checks that do not touch the verdict."""
    bad = 0

    def chk(name, cond, extra=""):
        nonlocal bad
        print(f"  {'ok  ' if cond else 'FAIL'}  {name} {extra}")
        bad += 0 if cond else 1

    # NW se: white noise -> lag-0 se ~ sd/sqrt(n)
    rng = np.random.default_rng(1)
    x = rng.normal(size=4000)
    chk("nw_se(lag 0) matches the iid SE",
        abs(nw_se(x, 0) - x.std(ddof=0) / math.sqrt(len(x))) < 1e-9)
    # an overlapping series must get a LARGER se at the right lag
    y = pd.Series(rng.normal(size=4000)).rolling(42).mean().dropna().to_numpy()
    chk("nw_se grows with the lag on an overlapping series",
        nw_se(y, 41) > 2.5 * nw_se(y, 1),
        f"(lag1 {nw_se(y,1):.5f} -> lag41 {nw_se(y,41):.5f})")
    # frozen-run detector
    v = np.array([1.0, 2, 3] + [7.0] * 12 + [9.0])
    chk("frozen-run detector finds the run start", _first_frozen(v) == 3,
        f"got {_first_frozen(v)}")
    chk("frozen-run detector is silent on a clean series",
        _first_frozen(np.arange(50.0)) is None)
    # gap detector
    g = np.array([1.0] * 5 + [np.nan] * 12 + [2.0] * 5)
    chk("gap detector finds an interior gap", _first_gap(g) == 5, f"got {_first_gap(g)}")
    chk("gap detector ignores leading/trailing NaN",
        _first_gap(np.array([np.nan] * 20 + [1.0] * 20 + [np.nan] * 20)) is None)
    # cross-sectional residual is orthogonal to the control
    a = rng.normal(size=200)
    b = 3 * a + rng.normal(size=200)
    r = _xs_residual(b, a)
    chk("xs residual is orthogonal to its control", abs(np.corrcoef(r, a)[0, 1]) < 1e-10)
    # bucket_series sign convention on a planted effect
    n_d, n_s = 300, 60
    P = {"dates": pd.date_range("2018-01-01", periods=n_d, freq="B"),
         "cols": [f"S{i}" for i in range(n_s)],
         "FWD": np.zeros((n_d, n_s)), "OPEN": np.ones((n_d, n_s), bool),
         "SIG": np.zeros((n_d, n_s)), "SIZE": np.zeros((n_d, n_s)),
         "BENCH": np.zeros(n_d), "horizon": 42, "step": 1, "lag": 41}
    for i in range(n_d):
        s = rng.normal(size=n_s)
        P["SIG"][i] = s
        P["FWD"][i] = -0.01 * s + 0.001 * rng.normal(size=n_s)   # LOW sig -> HIGH ret
    bs = bucket_series(P, "SIG", 3)
    chk("bucket_series spread is LOW-minus-HIGH and finds a planted +ve effect",
        np.nanmean(bs["spread"]) > 0.01, f"({1e4*np.nanmean(bs['spread']):.0f} bps)")
    # planted NULL must come back inside the random-bucket control
    for i in range(n_d):
        P["FWD"][i] = 0.001 * rng.normal(size=n_s)
    bs0 = bucket_series(P, "SIG", 3)
    c = null_random_bucket(P, 3, 100)
    chk("a planted null lands inside the random-bucket control",
        c["lo_bps"] <= 1e4 * np.nanmean(bs0["spread"]) <= c["hi_bps"],
        f"({1e4*np.nanmean(bs0['spread']):.2f} vs [{c['lo_bps']}, {c['hi_bps']}])")
    # beta_alpha recovers a planted beta
    bench = rng.normal(size=1000) * 0.02
    z = 0.7 * bench + 0.001 + rng.normal(size=1000) * 0.001
    ba, _ = beta_alpha(z, bench, 1)
    chk("beta_alpha recovers a planted beta", abs(ba["beta"] - 0.7) < 0.02,
        f"(got {ba['beta']})")
    chk("beta_alpha recovers a planted alpha", abs(ba["alpha_bps"] - 10.0) < 1.5,
        f"(got {ba['alpha_bps']})")
    # thirds
    t = thirds(np.concatenate([np.full(100, 0.01), np.zeros(100), np.full(100, -0.01)]))
    chk("thirds splits into three eras", t == [100.0, 0.0, -100.0], f"(got {t})")
    print(f"\n  {'PASS' if bad == 0 else str(bad) + ' FAILURES'}")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--draws", type=int, default=DRAWS)
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    run(refresh=a.refresh, draws=a.draws)


if __name__ == "__main__":
    main()
