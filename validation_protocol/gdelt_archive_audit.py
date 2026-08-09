"""Audit and fetch the official GDELT GKG archive without relaxing H33.

This utility checks file-level availability only.  A complete file inventory is
necessary, but not sufficient, to certify the preregistration's
``gdelt_archive_days_complete`` metadata gate.  Entity mapping, record parsing,
and exchange-session attribution must still be audited separately.

Examples
--------
Audit the historical US/UK stage window against the daily GKG 1.0 stream::

    python -m validation_protocol.gdelt_archive_audit audit \
      --stream v1 --start 2017-01-03 --end 2025-12-31

Audit the same window against the 15-minute GKG 2.x stream::

    python -m validation_protocol.gdelt_archive_audit audit \
      --stream v2 --start 2017-01-03 --end 2025-12-31

Download a short date range only after its official inventory is complete::

    python -m validation_protocol.gdelt_archive_audit download \
      --stream v2 --start 2017-01-03 --end 2017-01-03 \
      --output-dir path/to/raw-gdelt --execute
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import md5, sha256
import json
from pathlib import Path
import re
import sys
from typing import Iterable, TypeVar
from urllib.request import HTTPRedirectHandler, Request, build_opener


# GDELT's data host currently serves these archive endpoints over HTTP.  The
# URLs are the official endpoints linked from https://www.gdeltproject.org/data.html.
V1_BASE_URL = "http://data.gdeltproject.org/gkg"
V1_MD5_URL = f"{V1_BASE_URL}/md5sums"
V1_SIZE_URL = f"{V1_BASE_URL}/filesizes"
V2_BASE_URL = "http://data.gdeltproject.org/gdeltv2"
V2_MASTER_URL = f"{V2_BASE_URL}/masterfilelist.txt"
USER_AGENT = "WeWillSee-H33-archive-audit/1.0"
STREAMS = ("v1", "v2")
TRANSPORT_WARNING = (
    "GDELT serves the archive manifests and files used here over unauthenticated "
    "HTTP. Published MD5 values and recorded SHA-256 manifest hashes detect "
    "inconsistency and support reproducibility, but do not authenticate GDELT as "
    "the source."
)

V1_NAME = re.compile(r"^(?P<day>\d{8})\.gkg\.csv\.zip$")
V2_NAME = re.compile(r"^(?P<stamp>\d{14})\.gkg\.csv\.zip$")
MD5_RE = re.compile(r"^[0-9a-f]{32}$")
T = TypeVar("T")


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_URL_OPENER = build_opener(_RejectRedirects)


@dataclass(frozen=True)
class ArchiveFile:
    timestamp: str
    name: str
    url: str
    size_bytes: int
    md5_hex: str


def _store_unique(mapping: dict[str, T], key: str, value: T, label: str) -> None:
    existing = mapping.get(key)
    if existing is not None and existing != value:
        raise ValueError(f"conflicting {label} entries for {key}")
    mapping[key] = value


def _validate_stream(stream: str) -> None:
    if stream not in STREAMS:
        raise ValueError(f"unsupported GDELT stream: {stream}")


def _official_url_for_item(item: ArchiveFile) -> str:
    v1_match = V1_NAME.fullmatch(item.name)
    v2_match = V2_NAME.fullmatch(item.name)
    if v1_match:
        expected_timestamp = v1_match.group("day")
        expected_url = f"{V1_BASE_URL}/{item.name}"
    elif v2_match:
        expected_timestamp = v2_match.group("stamp")
        expected_url = f"{V2_BASE_URL}/{item.name}"
    else:
        raise ValueError(f"unsupported GDELT archive filename: {item.name}")
    if item.timestamp != expected_timestamp:
        raise ValueError(f"timestamp does not match archive filename: {item.name}")
    if item.url != expected_url:
        raise ValueError(f"archive URL is not the pinned official URL for {item.name}")
    if item.size_bytes <= 0:
        raise ValueError(f"official size must be positive for {item.name}")
    if not MD5_RE.fullmatch(item.md5_hex.lower()):
        raise ValueError(f"invalid official MD5 for {item.name}")
    return expected_url


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def _days(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _md5_file(path: Path) -> str:
    # MD5 is used only to verify bytes against GDELT's published archive
    # manifests, not for a security-sensitive purpose.
    digest = md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch(url: str, path: Path, refresh: bool) -> Path:
    if path.is_file() and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with _URL_OPENER.open(request, timeout=120) as response, temporary.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    temporary.replace(path)
    return path


def _v1_inventory(cache_dir: Path, refresh: bool) -> tuple[dict[str, ArchiveFile], dict[str, str]]:
    md5_path = _fetch(V1_MD5_URL, cache_dir / "gkg-v1-md5sums.txt", refresh)
    size_path = _fetch(V1_SIZE_URL, cache_dir / "gkg-v1-filesizes.txt", refresh)

    checksums: dict[str, str] = {}
    for line in md5_path.read_text(encoding="ascii", errors="strict").splitlines():
        parts = line.split()
        if len(parts) == 2 and V1_NAME.fullmatch(parts[1]) and MD5_RE.fullmatch(parts[0].lower()):
            _store_unique(checksums, parts[1], parts[0].lower(), "GDELT v1 MD5")

    sizes: dict[str, int] = {}
    for line in size_path.read_text(encoding="ascii", errors="strict").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and V1_NAME.fullmatch(parts[1]):
            size = int(parts[0])
            if size > 0:
                _store_unique(sizes, parts[1], size, "GDELT v1 size")

    inventory: dict[str, ArchiveFile] = {}
    for name in sorted(set(checksums) & set(sizes)):
        match = V1_NAME.fullmatch(name)
        assert match is not None
        stamp = match.group("day")
        inventory[stamp] = ArchiveFile(
            timestamp=stamp,
            name=name,
            url=f"{V1_BASE_URL}/{name}",
            size_bytes=sizes[name],
            md5_hex=checksums[name],
        )
    return inventory, {
        V1_MD5_URL: _sha256_file(md5_path),
        V1_SIZE_URL: _sha256_file(size_path),
    }


def _v2_inventory(cache_dir: Path, refresh: bool) -> tuple[dict[str, ArchiveFile], dict[str, str]]:
    master_path = _fetch(V2_MASTER_URL, cache_dir / "gkg-v2-masterfilelist.txt", refresh)
    inventory: dict[str, ArchiveFile] = {}
    with master_path.open("r", encoding="ascii", errors="strict") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) != 3 or not parts[0].isdigit() or not MD5_RE.fullmatch(parts[1].lower()):
                continue
            name = parts[2].rsplit("/", 1)[-1]
            match = V2_NAME.fullmatch(name)
            if not match:
                continue
            size = int(parts[0])
            official_url = f"{V2_BASE_URL}/{name}"
            if size <= 0 or parts[2] != official_url:
                continue
            stamp = match.group("stamp")
            item = ArchiveFile(
                timestamp=stamp,
                name=name,
                url=official_url,
                size_bytes=size,
                md5_hex=parts[1].lower(),
            )
            _store_unique(inventory, stamp, item, "GDELT v2 archive")
    return inventory, {V2_MASTER_URL: _sha256_file(master_path)}


def _load_inventory(
    stream: str, cache_dir: Path, refresh: bool
) -> tuple[dict[str, ArchiveFile], dict[str, str]]:
    if stream == "v1":
        return _v1_inventory(cache_dir, refresh)
    if stream == "v2":
        return _v2_inventory(cache_dir, refresh)
    raise ValueError(f"unsupported GDELT stream: {stream}")


def _expected_timestamps(stream: str, start: date, end: date) -> list[str]:
    _validate_stream(stream)
    if stream == "v1":
        return [day.strftime("%Y%m%d") for day in _days(start, end)]
    expected: list[str] = []
    for day in _days(start, end):
        at = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        for offset in range(96):
            expected.append((at + timedelta(minutes=15 * offset)).strftime("%Y%m%d%H%M%S"))
    return expected


def audit_inventory(
    stream: str,
    start: date,
    end: date,
    cache_dir: Path,
    refresh: bool = False,
) -> tuple[dict[str, object], dict[str, ArchiveFile]]:
    _validate_stream(stream)
    if start > end:
        raise ValueError("start date is after end date")
    inventory, source_hashes = _load_inventory(stream, cache_dir, refresh)
    expected = _expected_timestamps(stream, start, end)
    missing = [stamp for stamp in expected if stamp not in inventory]

    day_counts: dict[str, int] = {}
    for stamp in inventory:
        day = stamp[:8]
        if start.strftime("%Y%m%d") <= day <= end.strftime("%Y%m%d"):
            day_counts[day] = day_counts.get(day, 0) + 1
    expected_per_day = 1 if stream == "v1" else 96
    incomplete_days = [
        {
            "date": day.strftime("%Y-%m-%d"),
            "available_files": day_counts.get(day.strftime("%Y%m%d"), 0),
        }
        for day in _days(start, end)
        if day_counts.get(day.strftime("%Y%m%d"), 0) != expected_per_day
    ]

    result: dict[str, object] = {
        "stream": stream,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "expected_files": len(expected),
        "available_files": len(expected) - len(missing),
        "missing_file_count": len(missing),
        "missing_timestamps": missing,
        "incomplete_days": incomplete_days,
        "file_inventory_complete": not missing,
        "metadata_gate_warning": (
            "File inventory completeness is necessary but not sufficient to set "
            "metadata.gdelt_archive_days_complete=true."
        ),
        "transport_warning": TRANSPORT_WARNING,
        "source_manifest_sha256": source_hashes,
    }
    selected = {stamp: inventory[stamp] for stamp in expected if stamp in inventory}
    return result, selected


def _download_file(item: ArchiveFile, output_dir: Path) -> Path:
    official_url = _official_url_for_item(item)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / item.name
    if destination.is_file():
        if destination.stat().st_size == item.size_bytes and _md5_file(destination) == item.md5_hex:
            return destination
        raise ValueError(f"existing file fails official size/MD5 check: {destination}")

    temporary = destination.with_name(destination.name + ".part")
    request = Request(official_url, headers={"User-Agent": USER_AGENT})
    with _URL_OPENER.open(request, timeout=180) as response, temporary.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    if temporary.stat().st_size != item.size_bytes:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"downloaded size differs from official manifest for {item.name}")
    if _md5_file(temporary) != item.md5_hex:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"downloaded MD5 differs from official manifest for {item.name}")
    temporary.replace(destination)
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit or fetch official GDELT GKG files for the locked H33 protocol."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "download"):
        child = subparsers.add_parser(command)
        child.add_argument("--stream", choices=STREAMS, required=True)
        child.add_argument("--start", type=_parse_day, required=True)
        child.add_argument("--end", type=_parse_day, required=True)
        child.add_argument(
            "--cache-dir",
            type=Path,
            default=Path.home() / ".cache" / "wewillsee-h33" / "gdelt",
        )
        child.add_argument("--refresh", action="store_true")
        child.add_argument("--output", type=Path)
    download = subparsers.choices["download"]
    download.add_argument("--output-dir", type=Path, required=True)
    download.add_argument(
        "--execute",
        action="store_true",
        help="Without this flag, print the verified download plan without fetching raw files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result, selected = audit_inventory(
            args.stream, args.start, args.end, args.cache_dir, args.refresh
        )
        if args.command == "download":
            if not result["file_inventory_complete"]:
                result["download_decision"] = "REFUSED_INCOMPLETE_OFFICIAL_INVENTORY"
            else:
                plan = [asdict(selected[key]) for key in sorted(selected)]
                result["planned_download_bytes"] = sum(item["size_bytes"] for item in plan)
                result["planned_files"] = plan
                if args.execute:
                    downloaded = [
                        str(_download_file(selected[key], args.output_dir))
                        for key in sorted(selected)
                    ]
                    result["download_decision"] = "DOWNLOADED_AND_MD5_VERIFIED"
                    result["downloaded_files"] = downloaded
                else:
                    result["download_decision"] = "DRY_RUN_ADD_EXECUTE_TO_FETCH"
        rendered = json.dumps(result, indent=2, sort_keys=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        if not result["file_inventory_complete"]:
            return 2
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"decision": "ERROR", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
