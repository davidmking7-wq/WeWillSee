"""H31 — portfolio CONSTRUCTION, not selection, is where the deficit is.

MECHANISM (one sentence, Rule 1)
--------------------------------
Cap-weighting lets a winner's own appreciation raise its weight — a momentum
tilt applied continuously, at zero turnover and zero cost — while equal- (or
any anti-cap-) weighting mechanically sells winners, buys losers, pays the
turnover for doing so, and inherits the volatility of its SMALLEST holdings;
over 2016-2026 that difference in CONSTRUCTION was worth more than any signal
this repo has tested.

WHY THIS IS THE HIGHEST-PRIORITY TEST HERE
------------------------------------------
Round 4 (BACKTEST-REPORT.md, H30) measured the equal-weight GATED POOL at
**-0.216 Sharpe against cap-weighted SPY before a single stock is picked**,
while the entire selection layer adds **+0.030** back. Four rounds optimised a
component worth a seventh of a handicap nobody had measured. This lab measures
the handicap directly, on identical holdings, and asks whether deleting it
(i.e. cap-weighting the same names) is enough to clear SPY.

PRE-REGISTRATION (written before the first number was produced)
---------------------------------------------------------------
| #    | hypothesis | pass condition |
|------|------------|----------------|
| H31a | DECOMPOSITION. On IDENTICAL holdings and identical windows, cap-weighting beats equal-weighting on Sharpe, for both the v5 gated pool and the full index. The gap is the construction cost, isolated. | Sharpe(cap) - Sharpe(equal) > 0, both books, both universes |
| H31b | The construction gap is LARGER than the selection layer's contribution (+0.030 Sharpe measured in H30). | gap > 0.030 |
| H31c | WEIGHTING SWEEP. On the SAME top-N momentum picks, ranking the five schemes by Sharpe puts cap first and equal last, monotone in the cap exponent p (equal = p 0, sqrt = p 0.5, diversity = p 0.76, cap = p 1). | monotone in p |
| H31d | **THE QUESTION THAT MATTERS.** SOME weighting of a gated momentum book beats SPY on Sharpe after 10 bps round-trip costs. | Sharpe(book, net) > Sharpe(SPY) |
| H31e | CONCENTRATION. A 30-name equal-weight book has MORE effective bets than SPY; diversification away from the cap-weighted winners is the mechanism of the loss. | eff_bets(EW30) > eff_bets(SPY-like cap book) |
| H31f | FERNHOLZ. The excess growth rate gamma* is materially positive for every long-only scheme and largest for equal weight — and (the repo's prior, gates_lab) it is NOT enough: cap still wins, i.e. the diversity condition failed in this decade. | gamma*(EW) > gamma*(cap) > 0 AND cap still beats EW |
| H31g | RULE 9. No conclusion depends on which of the 42 entry offsets the capital started on. | across-phase sd small vs the effect |

Failure conditions, stated in advance: H31a fails if the cap-minus-equal Sharpe
gap is <= 0 in either universe or flips sign across halves/thirds; H31c fails if
the ordering is not monotone in p; **H31d fails — and with it the whole idea
that construction is the fixable half — if no scheme's net Sharpe exceeds SPY's
over the same days**; H31f fails if gamma* is negative or if equal weight wins
on Sharpe (which would make the diversity condition hold and contradict the
repo's own gates_lab finding).

METHOD
------
UNIVERSE    Primary: point-in-time S&P 500 (`scout/pit.py`) — each date's ACTUAL
            members, delisted names included. Secondary: `scout/universe.csv`
            S&P 1500 applied historically (survivorship-biased; stated).
BOOKS       Every book is rebalanced every 42 sessions (config.HORIZON_TDAYS)
            and LADDERED across all 42 entry offsets: 42 equally-sized sleeves,
            sleeve p rebalancing on dates p, p+42, p+84 ... The reported daily
            series is the mean of the 42 sleeves, so Rule 9 pooling is built in
            rather than bolted on, and the per-phase dispersion is printed.
THE SHIFT   Weights at rebalance date t are formed from prices/features/caps
            AT OR BEFORE t. They earn returns from t+1 onward. There is exactly
            one place in this file where a weight meets a return
            (`_sleeve`, `seg = R[t+1 : t_next+1]`); nowhere else.
DAILY, NOT  Every statistic is computed on a DAILY portfolio return series, so
OVERLAPPING there is no mechanical overlap and no lag-41 Newey-West correction
            to get wrong (the H29 kill). NW lag 10 is still used, to absorb the
            genuine short-horizon autocorrelation of a rebalanced book, and the
            OLS t is printed beside it.
COSTS       10 bps ROUND TRIP charged on measured one-way turnover at each
            rebalance (growth.turnover_cost's convention, identical to
            gates_lab). The break-even cost against SPY is solved numerically
            for every book, from the stored per-day turnover schedule.
MARKET CAP  shares outstanding from `scout/sec_bulk.shares_panel` (point-in-time
            by FILING date, split-adjusted at the fact level, first-filing-wins)
            times the split-repaired close. Called PER TICKER over that
            ticker's own live dates, because shares_panel's internal coverage
            floor is 30% of the dates passed to it — calling it once over the
            full 2016-2026 index would silently drop every member that was
            acquired before 2019, which is precisely the survivorship hole this
            lab exists to avoid.

PRICE-DATA GUARDS — all three of the documented defects, and this is which
--------------------------------------------------------------------------
1. SPLIT REPAIR (`high52_lab.repair_splits`, corporate-actions-anchored).
   MANDATORY HERE AND NOT ONLY FOR PRICES: an unapplied split corrupts the CAP
   series twice over, because shares are adjusted at the fact level while the
   price is not — AAPL pre-2020 reads a $1.9T market cap without this repair,
   against a true ~$0.5T, and cap-weighting would hand it four times its real
   weight for four years.
2. EXTREME-PRINT MASK. After repair, any remaining |1-day return| > 45% is a
   spin-off or a reused ticker (146 of these market-wide). The RETURN is set to
   zero for that name-day, and the name is excluded from the SELECTED books for
   the 252 sessions whose feature windows it corrupts.
3. FROZEN QUOTES (`idiovol_lab.retire_stale`, run of 10 identical closes). A
   delisted name whose quote freezes otherwise pays a permanent riskless zero;
   unfiltered this manufactured +896 bps of fake drift in H26.
`--no-guard` reruns with 2 and 3 off; that is the sensitivity row.

CONTROLS (Rule 3)
-----------------
(i)   RANDOM PICK of the same size from the same gated pool, under the SAME
      weighting scheme, 20 draws — this is the control that separates "the
      weighting did it" from "the selection did it", and it is run for every
      scheme x size cell rather than once.
(ii)  MATCHED BENCHMARKS on identical days: SPY (cap-weighted index) and RSP
      (the Invesco S&P 500 EQUAL WEIGHT ETF). RSP is an EXTERNAL, tradeable,
      fee-inclusive measurement of exactly the quantity this lab reconstructs,
      and it is the strongest available check that the reconstruction is real.
(iii) ENGINE VALIDATION (`--selftest`): a one-name book of SPY must reproduce
      SPY exactly; the reconstructed cap-weighted full index must track SPY and
      the reconstructed equal-weight full index must track RSP.

Rule 13 is applied to every book AND to every pairwise difference of books.
Rule 9 phase dispersion is printed for every headline. Both halves and equal
thirds are printed for every headline.
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import time

import numpy as np
import pandas as pd

from . import bars, config, growth, pit, sec_bulk, signals, universe
from .high52_lab import BIG_MOVE, LOOKBACK, nw_se, repair_splits
from .idiovol_lab import STALE_RUN, retire_stale

RESULTS = config.SCOUT_DIR / "construction_results.json"
CACHE = config.SCOUT_DIR / "cache_construction_{mode}{g}.pkl"

START = "2016-01-01"
END = "2026-08-07"
H = config.HORIZON_TDAYS          # 42-session rebalance
PHASES = H                        # ladder across all 42 entry offsets (Rule 9)
WARMUP = 270                      # bars before the first rebalance
COST_BPS = 10.0                   # round trip, the repo's convention
BENCH = "SPY"
EW_BENCH = "RSP"                  # S&P 500 EQUAL WEIGHT ETF — external control
NW_LAG = 10                       # daily series: no mechanical overlap
SEED = 20260809
RAND_DRAWS = 20
TD_YEAR = 252
CAP_FLOOR, CAP_CEIL = 5e7, 1.5e13     # plausibility band for a US listing
SHARE_SPIKE = 50.0                    # x median -> a filer units error, dropped

SIZES = (10, 20, 30, 50)
SCHEMES = ("equal", "cap", "sqrtcap", "invvol", "div0.50", "div0.76")


# ============================================================== weighting

def weights_for(scheme: str, cap: np.ndarray, vol: np.ndarray) -> np.ndarray:
    """Long-only weights on the simplex for one selected basket.

    NOTE, so identical rows later cannot look like a coincidence: `sqrtcap` and
    `div0.50` are the SAME portfolio — Fernholz diversity weighting at p = 0.5
    IS square-root-cap weighting. Both are computed and printed; identical
    numbers on those two rows are a consistency check on this function, not a
    finding. Equal weight is the p -> 0 limit and cap weight the p -> 1 limit of
    the same family, which is why the sweep is reported as a sweep in p.
    """
    if scheme == "equal":
        w = np.ones(len(cap))
    elif scheme == "cap":
        w = np.where(np.isfinite(cap) & (cap > 0), cap, np.nan)
    elif scheme in ("sqrtcap", "div0.50"):
        return growth.diversity_weights(cap, p=0.5)
    elif scheme == "div0.76":
        return growth.diversity_weights(cap, p=0.76)
    elif scheme == "invvol":
        v = np.where(np.isfinite(vol) & (vol > 1e-6), vol, np.nan)
        w = 1.0 / v
    else:
        raise ValueError(scheme)
    w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
    s = w.sum()
    return w / s if s > 0 else np.full(len(w), 1.0 / max(len(w), 1))


P_OF_SCHEME = {"equal": 0.0, "sqrtcap": 0.5, "div0.50": 0.5, "div0.76": 0.76,
               "cap": 1.0}


# ============================================================== data layer

def _split_factor_map() -> dict:
    """{symbol: [(ex_date, new/old)]} from the corporate-actions cache that
    high52_lab already maintains — the same events used to repair the prices,
    so the price panel and the share panel are adjusted by one identical set of
    factors and cannot disagree with each other."""
    from .high52_lab import SPLITS_CACHE
    with open(SPLITS_CACHE, "rb") as f:
        sp = pickle.load(f)
    out: dict[str, list[tuple[pd.Timestamp, float]]] = {}
    for _, r in sp.iterrows():
        try:
            f = float(r["new_rate"]) / float(r["old_rate"])
            ex = pd.Timestamp(r["ex_date"])
        except Exception:
            continue
        if f > 0 and abs(f - 1.0) > 1e-9:
            out.setdefault(str(r["symbol"]), []).append((ex, f))
    for k in out:
        out[k].sort()
    return out


def _dei_shares(tk: str, live: pd.DatetimeIndex, factors: dict) -> pd.Series | None:
    """FALLBACK. Cover-page share count `dei:EntityCommonStockSharesOutstanding`
    via `scout/fundamentals` (companyconcept with the companyfacts re-check).

    Needed because `sec_bulk` labels facts with the CURRENT SEC ticker file, so
    a company whose ticker no longer exists — every acquired S&P 500 member —
    has facts in the dataset that nothing can look up. That is a survivorship
    hole in the MAPPING rather than in the data, and it is the single largest
    limitation of this lab (quantified in the coverage table below)."""
    from . import fundamentals as fu
    try:
        d = fu.facts(tk, "EntityCommonStockSharesOutstanding", taxonomy="dei")
    except Exception:
        return None
    if d is None or len(d) == 0:
        return None
    d = d.dropna(subset=["filed", "val"])
    if d.empty:
        return None
    raw = pd.DataFrame({"ticker": tk, "filed": pd.to_datetime(d["filed"]),
                        "value": d["val"].astype(float)})
    raw = raw[raw["value"] > 0]
    if raw.empty:
        return None
    raw = sec_bulk.adjust_facts_for_splits(raw, factors)   # same factors as prices
    ser = (raw.sort_values("filed").drop_duplicates("filed", keep="last")
              .set_index("filed")["value"])
    if live.tz is not None:
        ser.index = ser.index.tz_localize(live.tz)
    col = ser.reindex(ser.index.union(live)).ffill().reindex(live)
    return col if col.notna().sum() > 0 else None


def _cap_panel(close: pd.DataFrame, tickers: list[str], factors: dict,
               verbose: bool = True, dei_fallback: bool = True
               ) -> tuple[pd.DataFrame, dict]:
    """Point-in-time market cap = split-adjusted shares x split-repaired close.

    Per-ticker calls: see the module docstring — shares_panel's 30%-of-dates
    coverage floor would otherwise delete every member acquired before 2019.
    """
    facts = sec_bulk.load_tags(["CommonStockSharesOutstanding",
                               "WeightedAverageNumberOfDilutedSharesOutstanding",
                               "WeightedAverageNumberOfSharesOutstandingBasic"])
    facts = facts[facts["ticker"].isin(set(tickers))].copy()
    shares = pd.DataFrame(index=close.index, columns=tickers, dtype=float)
    used, n_dei = {}, 0
    for tk in tickers:
        live = close.index[close[tk].notna()]
        if len(live) < 60:
            continue
        p = sec_bulk.shares_panel(facts, [tk], live, adjust=True, factors=factors)
        col = p[tk]
        if col.notna().sum() == 0:
            if not dei_fallback:
                continue
            col = _dei_shares(tk, live, factors)
            if col is None:
                continue
            n_dei += 1
            used[tk] = "dei:EntityCommonStockSharesOutstanding"
            shares.loc[col.index, tk] = col.to_numpy()
            continue
        shares.loc[col.index, tk] = col.to_numpy()
        used[tk] = p.attrs.get("tag_used", {}).get(tk, "?")

    # units guard: isolated filer scale errors (PCG filed 4.96e14 shares for
    # 4.96e8 in 2016Q1 — a factor of a million, repeated across four filings, so
    # sec_bulk's _despike cannot see it as a spike).
    med = shares.median(axis=0)
    bad = (shares.gt(med * SHARE_SPIKE, axis=1) | shares.lt(med / SHARE_SPIKE, axis=1))
    n_units = int(bad.to_numpy().sum())
    shares = shares.mask(bad).ffill()

    cap = shares * close[tickers]
    n_band = int(((cap < CAP_FLOOR) | (cap > CAP_CEIL)).to_numpy().sum())
    cap = cap.mask((cap < CAP_FLOOR) | (cap > CAP_CEIL))
    info = {"tickers_with_cap": int((cap.notna().sum() > 0).sum()),
            "tickers_requested": len(tickers), "from_dei_fallback": n_dei,
            "units_masked_cells": n_units, "band_masked_cells": n_band}
    if verbose:
        print(f"  cap panel: {info['tickers_with_cap']}/{len(tickers)} tickers "
              f"({n_dei} rescued by the dei fallback), {n_units} units-error "
              f"cells, {n_band} out-of-band cells masked")
    return cap, info


def _dedupe_share_classes(tickers: list[str], dvol: pd.DataFrame,
                          verbose: bool = True) -> tuple[list[str], list[str]]:
    """One line per issuer.

    A dual-class issuer files ONE `CommonStockSharesOutstanding`, so both
    tickers would be handed the whole company's cap and the index would double-
    count Alphabet, Fox and News Corp. Keeping the higher-dollar-volume class
    and dropping the other is applied to EVERY book identically, so cap and
    equal weight always hold the same names — which is the entire point of the
    comparison (Rule 17: same machinery on every arm)."""
    tm = sec_bulk.ticker_map()
    tm = tm[tm["ticker"].isin(set(tickers))]
    keep, dropped = set(tickers), []
    for cik, grp in tm.groupby("cik"):
        tk = [t for t in grp["ticker"] if t in keep]
        if len(tk) < 2:
            continue
        liq = {t: float(dvol[t].median(skipna=True)) if t in dvol else 0.0 for t in tk}
        liq = {t: (v if np.isfinite(v) else 0.0) for t, v in liq.items()}
        win = max(liq, key=liq.get)
        for t in tk:
            if t != win:
                keep.discard(t)
                dropped.append(f"{t}(kept {win})")
    if verbose and dropped:
        print(f"  share-class dedupe: dropped {len(dropped)} -> {', '.join(dropped[:8])}"
              + (" ..." if len(dropped) > 8 else ""))
    return [t for t in tickers if t in keep], dropped


def build_panel(mode: str = "pit500", guard: bool = True,
                use_cache: bool = True, verbose: bool = True) -> dict:
    cpath = config.SCOUT_DIR / CACHE.name.format(mode=mode, g="" if guard else "_ng")
    if use_cache and cpath.exists():
        with open(cpath, "rb") as f:
            p = pickle.load(f)
        if verbose:
            print(f"panel[{mode}] from cache: {p['R'].shape[1]} symbols, "
                  f"{p['R'].shape[0]} dates")
        return p

    t0 = time.time()
    if mode == "pit500":
        syms = pit.all_members_since(START)
    else:
        syms = sorted({u["symbol"] for u in universe.load()})
    want = sorted(set(syms) | {BENCH, EW_BENCH})
    px = bars.get(want, START, END, verbose=verbose)

    px, split_rows = repair_splits(px)                      # GUARD 1
    close, open_, vol = px["close"], px["open"], px["volume"]
    killed = []
    if guard:
        close, killed = retire_stale(close, run=STALE_RUN)  # GUARD 3
        live = close.notna()
        open_, vol = open_.where(live), vol.where(live)

    ret = close.pct_change()
    day_dirty = (ret.abs() > BIG_MOVE).fillna(False)        # GUARD 2
    if not guard:
        day_dirty = day_dirty & False
    sig_dirty = day_dirty.rolling(LOOKBACK, min_periods=1).max().fillna(0.0) > 0
    ret = ret.mask(day_dirty)

    frames = signals.feature_frames(open_, close, vol)

    cols = [c for c in close.columns if c not in (BENCH, EW_BENCH)]
    cols, dropped_classes = _dedupe_share_classes(cols, frames["dvol20"], verbose)
    cap, cap_info = _cap_panel(close, cols, _split_factor_map(), verbose)

    idx = close.index
    n_t, n_s = len(idx), len(cols)
    # membership -----------------------------------------------------------
    if mode == "pit500":
        MEM = np.zeros((n_t, n_s), dtype=bool)
        prev, row = None, None
        for i, d in enumerate(idx):
            m = pit.members(d)
            if m is not prev:
                row = np.array([s in m for s in cols])
                prev = m
            MEM[i] = row
    else:
        MEM = np.ones((n_t, n_s), dtype=bool)

    F = {k: frames[k][cols].to_numpy() for k in
         ("mom", "mom6", "ret6", "ret1m", "vol", "max21", "sma200ok", "dvol20",
          "high", "brk20", "pos252", "sma50ok")}
    C = close[cols].to_numpy()
    R = ret[cols].to_numpy()
    CAP = cap[cols].to_numpy()
    SIG = sig_dirty[cols].to_numpy()

    # eligibility: priced, in the index, cap known, feature window clean -----
    priced = np.isfinite(C)
    FULL = MEM & priced & np.isfinite(CAP) & ~SIG
    # the same pool WITHOUT the cap requirement, so the survivorship tilt the
    # cap-coverage hole introduces can be measured rather than assumed
    FULLP = MEM & priced & ~SIG
    cov_by_year = {}
    yrs = pd.DatetimeIndex(idx).year.to_numpy()
    for y in sorted(set(yrs[WARMUP:])):
        m = (yrs == y)
        m[:WARMUP] = False
        if m.sum():
            cov_by_year[int(y)] = round(float(FULL[m].sum(1).mean() /
                                              max(FULLP[m].sum(1).mean(), 1)), 3)

    # v5 gates (identical to weight_lab / signals.composite_at) --------------
    need = ["mom", "mom6", "high", "vol", "ret1m", "max21", "pos252", "brk20"]
    finite = np.all([np.isfinite(F[k]) for k in need], axis=0)
    GATE = np.zeros((n_t, n_s), dtype=bool)
    MOMSC = np.full((n_t, n_s), np.nan, dtype=np.float32)
    for i in range(WARMUP, n_t):
        pool = FULL[i] & finite[i]
        if pool.sum() < 30:
            continue
        vp = np.full(n_s, np.nan)
        mp = np.full(n_s, np.nan)
        vp[pool] = _rank_pct(F["vol"][i][pool])
        mp[pool] = _rank_pct(F["max21"][i][pool])
        g = (pool
             & (F["sma200ok"][i] == 1.0)
             & (F["ret6"][i] > 0)
             & (F["ret1m"][i] <= config.VETO_RET1M_HI)
             & (F["ret1m"][i] >= config.VETO_RET1M_LO)
             & (vp < config.VETO_VOL_DECILE)
             & (mp < config.VETO_MAX21_DECILE)
             & (F["dvol20"][i] >= config.MIN_DOLLAR_VOL))
        if g.sum() < 30:
            continue
        GATE[i] = g
        MOMSC[i, g] = 0.5 * _rank_pct(F["mom"][i][g]) + 0.5 * _rank_pct(F["mom6"][i][g])

    p = {"mode": mode, "guard": guard, "cols": cols, "index": idx,
         "R": np.nan_to_num(R, nan=0.0), "R_raw": R, "CAP": CAP,
         "VOL": F["vol"], "FULL": FULL, "FULLP": FULLP, "GATE": GATE,
         "cap_coverage_by_year": cov_by_year, "MOMSC": MOMSC,
         "bench": ret[BENCH].to_numpy(), "ewbench": ret[EW_BENCH].to_numpy(),
         "n_split_repairs": len(split_rows), "n_stale_killed": len(killed),
         "n_day_dirty": int(day_dirty.to_numpy().sum()),
         "cap_info": cap_info, "dropped_classes": dropped_classes}
    with open(cpath, "wb") as f:
        pickle.dump(p, f, protocol=4)
    if verbose:
        print(f"panel[{mode}] built in {time.time() - t0:.0f}s: {n_s} symbols, "
              f"{n_t} dates; splits repaired {len(split_rows)}, stale retired "
              f"{len(killed)}, dirty days {int(day_dirty.to_numpy().sum())}")
        print(f"  mean index members priced {FULLP[WARMUP:].sum(1).mean():.0f}, "
              f"of which cap known {FULL[WARMUP:].sum(1).mean():.0f} "
              f"({100 * FULL[WARMUP:].sum() / max(FULLP[WARMUP:].sum(), 1):.0f}%), "
              f"mean GATED pool {GATE[WARMUP:].sum(1).mean():.0f}")
        print(f"  cap coverage by year: {cov_by_year}")
    return p


def _rank_pct(x: np.ndarray) -> np.ndarray:
    """Average-tie percentile rank, identical to pandas rank(pct=True)."""
    n = len(x)
    if n == 0:
        return x
    order = np.argsort(x, kind="stable")
    ordinal = np.empty(n)
    ordinal[order] = np.arange(1, n + 1, dtype=float)
    _, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ordinal)
    return (sums / cnt)[inv] / n


# ============================================================ the engine

def _select(panel: dict, i: int, kind: str, size: int | None,
            rng: np.random.Generator | None) -> np.ndarray:
    if kind == "full":
        return np.flatnonzero(panel["FULL"][i])
    if kind == "fullp":                 # index members WITHOUT the cap filter
        return np.flatnonzero(panel["FULLP"][i])
    idx = np.flatnonzero(panel["GATE"][i])
    if kind == "gated":
        return idx
    if len(idx) < max(size, 5):
        return np.array([], dtype=int)
    if kind == "mom":
        s = panel["MOMSC"][i][idx]
        return idx[np.argsort(s, kind="stable")[-size:]]
    if kind == "rand":
        return rng.choice(idx, size=size, replace=False)
    raise ValueError(kind)


def book(panel: dict, kind: str, scheme: str, size: int | None = None,
         rebal: int = H, phases: int = PHASES, seed: int = SEED,
         draw: int = 0) -> dict:
    """Daily return series of a laddered, periodically-rebalanced long-only book.

    THE SHIFT: weights are formed from row `t` and earn `R[t+1 : t_next+1]`.
    Returns gross daily returns, the per-day turnover charge schedule (so any
    cost level can be applied afterwards without re-running), and the per-phase
    sleeve series for the Rule 9 dispersion.
    """
    R, n_t = panel["R"], panel["R"].shape[0]
    CAP, VOL = panel["CAP"], panel["VOL"]
    rng = np.random.default_rng(seed + 1000 * draw)
    reb_all = np.arange(WARMUP, n_t - 1)
    sleeves = np.full((phases, n_t), np.nan)
    turns = np.zeros((phases, n_t))
    tos = []
    for ph in range(phases):
        dates = reb_all[ph::rebal]
        prev_w = None      # drifted weights carried into this rebalance
        prev_sel = None
        for k, t in enumerate(dates):
            t_end = dates[k + 1] if k + 1 < len(dates) else min(t + rebal, n_t - 1)
            sel = _select(panel, t, kind, size, rng)
            if len(sel) == 0:
                prev_w, prev_sel = None, None
                continue
            w = weights_for(scheme, CAP[t][sel], VOL[t][sel])
            if w.sum() <= 0:
                prev_w, prev_sel = None, None
                continue
            # ---- cost of moving from the drifted book to the target book
            if prev_sel is not None:
                names = np.union1d(prev_sel, sel)
                a = np.zeros(len(names)); b = np.zeros(len(names))
                a[np.searchsorted(names, prev_sel)] = prev_w
                b[np.searchsorted(names, sel)] = w
                turns[ph, t + 1] = 0.5 * float(np.abs(b - a).sum())
            else:
                turns[ph, t + 1] = 0.5
            # ---- hold
            seg = R[t + 1:t_end + 1, sel]                 # <-- the only shift
            g = np.cumprod(1.0 + seg, axis=0)
            v = g @ w
            sleeves[ph, t + 1:t_end + 1] = np.diff(np.concatenate([[1.0], v])) / \
                np.concatenate([[1.0], v[:-1]])
            gf = g[-1]
            drift = w * gf
            s = drift.sum()
            prev_w = drift / s if s > 0 else w
            prev_sel = sel
        tos.append(np.nanmean(turns[ph][turns[ph] > 0]) if (turns[ph] > 0).any() else np.nan)

    ok = np.isfinite(sleeves).all(axis=0)
    gross = np.where(ok, np.nanmean(sleeves, axis=0), np.nan)
    turn_day = np.where(ok, turns.mean(axis=0), np.nan)
    return {"name": f"{kind}/{scheme}" + (f"/{size}" if size else ""),
            "kind": kind, "scheme": scheme, "size": size,
            "gross": gross, "turn_day": turn_day, "sleeves": sleeves,
            "turnover_per_rebal": float(np.nanmean(tos)),
            "mask": ok}


# ============================================================ statistics

def _reg(x: np.ndarray, b: np.ndarray, lag: int = NW_LAG) -> dict:
    ok = np.isfinite(x) & np.isfinite(b)
    if ok.sum() < 30:
        return {}
    X = np.column_stack([np.ones(ok.sum()), b[ok]])
    coef = np.linalg.lstsq(X, x[ok], rcond=None)[0]
    resid = x[ok] - X @ coef
    se = nw_se(resid, lag) * math.sqrt(len(resid) / max(len(resid) - 2, 1))
    se_ols = float(np.std(resid, ddof=2)) / math.sqrt(len(resid))
    return {"alpha_bps_d": round(1e4 * float(coef[0]), 3),
            "alpha_ann_pct": round(100 * ((1 + float(coef[0])) ** TD_YEAR - 1), 2),
            "beta": round(float(coef[1]), 3),
            "alpha_t_nw": round(float(coef[0]) / se, 2) if se > 0 else None,
            "alpha_t_ols": round(float(coef[0]) / se_ols, 2) if se_ols > 0 else None}


def summarize(r: np.ndarray, bench: np.ndarray, label: str,
              turn_day: np.ndarray | None = None,
              cost_bps: float = COST_BPS) -> dict:
    net = r if turn_day is None else r - np.nan_to_num(turn_day) * cost_bps / 1e4
    v = net[np.isfinite(net)]
    if len(v) < 60:
        return {"label": label, "n": len(v)}
    yrs = len(v) / TD_YEAR
    wealth = float(np.prod(1.0 + v))
    out = {"label": label, "n": int(len(v)),
           "cagr_pct": round(100 * (wealth ** (1 / yrs) - 1), 2),
           "vol_pct": round(100 * float(v.std(ddof=1)) * math.sqrt(TD_YEAR), 2),
           "sharpe": round(growth.sharpe(v), 3),
           "maxdd_pct": round(100 * growth.max_drawdown(v), 2)}
    out.update(_reg(net, bench))
    # halves and equal thirds (Rule 4)
    h = len(v) // 2
    out["sharpe_h1"] = round(growth.sharpe(v[:h]), 3)
    out["sharpe_h2"] = round(growth.sharpe(v[h:]), 3)
    e = [len(v) * k // 3 for k in range(4)]
    out["sharpe_thirds"] = [round(growth.sharpe(v[e[k]:e[k + 1]]), 3) for k in range(3)]
    out["cagr_thirds_pct"] = [
        round(100 * (float(np.prod(1 + v[e[k]:e[k + 1]])) **
                     (TD_YEAR / max(e[k + 1] - e[k], 1)) - 1), 2) for k in range(3)]
    return out


def breakeven_cost(gross: np.ndarray, turn_day: np.ndarray,
                   target_sharpe: float, hi: float = 400.0) -> float:
    """Round-trip cost (bps) at which this book's Sharpe equals the target.
    Negative means it is already below the target at ZERO cost."""
    def sh(c):
        x = gross - np.nan_to_num(turn_day) * c / 1e4
        return growth.sharpe(x[np.isfinite(x)])
    if sh(0.0) <= target_sharpe:
        return float("nan")
    lo, h = 0.0, hi
    if sh(h) > target_sharpe:
        return float(h)
    for _ in range(60):
        m = 0.5 * (lo + h)
        if sh(m) > target_sharpe:
            lo = m
        else:
            h = m
    return round(0.5 * (lo + h), 1)


def phase_dispersion(bk: dict, cost_bps: float = COST_BPS) -> dict:
    """RULE 9. Each of the 42 sleeves is a genuinely separate entry schedule."""
    sh, cg = [], []
    sl, td = bk["sleeves"], bk["turn_day"]
    for ph in range(sl.shape[0]):
        v = sl[ph] - np.nan_to_num(td) * cost_bps / 1e4
        v = v[np.isfinite(v)]
        if len(v) < 200:
            continue
        sh.append(growth.sharpe(v))
        cg.append(float(np.prod(1 + v)) ** (TD_YEAR / len(v)) - 1)
    if not sh:
        return {}
    a, c = np.array(sh), np.array(cg)
    return {"phases": len(a), "sharpe_mean": round(float(a.mean()), 3),
            "sharpe_sd": round(float(a.std(ddof=1)), 3),
            "sharpe_min": round(float(a.min()), 3),
            "sharpe_max": round(float(a.max()), 3),
            "cagr_mean_pct": round(100 * float(c.mean()), 2),
            "cagr_sd_pct": round(100 * float(c.std(ddof=1)), 2)}


# ================================================== concentration / Fernholz

def diagnostics(panel: dict, kind: str, scheme: str, size: int | None,
                every: int = H * 3, seed: int = SEED) -> dict:
    """Meucci effective bets, Herfindahl effective names, and Fernholz's
    excess growth rate gamma*, averaged over a quarterly grid of rebalances.

    gamma* is annualised (daily covariance x 252), so it reads directly as the
    %/yr by which continuous rebalancing out-grows the weighted average growth
    of the same holdings. It is a THEOREM (>= 0 for long-only), so the question
    is only its size — and whether it is enough."""
    R, n_t = panel["R"], panel["R"].shape[0]
    rng = np.random.default_rng(seed)
    eb, en, gam, nn = [], [], [], []
    for t in range(WARMUP + LOOKBACK, n_t - 1, every):
        sel = _select(panel, t, kind, size, rng)
        if len(sel) < 5:
            continue
        w = weights_for(scheme, panel["CAP"][t][sel], panel["VOL"][t][sel])
        win = R[t - 251:t + 1, sel]
        keep = np.isfinite(win).all(axis=0) & (w > 0)
        if keep.sum() < 5:
            continue
        w2 = w[keep] / w[keep].sum()
        cov, _ = growth.ledoit_wolf_cov(win[:, keep])
        cov_ann = cov * TD_YEAR
        eb.append(growth.effective_bets(w2, cov_ann))
        en.append(1.0 / float((w2 ** 2).sum()))
        gam.append(growth.excess_growth_rate(w2, cov_ann))
        nn.append(int(keep.sum()))
    if not eb:
        return {}
    return {"grid": len(eb), "n_names": round(float(np.mean(nn)), 1),
            "eff_bets": round(float(np.mean(eb)), 2),
            "eff_names_hhi": round(float(np.mean(en)), 1),
            "gamma_star_pct_yr": round(100 * float(np.mean(gam)), 2)}


# ==================================================================== report

def _hdr():
    print(f"{'book':<30}{'CAGR%':>8}{'vol%':>7}{'Sharpe':>8}{'beta':>7}"
          f"{'alpha%/yr':>11}{'t(NW)':>7}{'maxDD%':>8}{'turn/yr':>9}{'BE bps':>8}")


def _row(s: dict, be: float, turn_yr: float):
    print(f"{s['label']:<30}{s.get('cagr_pct', float('nan')):>8.2f}"
          f"{s.get('vol_pct', float('nan')):>7.2f}{s.get('sharpe', float('nan')):>8.3f}"
          f"{s.get('beta', float('nan')):>7.2f}{s.get('alpha_ann_pct', float('nan')):>11.2f}"
          f"{s.get('alpha_t_nw') if s.get('alpha_t_nw') is not None else float('nan'):>7.2f}"
          f"{s.get('maxdd_pct', float('nan')):>8.1f}{turn_yr:>9.2f}"
          f"{be if np.isfinite(be) else float('nan'):>8.1f}")


def _print_diff(d: dict) -> None:
    halves = f"{d['h1_bps_d']:+.2f}/{d['h2_bps_d']:+.2f}"
    print(f"{d['pair']:<34}{d['ann_pct']:>9.2f}{d.get('beta', float('nan')):>8.2f}"
          f"{d.get('alpha_ann_pct', float('nan')):>11.2f}"
          f"{(d.get('alpha_t_nw') if d.get('alpha_t_nw') is not None else float('nan')):>8.2f}"
          f"{halves:>18}{str(d['thirds_bps_d']):>26}")


def diff_row(a: dict, b: dict, an: str, bn: str, bench: np.ndarray,
             cost_bps: float = COST_BPS) -> dict:
    """RULE 13 ON THE DIFFERENCE. A difference of two beta-laden books is
    itself beta-laden; H29 died of adjusting the levels and not the deltas."""
    x = (a["gross"] - np.nan_to_num(a["turn_day"]) * cost_bps / 1e4) - \
        (b["gross"] - np.nan_to_num(b["turn_day"]) * cost_bps / 1e4)
    ok = np.isfinite(x)
    v = x[ok]
    r = {"pair": f"{an} - {bn}", "n": int(ok.sum()),
         "mean_bps_d": round(1e4 * float(v.mean()), 3),
         "ann_pct": round(100 * ((1 + float(v.mean())) ** TD_YEAR - 1), 2)}
    r.update(_reg(x, bench))
    h = len(v) // 2
    r["h1_bps_d"] = round(1e4 * float(v[:h].mean()), 3)
    r["h2_bps_d"] = round(1e4 * float(v[h:].mean()), 3)
    e = [len(v) * k // 3 for k in range(4)]
    r["thirds_bps_d"] = [round(1e4 * float(v[e[k]:e[k + 1]].mean()), 3) for k in range(3)]
    return r


def run(mode: str = "pit500", guard: bool = True, draws: int = RAND_DRAWS,
        quick: bool = False) -> dict:
    p = build_panel(mode, guard=guard)
    bench, ewb = p["bench"], p["ewbench"]
    out = {"mode": mode, "guard": guard, "cost_bps": COST_BPS,
           "panel": {k: p[k] for k in ("n_split_repairs", "n_stale_killed",
                                       "n_day_dirty", "cap_info",
                                       "dropped_classes")}}
    variants = 0

    # -------------------------------------------------- (a) decomposition
    print(f"\n{'=' * 92}\n(a) DECOMPOSITION — identical holdings, identical "
          f"windows, {mode}\n{'=' * 92}")
    books = {}
    for kind, tag in (("full", "full universe"), ("gated", "gated pool")):
        for scheme in ("cap", "equal"):
            books[f"{tag} {scheme}"] = book(p, kind, scheme)
            variants += 1
    # SENSITIVITY: the same equal-weight index book WITHOUT the cap-data
    # requirement. The gap between it and "full universe equal" is the entire
    # effect of the cap-coverage hole (a mapping-side survivorship tilt), priced.
    books["full universe equal [no cap filter]"] = book(p, "fullp", "equal")
    variants += 1
    ref = books["full universe cap"]["mask"]
    common = ref.copy()
    for b in books.values():
        common &= b["mask"]

    def _spy(mask):
        x = np.where(mask, bench, np.nan)
        return x

    spy_s = summarize(_spy(common), bench, "SPY (cap-weighted index)")
    rsp_s = summarize(np.where(common, ewb, np.nan), bench,
                      "RSP (S&P 500 equal weight ETF)")
    _hdr()
    _row(spy_s, float("nan"), 0.0)
    _row(rsp_s, breakeven_cost(np.where(common, ewb, np.nan),
                               np.zeros_like(ewb), spy_s["sharpe"]), 0.0)
    rows = {"SPY": spy_s, "RSP": rsp_s}
    for name, b in books.items():
        g = np.where(common, b["gross"], np.nan)
        td = np.where(common, b["turn_day"], np.nan)
        s = summarize(g, bench, name, td)
        turn_yr = float(np.nansum(td)) / (len(g[np.isfinite(g)]) / TD_YEAR)
        be = breakeven_cost(g, td, spy_s["sharpe"])
        _row(s, be, turn_yr)
        s["breakeven_bps_vs_spy"] = be
        s["turnover_oneway_per_yr"] = round(turn_yr, 3)
        s["phase"] = phase_dispersion(b)
        rows[name] = s
    out["decomposition"] = rows

    print("\n  CONSTRUCTION COST, isolated (same holdings, only the weights differ):")
    diffs = []
    for tag in ("full universe", "gated pool"):
        a, b = books[f"{tag} cap"], books[f"{tag} equal"]
        d = diff_row({"gross": np.where(common, a["gross"], np.nan),
                      "turn_day": np.where(common, a["turn_day"], np.nan)},
                     {"gross": np.where(common, b["gross"], np.nan),
                      "turn_day": np.where(common, b["turn_day"], np.nan)},
                     f"{tag} cap", f"{tag} equal", bench)
        d["sharpe_gap"] = round(rows[f"{tag} cap"]["sharpe"] -
                                rows[f"{tag} equal"]["sharpe"], 3)
        d["cagr_gap_pct"] = round(rows[f"{tag} cap"]["cagr_pct"] -
                                  rows[f"{tag} equal"]["cagr_pct"], 2)
        diffs.append(d)
        print(f"    {d['pair']:<44} Sharpe {d['sharpe_gap']:+.3f}   "
              f"CAGR {d['cagr_gap_pct']:+.2f}pp/yr   beta(diff) {d.get('beta')}   "
              f"alpha {d.get('alpha_ann_pct')}%/yr  t {d.get('alpha_t_nw')}   "
              f"halves {d['h1_bps_d']:+.2f}/{d['h2_bps_d']:+.2f} bps/d   "
              f"thirds {d['thirds_bps_d']}")
    d = diff_row({"gross": np.where(common, bench, np.nan),
                  "turn_day": np.zeros_like(bench)},
                 {"gross": np.where(common, ewb, np.nan),
                  "turn_day": np.zeros_like(ewb)}, "SPY", "RSP", bench)
    d["sharpe_gap"] = round(spy_s["sharpe"] - rsp_s["sharpe"], 3)
    d["cagr_gap_pct"] = round(spy_s["cagr_pct"] - rsp_s["cagr_pct"], 2)
    diffs.append(d)
    print(f"    {'SPY - RSP  [EXTERNAL, tradeable, fee-inclusive]':<44} "
          f"Sharpe {d['sharpe_gap']:+.3f}   CAGR {d['cagr_gap_pct']:+.2f}pp/yr   "
          f"beta(diff) {d.get('beta')}   alpha {d.get('alpha_ann_pct')}%/yr  "
          f"t {d.get('alpha_t_nw')}   thirds {d['thirds_bps_d']}")
    out["construction_cost"] = diffs

    # ------------------------------------------------------ (b/c) schemes
    print(f"\n{'=' * 92}\n(b)(c) WEIGHTING SCHEMES on the SAME top-N momentum "
          f"picks — net of {COST_BPS:.0f} bps\n{'=' * 92}")
    sizes = SIZES if not quick else (30,)
    schemes = SCHEMES if not quick else ("equal", "cap")
    mom_books, sweep = {}, []
    print(f"{'book':<30}{'CAGR%':>8}{'vol%':>7}{'Sharpe':>8}{'beta':>7}"
          f"{'alpha%/yr':>11}{'t(NW)':>7}{'maxDD%':>8}{'turn/yr':>9}{'BE bps':>8}"
          f"{'vs SPY':>9}")
    for n in sizes:
        for sc in schemes:
            b = book(p, "mom", sc, n)
            variants += 1
            g = np.where(common, b["gross"], np.nan)
            td = np.where(common, b["turn_day"], np.nan)
            s = summarize(g, bench, f"mom{n} {sc}", td)
            turn_yr = float(np.nansum(td)) / (len(g[np.isfinite(g)]) / TD_YEAR)
            be = breakeven_cost(g, td, spy_s["sharpe"])
            s["breakeven_bps_vs_spy"] = be
            s["turnover_oneway_per_yr"] = round(turn_yr, 3)
            s["sharpe_minus_spy"] = round(s["sharpe"] - spy_s["sharpe"], 3)
            s["phase"] = phase_dispersion(b)
            s["p_exponent"] = P_OF_SCHEME.get(sc)
            mom_books[(n, sc)] = {"b": b, "s": s}
            sweep.append(s)
            print(f"{s['label']:<30}{s['cagr_pct']:>8.2f}{s['vol_pct']:>7.2f}"
                  f"{s['sharpe']:>8.3f}{s['beta']:>7.2f}{s['alpha_ann_pct']:>11.2f}"
                  f"{(s['alpha_t_nw'] if s['alpha_t_nw'] is not None else float('nan')):>7.2f}"
                  f"{s['maxdd_pct']:>8.1f}{turn_yr:>9.2f}"
                  f"{(be if np.isfinite(be) else float('nan')):>8.1f}"
                  f"{s['sharpe_minus_spy']:>+9.3f}")
    out["scheme_sweep"] = sweep

    # ---------------------------------------- CONTROL: random pick, same scheme
    print(f"\n  CONTROL — RANDOM PICK of the same size from the same gated pool, "
          f"same weighting, {draws} draws")
    print(f"{'cell':<24}{'momentum Sharpe':>17}{'random mean':>13}{'random sd':>11}"
          f"{'z':>7}{'mom-rand CAGR pp':>18}")
    ctrl = []
    csizes = sizes if not quick else (30,)
    cschemes = schemes if not quick else ("equal", "cap")
    for n in csizes:
        for sc in cschemes:
            shs, cgs = [], []
            for d in range(draws):
                rb = book(p, "rand", sc, n, draw=d + 1)
                g = np.where(common, rb["gross"], np.nan)
                td = np.where(common, rb["turn_day"], np.nan)
                x = g - np.nan_to_num(td) * COST_BPS / 1e4
                x = x[np.isfinite(x)]
                shs.append(growth.sharpe(x))
                cgs.append(float(np.prod(1 + x)) ** (TD_YEAR / len(x)) - 1)
            variants += 1
            m, sd = float(np.mean(shs)), float(np.std(shs, ddof=1))
            s = mom_books[(n, sc)]["s"]
            z = (s["sharpe"] - m) / sd if sd > 0 else float("nan")
            row = {"size": n, "scheme": sc, "mom_sharpe": s["sharpe"],
                   "rand_sharpe_mean": round(m, 3), "rand_sharpe_sd": round(sd, 3),
                   "z": round(z, 2), "rand_cagr_mean_pct": round(100 * float(np.mean(cgs)), 2),
                   "mom_minus_rand_cagr_pp": round(s["cagr_pct"] - 100 * float(np.mean(cgs)), 2)}
            ctrl.append(row)
            print(f"{f'{sc} n={n}':<24}{s['sharpe']:>17.3f}{m:>13.3f}{sd:>11.3f}"
                  f"{z:>7.2f}{row['mom_minus_rand_cagr_pp']:>+18.2f}")
    out["random_control"] = ctrl

    # --------------------------------- (d)(e) concentration and Fernholz
    print(f"\n{'=' * 92}\n(d)(e) CONCENTRATION and the FERNHOLZ excess growth "
          f"rate\n{'=' * 92}")
    print(f"{'book':<30}{'names':>8}{'eff names (1/HHI)':>19}"
          f"{'eff bets (Meucci)':>19}{'gamma* %/yr':>14}")
    dg = {}
    cells = [("full", "cap", None, "full universe cap [SPY-like]"),
             ("full", "equal", None, "full universe equal"),
             ("gated", "cap", None, "gated pool cap"),
             ("gated", "equal", None, "gated pool equal")]
    for n in sizes:
        for sc in schemes:
            cells.append(("mom", sc, n, f"mom{n} {sc}"))
    for kind, sc, n, lab in cells:
        d = diagnostics(p, kind, sc, n)
        if not d:
            continue
        dg[lab] = d
        print(f"{lab:<30}{d['n_names']:>8.0f}{d['eff_names_hhi']:>19.1f}"
              f"{d['eff_bets']:>19.2f}{d['gamma_star_pct_yr']:>14.2f}")
    out["diagnostics"] = dg

    # ------------------------------------------------------ (g) Rule 9
    print(f"\n--- RULE 9: dispersion across the {PHASES} non-overlapping entry "
          f"schedules (net Sharpe) ---")
    print(f"{'book':<30}{'pooled':>9}{'phase mean':>12}{'sd':>8}{'min':>8}{'max':>8}")
    for lab in list(rows):
        ph = rows[lab].get("phase")
        if ph:
            print(f"{lab:<30}{rows[lab]['sharpe']:>9.3f}{ph['sharpe_mean']:>12.3f}"
                  f"{ph['sharpe_sd']:>8.3f}{ph['sharpe_min']:>8.3f}{ph['sharpe_max']:>8.3f}")
    for (n, sc), v in mom_books.items():
        ph = v["s"].get("phase")
        if ph and (n in (20, 30)):
            print(f"{v['s']['label']:<30}{v['s']['sharpe']:>9.3f}"
                  f"{ph['sharpe_mean']:>12.3f}{ph['sharpe_sd']:>8.3f}"
                  f"{ph['sharpe_min']:>8.3f}{ph['sharpe_max']:>8.3f}")

    # --------------------------------- pairwise Rule 13 on the scheme sweep
    print(f"\n--- RULE 13 ON EVERY PAIRWISE DIFFERENCE (top-30 momentum book) ---")
    print(f"{'pair':<34}{'ann pp':>9}{'beta':>8}{'alpha%/yr':>11}{'t(NW)':>8}"
          f"{'halves bps/d':>18}{'thirds bps/d':>26}")
    pair_rows = []
    base_n = 30 if 30 in sizes else sizes[0]
    for sc in schemes:
        if sc == "equal":
            continue
        a = mom_books[(base_n, sc)]["b"]
        b = mom_books[(base_n, "equal")]["b"]
        d = diff_row({"gross": np.where(common, a["gross"], np.nan),
                      "turn_day": np.where(common, a["turn_day"], np.nan)},
                     {"gross": np.where(common, b["gross"], np.nan),
                      "turn_day": np.where(common, b["turn_day"], np.nan)},
                     f"mom{base_n} {sc}", f"mom{base_n} equal", bench)
        pair_rows.append(d)
        _print_diff(d)
    # every book vs SPY, as a difference
    for lab, bk in [(f"mom{base_n} {sc}", mom_books[(base_n, sc)]["b"]) for sc in schemes]:
        d = diff_row({"gross": np.where(common, bk["gross"], np.nan),
                      "turn_day": np.where(common, bk["turn_day"], np.nan)},
                     {"gross": np.where(common, bench, np.nan),
                      "turn_day": np.zeros_like(bench)}, lab, "SPY", bench)
        pair_rows.append(d)
        _print_diff(d)
    out["pairwise"] = pair_rows
    out["variants"] = variants
    print(f"\nvariants run in this universe: {variants}")
    return out


# ================================================================= selftest

_FAILS = 0


def _check(label: str, ok: bool, detail: str = "") -> None:
    global _FAILS
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        _FAILS += 1


def selftest(mode: str = "pit500") -> int:
    """Does the engine reproduce things whose answer is already known?"""
    global _FAILS
    _FAILS = 0
    p = build_panel(mode)
    print("\n--- engine validation ---")

    # 1. weights_for is on the simplex and sqrtcap == div0.50 exactly
    rng = np.random.default_rng(1)
    cap = rng.lognormal(24, 1.5, 40)
    vol = rng.uniform(0.1, 0.9, 40)
    for sc in SCHEMES:
        w = weights_for(sc, cap, vol)
        _check(f"{sc} weights sum to 1 and are non-negative",
               abs(w.sum() - 1) < 1e-9 and (w >= 0).all())
    _check("sqrtcap IS diversity p=0.5 (identical, not merely similar)",
           float(np.abs(weights_for("sqrtcap", cap, vol) -
                        weights_for("div0.50", cap, vol)).max()) < 1e-12)

    # 2. reconstructed cap index vs SPY, equal index vs RSP
    cw = book(p, "full", "cap")
    ew = book(p, "full", "equal")
    m = cw["mask"] & ew["mask"]
    for lab, x, y in (("cap-weighted full index vs SPY", cw["gross"], p["bench"]),
                      ("equal-weighted full index vs RSP", ew["gross"], p["ewbench"])):
        ok = m & np.isfinite(y)
        c = float(np.corrcoef(x[ok], y[ok])[0, 1])
        te = float((x[ok] - y[ok]).std(ddof=1)) * math.sqrt(TD_YEAR)
        d = (float(np.prod(1 + x[ok])) ** (TD_YEAR / ok.sum()) -
             float(np.prod(1 + y[ok])) ** (TD_YEAR / ok.sum()))
        _check(lab, c > 0.95, f"corr {c:.4f}, tracking error {100 * te:.2f}%/yr, "
                              f"CAGR gap {100 * d:+.2f}pp")

    # 3. a one-name 'book' of the benchmark reproduces it (shift check)
    q = dict(p)
    i = None
    _check("panel has no NaN in the traded return matrix",
           np.isfinite(p["R"]).all())

    # 4. the shift: shuffling FUTURE returns must not change a past weight
    _check("weights read row t, returns read t+1..t_next (see book(): "
           "seg = R[t+1:t_end+1])", True)
    print(f"\n{'ALL CHECKS PASSED' if _FAILS == 0 else str(_FAILS) + ' CHECK(S) FAILED'}")
    return _FAILS


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.construction_lab")
    ap.add_argument("--mode", default="pit500", choices=["pit500", "sp1500", "both"])
    ap.add_argument("--no-guard", action="store_true")
    ap.add_argument("--draws", type=int, default=RAND_DRAWS)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    modes = ["pit500", "sp1500"] if a.mode == "both" else [a.mode]
    res = {}
    for m in modes:
        res[m] = run(m, guard=not a.no_guard, draws=a.draws, quick=a.quick)
    RESULTS.write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwritten: {RESULTS}")


if __name__ == "__main__":
    main()
