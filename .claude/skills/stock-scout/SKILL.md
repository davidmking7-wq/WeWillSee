---
name: stock-scout
description: Research S&P 1500 stocks for 1-2 month +5% candidates, with calibrated historical stats; updates the picks.xlsx research scorecard with past and current picks. Use when the user asks for stock ideas or to run/update their stock scout.
---

# Stock Scout

Research tool in this repository (the `scout/` package). It finds S&P 500
stocks with the strongest evidence-based pattern for gaining **at least +5%**
within 42 trading days (~2 months) and ranks them by
**OppScore = P(+5%) × average peak gain × speed to +5% × (1 − P(−5% first))**
— assurance × profit × speed × safety, every factor an empirical stat from 10
years of similar stocks (same score bucket, volatility group, market regime).
**+5% is the minimum bar, not the goal** — the ranking's profit term is the
average peak gain (big runners earn rank), P(+10%) and P(+15%) are quoted,
and HIT picks keep being re-priced until their deadline. It quotes calibrated
probabilities with honest uncertainty and keeps a running scorecard in
`picks.xlsx` (predicted growth % AND realized growth % per pick).
It never buys anything. This repository has no broker-order path; the rejected
weekly executor remains excluded and disabled.

This is research only. A paper-forward signal is frozen after the market
closes, the next trading day's open is its reference entry, and the cost
assumption written before the test is applied to every result. Never use the
signal-day close as a forward fill. No strategy becomes current behavior until
it passes the frozen paper-forward gate and the `main` merge gate in
`FORWARD-TEST.md`. Passing those gates still does not allow live execution.

The signal engine is **v5** (`config.ENGINE`) over the **S&P 1500** —
large caps plus mid/small caps, where under-the-radar candidates live;
each candidate carries a `segment` (large/mid/small — mention it for
non-large picks, users like knowing a name is off the beaten path). Every
scan, calibration and recorded pick is engine-stamped. See
`SCOUT-DESIGN.md` for lineage and `BACKTEST-REPORT.md` for validation —
including the point-in-time survivorship correction and its honest limit:
the tool does NOT beat buy-and-hold SPY. It measures chance, speed, and path
safety for 2-month ideas, but those measurements have not produced extra
return over SPY. Never present it as market-beating.

Run commands from the repo root. Use the project venv's python if present
(`.venv/bin/python`, on Windows `.venv\Scripts\python`), else `python3`.
Requires `.env` with Alpaca data keys (see `SETUP.md`).

Run all five phases in order, every time.

## Phase 1 — Update past picks

```
python -m scout.cli update
```

Re-prices every OPEN pick, marks HITs (+5% close reached before the
Deadline) and MISSes, rebuilds the Track Record sheet. HIT picks keep
being re-priced until their Deadline (5% is the minimum, not the goal —
"Best So Far %" shows how far winners actually ran). Note any newly
resolved picks for the final report. "no OPEN picks to update" is fine on
early runs. Older workbook rows without an Engine label are auto-stamped
"v1" — that is correct, leave them.

## Phase 2 — Quant scan

```
python -m scout.cli scan
```

May take a few minutes when it (re)builds the calibration — first run after
an engine change always rebuilds from scratch (10 years of data); tell the
user if so. Then read `scout/last_scan.json`.

**If `crash_risk` is true** (bear market + high volatility): report it and
set expectations DOWN — crash-flagged windows historically averaged +0.5%
per window against +5.6% otherwise, and only 29% of them reached +5%. Do
NOT recommend sitting the cycle out: that was tested directly
(hypotheses.md H5a) and cost return, because those windows are dull, not
dangerous — their worst was −8.3%, and none of the portfolio's five worst
windows was crash-flagged. Grades cap at B while the flag is on, and the
report must say plainly that the odds are near the base rate this cycle.

The engine's extra gates (positive 6-month return, no lottery spikes)
thin the candidate pool in rough markets — a short candidate list is honest,
not a failure. Earnings policy (from REAL SEC EDGAR dates, train AND
holdout — see BACKTEST-REPORT.md): an earnings date INSIDE the window is
historically the BETTER cohort (the catalyst ahead drives the +5% move) —
never treat it as a reason to skip; note the date and size the risk in
research. The genuinely weak cohort is stocks that JUST reported (within
~2 weeks before the scan) — their catalyst is spent, they hit ~40-47% vs
~62%; the scan pushes them to the bottom of both lists and downgrades
their grade. Don't rescue one into the top 3. Also give defensive-sector
picks (Consumer Staples especially) extra research scrutiny: the engine's
pattern historically performs worst there (a mechanical exclusion tested
as a wash, so it's research color, not a rule).

## Phase 3 — Research the candidates

Web-research the top ~10 candidates from `last_scan.json` (parallel subagents
work well — one per 3-4 tickers). For each, find:

1. **Next earnings date.** The scan already fetched these best-effort:
   each candidate has `earnings_date` / `earnings_in_window`, and in-window
   candidates arrive with their grade ALREADY downgraded one notch. Your job
   is to VERIFY the flagged dates (sources drift) and to fill the gaps — if
   the scan's `earnings_checked` is false or a candidate's date is null, do
   the web lookup yourself. A verified in-window earnings date must be
   mentioned in the thesis; never un-downgrade.
2. **Pending binary events**: M&A involvement, FDA/court decisions, guidance
   withdrawals, investigations. Any found → downgrade, or drop the ticker.
3. **News tone last 2-4 weeks** and **direction of analyst revisions**
   (upgrades/target raises vs cuts). While checking news, note any recent
   INSIDER BUYING (open-market purchases by officers/directors — rare on
   momentum names and historically excellent when present: 69% hit,
   +6.9% avg, zero tail in our sample, though n is small). Mention it in
   the thesis as a plus. Do NOT penalize insider selling — heavy selling
   into strength tested as profit-taking noise, not a warning
   (sell-cluster picks actually performed BETTER; see scout/hypotheses.md).
4. **Corrected analyst target** (12-month view, context + tie-break only —
   never the primary ranking; raw target levels are a documented trap: the
   highest-claimed-upside stocks historically perform WORST). For each
   finalist find the freshest consensus target (mean AND median), analyst
   count, and low-high range, then:
   - claimed upside % = 100 × (consensus / price − 1)
   - **corrected guess % = 5 + 0.22 × claimed upside** (research-backed
     deflate-then-shrink; analysts overshoot ~7-12pp on US large caps)
   - **Mark "n/r"** (not reliable) if targets are scattered — range wider
     than ~60% of the price — or the mean is dragged by stale pre-rerating
     targets (median far from mean). Scattered targets predict *negatively*.
   - **Red flag → downgrade**: claimed upside > 40% with wide dispersion
     (usually stale targets after bad news, not genuine upside).
   - A negative claimed upside alone is NOT a downgrade (analyst
     "overvalued" claims have no predictive value) — but note it.
   - Among stocks with reliable numbers, use the corrected-guess rank as
     the FINAL tie-break after the quant ordering.

Select TWO lists (a stock may appear in both — mark it "both"):

1. **Best Overall — top 3**: the first 3 research-cleared symbols in the
   scan's `overall_order` (balanced chance × gain × speed × safety).
   **These are the candidates, not a prescribed portfolio size.** The
   claim that a 2-3 name book was the best configuration came from a
   backtest that sampled one entry schedule; pooled across all six
   schedules (BACKTEST-REPORT.md, Round 2), every book size from 1 to 8
   returns the same ~+2% per window, and concentration changes only the
   dispersion — top-1 swings 5.4pp between schedules and draws down 48%,
   top-8 swings 1.7pp and draws down 30%. So: report the ordering, say
   that a smaller book means a wider range of outcomes rather than a
   higher expected return, and let the user choose. Never tell them
   concentration earns more.
2. **Biggest Gain — top 3**: the first 3 research-cleared symbols in
   `big_gain_order` (gain-weighted ranking; only stocks with Chance +5%
   ≥ 62% qualify). If fewer than 3 qualify — or none — say so honestly in
   the report; never pad the list with ineligible stocks. This list is
   CONTEXT and alternatives — not a second portfolio and not a reason to
   increase concentration.

"Research-cleared" = no unresearchable red flag; dropped stocks are replaced
by the next in that same order. Write `scout/final_picks.json`:

```json
[{"symbol": "XYZ", "grade": "B", "list": "overall|big_gain|both",
  "analyst_guess_corrected": 7.9,
  "thesis": "2-3 sentences: why the pattern is strong, what the research
             found, and the main risk. Mention earnings date if inside."}]
```

`analyst_guess_corrected` is the corrected 12-month guess from step 4 (a
number in percent, or the string "n/r").

`grade` starts from the scan's `grade_quant`, only ever downgraded by
research, never upgraded.

## Phase 4 — Record

```
python -m scout.cli record scout/final_picks.json
```

Appends the picks to `picks.xlsx` (stamped with `config.ENGINE`) and rebuilds the
Track Record.

## Phase 5 — Report to the user

Show, in plain language (the user prefers no jargon):

1. Any past picks resolved this run (HIT/MISS) and the current overall
   hit-rate from the Track Record vs the average predicted P — that's the
   tool's real track record. If both v1 and v3 picks exist, mention the
   per-engine split (the Track Record sheet has a "By engine" section).
2. TWO tables in plain words. "Best Overall (top 3)": Stock | Price | Chance
   of +5% | Chance of +10% | Usual peak gain | Days it usually takes |
   Chance of a -5% dip first | Confidence | one-line why (note earnings
   date if inside the window). Then "Biggest Gain (top 3, only 62%+
   chance)": same columns ordered by gain. Explain once, simply: 5% is only
   the minimum bar — the overall list balances chance × gain size × speed ×
   safety; the gain list chases the biggest average peaks among stocks
   still clearing the 62% chance bar.
   Then the selling rules, once, plainly — they are PER-STOCK (each pick's
   own dollar levels live in the "Sell Signal" and "Sell Below (Disaster)"
   columns and each candidate's `sell_if`): ordinary stop-losses tested
   WORSE — what survived ten years of testing is (1) a disaster stop sized
   to the stock: a close below 2x that stock's own normal 2-month move
   under the buy price → sell, the pattern is broken (calm stocks get
   tight levels, lively ones get room). Be honest about what it is: at
   portfolio level it fired on 3 of 108 positions in ten years — real
   catastrophe insurance, not a return booster. And (2) otherwise sell at
   the deadline. Every `update` run refreshes the research levels and flags
   any pick whose simulated signal says SELL — surface those prominently.
   **The old rule "once a pick touches +5%, never let it become a loss"
   is NO LONGER a rule** — tested at portfolio level it cut compounded
   return by about a third (hypotheses.md H6c), because momentum names
   routinely dip back through the entry price and then run. Do not recommend
   or offer this rejected rule as an optional exit. Mention it only as a
   historical retraction if the user asks about the old rule.
3. **Mandatory context line** (never omit): the regime base rate — e.g.
   "Right now X% of eligible S&P stocks touch +5% in 2 months anyway; these
   picks historically did it Y% of the time (lift Z)." A 65% P(hit) in a bull
   market is mostly base rate, and the user must see that.
   Then the **portfolio goal tracker** (the user's stated goal is +5%+ per
   1-2 months on the whole portfolio). Use the CORRECTED numbers from
   BACKTEST-REPORT.md Round 2 — pooled across every entry schedule, not
   the old single-schedule headline: the historical pooled estimate was
   roughly **+2% per 42-day window**, not a forecast or promise, with ≥+5%
   landing in **40-47%** of windows (never all of
   them — nothing documented achieves that), a worst window around
   **−18% to −25%**, multi-window losing streaks, and **no reliable edge
   over simply holding SPY** (+2.5%/window on the same decade). The
   scorecard's useful output is its measured chance, speed, and path, not a
   claim that it compounds faster. If discussing the historical entry-date
   study, explain that splitting observations across two dates did not raise
   the average; it only reduced dependence on one lucky start date. Do not
   turn that research control into allocation advice.
   Never suggest profit targets, static leverage, or 1-stock
   concentration to force the number (each is documented to destroy the
   edge or add only dispersion).
4. The caveats from `last_scan.json`, briefly, plus: research scorecard, not
   financial advice; nothing was bought; and (from BACKTEST-REPORT.md) the
   tool historically does NOT beat buy-and-hold SPY. It reports measured
   chance, speed, and path; it does not promise index outperformance.
5. **The paper-entry rule, in bold, every run:** this is not a buy
   instruction. Freeze the signal after the market closes and use the next
   trading day's OPEN as the paper reference entry. Never backfill the
   signal-day close or skip a gap after seeing it. State the transaction-cost
   assumption in the frozen forward-test contract and apply it to every
   result. The strategy remains experimental unless it passes both gates in
   `FORWARD-TEST.md`, and the repository never places an order.
6. **Insider buying, when present** (the scan checks real SEC Form 4
   filings automatically): if a candidate's `insider_buyers` > 0, say so
   prominently — officers/directors buying their own stock before a pick
   is rare and was historically excellent (69% hit, +6.9% avg, zero
   disasters in our sample; small sample, so a plus, not a promise). It
   also lands in the workbook's "Insider Buys" column. Never treat
   insider SELLING as a warning — tested as profit-taking noise.
   (An ML second-opinion feature was built, tested as a selector, found
   to REDUCE returns, and removed at the user's request — see
   scout/hypotheses.md H3/H3b; don't rebuild it.)
7. Mention `picks.xlsx` was updated (send it with SendUserFile if available).

## Failure notes

- Alpaca keys live in `.env` at the repo root; data-only usage. If auth
  fails, tell the user to create/rotate keys per `SETUP.md` — don't ask
  them to paste keys into chat.
- If the universe/calibration fetch fails, the CLI falls back to cached
  files; note their age in the report.
- Never buy anything, never upgrade a grade, never edit
  `scout/calibration.json` by hand. Do not add a broker-order path; the
  rejected weekly executor stays excluded and disabled.
- A ranking, probability, portfolio, entry, or exit change must pass the
  frozen paper-forward test and `main` merge gate in `FORWARD-TEST.md` before
  it can become current research behavior. A pass never authorizes live use.
- Never tune signal weights or thresholds against the calibration panel
  (data snooping — see SCOUT-DESIGN.md). Engine changes require bumping
  `config.ENGINE` and a from-scratch recalibration (automatic).
