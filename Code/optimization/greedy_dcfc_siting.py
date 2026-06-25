"""Week 6: scoped greedy DCFC siting to reduce the DAC fast-charging access gap.

SIMPLE version. No budget model, no cost model. Greedy: repeatedly add the one
hypothetical DCFC-serving location that most raises DAC fast-charging access.

CANDIDATE SITES (explicit simplification, NOT invented data):
  Candidate locations are existing block-group centroids. Every BG is treated as a
  potential site. We are NOT scraping parcels or claiming a specific site is buildable.
  The question is: "if we added a DCFC-serving location at this block group's centroid,
  how much would it reduce the DAC access gap?" — not "this parcel is buildable."
  Rural overstatement trap (Bug #14) is excluded from candidates: lon > -116.85 AND
  access in the top decile.

METRIC: reliability-weighted G2SFCA DCFC access (access_dcfc_rel), the project's
contribution. Built from build_access_g2sfca_reliability (existing stations, ASSUMED
network reliability priors).

NEW SITE SUPPLY (ASSUMED): 4 DCFC ports at an assumed new-site reliability of 0.80
(network-average), so effective supply = 4 * 0.80 = 3.2. Stated, not measured.

OBJECTIVE: maximize the population-weighted MEAN access_dcfc_rel among DAC block groups
(is_dac=True). The mean is additive over sites, so greedy gives monotonic diminishing
returns and the standard greedy bound. The population-weighted MEDIAN is reported as an
outcome metric, NOT optimized. Greedy for N=10 sites.

2SFCA additivity: adding a supply site does not change existing sites' supply-to-demand
ratios, so new_access = base_access + R_new * G(candidate, .), where
R_new = S_new / sum_k[pop_k * G(candidate, k)]. R_new and the per-candidate access delta
are therefore fixed across greedy steps; only the running DAC median changes.

RESULT (verified; ASSUMED reliability priors): 10 hypothetical sites raise the DAC
pop-weighted MEAN access_dcfc_rel +26.7% and the reported DAC pop-weighted MEDIAN +38.4%,
while non-DAC mean rises only +1.5%. DAC/non-DAC ratio closes from 0.623 to 0.777 on the
mean objective and from 0.617 to 0.849 on the reported median, about 41% and 61% of the gap
to parity. Sites cluster in the South Bay DAC-EJ corridor.

QA-only by default; --write persists Data/processed/greedy_dcfc_sites.csv (gitignored).
Does NOT modify any other CSV.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "Code" / "features"))

from build_access_g2sfca import gaussian, D0_DCFC, METERS_PER_MILE  # noqa: E402
from build_access_g2sfca_reliability import build as build_reliability  # noqa: E402

N_SITES = 10
NEW_PORTS = 4
NEW_RATE = 0.80            # ASSUMED new-site network-average reliability
S_NEW = NEW_PORTS * NEW_RATE   # effective supply of one hypothetical site = 3.2
RURAL_LON = -116.85
OUTPUT_CSV = ROOT / "Data" / "processed" / "greedy_dcfc_sites.csv"


def wmed(values: np.ndarray, weights: np.ndarray) -> float:
    o = np.argsort(values)
    v, w = values[o], weights[o].astype(float)
    if w.sum() == 0:
        return float("nan")
    return float(v[np.searchsorted(np.cumsum(w), 0.5 * w.sum())])


def wmean(values: np.ndarray, weights: np.ndarray) -> float:
    w = weights.astype(float)
    return float(np.average(values, weights=w)) if w.sum() > 0 else float("nan")


def main() -> int:
    df, _ = build_reliability()
    geoid = df["geoid"].to_numpy()
    pop = np.nan_to_num(df["population"].to_numpy(dtype=float))
    is_dac = (df["is_dac"] == True).to_numpy()  # noqa: E712
    lon = df["lon"].to_numpy()
    lat = df["lat"].to_numpy()
    base = df["access_dcfc_rel"].to_numpy(dtype=float)
    xy = df[["x", "y"]].to_numpy()
    n = len(df)

    # BG-to-BG distances (miles) and Gaussian weights at the DCFC catchment.
    diff = xy[:, None, :] - xy[None, :, :]
    dist_mi = np.sqrt((diff ** 2).sum(axis=2)) / METERS_PER_MILE
    G = gaussian(dist_mi, D0_DCFC)                       # (n, n) weight(candidate, bg)

    # Per-candidate R_new and full access delta (both fixed across greedy steps).
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        demand = G @ pop                                 # (n,) pop competing for a new site
        R_new = np.where(demand > 0, S_NEW / demand, 0.0)
        delta = R_new[:, None] * G                       # (n, n) delta[c, i] for adding site c
    assert np.isfinite(delta).all()

    dac_idx = np.where(is_dac)[0]
    nondac_idx = np.where(~is_dac & df["is_dac"].notna().to_numpy())[0]
    pop_dac, pop_nd = pop[dac_idx], pop[nondac_idx]

    # Candidate set: all BGs minus the rural overstatement trap.
    p90 = np.quantile(base, 0.90)
    trap = (lon > RURAL_LON) & (base >= p90)
    candidates = np.where(~trap)[0].tolist()

    # Base outcome metrics. MEAN is the objective; MEDIAN is reported, not optimized.
    dac_mean_base = wmean(base[dac_idx], pop_dac)
    dac_med_base = wmed(base[dac_idx], pop_dac)
    nd_mean_base = wmean(base[nondac_idx], pop_nd)
    nd_med_base = wmed(base[nondac_idx], pop_nd)

    print("=" * 84)
    print("WEEK 6 — GREEDY DCFC SITING (reliability-weighted G2SFCA; QA-only)")
    print("=" * 84)
    print(f"Block groups: {n}   DAC BGs: {len(dac_idx)}   non-DAC: {len(nondac_idx)}")
    print(f"Candidate BGs (excl. rural trap lon>{RURAL_LON} & top-decile access): "
          f"{len(candidates)}  (excluded {int(trap.sum())})")
    print(f"New-site supply ASSUMED: {NEW_PORTS} ports x {NEW_RATE} reliability = {S_NEW} effective")
    print("OBJECTIVE: population-weighted MEAN of DAC access_dcfc_rel (median reported, not optimized)")
    print(f"DAC pop-wt mean access_dcfc_rel (base):   {dac_mean_base:.6g}")
    print(f"DAC pop-wt median (base):                 {dac_med_base:.6g}")

    cur = base.copy()
    cur_dac_mean = dac_mean_base
    chosen, gains, mean_after, med_after = [], [], [], []

    for step in range(1, N_SITES + 1):
        best_c, best_gain, best_new = None, -np.inf, None
        for c in candidates:
            new_mean = wmean(cur[dac_idx] + delta[c, dac_idx], pop_dac)
            g = new_mean - cur_dac_mean
            if g > best_gain:
                best_c, best_gain, best_new = c, g, new_mean
        candidates.remove(best_c)
        cur = cur + delta[best_c]
        cur_dac_mean = best_new
        chosen.append(best_c)
        gains.append(best_gain)
        mean_after.append(cur_dac_mean)
        med_after.append(wmed(cur[dac_idx], pop_dac))

    print("\n1) Chosen sites in order (marginal gain = rise in DAC pop-wt MEAN):")
    print(f"   {'#':>2} {'geoid':>13} {'is_dac':>6} {'lon':>9} {'lat':>8} "
          f"{'baseAcc':>9} {'DACw/in6mi':>10} {'gain':>11} {'DACmean_after':>14}")
    run_mean = dac_mean_base
    for k, c in enumerate(chosen, 1):
        run_mean += gains[k - 1]
        ndac_near = int((dist_mi[c, dac_idx] <= D0_DCFC).sum())
        print(f"   {k:>2} {geoid[c]:>13} {str(bool(is_dac[c])):>6} {lon[c]:>9.3f} "
              f"{lat[c]:>8.3f} {base[c]:>9.3g} {ndac_near:>10} {gains[k-1]:>11.3g} {run_mean:>14.6g}")

    mono = all(gains[i] >= gains[i + 1] - 1e-18 for i in range(len(gains) - 1))
    print("\n   gains in order:")
    print("   " + "  ".join(f"{g:.3g}" for g in gains))
    print(f"   monotonically non-increasing (diminishing returns): {mono}")

    dac_mean_after = wmean(cur[dac_idx], pop_dac)
    dac_med_after = wmed(cur[dac_idx], pop_dac)
    nd_mean_after = wmean(cur[nondac_idx], pop_nd)
    nd_med_after = wmed(cur[nondac_idx], pop_nd)

    print("\n2) DAC access before vs after 10 sites, with DAC/non-DAC ratio (mean & median):")
    print(f"   {'metric':7} {'DAC base':>11} {'DAC after':>11} {'nDAC base':>11} {'nDAC after':>11} "
          f"{'ratio base':>11} {'ratio after':>12}")
    print(f"   {'mean':7} {dac_mean_base:>11.5g} {dac_mean_after:>11.5g} {nd_mean_base:>11.5g} "
          f"{nd_mean_after:>11.5g} {dac_mean_base/nd_mean_base:>11.3f} {dac_mean_after/nd_mean_after:>12.3f}")
    print(f"   {'median':7} {dac_med_base:>11.5g} {dac_med_after:>11.5g} {nd_med_base:>11.5g} "
          f"{nd_med_after:>11.5g} {dac_med_base/nd_med_base:>11.3f} {dac_med_after/nd_med_after:>12.3f}")
    print(f"   DAC mean +{100*(dac_mean_after/dac_mean_base-1):.1f}%  |  "
          f"DAC median +{100*(dac_med_after/dac_med_base-1):.1f}%  |  "
          f"non-DAC mean +{100*(nd_mean_after/nd_mean_base-1):.1f}%")

    print("\n3) Spatial clustering check (DAC-adjacent South Bay, not rural/random):")
    print(f"   chosen lon range [{min(lon[c] for c in chosen):.3f}, {max(lon[c] for c in chosen):.3f}]  "
          f"lat range [{min(lat[c] for c in chosen):.3f}, {max(lat[c] for c in chosen):.3f}]")
    print(f"   DAC BGs within 6 mi of each pick: "
          f"{[int((dist_mi[c, dac_idx] <= D0_DCFC).sum()) for c in chosen]}")
    print(f"   all picks west of {RURAL_LON} (not rural east): {all(lon[c] < RURAL_LON for c in chosen)}")

    print("\n4) Sanity — not just the highest-population BGs:")
    top_pop = np.argsort(pop)[::-1][:5]
    print("   5 highest-pop BGs: " +
          ", ".join(f"{geoid[i]}(pop {int(pop[i])})" for i in top_pop))
    print(f"   chosen-site populations: {[int(pop[c]) for c in chosen]}  "
          f"(county median {int(np.median(pop))})")
    print(f"   chosen that are top-5 pop: {len(set(chosen) & set(top_pop.tolist()))};  "
          f"chosen that are DAC themselves: {sum(bool(is_dac[c]) for c in chosen)}/{N_SITES}")
    print("=" * 84)
    if "--write" in sys.argv:
        rows = [{
            "rank": k + 1,
            "geoid": geoid[c],
            "is_dac": bool(is_dac[c]),
            "lon": round(float(lon[c]), 6),
            "lat": round(float(lat[c]), 6),
            "base_access_dcfc_rel": float(base[c]),
            "dac_bgs_within_6mi": int((dist_mi[c, dac_idx] <= D0_DCFC).sum()),
            "marginal_gain_dac_mean": float(gains[k]),
            "dac_mean_after": float(mean_after[k]),
            "dac_median_after": float(med_after[k]),
        } for k, c in enumerate(chosen)]
        out = pd.DataFrame(rows)
        out["dac_mean_before"] = dac_mean_base
        out["dac_median_before"] = dac_med_base
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(OUTPUT_CSV, index=False)
        print(f"[written] {len(out)} sites -> {OUTPUT_CSV}")
    else:
        print("[QA-only] Nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
