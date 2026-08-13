"""Regime lab: forensics on the top-2 portfolio's LOSSES, and tests of
ex-ante exposure rules meant to avoid them (registry H5a-H5g).

Part 1 (forensics) is descriptive: every non-overlapping 42-td window of
the baseline run is dumped with its return, the two picks and their
individual returns, and the market state KNOWN AT ENTRY -- trend, market
vol percentile, market drawdown, breadth, the engine's own eligible-pool
size, and the picks' forecast volatility. Then each state flag is scored
on whether it actually separates the losing windows from the rest.

Part 2 (tests) applies exposure rules to those same windows: cash or half
size when a flag is on, 0 return on the sidelined part (no shorting, no
leverage -- both documented to destroy the edge). Every variant is
compared with the baseline on identical periods and on each half of the
sample, so a win has to show up twice.

Usage: python -m scout.regime_lab [--universe sp1500] [--n 2]
"""
import argparse
import json
import math

import numpy as np
import pandas as pd

from . import config, portfolio_lab

H = config.HORIZON_TDAYS


def market_state(c, idx):
    """Ex-ante daily state series. Every value at date t uses only data
    available at t (expanding quantiles, trailing windows)."""
    spy = c["SPY"].dropna()
    bull = (spy > spy.rolling(200).mean()).reindex(idx)
    vol21 = (spy.pct_change().rolling(21).std() * math.sqrt(252)).reindex(idx)
    volq80 = vol21.expanding(min_periods=252).quantile(0.80)
    dd = (spy / spy.rolling(252).max() - 1).reindex(idx)
    above = c.gt(c.rolling(200).mean())
    breadth = (above.sum(axis=1) / c.rolling(200).mean().notna().sum(axis=1))
    breadthq20 = breadth.expanding(min_periods=252).quantile(0.20)
    return {"bull": bull, "vol21": vol21, "volq80": volq80, "dd": dd,
            "breadth": breadth, "breadthq20": breadthq20}


def build_windows(c, idx, scans, n):
    """One record per non-overlapping window: realized top-n return, the
    picks, and the entry-time state."""
    st = market_state(c, idx)
    stride = max(1, math.ceil(H / 21))
    sel = scans[::stride]
    rows = []
    for scan in sel:
        pos = scan["pos"]
        basis = c.iloc[pos]
        win = c.iloc[pos + 1: pos + 1 + H]
        legs = []
        for sym in scan["ranked"][:n]:
            if sym not in win.columns or pd.isna(basis.get(sym)):
                continue
            seg = (win[sym] / basis[sym]).dropna()
            if len(seg) >= 5:
                legs.append((sym, float(seg.values[-1] - 1),
                             float(seg.values.min() - 1)))
        ret = float(np.mean([l[1] for l in legs])) if legs else 0.0
        b = st["bull"].iloc[pos]
        bull = bool(b) if not pd.isna(b) else True
        sv, q = st["vol21"].iloc[pos], st["volq80"].iloc[pos]
        highvol = bool(not pd.isna(sv) and not pd.isna(q) and float(sv) > float(q))
        br, bq = st["breadth"].iloc[pos], st["breadthq20"].iloc[pos]
        lowbreadth = bool(not pd.isna(br) and not pd.isna(bq) and float(br) < float(bq))
        sig = [scan["sigma42"][s] for s, _, _ in legs if s in scan["sigma42"]]
        spy_ret = float(win["SPY"].dropna().values[-1] / basis["SPY"] - 1)
        rows.append({
            "date": scan["date"], "pos": pos, "ret": ret, "spy": spy_ret,
            "legs": legs, "bull": bull, "bear": not bull,
            "vol21": None if pd.isna(sv) else round(float(sv), 3),
            "highvol": highvol, "crash": (not bull) and highvol,
            "dd": None if pd.isna(dd_ := st["dd"].iloc[pos]) else round(float(dd_), 3),
            "breadth": None if pd.isna(br) else round(float(br), 3),
            "lowbreadth": lowbreadth,
            "pool": scan.get("pool"), "top_score": scan.get("top_score"),
            "sigma": float(np.mean(sig)) if sig else None,
        })
    # engine-internal flags need expanding baselines across scan dates
    pool = pd.Series([r["pool"] for r in rows], dtype=float)
    poolq25 = pool.expanding(min_periods=8).quantile(0.25)
    sigma = pd.Series([r["sigma"] for r in rows], dtype=float)
    sigmed = sigma.expanding(min_periods=8).median()
    for i, r in enumerate(rows):
        pq = poolq25.iloc[i]
        r["smallpool"] = bool(not pd.isna(pq) and r["pool"] < float(pq))
        tgt, cur = sigmed.iloc[i], sigma.iloc[i]
        r["volscale"] = (1.0 if pd.isna(tgt) or pd.isna(cur) or cur <= 0
                         else min(1.0, float(tgt) / float(cur)))
    return rows


FLAGS = ["bear", "highvol", "crash", "lowbreadth", "smallpool"]

VARIANTS = {
    "baseline":            lambda r: 1.0,
    "H5a crash->cash":     lambda r: 0.0 if r["crash"] else 1.0,
    "H5a' crash->half":    lambda r: 0.5 if r["crash"] else 1.0,
    "H5b bear->half":      lambda r: 0.5 if r["bear"] else 1.0,
    "H5b' bear->cash":     lambda r: 0.0 if r["bear"] else 1.0,
    "H5c highvol->half":   lambda r: 0.5 if r["highvol"] else 1.0,
    "H5d crash0+hivol.5":  lambda r: 0.0 if r["crash"] else (0.5 if r["highvol"] else 1.0),
    "H5e smallpool->half": lambda r: 0.5 if r["smallpool"] else 1.0,
    "H5f lowbreadth->half": lambda r: 0.5 if r["lowbreadth"] else 1.0,
    "H5g voltarget":       lambda r: r["volscale"],
    "H5g' voltarget+crash0": lambda r: 0.0 if r["crash"] else r["volscale"],
}


def apply_variant(rows, fn):
    return [fn(r) * r["ret"] for r in rows]


def line(name, m, extra=""):
    return (f"{name:<24}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
            f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}"
            f"{m['compounded']:>12}  {extra}")


HDR = (f"{'strategy':<24}{'periods':>8}{'avg%':>7}{'>=+5%':>7}{'pos%':>6}"
       f"{'worst%':>8}{'maxDD%':>8}{'compounded%':>12}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.regime_lab")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--n", type=int, default=2, help="picks per window")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    c, idx, scans = portfolio_lab.collect(args.universe, args.start, args.end)
    rows = build_windows(c, idx, scans, args.n)
    print(f"\n{len(rows)} non-overlapping windows, top-{args.n}, "
          f"{rows[0]['date']} .. {rows[-1]['date']} ({args.universe})\n")

    # ---------- Part 1: forensics ----------
    print("=== EVERY WINDOW (entry state known BEFORE the window) ===")
    print(f"{'entry':<12}{'ret%':>8}{'spy%':>8}  {'state':<34}"
          f"{'pool':>6}{'sig':>6}  picks")
    for r in rows:
        flags = ",".join(f for f in FLAGS if r[f]) or "-"
        legs = " ".join(f"{s}{v*100:+.0f}" for s, v, _ in r["legs"])
        print(f"{r['date']:<12}{r['ret']*100:>8.1f}{r['spy']*100:>8.1f}  "
              f"{flags:<34}{r['pool']:>6}"
              f"{(r['sigma'] or 0)*100:>6.0f}  {legs}")

    losses = sorted(rows, key=lambda r: r["ret"])
    tot_loss = sum(r["ret"] for r in rows if r["ret"] < 0)
    print(f"\n{sum(1 for r in rows if r['ret'] < 0)} losing windows, "
          f"summed loss {tot_loss*100:.1f}pp; "
          f"worst 5 = {sum(r['ret'] for r in losses[:5])*100:.1f}pp "
          f"({sum(r['ret'] for r in losses[:5])/tot_loss*100:.0f}% of all losses)")
    print("\n=== WORST 8 WINDOWS ===")
    for r in losses[:8]:
        flags = ",".join(f for f in FLAGS if r[f]) or "NO FLAG ON"
        print(f"  {r['date']}  {r['ret']*100:>6.1f}%  spy {r['spy']*100:>6.1f}%  "
              f"dd {(r['dd'] or 0)*100:>6.1f}%  breadth {r['breadth']}  "
              f"[{flags}]")

    print("\n=== DOES EACH FLAG SEPARATE THE LOSSES? ===")
    print(f"{'flag':<14}{'n_on':>6}{'avg_on':>9}{'avg_off':>9}{'worst_on':>10}"
          f"{'>=5%_on':>9}{'worst5_caught':>15}")
    worst5 = {r["date"] for r in losses[:5]}
    for f in FLAGS:
        on = [r for r in rows if r[f]]
        off = [r for r in rows if not r[f]]
        if not on:
            print(f"{f:<14}{0:>6}   never on")
            continue
        caught = sum(1 for r in on if r["date"] in worst5)
        print(f"{f:<14}{len(on):>6}{np.mean([r['ret'] for r in on])*100:>9.2f}"
              f"{np.mean([r['ret'] for r in off])*100:>9.2f}"
              f"{min(r['ret'] for r in on)*100:>10.1f}"
              f"{np.mean([r['ret'] >= .05 for r in on])*100:>9.0f}"
              f"{caught:>12}/5")

    # ---------- Part 2: exposure variants ----------
    half = len(rows) // 2
    out = {"universe": args.universe, "n": args.n,
           "span": [rows[0]["date"], rows[-1]["date"]], "variants": {}}
    print("\n=== EXPOSURE VARIANTS, ALL PERIODS ===")
    print(HDR)
    base = apply_variant(rows, VARIANTS["baseline"])
    for name, fn in VARIANTS.items():
        rets = apply_variant(rows, fn)
        m = portfolio_lab.metrics(rets)
        touched = sum(1 for r in rows if fn(r) < 1.0)
        d = np.array(rets) - np.array(base)
        t = (float(np.mean(d)) / (float(np.std(d, ddof=1)) / math.sqrt(len(d)))
             if float(np.std(d, ddof=1)) > 0 else 0.0)
        out["variants"][name] = dict(m, touched=touched, t_vs_base=round(t, 2))
        print(line(name, m, f"touch {touched:>2}  t {t:+.2f}"))

    for tag, sl in (("FIRST HALF", slice(0, half)), ("SECOND HALF", slice(half, None))):
        print(f"\n=== {tag} ({rows[sl][0]['date']} .. {rows[sl][-1]['date']}) ===")
        print(HDR)
        for name, fn in VARIANTS.items():
            m = portfolio_lab.metrics(apply_variant(rows[sl], fn))
            out["variants"][name][tag.lower().replace(" ", "_")] = m
            print(line(name, m))

    spy_rets = [r["spy"] for r in rows]
    m = portfolio_lab.metrics(spy_rets)
    out["variants"]["SPY"] = m
    print("\n" + line("SPY (same periods)", m))
    out["windows"] = [{k: v for k, v in r.items() if k != "legs"} for r in rows]
    print("\nRESULT_JSON: " + json.dumps(out))


if __name__ == "__main__":
    main()
