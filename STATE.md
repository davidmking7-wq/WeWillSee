# Where this project stands

Written 2026-08-09 at the end of a long session. Read this first if you are
picking the work up cold — it is the shortest path to not repeating anything.

## The one-line summary

**Nothing tested beats SPY.** Five rounds, ~800 variants, 18 registered
hypotheses, 17 reported, zero shipped signals, seven retracted or killed
headlines. What the
project has instead is a data layer whose defects are known, a research process
that catches itself, and one structural finding that reframes the whole effort.

## Operational status

- **Research only.** The repository reads data and updates a scorecard; it has
  no live-order path.
- **The weekly executor stays out.** Its strategy was rejected and the executor
  is deliberately absent/disabled rather than waiting to be scheduled.
- **Paper-forward before promotion.** A backtest result can enter a lab, but a
  change that affects picks, probabilities, portfolio construction, or exits
  cannot become current `main` behavior until it passes the frozen forward-test
  contract in `FORWARD-TEST.md` on future data.
- **A merge is not trading permission.** Passing the gate only permits a
  research-code change. Live execution remains prohibited.

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
went. H31 later confirmed that cap-weighting recovers most of this handicap,
but still does not beat SPY.

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

## BLOCKED: the Alpaca keys are dead (2026-08-09)

Both `data.alpaca.markets` and `paper-api.alpaca.markets` return **401
unauthorized**. `.env` is intact and the key is being read correctly (26-char
key, 44-char secret) — the credentials were revoked or rotated at Alpaca's end.

**To unblock:** get free keys at https://alpaca.markets (paper account,
data-only), put them in `.env` at the repo root (gitignored), and re-run.

**What still works with no credentials at all:**
- `scout/sec_bulk.py` — 23.4M XBRL facts, already built on disk
- `scout/bars.py` — 1,506 symbols x 2,664 dates, 2016-2026, already cached
- `scout/deals.py` — SEC filings need no key
- `python -m scout.growth_selftest` — 51 checks, fully offline
- every result and document in this repo

Nothing already measured is lost.

## Round 6 — STOPPED, incomplete, and worth resuming

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

The construction result is confirmed but **not significant on its own**
(t 1.02-1.51 depending on universe and book). Its credibility rests on
consistency — every half, every third, both universes, difference beta ~0.05 —
and on the SPY-vs-RSP external check, not on a p-value.

The next research candidate is to switch the engine's paper book from equal
weight to cap weight. It requires no new signal and is the only change five
rounds of work support, but it is not yet approved behavior: freeze the exact
rule, register its forward success bar, and run it through `FORWARD-TEST.md`.
It will not beat the market; the historical result merely recovered roughly
the 2.7 percentage points per year the equal-weight construction had lost.

If you want to test further, the open question is whether the cap-vs-equal gap
is a permanent property or a feature of the 2016-2026 mega-cap decade. It is
almost certainly partly the latter — `gates_lab` already found cap-weight
beating every equal-weight book in this window, and Fernholz's diversity theorem
says the reverse should hold when concentration mean-reverts.

## The honest bottom line

"Beat the market by a landslide" requires `g = S^2/2` — growth is quadratic in
Sharpe, and Sharpe comes from **uncorrelated** return sources, not better
forecasts. Every source tested so far correlates with equity beta. Until one
does not, leverage cannot manufacture a landslide, and the measured answer stays:
own the index, enter at the close, size with better volatility estimates.
