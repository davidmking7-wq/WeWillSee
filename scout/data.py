"""Daily OHLCV via Alpaca. Uses the SIP (consolidated all-exchange) feed with
split/dividend adjustment — the free plan allows SIP *history* (only the last
~15 minutes are restricted), and consolidated volume is what makes the
volume-surge signal meaningful (IEX carries ~2.5% of tape).

Returns open/close/volume frames (time x symbol) plus machine-readable
``metadata`` describing requested, returned, and missing-symbol coverage.
"""
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from . import config

CHUNK = 150  # symbols per request (practical cap ~200)
MAX_ATTEMPTS = 3
COVERAGE_SCHEMA_VERSION = 1


class MarketDataFetchError(RuntimeError):
    """A fail-closed market-data error with machine-readable coverage facts."""

    def __init__(self, message: str, metadata: dict):
        super().__init__(message)
        self.metadata = metadata


def _base_metadata(
    symbols: list[str], start: datetime, end: datetime,
    max_missing_fraction: float,
) -> dict:
    return {
        "coverage_schema_version": COVERAGE_SCHEMA_VERSION,
        "status": "incomplete",
        "provider": "alpaca",
        "feed": "sip",
        "adjustment": "all",
        "timeframe": "day",
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "requested_symbols": symbols,
        "requested_symbol_count": len(symbols),
        "returned_symbols": [],
        "returned_symbol_count": 0,
        "missing_symbols": list(symbols),
        "missing_symbol_count": len(symbols),
        "missing_symbol_fraction": 1.0 if symbols else 0.0,
        "declared_threshold": {
            "name": "BACKTEST_MAX_MISSING_SYMBOL_FRACTION",
            "max_missing_symbol_fraction": max_missing_fraction,
        },
        "threshold_passed": False,
        "observed_start": None,
        "observed_end": None,
        "chunks": [],
    }


def _update_coverage(metadata: dict, allbars: pd.DataFrame | None) -> None:
    requested = metadata["requested_symbols"]
    if allbars is None or allbars.empty:
        returned = []
        observed_start = observed_end = None
    else:
        returned_set = set(allbars["symbol"].astype(str))
        returned = [symbol for symbol in requested if symbol in returned_set]
        timestamps = pd.to_datetime(allbars["timestamp"], utc=True)
        observed_start = timestamps.min().isoformat()
        observed_end = timestamps.max().isoformat()
    missing = [symbol for symbol in requested if symbol not in set(returned)]
    count = len(requested)
    fraction = len(missing) / count if count else 0.0
    maximum = metadata["declared_threshold"]["max_missing_symbol_fraction"]
    metadata.update({
        "returned_symbols": returned,
        "returned_symbol_count": len(returned),
        "missing_symbols": missing,
        "missing_symbol_count": len(missing),
        "missing_symbol_fraction": fraction,
        "threshold_passed": fraction <= maximum,
        "observed_start": observed_start,
        "observed_end": observed_end,
    })


def _safe_error_message(exc: Exception) -> str:
    """Keep retry diagnostics without persisting configured credentials."""
    message = str(exc)
    for secret in (config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message[:500]


def daily_ohlcv(
    symbols: list[str], days: int, *, max_attempts: int = MAX_ATTEMPTS,
    retry_backoff_seconds: float = 1.0,
    max_missing_fraction: float | None = None,
) -> dict[str, pd.DataFrame | dict]:
    """Fetch adjusted daily bars, retry every chunk, and fail closed.

    Confirmatory research defaults to the repository's declared zero/tiny
    missing-symbol threshold.  A successful return includes ``metadata`` so a
    cache or result can prove exactly what was requested and received.
    """
    if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
        raise RuntimeError(
            "Alpaca credentials are required only for a network data fetch; "
            "offline audit and tests do not need them"
        )
    if days <= 0:
        raise ValueError("days must be positive")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    if retry_backoff_seconds < 0:
        raise ValueError("retry_backoff_seconds cannot be negative")
    if max_missing_fraction is None:
        max_missing_fraction = config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION
    if not 0 <= max_missing_fraction <= 1:
        raise ValueError("max_missing_fraction must be between zero and one")

    # De-duplicate without changing request order.  Coverage counts are then
    # unambiguous and stable across runs.
    symbols = list(dict.fromkeys(str(symbol) for symbol in symbols))
    if not symbols:
        raise ValueError("at least one symbol is required")

    client = StockHistoricalDataClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    end = now - timedelta(minutes=20)   # SIP data older than 15 min is free
    metadata = _base_metadata(symbols, start, end, max_missing_fraction)
    frames = []
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        chunk_record = {
            "chunk_number": i // CHUNK + 1,
            "requested_symbols": chunk,
            "attempts": 0,
            "errors": [],
            "completed": False,
        }
        metadata["chunks"].append(chunk_record)
        for attempt in range(1, max_attempts + 1):
            chunk_record["attempts"] = attempt
            try:
                req = StockBarsRequest(
                    symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                    start=start, end=end, adjustment=Adjustment.ALL,
                    feed=DataFeed.SIP,
                )
                df = client.get_stock_bars(req).df
                if not df.empty:
                    frames.append(df.reset_index())
                chunk_record["completed"] = True
                chunk_record["returned_row_count"] = int(len(df))
                break
            except Exception as exc:  # provider/client failures must not be skipped
                chunk_record["errors"].append({
                    "attempt": attempt,
                    "type": type(exc).__name__,
                    "message": _safe_error_message(exc),
                })
                if attempt < max_attempts and retry_backoff_seconds:
                    time.sleep(retry_backoff_seconds * (2 ** (attempt - 1)))
        if not chunk_record["completed"]:
            partial = pd.concat(frames, ignore_index=True) if frames else None
            _update_coverage(metadata, partial)
            metadata["status"] = "failed_closed_chunk_error"
            raise MarketDataFetchError(
                f"market-data chunk {chunk_record['chunk_number']} failed after "
                f"{max_attempts} attempts; no partial dataset was returned",
                metadata,
            )
    if not frames:
        _update_coverage(metadata, None)
        metadata["status"] = "failed_closed_no_data"
        raise MarketDataFetchError("no market data returned at all", metadata)
    allbars = pd.concat(frames, ignore_index=True)
    _update_coverage(metadata, allbars)
    if not metadata["threshold_passed"]:
        metadata["status"] = "failed_closed_missing_symbol_threshold"
        raise MarketDataFetchError(
            f"market data omitted {metadata['missing_symbol_count']} of "
            f"{metadata['requested_symbol_count']} requested symbols "
            f"({metadata['missing_symbol_fraction']:.4%}), above the declared "
            f"{max_missing_fraction:.4%} threshold",
            metadata,
        )
    allbars["timestamp"] = (pd.to_datetime(allbars["timestamp"])
                            .dt.tz_convert("US/Eastern").dt.normalize())
    out = {}
    for field in ("open", "close", "volume"):
        out[field] = (allbars.pivot_table(index="timestamp", columns="symbol",
                                          values=field, aggfunc="last")
                      .sort_index())
    metadata["status"] = "complete"
    out["metadata"] = metadata
    return out
