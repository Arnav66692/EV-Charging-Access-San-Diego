"""Reliability rank-inversion check — the paper's decisive composition test.

The paper argues the reliability-weighted gap is driven by network COMPOSITION:
disadvantaged communities draw their fast charging from lower-reliability networks
(EVgo-heavy) while the rest of the county is Tesla-heavy. The decisive test inverts
the real-world reliability ordering so the network DACs rely on most (EVgo) receives
the TOP prior and Tesla the BOTTOM. If composition drives the gap, this inversion
should narrow it (the paper reports a narrowing to 0.646, still short of parity).

The committed build_access_g2sfca_reliability.PRIOR_SETS does NOT contain this true
inversion — only a milder "alt ordering (EA>CP, eVgo up)" shuffle. The generator of
the cited 0.646 was never committed, so this script reconstructs the inversion from
the committed reliability primitives and reports what they yield. Exactly matching
0.646 is not expected; the self-check here is the NEGATIVE confirmation that no
committed prior set reproduces 0.646, plus a positive anchor that the base
reliability ratio reproduces the committed 0.6173.

Inversion construction (same value multiset, reassigned in reversed rank order):
take the baseline named priors, force EVgo to the top value and Tesla to the bottom,
and give the remaining networks the remaining values in reversed baseline-rank order.

Estimator: population-weighted median DCFC access ratio (DAC / non-DAC), the paper's
headline estimator (the committed dac_ratio() uses plain median; the paper's
reliability sweeps 0.622/0.603/0.646 are pop-weighted).

Data note: inputs live under Data/raw/ and Data/processed/, which are gitignored.
This script is committed; its inputs are produced by the pipeline (see README).

Run: .venv/bin/python Code/analysis/reliability_rank_inversion.py
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

# Reuse committed primitives unchanged.
from build_access_g2sfca import (  # noqa: E402
    g2sfca, load_bg_centroids, D0_DCFC, METERS_PER_MILE, WGS84, CA_ALBERS,
)
from build_access_g2sfca_reliability import (  # noqa: E402
    success_rate, RELIABILITY_PRIORS, DEFAULT_RATE, PRIOR_SETS, _prior_rate,
)

STATIONS_CSV = ROOT / "Data" / "raw" / "afdc_stations_sandiego.csv"
ACCESS_CSV = ROOT / "Data" / "processed" / "blockgroup_access.csv"

CITED_INVERSION = 0.646
ANCHOR_BASE_MEDIAN = 0.6173        # committed reliability pop-wt median ratio
ANCHOR_TOL = 0.001


def load_bg() -> pd.DataFrame:
    cent = load_bg_centroids()                       # geoid, x, y, lon, lat
    acc = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    df = acc.merge(cent, on="geoid", how="left")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0)
    df["is_dac_b"] = df["is_dac"].map({True: True, False: False, "True": True, "False": False})
    return df[df["is_dac_b"].notna()].copy()


def load_dcfc_stations(status_filter) -> pd.DataFrame:
    """DCFC stations (ev_dc_fast_num >= 1), optionally restricted by status_code.
    Mirrors build_access_g2sfca_reliability.load_stations_with_network, adding the
    status filter applied at load time."""
    df = pd.read_csv(STATIONS_CSV).dropna(subset=["latitude", "longitude"]).copy()
    df["ev_dc_fast_num"] = pd.to_numeric(df["ev_dc_fast_num"], errors="coerce").fillna(0)
    df["ev_network"] = df["ev_network"].fillna("Non-Networked")
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


def popwt_median_ratio(bg: pd.DataFrame, st: pd.DataFrame, rate_fn) -> float:
    D = np.sqrt((bg["x"].to_numpy()[:, None] - st["x"].to_numpy()[None, :]) ** 2
                + (bg["y"].to_numpy()[:, None] - st["y"].to_numpy()[None, :]) ** 2) / METERS_PER_MILE
    rate = np.array([rate_fn(n) for n in st["ev_network"]])
    supply = st["ev_dc_fast_num"].to_numpy().astype(float) * rate
    access = g2sfca(D, bg["population"].to_numpy(), supply, D0_DCFC)
    dac = bg["is_dac_b"].to_numpy().astype(bool)
    pop = bg["population"].to_numpy()
    return wmedian(access[dac], pop[dac]) / wmedian(access[~dac], pop[~dac])


def build_inverted_priors() -> dict:
    """Reverse the network reliability ranking using the SAME value multiset:
    EVgo (DAC-dominant) gets the top value, Tesla the bottom, the rest take the
    remaining values in reversed baseline-rank order."""
    base = dict(RELIABILITY_PRIORS)
    values = sorted(base.values(), reverse=True)
    others = [k for k in base if k not in ("evgo", "tesla")]
    others_asc = sorted(others, key=lambda k: base[k])
    order = ["evgo"] + others_asc + ["tesla"]
    return dict(zip(order, values))


def inverted_rate(inv: dict):
    def f(network: str) -> float:
        n = (network or "").lower()
        if "tesla" in n: return inv["tesla"]
        if "chargepoint" in n: return inv["chargepoint"]
        if "electrify america" in n: return inv["electrify america"]
        if "evgo" in n or "ev go" in n: return inv["evgo"]
        if "blink" in n: return inv["blink"]
        if "shell recharge" in n: return inv["shell recharge"]
        return DEFAULT_RATE
    return f


def main() -> int:
    print("=" * 76)
    print("RELIABILITY RANK-INVERSION — composition test (pop-weighted median ratio)")
    print("=" * 76)
    bg = load_bg()
    st_all = load_dcfc_stations(None)

    # Positive anchor: base reliability ratio must reproduce the committed 0.6173.
    base = popwt_median_ratio(bg, st_all, success_rate)
    print(f"\n[anchor] base reliability pop-wt median ratio (all-status) = {base:.4f}  "
          f"(committed {ANCHOR_BASE_MEDIAN})")
    if abs(base - ANCHOR_BASE_MEDIAN) > ANCHOR_TOL:
        print(f"STOP: anchor self-check failed (|{base:.4f} - {ANCHOR_BASE_MEDIAN}| > {ANCHOR_TOL}).")
        return 1

    # Negative self-check: no committed prior set reproduces the cited 0.646.
    print("\n[self-check] committed PRIOR_SETS (pop-wt median) vs cited 0.646:")
    reproduced = False
    for name, p in PRIOR_SETS.items():
        r = popwt_median_ratio(bg, st_all, lambda net, _p=p: _prior_rate(net, _p))
        hit = abs(round(r, 3) - CITED_INVERSION) < 1e-9
        reproduced |= hit
        print(f"   {name:34s} {r:.4f}{'   <- equals 0.646' if hit else ''}")
    if reproduced:
        print("STOP: a committed set unexpectedly reproduced 0.646; investigate.")
        return 1
    print("   confirmed: 0.646 is NOT produced by any committed set (its generator was never committed).")

    # Reconstructed true inversion.
    inv = build_inverted_priors()
    print("\nReconstructed true inversion (baseline -> inverted; same value multiset):")
    for k in ["tesla", "chargepoint", "electrify america", "evgo", "blink", "shell recharge"]:
        print(f"   {k:18s} {RELIABILITY_PRIORS[k]:.2f} -> {inv[k]:.2f}")
    f = inverted_rate(inv)
    r_all = popwt_median_ratio(bg, load_dcfc_stations(None), f)
    r_e = popwt_median_ratio(bg, load_dcfc_stations(["E"]), f)

    print("\nINVERSION DCFC pop-weighted median ratio (DAC / non-DAC):")
    print(f"   all-status = {r_all:.4f}   (paper cited 0.646; not reproducible from committed code)")
    print(f"   E-only     = {r_e:.4f}")
    print("\nInterpretation: a ratio ABOVE the unweighted 0.632 but still BELOW 1.0 is the")
    print("composition signature — making the DAC network most reliable improves their")
    print("relative access yet the raw supply disparity leaves them worse served.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
