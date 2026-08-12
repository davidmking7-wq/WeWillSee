"""H40 (handoff H36a) — PURE NEWS: is the UNEXPECTED component of news tone
more predictive than the raw headline signal?

MECHANISM (one sentence)
------------------------
Part of any day's news tone is predictable from the firm's prior state (a
stock that fell for a month gets gloomy coverage regardless of new facts);
the residual after removing that predictable part is the candidate
information shock, and the 2026 "Inefficient Pricing of News" mechanism says
the market underreacts to THAT, not to raw tone.

WHY THIS IS NEW HERE
--------------------
H15/H16/H17 tested RAW attention/tone/novelty and were rejected: they forecast
the SIZE of the next move and none of its sign. None of them removed the
predictable component first. H40a is the cheap scalar falsifier of the
residual-news idea using repo-feasible data; it is NOT a replication of the
paper (which uses full-article embeddings). The design below was frozen before
any return was computed.

SCOPE, STATED HONESTLY
----------------------
The cached Benzinga panel covers 120 TODAY-liquid names, 2016-01..2026-07.
That is a survivorship-tilted universe (no name that died before 2026 is in
it), the same cohort scoping as H15/H16. A rejection here is scoped to liquid
large caps; an advance would still need the PIT-universe test before any
production claim. The 120-name limitation is why H40a's only positive outcome
is ADVANCE_TO_H40B, never a production sleeve.

FROZEN DESIGN (handoff section 7, verbatim where it specifies)
--------------------------------------------------------------
TIMING      A story trades the close of session t only if published >= 15
            MINUTES before that session's close (15:45 ET regular, 12:45 on
            half-days — stricter than news_data.attribute_sessions' at-close
            rule); later stories roll to the next session. Entry AT the close
            of t, returns earned from t+1 onward.
PREDICTORS  through t-1 only, cross-sectionally z-scored per date:
            log price | 21s return | 126s return | 21s realised vol |
            log trailing-21 median dollar volume | 63s beta to SPY |
            trailing-21 specific-news count | trailing-21 mean raw tone
MODEL       expanding walk-forward ridge, lambda = 1e-3 (frozen), refit every
            21 sessions, minimum 252 sessions of training history. TARGET IS
            THE NEWS TONE ITSELF, never a return. pure = raw - predicted.
PORTFOLIO   per formation date require >= 12 names with attributable news;
            top-tercile minus bottom-tercile long-short (diagnostic) and
            top-tercile long-only vs SPY; overlapping cohorts, equal capital.
HORIZONS    21 and 42 sessions primary; 1, 5, 126 diagnostic.
COSTS       10 bps per leg at 1x, both legs charged; 2x stress.
CONTROLS    (1) within-date permutation of scores (destroys the firm-score
            link, preserves each date's return environment); (2) firm-date
            timing shuffle (circularly rotates each firm's score series,
            preserving its distribution, destroying timing). 500 draws each.
POSITIVE    OOS R^2 of the tone prediction must be > 0, else the verdict is
CONTROL     INCONCLUSIVE_REPRESENTATION — the mechanism was not tested.
DECISION    KILL_H40_SCALAR | INCONCLUSIVE_REPRESENTATION | ADVANCE_TO_H40B.
            Never a production sleeve from this file (handoff 7.7).

RULE 18: no momentum/SMA/quality/composite gates anywhere. The only filters
are data protections: templated-wire and broadtape stories dropped (measured
noise, pre-registered in news_data.py), integrity guards from
price_integrity.build_panel.

Run:  python -m scout.h40_pure_news            # full run, writes h40_results.json
      python -m scout.h40_pure_news --selftest
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np
import pandas as pd

from . import config, news_data
from .price_integrity import build_panel

RESULTS = config.SCOUT_DIR / "h40_results.json"
NEWS_CACHE = config.SCOUT_DIR / "cache_news_liquid120.pkl"

RIDGE_LAMBDA = 1e-3          # frozen (handoff 7.3)
REFIT_EVERY = 21
MIN_TRAIN = 252
MIN_ELIGIBLE = 12
HORIZONS_PRIMARY = (21, 42)
HORIZONS_DIAG = (1, 5, 126)
COST_BPS_LEG = 10.0
N_DRAWS = 500
EARLY_CUTOFF_MIN = 15        # minutes before the close a story must exist

FEATURES = ["log_px", "ret21", "ret126", "rv21", "log_dv21",
            "beta63", "news_n21", "tone21"]


# ------------------------------------------------------------------ data prep

def story_sessions(df: pd.DataFrame, close_index) -> pd.Series:
    """attribute_sessions with the STRICTER 15-minutes-before-close rule."""
    et = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert(news_data.ET)
    shifted = et + pd.Timedelta(minutes=EARLY_CUTOFF_MIN)
    return news_data.attribute_sessions(
        shifted.dt.tz_convert("UTC"), close_index)


def daily_tone_panel(close: pd.DataFrame, verbose=True):
    """(tone, count) time x symbol frames from the cached story-level panel."""
    df = pd.read_pickle(NEWS_CACHE)
    n0 = len(df)
    keep = ~news_data.is_templated(df["headline"])
    keep &= ~news_data.is_broadtape(df["n_tags"])
    df = df[keep].copy()
    df["session"] = story_sessions(df, close.index)
    df = df.dropna(subset=["session"])
    sc = news_data.score_headlines(df["headline"])
    df["tone"] = sc["tone"].to_numpy()
    g = df.groupby(["session", "symbol"])["tone"]
    tone = g.mean().unstack()
    count = g.size().unstack()
    naive = close.index.tz_convert("US/Eastern").tz_localize(None).normalize()
    tone = tone.reindex(naive)
    count = count.reindex(naive)
    tone.index = close.index
    count.index = close.index
    if verbose:
        print(f"  news: {n0} stories -> {keep.sum()} after wire/broadtape filters"
              f" -> {int(count.sum().sum())} (session,symbol) attributions")
    return tone, count


def build_features(close, volume, ret, spy_ret, tone, count):
    """All eight predictors, each usable at t only with data through t-1."""
    f = {}
    f["log_px"] = np.log(close).shift(1)
    f["ret21"] = close.pct_change(21, fill_method=None).shift(1)
    f["ret126"] = close.pct_change(126, fill_method=None).shift(1)
    f["rv21"] = ret.rolling(21).std().shift(1)
    f["log_dv21"] = np.log((close * volume).rolling(21).median()).shift(1)
    cov = ret.rolling(63).cov(spy_ret)
    var = spy_ret.rolling(63).var()
    f["beta63"] = cov.div(var, axis=0).shift(1)
    f["news_n21"] = count.fillna(0.0).rolling(21).sum().shift(1)
    f["tone21"] = tone.rolling(21, min_periods=1).mean().shift(1)
    return f


def _zscore_by_date(frame: pd.DataFrame) -> pd.DataFrame:
    mu = frame.mean(axis=1)
    sd = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mu, axis=0).div(sd, axis=0)


# -------------------------------------------------------- walk-forward ridge

def walk_forward(tone, feats, verbose=True):
    """Expanding ridge predicting TODAY'S tone from t-1 features.

    Returns (predicted, oos_r2). Fit rows are (date, firm) pairs where the firm
    HAS news that date. Prediction rows are the same; a firm with no news has
    no tone to predict. Refit every REFIT_EVERY sessions; each fit uses only
    rows strictly before its first prediction date."""
    z = {k: _zscore_by_date(v) for k, v in feats.items()}
    dates = tone.index
    X_parts, y_parts, meta = [], [], []
    for j, d in enumerate(dates):
        row_y = tone.iloc[j]
        names = row_y.dropna().index
        if len(names) == 0:
            continue
        cols = np.column_stack([z[k].iloc[j].reindex(names).to_numpy()
                                for k in FEATURES])
        ok = np.isfinite(cols).all(axis=1)
        if not ok.any():
            continue
        X_parts.append(cols[ok])
        y_parts.append(row_y[names[ok]].to_numpy())
        meta.extend((j, s) for s in names[ok])
    X = np.vstack(X_parts)
    y = np.concatenate(y_parts)
    day_ix = np.array([m[0] for m in meta])

    pred = np.full(len(y), np.nan)
    lamI = RIDGE_LAMBDA * np.eye(X.shape[1] + 1)
    Xb = np.column_stack([np.ones(len(X)), X])
    first_fit_day = MIN_TRAIN
    ss_res = ss_tot = 0.0
    for start in range(first_fit_day, int(day_ix.max()) + 1, REFIT_EVERY):
        train = day_ix < start
        test = (day_ix >= start) & (day_ix < start + REFIT_EVERY)
        if train.sum() < 500 or not test.any():
            continue
        A = Xb[train]
        w = np.linalg.solve(A.T @ A + lamI, A.T @ y[train])
        pred[test] = Xb[test] @ w
        mu_train = y[train].mean()
        ss_res += float(((y[test] - pred[test]) ** 2).sum())
        ss_tot += float(((y[test] - mu_train) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

    predicted = pd.DataFrame(np.nan, index=tone.index, columns=tone.columns)
    for (j, s), p in zip(meta, pred):
        if np.isfinite(p):
            predicted.iloc[j, predicted.columns.get_loc(s)] = p
    if verbose:
        print(f"  walk-forward: {len(y)} (date,firm) rows, OOS R^2 = {r2:+.4f}")
    return predicted, float(r2)


# ------------------------------------------------------------- the portfolio

def tercile_books(score, ret, horizon):
    """Overlapping-cohort daily returns: (long_short, long_only, n_formations).

    At each formation date t with >= MIN_ELIGIBLE scored names, go long the top
    tercile and short the bottom (equal weight inside the leg), hold `horizon`
    sessions, 1/horizon of capital per active cohort. Signal at t -> returns
    from t+1 (iloc row t+1 .. t+horizon)."""
    dates = score.index
    n = len(dates)
    ls = np.zeros(n)
    lo = np.zeros(n)
    active = np.zeros(n)
    n_form = 0
    for j in range(n - 1):
        row = score.iloc[j].dropna()
        if len(row) < MIN_ELIGIBLE:
            continue
        n_form += 1
        k = len(row) // 3
        top = row.nlargest(k).index
        bot = row.nsmallest(k).index
        end = min(j + horizon, n - 1)
        seg = ret.iloc[j + 1:end + 1]
        long_r = seg[top].mean(axis=1).fillna(0.0).to_numpy()
        short_r = seg[bot].mean(axis=1).fillna(0.0).to_numpy()
        ls[j + 1:end + 1] += (long_r - short_r) / horizon
        lo[j + 1:end + 1] += long_r / horizon
        active[j + 1:end + 1] += 1.0 / horizon
    ls_s = pd.Series(ls, index=dates)
    lo_s = pd.Series(np.where(active > 0, lo / np.maximum(active, 1e-12), 0.0),
                     index=dates)
    return ls_s, lo_s, n_form


def nw_t(x: pd.Series, lag: int) -> float:
    x = x.dropna().to_numpy()
    n = len(x)
    if n < lag + 2:
        return np.nan
    mu = x.mean()
    e = x - mu
    s = float(e @ e) / n
    for h in range(1, lag + 1):
        w = 1 - h / (lag + 1)
        s += 2 * w * float(e[:-h] @ e[h:]) / n
    return mu / math.sqrt(s / n)


def perf(series: pd.Series, horizon: int, cost_mult: float, n_legs: int,
         turnover_per_day: float) -> dict:
    """Annualised mean with costs charged on measured formation turnover."""
    cost = cost_mult * COST_BPS_LEG / 1e4 * n_legs * turnover_per_day
    s = series - cost
    return {"ann_pct": round(252 * float(s.mean()) * 100, 3),
            "t_nw": round(nw_t(s, lag=horizon), 2),
            "vol_pct": round(float(s.std()) * math.sqrt(252) * 100, 2)}


def split_stats(series: pd.Series, horizon: int, k: int) -> list[dict]:
    s = series.dropna()
    edges = np.linspace(0, len(s), k + 1).astype(int)
    return [{"span": f"{s.index[a].date()}..{s.index[b-1].date()}",
             "ann_pct": round(252 * float(s.iloc[a:b].mean()) * 100, 2),
             "t_nw": round(nw_t(s.iloc[a:b], horizon), 2)}
            for a, b in zip(edges[:-1], edges[1:])]


def alpha_beta(series: pd.Series, spy: pd.Series, horizon: int) -> dict:
    df = pd.concat([series, spy], axis=1, keys=["p", "m"]).dropna()
    x = df["m"].to_numpy()
    y = df["p"].to_numpy()
    b = float(np.cov(y, x)[0, 1] / np.var(x))
    resid = pd.Series(y - b * x, index=df.index)
    return {"beta": round(b, 3),
            "alpha_ann_pct": round(252 * float(resid.mean()) * 100, 3),
            "t_alpha_nw": round(nw_t(resid, horizon), 2)}


# ------------------------------------------------------------------ controls

def within_date_permutation(score, ret, horizon, n_draws, rng, real_ann):
    """Shuffle scores ACROSS firms within each date; same machinery."""
    vals = []
    for _ in range(n_draws):
        # permute BEFORE wrapping: pandas copy-on-write severs the buffer
        # link, so mutating the array after DataFrame() silently does nothing
        arr = score.to_numpy().copy()
        for i in range(arr.shape[0]):
            row = arr[i]
            m = np.isfinite(row)
            if m.sum() > 1:
                row[m] = rng.permutation(row[m])
        sh = pd.DataFrame(arr, index=score.index, columns=score.columns)
        ls, _, _ = tercile_books(sh, ret, horizon)
        vals.append(252 * float(ls.mean()) * 100)
    vals = np.array(vals)
    return {"null_mean_ann_pct": round(float(vals.mean()), 3),
            "null_sd": round(float(vals.std(ddof=1)), 3),
            "real_ann_pct": round(real_ann, 3),
            "pctile_of_real": round(float((vals < real_ann).mean() * 100), 1)}


def timing_shuffle(score, ret, horizon, n_draws, rng, real_ann):
    """Circularly rotate each firm's score SERIES by an independent offset."""
    vals = []
    n = len(score)
    for _ in range(n_draws):
        sh = {}
        for c in score.columns:
            k = int(rng.integers(63, n - 63))
            sh[c] = np.roll(score[c].to_numpy(), k)
        ls, _, _ = tercile_books(pd.DataFrame(sh, index=score.index),
                                 ret, horizon)
        vals.append(252 * float(ls.mean()) * 100)
    vals = np.array(vals)
    return {"null_mean_ann_pct": round(float(vals.mean()), 3),
            "null_sd": round(float(vals.std(ddof=1)), 3),
            "real_ann_pct": round(real_ann, 3),
            "pctile_of_real": round(float((vals < real_ann).mean() * 100), 1)}


# ---------------------------------------------------------------------- main

def run(quick: bool = False) -> dict:
    df = pd.read_pickle(NEWS_CACHE)
    symbols = sorted(df["symbol"].unique())
    print(f"  universe: {len(symbols)} cached liquid names (scope stated in docstring)")
    P = build_panel("2016-01-04", "2026-08-07", symbols=symbols,
                    extra=("SPY", "BIL"), min_coverage=0.95)
    close, volume, ret = P.close[symbols], P.volume[symbols], P.ret[symbols]
    spy = P.ret["SPY"]

    tone, count = daily_tone_panel(P.close)
    tone, count = tone[symbols], count[symbols]
    feats = build_features(close, volume, ret, spy, tone, count)
    predicted, oos_r2 = walk_forward(tone, feats)
    pure = tone - predicted            # NaN unless both exist -> post-warmup only

    variants = []
    out = {"hypothesis": "H40 (handoff H36a) pure news",
           "universe": {"n_names": len(symbols), "scope":
                        "TODAY-liquid 120; survivorship-tilted; verdict scoped"},
           "integrity": P.report, "oos_r2": round(oos_r2, 4),
           "ridge_lambda": RIDGE_LAMBDA, "refit_every": REFIT_EVERY,
           "min_train": MIN_TRAIN, "min_eligible": MIN_ELIGIBLE,
           "timing_rule": f"story >= {EARLY_CUTOFF_MIN} min before close",
           "signals": {}}

    rng = np.random.default_rng(20260812)
    draws = 50 if quick else N_DRAWS
    scores = {"raw": tone, "predictable": predicted, "pure": pure}
    for name, score in scores.items():
        blk = {}
        for h in HORIZONS_PRIMARY + (HORIZONS_DIAG if not quick else ()):
            ls, lo, n_form = tercile_books(score, ret, h)
            # one leg turns over fully each formation; per-day one-way turnover
            tpd = 2.0 / h        # both legs, 1/h of capital re-formed per day
            row = {"n_formations": n_form,
                   "long_short": {
                       "gross": perf(ls, h, 0.0, 2, tpd),
                       "net_1x": perf(ls, h, 1.0, 2, tpd),
                       "net_2x": perf(ls, h, 2.0, 2, tpd),
                       "halves": split_stats(ls, h, 2),
                       "thirds": split_stats(ls, h, 3),
                       "vs_spy": alpha_beta(ls, spy, h)},
                   "long_only_minus_spy": {
                       "net_1x": perf(lo.sub(spy, fill_value=0.0), h, 1.0, 1, 1.0 / h),
                       "vs_spy": alpha_beta(lo, spy, h)}}
            variants.append(f"{name}_h{h}")
            blk[f"h{h}"] = row
        out["signals"][name] = blk

    # the two mandated nulls, on the primary spec (pure, h=21)
    ls21, _, _ = tercile_books(pure, ret, 21)
    real_ann = 252 * float(ls21.mean()) * 100
    print("  running within-date permutation null...")
    out["null_within_date"] = within_date_permutation(pure, ret, 21, draws, rng, real_ann)
    print("  running firm-date timing shuffle null...")
    out["null_timing_shuffle"] = timing_shuffle(pure, ret, 21, draws, rng, real_ann)
    variants += ["null_within_date", "null_timing_shuffle"]

    # ----------------------------------------------------------- the decision
    p21 = out["signals"]["pure"]["h21"]["long_short"]
    p42 = out["signals"]["pure"]["h42"]["long_short"]
    r21 = out["signals"]["raw"]["h21"]["long_short"]
    if oos_r2 <= 0:
        verdict = "INCONCLUSIVE_REPRESENTATION"
        why = ("OOS news-prediction R^2 <= 0: the scalar features cannot "
               "predict tone, so the residual was never isolated and the "
               "external mechanism is untested, not rejected (handoff 7.5).")
    else:
        surv = []
        for tag, cell in (("h21", p21), ("h42", p42)):
            sgn = cell["net_2x"]["ann_pct"] > 0 and cell["net_2x"]["t_nw"] > 2
            halves_ok = all(x["ann_pct"] > 0 for x in cell["halves"])
            thirds_ok = sum(x["ann_pct"] > 0 for x in cell["thirds"]) >= 2
            nulls_ok = (out["null_within_date"]["pctile_of_real"] > 95
                        and out["null_timing_shuffle"]["pctile_of_real"] > 95)
            beats_raw = cell["net_2x"]["ann_pct"] > r21["net_2x"]["ann_pct"]
            surv.append(sgn and halves_ok and thirds_ok and nulls_ok and beats_raw)
        if any(surv):
            verdict = "ADVANCE_TO_H40B"
            why = "pure tone survives the full 7.7 gate at >=1 primary horizon."
        else:
            verdict = "KILL_H40_SCALAR"
            why = (f"pure h21 net-2x {p21['net_2x']['ann_pct']}%/yr "
                   f"(t {p21['net_2x']['t_nw']}), h42 "
                   f"{p42['net_2x']['ann_pct']}% (t {p42['net_2x']['t_nw']}); "
                   f"gate of handoff 7.7 not met.")
    out["variants_tried"] = variants
    out["verdict"] = {"call": verdict, "why": why,
                      "production_approved": False,
                      "note": "H40a can never be production-approved (handoff 7.7)"}
    RESULTS.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nVERDICT: {verdict}\n  {why}\nwrote {RESULTS}")
    return out


# ----------------------------------------------------------------- self-test

def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok &= bool(cond)

    idx = pd.date_range("2021-01-04", periods=260, freq="B", tz="US/Eastern")
    rng = np.random.default_rng(3)
    syms = [f"S{i}" for i in range(20)]

    # (1) the 15-minute rule: 15:50 ET story may NOT trade that close
    close_like = pd.DataFrame(1.0, index=idx, columns=["X"])
    df = pd.DataFrame({"created_at": [
        pd.Timestamp("2021-06-01 15:50", tz="US/Eastern").tz_convert("UTC"),
        pd.Timestamp("2021-06-01 15:40", tz="US/Eastern").tz_convert("UTC")]})
    ses = story_sessions(df, close_like.index)
    check("15:50 story rolls to the NEXT session",
          ses.iloc[0].normalize() == pd.Timestamp("2021-06-02"))
    check("15:40 story trades the SAME close",
          ses.iloc[1].normalize() == pd.Timestamp("2021-06-01"))

    # (2) no lookahead: returns after day D permuted -> book identical up to D
    score = pd.DataFrame(rng.normal(0, 1, (260, 20)), index=idx, columns=syms)
    ret = pd.DataFrame(rng.normal(0, .02, (260, 20)), index=idx, columns=syms)
    ls1, _, _ = tercile_books(score, ret, 5)
    D = 130
    ret2 = ret.copy()
    ret2.iloc[D + 1:] = ret2.iloc[D + 1:].to_numpy()[rng.permutation(260 - D - 1)]
    ls2, _, _ = tercile_books(score, ret2, 5)
    check("permuting returns after D leaves the book bit-identical up to D",
          np.allclose(ls1.iloc[:D + 1], ls2.iloc[:D + 1]))

    # (3) a planted signal is found, and the within-date permutation destroys it
    fwd = ret.shift(-1)
    planted = fwd + rng.normal(0, .01, fwd.shape)      # score knows tomorrow
    ls3, _, _ = tercile_books(planted, ret, 1)
    check("machinery finds a planted 1-day signal",
          252 * ls3.mean() > 0.5)
    res = within_date_permutation(planted, ret, 1, 30, rng,
                                  252 * float(ls3.mean()) * 100)
    check("within-date permutation destroys it (real > 95th pctile of null)",
          res["pctile_of_real"] > 95)

    # (4) ridge recovers a planted linear tone model out of sample
    # walk_forward consumes features AS GIVEN at row j (build_features has
    # already applied the t-1 shift in production), so the planted model is
    # simply tone[j] = 0.5 * z(f0)[j] + noise with f0 passed through unshifted
    f0 = pd.DataFrame(rng.normal(0, 1, (260, 20)), index=idx, columns=syms)
    tone = 0.5 * _zscore_by_date(f0) + rng.normal(0, .1, (260, 20))
    tone = pd.DataFrame(tone.to_numpy(), index=idx, columns=syms)
    feats = {k: (f0 if k == FEATURES[0] else
                 pd.DataFrame(rng.normal(0, 1, (260, 20)), index=idx, columns=syms))
             for k in FEATURES}
    import scout.h40_pure_news as me
    keep = me.MIN_TRAIN
    try:
        me.MIN_TRAIN = 120
        pred, r2 = walk_forward(tone, feats, verbose=False)
    finally:
        me.MIN_TRAIN = keep
    check(f"walk-forward ridge finds a planted tone model OOS (R2={r2:.2f} > 0.1)",
          r2 > 0.1)

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.h40_pure_news")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    run(quick=args.quick)


if __name__ == "__main__":
    main()
