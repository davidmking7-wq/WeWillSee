"""Sleeve lab: can BREADTH beat the market where SELECTION could not?

THE QUESTION THIS LAB EXISTS TO ANSWER
--------------------------------------
Every result in BACKTEST-REPORT.md attacks the same term of the growth
identity and loses: the engine tried to raise mu by picking better stocks,
and ten years of data say its ranking sorts nothing (decile 1 minus decile
10 = -0.26% at 42 td) while its gates only lower beta.

growth.py states the alternative in one line:

    g* = S^2 / 2        and        S_p = w'S / sqrt(w'Cw)

Growth is quadratic in Sharpe, and Sharpe is bought with UNCORRELATED
sleeves rather than with better forecasts. Four Sharpe-0.6 sleeves at zero
correlation combine to 1.20; the same four at rho=0.3 give 0.87. So the
registered question is:

    Does a book of weakly-correlated return sources -- multi-asset trend,
    cross-asset relative momentum, defensive equity, and the repo's own
    gated equity book -- reach a HIGHER SHARPE than SPY, and does the
    volatility-targeted, fractional-Kelly version of that book then beat
    SPY's RETURN once it is levered to a comparable risk?

Beating SPY on return at LOWER risk would be a landslide. Beating it on
Sharpe and then choosing the leverage is the only honest route to one, and
the leverage step is where the ruin risk lives -- hence the drawdown
constraint rather than full Kelly.

WHAT WOULD MAKE THIS FAIL (stated before running it)
----------------------------------------------------
1. The sleeves turn out correlated. Trend on equity ETFs in a decade with
   one dominant equity trend is not a separate bet from equities. Watch
   `effective_bets` and the sleeve correlation matrix, not the headline.
2. 2016-2026 is one macro era with one huge equity trend and one bond bear.
   Multi-asset trend's worst decade on record is roughly this one; a good
   result here would be surprising and a mediocre one is not disproof.
   The 100-year evidence (Hurst-Ooi-Pedersen) is the prior; this window is
   a consistency check, not the test.
3. ETF SELECTION is a look-back choice made in 2026 with survivors.
   The instrument list below is deliberately boring, large and old for
   exactly that reason, but it is not point-in-time and cannot be.
4. Leverage is assumed free and continuous. It is neither. The lab reports
   the unlevered book too, and the levered number should be read as an
   upper bound.

HOUSE RULES OBSERVED (RESEARCH-AGENDA.md section 1)
---------------------------------------------------
- Mechanism stated before the test: see the docstrings in growth.py and the
  registry rows H9-H14 in scout/hypotheses.md, written before this ran.
- Every signal is shifted one bar before it weights a return. `--audit`
  re-runs the whole book with the shift removed; if the shifted and
  unshifted results are close, the lab is not accidentally clairvoyant.
- Costs are turnover-based at --cost-bps and reported separately.
- Results are split into halves, and `--synthetic` runs the entire
  pipeline on generated data with a KNOWN answer so a plumbing error
  cannot be mistaken for an edge.

Usage:
  python -m scout.sleeve_lab                      # needs Alpaca keys in .env
  python -m scout.sleeve_lab --synthetic          # no keys, no network
  python -m scout.sleeve_lab --target-vol 0.12 --cost-bps 5 --audit
"""
from __future__ import annotations

import argparse
import json
import math
import pickle

import numpy as np
import pandas as pd

from . import growth as g

TD_YEAR = 252
BENCH = "SPY"
CASH = "BIL"          # 1-3 month T-bill ETF; the excess-return baseline

# Instruments, chosen for age and liquidity rather than for performance.
# Grouped so the cross-sectional sleeve can rank WITHIN a group and the
# report can show where the risk actually sits.
SLEEVE_UNIVERSE: dict[str, list[str]] = {
    "equity_us":     ["SPY", "IWM", "QQQ"],
    "equity_intl":   ["EFA", "EEM"],
    "rates":         ["IEF", "TLT", "SHY"],
    "credit":        ["LQD", "HYG"],
    "commodity":     ["DBC", "USO", "DBA"],
    "metals":        ["GLD", "SLV"],
    "real_assets":   ["VNQ", "XLE"],
    "currency":      ["UUP", "FXE"],
}
ALL_SYMBOLS = sorted({s for v in SLEEVE_UNIVERSE.values() for s in v}
                     | {BENCH, CASH})

CACHE = "sleeve_bars.pkl"


# --------------------------------------------------------------------- data

def load_prices(years: int, use_cache: bool = True) -> pd.DataFrame:
    """Daily adjusted closes for ALL_SYMBOLS, time x symbol."""
    from . import config                     # imported here: needs API keys
    path = config.SCOUT_DIR / CACHE
    if use_cache and path.exists():
        with open(path, "rb") as f:
            close = pickle.load(f)
        print(f"  bars from cache: {close.shape[0]} days x {close.shape[1]} symbols")
        return close
    from . import data
    bars = data.daily_ohlcv(ALL_SYMBOLS, days=int(years * 365.25) + 30)
    close = bars["close"].sort_index()
    with open(path, "wb") as f:
        pickle.dump(close, f)
    print(f"  fetched {close.shape[0]} days x {close.shape[1]} symbols")
    return close


def null_prices(n_days: int, seed: int, rf: float = 0.00008) -> pd.DataFrame:
    """Independent random walks whose expected return EQUALS the cash rate,
    so every excess return is pure noise and any book -- long, short or
    levered -- has zero expected excess.

    Giving the assets zero arithmetic drift instead would quietly make the
    null "cash beats everything", which a long-biased sleeve then fails for
    a reason that has nothing to do with its signal."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2016-01-04", periods=n_days)
    close = pd.DataFrame(
        {s: 100 * np.cumprod(1 + rf + rng.normal(0, 0.009, n_days))
         for s in ALL_SYMBOLS}, index=idx)
    close[CASH] = 100 * np.cumprod(np.full(n_days, 1 + rf))
    return close


def null_distribution(n_days: int, reps: int, args) -> None:
    """The control done properly: ONE null draw is not a control.

    A 10-year Sharpe has a standard error near sqrt(1/10) = 0.32, so a single
    null run routinely prints +/-0.5 and means nothing. What must be true is
    that the sleeves average ~0 ACROSS draws. This prints that distribution
    and the t-statistic of each sleeve's mean against zero."""
    from collections import defaultdict
    out = defaultdict(list)
    for k in range(reps):
        close = null_prices(n_days, seed=1000 + k)
        rets = close.pct_change()
        ex = rets.sub(rets[CASH].fillna(0.0), axis=0)
        syms = [s for s in ALL_SYMBOLS if s != CASH]
        flag = rebalance_calendar(close.index, args.rebal)
        for name, fn in SLEEVES.items():
            pos = hold_between(fn(close, ex, syms, args.per_asset_vol,
                                  args.max_asset_lev, 1), flag)
            r, _ = book_returns(pos, ex, args.cost_bps)
            out[name].append(g.sharpe(r))
    print(f"=== SYNTHETIC NULL, {reps} independent draws of "
          f"{n_days // TD_YEAR} years ===")
    print("Assets earn exactly the cash rate. Every sleeve's MEAN Sharpe "
          "must be ~0.\n")
    print(f"{'sleeve':<12}{'mean SR':>9}{'sd':>7}{'t':>7}{'min':>7}{'max':>7}")
    print("-" * 49)
    bad = []
    for name, vals in out.items():
        a = np.array(vals)
        t = float(a.mean() / (a.std(ddof=1) / math.sqrt(len(a)))) if a.std(ddof=1) else 0.0
        print(f"{name:<12}{a.mean():>9.3f}{a.std(ddof=1):>7.3f}{t:>7.2f}"
              f"{a.min():>7.2f}{a.max():>7.2f}")
        if abs(t) > 3.0:
            bad.append(name)
    print("\n" + ("PASS: no sleeve manufactures a Sharpe from noise."
                  if not bad else
                  f"FAIL: {', '.join(bad)} shows |t| > 3 on pure noise -- "
                  "there is a lookahead or accounting bug."))


def synthetic_prices(n_days: int = 252 * 10, seed: int = 7) -> pd.DataFrame:
    """Generated multi-asset data whose answer is known by construction.

    Three latent factors (equity, rates, commodity) plus idiosyncratic noise
    and stochastic volatility, with slow drifts that persist for months so a
    trend filter has something real to find. The point is NOT to predict what
    real data will show -- it is to confirm that the pipeline recovers an
    edge that is definitely present, and reports ~0 when it is definitely
    absent (`--synthetic-null`)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2016-01-04", periods=n_days)
    factors = np.zeros((n_days, 3))
    drift = np.zeros(3)
    for t in range(n_days):
        drift = 0.995 * drift + rng.normal(0, 0.00012, 3)   # slow, persistent
        factors[t] = drift + rng.normal(0, 0.007, 3)
    loading = {"equity_us": (1.0, -0.1, 0.0), "equity_intl": (0.9, -0.1, 0.1),
               "rates": (-0.2, 1.0, 0.0), "credit": (0.4, 0.6, 0.0),
               "commodity": (0.1, -0.1, 1.0), "metals": (0.0, 0.3, 0.6),
               "real_assets": (0.7, 0.2, 0.3), "currency": (-0.1, 0.2, -0.2)}
    out = {}
    for group, syms in SLEEVE_UNIVERSE.items():
        b = np.array(loading[group])
        for s in syms:
            vol_state = np.exp(np.cumsum(rng.normal(0, 0.02, n_days)) * 0.5)
            r = factors @ b + rng.normal(0, 0.006, n_days) * vol_state
            out[s] = 100 * np.cumprod(1 + r)
    out[CASH] = 100 * np.cumprod(1 + np.full(n_days, 0.00008))
    return pd.DataFrame(out, index=idx)[ALL_SYMBOLS]


# ------------------------------------------------------------------ sleeves

def _risk_scaled(signal: pd.DataFrame, rets: pd.DataFrame, per_asset_vol: float,
                 max_lev: float, shift: int) -> pd.DataFrame:
    """Turn a -1..1 forecast into positions each targeting `per_asset_vol`.

    `shift` is 1 in every honest run: the weight applied to day t's return is
    built from information through t-1."""
    vol = rets.apply(lambda c: g.blended_vol(c))
    scalar = (per_asset_vol / vol.replace(0.0, np.nan)).clip(upper=max_lev)
    return (signal * scalar).shift(shift)


def sleeve_trend(close: pd.DataFrame, rets: pd.DataFrame, syms: list[str],
                 per_asset_vol: float, max_lev: float, shift: int) -> pd.DataFrame:
    """Time-series momentum: long what is trending up, short what is not.

    Mechanism (Moskowitz-Ooi-Pedersen 2012; Hurst-Ooi-Pedersen 2017 over
    100+ years): macro information diffuses slowly and institutional flows
    (rebalancing, hedging, risk limits) push in the direction of recent
    moves. It is a long/short bet on the SIGN of drift, which is why it can
    be uncorrelated with the equity premium and why it tends to earn in the
    crises that hurt everything else."""
    sig = pd.DataFrame({s: g.trend_forecast(close[s]) for s in syms})
    return _risk_scaled(sig, rets[syms], per_asset_vol, max_lev, shift)


def sleeve_xsec(close: pd.DataFrame, rets: pd.DataFrame, syms: list[str],
                per_asset_vol: float, max_lev: float, shift: int,
                lookback: int = 126) -> pd.DataFrame:
    """Cross-asset relative momentum: long the strongest half of the
    instrument set, short the weakest, dollar- and risk-balanced.

    Distinct from `sleeve_trend`: this one is market-neutral ACROSS assets,
    so it earns when the ordering of asset classes persists even if every
    one of them falls. Cross-sectional and time-series momentum are the two
    halves of the same literature and are far from perfectly correlated."""
    past = close[syms].pct_change(lookback)
    rank = past.rank(axis=1, pct=True)
    sig = (2 * rank - 1).where(past.notna())            # -1 .. +1, mean ~0
    sig = sig.sub(sig.mean(axis=1), axis=0)
    return _risk_scaled(sig, rets[syms], per_asset_vol, max_lev, shift)


def sleeve_defensive(close: pd.DataFrame, rets: pd.DataFrame, syms: list[str],
                     per_asset_vol: float, max_lev: float, shift: int) -> pd.DataFrame:
    """Betting-against-beta, long-only form: hold the LOW-volatility half of
    the instrument set at equal RISK.

    Mechanism (Frazzini-Pedersen 2014; Black 1972): investors who want more
    return but cannot use leverage bid up high-beta assets instead, so
    high-beta is chronically overpriced. The correction is to hold low-beta
    and lever it -- which is exactly what the vol-targeting layer below
    does, and which is why this sleeve only makes sense inside a levered
    book. Held unlevered it just returns less than the market, slowly."""
    vol = rets[syms].apply(lambda c: g.blended_vol(c))
    rank = vol.rank(axis=1, pct=True)
    sig = (rank <= 0.5).astype(float).where(vol.notna())
    return _risk_scaled(sig, rets[syms], per_asset_vol, max_lev, shift)


SLEEVES = {"trend": sleeve_trend, "xsec": sleeve_xsec, "defensive": sleeve_defensive}


# ---------------------------------------------------------------- accounting

def book_returns(pos: pd.DataFrame, rets: pd.DataFrame,
                 cost_bps: float) -> tuple[pd.Series, pd.Series]:
    """Gross-of-signal, net-of-cost returns of a position book, plus turnover.

    Positions are already lagged. Turnover is the two-way change in weights,
    the same definition gates_lab uses, charged at cost_bps."""
    p = pos.reindex(columns=rets.columns).fillna(0.0)
    gross = (p * rets[p.columns]).sum(axis=1)
    turn = p.diff().abs().sum(axis=1) * 0.5
    return gross - turn * cost_bps / 10_000.0, turn


def rebalance_calendar(index: pd.DatetimeIndex, every: int) -> pd.Series:
    """Hold positions constant between rebalances (a daily-rebalanced book is
    a turnover fiction). Returns a boolean series marking rebalance days."""
    flag = pd.Series(False, index=index)
    flag.iloc[::every] = True
    return flag


def hold_between(pos: pd.DataFrame, flag: pd.Series) -> pd.DataFrame:
    """Freeze weights between rebalance dates.

    Note this holds the WEIGHT constant rather than the share count, so it
    is a slight overstatement of turnover between rebalances (a real book
    drifts). Overstating cost is the safe direction for a lab whose job is
    to look for an edge."""
    return pos.where(flag, other=np.nan, axis=0).ffill()


def normalise_vol(r: pd.Series, target: float, max_lev: float) -> pd.Series:
    """Scale a return stream to a constant target volatility, causally.

    Applied to every sleeve BEFORE combining them, so the combination
    weights are pure risk allocation rather than an accident of which
    sleeve happened to be built hotter."""
    lev = g.vol_target_scalar(g.blended_vol(r), target, max_leverage=max_lev)
    return (lev.shift(1) * r).dropna()


def causal_weights(sr: pd.DataFrame, method: str, flag: pd.Series,
                   lookback: int = 504, min_obs: int = 252) -> pd.DataFrame:
    """Sleeve weights recomputed at each rebalance from TRAILING data only.

    The obvious implementation -- inverse full-sample volatility, or HRP on
    the full-sample covariance -- uses the whole history to weight its own
    first day. That is lookahead, and it is the exact failure mode
    RESEARCH-AGENDA rule 4 (purged walk-forward) exists to prevent. Here the
    weights at date t are fitted on (t - lookback, t) and held until the next
    rebalance, so every weight is one a live book could have set.

    `method`: 'eqrisk' (inverse trailing vol) or 'hrp' (Ledoit-Wolf shrunk
    covariance -> hierarchical risk parity)."""
    cols = list(sr.columns)
    rows: dict[pd.Timestamp, np.ndarray] = {}
    for i, ts in enumerate(sr.index):
        if not bool(flag.get(ts, False)):
            continue
        window = sr.iloc[max(0, i - lookback):i]
        if len(window) < min_obs:
            continue
        if method == "eqrisk":
            sd = window.std(ddof=1).replace(0.0, np.nan)
            w = (1.0 / sd).fillna(0.0)
            w = w / w.sum() if w.sum() > 0 else pd.Series(1.0 / len(cols), index=cols)
            rows[ts] = w.reindex(cols).to_numpy()
        else:
            cov, _ = g.ledoit_wolf_cov(window.to_numpy())
            rows[ts] = g.hrp_weights(cov)
    if not rows:
        return pd.DataFrame(1.0 / len(cols), index=sr.index, columns=cols)
    w = pd.DataFrame(rows).T
    w.columns = cols
    return w.reindex(sr.index).ffill().dropna()


def causal_kelly_leverage(r: pd.Series, n_params: int, max_dd: float,
                          dd_prob: float, max_lev: float,
                          min_obs: int = 756) -> tuple[pd.Series, pd.Series]:
    """Expanding-window fractional-Kelly leverage path.

    At each date the leverage uses only returns strictly before it:

        L_t = min(f_drawdown, f_estimation) * mu_t / sigma_t^2

    f_drawdown from `kelly_fraction_for_drawdown` (a constraint, fixed ex
    ante) and f_estimation from `kelly_shrinkage` (which grows as the track
    record lengthens). Requires 3 years before it takes any risk at all --
    `min_track_record_length` says a Sharpe-1.0 book needs ~2.7 years just
    to be distinguishable from zero, so betting before then is betting on
    an unmeasured quantity."""
    f_dd = g.kelly_fraction_for_drawdown(max_dd, dd_prob)
    lev = pd.Series(0.0, index=r.index)
    for i in range(min_obs, len(r)):
        past = r.iloc[:i]
        mu = float(past.mean()) * TD_YEAR
        sd = float(past.std(ddof=1)) * math.sqrt(TD_YEAR)
        if sd <= 0:
            continue
        f_est = g.kelly_shrinkage(mu / sd, n_params, i)
        lev.iloc[i] = float(np.clip(min(f_dd, f_est) * g.optimal_leverage(mu, sd),
                                    0.0, max_lev))
    return lev, pd.Series({"f_drawdown": round(f_dd, 3)})


def describe(rets: pd.Series, bench: pd.Series, label: str) -> dict:
    r = pd.Series(rets).dropna()
    b = pd.Series(bench).reindex(r.index).fillna(0.0)
    if len(r) < TD_YEAR:
        return {"strategy": label, "note": "too short"}
    years = len(r) / TD_YEAR
    total = float((1 + r).prod())
    cagr = total ** (1 / years) - 1
    vol = float(r.std(ddof=1) * math.sqrt(TD_YEAR))
    var_b = float(b.var(ddof=1))
    beta = float(r.cov(b) / var_b) if var_b > 0 else 0.0
    return {
        "strategy": label,
        "cagr_pct": round(100 * cagr, 2),
        "vol_pct": round(100 * vol, 2),
        "sharpe": round(g.sharpe(r), 2),
        "max_dd_pct": round(100 * g.max_drawdown(r), 1),
        "beta": round(beta, 2),
        "ann_alpha_pct": round(100 * (float(r.mean() - beta * b.mean()) * TD_YEAR), 2),
        "skew": round(float(r.skew()), 2),
        "total_pct": round(100 * (total - 1), 1),
    }


def print_table(rows: list[dict], title: str) -> None:
    print(f"\n{title}")
    hdr = (f"{'strategy':<22}{'CAGR%':>8}{'vol%':>7}{'Sharpe':>8}{'maxDD%':>8}"
           f"{'beta':>6}{'annAlpha%':>11}{'skew':>7}{'total%':>10}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if "note" in r:
            print(f"{r['strategy']:<22}{r['note']:>58}")
            continue
        print(f"{r['strategy']:<22}{r['cagr_pct']:>8}{r['vol_pct']:>7}"
              f"{r['sharpe']:>8}{r['max_dd_pct']:>8}{r['beta']:>6}"
              f"{r['ann_alpha_pct']:>11}{r['skew']:>7}{r['total_pct']:>10}")


# ---------------------------------------------------------------------- run

def run(close: pd.DataFrame, args) -> dict:
    close = close.sort_index().ffill()
    rets = close.pct_change()
    cash = rets[CASH].fillna(0.0) if CASH in rets else pd.Series(0.0, index=rets.index)
    ex = rets.sub(cash, axis=0)                     # excess over T-bills
    syms = [s for s in ALL_SYMBOLS if s not in (CASH,)]
    syms = [s for s in syms if close[s].notna().sum() > 400]
    flag = rebalance_calendar(close.index, args.rebal)
    shift = 0 if args.audit else 1

    sleeve_rets, sleeve_turn = {}, {}
    for name, fn in SLEEVES.items():
        pos = fn(close, ex, syms, args.per_asset_vol, args.max_asset_lev, shift)
        pos = hold_between(pos, flag)
        r, turn = book_returns(pos, ex, args.cost_bps)
        sleeve_rets[name] = r
        sleeve_turn[name] = float(turn.mean() * TD_YEAR)

    raw = pd.DataFrame(sleeve_rets).dropna()
    spy_ex = ex[BENCH].reindex(raw.index).fillna(0.0)

    # The repo's own equity book as a fourth sleeve: long SPY at the beta the
    # gates lab measured (0.77). Standing in for gated_eqw without re-running
    # the S&P 1500 pipeline -- it is the honest summary of what that book is,
    # and including it keeps the comparison fair to the existing engine.
    raw["gated_equity"] = 0.77 * spy_ex

    # Every sleeve normalised to the same risk before combination.
    sr = pd.DataFrame({c: normalise_vol(raw[c], args.sleeve_vol, args.max_lev)
                       for c in raw.columns}).dropna()
    spy_ex = spy_ex.reindex(sr.index).fillna(0.0)
    flag = flag.reindex(sr.index).fillna(False)

    corr = sr.corr()
    cov_ann = sr.cov() * TD_YEAR

    # --- combination, with weights fitted only on trailing data
    books: dict[str, pd.Series] = {}
    weights: dict[str, pd.DataFrame] = {}
    for method, label in (("eqrisk", "combo_eqrisk"), ("hrp", "combo_hrp")):
        w = causal_weights(sr, method, flag, lookback=args.weight_lookback)
        aligned = sr.reindex(w.index)
        books[label] = (aligned * w).sum(axis=1)
        weights[label] = w

    for name in list(books):
        base = books[name]
        lev = g.vol_target_scalar(g.blended_vol(base), args.target_vol,
                                  max_leverage=args.max_lev)
        books[name + "_voltgt"] = (lev.shift(1) * base).dropna()

    # --- fractional Kelly, also causal
    best = max((n for n in books if n.endswith("_voltgt")),
               key=lambda n: g.sharpe(books[n]))
    b = books[best]
    lev_k, kinfo = causal_kelly_leverage(b, sr.shape[1], args.max_dd,
                                         args.dd_prob, args.max_lev)
    live = lev_k > 0
    if live.any():
        books[f"{best}_kelly"] = (lev_k * b)[live]
    kelly_note = {"base": best, "f_drawdown": float(kinfo["f_drawdown"]),
                  "days_levered": int(live.sum()),
                  "mean_leverage": round(float(lev_k[live].mean()), 2) if live.any() else 0.0,
                  "final_leverage": round(float(lev_k.iloc[-1]), 2)}

    # --- report
    rows = [describe(sr[c], spy_ex, c) for c in sr.columns]
    rows.append(describe(spy_ex, spy_ex, "SPY (excess)"))
    print_table(rows, f"SLEEVES (excess of T-bills, net of costs, each "
                      f"normalised to {args.sleeve_vol:.0%} vol)")

    print("\nsleeve correlation matrix  "
          "(THE number that decides this lab -- low correlation is the edge)")
    print(corr.round(2).to_string())
    w_last = weights["combo_eqrisk"].iloc[-1].to_numpy()
    ne = g.effective_bets(w_last, cov_ann.to_numpy())
    gam = g.excess_growth_rate(w_last, cov_ann.to_numpy())
    pred = g.combine_sharpe([g.sharpe(sr[c]) for c in sr.columns],
                            corr.to_numpy(), w_last)
    print(f"\neffective bets (final equal-risk weights): {ne:.2f} of "
          f"{sr.shape[1]} sleeves")
    print(f"rebalancing premium gamma*:                {100*gam:.2f}%/yr")
    print(f"predicted combined Sharpe from the parts:  {pred:.2f}")

    crows = [describe(v, spy_ex, k) for k, v in books.items()]
    crows.append(describe(spy_ex, spy_ex, "SPY (excess)"))
    print_table(crows, "COMBINED BOOKS")

    print(f"\nKelly sizing on {kelly_note['base']} (expanding window, 3y warm-up): "
          f"drawdown-constrained fraction {kelly_note['f_drawdown']} "
          f"(<= {args.max_dd:.0%} from start at {args.dd_prob:.0%} probability), "
          f"mean leverage {kelly_note['mean_leverage']}x, "
          f"latest {kelly_note['final_leverage']}x")
    if kelly_note["days_levered"] == 0:
        print("  -> leverage stayed at ZERO throughout: the trailing estimate "
              "of mu was never positive. That is the rule working, not failing.")

    # --- halves, because a single-era number is not evidence
    half = len(sr) // 2
    for tag, sl in (("first half", slice(0, half)), ("second half", slice(half, None))):
        hrows = []
        for k in ("combo_eqrisk_voltgt", "combo_hrp_voltgt"):
            seg = books[k].reindex(sr.index).iloc[sl].dropna()
            if len(seg) >= TD_YEAR:
                hrows.append(describe(seg, spy_ex.reindex(seg.index), k))
        hrows.append(describe(spy_ex.iloc[sl], spy_ex.iloc[sl], "SPY (excess)"))
        print_table(hrows, f"CONSISTENCY -- {tag} "
                           f"({sr.index[sl][0].date()} .. {sr.index[sl][-1].date()})")

    print("\nannualised turnover by sleeve: "
          + ", ".join(f"{k} {v:.1f}x" for k, v in sleeve_turn.items()))
    if args.audit:
        print("\n*** --audit: signals were NOT lagged. These numbers are "
              "deliberately contaminated. If they resemble the honest run, "
              "the lab has no lookahead; if they are far better, it does. ***")

    return {"sleeves": rows, "combined": crows, "kelly": kelly_note,
            "correlation": corr.round(3).to_dict(),
            "effective_bets": round(ne, 2),
            "excess_growth_pct": round(100 * gam, 3),
            "turnover": sleeve_turn, "audit_mode": bool(args.audit),
            "params": {"target_vol": args.target_vol, "cost_bps": args.cost_bps,
                       "rebal": args.rebal, "max_lev": args.max_lev}}


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.sleeve_lab")
    ap.add_argument("--synthetic", action="store_true",
                    help="run on generated data with a known answer (no keys)")
    ap.add_argument("--synthetic-null", action="store_true",
                    help="generated data with NO predictable drift: every "
                         "sleeve must come out ~0. The lab's own control.")
    ap.add_argument("--null-reps", type=int, default=12,
                    help="independent null draws (one is not a control)")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--rebal", type=int, default=5, help="trading days between rebalances")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--per-asset-vol", type=float, default=0.10)
    ap.add_argument("--max-asset-lev", type=float, default=3.0)
    ap.add_argument("--sleeve-vol", type=float, default=0.10,
                    help="each sleeve normalised to this vol before combining")
    ap.add_argument("--weight-lookback", type=int, default=504,
                    help="trailing days used to fit combination weights")
    ap.add_argument("--target-vol", type=float, default=0.12)
    ap.add_argument("--max-lev", type=float, default=3.0)
    ap.add_argument("--max-dd", type=float, default=0.30,
                    help="drawdown-from-start the Kelly fraction is sized for")
    ap.add_argument("--dd-prob", type=float, default=0.10)
    ap.add_argument("--audit", action="store_true",
                    help="remove the 1-bar signal lag (lookahead control)")
    args = ap.parse_args()

    if args.synthetic_null:
        null_distribution(TD_YEAR * args.years, args.null_reps, args)
        return
    if args.synthetic:
        close = synthetic_prices(TD_YEAR * args.years)
        print("=== SYNTHETIC: persistent factor drifts, edge present ===")
        print("Trend and xsec should be clearly positive. If they are not, "
              "the pipeline is broken, not the market.\n")
    else:
        close = load_prices(args.years, use_cache=not args.no_cache)

    out = run(close, args)

    if not (args.synthetic or args.synthetic_null):
        from . import config
        path = config.SCOUT_DIR / "sleeve_results.json"
        with open(path, "w") as f:
            json.dump(out, f, indent=1)
        print(f"\nwrote {path.name}")


if __name__ == "__main__":
    main()
