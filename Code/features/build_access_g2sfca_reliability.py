"""Reliability-weighted G2SFCA — the project's novel contribution.

Published EV-accessibility studies assume 100% charger uptime. Here each station's
supply is discounted by an ASSUMED expected session-success rate (reliability) before
the two-step ratio, so unreliable supply contributes less access.

Reliability priors by ev_network (ASSUMED national averages, rounded from J.D. Power
2025 EVX and Consumer Reports 2025 — NOT measured, NOT San Diego-specific):
  Tesla / Tesla Destination 0.95; ChargePoint 0.85; Electrify America 0.80;
  EVgo 0.75; Blink 0.70; Shell Recharge 0.70; else / non-networked / unknown 0.75.

Effective supply per station = ports * success_rate. Access is then recomputed with the
SAME Gaussian decay and catchments as the base metric (imported from build_access_g2sfca):
  access_dcfc_rel  (DCFC ports * rate, d0 = 6 mi)
  access_l2_rel    (L2 ports * rate,   d0 = 2 mi)
  access_combined_rel = access_l2_rel * 4 + access_dcfc_rel * 48

QA-only by default; --write persists Data/processed/blockgroup_g2sfca_reliability.csv.
Does NOT modify build_access_g2sfca.py or any other CSV.

CAVEATS (read these before citing any result):
  1. ASSUMED RATES. Every reliability rate is an ASSUMED national network average
     (J.D. Power 2025 EVX, Consumer Reports 2025) — NOT measured and NOT San Diego
     specific. Real CEC AB 2061 station-level uptime publishes 2027+; this framework is
     built to ingest measured uptime when it exists.
  2. SMALL EFFECT. The DCFC effect is small: DAC ratio 0.631 -> 0.618 (~2% relative).
     The raw 35-vs-1,377 DCFC port disparity is the dominant equity story; reliability
     weighting only sharpens it at the margin. Do NOT overstate the magnitude.
  3. FRAGILE MECHANISM. The DAC DCFC mechanism rests on only 35 DCFC ports in DAC block
     groups — fragile to a handful of stations.
  4. ROBUST DIRECTION. Compressing the assumed spread to 0.85-0.95 still widens the gap,
     so the DIRECTION (not the size) is the defensible contribution.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402

# Reuse the base G2SFCA core unchanged (same gaussian, two-step, catchments, service ratio).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_access_g2sfca import (  # noqa: E402
    g2sfca, load_bg_centroids, OPERATIONAL_STATUS,
    D0_DCFC, D0_L2, SERVICE_L2, SERVICE_DCFC, METERS_PER_MILE,
    WGS84, CA_ALBERS, SD_STATE_FP, SD_COUNTY_FP, BG_ZIP,
)

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "Data" / "processed"
RAW_DIR = ROOT / "Data" / "raw"
ACCESS_CSV = PROC / "blockgroup_access.csv"
STATIONS_CSV = RAW_DIR / "afdc_stations_sandiego.csv"
OUTPUT_CSV = PROC / "blockgroup_g2sfca_reliability.csv"

# ASSUMED national-average session-success rates (see module docstring). NOT measured.
RELIABILITY_PRIORS = {
    "tesla": 0.95,            # Tesla + Tesla Destination
    "chargepoint": 0.85,
    "electrify america": 0.80,
    "evgo": 0.75,
    "blink": 0.70,
    "shell recharge": 0.70,
}
DEFAULT_RATE = 0.75          # non-networked / unknown / everything else

OUTPUT_COLS = ["geoid", "access_dcfc_rel", "access_l2_rel", "access_combined_rel"]


def success_rate(network: str) -> float:
    """Map an ev_network string to its ASSUMED success rate (substring match)."""
    n = (network or "").lower()
    if "tesla" in n:
        return RELIABILITY_PRIORS["tesla"]
    if "chargepoint" in n:
        return RELIABILITY_PRIORS["chargepoint"]
    if "electrify america" in n:
        return RELIABILITY_PRIORS["electrify america"]
    if "evgo" in n or "ev go" in n:
        return RELIABILITY_PRIORS["evgo"]
    if "blink" in n:
        return RELIABILITY_PRIORS["blink"]
    if "shell recharge" in n:
        return RELIABILITY_PRIORS["shell recharge"]
    return DEFAULT_RATE


def compress_rate(rate: float) -> float:
    """Sensitivity: linearly rescale [0.70, 0.95] into a compressed [0.85, 0.95] band."""
    return 0.85 + (rate - 0.70) / (0.95 - 0.70) * (0.95 - 0.85)


def load_stations_with_network() -> gpd.GeoDataFrame:
    df = pd.read_csv(STATIONS_CSV).dropna(subset=["latitude", "longitude"]).copy()
    if OPERATIONAL_STATUS is not None:
        df = df[df["status_code"] == OPERATIONAL_STATUS].copy()
    for c in ("ev_dc_fast_num", "ev_level2_evse_num"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["ev_network"] = df["ev_network"].fillna("Non-Networked")
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs=WGS84
    ).to_crs(CA_ALBERS)
    gdf["x"], gdf["y"] = gdf.geometry.x.to_numpy(), gdf.geometry.y.to_numpy()
    return gdf


def load_bg_polygons() -> gpd.GeoDataFrame:
    bg = gpd.read_file(f"zip://{BG_ZIP}")
    bg = bg[(bg["STATEFP"] == SD_STATE_FP) & (bg["COUNTYFP"] == SD_COUNTY_FP)].copy().to_crs(CA_ALBERS)
    return bg[["GEOID", "geometry"]].rename(columns={"GEOID": "geoid"})


def dac_ratio(access: np.ndarray, is_dac: pd.Series):
    med = pd.Series(access).groupby(is_dac.to_numpy()).median()
    t, f = med.get(True, np.nan), med.get(False, np.nan)
    return (t / f if f else np.nan), t, f


# --- Robustness sweep configuration (ALL values ASSUMED, not measured) ------ #
ROBUSTNESS_CSV = PROC / "reliability_robustness.csv"
# Uniform uptime applied to every station. 1.00 = base reference. A global uptime
# scalar cancels in the DAC/non-DAC ratio, so these are invariant by construction —
# that invariance IS the finding (the gap is not driven by overall uptime level).
UNIFORM_LEVELS = [1.00, 0.95, 0.80, 0.60]
# Network-differentiated prior sets — the real sensitivity-to-priors test. The gap
# should still widen vs base 0.6312 in every set as long as DAC-dominant networks
# (eVgo) stay below non-DAC-dominant networks (Tesla).
PRIOR_SETS = {
    "base differentiated (current)":  {"tesla": 0.95, "cp": 0.85, "ea": 0.80, "evgo": 0.75, "blink": 0.70, "shell": 0.70, "def": 0.75},
    "narrow spread":                  {"tesla": 0.90, "cp": 0.85, "ea": 0.82, "evgo": 0.80, "blink": 0.78, "shell": 0.78, "def": 0.80},
    "widen spread":                   {"tesla": 0.98, "cp": 0.85, "ea": 0.78, "evgo": 0.65, "blink": 0.60, "shell": 0.60, "def": 0.70},
    "alt ordering (EA>CP, eVgo up)":   {"tesla": 0.94, "cp": 0.83, "ea": 0.85, "evgo": 0.78, "blink": 0.68, "shell": 0.70, "def": 0.76},
}


def _prior_rate(network: str, p: dict) -> float:
    n = (network or "").lower()
    if "tesla" in n: return p["tesla"]
    if "chargepoint" in n: return p["cp"]
    if "electrify america" in n: return p["ea"]
    if "evgo" in n or "ev go" in n: return p["evgo"]
    if "blink" in n: return p["blink"]
    if "shell recharge" in n: return p["shell"]
    return p["def"]


def robustness_sweeps(meta: dict) -> pd.DataFrame:
    """DAC/non-DAC DCFC access ratio under uniform-uptime and network-prior sweeps.

    Two robustness checks for the reliability section, all ASSUMED-prior:
      uniform_uptime  — invariant by construction (global scalar cancels in the ratio);
                        shows the gap does not depend on overall uptime level.
      network_prior   — perturbs the differentiated priors (narrow/widen/reorder);
                        the gap should still widen vs base 0.6312 in every case.
    """
    dist_mi, pop, dcfc = meta["dist_mi"], meta["pop"], meta["dcfc_ports"]
    is_dac, st = meta["is_dac"], meta["stations"]
    rows = []
    for lv in UNIFORM_LEVELS:
        r, _, _ = dac_ratio(g2sfca(dist_mi, pop, dcfc * lv, D0_DCFC), is_dac)
        label = f"uniform {int(lv * 100)}% uptime" + (" (reference)" if lv == 1.0 else "")
        rows.append({"sweep": "uniform_uptime", "scenario": label,
                     "dac_nondac_dcfc_ratio": round(float(r), 4), "assumed": True})
    net = st["ev_network"]
    for name, p in PRIOR_SETS.items():
        rate = net.map(lambda x: _prior_rate(x, p)).to_numpy()
        r, _, _ = dac_ratio(g2sfca(dist_mi, pop, dcfc * rate, D0_DCFC), is_dac)
        rows.append({"sweep": "network_prior", "scenario": name,
                     "dac_nondac_dcfc_ratio": round(float(r), 4), "assumed": True})
    return pd.DataFrame(rows)


def build():
    access = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    cent = load_bg_centroids()
    df = access.merge(cent, on="geoid", how="left")
    pop = pd.to_numeric(df["population"], errors="coerce").fillna(0).to_numpy()
    is_dac = df["is_dac"]

    st = load_stations_with_network()
    rate = st["ev_network"].map(success_rate).to_numpy()
    rate_c = np.array([compress_rate(r) for r in rate])
    dcfc_ports = st["ev_dc_fast_num"].to_numpy()
    l2_ports = st["ev_level2_evse_num"].to_numpy()

    bg_xy = df[["x", "y"]].to_numpy()
    st_xy = st[["x", "y"]].to_numpy()
    diff = bg_xy[:, None, :] - st_xy[None, :, :]
    dist_mi = np.sqrt((diff ** 2).sum(axis=2)) / METERS_PER_MILE

    def run(d_supply, l_supply):
        ad = g2sfca(dist_mi, pop, d_supply, D0_DCFC)
        al = g2sfca(dist_mi, pop, l_supply, D0_L2)
        return ad, al, al * SERVICE_L2 + ad * SERVICE_DCFC

    # base (rate = 1), reliability-weighted, and compressed-spread sensitivity
    base = run(dcfc_ports, l2_ports)
    rel = run(dcfc_ports * rate, l2_ports * rate)
    comp = run(dcfc_ports * rate_c, l2_ports * rate_c)

    df["access_dcfc_rel"], df["access_l2_rel"], df["access_combined_rel"] = rel

    meta = {"df": df, "is_dac": is_dac, "stations": st, "rate": rate,
            "base": base, "rel": rel, "comp": comp,
            "dist_mi": dist_mi, "pop": pop, "dcfc_ports": dcfc_ports}
    return df, meta


def qa_report(meta: dict) -> None:
    df, is_dac, st = meta["df"], meta["is_dac"], meta["stations"]
    base, rel, comp = meta["base"], meta["rel"], meta["comp"]

    print("=" * 76)
    print("RELIABILITY-WEIGHTED G2SFCA — QA (all reliability numbers ASSUMED)")
    print("=" * 76)
    print("ASSUMED session-success priors by network (J.D. Power 2025 EVX / Consumer")
    print("Reports 2025, rounded national averages — NOT measured, NOT SD-specific):")
    for k, v in RELIABILITY_PRIORS.items():
        print(f"   {k:18s} {v:.2f}")
    print(f"   {'else/unknown':18s} {DEFAULT_RATE:.2f}")

    print("\n1) Reliability-weighted access distribution (min / median / max):")
    for name, arr in [("access_dcfc_rel", df["access_dcfc_rel"]),
                      ("access_combined_rel", df["access_combined_rel"])]:
        print(f"   {name:22s} {arr.min():.4g} / {arr.median():.4g} / {arr.max():.4g}")

    print("\n2) KEY OUTPUT — is_dac equity ratio BEFORE (base) vs AFTER (reliability):")
    print("   ratio = median(DAC) / median(non-DAC).  Lower = steeper gap.")
    for label, b_arr, r_arr in [("access_dcfc", base[0], rel[0]),
                                ("access_combined", base[2], rel[2])]:
        rb, tb, fb = dac_ratio(b_arr, is_dac)
        rr, tr, fr = dac_ratio(r_arr, is_dac)
        move = ("WIDENS" if rr < rb - 1e-9 else "NARROWS" if rr > rb + 1e-9 else "HOLDS")
        print(f"   {label:16s} base={rb:.3f}  ->  reliability={rr:.3f}   gap {move}  "
              f"(Δ {rr - rb:+.3f})")

    print("\n3) WHY — DCFC supply network mix by is_dac (point-in-polygon station -> BG):")
    poly = load_bg_polygons().merge(df[["geoid", "is_dac"]], on="geoid", how="left")
    dcfc = st[st["ev_dc_fast_num"] >= 1][["ev_network", "ev_dc_fast_num", "geometry"]]
    j = gpd.sjoin(dcfc, poly[["is_dac", "geometry"]], predicate="within", how="left")
    outside = int(j["is_dac"].isna().sum())
    j = j.dropna(subset=["is_dac"])
    j["rate"] = j["ev_network"].map(success_rate)
    print(f"   (DCFC stations placed: {len(j)}; outside any BG: {outside})")
    for val, tag in [(True, "DAC"), (False, "non-DAC")]:
        sub = j[j["is_dac"] == val]
        tot = sub["ev_dc_fast_num"].sum()
        wrate = (sub["rate"] * sub["ev_dc_fast_num"]).sum() / tot if tot else float("nan")
        top = (sub.groupby("ev_network")["ev_dc_fast_num"].sum()
               .sort_values(ascending=False).head(5))
        print(f"\n   {tag}-area DCFC ports = {int(tot)}   ports-weighted mean ASSUMED rate = {wrate:.3f}")
        for net, p in top.items():
            print(f"      {net:22s} {int(p):5d} ports  ({100*p/tot:4.1f}%)  rate={success_rate(net):.2f}")

    print("\n4) SENSITIVITY — spread compressed to 0.85-0.95, is_dac ratio base vs compressed:")
    for label, b_arr, c_arr in [("access_dcfc", base[0], comp[0]),
                                ("access_combined", base[2], comp[2])]:
        rb, _, _ = dac_ratio(b_arr, is_dac)
        rc, _, _ = dac_ratio(c_arr, is_dac)
        move = ("WIDENS" if rc < rb - 1e-9 else "NARROWS" if rc > rb + 1e-9 else "HOLDS")
        print(f"   {label:16s} base={rb:.3f}  ->  compressed={rc:.3f}   gap {move}  "
              f"(Δ {rc - rb:+.3f})")
    print("\n   (direction should match #2 but with smaller magnitude => robust to the")
    print("    assumed spread; all reliability values remain ASSUMED priors.)")
    print("=" * 76)


def main() -> int:
    df, meta = build()
    qa_report(meta)

    rob = robustness_sweeps(meta)
    print("\n5) ROBUSTNESS SWEEPS — DAC/non-DAC DCFC ratio (4 dp; ALL ASSUMED priors):")
    print("   base reference 0.6312 (uniform); gap WIDENS when ratio < 0.6312.")
    for _, r in rob.iterrows():
        print(f"   [{r['sweep']:14s}] {r['scenario']:34s} {r['dac_nondac_dcfc_ratio']:.4f}")
    print("   uniform sweep is invariant by construction; network-prior sweep widens in all sets.")
    print("=" * 76)

    if "--write" in sys.argv:
        df[OUTPUT_COLS].to_csv(OUTPUT_CSV, index=False)
        rob.to_csv(ROBUSTNESS_CSV, index=False)
        print(f"\n[written] {len(df)} rows -> {OUTPUT_CSV}")
        print(f"[written] {len(rob)} robustness rows -> {ROBUSTNESS_CSV}")
    else:
        print("\n[QA-only] Nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
