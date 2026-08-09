# Forward test and `main` merge gate

## Current status

No strategy in this repository has beaten SPY, and no strategy is approved for
live execution. The repository is a research scorecard. The rejected weekly
executor is deliberately excluded and disabled.

“Paper-only” here means hypothetical positions recorded before the outcome is
known. They may be mirrored manually in an isolated broker paper account, but
this repository does not submit those orders. Never connect this workflow to a
live account.

## Why this gate exists

Several ideas looked strong in old data and then failed a more honest check:

- the apparent +733% result was the luckiest of six valid start schedules;
- the top-2/3 concentration advantage disappeared when all schedules were used;
- the breakeven-after-+5% rule cut compounded return by about one third;
- the automatic crash sit-out rule reduced return;
- no completed selection or portfolio test beat SPY.

A backtest can suggest what to test. It cannot approve a change by itself.

## Gate 1: frozen paper-forward test

Before the first forward observation, add a short contract to the hypothesis
registry or the candidate pull request. It must state:

1. the exact rule being tested and the engine/version that produces it;
2. the one result it claims to improve;
3. the benchmark or control it must beat;
4. trading-cost and missing-data treatment;
5. the minimum number of completed observations and test end date;
6. the numeric pass, fail, and inconclusive rules.

Then run the test under these rules:

1. Record every scan, candidate, reference price, and deadline before its
   future result is known.
2. Do not edit, skip, or replace an observation after seeing what happens.
3. Keep the code and settings frozen. A change starts a new version and a new
   forward test; it does not rewrite the current one.
4. Wait for each full 42-trading-day window unless the registered rule has a
   different horizon. Partial windows do not count as wins.
5. Compare against SPY and the relevant base-rate/random control on the same
   dates. A return claim must beat SPY after stated costs; a narrower claim
   must pass the exact metric written in the contract.
6. Publish every result, including failures, missing prices, and delistings.

The minimum calendar span is **six months**, with **twelve months the default**.
There is no early PASS because the first few observations look good. If the
frozen contract requires more time or more completed outcomes, that longer gate
wins; six or twelve months is then only an interim checkpoint. A valid failure
may be recorded when its prewritten failure condition is met, but the rule may
not be replaced mid-test.

Possible outcomes are **PASS**, **FAIL**, or **INCONCLUSIVE**. Only PASS can
proceed to the next gate. “Promising” is not PASS.

## Gate 2: promotion to `main`

A change that affects rankings, quoted probabilities, portfolio weights, or
sell guidance may become current `main` behavior only when its pull request
contains all of the following:

- the registered hypothesis and frozen forward-test contract;
- the completed paper-forward report with every observation;
- the existing honest backtests, including point-in-time data where available,
  all entry phases, SPY, appropriate controls, and stated costs;
- targeted tests or an independent reproduction of the changed calculation;
- an explicit list of data problems and remaining uncertainty;
- updates to `README.md`, `SCOUT-DESIGN.md`, `STATE.md`, and
  `BACKTEST-REPORT.md`, including any retraction the new result requires;
- confirmation that no broker-order or live-execution path was added.

Documentation, tests, and bug fixes that cannot alter research outputs may use
the normal review process. A new idea may also merge as a clearly disabled lab,
but it must not change current recommendations or be described as validated.

Passing both gates permits a research-code change only. Live execution remains
out of scope and prohibited.
