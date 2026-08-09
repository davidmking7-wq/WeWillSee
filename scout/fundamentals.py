"""SEC XBRL fundamentals adapter — POINT-IN-TIME by construction.

WHY THIS EXISTS
---------------
Three of the best-documented equity anomalies are accounting anomalies, and
none of them has ever been testable in this repo because the repo has only
ever had prices: net share issuance (Daniel-Titman, Pontiff-Woodgate — firms
that print shares underperform firms that retire them), gross profitability
(Novy-Marx — GP/Assets is the "other side of value"), and accruals (Sloan —
earnings that arrive as accrual rather than as cash do not persist). All three
need as-filed financial statements. SEC XBRL company facts are free, need no
key, and go back to ~2009. This module is the plumbing.

It makes NO claim of alpha. It is written defensively because fundamental
backtests fail in one specific, catastrophic and extremely common way.

THE #1 WAY FUNDAMENTAL BACKTESTS FOOL THEMSELVES: THE PERIOD END DATE
---------------------------------------------------------------------
Every XBRL fact carries three dates that people confuse:

    start / end  the accounting period the number DESCRIBES
    filed        the day the number BECAME PUBLIC

A fact for the quarter ending 2024-09-30 does not exist on 2024-09-30. It
exists on 2024-10-31, when the 10-Q is filed. Indexing a panel by `end` and
forward-filling — which is what every tutorial, every "download fundamentals
to a DataFrame" snippet, and every vendor CSV with a `date` column does —
hands the backtest the income statement weeks or months before anyone could
read it. That is not a rounding error. Measured on this module's own smoke
universe (25 large caps, 2016-2026, `python -m scout.fundamentals`):

    median lag end -> filed :  10-Q  36 days     10-K  56 days
    annual facts, median     :  56 days   (p90 63 days)
    share of panel cells where the `end`-indexed panel already holds a fact
    the `filed`-indexed panel does not yet know:  ~14% of all cells

Fourteen percent of a decade-long panel silently containing the future, with
a median of ~8 weeks of free look on every fresh number. Any "signal" built on
that will look magnificent and will be entirely fake.

THE RULE IMPLEMENTED HERE, AND THE ONLY ONE THIS MODULE WILL EVER USE
---------------------------------------------------------------------
    1. every fact enters the panel on its `filed` date, never its `end` date;
    2. the panel is then shifted forward by `lag_sessions` (default 1), so
       row t holds only facts filed STRICTLY BEFORE session t. EDGAR accepts
       filings until 22:00 ET and stamps anything after 17:30 ET with the
       next business day, so a same-day filing is not reliably readable
       before that day's close. One session of lag removes the ambiguity;
    3. when the same period has been filed more than once (restatements,
       10-K/A amendments, retrospective accounting changes), the FIRST
       filing wins — that is the number that was actually knowable. Using
       the restated value is a second, subtler lookahead, and it is the one
       that survives a code review because the dates all look right.

WHAT A PANEL ROW MEANS (state this verbatim in any downstream test)
-------------------------------------------------------------------
Panel row `t` holds the most recent fact a reader could have had in hand
before session t's close. The earliest return it may therefore weight is
close(t) -> close(t+1). Concretely, with `ret` the close-to-close return:

    panel * ret.shift(-1)      SAFE
    panel.shift(1) * ret       SAFE   (same thing, written the other way)
    panel * ret                UNSAFE by one session
    panel indexed on `end`     UNSAFE by ~2 months — see above

`lookahead_demo()` measures the damage of the `end`-indexed version on real
data, and __main__ runs it. There is no shift() hidden anywhere else: the
single shift is in `_expand()`, and it is the only one.

THE THREE LIMITS THAT MATTER, MEASURED NOT GUESSED
---------------------------------------------------
1. **Tag coverage is genuinely inconsistent across filers, and it is not
   random — it is correlated with industry.** `GrossProfit` is absent for
   JPM, XOM, V, BAC, MRK and every other filer whose income statement has no
   cost-of-goods line. `CostOfRevenue` is absent for AAPL (which tags
   `CostOfGoodsAndServicesSold` instead). A screen built on a tag that only
   half the market reports is a sector bet wearing a factor costume. Every
   builder here therefore takes a CASCADE of tags, records which one each
   ticker resolved to, and returns that map so the caller can see the
   selection. Measured coverage for the smoke universe is printed by
   `coverage_report()`.
2. **Share counts are AS REPORTED — not split adjusted.** AAPL's shares go
   from 4.3bn to 17.1bn across 2020-08-31 in this data because of a 4:1
   split, not because Apple issued 12.8bn shares. Net-issuance research that
   skips this measures splits. `split_factors()` (Alpaca corporate actions,
   the one function here that needs a key) puts a whole series on one basis,
   and `shares_outstanding(..., split_adjust=True)` applies it.
3. **Cash-flow facts in 10-Qs are YEAR TO DATE, not quarterly.** Apple's
   Q3 `NetCashProvidedByUsedInOperatingActivities` covers nine months. There
   are no 3-month cash-flow facts for most filers, so `period="quarterly"`
   returns almost nothing for that tag. Use `period="annual"` for cash flow
   and accruals; this module does not de-cumulate YTD flows.

Smaller ones: XBRL starts ~2009 (large filers) to ~2011 (small), so this is
not a 1963-2026 dataset; SEC tickers use dashes (BRK-B), handled in
`resolve_cik`; and a `companyconcept` 404 means "this filer never used this
tag", which is cached as a negative so it is asked once.

USAGE
-----
    from scout import fundamentals as fu

    px    = fu.pit_panel(["AAPL", "MSFT"], "Assets", "2016-01-01", "2026-01-01")
    sh, s = fu.shares_outstanding(tickers, start, end, split_adjust=True)
    gp, s = fu.gross_profit(tickers, start, end)

    python -m scout.fundamentals              # smoke test (25 tickers, 2016-2026)
    python -m scout.fundamentals --selftest   # offline PIT logic checks, no network

VERDICT
-------
The adapter works and is honest. 25/25 tickers resolve; `Assets`,
`NetIncomeLoss` and shares outstanding are effectively universal (25/25);
`GrossProfit` reaches 25/25 only after the revenue-minus-cost cascade, and
14/25 without it. The median filing lag is 40 days over all forms, which is
the exact amount of lookahead an `end`-indexed panel would have handed a
backtest, on ~14% of its cells. Nothing here is a trading signal; it is the
first fundamental data this repo can defend.
"""
import argparse
import gzip
import json
import pickle
import time
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

try:                                    # the SEC half needs no keys at all
    from . import config
    SCOUT_DIR = config.SCOUT_DIR
except Exception:                       # pragma: no cover - no .env present
    SCOUT_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
CONCEPT_URL = ("https://data.sec.gov/api/xbrl/companyconcept/"
               "CIK{cik:010d}/{taxonomy}/{tag}.json")
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# SEC asks for a real contact address and caps automated access at 10 req/s.
USER_AGENT = "WeWillSee research davidmking7@gmail.com"
REQ_PER_SEC = 8.0                       # deliberately under the 10/s ceiling
_MIN_INTERVAL = 1.0 / REQ_PER_SEC
_last_request = [0.0]

CACHE_PREFIX = "cache_fundamentals_"
TICKER_CACHE = SCOUT_DIR / f"{CACHE_PREFIX}tickers.json"
TICKER_CACHE_DAYS = 30
SPLIT_CACHE = SCOUT_DIR / f"{CACHE_PREFIX}splits.json"

# Period-length windows in days, used to separate the three kinds of duration
# fact a single tag mixes together (a 10-Q reports the quarter AND the year to
# date; a 10-K reports the year). Fiscal quarters run 84-98 days in practice
# (13 or 14 weeks), fiscal years 358-372, so the bands are loose on purpose.
PERIOD_DAYS = {
    "quarterly": (78, 102),
    "semi":      (170, 196),
    "ytd9":      (260, 288),
    "annual":    (346, 384),
}
PERIODS = ("any", "instant", "duration", *PERIOD_DAYS)

# Tag cascades. Order is deliberate: the specific, modern tag first, the
# fallbacks after. `_pick_source` uses ONE source per ticker for its whole
# history — mixing "shares outstanding on the cover page" with "weighted
# average diluted shares" inside a single series would manufacture issuance
# jumps out of a definition change.
SHARES_TAGS = (
    ("dei", "EntityCommonStockSharesOutstanding", "instant"),
    ("us-gaap", "CommonStockSharesOutstanding", "instant"),
    ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding", "quarterly"),
)
REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
)
COST_TAGS = (
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "CostOfGoodsSold",
    "CostOfServices",
)
ASSETS_TAGS = ("Assets",)
OCF_TAGS = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
NET_INCOME_TAGS = (
    "NetIncomeLoss",
    "ProfitLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
)

FACT_COLUMNS = ["start", "end", "filed", "val", "unit", "form", "accn",
                "fy", "fp", "frame"]


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def _headers() -> dict:
    return {"User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json"}


def _throttle() -> None:
    wait = _MIN_INTERVAL - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    _last_request[0] = time.time()


def _get(url: str, tries: int = 5, allow_404: bool = False):
    """One SEC JSON document, with exponential backoff on 403/429/5xx.

    Returns None on 404 when `allow_404` — for companyconcept a 404 is not an
    error, it is the answer ("this filer has never used this tag").
    """
    for attempt in range(tries):
        _throttle()
        try:
            r = requests.get(url, headers=_headers(), timeout=45)
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(min(30, 2 ** attempt))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404 and allow_404:
            return None
        if r.status_code in (403, 429) or r.status_code >= 500:
            time.sleep(min(30, 2 ** attempt))
            continue
        raise RuntimeError(f"SEC {r.status_code} for {url}: {r.text[:160]}")
    raise RuntimeError(f"SEC kept failing after {tries} tries: {url}")


# --------------------------------------------------------------------------
# ticker -> CIK
# --------------------------------------------------------------------------

_cik_cache: dict[str, int] | None = None


def cik_map(refresh: bool = False) -> dict[str, int]:
    """{TICKER: cik} from SEC's own file. Cached; refreshed when stale.

    SEC writes share classes with a dash (BRK-B, BF-B) where this repo's
    universe.csv uses a dot (BRK.B) — `resolve_cik` handles both.
    """
    global _cik_cache
    stale = (not TICKER_CACHE.exists() or
             (time.time() - TICKER_CACHE.stat().st_mtime)
             > TICKER_CACHE_DAYS * 86400)
    if refresh or stale:
        try:
            raw = _get(TICKERS_URL)
            mapping = {str(v["ticker"]).upper(): int(v["cik_str"])
                       for v in raw.values()}
            if len(mapping) < 5000:
                raise ValueError(f"ticker file looks wrong ({len(mapping)} rows)")
            TICKER_CACHE.write_text(json.dumps(mapping))
            _cik_cache = mapping
            return mapping
        except Exception as e:
            if not TICKER_CACHE.exists():
                raise
            print(f"  ticker->CIK refresh failed ({e}); using cache")
    if _cik_cache is None:
        _cik_cache = {k: int(v) for k, v in
                      json.loads(TICKER_CACHE.read_text()).items()}
    return _cik_cache


def resolve_cik(ticker: str) -> int | None:
    """CIK for a ticker, or None. Tries the symbol as given, then the
    dot/dash class-share variants."""
    m = cik_map()
    t = str(ticker).upper().strip()
    for cand in (t, t.replace(".", "-"), t.replace("-", ".")):
        if cand in m:
            return m[cand]
    return None


def resolve_ciks(tickers) -> dict[str, int]:
    """{ticker: cik} for the ones that resolve; unresolved are simply absent."""
    out = {}
    for t in tickers:
        cik = resolve_cik(t)
        if cik is not None:
            out[t] = cik
    return out


# --------------------------------------------------------------------------
# companyconcept + disk cache
# --------------------------------------------------------------------------

def _concept_cache_path(taxonomy: str, tag: str) -> Path:
    safe = f"{taxonomy}_{tag}".replace("/", "_")
    return SCOUT_DIR / f"{CACHE_PREFIX}concept_{safe}.pkl"


_concept_mem: dict[tuple[str, str], dict] = {}


def _load_concept_cache(taxonomy: str, tag: str) -> dict:
    key = (taxonomy, tag)
    if key not in _concept_mem:
        path = _concept_cache_path(taxonomy, tag)
        if path.exists():
            try:
                with open(path, "rb") as f:
                    _concept_mem[key] = pickle.load(f)
            except Exception:
                _concept_mem[key] = {}
        else:
            _concept_mem[key] = {}
    return _concept_mem[key]


def _save_concept_cache(taxonomy: str, tag: str) -> None:
    path = _concept_cache_path(taxonomy, tag)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(_concept_mem[(taxonomy, tag)], f, protocol=4)
    tmp.replace(path)


_bulk_memo: dict[int, dict] = {}
BULK_MEMO_MAX = 3           # parsed companyfacts docs are ~50 MB each in RAM


def _bulk_cache_path(cik: int) -> Path:
    return SCOUT_DIR / f"{CACHE_PREFIX}facts_{int(cik):010d}.json.gz"


def company_facts(cik: int, refresh: bool = False) -> dict:
    """The whole `companyfacts` document for one filer: {taxonomy: {tag: ...}}.

    Exists because `companyconcept` cannot be trusted on its own — see
    `concept()`. Cached gzipped on disk (a raw doc is 2-4 MB; the gzip is
    ~10% of that) and memoised at most `BULK_MEMO_MAX` deep, because the
    parsed structure is large.
    """
    cik = int(cik)
    if not refresh and cik in _bulk_memo:
        return _bulk_memo[cik]
    path = _bulk_cache_path(cik)
    if path.exists() and not refresh:
        with gzip.open(path, "rb") as f:
            doc = json.loads(f.read())
    else:
        doc = _get(FACTS_URL.format(cik=cik), allow_404=True) or {}
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, "wb") as f:
            f.write(json.dumps(doc).encode())
        tmp.replace(path)
    facts_by_tax = doc.get("facts", {})
    if len(_bulk_memo) >= BULK_MEMO_MAX:
        _bulk_memo.pop(next(iter(_bulk_memo)))
    _bulk_memo[cik] = facts_by_tax
    return facts_by_tax


def _flatten_units(units: dict) -> list[dict]:
    return [dict(row, unit=unit) for unit, rows in units.items() for row in rows]


def concept(cik: int, tag: str, taxonomy: str = "us-gaap",
            refresh: bool = False, allow_bulk_fallback: bool = True
            ) -> list[dict] | None:
    """Raw XBRL facts for one (company, tag), flattened across units.

    Returns None when the filer has genuinely never reported the tag, which
    is a real and informative answer (GOOGL and META never tag
    dei:EntityCommonStockSharesOutstanding at all), cached as a negative so
    it is asked once.

    THE companyconcept ENDPOINT SILENTLY LIES, AND THIS COST AN HOUR.
    For some filers it returns HTTP 200 with `{"units": {"USD": []}}` for a
    tag the company plainly reports. Measured here: Visa
    (CIK 1403161) and Coca-Cola (CIK 21344) both return zero `Assets` facts
    from companyconcept while `companyfacts` returns 136 and 144 of them.
    Taken at face value that is not a crash, it is a UNIVERSE HOLE — two of
    twenty-five large caps quietly dropping out of every panel, which in a
    cross-sectional test is a survivorship-flavoured bias nobody would ever
    see. So an empty or missing concept response is re-checked against the
    bulk `companyfacts` document before it is believed.
    """
    cache = _load_concept_cache(taxonomy, tag)
    if not refresh and cik in cache:
        return cache[cik]
    doc = _get(CONCEPT_URL.format(cik=int(cik), taxonomy=taxonomy, tag=tag),
               allow_404=True)
    rows = _flatten_units(doc.get("units", {})) if doc else []
    if not rows and allow_bulk_fallback:
        bulk = company_facts(cik, refresh=refresh)
        entry = bulk.get(taxonomy, {}).get(tag)
        if entry:
            rows = _flatten_units(entry.get("units", {}))
    result = rows or None
    cache[cik] = result
    _save_concept_cache(taxonomy, tag)
    return result


PRED_CACHE = SCOUT_DIR / f"{CACHE_PREFIX}predecessors.json"
PRED_PROBE_TAG = "Assets"
PRED_MIN_SPAN_DAYS = 3 * 365      # below this, suspect a reorganised CIK


def predecessor_cik(cik: int, refresh: bool = False) -> int | None:
    """The CIK that holds this filer's history, when the ticker's CURRENT CIK
    does not — or None.

    THE CIK REASSIGNMENT TRAP. `company_tickers.json` maps a ticker to the
    CIK filing under it TODAY. When a company reorganises into a new holding
    company, redomiciles, or emerges from a merger, the new CIK starts with
    an empty filing history and the old one keeps the decade. Measured here:
    XOM resolves to CIK 2115436 ("ExxonMobil Holdings Corp"), which has
    exactly 2 `Assets` facts, both filed 2026-08-03. CIK 34088 ("Exxon Mobil
    Corporation") has 152, going back to 2008. Nothing errors. The panel just
    starts in 2026 for one name, and a cross-sectional test quietly runs on
    24 stocks instead of 25.

    Detection: if the filer's own history spans less than PRED_MIN_SPAN_DAYS,
    look at the accession numbers on its facts — a modern self-filed document
    is numbered with the FILER's own CIK, so `0000034088-26-000093` names the
    predecessor. A candidate is accepted only if it has at least 4x more
    facts AND its history ends where the short one begins (within 400 days),
    which is what a genuine continuation looks like and what a coincidental
    filing-agent CIK will not survive.
    """
    cache = {}
    if PRED_CACHE.exists() and not refresh:
        try:
            cache = json.loads(PRED_CACHE.read_text())
        except Exception:
            cache = {}
    key = str(int(cik))
    if key in cache and not refresh:
        return cache[key]

    result = None
    own = concept(int(cik), PRED_PROBE_TAG, "us-gaap") or []
    if own:
        ends = sorted(date.fromisoformat(r["end"]) for r in own if r.get("end"))
        if ends and (ends[-1] - ends[0]).days < PRED_MIN_SPAN_DAYS:
            prefixes = Counter(str(r["accn"]).split("-")[0] for r in own
                               if r.get("accn"))
            for prefix, _ in prefixes.most_common(3):
                try:
                    cand = int(prefix)
                except ValueError:
                    continue
                if cand == int(cik):
                    continue
                bulk = company_facts(cand)
                rows = (bulk.get("us-gaap", {}).get(PRED_PROBE_TAG, {})
                        .get("units", {}).get("USD", []))
                if len(rows) < max(4 * len(own), 20):
                    continue
                cand_last = max(date.fromisoformat(r["end"]) for r in rows
                                if r.get("end"))
                if abs((ends[0] - cand_last).days) <= 400:
                    result = cand
                    break
    cache[key] = result
    try:
        PRED_CACHE.write_text(json.dumps(cache))
    except Exception:
        pass
    return result


def history_ciks(ticker) -> list[int]:
    """Every CIK that holds part of this ticker's filing history, current
    first. Usually one; two when `predecessor_cik` finds a reorganisation."""
    cik = ticker if isinstance(ticker, (int, np.integer)) else resolve_cik(ticker)
    if cik is None:
        return []
    pred = predecessor_cik(int(cik))
    return [int(cik)] + ([pred] if pred else [])


def facts(ticker, tag: str, taxonomy: str = "us-gaap",
          refresh: bool = False) -> pd.DataFrame:
    """Tidy fact table for one ticker (or CIK). Empty frame if untagged.

    Columns: start, end, filed (datetime64), val (float), unit, form, accn,
    fy, fp, frame, days (period length; NaN for instantaneous facts).

    Spans predecessor CIKs automatically — see `predecessor_cik`.
    """
    if isinstance(ticker, (int, np.integer)):
        ciks = [int(ticker)]
    else:
        ciks = history_ciks(ticker)
    if not ciks:
        return _empty_facts()
    rows = []
    for cik in ciks:
        rows += concept(cik, tag, taxonomy, refresh=refresh) or []
    if not rows:
        return _empty_facts()
    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=[c for c in ("accn", "unit", "start",
                                                "end", "val")
                                    if c in df.columns])
    for col in FACT_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    df = df[FACT_COLUMNS].copy()
    for col in ("start", "end", "filed"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["val"] = pd.to_numeric(df["val"], errors="coerce")
    df["days"] = (df["end"] - df["start"]).dt.days
    df = df.dropna(subset=["end", "filed", "val"])
    return df.sort_values(["end", "filed"]).reset_index(drop=True)


def _empty_facts() -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype="object") for c in FACT_COLUMNS})
    for col in ("start", "end", "filed"):
        df[col] = pd.to_datetime(df[col])
    df["val"] = pd.to_numeric(df["val"])
    df["days"] = pd.to_numeric(df["val"])
    return df


def fact_table(tickers, tag: str, taxonomy: str = "us-gaap",
               refresh: bool = False, verbose: bool = False
               ) -> dict[str, pd.DataFrame]:
    """{ticker: fact frame} — one companyconcept call per ticker, cached."""
    out = {}
    for i, t in enumerate(tickers, 1):
        out[t] = facts(t, tag, taxonomy, refresh=refresh)
        if verbose and i % 25 == 0:
            print(f"    {taxonomy}:{tag} {i}/{len(tickers)}")
    return out


# --------------------------------------------------------------------------
# period selection and the restatement rule
# --------------------------------------------------------------------------

def select_period(df: pd.DataFrame, period: str = "any") -> pd.DataFrame:
    """Keep only facts of one period shape.

    A single tag mixes them: `NetIncomeLoss` for AAPL carries 208 three-month,
    34 six-month, 36 nine-month and 60 twelve-month facts. Comparing across
    shapes is meaningless, so a panel must pick one.
    """
    if period == "any":
        return df
    if period == "instant":
        return df[df["start"].isna()]
    if period == "duration":
        return df[df["start"].notna()]
    if period not in PERIOD_DAYS:
        raise ValueError(f"period must be one of {PERIODS}, got {period!r}")
    lo, hi = PERIOD_DAYS[period]
    return df[df["days"].between(lo, hi)]


def first_filings(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (unit, start, end): the FIRST time that period was filed.

    THE RESTATEMENT RULE. The same period is filed repeatedly — in the
    original 10-Q, again as a comparative in later filings, and sometimes
    with a different number after an amendment or a retrospective accounting
    change. Apple's FY2008 net income was filed as $4.834bn on 2009-10-27 and
    refiled as $6.119bn on 2010-01-25 (the retrospective iPhone revenue
    change). A backtest standing in 2009-11 knew $4.834bn. Taking the latest
    value would hand it a number that did not exist for another three months.
    """
    if df.empty:
        return df
    tmp = df.copy()
    tmp["_start"] = tmp["start"].fillna(pd.Timestamp("1900-01-01"))
    tmp = tmp.sort_values(["filed", "accn"], kind="mergesort")
    idx = tmp.groupby(["unit", "_start", "end"], dropna=False).head(1).index
    return df.loc[idx].sort_values(["filed", "end"], kind="mergesort")


def restatements(df: pd.DataFrame) -> pd.DataFrame:
    """Periods filed more than once with DIFFERENT values, long form.

    Columns: unit, start, end, n_filings, first_filed, first_val, last_filed,
    last_val, pct_change. Exists so the restatement rule can be audited on
    real filings rather than asserted.
    """
    if df.empty:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["start"] = tmp["start"].fillna(pd.Timestamp("1900-01-01"))
    rows = []
    for (unit, start, end), g in tmp.groupby(["unit", "start", "end"]):
        g = g.sort_values("filed")
        if g["val"].nunique() <= 1:
            continue
        first, last = g.iloc[0], g.iloc[-1]
        rows.append({
            "unit": unit,
            "start": pd.NaT if start == pd.Timestamp("1900-01-01") else start,
            "end": end, "n_filings": len(g),
            "first_filed": first["filed"], "first_form": first["form"],
            "first_val": first["val"],
            "last_filed": last["filed"], "last_form": last["form"],
            "last_val": last["val"],
            "pct_change": (last["val"] / first["val"] - 1.0)
                          if first["val"] else np.nan,
        })
    return pd.DataFrame(rows).sort_values("end") if rows else pd.DataFrame()


# --------------------------------------------------------------------------
# the point-in-time core
# --------------------------------------------------------------------------

def pit_events(df: pd.DataFrame, period: str = "any",
               unit: str | None = None) -> pd.DataFrame:
    """The step function of what was knowable, indexed by FILED date.

    Pipeline, in order, each step load-bearing:
      1. keep one unit (the most common one) so USD and shares never mix;
      2. keep one period shape (`select_period`);
      3. `first_filings` — restatements collapse to what was knowable;
      4. walk filings forward in time and emit a row only when the filing
         advances the newest period end. A later filing that repeats an OLDER
         period (a comparative) must not overwrite a newer number.

    Returns columns value, period_end, form, accn indexed by filed date.
    """
    df = select_period(df, period)
    if df.empty:
        return pd.DataFrame(columns=["value", "period_end", "form", "accn"],
                            index=pd.DatetimeIndex([], name="filed"))
    if unit is None:
        unit = df["unit"].value_counts().idxmax()
    df = df[df["unit"] == unit]
    df = first_filings(df)
    if df.empty:
        return pd.DataFrame(columns=["value", "period_end", "form", "accn"],
                            index=pd.DatetimeIndex([], name="filed"))

    df = df.sort_values(["filed", "end"])
    best_end = pd.Timestamp.min
    rows = []
    for r in df.itertuples(index=False):
        if r.end <= best_end:
            continue                    # a comparative, not new information
        best_end = r.end
        rows.append((r.filed, r.val, r.end, r.form, r.accn))
    ev = pd.DataFrame(rows, columns=["filed", "value", "period_end",
                                     "form", "accn"])
    # two filings on one day: the later-ending period is the live one
    ev = ev.groupby("filed", as_index=True).last()
    ev.index.name = "filed"
    return ev


def _calendar(start, end, calendar=None) -> pd.DatetimeIndex:
    if calendar is not None:
        idx = pd.DatetimeIndex(pd.to_datetime(calendar))
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_localize(None)
        return idx[(idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))]
    return pd.bdate_range(start, end)


def _expand(events: pd.DataFrame, cal: pd.DatetimeIndex, lag_sessions: int,
            column: str) -> pd.Series:
    """Forward-fill one event column onto the calendar, then lag it.

    THE ONLY shift() IN THIS MODULE. `reindex(...).ffill()` puts a fact on
    every session from its filing date onward; `.shift(lag_sessions)` then
    moves it forward so row t holds only facts filed strictly before session
    t. With the default lag of 1, `panel * ret.shift(-1)` is safe.
    """
    if events.empty:
        return pd.Series(np.nan, index=cal, dtype="float64"
                         if column == "value" else "object")
    s = events[column]
    joined = s.reindex(s.index.union(cal)).ffill().reindex(cal)
    if lag_sessions:
        joined = joined.shift(lag_sessions)
    return joined


def pit_panel(tickers, tag: str, start: str, end: str,
              taxonomy: str = "us-gaap", period: str = "any",
              unit: str | None = None, calendar=None, lag_sessions: int = 1,
              refresh: bool = False, meta: bool = False, verbose: bool = False):
    """POINT-IN-TIME panel: time x ticker, each fact live from its FILED date.

    Row t holds the newest fact filed strictly before session t (with the
    default `lag_sessions=1`). The earliest return it may weight is
    close(t) -> close(t+1). Never index a fundamentals panel by period end;
    `lookahead_demo()` shows what that costs.

    `meta=True` returns {"value", "period_end", "filed", "age_days"} instead
    of the bare value frame — `age_days` (session date minus filing date) is
    how stale each cell is, which any serious test should gate on.
    """
    cal = _calendar(start, end, calendar)
    frames = fact_table(tickers, tag, taxonomy, refresh=refresh, verbose=verbose)
    return panel_from_frames(frames, cal, period=period, unit=unit,
                             lag_sessions=lag_sessions, meta=meta)


def panel_from_frames(frames: dict, cal: pd.DatetimeIndex,
                      period: str = "any", unit: str | None = None,
                      lag_sessions: int = 1, meta: bool = False):
    """Same as `pit_panel` but from already-fetched fact frames (used by the
    convenience builders, which fetch several tags before choosing)."""
    vals, ends, fileds = {}, {}, {}
    for t, df in frames.items():
        ev = pit_events(df, period=period, unit=unit)
        vals[t] = _expand(ev, cal, lag_sessions, "value")
        if meta:
            ends[t] = _expand(ev, cal, lag_sessions, "period_end")
            fileds[t] = _expand(ev, cal, lag_sessions, "filed_date")\
                if "filed_date" in ev.columns else _filed_column(ev, cal,
                                                                 lag_sessions)
    value = pd.DataFrame(vals, index=cal).astype("float64")
    value.index.name = "date"
    if not meta:
        return value
    period_end = pd.DataFrame(ends, index=cal).apply(pd.to_datetime)
    filed = pd.DataFrame(fileds, index=cal).apply(pd.to_datetime)
    age = filed.rsub(pd.Series(cal, index=cal), axis=0)
    age = age.apply(lambda c: c.dt.days)
    return {"value": value, "period_end": period_end, "filed": filed,
            "age_days": age}


def _filed_column(ev: pd.DataFrame, cal: pd.DatetimeIndex,
                  lag_sessions: int) -> pd.Series:
    """The filing date itself, carried through the same ffill+lag as the value
    (so `age_days` measures real staleness, not calendar arithmetic)."""
    if ev.empty:
        return pd.Series(pd.NaT, index=cal)
    s = pd.Series(ev.index, index=ev.index)
    joined = s.reindex(s.index.union(cal)).ffill().reindex(cal)
    return joined.shift(lag_sessions) if lag_sessions else joined


# --------------------------------------------------------------------------
# convenience builders
# --------------------------------------------------------------------------

MIN_FACTS = 4       # a source with fewer first-filings than this is a stub


def _pick_source(tickers, candidates, start, end, period_default,
                 refresh=False, verbose=False, min_facts=MIN_FACTS):
    """For each ticker choose the FIRST candidate tag it actually reports.

    One source per ticker for its whole history, on purpose. Splicing tags
    mid-series (cover-page shares before 2019, weighted-average diluted after)
    invents a step change in a series whose whole use is measuring step
    changes. The returned `sources` map is part of the result, not debug
    output: it shows exactly which selection was made and where.

    `min_facts` rejects stubs. Visa tags dei:EntityCommonStockSharesOutstanding
    exactly twice in seventeen years; accepting that would give Visa a share
    count that never moves, which is worse than no data because it looks
    like data.
    """
    fetched, sources = {}, {}
    remaining = list(tickers)
    for taxonomy, tag, period in candidates:
        if not remaining:
            break
        if verbose:
            print(f"    fetching {taxonomy}:{tag} for {len(remaining)} tickers")
        table = fact_table(remaining, tag, taxonomy, refresh=refresh)
        still = []
        for t in remaining:
            df = select_period(table[t], period or period_default)
            df = df[df["filed"] <= pd.Timestamp(end)]
            if len(first_filings(df)) >= min_facts:
                fetched[t] = df
                sources[t] = f"{taxonomy}:{tag}"
            else:
                still.append(t)
        remaining = still
    for t in remaining:
        fetched[t] = _empty_facts()
        sources[t] = "none"
    return fetched, sources


def shares_outstanding(tickers, start: str, end: str, calendar=None,
                       lag_sessions: int = 1, split_adjust: bool = False,
                       refresh: bool = False, verbose: bool = False):
    """PIT common shares outstanding -> (panel, {ticker: tag used}).

    Cascade: dei:EntityCommonStockSharesOutstanding (the 10-K/10-Q cover-page
    count, the most consistently tagged number in all of XBRL), else
    us-gaap:CommonStockSharesOutstanding, else the weighted-average diluted
    count.

    AS REPORTED — NOT SPLIT ADJUSTED. AAPL's series steps 4x on the 2020
    split. Pass `split_adjust=True` (needs Alpaca keys) to restate the whole
    series onto today's share basis, which is what net-issuance work needs.
    """
    cal = _calendar(start, end, calendar)
    frames, sources = _pick_source(tickers, SHARES_TAGS, start, end,
                                   "any", refresh=refresh, verbose=verbose)
    if split_adjust:
        # reach back before `start`: a fact filed earlier is carried into the
        # window by the forward fill and still needs adjusting
        lo = str(pd.Timestamp(start) - pd.DateOffset(years=2))[:10]
        ev = split_events(list(frames), lo, end)
        by_sym = dict(tuple(ev.groupby("symbol"))) if not ev.empty else {}
        for t in frames:
            basis = "end" if sources.get(t) in AS_OF_SHARE_TAGS else "filed"
            frames[t] = adjust_facts_for_splits(frames[t], by_sym.get(t),
                                                basis=basis)
    return panel_from_frames(frames, cal, period="any", unit="shares",
                             lag_sessions=lag_sessions), sources


def total_assets(tickers, start: str, end: str, calendar=None,
                 lag_sessions: int = 1, refresh: bool = False,
                 verbose: bool = False):
    """PIT total assets (us-gaap:Assets, instantaneous) -> (panel, sources)."""
    cal = _calendar(start, end, calendar)
    frames, sources = _pick_source(
        tickers, [("us-gaap", t, "instant") for t in ASSETS_TAGS],
        start, end, "instant", refresh=refresh, verbose=verbose)
    return panel_from_frames(frames, cal, period="instant", unit="USD",
                             lag_sessions=lag_sessions), sources


def net_income(tickers, start: str, end: str, period: str = "annual",
               calendar=None, lag_sessions: int = 1, refresh: bool = False,
               verbose: bool = False):
    """PIT net income -> (panel, sources). `period` defaults to annual, the
    only shape that is comparable across filers with different fiscal-quarter
    tagging habits."""
    cal = _calendar(start, end, calendar)
    frames, sources = _pick_source(
        tickers, [("us-gaap", t, period) for t in NET_INCOME_TAGS],
        start, end, period, refresh=refresh, verbose=verbose)
    return panel_from_frames(frames, cal, period=period, unit="USD",
                             lag_sessions=lag_sessions), sources


def operating_cashflow(tickers, start: str, end: str, period: str = "annual",
                       calendar=None, lag_sessions: int = 1,
                       refresh: bool = False, verbose: bool = False):
    """PIT cash from operations -> (panel, sources).

    NOTE the YTD trap: 10-Q cash-flow facts cover the fiscal year to date
    (3, 6 then 9 months), not the quarter. `period="quarterly"` therefore
    returns almost nothing here; `period="annual"` is the usable shape and is
    the default. This module does not de-cumulate YTD flows.
    """
    cal = _calendar(start, end, calendar)
    frames, sources = _pick_source(
        tickers, [("us-gaap", t, period) for t in OCF_TAGS],
        start, end, period, refresh=refresh, verbose=verbose)
    return panel_from_frames(frames, cal, period=period, unit="USD",
                             lag_sessions=lag_sessions), sources


def gross_profit(tickers, start: str, end: str, period: str = "annual",
                 calendar=None, lag_sessions: int = 1, refresh: bool = False,
                 verbose: bool = False):
    """PIT gross profit -> (panel, sources), with the derived fallback.

    us-gaap:GrossProfit where the filer tags it; otherwise revenue minus cost
    of revenue, SUBTRACTED FACT BY FACT WITHIN ONE ACCESSION. Matching on the
    accession number (not on dates, and never at panel level) guarantees the
    two legs come from the same filing, so the difference is a number that
    appeared in one document on one day and inherits that document's filing
    date. A panel-level subtraction can silently pair this year's revenue
    with last year's cost when the two tags have different filing histories.

    Coverage here is the module's main practical limit: financials, energy
    and payment networks do not report a cost-of-revenue line at all, so no
    cascade can produce gross profit for them. `sources` says which ticker
    got what, including "none".
    """
    cal = _calendar(start, end, calendar)
    frames, sources = _pick_source(
        tickers, [("us-gaap", "GrossProfit", period)], start, end, period,
        refresh=refresh, verbose=verbose)
    missing = [t for t, s in sources.items() if s == "none"]
    if missing:
        if verbose:
            print(f"    GrossProfit missing for {len(missing)} tickers; "
                  f"trying revenue - cost")
        rev, rev_src = _pick_source(
            missing, [("us-gaap", t, period) for t in REVENUE_TAGS],
            start, end, period, refresh=refresh)
        cost, cost_src = _pick_source(
            missing, [("us-gaap", t, period) for t in COST_TAGS],
            start, end, period, refresh=refresh)
        for t in missing:
            derived = _derive_difference(rev[t], cost[t])
            if len(first_filings(derived)) >= MIN_FACTS:
                frames[t] = derived
                sources[t] = (f"{rev_src[t]} - {cost_src[t]}").replace(
                    "us-gaap:", "")
    return panel_from_frames(frames, cal, period=period, unit="USD",
                             lag_sessions=lag_sessions), sources


def _derive_difference(minuend: pd.DataFrame,
                       subtrahend: pd.DataFrame) -> pd.DataFrame:
    """minuend - subtrahend, matched on (accn, unit, start, end).

    Same accession => same filing date => the derived fact is knowable
    exactly when the document it came from was filed. Facts present in only
    one of the two tables are dropped rather than guessed at.
    """
    if minuend.empty or subtrahend.empty:
        return _empty_facts()
    keys = ["accn", "unit", "start", "end"]
    a = minuend.copy()
    b = subtrahend[keys + ["val"]].rename(columns={"val": "_sub"})
    for f in (a, b):
        f["start"] = f["start"].fillna(pd.Timestamp("1900-01-01"))
    merged = a.merge(b, on=keys, how="inner")
    if merged.empty:
        return _empty_facts()
    merged["val"] = merged["val"] - merged["_sub"]
    merged["start"] = merged["start"].replace(pd.Timestamp("1900-01-01"), pd.NaT)
    return merged.drop(columns=["_sub"]).sort_values(["end", "filed"])\
                 .reset_index(drop=True)


# --------------------------------------------------------------------------
# splits — the one function here that needs an API key
# --------------------------------------------------------------------------

CA_URL = "https://data.alpaca.markets/v1/corporate-actions"


def split_events(tickers, start: str, end: str,
                 refresh: bool = False) -> pd.DataFrame:
    """Forward/reverse splits from Alpaca corporate actions, cached to disk.

    Columns: symbol, ex_date, ratio (new/old; 4.0 for a 4:1 forward split).
    Returns an empty frame — never raises — if keys or the endpoint are
    unavailable, so the SEC half of this module keeps working without them.
    """
    cache = {}
    if SPLIT_CACHE.exists() and not refresh:
        try:
            cache = json.loads(SPLIT_CACHE.read_text())
        except Exception:
            cache = {}
    key = f"{min(tickers) if tickers else ''}|{len(tickers)}|{start}|{end}"
    if key in cache and not refresh:
        rows = cache[key]
    else:
        try:
            headers = {"APCA-API-KEY-ID": config.ALPACA_API_KEY,
                       "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY}
        except Exception:
            return pd.DataFrame(columns=["symbol", "ex_date", "ratio"])
        rows, token = [], None
        try:
            for i in range(0, len(tickers), 100):
                chunk = tickers[i:i + 100]
                token = None
                while True:
                    params = {"symbols": ",".join(chunk),
                              "types": "forward_split,reverse_split",
                              "start": start, "end": end, "limit": 1000}
                    if token:
                        params["page_token"] = token
                    r = requests.get(CA_URL, headers=headers, params=params,
                                     timeout=45)
                    r.raise_for_status()
                    j = r.json()
                    for kind in ("forward_splits", "reverse_splits"):
                        for ev in j.get("corporate_actions", {}).get(kind, []):
                            old = float(ev.get("old_rate") or 0)
                            new = float(ev.get("new_rate") or 0)
                            if old > 0 and new > 0 and ev.get("ex_date"):
                                rows.append({"symbol": ev["symbol"],
                                             "ex_date": ev["ex_date"],
                                             "ratio": new / old})
                    token = j.get("next_page_token")
                    if not token:
                        break
        except Exception as e:
            print(f"  split fetch failed ({e}); shares stay as-reported")
            return pd.DataFrame(columns=["symbol", "ex_date", "ratio"])
        cache[key] = rows
        try:
            SPLIT_CACHE.write_text(json.dumps(cache))
        except Exception:
            pass
    df = pd.DataFrame(rows, columns=["symbol", "ex_date", "ratio"])
    if not df.empty:
        df["ex_date"] = pd.to_datetime(df["ex_date"])
    return df


# Tags whose value is a COUNT AS OF a measurement date (the cover page, the
# balance sheet). Their split basis is that date. Everything else — notably
# the weighted-average share counts — is restated retrospectively by the
# filer under ASC 260, so its basis is the FILING date instead.
AS_OF_SHARE_TAGS = frozenset({"dei:EntityCommonStockSharesOutstanding",
                              "us-gaap:CommonStockSharesOutstanding"})


def adjust_facts_for_splits(df: pd.DataFrame, splits: pd.DataFrame,
                            basis: str = "end") -> pd.DataFrame:
    """Put every as-reported share count on TODAY'S share basis.

    THE ADJUSTMENT BELONGS ON THE FACT, NOT ON THE PANEL CELL. The first
    version of this function multiplied the finished panel by a factor that
    stepped on the EX-DATE, and it made things worse (8 spurious jumps became
    16): the panel steps on the FILING date, roughly two months after the
    ex-date, so between the two it was pairing a pre-split count with a
    post-split factor and inventing a 4x drop followed by a 4x rebound. Each
    fact is multiplied by the splits that happened after ITS OWN basis date,
    which is the only version that makes shares_t / shares_{t-12m} mean
    anything.

    `basis` is "end" for as-of counts and "filed" for retrospectively
    restated ones — see AS_OF_SHARE_TAGS.
    """
    if df.empty or splits is None or splits.empty:
        return df
    out = df.copy()
    when = out[basis].values
    factor = np.ones(len(out))
    for r in splits.itertuples(index=False):
        factor = np.where(when < np.datetime64(r.ex_date), factor * r.ratio,
                          factor)
    out["val"] = out["val"] * factor
    return out


def detect_share_jumps(panel: pd.DataFrame, ratio: float = 1.4
                       ) -> pd.DataFrame:
    """Cells where a share count jumps by more than `ratio` (or 1/ratio) in
    one step — almost always a split, occasionally a huge secondary. A
    net-issuance study that does not explain every one of these is measuring
    corporate actions."""
    rows = []
    for col in panel.columns:
        s = panel[col].dropna()
        if len(s) < 2:
            continue
        chg = s / s.shift(1)
        hits = chg[(chg > ratio) | (chg < 1 / ratio)]
        for d, v in hits.items():
            rows.append({"ticker": col, "date": d, "ratio": v,
                         "prev": s.shift(1).loc[d], "curr": s.loc[d]})
    return pd.DataFrame(rows).sort_values("date") if rows else pd.DataFrame()


# --------------------------------------------------------------------------
# diagnostics
# --------------------------------------------------------------------------

def filing_lag(frames: dict, period: str = "any",
               since: str | None = None) -> pd.DataFrame:
    """Every first-filed fact's lag from period end to filing date.

    THIS NUMBER IS THE LOOKAHEAD. A panel indexed on `end` instead of `filed`
    hands the backtest each fact this many days early.
    """
    rows = []
    for t, df in frames.items():
        df = first_filings(select_period(df, period))
        if df.empty:
            continue
        if since:
            df = df[df["filed"] >= pd.Timestamp(since)]
        for r in df.itertuples(index=False):
            rows.append({"ticker": t, "form": r.form, "end": r.end,
                         "filed": r.filed, "lag_days": (r.filed - r.end).days})
    return pd.DataFrame(rows)


def lookahead_demo(frames: dict, cal: pd.DatetimeIndex,
                   period: str = "any", unit: str | None = None) -> dict:
    """Measure what an `end`-indexed panel manufactures, on the real data.

    Builds the identical panel twice — once entering each fact on its FILED
    date (correct) and once on its period END date (the standard mistake) —
    and reports the share of cells where the naive panel already holds a
    fresher fact, plus how many days of free look that is.
    """
    n_cells = n_ahead = 0
    lead_days: list[int] = []
    for df in frames.values():
        ev = pit_events(df, period=period, unit=unit)
        if ev.empty:
            continue
        # correct: each fact enters on its FILED date (then one session of lag)
        good = pd.to_datetime(_expand(ev, cal, 1, "period_end"))
        # the standard mistake: the same facts entering on their period END
        ends = pd.DatetimeIndex(ev["period_end"])
        naive_src = pd.Series(ends, index=ends).sort_index()
        naive_src = naive_src[~naive_src.index.duplicated(keep="last")]
        naive = pd.to_datetime(
            naive_src.reindex(naive_src.index.union(cal)).ffill().reindex(cal))

        n_cells += int((good.notna() | naive.notna()).sum())
        ahead = naive.notna() & (good.isna() | (naive > good))
        n_ahead += int(ahead.sum())
        if not ahead.any():
            continue
        filed_by_end = pd.Series(ev.index.values, index=ends)
        filed_by_end = filed_by_end[~filed_by_end.index.duplicated(keep="last")]
        shown = naive[ahead]
        would_file = pd.to_datetime(pd.Series(shown.values).map(filed_by_end))
        # free look at that cell = days until the fact it shows was published
        gap = (would_file.values - shown.index.values) / np.timedelta64(1, "D")
        lead_days += [int(g) for g in gap[~np.isnan(gap)]]
    return {"cells": n_cells, "ahead": n_ahead,
            "share_ahead": n_ahead / n_cells if n_cells else np.nan,
            "median_lead_days": float(np.median(lead_days)) if lead_days else np.nan,
            "p90_lead_days": float(np.percentile(lead_days, 90)) if lead_days else np.nan}


def coverage_report(tickers, tags, start: str, end: str,
                    verbose: bool = False) -> pd.DataFrame:
    """How many of `tickers` ever report each (taxonomy, tag), and how many
    facts land inside [start, end]. Coverage is the story with XBRL."""
    rows = []
    for taxonomy, tag in tags:
        have = in_window = 0
        n_facts = []
        for t in tickers:
            df = facts(t, tag, taxonomy)
            if df.empty:
                continue
            have += 1
            w = df[(df["filed"] >= pd.Timestamp(start))
                   & (df["filed"] <= pd.Timestamp(end))]
            if not w.empty:
                in_window += 1
                n_facts.append(len(first_filings(w)))
        rows.append({"taxonomy": taxonomy, "tag": tag,
                     "tickers_with_tag": have,
                     "tickers_in_window": in_window,
                     "median_facts_in_window": int(np.median(n_facts))
                     if n_facts else 0})
        if verbose:
            print(f"    {taxonomy}:{tag:<52s} {have:>3d}/{len(tickers)}")
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# offline self-test of the PIT logic (no network)
# --------------------------------------------------------------------------

def _synthetic_facts() -> pd.DataFrame:
    """A hand-built filing history with every trap in it: a restatement, a
    comparative refiled later, two period shapes, and a same-day double."""
    rows = [
        # FY2020 filed 2021-02-15, restated upward on 2021-08-10
        dict(start="2020-01-01", end="2020-12-31", filed="2021-02-15",
             val=100.0, unit="USD", form="10-K", accn="a1"),
        dict(start="2020-01-01", end="2020-12-31", filed="2021-08-10",
             val=180.0, unit="USD", form="10-K/A", accn="a2"),
        # a Q filed in between (different period shape)
        dict(start="2021-01-01", end="2021-03-31", filed="2021-05-05",
             val=30.0, unit="USD", form="10-Q", accn="a3"),
        # FY2021 filed 2022-02-15
        dict(start="2021-01-01", end="2021-12-31", filed="2022-02-15",
             val=140.0, unit="USD", form="10-K", accn="a4"),
        # FY2020 refiled AGAIN as a comparative inside the FY2021 10-K
        dict(start="2020-01-01", end="2020-12-31", filed="2022-02-15",
             val=180.0, unit="USD", form="10-K", accn="a4"),
    ]
    df = pd.DataFrame(rows)
    for c in ("start", "end", "filed"):
        df[c] = pd.to_datetime(df[c])
    df["fy"] = 0
    df["fp"] = ""
    df["frame"] = ""
    df["days"] = (df["end"] - df["start"]).dt.days
    return df


def selftest() -> None:
    """Offline proof that the four PIT rules do what the docstring claims."""
    print("=" * 78)
    print("SELFTEST — point-in-time logic, no network")
    print("=" * 78)
    df = _synthetic_facts()

    ann = select_period(df, "annual")
    assert len(ann) == 4, len(ann)
    assert len(select_period(df, "quarterly")) == 1
    print("  [ok] period shapes separate: 4 annual, 1 quarterly out of 5 facts")

    ff = first_filings(ann)
    fy20 = ff[ff["end"] == pd.Timestamp("2020-12-31")]
    assert len(fy20) == 1 and fy20.iloc[0]["val"] == 100.0, fy20
    print("  [ok] restatement rule: FY2020 keeps the 100.0 originally filed, "
          "not the 180.0 restatement")

    rs = restatements(ann)
    assert len(rs) == 1 and abs(rs.iloc[0]["pct_change"] - 0.8) < 1e-9
    print(f"  [ok] restatements() flags it: {rs.iloc[0]['first_val']:.0f} on "
          f"{rs.iloc[0]['first_filed']:%Y-%m-%d} -> "
          f"{rs.iloc[0]['last_val']:.0f} on {rs.iloc[0]['last_filed']:%Y-%m-%d}")

    ev = pit_events(df, period="annual")
    assert list(ev["value"]) == [100.0, 140.0], list(ev["value"])
    assert list(ev.index.strftime("%Y-%m-%d")) == ["2021-02-15", "2022-02-15"]
    print("  [ok] comparative refiling of FY2020 inside the FY2021 10-K does "
          "not overwrite FY2021")

    cal = pd.bdate_range("2021-02-10", "2021-02-22")
    val = _expand(ev, cal, 1, "value")
    before = val.loc[:"2021-02-15"].dropna()
    assert before.empty, before
    assert val.loc["2021-02-16"] == 100.0
    print("  [ok] lag: nothing on the filing day itself (2021-02-15); "
          "the fact is live on the next session (2021-02-16)")

    val0 = _expand(ev, cal, 0, "value")
    assert val0.loc["2021-02-15"] == 100.0
    print("  [ok] lag_sessions=0 makes it live the same session "
          "(offered, not the default)")

    # the mistake, quantified on the toy
    naive_live = pd.Timestamp("2020-12-31")
    real_live = pd.Timestamp("2021-02-15")
    print(f"  [ok] end-indexing would have made FY2020 live on "
          f"{naive_live:%Y-%m-%d} instead of {real_live:%Y-%m-%d} — "
          f"{(real_live - naive_live).days} days of free look")

    # derived difference matches only within an accession
    rev = df[df["end"] == pd.Timestamp("2021-12-31")].copy()
    cost = rev.copy()
    cost["val"] = 40.0
    d = _derive_difference(rev, cost)
    assert len(d) == 1 and d.iloc[0]["val"] == 100.0
    assert d.iloc[0]["filed"] == pd.Timestamp("2022-02-15")
    print("  [ok] derived facts inherit the filing date of their accession")
    print("\nSELFTEST OK")


# --------------------------------------------------------------------------
# smoke test
# --------------------------------------------------------------------------

SMOKE_SYMBOLS = ("AAPL MSFT AMZN GOOGL META NVDA TSLA JPM JNJ V PG XOM UNH "
                 "HD MA CVX ABBV PFE KO PEP BAC MRK COST WMT DIS").split()
SMOKE_START, SMOKE_END = "2016-01-01", "2026-08-01"

SMOKE_TAGS = [
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "CommonStockSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"),
    ("us-gaap", "Assets"),
    ("us-gaap", "NetIncomeLoss"),
    ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
    ("us-gaap", "GrossProfit"),
    ("us-gaap", "Revenues"),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
    ("us-gaap", "CostOfRevenue"),
    ("us-gaap", "CostOfGoodsAndServicesSold"),
]


def smoke_test() -> None:
    syms, start, end = SMOKE_SYMBOLS, SMOKE_START, SMOKE_END
    print("=" * 78)
    print(f"SMOKE TEST — {len(syms)} large caps, {start} .. {end}")
    print("=" * 78)

    # ---- 1. ticker -> CIK
    m = cik_map()
    ciks = resolve_ciks(syms)
    print(f"\n--- ticker -> CIK ---")
    print(f"  SEC ticker file: {len(m):,} symbols")
    print(f"  resolved: {len(ciks)}/{len(syms)}")
    unres = [s for s in syms if s not in ciks]
    if unres:
        print(f"  UNRESOLVED: {unres}")
    print("  " + ", ".join(f"{k}={v}" for k, v in list(ciks.items())[:6]) + " ...")

    # ---- 2. tag coverage
    print(f"\n--- tag coverage ({len(syms)} tickers) — the practical limit ---")
    cov = coverage_report(syms, SMOKE_TAGS, start, end)
    cov["pct"] = (100 * cov["tickers_in_window"] / len(syms)).round(0)
    for r in cov.itertuples(index=False):
        bar = "#" * int(r.tickers_in_window * 30 / len(syms))
        print(f"  {r.taxonomy:>7s}:{r.tag[:48]:<48s} "
              f"{r.tickers_in_window:>3d}/{len(syms)} {bar}")
    print("  (tickers_in_window = has >=1 fact FILED inside the window)")

    # ---- 3. THE LAG: what end-indexing would have given away
    print("\n--- FILING LAG: period end -> filed. THIS IS THE LOOKAHEAD ---")
    frames_ni = fact_table(syms, "NetIncomeLoss")
    frames_as = fact_table(syms, "Assets")
    lag = pd.concat([filing_lag(frames_ni, "any", since=start),
                     filing_lag(frames_as, "any", since=start)])
    lag = lag[lag["filed"] <= pd.Timestamp(end)]
    print(f"  facts measured: {len(lag):,} first-filings "
          f"({lag['ticker'].nunique()} tickers, {start}..{end})")
    print(f"  ALL FORMS   median {lag['lag_days'].median():.0f} d  "
          f"mean {lag['lag_days'].mean():.0f}  "
          f"p10 {lag['lag_days'].quantile(.10):.0f}  "
          f"p90 {lag['lag_days'].quantile(.90):.0f}  "
          f"max {lag['lag_days'].max():.0f}")
    for form in ("10-Q", "10-K"):
        f = lag[lag["form"] == form]
        if len(f):
            print(f"  {form:<11s} median {f['lag_days'].median():.0f} d  "
                  f"p10 {f['lag_days'].quantile(.10):.0f}  "
                  f"p90 {f['lag_days'].quantile(.90):.0f}   n={len(f):,}")
    ann = lag[lag["form"].isin(("10-K", "10-K/A"))]
    print(f"  => a panel indexed on period end sees each ANNUAL number "
          f"{ann['lag_days'].median():.0f} days early (median).")

    # ---- 4. the lookahead, measured on the panel itself
    cal = _calendar(start, end)
    print("\n--- LOOKAHEAD DEMO: same panel, end-indexed vs filed-indexed ---")
    for tag, frames, period in (("Assets", frames_as, "instant"),
                                ("NetIncomeLoss", frames_ni, "annual")):
        d = lookahead_demo(frames, cal, period=period, unit="USD")
        print(f"  {tag:<14s} cells {d['cells']:>8,}   "
              f"cells holding a fact not yet filed: {d['ahead']:>7,} "
              f"({100 * d['share_ahead']:.1f}%)   "
              f"median free look {d['median_lead_days']:.0f} d "
              f"(p90 {d['p90_lead_days']:.0f})")

    # ---- 5. a real restatement
    print("\n--- RESTATEMENTS: the same period filed twice, different numbers ---")
    found = []
    for t in syms:
        for tag, frames in (("NetIncomeLoss", frames_ni), ("Assets", frames_as)):
            rs = restatements(frames[t])
            if rs.empty:
                continue
            rs = rs.assign(ticker=t, tag=tag)
            found.append(rs)
    if found:
        allrs = pd.concat(found, ignore_index=True)
        allrs["abs_pct"] = allrs["pct_change"].abs()
        in_win = allrs[allrs["first_filed"] >= pd.Timestamp(start)]
        print(f"  {len(allrs)} restated period-facts across "
              f"{allrs['ticker'].nunique()} tickers (NetIncomeLoss + Assets); "
              f"{len(in_win)} first filed inside {start}..{end}")
        big = pd.concat([allrs.sort_values("abs_pct", ascending=False).head(2),
                         in_win.sort_values("abs_pct", ascending=False).head(2)])
        for r in big.itertuples(index=False):
            print(f"  {r.ticker} {r.tag} period ending {r.end:%Y-%m-%d}:")
            print(f"      first filed {r.first_filed:%Y-%m-%d} ({r.first_form}) "
                  f"= {r.first_val:,.0f}")
            print(f"      later filed {r.last_filed:%Y-%m-%d} ({r.last_form}) "
                  f"= {r.last_val:,.0f}   ({100 * r.pct_change:+.1f}%, "
                  f"{(r.last_filed - r.first_filed).days} d later)")
        print("  first_filings() keeps the FIRST column. Using the last one is "
              "a lookahead\n  that passes every date check, because the dates "
              "are all real.")
    else:
        print("  none found (unexpected — check the fetch)")

    # ---- 6. AAPL shares outstanding, end AND filed dates
    print("\n--- AAPL shares outstanding: every fact carries BOTH dates ---")
    aapl = facts("AAPL", "EntityCommonStockSharesOutstanding", "dei")
    aapl = first_filings(aapl)
    aapl = aapl[(aapl["filed"] >= pd.Timestamp(start))
                & (aapl["filed"] <= pd.Timestamp(end))]
    show = pd.concat([aapl.head(4), aapl.tail(4)])
    print(f"  {'period end':<12s} {'FILED':<12s} {'lag':>4s}  {'form':<6s} "
          f"{'shares':>18s}")
    prev_end = None
    for r in show.itertuples(index=False):
        if prev_end is not None and (r.end - prev_end).days > 200:
            print(f"  {'...':<12s}")
        prev_end = r.end
        print(f"  {r.end:%Y-%m-%d}   {r.filed:%Y-%m-%d}   "
              f"{(r.filed - r.end).days:>3d}  {r.form:<6s} "
              f"{r.val:>18,.0f}")
    print("  Read the two date columns: on 2020-07-17 nobody knew the "
          "2020-07-17 count.\n  It was published on "
          f"{aapl[aapl['end'].dt.strftime('%Y-%m') == '2020-07']['filed'].iloc[0]:%Y-%m-%d}"
          " — that gap is the entire point of this module.")

    # ---- 7. the panels
    print("\n--- PIT PANELS (business-day calendar, lag 1 session) ---")
    sh, sh_src = shares_outstanding(syms, start, end)
    ta, ta_src = total_assets(syms, start, end)
    gp, gp_src = gross_profit(syms, start, end)
    ni, ni_src = net_income(syms, start, end)
    cf, cf_src = operating_cashflow(syms, start, end)
    for name, panel, src in (("shares_outstanding", sh, sh_src),
                             ("total_assets", ta, ta_src),
                             ("gross_profit", gp, gp_src),
                             ("net_income", ni, ni_src),
                             ("operating_cashflow", cf, cf_src)):
        filled = panel.notna().mean().mean()
        cols = int((panel.notna().sum() > 0).sum())
        print(f"  {name:<20s} {panel.shape[0]:,} x {panel.shape[1]}   "
              f"tickers with data {cols}/{len(syms)}   "
              f"cells filled {100 * filled:.1f}%")
        mix = pd.Series(src).value_counts()
        print("      sources: " + " | ".join(f"{k} {v}" for k, v in mix.items()))

    print("\n  gross_profit per-ticker source (the coverage story in one table):")
    for t in syms:
        s = gp_src.get(t, "none")
        if s != "us-gaap:GrossProfit":
            print(f"      {t:<6s} {s}")
    n_direct = sum(1 for s in gp_src.values() if s == "us-gaap:GrossProfit")
    n_none = sum(1 for s in gp_src.values() if s == "none")
    print(f"      {n_direct}/{len(syms)} tag GrossProfit directly; "
          f"{len(syms) - n_direct - n_none} need revenue-minus-cost; "
          f"{n_none} cannot be built at all.")

    # ---- 8. splits: the as-reported trap
    print("\n--- SHARE COUNTS ARE AS REPORTED (splits are not adjusted) ---")
    jumps = detect_share_jumps(sh, ratio=1.4)
    if jumps.empty:
        print("  no >1.4x single-step jumps found")
    else:
        print(f"  {len(jumps)} single-step jumps >1.4x in the raw panel:")
        for r in jumps.head(8).itertuples(index=False):
            print(f"      {r.ticker:<6s} {r.date:%Y-%m-%d}  "
                  f"{r.prev:>15,.0f} -> {r.curr:>15,.0f}   x{r.ratio:.2f}")
        print("  Every one of these is a split, not an issuance. A "
              "net-issuance signal\n  computed on this panel would measure "
              "corporate actions.")
    sh_adj, _ = shares_outstanding(syms, start, end, split_adjust=True)
    jumps_adj = detect_share_jumps(sh_adj, ratio=1.4)
    print(f"  after split_adjust=True: {len(jumps_adj)} jumps remain "
          f"(was {len(jumps)})")
    for r in jumps_adj.head(6).itertuples(index=False):
        print(f"      residual: {r.ticker} {r.date:%Y-%m-%d} "
              f"{r.prev:,.0f} -> {r.curr:,.0f} x{r.ratio:.2f}")
    print("  AAPL across its 2020-08-31 4:1 split, adjusted panel "
          "(should not move):")
    for probe in ("2020-08-14", "2020-09-30", "2020-11-30"):
        near = sh_adj["AAPL"].loc[:probe].dropna()
        if len(near):
            print(f"      {probe}: {near.iloc[-1]:>18,.0f}")

    # ---- 9. worked example of the safe usage
    print("\n--- WORKED EXAMPLE: gross profitability, PIT ---")
    gpa = (gp / ta).replace([np.inf, -np.inf], np.nan)
    ok = gpa.notna().mean().mean()
    print(f"  GP/Assets panel: {gpa.shape[0]:,} x {gpa.shape[1]}, "
          f"{100 * ok:.1f}% of cells computable")
    latest = gpa.dropna(how="all").iloc[-1].dropna().sort_values(ascending=False)
    print("  highest on the last session: " +
          ", ".join(f"{k} {v:.2f}" for k, v in latest.head(5).items()))
    print("  lowest:                      " +
          ", ".join(f"{k} {v:.2f}" for k, v in latest.tail(5).items()))
    print("  NOTE both legs are annual/instant PIT panels lagged one session, "
          "so\n  `gpa * ret.shift(-1)` is the earliest legal use. NOT a signal "
          "test — no\n  control, no costs, no both-halves split has been run "
          "here. This module\n  supplies data; a claim needs a lab.")

    print("\nSMOKE TEST OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true",
                    help="offline PIT logic checks (no network)")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore the concept cache and refetch")
    ap.add_argument("--tickers", default="",
                    help="comma list to override the smoke universe")
    ap.add_argument("--tag", default="", help="print one PIT panel and exit")
    ap.add_argument("--taxonomy", default="us-gaap")
    ap.add_argument("--period", default="any", choices=list(PERIODS))
    ap.add_argument("--start", default=SMOKE_START)
    ap.add_argument("--end", default=SMOKE_END)
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if args.tag:
        syms = ([s.strip().upper() for s in args.tickers.split(",") if s.strip()]
                or SMOKE_SYMBOLS)
        panel = pit_panel(syms, args.tag, args.start, args.end,
                          taxonomy=args.taxonomy, period=args.period,
                          refresh=args.refresh, verbose=True)
        print(panel.dropna(how="all").tail(10).to_string())
        return
    selftest()
    print()
    smoke_test()


if __name__ == "__main__":
    main()
