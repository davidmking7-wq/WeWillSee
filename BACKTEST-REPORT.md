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

> **⚠️ READ THE NEXT SECTION BEFORE USING THIS TABLE.** Every row above
> samples ONE entry schedule out of six. Re-run on the other five, the
> top-2 row falls to about **+2.1%/window** and the ordering between rows
> disappears. The table is kept for the audit trail, not as an
> expectation.

- **Stability:** top-2 led BOTH halves of this schedule (+4.28%/window
  2017-21, +4.90% 2022-26) — which is why it survived review for as long
  as it did. Both-halves consistency does not protect against the
  entry-date problem below: both halves share the same entry dates.
  The velocity strategy is regime-dependent (weak in trending years,
  best in choppy ones).
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
documented short of Medallion. For the rest of the expectation, see the
correction below: the "+2.5 to +4.5% per window" this report used to
promise was measured on one entry schedule and does not survive.

## Round 2 — the loss forensics, and the correction they forced

The question asked was: where do the losses in the +733% run come from,
can bear markets be predicted better, and can the result be improved?
Three labs were built (`scout/regime_lab.py`, `scout/tail_lab.py`,
`scout/phase_lab.py`); 23 variants were pre-registered in
`scout/hypotheses.md` and tested. Not one improved the baseline, and the
third lab showed why: the baseline was not what it looked like.

### 1. The losses are not bear-market losses

Every one of the 54 windows was dumped with the market state known AT
ENTRY. The result contradicts the intuition (mine and the user's):

| entry state | n | avg/window | worst | ≥+5% |
|---|---|---|---|---|
| bear (SPY < 200d SMA) | 11 | **+0.49%** | −8.3% | 27% |
| crash flag (bear AND high vol) | 7 | **+0.52%** | −8.3% | 29% |
| high vol only | 15 | **+6.84%** | −8.3% | 53% |
| calm / no flag | 30 | +3.73% | **−22.7%** | 43% |

Bear and crash windows are *dull, not dangerous* — low returns, but
positive, and their worst is −8.3%. **Zero of the five worst windows
carried any market-state flag.** The real damage is single-name
collapses in calm bull markets: 2020-01 (BLDR −27%), 2024-11 (FICO
−17%), 2019-07 (OKTA −22%), 2018-05 (IBKR −21%). 18 losing windows sum
to −135pp; the worst 5 are half of that.

High volatility is the strategy's *best* state, not its worst — long-only
momentum in a high-vol tape is buying the rebound. Every exposure rule
built on market state therefore lost money: crash→cash +716%, bear→half
+723%, high-vol→half **+437%**, breadth→half +668%, engine-pool→half
+610%, vol-targeting +602% — all against +733%. (Vol-targeting was the
one with a real defense: in 2022-2026 alone it improved worst and maxDD
at no cost. It fails 2017-2021 by de-levering the 2020-21 rally, so it is
not shipped.)

### 2. Stop rules cannot reach that tail either

The portfolio backtest had always held to the deadline, so the tool's own
per-stock exits were tested inside it for the first time:

| rule | avg/window | worst | maxDD | compounded | fired |
|---|---|---|---|---|---|
| hold to deadline (baseline) | +4.59% | −22.7% | −29.1% | +733% | — |
| disaster stop 2.0σ (shipped) | +4.56% | −22.4% | −29.4% | +719% | 3 / 108 legs |
| disaster + replace next-ranked | +4.66% | −22.1% | −28.5% | +768% | 3 |
| **breakeven after +5% (shipped)** | **+3.76%** | −14.6% | −23.1% | **+471%** | 29 |
| trailing 1.5σ | +4.01% | −15.0% | −27.2% | +516% | 19 |
| inverse-vol weights | +4.47% | −22.0% | −28.6% | +692% | — |

Two things worth acting on. The **disaster stop is nearly inert** — 2σ is
~26% below entry, it fired 3 times in ten years; keep it as catastrophe
insurance, but it is not a return lever and it did not prevent a single
worst window. The **breakeven rule costs real money**: it fires 29 times,
saves 2020-01 (−22.7% → −4.1%), and loses far more selling winners that
dip through entry and then run. It was adopted on single-stock stats and
never checked at portfolio level. **Corrected: it is no longer a rule,
only an option for someone who wants a smoother ride and accepts ~35%
less compounded return.**

### 3. The finding that matters: +733% was the luckiest of six schedules

Scans exist every 21 trading days and holds last 42, so the
non-overlapping backtest takes every *other* scan — one of two possible
entry schedules, and nobody had ever run the other. Sampling every 7
trading days gives six equally valid schedules, each with 53
non-overlapping windows over the same decade and the same engine:

| entry offset | +0 td | +7 td | +14 td | +21 td | +28 td | +35 td |
|---|---|---|---|---|---|---|
| avg/window | **+4.56%** | +0.78% | +0.43% | +3.48% | +0.66% | +2.63% |
| compounded | **+685%** | −14% | −4% | +304% | −6% | +215% |

The shipped number is the maximum of six draws. Pooled, the honest
estimate is **+2.09% per window / +197% compounded, against SPY's +2.53%
/ +248%** on the identical span. The spread is not evidence of a "good
phase": its SD (1.7pp) is exactly the sampling noise of 53 windows
(SE ≈ 1.5pp). Six noisy estimates of one mean — and the report had been
quoting the largest.

Pooling also dissolves the concentration result that drove the whole
recommendation:

| book | pooled avg/window | phase spread | ladder compounded | worst | maxDD | ≥+5% |
|---|---|---|---|---|---|---|
| top-1 | +1.97% | 5.43pp | +178% | −24.8% | −48.3% | 45% |
| top-2 | +2.09% | 4.13pp | +197% | −20.1% | −46.1% | 47% |
| top-3 | +2.02% | 3.62pp | +165% | −19.5% | −41.7% | 40% |
| top-5 | +2.01% | 1.91pp | +144% | −19.8% | −37.9% | 32% |
| top-8 | +2.21% | 1.68pp | +177% | −17.8% | −29.9% | 38% |
| SPY | +2.53% | — | +248% | −16.0% | −17.9% | 38% |

**Concentration buys no return — only dispersion.** Every book size lands
within 0.25pp of the same ~+2% per window; what changes monotonically is
how much the answer depends on when you started (5.43pp → 1.68pp) and how
deep the drawdown gets (−48% → −30%). The one thing concentration does
deliver is the tool's actual claim: a top-2 book reaches +5% in 47% of
windows vs SPY's 38% — it gets there more often, and gives it back on the
misses, which is why the averages match.

### 4. What ships from Round 2

- **The ladder** (`H7b`): split capital across entry dates instead of
  betting the account on one. It cannot raise the mean — it *is* the
  mean — but a 6-sleeve ladder's worst window is −20.1% and maxDD −46.1%
  against single-schedule worsts of −30.7% and −82.8%. Two sleeves a
  month apart already gets most of it (−18.4% / −29.6%).
- **The corrected expectation**, replacing "+2.5 to +4.5% per window":
  roughly **+2% per 42-day window, ≥+5% in 40-47% of windows, worst
  window −18% to −25%, and no reliable edge over holding SPY.** The
  tool's defensible value is unchanged and narrower than the old
  headline: it finds names that reach +5% *sooner and more often* than
  the index, with calibrated odds — not names that compound faster.
- **Breakeven-after-+5% demoted** from rule to option (see above).
- Nothing else. 23 pre-registered variants, zero winners.

The failure this round exposes is a process failure worth naming: every
prior guard (walk-forward calibration, train/holdout split, both-halves
consistency, engine versioning) was defeated by a single unexamined
choice — the entry-date grid, which both halves shared. **Any future
portfolio claim in this report must be pooled across entry phases
(`python -m scout.phase_lab --sweep ...`) before it is quoted.**

## The ML Check as a selector — tested, rejected (information only)

The meta-label model (walk-forward AUC 0.60; strong-bucket picks hit 73%
vs 55% weak) was tested as an actual pick SELECTOR
(`python -m scout.ml_portfolio_lab`, fully walk-forward, all variants on
the same 39 out-of-fold non-overlapping periods):

| variant | avg/window | windows ≥ +5% | worst | compounded |
|---|---|---|---|---|
| top-2 composite order (baseline) | **+4.88%** | **51%** | −22.7% | **+409%** |
| top-2, skip ML-weak | +3.45% | 46% | −26.9% | +193% |
| top-2 ranked by model | +3.86% | 49% | −30.7% | +193% |
| top-3 baseline / skip / rank | +4.51 / +3.70 / +3.65 | 46/41/49 | — | +362 / +235 / +213 |

Worse in BOTH halves for every ML-selected variant. Why a good hit
classifier hurts selection: it predicts the ODDS of touching +5%, but
portfolio profit lives in how far winners RUN — and chasing hit odds
tilts toward safer, smaller-enders while the composite order carries the
end-return information. Verdict: the ML Check ships as INFORMATION and a
research-scrutiny flag only; it never skips or reorders picks. (Insider
buys, the other Round-1 candidate, remain display-only: 13 events in ten
years — 69% hit, +6.9% avg, zero tail — cannot move a backtest.)

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

## The alpha stack — tested on real data, REJECTED (scout/sleeve_lab.py)

ALPHA-STACK.md argued that since the selection layer adds no return, the
lever must be portfolio GEOMETRY: stack weakly-correlated sleeves to raise
Sharpe, then convert Sharpe into return with volatility targeting and
fractional Kelly. It projected a stacked Sharpe of 0.73 against a book of
0.50, i.e. ~1.5x the market's excess return at the same risk.

**Measured, it does not work.** 2534 trading days (2016-08 .. 2026-08),
20 ETFs, engine-independent, entry lagged one bar, excess of BIL, weights
fitted on trailing 504-day windows only.

### Sleeves, each normalised to 10% volatility

| sleeve | CAGR% | vol% | Sharpe | maxDD% | beta | skew |
|---|---|---|---|---|---|---|
| trend (5 td rebal) | 1.95 | 10.63 | 0.24 | -36.8 | 0.09 | -0.76 |
| trend (21 td rebal) | 4.04 | 10.58 | 0.43 | -27.2 | 0.14 | -0.71 |
| xsec relative momentum | 2.13 | 10.98 | 0.25 | -35.6 | 0.01 | -0.52 |
| defensive (low-vol half) | 3.60 | 10.56 | 0.39 | -27.0 | 0.25 | -0.52 |
| gated_equity (= vol-targeted SPY) | 8.44 | 10.90 | 0.80 | -17.5 | 0.53 | -0.94 |
| **SPY (excess)** | **12.85** | **18.00** | **0.76** | **-34.0** | 1.00 | -0.34 |

**Every diversifying sleeve is below SPY's Sharpe standalone**, at 0.24-0.46
against 0.76. The projection assumed trend would land at S_eff 0.34 after
haircuts; at the 5-day cadence it delivered 0.24, at monthly 0.43. That part
was roughly right. What was badly wrong is everything downstream.

### The correlation assumption was wrong by a factor of three

|  | trend | xsec | defensive | gated_equity |
|---|---|---|---|---|
| trend | 1.00 | **0.67** | 0.40 | 0.39 |
| xsec | 0.67 | 1.00 | 0.07 | 0.21 |
| defensive | 0.40 | 0.07 | 1.00 | 0.51 |
| gated_equity | 0.39 | 0.21 | 0.51 | 1.00 |

ALPHA-STACK assumed rho = 0.25 between sleeves and flagged that assumption
as the thing the whole result rested on. Measured: **0.67** between trend and
cross-sectional momentum, 0.51 between the defensive sleeve and equity.

**Effective bets: 1.02 of 4 sleeves.** Meucci's diagnostic says this book is
ONE bet wearing four coats. That is the single number that kills the thesis,
and it was pre-registered as the most likely failure (H10).

### The combination, and the leverage on top of it

| book | CAGR% | vol% | Sharpe | maxDD% |
|---|---|---|---|---|
| combo_eqrisk | 1.86 | 7.69 | 0.28 | -16.2 |
| combo_hrp | 2.01 | 7.66 | 0.30 | -15.7 |
| combo_eqrisk + vol target | 3.82 | 12.50 | 0.36 | -31.1 |
| combo_hrp + vol target | 4.27 | 12.54 | 0.40 | -30.1 |
| **+ fractional Kelly** | **-5.65** | 19.62 | **-0.20** | **-47.0** |
| **SPY (excess)** | **12.85** | 18.00 | **0.76** | -34.0 |

Projected 0.73. **Measured 0.40**, against SPY's 0.76 — barely half the
benchmark, not 1.5x it.

The Kelly row deserves its own sentence. The sizing rule behaved exactly as
designed (expanding window, de-levering to 0.85x by the end) and still
produced -0.20 Sharpe, because **leverage converts Sharpe into return and
this book's Sharpe was below the benchmark's.** Kelly cannot rescue a
signal; it can only scale one. Applying it to a weak book magnifies the
weakness, which is the whole content of `growth_at_leverage`.

### Halves: the sign flips

| | first half 2017-2021 | second half 2021-2026 |
|---|---|---|
| combo_eqrisk_voltgt | **1.13** | **-0.25** |
| combo_hrp_voltgt | **1.18** | **-0.23** |
| SPY (excess) | 0.92 | 0.60 |

The stack beat SPY on Sharpe in the first half and lost outright in the
second. By this repo's own standing rule (SCOUT-DESIGN, sell-rule and H5g
sections): a result that flips sign across halves is noise, not an effect.

### It is not a cost artifact

| variant | best sleeve Sharpe |
|---|---|
| 5 td rebalance, 5 bps | 0.39 |
| 21 td rebalance, 5 bps | 0.46 |
| 5 td rebalance, **0 bps** | 0.42 |
| 21 td rebalance, **0 bps** | 0.48 |

Turnover was the obvious suspect at 63-69x/yr for the trend sleeves. Cutting
rebalance frequency and setting costs to literally zero lifts the best sleeve
to 0.48 — still well under SPY's 0.76, and the sleeve correlations get
slightly WORSE (trend/xsec 0.70). There is no cost fix.

### The one thing that partly survived: volatility targeting (H11)

Applied to SPY alone, over the same window:

| | CAGR% | vol% | Sharpe | maxDD% |
|---|---|---|---|---|
| SPY (excess) | 12.92 | 17.64 | 0.78 | **-34.0** |
| vol-targeted, rescaled to SPY's vol | 13.41 | 17.74 | 0.80 | **-27.3** |

Sharpe 0.78 -> 0.80 and maxDD -34.0% -> -27.3% at matched volatility. But by
halves: **1.03 vs SPY's 0.92, then 0.56 vs SPY's 0.63.** The drawdown
improvement is consistent; the Sharpe uplift is not. Verdict: a drawdown
tool, not a return enhancer — the same conclusion the gates lab reached about
the gates, reached again by a different route. Not shipped.

### Why this is a useful negative result

The stack was the strongest argument available for beating the market with
free data, and it was built with every control this repo has: causal weights,
a 12-draw synthetic null, a known-edge synthetic, a lookahead audit, and
hypotheses registered before the run. It still lost, and the pre-registered
failure condition (H10, sleeve correlation) is exactly the one that fired.

Honest caveats that do NOT rescue it but bound what was tested: 19 ETFs are a
thin proxy for the 50-80 futures a real trend programme trades; 2017-2026 is
managed futures' worst documented decade AND the strongest mega-cap
concentration on record; and leverage was assumed free. A better instrument
set could plausibly move trend from 0.43 toward its published 0.75. It could
not plausibly move the sleeve correlation from 0.67 to 0.25, and that is the
number the thesis needed.

## Data integrity — are the prices themselves clean? (scout/data_audit.py)

Audited 2026-08-09, prompted by an incidental finding while building the
intraday adapter. Every result in this repository rests on an assumption
nobody had checked in three research rounds: that Alpaca bars fetched with
`adjustment=all` are actually adjusted.

**They are not, always.** S&P 1500, 2016-2026:

| check | result |
|---|---|
| splits in Alpaca's corporate-actions feed | 204 (198 checkable) |
| **of those, UNADJUSTED in the bars** | **10 (5.1%)** |
| further \|1-day\| > 50% moves with no split on file | 146 |

| symbol | ex-date | factor | fake 1-day return |
|---|---|---|---|
| SIRI | 2024-09-10 | 1:10 reverse | **+925.6%** |
| DEA | 2025-04-28 | 0.400 | +155.6% |
| SNEX | 2023-11-27 | 1.500 | +47.7% |
| CNX | 2017-11-29 | 0.125 | −89.6% |
| FNF | 2017-10-02 | 0.307 | −77.8% |
| AAPL | 2020-08-31 | 4:1 forward | −74.2% |
| TRN | 2018-11-01 | 0.333 | −73.5% |
| AA | 2016-11-01 | 0.333 | −73.3% |
| EQT | 2018-11-13 | 0.800 | −57.2% |
| AWI | 2016-04-04 | 0.500 | −56.6% |

Note the vendor disagrees with itself: the corporate-actions endpoint knows
about every one of these splits, and the bars endpoint does not apply them.

The 146 orphan moves are mostly **spin-offs** — the parent drops by the value
of the child and no split is recorded anywhere (RTX −71.0% at the
Carrier/Otis separation, APTV −71.6% at the Delphi spin) — and **reused
tickers** splicing two unrelated companies into one series.

### Did it reach the picks? Almost not at all.

Re-scoring the universe with `signals.composite_at` across 114 month-end
dates, 1,710 top-15 slots:

| | |
|---|---|
| slots taken by a name within 1 yr after a fake **+45%** move | **10 (0.58%)** |
| slots taken by a name within 1 yr after a fake **−45%** move | **0 (0.00%)** |

And several of those ten are plausibly genuine 45% moves (biotech does that)
rather than corruption, so 0.58% is an upper bound.

**Why it did not matter: the vetoes.** `VETO_RET1M_HI` (+25%) and
`VETO_RET1M_LO` (−15%), plus the top-vol-decile and MAX-effect vetoes,
exclude any name that just printed an enormous move — which is exactly what
a corrupted bar looks like. Those gates were adopted from the reversal and
lottery-effect literature for entirely unrelated reasons, and they block this
by accident. `gates_lab` concluded the gates "do not earn their place" on
return grounds; this is a use for them that no return table would ever show.

**Verdict: real data debt, no retraction required.** No previously reported
result changes. What changes is the confidence interval around anything that
touches a corporate action.

### What this audit does NOT cover, and it is the worrying part

It uses **today's** S&P 1500 membership. The point-in-time backtests
(`--universe pit500`) deliberately include delisted names, and those are
precisely the symbols most likely to carry bad final prints, reused tickers
and unadjusted terminal corporate actions — and precisely the ones that
cannot be cross-checked, because the corporate-actions feed thins out for
dead symbols. Treat pit500 numbers as carrying an extra, unquantified
data-quality discount on top of the survivorship correction they already
document.

## H21 — short-horizon reversal, and whether news says when it is paid (scout/reversal_lab.py)

Mechanism first: a one-week price move produced by uninformed liquidity
DEMAND must be paid for, so it reverses — the reversal return is the fee
earned by whoever absorbed the flow (Campbell-Grossman-Wang; Nagel 2012) —
while a move produced by INFORMATION does not reverse, because it is the new
price. This repo had tested momentum four times and measured it sorting
nothing; reversal is the opposite sign at the opposite horizon and had never
been tested here once. The cached news panel is the conditioner the mechanism
asks for, which is what makes this a mechanism test rather than a scan.

**Setup.** 120 point-in-time-liquid S&P 500 members as of 2016-01-04 (the same
panel the news labs use), 2,664 sessions 2016-01-04 .. 2026-08-07, 272,653
symbol-sessions eligible at h=5. Signal `close.shift(1)/close.shift(6) - 1` —
the 5-session return ending at close(t-1), so the position's first session is
SKIPPED. Book: long the bottom quintile, short the top, equal weight, held
close(t)→close(t+5), weekly rebalance. Groups: whether the name carried any
specific (non-templated, ≤10-tag) story in sessions t-5..t-1.

### The unconditional result — right sign, no size, and it is beta

| h | losers−winners (bps) | t | halves | beta to SPY | alpha (bps) | t_alpha |
|---|---|---|---|---|---|---|
| 1 | +1.44 | +0.54 | +2.66 / +0.23 | +0.29 | −0.39 | −0.15 |
| **5** | **+6.95** [−12.32, +26.70] | **+0.69** | +7.31 / +6.59 | **+0.33** | **−3.35** | −0.35 |
| 10 | −0.41 | −0.03 | −1.06 / +0.24 | +0.24 | −15.30 | −1.07 |
| 21 | +19.64 | +0.94 | +34.07 / +5.23 | +0.15 | +0.73 | +0.03 |

Rule 13 does the damage: buying five-day losers and shorting five-day winners
is a **long-beta** position, because the name that just fell is temporarily the
high-beta one. Market-adjusted, the h=5 spread is negative.

### The hypothesis — the conditioning does not fire

On the 1,488 dates where both legs are scorable, quiet **+9.70** vs news
**−2.00**, difference **+11.69 bps [−12.71, +36.08], t = +0.94**. It fails both
pre-registered failure conditions: halves **−10.23 / +33.61** (a sign flip),
and the difference sits inside the news-label-shuffle null (+0.55 ± 7.61, 94th
percentile, **p = 0.12**). At h=1 the difference carries the WRONG sign in both
halves. Abnormal news volume in terciles — the sharper conditioner, ~38 names a
bucket, no coverage problem — gives **+8.58 / +3.03 / +8.37**, a U rather than
a slope; low minus high is **+0.05 bps, t = +0.01**.

### Costs finish it

| book | gross bps/wk | turnover | break-even | net %/yr at 10 bps |
|---|---|---|---|---|
| long/short, all names | +6.95 | 1.57 | **4.44 bps** | −4.40 |
| long/short, quiet | +9.70 | 1.87 | 5.18 | −4.55 |
| long-only losers, all | +6.57 | 0.78 | 8.45 | −0.61 |
| **long-only losers, quiet** | +16.33 | 0.94 | **17.47** | **+3.52** |

The single book that clears cost is long-only-quiet — and its halves are
**−1.14 / +33.79**, and the sized random-subset null it must beat is +4.12 ±
4.12, not zero. Per the H1b house rule that is a new hypothesis, not a result.

### The one |t| > 2 cell, and why it is not quoted

In the top-liquidity half the quiet-minus-news difference reads **+71.19 bps,
t = 2.54**, and beats its own null at p = 0.000. It is measured on **159 dates
— 31 independent weekly windows** — because inside the 50 most liquid names the
quiet group has only 2.55 members in the loser cell. **158 of those 159 dates
are 2016-2021 and none are 2024-2025**, so both "halves" of that series are the
same era. At MIN_CELL=1 it halves to +39.75 on 910 dates. H7a is this repo
having quoted the luckiest of six entry phases once already; this is the same
shape and it is reported as a coverage artefact, not a finding.

### NEW DATA DEBT: frozen quotes and reused tickers (distinct from the split debt)

Alpaca keeps printing a delisted ticker at its last trade. In this 120-name
panel **EMC** freezes at one price from 2016-09-06 (Dell closed the
acquisition) and **MON** from 2018-06-06 (Bayer), after which a *different*
company reuses MON on 2021-03-16 at 9.79 against the stale 127.95 — a
fabricated **−92.4%** one-day return. Those two names alone account for **2,577
of the panel's 4,288 exactly-zero one-day returns**, and because a delisted
name also stops being written about, every one of those sessions is a permanent
member of the NO-NEWS group with a guaranteed-zero forward return — on the
exact leg this study measures. `reversal_lab.retire_stale` drops a symbol from
its first run of ≥10 identical consecutive closes. Any study in this repo that
conditions on quiet or low-volatility behaviour needs the same rule; the
data-integrity audit above does not catch it, because a frozen price produces
no large return to flag.

### Verdict

**REJECTED.** There is no unconditional short-horizon reversal in this large-cap
panel worth conditioning (7 bps a week, t = 0.69, and all of it beta), and the
news conditioning does not separate what the mechanism says it should. The
controls behave — the date-shuffle destroys the effect, as a timing claim
requires, and the offline selftest recovers a planted quiet-only reversal at
+185.7 bps and kills it with the news-label shuffle — so this is a null about
the world, not about the pipeline. Scope: large caps, one publisher, no
post-2016 additions, and Nagel's central VIX conditioning deliberately not run
after the null, so as not to hunt a variant. Trial count +16.

## Round 3 — the untouched data: news text, intraday bars, fundamentals

Triggered by a fair complaint: Round 2 tested ONE family of ideas and wrote a
verdict as if it had covered the space. This round opened the datasets this
repo had never touched — Benzinga news back to 2015, minute bars back to 2016,
and the SEC's bulk XBRL fundamentals — and pre-registered ten hypotheses
across them. Five have reported; the rest are in flight.

**Score so far: 5 tested, 5 rejected, 1 shipped rule demoted, 1 engine weight
condemned.** Detail below; registry rows in `scout/hypotheses.md` H15-H28.

### The table

| # | hypothesis | verdict | the number that decided it |
|---|---|---|---|
| H15 | attention shock -> reversal | **REJECTED** | date-shuffled news reproduces the whole spread |
| H16 | headline sentiment -> drift | **REJECTED** | wrong sign, every CI straddles zero |
| H17 | novel news drifts, stale reverses | **REJECTED** | real effect sits inside all three nulls, \|z\| <= 0.61 |
| H18 | equity premium accrues overnight | **REJECTED** | break-even 3.88 bps against a 5-10 bps cost band |
| H25 | 52-week-high proximity as a signal | **REJECTED** | it is a beta sort; market-adjusted t = 0.29 |

### 1. News carries volatility, not direction (H15, H16, H17)

Three independent attacks on the news panel, 32 + 18 + 24 variants, and they
converge on one sentence: **coverage forecasts the SIZE of the next move and
almost none of its sign.**

- Attention (H15): top-quintile next-session absolute move 1.45% vs 1.32% for
  the bottom quintile and 1.34% for the pool. Signed returns: nothing.
- Novelty (H17), a different measure entirely: stale-heavy names show
  same-day \|return\| 1.807% vs 1.291% novel, next-session 1.530% vs 1.315%,
  and signed next-session +7.82 vs +6.94 bps. Same finding, arrived at
  independently.

**What killed H15 is worth generalising.** The registered sign was right in
16 of 16 cells and the best \|t\| anywhere was 2.92 — borderline against the
repo's t>3 bar, and the kind of result a less careful round would have
shipped. Then the date-shuffled control:

| | h=1 | h=5 | h=21 | h=42 |
|---|---|---|---|---|
| real news dates | -2.31 | -3.42 | -15.81 | -23.56 bps |
| **dates shuffled** | **-0.57** | **-2.61** | **-10.61** | **-21.90** bps |

Destroying the timing barely dents the spread. The "signal" is a static
property of *which stocks get heavily covered*, not of *when* they are
covered. Timing-attributable residual: -1.74 / -0.82 / -5.19 / -1.66 bps.

H16 adds a separate lesson: the pre-registered ALTERNATIVE explanation was
also wrong. Tone was expected to be short-term reversal in a costume; in fact
the same-session return predicts nothing here either (lambda t between +0.19
and -0.76), and tone correlates with it at only 0.117. Two dead things, dead
independently. Cost of trading tone at h=1: **43.3%/yr**.

H17 also produced the round's most useful methodological result. Its
difference-in-differences design is largely immune to the news-timestamp
error that inflated H15's spread by 43%: re-run under deliberately wrong
after-close attribution it gives +0.32/-4.43/-6.42/-3.92 against the honest
-0.83/-3.91/-5.62/+3.85. Measured attenuation on planted leaks is 3.6x / 2.8x
/ 1.7x as the leak grows, so **robustness, not immunity** — but it is the
right shape for a design to have.

### 2. Overnight returns: real, and not tradeable (H18)

| leg | ann. return | Sharpe |
|---|---|---|
| SPY overnight (close -> open) | +9.54% | 0.86 |
| SPY intraday (open -> close) | +5.97% | 0.50 |
| SPY buy-and-hold | **+16.08%** | **0.94** |

The direction of Lou-Polk-Skouras replicates — overnight beats intraday, and
overnight wins in 83 of 114 individual names (73%, clearing the pre-registered
two-thirds bar). But the famous form of the claim needs the intraday leg to be
**zero or negative**, and here it is solidly positive. The market-level gap is
+1.22 bps/session with a permutation p of 0.561 — inside its own null.

It also decays exactly as post-publication decay should: the EW-120 gap runs
+17.4/+2.3 %/yr in the first half and +8.3/+6.7 in the second, shrinking ~70%
across a 2019 paper's publication date.

**And the costs settle it.** An overnight-only book trades 252 round trips a
year, so break-even round-trip cost equals the mean overnight return:

| book | break-even | net at 5 bps | buy-and-hold |
|---|---|---|---|
| SPY | 3.88 bps | -3.43%/yr | +16.08% |
| EW-120 | 5.05 bps | -0.61%/yr | +17.67% |
| gated composite Q5 | 5.39 bps | +0.51%/yr | +9.81% |

Against a 5-10 bps large-cap band, SPY fails outright and the other two scrape
past the letter of the bar while failing its substance. Deflated Sharpe of the
strongest net book: **0.140**.

#### H18e — the H4 verdict, and it is a demotion, not a kill

`scout/hypotheses.md` H4 ("enter at/near the CLOSE, never the open") is the
only rule this repo ever shipped **with no local test at all**. Minute bars
finally made it testable. On the shipped book size, 2,219 entry dates:

| entry | 42-session outcome | hit rate |
|---|---|---|
| close(t) | **+2.70%** | 64.24% |
| open(t+1) | +2.64% | 63.81% |

Advantage of buying the close: **+5.29 bps/window, 95% CI [+0.39, +10.73],
NW t = +2.07, positive in BOTH halves** (+7.87 / +2.72). At book size 5 it
strengthens to +6.18 bps, t = +3.04.

Then its own control: a **random pick of 2 names from the identical pool on
the identical dates earns +4.51 bps** [p5 +2.45, p95 +6.79] — and +5.29 sits
inside that interval. Pick-minus-pool edge: +0.68 bps, NW t = +0.44.

**So H4 stays shipped, and its justification changes.** Buying the close is
real and free, but it is a property of the overnight session generally, not
of the engine's picks. It was being credited to the wrong thing. The rule
costs nothing to keep and the honest reason to keep it is "the whole market's
premium accrues overnight", not "our picks gap up".

### 3. The 52-week high is a beta sort — and it is the engine's biggest weight (H25)

`config.W_HIGH = 0.25` is the single largest weight in the composite, larger
than 12-1 momentum, and until now it had never been tested on its own.

S&P 1500, 109 monthly formations, 42-session holds. Deciles by proximity:

| decile (low -> high proximity) | 1 | 2 | 5 | 8 | 10 | D10-D1 |
|---|---|---|---|---|---|---|
| raw return, bps/window | 388 | 302 | 264 | 237 | 205 | **-182.8** (t -1.84) |
| **SPY beta** | **1.61** | **1.30** | **1.07** | **0.93** | **0.79** | |
| market-adjusted | -21 | -30 | -7 | -0 | +3 | **+23.9** (t 0.29) |

The beta column is the whole story: proximity orders the cross-section by beta
almost perfectly, and the raw return profile is that beta profile priced at
this decade's equity premium. Risk-adjust and **nothing remains** (t = 0.29).

Run the identical machinery on 12-1 momentum and it behaves the opposite way —
beta is U-shaped (1.49 / 0.98 / 1.15) so it *cannot* manufacture a monotone
profile, and the market-adjusted spread is **+177.1 bps (t 2.11)**, i.e.
momentum survives the adjustment that kills proximity.

**The deciding test.** Proximity spread measured INSIDE momentum terciles:
-151 / -62 / -173 bps (t -2.34 / -1.41 / **-3.31**) — negative in all three,
the opposite of the registered sign. The reverse sort survives: momentum
inside proximity terciles is +53 / +124 / +42 market-adjusted.

Fama-MacBeth, top-to-bottom rank differences:

| coefficient | estimate | t |
|---|---|---|
| high52 alone | -141.4 | -1.55 |
| **high52, controlling for momentum** | **-298.6** | **-3.17** |
| **momentum, controlling for high52** | **+265.0** | **+3.74** |

Both cross this repo's t>3 bar, in opposite directions. And the date-shuffle
control shows why: **a proximity snapshot a full year out of date reproduces
69% of the spread.** It identifies a persistent stock type — high-beta
laggards — not a timing state.

Two further nails. George-Hwang's effect should GROW with horizon; measured at
21/42/126 sessions it goes -142 / -183 / -538 bps, growing more negative. And
their crash claim inverts: in bear formations proximity's spread is **-722 bps
against momentum's -48**, with a worst window of -3095 bps.

Break-even round-trip cost is **negative** (-83.2 bps ungated), meaning there
is nothing to protect even at zero cost.

**Consequence for the engine, stated plainly: the largest weight in the v5
composite measures negative at t = -3.17 once momentum is controlled, while
the momentum weights measure positive at t = +3.74.** That is the first
result in three rounds that points at a specific, testable engine change
rather than at a rejection. It is in-sample and the 2022-2026 holdout is
retired, so it does not license a v6 by itself — but the standard of evidence
for REMOVING a component that measures negative is not the standard for
adding one, and this is now the highest-priority item in the agenda.

An honesty note the lab earned: it **found and fixed a lookahead in its own
control** mid-study. Drawing date-shuffle donors uniformly allowed donor
dates after the formation date, reading closes inside the holding window; that
version manufactured +130.5 bps out of nothing. Donors are now restricted to
at least a year stale. The module retains the inverted-donor self-test that
measures the contamination such a leak produces (+57 to +127 bps).

### Round 3 caveats that apply to all of the above

1. **The news universe is 120 large caps, point-in-time as of 2016-01-04** —
   so no TSLA, no NVDA-as-a-mega-cap, no post-2016 index addition. That is
   precisely the cohort retail-attention effects are loudest in. The news
   rejections are scoped to large caps and should not be read as universal.
2. **Price-data debt applies** (see the audit section): 5.1% of splits are
   unadjusted and 146 further >50% one-day moves come from spin-offs and
   reused tickers. H25 repaired 13 splits and masked 296 residual moves; the
   AAPL case alone pinned its 52-week proximity at a fake 0.256 for a year.
   Studies without the engine's vetoes must guard this explicitly.
3. **Trial count.** These five labs ran 32 + 18 + 24 + 18 + 58 = 150 variants.
   The repo's running N is now roughly 340, which raises the deflated-Sharpe
   bar for everything that follows.

### 4. Volatility forecasting: the forecast wins, the trade does not (H20)

The only CONFIRMED row in Round 3, and it is confirmed on one of its two
halves. QLIKE on 1,861 dates, 52,453 symbol-sessions, 29 names:

| forecaster | QLIKE (lower better) |
|---|---|
| **HAR on log realised variance (5-min)** | **0.3971** |
| HAR pooled | 0.4017 |
| EWMA on realised variance | 0.4556 |
| EWMA on daily squared returns | 0.4957 |
| **`growth.blended_vol` (the incumbent)** | **0.4980** |
| random walk on RV | 0.5583 |
| unconditional mean | 0.6368 |
| date-shuffled RV (control) | 0.6951 |

Best model beats the incumbent by **20.3% of QLIKE, t = -6.46, in 29 of 29
symbols and in both halves.** MSE agrees.

**The mechanism row (H20c) is the one that matters.** Hold the estimator and
lambda fixed at 0.94 and swap only the INPUT — 5-minute realised variance for
daily squared returns: -0.0401, t = -6.83, halves -0.0386/-0.0415. The daily
EWMA beats the incumbent in only 17 of 29 names; the RV-fed version wins
29 of 29. So the gain is the intraday DATA, not a badly specified incumbent.

The date-shuffle control lands the forecast **worse than the expanding sample
mean** (+0.0583, t = +4.42). Destroying the timing destroys the skill — the
exact test H15's attention signal could not survive.

**The payoff is rejected.** Volatility-targeting SPY with each forecast:

| book | Sharpe | halves | maxDD (vol-matched) | break-even |
|---|---|---|---|---|
| buy and hold | 0.8631 | 0.601 / **1.322** | -33.84% | — |
| voltgt, incumbent | 0.8857 | 0.644 / 1.138 | -25.16% | 12.5 bps |
| voltgt, EWMA-RV | 0.9257 | 0.646 / 1.218 | -27.71% | 34.5 bps |
| voltgt, HAR-log | 0.9587 | 0.811 / 1.109 | -26.72% | 7.0 bps |

Every second half is BELOW buy-and-hold's 1.322 — H11's exact failure shape.
All Sharpe differences have bootstrap CIs straddling zero and sit inside the
shuffled-leverage null (76th-90th percentile). At 10 bps the best forecast
underperforms outright.

**The tell, reported by the lab against its own result:** adding one MORE day
of lag RAISES the best book's Sharpe from 0.959 to 1.044 and its second half
from 1.109 to 1.249. A real timing edge degrades when lagged; this improves.
The +0.096 point estimate is noise and was not defended.

Two structural ceilings worth keeping: only **59.9% of close-to-close variance
is open-to-close** — the rest is the overnight gap, permanently a
one-observation estimate — and vol targeting de-levers into volatility, which
is structurally short the case where conditional mean and conditional variance
move together. No variance model fixes that, because only one of the two is
being forecast.

**What it is worth.** Not a strategy. The repo uses daily-close volatility in
three places that are risk management rather than timing: `VOL_BAND` and
`VETO_VOL_DECILE` in signals.py, `SELL_DISASTER_SIGMA x sigma42` for the
per-stock disaster level, and the volatility tercile in calibration. A 20%
better variance forecast improves all three without betting on it.

### 5. Intraday momentum: the mechanism names the wrong half hour (H19)

Gao-Han-Li-Zhou's rule — first half hour predicts last half hour — has the
**wrong sign on all three instruments**: -0.815 / -0.497 / -0.273 bps per
session on SPY / QQQ / IWM, hit rates 48.3 / 49.1 / 49.1% (below a coin).
The paper's own regression fails to replicate: b = -0.061 / -0.011 / -0.031
against their reported +0.05 at t 3-5.

**The term structure refutes it without needing a significance threshold.**
Hold sign(first half hour) through each of the twelve later half-hour bins:

| bin | 11:00 (peak) | ... | **15:30-16:00** |
|---|---|---|---|
| SPY / QQQ / IWM, bps | +1.25 / +1.02 / +1.09 | mildly positive | **-0.81 / -0.50 / -0.27** |

Continuation is mildly positive across the middle of the session, and the
closing half hour — the one the mechanism names — is the **only bin negative
on all three instruments**. It is the worst of the thirteen.

The mid-day variant is the only survivor and it is the opposite claim:
sign(r1) -> 10:00-15:30 earns +2.06 / +4.91 / +3.93 bps, positive in both
halves on all three. That is generic same-day continuation smeared across the
session — the autocorrelation alternative — not a close-specific effect. Its
break-even is 2.07 / 4.93 / 3.96 bps against a 5-10 bps band, so untradeable
regardless. 61 variants.

### 6. Post-earnings drift: priced in two days (H26)

The repo rejected PEAD once already (H2b) sorted on the PRICE REACTION. H26
is the honest version — sorted on the actual earnings surprise (SUE), which
required fundamentals the repo did not have until this round.

**Strict point-in-time SUE deciles**, entry at close of the session AFTER the
later of the 8-K date and the filing date: D10-D1 = +11.11 / -2.46 / +21.19 /
-1.58 bps at h = 5/21/42/63, t = +0.77 / -0.07 / +0.45 / -0.03, sign flipping
across halves at three of four horizons. 41,378 ranked events.

**The positive control is what makes this interesting.** Mean 2-day
announcement reaction by SUE decile:

| decile | 1 | 2 | 5 | 8 | 10 | D10-D1 |
|---|---|---|---|---|---|---|
| bps | -117.0 | -89.4 | +42.8 | +117.7 | +186.1 | **+303.1** (t **+15.43**) |

That is the only t-statistic in the entire study clearing the repo's t>3 bar,
and it sits on the row saying **the surprise is already in the price**.

Event-time cumulative abnormal return confirms it: **89% of the entire
63-session spread is already paid by the close of the day after the
announcement.** The residual ~39 bps over three months is inside every error
bar in the file.

The firm-level date shuffle finishes it: the single cell carrying the
registered sign (announcement-anchored h=21, +51.36 bps, positive in both
halves) has a shuffle null of +27.88 — **54% of it survives destroying its
timing completely.**

Two further notes. H2b replicated to within 0.06pp (+5% reactors end +1.88%,
-5% reactors +1.94%), so the pipelines agree. And the size pattern **inverts**
the documented one: what little drift exists is in LARGE caps here
(h=63 liquidity-HIGH +153.41, t=+1.73) and negative down-cap, the opposite of
the literature. 65 variants.

**A data-integrity finding larger than the hypothesis.** With frozen-quote
retirement switched off, the unwinsorised h=63 spread reads **+896.68 bps**
(halves +2053 / -274) against the clean run's -3.16. Delisted and halted names
printing an unchanged close manufacture an enormous fake drift. This is a
THIRD price defect beyond the unadjusted splits and the spin-offs: 23 symbols
were dropped at their first run of 10 identical closes, plus 377 zero-volume
sessions blanked. Any study on this data must retire frozen quotes explicitly.

### 7. Net share repurchase: the one signal still standing (H22) — INCONCLUSIVE

Point-in-time S&P 500, 2,664 sessions, mean 490 eligible names.

| | h=42 | CI | NW t | halves |
|---|---|---|---|---|
| **net repurchase** (-1 x 12m log change in shares) | **+1.748 bps/day** | [-0.151, +3.720] | 1.81 | +2.009 / +1.488 |
| gross profit / assets | -0.412 bps/day | [-3.079, +2.099] | -0.298 | +0.984 / -1.807 |

Gross profitability is **rejected** — wrong sign, halves flip, and the
high-profitability quintile underperformed its own pool (12.59% vs 14.76%/yr).

Net repurchase is the only signal in three rounds with all of the following at
once, and it still does not clear the bar:

- **Not beta** (Rule 13): beta -0.001, alpha 4.42%/yr. Contrast H25, where the
  entire effect was beta.
- **Monotone in horizon**: +1.631 / +1.748 / +1.819 at h = 21 / 42 / 126.
- **Same sign in both halves**, and it clears its placebo null (z = 2.80).
- **Genuinely independent of the engine**: Spearman to raw 12-1 momentum
  **-0.015**, to the gated v5 composite **+0.010**, over 113 monthly dates —
  an order of magnitude inside the 0.2 independence threshold. This is the
  first non-price signal ever tested here and it is orthogonal.
- **Cost-insensitive**: the signal is quarterly, so turnover is 0.0131x/day
  and the **break-even round-trip cost is 267 bps against the 10 charged** —
  27x headroom. Nothing else in this repo has that property.

Why it is INCONCLUSIVE rather than confirmed:

1. **t = 1.81 against a t>3 bar.** On 56 strictly non-overlapping 42-session
   windows it is +0.685%/window at t = 1.587, positive in 57.1%. Deflated
   Sharpe 0.470.
2. **It dies exactly where the engine lives.** Double-sorted, the net-repurchase
   spread is +94.4 / +88.2 / **+13.0** bps across momentum terciles T1/T2/T3 —
   the effect is gone in the top momentum tercile, which is precisely where the
   v5 gates confine the engine. An independent signal that vanishes inside your
   own eligible pool is not usable as an overlay on that pool.
3. Q5 net 17.12%/yr at Sharpe 0.819 against SPY's 15.82% at 0.884 — beats on
   return, **loses on Sharpe**, which was the pre-registered failure condition.

Verdict: the most promising thing found in three rounds, and still not
shippable. It earns a live-tracking slot, not a weight. 58 variants.

### 8. H20 verification — survives 2/3, with a mandatory correction to its own headline

The three adversarial verifiers split 2-1 in favour, so H20's forecast result
stands. But two of them independently found the same defect in its headline
number, and it must be restated.

**The claim was "-20.3% of QLIKE versus the incumbent". About 40% of that gap
is a MODEL upgrade, not a DATA upgrade.**

Of the twelve forecasters in the lab, every model that ESTIMATES a coefficient
(`har_rv`, `har_log`, `har_log_pool`) is fed 5-minute realised variance, and
every model fed daily closes (`blended_daily`, `ewma_daily_094`) is a frozen
recipe with no fitted parameters anywhere. The comparison therefore prices
measurement AND model class, and reports the total as measurement.

Both verifiers built the missing cell — the lab's own HAR machinery, same
walk-forward, same refit schedule, run on DAILY closes with no intraday bar
ever touched — and got nearly identical answers:

| forecaster | QLIKE | vs incumbent |
|---|---|---|
| `blended_daily` (incumbent) | 0.4980 | — |
| **fitted HAR on daily squared returns** | **0.4575 - 0.4701** | **-6.2% to -8.1%** (free, no intraday data) |
| `har_log` (5-minute) | 0.3971 | -20.3% total |
| **genuine 5-minute component** | | **-13.1% to -16.3%** |

The decomposition is exact: -0.0412 (model) + -0.0602 (data) = -0.1014
(headline). **The honest number for what intraday data buys is -13% to -16%,
not -20.3%**, and roughly a third of the advertised gain is available for free
by fitting a HAR to data this repo already has.

That correction does not overturn the result — the mechanism row (H20c) held
the estimator and lambda fixed and swapped only the input, giving -0.0401 at
t = -6.83 in both halves, and it is unaffected by this criticism. The intraday
data genuinely helps. It helps about a third less than advertised.

**What the lookahead verifier found (and did not find).** It reproduced the
run exactly, then truncated the cached panel at 2024-01-03 and rebuilt every
forecaster: all eleven deterministic forecasters returned max|diff| = 0.000
with zero pattern mismatches, which a peek would have moved. It then wrote an
independent walk-forward log-HAR with different refit anchoring and an
explicit as-of training constraint, and matched. Two real defects were logged
and neither touches the headline: a hardcoded log line claims a split-repair
step that the cached-panel path never executes (the underlying repair is
nonetheless real — ten in-sample splits verified clean), and the stated
universe rule does not match the cache as it stands (26 further symbols
qualify).

**Round 3 correction log.** This is the second headline this round to be
restated after verification, following H25's raw decile profile. Both were
caught by controls the labs were required to run rather than by luck, which is
the system working — but the pattern is worth naming: **a comparison is only
as honest as its weakest arm.** H20 compared a fitted model to an unfitted
one; H25 compared raw returns to nothing at all. Rule 16 follows.

### 9. Accruals (H27) — NOT PROVEN, and its t-statistic did not survive

The lab returned "the sign is right, it clears t>3, and its own controls empty
it": Q1(low accruals) minus Q5(high) = +0.53 / +1.06 / +3.08 / +6.56% per
21/42/126/252-session hold, block-bootstrap t = 3.00 / 3.34 / 3.41 / 3.75 on
127 formation dates and 133,627 legs.

The verifier reproduced every number to the printed decimal, confirmed the
mechanism findings, and then killed the t-statistic:

**At h=21 the stride is 1, so the block bootstrap IS the i.i.d. bootstrap of
the mean, whose exact analytic value is mean/(sd/sqrt(n)) = 2.9510. The printed
3.0006 clears the house bar by six ten-thousandths on a 5,000-replication
estimate whose own Monte-Carlo standard deviation is 0.032.** Re-seeding the
identical bootstrap 60 times gives mean t = 2.968, sd 0.032, and **85% of seeds
land below 3.00.**

So "clears t>3" at h=21 is a coin flip on the random seed. It clears at three
of four horizons, not four, and the row that was headlined is the weakest one.

The direction of the finding is unaffected and the verifier said so explicitly
— nothing it did made accruals look better. But the framing "the statistics
pass, the mechanism fails" is wrong: the statistics do not pass either, at this
repo's own stated standard.

**Rule 16: a bootstrap t-statistic that lands within its own Monte-Carlo noise
of the acceptance threshold has not cleared it.** Report the analytic value
where one exists, report the Monte-Carlo standard deviation of the bootstrap
estimate itself, and re-seed before quoting a number within ~2 MC standard
deviations of a bar. H27 cleared by 0.02 of one MC standard deviation.

**Rule 17: give every arm of a comparison the same machinery.** H20 measured a
fitted model against an unfitted one and charged the whole difference to its
data source; a third of the gap was the fitting. Before attributing a gap to
the thing you are testing, build the cell that isolates it.

### Verification tally, Round 3

Only results that were not outright rejections face the adversarial panel —
three independent verifiers per claim, attacking along different axes
(alignment/lookahead, statistics/multiplicity, economics/costs), with a
majority required to uphold.

| claim | verifiers upholding | outcome |
|---|---|---|
| **H20** forecast (5-min RV beats daily closes) | **2 of 3** | **SURVIVES**, headline cut from -20.3% to -13/-16% |
| **H27** accruals | **1 of 3** | **KILLED IN VERIFICATION** |
| H22 net repurchase | pending | — |

H27 is the round's clearest demonstration of why the panel exists. The lab's
own verdict was already the cautious "NOT PROVEN", it reproduced to the printed
decimal, and its mechanism findings were confirmed sound by every verifier.
What did not survive was the single affirmative statistic in the write-up —
"clears t>3" — which turned out to be a Monte-Carlo coin flip (analytic value
2.9510; 85% of re-seeds below the bar). Two of three verifiers refused it on
that basis, and they were right to: this repo's entire multiple-testing
discipline is built on that threshold meaning something.

**Round 3 running score: 14 registered, 12 reported, 10 rejected outright,
1 surviving with a corrected headline (H20), 1 killed in verification (H27),
1 inconclusive and awaiting verification (H22), 2 still running (H23, H24).**

### 10. Illiquidity (H23) — the round's cleanest survivorship demonstration

This one looked like the winner, and it is the most instructive rejection in
three rounds because of *how* it died.

**On today's S&P 1500 it passes everything.** Amihud illiquidity, quintiles,
42-session holds:

| | value |
|---|---|
| Q5-Q1 | **+198.39 bps/hold**, CI [+105.63, +295.45], **t = +4.09** |
| both halves | +241.52 / +155.28 — same sign |
| entry phases (Rule 9) | positive on **all 42** |
| Rule 13 | **not a beta sort** — quintile betas 0.96/1.03/1.09/1.14/1.12, long-short beta +0.13, alpha **+8.55%/yr** (t +2.31) |
| controls | random quintiles -0.11 +/- 2.39; symbol placebo -0.17 +/- 18.16 |
| tradeable book | Q5 **+28.31%/yr, Sharpe 1.13**, alpha +9.29%/yr |
| costs | charged at each stock's OWN Corwin-Schultz spread (58-93 bps), effect survives |

t = +4.09 clears the house bar. Both halves. Every entry phase. Not beta. Real
per-stock spread costs. By every rule this repo has written, it ships.

**Then run the identical code on point-in-time membership:**

| universe | Amihud Q5-Q1 | dollar-volume sort | Q5 book |
|---|---|---|---|
| today's S&P 1500 | **+198.39** bps (t +4.09) | +150.97 | +28.31%/yr, Sharpe 1.13, alpha +9.29% |
| **point-in-time S&P 500** | **-42.68** bps (t -0.85) | **-86.16** (t -2.14, wrong-signed) | +14.71%/yr, Sharpe 0.59, alpha **-4.20%** |

The sign inverts. The tradeable book goes from beating SPY comfortably to
losing to SPY (0.59 vs 0.90 Sharpe), losing to its own Q1 (+16.35%,
Sharpe 0.94), and losing in **both halves** (0.73/0.43 against 1.03/0.83).

The contamination gradient is exactly what survivorship predicts: large caps
+138.89, mid +450.21, small +479.09 bps, sub-$10M slice +439.47 (t 9.78).
The illiquid tail of *today's* index is disproportionately made of companies
that were small in 2016 and **grew into the index** — the ones that survived.
Even the benchmarks disagree by the size of the effect: equal-weight S&P 1500
returns +19.61%/yr against point-in-time's +15.00%.

**Consequence, and it is the opposite of the registered expectation:
`MIN_DOLLAR_VOL = $10M` is vindicated, not condemned.** The lab was
registered to test whether the gate throws away a real premium. On honest data
there is no premium below it to throw away — the apparent one is the index
reconstituting itself. The sub-$10M slice's +439 bps at t = 9.78 is the purest
measurement of the bias in this repo, not a trading opportunity.

**And costs did not decide it, which is worth recording.** The classic finding
is that the illiquidity premium is eaten by the cost of accessing it. At a
42-session horizon that does not reproduce: illiquidity is extremely
persistent, so turnover is low and the long-short survives its own
77.7 bps blended spread (+11.92% -> +10.75%/yr). The effect was not too
expensive to capture. It was not there. 46 variants.

### 11. Short-horizon reversal (H21) — Rule 13 again

Registered as the most important untested idea in the repo: this repo has
tested momentum four times and never once tested its opposite.

Unconditional 5-session reversal: +6.95 bps [-12.32, +26.70], t = +0.69. Then
Rule 13: **the dollar-neutral book runs beta +0.33** — a stock that just fell
for five days is temporarily the high-beta one — and market-adjusted alpha is
**-3.35 bps (t = -0.35). The whole gross spread is the beta.** Third time this
round that a raw cross-sectional spread turned out to be a risk exposure.

The mechanism test (Nagel's: reversal is paid on uninformed liquidity demand,
so it should be strong on no-news moves and absent on news moves) gave
quiet +9.70 vs news -2.00, difference +11.69 bps — right sign, and **both**
pre-registered failure conditions fired: halves flip (-10.23 then +33.61), and
it sits inside the news-label-shuffle null (p = 0.17). The sharper conditioner,
abnormal news volume, gives +8.58 / +3.03 / +8.37 — **a U, not a slope** —
with low-minus-high of +0.05 bps (t = +0.01).

The lab's own honesty note is the most useful line in it: an independent
re-implementation written from the hypothesis text agrees within 5% on every
thick cell (+7.28 vs +6.95 unconditional, beta +0.340 vs +0.33) and **moves
64% on the 4.3-name quiet cell** (+15.90 vs +9.70). That disagreement between
two correct implementations is a sharper error bar on the thin cell than any
confidence interval in the file. 18 variants.

### 12. News-measured earnings surprise (H24) — 155 variants, all null

Every forward spread's CI straddles zero, and at h=21 **the largest spread of
the five belongs to the CONTROL** (the price reaction, +54.23 bps) — the
registered failure condition, stated before the run.

The contemporaneous control makes the null readable and delivers the round's
single most quotable number. Two-day announcement reaction by tone quintile:
**-385.9 / -130.4 / +43.4 / +170.9 / +278.6 bps, Q5-Q1 = +664.5 at t = +22.22**,
monotone across all five.

**+664.5 bps contemporaneous against +27.6 bps forward at h=21 — a factor of
24. Entering one session earlier would have manufactured that first number as
"PEAD".** That single comparison is the best argument in this repo for why the
entry-timing discipline exists at all.

Abnormal volume sorts the ABSOLUTE reaction monotonically (3.18 -> 5.12%) and
the signed one barely (+26.3, t = +0.91) — H15's "attention forecasts size,
not sign" reproduced independently at earnings announcements, now four times
in this round by four different measures.

The price-reaction control reproduces H2b verbatim: +5% reactors end +2.40%
(n=620), -5% reactors +2.56% (n=545), difference **-0.17pp** against H2b's
"end identically" and H26's -0.06pp. Three independent pipelines, one answer.
155 variants.

## Round 3 — final tally and what it means

**14 registered, 14 reported. 11 rejected outright. 1 confirmed and corrected
(H20, survived 2/3). 1 killed in verification (H27, 1/3). 1 inconclusive
(H22).** Roughly 800 variants; running N past 700.

### The three things this round actually produced

**1. A specific engine change to test.** `W_HIGH = 0.25` is the largest weight
in the v5 composite and measures **-298.6 (t -3.17)** once momentum is
controlled, while momentum measures **+265.0 (t +3.74)** controlling for it.
Cheapest possible next step: set `W_HIGH = 0` and re-run `scout.backtest`.

**2. Three price-data defects nobody knew about**, all found by labs that were
required to guard against defects they hadn't yet met: unadjusted splits (5.1%,
SIRI reads +925.6%), unadjusted spin-offs and reused tickers (146 events), and
frozen quotes on delisted names (which alone manufactured +896 bps of fake
drift in H26 when unfiltered).

**3. Five method rules (13-17)**, each bought with a specific mistake made and
caught here. Rules 13 and 16 have already killed three separate results.

### The one-sentence summary of the data

**News, attention, novelty, tone, earnings-surprise coverage and abnormal
volume all forecast the SIZE of the next move and essentially none of its
sign** — measured four separate ways, by four labs, with four different
conditioning variables, each reaching it independently.

### And the honest bottom line, unchanged

Nothing found in three rounds beats the market. The most promising candidate
(H22 net repurchase) is orthogonal to the engine and cost-insensitive, and
still sits at t = 1.81 while vanishing inside the engine's own eligible pool.
The best-verified finding (H20) is a measurement improvement, not a trade.

What the repo has instead is a research process that caught itself three times
in one round — H25's beta sort, H20's inflated headline, H27's coin-flip
t-statistic — and a data layer it now understands the defects of. That is worth
more than a signal it would have shipped and lost money on.
