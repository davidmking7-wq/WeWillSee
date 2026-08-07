# Stock Scout — design & progress

Durable state for the project. If context is lost, resume from here.

## What this is

A **user-invoked skill** `/stock-scout` (no auto-buying, research only):
1. Finds best short-term picks — **1–2 month horizon, expecting ≥5% upside**
   (5% is the MINIMUM bar, not the target).
2. States **how good/reliable each assessment is** (empirical probability +
   grade, always next to the base rate).
3. Writes past + current picks to **picks.xlsx**, updated every run
   (past picks re-priced, marked HIT/MISS, scoreboard of hit-rate).

Label definition (verbatim, used everywhere):
**HIT = max close over the next 42 trading days ≥ entry close × 1.05**
(first-passage; entry = close on the scan date, window starts the next day).

## Architecture

- `scout/` package (Python 3.11+, Alpaca keys in `.env` at repo root):
  - `universe.py` — current S&P 500 constituents cached in `scout/universe.csv`,
    refreshed when >60 days old.
  - `data.py` — Alpaca **SIP feed** daily bars (free for history >15 min old),
    adjustment=all — consolidated closes + real volume (IEX is ~2.5% of tape).
  - `signals.py` — the signal engine (versioned via `config.ENGINE`).
  - `calibrate.py` — walk-forward history: at each past non-overlapping
    42-day step, score the universe and measure what happened. Cells =
    score bucket × volatility tercile × regime (SPY above/below 200d SMA).
    Cache `scout/calibration.json`, engine-tagged, refreshed monthly.
  - `excel_book.py` — `picks.xlsx`: sheets Picks / Track Record / How To
    Read This, all plain language; every row engine-stamped.
  - `cli.py` — `update` / `scan` / `record final_picks.json` / `calibrate`.
- Skill: `.claude/skills/stock-scout/SKILL.md` orchestrates:
  update → scan → Claude web-researches top candidates → pick final lists,
  write theses, downgrade grades on red flags → record → report.

## Statistical honesty (v2 foundations, kept in every version)

- Non-overlapping 42-day windows since 2016; **cluster bootstrap by date**
  for CIs (same-date outcomes are correlated); n_eff from bootstrap
  variance; bucket P **shrunk toward regime base rate** (K=20); cells with
  n_eff<20 refuse to quote P ("n/q"); companion stats P(-5% first),
  median & 5th-pct day-42 return.
- Regime: bull/bear by SPY 200d; **crash flag** = bear + SPY 21d vol > q80
  → skill recommends zero picks (momentum-crash state).
- Known limits (documented in Excel About + report caveats): survivorship
  (today's constituents applied historically), single macro era 2016-2026,
  ~3 bear episodes. Rely on **lift over base rate**, not raw P.
- Key empirical finding (v2): composite rank shows ~no lift over the gated
  base rate in bull regimes; the honest edge = the gates' quality/asymmetry,
  crash-regime avoidance, the event-research overlay, and the tracked
  scoreboard — never oversell P(hit).

## Ranking (v3 scoring model, unchanged since)

- **OppScore = 1000 × P(+5%) × med max gain × (42 / med days to +5%)
  × (1 − P(−5% first))** — assurance × profit × speed × safety. Fixed
  ex-ante formula over empirical cells (no fitting).
- Two lists, 3 picks each: **Best Overall** (OppScore order) and **Biggest
  Gain** — GainScore = 1000 × usual peak × P(+10%), eligibility floor
  P(+5%) ≥ 62% (`config.GAIN_MIN_P5`), within-cell tie-break by stock
  volatility. The gain list may honestly be short or empty.
- Corrected analyst targets (research layer, context + tie-break only):
  **corrected 1yr guess = 5% + 0.22 × claimed upside** (analysts overshoot
  ~7-12pp on US large caps); dispersion gate → "n/r" when targets are
  scattered (range > ~60% of price — scattered targets predict NEGATIVELY);
  red flag = claimed upside >40% + wide dispersion; negative claims are not
  informative (no downgrade). Raw target levels are a documented trap
  (Han-Kang-Kim 2022, Palley-Steffen-Zhang 2025).

## Signal engine lineage

### v1 (original)
Core ranks: 12-1 momentum (.35), 52w-high proximity (.25), up-gap+volume
PEAD proxy (.15); vol band (.10), 1-month guard (.10), SMA50 (.05).
Hard gate SMA200; vetoes: 1m return >+25% or <-15%, top vol decile.

### v3 (adopted 2026-08, tested on the full 2014-2017 monthly census)
38 non-crash entry dates, five picks per date, exact HIT rule, market =
equal-weight S&P over the same windows (avg +1.78%):

| pipeline | hit rate | avg return at day 42 | beat market | med days to +5% | fell -5% first |
|---|---|---|---|---|---|
| v1 | 56.3% | +4.01% | 31/38 | 15 | 36% |
| v2 (6m mom + smooth + abs-mom gate) | 61.1% | +4.42% | 29/38 | 16 | 40% |
| **v3 (v2 + near-breakout + lottery-spike gate)** | **61.1%** | **+4.63%** | **30/38** | **16** | **39%** |

Changes vs v1, all frozen from published research:
1. `mom6` 6-1 month momentum beside 12-1 [MSCI standard]
2. `pos252` smooth-path tilt — share of up-days over the year
   [frog-in-the-pan, Da-Gurun-Warachka 2014]
3. HARD GATE `ret6 > 0` (absolute momentum) [Antonacci]
4. `brk20` closeness to the 20-day high (speed/breakout)
   [52w-high family, George-Hwang]
5. HARD GATE: max 1-day return last 21d below the 90th cross-sectional
   percentile (no lottery spikes) [Bali et al. MAX effect]

Weights (sum 1.00): mom12 .20 | mom6 .15 | high52 .25 | gap .05 |
smooth .10 | brk20 .07 | volband .10 | guard .05 | sma50 .03.

**Ablations — tried and REJECTED, do not re-add:**
- MSCI risk-adjusted momentum (mom/vol): hit rate DOWN 1.6pp. Dividing by
  vol tilts to calm names, but touching +5% inside 42 trading days NEEDS
  movement (that's why VOL_BAND exists). Objective mismatch: published
  momentum research optimizes smooth multi-year returns; OppScore optimizes
  gain × speed × consistency inside 2 months. Different games.
- Monthly-consistency score (Grinblatt-Moskowitz): hit rate DOWN 3.7pp —
  rewards slow steady grinders, the wrong horse for a 2-month sprint.

Known trade-off: v1 was slightly faster (median 15 days vs 16) and
dipped -5% first slightly less often (36% vs 39%) — it loves explosive
names. v3 trades a sliver of speed for more hits and more end-of-window
return. If the 2016-2026 calibration shows the same pattern, that's a knob
to think about, not a bug.

Caveats on the v3 evidence itself: the 2014-2017 panel's 38 windows overlap
(each is 2 months), so the effective independent sample is roughly half;
component selection used this same tape; prices were split- but not
dividend-adjusted, ~505 stocks with survivorship. The 2016-2026 calibration
at home (different pipeline, dividend-adjusted SIP data) is the test this
panel couldn't have peeked at.

### Engine-version discipline (enforced in code)
- `config.ENGINE` stamps `calibration.json`, `last_scan.json`, and every
  `picks.xlsx` row. `calibrate.run()` discards a cached calibration whose
  engine tag doesn't match — swapping signals can never silently reuse
  probability tables fitted to the old ranking.
- `excel_book` migrates older workbooks by appending the Engine column and
  stamping pre-existing rows `v1`; the Track Record reports hit-rates
  **by engine** so an upgrade can't hide behind the old version's results.
- Pre-switch open picks (2026-08-05: FTNT, URI, DAL) remain v1 picks.

## Future work (noted, not built)
- `backtest.py` harness to replay v-next candidates on 2016-2026 SIP data
  before any future engine bump.
- Logistic-regression calibrator; as-of historical constituents
  (fja05680/sp500) to kill survivorship; purged-CV validation; earnings
  calendar API (Claude web-search covers it per-run for now).
