"""Scout settings. Reads Alpaca keys (data-only) from .env at the repo root.

All signal thresholds are frozen ex ante from the literature (see
SCOUT-DESIGN.md) — do NOT tune them against the calibration panel, that's
data snooping and would corrupt the reported probabilities.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

SCOUT_DIR = ROOT / "scout"
UNIVERSE_CSV = SCOUT_DIR / "universe.csv"
CALIBRATION_JSON = SCOUT_DIR / "calibration.json"
LAST_SCAN_JSON = SCOUT_DIR / "last_scan.json"
EXCEL_PATH = ROOT / "picks.xlsx"

# Signal-engine version. Stamped into calibration.json, last_scan.json and
# every picks.xlsx row so probabilities and the track record never silently
# mix engines. Changing signals.py MUST bump this — calibrate.run() refuses
# a cached calibration whose engine tag doesn't match.
ENGINE = "v3"

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

# Composite weights — v3 engine (sum 1.00). Tested on the 2014-2017 monthly
# panel: v1 56.3% hit / +4.01% avg vs v3 61.1% / +4.63% (see SCOUT-DESIGN.md).
W_MOM12 = 0.20     # 12-1 momentum, cross-sectional percentile
W_MOM6 = 0.15      # 6-1 momentum percentile                [MSCI standard]
W_HIGH = 0.25      # 52-week-high proximity percentile — biggest factor
W_GAP = 0.05       # up-gap >=3% on >=2x 20d-median volume, last 20 sessions
W_SMOOTH = 0.10    # share of up-days over the year          [Da-Gurun-Warachka]
W_BRK20 = 0.07     # closeness to 20-day high (speed)        [George-Hwang family]
W_VOL = 0.10       # 20-40% annualized vol band preferred
W_GUARD = 0.05     # penalize top-quintile 1-month runners
W_SMA50 = 0.03     # close > SMA50 tiebreaker only (double-counts momentum)

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

# Calibration statistics
SHRINK_K = 20               # shrink bucket P toward regime base rate
MIN_NEFF = 20               # refuse to quote P below this effective sample size
BOOT_REPS = 1000            # cluster bootstrap (resample dates) repetitions

UNIVERSE_URL = ("https://raw.githubusercontent.com/datasets/"
                "s-and-p-500-companies/main/data/constituents.csv")
