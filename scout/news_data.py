"""News adapter: Benzinga headlines via Alpaca, mapped onto TRADING SESSIONS.

MECHANISM (why text is worth adding to this repo at all)
--------------------------------------------------------
Prices aggregate information; headlines are the *arrival* of it. Two frictions
make the arrival itself measurable rather than instantly priced: attention is
scarce (a story about a stock nobody is watching is absorbed slowly), and the
first story about a fact is not the fifth. Everything in here exists to make
those two things countable — a per-session count of stories, and a flag for
whether a story said something that was not already said in the last five days
— without pretending that a keyword scorer understands English.

This module makes NO claim of alpha. It is the plumbing three claims will
later be tested on, and it is written defensively because news studies fail in
one specific, well-known way.

THE #1 WAY NEWS STUDIES FOOL THEMSELVES: THE TIMESTAMP
------------------------------------------------------
`created_at` is wall-clock UTC. In winter 20:30 UTC is 15:30 ET — before the
bell. In summer the same 20:30 UTC is 16:30 ET — AFTER it. A study that
attributes both to "that day" is trading on news the market had not seen.
Measured on the smoke sample (30 large caps, Q1 2023, 7,615 symbol-rows),
18.8% of rows have to roll forward at all, and the two ways people actually
get this wrong land this many rows on an EARLIER session than they were
publishable for:
    ET calendar date, no close cutoff  ->  13.3% of rows too early
    UTC calendar date, no conversion   ->   9.6% of rows too early
One row in eight is a free look at the future — more than enough to
manufacture spectacular, fake alpha, and below it is measured in bps.

The rule implemented here, and the only one this module will ever use:

    1. convert created_at to US/Eastern (handles DST automatically),
    2. if the ET wall-clock time is BEFORE that day's close, the story belongs
       to that calendar day; if it is AT or AFTER the close, it belongs to the
       next calendar day,
    3. the attributed SESSION is the first row of `close_index` on or after
       that calendar day (so Saturday 10:00 ET, Friday 21:00 ET and a holiday
       all roll forward to the next actual session).

"the close" is 16:00 ET, except on the ~2-3 half-days a year the NYSE closes
at 13:00 ET (day after Thanksgiving, some Dec 24 / Jul 3) — the 23 such dates
in 2016-2026 are listed in EARLY_CLOSE_DATES. It is a small correction, but it
is a correction in the lookahead direction, so it is made.

WHAT THE ATTRIBUTION MEANS FOR THE CALLER (state this in any downstream test)
----------------------------------------------------------------------------
Panel row `t` holds the news a trader could have read BEFORE session t's
close. The earliest return it may therefore weight is close(t) -> close(t+1).
Concretely: `panel["n_headlines"].shift(1) * returns` is safe, and so is
`panel["n_headlines"] * returns.shift(-1)`; `panel["n_headlines"] * returns`
is NOT — that trades the same session's close on news timestamped up to a
minute before it. `audit_attribution()` prints the evidence that the roll
happens where it should, and __main__ runs it.

SENTIMENT: A CRUDE PROXY, SAID OUT LOUD
---------------------------------------
`score_headlines` is a Loughran-McDonald-*style* word count over 435 hand-typed
finance words in four lists (negative 194 / positive 129 / uncertainty 64 /
litigious 62) plus 41 repair phrases. It is not the LM dictionary (that is ~4k
words and a download); it is not a language model; it has no syntax beyond a
3-token negation flip. Documented failure modes, all real outputs:
"Beats Estimates But Warns On Guidance" scores +0.167 (should be negative);
"Company Reports Record Loss" scores 0.000 ("record" cancels "loss").
Treat the output as a noisy label, use it in aggregate, and never quote a
result that only survives at one threshold.

TEMPLATED WIRE CONTENT
----------------------
Measured with the classifier in this file on a 2,674-headline sample spanning
2016/2018/2020/2022/2025: 31.2% of Benzinga output tagged to large caps is
machine-written — 15.3% content-free wire ("12 Consumer Discretionary Stocks
Moving In Tuesday's Intraday Session", "Exxon Mobil Unusual Options Activity",
"If You Invested $1,000 In Apple Stock...") and 15.9% single-name analyst
actions. `is_templated` flags the first group only; analyst actions are
bot-written but they are about ONE company and they move prices, so they get
their own flag (`is_analyst_action`) and the caller decides.

A second, sharper filter is structural rather than textual: the tag count. One
2020-03-16 story was tagged to 2,568 symbols ("Stocks That Hit 52-Week Lows On
Monday"); a story tagged to hundreds of tickers carries no symbol-specific
information by construction. 6.3% of the sample carries >10 tags, and 82.6%
survives both filters. `n_tags` is kept on every row for exactly that reason.

KNOWN LIMITS (measured, not guessed)
------------------------------------
1. The API's start/end filter is on `updated_at`, not `created_at`: 0.35% of
   rows in the 2016 shards were CREATED outside the month they came back in
   (measured over 42,481 rows). Assembled over a long range this is harmless —
   the story is in some shard — but a story created in the final month of a
   range and revised after `end` is never fetched. Expect ~0.3% under-coverage
   in the last month of any range, and nowhere else.
2. `summary` is populated on only ~23% of stories and `content` is empty
   unless include_content is requested (this module does not request it —
   it triples payload size for text no downstream user has asked for yet).
3. The feed is one publisher. Benzinga is fast and broad on US equities but it
   is not the tape; absence of a headline is not absence of news.
4. Coverage is wildly uneven across names, and that is the data, not a bug:
   in Q1 2023 the smoke universe ran from TSLA at 18.4 stories/session to
   BRK.B at 0.2. Any cross-sectional news measure has to be normalized within
   the session or it will just rank stocks by how much Benzinga likes them.
5. The cached panel universe is point-in-time as of 2016 (see
   liquid_universe) — which means it EXCLUDES every stock added to the index
   after 2016. That is the deliberate trade: no survivorship, at the cost of
   no TSLA.

VERDICT (what this module is and is not)
----------------------------------------
Working adapter, verified end to end. It is DATA, not a result: no hypothesis
is tested here, no return is computed, and nothing in this file should be read
as evidence that news predicts anything. The one substantive finding is
negative and about the data itself: `source` is degenerate (every row is
Benzinga, and the field is empty before ~2021), so "source diversity" is not
an available axis on this feed — `author` is, and templated content is
concentrated in a handful of desk bylines.

HOW MUCH THE TIMESTAMP RULE IS WORTH, MEASURED
----------------------------------------------
`--lookahead-demo` runs the same crude tone signal against the same next-day
returns twice, changing only the attribution. Measured on the full cached
panel — 120 point-in-time names, 2016-01-02..2026-07-31, 464,430 symbol-rows,
2,655 daily observations, tercile long-short, t clustered by date:

    NAIVE   (UTC calendar date)   +6.42 bps/day   t=+3.55   H1 +9.62 | H2 +3.23
    CORRECT (this module's rule)  -2.32 bps/day   t=-1.30   H1 +0.23 | H2 -4.87

The naive number clears this repo's own t>3 publication bar and holds its sign
in both halves. It is entirely an artifact of the timestamp: 8.74 bps/day, or
about 22% a year, of alpha that does not exist. The correct number is a
sign-flipping non-result, which is what it should be. Every guardrail in
RESEARCH-AGENDA.md section 1 — both halves, t>3, date-clustered errors —
passes the fake one, because they all share the same corrupted index. This is
the single reason to use `attribute_sessions` and never `.dt.date`.

Usage:
  python -m scout.news_data                    # selftest + smoke test
  python -m scout.news_data --build-panel      # cache the liquid-120 panel
  python -m scout.news_data --panel-report     # describe the cached panel
  python -m scout.news_data --lookahead-demo   # price the timestamp mistake
  python -m scout.news_data --build-panel --start 2019-01-01
"""
import argparse
import hashlib
import json
import re
import time
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import config

NEWS_URL = "https://data.alpaca.markets/v1beta1/news"
PAGE_LIMIT = 50                 # hard API cap: limit=100 returns HTTP 400
MAX_SYMBOLS_PER_REQ = 150       # keep the query string sane; stories are deduped
ET = "US/Eastern"

# Shared 200 req/min budget across every agent running against this key.
# Take a bit over half and no more; a single thread at ~0.44 s/request already
# runs at ~135/min unthrottled, so this is a real cap, not decoration.
REQ_PER_MIN = 110
_MIN_INTERVAL = 60.0 / REQ_PER_MIN
_last_request = [0.0]

CACHE_PREFIX = "cache_news_"
MANIFEST = config.SCOUT_DIR / "cache_news_manifest.json"

# NYSE 13:00 ET half-days, 2016-2026 (day after Thanksgiving; Dec 24 and Jul 3
# when they fall on a weekday that is not itself a holiday). Best-effort list;
# a missing date costs ~3 hours of misattribution on ~1 day a year.
EARLY_CLOSE_DATES = frozenset(date.fromisoformat(d) for d in (
    "2016-11-25",
    "2017-07-03", "2017-11-24",
    "2018-07-03", "2018-11-23", "2018-12-24",
    "2019-07-03", "2019-11-29", "2019-12-24",
    "2020-11-27", "2020-12-24",
    "2021-11-26",
    "2022-11-25",
    "2023-07-03", "2023-11-24",
    "2024-07-03", "2024-11-29", "2024-12-24",
    "2025-07-03", "2025-11-28", "2025-12-24",
    "2026-11-27", "2026-12-24",
))
REGULAR_CLOSE_MIN = 16 * 60     # 16:00 ET
EARLY_CLOSE_MIN = 13 * 60       # 13:00 ET


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def _headers() -> dict:
    return {"APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY}


def _throttle() -> None:
    wait = _MIN_INTERVAL - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    _last_request[0] = time.time()


def _get(params: dict, tries: int = 6) -> dict:
    """One page, with exponential backoff on 429/5xx. Raises on hard failure."""
    for attempt in range(tries):
        _throttle()
        try:
            r = requests.get(NEWS_URL, headers=_headers(), params=params,
                             timeout=60)
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(min(30, 2 ** attempt))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429 or r.status_code >= 500:
            back = float(r.headers.get("Retry-After", 0)) or min(30, 2 ** attempt)
            time.sleep(back)
            continue
        raise RuntimeError(f"news API {r.status_code}: {r.text[:200]}")
    raise RuntimeError(f"news API kept failing after {tries} tries")


def _fetch_raw(symbols: list[str], start: str, end: str) -> list[dict]:
    """Every story tagged to any of `symbols` in [start, end), oldest first.

    Deduped by story id: a story tagged to symbols in two different request
    chunks comes back twice.
    """
    seen, out = set(), []
    for i in range(0, len(symbols), MAX_SYMBOLS_PER_REQ):
        chunk = symbols[i:i + MAX_SYMBOLS_PER_REQ]
        token = None
        while True:
            params = {"symbols": ",".join(chunk), "start": _rfc3339(start),
                      "end": _rfc3339(end), "limit": PAGE_LIMIT, "sort": "asc"}
            if token:
                params["page_token"] = token
            page = _get(params)
            for story in page.get("news", []):
                if story["id"] not in seen:
                    seen.add(story["id"])
                    out.append(story)
            token = page.get("next_page_token")
            if not token:
                break
    return out


def _rfc3339(day: str) -> str:
    return day if "T" in str(day) else f"{day}T00:00:00Z"


# --------------------------------------------------------------------------
# fetch + disk cache
# --------------------------------------------------------------------------

def _universe_key(symbols: list[str]) -> str:
    blob = ",".join(sorted(set(symbols))).encode()
    return hashlib.sha1(blob).hexdigest()[:10]


def _shard_path(key: str, month: str) -> Path:
    return config.SCOUT_DIR / f"{CACHE_PREFIX}{key}_{month}.pkl"


def _months(start: str, end: str) -> list[tuple[str, str, str]]:
    """[(label 'YYYY-MM', month_start, next_month_start), ...] spanning [start, end).

    Every shard covers a WHOLE calendar month even when the requested range
    starts or ends mid-month. That costs a little extra fetching at the two
    edges and buys the property that makes the cache safe: a shard on disk is
    always complete, so a later call for a wider range can trust it instead of
    silently inheriting a truncated month. fetch_news trims to the exact range
    after assembling.
    """
    lo = date.fromisoformat(str(start)[:10])
    hi = date.fromisoformat(str(end)[:10])
    out, cur = [], lo.replace(day=1)
    while cur < hi:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        out.append((cur.strftime("%Y-%m"), str(cur), str(nxt)))
        cur = nxt
    return out


def _to_frame(stories: list[dict], symbols: set[str] | None) -> pd.DataFrame:
    """Explode stories to one row per (story, tagged symbol we asked for)."""
    rows = []
    for s in stories:
        tags = s.get("symbols") or []
        n_tags = len(tags)
        keep = [t for t in tags if symbols is None or t in symbols]
        for t in keep:
            rows.append((s["created_at"], t, s.get("headline", "") or "",
                         s.get("summary", "") or "", s.get("source", "") or "",
                         s.get("author", "") or "", s["id"],
                         s.get("url", "") or "", n_tags))
    cols = ["created_at", "symbol", "headline", "summary", "source", "author",
            "id", "url", "n_tags"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
        return df
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    return df.sort_values(["created_at", "symbol"]).reset_index(drop=True)


def fetch_news(symbols: list[str], start: str, end: str, use_cache: bool = True,
               verbose: bool = True) -> pd.DataFrame:
    """Benzinga stories for `symbols` over [start, end), one row per tagged symbol.

    Columns: created_at (UTC tz-aware), symbol, headline, summary, source,
    author, id, url, n_tags. `n_tags` is how many tickers the ORIGINAL story
    carried (not how many survived the universe filter) — the cheapest and most
    reliable broad-tape filter this feed offers.

    Cached to scout/cache_news_<universe-hash>_<YYYY-MM>.pkl, one shard per
    calendar month. Sharding by month and keying by the universe (not the date
    range) means a second agent asking for a sub-range, or the same range plus
    one more month, re-uses everything already on disk and re-fetches only the
    gap. Shards are written as they complete, so an interrupted build is not
    lost.

    Caveat, measured: the API filters on `updated_at`, so ~0.35% of stories
    arrive in a month other than the one they were created in. The result is
    trimmed to [start, end) on `created_at`, which makes assembled ranges
    correct in the middle and ~0.3% short in the FINAL month only (a story
    created there and revised after `end` is never returned).
    """
    symbols = sorted(set(symbols))
    key = _universe_key(symbols)
    want = set(symbols)
    frames, fetched, cached = [], 0, 0
    for label, lo, hi in _months(start, end):
        path = _shard_path(key, label)
        if use_cache and path.exists():
            frames.append(pd.read_pickle(path))
            cached += 1
            continue
        t0 = time.time()
        part = _to_frame(_fetch_raw(symbols, lo, hi), want)
        part.to_pickle(path)
        frames.append(part)
        fetched += 1
        if verbose:
            print(f"  {label}: {len(part):6,} rows  ({time.time() - t0:5.1f}s)",
                  flush=True)
    if not frames:
        return _to_frame([], want)
    df = (pd.concat(frames, ignore_index=True)
          .drop_duplicates(subset=["id", "symbol"])
          .sort_values(["created_at", "symbol"]).reset_index(drop=True))
    lo_ts = pd.Timestamp(_rfc3339(start))
    hi_ts = pd.Timestamp(_rfc3339(end))
    df = df[(df["created_at"] >= lo_ts) & (df["created_at"] < hi_ts)]
    df = df.reset_index(drop=True)
    if verbose:
        print(f"  {len(df):,} rows  ({cached} months cached, {fetched} fetched)")
    _update_manifest(key, symbols, start, end, len(df))
    return df


def _update_manifest(key: str, symbols: list[str], start: str, end: str,
                     rows: int) -> None:
    """Advertise what is on disk so other agents can find it without an API call."""
    try:
        man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    except Exception:
        man = {}
    entry = man.get(key, {})
    shards = sorted(p.name for p in config.SCOUT_DIR.glob(f"{CACHE_PREFIX}{key}_*.pkl"))
    man[key] = {"n_symbols": len(symbols), "symbols": symbols,
                "first_month": shards[0][-11:-4] if shards else None,
                "last_month": shards[-1][-11:-4] if shards else None,
                "n_shards": len(shards),
                "last_range": [str(start), str(end)], "last_rows": rows,
                "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "built": entry.get("built", datetime.now(timezone.utc)
                                   .strftime("%Y-%m-%d"))}
    MANIFEST.write_text(json.dumps(man, indent=1))


# --------------------------------------------------------------------------
# session attribution — the part that must not be wrong
# --------------------------------------------------------------------------

def _session_index(close_index) -> pd.DatetimeIndex:
    idx = getattr(close_index, "index", close_index)
    idx = pd.DatetimeIndex(idx)
    if idx.tz is not None:
        idx = idx.tz_convert(ET).tz_localize(None)
    return idx.normalize()


def attribute_sessions(created_at: pd.Series, close_index) -> pd.Series:
    """UTC publication timestamps -> the trading session they may be acted on.

    Before that day's close -> that day (or the next session, if the day is not
    one). At or after the close -> the next session. Weekends, holidays and
    after-hours all roll forward. Returns NaT for stories published after the
    last session in `close_index` (nothing to attribute them to yet).
    """
    sessions = _session_index(close_index)
    et = pd.to_datetime(created_at, utc=True).dt.tz_convert(ET)
    wall = et.dt.tz_localize(None)                 # ET wall clock, naive
    day = wall.dt.normalize()
    minute = wall.dt.hour * 60 + wall.dt.minute
    cutoff = np.where(pd.Index(day.dt.date).isin(EARLY_CLOSE_DATES),
                      EARLY_CLOSE_MIN, REGULAR_CLOSE_MIN)
    eff = day + pd.to_timedelta((minute.to_numpy() >= cutoff).astype(int), unit="D")
    pos = sessions.searchsorted(pd.DatetimeIndex(eff), side="left")
    out = pd.Series(pd.NaT, index=created_at.index, dtype="datetime64[ns]")
    ok = pos < len(sessions)
    out[ok] = sessions[pos[ok]]
    return out


def audit_attribution(df: pd.DataFrame, close_index, n_examples: int = 4) -> dict:
    """Print the proof that the after-close roll fires, and return its stats.

    A control that costs nothing: if the roll were broken, `rolled` would be
    ~0% and the ET-hour histogram of same-day attributions would run past 16.
    """
    sessions = _session_index(close_index)
    sess = attribute_sessions(df["created_at"], close_index)
    et = df["created_at"].dt.tz_convert(ET)
    wall_day = et.dt.tz_localize(None).dt.normalize()
    valid = sess.notna()
    rolled = (sess > wall_day) & valid
    minute = et.dt.hour * 60 + et.dt.minute
    cutoff = np.where(pd.Index(wall_day.dt.date).isin(EARLY_CLOSE_DATES),
                      EARLY_CLOSE_MIN, REGULAR_CLOSE_MIN)
    after = minute.to_numpy() >= cutoff
    same_day_after_close = int((valid & ~rolled & after).sum())
    stats = {"rows": int(valid.sum()),
             "rolled_to_later_session": int(rolled.sum()),
             "rolled_pct": round(100 * rolled.sum() / max(int(valid.sum()), 1), 1),
             "published_at_or_after_close": int((valid & after).sum()),
             "VIOLATIONS_same_session_after_close": same_day_after_close,
             "unattributable_after_last_session": int((~valid).sum())}
    print("  attribution audit:", json.dumps(stats))
    assert same_day_after_close == 0, "LOOKAHEAD: after-close story kept same session"
    on_session = df["created_at"].dt.tz_convert(ET).dt.tz_localize(None) \
        .dt.normalize().isin(sessions)
    picks = df.index[valid & rolled & on_session][:n_examples]
    print(f"  {'UTC published':<20} {'ET published':<20} {'ET date':<11}"
          f" {'-> session':<11} roll")
    for i in picks:
        e = et.loc[i]
        print(f"  {df['created_at'].loc[i]:%Y-%m-%d %H:%M} UTC   "
              f"{e:%Y-%m-%d %H:%M} ET   {e:%Y-%m-%d}  "
              f"-> {sess.loc[i]:%Y-%m-%d}  +{(sess.loc[i] - e.normalize().tz_localize(None)).days}d")
    return stats


# --------------------------------------------------------------------------
# templated-wire detection (patterns read off the actual tape, not imagined)
# --------------------------------------------------------------------------

# Ordered: first match wins. Roundup columns must precede analyst_action so
# "Benzinga's Top Upgrades, Downgrades" is a column, not a rating change.
_CATEGORY_PATTERNS = [
    ("options_flow", re.compile(
        r"whale|unusual options|option[s]? alert|options activity|options market"
        r"|option trades|smart money|behind the scenes of .* options", re.I)),
    ("performance_gimmick", re.compile(
        r"if you (had )?(invested|bought)|\$[\d,]+ invested in|here'?s how much"
        r"|would (be|have been) worth|worth this much|how much you would have"
        r"|ways to get rich", re.I)),
    ("trending_social", re.compile(
        r"wallstreetbets|swaggy stocks|stocktwits|trending stocks|reddit", re.I)),
    ("earnings_calendar", re.compile(
        r"^earnings scheduled for|^(this|next) week'?s earnings"
        r"|earnings preview.*(week|ahead)|^\d+ stocks? reporting", re.I)),
    ("movers_list", re.compile(
        r"stocks? (moving|movers|hitting|that hit|which set|to watch|with whale)"
        r"|^\d+ (biggest )?movers|biggest movers from"
        r"|(pre-?market|intraday|after[- ]hours|regular) session\b"
        r"|52[- ]week (highs|lows)\b"
        r"|^\d+\s+[\w &]+ stocks\b", re.I)),
    ("market_wrap", re.compile(
        r"^(mid-?day|mid-?morning|mid-?afternoon|early|late)?[ -]*market update"
        r"|^the market in \d+ minutes|^market (wrap|recap|snapshot)"
        r"|^a peek into the markets|^benzinga pro"
        r"|^(us|u\.s\.) (stock )?(futures|markets|indices)\b"
        r"|^(s&p|dow|nasdaq)[^:]{0,30}(settles|closes|opens|futures)"
        r"|^stock market (pops|falls|rises|closes|opens)"
        r"|^top wall street forecasters", re.I)),
    ("column_series", re.compile(
        r"^the daily biotech pulse|^the week ahead in|^benzinga'?s top"
        r"|^fast money picks|final trades|^bulls and bears of the"
        r"|^analyst expectations for|^what \d+ analyst ratings"
        r"|^\d+ stocks to watch|^insider (buying|selling) (round ?up|activity)"
        r"|stocks insiders are (buying|selling)", re.I)),
    ("analyst_action", re.compile(
        r"\b(maintains|reiterates|initiates coverage|assumes coverage"
        r"|resumes coverage|upgrades|downgrades)\b"
        r"|\b(raises|lowers|cuts|boosts|announces) (the )?(pt|price target)\b"
        r"|price target to \$?\d", re.I)),
]

# Categories that carry no company-specific information. `analyst_action` is
# machine-written too, but it is SINGLE-NAME and it moves prices, so it is
# deliberately NOT swept into is_templated — use is_analyst_action() to treat
# it separately.
TEMPLATED_CATEGORIES = frozenset({
    "options_flow", "performance_gimmick", "trending_social",
    "earnings_calendar", "movers_list", "market_wrap", "column_series"})


def headline_category(headline: str) -> str:
    """One of TEMPLATED_CATEGORIES, 'analyst_action', or 'other'."""
    h = headline or ""
    for name, pat in _CATEGORY_PATTERNS:
        if pat.search(h):
            return name
    return "other"


def categorize(headlines: pd.Series) -> pd.Series:
    return headlines.fillna("").map(headline_category)


def is_templated(headline) -> "bool | pd.Series":
    """True for machine-written wire content that is not about one company.

    Accepts a string or a Series. Measured coverage on a 2,674-headline
    multi-era sample: ~14% templated by text, plus ~16% analyst_action which
    this function deliberately does NOT flag. Combine with `n_tags` for the
    structural filter (see is_broadtape).
    """
    if isinstance(headline, pd.Series):
        return categorize(headline).isin(TEMPLATED_CATEGORIES)
    return headline_category(headline) in TEMPLATED_CATEGORIES


def is_analyst_action(headline) -> "bool | pd.Series":
    if isinstance(headline, pd.Series):
        return categorize(headline).eq("analyst_action")
    return headline_category(headline) == "analyst_action"


def is_broadtape(n_tags, max_tags: int = 10) -> "bool | pd.Series":
    """Structural noise filter: a story tagged to > max_tags tickers cannot be
    carrying much information about any one of them. Independent of wording,
    so it catches templates this file never saw."""
    return n_tags > max_tags


def source_breakdown(df: pd.DataFrame, top: int = 10) -> dict[str, pd.DataFrame]:
    """Volume and templated-share by source and by author.

    The finding this exists to surface: `source` is degenerate on this feed
    (Benzinga only, and blank before ~2021), so the useful axis is `author`.
    """
    d = df.drop_duplicates(subset=["id"]).copy()
    d["category"] = categorize(d["headline"])
    d["templated"] = d["category"].isin(TEMPLATED_CATEGORIES)
    out = {}
    for field in ("source", "author"):
        g = (d.assign(**{field: d[field].replace("", "(blank)")})
             .groupby(field)
             .agg(stories=("id", "size"), templated_pct=("templated", "mean"),
                  median_tags=("n_tags", "median"))
             .sort_values("stories", ascending=False))
        g["templated_pct"] = (100 * g["templated_pct"]).round(1)
        out[field] = g.head(top)
    return out


# --------------------------------------------------------------------------
# sentiment — Loughran-McDonald STYLE, hand-typed, deliberately small
# --------------------------------------------------------------------------
# Written from the finance/headline domain, not downloaded. Four lists in the
# LM spirit: negative and positive tone, plus uncertainty and litigious, which
# LM found matter independently of tone. Lists overlap on purpose ("lawsuit" is
# both negative and litigious) because the four counts are reported separately.
# This is a bag of words. It has no idea what a sentence means.

NEGATIVE_WORDS = frozenset("""
plunge plunges plunged plunging plummet plummets plummeted slump slumps slumped
sluggish sink sinks sank sinking tumble tumbles tumbled tumbling slide slides
slid crash crashes crashed dive dives crater craters cratered tank tanks tanked
drop drops dropped fall falls fell falling decline declines declined declining
slash slashes slashed cut cuts cutting miss misses missed missing shortfall
weak weaker weakness soft softer disappoint disappoints disappointing
downgrade downgrades downgraded underperform underperforms underweight bearish
warn warns warned warning halt halts halted suspend suspends suspended
recall recalls recalled probe probes probed investigation investigating
subpoena lawsuit lawsuits sue sues sued fraud fraudulent misconduct scandal
bankruptcy bankrupt insolvency default defaults delist delisted delisting
restructuring layoff layoffs fired resign resigns resigned resignation ousted
writedown writeoff impairment loss losses lossmaking deficit contraction
delay delays delayed setback setbacks failure fails failed failing
breach hack hacked cyberattack outage shutdown strike boycott
tariff tariffs sanction sanctions penalty penalties fine fined violation
glut oversupply downturn recession slowdown headwind headwinds
concerns worries worried pressure pressured struggles struggling struggle
selloff worst negative deteriorate deteriorating downside
reject rejects rejected refuses refused cancel cancels cancelled canceled
scrapped scraps halting curbs curb litigation dilution downbeat pessimistic
overvalued fraudulently stumbles stumble slipping slips
""".split())

POSITIVE_WORDS = frozenset("""
surge surges surged surging soar soars soared soaring jump jumps jumped
rally rallies rallied rallying climb climbs climbed gain gains gained
rise rises rose rising advance advances advanced spike spikes
beat beats exceeded exceeds exceeding outperform outperforms outperformed
upgrade upgrades upgraded overweight bullish outperformer
record records strong stronger strength robust solid healthy resilient
growth grows growing profit profits profitable
breakthrough approval approves approved clearance authorized
win wins won awarded contract partnership collaboration alliance
launch launches launched expansion expands expanding
boost boosts boosted raise raises raised hike hikes lifted lifts
dividend buyback buybacks repurchase accretive upside optimistic confident
momentum milestone tops topped best leading leader innovative efficiency
synergies upbeat favorable positive rebound rebounds rebounded recovery
recovers recovering surpass surpasses surpassed acquire acquires acquisition
premium outsized blockbuster strengthened improving improved improves
""".split())

UNCERTAINTY_WORDS = frozenset("""
may might could possible possibly uncertain uncertainty unclear unknown
potential potentially approximate appears appear seems seem believe believes
expect expects expected anticipate anticipates estimate estimates estimated
assume assumes forecast forecasts projected preliminary tentative pending
speculation speculative rumor rumors rumored reportedly reported exploring
considering weighing mulls mulling eyes eyeing reviewing contingent
volatile volatility risk risks risky ambiguous cautious caution question
questions doubt doubts likely unlikely
""".split())

LITIGIOUS_WORDS = frozenset("""
lawsuit lawsuits sue sues sued suing litigation court courts judge jury
plaintiff plaintiffs defendant settlement settle settles settled subpoena
indictment indicted prosecutor prosecutors antitrust regulator regulators
regulatory probe investigation injunction appeal appeals ruling ruled verdict
allegation allegations alleged alleges allege fine fined penalty penalties
violation violations noncompliance compliance decree arbitration
testimony deposition sec doj ftc attorney counterclaim
patent infringement infringing trademark copyright
""".split())

# Multi-word phrases the bag of words gets wrong on its own. Matched against
# the normalized headline string; each contributes to pos or neg directly.
NEGATIVE_PHRASES = (
    "cuts guidance", "guidance cut", "lowers guidance", "cuts price target",
    "lowers price target", "profit warning", "going concern", "class action",
    "steps down", "worse than expected", "below estimates", "misses estimates",
    "short seller", "chapter 11", "cuts outlook", "lowers outlook",
    "falls short", "under pressure", "sinks after", "slides after",
    "halted for", "wells notice", "restates results", "accounting probe",
)
POSITIVE_PHRASES = (
    "raises guidance", "boosts guidance", "raises outlook", "lifts outlook",
    "beats estimates", "better than expected", "above estimates",
    "raises price target", "boosts price target", "tops estimates",
    "record revenue", "record profit", "all-time high", "52-week high",
    "share buyback", "dividend increase", "raises dividend",
)
NEGATORS = frozenset("no not never without fails failed fail unable "
                     "cannot denies denied lacks".split())

_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> tuple[str, list[str]]:
    flat = _TOKEN_RE.sub(" ", str(text).lower()).strip()
    return flat, flat.split()


# Phrases are matched against the NORMALIZED headline, in which every
# non-alphanumeric run has become a single space. Normalize them the same way
# or entries like "all-time high" and "52-week high" could never fire.
_NEG_PHRASES = tuple(_normalize(p)[0] for p in NEGATIVE_PHRASES)
_POS_PHRASES = tuple(_normalize(p)[0] for p in POSITIVE_PHRASES)


def score_headline(headline: str) -> dict:
    """Word counts + a tone score for one headline. See score_headlines."""
    flat, toks = _normalize(headline)
    pos = neg = 0
    for i, w in enumerate(toks):
        negated = any(t in NEGATORS for t in toks[max(0, i - 3):i])
        if w in POSITIVE_WORDS:
            neg += 1 if negated else 0
            pos += 0 if negated else 1
        elif w in NEGATIVE_WORDS:
            pos += 1 if negated else 0
            neg += 0 if negated else 1
    for p in _NEG_PHRASES:
        if p in flat:
            neg += 1
    for p in _POS_PHRASES:
        if p in flat:
            pos += 1
    unc = sum(1 for w in toks if w in UNCERTAINTY_WORDS)
    lit = sum(1 for w in toks if w in LITIGIOUS_WORDS)
    n = max(len(toks), 1)
    return {"n_words": len(toks), "pos": pos, "neg": neg, "unc": unc,
            "lit": lit, "tone": (pos - neg) / n}


def score_headlines(series: pd.Series) -> pd.DataFrame:
    """Loughran-McDonald-STYLE scoring of a Series of headlines.

    Returns a DataFrame aligned to `series` with columns
    [n_words, pos, neg, unc, lit, tone], tone = (pos - neg) / n_words, the LM
    normalization. Positive/negative words inside 3 tokens of a negator flip
    sign; a short phrase list repairs the cases a bag of words most obviously
    breaks on ("cuts guidance", "beats estimates").

    CRUDE PROXY, said once more: ~330 hand-typed words, no syntax, no context.
    "Record Loss" scores positive. Use it in aggregate; do not build a claim
    that only exists at one cutoff.
    """
    if len(series) == 0:
        return pd.DataFrame(columns=["n_words", "pos", "neg", "unc", "lit", "tone"],
                            index=series.index)
    uniq = pd.Index(series.fillna("").unique())
    table = pd.DataFrame([score_headline(h) for h in uniq], index=uniq)
    out = table.reindex(series.fillna("").to_numpy())
    out.index = series.index
    return out


# --------------------------------------------------------------------------
# novelty — "has this symbol already been told this?"
# --------------------------------------------------------------------------

_STOP = frozenset("""
a an the of in on for to and or with at by from as is are was were be been
this that these those it its it's after before over under into out up down
what why how when who whom which s t new says say said amid vs
""".split())


def _content_tokens(headline: str) -> frozenset:
    _, toks = _normalize(headline)
    return frozenset(w for w in toks if w not in _STOP and len(w) > 2)


def novelty_flags(df: pd.DataFrame, days: int = 5,
                  threshold: float = 0.6) -> pd.Series:
    """True where a headline is NOT a near-duplicate of the same symbol's own
    stories in the prior `days` calendar days.

    Similarity = Jaccard overlap of content tokens (stopwords and 1-2 character
    tokens dropped). >= `threshold` against ANY prior story for that symbol
    inside the window marks the row stale. Deliberately cheap: no embeddings,
    no ML, O(stories x window) with a per-symbol deque.

    Strictly backward-looking — the comparison set for a story at time t
    contains only stories with created_at < t, so this flag is computable in
    real time and adds no lookahead.

    WARM-UP EDGE: the history is whatever is in `df`. The first `days` of any
    slice therefore see an empty (or short) look-back and are biased toward
    novel. Fetch `days` extra at the front and drop the warm-up, or accept a
    5-day burn-in at the start of the sample.
    """
    if df.empty:
        return pd.Series(dtype=bool, index=df.index)
    heads = df["headline"].fillna("").to_numpy()
    # Force nanoseconds explicitly. pandas 2 infers datetime64[us] when a frame
    # is built from Timestamps, and a bare .astype("int64") would then hand
    # back MICROseconds — silently widening the window by 1000x. The selftest
    # exists because that bug shipped once in this file.
    times = (df["created_at"].dt.tz_convert("UTC").dt.tz_localize(None)
             .to_numpy(dtype="datetime64[ns]").astype("int64"))
    syms = df["symbol"].to_numpy()
    window_ns = int(days) * 86_400 * 1_000_000_000
    order = np.lexsort((times, syms))                        # by symbol, then time
    cache: dict[str, frozenset] = {}
    out = np.ones(len(df), dtype=bool)
    cur_sym, hist = None, deque()
    for p in order:
        s = syms[p]
        if s != cur_sym:
            cur_sym, hist = s, deque()
        t = times[p]
        while hist and t - hist[0][0] > window_ns:
            hist.popleft()
        h = heads[p]
        toks = cache.get(h)
        if toks is None:
            toks = cache[h] = _content_tokens(h)
        novel = bool(toks)      # an empty headline says nothing new by definition
        if novel:
            for _, prior in hist:
                if not prior:
                    continue
                inter = len(toks & prior)
                if inter and inter / len(toks | prior) >= threshold:
                    novel = False
                    break
        out[p] = novel
        hist.append((t, toks))
    return pd.Series(out, index=df.index)


# --------------------------------------------------------------------------
# the panel
# --------------------------------------------------------------------------

def daily_news_panel(df: pd.DataFrame, close_index, max_tags: int = 10,
                     novelty_days: int = 5, novelty_threshold: float = 0.6,
                     verbose: bool = False) -> dict[str, pd.DataFrame]:
    """Story-level rows -> {name: time x symbol DataFrame}, indexed by SESSION.

    Row t holds everything published before session t's close (see the module
    docstring). The earliest return any of these frames may weight is
    close(t) -> close(t+1): shift the panel forward one bar, or shift returns
    back one bar, but never multiply row t by session t's own return.

    Frames returned
      n_headlines  stories tagged to the symbol, attributed to that session
      n_novel      of those, ones not near-duplicating the prior 5 days
      is_novel     bool: n_novel > 0
      n_specific   not templated AND n_tags <= max_tags (the usable subset)
      n_templated  machine-written wire (movers lists, market wraps, ...)
      n_analyst    analyst rating / price-target actions (single-name, kept apart)
      tone         mean LM-style tone of that session's stories (NaN if none)
      tone_specific  same, over n_specific stories only
      neg_words / pos_words  raw counts, so a caller can re-normalize

    Counts are 0 on sessions with no news; tone frames are NaN there — a
    quiet day has no sentiment, and filling it with 0 would silently label it
    neutral-and-observed.
    """
    sessions = _session_index(close_index)
    cols = sorted(set(df["symbol"])) if not df.empty else []
    empty = pd.DataFrame(0.0, index=sessions, columns=cols)
    if df.empty:
        out = {k: empty.copy() for k in
               ("n_headlines", "n_novel", "n_specific", "n_templated",
                "n_analyst", "pos_words", "neg_words")}
        out["tone"] = empty * np.nan
        out["tone_specific"] = empty * np.nan
        out["is_novel"] = empty.astype(bool)
        return out

    d = df.copy()
    d["session"] = attribute_sessions(d["created_at"], sessions)
    dropped = int(d["session"].isna().sum())
    d = d[d["session"].notna()]
    if verbose and dropped:
        print(f"  {dropped:,} rows published after the last session — dropped")

    d["novel"] = (d["is_novel"] if "is_novel" in d.columns
                  else novelty_flags(d, novelty_days, novelty_threshold))
    cat = categorize(d["headline"])
    d["templated"] = cat.isin(TEMPLATED_CATEGORIES)
    d["analyst"] = cat.eq("analyst_action")
    d["specific"] = (~d["templated"]) & (~is_broadtape(d["n_tags"], max_tags))
    sc = score_headlines(d["headline"])
    d["tone"] = sc["tone"].to_numpy()
    d["pos"] = sc["pos"].to_numpy()
    d["neg"] = sc["neg"].to_numpy()

    def pivot(values, how="sum"):
        p = d.pivot_table(index="session", columns="symbol", values=values,
                          aggfunc=how)
        return p.reindex(index=sessions, columns=cols)

    d["one"] = 1.0
    out = {
        "n_headlines": pivot("one").fillna(0.0),
        "n_novel": pivot("novel").fillna(0.0),
        "n_specific": pivot("specific").fillna(0.0),
        "n_templated": pivot("templated").fillna(0.0),
        "n_analyst": pivot("analyst").fillna(0.0),
        "pos_words": pivot("pos").fillna(0.0),
        "neg_words": pivot("neg").fillna(0.0),
        "tone": pivot("tone", "mean"),
    }
    spec = d[d["specific"]]
    out["tone_specific"] = (spec.pivot_table(index="session", columns="symbol",
                                             values="tone", aggfunc="mean")
                            .reindex(index=sessions, columns=cols)
                            if not spec.empty else empty * np.nan)
    out["is_novel"] = (out["n_novel"] > 0)
    return out


# --------------------------------------------------------------------------
# the cached panel universe (point-in-time, no survivorship)
# --------------------------------------------------------------------------

PANEL_START = "2016-01-01"
PANEL_END = "2026-08-01"
PANEL_N = 120
PANEL_PICKLE = config.SCOUT_DIR / "cache_news_liquid120.pkl"
PANEL_SYMBOLS_JSON = config.SCOUT_DIR / "cache_news_liquid120_symbols.json"


def liquid_universe(n: int = PANEL_N, asof: str = "2016-01-04",
                    measure_year: int = 2016) -> list[str]:
    """The `n` most liquid S&P 500 members AS OF `asof`, ranked by median daily
    dollar volume during `measure_year` only.

    Survivorship: this uses scout/pit.py point-in-time membership and measures
    liquidity with data from the START of the sample, so the list is knowable
    on 2016-01-04 and contains the names that later vanished (BRCM, CELG, EMC,
    TWX, ESRX, MON, AET, PXD ...) rather than today's survivors. That is the
    whole point — picking "the 120 most liquid names today" and running them
    back to 2016 is the standard way to invent 1-3pp of fake performance, and
    this repo has already retracted numbers to that family of error.

    The cost is real and must be stated: names that JOINED the index later
    (TSLA, and every post-2016 addition) are absent. A study that needs them
    should call fetch_news() with its own list and own the bias.
    """
    from . import pit
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    members = sorted(pit.members(asof))
    client = StockHistoricalDataClient(config.ALPACA_API_KEY,
                                       config.ALPACA_SECRET_KEY)
    frames = []
    for i in range(0, len(members), 150):
        req = StockBarsRequest(symbol_or_symbols=members[i:i + 150],
                               timeframe=TimeFrame.Day,
                               start=datetime(measure_year, 1, 1),
                               end=datetime(measure_year, 12, 31),
                               adjustment=Adjustment.ALL, feed=DataFeed.SIP)
        bars = client.get_stock_bars(req).df
        if not bars.empty:
            frames.append(bars.reset_index())
    allb = pd.concat(frames, ignore_index=True)
    allb["dv"] = allb["close"] * allb["volume"]
    dv = allb.groupby("symbol")["dv"].median().sort_values(ascending=False)
    return list(dv.index[:n])


def build_panel(start: str = PANEL_START, end: str = PANEL_END,
                n: int = PANEL_N) -> pd.DataFrame:
    """Fetch + cache the shared downstream panel. Resumable: monthly shards."""
    if PANEL_SYMBOLS_JSON.exists():
        syms = json.loads(PANEL_SYMBOLS_JSON.read_text())
    else:
        print(f"deriving the point-in-time liquid-{n} universe ...")
        syms = liquid_universe(n)
        PANEL_SYMBOLS_JSON.write_text(json.dumps(syms, indent=1))
    print(f"universe: {len(syms)} symbols (point-in-time S&P 500 as of 2016-01-04, "
          f"ranked by 2016 dollar volume)")
    print(f"range: {start} .. {end}")
    t0 = time.time()
    df = fetch_news(syms, start, end)
    df.to_pickle(PANEL_PICKLE)
    print(f"\ncached {len(df):,} symbol-rows "
          f"({df['id'].nunique():,} distinct stories) -> {PANEL_PICKLE.name}"
          f"  [{(time.time() - t0) / 60:.1f} min]")
    print(f"coverage: {df['created_at'].min()} .. {df['created_at'].max()}")
    return df


def load_panel() -> pd.DataFrame:
    """Downstream entry point: the cached liquid-120 news panel."""
    if not PANEL_PICKLE.exists():
        raise FileNotFoundError(
            f"{PANEL_PICKLE} missing — run `python -m scout.news_data --build-panel`")
    return pd.read_pickle(PANEL_PICKLE)


def _attribute_naive(created_at: pd.Series, sessions: pd.DatetimeIndex) -> pd.Series:
    """The WRONG mapping, implemented only so its damage can be measured:
    take the UTC calendar date and use the first session on or after it. No
    timezone conversion, no close cutoff. This is what a news study does by
    accident, and lookahead_demo() prices the mistake."""
    day = pd.to_datetime(created_at, utc=True).dt.tz_localize(None).dt.normalize()
    pos = sessions.searchsorted(pd.DatetimeIndex(day), side="left")
    out = pd.Series(pd.NaT, index=created_at.index, dtype="datetime64[ns]")
    ok = pos < len(sessions)
    out[ok] = sessions[pos[ok]]
    return out


def _tone_frame(df: pd.DataFrame, sessions: pd.DatetimeIndex,
                naive: bool) -> pd.DataFrame:
    sess = (_attribute_naive(df["created_at"], sessions) if naive
            else attribute_sessions(df["created_at"], sessions))
    d = df.assign(session=sess)
    d = d[d["session"].notna()]
    d = d.assign(tone=score_headlines(d["headline"])["tone"].to_numpy())
    return (d.pivot_table(index="session", columns="symbol", values="tone",
                          aggfunc="mean")
            .reindex(index=sessions))


def lookahead_demo(df: pd.DataFrame | None = None, days: int = 4000) -> dict:
    """Price the timestamp mistake, in basis points, on this repo's own data.

    THE EXPERIMENT. Same panel, same sentiment scorer, same outcome — only the
    session attribution differs:

      treatment  NAIVE : story's UTC calendar date -> that (or the next) session
      control    CORRECT: ET wall clock, roll at the close (this module's rule)

    Signal: mean LM-style tone of a symbol's stories on session t. Outcome: the
    NEXT session's return, close(t) -> close(t+1) — the earliest return the
    correct mapping is allowed to touch. Score = mean daily spread between the
    top and bottom tone terciles of the names that had news that session.

    WHAT EACH OUTCOME MEANS, stated before the numbers:
      - If NAIVE >> CORRECT, the naive mapping is reading tomorrow's news, and
        every published number built on it is an artifact.
      - If they are equal, the roll does not matter on this data and the whole
        EARLY_CLOSE / DST apparatus in this file is ceremony.
      - CORRECT being near zero is the EXPECTED, boring result. It is not
        evidence that news is useless; it is one crude signal at one horizon.

    t-statistics cluster by DATE (the daily spread series is the unit of
    observation) because same-session outcomes are correlated, exactly as
    scout/calibrate.py does. Both halves are reported. Gross of costs: the
    comparison is between two attributions, and costs are identical for both.
    """
    from . import data
    if df is None:
        df = load_panel()
    syms = sorted(df["symbol"].unique())
    print(f"loading daily bars for {len(syms)} symbols ...")
    close = data.daily_ohlcv(syms, days=days)["close"]
    sessions = _session_index(close)
    ret = close.copy()
    ret.index = sessions
    ret = ret.pct_change()
    fwd = ret.shift(-1)                       # close(t) -> close(t+1). THE SHIFT.

    lo, hi = df["created_at"].min(), df["created_at"].max()
    print(f"news {lo:%Y-%m-%d} .. {hi:%Y-%m-%d} | {len(df):,} symbol-rows | "
          f"{len(sessions):,} sessions")
    out = {}
    for label, naive in (("CORRECT (this module's rule)", False),
                         ("NAIVE   (UTC calendar date)", True)):
        tone = _tone_frame(df, sessions, naive).reindex(columns=fwd.columns)
        rank = tone.rank(axis=1, pct=True)
        top = fwd.where(rank >= 2 / 3)
        bot = fwd.where(rank <= 1 / 3)
        breadth = tone.notna().sum(axis=1)
        spread = (top.mean(axis=1) - bot.mean(axis=1))[breadth >= 6].dropna()
        half = len(spread) // 2
        rows = {"n_days": len(spread), "bps": 1e4 * spread.mean(),
                "t": spread.mean() / (spread.std(ddof=1) / np.sqrt(len(spread))),
                "h1_bps": 1e4 * spread.iloc[:half].mean(),
                "h2_bps": 1e4 * spread.iloc[half:].mean()}
        out[label] = rows
        print(f"  {label}: {rows['bps']:+7.2f} bps/day  t={rows['t']:+5.2f}  "
              f"(H1 {rows['h1_bps']:+.2f} | H2 {rows['h2_bps']:+.2f})  "
              f"n={rows['n_days']:,} days")
    naive = out["NAIVE   (UTC calendar date)"]
    correct = out["CORRECT (this module's rule)"]
    gap = naive["bps"] - correct["bps"]
    print(f"\n  THE MISTAKE IS WORTH {gap:+.2f} bps/day "
          f"= {252 * gap / 100:+.1f}% a year of pure artifact "
          f"(252 sessions, simple, gross).")
    if naive["t"] >= 3 > correct["t"]:
        print(f"  Note the t-statistics: the NAIVE version clears this repo's "
              f"own t>3 publication\n  bar ({naive['t']:+.2f}) while the correct "
              f"one does not ({correct['t']:+.2f}). Every guardrail in\n  "
              f"RESEARCH-AGENDA.md section 1 would have passed it through.")
    flip = correct["h1_bps"] * correct["h2_bps"] < 0
    print(f"  Halves of the CORRECT row: {correct['h1_bps']:+.2f} / "
          f"{correct['h2_bps']:+.2f} bps — "
          + ("SIGN FLIP across halves, i.e. noise."
             if flip else "same sign, but see the t-stat before believing it."))
    print("  The CORRECT row is not a strategy: it is one crude signal at one "
          "horizon,\n  reported only as the baseline the naive number has to be "
          "compared against.")
    return out


def panel_report(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Year-by-year and both-halves description of the cached panel.

    Not a result — a warning label. This tape is NOT stationary: Benzinga's
    output, its templated share and its per-symbol concentration all move a
    lot across 2016-2026. Any news measure that is not cross-sectionally
    normalized WITHIN a session is partly measuring the publisher's staffing.
    Downstream agents should read this table before designing a signal, and
    should expect the two halves of the sample to differ.
    """
    if df is None:
        df = load_panel()
    d = df.drop_duplicates(subset=["id"]).copy()
    d["year"] = d["created_at"].dt.year
    cat = categorize(d["headline"])
    d["templated"] = cat.isin(TEMPLATED_CATEGORIES)
    d["analyst"] = cat.eq("analyst_action")
    d["broadtape"] = is_broadtape(d["n_tags"])
    d["tone"] = score_headlines(d["headline"])["tone"].to_numpy()
    tab = d.groupby("year").agg(stories=("id", "size"),
                                templated_pct=("templated", "mean"),
                                analyst_pct=("analyst", "mean"),
                                broadtape_pct=("broadtape", "mean"),
                                median_tags=("n_tags", "median"),
                                mean_tone=("tone", "mean"))
    for c in ("templated_pct", "analyst_pct", "broadtape_pct"):
        tab[c] = (100 * tab[c]).round(1)
    tab["mean_tone"] = tab["mean_tone"].round(4)
    print("\n--- panel by year (distinct stories) ---")
    print(tab.to_string())
    mid = d["created_at"].quantile(0.5)
    halves = d.assign(half=np.where(d["created_at"] < mid, "H1", "H2"))
    hs = halves.groupby("half").agg(stories=("id", "size"),
                                    templated_pct=("templated", "mean"),
                                    mean_tone=("tone", "mean"),
                                    symbols=("symbol", "nunique"))
    hs["templated_pct"] = (100 * hs["templated_pct"]).round(1)
    hs["mean_tone"] = hs["mean_tone"].round(4)
    print(f"\n--- both halves (split at {mid:%Y-%m-%d}) ---")
    print(hs.to_string())
    print("  Read this as a stationarity warning, not a finding: volume and "
          "mix differ across halves,\n  so any absolute news-count threshold "
          "fitted on one half will not mean the same thing in the other.")
    return tab


# --------------------------------------------------------------------------
# smoke test
# --------------------------------------------------------------------------

SMOKE_SYMBOLS = ("AAPL MSFT AMZN GOOGL META NVDA TSLA BRK.B JPM JNJ V PG XOM "
                 "UNH HD MA CVX ABBV PFE KO PEP BAC MRK COST WMT DIS CSCO ADBE "
                 "CRM NFLX").split()


def smoke_test() -> None:
    start, end = "2023-01-01", "2023-04-01"
    print("=" * 78)
    print(f"SMOKE TEST — {len(SMOKE_SYMBOLS)} large caps, {start} .. {end}")
    print("=" * 78)
    df = fetch_news(SMOKE_SYMBOLS, start, end)
    print(f"\nrows (symbol-story pairs): {len(df):,}")
    print(f"distinct stories:          {df['id'].nunique():,}")
    print(f"symbols with news:         {df['symbol'].nunique()} of {len(SMOKE_SYMBOLS)}")
    print(f"created_at range (UTC):    {df['created_at'].min()} .. {df['created_at'].max()}")

    from . import data
    print("\nloading daily bars for the session calendar ...")
    bars = data.daily_ohlcv(SMOKE_SYMBOLS, days=1350)
    close = bars["close"]
    sessions = _session_index(close)
    sessions = sessions[(sessions >= "2023-01-01") & (sessions < "2023-04-08")]
    print(f"sessions in window: {len(sessions)}  "
          f"({sessions[0]:%Y-%m-%d} .. {sessions[-1]:%Y-%m-%d})")

    # ---- headlines per symbol per session
    panel = daily_news_panel(df, sessions, verbose=True)
    n = panel["n_headlines"]
    flat = n.stack()
    print("\n--- headlines per symbol per session (all symbol-sessions) ---")
    print(f"  symbol-sessions: {flat.size:,}   with >=1 story: "
          f"{int((flat > 0).sum()):,} ({100 * (flat > 0).mean():.1f}%)")
    print(f"  mean {flat.mean():.2f} | median {flat.median():.0f} | "
          f"p90 {flat.quantile(.90):.0f} | p99 {flat.quantile(.99):.0f} | "
          f"max {flat.max():.0f}")
    busiest = flat.sort_values(ascending=False).head(3)
    for (d0, s0), v in busiest.items():
        print(f"  busiest: {s0} on {d0:%Y-%m-%d}: {v:.0f} stories")
    print("  per-symbol mean stories/session:")
    per = n.mean().sort_values(ascending=False)
    print("    top:  " + ", ".join(f"{s} {v:.1f}" for s, v in per.head(5).items()))
    print("    tail: " + ", ".join(f"{s} {v:.1f}" for s, v in per.tail(5).items()))
    print(f"  novelty: {100 * panel['n_novel'].sum().sum() / max(n.sum().sum(), 1):.1f}%"
          f" of attributed stories are novel vs the prior 5 days"
          f" (the first 5 days of any slice are warm-up and biased novel)")
    print(f"  templated: {100 * panel['n_templated'].sum().sum() / max(n.sum().sum(), 1):.1f}%"
          f" | analyst actions: "
          f"{100 * panel['n_analyst'].sum().sum() / max(n.sum().sum(), 1):.1f}%"
          f" | specific: "
          f"{100 * panel['n_specific'].sum().sum() / max(n.sum().sum(), 1):.1f}%")

    # ---- sentiment extremes
    uniq = df.drop_duplicates(subset=["id"])[["headline", "n_tags"]].copy()
    sc = score_headlines(uniq["headline"])
    uniq = pd.concat([uniq.reset_index(drop=True), sc.reset_index(drop=True)], axis=1)
    uniq = uniq[uniq["n_words"] >= 6]
    uniq["category"] = categorize(uniq["headline"])

    def extremes(frame, label):
        print(f"\n--- 5 most NEGATIVE headlines ({label}) ---")
        for _, r in frame.sort_values("tone").head(5).iterrows():
            print(f"  {r['tone']:+.3f} (neg {r['neg']:.0f}/pos {r['pos']:.0f})  "
                  f"{r['headline'][:98]}")
        print(f"--- 5 most POSITIVE headlines ({label}) ---")
        for _, r in frame.sort_values("tone", ascending=False).head(5).iterrows():
            print(f"  {r['tone']:+.3f} (neg {r['neg']:.0f}/pos {r['pos']:.0f})  "
                  f"{r['headline'][:98]}")

    extremes(uniq, "all stories")
    spec = uniq[(~uniq["category"].isin(TEMPLATED_CATEGORIES))
                & (uniq["category"] != "analyst_action")
                & (uniq["n_tags"] <= 10)]
    extremes(spec, f"company-specific only, n={len(spec):,}")
    print(f"\n  tone distribution: mean {uniq['tone'].mean():+.4f} | "
          f"share non-zero {100 * (uniq['tone'] != 0).mean():.1f}% | "
          f"uncertainty words/headline {uniq['unc'].mean():.2f} | "
          f"litigious {uniq['lit'].mean():.2f}")
    print("  category mix (distinct stories):")
    mix = uniq["category"].value_counts()
    print("    " + " | ".join(f"{k} {100 * v / len(uniq):.1f}%"
                              for k, v in mix.items()))

    # ---- source / author breakdown
    br = source_breakdown(df, top=10)
    print("\n--- top sources by volume (distinct stories) ---")
    print(br["source"].to_string())
    print("  NOTE: the `source` field is degenerate on this feed — Benzinga "
          "only, and blank before ~2021.\n  Use `author`:")
    print("\n--- top 10 authors by volume ---")
    print(br["author"].to_string())

    # ---- the timestamp proof
    print("\n--- AFTER-CLOSE ROLL: worked examples + audit ---")
    audit_attribution(df, sessions)
    _worked_example(df, sessions)
    _control_checks(df, sessions, panel)
    print("\nSMOKE TEST OK")


def _worked_example(df: pd.DataFrame, sessions) -> None:
    """Real stories on each side of the 16:00 ET line, traced end to end, plus
    the cost of getting it wrong."""
    idx = _session_index(sessions)
    et = df["created_at"].dt.tz_convert(ET)
    sess = attribute_sessions(df["created_at"], idx)
    wall = et.dt.tz_localize(None)
    day = wall.dt.normalize()
    is_session_day = day.isin(idx)
    minute = et.dt.hour * 60 + et.dt.minute
    ok = sess.notna()
    cases = (
        ("BEFORE close, trading day", ok & is_session_day & (minute < 16 * 60)),
        ("AFTER close,  trading day", ok & is_session_day & (minute >= 20 * 60)),
        ("FRIDAY night", ok & (wall.dt.dayofweek == 4) & (minute >= 17 * 60)),
        ("SATURDAY morning", ok & (wall.dt.dayofweek == 5) & (minute < 12 * 60)),
    )
    print("  Four real stories, one pipeline:")
    for label, mask in cases:
        hits = df.index[mask]
        if len(hits) == 0:
            print(f"    [{label}] no example in this sample")
            continue
        i = hits[len(hits) // 2]
        e, s = et.loc[i], sess.loc[i]
        gap = (s - e.tz_localize(None).normalize()).days
        print(f"    [{label}] {df.loc[i, 'symbol']:<5} "
              f"{df.loc[i, 'created_at']:%Y-%m-%d %H:%M} UTC "
              f"= {e:%a %Y-%m-%d %H:%M} ET  ->  session {s:%a %Y-%m-%d} (+{gap}d)")
        print(f"          \"{df.loc[i, 'headline'][:84]}\"")
        # the invariant each case exists to prove
        if label.startswith("BEFORE"):
            assert s == e.tz_localize(None).normalize(), (i, s)
        else:
            assert s > e.tz_localize(None).normalize(), (i, s)
    # The two ways this is actually got wrong, priced in rows on this sample.
    def _naive(days_series):
        pos = idx.searchsorted(pd.DatetimeIndex(days_series), side="left")
        good = pos < len(idx)
        s = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
        s[good] = idx[pos[good]]
        return int(((s != sess) & ok).sum())

    utc_day = df["created_at"].dt.tz_localize(None).dt.normalize()
    n = max(int(ok.sum()), 1)
    et_wrong, utc_wrong = _naive(day), _naive(utc_day)
    print(f"  COST OF GETTING IT WRONG, on {n:,} rows:")
    print(f"    ET date, no close cutoff  (converted the tz, forgot the bell): "
          f"{et_wrong:,} rows ({100 * et_wrong / n:.1f}%) too early")
    print(f"    UTC date, no conversion   (`.dt.date` on a UTC column):        "
          f"{utc_wrong:,} rows ({100 * utc_wrong / n:.1f}%) too early")
    print("    Every one of those is a free look at news the market had not "
          "seen when that\n    session closed. --lookahead-demo turns the second "
          "one into basis points.")


def _control_checks(df: pd.DataFrame, sessions, panel: dict) -> None:
    """Cheap controls on the plumbing itself (this module makes no return claim,
    so these check the ADAPTER, not an edge)."""
    print("\n--- controls on the adapter ---")
    # 1. counts conserve: every attributable row lands in exactly one cell
    sess = attribute_sessions(df["created_at"], sessions)
    attributable = int(sess.notna().sum())
    in_panel = int(panel["n_headlines"].to_numpy().sum())
    print(f"  conservation: {attributable:,} attributable rows -> "
          f"{in_panel:,} counted in the panel "
          f"({'OK' if attributable == in_panel else 'MISMATCH'})")
    assert attributable == in_panel
    # 2. shuffled-headline control for the sentiment scorer: tone on real
    #    headlines vs tone on headlines with their words shuffled across the
    #    corpus. A bag of words is order-free, so these MUST match — if they
    #    diverge, the scorer is reading something it should not.
    rng = np.random.default_rng(0)
    heads = df.drop_duplicates(subset=["id"])["headline"].head(3000)
    real = score_headlines(heads)["tone"].mean()
    shuffled = heads.map(lambda h: " ".join(rng.permutation(h.split())))
    shuf = score_headlines(shuffled)["tone"].mean()
    print(f"  word-order control: tone real {real:+.4f} vs word-shuffled "
          f"{shuf:+.4f} (a bag of words is order-free, so these should be "
          f"near-equal;\n      the 3-token negation window and the phrase list "
          f"are the only order effects)")
    # 3. novelty control: duplicate every headline 1 day later; the copy must
    #    be flagged stale.
    sub = df.head(400).copy()
    dup = sub.copy()
    dup["created_at"] = dup["created_at"] + pd.Timedelta(days=1)
    dup["id"] = dup["id"] + 10**9
    both = pd.concat([sub, dup], ignore_index=True)
    flags = novelty_flags(both)
    caught = 1 - flags.iloc[len(sub):].mean()
    print(f"  novelty control: {100 * caught:.1f}% of exact 1-day-later "
          f"duplicates flagged stale (should be ~100%)")
    assert caught > 0.95


def selftest() -> None:
    """Pin the attribution rules on synthetic timestamps — no API, no market
    data. Runs in under a second, so there is no excuse for a regression here.
    """
    sessions = pd.DatetimeIndex([
        "2023-01-13",                                  # Fri
        "2023-01-17", "2023-01-18",                    # Tue (Mon 16th = MLK), Wed
        "2023-02-17", "2023-02-21",                    # Fri, Tue (Mon 20th holiday)
        "2023-07-14", "2023-07-17",                    # Fri, Mon
        "2023-11-22", "2023-11-24", "2023-11-27",      # Wed, half-day Fri, Mon
    ])
    cases = [
        # (UTC timestamp, expected session, what it proves)
        ("2023-01-13T15:00:00Z", "2023-01-13", "10:00 ET, before close -> same day"),
        ("2023-01-13T20:30:00Z", "2023-01-13", "20:30 UTC in WINTER = 15:30 ET -> same day"),
        ("2023-07-14T20:30:00Z", "2023-07-17", "20:30 UTC in SUMMER = 16:30 ET -> next session"),
        ("2023-01-13T21:00:00Z", "2023-01-17", "16:00 ET exactly -> rolls (Fri -> Tue, MLK Mon)"),
        ("2023-01-14T17:00:00Z", "2023-01-17", "Saturday noon ET -> next session"),
        ("2023-02-17T22:00:00Z", "2023-02-21", "Fri night -> skips Presidents' Day"),
        ("2023-11-24T18:30:00Z", "2023-11-27", "13:30 ET on the HALF DAY -> next session"),
        ("2023-11-24T17:30:00Z", "2023-11-24", "12:30 ET on the half day -> same session"),
        ("2023-11-22T20:00:00Z", "2023-11-22", "15:00 ET on a full day -> same session"),
    ]
    ts = pd.Series(pd.to_datetime([c[0] for c in cases], utc=True))
    got = attribute_sessions(ts, sessions)
    print("--- attribution rules (synthetic) ---")
    for (raw, want, why), g in zip(cases, got):
        mark = "ok " if g == pd.Timestamp(want) else "FAIL"
        print(f"  [{mark}] {raw} -> {g:%Y-%m-%d} (want {want})  {why}")
        assert g == pd.Timestamp(want), (raw, g, want)
    # future story: nothing to attribute it to
    late = attribute_sessions(pd.Series(pd.to_datetime(["2030-01-01T00:00:00Z"])),
                              sessions)
    assert late.isna().all()
    print("  [ok ] a story after the last session is NaT, not silently clamped")

    print("--- lexicon ---")
    for text, sign in (("Tesla Stock Plunges After Guidance Cut", "neg"),
                       ("Apple Beats Estimates, Raises Dividend", "pos"),
                       ("Pfizer Fails To Beat Revenue Estimates", "neg"),
                       ("Boeing Halted After Recall Probe", "neg"),
                       ("Nvidia Hits All-Time High On Record Revenue", "pos")):
        s = score_headline(text)
        ok = (s["tone"] < 0) if sign == "neg" else (s["tone"] > 0)
        print(f"  [{'ok ' if ok else 'FAIL'}] {s['tone']:+.3f} "
              f"(pos {s['pos']} neg {s['neg']}) {text}")
        assert ok, text
    bad = score_headline("Company Reports Record Loss")
    print(f"  [known] 'Company Reports Record Loss' scores {bad['tone']:+.3f} — "
          f"the documented failure mode of a bag of words")

    print("--- categories ---")
    for text, want in (
            ("12 Consumer Discretionary Stocks Moving In Tuesday's Intraday Session", "movers_list"),
            ("Exxon Mobil Unusual Options Activity", "options_flow"),
            ("If You Invested $1,000 In Apple Stock When Donald Trump Sold...", "performance_gimmick"),
            ("Earnings Scheduled For February 6, 2025", "earnings_calendar"),
            ("Top 15 Trending Stocks On WallStreetBets As Of Tuesday", "trending_social"),
            ("Mid-Afternoon Market Update: Dow Falls 270 Points", "market_wrap"),
            ("The Daily Biotech Pulse: Setback For DBV", "column_series"),
            ("Goldman Sachs Maintains Buy on Tesla, Lowers Price Target to $205", "analyst_action"),
            ("Apple Tells Suppliers To Build Fewer Components For AirPods", "other")):
        got_cat = headline_category(text)
        print(f"  [{'ok ' if got_cat == want else 'FAIL'}] {got_cat:<20} {text[:62]}")
        assert got_cat == want, (text, got_cat, want)

    print("--- novelty ---")
    base = pd.Timestamp("2023-03-01", tz="UTC")
    demo = pd.DataFrame({
        "created_at": [base, base + pd.Timedelta("1D"), base + pd.Timedelta("2D"),
                       base + pd.Timedelta("9D")],
        "symbol": ["AAPL"] * 4,
        "headline": ["Apple Tells Suppliers To Build Fewer AirPods Components",
                     "Apple Tells Suppliers To Build Fewer AirPods Components",
                     "Apple Wins Patent Dispute Over Smartwatch Sensors",
                     "Apple Tells Suppliers To Build Fewer AirPods Components"],
    })
    flags = novelty_flags(demo).tolist()
    print(f"  {flags}  (first=new, second=echo within 5d, third=different story, "
          f"fourth=same text but 9d later so novel again)")
    assert flags == [True, False, True, True]
    print("\nSELFTEST OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build-panel", action="store_true",
                    help="fetch + cache the shared liquid-120 panel")
    ap.add_argument("--selftest", action="store_true",
                    help="offline checks of attribution/lexicon/novelty (no API)")
    ap.add_argument("--panel-report", action="store_true",
                    help="describe the cached panel (by year and both halves)")
    ap.add_argument("--lookahead-demo", action="store_true",
                    help="measure what the naive timestamp mapping manufactures")
    ap.add_argument("--start", default=PANEL_START)
    ap.add_argument("--end", default=PANEL_END)
    ap.add_argument("--n", type=int, default=PANEL_N)
    args = ap.parse_args()
    if args.selftest:
        selftest()
    elif args.lookahead_demo:
        lookahead_demo()
    elif args.panel_report:
        panel_report()
    elif args.build_panel:
        panel_report(build_panel(args.start, args.end, args.n))
    else:
        selftest()
        print()
        smoke_test()


if __name__ == "__main__":
    main()
