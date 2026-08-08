"""Stock Scout CLI — run via  python -m scout.cli <command>  (from the repo
root, using the project venv if there is one).

Commands:
  scan             score the universe, write top candidates to scout/last_scan.json
  update           re-price OPEN picks in picks.xlsx, resolve HIT/MISS
  record <json>    append finalized picks (after research) from JSON to picks.xlsx
  calibrate        force a calibration refresh

Two rankings, both from empirical cells (score bucket × vol group × regime):
- Overall Score = 1000 * P(+5%) * usual peak gain * (42 / usual days to +5%)
                  * (1 - P(-5% dip first))       [chance x gain x speed x safety]
- Gain Score    = 1000 * usual peak gain * P(+10%), only for stocks whose
                  P(+5%) >= GAIN_MIN_P5 (user's 62% floor); within a tied
                  cell, the stock's own volatility breaks ties (bigger engine
                  travels further).
"""
import argparse
import json
import math
from datetime import date, datetime

import pandas as pd

from . import calibrate, config, data, earnings, excel_book, signals, universe

POOL = 30   # composite-score pool that the rankings then re-order


def _as_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _grade(stats: dict | None, base: float | None) -> str:
    if not stats or base is None or stats.get("n_eff", 0) < config.MIN_NEFF:
        return "C"
    if stats.get("lift") and stats["lift"] >= 1.10 and stats["lo"] > base + 0.02:
        return "A"
    if stats["p5_raw"] > base:
        return "B"
    return "C"


def _opp_score(s: dict) -> float | None:
    """Assurance x profit x speed x safety. Profit = MEAN max gain (not
    median): 5% is the minimum bar, so cells whose winners run further get
    ranked higher — 'if I can, I want more'."""
    if not s or s.get("p5") is None or not s.get("med_days_to_hit"):
        return None
    gain = s.get("mean_max_gain", s.get("med_max_gain"))
    return round(1000 * s["p5"] * max(gain, 0)
                 * (config.HORIZON_TDAYS / s["med_days_to_hit"])
                 * (1 - s["p_drop_first"]), 1)


def _gain_score(s: dict) -> float | None:
    if not s or s.get("p10") is None:
        return None
    gain = s.get("mean_max_gain", s.get("med_max_gain"))
    if gain is None:
        return None
    return round(1000 * max(gain, 0) * s["p10"], 1)


def cmd_scan(args) -> None:
    uni = universe.load()
    info = {u["symbol"]: u for u in uni}
    cal = calibrate.run(force=args.force)

    syms = sorted(set(info) | {calibrate.REGIME_SYM})
    print(f"scan: fetching bars for {len(syms)} symbols...")
    bars = data.daily_ohlcv(syms, config.SCAN_HISTORY_DAYS)
    c = bars["close"]
    frames = signals.feature_frames(bars["open"], c, bars["volume"])
    ts = c.index[-1]
    snap = signals.composite_at(frames, ts).drop(index=[calibrate.REGIME_SYM],
                                                 errors="ignore")
    pct = snap["score"].rank(pct=True)
    terc = pd.cut(snap["vol"].rank(pct=True), [0, 1 / 3, 2 / 3, 1.01],
                  labels=["lowvol", "midvol", "highvol"])

    spy = c[calibrate.REGIME_SYM].dropna()
    regime = ("bull" if float(spy.iloc[-1]) > float(spy.rolling(200).mean().iloc[-1])
              else "bear")
    spy_vol21 = float(spy.pct_change().rolling(21).std().iloc[-1] * math.sqrt(252))
    crash_risk = regime == "bear" and spy_vol21 > cal.get("spy_vol_q80", 99)
    reg = cal["regimes"].get(regime, {})
    base = reg.get("base_rate")
    horizon_end = (ts + pd.tseries.offsets.BDay(config.HORIZON_TDAYS)).date()

    pool_syms = list(snap.index[:POOL])
    print("checking earnings calendars (best-effort)...")
    ecal = earnings.next_earnings(pool_syms)
    n_edates = sum(1 for v in ecal.values() if v)
    if n_edates == 0:
        print("  no earnings source reachable — the research phase must "
              "check earnings dates by web search instead")

    candidates = []
    for sym in pool_syms:
        row = snap.loc[sym]
        bucket = calibrate.bucket_of(float(pct[sym]))
        bstats = (reg.get("buckets") or {}).get(bucket) or {}
        cell = (bstats.get("terciles") or {}).get(str(terc[sym]))
        stats = cell if cell and cell.get("n_eff", 0) >= config.MIN_NEFF else bstats
        quotable = bool(stats and stats.get("n_eff", 0) >= config.MIN_NEFF)
        price = float(c[sym].dropna().iloc[-1])
        edate = ecal.get(sym)
        e_inside = bool(edate and str(edate) <= str(horizon_end))
        grade = _grade(stats, base)
        if e_inside and grade in ("A", "B"):
            grade = {"A": "B", "B": "C"}[grade]   # binary event inside window
        sigma42 = float(row["vol"]) * math.sqrt(config.HORIZON_TDAYS / 252)
        disaster_price = round(price * (1 - config.SELL_DISASTER_SIGMA * sigma42), 2)
        sig_text = (f"12-1 mom {row['mom']:+.0%} (p{row['mom_pct']:.0%}); "
                    f"6-1 mom {row['mom6']:+.0%}; "
                    f"{row['high']:.0%} of 52w high; "
                    f"{row['brk20']:.0%} of 20d high; "
                    f"1m {row['ret1m']:+.1%}; vol {row['vol']:.0%} ({terc[sym]})"
                    + ("; recent up-gap+volume surge" if row["gap"] > 0 else "")
                    + (f"; EARNINGS {edate} inside window" if e_inside else ""))
        p5 = stats.get("p5") if quotable else None
        candidates.append({
            "symbol": sym, "name": info.get(sym, {}).get("name", ""),
            "sector": info.get(sym, {}).get("sector", ""),
            "price": round(price, 2),
            "target_price": round(price * (1 + config.TARGET_GAIN), 2),
            "score": round(float(row["score"]), 1),
            "rank_pct": round(float(pct[sym]), 3),
            "bucket": bucket, "vol_tercile": str(terc[sym]),
            "vol": round(float(row["vol"]), 3),
            "cell": "tercile" if stats is cell else "bucket",
            "opp_score": _opp_score(stats) if quotable else None,
            "gain_score": _gain_score(stats) if quotable else None,
            "gain_eligible": bool(quotable and p5 is not None
                                  and p5 >= config.GAIN_MIN_P5),
            "p5": p5,
            "p10": stats.get("p10") if quotable else None,
            "p15": stats.get("p15") if quotable else None,
            "mean_max_gain": stats.get("mean_max_gain") if quotable else None,
            "pend5": stats.get("pend5") if quotable else None,
            "ci": [stats["lo"], stats["hi"]] if quotable else None,
            "lift": stats.get("lift") if quotable else None,
            "p_drop_first": stats.get("p_drop_first") if quotable else None,
            "med_end_ret": stats.get("med_end_ret") if quotable else None,
            "med_max_gain": stats.get("med_max_gain") if quotable else None,
            "med_days_to_hit": stats.get("med_days_to_hit") if quotable else None,
            "p5_end_ret": stats.get("p5_end_ret") if quotable else None,
            "n_eff": stats.get("n_eff") if stats else None,
            "grade_quant": grade,
            "earnings_date": edate,
            "earnings_in_window": e_inside,
            "sigma42": round(sigma42, 4),
            "disaster_price": disaster_price,
            "sell_if": (f"this stock's normal 2-month move is about "
                        f"±{sigma42:.0%}; sell on a close at/below "
                        f"${disaster_price} (2x that move — its own disaster "
                        f"level; ordinary stops tested worse); once it "
                        f"touches ${round(price * (1 + config.TARGET_GAIN), 2)}, "
                        f"never let it become a loss — sell on any close "
                        f"at/below breakeven (${round(price, 2)}); otherwise "
                        f"sell at the deadline {horizon_end}"),
            "signals_text": sig_text,
        })
    # earnings-clean candidates rank ahead of earnings-in-window ones:
    # windows containing an event day carry a 30% (vs 7%) chance of ending
    # below -10%, and skipping them tested better on train AND holdout
    candidates.sort(key=lambda cd: (cd["opp_score"] is None,
                                    bool(cd["earnings_in_window"]),
                                    -(cd["opp_score"] or 0), -cd["score"]))
    candidates = candidates[:config.TOP_CANDIDATES]
    big_gain_order = sorted(
        [cd for cd in candidates if cd["gain_eligible"]],
        key=lambda cd: (bool(cd["earnings_in_window"]),
                        -(cd["gain_score"] or 0), -cd["vol"], -cd["score"]))

    out = {"asof": str(ts.date()), "engine": config.ENGINE,
           "earnings_checked": n_edates > 0,
           "regime": regime, "crash_risk": crash_risk,
           "spy_vol21": round(spy_vol21, 4), "base_rate": base,
           "market_base_rate": reg.get("market_base_rate"),
           "horizon_end": str(horizon_end), "target_gain": config.TARGET_GAIN,
           "gain_min_p5": config.GAIN_MIN_P5,
           "label": cal.get("label"), "opp_score_def": cal.get("opp_score"),
           "caveats": cal.get("caveats", []),
           "calibration": {"generated": cal["generated"], "span": cal["span"],
                           "n_dates": cal["n_dates"],
                           "engine": cal.get("engine", "v1")},
           "overall_order": [cd["symbol"] for cd in candidates],
           "big_gain_order": [cd["symbol"] for cd in big_gain_order],
           "candidates": candidates}
    config.LAST_SCAN_JSON.write_text(json.dumps(out, indent=1), encoding="utf-8")

    mkt = reg.get("market_base_rate")
    print(f"\nasof {out['asof']} | engine {config.ENGINE} | regime {regime.upper()}"
          + (f" | market base {mkt:.0%}" if mkt else "")
          + (f" | after quality gates {base:.0%} touch +5% within 2 months"
             if base is not None else ""))
    if crash_risk:
        print("!! CRASH-RISK REGIME (bear + high SPY vol): momentum signals "
              "historically invert here. Strong case for ZERO picks this cycle.")
    print(f"{'sym':<6}{'opp':>6}{'gain':>6}{'P+5%':>6}{'P+10%':>6}{'peak':>6}"
          f"{'days':>5}{'dip':>5}{'grade':>6}  signals")
    for cd in candidates:
        if cd["opp_score"] is not None:
            print(f"{cd['symbol']:<6}{cd['opp_score']:>6.1f}{cd['gain_score']:>6.1f}"
                  f"{cd['p5']:>6.0%}{cd['p10']:>6.0%}{cd['med_max_gain']:>6.1%}"
                  f"{cd['med_days_to_hit']:>5.0f}{cd['p_drop_first']:>5.0%}"
                  f"{cd['grade_quant']:>6}  {cd['signals_text']}")
        else:
            print(f"{cd['symbol']:<6}{'n/q':>6}{'':>34}{cd['grade_quant']:>6}  "
                  f"{cd['signals_text']}")
    print(f"\nbig-gain eligible (P+5% >= {config.GAIN_MIN_P5:.0%}): "
          + (", ".join(out["big_gain_order"]) or "NONE this run"))
    print(f"wrote {config.LAST_SCAN_JSON}")


def _sell_signal(result: str, basis: float, latest: float, peak: float,
                 hz_end: date, disaster: float, per_stock: bool = True) -> str:
    """Plain-language sell instruction (see the sell-guidance block in
    config). `disaster` is this stock's own level (2x its expected 2-month
    move below entry, computed at pick time). Guidance only — never changes
    the HIT/MISS labels the scoreboard is graded on."""
    if result == "MISS":
        return "SELL — deadline passed"
    if result == "HIT":
        if latest <= basis:
            return (f"SELL — hit +5%, then closed back at/below breakeven "
                    f"(${basis:.2f}); never let a winner become a loss")
        return (f"hold — it already hit +5%: sell on any close at/below "
                f"breakeven (${basis:.2f}), otherwise sell at the deadline "
                f"{hz_end}")
    kind = ("this stock's own disaster level, 2x its normal 2-month move"
            if per_stock else "-15% fallback level; per-stock levels start "
            "with newly recorded picks")
    if latest <= disaster:
        return (f"SELL — closed at/below ${disaster:.2f} ({kind}); the "
                f"pattern is broken")
    return (f"hold — ordinary stops tested worse; sell only on a close "
            f"at/below ${disaster:.2f} ({kind}), else at the deadline "
            f"{hz_end}")


def cmd_update(args) -> None:
    picks = excel_book.open_picks()
    if not picks:
        print("no OPEN picks to update")
        return
    tickers = sorted({p["Stock"] for p in picks})
    earliest = min(_as_date(p["Date Picked"]) for p in picks)
    days = (date.today() - earliest).days + 10
    print(f"update: re-pricing {len(picks)} open picks ({len(tickers)} tickers)...")
    bars = data.daily_ohlcv(tickers, max(days, 15))
    c = bars["close"]

    updates, resolved, no_data = [], [], []
    for p in picks:
        sym, basis = p["Stock"], float(p["Price Then"])
        pick_d, hz_end = _as_date(p["Date Picked"]), _as_date(p["Deadline"])
        if sym not in c:
            no_data.append(sym)
            continue
        s = c[sym].dropna()
        after = s[s.index.date > pick_d]
        if after.empty:
            no_data.append(sym)
            continue
        latest = float(after.iloc[-1])
        within = after[after.index.date <= hz_end]
        maxc = float(within.max()) if not within.empty else latest
        u = {"_row": p["_row"], "Price Now": round(latest, 2),
             "Gain So Far %": round(100 * (latest / basis - 1), 1),
             "Best So Far %": round(100 * (maxc / basis - 1), 1)}
        if p["Result"] == "HIT":
            # already resolved — keep tracking the run-up until the deadline
            u["Result"] = "HIT"
        elif maxc / basis - 1 >= config.TARGET_GAIN:
            first_hit = within[within / basis - 1 >= config.TARGET_GAIN].index[0]
            u["Result"], u["Hit Date"] = "HIT", str(first_hit.date())
            resolved.append(f"{sym} HIT on {u['Hit Date']} "
                            f"(best {u['Best So Far %']:+.1f}%)")
        elif date.today() > hz_end:
            u["Result"] = "MISS"
            resolved.append(f"{sym} MISS (best reached {u['Best So Far %']:+.1f}%)")
        else:
            u["Result"] = "OPEN"
        stored = p.get("Sell Below (Disaster)")
        per_stock = isinstance(stored, (int, float))
        disaster = (float(stored) if per_stock
                    else basis * (1 - config.SELL_DISASTER_FALLBACK))
        u["Sell Signal"] = _sell_signal(u["Result"], basis, latest, maxc,
                                        hz_end, disaster, per_stock)
        if u["Sell Signal"].startswith("SELL"):
            resolved.append(f"{sym} sell signal: {u['Sell Signal']}")
        updates.append(u)

    excel_book.resolve(updates)
    print(f"updated {len(updates)} picks -> {config.EXCEL_PATH}")
    for line in resolved:
        print(f"  {line}")
    if no_data:
        print(f"  no new trading day since pick yet for: {', '.join(no_data)}")


LIST_NAMES = {"overall": "Best Overall", "big_gain": "Biggest Gain",
              "both": "Both"}


def cmd_record(args) -> None:
    scan = json.loads(config.LAST_SCAN_JSON.read_text(encoding="utf-8"))
    by_sym = {cd["symbol"]: cd for cd in scan["candidates"]}
    with open(args.file, encoding="utf-8") as f:
        finals = json.load(f)

    def pc(x, digits=1):
        return round(100 * x, digits) if x is not None else ""

    rows = []
    for fp in finals:
        cd = by_sym.get(fp["symbol"])
        if not cd:
            print(f"  {fp['symbol']} not in last scan — skipped")
            continue
        rows.append({
            "Date Picked": scan["asof"], "Stock": cd["symbol"],
            "Company": cd["name"], "Industry": cd["sector"],
            "List": LIST_NAMES.get(fp.get("list", "overall"), "Best Overall"),
            "Price Then": cd["price"], "Min Goal (+5%)": cd["target_price"],
            "Deadline": scan["horizon_end"],
            "Chance +5%": pc(cd.get("p5")) or "no number",
            "Chance +10%": pc(cd.get("p10")),
            "Chance +15%": pc(cd.get("p15")),
            "Earnings Before Deadline": ((cd.get("earnings_date") or "")
                                         if cd.get("earnings_in_window") else ""),
            "Usual Gain %": pc(cd.get("med_end_ret")),
            "Usual Peak %": pc(cd.get("med_max_gain")),
            "Analysts' Guess % (corrected)": fp.get("analyst_guess_corrected", ""),
            "Usual Days to +5%": cd.get("med_days_to_hit") or "",
            "Chance of -5% Dip First": pc(cd.get("p_drop_first")),
            "Avg Stock Chance +5%": pc(scan.get("base_rate")),
            "Overall Score": cd.get("opp_score") or "",
            "Gain Score": cd.get("gain_score") or "",
            "Confidence": fp.get("grade", cd["grade_quant"]),
            "Why (short)": fp.get("thesis", ""),
            "Result": "OPEN", "Last Checked": str(date.today()),
            "Engine": scan.get("engine", config.ENGINE),
            "Sell Signal": cd.get("sell_if", ""),
            "Sell Below (Disaster)": cd.get("disaster_price", ""),
        })
    n = excel_book.append_picks(rows)
    print(f"recorded {n} picks -> {config.EXCEL_PATH}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_scan = sub.add_parser("scan")
    p_scan.add_argument("--force", action="store_true", help="force recalibration first")
    sub.add_parser("update")
    p_rec = sub.add_parser("record")
    p_rec.add_argument("file")
    sub.add_parser("calibrate")
    args = ap.parse_args()
    if args.cmd == "scan":
        cmd_scan(args)
    elif args.cmd == "update":
        cmd_update(args)
    elif args.cmd == "record":
        cmd_record(args)
    elif args.cmd == "calibrate":
        calibrate.run(force=True)


if __name__ == "__main__":
    main()
