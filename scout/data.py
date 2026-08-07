"""Daily OHLCV via Alpaca. Uses the SIP (consolidated all-exchange) feed with
split/dividend adjustment — the free plan allows SIP *history* (only the last
~15 minutes are restricted), and consolidated volume is what makes the
volume-surge signal meaningful (IEX carries ~2.5% of tape).

Returns {"open": df, "close": df, "volume": df} — each time × symbol.
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from . import config

CHUNK = 150  # symbols per request (practical cap ~200)


def daily_ohlcv(symbols: list[str], days: int) -> dict[str, pd.DataFrame]:
    client = StockHistoricalDataClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    end = now - timedelta(minutes=20)   # SIP data older than 15 min is free
    frames = []
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        try:
            req = StockBarsRequest(symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                                   start=start, end=end,
                                   adjustment=Adjustment.ALL, feed=DataFeed.SIP)
            df = client.get_stock_bars(req).df
            if not df.empty:
                frames.append(df.reset_index())
        except Exception as e:
            print(f"  bars chunk {i // CHUNK + 1} failed ({len(chunk)} syms): {e}")
    if not frames:
        raise RuntimeError("no market data returned at all")
    allbars = pd.concat(frames, ignore_index=True)
    allbars["timestamp"] = (pd.to_datetime(allbars["timestamp"])
                            .dt.tz_convert("US/Eastern").dt.normalize())
    out = {}
    for field in ("open", "close", "volume"):
        out[field] = (allbars.pivot_table(index="timestamp", columns="symbol",
                                          values=field, aggfunc="last")
                      .sort_index())
    return out
