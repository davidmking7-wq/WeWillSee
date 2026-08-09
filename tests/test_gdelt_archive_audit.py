from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

from validation_protocol import gdelt_archive_audit as audit


GOOD_MD5 = "0123456789abcdef0123456789abcdef"
OTHER_MD5 = "fedcba9876543210fedcba9876543210"


def test_expected_inventory_cadence() -> None:
    assert audit._expected_timestamps("v1", date(2025, 1, 1), date(2025, 1, 2)) == [
        "20250101",
        "20250102",
    ]

    expected_v2 = audit._expected_timestamps("v2", date(2025, 1, 1), date(2025, 1, 1))
    assert len(expected_v2) == 96
    assert expected_v2[0] == "20250101000000"
    assert expected_v2[-1] == "20250101234500"

    with pytest.raises(ValueError, match="unsupported GDELT stream"):
        audit._expected_timestamps("unknown", date(2025, 1, 1), date(2025, 1, 1))


def test_v1_parser_requires_matching_positive_size_and_md5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    md5_path = tmp_path / "md5sums"
    size_path = tmp_path / "filesizes"
    md5_path.write_text(
        "\n".join(
            [
                f"{GOOD_MD5}  20250101.gkg.csv.zip",
                f"{GOOD_MD5}  20250102.gkg.csv.zip",
                "not-an-md5  20250103.gkg.csv.zip",
            ]
        ),
        encoding="ascii",
    )
    size_path.write_text(
        "\n".join(
            [
                "123 20250101.gkg.csv.zip",
                "0 20250102.gkg.csv.zip",
                "456 20250103.gkg.csv.zip",
            ]
        ),
        encoding="ascii",
    )

    def fake_fetch(url: str, path: Path, refresh: bool) -> Path:
        del path, refresh
        return md5_path if url == audit.V1_MD5_URL else size_path

    monkeypatch.setattr(audit, "_fetch", fake_fetch)
    inventory, _ = audit._v1_inventory(tmp_path, refresh=False)

    assert list(inventory) == ["20250101"]
    assert inventory["20250101"].size_bytes == 123


def test_v2_parser_rejects_unpinned_urls_zero_sizes_and_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    master_path = tmp_path / "masterfilelist.txt"
    good_name = "20250101000000.gkg.csv.zip"
    foreign_name = "20250101001500.gkg.csv.zip"
    zero_name = "20250101003000.gkg.csv.zip"
    master_path.write_text(
        "\n".join(
            [
                f"123 {GOOD_MD5} {audit.V2_BASE_URL}/{good_name}",
                f"123 {GOOD_MD5} http://example.invalid/{foreign_name}",
                f"0 {GOOD_MD5} {audit.V2_BASE_URL}/{zero_name}",
            ]
        ),
        encoding="ascii",
    )
    monkeypatch.setattr(audit, "_fetch", lambda *args, **kwargs: master_path)

    inventory, _ = audit._v2_inventory(tmp_path, refresh=False)
    assert list(inventory) == ["20250101000000"]

    master_path.write_text(
        "\n".join(
            [
                f"123 {GOOD_MD5} {audit.V2_BASE_URL}/{good_name}",
                f"456 {OTHER_MD5} {audit.V2_BASE_URL}/{good_name}",
            ]
        ),
        encoding="ascii",
    )
    with pytest.raises(ValueError, match="conflicting GDELT v2 archive entries"):
        audit._v2_inventory(tmp_path, refresh=False)


def test_audit_reports_missing_files_and_incomplete_day(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = audit.ArchiveFile(
        timestamp="20250101000000",
        name="20250101000000.gkg.csv.zip",
        url=f"{audit.V2_BASE_URL}/20250101000000.gkg.csv.zip",
        size_bytes=123,
        md5_hex=GOOD_MD5,
    )
    monkeypatch.setattr(
        audit,
        "_load_inventory",
        lambda *args, **kwargs: ({first.timestamp: first}, {audit.V2_MASTER_URL: "hash"}),
    )

    result, selected = audit.audit_inventory(
        "v2", date(2025, 1, 1), date(2025, 1, 1), tmp_path
    )

    assert result["expected_files"] == 96
    assert result["available_files"] == 1
    assert result["missing_file_count"] == 95
    assert result["file_inventory_complete"] is False
    assert result["incomplete_days"] == [{"date": "2025-01-01", "available_files": 1}]
    assert result["transport_warning"] == audit.TRANSPORT_WARNING
    assert list(selected) == [first.timestamp]


def test_download_command_refuses_incomplete_inventory_even_with_execute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        audit,
        "audit_inventory",
        lambda *args, **kwargs: (
            {"file_inventory_complete": False, "missing_file_count": 1},
            {},
        ),
    )
    monkeypatch.setattr(
        audit,
        "_download_file",
        lambda *args, **kwargs: pytest.fail("incomplete inventory must not download"),
    )

    exit_code = audit.main(
        [
            "download",
            "--stream",
            "v2",
            "--start",
            "2025-01-01",
            "--end",
            "2025-01-01",
            "--output-dir",
            str(tmp_path / "raw"),
            "--execute",
        ]
    )

    rendered = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert rendered["download_decision"] == "REFUSED_INCOMPLETE_OFFICIAL_INVENTORY"
    assert not (tmp_path / "raw").exists()


def test_download_rejects_untrusted_item_before_network_or_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = audit.ArchiveFile(
        timestamp="20250101000000",
        name="20250101000000.gkg.csv.zip",
        url="http://127.0.0.1/private",
        size_bytes=123,
        md5_hex=GOOD_MD5,
    )
    monkeypatch.setattr(
        audit._URL_OPENER,
        "open",
        lambda *args, **kwargs: pytest.fail("untrusted URL must not be opened"),
    )

    with pytest.raises(ValueError, match="not the pinned official URL"):
        audit._download_file(item, tmp_path / "raw")
    assert not (tmp_path / "raw").exists()
