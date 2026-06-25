"""Pull CalEnviroScreen 4.0 data for San Diego County tracts.

Source: CalEnviroScreen 4.0 (October 2021 final release), published by OEHHA.
        Accessed via ArcGIS FeatureServer hosted by a public ArcGIS Online item:
        https://services1.arcgis.com/PCHfdHz4GlDNAhBb/arcgis/rest/services/
            CalEnviroScreen_4_0_Results_/FeatureServer/0

Columns kept:
  geoid        — 11-digit census tract GEOID (zero-padded)
  ces_score    — CalEnviroScreen 4.0 raw score (CIscore)
  ces_pctile   — CalEnviroScreen 4.0 score percentile 0–100 (CIscoreP)
  is_dac       — True when ces_pctile >= 75 (SB 535 / AB 1550 DAC proxy)

NOTE on is_dac: CalEnviroScreen 4.0 percentile >= 75 is used as the SB 535
Disadvantaged Community proxy (top-quartile tracts). CARB's official DAC list
may also include adjacent low-income tracts; this field is a first-order proxy
only and must not be used as a regulatory determination.

Output: Data/raw/calenviroscreen_sandiego.csv keyed by geoid.
Version: CalEnviroScreen 4.0, October 2021 final release (accessed via ArcGIS Online).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "Data" / "raw"
OUTPUT_CSV = RAW_DIR / "calenviroscreen_sandiego.csv"

# Statewide ArcGIS FeatureServer for CalEnviroScreen 4.0 results.
ARCGIS_URL = (
    "https://services1.arcgis.com/PCHfdHz4GlDNAhBb/arcgis/rest/services"
    "/CalEnviroScreen_4_0_Results_/FeatureServer/0/query"
)

# San Diego County tracts are stored as 10-digit integers: 6073XXXXXX.
SD_WHERE = "tract >= 6073000000 AND tract < 6074000000"
FIELDS = "tract,TractTXT,CIscore,CIscoreP"
DAC_THRESHOLD = 75.0


def fetch_ces(max_records: int = 2000) -> pd.DataFrame:
    """Page through the ArcGIS service and return all SD County CES records."""
    params = {
        "where": SD_WHERE,
        "outFields": FIELDS,
        "resultOffset": 0,
        "resultRecordCount": max_records,
        "f": "json",
    }
    print(f"Requesting CalEnviroScreen 4.0 from ArcGIS FeatureServer...")
    resp = requests.get(ARCGIS_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        raise RuntimeError(
            f"No features returned. ArcGIS error: {data.get('error')}"
        )

    rows = [f["attributes"] for f in features]
    df = pd.DataFrame(rows)
    print(f"  Returned {len(df)} San Diego County tracts.")
    return df


def build_geoid(tract_val) -> str:
    """Zero-pad a 10-digit tract integer to an 11-digit GEOID string."""
    return str(int(tract_val)).zfill(11)


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["geoid"] = df["tract"].apply(build_geoid)
    df["ces_score"] = pd.to_numeric(df["CIscore"], errors="coerce")
    df["ces_pctile"] = pd.to_numeric(df["CIscoreP"], errors="coerce")
    df["is_dac"] = df["ces_pctile"] >= DAC_THRESHOLD
    return df[["geoid", "ces_score", "ces_pctile", "is_dac"]].copy()


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    df_raw = fetch_ces()
    df = tidy(df_raw)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\nWrote {len(df)} rows -> {OUTPUT_CSV}")
    print(f"Rows: {len(df)}")
    print(f"DAC tracts (ces_pctile >= {DAC_THRESHOLD}): {df['is_dac'].sum()}")
    print(f"ces_score  min={df['ces_score'].min():.2f}  max={df['ces_score'].max():.2f}")
    print(f"ces_pctile min={df['ces_pctile'].min():.1f}  max={df['ces_pctile'].max():.1f}")
    nulls = df.isnull().sum()
    print("\nNull counts per column:")
    for col, n in nulls.items():
        print(f"  {col}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
