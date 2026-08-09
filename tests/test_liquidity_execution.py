import pandas as pd
import pytest

from scout import liquidity_lab


def test_liquidity_gate_compares_costed_picks_with_spy():
    rows = pd.DataFrame([
        {
            "gate": 10_000_000.0,
            "pos": 1,
            "date": "2024-01-02",
            "sym": "AAA",
            "pool": 100,
            "end": 0.06,
            "mx": 0.08,
            "hit": True,
            "hit10": False,
            "dip": False,
            "cs": 0.02,
            "dv": 20_000_000.0,
            "spy": 0.05,
        }
    ])

    result = liquidity_lab.summarise_gate(
        rows, 10_000_000.0, {"AAA": "small"},
    )

    assert result["gross_pct"] == pytest.approx(6.0)
    assert result["net_pct"] == pytest.approx(4.0)
    assert result["beat_spy_gross_pct"] == pytest.approx(100.0)
    assert result["beat_spy_pct"] == pytest.approx(0.0)
