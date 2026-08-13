from __future__ import annotations

from contextlib import redirect_stderr
import io
import unittest

import numpy as np
import pandas as pd

from validation_protocol.adapter import StageData
from validation_protocol.runner import (
    DEFAULT_PROTOCOL,
    _hac_ols,
    _parse_args,
    _stable_thirds_selection,
    build_cohorts,
    load_locked_protocol,
    protocol_sha256,
)


class ProtocolLockTests(unittest.TestCase):
    def test_protocol_matches_hash_sidecar(self) -> None:
        protocol = load_locked_protocol(DEFAULT_PROTOCOL)
        sidecar_hash = (
            DEFAULT_PROTOCOL.with_name(protocol["lock"]["hash_sidecar"])
            .read_text(encoding="ascii")
            .split()[0]
        )
        self.assertEqual(protocol_sha256(DEFAULT_PROTOCOL), sidecar_hash)
        self.assertEqual(protocol["origin"]["confirmatory_rule_count"], 1)
        self.assertTrue(protocol["hypothesis"]["single_rule_only"])

    def test_cli_has_no_parameter_override(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                _parse_args(
                    [
                        "--data-root",
                        "unused",
                        "--stage",
                        "unseen_us_companies",
                        "--holding-days",
                        "21",
                    ]
                )


class RuleTests(unittest.TestCase):
    def test_exact_two_stage_tercile_selection(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": [f"C{i:03d}" for i in range(90)],
                "coverage_residual": np.arange(90, dtype=float),
                "momentum": np.arange(90, dtype=float),
            }
        )
        selected = _stable_thirds_selection(frame)
        self.assertEqual(selected, [f"C{i:03d}" for i in range(20, 30)])

    def test_next_open_entry_and_42_session_open_exit(self) -> None:
        protocol = load_locked_protocol(DEFAULT_PROTOCOL)
        dates = pd.bdate_range("2020-01-01", periods=310)
        ids = [f"C{i:03d}" for i in range(90)]
        signal_i = 252
        entry_i = signal_i + 1
        exit_i = entry_i + 42

        price_rows = []
        mention_rows = []
        member_rows = []
        for i, date in enumerate(dates):
            for j, company_id in enumerate(ids):
                # Increasing slopes make C020..C029 the top momentum third
                # inside low-coverage C000..C029.
                close = 100.0 * (1.0 + (j + 1) * i / 1_000_000.0)
                open_tri = 100.0
                if i == signal_i and 20 <= j < 30:
                    open_tri = 1_000_000.0  # must not be read as the entry
                if i == exit_i and 20 <= j < 30:
                    open_tri = 110.0
                price_rows.append(
                    {
                        "date": date,
                        "company_id": company_id,
                        "open_total_return": open_tri,
                        "close_total_return": close,
                        "dollar_volume_usd": 1_000_000.0,
                    }
                )
                mention_rows.append(
                    {
                        "date": date,
                        "company_id": company_id,
                        "mention_count": 1 if j < 30 else 10,
                    }
                )
                member_rows.append(
                    {"date": date, "company_id": company_id, "eligible": True}
                )

        data = StageData(
            prices=pd.DataFrame(price_rows),
            mentions=pd.DataFrame(mention_rows),
            membership=pd.DataFrame(member_rows),
            metadata={},
            file_sha256={},
        )
        stage = {
            "signal_start": dates[signal_i].date().isoformat(),
            "signal_end": dates[signal_i].date().isoformat(),
        }
        cohorts, counters = build_cohorts(data, protocol, stage)
        self.assertEqual(counters["candidate_signal_dates"], 1)
        self.assertEqual(len(cohorts), 1)
        self.assertEqual(cohorts[0].selected_names, 10)
        # 10% open-to-open return less the frozen 20 bp round trip.
        self.assertAlmostEqual(cohorts[0].selected_net, 0.098, places=12)
        self.assertAlmostEqual(cohorts[0].benchmark_gross, 1.0 / 90.0, places=12)

    def test_hac_regression_recovers_positive_alpha(self) -> None:
        rng = np.random.default_rng(20260810)
        benchmark = rng.normal(0.01, 0.03, 300)
        selected = 0.005 + 0.8 * benchmark + rng.normal(0.0, 0.005, 300)
        result = _hac_ols(
            selected,
            np.column_stack([np.ones(len(selected)), benchmark]),
            lag=41,
        )
        self.assertGreater(result["coefficient_0"], 0.004)
        self.assertGreater(result["t_0"], 2.0)
        self.assertAlmostEqual(result["coefficient_1"], 0.8, delta=0.08)


if __name__ == "__main__":
    unittest.main()
