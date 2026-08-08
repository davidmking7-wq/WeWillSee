# Stock Scout — Final Backtest Report (engines v1 / v3 / v4)

Run 2026-08-08 on 10 years of dividend-adjusted Alpaca SIP daily bars,
via `python -m scout.backtest` (full machine-readable results in
`scout/backtest_results.json`).

## What was tested

- **Entries:** every ~21 trading days, 2017-07-10 → 2026-05-18 (107 dates).
- **Picks:** the engine's top 5 by composite score at each entry.
- **Label (verbatim):** HIT = max close over the next 42 trading days
  ≥ entry close × 1.05. +5% is the MINIMUM bar — the +10%/+15% rates and
  peak-gain columns measure how far picks actually run.
- **Benchmarks over the identical 42-day windows:**
  - **SPY** — the actual S&P 500 ETF (what "just buy the index" earns);
  - **eq-w market** — equal-weight average of the whole universe.
- **Engines:** v1 (original), v3 (2026-08 upgrade), v4 (current: v3 minus
  the gap/volume signal, gain-forward objective).

## Headline table — all 107 monthly entries

| engine | hit +5% | hit +10% | hit +15% | avg end % | mean peak % | med days to +5% | dipped −5% first | beat SPY (windows) | SPY avg % |
|---|---|---|---|---|---|---|---|---|---|
| v1 | 59.3 | 33.1 | 16.8 | +1.62 | 8.36 | 16 | 49.2% | 45/107 | +2.51 |
| v3 | 61.5 | 35.2 | 18.7 | +2.23 | 8.94 | 15 | 45.9% | 50/105 | +2.39 |
| **v4** | **61.9** | **37.1** | **19.2** | **+2.49** | **9.22** | **15** | **45.5%** | 49/105 | +2.39 |

Strictly non-overlapping windows (the statistically independent subset,
53 dates): v4 hit 60.8%, avg end +2.03%, median **13 days** to +5%,
dip-first 42.6% — v1: 60.0%, +1.54%, 15.5 days, 51.1%.

**v4 is the best engine ever tested here on every dimension of the
objective (gain × speed × safety):** most +10%/+15% winners, biggest
average peak, fastest to +5%, fewest painful dips. Gains concentrate in
bull regimes (63.2% hit, +2.9% avg end vs the market's +2.53%).

## The S&P 500 comparison — read this before anything else

Compounding the non-overlapping windows sequentially (equal-weight 5 picks,
hold to day 42, roll; no costs):

| | total growth 2017→2026 |
|---|---|
| v4 picks | **+150%** |
| SPY (same windows) | **+224%** |
| eq-w universe (same windows) | +279% |

**The scout does NOT beat buy-and-hold.** Its picks beat SPY in fewer than
half the individual windows, and its average window return (+2.49%) sits
below the equal-weight market's (+2.73%). Nothing about v4 changed that,
and no honest reading of this data supports using the tool as an
"outperform the index" strategy. (v1's SPY column reads +251% because v1
traded 2 windows — deep 2020/2022 stress dates — that v3/v4's stricter
gates sat out; within any engine's row the comparison is apples-to-apples.)

### Why a 62% hit rate does not mean "+5% banked every window"

Intuition says 5% × 6 windows a year should compound to several hundred
percent. It doesn't, for two reasons, both measured (v4, 525 picks):

- **The 38% of picks that never touch +5% average −6.6% at day 42.**
  Misses cost real money; they are not just absent wins.
- **Selling the instant a pick touches +5% is the WORST strategy tested:**
  0.62 × (+5%) + 0.38 × (−6.6%) ≈ **+0.57% per window → only +20%
  compounded 2017-2026**. Capping winners at +5% while eating losses in
  full destroys the edge.
- The +150% exists because winners RUN: picks that touched +5% ended at
  **+8.1% on average**. The ride beyond +5% is most of the profit — the
  quantitative reason +5% must be treated as a minimum bar, never a sell
  trigger.

What the tool IS measurably good at — its actual stated purpose:
- finding stocks that **touch +5% within 2 months** more often than its own
  gated base rate, **faster** (median 13-15 days vs the 42-day budget), with
  a **less painful path** (dip-first rate down from ~51% to ~43-45%);
- producing far more +10%/+15% runners than v1 while keeping the same floor;
- knowing when to stand aside (bear windows: 55% hit, ~0 avg end — the
  crash rule's "zero picks" stance is validated again).

## The v4 selection protocol (why to trust it more than a lucky draw)

Four literature-grounded candidate changes were evaluated on a TRAIN period
(2017-07..2021-12) with a v3 control; only the winner went to a single-shot
HOLDOUT (2022-01..2026-05). NOGAP (drop the gap/volume-surge signal, weight
to 6-1 momentum) won train broadly (hit 66.0 vs 64.9, +10% rate 35.5 vs
32.8, avg end +2.41 vs +2.01, faster, safer) and held up on holdout (gain
and speed better, hit rate equal in the independent subset). Rejected:
sector-relative momentum (wash), 20-day-high gate (wash), 5-day pullback
veto (hurt gain and speed). Full tables in SCOUT-DESIGN.md.

The backtest harness itself was adversarially reviewed before the holdout
ran; a lookahead bug in the crash-regime flag (full-sample volatility
quantile) and a non-overlap stride bug were fixed first.

## Sell rules — tested, and mostly rejected

Motivated by the miss anatomy (misses average −6.6% because broken momentum
has no floor: 23% of misses end below −10%, and ~19% contain a >7%
single-day crash), 18 close-based sell rules were tested over the v4
engine's picks via `python -m scout.exitlab` — hard stops (−8/−10/−12/−15/
−18%), time stops (day 21/30 at several levels), trend breaks (close below
50d SMA), crash exits (>7% one-day drop), trailing and breakeven exits.
Rules were designed on TRAIN 2017-2021 and the survivors judged once on
HOLDOUT 2022-2026. All exits execute at the breaching CLOSE (no pretending
you got out at the stop level through a gap).

**Finding 1 — no rule that can act BEFORE the deadline survived.** Every
hard stop, time stop and trend stop reduced the average window return in
BOTH periods (e.g. −10% stop: +1.09%/window on train vs +2.41% holding).
Two mechanisms, both visible in the data: 20% of eventual winners close
≤−5% before hitting (stops sell recoveries), and crashes gap through stop
levels (a −10% stop's realized exits averaged below −10%, so the loss tail
actually got WORSE). The deadline itself is the only pre-hit sell rule the
data supports.

**Finding 2 — protection AFTER a pick touches +5% is the only family worth
shipping, and the accounting matters.** "Once +5% is touched, sell on a
close at/below max(breakeven, peak−8%)":
- If exit proceeds sit in CASH for the rest of the window, the rule costs
  ~0.3pp per window (~2%/yr) — protection is not free.
- If exit proceeds are REDEPLOYED (modeled: into SPY for the window's
  remainder — the adversarial review of this harness flagged the cash
  assumption, and this check answers it), the rule is roughly
  return-neutral: full period +2.47%/window vs +2.49% holding, with BETTER
  compounded growth (+169% vs +150%); train favored protection (+95% vs
  +65% compounded), holdout favored holding (+102% vs +117%) — era noise
  around zero.
- Under both accountings it reliably buys a smaller average loser (−6.0%
  vs −7.9%) and a smaller tail (11% vs 14% of picks below −10%).
That combination — ~zero expected cost with redeployment, consistently
smaller losses — is why it ships. (Hard stops occasionally look good under
redeployment in crisis windows — e.g. stopped out into the 2020 SPY
rebound — but that is timing luck concentrated in 2-3 windows, they still
fail train AND holdout averages, and they whipsaw. Still rejected.)

| rule (full period) | avg/window | compounded | picks < −10% | avg loser |
|---|---|---|---|---|
| hold to deadline | **+2.49%** | **+150%** | 13.5% | −7.9% |
| protect after +5% (shipped as guidance) | +2.13% | +111% | 11.2% | −6.0% |
| −15% hard stop | +2.11% | +113% | 16.4% | −8.6% |
| sell if below entry at day 21 | +1.69% | +74% | 10.5% | −6.3% |
| close < 50d SMA | +0.96% | +37% | 5.0% | −5.3% |

**What ships** — the pipeline prints a per-pick "Sell Signal" with live
dollar levels, refreshed on every update:
1. **Disaster stop:** a close ≤ −15% from entry → sell. Rarely fires;
   truncates catastrophes (worst pick −32.5% → −24.2%) at ~zero mean cost
   under redeployment (+2.43 vs +2.49 per window). Tail-capping only.
2. **No other stop before the deadline; the deadline is the exit.**
3. **After a +5% touch:** protect at max(breakeven, peak−8%).
The guidance never alters the scoreboard's HIT/MISS labels. The
loss-prevention that actually works for free is at ENTRY: the earnings
gate (binary-event days cause the worst single-day wrecks), the lottery-
spike veto, and the crash-regime rule.

**The literature says the same thing** (checked independently):
Kaminski & Lo 2014 prove a stop only raises expected return when serial
correlation at the stop's trigger frequency exceeds the per-period Sharpe
ratio — daily single-stock returns lean toward REVERSAL, so tight stops
sell noise dips right before the expected bounce. Lei & Li 2009 (individual
US stocks, 3-12 month holds) find stops "neither reduce nor increase
losses" in expectation — their value is risk reduction, and only WIDE
volatility-scaled thresholds dominate. Han-Zhou-Zhu's famous pro-stop
result lives in monthly-re-formed decile portfolios with re-entry and
optimistic fills — on the long-winners side alone their 10% stop left mean
returns flat, and a −23% gap month still got through. The designs the
literature actually supports for this horizon — time-based exit,
deep disaster stop, wide post-gain trailing — are exactly the three that
survived here.

## Caveats (all apply, none are optional reading)

1. **Survivorship**: today's S&P 500 applied historically. This inflates
   the eq-w benchmark MORE than the picks (the benchmark holds every
   eventual winner), but raw hit rates also run a few points optimistic.
2. **Overlap**: monthly entries overlap 2-month windows (~2× effective
   sample); the non-overlapping subset is the honest one.
3. **No costs, slippage, or taxes** in any number above.
4. **Within-window delistings** drop out of picks and benchmarks alike.
5. **Single macro era** (2017-2026, mostly bull); bear stats rest on ~3
   episodes. The v4 ship decision conditions on its holdout — the protocol
   reduces snooping, it does not eliminate it.
6. This is a research scorecard, not financial advice. Nothing is bought
   automatically.
