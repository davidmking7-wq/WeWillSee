"""H32 — Buffett's "workouts": merger arbitrage as an (allegedly) market-neutral sleeve.

MECHANISM (one sentence, before any number)
-------------------------------------------
Once a merger agreement fixes a price and a date, the residual discount at which
the target trades is payment for bearing DEAL-BREAK risk (regulatory, financing,
vote), a hazard that is close to orthogonal to equity beta except in credit
crises — so a diversified book of announced deals should earn a positive return
with near-zero market exposure, which is the only structural route to a higher
Sharpe this repo has not yet tried.

THE WAY THIS STUDY FAILS, AND HOW IT IS PREVENTED
-------------------------------------------------
If the deal list is assembled from deals that COMPLETED, the measured premium is
a fabrication. Two defences, in order of strength:

1. THE ANCHOR IS A TARGET-FILED DOCUMENT, NOT AN OUTCOME. The sample is every
   PREM14A / PRER14A / DEFM14A / PREM14C / DEFM14C / SC 14D9 filed 2016-2026,
   read out of the SEC's quarterly `form.idx`. Those forms are filed by the
   TARGET, weeks-to-months before anyone knows whether the deal closes, and
   EDGAR keeps them forever whether it closed or not. Nothing about completion
   enters the selection.

2. THE PRIMARY ENTRY IS THE FILING DATE ITSELF. Entering at
   (first target merger filing) + 1 close makes the sample survivorship-COMPLETE
   BY CONSTRUCTION: conditional on that filing existing on date T, every deal
   alive on T is in the list, and its future is unknown to the sampler.
   A second specification enters at the announcement 8-K instead (the Buffett
   spec); that one has a real, stated hole — deals that die between announcement
   and the first proxy are missing from it — so it is reported as secondary.

The ticker is extracted FROM THE FILING TEXT, never from a current ticker map.
A current map (`company_tickers.json`) only knows companies that still file, so
using it would silently keep the deals that BROKE and drop the ones that closed:
the survivorship error running backwards. Coverage is reported by outcome to
show the extraction is not differential.

DATA DEFECTS GUARDED (all three named in BACKTEST-REPORT.md)
------------------------------------------------------------
1. unadjusted splits  -> Alpaca corporate-actions splits are pulled for every
   deal symbol and any bar-implied jump matching a known split ratio is repaired;
   a >|50%| move that is NOT a split is kept, because for a merger target that
   move is usually the deal breaking and deleting it would delete the tail.
2. spin-offs / reused tickers -> a symbol's bars are truncated at its confirmed
   merger effective date (Alpaca cash/stock merger corporate action); any later
   bars belong to a different company wearing the same ticker.
3. frozen quotes -> a run of >= 6 identical closes retires the symbol at the
   start of the run; this is the single most dangerous defect here because a
   delisted target is exactly the case that manufactures it.

WHAT IT MEASURED (2026-08-09, 448 deals, 2016-02-04..2026-08-03)
-----------------------------------------------------------------
The MECHANISM is real and large; the RETURN is not.

  sleeve   6.68%/yr, vol 9.29%, Sharpe 0.718, beta 0.271, corr 0.511,
           market-adjusted alpha +2.39%/yr at NW t 1.02, max DD -16.5%
  SPY      15.82%/yr, vol 17.54%, Sharpe 0.901, max DD -33.8%
  placebo  the SAME names 250 sessions EARLIER: beta 1.054, alpha -1.54%

The announcement converts a beta-1.05 stock into a beta-0.27 asset, and the
sleeve lost 8.3% while SPY lost 33.5% in the COVID crash. But alpha is +2.4%/yr
at t = 1.02, it is zero at 38 bps/side of slippage, deflated Sharpe is 0.21 at
N = 730, and adding the sleeve to a SPY book raises Sharpe by +0.049 gross,
+0.006 at 25 bps/side and +0.000 at 50. VERDICT: REJECTED as a tradeable edge;
the low beta is the finding, and it is not free.

Run:
    python -m scout.workout_lab --stage index     # SEC quarterly form indexes
    python -m scout.workout_lab --stage tickers   # ticker out of the filing text
    python -m scout.workout_lab --stage announce  # 8-K announcement dates
    python -m scout.workout_lab --stage prices    # bars + corporate actions
    python -m scout.workout_lab --stage measure   # the experiment
    python -m scout.workout_lab --all
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import html
import io
import json
import math
import pickle
import re
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config

UA = {"User-Agent": "WeWillSee research davidmking7@gmail.com"}
CACHE = config.SCOUT_DIR / "cache_workout"
CACHE.mkdir(exist_ok=True)

IDX_PKL = CACHE / "filings.pkl"
TICK_PKL = CACHE / "tickers.pkl"
ANN_PKL = CACHE / "announce.pkl"
PX_PKL = CACHE / "prices.pkl"
CA_PKL = CACHE / "corpact.pkl"
RESULTS = config.SCOUT_DIR / "workout_results.json"

START = "2016-01-01"
END = "2026-08-07"

# Target-filed merger documents. Every one of these is filed BY THE COMPANY
# BEING ACQUIRED, and every one of them exists long before the outcome.
TARGET_FORMS = {"PREM14A", "PRER14A", "DEFM14A", "PREM14C", "DEFM14C", "SC 14D9"}


# --------------------------------------------------------------- stage 1: index

def _quarters() -> list[tuple[int, int]]:
    out = []
    for y in range(2016, 2027):
        for q in (1, 2, 3, 4):
            if y == 2026 and q > 3:
                continue
            out.append((y, q))
    return out


def stage_index(verbose: bool = True) -> pd.DataFrame:
    """Every target-filed merger document 2016-2026, from SEC quarterly indexes."""
    if IDX_PKL.exists():
        df = pickle.load(open(IDX_PKL, "rb"))
        if verbose:
            print(f"  index: {len(df):,} filings cached, {df.cik.nunique():,} CIKs")
        return df

    rows = []
    for (y, q) in _quarters():
        url = f"https://www.sec.gov/Archives/edgar/full-index/{y}/QTR{q}/form.zip"
        try:
            r = requests.get(url, headers=UA, timeout=180)
            if r.status_code != 200:
                if verbose:
                    print(f"  {y}Q{q}: HTTP {r.status_code}")
                continue
            z = zipfile.ZipFile(io.BytesIO(r.content))
            raw = z.read("form.idx").decode("latin-1")
        except Exception as e:
            print(f"  {y}Q{q}: {type(e).__name__} {e}")
            continue
        n0 = len(rows)
        # Fixed-width columns SHIFT when a company name overflows its field
        # ("...MI/  805993"), so parse from the RIGHT with a regex instead:
        # the tail is always <cik> <yyyy-mm-dd> edgar/....
        tail = re.compile(r"^(\S+(?:\s\S+)*?)\s{2,}(.+?)\s+(\d{1,10})\s+"
                          r"(\d{4}-\d{2}-\d{2})\s+(edgar/\S+)\s*$")
        for line in raw.split("\n"):
            if "edgar/" not in line:
                continue
            m = tail.match(line.rstrip())
            if not m:
                continue
            form = m.group(1).strip()
            if form not in TARGET_FORMS:
                continue
            rows.append({"form": form, "name": m.group(2).strip(),
                         "cik": int(m.group(3)), "date": m.group(4),
                         "path": m.group(5)})
        if verbose:
            print(f"  {y}Q{q}: {len(rows) - n0} target merger filings")
        time.sleep(0.12)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= START) & (df["date"] <= END)].sort_values(["cik", "date"])
    pickle.dump(df, open(IDX_PKL, "wb"))
    if verbose:
        print(f"  index: {len(df):,} filings, {df.cik.nunique():,} unique CIKs")
    return df


# ------------------------------------------------------------- stage 2: tickers

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
EXCH = r"(?:NYSE American|NYSE MKT|NYSE Amex|NYSE|NASDAQ|Nasdaq|AMEX|NASDAQ Global Select Market|OTC)"
PAT_PAREN = re.compile(r"\(\s*" + EXCH + r"\s*[:\-]\s*([A-Z]{1,5})\s*\)")
PAT_SYMBOL = re.compile(r"(?:trading\s+)?symbol[s]?[^A-Za-z0-9]{0,30}[\"“‘']?([A-Z]{1,5})[\"”’']?")
STOP = {"THE", "AND", "FOR", "INC", "LLC", "CO", "LP", "SEC", "USA", "NYSE",
        "OTC", "AMEX", "A", "B", "I", "II", "III", "IV", "V", "X", "NA", "N",
        "CUSIP", "ITEM", "PART", "NOTE", "NO", "YES", "NONE", "NYSEA"}


def _head_text(url: str, nbytes: int = 400_000) -> str:
    r = requests.get(url, headers=UA, stream=True, timeout=90)
    raw = r.raw.read(nbytes, decode_content=True)
    r.close()
    t = raw.decode("utf-8", errors="ignore")
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", t)))


SUFFIX = re.compile(r"\b(INC|CORP|CORPORATION|COMPANY|CO|LTD|LIMITED|LLC|LP|PLC|"
                    r"HOLDINGS|HOLDING|GROUP|TRUST|THE|NV|SA|AB|AG|CLASS|COMMON|"
                    r"NEW|OLD|USA|US|INTERNATIONAL|INDUSTRIES|TECHNOLOGIES|"
                    r"PARTNERS|BANCORP|FINANCIAL|SYSTEMS|SOLUTIONS|/[A-Z]{2}/?)\b")
PARENT_WORDS = re.compile(r"\b(parent|acquir(?:o|e)r|purchaser|buyer|offeror|"
                          r"merger sub|bidco|topco)\b", re.I)
SELF_WORDS = re.compile(r"\b(our common stock|our shares|the Company.s common stock|"
                        r"shares of our|subject company|the Company.s shares)\b", re.I)


def _name_tokens(name: str) -> list[str]:
    n = SUFFIX.sub(" ", re.sub(r"[^A-Za-z0-9 ]", " ", name.upper()))
    return [t for t in n.split() if len(t) >= 4][:3]


def _extract_ticker(text: str, name: str = "") -> tuple[str | None, list, dict]:
    """Ticker of the SUBJECT company, scored by the context around each mention.

    Both parties' symbols appear on a merger proxy cover page ("Parent common
    stock is listed under the symbol ABC"), and simply taking the most frequent
    one hands back the ACQUIRER about a third of the time. Each candidate is
    therefore scored on a 320-character window: the filer's own distinctive name
    tokens and self-referential phrases add, parent/acquirer words subtract."""
    toks = _name_tokens(name)
    letters = re.sub(r"[^A-Z]", "", name.upper())
    scores: dict[str, float] = {}
    order: dict[str, int] = {}
    k = 0
    for pat, base in ((PAT_PAREN, 1.0), (PAT_SYMBOL, 1.0)):
        for m in pat.finditer(text):
            s = m.group(1)
            if not s or s in STOP:
                continue
            lo = max(0, m.start() - 320)
            win = text[lo:m.end() + 120]
            sc = base
            if any(t in win.upper() for t in toks):
                sc += 3.0
            if SELF_WORDS.search(win):
                sc += 2.0
            if PARENT_WORDS.search(win):
                sc -= 4.0
            # BEST-context wins, not most-mentioned: an acquirer named on every
            # page otherwise outscores a target named twice on the cover.
            scores[s] = max(scores.get(s, -99.0), sc)
            order.setdefault(s, k)
            k += 1
    if not scores:
        return None, [], {}
    # a ticker that is a subsequence of the filer's own name is almost always
    # the filer's own ticker (AMNB <- AMericaN national Bankshares)
    for s in scores:
        i = 0
        for ch in letters:
            if i < len(s) and ch == s[i]:
                i += 1
        if i == len(s):
            scores[s] += 2.5
    best = sorted(scores, key=lambda c: (-scores[c], order[c]))[0]
    top = sorted(scores, key=lambda c: -scores[c])[:5]
    if scores[best] <= 0:
        return None, top, scores
    return best, top, scores


SPAC = re.compile(r"acquisition (?:corp|company|holdings)|blank check|trust account"
                  r"|business combination", re.I)


# Is the filer the company BEING ACQUIRED (target) or the one ISSUING shares
# to pay for it (acquirer)? Both file DEFM14A. This is a property of the text,
# not of the outcome, so it cannot introduce survivorship.
PAT_TARGET = re.compile(
    r"converted into the right to receive|will be cancelled and converted"
    r"|become a wholly[ -]owned subsidiary of|you will (?:be entitled to )?receive\s*\$",
    re.I)
PAT_ISSUER = re.compile(
    r"share issuance proposal|issuance of shares of (?:our|the Company.s) common stock"
    r"|the Share Issuance", re.I)
# per-share cash consideration
PAT_PRICE = re.compile(
    r"\$\s?([0-9]{1,4}(?:\.[0-9]{1,4})?)\s*(?:in cash)?\s*,?\s*"
    r"(?:without interest\s*,?\s*)?(?:in cash\s*,?\s*)?"
    r"(?:per share|for each share|in cash per share|for each outstanding share)", re.I)
PAT_RIGHT = re.compile(
    r"right to receive\s*(?:an amount in cash equal to\s*)?\$\s?"
    r"([0-9]{1,4}(?:\.[0-9]{1,4})?)", re.I)


def _extract_features(text: str, name: str = "") -> dict:
    tk, alts, _ = _extract_ticker(text, name)
    prices = [float(m.group(1)) for m in PAT_PRICE.finditer(text)]
    prices += [float(m.group(1)) for m in PAT_RIGHT.finditer(text)]
    prices = [p for p in prices if 0.05 <= p <= 2000]
    deal_px = float(pd.Series(prices).mode().iloc[0]) if prices else None
    return {"ticker": tk, "alts": alts, "deal_px": deal_px,
            "n_price": len(prices),
            "target_hits": len(PAT_TARGET.findall(text)),
            "issuer_hits": len(PAT_ISSUER.findall(text)),
            "spac_hits": len(SPAC.findall(text)),
            "nchars": len(text)}


def stage_tickers(df: pd.DataFrame, verbose: bool = True) -> dict:
    """CIK -> ticker, read out of the earliest target merger filing. Outcome-blind."""
    cache = pickle.load(open(TICK_PKL, "rb")) if TICK_PKL.exists() else {}
    first = df.sort_values("date").groupby("cik").first()
    todo = [(int(cik), r["path"], r["name"]) for cik, r in first.iterrows()
            if int(cik) not in cache]
    if verbose:
        print(f"  tickers: {len(cache):,} cached, {len(todo):,} to fetch")

    def work(job):
        cik, path, name = job
        try:
            t = _head_text("https://www.sec.gov/Archives/" + path)
            return cik, _extract_features(t, name)
        except Exception as e:
            return cik, {"ticker": None, "alts": [], "err": type(e).__name__}

    done = 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for cik, res in ex.map(work, todo):
            cache[cik] = res
            done += 1
            if verbose and done % 250 == 0:
                print(f"    {done}/{len(todo)}")
                pickle.dump(cache, open(TICK_PKL, "wb"))
    pickle.dump(cache, open(TICK_PKL, "wb"))
    hit = sum(1 for v in cache.values() if v.get("ticker"))
    if verbose:
        print(f"  tickers: {hit:,}/{len(cache):,} extracted ({100*hit/max(len(cache),1):.1f}%)")
    return cache


# ----------------------------------------------------------- stage 3: announce

def stage_announce(ciks: list[int], verbose: bool = True) -> dict:
    """Earliest 8-K containing 'Agreement and Plan of Merger', per target CIK.

    This is the ANNOUNCEMENT anchor for the secondary specification. It is not
    used to select the sample — selection is the proxy filing — so a CIK with no
    such 8-K simply drops out of the secondary spec, not out of the study."""
    cache = pickle.load(open(ANN_PKL, "rb")) if ANN_PKL.exists() else {}
    todo = [c for c in ciks if c not in cache]
    if verbose:
        print(f"  announce: {len(cache):,} cached, {len(todo):,} to fetch")

    def work(cik):
        url = ("https://efts.sec.gov/LATEST/search-index?q=%22Agreement+and+Plan"
               f"+of+Merger%22&forms=8-K&ciks={cik:010d}")
        try:
            r = requests.get(url, headers=UA, timeout=60)
            if r.status_code != 200:
                return cik, {"err": r.status_code}
            hits = r.json()["hits"]["hits"]
            out = []
            for h in hits:
                s = h["_source"]
                out.append({"date": s["file_date"], "items": s.get("items") or []})
            return cik, {"hits": out}
        except Exception as e:
            return cik, {"err": type(e).__name__}

    done = 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for cik, res in ex.map(work, todo):
            cache[cik] = res
            done += 1
            if verbose and done % 250 == 0:
                print(f"    {done}/{len(todo)}")
                pickle.dump(cache, open(ANN_PKL, "wb"))
    pickle.dump(cache, open(ANN_PKL, "wb"))
    return cache


# ------------------------------------------------------- stage 4: corp actions

CA_TYPES = ("cash_merger", "stock_merger", "stock_and_cash_merger",
            "forward_split", "reverse_split", "unit_split")


def fetch_corpactions(symbols: list[str], verbose: bool = True) -> dict:
    """Alpaca corporate actions for the deal symbols: mergers (effective date and
    cash rate) and splits (for the split-repair guard)."""
    if CA_PKL.exists():
        ca = pickle.load(open(CA_PKL, "rb"))
        if set(symbols) <= set(ca.get("_asked", [])):
            if verbose:
                print(f"  corpactions: cached ({len(ca.get('mergers', {})):,} mergers)")
            return ca
    h = {"APCA-API-KEY-ID": config.ALPACA_API_KEY,
         "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY}
    mergers, splits = {}, {}
    syms = sorted(set(symbols))
    for i in range(0, len(syms), 100):
        chunk = syms[i:i + 100]
        tok = None
        while True:
            p = {"symbols": ",".join(chunk), "types": ",".join(CA_TYPES),
                 "start": START, "end": END, "limit": 1000}
            if tok:
                p["page_token"] = tok
            r = requests.get("https://data.alpaca.markets/v1/corporate-actions",
                             headers=h, params=p, timeout=90)
            if r.status_code != 200:
                print(f"  corpactions HTTP {r.status_code}: {r.text[:200]}")
                break
            j = r.json()
            for kind, arr in (j.get("corporate_actions") or {}).items():
                for a in arr:
                    s = a.get("acquiree_symbol") or a.get("symbol")
                    if not s:
                        continue
                    if "merger" in kind:
                        d = a.get("effective_date") or a.get("process_date")
                        if s not in mergers or d < mergers[s]["date"]:
                            mergers[s] = {"date": d, "kind": kind,
                                          "rate": a.get("rate"),
                                          "acquirer": a.get("acquirer_symbol")}
                    else:
                        splits.setdefault(s, []).append(
                            {"date": a.get("ex_date") or a.get("process_date"),
                             "old": a.get("old_rate"), "new": a.get("new_rate")})
            tok = j.get("next_page_token")
            if not tok:
                break
        if verbose and (i // 100) % 5 == 0:
            print(f"    corpactions {i + len(chunk)}/{len(syms)}")
    ca = {"mergers": mergers, "splits": splits, "_asked": syms}
    pickle.dump(ca, open(CA_PKL, "wb"))
    if verbose:
        print(f"  corpactions: {len(mergers):,} completed mergers, "
              f"{len(splits):,} symbols with splits")
    return ca


# ------------------------------------------------------------- price guards

def clean_series(px: pd.Series, splits: list[dict] | None,
                 merger_date: pd.Timestamp | None, freeze_run: int = 6,
                 gap_days: int = 15) -> pd.Series:
    """Apply the three documented guards. Returns a truncated, repaired close series."""
    s = px.dropna()
    if s.empty:
        return s

    # (2) reused ticker / spin-off: nothing after a confirmed merger effective date
    if merger_date is not None:
        s = s[s.index <= merger_date + pd.Timedelta(days=3)]
        if s.empty:
            return s

    # (3) frozen quotes: retire at the first run of >= 6 identical closes
    v = s.values
    run, start = 1, 0
    cut = None
    for i in range(1, len(v)) if freeze_run else ():
        if v[i] == v[i - 1]:
            run += 1
            if run >= freeze_run:
                cut = start
                break
        else:
            run, start = 1, i
    if cut is not None:
        s = s.iloc[:cut + 1]
    if len(s) < 2:
        return s

    # (2b) reused ticker without a merger corporate action: when a ticker is
    # retired and later re-issued to a different company there is a long hole in
    # the tape first. Truncate at the first gap of >= `gap_days` calendar days.
    if gap_days:
        holes = s.index.to_series().diff().dt.days
        big = np.where(holes.values > gap_days)[0]
        if len(big):
            s = s.iloc[:int(big[0])]
    if len(s) < 2:
        return s

    # (1) unadjusted splits: repair only jumps that match a declared split ratio
    if splits:
        r = s / s.shift(1)
        for sp in splits:
            try:
                d = pd.Timestamp(sp["date"]).tz_localize(s.index.tz)
                ratio = float(sp["new"]) / float(sp["old"])
            except Exception:
                continue
            near = r.index[(r.index >= d - pd.Timedelta(days=4)) &
                           (r.index <= d + pd.Timedelta(days=4))]
            for t in near:
                if abs(r.loc[t] * ratio - 1.0) < 0.06:      # unadjusted jump
                    s.loc[s.index >= t] = s.loc[s.index >= t] * ratio
                    r = s / s.shift(1)
                    break
    return s


# --------------------------------------------------------------- deal assembly

def build_deals(verbose: bool = True) -> pd.DataFrame:
    idx = stage_index(verbose=verbose)
    tick = stage_tickers(idx, verbose=verbose)

    first = idx.sort_values("date").groupby("cik").agg(
        name=("name", "first"), file_date=("date", "first"), form=("form", "first"),
        n_filings=("form", "size"))
    first["ticker"] = [tick.get(int(c), {}).get("ticker") for c in first.index]
    first["alts"] = [tick.get(int(c), {}).get("alts", []) for c in first.index]
    deals = first[first["ticker"].notna()].copy()
    deals.index.name = "cik"
    if verbose:
        print(f"  deals: {len(deals):,} with an extracted ticker "
              f"(of {len(first):,} target CIKs)")
    return deals.reset_index()


def load_px(symbols: list[str], verbose: bool = True) -> dict:
    """Bars through the SHARED cache, then snapshot the slice this lab needs.

    ~80 of the extracted tickers do not exist at the data vendor at all (dead
    OTC names, foreign lines). `bars.get` re-requests anything it has never
    seen, so those are asked for on every single run and eventually the whole
    request returns nothing and raises. The master cache is still the source of
    truth and is populated by the first call; this only avoids re-asking for
    tickers the vendor has already refused."""
    from . import bars
    if PX_PKL.exists():
        px = pickle.load(open(PX_PKL, "rb"))
        if set(symbols) <= set(px["_asked"]):
            if verbose:
                print(f"  prices: lab snapshot, {px['close'].shape}")
            return px
    want = sorted(set(symbols) | {"SPY"})
    try:
        px = bars.get(want, START, END, verbose=verbose)
    except RuntimeError:
        store = pd.read_pickle(bars.MASTER)
        have = [s for s in want if s in store["close"].columns]
        px = bars.get(have, START, END, verbose=verbose)
    px["_asked"] = want
    pickle.dump(px, open(PX_PKL, "wb"))
    return px


# --------------------------------------------------------------- statistics

def nw_t(x: np.ndarray, lag: int) -> tuple[float, float, float]:
    """mean, Newey-West SE, t. Lag must cover the overlap actually present."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return (float("nan"),) * 3
    mu = x.mean()
    e = x - mu
    g0 = (e @ e) / n
    s = g0
    for L in range(1, min(lag, n - 1) + 1):
        g = (e[L:] @ e[:-L]) / n
        s += 2 * (1 - L / (lag + 1)) * g
    s = max(s, 1e-18)
    se = math.sqrt(s / n)
    return mu, se, mu / se


def ols_alpha_beta(y: np.ndarray, x: np.ndarray, lag: int = 0):
    """y = a + b x. Returns alpha, beta, t(alpha), t(beta), R2, corr."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    n = len(y)
    if n < 10:
        return dict(alpha=np.nan, beta=np.nan, t_alpha=np.nan, t_beta=np.nan,
                    r2=np.nan, corr=np.nan, n=n)
    X = np.column_stack([np.ones(n), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    XtX_inv = np.linalg.inv(X.T @ X)
    if lag > 0:
        # Newey-West HAC
        S = np.zeros((2, 2))
        u = X * resid[:, None]
        S += u.T @ u
        for L in range(1, min(lag, n - 1) + 1):
            w = 1 - L / (lag + 1)
            G = u[L:].T @ u[:-L]
            S += w * (G + G.T)
        cov = XtX_inv @ S @ XtX_inv
    else:
        cov = XtX_inv * (resid @ resid) / max(n - 2, 1)
    se = np.sqrt(np.diag(cov))
    return dict(alpha=float(b[0]), beta=float(b[1]),
                t_alpha=float(b[0] / se[0]) if se[0] > 0 else np.nan,
                t_beta=float(b[1] / se[1]) if se[1] > 0 else np.nan,
                r2=float(1 - resid.var() / y.var()) if y.var() > 0 else np.nan,
                corr=float(np.corrcoef(y, x)[0, 1]), n=n)


def sharpe(r: np.ndarray, ppy: int = 252) -> float:
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if len(r) < 5 or r.std(ddof=1) == 0:
        return float("nan")
    return float(r.mean() / r.std(ddof=1) * math.sqrt(ppy))


# --------------------------------------------------------------- deal universe

SPAC_NAME = re.compile(r"\bacquisition (?:corp|co|company|holdings|inc)\b"
                       r"|\bcapital corp\b.*\bacquisition\b", re.I)


def ticker_is_namelike(name: str, ticker: str | None) -> bool:
    """Is `ticker` a letter-subsequence of the filer's own company name?

    US tickers are overwhelmingly built from the issuer's name (AMNB <-
    AMericaN Bankshares), so this is a cheap and OUTCOME-BLIND precision test
    that removes the systematic failure of the text extractor: in a
    stock-for-stock deal the ACQUIRER's symbol is quoted on the target's cover
    page ("Parent common stock trades under FHN"), and the acquirer's symbol
    is not a subsequence of the target's name. It costs real deals (a ticker
    unrelated to the name) and that cost is reported."""
    if not isinstance(ticker, str) or not ticker or not isinstance(name, str):
        return False
    letters = re.sub(r"[^A-Z]", "", name.upper())
    i = 0
    for ch in letters:
        if i < len(ticker) and ch == ticker[i]:
            i += 1
    return i == len(ticker)


def deal_universe(verbose: bool = True) -> pd.DataFrame:
    """One row per DEAL. Selection uses only properties of the filing itself."""
    idx = stage_index(verbose=verbose)
    feat = pickle.load(open(TICK_PKL, "rb"))

    # cluster a CIK's filings into deals: a new deal starts when a filing is
    # more than 365 days after the current cluster's first filing.
    rows = []
    for cik, g in idx.sort_values("date").groupby("cik"):
        anchor = None
        for _, r in g.iterrows():
            if anchor is None or (r["date"] - anchor["date"]).days > 365:
                anchor = r
                rows.append({"cik": int(cik), "name": r["name"], "t0": r["date"],
                             "form": r["form"], "path": r["path"]})
    d = pd.DataFrame(rows)
    f = pd.DataFrame.from_dict(feat, orient="index")
    for c in ("ticker", "deal_px", "target_hits", "issuer_hits", "spac_hits"):
        d[c] = d["cik"].map(f[c]) if c in f.columns else np.nan
    # features were read from each CIK's FIRST filing; later deals for the same
    # CIK inherit only the ticker, which is a company property, not a deal one.
    d.loc[d.groupby("cik").cumcount() > 0, ["deal_px", "target_hits",
                                            "issuer_hits", "spac_hits"]] = np.nan
    d["is_spac"] = (d["name"].str.contains(SPAC_NAME, na=False) |
                    (d["spac_hits"].fillna(0) > 50))
    d["namelike"] = [ticker_is_namelike(n, t)
                     for n, t in zip(d["name"], d["ticker"])]
    if verbose:
        print(f"  deal universe: {len(d):,} deal-clusters, "
              f"{d.ticker.notna().sum():,} with a ticker, "
              f"{int(d.is_spac.sum()):,} SPACs")
    return d


# ------------------------------------------------------------------- the sleeve

def build_book(deals: pd.DataFrame, close: pd.DataFrame, vol: pd.DataFrame,
               ca: dict, entry_offset: int = 1, max_hold: int = 252,
               min_dv: float = 1e6, min_px: float = 1.0, freeze_run: int = 6,
               use_ca_rate: bool = False, gap_days: int = 15,
               premium_band: tuple | None = (0.85, 3.0),
               verbose: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-deal outcomes and the daily equal-weight sleeve.

    NO LOOKAHEAD: the only date used to decide anything is t0 (the SEC filing
    date, public that day). Entry price is the close `entry_offset` sessions
    AFTER t0, and the first return counted is the session after THAT.
    Liquidity and price screens are computed on the 20 sessions ending at t0."""
    dates = close.index
    per_deal, series = [], {}
    for _, r in deals.iterrows():
        sym = r["ticker"]
        if sym not in close.columns:
            per_deal.append({**r, "drop": "no_bars"})
            continue
        mg = ca.get("mergers", {}).get(sym)
        mdate = pd.Timestamp(mg["date"]).tz_localize(dates.tz) if mg else None
        s = clean_series(close[sym], ca.get("splits", {}).get(sym), mdate,
                         freeze_run=freeze_run, gap_days=gap_days)
        if len(s) < 30:
            per_deal.append({**r, "drop": "short_series"})
            continue
        t0 = r["t0"].tz_localize(dates.tz) if r["t0"].tz is None else r["t0"]
        pre = s[s.index <= t0]
        if len(pre) < 20:
            per_deal.append({**r, "drop": "not_trading_at_t0"})
            continue
        dv = (close[sym] * vol[sym]).reindex(pre.index[-20:]).median()
        px0 = float(pre.iloc[-1])
        if not np.isfinite(dv) or dv < min_dv or px0 < min_px:
            per_deal.append({**r, "drop": "illiquid", "dv20": float(dv),
                             "px_t0": px0})
            continue
        # price-level sanity. An adjusted close of 635,895 (Telaria/RUBI) or
        # 6,710 (FFIE) is a reused ticker whose NEW owner later reverse-split,
        # rescaling the old company's whole history. No US common trades there.
        if not (0.5 <= px0 <= 2000):
            per_deal.append({**r, "drop": "price_level", "px_t0": px0})
            continue
        pre60 = pre.iloc[-60:]
        if float(pre60.max() / max(pre60.min(), 1e-9)) > 6:
            per_deal.append({**r, "drop": "prewindow_range", "px_t0": px0})
            continue
        # the workout definition itself: a stated terminal price that is a sane
        # multiple of the market price ON THE FILING DATE. Both numbers are
        # known at t0. It also throws out extraction garbage, where an exchange
        # RATIO of 1.0 was read as a $1.00 cash price.
        prem = (float(r["deal_px"]) / px0) if pd.notna(r.get("deal_px")) else np.nan
        if premium_band is not None and pd.notna(r.get("deal_px")):
            if not (premium_band[0] <= prem <= premium_band[1]):
                per_deal.append({**r, "drop": "premium_band", "px_t0": px0,
                                 "prem_ratio": prem})
                continue
        post = s[s.index > t0]
        if len(post) < entry_offset + 2:
            per_deal.append({**r, "drop": "no_post_bars"})
            continue
        ei = entry_offset - 1
        entry_date, entry_px = post.index[ei], float(post.iloc[ei])
        hold = post.iloc[ei:ei + max_hold + 1]
        exit_date, exit_px = hold.index[-1], float(hold.iloc[-1])
        n_td = len(hold) - 1
        if use_ca_rate and mg and mg.get("rate") and n_td < max_hold:
            # variant only: settle a completed CASH merger at the cash actually
            # paid rather than the last tape print. Deliberately NOT the
            # headline: `rate` exists only for deals that closed, so preferring
            # it improves exactly the completed subset.
            try:
                exit_px = float(mg["rate"])
            except (TypeError, ValueError):
                pass
        if n_td < 2:
            per_deal.append({**r, "drop": "no_holding_period"})
            continue
        # a 10x range inside a one-year merger window is a split/spin-off/reuse
        # artifact, not a deal outcome: the worst real break loses ~80%.
        if float(hold.max() / max(hold.min(), 1e-9)) > 10:
            per_deal.append({**r, "drop": "window_range"})
            continue
        ret = exit_px / entry_px - 1.0
        # descriptive only, never used for selection: did the tape end?
        last_bar = s.index[-1]
        completed = bool(mg) or (last_bar <= hold.index[-1] + pd.Timedelta(days=5)
                                 and last_bar < dates[-1] - pd.Timedelta(days=15))
        censored = (n_td >= max_hold) or (exit_date >= dates[-1] - pd.Timedelta(days=5)
                                          and not completed)
        per_deal.append({**r, "drop": None, "entry_date": entry_date,
                         "entry_px": entry_px, "exit_date": exit_date,
                         "exit_px": exit_px, "n_td": n_td, "ret": ret,
                         "ann": (1 + ret) ** (252 / max(n_td, 1)) - 1,
                         "dv20": float(dv), "px_t0": px0,
                         "completed": completed, "censored": censored,
                         "merger_ca": bool(mg), "premium": prem - 1.0})
        series[f"{sym}|{r['cik']}|{r['t0'].date()}"] = hold.pct_change().iloc[1:]

    pd_df = pd.DataFrame(per_deal)
    book = pd.DataFrame(series).reindex(dates)
    if verbose and "drop" in pd_df:
        print("  build_book drops:", pd_df["drop"].value_counts(dropna=False).to_dict())
    return pd_df, book


def sleeve_returns(book: pd.DataFrame) -> pd.Series:
    """Equal weight across the deals live that day; flat (0) when none are."""
    r = book.mean(axis=1, skipna=True)
    return r.fillna(0.0)


# ------------------------------------------------------------------ experiment

def describe(r: pd.Series, bench: pd.Series, label: str, lag: int = 10) -> dict:
    r = r.reindex(bench.index).fillna(0.0)
    ab = ols_alpha_beta(r.values, bench.values, lag=lag)
    mu, se, t = nw_t(r.values, lag)
    out = {"label": label, "n_days": int(len(r)),
           "ann_ret_pct": 100 * float(r.mean()) * 252,
           "ann_vol_pct": 100 * float(r.std(ddof=1)) * math.sqrt(252),
           "sharpe": sharpe(r.values), "t_mean_nw": float(t),
           "beta_spy": ab["beta"], "corr_spy": ab["corr"],
           "alpha_ann_pct": 100 * ab["alpha"] * 252,
           "t_alpha_nw": ab["t_alpha"],
           "skew_daily": float(pd.Series(r).skew()),
           "max_dd_pct": 100 * float(((1 + r).cumprod() /
                                      (1 + r).cumprod().cummax() - 1).min())}
    return out


def split_stats(r: pd.Series, bench: pd.Series, k: int, tag: str) -> list[dict]:
    n = len(r)
    edges = [int(round(i * n / k)) for i in range(k + 1)]
    out = []
    for i in range(k):
        sl = slice(edges[i], edges[i + 1])
        out.append(describe(r.iloc[sl], bench.iloc[sl],
                            f"{tag}{i+1}/{k} {r.index[edges[i]].date()}..{r.index[edges[i+1]-1].date()}"))
    return out


def cost_drag(book: pd.DataFrame, bps: float) -> pd.Series:
    """Round-trip slippage charged on the day a deal enters and the day it exits,
    at that day's equal weight."""
    live = book.notna()
    n = live.sum(axis=1).replace(0, np.nan)
    first = live & (~live.shift(1, fill_value=False))
    last = live & (~live.shift(-1, fill_value=False))
    hits = (first.astype(float) + last.astype(float)).sum(axis=1)
    return (hits * (bps / 1e4) / n).fillna(0.0)


def stage_tickers_fallback(idx: pd.DataFrame, verbose: bool = True) -> dict:
    """Second pass for CIKs whose FIRST filing yielded no ticker.

    SC 14D9 cover pages do not state a trading symbol at all (verified on
    BKS / MBLY / CERE / ETNB: zero matches even in the first 1.5 MB), so a
    CIK whose earliest merger document is a 14D9 needs its NEXT filing tried.
    This is a parsing retry, not a selection rule: it cannot see the outcome."""
    cache = pickle.load(open(TICK_PKL, "rb"))
    need = {c for c, v in cache.items() if not v.get("ticker")}
    todo = []
    for cik, g in idx.sort_values("date").groupby("cik"):
        if int(cik) not in need or len(g) < 2:
            continue
        first_path = g.iloc[0]["path"]
        alt = g[g["path"] != first_path]
        alt = alt[alt["form"] != g.iloc[0]["form"]]
        if alt.empty:
            alt = g[g["path"] != first_path]
        if not alt.empty:
            todo.append((int(cik), alt.iloc[0]["path"], alt.iloc[0]["name"]))
    if verbose:
        print(f"  ticker fallback: {len(todo):,} CIKs to retry")

    def work(job):
        cik, path, name = job
        try:
            return cik, _extract_features(_head_text(
                "https://www.sec.gov/Archives/" + path), name)
        except Exception as e:
            return cik, {"ticker": None, "err": type(e).__name__}

    fixed = 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for cik, res in ex.map(work, todo):
            if res.get("ticker"):
                old = cache[cik]
                res["target_hits"] = max(res.get("target_hits", 0),
                                         old.get("target_hits", 0) or 0)
                cache[cik] = res
                fixed += 1
    pickle.dump(cache, open(TICK_PKL, "wb"))
    if verbose:
        print(f"  ticker fallback: recovered {fixed:,}")
    return cache


def stage_tickers_tender(idx: pd.DataFrame, verbose: bool = True) -> dict:
    """Third pass, aimed squarely at tender offers.

    An SC 14D9 cover page never states a trading symbol, so a target whose only
    merger document is a 14D9 has no ticker and would drop out — and tender
    offers are the FAST, high-completion end of the deal distribution, so
    losing them is a real distortion. The bidder's SC TO-T ('Offer to
    Purchase') does state it, and EDGAR indexes the TO-T under the SUBJECT
    company's CIK, so it is reachable in one search per target."""
    cache = pickle.load(open(TICK_PKL, "rb"))
    need = sorted({int(c) for c, v in cache.items() if not v.get("ticker")})
    if verbose:
        print(f"  tender fallback: {len(need):,} CIKs still without a ticker")
    names = idx.sort_values("date").groupby("cik")["name"].first().to_dict()

    def work(cik):
        try:
            u = ("https://efts.sec.gov/LATEST/search-index?q=%22Offer+to+Purchase%22"
                 f"&forms=SC+TO-T&ciks={cik:010d}")
            r = requests.get(u, headers=UA, timeout=60)
            hits = r.json()["hits"]["hits"] if r.status_code == 200 else []
            if not hits:
                return cik, None
            h = sorted(hits, key=lambda x: x["_source"]["file_date"])[0]
            acc, doc = h["_id"].split(":", 1)
            url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                   f"{acc.replace('-', '')}/{doc}")
            return cik, _extract_features(_head_text(url), names.get(cik, ""))
        except Exception:
            return cik, None

    fixed = 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for cik, res in ex.map(work, need):
            if res and res.get("ticker"):
                old = cache[cik]
                res["target_hits"] = max(res.get("target_hits", 0) or 0,
                                         old.get("target_hits", 0) or 0)
                cache[cik] = res
                fixed += 1
    pickle.dump(cache, open(TICK_PKL, "wb"))
    if verbose:
        print(f"  tender fallback: recovered {fixed:,}")
    return cache


def run_experiment(min_dv: float = 1e6, max_hold: int = 252,
                   entry_offset: int = 1, require_cash: bool = True,
                   require_8k: bool = True, ann_lag: tuple = (0, 120),
                   premium_band: tuple = (0.8, 2.5),
                   verbose: bool = True) -> dict:
    from . import bars, growth

    deals = deal_universe(verbose=verbose)
    d = deals[deals["ticker"].notna() & (~deals["is_spac"])].copy()
    steps = [("start", len(d))]
    # Every filter below is a property of the FILING or of pre-t0 prices.
    # None of them can see whether the deal closed.
    d = d[(d["target_hits"].fillna(0) >= 1) | d["target_hits"].isna()]
    steps.append(("filer's own shares convert (target, not acquirer)", len(d)))
    d = d[(d["issuer_hits"].fillna(0) == 0)]
    steps.append(("not a share-ISSUANCE proxy (drops acquirer-side)", len(d)))
    d = d[d["namelike"]]
    steps.append(("ticker is a subsequence of the filer's name", len(d)))
    if require_cash:
        d = d[d["deal_px"].notna()]
        steps.append(("a fixed per-share cash price in the text", len(d)))
    if require_8k:
        ann = stage_announce(sorted(d["cik"].unique().tolist()), verbose=False)
        a0, lag = [], []
        for _, r in d.iterrows():
            hits = (ann.get(int(r["cik"])) or {}).get("hits") or []
            ds = sorted(pd.Timestamp(h["date"]) for h in hits)
            ds = [x for x in ds if x <= r["t0"]]
            a0.append(ds[-1] if ds else pd.NaT)
        d = d.assign(ann_date=a0)
        d["lag_days"] = (d["t0"] - d["ann_date"]).dt.days
        d = d[d["lag_days"].between(*ann_lag)]
        steps.append((f"a merger 8-K {ann_lag[0]}-{ann_lag[1]}d before the proxy", len(d)))
    sel = d.copy()
    if verbose:
        print("  selection funnel (all filters known at t0):")
        for k, v in steps:
            print(f"    {v:6,d}  {k}")
    syms = sorted(sel["ticker"].unique())

    px = load_px(syms, verbose=verbose)
    close, vol = px["close"], px["volume"]
    ca = fetch_corpactions([s for s in syms if s in close.columns], verbose=verbose)

    pdl, book = build_book(sel, close, vol, ca, entry_offset=entry_offset,
                           max_hold=max_hold, min_dv=min_dv,
                           premium_band=premium_band, verbose=verbose)
    live = pdl[pdl["drop"].isna()].copy()
    for c in ("completed", "censored", "merger_ca"):
        live[c] = live[c].astype(bool)
    for c in ("ret", "ann", "n_td", "dv20", "px_t0", "entry_px", "exit_px"):
        live[c] = pd.to_numeric(live[c], errors="coerce")
    spy = close["SPY"].pct_change().reindex(close.index).fillna(0.0)
    sleeve = sleeve_returns(book)
    return {"deals": deals, "sel": sel, "per_deal": pdl, "live": live,
            "book": book, "sleeve": sleeve, "spy": spy, "close": close,
            "vol": vol, "ca": ca}


# ---------------------------------------------------------------- controls

def book_from_windows(windows, close: pd.DataFrame) -> pd.DataFrame:
    """windows: list of (symbol, entry_date, exit_date). Returns a deal-by-day
    return frame with the same shape convention as build_book."""
    series = {}
    for i, (sym, a, b) in enumerate(windows):
        if sym not in close.columns:
            continue
        s = close[sym].loc[a:b].dropna()
        if len(s) < 3:
            continue
        series[f"{sym}|{i}"] = s.pct_change().iloc[1:]
    return pd.DataFrame(series).reindex(close.index)


def random_control(live: pd.DataFrame, close: pd.DataFrame, dvroll: pd.DataFrame,
                   pool: list[str], seed: int) -> pd.DataFrame:
    """A random stock from the same eligible pool, matched on dollar-volume
    quintile at entry, held over the IDENTICAL calendar window.

    The pool is the current S&P 1500, which is survivorship-favoured; that
    makes this control HARDER to beat, never easier."""
    rng = np.random.default_rng(seed)
    have = close[pool].notna()
    dvp = dvroll[pool]
    windows = []
    for _, r in live.iterrows():
        a, b = r["entry_date"], r["exit_date"]
        if a not in have.index or b not in have.index:
            continue
        ok = have.loc[a] & have.loc[b]
        cands = np.array(pool)[ok.values]
        if len(cands) == 0:
            continue
        dv_here = dvp.loc[a, cands]
        good = dv_here.dropna()
        same = cands
        if len(good) >= 25:
            edges = np.nanquantile(good.values, [.2, .4, .6, .8])
            mine = int(np.searchsorted(edges, r["dv20"]))
            their = np.searchsorted(edges, dv_here.values)
            pick = cands[(their == mine) & np.isfinite(dv_here.values)]
            if len(pick) >= 3:
                same = pick
        windows.append((str(rng.choice(same)), a, b))
    return book_from_windows(windows, close)


def placebo_control(live: pd.DataFrame, close: pd.DataFrame,
                    shift_td: int = 250) -> pd.DataFrame:
    """Same tickers, same holding LENGTH, but the window is moved `shift_td`
    sessions EARLIER — long before the merger agreement existed. Isolates
    'is it the event, or is it these names?'"""
    idx = close.index
    windows = []
    for _, r in live.iterrows():
        try:
            i0 = idx.get_loc(r["entry_date"])
            i1 = idx.get_loc(r["exit_date"])
        except KeyError:
            continue
        j0, j1 = i0 - shift_td, i1 - shift_td
        if j0 < 0:
            continue
        windows.append((r["ticker"], idx[j0], idx[j1]))
    return book_from_windows(windows, close)


def announcement_dates(sel: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Secondary anchor: the target's own merger 8-K.

    THIS SPEC HAS A HOLE AND IT IS STATED RATHER THAN HIDDEN. A deal that dies
    between announcement and the first proxy never generates a proxy, so it is
    absent from the sample while its (usually bad) return would have been
    inside an announcement-anchored book. The proxy-anchored spec has no such
    hole, which is why it is the primary."""
    s = sel.copy()
    s["t0_filing"] = s["t0"]
    s["t0"] = s["ann_date"]
    keep = s[s["t0"].notna()].copy()
    if verbose:
        print(f"  announcement anchor: {len(keep):,}/{len(s):,} deals; median lag "
              f"announcement -> proxy {keep['lag_days'].median():.0f} days")
    return keep


def fmt(d: dict) -> str:
    return (f"{d['label'][:44]:<44} ret {d['ann_ret_pct']:7.2f}%  vol {d['ann_vol_pct']:6.2f}%"
            f"  SR {d['sharpe']:6.3f}  beta {d['beta_spy']:6.3f}  rho {d['corr_spy']:6.3f}"
            f"  alpha {d['alpha_ann_pct']:7.2f}%  t {d['t_alpha_nw']:6.2f}"
            f"  dd {d['max_dd_pct']:7.1f}%")


def report(res: dict, n_trials: int, verbose: bool = True) -> dict:
    from . import growth
    live, book, sleeve, spy = res["live"], res["book"], res["sleeve"], res["spy"]
    close, vol = res["close"], res["vol"]
    out: dict = {}
    P = print if verbose else (lambda *a, **k: None)

    # ---------------------------------------------------------------- sample
    idx_all = stage_index(verbose=False)
    P("\n" + "=" * 118)
    P("SAMPLE — assembled from TARGET-FILED merger documents, never from outcomes")
    P("=" * 118)
    d = res["deals"]
    P(f"  SEC filings scanned          {len(idx_all):,}  ({idx_all.form.value_counts().to_dict()})")
    P(f"  deal clusters                {len(d):,} over {d.cik.nunique():,} CIKs")
    P(f"  ticker extracted from text   {d.ticker.notna().sum():,}")
    P(f"  SPAC/blank-check excluded    {int(d.is_spac.sum()):,}")
    P(f"  candidate deals              {len(res['sel']):,}")
    P(f"  drops: {res['per_deal']['drop'].value_counts(dropna=False).to_dict()}")
    P(f"  FINAL SAMPLE                 {len(live):,} deals, "
      f"{live.entry_date.min().date()} .. {live.entry_date.max().date()}")
    P(f"  forms: {live.form.value_counts().to_dict()}")
    known_breaks = ["RAD", "TRCO", "TGNA", "FHN", "ACI", "ROG", "NXPI", "SPWH",
                    "PACB", "BATL", "USM", "CBRL"]
    got = [t for t in known_breaks if t in set(live["ticker"])]
    P(f"  SURVIVORSHIP PROOF — famous BROKEN/BLOCKED deals present in the sample: "
      f"{got}")
    out["broken_deals_present"] = got
    P(f"  completed {int(live.completed.sum()):,} | not completed within the cap "
      f"{int((~live.completed).sum()):,} | still open at data end {int(live.censored.sum()):,}")
    out["sample"] = {"filings": int(len(idx_all)), "clusters": int(len(d)),
                     "candidates": int(len(res["sel"])), "n_deals": int(len(live)),
                     "completed": int(live.completed.sum()),
                     "not_completed": int((~live.completed).sum()),
                     "forms": {k: int(v) for k, v in live.form.value_counts().items()},
                     "first": str(live.entry_date.min().date()),
                     "last": str(live.entry_date.max().date())}

    # -------------------------------------------------------------- per deal
    P("\n" + "=" * 118)
    P("PER-DEAL OUTCOMES — buy the target at (filing + 1) close, hold to delist / termination / 252-td cap")
    P("=" * 118)
    r = live["ret"].values
    P(f"  n={len(r)}  mean {100*r.mean():+.2f}%  median {100*np.median(r):+.2f}%  "
      f"sd {100*r.std(ddof=1):.2f}%  skew {float(pd.Series(r).skew()):+.2f}  "
      f"kurt {float(pd.Series(r).kurt()):+.2f}")
    P(f"  mean hold {live.n_td.mean():.0f} td (median {live.n_td.median():.0f})   "
      f"win rate {100*(r > 0).mean():.1f}%")
    br = live[live["ret"] < -0.10]
    P(f"  BREAK TAIL: {len(br)} deals lost >10% ({100*len(br)/len(live):.1f}%), "
      f"mean loss {100*br['ret'].mean():.2f}%, worst {100*r.min():.2f}%")
    cmp_, notc = live[live.completed], live[~live.completed]
    P(f"  completed  n={len(cmp_):3d} mean {100*cmp_.ret.mean():+.2f}% hold {cmp_.n_td.mean():.0f} td")
    P(f"  NOT compl. n={len(notc):3d} mean {100*notc.ret.mean():+.2f}% hold {notc.n_td.mean():.0f} td")
    out["per_deal"] = {"n": int(len(r)), "mean_pct": 100 * float(r.mean()),
                       "median_pct": 100 * float(np.median(r)),
                       "sd_pct": 100 * float(r.std(ddof=1)),
                       "skew": float(pd.Series(r).skew()),
                       "kurt": float(pd.Series(r).kurt()),
                       "win_rate_pct": 100 * float((r > 0).mean()),
                       "mean_hold_td": float(live.n_td.mean()),
                       "break_rate_pct": 100 * len(br) / len(live),
                       "loss_given_break_pct": 100 * float(br["ret"].mean()) if len(br) else None,
                       "worst_pct": 100 * float(r.min()),
                       "completed_mean_pct": 100 * float(cmp_.ret.mean()) if len(cmp_) else None,
                       "not_completed_mean_pct": 100 * float(notc.ret.mean()) if len(notc) else None}

    # ---------------------------------------------------------------- sleeve
    P("\n" + "=" * 118)
    P("THE SLEEVE — equal weight across deals live that day, cash when none. Rule 13 on every line.")
    P("=" * 118)
    base = describe(sleeve, spy, "WORKOUT sleeve (gross)")
    P("  " + fmt(base))
    P("  " + fmt(describe(spy, spy, "SPY buy-and-hold")))
    nlive = book.notna().sum(axis=1)
    P(f"  avg live deals {nlive.mean():.1f} (max {int(nlive.max())}), "
      f"invested on {100*(nlive > 0).mean():.1f}% of sessions")
    out["sleeve_gross"] = base
    out["spy"] = describe(spy, spy, "SPY")
    out["avg_live"] = float(nlive.mean())
    out["pct_days_invested"] = float(100 * (nlive > 0).mean())

    # -------------------------------------------------------------- controls
    P("\n" + "=" * 118)
    P("CONTROLS")
    P("=" * 118)
    pool = [s for s in pd.read_csv(config.UNIVERSE_CSV)["symbol"] if s in close.columns]
    dvroll = (close[pool] * vol[pool]).rolling(20).mean()
    ctrl_series, ctrl_rows = [], []
    for seed in range(8):
        cb = random_control(live, close, dvroll, pool, seed)
        cr = sleeve_returns(cb)
        ctrl_series.append(cr)
        ctrl_rows.append(describe(cr, spy, f"random pick seed {seed}"))
    cavg = pd.concat(ctrl_series, axis=1).mean(axis=1)
    P("  " + fmt(describe(cavg, spy, "CONTROL random S&P1500 pick, same windows")))
    P(f"     across 8 seeds: ann ret {np.mean([c['ann_ret_pct'] for c in ctrl_rows]):+.2f}% "
      f"+/- {np.std([c['ann_ret_pct'] for c in ctrl_rows]):.2f}, "
      f"Sharpe {np.mean([c['sharpe'] for c in ctrl_rows]):.3f}")
    pb = sleeve_returns(placebo_control(live, close, 250))
    P("  " + fmt(describe(pb, spy, "CONTROL placebo: same names, 250 td earlier")))
    spywin = sleeve_returns(book_from_windows(
        [("SPY", r["entry_date"], r["exit_date"]) for _, r in live.iterrows()], close))
    P("  " + fmt(describe(spywin, spy, "CONTROL SPY over the identical windows")))
    P("  --- DIFFERENCES (Rule 13: risk-adjust the difference, not only the levels)")
    for nm, c in (("random pick", cavg), ("placebo", pb), ("SPY windows", spywin)):
        P("  " + fmt(describe(sleeve - c, spy, f"workout MINUS {nm}")))
    out["control_random"] = describe(cavg, spy, "random")
    out["control_placebo"] = describe(pb, spy, "placebo")
    out["control_spywin"] = describe(spywin, spy, "spy_windows")
    out["diff_random"] = describe(sleeve - cavg, spy, "workout-random")
    out["diff_placebo"] = describe(sleeve - pb, spy, "workout-placebo")
    out["diff_spywin"] = describe(sleeve - spywin, spy, "workout-spywindows")

    # ------------------------------------------------------- halves / thirds
    P("\n" + "=" * 118)
    P("BOTH HALVES, EQUAL THIRDS, AND 2020 (the era checks that killed H22)")
    P("=" * 118)
    for row in split_stats(sleeve, spy, 2, "half "):
        P("  " + fmt(row))
    for row in split_stats(sleeve, spy, 3, "third "):
        P("  " + fmt(row))
    out["halves"] = split_stats(sleeve, spy, 2, "half ")
    out["thirds"] = split_stats(sleeve, spy, 3, "third ")
    for a, b, tag in (("2020-02-19", "2020-03-23", "COVID crash"),
                      ("2020-03-24", "2020-06-30", "COVID recovery"),
                      ("2020-01-01", "2020-12-31", "all of 2020")):
        m = (sleeve.index >= a) & (sleeve.index <= b)
        s_, y_ = sleeve[m], spy[m]
        P(f"  {tag:<16} {a}..{b}  sleeve {100*((1+s_).prod()-1):+7.2f}%   "
          f"SPY {100*((1+y_).prod()-1):+7.2f}%   n={int(m.sum())} sessions, "
          f"live deals avg {nlive[m].mean():.1f}")
        out[f"window_{tag.replace(' ', '_')}"] = {
            "sleeve_pct": 100 * float((1 + s_).prod() - 1),
            "spy_pct": 100 * float((1 + y_).prod() - 1)}
    d20 = live[(live.entry_date >= "2019-06-01") & (live.entry_date <= "2020-03-31")]
    if len(d20):
        P(f"  deals live into the crash (entered 2019-06..2020-03): n={len(d20)}, "
          f"mean {100*d20.ret.mean():+.2f}%, worst {100*d20.ret.min():+.2f}%, "
          f"break rate {100*(d20.ret < -0.10).mean():.1f}%")
        out["crash_cohort"] = {"n": int(len(d20)), "mean_pct": 100 * float(d20.ret.mean()),
                               "worst_pct": 100 * float(d20.ret.min()),
                               "break_rate_pct": 100 * float((d20.ret < -0.10).mean())}

    # ------------------------------------------------------------------ cost
    P("\n" + "=" * 118)
    P("COSTS — round-trip slippage charged on the entry and exit sessions at that day's weight")
    P("=" * 118)
    rows = []
    for bps in (0, 10, 25, 50, 100, 200):
        net = sleeve - cost_drag(book, bps)
        row = describe(net, spy, f"net of {bps} bps per side")
        rows.append({"bps": bps, **row})
        P("  " + fmt(row))
    xs = np.array([r["bps"] for r in rows], float)

    def breakeven(ys: np.ndarray) -> float:
        # ys decreases in bps, so -ys increases and is a valid np.interp xp
        if ys[0] <= 0:
            return 0.0
        if ys[-1] > 0:
            return float("inf")
        return float(np.interp(0.0, -ys, xs))

    be_ret = breakeven(np.array([r["ann_ret_pct"] for r in rows], float))
    be_alpha = breakeven(np.array([r["alpha_ann_pct"] for r in rows], float))
    P(f"  BREAK-EVEN cost: total return zero at {be_ret:.0f} bps/side; "
      f"market-adjusted alpha zero at {be_alpha:.0f} bps/side")
    out["costs"] = rows
    out["breakeven_bps_return"] = be_ret
    out["breakeven_bps_alpha"] = be_alpha

    # ------------------------------------------------- entry phases (Rule 9)
    P("\n" + "=" * 118)
    P("RULE 9 — pooled across entry timing (offset in sessions after the SEC filing)")
    P("=" * 118)
    ph = []
    for off in (1, 2, 3, 5, 8, 13, 21):
        pdl2, bk2 = build_book(res["sel"], close, vol, res["ca"], entry_offset=off,
                               verbose=False)
        s2 = sleeve_returns(bk2)
        l2 = pdl2[pdl2["drop"].isna()]
        row = describe(s2, spy, f"entry = filing + {off} sessions")
        row["n_deals"] = int(len(l2))
        row["mean_deal_pct"] = 100 * float(l2["ret"].mean())
        ph.append(row)
        P("  " + fmt(row) + f"  n={row['n_deals']} mean/deal {row['mean_deal_pct']:+.2f}%")
    out["entry_phases"] = ph

    # ---------------------------------------------- deflated Sharpe, Rule 16
    P("\n" + "=" * 118)
    P("SIGNIFICANCE")
    P("=" * 118)
    sr_d = float(np.mean(sleeve)) / float(np.std(sleeve, ddof=1))
    dsr = growth.deflated_sharpe(sr_d, n_trials=n_trials, n_obs=len(sleeve),
                                 skew=float(sleeve.skew()),
                                 kurtosis=float(sleeve.kurt() + 3.0))
    P(f"  daily Sharpe {sr_d:.4f} (annualised {base['sharpe']:.3f}), "
      f"skew {sleeve.skew():+.2f}, excess kurt {sleeve.kurt():+.1f}")
    P(f"  deflated Sharpe at N={n_trials}: {dsr:.4f}")
    boots = []
    for seed in (11, 12, 13):
        rng = np.random.default_rng(seed)
        v = sleeve.values
        L, nb = 21, 4000
        ts = []
        for _ in range(nb):
            starts = rng.integers(0, len(v) - L, size=len(v) // L)
            samp = np.concatenate([v[s:s + L] for s in starts])
            ts.append(samp.mean() / (samp.std(ddof=1) / math.sqrt(len(samp))))
        boots.append(float(np.mean(ts)))
    P(f"  block bootstrap t (L=21, 4000 reps): {np.mean(boots):.3f}, "
      f"Monte-Carlo sd across 3 seeds {np.std(boots):.3f}   [Rule 16]")
    out["deflated_sharpe"] = float(dsr)
    out["daily_sharpe"] = sr_d
    out["boot_t_mean"] = float(np.mean(boots))
    out["boot_t_mc_sd"] = float(np.std(boots))
    out["n_trials"] = n_trials

    # -------------------------------------------------------------- capacity
    P("\n" + "=" * 118)
    P("CAPACITY")
    P("=" * 118)
    dv = live["dv20"]
    P(f"  target 20d dollar volume at filing: median ${dv.median()/1e6:.1f}M, "
      f"25th ${dv.quantile(.25)/1e6:.1f}M, 10th ${dv.quantile(.10)/1e6:.1f}M")
    P(f"  at 1% of ADV over 5 sessions and {nlive.mean():.0f} concurrent names, "
      f"book capacity ~ ${nlive.mean()*0.05*dv.median()/1e6:.1f}M")
    out["capacity"] = {"median_dv_musd": float(dv.median() / 1e6),
                       "p10_dv_musd": float(dv.quantile(.10) / 1e6),
                       "book_capacity_musd": float(nlive.mean() * 0.05 * dv.median() / 1e6)}

    # ------------------------------- does it help a portfolio that owns SPY?
    P("\n" + "=" * 118)
    P("THE ONLY QUESTION THAT MATTERS HERE — does a low-beta sleeve improve a book that already owns SPY?")
    P("=" * 118)
    ss, sy = describe(sleeve, spy, "x")["sharpe"], out["spy"]["sharpe"]
    rho = base["corr_spy"]
    corr = [[1.0, rho], [rho, 1.0]]
    best = growth.best_long_only_sharpe([sy, ss], corr)
    P(f"  SPY Sharpe {sy:.3f} | sleeve Sharpe {ss:.3f} | correlation {rho:.3f}")
    P(f"  best long-only risk-weighted combination: {best:.3f}  "
      f"(gain over SPY alone {best - sy:+.3f})")
    for bps in (10, 25, 50):
        sn = describe(sleeve - cost_drag(book, bps), spy, "x")["sharpe"]
        b2 = growth.best_long_only_sharpe([sy, sn], corr)
        P(f"  net of {bps:3d} bps/side: sleeve {sn:.3f} -> combination {b2:.3f} "
          f"({b2 - sy:+.3f} vs SPY)")
        out[f"combo_{bps}bps"] = float(b2)
    out["combo_gross"] = float(best)
    out["combo_gain_gross"] = float(best - sy)
    return out


def variants(res: dict, verbose: bool = True) -> list[dict]:
    """Every specification actually run, reported whether it helps or not."""
    close, vol, ca, spy, sel = (res["close"], res["vol"], res["ca"],
                                res["spy"], res["sel"])
    rows = []

    def run(label, **kw):
        selx = kw.pop("sel", sel)
        if len(selx) == 0:
            if verbose:
                print(f"  {label[:44]:<44} EMPTY — no deals meet this spec")
            return None
        pdl, bk = build_book(selx, close, vol, ca, verbose=False, **kw)
        l = pdl[pdl["drop"].isna()].copy()
        if len(l):
            l["ret"] = pd.to_numeric(l["ret"], errors="coerce")
        s = sleeve_returns(bk)
        d = describe(s, spy, label)
        d["n_deals"] = int(len(l))
        d["mean_deal_pct"] = 100 * float(l["ret"].mean()) if len(l) else np.nan
        d["break_rate_pct"] = 100 * float((l["ret"] < -0.10).mean()) if len(l) else np.nan
        d["deal_skew"] = float(l["ret"].skew()) if len(l) else np.nan
        rows.append(d)
        if verbose:
            print("  " + fmt(d) + f"  n={d['n_deals']:4d} deal {d['mean_deal_pct']:+6.2f}%"
                  f" brk {d['break_rate_pct']:4.1f}% skew {d['deal_skew']:+5.2f}")
        return d

    if verbose:
        print("\n" + "=" * 118)
        print("EVERY VARIANT RUN")
        print("=" * 118)
    run("V1  PRIMARY  proxy anchor, +1, 252td, $1M, freeze6")
    run("V2  liquidity $10M (retail-tradeable)", min_dv=1e7)
    run("V3  liquidity $50M", min_dv=5e7)
    run("V4  no liquidity screen", min_dv=0.0, min_px=0.0)
    run("V5  max hold 63 td", max_hold=63)
    run("V6  max hold 126 td", max_hold=126)
    run("V7  max hold 504 td", max_hold=504)
    run("V8  freeze guard 10 (looser)", freeze_run=10)
    run("V9  NO freeze guard", freeze_run=0)
    run("V10 cash settled at the CA rate", use_ca_rate=True)
    run("V11 SC 14D9 tender offers only", sel=sel[sel.form == "SC 14D9"])
    run("V12 proxy forms only (no tenders)", sel=sel[sel.form != "SC 14D9"])
    px_ok = sel["deal_px"].notna()
    run("V13 a per-share cash price in the text", sel=sel[px_ok])
    run("V14 no cash price found in the text", sel=sel[~px_ok])
    run("V15 2016-2020 entries only",
        sel=sel[sel.t0 < "2021-01-01"])
    run("V16 2021-2026 entries only",
        sel=sel[sel.t0 >= "2021-01-01"])
    run("V17 no premium-band guard", premium_band=None)
    run("V18 tight premium band 1.00-1.15", premium_band=(1.0, 1.15))
    run("V19 wide spreads only, 1.15-2.5", premium_band=(1.15, 2.5))
    run("V20 NO reused-ticker gap guard", gap_days=0)
    if "ann_date" in sel.columns:
        s2 = sel.copy()
        s2["t0"] = s2["ann_date"]
        run("V21 ANNOUNCEMENT (8-K) anchor, not the proxy", sel=s2)
    return rows


def spec_variants(n_start: int = 21, verbose: bool = True) -> list[dict]:
    """Variants that change the SAMPLE, so the whole pipeline is re-run."""
    rows = []
    specs = [("S1 no cash-price requirement", dict(require_cash=False)),
             ("S2 no 8-K requirement", dict(require_8k=False)),
             ("S3 8-K lag window 0-365d", dict(ann_lag=(0, 365))),
             ("S4 8-K lag window 0-60d", dict(ann_lag=(0, 60))),
             ("S5 liquidity $10M", dict(min_dv=1e7))]
    for i, (label, kw) in enumerate(specs):
        r = run_experiment(verbose=False, **kw)
        s = r["sleeve"]
        l = r["live"]
        d = describe(s, r["spy"], f"{label}")
        d["n_deals"] = int(len(l))
        d["mean_deal_pct"] = 100 * float(l["ret"].mean())
        rows.append(d)
        if verbose:
            print("  " + fmt(d) + f"  n={d['n_deals']:4d} deal {d['mean_deal_pct']:+6.2f}%")
    return rows


def main():
    ap = argparse.ArgumentParser(prog="scout.workout_lab")
    ap.add_argument("--stage", default="all")
    ap.add_argument("--min-dv", type=float, default=1e6)
    ap.add_argument("--max-hold", type=int, default=252)
    ap.add_argument("--n-trials", type=int, default=730)
    args = ap.parse_args()
    if args.stage in ("index", "all"):
        stage_index()
    if args.stage in ("tickers", "all"):
        stage_tickers(stage_index(verbose=False))
    if args.stage in ("fallback", "all"):
        stage_tickers_fallback(stage_index(verbose=False))
    if args.stage in ("tender", "all"):
        stage_tickers_tender(stage_index(verbose=False))
    if args.stage in ("measure", "all"):
        res = run_experiment(min_dv=args.min_dv, max_hold=args.max_hold)
        out = report(res, n_trials=args.n_trials)
        out["variants"] = variants(res)
        print("\n" + "=" * 118)
        print("SPEC VARIANTS (whole pipeline re-run)")
        print("=" * 118)
        out["spec_variants"] = spec_variants()
        RESULTS.write_text(json.dumps(out, indent=1, default=str))
        print(f"\nwrote {RESULTS}")
    if args.stage == "announce":
        res = run_experiment(min_dv=args.min_dv, max_hold=args.max_hold)
        sel2 = announcement_dates(res["sel"])
        pdl, bk = build_book(sel2, res["close"], res["vol"], res["ca"])
        s = sleeve_returns(bk)
        l = pdl[pdl["drop"].isna()]
        print("\nANNOUNCEMENT (8-K) ANCHOR — secondary spec, hole stated in the docstring")
        print("  " + fmt(describe(s, res["spy"], "workout sleeve, 8-K anchor")))
        print(f"  n={len(l)} deals, mean/deal {100*l['ret'].mean():+.2f}%, "
              f"median hold {l['n_td'].median():.0f} td, "
              f"break rate {100*(l['ret'] < -0.10).mean():.1f}%")
        for row in split_stats(s, res["spy"], 2, "half "):
            print("  " + fmt(row))
        for row in split_stats(s, res["spy"], 3, "third "):
            print("  " + fmt(row))


if __name__ == "__main__":
    main()
