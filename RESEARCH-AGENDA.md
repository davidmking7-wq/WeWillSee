# Research Agenda — faster or bigger gains, and how to find them

Written 2026-08-08 after a combined empirical + literature deep-dive.
No pipeline changes made; this is the map for what to test next and HOW.

## How edges are actually found (the method, first)

The professional process, distilled — and now the house rules here:
1. **Mechanism before data.** An idea gets tested only if its cause can be
   stated in one sentence first (a behavioral friction, a forced flow, a
   structural constraint). Pattern-mining OHLCV is how solo researchers
   fool themselves.
2. **Hypothesis registry.** Every idea and every variant is logged BEFORE
   testing, so the trial count N is honest. All multiple-testing math is
   a function of N; lying to yourself about N is the classic death.
3. **Significance sized for the trial count:** t > 3 (not 2) for anything
   standalone (Harvey-Liu); deflated Sharpe with the registry's N.
   Corollary: ~10 years of daily data honestly validates maybe ONE modest
   edge per year of work. Choose hypotheses by prior, not by scan.
4. **Purged walk-forward** (parameters fit only on data ending ≥1 full
   label window before the test block), costs modeled at 1× AND 2×, and
   never headline the all-period backtest.
5. **Paper-trade incubation** before capital: the picks.xlsx scorecard IS
   the incubator — add signal-price vs fill-price tracking.
6. **ML only for meta-labeling** (predicting when the existing signal
   works), never for signal discovery at this data size.
7. Post-publication decay is real (McLean-Pontiff): haircut any published
   effect ~26% out-of-sample, ~58% post-publication.

## Question 1: same gain in LESS time — answer: NO (measured, twice)

- Our own data: top-pick excess return vs SPY is NEGATIVE through day 21
  (−0.45%), all edge accrues days 21–42 (peak day ~35). Holding only the
  first 5–21 days then switching to SPY annualizes at 6.7–15.1% — at or
  BELOW SPY itself; the full 42-day hold makes 23.2%.
- The literature says the same (Jegadeesh-Titman event-time: month 1 weak
  or negative, peak months 2–5; no credible study shows momentum alpha in
  days 1–14; fresh entries right after ranking face short-term reversal).
- The cost math kills faster cycling independently: halving the hold
  doubles turnover (+1.2–2.4%/yr drag) for a winner-side gain of the same
  order. Cost-mitigation that DOES work: buy/hold bands, not speed.
- One legitimate fast variant exists — short-term momentum among
  HIGH-TURNOVER names only (Medhat-Schmeling RFS 2021, 1-month holds) —
  but it is a different strategy, not an acceleration of this one.
- Minor measured note: our excess peaks near day 35 and fades slightly by
  42; a 35-day exit is worth a registered test (expected gain ~0.1-0.2pp
  per window — marginal).

## Question 2: MORE gain — answer: yes, modestly. Ceiling ~2–6%/yr extra.

Ranked by evidence quality × cost, all free-data, all registry-worthy:

1. **Insider cluster-buying overlay** (SEC Form 4, free, real-time).
   Opportunistic/cluster buys still show 4–8% abnormal over 6–12 months
   in small/mid caps — the strongest surviving free signal. Use as a
   tie-break/overweight on existing candidates. Expected +1–3%/yr.
2. **Earnings-pipeline extensions** (data already in hand): pre-earnings
   momentum variant (enter shortly before scheduled reports — the
   surviving form of the announcement premium; our own decomposition
   shows the announcement's 2 days carry the densest return, +0.44% at
   22bp/day); small-cap PEAD via free EDGAR XBRL surprises (dead in
   large caps, alive down-cap). Expected +0.5–2%/yr.
3. **Meta-labeling the v5 engine**: small classifier predicting which of
   OUR OWN picks will hit, from regime/vol/liquidity/insider/earnings
   features. The one ML project that fits this data size. Expected
   +0.5–1.5%/yr via avoided losers.
4. **Execution hygiene (adopt, no test needed)**: enter at/near the CLOSE,
   never the open; never chase opening gaps (overnight-return
   literature). ~+0.5–1%/yr, free.
5. Also registry-worthy: residual (market-adjusted) momentum ranking;
   short-interest exclusion screen (FINRA data, free); same-calendar-month
   seasonality tilt (Heston-Sadka); sleeve-level vol management
   (Barroso-Santa-Clara). Frog-in-the-pan: marginal.
6. **Declared dead — do not spend time**: index add/delete effects,
   post-split drift, day-of-week effects, overnight-only trading,
   pre-FOMC drift, generic 13F cloning, ML signal mining.
7. **Declared dead by Round 7 (2026-08-12) — the whole zero-forecast
   family**: long-only minimum-variance / low-vol construction as a growth
   edge (H37 — the levered book loses at zero financing spread; it is the
   low-vol anomaly, named), volatility harvesting / rebalancing premium
   vs buy-and-hold (H38 — Jensen's drift collects ~101% of gamma*; the
   tradeable sign was NEGATIVE this decade), and calendar forced-flow
   timing on SPY (H39 — 41st percentile of its own matched null). Every
   mechanical premium the covariance matrix offers is already inside
   cap-weighted buy-and-hold.

Data debt to settle before trusting any new small-cap result: one month
of a delisting-inclusive dataset to re-run the S&P 1500 headline once —
our own PIT test proved ~1pp/window of mirage in large caps; small caps
are worse.

## Round 1 results (2026-08-08, all four tested — see scout/hypotheses.md)

1. **Insider buying: promising, unproven.** Right sign in both halves
   (69% hit, +6.9% avg, zero tail losses) but only 13 occurrences in ten
   years — insiders almost never buy into momentum strength. Not shipped.
   The surprise: heavy insider SELLING marked BETTER picks (74% vs 60%
   hit, both halves, n=93) — selling into strength is profit-taking, not
   information. Sign-flipped ⇒ new hypothesis, not tradeable; the one
   actionable takeaway is to never penalize insider selling.
2. **Earnings extensions: both rejected.** Timing entries to 5-15 td
   before the report loses more ranking quality than the catalyst adds;
   announcement-reaction drift is dead even in mid/small caps (positive
   and negative reactors end identically, n≈6k).
3. **Meta-labeling: validated and shipped** (the round's winner). ML
   Check column: walk-forward AUC 0.60 vs 0.45, strong-bucket 73%/+4.4%
   vs weak-bucket 55%/−0.1%. Fits during calibration, scores during
   scans — user-invoked only.
4. **Buy-at-the-close rule: shipped** — bold banner in the workbook +
   skill report line.

Score: 1 shipped signal, 1 shipped discipline, 3 honest rejections, 1
flagged for more data. That ratio is what real research looks like.

## Round 2 results (2026-08-08) — nothing shipped, one number retracted

Asked: where do the losses come from, can bear markets be predicted
better, can the +733% run be improved? 23 pre-registered variants across
three new labs (`regime_lab`, `tail_lab`, `phase_lab`). Zero improved it.
Full numbers in BACKTEST-REPORT.md "Round 2"; the method lessons:

1. **The intuition was wrong, and the data said so immediately.** Bear
   and crash windows average +0.5% with a −8.3% worst; the portfolio's
   five worst windows carried NO market-state flag. High volatility is
   the *best* entry state (+6.8%/window). Every regime-based exposure
   rule therefore lost money. Checking the forensics BEFORE building the
   protection is what stopped a plausible, expensive rule from shipping.
2. **A shipped rule failed its first honest test.** The breakeven-after-
   +5% exit was adopted on single-stock statistics and never run at
   portfolio level; there it costs about a third of the compounded
   return. Rule 8 for the house: *every* rule must be tested at the level
   it is applied, not the level it was discovered.
3. **The biggest failure was a sampling choice nobody had questioned.**
   Holds are 42 td and scans are 21 td apart, so the non-overlapping
   backtest silently picked one of six possible entry schedules — and it
   was the best one. The other five return +0.4% to +3.5% per window
   against its +4.6%. Walk-forward, train/holdout, both-halves
   consistency and engine versioning all passed; none of them could see
   this, because every one of them shared the same entry dates.
   **Rule 9: any portfolio-level claim must be pooled across entry
   phases before it is quoted** (`phase_lab --sweep`).
4. **What survived is smaller and truer**: pooled, the engine returns
   ~+2%/window at every book size from 1 to 8, versus SPY's +2.5%.
   Concentration buys dispersion, not return. The tool's real, still-
   defensible claim is the calibrated one — these names reach +5% sooner
   and more often (47% of windows vs SPY's 38%) — not that they compound
   faster.
5. **The only adoption is a de-risking, not an edge**: ladder the
   capital across entry dates so the outcome stops depending on which
   day the account started.

Score: 0 shipped signals, 1 retracted headline, 1 demoted rule, 1 new
protocol rule. A round that deletes a false number is worth more than a
round that adds a true-looking one.

## The honest bottom line

Faster is not available: the profit physically accrues in weeks 4–8 and
cannot be harvested early. Bigger is available only in increments — a
disciplined year of the ranked program above might add 2–6 points a year
on top of the current engine, each increment fought for with the method
in section 1. Anyone offering more than that is selling something.

## Correction to the significance bar (2026-08-09, at the user's challenge)

Section 1 rule 3 of this document says **"t > 3 (not 2) for anything standalone
(Harvey-Liu)"**. That rule has been applied bluntly across Round 3 — including
to results it was never meant for — and the user was right to push back on it.
This section corrects it.

**What the rule is actually for.** Harvey-Liu's argument is about MULTIPLE
TESTING. The finance literature has tested thousands of factors, so a t of 2
inside that search space is close to meaningless: at a 5% false-positive rate,
800 tests throw off roughly 40 spurious "discoveries" by chance alone. Round 3
ran ~800 variants. In that context t = 2 genuinely is noise.

**What it is not for.** The multiple-testing penalty applies to the SEARCH that
produced a number, not to every number. A hypothesis with a strong external
prior, registered before anyone looked, is a CONFIRMATORY test and does not
inherit the search cost of the exploratory sweep running alongside it.

### The corrected rule

**The bar scales with how much search produced the number.**

| regime | what it looks like | bar |
|---|---|---|
| **Confirmatory** | strong external evidence base, pre-registered, one or a few specifications | t ~ 2 with consistent halves, consistent entry phases, and Rule 13 satisfied is meaningful evidence |
| **Exploratory** | found by sweeping, or the Nth variant of a family | t > 3 AND a deflated Sharpe computed at the true running N |

Report, for every claim: the t-statistic, the number of variants YOU ran, and
which regime the claim is in. Do not reject a confirmatory result solely for
failing t > 3, and do not accept an exploratory one solely for passing t = 2.

### Worked example, and why this matters here

**Cross-sectional momentum** (Jegadeesh-Titman 1993; replicated across 40+
countries and 200+ years; and independently in this repo's own v3/v4
train/holdout protocol) measured **+132.8 bps per 42 sessions gated, t = 2.04,
positive in both halves**, market-adjusted, in H25. Under a blanket t > 3 that
is "rejected". Under the corrected rule it is a confirmatory test clearing its
bar, and it is the strongest live result in this repo.

**Headline news tone**, the 800th variant of a within-sample sweep, at t = 2
would be noise. Same number, different evidentiary weight, because a different
amount of searching produced it.

The blanket rule caused momentum to be under-reported for a full round while
fourteen exploratory hypotheses were being correctly rejected. That is the cost
of a bar that does not distinguish between the two.

### What does NOT change

Rules 13-17 all stand and none of them are significance thresholds — they are
about whether the number means what it appears to mean:
risk-adjust before believing a sort (13); quote the permutation SE against the
Newey-West SE (14); controls can leak too (15); a bootstrap t inside its own
Monte-Carlo noise has not cleared anything (16); give every arm of a comparison
the same machinery (17). A confirmatory result still has to survive all five,
plus the equal-thirds era check that killed H22 and the entry-phase pooling of
Rule 9.

Momentum at t = 2.04 is promoted to "the live candidate", not to "shipped".

## Adopted from Mira (2026-08-09): the downgrade taxonomy and refresh conditions

`byteseek/Mira` (https://github.com/byteseek/Mira) is an agent-native investment
research workspace. Two of its skills are now installed at
`.claude/skills/data-analysis-quality-gate/` and
`.claude/skills/macro-economic-analysis/`.

**An honest assessment of what it adds, because overselling it would be the
exact failure this repo keeps documenting.** Mira's quality gate exists to stop
an LLM from asserting a number it never computed — it forces a data-requirement
brief, a calculation ledger, and an explicit downgrade when the arithmetic was
skipped. That is a real and common failure mode, and it is **not the one that
has been killing us.** Our labs always computed everything; all seven
retractions were subtler — beta in disguise (four times), a Newey-West lag wrong
by 41x, a missing risk-free rate, and eighteen lucky deals. Across Mira's ten
skills and fourteen loops, exactly one file mentions backtesting at all, and
nothing addresses survivorship, point-in-time membership, or multiple testing.
Rules 9 and 13-17 remain the load-bearing discipline here.

Two things from it are genuinely worth adopting.

### 1. A downgrade vocabulary

This repo has verdicts (CONFIRMED / REJECTED / INCONCLUSIVE) but no vocabulary
for *why* something is not yet trusted, which has let "inconclusive" cover very
different situations. Adopt Mira's taxonomy:

| tag | meaning | example from our record |
|---|---|---|
| `calculation_gap` | the arithmetic was not done or was done wrong | H29 — market-adjusted the levels, never the deltas |
| `source_gap` | the data cannot answer the question | H33 — 120 large caps cannot test a neglect premium |
| `watch_only` | direction is right, evidence is not sufficient to act | H31 — consistent everywhere, t only 1.02-1.51 |
| `needs_refresh` | true in-sample, conditional on a regime that may end | H31 again — the cap-vs-equal gap is partly a mega-cap decade |

### 2. `refresh_condition` — what would change the answer

Mira requires every durable conclusion to record what would overturn it. This
repo has never done that, and it is exactly what a five-round research record
needs, because several results are **conditional rather than wrong**.

Conditions now on the record:

- **H31 (cap-weighting, +0.150 Sharpe):** reverses if market concentration
  mean-reverts. Fernholz's diversity theorem says equal-weight should win when
  it does; `gates_lab` already measured cap-weight beating every equal-weight
  book across 2017-2026, the most concentration-driven decade on record.
  **Refresh when the top-10 share of S&P 500 market cap falls for two
  consecutive years.**
- **H20 (5-min realised variance, 13-16% better):** a measurement result, not a
  market one. Refreshes only if the data source changes.
- **H32 (merger arb, beta 0.271):** the beta collapse is structural and should
  persist. The absent return was 18 bidding wars; **refresh if a period with a
  materially higher topping-bid rate occurs**, and note the sample contains no
  2008-style credit crisis, which is merger arb's canonical failure.
- **The fourteen rejected signals:** no refresh condition. They were rejected on
  mechanism, sign, or controls, not on regime.
