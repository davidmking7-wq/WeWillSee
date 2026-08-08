# Stock Scout — Final Backtest Report (engines v1 / v3 / v4 / v5)

Run 2026-08-08 on 10 years of dividend-adjusted Alpaca SIP daily bars,
via `python -m scout.backtest` (machine-readable results:
`scout/backtest_results.json` for the current-S&P-500 universe,
`backtest_results_pit500.json` for point-in-time, and
`backtest_results_sp1500.json` for the expanded universe).

## What was tested

- **Entries:** every ~21 trading days, 2017-07-10 → 2026-05-18 (107 dates).
- **Picks:** the engine's top 5 by composite score at each entry.
- **Label (verbatim):** HIT = max close over the next 42 trading days
  ≥ entry close × 1.05. +5% is the MINIMUM bar — the +10%/+15% rates and
  peak-gain columns measure how far picks actually run.
- **Benchmarks over the identical 42-day windows:**
  - **SPY** — the actual S&P 500 ETF (what "just buy the index" earns);
  - **eq-w market** — equal-weight average of the same universe.
- **Engines:** v1 (original), v3, v4 (gain-forward), v5 (current: v4 +
  tradeable-liquidity gate, S&P 1500 universe).
- **Three universes:** today's S&P 500 (the original test, survivorship-
  biased), the **POINT-IN-TIME S&P 500** (each date's ACTUAL members from
  the fja05680 dataset, later-delisted stocks included and held to their
  final print — SIVB's collapse books −57%), and today's **S&P 1500**
  (the live universe: large + mid + small caps).

## The honest headline — point-in-time S&P 500 (each date's real members)

| engine (PIT universe) | hit +5% | hit +10% | avg end % | med days | beat eq-w mkt | eq-w mkt avg % | SPY avg % |
|---|---|---|---|---|---|---|---|
| v1 | 57.9 | 30.9 | +0.87 | 16 | 49/107 | +2.04 | +2.51 |
| v3 | 58.5 | 31.8 | +1.34 | 15 | 50/105 | +1.94 | +2.39 |
| **v5** | **58.9** | **34.1** | **+1.47** | **14** | **54/105** | +1.94 | +2.39 |

What the survivorship correction reveals:
- **~1 point per window of the old numbers was mirage** (+2.49 → +1.47
  avg end for the live engine; hit rate 61.9 → 58.9). Every earlier table
  in this report overstates by roughly that much.
- **The benchmark was equally inflated** (+2.73 → +1.94), so the engine's
  RELATIVE standing improves: v5 beats the honest equal-weight market in
  a majority of windows (54/105) — the first majority in this project.
- **The engine ordering (v5 > v3 > v1) survives the correction** on every
  dimension — the upgrades were real, not survivorship artifacts.
- Residual imperfections (verified): 20/742 member-tickers (2.7%) have no
  Alpaca bars (mostly early-2016 renames/acquisitions); a handful of
  reused tickers splice two companies' histories, mostly outside their
  membership windows; positions still open AT a delisting halt exit at
  the final print (understates true losses only in that rare case).

## The expanded universe — S&P 1500 (the live engine's home)

Under-the-radar mid/small caps are where the bigger movers live. Same
test, today's S&P 1500 (survivorship caveat applies MORE strongly here —
no free point-in-time source exists for mid/small; the eq-w market's
+3.78%/window shows the bias direction):

| engine (S&P 1500) | hit +5% | hit +10% | hit +15% | avg end % | mean peak % | med days | beat SPY |
|---|---|---|---|---|---|---|---|
| v1 | 63.4 | 39.3 | 22.1 | +1.80 | 9.80 | 13 | 44/107 |
| v3 | 62.6 | 40.6 | 25.6 | +2.06 | 10.50 | 12 | 49/107 |
| **v5** | **63.6** | **42.1** | **25.8** | **+2.26** | **10.65** | **12** | **54/107** |

Versus the same engine confined to the S&P 500: more hits (63.6 vs 61.9),
substantially more big winners (+15% reached 25.8% vs 19.2% of the time),
bigger average peaks (10.65% vs 9.22%), faster (12 vs 15 days), and
compounded +243% vs +150% — pulling even with SPY buy-and-hold (+251%)
for the first time. The liquidity gate (20d median dollar volume ≥ $10M)
keeps the small-cap picks tradeable. Discount these raw levels for
small-cap survivorship; the cross-universe IMPROVEMENT is the robust part
(it appears identically for all three engines).

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

## Where the losses actually come from (forensics, 525 v4 picks)

- **The tail is event-driven.** Only 20% of misses contain a down
  "event day" (|1-day move| ≥ 6% on ≥2.5× volume — the earnings/news
  signature), but those misses average −11.8% vs −5.3% without, and **44%
  of all picks ending below −10% contain one**. Windows containing any
  event day have a 30% (vs 7%) chance of ending below −10% — earnings are
  the catastrophes, not the everyday losses.
- **Half of all misses are pure stock failures in rising markets**
  (avg −5.2%): the pattern just stops working, slowly. 57% of misses are
  still falling at the deadline — there is no recovery to wait for inside
  the horizon.
- **A quarter of misses are market-driven** (SPY down >2% over the same
  window; avg −8.9%) — the crash-regime rule's territory.
- Sector spread is large (full-period diagnostic): Info Tech picks hit 80%
  with +5.7% avg end; Consumer Staples 44%/−0.6%, Energy 53%/−0.2%. A
  train-selected "exclude weak sectors" rule was tested and did NOT survive
  holdout (below) — treat sector as research color, not a mechanical rule.

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

**Finding 3 — per-stock levels beat one-size-fits-all.** A second
train/holdout round tested levels scaled to each stock's own expected
42-day move (σ42): disaster stops at K×σ42 (K = 1.0–2.0) and post-hit
trails at J×σ42 (J = 0.4–0.8). Results:
- **vstop200 (2×σ42 disaster stop) beat the fixed −15% stop in BOTH
  periods** (holdout +2.35%/window vs +2.20, compounded 103.6% vs 100.1%,
  and it kills no extra winners: 6.9% = same as holding). A calm stock
  gets a ~16% stop, a lively one ~25% — noise stays inside the level.
- Tighter vol-scaled stops (1–1.5×σ42) still hurt — scaling doesn't fix
  the whipsaw problem, only widening does.
- Vol-scaled post-hit trails did NOT beat the simple **breakeven floor**
  (be_hit: holdout +2.11%/window, best of every post-hit variant; the
  fixed 8%-peak-trail sold ongoing runners and lost ~0.2pp to it).

**Re-confirmed on the current v5 / S&P 1500 pipeline** (full period,
cash-exit accounting): the per-stock disaster stop remains the best exit
rule and its edge over the wide rule GROWS on the wider universe — fixed
−15% stop: +1.65%/window, 22.8% tail, +155% compounded; per-stock 2×σ42
stop: +2.02%/window, 17.9% tail, +228% compounded (hold: +2.26%/+243%).
Small caps move more, so a one-size stop whipsaws them harder — exactly
why the level must come from each stock's own volatility. The post-hit
breakeven floor costs more here (~0.45pp/window cash; big small-cap
winners re-run after round-trips) — it stays loss-minimizing guidance
with its price stated, not a return enhancer.

**What ships** — the pipeline prints a per-pick "Sell Signal" with live
PER-STOCK dollar levels, refreshed on every update:
1. **Disaster stop at 2× the stock's own expected 2-month move** below
   entry (stored per pick as "Sell Below (Disaster)"). Rarely fires;
   truncates catastrophes. Tail-capping only.
2. **No other stop before the deadline; the deadline is the exit.**
3. **After a +5% touch: breakeven floor** — sell on any close back
   at/below entry; a winner is never allowed to become a loss.
The guidance never alters the scoreboard's HIT/MISS labels. The
loss-prevention that actually works for free is at ENTRY: the earnings
gate (binary-event days cause the worst single-day wrecks), the lottery-
spike veto, and the crash-regime rule.

## Earnings: what REAL dates say (supersedes every proxy result)

A complete map of real earnings-announcement dates was built from SEC
EDGAR (8-K Item 2.02 filings — 21,457 dates, 483/502 symbols, 2016-2026,
`scout/earnings_history.json`) and the tests re-run. **The real dates
overturn the proxy conclusion:**

| cohort (real dates) | train hit / avg end | holdout hit / avg end |
|---|---|---|
| earnings AHEAD, inside the window (~69% of picks) | **70.9% / +2.26%** | **64.2% / +4.13%** |
| no earnings in window | 55.4% / +2.80% | 43.2% / +0.35% |
| JUST reported (≤10 td before entry) | **46.9% / −0.90%** | **40.4% / +1.49%** |

- **The scheduled report ahead is the CATALYST, not the enemy** — picks
  holding into earnings are the engine's best cohort in both periods.
  The earlier proxy labs were accidentally measuring recent-volatility
  avoidance, not earnings avoidance (their detectors fired on any big
  move). The proxy-based "rank earnings-clean first" ordering was
  therefore reverted.
- **The genuinely weak cohort is freshly-reported stocks** — the catalyst
  is spent ("no earnings in window" is nearly the same set). Both periods
  agree, decisively. SHIPPED: the scan now flags just-reported candidates
  (live EDGAR check), pushes them to the bottom of both lists and
  downgrades their grade; earnings-inside-window carries no penalty (the
  date stays visible — a report can still wreck a single pick overnight,
  which is what the per-stock disaster level and research phase are for).
- Selling right before a known event tested unreliable in both proxy
  labs — entry policy, not exits, is where earnings are handled.

## Exits based on each pick's own expectations — tested, rejected

Per the "specific to the stock" directive, exit rules driven by each
pick's cell expectations (typical days-to-+5%, typical peak gain; built
from train picks only, applied frozen to holdout; adversarially verified)
were stacked on the shipped discipline:

| stack (holdout, expectations frozen) | avg/window | compounded |
|---|---|---|
| hold to deadline | +2.57% | +116.9% |
| shipped guidance (per-stock disaster + breakeven) | +1.91% | +95.4% |
| + time budget (sell if not +5% by 2× its expected days) | +1.70% | +64.8% |
| + take-profit at 1.25× its expected peak | +1.64% | +78.0% |
| + protect once above its expected peak | +1.35% | +79.3% |

Every expectation-based exit LOST out of sample. The reasons are already
in the forensics: losers rarely recover in-horizon (so early time-exits
only lock smaller losses while killing the late bloomers), and winners
run past their cell's expected peak often enough that capping or
tight-protecting at the expectation costs more than it saves. The
per-stock personalization that survives testing remains: the disaster
level from the stock's own volatility, the breakeven floor after +5%,
and the deadline. (Caveat: take-profit results carry an optimistic
execution bias — gaps book above the level — making the rejection
conservative.)

## Other entry-side rules

- **Weak-sector exclusion (tested, NOT shipped):** excluding the train
  period's weak sectors (rule selected Consumer Staples) helped train
  (+2.61 vs +2.41) but was a wash on holdout (+2.53 vs +2.57, same tail) —
  documented so nobody re-adds it; sector stays research color.

Verification meta-caveats (from the adversarial reviews, all labs): today's
GICS labels applied historically make the sector table anachronistic;
survivorship differs by sector; the proxy earnings detectors had limited
precision (0.2–0.59), which is exactly why the SEC EDGAR real-dates run
above supersedes them; and every lab has confirmed on the same 2022–2026
holdout — each use erodes its independence. **The holdout is now retired:
any future rule change needs fresh out-of-sample data (i.e., live track
record) before it ships.**

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

## The goal: "at least +5% every 1-2 months" — measured, then researched

The goal was measured DIRECTLY (`python -m scout.portfolio_lab`): the
whole portfolio's return per 42-td window, across concentration levels
and a velocity variant (sell at +5% touch, redeploy into the next-ranked
name). 54 non-overlapping windows, 2017-2026:

| strategy (S&P 1500) | avg/window | windows ≥ +5% | worst window | compounded |
|---|---|---|---|---|
| top-2 concentrated | **+4.59%** | **46%** | −22.7% | **+733%** |
| top-3 | +4.02% | 43% | −24.0% | +554% |
| top-5 (current default) | +2.63% | 43% | −19.6% | +243% |
| roll-5 (sell at +5%, redeploy) | +3.29% | 48% | −20.9% | +357% |
| SPY | +2.50% | 37% | −16.0% | +251% |

- **Stability:** top-2 is the one configuration that led BOTH halves
  (+4.28%/window 2017-21, +4.90% 2022-26). The velocity strategy is
  regime-dependent (weak in trending years, best in choppy ones).
- **The honest floor:** on the point-in-time S&P 500, concentration
  collapses (top-1: +0.34%/window; top-2: +1.89%) — a large share of the
  concentrated edge lives in the mid/small segment, whose survivorship
  cannot be corrected with free data. Reality sits between the two tables.
- **The literature says the same thing from the other side** (checked
  independently): even elite systematic funds land ≥+5% in only ~10-25%
  of months (MTUM: ~61% of months positive, avg +1.35%); the only
  documented every-month-level consistency is Renaissance's closed
  Medallion fund. Concentrating to 1-3 names raises the left tail faster
  than the right (our PIT top-1 collapse is textbook); profit targets cut
  the right tail momentum lives on (stops yes, targets no — matching our
  own exit-lab findings); vol-targeting (Barroso-Santa-Clara) is the
  best-documented CONSISTENCY upgrade but manufactures no edge; static
  2x leverage doubles crash depth for ~nothing after ~5.8% margin rates.

**The verdict, stated plainly:** "+5% or more EVERY window" is not a
target any evidence supports — not for this tool, not for anything
documented short of Medallion. The closest achievable, measured
formulation: a concentrated 2-3 pick book from the top of the scan's
overall order, stops-not-targets, crash rule respected — expect roughly
**+2.5 to +4.5% per window** (depending on how much of the small-cap
edge survives survivorship), with **≥+5% landing in roughly 40-50% of
windows**, a worst window of −15% to −25% every couple of years, and
losing streaks that WILL span multiple windows. Success should be scored
the way this scorecard already scores it: predicted vs realized, window
by window — not by demanding the impossible window-after-window.

## Caveats (all apply, none are optional reading)

1. **Survivorship**: now QUANTIFIED by the point-in-time section above —
   roughly +3pp of hit rate and +1pp of window return in the
   current-members tables. The S&P 1500 tables retain the bias (no free
   point-in-time source for mid/small); discount their raw levels and
   trust cross-engine/cross-universe comparisons instead.
2. **Overlap**: monthly entries overlap 2-month windows (~2× effective
   sample); the non-overlapping subset is the honest one.
3. **No costs, slippage, or taxes** in any number above.
4. **Within-window delistings** drop out of picks and benchmarks alike.
5. **Single macro era** (2017-2026, mostly bull); bear stats rest on ~3
   episodes. The v4 ship decision conditions on its holdout — the protocol
   reduces snooping, it does not eliminate it.
6. This is a research scorecard, not financial advice. Nothing is bought
   automatically.
