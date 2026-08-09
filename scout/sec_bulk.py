"""SEC bulk financial-statement data: the whole market's fundamentals in minutes.

WHY THIS EXISTS
---------------
`scout/fundamentals.py` reads the SEC's per-company XBRL API
(`companyconcept/CIK.../us-gaap/{tag}.json`). That is one HTTP request per
company PER TAG, politely rate-limited to ~10/s — so 500 companies x 6 tags
is 3,000 requests and several minutes, and a full-universe study is an hour.

The SEC also publishes the same data in bulk, and measured from this
container it downloads at **35 MB/s**:

    https://www.sec.gov/files/dera/data/financial-statement-data-sets/YYYYqQ.zip

Each quarterly ZIP is ~124 MB and contains every numeric fact from every
filing that quarter. All of 2016-2026 is ~42 quarters, ~5 GB, about two to
three minutes of wall clock. That is roughly a hundredfold speedup over the
per-company API, and it is the difference between "test this on 25 tickers"
and "test this on the whole universe".

THE FILES INSIDE EACH ZIP
-------------------------
    sub.txt   one row per SUBMISSION: adsh (accession), cik, name, form,
              period, FILED  <-- the point-in-time date, fy, fp
    num.txt   one row per NUMERIC FACT: adsh, tag, version, ddate (period
              end), qtrs (0 = instant, 1 = quarter, 4 = annual), uom, value
    pre.txt   presentation, tag.txt   tag definitions

Joining num -> sub on `adsh` attaches the FILED date to every fact, which is
the entire point: a backtest may use a fact from its filing date onward,
never from its period end. Using `ddate` instead of `filed` silently grants
three to six months of lookahead, and it is the single most common way a
fundamental backtest manufactures alpha that was never available.

This module keeps `qtrs` and `ddate` rather than flattening them, because a
"revenue" number means nothing without knowing whether it covers a quarter
or a year — mixing the two is the second most common error.

Run:
  python -m scout.sec_bulk --start 2016 --end 2026        # download + build
  python -m scout.sec_bulk --start 2023 --end 2024 --keep-zips
"""
from __future__ import annotations

import argparse
import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config

BASE = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
UA = {"User-Agent": "WeWillSee research davidmking7@gmail.com"}

CACHE_DIR = config.SCOUT_DIR / "cache_secbulk"
FACTS_PKL = CACHE_DIR / "facts.pkl"
TICKERS_JSON = CACHE_DIR / "company_tickers.json"

# Only these tags are kept. num.txt holds millions of rows per quarter and
# most of them are irrelevant; filtering at parse time is what keeps the
# whole build inside a couple of gigabytes of RAM.
DEFAULT_TAGS = (
    # shares outstanding -> net issuance (Pontiff-Woodgate)
    "CommonStockSharesOutstanding",
    "CommonStockSharesIssued",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "EntityCommonStockSharesOutstanding",
    # profitability (Novy-Marx)
    "GrossProfit", "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
    "CostOfRevenue", "CostOfGoodsAndServicesSold",
    # balance sheet / accruals
    "Assets", "Liabilities", "StockholdersEquity",
    "AssetsCurrent", "LiabilitiesCurrent",
    # cash flow and earnings
    "NetIncomeLoss", "NetCashProvidedByUsedInOperatingActivities",
    "PaymentsForRepurchaseOfCommonStock",
    "ResearchAndDevelopmentExpense",
)


def quarters(start_year: int, end_year: int) -> list[tuple[int, int]]:
    out = []
    for y in range(start_year, end_year + 1):
        for q in (1, 2, 3, 4):
            out.append((y, q))
    return out


def download_quarter(year: int, q: int, keep: bool = False) -> bytes | None:
    """Fetch one quarterly ZIP. Returns raw bytes, or None if not published
    yet (future quarters 404, which is expected near the present)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{year}q{q}.zip"
    if path.exists():
        return path.read_bytes()
    url = f"{BASE}/{year}q{q}.zip"
    r = requests.get(url, headers=UA, timeout=180)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    if keep:
        path.write_bytes(r.content)
    return r.content


def parse_quarter(blob: bytes, tags: set[str]) -> pd.DataFrame:
    """num.txt joined to sub.txt, filtered to `tags`.

    Returns columns [cik, adsh, tag, ddate, qtrs, uom, value, filed, form].
    `filed` is what a backtest is allowed to condition on; `ddate` is what it
    is NOT allowed to condition on."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        with z.open("sub.txt") as f:
            sub = pd.read_csv(f, sep="\t", low_memory=False,
                              usecols=["adsh", "cik", "form", "period", "filed", "fy", "fp"])
        with z.open("num.txt") as f:
            num = pd.read_csv(f, sep="\t", low_memory=False,
                              usecols=["adsh", "tag", "version", "ddate", "qtrs",
                                       "uom", "segments", "coreg", "value"])
    num = num[num["tag"].isin(tags)]
    # us-gaap only (version looks like "us-gaap/2023"); dei tags carry their own
    num = num[num["version"].astype(str).str.startswith(("us-gaap", "dei"))]
    df = num.merge(sub, on="adsh", how="inner")
    df["filed"] = pd.to_datetime(df["filed"], format="%Y%m%d", errors="coerce")
    df["ddate"] = pd.to_datetime(df["ddate"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["filed", "ddate", "value"])
    return df[["cik", "adsh", "tag", "ddate", "qtrs", "uom", "segments", "coreg",
               "value", "filed", "form"]]


def ticker_map() -> pd.DataFrame:
    """CIK -> ticker. Cached; the SEC file is small and changes slowly.

    One CIK can carry several tickers (share classes). Keeping them all and
    letting the caller pick is safer than guessing which class is 'the'
    stock — GOOGL/GOOG and BRK.A/BRK.B both matter."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if TICKERS_JSON.exists():
        raw = json.loads(TICKERS_JSON.read_text())
    else:
        r = requests.get(TICKERS_URL, headers=UA, timeout=60)
        r.raise_for_status()
        raw = r.json()
        TICKERS_JSON.write_text(json.dumps(raw))
    rows = [{"cik": int(v["cik_str"]), "ticker": str(v["ticker"]).upper(),
             "name": v.get("title", "")} for v in raw.values()]
    return pd.DataFrame(rows).drop_duplicates()


def build(start_year: int, end_year: int, tags=DEFAULT_TAGS,
          keep_zips: bool = False, verbose: bool = True) -> pd.DataFrame:
    """Download and parse every quarter into one tidy facts table."""
    tagset = set(tags)
    frames, missing = [], []
    t0 = time.time()
    for y, q in quarters(start_year, end_year):
        blob = download_quarter(y, q, keep=keep_zips)
        if blob is None:
            missing.append(f"{y}q{q}")
            continue
        df = parse_quarter(blob, tagset)
        frames.append(df)
        if verbose:
            print(f"  {y}q{q}: {len(df):>8,} facts   "
                  f"({time.time() - t0:5.0f}s elapsed)")
    if not frames:
        raise RuntimeError("no quarters downloaded")
    facts = pd.concat(frames, ignore_index=True)
    tm = ticker_map()
    facts = facts.merge(tm, on="cik", how="left")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    facts.to_pickle(FACTS_PKL)
    if verbose:
        print(f"\n{len(facts):,} facts, {facts['cik'].nunique():,} CIKs, "
              f"{facts['ticker'].nunique():,} tickers, "
              f"{facts['filed'].min().date()}..{facts['filed'].max().date()}")
        if missing:
            print(f"not published: {', '.join(missing)}")
        print(f"wrote {FACTS_PKL.name} in {time.time() - t0:.0f}s")
    return facts


def load(rebuild: bool = False, **kw) -> pd.DataFrame:
    if FACTS_PKL.exists() and not rebuild:
        return pd.read_pickle(FACTS_PKL)
    return build(**kw)


def pit_panel(facts: pd.DataFrame, tag: str, tickers: list[str],
              dates: pd.DatetimeIndex, qtrs: int | None = None,
              consolidated_only: bool = True) -> pd.DataFrame:
    """Point-in-time panel: value of `tag` KNOWABLE at each date.

    THREE disciplines are enforced here and all of them matter:

    0. CONSOLIDATED ROWS ONLY (`segments` and `coreg` both empty). This is the
       one that silently destroys share-count signals. 61% of
       CommonStockSharesOutstanding rows carry a `segments` dimension --
       `ClassOfStock=CommonClassA;`, `ClassOfStock=CommonClassB;` and so on --
       and the consolidated total is the row with NO segment. For Alphabet in
       2023 the file contains Class A 5.899bn, Class B 0.870bn, Class C 5.691bn
       AND the total 12.460bn; picking among them arbitrarily makes the series
       jump between 0.87bn and 12.46bn from quarter to quarter, which reads as
       repeated ±190% issuance. Ford does the same thing. Filtering to the
       unsegmented row is what makes the panel a company-level series at all.

    and the two that were already here:
      1. a fact appears only from its FILED date onward, never its period end;
      2. when the same (ticker, period) is filed more than once (restatements,
         10-K/A amendments), the FIRST filing wins — that is what was actually
         knowable at the time, and using the restated value is lookahead
         wearing an accountant's hat.

    `qtrs` filters the period length (0 = instantaneous/balance-sheet,
    1 = one quarter, 4 = annual). Mixing them silently is how a revenue
    signal ends up comparing annual figures to quarterly ones."""
    df = facts[(facts["tag"] == tag) & (facts["ticker"].isin(tickers))]
    if consolidated_only and "segments" in df.columns:
        df = df[df["segments"].isna() & df["coreg"].isna()]
    if qtrs is not None:
        df = df[df["qtrs"] == qtrs]
    if df.empty:
        return pd.DataFrame(index=dates, columns=tickers, dtype=float)
    # first filing of each (ticker, period) wins
    df = (df.sort_values("filed")
            .drop_duplicates(subset=["ticker", "ddate", "qtrs"], keep="first"))
    # latest fact known as of each date
    df = df.sort_values(["ticker", "filed", "ddate"])
    wide = (df.pivot_table(index="filed", columns="ticker", values="value",
                           aggfunc="last")
              .sort_index())
    tz = dates.tz
    if tz is not None:
        wide.index = wide.index.tz_localize(tz)
    out = wide.reindex(wide.index.union(dates)).ffill().reindex(dates)
    return out.reindex(columns=tickers)


def split_factors(symbols: list[str], start: str = "2016-01-01",
                  end: str = "2026-12-31") -> dict[str, list[tuple[pd.Timestamp, float]]]:
    """{symbol: [(ex_date, new/old), ...]} from Alpaca's corporate-actions feed."""
    from . import data_audit
    sp = data_audit.fetch_splits(symbols, start, end)
    out: dict[str, list[tuple[pd.Timestamp, float]]] = {}
    for _, s in sp.iterrows():
        try:
            f = float(s["new_rate"]) / float(s["old_rate"])
            ex = pd.Timestamp(s["ex_date"])
        except Exception:
            continue
        if f > 0 and abs(f - 1.0) > 1e-9:
            out.setdefault(s["symbol"], []).append((ex, f))
    for k in out:
        out[k].sort()
    return out


def adjust_facts_for_splits(df: pd.DataFrame,
                            factors: dict[str, list[tuple[pd.Timestamp, float]]]
                            ) -> pd.DataFrame:
    """Restate fact-level share counts in TODAY'S share terms.

    THE SUBTLETY THAT MAKES OR BREAKS THIS, learned the hard way from NVDA.
    A share count is expressed in the shares that existed WHEN THE FILING WAS
    MADE, and companies re-report prior periods in post-split terms in later
    filings. NVDA's own facts show it exactly:

        ddate 2021-01-31, filed 2021-02-26  ->   0.620bn   (pre 4:1 and 10:1)
        ddate 2021-01-31, filed 2022-03-18  ->   2.479bn   (post 4:1)
        ddate 2024-01-31, filed 2024-02-21  ->   2.464bn   (post 4:1, pre 10:1)
        ddate 2024-01-31, filed 2025-02-26  ->  24.643bn   (post both)

    Same period, three different correct numbers. So the adjustment a fact
    needs is the product of every split whose ex-date falls after ITS FILING
    DATE — not after the date you happen to be reading the panel on.

    Getting that wrong is invisible and destructive. My first version adjusted
    by the panel's observation date, which left a fact filed before a split but
    read after it under-adjusted by exactly the split factor: NVDA printed
    6.20bn (0.620 x 10, missing the x4) and 2.46bn (missing the x10) against a
    true ~24.5bn, showing as -137% then +140% "issuance" in consecutive years.
    It looked like dirty vendor data. It was arithmetic applied at the wrong
    index."""
    out = df.copy()
    mult = pd.Series(1.0, index=out.index)
    for sym, fl in factors.items():
        m = out["ticker"] == sym
        if not m.any():
            continue
        for ex, f in fl:
            mult.loc[m & (out["filed"] < ex)] *= f
    out["value"] = out["value"] * mult
    return out


SHARE_TAGS = (("CommonStockSharesOutstanding", 0),
              ("WeightedAverageNumberOfDilutedSharesOutstanding", 4),
              ("WeightedAverageNumberOfDilutedSharesOutstanding", 1),
              ("WeightedAverageNumberOfSharesOutstandingBasic", 4),
              ("WeightedAverageNumberOfSharesOutstandingBasic", 1))


def _despike(col: pd.Series, tol: float = 0.35) -> pd.Series:
    """Drop isolated single-observation spikes, working on DISTINCT VALUES.

    Even after the segment filter a handful of stray facts survive — NVDA
    prints 6.20bn and 2.46bn in single quarters against a stable ~24bn, which
    is a mis-scaled or mis-tagged filing rather than a corporate event.

    The subtlety that makes a naive version useless: this operates on a
    forward-filled DAILY panel, so a bad fact is repeated for ~60 sessions and
    its immediate neighbours are copies of itself. Comparing a point to
    yesterday therefore never sees a spike. The series is first collapsed to
    its distinct values (one row per change), despiked there, and then
    re-expanded — so "neighbour" means the previous and next REPORTED value,
    which is what the word was supposed to mean.

    A value is dropped when it differs from both surrounding reports by more
    than `tol` in log terms while those two agree with each other. A genuine
    issuance or buyback moves the level and leaves it moved, so real step
    changes survive."""
    v = col.dropna()
    if len(v) < 3:
        return col
    events = v[v != v.shift()]                 # one row per distinct value
    if len(events) < 3:
        return col
    lv = np.log(events)
    prev, nxt = lv.shift(1), lv.shift(-1)
    spike = (((lv - prev).abs() > tol) & ((lv - nxt).abs() > tol)
             & ((prev - nxt).abs() < tol)).fillna(False)
    if not spike.any():
        return col
    bad_values = set(events[spike].to_numpy())
    cleaned = v.where(~v.isin(bad_values))
    return cleaned.reindex(col.index).ffill()


def shares_panel(facts: pd.DataFrame, tickers: list[str], dates: pd.DatetimeIndex,
                 adjust: bool = True) -> pd.DataFrame:
    """Split-adjusted shares outstanding, point-in-time, with a tag fallback.

    No single tag covers the market, so each ticker takes the first tag in
    SHARE_TAGS that has data for it. The choice is made ONCE per ticker and
    held: switching tags mid-series manufactures fake issuance at the switch.

    Order of operations matters. Splits are applied at the FACT level, keyed on
    each fact's filing date (see adjust_facts_for_splits), and only then is the
    series forward-filled onto `dates`. Adjusting the forward-filled panel
    instead is wrong and silently so."""
    df = facts[facts["ticker"].isin(tickers)]
    if "segments" in df.columns:
        df = df[df["segments"].isna() & df["coreg"].isna()]
    df = df[df["value"] > 0]
    if adjust:
        df = adjust_facts_for_splits(df, split_factors(sorted(set(tickers))))

    out = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    chosen = {}
    tz = dates.tz
    for tk in tickers:
        for tag, q in SHARE_TAGS:
            d = df[(df["ticker"] == tk) & (df["tag"] == tag) & (df["qtrs"] == q)]
            if d.empty:
                continue
            # first filing of a period wins: what was knowable then, not the
            # later restatement
            d = (d.sort_values("filed")
                   .drop_duplicates(subset=["ddate", "qtrs"], keep="first"))
            ser = d.set_index("filed")["value"].sort_index()
            ser = ser[~ser.index.duplicated(keep="last")]
            if tz is not None:
                ser.index = ser.index.tz_localize(tz)
            col = ser.reindex(ser.index.union(dates)).ffill().reindex(dates)
            if col.notna().sum() > 0.3 * len(dates):
                out[tk] = col
                chosen[tk] = f"{tag}(q{q})"
                break
    out.attrs["tag_used"] = chosen
    return out


def net_issuance(facts: pd.DataFrame, tickers: list[str], dates: pd.DatetimeIndex,
                 lookback: int = 252) -> pd.DataFrame:
    """12-month log change in split-adjusted shares outstanding.

    Negative = net buyback. Pontiff-Woodgate (2008): managers issue when they
    believe the stock is overpriced and repurchase when underpriced, so this is
    a free quarterly read on insider valuation. Log change rather than percent
    so issuance and buybacks are symmetric."""
    sh = shares_panel(facts, tickers, dates)
    return (sh / sh.shift(lookback)).apply(lambda c: c.map(
        lambda v: float('nan') if not (v and v > 0) else __import__('math').log(v)))


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.sec_bulk")
    ap.add_argument("--start", type=int, default=2016)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--keep-zips", action="store_true",
                    help="keep the downloaded ZIPs (~124 MB each)")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    facts = load(rebuild=args.rebuild, start_year=args.start, end_year=args.end,
                 keep_zips=args.keep_zips)

    print("\n=== coverage by tag ===")
    cov = (facts.groupby("tag")
                .agg(facts_n=("value", "size"), tickers=("ticker", "nunique"))
                .sort_values("facts_n", ascending=False))
    print(cov.to_string())

    print(f"\n=== filing lag (period end -> filed) ===")
    lag_all = (facts["filed"] - facts["ddate"]).dt.days
    # The all-facts median is INFLATED and must not be quoted on its own: every
    # 10-K restates two or three prior years as comparatives, so most rows are
    # old periods re-reported inside a recent filing. The number that describes
    # the actual reporting delay is the lag of the NEWEST period in each filing.
    newest = facts.loc[facts.groupby("adsh")["ddate"].idxmax()]
    lag_new = (newest["filed"] - newest["ddate"]).dt.days
    print(f"all facts:          median {lag_all.median():>4.0f} d   "
          f"(INFLATED — every 10-K re-reports 2-3 years of comparatives)")
    print(f"newest period only: median {lag_new.median():>4.0f} d, "
          f"p90 {lag_new.quantile(0.9):.0f}, p99 {lag_new.quantile(0.99):.0f}"
          f"   <- the real reporting delay")
    print("The second number is the lookahead a backtest grants itself if it "
          "conditions\non period end instead of filing date. pit_panel uses "
          "filing date.")

    # restatement check
    dup = (facts.groupby(["ticker", "tag", "ddate", "qtrs"])["filed"]
                .nunique())
    print(f"\n=== restatements ===")
    print(f"{(dup > 1).sum():,} of {len(dup):,} (ticker, tag, period) cells were "
          f"filed more than once\n({100 * (dup > 1).mean():.1f}%) — pit_panel "
          f"keeps the FIRST filing.")

    print("\n=== example: AAPL shares outstanding, as knowable ===")
    ex = facts[(facts["ticker"] == "AAPL") &
               (facts["tag"] == "CommonStockSharesOutstanding")]
    if ex.empty:
        ex = facts[(facts["ticker"] == "AAPL") &
                   (facts["tag"] == "WeightedAverageNumberOfDilutedSharesOutstanding")]
    print(ex.sort_values("filed")[["ddate", "filed", "qtrs", "value", "form"]]
            .tail(8).to_string(index=False))


if __name__ == "__main__":
    main()
