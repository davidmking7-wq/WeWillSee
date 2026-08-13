"""Intraday adapter: Alpaca minute bars -> session-level frames.

Everything in this repo so far has been built on daily CLOSES. A close hides
two economically different holding periods that happen to share a ticker.

MECHANISM
---------
The overnight window (16:00 -> 09:30) is a *closed-market risk transfer*: the
inventory cannot be hedged, information accumulates with no continuous price,
and whoever holds it demands compensation — so the risk premium is paid at the
open, in the gap. The intraday window (09:30 -> 16:00) is the opposite: a
continuous, competitive, liquidity-rich auction where market makers can and do
flatten, so it pays mostly for providing liquidity, not for bearing overnight
risk. Lou-Polk-Skouras (JFE 2019) is the reference decomposition, and this
module exists to make it — and any other clock-time question — computable here.
(Read the VERDICT before believing that paragraph: the strong form of it does
not survive contact with 2018-2026 data.)

The same bars answer a second question the repo has never been able to ask: is
a volatility estimate built from 5-minute returns (realised volatility) a
better forecast of tomorrow's move than one built from daily closes? Theory
says yes and by a lot — RV converges to integrated variance as the sampling
interval shrinks, whereas a squared daily return is a one-observation estimate
of the same quantity (Andersen-Bollerslev 1998). That is a measurement claim,
not an anomaly, so it should replicate cleanly or the plumbing is wrong.

METHOD
------
`fetch_minute_bars` pulls /v2/stocks/bars (SIP, adjustment=all) with
pagination, a shared token-bucket rate limiter, 429/5xx retry with exponential
backoff, and a per-symbol disk cache under scout/cache_intraday_*.pkl that
extends itself rather than refetching.

`session_frames` turns those bars into date x symbol DataFrames. Four traps
are handled explicitly, because each of them silently corrupts a study:

1. EXTENDED HOURS. Alpaca returns bars from 04:00 to 20:00 ET. Taking the
   first bar of the day as "the open" therefore gives a 04:00 pre-market print
   on thin volume, which destroys any overnight-return study. DEFAULT HERE IS
   REGULAR SESSION ONLY, 09:30 <= t < 16:00 ET, bar-start time in US/Eastern
   (so DST is handled by the tz database, not by an hour offset).
   `extended=True` is available and loudly documented. Measured cost of
   getting this wrong, GOOGL+AMZN Q1-2024: mean |overnight_ret| falls from
   0.73% to 0.26% and mean |intraday_ret| rises from 0.85% to 1.23% — the
   overnight gap does not disappear, it is silently relabelled as intraday.

2. HALF-DAYS. On a 13:00 early close Alpaca KEEPS EMITTING BARS to 15:55 off
   after-hours prints (verified on SPY 2018-07-03: 39 five-minute bars print
   after the 13:00 auction, the last at 15:55). Naively taking the last bar
   before 16:00 gives the wrong close, and 15% of that session's "regular"
   volume still lands after 13:05, so a volume-share rule needs a tuned
   threshold. `early_close_ratio` instead compares pooled dollar volume in
   [12:55,13:05) against [15:45,16:00) — the closing auction is in exactly one
   of them — which separates by two orders of magnitude and needs no tuning.
   The result is cross-checked against the hardcoded NYSE calendar in
   `EARLY_CLOSES` and disagreements are printed, not swallowed. Missing
   sessions get no row; nothing is forward-filled or invented.

3. NEAR-EMPTY SESSIONS. Alpaca's tape has occasional data gaps: in this
   sample 23 symbol-sessions carry fewer than half a session's bars and 21 of
   them carry exactly ONE, so open_px == close_px, intraday_ret collapses to
   zero and the NEXT day's overnight return is measured against a close that
   never happened (AAPL/MSFT/AMZN/GOOGL/NVDA all on 2018-05-02 and 05-03).
   `min_bar_frac` (default 0.5) blanks them; blanking close_px also blanks the
   following prev_close, so no fabricated gap survives. Lower it for illiquid
   universes where a sparse session can be genuine.

4. ADJUSTMENT. See below. This one was the expensive find.

Two smaller things the code is explicit about rather than quiet about: the
closing AUCTION cannot be recovered from bars (it is stamped 16:00:00 and
shares that bar with early after-hours prints), so `close_px` is the last
continuous-session print unless `official_close=True`; and the cache holds
ADJUSTED prices whose factor is anchored to the present, so it drifts from a
fresh pull by any dividend paid after it was written.

THE ADJUSTMENT FINDING (read this before trusting any overnight number)
----------------------------------------------------------------------
Minute bars and scout/data.py daily bars carry the SAME adjustment. Measured
over 10 symbols x ~2150 sessions, the session close rebuilt from bars differs
from the daily bar by a MEDIAN of 1.1e-4 in log units with no signed drift
(|t| <= 3.0 on all ten, largest annualised drift 0.71%/yr) — and that residual
is the closing auction, not the adjustment: it is what `official_closes`
exists to explain. So the two tapes are consistent. That is the good news and
it is only half the question, because the shared adjustment is INCOMPLETE:

    Alpaca's adjustment=all does not apply the AAPL 4:1 split of 2020-08-31.

AAPL closes 484.24 on 2020-08-28 and 125.17 on 2020-08-31 in adjustment=all
daily bars *and* in adjustment=all minute bars — a fabricated -74.2% overnight
return. The split is in Alpaca's own /v1/corporate-actions feed (ex_date
2020-08-31, 4:1), so the bar-adjustment pipeline simply missed it. TSLA's 5:1
on the SAME DAY is applied correctly, as are NVDA 2021 4:1 and 2024 10:1, so
this is a per-symbol data defect, not a convention.

**This affects scout/data.py too** — every daily study in this repo that
touched AAPL over 2020-08-31 has a -74% return in it.

`split_events` + `unapplied_splits` diagnose it from the corporate-actions
feed (a split is "unapplied" when the ex-date price ratio sits at the split
ratio instead of near 1.0), and `fetch_minute_bars(repair_splits=True)`, the
default, back-adjusts pre-ex-date bars by old_rate/new_rate. `--audit` prints
the whole audit for any symbol list.

VERDICT (measured: SPY + 9 large caps, 5Min SIP bars, regular session only,
split-repaired, 2156 sessions 2018-01-02..2026-07-31, 3,069,719 bars)
--------------------------------------------------------------------------
1. THE ADAPTER WORKS AND FOUND A BUG IN THE REPO'S EXISTING DATA. That is the
   deliverable: `--selftest` passes 13 assertions on synthetic bars with a
   known answer, the volume-derived early-close calendar matches the hardcoded
   NYSE list exactly (18/18, zero disagreements either way), and the audit
   caught the unapplied AAPL split described above.

2. THE LOU-POLK-SKOURAS DECOMPOSITION DOES NOT REPRODUCE AT THE ADVERTISED
   STRENGTH. The direction survives; the effect does not.
     SPY cumulative   overnight +131.22%  intraday +36.26%  buy&hold +215.07%
     SPY annualised   overnight  +10.30%  intraday  +3.68%  buy&hold  +14.36%
     SPY ann. Sharpe  overnight    +0.85  intraday   +0.32  buy&hold   +0.80
   The famous version of this result has intraday at or below ZERO. Here it is
   solidly positive, and the two legs are not statistically distinguishable:
   the within-date label permutation control (10000 draws, the date is the
   cluster, one observation per date) puts the +2.36 bps/session mean gap at
   **p = 0.36**, i.e. t ~ 1.0 against this repo's t > 3 bar.
   Cross-sectional replication is weak too — overnight beats intraday in only
   6 of 10 names, and AAPL (+27.0% intraday vs -1.0% overnight), GOOGL and PG
   run the other way outright. Both halves agree in SIGN (h1 12.47 vs 1.29,
   h2 8.17 vs 6.14) but the gap shrinks by a third, which is what post-
   publication decay looks like (McLean-Pontiff; the paper is 2019 on pre-2014
   data). Two mechanical contributions were measured rather than assumed:
   the dividend lands entirely in the overnight leg by construction and is
   worth +1.63pp of it (gap 6.61pp total-return vs 4.96pp price-only), and
   using official auction closes instead of the last tape print moves it
   further the same way (overnight +121.13% vs intraday +42.54%).
   IT IS ALSO UNTRADEABLE, independently of significance: the overnight leg is
   252 round trips a year with a BREAK-EVEN round-trip cost of 4.20 bps —
   below the 5-10 bps large-cap band. At 5 bps it returns -2.8%/yr against
   buy-and-hold's +14.4%. RESEARCH-AGENDA.md already lists "overnight-only
   trading" as declared dead; this is a local confirmation, and the surviving
   use is execution hygiene (H4, buy at the close), which now has a number.

3. THE VOLATILITY MEASUREMENT CLAIM REPRODUCES DECISIVELY — the one clean win.
   Predictor at t vs |close-to-close return| at t+1, 20,898 symbol-days over
   2134 dates (the dates are the effective sample; the 10 symbols share them):
     predictor      pooled rho   within-symbol   half 1   half 2
     rv_5min             0.391           0.290    0.342    0.228
     sd21 (daily close)  0.350           0.219    0.258    0.167
     |daily return|      0.176           0.100    0.143    0.052
     rv_5min SHUFFLED    0.161          -0.011   -0.004   -0.020
   rv_5min beats both daily-close estimators in 10 of 10 symbols, in both
   halves, and the pooled gap over |daily return| is +0.215 with a
   date-clustered 95% CI of [+0.199, +0.230]. The shuffled control is the
   reason the within-symbol column exists: permuting rv across dates leaves
   the POOLED correlation at 0.161, because high-volatility names also have
   big moves — a cross-sectional level term that a naive pooled statistic
   would have quietly counted as forecasting skill.

So: one adapter, one data bug worth more than either study, one clean
measurement result, and one famous effect that this sample refuses to
confirm. Reported as measured.

Usage:
  python -m scout.intraday                    # the smoke test above (~2 min cold)
  python -m scout.intraday --selftest         # no keys, no network
  python -m scout.intraday --audit            # adjustment/split audit only
  python -m scout.intraday --symbols AAPL,MSFT --start 2024-01-01

"""
from __future__ import annotations

import argparse
import math
import os
import pickle
import threading
import time as _time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timezone

import numpy as np
import pandas as pd
import requests

from . import config

BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"
CA_URL = "https://data.alpaca.markets/v1/corporate-actions"
FEED = "sip"
ET = "US/Eastern"

REG_OPEN = time(9, 30)
REG_CLOSE = time(16, 0)
EARLY_CLOSE = time(13, 0)        # 13:00 auction; its 5-min bar starts at 13:00
EXT_OPEN = time(4, 0)
EXT_CLOSE = time(20, 0)

TD_YEAR = 252
PAGE_LIMIT = 10000               # server caps the real page well below this
MAX_RPM = 90                     # 200/min is shared across ALL agents on this
                                 # key; 140 drew 429s when a second agent was
                                 # running, so the default leaves real room
WORKERS = 4
MAX_GAP_DAYS = 5                 # prev_close is dropped across longer gaps

# NYSE 1:00 pm ET early closes, 2016-2026. Hardcoded as a CHECK on the
# volume-based detector in `detect_early_closes`, never as a substitute for it:
# __main__ reports any disagreement instead of silently trusting either.
EARLY_CLOSES = frozenset(map(pd.Timestamp, [
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
]))

SMOKE_SYMBOLS = ["SPY", "AAPL", "MSFT", "AMZN", "GOOGL",
                 "JPM", "JNJ", "XOM", "PG", "NVDA"]


# ------------------------------------------------------------------ transport

class _Limiter:
    """Token bucket shared by every worker thread. Alpaca's 200 req/min is
    shared across all agents on this key, so the default sits at 120."""

    def __init__(self, rpm: int = MAX_RPM):
        self.rpm = rpm
        self._lock = threading.Lock()
        self._hits: deque[float] = deque()

    def wait(self) -> None:
        while True:
            with self._lock:
                now = _time.monotonic()
                while self._hits and now - self._hits[0] > 60:
                    self._hits.popleft()
                if len(self._hits) < self.rpm:
                    self._hits.append(now)
                    return
                nap = 60 - (now - self._hits[0]) + 0.02
            _time.sleep(nap)


def _headers() -> dict[str, str]:
    return {"APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY}


def _get(url: str, params: dict, limiter: _Limiter | None = None,
         tries: int = 9) -> dict:
    """GET with 429/5xx exponential backoff.

    The budget is deliberately long (~8 minutes of cumulative sleep): the
    200 req/min quota is shared with every other agent on the key, so a burst
    of 429s is a neighbour's traffic, not a bug, and giving up mid-download
    throws away all the pages already paid for. Honours Retry-After when the
    server sends one. Jittered so parallel workers do not resynchronise into
    the same retry wave.

    Never logs params or headers: the key lives in the headers and must not
    reach stdout or a traceback.
    """
    rng = np.random.default_rng()
    for attempt in range(tries):
        if limiter is not None:
            limiter.wait()
        try:
            r = requests.get(url, params=params, headers=_headers(), timeout=90)
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            _time.sleep(min(2 ** attempt, 60) * (1 + rng.random()))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            if attempt == tries - 1:
                r.raise_for_status()
            wait = float(r.headers.get("Retry-After") or 0) or min(2 ** attempt, 60)
            _time.sleep(wait * (1 + rng.random()))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"exhausted retries on {url}")


def _rfc3339(x) -> str:
    """Accept 'YYYY-MM-DD', date, datetime or Timestamp -> RFC3339 UTC."""
    if isinstance(x, str):
        return x if "T" in x else f"{x}T00:00:00Z"
    if isinstance(x, datetime):
        return x.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{pd.Timestamp(x).date()}T00:00:00Z"


# ----------------------------------------------------------------- bar fetch

_COLS = {"o": "open", "h": "high", "l": "low", "c": "close",
         "v": "volume", "n": "trades", "vw": "vwap"}


def _frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=list(_COLS.values()),
                            index=pd.DatetimeIndex([], tz=ET, name="t"))
    df = pd.DataFrame(rows)
    idx = pd.DatetimeIndex(pd.to_datetime(df["t"], utc=True, format="ISO8601")
                           ).tz_convert(ET)
    # .values, not the Series: a dict of RangeIndex Series handed an explicit
    # DatetimeIndex gets REINDEXED onto it, i.e. silently turned into all-NaN.
    out = pd.DataFrame({new: df[old].to_numpy(dtype="float32")
                        for old, new in _COLS.items() if old in df},
                       index=idx)
    out.index.name = "t"
    return out[~out.index.duplicated(keep="last")].sort_index()


def _download(symbol: str, timeframe: str, start: str, end: str,
              adjustment: str, limiter: _Limiter) -> pd.DataFrame:
    # One DataFrame per page, not one giant list of dicts: a decade of 5-minute
    # bars is ~350k rows per symbol and the dict form costs ~10x the float32
    # frame, which matters when several symbols download concurrently.
    pages: list[pd.DataFrame] = []
    token = None
    while True:
        p = {"symbols": symbol, "timeframe": timeframe, "start": start,
             "end": end, "feed": FEED, "adjustment": adjustment,
             "limit": PAGE_LIMIT, "sort": "asc"}
        if token:
            p["page_token"] = token
        j = _get(BARS_URL, p, limiter)
        pages.append(_frame((j.get("bars") or {}).get(symbol) or []))
        token = j.get("next_page_token")
        if not token:
            break
    return pd.concat(pages) if pages else _frame([])


def _cache_path(symbol: str, timeframe: str, adjustment: str):
    safe = symbol.replace("/", "-")
    return config.SCOUT_DIR / f"cache_intraday_{timeframe}_{adjustment}_{safe}.pkl"


def _load_cache(path):
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def fetch_minute_bars(symbols: list[str], start, end, timeframe: str = "1Min",
                      adjustment: str = "all", use_cache: bool = True,
                      repair_splits: bool = True, workers: int = WORKERS,
                      rpm: int = MAX_RPM, quiet: bool = False,
                      ) -> dict[str, pd.DataFrame]:
    """Per-symbol intraday bars, ALL session phases included (04:00-20:00 ET).

    Returns {symbol: DataFrame(index=tz-aware US/Eastern bar-start timestamps,
    columns=open/high/low/close/volume/trades/vwap)}. Filter to a session with
    `regular_session()` — or just use `session_frames()`, which does it.

    Cache: scout/cache_intraday_{timeframe}_{adjustment}_{SYM}.pkl, one file
    per symbol, keyed on the covered [start, end) span; a wider request fetches
    only the missing head and tail. NOTE the cache stores ADJUSTED prices, and
    Alpaca's adjustment factor is anchored to the present, so a cache built
    today and re-read after a future dividend will differ from a fresh pull by
    that dividend's factor. The file stamps `fetched`; delete it (or pass
    use_cache=False) when that matters. Raw-price users should pass
    adjustment='raw', which is stable forever and cached separately.

    `repair_splits=True` (default) fixes splits Alpaca failed to apply — see
    the module docstring. It costs one /v1/corporate-actions request.
    """
    symbols = list(dict.fromkeys(symbols))
    s_iso, e_iso = _rfc3339(start), _rfc3339(end)
    s_ts, e_ts = pd.Timestamp(s_iso).tz_convert(ET), pd.Timestamp(e_iso).tz_convert(ET)
    limiter = _Limiter(rpm)
    out: dict[str, pd.DataFrame] = {}
    fetched = []

    def one(sym: str) -> tuple[str, pd.DataFrame]:
        path = _cache_path(sym, timeframe, adjustment)
        blob = _load_cache(path) if use_cache else None
        parts, cs, ce = [], None, None
        if blob is not None:
            parts.append(blob["bars"])
            cs, ce = blob["cov_start"], blob["cov_end"]
        if cs is None:
            parts.append(_download(sym, timeframe, s_iso, e_iso, adjustment, limiter))
            cs, ce = s_ts, e_ts
            fetched.append(sym)
        else:
            if s_ts < cs:
                parts.append(_download(sym, timeframe, s_iso, _rfc3339(cs),
                                       adjustment, limiter))
                cs = s_ts
                fetched.append(sym)
            if e_ts > ce:
                parts.append(_download(sym, timeframe, _rfc3339(ce), e_iso,
                                       adjustment, limiter))
                ce = e_ts
                fetched.append(sym)
        df = pd.concat(parts).sort_index()
        df = df[~df.index.duplicated(keep="last")]
        if not quiet and sym in fetched:
            print(f"    {sym}: {len(df):,} bars downloaded", flush=True)
        if use_cache:
            # write-then-rename: several agents share this repo and a partial
            # pickle from a concurrent writer would poison every later read
            tmp = path.with_suffix(f".{os.getpid()}.tmp")
            with open(tmp, "wb") as f:
                pickle.dump({"symbol": sym, "timeframe": timeframe,
                             "adjustment": adjustment, "feed": FEED,
                             "cov_start": cs, "cov_end": ce,
                             "fetched": datetime.now(timezone.utc).isoformat(),
                             "bars": df}, f, protocol=5)
            os.replace(tmp, path)
        return sym, df.loc[(df.index >= s_ts) & (df.index < e_ts)]

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for sym, df in ex.map(one, symbols):
            out[sym] = df
    if not quiet:
        n = sum(len(v) for v in out.values())
        print(f"  intraday {timeframe}: {n:,} bars, {len(out)} symbols"
              f"{f' ({len(set(fetched))} downloaded, rest cached)' if fetched else ' (all cached)'}")

    if repair_splits:
        events = split_events(symbols, start, end)
        for sym, df in out.items():
            out[sym] = apply_split_repair(df, events.get(sym, []), quiet=quiet)
    return out


# ------------------------------------------------------- corporate actions

def split_events(symbols: list[str], start, end) -> dict[str, list[dict]]:
    """Forward/reverse splits from Alpaca's own corporate-actions feed, as
    {symbol: [{'ex_date': Timestamp, 'ratio': new/old}, ...]}. `ratio` is the
    share multiplier: 4.0 for a 4:1 forward split, 0.1 for a 1:10 reverse."""
    out: dict[str, list[dict]] = {}
    token = None
    while True:
        p = {"symbols": ",".join(symbols), "start": str(pd.Timestamp(start).date()),
             "end": str(pd.Timestamp(end).date()),
             "types": "forward_split,reverse_split", "limit": 1000}
        if token:
            p["page_token"] = token
        j = _get(CA_URL, p)
        ca = j.get("corporate_actions") or {}
        for kind in ("forward_splits", "reverse_splits"):
            for e in ca.get(kind) or []:
                out.setdefault(e["symbol"], []).append(
                    {"ex_date": pd.Timestamp(e["ex_date"]),
                     "ratio": float(e["new_rate"]) / float(e["old_rate"]),
                     "kind": kind[:-1]})
        token = j.get("next_page_token")
        if not token:
            break
    for v in out.values():
        v.sort(key=lambda e: e["ex_date"])
    return out


def unapplied_splits(df: pd.DataFrame, events: list[dict],
                     tol: float = 0.15) -> list[dict]:
    """Which of `events` the bar series has NOT been adjusted for."""
    return [] if df.empty else unapplied_splits_close(_daily_close(df), events, tol)


def unapplied_splits_close(d: pd.Series, events: list[dict],
                           tol: float = 0.15) -> list[dict]:
    """Same test against a DAILY CLOSE series (works for scout/data.py output).

    On the ex-date the *unadjusted* price ratio close(ex)/close(prev) sits at
    1/ratio times the true one-day return; an adjusted series sits near 1.0.
    Classify on log distance, tol=0.15 (a 16% one-day move would be needed to
    confuse the two for a 4:1 split — and never for a 10:1).
    """
    if len(d) == 0 or not events:
        return []
    d = d.dropna()
    flagged = []
    for e in events:
        ex = e["ex_date"]
        prev = d.index[d.index < ex]
        if not len(prev) or ex not in d.index:
            continue
        obs = math.log(float(d.loc[ex]) / float(d.loc[prev[-1]]))
        if abs(obs + math.log(e["ratio"])) < tol:       # sits at the split ratio
            flagged.append({**e, "jump": math.exp(obs),
                            "prev_close": float(d.loc[prev[-1]]),
                            "ex_close": float(d.loc[ex]), "applied": False})
        elif abs(obs) >= tol:
            flagged.append({**e, "jump": math.exp(obs),
                            "prev_close": float(d.loc[prev[-1]]),
                            "ex_close": float(d.loc[ex]), "applied": None})
    return [f for f in flagged if f["applied"] is not True]


def official_closes(symbols: list[str], start, end,
                    repair: bool = True) -> pd.DataFrame:
    """Official CLOSING-AUCTION prices, from scout/data.py's daily bars,
    split-repaired the same way the minute tape is.

    Needed because the auction print cannot be isolated from minute bars: the
    cross is timestamped 16:00:00, so it lands in the 16:00 bar together with
    the first after-hours trades, and it is neither that bar's open nor its
    close (AAPL 2018-06-29: cross 174.46 adjusted, 16:00 bar o=172.39 c=174.69).
    """
    from . import data
    days = (datetime.now(timezone.utc).replace(tzinfo=None)
            - pd.Timestamp(start).to_pydatetime()).days + 5
    close = data.daily_ohlcv(list(symbols), days=days)["close"].astype("float64")
    close.index = pd.DatetimeIndex(close.index).tz_localize(None).normalize()
    close = close.loc[(close.index >= pd.Timestamp(start))
                      & (close.index <= pd.Timestamp(end))]
    if repair:
        events = split_events(list(symbols), start, end)
        for sym in close.columns:
            for e in unapplied_splits_close(close[sym], events.get(sym, [])):
                if e["applied"] is False:
                    m = close.index < e["ex_date"]
                    close.loc[m, sym] = close.loc[m, sym] / e["ratio"]
    return close


def apply_split_repair(df: pd.DataFrame, events: list[dict],
                       quiet: bool = False) -> pd.DataFrame:
    """Back-adjust bars strictly before the ex-date of every UNAPPLIED split."""
    bad = [e for e in unapplied_splits(df, events) if e["applied"] is False]
    if not bad:
        return df
    df = df.copy()
    for e in bad:
        ex_open = pd.Timestamp(e["ex_date"]).tz_localize(ET)
        m = df.index < ex_open
        for col in ("open", "high", "low", "close", "vwap"):
            if col in df:
                df.loc[m, col] = df.loc[m, col] / np.float32(e["ratio"])
        for col in ("volume",):
            if col in df:
                df.loc[m, col] = df.loc[m, col] * np.float32(e["ratio"])
        if not quiet:
            print(f"  SPLIT REPAIR: {e['ex_date'].date()} {e['ratio']:g}:1 was NOT "
                  f"applied by Alpaca ({e['prev_close']:.2f} -> {e['ex_close']:.2f}); "
                  f"back-adjusted {int(m.sum()):,} bars")
    return df


# ------------------------------------------------------------ session logic

def _daily_close(df: pd.DataFrame) -> pd.Series:
    """Last REGULAR-session bar close per session date (no half-day logic —
    used only for split detection, where a 13:00 vs 15:55 close is irrelevant)."""
    r = regular_session(df)
    if r.empty:
        return pd.Series(dtype="float64")
    return r["close"].astype("float64").groupby(_sessions(r)).last()


def _sessions(df: pd.DataFrame) -> np.ndarray:
    """tz-naive session date for every bar (ET calendar day of the bar start),
    as a plain numpy array. NOT a DatetimeIndex: pandas treats an Index passed
    to .groupby() as an aligned object and silently returns all-NaN groups."""
    return df.index.normalize().tz_localize(None).values


def _bar_minutes(bars: dict[str, pd.DataFrame]) -> float:
    """Bar interval in minutes, read off the data instead of parsed out of the
    timeframe string (which the caller may not have passed here)."""
    for df in bars.values():
        if len(df) > 50:
            d = np.diff(df.index.values[:5000]).astype("timedelta64[s]").astype(float)
            d = d[d > 0]
            if len(d):
                return float(np.median(d) / 60.0)
    return 5.0


def regular_session(df: pd.DataFrame) -> pd.DataFrame:
    t = df.index.time
    return df[(t >= REG_OPEN) & (t < REG_CLOSE)]


def _extended_session(df: pd.DataFrame) -> pd.DataFrame:
    t = df.index.time
    return df[(t >= EXT_OPEN) & (t < EXT_CLOSE)]


def early_close_ratio(bars: dict[str, pd.DataFrame]) -> pd.Series:
    """Per session: pooled dollar volume in [12:55,13:05) divided by pooled
    dollar volume in [15:45,16:00).

    The discriminator is the CLOSING AUCTION, not the session's shape. On a
    13:00 early close the auction cross lands in the 13:00 bar and the 15:45
    window holds only after-hours dust, so the ratio explodes; on a full day
    the 15:45 window holds the cross and the ratio is well below 1. Naive
    alternatives fail: on SPY 2018-07-03 fully 15% of the "session" volume
    still prints after 13:05, so a volume-share rule needs a tuned threshold
    while this one separates by two orders of magnitude.

    Pooled across every symbol supplied so one illiquid name cannot flip a
    date. Data-derived on purpose — the alternative is trusting a hardcoded
    calendar, and this repo does not trust what it can measure."""
    lo, hi = {}, {}
    for df in bars.values():
        r = regular_session(df)
        if r.empty:
            continue
        dv = r["vwap"].astype("float64").values * r["volume"].astype("float64").values
        s = _sessions(r)
        t = r.index.time
        for bucket, m in ((lo, (t >= time(12, 55)) & (t < time(13, 5))),
                          (hi, (t >= time(15, 45)) & (t < time(16, 0)))):
            if not m.any():
                continue
            agg = pd.Series(dv[m]).groupby(s[m]).sum()
            for k, v in agg.items():
                bucket[k] = bucket.get(k, 0.0) + v
    keys = sorted(set(lo) | set(hi))
    return pd.Series([lo.get(k, 0.0) / hi[k] if hi.get(k) else np.inf
                      for k in keys], index=pd.DatetimeIndex(keys))


def detect_early_closes(bars: dict[str, pd.DataFrame],
                        ratio: float = 1.0) -> pd.DatetimeIndex:
    """Sessions that ended at 13:00 ET (see `early_close_ratio`)."""
    r = early_close_ratio(bars)
    return pd.DatetimeIndex(r.index[r > ratio])


def session_frames(symbols: list[str], start, end, timeframe: str = "5Min",
                   extended: bool = False, bars: dict | None = None,
                   official_close: bool = False, min_bar_frac: float = 0.5,
                   max_gap_days: int = MAX_GAP_DAYS, quiet: bool = False,
                   **fetch_kw) -> dict[str, pd.DataFrame]:
    """Session-level date x symbol frames from intraday bars.

    SESSION USED: regular only, 09:30 <= bar-start < 16:00 ET (13:00 on the
    detected early closes), split-repaired, adjustment=all. `extended=True`
    switches to 04:00-20:00 ET and then open_px/close_px are NOT the official
    open and close — they are the first and last print of the extended day.

    Keys (all DataFrames, index = tz-naive session date, columns = symbols):
      open_px       first trade of the session (open of the 09:30 bar)
      high_px/low_px session extremes
      close_px      last bar close at/before the session close. THIS IS THE
                    LAST CONTINUOUS-TRADING PRINT, NOT THE CLOSING AUCTION:
                    the cross is stamped 16:00:00 and lands in the 16:00 bar
                    mixed with early after-hours trades, so it cannot be
                    isolated from bars. Median gap to the official close is
                    ~1 bp and it enters intraday_ret(t) and overnight_ret(t+1)
                    with opposite signs, so it largely telescopes away; pass
                    `official_close=True` to splice in scout/data.py's
                    auction closes instead and see for yourself.
      vwap          dollar-volume-weighted average price over the session
      dollar_vol    sum(bar vwap * bar volume)
      n_bars        bars used (78 on a full 5Min day, 43 on a half-day)
      prev_close    close_px of the PREVIOUS session (shift(1)), NaN across
                    gaps longer than `max_gap_days` calendar days
      overnight_ret open_px / prev_close - 1
      intraday_ret  close_px / open_px - 1
      close_ret     close_px / prev_close - 1   [= the daily total return;
                    (1+overnight)(1+intraday) = 1+close_ret exactly]
      first30_ret   09:30 -> 10:00 (open_px -> last bar close before 10:00)
      last30_ret    15:30 -> 16:00; NaN on half-days, which have no 15:30
      rv_5min       sqrt(sum of squared 5-minute log returns), open->close,
                    in RETURN units per session (not annualised)

    NO LOOKAHEAD: every field on row t is computed only from bars stamped
    inside session t, except `prev_close`, which is `close_px.shift(1)` — the
    single shift in this file, and it looks BACKWARD. Nothing here consumes a
    future bar. A caller who wants to predict day t+1 must shift the target,
    not the signal (see `vol_forecast_study`).
    """
    if bars is None:
        bars = fetch_minute_bars(symbols, start, end, timeframe=timeframe,
                                 quiet=quiet, **fetch_kw)
    if not quiet and any((df.index[1:] - df.index[:-1]).min() > pd.Timedelta("5min")
                         for df in bars.values() if len(df) > 1):
        print("  WARNING: bars are coarser than 5 minutes — rv_5min is realised"
              " vol at THAT sampling interval and is not comparable to the"
              " 5-minute figure (RV falls as the interval widens).")
    early = detect_early_closes(bars)
    if not quiet:
        print(f"  early closes detected: {len(early)} sessions"
              f"{' (' + ', '.join(str(d.date()) for d in early[:4]) + ', ...)' if len(early) else ''}")

    fields = ["open_px", "high_px", "low_px", "close_px", "vwap", "dollar_vol",
              "n_bars", "first30_ret", "last30_ret", "rv_5min"]
    cols: dict[str, dict[str, pd.Series]] = {f: {} for f in fields}

    for sym in symbols:
        df = bars.get(sym)
        if df is None or df.empty:
            continue
        # A session must have real regular-session activity to exist at all;
        # this also kills the boundary artifact where a request's `start`
        # clips into the previous session's after-hours tape.
        live = np.unique(_sessions(regular_session(df)))
        d = _extended_session(df) if extended else regular_session(df)
        if not extended:
            cut = np.where(np.isin(_sessions(d), early.values),
                           time(13, 5), REG_CLOSE)
            d = d[d.index.time < cut]
        d = d[np.isin(_sessions(d), live)]
        if d.empty:
            continue
        s = _sessions(d)
        px = d[["open", "high", "low", "close"]].astype("float64")
        vol = d["volume"].astype("float64")
        dv = d["vwap"].astype("float64") * vol
        g = px.groupby(s)

        cols["open_px"][sym] = g["open"].first()
        cols["high_px"][sym] = g["high"].max()
        cols["low_px"][sym] = g["low"].min()
        cols["close_px"][sym] = g["close"].last()
        cols["n_bars"][sym] = px["close"].groupby(s).size()
        tot_v = vol.groupby(s).sum()
        cols["dollar_vol"][sym] = dv.groupby(s).sum()
        cols["vwap"][sym] = dv.groupby(s).sum() / tot_v.replace(0.0, np.nan)

        # first 30 / last 30 minutes: last bar STARTING before the boundary
        t = d.index.time
        m10 = t < time(10, 0)
        p10 = px["close"][m10].groupby(s[m10]).last()
        cols["first30_ret"][sym] = p10 / cols["open_px"][sym] - 1.0
        m1530 = t < time(15, 30)
        p1530 = px["close"][m1530].groupby(s[m1530]).last()
        # a half-day has no 15:30; reindex leaves NaN rather than a fake number
        base = p1530.reindex(cols["close_px"][sym].index)
        base[np.isin(base.index, early.values)] = np.nan
        cols["last30_ret"][sym] = cols["close_px"][sym] / base - 1.0

        cols["rv_5min"][sym] = _realised_vol(px, s)

    out = {f: pd.DataFrame(cols[f]).sort_index() for f in fields}
    idx = out["close_px"].index
    for f in fields:
        out[f] = out[f].reindex(index=idx, columns=list(symbols))

    # Alpaca's tape has occasional near-empty sessions (SPY+9 large caps,
    # 2018-2026: 21 symbol-sessions with a SINGLE 5-minute bar, e.g. AAPL/MSFT/
    # AMZN/GOOGL/NVDA on 2018-05-02). open_px and close_px then come from the
    # same bar, intraday_ret collapses to ~0 and the next day's overnight_ret
    # is measured against a close that never happened. Blank them rather than
    # publish them; blanking close_px also blanks the following prev_close, so
    # no fabricated gap survives. Lower or zero `min_bar_frac` for genuinely
    # illiquid universes, where a sparse session can be real.
    if min_bar_frac > 0:
        iv = max(1, int(round(_bar_minutes(bars))))
        full = 390 // iv
        expected = pd.Series(np.where(np.isin(idx, early.values),
                                      210 // iv + 1, full), index=idx)
        thin = out["n_bars"].lt(expected * min_bar_frac, axis=0) & out["n_bars"].notna()
        if thin.to_numpy().any():
            if not quiet:
                print(f"  dropped {int(thin.to_numpy().sum())} thin symbol-sessions "
                      f"(< {min_bar_frac:g} x {full} bars): data gaps, not trading days")
            for f in fields:
                out[f] = out[f].mask(thin)

    if official_close:
        off = official_closes(symbols, idx[0], idx[-1]).reindex(
            index=idx, columns=list(symbols))
        out["close_px"] = out["close_px"].where(off.isna(), off)

    close = out["close_px"]
    prev = close.shift(1)                                   # the only shift()
    gap = pd.Series(idx, index=idx).diff().dt.days.values
    prev.loc[gap > max_gap_days] = np.nan       # never span a delisting hole
    out["prev_close"] = prev
    out["overnight_ret"] = out["open_px"] / prev - 1.0
    out["intraday_ret"] = close / out["open_px"] - 1.0
    out["close_ret"] = close / prev - 1.0
    return out


def _realised_vol(px: pd.DataFrame, s: pd.DatetimeIndex) -> pd.Series:
    """sqrt(sum of squared 5-minute log returns) per session, open -> close.

    The first return of each session is log(close_1 / open_1) so the sum of
    returns telescopes exactly to log(close/open): RV covers the same interval
    as `intraday_ret` and nothing is dropped or double counted. If the bars are
    finer than 5 minutes they are resampled to a 5-minute grid first, so the
    field means the same thing at every input timeframe."""
    if len(px) and (px.index[1:] - px.index[:-1]).min() < pd.Timedelta("5min"):
        agg = px.resample("5min", label="left", closed="left").agg(
            {"open": "first", "close": "last"}).dropna()
        px, s = agg, _sessions(agg)
    lr = np.log(px["close"].values)
    r = np.empty(len(lr))
    r[1:] = lr[1:] - lr[:-1]
    first = np.r_[True, s[1:] != s[:-1]]
    r[first] = np.log(px["close"].values[first] / px["open"].values[first])
    return pd.Series(r ** 2, index=px.index).groupby(s).sum() ** 0.5


# ------------------------------------------------------------------- audits

def adjustment_audit(symbols: list[str], start, end, timeframe: str = "5Min",
                     bars: dict | None = None) -> dict:
    """Does the minute tape carry the same adjustment as scout/data.py's daily
    tape, and is that shared adjustment actually right?

    Three separate questions, all answered:
      (a) CONSISTENCY — session closes rebuilt from bars vs data.daily_ohlcv.
          Same backend, so agreement is expected; a disagreement in the
          hundreds of bps would mean the two endpoints apply different
          corporate-action sets.
      (b) MICROSTRUCTURE — the residual after (a) is the closing auction (see
          `official_closes`). Reported as a SIGNED mean log difference with a
          t-stat and an annualised drift, because a signed residual would move
          the overnight/intraday split while a symmetric one telescopes away.
      (c) CORRECTNESS — every split in /v1/corporate-actions checked against
          the ex-date price jump. This is the independent test, and it is the
          one that fails.
    """
    if bars is None:
        bars = fetch_minute_bars(symbols, start, end, timeframe=timeframe,
                                 repair_splits=False)
    daily = official_closes(symbols, start, end, repair=False)
    sess = session_frames(symbols, start, end, timeframe=timeframe, bars=bars,
                          quiet=True)["close_px"]

    events = split_events(symbols, start, end)
    rows = []
    for sym in symbols:
        if sym not in bars or bars[sym].empty or sym not in daily.columns:
            continue
        j = pd.DataFrame({"minute": sess[sym], "daily": daily[sym]}).dropna()
        lg = np.log(j["minute"] / j["daily"])
        rel = lg.abs()
        n = len(j)
        se = float(lg.std() / math.sqrt(n)) if n > 1 else np.nan
        rows.append({"symbol": sym, "n_days": n,
                     "median_abs_log_diff": float(rel.median()) if n else np.nan,
                     "max_abs_log_diff": float(rel.max()) if n else np.nan,
                     "mean_log_diff": float(lg.mean()) if n else np.nan,
                     "t_stat": float(lg.mean() / se) if se and se > 0 else np.nan,
                     "drift_pct_per_yr": float(lg.mean() * TD_YEAR * 100) if n else np.nan,
                     "splits": len(events.get(sym, [])),
                     "unapplied": unapplied_splits(bars[sym], events.get(sym, []))})
    return {"consistency": pd.DataFrame(rows).set_index("symbol"),
            "events": events}


# ------------------------------------------------------------- smoke-test lab

def _spearman(a: pd.Series, b: pd.Series) -> float:
    """Rank correlation. scipy is not a dependency of this repo, and Spearman
    IS Pearson on ranks — average ranks handle the ties."""
    return float(a.rank().corr(b.rank()))


def _np_spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Bootstrap-inner-loop Spearman. Ordinal ranks (ties broken arbitrarily
    rather than averaged) — the inputs are continuous prices and returns, so
    exact ties are rare enough that this matches `_spearman` to ~1e-6."""
    ra = np.empty(len(a))
    rb = np.empty(len(b))
    ra[np.argsort(a, kind="stable")] = np.arange(len(a))
    rb[np.argsort(b, kind="stable")] = np.arange(len(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def _ann_sharpe(r: pd.Series) -> float:
    r = r.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(TD_YEAR)) if sd > 0 else np.nan


def _cum(r: pd.Series) -> float:
    return float((1 + r.dropna()).prod() - 1)


def _ann_ret(r: pd.Series) -> float:
    r = r.dropna()
    return float((1 + r).prod() ** (TD_YEAR / len(r)) - 1) if len(r) else np.nan


def decomposition(sess: dict, sym: str) -> dict:
    on = sess["overnight_ret"][sym]
    idr = sess["intraday_ret"][sym]
    tot = sess["close_ret"][sym]
    ok = on.notna() & idr.notna() & tot.notna()
    on, idr, tot = on[ok], idr[ok], tot[ok]
    return {"symbol": sym, "n": int(ok.sum()),
            "cum_overnight": _cum(on), "cum_intraday": _cum(idr),
            "cum_total": _cum(tot),
            "ann_overnight": _ann_ret(on), "ann_intraday": _ann_ret(idr),
            "ann_total": _ann_ret(tot),
            "sharpe_overnight": _ann_sharpe(on), "sharpe_intraday": _ann_sharpe(idr),
            "sharpe_total": _ann_sharpe(tot),
            "mean_overnight_bps": float(on.mean() * 1e4),
            "mean_intraday_bps": float(idr.mean() * 1e4),
            "identity_max_err": float(((1 + on) * (1 + idr) - (1 + tot)).abs().max())}


def leg_permutation_test(sess: dict, sym: str, reps: int = 10000,
                         seed: int = 42) -> dict:
    """CONTROL for the decomposition. Null: the two legs of a day are
    exchangeable — the overnight/intraday label carries no information. Swap
    the labels independently on each DATE (the date is the cluster; one symbol
    means one observation per cluster) and rebuild the statistic.

    TWO statistics, because they test different things and only one of them is
    clean:
      mean gap    — the economically relevant one. Under label exchangeability
                    its expectation is exactly zero, so the p-value means what
                    it looks like.
      Sharpe gap  — reported because Sharpe is what gets quoted, but note that
                    exchangeability is a COMPOUND null: the overnight window is
                    structurally less volatile than the six-and-a-half-hour
                    session, so part of any rejection here is the variance
                    difference rather than the return difference.
    """
    on = sess["overnight_ret"][sym]
    idr = sess["intraday_ret"][sym]
    ok = on.notna() & idr.notna()
    a, b = on[ok].values, idr[ok].values
    obs_m = (a.mean() - b.mean()) * 1e4
    obs_s = _ann_sharpe(pd.Series(a)) - _ann_sharpe(pd.Series(b))
    rng = np.random.default_rng(seed)
    n = len(a)
    hits_m = hits_s = 0
    for _ in range(reps):
        flip = rng.random(n) < 0.5
        x = np.where(flip, b, a)
        y = np.where(flip, a, b)
        hits_m += abs((x.mean() - y.mean()) * 1e4) >= abs(obs_m)
        g = (x.mean() / x.std(ddof=1) - y.mean() / y.std(ddof=1)) * math.sqrt(TD_YEAR)
        hits_s += abs(g) >= abs(obs_s)
    return {"observed_mean_gap_bps": obs_m, "p_mean": (hits_m + 1) / (reps + 1),
            "observed_sharpe_gap": obs_s, "p_sharpe": (hits_s + 1) / (reps + 1),
            "reps": reps, "n_dates": n}


def cost_table(sess: dict, sym: str, bps_list=(0.0, 5.0, 10.0)) -> pd.DataFrame:
    """Overnight-only and intraday-only both need ONE round trip per session
    (252/yr). Buy-and-hold needs none, which is the entire point."""
    on = sess["overnight_ret"][sym].dropna()
    idr = sess["intraday_ret"][sym].dropna()
    tot = sess["close_ret"][sym].dropna()
    rows = []
    for bps in bps_list:
        c = bps / 1e4
        rows.append({"round_trip_bps": bps,
                     "overnight_ann": _ann_ret(on - c),
                     "overnight_sharpe": _ann_sharpe(on - c),
                     "intraday_ann": _ann_ret(idr - c),
                     "intraday_sharpe": _ann_sharpe(idr - c),
                     "buyhold_ann": _ann_ret(tot)})
    df = pd.DataFrame(rows).set_index("round_trip_bps")
    df.attrs["breakeven_overnight_bps"] = float(on.mean() * 1e4)
    df.attrs["breakeven_intraday_bps"] = float(idr.mean() * 1e4)
    return df


def vol_forecast_study(sess: dict, symbols: list[str], seed: int = 42) -> dict:
    """Does rv_5min beat a daily-close volatility estimate at forecasting the
    NEXT day's absolute return?

    THE SHIFT, EXPLICITLY: predictors are dated t (they use only bars from
    session t); the target is `absret.shift(-1)`, i.e. |close-to-close return|
    on session t+1. Predictor t -> outcome t+1. Nothing else is shifted.

    Predictors, all known at 16:00 on day t:
      rv_5min      realised vol from 5-minute returns, session t
      abs_dret     |close_ret| on day t          (the 1-observation daily estimate)
      sd21         rolling 21-day sd of close_ret through day t

    CONTROLS: (1) the daily-close estimators are the matched benchmark;
    (2) rv_5min permuted across dates within each symbol destroys the
    alignment and must collapse to ~0; (3) both halves reported; (4) the
    bootstrap resamples DATES, not rows, because the 10 symbols share days.
    """
    absret = sess["close_ret"].abs()
    sd21 = sess["close_ret"].rolling(21).std()
    preds = {"rv_5min": sess["rv_5min"], "abs_dret": absret, "sd21": sd21}
    target = absret.shift(-1)               # <<< the only forward shift

    rng = np.random.default_rng(seed)
    long = []
    for sym in symbols:
        if sym not in target.columns:
            continue
        d = pd.DataFrame({k: v[sym] for k, v in preds.items()})
        d["y"] = target[sym]
        d["symbol"] = sym
        d["date"] = d.index
        long.append(d.dropna())
    panel = pd.concat(long, ignore_index=True)
    perm = panel.groupby("symbol")["rv_5min"].transform(
        lambda s: rng.permutation(s.values))
    panel["rv_shuffled"] = perm

    keys = ("rv_5min", "abs_dret", "sd21", "rv_shuffled")

    def corrs(sub: pd.DataFrame) -> dict:
        per = {k: sub.groupby("symbol").apply(
            lambda g, k=k: _spearman(g[k], g["y"]), include_groups=False)
            for k in keys}
        return {k: {"pooled_spearman": _spearman(sub[k], sub["y"]),
                    "pooled_pearson": float(sub[k].corr(sub["y"])),
                    # per-symbol TIME-SERIES rank correlation, averaged. The
                    # pooled figure also contains a cross-sectional term (a
                    # high-vol name has high vol AND big moves), which is why
                    # the shuffled control does not vanish there and does here.
                    "mean_within_symbol": float(per[k].mean()),
                    "min_within_symbol": float(per[k].min())}
                for k in keys}

    dates = np.sort(panel["date"].unique())
    mid = dates[len(dates) // 2]
    out = {"n_obs": len(panel), "n_dates": len(dates), "n_symbols": panel.symbol.nunique(),
           "all": corrs(panel),
           "half1": corrs(panel[panel["date"] < mid]),
           "half2": corrs(panel[panel["date"] >= mid]),
           "span": (str(pd.Timestamp(dates[0]).date()), str(pd.Timestamp(dates[-1]).date()))}
    per_sym = {k: panel.groupby("symbol").apply(
        lambda g, k=k: _spearman(g[k], g["y"]), include_groups=False) for k in keys}
    out["per_symbol"] = pd.DataFrame(per_sym)
    out["beats_absdret_in"] = int((per_sym["rv_5min"] > per_sym["abs_dret"]).sum())
    out["beats_sd21_in"] = int((per_sym["rv_5min"] > per_sym["sd21"]).sum())

    # Date-clustered bootstrap of the rv - abs_dret Spearman gap. Resample
    # DATES, not rows: the symbols share every date, so a row bootstrap would
    # treat 10 correlated observations as 10 independent ones and give a CI
    # roughly sqrt(10) too narrow. Done on numpy row-index groups because the
    # DataFrame version is ~1000x slower for no extra correctness.
    order = np.argsort(panel["date"].values, kind="stable")
    dcodes = pd.factorize(panel["date"].values[order])[0]
    groups = np.split(order, np.flatnonzero(np.diff(dcodes)) + 1)
    a = panel["rv_5min"].to_numpy(float)
    b = panel["abs_dret"].to_numpy(float)
    y = panel["y"].to_numpy(float)
    gaps = []
    for _ in range(400):
        rows = np.concatenate([groups[i] for i in
                               rng.integers(0, len(groups), len(groups))])
        gaps.append(_np_spearman(a[rows], y[rows]) - _np_spearman(b[rows], y[rows]))
    out["gap_rv_minus_absdret"] = {
        "point": (out["all"]["rv_5min"]["pooled_spearman"]
                  - out["all"]["abs_dret"]["pooled_spearman"]),
        "ci95": [float(x) for x in np.percentile(gaps, [2.5, 97.5])],
        "reps": len(gaps), "cluster": "date"}
    return out


# ---------------------------------------------------------------- self-test

def synthetic_bars(seed: int = 0) -> tuple[dict, dict]:
    """Hand-built 5-minute tape with a KNOWN answer: four full sessions, one
    13:00 half-day that keeps printing after-hours bars on the same grid, one
    missing session, and a 4:1 split the "vendor" forgot to apply.

    Returns (bars, truth). Used by `selftest` so a plumbing error in the
    session logic cannot hide behind real-data noise."""
    rng = np.random.default_rng(seed)
    days = ["2024-06-03", "2024-06-04", "2024-06-05", "2024-06-07", "2024-06-10"]
    half = pd.Timestamp("2024-06-05")           # pretend early close
    split_ex = pd.Timestamp("2024-06-07")       # 4:1, NOT applied by the vendor
    # 2024-06-06 is deliberately absent: a missing session must produce no row.
    rows, truth = [], {"open": {}, "close": {}, "rv": {}}
    px = 100.0
    for d in days:
        day = pd.Timestamp(d)
        last = time(13, 0) if day == half else time(15, 55)
        grid = pd.date_range(f"{d} 09:30", f"{d} 15:55", freq="5min", tz=ET)
        px = px * (1 + rng.normal(0, 0.004))     # overnight gap
        o = px
        lr = []
        for t_ in grid:
            live = t_.time() <= last
            step = rng.normal(0, 0.0009) if live else rng.normal(0, 0.0002)
            c = px * (1 + step)
            # the closing auction is the volume spike; after-hours bars are dust
            v = 50_000.0 if live else 200.0
            if t_.time() == last:
                v = 2_000_000.0
            rows.append({"t": t_, "open": px, "high": max(px, c),
                         "low": min(px, c), "close": c, "volume": v,
                         "trades": 10.0, "vwap": (px + c) / 2})
            if live:
                lr.append(math.log(c / px))
            px = c
            if t_.time() == last:
                close_px = c
        truth["open"][day] = o
        truth["close"][day] = close_px
        truth["rv"][day] = math.sqrt(sum(x * x for x in lr))
        px = close_px                            # ignore the after-hours drift
    df = pd.DataFrame(rows).set_index("t").astype("float32")
    # un-apply the split: multiply every pre-ex-date price by 4, volume by 1/4
    m = df.index < split_ex.tz_localize(ET)
    for col in ("open", "high", "low", "close", "vwap"):
        df.loc[m, col] = df.loc[m, col] * 4.0
    df.loc[m, "volume"] = df.loc[m, "volume"] / 4.0
    for k in ("open", "close"):
        for day in list(truth[k]):
            if day < split_ex:
                truth[k][day] *= 4.0
    truth["events"] = [{"ex_date": split_ex, "ratio": 4.0, "kind": "forward_split"}]
    truth["half"] = half
    truth["missing"] = pd.Timestamp("2024-06-06")
    return {"TEST": df}, truth


def selftest() -> int:
    """Assertions on the pure session logic. No keys, no network."""
    bars, truth = synthetic_bars()
    fails = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}{'   ' + detail if detail else ''}")
        if not cond:
            fails.append(name)

    early = detect_early_closes(bars)
    check("half-day detected from the auction-volume ratio",
          list(early) == [truth["half"]], f"got {[str(x.date()) for x in early]}")

    s = session_frames(["TEST"], "2024-06-01", "2024-06-11", bars=bars, quiet=True)
    idx = s["close_px"].index
    check("missing session invents no row", truth["missing"] not in idx)
    check("session count", len(idx) == 5, f"got {len(idx)}")
    check("n_bars: 78 full / 43 half",
          set(s["n_bars"]["TEST"].values.tolist()) == {78.0, 43.0},
          f"got {sorted(set(s['n_bars']['TEST'].values.tolist()))}")
    o_err = max(abs(s["open_px"]["TEST"][d] / v - 1) for d, v in truth["open"].items())
    c_err = max(abs(s["close_px"]["TEST"][d] / v - 1) for d, v in truth["close"].items())
    check("open_px matches the injected session open", o_err < 1e-5, f"max rel {o_err:.2e}")
    check("close_px is the AUCTION bar, not the last after-hours print",
          c_err < 1e-5, f"max rel {c_err:.2e}")
    rv_err = max(abs(s["rv_5min"]["TEST"][d] / v - 1) for d, v in truth["rv"].items())
    check("rv_5min reproduces sqrt(sum sq 5-min log returns)", rv_err < 1e-4,
          f"max rel {rv_err:.2e}")
    ident = ((1 + s["overnight_ret"]) * (1 + s["intraday_ret"])
             - (1 + s["close_ret"])).abs().max().max()
    check("(1+overnight)(1+intraday) == 1+close_ret", ident < 1e-9, f"max {ident:.2e}")
    check("last30_ret is NaN on the half-day (never invented)",
          bool(pd.isna(s["last30_ret"]["TEST"][truth["half"]])))
    check("first30_ret is present on the half-day",
          bool(pd.notna(s["first30_ret"]["TEST"][truth["half"]])))

    found = unapplied_splits(bars["TEST"], truth["events"])
    check("unapplied split detected", len(found) == 1 and found[0]["applied"] is False,
          f"got {found}")
    fixed = apply_split_repair(bars["TEST"], truth["events"], quiet=True)
    s2 = session_frames(["TEST"], "2024-06-01", "2024-06-11", bars={"TEST": fixed},
                        quiet=True)
    jump = abs(s2["overnight_ret"]["TEST"][pd.Timestamp("2024-06-07")])
    check("split repair removes the fabricated -75% overnight return",
          jump < 0.05, f"|overnight| on ex-date = {jump:.4f}")
    raw_jump = abs(s["overnight_ret"]["TEST"][pd.Timestamp("2024-06-07")])
    check("...and it was really there before the repair", raw_jump > 0.7,
          f"|overnight| unrepaired = {raw_jump:.4f}")

    print(f"\n  {len(fails)} failure(s)" + (f": {fails}" if fails else ""))
    return 1 if fails else 0


# ------------------------------------------------------------------- report

def _pct(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:+.2f}%"


def main() -> None:
    ap = argparse.ArgumentParser(description="intraday adapter + smoke test")
    ap.add_argument("--symbols", default=",".join(SMOKE_SYMBOLS))
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-08-01")
    ap.add_argument("--timeframe", default="5Min")
    ap.add_argument("--extended", action="store_true",
                    help="use 04:00-20:00 ET instead of the regular session")
    ap.add_argument("--audit", action="store_true", help="adjustment audit only")
    ap.add_argument("--selftest", action="store_true",
                    help="assert the session logic on synthetic bars; no keys, no network")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--rpm", type=int, default=MAX_RPM)
    a = ap.parse_args()
    syms = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]

    if a.selftest:
        print("scout.intraday selftest — synthetic bars, known answer, no network")
        raise SystemExit(selftest())

    t0 = _time.time()
    print(f"scout.intraday — {len(syms)} symbols, {a.start}..{a.end}, "
          f"{a.timeframe}, feed={FEED}, "
          f"session={'EXTENDED 04:00-20:00' if a.extended else 'REGULAR 09:30-16:00'} ET")

    raw = fetch_minute_bars(syms, a.start, a.end, timeframe=a.timeframe,
                            use_cache=not a.no_cache, repair_splits=False,
                            workers=a.workers, rpm=a.rpm)
    print(f"  fetch took {_time.time() - t0:.0f}s")

    # ---------------------------------------------------------------- audit
    print("\n=== ADJUSTMENT AUDIT: minute bars vs scout/data.py daily bars ===")
    aud = adjustment_audit(syms, a.start, a.end, bars=raw)
    con = aud["consistency"]
    print("  session close rebuilt from bars vs data.daily_ohlcv (log units):")
    print(con[["n_days", "median_abs_log_diff", "max_abs_log_diff",
               "mean_log_diff", "t_stat", "drift_pct_per_yr", "splits"]]
          .to_string(float_format=lambda x: f"{x:,.5f}"))
    print("  (median ~1e-4 = the closing auction, which minute bars cannot"
          " isolate — see official_closes(); a signed drift with |t|>3 would"
          " be a real adjustment mismatch)")
    print("\nsplits in sample, per Alpaca /v1/corporate-actions:")
    for sym, evs in sorted(aud["events"].items()):
        for e in evs:
            print(f"  {sym:6s} {e['ex_date'].date()}  {e['ratio']:g}:1  {e['kind']}")
    bad = {s: r["unapplied"] for s, r in con.iterrows() if r["unapplied"]}
    if bad:
        print("\n  *** SPLITS ALPACA DID NOT APPLY (adjustment=all) ***")
        for sym, evs in bad.items():
            for e in evs:
                print(f"  {sym:6s} {e['ex_date'].date()} {e['ratio']:g}:1 — close "
                      f"{e['prev_close']:.2f} -> {e['ex_close']:.2f} "
                      f"({(e['jump'] - 1) * 100:+.1f}% fabricated overnight return, "
                      f"applied={e['applied']})")
        print("  Minute AND daily bars share the defect, so scout/data.py carries it too.")
    else:
        print("\n  no unapplied splits found in this symbol list.")
    if a.audit:
        return

    # -------------------------------------------------------------- frames
    bars = {s: apply_split_repair(df, aud["events"].get(s, []))
            for s, df in raw.items()}
    print("\n=== SESSION FRAMES ===")
    sess = session_frames(syms, a.start, a.end, timeframe=a.timeframe,
                          extended=a.extended, bars=bars)
    idx = sess["close_px"].index
    print(f"  {len(idx)} sessions, {idx[0].date()}..{idx[-1].date()}")
    nb = sess["n_bars"]
    print(f"  bars per session: median {int(nb.median().median())}, "
          f"min {int(nb.min().min())}, max {int(nb.max().max())}")
    half = detect_early_closes(bars)
    miss = sorted(set(half) - EARLY_CLOSES)
    extra = sorted(d for d in EARLY_CLOSES if d in idx and d not in set(half))
    print(f"  half-days: detected {len(half)}; disagreements with the hardcoded "
          f"NYSE list — detected-only {[str(d.date()) for d in miss]}, "
          f"listed-only {[str(d.date()) for d in extra]}")
    print(f"  last30_ret NaN on half-days (never invented): "
          f"{int(sess['last30_ret'].loc[sess['last30_ret'].index.isin(half)].notna().sum().sum())} "
          f"non-NaN values across {len(half)} half-days x {len(syms)} symbols")
    print("  sample rows (SPY):")
    show = pd.DataFrame({k: sess[k]["SPY"] for k in
                         ("open_px", "close_px", "prev_close", "overnight_ret",
                          "intraday_ret", "first30_ret", "last30_ret",
                          "rv_5min", "vwap")}).dropna().tail(3)
    print(show.to_string(float_format=lambda x: f"{x:.6f}"))

    # -------------------------------------------- overnight vs intraday (SPY)
    print("\n=== LOU-POLK-SKOURAS DECOMPOSITION — SPY ===")
    d = decomposition(sess, "SPY")
    print(f"  n = {d['n']} sessions   "
          f"(identity (1+on)(1+id) = 1+total holds to {d['identity_max_err']:.2e})")
    print(f"  cumulative   overnight {_pct(d['cum_overnight'])}   "
          f"intraday {_pct(d['cum_intraday'])}   buy&hold {_pct(d['cum_total'])}")
    print(f"  annualised   overnight {_pct(d['ann_overnight'])}   "
          f"intraday {_pct(d['ann_intraday'])}   buy&hold {_pct(d['ann_total'])}")
    print(f"  ann. Sharpe  overnight {d['sharpe_overnight']:+.2f}   "
          f"intraday {d['sharpe_intraday']:+.2f}   buy&hold {d['sharpe_total']:+.2f}")
    print(f"  mean/session overnight {d['mean_overnight_bps']:+.2f} bps   "
          f"intraday {d['mean_intraday_bps']:+.2f} bps")

    print("\n  both halves (a sign flip here would mean noise):")
    mid = idx[len(idx) // 2]
    for tag, sl in (("half 1", idx < mid), ("half 2", idx >= mid)):
        sub = {k: v[sl] for k, v in sess.items()}
        h = decomposition(sub, "SPY")
        print(f"    {tag} {str(idx[sl][0].date())}..{str(idx[sl][-1].date())}: "
              f"overnight {_pct(h['ann_overnight'])} (S {h['sharpe_overnight']:+.2f}) "
              f"vs intraday {_pct(h['ann_intraday'])} (S {h['sharpe_intraday']:+.2f})")

    print("\n  CONTROL — within-date leg-label permutation (the labels are")
    print("  exchangeable under the null; the date is the cluster):")
    pt = leg_permutation_test(sess, "SPY")
    print(f"    mean gap   {pt['observed_mean_gap_bps']:+.2f} bps/session, "
          f"p = {pt['p_mean']:.4f}   [the clean test]")
    print(f"    Sharpe gap {pt['observed_sharpe_gap']:+.2f}, "
          f"p = {pt['p_sharpe']:.4f}   [compound null — also reflects the "
          f"structural vol difference]")
    print(f"    {pt['reps']} draws over {pt['n_dates']} dates "
          f"(1 observation per date: dates ARE the effective sample)")

    print("\n  CONTROL — replication across the 9 individual large caps:")
    reps = pd.DataFrame([decomposition(sess, s) for s in syms]).set_index("symbol")
    print(reps[["n", "ann_overnight", "ann_intraday", "ann_total",
                "sharpe_overnight", "sharpe_intraday"]]
          .to_string(float_format=lambda x: f"{x:.3f}"))
    win = int((reps["ann_overnight"] > reps["ann_intraday"]).sum())
    print(f"    overnight > intraday in {win} of {len(reps)} symbols")

    print("\n  ROBUSTNESS — same decomposition on OFFICIAL auction closes")
    print("  (close_px spliced from scout/data.py, split-repaired):")
    sess_off = session_frames(syms, a.start, a.end, timeframe=a.timeframe,
                              extended=a.extended, bars=bars,
                              official_close=True, quiet=True)
    do = decomposition(sess_off, "SPY")
    print(f"    cumulative overnight {_pct(do['cum_overnight'])} vs "
          f"intraday {_pct(do['cum_intraday'])}; Sharpe "
          f"{do['sharpe_overnight']:+.2f} / {do['sharpe_intraday']:+.2f} "
          f"(tape closes: {_pct(d['cum_overnight'])} / {_pct(d['cum_intraday'])}, "
          f"{d['sharpe_overnight']:+.2f} / {d['sharpe_intraday']:+.2f})")

    print("\n  DIVIDENDS — adjustment=all back-adjusts the ex-date price drop,")
    print("  so the whole dividend lands in the OVERNIGHT leg by construction")
    print("  (the drop happens at the open). Re-run on adjustment='raw' prices,")
    print("  which are price-only, to see how much of the gap that is:")
    try:
        rawb = fetch_minute_bars(["SPY"], a.start, a.end, timeframe=a.timeframe,
                                 adjustment="raw", use_cache=not a.no_cache,
                                 workers=1, rpm=a.rpm, quiet=True)
        sr = session_frames(["SPY"], a.start, a.end, timeframe=a.timeframe,
                            bars=rawb, quiet=True)
        dr = decomposition(sr, "SPY")
        print(f"    price-only  overnight {_pct(dr['ann_overnight'])}/yr vs "
              f"intraday {_pct(dr['ann_intraday'])}/yr "
              f"(total-return: {_pct(d['ann_overnight'])} vs {_pct(d['ann_intraday'])})")
        div_on = (d["ann_overnight"] - dr["ann_overnight"]) * 100
        gap_tr = (d["ann_overnight"] - d["ann_intraday"]) * 100
        gap_px = (dr["ann_overnight"] - dr["ann_intraday"]) * 100
        print(f"    => the dividend adds {div_on:+.2f}pp to the overnight leg; "
              f"the overnight-minus-intraday gap is {gap_tr:.2f}pp on total "
              f"return and {gap_px:.2f}pp on price only")
    except Exception as e:                       # never let a diagnostic kill the run
        print(f"    (raw-price check unavailable: {type(e).__name__})")

    print("\n  COSTS — both legs are 252 round trips a year:")
    ct = cost_table(sess, "SPY")
    print(ct.to_string(float_format=lambda x: f"{x:+.4f}"))
    print(f"    BREAK-EVEN round-trip cost: overnight "
          f"{ct.attrs['breakeven_overnight_bps']:.2f} bps, intraday "
          f"{ct.attrs['breakeven_intraday_bps']:.2f} bps "
          f"(large-cap realistic band is 5-10 bps)")

    # ------------------------------------------------------- volatility study
    print("\n=== rv_5min VS A DAILY-CLOSE VOL ESTIMATE, FORECASTING |ret| AT t+1 ===")
    vs = vol_forecast_study(sess, syms)
    print(f"  panel {vs['n_obs']:,} symbol-days, {vs['n_dates']} dates, "
          f"{vs['n_symbols']} symbols, {vs['span'][0]}..{vs['span'][1]}")
    print("  predictor(t) vs |close-to-close return|(t+1)   [target = .shift(-1)]")
    print(f"    {'predictor':<12}{'pooled sp':>10}{'pooled pe':>10}"
          f"{'within-sym':>11}{'h1 within':>11}{'h2 within':>11}")
    for k in ("rv_5min", "abs_dret", "sd21", "rv_shuffled"):
        print(f"    {k:<12}{vs['all'][k]['pooled_spearman']:>10.3f}"
              f"{vs['all'][k]['pooled_pearson']:>10.3f}"
              f"{vs['all'][k]['mean_within_symbol']:>11.3f}"
              f"{vs['half1'][k]['mean_within_symbol']:>11.3f}"
              f"{vs['half2'][k]['mean_within_symbol']:>11.3f}")
    print("  CONTROL: rv_shuffled = rv_5min permuted across dates within each")
    print("  symbol. Its within-symbol column is the zero this study is measured")
    print("  against; its pooled column is the cross-sectional level term that")
    print("  the pooled statistic silently contains (high-vol names move more).")
    g = vs["gap_rv_minus_absdret"]
    print(f"  rv_5min - abs_dret pooled Spearman gap: {g['point']:+.3f}, "
          f"95% CI [{g['ci95'][0]:+.3f}, {g['ci95'][1]:+.3f}] "
          f"({g['reps']} bootstrap reps clustered by {g['cluster']})")
    print(f"  rv_5min beats abs_dret in {vs['beats_absdret_in']}/{vs['n_symbols']} "
          f"symbols and sd21 in {vs['beats_sd21_in']}/{vs['n_symbols']}:")
    print(vs["per_symbol"].to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"  effective independent sample: {vs['n_dates']} dates, NOT "
          f"{vs['n_obs']:,} rows — the symbols share every date.")
    print(f"\ntotal runtime {_time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
