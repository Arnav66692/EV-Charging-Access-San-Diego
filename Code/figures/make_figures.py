"""Generate publication-quality paper figures from the committed processed CSVs.

Six figures (300 DPI PNG, colorblind-safe Okabe-Ito palette) -> Figures/:
  F1  the reversal: DAC vs non-DAC, distance-to-DCFC (closer) vs G2SFCA access (worse)
  F2  county choropleth of DCFC G2SFCA access (percentile shading)
  F3  Q4/Q1 access ratio by equity axis (income, renter, multifamily, DAC), L2 vs DCFC
  F4  reliability mechanism: DCFC supply network mix by is_dac
  F5  reliability-weighted DAC/non-DAC ratio, base vs reliability-weighted
  F6  centerpiece map: 10 greedy DCFC sites over DAC-shaded San Diego County

Read-only on the CSVs (plus TIGER BG geometry and the AFDC stations CSV for the
network-mix and map figures). Writes only PNGs to Figures/.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "Data" / "processed"
RAW = ROOT / "Data" / "raw"
FIG = ROOT / "Figures"
sys.path.insert(0, str(ROOT / "Code" / "analysis"))
from equity_contrasts import pop_quartiles  # noqa: E402  (shared pop-weighted quartile method)

BG_ZIP = RAW / "tl_2024_06_bg.zip"
STATIONS_CSV = RAW / "afdc_stations_sandiego.csv"
CA_ALBERS = "EPSG:3310"
WGS84 = "EPSG:4326"
SD_STATE, SD_CTY = "06", "073"
DPI = 300
# Operational-only default; mirrors build_access_g2sfca.OPERATIONAL_STATUS. The access
# columns in the processed CSVs are already E-only (built operational-only); this filter
# keeps fig4's direct station read consistent. Set to None to include all statuses.
OPERATIONAL_STATUS = "E"

# Okabe-Ito colorblind-safe palette
OI = {
    "orange": "#E69F00", "skyblue": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
    "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7", "black": "#000000",
    "grey": "#999999",
}
C_DAC, C_NONDAC = OI["vermillion"], OI["blue"]   # DAC highlighted, non-DAC reference

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": DPI, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "figure.autolayout": False,
})


def wmed(v: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(v)
    v, w = v[o], w[o].astype(float)
    return float(v[np.searchsorted(np.cumsum(w), 0.5 * w.sum())]) if w.sum() else float("nan")


def load_joined() -> pd.DataFrame:
    acc = pd.read_csv(PROC / "blockgroup_access.csv", dtype={"geoid": str})
    g2 = pd.read_csv(PROC / "blockgroup_g2sfca.csv", dtype={"geoid": str})
    dist = pd.read_csv(PROC / "blockgroup_distance.csv", dtype={"geoid": str})
    rel = pd.read_csv(PROC / "blockgroup_g2sfca_reliability.csv", dtype={"geoid": str})
    df = acc.merge(g2, on="geoid").merge(dist, on="geoid").merge(rel, on="geoid")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0)
    # Exclude the single NaN-is_dac BG (water tract 06073 9901, population 0) before the bool
    # coercion so the figure path matches the numbers pipeline: 142 DAC / 1915 non-DAC / 1 excluded.
    df = df[df["is_dac"].notna()].copy()
    df["is_dac"] = df["is_dac"] == True  # noqa: E712
    return df


def load_bg_geom() -> gpd.GeoDataFrame:
    bg = gpd.read_file(f"zip://{BG_ZIP}")
    bg = bg[(bg["STATEFP"] == SD_STATE) & (bg["COUNTYFP"] == SD_CTY)].copy().to_crs(CA_ALBERS)
    return bg[["GEOID", "geometry"]].rename(columns={"GEOID": "geoid"})


def _saved(path: Path, ax_or_vals) -> None:
    """Print a save confirmation with a non-empty sanity check."""
    n = ax_or_vals if isinstance(ax_or_vals, int) else len(ax_or_vals)
    print(f"  saved {path.name}  ({path.stat().st_size // 1024} KB, {n} data elements)")
    assert n > 0, f"{path.name} appears empty"


# --------------------------------------------------------------------------- #

def fig1_reversal(df: pd.DataFrame) -> None:
    dac, nd = df[df.is_dac], df[~df.is_dac]
    d_dac = wmed(dac["dist_nearest_dcfc_mi"].to_numpy(), dac["population"].to_numpy())
    d_nd = wmed(nd["dist_nearest_dcfc_mi"].to_numpy(), nd["population"].to_numpy())
    a_dac = wmed(dac["access_dcfc"].to_numpy(), dac["population"].to_numpy())
    a_nd = wmed(nd["access_dcfc"].to_numpy(), nd["population"].to_numpy())

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9, 4.2))
    for ax, vals, title, ylab, better in [
        (axL, (d_dac, d_nd), "Distance to nearest DCFC\n(DAC are CLOSER)", "miles (pop-wt median)", "low"),
        (axR, (a_dac, a_nd), "G2SFCA DCFC access\n(DAC are WORSE served)", "access (pop-wt median)", "high"),
    ]:
        bars = ax.bar(["DAC", "non-DAC"], vals, color=[C_DAC, C_NONDAC], width=0.6)
        ax.set_title(title); ax.set_ylabel(ylab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.3g}", ha="center", va="bottom", fontsize=9)
        ax.margins(y=0.18)
    fig.suptitle("The reversal: DACs are closer to fast charging yet have less access",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    p = FIG / "F1_reversal_distance_vs_access.png"
    fig.savefig(p); plt.close(fig)
    _saved(p, 4)


def fig2_choropleth(df: pd.DataFrame, geom: gpd.GeoDataFrame) -> None:
    # G2SFCA overstates access in sparse rural BGs (few people competing). Grey out
    # low-density BGs so the colored surface reflects access where people actually live.
    DENS_MIN = 200.0  # people / km^2
    g = geom.merge(df[["geoid", "access_dcfc", "population"]], on="geoid", how="left")
    g["dens"] = g["population"] / (g.geometry.area / 1e6)
    pop_mask = g["dens"] >= DENS_MIN
    g["pct"] = np.nan
    g.loc[pop_mask, "pct"] = g.loc[pop_mask, "access_dcfc"].rank(pct=True) * 100

    fig, ax = plt.subplots(figsize=(7.5, 8))
    g[~pop_mask].plot(ax=ax, color="#E0E0E0", edgecolor="none")
    g[pop_mask].plot(column="pct", cmap="cividis", legend=True, ax=ax, edgecolor="none",
                     legend_kwds={"label": "DCFC access (G2SFCA percentile, populated BGs)",
                                  "shrink": 0.55})
    g.dissolve().boundary.plot(ax=ax, color=OI["black"], linewidth=0.6)
    ax.set_title("DCFC accessibility across San Diego County\n"
                 f"(grey = low-density BGs <{DENS_MIN:.0f}/km²; G2SFCA overstates sparse areas)",
                 fontsize=11)
    ax.set_axis_off()
    fig.tight_layout()
    p = FIG / "F2_access_choropleth.png"
    fig.savefig(p); plt.close(fig)
    _saved(p, int(pop_mask.sum()))


def fig3_ratios(df: pd.DataFrame) -> None:
    axes_def = [("median_hhi", "Income"), ("renter_percent", "Renter"),
                ("multifamily_housing_percent", "Multifamily")]
    labels, l2r, dcr = [], [], []
    for var, name in axes_def:
        q = pop_quartiles(df[var], df["population"])
        d = df.assign(_q=q).dropna(subset=["_q"])
        for col, store in (("access_l2", l2r), ("access_dcfc", dcr)):
            q4, q1 = d[d["_q"] == 4], d[d["_q"] == 1]
            m4 = wmed(q4[col].to_numpy(), q4["population"].to_numpy())
            m1 = wmed(q1[col].to_numpy(), q1["population"].to_numpy())
            store.append(m4 / m1)
        labels.append(name)
    # DAC: DAC / non-DAC ratio (population-weighted median, headline estimator)
    for col, store in (("access_l2", l2r), ("access_dcfc", dcr)):
        dac_g, nd_g = df[df.is_dac], df[~df.is_dac]
        mt = wmed(dac_g[col].to_numpy(), dac_g["population"].to_numpy())
        mf = wmed(nd_g[col].to_numpy(), nd_g["population"].to_numpy())
        store.append(mt / mf)
    labels.append("DAC")

    x = np.arange(len(labels)); w = 0.38
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.bar(x - w/2, l2r, w, label="L2", color=OI["green"])
    ax.bar(x + w/2, dcr, w, label="DCFC", color=OI["orange"])
    ax.axhline(1.0, color=OI["black"], lw=1, ls="--")
    ax.text(len(labels)-0.5, 1.02, "parity", fontsize=8, color=OI["black"])
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("access ratio  (Q4/Q1; DAC = DAC/non-DAC)")
    ax.set_title("Access ratios by equity axis (Q4/Q1; DAC = DAC/non-DAC)\n"
                 "Renters better-served (esp. L2); DAC is the sharpest gap", fontsize=11)
    for xi, (a, b) in enumerate(zip(l2r, dcr)):
        ax.text(xi - w/2, a, f"{a:.2f}", ha="center", va="bottom", fontsize=8)
        ax.text(xi + w/2, b, f"{b:.2f}", ha="center", va="bottom", fontsize=8)
    ax.legend(); ax.margins(y=0.15)
    fig.tight_layout()
    p = FIG / "F3_equity_ratios_L2_vs_DCFC.png"
    fig.savefig(p); plt.close(fig)
    _saved(p, len(labels) * 2)


def _network_group(name: str) -> str:
    n = (name or "").lower()
    if "tesla" in n: return "Tesla"
    if "evgo" in n: return "eVgo"
    if "electrify america" in n: return "Electrify America"
    if "chargepoint" in n: return "ChargePoint"
    return "Other"


def fig4_network_mix(df: pd.DataFrame, geom: gpd.GeoDataFrame) -> None:
    poly = geom.merge(df[["geoid", "is_dac"]], on="geoid", how="left")
    st = pd.read_csv(STATIONS_CSV).dropna(subset=["latitude", "longitude"]).copy()
    if OPERATIONAL_STATUS is not None:
        st = st[st["status_code"] == OPERATIONAL_STATUS].copy()
    st["ev_dc_fast_num"] = pd.to_numeric(st["ev_dc_fast_num"], errors="coerce").fillna(0)
    st = st[st["ev_dc_fast_num"] >= 1]
    sp = gpd.GeoDataFrame(st, geometry=gpd.points_from_xy(st.longitude, st.latitude),
                          crs=WGS84).to_crs(CA_ALBERS)
    j = gpd.sjoin(sp[["ev_network", "ev_dc_fast_num", "geometry"]],
                  poly[["is_dac", "geometry"]], predicate="within", how="left").dropna(subset=["is_dac"])
    j["grp"] = j["ev_network"].map(_network_group)
    order = ["Tesla", "Electrify America", "eVgo", "ChargePoint", "Other"]
    colors = [OI["blue"], OI["orange"], OI["vermillion"], OI["green"], OI["grey"]]

    fig, ax = plt.subplots(figsize=(7, 4.6))
    groups = ["DAC areas", "non-DAC areas"]
    bottoms = np.zeros(2)
    for net, col in zip(order, colors):
        shares = []
        for val in (True, False):
            sub = j[j["is_dac"] == val]
            tot = sub["ev_dc_fast_num"].sum()
            seg = sub.loc[sub["grp"] == net, "ev_dc_fast_num"].sum() / tot * 100 if tot else 0
            shares.append(seg)
        ax.bar(groups, shares, bottom=bottoms, label=net, color=col, width=0.55)
        for i, s in enumerate(shares):
            if s > 4:
                ax.text(i, bottoms[i] + s/2, f"{s:.0f}%", ha="center", va="center",
                        fontsize=8, color="white" if net != "ChargePoint" else "black")
        bottoms += shares
    ax.set_ylabel("share of DCFC ports (%)")
    ax.set_title("Why reliability widens the gap:\nDAC DCFC supply is eVgo-heavy, non-DAC is Tesla-heavy")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
    ax.set_ylim(0, 100)
    fig.tight_layout()
    p = FIG / "F4_network_mix_by_dac.png"
    fig.savefig(p); plt.close(fig)
    _saved(p, len(order) * 2)


def fig5_reliability_ratio(df: pd.DataFrame) -> None:
    def ratio(col):
        dac_g, nd_g = df[df.is_dac], df[~df.is_dac]
        return (wmed(dac_g[col].to_numpy(), dac_g["population"].to_numpy())
                / wmed(nd_g[col].to_numpy(), nd_g["population"].to_numpy()))
    base = ratio("access_dcfc")
    rel = ratio("access_dcfc_rel")
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    bars = ax.bar(["Base\n(100% uptime)", "Reliability-\nweighted"], [base, rel],
                  color=[OI["skyblue"], OI["vermillion"]], width=0.55)
    ax.axhline(1.0, color=OI["black"], lw=1, ls="--")
    ax.text(1.5, 1.01, "parity", fontsize=8, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("DAC / non-DAC median DCFC access ratio")
    ax.set_title("Reliability weighting widens the DAC gap\n(small but consistent; ASSUMED priors)")
    for b, v in zip(bars, [base, rel]):
        ax.text(b.get_x()+b.get_width()/2, v, f"{v:.3f}", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    p = FIG / "F5_reliability_ratio_base_vs_weighted.png"
    fig.savefig(p); plt.close(fig)
    _saved(p, 2)


def fig6_siting_map(df: pd.DataFrame, geom: gpd.GeoDataFrame) -> None:
    from matplotlib.patches import Patch, Rectangle
    from matplotlib.lines import Line2D
    g = geom.merge(df[["geoid", "is_dac"]], on="geoid", how="left")
    g_dac = g[g.is_dac == True]          # noqa: E712
    g_nd = g[g.is_dac != True]           # noqa: E712
    sites = pd.read_csv(PROC / "greedy_dcfc_sites.csv", dtype={"geoid": str})
    sp = gpd.GeoDataFrame(sites, geometry=gpd.points_from_xy(sites.lon, sites.lat),
                          crs=WGS84).to_crs(CA_ALBERS)

    # Zoom window around the sites (padded), in EPSG:3310 meters.
    minx, miny, maxx, maxy = sp.total_bounds
    pad = 3500.0   # tight zoom so the clustered South Bay sites separate
    zx0, zy0, zx1, zy1 = minx - pad, miny - pad, maxx + pad, maxy + pad

    fig, (axC, axZ) = plt.subplots(1, 2, figsize=(13, 7),
                                   gridspec_kw={"width_ratios": [1.1, 1]})

    # --- left: county context ---
    g_nd.plot(ax=axC, color="#EDEDED", edgecolor="white", linewidth=0.1)
    g_dac.plot(ax=axC, color=OI["skyblue"], edgecolor="white", linewidth=0.1)
    g.dissolve().boundary.plot(ax=axC, color=OI["black"], linewidth=0.8)
    sp.plot(ax=axC, color=OI["vermillion"], marker="*", markersize=55,
            edgecolor="black", linewidth=0.4, zorder=5)
    axC.add_patch(Rectangle((zx0, zy0), zx1 - zx0, zy1 - zy0, fill=False,
                            edgecolor=OI["vermillion"], linewidth=1.5, zorder=6))
    axC.set_title("San Diego County context", fontsize=11)
    axC.set_axis_off()

    # --- right: zoomed South Bay ---
    g_nd.plot(ax=axZ, color="#EDEDED", edgecolor="white", linewidth=0.2)
    g_dac.plot(ax=axZ, color=OI["skyblue"], edgecolor="white", linewidth=0.2)
    g.dissolve().boundary.plot(ax=axZ, color=OI["black"], linewidth=0.8)
    sp.plot(ax=axZ, color=OI["vermillion"], marker="*", markersize=150,
            edgecolor="black", linewidth=0.5, zorder=5)
    # Rank numbers as leader-line callouts in a column down the right edge, so the
    # tightly-clustered sites stay individually legible (no overlapping on-star labels).
    order = sp.sort_values("lat", ascending=False).reset_index(drop=True)
    label_x = zx1 - (zx1 - zx0) * 0.05
    label_ys = np.linspace(zy1 - (zy1 - zy0) * 0.08, zy0 + (zy1 - zy0) * 0.08, len(order))
    for i, (_, r) in enumerate(order.iterrows()):
        axZ.annotate(
            str(int(r["rank"])), xy=(r.geometry.x, r.geometry.y),
            xytext=(label_x, label_ys[i]), ha="center", va="center",
            fontsize=10, fontweight="bold", color="black", zorder=7,
            bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec=OI["vermillion"], lw=1.3),
            arrowprops=dict(arrowstyle="-", color="#666666", lw=0.6, shrinkA=3, shrinkB=5),
        )
    axZ.set_xlim(zx0, zx1); axZ.set_ylim(zy0, zy1)
    axZ.set_title("Zoom: South Bay DAC corridor (sites 1–10 by greedy rank)", fontsize=11)
    axZ.set_axis_off()

    axZ.legend(handles=[Patch(facecolor=OI["skyblue"], label="DAC block group"),
                        Patch(facecolor="#EDEDED", label="non-DAC block group"),
                        Line2D([0], [0], marker="*", color="w", markerfacecolor=OI["vermillion"],
                               markeredgecolor="black", markersize=15, label="Greedy DCFC site")],
               loc="lower left", fontsize=9)
    fig.suptitle("Where 10 new DCFC sites most close the DAC fast-charging gap",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    p = FIG / "F6_greedy_siting_map.png"
    fig.savefig(p); plt.close(fig)
    _saved(p, len(sp))


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    df = load_joined()
    geom = load_bg_geom()
    print(f"Loaded {len(df)} block groups, {int(df.is_dac.sum())} DAC. Writing to {FIG}/ ...")
    fig1_reversal(df)
    fig2_choropleth(df, geom)
    fig3_ratios(df)
    fig4_network_mix(df, geom)
    fig5_reliability_ratio(df)
    fig6_siting_map(df, geom)
    print("All figures generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
