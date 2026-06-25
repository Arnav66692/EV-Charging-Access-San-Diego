"""Across-water (bayfront) robustness check for the DCFC access gap.

Straight-line distance can cross San Diego Bay, so a block group can appear close
to a fast charger that is actually only reachable by going around the bay. This
check excludes block groups whose nearest DCFC station is reached only by a
straight-line path crossing bay water, then recomputes the primary ratio. If the
gap is an artifact of measuring distance across water, excluding these block groups
should move it materially; it does not.

Method:
  - Nearest DCFC station to each block-group centroid (Euclidean, EPSG:3310).
  - Bay water = TIGER/Line 2024 AREAWATER polygons for San Diego County (FIPS 06073)
    whose FULLNAME contains "Bay" (San Diego Bay + Mission Bay). This isolates bay
    crossings from incidental ocean/lagoon/lake slivers along the coastline.
  - A block group is excluded if the straight segment from its centroid to its
    nearest DCFC station crosses (passes through the interior of) the bay water.
  - Recompute the population-weighted median DCFC access ratio on the remaining
    block groups.

The areawater file is fetched from the public Census static server if not present
(no API key). pull_tiger.py fetches the block-group geometry; this file extends the
same Data/raw/ TIGER inputs with the county areawater layer.

Self-check (all-status): 14 block groups excluded; ratio moves 0.6321 -> 0.6318.

Data note: inputs live under Data/raw/ and Data/processed/, which are gitignored.
This script is committed; its inputs are produced by the pipeline (see README).

Run: .venv/bin/python Code/analysis/across_water_check.py
Deterministic. Writes nothing.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402
from shapely.geometry import LineString  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Code" / "features"))

from build_access_g2sfca import (  # noqa: E402
    g2sfca, load_bg_centroids, D0_DCFC, METERS_PER_MILE, WGS84, CA_ALBERS,
)

STATIONS_CSV = ROOT / "Data" / "raw" / "afdc_stations_sandiego.csv"
ACCESS_CSV = ROOT / "Data" / "processed" / "blockgroup_access.csv"
AREAWATER_ZIP = ROOT / "Data" / "raw" / "tl_2024_06073_areawater.zip"
AREAWATER_URL = ("https://www2.census.gov/geo/tiger/TIGER2024/AREAWATER/"
                 "tl_2024_06073_areawater.zip")

FULL_TARGET = 0.6321
EXCL_TARGET = 0.6318
N_EXCLUDED_TARGET = 14
TOL = 0.0006


def load_bg() -> pd.DataFrame:
    cent = load_bg_centroids()
    acc = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    df = acc.merge(cent, on="geoid", how="left")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0)
    df["is_dac_b"] = df["is_dac"].map({True: True, False: False, "True": True, "False": False})
    return df[df["is_dac_b"].notna()].copy()


def load_dcfc_stations(status_filter) -> pd.DataFrame:
    df = pd.read_csv(STATIONS_CSV).dropna(subset=["latitude", "longitude"]).copy()
    df["ev_dc_fast_num"] = pd.to_numeric(df["ev_dc_fast_num"], errors="coerce").fillna(0)
    if status_filter is not None:
        df = df[df["status_code"].isin(status_filter)]
    df = df[df["ev_dc_fast_num"] > 0].copy()
    pts = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs=WGS84
    ).to_crs(CA_ALBERS)
    df["x"], df["y"] = pts.geometry.x.to_numpy(), pts.geometry.y.to_numpy()
    return df


def bay_water():
    if not AREAWATER_ZIP.exists():
        AREAWATER_ZIP.parent.mkdir(parents=True, exist_ok=True)
        print(f"  downloading {AREAWATER_ZIP.name} ...")
        with requests.get(AREAWATER_URL, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(AREAWATER_ZIP, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
    water = gpd.read_file(f"zip://{AREAWATER_ZIP}").to_crs(CA_ALBERS)
    bay = water[water["FULLNAME"].str.contains("Bay", na=False)]
    return bay.geometry.union_all()


def wmedian(values: np.ndarray, weights: np.ndarray) -> float:
    o = np.argsort(values)
    v, w = values[o], weights[o].astype(float)
    return float(v[np.searchsorted(np.cumsum(w), 0.5 * w.sum())])


def access_array(bg: pd.DataFrame, st: pd.DataFrame) -> np.ndarray:
    D = np.sqrt((bg["x"].to_numpy()[:, None] - st["x"].to_numpy()[None, :]) ** 2
                + (bg["y"].to_numpy()[:, None] - st["y"].to_numpy()[None, :]) ** 2) / METERS_PER_MILE
    return g2sfca(D, bg["population"].to_numpy(), st["ev_dc_fast_num"].to_numpy().astype(float), D0_DCFC)


def ratio_with_mask(bg: pd.DataFrame, access: np.ndarray, keep: np.ndarray) -> float:
    dac = bg["is_dac_b"].to_numpy().astype(bool)
    pop = bg["population"].to_numpy()
    kd, kn = keep & dac, keep & (~dac)
    return wmedian(access[kd], pop[kd]) / wmedian(access[kn], pop[kn])


def water_crossing_mask(bg: pd.DataFrame, st: pd.DataFrame, bay) -> np.ndarray:
    """True for block groups whose nearest-DCFC straight segment crosses bay water."""
    bx, by = bg["x"].to_numpy(), bg["y"].to_numpy()
    sx, sy = st["x"].to_numpy(), st["y"].to_numpy()
    D = np.sqrt((bx[:, None] - sx[None, :]) ** 2 + (by[:, None] - sy[None, :]) ** 2)
    nearest = D.argmin(axis=1)
    crosses = np.zeros(len(bg), dtype=bool)
    for i in range(len(bg)):
        seg = LineString([(bx[i], by[i]), (sx[nearest[i]], sy[nearest[i]])])
        crosses[i] = seg.crosses(bay)
    return crosses


def run(bg: pd.DataFrame, st: pd.DataFrame, bay):
    access = access_array(bg, st)
    crosses = water_crossing_mask(bg, st, bay)
    full = ratio_with_mask(bg, access, np.ones(len(bg), dtype=bool))
    excl = ratio_with_mask(bg, access, ~crosses)
    return full, excl, int(crosses.sum())


def main() -> int:
    print("=" * 76)
    print("ACROSS-WATER ROBUSTNESS — exclude bay-crossing block groups")
    print("=" * 76)
    bg = load_bg()
    bay = bay_water()

    full, excl, n = run(bg, load_dcfc_stations(None), bay)
    print(f"\n[self-check] all-status: full = {full:.4f}, excl-water = {excl:.4f}, "
          f"excluded = {n}  (targets {FULL_TARGET} -> {EXCL_TARGET}, {N_EXCLUDED_TARGET} BGs)")
    if abs(full - FULL_TARGET) > TOL or abs(excl - EXCL_TARGET) > TOL or n != N_EXCLUDED_TARGET:
        print("STOP: across-water self-check did not match. Reporting discrepancy, not proceeding.")
        return 1
    print("   self-check passed.")

    full_e, excl_e, n_e = run(bg, load_dcfc_stations(["E"]), bay)
    print(f"\nE-only (status_code == 'E'): full = {full_e:.4f}, excl-water = {excl_e:.4f}, "
          f"excluded = {n_e}")
    print(f"   across-water moves the E-only primary ratio {full_e:.4f} -> {excl_e:.4f}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
