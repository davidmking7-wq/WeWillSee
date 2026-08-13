"""Merger deal universe — assembled from ANNOUNCEMENTS, not from completions.

WHY THIS MODULE EXISTS, AND WHY THE OBVIOUS SOURCE IS POISON
------------------------------------------------------------
Alpaca's corporate-actions feed exposes `cash_merger`, `stock_merger` and
`stock_and_cash_merger` — 5,319 structured events over 2016-2026, with an
effective date, an acquiree symbol and a rate. It is fast, clean, and the
natural thing to reach for.

**It contains only deals that COMPLETED.** A merger that was announced and then
broke — blocked by regulators, financing pulled, shareholders voted no, buyer
walked — never generates a merger corporate action, because no corporate action
ever occurred. Building a merger-arbitrage study from that feed measures the
return of deals conditional on them having worked, which is not a strategy
anyone could have traded. It would look spectacular.

This is the same failure that inverted H23 (illiquidity looked like t = +4.09
until the universe was made point-in-time) and it is the specific trap the
Buffett-workouts hypothesis is most likely to fall into, because the poisoned
source is so much easier to use than the honest one.

THE HONEST CONSTRUCTION
-----------------------
    ANNOUNCEMENTS are the spine.  COMPLETIONS only supply the OUTCOME.

    announcements()   SEC EDGAR full-text search over the forms that mark a
                      definitive deal: DEFM14A (merger proxy), SC 14D9 and
                      SC TO-T (tender offers). Every deal that was ever
                      announced appears here, including the ones that died.
    completed()       Alpaca corporate actions — used ONLY to ask "did this
                      announced deal finish, and when".
    universe()        left-joins the two. An announcement with no completion
                      inside the window is a BREAK or a still-pending deal,
                      and those are the observations that carry the left tail.

A study that reports a merger-arb return without reporting its break rate has
not measured the risk it was being paid for.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not parse the deal PRICE out of the filing text. Terms live in prose
("$54.20 in cash per share", "0.6270 shares of Parent common stock") and
extracting them reliably is its own project. What is available without that:
the announcement date, the target, the form type, and the outcome — which is
enough to measure the announcement-to-completion return from market prices,
the break rate, and the correlation to the market. That is the core of the
hypothesis. Deal terms would add the ex-ante spread, and are future work.

EDGAR full-text search covers 2001+ and caps at 10,000 hits per query, so
queries are chunked by quarter.

Run:
  python -m scout.deals --build --start 2016-01-01 --end 2026-08-01
  python -m scout.deals --status
"""
from __future__ import annotations

import argparse
import json
import time

import pandas as pd
import requests

from . import config

UA = {"User-Agent": "WeWillSee research davidmking7@gmail.com"}
FTS = "https://efts.sec.gov/LATEST/search-index"
CA = "https://data.alpaca.markets/v1/corporate-actions"

ANNOUNCE_FORMS = ("DEFM14A", "SC 14D9", "SC TO-T")
MERGER_TYPES = ("cash_merger", "stock_merger", "stock_and_cash_merger")

CACHE_ANN = config.SCOUT_DIR / "cache_deals_announcements.pkl"
CACHE_DONE = config.SCOUT_DIR / "cache_deals_completed.pkl"


def _alpaca_headers() -> dict:
    return {"APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY}


# ------------------------------------------------------------- announcements

def _fts_page(form: str, start: str, end: str, frm: int) -> dict:
    params = {"q": '"merger agreement"', "forms": form,
              "dateRange": "custom", "startdt": start, "enddt": end}
    if frm:
        params["from"] = frm
    for attempt in range(5):
        r = requests.get(FTS, headers=UA, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        time.sleep(1.5 * (attempt + 1))
    return {}


def announcements(start: str, end: str, use_cache: bool = True,
                  verbose: bool = True) -> pd.DataFrame:
    """Every definitive-deal filing in the window, including deals that died.

    Chunked by quarter because EDGAR full-text search caps at 10,000 hits and
    silently truncates rather than erroring — a single decade-wide query would
    quietly drop most of the sample and there would be nothing in the response
    to say so."""
    if use_cache and CACHE_ANN.exists():
        df = pd.read_pickle(CACHE_ANN)
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        if df["filed"].min() <= lo and df["filed"].max() >= hi - pd.Timedelta(days=95):
            if verbose:
                print(f"  announcements: {len(df)} from cache")
            return df[(df["filed"] >= lo) & (df["filed"] <= hi)]

    rows = []
    for q_start in pd.date_range(start, end, freq="QS"):
        q_end = min(q_start + pd.offsets.QuarterEnd(0), pd.Timestamp(end))
        for form in ANNOUNCE_FORMS:
            frm, seen = 0, 0
            while True:
                j = _fts_page(form, str(q_start.date()), str(q_end.date()), frm)
                hits = (j.get("hits") or {}).get("hits") or []
                if not hits:
                    break
                for h in hits:
                    s = h.get("_source", {})
                    names = s.get("display_names") or []
                    rows.append({
                        "filed": pd.Timestamp(s.get("file_date")),
                        "form": form,
                        "target_name": names[0] if names else None,
                        "ticker": _ticker_from(names[0]) if names else None,
                        "cik": (s.get("ciks") or [None])[0],
                        "adsh": s.get("adsh") or h.get("_id"),
                    })
                seen += len(hits)
                total = ((j.get("hits") or {}).get("total") or {}).get("value", 0)
                frm += len(hits)
                if seen >= min(total, 9990) or len(hits) == 0:
                    break
            time.sleep(0.12)         # SEC asks for <=10 req/s; stay well under
        if verbose:
            print(f"  {q_start.date()}..{q_end.date()}: {len(rows)} cumulative")

    df = pd.DataFrame(rows).dropna(subset=["filed"]).drop_duplicates(subset=["adsh"])
    df.to_pickle(CACHE_ANN)
    if verbose:
        print(f"  announcements: {len(df)} filings, "
              f"{df['ticker'].notna().sum()} with a parsed ticker")
    return df


def _ticker_from(display_name: str | None) -> str | None:
    """EDGAR renders names as 'Acme Corp (ACME) (CIK 0000123456)'."""
    if not display_name or "(" not in display_name:
        return None
    parts = [p.strip(" )") for p in display_name.split("(")[1:]]
    for p in parts:
        if p and p.upper() == p and p.replace(".", "").replace("-", "").isalnum() \
                and not p.startswith("CIK") and 1 <= len(p) <= 6:
            return p
    return None


# ---------------------------------------------------------------- completions

def completed(start: str, end: str, use_cache: bool = True,
              verbose: bool = True) -> pd.DataFrame:
    """Mergers that actually processed. SURVIVORSHIP-POISONED ON ITS OWN —
    join it TO the announcements, never use it as the population."""
    if use_cache and CACHE_DONE.exists():
        df = pd.read_pickle(CACHE_DONE)
        if verbose:
            print(f"  completions: {len(df)} from cache")
        return df
    rows = []
    for t in MERGER_TYPES:
        tok = None
        while True:
            p = {"types": t, "start": start, "end": end, "limit": 1000}
            if tok:
                p["page_token"] = tok
            r = requests.get(CA, headers=_alpaca_headers(), params=p, timeout=60)
            if not r.ok:
                break
            j = r.json()
            for _, events in (j.get("corporate_actions") or {}).items():
                for e in events:
                    rows.append({"kind": t,
                                 "ticker": e.get("acquiree_symbol"),
                                 "effective": pd.Timestamp(e.get("effective_date"))
                                 if e.get("effective_date") else pd.NaT,
                                 "rate": e.get("rate")})
            tok = j.get("next_page_token")
            if not tok:
                break
    df = pd.DataFrame(rows).dropna(subset=["effective"])
    df.to_pickle(CACHE_DONE)
    if verbose:
        print(f"  completions: {len(df)} merger events")
    return df


# ------------------------------------------------------------------- universe

def universe(start: str, end: str, max_days: int = 400,
             verbose: bool = True) -> pd.DataFrame:
    """Announcements joined to outcomes. One row per announced deal.

    `completed` is True only when a merger corporate action for that ticker
    lands AFTER the announcement and within `max_days`. Everything else is a
    break or a still-pending deal, and those rows are the whole point: they
    carry the left tail that makes this an insurance-like return rather than
    a free spread."""
    ann = announcements(start, end, verbose=verbose)
    done = completed(start, end, verbose=verbose)
    ann = ann[ann["ticker"].notna()].copy()

    by_tkr: dict[str, list[pd.Timestamp]] = {}
    for t, e in zip(done["ticker"], done["effective"]):
        by_tkr.setdefault(t, []).append(e)

    eff, comp = [], []
    for tkr, filed in zip(ann["ticker"], ann["filed"]):
        cands = [d for d in by_tkr.get(tkr, [])
                 if pd.notna(d) and filed <= d <= filed + pd.Timedelta(days=max_days)]
        eff.append(min(cands) if cands else pd.NaT)
        comp.append(bool(cands))
    ann["effective"] = eff
    ann["completed"] = comp
    ann["days_to_close"] = (ann["effective"] - ann["filed"]).dt.days

    # one row per (ticker, deal): the FIRST definitive filing is the announcement
    ann = ann.sort_values("filed").drop_duplicates(subset=["ticker", "effective"],
                                                   keep="first")
    if verbose:
        n, c = len(ann), int(ann["completed"].sum())
        print(f"\n  deal universe: {n} announced, {c} completed "
              f"({100 * c / max(n, 1):.1f}%), {n - c} broken or pending")
        print(f"  median days to close: {ann['days_to_close'].median():.0f}")
        print("  NOTE: 'broken or pending' includes deals still live at the end of "
              "the window\n  and any completion the corporate-action feed missed — "
              "treat it as an UPPER\n  bound on the break rate, not the break rate.")
    return ann


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.deals")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2026-08-01")
    args = ap.parse_args()

    if args.status and not args.build:
        for p in (CACHE_ANN, CACHE_DONE):
            print(f"{p.name}: {'yes' if p.exists() else 'no'}")
        return

    u = universe(args.start, args.end)
    print("\nby year announced:")
    print(u.groupby(u["filed"].dt.year)
           .agg(announced=("ticker", "size"), completed=("completed", "sum"))
           .to_string())
    print("\nsample:")
    print(u[["filed", "ticker", "form", "effective", "completed", "days_to_close"]]
          .head(12).to_string(index=False))


if __name__ == "__main__":
    main()
