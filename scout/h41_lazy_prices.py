"""H41 (handoff H37a) — LAZY PRICES: does a big year-over-year change in a
company's 10-K text predict underperformance?

MECHANISM (one sentence)
------------------------
Firms mostly copy last year's 10-K; when they rewrite it something changed,
usually for the worse, and investors are slow to read — so LOW similarity
(changers) should underperform HIGH similarity (nonchangers) over the months
after filing (Cohen-Malloy-Nguyen "Lazy Prices").

WHY 2016-2026 IS THE RIGHT SAMPLE
---------------------------------
The original paper used 1995-2014. Our window is almost entirely OUTSIDE the
discovery sample, and the 2020+ half is fully post-publication — the
decision-relevant split (handoff 8.5): an effect that exists only 2016-2019
was arbitraged or never real.

IDENTITY, WITHOUT SURVIVORSHIP
------------------------------
CIKs come from scout/historical_identity.py: 719/742 PIT members resolve
cleanly, 9 more by disjoint filing-date spans; the 14 hard/unresolved are
COUNTED OUT LOUD, not silently dropped (they are disproportionately the
acquired — exactly the firms whose last 10-Ks changed most).

TEXT PIPELINE (frozen before any return was computed)
-----------------------------------------------------
Original 10-K filings only (form == "10-K"; no 10-K/A amendments, no 10-Q),
indexed by SEC FILING date, never period end. For each company chronologically:
fetch the primary document, strip HTML/XBRL markup, lowercase, drop digits and
punctuation, tokenize on whitespace; drop tokens shorter than 3 chars.
  cosine   = TF vectors, L2-normalised (hashed to 2^18 dims)
  jaccard  = token SETS (robustness diagnostic, handoff 8.3)
Similarity is computed against the company's IMMEDIATELY PREVIOUS original
10-K while both are in memory; only the numbers are stored — no filing text
ever lands on disk. Pairs more than 550 days apart are dropped (a skipped
year is not a year-over-year change).

PORTFOLIO (frozen)
------------------
Enter ONE CALENDAR MONTH after the filing date, at the next executable close;
hold 9 months (189 sessions); overlapping cohorts, equal capital across active
cohorts; monthly formation from pooled events. Sort each formation month's
events into quintiles by similarity — Q5 (nonchangers) long, Q1 (changers)
short — using an EXPANDING history of similarity scores through that formation
date only (no full-sample breakpoints: that would be lookahead).
Report: L/S; long leg vs SPY; short leg alone; equal-weight AND value-weight
(shares from sec_bulk.shares_panel x price); 2016-2019 vs 2020+; gross/1x/2x
(10 bps per leg); borrow at 25/100 bps/yr on the short leg; Rule 13 beta/alpha;
top-10 event contribution; sector left as a stated limitation (no PIT sector
map in the repo — GICS is licensed).

RULE 18: no gates. Data protections only (price_integrity panel).

Run:
  python -m scout.h41_lazy_prices --fetch      # harvest similarities (network)
  python -m scout.h41_lazy_prices --run        # portfolio + controls
  python -m scout.h41_lazy_prices --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import html as htmllib
import json
import math
import re
import time

import numpy as np
import pandas as pd
import requests

from . import config, pit
from .price_integrity import build_panel

UA = {"User-Agent": "WeWillSee research davidmking7@gmail.com"}
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"

SIMS_CSV = config.SCOUT_DIR / "cache_h41_similarities.csv"
RESULTS = config.SCOUT_DIR / "h41_results.json"
IDENTITY = config.SCOUT_DIR / "identity_map.json"

HASH_DIM = 2 ** 18
LAG_SESSIONS = 21            # one calendar month after filing
HOLD_SESSIONS = 189          # nine months
MAX_PAIR_DAYS = 550
COST_BPS_LEG = 10.0
MIN_TOKENS = 2000            # a 10-K with fewer real tokens is a parse failure

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z]{3,}")


# ------------------------------------------------------------------ fetching

def _get(url: str, tries: int = 5) -> requests.Response | None:
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            if r.status_code == 200:
                return r
            if r.status_code in (403, 429):
                time.sleep(2.0 * (k + 1))
                continue
            return None
        except requests.RequestException:
            time.sleep(2.0 * (k + 1))
    return None


def clean_text(raw: str) -> list[str]:
    """HTML/XBRL -> lowercase alpha tokens, len >= 3."""
    txt = htmllib.unescape(raw)
    txt = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", txt)
    txt = _TAG_RE.sub(" ", txt)
    return _TOKEN_RE.findall(txt.lower())


def tf_vector(tokens: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Hashed L2-normalised TF vector as (indices, values), plus nothing big."""
    counts: dict[int, float] = {}
    for t in tokens:
        h = int.from_bytes(hashlib.blake2b(t.encode(), digest_size=8).digest(),
                           "little") % HASH_DIM
        counts[h] = counts.get(h, 0.0) + 1.0
    idx = np.fromiter(counts.keys(), dtype=np.int64)
    val = np.fromiter(counts.values(), dtype=np.float64)
    val /= np.linalg.norm(val)
    order = np.argsort(idx)
    return idx[order], val[order]


def cosine(a, b) -> float:
    ia, va = a
    ib, vb = b
    i = j = 0
    s = 0.0
    while i < len(ia) and j < len(ib):
        if ia[i] == ib[j]:
            s += va[i] * vb[j]
            i += 1
            j += 1
        elif ia[i] < ib[j]:
            i += 1
        else:
            j += 1
    return s


def resolve_ciks() -> tuple[dict[str, list[dict]], dict]:
    """ticker -> [{cik, from, to}] from the identity map, conflicts by span."""
    rep = json.loads(IDENTITY.read_text())
    out: dict[str, list[dict]] = {}
    skipped = []
    for r in rep["rows"]:
        src = r.get("source")
        if src in ("current", "instance"):
            out[r["ticker"]] = [{"cik": r["cik"], "from": None, "to": None}]
        elif src == "conflict_date_resolvable":
            out[r["ticker"]] = [{"cik": c["cik"], "from": c["first_filed"],
                                 "to": c["last_filed"]} for c in r["candidates"]]
        else:
            skipped.append(r["ticker"])
    meta = {"resolved": len(out), "skipped_identity": sorted(skipped)}
    return out, meta


def fetch(verbose: bool = True) -> pd.DataFrame:
    """Harvest per-company chronological 10-K similarity pairs. Resumable."""
    ciks, meta = resolve_ciks()
    done_pairs = set()
    rows = []
    if SIMS_CSV.exists():
        prev = pd.read_csv(SIMS_CSV)
        rows = prev.to_dict("records")
        done_pairs = set(prev["accession"])
        if verbose:
            print(f"  resuming: {len(rows)} pairs already harvested")

    tickers = sorted(ciks)
    t0 = time.time()
    for n, tkr in enumerate(tickers):
        for ent in ciks[tkr]:
            cik = ent["cik"]
            r = _get(SUBMISSIONS.format(cik=cik))
            if r is None:
                continue
            j = r.json()
            recent = j.get("filings", {}).get("recent", {})
            older_files = [f["name"] for f in j.get("filings", {}).get("files", [])]
            frames = [pd.DataFrame(recent)]
            for fn in older_files:
                rr = _get(f"https://data.sec.gov/submissions/{fn}")
                if rr is not None:
                    frames.append(pd.DataFrame(rr.json()))
            sub = pd.concat(frames, ignore_index=True)
            sub = sub[sub["form"] == "10-K"].copy()          # ORIGINALS only
            if sub.empty:
                continue
            sub["filed"] = pd.to_datetime(sub["filingDate"])
            sub = sub[(sub["filed"] >= "2014-06-01") & (sub["filed"] <= "2026-08-07")]
            if ent["from"]:
                sub = sub[(sub["filed"] >= ent["from"]) & (sub["filed"] <= ent["to"])]
            sub = sub.sort_values("filed")
            prev_vec = prev_set = prev_filed = None
            for _, f in sub.iterrows():
                acc = f["accessionNumber"]
                if acc in done_pairs:
                    # already harvested as the LATER element of a pair; we
                    # still need it as prev for the next one -> refetch lazily
                    pass
                doc = f.get("primaryDocument") or ""
                if not doc:
                    continue
                url = ARCHIVE.format(cik=cik, acc_nodash=acc.replace("-", ""),
                                     doc=doc)
                resp = _get(url)
                if resp is None:
                    continue
                toks = clean_text(resp.text)
                if len(toks) < MIN_TOKENS:
                    prev_vec = prev_set = prev_filed = None
                    continue
                vec = tf_vector(toks)
                tset = set(toks)
                if prev_vec is not None and acc not in done_pairs:
                    gap = (f["filed"] - prev_filed).days
                    if 200 <= gap <= MAX_PAIR_DAYS:
                        rows.append({
                            "ticker": tkr, "cik": cik, "accession": acc,
                            "filed": str(f["filed"].date()),
                            "prev_filed": str(prev_filed.date()),
                            "gap_days": gap,
                            "cosine": round(cosine(prev_vec, vec), 6),
                            "jaccard": round(len(tset & prev_set)
                                             / max(1, len(tset | prev_set)), 6),
                            "n_tokens": len(toks)})
                        done_pairs.add(acc)
                prev_vec, prev_set, prev_filed = vec, tset, f["filed"]
                time.sleep(0.12)
        if verbose and (n + 1) % 25 == 0:
            pd.DataFrame(rows).to_csv(SIMS_CSV, index=False)
            print(f"  {n + 1}/{len(tickers)} tickers, {len(rows)} pairs, "
                  f"{time.time() - t0:.0f}s")
    df = pd.DataFrame(rows)
    df.to_csv(SIMS_CSV, index=False)
    if verbose:
        print(f"  fetched {len(df)} year-over-year pairs "
              f"({meta['skipped_identity']} identity-skipped)")
    return df


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


def ann(s: pd.Series) -> float:
    return 252 * float(s.mean()) * 100


def build_books(events: pd.DataFrame, ret: pd.DataFrame, close: pd.DataFrame,
                shares: pd.DataFrame | None, weight: str, sim_col: str):
    """Overlapping 9-month cohorts, expanding quintile breakpoints.

    events: one row per (ticker, filed, similarity). Entry at the first
    session >= filed + LAG_SESSIONS sessions; each monthly cohort holds
    HOLD_SESSIONS; 1/HOLD of capital per active session-cohort."""
    dates = ret.index
    naive = pd.DatetimeIndex(dates.tz_localize(None).normalize())
    ev = events.copy()
    ev["filed_ts"] = pd.to_datetime(ev["filed"])
    pos = naive.searchsorted(ev["filed_ts"]) + LAG_SESSIONS
    ev["entry_iloc"] = pos
    ev = ev[ev["entry_iloc"] < len(dates) - 1]

    n = len(dates)
    long_r = np.zeros(n)
    short_r = np.zeros(n)
    active_l = np.zeros(n)
    active_s = np.zeros(n)
    contrib = []           # (ticker, entry_date, leg, summed return contribution)
    ev = ev.sort_values("entry_iloc")
    hist: list[float] = []
    # group events by entry month; breakpoints from history BEFORE the month
    ev["entry_month"] = pd.PeriodIndex(
        [naive[min(i, n - 1)] for i in ev["entry_iloc"]], freq="M")
    for month, grp in ev.groupby("entry_month"):
        sims = grp[sim_col].to_numpy()
        if len(hist) >= 50:
            q_lo, q_hi = np.quantile(hist, [0.2, 0.8])
        else:
            hist.extend(sims)
            continue                        # burn-in: no trade, record history
        hist.extend(sims)
        for _, e in grp.iterrows():
            sym = e["ticker"]
            if sym not in ret.columns:
                continue
            j0 = int(e["entry_iloc"])
            j1 = min(j0 + HOLD_SESSIONS, n - 1)
            seg = ret[sym].iloc[j0 + 1:j1 + 1]
            if weight == "vw" and shares is not None:
                w = np.nan
                if sym in shares.columns:
                    sh = shares[sym].iloc[j0]
                    px = close[sym].iloc[j0]
                    w = sh * px
                if not np.isfinite(w):
                    continue
            else:
                w = 1.0
            leg = None
            if e[sim_col] >= q_hi:
                leg = "L"
            elif e[sim_col] <= q_lo:
                leg = "S"
            if leg is None:
                continue
            r = seg.fillna(0.0).to_numpy()
            span = slice(j0 + 1, j0 + 1 + len(r))
            if leg == "L":
                long_r[span] += w * r
                active_l[span] += w
            else:
                short_r[span] += w * r
                active_s[span] += w
            contrib.append((sym, str(naive[j0].date()), leg,
                            float(w * r.sum())))
    L = pd.Series(np.divide(long_r, active_l, out=np.zeros(n),
                            where=active_l > 0), index=dates)
    S = pd.Series(np.divide(short_r, active_s, out=np.zeros(n),
                            where=active_s > 0), index=dates)
    return L, S, contrib


def stats_block(series: pd.Series, spy: pd.Series, label: str,
                cost_ann_pct: float = 0.0) -> dict:
    s = series - cost_ann_pct / 100 / 252
    df = pd.concat([s, spy], axis=1, keys=["p", "m"]).dropna()
    b = float(np.cov(df["p"], df["m"])[0, 1] / np.var(df["m"].to_numpy()))
    resid = df["p"] - b * df["m"]
    halves = []
    h = len(df) // 2
    for a, z in ((0, h), (h, len(df))):
        seg = df["p"].iloc[a:z]
        halves.append({"ann_pct": round(ann(seg), 2),
                       "t": round(nw_t(seg, HOLD_SESSIONS), 2)})
    return {"label": label, "ann_pct": round(ann(s), 3),
            "t_nw": round(nw_t(s, HOLD_SESSIONS), 2),
            "vol_pct": round(float(s.std()) * math.sqrt(252) * 100, 2),
            "beta": round(b, 3), "alpha_ann_pct": round(ann(resid), 3),
            "t_alpha": round(nw_t(resid, HOLD_SESSIONS), 2), "halves": halves}


def run(verbose: bool = True) -> dict:
    from . import sec_bulk
    sims = pd.read_csv(SIMS_CSV)
    n_pairs = len(sims)
    P = build_panel("2016-01-04", "2026-08-07", extra=("SPY", "BIL"))
    ret, close, spy = P.ret, P.close, P.ret["SPY"]
    try:
        shares = sec_bulk.shares_panel()
        shares = shares.reindex(index=close.index, method="ffill")
    except Exception as e:
        shares = None
        print(f"  shares panel unavailable ({type(e).__name__}) — VW skipped, stated")

    sims = sims[pd.to_datetime(sims["filed"]) >= "2016-01-01"]
    out = {"hypothesis": "H41 (handoff H37a) lazy prices",
           "pairs_total": n_pairs, "pairs_2016plus": len(sims),
           "identity_skipped": resolve_ciks()[1]["skipped_identity"],
           "similarity_distribution": {
               "cosine": {k: round(float(v), 4) for k, v in
                          sims["cosine"].describe().items()},
               "jaccard_corr_with_cosine": round(float(
                   sims[["cosine", "jaccard"]].corr().iloc[0, 1]), 3)},
           "lag_sessions": LAG_SESSIONS, "hold_sessions": HOLD_SESSIONS,
           "books": {}, "variants_tried": []}

    for sim_col in ("cosine", "jaccard"):
        for weight in ("ew", "vw") if shares is not None else ("ew",):
            L, S, contrib = build_books(sims, ret, close, shares, weight, sim_col)
            ls = L - S
            blk = {
                "long_short_gross": stats_block(ls, spy, "Q5-Q1 gross"),
                "long_short_net1x": stats_block(
                    ls, spy, "net 1x",
                    cost_ann_pct=2 * COST_BPS_LEG / 100 * (12 / 9)),
                "long_short_net2x_borrow100": stats_block(
                    ls, spy, "net 2x + 100bp borrow",
                    cost_ann_pct=4 * COST_BPS_LEG / 100 * (12 / 9) + 1.0),
                "long_minus_spy": stats_block(L - spy, spy, "long leg - SPY"),
                "short_leg_alone": stats_block(S, spy, "short leg (raw)"),
            }
            # era split, the decision-relevant one
            for era, (a, b) in {"2016_2019": ("2016-01-01", "2019-12-31"),
                                "2020_plus": ("2020-01-01", "2026-08-07")}.items():
                seg = ls.loc[a:b]
                blk[f"era_{era}"] = {"ann_pct": round(ann(seg), 2),
                                     "t": round(nw_t(seg, HOLD_SESSIONS), 2)}
            # concentration: top-10 events' share of total L/S P&L
            c = pd.DataFrame(contrib, columns=["sym", "entry", "leg", "pnl"])
            c["signed"] = np.where(c["leg"] == "L", c["pnl"], -c["pnl"])
            tot = c["signed"].sum()
            top10 = c.reindex(c["signed"].abs().nlargest(10).index)
            blk["top10_event_share_of_pnl"] = round(
                float(top10["signed"].sum() / tot), 3) if tot != 0 else None
            blk["n_events_traded"] = int(len(c))
            out["books"][f"{sim_col}_{weight}"] = blk
            out["variants_tried"].append(f"{sim_col}_{weight}")
            if verbose:
                g = blk["long_short_gross"]
                print(f"  {sim_col}/{weight}: L/S {g['ann_pct']}%/yr "
                      f"(t {g['t_nw']}), alpha {g['alpha_ann_pct']}% "
                      f"(t {g['t_alpha']}), era20+ "
                      f"{blk['era_2020_plus']['ann_pct']}%")

    # ------------------------------------------------------------- decision
    prim = out["books"]["cosine_ew"]
    era_new = prim["era_2020_plus"]
    g = prim["long_short_net2x_borrow100"]
    right_sign_alive = era_new["ann_pct"] > 0 and g["ann_pct"] > 0
    strong = right_sign_alive and g["t_nw"] > 2 and \
        all(h["ann_pct"] > 0 for h in prim["long_short_gross"]["halves"])
    if strong:
        verdict, why = "ADVANCE_TO_H41B", \
            "sign + 2020+ era + stressed costs + both halves all positive."
    elif right_sign_alive:
        verdict, why = "ADVANCE_TO_H41B", \
            ("right sign incl. 2020+ era and stressed costs, but not " \
             "significant — advance is for the PREREGISTERED optionability " \
             "split only, per handoff 8.8, not a production claim.")
    else:
        verdict, why = "KILL_H41", \
            (f"L/S net-stressed {g['ann_pct']}%/yr (t {g['t_nw']}), 2020+ era "
             f"{era_new['ann_pct']}%/yr — the post-publication sample does "
             f"not pay.")
    out["verdict"] = {"call": verdict, "why": why, "production_approved": False}
    out["limitations"] = [
        "no PIT sector map in the repo (GICS licensed) — sector concentration unreported",
        "short borrow modeled as a flat 100 bps/yr fee, not name-level",
        "14 identity-unresolved PIT members excluded and counted",
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

    # text cleaning + similarity identities
    a = clean_text("<html><body>The company reported strong revenue growth "
                   "of 123 million dollars.</body></html>")
    check("clean_text strips markup and digits",
          "html" not in a and "123" not in " ".join(a) and "company" in a)
    va, vb = tf_vector(a), tf_vector(a)
    check("cosine(self) == 1", abs(cosine(va, vb) - 1) < 1e-9)
    b = clean_text("completely different words about litigation and defaults "
                   "everywhere risk risk risk")
    check("cosine(disjoint) == 0", cosine(va, tf_vector(b)) < 1e-9)

    # entry lag: an event filed on session j may first earn at j+LAG+1
    idx = pd.date_range("2020-01-01", periods=300, freq="B", tz="US/Eastern")
    ret = pd.DataFrame(0.0, index=idx, columns=["XX", "SPY"])
    spike = 100
    ret.iloc[spike, 0] = 1.0                       # a +100% day
    # filed so that entry_iloc = spike-1: entry at that close earns from
    # `spike` onward — the first legitimately capturable session
    ev = pd.DataFrame([{"ticker": "XX",
                        "filed": str(idx[spike - LAG_SESSIONS - 1].date()),
                        "cosine": 0.99, "jaccard": 0.99}])
    # burn-in bypass: preload history via 60 dummy events far in the past
    dummies = pd.DataFrame([{"ticker": "YY", "filed": "2019-01-02",
                             "cosine": 0.5 + i / 1000, "jaccard": 0.5}
                            for i in range(60)])
    close = (1 + ret).cumprod() * 100
    L, S, _ = build_books(pd.concat([dummies, ev]), ret, close, None, "ew",
                          "cosine")
    check("event entered with the 21-session lag captures the later spike",
          L.iloc[spike] > 0)
    ev2 = ev.assign(filed=str(idx[spike].date()))   # filed ON the spike day
    L2, _, _ = build_books(pd.concat([dummies, ev2]), ret, close, None, "ew",
                           "cosine")
    check("event filed the day of the spike does NOT capture it (lag enforced)",
          L2.iloc[spike] == 0)

    # expanding breakpoints: first 50 events are burn-in, never traded
    L3, S3, c3 = build_books(dummies, ret, close, None, "ew", "cosine")
    check("burn-in events are not traded", len(c3) == 0)

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.h41_lazy_prices")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(_selftest())
    if args.fetch:
        fetch()
    if args.run:
        run()


if __name__ == "__main__":
    main()
