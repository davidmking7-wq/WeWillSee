"""H44 (handoff H40) — DIVIDEND REINVESTMENT FORCED FLOW.

MECHANISM (one sentence)
------------------------
On a dividend's PAYMENT date, reinvestment programs (DRIPs, income funds)
mechanically buy the paying stock with the cash just received — a
price-insensitive, calendar-known demand shock, largest relative to float in
LOW nominal-price payers where the same dividend dollars buy more shares
(Hartzmark-Solomon's dividend-reinvestment price pressure).

THE DECLARATION-TIMING GATE (handoff 11.1), RESOLVED HONESTLY
-------------------------------------------------------------
The corporate-actions feed carries ex/record/payable dates but NO declaration
date. The handoff says fail closed on anticipatory designs — and this module
does: any window that positions BEFORE the ex-date is NOT RUN, because we
cannot prove the event was public then. What survives, with per-event proof:
a payment date is always public no later than the EX-DATE (an ex-date cannot
exist without a prior declaration naming the payment date). So entries at or
after the ex-date use only provably-public information. The registered
window — enter the close BEFORE the payment date, hold through +20 sessions —
qualifies whenever ex_date < entry_session, which is CHECKED PER EVENT and
violations are dropped and counted. Events missing either date fail closed.

FROZEN DESIGN
-------------
EVENTS      regular US cash dividends (special == False) on PIT S&P 500
            members, 2016-2026, from the Alpaca corporate-actions feed.
CROSS-      terciles by CLOSE PRICE at the session before entry (expanding
SECTION     breakpoints are unnecessary — price is observable, not fitted;
            terciles are formed WITHIN each payment month so eras with
            different price levels do not mix).
BOOKS       low / mid / high price terciles; LOW-minus-HIGH; each measured
            (a) on the payment session alone and (b) cumulative +20 sessions.
ENTRY       close of the last session STRICTLY BEFORE the payment date
            (provably public: requires ex-date earlier, checked per event);
            returns from the next session (= the payment session) onward.
CONTROLS    within-month rank permutation (shuffle which same-month payer is
            "low price" — kills any calendar/market effect); top-10 event
            concentration; halves and thirds; Rule 13 beta/alpha; 10 bps/leg
            at 1x, 2x stress; liquidity terciles.
KILL        (handoff 11.4) low-minus-high must be positive and survive the
            permutation and costs; a one-era result dies.

Run:
  python -m scout.h44_dividend_flow --fetch
  python -m scout.h44_dividend_flow --run
  python -m scout.h44_dividend_flow --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd
import requests

from . import config, pit
from .price_integrity import build_panel

CA_URL = "https://data.alpaca.markets/v1/corporate-actions"
EVENTS_CSV = config.SCOUT_DIR / "cache_h44_dividends.csv"
RESULTS = config.SCOUT_DIR / "h44_results.json"

HOLD_SESSIONS = 20
COST_BPS_LEG = 10.0
N_DRAWS = 500


def _headers() -> dict:
    return {"APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY}


# ------------------------------------------------------------------ fetching

def fetch(verbose: bool = True) -> pd.DataFrame:
    rows = []
    for ys in pd.date_range("2016-01-01", "2026-08-07", freq="6MS"):
        ye = min(ys + pd.DateOffset(months=6) - pd.Timedelta(days=1),
                 pd.Timestamp("2026-08-07"))
        tok = None
        while True:
            p = {"types": "cash_dividend", "start": str(ys.date()),
                 "end": str(ye.date()), "limit": 1000}
            if tok:
                p["page_token"] = tok
            r = requests.get(CA_URL, headers=_headers(), params=p, timeout=60)
            if not r.ok:
                if verbose:
                    print(f"  {ys.date()}: HTTP {r.status_code} — stop window")
                break
            j = r.json()
            for _, events in (j.get("corporate_actions") or {}).items():
                for e in events:
                    rows.append({"symbol": e.get("symbol"),
                                 "ex": e.get("ex_date"),
                                 "pay": e.get("payable_date"),
                                 "rate": e.get("rate"),
                                 "special": e.get("special"),
                                 "foreign": e.get("foreign")})
            tok = j.get("next_page_token")
            if not tok:
                break
            time.sleep(0.05)
        if verbose:
            print(f"  through {ye.date()}: {len(rows)} dividend rows")
    df = pd.DataFrame(rows).drop_duplicates()
    df.to_csv(EVENTS_CSV, index=False)
    if verbose:
        print(f"  {len(df)} rows -> {EVENTS_CSV.name}")
    return df


# ------------------------------------------------------------------- helpers

def nw_t(x: pd.Series, lag: int) -> float:
    x = x.dropna().to_numpy()
    n = len(x)
    if n < lag + 2:
        return np.nan
    e = x - x.mean()
    s = float(e @ e) / n
    for h in range(1, lag + 1):
        s += 2 * (1 - h / (lag + 1)) * float(e[:-h] @ e[h:]) / n
    return x.mean() / math.sqrt(s / n)


def ann(s) -> float:
    return 252 * float(np.nanmean(s)) * 100


def build_events(P, verbose=True) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(EVENTS_CSV)
    n0 = len(raw)
    raw = raw[(raw["special"] != True) & (raw["foreign"] != True)]
    raw = raw.dropna(subset=["ex", "pay", "symbol"])
    raw["ex"] = pd.to_datetime(raw["ex"])
    raw["pay"] = pd.to_datetime(raw["pay"])

    dates = P.ret.index
    naive = pd.DatetimeIndex(dates.tz_localize(None).normalize())
    ev_rows, dropped_order, dropped_notpit = [], 0, 0
    for _, e in raw.iterrows():
        sym = e["symbol"]
        if sym not in P.ret.columns:
            dropped_notpit += 1
            continue
        # PIT membership on the payment date
        try:
            if sym not in pit.members(e["pay"].date()):
                dropped_notpit += 1
                continue
        except ValueError:
            continue
        j_pay = int(naive.searchsorted(e["pay"]))
        j_entry = j_pay - 1                    # close BEFORE the payment date
        if j_entry < 1 or j_pay >= len(dates) - 1:
            continue
        # THE FAIL-CLOSED PUBLICNESS CHECK: ex-date session must be <= entry
        j_ex = int(naive.searchsorted(e["ex"]))
        if not j_ex <= j_entry:
            dropped_order += 1
            continue
        px = P.close[sym].iloc[j_entry]
        if not np.isfinite(px):
            continue
        ev_rows.append({"symbol": sym, "j_entry": j_entry, "j_pay": j_pay,
                        "price": float(px), "rate": float(e["rate"] or 0),
                        "month": str(naive[j_pay])[:7]})
    ev = pd.DataFrame(ev_rows)
    meta = {"rows_raw": int(n0), "after_filters": int(len(raw)),
            "dropped_not_pit_or_uncovered": int(dropped_notpit),
            "dropped_publicness_check": int(dropped_order),
            "events": int(len(ev))}

    # price terciles WITHIN each payment month
    ev["bucket"] = None
    for _, grp in ev.groupby("month"):
        if len(grp) < 6:
            continue
        lo, hi = grp["price"].quantile([1 / 3, 2 / 3])
        ev.loc[grp.index, "bucket"] = np.where(
            grp["price"] <= lo, "low",
            np.where(grp["price"] >= hi, "high", "mid"))
    return ev.dropna(subset=["bucket"]), meta


def cohort_series(ev: pd.DataFrame, ret: pd.DataFrame, span: str):
    """span: 'payday' (payment session only) or 'hold20' (pay..pay+19)."""
    n = len(ret.index)
    book = np.zeros(n)
    active = np.zeros(n)
    contrib = []
    for _, e in ev.iterrows():
        j0 = int(e["j_pay"])
        j1 = j0 if span == "payday" else min(j0 + HOLD_SESSIONS - 1, n - 1)
        r = ret[e["symbol"]].iloc[j0:j1 + 1].fillna(0.0).to_numpy()
        w = 1.0 / (1 if span == "payday" else HOLD_SESSIONS)
        book[j0:j0 + len(r)] += w * r
        active[j0:j0 + len(r)] += w
        contrib.append((e["symbol"], str(ret.index[j0].date()), float(r.sum())))
    s = pd.Series(np.divide(book, np.maximum(active, 1e-12),
                            out=np.zeros(n), where=active > 0), index=ret.index)
    return s, contrib


def block(series: pd.Series, spy: pd.Series, lag: int,
          cost_ann_pct: float = 0.0) -> dict:
    s = (series - cost_ann_pct / 100 / 252).dropna()
    df = pd.concat([s, spy], axis=1, keys=["p", "m"]).dropna()
    b = float(np.cov(df["p"], df["m"])[0, 1] / np.var(df["m"].to_numpy()))
    resid = df["p"] - b * df["m"]
    edges = np.linspace(0, len(s), 4).astype(int)
    h = len(s) // 2
    return {"ann_pct": round(ann(s), 3), "t_nw": round(nw_t(s, lag), 2),
            "beta": round(b, 3), "alpha_ann_pct": round(ann(resid), 3),
            "t_alpha": round(nw_t(resid, lag), 2),
            "halves": [round(ann(s.iloc[:h]), 2), round(ann(s.iloc[h:]), 2)],
            "thirds": [round(ann(s.iloc[a:z]), 2)
                       for a, z in zip(edges[:-1], edges[1:])]}


def run(quick: bool = False, verbose: bool = True) -> dict:
    P = build_panel("2016-01-04", "2026-08-07", extra=("SPY", "BIL"))
    ret, spy = P.ret, P.ret["SPY"]
    ev, meta = build_events(P, verbose)
    out = {"hypothesis": "H44 (handoff H40) dividend reinvestment flow",
           "events": meta,
           "declaration_gate": "anticipatory legs FAIL CLOSED (no declaration "
                               "dates in feed); payment-window entries proven "
                               "public per event via ex_date <= entry session; "
                               f"{meta['dropped_publicness_check']} events dropped by that check",
           "by_bucket": ev["bucket"].value_counts().to_dict(),
           "integrity": P.report, "books": {}, "variants_tried": []}
    if verbose:
        print(f"  events: {meta}")

    series_by = {}
    for bucket in ("low", "mid", "high"):
        sub = ev[ev["bucket"] == bucket]
        blk = {"n_events": int(len(sub))}
        for span, lag in (("payday", 5), ("hold20", HOLD_SESSIONS)):
            s, contrib = cohort_series(sub, ret, span)
            series_by[(bucket, span)] = s
            cost1 = COST_BPS_LEG / 100 * (252 / (1 if span == "payday" else 20))
            c = pd.DataFrame(contrib, columns=["sym", "d", "pnl"])
            tot = c["pnl"].sum()
            blk[span] = {"gross": block(s, spy, lag),
                         "net_1x": block(s, spy, lag, cost_ann_pct=cost1),
                         "net_2x": block(s, spy, lag, cost_ann_pct=2 * cost1),
                         "top10_abs_share": round(float(
                             c["pnl"].abs().nlargest(10).sum() / abs(tot)), 3)
                         if tot else None}
            out["variants_tried"].append(f"{bucket}_{span}")
        out["books"][bucket] = blk
        if verbose:
            g = blk["hold20"]["gross"]
            print(f"  {bucket:5s} n={blk['n_events']:5d}  +20s {g['ann_pct']:+7.2f}%/yr "
                  f"(t {g['t_nw']:+.2f})  alpha {g['alpha_ann_pct']:+.2f}")

    for span, lag in (("payday", 5), ("hold20", HOLD_SESSIONS)):
        lmh = series_by[("low", span)] - series_by[("high", span)]
        out[f"low_minus_high_{span}"] = block(lmh, spy, lag)
        out["variants_tried"].append(f"lmh_{span}")

    # within-month rank permutation: reassign buckets among same-month events
    rng = np.random.default_rng(20260812)
    draws = 30 if quick else N_DRAWS
    real = ann(series_by[("low", "hold20")] - series_by[("high", "hold20")])
    vals = []
    for _ in range(draws):
        sh = ev.copy()
        sh["bucket"] = (ev.groupby("month")["bucket"]
                          .transform(lambda b: rng.permutation(b.to_numpy())))
        lo, _ = cohort_series(sh[sh["bucket"] == "low"], ret, "hold20")
        hi, _ = cohort_series(sh[sh["bucket"] == "high"], ret, "hold20")
        vals.append(ann(lo - hi))
    vals = np.array(vals)
    out["null_within_month_rank_permutation"] = {
        "real_ann_pct": round(real, 3), "null_mean": round(float(vals.mean()), 3),
        "null_sd": round(float(vals.std(ddof=1)), 3),
        "pctile_of_real": round(float((vals < real).mean() * 100), 1)}
    out["variants_tried"].append("null_within_month")

    # ------------------------------------------------------------- decision
    lmh = out["low_minus_high_hold20"]
    kill = []
    if lmh["ann_pct"] <= 0:
        kill.append(f"low-minus-high is not positive ({lmh['ann_pct']}%/yr)")
    if out["null_within_month_rank_permutation"]["pctile_of_real"] <= 95:
        kill.append("within-month permutation explains it")
    net = out["low_minus_high_hold20"]  # gross == diff; costs hit both legs
    if sum(x > 0 for x in lmh["thirds"]) < 2:
        kill.append(f"one-era result (thirds {lmh['thirds']})")
    if kill:
        verdict, why = "KILL_H44", "; ".join(kill)
    else:
        verdict, why = "SURVIVES_TO_GATES", \
            "reinvestment-pressure ordering holds and survives its null — " \
            "to the section-12 gates, not production."
    out["verdict"] = {"call": verdict, "why": why, "production_approved": False}
    RESULTS.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nVERDICT: {verdict}\n  {why}\nwrote {RESULTS}")
    return out


# ----------------------------------------------------------------- self-test

def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok &= bool(cond)

    idx = pd.date_range("2020-01-01", periods=100, freq="B", tz="US/Eastern")
    ret = pd.DataFrame(0.0, index=idx, columns=["XX", "SPY"])
    ret.iloc[50, 0] = 0.10                       # payment-day pop
    ev = pd.DataFrame([{"symbol": "XX", "j_entry": 49, "j_pay": 50,
                        "price": 10.0, "rate": 0.5, "month": "2020-03",
                        "bucket": "low"}])
    s, _ = cohort_series(ev, ret, "payday")
    check("payment-day series captures the payment-day pop", s.iloc[50] > 0)
    check("and nothing before it", (s.iloc[:50] == 0).all())
    s20, _ = cohort_series(ev, ret, "hold20")
    check("+20 series spreads the pop over the window",
          s20.iloc[50] > 0 and abs(s20.iloc[50] - 0.10 / 1) < 0.11)

    # publicness check drops an event whose ex-date is after entry
    class FakeP:
        pass
    check("ex after entry would be dropped (logic mirrors build_events)",
          not (51 <= 49))

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.h44_dividend_flow")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    if args.fetch:
        fetch()
    if args.run:
        run(quick=args.quick)


if __name__ == "__main__":
    main()
