import json

import pandas as pd

from scout import audit, backtest, config, execution


def _artifact_engine_payload():
    return {
        "all": {
            "selected_legs": 1, "missing_entries": 0, "partial_legs": 0,
            "data_quality_legs": 0, "benchmark_membership_legs": 1,
            "benchmark_eligible_signal_close_legs": 1,
            "benchmark_excluded_no_signal_close_legs": 0,
            "benchmark_missing_entries": 0, "benchmark_partial_legs": 0,
            "benchmark_data_quality_legs": 0,
        },
        "compounded_non_overlapping": {
            "headline_benchmark": "SPY buy-and-hold: one entry, one final exit",
            "spy_buy_and_hold_growth_pct": 1.0,
            "spy_buy_and_hold_round_trips": 1,
            "spy_window_reset_growth_pct": 1.0,
            "spy_window_reset_round_trips": 1,
            "eqw_market_window_reset_growth_pct": 1.0,
        },
    }


def test_split_leakage_finds_forward_labels_crossing_boundary():
    idx = pd.bdate_range("2020-01-01", periods=420)
    result = audit.split_leakage(
        idx, str(idx[280].date()), str(idx[290].date()), horizon=42, step=5,
    )

    assert result.status == "FAIL"
    assert result.details["leaking_windows"]


def test_split_leakage_passes_with_purged_boundary():
    idx = pd.bdate_range("2020-01-01", periods=420)
    result = audit.split_leakage(
        idx, str(idx[270].date()), str(idx[350].date()), horizon=42, step=5,
    )

    assert result.status == "PASS"


def test_trial_counter_reports_registered_rows(tmp_path):
    path = tmp_path / "hypotheses.md"
    path.write_text(
        "| H1 | date | idea | sign | REGISTERED |\n"
        "| H1b | date | idea | sign | REJECTED |\n"
        "| H2 | date | idea | sign | CONFIRMED |\n",
        encoding="utf-8",
    )
    result = audit.trial_count(path)

    assert result.status == "PASS"
    assert result.details["minimum_registered_trials"] == 3


def test_artifact_check_rejects_missing_execution_metadata(tmp_path):
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"engines": {config.ENGINE: {}}}),
                           encoding="utf-8")
    claims = tmp_path / "claims.md"
    claims.write_text("Results assume no costs.\n", encoding="utf-8")

    result = audit.artifact_and_claim_metadata([result_path], claims)

    assert result.status == "FAIL"
    assert result.details["artifacts"][0]["missing_metadata"]
    assert result.details["stale_claims"]


def test_artifact_check_rejects_assumptions_that_do_not_match_audit(tmp_path):
    expected = execution.ExecutionAssumptions(
        spread_bps=5, slippage_bps=5, commission_bps=0,
    )
    artifact_execution = expected.metadata() | {"spread_bps": 0}
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({
        "artifact": {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "git_commit": "abc", "engine_config": config.ENGINE,
            "data_fingerprint": "123", "entry_timing": expected.entry_timing,
            "execution": artifact_execution,
            "missing_leg_policy": expected.missing_leg_policy,
        },
        "engines": {config.ENGINE: _artifact_engine_payload()},
    }), encoding="utf-8")
    claims = tmp_path / "claims.md"
    claims.write_text("current assumptions\n", encoding="utf-8")

    result = audit.artifact_and_claim_metadata(
        [result_path], claims, expected,
    )

    assert result.status == "FAIL"
    assert "spread_bps" in result.details["artifacts"][0]["assumption_mismatches"]


def test_artifact_check_rejects_explicit_stale_marker(tmp_path):
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({
        "_artifact_status": "STALE_PRE_CORRECTNESS_FIX_DO_NOT_CITE",
        "engines": {config.ENGINE: _artifact_engine_payload()},
    }), encoding="utf-8")
    claims = tmp_path / "claims.md"
    claims.write_text("current assumptions\n", encoding="utf-8")

    result = audit.artifact_and_claim_metadata([result_path], claims)

    assert result.status == "FAIL"
    assert any("explicitly marked STALE" in problem
               for problem in result.details["problems"])


def _compound_window(strategy_end, spy_end=1.10):
    return {
        "strategy_equity": [1.0, strategy_end],
        "spy_equity": [1.0, spy_end],
        "mkt_equity": [1.0, 1.0],
        "spy_buy_hold_entry_price_fill": 100.0,
        "spy_buy_hold_entry_date": "2020-01-02",
        "spy_buy_hold_exit_price_raw": 110.0,
        "spy_buy_hold_exit_date": "2020-03-01",
        "spy_buy_hold_side_cost_rate": 0.0,
    }


def test_cost_check_fails_if_costs_appear_beneficial(monkeypatch):
    idx = pd.bdate_range("2020-01-01", periods=400)
    bars = {"close": pd.DataFrame({"SPY": 1.0}, index=idx)}

    def fake_run(*_args, assumptions, **_kwargs):
        return [_compound_window(1.25 if assumptions.side_cost_rate else 1.20)]

    monkeypatch.setattr(audit.backtest, "positions_for", lambda *_args: [300])
    monkeypatch.setattr(audit.backtest, "run_engine", fake_run)
    result = audit.cost_sensitivity(
        bars, "sp500", 5, 21,
        execution.ExecutionAssumptions(spread_bps=5, slippage_bps=5),
    )

    assert result.status == "FAIL"
    assert result.details["drag_pct_points"] < 0
    assert "declared costs appear to improve the result" in result.details["problems"]


def test_cost_check_requires_net_outperformance_of_continuous_spy(monkeypatch):
    idx = pd.bdate_range("2020-01-01", periods=400)
    bars = {"close": pd.DataFrame({"SPY": 1.0}, index=idx)}

    def fake_run(*_args, assumptions, **_kwargs):
        return [_compound_window(1.05 if assumptions.side_cost_rate else 1.06)]

    monkeypatch.setattr(audit.backtest, "positions_for", lambda *_args: [300])
    monkeypatch.setattr(audit.backtest, "run_engine", fake_run)
    result = audit.cost_sensitivity(
        bars, "sp500", 5, 21,
        execution.ExecutionAssumptions(spread_bps=5, slippage_bps=5),
    )

    assert result.status == "FAIL"
    assert result.details["drag_pct_points"] > 0
    assert result.details["net_excess_over_spy_buy_hold_pct_points"] < 0


def test_strict_exit_treats_warn_and_skip_as_unresolved_until_named_waiver():
    checks = [
        audit.Check("pass", "PASS", "ok", {}),
        audit.Check("warning", "WARN", "uncertain", {}),
        audit.Check("skipped", "SKIP", "missing", {}),
    ]

    assert [c.name for c in audit.unresolved_checks(checks)] == ["warning", "skipped"]
    assert [c.name for c in audit.unresolved_checks(checks, {"warning"})] == ["skipped"]


def test_random_control_with_no_lift_is_a_failure(monkeypatch):
    symbols = [f"S{i:02d}" for i in range(50)]
    idx = pd.bdate_range("2020-01-01", periods=2)
    frame = pd.DataFrame(1.0, index=idx, columns=["SPY", *symbols])
    bars = {"open": frame, "close": frame, "volume": frame}
    monkeypatch.setattr(audit.backtest, "positions_for", lambda *_args: [0])
    monkeypatch.setattr(
        audit.signals, "feature_frames", lambda *_args: {"unused": frame},
    )
    monkeypatch.setattr(
        audit.signals, "composite_at",
        lambda *_args: pd.DataFrame({"score": range(50)}, index=symbols),
    )

    def fake_simulate(_open, _close, _pos, selected, _horizon, _assumptions):
        return {"outcomes": {
            symbol: {"end": 0.0, "hit": False} for symbol in selected
        }}

    monkeypatch.setattr(audit.execution, "simulate_window", fake_simulate)
    result = audit.random_pick_lift(
        bars, "sp500", 5, 21, 20, execution.DEFAULT_EXECUTION,
    )

    assert result.status == "FAIL"
    assert result.details["return_percentile"] == 0.0
    assert result.details["hit_percentile"] == 0.0


def test_artifact_provenance_can_verify_source_and_loaded_data(tmp_path, monkeypatch):
    idx = pd.bdate_range("2024-01-01", periods=3)
    frame = pd.DataFrame({"SPY": [100.0, 101.0, 102.0]}, index=idx)
    fetch = {
        "coverage_schema_version": 1,
        "status": "complete",
        "requested_symbols": ["SPY"], "requested_symbol_count": 1,
        "returned_symbols": ["SPY"], "returned_symbol_count": 1,
        "missing_symbols": [], "missing_symbol_count": 0,
        "missing_symbol_fraction": 0.0,
        "declared_threshold": {
            "name": "BACKTEST_MAX_MISSING_SYMBOL_FRACTION",
            "max_missing_symbol_fraction":
                config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION,
        },
        "threshold_passed": True, "universe_mode": "sp500",
        "observed_start": "2024-01-01T00:00:00+00:00",
        "observed_end": "2024-01-03T00:00:00+00:00",
        "chunks": [{"chunk_number": 1, "attempts": 1, "completed": True}],
    }
    bars = {
        "open": frame.copy(), "close": frame.copy(), "volume": frame.copy(),
        "metadata": fetch,
    }
    signal_span = ["2024-01-01", "2024-01-03"]
    assumptions = execution.DEFAULT_EXECUTION
    source_hash = backtest._scout_source_hash()
    monkeypatch.setattr(backtest, "_git_scout_source_hash", lambda _commit: source_hash)
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({
        "span": signal_span,
        "artifact": {
            "provenance_schema_version": 2,
            "generated_at": "2026-01-01T00:00:00+00:00",
            "git_commit": backtest._git_state()["commit"],
            "git_dirty": False,
            "scout_source_hash": source_hash,
            "engine_config": config.ENGINE,
            "data_fingerprint": backtest._data_fingerprint(bars),
            "universe_mode": "sp500", "signal_span": signal_span,
            "data_span": signal_span,
            "data_coverage": backtest._data_coverage(bars, "sp500"),
            "entry_timing": assumptions.entry_timing,
            "execution": assumptions.metadata(),
            "missing_leg_policy": assumptions.missing_leg_policy,
        },
        "engines": {config.ENGINE: _artifact_engine_payload()},
    }), encoding="utf-8")
    claims = tmp_path / "claims.md"
    claims.write_text("Current assumptions.\n", encoding="utf-8")

    result = audit.artifact_and_claim_metadata(
        [result_path], claims, assumptions, bars, "sp500",
    )

    assert result.status == "PASS"
    assert result.details["artifacts"][0]["data_fingerprint_verified"] is True
