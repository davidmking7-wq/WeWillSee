# Locked candidate-path validation

Generated: 2026-08-09T22:19:18.200028+00:00
Common published endpoint: 2026-05

This is a one-shot historical test of the committed preregistration. No result below authorizes live trading or a merge to main.

## Fail-closed verdict

| Candidate | Final status | Actual primary start | Reason | Landslide status |
|---|---|---:|---|---|
| P1 diversified trend | PASS_LOCKED_HISTORICAL | 1991-01 | ALL_LOCKED_GATES_AND_PROTOCOL_AUDITS_MET | n/a |
| P2 global market-neutral styles | DATA_INCONCLUSIVE | 1993-11 | INVALID_PROTOCOL_COVERAGE | n/a |
| P3 developed core + overlays | DATA_INCONCLUSIVE | 1996-11 | INVALID_PROTOCOL_COVERAGE and INHERITS_P2_INVALIDITY | DATA_INCONCLUSIVE |

P1 is the only locked historical pass. It starts exactly at 1991-01 and meets its gate under both the frozen fixed-drag calculation and the audit-only interpretation that makes drag proportional to actual sleeve scale.

P2 starts at 1993-11, not the frozen 1991-01 common start. P3 and its benchmark start at 1996-11, and P3 also depends on the invalid-coverage P2 sleeve. Their raw numbers remain useful diagnostics, but neither candidate may receive a PASS.

On only the evaluable subset, P3's base-cost CAGR advantage was 7.56% and the raw eight-point landslide check was not met. The locked landslide status is still DATA_INCONCLUSIVE because the frozen start coverage was not met.

The 2010+ slice was untouched by this run only. It was not unknown when the ideas were selected and is not independent of the existing finance literature.

## Audit-only sensitivities (not the locked primary)

No parameter, data source, split, cost rate, or trading rule was changed. These are two explicit readings of how the already-registered cost and funding rates scale.

- When sleeve drag is multiplied by actual sleeve scale, P2's base-cost positive rate across overlapping 60-month windows is 68.07%, below its 70% gate.
- Under that proportional-drag sensitivity, P3's 2010+ stress-cost CAGR edge is -0.49% per year.
- Keeping the locked sleeve-cost calculation but charging funding on the market plus the two sleeves at their actual inner scales makes P3's 2010+ stress-cost edge -0.36% per year, versus 0.13% under the locked primary funding formula.

These sensitivities are audit warnings, not post-result replacements for the frozen primary.

## Protocol coverage audit

Frozen common start: 1991-01

- P1: VALID; locked_primary_base=1991-01, locked_primary_stress=1991-01, proportional_cost_sensitivity_base=1991-01, proportional_cost_sensitivity_stress=1991-01
- P2: INVALID_PROTOCOL_COVERAGE; locked_primary_base=1993-11, locked_primary_stress=1993-11, proportional_cost_sensitivity_base=1993-11, proportional_cost_sensitivity_stress=1993-11
- P3: INVALID_PROTOCOL_COVERAGE; locked_primary_base=1996-11, locked_primary_benchmark_base=1996-11, locked_primary_stress=1996-11, locked_primary_benchmark_stress=1996-11, proportional_cost_sensitivity_base=1996-11, proportional_cost_benchmark_base=1996-11, proportional_cost_sensitivity_stress=1996-11, proportional_cost_benchmark_stress=1996-11

## Locked primary: base costs

### P1

| Period | Start | End | Months | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full evaluable history | 1991-01 | 2026-05 | 425 | 8.58% | 10.51% | 0.838 | -23.18% | -8.10% |
| evaluable pre-2010 subset (requested 1991-2009) | 1991-01 | 2009-12 | 228 | 13.55% | 10.65% | 1.252 | -13.78% | -6.84% |
| 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 3.09% | 10.16% | 0.350 | -23.18% | -8.10% |
| decade_1990s | 1991-01 | 1999-12 | 108 | 15.57% | 10.12% | 1.489 | -13.78% | -6.84% |
| decade_2000s | 2000-01 | 2009-12 | 120 | 11.77% | 11.13% | 1.059 | -11.60% | -6.36% |
| decade_2010s | 2010-01 | 2019-12 | 120 | 3.61% | 10.52% | 0.389 | -21.91% | -7.26% |
| decade_2020s | 2020-01 | 2026-05 | 77 | 2.28% | 9.63% | 0.282 | -20.42% | -8.10% |

Overlapping rolling 60-month positive rate: 87.70% (366 windows; adjacent windows share 59 months and are not independent).

### P2

| Period | Start | End | Months | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full evaluable history | 1993-11 | 2026-05 | 391 | 4.04% | 5.98% | 0.693 | -23.92% | -8.51% |
| evaluable pre-2010 subset (requested 1991-2009) | 1993-11 | 2009-12 | 194 | 5.21% | 7.19% | 0.744 | -23.92% | -8.51% |
| 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 2.89% | 4.46% | 0.661 | -14.99% | -4.14% |
| decade_1990s | 1993-11 | 1999-12 | 74 | 3.17% | 4.16% | 0.771 | -8.50% | -4.08% |
| decade_2000s | 2000-01 | 2009-12 | 120 | 6.50% | 8.54% | 0.781 | -23.92% | -8.51% |
| decade_2010s | 2010-01 | 2019-12 | 120 | 1.81% | 3.52% | 0.528 | -7.10% | -3.52% |
| decade_2020s | 2020-01 | 2026-05 | 77 | 4.59% | 5.61% | 0.829 | -9.33% | -4.14% |

Overlapping rolling 60-month positive rate: 85.54% (332 windows; adjacent windows share 59 months and are not independent).

### P3 and identically scaled benchmark

| Series / period | Start | End | Months | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P3 full evaluable history | 1996-11 | 2026-05 | 355 | 15.29% | 16.00% | 0.839 | -45.90% | -13.10% |
| Benchmark full evaluable history | 1996-11 | 2026-05 | 355 | 7.73% | 16.51% | 0.404 | -61.00% | -22.22% |
| P3 evaluable pre-2010 subset (requested 1991-2009) | 1996-11 | 2009-12 | 158 | 17.83% | 16.99% | 0.868 | -45.90% | -12.77% |
| Benchmark evaluable pre-2010 subset (requested 1991-2009) | 1996-11 | 2009-12 | 158 | 4.69% | 18.33% | 0.170 | -61.00% | -22.22% |
| P3 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 13.29% | 15.17% | 0.813 | -30.54% | -13.10% |
| Benchmark 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 10.23% | 14.91% | 0.639 | -26.76% | -16.32% |
| P3 decade_1990s | 1996-11 | 1999-12 | 38 | 37.58% | 17.73% | 1.638 | -11.64% | -11.64% |
| Benchmark decade_1990s | 1996-11 | 1999-12 | 38 | 22.16% | 20.09% | 0.866 | -21.35% | -20.20% |
| P3 decade_2000s | 2000-01 | 2009-12 | 120 | 12.19% | 16.56% | 0.615 | -45.90% | -12.77% |
| Benchmark decade_2000s | 2000-01 | 2009-12 | 120 | -0.31% | 17.58% | -0.081 | -61.00% | -22.22% |
| P3 decade_2010s | 2010-01 | 2019-12 | 120 | 11.58% | 14.12% | 0.814 | -30.54% | -12.31% |
| Benchmark decade_2010s | 2010-01 | 2019-12 | 120 | 9.69% | 14.04% | 0.695 | -21.93% | -12.16% |
| P3 decade_2020s | 2020-01 | 2026-05 | 77 | 15.99% | 16.75% | 0.813 | -24.24% | -13.10% |
| Benchmark decade_2020s | 2020-01 | 2026-05 | 77 | 11.07% | 16.27% | 0.564 | -26.76% | -16.32% |

Evaluable-subset full-history CAGR advantage: 7.56%; Sharpe advantage: 0.435; drawdown advantage: 15.11%.
Overlapping rolling 60-month benchmark win rate: 89.19% (296 windows; not independent).


## Locked primary: stress costs

### P1

| Period | Start | End | Months | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full evaluable history | 1991-01 | 2026-05 | 425 | 7.50% | 10.51% | 0.743 | -27.49% | -8.19% |
| evaluable pre-2010 subset (requested 1991-2009) | 1991-01 | 2009-12 | 228 | 12.43% | 10.65% | 1.158 | -14.29% | -6.92% |
| 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 2.06% | 10.16% | 0.251 | -27.49% | -8.19% |
| decade_1990s | 1991-01 | 1999-12 | 108 | 14.43% | 10.12% | 1.390 | -14.29% | -6.92% |
| decade_2000s | 2000-01 | 2009-12 | 120 | 10.67% | 11.13% | 0.969 | -11.97% | -6.45% |
| decade_2010s | 2010-01 | 2019-12 | 120 | 2.58% | 10.52% | 0.294 | -24.24% | -7.34% |
| decade_2020s | 2020-01 | 2026-05 | 77 | 1.26% | 9.63% | 0.178 | -21.75% | -8.19% |

Overlapping rolling 60-month positive rate: 81.69% (366 windows; adjacent windows share 59 months and are not independent).

### P2

| Period | Start | End | Months | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full evaluable history | 1993-11 | 2026-05 | 391 | 3.00% | 5.98% | 0.526 | -25.14% | -8.59% |
| evaluable pre-2010 subset (requested 1991-2009) | 1993-11 | 2009-12 | 194 | 4.17% | 7.19% | 0.605 | -24.69% | -8.59% |
| 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 1.87% | 4.46% | 0.437 | -18.68% | -4.23% |
| decade_1990s | 1993-11 | 1999-12 | 74 | 2.14% | 4.16% | 0.531 | -9.65% | -4.16% |
| decade_2000s | 2000-01 | 2009-12 | 120 | 5.44% | 8.54% | 0.664 | -24.69% | -8.59% |
| decade_2010s | 2010-01 | 2019-12 | 120 | 0.80% | 3.52% | 0.244 | -9.79% | -3.60% |
| decade_2020s | 2020-01 | 2026-05 | 77 | 3.55% | 5.61% | 0.650 | -10.17% | -4.23% |

Overlapping rolling 60-month positive rate: 68.07% (332 windows; adjacent windows share 59 months and are not independent).

### P3 and identically scaled benchmark

| Series / period | Start | End | Months | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P3 full evaluable history | 1996-11 | 2026-05 | 355 | 11.97% | 15.98% | 0.654 | -47.93% | -13.39% |
| Benchmark full evaluable history | 1996-11 | 2026-05 | 355 | 7.46% | 16.51% | 0.389 | -61.27% | -22.24% |
| P3 evaluable pre-2010 subset (requested 1991-2009) | 1996-11 | 2009-12 | 158 | 14.32% | 16.96% | 0.689 | -47.93% | -12.97% |
| Benchmark evaluable pre-2010 subset (requested 1991-2009) | 1996-11 | 2009-12 | 158 | 4.39% | 18.33% | 0.154 | -61.27% | -22.24% |
| P3 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 10.11% | 15.18% | 0.624 | -34.41% | -13.39% |
| Benchmark 2010+ slice (untouched by this run only) | 2010-01 | 2026-05 | 197 | 9.99% | 14.92% | 0.624 | -26.84% | -16.35% |
| P3 decade_1990s | 1996-11 | 1999-12 | 38 | 33.79% | 17.70% | 1.478 | -11.88% | -11.88% |
| Benchmark decade_1990s | 1996-11 | 1999-12 | 38 | 21.62% | 20.10% | 0.843 | -21.52% | -20.26% |
| P3 decade_2000s | 2000-01 | 2009-12 | 120 | 8.77% | 16.52% | 0.428 | -47.93% | -12.97% |
| Benchmark decade_2000s | 2000-01 | 2009-12 | 120 | -0.54% | 17.58% | -0.094 | -61.27% | -22.24% |
| P3 decade_2010s | 2010-01 | 2019-12 | 120 | 8.28% | 14.13% | 0.599 | -33.35% | -12.68% |
| Benchmark decade_2010s | 2010-01 | 2019-12 | 120 | 9.33% | 14.04% | 0.672 | -22.43% | -12.22% |
| P3 decade_2020s | 2020-01 | 2026-05 | 77 | 13.03% | 16.76% | 0.657 | -25.04% | -13.39% |
| Benchmark decade_2020s | 2020-01 | 2026-05 | 77 | 11.01% | 16.28% | 0.560 | -26.84% | -16.35% |

Evaluable-subset full-history CAGR advantage: 4.51%; Sharpe advantage: 0.266; drawdown advantage: 13.34%.
Overlapping rolling 60-month benchmark win rate: 68.92% (296 windows; not independent).

## Breadth and independence diagnostics

### Trend asset classes

| Asset class | Raw annualized average | Base CAGR | Base Sharpe | Base max drawdown | Stress CAGR | Positive |
|---|---:|---:|---:|---:|---:|---:|
| TSMOM^CM | 8.85% | 5.25% | 0.528 | -33.73% | 4.20% | True |
| TSMOM^EQ | 12.66% | 3.56% | 0.386 | -46.24% | 2.54% | True |
| TSMOM^FI | 17.27% | 5.13% | 0.539 | -23.25% | 4.09% | True |
| TSMOM^FX | 8.70% | 3.91% | 0.414 | -32.84% | 2.88% | True |

### Equity regions after locked primary base costs

| Region | Start | Base CAGR | Base Sharpe | Base max drawdown | Stress CAGR | Positive |
|---|---:|---:|---:|---:|---:|---:|
| North America | 1993-11 | 2.03% | 0.287 | -41.13% | 1.02% | True |
| Europe | 1993-11 | 4.86% | 0.799 | -17.27% | 3.82% | True |
| Japan | 1993-11 | 1.03% | 0.190 | -38.91% | 0.03% | True |
| Asia Pacific ex Japan | 1993-11 | 6.95% | 0.947 | -31.95% | 5.89% | True |

### Evaluable-subset return correlations

| | P1 | P2 | Developed benchmark excess |
|---|---:|---:|---:|
| P1 | 1.000 | 0.392 | -0.160 |
| P2 | 0.392 | 1.000 | -0.451 |
| Developed benchmark excess | -0.160 | -0.451 | 1.000 |

## Locked gate diagnostics

### P1

Final status: PASS_LOCKED_HISTORICAL (ALL_LOCKED_GATES_AND_PROTOCOL_AUDITS_MET).
Raw gate on the evaluable subset: met.

- MET - sharpe_at_least_0_50
- MET - development_cagr_positive
- MET - validation_cagr_positive
- MET - rolling_60m_positive_at_least_70pct
- MET - max_drawdown_no_worse_than_minus_40pct
- MET - breadth_at_least_3_of_4
- MET - stress_full_cagr_positive

Cost-interpretation audit: locked primary gate met; proportional-drag sensitivity gate met.

### P2

Final status: DATA_INCONCLUSIVE (INVALID_PROTOCOL_COVERAGE).
Raw gate on the evaluable subset: met.

- MET - sharpe_at_least_0_50
- MET - development_cagr_positive
- MET - validation_cagr_positive
- MET - rolling_60m_positive_at_least_70pct
- MET - max_drawdown_no_worse_than_minus_40pct
- MET - breadth_at_least_3_of_4
- MET - stress_full_cagr_positive

Cost-interpretation audit: locked primary gate met; proportional-drag sensitivity gate not met.

### P3

Final status: DATA_INCONCLUSIVE (INVALID_PROTOCOL_COVERAGE).
Raw gate on the evaluable subset: met.

- MET - cagr_advantage_at_least_5pp
- MET - sharpe_advantage_at_least_0_25
- MET - max_drawdown_no_worse
- MET - development_excess_cagr_positive
- MET - validation_excess_cagr_positive
- MET - rolling_60m_excess_at_least_70pct
- MET - stress_cagr_advantage_at_least_2pp

Cost-interpretation audit: locked primary gate met; proportional-drag sensitivity gate met.

Locked landslide status: DATA_INCONCLUSIVE.
Evaluated-subset landslide check: NO.

## Frozen original-paper older trend diagnostic

| Series | Start | End | Months | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P1 base costs (1985-1990 request; effective after warm-up) | 1988-01 | 1990-12 | 36 | 9.12% | 8.20% | 1.108 | -5.20% | -4.25% |
| P1 stress costs (1985-1990 request; effective after warm-up) | 1988-01 | 1990-12 | 36 | 8.05% | 8.20% | 0.986 | -5.36% | -4.34% |

The 36-month causal volatility lookback leaves only 1988-01 through 1990-12 evaluable in the requested 1985-1990 slice.

## Calculation and funding assumptions

- AQR original-paper returns are used through 2009-12; the current workbook is used only from 2010-01 onward.
- French percentages are converted to decimal returns exactly once.
- Locked primary sleeve costs divide the annual drag by 12 and subtract it once after sleeve scaling.
- The audit-only proportional-drag sensitivity multiplies that same rate by actual sleeve scale; rates are unchanged.
- Volatility at month t uses only t-36 through t-1; leverage is capped at 1.50.
- P3 and its benchmark keep unallocated capital at the published risk-free return.
- Locked primary P3 financing is max(2 x outer scale - 1, 0); it does not include inner sleeve scales.
- The audit-only financing sensitivity uses max(outer scale x (1 + 0.5 x P1 scale + 0.5 x P2 scale) - 1, 0).
- Benchmark financing is max(benchmark scale - 1, 0) in both readings.
- Monthly wealth, including the initial cash mark, is used for drawdown.
- Rolling 60-month windows overlap by 59 months, so their win-rate observations are not independent.

## Limits

These are hypothetical research factors, not executable broker fills. Public series can be revised, and short borrow, turnover, market impact, and capacity are simplified. The 2010+ slice was untouched by this run only, not unknown when the ideas were chosen. P1's historical pass still requires the frozen 6-12 month paper-forward gate; P2 and P3 first require a valid rerun with complete frozen-start coverage.
