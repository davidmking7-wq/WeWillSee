# Stock Scout

Run the **/stock-scout** skill in Claude Code (it lives in
`.claude/skills/stock-scout/`). It:

1. Re-prices every past pick in `picks.xlsx` — marks HITs (touched +5%
   within ~2 months) and MISSes, and updates the scoreboard, so the tool's
   real track record is always visible next to its predictions.
2. Scans the S&P 500 for stocks with the strongest evidence-based pattern
   for gaining **at least +5%** within 42 trading days (12-1 and 6-1
   momentum, 52-week-high proximity, smooth-path tilt, near-breakout,
   volume-surge gaps — with trend gates, absolute-momentum gate, and
   overheating/lottery vetoes), then ranks them by
   **OppScore = P(+5%) × typical max gain × speed to +5% × (1 − P(−5% first))**
   — assurance × profit × speed × safety, all measured from 10 years of
   similar stocks (same score bucket, volatility group, market regime).
3. Quotes honesty-first reliability and growth: predicted growth % (median
   2-month result and typical max gain), P(+5%) and P(+10%) calibrated on 10
   years **next to the base rate** (in good markets most stocks touch +5%
   anyway — beating the base rate is the whole game), a confidence range,
   and P(the stock drops -5% first).
4. Web-researches the finalists (earnings dates inside the window, pending
   binary events, news) and only ever *downgrades* grades based on findings.
5. Appends the final 3-5 picks to `picks.xlsx`.

It never buys anything. It is a research scorecard, not financial advice.

## Signal engine: v3

The scanner runs the v3 engine (see `SCOUT-DESIGN.md` for the full lineage
and the ablation record). On the 2014-2017 monthly census (38 entry dates):
v1 hit 56.3% with +4.01% per window; v3 hits 61.1% with +4.63%, beating the
equal-weight market (+1.78%) in ~4 of 5 windows, median winner in ~16 days.
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
```

(Use `.venv/bin/python` / `.venv\Scripts\python` if you set up a venv.)

Key files: `scout/` (engine), `picks.xlsx` (the scorecard you open),
`scout/calibration.json` (probability tables, generated),
`SCOUT-DESIGN.md` (method + its honest limits), `SETUP.md` (install).
