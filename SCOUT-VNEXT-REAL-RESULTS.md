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
| H42 | opportunistic insider purchases | yes — CMP classifier verbatim | 4 buckets × 4 horizons + contrast + buckets + null | **routine α +7.73 vs opportunistic −0.74 (h63); real book at 18.7th pctile of its own timing null; 2x costs zero the excess** | **KILL_H42** — 3-lens adversarially verified |
| H43 | repurchase announcement × valuation | yes | 3 buckets × 4 horizons + V−G + matched null | **V−G = −4.74%/yr (backwards); random-firm null not beaten; thirds flip sign** | **KILL_H43** |
| H44 | dividend reinvestment flow | yes | 3 terciles × 2 windows + L−H + permutation null + pre-ex placebo + regime excision | **active-span L−H +7.87%/yr t 1.61 — but one 3-yr window carries 96% of P&L (remainder t 0.13), flow window holds none of it, dose-response reversed** | **KILL_H44** — survival revoked by 3-lens verification |

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
- **The kill was adversarially verified by three independent agents before
  being accepted** (implementation / power / null-construction lenses). One
  found a real identity bug — a last-row-wins CIK inversion pricing 273
  events with the WRONG company's returns and zero-filling dead columns —
  which had been FLATTERING the mechanism. The numbers below are the
  corrected run under filing-symbol-verified identity (`resolve_cik`, with
  `ISSUERTRADINGSYMBOL` cross-check; unresolvable collisions dropped and
  counted). The null-construction lens reproduced the shuffle bit-for-bit
  and quantified two pro-null biases at ~1pt combined — not enough to matter.
- h63 gross, long-only vs SPY (Rule 13), corrected identity:

| bucket | n | ann %/yr | t | alpha %/yr | t(alpha) |
|---|---:|---:|---:|---:|---:|
| all | 7,620 | +22.07 | 3.72 | +5.07 | 1.05 |
| routine | 573 | +17.92 | 2.13 | **+7.73** | 0.88 |
| opportunistic | 531 | +15.40 | 2.00 | **−0.74** | −0.11 |
| unclassifiable | 6,516 | +20.26 | 3.67 | +3.15 | 0.80 |

- three independent kill grounds: **the mechanism's ordering is BACKWARDS**
  (routine α +7.73 vs opportunistic −0.74); **the timing-shuffle null is not
  approached** (real book at the **18.7th percentile** of issuer-date-rotated
  versions of itself — random re-timing does better); **2x costs zero the
  market-adjusted excess**.
- kill classification (power lens, adopted): **no detectable effect on PIT
  S&P 500 large caps.** The design's minimum detectable alpha at t=2 is
  ~13%/yr against a plausible post-publication large-cap effect of 1–4%/yr,
  so this kills the TRADE on this universe without adjudicating the canonical
  small-cap mechanism — `source_gap`, carried to §J. A small-cap retest is a
  NEW preregistered hypothesis, not a rescue.
- production-approved: **NO**

## F. H43 result block — KILL_H43

- 24,488 8-K filings matching `"repurchase program" "authorized"` (FTS,
  quarterly chunks) → 4,842 PIT-matched under date-aware identity → **1,985
  events** after the 365-day per-company cooldown → **1,425 with
  point-in-time B/M** (filing-date discipline, consolidated rows,
  split-adjusted shares). Numbers below are the corrected re-run after the
  identity hardening that H42's verification forced (the verdict was
  unchanged by it).
- h126 gross, long-only vs SPY (Rule 13):

| bucket | n | ann %/yr | t | alpha %/yr | t(alpha) |
|---|---:|---:|---:|---:|---:|
| value | 442 | +15.30 | 2.58 | **−1.48** | −0.33 |
| mid | 464 | +15.45 | 3.32 | −0.80 | −0.30 |
| glamour | 489 | +20.04 | 4.66 | **+3.50** | 1.40 |

- **the value conditioning is BACKWARDS**: value − glamour = **−4.74%/yr** at
  h126; the mechanism predicted the opposite sign
- matched control: value-bucket events are **indistinguishable from random
  PIT firms on the same sessions** (the calendar, not the announcement,
  carries the return)
- V−G thirds `[−15.25, +7.59, −6.57]` — sign flips across eras
- kill class (handoff §16): **structural kill on this decade** — with the
  honest macro note that 2016-2026 was historically hostile to value as a
  style; §J records what could reopen it
- production-approved: **NO**

## G. H44 result block — KILL_H44 (initial survival REVOKED by verification)

- The lab's first run said SURVIVES_TO_GATES. Three adversarial verification
  agents voided it, and the hardened lab (fail-closed active span, registered
  pre-ex placebo, the liquidity control the first run had registered but not
  implemented, an H22-pattern regime-excision rule) reaches KILL by its own
  rules. This is the program's third self-revocation-grade catch and the
  reason survivals get verified harder than kills.
- DATA HOLE found by verification: the dividend feed is EMPTY before mid-2019
  (2016: 2 rows, 2017: 0, 2018: 1). True span **2019-07-12..2026-08-07**;
  events by year 2019: 55 → 2020-2026: ~1,100-1,550/yr; the original "+0.10
  first third" was two active sessions diluted over 888 empty days.
- active-span numbers (9,620 events): L−H +20s **+7.87%/yr, t 1.61**, at the
  99.2nd pctile of the within-month permutation null — and then:
  - **regime excision (the kill)**: the best 3-year window (2019-07..2022-07)
    carries **96% of cumulative P&L**; excised, the remainder is **t 0.13**
  - **mechanism voided** (verification): the flow window (days 0-2) holds
    −0.1 bps pooled; the spread accrues days 3-19 with no decay; dose-response
    REVERSED (low-yield half carries more); the paying leg is the HIGH-price
    leg lagging SPY (α −5.14) — the book shorts expensive payers, it does not
    ride DRIP pressure
  - **null miscalibrated for factor risk** (verification): dependence-
    respecting p ≈ 0.04-0.06 one-sided; a clean PRE-EX placebo in the
    verifier's construction reproduced ~89% of the spread where no flow can
    exist (the hardened lab's own placebo variant prints −9.5%/yr — window
    construction matters, and neither supports a flow reading)
  - liquidity terciles (the registered control, now implemented): spread in
    all three (7.3-12.3%/yr) — not an illiquidity artifact, consistent with a
    factor loading
- kill class (handoff §16): **structural on the mechanism** (timing, dose-
  response and leg attribution all contradict flow) and **regime-concentrated
  on the return** (one window = 96%). What could reopen it: nothing about
  THIS design; a declaration-dated feed with pre-2019 coverage would allow a
  different, properly anticipatory design as a NEW preregistration.
- production-approved: **NO**

## H. Standalone survivor table — empty. H42, H43, H44 all killed; H40/H41 pending

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
- **H43 repurchase × undervaluation — structural kill.** The conditioning
  variable worked in reverse (glamour announcers beat value announcers by
  4.7 pp/yr at h126), the matched-dates random-firm control was not beaten,
  and the effect flips sign across eras. Caveat recorded rather than argued:
  2016-2026 was the most value-hostile decade on record, and the mechanism is
  a value-conditioned one — a future regime where B/M spreads compress could
  legitimately justify ONE new preregistration; nothing about this run may be
  retuned into survival.

## K. ChatGPT review targets — final section, written when all blocks close

---
## RESUME NOTE (written at 90% usage)
If this session dies: H44 rerun (`h44_run2.log`), H40 (`h40_run.log`) and the
H41 fetch (`h41_fetch.log`) may still be running or finished in scratchpad.
To close the program: read each log tail, `python -m scout.h41_lazy_prices
--run` once its fetch completes, paste each verdict into its block above,
then write sections H-K (no survivor so far → likely
INSUFFICIENT_FINAL_SLEEVES). All labs are committed; nothing is lost.
