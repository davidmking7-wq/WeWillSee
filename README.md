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
5. Appends the final picks to `picks.xlsx`. **The recommended portfolio
   is the top 2-3 of the Best Overall list** — the concentration level
   the portfolio lab found best for the +5%-per-window goal (avg +2.5 to
   +4.5% per window historically; see BACKTEST-REPORT.md); the Biggest
   Gain list is context and alternatives, not extra positions.

It never buys anything. It is a research scorecard, not financial advice.

## Signal engine: v5, universe: S&P 1500

The scanner runs the v5 engine (v4 signals + a tradeable-liquidity gate)
over the **S&P 1500** — large caps plus the MidCap 400 and SmallCap 600,
where under-the-radar candidates live; every pick is segment-labeled.
See `SCOUT-DESIGN.md` for lineage and `BACKTEST-REPORT.md` for the full
validation, including a **point-in-time S&P 500 test** (each date's actual
members, delisted stocks included) that quantifies survivorship bias, and
the S&P 1500 test where the engine reaches 63.6% hit rate with far more
+10%/+15% runners and compounds even with SPY buy-and-hold.

**Honesty headline:** on the survivorship-corrected test the scout still
does not beat buy-and-hold SPY on compounded returns — its edge is
first-passage odds, speed and path safety for 2-month swing ideas, and it
now beats the honest equal-weight market in a majority of windows. The
report says this plainly; so should you.

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

## Beyond stock picking: `ALPHA-STACK.md`

The backtests in this repo say the selection layer adds no return at any
horizon tested — the composite's best-ranked decile is its worst, and the
gates are a defensiveness overlay. **ALPHA-STACK.md** takes that seriously
and asks where an edge can legitimately come from instead, working from

```
g = mu - sigma^2/2      L* = mu/sigma^2      g(L*) = S^2/2
```

Growth is quadratic in Sharpe, and Sharpe is bought with weakly-correlated
sleeves rather than with better forecasts.

**It was built, tested on 2016-2026, and it lost.** Projected stacked Sharpe
0.73; measured **0.40 against SPY's 0.76**. The sleeves turned out correlated
(0.67 between trend and cross-sectional momentum; effective bets 1.02 of 4),
which was the pre-registered failure condition. Volatility targeting improved
drawdown but not return consistently; fractional Kelly worked mechanically
and still lost, because leverage scales an edge and cannot create one. See
BACKTEST-REPORT.md "The alpha stack" and `scout/hypotheses.md` H9-H14.

What survives is the diagnosis and the toolkit, not the trade.

```
python -m scout.growth_selftest          # 51 checks, no API keys needed
python -m scout.agenda_rank              # which project is worth building
python -m scout.sleeve_lab --synthetic-null   # the lab's own control
python -m scout.sleeve_lab               # the real experiment (needs keys)
```

`scout/growth.py` holds the formulas (Kelly and the drawdown-constrained
fraction, Fernholz's excess growth rate, Ledoit-Wolf shrinkage, HRP, Meucci
effective bets, EWMAC trend, Kalman beta, deflated Sharpe, Wald's SPRT).
Hypotheses H9-H14 in `scout/hypotheses.md` were registered before the lab
ran, including the one already showing evidence against it.

(Use `.venv/bin/python` / `.venv\Scripts\python` if you set up a venv.)

Key files: `scout/` (engine), `picks.xlsx` (the scorecard you open),
`scout/calibration.json` (probability tables, generated),
`SCOUT-DESIGN.md` (method + its honest limits), `BACKTEST-REPORT.md`
(the validation), `SETUP.md` (install).
