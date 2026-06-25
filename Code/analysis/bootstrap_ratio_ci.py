"""Bootstrap confidence intervals for the DCFC access gap.

Rebuilds the two resampling procedures behind Data/processed/bootstrap_ratio_ci.csv,
computed here on the operational (status_code == 'E') station set, with the
population-weighted median DCFC ratio (DAC / non-DAC) as the statistic.

  SCHEME 1 — station-level bootstrap. Resample the DCFC stations with replacement
    (a station drawn twice contributes its ports twice), recompute access for every
    block group, take the ratio. Captures the uncertainty from the thin DCFC base.

  SCHEME 2 — spatial block bootstrap. Compute access once on the full station set,
    then resample whole census tracts with replacement and take the ratio over the
    block groups in the drawn tracts. Captures spatially-clustered sampling
    uncertainty (neighbouring block groups are not independent).

Draw count B and seed match the committed CSV (B = 2000, seed = 1234) so the result
is reproducible. There is no committed CI to match exactly (the original generator
was never committed and its RNG call order is unknown), so the SELF-CHECK anchors on
what is checkable: the point estimate the bootstrap centers on, and the DAC /
non-DAC DCFC port counts. If those do not reproduce, the harness is broken and the
script stops rather than report intervals built on it.

  E-only anchors:     ratio 0.6845, ports 33 / 1,312
  all-status anchors: ratio 0.6321, ports 35 / 1,377   (sanity check on the harness)

For context the committed all-status CSV intervals are printed next to the E-only
intervals so the shift is visible.

Data note: inputs live under Data/raw/ and Data/processed/, which are gitignored.
This script is committed; its inputs are produced by the pipeline (see README).

Run: .venv/bin/python Code/analysis/bootstrap_ratio_ci.py
Deterministic given the seed. Writes nothing.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Code" / "features"))

from build_access_g2sfca import (  # noqa: E402
    g2sfca, load_bg_centroids, D0_DCFC, METERS_PER_MILE,
    WGS84, CA_ALBERS, SD_STATE_FP, SD_COUNTY_FP, BG_ZIP,
)

STATIONS_CSV = ROOT / "Data" / "raw" / "afdc_stations_sandiego.csv"
ACCESS_CSV = ROOT / "Data" / "processed" / "blockgroup_access.csv"

SEED = 1234
B = 2000

# Anchors (point estimate + ports) by station set.
ANCHORS = {
    "all-status": {"filter": None, "ratio": 0.6321, "dac_ports": 35, "nondac_ports": 1377},
    "E-only": {"filter": ["E"], "ratio": 0.6845, "dac_ports": 33, "nondac_ports": 1312},
}
RATIO_TOL = 0.001

# Committed all-status CSV intervals (pop-weighted median) for context.
COMMITTED = {
    "station_bootstrap": {"ci": (0.4042, 0.9473), "parity": 0.0160},
    "spatial_block_bootstrap": {"ci": (0.5460, 0.7617), "parity": 0.0000},
}


def load_bg() -> pd.DataFrame:
    cent = load_bg_centroids()
    acc = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    df = acc.merge(cent, on="geoid", how="left")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0)
    df["is_dac_b"] = df["is_dac"].map({True: True, False: False, "True": True, "False": False})
    df = df[df["is_dac_b"].notna()].copy()
    df["tract"] = df["geoid"].str[:11]
    return df


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


def wmedian(values: np.ndarray, weights: np.ndarray) -> float:
    if len(values) == 0 or weights.sum() == 0:
        return float("nan")
    o = np.argsort(values)
    v, w = values[o], weights[o].astype(float)
    return float(v[np.searchsorted(np.cumsum(w), 0.5 * w.sum())])


def dist_matrix(bg: pd.DataFrame, st: pd.DataFrame) -> np.ndarray:
    return np.sqrt((bg["x"].to_numpy()[:, None] - st["x"].to_numpy()[None, :]) ** 2
                   + (bg["y"].to_numpy()[:, None] - st["y"].to_numpy()[None, :]) ** 2) / METERS_PER_MILE


def access_full(bg: pd.DataFrame, st: pd.DataFrame) -> np.ndarray:
    D = dist_matrix(bg, st)
    return g2sfca(D, bg["population"].to_numpy(), st["ev_dc_fast_num"].to_numpy().astype(float), D0_DCFC)


def ratio_from_access(access: np.ndarray, dac: np.ndarray, pop: np.ndarray, bg_idx: np.ndarray) -> float:
    a, dm, w = access[bg_idx], dac[bg_idx], pop[bg_idx]
    return wmedian(a[dm], w[dm]) / wmedian(a[~dm], w[~dm])


def dac_port_counts(bg_poly: gpd.GeoDataFrame, st: pd.DataFrame) -> tuple[int, int]:
    pts = gpd.GeoDataFrame(
        st, geometry=gpd.points_from_xy(st["longitude"], st["latitude"]), crs=WGS84
    )
    j = gpd.sjoin(pts, bg_poly, predicate="within", how="left").dropna(subset=["is_dac_b"])
    m = j["is_dac_b"].to_numpy().astype(bool)
    dacp = int(j.loc[m, "ev_dc_fast_num"].sum())
    nonp = int(j.loc[~m, "ev_dc_fast_num"].sum())
    return dacp, nonp


def load_bg_polygons(bg: pd.DataFrame) -> gpd.GeoDataFrame:
    poly = gpd.read_file(f"zip://{BG_ZIP}")
    poly = poly[(poly["STATEFP"] == SD_STATE_FP) & (poly["COUNTYFP"] == SD_COUNTY_FP)].copy()
    poly["geoid"] = poly["GEOID"].astype(str)
    poly = poly.merge(bg[["geoid", "is_dac_b"]], on="geoid", how="left")
    return poly[["is_dac_b", "geometry"]]


def summarize(ratios: np.ndarray) -> dict:
    r = ratios[np.isfinite(ratios)]
    return {
        "ci_low": float(np.percentile(r, 2.5)),
        "ci_high": float(np.percentile(r, 97.5)),
        "frac_ge_parity": float(np.mean(r >= 1.0)),
        "frac_same_dir": float(np.mean(r < 1.0)),
        "n_valid": int(len(r)),
    }


def station_bootstrap(bg: pd.DataFrame, st: pd.DataFrame) -> np.ndarray:
    D = dist_matrix(bg, st)
    supply = st["ev_dc_fast_num"].to_numpy().astype(float)
    pop = bg["population"].to_numpy()
    dac = bg["is_dac_b"].to_numpy().astype(bool)
    all_bg = np.arange(len(bg))
    n = len(st)
    out = np.empty(B)
    for b in range(B):
        idx = np.random.randint(0, n, n)             # resample stations with replacement
        access = g2sfca(D[:, idx], pop, supply[idx], D0_DCFC)
        out[b] = ratio_from_access(access, dac, pop, all_bg)
    return out


def spatial_block_bootstrap(bg: pd.DataFrame, access: np.ndarray) -> np.ndarray:
    pop = bg["population"].to_numpy()
    dac = bg["is_dac_b"].to_numpy().astype(bool)
    tracts = bg["tract"].to_numpy()
    uniq = np.unique(tracts)
    # Map each tract -> array of block-group row indices.
    members = {t: np.where(tracts == t)[0] for t in uniq}
    k = len(uniq)
    out = np.empty(B)
    for b in range(B):
        drawn = uniq[np.random.randint(0, k, k)]     # resample whole tracts with replacement
        bg_idx = np.concatenate([members[t] for t in drawn])
        out[b] = ratio_from_access(access, dac, pop, bg_idx)
    return out


def main() -> int:
    print("=" * 80)
    print(f"BOOTSTRAP CIs — DCFC pop-weighted median ratio   (B={B}, seed={SEED})")
    print("=" * 80)
    bg = load_bg()
    bg_poly = load_bg_polygons(bg)

    # ---- self-check: point estimates and port counts ----
    print("\n[self-check] point estimate + DCFC port counts:")
    for tag, spec in ANCHORS.items():
        st = load_dcfc_stations(spec["filter"])
        access = access_full(bg, st)
        pt = ratio_from_access(access, bg["is_dac_b"].to_numpy().astype(bool),
                               bg["population"].to_numpy(), np.arange(len(bg)))
        dacp, nonp = dac_port_counts(bg_poly, st)
        ok = (abs(pt - spec["ratio"]) <= RATIO_TOL
              and dacp == spec["dac_ports"] and nonp == spec["nondac_ports"])
        print(f"   {tag:11s} ratio={pt:.4f} (target {spec['ratio']})   "
              f"ports {dacp}/{nonp} (target {spec['dac_ports']}/{spec['nondac_ports']})   "
              f"{'OK' if ok else 'MISMATCH'}")
        if not ok:
            print("STOP: harness self-check failed; not reporting intervals.")
            return 1
    print("   harness self-check passed.")

    # ---- bootstraps ----
    rows = []
    for tag, spec in ANCHORS.items():
        st = load_dcfc_stations(spec["filter"])
        access = access_full(bg, st)

        np.random.seed(SEED)
        s1 = summarize(station_bootstrap(bg, st))
        np.random.seed(SEED)
        s2 = summarize(spatial_block_bootstrap(bg, access))
        rows.append((tag, "station_bootstrap", s1))
        rows.append((tag, "spatial_block_bootstrap", s2))

    print(f"\n{'set':11s} {'scheme':24s} {'95% CI':>20s} {'>=parity':>9s} {'same-dir':>9s}")
    for tag, scheme, s in rows:
        ci = f"[{s['ci_low']:.4f}, {s['ci_high']:.4f}]"
        print(f"{tag:11s} {scheme:24s} {ci:>20s} {100*s['frac_ge_parity']:8.2f}% {100*s['frac_same_dir']:8.2f}%")

    print("\nCommitted all-status CSV (pop-weighted median) for context:")
    for scheme, c in COMMITTED.items():
        print(f"   {scheme:24s} [{c['ci'][0]:.4f}, {c['ci'][1]:.4f}]   >=parity {100*c['parity']:.2f}%")
    print("\nNote: E-only CIs use the same B and seed; they will not byte-match the committed")
    print("all-status CSV because the resampled inputs differ and the original RNG call order")
    print("was never committed. The point-estimate centers are the validated anchor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
