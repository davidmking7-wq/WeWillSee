import pickle
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from scout import backtest, config, data, execution


def _provider_frame(symbols):
    timestamps = pd.to_datetime(["2024-01-02", "2024-01-03"], utc=True)
    index = pd.MultiIndex.from_product(
        [symbols, timestamps], names=["symbol", "timestamp"],
    )
    count = len(index)
    return pd.DataFrame({
        "open": np.arange(count, dtype=float) + 100,
        "close": np.arange(count, dtype=float) + 101,
        "volume": np.arange(count, dtype=float) + 1_000,
    }, index=index)


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get_stock_bars(self, _request):
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(df=response)


def _patch_client(monkeypatch, responses):
    client = _FakeClient(responses)
    monkeypatch.setattr(config, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(config, "ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(data, "StockHistoricalDataClient", lambda *_args: client)
    return client


def test_daily_fetch_retries_then_preserves_complete_coverage(monkeypatch):
    client = _patch_client(
        monkeypatch, [RuntimeError("transient"), _provider_frame(["AAA"])],
    )

    bars = data.daily_ohlcv(
        ["AAA"], 5, max_attempts=2, retry_backoff_seconds=0,
    )

    assert client.calls == 2
    assert bars["metadata"]["status"] == "complete"
    assert bars["metadata"]["threshold_passed"] is True
    assert bars["metadata"]["requested_symbol_count"] == 1
    assert bars["metadata"]["returned_symbol_count"] == 1
    assert bars["metadata"]["missing_symbol_count"] == 0
    assert bars["metadata"]["chunks"][0]["attempts"] == 2


def test_daily_fetch_fails_closed_after_chunk_retries(monkeypatch):
    client = _patch_client(
        monkeypatch, [RuntimeError("one test-secret"), RuntimeError("two")],
    )

    with pytest.raises(data.MarketDataFetchError) as caught:
        data.daily_ohlcv(
            ["AAA"], 5, max_attempts=2, retry_backoff_seconds=0,
        )

    assert client.calls == 2
    assert caught.value.metadata["status"] == "failed_closed_chunk_error"
    assert caught.value.metadata["chunks"][0]["completed"] is False
    assert "test-secret" not in caught.value.metadata["chunks"][0]["errors"][0]["message"]


def test_daily_fetch_fails_closed_when_declared_symbol_coverage_is_missing(monkeypatch):
    _patch_client(monkeypatch, [_provider_frame(["AAA"]), _provider_frame(["AAA"])])

    with pytest.raises(data.MarketDataFetchError) as caught:
        data.daily_ohlcv(
            ["AAA", "BBB"], 5, max_attempts=1, retry_backoff_seconds=0,
        )

    metadata = caught.value.metadata
    assert metadata["status"] == "failed_closed_missing_symbol_threshold"
    assert metadata["missing_symbols"] == ["BBB"]
    assert metadata["declared_threshold"] == {
        "name": "BACKTEST_MAX_MISSING_SYMBOL_FRACTION",
        "max_missing_symbol_fraction": config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION,
    }


def test_daily_fetch_recovers_a_symbol_omitted_from_a_large_batch(monkeypatch):
    client = _patch_client(
        monkeypatch, [_provider_frame(["AAA"]), _provider_frame(["BBB"])],
    )

    bars = data.daily_ohlcv(
        ["AAA", "BBB"], 5, max_attempts=1, retry_backoff_seconds=0,
        max_missing_fraction=0,
    )

    assert client.calls == 2
    assert bars["metadata"]["missing_symbols"] == []
    assert bars["metadata"]["returned_symbol_count"] == 2
    assert bars["metadata"]["chunks"][1]["phase"] == "missing_symbol_recovery"


def test_load_bars_rejects_legacy_cache_without_coverage(monkeypatch, tmp_path):
    idx = pd.bdate_range("2024-01-01", periods=3)
    frame = pd.DataFrame({"SPY": [1.0, 1.1, 1.2]}, index=idx)
    legacy = {"open": frame, "close": frame, "volume": frame}
    cache = tmp_path / "legacy.pkl"
    with open(cache, "wb") as handle:
        pickle.dump(legacy, handle)
    monkeypatch.setattr(backtest, "CACHE", cache)
    monkeypatch.setattr(backtest, "universe_symbols", lambda _mode: ["SPY"])

    with pytest.raises(RuntimeError, match="legacy cache"):
        backtest.load_bars(mode="sp500")


def _bars_for_engine():
    idx = pd.bdate_range("2020-01-01", periods=55)
    base = np.arange(len(idx), dtype=float) + 100
    close = pd.DataFrame({
        "SPY": base,
        "AAA": base * 1.01,
        "PRE": base * 1.02,
        "CCC": base * 1.03,
    }, index=idx)
    close.loc[idx[2], "PRE"] = np.nan
    open_prices = close.ffill().copy()
    open_prices.loc[idx[3], "PRE"] = 123.0  # must not make PRE benchmark-eligible
    volume = close.fillna(1.0) * 1_000
    return {"open": open_prices, "close": close, "volume": volume}


def test_benchmark_membership_uses_signal_close_without_next_open_peek():
    bars = _bars_for_engine()

    def feature_frames(_open, close, _volume):
        return {"score": close}

    def composite(_frames, _ts):
        return pd.DataFrame({"score": [100.0]}, index=["AAA"])

    windows = backtest.run_engine(
        "test", feature_frames, composite, bars, [2], 1, min_pool=1,
        assumptions=execution.ExecutionAssumptions(
            spread_bps=0, slippage_bps=0, commission_bps=0,
        ),
    )

    assert len(windows) == 1
    window = windows[0]
    assert window["benchmark_membership_count"] == 3
    assert window["benchmark_eligible_count"] == 2
    assert window["benchmark_excluded_no_signal_close"] == ["PRE"]
    assert window["benchmark_missing_entries"] == []
    summary = backtest.agg(windows)
    assert summary["benchmark_excluded_no_signal_close_legs"] == 1
    assert summary["benchmark_signal_close_coverage_pct"] == pytest.approx(66.6667)


def test_compound_headlines_one_entry_spy_and_labels_window_resets():
    windows = [
        {
            "strategy_equity": [1.0, 1.10], "spy_equity": [1.0, 1.05],
            "mkt_equity": [1.0, 1.04], "spy_buy_hold_entry_price_fill": 100.0,
            "spy_buy_hold_entry_date": "2020-01-02",
            "spy_buy_hold_exit_price_raw": 105.0,
            "spy_buy_hold_exit_date": "2020-02-01",
            "spy_buy_hold_side_cost_rate": 0.0,
        },
        {
            "strategy_equity": [1.0, 1.20], "spy_equity": [1.0, 1.05],
            "mkt_equity": [1.0, 1.03], "spy_buy_hold_entry_price_fill": 110.0,
            "spy_buy_hold_entry_date": "2020-02-02",
            "spy_buy_hold_exit_price_raw": 130.0,
            "spy_buy_hold_exit_date": "2020-03-01",
            "spy_buy_hold_side_cost_rate": 0.0,
        },
    ]

    result = backtest.compound(windows)

    assert result["headline_benchmark"].startswith("SPY buy-and-hold")
    assert result["spy_buy_and_hold_growth_pct"] == pytest.approx(30.0)
    assert result["spy_buy_and_hold_round_trips"] == 1
    assert result["spy_window_reset_growth_pct"] == pytest.approx(10.25)
    assert result["spy_window_reset_round_trips"] == 2


def test_positions_include_last_signal_with_exact_horizon_remaining():
    idx = pd.bdate_range(
        "2020-01-01", periods=backtest.WARMUP + config.HORIZON_TDAYS + 1,
    )

    assert backtest.positions_for(idx, None, None, 1)[-1] == backtest.WARMUP


def test_data_fingerprint_is_full_and_changes_with_one_value():
    bars = _bars_for_engine()
    original = backtest._data_fingerprint(bars)
    changed = {key: value.copy() for key, value in bars.items()}
    changed["close"].iloc[-1, -1] += 0.01

    assert len(original) == 64
    assert original == backtest._data_fingerprint(bars)
    assert original != backtest._data_fingerprint(changed)


def test_source_hash_is_independent_of_checkout_line_endings():
    lf = backtest._hash_scout_sources([("scout/example.py", b"x = 1\n")])
    crlf = backtest._hash_scout_sources([("scout/example.py", b"x = 1\r\n")])

    assert lf == crlf
