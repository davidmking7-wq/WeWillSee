"""H25 — 52-week-high proximity as a STANDALONE signal, not a composite ingredient.

MECHANISM (one sentence, Rule 1)
--------------------------------
George-Hwang (2004): investors anchor on the 52-week high and treat it as a
psychological ceiling, so good news arriving while a stock sits near that high
is under-reacted to, and the under-reaction resolves as drift over the
following months.

WHY THIS REPO CARES
-------------------
`config.W_HIGH = 0.25` is the single largest weight in the v5 composite —
bigger than 12-1 momentum — and it had never been tested on its own. The
composite as a whole was measured sorting nothing (decile 1 minus decile 10 =
-0.26% at 42 td, BACKTEST-REPORT.md). Either this ingredient is dead too, or
it is alive and being diluted by the other seven weights.

George-Hwang's actual claim is a HORSE RACE claim: nearness-to-high dominates
conventional momentum, and survives controlling for it. So the deciding row
here is not "does high52 sort" — it is "does high52 sort ONCE MOMENTUM IS
HELD FIXED". A signal that only works through momentum is not a separate
signal, and this engine already owns the momentum.

PRE-REGISTRATION (written before the first number was produced)
---------------------------------------------------------------
| #  | hypothesis | expected sign |
|----|------------|---------------|
| H25a | high52 decile spread D10-D1 over 42 sessions is positive, S&P 1500 | > 0 |
| H25b | same on the survivorship-free point-in-time S&P 500 | > 0 |
| H25c | high52 still sorts INSIDE the repo's gated eligible pool (the actionable form) | > 0 |
| H25d | horse race: 12-1 momentum decile spread on the identical pool | > 0 |
| H25e | **DECIDING ROW.** high52 spread survives inside every 12-1 momentum tercile | > 0 in all 3 |
| H25f | Fama-MacBeth: lambda_high52 stays positive with t > 3 once momentum rank is in the regression | t > 3 |
| H25g | momentum-orthogonalized high52 (cross-sectional residual) still sorts | > 0 |
| H25h | the LONG-ONLY top decile — the only form this repo could trade — beats the equal-weight eligible pool after 10 bps | > 0 net |
| H25i | horizon sensitivity 21 / 42 / 126 sessions (George-Hwang used 6 months) | positive, growing with h |
| H25j | George-Hwang's crash claim: high52's worst window is shallower than 12-1 momentum's | worst(high52) > worst(mom) |
| H25k | split-debt sensitivity: the guarded and unguarded answers agree in sign | same sign |

Failure conditions, stated in advance: H25a/b fail if the spread's sign flips
across halves or sits inside the random-decile null; **H25e fails — and takes
the standalone claim with it — if the spread is not positive in all three
momentum terciles**; H25h fails if the break-even round-trip cost is under
10 bps. A date-shuffled null that reproduces the spread means the effect is a
static property of WHICH stocks are habitually near their highs, not a timing
signal (this is exactly how H15 died).

METHOD
------
Signal      high52_t = close_t / max(close over the trailing 252 sessions
            INCLUDING t) — bit-identical to `signals.feature_frames()["high"]`,
            so this measures the engine's own ingredient, not a lookalike.
Momentum    mom12_t = close_{t-21}/close_{t-252} - 1 — `frames["mom"]`.
THE SHIFT   Everything in the signal row is built from closes at or before t.
            The forward return is `close_{t+42} / close_t - 1`, i.e. it is
            driven by the returns of sessions t+1 ... t+42 only. Formation
            close t is the entry price (the repo's shipped H4 buy-at-the-close
            rule). There is no other place in this file where a signal and a
            return can touch.
Formation   every 21 sessions (monthly), hold 42 sessions, equal weight,
            deciles and quintiles both reported.
Sample      2016-01 .. 2026-08 Alpaca SIP daily bars, split+dividend adjusted
            and then REPAIRED (see below). ~115 formation dates.
Effective n 42-td holds formed every 21 td overlap two-deep, so the effective
            independent sample is HALF the date count. Every t-statistic uses
            Newey-West lag 1; every CI is a moving-block bootstrap with block
            length 2; and both non-overlapping entry PHASES are reported
            separately (RESEARCH-AGENDA Rule 9).

SPLIT-DEBT GUARD — say which (both, in this order)
--------------------------------------------------
1. REPAIR. Alpaca's corporate-actions feed is queried for every symbol; any
   split whose ex-date one-day return exceeds 35% was never applied to the
   bars, and all closes/opens strictly before that ex-date are divided by the
   split factor (volume multiplied). This is the fix that matters here: the
   missing AAPL 2020-08-31 4:1 split leaves a fake -74.2% print that pins
   AAPL's 52-week-high proximity near 0.25 for a FULL YEAR of the strongest
   run in the sample — a decile-1 label on the best large-cap in the panel.
2. MASK what repair cannot reach. After repair, any remaining |1-day return|
   > 45% is a spin-off or a reused ticker with no paper trail (146 of these
   in the S&P 1500 per scout/data_audit.py). The symbol is removed from the
   cross-section for the 252 sessions whose rolling max it corrupts, and any
   stock-window whose forward path contains one is dropped.
`--no-guard` reruns everything unguarded, which is H25k.

CONTROLS (nulls, not trials)
----------------------------
(i)  random-decile assignment from the identical eligible pool, 200 draws;
(ii) DATE-SHUFFLED signal — each formation date is scored with another
     randomly chosen date's high52 snapshot, 200 draws. This is the control
     that killed H15: it holds "which stocks tend to sit near their highs"
     fixed and destroys only the timing;
(iii) matched benchmark — the equal-weight eligible pool over the identical
     windows, plus SPY.
Per house Rule 14 the ratio of each null's SE to the real series' Newey-West
SE is printed next to it. Per house Rule 13 every dollar-neutral book is
regressed on SPY before its sign is quoted.

VERDICT — REJECTED on every registered row, in both universes (2026-08-09)
--------------------------------------------------------------------------
109 monthly formations 2017-05-10 .. 2026-05-19 (effective independent sample
~54), 42-session holds, equal weight. Every number below is printed by
`python -m scout.high52_lab` and stored in scout/high52_results.json.

**The finding is bigger than the rejection: a 52-week-high sort is a BETA
sort.** S&P 1500, all eligible names, mean return per decile in bps per 42 td,
low proximity -> high proximity:

    high52 raw       388  302  264  273  264  273  246  237  233  205
    high52 SPY beta 1.61 1.30 1.15 1.15 1.07 1.01 0.95 0.93 0.89 0.79
    high52 mkt-adj   -21  -30  -28  -20   -7   15    4   -0    7    3

    mom12  raw       336  235  223  229  240  227  241  250  277  427
    mom12  SPY beta 1.49 1.19 1.07 0.99 0.98 0.99 0.98 0.97 1.03 1.15
    mom12  mkt-adj   -44  -68  -50  -25   -9  -24   -8    2   14  133

A stock far below its 52-week high is a stock that recently fell, and fallen
stocks carry higher betas — so the proximity sort orders the cross-section by
beta almost perfectly (1.61 -> 0.79, monotone), and the raw return profile is
that beta profile priced at the decade's equity premium. Take the beta out and
the profile is flat noise. Momentum's beta profile is U-shaped and therefore
CANNOT generate a monotone return profile; its market-adjusted top decile
still earns +133 bps a window. The two signals are not the same thing wearing
different clothes, and the one this repo weights least is the one that works.

  H25a  S&P 1500 D10-D1  -182.8 bps/42td, NW t -1.84, both halves negative
        (-237 / -130), 39% of windows positive. Market-adjusted: +23.9 bps,
        t 0.29, beta -0.81. REJECTED (raw wrong sign; adjusted indistinct).
  H25b  PIT S&P 500 D10-D1  -53.7 bps, t -0.58, halves -132 / +23.
        Market-adjusted +130.9 bps, t 1.67 — right sign, nowhere near t>3,
        and it flips to nothing on the bigger universe. REJECTED.
  H25c  Gated (the repo's own eligible pool) D10-D1  -131.5 bps, t -2.04,
        BOTH halves negative; market-adjusted +5.4 bps, t 0.10. Decile means
        inside the gate fall 279 -> 148 monotonically. REJECTED. This is the
        actionable row: W_HIGH = 0.25 tilts the engine toward the decile that
        earns least inside the engine's own pool.
  H25d  12-1 momentum on the identical pool: +91.0 bps ungated (t 1.04),
        +132.8 gated (t 2.04, both halves positive), market-adjusted +177.1
        (t 2.11). Momentum wins the horse race on every estimator — but note
        it clears this repo's t>3 bar only in the Fama-MacBeth form (H25f,
        t 3.74), not in the decile-spread form. "Momentum beats proximity"
        is a well-supported ordering; "momentum is a validated standalone
        edge here" is NOT what this lab measured.
  H25e  **DECIDING ROW.** high52 tercile spread inside 12-1 momentum
        terciles: raw -151 / -62 / -173 bps (t -2.34 / -1.41 / -3.31) —
        NEGATIVE in all three, the opposite of the registered sign. Market-
        adjusted the same three cells are -13 / +29 / -87 (t -0.27 / 0.82 /
        -1.81): nothing, with no monotone pattern. REJECTED both ways.
        The reverse sort survives: momentum inside high52 terciles earns
        +10 / +162 / +81 raw and +53 / +124 / +42 market-adjusted, with
        t 3.24 in the middle cell.
  H25f  Fama-MacBeth, S&P 1500: lambda_high52 = -298.6 bps, t -3.17 with
        momentum in the regression; lambda_mom12 = +265.0, t +3.74. The only
        coefficient that clears this repo's t>3 bar in its registered
        direction belongs to momentum. REJECTED.
  H25g  high52 orthogonalized to the momentum rank: -226.0 bps, t -3.30 raw;
        -86.3 bps, t -1.51 market-adjusted (beta -0.55). The apparent
        significance was beta. REJECTED.
  H25h  Long-only D10 minus the equal-weight eligible pool: -63.3 bps/window
        gross on 0.76 one-way turnover; break-even round-trip cost is
        NEGATIVE (-83.2 bps ungated, -60.2 gated), so no cost assumption
        rescues it. Gross Sharpe of the D10-D1 book -0.50. REJECTED.
  H25i  Holds of 21 / 42 / 126 sessions: -142 / -183 / -538 bps (S&P 1500).
        George-Hwang's effect should GROW with horizon; this one grows more
        negative. REJECTED.
  H25j  Crash claim REJECTED, and backwards: in bear formations high52's
        spread is -722 bps against momentum's -48, and its worst window
        (-3095 bps, formed 2020-10-09) is worse than momentum's (-2733).
        Being long the names nearest their highs and short the laggards is a
        short-beta book, and short-beta books lose hardest in rebounds.
  H25k  Split-debt sensitivity: the SIGN is identical in all four data
        configurations, the MAGNITUDE is not. Unmasked, the S&P 1500 spread
        reads -974 bps instead of -183 and the worst window reads -41,254 bps
        (-412%), because orphan moves land in decile 1 by construction — a
        reused ticker or a spin-off leaves the price far under a stale
        52-week max. The repo-gated version is immune (-131.5 guarded vs
        -131.9 raw): the vetoes block corrupt bars, corroborating
        scout/data_audit.py on a completely different estimator.

CONTROL RESULTS
  Random-decile null +0.71 bps (S&P 1500) — the sort is doing something, but
  Rule 14 shows why that means little: the null's SE is 0.15x the real
  series' Newey-West SE, so its z of -12.65 is anti-conservative by ~7x
  against an honest t of -1.84.
  DATE-SHUFFLED null (donors >= 1 year in the PAST) = -127.6 bps against a
  real -185.7 on the same dates: **a signal snapshot a full year out of date
  reproduces 69% of the spread**, and the real-vs-null z is only -1.62. This
  is the H15 verdict in a new costume — the sort identifies a persistent
  STOCK TYPE (high-beta laggards), not a timing state.
  LOOKAHEAD SELF-TEST: inverting only the donor's time direction moves the
  same estimator by +57 bps (S&P 1500) and +127 bps (PIT 500). That is the
  size of the contamination this pipeline would print if it leaked the
  future. It uses past-only data everywhere, so none of it is in the numbers.

WHAT THIS MEANS FOR THE ENGINE
  W_HIGH = 0.25 is not a diluted good signal. It is a beta tilt with the
  wrong sign inside the engine's own gated pool, and the ingredient it is
  weighted above (12-1 momentum, 0.20) is the one carrying market-adjusted
  return. This lab does NOT re-weight anything — a weight change needs its
  own out-of-sample test at the level it is applied (house Rule 8) — but it
  removes the assumption that high52 was pulling its weight.
  Two honest caveats against over-reading: (i) the 52-week-high family also
  earns W_BRK20 = 0.07 via the 20-day high, which is NOT tested here;
  (ii) George-Hwang published in 2004 and McLean-Pontiff's post-publication
  haircut is ~58%, so a null in 2017-2026 is what a decayed real effect
  would also look like. The negative sign is beta; the absence of positive
  alpha is the result.

TRIAL COUNT
  N = 58 (26 measured cells per universe x 2 universes, plus 6 split-debt
  reconfigurations of the headline). Control draws are nulls and do not
  count; the Rule-13 market-adjusted figures are re-expressions of variants
  already counted, not new trials. The single best book found in the
  registered direction — the PIT-500 market-adjusted D10-D1, +130.9 bps per
  window — has an annualised gross Sharpe of 0.45 and a DEFLATED Sharpe of
  **0.336** at N=58 (0.023 for the same book on the S&P 1500). Using the
  Newey-West-inflated standard deviation instead of the sample one takes it
  to 0.40 / 0.258. Bailey-Lopez de Prado want ~1.0. Nothing here survives
  its own trial count, and the book in question is a beta hedge, not a
  signal.

LIMITS OF THIS STUDY, stated plainly
  - Sample starts 2017-05 (270-session warm-up on bars beginning 2016-04),
    109 monthly formations, effective independent sample ~54. Ten years,
    one macro era, ~3 bear episodes: this can reject a large effect, not a
    2%/yr one.
  - The S&P 1500 leg uses TODAY'S membership applied historically
    (survivorship); the PIT-500 leg is survivorship-free but large-cap only
    and carries the extra data-quality discount data_audit.py documents for
    delisted names. They disagree in magnitude and agree in sign.
  - Betas are fitted in-sample on the same windows their alphas are read
    from, which makes every alpha t-statistic here optimistic — and every
    alpha is small anyway.
  - Ties: 5.8% (S&P 1500) / 6.3% (PIT 500) of the eligible pool sits exactly
    AT its 52-week high on any given formation date, and those ties are
    broken by symbol order. Decile 10 is therefore "at the high, plus
    whoever sorts first alphabetically among the tied".

Run:
  python -m scout.high52_lab                      # both universes, guarded
  python -m scout.high52_lab --universe pit500
  python -m scout.high52_lab --no-guard           # H25k sensitivity
  python -m scout.high52_lab --draws 400
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import time

import numpy as np
import pandas as pd

from . import config, data, data_audit, growth, pit, signals, universe

BARS_CACHE = config.SCOUT_DIR / "cache_high52_bars.pkl"
SPLITS_CACHE = config.SCOUT_DIR / "cache_high52_splits.pkl"
RESULTS = config.SCOUT_DIR / "high52_results.json"

H = config.HORIZON_TDAYS        # 42-session hold
STEP = 21                       # monthly formation
WARMUP = 270                    # bars before the first formation date
BIG_MOVE = 0.45                 # |1-day| beyond which a bar is presumed corrupt
SPLIT_BAD = 0.35                # |ex-date return| implying the split was not applied
LOOKBACK = 252                  # the 52-week window the signal reads
SEED = 20260809
DRAWS = 200
BOOT_REPS = 2000
COST_BPS = 10.0                 # round trip, large caps (config-free literal: this
                                # lab charges costs, the engine does not model them)
BENCH = "SPY"


# --------------------------------------------------------------- data layer

def load_bars(no_cache: bool = False) -> dict:
    """Union panel: today's S&P 1500 plus every point-in-time S&P 500 member
    since 2016 (delisted names included), plus SPY."""
    if BARS_CACHE.exists() and not no_cache:
        with open(BARS_CACHE, "rb") as f:
            bars = pickle.load(f)
        print(f"bars from cache: {bars['close'].shape[0]} sessions x "
              f"{bars['close'].shape[1]} symbols")
        return bars
    syms = sorted({u["symbol"] for u in universe.load()}
                  | set(pit.all_members_since("2016-01-01")) | {BENCH})
    print(f"fetching {len(syms)} symbols of SIP daily bars (a few minutes)...")
    bars = data.daily_ohlcv(syms, config.CALIB_YEARS * 365 + 120)
    with open(BARS_CACHE, "wb") as f:
        pickle.dump(bars, f)
    return bars


def _fetch_splits_retry(syms: list[str], tries: int = 6) -> pd.DataFrame:
    """Same endpoint as data_audit.fetch_splits, but a rate-limited chunk is
    RETRIED instead of silently dropped — a missing split is a missing repair,
    which is exactly the failure this lab must not have. Other labs share this
    box and the corporate-actions endpoint 429s under concurrent load."""
    import requests
    rows, failed = [], 0
    for i in range(0, len(syms), 60):
        chunk, token, ok = syms[i:i + 60], None, False
        for attempt in range(tries):
            params = {"symbols": ",".join(chunk),
                      "types": "forward_split,reverse_split",
                      "start": "2015-06-01", "end": "2026-08-09", "limit": 1000}
            if token:
                params["page_token"] = token
            r = requests.get(data_audit.CA_URL, headers=data_audit._headers(),
                             params=params, timeout=60)
            if not r.ok:
                time.sleep(2 ** attempt)
                continue
            body = r.json()
            acts = body.get("corporate_actions", {})
            for kind in ("forward_splits", "reverse_splits"):
                for a in acts.get(kind, []):
                    rows.append({"symbol": a.get("symbol"), "ex_date": a.get("ex_date"),
                                 "old_rate": a.get("old_rate"),
                                 "new_rate": a.get("new_rate"), "kind": kind})
            token = body.get("next_page_token")
            if not token:
                ok = True
                break
        if not ok:
            failed += len(chunk)
    if failed:
        print(f"  WARNING: {failed} symbols' corporate actions unavailable "
              "after retries — their splits cannot be repaired")
    return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame()


def repair_splits(bars: dict, no_cache: bool = False) -> tuple[dict, list[dict]]:
    """Back-adjust every split Alpaca's bars endpoint failed to apply.

    The corporate-actions endpoint and the bars endpoint disagree inside the
    same vendor (scout/data_audit.py: 10 of 198 checkable splits unadjusted).
    A missing split is fatal for THIS signal specifically, because the 252-day
    rolling max carries the pre-split price level for a full year.
    """
    close = bars["close"]
    syms = sorted(close.columns)
    if SPLITS_CACHE.exists() and not no_cache:
        with open(SPLITS_CACHE, "rb") as f:
            splits = pickle.load(f)
    else:
        print("fetching corporate actions (splits) for the union universe...")
        splits = _fetch_splits_retry(syms)
        with open(SPLITS_CACHE, "wb") as f:
            pickle.dump(splits, f)
    if splits.empty:
        return bars, []

    checked = data_audit.check_splits(close, splits)
    bad = checked[checked["unadjusted"]].sort_values("ret_pct")
    out = {k: v.copy() for k, v in bars.items()}
    for _, row in bad.iterrows():
        sym, factor = row["symbol"], float(row["factor"])
        if not np.isfinite(factor) or factor <= 0:
            continue
        ex = pd.Timestamp(row["ex_date"], tz=close.index.tz)
        m = out["close"].index < ex
        for field in ("open", "close"):
            out[field].loc[m, sym] = out[field].loc[m, sym] / factor
        if "volume" in out:
            out["volume"].loc[m, sym] = out["volume"].loc[m, sym] * factor
    return out, bad.to_dict("records")


def contamination(close: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(signal_dirty, day_dirty) boolean frames as numpy arrays.

    signal_dirty[t, s]: the trailing 252-session window ending at t contains a
    |1-day| move above BIG_MOVE, so the 52-week max — and therefore the
    signal — is untrustworthy.
    day_dirty[t, s]: session t itself carries such a move (used to disqualify
    the forward window).
    """
    ret = close.pct_change()
    day = (ret.abs() > BIG_MOVE).fillna(False)
    sig = day.rolling(LOOKBACK, min_periods=1).max().fillna(0.0) > 0
    return sig.to_numpy(), day.to_numpy()


# ----------------------------------------------------- panel assembly (numpy)

def prep(bars: dict, guard: bool = True) -> dict:
    """One-off feature build shared by every universe and horizon."""
    c, o, v = bars["close"], bars["open"], bars["volume"]
    frames = signals.feature_frames(o, c, v)
    sig_dirty, day_dirty = contamination(c)
    if not guard:
        sig_dirty = np.zeros_like(sig_dirty)
        day_dirty = np.zeros_like(day_dirty)
    return {"index": c.index, "cols": list(c.columns), "C": c.to_numpy(),
            "F": {k: f.to_numpy() for k, f in frames.items()},
            "sig_dirty": sig_dirty, "day_dirty": day_dirty,
            "bench_series": c[BENCH].dropna(), "guard": guard}


def build_panel(ctx: dict, mode: str, horizon: int = H) -> dict:
    """Aligned formation-date arrays. Everything downstream is pure numpy.

    Returns dates, symbol list, and (n_dates x n_symbols) arrays:
      SIG   52-week-high proximity at the formation close
      MOM   12-1 momentum at the formation close
      FWD   close_{t+horizon} / close_t - 1   (partial paths use the last print)
      OPEN  eligibility mask (universe membership + finite signal + usable path)
      GATE  the repo's v5 eligible pool (composite_at's gates and vetoes)

    THE SHIFT LIVES HERE AND NOWHERE ELSE: the signal row is `[pos]`, the
    return window is `[pos+1 : pos+1+horizon]`.
    """
    cols, idx, C, F = ctx["cols"], ctx["index"], ctx["C"], ctx["F"]
    sig_dirty, day_dirty, guard = ctx["sig_dirty"], ctx["day_dirty"], ctx["guard"]
    col_i = {s: i for i, s in enumerate(cols)}

    if mode == "sp1500":
        members = {u["symbol"] for u in universe.load()}
        member_mask_static = np.array([s in members for s in cols])
    positions = list(range(WARMUP, len(idx) - horizon - 1, STEP))

    dates, SIG, MOM, FWD, OPEN, GATE = [], [], [], [], [], []
    partial = 0
    for pos in positions:
        ts = idx[pos]
        if mode == "pit500":
            mem = pit.members(ts)
            mmask = np.array([s in mem for s in cols])
        else:
            mmask = member_mask_static

        basis = C[pos]
        win = C[pos + 1: pos + 1 + horizon]
        cnt = np.isfinite(win).sum(axis=0)
        # last available print in the window (delisting-tolerant, as
        # backtest.window_outcomes does for point-in-time mode)
        last = pd.DataFrame(win).ffill().to_numpy()[-1]
        need = 5 if mode == "pit500" else horizon
        path_ok = (cnt >= need) & np.isfinite(basis) & np.isfinite(last) & (basis > 0)
        partial += int(((cnt >= need) & (cnt < horizon)).sum())
        fwd = np.where(path_ok, last / np.where(basis == 0, np.nan, basis) - 1.0, np.nan)

        fwd_clean = ~day_dirty[pos + 1: pos + 1 + horizon].any(axis=0)
        sig_row = F["high"][pos]
        mom_row = F["mom"][pos]
        need_cols = ["mom", "mom6", "high", "vol", "ret1m", "max21", "pos252", "brk20"]
        finite = np.all([np.isfinite(F[k][pos]) for k in need_cols], axis=0)

        open_mask = (mmask & finite & path_ok & np.isfinite(fwd)
                     & ~sig_dirty[pos] & fwd_clean)
        if open_mask.sum() < 50:
            continue

        # the repo's own eligible pool, cross-sectional deciles taken inside
        # the same membership the engine would have seen that day
        sub = {k: F[k][pos] for k in ("vol", "max21", "ret6", "ret1m",
                                      "sma200ok", "dvol20")}
        pool = mmask & finite
        vol_pct = _rank_pct_masked(sub["vol"], pool)
        max_pct = _rank_pct_masked(sub["max21"], pool)
        gate = (open_mask
                & (sub["sma200ok"] == 1.0)
                & (sub["ret6"] > 0)
                & (sub["ret1m"] <= config.VETO_RET1M_HI)
                & (sub["ret1m"] >= config.VETO_RET1M_LO)
                & (vol_pct < config.VETO_VOL_DECILE)
                & (max_pct < config.VETO_MAX21_DECILE)
                & (sub["dvol20"] >= config.MIN_DOLLAR_VOL))

        dates.append(ts)
        SIG.append(sig_row)
        MOM.append(mom_row)
        FWD.append(fwd)
        OPEN.append(open_mask)
        GATE.append(gate)

    bench_i = col_i.get(BENCH)
    bench = []
    for pos in [idx.get_loc(d) for d in dates]:
        b0, b1 = C[pos, bench_i], C[pos + horizon, bench_i]
        bench.append(b1 / b0 - 1 if np.isfinite(b0) and np.isfinite(b1) else np.nan)
    spy = ctx["bench_series"]
    bull = (spy > spy.rolling(200).mean()).reindex(idx)

    return {"mode": mode, "horizon": horizon, "guard": guard,
            "dates": dates, "cols": cols,
            "SIG": np.array(SIG), "MOM": np.array(MOM), "FWD": np.array(FWD),
            "OPEN": np.array(OPEN), "GATE": np.array(GATE),
            "bench": np.array(bench, float),
            "bull": np.array([bool(bull.loc[d]) if pd.notna(bull.loc[d]) else True
                              for d in dates]),
            "partial_paths": partial}


def _rank_pct_masked(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank computed WITHIN `mask` (NaN elsewhere)."""
    out = np.full(len(x), np.nan)
    v = x[mask]
    ok = np.isfinite(v)
    if ok.sum() == 0:
        return out
    r = np.empty(len(v))
    r[:] = np.nan
    order = np.argsort(np.argsort(v[ok], kind="stable"), kind="stable")
    r[ok] = (order + 1) / ok.sum()
    out[mask] = r
    return out


# ------------------------------------------------------------- estimators

def _rank_pct(x: np.ndarray) -> np.ndarray:
    order = np.argsort(np.argsort(x, kind="stable"), kind="stable")
    return (order + 1) / len(x)


def bucket_means(sig: np.ndarray, fwd: np.ndarray, nq: int) -> np.ndarray:
    """Equal-count bucket means of `fwd`, buckets low->high on `sig`.
    Ties are broken by symbol order (stable sort) — deterministic and
    unrelated to the outcome."""
    n = len(sig)
    if n < nq * 2:
        return np.full(nq, np.nan)
    order = np.argsort(sig, kind="stable")
    f = fwd[order]
    edges = (np.arange(nq + 1) * n) // nq
    return np.array([f[edges[k]:edges[k + 1]].mean() for k in range(nq)])


def decile_series(panel: dict, nq: int, gated: bool = False,
                  col: str = "SIG") -> dict:
    """Per-formation-date bucket means, spread, pool mean and pool size."""
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    rows, spread, pool, sizes = [], [], [], []
    for i in range(len(panel["dates"])):
        m = mask_all[i]
        if m.sum() < max(nq * 2, 30):
            rows.append(np.full(nq, np.nan))
            spread.append(np.nan)
            pool.append(np.nan)
            sizes.append(int(m.sum()))
            continue
        b = bucket_means(panel[col][i][m], panel["FWD"][i][m], nq)
        rows.append(b)
        spread.append(b[-1] - b[0])
        pool.append(float(panel["FWD"][i][m].mean()))
        sizes.append(int(m.sum()))
    return {"buckets": np.array(rows), "spread": np.array(spread),
            "pool": np.array(pool), "size": np.array(sizes), "nq": nq}


def nw_se(x: np.ndarray, lag: int) -> float:
    """Newey-West standard error of the mean of an overlapping series."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    e = x - x.mean()
    s = float(e @ e) / n
    for l in range(1, lag + 1):
        s += 2.0 * (1 - l / (lag + 1)) * float(e[l:] @ e[:-l]) / n
    return math.sqrt(max(s, 1e-18) / n)


def block_boot_ci(x: np.ndarray, block: int, reps: int = BOOT_REPS,
                  seed: int = SEED) -> tuple[float, float]:
    """Moving-block bootstrap CI for the mean. One observation per FORMATION
    DATE, so resampling is date-clustered (scout/calibrate.py's discipline);
    the block length is what additionally respects overlapping holds."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3 * block:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n]
    means = x[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def stats(x: np.ndarray, lag: int = 1) -> dict:
    x = np.asarray(x, float)
    v = x[np.isfinite(x)]
    if len(v) < 3:
        return {"n": len(v), "mean_bps": None}
    se = nw_se(v, lag)
    lo, hi = block_boot_ci(v, block=lag + 1)
    half = len(v) // 2
    return {"n": int(len(v)),
            "mean_bps": round(1e4 * float(v.mean()), 1),
            "sd_bps": round(1e4 * float(v.std(ddof=1)), 1),
            "nw_t": round(float(v.mean()) / se, 2) if se > 0 else None,
            "nw_se_bps": round(1e4 * se, 1),
            "ci_lo_bps": round(1e4 * lo, 1), "ci_hi_bps": round(1e4 * hi, 1),
            "h1_bps": round(1e4 * float(v[:half].mean()), 1),
            "h2_bps": round(1e4 * float(v[half:].mean()), 1),
            "pos_frac": round(float((v > 0).mean()), 3),
            "worst_bps": round(1e4 * float(v.min()), 1),
            "best_bps": round(1e4 * float(v.max()), 1)}


def phase_split(x: np.ndarray, phases: int) -> list[dict]:
    """RESEARCH-AGENDA Rule 9: a 42-td hold formed every 21 td silently picks
    one of `phases` non-overlapping entry schedules. Report each."""
    out = []
    for p in range(phases):
        v = x[p::phases]
        v = v[np.isfinite(v)]
        if len(v) < 3:
            out.append({"phase": p, "n": len(v), "mean_bps": None})
            continue
        se = nw_se(v, 0)                      # this subset does NOT overlap
        out.append({"phase": p, "n": int(len(v)),
                    "mean_bps": round(1e4 * float(v.mean()), 1),
                    "t": round(float(v.mean()) / se, 2) if se > 0 else None})
    return out


# ---------------------------------------------------------------- controls

def null_random(panel: dict, nq: int, gated: bool, draws: int,
                seed: int = SEED) -> dict:
    """Random-decile assignment from the identical eligible pool."""
    rng = np.random.default_rng(seed)
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    n_dates = len(panel["dates"])
    means = np.empty(draws)
    series = np.empty((draws, n_dates))
    series[:] = np.nan
    for d in range(draws):
        for i in range(n_dates):
            m = mask_all[i]
            if m.sum() < max(nq * 2, 30):
                continue
            f = panel["FWD"][i][m]
            p = rng.permutation(f)
            edges = (np.arange(nq + 1) * len(p)) // nq
            series[d, i] = p[edges[nq - 1]:].mean() - p[:edges[1]].mean()
        means[d] = np.nanmean(series[d])
    return {"draws": draws, "mean_bps": round(1e4 * float(means.mean()), 2),
            "se_bps": round(1e4 * float(means.std(ddof=1)), 2),
            "lo_bps": round(1e4 * float(np.percentile(means, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(means, 97.5)), 1)}


STALE = 12          # donor dates must be >= 12 formations (~1 yr) in the past


def null_dateshuffle(panel: dict, nq: int, gated: bool, draws: int,
                     seed: int = SEED, future: bool = False) -> dict:
    """H15's killer control: score each date with ANOTHER date's high52
    snapshot. It keeps 'which stocks habitually sit near their highs' intact
    and destroys only the timing, so if it reproduces the spread the effect is
    a stock-identity property, not a signal.

    THE DONOR MUST BE IN THE PAST. A donor date j > i reads closes from inside
    (or after) date i's own holding window, so a stock near its 52-week high
    at j has BY CONSTRUCTION risen during window i — the control would then
    manufacture a large positive spread out of pure lookahead. Donors are
    drawn from j <= i - STALE, which is both lookahead-free and a full year
    stale, and the real series is re-measured on the same date subset so the
    comparison is like-for-like.
    """
    rng = np.random.default_rng(seed + 1)
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    n_dates = len(panel["dates"])
    usable = ([i for i in range(n_dates - STALE)] if future
              else [i for i in range(n_dates) if i >= STALE])
    means = np.empty(draws)
    for d in range(draws):
        vals = []
        for i in usable:
            j = (int(rng.integers(i + STALE, n_dates)) if future
                 else int(rng.integers(0, i - STALE + 1)))
            m = mask_all[i] & np.isfinite(panel["SIG"][j])
            if m.sum() < max(nq * 2, 30):
                continue
            b = bucket_means(panel["SIG"][j][m], panel["FWD"][i][m], nq)
            vals.append(b[-1] - b[0])
        means[d] = float(np.mean(vals)) if vals else np.nan
    means = means[np.isfinite(means)]
    return {"draws": int(len(means)), "dates_used": len(usable),
            "donor_rule": (f"j >= i + {STALE} (FUTURE — deliberate lookahead)"
                           if future else
                           f"j <= i - {STALE} (past only, >= 1 yr stale)"),
            "mean_bps": round(1e4 * float(means.mean()), 2),
            "se_bps": round(1e4 * float(means.std(ddof=1)), 2),
            "lo_bps": round(1e4 * float(np.percentile(means, 2.5)), 1),
            "hi_bps": round(1e4 * float(np.percentile(means, 97.5)), 1)}


# --------------------------------------------------------------- horse race

def rank_correlation(panel: dict, gated: bool = False) -> dict:
    """Average cross-sectional Spearman rho between high52 and 12-1 momentum."""
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    rhos = []
    for i in range(len(panel["dates"])):
        m = mask_all[i]
        if m.sum() < 30:
            continue
        a, b = _rank_pct(panel["SIG"][i][m]), _rank_pct(panel["MOM"][i][m])
        rhos.append(float(np.corrcoef(a, b)[0, 1]))
    return {"mean_rho": round(float(np.mean(rhos)), 3),
            "min": round(float(np.min(rhos)), 3),
            "max": round(float(np.max(rhos)), 3), "dates": len(rhos)}


def double_sort(panel: dict, nq_ctrl: int = 3, nq_sig: int = 3,
                gated: bool = False, control: str = "MOM",
                signal: str = "SIG") -> dict:
    """Conditional sort: split on `control` first, then bucket on `signal`
    INSIDE each control bucket. This is the George-Hwang claim's real test."""
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    cells = np.full((len(panel["dates"]), nq_ctrl, nq_sig), np.nan)
    for i in range(len(panel["dates"])):
        m = mask_all[i]
        if m.sum() < nq_ctrl * nq_sig * 5:
            continue
        cv, sv, fv = panel[control][i][m], panel[signal][i][m], panel["FWD"][i][m]
        order = np.argsort(cv, kind="stable")
        edges = (np.arange(nq_ctrl + 1) * len(cv)) // nq_ctrl
        for k in range(nq_ctrl):
            sl = order[edges[k]:edges[k + 1]]
            cells[i, k] = bucket_means(sv[sl], fv[sl], nq_sig)
    out = {"nq_ctrl": nq_ctrl, "nq_sig": nq_sig, "control": control,
           "signal": signal, "grid": [], "within": [], "within_beta": []}
    for k in range(nq_ctrl):
        out["grid"].append([round(1e4 * float(np.nanmean(cells[:, k, q])), 1)
                            for q in range(nq_sig)])
        sp = cells[:, k, -1] - cells[:, k, 0]
        out["within"].append(stats(sp))
        b, _ = beta_to_bench(sp, panel["bench"])
        out["within_beta"].append(b)
    return out


def decile_betas(ds: dict, bench: np.ndarray) -> dict:
    """Each bucket's SPY beta and its market-adjusted mean return.

    A high52 sort is suspected of being a BETA sort: a stock far below its
    52-week high is a stock that has recently fallen, and fallen stocks carry
    higher betas. If the beta profile slopes monotonically, the raw decile
    profile is a risk profile and says nothing about anchoring."""
    betas, adj = [], []
    for k in range(ds["nq"]):
        x = ds["buckets"][:, k]
        b, _ = beta_to_bench(x, bench)
        betas.append(b.get("beta"))
        adj.append(b.get("alpha_bps"))
    return {"beta": betas, "alpha_bps": adj}


def fama_macbeth(panel: dict, gated: bool = False) -> dict:
    """Per-date cross-sectional OLS of the forward 42-td return on centered
    percentile ranks of high52 and 12-1 momentum; coefficients averaged with
    Newey-West lag-1 t-statistics (Fama-MacBeth with overlapping holds).

    A coefficient is the top-to-bottom return difference implied by the rank,
    so it is directly comparable to a decile spread (D10-D1 covers about 0.9
    of the rank range)."""
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    lam_uni_h, lam_uni_m, lam_h, lam_m = [], [], [], []
    for i in range(len(panel["dates"])):
        m = mask_all[i]
        if m.sum() < 50:
            continue
        y = panel["FWD"][i][m]
        h = _rank_pct(panel["SIG"][i][m]) - 0.5
        mo = _rank_pct(panel["MOM"][i][m]) - 0.5
        one = np.ones(len(y))
        lam_uni_h.append(np.linalg.lstsq(np.column_stack([one, h]), y, rcond=None)[0][1])
        lam_uni_m.append(np.linalg.lstsq(np.column_stack([one, mo]), y, rcond=None)[0][1])
        b = np.linalg.lstsq(np.column_stack([one, h, mo]), y, rcond=None)[0]
        lam_h.append(b[1])
        lam_m.append(b[2])
    return {"high52_alone": stats(np.array(lam_uni_h)),
            "mom12_alone": stats(np.array(lam_uni_m)),
            "high52_joint": stats(np.array(lam_h)),
            "mom12_joint": stats(np.array(lam_m))}


def residual_signal(panel: dict, gated: bool = False) -> np.ndarray:
    """high52 rank orthogonalized to the 12-1 momentum rank, per date."""
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    RES = np.full(panel["SIG"].shape, np.nan)
    for i in range(len(panel["dates"])):
        m = mask_all[i]
        if m.sum() < 50:
            continue
        h = _rank_pct(panel["SIG"][i][m])
        mo = _rank_pct(panel["MOM"][i][m])
        X = np.column_stack([np.ones(len(mo)), mo])
        beta = np.linalg.lstsq(X, h, rcond=None)[0]
        RES[i][m] = h - X @ beta
    return RES


# ------------------------------------------------------------------- costs

def turnover(panel: dict, nq: int, gated: bool, top: bool = True,
             col: str = "SIG", phases: int = 2) -> float:
    """One-way turnover of an extreme bucket per 42-session hold, measured on
    the non-overlapping entry schedules only (consecutive formation dates are
    21 td apart; the tradeable book turns over once per HOLD)."""
    mask_all = panel["GATE"] if gated else panel["OPEN"]
    turns = []
    for p in range(phases):
        prev = None
        for i in range(p, len(panel["dates"]), phases):
            m = mask_all[i]
            if m.sum() < max(nq * 2, 30):
                prev = None
                continue
            sig = panel[col][i][m]
            names = np.flatnonzero(m)[np.argsort(sig, kind="stable")]
            k = len(names) // nq
            cur = set(names[-k:] if top else names[:k])
            if prev is not None and cur:
                turns.append(1.0 - len(cur & prev) / len(cur))
            prev = cur
    return float(np.mean(turns)) if turns else float("nan")


def beta_to_bench(x: np.ndarray, bench: np.ndarray) -> dict:
    """House Rule 13: a dollar-neutral book is not market-neutral. Regress
    before quoting a sign.

    The beta is fitted in-sample on the same windows the alpha is read from,
    which makes the alpha t-statistic OPTIMISTIC — stated here rather than
    hidden. The market-adjusted series (alpha + residual) is returned so its
    two halves can be inspected."""
    ok = np.isfinite(x) & np.isfinite(bench)
    if ok.sum() < 10:
        return {}, np.array([])
    X = np.column_stack([np.ones(ok.sum()), bench[ok]])
    b = np.linalg.lstsq(X, x[ok], rcond=None)[0]
    resid = x[ok] - X @ b
    se = nw_se(resid, 1) * math.sqrt(len(resid) / max(len(resid) - 2, 1))
    adj = np.full(len(x), np.nan)
    adj[ok] = b[0] + resid
    half = ok.sum() // 2
    return {"alpha_bps": round(1e4 * float(b[0]), 1),
            "beta": round(float(b[1]), 3),
            "alpha_t": round(float(b[0]) / se, 2) if se > 0 else None,
            "alpha_h1_bps": round(1e4 * float(adj[ok][:half].mean()), 1),
            "alpha_h2_bps": round(1e4 * float(adj[ok][half:].mean()), 1)}, adj


# ------------------------------------------------------------------ report

def fmt(s: dict | None) -> str:
    if not s or s.get("mean_bps") is None:
        return f"{'n/q':>90}"
    return (f"{s['mean_bps']:>9.1f}{s['nw_t']:>8.2f}"
            f"{s['ci_lo_bps']:>10.1f}{s['ci_hi_bps']:>10.1f}"
            f"{s['h1_bps']:>10.1f}{s['h2_bps']:>10.1f}"
            f"{s['pos_frac']:>8.2f}{s['worst_bps']:>10.1f}{s['n']:>6}")


HDR = (f"{'variant':<40}{'mean bps':>9}{'NW t':>8}{'ci lo':>10}{'ci hi':>10}"
       f"{'half1':>10}{'half2':>10}{'pos%':>8}{'worst':>10}{'n':>6}")


def run_universe(ctx: dict, mode: str, draws: int, guard: bool,
                 horizons: tuple[int, ...]) -> dict:
    print(f"\n{'=' * 118}\n=== UNIVERSE {mode}  (guard={'ON' if guard else 'OFF'})\n{'=' * 118}")
    panel = build_panel(ctx, mode, horizon=H)
    n = len(panel["dates"])
    phases = max(1, H // STEP)
    print(f"{n} formation dates {panel['dates'][0].date()} .. {panel['dates'][-1].date()}"
          f"  |  hold {H} td, formed every {STEP} td  ->  {phases} non-overlapping "
          f"entry phases, effective independent sample ~{n // phases}")
    open_sz = panel["OPEN"].sum(axis=1)
    gate_sz = panel["GATE"].sum(axis=1)
    print(f"pool sizes: eligible mean {open_sz.mean():.0f} "
          f"(min {open_sz.min()}, max {open_sz.max()}); "
          f"repo-gated mean {gate_sz.mean():.0f} "
          f"(min {gate_sz.min()}, max {gate_sz.max()})")
    at_high = [(panel["SIG"][i][panel["OPEN"][i]] >= 0.9999).mean()
               for i in range(n)]
    print(f"share of the eligible pool sitting exactly AT its 52-week high: "
          f"{100 * float(np.mean(at_high)):.1f}% (ties broken by symbol order)")
    print(f"partial forward paths kept (delisting-tolerant): {panel['partial_paths']}")

    out = {"mode": mode, "guard": guard, "dates": n,
           "span": [str(panel["dates"][0].date()), str(panel["dates"][-1].date())],
           "phases": phases, "pool_mean": float(open_sz.mean()),
           "gated_pool_mean": float(gate_sz.mean())}

    # ---------------------------------------------------------- H25a/b/c/d
    print(f"\n--- decile / quintile sorts, {H}-session hold, equal weight ---")
    print(HDR)
    rows = {}
    for gated in (False, True):
        tag = "gated pool" if gated else "all eligible"
        for nq in (10, 5):
            ds = decile_series(panel, nq, gated=gated, col="SIG")
            s = stats(ds["spread"])
            rows[f"high52 D{nq}-D1 [{tag}]"] = (s, ds)
            print(f"{'high52 top-bottom /' + str(nq) + ' [' + tag + ']':<40}{fmt(s)}")
            dm = decile_series(panel, nq, gated=gated, col="MOM")
            sm = stats(dm["spread"])
            rows[f"mom12 D{nq}-D1 [{tag}]"] = (sm, dm)
            print(f"{'mom12  top-bottom /' + str(nq) + ' [' + tag + ']':<40}{fmt(sm)}")

    d10 = decile_series(panel, 10, gated=False, col="SIG")
    d10g = decile_series(panel, 10, gated=True, col="SIG")
    m10 = decile_series(panel, 10, gated=False, col="MOM")
    out["deciles_ungated"] = [round(1e4 * float(np.nanmean(d10["buckets"][:, k])), 1)
                              for k in range(10)]
    out["deciles_gated"] = [round(1e4 * float(np.nanmean(d10g["buckets"][:, k])), 1)
                            for k in range(10)]
    out["deciles_mom_ungated"] = [round(1e4 * float(np.nanmean(m10["buckets"][:, k])), 1)
                                  for k in range(10)]
    print("\ndecile means (bps per 42 td), low proximity -> high proximity:")
    print("  high52 ungated : " + " ".join(f"{v:>7.0f}" for v in out["deciles_ungated"]))
    print("  high52 gated   : " + " ".join(f"{v:>7.0f}" for v in out["deciles_gated"]))
    print("  mom12  ungated : " + " ".join(f"{v:>7.0f}" for v in out["deciles_mom_ungated"]))
    print(f"  equal-weight eligible pool: "
          f"{1e4 * float(np.nanmean(d10['pool'])):.0f} bps   "
          f"SPY over the same windows: {1e4 * float(np.nanmean(panel['bench'])):.0f} bps")

    db = decile_betas(d10, panel["bench"])
    dbm = decile_betas(m10, panel["bench"])
    out["decile_betas_high52"] = db
    out["decile_betas_mom12"] = dbm
    print("\nis the sort a RISK sort? SPY beta and market-adjusted mean per decile:")
    print("  high52 beta    : " + " ".join(f"{v:>7.2f}" for v in db["beta"]))
    print("  high52 mkt-adj : " + " ".join(f"{v:>7.0f}" for v in db["alpha_bps"]))
    print("  mom12  beta    : " + " ".join(f"{v:>7.2f}" for v in dbm["beta"]))
    print("  mom12  mkt-adj : " + " ".join(f"{v:>7.0f}" for v in dbm["alpha_bps"]))

    out["spreads"] = {k: v[0] for k, v in rows.items()}

    # ------------------------------------------------------------ Rule 9
    print("\n--- Rule 9: non-overlapping entry phases (high52 D10-D1, ungated) ---")
    out["phases_high52"] = phase_split(d10["spread"], phases)
    for p in out["phases_high52"]:
        print(f"  phase {p['phase']}: n={p['n']:<4} mean {p['mean_bps']} bps  t={p['t']}")

    # ----------------------------------------------------------- controls
    print(f"\n--- CONTROLS ({draws} draws each; Rule 14 prints null SE / real NW SE) ---")
    real = stats(d10["spread"])
    real_stale = stats(d10["spread"][STALE:])       # like-for-like with the shuffle
    nr = null_random(panel, 10, False, draws)
    nd = null_dateshuffle(panel, 10, False, draws)
    for name, nul, ref in (("random decile from same pool", nr, real),
                           ("DATE-SHUFFLED high52 (past donors)", nd, real_stale)):
        ratio = nul["se_bps"] / ref["nw_se_bps"] if ref["nw_se_bps"] else float("nan")
        z = (ref["mean_bps"] - nul["mean_bps"]) / nul["se_bps"] if nul["se_bps"] else None
        print(f"  {name:<36} null {nul['mean_bps']:>8.2f} bps  "
              f"95% [{nul['lo_bps']:>7.1f},{nul['hi_bps']:>7.1f}]  real {ref['mean_bps']:>8.1f}  "
              f"nullSE/realNWSE {ratio:>5.2f}  z {z:>6.2f}")
    nf = null_dateshuffle(panel, 10, False, max(20, draws // 4), future=True)
    out["null_random"] = nr
    out["null_dateshuffle"] = nd
    out["lookahead_detector"] = nf
    out["real_spread"] = real
    out["real_spread_stale_subset"] = real_stale
    swing = nf["mean_bps"] - nd["mean_bps"]
    out["lookahead_swing_bps"] = round(swing, 2)
    print(f"  {'LOOKAHEAD DETECTOR (donors from the FUTURE)':<36} "
          f"null {nf['mean_bps']:>8.2f} bps  95% [{nf['lo_bps']:>7.1f},"
          f"{nf['hi_bps']:>7.1f}]   swing vs past-donor null {swing:+.1f} bps")
    print("    ^ the SAME estimator with only the donor's time direction "
          "inverted. Not a control —\n      a self-test. The swing is what this "
          "pipeline WOULD print if it leaked the future;\n      every reported "
          "figure uses past-only data, so none of it is in them.")

    # ------------------------------------------------------ Rule 13 / bench
    print("\n--- Rule 13: regress every book on SPY before quoting its sign ---")
    print("    (beta fitted in-sample on the same windows -> alpha t is optimistic)")
    ls = d10["spread"]
    lo_excess = d10["buckets"][:, -1] - d10["pool"]
    out["beta_ls"], adj_ls = beta_to_bench(ls, panel["bench"])
    out["beta_longonly"], _ = beta_to_bench(d10["buckets"][:, -1], panel["bench"])
    out["beta_longonly_excess"], adj_lo = beta_to_bench(lo_excess, panel["bench"])
    out["beta_ls_gated"], _ = beta_to_bench(d10g["spread"], panel["bench"])
    out["beta_ls_mom"], _ = beta_to_bench(m10["spread"], panel["bench"])
    for lab, b in (("high52 D10-D1", out["beta_ls"]),
                   ("high52 D10-D1 [gated]", out["beta_ls_gated"]),
                   ("mom12  D10-D1", out["beta_ls_mom"]),
                   ("high52 D10 long-only", out["beta_longonly"]),
                   ("high52 D10 minus pool", out["beta_longonly_excess"])):
        print(f"  {lab:<26} beta {b['beta']:>7.3f}   alpha {b['alpha_bps']:>8.1f} bps  "
              f"t {b['alpha_t']:>6.2f}   halves {b['alpha_h1_bps']:>8.1f} / "
              f"{b['alpha_h2_bps']:>8.1f}")
    out["market_adj_ls"] = stats(adj_ls)
    print(f"\n  {'market-adjusted high52 D10-D1':<40}{fmt(out['market_adj_ls'])}")

    order = np.argsort(np.where(np.isfinite(ls), ls, np.inf))[:5]
    print("\n  five worst high52 D10-D1 windows (formation date -> spread, SPY):")
    for i in order:
        print(f"    {panel['dates'][i].date()}  {1e4 * ls[i]:>9.0f} bps   "
              f"SPY {1e4 * panel['bench'][i]:>8.0f} bps   "
              f"{'bull' if panel['bull'][i] else 'BEAR'}")

    # -------------------------------------------------------- horse race
    print("\n--- HORSE RACE: 52-week-high proximity vs 12-1 momentum ---")
    rc = rank_correlation(panel, gated=False)
    rcg = rank_correlation(panel, gated=True)
    out["rank_corr"] = rc
    out["rank_corr_gated"] = rcg
    print(f"  cross-sectional Spearman rho(high52, mom12): "
          f"{rc['mean_rho']} [{rc['min']}, {rc['max']}] over {rc['dates']} dates; "
          f"inside the gated pool {rcg['mean_rho']}")

    ds3 = double_sort(panel, 3, 3, gated=False, control="MOM", signal="SIG")
    out["double_sort_mom_then_high"] = ds3
    print("\n  CONDITIONAL SORT — momentum tercile first, then high52 tercile")
    print(f"  {'':<22}{'lowH':>9}{'midH':>9}{'highH':>9}   "
          f"{'highH-lowH':>11}{'NW t':>7}{'half1':>9}{'half2':>9}")
    labels = ["low mom12", "mid mom12", "high mom12"]
    for k in range(3):
        g, w, b = ds3["grid"][k], ds3["within"][k], ds3["within_beta"][k]
        print(f"  {labels[k]:<22}{g[0]:>9.0f}{g[1]:>9.0f}{g[2]:>9.0f}   "
              f"{w['mean_bps']:>11.0f}{w['nw_t']:>7.2f}"
              f"{w['h1_bps']:>9.0f}{w['h2_bps']:>9.0f}"
              f"   | beta {b['beta']:>6.2f}  mkt-adj {b['alpha_bps']:>7.0f} "
              f"t {b['alpha_t']:>5.2f}")

    ds3r = double_sort(panel, 3, 3, gated=False, control="SIG", signal="MOM")
    out["double_sort_high_then_mom"] = ds3r
    print("\n  REVERSE — high52 tercile first, then momentum tercile")
    print(f"  {'':<22}{'lowM':>9}{'midM':>9}{'highM':>9}   "
          f"{'highM-lowM':>11}{'NW t':>7}{'half1':>9}{'half2':>9}")
    labels = ["low high52", "mid high52", "high high52"]
    for k in range(3):
        g, w, b = ds3r["grid"][k], ds3r["within"][k], ds3r["within_beta"][k]
        print(f"  {labels[k]:<22}{g[0]:>9.0f}{g[1]:>9.0f}{g[2]:>9.0f}   "
              f"{w['mean_bps']:>11.0f}{w['nw_t']:>7.2f}"
              f"{w['h1_bps']:>9.0f}{w['h2_bps']:>9.0f}"
              f"   | beta {b['beta']:>6.2f}  mkt-adj {b['alpha_bps']:>7.0f} "
              f"t {b['alpha_t']:>5.2f}")

    fm = fama_macbeth(panel, gated=False)
    out["fama_macbeth"] = fm
    print("\n  FAMA-MACBETH (coefficients are top-to-bottom rank differences, bps)")
    print(f"  {'model':<40}{'mean bps':>9}{'NW t':>8}{'ci lo':>10}{'ci hi':>10}"
          f"{'half1':>10}{'half2':>10}{'pos%':>8}{'worst':>10}{'n':>6}")
    for k, lab in (("high52_alone", "high52 alone"),
                   ("mom12_alone", "mom12 alone"),
                   ("high52_joint", "high52 | controlling for mom12"),
                   ("mom12_joint", "mom12 | controlling for high52")):
        print(f"  {lab:<40}{fmt(fm[k])}")

    RES = residual_signal(panel, gated=False)
    panel["RES"] = RES
    dr = decile_series(panel, 10, gated=False, col="RES")
    out["residual_spread"] = stats(dr["spread"])
    out["residual_beta"], adj_res = beta_to_bench(dr["spread"], panel["bench"])
    print(f"\n  {'high52 orthogonalized to mom12, D10-D1':<40}{fmt(out['residual_spread'])}")
    print(f"  {'  ... same book, market-adjusted':<40}{fmt(stats(adj_res))}"
          f"   beta {out['residual_beta']['beta']:.2f}")
    out["residual_spread_mktadj"] = stats(adj_res)

    # -------------------------------------------------- crash claim (H25j)
    bull = panel["bull"]
    out["crash"] = {
        "high52_bear_bps": round(1e4 * float(np.nanmean(ls[~bull])), 1) if (~bull).any() else None,
        "high52_bull_bps": round(1e4 * float(np.nanmean(ls[bull])), 1),
        "mom_bear_bps": round(1e4 * float(np.nanmean(m10["spread"][~bull])), 1) if (~bull).any() else None,
        "mom_bull_bps": round(1e4 * float(np.nanmean(m10["spread"][bull])), 1),
        "high52_worst_bps": round(1e4 * float(np.nanmin(ls)), 1),
        "mom_worst_bps": round(1e4 * float(np.nanmin(m10["spread"])), 1),
        "bear_dates": int((~bull).sum())}
    print(f"\n--- H25j crash claim (bear = SPY < 200d SMA at formation, "
          f"{out['crash']['bear_dates']} of {n} dates) ---")
    print(f"  high52 D10-D1  bull {out['crash']['high52_bull_bps']:>8} bps   "
          f"bear {out['crash']['high52_bear_bps']:>8} bps   "
          f"worst window {out['crash']['high52_worst_bps']:>8} bps")
    print(f"  mom12  D10-D1  bull {out['crash']['mom_bull_bps']:>8} bps   "
          f"bear {out['crash']['mom_bear_bps']:>8} bps   "
          f"worst window {out['crash']['mom_worst_bps']:>8} bps")

    # ------------------------------------------------------- costs (H25h)
    print("\n--- COSTS: measured turnover and the break-even round-trip cost ---")
    cost = {}
    for gated, ds in (("all eligible", d10), ("gated pool", d10g)):
        g = gated == "gated pool"
        t_long = turnover(panel, 10, g, top=True, phases=phases)
        t_short = turnover(panel, 10, g, top=False, phases=phases)
        sp = float(np.nanmean(ds["spread"]))
        lo = float(np.nanmean(ds["buckets"][:, -1] - ds["pool"]))
        be_ls = 1e4 * sp / (t_long + t_short) if (t_long + t_short) > 0 else float("nan")
        be_lo = 1e4 * lo / t_long if t_long > 0 else float("nan")
        net_ls = 1e4 * sp - COST_BPS * (t_long + t_short)
        net_lo = 1e4 * lo - COST_BPS * t_long
        cost[gated] = {"turnover_long": round(t_long, 3),
                       "turnover_short": round(t_short, 3),
                       "gross_ls_bps": round(1e4 * sp, 1),
                       "net_ls_bps_10": round(net_ls, 1),
                       "net_ls_bps_20": round(1e4 * sp - 2 * COST_BPS * (t_long + t_short), 1),
                       "breakeven_ls_bps": round(be_ls, 1),
                       "gross_longonly_excess_bps": round(1e4 * lo, 1),
                       "net_longonly_bps_10": round(net_lo, 1),
                       "breakeven_longonly_bps": round(be_lo, 1)}
        print(f"  [{gated}] one-way turnover per {H}-td hold: "
              f"long {t_long:.2f}  short {t_short:.2f}")
        print(f"      D10-D1  gross {1e4 * sp:>8.1f} bps   net@10bps {net_ls:>8.1f}   "
              f"net@20bps {1e4 * sp - 2 * COST_BPS * (t_long + t_short):>8.1f}   "
              f"BREAK-EVEN {be_ls:>8.1f} bps")
        print(f"      D10-pool gross {1e4 * lo:>7.1f} bps   net@10bps {net_lo:>8.1f}   "
              f"BREAK-EVEN {be_lo:>8.1f} bps")
    out["costs"] = cost

    sr = growth.sharpe(ds_series := d10["spread"][np.isfinite(d10["spread"])],
                       periods_per_year=252 / H)
    sr_lo = growth.sharpe(lo_excess[np.isfinite(lo_excess)], periods_per_year=252 / H)
    out["sharpe_ls_gross"] = round(sr, 3)
    out["sharpe_longonly_excess_gross"] = round(sr_lo, 3)
    print(f"  gross annualized Sharpe: D10-D1 {sr:.2f}   D10-minus-pool {sr_lo:.2f} "
          f"({len(ds_series)} windows/yr basis {252 / H:.1f})")

    # ------------------------------------------- horizon sensitivity (H25i)
    print("\n--- H25i horizon sensitivity (D10-D1, ungated, same guard) ---")
    hz = {}
    for h in horizons:
        if h == H:
            s, sg = real, stats(d10g["spread"])
        else:
            p2 = build_panel(ctx, mode, horizon=h)
            lag = max(1, int(math.ceil(h / STEP)) - 1)
            s = stats(decile_series(p2, 10, gated=False, col="SIG")["spread"], lag=lag)
            sg = stats(decile_series(p2, 10, gated=True, col="SIG")["spread"], lag=lag)
        hz[h] = {"ungated": s, "gated": sg}
        print(f"  {'hold ' + str(h) + ' sessions  [all eligible]':<40}{fmt(s)}")
        print(f"  {'hold ' + str(h) + ' sessions  [gated pool]':<40}{fmt(sg)}")
    out["horizons"] = hz
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.high52_lab")
    ap.add_argument("--universe", default="both",
                    choices=["sp1500", "pit500", "both"])
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--no-guard", action="store_true",
                    help="H25k: rerun with the |1-day|>45% mask OFF")
    ap.add_argument("--no-repair", action="store_true",
                    help="H25k: also skip the corporate-actions split repair — "
                         "i.e. run on the bars exactly as Alpaca serves them")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--horizons", default="21,42,126")
    ap.add_argument("--trials", type=int, default=58,
                    help="registry trial count for the deflated Sharpe: 26 "
                         "measured cells per universe x 2, plus the 6 "
                         "split-debt reconfigurations of the headline")
    args = ap.parse_args()

    bars = load_bars(args.no_cache)
    if args.no_repair:
        repaired = []
        print("\nSPLIT REPAIR SKIPPED (--no-repair): running on the bars exactly "
              "as Alpaca serves them, unadjusted splits and all.")
    else:
        bars, repaired = repair_splits(bars, args.no_cache)
        print(f"\nSPLIT REPAIR: {len(repaired)} splits were in Alpaca's "
              f"corporate-actions feed but NOT applied to its bars — back-adjusted.")
    for r in repaired[:14]:
        print(f"  {r['symbol']:<6} {r['ex_date']}  factor {r['factor']:<8} "
              f"fake 1-day return {r['ret_pct']:>8.1f}%")
    ret = bars["close"].pct_change()
    leftover = int((ret.abs() > BIG_MOVE).sum().sum())
    print(f"remaining |1-day| > {BIG_MOVE:.0%} moves after repair (spin-offs / "
          f"reused tickers): {leftover} — "
          f"{'MASKED for the 252 sessions each contaminates' if not args.no_guard else 'NOT MASKED (--no-guard)'}")

    horizons = tuple(int(x) for x in args.horizons.split(","))
    modes = ["sp1500", "pit500"] if args.universe == "both" else [args.universe]
    ctx = prep(bars, guard=not args.no_guard)
    out = {"engine_ingredient": "config.W_HIGH", "w_high": config.W_HIGH,
           "cost_bps_round_trip": COST_BPS, "guard": not args.no_guard,
           "split_repairs": repaired, "orphan_moves_left": leftover,
           "universes": {}}
    for mode in modes:
        out["universes"][mode] = run_universe(ctx, mode, args.draws,
                                              not args.no_guard, horizons)

    # ------------------------------------------ trial count and deflation
    # The registry N is what all multiple-testing math is a function of
    # (RESEARCH-AGENDA rule 3); lying about it is the classic death. Control
    # draws are nulls and do not count; the Rule-13 market-adjusted figures
    # are re-expressions of a variant already counted, not new trials.
    print(f"\n{'=' * 118}\n=== TRIAL COUNT AND DEFLATION (N = {args.trials}) ===")
    print("Best book found IN THE REGISTERED (positive) DIRECTION, per universe:")
    for mode, o in out["universes"].items():
        m = o.get("market_adj_ls")
        if not m or m.get("mean_bps") is None or not m.get("sd_bps"):
            continue
        sr_win = (m["mean_bps"] / 1e4) / (m["sd_bps"] / 1e4)
        dsr = growth.deflated_sharpe(sr_win, n_trials=args.trials, n_obs=m["n"])
        o["deflated_sharpe"] = round(float(dsr), 3)
        print(f"  {mode:<8} market-adjusted high52 D10-D1  "
              f"{m['mean_bps']:>8.1f} bps/window  NW t {m['nw_t']:>5.2f}  "
              f"annualised Sharpe {sr_win * math.sqrt(252 / H):>6.2f}  "
              f"DEFLATED SHARPE {dsr:.3f}")
    print("  (Bailey-Lopez de Prado want DSR near 1.0 to call a Sharpe real; "
          "this repo's\n   own bar is t > 3 for anything standalone.)")

    path = (RESULTS if not (args.no_guard or args.no_repair)
            else RESULTS.with_name("high52_results_noguard.json"))
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {path.name}")


if __name__ == "__main__":
    main()
