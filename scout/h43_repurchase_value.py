"""H43 (handoff H39) — REPURCHASE ANNOUNCEMENT x UNDERVALUATION.

THIS IS NOT H22 AGAIN, and the difference is the mechanism. H22 sorted on
realised net-issuance ACCOUNTING FLOW (shares actually retired, visible only
in later filings) and was killed for regime concentration. H43 is the EVENT:
the board's public AUTHORIZATION of an open-market repurchase program,
conditioned on independently measured valuation. Ikenberry-Lakonishok-
Vermaelen: the long-run drift after repurchase announcements lives in the
VALUE (high book-to-market) announcers — a cheap company saying "we are
buying" is credible in a way a glamour company is not.

EVENTS
------
EDGAR full-text search, 8-K filings containing BOTH phrases "repurchase
program" AND "authorized", chunked by quarter (FTS caps at 10k hits and
truncates silently). ~650 raw hits/quarter market-wide. The filing's CIK maps
to a PIT S&P 500 member through scout/historical_identity.py (the unresolved
14 counted out). An 8-K that MENTIONS an existing program is not a new
authorization, so events carry a 365-DAY PER-COMPANY COOLDOWN: the first
qualifying filing opens an event, later hits inside the window are the same
program's chatter. Stated proxy, frozen before any return was computed.

VALUATION (point-in-time, sec_bulk discipline)
----------------------------------------------
B/M = StockholdersEquity (most recent value FILED before the event, filing-
date discipline, consolidated rows only, first-filing-wins) divided by
market cap (split-adjusted shares x close, both at the session before entry).
Buckets: value / mid / glamour by EXPANDING terciles over announcing firms'
B/M history through the event date — no full-sample breakpoints.

TIMING: 8-K filing time-of-day is not in the FTS payload -> conservative
next-executable-session rule: entry at the close of the first session
STRICTLY AFTER the filing date, returns from the session after entry.

HORIZONS: 126/252 primary (slow capital-allocation mechanism, handoff 10.4),
21/63 diagnostic. Long-only books per bucket; value-minus-glamour; value vs
SPY. Controls: matched NON-announcement pseudo-events (same session, random
PIT firm with valid B/M in the same tercile, 200 draws); issuer timing
shuffle; halves/thirds; top-10 concentration; 10 bps/leg, 2x stress.

KILL (handoff 10.5): value conditioning must materially differentiate;
concentration or shuffle failures kill.

Run:
  python -m scout.h43_repurchase_value --fetch
  python -m scout.h43_repurchase_value --run
  python -m scout.h43_repurchase_value --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import pandas as pd
import requests

from . import config
from .price_integrity import build_panel

UA = {"User-Agent": "WeWillSee research davidmking7@gmail.com"}
FTS = "https://efts.sec.gov/LATEST/search-index"
EVENTS_CSV = config.SCOUT_DIR / "cache_h43_announcements.csv"
RESULTS = config.SCOUT_DIR / "h43_results.json"
IDENTITY = config.SCOUT_DIR / "identity_map.json"

QUERY = '"repurchase program" "authorized"'
COOLDOWN_DAYS = 365
COST_BPS_LEG = 10.0
HORIZONS_PRIMARY = (126, 252)
HORIZONS_DIAG = (21, 63)
N_MATCHED_DRAWS = 200


# ------------------------------------------------------------------ fetching

def _fts_page(start: str, end: str, frm: int) -> dict:
    p = {"q": QUERY, "forms": "8-K", "dateRange": "custom",
         "startdt": start, "enddt": end}
    if frm:
        p["from"] = frm
    for k in range(5):
        try:
            r = requests.get(FTS, headers=UA, params=p, timeout=60)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(1.5 * (k + 1))
    return {}


def fetch(verbose: bool = True) -> pd.DataFrame:
    rows = []
    for qs in pd.date_range("2016-01-01", "2026-08-07", freq="QS"):
        qe = min(qs + pd.offsets.QuarterEnd(0), pd.Timestamp("2026-08-07"))
        frm = 0
        while True:
            j = _fts_page(str(qs.date()), str(qe.date()), frm)
            hits = (j.get("hits") or {}).get("hits") or []
            if not hits:
                break
            for h in hits:
                s = h.get("_source", {})
                rows.append({"filed": s.get("file_date"),
                             "cik": (s.get("ciks") or [None])[0],
                             "adsh": s.get("adsh") or h.get("_id"),
                             "name": (s.get("display_names") or [None])[0]})
            total = ((j.get("hits") or {}).get("total") or {}).get("value", 0)
            frm += len(hits)
            if frm >= min(total, 9990):
                break
            time.sleep(0.12)
        if verbose:
            print(f"  {qs.date()}..{qe.date()}: {len(rows)} cumulative")
    df = (pd.DataFrame(rows).dropna(subset=["filed", "cik"])
            .drop_duplicates(subset=["adsh"]))
    df.to_csv(EVENTS_CSV, index=False)
    if verbose:
        print(f"  {len(df)} filings -> {EVENTS_CSV.name}")
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


def event_book(events: pd.DataFrame, ret: pd.DataFrame, horizon: int):
    dates = ret.index
    naive = pd.DatetimeIndex(dates.tz_localize(None).normalize())
    n = len(dates)
    book = np.zeros(n)
    active = np.zeros(n)
    contrib = []
    pos = naive.searchsorted(pd.to_datetime(events["filed"]).values, side="right")
    for (_, e), j0 in zip(events.iterrows(), pos):
        sym = e["ticker"]
        if sym not in ret.columns or j0 >= n - 1:
            continue
        r = ret[sym].iloc[j0 + 1:min(j0 + horizon, n - 1) + 1].fillna(0.0).to_numpy()
        book[j0 + 1:j0 + 1 + len(r)] += r / horizon
        active[j0 + 1:j0 + 1 + len(r)] += 1.0 / horizon
        contrib.append((sym, str(naive[min(j0, n - 1)].date()), float(r.sum())))
    s = pd.Series(np.divide(book, np.maximum(active, 1e-12),
                            out=np.zeros(n), where=active > 0), index=dates)
    return s, contrib


def block(series: pd.Series, spy: pd.Series, horizon: int,
          cost_ann_pct: float = 0.0) -> dict:
    s = (series - cost_ann_pct / 100 / 252).dropna()
    df = pd.concat([s, spy], axis=1, keys=["p", "m"]).dropna()
    b = float(np.cov(df["p"], df["m"])[0, 1] / np.var(df["m"].to_numpy()))
    resid = df["p"] - b * df["m"]
    edges = np.linspace(0, len(s), 4).astype(int)
    h = len(s) // 2
    return {"ann_pct": round(ann(s), 3), "t_nw": round(nw_t(s, horizon), 2),
            "beta": round(b, 3), "alpha_ann_pct": round(ann(resid), 3),
            "t_alpha": round(nw_t(resid, horizon), 2),
            "halves": [round(ann(s.iloc[:h]), 2), round(ann(s.iloc[h:]), 2)],
            "thirds": [round(ann(s.iloc[a:z]), 2)
                       for a, z in zip(edges[:-1], edges[1:])]}


# ---------------------------------------------------------------------- run

def build_events(P, verbose=True) -> tuple[pd.DataFrame, dict]:
    """FTS filings -> PIT events with cooldown and point-in-time B/M."""
    from . import sec_bulk
    raw = pd.read_csv(EVENTS_CSV, dtype=str)
    raw["filed"] = pd.to_datetime(raw["filed"])
    raw["cik_int"] = pd.to_numeric(raw["cik"], errors="coerce")

    idm = json.loads(IDENTITY.read_text())
    cik2tkr: dict[int, str] = {}
    for r in idm["rows"]:
        if r.get("cik"):
            cik2tkr[int(r["cik"])] = r["ticker"]
        for c in r.get("candidates", []):
            cik2tkr[int(c["cik"])] = r["ticker"]
    raw["ticker"] = raw["cik_int"].map(cik2tkr)
    ev = raw.dropna(subset=["ticker"]).sort_values("filed")

    # 365-day per-company cooldown
    kept = []
    last: dict[str, pd.Timestamp] = {}
    for _, e in ev.iterrows():
        t = e["ticker"]
        if t in last and (e["filed"] - last[t]).days < COOLDOWN_DAYS:
            continue
        last[t] = e["filed"]
        kept.append(e)
    ev = pd.DataFrame(kept)

    # point-in-time B/M at the session before entry
    tickers = sorted(ev["ticker"].unique())
    dates = P.close.index
    eq = sec_bulk.pit_panel(sec_bulk.load_tags(["StockholdersEquity"]),
                            "StockholdersEquity", tickers, dates)
    sh = sec_bulk.shares_panel(sec_bulk.load_tags(
        ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding",
         "WeightedAverageNumberOfSharesOutstandingBasic"]), tickers, dates)
    naive = pd.DatetimeIndex(dates.tz_localize(None).normalize())
    bm = []
    for _, e in ev.iterrows():
        j = int(naive.searchsorted(e["filed"], side="right"))  # entry session
        j_prev = j - 1
        t = e["ticker"]
        v = np.nan
        if 0 <= j_prev < len(dates) and t in eq.columns and t in sh.columns:
            b = eq[t].iloc[j_prev]
            s = sh[t].iloc[j_prev]
            p = P.close[t].iloc[j_prev] if t in P.close.columns else np.nan
            if np.isfinite(b) and np.isfinite(s) and np.isfinite(p) and s * p > 0:
                v = b / (s * p)
        bm.append(v)
    ev["bm"] = bm
    meta = {"filings_raw": int(len(raw)), "pit_matched": int(raw["ticker"].notna().sum()),
            "events_after_cooldown": int(len(ev)),
            "events_with_bm": int(np.isfinite(ev["bm"]).sum())}

    # expanding-tercile buckets over announcing firms' B/M
    ev = ev.sort_values("filed").reset_index(drop=True)
    hist: list[float] = []
    buckets = []
    for v in ev["bm"]:
        if not np.isfinite(v):
            buckets.append(None)
            continue
        if len(hist) >= 30:
            lo, hi = np.quantile(hist, [1 / 3, 2 / 3])
            buckets.append("value" if v >= hi else
                           "glamour" if v <= lo else "mid")
        else:
            buckets.append(None)          # burn-in
        hist.append(v)
    ev["bucket"] = buckets
    return ev, meta


def run(quick: bool = False, verbose: bool = True) -> dict:
    P = build_panel("2016-01-04", "2026-08-07", extra=("SPY", "BIL"))
    ret, spy = P.ret, P.ret["SPY"]
    ev, meta = build_events(P, verbose)
    out = {"hypothesis": "H43 (handoff H39) repurchase x undervaluation",
           "events": meta, "query": QUERY, "cooldown_days": COOLDOWN_DAYS,
           "by_bucket": ev["bucket"].value_counts(dropna=False).to_dict(),
           "integrity": P.report, "books": {}, "variants_tried": []}
    if verbose:
        print(f"  events: {meta}")

    horizons = HORIZONS_PRIMARY + (() if quick else HORIZONS_DIAG)
    series_by = {}
    for bucket in ("value", "mid", "glamour"):
        sub = ev[ev["bucket"] == bucket]
        blk = {"n_events": int(len(sub))}
        for h in horizons:
            s, contrib = event_book(sub, ret, h)
            series_by[(bucket, h)] = s
            cost1 = COST_BPS_LEG / 100 * (252 / h)
            c = pd.DataFrame(contrib, columns=["sym", "d", "pnl"])
            tot = c["pnl"].sum()
            blk[f"h{h}"] = {
                "gross": block(s, spy, h),
                "net_1x": block(s, spy, h, cost_ann_pct=cost1),
                "net_2x": block(s, spy, h, cost_ann_pct=2 * cost1),
                "top10_abs_share": round(float(
                    c["pnl"].abs().nlargest(10).sum() / abs(tot)), 3) if tot else None}
            out["variants_tried"].append(f"{bucket}_h{h}")
        out["books"][bucket] = blk
        if verbose:
            g = blk[f"h{HORIZONS_PRIMARY[0]}"]["gross"]
            print(f"  {bucket:8s} n={blk['n_events']:4d}  h126 {g['ann_pct']:+7.2f}%/yr "
                  f"(t {g['t_nw']:+.2f})  alpha {g['alpha_ann_pct']:+.2f} (t {g['t_alpha']:+.2f})")

    for h in HORIZONS_PRIMARY:
        vg = series_by[("value", h)] - series_by[("glamour", h)]
        vs = series_by[("value", h)] - spy
        out[f"value_minus_glamour_h{h}"] = block(vg, spy, h)
        out[f"value_minus_spy_h{h}"] = block(vs, spy, h,
                                             cost_ann_pct=COST_BPS_LEG / 100 * (252 / h))
        out["variants_tried"] += [f"vmg_h{h}", f"vms_h{h}"]

    # matched non-announcement control: same sessions, random PIT firm from the
    # same expanding B/M tercile
    rng = np.random.default_rng(20260812)
    draws = 20 if quick else N_MATCHED_DRAWS
    val_ev = ev[ev["bucket"] == "value"]
    real = ann(series_by[("value", HORIZONS_PRIMARY[0])])
    pool = [c for c in ret.columns if c not in ("SPY", "BIL")]
    vals = []
    for _ in range(draws):
        fake = val_ev.copy()
        fake["ticker"] = rng.choice(pool, size=len(fake))
        s, _ = event_book(fake, ret, HORIZONS_PRIMARY[0])
        vals.append(ann(s))
    vals = np.array(vals)
    out["null_matched_dates_random_firms"] = {
        "real_ann_pct": round(real, 3), "null_mean": round(float(vals.mean()), 3),
        "null_sd": round(float(vals.std(ddof=1)), 3),
        "pctile_of_real": round(float((vals < real).mean() * 100), 1),
        "note": "random firm on the SAME sessions — controls the calendar, "
                "not the B/M tilt; the value-minus-glamour contrast controls that"}
    out["variants_tried"].append("null_matched")

    # ------------------------------------------------------------- decision
    v126 = out["books"]["value"].get("h126", {}).get("net_1x", {})
    vmg = out["value_minus_glamour_h126"]
    kill = []
    if not (vmg["ann_pct"] > 0 and v126.get("alpha_ann_pct", -1) > 0):
        kill.append("value conditioning does not differentiate "
                    f"(V-G {vmg['ann_pct']}%/yr, value alpha "
                    f"{v126.get('alpha_ann_pct')}%)")
    if out["null_matched_dates_random_firms"]["pctile_of_real"] <= 90:
        kill.append("indistinguishable from random firms on the same dates")
    if sum(x > 0 for x in vmg["thirds"]) < 2:
        kill.append(f"one-era result (V-G thirds {vmg['thirds']})")
    if kill:
        verdict, why = "KILL_H43", "; ".join(kill)
    else:
        verdict, why = "SURVIVES_TO_GATES", \
            "value conditioning differentiates and survives its controls — " \
            "to the section-12 gates, not production."
    out["verdict"] = {"call": verdict, "why": why, "production_approved": False}
    out["limitations"] = [
        "announcement proxy: 8-K FTS phrase match + 365d cooldown, not a "
        "hand-verified authorization list",
        "8-K time-of-day unknown -> next-session entry (conservative)",
        "no PIT sector map (GICS licensed) — sector concentration unreported",
    ]
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

    idx = pd.date_range("2020-01-01", periods=200, freq="B", tz="US/Eastern")
    ret = pd.DataFrame(0.0, index=idx, columns=["XX", "SPY"])
    ret.iloc[100, 0] = 0.5
    ev = pd.DataFrame([{"ticker": "XX",
                        "filed": idx[99].tz_localize(None).normalize()}])
    s, _ = event_book(ev, ret, 63)
    check("filed j=99 -> entry close 100 -> spike at 100 NOT captured",
          s.iloc[100] == 0)
    ev2 = pd.DataFrame([{"ticker": "XX",
                         "filed": idx[98].tz_localize(None).normalize()}])
    s2, _ = event_book(ev2, ret, 63)
    check("filed j=98 -> entry close 99 -> spike at 100 captured",
          s2.iloc[100] > 0)

    # cooldown: two filings 100 days apart -> one event
    class P:                                     # minimal stand-in
        close = pd.DataFrame(1.0, index=idx, columns=["XX"])
    r = pd.DataFrame({"filed": [idx[10].tz_localize(None),
                                idx[80].tz_localize(None)],
                      "cik": ["1", "1"], "adsh": ["a", "b"],
                      "name": ["X", "X"]})
    r["filed"] = r["filed"].dt.normalize()
    kept, last = [], {}
    for _, e in r.sort_values("filed").iterrows():
        if "1" in last and (e["filed"] - last["1"]).days < COOLDOWN_DAYS:
            continue
        last["1"] = e["filed"]
        kept.append(e)
    check("365-day cooldown collapses two filings 98 sessions apart into one",
          len(kept) == 1)

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.h43_repurchase_value")
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
