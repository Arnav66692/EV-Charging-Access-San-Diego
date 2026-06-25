"""Week 5 equity contrasts: G2SFCA access vs income, renter, multifamily, DAC.

QA-only analysis. Joins the G2SFCA accessibility metric to the Table B equity variables
and reports, per equity axis:
  1. median access per population-weighted quartile (or per is_dac group)
  2. disadvantaged-vs-advantaged ratio (lower = steeper access gap)
  3. population-weighted below-median EXPOSURE: share of people in the disadvantaged group
     who live in a BG with access below the population-weighted median, vs the advantaged
  4. Spearman rank correlation between access and each continuous variable

Quartiles are population-weighted, so they split PEOPLE, not block groups.

Spatial-autocorrelation caveat: census block groups are spatially autocorrelated, so
report effect SIZE as primary evidence; treat any p-value as OPTIMISTIC. A Moran's-I-aware
significance test is a noted refinement and is intentionally NOT run here.

Writes nothing. No CSV, no commit.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "Data" / "raw"
PROC = ROOT / "Data" / "processed"
G2_CSV = PROC / "blockgroup_g2sfca.csv"
ACCESS_CSV = PROC / "blockgroup_access.csv"
BG_ZIP = RAW_DIR / "tl_2024_06_bg.zip"

WGS84 = "EPSG:4326"
CA_ALBERS = "EPSG:3310"
SD_STATE = "06"
SD_CTY = "073"
RURAL_LON = -116.85          # matches build_access_g2sfca rural-tail flag

ACCESS_COLS = ["access_dcfc", "access_combined"]
# (variable, disadvantaged_side, label). low => Q1 disadvantaged; high => Q4 disadvantaged.
QUART_AXES = [
    ("median_hhi", "low", "income (Q1 low vs Q4 high)"),
    ("renter_percent", "high", "renter (Q4 high vs Q1 low)"),
    ("multifamily_housing_percent", "high", "multifamily (Q4 high vs Q1 low)"),
]
CONT_VARS = ["median_hhi", "renter_percent", "multifamily_housing_percent"]


# --------------------------------------------------------------------------- #
# Weighted helpers
# --------------------------------------------------------------------------- #

def w_quantile_breaks(v: np.ndarray, w: np.ndarray, probs=(0.25, 0.5, 0.75)) -> np.ndarray:
    o = np.argsort(v)
    v, w = v[o], w[o].astype(float)
    cdf = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp(probs, cdf, v)


def pop_quartiles(values: pd.Series, weights: pd.Series) -> pd.Series:
    """Quartile labels 1..4 by population-weighted breaks; NaN values stay NaN."""
    m = values.notna() & weights.notna()
    b = w_quantile_breaks(values[m].to_numpy(), weights[m].to_numpy())
    bins = [-np.inf, *b, np.inf]
    return pd.cut(values, bins=bins, labels=[1, 2, 3, 4], include_lowest=True)


def w_median(v: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(v)
    v, w = v[o], w[o].astype(float)
    return float(v[np.searchsorted(np.cumsum(w), 0.5 * w.sum())])


def spearman(df: pd.DataFrame, a: str, b: str) -> float:
    s = df[[a, b]].dropna()
    return float(s.corr(method="spearman").iloc[0, 1]) if len(s) >= 3 else float("nan")


def _exposure(frame: pd.DataFrame, mask: pd.Series, access_col: str, pwmed: float) -> float:
    g = frame[mask]
    tot = g["population"].sum()
    if tot == 0:
        return float("nan")
    return g.loc[g[access_col] < pwmed, "population"].sum() / tot


# --------------------------------------------------------------------------- #
# Contrast rows for one access column on one (sub)sample
# --------------------------------------------------------------------------- #

def contrast_rows(df: pd.DataFrame, access_col: str, income_src: pd.DataFrame | None = None):
    rows = []
    for var, side, name in QUART_AXES:
        src = income_src if (var == "median_hhi" and income_src is not None) else df
        q = pop_quartiles(src[var], src["population"])
        d = src.assign(_q=q).dropna(subset=["_q"])
        med = d.groupby("_q", observed=True)[access_col].median()
        dis, adv = (1, 4) if side == "low" else (4, 1)
        dmed, amed = med.get(dis, np.nan), med.get(adv, np.nan)
        ratio = dmed / amed if amed else np.nan
        pw = w_median(src[access_col].to_numpy(), src["population"].to_numpy())
        e_dis = _exposure(src, q == dis, access_col, pw)
        e_adv = _exposure(src, q == adv, access_col, pw)
        rows.append((name, dmed, amed, ratio, e_dis, e_adv))

    # DAC (binary)
    md = df.groupby("is_dac", dropna=True)[access_col].median()
    dmed, amed = md.get(True, np.nan), md.get(False, np.nan)
    ratio = dmed / amed if amed else np.nan
    pw = w_median(df[access_col].to_numpy(), df["population"].to_numpy())
    e_dis = _exposure(df, df["is_dac"] == True, access_col, pw)   # noqa: E712
    e_adv = _exposure(df, df["is_dac"] == False, access_col, pw)  # noqa: E712
    rows.append(("DAC (True vs False)", dmed, amed, ratio, e_dis, e_adv))
    return rows


def print_table(title: str, rows) -> None:
    print(f"\n{title}")
    print(f"  {'axis':34s} {'disadv':>9s} {'adv':>9s} {'ratio':>6s} {'below%dis':>9s} {'below%adv':>9s}")
    for name, dmed, amed, ratio, edis, eadv in rows:
        print(f"  {name:34s} {dmed:9.3g} {amed:9.3g} {ratio:6.2f} "
              f"{100*edis:9.1f} {100*eadv:9.1f}")


def print_corr(df: pd.DataFrame, access_col: str) -> None:
    print(f"  Spearman({access_col}, var) [effect size; p-values optimistic, not reported]:")
    for v in CONT_VARS:
        print(f"    vs {v:30s} rho = {spearman(df, access_col, v):+.3f}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def load_lon() -> pd.DataFrame:
    bg = gpd.read_file(f"zip://{BG_ZIP}")
    bg = bg[(bg["STATEFP"] == SD_STATE) & (bg["COUNTYFP"] == SD_CTY)].copy().to_crs(CA_ALBERS)
    cent = bg.geometry.centroid
    lon = gpd.GeoSeries(cent, crs=CA_ALBERS).to_crs(WGS84).x.to_numpy()
    return pd.DataFrame({"geoid": bg["GEOID"].astype(str), "lon": lon})


def main() -> int:
    g2 = pd.read_csv(G2_CSV, dtype={"geoid": str})
    acc = pd.read_csv(ACCESS_CSV, dtype={"geoid": str})
    df = acc.merge(g2, on="geoid", how="inner").merge(load_lon(), on="geoid", how="left")
    df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(0)

    print("=" * 78)
    print("WEEK 5 EQUITY CONTRASTS — G2SFCA access vs income / renter / multifamily / DAC")
    print("=" * 78)
    print(f"Block groups: {len(df)}   total population: {int(df['population'].sum()):,}")
    print(f"NaN median_hhi (excluded from income axis): {int(df['median_hhi'].isna().sum())}   "
          f"income_imputed: {int((df['income_imputed'] == True).sum())}   "  # noqa: E712
          f"ces_crosswalked: {int((df['ces_crosswalked'] == True).sum())}")  # noqa: E712

    print("\nPopulation-weighted quartile check (each Q should hold ~25% of people):")
    for var, _, name in QUART_AXES:
        q = pop_quartiles(df[var], df["population"])
        shares = df.assign(_q=q).groupby("_q", observed=True)["population"].sum()
        tot = shares.sum()
        pct = "  ".join(f"Q{int(k)}={100*v/tot:.0f}%" for k, v in shares.items())
        print(f"  {name:34s} {pct}")

    print("\n" + "-" * 78)
    print("MAIN CONTRASTS (full sample). below%dis/adv = share of that group's PEOPLE")
    print("living in a BG below the population-weighted median access. Higher = worse.")
    print("-" * 78)
    for access_col in ACCESS_COLS:
        print_table(f"[{access_col}]", contrast_rows(df, access_col))
        print_corr(df, access_col)

    # Ranking by steepest gap (lowest disadvantaged/advantaged ratio), access_dcfc.
    rows = contrast_rows(df, "access_dcfc")
    ranking = sorted(((name, r) for name, _, _, r, _, _ in rows), key=lambda t: t[1])
    print("\n" + "=" * 78)
    print("COMPARISON QUESTION — axes ranked by access_dcfc gap steepness (low ratio = sharp):")
    for i, (name, r) in enumerate(ranking, 1):
        print(f"  {i}. {name:34s} ratio = {r:.2f}")
    print(f"\n  >>> SHARPEST access_dcfc gap: {ranking[0][0]}  (ratio {ranking[0][1]:.2f}) <<<")

    # ----------------------------------------------------------------- #
    # Robustness
    # ----------------------------------------------------------------- #
    print("\n" + "=" * 78)
    print("ROBUSTNESS (access_dcfc)")
    print("=" * 78)

    # (a) directly-matched DACs only
    a = df[df["ces_crosswalked"] != True]  # noqa: E712
    print(f"\n(a) EXCLUDING ces_crosswalked=True  (n={len(a)})")
    print_table("[access_dcfc | no crosswalk]", contrast_rows(a, "access_dcfc"))

    # (b) drop rural low-density overstatement tail (lon > RURAL_LON & top-decile access_dcfc)
    p90 = df["access_dcfc"].quantile(0.90)
    tail = (df["lon"] > RURAL_LON) & (df["access_dcfc"] >= p90)
    b = df[~tail]
    print(f"\n(b) EXCLUDING rural overstatement tail  (dropped {int(tail.sum())}, n={len(b)})")
    print_table("[access_dcfc | no rural tail]", contrast_rows(b, "access_dcfc"))
    print_corr(b, "access_dcfc")

    # (c) income axis only, excluding income_imputed=True
    c_inc = df[df["income_imputed"] != True]  # noqa: E712
    print(f"\n(c) INCOME axis EXCLUDING income_imputed=True  (income n={len(c_inc)})")
    for access_col in ACCESS_COLS:
        q = pop_quartiles(c_inc["median_hhi"], c_inc["population"])
        d = c_inc.assign(_q=q).dropna(subset=["_q"])
        med = d.groupby("_q", observed=True)[access_col].median()
        ratio = med.get(1, np.nan) / med.get(4, np.nan)
        print(f"  [{access_col:16s}] income Q1/Q4 ratio = {ratio:.2f}  "
              f"(Q1={med.get(1, np.nan):.3g}  Q4={med.get(4, np.nan):.3g})")

    print("\n" + "=" * 78)
    print("[QA-only] Nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
