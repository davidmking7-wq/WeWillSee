import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments import candidate_paths


def monthly(values, start="2000-01"):
    index = pd.period_range(start, periods=len(values), freq="M")
    return pd.Series(values, index=index, dtype=float)


def test_causal_volatility_scale_cannot_see_current_return():
    original = monthly(np.linspace(-0.02, 0.03, 40))
    changed = original.copy()
    changed.iloc[36] = 9.0

    original_scale = candidate_paths.causal_vol_scale(original, target=0.10)
    changed_scale = candidate_paths.causal_vol_scale(changed, target=0.10)

    assert original_scale.iloc[36] == pytest.approx(changed_scale.iloc[36])
    assert original_scale.iloc[37] != pytest.approx(changed_scale.iloc[37])


def test_higher_registered_cost_always_reduces_same_month_return():
    gross = monthly([0.02, -0.01, 0.0])
    base = candidate_paths.apply_annual_drag(gross, 0.01)
    stress = candidate_paths.apply_annual_drag(gross, 0.03)

    assert (stress < base).all()
    assert (base - stress).to_numpy() == pytest.approx(np.repeat(0.02 / 12.0, 3))


def test_missing_month_and_missing_value_fail_loudly():
    gap = monthly([0.01, 0.02, 0.03]).drop(pd.Period("2000-02", freq="M"))
    with pytest.raises(candidate_paths.DataValidationError, match="missing month"):
        candidate_paths.validate_monthly_frame(gap, "synthetic")

    missing = monthly([0.01, np.nan, 0.03])
    with pytest.raises(candidate_paths.DataValidationError, match="missing/non-finite"):
        candidate_paths.validate_monthly_frame(missing, "synthetic")

    missing_column = pd.DataFrame({"A": [0.01, 0.02]}, index=monthly([0, 0]).index)
    with pytest.raises(candidate_paths.DataValidationError, match="missing selected series"):
        candidate_paths.validate_monthly_frame(
            missing_column, "synthetic", required_columns=("A", "B")
        )


def test_drawdown_uses_every_monthly_mark_and_initial_cash():
    returns = monthly([0.10, -0.20, 0.05, 0.30])
    assert candidate_paths.max_drawdown(returns) == pytest.approx(-0.20)

    first_month_loss = monthly([-0.25, 0.40])
    assert candidate_paths.max_drawdown(first_month_loss) == pytest.approx(-0.25)


def test_rolling_rate_counts_only_complete_windows():
    returns = monthly(np.repeat(0.01, 61))
    result = candidate_paths.rolling_win_rate(returns, window=60)

    assert result["windows"] == 2
    assert result["win_rate"] == pytest.approx(1.0)


def _coverage_cases(p1_start="1991-01", p2_start="1993-11", p3_start="1996-11"):
    def candidate(start, benchmark=False):
        item = {"periods": {"full": {"start": start}}}
        if benchmark:
            item["benchmark_periods"] = {"full": {"start": start}}
        return item

    case = {
        "P1": candidate(p1_start),
        "P2": candidate(p2_start),
        "P3": candidate(p3_start, benchmark=True),
    }
    return {"base": case, "stress": case}


def _passing_gate(*, landslide=False):
    gate = {"checks": {"synthetic_gate": True}, "failed_checks": [], "passed": True}
    if landslide is not None:
        gate.update(
            {
                "landslide": landslide,
                "landslide_checks": {"synthetic_landslide": landslide},
                "landslide_failed_checks": [] if landslide else ["synthetic_landslide"],
            }
        )
    return gate


def test_protocol_start_gate_fails_closed_and_p3_inherits_p2_invalidity():
    cases = _coverage_cases()
    audit = candidate_paths.protocol_coverage_audit(cases, cases)

    assert audit["candidates"]["P1"]["valid"] is True
    assert audit["candidates"]["P2"]["valid"] is False
    assert audit["candidates"]["P2"]["observed_starts"]["locked_primary_base"] == "1993-11"
    assert audit["candidates"]["P3"]["valid"] is False
    assert "INHERITS_P2_INVALIDITY" in audit["candidates"]["P3"]["reasons"]

    p2 = candidate_paths._honesty_verdict(
        "P2", _passing_gate(landslide=None), audit["candidates"]["P2"]
    )
    p3 = candidate_paths._honesty_verdict(
        "P3", _passing_gate(landslide=True), audit["candidates"]["P3"]
    )
    assert p2["status"] == candidate_paths.DATA_INCONCLUSIVE
    assert p2["status_reason"] == candidate_paths.INVALID_PROTOCOL_COVERAGE
    assert p2["passed"] is None
    assert p3["status"] == candidate_paths.DATA_INCONCLUSIVE
    assert p3["landslide"] is None
    assert p3["landslide_status"] == candidate_paths.DATA_INCONCLUSIVE
    assert p3["evaluated_subset_landslide"] is True


def test_p1_needs_exact_start_and_both_cost_interpretations_for_locked_pass():
    exact_cases = _coverage_cases(p2_start="1991-01", p3_start="1991-01")
    coverage = candidate_paths.protocol_coverage_audit(exact_cases, exact_cases)[
        "candidates"
    ]["P1"]
    primary = _passing_gate(landslide=None)
    alternative_pass = _passing_gate(landslide=None)
    alternative_fail = {
        "checks": {"synthetic_gate": False},
        "failed_checks": ["synthetic_gate"],
        "passed": False,
    }

    passed = candidate_paths._honesty_verdict(
        "P1", primary, coverage, proportional_cost_gate=alternative_pass
    )
    diagnostic = candidate_paths._honesty_verdict(
        "P1", primary, coverage, proportional_cost_gate=alternative_fail
    )
    assert passed["status"] == candidate_paths.PASS_LOCKED_HISTORICAL
    assert passed["passed"] is True
    assert diagnostic["status"] == candidate_paths.DIAGNOSTIC_ONLY
    assert diagnostic["passed"] is None


def test_generated_artifacts_use_fail_closed_status_and_honest_slice_language():
    result_dir = Path(candidate_paths.__file__).with_name("results")
    results = json.loads((result_dir / "candidate_paths_results.json").read_text(encoding="utf-8"))
    report = (result_dir / "candidate_paths_report.md").read_text(encoding="utf-8")

    assert results["pass_fail"]["P1"]["status"] == "PASS_LOCKED_HISTORICAL"
    assert results["pass_fail"]["P2"]["status"] == "DATA_INCONCLUSIVE"
    assert results["pass_fail"]["P3"]["status"] == "DATA_INCONCLUSIVE"
    assert results["pass_fail"]["P3"]["landslide"] is None
    cost_sensitivity = results["audit_sensitivities"][
        "cost_drag_proportional_to_actual_scale"
    ]
    funding_sensitivity = results["audit_sensitivities"][
        "financing_notional_includes_inner_sleeve_scale"
    ]
    assert cost_sensitivity["cases"]["base"]["P2"]["rolling_60m_positive"][
        "win_rate"
    ] == pytest.approx(0.6807228915662651)
    assert cost_sensitivity["cases"]["stress"]["P3"]["advantages"][
        "untouched_2010_latest"
    ]["cagr"] < 0.0
    assert funding_sensitivity["cases"]["stress"]["P3"]["advantages"][
        "untouched_2010_latest"
    ]["cagr"] == pytest.approx(-0.003554143360489981)
    assert results["cases"]["stress"]["P3"]["advantages"][
        "untouched_2010_latest"
    ]["cagr"] == pytest.approx(0.0012801330305081127)
    assert results["metadata"]["source_sha256"]["developed_5.zip"] == (
        "a3cbe11b54908d7f06f50dea1f5c133dd926383792f21aba28a1b0f6cc84f80a"
    )
    assert "P2 starts at 1993-11, not the frozen 1991-01 common start" in report
    assert "P3 and its benchmark start at 1996-11" in report
    assert "2010+ slice was untouched by this run only" in report
    assert "P2 global market-neutral styles | PASS" not in report
    assert "P3 developed core + overlays | PASS" not in report
