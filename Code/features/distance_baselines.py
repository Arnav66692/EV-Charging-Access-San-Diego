"""Distance baselines for EV charging access — the floor E2SFCA must beat.

For each San Diego County block group, compute the straight-line distance to:
  - the nearest public charging station of any type (dist_nearest_charger_mi)
  - the nearest DC-fast station, ev_dc_fast_num >= 1 (dist_nearest_dcfc_mi)

All distance math is done in California Albers (EPSG:3310, meters) on block-group
centroids and station points, then converted to miles. Nearest is found with a
geopandas spatial nearest join (sjoin_nearest) on the projected coordinates.

These are deliberately simple baselines. NO catchment radius, NO distance decay,
NO E2SFCA here. This script does NOT modify blockgroup_access.csv.

QA-only by default; pass --write to persist Data/processed/blockgroup_distance.csv.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "Data" / "raw"
PROCESSED_DIR = ROOT / "Data" / "processed"

BG_ZIP = RAW_DIR / "tl_2024_06_bg.zip"
STATIONS_CSV = RAW_DIR / "afdc_stations_sandiego.csv"
ACCESS_CSV = PROCESSED_DIR / "blockgroup_access.csv"   # read-only, for is_dac equity read
OUTPUT_CSV = PROCESSED_DIR / "blockgroup_distance.csv"

WGS84 = "EPSG:4326"
CA_ALBERS = "EPSG:3310"          # California Albers, meters
SD_STATE_FP = "06"
SD_COUNTY_FP = "073"
METERS_PER_MILE = 1609.344

OUTPUT_COLS = ["geoid", "dist_nearest_charger_mi", "dist_nearest_dcfc_mi"]


def load_bg_centroids() -> gpd.GeoDataFrame:
    """Block-group centroids in EPSG:3310, with WGS84 lon/lat kept for QA labels."""
    bg = gpd.read_file(f"zip://{BG_ZIP}")
    bg = bg[(bg["STATEFP"] == SD_STATE_FP) & (bg["COUNTYFP"] == SD_COUNTY_FP)].copy()
    bg = bg.to_crs(CA_ALBERS)
    cent = bg.geometry.centroid                      # planar centroid in projected CRS
    pts = gpd.GeoDataFrame(
        {"geoid": bg["GEOID"].astype(str)}, geometry=cent, crs=CA_ALBERS
    )
    ll = pts.to_crs(WGS84)
    pts["lon"] = ll.geometry.x
    pts["lat"] = ll.geometry.y
    return pts


# Operational-only default; mirrors build_access_g2sfca.OPERATIONAL_STATUS so the
# nearest-charger baselines (and F1's distance figure) count only in-service
# (status_code == "E") stations. Set to None to include all statuses.
OPERATIONAL_STATUS = "E"


def load_stations() -> gpd.GeoDataFrame:
    df = pd.read_csv(STATIONS_CSV)
    df = df.dropna(subset=["latitude", "longitude"]).copy()
    if OPERATIONAL_STATUS is not None:
        df = df[df["status_code"] == OPERATIONAL_STATUS].copy()
    df["ev_dc_fast_num"] = pd.to_numeric(df["ev_dc_fast_num"], errors="coerce").fillna(0)
    gdf = gpd.GeoDataFrame(
        df[["city", "ev_dc_fast_num"]],
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs=WGS84,
    ).to_crs(CA_ALBERS)
    return gdf


def nearest(bg_pts: gpd.GeoDataFrame, stations: gpd.GeoDataFrame, name: str) -> pd.DataFrame:
    """Nearest station to each BG centroid; returns geoid, <name>_mi, <name>_city."""
    j = gpd.sjoin_nearest(
        bg_pts[["geoid", "geometry"]], stations[["city", "geometry"]],
        how="left", distance_col="_dist_m",
    )
    # Equidistant ties can duplicate a geoid; keep one.
    j = j.drop_duplicates(subset="geoid", keep="first")
    out = pd.DataFrame({
        "geoid": j["geoid"].to_numpy(),
        f"{name}_mi": j["_dist_m"].to_numpy() / METERS_PER_MILE,
        f"{name}_city": j["city"].to_numpy(),
    })
    return out


def build() -> tuple[pd.DataFrame, dict]:
    bg = load_bg_centroids()
    st = load_stations()
    dcfc = st[st["ev_dc_fast_num"] >= 1]

    near_all = nearest(bg, st, "dist_nearest_charger")
    near_dcfc = nearest(bg, dcfc, "dist_nearest_dcfc")

    df = (
        bg[["geoid", "lon", "lat"]]
        .merge(near_all, on="geoid", how="left")
        .merge(near_dcfc, on="geoid", how="left")
    )
    meta = {"n_bg": len(df), "n_stations": len(st), "n_dcfc": len(dcfc)}
    return df, meta


def qa_report(df: pd.DataFrame, meta: dict) -> None:
    print("\n" + "=" * 66)
    print("QA — distance baselines (projected EPSG:3310, miles)")
    print("=" * 66)
    print(f"Block groups: {meta['n_bg']}   stations: {meta['n_stations']}   "
          f"DCFC stations: {meta['n_dcfc']}")

    for col in ("dist_nearest_charger_mi", "dist_nearest_dcfc_mi"):
        s = df[col]
        print(f"\n{col}:  min {s.min():.2f}  median {s.median():.2f}  max {s.max():.2f}  "
              f"(nulls {int(s.isna().sum())})")

    far = int((df["dist_nearest_dcfc_mi"] > 10).sum())
    print(f"\nBlock groups whose nearest DCFC is > 10 miles: {far}")

    cols = ["geoid", "lat", "lon", "dist_nearest_charger_mi", "dist_nearest_charger_city"]
    print("\nSanity — 5 CLOSEST block groups (expect coastal/urban, nearest city SD/Carlsbad):")
    print(df.nsmallest(5, "dist_nearest_charger_mi")[cols].to_string(index=False))
    print("\nSanity — 5 FARTHEST block groups (expect rural east county, more eastern lon):")
    print(df.nlargest(5, "dist_nearest_charger_mi")[cols].to_string(index=False))

    # Coarse west (coastal/urban) vs east (rural) split by centroid longitude.
    west = df[df["lon"] < -117.1]
    east = df[df["lon"] > -116.7]
    print(f"\nWest of -117.10 (coastal/urban, n={len(west)}): "
          f"median nearest charger {west['dist_nearest_charger_mi'].median():.2f} mi")
    print(f"East of -116.70 (rural east, n={len(east)}): "
          f"median nearest charger {east['dist_nearest_charger_mi'].median():.2f} mi")

    print("\nFIRST EQUITY READ — median distance by is_dac (is_dac from blockgroup_access.csv):")
    access = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})[["geoid", "is_dac"]]
    eq = df.merge(access, on="geoid", how="left")
    g = eq.groupby("is_dac", dropna=False)[
        ["dist_nearest_charger_mi", "dist_nearest_dcfc_mi"]
    ].median()
    print(g.to_string())
    print("=" * 66)


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df, meta = build()
    qa_report(df, meta)

    if "--write" in sys.argv:
        df[OUTPUT_COLS].to_csv(OUTPUT_CSV, index=False)
        print(f"\n[written] {len(df)} rows -> {OUTPUT_CSV}")
    else:
        print("\n[QA-only] CSV not written. Re-run with --write to persist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
