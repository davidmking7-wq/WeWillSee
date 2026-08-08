"""Per-stock features for a ~2-month horizon (engine v4), built as full
time-series frames so one computation serves both today's scan and historical
calibration (bit-identical pipelines — a calibration on a different pipeline
is worthless).

Lineage. 2014-2017 monthly panel (38 non-crash entry dates, exact HIT rule):
  v1 (original):                         hit 56.3% | avg 42td +4.01% | beat mkt 31/38
  v2 (+ 6m mom, smooth tilt, abs-mom gate): 61.1% | +4.42% | 29/38
  v3 (+ near-breakout, lottery-spike gate): 61.1% | +4.63% | 30/38 | med 16d to +5%
v4 (2026-08): drop the gap/volume-surge signal from the score, weight to 6-1
momentum. Chosen by train/holdout protocol on 2016-2026 SIP data (train
2017-2021: hit 66.0 vs 64.9, gain/speed/safety all better; holdout 2022-2026:
hit ~equal, gain and speed better). See SCOUT-DESIGN.md for the full record.
The gap feature is still computed as research context — it just earns no
score weight.

Ablation notes — tried and REJECTED, do not re-add:
  - MSCI risk-adjusted momentum (mom/vol): hit rate DOWN 1.6pp. Dividing by
    vol tilts to calm names, but touching +5% inside 42 trading days NEEDS
    movement (that's why VOL_BAND exists). Objective mismatch.
  - Monthly-consistency score (Grinblatt-Moskowitz): hit rate DOWN 3.7pp.
  - Sector-relative momentum blend, 20d-high hard gate: no train edge (2026-08 lab).
  - 5-day pullback veto: hurt gain and speed (2026-08 lab).

Core ranks: 12-1 and 6-1 momentum, 52-week-high proximity, smooth-path tilt,
near-breakout. Hard gates: SMA200, positive 6-month return (absolute
momentum). Vetoes: 1-month extremes, top vol decile, top-decile single-day
spike (lottery stocks).
"""
import numpy as np
import pandas as pd

from . import config


def feature_frames(o: pd.DataFrame, c: pd.DataFrame, v: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Each value is a time × symbol DataFrame aligned to c's index."""
    ret = c.pct_change()
    mom = c.shift(21) / c.shift(252) - 1
    mom6 = c.shift(21) / c.shift(126) - 1
    ret6 = c / c.shift(126) - 1
    ret1m = c / c.shift(21) - 1
    high_prox = c / c.rolling(252, min_periods=200).max()
    brk20 = c / c.rolling(20, min_periods=10).max()
    sma50ok = (c > c.rolling(50).mean()).astype(float)
    sma200ok = (c > c.rolling(200).mean()).astype(float)
    vol63 = ret.rolling(63).std() * np.sqrt(252)
    pos252 = (ret > 0).rolling(252, min_periods=200).mean()
    max21 = ret.rolling(21).max()

    gap_ret = o / c.shift(1) - 1
    vol_med = v.rolling(20, min_periods=10).median()
    surge = (gap_ret >= 0.03) & (v >= 2 * vol_med)
    gapmag = gap_ret.where(surge, 0.0)
    gap = gapmag.rolling(20, min_periods=1).max().clip(0, 0.06) / 0.06

    return {"mom": mom, "mom6": mom6, "ret6": ret6, "ret1m": ret1m,
            "high": high_prox, "brk20": brk20, "sma50ok": sma50ok,
            "sma200ok": sma200ok, "vol": vol63, "gap": gap,
            "pos252": pos252, "max21": max21}


def composite_at(frames: dict[str, pd.DataFrame], ts) -> pd.DataFrame:
    """Cross-sectional composite (0-100) at one timestamp, after gates/vetoes.
    Stocks failing a hard gate or hitting a veto are dropped entirely —
    identically at scan time and in calibration."""
    row = {k: f.loc[ts] for k, f in frames.items()}
    df = pd.DataFrame(row).dropna(subset=["mom", "mom6", "high", "vol",
                                          "ret1m", "max21", "pos252", "brk20"])
    if df.empty:
        return df

    vol_decile = df["vol"].rank(pct=True)
    max_decile = df["max21"].rank(pct=True)
    keep = ((df["sma200ok"] == 1.0)
            & (df["ret6"] > 0)                          # absolute momentum
            & (df["ret1m"] <= config.VETO_RET1M_HI)
            & (df["ret1m"] >= config.VETO_RET1M_LO)
            & (vol_decile < config.VETO_VOL_DECILE)
            & (max_decile < config.VETO_MAX21_DECILE))  # no lottery spikes
    df = df[keep]
    if df.empty:
        return df

    mom_pct = df["mom"].rank(pct=True)
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
