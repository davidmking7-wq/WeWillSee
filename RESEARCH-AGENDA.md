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

Data debt to settle before trusting any new small-cap result: one month
of a delisting-inclusive dataset to re-run the S&P 1500 headline once —
our own PIT test proved ~1pp/window of mirage in large caps; small caps
are worse.

## The honest bottom line

Faster is not available: the profit physically accrues in weeks 4–8 and
cannot be harvested early. Bigger is available only in increments — a
disciplined year of the ranked program above might add 2–6 points a year
on top of the current engine, each increment fought for with the method
in section 1. Anyone offering more than that is selling something.
