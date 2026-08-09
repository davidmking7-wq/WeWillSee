# Where this project stands

Written 2026-08-09 at the end of a long session. Read this first if you are
picking the work up cold — it is the shortest path to not repeating anything.

## The one-line summary

**Nothing tested beats SPY.** Five rounds, ~800 variants, 16 registered
hypotheses, zero shipped signals, six retracted or killed headlines. What the
project has instead is a data layer whose defects are known, a research process
that catches itself, and one structural finding that reframes the whole effort.

## What is PROVEN to work best, in order

1. **SPY buy-and-hold.** CAGR 14.99%, Sharpe 1.004. Every book built lost to it
   on Sharpe. On point-in-time data, 0 of 24 books beat it on either measure.
2. **Enter at the close, never the next open.** +5.29 bps/window, both halves,
   t = 2.07. Free. Caveat: a random pick earns +4.51, so it is a market-wide
   overnight effect, not selection-specific. Keep the rule, drop the story.
3. **Forecast volatility from 5-minute realised variance, not daily closes.**
   13-16% better QLIKE (corrected down from a claimed 20.3%), 29 of 29 symbols,
   both halves, survived 2 of 3 verifiers. Use for SIZING and stop levels only —
   its own market-timing payoff was rejected, and adding lag *improved* it.
4. **Keep the gates and the $10M liquidity floor.** Gates cut drawdown at
   slightly better Sharpe. H23 proved the apparent premium below the floor
   inverts to negative on point-in-time data — the floor is protecting you.
5. **If ranking at all, rank on momentum alone.** `drop mom12` costs -57.2 bps
   (t -3.20), consistent halves, both universes, and it is NOT a beta artifact.
   But the tradeable long-only alpha vs SPY is +14 bps/window at t = 0.28. It
   tells you how to rank; it does not say ranking beats the index.

## The finding that reframes everything

**The equal-weight gated pool is -0.216 Sharpe against cap-weighted SPY BEFORE
a single stock is picked. The selection layer adds +0.030 back.**

Four rounds optimised a component worth one seventh of a structural handicap
nobody had measured. Portfolio CONSTRUCTION, not selection, is where the money
went. H31 (running at time of writing) tests whether cap-weighting recovers it.

## Do NOT re-test these

All rejected with controls; details in BACKTEST-REPORT.md and hypotheses.md.

| dead | how it died |
|---|---|
| news attention, tone, novelty, earnings-news | forecast the SIZE of the next move, never the sign — four independent ways |
| 52-week-high weight (H25) | a beta sort; market-adjusted t = 0.29 |
| short-horizon reversal (H21) | beta +0.33; alpha -3.35 bps |
| illiquidity (H23) | t = +4.09 on today's index, **-42.68 on point-in-time** |
| post-earnings drift (H26) | 89% priced by the day after; contemporaneous t = +15.4, forward ~0 |
| intraday momentum (H19) | the closing half hour is the WORST of thirteen bins |
| accruals (H27) | killed in verification: t = 3.0006 vs an analytic 2.9510 |
| net share repurchase (H22) | killed in verification: one 2.7-year regime, half a sector tilt |
| idiosyncratic vol (H28), sentiment (H16), multi-asset trend sleeves | rejected |
| **W_HIGH = 0 (H29) — RETRACTED** | the "fix" was +65.7 raw = -5.1 alpha + 71.8 beta. **Do not change config.W_HIGH.** |

## Data defects you must guard (all measured here)

1. **5.1% of splits unadjusted** — SIRI reads +925.6%, AAPL 2020-08-31 reads -74.2%
2. **146 further >50% one-day moves** — spin-offs and reused tickers
3. **Frozen quotes** on delisted/halted names — unfiltered these manufactured
   +896 bps of fake drift in H26. Retire a symbol at its first run of ~10
   identical closes.
4. **Completed-merger feeds are survivorship-poisoned** — see `scout/deals.py`.

## Infrastructure built (use it, do not rebuild it)

- `scout/bars.py` — shared daily-bar cache. 1,506 symbols x 2,664 dates,
  2016-2026, 93.3% dense. A full S&P 1500 request returns in ~3 seconds.
  Seven labs each wasted ten minutes before this existed.
- `scout/sec_bulk.py` — 23.4M XBRL facts, whole market, point-in-time by FILING
  date. Use `load_tags([...])`, never `load()` (~4 GB resident). Four bugs were
  found and fixed in it, each of which had produced a confident wrong answer.
- `scout/news_data.py` — Benzinga panel 2016-2026, fully cached, with
  after-close attribution and a templated-wire filter.
- `scout/intraday.py` — 5-min bars, session decomposition, split repair.
- `scout/deals.py` — merger universe built from ANNOUNCEMENTS, not completions.
- `scout/growth.py` + `growth_selftest.py` — Kelly, drawdown-constrained
  fraction, Fernholz excess growth, HRP, effective bets, deflated Sharpe, SPRT.
  51 self-checks, no keys needed: `python -m scout.growth_selftest`.

## Method rules that have each already killed something

9 (pool entry phases), 13 (risk-adjust every sort **and every difference**),
14 (permutation SE vs Newey-West SE), 15 (controls leak too), 16 (a bootstrap t
inside its own Monte-Carlo noise has cleared nothing), 17 (same machinery on
every arm of a comparison). Plus the corrected significance bar in
RESEARCH-AGENDA.md: **confirmatory results clear at t ~ 2; exploratory ones
need t > 3 and a deflated Sharpe at the running N (>700).**

Rule 13 caught its own author's next mistake one level down — H29 adjusted the
levels and forgot that a *difference* of two beta-laden sorts is beta-laden.

## Round 5 results (complete)

- **H32 workouts — REJECTED, but the first non-beta source found here.**
  448 announced deals. Sleeve 6.68%/yr, Sharpe 0.718, **beta 0.271** (t~7
  against 1.0), maxDD -16.5% vs SPY's -33.8%; COVID crash -8.28% vs -33.48%.
  The placebo settles causation — same tickers 250 sessions earlier have beta
  1.054. All three equal thirds positive; 7 of 7 entry offsets positive.
  **Rejected because:** alpha t = 1.02, correlation to SPY is 0.511 (not ~0),
  and break-even on ALPHA is 38 bps/side — added to SPY it is +0.049 Sharpe
  gross, +0.006 at 25 bps, +0.000 at 50 bps. Buffett claimed 10-20%/yr largely
  uncorrelated; measured 6.7%/yr at rho 0.51 — sixty years of competition.
  **UNVERIFIED: all three verifiers died on the spend limit.**
- **H33 coverage — REJECTED** (51 variants). Not priced: +25.5 bps, t 0.53,
  thirds [-65.3, +166.7, -25.1]. The Hong-Lim-Stein interaction died four ways.
  **But it reproduced the structural finding independently: weighting the same
  102 names is worth +91.8 bps/window against a best selection spread of
  +25.5 — construction beats selection 3.6 : 1.**
- **H34 partnership — REJECTED** (112 variants). At rho 0.511 the combination
  cannot reach a landslide.
- **H31 construction — NEVER RAN** (spend limit). See below.

## THE NEXT ACTION, and it is the only one that matters

**Run `python -m scout.construction_lab`.** It is committed and ready.

It asks whether cap-weighting recovers the -0.216 Sharpe construction handicap.
That question is now supported by TWO independent measurements — Round 4's
-0.216 (construction) against +0.030 (selection), and H33's 3.6 : 1 on a panel
Round 4 never touched. It is the largest measured effect in the project, it
requires no signal, and it has never been tested.

Everything else in five rounds has been optimising the smaller layer.

## The honest bottom line

"Beat the market by a landslide" requires `g = S^2/2` — growth is quadratic in
Sharpe, and Sharpe comes from **uncorrelated** return sources, not better
forecasts. Every source tested so far correlates with equity beta. Until one
does not, leverage cannot manufacture a landslide, and the measured answer stays:
own the index, enter at the close, size with better volatility estimates.
