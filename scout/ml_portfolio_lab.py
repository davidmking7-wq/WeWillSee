"""ML-filtered portfolio lab: does applying the ML Check (registry H3) to
pick SELECTION improve the portfolio numbers vs the shipped top-N
baseline? Fully walk-forward: at each cycle the model is refitted on past
cycles only (2-cycle purge), then:

  baseN    top-N in composite order (the shipped baseline)
  skipN    composite order, but skip picks whose model probability falls
           in the bottom tercile of the TRAINING predictions (the shipped
           "weak = red flag" rule, mechanized), refill from the top-10
  rankN    top-N by model probability among the day's top-10 (the
           "better option" variant — model ordering instead of composite)

All variants evaluated on the SAME out-of-fold cycles (model warm-up
excluded for everyone), non-overlapping 42-td periods, S&P 1500.
Usage: python -m scout.ml_portfolio_lab
"""
import math

import numpy as np
import pandas as pd

from . import config
from .meta import FEATURES, fit_logistic
from .meta_lab import build_panel, predict

H = config.HORIZON_TDAYS


def metrics(rets):
    curve = np.cumprod([1 + r for r in rets])
    peak = np.maximum.accumulate(curve)
    return {"periods": len(rets),
            "avg": round(100 * float(np.mean(rets)), 2),
            "pct_ge5": round(100 * float(np.mean([r >= 0.05 for r in rets])), 1),
            "pct_pos": round(100 * float(np.mean([r > 0 for r in rets])), 1),
            "worst": round(100 * float(min(rets)), 1),
            "max_dd": round(100 * float((curve / peak - 1).min()), 1),
            "compounded": round(100 * float(curve[-1] - 1), 1)}


def main() -> None:
    df = build_panel()
    df["ord"] = df.groupby("cycle").cumcount()
    cycles = sorted(df["cycle"].unique())

    per_cycle = {}          # cycle -> dict(variant -> portfolio return)
    for i, cyc in enumerate(cycles):
        if i < 30:
            continue
        train = df[df["cycle"] <= cycles[i - 3]]
        test = df[df["cycle"] == cyc].sort_values("ord")
        if len(train) < 150 or not len(test):
            continue
        mu, sd = train[FEATURES].mean(), train[FEATURES].std().replace(0, 1)
        w = fit_logistic(((train[FEATURES] - mu) / sd).values,
                         train["hit"].values)
        p_train = predict(w, ((train[FEATURES] - mu) / sd).values)
        cut_weak = float(np.quantile(p_train, 1 / 3))
        t = test.copy()
        t["p"] = predict(w, ((t[FEATURES] - mu) / sd).values)
        out = {}
        for n in (2, 3):
            out[f"base{n}"] = float(t.head(n)["end"].mean())
            keep = t[t["p"] > cut_weak]
            chosen = keep.head(n) if len(keep) >= n else t.head(n)
            out[f"skip{n}"] = float(chosen["end"].mean())
            out[f"rank{n}"] = float(t.nlargest(n, "p")["end"].mean())
        per_cycle[cyc] = out

    oof = sorted(per_cycle)
    nonovl = oof[::max(1, math.ceil(H / 21))]
    variants = ["base2", "skip2", "rank2", "base3", "skip3", "rank3"]
    print(f"{len(oof)} out-of-fold cycles, {len(nonovl)} non-overlapping "
          f"periods ({cycles[30]}..{cycles[-1]})")
    hdr = (f"{'variant':<10}{'avg/win%':>9}{'>=+5%':>7}{'pos%':>6}"
           f"{'worst%':>8}{'maxDD%':>8}{'compounded%':>12}")
    for label, sel in (("ALL OOF", nonovl),
                       ("first half", nonovl[:len(nonovl) // 2]),
                       ("second half", nonovl[len(nonovl) // 2:])):
        print(f"\n[{label}]")
        print(hdr)
        for v in variants:
            m = metrics([per_cycle[cyc][v] for cyc in sel])
            print(f"{v:<10}{m['avg']:>9}{m['pct_ge5']:>7}{m['pct_pos']:>6}"
                  f"{m['worst']:>8}{m['max_dd']:>8}{m['compounded']:>12}")


if __name__ == "__main__":
    main()
