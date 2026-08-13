"""Data-integrity audit: are the prices this repo trusts actually clean?

WHY THIS EXISTS
---------------
Every result in this repository -- ten years of backtests, four engine
versions, three research rounds -- rests on one assumption nobody had ever
checked: that `scout/data.py`'s Alpaca bars, fetched with `adjustment=all`,
are actually adjusted.

They are not, always. Audited 2026-08-09 over the S&P 1500:

    198 splits checked, 10 UNADJUSTED (5.1%)
    SIRI  2024-09-10  1:10 reverse split -> fake  +925.6% one-day return
    DEA   2025-04-28                     -> fake  +155.6%
    CNX   2017-11-29                     -> fake   -89.6%
    FNF   2017-10-02                     -> fake   -77.8%
    AAPL  2020-08-31  4:1 forward split  -> fake   -74.2%
    ...plus TRN, AA, EQT, AWI, SNEX

    and 146 further |1-day| > 50% moves NOT explained by any split in
    Alpaca's own corporate-actions feed -- spin-offs (RTX -71.0% at the
    Carrier/Otis separation, APTV -71.6% at the Delphi spin) and reused
    tickers splicing two unrelated companies' histories.

A fake +925% return makes a stock the best momentum name in the universe
for a year. A fake -74% distorts volatility, 52-week-high proximity and
every moving average for as long as the lookback window is.

WHAT THE AUDIT FOUND ABOUT IMPACT -- and this is the part that matters
---------------------------------------------------------------------
Almost nothing reached the picks. Re-running `signals.composite_at` across
114 month-end scan dates, 1,710 top-15 slots:

    slots filled by a name within 1 year AFTER a fake +45% move:  10 (0.58%)
    slots filled by a name within 1 year AFTER a fake -45% move:   0 (0.00%)

and several of those ten are probably genuine 45% moves (biotech does that)
rather than corruption.

The reason is the vetoes. `config.VETO_RET1M_HI` (+25%) and
`VETO_RET1M_LO` (-15%), plus the top-vol-decile and MAX-effect vetoes,
exclude any name that just printed an enormous move -- which is exactly what
a corrupted bar looks like. The gates were adopted from the reversal and
lottery-effect literature for entirely different reasons and blocked this by
accident. **No previously reported result needs retracting.**

WHAT IS NOT COVERED
-------------------
This audit uses TODAY'S S&P 1500 membership. The point-in-time backtests
(`--universe pit500`) deliberately include delisted names, and those are
precisely the ones most likely to carry bad final prints, reused tickers and
unadjusted terminal corporate actions -- and precisely the ones no audit can
cross-check, because the corporate-actions feed thins out for dead symbols.
Treat pit500 results as carrying an extra, unquantified data-quality
discount on top of the survivorship correction they already document.

Run:
  python -m scout.data_audit                 # splits + orphan moves + impact
  python -m scout.data_audit --no-impact     # just the data checks (faster)
  python -m scout.data_audit --universe-file scout/universe.csv
"""
from __future__ import annotations

import argparse
import json

import pandas as pd
import requests

from . import config, data

CA_URL = "https://data.alpaca.markets/v1/corporate-actions"
BIG_MOVE = 0.45          # |1-day return| beyond which a bar is implausible
SPLIT_BAD = 0.35         # |1-day return| at a split ex-date implying no adjustment
CHUNK = 100


def _headers() -> dict:
    return {"APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY}


def fetch_splits(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Alpaca's own corporate-actions feed: the ground truth we check against.

    Note the asymmetry that makes this audit worth running at all -- the
    corporate-actions endpoint knows about these splits, and the bars
    endpoint does not always apply them. The two disagree with each other
    inside the same vendor."""
    out = []
    for i in range(0, len(symbols), CHUNK):
        chunk, token = symbols[i:i + CHUNK], None
        while True:
            params = {"symbols": ",".join(chunk),
                      "types": "forward_split,reverse_split",
                      "start": start, "end": end, "limit": 1000}
            if token:
                params["page_token"] = token
            r = requests.get(CA_URL, headers=_headers(), params=params, timeout=60)
            if not r.ok:
                print(f"  corporate-actions chunk {i // CHUNK + 1} failed: {r.status_code}")
                break
            body = r.json()
            actions = body.get("corporate_actions", {})
            for kind in ("forward_splits", "reverse_splits"):
                for a in actions.get(kind, []):
                    out.append({"symbol": a.get("symbol"), "ex_date": a.get("ex_date"),
                                "old_rate": a.get("old_rate"), "new_rate": a.get("new_rate"),
                                "kind": kind})
            token = body.get("next_page_token")
            if not token:
                break
    return pd.DataFrame(out).drop_duplicates()


def check_splits(close: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    """For each split, look at the first return on/after the ex-date. An
    adjusted series shows an ordinary move there; an unadjusted one shows
    the split ratio."""
    ret = close.pct_change()
    rows = []
    for _, s in splits.iterrows():
        sym = s["symbol"]
        if sym not in ret.columns:
            continue
        try:
            ex = pd.Timestamp(s["ex_date"], tz=ret.index.tz)
        except Exception:
            continue
        idx = ret.index[(ret.index >= ex) & (ret.index <= ex + pd.Timedelta(days=5))]
        if not len(idx):
            continue
        r = ret.loc[idx[0], sym]
        if pd.isna(r):
            continue
        try:
            factor = float(s["new_rate"]) / float(s["old_rate"])
        except Exception:
            factor = float("nan")
        rows.append({"symbol": sym, "ex_date": str(ex.date()), "factor": round(factor, 4),
                     "ret_pct": round(100 * float(r), 1),
                     "unadjusted": bool(abs(float(r)) > SPLIT_BAD)})
    return pd.DataFrame(rows)


def orphan_moves(close: pd.DataFrame, splits: pd.DataFrame,
                 threshold: float = 0.50) -> pd.DataFrame:
    """Implausible one-day moves NOT near any split in the feed.

    These are the ones with no paper trail: spin-offs (the parent drops by
    the value of the child and no split is recorded), and reused tickers
    where two unrelated companies' prices are spliced into one series."""
    ret = close.pct_change()
    known = set()
    for _, s in splits.iterrows():
        try:
            ex = pd.Timestamp(s["ex_date"])
        except Exception:
            continue
        for k in range(-6, 2):
            known.add((s["symbol"], str((ex + pd.Timedelta(days=k)).date())))
    stacked = ret.stack()
    big = stacked[stacked.abs() > threshold]
    rows = [{"date": str(ts.date()), "symbol": sym, "ret_pct": round(100 * float(v), 1)}
            for (ts, sym), v in big.items() if (sym, str(ts.date())) not in known]
    return pd.DataFrame(rows).sort_values("ret_pct") if rows else pd.DataFrame()


def pick_impact(close: pd.DataFrame, threshold: float = BIG_MOVE,
                stride: int = 21) -> dict:
    """Did any of this reach the picks? Re-score the universe at month-ends
    and count top-N slots taken by a name within a year after a corrupt-looking
    move.

    Volume is stubbed high because the liquidity gate is not what this
    measures, and the open frame is stubbed to close because the gap feature
    carries no score weight in v4/v5. Both are documented approximations
    that make the test STRICTER (nothing is excluded for liquidity), not
    looser."""
    from . import signals
    ret = close.pct_change()
    stacked = ret.stack()
    events: dict[str, list] = {}
    for (ts, sym), v in stacked[stacked.abs() > threshold].items():
        events.setdefault(sym, []).append((ts, 1 if v > 0 else -1))

    frames = signals.feature_frames(close.copy(), close,
                                    pd.DataFrame(1e9, index=close.index,
                                                 columns=close.columns))
    idx = close.index
    dates = [idx[i] for i in range(270, len(idx), stride)]
    slots = pos = neg = 0
    examples = []
    for dt in dates:
        df = signals.composite_at(frames, dt)
        if df.empty:
            continue
        top = list(df.index[:config.TOP_CANDIDATES])
        slots += len(top)
        for sym in top:
            for ev, sign in events.get(sym, []):
                if 0 < (dt - ev).days <= 365:
                    if sign > 0:
                        pos += 1
                        examples.append((str(dt.date()), sym, str(ev.date())))
                    else:
                        neg += 1
                    break
    return {"scan_dates": len(dates), "slots": slots,
            "after_fake_up": pos, "after_fake_down": neg,
            "pct_contaminated": round(100 * (pos + neg) / max(slots, 1), 2),
            "examples": examples[:20]}


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.data_audit")
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2026-08-08")
    ap.add_argument("--no-impact", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.50)
    args = ap.parse_args()

    u = pd.read_csv(config.UNIVERSE_CSV)
    col = next(c for c in u.columns if c.lower() in ("symbol", "ticker"))
    symbols = sorted(u[col].astype(str).str.strip().unique().tolist())
    print(f"universe: {len(symbols)} symbols")

    print("fetching corporate actions...")
    splits = fetch_splits(symbols, args.start, args.end)
    print(f"  {len(splits)} splits {args.start}..{args.end}")

    print("fetching daily bars (this is the slow part)...")
    close = data.daily_ohlcv(symbols, days=int(10.7 * 365))["close"].sort_index()
    print(f"  {close.shape[1]} symbols x {close.shape[0]} sessions "
          f"({close.index[0].date()}..{close.index[-1].date()})")

    checked = check_splits(close, splits)
    bad = checked[checked["unadjusted"]].sort_values("ret_pct")
    print(f"\n=== SPLIT ADJUSTMENT ===")
    print(f"checkable: {len(checked)}   UNADJUSTED: {len(bad)} "
          f"({100 * len(bad) / max(len(checked), 1):.1f}%)")
    if len(bad):
        print(bad[["symbol", "ex_date", "factor", "ret_pct"]].to_string(index=False))

    orphans = orphan_moves(close, splits, args.threshold)
    print(f"\n=== ORPHAN MOVES (|1d| > {args.threshold:.0%}, no split on file) ===")
    print(f"count: {len(orphans)}  "
          "(spin-offs and reused tickers; Alpaca records no action for these)")
    if len(orphans):
        print(orphans.head(15).to_string(index=False))

    out = {"universe": len(symbols), "splits": len(splits),
           "unadjusted": bad.to_dict("records"), "orphan_count": int(len(orphans)),
           "orphans": orphans.head(60).to_dict("records") if len(orphans) else []}

    if not args.no_impact:
        print("\n=== IMPACT ON PICKS ===")
        imp = pick_impact(close)
        print(f"scan dates {imp['scan_dates']}, top-{config.TOP_CANDIDATES} slots "
              f"{imp['slots']}")
        print(f"  after a fake UP move (1yr):   {imp['after_fake_up']}")
        print(f"  after a fake DOWN move (1yr): {imp['after_fake_down']}")
        print(f"  contaminated: {imp['pct_contaminated']}% of slots")
        print("\nThe vetoes (ret1m outside -15%..+25%, top-vol decile, MAX effect) "
              "exclude\nnames that just printed an enormous move -- which is what a "
              "corrupted bar\nlooks like. They were adopted for other reasons and "
              "block this by accident.")
        out["impact"] = imp

    path = config.SCOUT_DIR / "data_audit.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {path.name}")


if __name__ == "__main__":
    main()
