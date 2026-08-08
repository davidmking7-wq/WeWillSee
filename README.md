# Stock Scout

Run the **/stock-scout** skill in Claude Code (it lives in
`.claude/skills/stock-scout/`). It:

1. Re-prices every past pick in `picks.xlsx` — marks HITs (touched +5%
   within ~2 months) and MISSes, and updates the scoreboard, so the tool's
   real track record is always visible next to its predictions.
2. Scans the S&P 500 for stocks with the strongest evidence-based pattern
   for gaining **at least +5%** within 42 trading days (12-1 and 6-1
   momentum, 52-week-high proximity, smooth-path tilt, near-breakout — with
   trend gates, absolute-momentum gate, and overheating/lottery vetoes),
   then ranks them by
   **OppScore = P(+5%) × average peak gain × speed to +5% × (1 − P(−5% first))**
   — assurance × profit × speed × safety, all measured from 10 years of
   similar stocks (same score bucket, volatility group, market regime).
   **+5% is the minimum bar, not the goal**: the profit term is the AVERAGE
   peak (fat right tails earn rank), P(+10%)/P(+15%) are quoted, and winning
   picks keep being re-priced until their deadline so the scorecard shows
   how far they actually ran.
   The scan also fetches each candidate's **next earnings date**; a report
   inside the window auto-downgrades the pick's confidence one notch.
3. Quotes honesty-first reliability and growth: predicted growth % (median
   2-month result and typical max gain), P(+5%) and P(+10%) calibrated on 10
   years **next to the base rate** (in good markets most stocks touch +5%
   anyway — beating the base rate is the whole game), a confidence range,
   and P(the stock drops -5% first).
4. Web-researches the finalists (earnings dates inside the window, pending
   binary events, news) and only ever *downgrades* grades based on findings.
5. Appends the final 3-5 picks to `picks.xlsx`.

It never buys anything. It is a research scorecard, not financial advice.

## Signal engine: v4

The scanner runs the v4 engine, selected by a train/holdout protocol on
2016-2026 data (see `SCOUT-DESIGN.md` for lineage and `BACKTEST-REPORT.md`
for the full validation, including the S&P 500 comparison). On 107 monthly
entries 2017-2026: v4 hits +5% on 61.9% of picks (v1: 59.3%), reaches +10%
on 37.1% (v1: 33.1%), median 15 days to +5%, with fewer -5%-first dips.

**Honesty headline from the backtest:** the scout does NOT beat buy-and-hold
SPY on compounded returns — its edge is first-passage odds, speed and path
safety for 2-month swing ideas, not index outperformance. The report says
this plainly; so should you.

Every pick row, scan and calibration is stamped with its engine version so
track records never mix engines: pre-switch picks stay scored as `v1`.
Changing `scout/signals.py` requires bumping `config.ENGINE` — the
calibration cache is engine-tagged and rebuilds itself on mismatch, so new
signals can never silently reuse probability tables fitted to old rankings.

Manual CLI (same thing the skill drives), from the repo root:

```
python -m scout.cli update      # re-price past picks
python -m scout.cli scan        # score the universe
python -m scout.cli record scout/final_picks.json
python -m scout.cli calibrate   # force recalibration
python -m scout.backtest        # regenerate the engine-vs-SPY validation
python -m scout.labtest --variant ...   # research harness for future engine ideas
```

(Use `.venv/bin/python` / `.venv\Scripts\python` if you set up a venv.)

Key files: `scout/` (engine), `picks.xlsx` (the scorecard you open),
`scout/calibration.json` (probability tables, generated),
`SCOUT-DESIGN.md` (method + its honest limits), `BACKTEST-REPORT.md`
(the validation), `SETUP.md` (install).
