# Hypothesis Registry

Rule (RESEARCH-AGENDA.md): every idea is logged HERE, with its mechanism
and expected sign, BEFORE any test runs. Every variant tried gets a row.
The trial count N below feeds the multiple-testing discipline.

| # | date | hypothesis (mechanism, one sentence) | expected sign | status |
|---|---|---|---|---|
| H1 | 2026-08-08 | Opportunistic open-market insider BUYING (code P, officer/director, non-plan) within 30d before entry predicts higher hit rate — insiders act on unpriced private information, strongest down-cap. | picks with buys > picks without | testing |
| H1b | 2026-08-08 | Heavy non-plan insider SELLING clusters (≥3 distinct sellers, 30d) predict lower hit rate. | sell-cluster picks < others | testing |
| H2a | 2026-08-08 | Entering when the scheduled report is 5-15 td ahead concentrates the earnings-catalyst premium (risk premium for holding the binary event) into the window's front half. | earnings-timed top-3 ≥ standard top-3 | testing |
| H2b | 2026-08-08 | Small/mid caps with a large positive announcement reaction (2-day ≥ +5%) drift further over the next 42 td (PEAD survives down-cap where algos don't price it instantly). | post-reaction cohort > SPY + > base | testing |
| H3 | 2026-08-08 | A walk-forward logistic model on entry-time features (regime, vol, segment, momentum shape, earnings flags) separates our own picks' HIT probability better than the calibration cell alone (meta-labeling refines a known signal). | model AUC > cell baseline | testing |
| H4 | 2026-08-08 | Entering at/near the close (never the open) avoids paying overnight drift + open-auction spreads. Adopted from literature (Lou-Polk-Skouras) without a local test — execution hygiene, not a signal; not testable with daily bars alone. | n/a | adopted |

Prior related trials (count toward N): earnings proxy-skip (2 variants —
REVERSED by real dates), sell-before-event (failed), catalyst-ahead
ranking (shipped), 25+ exit rules, 4 engine variants, 5 expectation
exits, sector exclusion (failed), 12 portfolio configs.
