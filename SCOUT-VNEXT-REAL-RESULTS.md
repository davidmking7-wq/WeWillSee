# SCOUT-VNEXT-REAL-RESULTS

The canonical results file for the vNext real-backtest program (execution
handoff of 2026-08-12). **FINAL** — all five hypotheses decided 2026-08-12/13.

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
| H40a | pure/unexpected news (scalar) | yes — docstring pre-registration | raw/predictable/pure × 5 horizons + 2 nulls | **OOS R² +0.055 (representation tested); pure L/S gross −0.78%/yr at beta 0.00, at the 2.4th/8.0th pctile of its own nulls** | **KILL_H40_SCALAR** |
| H41a | 10-K textual change | yes | cosine/jaccard × EW × eras | **L/S Q5−Q1 gross −2.36%/yr (t −0.73, beta 0.02); 2020+ era −3.67%/yr; Jaccard agrees** | **KILL_H41** |
| H42 | opportunistic insider purchases | yes — CMP classifier verbatim | 4 buckets × 4 horizons + contrast + buckets + null | **routine α +7.73 vs opportunistic −0.74 (h63); real book at 18.7th pctile of its own timing null; 2x costs zero the excess** | **KILL_H42** — 3-lens adversarially verified |
| H43 | repurchase announcement × valuation | yes | 3 buckets × 4 horizons + V−G + matched null | **V−G = −4.74%/yr (backwards); random-firm null not beaten; thirds flip sign** | **KILL_H43** |
| H44 | dividend reinvestment flow | yes | 3 terciles × 2 windows + L−H + permutation null + pre-ex placebo + regime excision | **active-span L−H +7.87%/yr t 1.61 — but one 3-yr window carries 96% of P&L (remainder t 0.13), flow window holds none of it, dose-response reversed** | **KILL_H44** — survival revoked by 3-lens verification |

## C. H40 result block — KILL_H40_SCALAR

- 464,430 stories → wire/broadtape filtered → 42,230 (date, firm) tone rows;
  796 tradeable formations at h21 (≥12 eligible names each)
- **positive control PASSED**: walk-forward ridge OOS R² = **+0.055** — tone
  IS predictable from the firm's prior state, so the residual ("pure") tone
  was genuinely isolated and the mechanism genuinely tested (this is a real
  kill, not INCONCLUSIVE_REPRESENTATION)
- h21 long-short, gross, beta vs SPY:

| signal | ann %/yr | t | beta | alpha %/yr |
|---|---:|---:|---:|---:|
| raw tone | −2.70 | −1.72 | −0.10 | −1.18 |
| predictable tone | −2.38 | −1.17 | −0.07 | −1.28 |
| pure tone | **−0.78** | −1.37 | 0.00 | −0.83 |

- the real pure-tone book sits at the **2.4th percentile** of the within-date
  permutation null and the **8.0th** of the timing-shuffle null — WORSE than
  randomly assigned scores; there is nothing here even before costs (net-2x
  at h21 is −10.4%/yr, mostly deterministic cost drag at that turnover)
- fifth independent confirmation of the repo's standing result: news content
  forecasts the SIZE of the next move and none of its SIGN (H15/H16/H17/H24
  before it) — removing the predictable component does not change that
- scope: 120 today-liquid large caps; the paper's full-article embeddings are
  NOT tested by this scalar proxy (handoff 7.1 said exactly this in advance)
- production-approved: **NO**

## D. H41 result block — KILL_H41

- **6,603 year-over-year original-10-K pairs** (684 companies; 14 identity-
  skipped tickers listed in the JSON), text streamed and never stored;
  similarity = hashed-TF cosine, Jaccard as the registered robustness check
  (cosine-Jaccard correlation in-sample: see JSON)
- entry one month after FILING date, hold 9 months, overlapping cohorts,
  EXPANDING quintile breakpoints (no full-sample sort)
- Q5−Q1 (nonchangers minus changers), equal weight, gross: **−2.36%/yr
  (t −0.73), beta 0.015, alpha −2.59%/yr (t −0.80)** — the SIGN is against
  the mechanism; 2,698 events traded, top-10 share 15% (not concentration)
- the decision-relevant split (handoff 8.5): 2016-2019 **−0.19%/yr**;
  **2020+ (fully post-publication): −3.67%/yr** — the effect is absent in
  the near-sample era and negative after publication
- Jaccard robustness agrees (−1.75%/yr, t −0.54); long leg alone trails SPY
  by −2.47%/yr — nonchangers were not safe havens this decade
- limitations, stated: value-weight variant skipped (shares-panel call
  signature error at run time; with EW wrong-signed at both eras a VW rescue
  would be a post-hoc new trial under section 15 anyway and was not
  attempted); borrow modeled flat; no PIT sector map
- kill class (handoff §16): **structural kill on 2016-2026 large caps** —
  wrong sign, both similarity measures, worst in the post-publication era.
  H41b (optionability split) is NOT triggered: handoff 8.8 permits it only
  when the basic sign is correct.
- production-approved: **NO**

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

## H. Standalone survivor table

**Empty. All five mechanisms were killed.** No sleeve reached the section-12
gates, so no gate table, correlation matrix, or effective-bets figure exists
to report.

## I. Combined Scout result

No final-approved sleeves exist, so no combination was run and none of the
architecture gates could be evaluated. Architecture verdict, per the
handoff's own vocabulary and rule against halfway labels:

**`INSUFFICIENT_FINAL_SLEEVES`**

The +13–20 pp/yr objective was explicitly evaluated and is **not met, and
not approachable from these five mechanisms on this data**: the best
surviving CANDIDATE number anywhere in the program (H44's +7.9%/yr spread)
was revoked on verification, and every other mechanism produced a wrong
sign or a sub-noise effect.

## J. What failed and why — complete

| mechanism | kill class | one line | could reopen it |
|---|---|---|---|
| H40 pure news | structural on this cohort | representation tested (OOS R² +0.055) and the residual still has no sign information — below its own nulls | full-article embeddings (the paper's actual variable), small caps |
| H41 lazy prices | structural | wrong sign both similarity measures, −3.7%/yr in the fully post-publication era | nothing about this design; a mid/small-cap PIT universe is a new hypothesis |
| H42 opportunistic insiders | no detectable effect (source_gap) | ordering backwards AND below its timing null; MDE ~13%/yr on this universe | delisting-inclusive small/mid-cap PIT universe with capacity modeling |
| H43 repurchase × value | structural this decade | value conditioning ran backwards (glamour won by 4.7pp); random firms on same dates matched it | a regime where B/M spreads compress — ONE new preregistration allowed |
| H44 dividend flow | structural on mechanism, regime-concentrated on return | flow window holds none of the P&L; dose-response reversed; one 3-yr window = 96% of P&L; feed empty pre-2019 | a declaration-dated, pre-2019-covered feed enabling a genuinely anticipatory design |

Process record, because it is part of the evidence: three of the five
verdicts were adversarially attacked by independent verification agents
before acceptance. That process caught (a) a CIK-inversion bug pricing 273
events with the wrong company's returns — which had been FLATTERING the dying
hypothesis, (b) a registered control that was never implemented, (c) a data
feed empty for a third of the claimed span, and (d) one false survival
(H44), revoked. Every catch made a kill stronger or truer; none rescued
anything. The labs' planted-defect self-tests (28 checks across five
modules) all pass.

## K. ChatGPT review targets

1. **Suspiciously strong:** nothing survived, but H42's `unclassifiable`
   bucket (+20.3%/yr, t 3.67, n=6,516) is raw beta-heavy exposure worth
   confirming as such, not alpha.
2. **Weakest data assumption:** H43's event definition (FTS phrase match +
   365-day cooldown) — a hand-verified authorization list could reclassify
   some events, though the value-conditioning reversal would have to flip
   sign to matter.
3. **Timestamp leak candidates:** all entries are next-session-after-filing
   or provably-public-by-ex-date; the one place worth re-auditing is H40's
   15-minute pre-close rule against Benzinga's `created_at` clock skew.
4. **Residual survivorship:** the 14 identity-unresolved PIT members
   (listed in §A) are excluded from H41-H43 — disproportionately acquired
   firms, so their absence most plausibly BIASES AGAINST event-drift
   findings; worth a sensitivity pass if any mechanism is ever revisited.
5. **Tiny-sample dependence:** H44's kill itself (96% of P&L in one window)
   is robust; H42's routine bucket (n=573, α +7.7 at t 0.9) is noise, not a
   lead.
6. **Cost-fragile results:** none survived to be cost-fragile.
7. **Overlapping mechanisms:** none survived to overlap.
8. **Combined-gate failures:** `INSUFFICIENT_FINAL_SLEEVES` — zero of the
   required three independent sleeves.
9. **Recommended next falsification:** the one undead thread in the whole
   repo is CONSTRUCTION (H31: cap-weighting the same holdings, +0.15 Sharpe,
   externally confirmed by SPY−RSP) and the trend overlay's drawdown claim
   (H35, survives matched nulls with both crashes excised). A falsification
   worth running: does the H35 overlay's drawdown protection survive on
   pre-2016 data (2000-2015, two full bear markets) fetched from a second
   vendor — i.e., is it Faber's published result or this decade's shape?

> **STOP HERE. Do not tune further. Return `SCOUT-VNEXT-REAL-RESULTS.md` to
> the user so ChatGPT can independently review the evidence and decide what
> to do next.**

