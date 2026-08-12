"""H42 (handoff H38) — OPPORTUNISTIC INSIDER PURCHASES, routine traders removed.

MECHANISM (one sentence)
------------------------
Some insiders buy on a private-information clock and some on a calendar clock
(diversification programs, year-end rebalancing); Cohen-Malloy-Pomorski showed
the predictive content lives almost entirely in the NON-routine ("opportunistic")
purchases, so the test is opportunistic-vs-routine, never "all Form 4 buys".

DATA
----
SEC insider-transactions data sets (DERA quarterly TSVs), 2013Q1-2026Q1,
streamed and discarded — only the purchase rows land on disk. Purchases are
non-derivative Form 4 rows with TRANS_CODE == 'P' and TRANS_ACQUIRED_DISP_CD
== 'A': open-market or private purchase of the issuer's stock. Grants, awards,
option exercises, conversions and gifts are excluded by the code filter, per
handoff 9.1. SUBMISSION carries the FILING date (public knowledge) and the
issuer's ticker AT FILING TIME — a second survivorship-free identity source,
cross-checked against scout/historical_identity.py.

THE CLASSIFIER (frozen ex ante, Cohen-Malloy-Pomorski's rule verbatim)
----------------------------------------------------------------------
An insider-firm pair is CLASSIFIABLE at a trade if it shows at least one
purchase in EACH of the three preceding calendar years. A classifiable trade
is ROUTINE if each of those three years contains a purchase in the SAME
calendar month as the current trade; otherwise OPPORTUNISTIC. Trades by
insiders with thinner history are UNCLASSIFIABLE and reported as their own
bucket — never silently merged. 2013-2015 purchases exist only to classify
2016+ trades; they are never traded.

TIMING (handoff 9.2, conservative)
----------------------------------
The data sets carry the filing DATE, not the intraday timestamp, so no
same-close fill can be justified: entry is at the close of the FIRST session
STRICTLY AFTER the filing date, earning returns from the session after that.

PORTFOLIO
---------
Universe: purchases whose issuer CIK maps to a PIT S&P 500 member (identity
map inverted); the unresolved 14 are counted out. Long-only overlapping
cohorts, equal capital; horizons 63/126 primary, 21/252 diagnostic; books:
ALL / ROUTINE / OPPORTUNISTIC / UNCLASSIFIABLE, plus OPP-minus-ROUTINE
directly. 10 bps per leg, 2x stress. Controls: issuer-level timing shuffle
(each issuer's event dates circularly rotated), halves, thirds, top-10 event
concentration, dollar-size and liquidity terciles.

KILL RULES (handoff 9.6): opportunistic must materially beat routine/all;
shuffle must not explain it; no single era/bucket may carry it; 2x costs must
not zero the long-only excess.

Run:
  python -m scout.h42_insiders --fetch
  python -m scout.h42_insiders --run
  python -m scout.h42_insiders --selftest
"""
from __future__ import annotations

import argparse
import io
import json
import math
import time
import zipfile

import numpy as np
import pandas as pd
import requests

from . import config
from .price_integrity import build_panel

UA = {"User-Agent": "WeWillSee research davidmking7@gmail.com"}
BASE = ("https://www.sec.gov/files/structureddata/data/"
        "insider-transactions-data-sets")
PURCHASES_CSV = config.SCOUT_DIR / "cache_h42_purchases.csv"
RESULTS = config.SCOUT_DIR / "h42_results.json"
IDENTITY = config.SCOUT_DIR / "identity_map.json"

FETCH_START_Y = 2013         # 3 classification years before the 2016 sample
COST_BPS_LEG = 10.0
HORIZONS_PRIMARY = (63, 126)
HORIZONS_DIAG = (21, 252)
N_DRAWS = 300


# ------------------------------------------------------------------ fetching

def fetch(verbose: bool = True) -> pd.DataFrame:
    rows = []
    for y in range(FETCH_START_Y, 2027):
        for q in (1, 2, 3, 4):
            url = f"{BASE}/{y}q{q}_form345.zip"
            try:
                r = requests.get(url, headers=UA, timeout=300)
                if r.status_code != 200:
                    if verbose:
                        print(f"  {y}q{q}: HTTP {r.status_code} — skip")
                    continue
                z = zipfile.ZipFile(io.BytesIO(r.content))
                sub = pd.read_csv(z.open("SUBMISSION.tsv"), sep="\t",
                                  usecols=["ACCESSION_NUMBER", "FILING_DATE",
                                           "DOCUMENT_TYPE", "ISSUERCIK",
                                           "ISSUERTRADINGSYMBOL"],
                                  dtype=str, low_memory=False)
                nd = pd.read_csv(z.open("NONDERIV_TRANS.tsv"), sep="\t",
                                 usecols=["ACCESSION_NUMBER", "TRANS_DATE",
                                          "TRANS_FORM_TYPE", "TRANS_CODE",
                                          "TRANS_SHARES", "TRANS_PRICEPERSHARE",
                                          "TRANS_ACQUIRED_DISP_CD"],
                                 dtype=str, low_memory=False)
                ro = pd.read_csv(z.open("REPORTINGOWNER.tsv"), sep="\t",
                                 usecols=["ACCESSION_NUMBER", "RPTOWNERCIK"],
                                 dtype=str, low_memory=False)
            except Exception as e:
                if verbose:
                    print(f"  {y}q{q}: {type(e).__name__} — skip")
                continue
            buys = nd[(nd["TRANS_CODE"] == "P")
                      & (nd["TRANS_ACQUIRED_DISP_CD"] == "A")
                      & (nd["TRANS_FORM_TYPE"].astype(float) == 4)]
            m = (buys.merge(sub[sub["DOCUMENT_TYPE"] == "4"],
                            on="ACCESSION_NUMBER")
                     .merge(ro.drop_duplicates("ACCESSION_NUMBER"),
                            on="ACCESSION_NUMBER"))
            rows.append(m)
            if verbose:
                print(f"  {y}q{q}: {len(m)} purchase rows")
            time.sleep(0.2)
    df = pd.concat(rows, ignore_index=True)
    df.to_csv(PURCHASES_CSV, index=False)
    if verbose:
        print(f"  total {len(df)} purchase rows -> {PURCHASES_CSV.name}")
    return df


# ------------------------------------------------------------ classification

def classify(df: pd.DataFrame) -> pd.DataFrame:
    """CMP labels per purchase row. Frozen rule, see module docstring."""
    d = df.copy()
    d["filed"] = pd.to_datetime(d["FILING_DATE"], errors="coerce")
    d["trans"] = pd.to_datetime(d["TRANS_DATE"], errors="coerce")
    d = d.dropna(subset=["filed", "trans"])
    d["year"] = d["trans"].dt.year
    d["month"] = d["trans"].dt.month
    key = list(zip(d["RPTOWNERCIK"], d["ISSUERCIK"]))
    d["pair"] = key
    # purchase-years and purchase-(year,month) sets per insider-firm pair
    years_by_pair: dict = {}
    ym_by_pair: dict = {}
    for pair, yr, mo in zip(d["pair"], d["year"], d["month"]):
        years_by_pair.setdefault(pair, set()).add(yr)
        ym_by_pair.setdefault(pair, set()).add((yr, mo))
    labels = []
    for pair, yr, mo in zip(d["pair"], d["year"], d["month"]):
        yrs = years_by_pair[pair]
        if not all((yr - k) in yrs for k in (1, 2, 3)):
            labels.append("unclassifiable")
        elif all((yr - k, mo) in ym_by_pair[pair] for k in (1, 2, 3)):
            labels.append("routine")
        else:
            labels.append("opportunistic")
    d["label"] = labels
    return d


# ------------------------------------------------------------- the portfolio

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
    """Long-only overlapping cohorts. Entry close of first session STRICTLY
    after the filing date; returns from the session after entry."""
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
        j1 = min(j0 + horizon, n - 1)
        r = ret[sym].iloc[j0 + 1:j1 + 1].fillna(0.0).to_numpy()
        book[j0 + 1:j0 + 1 + len(r)] += r / horizon
        active[j0 + 1:j0 + 1 + len(r)] += 1.0 / horizon
        contrib.append((sym, str(naive[j0].date()), float(r.sum())))
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
    thirds = [round(ann(s.iloc[a:z]), 2) for a, z in zip(edges[:-1], edges[1:])]
    h = len(s) // 2
    return {"ann_pct": round(ann(s), 3), "t_nw": round(nw_t(s, horizon), 2),
            "beta": round(b, 3), "alpha_ann_pct": round(ann(resid), 3),
            "t_alpha": round(nw_t(resid, horizon), 2),
            "halves": [round(ann(s.iloc[:h]), 2), round(ann(s.iloc[h:]), 2)],
            "thirds": thirds}


def run(quick: bool = False, verbose: bool = True) -> dict:
    raw = pd.read_csv(PURCHASES_CSV, dtype=str)
    d = classify(raw)

    # PIT filter through the identity map, inverted (cik -> ticker)
    idm = json.loads(IDENTITY.read_text())
    cik2tkr: dict[int, str] = {}
    for r in idm["rows"]:
        if r.get("cik"):
            cik2tkr[int(r["cik"])] = r["ticker"]
        for c in r.get("candidates", []):
            cik2tkr[int(c["cik"])] = r["ticker"]
    d["issuer_cik_int"] = pd.to_numeric(d["ISSUERCIK"], errors="coerce")
    d["ticker"] = d["issuer_cik_int"].map(cik2tkr)
    n_all_mkt = len(d)
    d = d.dropna(subset=["ticker"])
    d = d[d["filed"] >= "2016-01-04"]
    d["dollars"] = (pd.to_numeric(d["TRANS_SHARES"], errors="coerce")
                    * pd.to_numeric(d["TRANS_PRICEPERSHARE"], errors="coerce"))
    # one EVENT per (issuer, filing date, label): multiple rows in one filing
    # are one decision
    ev = (d.groupby(["ticker", "filed", "label"], as_index=False)
            .agg(dollars=("dollars", "sum"), n_rows=("ticker", "size")))
    ev["filed"] = pd.to_datetime(ev["filed"])

    P = build_panel("2016-01-04", "2026-08-07", extra=("SPY", "BIL"))
    ret, spy = P.ret, P.ret["SPY"]
    dv = (P.close * P.volume).rolling(60).median()

    out = {"hypothesis": "H42 (handoff H38) opportunistic insiders",
           "purchase_rows_market_wide": n_all_mkt,
           "events_pit": int(len(ev)),
           "by_label": ev["label"].value_counts().to_dict(),
           "classifier": "CMP: classifiable = purchases in each of 3 prior "
                         "years (same insider-firm pair); routine = same "
                         "calendar month in all 3; frozen ex ante",
           "timing": "entry at close of first session STRICTLY after filing "
                     "date (datasets carry no intraday time)",
           "integrity": P.report, "books": {}, "variants_tried": []}

    horizons = HORIZONS_PRIMARY + (() if quick else HORIZONS_DIAG)
    series_by = {}
    for label in ("all", "routine", "opportunistic", "unclassifiable"):
        sub = ev if label == "all" else ev[ev["label"] == label]
        blk = {"n_events": int(len(sub))}
        for h in horizons:
            s, contrib = event_book(sub, ret, h)
            series_by[(label, h)] = s
            cost1 = COST_BPS_LEG / 100 * (252 / h) / 100 * 100  # %/yr, 1 leg
            c = pd.DataFrame(contrib, columns=["sym", "d", "pnl"])
            tot = c["pnl"].sum()
            top10 = round(float(c["pnl"].abs().nlargest(10).sum()
                                / abs(tot)), 3) if tot else None
            blk[f"h{h}"] = {
                "gross": block(s, spy, h),
                "net_1x": block(s, spy, h, cost_ann_pct=cost1),
                "net_2x": block(s, spy, h, cost_ann_pct=2 * cost1),
                "minus_spy_net1x": block(s - spy, spy, h, cost_ann_pct=cost1),
                "top10_abs_share": top10}
            out["variants_tried"].append(f"{label}_h{h}")
        out["books"][label] = blk
        if verbose and not quick:
            g = blk["h63"]["gross"]
            print(f"  {label:15s} n={blk['n_events']:5d}  h63 {g['ann_pct']:+7.2f}%/yr"
                  f" (t {g['t_nw']:+.2f})  alpha {g['alpha_ann_pct']:+.2f} "
                  f"(t {g['t_alpha']:+.2f})")

    # opportunistic minus routine, the mechanism's own contrast
    for h in HORIZONS_PRIMARY:
        diff = series_by[("opportunistic", h)] - series_by[("routine", h)]
        out[f"opp_minus_routine_h{h}"] = block(diff, spy, h)
        out["variants_tried"].append(f"opp_minus_routine_h{h}")

    # dollar-size and liquidity terciles on the opportunistic book (h=63)
    opp = ev[ev["label"] == "opportunistic"].copy()
    naive = pd.DatetimeIndex(ret.index.tz_localize(None).normalize())
    pos = naive.searchsorted(opp["filed"].values, side="right").clip(0, len(naive) - 1)
    liq = []
    for (_, e), j in zip(opp.iterrows(), pos):
        liq.append(dv[e["ticker"]].iloc[j] if e["ticker"] in dv.columns else np.nan)
    opp["liq"] = liq
    for dim in ("dollars", "liq"):
        qs = opp[dim].quantile([1 / 3, 2 / 3])
        cells = {}
        for name, sel in (("t1", opp[dim] <= qs.iloc[0]),
                          ("t2", (opp[dim] > qs.iloc[0]) & (opp[dim] <= qs.iloc[1])),
                          ("t3", opp[dim] > qs.iloc[1])):
            s, _ = event_book(opp[sel], ret, 63)
            cells[name] = {"n": int(sel.sum()), "ann_pct": round(ann(s), 2),
                           "t": round(nw_t(s, 63), 2)}
        out[f"opportunistic_by_{dim}"] = cells
        out["variants_tried"].append(f"buckets_{dim}")

    # timing-shuffle null on the opportunistic h63 book
    rng = np.random.default_rng(20260812)
    draws = 30 if quick else N_DRAWS
    real = ann(series_by[("opportunistic", 63)])
    vals = []
    n_dates = len(ret.index)
    for _ in range(draws):
        sh = opp.copy()
        # rotate each issuer's filing dates by an issuer-specific offset
        off = {t: int(rng.integers(126, n_dates - 126)) for t in sh["ticker"].unique()}
        newpos = [(naive.searchsorted(f, side="right") + off[t]) % (n_dates - 2)
                  for t, f in zip(sh["ticker"], sh["filed"])]
        sh["filed"] = [naive[j] for j in newpos]
        s, _ = event_book(sh, ret, 63)
        vals.append(ann(s))
    vals = np.array(vals)
    out["null_timing_shuffle"] = {
        "real_ann_pct": round(real, 3),
        "null_mean": round(float(vals.mean()), 3),
        "null_sd": round(float(vals.std(ddof=1)), 3),
        "pctile_of_real": round(float((vals < real).mean() * 100), 1)}
    out["variants_tried"].append("null_timing_shuffle")

    # ------------------------------------------------------------- decision
    o63 = out["books"]["opportunistic"]["h63"]
    r63 = out["books"]["routine"]["h63"]
    omr = out["opp_minus_routine_h63"]
    kill_reasons = []
    if not (o63["net_1x"]["alpha_ann_pct"] > r63["net_1x"]["alpha_ann_pct"]
            and omr["ann_pct"] > 0):
        kill_reasons.append("opportunistic does not beat routine")
    if out["null_timing_shuffle"]["pctile_of_real"] <= 95:
        kill_reasons.append(
            f"timing shuffle explains it (real at "
            f"{out['null_timing_shuffle']['pctile_of_real']}th pctile)")
    if o63["net_2x"]["alpha_ann_pct"] <= 0:
        kill_reasons.append("2x costs zero the market-adjusted excess")
    thirds = o63["gross"]["thirds"]
    if sum(x > 0 for x in thirds) < 2:
        kill_reasons.append(f"carried by one era (thirds {thirds})")
    if kill_reasons:
        verdict, why = "KILL_H42", "; ".join(kill_reasons)
    else:
        verdict, why = "SURVIVES_TO_GATES", \
            "opportunistic > routine, shuffle cleared, eras consistent — " \
            "goes to the standalone sleeve gates (section 12), NOT production."
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

    # classifier on a constructed history
    rows = []
    for yr in (2016, 2017, 2018, 2019):
        rows.append({"RPTOWNERCIK": "1", "ISSUERCIK": "9", "FILING_DATE":
                     f"{yr}-03-15", "TRANS_DATE": f"{yr}-03-14"})   # every March
    rows.append({"RPTOWNERCIK": "2", "ISSUERCIK": "9",
                 "FILING_DATE": "2019-07-02", "TRANS_DATE": "2019-07-01"})
    for yr in (2016, 2017, 2018):
        rows.append({"RPTOWNERCIK": "3", "ISSUERCIK": "9", "FILING_DATE":
                     f"{yr}-0{yr - 2013}-10", "TRANS_DATE": f"{yr}-0{yr - 2013}-09"})
    rows.append({"RPTOWNERCIK": "3", "ISSUERCIK": "9",
                 "FILING_DATE": "2019-11-05", "TRANS_DATE": "2019-11-04"})
    d = classify(pd.DataFrame(rows))
    lab = dict(zip(zip(d["RPTOWNERCIK"], d["trans"].dt.year), d["label"]))
    check("4th same-month March buy is ROUTINE", lab[("1", 2019)] == "routine")
    check("single-buy insider is UNCLASSIFIABLE", lab[("2", 2019)] == "unclassifiable")
    check("3-year history, different months -> OPPORTUNISTIC",
          lab[("3", 2019)] == "opportunistic")
    check("2016 trade lacks 3 prior years in-window -> UNCLASSIFIABLE",
          lab[("1", 2016)] == "unclassifiable")

    # timing: filed on session j -> entry close j+1 -> first return j+2
    idx = pd.date_range("2020-01-01", periods=200, freq="B", tz="US/Eastern")
    ret = pd.DataFrame(0.0, index=idx, columns=["XX", "SPY"])
    ret.iloc[100, 0] = 0.5
    ev = pd.DataFrame([{"ticker": "XX", "filed": idx[98].tz_localize(None)
                        .normalize()}])
    s, _ = event_book(ev, ret, 63)
    check("filed at j=98: entry close 99, spike at 100 captured", s.iloc[100] > 0)
    ev2 = pd.DataFrame([{"ticker": "XX", "filed": idx[99].tz_localize(None)
                         .normalize()}])
    s2, _ = event_book(ev2, ret, 63)
    check("filed at j=99: entry close 100, spike at 100 NOT captured",
          s2.iloc[100] == 0)
    ev3 = pd.DataFrame([{"ticker": "XX", "filed": idx[100].tz_localize(None)
                         .normalize()}])
    s3, _ = event_book(ev3, ret, 63)
    check("filed ON the spike day cannot capture it", s3.iloc[100] == 0)

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.h42_insiders")
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
