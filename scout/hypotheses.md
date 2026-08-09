# Hypothesis Registry

Rule (RESEARCH-AGENDA.md): every idea is logged HERE, with its mechanism
and expected sign, BEFORE any test runs. Every variant tried gets a row.
The trial count N below feeds the multiple-testing discipline.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H1 | 2026-08-08 | Opportunistic open-market insider BUYING (code P, officer/director, non-plan) within 30d before entry predicts higher hit rate — insiders act on unpriced private information, strongest down-cap. | picks with buys > picks without | **PROMISING, UNPROVEN** — sign right in BOTH halves (all: 69% hit, +6.9% avg, 0% tail) but n=13 in ten years: insiders almost never buy into momentum strength. Fails the t>3 bar by construction. Not shipped; revisit with a larger event-study sample or live accumulation. |
| H1b | 2026-08-08 | Heavy non-plan insider SELLING clusters (≥3 distinct sellers, 30d) predict lower hit rate. | sell-cluster picks < others | **REJECTED — SIGN FLIPPED** (sell-cluster picks hit 74% vs 60% quiet, +4.8% vs +1.8%, both halves, n=93). Interpretation: heavy selling marks the strongest, most-run names (insiders take profits into strength; sells are liquidity, not information). A flipped sign is a NEW hypothesis, not a shippable result — do NOT trade it without fresh validation. Actionable now: never penalize insider selling. |
| H2a | 2026-08-08 | Entering when the scheduled report is 5-15 td ahead concentrates the earnings-catalyst premium (risk premium for holding the binary event) into the window's front half. | earnings-timed top-3 ≥ standard top-3 | **REJECTED** — worse avg end in both halves (train +0.74 vs +2.21; holdout +2.61 vs +3.50): forcing the timing sacrifices ranking quality, which dominates. |
| H2b | 2026-08-08 | Small/mid caps with a large positive announcement reaction (2-day ≥ +5%) drift further over the next 42 td (PEAD survives down-cap where algos don't price it instantly). | post-reaction cohort > SPY + > base | **REJECTED** — no drift asymmetry: +5% reactors and −5% reactors end identically (≈+1.7-2.4% both, ≈SPY), n=2-3k per cell. PEAD via price reaction is dead down-cap too, in this sample. |
| H3 | 2026-08-08 | A walk-forward logistic model on entry-time features (regime, vol, segment, momentum shape, earnings flags) separates our own picks' HIT probability better than the calibration cell alone (meta-labeling refines a known signal). | model AUC > cell baseline | **VALIDATED AS INFORMATION — then REMOVED from the product at user request** (2026-08-08; selection use failed H3b, informational value judged not worth the complexity) — OOF AUC 0.60 vs 0.45 rank-only, both halves; top-third 73%/+4.4% vs bottom-third 55%/−0.1%. Shipped as the ML Check column (fit in user-invoked calibration, scored in user-invoked scans only). |
| H3b | 2026-08-08 | Using the H3 model for SELECTION (skip ML-weak picks, or rank by model p) improves portfolio returns over composite order. | ML-selected top-N > baseline top-N | **REJECTED** (scout/ml_portfolio_lab.py, walk-forward, same 39 OOF periods): baseline top-2 +4.88%/win, 51% of windows ≥+5%, +409% comp; skip-weak +3.45%/+193%; rank-by-model +3.86%/+193% with a −31% worst window — worse in BOTH halves. The model predicts hit odds; portfolio profit lives in end returns, which composite order captures better. ML Check stays information-only; the skill must never auto-replace a pick on a weak flag. |
| H4 | 2026-08-08 | Entering at/near the close (never the open) avoids paying overnight drift + open-auction spreads. Adopted from literature (Lou-Polk-Skouras) without a local test — execution hygiene, not a signal; not testable with daily bars alone. | n/a | **ADOPTED, SHIPPED — and TESTED at last by H18e/H18f (2026-08-09).** The rule is KEPT and its rationale is REWRITTEN: on identical picks, close(t) entry beats open(t+1) entry by **+5.29 bps per 42-session window** at the shipped book size (CI [+0.39, +10.73], positive in both halves, costs cancel), but a random draw from the same eligible pool earns +4.51 bps and the picks' own first-night edge over that pool is +0.68 bps with a CI straddling zero. So H4 is the MARKET's overnight drift, worth ~+0.3%/yr, not an edge in the picks — and its second half ("never chase opening gaps", the open auction's wider spread) is still untested because bars carry no quotes. |

| H5a | 2026-08-08 | Crash-state windows (SPY < 200d SMA AND SPY 21d vol > its expanding 80th pctile — the tool's EXISTING ex-ante crash flag, Daniel-Moskowitz panic states) produce the portfolio's worst windows; sitting in cash there cuts losses more than it costs upside. | crash→cash ≥ baseline on compounded + better worst/maxDD | **REJECTED — PREMISE FALSE** (scout/regime_lab.py, 54 windows). Crash windows average **+0.52%** — low, but POSITIVE, and their worst is only −8.3%. Cash there costs return (+716% vs +733%) and does not touch the real tail: **0 of the 5 worst windows were crash-flagged.** |
| H5b | 2026-08-08 | Bear windows (SPY < 200d SMA at entry) warrant HALF exposure, not zero (momentum's bear-market rebound risk cuts both ways). | bear→half improves maxDD without losing compounded | **REJECTED** — bear windows average +0.49% (n=11, worst −8.3%); half = +723%, cash = +705%, both below +733%. Confirms the earlier bull-only result with a cleaner decomposition. |
| H5c | 2026-08-08 | High-volatility entries (SPY 21d vol > expanding q80, regardless of trend) warrant half exposure (vol clustering ⇒ fat tails ahead; Barroso-Santa-Clara mechanism, long-only form). | highvol→half improves worst/maxDD at small avg cost | **REJECTED — SIGN FLIPPED, WORST VARIANT TESTED.** High-vol windows are the BEST windows: +6.84% vs +3.73% when calm, 53% reach +5%. Halving there cuts compounded from +733% to **+437%** (t=−2.25 vs baseline), and does not improve worst (−22.7%) or maxDD. Long-only momentum in a high-vol tape is buying the rebound, not the crash. |
| H5d | 2026-08-08 | H5a + H5c combined. | best left-tail protection | **REJECTED** — +429% vs +733%; inherits H5c's damage. |
| H5e | 2026-08-08 | When the engine's OWN eligible pool collapses (few names clear the gates vs its expanding median), the cross-section has no healthy momentum and the top-2 book is being picked from junk — an internal breadth warning needing no new data. | small-pool windows < normal windows; half exposure helps | **REJECTED** — small-pool windows do run cooler (+2.87% vs +5.14%) but never lose big (worst −8.3%, 0 of the worst 5); half exposure = +610% vs +733%. The gates are already doing their job — a thin pool is not a reason to shrink. |
| H5f | 2026-08-08 | Market breadth (share of the universe above its own 200d SMA) below its expanding 20th percentile marks a narrow, fragile tape where momentum unwinds. | low-breadth windows < others; half exposure helps | **REJECTED** — best of the market-state flags (catches 1 of the worst 5, avg +1.68% vs +5.51%) but still costs money: +668% vs +733%. |
| H5g | 2026-08-08 | Volatility targeting on the PICKS' own forecast vol (Barroso-Santa-Clara, long-only form): scale exposure by expanding-median sigma42 / current sigma42, capped at 1x (never lever). Momentum crashes are forecastable through the strategy's own vol, more than through market state. | better worst/maxDD and ≥ baseline compounded | **REJECTED overall (+602% vs +733%), and the ONLY variant that helped in the recent half** (2022-2026: worst −12.8 vs −14.6, maxDD −13.4 vs −16.1, +219% vs +223% — protection at ~no cost). Fails first half badly (+120% vs +158%) because it de-levers the 2020-2021 high-vol rally. Inconsistent across halves ⇒ not shipped. |

### H6 — where the losses actually are (registered AFTER the H5 forensics)

The H5 forensics killed the market-state premise and pointed somewhere
else: the top-2 book's worst windows are **single-name collapses in calm
bull markets** (2020-01 BLDR −27, 2024-11 FICO −17, 2019-07 OKTA −22,
2018-05 IBKR −21). 18 losing windows sum to −135pp and the worst 5 are
half of that. So the tail is **idiosyncratic**, and the lever is the
per-stock exit the tool already ships but the portfolio backtest never
applied — `window_strategy` holds every pick to the deadline.

These rows are exploratory-by-construction (born from looking at the
losses), so they carry a higher snooping discount: only the SHIPPED
parameter (2.0 sigma) counts as pre-specified; the others are sensitivity
checks reported for honesty, never for picking a winner.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H6a | 2026-08-08 | Applying the tool's own shipped per-stock disaster stop (close ≤ entry − 2.0 x that stock's sigma42) inside the top-2 window portfolio caps the idiosyncratic collapses that produce every worst window. | better worst/maxDD, small cost to avg | **NEUTRAL — the stop is nearly inert here** (scout/tail_lab.py). 2.0 sigma42 is ~26% below entry, so it fired on only **3 of 108 legs in ten years**: worst window −22.7% → −22.4%, compounded +733% → +719%. It caps a catastrophe it almost never meets; keep it (cheap insurance, real in a 2008), but it is not a return lever. |
| H6b | 2026-08-08 | Stopping out and REPLACING with the next-ranked name from the same scan for the rest of the window recovers the cost of H6a (capital keeps working instead of sitting in cash). | ≥ baseline compounded AND better worst | **NOT PROVEN — n=3.** Best number in the family (+768% vs +733%, worst −22.1%, t=+1.19) but it rests on three replacement events in a decade. Not shippable on that evidence; re-test if the stop ever fires often. |
| H6c | 2026-08-08 | The shipped breakeven rule (once a pick closes +5%, exit on any close back at/below entry) protects give-backs without capping upside. | better worst, small avg cost | **REJECTED — AND IT IS A SHIPPED RULE.** Fires on 29 of 108 legs; cuts compounded from +733% to **+471%** (both halves worse). It does exactly one good thing — 2020-01 goes −22.7% → −4.1% — and pays for it by selling winners that dip and then run. Momentum names round-trip through entry all the time. Docs/skill corrected. |
| H6d | 2026-08-08 | A trailing stop at 1.5 x sigma42 below the running peak (Lei-Li) beats a fixed disaster level. | trailing ≥ disaster stop | **REJECTED** — 1.5 sigma: +516%; 2.0 sigma: +662%; both below +733%, both halves. Consistent with exitlab's single-stock finding: trailing exits sell the shakeouts momentum needs to survive. |
| H6e | 2026-08-08 | Inverse-volatility weighting of the two picks (risk parity, instead of 50/50) shrinks the tail because the collapses come from the higher-sigma name. | better worst/maxDD at no avg cost | **REJECTED (marginal)** — +692% vs +733%; worst −22.0 vs −22.7. The collapses were not the high-sigma name (2020-01's BLDR had *below*-median sigma), so the premise fails. |
| H6f | 2026-08-08 | Stop sensitivity: 1.5 / 2.5 / 3.0 sigma. Reported to show whether H6a's result is a knife-edge or a plateau. | monotone-ish, no cherry-picking | **PLATEAU, monotone** — 1.5σ +635%, 2.0σ +719%, 2.5σ +698%, 3.0σ +733% (never fires). Tighter always costs more; the shipped 2.0 is on a flat part of the curve, not a tuned peak. |

### H7 — is +733% a lucky calendar phase, and does laddering fix it?

The whole portfolio lab samples ONE phase: scans exist every 21 trading
days, and the non-overlapping run takes every other one (index 0, 2,
4...). The odd phase (1, 3, 5...) is an equally valid, fully independent
set of 54 windows that has never been looked at. If the two phases
disagree, part of +733% is entry-date luck and the honest number is the
average of the two.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H7a | 2026-08-08 | The odd calendar phase gives materially the same result as the even one (the edge is in the ranking, not the entry date). | phase spread small | **REJECTED — AND IT INVALIDATES THE HEADLINE NUMBER** (scout/phase_lab.py). Six equally valid entry schedules (offset 0/7/14/21/28/35 td) give avg/window **+4.56, +0.78, +0.43, +3.48, +0.66, +2.63** and compounded **+685, −14, −4, +304, −6, +215**. The shipped +733% run is the LUCKIEST OF SIX. Pooled best estimate: **+2.09%/window**, vs SPY +2.53%. The phase spread (SD 1.7pp) is exactly the sampling noise of 53 windows (SE 1.5pp) — six noisy draws of one mean, and we had been quoting the max. |
| H7b | 2026-08-08 | A LADDER — half the capital entering on each phase, so a new top-2 book starts every month instead of every two — keeps the same average return while cutting the worst window and the drawdown, because no single entry date owns the whole account (time diversification, not name dilution: name dilution already tested worse at top-3/top-5). | ≈ equal avg, better worst/maxDD/consistency | **ADOPTED as the honest implementation** (not as an edge). It cannot raise the mean — it IS the mean — but it removes the coin flip: 6-sleeve ladder worst window −20.1% and maxDD −46.1% against single-phase worsts of −30.7% and −82.8%; 2-sleeve ladder −18.4%/−29.6%. Shipping a strategy whose outcome depends on which Monday you started is indefensible once you know the spread. |
| H8 | 2026-08-08 | Registered right after H7a (a re-test of an already-shipped decision on unbiased sampling, not a new signal hunt): the top-2 book was chosen on ONE phase, so pooled across all six phases the ranking of book sizes may change. | pooled ordering differs from single-phase | **CONFIRMED — the ordering vanishes.** Pooled avg/window: top1 **1.97**, top2 **2.09**, top3 **2.02**, top5 **2.01**, top8 **2.21**, SPY **2.53**. Concentration buys no return at all; it only buys dispersion (phase spread top1 5.43pp → top8 1.68pp; ladder maxDD −48.3% → −29.9%). The "top-2 is the best configuration" claim was a single-phase artifact. |

Protocol note for H5: the 2022-2026 holdout is exhausted, so acceptance
requires (a) parameters frozen ex ante (they are: the crash flag shipped
in v2, q80/200sma are the tool's existing definitions, 0.5 is the only
new constant), (b) improvement concentrated in the windows the mechanism
targets, (c) consistency across both halves, (d) explicit small-N
disclosure (bear/crash windows are few). Anything that passes ships as
PROVISIONAL pending live confirmation.

Round-2 trial count: H5 = 11 exposure variants, H6 = 12 exit/weighting
variants, H7/H8 = 6 phases x 5 book sizes. Nothing in H5 or H6 beat the
baseline, and H7 showed the baseline itself was a lucky draw — so the
round's only positive output is a correction, not a new signal. That is
the expected outcome of an honest multiple-testing regime; the alarming
result would have been finding a "winner" among 23 tries.

Prior related trials (count toward N): earnings proxy-skip (2 variants —
REVERSED by real dates), sell-before-event (failed), catalyst-ahead
ranking (shipped), 25+ exit rules, 4 engine variants, 5 expectation
exits, sector exclusion (failed), 12 portfolio configs, ML meta-label
(removed), bull-only filter (tested in portfolio lab — hurt).

### H9-H14 — portfolio geometry instead of stock selection (registered 2026-08-09, BEFORE any real-data run)

Registered per RESEARCH-AGENDA rule 2. Context: the weekly forensics and the
gates lab jointly established that the SELECTION layer adds nothing at any
horizon tested (decile 1 minus decile 10 = -0.099% at 5 td, -0.257% at 42 td;
gated book ann. alpha -1.08% on point-in-time data). These rows therefore
attack a different term of `g = mu - sigma^2/2` — see ALPHA-STACK.md for the
derivation and `scout/growth.py` for the formulas. Every one of them counts
toward N whatever the result.

Failure conditions are stated for each, because a hypothesis without one is
not a hypothesis.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H9 | 2026-08-09 | Multi-asset time-series trend over liquid ETFs earns a positive Sharpe that is roughly UNCORRELATED with the equity book, because it bets on the sign of drift across four asset classes rather than on the equity premium (macro information diffuses slowly; institutional flows push with recent moves). | sleeve Sharpe > 0, \|rho to SPY\| < 0.3 | **REGISTERED — not yet run on real data.** Synthetic-edge run recovers Sharpe 2.81, synthetic null 12 draws mean -0.06 (t=-0.54). Fails if the real sleeve is unprofitable OR if rho to the equity book exceeds 0.3, which would make it the equity premium in a costume. Prior note: 2016-2026 contains managed futures' worst decade, so a weak result here is weak evidence against a 100-year prior. |
| H10 | 2026-08-09 | Cross-asset RELATIVE momentum (long the strongest half of the instrument set, short the weakest) is a materially different bet from H9's time-series trend, so the two combine to a higher Sharpe than either alone. | rho(trend, xsec) < 0.5 | **REGISTERED — early evidence AGAINST.** Both synthetic runs put rho at 0.77-0.78 and effective_bets at 1.6-2.0 of 4 sleeves. If real data agrees, H10 is rejected and the stack is two bets, not four — which cuts the projected stacked Sharpe from 0.73 to roughly 0.55. Recorded now so the number is not quietly revised later. |
| H11 | 2026-08-09 | Volatility targeting the COMBINED book (allowed to lever UP, unlike the H5g variant that was capped at 1x) raises its Sharpe, because volatility is forecastable while return is not and the growth identity subtracts sigma^2/2. | Sharpe(vol-targeted) > Sharpe(raw), both halves | **REGISTERED.** Distinct from H5g, which was rejected: that one was long-only single stocks, capped at 1x, so it could only ever de-lever and lost the 2020-21 high-vol rally. Fails if the uplift is absent in either half, or if it comes entirely from leverage rather than from stabilised risk (check: does realised vol actually land near target?). |
| H12 | 2026-08-09 | Trailing-window HRP weighting of the sleeves beats trailing inverse-volatility weighting out of sample, because it never inverts the covariance matrix and so does not amplify small-eigenvalue error. | Sharpe(hrp) >= Sharpe(eqrisk) | **REGISTERED — early evidence AGAINST.** In the synthetic-edge run HRP scored 0.32 against equal-risk's 0.96. With only 4 sleeves there is barely a hierarchy to exploit, which is a fair prior for rejection: HRP's published advantage is at 20+ assets. |
| H13 | 2026-08-09 | Expanding-window fractional Kelly, sized by the drawdown constraint f = 2ln(1-q)/(ln(1-q)+lnP), converts the combined book's Sharpe into return WITHOUT breaching the stated drawdown budget. | realised max drawdown <= the budget; growth rises | **REGISTERED.** The formula bounds drawdown FROM THE START, not from a running peak — the self-test measures peak-to-trough at a median -29.8% against a 20% start-relative budget on the same paths. Fails if realised peak-to-trough exceeds roughly 1.5x the budget, or if leverage spends most of the sample at the cap (which would mean the constraint never bound and the sizing is decorative). |
| H14 | 2026-08-09 | The rebalancing premium gamma* = 0.5(sum w_i sigma_ii - w'Sigma w) is a material, harvestable part of a diversified book's return — the term the concentrated top-2 book was giving away (H8: "concentration buys dispersion, not return"). | gamma* > 1%/yr on the sleeve book | **REGISTERED — identity, not anomaly.** gamma* >= 0 is a theorem (verified over 300 random long-only books in the self-test) so the hypothesis is about MAGNITUDE only. Honest counterweight already on the record: the gates lab measured cap-weighted SPY beating every equal-weight book by ~3pp/yr in 2017-2026, i.e. Fernholz's diversity condition failed in exactly this window. A large gamma* that still loses to SPY is the expected outcome, not a contradiction. |

Trial-count note: H9-H14 add 6 registered hypotheses plus the sleeve lab's
variants (3 sleeves x 2 weighting schemes x 2 leverage layers = 12 configs),
so N rises by ~18. The provability arithmetic in ALPHA-STACK.md Part 3 is
computed AT that trial count: at N~120 and ten years of daily data, none of
these can clear a deflated-Sharpe gate locally. They are therefore accepted
or rejected on (a) external evidence strength, (b) failing to be disconfirmed
here, and (c) the controls in the lab — never on a local p-value.

Method rows adopted from this round, independent of any result:

- **Rule 10: one null draw is not a control.** A 10-year Sharpe has a
  standard error near 0.32. The sleeve lab's first single-draw null printed
  -0.64 for a sleeve that is unbiased across 12 draws (mean -0.07). Any
  "our null looks clean" claim must quote a distribution and a t-statistic.
- **Rule 11: fit every weight on trailing data only.** The sleeve lab's first
  draft weighted sleeves by full-sample inverse volatility and full-sample
  HRP. Both are lookahead, both are easy to write by accident, and neither is
  visible in a headline number. `causal_weights` exists because of it.

### H9-H14 results (2026-08-09, real data — full tables in BACKTEST-REPORT.md "The alpha stack")

Ran on 2534 days of Alpaca SIP data, 20 ETFs, 2016-08..2026-08. Registered
above BEFORE the run; statuses filled in after. **Nothing shipped.**

| # | verdict |
|---|---|
| H9 multi-asset trend | **HALF-CONFIRMED, NOT USEFUL.** The diversification claim holds — beta to equity 0.09-0.14, well inside the pre-registered \|rho\|<0.3 bar. The return claim fails: Sharpe 0.24 at the 5-day cadence, 0.43 monthly, 0.48 at literally zero cost, against SPY's 0.76. An uncorrelated sleeve that earns a third of the benchmark's Sharpe adds nothing at any long-only weight — which `agenda_rank` predicts for exactly these inputs. Prior caveat stands: 2017-2026 is managed futures' worst documented decade and 19 ETFs are a thin proxy for 50-80 futures. |
| H10 sleeve independence | **REJECTED, as pre-registered.** rho(trend, xsec) = 0.67 at 5 td and 0.70 at 21 td, against the <0.5 bar. **Effective bets 1.02 of 4.** The stack is one bet wearing four coats. This was written down in advance as the most likely failure, and it is the one that fired. |
| H11 volatility targeting | **PARTIAL — a drawdown tool, not a return tool.** On SPY at matched volatility: Sharpe 0.78 -> 0.80, maxDD -34.0% -> -27.3%. But by halves 1.03 vs 0.92 then 0.56 vs 0.63 — the drawdown gain is consistent, the Sharpe gain is not. Fails the both-halves condition. NOT shipped, and the ALPHA-STACK projection of +0.11 Sharpe from this overlay is retracted. |
| H12 HRP vs inverse-vol | **REJECTED (no material difference).** 0.30 vs 0.28 combined Sharpe. With 4 sleeves there is no hierarchy to exploit; HRP's published advantage is at 20+ assets, as the pre-registered prior said. |
| H13 fractional Kelly | **MECHANICALLY CORRECT, OUTCOME NEGATIVE.** The expanding-window rule behaved as designed (mean 1.52x, de-levering to 0.85x by the end) and still turned a 0.40-Sharpe book into -0.20 with a -47% drawdown. Leverage converts Sharpe into return; it cannot create Sharpe. Applying it to a book weaker than the benchmark magnifies the weakness — `growth_at_leverage` says so directly, and this is that formula measured. The drawdown budget was breached (-47% against a 30% start-relative budget), which is consistent with the self-test's finding that peak-to-trough runs ~1.5x the start-relative bound. |
| H14 rebalancing premium | **REAL BUT NEGLIGIBLE.** gamma* = 0.27%/yr on the 4-sleeve book. The theorem holds (it is always >= 0) and the magnitude is simply too small to matter at this holding count. Harvesting it materially needs many more, less-correlated positions — which is the same requirement H10 just failed. |

**Round verdict: 0 shipped, 6 tested, 1 projection retracted.** The
projection in ALPHA-STACK.md Part 3 (stacked Sharpe 0.73, ~1.5x the market's
excess return at equal risk) is **measured at 0.40 against SPY's 0.76** and
is withdrawn. The error was not in the algebra — the combination identity is
exact — but in the input: rho between sleeves was assumed 0.25 and measured
0.67. The document flagged that assumption as the one the result rested on,
which is the only thing that went right about it.

Trial count: N rises by 18 (6 hypotheses + 12 lab configurations), plus the
4 cost/cadence sensitivity runs, which were diagnostics reported in full
rather than a search for a winner — all four are in BACKTEST-REPORT.md
including the ones that look best.

- **Rule 12: a sizing rule is not a strategy.** H13 is the cleanest
  demonstration in the repo: a correctly implemented, correctly de-levering
  Kelly rule still lost money because the thing it was sizing had no edge.
  Test the signal before building the sizing on top of it.

### H16 — headline sentiment drift, and whether it is anything but reversal (registered 2026-08-09, BEFORE any run)

Mechanism (Tetlock 2007; Tetlock-Saar-Tsechansky-Macskassy 2008): media tone
carries fundamental information that is incorporated with a lag, because
reading and interpreting text is costly, so pessimistic coverage predicts
lower subsequent returns and optimistic coverage higher ones beyond what the
same-session price move already reflects. Lab: `scout/news_sentiment_lab.py`
over the cached Benzinga panel (120 point-in-time-liquid S&P 500 names as of
2016-01-04, 2016-2026, 308,870 stories).

The decisive question is stated up front, per Rule 1: **most naive news
studies re-discover short-term reversal in a costume.** H16c is therefore
the row that decides H16 — a tone effect that vanishes once the same-session
return is in the regression is not a news effect.

Signal: net tone_{i,t} = (pos - neg) / (pos + neg + 1) summed over every
story attributable to session t (news_data's timestamp rule: readable before
close t). Cross-sectionally ranked within the date among liquid names that
have news. **The shift:** weights formed at close t are multiplied by the
close(t)->close(t+1) return and onward — `Wbar.shift(1) * ret1` in
`ls_portfolio`, nowhere else.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H16a | 2026-08-09 | Cross-sectional net headline tone predicts forward returns: quintile long-short (Q5-Q1) is positive at 1/5/21/42 sessions, strongest early and decaying (slow diffusion of textual information). | LS > 0, monotone decay | **REJECTED — WRONG SIGN, AND NOT SIGNIFICANT EITHER WAY.** Q5-Q1 earns **-2.19 / -1.51 / -1.27 / -1.09 bps per day** at h = 1 / 5 / 21 / 42 (Tetlock predicts positive). Newey-West t = -0.99 / -1.15 / -1.46 / -1.33; every 95% moving-block bootstrap CI straddles zero ([-6.10, +2.27] at h=1, [-2.95, +0.53] at h=21). Both halves negative at all four horizons, so the sign is stable even though the magnitude is not distinguishable from noise. n = 2,637 dates, 142,000 symbol-sessions with news, mean cross-section 53. |
| H16b | 2026-08-09 | Restricting to SPECIFIC stories (not templated wire, <= 10 tags) sharpens the effect, because broadtape movers-lists carry no firm-specific information and only add noise. | LS(specific) >= LS(all) | **REJECTED.** Filtering does not sharpen anything: at h=1 the spread goes to -0.17 bps (t = -0.07) and the two halves disagree in sign (+2.14 then -2.48 bps). At h=21/42 it is indistinguishable from the all-story version (-1.09 both). The cleanest reading is that the all-story spread was never carrying firm-specific information to concentrate. |
| H16c | 2026-08-09 | **THE DECIDING ROW.** Tone has incremental power over the same-session return: in a joint Fama-MacBeth cross-sectional regression of forward return on tone rank AND same-session return rank, the tone coefficient stays positive and significant with date-clustered (Newey-West) standard errors. | lambda_tone > 0 with t > 3 | **REJECTED — AND THE PRE-REGISTERED EXPLANATION IS ALSO WRONG.** Tone is NOT reversal in a costume, because there is no reversal here to hide behind: the same-session return alone predicts nothing (lambda_ret t = +0.19 / -0.76 / -0.64 / -0.20 at h = 1/5/21/42) and its rank correlates with the tone rank at only **0.117**. Adding it therefore barely moves tone (-4.12 -> -3.59 bps/rank at h=1; -25.0 -> -20.6 at h=21). Tone simply never reaches significance on its own: t_tone = -1.84 / -1.27 / -1.40 / -1.35. H16 fails on POWER, not on confounding — a different and more honest failure than the one that was expected. |
| H16d | 2026-08-09 | The tone spread survives inside each tercile of the same-session return (a double sort separates news content from price reversal). | tone spread > 0 in all 3 return terciles | **REJECTED — spread is negative in every cell.** h=5: -1.58 / -11.66 / -13.82 bps across the three same-session-return terciles; h=21: -37.86 / -47.50 / -35.33 bps. ~47,000 observations per cell. The sign does not depend on the price move, which corroborates H16c: this is not reversal. |

Controls (nulls, not trials): (i) tone shuffled across symbols WITHIN each
date, 200 draws; (ii) placebo — each symbol permanently assigned another
symbol's tone series, which keeps each tone series' own time-series
properties and breaks only the pairing, 200 draws; (iii) random quintile
assignment from the identical eligible pool, 200 draws; (iv) matched
benchmark = equal-weight of the eligible-with-news pool. Both halves split at
the median date. Moving-block bootstrap by date, block length = holding
period, because overlapping holds make adjacent days dependent. Costs 10 bps
round trip on measured turnover, plus the break-even round-trip cost.

Failure conditions, stated in advance: H16a fails if the sign flips across
halves or the LS mean is inside the shuffled-tone null; H16c fails — and
takes H16 with it — if lambda_tone loses significance once the same-session
return is included; the whole thing is untradeable regardless of sign if the
break-even round-trip cost is below 10 bps.

### H16 results (2026-08-09) — REJECTED, plus two findings worth more than it

| # | verdict |
|---|---|
| H16e | **POST-HOC, registered after the sign came out negative** (4 variants, h = 1/5/21/42): is the negative tone tilt just momentum or attention written in words? Adding the trailing 21-session return to the joint regression absorbs 30-45% of the tone coefficient at h=5 (-6.94 -> -4.74) and h=21 (-20.6 -> -14.0) and none of it at h=1 or h=42; log story count explains nothing (t_attn = 0.04 / -0.12 / 0.77 / 1.29). So part of it is momentum in words, not all of it — and no coefficient in the table is distinguishable from zero. |

**Finding 1 — the spread is mostly BETA, and market-adjusted there is nothing
at all.** A dollar-neutral quintile spread is not market-neutral: pessimistic
coverage clusters in temporarily high-beta names, so the book runs beta
**-0.16 / -0.15 / -0.11 / -0.10** on SPY. In a decade when SPY compounded at
15.82%/yr that tilt alone is roughly half the raw spread (-2.67 of -5.51 %/yr
at h=1; -1.79 of -3.20 at h=21). Residual alpha t-statistics are -0.52 /
-0.44 / -0.65 / -0.63, and for firm-specific stories at h=1 and h=5 the alpha
is POSITIVE (+2.63% and +0.62%/yr, t = +0.46 and +0.19). Rule 13 for the
house: **regress every dollar-neutral book on the benchmark before quoting its
sign** — dollar-neutral is not risk-neutral, and a 0.15 beta is worth 2.4%/yr
in this sample.

**Finding 2 — a within-date permutation null is the wrong control for a
persistent signal, and it is anti-conservative by 2-3x.** The three nulls
disagree, and the disagreement is the point. Shuffled-tone and random-pick
nulls produce a standard error 2.26x and 2.70x TIGHTER than the Newey-West SE
of the real series at h=21 (2.96x and 3.49x at h=42), so they score the result
at z = -3.34 and -3.90 — apparently clearing this repo's t>3 bar — while the
honest t is -1.46. Permuting labels within a date destroys the persistence of
a tone tilt (sticky sector and attention exposure) and therefore the
autocorrelation of the P&L it generates. The **placebo** null, in which every
symbol keeps its own tone series and only the pairing is broken, reproduces
the real width (SE ratio 1.25 at h=21) and agrees with the block bootstrap:
z = -1.85. Rule 14: **never quote a permutation p-value without printing the
ratio of the null's SE to the real series' Newey-West SE next to it.**

**Costs.** At 10 bps round trip the h=1 book loses 48.8%/yr net on measured
turnover of 3.44x gross per day. In the REGISTERED direction the break-even
round-trip cost is negative at every horizon, because the gross return is
negative.

**Sign-flip footnote (NOT a result — H1b house rule).** The best contrarian
variant (all stories, h=21) is gross Sharpe 0.416, +3.20%/yr, break-even 15.0
bps, netting +1.06%/yr after its own turnover at 10 bps — against SPY's
+15.82%/yr. Of that 3.20%, **1.79pp is the +0.113 beta it inherits by being
long the pessimistic names**; residual alpha +1.33%/yr at t = +0.65. Deflated
Sharpe at the two-sided trial count 2N=36 is 0.212. A levered-down index
position, not a signal.

Trial count: N rises by **18** (H16a 4 + H16b 4 + H16c 4 + H16d 2 registered,
H16e 4 post-hoc). Control draws are nulls and do not count. Deflated Sharpe of
the best variant in the registered direction, at N=18: **0.027**.

Data notes stamped on this round: (i) `scout/data.py` daily bars still carry
the missing AAPL 2020-08-31 4:1 split — the lab repairs 1,173 bars from
Alpaca's own corporate-actions feed, and any daily study in this repo that
spans that date without a repair contains a fabricated -74.2% return; (ii)
`intraday.unapplied_splits_close(tol=0.15)` CANNOT classify events whose log
ratio is under 0.30 — it false-positived MET's 2017-08-07 Brighthouse spin-off
(filed ratio 1.122, bars already adjusted, observed jump 1.0099), so this lab
only auto-repairs ratios above exp(0.35) and prints the rest; (iii) 49% of
symbol-sessions with news score exactly zero net tone (no lexicon word fired),
which forces unequal quintiles — mean sizes Q1 7.2, Q2 12.9, Q3 14.7, Q4 7.7,
Q5 10.7 — so Q1 and Q5 are the genuinely negative and genuinely positive
names, not 20% buckets; (iv) **the one-day contamination scale, measured on
this exact panel**: tone rank x its OWN session's return = **+6.80 bps**, tone
rank x the NEXT session's return = **-0.35 bps**. Attributing a story to the
session it was published in rather than the session it can be traded in would
have produced a large POSITIVE "Tetlock effect" roughly 20x the honest number
and with the opposite sign. Any news study in this repo that cannot point at
its shift is presumed to be measuring that +6.80.

### H18 — does the equity premium accrue overnight, and does the SHIPPED H4 rule survive? (registered 2026-08-09, BEFORE any run)

Mechanism (Lou-Polk-Skouras JFE 2019; Cliff-Cooper-Gulen 2008;
Hendershott-Livdan-Roesch 2020): the overnight window is a closed-market risk
transfer — inventory cannot be hedged, information accrues with no continuous
price, and whoever carries it demands compensation, which is paid in the
opening gap; the intraday window is a continuous competitive auction where
market makers flatten, so it pays for liquidity provision, not for bearing
overnight risk. If true, close-to-open captures nearly all of the long-run
equity premium and open-to-close contributes ~zero.

**Why this matters HERE specifically: H4 above ("enter at/near the CLOSE,
never the open") is the only shipped rule in this repo with no local test.**
It was adopted from this literature on 2026-08-08 and shipped as a banner in
picks.xlsx. H18e/H18f are its first honest test.

Lab: `scout/overnight_lab.py`. Universe = the 120 most liquid S&P 500 members
AS OF 2016-01-04 by point-in-time membership (`scout/pit.py`; the same panel
the news labs use, so BRCM/CELG/EMC/TWX/ESRX/MON/AET/PXD are in and no
post-2016 addition is) plus SPY as benchmark only. Daily SIP bars, official
opening and closing auction prices, split-repaired against Alpaca's own
corporate-actions feed.

**The shift:** legs are built with exactly one backward shift,
`close.shift(1)` -> `prev_close`; overnight(t) = open(t)/prev_close(t) - 1 and
intraday(t) = close(t)/open(t) - 1, and every portfolio applies
`W.shift(1) * leg`, so a signal computed through close(t) earns its first
return in the close(t)->open(t+1) gap.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H18a | 2026-08-09 | SPY's equity premium accrues in the close-to-open leg; the open-to-close leg contributes ~zero or negative. | ann(overnight) >> ann(intraday), intraday <= 0 | **DIRECTION RIGHT, NOT ESTABLISHED** — see H18 results below |
| H18b | 2026-08-09 | The same holds in the cross-section: an equal-weight book of the 120 names earns its premium overnight, and the pattern replicates in a large majority of individual names (a market-level result driven by 6 of 120 stocks is not the LPS mechanism). | EW overnight > intraday; >= 2/3 of names agree | **PERVASIVE, NOT SEPARABLE** — see H18 results below |
| H18c | 2026-08-09 | LPS's ACTUAL factor claim: classic 12-1 winner-minus-loser momentum earns its spread overnight and gives part of it back intraday (institutional momentum demand is expressed at the open). | WML overnight > 0 > WML intraday | **SIGN RIGHT, UNSTABLE** — see H18 results below |
| H18d | 2026-08-09 | The repo's OWN gated v4 composite book (long-only top quintile of the eligible pool) likewise earns its excess overnight. | book overnight > intraday | **TRUE, AND EMPTIED BY ITS OWN CONTROL** — see H18 results below |
| H18e | 2026-08-09 | **THE DECIDING ROW FOR H4.** On identical picks, a 42-session swing trade entered at close(t) beats the same trade entered at open(t+1), because the entry price forgone is exactly one overnight return, which the mechanism says is positive. Book size 2 (the shipped size). | mean(close-entry) - mean(open-entry) > 0, hit rate higher | **FAILURE CONDITION FIRES; H4 KEPT, RESTATED** — see H18 results below |
| H18f | 2026-08-09 | H18e at book size 5 (sensitivity, reported whatever it says). | same sign as H18e | **same sign, +6.18 bps** — see H18 results below |
| H18g | 2026-08-09 | An overnight-only strategy (buy the close, sell the open, every session) survives realistic costs. Registered as the expected-NEGATIVE row: it trades a full round trip every day, so break-even round-trip cost equals the mean daily overnight return in bps. | break-even >= 5 bps to be tradeable | **REJECTED, as expected** — break-even 3.88/5.05/5.39 bps; see H18 results below |

Diagnostics registered alongside (reported in full, not searched over):
price-only (`adjustment=split`) reruns of H18a/H18b to size how much of any
overnight premium is simply the dividend, which lands in the overnight leg by
construction; cost grid 0/5/10 bps round trip; both halves split at the median
date on every row.

### H22 — the first NON-price signals in this repo: net share issuance and gross profitability (registered 2026-08-09, BEFORE any run)

Mechanism, one sentence each (Rule 1):
(1) **Net share issuance** — Pontiff-Woodgate (2008), Daniel-Titman (2006):
managers issue equity when they believe the stock is overpriced and repurchase
when they believe it is underpriced, so the twelve-month change in shares
outstanding is a free quarterly read on the best-informed insider's valuation.
(2) **Gross profitability** — Novy-Marx (2013): gross profit over total assets
measures productive capacity at the point in the income statement least
contaminated by accounting discretion, so it sorts returns where bottom-line
earnings do not.

Why it matters HERE: every signal this repo has ever ranked on is a function of
past prices, and the gates lab established that the price composite sorts
nothing (decile 1 minus decile 10 = -0.099% at 5 td, -0.257% at 42 td). These
are the two strongest documented free NON-price signals, and until
`scout/sec_bulk.py` existed there was no point-in-time fundamental data here to
test them with.

Lab: `scout/fundamental_lab.py`. Universe = point-in-time S&P 500 membership
(`scout/pit.py`) 2016-2026, so each date ranks only that day's actual members
and delisted names stay in until their last print. **The shift:** signals are
built from facts whose SEC FILING date is <= t, quintile weights are formed at
close t, and every portfolio applies `wbar.shift(1) * ret1`, so the first
return any signal can touch is close(t) -> close(t+1).

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H22a | 2026-08-09 | Low net issuance (net repurchase) beats high net issuance: the quintile spread on -1 x the 12-month log change in split-adjusted shares outstanding is positive at a 42-session hold. | Q5-Q1 > 0 | **NOT PROVEN — right sign, every control passed, not enough independent windows.** +1.748 bps/day at h=42, CI **[-0.151, +3.720]**, NW t=1.81. Halves agree (+2.009/+1.488); monotone in horizon (+1.631/+1.748/+1.819 at 21/42/126); Rule 13 clean (beta **-0.001**, alpha 4.42%/yr); clears the PLACEBO null (-0.050±0.643, **z=2.80**); break-even **267 bps** round trip vs 10 charged; Q5/Q1/pool = 17.21/12.81/14.36%/yr. But on the honest effective sample — **56 non-overlapping 42-session windows** — it is +0.685%/window at **t=1.59**, positive in 57%. Bar is t>3. **DSR=0.470** at N=14. Not rejected; under-powered. |
| H22b | 2026-08-09 | High gross profit / total assets beats low: the quintile spread on GP/AT is positive at a 42-session hold. | Q5-Q1 > 0 | **REJECTED — wrong sign and the halves flip.** -0.412 bps/day at h=42 (registered direction was positive), CI [-3.079, +2.099], NW t=-0.30; halves **+0.984 / -1.807**. Sits inside the placebo null (z=-0.40, p=0.67); 62 non-overlapping windows give t=-0.34 and a 41.9% win rate; Q5 12.59% vs pool 14.76%/yr — the high-GP/AT quintile UNDERPERFORMED the pool it was drawn from. Break-even cost is negative. Fails its own pre-registered sign-flip condition. |
| H22c | 2026-08-09 | **THE DECIDING ROW.** Both signals are INDEPENDENT of the repo's existing price composite: the cross-sectional rank correlation to 12-1 momentum and to the gated v5 composite score is small, and the fundamental spread survives inside every momentum tercile. A signal that re-expresses momentum adds nothing to a momentum engine no matter how well it sorts on its own. | \|rho\| < 0.2 AND spread > 0 in all 3 momentum terciles | **CONFIRMED for net repurchase, and it is the one durable result of the round — but read the second half.** Spearman to raw 12-1 momentum: **-0.015** (net repurchase, sd 0.095) and +0.047 (GP/AT); to the **GATED v5 composite** computed with `signals.composite_at` exactly as the scan computes it: **+0.010** and +0.042, over 113/115 monthly dates. An order of magnitude inside the 0.2 threshold — the first signal in this repo that is not a function of past prices. The double sort passes the letter of the test (net-repurchase spread **+94.4 / +88.2 / +13.0** bps in momentum terciles T1/T2/T3, positive in all three) and fails its spirit: the effect is **gone in the top momentum tercile**, which is exactly where the v5 gates (SMA200, positive 6-month return, lottery vetoes) confine the engine. Orthogonal and inaccessible at once. GP/AT and the combo do not even pass the letter (+6.4/+67.2/**-50.8** and +27.8/+108.7/**-59.1**). |
| H22d | 2026-08-09 | The two signals combine: an equal-weight average of the two cross-sectional ranks spreads wider than either alone (they proxy different frictions, so their errors are weakly correlated). | combined spread >= max(single spreads) | **REJECTED.** Combined +1.272 bps/day at h=42 against net repurchase alone at **+1.748** — the combination is WORSE than its better leg, which is what averaging a live signal with a dead one does. Halves flip (+3.328 / -0.782), CI [-1.122, +3.677], and it costs coverage: the intersection where both signals exist is 206.9 names/date against 345.2 for net repurchase alone. |
| H22e | 2026-08-09 | The long-only top quintile — the only form this repo could actually trade — beats SPY on Sharpe after 10 bps round trip. | Sharpe(Q5 net) > Sharpe(SPY) | **REJECTED, as pre-registered — and the failure is instructive.** Net-repurchase Q5 after 10 bps: **17.12%/yr at Sharpe 0.819** against **SPY 15.82%/yr at Sharpe 0.884**. It BEATS SPY on return by 1.30pp/yr and still loses on Sharpe, because an equal-weight 69-name book carries more volatility than the cap-weighted index — the same shape ALPHA-STACK.md found. GP/AT Q5 12.56% (Sharpe 0.648) and combo 16.64% (Sharpe 0.839) also lose. Excess over the matched equal-weight pool is only +1.098 bps/day, so most of Q5's 17.12% is "S&P 500 names went up", not selection. |
| H22f | 2026-08-09 | ROBUSTNESS, registered ex ante so it cannot be used as a rescue: the GP/AT result holds on the subset of names that tag `GrossProfit` directly, without the Revenue-minus-COGS derivation. | same sign, similar magnitude | **PASSES — and it exonerates the derivation, not the signal.** Restricting to the 237 tickers that tag `GrossProfit` directly gives -0.306 bps/day at h=42 against -0.412 for the full panel: same sign, same magnitude, same null (halves +1.705 / -2.316). So H22b did not die of the Revenue-minus-COGS reconstruction; GP/AT simply does not sort this cohort. Coverage cost of the restriction is severe — 158.7 names/date (31.9% of members) against 250.7 (50.4%). |
| H22g | 2026-08-09 | RULE 9 COMPLIANCE: a 21-td ("monthly") rebalance gives the same answer as the phase-pooled daily-formation estimator, and the spread across the 21 possible entry phases is small relative to the effect. | phase spread << effect | **CONFIRMED.** All 21 monthly entry phases for net repurchase: mean **+1.756** bps, sd **0.049**, min +1.655, max +1.846, against the phase-pooled daily-formation estimator's +1.748. Phase choice is worth **2.8%** of the effect, and turnover is identical (0.0132 vs 0.0131x/day). GP/AT likewise (mean -0.412, sd 0.058). Unlike H7a — where the repo had been quoting the luckiest of six schedules — a slow quarterly signal genuinely does not care when you start. |

Sensitivity reported for H22a/H22b whatever it says: holds of 21, 42 and 126
sessions (fundamental signals are slow; 42 is this repo's horizon and is the
registered headline, the other two are context, not a search).

Controls (nulls, not trials): (i) RANDOM-PICK quintiles from the identical
eligible pool, 200 draws — the control that separates "buyback stocks went up"
from "S&P 500 stocks went up"; (ii) PLACEBO, each symbol permanently assigned
another symbol's whole signal series so every series keeps its own persistence
and only the pairing breaks, 200 draws — Finding 2 of H16 established this is
the only honest null for a persistent signal; (iii) within-date SHUFFLE, 200
draws, reported WITH the SE-ratio Rule 14 requires so its anti-conservatism is
visible; (iv) matched benchmarks — equal weight of the eligible pool, and SPY;
(v) Rule 13 — every dollar-neutral book regressed on SPY before its sign is
quoted.

Method: quintiles, equal weight, 42-session overlapping cohorts, 10 bps round
trip charged on measured turnover, break-even round-trip cost reported. Both
halves split at the median date. Moving-block bootstrap by date with block =
holding period (the cluster-by-date bootstrap this repo uses in
`scout/calibrate.py`, plus the block that overlapping holds require).

Data debt handled explicitly: 5.1% of splits are unapplied in Alpaca daily bars.
This lab repairs them from Alpaca's OWN corporate-actions feed AND masks any
residual \|1-day return\| > 45%, and prints the count of each.

Failure conditions, stated in advance: H22a/H22b fail if the spread's sign
flips across halves, or if it sits inside the placebo null, or if the
break-even round-trip cost is under 10 bps; **H22c fails — and takes the
practical case for the whole hypothesis with it — if the rank correlation to
momentum exceeds 0.2 in magnitude or the spread disappears inside momentum
terciles**, because this repo already owns the momentum; H22d fails if the
combination does not beat the better single signal; H22f fails if the derived-GP
and real-GP subsets disagree in sign.

Coverage is the binding constraint and is reported before any return number:
of 742 point-in-time members since 2016, 729 have Alpaca bars and only 593 map
to a CIK in the SEC's ticker file at all (that file maps CIK to the CURRENT
ticker, so acquired and renamed companies silently vanish — a survivorship leak
in the FUNDAMENTAL data even though the price universe is point-in-time).
`GrossProfit` is tagged by 237 of them; the rest need the Revenue-minus-COGS
derivation, and financials do not report a gross profit at all.

### H22 results (2026-08-09) — one signal survives its controls and dies of sample size; the other is simply dead

Ran on 2,664 sessions, 2016-01-04 .. 2026-08-07, mean 496.9 point-in-time
members and 490.0 eligible names per date. `python -m scout.fundamental_lab`,
875s warm; 25/25 offline selftests pass, including the lookahead proof
(unshifted same-day signal earns +416 bps, shifted +(-0.19) bps).

**Coverage is the binding constraint and it is worse for profitability than for
issuance.** Net issuance is present on **345.2 names/date (69.4% of members)**;
GP/AT on **250.7 (50.4%)**; GP/AT restricted to direct `GrossProfit` taggers on
**158.7 (31.9%)**; the two-signal intersection on **206.9 (41.6%)**. Of 742
point-in-time members only **593 map to a CIK at all** in the SEC's ticker
file, which maps CIK to the CURRENT ticker — so acquired and renamed companies
vanish. **The price universe is point-in-time; the fundamental universe is
not.** That is a survivorship leak in the fundamental layer, it biases toward
survivors, and no amount of `pit.py` fixes it.

**The one durable result is H22c, and it is a negative for the engine even
though it is a positive for the signal.** Net repurchase correlates **-0.015**
with 12-1 momentum and **+0.010** with the gated v5 composite. This repo has
never had a signal that was not a function of past prices, and now it does. But
the double sort says the spread is **+94.4 / +88.2 / +13.0** bps across
momentum terciles T1/T2/T3: the information lives where momentum is weak and
evaporates where momentum is strong. The v5 gates (SMA200, positive 6-month
return, vol and lottery vetoes) exist precisely to keep the engine in T3. **The
signal is orthogonal to the engine and inaccessible to it for the same reason.**

**Method note that outranks the verdict — a daily `n_eff` can exceed `n_days`.**
The lab's own `_n_eff`, computed from the daily long-short series, reports
**3,220 effective observations at h=42 against 2,664 days**. That is not a bug:
a long-short book's DAILY returns are near-serially-uncorrelated even when its
POSITIONS turn over quarterly, so the daily series looks independent while the
bets are not. The honest count is non-overlapping windows — **56** of them —
and on those the headline is **+0.685% per window at t = 1.587**, positive in
57.1%. The daily statistic flattered the sample by roughly **50x**.
`nonoverlap_blocks` had been written for exactly this and was never called; it
is now wired into `report()`. **Rule 16 for the house: never quote an n_eff
computed from a daily series for a signal whose positions turn over slowly —
quote non-overlapping windows, and if n_eff > n_days, that IS the bug report.**

**Rule 14 fires again, hardest yet.** The within-date SHUFFLE and RANDOM nulls
are **12.1x and 11.0x TIGHTER** than the Newey-West SE of the real series, and
both return p = 0.000. Quoting them would have "confirmed" a t = 1.59 result at
three decimals. The PLACEBO null — each symbol keeps its own signal series,
only the pairing breaks — is 1.51x, and it is the only one worth reading. It
does clear (z = 2.80), which is why H22a is "not proven" rather than rejected.

**Data debt, handled with BOTH guards.** Alpaca's own corporate-actions feed
repaired **3 unapplied splits** — AAPL 2020-08-31 (4:1, 1,173 bars rescaled,
the exact -74.2% fake in BACKTEST-REPORT.md) and ROL twice (1.5:1 in 2018 and
2020) — **13 further events were ambiguous** and left to the mask, and **138
cells with |1-day return| > 45%** were removed from eligibility AND P&L.

**A new item of data debt, specific to SEC share counts: UNIT SWITCHES.**
Filers change scale between filings and the SEC bulk data preserves it. MCD's
diluted share count goes 7.413e8 (2023-02) then 732.3 (2024-02); COP 1.246e6
(2016) then 1.278e9 (2023); GRMN alternates 1.9e5 and 1.9e8 every year because
the 10-K reports thousands and the 10-Qs report units. Untreated, MCD reads as
a 99.9999% buyback and lands in the extreme quintile of every sort.
`sec_bulk._despike` cannot catch these — a permanent scale change looks like a
corporate event and an alternating one has no agreeing neighbours.
`fundamental_lab.normalize_share_units` divides each observation by 10^(3k)
where k is its log10 distance from the ticker's own median scale, rounded to a
multiple of 3, which cannot fire below a ~31x deviation and so cannot erase a
real issuance. It rescaled **4,538 daily cells over 18 tickers**; a further
**2,795 cells** with |12m log share change| > 1 were dropped as residual
filing artefacts. Any future study using SEC share counts must do this.

**What would change the verdict.** Not more variants — more independent
windows, or a cohort where the effect is not confined to weak-momentum names.
Net issuance is the best non-price candidate this repo has found; at 56
independent windows it cannot be confirmed here, and pretending otherwise is
how the two retracted headlines happened.

Controls (nulls, not trials): (i) within-date LEG-LABEL permutation — a
sign-flip randomisation of the overnight-minus-intraday difference, 10,000
draws, with the SE-ratio print Rule 14 requires; (ii) moving-block bootstrap
by date; (iii) for H18e/H18f a RANDOM-PICK control drawing the same number of
names from the identical eligible pool (200 draws), which is what separates
"momentum picks gap up at the open" from "the whole market drifts up
overnight"; (iv) matched benchmarks — buy-and-hold close-to-close, and SPY.

Failure conditions, stated in advance: H18a/H18b fail if the gap is inside the
permutation null or flips sign across halves; H18c fails if the intraday leg
of WML is not negative; **H18e fails — and takes the shipped H4 rule with it —
if the close-entry advantage is not positive in both halves, or if it is
statistically indistinguishable from the random-pick control** (in which case
H4 is a market-wide drift statement, not a rule about picks); H18g fails if
break-even round-trip cost is under 5 bps.

### H18 results (2026-08-09, real data — `scout/overnight_lab.py`)

Ran on 2,664 sessions of Alpaca SIP daily bars, 2016-01-04..2026-08-07, the
121-ticker point-in-time panel, 280,106 eligible symbol-sessions. Registered
above BEFORE the run; statuses filled in after. **Nothing new shipped. H4
survives as a rule and loses its rationale.** Data integrity, printed by the
lab: 1 unapplied split repaired (AAPL 2020-08-31, a fabricated **-74.2%
OVERNIGHT** return — this study is the one where that defect would have been
fatal, since the entire error lands in the leg being measured), 1 ambiguous
event left alone (MET), 1 extreme leg blanked (OXY 2020-03-09, a REAL -52%
day; switching the guard off moves the EW-120 overnight mean by 0.011 bps),
identity residual 2.2e-16.

| # | verdict |
|---|---|
| H18a SPY | **DIRECTION RIGHT, EFFECT NOT ESTABLISHED.** Overnight +9.54%/yr (Sharpe 0.86) vs intraday +5.97%/yr (0.50), buy-and-hold +16.08% (0.94). The famous form has intraday at or below zero; here it is solidly positive. Gap +1.22 bps/session at permutation p = 0.56, block-bootstrap CI [-3.46, +5.41]. The registered failure condition ("inside the permutation null") FIRES. |
| H18b cross-section | **PERVASIVE, NOT SEPARABLE.** EW-120 book: overnight +12.73%/yr (Sharpe 1.06) vs intraday +4.44%/yr (0.39); overnight wins in **83 of 114 names (73%)**, clearing the pre-registered 2/3 bar. The market-level gap is still inside its null (p = 0.17, CI [-1.15, +6.87]) — broad enough to be nearly everywhere, small enough to be unprovable at n = 2,643. Decays as McLean-Pontiff predicts: +17.4/+2.3 %/yr in half 1, +8.3/+6.7 in half 2. |
| H18c WML 12-1 | **SIGN AS PREDICTED, STABILITY NOT.** Overnight +4.88%/yr, intraday -5.20%/yr — LPS's sign exactly, so the registered failure condition does not fire. But the overnight leg flips sign across halves (-5.4 then +16.3 %/yr) at p = 0.24, and the spread is a difference of two large POSITIVE overnight returns (winners +8.25 bps/session, losers +5.89). Everything is paid overnight; winners marginally more. |
| H18d the repo's book | **TRUE AS WRITTEN, EMPTY AS A CLAIM ABOUT THE BOOK.** Gated top-quintile composite: overnight +14.00%/yr vs intraday -3.58%/yr, gap +6.41 bps, p = 0.007, **z = +3.03 — the only row this round that reaches the t>3 bar.** Then the control added because the number looked good: the ELIGIBLE POOL earns +12.38%/yr overnight and +0.97% intraday by itself. Q5-minus-pool = +1.43%/yr overnight, sign-flipped across halves (+3.06 then -0.18), p = 0.06, on an excess book that loses 3.04%/yr. Not a churn artifact either (monthly rebalance +15.01 vs -3.14 %/yr; churn 17.5%/session -> 2.3%). |
| **H18e (book 2) — THE H4 ROW** | **THE RULE SURVIVES, ITS RATIONALE DOES NOT.** Close(t) entry beats open(t+1) entry by **+5.29 bps/window** (95% CI [+0.39, +10.73], NW t = +2.07, positive in BOTH halves +7.87/+2.72); hit rate 64.24% vs 63.81% (+0.43pp). Costs cancel exactly — identical turnover, identical exit — so that is a NET number. But the random-pick control drawing 2 names from the identical pool on the identical dates earns **+4.51 bps [p5 +2.45, p95 +6.79]**, and +5.29 sits inside it; the picks' first-night gap is +5.13 bps against the pool's +4.45 and SPY's +4.51, an edge of +0.68 bps (CI [-2.68, +4.27], t = 0.44). **The registered failure condition "indistinguishable from the random-pick control" FIRES.** H4 is therefore a market-wide-drift statement, exactly as the row warned. |
| H18f (book 5) | Same sign, slightly larger: +6.18 bps/window (CI [+2.18, +10.01], NW t = +3.04, halves +9.12/+3.24), hit +0.38pp, pick-minus-pool edge +1.68 bps (CI [-0.42, +3.95]). Its +6.18 clears the control's p95 (+5.98) by a whisker. Reported as the sensitivity row it was registered as, not as a rescue of H18e. |
| H18g overnight-only | **REJECTED.** Break-even round-trip cost 3.88 bps (SPY), 5.05 (EW-120), 5.39 (composite Q5) against a 5-10 bps band. SPY fails the 5 bps bar outright; the two books scrape past its letter and fail its substance — at 5 bps they return -3.43% / -0.61% / +0.51% a year against buy-and-hold's +16.08% / +17.67% / +9.81%. Best book: gross Sharpe 1.39, net 0.10, **deflated Sharpe 0.140** at N=7. Agrees with `scout/intraday.py`'s independent 2018-2026 minute-bar run (break-even 4.20 bps). |

**Consequence for the shipped H4 banner.** Keep the rule: it is free, its sign
is right in both halves and at both book sizes, and the CI on the raw
advantage excludes zero. Restate what it is: worth about **+5 bps per
42-session window (~+0.3%/yr at six windows a year)**, and it is the market's
overnight drift rather than anything about the picks.
`RESEARCH-AGENDA.md` item 4 claims "+0.5-1%/yr" for this rule — that
overstates the measurable half by 2-3x. The other half of H4 ("never chase
opening gaps", i.e. the opening auction's wider spread) is **still untested**
and probably the larger half; bars carry no quotes, so it needs a
quote/TAQ-grade source this repo does not have.

**Rule 15 for the house: a leg (or window, or bucket) decomposition of a BOOK
is not a statement about the book until the pool it was drawn from has been
subtracted.** H18d passed the t>3 bar and meant nothing, because the eligible
universe carried 4.77 of its 5.39 bps/session overnight. This is the same
error family as Rule 13 (regress dollar-neutral books on the benchmark before
quoting their sign) and it cost nothing to catch, because the control is one
extra line: `ew_leg(pool, leg)`.

Code note stamped on this round: `DataFrame.shift` on a BOOLEAN frame upcasts
to object, and `~` on an object frame calls Python's int-valued `~True == -2`,
which is truthy — so `sel & ~sel.shift(1)` reports 100% turnover for a book
that never changes. It did, until the self-test caught it. `_prev()` exists
for that reason and every boolean shift in the lab goes through it.

Trial count: N rises by **10** (H18a-H18g registered = 7, plus 3 post-hoc
diagnostics: pool-relative legs, monthly rebalance, extreme-guard sensitivity).
Control draws (10,000 permutations, 2,000 block-bootstrap resamples, 200
random-pick draws) are nulls and do not count.

### H21 — short-horizon reversal as a LIQUIDITY premium, conditioned on news (registered 2026-08-09, BEFORE any run)

Mechanism (Campbell-Grossman-Wang 1993; Nagel RFS 2012 "Evaporating
Liquidity"; Da-Liu-Schaumburg RFS 2014): a one-week price move produced by
uninformed liquidity DEMAND must be paid for, so it reverses — the reversal
return IS the fee earned by whoever absorbed the order flow; a move produced
by INFORMATION does not reverse, because it is the new price. The same raw
signal therefore has opposite economics depending on its cause, and the
cached news panel is a direct proxy for that cause.

**Why this row exists: the repo has tested momentum four times and measured it
sorting nothing (decile 1 minus decile 10 = -0.26% at 42 td). Short-horizon
REVERSAL is the opposite sign at the opposite horizon and has never been
tested here once.** H15/H16 rejected news-based SIGNALS; H21 uses news only as
a CONDITIONER on a price signal, which is a different claim.

Lab: `scout/reversal_lab.py`. Universe = the same 120 point-in-time-liquid
S&P 500 members as of 2016-01-04 that the news labs use (scout/pit.py, no
post-2016 additions), 2016-01..2026-08, split-repaired daily SIP closes.

**The shift:** `sig(t) = close.shift(1) / close.shift(6) - 1` — the 5-session
return ending at close(t-1), so session t itself is SKIPPED (a one-day gap
kills bid-ask bounce, the classic fake reversal). The book is formed at
close(t) and earns `fwd_h(t) = close.shift(-h) / close - 1`. Signal and return
share index t and touch disjoint price ranges: the signal reads closes at t-6
and t-1, the return reads closes at t and t+h. Registered direction: LONG the
bottom quintile (losers), SHORT the top quintile (winners); spread = Q1 - Q5,
positive means reversal.

**News conditioning:** specific stories (news_data.is_templated /
is_broadtape drop machine wire copy and >10-tag broadtape) attributed to
sessions t-5..t-1 — the same five sessions the formation return spans, all
readable before close t under news_data's 16:00-ET rule.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H21a | 2026-08-09 | Unconditional short-horizon reversal exists in this large-cap panel: the bottom quintile of the skip-a-day 5-session return beats the top quintile over the next 5 sessions. | Q1 - Q5 > 0 at h=5 | **REJECTED — RIGHT SIGN, NO SIZE, AND IT IS BETA.** Losers minus winners earns **+1.44 / +6.95 / -0.41 / +19.64 bps** at h = 1 / 5 / 10 / 21, block-bootstrap t = +0.54 / +0.69 / -0.03 / +0.94; the h=5 CI is [-12.32, +26.70] on 2,599 dates. Both halves agree at h=5 (+7.31 / +6.59) so the sign is stable, but Rule 13 removes it entirely: the dollar-neutral book runs **beta +0.29 / +0.33 / +0.24 / +0.15** to SPY (a stock that just fell five days is temporarily the high-beta one), and market-adjusted alpha is **-3.35 bps at h=5 (t=-0.35)** and -15.30 at h=10. The whole gross spread is the beta. |
| H21b | 2026-08-09 | **THE DECIDING ROW.** Reversal is a liquidity premium, so it is STRONG among stocks with NO specific news in the formation week and WEAK OR ABSENT among stocks that had news. | spread(no-news) - spread(news) > 0, CI on the DIFFERENCE excluding zero | **REJECTED — ON BOTH PRE-REGISTERED FAILURE CONDITIONS.** On the 1,488 common dates the quiet leg earns +9.70 bps and the news leg -2.00: the DIFFERENCE is **+11.69 bps [-12.71, +36.08], t = +0.94**. (i) The halves are **-10.23 then +33.61** — a sign flip, which this house calls noise and says so. (ii) The difference sits INSIDE the news-label-shuffle null (null +0.55 ± 7.61, 94th percentile, **p = 0.12**). At h=1 the difference is **-6.29 bps, the WRONG sign in both halves** (-6.62 / -5.97, t=-1.60). The registered sign is right at h=5/10/21 and wrong at h=1, and no horizon is distinguishable from zero. |
| H21c | 2026-08-09 | The same ordering appears monotonically across terciles of ABNORMAL news volume (log((k+1)/(median k over the prior 60 sessions +1))), because abnormal coverage is the sharper proxy for "the move was information". | spread falls monotonically from the low-attention to the high-attention tercile | **REJECTED — FLAT, AND NOT EVEN MONOTONE.** +8.58 / +3.03 / +8.37 bps across low/mid/high abnormal news: a U, not a slope. Low minus high is **+0.05 bps, t = +0.01**, on 2,566 dates. This is the cleanest rejection in the round because it has none of the coverage problems the binary split has — each tercile carries ~38 names a day. |
| H21d | 2026-08-09 | The LONG-ONLY leg (buy the losers, no shorts — the only practically tradeable form for this user) beats the equal-weight eligible pool, and does so more in the no-news group. | Q1 - pool > 0, larger for no-news | **NOT PROVEN — the only cell that clears costs, and it flips sign across halves.** Losers minus the matched equal-weight pool: all **+6.57 bps (t=1.24)**, quiet **+16.33 (t=2.04)**, news **+4.79 (t=0.89)** per 5-session hold. The quiet leg is the ONE book in the study that survives 10 bps (turnover 0.94, break-even 17.47 bps, net **+3.52%/yr** against SPY's ~+15.8%/yr over the same decade) — and its halves are **-1.14 then +33.79** (split 2020-07-23), and the sized random-subset null it must beat is +4.12 ± 4.12, not zero. Per the H1b house rule that is a new hypothesis needing fresh data, not a shippable result. |
| H21e | 2026-08-09 | Reversal profits classically concentrate in illiquid names, so restricting to the top-liquidity half of the panel should SHRINK the spread; registered as the expected-NEGATIVE row that decides tradeability. | spread(top-liquidity half) < spread(all), possibly to zero | **PREMISE NOT CONFIRMED, AND THE ONE BIG NUMBER IS A COVERAGE ARTEFACT.** Unconditional reversal is if anything LARGER in liquid names: +10.61 (top half) / +10.34 (ex bottom tercile) / +6.95 (all) / +5.77 (bottom tercile), none with \|t\| > 1.2 — but every name here is a top-500 US large cap, so this is not evidence against the down-cap literature. The top-liquidity half's quiet-minus-news difference reads **+71.19 bps, t = 2.54, p = 0.000 against its own null** — the only \|t\| > 2 in the file — and it is measured on **159 dates = 31 independent weekly windows**, because the quiet group inside the 50 most liquid names has only 2.55 members in the loser cell. **158 of those 159 dates fall in 2016-2021 and none in 2024-2025**, so both "halves" of that series sit inside the first six years. Relaxing MIN_CELL to 1 halves it to +39.75 on 910 dates. This is H7a's shape exactly: a real-looking number that is one slice of the calendar. NOT quoted as a result. |
| H21f | 2026-08-09 | Costs decide it at weekly rebalancing: the break-even round-trip cost must clear the 10 bps charged for large caps. | break-even >= 10 bps | **FAILED for every long/short book.** Break-even round-trip cost **4.44 bps (all names), 5.18 (quiet), 2.98 (news)** against 10 charged, on measured turnover of 1.57-1.87x gross per rebalance — the book loses 4.4-5.7%/yr net. Long-only pays one leg instead of two: **8.45 (all) / 17.47 (quiet) / 5.96 (news)**. Only long-only-quiet clears, and that is the H21d cell with the sign flip. No borrow cost, no impact and no shorting constraint are modelled; all three push the same way. |

Registered variants, all reported whatever they say (16 total): unconditional
Q1-Q5 at h = 1/5/10/21 (4); news-conditioned with COMMON breakpoints at
h = 5 (primary) and 1/10/21 (4); news-conditioned with WITHIN-GROUP terciles
at h=5 (1); abnormal-news terciles at h=5 (1); long-only at h=5 (1);
liquidity top-half and ex-bottom-tercile (2); the NO-SKIP signal that shows
what the one-day gap is worth (1); news counted over t-5..t instead of
t-5..t-1 (1); and the extreme-print-filtered rerun (1).

Controls (nulls, not trials): (i) RANDOM-PICK — quintile labels permuted
inside each session over the identical eligible pool, 200 draws, mean AND SD
quoted (Rule 10); (ii) DATE-SHUFFLE of the signal — each symbol's formation
return permuted across dates, 200 draws; unlike H15 this control must NOT kill
the effect, because reversal is a timing claim by construction, so it
discriminates rather than merely nulls; (iii) NEWS-LABEL SHUFFLE — the
news/no-news assignment permuted across symbols within each date preserving
group sizes, 200 draws: this is the null for the DIFFERENCE, and it is what
decides H21b; (iv) MATCHED BENCHMARKS — the equal-weight eligible pool and
SPY. Every permutation p-value is printed next to the ratio of the null's SD
to the real series' block-bootstrap SE (Rule 14). Rule 13 is honoured: the
dollar-neutral book is regressed on SPY before its sign is quoted.

Data hygiene stated in advance (the repo's known 5.1% unadjusted-split debt):
closes are the SPLIT-REPAIRED series built by `news_attention_lab.load_close`
(the AAPL 2020-08-31 4:1 repair among them), PLUS a stale-quote retirement
rule — a symbol is dropped permanently from its first run of >=10 identical
consecutive closes, which is how a delisted ticker's frozen quote and a
reused-ticker splice present. Every remaining |1-day return| > 45% is
enumerated individually with a verdict, and the whole study is rerun with
those windows excluded.

Failure conditions, stated in advance: H21a fails if the unconditional spread
is inside the random-pick null or flips sign across halves; **H21b fails — and
takes H21 with it — if the no-news-minus-news difference is inside the
news-label-shuffle null, or if it flips sign across halves**; H21c fails if
the ordering is not monotone; H21f fails, and makes the whole thing
untradeable regardless of sign, if the break-even round-trip cost is under
10 bps.

### H17 — novel news drifts, stale (recycled) news reverses (registered 2026-08-09; statuses filled in after the run)

Mechanism (Tetlock 2011, "All the News That's Fit to Reprint"): investors
cannot cheaply tell a genuinely new fact from the fifth retelling of an old
one, so they UNDERREACT to novel information (its price move continues) and
OVERREACT to recycled information (its move unwinds). The theory therefore
predicts OPPOSITE SIGNS for two things a headline count cannot distinguish,
which is what makes it survivable after H15 and H16: the date-shuffle control
that killed H15 destroyed a static property of WHICH STOCKS get covered, and a
static property cannot flip sign with the direction of the news day.

Lab: `scout/news_novelty_lab.py` over the cached Benzinga panel (120
point-in-time-liquid S&P 500 names as of 2016-01-04, 2016-2026, 308,870
stories, 464,430 symbol-rows). Prices are split-REPAIRED (AAPL 2020-08-31, 1,173
bars) AND guarded by an explicit |1-day return| > 45% filter — which finds
exactly 2 residual cells, OXY 2020-03-09 (a real -52% oil-crash day) and
MON 2021-03-16 (delisted ticker reused) — plus a $20M 21-session median dollar
volume floor computed through t.

Signal: `max_prior_similarity` returns the CONTINUOUS quantity
`news_data.novelty_flags` thresholds — each story's maximum Jaccard overlap with
the same symbol's stories over the prior 5 days — and the lab asserts
`(sim < thr) == novelty_flags(df, 5, thr)` exactly at every threshold on the
real panel. Session signal = mean similarity over that session's SPECIFIC
stories, ranked within date, cut into terciles. **The shift:** every regressor
is known at close(t) (news readable before close t; r0 = close(t)/close(t-1)-1)
and `fwd_h(t) = close(t+h)/close(t) - 1`; the portfolio form is
`W.shift(1) * ret1` through `news_sentiment_lab.run_portfolio`.

The headline statistic is a DIFFERENCE-IN-DIFFERENCES, chosen so that any
constant bias in the novelty detector cancels:
`DiD = [novel - stale | up day] - [novel - stale | down day]`, registered
POSITIVE.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H17a | 2026-08-09 | Conditional on the news-day move, novel coverage drifts and stale coverage reverses, so the novel-minus-stale spread is positive on up days and negative on down days. | DiD > 0 at h=1/5/21/42 | **REJECTED — WRONG SIGN AND INSIDE THE NOISE.** DiD = **-0.83 / -3.91 / -5.62 / +3.85 bps** at h = 1/5/21/42, t = -0.24/-0.55/-0.37/+0.17, every 95% block-bootstrap CI straddling zero ([-7.60,+6.16] at h=1; [-35.29,+24.53] at h=21). Halves flip sign at three of four horizons. Across 3 staleness measures x 4 horizons only 6 of 12 cells carry the registered sign; the best (spec_max h=42, +14.95 bps) has t=0.69. n = 1,765-1,812 dates. |
| H17b | 2026-08-09 | The same claim as a dollar-neutral book (long novel-up + stale-down, short stale-up + novel-down) survives 10 bps round trip. | break-even >= 10 bps | **REJECTED.** Gross **-2.04 / +0.75 / +0.11 / +0.31 %/yr** against the matched equal-weight pool at +16.8 to +17.9%/yr and SPY at +15.82%/yr. Break-even round-trip cost **-0.48 / 0.88 / 0.52 / 3.08 bps** against 10 charged; net -44.1 / -7.7 / -1.9 / -0.7 %/yr. Unlike H16's tone book this one IS market-neutral (beta +0.025/+0.034/+0.007/-0.002), so there is no beta artifact to strip — there is simply nothing. |
| H17c | 2026-08-09 | **THE DECIDING ROW.** In a Fama-MacBeth cross-sectional regression of forward return on same-day-return rank, staleness rank and their INTERACTION, the interaction is negative: a move made on recycled news reverses relative to one made on novel news. | lambda(r0 x stale) < 0, t < -3 | **REJECTED — SIGN FLIPPED, THEN ABSORBED BY ATTENTION.** lambda(r0 x stale) = **+7.32 / +20.94 / +47.37 / +37.00 bps** (t = +1.02/+1.35/+1.42/+0.77): in this sample stale moves continue marginally MORE. Adding attention and attention x return removes 54% / 32% / 85% / 131% of it (|t| <= 0.79). The staleness LEVEL behaves the same: +58.5 (t=1.91) at h=42 alone, +19.0 (t=0.88) with attention in. Staleness-by-repetition is 0.45 rank-correlated with story count. And there is no reversal for a news effect to hide behind: lambda(r0) alone is +0.18/-7.70/-9.54/-2.50 with \|t\| <= 1.10, reproducing H16c. |
| H17d | 2026-08-09 | The literal `is_novel` split (NOVEL-heavy = every specific story novel; STALE-heavy = at least one repeat) shows the same sign at every Jaccard threshold in {0.4, 0.5, 0.6, 0.7, 0.8}. | same sign at all five | **REJECTED — THE TEXTBOOK ONE-THRESHOLD FAILURE.** At h=42 the DiD runs **-14.34 / -67.54 / +10.54 / +274.45 / +595.08 bps** while usable dates collapse 724 -> 16. Exactly one of the 20 binary cells has a CI excluding zero (thr=0.5, h=42, -67.54, t=-2.18) and it is the WRONG sign with neighbours -14.34 and +10.54. Measured reason the binary flag cannot carry this test: at the shipped 0.6 cut only **2.5%** of covered symbol-sessions contain any stale story (22.2 novel names per date against 1.6), and staleness-by-count is mechanically attention — 1.1% of one-story sessions contain a repeat against 48.7% of >10-story sessions. |
| H17e | 2026-08-09 | Variant: staleness over ALL stories rather than firm-specific ones (templated wire is recycled coverage by construction). | same sign as H17a | **REJECTED** — +0.80 / -3.81 / -5.17 / +6.61 bps, \|t\| <= 0.56. |
| H17f | 2026-08-09 | Variant: MAX rather than MEAN similarity per session (one reprint is enough to make the day stale). | same sign as H17a | **NOT REJECTED ON SIGN, REJECTED ON EVERYTHING ELSE** — the only measure positive at all four horizons (+0.65 / +8.30 / +13.41 / +14.95 bps) and the best cell in the study, but max t = 1.14, both halves disagree in sign at h=5 and h=21, and it is inside every null. |
| H17g | 2026-08-09 | The effect concentrates where the news actually moved the price (\|same-day return\| > 2%). | DiD larger than H17a | **UNTESTABLE ON THIS PANEL — reported as such.** Requiring 3 names in each of four cells among big movers leaves **19-21 usable dates** in ten years. Numbers are printed (+11.72 / -1.03 / -122.94 / -46.83) and mean nothing. |

Controls (nulls, not trials): (i) LABEL SHUFFLE — staleness permuted across the
covered symbols within each date, 200 draws, the one that must kill it;
(ii) DATE SHUFFLE — H15's killer applied to this spread, each symbol's
staleness series permuted across dates, 200 draws; (iii) RANDOM PICK from the
identical pool, 200 draws; (iv) MATCHED BENCHMARK — the equal-weight
eligible-with-news pool plus a SPY regression (Rule 13); (v) POSITIVE CONTROL.
**The real DiD is inside all three nulls at every horizon: |z| <= 0.61,
one-sided p 0.30-0.68.** The date-shuffle null MEAN is -1.44 / -1.86 / -2.85 /
-10.34 bps, so a static stock-characteristic component of this DiD exists and at
h=42 is nearly three times the real effect — H15's confound survives into the
differenced statistic, it simply has nothing left to explain.

Positive control (what IS there): novel tercile vs stale tercile — 1.41 vs 4.37
stories per session, |same-day return| 1.291% vs 1.807%, |next-session return|
1.315% vs 1.530%, signed next-session return +6.94 vs +7.82 bps. That is H15's
finding reached through a different measure: news intensity forecasts the SIZE
of the next move and almost none of its sign.

Robustness on the two free parameters, both reported whatever they said:
the novelty LOOK-BACK moves the h=21 DiD from -18.83 (3 days) to -5.62
(5, the default) to -32.13 bps (10 days, t=-2.10) — the most "significant" cell
in the study is anti-Tetlock, and a longer window making more coverage look
stale is what an attention proxy does. MIN_CELL is load-bearing too: at
MIN_CELL=1 (2,400 dates) the DiD is +0.54 / +0.50 / +0.26 / +7.00 bps.

**Two method results worth more than the rejection:**

- **Rule 15: difference two direction-conditioned spreads and the timestamp
  mistake mostly cancels — mostly.** Re-run under news_data's deliberately wrong
  attribution the primary DiD is +0.32 / -4.43 / -6.42 / -3.92 bps against the
  honest -0.83 / -3.91 / -5.62 / +3.85. The same error inflated H15's spread by
  43% and manufactured +8.74 bps/day in news_data's tone demo. Measured
  attenuation on planted synthetic leaks is 3.6x / 2.8x / 1.7x as the leak grows
  from 0.3% to 3% a day, so this is robustness and NOT immunity; the channel
  stays closed at the source.
- **Rule 14 gets its exonerating case.** H16 found within-date permutation
  nulls 2.3-3.5x too tight. Here SE_ratio (block-bootstrap SE / permutation SE)
  is 0.94-1.14 at every horizon for all three nulls. The difference is the
  statistic, not the data: a persistent long-short book inherits the
  autocorrelation of a sticky sector tilt; a DiD of four direction-conditioned
  cells differences that persistence away. Keep printing the ratio — this is the
  case where it clears the permutation.

Trial count: N rises by **36** registered (signal x horizon) cells — H17a/e/f
3 measures x 4 horizons = 12, H17d 5 thresholds x 4 = 20, H17g 4. Control draws
are nulls and do not count. Deflated Sharpe of the best book at N=36: **0.059**.

### H21 results (2026-08-09) — REJECTED, and two method notes worth more than the verdict

Ran on 2,664 sessions x 120 point-in-time-liquid S&P 500 names, 2016-01-04 ..
2026-08-07: 280,359 usable symbol-sessions, 272,653 eligible at h=5, 17.1% of
them with NO specific story in the formation week. Effective independent
sample: at most 2,664 dates (the cross-section is collapsed to one spread per
session first), ~532 non-overlapping weekly windows per entry phase with 5
phases — and the DIFFERENCE only 1,488 dates ≈ 297 windows.

**The rejection is not about power, and the controls prove it.** The lab's
offline selftest plants a quiet-group-only reversal and recovers it (+185.7
quiet vs -1.2 news), then kills it with the news-label shuffle (+1.7) and with
a ONE-SESSION misalignment of the conditioner (+6.9). The conditioner is alive
on real data too (news-week |return| 3.22% vs 2.67% quiet, next-session 1.36%
vs 1.29%). The machinery would have found the effect had it been there.

**The date-shuffle control BEHAVES here, which is the difference from H15.**
Permuting each symbol's formation return across dates takes the spread from
+6.95 to -2.73 ± 2.56 bps, so the little that is present is timing-attributable
rather than a stock characteristic. H15 died because its control reproduced the
effect; H21 dies because there is barely an effect to control for.

**Data note that is bigger than it looks — the frozen-quote defect.** Alpaca
keeps printing a delisted ticker at its last trade, and when a ticker is later
REUSED the splice manufactures an enormous one-day return. In this 120-name
panel EMC freezes at one price from 2016-09-06 and MON from 2018-06-06, then a
different company reuses MON on 2021-03-16 at 9.79 against the stale 127.95 —
a fabricated **-92.4%** day. Those two names alone account for 2,577 of the
panel's 4,288 exactly-zero one-day returns, and because a delisted name also
stops being written about, every one of those sessions is a permanent member of
the NO-NEWS group with a guaranteed-zero forward return — sitting on the exact
leg this study measures. `reversal_lab.retire_stale` drops a symbol from its
first run of >=10 identical consecutive closes. This is a NEW item of data debt
for BACKTEST-REPORT.md, distinct from the 5.1% unadjusted-split debt, and any
study in this repo that conditions on quiet/low-volatility behaviour should
apply the same rule. After it, the only remaining |1-day return| > 45% in the
panel is OXY 2020-03-09 at -52.0%, which is real; excluding its windows moves
the h=5 spread from +6.95 to +7.21 bps.

**Rule 14 fires hard, again.** The within-date permutation nulls are **4.2x and
3.9x TIGHTER** than the block-bootstrap SE of the real series, so their
p = 0.000 is an artefact of the null. Quoting them would have "confirmed" a
t = 0.69 result at three decimal places. The news-label-shuffle null, which
permutes group membership rather than price ranks, is only 1.6x tighter — and
it does not reject (p = 0.12).

**Two things that are worth keeping from a null round:**
- **The one-day skip is worth nothing in mega-caps.** No-skip earns +7.31 bps
  against skip-1's +6.95. Bid-ask bounce is not measurable at daily closes in
  120 of the most liquid US names, which is itself part of why the classic
  effect is absent — there is no microstructure noise left to reverse.
- **Rule 15 for the house: a conditioning variable whose group is thin creates
  a DATE-SELECTION problem, not just a noise problem.** Requiring 2 names in
  both extreme quintiles drops the quiet leg from 2,599 dates to 1,488, and in
  the top-liquidity half to 159 — of which 158 are 2016-2021. The resulting
  "both halves" test compares two slices of the same era and cannot see the
  problem. Always print the date coverage, the split date of each series, and
  the count at the relaxed threshold next to any conditional spread.

Scope of the rejection, stated as narrowly as it deserves: 120 large caps, one
publisher, no post-2016 index additions, and **Nagel's central conditioning —
that liquidity provision pays most when VIX is high and market makers are
constrained — was deliberately NOT run**, because adding it after seeing a null
would be hunting a variant. It is the registry row a future lab should open.

Trial count: N rises by **16** (4 unconditional horizons, 4 news-conditioned
horizons, within-group terciles, abnormal-news terciles, long-only, 2 liquidity
subsets plus the bottom tercile, no-skip, the t-5..t news window, the
extreme-print rerun). Controls are nulls and do not count; the MIN_CELL grid is
a coverage diagnostic reported in full. Best |t| anywhere in the file is 2.54,
in the cell measured on 31 independent windows.

### H15-H28 — Round 3: the untouched data (registered 2026-08-09 BEFORE any run)

Context: Rounds 1-2 tested only price-derived signals on daily closes. This
round opened Benzinga news (2015+), minute bars (2016+) and SEC bulk XBRL
fundamentals (23.4M facts, 12,246 companies) — none of which this repo had
ever used. Adapters: scout/news_data.py, scout/intraday.py, scout/sec_bulk.py.

Six have reported (H15, H16, H17, H18/H4, H20, H25). H19, H21-H24 and H26-H28
are in flight; rows will be completed as they land.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H15 | 2026-08-09 | Abnormal news volume is an attention shock; retail buying pressure on attention-grabbing stocks is not information, so it reverses (Barber-Odean, Da-Engelberg-Gao). | top-attention quintile underperforms | **REJECTED — killed by its own control.** Registered sign right in 16/16 cells, best \|t\| 2.92 against the t>3 bar. But the DATE-SHUFFLED panel reproduces nearly the whole spread (-0.57/-2.61/-10.61/-21.90 bps vs real -2.31/-3.42/-15.81/-23.56): destroying the timing barely dents it, so this is a static property of WHICH stocks get covered, not of WHEN. Positive control confirms the pipeline works — attention forecasts the SIZE of the next move (1.45% vs 1.32% absolute) and almost none of its sign. 32 variants. |
| H16 | 2026-08-09 | Media tone carries fundamental information incorporated with a lag because processing text is costly (Tetlock 2007). | positive tone -> positive drift | **REJECTED — wrong sign.** -2.186/-1.512/-1.268/-1.087 bps/day at h=1/5/21/42, NW t -0.99 to -1.46, every bootstrap CI straddles zero. 43.3%/yr of cost at h=1. **The pre-registered ALTERNATIVE was also wrong**: tone was expected to be short-term reversal in disguise, but the same-session return predicts nothing here either (t +0.19 to -0.76) and correlates with tone at only 0.117. Two dead things, dead independently. 18 variants. |
| H17 | 2026-08-09 | Investors underreact to genuinely NEW information and overreact to RECYCLED coverage, so novelty and staleness carry opposite signs (Tetlock 2011). | novel drifts, stale reverses | **REJECTED — inside every null.** DiD -0.83/-3.91/-5.62/+3.85 bps, all CIs straddle zero, and the real effect sits INSIDE all three permutation nulls at every horizon (\|z\| <= 0.61). Fama-MacBeth stale-x-return is POSITIVE (+7.32 to +47.37) where Tetlock predicts negative. Mechanical reason the binary flag cannot carry the test: at the shipped Jaccard 0.6, **96.5% of stories are novel**, so only 2.5% of covered sessions contain a stale story (22.2 novel names/date against 1.6). Independently reproduces H15's finding by a different measure. 24 variants. |
| H18 | 2026-08-09 | The equity premium accrues in the close-to-open leg while open-to-close contributes ~zero (Lou-Polk-Skouras 2019). | overnight >> intraday, intraday <= 0 | **REJECTED AS A STRATEGY; direction replicates.** SPY overnight +9.54%/yr (Sharpe 0.86) vs intraday +5.97% (0.50) vs buy-and-hold +16.08% (0.94) — overnight wins, but the famous form needs intraday <= 0 and it is solidly positive; the market-level gap (+1.22 bps/session) is inside its permutation null (p=0.561). Overnight wins in 83/114 names (73%), clearing the pre-registered 2/3 bar. Decays ~70% across halves, the shape of post-publication decay for a 2019 paper. **Costs settle it**: break-even round-trip 3.88 (SPY) / 5.05 (EW-120) / 5.39 (composite Q5) bps against a 5-10 bps band; at 5 bps the books return -3.43% / -0.61% / +0.51% a year against buy-and-hold's +16.08% / +17.67% / +9.81%. Deflated Sharpe 0.140. 18 variants. |
| **H4** | *retested 2026-08-09 under H18e* | Entering at/near the CLOSE beats entering at the next open. **The only rule this repo ever shipped with no local test.** | close > open | **CONFIRMED AS A RULE, DEMOTED AS AN EDGE.** Shipped book size, 2,219 entry dates: close(t) +2.70% vs open(t+1) +2.64% per 42-session window = **+5.29 bps/window, CI [+0.39,+10.73], NW t +2.07, positive in BOTH halves**; hit rate +0.43pp. But a RANDOM pick of 2 names from the identical pool on identical dates earns **+4.51 bps** [p5 +2.45, p95 +6.79] and +5.29 sits inside it; pick-minus-pool is +0.68 bps (t +0.44). So buying the close is real and free, but it is a property of the overnight session generally, NOT of the engine's picks — it was being credited to the wrong thing. Rule kept; justification corrected in the docs. |
| H20 | 2026-08-09 | Summing 78 squared 5-minute returns estimates a day's variance far more precisely than one squared daily return, so it forecasts next-day risk better and fixes the volatility targeting that half-worked in H11 (Andersen-Bollerslev 1998; Corsi 2009). | RV models beat daily-close models on QLIKE; vol targeting then works in both halves | **FORECAST CONFIRMED DECISIVELY, PAYOFF REJECTED.** HAR on 5-minute RV cuts out-of-sample QLIKE **20.3% below the incumbent `blended_vol` (t = -6.46, 29/29 symbols, both halves, identical ranking under both proxies)**, and the mechanism row isolates it to the MEASUREMENT: the same EWMA at the same lambda gains -0.0401 (t = -6.83) purely from being fed RV instead of daily r^2. Then it buys nothing. SPY vol targeting still fails the both-halves bar (0.811 vs 0.601, then **1.109 vs 1.322**) — H11's exact shape with a much better forecast; every Sharpe gain sits inside a shuffled-leverage null and every CI straddles zero; adding a day of LAG *improves* the book, which is what noise does. The drawdown cut (-33.8% -> -25.2%) is real, clears its null, and is **deepest under the CRUDEST forecast**. HAR's 33.3x turnover puts break-even at **7.0 bps against a 10 bps bar** — the best QLIKE model is the worst net book. Ceiling measured: only **59.9%** of daily variance is open-to-close. 32 variants. |
| H25 | 2026-08-09 | 52-week-high proximity is a standalone signal that dominates conventional momentum and avoids its crashes (George-Hwang 2004). | high proximity outperforms | **REJECTED — AND IT CONDEMNS THE ENGINE'S LARGEST WEIGHT.** `config.W_HIGH = 0.25` is bigger than 12-1 momentum and had never been tested alone. Deciles: raw D10-D1 -182.8 (t -1.84) but **SPY beta falls monotonically 1.61 -> 0.79**, and market-adjusted D10-D1 is **+23.9 (t 0.29)** — it is a beta sort. Momentum on the identical pool has U-shaped beta and a market-adjusted +177.1 (t 2.11), i.e. it survives the adjustment that kills proximity. Deciding test — proximity INSIDE momentum terciles: -151/-62/-173 bps (t -2.34/-1.41/-3.31), negative in all three, opposite of the registered sign; the reverse sort survives. **Fama-MacBeth: high52 controlling for momentum -298.6 (t -3.17); momentum controlling for high52 +265.0 (t +3.74)** — both past the t>3 bar, in opposite directions. Date-shuffle: a proximity snapshot a FULL YEAR stale reproduces 69% of the spread, so it identifies a persistent stock type (high-beta laggards), not a timing state. Horizon 21/42/126 td: -142/-183/-538, growing more negative where George-Hwang requires growth. Crash claim inverts: bear-formation spread -722 bps against momentum's -48. Break-even cost NEGATIVE (-83.2 bps). 58 variants. |

**The one actionable item in three rounds.** H25 is the first result that points
at a specific engine change rather than at a rejection: the largest weight in
the v5 composite measures **negative at t = -3.17** once momentum is
controlled, while the momentum weights measure **positive at t = +3.74**. It is
in-sample and the 2022-2026 holdout is retired, so it does not license a v6 on
its own — but the evidence bar for REMOVING a component that measures negative
is not the bar for adding one. Highest-priority agenda item.

**Method rules added this round.**

- **Rule 13: risk-adjust every cross-sectional sort before believing it.** H25's
  raw decile profile was monotone, large and completely spurious — the sort
  ordered the cross-section by beta and the profile was the equity premium
  priced by beta. Report each bucket's beta and market-adjusted mean alongside
  the raw mean, always.
- **Rule 14: quote the permutation SE against the Newey-West SE.** H25's random
  null had an SE 0.15x the real series', making its z anti-conservative by ~7x
  (z -12.65 against an honest t of -1.84). A permutation p-value is not
  quotable on its own for a persistent long-short book. H17 is the exonerating
  case: its DiD design gives an SE ratio of 0.94-1.14, because differencing
  four direction-conditioned cells removes the persistence.
- **Rule 15: a control can leak too.** H25's date-shuffle drew donor dates
  uniformly, allowing donors AFTER the formation date and reading closes inside
  the holding window; that version manufactured +130.5 bps out of nothing. The
  lab found and fixed it mid-study. Audit the controls with the same suspicion
  as the signal, and keep an inverted-donor self-test that measures what a leak
  would look like.

**Trial count.** These five labs ran 32 + 18 + 24 + 18 + 58 = **150 variants**,
taking the repo's running N to roughly **340**. Every deflated-Sharpe
calculation from here uses that number, which raises the bar for everything
that follows — as it should.

### H21g/H21h — Nagel's CENTRAL conditioning: reversal is paid when liquidity is EXPENSIVE (registered 2026-08-09, BEFORE any run)

The H21 round closed with an explicit note that one form of the mechanism was
deliberately left unrun — "Nagel's central conditioning — that liquidity
provision pays most when VIX is high and market makers are constrained — was
deliberately NOT run, because adding it after seeing a null would be hunting a
variant. It is the registry row a future lab should open." This is that row,
opened as its own pre-registration with its own failure conditions, and it
counts toward N whatever it says.

Mechanism (Nagel RFS 2012, the paper H21 is named after; Campbell-Grossman-Wang
1993): the reversal return is the FEE earned by whoever absorbs uninformed order
flow, and a fee is set by the supplier's constraint — when volatility is high,
market makers' risk-bearing capacity is impaired, they withdraw, and the price
of immediacy rises. So the liquidity theory does not predict a constant
reversal; it predicts a reversal that is LARGE when volatility is high and
absent when it is low. Nagel's headline is exactly that: VIX forecasts the
returns to a reversal strategy with an R^2 near 0.3 at the weekly horizon.

**Why this changes how H21a's null should be read.** H21a measured +6.95 bps a
week at t = +0.69. If the true process is a large constrained-state premium
mixed with a zero calm-state premium, an unconditional average has no power by
construction, and "no reversal on average" is not evidence against a liquidity
premium — it is the average of a thing that is only sometimes there.

State variable, US-EQUITIES-ONLY by the user's scope constraint: VIX is the
literature's regressor but is an index, so this row uses **SPY's own trailing
21-session realised volatility**, annualised, which is the definition this
repo's crash flag already uses. Known at close(t-1) (`.shift(1)`), cut into
terciles by an **EXPANDING** quantile with a 252-session burn-in — never a
full-sample quantile, which is the exact lookahead `scout/backtest.py` had to
fix in the v4 harness.

Conditioning is on the DATE, not on the cross-section, so the quintile ranking
is bit-identical to H21a/H21b; the per-date spread series is simply subset.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H21g | 2026-08-09 | The unconditional reversal spread at h=5 is larger in the high-volatility tercile than in the low-volatility tercile, because the fee for supplying immediacy rises when market-maker capacity is impaired. | spread(high vol) - spread(low vol) > 0 | REGISTERED — not yet run |
| H21h | 2026-08-09 | The JOINT form: H21b's quiet-minus-news difference is larger in the high-volatility state — an uninformed move costs most to absorb exactly when absorbing it is expensive. | diff(high vol) > diff(low vol), high-vol diff outside its news-label-shuffle null | REGISTERED — not yet run |

Mandatory honesty diagnostic, registered ex ante so it cannot be used as a
rescue: a high-volatility state inflates EVERY cross-sectional spread
mechanically. The spread is therefore reported twice — raw bps, and NORMALISED
by that state's own cross-sectional dispersion of the 5-session forward return.
**If the raw ordering appears and the normalised ordering does not, the result
is volatility scaling and not a price of liquidity, and must be reported as
such.** Costs are charged in-state (a premium that exists only in high-vol
states must clear 10 bps in those states, not on the pooled average), and
Rule 13's SPY beta regression is run inside each state.

Failure conditions, stated in advance: H21g fails if high-minus-low is
negative, or flips sign across halves, or is absent in the normalised measure;
H21h fails if the high-vol difference sits inside its own news-label-shuffle
null or flips sign across halves. Known power limit disclosed in advance: a
tercile of 2,600 dates is ~866 dates ≈ 173 independent weekly windows, and the
quiet-leg coverage problem of H21b (Rule 15) applies inside each state and will
be printed as a per-state date count before any return number.

### H20 — 5-minute realized variance forecasts next-day risk better than daily closes (registered 2026-08-09, BEFORE any run)

Mechanism (Andersen-Bollerslev 1998; Corsi 2009; Patton 2011): the variance of
a day's return is a SUM over the day, so summing 78 squared 5-minute returns
estimates it with roughly 1/78th the estimator variance of the single squared
daily return — one observation of a random variable is a terrible estimate of
its second moment, and the intraday tape supplies 78. A forecaster fed the
low-noise measurement should therefore forecast tomorrow's variance better
than one fed the noisy one, for the same model form.

**Why this row exists.** Volatility targeting (H11) is the ONE thing in this
repo's alpha stack that half-worked: on SPY it cut maxDD from -34.0% to -27.3%
at matched vol, but its Sharpe gain flipped across halves (1.03 vs 0.92, then
0.56 vs 0.63) and it was NOT shipped. H11 was fed `growth.blended_vol`, which
sees only daily closes. If the forecast is the binding constraint, a better
forecast fixes it; if it is not, H20 says so and the vol-targeting idea is
closed for good on a measurement rather than a hunch. This is also the first
row in the repo that tests a RISK model rather than a return signal, so its
loss function is a forecast loss, not a P&L.

Lab: `scout/rv_forecast_lab.py`. Universe = every symbol in the pre-warmed
5-minute cache with complete 2018-01-02..2026-07-31 coverage (28 US large caps
+ SPY as benchmark; GOOG dropped as a GOOGL dual-class duplicate, QQQ/IWM
dropped as ETFs). 5Min bars, regular session only, split-repaired by
`intraday.apply_split_repair`, PLUS an explicit |close-to-close| > 45% blank
(the repo's documented 5.1% unadjusted-split debt), both counts reported.

**The realized measures.** `rv_oc = rv_5min^2` is open-to-close only; the
target is CLOSE-TO-CLOSE variance, so the primary proxy is the Hansen-Lunde
naive sum `rv_cc = rv_oc + overnight_ret^2`. The single squared close-to-close
return `r2` is the second, much noisier, conditionally-unbiased proxy; Patton
(2011) proves QLIKE and MSE rank forecasts consistently under EITHER, so a
disagreement between the two proxies is itself a finding.

**The shift, explicitly.** Every forecaster produces `fc[t]` = the variance
forecast FOR session t, built only from sessions <= t-1. In code the features
are dated t and the prediction is `.shift(1)`-ed onto t+1; that is the only
forward alignment in the file. Losses compare `fc[t]` with the proxy realized
ON t. The vol-target book earns `L[t] * close_ret[t]` where
`L[t] = clip(target/sqrt(252*fc[t]), 0, 2)` — settable at the close of t-1.
(H11/`sleeve_lab` applied a further `.shift(1)`, one day more conservative;
that convention is rerun as a registered sensitivity so the two are
comparable.)

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H20a | 2026-08-09 | EWMA(lambda=0.94) on 5-minute realized variance beats the repo's incumbent `growth.blended_vol` (daily closes) on out-of-sample QLIKE, because the same estimator form fed a 78x less noisy measurement makes a better forecast. | dQLIKE = QLIKE(ewma_rv) - QLIKE(blended) < 0, both halves | REGISTERED — not yet run |
| H20b | 2026-08-09 | HAR (daily/weekly/monthly realized variance, walk-forward OLS) beats EWMA-RV, because volatility is long-memory and three heterogeneous horizons approximate that better than one exponential decay. | QLIKE(har) < QLIKE(ewma_rv) | REGISTERED — not yet run |
| H20c | 2026-08-09 | **THE DECIDING ROW FOR THE MECHANISM.** The advantage is the MEASUREMENT, not the estimator form: EWMA-RV beats EWMA on daily squared returns run at the identical lambda. Without this row, any RV win could just be "the incumbent's 63-day rolling leg is badly specified". | QLIKE(ewma_rv) < QLIKE(ewma_daily_094) | REGISTERED — not yet run |
| H20d | 2026-08-09 | The QLIKE ranking is the same under BOTH proxies (rv_cc and the single squared daily return), as Patton's robustness proves it must be if the proxies are conditionally unbiased. | same ordering under both | REGISTERED — reported whatever it says |
| H20e | 2026-08-09 | **THE PAYOFF ROW.** Feeding the better forecast into SPY volatility targeting makes the Sharpe uplift survive in BOTH halves — the condition H11 failed — because H11's failure was forecast error, not a flaw in the targeting identity. | Sharpe(voltgt_best) > Sharpe(buy-and-hold) in both halves | REGISTERED — registered as the row most likely to FAIL, because the H11 halves were 1.03/0.92 then 0.56/0.63 and a variance forecast cannot change the sign of a mean |
| H20f | 2026-08-09 | The drawdown benefit at matched volatility is real and survives the forecast swap; a better forecast makes it LARGER. | maxDD(voltgt) < maxDD(buy-and-hold), best forecast best | REGISTERED — not yet run |
| H20g | 2026-08-09 | COSTS: any QLIKE win must survive the turnover it buys. A forecast that reacts faster re-levers more often, so break-even round-trip cost must clear the 5-10 bps band for large caps. | break-even >= 10 bps | REGISTERED — not yet run |

Registered forecasters, all reported whatever they say (11): `blended_daily`
(the incumbent), `ewma_daily_094` (RiskMetrics on daily r^2 — the H20c
control), `ewma_rv_094` / `ewma_rv_090` / `ewma_rv_097` (lambda sensitivity,
frozen values, not fitted), `rw_rv` (yesterday's RV — the naive random walk),
`uncond` (expanding-window mean — the naive constant, which every model must
beat or the study is vacuous), `har_rv` (per-symbol OLS in levels),
`har_log` (per-symbol OLS in logs with the exp(s^2/2) Jensen correction),
`har_log_pool` (one pooled panel fit), and `ewma_rv_shuf` (the CONTROL).
Scored under 2 proxies. Payoff books: buy-and-hold, vol-target under each of
4 forecasts, an expanding-mean CONSTANT-leverage book, a shuffled-leverage
null, on SPY and on the equal-weight 28-name book.

Controls (nulls, not trials): (i) **DATE-SHUFFLE** — `rv_cc` permuted across
dates within each symbol, then run through the identical EWMA; forecast skill
must collapse to the unconditional benchmark, and this is the H15 lesson
applied to a risk model. (ii) **NAIVE BENCHMARKS** — `uncond` and `rw_rv`
bound the problem from below; a model that cannot beat the expanding sample
mean has measured nothing. (iii) **CONSTANT-LEVERAGE control for the payoff
row** — the same book run at the causal expanding-mean of the forecast's own
leverage, which strips out timing and leaves only average exposure; if it
matches the targeted book, the forecast contributed nothing and only the
leverage level did. (iv) **SHUFFLED-LEVERAGE null**, 200 draws, mean AND SD
quoted (Rule 10). (v) **matched benchmark** SPY buy-and-hold, and every
levered series rescaled by a single constant to SPY's realised vol before
drawdowns are compared (Sharpe is invariant to that constant, drawdown is
not).

Statistics: losses are averaged across symbols WITHIN each date, so the unit
of observation is a date (symbols share days and their variances are one
common factor plus noise — a row bootstrap would claim ~29x more independence
than exists). Newey-West t on the date series, a moving-block bootstrap by
date, and the ratio of the bootstrap SE to the NW SE printed next to every
p-value (Rule 14). Both halves reported for every row. n_eff from the variance
ratio, as `calibrate.py` does.

Failure conditions, stated in advance: H20a fails if dQLIKE is positive, or if
its sign flips across halves, or if its CI straddles zero; **H20c fails — and
takes the MECHANISM with it, leaving only "a different estimator" — if EWMA-RV
does not beat EWMA-daily at the same lambda**; H20e fails if either half's
targeted Sharpe is below buy-and-hold's, which is exactly what H11 recorded;
H20f fails if the drawdown improvement is not present under every forecast;
H20g fails if break-even round-trip cost is under 10 bps.

Known limits stated in advance: the minute cache starts 2018-01-02, so this is
8.6 years and ~2,160 sessions against H11's 2016-2026 — the LEVELS here are
not comparable to the H11 table, only the differences between forecasters on
this common sample are. `close_px` is the last continuous 5-minute print, not
the closing auction (median gap ~1 bp, `--official-close` splices the auction
in). Leverage is assumed free (rf = 0) exactly as ALPHA-STACK assumed it; mean
leverage is printed for every book so the reader can size that assumption.

### H21g/H21h results (2026-08-09, real data — `scout/reversal_lab.py`)

Same panel as H21: 2,664 sessions x 120 point-in-time-liquid names,
2016-01-04 .. 2026-08-07. The 252-session burn-in leaves 2,412 sessions
classified; the state changes 139 times, so it is persistent rather than
day-to-day noise. Terciles carry mean annualised SPY realised vol of
**7.04% / 11.43% / 22.87%** — the cut separates genuinely different markets.

| # | verdict |
|---|---|
| H21g | **REJECTED.** The reversal spread by volatility state is **+12.85 / -4.11 / +17.63 bps** (low/mid/high), block-bootstrap t = +0.88 / -0.35 / +0.76. High minus low is **+4.79 bps, SE 27.29, t = +0.18** — the registered sign, and nothing else. It is **not monotone**: the mid-vol state is NEGATIVE, the same U shape H21c found in abnormal-news terciles. The pre-registered failure condition "flips sign across halves" FIRES: high-minus-low is **-0.84 in the first half and +10.41 in the second**. The registered honesty diagnostic does not save it either — normalised by each state's own cross-sectional dispersion the ordering survives (+0.0291 low vs +0.0487 high) but on a contrast whose t is 0.18, a preserved ordering is a preserved coin flip. **And Rule 13 REVERSES it:** the high-vol book runs **beta +0.41** to SPY against the low-vol book's **-0.07**, so market-adjusted the alphas are **+3.05 bps (t=+0.14) in the high-vol state against +13.84 (t=+0.94) in the low-vol state**. The state where Nagel's mechanism predicts the largest premium is the state where, after removing the market, there is least. In-state break-even round-trip cost is 8.16 / -2.62 / **11.27** bps against 10 charged — the high-vol cell scrapes past the letter of the cost bar on a t=0.76 gross number. |
| H21h | **NOT REJECTED BY ITS OWN CONDITIONS, AND NOT A RESULT — the coverage check is what settles it.** The quiet-minus-news difference is **-22.93 / +10.05 / +30.31 bps** across the three states, which is monotone in the registered direction, and the high-vol cell's halves are **+31.33 / +29.30** — no sign flip. Its news-label-shuffle null is -1.49 ± 13.44 at the 98th percentile, p = 0.030, so the "inside the null" condition does not fire either. **Both of those readings are wrong, for reasons this file already wrote down.** (i) Rule 14: the permutation null's SD is **0.63x** the block bootstrap's, i.e. 1.6x too tight, so p = 0.030 is anti-conservative; the honest statistic is **+30.31 bps [-9.66, +73.69], t = +1.43** on 574 dates = **114 independent weekly windows**. (ii) Rule 15, the check that killed H21e's t=2.54 cell: the high-vol scorable dates are **2018:116, 2019:114, 2020:129, 2021:56, 2022:103, 2023:11, 2024:9, 2025:23, 2026:13** — **90% of them fall in 2018-2022**, and the median date lands inside 2020, so the "stable halves" compare two slices of the same five years. Zero dates in 2016-2017 by construction (burn-in). This is H7a's shape for the third time in one file. |

Long-only form, the only one this user could trade (losers minus the matched
equal-weight pool, quiet group, high-vol sessions only): **+27.27 bps
[-4.18, +57.02], t = +1.75, n = 722 dates**, turnover 0.93, break-even
**29.41 bps** against 10 charged, net **+17.99 bps per 5-session hold**. It is
the best-looking book anywhere in H21 and it is not shippable: the CI straddles
zero, the halves are **+7.37 then +47.16** — a 6x spread — and it inherits the
same 2018-2022 concentration.

**What H21g/H21h actually add to the H21 verdict.** The H21 round left open the
possibility that "no reversal on average" was a mixture artefact — a real
constrained-state premium averaged with a calm-state zero. That defence is now
tested and it does not hold: conditioning on the price of liquidity moves the
unconditional spread by +4.79 bps at t = +0.18, and what movement there is turns
out to be SPY beta. **H21 stays REJECTED, and it is now rejected against the
mechanism's own preferred conditioning rather than in spite of it.**

Caveat kept narrow, as the H21 scope note requires: realised volatility is an
equity-only stand-in for VIX (the user's scope excludes index derivatives), and
Nagel's result is strongest in small caps and at intraday-to-daily horizons,
neither of which this 120-mega-cap weekly panel can reach.

Trial count: N rises by **2** registered rows (H21g, H21h), taking H21 to 18 and
the repo to roughly 342. The in-state cost rows, the Rule 15 year-coverage
print and the long-only in-state book are diagnostics required by existing house
rules, reported in full, not a search. Controls are nulls and do not count.

**Method note — Rule 16 for the house: verify a lab by rewriting it, not by
rereading it.** H21's headline numbers were reproduced from a second,
deliberately naive implementation (plain `rank(pct=True)` quintiles and
`groupby` means instead of the lab's seeded-lexsort labeller and `cell_means`).
Everything computed on a THICK cell agreed to within 5% — unconditional spread
+7.28 vs +6.95 bps, SPY beta +0.340 vs +0.33, market-adjusted alpha -3.31 vs
-3.35 bps, news leg -1.44 vs -2.00 — while the statistic computed on the
4.3-name quiet cell moved **64%**, from +9.70 to +15.90 bps, and the difference
from +11.69 to +17.34. Both implementations are correct; the quiet-leg number
is simply not robust to an innocuous tie-breaking convention. That is a sharper
statement of the thin-cell problem than any confidence interval in the file, and
it is free: the agreement on thick cells is what licenses trusting the code at
all, and the disagreement on the thin one is the error bar that matters.

### H19 — does the FIRST half hour predict the LAST half hour? (registered 2026-08-09, BEFORE any run)

Mechanism (Gao-Han-Li-Zhou, "Market intraday momentum", JFE 129(2) 2018): a
large block of end-of-day demand is MECHANICALLY a function of the morning's
move — leveraged ETFs must rebalance toward the close in the direction of the
day's return, and investors who cannot watch the tape all day (infrequent
rebalancers, late institutional flow, closing-auction MOC orders) concentrate
their trading in the last half hour — so the 15:30-16:00 return is partially
forecastable from the 09:30-10:00 return.

Why it earned a test here: it is the rare anomaly whose cause is a plumbing
constraint rather than a belief, so sentiment changing cannot arbitrage it away;
and it is the first hypothesis in this repo whose entire holding period is 30
minutes, which makes the COST ANALYSIS the study — 252 round trips a year is
2.5%/yr at 1 bp and 12.6%/yr at 5 bps. Also: 2018-2026 is entirely
POST-publication for a 2018 paper whose evidence ran to 2013, so this is the
McLean-Pontiff test RESEARCH-AGENDA.md item 7 demands.

Lab: `scout/intraday_momentum_lab.py` over `scout/intraday.py` 5-minute SIP
bars, split-repaired, regular session only, 2018-01-02..2026-07-31. SPY, QQQ,
IWM as the index instruments (ETFs as benchmarks/replications only, per the
US-equities-only scope) plus the most liquid US large caps in the 5-minute
cache. The session is cut into the paper's 13 half-hour bins; P0 = the 09:30
opening print, Pj = the close of the last bar STARTING before 09:30+30j, so
P1 = 10:00, P12 = 15:30, P13 = 16:00.

**The shift: there isn't one in the core test, and there must not be.** The
ordering is enforced by CLOCK TIME inside a single session — the signal reads
bars whose start time is < 10:00 ET, the traded return reads bars whose start
time is >= 15:30 ET, 5.5 hours and no shared bar apart. The two places a
shift() appears are stated loudly: H19e's GHLZ signal divides by
`P13.shift(1)` (the previous session's close, a BACKWARD shift), and the
magnitude-scaled variant standardises r1 by a rolling sd over the 60 sessions
ENDING AT t-1 (`.shift(1)` on the rolling window). The placebo deliberately
uses `r1.shift(1)`. `r1`/`r13` are asserted equal to `intraday.session_frames`'
independently-computed `first30_ret`/`last30_ret` — measured difference
**exactly 0.0** on every session of every symbol checked.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H19a | 2026-08-09 | SPY's 09:30-10:00 return predicts its 15:30-16:00 return, because the morning move mechanically sets the size and direction of the late rebalancing flow. | sign(r1)->r13 > 0 | **REJECTED — WRONG SIGN.** -0.82 bps/session, NW t = -1.02, CI [-2.40, +0.65], hit 48.27%, both halves negative (-0.90 / -0.72). Regression b = **-0.0613** (t = -0.68, R2 0.333%) against GHLZ's +0.05 / t 3-5 / R2 ~1%. Inside the randomized-sign null [-1.18, +1.25] and the date-shuffle null [-1.26, +1.19]. n = 2,138 sessions. |
| H19b | 2026-08-09 | The same on QQQ (independent replication). | same sign | **REJECTED** — -0.50 bps, t = -0.57, hit 49.06%, halves -0.08 / -0.91, b = -0.0109 (t = -0.25, R2 0.017%). |
| H19c | 2026-08-09 | The same on IWM (independent replication; small caps should show it MORE if the mechanism is rebalancing flow). | same sign, larger | **REJECTED** — -0.27 bps, t = -0.36, hit 49.06%, halves -0.64 / +0.09, b = -0.0314 (t = -1.05). Smallest, not largest: the mechanism's size ordering does not appear either. |
| H19d | 2026-08-09 | A magnitude-scaled position (r1 over its trailing 60-session sd, clipped at 2) beats the pure sign, because the flow is proportional to the move, not to its direction. | scaled >= sign | **REJECTED, AND WORSE THAN THE SIGN** — -1.60 / -1.06 / -0.82 bps. Scaling up on big mornings makes the wrong-sign bet bigger, which is what a real negative slope does. |
| H19e | 2026-08-09 | GHLZ's OWN r1, which is measured from the PREVIOUS CLOSE and so contains the overnight gap, works where the open-to-10:00 version does not. | > 0 | **REJECTED** — -0.28 / -0.04 / **-1.44** bps; IWM t = -1.97 with CI [-2.85, -0.02], i.e. the only CI in the study excluding zero points the WRONG way. This is also the only row a split defect could touch (its signal crosses the overnight), which is why the AAPL 2020-08-31 repair is not optional. |
| H19f | 2026-08-09 | The MID-DAY control: if 09:30-10:00 also predicts 10:00-15:30, the effect is generic same-day autocorrelation and NOT the close-specific mechanism. Registered as the row that DISCRIMINATES, with no directional prediction. | close-specific => midday ~ 0 | **THE MECHANISM'S DISCRIMINATING TEST FIRES AGAINST IT.** Mid-day is the only thing alive in the study: **+2.06 / +4.91 / +3.93 bps**, positive in BOTH halves on all three (+1.75/+2.37, +5.06/+4.76, +2.37/+5.50), date-shuffle p = 0.104 / 0.014 / 0.037 at Rule-14 SE-ratios 1.00 / 1.10 / 0.98, and beating its always-long benchmark (+1.21 / +1.39 / -0.43). So continuation exists and is smeared across the middle of the session — the alternative hypothesis — while the close is the one place it is absent. **Untradeable regardless: break-even +2.07 / +4.93 / +3.96 bps against a 5-10 bps band.** |
| H19g | 2026-08-09 | GHLZ's other and stronger predictor, the SECOND-to-last half hour (r12), predicts r13. | > 0 | **NOT REJECTED ON SIGN, REJECTED ON EVERYTHING ELSE.** +0.97 / +1.01 / +0.37 bps (t = 1.45 / 1.32 / 0.50, shuffle p = 0.085 / 0.114 / 0.309) but the sign **flips across halves on all three** (+2.12/-0.17, +2.68/-0.66, +1.51/-0.77) — this house calls that noise — and break-even is 0.98 / 1.02 / 0.38 bps. |
| H19h | 2026-08-09 | It works on single large caps, where the late-day flow is less index-driven but the spreads are wider (registered expecting a WEAKER gross effect and a much worse net one). | book > 0 gross | **REJECTED.** Equal-weight book of **50** large caps: **-0.54 bps/session, NW t = -1.16**, block-bootstrap CI [-1.49, +0.20], both halves negative (-0.76 / -0.33), hit 48.22%; only **14 of 50** names positive and **5 of 50** positive in both halves. Cross-sectional top-third-minus-bottom-third: -0.91 bps (t = -2.08), negative in both halves (-1.64 / -0.18). Prev-day placebo -0.22 bps. Negative everywhere, significant nowhere at the t>3 bar — **and the reason that last clause is phrased carefully is the Rule 14 note below, which is about this lab's own first draft.** |
| H19i | 2026-08-09 | COSTS DECIDE IT: at 252 round trips a year the break-even round-trip cost must clear the 5-10 bps large-cap band. | break-even >= 5 bps | **FAILED, AND NOT NARROWLY.** Break-even is NEGATIVE for every close-specific row in the study, so no cost is low enough. Net annualised: SPY -4.6% / -7.0% / -13.7% at 1 / 2 / 5 bps; the 50-stock book -3.9% / -6.3% / -13.1% / -23.4% at 1 / 2 / 5 / 10 bps. The only positive row in the whole study (H19f mid-day) breaks even at 2.07 / 4.93 / 3.96 bps, still under the band. |
| H19j | 2026-08-09 | DIAGNOSTIC, reported in full: hold sign(r1) through each of the 12 later half hours. If the mechanism is right the profit concentrates in the LAST bin. | max at j=13 | **THE CLEANEST REFUTATION IN THE ROUND, and it needs no significance threshold.** Continuation is mildly POSITIVE through the middle of the session (peak at the 11:00 bin: +1.25 / +1.02 / +1.09 bps) and the 15:30-16:00 bin is **the only one negative on all three instruments** (-0.81 / -0.50 / -0.27). The mechanism names the last half hour; it is the worst of the thirteen. |
| H19k | 2026-08-09 | Exiting in the OFFICIAL CLOSING AUCTION rather than at the last 16:00 tape print rescues it, because the auction is the venue the mechanism actually names and a 5-minute bar cannot isolate that print. | auction > tape | **REJECTED — NO DIFFERENCE.** -0.70 / -0.41 / -0.17 bps against the tape version's -0.82 / -0.50 / -0.27. The auction print differs from the 16:00 tape print by a median 8.0e-05 to 1.3e-04 in log units, so there was never much room for it to matter. |

Controls (nulls, not trials): (i) RANDOMIZED SIGN, 2,000 draws — the book
version (`book_nulls`) runs three variants and quotes only one, see the Rule 14
note below; (ii) DATE SHUFFLE of the signal,
2,000 draws, which preserves the signal's marginal (including the fact that
mornings are up ~52% of the time, so the null carries the strategy's long
bias) and destroys only the pairing; (iii) PREV-DAY PLACEBO, sign(r1 of t-1)
-> r13 of t, which came out **-0.61 / +0.09 / -1.28** bps, i.e. as large as
the real signal — its own verdict; (iv) MATCHED BENCHMARKS — always-long r13,
always-long the mid-day window, and buy-and-hold 09:30-16:00; (v) both halves
on every row.

**Rule 14 both exonerated and fired, in the same lab — which is the useful
part of this round.**

- On the SINGLE-INSTRUMENT rows it is exonerated. SE-ratios (permutation null
  SD over the real series' Newey-West SE) land at **0.93-1.10** on every ETF
  row, so unlike H16 (2.3-3.5x too tight) and H21 (3.9-4.2x too tight) these
  permutation p-values can be read at face value. The reason is structural: a
  30-minute non-overlapping hold generates a P&L series with almost no
  autocorrelation for a permutation to destroy, which is exactly the condition
  under which within-date permutation is valid.
- On the 50-NAME BOOK it fired, against this lab's own first draft. The
  obvious null — an independent coin per name, then average — scored the book
  at **3.7 SD below the null, one-sided p = 1.000**, which would have licensed
  a confident "significantly negative". It is wrong, and its SE-ratio is
  **0.31**: the real book's signs are correlated across names (on most
  sessions the whole market's first half hour points the same way), so the
  real book is close to a levered bet on the market's last half hour, while an
  independent-sign null diversifies that factor away and comes out three times
  TIGHTER than the book's own Newey-West SE of 0.468 bps. `book_nulls`
  therefore also runs **`rowshuf`**, which permutes whole CROSS-SECTIONS across
  dates so the within-date sign correlation survives and only the date pairing
  is destroyed; the report labels the other two "do not quote". `rowshuf`
  widens to SE-ratio 0.59 and still under-states, so **the quoted statistic is
  the Newey-West t of -1.16 with a CI straddling zero, not any permutation
  p-value.** The self-test reproduces the failure mode on demand on a synthetic
  market-correlated panel: SE-ratio 1.05 for `rowshuf` against 0.29-0.30 for
  the per-name nulls.
- **Rule 16 for the house, generalising both:** a permutation null must
  preserve every dependence the real statistic inherits — across TIME for a
  persistent book (H16), and across NAMES for a cross-sectional one (here).
  Permuting the dimension that carries the correlation is how a null becomes
  anti-conservative, and the SE-ratio is what catches it.

**Effective independent sample.** One observation per SESSION and the windows
cannot overlap (a 30-minute hold does not touch tomorrow), so n = 2,138 IS the
independent sample per instrument — no cluster inflation to correct, which is
the one statistical luxury this hypothesis has over every other lab in the
file. What is NOT independent is the three instruments: SPY, QQQ and IWM share
every date and nearly all of their market factor, so they are one experiment
shown three ways; and the 50 stocks are collapsed to one book number per
session before anything is tested (49.2 names per session on average, minimum
23 — the panel is unbalanced because a few names list part-way through).

Data integrity, printed by the lab: **15,362,973 bars over 61 symbols**, 59
passing the 750-session bar, **124,909 symbol-sessions -> 123,680 kept**; 1,041
half-days dropped (volume-detected UNION the hardcoded NYSE calendar, because
on a 13:00 close Alpaca keeps printing after-hours bars to 15:55 and a naive
grid builds a fake r13 out of them); 186 incomplete grids dropped; **2** extreme
prints dropped and enumerated (APP 2024-11-07, HOOD 2021-08-04), under BOTH the
repo's standing |1-day return| > 45% rule and a |half-hour return| > 25% rule.

The split repair fired **three** times and **only one is a real split**: AAPL
2020-08-31 4:1 (111,873 bars back-adjusted) is genuine, while HON 2018-10-01
(1.011:1) and HON 2018-10-29 (1.032:1) are the Garrett Motion and Resideo
SPIN-OFFS, which Alpaca's feed reports as `forward_split` and which
`unapplied_splits_close` cannot classify at ratios that close to 1 — the same
false-positive class as the MET 2017-08-07 case already on the record. **All
three are harmless here for the same reason**: an unapplied split cannot
contaminate the core test even in principle, because r1 and r13 are both
WITHIN-session ratios and a split factor cancels in both, and rescaling every
bar strictly before an ex-date leaves every within-session ratio untouched.
Only H19e's signal crosses the overnight, so the two false positives can move
exactly two symbol-sessions of ~124,000. This split-insensitivity is why the
study could afford a universe the daily labs could not.

Scope of the rejection, stated as narrowly as it deserves: three US index ETFs
and 50 US large caps, 2018-2026, one 5-minute SIP tape, and a universe that is
HINDSIGHT-LIQUID (today's most-traded names, warmed by an earlier job) — a bias
that flatters a long-drift strategy and therefore makes this rejection
conservative. The sample is entirely post-publication for a 2018 paper whose
evidence ran to 2013, so McLean-Pontiff decay is the charitable reading; this
lab cannot separate decay from an effect that never generalised, because it
does not own the original window.

Trial count: N rises by **61** — 7 specifications (sign, scaled, GHLZ-r1,
r12, mid-day, auction-exit, placebo) x 3 instruments = 21, plus 4 book-level
specifications on the single-stock leg, plus the 12-bin term-structure
diagnostic x 3 instruments = 36. Control draws (2,000 permutations per null,
2,000 block-bootstrap resamples, 500 book-null draws) are nulls and do not
count. No variant in the registered direction is positive, so there is no best
book to deflate.

### H20 results (2026-08-09, real data — `scout/rv_forecast_lab.py`)

Ran on 2,156 sessions x 29 symbols of 5-minute bars (2018-01-02..2026-07-31);
scored out of sample on **1,861 dates / 52,453 symbol-sessions**, 2019-03-07..
2026-07-31, after a 280-session warm-up, every forecaster on the IDENTICAL
cells. Registered above BEFORE the run; statuses filled in after.

**The forecast rows are the strongest confirmations in this file. The payoff
row is a rejection. Both of those sentences are the result.**

| # | verdict |
|---|---|
| H20a RV-EWMA vs the incumbent | **CONFIRMED.** EWMA(0.94) on 5-minute realized variance beats `growth.blended_vol` by **-0.0424 QLIKE, NW t = -3.90**, block-bootstrap CI [-0.0735, -0.0224], negative in BOTH halves (-0.0627 / -0.0221), and it wins in **29 of 29 symbols**. n_eff 405 of 1,861 dates. |
| H20b HAR vs RV-EWMA | **CONFIRMED — the largest effect in the file.** HAR beats RV-EWMA by **-0.0585 (t = -7.86)**, CI [-0.0758, -0.0430], both halves, n_eff 861. Pooled-panel HAR is nearly identical (-0.0539, t = -6.05). Best model against the incumbent: QLIKE **0.3971 vs 0.4980 = -20.3%, t = -6.46**, 29/29 symbols, and the MSE ordering agrees (319.6 vs 333.8). |
| H20c **THE MECHANISM ROW** | **CONFIRMED — it is the MEASUREMENT, not the estimator.** Identical EWMA recursion at identical lambda, fed 78 squared 5-minute returns instead of one squared daily return: **-0.0401 QLIKE, t = -6.83**, halves -0.0386 / -0.0415, n_eff 1,192 — the most precisely estimated row here. The daily-r^2 EWMA beats the incumbent in only **17 of 29** names; the RV-fed one does in **29 of 29**. Andersen-Bollerslev replicates cleanly on this tape. |
| H20d proxy invariance | **CONFIRMED.** Spearman rank correlation between the two proxies' orderings = **1.000**, same winner (`har_log`) under both the low-noise `rv_cc` and the single squared daily return. Patton's robustness result holds exactly, which also means neither proxy is quietly doing the work. |
| H20e **THE PAYOFF ROW** | **REJECTED on SPY — the registered failure condition fires, exactly as it did for H11.** Best forecast: Sharpe 0.959 against buy-and-hold 0.863, but by halves **0.811 vs 0.601 then 1.109 vs 1.322** — better in the turbulent half, worse in the calm one. That is H11's shape reproduced with a 20%-better forecast. Every Sharpe difference against buy-and-hold (+0.023 / +0.063 / +0.096 / +0.098 across the four forecasts) has a bootstrap CI **straddling zero** (widest [-0.285, +0.475]), P(>0) = 0.53-0.66, and every one sits **inside the shuffled-leverage null** (76th-90th percentile). On the 28-name per-asset book the both-halves condition IS met — but by the INCUMBENT too, and the BEST forecast makes the WORST book (har_log 1.432 against ewma_rv's 1.493 and blended's 1.444). **The payoff is not ordered by forecast quality. That is the finding.** |
| H20f drawdown | **HALF-CONFIRMED; THE SECOND CLAUSE REJECTED.** On SPY the matched-vol drawdown benefit is real and present under every forecast (-33.8% -> -25.2 / -27.7 / -26.7 / -27.0) and is the ONLY payoff quantity that clears its null (4th-12th percentile of 200 shuffled-leverage draws). But it does **not grow with forecast quality** — the crude daily incumbent cuts the drawdown DEEPEST of the four — and on the per-asset book every overlay's matched drawdown is WORSE than the unlevered book's (-32.3 to -39.0 against -31.3). Drawdown control comes from de-levering at all, not from de-levering accurately. |
| H20g costs | **FAILS FOR THE WINNER, PASSES FOR THE RUNNER-UP.** HAR re-levers constantly: **33.3x annual one-way turnover against EWMA-RV's 4.4x**, break-even round-trip **7.0 bps against the registered 10 bps bar**. At 10 bps HAR's Sharpe is **0.823, below buy-and-hold's 0.863**, while cheap EWMA-RV holds 0.908 (break-even 34.5 bps). **The best QLIKE model is the worst net-of-cost book.** |

**Finding 1 — the tell that settles the payoff row.** Rerunning the payoff with
H11/`sleeve_lab`'s extra `.shift(1)` — one MORE day of staleness — *raises* the
best book's Sharpe from 0.959 to **1.044** and its second half from 1.109 to
1.249. A genuine timing edge degrades when you lag it. This one improves. That
is what noise does, and it is worth more than the point estimate it destroys.

**Finding 2 — the ceiling, measured rather than assumed.** Only **59.9%** of
close-to-close variance in this panel is open-to-close. The other 40% arrives
in the overnight gap, which no intraday tape can measure and which stays a
ONE-observation-per-day estimate however fine the bars get. A 78x better
measurement of 60% of the problem buys 20% of the loss — the arithmetic is
consistent, and it bounds what any future intraday risk model here can add.
(Filtering the two legs separately at the same lambda is an exact identity —
EWMA is linear — and the lab prints that identity as a machinery check; at
different lambdas, 0.97 intraday / 0.80 overnight, it gains a statistically
insignificant -0.0044, t = -1.09.)

**Finding 3 — the failure is the market's shape, not the model's.** The halves
are not two samples of one regime: half 1 (2019-03..2022-11) runs 23.2% vol at
Sharpe 0.601 and contains COVID and the 2022 bear; half 2 (2022-11..2026-07)
runs 14.9% vol at Sharpe 1.322. Volatility targeting de-levers into volatility,
so in a calm rising tape it is structurally short the thing that is paying.
This is H5g's rejected long-only overlay reaching the same conclusion from the
other direction, and no variance forecast can fix it, because the problem is
that the CONDITIONAL MEAN and the conditional variance moved together and only
one of them is being forecast.

**Method rule added this round.**

- **Rule 16: a better input is not a better outcome — test the conversion, not
  just the input.** H20 measures the cleanest, most replicated forecast
  improvement in this repository (t = -6.5, 29/29 symbols, both halves, two
  proxies, survives the auction-close rerun) and converts it into a P&L
  difference indistinguishable from permuted leverage. The chain
  "better measurement -> better forecast -> better decision" broke at the last
  link, and only the last link is worth money. Every future accuracy claim in
  this repo must carry the decision test that H20e is, and must report the
  turnover the accuracy costs.

Data hygiene, as registered: `intraday.apply_split_repair` fired once in this
panel (AAPL 2020-08-31 4:1, 111,873 bars back-adjusted); the explicit
|close-to-close| > 45% guard blanked **0** further symbol-sessions, and the
largest surviving daily moves are all genuine events (ORCL +35.9% 2025-09-10,
NFLX -35.1% 2022-04-20, LITE 2018-11-12, META -26.4% 2022-02-03). 74 thin
symbol-sessions were dropped by `session_frames`. The whole forecast section
was rerun with `--official-close` (closing-auction prints spliced in place of
the last continuous 5-minute print) and reproduces every QLIKE to three
decimals and every t-statistic to two.

Trial count: N rises by **32** — 9 counted forecasters x 2 proxies = 18 scoring
cells (`uncond`, `rw_rv` and the date-shuffled control are nulls and do not
count), 4 forecasts x 2 books = 8 payoff configurations, the 4-config
`--extra-lag` rerun, and 2 cells for the post-hoc split-leg forecaster. The
`--official-close` rerun is a robustness reproduction of the same cells, not a
new search. Best |t| anywhere in the study is **-7.86**, and it belongs to a
forecast-accuracy row that made no money.

### H26 — real post-earnings drift, sorted on the SURPRISE rather than the price reaction (`scout/sue_lab.py`, run 2026-08-09)

Mechanism (Bernard-Thomas 1989/1990; Foster-Olsen-Shevlin; Livnat-Mendenhall
2006): investors do not fully appreciate the autocorrelation in quarterly
earnings changes, so a firm whose earnings surprise the seasonal random walk
keeps having that surprise priced in for weeks after the announcement. PEAD is
the most-replicated anomaly in finance and its standard sort variable is SUE,
**not** the price reaction that H2b already rejected. Until `scout/sec_bulk.py`
existed this repo had no earnings-surprise measure at all.

Universe TODAY's S&P 1500 (1,390 firms produce a usable SUE), 2017-01..2026-03,
42,119 usable events on 2,026 entry sessions, 41,378 ranked at h=21.
`SUE_q = (NI_q - NI_{q-4}) / sd(NI_j - NI_{j-4}, j=q-8..q-1)` on consolidated
GAAP `NetIncomeLoss` LEVELS (the share count cancels, which also immunises it
against the split-adjustment trap), >= 6 of 8 trailing diffs.
**The shift:** entry = close of the session AFTER the later of the 8-K Item 2.02
date and the 10-Q/10-K filing date; decile breakpoints from the PREVIOUS 63
sessions of announcements, never the current cohort; asserted on the real event
table before any number prints.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H26a | 2026-08-09 | SUE deciles drift: D10-D1 market-adjusted is positive at 5/21/42/63 sessions under strict point-in-time entry. | D10-D1 > 0, decaying | **REJECTED.** **+11.11 / -2.46 / +21.19 / -1.58 bps**, t = +0.77 / -0.07 / +0.45 / -0.03, 95% CI [-74.66,+65.34] at h=21; the sign flips across halves at three of four horizons and the decile profile is non-monotone everywhere (at h=21 D1 is the second-BEST decile). Unwinsorised +8.81/-16.59/+17.45/-3.16; raw (not market-adjusted) +8.47/-22.84/+4.49/-17.43. Rule 13 has nothing to strip: trailing beta is 1.04-1.10 across all ten deciles. |
| H26b | 2026-08-09 | **THE DECIDING ROW.** The effect is in the TIMING of the surprise, so permuting each firm's own SUEs across that firm's own announcement dates must destroy it. | shuffle null ≈ 0 | **FIRES — H15's failure mode, reached through accounting data.** Strict spec h=63: real **-1.58**, firm-level date-shuffle null **+79.49 ± 33.23**. The one cell with the registered sign (announcement-anchored h=21, +51.36, both halves positive) has a shuffle null of **+27.88 ± 17.40, p = 0.085** — 54% of it survives destroying its timing entirely, and at h=63 the static component (+81.16) is three times the real effect (+27.12). Random-pick nulls have an SE 0.51-0.67x the block bootstrap's (Rule 14 print). |
| H26c | 2026-08-09 | POSITIVE CONTROL, registered so a null is readable: SUE must sort the announcement-day reaction. | monotone, large | **PASSES EMPHATICALLY — and it is the finding.** Two-day reaction by SUE decile: **-117.0 -89.4 -24.3 +10.4 +42.8 +92.1 +91.6 +117.7 +143.3 +186.1 bps**, D10-D1 **+303.1 at t = +15.43**. Event-time CAR from close(a-1): D10-D1 = **+313.2 / +301.8 / +351.5 / +335.8 / +352.1** bps at (-1,+1)/(+5)/(+21)/(+42)/(+63) — **89% of the whole three-month spread is paid by close(a+1).** The market prices the seasonal-random-walk surprise in one session and then stops. That is the honest 2026 statement of PEAD in the S&P 1500. |
| H26d | 2026-08-09 | CONTROL: the 2-day price-reaction sort must reproduce H2b's null on this pipeline. | ≈ 0 | **REPRODUCED.** Mid/small caps, 42 sessions, raw: reaction >= +5% ends **+1.88%** (n=6,483), <= -5% ends **+1.94%** (n=5,725), difference **-0.06pp** — H2b recorded "end identically, ~+1.7-2.4% both". Reaction deciles D10-D1 -11.34/+45.23/+80.12/+41.60, \|t\| <= 1.82. SUE and the 2-day reaction correlate at rank **0.118**, so the two sorts genuinely are different variables. |
| H26e | 2026-08-09 | PEAD is documented to concentrate down-cap, where it cannot be traded cheaply. | LOW liquidity > HIGH | **SIGN INVERTED.** h=21 by liquidity tercile: LOW -15.78 / MID -13.99 / HIGH +14.22; h=63: LOW -76.91 / MID +3.65 / **HIGH +153.41 (t=+1.73)**. By segment at h=63: small -25.77, mid -96.91, large +114.59. The ann-anchored spec orders the same way (h=63 HIGH +181.48, t=+2.33). The only cells carrying the registered sign are the largest and most liquid — the opposite of the mechanism's own prediction, and the shape of a multiple comparison (12 cells cut, 2 clear \|t\|=2). |
| H26f | 2026-08-09 | LATE-WINDOW PLACEBO: drift is over by ~60 sessions, so sessions +63..+126 on the same surprise must pay ~0. | ≈ 0, less than in-window | **NO DRIFT CLOCK.** +18.72 bps over the late window = **+0.30 bps/session against the in-window -0.03**. Both are zero; the late window is if anything the larger of the two. |
| H26g | 2026-08-09 | Costs decide tradeability at 10 bps round trip. | break-even >= 10 bps | **FAILS.** Two-legged D10-D1 break-even 5.6 / -1.2 / 10.6 / -0.8 bps. The long-only D10-minus-pool form (the only tradeable shape here) is +0.21 / +15.92 / +8.55 / +10.92 bps at t = +0.02 / +0.86 / +0.29 / +0.33, best net **+0.71%/yr** against SPY's ~+15.8%/yr. |

Registered variants, all reported, counted from the run's own output: **53
long-short decile/quintile sort cells** (strict-PIT x 4 horizons; raw
not-market-adjusted x 4; announcement-anchored x 4; price-reaction x 4;
quintiles x 2; SUE winsorised ±8 x 2 — a no-op by construction, see below;
price-scaled SUE x 2; |1-day|>45% excluded x 2; liquidity terciles 3 x 2 on
each of the two entry specs = 12; segments 3 x 2 on each = 12; late window 1),
plus **4 unwinsorised reruns** and **8 long-only D10-minus-pool books** = **65
cells**, plus one whole-study rerun with the frozen-quote guard off. The
"winsorise SUE at ±8" row is reported as the no-op it is: clipping a variable
used only through a rank cannot move a decile boundary, and it moves h=21 and
h=63 by exactly 0.00 bps. Controls (nulls, not trials): random-pick 200 draws,
firm-level date-shuffle 200 draws, price-reaction sort, matched pool + SPY, the
positive control, the late-window placebo.

Effective independent sample, stated because it is the binding constraint: the
cross-section is collapsed to one row per SESSION before any statistic, so
41,378 events are **2,026 sessions = 96 non-overlapping 21-session holds and 32
at h=63**. This study excludes a drift larger than roughly 0.7%/quarter in this
universe; it cannot exclude one of 20-30 bps.

**Data-integrity finding, bigger than the hypothesis.** The brief's warning was
the 5.1% unapplied-split debt; this lab repairs 5 such events (AAPL 2020-08-31
4:1, SIRI 2024-09-10 1:10, ROL x2, DEA) and prints the 12 it cannot classify.
The defect that actually moved the numbers was the **frozen quote**: Alpaca
keeps printing a delisted ticker at its last trade, and a Chapter-11 ticker
reissued to the reorganised company splices a penny quote onto a $30-70 price.
With the retirement rule off, the UNWINSORISED h=63 D10-D1 spread is
**+896.68 bps (halves +2053.15 / -274.01)** against the clean run's -3.16, and
-174.51 / -188.99 / -153.52 at h=5/21/42. Those splices land in the LOW-SUE
decile by construction — a company about to reorganise reports terrible
earnings — so they are worth **thirty times** any effect being measured and
carry whichever sign the splice happens to have. 23 symbols retired, 377
zero-volume sessions blanked; the 1%/99% return winsorisation independently
removes almost all of it, so the two guards are belt and braces. **Rule 17 for
the house: any study whose sort variable correlates with financial distress
must retire frozen quotes BEFORE it reports a number, because the artefact
concentrates in one extreme bucket rather than spreading across the
cross-section.**

Trial count: N rises by **65** registered cells, taking the repo past ~410.
Controls are nulls and do not count. Best |t| in the registered direction
anywhere in the study is **+2.33**, in a liquidity cell whose sign contradicts
the mechanism; the only |t| that clears the house's t>3 bar is the **+15.43** on
the announcement-day reaction — i.e. on the row that says the surprise is
already in the price.

### H27 — the accruals anomaly: earnings that are not cash flow do not persist (registered 2026-08-09; statuses filled in after the run)

Mechanism (Sloan 1996): the accrual component of earnings is less persistent
than the cash component, and investors fixate on the headline number without
decomposing it, so firms whose profits are mostly accruals are systematically
over-valued and underperform as those accruals fail to convert into cash.

Prior stated BEFORE the run so the result could not be re-framed afterwards:
Green-Hand-Soliman (2011) document the effect's decay to insignificance in
large caps after ~2003, Sloan's own hedge portfolio is dominated by microcaps,
and McLean-Pontiff's post-publication haircut is ~58%. Index members over
2016-2026 are the hardest possible cohort — **a null was the modal expected
outcome**, and a null here is weak evidence about the small-cap tape.

Lab: `scout/accruals_lab.py`. Signal = (NetIncomeLoss(qtrs=4) −
NetCashProvidedByUsedInOperatingActivities(qtrs=4)) / average Assets(qtrs=0),
the two flows INNER-JOINED on (ticker, fiscal year end) so the earnings and
the cash flow always cover the same period. **The shift:** a record enters the
panel at `max(filed)` of its four component facts, never at period end; within
a ticker a later filing may only introduce a NEWER fiscal year (10-K
comparatives can never overwrite a fresher number); the panel is then
`shift(1)`ed so a filing dated t is used from t+1; returns are
`close.shift(-h)/close - 1` at the same index t. Staleness cap 550 days.
Universes: sp1500 (today's members, survivorship on the entry side, PRIMARY
because the anomaly is documented down-cap) and pit500 (`scout/pit.py`, each
date's ACTUAL members). 127 month ends 2016-02..2026-08, 13,658 usable annual
records over 1,441 tickers, 133,627 symbol-formation-date legs at h=42.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H27a | 2026-08-09 | The LOW-accrual quintile beats the HIGH-accrual quintile at a 42-session hold, equal weight, monthly formation. | Q1−Q5 > 0 | **SIGN RIGHT, CLEARS t>3, AND STILL NOT PROVEN.** sp1500 Q1−Q5 = **+0.53 / +1.06 / +3.08 / +6.56 %** per 21/42/126/252-session hold, block-bootstrap t = **3.00 / 3.34 / 3.41 / 3.75**, positive in both halves (+1.37/+0.74 at h=42), no entry-phase luck (h=42 phases +1.04/+1.07 — Rule 9 clean, unlike H7a). Costs irrelevant: turnover 0.23/window, break-even **461 bps** against 10 charged. Annualised L/S Sharpe 0.85, deflated Sharpe **0.63** at N=58 — the highest in this repo by 4x. Rejected as a *result* by H27b/c/e below, not by its own t. |
| H27b | 2026-08-09 | **DECIDING ROW 1 — the mechanism, not the sort.** Sloan's claim is that HIGH-accrual firms are over-valued, so the high quintile must underperform the matched equal-weight pool. | Q5 − pool < 0 | **REJECTED — THE SHORT LEG IS EMPTY.** Q5 − pool = **+0.06 / +0.12 / +0.37 / +0.95 %**, positive at every horizon. Q1 − pool = +1.18% (t=4.70) at h=42, so **100% of the spread is the long leg**. Bucket returns 4.21 / 2.75 / 2.61 / 2.44 / 3.15 against a pool of 3.03 are a U, not the monotone decline the anomaly predicts. |
| H27c | 2026-08-09 | **DECIDING ROW 2 — the date shuffle.** Permuting each firm's OWN accrual history across formation dates keeps the firm and its accrual distribution and destroys only WHICH YEAR it accrued; Sloan's mechanism is a claim about the year, so most of the spread must die. | shuffled << actual | **HALF-FAILS.** The shuffle earns **+0.45 of the +1.06%** at h=42 (static share 43%; 51/49/56% at the other horizons). Timing-attributable residual **+0.60%, t = 1.91** — below the house t>3 bar. Rule 14 print, as required: the shuffle null's SD is **0.36x** the real block-bootstrap SE, so its p = 0.00 is an artefact of the null and is NOT quoted. The PLACEBO null (each symbol permanently assigned another symbol's whole accrual history) has SE ratio 0.77 and mean +0.01 ± 0.24, so the pairing itself is real; it is the TIMING that is not established. |
| H27d | 2026-08-09 | **THE ROW THAT DECIDED WHETHER TO BUILD IT.** The signal is independent of what this repo already computes — the v5 momentum composite and `sec_bulk.net_issuance` (Pontiff-Woodgate note issuance and accruals are related by construction). | \|rho\| < 0.2 | **PASSES, CLEANLY — the one unambiguous positive in the round.** Cross-sectional Spearman **−0.043** to the v5 composite (sd 0.091) and **−0.065** to 12-month net issuance (sd 0.028); return correlation of the books **+0.201** and **−0.370**. Accruals are not momentum in a costume and not issuance in a costume. (Context: over these dates the v5 composite's own Q5−Q1 is −0.51%/hold and the low-issuance book −0.29%/hold.) |
| H27e | 2026-08-09 | Survivorship: the primary universe is today's S&P 1500, so the result must survive on point-in-time membership. | pit500 spread > 0 and significant | **FAILS.** pit500 h=42 = **+0.42%, CI [−0.06, +0.90], t = 1.70**; long-only Q1 vs SPY +0.25% (t=0.90) with halves **+0.79 / −0.29**. Nearest like-for-like on large caps: today's members +0.72% vs each date's actual members +0.42%, i.e. ~40% of the large-cap spread goes away when membership stops being chosen with hindsight. Not a clean decomposition (XBRL coverage 92.8% vs 76.1%) but it points one way. |
| H27f | 2026-08-09 | Rule 13: the dollar-neutral book is regressed on SPY before its sign is quoted. | alpha survives | **PASSES — the first candidate this round to do so.** ls_beta **+0.14** at h=42, alpha **+0.68%, t = 2.34** (sp1500); pit500 beta +0.01, alpha +0.38%, t = 1.59. Unlike H25 (52-week high), H21 (reversal) and H16 (tone), this is NOT a beta artefact. |
| H27g | 2026-08-09 | Variant, registered as a staleness probe: the accrual known 12 MONTHS AGO should sort WORSE, because a mispricing corrects as the accruals fail to convert. | stale < fresh | **REJECTED — STALE IS NOT WORSE, IT IS BETTER.** +1.12% (t=3.64) against the fresh +1.06%, on a signal whose 12-month cross-sectional rank autocorrelation is only **+0.49** (37% of names still within a fifth of their old percentile). Companion diagnostic: an accrual that will not be FILED for another 12 months earns **+0.90%** — no better than the honest one. Accounting news that arrives on a filing date does not behave like this; a slow-moving firm type does. |
| H27h | 2026-08-09 | Variants reported whatever they said (10 families, 58 cells): guard off, three size segments, sector-neutral ranks, deciles, ending-assets scaling, ex-financials/real-estate, the +12m peek diagnostic, the $10M liquidity gate, gross-profitability terciles. | n/a | Guard off +1.16 vs +1.06 (the bad-print exclusion is worth 0.10pp, and 8.00 vs 6.56 at h=252). Segments at h=42: large **+0.72** (t 2.46), mid **+1.57** (t 3.53), small **+0.79** (t 1.99) — mid-caps strongest, small-caps weakest, which is the opposite of the down-cap prior. Sector-neutral +0.71 (t 3.19) — two thirds survives, so it is not ONLY a sector bet. Deciles D1−D10 +1.32. Ending assets +1.07. Ex-financials/RE **+1.20**. Liquidity-gated +1.13 (t 3.73) — it is not hiding in untradeable names. Gross-profitability terciles: **+2.32 (t 3.53) / +1.02 / +0.84 (t 1.31)** from low to high profitability, so it is not the Novy-Marx quality premium in a costume — it is strongest where profitability is worst (41% GP coverage; weak evidence). |

Controls (nulls, not trials): (i) RANDOM-PICK, labels permuted inside each
formation date, 200 draws; (ii) PLACEBO PAIRING, each symbol permanently
assigned another symbol's whole accrual history, 200 draws — the only honest
null for a persistent characteristic (H16 Finding 2); (iii) DATE SHUFFLE, 200
draws, the deciding one; (iv) MATCHED BENCHMARK, equal weight of the eligible
pool, plus SPY; (v) Rule 13 regression. Every null is printed with the ratio of
its SD to the real series' block-bootstrap SE, as Rule 14 requires.

Data debt handled explicitly: 253 prints with |1-day return| > 45% over 152
symbols (SIRI 2024-09-10 **+925.6%**, GPOR +585.0%, FTR +278.9%) — a
(symbol, formation date) leg is DROPPED when one falls inside its holding
window, and the whole study is re-run with the guard OFF so the choice is
priced (+1.06 vs +1.16 at h=42). 40 symbols retired at a frozen-quote run of
>=10 identical closes (the H21 defect).

**Coverage, stated before the returns as the binding constraint.** 1,431 of
1,505 current S&P 1500 members have a period-matched NI + CFO + assets record
(95.1%); the 74 that do not tag consolidated earnings as `ProfitLoss` rather
than `NetIncomeLoss`, which is not in `sec_bulk`'s tag set — a SYSTEMATIC
exclusion (utilities, firms with minority interests), not noise. Only **557 of
732** point-in-time S&P 500 members map at all (76.1%), and the missing ones
are the DELISTED: `company_tickers.json` maps CIKs to CURRENT tickers, so an
acquired company's facts are unreachable. **The survivorship-free universe is
therefore survivorship-CONTAMINATED on the fundamental side**, which bounds
what H27e can prove.

Effective independent sample: the cross-section is collapsed to one spread per
formation date before any statistic, so n is at most **127 dates**, not the
133,627 legs — and with a 42-session hold on a monthly grid that is ~63
non-overlapping windows per entry phase across 2 phases. At h=252 it is ~10.

**H27 verdict: NOT PROVEN.** The registered sign is right, clears t>3 at four
horizons, survives Rule 13, has no phase luck, costs nothing to trade, and is
independent of everything this repo owns — and the leg the anomaly is named
after does nothing, 43% of it is a static firm characteristic, a year-stale
signal works better than a fresh one, and point-in-time membership cuts it by
60%. What was measured is that **firms whose cash flow massively exceeds their
reported earnings outperformed in 2016-2026** (Q1 median accrual −0.116, 25.0%
Information Technology and 9.6% Energy against pool shares of 12.9% and 4.0%,
versus a Q5 that is **38.9% Financials** where NI − CFO is not an accrual in
any accounting sense). That is a firm-type premium with a plausible non-cash-
charge explanation this repo cannot test — `sec_bulk` carries no
depreciation or stock-compensation tag — not Sloan's mispricing correction.

Trial count: N rises by **58** registered cells (4 horizons x 2 universes,
guard-off 4, 3 segments x 4, sector-neutral 4, deciles 4, ending-assets 4,
stale-12m 4, ex-financials 4, peek 4, liquidity 4, 3 GP terciles x 2).
Controls are nulls and do not count. Deflated Sharpe of the best book at
N=58: **0.63** — which is the highest in this repo and still describes a book
whose own controls say it is a style tilt.

### H24 — post-earnings drift measured from the NEWS rather than the price (`scout/news_pead_lab.py`, run 2026-08-09)

Mechanism (Barber-Odean 2008; Tetlock 2007; Bernard-Thomas 1989): the market
learns how a quarter landed from the coverage that follows the release — how
much is written and how positive it reads — so if that text diffuses more
slowly than the price reaction, a news-measured surprise should forecast drift
where the reaction alone does not. This is the first surprise measure in this
repo that needs no fundamental data: H2b rejected the PRICE reaction, H26
rejected accounting SUE, and neither ever read the announcement's own news.

Universe the cached Benzinga panel — 120 point-in-time-liquid S&P 500 members
as of 2016-01-04 — joined to REAL 8-K Item 2.02 dates from
`scout/earnings_history.json`. **3,725 usable events, 95 firms,
2016-04-07..2026-02-04**, 1,271 distinct entry sessions. Quintiles against the
previous 252 sessions of announcements (Livnat-Mendenhall breakpoints, min
cohort 100), market-adjusted, 1%/99% winsorised, block bootstrap over sessions
with block = h, 2,000 draws. **The shift:** signals read news attributed by
`news_data`'s rule to sessions {e, e+1} — everything readable before close(e+1)
— plus a coverage baseline over [e-63, e-1]; ENTRY = close(e+1); fwd_h =
close(e+1+h)/close(e+1) − 1. The two-session window is forced, not chosen: an
8-K's filing DATE does not say whether the release was pre-open (moves session
e) or post-close (moves session e+1), so {e, e+1} is the smallest window that
contains the reaction under both and close(e+1) the first price after it under
both. `main` asserts it on the real table; `--selftest` proves it on synthetic.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H24a | 2026-08-09 | A — net headline TONE in the two sessions around the announcement forecasts drift at 21 and 42 sessions. | Q5-Q1 > 0 | **REJECTED — no drift, and half the variable is the price.** +27.63 bps (t=+0.71) at h=21 and +29.26 (t=+0.53) at h=42, all stories; +19.38 / -5.19 for specific-only. Every CI straddles zero; halves disagree in 6 of 10 primary cells. Tone's rank correlation to the same announcement's reaction is **+0.407** (SUE's was 0.118) — a headline written after the bell largely reports the move — so inside reaction terciles the spread is **-118.21 / +28.91 / -101.01** bps at h=42, negative in four of six cells and never the registered sign. Tone on session e alone (before the move can be reported) is +46.43 at h=21 (t=+1.22, halves +86.20/-6.91) and -8.70 at h=42. |
| H24b | 2026-08-09 | B — abnormal headline VOLUME on the announcement window forecasts drift (attention shock at the one event where attention is guaranteed). | Q5-Q1 != 0 | **REJECTED — and H15's failure mode fires again, at h=5.** +39.56 (t=+0.96) / +10.98 (t=+0.21) at h=21/42 all-story, -9.93 / -19.01 specific. The three largest \|t\| in the whole study are at h=5 — abn(spec) +35.74 (t=+1.87, halves +34.92/+36.57), C +33.25, abn(all) +31.31 — and the FIRM-LEVEL DATE SHUFFLE returns **+19.29 ± 15.92 (p=0.205)** against abn(all)'s +31.31: **62% of it survives destroying the timing entirely**, so it is which firms get swarmed, not when. Unlike tone, B IS genuinely independent of the price (rank corr **+0.034**) — and equally null. |
| H24c | 2026-08-09 | **THE CONTROL THAT MUST REPRODUCE H2b.** C — the two-session price reaction predicts nothing at 21/42 sessions. | ≈ 0 | **REPRODUCED.** The H2b cohort test run verbatim: reaction ≥ +5% ends **+2.40%** (n=620), ≤ −5% ends **+2.56%** (n=545), difference **−0.17pp** (H2b: "end identically, ~+1.7-2.4% both"; H26d: −0.06pp). Quintile spread +54.23 (t=+1.39) at h=21 and +13.15 (t=+0.24) at h=42. **And A and B did not beat it** — at h=21 the largest spread of the five belongs to the control, and at h=5 the only cell clearing both nulls (random p=0.030, shuffle p=0.020) is C. That is H24's pre-registered failure condition, stated before the run. |
| H24d | 2026-08-09 | POSITIVE CONTROL, registered so a null is readable: the news instruments must sort the announcement's OWN reaction. | monotone | **PASSES EMPHATICALLY, AND IT IS THE FINDING.** Two-day market-adjusted reaction by tone quintile: **-385.9 -130.4 +43.4 +170.9 +278.6 bps, Q5-Q1 +664.5 at t=+22.22** (specific +699.7, t=+23.70), monotone across all five. Abnormal volume sorts the ABSOLUTE reaction monotonically — **3.18 / 3.78 / 3.97 / 4.60 / 5.12 %** — and the signed one barely (+26.3, t=+0.91), which is H15's "attention forecasts size, not sign" reproduced at the event where attention is guaranteed. A 435-word hand lexicon reads the earnings verdict at t=+22 and that buys **nothing** the next day. Contamination scale: +664.5 contemporaneous against +27.6 forward at h=21 — entering one session earlier would have manufactured a 24x "PEAD" that is entirely the announcement move. |
| H24e | 2026-08-09 | LATE-WINDOW PLACEBO: sessions +42..+84 on the same signal must pay ~0. | ≈ 0 | **NO DRIFT CLOCK, same as H26f.** Tone +27.71 bps (+0.66/session) against the in-window +0.70/session; abn(all) +78.00 (+1.86) against +0.26. The late window is if anything the larger — both are zero. |

Registered variants, counted from the run's own output: **155 sort cells**
(primary 5 signals x 4 horizons = 20, their unwinsorised twins 20, raw
not-market-adjusted 10, deciles 10, ex-defect 10, tone-by-session 8, liquidity
terciles 24, reaction-tercile double sorts 48, late placebo 5). Controls are
nulls and do not count: random-pick 200 draws x 20 cells, firm-level date
shuffle 200 x 20, the price-reaction sort, the H2b cohort test, matched pool +
SPY, the positive control, the late placebo. **Best \|t\| anywhere in the
registered set is +1.87**, at h=5, in a cell whose own date shuffle reproduces
most of it; at the registered headline horizons the best is **+0.96**.

Effective independent sample, the binding constraint: 3,580 ranked events on
1,271 distinct entry sessions inside a 2,664-session calendar = **63
non-overlapping 42-session windows**, 127 at h=21. This study excludes a
news-sorted drift bigger than roughly 1.1%/quarter in this cohort; it cannot
exclude one of 20-30 bps.

**Instrument quality, measured, because this is where H24 differs from H16.**
H16 measured tone on every session of every name and 49% of symbol-sessions
scored exactly zero because no lexicon word fired. Conditioning on an earnings
announcement fixes that: the window carries a **median of 15 stories** (mean
18.1), 98.8% of events have at least one, and only **9.7%** score zero tone.
The instrument was ~5x denser and pointed at the event the literature says it
should work on, and it still measured nothing forward.

**Method note that outlives the verdict — Rule 14 is EXONERATED by this design.**
H16, H22 and H25 found permutation nulls 2.3x, 12.1x and 6.7x TIGHTER than the
honest standard error, which is why Rule 14 exists. Here all 40 of them land at
**0.66x to 1.10x of the block bootstrap's SE** (median 0.90). The reason is
structural: a persistent daily long-short book's P&L is autocorrelated and
within-date permutation destroys that, while an event study whose cross-section
is collapsed to one row per SESSION before any statistic, with breakpoints from
a trailing cohort, has no such persistence to destroy. **Rule 18: Rule 14 is a
warning about a DESIGN, not about permutation tests — collapse to sessions and
take breakpoints from a trailing cohort, and the permutation p-value becomes
quotable again.** Print the ratio either way; that is what shows which case you
are in.

**Survivorship, in the EVENT layer rather than the price layer.** The price
universe is point-in-time, but only **96 of the 120 panel names have any 8-K
history**: the SEC's ticker file maps CIK to the CURRENT ticker, so FB, UTX,
BRCM, CELG, TWX, EMC, MON, AET, PXD, ESRX, ATVI, ALXN, MYL, CBS, WBA, EA and 8
others vanish, and XOM contributes one usable date. The missing names are the
acquired and the renamed, so the event sample tilts to survivors. Same leak
H22 and H26 documented, reached by a third route; no `pit.py` fixes it.

Trial count: N rises by **155** registered cells.
