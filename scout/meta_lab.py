"""Meta-labeling lab (registry H3): can a small walk-forward logistic
model on entry-time features predict which of OUR OWN picks will hit,
better than composite rank alone? Lopez de Prado's one retail-viable ML
use — refining a known signal, not mining a new one. NOT part of the
pipeline; if it ships it runs only inside a user-invoked scan.

Plain numpy logistic regression (no new dependencies), standardized
features, L2, expanding walk-forward with a 2-cycle purge (~one full
label window) between train and test.

Usage: python -m scout.meta_lab
"""
import json
import math

import numpy as np
import pandas as pd

from . import backtest, config, signals, universe

H = config.HORIZON_TDAYS
FEATURES = ["rank_pct", "mom", "mom6", "high", "brk20", "pos252", "vol",
            "bull", "mid", "small", "earn_ahead", "just_rep"]


def build_panel():
    bars = backtest.load_bars(mode="sp1500")
    c = bars["close"]
    idx = c.index
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    spy = c["SPY"].dropna()
    bull = (spy > spy.rolling(200).mean()).reindex(idx)
    seg = {u["symbol"]: u.get("segment", "large") for u in universe.load()}
    emap = json.load(open(config.SCOUT_DIR / "earnings_history.json"))
    dates_np = np.array([str(d.date()) for d in idx.tz_localize(None)])
    ep = {s: np.searchsorted(dates_np, np.array(sorted(d))) for s, d in emap.items()}

    rows = []
    for cyc, pos in enumerate(backtest.positions_for(idx, None, None, 21)):
        snap = signals.composite_at(frames, idx[pos]).drop(index=["SPY"],
                                                           errors="ignore")
        if len(snap) < 50:
            continue
        pct = snap["score"].rank(pct=True)
        basis = c.iloc[pos]
        for sym in list(snap.index[:10]):
            if sym not in c.columns or pd.isna(basis.get(sym)):
                continue
            fwd = (c.iloc[pos + 1: pos + 1 + H][sym] / basis[sym]).dropna()
            if len(fwd) < H:
                continue
            r = fwd.values
            evs = ep.get(sym, np.array([]))
            nxt = evs[evs > pos] if len(evs) else np.array([])
            prev = evs[evs <= pos] if len(evs) else np.array([])
            rows.append({
                "cycle": cyc,
                "rank_pct": float(pct[sym]),
                "mom": float(snap.loc[sym, "mom"]),
                "mom6": float(snap.loc[sym, "mom6"]),
                "high": float(snap.loc[sym, "high"]),
                "brk20": float(snap.loc[sym, "brk20"]),
                "pos252": float(snap.loc[sym, "pos252"]),
                "vol": float(snap.loc[sym, "vol"]),
                "bull": 1.0 if bool(bull.iloc[pos]) else 0.0,
                "mid": 1.0 if seg.get(sym) == "mid" else 0.0,
                "small": 1.0 if seg.get(sym) == "small" else 0.0,
                "earn_ahead": 1.0 if len(nxt) and nxt[0] <= pos + 15 else 0.0,
                "just_rep": 1.0 if len(prev) and prev[-1] >= pos - 10 else 0.0,
                "hit": 1.0 if (r >= 1.05).any() else 0.0,
                "end": float(r[-1] - 1),
            })
    return pd.DataFrame(rows)


def fit_logistic(X, y, l2=1.0, iters=400, lr=0.1):
    w = np.zeros(X.shape[1] + 1)
    Xb = np.hstack([np.ones((len(X), 1)), X])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        g = Xb.T @ (p - y) / len(y) + l2 * np.r_[0, w[1:]] / len(y)
        w -= lr * g
    return w


def predict(w, X):
    Xb = np.hstack([np.ones((len(X), 1)), X])
    return 1 / (1 + np.exp(-Xb @ w))


def auc(y, p):
    order = np.argsort(p)
    ranks = np.empty(len(p))
    ranks[order] = np.arange(1, len(p) + 1)
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    return (ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def main() -> None:
    df = build_panel()
    cycles = sorted(df["cycle"].unique())
    print(f"panel: {len(df)} picks over {len(cycles)} cycles")

    oof = []
    for i, cyc in enumerate(cycles):
        if i < 30:
            continue
        train = df[df["cycle"] <= cycles[i - 3]]        # 2-cycle purge
        test = df[df["cycle"] == cyc]
        if len(train) < 150 or not len(test):
            continue
        mu, sd = train[FEATURES].mean(), train[FEATURES].std().replace(0, 1)
        Xtr = ((train[FEATURES] - mu) / sd).values
        Xte = ((test[FEATURES] - mu) / sd).values
        w = fit_logistic(Xtr, train["hit"].values)
        w_base = fit_logistic(Xtr[:, :1], train["hit"].values)   # rank_pct only
        t = test.copy()
        t["p_model"] = predict(w, Xte)
        t["p_base"] = predict(w_base, Xte[:, :1])
        oof.append(t)
    o = pd.concat(oof)
    print(f"out-of-fold picks: {len(o)} "
          f"({o['cycle'].min()}..{o['cycle'].max()} cycles)")

    for label, sub in (("ALL OOF", o),
                       ("first half", o[o["cycle"] <= np.median(o["cycle"])]),
                       ("second half", o[o["cycle"] > np.median(o["cycle"])])):
        a_m = auc(sub["hit"].values, sub["p_model"].values)
        a_b = auc(sub["hit"].values, sub["p_base"].values)
        print(f"[{label:<11}] AUC model {a_m:.3f} vs rank-only {a_b:.3f} "
              f"(n={len(sub)}, base hit {sub['hit'].mean():.0%})")
    q = o["p_model"].quantile([1 / 3, 2 / 3]).values
    lo_t = o[o["p_model"] <= q[0]]
    hi_t = o[o["p_model"] >= q[1]]
    print(f"model top-third:    hit {hi_t['hit'].mean():.1%}, avg end "
          f"{100*hi_t['end'].mean():+.2f}% (n={len(hi_t)})")
    print(f"model bottom-third: hit {lo_t['hit'].mean():.1%}, avg end "
          f"{100*lo_t['end'].mean():+.2f}% (n={len(lo_t)})")


if __name__ == "__main__":
    main()
