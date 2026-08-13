"""Variant lab: candidate engine upgrades, tested train/holdout to avoid
data snooping. NOT part of the shipped pipeline — a research harness.

Protocol (documented in SCOUT-DESIGN.md):
- TRAIN --start 2017-01-01 --end 2021-12-31 (first usable entry ~2017-07
  after the warmup): run every candidate, compare to the v3 control.
- HOLDOUT --start 2022-01-01: run ONLY the survivors, once. What survives
  the holdout ships; what doesn't is documented as rejected.
- Selection metric: the user's objective — gain x speed x safety subject to
  hit-rate not degrading (hit%, mean max gain, median days, dip-first rate).
- Honesty limit: the holdout is single-shot but the ship decision itself
  conditions on it, and both eras share the survivorship universe — this
  protocol reduces snooping, it does not eliminate it.

2026-08 round (v3 control): NOGAP won train AND holdout and shipped as v4;
SECREL and TIGHTHIGH were washes; PULLBACK hurt gain and speed. The control
is now v4 (the current signals module).

Variants (each a single literature-grounded change on top of the control):
  SECREL     half the 12-1 momentum rank becomes sector-relative
             [Moskowitz-Grinblatt industry momentum; Da-Schaumburg]
             (known artifact: rank is computed post-gate, so a sector with
             one survivor gets pct 1.0 — fine for a coarse A/B, would need
             pre-gate ranking if it ever shipped; no train edge 2026-08)
  PULLBACK   veto stocks up >4% over the last 5 sessions (don't chase
             micro-spikes) [Jegadeesh 1990] (hurt gain+speed 2026-08)
  TIGHTHIGH  hard gate: within 20% of the 52-week high
             [George-Hwang 2004] (no train edge 2026-08)
  COMBO      surviving variants combined (run only after train results)

Usage:
  python -m scout.labtest --variant SECREL --start 2017-01-01 --end 2021-12-31
  python -m scout.labtest --variant COMBO --combo SECREL,NOGAP --start ...
Prints a human table plus a final machine-readable JSON line.
"""
import argparse
import json

import numpy as np
import pandas as pd

from . import backtest, config, signals, universe


def _sector_map() -> pd.Series:
    uni = universe.load()
    return pd.Series({u["symbol"]: u["sector"] or "Unknown" for u in uni})


def build_engine(secrel=False, pullback=False, tighthigh=False):
    """Parameterized engine derived from the current signals module (v4).
    Each flag is one variant change; no flags = the shipped engine's shape."""
    sectors = _sector_map() if secrel else None

    def feature_frames(o, c, v):
        frames = signals.feature_frames(o, c, v)
        if pullback:
            frames["ret5"] = c / c.shift(5) - 1
        return frames

    def composite_at(frames, ts):
        row = {k: f.loc[ts] for k, f in frames.items()}
        df = pd.DataFrame(row).dropna(subset=["mom", "mom6", "high", "vol",
                                              "ret1m", "max21", "pos252",
                                              "brk20"])
        if df.empty:
            return df
        vol_decile = df["vol"].rank(pct=True)
        max_decile = df["max21"].rank(pct=True)
        keep = ((df["sma200ok"] == 1.0)
                & (df["ret6"] > 0)
                & (df["ret1m"] <= config.VETO_RET1M_HI)
                & (df["ret1m"] >= config.VETO_RET1M_LO)
                & (vol_decile < config.VETO_VOL_DECILE)
                & (max_decile < config.VETO_MAX21_DECILE))
        if pullback:
            keep &= df["ret5"] <= 0.04
        if tighthigh:
            keep &= df["high"] >= 0.80
        df = df[keep]
        if df.empty:
            return df

        mom_pct = df["mom"].rank(pct=True)
        if secrel:
            sec = sectors.reindex(df.index).fillna("Unknown")
            mom_sec_pct = df["mom"].groupby(sec).rank(pct=True)
            mom_pct = 0.5 * mom_pct + 0.5 * mom_sec_pct
        mom6_pct = df["mom6"].rank(pct=True)
        high_pct = df["high"].rank(pct=True)
        smooth_pct = df["pos252"].rank(pct=True)
        brk_pct = df["brk20"].rank(pct=True)
        lo, hi = config.VOL_BAND
        below = ((lo - df["vol"]) / 0.10).clip(lower=0)
        above = ((df["vol"] - hi) / 0.25).clip(lower=0)
        vol_band = (1 - pd.concat([below, above], axis=1).max(axis=1)).clip(0, 1)
        r1_pct = df["ret1m"].rank(pct=True)
        guard = 1 - ((r1_pct - 0.8).clip(lower=0) * 5)

        df["score"] = 100 * (config.W_MOM12 * mom_pct
                             + config.W_MOM6 * mom6_pct
                             + config.W_HIGH * high_pct
                             + config.W_SMOOTH * smooth_pct
                             + config.W_BRK20 * brk_pct
                             + config.W_VOL * vol_band
                             + config.W_GUARD * guard
                             + config.W_SMA50 * df["sma50ok"])
        df["mom_pct"] = mom_pct
        return df.sort_values("score", ascending=False)

    return feature_frames, composite_at


VARIANTS = {
    "v4": {},
    "SECREL": {"secrel": True},
    "PULLBACK": {"pullback": True},
    "TIGHTHIGH": {"tighthigh": True},
}


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.labtest")
    ap.add_argument("--variant", required=True,
                    help="one of " + ", ".join(VARIANTS) + ", or COMBO")
    ap.add_argument("--combo", default="",
                    help="comma-separated variant names to combine (COMBO only)")
    ap.add_argument("--picks", type=int, default=5)
    ap.add_argument("--step", type=int, default=21)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    if args.variant == "COMBO":
        flags = {}
        for name in args.combo.split(","):
            name = name.strip()
            if name not in VARIANTS or not VARIANTS[name]:
                raise SystemExit(f"bad combo member: {name!r}")
            flags.update(VARIANTS[name])
        label = "COMBO(" + args.combo + ")"
    elif args.variant in VARIANTS:
        flags = VARIANTS[args.variant]
        label = args.variant
    else:
        raise SystemExit(f"unknown variant {args.variant!r}")

    ff, comp = build_engine(**flags)
    out = backtest.run(args.picks, args.step, no_cache=False,
                       start=args.start, end=args.end,
                       engines={label: (ff, comp)}, out_path=None)
    summary = {"variant": label, "span": out["span"],
               "all": out["engines"][label]["all"],
               "non_overlapping": out["engines"][label]["non_overlapping"],
               "bull": out["engines"][label]["bull"],
               "bear": out["engines"][label]["bear"]}
    print("\nRESULT_JSON: " + json.dumps(summary))


if __name__ == "__main__":
    main()
