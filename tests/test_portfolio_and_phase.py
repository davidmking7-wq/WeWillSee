import pandas as pd
import pytest

from scout import execution, phase_lab, portfolio_lab


def zero_cost():
    return execution.ExecutionAssumptions(
        spread_bps=0, slippage_bps=0, commission_bps=0,
    )


def test_metrics_use_daily_drawdown_not_period_end_only():
    m = portfolio_lab.metrics([0.10], equity_curve=[1.0, 0.5, 1.10])

    assert m["compounded"] == pytest.approx(10.0)
    assert m["max_dd"] == pytest.approx(-50.0)
    assert m["drawdown_frequency"] == "daily"


def test_phase_sleeve_retains_intraperiod_crash_in_daily_curve():
    idx = pd.bdate_range("2024-01-02", periods=43)
    prices = [100.0] * 43
    prices[10] = 50.0
    prices[42] = 110.0
    o = pd.DataFrame({"AAA": [100.0] * 43}, index=idx)
    c = pd.DataFrame({"AAA": prices}, index=idx)
    scan = {"pos": 0, "ranked": ["AAA"], "date": "2024-01-02"}

    curve, skipped = phase_lab.sleeve_curve(
        o, c, {0: scan}, [0, 42], 1, 0, 21, zero_cost(),
    )
    rets = phase_lab.sampled(curve, [0, 42], 1)
    m = portfolio_lab.metrics(rets, equity_curve=[curve[t] for t in range(43)])

    assert skipped == 0
    assert curve[10] == pytest.approx(0.5)
    assert curve[42] == pytest.approx(1.1)
    assert m["max_dd"] == pytest.approx(-50.0)


def test_rolling_strategy_fills_signal_at_next_open_and_keeps_daily_equity():
    idx = pd.bdate_range("2024-01-02", periods=43)
    o = pd.DataFrame({"AAA": [100.0] + [110.0] * 42}, index=idx)
    c = pd.DataFrame({"AAA": [100.0] + [110.0] * 42}, index=idx)
    scans = [{
        "pos": 0, "ranked": ["AAA"], "sigma42": {"AAA": 0.2},
        "bull": True, "date": str(idx[0].date()),
    }]

    rets, details = portfolio_lab.rolling_strategy(
        c, idx, scans, 1, open_prices=o, assumptions=zero_cost(),
        return_details=True,
    )

    assert rets == pytest.approx([0.0])
    assert len(details["equity_curve"]) == 43
    assert details["equity_curve"][1] == pytest.approx(1.0)


def test_rolling_close_trigger_exits_at_next_open_not_the_triggering_close():
    idx = pd.bdate_range("2024-01-02", periods=44)
    opens = [100.0, 100.0, 80.0] + [80.0] * 41
    closes = [100.0, 110.0, 80.0] + [80.0] * 41
    o = pd.DataFrame({"AAA": opens}, index=idx)
    c = pd.DataFrame({"AAA": closes}, index=idx)
    scans = [{
        "pos": 0, "ranked": ["AAA"], "sigma42": {"AAA": 0.2},
        "bull": True, "date": str(idx[0].date()),
    }]

    _, details = portfolio_lab.rolling_strategy(
        c, idx, scans, 1, open_prices=o, assumptions=zero_cost(),
        return_details=True,
    )

    assert details["exit_fills"][0][2] == "target"
    assert details["exit_fills"][0][3] == str(idx[2].date())
    assert details["equity_curve"][1] == pytest.approx(1.10)
    assert details["equity_curve"][2] == pytest.approx(0.80)
