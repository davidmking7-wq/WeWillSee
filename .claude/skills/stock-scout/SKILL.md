---
name: stock-scout
description: Scan the S&P 500 for the best 1-2 month picks expecting +5% upside, with calibrated reliability stats; updates the picks.xlsx scorecard with past and current picks. Use when the user asks for stock picks, short-term ideas, or to run/update their stock scout.
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
It never buys anything.

The signal engine is **v4** (`config.ENGINE`); every scan, calibration and
recorded pick is engine-stamped. See `SCOUT-DESIGN.md` for lineage and
`BACKTEST-REPORT.md` for validation — including its honest limit: the tool
does NOT beat buy-and-hold SPY; its edge is chance × speed × path-safety
for 2-month ideas. Never present it as market-beating.

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

**If `crash_risk` is true** (bear market + high volatility — the regime where
momentum historically inverts): report that, recommend zero picks this cycle,
and skip to Phase 5 unless the user explicitly wants picks anyway (then all
grades are C and the report must say why).

The v3 engine's extra gates (positive 6-month return, no lottery spikes)
thin the candidate pool in rough markets — a short candidate list is honest,
not a failure.

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
   (upgrades/target raises vs cuts).
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
2. **Biggest Gain — top 3**: the first 3 research-cleared symbols in
   `big_gain_order` (gain-weighted ranking; only stocks with Chance +5%
   ≥ 62% qualify). If fewer than 3 qualify — or none — say so honestly in
   the report; never pad the list with ineligible stocks.

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

Appends the picks to `picks.xlsx` (engine-stamped v3) and rebuilds the
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
   Then the selling rules, once, plainly (they are per-pick in the "Sell
   Signal" column and each candidate's `sell_if`): ordinary stop-losses
   tested WORSE — the three rules that survived ten years of testing are
   (1) a -15% disaster stop (close 15% below the buy price → sell, the
   pattern is broken; exists to cap catastrophes, not add return),
   (2) otherwise sell at the deadline, and (3) once a pick touches +5%,
   protect it — sell if it closes back at breakeven or 8% below its best
   close (whichever is higher). Every `update` run refreshes the live
   levels and flags any pick whose signal says SELL — surface those
   prominently.
3. **Mandatory context line** (never omit): the regime base rate — e.g.
   "Right now X% of eligible S&P stocks touch +5% in 2 months anyway; these
   picks historically did it Y% of the time (lift Z)." A 65% P(hit) in a bull
   market is mostly base rate, and the user must see that.
4. The caveats from `last_scan.json`, briefly, plus: research scorecard, not
   financial advice; nothing was bought; and (from BACKTEST-REPORT.md) the
   tool historically does NOT beat buy-and-hold SPY — its value is finding
   likely-fast +5%+ movers with a safer path, not index outperformance.
5. Mention `picks.xlsx` was updated (send it with SendUserFile if available).

## Failure notes

- Alpaca keys live in `.env` at the repo root; data-only usage. If auth
  fails, tell the user to create/rotate keys per `SETUP.md` — don't ask
  them to paste keys into chat.
- If the universe/calibration fetch fails, the CLI falls back to cached
  files; note their age in the report.
- Never buy anything, never upgrade a grade, never edit
  `scout/calibration.json` by hand.
- Never tune signal weights or thresholds against the calibration panel
  (data snooping — see SCOUT-DESIGN.md). Engine changes require bumping
  `config.ENGINE` and a from-scratch recalibration (automatic).
