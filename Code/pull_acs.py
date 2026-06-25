"""Pull ACS 5-year block-group data for San Diego County.

Source: U.S. Census Bureau American Community Survey 5-year estimates (2023)
        https://api.census.gov/data/2023/acs/acs5
        CENSUS_API_KEY required in .env (mandatory as of 2026-05-12).

Tables pulled at block-group level (state 06, county 073):
  B25003  Tenure (owner vs renter)
  B25024  Units in structure (multifamily share)
  B19013  Median household income
  B08303  Travel time to work
  B25044  Vehicles available by tenure

Output: Data/raw/acs_blockgroups_sandiego.csv, keyed by 12-digit GEOID.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "Data" / "raw"
OUTPUT_CSV = RAW_DIR / "acs_blockgroups_sandiego.csv"

CENSUS_BASE = "https://api.census.gov/data/2023/acs/acs5"

# Variables to pull per table.  Compact: only the estimates needed downstream.
VARIABLES = [
    # B25003 Tenure
    "B25003_001E",   # total housing units
    "B25003_002E",   # owner occupied
    "B25003_003E",   # renter occupied
    # B25024 Units in structure (2+ units = multifamily)
    "B25024_001E",   # total
    "B25024_002E",   # 1 unit, detached
    "B25024_003E",   # 1 unit, attached
    "B25024_004E",   # 2 units
    "B25024_005E",   # 3 or 4 units
    "B25024_006E",   # 5 to 9 units
    "B25024_007E",   # 10 to 19 units
    "B25024_008E",   # 20 to 49 units
    "B25024_009E",   # 50 or more units
    # B19013 Median household income
    "B19013_001E",   # median HHI (−1 when suppressed)
    # B08303 Travel time to work (workers 16+)
    "B08303_001E",   # total workers
    "B08303_002E",   # < 5 min
    "B08303_003E",   # 5-9 min
    "B08303_004E",   # 10-14 min
    "B08303_005E",   # 15-19 min
    "B08303_006E",   # 20-24 min
    "B08303_007E",   # 25-29 min
    "B08303_008E",   # 30-34 min
    "B08303_009E",   # 35-39 min
    "B08303_010E",   # 40-44 min
    "B08303_011E",   # 45-59 min
    "B08303_012E",   # 60-89 min
    "B08303_013E",   # 90+ min
    # B25044 Vehicles available by tenure
    "B25044_001E",   # total occupied units
    "B25044_002E",   # owner occupied
    "B25044_003E",   # owner occupied, no vehicle
    "B25044_009E",   # renter occupied
    "B25044_010E",   # renter occupied, no vehicle
]

# Human-readable column rename (drop the table code prefix).
RENAME = {
    "B25003_001E": "tenure_total",
    "B25003_002E": "tenure_owner",
    "B25003_003E": "tenure_renter",
    "B25024_001E": "units_struct_total",
    "B25024_002E": "units_1det",
    "B25024_003E": "units_1att",
    "B25024_004E": "units_2",
    "B25024_005E": "units_3_4",
    "B25024_006E": "units_5_9",
    "B25024_007E": "units_10_19",
    "B25024_008E": "units_20_49",
    "B25024_009E": "units_50plus",
    "B19013_001E": "median_hhi",
    "B08303_001E": "commute_workers",
    "B08303_002E": "commute_lt5",
    "B08303_003E": "commute_5_9",
    "B08303_004E": "commute_10_14",
    "B08303_005E": "commute_15_19",
    "B08303_006E": "commute_20_24",
    "B08303_007E": "commute_25_29",
    "B08303_008E": "commute_30_34",
    "B08303_009E": "commute_35_39",
    "B08303_010E": "commute_40_44",
    "B08303_011E": "commute_45_59",
    "B08303_012E": "commute_60_89",
    "B08303_013E": "commute_90plus",
    "B25044_001E": "veh_total",
    "B25044_002E": "veh_owner",
    "B25044_003E": "veh_owner_none",
    "B25044_009E": "veh_renter",
    "B25044_010E": "veh_renter_none",
}


def fetch_acs(api_key: str) -> pd.DataFrame:
    """GET all block groups for SD County and return a tidy DataFrame."""
    get_vars = ",".join(["NAME"] + VARIABLES)
    params = {
        "get": get_vars,
        "for": "block group:*",
        "in": "state:06 county:073 tract:*",
        "key": api_key,
    }
    print(f"Requesting {CENSUS_BASE} (B25003, B25024, B19013, B08303, B25044)...")
    resp = requests.get(CENSUS_BASE, params=params, timeout=120)
    resp.raise_for_status()

    raw = resp.json()
    header, *rows = raw
    df = pd.DataFrame(rows, columns=header)
    print(f"  API returned {len(df)} block groups.")
    return df


def build_geoid(df: pd.DataFrame) -> pd.DataFrame:
    """Construct 12-digit GEOID = state(2)+county(3)+tract(6)+blockgroup(1)."""
    df["geoid"] = (
        df["state"].str.zfill(2)
        + df["county"].str.zfill(3)
        + df["tract"].str.zfill(6)
        + df["block group"].str.zfill(1)
    )
    return df


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Census estimate columns to numeric; replace suppression sentinels with NaN.

    The Census API uses two suppression codes:
      -1          (generic "not applicable / not available")
      -666666666  (B19013 median income suppressed at block-group level due to
                   small sample; returned as the integer −666666666)
    Both must be treated as missing.
    """
    SENTINELS = {-1, -666666666}
    for col in RENAME.values():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].replace(list(SENTINELS), float("nan"))
    return df


def print_summary(df: pd.DataFrame) -> None:
    print(f"\nRows: {len(df)}")
    print("\nNull counts per column:")
    nulls = df.isnull().sum()
    max_name = max(len(c) for c in df.columns)
    for col, n in nulls.items():
        pct = 100 * n / len(df)
        print(f"  {col:<{max_name}}  {n:5d} ({pct:.1f}%)")


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("CENSUS_API_KEY")
    if not api_key:
        print(
            "ERROR: CENSUS_API_KEY not found in .env\n"
            "Add it to .env as: CENSUS_API_KEY=<your_key>\n"
            "Register at https://api.census.gov/data/key_signup.html",
            file=sys.stderr,
        )
        return 1

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_acs(api_key)
    df = build_geoid(df)
    df = df.rename(columns=RENAME)

    keep = ["geoid", "NAME"] + list(RENAME.values())
    df = df[[c for c in keep if c in df.columns]].copy()
    df = coerce_numeric(df)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote {len(df)} rows -> {OUTPUT_CSV}")
    print_summary(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
