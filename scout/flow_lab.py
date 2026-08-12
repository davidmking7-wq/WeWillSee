"""H39 — FORCED FLOW: trade against the people who have to trade.

MECHANISM (one sentence, Rule 1, written before a single number was computed)
------------------------------------------------------------------------------
Some participants transact on a CALENDAR rather than on a price — payroll and
401(k) contributions settle at the turn of the month, index funds must print
their rebalance at a specific close, and December selling is tax-motivated and
price-insensitive — so standing ready to take the other side of a
price-insensitive forced order should be compensated, and that compensation is
payment for absorbing somebody else's constraint, NOT a forecast of anything:
the calendar is published years in advance and contains no information about
where the market is going.

METHOD (summary; the long form is below)
----------------------------------------
Hold SPY on the return-days that fall inside a PRE-REGISTERED forced-flow
window and hold BIL (real, cached, no hardcoded risk-free rate) on every other
day, 2016-01-05 .. 2026-08-07, close-to-close, and measure it against SPY
buy-and-hold. Then destroy it with a null that holds the number of days in
market and the window-length distribution FIXED and randomises only WHERE the
windows sit, 10,000 draws over four seeds, plus an exhaustive 2,663-rotation
control.

VERDICT (2026-08-10, filled in after the run; every number reproduced by
`python -m scout.flow_lab`)
----------------------------------------------------------------------------
**REJECTED.** See the RESULTS section at the bottom of this docstring. The
forced-flow calendar earns a higher SHARPE than SPY and a much smaller
drawdown, and BOTH of those are entirely explained by being out of the market
three-quarters of the time during a decade containing two crashes: the
matched-time-in-market null reproduces them. The real calendar sits at the
**39.6th percentile** of that null on Sharpe — i.e. a random set of windows of
the same shape and the same total exposure beats it 60% of the time. It loses
to SPY on compounded return before costs, so the break-even cost per round trip
is NEGATIVE and there is nothing to lever. The mechanism may well be real at
the tick level; at the daily close, on the market index, over ten years, it is
worth nothing measurable.

--------------------------------------------------------------------------
PRE-REGISTRATION — the windows, and the named forced flow behind each
--------------------------------------------------------------------------
This hypothesis is one step away from calendar data-mining and exactly one
thing separates it: every window below was fixed from the published literature
BEFORE any return was computed, and each carries a named mechanism. Anything
added afterwards is logged in `variants_tried` and demotes the result to
EXPLORATORY. Nothing was added afterwards.

| id | window (in RETURN-days) | source | forced flow |
|----|-------------------------|--------|-------------|
| TOM-A | the last trading day of month t, plus trading days 1-3 of month t+1 (4 consecutive sessions) | Ariel (1987); Lakonishok & Smidt (1988); McConnell & Xu (2008) use exactly day -1..+3 | US payrolls, 401(k)/IRA contributions and pension accruals settle at the month turn and are invested mechanically on receipt; the buyer does not look at the price |
| TAX-A | the last 5 trading days of December, plus trading days 1-10 of January (15 consecutive sessions) | Roll (1983); Reinganum (1983); Ritter (1988) "parking the proceeds" | December selling is tax-loss harvesting — the seller's deadline is 31 December and their reservation price is irrelevant — and the proceeds are reinvested in the new year |
| REB-A | the session whose CLOSE carries the quarterly S&P rebalance: the 3rd Friday of March, June, September and December (1 session) | S&P index methodology (share/float updates effective after the close of the 3rd Friday of the quarter-ending month); quarterly-rebalance/triple-witching literature | index funds have a tracking-error mandate and MUST transact at the closing print, whatever it is |
| **UNION** | **TOM-A ∪ TAX-A ∪ REB-A** | — | **THE STRATEGY. Declared the headline before running.** |

Three sensitivity variants were ALSO pre-registered, as the same mechanism with
the other span the literature uses. They are counted in the trial count and
they are NOT eligible to become the headline:

| id | window | why it is the same idea |
|----|--------|------------------------|
| TOM-B | last 4 trading days of month t + days 1-3 of t+1 (7 sessions) | Lakonishok & Smidt's broader turn-of-month span |
| TAX-B | last 5 trading days of December + days 1-5 of January (10 sessions) | the short read of "reverses in early January" |
| REB-B | the 3rd Friday + the following session (2 sessions) | if the pressure reverses AFTER the print rather than accruing INTO it, this is where it shows up |

HONESTY ABOUT REB. Of the three, the rebalance window has the weakest prior for
a MARKET-DIRECTIONAL effect, and this was written down in advance: an S&P
share/float rebalance is a CROSS-SECTIONAL reshuffle that is close to
cash-neutral in aggregate, so there is no strong reason the index level should
be pushed in a particular direction on that date. It is pre-registered because
the assignment pre-registers it, and because triple-witching flow is genuinely
forced; its expected contribution was stated in advance as "smallest of the
three, possibly zero, possibly negative". That is what it turned out to be.

CALENDAR IDEAS EXAMINED AND REJECTED ON SIGHT (they are in the trial count)
---------------------------------------------------------------------------
Counted because Rule 2 counts everything that was considered, not everything
that was run:
 1. day-of-week / weekend effect — **DECLARED DEAD**, RESEARCH-AGENDA.md line 74
 2. overnight-only trading — **DECLARED DEAD**, same line
 3. index add/delete effects — **DECLARED DEAD**, same line
 4. post-split drift — **DECLARED DEAD**, same line
 5. pre-FOMC drift — **DECLARED DEAD**, same line
 6. Halloween / sell-in-May — no forced-flow mechanism; it is a seasonality
    label attached to a return pattern, which is the exact thing this design
    is built to avoid
 7. holiday effect (pre-holiday sessions) — the proposed mechanism is attention
    and short-covering, not a forced flow
 8. month-of-year seasonality tilt (Heston-Sadka) — a cross-sectional
    conditioning story, and here it would be a 12-cell sweep
 9. quarter-end window dressing — a real forced flow, but it is a
    cross-sectional tilt among managers' holdings and is not identifiable at
    the index level with the data here
10. FOMC-cycle even-week pattern — no forced flow, and the published version is
    a two-week cycle fitted on the same decade

--------------------------------------------------------------------------
METHOD, in full
--------------------------------------------------------------------------
SPAN        The full cached master span. Closes 2016-01-04 .. 2026-08-07 (2,664
            dates) give 2,663 close-to-close return-days, 10.567 years.
INSTRUMENTS SPY (dividend-adjusted closes from `scout/bars.py`, the same series
            the repo benchmarks everything against: CAGR 15.29%, matching the
            15.31% in BACKTEST-REPORT.md) and BIL as the cash leg. BIL is REAL
            and CACHED and its realised drift over the span is 2.11%/yr; no
            risk-free rate is hardcoded anywhere in this file. That mistake
            (a hardcoded/absent rf) is what turned H32's "+0.049 Sharpe added"
            into an honest "+0.006", and it is the single easiest way to be
            wrong about a strategy that sits in cash most of the time — which
            this one does, 74% of the time. Every Sharpe below is on returns in
            EXCESS OF BIL, computed day by day, and every alpha is a Jensen
            alpha on excess returns.
THE SHIFT   There is exactly one and it is structural. Define day d to be
            "in market" if the strategy earns SPY's close(d-1) -> close(d)
            return. Owning that return requires the SPY purchase to happen at
            the CLOSE OF DAY d-1, which the code does by construction: the mask
            is a mask over RETURN-days and the trade that creates it is the
            previous close. There is no `.shift()` on a signal because there is
            no signal — the mask is a function of the exchange calendar alone
            and depends on no price, no volume and no fundamental. Nothing that
            happens on day d, or on any day before it, is used to decide
            whether day d is in the window. That is a stronger statement than
            "the shift is correct": the design cannot look ahead at data
            because it never reads data.
THE ONE     The mask is built from the REALISED trading calendar (the index of
LOOKAHEAD   the cached bars). Scheduled holidays are published years ahead, so
            "the last trading day of March 2019" is knowable in advance — but
            UNSCHEDULED closures are not. The span contains exactly two:
            2018-12-05 (George H. W. Bush) and 2025-01-09 (Jimmy Carter), each
            announced 2-5 days in advance and each announced before the trade
            that would have been affected. Neither falls on a boundary that
            moves a window by more than one session. This is disclosed rather
            than fixed; the honest size of the contamination is 2 sessions in
            2,663.
COSTS       A round trip is one SPY buy + one SPY sell, i.e. one contiguous
            in-market block. `cost_bps` is charged per ROUND TRIP on full
            notional, split half on the block's first in-market day and half on
            its last. Charged at 0 / 5 / 10 / 20 bps and the BREAK-EVEN round
            trip cost is solved numerically. Two things this understates and
            they are stated rather than modelled: the BIL leg is also traded on
            every switch (BIL's spread is ~1 bp, so this is roughly a 10%
            understatement of the true round trip), and the month-turn is one
            of the highest-volume windows of the month, so SPY's spread there
            is at or below its average. The break-even number is reported so a
            reader can rescale to their own assumption.
GUARDS      All three documented price defects, and this is exactly which:
            (1) unadjusted splits — SPY has never split and BIL has never
                split; the maximum absolute one-day move in the span is 10.78%
                (SPY, 2020-03-24) and 0.077% (BIL), so there is no split
                residue to repair. Verified in `audit()`, not assumed.
            (2) spin-offs / reused tickers — neither symbol has been reused and
                no |1-day| move exceeds the 45% screen.
            (3) frozen quotes — the standard guard (a run of ~10 identical
                closes retires the symbol) WOULD RETIRE BIL, and doing so would
                be wrong. BIL's longest run of identical closes is 53 sessions,
                2020-12-07..2021-02-23, and it traded a median 1.24M shares a
                day throughout. That is not a stale delisted quote; it is a
                T-bill ETF at a zero policy rate, whose NAV genuinely did not
                move at penny granularity. The guard exists to catch a dead
                name paying a fake riskless drift; BIL's flat stretch pays
                exactly the zero it should. The override is deliberate,
                is printed by `audit()`, and is the correct call here — but a
                reader should know it was made.
UNIVERSE    Two ETFs. There is no cross-section, no survivorship question, no
            point-in-time membership question and no selection of any kind.
            This is the cleanest sample in the repo and it is the reason the
            hypothesis is worth testing: whatever is measured here cannot be
            survivorship and cannot be a beta sort in disguise.

--------------------------------------------------------------------------
THE DECISIVE CONTROL, and why the result is worthless without it
--------------------------------------------------------------------------
2016-2026 contains the COVID crash (-33.7% peak to trough) and the 2022 bear.
ANY rule that sits in cash three-quarters of the time will post a high Sharpe
and a small drawdown for reasons that have NOTHING to do with its signal: it
simply was not there. A t-statistic on the strategy-minus-SPY difference cannot
see this, because the difference is dominated by the days out of the market.

CONTROL 1 — MATCHED-TIME-IN-MARKET NULL (the one that decides it).
    Decompose the real mask into its contiguous blocks. Record the MULTISET of
    block lengths. Draw a random calendar with (a) the identical number of
    blocks, (b) the identical multiset of block lengths, (c) therefore the
    identical number of days in market and the identical number of round trips,
    placed uniformly at random over the 2,663 return-days with at least one
    out-of-market day between blocks so the blocks cannot merge. Run the
    IDENTICAL strategy — SPY inside, BIL outside — on each. 10,000 draws over
    4 independent seeds (2,500 each), so Rule 16's re-seeding is built in
    rather than bolted on. The real calendar is reported as a PERCENTILE of
    that null, with the Monte-Carlo standard error of the percentile,
    sqrt(p(1-p)/N).
    Everything mechanical is held fixed by construction: exposure, trade count,
    holding-period distribution, the cash leg, the crash-avoidance rate. The
    ONLY thing that varies is WHERE the windows sit in the calendar. If the
    real calendar is not beyond the 95th percentile, the honest verdict is that
    the calendar is nothing, and this file says exactly that.
CONTROL 2 — EXHAUSTIVE ROTATION. All 2,663 circular rotations of the real mask.
    This preserves the block lengths AND their exact sequence and spacing,
    destroying only the alignment to the calendar. It is a stricter shape match
    than Control 1 and it is evaluated exhaustively rather than sampled, so it
    has no Monte-Carlo error at all.
CONTROL 3 — THE DIRECT TEST, with no cash leg and no strategy wrapper. Compare
    SPY's own excess-over-BIL daily return INSIDE the windows against OUTSIDE
    them (Welch t, and Newey-West). If the flow premium exists, in-window days
    must pay more per day than out-window days. This is the mechanism stated in
    its most naked form and it is immune to every criticism of the wrapper.

Rule 13 is applied to the book AND to the difference. Rule 9's entry-phase
pooling has no analogue here — the calendar is fixed, there is nothing to
phase — and Control 2 is the closest thing to it, so it is reported in that
slot. Both halves and equal thirds are reported for every headline, because
the thirds check is what killed H22 and a calendar rule is precisely the kind
of result it kills.

--------------------------------------------------------------------------
WHAT THIS TEST CANNOT SETTLE — read before quoting any number above
--------------------------------------------------------------------------
1. **It tests the INDEX, not the flow.** A forced buyer at the month turn buys
   a diversified basket; the price impact is absorbed by market makers within
   the day and is largest in the names with the least depth. Measuring SPY's
   close-to-close return is the bluntest possible instrument for it. A negative
   here is evidence that the effect is not harvestable by a retail-style
   close-to-close index switch — it is NOT evidence that forced flow does not
   move prices. The tick-level version of this question is out of reach of
   daily bars.
2. **Ten years is 127 month-turns, 10 December-Januaries and 42 rebalances.**
   For TAX-A the effective sample size is TEN. No amount of daily-return
   arithmetic changes that: a 15-day window observed 10 times cannot resolve a
   30 bps effect, and the confidence intervals below say so honestly rather
   than hiding behind 2,663 daily observations.
3. **Post-publication decay.** Ariel is 1987 and Roll is 1983. McLean-Pontiff
   put the out-of-sample haircut at ~26% and the post-publication haircut at
   ~58%; the turn-of-month effect has been public for four decades and is
   trivially implementable, which is the profile of an effect that should be
   arbitraged flat. Finding nothing is the MODAL outcome here, not a surprise,
   and the design was chosen knowing that.
4. **The null cannot distinguish "no effect" from "an effect too small to see
   against a 2-crash decade".** A matched-exposure null is the right control
   and it is also a demanding one: it hands the random calendars the same
   crash-avoidance lottery ticket the real one holds. What it establishes is
   that the real calendar is not distinguishable from a random one of the same
   shape. That is the correct claim and it is weaker than "the effect is zero".
5. **BIL is not a money-market account.** It has an expense ratio (~13 bps) and
   a bid-ask spread, both already inside its realised price series, so the cash
   leg here is if anything conservative — but it is a specific instrument, not
   "the risk-free rate".

--------------------------------------------------------------------------
RESULTS (2026-08-10) — every number below is printed by __main__
--------------------------------------------------------------------------
See scout/flow_results.json. Headline, UNION calendar, gross:

    days in market 691 of 2663 (25.9%), 157 round trips (14.9/yr)
    strategy  CAGR  6.42%   vol  9.16%   Sharpe 0.470   maxDD -16.0%
    SPY       CAGR 15.29%   vol 18.10%   Sharpe 0.729   maxDD -33.7%

The strategy loses to SPY on return AND on Sharpe. The null percentile is
39.6 (Sharpe) — the real calendar is BELOW the median random calendar of the
same shape. The direct in-window-vs-out-window test on SPY's own returns gives
+1.14 bps/day, t = 0.42. Break-even cost is negative. There is nothing here.
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np
import pandas as pd

from . import bars, config, growth

# ---------------------------------------------------------------------------
# constants — nothing here is fitted, everything is pre-registered
# ---------------------------------------------------------------------------
START = "2016-01-01"
END = "2026-08-08"
TD_YEAR = 252
BPS = 1e-4
RESULTS = config.SCOUT_DIR / "flow_results.json"

# Monte-Carlo budget. 4 seeds x 2500 = 10,000 draws; the assignment's floor is
# 2,000 and Rule 16 wants the re-seed, so both are satisfied by construction.
NULL_SEEDS = (20260810, 11, 977, 4242)
NULL_DRAWS_PER_SEED = 2500

# The extreme-print screen used everywhere else in the repo.
BIG_MOVE = 0.45
# The frozen-quote screen used everywhere else in the repo.
STALE_RUN = 10

# Calendar ideas considered and rejected without computing a return. Counted.
REJECTED_ON_SIGHT = [
    ("day-of-week / weekend effect", "DECLARED DEAD in RESEARCH-AGENDA.md"),
    ("overnight-only trading", "DECLARED DEAD in RESEARCH-AGENDA.md"),
    ("index add/delete effect", "DECLARED DEAD in RESEARCH-AGENDA.md"),
    ("post-split drift", "DECLARED DEAD in RESEARCH-AGENDA.md"),
    ("pre-FOMC drift", "DECLARED DEAD in RESEARCH-AGENDA.md"),
    ("Halloween / sell-in-May", "no forced-flow mechanism; label on a pattern"),
    ("pre-holiday sessions", "mechanism is attention, not a forced flow"),
    ("Heston-Sadka month-of-year tilt", "cross-sectional, and a 12-cell sweep"),
    ("quarter-end window dressing", "real flow, not identifiable at index level"),
    ("FOMC even-week cycle", "no forced flow; fitted on this same decade"),
]


# ---------------------------------------------------------------------------
# 1. the calendar — the whole "signal", and it reads no market data
# ---------------------------------------------------------------------------
def _ordinals(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Per-session position within its own calendar month, forwards and back."""
    d = pd.DataFrame(index=index)
    d["y"] = index.year
    d["m"] = index.month
    key = d["y"] * 100 + d["m"]
    d["ord"] = key.groupby(key).cumcount() + 1            # 1 = first session
    d["rev"] = key.groupby(key).cumcount(ascending=False) + 1   # 1 = last
    return d


def _third_friday_sessions(index: pd.DatetimeIndex, months=(3, 6, 9, 12)) -> list:
    """The trading session carrying each quarterly rebalance close.

    The S&P quarterly share/float rebalance is effective after the close of the
    3rd Friday of the quarter-ending month. If that Friday is a holiday (Good
    Friday can in principle land on the 3rd Friday of March; it does not in this
    span) the last session on or before it is used instead."""
    naive = index.tz_localize(None).normalize() if index.tz is not None else index
    out = []
    for (y, m) in sorted({(t.year, t.month) for t in naive if t.month in months}):
        fridays = [t for t in pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D")
                   if t.month == m and t.weekday() == 4]
        if len(fridays) < 3:
            continue
        target = fridays[2]
        cand = naive[naive <= target]
        if len(cand) == 0:
            continue
        out.append(cand[-1])
    return out


def build_masks(close_index: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    """Boolean masks over RETURN-days (close_index[1:]).

    mask[i] True  <=>  the strategy earns SPY's close(i) -> close(i+1) return,
    which it does by BUYING AT THE CLOSE of close_index[i]. The mask therefore
    already encodes the close-to-close execution protocol; there is no separate
    shift because there is no signal to shift."""
    d = _ordinals(close_index)
    ordn, rev, mon = d["ord"].values, d["rev"].values, d["m"].values

    tom_a = (rev == 1) | (ordn <= 3)                       # Ariel / L-S / McC-Xu
    tom_b = (rev <= 4) | (ordn <= 3)                       # broader L-S span
    tax_a = ((mon == 12) & (rev <= 5)) | ((mon == 1) & (ordn <= 10))
    tax_b = ((mon == 12) & (rev <= 5)) | ((mon == 1) & (ordn <= 5))

    naive = (close_index.tz_localize(None).normalize()
             if close_index.tz is not None else close_index)
    reb_days = set(_third_friday_sessions(close_index))
    reb_a = np.array([t in reb_days for t in naive])
    nxt = np.zeros(len(reb_a), bool)
    nxt[1:] = reb_a[:-1]
    reb_b = reb_a | nxt

    full = {"TOM-A": tom_a, "TOM-B": tom_b, "TAX-A": tax_a, "TAX-B": tax_b,
            "REB-A": reb_a, "REB-B": reb_b}
    full["UNION"] = full["TOM-A"] | full["TAX-A"] | full["REB-A"]
    full["UNION-B"] = full["TOM-B"] | full["TAX-B"] | full["REB-B"]
    full["TOM+TAX"] = full["TOM-A"] | full["TAX-A"]
    # drop the first element: return-day i corresponds to close_index[i+1]
    return {k: v[1:].copy() for k, v in full.items()}


# ---------------------------------------------------------------------------
# 2. blocks, costs, and the strategy itself
# ---------------------------------------------------------------------------
def blocks_of(mask: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous in-market runs as [start, end] inclusive index pairs.

    One block == one round trip: buy at the close BEFORE `start`, sell at the
    close of `end`."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def strategy_returns(mask: np.ndarray, spy: np.ndarray, bil: np.ndarray,
                     cost_bps: float = 0.0) -> np.ndarray:
    """SPY inside the mask, BIL outside, cost_bps charged per ROUND TRIP."""
    r = np.where(mask, spy, bil).astype(float)
    if cost_bps:
        half = 0.5 * cost_bps * BPS
        for (a, b) in blocks_of(mask):
            r[a] -= half
            r[b] -= half
    return r


# ---------------------------------------------------------------------------
# 3. statistics — all excess of BIL, no hardcoded rate anywhere
# ---------------------------------------------------------------------------
def cagr(r: np.ndarray) -> float:
    n = len(r)
    return float(np.exp(np.log1p(r).sum() * TD_YEAR / n) - 1.0) if n else float("nan")


def ann_vol(r: np.ndarray) -> float:
    return float(np.std(r, ddof=1) * math.sqrt(TD_YEAR))


def sharpe_ex(r: np.ndarray, rf: np.ndarray) -> float:
    ex = r - rf
    sd = float(np.std(ex, ddof=1))
    return float(np.mean(ex) / sd * math.sqrt(TD_YEAR)) if sd > 0 else 0.0


def nw_se(x: np.ndarray, lag: int) -> float:
    """Newey-West standard error of the mean (identical to high52_lab.nw_se)."""
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


def alpha_beta(y_ex: np.ndarray, m_ex: np.ndarray, lag: int = 10) -> dict:
    """Rule 13. Jensen alpha and beta of an EXCESS series on the EXCESS market.

    Both arguments must already be in excess of BIL. Regressing raw on raw is
    the mechanical error that turned H32's alpha from +2.39% into +0.76%, and
    it bites hardest exactly when beta is far from 1 — which is this book's
    situation (beta ~0.26), so it is the single most important line here."""
    x = np.column_stack([np.ones(len(m_ex)), m_ex])
    coef, *_ = np.linalg.lstsq(x, y_ex, rcond=None)
    resid = y_ex - x @ coef
    se_ols = float(np.sqrt(np.sum(resid ** 2) / (len(y_ex) - 2)
                           / np.sum((m_ex - m_ex.mean()) ** 2)))
    # NW t on the alpha: regress out beta and take the NW SE of the mean residual
    a_series = y_ex - coef[1] * m_ex
    se_nw = nw_se(a_series, lag)
    # a_series is IDENTICALLY ZERO when y is the market itself (beta == 1 by
    # construction); guard so the SPY-on-SPY row prints nan instead of 0/0.
    se_ols_alpha = float(np.std(a_series, ddof=1) / math.sqrt(len(a_series)))
    t_ols = (float(np.mean(a_series) / se_ols_alpha)
             if se_ols_alpha > 1e-18 else float("nan"))
    t_nw = (float(np.mean(a_series) / se_nw)
            if (se_nw and se_nw > 1e-18) else float("nan"))
    return {"alpha_ann_pct": float(coef[0] * TD_YEAR * 100),
            "beta": float(coef[1]),
            "alpha_t_ols": t_ols,
            "alpha_t_nw": t_nw,
            "beta_se_ols": se_ols,
            "corr": float(np.corrcoef(y_ex, m_ex)[0, 1])}


def book(r: np.ndarray, bil: np.ndarray, spy: np.ndarray) -> dict:
    ex = r - bil
    m_ex = spy - bil
    ab = alpha_beta(ex, m_ex)
    return {"cagr_pct": cagr(r) * 100, "vol_pct": ann_vol(r) * 100,
            "sharpe": sharpe_ex(r, bil), "maxdd_pct": growth.max_drawdown(r) * 100,
            "skew": float(pd.Series(ex).skew()),
            "kurt": float(pd.Series(ex).kurtosis() + 3.0),
            **ab}


# ---------------------------------------------------------------------------
# 4. the matched-time-in-market null (Control 1) — fully vectorised
# ---------------------------------------------------------------------------
def _null_masks(lengths: np.ndarray, T: int, draws: int, seed: int) -> np.ndarray:
    """`draws` x T float32 0/1 matrix. Same block count, same length multiset.

    Blocks are separated by at least one out-of-market day so they cannot merge
    and silently reduce the round-trip count; the free days are distributed over
    the K+1 gaps by a uniform composition (sorted sample without replacement,
    the stars-and-bars construction)."""
    K = len(lengths)
    S = int(lengths.sum())
    free = T - S - (K - 1)
    if free < 0:
        raise ValueError("blocks do not fit")
    rng = np.random.default_rng(seed)
    M = np.zeros((draws, T), dtype=np.float32)
    idx = np.arange(T)
    for k in range(draws):
        L = rng.permutation(lengths)
        # uniform composition of `free` into K+1 non-negative parts
        # (stars and bars): K distinct cut points in {0..free+K-1}.
        cut = np.sort(rng.choice(free + K, size=K, replace=False))
        gaps = np.diff(np.concatenate([[-1], cut])) - 1          # K parts >= 0
        # gaps[j] = extra free days before block j ; plus 1 mandatory after each
        starts = np.cumsum(gaps + np.concatenate([[0], L[:-1] + 1]))
        rows = np.zeros(T, dtype=np.float32)
        for s, l in zip(starts, L):
            rows[s:s + l] = 1.0
        M[k] = rows
    assert np.allclose(M.sum(axis=1), S), "null draw lost days in market"
    return M


def _null_stats(M: np.ndarray, spy: np.ndarray, bil: np.ndarray) -> dict:
    """Sharpe / CAGR / alpha for every row of M, without materialising returns.

    strat = bil + M*(spy-bil), so every statistic reduces to a matrix-vector
    product. 10,000 draws x 2,663 days costs a fraction of a second."""
    T = M.shape[1]
    d = (spy - bil).astype(np.float64)
    m1 = M @ d / T                                   # mean excess per draw
    m2 = M @ (d * d) / T                             # E[x^2]
    var = (m2 - m1 * m1) * T / (T - 1)
    sh = m1 / np.sqrt(np.maximum(var, 1e-30)) * math.sqrt(TD_YEAR)

    lb, ls = np.log1p(bil), np.log1p(spy)
    logsum = float(lb.sum()) + M @ (ls - lb)
    cg = np.exp(logsum * TD_YEAR / T) - 1.0

    m_ex = d
    mm = float(m_ex.mean())
    vm = float(((m_ex - mm) ** 2).sum() / T)
    cov = M @ (d * m_ex) / T - m1 * mm
    beta = cov / vm
    alpha = (m1 - beta * mm) * TD_YEAR
    return {"sharpe": sh, "cagr": cg, "alpha": alpha, "beta": beta}


def _norm_ppf_safe(p: float) -> float:
    return growth.norm_ppf(min(max(p, 1e-12), 1 - 1e-12))


def percentile_of(real: float, null: np.ndarray) -> dict:
    n = len(null)
    p = float(np.mean(null < real))
    return {"percentile": p * 100,
            "mc_se_pctpts": float(math.sqrt(max(p * (1 - p), 1e-12) / n) * 100),
            "null_mean": float(np.mean(null)), "null_sd": float(np.std(null, ddof=1)),
            "null_p50": float(np.percentile(null, 50)),
            "null_p95": float(np.percentile(null, 95)),
            "null_p99": float(np.percentile(null, 99)), "n_draws": n}


# ---------------------------------------------------------------------------
# 5. sub-period splits
# ---------------------------------------------------------------------------
def splits(mask, spy, bil, dates, k: int) -> list[dict]:
    T = len(spy)
    edges = [round(i * T / k) for i in range(k + 1)]
    out = []
    for i in range(k):
        a, b = edges[i], edges[i + 1]
        s = strategy_returns(mask[a:b], spy[a:b], bil[a:b])
        bk = book(s, bil[a:b], spy[a:b])
        sp = book(spy[a:b], bil[a:b], spy[a:b])
        diff = s - spy[a:b]
        se = nw_se(diff, 10)
        out.append({"from": str(dates[a].date()), "to": str(dates[b - 1].date()),
                    "n_days": b - a, "days_in_mkt": int(mask[a:b].sum()),
                    "strat_cagr_pct": bk["cagr_pct"], "spy_cagr_pct": sp["cagr_pct"],
                    "cagr_diff_pp": bk["cagr_pct"] - sp["cagr_pct"],
                    "strat_sharpe": bk["sharpe"], "spy_sharpe": sp["sharpe"],
                    "sharpe_diff": bk["sharpe"] - sp["sharpe"],
                    "alpha_ann_pct": bk["alpha_ann_pct"],
                    "alpha_t_nw": bk["alpha_t_nw"],
                    "diff_mean_bps_day": float(diff.mean()) * 1e4,
                    "diff_t_nw": float(diff.mean() / se) if se else float("nan")})
    return out


# ---------------------------------------------------------------------------
# 6. the levered version — g = S^2/2, but only if the Sharpe survives
# ---------------------------------------------------------------------------
def levered(mask, spy, bil, target_vol: float, spread_bps: float,
            cost_bps: float = 0.0) -> dict:
    """Lever the IN-WINDOW SPY exposure to match SPY's full-period realised vol,
    financed at the REAL BIL yield plus `spread_bps`.

    in-window : L*spy - (L-1)*(bil + spread/252)
    out-window: bil
    L is solved so the levered series' full-period realised vol equals SPY's."""
    sp_d = spread_bps * BPS / TD_YEAR

    def series(L):
        r = np.where(mask, L * spy - (L - 1) * (bil + sp_d), bil)
        if cost_bps:
            half = 0.5 * cost_bps * BPS * L
            for (a, b) in blocks_of(mask):
                r[a] -= half
                r[b] -= half
        return r

    lo, hi = 1.0, 20.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if ann_vol(series(mid)) < target_vol:
            lo = mid
        else:
            hi = mid
    L = 0.5 * (lo + hi)
    r = series(L)
    bk = book(r, bil, spy)
    return {"leverage": L, "spread_bps": spread_bps, **bk}


# ---------------------------------------------------------------------------
# 7. data + guards
# ---------------------------------------------------------------------------
def load() -> dict:
    px = bars.get(["SPY", "BIL"], START, END)
    close = px["close"][["SPY", "BIL"]].dropna()
    vol = px["volume"][["SPY", "BIL"]].reindex(close.index)
    return {"close": close, "volume": vol}


def audit(close: pd.DataFrame, volume: pd.DataFrame) -> dict:
    """The three documented defects, checked rather than assumed."""
    out = {}
    r = close.pct_change().dropna()
    for s in ("SPY", "BIL"):
        v = close[s].values
        run, best, end = 1, 1, 0
        for i in range(1, len(v)):
            run = run + 1 if v[i] == v[i - 1] else 1
            if run > best:
                best, end = run, i
        seg = slice(end - best + 1, end + 1)
        out[s] = {
            "max_abs_1d_move_pct": float(r[s].abs().max() * 100),
            "n_moves_over_45pct": int((r[s].abs() > BIG_MOVE).sum()),
            "max_identical_close_run": int(best),
            "stale_run_flagged": bool(best >= STALE_RUN),
            "stale_run_from": str(close.index[seg][0].date()),
            "stale_run_to": str(close.index[seg][-1].date()),
            "median_volume_in_run": float(np.median(volume[s].values[seg])),
        }
    out["frozen_quote_override"] = (
        "BIL trips the >=10-identical-close screen with a 53-session run "
        "(2020-12-07..2021-02-23) on a median 1.24M shares/day. That is a "
        "T-bill ETF at a zero policy rate, not a delisted stale quote. The "
        "guard is deliberately overridden for BIL and only for BIL; SPY does "
        "not trip it (max run 2).")
    out["split_guard"] = (
        "Neither SPY nor BIL has ever split and no |1-day| move approaches the "
        "45% screen, so the repo's split-repair and extreme-print masks are "
        "no-ops here. Verified, not assumed.")
    # unscheduled closures
    idx = close.index.tz_localize(None).normalize()
    wd = pd.bdate_range(idx.min(), idx.max())
    miss = wd.difference(idx)
    unsched = [str(d.date()) for d in miss
               if str(d.date()) in ("2018-12-05", "2025-01-09")]
    out["unscheduled_closures_in_span"] = unsched
    out["calendar_lookahead_note"] = (
        "The mask is built from the REALISED trading calendar. Scheduled "
        "holidays are published years ahead; the only two unscheduled closures "
        "in the span are listed above (2 sessions in 2,663), each announced "
        "2-5 days before the fact. Disclosed, not fixed.")
    return out


# ---------------------------------------------------------------------------
# 8. main
# ---------------------------------------------------------------------------
def run(draws_per_seed: int = NULL_DRAWS_PER_SEED, quiet: bool = False) -> dict:
    P = lambda *a: None if quiet else print(*a)

    data = load()
    close, volume = data["close"], data["volume"]
    dates_all = close.index
    ret = close.pct_change().dropna()
    dates = ret.index
    spy = ret["SPY"].values.astype(float)
    bil = ret["BIL"].values.astype(float)
    T = len(spy)
    years = T / TD_YEAR

    res: dict = {"hypothesis": "H39 forced flow",
                 "span": {"from": str(dates[0].date()), "to": str(dates[-1].date()),
                          "n_return_days": T, "years": years,
                          "n_closes": len(dates_all)}}

    P("=" * 78)
    P("H39 FORCED FLOW — trade against people who must trade")
    P("=" * 78)
    P(f"span {dates[0].date()} .. {dates[-1].date()}  "
      f"{T} return-days ({years:.3f}y)")

    # --- guards -----------------------------------------------------------
    res["audit"] = audit(close, volume)
    P(f"\nGUARDS  SPY max|1d| {res['audit']['SPY']['max_abs_1d_move_pct']:.2f}%  "
      f"stale-run {res['audit']['SPY']['max_identical_close_run']}   |   "
      f"BIL max|1d| {res['audit']['BIL']['max_abs_1d_move_pct']:.3f}%  "
      f"stale-run {res['audit']['BIL']['max_identical_close_run']} (OVERRIDDEN)")
    P(f"        unscheduled closures in span: "
      f"{res['audit']['unscheduled_closures_in_span']}")

    # --- benchmarks -------------------------------------------------------
    spy_book = book(spy, bil, spy)
    bil_book = {"cagr_pct": cagr(bil) * 100, "vol_pct": ann_vol(bil) * 100}
    res["spy"] = spy_book
    res["bil"] = bil_book
    P(f"\nSPY  CAGR {spy_book['cagr_pct']:6.2f}%  vol {spy_book['vol_pct']:5.2f}%  "
      f"Sharpe {spy_book['sharpe']:.3f}  maxDD {spy_book['maxdd_pct']:6.1f}%")
    P(f"BIL  CAGR {bil_book['cagr_pct']:6.2f}%  vol {bil_book['vol_pct']:5.2f}%   "
      f"(the cash leg; NO rate is hardcoded anywhere in this file)")

    # --- calendars --------------------------------------------------------
    masks = build_masks(dates_all)
    res["calendars"] = {}
    P("\n" + "-" * 78)
    P("CALENDARS (pre-registered; the headline was declared UNION before running)")
    P("-" * 78)
    P(f"{'id':10s} {'days':>6s} {'%mkt':>6s} {'trips':>6s} {'trips/y':>8s} "
      f"{'CAGR%':>7s} {'vol%':>6s} {'Sharpe':>7s} {'maxDD%':>7s} "
      f"{'beta':>6s} {'alpha%':>7s} {'a_t':>6s}")
    for name, mk in masks.items():
        r = strategy_returns(mk, spy, bil)
        bk = book(r, bil, spy)
        bl = blocks_of(mk)
        row = {"days_in_market": int(mk.sum()),
               "pct_in_market": float(mk.mean() * 100),
               "round_trips": len(bl),
               "round_trips_per_year": len(bl) / years,
               "mean_block_len": float(np.mean([b - a + 1 for a, b in bl])),
               **bk}
        res["calendars"][name] = row
        P(f"{name:10s} {row['days_in_market']:6d} {row['pct_in_market']:5.1f}% "
          f"{row['round_trips']:6d} {row['round_trips_per_year']:8.1f} "
          f"{bk['cagr_pct']:7.2f} {bk['vol_pct']:6.2f} {bk['sharpe']:7.3f} "
          f"{bk['maxdd_pct']:7.1f} {bk['beta']:6.3f} {bk['alpha_ann_pct']:7.2f} "
          f"{bk['alpha_t_nw']:6.2f}")

    HEAD = "UNION"
    mask = masks[HEAD]
    strat = strategy_returns(mask, spy, bil)
    hb = res["calendars"][HEAD]
    diff = strat - spy
    res["headline"] = {
        "calendar": HEAD,
        "gross": hb,
        "vs_spy": {
            "cagr_diff_pp": hb["cagr_pct"] - spy_book["cagr_pct"],
            "sharpe_diff": hb["sharpe"] - spy_book["sharpe"],
            "diff_mean_bps_day": float(diff.mean()) * 1e4,
            "diff_t_ols": float(diff.mean() / (diff.std(ddof=1) / math.sqrt(T))),
            "diff_t_nw": {str(l): float(diff.mean() / nw_se(diff, l))
                          for l in (0, 1, 5, 10, 21)},
        },
    }
    P(f"\nHEADLINE = {HEAD}: strat Sharpe {hb['sharpe']:.3f} vs SPY "
      f"{spy_book['sharpe']:.3f}  (diff {hb['sharpe'] - spy_book['sharpe']:+.3f}), "
      f"CAGR {hb['cagr_pct']:.2f}% vs {spy_book['cagr_pct']:.2f}% "
      f"({hb['cagr_pct'] - spy_book['cagr_pct']:+.2f}pp)")
    P("  strat-minus-SPY daily diff  "
      f"{res['headline']['vs_spy']['diff_mean_bps_day']:+.3f} bps/day  "
      f"t_ols {res['headline']['vs_spy']['diff_t_ols']:+.2f}  "
      + "  ".join(f"t_nw{l} {v:+.2f}"
                  for l, v in res["headline"]["vs_spy"]["diff_t_nw"].items()))

    # Rule 13 on the DIFFERENCE, not only on the levels (the H29 mistake).
    dab = alpha_beta(diff, spy - bil)
    res["headline"]["rule13_on_difference"] = dab
    P(f"  RULE 13 on the difference: beta {dab['beta']:+.3f}  "
      f"alpha {dab['alpha_ann_pct']:+.2f}%/yr  t_nw {dab['alpha_t_nw']:+.2f}")

    # --- Control 3: the direct, wrapper-free mechanism test ---------------
    ex_spy = spy - bil
    inw, outw = ex_spy[mask], ex_spy[~mask]
    se_in = nw_se(inw, 5)
    tw = ((inw.mean() - outw.mean())
          / math.sqrt(inw.var(ddof=1) / len(inw) + outw.var(ddof=1) / len(outw)))
    res["control3_direct"] = {
        "in_window_bps_day": float(inw.mean()) * 1e4,
        "out_window_bps_day": float(outw.mean()) * 1e4,
        "difference_bps_day": float(inw.mean() - outw.mean()) * 1e4,
        "welch_t": float(tw),
        "in_window_t_vs_zero_nw5": float(inw.mean() / se_in),
        "n_in": int(mask.sum()), "n_out": int((~mask).sum()),
    }
    P("\nCONTROL 3 — SPY's OWN excess return, in-window vs out-window "
      "(no cash leg, no wrapper):")
    P(f"  in  {res['control3_direct']['in_window_bps_day']:+.3f} bps/day "
      f"(n={res['control3_direct']['n_in']})   "
      f"out {res['control3_direct']['out_window_bps_day']:+.3f} bps/day "
      f"(n={res['control3_direct']['n_out']})   "
      f"diff {res['control3_direct']['difference_bps_day']:+.3f}  "
      f"Welch t {tw:+.2f}")

    # Per-window direct test, and the SAME matched-placement null run on EVERY
    # arm (Rule 17: every arm of a comparison gets identical machinery, so no
    # window can be promoted by having been tested more carefully than another).
    # The statistic is the in-window mean excess return of SPY itself; the null
    # keeps the block-length multiset and randomises only placement.
    res["control3_by_window"] = {}
    P(f"    {'window':9s} {'n':>4s} {'in':>8s} {'out':>8s} {'diff':>8s} "
      f"{'welch_t':>8s} {'null_pctile':>12s} {'+/-':>5s}")
    for name, mk in masks.items():
        a, b = ex_spy[mk], ex_spy[~mk]
        t = ((a.mean() - b.mean())
             / math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)))
        lens_w = np.array([q - p + 1 for p, q in blocks_of(mk)])
        Mw = _null_masks(lens_w, T, draws_per_seed, NULL_SEEDS[0])
        null_in = (Mw @ ex_spy) / float(mk.sum())
        del Mw
        pc = percentile_of(float(a.mean()), null_in)
        res["control3_by_window"][name] = {
            "n": int(mk.sum()), "in_bps_day": float(a.mean()) * 1e4,
            "out_bps_day": float(b.mean()) * 1e4,
            "diff_bps_day": float(a.mean() - b.mean()) * 1e4, "welch_t": float(t),
            "matched_null_percentile_of_in_window_mean": pc["percentile"],
            "matched_null_mc_se_pctpts": pc["mc_se_pctpts"],
            "matched_null_mean_bps_day": pc["null_mean"] * 1e4,
            "matched_null_p05_bps_day": float(np.percentile(null_in, 5)) * 1e4,
            "matched_null_p95_bps_day": pc["null_p95"] * 1e4}
        P(f"    {name:9s} {int(mk.sum()):4d} {a.mean()*1e4:+8.3f} "
          f"{b.mean()*1e4:+8.3f} {(a.mean()-b.mean())*1e4:+8.3f} {t:+8.2f} "
          f"{pc['percentile']:11.1f} {pc['mc_se_pctpts']:5.2f}")

    # Multiple testing across the pre-registered window set, stated explicitly.
    n_windows = len(masks)
    worst = min(res["control3_by_window"].items(),
                key=lambda kv: kv[1]["welch_t"])
    best = max(res["control3_by_window"].items(),
               key=lambda kv: kv[1]["welch_t"])
    res["control3_multiple_testing"] = {
        "n_windows_tested": n_windows,
        "sidak_two_sided_t_threshold_at_5pct": float(
            abs(_norm_ppf_safe(1 - 0.5 * (1 - (1 - 0.05) ** (1.0 / n_windows))))),
        "most_positive": {"window": best[0], "welch_t": best[1]["welch_t"]},
        "most_negative": {"window": worst[0], "welch_t": worst[1]["welch_t"]},
        "note": ("the pre-registered set contains 9 calendars, so a |t| of ~2 "
                 "on any one of them is expected under the null; the Sidak "
                 "threshold is quoted so no single window can be read alone")}
    P(f"    across {n_windows} calendars the Sidak two-sided |t| bar at 5% is "
      f"{res['control3_multiple_testing']['sidak_two_sided_t_threshold_at_5pct']:.2f}; "
      f"most positive {best[0]} t {best[1]['welch_t']:+.2f}, "
      f"most negative {worst[0]} t {worst[1]['welch_t']:+.2f}")

    # --- REB-A forensics --------------------------------------------------
    # REB-A came back SIGNIFICANT WITH THE WRONG SIGN. Before that is allowed
    # to mean anything, it gets the decomposition that killed H32: is it a
    # population effect, or is it three crash days wearing a calendar label?
    P("\n" + "-" * 78)
    P("REB-A FORENSICS — the one window that cleared a threshold, and it is "
      "NEGATIVE")
    P("-" * 78)
    rb = masks["REB-A"]
    rx = ex_spy[rb]
    rdates = [str(t.date()) for t in dates[rb]]
    rmon = np.array([t.month for t in dates[rb]])
    order = np.argsort(rx)
    drop = {}
    for k in (0, 1, 2, 3, 5):
        keep = np.sort(order[k:])
        v = rx[keep]
        o = ex_spy[~rb]
        t = ((v.mean() - o.mean())
             / math.sqrt(v.var(ddof=1) / len(v) + o.var(ddof=1) / len(o)))
        drop[f"drop_worst_{k}"] = {"n": int(len(v)),
                                   "mean_bps_day": float(v.mean()) * 1e4,
                                   "welch_t": float(t)}
    thirds_reb = []
    for i in range(3):
        a, b = round(i * T / 3), round((i + 1) * T / 3)
        sel = rb.copy()
        sel[:a] = False
        sel[b:] = False
        v = ex_spy[sel]
        thirds_reb.append({"n": int(sel.sum()),
                           "mean_bps_day": float(v.mean()) * 1e4 if len(v) else None,
                           "pct_negative": float((v < 0).mean() * 100) if len(v) else None})
    # Sign test: robust to the outliers the mean is exposed to, which is the
    # whole worry with n=42.
    n_neg = int((rx < 0).sum())
    p_up = float((ex_spy > 0).mean())
    from math import comb
    p_sign = float(sum(comb(len(rx), k) * (p_up ** k) * ((1 - p_up) ** (len(rx) - k))
                       for k in range(0, len(rx) - n_neg + 1)))

    # THE CONFOUND CONTROL. The 3rd Friday of a quarter-ending month is three
    # things at once: (a) the quarterly S&P share/float rebalance, (b) quarterly
    # index-option and futures expiry ("quadruple witching"), (c) a Friday. The
    # 3rd Friday of the OTHER EIGHT months is (b-lite) + (c) WITHOUT (a) — it is
    # monthly equity-option expiry with no quarterly index rebalance. Comparing
    # the two holds day-of-week and expiry-week fixed and varies only the
    # rebalance. This is NOT a day-of-week test (declared dead, RESEARCH-AGENDA
    # line 74) and is not run as one; it is the control that decides whether
    # "quarterly rebalance" is the right label for the REB-A number at all.
    off_days = set(_third_friday_sessions(dates_all,
                                          months=(1, 2, 4, 5, 7, 8, 10, 11)))
    naive_r = (dates.tz_localize(None).normalize()
               if dates.tz is not None else dates)
    ctrl = np.array([t in off_days for t in naive_r])
    cx = ex_spy[ctrl]
    t_ctrl = ((cx.mean() - ex_spy[~ctrl].mean())
              / math.sqrt(cx.var(ddof=1) / len(cx)
                          + ex_spy[~ctrl].var(ddof=1) / len(ex_spy[~ctrl])))
    t_vs = ((rx.mean() - cx.mean())
            / math.sqrt(rx.var(ddof=1) / len(rx) + cx.var(ddof=1) / len(cx)))

    res["reb_forensics"] = {
        "n": int(rb.sum()),
        "sign_test": {"n_negative": n_neg, "n": int(len(rx)),
                      "spy_unconditional_up_day_rate_pct": p_up * 100,
                      "one_sided_binomial_p": p_sign},
        "confound_control_nonquarter_third_fridays": {
            "n": int(ctrl.sum()),
            "mean_bps_day": float(cx.mean()) * 1e4,
            "median_bps_day": float(np.median(cx)) * 1e4,
            "pct_negative": float((cx < 0).mean() * 100),
            "welch_t_vs_all_other_days": float(t_ctrl),
            "welch_t_REBA_minus_control": float(t_vs),
            "reading": ("holds Friday and option-expiry fixed, varies only the "
                        "quarterly index rebalance")},
        "mean_bps_day": float(rx.mean()) * 1e4,
        "median_bps_day": float(np.median(rx)) * 1e4,
        "pct_negative": float((rx < 0).mean() * 100),
        "worst_5": [{"date": rdates[i], "excess_bps": float(rx[i]) * 1e4}
                    for i in order[:5]],
        "best_5": [{"date": rdates[i], "excess_bps": float(rx[i]) * 1e4}
                   for i in order[-5:][::-1]],
        "drop_worst_sensitivity": drop,
        "by_third": thirds_reb,
        "by_month": {int(m): {"n": int((rmon == m).sum()),
                              "mean_bps_day": float(rx[rmon == m].mean()) * 1e4}
                     for m in (3, 6, 9, 12)},
        "matched_null_percentile": res["control3_by_window"]["REB-A"][
            "matched_null_percentile_of_in_window_mean"],
        "regime": "EXPLORATORY-IF-TRADED",
        "reading": ("This is a pre-registered window whose |t| clears the "
                    "Sidak bar across the 9 calendars tested, and whose "
                    "matched-placement null percentile is ~1. It is also the "
                    "OPPOSITE sign to the hypothesis: being long into the "
                    "quarterly rebalance close LOSES. Turning that into a "
                    "short is a POST-HOC SIGN FLIP and would be EXPLORATORY, "
                    "needing t>3 and a deflated Sharpe at N>700; see the "
                    "drop-worst sensitivity and the median before believing "
                    "any of it."),
    }
    P(f"  n={res['reb_forensics']['n']}  mean {res['reb_forensics']['mean_bps_day']:+.2f} "
      f"bps  MEDIAN {res['reb_forensics']['median_bps_day']:+.2f} bps  "
      f"{res['reb_forensics']['pct_negative']:.0f}% of days negative")
    P("  worst 5: " + ", ".join(f"{d['date']} {d['excess_bps']:+.0f}"
                                for d in res["reb_forensics"]["worst_5"]))
    P("  drop-the-worst sensitivity: " + "  ".join(
        f"{k.split('_')[-1]}->{v['mean_bps_day']:+.1f}bps t{v['welch_t']:+.2f}"
        for k, v in drop.items()))
    P("  by third (n, mean bps, %neg): " + "  ".join(
        f"[{d['n']}, {d['mean_bps_day']:+.1f}, {d['pct_negative']:.0f}%]"
        for d in thirds_reb))
    P("  by quarter-month: " + "  ".join(
        f"M{m}: n={v['n']} {v['mean_bps_day']:+.1f}"
        for m, v in res["reb_forensics"]["by_month"].items()))

    # --- Control 1: matched-time-in-market null ---------------------------
    lens = np.array([b - a + 1 for a, b in blocks_of(mask)])
    P("\n" + "-" * 78)
    P("CONTROL 1 — MATCHED-TIME-IN-MARKET NULL (the decisive one)")
    P("-" * 78)
    P(f"  holding fixed: {int(mask.sum())} days in market, {len(lens)} blocks, "
      f"block lengths {sorted(set(lens.tolist()))} with counts "
      f"{ {int(l): int((lens == l).sum()) for l in sorted(set(lens.tolist()))} }")
    P("  varying: ONLY where the blocks sit.")

    per_seed, pooled = [], {"sharpe": [], "cagr": [], "alpha": []}
    for sd in NULL_SEEDS:
        M = _null_masks(lens, T, draws_per_seed, sd)
        st = _null_stats(M, spy, bil)
        for k in pooled:
            pooled[k].append(st[k])
        per_seed.append({
            "seed": sd, "draws": draws_per_seed,
            "sharpe_pct": percentile_of(hb["sharpe"], st["sharpe"])["percentile"],
            "cagr_pct": percentile_of(hb["cagr_pct"] / 100, st["cagr"])["percentile"],
            "alpha_pct": percentile_of(hb["alpha_ann_pct"] / 100,
                                       st["alpha"])["percentile"]})
        del M
    for k in pooled:
        pooled[k] = np.concatenate(pooled[k])

    res["control1_null"] = {
        "design": ("same block count, same multiset of block lengths, same days "
                   "in market, same round-trip count, >=1 out-day between "
                   "blocks; only the placement is randomised"),
        "n_blocks": int(len(lens)), "days_in_market": int(mask.sum()),
        "block_length_counts": {int(l): int((lens == l).sum())
                                for l in sorted(set(lens.tolist()))},
        "per_seed": per_seed,
        "sharpe": percentile_of(hb["sharpe"], pooled["sharpe"]),
        "cagr": percentile_of(hb["cagr_pct"] / 100, pooled["cagr"]),
        "alpha": percentile_of(hb["alpha_ann_pct"] / 100, pooled["alpha"]),
        "seed_sd_of_sharpe_percentile":
            float(np.std([p["sharpe_pct"] for p in per_seed], ddof=1)),
    }
    for k in ("sharpe", "cagr", "alpha"):
        d = res["control1_null"][k]
        real = {"sharpe": hb["sharpe"], "cagr": hb["cagr_pct"] / 100,
                "alpha": hb["alpha_ann_pct"] / 100}[k]
        P(f"  {k:7s} real {real:+.4f}   null mean {d['null_mean']:+.4f} "
          f"sd {d['null_sd']:.4f}  p50 {d['null_p50']:+.4f} "
          f"p95 {d['null_p95']:+.4f}  ->  PERCENTILE "
          f"{d['percentile']:.1f} +/- {d['mc_se_pctpts']:.2f} (MC se, N={d['n_draws']})")
    P(f"  Rule 16 re-seed: per-seed Sharpe percentiles "
      f"{[round(p['sharpe_pct'], 1) for p in per_seed]}, "
      f"sd {res['control1_null']['seed_sd_of_sharpe_percentile']:.2f} pts")

    # --- Control 2: exhaustive rotation -----------------------------------
    R = np.zeros((T, T), dtype=np.float32)
    base = mask.astype(np.float32)
    for j in range(T):
        R[j] = np.roll(base, j)
    rot = _null_stats(R, spy, bil)
    del R
    res["control2_rotation"] = {
        "design": ("all 2,663 circular rotations of the real mask: block "
                   "lengths AND their exact sequence and spacing preserved, "
                   "only the calendar alignment destroyed; exhaustive, so no "
                   "Monte-Carlo error"),
        "sharpe": percentile_of(hb["sharpe"], rot["sharpe"]),
        "cagr": percentile_of(hb["cagr_pct"] / 100, rot["cagr"]),
        "alpha": percentile_of(hb["alpha_ann_pct"] / 100, rot["alpha"])}
    P("\nCONTROL 2 — exhaustive rotation (all 2,663 shifts of the same mask):")
    for k in ("sharpe", "cagr", "alpha"):
        d = res["control2_rotation"][k]
        P(f"  {k:7s} percentile {d['percentile']:.1f}  "
          f"(null mean {d['null_mean']:+.4f}, p95 {d['null_p95']:+.4f})")

    # --- halves and thirds ------------------------------------------------
    res["halves"] = splits(mask, spy, bil, dates, 2)
    res["thirds"] = splits(mask, spy, bil, dates, 3)
    P("\n" + "-" * 78)
    P("BOTH HALVES and EQUAL THIRDS (the check that killed H22)")
    P("-" * 78)
    for lab, rows in (("half", res["halves"]), ("third", res["thirds"])):
        for i, s in enumerate(rows, 1):
            P(f"  {lab} {i} {s['from']}..{s['to']}  "
              f"strat CAGR {s['strat_cagr_pct']:6.2f}%  SPY {s['spy_cagr_pct']:6.2f}%  "
              f"diff {s['cagr_diff_pp']:+6.2f}pp   Sharpe {s['strat_sharpe']:+.3f} "
              f"vs {s['spy_sharpe']:+.3f} ({s['sharpe_diff']:+.3f})   "
              f"alpha {s['alpha_ann_pct']:+6.2f}% t {s['alpha_t_nw']:+.2f}")

    # --- costs ------------------------------------------------------------
    P("\n" + "-" * 78)
    P("COSTS")
    P("-" * 78)
    cost_rows = []
    for c in (0.0, 5.0, 10.0, 20.0):
        r = strategy_returns(mask, spy, bil, cost_bps=c)
        bk = book(r, bil, spy)
        cost_rows.append({"cost_bps_round_trip": c, **bk})
        P(f"  {c:5.1f} bps/round-trip  CAGR {bk['cagr_pct']:6.2f}%  "
          f"Sharpe {bk['sharpe']:.3f}  (SPY {spy_book['cagr_pct']:.2f}% / "
          f"{spy_book['sharpe']:.3f})")
    res["costs"] = cost_rows

    n_trips = hb["round_trips"]
    gross_gap_log = (math.log1p(hb["cagr_pct"] / 100)
                     - math.log1p(spy_book["cagr_pct"] / 100))
    be_cagr = gross_gap_log * years / n_trips * 1e4
    lo, hi = -500.0, 500.0
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        s_ = strategy_returns(mask, spy, bil, cost_bps=mid)
        if sharpe_ex(s_, bil) > spy_book["sharpe"]:
            lo = mid
        else:
            hi = mid
    be_sharpe = 0.5 * (lo + hi)
    res["break_even"] = {
        "round_trips_total": n_trips, "round_trips_per_year": n_trips / years,
        "break_even_bps_per_round_trip_on_CAGR": be_cagr,
        "break_even_bps_per_round_trip_on_SHARPE": be_sharpe,
        "note": ("negative means the strategy loses to SPY on that metric "
                 "BEFORE any cost, so no cost level makes it work; the SPY leg "
                 "only is charged, BIL's ~1bp spread would add ~10% more")}
    P(f"  round trips {n_trips} total, {n_trips / years:.1f}/yr "
      f"({2 * n_trips / years:.0f} one-way trades/yr)")
    P(f"  BREAK-EVEN vs SPY on CAGR   : {be_cagr:+.1f} bps per round trip")
    P(f"  BREAK-EVEN vs SPY on SHARPE : {be_sharpe:+.1f} bps per round trip")

    # --- leverage ---------------------------------------------------------
    P("\n" + "-" * 78)
    P("LEVERED TO SPY'S REALISED VOL (g = S^2/2) — conditional on the null")
    P("-" * 78)
    cleared = res["control1_null"]["sharpe"]["percentile"] >= 95.0
    tgt = spy_book["vol_pct"] / 100
    lev_rows = []
    for spread in (0.0, 50.0, 100.0, 150.0):
        lv = levered(mask, spy, bil, tgt, spread)
        lev_rows.append(lv)
        P(f"  spread {spread:5.0f} bps  L {lv['leverage']:.2f}x  "
          f"CAGR {lv['cagr_pct']:6.2f}%  vol {lv['vol_pct']:5.2f}%  "
          f"Sharpe {lv['sharpe']:.3f}  maxDD {lv['maxdd_pct']:6.1f}%  "
          f"(SPY {spy_book['cagr_pct']:.2f}% / {spy_book['vol_pct']:.2f}% / "
          f"{spy_book['sharpe']:.3f})")
    # A break-even financing spread only exists if the UNLEVERED-FINANCING case
    # (spread 0) already beats SPY; otherwise there is no spread, however
    # generous, that gets there and reporting "0 bps" would be a lie.
    if lev_rows[0]["cagr_pct"] > spy_book["cagr_pct"]:
        lo, hi = 0.0, 5000.0
        for _ in range(120):
            mid = 0.5 * (lo + hi)
            if levered(mask, spy, bil, tgt, mid)["cagr_pct"] > spy_book["cagr_pct"]:
                lo = mid
            else:
                hi = mid
        be_spread = 0.5 * (lo + hi)
    else:
        be_spread = None
    res["levered"] = {
        "null_cleared": bool(cleared),
        "target_vol_pct": tgt * 100,
        "rows": lev_rows,
        "break_even_financing_spread_bps": be_spread,
        "identity_check": {
            "predicted_cagr_gap_pp_at_matched_vol":
                (hb["sharpe"] - spy_book["sharpe"]) * tgt * 100,
            "note": ("at matched vol the arithmetic-mean gap is "
                     "(S_strat - S_spy) * sigma_SPY; this is the g = S^2/2 "
                     "lever and it is NEGATIVE here because the Sharpe gap is")},
        "verdict": ("VOID — the assignment's precondition (real calendar beyond "
                    "the 95th percentile of the matched-time-in-market null) "
                    "was NOT met, so levering this is levering noise. The rows "
                    "are reported only to show that leverage cannot rescue it."
                    if not cleared else "null cleared; leverage is meaningful")}
    P(f"  break-even financing spread vs SPY CAGR: "
      f"{('%.0f bps' % be_spread) if be_spread is not None else 'NONE EXISTS — it loses to SPY even at zero financing spread'}")
    P(f"  {res['levered']['verdict']}")

    # --- trial count, deflated Sharpe, verdict ----------------------------
    computed = list(res["calendars"].keys())
    variants = []
    for name in computed:
        variants.append({"variant": f"calendar:{name}", "computed": True,
                         "sharpe": res["calendars"][name]["sharpe"],
                         "cagr_pct": res["calendars"][name]["cagr_pct"]})
    for c in cost_rows[1:]:
        variants.append({"variant": f"cost:{c['cost_bps_round_trip']}bps_rt",
                         "computed": True, "sharpe": c["sharpe"]})
    for lv in lev_rows:
        variants.append({"variant": f"levered:spread{lv['spread_bps']:.0f}bps",
                         "computed": True, "sharpe": lv["sharpe"]})
    for name, why in REJECTED_ON_SIGHT:
        variants.append({"variant": f"rejected-on-sight:{name}", "computed": False,
                         "why": why})
    res["variants_tried"] = variants
    n_mine = len(variants)

    sr_d = float(np.mean(strat - bil) / np.std(strat - bil, ddof=1))
    res["deflated_sharpe"] = {
        "sr_daily": sr_d, "sr_annual": hb["sharpe"], "n_obs": T,
        "at_my_own_N": {str(n_mine): growth.deflated_sharpe(
            sr_d, n_mine, T, hb["skew"], hb["kurt"])},
        "at_repo_running_N": {str(n): growth.deflated_sharpe(
            sr_d, n, T, hb["skew"], hb["kurt"]) for n in (700, 800)},
        "note": ("DSR here is close to meaningless in the usual direction: the "
                 "raw Sharpe is BELOW the benchmark's, so no deflation is "
                 "needed to reject it.")}

    p_sh_note = res["control1_null"]["sharpe"]["percentile"]

    P("\nDEFLATED SHARPE")
    P(f"  daily SR {sr_d:.5f} (annual {hb['sharpe']:.3f}), n_obs {T}, "
      f"skew {hb['skew']:+.2f}, kurt {hb['kurt']:.2f}")
    P(f"  DSR at my own N={n_mine}: "
      f"{res['deflated_sharpe']['at_my_own_N'][str(n_mine)]:.4f}   "
      + "  ".join(f"at N={n}: {v:.4f}"
                  for n, v in res["deflated_sharpe"]["at_repo_running_N"].items()))
    P("  (the raw Sharpe is already BELOW SPY's, so deflation is not what "
      "rejects this — it is rejected before any multiple-testing penalty)")

    res["regime"] = "CONFIRMATORY"
    res["regime_note"] = (
        "Pre-registered windows from the published literature, one declared "
        "headline (UNION), 3 primary + 3 sensitivity calendars, 3 combination "
        f"calendars, {n_mine} variants counted in total including "
        f"{len(REJECTED_ON_SIGHT)} rejected on sight. A confirmatory test at "
        "t~2 would have been meaningful here and the bar was NOT raised to "
        f"t>3; the measured direct-test t is "
        f"{res['control3_direct']['welch_t']:+.2f} and the headline sits at the "
        f"{p_sh_note:.1f}th percentile of its own matched null, BELOW the "
        "median, so the confirmatory-vs-exploratory distinction never becomes "
        "load-bearing.")

    p_sh = res["control1_null"]["sharpe"]["percentile"]
    res["verdict"] = {
        "call": "REJECTED",
        "downgrade_tag": "source_gap",
        "one_line": (
            f"A pre-registered forced-flow calendar (turn of month + tax-loss "
            f"reversal + quarterly rebalance) holding SPY {hb['pct_in_market']:.1f}% "
            f"of days and BIL otherwise earns {hb['cagr_pct']:.2f}%/yr at Sharpe "
            f"{hb['sharpe']:.3f} against SPY's {spy_book['cagr_pct']:.2f}% and "
            f"{spy_book['sharpe']:.3f}, and sits at the {p_sh:.1f}th percentile "
            f"of a matched-time-in-market null — below the median random "
            f"calendar of the same shape — so it is nothing."),
        "refresh_condition": (
            "Refresh if a same-shape close-to-close test on a SMALL-CAP or "
            "equal-weight vehicle (RSP/IWM) is run: the payroll-flow mechanism "
            "predicts the largest impact where depth is thinnest, and SPY is "
            "the deepest instrument in the world. Also refresh on a materially "
            "longer sample: 10 December-Januaries cannot resolve TAX-A."),
    }
    P("\n" + "=" * 78)
    P(f"VERDICT: {res['verdict']['call']}  [{res['verdict']['downgrade_tag']}]  "
      f"regime {res['regime']}, {n_mine} variants counted")
    P(res["verdict"]["one_line"])
    P("=" * 78)

    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=NULL_DRAWS_PER_SEED,
                    help="Monte-Carlo draws PER SEED (4 seeds)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    res = run(draws_per_seed=a.draws, quiet=a.quiet)

    def clean(o):
        """NaN/Inf are not valid JSON; a verifier must not have to guess."""
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (float, np.floating)):
            return float(o) if math.isfinite(float(o)) else None
        if isinstance(o, (int, np.integer)):
            return int(o)
        if isinstance(o, (bool, np.bool_)):
            return bool(o)
        return o

    with open(RESULTS, "w") as f:
        json.dump(clean(res), f, indent=2, allow_nan=False)
    print(f"\nwrote {RESULTS}")


if __name__ == "__main__":
    main()
