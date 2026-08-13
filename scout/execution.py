"""Shared, explicit execution assumptions for every backtest path.

Signals are formed with a day's completed close.  The default fill is therefore
the following trading day's open; ``signal_close`` exists only as an audit
comparison and is deliberately named so a result cannot hide same-bar fills.

Quoted spread is treated as a full bid/ask spread, so half is paid on each side.
Slippage and commission are per side.  Daily equity is marked at the close as if
the position were liquidated there, including the estimated exit cost.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from . import config


ENTRY_TIMINGS = ("next_open", "signal_close")
MISSING_POLICIES = ("total_loss", "last_print")


@dataclass(frozen=True)
class ExecutionAssumptions:
    """Execution and missing-data rules used by a simulation."""

    entry_timing: str = "next_open"
    spread_bps: float = config.BACKTEST_SPREAD_BPS
    slippage_bps: float = config.BACKTEST_SLIPPAGE_BPS
    commission_bps: float = config.BACKTEST_COMMISSION_BPS
    missing_leg_policy: str = config.BACKTEST_MISSING_LEG_POLICY

    def __post_init__(self) -> None:
        if self.entry_timing not in ENTRY_TIMINGS:
            raise ValueError(f"entry_timing must be one of {ENTRY_TIMINGS}")
        if self.missing_leg_policy not in MISSING_POLICIES:
            raise ValueError(f"missing_leg_policy must be one of {MISSING_POLICIES}")
        for name in ("spread_bps", "slippage_bps", "commission_bps"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")

    @property
    def side_cost_rate(self) -> float:
        """Cost paid on one side of a trade as a decimal fraction."""
        return (self.spread_bps / 2 + self.slippage_bps + self.commission_bps) / 10_000

    @property
    def estimated_round_trip_bps(self) -> float:
        return 2 * self.side_cost_rate * 10_000

    def metadata(self) -> dict:
        out = asdict(self)
        out["spread_interpretation"] = "full quoted spread; half charged per side"
        out["estimated_round_trip_bps"] = round(self.estimated_round_trip_bps, 4)
        return out


DEFAULT_EXECUTION = ExecutionAssumptions()


def add_execution_args(parser) -> None:
    parser.add_argument(
        "--entry-timing", choices=ENTRY_TIMINGS, default=DEFAULT_EXECUTION.entry_timing,
        help="next_open is honest default; signal_close is audit-only same-bar execution",
    )
    parser.add_argument("--spread-bps", type=float, default=DEFAULT_EXECUTION.spread_bps,
                        help="full quoted bid/ask spread in basis points")
    parser.add_argument("--slippage-bps", type=float, default=DEFAULT_EXECUTION.slippage_bps,
                        help="market impact/slippage per side in basis points")
    parser.add_argument("--commission-bps", type=float,
                        default=DEFAULT_EXECUTION.commission_bps,
                        help="commission per side in basis points")
    parser.add_argument("--missing-leg-policy", choices=MISSING_POLICIES,
                        default=DEFAULT_EXECUTION.missing_leg_policy,
                        help="total_loss is conservative; last_print is a sensitivity case")


def from_args(args) -> ExecutionAssumptions:
    return ExecutionAssumptions(
        entry_timing=args.entry_timing,
        spread_bps=args.spread_bps,
        slippage_bps=args.slippage_bps,
        commission_bps=args.commission_bps,
        missing_leg_policy=args.missing_leg_policy,
    )


def _safe_value(frame: pd.DataFrame, pos: int, sym: str) -> float | None:
    if sym not in frame.columns or pos < 0 or pos >= len(frame):
        return None
    value = frame.iloc[pos].get(sym)
    return None if pd.isna(value) else float(value)


def simulate_leg(
    open_prices: pd.DataFrame,
    close_prices: pd.DataFrame,
    signal_pos: int,
    sym: str,
    horizon: int,
    assumptions: ExecutionAssumptions = DEFAULT_EXECUTION,
) -> dict:
    """Simulate one selected slot and always return a full-weight outcome.

    A missing entry is an unfilled order and remains cash (0% return), but is
    reported. Once filled, a disappearance with observable post-horizon rows
    and no later quote is a total loss by default. A quote that resumes after
    the horizon, or a gap at the dataset boundary that cannot be classified,
    is carried at the last mark and explicitly reported. ``last_print`` is
    available for acquisition-style sensitivity analysis. Interior NaN gaps
    are carried at the last mark when a later quote exists.
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if signal_pos + horizon >= len(close_prices):
        raise ValueError("not enough future rows for the requested horizon")

    if assumptions.entry_timing == "next_open":
        entry_pos = signal_pos + 1
        raw_entry = _safe_value(open_prices, entry_pos, sym)
    else:
        entry_pos = signal_pos
        raw_entry = _safe_value(close_prices, signal_pos, sym)

    dates = close_prices.index[signal_pos + 1: signal_pos + 1 + horizon]
    cash_path = np.ones(horizon + 1, dtype=float)
    if raw_entry is None or raw_entry <= 0:
        return {
            "symbol": sym, "status": "missing_entry", "filled": False,
            "entry_timing": assumptions.entry_timing, "entry_date": None,
            "entry_price_raw": None, "entry_price_fill": None,
            "exit_price_raw": None, "observed_bars": 0,
            "missing_terminal_bars": horizon, "first_missing_date": str(dates[0].date()),
            "terminal_classification": "entry_never_filled",
            "hit": False, "end": 0.0, "max": 0.0, "hit10": False,
            "hit15": False, "days": None, "dip_first": False,
            "path": cash_path.tolist(),
        }

    side = assumptions.side_cost_rate
    fill = raw_entry * (1 + side)
    if sym in close_prices.columns:
        raw = close_prices[sym].iloc[signal_pos + 1: signal_pos + 1 + horizon].astype(float)
    else:
        raw = pd.Series(np.nan, index=dates, dtype=float)
    observed = int(raw.notna().sum())
    valid_positions = np.flatnonzero(raw.notna().to_numpy())
    last_valid = int(valid_positions[-1]) if len(valid_positions) else -1
    terminal_missing = horizon - (last_valid + 1)

    # A close may be absent on an isolated halt/data-gap day and return later.
    # Carry the prior mark across interior gaps; only the terminal disappearance
    # invokes the declared missing-leg policy.
    marked = raw.ffill().fillna(raw_entry).to_numpy(dtype=float)
    net = marked * (1 - side) / fill
    status = "complete"
    first_missing_date = None
    terminal_classification = None
    if terminal_missing:
        first_missing_date = str(dates[last_valid + 1].date())
        # A NaN exactly at the measurement boundary is not proof that the
        # company disappeared.  Looking *after* the return window is allowed
        # only to classify data quality; those later prices are never used in
        # the measured return.  If trading resumes, carry the last observable
        # mark.  If the whole dataset ends here, the outcome is unresolved and
        # is also carried at the last print instead of inventing a delisting.
        after_horizon = (
            close_prices[sym].iloc[signal_pos + horizon + 1:]
            if sym in close_prices.columns else pd.Series(dtype=float)
        )
        after_horizon_open = (
            open_prices[sym].iloc[signal_pos + horizon + 1:]
            if sym in open_prices.columns else pd.Series(dtype=float)
        )
        resumes_after_horizon = bool(
            after_horizon.notna().any() or after_horizon_open.notna().any()
        )
        dataset_boundary = signal_pos + horizon >= len(close_prices) - 1
        if resumes_after_horizon:
            status = "boundary_gap_last_print"
            terminal_classification = "temporary_gap_confirmed_after_horizon"
        elif dataset_boundary:
            status = "unresolved_dataset_boundary_last_print"
            terminal_classification = "no_post_horizon_rows_to_classify"
        elif assumptions.missing_leg_policy == "total_loss":
            net[last_valid + 1:] = 0.0
            status = "partial_total_loss"
            terminal_classification = "terminal_no_later_quote"
        else:
            status = "partial_last_print"
            terminal_classification = "terminal_no_later_quote"

    path = np.concatenate(([1.0], net))
    future = path[1:]
    up = future >= 1.0 + config.TARGET_GAIN
    dn = future <= 1.0 + config.DROP_GAIN
    hit = bool(up.any())
    first_up = int(np.argmax(up)) if hit else horizon + 1
    first_dn = int(np.argmax(dn)) if dn.any() else horizon + 1
    exit_raw = float(raw.dropna().iloc[-1]) if observed else None
    return {
        "symbol": sym, "status": status, "filled": True,
        "entry_timing": assumptions.entry_timing,
        "entry_date": str(close_prices.index[entry_pos].date()),
        "entry_price_raw": raw_entry, "entry_price_fill": fill,
        "exit_price_raw": exit_raw, "observed_bars": observed,
        "missing_terminal_bars": terminal_missing,
        "first_missing_date": first_missing_date,
        "terminal_classification": terminal_classification,
        "hit": hit, "end": float(future[-1] - 1),
        "max": float(np.max(future) - 1),
        "hit10": bool((future >= 1.10).any()),
        "hit15": bool((future >= 1.15).any()),
        "days": first_up + 1 if hit else None,
        "dip_first": bool(dn.any() and first_dn < first_up),
        "path": path.tolist(),
    }


def simulate_window(
    open_prices: pd.DataFrame,
    close_prices: pd.DataFrame,
    signal_pos: int,
    symbols: Iterable[str],
    horizon: int,
    assumptions: ExecutionAssumptions = DEFAULT_EXECUTION,
) -> dict:
    """Equal-weight selected slots, including unfilled/missing slots."""
    symbols = list(symbols)
    outcomes = {
        sym: simulate_leg(open_prices, close_prices, signal_pos, sym, horizon, assumptions)
        for sym in symbols
    }
    if outcomes:
        equity = np.mean([o["path"] for o in outcomes.values()], axis=0)
    else:
        equity = np.ones(horizon + 1, dtype=float)
    missing_entries = [s for s, o in outcomes.items() if o["status"] == "missing_entry"]
    partial = [s for s, o in outcomes.items() if o["status"].startswith("partial_")]
    data_quality = [
        s for s, o in outcomes.items()
        if o["status"] in {
            "boundary_gap_last_print",
            "unresolved_dataset_boundary_last_print",
        }
    ]
    return {
        "outcomes": outcomes,
        "equity": equity.tolist(),
        "selected": len(symbols),
        "filled": sum(bool(o["filled"]) for o in outcomes.values()),
        "missing_entries": missing_entries,
        "partial_legs": partial,
        "data_quality_legs": data_quality,
    }


def max_drawdown(equity: Iterable[float]) -> float:
    values = np.asarray(list(equity), dtype=float)
    if not len(values):
        return 0.0
    peaks = np.maximum.accumulate(values)
    return float(np.min(values / peaks - 1))


def stitch_curves(curves: Iterable[Iterable[float]]) -> list[float]:
    """Compound window-relative daily curves into one daily equity path."""
    out = [1.0]
    capital = 1.0
    for curve in curves:
        values = np.asarray(list(curve), dtype=float)
        if not len(values):
            continue
        base = values[0]
        if base <= 0:
            raise ValueError("curve must start above zero")
        rel = values / base
        out.extend((capital * rel[1:]).tolist())
        capital *= float(rel[-1])
    return out
