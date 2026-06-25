"""Income-weighted demand sensitivity for the DCFC access gap.

Rebuilds the demand-reweight sensitivity behind
Data/processed/demand_reweight_sensitivity.csv. The G2SFCA demand term is normally
residential population. Here demand is scaled toward higher-income block groups as a
proxy for electric-vehicle ownership:

    demand_k = population_k * income_k ** beta

with beta = 0 (baseline population), 1 (linear), 2 (quadratic). Higher-income block
groups exert more demand, raising competition where EV ownership is likely highest.

The DAC / non-DAC ratio is invariant to any global rescaling of income, because a
constant factor on demand cancels in the ratio; only the relative income weighting
matters. Missing income (median_hhi NaN after tract imputation) is filled with the
county median income so every block group carries a demand weight.

Estimator: population-weighted median DCFC access ratio (weights are ACTUAL
population, so the contrast still reflects people; the reweight changes only the
competition denominator).

Self-check (all-status, matching demand_reweight_sensitivity.csv pop_weighted_median):
    beta 0 -> 0.6321,  beta 1 (linear) -> 0.7740,  beta 2 (quadratic) -> 0.8949.

Data note: inputs live under Data/raw/ and Data/processed/, which are gitignored.
This script is committed; its inputs are produced by the pipeline (see README).

Run: .venv/bin/python Code/analysis/income_reweight_sensitivity.py
Deterministic. Writes nothing.
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
    g2sfca, load_bg_centroids, D0_DCFC, METERS_PER_MILE, WGS84, CA_ALBERS,
)

STATIONS_CSV = ROOT / "Data" / "raw" / "afdc_stations_sandiego.csv"
ACCESS_CSV = ROOT / "Data" / "processed" / "blockgroup_access.csv"

# (beta, label, all-status target) for the self-check.
TARGETS = [(1, "linear", 0.7740), (2, "quadratic", 0.8949)]
BASE_TARGET = 0.6321
TOL = 0.001


def load_bg() -> pd.DataFrame:
    cent = load_bg_centroids()
    acc = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    df = acc.merge(cent, on="geoid", how="left")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0)
    df["income"] = pd.to_numeric(df["median_hhi"], errors="coerce")
    df["income"] = df["income"].fillna(df["income"].median())   # county median for the few NaN
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


def wmedian(values: np.ndarray, weights: np.ndarray) -> float:
    o = np.argsort(values)
    v, w = values[o], weights[o].astype(float)
    return float(v[np.searchsorted(np.cumsum(w), 0.5 * w.sum())])


def reweighted_ratio(bg: pd.DataFrame, st: pd.DataFrame, beta: float) -> float:
    D = np.sqrt((bg["x"].to_numpy()[:, None] - st["x"].to_numpy()[None, :]) ** 2
                + (bg["y"].to_numpy()[:, None] - st["y"].to_numpy()[None, :]) ** 2) / METERS_PER_MILE
    pop = bg["population"].to_numpy()
    weight = bg["income"].to_numpy() ** beta if beta != 0 else np.ones_like(pop)
    demand = pop * weight
    supply = st["ev_dc_fast_num"].to_numpy().astype(float)
    access = g2sfca(D, demand, supply, D0_DCFC)
    dac = bg["is_dac_b"].to_numpy().astype(bool)
    return wmedian(access[dac], pop[dac]) / wmedian(access[~dac], pop[~dac])


def main() -> int:
    print("=" * 76)
    print("INCOME-WEIGHTED DEMAND SENSITIVITY — DCFC pop-weighted median ratio")
    print("=" * 76)
    bg = load_bg()
    st_all = load_dcfc_stations(None)
    st_e = load_dcfc_stations(["E"])

    base = reweighted_ratio(bg, st_all, 0)
    print(f"\n[self-check] beta=0 baseline (all-status) = {base:.4f}  (target {BASE_TARGET})")
    if abs(base - BASE_TARGET) > TOL:
        print(f"STOP: baseline self-check failed (|{base:.4f} - {BASE_TARGET}| > {TOL}).")
        return 1
    for beta, label, target in TARGETS:
        r = reweighted_ratio(bg, st_all, beta)
        print(f"[self-check] beta={beta} {label} (all-status) = {r:.4f}  (target {target})")
        if abs(r - target) > TOL:
            print(f"STOP: {label} self-check failed (|{r:.4f} - {target}| > {TOL}).")
            return 1
    print("   all self-checks passed.")

    print("\nE-only (status_code == 'E') results:")
    for beta, label, _ in [(0, "baseline", 0)] + TARGETS:
        r = reweighted_ratio(bg, st_e, beta)
        print(f"   beta={beta} {label:9s} = {r:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
