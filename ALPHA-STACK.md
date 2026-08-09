# The Alpha Stack — where a landslide can legitimately come from

Written 2026-08-09, after re-reading every result in `BACKTEST-REPORT.md`,
`SCOUT-DESIGN.md`, `RESEARCH-AGENDA.md` and `scout/hypotheses.md`, including
the weekly-hold and gates labs from the session that closed PR #2.

The brief was: *search creatively, across fields, for formulas that make
sense, and find a legitimate way to beat the market by a landslide.*

This document is the answer. It has three parts: **why the current design
cannot win** (from this repo's own numbers), **the formulas that can**, and
**how much they are actually worth** — with the arithmetic shown, because
the size of the answer is the part everyone skips.

Code: `scout/growth.py` (the formulas), `scout/growth_selftest.py` (51
checks against simulations with known answers — run it, it needs no keys),
`scout/sleeve_lab.py` (the experiment), `scout/agenda_rank.py` (which
project to build first).

---

## Part 1 — Why the engine cannot beat the market, in one equation

Long-run wealth compounds at

```
    g  =  mu  -  sigma^2 / 2
```

Not at `mu`. The variance term is subtracted, always. Now put the repo's own
measurements next to it:

| what was measured | where | what it means for `g` |
|---|---|---|
| composite decile 1 minus decile 10 = **−0.26%** at 42 td | weekly forensics | `mu` spread ≈ **0** |
| gated book alpha **−1.08%/yr**, beta 0.77, on point-in-time data | gates lab | gates cut `mu` and `sigma` together |
| top-1 book: sd 5.06%/wk → **0.128%/wk** of drag | weekly forensics | `sigma^2/2` ≈ **−6.6%/yr** |
| pooled across entry phases: **+2.09%**/window vs SPY's **+2.53%** | H7a | net: below the benchmark |

The engine optimised **P(touch +5% within 42 td)**. First passage to a
threshold is driven by *volatility*, not by *drift*. So the objective
function was, by construction, a variance-maximiser — and variance is the
term that gets subtracted. The 63.6% hit rate and the −75% weekly compounded
return are not in tension; they are the same fact seen from two angles.

This is not a bug to fix in the ranking. It is the wrong term of the equation.

**The lever that is available instead.** At leverage `L` on an edge of
Sharpe `S`:

```
    g(L) = L*mu - L^2 sigma^2 / 2      maximised at  L* = mu/sigma^2
    g(L*) = S^2 / 2
```

Growth is **quadratic in Sharpe**. Doubling Sharpe *quadruples* achievable
growth. Nothing else in the toolbox has that exponent. So the research
target is Sharpe — and the way to buy Sharpe is not skill, it is breadth:

```
    IR = IC * sqrt(BR) * TC                    (Grinold)
    S_portfolio = w'S / sqrt(w'Cw)             (the combination identity)
```

A top-2 book rebalanced monthly has BR ≈ 24 and long-only TC ≈ 0.55. To
reach IR 1.0 it would need **IC 0.37** — roughly four times the best IC
anyone has ever documented out of sample. The measured IC was ~0. The
deficiency was never the signal; two names is not a strategy, it is a sample
of size two.

Meanwhile four sleeves of Sharpe 0.6 at zero correlation combine to **1.20**.
That, and only that, is the arithmetic of a landslide.

---

## Part 2 — The formulas, and the field each came from

All implemented in `scout/growth.py`, all validated against simulations in
`scout/growth_selftest.py`.

### 2.1 Information theory — Kelly, Shannon

| formula | code | what it does |
|---|---|---|
| `g = mu - sigma^2/2` | `growth_rate` | the objective the engine should have had |
| `L* = mu/sigma^2`, `g* = S^2/2` | `optimal_leverage` | converts Sharpe into return; the quadratic |
| `f = Sigma^-1 mu` | `kelly_weights` | growth-optimal weights |
| `lambda* = S^2/(S^2 + N/T)` | `kelly_shrinkage` | how much of Kelly survives estimation error |
| `f = 2 ln(1-q) / (ln(1-q) + ln P)` | `kelly_fraction_for_drawdown` | the fraction whose lifetime chance of a `q` drawdown is `P` |

The drawdown formula is the one that makes Kelly usable. Full Kelly carries a
**50% chance of halving the stake** — the self-test verifies this by
simulation. Sizing for "≤30% down from start, at 10% probability" gives
f = 0.27. Everything downstream is quoted at that fraction, not at full
Kelly, because full Kelly is a number for people who cannot be fired.

`kelly_shrinkage` also settles an old question by arithmetic: a 4-sleeve book
on 10 years of daily data shrinks by 0.2%; a 500-stock covariance on the same
data shrinks to 0.83 and keeps falling. **Per-stock Kelly on the S&P 1500 is
not available at this data size.** That is a fact about sample size, not
about effort.

### 2.2 Stochastic portfolio theory — Fernholz. The one *provable* edge

```
    gamma* = 0.5 * ( sum_i w_i sigma_ii  -  w' Sigma w )   >= 0
```

`excess_growth_rate`. For any long-only weights on the simplex this is
non-negative **by Jensen's inequality** — it is a theorem, not a backtest.
It is the rate at which a continuously rebalanced portfolio out-grows the
weighted average growth of its own constituents (the "rebalancing premium",
"Shannon's demon", "volatility harvesting").

The self-test demonstrates it: two simulated assets each engineered to grow
at **exactly zero**, rebalanced 50/50, compound at 2.52%/yr — the predicted
`gamma*` to three decimals.

`gamma*` is **zero for a single position** and rises with holding dispersion.
So H8's conclusion — "concentration buys dispersion, not return" — is this
formula with a minus sign in front. The concentrated book was paying `gamma*`
away.

Honest caveat, and this repo already measured its shadow: Fernholz's
diversity-weighted portfolio (`diversity_weights`, `w_i ∝ cap_i^p`) provably
beats the cap-weighted index over any period in which market *diversity does
not fall*. That condition **failed** in 2017–2026, the most concentration-
driven decade on record — which is exactly why `gates_lab` found cap-weighted
SPY beating every equal-weight book by 3pp/yr. Diversity weighting is a bet
on concentration mean-reverting, and must be sized as one.

### 2.3 Control theory — volatility targeting

`w_t = sigma_target / sigma_forecast_t`, with `blended_vol` (EWMA λ=0.94
plus a slower rolling estimate, both causal).

Volatility is the one property of returns that is genuinely forecastable —
clustering is the most replicated fact in empirical finance. Return is not.
Targeting the forecastable quantity stabilises `sigma`, and by the growth
identity a stable `sigma` compounds better than a spiky one with the same mean.

**This repo already tested a crippled version and rejected it (H5g)** — capped
at 1× so it could only ever de-lever, which in the 2020–2021 high-vol rally
was pure cost. The formula only pays when it may lever *up* in calm periods.
The self-test shows the technique's real limit too: with 6-month vol regimes
it lifts Sharpe substantially; flip the regimes to 21 days and the gain
collapses, because an 11-day-half-life forecast cannot track them.

### 2.4 Signal processing — matched filters and Kalman

- `ewmac_forecast` / `trend_forecast`: an EWMA crossover is the discrete
  matched filter for a drift in noise. Blended across four speeds and
  squashed by `tanh`, normalised by price volatility so a bond ETF and a
  copper ETF can sit in the same book.
- `kalman_beta`: minimum-variance time-varying beta. A rolling-window beta is
  a rectangular filter — it lags by half the window and forgets everything at
  once when the window rolls. The self-test's step change from β=0.5 to
  β=1.5 is tracked within ~100 bars.
- `ou_half_life`: the Langevin equation from statistical physics, used as a
  *horizon* input rather than a signal. A spread with a 90-day half-life must
  not be traded on a 5-day clock — which, generalised, is exactly what the
  weekly lab discovered the hard way.

### 2.5 Machine learning without the overfitting — HRP and shrinkage

- `ledoit_wolf_cov`: analytic shrinkage toward a scaled identity. The sample
  covariance of N assets on T observations has ~N²/2 free parameters and its
  smallest eigenvalues are biased toward zero; Kelly and mean-variance both
  *invert* it, amplifying exactly that error.
- `hrp_weights`: Hierarchical Risk Parity — recursive bisection of a
  correlation-clustered ordering, using the proper metric
  `d_ij = sqrt((1-rho_ij)/2)`. Never inverts anything, so it does not
  inherit the instability. Single-linkage clustering is written out longhand
  so the repo gains no new dependency.
- `effective_bets`: Meucci's `exp(entropy of PCA risk contributions)`.
  Straight information theory. A book of 30 names that all load on one factor
  has N_ent ≈ 1 and is a single bet in costume. **Counting positions answers
  a question nobody asked.**

### 2.6 Clinical trials — knowing when to stop

- `deflated_sharpe` (Bailey–López de Prado): the probability an observed
  Sharpe is real given how many strategies were tried. Note it penalises
  **negative skew and fat tails** — so any strategy earning a premium for
  selling insurance is docked by construction, which is correct.
- `min_track_record_length`: how long until you *could possibly* know. A
  Sharpe-1.0 strategy needs **2.7 years**; a Sharpe-0.5 strategy needs
  **10.8 years**. This is the honest reply to "it is down three months, is it
  broken."
- `sprt_decision` (Wald): a formal kill switch with stated error rates,
  reaching a decision in the smallest expected number of observations of any
  test. The self-test measures the realised rates over 40 runs each: 5% false
  keeps, 10% misses, median 356 observations to kill a dead strategy.
  Medicine adopted this so trials stop as soon as the answer is known. A live
  strategy deserves the same courtesy — in both directions.

### 2.7 Evolutionary ecology — bet-hedging

Geometric mean fitness in a fluctuating environment is the *same* criterion
as Kelly: maximise `E[log W]`, subject to surviving the bad state. That
constraint is `kelly_fraction_for_drawdown`. Ecology got there first, and its
framing is better: an organism that maximises expected offspring goes extinct;
one that maximises log offspring persists.

---

## Part 3 — What it is worth, and what to build first

`python -m scout.agenda_rank` scores every candidate by the growth it adds to
the **whole book**, not by its standalone Sharpe:

```
    S_eff    = S_lit * decay * transfer            (McLean-Pontiff + Grinold TC)
    S_after  = best LONG-ONLY mix of (book, sleeve) given rho
    dGrowth  = (S_after^2 - S_book^2)/2 * f_kelly
    score    = dGrowth * prior * data_availability / effort_days
```

Ranking by `dGrowth` instead of by `S_lit` **reorders the agenda**, and the
reason is the correlation column: a sleeve of Sharpe 0.4 uncorrelated to your
book beats a sleeve of Sharpe 0.8 correlated 0.8 to it.

The current output, against a book of Sharpe 0.50:

| rank | candidate | S_lit | S_eff | rho | dGrowth | years to prove | days |
|---|---|---|---|---|---|---|---|
| 1 | volatility targeting | 0.15 | 0.11 | 0.95 | +1.7% | paired | 2 |
| 2 | fractional Kelly sizing | 0.10 | 0.09 | 0.98 | +1.3% | paired | 2 |
| 3 | multi-asset trend | 0.75 | 0.34 | 0.05 | +1.3% | 24 | 6 |
| 4 | merger arbitrage | 0.80 | 0.22 | 0.20 | +0.2% | 58 | 20 |
| 5 | cross-asset carry | 0.70 | 0.21 | 0.25 | +0.1% | 60 | 12 *(paid data)* |
| … | net issuance, quality, short interest, seasonality | | | | ~0 | 180–550 | |
| 15 | **stock selection inside the S&P 1500** | **0.00** | 0.00 | 1.00 | 0.0% | inf | 30 |

Two findings deserve to be read slowly.

**Most published anomalies add nothing to a decent book.** After the
McLean-Pontiff decay haircut (−26% out of sample, −58% post-publication) and
a realistic transfer coefficient, net share issuance lands at S_eff 0.12.
Combined long-only with a Sharpe-0.50 book at rho 0.30, the best attainable
weight is **zero** — it makes the book worse at any positive size. The math
says: do not build it. That kills roughly half of `RESEARCH-AGENDA.md`'s
ranked programme, and it should.

**The last row is the current engine**, listed so the ranking includes the
thing this repo has spent the most time on. It scores zero because that is
what was measured.

### The stack, costed

```
  current book                       Sharpe 0.50
  + multi-asset trend                S_eff 0.34  rho 0.05   (6 days)
  + merger arbitrage                 S_eff 0.22  rho 0.20   (20 days)
  = equal-risk combination           Sharpe 0.53   (rho=0.25 BETWEEN sleeves)
  + volatility targeting             +0.11 overlay          (2 days)
  + fractional Kelly sizing          +0.09 overlay          (2 days)
  = stacked                          Sharpe 0.73

  At the market's own volatility (15%), excess return:
     today      7.5%/yr
     stacked   11.0%/yr      -> 1.5x the market's excess return at the SAME risk

  Compounded growth at the 30%-drawdown Kelly fraction (f=0.27):
     today      3.4%/yr
     stacked    7.2%/yr      -> 2.1x, because growth is QUADRATIC in Sharpe
```

**So: roughly 1.5× the market's excess return at unchanged risk, or ~2×
the compounded growth at a fixed drawdown budget.** That is what a landslide
honestly looks like from free data and a laptop. It is not 10×, and it is not
a bigger number waiting to be found by a better ranking — it is 30 days of
work across four independent builds, each of which can fail its own test, and
the whole figure rests on the assumed rho=0.25 *between* sleeves. Run
`--sleeve-corr 0.5` and watch it degrade; that sensitivity is the honest
uncertainty band.

### The provability problem, which nothing fixes

**Zero of fifteen candidates could be proven on ten years of our own data.**
`min_track_record_length` says multi-asset trend at S_eff 0.34 needs 24
years; net share issuance needs 183. Deflated-Sharpe probabilities at this
repo's ~120-trial count are near zero for almost every row.

This is not a reason to stop. It is the reason the **external evidence base
has to carry the weight**: a 100-year, 58-instrument, four-asset-class study
(Hurst–Ooi–Pedersen) is worth more than anything this repo can establish on
2016–2026, and candidates should be selected for the strength of that outside
record rather than for how well they backtest here. Our own tests can only
*disconfirm* — which is exactly the job the labs in this repo have been doing
well, and should keep doing.

---

## Part 4 — The experiment

`scout/sleeve_lab.py` runs the question directly: build multi-asset trend,
cross-asset relative momentum and a defensive sleeve over ~19 liquid ETFs;
add the repo's own gated equity book as a fourth; normalise each to equal
risk; combine with trailing-window equal-risk and HRP weights; volatility-
target the combination; size it with expanding-window fractional Kelly.

Everything is causal. Weights at date *t* are fitted on `(t-504, t)`. The
first draft was not — it used full-sample inverse volatility and full-sample
HRP, which is lookahead, and the null control is what caught it.

**Three controls before any result is believed:**

1. `--synthetic-null` — 12 independent draws of assets that earn *exactly*
   the cash rate. Every sleeve's mean Sharpe must be ~0. Currently: trend
   −0.06, xsec −0.16, defensive −0.07, all |t| < 2. *One* null draw is not a
   control — a 10-year Sharpe has a standard error near 0.32, and the first
   single-draw run printed −0.64 for a sleeve that is unbiased.
2. `--synthetic` — generated data with a known edge. Trend reaches Sharpe
   2.81 and the stacked Kelly book 1.23, confirming the plumbing recovers an
   edge that is definitely there.
3. `--audit` — re-runs with the one-bar signal lag removed. If the honest and
   contaminated runs look alike, there is no lookahead.

**It has not yet been run on real data**, because `scout/data.py` needs
Alpaca keys and this container has none (`.env` is correctly gitignored, and
the keys from the earlier sessions did not travel with the branch). Adding
them and running `python -m scout.sleeve_lab` produces the real table.

### Registered before it runs

Hypotheses **H9–H14** are in `scout/hypotheses.md`, written before the lab
touched real data, with expected signs and the conditions that would make
each one fail. Per house rule 2, they count toward N whatever the outcome.

The single most likely failure is already written down: **the sleeves turn
out correlated.** Trend and cross-sectional momentum on the same ETF set
correlate 0.77–0.78 in both synthetic runs, which drops `effective_bets` to
1.6–2.0 of 4. If that survives on real data, this stack is two bets wearing
four coats, and the honest stacked Sharpe is much closer to 0.55 than 0.73.

---

## Part 5 — What this does not claim

- **No new stock-selection signal.** The repo's evidence says that layer is
  empty, and nothing here contradicts it.
- **No result on real data yet.** Everything above is either an identity
  (`gamma*`, the growth equation, the combination formula — true by proof),
  a simulation (the self-test), or an estimate from external literature with
  its haircuts shown.
- **Leverage is assumed free and continuous.** It is neither. The sleeve lab
  reports the unlevered book alongside; treat the levered figure as an upper
  bound.
- **2016–2026 is one macro era.** It contains multi-asset trend's worst
  decade *and* the strongest mega-cap concentration on record — the two
  conditions least favourable to two of the four components. A mediocre
  result on this window is not disproof, and a spectacular one should be
  disbelieved.
- **Rule 9 still applies.** Any portfolio-level claim must be pooled across
  entry phases before it is quoted. Weekly-tiling labs are exempt; this one
  rebalances every 5 days and tiles the calendar, so it inherits the
  exemption — but the moment anything here is run at a 42-day cadence, it
  must go through `phase_lab --sweep` first.
