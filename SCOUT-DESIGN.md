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
dividend-adjusted, ~505 stocks with survivorship. The 2016-2026 validation
below (different decade, dividend-adjusted SIP data, this exact codebase)
is the test that panel couldn't have peeked at.

### 2016-2026 out-of-sample validation

The definitive engine comparison (v1/v3/v4, vs both the equal-weight
universe AND the S&P 500 itself, with compounded growth) lives in
**BACKTEST-REPORT.md**, regenerated from `python -m scout.backtest`
(machine-readable: `scout/backtest_results.json`).

The findings that shape how this tool must be presented:
- **The v3 and v4 switches hold out of sample**: more hits, faster to +5%,
  fewer -5%-first dips than v1, with gains concentrated in bull regimes.
- **What did NOT replicate from the 2014-2017 census:** "beats the market
  ~4 windows out of 5". On 2017-2026 every engine beats the benchmarks in
  fewer than half the windows and compounds BELOW buy-and-hold SPY.
  The composite's edge is in first-passage odds, speed and path safety —
  NOT end-of-window outperformance. Never sell it as market-beating.
- **Bear-regime warning:** post-v1 engines' average end return in bear
  windows is ~0 on a tiny sample (~3 episodes). The honest posture in bear
  regimes is fewer or zero picks, not confidence in the numbers.

### v4 (adopted 2026-08-07): gain-forward objective + leaner engine + earnings flag

The user's directive: +5% must behave as a MINIMUM, not a goal — optimize
high gain × low risk × low wait, and account for earnings inside the window.

**Objective changes (definitional, not fitted):**
- OppScore's profit term switched from MEDIAN max gain to MEAN max gain
  (winsorized at +50%): cells whose winners run far now outrank cells that
  merely clear the bar. GainScore likewise.
- New cell stats: P(+15%), mean max gain.
- picks.xlsx: HIT picks keep being re-priced until the Deadline (previously
  tracking froze at +5%), "Goal (+5%)" renamed "Min Goal (+5%)", new
  "Chance +15%" and "Earnings Before Deadline" columns.

**Signal change (selected by train/holdout protocol on 2016-2026 SIP data):**
Candidates, each one literature-grounded change on v3: SECREL
(sector-relative momentum), NOGAP (drop gap/volume PEAD proxy → weight to
6-1 momentum), PULLBACK (veto 5d micro-spikes), TIGHTHIGH (52w-high ≥0.80
gate). Train 2017-07..2021-12 (53 monthly dates, 5 picks):

| variant | hit% | P+10% | avg end% | mean peak% | med days | dip% |
|---|---|---|---|---|---|---|
| v3 control | 64.9 | 32.8 | 2.01 | 8.70 | 17 | 44.9 |
| **NOGAP** | **66.0** | **35.5** | **2.41** | **9.11** | **16** | **43.8** |
| SECREL | 64.9 | 33.6 | 1.95 | 8.63 | 16 | 45.3 |
| PULLBACK | 63.9 | 30.2 | 1.61 | 7.93 | 18 | 44.3 |
| TIGHTHIGH | 64.5 | 32.8 | 2.03 | 8.69 | 17 | 45.3 |

Only NOGAP improved the full objective → single-shot holdout
2022-01..2026-05 (52 dates): hit 57.7 vs 58.1 (equal at 60.0 in the
non-overlapping subset), avg end +2.57 vs +2.44, P+10% 38.8 vs 37.7,
P+15% 23.1 vs 21.9, median 12 vs 13 days, dip 47.3 vs 46.9. Gain and speed
better, hit and safety within noise → **shipped. v4 = v3 minus the gap
signal (weight to 6-1 momentum).** The gap feature is still computed as
research context; it earns no score weight. Honesty note: the ship decision
conditions on the holdout, and both eras share the survivorship universe —
the protocol reduces snooping, it does not eliminate it.

**Earnings inside the window (pipeline, not just research):** scan now
fetches each candidate's next earnings date (Yahoo calendar with yfinance /
NASDAQ fallbacks, cached, strictly best-effort — a blocked source degrades
to the old web-research behavior). A date on or before the deadline flags
the candidate, auto-downgrades its grade one notch (A→B→C), and lands in
the "Earnings Before Deadline" column. Research confirms rather than
discovers.

**Backtest harness fixes (from adversarial review, before the holdout ran):**
crash-flag volatility threshold now an expanding quantile (was full-sample —
lookahead); non-overlapping stride uses ceil (round() could overlap);
strategy-vs-benchmark averaging made weight-consistent (per-date); NaN
guards on regime/vol. Plus: SPY benchmark columns (beat-SPY per window,
avg SPY window return) and sequential compounding of the non-overlapping
windows. Known remaining limits (documented, accepted): symbols delisted
mid-window drop out of picks AND benchmarks; SPY sits in the cross-sectional
rank pool (1/500 distortion, consistent across scan/calibration/backtest);
labtest's SECREL rank is post-gate.

### Sell rules (2026-08-08, scout/exitlab.py)

User directive: "if stock x does y you should sell, so losses are minimal —
and account for it in testing." 19 close-based exit rules tested train
(2017-2021) / holdout (2022-2026) over the v4 engine's picks, under BOTH
cash-exit and redeploy-into-SPY accounting; simulation adversarially
verified (no bugs); conclusions cross-checked against Kaminski-Lo 2014,
Lei-Li 2009, Han-Zhou-Zhu. Full record in BACKTEST-REPORT.md. Verdict:
ordinary stops/time/trend exits reduce returns (whipsaw + gap-through;
daily single-stock autocorrelation has the wrong sign for stops). Shipped
as per-pick "Sell Signal" guidance (config.SELL_DISASTER_STOP,
SELL_TRAIL_AFTER_HIT): (1) −15% disaster stop — tail-capping at ~zero mean
cost with redeployment; (2) otherwise the deadline is the exit; (3) after
a +5% touch, protect at max(breakeven, peak−8%) — return-neutral with
redeployment, cuts the average loser −7.9%→−6.0%. scan emits `sell_if`,
update refreshes live levels and flags "SELL" states in the Excel "Sell
Signal" column. HIT/MISS labels are never altered by the guidance. Real
loss prevention lives at entry: earnings gate, lottery-spike veto, crash
rule.

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
