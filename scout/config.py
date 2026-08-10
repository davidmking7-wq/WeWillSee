"""Scout settings. Reads Alpaca keys (data-only) from .env at the repo root.

This project is research-only. The keys are used for market data, not order
submission. There is no live execution path or weekly executor in this branch.

All signal thresholds are frozen ex ante from the literature (see
SCOUT-DESIGN.md) — do NOT tune them against the calibration panel, that's
data snooping and would corrupt the reported probabilities.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

def _alpaca_credentials() -> tuple[str | None, str | None]:
    """Load data-only credentials without copying secrets into this repo."""
    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    credential_file = os.environ.get("ALPACA_CREDENTIAL_FILE")
    if credential_file and (not key or not secret):
        path = Path(credential_file).expanduser()
        try:
            lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                     if line.strip()]
        except OSError as exc:
            raise RuntimeError(f"cannot read ALPACA_CREDENTIAL_FILE: {path}") from exc
        if len(lines) != 2:
            raise RuntimeError("ALPACA_CREDENTIAL_FILE must contain exactly two non-empty lines")
        key = key or lines[0]
        secret = secret or lines[1]
    return key, secret


ALPACA_API_KEY, ALPACA_SECRET_KEY = _alpaca_credentials()

SCOUT_DIR = ROOT / "scout"
UNIVERSE_CSV = SCOUT_DIR / "universe.csv"
CALIBRATION_JSON = SCOUT_DIR / "calibration.json"
LAST_SCAN_JSON = SCOUT_DIR / "last_scan.json"
EXCEL_PATH = ROOT / "picks.xlsx"

# Signal-engine version. Stamped into calibration.json, last_scan.json and
# every picks.xlsx row so probabilities and the track record never silently
# mix engines. Changing signals.py MUST bump this — calibrate.run() refuses
# a cached calibration whose engine tag doesn't match.
# v5 = v4 signals over the S&P 1500 universe (large+mid+small segments)
# with a tradeable-liquidity gate. The universe is part of the engine:
# cross-sectional ranks change with it, so probabilities must rebuild.
ENGINE = "v5"

# Label definition (state verbatim in every report):
# HIT = max CLOSE over the next 42 trading days >= entry close * 1.05
# (first-passage; entry = close on the scan date, window starts the next day)
HORIZON_TDAYS = 42
TARGET_GAIN = 0.05
DROP_GAIN = -0.05           # companion stat: touched -5% before +5%

SCAN_HISTORY_DAYS = 480     # calendar days of bars a scan needs
CALIB_YEARS = 10            # Alpaca SIP history starts 2016 — use all of it
CALIB_STALE_DAYS = 30
UNIVERSE_STALE_DAYS = 60
TOP_CANDIDATES = 15

# Universe = S&P 1500 (large 500 + mid 400 + small 600): the mid/small
# segments are where under-the-radar candidates live. Illiquid names are
# gated at scan time, not in the universe file:
MIN_DOLLAR_VOL = 10_000_000     # 20d median close*volume floor (entry-time)

# Composite weights — v4 engine (sum 1.00). v4 = v3 minus the gap/volume
# PEAD proxy (its weight moved to 6-1 momentum), selected by train/holdout
# on 2016-2026 SIP data — see SCOUT-DESIGN.md for the full protocol record.
W_MOM12 = 0.20     # 12-1 momentum, cross-sectional percentile
W_MOM6 = 0.20      # 6-1 momentum percentile                [MSCI standard]
W_HIGH = 0.25      # 52-week-high proximity percentile — biggest factor
W_SMOOTH = 0.10    # share of up-days over the year          [Da-Gurun-Warachka]
W_BRK20 = 0.07     # closeness to 20-day high (speed)        [George-Hwang family]
W_VOL = 0.10       # 20-40% annualized vol band preferred
W_GUARD = 0.05     # penalize top-quintile 1-month runners
W_SMA50 = 0.03     # close > SMA50 tiebreaker only (double-counts momentum)
# The up-gap+volume-surge feature is still computed for research context
# (it appears in the scan's signals text) but earns no score weight.

# Hard gates / vetoes (literature-frozen)
VETO_RET1M_HI = 0.25        # 1-month return above +25% -> excluded (reversal)
VETO_RET1M_LO = -0.15       # 1-month return below -15% -> excluded
VETO_VOL_DECILE = 0.90      # top cross-sectional vol decile -> excluded (lottery)
VETO_MAX21_DECILE = 0.90    # top-decile single-day pop last month -> excluded
                            # (Bali et al. MAX effect — lottery spikes fade)
VOL_BAND = (0.20, 0.40)     # preferred annualized 63d vol
# Hard gates applied in signals.composite_at: close > SMA200, and
# 6-month return > 0 (absolute momentum, Antonacci).

# "Biggest gain" list: only stocks whose cell shows at least this chance of
# reaching the +5% minimum bar (user-set floor). List may be empty — that's
# honest, not a bug.
GAIN_MIN_P5 = 0.62

# Sell guidance (exit-rule lab, scout/exitlab.py — full record in
# BACKTEST-REPORT.md; corroborated by Kaminski-Lo 2014, Lei-Li 2009).
# Tested 2017-2026 train/holdout: ordinary stops/time/trend exits before
# the deadline reduce returns (whipsaw + gap-through — daily single-stock
# returns lean toward reversal, so stops sell dips right before the
# expected bounce). Current PER-STOCK guidance is deliberately narrow
# (HIT/MISS labels are never altered):
#  1. DISASTER stop at SELL_DISASTER_SIGMA x the stock's own expected
#     42-day move (sigma42 = annualized 63d vol * sqrt(42/252)) below
#     entry. Beat the fixed -15% stop on BOTH train and holdout
#     (vstop200 vs stop15). Tail-capping, not return enhancement.
#  2. No other stop before the deadline; the deadline is the exit.
# Touching +5% is a scorecard milestone, not a sell trigger. The former
# breakeven-after-+5% rule was removed after the portfolio-level test showed
# that it cut compounded return by about one third (BACKTEST-REPORT, Round 2).
SELL_DISASTER_SIGMA = 2.0
SELL_DISASTER_FALLBACK = 0.15   # rows recorded before per-stock levels

# Calibration statistics
SHRINK_K = 20               # shrink bucket P toward regime base rate
MIN_NEFF = 20               # refuse to quote P below this effective sample size
BOOT_REPS = 1000            # cluster bootstrap (resample dates) repetitions

UNIVERSE_URL = ("https://raw.githubusercontent.com/datasets/"
                "s-and-p-500-companies/main/data/constituents.csv")
