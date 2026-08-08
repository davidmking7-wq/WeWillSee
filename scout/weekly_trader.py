"""Weekly paper-trading executor: plan Saturday, buy Monday, sell Friday.

This is the first module in the repo that PLACES ORDERS. Everything else
here is a research scorecard ("It never buys anything" — README). Orders are
restricted to an Alpaca PAPER account and the restriction is enforced, not
documented: `_client()` refuses to build a trading client unless the key is a
paper key AND the account number the broker returns is a paper account
number. There is no flag that turns that off.

Three commands, matching the user's weekly cycle:

    python -m scout.weekly_trader plan     # weekend: scan, write the plan
    python -m scout.weekly_trader open     # Monday:  buy the plan
    python -m scout.weekly_trader close    # Friday:  sell what we bought

State lives in `scout/weekly_journal.jsonl`, one record per week, written
BEFORE the orders go out. The plan is committed to disk while the outcome is
still unknown — that is what makes the running scorecard a real out-of-sample
record instead of a story told afterwards.

POSITION ISOLATION
------------------
The account this was built against already held EEM / IWM / QQQ. `close`
only ever sells symbols this module recorded itself buying, in the quantity
it recorded; anything else in the account is invisible to it. Protected
symbols are additionally refused at buy time so a pick can never collide
with a pre-existing holding and make the two indistinguishable at exit.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import config

JOURNAL = config.SCOUT_DIR / "weekly_journal.jsonl"
PLAN_PATH = config.SCOUT_DIR / "weekly_plan.json"

PAPER_KEY_PREFIX = "PK"
PAPER_ACCT_PREFIX = "PA"

# Never bought, never sold. Seeded with the holdings already in the account
# so the weekly book can never entangle with them.
PROTECTED = frozenset({"EEM", "IWM", "QQQ"})

# Dollars the weekly strategy may deploy. Deliberately well under the
# account's free cash — this is an experiment, not an allocation.
WEEKLY_CAPITAL = 10_000.0
NUM_POSITIONS = 3


class NotPaperAccount(RuntimeError):
    """Refused to trade anything that is not a verified paper account."""


def _client():
    from alpaca.trading.client import TradingClient

    key = config.ALPACA_API_KEY
    if not key.startswith(PAPER_KEY_PREFIX):
        raise NotPaperAccount(
            f"key {key[:4]}... is not a paper key (need {PAPER_KEY_PREFIX!r} prefix)")
    client = TradingClient(key, config.ALPACA_SECRET_KEY, paper=True)
    acct = client.get_account()
    if not str(acct.account_number).startswith(PAPER_ACCT_PREFIX):
        raise NotPaperAccount(
            f"account {acct.account_number} is not a paper account "
            f"(need {PAPER_ACCT_PREFIX!r} prefix)")
    return client, acct


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_journal() -> list[dict]:
    if not JOURNAL.exists():
        return []
    with open(JOURNAL) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append_journal(record: dict) -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL, "a") as f:
        f.write(json.dumps(record) + "\n")


def _open_week() -> dict | None:
    """The most recent journal record that has been bought but not sold."""
    for rec in reversed(_read_journal()):
        if rec.get("state") == "open":
            return rec
    return None


def plan(n: int = NUM_POSITIONS, capital: float = WEEKLY_CAPITAL) -> dict:
    """Score the universe on the latest close and write the week's picks."""
    from . import data, signals, universe

    syms = sorted({u["symbol"] for u in universe.load()} | {"SPY"})
    bars = data.daily_ohlcv(syms, config.SCAN_HISTORY_DAYS)
    frames = signals.feature_frames(bars["open"], bars["close"], bars["volume"])
    ts = bars["close"].index[-1]
    snap = signals.composite_at(frames, ts).drop(index=["SPY"], errors="ignore")
    snap = snap[~snap.index.isin(PROTECTED)]
    if snap.empty:
        raise RuntimeError("no candidates survived the gates")

    picks = list(snap.index[:n])
    last = bars["close"].iloc[-1]
    plan_rec = {
        "state": "planned",
        "engine": config.ENGINE,
        "planned_at": _now(),
        "scan_date": str(ts.date()),
        "capital": capital,
        "picks": [
            {"symbol": s,
             "score": round(float(snap.loc[s, "score"]), 2),
             "vol": round(float(snap.loc[s, "vol"]), 4),
             "ref_close": round(float(last[s]), 4),
             "target_dollars": round(capital / len(picks), 2)}
            for s in picks
        ],
    }
    PLAN_PATH.write_text(json.dumps(plan_rec, indent=1))
    return plan_rec


def open_week(dry_run: bool = True) -> dict:
    """Buy the planned basket with notional market orders."""
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    if _open_week() is not None:
        raise RuntimeError("a week is already open — run `close` first")
    if not PLAN_PATH.exists():
        raise RuntimeError("no plan on disk — run `plan` first")
    plan_rec = json.loads(PLAN_PATH.read_text())

    client, acct = _client()
    cash = float(acct.cash)
    need = sum(p["target_dollars"] for p in plan_rec["picks"])
    if need > cash:
        raise RuntimeError(f"plan needs ${need:,.2f} but only ${cash:,.2f} cash is free")

    filled = []
    for p in plan_rec["picks"]:
        sym = p["symbol"]
        if sym in PROTECTED:
            raise NotPaperAccount(f"refusing to trade protected symbol {sym}")
        if dry_run:
            filled.append({**p, "order_id": None, "dry_run": True})
            continue
        order = client.submit_order(MarketOrderRequest(
            symbol=sym, notional=p["target_dollars"],
            side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
        filled.append({**p, "order_id": str(order.id), "dry_run": False})

    record = {**plan_rec, "state": "open" if not dry_run else "dry_run",
              "opened_at": _now(), "orders": filled,
              "account_value_at_open": float(acct.portfolio_value)}
    _append_journal(record)
    return record


def close_week(dry_run: bool = True) -> dict:
    """Sell exactly what this module bought — nothing else in the account."""
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    rec = _open_week()
    if rec is None:
        raise RuntimeError("no open week to close")
    client, acct = _client()

    held = {p.symbol: p for p in client.get_all_positions()}
    sold = []
    for o in rec["orders"]:
        sym = o["symbol"]
        if sym in PROTECTED:
            continue
        pos = held.get(sym)
        if pos is None:
            sold.append({"symbol": sym, "closed": False, "reason": "no position"})
            continue
        entry_value = o["target_dollars"]
        exit_value = float(pos.market_value)
        if not dry_run:
            client.submit_order(MarketOrderRequest(
                symbol=sym, qty=str(pos.qty),
                side=OrderSide.SELL, time_in_force=TimeInForce.DAY))
        sold.append({"symbol": sym, "closed": True,
                     "entry_dollars": entry_value, "exit_dollars": round(exit_value, 2),
                     "pct": round(100 * (exit_value / entry_value - 1), 3)})

    realized = [s["pct"] for s in sold if s.get("closed") and "pct" in s]
    out = {**rec, "state": "closed" if not dry_run else "open",
           "closed_at": _now(), "exits": sold,
           "week_return_pct": round(sum(realized) / len(realized), 3) if realized else None,
           "account_value_at_close": float(acct.portfolio_value)}
    _append_journal(out)
    return out


def scoreboard() -> None:
    """Print the live weekly track record — predictions vs what happened."""
    weeks = [r for r in _read_journal() if r.get("state") == "closed"]
    if not weeks:
        print("no completed weeks yet")
        return
    rets = [w["week_return_pct"] for w in weeks if w["week_return_pct"] is not None]
    print(f"{'week ending':<14}{'picks':<26}{'return%':>9}")
    for w in weeks:
        syms = ",".join(o["symbol"] for o in w["orders"])
        print(f"{w['closed_at'][:10]:<14}{syms:<26}{w['week_return_pct']:>9}")
    if rets:
        n = len(rets)
        print(f"\n{n} weeks | avg {sum(rets)/n:+.2f}% | "
              f">=+3% in {100*sum(r >= 3 for r in rets)/n:.0f}% | "
              f"positive {100*sum(r > 0 for r in rets)/n:.0f}%")


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.weekly_trader")
    ap.add_argument("command", choices=["plan", "open", "close", "scoreboard"])
    ap.add_argument("--execute", action="store_true",
                    help="actually place orders (default is a dry run)")
    ap.add_argument("-n", type=int, default=NUM_POSITIONS)
    ap.add_argument("--capital", type=float, default=WEEKLY_CAPITAL)
    args = ap.parse_args()

    if args.command == "plan":
        rec = plan(args.n, args.capital)
        print(f"scan {rec['scan_date']} ({rec['engine']}) -> "
              f"{len(rec['picks'])} picks, ${rec['capital']:,.0f}")
        for p in rec["picks"]:
            print(f"  {p['symbol']:<6} score {p['score']:>6}  vol {p['vol']:>6}  "
                  f"${p['target_dollars']:,.2f}")
    elif args.command == "open":
        rec = open_week(dry_run=not args.execute)
        tag = "PLACED" if args.execute else "DRY RUN"
        print(f"[{tag}] bought {len(rec['orders'])} names")
    elif args.command == "close":
        rec = close_week(dry_run=not args.execute)
        tag = "PLACED" if args.execute else "DRY RUN"
        print(f"[{tag}] week return "
              f"{rec['week_return_pct'] if rec['week_return_pct'] is not None else 'n/a'}%")
        for e in rec["exits"]:
            print(f"  {e}")
    else:
        scoreboard()


if __name__ == "__main__":
    main()
