"""Meta-label model (shipped form of registry H3, validated in meta_lab:
out-of-fold AUC 0.60 vs 0.45 rank-only, both halves; top-third of model
probability hit 73%/+4.4% vs bottom-third 55%/-0.1%).

A tiny numpy logistic regression over entry-time features of OUR OWN
candidates, fitted during calibration (user-invoked only — there is no
background process) and stored inside calibration.json. At scan time the
stored weights score each candidate; the scan displays the probability
and a strong/ok/weak bucket. It never reorders the lists by itself —
the skill treats "weak" as a research red flag.
"""
import numpy as np
import pandas as pd

from . import config

FEATURES = ["rank_pct", "mom", "mom6", "high", "brk20", "pos252", "vol",
            "bull", "mid", "small", "earn_ahead", "just_rep"]


def fit_logistic(X, y, l2=1.0, iters=400, lr=0.1):
    w = np.zeros(X.shape[1] + 1)
    Xb = np.hstack([np.ones((len(X), 1)), X])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        g = Xb.T @ (p - y) / len(y) + l2 * np.r_[0, w[1:]] / len(y)
        w -= lr * g
    return w


def predict_proba(model: dict, feats: dict) -> float | None:
    try:
        x = np.array([(float(feats[f]) - model["mu"][i]) / model["sd"][i]
                      for i, f in enumerate(model["features"])])
    except (KeyError, TypeError, ValueError):
        return None
    z = model["w"][0] + float(np.dot(model["w"][1:], x))
    return float(1 / (1 + np.exp(-z)))


def bucket(model: dict, p: float | None) -> str:
    if p is None:
        return ""
    lo, hi = model["cut_lo"], model["cut_hi"]
    return "strong" if p >= hi else ("weak" if p <= lo else "ok")


def train_model(panel: pd.DataFrame) -> dict:
    """Fit on the full historical panel (built by calibrate from the same
    bars as everything else). Stores standardization, weights and the
    tercile cutoffs used for strong/ok/weak."""
    mu = panel[FEATURES].mean()
    sd = panel[FEATURES].std().replace(0, 1)
    X = ((panel[FEATURES] - mu) / sd).values
    y = panel["hit"].values.astype(float)
    w = fit_logistic(X, y)
    Xb = np.hstack([np.ones((len(X), 1)), X])
    p = 1 / (1 + np.exp(-Xb @ w))
    return {
        "features": FEATURES,
        "mu": [round(float(v), 6) for v in mu],
        "sd": [round(float(v), 6) for v in sd],
        "w": [round(float(v), 6) for v in w],
        "cut_lo": round(float(np.quantile(p, 1 / 3)), 4),
        "cut_hi": round(float(np.quantile(p, 2 / 3)), 4),
        "n": int(len(panel)),
        "note": "walk-forward validation in scout/meta_lab.py (AUC 0.60 vs "
                "0.45 rank-only, both halves; top-third 73% hit vs "
                "bottom-third 55%)",
    }
