# Final test data handoff

Generated 2026-08-10. This file is the short, durable explanation of the raw
JSON and CSV files beside it. It is research evidence, not a promise and not
permission to trade live money.

## Bottom line

The corrected stock scanner did not beat the market. Its best version grew
124.4% in the non-overlapping historical simulation while one continuous SPY
holding grew 250.5%. The scanner also fell 41.3% from peak to trough. It must
remain disabled as an executor.

Of the three separately locked follow-up paths, only diversified trend passed
its historical gate. That is permission to start a frozen paper test, not proof
that it will beat SPY in practice. The two other paths do not have the full
locked date range and are DATA_INCONCLUSIVE. The locked low-news idea could not
be run honestly with the available historical news and membership data.

## Fresh corrected stock-scanner test

- Raw result: `scout/backtest_results.json`
- Audit result: `experiments/results/backtest_audit_sp500.json`
- Engine source commit recorded by the final artifact: `2b8e209`
- Market data: adjusted Alpaca SIP daily bars
- Requested coverage: 504 symbols
- Returned coverage: 504 symbols (100%)
- Batch recovery: DOW was omitted from the large batch and successfully
  recovered by an automatic one-symbol retry
- Missing symbols after recovery: none
- Bar span: 2016-06-13 through 2026-08-07
- Signal span: 2017-07-10 through 2026-05-18
- Rule: five picks approximately every 21 trading days, held 42 trading days
- Entry: next trading day's open after the completed signal close
- Trading friction: 5 bps full spread plus 5 bps slippage per side, for an
  estimated 15 bps round trip; zero commission was assumed
- Missing filled position: conservative total-loss rule
- Headline comparison: one continuous SPY entry and one final exit

### v5 results

| Measurement | Result |
|---|---:|
| Entry dates | 105 |
| Reached +5% within 42 days | 60.8% |
| Reached +10% | 36.6% |
| Reached +15% | 17.9% |
| Average return at day 42 | +2.12% |
| Average best point inside window | +8.97% |
| Median days to first +5% | 15 |
| Fell 5% before reaching +5% | 48.2% |
| Beat equal-weight market window | 50 of 105 |
| Beat SPY window | 48 of 105 |

### Honest non-overlapping growth comparison

| Measurement | Result |
|---|---:|
| Independent-ish windows | 53 |
| v5 scanner growth | +124.4% |
| Continuous SPY growth | +250.5% |
| SPY advantage | +126.0 percentage points |
| Equal-weight market with window resets | +240.9% |
| v5 daily maximum drawdown | -41.3% |

Verdict: FAIL. The scanner made money historically but did much worse than the
simple market holding, with a deep fall along the way.

## Lie-detector verdict

| Check | Result | Plain meaning |
|---|---|---|
| Data coverage | PASS | All 504 names returned after one automatic individual retry |
| Registered-trial count | PASS | At least 117 prior hypothesis rows were counted |
| Start-date sensitivity | PASS | Six starting schedules varied by 1.48 points |
| Missing/delisted selected positions | PASS | No selected leg vanished or was silently dropped in this run |
| Training/test separation | FAIL | Two training outcomes extended into the test period |
| Random-pick comparison | FAIL | Return beat 73% and hit rate beat 91.5% of random controls; not strong enough for the locked bar |
| Trading friction and SPY | FAIL | Friction reduced results by 18.57 points and net growth lagged SPY by 126.04 points |
| Current-member bias | WARN | Current-member average differed from the older point-in-time artifact by +0.65 points per window |

The old point-in-time artifact uses pre-correction assumptions, so its bias
number is only a warning until that universe is rerun with the corrected code.

## Three preregistered follow-up paths

Raw monthly data, all cases, source hashes, and formulas are in:

- `experiments/results/candidate_paths_monthly.csv`
- `experiments/results/candidate_paths_results.json`
- `experiments/results/candidate_paths_report.md`

### P1 — diversified trend

Simple description: follow long price trends across commodities, stock-index
futures, bonds, and currencies instead of trying to choose individual stocks.

- Status: PASS_LOCKED_HISTORICAL
- Full period: 1991-01 through 2026-05
- Historical annual growth: 8.58%
- Historical Sharpe: 0.838
- Worst historical drawdown: -23.18%
- 2010+ annual growth: only 3.09%

Pros: many different markets; little dependence on one company; passed the
locked historical checks even under the alternative cost reading.

Cons: recent returns were weak; the test uses research-factor returns rather
than broker fills; a practical version needs futures or a managed-futures fund;
it has not passed a live paper period.

### P2 — global value/quality/momentum long-short mix

Simple description: own groups of cheap, profitable, improving winners and
short the opposite groups in four world regions.

- Status: DATA_INCONCLUSIVE
- Actual start: 1993-11, 34 months later than the locked start
- With trading friction scaled to actual exposure, only 68.07% of overlapping
  five-year windows were positive, below the locked 70% bar

Pros: spreads risk across regions and several different ideas.

Cons: missing locked history; costly and complicated short positions; heavy
turnover and borrowing; the apparent pass depended on how costs were applied.

### P3 — market core plus P1 and P2

Simple description: keep the broad market, then add half-sized trend and
long-short return engines.

- Status: DATA_INCONCLUSIVE
- Actual start: 1996-11, 70 months later than the locked start
- Available-subset annual advantage: 7.56 points, below the locked 8-point
  landslide label
- 2010+ stress advantage becomes -0.49 points with proportional trading
  friction and -0.36 points with fuller borrowing-cost treatment

Pros: the most direct attempt to keep market growth while adding two different
sources of return.

Cons: inherits P2's missing data; uses leverage and shorting; recent advantage
disappears under tougher, realistic readings of costs.

## Locked low-news validation

The H33 rule was frozen before external data work. It was not run because the
available GDELT archive cannot prove exact before-close publication timing and
has thousands of missing 15-minute files. Historical index-membership and dead
company coverage also require stronger paid data. Its correct status is
DATA_INCONCLUSIVE, not a win or a loss. Details are in
`validation_protocol/DATA_SOURCE_BLOCKERS.md`.

## What can honestly move forward

Only P1 may enter a frozen paper observation. Use at least six months; twelve
months is the default. Do not change the rule after seeing results. P2, P3, H33,
and the stock scanner must not be promoted unless their stated data problems
are fixed and a new protocol is locked before another result is viewed.
