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
| H4 | 2026-08-08 | Entering at/near the close (never the open) avoids paying overnight drift + open-auction spreads. Adopted from literature (Lou-Polk-Skouras) without a local test — execution hygiene, not a signal; not testable with daily bars alone. | n/a | **ADOPTED, SHIPPED** — bold banner atop the workbook's How To Read This + skill report line. |

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
| H18a | 2026-08-09 | SPY's equity premium accrues in the close-to-open leg; the open-to-close leg contributes ~zero or negative. | ann(overnight) >> ann(intraday), intraday <= 0 | REGISTERED — not yet run |
| H18b | 2026-08-09 | The same holds in the cross-section: an equal-weight book of the 120 names earns its premium overnight, and the pattern replicates in a large majority of individual names (a market-level result driven by 6 of 120 stocks is not the LPS mechanism). | EW overnight > intraday; >= 2/3 of names agree | REGISTERED — not yet run |
| H18c | 2026-08-09 | LPS's ACTUAL factor claim: classic 12-1 winner-minus-loser momentum earns its spread overnight and gives part of it back intraday (institutional momentum demand is expressed at the open). | WML overnight > 0 > WML intraday | REGISTERED — not yet run |
| H18d | 2026-08-09 | The repo's OWN gated v4 composite book (long-only top quintile of the eligible pool) likewise earns its excess overnight. | book overnight > intraday | REGISTERED — not yet run |
| H18e | 2026-08-09 | **THE DECIDING ROW FOR H4.** On identical picks, a 42-session swing trade entered at close(t) beats the same trade entered at open(t+1), because the entry price forgone is exactly one overnight return, which the mechanism says is positive. Book size 2 (the shipped size). | mean(close-entry) - mean(open-entry) > 0, hit rate higher | REGISTERED — not yet run |
| H18f | 2026-08-09 | H18e at book size 5 (sensitivity, reported whatever it says). | same sign as H18e | REGISTERED — not yet run |
| H18g | 2026-08-09 | An overnight-only strategy (buy the close, sell the open, every session) survives realistic costs. Registered as the expected-NEGATIVE row: it trades a full round trip every day, so break-even round-trip cost equals the mean daily overnight return in bps. | break-even >= 5 bps to be tradeable | REGISTERED — expected to FAIL; RESEARCH-AGENDA.md already lists overnight-only trading as dead |

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
| H22a | 2026-08-09 | Low net issuance (net repurchase) beats high net issuance: the quintile spread on -1 x the 12-month log change in split-adjusted shares outstanding is positive at a 42-session hold. | Q5-Q1 > 0 | REGISTERED — not yet run |
| H22b | 2026-08-09 | High gross profit / total assets beats low: the quintile spread on GP/AT is positive at a 42-session hold. | Q5-Q1 > 0 | REGISTERED — not yet run |
| H22c | 2026-08-09 | **THE DECIDING ROW.** Both signals are INDEPENDENT of the repo's existing price composite: the cross-sectional rank correlation to 12-1 momentum and to the gated v5 composite score is small, and the fundamental spread survives inside every momentum tercile. A signal that re-expresses momentum adds nothing to a momentum engine no matter how well it sorts on its own. | \|rho\| < 0.2 AND spread > 0 in all 3 momentum terciles | REGISTERED — not yet run |
| H22d | 2026-08-09 | The two signals combine: an equal-weight average of the two cross-sectional ranks spreads wider than either alone (they proxy different frictions, so their errors are weakly correlated). | combined spread >= max(single spreads) | REGISTERED — not yet run |
| H22e | 2026-08-09 | The long-only top quintile — the only form this repo could actually trade — beats SPY on Sharpe after 10 bps round trip. | Sharpe(Q5 net) > Sharpe(SPY) | REGISTERED — expected to FAIL on Sharpe; registered because long-only is the shipped form and the answer must be measured, not assumed |
| H22f | 2026-08-09 | ROBUSTNESS, registered ex ante so it cannot be used as a rescue: the GP/AT result holds on the subset of names that tag `GrossProfit` directly, without the Revenue-minus-COGS derivation. | same sign, similar magnitude | REGISTERED — not yet run |
| H22g | 2026-08-09 | RULE 9 COMPLIANCE: a 21-td ("monthly") rebalance gives the same answer as the phase-pooled daily-formation estimator, and the spread across the 21 possible entry phases is small relative to the effect. | phase spread << effect | REGISTERED — not yet run |

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
| H21a | 2026-08-09 | Unconditional short-horizon reversal exists in this large-cap panel: the bottom quintile of the skip-a-day 5-session return beats the top quintile over the next 5 sessions. | Q1 - Q5 > 0 at h=5 | REGISTERED — not yet run |
| H21b | 2026-08-09 | **THE DECIDING ROW.** Reversal is a liquidity premium, so it is STRONG among stocks with NO specific news in the formation week and WEAK OR ABSENT among stocks that had news. | spread(no-news) - spread(news) > 0, CI on the DIFFERENCE excluding zero | REGISTERED — not yet run |
| H21c | 2026-08-09 | The same ordering appears monotonically across terciles of ABNORMAL news volume (log((k+1)/(median k over the prior 60 sessions +1))), because abnormal coverage is the sharper proxy for "the move was information". | spread falls monotonically from the low-attention to the high-attention tercile | REGISTERED — not yet run |
| H21d | 2026-08-09 | The LONG-ONLY leg (buy the losers, no shorts — the only practically tradeable form for this user) beats the equal-weight eligible pool, and does so more in the no-news group. | Q1 - pool > 0, larger for no-news | REGISTERED — not yet run |
| H21e | 2026-08-09 | Reversal profits classically concentrate in illiquid names, so restricting to the top-liquidity half of the panel should SHRINK the spread; registered as the expected-NEGATIVE row that decides tradeability. | spread(top-liquidity half) < spread(all), possibly to zero | REGISTERED — expected to SHRINK |
| H21f | 2026-08-09 | Costs decide it at weekly rebalancing: the break-even round-trip cost must clear the 10 bps charged for large caps. | break-even >= 10 bps | REGISTERED — the tradeability gate |

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
