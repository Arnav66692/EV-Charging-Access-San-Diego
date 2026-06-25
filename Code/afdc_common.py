"""Shared AFDC helpers: API fetch + San Diego County point-in-polygon clip.

Imported by both pull_afdc.py and snapshot_afdc.py so the fetch and clip logic
lives in exactly one place.

The API is served from developer.nlr.gov (the developer.nrel.gov host was retired
2026-05-29). The endpoint runs on federal infrastructure via api.data.gov.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# Silence the harmless LibreSSL/urllib3 notice on macOS system Python.
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402  (import after warning filter)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "Data" / "raw"

AFDC_URL = "https://developer.nlr.gov/api/alt-fuel-stations/v1.json"
TIGER_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip"
)
TIGER_ZIP = RAW_DIR / "tl_2024_us_county.zip"

SAN_DIEGO_GEOID = "06073"
WGS84 = "EPSG:4326"


def get_api_key() -> str:
    """Load NREL_API_KEY from the project .env."""
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("NREL_API_KEY")
    if not api_key:
        raise RuntimeError("NREL_API_KEY not found in .env")
    return api_key


def fetch_stations(api_key: str) -> pd.DataFrame:
    """GET all public CA electric stations and return the fuel_stations array."""
    params = {
        "fuel_type": "ELEC",
        "state": "CA",
        "access": "public",
        "limit": "all",
        "api_key": api_key,
    }
    print(f"Requesting {AFDC_URL} (fuel_type=ELEC, state=CA, access=public)...")
    resp = requests.get(AFDC_URL, params=params, timeout=180)
    resp.raise_for_status()
    payload = resp.json()
    stations = payload.get("fuel_stations", [])
    print(f"  API returned {len(stations)} California stations.")
    return pd.DataFrame(stations)


def load_san_diego_boundary() -> gpd.GeoDataFrame:
    """Download (if needed) the TIGER county file and return SD County in WGS84."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not TIGER_ZIP.exists():
        print(f"Downloading Census TIGER county shapefile -> {TIGER_ZIP.name}...")
        with requests.get(TIGER_URL, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(TIGER_ZIP, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
    else:
        print(f"Using cached TIGER county shapefile {TIGER_ZIP.name}.")

    counties = gpd.read_file(f"zip://{TIGER_ZIP}")
    sd = counties.loc[counties["GEOID"] == SAN_DIEGO_GEOID]
    if sd.empty:
        raise RuntimeError(f"GEOID {SAN_DIEGO_GEOID} not found in TIGER counties.")
    return sd.to_crs(WGS84)


def clip_to_san_diego(df: pd.DataFrame, sd: gpd.GeoDataFrame) -> pd.DataFrame:
    """Point-in-polygon clip of stations to the San Diego County boundary."""
    pts = df.dropna(subset=["latitude", "longitude"]).copy()
    stations = gpd.GeoDataFrame(
        pts,
        geometry=gpd.points_from_xy(pts["longitude"], pts["latitude"]),
        crs=WGS84,
    )
    joined = gpd.sjoin(
        stations, sd[["geometry"]], predicate="within", how="inner"
    )
    print(f"  {len(joined)} stations fall inside San Diego County (FIPS 06073).")
    return pd.DataFrame(joined.drop(columns="geometry"))


def get_sandiego_stations(api_key: str | None = None) -> pd.DataFrame:
    """Convenience: fetch CA stations and return only those in San Diego County."""
    if api_key is None:
        api_key = get_api_key()
    df = fetch_stations(api_key)
    sd = load_san_diego_boundary()
    return clip_to_san_diego(df, sd)
