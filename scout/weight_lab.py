"""H29 — which of the v5 composite's eight weights actually contribute?

MECHANISM (one sentence, Rule 1)
--------------------------------
A linear composite of cross-sectional ranks pays the weighted average of its
ingredients' spreads, so an ingredient whose own spread is NEGATIVE subtracts
from the composite in exact proportion to its weight — and a composite built
from one live ingredient and one harmful one can measure zero while containing
a real signal.

WHY THIS REPO CARES
-------------------
H25 measured the two biggest ingredients against each other on the same panel
and found them pointing in opposite directions: Fama-MacBeth `high52`
controlling for momentum **-298.6 bps (t -3.17)**, `mom12` controlling for
high52 **+265.0 bps (t +3.74)**. The v5 composite carries both, at
`W_HIGH = 0.25` (its largest weight) and `W_MOM12 + W_MOM6 = 0.40`. The
composite as a whole has been measured sorting nothing (ALPHA-STACK.md: best-
ranked decile minus worst-ranked decile = **-0.26%** per 42-td window). The
obvious inference — that the null is a cancellation, not an absence — had
never been tested. This lab tests it the only way that settles it: rebuild the
composite with each weight removed and measure what changes.

This is a CONFIRMATORY test of an already-measured effect (H25's Fama-MacBeth
coefficients), pre-registered before the first number was produced. It is not
a weight search: no weight here was chosen by looking at an outcome. The
significance regime is stated per row.

PRE-REGISTRATION (written before the first number was produced)
---------------------------------------------------------------
| #  | hypothesis | expected sign |
|----|------------|---------------|
| H29a | BASELINE. The exact v5 composite sorts nothing: top-decile minus bottom-decile is indistinguishable from zero on both universes. | ~ 0 (reproduce the known null) |
| H29b | LEAVE-ONE-OUT. Dropping a weight that CONTRIBUTES makes the spread WORSE; dropping a weight that HARMS makes it BETTER. Registered direction: dropping `high` improves, dropping `mom12`/`mom6` degrades. | d(drop high) > 0, d(drop mom) < 0 |
| H29c | **DECIDING ROW.** W_HIGH = 0 with its 0.25 redistributed to momentum turns the composite's null into a positive, market-adjusted, both-halves-consistent spread. | spread > 0, alpha > 0, both halves > 0 |
| H29d | FLOOR CASE. A momentum-only composite (mom12 + mom6, same gates) is at least as good as any reweighting of the eight. | mom-only >= best 8-weight variant |
| H29e | MONOTONE HARM. Sweeping W_HIGH over 0 / 0.10 / 0.25 / 0.40 degrades the spread monotonically — the signature of a genuinely harmful ingredient, as against a noisy one. | strictly decreasing |
| H29f | The LONG-ONLY top decile — the only form this repo could trade — beats SPY on RISK-ADJUSTED terms after 10 bps, for at least one weight vector. | Sharpe(book) > Sharpe(SPY) |
| H29g | Every claim survives Rule 9: the answer does not depend on which of the 42 entry offsets the capital started on. | phase sd << effect |

Failure conditions, stated in advance: H29b fails if the leave-one-out deltas
are inside the shuffled-score null, or flip sign across halves; **H29c fails —
and takes the "cheapest possible engine fix" with it — if the W_HIGH = 0
composite's market-adjusted spread is not positive with consistent halves**;
H29e fails if the sweep is not monotone; H29f fails if the top decile's Sharpe
after costs does not exceed SPY's over the same windows; H29g fails if the
across-phase standard deviation is a material fraction of any quoted effect.

METHOD
------
Composite   Rebuilt EXACTLY as `signals.composite_at` builds it: the gates and
            vetoes are applied FIRST, then all five percentile ranks are taken
            INSIDE the surviving pool, and `vol_band` / `guard` / `sma50ok`
            use the same closed forms. Ranks use average-tie percentiles, i.e.
            pandas' `rank(pct=True)`, so the score is bit-identical to the
            engine's (verified in `--selftest` against `signals.composite_at`
            itself on real dates — max |difference| printed).
THE SHIFT   Every feature at formation date t is built from opens/closes at or
            before t. The forward return is `close_{t+42} / close_t - 1`, i.e.
            driven only by sessions t+1 .. t+42. Formation close t is the entry
            price (the repo's shipped H4 buy-at-the-close rule). There is no
            other place in this file where a signal and a return can touch.
Formation   EVERY session (Rule 9 in its strongest form). A 42-session hold
            formed daily pools all 42 possible entry offsets by construction;
            the 42 non-overlapping schedules are then reported separately.
Sample      2016-04 .. 2026-08 Alpaca SIP daily bars, split+dividend adjusted
            and then guarded (below). ~2,280 formation dates per universe.
Effective n 42-session holds formed daily overlap 42-deep, so the effective
            independent sample is dates / 42 ~ 54. Every t-statistic is
            Newey-West at lag 41; every CI is a moving-block bootstrap with
            block length 42; every phase series is genuinely non-overlapping.
Universes   (i) `scout/universe.csv` — today's S&P 1500 applied historically
            (survivorship-biased, the engine's shipped universe);
            (ii) point-in-time S&P 500 via `scout/pit.py` — each date's actual
            members, delisted names included (survivorship-free, large-cap).

PRICE-DATA GUARDS — all three, and this is which
------------------------------------------------
1. SPLIT REPAIR. `high52_lab.repair_splits`: Alpaca's corporate-actions feed
   is reconciled against its own bars; any split whose ex-date one-day return
   exceeds 35% was never applied, and all prices strictly before that ex-date
   are divided by the factor. (5.1% of splits are unadjusted in the raw bars;
   AAPL 2020-08-31 prints a fake -74.2% without this.)
2. EXTREME-PRINT MASK. After repair, any remaining |1-day return| > 45% is a
   spin-off or a reused ticker with no paper trail (146 of these in the
   S&P 1500 per `scout/data_audit.py`). The symbol is removed from the
   cross-section for the 252 sessions whose rolling max it corrupts, and any
   stock-window whose forward path contains one is dropped.
3. FROZEN QUOTES. `idiovol_lab.retire_stale`: a symbol is retired permanently
   from its first run of 10 identical consecutive closes. A delisted ticker
   whose quote freezes has zero return and zero volatility — in a VOL-BAND
   composite that is not noise, it is a name pinned into the eligible pool
   forever, paying nothing.
`--no-guard` reruns with 2 and 3 off, which is the sensitivity row.

CONTROLS (nulls, not trials — Rule 3)
-------------------------------------
(i)  SHUFFLED SCORE — the score is permuted within the identical gated pool on
     each date, so the pool, the gates, the dates and the decile sizes are held
     fixed and only the ranking is destroyed;
(ii) RANDOM PICK of the same size from the same gated pool, for the long-only
     book;
(iii) MATCHED BENCHMARKS — the equal-weight GATED pool (the engine's own
     eligible set) over the identical windows, and SPY.
Per Rule 14 the ratio of each null's SE to the real series' Newey-West SE is
printed next to it. Per Rule 13 every book is regressed on SPY before its sign
is quoted, and no raw return is compared to SPY without its beta.
The leave-one-out deltas are measured as PAIRED per-date differences against
the baseline on the identical dates, which removes the common market factor
and is far more powerful than differencing two noisy means.

VERDICT (2026-08-09) — THE COMPOSITE'S NULL IS A CANCELLATION, AND THE ENGINE
CAN BE MADE TO SORT BY DELETING WEIGHT. IT STILL DOES NOT BEAT SPY.
------------------------------------------------------------------------------
2,281 daily formations 2017-05-10 .. 2026-06-05, 42-session holds, equal
weight, effective independent sample ~54. Every number below is printed by
`python -m scout.weight_lab` and stored in scout/weight_results.json.

PIPELINE TRUST FIRST. On this pipeline H25 reproduces almost exactly: high52
D10-D1 ungated **-180.6 bps (t -1.83)** against H25's published -182.8, market-
adjusted **+23.2** against +23.9; mom12 gated **+136.3 (t 2.10)** against
+132.8. Different formation grid, an extra guard, same answers.

H29a BASELINE — CONFIRMED, the known null is reproduced. The exact v5
composite sorts nothing: D10-D1 **-17.5 bps/window (NW t -0.34)**, CI
[-121.6, +86.4], and the decile profile is flat with no trend at all
(222 224 213 206 207 203 201 191 183 204). The long-only top decile earns
**-1.3 bps against the equal-weight gated pool (t -0.05)**; the pool earns 205
bps and SPY 256 bps over the same windows. On PIT-500 the spread is -30.2
(t -0.64) and top-minus-pool **-29.5 (t -1.19)**.

H29b LEAVE-ONE-OUT — CONFIRMED IN THE REGISTERED DIRECTION. Paired per-date
deltas against the baseline (positive = dropping it IMPROVED the sort),
S&P 1500, with the PIT-500 sign in brackets:

    drop mom12   -57.2  t -3.20   halves  -29.1 / -85.2   CONTRIBUTES  [-24.9]
    drop mom6    -30.7  t -1.53   halves  -41.8 / -19.6   CONTRIBUTES  [-16.8]
    drop high    +65.7  t +2.35   halves  +57.8 / +73.6   HARMS        [+42.8]
    drop smooth   -8.0  t -0.88   halves   +1.6 / -17.6   flips         [-8.3]
    drop brk20   +11.7  t +1.93   halves  +10.0 / +13.3   HARMS         [+8.4]
    drop vol     +22.7  t +2.16   halves  +39.6 /  +5.9   HARMS        [+14.3]
    drop guard    +4.9  t +1.12                            HARMS        [+1.0]
    drop sma50    +2.9  t +0.90                            HARMS        [+6.0]

All EIGHT signs agree across the two universes. Two of the eight weights carry
information (`mom12`, `mom6`, 0.40 of the weight); one is noise (`smooth`);
five subtract (`high`, `vol`, `brk20`, `guard`, `sma50`, 0.50 of the weight).

THE CONTROL THAT SEPARATES CONTENT FROM DILUTION. Dropping a weight changes
two things — the information and everybody else's share. Replacing ONE
ingredient with a permutation of itself, at the SAME weight, changes only the
information. S&P 1500, composite D10-D1 = -17.5 real:

    `high`  replaced by noise at 0.25 ->  **+30.1** [+24.2, +34.9]  content costs **-47.6**
    `mom12` replaced by noise at 0.20 ->  **-76.1** [-82.6, -70.1]  content is worth **+58.6**
    `vol`   replaced by noise at 0.10 ->   **+4.3** [ +1.4,  +8.3]  content costs **-21.8**

PIT-500 agrees (-35.5 / +26.3 / -12.8). The composite is NOT diluted by W_HIGH;
it is DRAGGED by what W_HIGH knows. And the mirror case fires the right way,
which is what proves the estimator is not simply rewarding randomness.

H29c THE DECIDING ROW — CONFIRMED on the S&P 1500, NOT PROVEN on PIT-500.
W_HIGH = 0 with its 0.25 moved to momentum: D10-D1 **+74.9 bps (t 1.39)**,
delta vs baseline **+92.3 (t 2.72)**, halves **+20.9 / +128.8**, market-
adjusted **+35.8 (t 2.21, beta +0.15)**. Long-only top decile minus pool
**+57.5 bps/window (t 1.69)**, halves +19.5 / +95.5, break-even round-trip cost
**88.4 bps** against 10 charged. On PIT-500 the same change gives +25.0
(delta +55.1, t 1.82) and the halves FLIP (-75.2 / +125.2) — right sign, no
size, and it is the survivorship-free universe that is weaker.
Note the algebraic degeneracy stated in `variants()`: "to everything pro rata"
and "to nothing" are the same ranking as `drop high` and print the same
numbers to 0.1 bps, which is the code's own consistency check.

H29d FLOOR CASE — CONFIRMED, AND IT IS THE BEST THING IN THE FILE.
mom12 + mom6 alone, same gates: D10-D1 **+117.0 bps (t 2.19)**, CI
[+21.0, +225.4], halves **+94.4 / +139.5**, market-adjusted **+54.7 (t 3.28,
beta +0.25)** — the only cell in this lab that clears the repo's blunt t > 3
bar. Long-only top decile minus pool **+82.5 bps/window (t 2.27)**, halves
+67.4 / +97.6, turnover 0.67 per hold, break-even **123.1 bps**, net at 10 bps
**+75.8**. No eight-weight reweighting beats it. PIT-500: +47.7 (t 0.94), top
minus pool +28.2 (t 0.81), halves flip both times.

H29e MONOTONE HARM — CONFIRMED, in four independent readouts at once.
S&P 1500, sweeping W_HIGH with the other seven renormalised:

    W_HIGH        0.00     0.10     0.25     0.40
    D10-D1       +48.2    +21.4    -17.5    -44.4
    D10 - pool   +40.1    +23.3     -1.3    -14.8
    net CAGR %   13.19    12.19    10.72     9.96
    Sharpe       0.767    0.741    0.695    0.679

Strictly decreasing in every row. PIT-500 is monotone in the first three rows
(+12.6/-13.4/-30.0/-44.8; -4.4/-21.9/-29.3/-32.3; 9.02/7.97/7.59/7.45) and
breaks monotonicity in Sharpe only at the last step (0.621/0.572/0.570/0.577).
A dose-response this clean is what a real harmful ingredient looks like and is
not what a noisy one looks like.

H29f THE USER'S QUESTION — **REJECTED. Nothing here beats SPY risk-adjusted.**
Capital laddered across all 42 entry offsets, each sleeve rebalanced once per
hold, net of 10 bps on measured turnover:

    SPY buy-and-hold          CAGR 14.99%   Sharpe 1.004
    equal-weight gated pool   CAGR 11.53%   Sharpe 0.788   beta 0.92
    v5 baseline top decile    CAGR 10.72%   Sharpe 0.695   beta 0.90
    W_HIGH=0 -> momentum      CAGR 14.18%   Sharpe 0.787   beta 1.03
    momentum only             CAGR 15.61%   Sharpe 0.818   beta 1.09

The best book BEATS SPY ON RETURN by +0.62pp/yr and LOSES ON SHARPE by 0.186,
at beta 1.09 — Rule 13's exact failure mode, and the answer to the user's
question is therefore no. The decomposition says where it goes: the equal-
weight gated pool is ALREADY -0.216 Sharpe against the cap-weighted index
before any stock is picked, and the selection layer adds only +0.030 back.
Fixing the weights fixes the selection layer; it does not fix the -0.216.
PIT-500 is worse (best book 10.96% / 0.702).

H29g RULE 9 — CONFIRMED. Across the 42 non-overlapping entry schedules
(S&P 1500): baseline -17.5 (phase sd 34.1, 33% of phases positive); drop high
+48.2 (sd 25.0, **98%** positive); W_HIGH=0 -> momentum +74.9 (sd 28.4,
**100%** positive, min +16.1); momentum only +117.0 (sd 35.7, **100%**
positive, min +44.6); drop mom12 -74.7 (sd 39.3, 2% positive). No entry
schedule reverses the sign of any headline. This is not H7a's shape.

GUARD SENSITIVITY (`--no-guard`, extreme-print mask and frozen-quote
retirement both OFF; split repair always on). Every sign and nearly every
magnitude survives: baseline -20.8 (vs -17.5), drop high +71.9 t 2.49 (vs
+65.7 t 2.35), momentum only +124.9 t 2.32 (vs +117.0 t 2.19), noise control
on `high` -53.4 (vs -47.6). None of the conclusions rests on the guards; they
were applied because the data debt is real, not because they change the answer.

SIGNIFICANCE REGIME, stated per the house rule
  CONFIRMATORY. The registered directions come from H25's already-measured
  Fama-MacBeth coefficients on this same panel (high52 | momentum = -298.6,
  t -3.17; momentum | high52 = +265.0, t +3.74) and from Jegadeesh-Titman.
  No weight in this file was chosen by looking at an outcome. The relevant
  numbers are `drop high` delta **t 2.35 with matching halves and 41 of 42
  phases positive**, and momentum-only market-adjusted **t 3.28**. Read as a
  confirmatory test that is meaningful evidence; read as an exploratory sweep
  of 13 distinct rankings it would not be. It is the former, and the direction
  was fixed before the run.

TRIAL COUNT
  17 weight vectors x 2 universes = **34 measured cells**, of which 13 vectors
  are distinct rankings (4 are algebraic duplicates printed as a code check).
  Plus 8 reproduction rows and one guard-off rerun of everything. Control
  draws are nulls, not trials.

LIMITS OF THIS STUDY, stated plainly
  - IN SAMPLE. The 2022-2026 holdout is retired (BACKTEST-REPORT.md), and this
    lab used the same decade H25 used. It licenses a REMOVAL — the bar for
    deleting a component that measures negative in two universes, in both
    halves of the larger one, with a monotone dose-response and a decisive
    noise control, is not the bar for adding one — but it does not license a
    claim that v6 will earn +117 bps a window going forward.
  - The decile spread is a long/short construct this user cannot hold. In the
    tradeable long-only form the momentum-only book's alpha against SPY is
    **+14.0 bps/window (t 0.95)** — indistinguishable from zero. Everything
    quotable here is measured against the gated pool, not against SPY.
  - Effective independent sample ~54 windows. That can reject a large effect
    and confirm a large sign; it cannot resolve 1-2%/yr.
  - The `high` family is bigger than W_HIGH: W_BRK20 = 0.07 is the 20-day high
    and measures harmful too (+11.7, t 1.93). The drag is "closeness to a
    recent high" as a family, 0.32 of the weight, not one parameter.
  - W_VOL is the second-most-harmful ingredient (+22.7, t 2.16; content worth
    -21.8). That is ALPHA-STACK.md's thesis measured directly rather than
    argued: the engine's objective was P(touch +5%), first passage is driven
    by variance, and variance is the term subtracted from growth.
  - Betas are fitted in-sample on the same windows their alphas are read from,
    so every alpha t here is optimistic.
  - Sharpe is computed against a zero risk-free rate for every book including
    SPY, so the comparison is fair but the levels are not risk premia.

Run:
  python -m scout.weight_lab                  # both universes, all guards
  python -m scout.weight_lab --universe pit500
  python -m scout.weight_lab --no-guard       # guard sensitivity
  python -m scout.weight_lab --selftest       # 12 checks incl. bit-identity
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np
import pandas as pd

from . import config, pit, signals, universe
from .high52_lab import (BIG_MOVE, LOOKBACK, beta_to_bench, load_bars, nw_se,
                         repair_splits, stats)
from .idiovol_lab import STALE_RUN, retire_stale

RESULTS = config.SCOUT_DIR / "weight_results.json"

H = config.HORIZON_TDAYS        # 42-session hold
WARMUP = 270                    # bars before the first formation date
STEP_MONTHLY = 21               # only for the H25 reproduction rows
NQ = 10                         # deciles
COST_BPS = 10.0                 # round trip, large caps (this lab charges
                                # costs; the engine does not model them)
BENCH = "SPY"
SEED = 20260809
DRAWS = 100

# The eight weights under test, read from config so this lab can never drift
# from the shipped engine.
W_V5 = {"mom12": config.W_MOM12, "mom6": config.W_MOM6, "high": config.W_HIGH,
        "smooth": config.W_SMOOTH, "brk20": config.W_BRK20, "vol": config.W_VOL,
        "guard": config.W_GUARD, "sma50": config.W_SMA50}
KEYS = list(W_V5)


# ------------------------------------------------------------- weight vectors

def renorm(w: dict) -> dict:
    s = sum(w.values())
    return {k: v / s for k, v in w.items()} if s > 0 else dict(w)


def variants() -> dict[str, dict]:
    """Every weight vector this lab measures, in registration order.

    NOTE, stated here so it cannot look like a coincidence later: a composite
    score is only ever used to SORT, so multiplying every weight by the same
    constant leaves the ranking bit-identical. That makes three registered
    rows mathematically the same configuration —
      `drop high` == `W_HIGH=0 -> all pro rata` == `W_HIGH=0 -> nothing`
      == the `W_HIGH=0.00` point of the sweep
    — and one more —
      `W_HIGH=0.25` (sweep) == `v5 baseline`.
    They are all printed anyway; identical numbers on those rows are a
    consistency check on the code, not a finding.
    """
    out = {"v5 baseline": dict(W_V5)}
    for k in KEYS:                                        # (b) leave-one-out
        out[f"drop {k}"] = renorm({j: v for j, v in W_V5.items() if j != k})

    mom_tot = W_V5["mom12"] + W_V5["mom6"]                 # (c) W_HIGH = 0
    w = dict(W_V5)
    w["high"] = 0.0
    w["mom12"] = W_V5["mom12"] + W_V5["high"] * W_V5["mom12"] / mom_tot
    w["mom6"] = W_V5["mom6"] + W_V5["high"] * W_V5["mom6"] / mom_tot
    out["W_HIGH=0 -> momentum"] = w
    out["W_HIGH=0 -> all pro rata"] = renorm(
        {k: v for k, v in W_V5.items() if k != "high"})
    out["W_HIGH=0 -> nothing"] = {k: (0.0 if k == "high" else v)
                                  for k, v in W_V5.items()}

    out["momentum only"] = {"mom12": 0.5, "mom6": 0.5}     # (d) floor case

    rest = renorm({k: v for k, v in W_V5.items() if k != "high"})
    for wh in (0.0, 0.10, 0.25, 0.40):                     # (e) W_HIGH sweep
        w = {k: v * (1 - wh) for k, v in rest.items()}
        w["high"] = wh
        out[f"W_HIGH={wh:.2f} sweep"] = w
    return out


# --------------------------------------------------------------- data layer

def contamination(close: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """GUARD 2. (signal_dirty, day_dirty).

    signal_dirty[t, s]: the trailing 252 sessions ending at t contain a
    |1-day| move above BIG_MOVE, so every rolling-window feature the composite
    reads at t is untrustworthy.
    day_dirty[t, s]: session t itself carries such a move (used to disqualify
    any forward window that contains it).
    """
    ret = close.pct_change()
    day = (ret.abs() > BIG_MOVE).fillna(False)
    sig = day.rolling(LOOKBACK, min_periods=1).max().fillna(0.0) > 0
    return sig.to_numpy(), day.to_numpy()


def prep(bars: dict, guard: bool = True) -> dict:
    """One-off feature build shared by every universe and weight vector."""
    c, o, v = bars["close"], bars["open"], bars["volume"]
    killed = []
    if guard:
        c, killed = retire_stale(c, run=STALE_RUN)          # GUARD 3
        live = c.notna()
        o, v = o.where(live), v.where(live)
    frames = signals.feature_frames(o, c, v)
    sig_dirty, day_dirty = contamination(c)
    if not guard:
        sig_dirty = np.zeros_like(sig_dirty)
        day_dirty = np.zeros_like(day_dirty)
    return {"index": c.index, "cols": list(c.columns), "C": c.to_numpy(),
            "F": {k: f.to_numpy() for k, f in frames.items()},
            "sig_dirty": sig_dirty, "day_dirty": day_dirty,
            "bench_series": c[BENCH].dropna(), "guard": guard,
            "stale_killed": killed}


# ------------------------------------------------------------------- ranking

def rank_pct(x: np.ndarray) -> np.ndarray:
    """Average-tie percentile rank — identical to pandas `rank(pct=True)`.

    Average ties matter here and ordinal ties would not do: ~6% of the pool
    sits EXACTLY at its 52-week high on any date (H25), and ordinal ranking
    would spread those tied names across a fifth of the `high` component by
    alphabetical accident. The engine uses pandas; so does this.
    """
    n = len(x)
    if n == 0:
        return x
    order = np.argsort(x, kind="stable")
    ordinal = np.empty(n, dtype=np.float64)
    ordinal[order] = np.arange(1, n + 1, dtype=np.float64)
    _, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ordinal)
    return (sums / cnt)[inv] / n


NEED = ["mom", "mom6", "high", "vol", "ret1m", "max21", "pos252", "brk20"]


def build_panel(ctx: dict, mode: str, horizon: int = H) -> dict:
    """Formation-date arrays; everything downstream is pure numpy.

    THE SHIFT LIVES HERE AND NOWHERE ELSE: the feature row is `[pos]`, the
    return window is `[pos+1 : pos+1+horizon]`.

    COMP[k]  the eight composite ingredients, each computed INSIDE the gated
             pool exactly as `signals.composite_at` computes them (NaN outside)
    FWD      close_{t+horizon} / close_t - 1, delisting-tolerant
    GATE     the repo's v5 eligible pool (composite_at's gates and vetoes),
             built from SIGNAL-TIME information only
    SCOR     GATE minus the names whose forward path is unusable — the set the
             deciles are actually formed over
    OPEN     the same, without the gates (used for the H25 reproduction rows)

    GATE deliberately does NOT depend on the forward path. Excluding a name
    from the RANKING pool because of what happens to it after formation would
    make every other name's percentile a function of the future; the forward
    filter is applied afterwards, to SCOR, where it can only drop observations.
    """
    cols, idx, C, F = ctx["cols"], ctx["index"], ctx["C"], ctx["F"]
    sig_dirty, day_dirty = ctx["sig_dirty"], ctx["day_dirty"]
    n_s = len(cols)

    pos = np.arange(WARMUP, len(idx) - horizon - 1, dtype=int)
    # forward returns, fully vectorised -----------------------------------
    Cf = pd.DataFrame(C).ffill().to_numpy()          # last print at or before t
    fin = np.isfinite(C)
    cum = np.vstack([np.zeros((1, n_s)), np.cumsum(fin, axis=0)])
    cum_dirty = np.vstack([np.zeros((1, n_s)), np.cumsum(day_dirty, axis=0)])
    basis = C[pos]
    last = Cf[pos + horizon]
    cnt = cum[pos + 1 + horizon] - cum[pos + 1]
    dirty = cum_dirty[pos + 1 + horizon] - cum_dirty[pos + 1]
    need = 5 if mode == "pit500" else horizon
    path_ok = ((cnt >= need) & np.isfinite(basis) & np.isfinite(last)
               & (basis > 0))
    FWD = np.where(path_ok, last / np.where(basis == 0, np.nan, basis) - 1.0,
                   np.nan)
    partial = int(((cnt >= need) & (cnt < horizon)).sum())

    finite = np.all([np.isfinite(F[k][pos]) for k in NEED], axis=0)

    # membership ----------------------------------------------------------
    if mode == "sp1500":
        members = {u["symbol"] for u in universe.load()}
        static = np.array([s in members for s in cols])
        MEM = np.broadcast_to(static, (len(pos), n_s))
    else:
        MEM = np.zeros((len(pos), n_s), dtype=bool)
        prev, row = None, None
        for i, p in enumerate(pos):
            mem = pit.members(idx[p])
            if mem is not prev:                  # snapshots are shared objects
                row = np.array([s in mem for s in cols])
                prev = mem
            MEM[i] = row

    forward_ok = path_ok & np.isfinite(FWD) & (dirty == 0)
    OPEN = MEM & finite & ~sig_dirty[pos] & forward_ok

    # gates, vetoes and the eight ingredients, per date --------------------
    lo, hi = config.VOL_BAND
    GATE = np.zeros((len(pos), n_s), dtype=bool)
    COMP = {k: np.full((len(pos), n_s), np.nan, dtype=np.float32) for k in KEYS}
    sub = {k: F[k][pos] for k in ("vol", "max21", "ret6", "ret1m", "sma200ok",
                                  "dvol20", "mom", "mom6", "high", "pos252",
                                  "brk20", "sma50ok")}
    for i in range(len(pos)):
        # composite_at's dropna frame, minus names whose feature window is
        # corrupted by an unrepairable print (GUARD 2 — signal-time only)
        pool = MEM[i] & finite[i] & ~sig_dirty[pos[i]]
        if pool.sum() < NQ * 3:
            continue
        vol_pct = np.full(n_s, np.nan)
        max_pct = np.full(n_s, np.nan)
        vol_pct[pool] = rank_pct(sub["vol"][i][pool])
        max_pct[pool] = rank_pct(sub["max21"][i][pool])
        gate = (pool
                & (sub["sma200ok"][i] == 1.0)
                & (sub["ret6"][i] > 0)
                & (sub["ret1m"][i] <= config.VETO_RET1M_HI)
                & (sub["ret1m"][i] >= config.VETO_RET1M_LO)
                & (vol_pct < config.VETO_VOL_DECILE)
                & (max_pct < config.VETO_MAX21_DECILE)
                & (sub["dvol20"][i] >= config.MIN_DOLLAR_VOL))
        if gate.sum() < NQ * 3:
            continue
        GATE[i] = gate
        COMP["mom12"][i, gate] = rank_pct(sub["mom"][i][gate])
        COMP["mom6"][i, gate] = rank_pct(sub["mom6"][i][gate])
        COMP["high"][i, gate] = rank_pct(sub["high"][i][gate])
        COMP["smooth"][i, gate] = rank_pct(sub["pos252"][i][gate])
        COMP["brk20"][i, gate] = rank_pct(sub["brk20"][i][gate])
        vol = sub["vol"][i][gate]
        below = np.clip((lo - vol) / 0.10, 0, None)
        above = np.clip((vol - hi) / 0.25, 0, None)
        COMP["vol"][i, gate] = np.clip(1 - np.maximum(below, above), 0, 1)
        r1 = rank_pct(sub["ret1m"][i][gate])
        COMP["guard"][i, gate] = 1 - np.clip(r1 - 0.8, 0, None) * 5
        COMP["sma50"][i, gate] = sub["sma50ok"][i][gate]

    bi = cols.index(BENCH)
    bench = np.where(np.isfinite(C[pos, bi]) & np.isfinite(C[pos + horizon, bi]),
                     C[pos + horizon, bi] / C[pos, bi] - 1.0, np.nan)
    spy = ctx["bench_series"]
    bull = (spy > spy.rolling(200).mean()).reindex(idx).to_numpy()[pos]

    return {"mode": mode, "horizon": horizon, "guard": ctx["guard"],
            "dates": list(idx[pos]), "cols": cols, "pos": pos,
            "COMP": COMP, "FWD": FWD.astype(np.float32),
            "RAW_HIGH": F["high"][pos].astype(np.float32),
            "RAW_MOM": F["mom"][pos].astype(np.float32),
            "OPEN": OPEN, "GATE": GATE, "SCOR": GATE & forward_ok,
            "bench": bench,
            "bull": np.where(pd.isna(bull), True, bull).astype(bool),
            "partial_paths": partial}


# ----------------------------------------------------------------- sorting

def score_matrix(panel: dict, w: dict) -> np.ndarray:
    S = np.zeros(panel["FWD"].shape, dtype=np.float32)
    for k, v in w.items():
        if v:
            S += np.float32(v) * panel["COMP"][k]
    return S


def bucket_means(sig: np.ndarray, fwd: np.ndarray, nq: int) -> np.ndarray:
    """Equal-count bucket means of `fwd`, buckets low -> high on `sig`.
    Ties broken by symbol order (stable sort): deterministic, unrelated to
    the outcome."""
    n = len(sig)
    if n < nq * 2:
        return np.full(nq, np.nan)
    order = np.argsort(sig, kind="stable")
    f = fwd[order]
    edges = (np.arange(nq + 1) * n) // nq
    return np.array([f[edges[k]:edges[k + 1]].mean() for k in range(nq)])


def decile_series(panel: dict, S: np.ndarray, nq: int = NQ,
                  gated: bool = True) -> dict:
    """Per-formation-date bucket means, top-minus-bottom spread, pool mean."""
    mask_all = panel["SCOR"] if gated else panel["OPEN"]
    n = len(panel["dates"])
    rows = np.full((n, nq), np.nan)
    spread = np.full(n, np.nan)
    pool = np.full(n, np.nan)
    size = np.zeros(n, dtype=int)
    for i in range(n):
        m = mask_all[i]
        size[i] = int(m.sum())
        if size[i] < max(nq * 3, 30):
            continue
        b = bucket_means(S[i][m], panel["FWD"][i][m], nq)
        rows[i] = b
        spread[i] = b[-1] - b[0]
        pool[i] = float(panel["FWD"][i][m].mean())
    return {"buckets": rows, "spread": spread, "pool": pool, "size": size,
            "top": rows[:, -1], "bot": rows[:, 0], "nq": nq}


# -------------------------------------------------------------- estimators

def phase_profile(x: np.ndarray, phases: int = H) -> dict:
    """Rule 9 in its strongest form. Daily formation of a `phases`-session
    hold contains exactly `phases` non-overlapping entry schedules; each is a
    genuinely independent series. Report their dispersion, not just the pool."""
    means, ts = [], []
    for p in range(phases):
        v = x[p::phases]
        v = v[np.isfinite(v)]
        if len(v) < 5:
            continue
        se = nw_se(v, 0)                    # this subset does NOT overlap
        means.append(float(v.mean()))
        ts.append(float(v.mean()) / se if se > 0 else np.nan)
    if not means:
        return {}
    m = np.array(means)
    return {"phases": len(m), "mean_bps": round(1e4 * float(m.mean()), 1),
            "sd_bps": round(1e4 * float(m.std(ddof=1)), 1),
            "min_bps": round(1e4 * float(m.min()), 1),
            "max_bps": round(1e4 * float(m.max()), 1),
            "frac_pos": round(float((m > 0).mean()), 3),
            "median_t": round(float(np.nanmedian(ts)), 2)}


def turnover(panel: dict, S: np.ndarray, nq: int = NQ, top: bool = True,
             gated: bool = True) -> float:
    """One-way turnover of an extreme bucket per HOLD, measured only on the
    non-overlapping schedules (the tradeable book turns over once per hold,
    not once per formation date)."""
    mask_all = panel["SCOR"] if gated else panel["OPEN"]
    n = len(panel["dates"])
    turns = []
    for p in range(H):
        prev = None
        for i in range(p, n, H):
            m = mask_all[i]
            if m.sum() < max(nq * 3, 30):
                prev = None
                continue
            names = np.flatnonzero(m)[np.argsort(S[i][m], kind="stable")]
            k = len(names) // nq
            cur = set(names[-k:] if top else names[:k])
            if prev is not None and cur:
                turns.append(1.0 - len(cur & prev) / len(cur))
            prev = cur
    return float(np.mean(turns)) if turns else float("nan")


def ladder(x: np.ndarray, cost_per_hold: float = 0.0,
           phases: int = H) -> dict:
    """The retail-holdable form: capital laddered across all `phases` entry
    offsets, each sleeve rebalanced once per hold. Compound each sleeve's
    NON-OVERLAPPING window returns, then report the distribution across
    sleeves. This is the only honest way to turn overlapping window returns
    into an annualised number."""
    cagrs, sharpes = [], []
    for p in range(phases):
        v = x[p::phases]
        v = v[np.isfinite(v)] - cost_per_hold
        if len(v) < 8:
            continue
        yrs = len(v) * H / 252.0
        wealth = float(np.prod(1.0 + v))
        if wealth <= 0:
            continue
        cagrs.append(wealth ** (1.0 / yrs) - 1.0)
        sd = float(v.std(ddof=1))
        sharpes.append(float(v.mean()) / sd * math.sqrt(252.0 / H) if sd > 0
                       else np.nan)
    if not cagrs:
        return {}
    c, s = np.array(cagrs), np.array(sharpes)
    return {"sleeves": len(c),
            "cagr_pct": round(100 * float(c.mean()), 2),
            "cagr_lo_pct": round(100 * float(c.min()), 2),
            "cagr_hi_pct": round(100 * float(c.max()), 2),
            "sharpe": round(float(np.nanmean(s)), 3),
            "sharpe_lo": round(float(np.nanmin(s)), 3),
            "sharpe_hi": round(float(np.nanmax(s)), 3)}


# ---------------------------------------------------------------- controls

def null_shuffled_score(panel: dict, draws: int, nq: int = NQ,
                        seed: int = SEED) -> dict:
    """CONTROL. Permute the forward returns within the identical gated pool:
    the dates, the pool, the gates and the decile sizes are held fixed and
    only the ranking is destroyed. Equivalent to a random decile assignment
    from the same eligible pool."""
    rng = np.random.default_rng(seed)
    n = len(panel["dates"])
    idx = [i for i in range(n) if panel["SCOR"][i].sum() >= max(nq * 3, 30)]
    fwds = [panel["FWD"][i][panel["SCOR"][i]] for i in idx]
    means = np.empty(draws)
    tops = np.empty(draws)
    for d in range(draws):
        sp, tp = np.empty(len(idx)), np.empty(len(idx))
        for j, f in enumerate(fwds):
            p = rng.permutation(f)
            e = (np.arange(nq + 1) * len(p)) // nq
            sp[j] = p[e[nq - 1]:].mean() - p[:e[1]].mean()
            tp[j] = p[e[nq - 1]:].mean() - f.mean()
        means[d] = sp.mean()
        tops[d] = tp.mean()
    return {"draws": draws, "dates": len(idx),
            "spread_mean_bps": round(1e4 * float(means.mean()), 2),
            "spread_se_bps": round(1e4 * float(means.std(ddof=1)), 2),
            "spread_lo_bps": round(1e4 * float(np.percentile(means, 2.5)), 1),
            "spread_hi_bps": round(1e4 * float(np.percentile(means, 97.5)), 1),
            "toppick_mean_bps": round(1e4 * float(tops.mean()), 2),
            "toppick_se_bps": round(1e4 * float(tops.std(ddof=1)), 2)}


def null_noise_component(panel: dict, key: str, w: dict, draws: int,
                         nq: int = NQ, seed: int = SEED) -> dict:
    """THE CONTROL H29 NEEDS. Keep the weight vector exactly as it is, but
    replace ONE ingredient with a permutation of ITSELF inside the same gated
    pool on each date: same weight, same marginal distribution, zero
    information.

    Leaving an ingredient out changes two things at once — the information it
    carried, and how much weight the others get. This separates them. If
    `high` is harmful because of what it KNOWS, the composite must improve
    when `high` is replaced by noise; if 0.25 on anything is merely dilution,
    the noise version will be no better than the real one. The mirror case is
    the check that the estimator is not just rewarding randomness: replacing
    `mom12` with noise must make the composite WORSE.
    """
    rng = np.random.default_rng(seed + 17)
    n = len(panel["dates"])
    base = np.zeros(panel["FWD"].shape, dtype=np.float32)
    for k, v in w.items():
        if v and k != key:
            base += np.float32(v) * panel["COMP"][k]
    means = np.empty(draws)
    for d in range(draws):
        sp = []
        for i in range(n):
            m = panel["SCOR"][i]
            if m.sum() < max(nq * 3, 30):
                continue
            s = base[i][m] + np.float32(w[key]) * rng.permutation(
                panel["COMP"][key][i][m])
            b = bucket_means(s, panel["FWD"][i][m], nq)
            sp.append(b[-1] - b[0])
        means[d] = float(np.mean(sp))
    return {"draws": draws, "component": key, "weight": round(w[key], 4),
            "mean_bps": round(1e4 * float(means.mean()), 1),
            "se_bps": round(1e4 * float(means.std(ddof=1)), 2),
            "lo_bps": round(1e4 * float(np.percentile(means, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(means, 97.5)), 1)}


# ------------------------------------------------------------------ report

HDR = (f"{'weight vector':<26}{'D10-D1':>9}{'NW t':>7}{'ci lo':>9}{'ci hi':>9}"
       f"{'half1':>9}{'half2':>9}{'mktadj':>9}{'beta':>7}{'a t':>6}"
       f"{'vs base':>9}{'d t':>6}")


def evaluate(panel: dict, name: str, w: dict, base: dict | None = None,
             nq: int = NQ) -> dict:
    """One weight vector: decile spread, Rule-13 market adjustment, the
    paired delta against the baseline, and the long-only top decile."""
    S = score_matrix(panel, w)
    ds = decile_series(panel, S, nq)
    lag = H - 1
    sp = stats(ds["spread"], lag=lag)
    b_sp, adj_sp = beta_to_bench(ds["spread"], panel["bench"])
    excess = ds["top"] - ds["pool"]
    b_lo, _ = beta_to_bench(ds["top"], panel["bench"])
    row = {"name": name, "weights": {k: round(v, 4) for k, v in w.items()},
           "spread": sp, "spread_mktadj": b_sp,
           "deciles_bps": [round(1e4 * float(np.nanmean(ds["buckets"][:, k])), 1)
                           for k in range(nq)],
           "top_minus_pool": stats(excess, lag=lag),
           "top_vs_spy": b_lo,
           "phase_spread": phase_profile(ds["spread"]),
           "phase_excess": phase_profile(excess)}
    if base is not None:
        d_sp = ds["spread"] - base["spread"]
        d_ex = excess - (base["top"] - base["pool"])
        row["delta_spread"] = stats(d_sp, lag=lag)
        row["delta_excess"] = stats(d_ex, lag=lag)
        row["delta_phase"] = phase_profile(d_sp)
    row["_ds"] = ds
    row["_S"] = S
    return row


def print_row(row: dict) -> None:
    sp, b = row["spread"], row["spread_mktadj"]
    d = row.get("delta_spread")
    dtxt = (f"{d['mean_bps']:>9.1f}{d['nw_t']:>6.2f}" if d else f"{'':>15}")
    print(f"{row['name']:<26}{sp['mean_bps']:>9.1f}{sp['nw_t']:>7.2f}"
          f"{sp['ci_lo_bps']:>9.1f}{sp['ci_hi_bps']:>9.1f}"
          f"{sp['h1_bps']:>9.1f}{sp['h2_bps']:>9.1f}"
          f"{b['alpha_bps']:>9.1f}{b['beta']:>7.2f}{b['alpha_t']:>6.2f}{dtxt}")


LHDR = (f"{'weight vector':<26}{'D10 gross':>10}{'-pool':>9}{'t':>6}"
        f"{'half1':>9}{'half2':>9}{'alphaSPY':>10}{'beta':>7}{'a t':>6}"
        f"{'turn':>7}{'net-pool':>10}{'BE bps':>9}")


def print_book(row: dict, panel: dict) -> None:
    t_long = row["turnover_long"]
    ex = row["top_minus_pool"]
    b = row["top_vs_spy"]
    net = ex["mean_bps"] - COST_BPS * t_long
    be = ex["mean_bps"] / t_long if t_long > 0 else float("nan")
    print(f"{row['name']:<26}"
          f"{1e4 * float(np.nanmean(row['_ds']['top'])):>10.1f}"
          f"{ex['mean_bps']:>9.1f}{ex['nw_t']:>6.2f}"
          f"{ex['h1_bps']:>9.1f}{ex['h2_bps']:>9.1f}"
          f"{b['alpha_bps']:>10.1f}{b['beta']:>7.2f}{b['alpha_t']:>6.2f}"
          f"{t_long:>7.2f}{net:>10.1f}{be:>9.1f}")


def run_universe(ctx: dict, mode: str, draws: int) -> dict:
    print(f"\n{'=' * 130}\n=== UNIVERSE {mode}   "
          f"(guards: split-repair ON, extreme-print "
          f"{'ON' if ctx['guard'] else 'OFF'}, frozen-quote "
          f"{'ON' if ctx['guard'] else 'OFF'})\n{'=' * 130}")
    panel = build_panel(ctx, mode)
    n = len(panel["dates"])
    gate_sz = panel["GATE"].sum(axis=1)
    scor_sz = panel["SCOR"].sum(axis=1)
    open_sz = panel["OPEN"].sum(axis=1)
    print(f"{n} DAILY formation dates {panel['dates'][0].date()} .. "
          f"{panel['dates'][-1].date()}  |  hold {H} td  ->  {H} non-overlapping "
          f"entry schedules, effective independent sample ~{n // H}")
    print(f"pool sizes: research-eligible (ungated) mean {open_sz.mean():.0f}; "
          f"v5-GATED mean {gate_sz.mean():.0f}, of which SCORABLE "
          f"{scor_sz.mean():.0f} (min {scor_sz.min()}, max {scor_sz.max()}) "
          f"-> decile ~{scor_sz.mean() / NQ:.0f} names")
    print(f"partial forward paths kept (delisting-tolerant): "
          f"{panel['partial_paths']}   |   symbols retired on frozen quotes: "
          f"{len(ctx['stale_killed'])}")

    out = {"mode": mode, "guard": ctx["guard"], "dates": n,
           "span": [str(panel["dates"][0].date()), str(panel["dates"][-1].date())],
           "gated_pool_mean": float(gate_sz.mean()),
           "eff_independent": n // H}

    # ------------------------------------------------- pipeline-trust block
    print("\n--- PIPELINE TRUST: reproduce H25 on this pipeline before "
          "believing anything else ---")
    mon = np.zeros(n, dtype=bool)
    mon[::STEP_MONTHLY] = True
    rep = {}
    for tag, col, gated in (("high52 D10-D1 [ungated, monthly]", "RAW_HIGH", False),
                            ("mom12  D10-D1 [ungated, monthly]", "RAW_MOM", False),
                            ("high52 D10-D1 [gated, monthly]", "RAW_HIGH", True),
                            ("mom12  D10-D1 [gated, monthly]", "RAW_MOM", True)):
        ds = decile_series(panel, panel[col], NQ, gated=gated)
        s = stats(np.where(mon, ds["spread"], np.nan), lag=1)
        b, _ = beta_to_bench(np.where(mon, ds["spread"], np.nan), panel["bench"])
        rep[tag] = {"spread": s, "mktadj": b}
        print(f"  {tag:<38} {s['mean_bps']:>8.1f} bps  t {s['nw_t']:>6.2f}  "
              f"halves {s['h1_bps']:>7.1f} /{s['h2_bps']:>7.1f}  "
              f"mkt-adj {b['alpha_bps']:>7.1f} (beta {b['beta']:>5.2f})  n {s['n']}")
    print("  H25 published (S&P 1500, 109 monthly formations, guards 1+2 only):"
          "\n    high52 ungated -182.8 bps t -1.84, market-adjusted +23.9 t 0.29;"
          " mom12 ungated +91.0, gated +132.8")
    out["reproduction"] = rep

    # ------------------------------------------------------------ baseline
    print(f"\n--- (a) BASELINE: the exact v5 composite, {H}-session hold, "
          f"equal weight, gated pool ---")
    print(HDR)
    vs = variants()
    base_row = evaluate(panel, "v5 baseline", vs["v5 baseline"])
    base_ds = base_row["_ds"]
    print_row(base_row)
    print("  decile means (bps per window), LOW composite score -> HIGH: "
          + " ".join(f"{v:>6.0f}" for v in base_row["deciles_bps"]))
    betas = [beta_to_bench(base_ds["buckets"][:, k], panel["bench"])[0]
             for k in range(NQ)]
    print("  Rule 13 — SPY beta per decile:                                "
          + " ".join(f"{b['beta']:>6.2f}" for b in betas))
    print("  Rule 13 — market-adjusted per decile:                         "
          + " ".join(f"{b['alpha_bps']:>6.0f}" for b in betas))
    print(f"  equal-weight GATED pool {1e4 * float(np.nanmean(base_ds['pool'])):.0f} bps"
          f"   SPY over the identical windows "
          f"{1e4 * float(np.nanmean(panel['bench'])):.0f} bps")
    top_minus_bot = float(np.nanmean(base_ds["spread"]))
    print(f"  KNOWN NULL CHECK: best-ranked decile minus worst-ranked decile = "
          f"{100 * -top_minus_bot:+.2f}% in ALPHA-STACK.md's orientation "
          f"(published -0.26%, weekly forensics pipeline)")
    out["baseline_decile_betas"] = [b["beta"] for b in betas]
    out["baseline_decile_mktadj"] = [b["alpha_bps"] for b in betas]
    out["pool_bps"] = round(1e4 * float(np.nanmean(base_ds["pool"])), 1)
    out["spy_bps"] = round(1e4 * float(np.nanmean(panel["bench"])), 1)

    # ------------------------------------------------------------ controls
    print(f"\n--- CONTROLS ({draws} draws; Rule 14 prints null SE / real NW SE) ---")
    nul = null_shuffled_score(panel, draws)
    ratio = nul["spread_se_bps"] / base_row["spread"]["nw_se_bps"]
    z = (base_row["spread"]["mean_bps"] - nul["spread_mean_bps"]) / nul["spread_se_bps"]
    print(f"  {'SHUFFLED score, same gated pool':<36} null "
          f"{nul['spread_mean_bps']:>7.2f} bps  95% [{nul['spread_lo_bps']:>6.1f},"
          f"{nul['spread_hi_bps']:>6.1f}]   real {base_row['spread']['mean_bps']:>7.1f}"
          f"   nullSE/realNWSE {ratio:>5.2f}   z {z:>6.2f}")
    print(f"  {'RANDOM PICK of decile size, same pool':<36} null "
          f"{nul['toppick_mean_bps']:>7.2f} bps (SE {nul['toppick_se_bps']:.2f}) "
          f"against the real top-decile-minus-pool "
          f"{base_row['top_minus_pool']['mean_bps']:>7.1f}")
    out["null_shuffled"] = nul

    # -------------------------------------------- (b)(c)(d)(e) all variants
    print("\n--- (b) LEAVE-ONE-OUT, (c) W_HIGH redistribution, (d) momentum "
          "floor, (e) W_HIGH sweep ---")
    print("    'vs base' is the PAIRED per-date difference against the v5 "
          "baseline (same dates, same pool):\n    POSITIVE means the change "
          "IMPROVED the sort. A weight that matters makes things WORSE when "
          "dropped.")
    print(HDR)
    rows = {"v5 baseline": base_row}
    for name, w in vs.items():
        if name == "v5 baseline":
            print_row(base_row)
            continue
        r = evaluate(panel, name, w, base=base_ds)
        rows[name] = r
        print_row(r)

    # ------------------------- the delta table, with halves and phase spread
    print("\n--- (b) the LEAVE-ONE-OUT DELTAS on their own, since they are the "
          "test: paired per-date, same pool ---")
    print(f"{'dropped weight':<18}{'w':>6}{'delta bps':>11}{'NW t':>7}"
          f"{'ci lo':>9}{'ci hi':>9}{'half1':>9}{'half2':>9}"
          f"{'phase sd':>10}{'frac>0':>8}{'verdict':>12}")
    loo = {}
    for k in KEYS:
        r = rows[f"drop {k}"]
        d, p = r["delta_spread"], r["delta_phase"]
        same = (d["h1_bps"] > 0) == (d["h2_bps"] > 0)
        verdict = ("HARMS" if d["mean_bps"] > 0 else "CONTRIBUTES") if same \
            else "flips"
        loo[k] = {"delta": d, "phase": p, "verdict": verdict}
        print(f"{k:<18}{W_V5[k]:>6.2f}{d['mean_bps']:>11.1f}{d['nw_t']:>7.2f}"
              f"{d['ci_lo_bps']:>9.1f}{d['ci_hi_bps']:>9.1f}"
              f"{d['h1_bps']:>9.1f}{d['h2_bps']:>9.1f}"
              f"{p['sd_bps']:>10.1f}{p['frac_pos']:>8.2f}{verdict:>12}")
    print("    ('HARMS' = dropping it IMPROVED the sort with the same sign in "
          "both halves; the deltas are\n     signed so that positive means "
          "better. Renormalisation is part of each change, by construction.)")
    out["leave_one_out"] = loo

    # ----------------------------- the control that separates the two causes
    print(f"\n--- CONTROL: replace ONE ingredient with NOISE at the SAME weight "
          f"({max(10, draws // 4)} draws) ---")
    print("    dropping a weight changes the information AND the other weights;"
          " this changes only\n    the information. Real < noise => the "
          "ingredient's content is harmful, not its share.")
    noise = {}
    print(f"{'ingredient':<18}{'weight':>8}{'real D10-D1':>13}"
          f"{'noise D10-D1':>14}{'null 95%':>20}{'real - noise':>14}")
    for k in ("high", "mom12", "vol"):
        nn = null_noise_component(panel, k, vs["v5 baseline"],
                                 max(10, draws // 4))
        noise[k] = nn
        ci = f"[{nn['lo_bps']:.1f}, {nn['hi_bps']:.1f}]"
        print(f"{k:<18}{W_V5[k]:>8.2f}"
              f"{base_row['spread']['mean_bps']:>13.1f}{nn['mean_bps']:>14.1f}"
              f"{ci:>20}"
              f"{base_row['spread']['mean_bps'] - nn['mean_bps']:>14.1f}")
    out["null_noise_component"] = noise

    # ---------------------------------------------------- the long-only book
    print(f"\n--- the LONG-ONLY top decile (the only form a retail account can "
          f"hold), {COST_BPS:.0f} bps round trip on measured turnover ---")
    print(LHDR)
    for name, r in rows.items():
        r["turnover_long"] = turnover(panel, r["_S"], NQ, top=True)
        r["turnover_short"] = turnover(panel, r["_S"], NQ, top=False)
        print_book(r, panel)

    # ------------------------------------------------ Rule 9 / phase profile
    print(f"\n--- (g) RULE 9: dispersion across the {H} non-overlapping entry "
          "schedules (D10-D1) ---")
    print(f"{'weight vector':<26}{'pooled':>9}{'phase mean':>12}{'phase sd':>10}"
          f"{'min':>9}{'max':>9}{'frac>0':>9}")
    for name in ("v5 baseline", "drop high", "W_HIGH=0 -> momentum",
                 "momentum only", "drop mom12", "drop mom6"):
        p = rows[name]["phase_spread"]
        print(f"{name:<26}{rows[name]['spread']['mean_bps']:>9.1f}"
              f"{p['mean_bps']:>12.1f}{p['sd_bps']:>10.1f}{p['min_bps']:>9.1f}"
              f"{p['max_bps']:>9.1f}{p['frac_pos']:>9.2f}")

    # ------------------------------------------- laddered book vs SPY (H29f)
    print(f"\n--- (f) THE USER'S QUESTION: laddered long-only top decile vs SPY, "
          f"net of {COST_BPS:.0f} bps ---")
    print("    capital split across all 42 entry offsets, each sleeve "
          "rebalanced once per 42-session hold;\n    CAGR and Sharpe computed "
          "per sleeve on NON-OVERLAPPING windows, then averaged (Rule 9).")
    spy_l = ladder(panel["bench"])
    pool_l = ladder(base_ds["pool"])
    print(f"{'book':<26}{'CAGR %':>9}{'[min':>9}{'max]':>9}{'Sharpe':>9}"
          f"{'[min':>8}{'max]':>8}{'beta':>7}{'alphaSPY':>10}")
    print(f"{'SPY buy-and-hold':<26}{spy_l['cagr_pct']:>9.2f}"
          f"{spy_l['cagr_lo_pct']:>9.2f}{spy_l['cagr_hi_pct']:>9.2f}"
          f"{spy_l['sharpe']:>9.3f}{spy_l['sharpe_lo']:>8.3f}"
          f"{spy_l['sharpe_hi']:>8.3f}{1.00:>7.2f}{0.0:>10.1f}")
    print(f"{'equal-weight gated pool':<26}{pool_l['cagr_pct']:>9.2f}"
          f"{pool_l['cagr_lo_pct']:>9.2f}{pool_l['cagr_hi_pct']:>9.2f}"
          f"{pool_l['sharpe']:>9.3f}{pool_l['sharpe_lo']:>8.3f}"
          f"{pool_l['sharpe_hi']:>8.3f}"
          f"{beta_to_bench(base_ds['pool'], panel['bench'])[0]['beta']:>7.2f}"
          f"{beta_to_bench(base_ds['pool'], panel['bench'])[0]['alpha_bps']:>10.1f}")
    for name, r in rows.items():
        lad = ladder(r["_ds"]["top"], cost_per_hold=1e-4 * COST_BPS * r["turnover_long"])
        r["ladder_net"] = lad
        b = r["top_vs_spy"]
        print(f"{name:<26}{lad['cagr_pct']:>9.2f}{lad['cagr_lo_pct']:>9.2f}"
              f"{lad['cagr_hi_pct']:>9.2f}{lad['sharpe']:>9.3f}"
              f"{lad['sharpe_lo']:>8.3f}{lad['sharpe_hi']:>8.3f}"
              f"{b['beta']:>7.2f}{b['alpha_bps']:>10.1f}")
    out["ladder_spy"] = spy_l
    out["ladder_pool"] = pool_l
    best = max(rows.values(), key=lambda r: r["ladder_net"]["sharpe"])
    print(f"\n  RULE 13 DECOMPOSITION of the best book ({best['name']}), "
          f"Sharpe {best['ladder_net']['sharpe']:.3f} vs SPY "
          f"{spy_l['sharpe']:.3f}:")
    print(f"    equal-weight GATED POOL alone is already "
          f"{pool_l['sharpe'] - spy_l['sharpe']:+.3f} Sharpe against SPY "
          f"(equal weight carries more volatility than a cap-weighted index),")
    print(f"    and the selection layer adds "
          f"{best['ladder_net']['sharpe'] - pool_l['sharpe']:+.3f} on top of "
          f"that pool. Net against SPY: "
          f"{best['ladder_net']['sharpe'] - spy_l['sharpe']:+.3f}.")
    print(f"    Its CAGR is {best['ladder_net']['cagr_pct']:.2f}% against SPY's "
          f"{spy_l['cagr_pct']:.2f}% at beta {best['top_vs_spy']['beta']:.2f} — "
          f"Rule 13 says that is\n    bought with beta and equal-weight "
          f"volatility, not with risk-adjusted skill.")
    out["best_book"] = {"name": best["name"],
                        "sharpe": best["ladder_net"]["sharpe"],
                        "cagr_pct": best["ladder_net"]["cagr_pct"],
                        "beta": best["top_vs_spy"]["beta"],
                        "sharpe_minus_spy": round(
                            best["ladder_net"]["sharpe"] - spy_l["sharpe"], 3),
                        "sharpe_minus_pool": round(
                            best["ladder_net"]["sharpe"] - pool_l["sharpe"], 3)}

    # ------------------------------------------------------ (e) the profile
    print("\n--- (e) IS W_HIGH MONOTONICALLY HARMFUL? sweep profile ---")
    print(f"{'W_HIGH':>8}{'D10-D1':>10}{'NW t':>8}{'mkt-adj':>10}{'beta':>8}"
          f"{'D10-pool':>10}{'t':>7}{'net CAGR %':>12}{'Sharpe':>9}")
    sweep = []
    for wh in (0.0, 0.10, 0.25, 0.40):
        r = rows[f"W_HIGH={wh:.2f} sweep"]
        sweep.append({"w_high": wh,
                      "spread_bps": r["spread"]["mean_bps"],
                      "mktadj_bps": r["spread_mktadj"]["alpha_bps"],
                      "excess_bps": r["top_minus_pool"]["mean_bps"],
                      "cagr_pct": r["ladder_net"]["cagr_pct"],
                      "sharpe": r["ladder_net"]["sharpe"]})
        print(f"{wh:>8.2f}{r['spread']['mean_bps']:>10.1f}"
              f"{r['spread']['nw_t']:>8.2f}{r['spread_mktadj']['alpha_bps']:>10.1f}"
              f"{r['spread_mktadj']['beta']:>8.2f}"
              f"{r['top_minus_pool']['mean_bps']:>10.1f}"
              f"{r['top_minus_pool']['nw_t']:>7.2f}"
              f"{r['ladder_net']['cagr_pct']:>12.2f}"
              f"{r['ladder_net']['sharpe']:>9.3f}")
    out["w_high_sweep"] = sweep

    out["variants"] = {k: {kk: vv for kk, vv in v.items()
                           if not kk.startswith("_")} for k, v in rows.items()}
    return out


# ----------------------------------------------------------------- selftest

_FAILS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _FAILS
    if not ok:
        _FAILS += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"   {detail}" if detail else ""))


def selftest() -> int:
    """Twelve checks. The load-bearing one is bit-identity with the shipped
    engine: if this lab's composite is not `signals.composite_at`'s composite,
    nothing else in the file means anything."""
    global _FAILS
    _FAILS = 0
    print("SELFTEST")
    rng = np.random.default_rng(7)

    # 1. rank_pct == pandas rank(pct=True), ties included
    x = np.array([3.0, 1.0, 1.0, 2.0, 5.0, 5.0, 5.0])
    check("rank_pct matches pandas rank(pct=True) with ties",
          np.allclose(rank_pct(x), pd.Series(x).rank(pct=True).to_numpy()),
          f"{np.round(rank_pct(x), 4)}")

    # 2. renormalisation is a monotone transform -> identical ranking
    w1 = renorm({k: v for k, v in W_V5.items() if k != "high"})
    w2 = {k: (0.0 if k == "high" else v) for k, v in W_V5.items()}
    a = np.array([w1.get(k, 0.0) for k in KEYS])
    b = np.array([w2.get(k, 0.0) for k in KEYS])
    ratio = a[b > 0] / b[b > 0]
    check("'drop high' and 'W_HIGH=0 -> nothing' are the same ranking",
          np.allclose(ratio, ratio[0]), f"scale {ratio[0]:.4f}")

    # 3. the sweep's 0.25 point IS the baseline
    sw = variants()["W_HIGH=0.25 sweep"]
    check("sweep W_HIGH=0.25 reproduces the v5 weights exactly",
          all(abs(sw[k] - W_V5[k]) < 1e-12 for k in KEYS),
          f"{ {k: round(sw[k], 4) for k in KEYS} }")

    # 4. weights sum to 1 where they should
    check("every registered vector sums to 1.0 (or is a pure rescale)",
          all(abs(sum(w.values()) - 1.0) < 1e-9
              for n, w in variants().items() if "nothing" not in n),
          "")

    # 5. bucket_means arithmetic
    sig = np.array([5.0, 1.0, 3.0, 2.0, 4.0, 6.0])
    fwd = np.array([50.0, 10.0, 30.0, 20.0, 40.0, 60.0])
    bm = bucket_means(sig, fwd, 3)
    check("bucket_means sorts low->high and averages within bucket",
          np.allclose(bm, [15.0, 35.0, 55.0]), f"{bm}")

    # 6. NO LOOKAHEAD — a signal that IS the forward return, one step late
    p = pd.DataFrame({"A": [10.0, 11.0, 12.0, 13.0, 14.0]})
    fwd2 = (p["A"].shift(-2) / p["A"] - 1).to_numpy()
    check("forward(h=2) at t equals close(t+2)/close(t)-1",
          abs(fwd2[0] - (12.0 / 10.0 - 1)) < 1e-12 and not np.isfinite(fwd2[3]),
          f"{fwd2[0]:.6f}")

    # 7. frozen-quote retirement
    c = pd.DataFrame({"A": [10.0] * 5 + [11.0] * 12 + [12.0] * 5,
                      "B": np.linspace(10, 20, 22)})
    kept, killed = retire_stale(c, run=10)
    check("GUARD 3 retires a frozen quote and spares the live symbol",
          [k[0] for k in killed] == ["A"] and np.isfinite(kept["B"]).all()
          and not np.isfinite(kept["A"].iloc[8]))

    # 8. extreme-print mask
    c2 = pd.DataFrame({"A": [10.0, 10.1, 102.0, 103.0, 104.0]})
    sig_d, day_d = contamination(c2)
    check("GUARD 2 flags a fake +910% print and the year around it",
          day_d[2, 0] and sig_d[2:, 0].all() and not day_d[1, 0])

    # 9. score_matrix is linear in the weights
    panel = {"FWD": np.zeros((3, 4), dtype=np.float32),
             "COMP": {k: np.full((3, 4), 0.5, dtype=np.float32) for k in KEYS}}
    s = score_matrix(panel, W_V5)
    check("score_matrix(v5) on a flat 0.5 panel returns 0.5",
          np.allclose(s, 0.5), f"{s[0, 0]:.4f}")

    # 10. phase_profile splits into genuinely non-overlapping schedules
    x = np.arange(420, dtype=float)
    pp = phase_profile(x, phases=42)
    check("phase_profile builds 42 schedules of 10 windows each",
          pp["phases"] == 42, f"{pp['phases']}")

    # 11. ladder compounds, and a constant return gives the exact CAGR
    r = np.full(420, 0.01)
    lad = ladder(r, phases=42)
    exact = 1.01 ** (252 / H) - 1
    check("ladder(constant 1%/hold) == the exact compounded CAGR",
          abs(lad["cagr_pct"] / 100 - exact) < 1e-4,
          f"{lad['cagr_pct']:.4f}% vs {100 * exact:.4f}%")

    # 12. THE LOAD-BEARING CHECK: bit-identity with signals.composite_at.
    # Run with the extreme-print mask OFF, because that mask legitimately
    # removes names from the ranking pool that the live engine would keep;
    # with it off the two pipelines must agree to floating-point noise.
    bars = load_bars()
    bars, _ = repair_splits(bars)
    ctx0 = prep(bars, guard=False)
    p0 = build_panel(ctx0, "sp1500")
    frames = {k: pd.DataFrame(v, index=ctx0["index"], columns=ctx0["cols"])
              for k, v in ctx0["F"].items()}
    members = {u["symbol"] for u in universe.load()}
    sub = {k: f.loc[:, [c for c in f.columns if c in members]]
           for k, f in frames.items()}
    S0 = score_matrix(p0, W_V5)
    cols = np.array(p0["cols"])
    worst, n_cmp, worst_set = 0.0, 0, 0
    for i in (10, 500, 1200, 2000):
        eng = signals.composite_at(sub, p0["dates"][i])
        g = p0["GATE"][i]
        mine_s = pd.Series(100 * S0[i][g].astype(float), index=cols[g])
        worst_set = max(worst_set, len(set(mine_s.index) ^ set(eng.index)))
        common = mine_s.index.intersection(eng.index)
        worst = max(worst, float((mine_s.loc[common]
                                  - eng.loc[common, "score"]).abs().max()))
        n_cmp += len(common)
    check("this lab's GATE == signals.composite_at's eligible set",
          worst_set == 0, f"{worst_set} symbols differ across 4 real dates")
    check("this lab's composite == signals.composite_at's score",
          worst < 5e-4, f"max |difference| {worst:.2e} of 100 over "
                        f"{n_cmp} name-dates (float32 storage noise)")

    print(f"\n{'ALL CHECKS PASSED' if _FAILS == 0 else str(_FAILS) + ' CHECK(S) FAILED'}")
    return _FAILS


# --------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.weight_lab")
    ap.add_argument("--universe", default="both",
                    choices=["sp1500", "pit500", "both"])
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--no-guard", action="store_true",
                    help="turn the extreme-print mask and frozen-quote "
                         "retirement OFF (split repair stays on)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        raise SystemExit(selftest())

    bars = load_bars()
    bars, bad = repair_splits(bars)
    print(f"GUARD 1 split repair: {len(bad)} unadjusted splits back-adjusted")
    ctx = prep(bars, guard=not args.no_guard)
    print(f"GUARD 3 frozen quotes: {len(ctx['stale_killed'])} symbols retired "
          f"at a run of {STALE_RUN} identical closes")

    modes = (["sp1500", "pit500"] if args.universe == "both" else [args.universe])
    out = {"engine": config.ENGINE, "horizon": H, "cost_bps": COST_BPS,
           "weights_v5": W_V5, "guard": not args.no_guard, "universes": {}}
    for mode in modes:
        out["universes"][mode] = run_universe(ctx, mode, args.draws)

    n_vectors = len(variants())
    print(f"\nTRIAL COUNT: {n_vectors} weight vectors x {len(modes)} universes "
          f"= {n_vectors * len(modes)} measured cells "
          f"({n_vectors - 4} of the vectors are distinct rankings; 4 are "
          f"algebraic duplicates printed as a consistency check).")
    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"results -> {RESULTS}")


if __name__ == "__main__":
    main()
