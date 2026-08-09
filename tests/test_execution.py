import numpy as np
import pandas as pd
import pytest

from scout import execution


def frames(open_values, close_values, columns=("AAA",)):
    idx = pd.bdate_range("2024-01-02", periods=len(open_values))
    o = pd.DataFrame(open_values, index=idx, columns=columns, dtype=float)
    c = pd.DataFrame(close_values, index=idx, columns=columns, dtype=float)
    return o, c


def zero_cost(**kwargs):
    return execution.ExecutionAssumptions(
        spread_bps=0, slippage_bps=0, commission_bps=0, **kwargs,
    )


def test_next_open_default_removes_same_close_gap_profit():
    o, c = frames([[100], [110], [110]], [[100], [110], [110]])
    honest = execution.simulate_leg(o, c, 0, "AAA", 2, zero_cost())
    same_close = execution.simulate_leg(
        o, c, 0, "AAA", 2, zero_cost(entry_timing="signal_close"),
    )

    assert honest["entry_price_raw"] == 110
    assert honest["end"] == pytest.approx(0.0)
    assert same_close["entry_price_raw"] == 100
    assert same_close["end"] == pytest.approx(0.10)


def test_costs_are_charged_on_entry_and_liquidation():
    o, c = frames([[100], [100], [100]], [[100], [100], [100]])
    assumptions = execution.ExecutionAssumptions(
        spread_bps=10, slippage_bps=5, commission_bps=2,
    )
    out = execution.simulate_leg(o, c, 0, "AAA", 2, assumptions)
    side = (10 / 2 + 5 + 2) / 10_000
    expected = (1 - side) / (1 + side) - 1

    assert out["end"] == pytest.approx(expected)
    assert assumptions.estimated_round_trip_bps == pytest.approx(24)


def test_missing_entry_keeps_its_slot_as_cash_instead_of_reweighting_winner():
    idx = pd.bdate_range("2024-01-02", periods=3)
    o = pd.DataFrame({"WIN": [100, 100, 100], "MISS": [100, np.nan, np.nan]},
                     index=idx)
    c = pd.DataFrame({"WIN": [100, 105, 110], "MISS": [100, np.nan, np.nan]},
                     index=idx)
    sim = execution.simulate_window(o, c, 0, ["WIN", "MISS"], 2, zero_cost())

    assert sim["missing_entries"] == ["MISS"]
    assert sim["outcomes"]["MISS"]["end"] == 0
    assert sim["equity"][-1] == pytest.approx(1.05)


def test_terminal_disappearance_is_total_loss_by_default_and_reported():
    o, c = frames(
        [[100], [100], [100], [100], [np.nan]],
        [[100], [90], [np.nan], [np.nan], [np.nan]],
    )
    total_loss = execution.simulate_leg(o, c, 0, "AAA", 3, zero_cost())
    last_print = execution.simulate_leg(
        o, c, 0, "AAA", 3, zero_cost(missing_leg_policy="last_print"),
    )

    assert total_loss["status"] == "partial_total_loss"
    assert total_loss["end"] == -1
    assert total_loss["missing_terminal_bars"] == 2
    assert last_print["status"] == "partial_last_print"
    assert last_print["end"] == pytest.approx(-0.10)


def test_final_day_gap_that_later_resumes_is_not_invented_as_a_delisting():
    o, c = frames(
        [[100], [100], [100], [100]],
        [[100], [100], [np.nan], [100]],
    )

    out = execution.simulate_leg(o, c, 0, "AAA", 2, zero_cost())

    assert out["status"] == "boundary_gap_last_print"
    assert out["terminal_classification"] == "temporary_gap_confirmed_after_horizon"
    assert out["end"] == pytest.approx(0.0)
    window = execution.simulate_window(o, c, 0, ["AAA"], 2, zero_cost())
    assert window["data_quality_legs"] == ["AAA"]


def test_gap_at_dataset_end_is_unresolved_not_an_automatic_total_loss():
    o, c = frames(
        [[100], [100], [100]],
        [[100], [90], [np.nan]],
    )

    out = execution.simulate_leg(o, c, 0, "AAA", 2, zero_cost())

    assert out["status"] == "unresolved_dataset_boundary_last_print"
    assert out["terminal_classification"] == "no_post_horizon_rows_to_classify"
    assert out["end"] == pytest.approx(-0.10)


def test_interior_quote_gap_is_carried_but_not_called_delisting():
    o, c = frames(
        [[100], [100], [100], [100]],
        [[100], [90], [np.nan], [110]],
    )
    out = execution.simulate_leg(o, c, 0, "AAA", 3, zero_cost())

    assert out["status"] == "complete"
    assert out["path"][2] == pytest.approx(0.9)
    assert out["end"] == pytest.approx(0.10)
