"""Tail lab: the H5 forensics showed the top-2 book's worst windows are
single-name collapses in calm bull markets, not bear markets. This lab
tests the only lever that targets that -- the PER-STOCK exit -- inside
the portfolio backtest, which until now held every pick to the deadline.

Rules simulated on each pick's daily close path (registry H6a-H6f):
  disaster  close <= entry - k * sigma42        (k=2.0 is the shipped rule)
  trailing  close <= running peak - k * sigma42
  breakeven once the pick closes >= +5%, exit on any close <= entry
  replace   after an exit, buy the next-ranked unheld name from the same
            scan at that close and run the same rules to the deadline
  weights   equal (50/50) or inverse-sigma42 (risk parity)

Cash after an exit earns 0 for the rest of the window. No shorting, no
leverage, no profit target (a +5% target was already proven to destroy
the edge -- see exitlab / BACKTEST-REPORT.md).

Usage: python -m scout.tail_lab [--universe sp1500] [--n 2]
"""
import argparse
import json
import math

import numpy as np
import pandas as pd

from . import config, portfolio_lab

H = config.HORIZON_TDAYS


def leg_return(path, sigma, rule):
    """One pick's realized return under `rule`, plus the exit day index
    (None = held to the deadline). path: array of price/entry - 1."""
    dis = rule.get("disaster")
    trail = rule.get("trail")
    be = rule.get("breakeven")
    peak = 0.0
    armed = False
    for i, r in enumerate(path):
        peak = max(peak, r)
        if r >= config.TARGET_GAIN:
            armed = True
        if dis is not None and r <= -dis * sigma:
            return r, i
        if trail is not None and r <= peak - trail * sigma:
            return r, i
        if be and armed and r <= 0.0:
            return r, i
    return (float(path[-1]), None) if len(path) else (0.0, None)


def window_return(c, scan, n, rule, weight="equal"):
    """Portfolio return for one window under `rule`."""
    pos = scan["pos"]
    basis = c.iloc[pos]
    win = c.iloc[pos + 1: pos + 1 + H]
    picks, used = [], set()
    for sym in scan["ranked"]:
        if len(picks) >= n:
            break
        if sym not in win.columns or pd.isna(basis.get(sym)):
            continue
        seg = (win[sym] / basis[sym]).dropna()
        if len(seg) < 5:
            continue
        picks.append(sym)
        used.add(sym)
    if not picks:
        return 0.0, 0
    sig = {s: scan["sigma42"].get(s) or 0.12 for s in picks}
    if weight == "invvol":
        raw = {s: 1.0 / sig[s] for s in picks}
        tot = sum(raw.values())
        w = {s: raw[s] / tot for s in picks}
    else:
        w = {s: 1.0 / len(picks) for s in picks}

    total, stops = 0.0, 0
    for sym in picks:
        seg = (win[sym] / basis[sym]).dropna().values - 1.0
        r, exit_i = leg_return(seg, sig[sym], rule)
        if exit_i is not None:
            stops += 1
            if rule.get("replace"):
                # redeploy this leg's remaining capital into the best
                # ranked name not already used, entered at the exit close
                r = _replace(c, scan, win, exit_i, used, sig, rule, r)
        total += w[sym] * r
    return total, stops


def _replace(c, scan, win, exit_i, used, sig, rule, r_so_far):
    """Compound the stopped leg into the next-ranked available name,
    entered at the close of the exit day, same rules, to the deadline."""
    capital = 1.0 + r_so_far
    for _ in range(2):                       # at most two replacements
        nxt = None
        for sym in scan["ranked"]:
            if sym in used or sym not in win.columns:
                continue
            sub = win[sym].iloc[exit_i:].dropna()
            if len(sub) >= 3:
                nxt = (sym, sub)
                break
        if nxt is None:
            break
        sym, sub = nxt
        used.add(sym)
        s = scan["sigma42"].get(sym) or 0.12
        # scale sigma to the shorter remaining horizon
        s = s * math.sqrt(max(len(sub), 1) / H)
        seg = sub.values / float(sub.values[0]) - 1.0
        r2, e2 = leg_return(seg[1:], s, rule)
        capital *= (1.0 + r2)
        if e2 is None:
            break
        exit_i = exit_i + 1 + e2
    return capital - 1.0


RULES = {
    "baseline hold to deadline": ({}, "equal"),
    "H6a disaster 2.0sig":       ({"disaster": 2.0}, "equal"),
    "H6b disaster 2.0 +replace": ({"disaster": 2.0, "replace": True}, "equal"),
    "H6c breakeven after +5%":   ({"breakeven": True}, "equal"),
    "H6ac disaster+breakeven":   ({"disaster": 2.0, "breakeven": True}, "equal"),
    "H6d trailing 1.5sig":       ({"trail": 1.5}, "equal"),
    "H6d' trailing 2.0sig":      ({"trail": 2.0}, "equal"),
    "H6e invvol weights":        ({}, "invvol"),
    "H6ae disaster + invvol":    ({"disaster": 2.0}, "invvol"),
    "H6f disaster 1.5sig":       ({"disaster": 1.5}, "equal"),
    "H6f disaster 2.5sig":       ({"disaster": 2.5}, "equal"),
    "H6f disaster 3.0sig":       ({"disaster": 3.0}, "equal"),
}

HDR = (f"{'strategy':<28}{'periods':>8}{'avg%':>7}{'>=+5%':>7}{'pos%':>6}"
       f"{'worst%':>8}{'maxDD%':>8}{'compounded%':>12}")


def line(name, m, extra=""):
    return (f"{name:<28}{m['periods']:>8}{m['avg']:>7}{m['pct_ge5']:>7}"
            f"{m['pct_pos']:>6}{m['worst']:>8}{m['max_dd']:>8}"
            f"{m['compounded']:>12}  {extra}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.tail_lab")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    c, idx, scans = portfolio_lab.collect(args.universe, args.start, args.end)
    stride = max(1, math.ceil(H / 21))
    sel = scans[::stride]
    print(f"\n{len(sel)} non-overlapping windows, top-{args.n}, "
          f"{sel[0]['date']} .. {sel[-1]['date']} ({args.universe})\n")

    results, out = {}, {"universe": args.universe, "n": args.n,
                        "span": [sel[0]["date"], sel[-1]["date"]],
                        "strategies": {}}
    for name, (rule, weight) in RULES.items():
        rets, stops = [], 0
        for scan in sel:
            r, s = window_return(c, scan, args.n, rule, weight)
            rets.append(r)
            stops += s
        results[name] = (rets, stops)

    base = results["baseline hold to deadline"][0]
    half = len(sel) // 2
    print("=== ALL PERIODS ===")
    print(HDR)
    for name, (rets, stops) in results.items():
        m = portfolio_lab.metrics(rets)
        d = np.array(rets) - np.array(base)
        sd = float(np.std(d, ddof=1))
        t = (float(np.mean(d)) / (sd / math.sqrt(len(d)))) if sd > 0 else 0.0
        out["strategies"][name] = dict(m, stops=stops, t_vs_base=round(t, 2))
        print(line(name, m, f"stops {stops:>3}  t {t:+.2f}"))

    for tag, sl in (("FIRST HALF", slice(0, half)),
                    ("SECOND HALF", slice(half, None))):
        print(f"\n=== {tag} ({sel[sl][0]['date']} .. {sel[sl][-1]['date']}) ===")
        print(HDR)
        for name, (rets, _) in results.items():
            m = portfolio_lab.metrics(rets[sl])
            out["strategies"][name][tag.lower().replace(" ", "_")] = m
            print(line(name, m))

    print("\n=== WORST 6 BASELINE WINDOWS, UNDER EACH RULE ===")
    order = sorted(range(len(sel)), key=lambda i: base[i])[:6]
    keys = ["baseline hold to deadline", "H6a disaster 2.0sig",
            "H6b disaster 2.0 +replace", "H6ac disaster+breakeven",
            "H6d trailing 1.5sig", "H6ae disaster + invvol"]
    print(f"{'entry':<12}" + "".join(f"{k.split()[0]:>12}" for k in keys))
    for i in order:
        print(f"{sel[i]['date']:<12}" +
              "".join(f"{results[k][0][i]*100:>12.1f}" for k in keys))

    print("\nRESULT_JSON: " + json.dumps(out))


if __name__ == "__main__":
    main()
