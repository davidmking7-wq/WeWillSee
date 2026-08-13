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
