# Where this project stands

Written 2026-08-09, updated 2026-08-12 after Round 7. Read this first if you
are picking the work up cold — it is the shortest path to not repeating
anything.

## The one-line summary

**Nothing tested beats SPY.** Seven rounds, ~1,000 variants, 22 registered
hypotheses, zero shipped signals, seven retracted or killed headlines. What the
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
| net share repurchase (H22) | killed in verification: **28% of sessions carried 81% of P&L** while the median split bisected that regime; half of the rest was a sector tilt |
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

## Round 5 results (complete, verified)

- **H31 construction — CONFIRMED, and the only non-beta structural result in
  five rounds.** Cap-weighting the SAME holdings is worth **+0.150 Sharpe and
  +3.48 pp/yr** (pit500; +0.160 on sp1500). The difference carries **beta
  0.077**, is positive in both halves and all three thirds, and on the momentum
  books runs +5.20 pp/yr at beta 0.06 (pit500) and +5.06 at beta 0.02 (sp1500) —
  positive in every half and all six thirds across both universes.
  **Externally confirmed by two real ETFs: SPY − RSP gives +0.180 Sharpe and
  +3.43 pp/yr at beta 0.043**, against our internal +0.150 / +3.48. The lab and
  the market agree to 0.03 of Sharpe.
  **But it does not beat SPY** — it turns a book losing by 2.73 pp/yr into one
  insignificantly ahead (t 0.46). A recovery, not an edge. Inverse-vol weighting
  is the one scheme that does NOT help.
- **H32 workouts — REJECTED, verification 1 of 3.** Two independent kills.
  (a) **No risk-free rate anywhere in the lab** — for every other hypothesis
  beta ≈ 1 so the `rf x (1 - beta)` bias is ~0; for the first beta-0.27 sleeve it
  is maximal. Alpha +2.39% (t 1.02) → **+0.76% (t 0.33)**; the gain from adding
  it to a SPY book goes +0.049 → **+0.006 GROSS and +0.000 at any cost level**.
  (b) **The return is 18 bidding wars.** Of 448 deals, 18 topping bids (4.0%)
  contribute +1.475 pp of the +1.728 pp total. Drop them and the sleeve goes
  6.68%/yr → **2.82%/yr**, alpha → **−1.08% (t −0.46)**. Spread capture net of
  breaks is +0.78%/yr — less than the round-trip cost these names quote. The
  pre-registered mechanism earned zero. Reported skew +1.00 was those same 18
  deals; remove the top 10 and it flips to **−4.41**.
  The era story was the rate cycle (rf by thirds 1.23/1.05/4.43% vs raw alphas
  1.69/1.50/5.02%, **correlation +1.000**).
  **What survived:** the sample IS announcement-based (SEC form.idx, never the
  completions feed), and the beta collapse is real — Dimson lead-lag betas
  0.220/0.261/0.254/0.317 never recover toward 1.0. A target pinned to a fixed
  cash price is a genuine risk property, just not a return source.
  Caveat for reuse: 3-5% of the book holds the wrong company (T = AT&T the
  acquirer, E = an Italian ADR, LEN = Lennar acquirer-side).
- **H33 coverage — REJECTED** (51 variants). Not priced: +25.5 bps, t 0.53,
  thirds [-65.3, +166.7, -25.1]. The Hong-Lim-Stein interaction died four ways.
  **It independently reproduced the construction finding: weighting the same 102
  names is worth +91.8 bps/window against a best selection spread of +25.5 —
  construction beats selection 3.6 : 1.**
- **H34 partnership — REJECTED** (112 variants). At rho 0.511 the combination
  cannot reach a landslide.

## Keys: unblocked 2026-08-10 (fresh Alpaca pair in `.env`, verified 200).
The master bar cache now holds **3,670 symbols x 2,664 dates** including SPY,
RSP, QQQ, IWM, IEF and BIL with full history. Rotate the keys when work pauses.

## Round 7 — COMPLETE (2026-08-12). Stop forecasting: three zero-forecast portfolios

Six rounds asked "which stocks will go up?" and measured IC ~ 0 every time;
with IC = 0, Grinold's IR = IC*sqrt(BR)*TC zeroes everything downstream. Round
7 changed the question: three designs whose expected return contains NO return
forecast anywhere, since with mu flat, g = mu - sigma^2/2 collapses to
g_p = mu - 0.5*w'Sigma w — all covariance terms, and covariance IS forecastable
here (29/29 symbols). Full write-up: BACKTEST-REPORT.md "Round 7"; registry
entries H37-H39.

| | verdict | the number that decides it |
|---|---|---|
| **H37 min-variance growth** (`zeroforecast_lab.py`) | mechanism CONFIRMED, trade REJECTED | Delta_mu vs its own EW bench = 0 (t -0.82) exactly as the theorem predicts — but vs SPY the residual mu gap is **-5.39%/yr**, and the vol-matched levered book **loses at a ZERO financing spread**. Attribution: it is the low-vol anomaly (loading t 20-32), named as such. |
| **H38 rebalancing premium** (`rebalance_lab.py`) | arithmetic CONFIRMED (gamma* recovered 1.0004 on synthetic), money REJECTED | Buy-and-hold's Jensen drift collects **~101%** of gamma* — and over the real decade the tradeable premium is **NEGATIVE**: -0.67%/yr at full horizon, all 12 entry phases negative. "Volatility harvesting" compares a portfolio to a non-portfolio. |
| **H39 forced flow** (`flow_lab.py`) | REJECTED outright | The pre-registered flow calendar (turn-of-month + tax-loss + index-rebalance, 25% of days in SPY, rest in BIL) sits at the **41st percentile of its own matched-time-in-market null** — below the median random calendar. In-window SPY earned 4.40 bps/day vs 5.79 outside. |

What the round settles: cap-weighted buy-and-hold **already collects every
mechanical premium these designs harvest** — gamma* via drift, the variance
saving via its megacap mu — at zero turnover and zero forecast. The
zero-forecast family is closed. Anything left must be real mu information the
market has not priced, or uncorrelated sleeves around a SPY core (the H32
diagnosis, still the only structural opening).

Process note: the three labs were written by agents that died at a spend limit
mid-round; they were run, debugged (two one-line crashes, no numbers touched)
and verified from the main session. Exploratory scrap for the ledger: SPY
earns **-36 bps/day on the 42 third-Friday index-rebalance sessions** (Welch
t -2.91, Sidak threshold 2.77 at 9 calendars) — one cell of nine, crash-day
contaminated, not tradeable long-only, recorded not believed.

## Round 6 — ran to completion 2026-08-10; full write-up pending

`overlay_lab.py` completed after the keys were restored (results committed in
`overlay_results.json`, 30+ variants, same-close vs next-close ladders, Rule
13a/b, matched-exposure nulls including 2020+2022-excised dropout). Headline
shape, subject to the pending write-up: every trend overlay cuts maxDD roughly
in half at roughly SPY's Sharpe (best dual_avg 0.848 vs SPY 0.761 same-sample)
with alpha t ~ 1.2-1.4 — the drawdown claim survives its nulls, the return
claim does not clear the bar. Write-up deliberately deferred: Round 7 was
published first by explicit instruction.

## Round 6 as originally planned — STOPPED, superseded by the above

The one genuinely untested idea left, and it came from an outside review of this
repo's record: *"several old tests were correct about their narrow question but
were applied to the wrong job. Volatility scaling can reduce risk, but it cannot
create return; a slow trend filter can avoid prolonged collapses, but it will
not predict every crash. The candidate needs both a real return source AND a
risk rule, with each doing only the job it can actually do."*

Verified against the record, that is right about three of our tests:
- **H5g** scaled volatility on a stock book, capped at 1x, and was judged on RETURN.
- **H5a/H5b/H5c** tested trend and crash flags as CRASH PREDICTORS on the picks
  and were rejected because "cash there costs return, +716% vs +733%" — a
  drawdown tool marked down for not making money.
- **The alpha-stack's vol targeting on SPY** cut drawdown -34.0% -> -27.3%
  CONSISTENTLY and was rejected because its SHARPE gain flipped across halves.

And it exposed a genuine gap, confirmed in the code: `sma200ok` exists in
`scout/signals.py:47` ONLY as a cross-sectional stock filter. **A trend rule has
never been applied to the index itself and judged on drawdown.**

`scout/overlay_lab.py` (57 KB) is written and committed. It stopped because
**BIL is not in the bar cache** and the keys died before it could be fetched.
That matters: BIL is the cash leg AND the risk-free rate, and its absence is
exactly what killed H32 (alpha +2.39% t 1.02 -> +0.76% t 0.33 once rf was
included). A trend overlay sits in cash by design, so running it without a real
bill series would repeat that error at its maximum.

**To resume:** restore keys, run `python -m scout.bars` to warm BIL/IEF/SHY,
then `python -m scout.overlay_lab`. The decisive control is already specified in
the module: a RANDOM-TIMING book with MATCHED TIME-IN-MARKET. If the real rule
sits inside that null, the "edge" is just reduced exposure in a volatile decade.

Honest prior: Faber 2007 is among the most published rules in finance,
2016-2026 is entirely post-publication and a documented bad decade for equity
trend. Expect *slightly better Sharpe, materially lower drawdown, lower raw
return* — and if that is the answer, that IS the result.

## THE NEXT ACTION

**The vNext execution handoff (uploaded 2026-08-12) is the next mission**: an
externally-reviewed program of five event-driven hypotheses — pure/unexpected
news, 10-K textual change (Lazy Prices), opportunistic insider purchases,
repurchase-announcement x undervaluation, dividend-reinvestment forced flow —
with standalone sleeve gates and a final portfolio architecture around a
continuous SPY core. Target: +13-20 pp/yr net excess. To avoid registry
collision the handoff's H36-H40 register here as **H40-H44**. Work per the
handoff runs on a dedicated branch (`claude/vnext-real-backtests` from
`agent/backtest-only`), deliverable `SCOUT-VNEXT-REAL-RESULTS.md`.

Its five mechanisms are exactly the kind Round 7 says are the only ones left:
event-driven mu information, not price-derived covariance. The repo's priors
that bear directly: generic news tone/PEAD already failed (the handoff's
designs are the residual/conditioned versions, which is the right response);
H22 was killed for regime concentration (the handoff's H39-analog conditions
on valuation instead of retuning it); and every timestamp/survivorship trap it
warns about has already been measured here.

Still true and still the cheapest confirmed improvement: **switch the engine's
book from equal weight to cap weight** — it stops the book losing ~2.7 pp/yr
to its own construction. The open question on it stands: the cap-vs-equal gap
is partly a mega-cap-decade feature (Fernholz's diversity theorem says it
reverses when concentration mean-reverts).

## The honest bottom line

"Beat the market by a landslide" requires `g = S^2/2` — growth is quadratic in
Sharpe, and Sharpe comes from **uncorrelated** return sources, not better
forecasts. Every source tested so far correlates with equity beta. Until one
does not, leverage cannot manufacture a landslide, and the measured answer stays:
own the index, enter at the close, size with better volatility estimates.
