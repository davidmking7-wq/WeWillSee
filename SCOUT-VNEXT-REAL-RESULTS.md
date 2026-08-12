# SCOUT-VNEXT-REAL-RESULTS

The canonical results file for the vNext real-backtest program (execution
handoff of 2026-08-12). **LIVING DOCUMENT while runs are in flight** — blocks
marked `RUNNING` fill in as their labs complete; nothing already written here
will be revised except to replace a `RUNNING` marker with measured numbers.

Registry note: the handoff's H36–H40 register in this repo as **H40–H44** to
avoid collision with the existing H36–H39 (`scout/hypotheses.md`).

---

## A. Reproducibility header

| | |
|---|---|
| repository | davidmking7-wq/WeWillSee |
| branch | `claude/vnext-real-backtests` (PR #6) |
| base commit at section-A write | `42c013cc48717b2aed279e778ad95efdfa9b6666` |
| run dates | 2026-08-12 (UTC) |
| python | 3.11.15, Linux 6.18.5 x86_64 |
| pandas / numpy / requests | 3.0.5 / 2.4.6 / 2.34.2 |
| price data | Alpaca SIP daily bars, shared master cache (3,670 symbols × 2,664 dates, 2016-01-04..2026-08-07) |
| fundamentals | SEC DERA financial-statement data sets, 23.4M facts, point-in-time by FILING date (`scout/sec_bulk.py`) |
| insider data | SEC DERA insider-transactions data sets 2013Q1–2026Q1, 404,474 market-wide purchase rows |
| news | Benzinga headlines, 120 liquid names, 2016-01..2026-07, 464,430 stories (cached) |
| filings | EDGAR submissions API + full-text search + primary documents (10-K text streamed, never stored) |
| PIT universe | S&P 500 point-in-time membership (fja05680/sp500), union 742 tickers 2016-2026 |
| PIT coverage | **740/742 (99.73%)**, fail-closed floor 90% (`scout/integrity_report.json`) |
| identity resolution | 602 current + 117 instance-recovered + 9 date-span = **728/742 (98.1%)**; 8 hard conflicts + 6 unresolved LISTED: AABA, BRCM, DISCK, FRC, NLSN, SBNY (`scout/identity_map.json`) |
| splits repaired | 7 (incl. AAPL 2020-08-31) against Alpaca corporate actions |
| frozen/reused tickers retired | 23 (first ≥10-identical-close run; BIL exempted with reason) |
| unresolved >45% one-day prints | 99, masked in returns, prices untouched |
| return fill policy | `pct_change(fill_method=None)` — no forward fill anywhere |
| commands | `python -m scout.price_integrity --report` · `python -m scout.historical_identity --build --resolve` · `python -m scout.h4X_* --fetch` / `--run` / `--selftest` (X = 0..4) |
| module self-tests | price_integrity 8/8 · h40 6/6 · h41 6/6 · h42 7/7 · h43 3/3 · h44 4/4 — all planted-defect style |

No API keys appear in this file, the repo, or any commit. `.env` is gitignored.

## B. Trial ledger

One row per mechanism-level decision; per-variant lists live in each lab's
results JSON (`variants_tried`).

| Trial | Mechanism | Frozen before result? | Variants (see JSON) | Result | Decision |
|---|---|---|---|---|---|
| H40a | pure/unexpected news (scalar) | yes — docstring pre-registration | raw/predictable/pure × 5 horizons + 2 nulls | RUNNING | — |
| H41a | 10-K textual change | yes | cosine/jaccard × EW/VW × eras | RUNNING (fetch) | — |
| H42 | opportunistic insider purchases | yes — CMP classifier verbatim | 4 buckets × 4 horizons + contrast + buckets + null | **routine α +7.19 vs opportunistic +0.84 (h63); real book at 33.7th pctile of its own timing null** | **KILL_H42** (verification in flight) |
| H43 | repurchase announcement × valuation | yes | 3 buckets × 4 horizons + V−G + matched null | RUNNING | — |
| H44 | dividend reinvestment flow | yes | 3 price terciles × 2 windows + L−H + permutation null | RUNNING | — |

## C. H40 result block — RUNNING

Lab `scout/h40_pure_news.py`, results `scout/h40_results.json` when done.
Universe scope stated in advance: 120 TODAY-liquid names (survivorship-tilted
cohort; the only positive outcome is ADVANCE_TO_H40B, never production).

## D. H41 result block — RUNNING (fetch stage)

Lab `scout/h41_lazy_prices.py`. Streaming ~6,000 original 10-Ks; similarity
pairs cached in `scout/cache_h41_similarities.csv` (resumable).

## E. H42 result block — KILL_H42

- purchase rows market-wide 2013–2026: **404,474**; PIT events 2016+: **7,985**
  (routine 577 / opportunistic 556 / unclassifiable 6,852)
- classifier, frozen ex ante: classifiable = purchases in each of 3 prior
  years (same insider–firm pair); routine = same calendar month in all three
- timing: filing DATE only in the datasets → entry at close of first session
  strictly after filing (conservative, per handoff 9.2)
- h63 gross, long-only vs SPY (Rule 13):

| bucket | n | ann %/yr | t | alpha %/yr | t(alpha) |
|---|---:|---:|---:|---:|---:|
| all | 7,985 | +21.29 | 3.73 | +4.88 | 1.07 |
| routine | 577 | +17.40 | 2.08 | **+7.19** | 0.82 |
| opportunistic | 556 | +16.77 | 2.26 | **+0.84** | 0.13 |
| unclassifiable | 6,852 | +19.11 | 3.55 | +2.70 | 0.70 |

- **the mechanism's own ordering is BACKWARDS** (routine > opportunistic), and
- **the timing-shuffle null explains the level**: the real opportunistic book
  sits at the **33.7th percentile** of issuer-date-rotated versions of itself —
  random re-timing does better. The headline return is beta plus firm mix.
- kill class (handoff §16): **structural kill on this universe**, with one
  scoping caveat carried to §J: CMP's original effect concentrated in small
  caps; the PIT S&P 500 is the large-cap cohort. A small-cap retest is a NEW
  preregistered hypothesis, not a rescue of this one.
- production-approved: **NO**

## F. H43 result block — RUNNING

Lab `scout/h43_repurchase_value.py`. 24,488 8-K authorization filings
harvested; PIT match + cooldown + point-in-time B/M in progress.

## G. H44 result block — RUNNING

Lab `scout/h44_dividend_flow.py`. 357,528 dividend rows harvested.
Declaration-date gate: anticipatory legs FAIL CLOSED (feed has no declaration
dates); payment-window entries proven public per event (ex-date session ≤
entry session, violations dropped and counted).

## H. Standalone survivor table — pending (no survivors yet; H42 dead)

## I. Combined Scout result — pending

Runs only if ≥1 sleeve passes the §12 gates; with fewer than three
independent survivors the verdict is `INSUFFICIENT_FINAL_SLEEVES` by rule,
not a synthetic "effective bets ≥ 3".

## J. What failed and why — filling as verdicts land

- **H42 opportunistic insiders — structural kill.** Ordering backwards AND
  timing-shuffle-explained on 2016-2026 PIT large caps. Data-limited caveat:
  the universe is the large-cap cohort; the canonical effect lived down-cap.
  A future data upgrade that could legitimately reopen it: a delisting-
  inclusive small/mid-cap PIT universe with capacity modeling.

## K. ChatGPT review targets — final section, written when all blocks close
