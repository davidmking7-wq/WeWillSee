"""Backtest lie detector: one command that tries to disprove the headline.

This command is offline by design.  It reads committed result artifacts and,
when a local bar cache is available, reruns adversarial controls.  It never
fetches market data and never needs Alpaca credentials.

Examples:
    python -m scout.audit --universe sp1500
    python -m scout.audit --cache scout/backtest_cache_1500.pkl --draws 200
    python -m scout.audit --json-out scout/audit_results.json
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest, config, execution, pit, signals


@dataclass
class Check:
    name: str
    status: str
    summary: str
    details: dict


def _check(name: str, status: str, summary: str, **details) -> Check:
    return Check(name, status, summary, details)


def load_cached_bars(mode: str, explicit: str | None = None) -> tuple[dict | None, Path]:
    path = Path(explicit) if explicit else {
        "sp500": backtest.CACHE,
        "pit500": backtest.CACHE_PIT,
        "sp1500": backtest.CACHE_1500,
    }[mode]
    if not path.is_absolute():
        path = config.ROOT / path
    if not path.exists():
        return None, path
    with open(path, "rb") as fh:
        bars = pickle.load(fh)
    for field in ("open", "close", "volume"):
        if field not in bars or not isinstance(bars[field], pd.DataFrame):
            raise ValueError(f"{path} is missing a {field!r} DataFrame")
    return bars, path


def cache_data_coverage(bars: dict, path: Path, mode: str) -> Check:
    """Make legacy/incomplete cache status visible instead of assuming clean data."""
    coverage = backtest._data_coverage(bars, mode)
    fetch = coverage.get("fetch") or {}
    required = {
        "coverage_schema_version", "status", "requested_symbols",
        "requested_symbol_count", "returned_symbols", "returned_symbol_count",
        "missing_symbols", "missing_symbol_count", "missing_symbol_fraction",
        "declared_threshold", "threshold_passed", "universe_mode",
        "chunks",
    }
    absent = sorted(required - set(fetch))
    threshold = fetch.get("declared_threshold") or {}
    configured = config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION
    problems = []
    if absent:
        problems.append("missing metadata: " + ", ".join(absent))
    if fetch.get("status") != "complete":
        problems.append(f"status={fetch.get('status')!r}")
    if fetch.get("threshold_passed") is not True:
        problems.append("coverage threshold did not pass")
    if threshold.get("name") != "BACKTEST_MAX_MISSING_SYMBOL_FRACTION":
        problems.append("missing-threshold label is absent or different")
    if threshold.get("max_missing_symbol_fraction") != configured:
        problems.append("declared missing threshold differs from config")
    if fetch.get("universe_mode") != mode:
        problems.append("cache universe mode differs from requested audit mode")
    declared_fraction = fetch.get("missing_symbol_fraction")
    if not isinstance(declared_fraction, (int, float)):
        problems.append("missing-symbol fraction is absent or not numeric")
    elif float(declared_fraction) > configured:
        problems.append("missing-symbol fraction exceeds the configured threshold")
    requested = fetch.get("requested_symbols", [])
    returned = fetch.get("returned_symbols", [])
    missing = fetch.get("missing_symbols", [])
    if fetch.get("requested_symbol_count") != len(requested):
        problems.append("requested symbol count is inconsistent")
    if fetch.get("returned_symbol_count") != len(returned):
        problems.append("returned symbol count is inconsistent")
    if fetch.get("missing_symbol_count") != len(missing):
        problems.append("missing symbol count is inconsistent")
    if set(requested) != set(returned) | set(missing):
        problems.append("returned and missing symbols do not partition the request")
    chunks = fetch.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        problems.append("chunk-attempt metadata is absent")
    elif any(not isinstance(chunk, dict) or chunk.get("completed") is not True
             for chunk in chunks):
        problems.append("one or more chunks did not complete")
    observed_close_symbols = set(
        bars["close"].columns[bars["close"].notna().any(axis=0)]
    )
    if set(returned) != observed_close_symbols:
        problems.append("declared returned symbols differ from observed close columns")
    status = "PASS" if not problems else "FAIL"
    return _check(
        "cache_data_coverage", status,
        "cache has complete declared coverage" if not problems else
        f"cache is legacy/incomplete ({len(problems)} problems)",
        path=str(path), coverage=coverage, problems=problems,
    )


def phase_sensitivity(
    bars: dict, mode: str, n_picks: int, phase_step: int,
    assumptions: execution.ExecutionAssumptions, start=None, end=None,
) -> Check:
    h = config.HORIZON_TDAYS
    if phase_step <= 0 or h % phase_step:
        return _check("start_phase", "FAIL", "phase step must divide the horizon",
                      horizon=h, phase_step=phase_step)
    idx = bars["close"].index
    all_positions = backtest.positions_for(idx, start, end, phase_step)
    if not all_positions:
        return _check("start_phase", "SKIP", "no eligible dates")
    name = config.ENGINE if config.ENGINE in backtest.ENGINES else "v5"
    ff, comp = backtest.ENGINES[name]
    windows = backtest.run_engine(
        name, ff, comp, bars, all_positions, n_picks,
        pit_mode=mode == "pit500", assumptions=assumptions,
    )
    phases = h // phase_step
    anchor = all_positions[0]
    rows = []
    for phase in range(phases):
        ws = [w for w in windows
              if ((w["pos"] - anchor) // phase_step) % phases == phase]
        if not ws:
            continue
        avg = 100 * float(np.mean([w["avg_end"] for w in ws]))
        comp_row = backtest.compound(ws)
        rows.append({
            "phase": phase, "offset_tdays": phase * phase_step,
            "windows": len(ws), "avg_window_pct": round(avg, 3),
            "compounded_pct": comp_row["strategy_growth_pct"],
            "daily_max_drawdown_pct": comp_row["strategy_daily_max_drawdown_pct"],
        })
    values = [r["avg_window_pct"] for r in rows]
    spread = max(values) - min(values) if values else math.nan
    status = "PASS" if spread <= 2.0 else "WARN"
    return _check(
        "start_phase", status,
        f"{spread:.2f} percentage-point spread across {len(rows)} start schedules",
        phase_step=phase_step, phases=rows, spread_pct_points=round(spread, 3),
    )


def random_pick_lift(
    bars: dict, mode: str, n_picks: int, step: int, draws: int,
    assumptions: execution.ExecutionAssumptions, start=None, end=None,
    seed: int = 42,
) -> Check:
    """Compare ranked picks with random names from the exact eligible pool."""
    if draws <= 0:
        return _check("random_pick_lift", "FAIL", "draws must be positive",
                      draws=draws)
    o, c = bars["open"], bars["close"]
    idx = c.index
    positions = backtest.positions_for(idx, start, end, step)
    frames = signals.feature_frames(o, c, bars["volume"])
    rng = np.random.default_rng(seed)
    random_end = np.zeros(draws, dtype=float)
    random_hit = np.zeros(draws, dtype=float)
    actual_ends, actual_hits = [], []
    used = 0
    for pos in positions:
        ts = idx[pos]
        if mode == "pit500":
            members = pit.members(ts)
            cols = [s for s in c.columns if s in members or s == backtest.REGIME_SYM]
            day = {k: f.loc[[ts], cols] for k, f in frames.items()}
            snap = signals.composite_at(day, ts)
        else:
            snap = signals.composite_at(frames, ts)
        snap = snap.drop(index=[backtest.REGIME_SYM], errors="ignore")
        if len(snap) < max(50, n_picks):
            continue
        syms = list(snap.index)
        sim = execution.simulate_window(o, c, pos, syms, config.HORIZON_TDAYS,
                                        assumptions)
        ends = np.array([sim["outcomes"][s]["end"] for s in syms])
        hits = np.array([sim["outcomes"][s]["hit"] for s in syms], dtype=float)
        actual_ends.append(float(np.mean(ends[:n_picks])))
        actual_hits.extend(hits[:n_picks].tolist())
        for draw in range(draws):
            chosen = rng.choice(len(syms), size=n_picks, replace=False)
            random_end[draw] += float(np.mean(ends[chosen]))
            random_hit[draw] += float(np.mean(hits[chosen]))
        used += 1
    if not used:
        return _check("random_pick_lift", "SKIP", "no eligible dates")
    random_end /= used
    random_hit /= used
    actual_end = float(np.mean(actual_ends))
    actual_hit = float(np.mean(actual_hits))
    p_end = float(np.mean(random_end < actual_end))
    p_hit = float(np.mean(random_hit < actual_hit))
    status = "PASS" if min(p_end, p_hit) >= 0.95 else "FAIL"
    return _check(
        "random_pick_lift", status,
        f"ranked return beat {p_end:.1%} of random controls; hit rate beat {p_hit:.1%}",
        dates=used, draws=draws, actual_avg_end_pct=round(100 * actual_end, 3),
        random_avg_end_pct=round(100 * float(np.mean(random_end)), 3),
        actual_hit_pct=round(100 * actual_hit, 2),
        random_hit_pct=round(100 * float(np.mean(random_hit)), 2),
        return_percentile=round(p_end, 4), hit_percentile=round(p_hit, 4),
    )


def cost_sensitivity(
    bars: dict, mode: str, n_picks: int, step: int,
    assumptions: execution.ExecutionAssumptions, start=None, end=None,
) -> Check:
    idx = bars["close"].index
    positions = backtest.positions_for(idx, start, end, step)
    name = config.ENGINE if config.ENGINE in backtest.ENGINES else "v5"
    ff, comp = backtest.ENGINES[name]
    zero = execution.ExecutionAssumptions(
        entry_timing=assumptions.entry_timing, spread_bps=0, slippage_bps=0,
        commission_bps=0, missing_leg_policy=assumptions.missing_leg_policy,
    )
    gross = backtest.run_engine(name, ff, comp, bars, positions, n_picks,
                                pit_mode=mode == "pit500", assumptions=zero)
    net = backtest.run_engine(name, ff, comp, bars, positions, n_picks,
                              pit_mode=mode == "pit500", assumptions=assumptions)
    stride = max(1, math.ceil(config.HORIZON_TDAYS / step))
    gross_c = backtest.compound(gross[::stride])
    net_c = backtest.compound(net[::stride])
    if gross_c is None or net_c is None:
        return _check("costs", "SKIP", "no eligible windows")
    drag = gross_c["strategy_growth_pct"] - net_c["strategy_growth_pct"]
    benchmark = net_c.get("spy_buy_and_hold_growth_pct")
    net_excess = (net_c["strategy_growth_pct"] - benchmark
                  if benchmark is not None else None)
    tolerance = 1e-8
    problems = []
    if drag < -tolerance:
        problems.append("declared costs appear to improve the result")
    if benchmark is None:
        problems.append("continuous SPY buy-and-hold benchmark is unavailable")
    elif net_excess <= tolerance:
        problems.append("net strategy did not beat continuous SPY buy-and-hold")
    status = "PASS" if not problems else "FAIL"
    return _check(
        "costs", status,
        (f"net excess over continuous SPY is {net_excess:+.3f} points; "
         f"cost drag is {drag:+.3f} points") if net_excess is not None else
        f"continuous SPY unavailable; cost drag is {drag:+.3f} points",
        assumptions=assumptions.metadata(), gross=gross_c, net=net_c,
        drag_pct_points=round(drag, 6),
        net_excess_over_spy_buy_hold_pct_points=(
            round(net_excess, 6) if net_excess is not None else None
        ),
        problems=problems,
    )


def missing_leg_audit(
    bars: dict, mode: str, n_picks: int, step: int,
    assumptions: execution.ExecutionAssumptions, start=None, end=None,
) -> Check:
    idx = bars["close"].index
    positions = backtest.positions_for(idx, start, end, step)
    name = config.ENGINE if config.ENGINE in backtest.ENGINES else "v5"
    ff, comp = backtest.ENGINES[name]
    windows = backtest.run_engine(
        name, ff, comp, bars, positions, n_picks,
        pit_mode=mode == "pit500", assumptions=assumptions,
    )
    selected = sum(len(w["symbols"]) for w in windows)
    missing = sum(len(w["missing_entries"]) for w in windows)
    partial = sum(len(w["partial_legs"]) for w in windows)
    data_quality = sum(len(w.get("data_quality_legs", [])) for w in windows)
    bench_missing = sum(len(w["benchmark_missing_entries"]) for w in windows)
    bench_partial = sum(len(w["benchmark_partial_legs"]) for w in windows)
    bench_data_quality = sum(
        len(w.get("benchmark_data_quality_legs", [])) for w in windows
    )
    bench_membership = sum(w.get("benchmark_membership_count", 0) for w in windows)
    bench_eligible = sum(w.get("benchmark_eligible_count", 0) for w in windows)
    bench_excluded = sum(
        w.get("benchmark_excluded_no_signal_close_count", 0) for w in windows
    )
    status = "PASS" if not (
        missing or partial or data_quality or bench_missing or bench_partial
        or bench_data_quality
    ) else "WARN"
    return _check(
        "missing_and_delisted_legs", status,
        f"{missing} unfilled, {partial} terminal, and {data_quality} unresolved/data-gap selected legs",
        windows=len(windows), selected_legs=selected, missing_entries=missing,
        partial_legs=partial, data_quality_legs=data_quality,
        benchmark_membership_legs=bench_membership,
        benchmark_eligible_signal_close_legs=bench_eligible,
        benchmark_excluded_no_signal_close_legs=bench_excluded,
        benchmark_signal_close_coverage_pct=(
            round(100 * bench_eligible / bench_membership, 6)
            if bench_membership else 0.0
        ),
        benchmark_missing_entries=bench_missing,
        benchmark_partial_legs=bench_partial,
        benchmark_data_quality_legs=bench_data_quality,
        policy=assumptions.missing_leg_policy,
    )


def split_leakage(
    idx: pd.DatetimeIndex, train_end: str, test_start: str,
    horizon: int = config.HORIZON_TDAYS, step: int = 21,
) -> Check:
    """Find training labels whose outcome window reaches the test period."""
    train_cut = pd.Timestamp(train_end)
    test_cut = pd.Timestamp(test_start)
    positions = backtest.positions_for(idx, None, None, step)
    leaking = []
    train_positions = []
    test_positions = []
    for pos in positions:
        signal_date = pd.Timestamp(idx[pos]).tz_localize(None)
        if signal_date <= train_cut:
            train_positions.append(pos)
            exit_date = pd.Timestamp(idx[pos + horizon]).tz_localize(None)
            if exit_date >= test_cut:
                leaking.append({"signal": str(signal_date.date()),
                                "label_end": str(exit_date.date())})
        if signal_date >= test_cut:
            test_positions.append(pos)
    status = "PASS" if not leaking else "FAIL"
    first_test = (str(pd.Timestamp(idx[test_positions[0] + 1]).date())
                  if test_positions else None)
    return _check(
        "train_test_leakage", status,
        "no training labels overlap test" if not leaking else
        f"{len(leaking)} training labels overlap the test period",
        train_end=train_end, test_start=test_start, horizon=horizon,
        leaking_windows=leaking, first_test_entry=first_test,
    )


def trial_count(path: Path) -> Check:
    if not path.exists():
        return _check("trial_count", "SKIP", f"missing {path}")
    text = path.read_text(encoding="utf-8")
    ids = []
    for line in text.splitlines():
        match = re.match(r"^\|\s*(H\d+[A-Za-z0-9'_-]*)\s*\|", line)
        if match:
            ids.append(match.group(1))
    unique = sorted(set(ids))
    status = "PASS" if unique else "FAIL"
    return _check(
        "trial_count", status,
        f"at least {len(unique)} registered hypothesis rows found",
        minimum_registered_trials=len(unique), hypothesis_ids=unique,
        warning="rows are a lower bound; every parameter/variant must also be counted",
    )


def artifact_and_claim_metadata(
    result_paths: list[Path], claim_path: Path,
    assumptions: execution.ExecutionAssumptions = execution.DEFAULT_EXECUTION,
    bars: dict | None = None, cache_mode: str | None = None,
) -> Check:
    required = {
        "provenance_schema_version", "generated_at", "git_commit", "git_dirty",
        "scout_source_hash", "engine_config", "data_fingerprint",
        "universe_mode", "signal_span", "data_span", "data_coverage",
        "entry_timing", "execution", "missing_leg_policy",
    }
    sha256 = re.compile(r"^[0-9a-f]{64}$")
    git_object = re.compile(r"^[0-9a-f]{40,64}$")
    current_git = backtest._git_state()
    current_source_hash = backtest._scout_source_hash()
    committed_source_hashes = {}
    artifacts = []
    failures = []
    for path in result_paths:
        if not path.exists():
            artifacts.append({"path": str(path), "status": "missing"})
            failures.append(f"{path.name}: missing")
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        meta = obj.get("artifact") or {}
        declared_status = obj.get("_artifact_status")
        absent = sorted(required - set(meta))
        engines = sorted((obj.get("engines") or {}).keys())
        engine_stale = config.ENGINE not in engines
        artifacts.append({"path": str(path), "missing_metadata": absent,
                          "engines": engines, "engine_config_stale": engine_stale,
                          "declared_artifact_status": declared_status,
                          "metadata": meta})
        if isinstance(declared_status, str) and declared_status.upper().startswith("STALE"):
            failures.append(f"{path.name}: explicitly marked {declared_status}")
        if absent:
            failures.append(f"{path.name}: missing {', '.join(absent)}")
        if engine_stale:
            failures.append(f"{path.name}: no {config.ENGINE} engine result")
        # Report execution differences even on a legacy artifact whose newer
        # provenance fields are absent; this keeps the failure diagnostic useful.
        expected_execution = assumptions.metadata()
        legacy_mismatches = {}
        if meta.get("engine_config") != config.ENGINE:
            legacy_mismatches["engine_config"] = {
                "artifact": meta.get("engine_config"), "expected": config.ENGINE,
            }
        if meta.get("entry_timing") != assumptions.entry_timing:
            legacy_mismatches["entry_timing"] = {
                "artifact": meta.get("entry_timing"),
                "expected": assumptions.entry_timing,
            }
        if meta.get("missing_leg_policy") != assumptions.missing_leg_policy:
            legacy_mismatches["missing_leg_policy"] = {
                "artifact": meta.get("missing_leg_policy"),
                "expected": assumptions.missing_leg_policy,
            }
        for key in ("spread_bps", "slippage_bps", "commission_bps"):
            actual = (meta.get("execution") or {}).get(key)
            expected = expected_execution[key]
            if actual != expected:
                legacy_mismatches[key] = {"artifact": actual, "expected": expected}
        artifacts[-1]["assumption_mismatches"] = legacy_mismatches
        if not absent:
            mismatches = {}
            if meta.get("engine_config") != config.ENGINE:
                mismatches["engine_config"] = {
                    "artifact": meta.get("engine_config"), "expected": config.ENGINE,
                }
            if meta.get("entry_timing") != assumptions.entry_timing:
                mismatches["entry_timing"] = {
                    "artifact": meta.get("entry_timing"),
                    "expected": assumptions.entry_timing,
                }
            if meta.get("missing_leg_policy") != assumptions.missing_leg_policy:
                mismatches["missing_leg_policy"] = {
                    "artifact": meta.get("missing_leg_policy"),
                    "expected": assumptions.missing_leg_policy,
                }
            for key in ("spread_bps", "slippage_bps", "commission_bps"):
                actual = (meta.get("execution") or {}).get(key)
                expected = expected_execution[key]
                if actual != expected:
                    mismatches[key] = {"artifact": actual, "expected": expected}

            if meta.get("provenance_schema_version") != 2:
                mismatches["provenance_schema_version"] = {
                    "artifact": meta.get("provenance_schema_version"), "expected": 2,
                }
            if meta.get("git_dirty") is not False:
                mismatches["git_dirty"] = {
                    "artifact": meta.get("git_dirty"), "expected": False,
                }
            declared_commit = meta.get("git_commit")
            if not isinstance(declared_commit, str) or not git_object.fullmatch(declared_commit):
                mismatches["git_commit"] = {
                    "artifact": declared_commit, "expected": "a full commit SHA",
                }
            source_hash = meta.get("scout_source_hash")
            if not isinstance(source_hash, str) or not sha256.fullmatch(source_hash):
                mismatches["scout_source_hash_format"] = {
                    "artifact": source_hash, "expected": "64 lowercase hex characters",
                }
            elif source_hash != current_source_hash:
                mismatches["scout_source_hash"] = {
                    "artifact": source_hash, "expected_current": current_source_hash,
                }
            if isinstance(declared_commit, str) and git_object.fullmatch(declared_commit):
                if declared_commit not in committed_source_hashes:
                    committed_source_hashes[declared_commit] = (
                        backtest._git_scout_source_hash(declared_commit)
                    )
                committed_source_hash = committed_source_hashes[declared_commit]
                artifacts[-1]["declared_commit_source_hash"] = committed_source_hash
                artifacts[-1]["current_git_commit"] = current_git.get("commit")
                if committed_source_hash is None:
                    mismatches["git_commit_unverifiable"] = {
                        "artifact": declared_commit,
                    }
                elif source_hash != committed_source_hash:
                    mismatches["scout_source_hash_at_git_commit"] = {
                        "artifact": source_hash,
                        "committed_source": committed_source_hash,
                    }
            fingerprint = meta.get("data_fingerprint")
            if not isinstance(fingerprint, str) or not sha256.fullmatch(fingerprint):
                mismatches["data_fingerprint_format"] = {
                    "artifact": fingerprint, "expected": "64 lowercase hex characters",
                }
            if meta.get("signal_span") != obj.get("span"):
                mismatches["signal_span"] = {
                    "artifact": meta.get("signal_span"), "top_level": obj.get("span"),
                }
            engine_result = (obj.get("engines") or {}).get(config.ENGINE) or {}
            all_summary = engine_result.get("all") or {}
            required_coverage_counts = {
                "selected_legs", "missing_entries", "partial_legs",
                "data_quality_legs", "benchmark_membership_legs",
                "benchmark_eligible_signal_close_legs",
                "benchmark_excluded_no_signal_close_legs",
                "benchmark_missing_entries", "benchmark_partial_legs",
                "benchmark_data_quality_legs",
            }
            absent_coverage_counts = sorted(
                required_coverage_counts - set(all_summary)
            )
            if absent_coverage_counts:
                mismatches["result_coverage_counts"] = {
                    "missing": absent_coverage_counts,
                }
            else:
                membership = all_summary["benchmark_membership_legs"]
                eligible = all_summary["benchmark_eligible_signal_close_legs"]
                excluded = all_summary["benchmark_excluded_no_signal_close_legs"]
                coverage_values = (membership, eligible, excluded)
                if (not all(isinstance(value, (int, float)) for value in coverage_values)
                        or membership != eligible + excluded):
                    mismatches["benchmark_coverage_arithmetic"] = {
                        "membership": membership, "eligible": eligible,
                        "excluded": excluded,
                    }
            compound_summary = (
                engine_result.get("compounded_non_overlapping") or {}
            )
            required_benchmark_fields = {
                "headline_benchmark", "spy_buy_and_hold_growth_pct",
                "spy_buy_and_hold_round_trips", "spy_window_reset_growth_pct",
                "spy_window_reset_round_trips",
                "eqw_market_window_reset_growth_pct",
            }
            absent_benchmark_fields = sorted(
                required_benchmark_fields - set(compound_summary)
            )
            if absent_benchmark_fields:
                mismatches["headline_benchmark_fields"] = {
                    "missing": absent_benchmark_fields,
                }
            elif compound_summary["spy_buy_and_hold_round_trips"] != 1:
                mismatches["headline_benchmark_round_trips"] = {
                    "artifact": compound_summary["spy_buy_and_hold_round_trips"],
                    "expected": 1,
                }
            universe_mode = meta.get("universe_mode")
            if universe_mode not in {"sp500", "pit500", "sp1500"}:
                mismatches["universe_mode"] = {
                    "artifact": universe_mode,
                    "expected": "sp500, pit500, or sp1500",
                }
            expected_mode_by_name = {
                "backtest_results.json": "sp500",
                "backtest_results_pit500.json": "pit500",
                "backtest_results_sp1500.json": "sp1500",
            }
            expected_path_mode = expected_mode_by_name.get(path.name)
            if expected_path_mode and universe_mode != expected_path_mode:
                mismatches["universe_mode_for_path"] = {
                    "artifact": universe_mode, "expected": expected_path_mode,
                }
            signal_span = meta.get("signal_span")
            data_span = meta.get("data_span")
            if not (isinstance(signal_span, list) and len(signal_span) == 2
                    and isinstance(data_span, list) and len(data_span) == 2):
                mismatches["span_shape"] = {
                    "signal_span": signal_span, "data_span": data_span,
                }
            else:
                try:
                    data_start, data_end = map(pd.Timestamp, data_span)
                    signal_start, signal_end = map(pd.Timestamp, signal_span)
                    contained = (
                        data_start <= signal_start <= signal_end <= data_end
                    )
                except (TypeError, ValueError):
                    contained = False
                if not contained:
                    mismatches["span_containment"] = {
                        "signal_span": signal_span, "data_span": data_span,
                    }

            coverage = meta.get("data_coverage") or {}
            fetch = coverage.get("fetch") or {}
            threshold = fetch.get("declared_threshold") or {}
            fetch_required = {
                "coverage_schema_version", "status", "requested_symbols",
                "requested_symbol_count", "returned_symbols",
                "returned_symbol_count", "missing_symbols",
                "missing_symbol_count", "missing_symbol_fraction",
                "declared_threshold", "threshold_passed", "universe_mode",
                "observed_start", "observed_end", "chunks",
            }
            missing_fetch_metadata = sorted(fetch_required - set(fetch))
            if missing_fetch_metadata:
                mismatches["data_coverage_missing_metadata"] = {
                    "missing": missing_fetch_metadata,
                }
            if coverage.get("status") != "complete" or fetch.get("status") != "complete":
                mismatches["data_coverage_status"] = {
                    "artifact": coverage.get("status"),
                    "fetch": fetch.get("status"), "expected": "complete",
                }
            if fetch.get("threshold_passed") is not True:
                mismatches["data_coverage_threshold_passed"] = {
                    "artifact": fetch.get("threshold_passed"), "expected": True,
                }
            chunks = fetch.get("chunks")
            if (not isinstance(chunks, list) or not chunks
                    or any(not isinstance(chunk, dict)
                           or chunk.get("completed") is not True
                           for chunk in chunks)):
                mismatches["data_coverage_chunks"] = {
                    "artifact": chunks,
                    "expected": "one or more completed chunk records",
                }
            configured_missing = config.BACKTEST_MAX_MISSING_SYMBOL_FRACTION
            if threshold.get("name") != "BACKTEST_MAX_MISSING_SYMBOL_FRACTION":
                mismatches["data_coverage_threshold_name"] = {
                    "artifact": threshold.get("name"),
                    "expected": "BACKTEST_MAX_MISSING_SYMBOL_FRACTION",
                }
            if threshold.get("max_missing_symbol_fraction") != configured_missing:
                mismatches["data_coverage_threshold"] = {
                    "artifact": threshold.get("max_missing_symbol_fraction"),
                    "expected": configured_missing,
                }
            if coverage.get("universe_mode") != meta.get("universe_mode"):
                mismatches["data_coverage_universe"] = {
                    "coverage": coverage.get("universe_mode"),
                    "artifact": meta.get("universe_mode"),
                }
            if coverage.get("observed_data_span") != meta.get("data_span"):
                mismatches["data_span"] = {
                    "coverage": coverage.get("observed_data_span"),
                    "artifact": meta.get("data_span"),
                }
            field_coverage = coverage.get("fields") or {}
            missing_fields = sorted({"open", "close", "volume"} - set(field_coverage))
            if missing_fields:
                mismatches["data_coverage_fields"] = {"missing": missing_fields}
            else:
                for field in ("open", "close", "volume"):
                    facts = field_coverage.get(field) or {}
                    required_facts = {
                        "rows", "columns", "symbols_with_any_value",
                        "non_null_values",
                    }
                    absent_facts = sorted(required_facts - set(facts))
                    if absent_facts:
                        mismatches[f"data_coverage_{field}"] = {
                            "missing": absent_facts,
                        }
                    elif any(not isinstance(facts[key], int) or facts[key] <= 0
                             for key in required_facts):
                        mismatches[f"data_coverage_{field}"] = {
                            "artifact": facts,
                            "expected": "positive integer coverage counts",
                        }
            if fetch.get("requested_symbol_count") != len(fetch.get("requested_symbols", [])):
                mismatches["requested_symbol_count"] = {
                    "declared": fetch.get("requested_symbol_count"),
                    "observed": len(fetch.get("requested_symbols", [])),
                }
            if fetch.get("returned_symbol_count") != len(fetch.get("returned_symbols", [])):
                mismatches["returned_symbol_count"] = {
                    "declared": fetch.get("returned_symbol_count"),
                    "observed": len(fetch.get("returned_symbols", [])),
                }
            if fetch.get("missing_symbol_count") != len(fetch.get("missing_symbols", [])):
                mismatches["missing_symbol_count"] = {
                    "declared": fetch.get("missing_symbol_count"),
                    "observed": len(fetch.get("missing_symbols", [])),
                }
            requested_count = fetch.get("requested_symbol_count")
            missing_count = fetch.get("missing_symbol_count")
            if isinstance(requested_count, int) and requested_count > 0 \
                    and isinstance(missing_count, int):
                observed_fraction = missing_count / requested_count
                declared_fraction = fetch.get("missing_symbol_fraction")
                if not isinstance(declared_fraction, (int, float)) or not math.isclose(
                    float(declared_fraction), observed_fraction,
                    rel_tol=0, abs_tol=1e-12,
                ):
                    mismatches["missing_symbol_fraction"] = {
                        "declared": declared_fraction,
                        "observed": observed_fraction,
                    }

            if bars is not None and cache_mode == meta.get("universe_mode"):
                observed_fingerprint = backtest._data_fingerprint(bars)
                artifacts[-1]["data_fingerprint_verified"] = True
                if fingerprint != observed_fingerprint:
                    mismatches["data_fingerprint"] = {
                        "artifact": fingerprint, "cache": observed_fingerprint,
                    }
            else:
                artifacts[-1]["data_fingerprint_verified"] = False
                artifacts[-1]["data_fingerprint_not_checked_reason"] = (
                    "no loaded cache for this artifact's universe"
                )
            artifacts[-1]["assumption_mismatches"] = mismatches
            if mismatches:
                failures.append(
                    f"{path.name}: provenance/assumptions differ on "
                    f"{', '.join(mismatches)}"
                )

    stale_claims = []
    if claim_path.exists():
        for number, line in enumerate(claim_path.read_text(encoding="utf-8").splitlines(), 1):
            low = line.lower()
            if "no costs" in low or "symbols delisted mid-window are dropped" in low:
                stale_claims.append({"line": number, "text": line.strip()})
    if stale_claims:
        failures.append(f"{claim_path.name}: {len(stale_claims)} pre-correctness claims")
    status = "PASS" if not failures else "FAIL"
    return _check(
        "artifact_and_claim_metadata", status,
        "artifacts and claims match current assumptions" if not failures else
        f"{len(failures)} stale/missing metadata problems",
        artifacts=artifacts, stale_claims=stale_claims, problems=failures,
    )


def survivorship_from_artifacts(current_path: Path, pit_path: Path) -> Check:
    if not current_path.exists() or not pit_path.exists():
        return _check("survivorship", "SKIP", "current and PIT artifacts are required")
    cur = json.loads(current_path.read_text(encoding="utf-8"))
    pit_obj = json.loads(pit_path.read_text(encoding="utf-8"))
    engine = config.ENGINE
    cur_engines, pit_engines = cur.get("engines", {}), pit_obj.get("engines", {})
    if engine not in cur_engines or engine not in pit_engines:
        return _check("survivorship", "WARN", f"{engine} is absent from one artifact",
                      current_engines=sorted(cur_engines), pit_engines=sorted(pit_engines))
    cur_all = cur_engines[engine]["all"]
    pit_all = pit_engines[engine]["all"]
    hit_bias = float(cur_all["hit_rate"]) - float(pit_all["hit_rate"])
    end_bias = float(cur_all["avg_end_ret"]) - float(pit_all["avg_end_ret"])
    return _check(
        "survivorship", "WARN" if abs(end_bias) >= 0.5 else "PASS",
        f"current-members result differs from PIT by {end_bias:+.2f} points/window",
        engine=engine, hit_rate_bias_pct_points=round(hit_bias, 3),
        avg_end_bias_pct_points=round(end_bias, 3),
        current=cur_all, point_in_time=pit_all,
    )


def unresolved_checks(checks: list[Check], waivers: set[str] | None = None) -> list[Check]:
    """Strict-by-default: WARN and SKIP are unresolved, not successful."""
    waived = waivers or set()
    return [check for check in checks
            if check.status != "PASS" and check.name not in waived]


def render(checks: list[Check], waivers: set[str] | None = None) -> None:
    waived = waivers or set()
    print("BACKTEST LIE DETECTOR")
    print("=====================")
    for check in checks:
        display = "WAIVE" if check.name in waived and check.status != "PASS" else check.status
        print(f"{display:>5}  {check.name:<28} {check.summary}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scout.audit")
    ap.add_argument("--universe", default="sp1500",
                    choices=["sp500", "pit500", "sp1500"])
    ap.add_argument("--cache", default=None,
                    help="existing local pickle; audit never downloads bars")
    ap.add_argument("--picks", type=int, default=5)
    ap.add_argument("--step", type=int, default=21)
    ap.add_argument("--phase-step", type=int, default=7)
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--train-end", default="2021-12-31")
    ap.add_argument("--test-start", default="2022-01-01")
    ap.add_argument("--results", action="append", default=None,
                    help="result artifact; may be supplied more than once")
    ap.add_argument("--claims", default=str(config.ROOT / "BACKTEST-REPORT.md"))
    ap.add_argument("--hypotheses", default=str(config.SCOUT_DIR / "hypotheses.md"))
    ap.add_argument("--json-out", default=None)
    ap.add_argument(
        "--waive", action="append", default=[], metavar="CHECK_NAME",
        help="explicitly waive one named non-PASS check; repeat for each waiver",
    )
    execution.add_execution_args(ap)
    args = ap.parse_args(argv)
    assumptions = execution.from_args(args)

    defaults = [config.SCOUT_DIR / "backtest_results.json",
                config.SCOUT_DIR / "backtest_results_pit500.json",
                config.SCOUT_DIR / "backtest_results_sp1500.json"]
    result_paths = [Path(p) for p in args.results] if args.results else defaults
    bars, cache_path = load_cached_bars(args.universe, args.cache)
    checks = [
        artifact_and_claim_metadata(
            result_paths, Path(args.claims), assumptions, bars, args.universe,
        ),
        trial_count(Path(args.hypotheses)),
        survivorship_from_artifacts(defaults[0], defaults[1]),
    ]

    if bars is None:
        checks.append(_check(
            "dynamic_controls", "SKIP",
            f"no local cache at {cache_path}; no network request was made",
        ))
    else:
        checks.extend([
            cache_data_coverage(bars, cache_path, args.universe),
            split_leakage(bars["close"].index, args.train_end, args.test_start,
                          step=args.step),
            phase_sensitivity(bars, args.universe, args.picks, args.phase_step,
                              assumptions, args.start, args.end),
            random_pick_lift(bars, args.universe, args.picks, args.step, args.draws,
                             assumptions, args.start, args.end),
            missing_leg_audit(bars, args.universe, args.picks, args.step,
                              assumptions, args.start, args.end),
            cost_sensitivity(bars, args.universe, args.picks, args.step,
                             assumptions, args.start, args.end),
        ])
    requested_waivers = set(args.waive)
    known = {check.name for check in checks}
    waivers = requested_waivers & known
    unknown = sorted(requested_waivers - known)
    if unknown:
        checks.append(_check(
            "waiver_validation", "FAIL",
            f"unknown waiver names: {', '.join(unknown)}",
            unknown_waivers=unknown,
        ))
    unresolved = unresolved_checks(checks, waivers)
    exit_code = 1 if unresolved else 0
    render(checks, waivers)
    payload = {
        "strict_default": True,
        "waived_checks": sorted(waivers),
        "unresolved_checks": [check.name for check in unresolved],
        "exit_code": exit_code,
        "checks": [asdict(c) for c in checks],
    }
    print("\nRESULT_JSON: " + json.dumps(payload))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
