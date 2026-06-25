"""Gaussian two-step floating catchment area (G2SFCA) EV charging accessibility.

Week 4 contribution. G2SFCA is the literature standard for spatial accessibility
(Luo & Wang 2003 introduced 2SFCA; Dai 2010 added the normalized Gaussian decay).
Here it is applied type-specifically to public EV charging in San Diego County.

Two runs (travel behavior differs by charger type):
  A) DCFC  — supply S_j = ev_dc_fast_num,    catchment d0 = 6 mi (equity-critical:
             renters without home charging depend on public fast charging).
  B) L2    — supply S_j = ev_level2_evse_num, catchment d0 = 2 mi.

Two-step method per run:
  Step 1 (per station j): R_j = S_j / sum_k[ pop_k * G(d_kj) ]   over BGs k within d0
  Step 2 (per BG i):  access_i = sum_j[ R_j * G(d_ij) ]          over stations j within d0

Combined capacity-weighted score:
  access_combined = access_l2 * 4 + access_dcfc * 48
  The 4 vs 48 weights (DCFC weighted ~12x L2) are an EXPLICIT MODELING ASSUMPTION of this
  project, reflecting the approximate daily service-throughput difference between charger
  types (a DCFC port turns over far more sessions/day than an L2 port). We could NOT confirm
  a specific literature source for these exact values, so they are stated as our assumption,
  not a literature citation (consistent with the README and references.bib). Multiplying
  port-based access by this assumed rate yields a daily-capacity-weighted accessibility so
  DCFC supply is not undercounted relative to its throughput.

All distances are computed in EPSG:3310 (California Albers, meters) -> miles.
QA-only by default; pass --write to persist Data/processed/blockgroup_g2sfca.csv.
Does NOT modify any other CSV.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "Data" / "raw"
PROCESSED_DIR = ROOT / "Data" / "processed"

ACCESS_CSV = PROCESSED_DIR / "blockgroup_access.csv"   # geoid, population, is_dac, ces_crosswalked
STATIONS_CSV = RAW_DIR / "afdc_stations_sandiego.csv"
BG_ZIP = RAW_DIR / "tl_2024_06_bg.zip"
OUTPUT_CSV = PROCESSED_DIR / "blockgroup_g2sfca.csv"

WGS84 = "EPSG:4326"
CA_ALBERS = "EPSG:3310"
SD_STATE_FP = "06"
SD_COUNTY_FP = "073"
METERS_PER_MILE = 1609.344

D0_DCFC = 6.0          # miles
D0_L2 = 2.0            # miles
SENS_RADII = [4.0, 6.0, 10.0]      # DCFC sensitivity sweep
SERVICE_L2 = 4         # sessions/day/port
SERVICE_DCFC = 48      # sessions/day/port

RURAL_LON = -116.85    # centroid longitude east of this = rural east county (QA flag only)

OUTPUT_COLS = ["geoid", "access_dcfc", "access_l2", "access_combined"]


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #

def load_bg_centroids() -> pd.DataFrame:
    """BG centroids in EPSG:3310 (x,y meters) + WGS84 lon/lat, keyed by geoid."""
    bg = gpd.read_file(f"zip://{BG_ZIP}")
    bg = bg[(bg["STATEFP"] == SD_STATE_FP) & (bg["COUNTYFP"] == SD_COUNTY_FP)].copy()
    bg = bg.to_crs(CA_ALBERS)
    cent = bg.geometry.centroid
    out = pd.DataFrame({"geoid": bg["GEOID"].astype(str)})
    out["x"], out["y"] = cent.x.to_numpy(), cent.y.to_numpy()
    ll = gpd.GeoSeries(cent, crs=CA_ALBERS).to_crs(WGS84)
    out["lon"], out["lat"] = ll.x.to_numpy(), ll.y.to_numpy()
    return out


# Operational-only default. The accessibility analysis counts a station as supply
# only when the AFDC data marks it in service (status_code == "E"); planned ("P")
# and temporarily-unavailable ("T") stations are excluded at load. This is the
# committed default so a clean clone reproduces the operational (E-only) figures
# and access numbers with no runtime patch. Set to None to include all statuses.
OPERATIONAL_STATUS = "E"


def load_stations() -> pd.DataFrame:
    df = pd.read_csv(STATIONS_CSV).dropna(subset=["latitude", "longitude"]).copy()
    if OPERATIONAL_STATUS is not None:
        df = df[df["status_code"] == OPERATIONAL_STATUS].copy()
    for c in ("ev_dc_fast_num", "ev_level2_evse_num"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    pts = gpd.GeoDataFrame(
        df[["city", "ev_dc_fast_num", "ev_level2_evse_num"]],
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs=WGS84,
    ).to_crs(CA_ALBERS)
    df["x"], df["y"] = pts.geometry.x.to_numpy(), pts.geometry.y.to_numpy()
    return df


# --------------------------------------------------------------------------- #
# G2SFCA core
# --------------------------------------------------------------------------- #

def gaussian(d: np.ndarray, d0: float) -> np.ndarray:
    """Dai (2010) normalized Gaussian: weight 1 at d=0, 0 at d=d0, 0 beyond d0."""
    w = (np.exp(-0.5 * (d / d0) ** 2) - np.exp(-0.5)) / (1 - np.exp(-0.5))
    return np.where(d <= d0, w, 0.0)


def g2sfca(dist_mi: np.ndarray, pop: np.ndarray, supply: np.ndarray, d0: float) -> np.ndarray:
    """Standard two-step. dist_mi: (N_bg, M_station); pop: (N,); supply: (M,)."""
    G = gaussian(dist_mi, d0)                      # (N, M)
    # numpy's SIMD matmul loop on macOS emits spurious divide/overflow/invalid FP
    # warnings even for finite inputs/outputs; suppress them and assert finiteness.
    # Masked division also avoids ever computing supply/demand where demand == 0.
    R = np.zeros(G.shape[1])
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        demand = pop @ G                           # (M,) population competing per station
        mask = demand > 0
        R[mask] = supply[mask] / demand[mask]      # (M,) supply-to-demand ratio
        access = G @ R                             # (N,) accessibility per BG
    assert np.isfinite(access).all(), "non-finite G2SFCA access values"
    return access


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #

def build() -> tuple[pd.DataFrame, dict]:
    access = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    cent = load_bg_centroids()
    df = access.merge(cent, on="geoid", how="left")
    missing = int(df["x"].isna().sum())
    if missing:
        raise RuntimeError(f"{missing} BGs have no centroid geometry (geoid mismatch).")

    st = load_stations()
    pop = pd.to_numeric(df["population"], errors="coerce").fillna(0).to_numpy()
    bg_xy = df[["x", "y"]].to_numpy()
    st_xy = st[["x", "y"]].to_numpy()

    # One distance matrix (N_bg x M_station) in miles, reused for all runs/radii.
    diff = bg_xy[:, None, :] - st_xy[None, :, :]
    dist_mi = np.sqrt((diff ** 2).sum(axis=2)) / METERS_PER_MILE

    s_dcfc = st["ev_dc_fast_num"].to_numpy()
    s_l2 = st["ev_level2_evse_num"].to_numpy()

    df["access_dcfc"] = g2sfca(dist_mi, pop, s_dcfc, D0_DCFC)
    df["access_l2"] = g2sfca(dist_mi, pop, s_l2, D0_L2)
    df["access_combined"] = df["access_l2"] * SERVICE_L2 + df["access_dcfc"] * SERVICE_DCFC

    # DCFC sensitivity sweep (QA only, not written).
    sens = {d0: g2sfca(dist_mi, pop, s_dcfc, d0) for d0 in SENS_RADII}

    meta = {
        "n_bg": len(df),
        "n_stations": len(st),
        "n_dcfc": int((s_dcfc >= 1).sum()),
        "n_l2": int((s_l2 >= 1).sum()),
        "sens": sens,
    }
    return df, meta


# --------------------------------------------------------------------------- #
# QA
# --------------------------------------------------------------------------- #

def _med_by_dac(frame: pd.DataFrame, values: np.ndarray | str, label: str) -> None:
    col = "_v"
    f = frame.copy()
    f[col] = frame[values].to_numpy() if isinstance(values, str) else values
    g = f.groupby("is_dac", dropna=False)[col].median()
    t, fa = g.get(True, float("nan")), g.get(False, float("nan"))
    direction = ("DAC BETTER served" if t > fa else "DAC WORSE served" if t < fa else "equal")
    ratio = (t / fa) if fa else float("nan")
    print(f"  {label}: DAC(True)={t:.4g}  non-DAC(False)={fa:.4g}  "
          f"ratio={ratio:.2f}  -> {direction}")


def qa_report(df: pd.DataFrame, meta: dict) -> None:
    print("\n" + "=" * 72)
    print("QA — G2SFCA accessibility (EPSG:3310, Gaussian decay, Dai 2010)")
    print("=" * 72)
    print(f"Block groups: {meta['n_bg']}   stations: {meta['n_stations']}   "
          f"DCFC-supply: {meta['n_dcfc']}   L2-supply: {meta['n_l2']}")
    print(f"Catchments: DCFC d0={D0_DCFC} mi, L2 d0={D0_L2} mi   "
          f"service ratio L2:DCFC = {SERVICE_L2}:{SERVICE_DCFC}")

    print("\n1) Distribution (min / median / max):")
    for c in ("access_dcfc", "access_l2", "access_combined"):
        s = df[c]
        print(f"   {c:16s}  {s.min():.4g}  /  {s.median():.4g}  /  {s.max():.4g}  "
              f"(zeros: {int((s == 0).sum())})")

    print("\n2) KEY TEST — equity contrast by is_dac (higher access = better served):")
    print("   (distance baseline showed DAC closer/better; does competition flip it?)")
    _med_by_dac(df, "access_dcfc", "access_dcfc    ")
    _med_by_dac(df, "access_combined", "access_combined")

    print("\n3) Same contrast EXCLUDING ces_crosswalked=True (directly-matched DACs only):")
    direct = df[df["ces_crosswalked"] != True]  # noqa: E712
    n_dac_direct = int((direct["is_dac"] == True).sum())  # noqa: E712
    print(f"   directly-matched rows: {len(direct)}  (DAC among them: {n_dac_direct})")
    _med_by_dac(direct, "access_dcfc", "access_dcfc    ")
    _med_by_dac(direct, "access_combined", "access_combined")

    print("\n4) Spatial sanity — top 10 BGs by access_dcfc (expect dense urban cores):")
    cols = ["geoid", "lat", "lon", "population", "access_dcfc"]
    print(df.nlargest(10, "access_dcfc")[cols].to_string(index=False))
    p90 = df["access_dcfc"].quantile(0.90)
    rural_hi = df[(df["lon"] > RURAL_LON) & (df["access_dcfc"] >= p90)]
    print(f"\n   Rural east BGs (lon > {RURAL_LON}) in the top-10% access_dcfc "
          f"(possible low-density OVERSTATEMENT): {len(rural_hi)}")
    if len(rural_hi):
        print(rural_hi.nlargest(min(8, len(rural_hi)), "access_dcfc")[cols].to_string(index=False))

    print("\n5) SENSITIVITY — access_dcfc equity contrast across d0 = 4 / 6 / 10 mi:")
    for d0 in SENS_RADII:
        _med_by_dac(df, meta["sens"][d0], f"d0={d0:>4} mi  access_dcfc")
    print("   (stable direction across radii => radius choice robust; flip => disclose)")
    print("=" * 72)


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
