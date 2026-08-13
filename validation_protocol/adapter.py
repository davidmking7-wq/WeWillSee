"""Strict CSV adapter for the locked H33 validation protocol.

This module deliberately contains no downloader and reads no environment
variables.  External data must be prepared after the protocol lock and placed
under the stage directory described in the preregistration.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pandas as pd


PRICE_COLUMNS = {
    "date",
    "company_id",
    "open_total_return",
    "close_total_return",
    "dollar_volume_usd",
}
MENTION_COLUMNS = {"date", "company_id", "mention_count"}
MEMBERSHIP_COLUMNS = {"date", "company_id", "eligible"}


class DataContractError(ValueError):
    """Raised when a supplied panel cannot support an honest locked test."""


@dataclass(frozen=True)
class StageData:
    prices: pd.DataFrame
    mentions: pd.DataFrame
    membership: pd.DataFrame
    metadata: dict[str, Any]
    file_sha256: dict[str, str]


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise DataContractError(f"missing required file: {path}")
    frame = pd.read_csv(path)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DataContractError(f"{path.name} is missing columns: {missing}")
    frame = frame.loc[:, sorted(required)].copy()
    frame["company_id"] = frame["company_id"].astype("string").str.strip()
    if frame["company_id"].isna().any() or (frame["company_id"] == "").any():
        raise DataContractError(f"{path.name} contains a blank company_id")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame.duplicated(["date", "company_id"]).any():
        raise DataContractError(f"{path.name} has duplicate date/company_id rows")
    return frame.sort_values(["date", "company_id"], kind="stable").reset_index(drop=True)


def _coerce_bool(series: pd.Series, label: str) -> pd.Series:
    mapping = {
        True: True,
        False: False,
        1: True,
        0: False,
        "1": True,
        "0": False,
        "true": True,
        "false": False,
        "TRUE": True,
        "FALSE": False,
    }
    out = series.map(mapping)
    if out.isna().any():
        bad = sorted(series[out.isna()].astype(str).unique().tolist())
        raise DataContractError(f"{label} contains non-boolean values: {bad[:5]}")
    return out.astype(bool)


def _validate_metadata(
    metadata: dict[str, Any], protocol: dict[str, Any], stage_id: str
) -> list[str]:
    failures: list[str] = []
    if metadata.get("stage_id") != stage_id:
        failures.append("metadata.stage_id does not match the requested stage")

    contract = protocol["data_contract"]
    for key in contract["metadata_json_required_true"]:
        if metadata.get(key) is not True:
            failures.append(f"metadata.{key} must be true")
    for key in contract["metadata_json_required_strings"]:
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"metadata.{key} must be a non-empty string")

    if stage_id in contract.get("discovery_exclusion_stages", []):
        for key in contract.get("discovery_exclusion_additional_true", []):
            if metadata.get(key) is not True:
                failures.append(f"metadata.{key} must be true")
        for key in contract.get("discovery_exclusion_additional_strings", []):
            value = metadata.get(key)
            if not isinstance(value, str) or not value.strip():
                failures.append(f"metadata.{key} must be a non-empty string")

    if metadata.get("mention_source") != protocol["rule"]["coverage_proxy"]["source_lock"]:
        failures.append("metadata.mention_source differs from the frozen GDELT proxy")

    prepared = metadata.get("prepared_at_utc")
    if isinstance(prepared, str) and prepared.strip():
        try:
            prepared_time = pd.Timestamp(prepared)
            lock_time = pd.Timestamp(protocol["lock"]["locked_at_utc"])
            if prepared_time.tzinfo is None:
                prepared_time = prepared_time.tz_localize("UTC")
            else:
                prepared_time = prepared_time.tz_convert("UTC")
            if prepared_time < lock_time:
                failures.append("metadata.prepared_at_utc predates the protocol lock")
        except ValueError:
            failures.append("metadata.prepared_at_utc is not a valid timestamp")
    return failures


def load_stage_data(
    data_root: str | Path,
    stage_id: str,
    protocol: dict[str, Any],
) -> tuple[StageData, list[str]]:
    """Load one stage and return the data plus non-negotiable quality failures."""

    stage_dir = Path(data_root) / stage_id
    paths = {
        "prices.csv": stage_dir / "prices.csv",
        "mentions.csv": stage_dir / "mentions.csv",
        "membership.csv": stage_dir / "membership.csv",
        "metadata.json": stage_dir / "metadata.json",
    }
    if not paths["metadata.json"].is_file():
        raise DataContractError(f"missing required file: {paths['metadata.json']}")
    metadata = json.loads(paths["metadata.json"].read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise DataContractError("metadata.json must contain one JSON object")

    prices = _read_csv(paths["prices.csv"], PRICE_COLUMNS)
    mentions = _read_csv(paths["mentions.csv"], MENTION_COLUMNS)
    membership = _read_csv(paths["membership.csv"], MEMBERSHIP_COLUMNS)

    numeric_price = ["open_total_return", "close_total_return", "dollar_volume_usd"]
    for column in numeric_price:
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    mentions["mention_count"] = pd.to_numeric(mentions["mention_count"], errors="coerce")
    membership["eligible"] = _coerce_bool(membership["eligible"], "membership.eligible")

    if prices[numeric_price].isna().any().any():
        raise DataContractError("prices.csv has missing or non-numeric required values")
    if (prices[["open_total_return", "close_total_return"]] <= 0).any().any():
        raise DataContractError("open and close total-return values must be positive")
    if (prices["dollar_volume_usd"] < 0).any():
        raise DataContractError("dollar_volume_usd must be non-negative")
    if mentions["mention_count"].isna().any() or (mentions["mention_count"] < 0).any():
        raise DataContractError("mention_count must be finite and non-negative")
    if ((mentions["mention_count"] % 1) != 0).any():
        raise DataContractError("mention_count must be an integer document count")

    hashes = {name: sha256_file(path) for name, path in paths.items()}
    failures = _validate_metadata(metadata, protocol, stage_id)
    return StageData(prices, mentions, membership, metadata, hashes), failures
