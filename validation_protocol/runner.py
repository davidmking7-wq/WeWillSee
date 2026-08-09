"""Runner for the single locked H33 external-validation rule."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .adapter import DataContractError, StageData, load_stage_data


DEFAULT_PROTOCOL = Path(__file__).with_name("preregistration_h33_locked_v1.json")


class ProtocolLockError(ValueError):
    """Raised when the preregistration no longer matches its lock sidecar."""


@dataclass(frozen=True)
class Cohort:
    signal_date: pd.Timestamp
    selected_net: float
    benchmark_gross: float
    selected_names: int
    eligible_names: int


def protocol_sha256(path: str | Path) -> str:
    # The lock protects the JSON rules, not Git's platform-specific checkout
    # line endings.  Hash canonical LF bytes so the same committed protocol
    # verifies on Windows (CRLF) and Unix (LF).
    canonical = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return sha256(canonical).hexdigest()


def load_locked_protocol(path: str | Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = Path(path)
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("lock", {}).get("status") != "LOCKED_BEFORE_EXTERNAL_DATA_FETCH":
        raise ProtocolLockError("protocol does not have the required locked status")
    sidecar = path.with_name(protocol["lock"]["hash_sidecar"])
    if not sidecar.is_file():
        raise ProtocolLockError(f"missing protocol hash sidecar: {sidecar}")
    expected = sidecar.read_text(encoding="ascii").strip().split()[0].lower()
    actual = protocol_sha256(path)
    if expected != actual:
        raise ProtocolLockError(
            f"protocol hash mismatch: expected {expected}, calculated {actual}"
        )
    return protocol


def _stage_spec(protocol: dict[str, Any], stage_id: str) -> dict[str, Any]:
    matches = [stage for stage in protocol["stages"] if stage["stage_id"] == stage_id]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicated stage_id: {stage_id}")
    return matches[0]


def _wide(frame: pd.DataFrame, value: str, dates: pd.DatetimeIndex, ids: list[str]) -> pd.DataFrame:
    return (
        frame.pivot(index="date", columns="company_id", values=value)
        .reindex(index=dates, columns=ids)
    )


def _stable_thirds_selection(features: pd.DataFrame) -> list[str]:
    """Apply the two exact stable sorts frozen in the preregistration."""

    needed = {"company_id", "coverage_residual", "momentum"}
    if not needed.issubset(features.columns):
        raise ValueError(f"features must contain {sorted(needed)}")
    ordered = features.sort_values(
        ["coverage_residual", "company_id"], kind="stable"
    ).reset_index(drop=True)
    low = ordered.iloc[: len(ordered) // 3].copy()
    low = low.sort_values(["momentum", "company_id"], kind="stable").reset_index(drop=True)
    selected = low.iloc[(2 * len(low)) // 3 :]
    return selected["company_id"].astype(str).tolist()


def _coverage_residual(coverage: pd.Series, adv: pd.Series) -> pd.Series:
    y = np.log1p(coverage.to_numpy(dtype=float))
    x = np.log(adv.to_numpy(dtype=float))
    design = np.column_stack([np.ones(len(x)), x])
    coefficient = np.linalg.lstsq(design, y, rcond=None)[0]
    return pd.Series(y - design @ coefficient, index=coverage.index)


def _hac_ols(y: np.ndarray, x: np.ndarray, lag: int) -> dict[str, float]:
    """OLS with a Bartlett-kernel Newey-West covariance matrix."""

    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if len(y) != len(x) or len(y) <= x.shape[1] + lag:
        raise ValueError("not enough observations for the requested HAC regression")
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ beta
    xu = x * resid[:, None]
    meat = xu.T @ xu
    for offset in range(1, lag + 1):
        weight = 1.0 - offset / (lag + 1.0)
        gamma = xu[offset:].T @ xu[:-offset]
        meat += weight * (gamma + gamma.T)
    bread = np.linalg.pinv(x.T @ x)
    covariance = bread @ meat @ bread
    covariance *= len(y) / (len(y) - x.shape[1])
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    t_value = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    return {
        "coefficient_0": float(beta[0]),
        "se_0": float(se[0]),
        "t_0": float(t_value[0]),
        **(
            {
                "coefficient_1": float(beta[1]),
                "se_1": float(se[1]),
                "t_1": float(t_value[1]),
            }
            if x.shape[1] > 1
            else {}
        ),
    }


def _prepare_matrices(data: StageData) -> dict[str, Any]:
    dates = pd.DatetimeIndex(sorted(data.prices["date"].unique()))
    ids = sorted(
        set(data.prices["company_id"].astype(str))
        | set(data.mentions["company_id"].astype(str))
        | set(data.membership["company_id"].astype(str))
    )
    open_tri = _wide(data.prices, "open_total_return", dates, ids)
    close_tri = _wide(data.prices, "close_total_return", dates, ids)
    dollar_volume = _wide(data.prices, "dollar_volume_usd", dates, ids)
    mentions = _wide(data.mentions, "mention_count", dates, ids).fillna(0.0)
    membership = _wide(data.membership, "eligible", dates, ids).fillna(False).astype(bool)
    return {
        "dates": dates,
        "ids": ids,
        "open": open_tri,
        "close": close_tri,
        "dollar_volume": dollar_volume,
        "mentions": mentions,
        "membership": membership,
    }


def build_cohorts(
    data: StageData,
    protocol: dict[str, Any],
    stage: dict[str, Any],
) -> tuple[list[Cohort], dict[str, int]]:
    matrices = _prepare_matrices(data)
    dates: pd.DatetimeIndex = matrices["dates"]
    lookback = int(protocol["rule"]["coverage_proxy"]["lookback_sessions"])
    skip = int(protocol["rule"]["momentum"]["skip_recent_sessions"])
    hold = int(protocol["rule"]["portfolio"]["holding_sessions"])
    min_pool = int(protocol["rule"]["portfolio"]["minimum_full_eligible_pool"])
    min_selected = int(protocol["rule"]["portfolio"]["minimum_selected_names"])
    cost = float(protocol["rule"]["portfolio"]["round_trip_cost_bps"]) / 10_000.0

    coverage = matrices["mentions"].rolling(lookback, min_periods=lookback).sum().shift(1)
    adv = matrices["dollar_volume"].rolling(lookback, min_periods=lookback).mean().shift(1)
    momentum = matrices["close"].shift(skip) / matrices["close"].shift(lookback) - 1.0

    start = pd.Timestamp(stage["signal_start"])
    end = pd.Timestamp(stage["signal_end"]) if stage.get("signal_end") else dates.max()
    counters = {
        "candidate_signal_dates": 0,
        "thin_or_incomplete_pool": 0,
        "missing_exit_formations": 0,
        "too_few_selected_names": 0,
    }
    cohorts: list[Cohort] = []

    for i, date in enumerate(dates):
        if date < start or date > end or i + hold + 1 >= len(dates):
            continue
        counters["candidate_signal_dates"] += 1
        member = matrices["membership"].iloc[i]
        feature_ok = (
            member
            & coverage.iloc[i].notna()
            & adv.iloc[i].notna()
            & (adv.iloc[i] > 0)
            & momentum.iloc[i].notna()
        )
        pool_ids = feature_ok[feature_ok].index.astype(str).tolist()
        if len(pool_ids) < min_pool:
            counters["thin_or_incomplete_pool"] += 1
            continue

        entry = matrices["open"].iloc[i + 1][pool_ids]
        exit_ = matrices["open"].iloc[i + hold + 1][pool_ids]
        if entry.isna().any() or exit_.isna().any() or (entry <= 0).any() or (exit_ <= 0).any():
            counters["missing_exit_formations"] += 1
            continue
        forward = exit_ / entry - 1.0

        residual = _coverage_residual(coverage.iloc[i][pool_ids], adv.iloc[i][pool_ids])
        features = pd.DataFrame(
            {
                "company_id": pool_ids,
                "coverage_residual": residual.reindex(pool_ids).to_numpy(),
                "momentum": momentum.iloc[i][pool_ids].to_numpy(),
            }
        )
        selected_ids = _stable_thirds_selection(features)
        if len(selected_ids) < min_selected:
            counters["too_few_selected_names"] += 1
            continue

        cohorts.append(
            Cohort(
                signal_date=date,
                selected_net=float(forward[selected_ids].mean() - cost),
                benchmark_gross=float(forward.mean()),
                selected_names=len(selected_ids),
                eligible_names=len(pool_ids),
            )
        )
    return cohorts, counters


def _metrics(cohorts: list[Cohort], protocol: dict[str, Any]) -> dict[str, Any]:
    frame = pd.DataFrame([cohort.__dict__ for cohort in cohorts]).sort_values("signal_date")
    y = frame["selected_net"].to_numpy(dtype=float)
    benchmark = frame["benchmark_gross"].to_numpy(dtype=float)
    active = y - benchmark
    lag = 41
    annualizer = float(protocol["statistics"]["annualization_factor"])

    alpha_reg = _hac_ols(y, np.column_stack([np.ones(len(y)), benchmark]), lag)
    active_reg = _hac_ols(active, np.ones((len(active), 1)), lag)
    midpoint = len(active) // 2
    half_1 = float(np.mean(active[:midpoint]) * annualizer)
    half_2 = float(np.mean(active[midpoint:]) * annualizer)
    return {
        "valid_formations": int(len(frame)),
        "effective_nonoverlap_blocks_floor": int(len(frame) // 42),
        "signal_first": frame["signal_date"].iloc[0].date().isoformat(),
        "signal_last": frame["signal_date"].iloc[-1].date().isoformat(),
        "annualized_alpha": float(alpha_reg["coefficient_0"] * annualizer),
        "hac_alpha_t": float(alpha_reg["t_0"]),
        "beta": float(alpha_reg["coefficient_1"]),
        "annualized_mean_active_return": float(np.mean(active) * annualizer),
        "hac_active_t": float(active_reg["t_0"]),
        "chronological_half_1_annualized_active": half_1,
        "chronological_half_2_annualized_active": half_2,
        "selected_name_count_min": int(frame["selected_names"].min()),
        "selected_name_count_median": float(frame["selected_names"].median()),
        "eligible_name_count_median": float(frame["eligible_names"].median()),
    }


def _stage_pass(metrics: dict[str, Any], protocol: dict[str, Any]) -> tuple[bool, list[str]]:
    thresholds = protocol["statistics"]["stage_pass_all_required"]
    checks = {
        "annualized_alpha": metrics["annualized_alpha"] >= thresholds["annualized_alpha_min"],
        "hac_alpha_t": metrics["hac_alpha_t"] >= thresholds["hac_alpha_t_min"],
        "annualized_mean_active_return": metrics["annualized_mean_active_return"]
        >= thresholds["annualized_mean_active_return_min"],
        "chronological_half_1_annualized_active": metrics[
            "chronological_half_1_annualized_active"
        ]
        >= thresholds["chronological_half_1_annualized_active_min"],
        "chronological_half_2_annualized_active": metrics[
            "chronological_half_2_annualized_active"
        ]
        >= thresholds["chronological_half_2_annualized_active_min"],
    }
    failures = [name for name, passed in checks.items() if not passed]
    return not failures, failures


def run_stage(
    data_root: str | Path,
    stage_id: str,
    protocol_path: str | Path = DEFAULT_PROTOCOL,
) -> dict[str, Any]:
    protocol = load_locked_protocol(protocol_path)
    stage = _stage_spec(protocol, stage_id)
    data, quality_failures = load_stage_data(data_root, stage_id, protocol)

    audit = {
        "prior_exploratory_trials_disclosed": protocol["origin"][
            "prior_exploratory_trials_disclosed"
        ],
        "confirmatory_rule_count": protocol["origin"]["confirmatory_rule_count"],
        "stage_order": stage["order"],
    }

    if quality_failures:
        return {
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": protocol_sha256(protocol_path),
            "stage_id": stage_id,
            "decision": "DATA_INCONCLUSIVE",
            "audit": audit,
            "data_quality_failures": quality_failures,
            "data_file_sha256": data.file_sha256,
        }

    cohorts, counters = build_cohorts(data, protocol, stage)
    quality_failures = []
    if counters["missing_exit_formations"]:
        quality_failures.append(
            f"{counters['missing_exit_formations']} formations had missing entry/exit values"
        )
    if len(cohorts) < int(stage["minimum_valid_formations"]):
        quality_failures.append(
            f"valid formations {len(cohorts)} below frozen minimum {stage['minimum_valid_formations']}"
        )
    effective_blocks = len(cohorts) // int(protocol["rule"]["portfolio"]["holding_sessions"])
    if effective_blocks < int(stage["minimum_effective_nonoverlap_blocks"]):
        quality_failures.append(
            "effective non-overlap blocks "
            f"{effective_blocks} below frozen minimum {stage['minimum_effective_nonoverlap_blocks']}"
        )
    if quality_failures:
        return {
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": protocol_sha256(protocol_path),
            "stage_id": stage_id,
            "decision": "DATA_INCONCLUSIVE",
            "audit": audit,
            "data_quality_failures": quality_failures,
            "formation_counters": counters,
            "data_file_sha256": data.file_sha256,
        }

    metrics = _metrics(cohorts, protocol)
    passed, threshold_failures = _stage_pass(metrics, protocol)
    return {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_sha256(protocol_path),
        "stage_id": stage_id,
        "decision": "PASS" if passed else "FAIL",
        "audit": audit,
        "failed_thresholds": threshold_failures,
        "metrics": metrics,
        "formation_counters": counters,
        "data_quality_failures": [],
        "data_file_sha256": data.file_sha256,
        "interpretation_limit": protocol["public_data_plan_and_limits"]["conclusion_limit"],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one stage of the locked H33 validation; parameters cannot be overridden."
    )
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--stage",
        required=True,
        choices=[
            "unseen_us_companies",
            "older_us_pre2016",
            "international_uk",
            "future_paper_us",
        ],
    )
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run_stage(args.data_root, args.stage, args.protocol)
    except (DataContractError, ProtocolLockError, ValueError, json.JSONDecodeError) as exc:
        result = {"stage_id": args.stage, "decision": "DATA_INCONCLUSIVE", "error": str(exc)}
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result.get("decision") in {"PASS", "FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
