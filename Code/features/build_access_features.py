"""Build Table B: block-group EV charger access features for San Diego County.

Joins AFDC stations (point-in-polygon) to ACS block groups, merges CalEnviroScreen
(by parent tract), imputes suppressed median income from the parent tract, and
computes charger ports per 1,000 residents.

Run with no flag to print the QA summary only (no file written).
Run with --write to persist Data/processed/blockgroup_access.csv after QA review.

Income imputation decision (recorded 2026-06-22): suppressed block-group median_hhi
(Census sentinel -666666666 -> NaN) is filled from the parent tract median income and
flagged with income_imputed; rows are NOT dropped. See README provenance.
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import geopandas as gpd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "Data" / "raw"
PROCESSED_DIR = ROOT / "Data" / "processed"

STATIONS_CSV = RAW_DIR / "afdc_stations_sandiego.csv"
ACS_CSV = RAW_DIR / "acs_blockgroups_sandiego.csv"
CES_CSV = RAW_DIR / "calenviroscreen_sandiego.csv"
BG_ZIP = RAW_DIR / "tl_2024_06_bg.zip"
OUTPUT_CSV = PROCESSED_DIR / "blockgroup_access.csv"

BG_SHP_URL = "https://www2.census.gov/geo/tiger/TIGER2024/BG/tl_2024_06_bg.zip"
CENSUS_BASE = "https://api.census.gov/data/2023/acs/acs5"
WGS84 = "EPSG:4326"
SD_COUNTY_FP = "073"
SD_STATE_FP = "06"

CENSUS_SENTINELS = [-666666666, -1]

DAC_THRESHOLD = 75.0  # CES percentile >= 75 => SB 535 Disadvantaged Community proxy

# Census 2020<->2010 tract relationship file (CA), for crosswalking CES 4.0
# (2010 tracts) onto the ACS/TIGER 2020 tract geography. AREALAND_PART gives the
# land-area overlap between each 2020/2010 tract pair, used for area weighting.
TRACT_REL_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/"
    "tab20_tract20_tract10_st06.txt"
)
TRACT_REL_TXT = RAW_DIR / "tab20_tract20_tract10_st06.txt"

# Final Table B column order.
TABLE_B_COLS = [
    "geoid",
    "NAME",
    "tract_geoid",
    "population",
    "existing_chargers_count",
    "fast_chargers_count",
    "l2_ports_total",
    "dcfc_ports_total",
    "charger_ports_total",
    "charger_ports_per_1000",
    "renter_percent",
    "multifamily_housing_percent",
    "median_hhi",
    "income_imputed",
    "vehicle_ownership_proxy",
    "is_dac",
    "ces_pctile",
    "ces_crosswalked",
]


# --------------------------------------------------------------------------- #
# STEP 1 — load with GEOID safety
# --------------------------------------------------------------------------- #

# Operational-only default; mirrors build_access_g2sfca.OPERATIONAL_STATUS so a clean
# clone's build -> figures pipeline counts only in-service (status_code == "E") stations
# (planned "P" and temporarily-unavailable "T" excluded). Set to None for all statuses.
OPERATIONAL_STATUS = "E"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stations = pd.read_csv(STATIONS_CSV)
    if OPERATIONAL_STATUS is not None:
        stations = stations[stations["status_code"] == OPERATIONAL_STATUS].copy()
    acs = pd.read_csv(ACS_CSV, dtype={"geoid": str})
    ces = pd.read_csv(CES_CSV, dtype={"geoid": str})

    # GEOID safety: California is FIPS 06 — a lost leading zero shortens the string.
    bad_bg = acs.loc[acs["geoid"].str.len() != 12, "geoid"]
    if not bad_bg.empty:
        raise ValueError(
            f"ACS block-group GEOIDs must be 12 chars; found {len(bad_bg)} bad "
            f"(e.g. {bad_bg.iloc[0]!r}). Did the leading zero get dropped?"
        )
    bad_tr = ces.loc[ces["geoid"].str.len() != 11, "geoid"]
    if not bad_tr.empty:
        raise ValueError(
            f"CES tract GEOIDs must be 11 chars; found {len(bad_tr)} bad "
            f"(e.g. {bad_tr.iloc[0]!r})."
        )
    print(f"[step1] GEOID safety OK: ACS BG=12 chars ({len(acs)}), "
          f"CES tract=11 chars ({len(ces)})")
    return stations, acs, ces


# --------------------------------------------------------------------------- #
# STEP 2 — block-group geometry
# --------------------------------------------------------------------------- #

def load_bg_geometry() -> gpd.GeoDataFrame:
    if not BG_ZIP.exists():
        print(f"[step2] downloading {BG_SHP_URL} ...")
        with requests.get(BG_SHP_URL, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(BG_ZIP, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
    else:
        print(f"[step2] using cached {BG_ZIP.name}")

    bg = gpd.read_file(f"zip://{BG_ZIP}")
    bg = bg[(bg["STATEFP"] == SD_STATE_FP) & (bg["COUNTYFP"] == SD_COUNTY_FP)].copy()
    bg = bg.to_crs(WGS84)
    bg = bg[["GEOID", "geometry"]].rename(columns={"GEOID": "geoid"})
    print(f"[step2] SD County block groups with geometry: {len(bg)}")
    return bg


# --------------------------------------------------------------------------- #
# STEP 3 — spatial join + aggregate
# --------------------------------------------------------------------------- #

def aggregate_stations(stations: pd.DataFrame, bg: gpd.GeoDataFrame) -> pd.DataFrame:
    s = stations.copy()
    n0 = len(s)
    s = s.dropna(subset=["latitude", "longitude"])
    if len(s) < n0:
        print(f"[step3] dropped {n0 - len(s)} stations with missing lat/long")

    s["ev_level2_evse_num"] = pd.to_numeric(s["ev_level2_evse_num"], errors="coerce").fillna(0)
    s["ev_dc_fast_num"] = pd.to_numeric(s["ev_dc_fast_num"], errors="coerce").fillna(0)

    pts = gpd.GeoDataFrame(
        s, geometry=gpd.points_from_xy(s["longitude"], s["latitude"]), crs=WGS84
    )
    joined = gpd.sjoin(pts, bg, predicate="within", how="left")

    outside = joined["geoid"].isna().sum()
    print(f"[step3] stations outside all block groups (excluded): {outside}")
    joined = joined.dropna(subset=["geoid"])

    # Warn if any landed in a BG geoid not present in the ACS spine (would be lost).
    joined["is_fast"] = joined["ev_dc_fast_num"] >= 1

    agg = joined.groupby("geoid").agg(
        existing_chargers_count=("geoid", "size"),
        fast_chargers_count=("is_fast", "sum"),
        l2_ports_total=("ev_level2_evse_num", "sum"),
        dcfc_ports_total=("ev_dc_fast_num", "sum"),
    ).reset_index()
    agg["charger_ports_total"] = agg["l2_ports_total"] + agg["dcfc_ports_total"]

    # Modal station city per BG (QA labelling only).
    city = (
        joined.dropna(subset=["city"])
        .groupby("geoid")["city"]
        .agg(lambda c: c.mode().iloc[0] if not c.mode().empty else None)
        .rename("station_city")
        .reset_index()
    )
    agg = agg.merge(city, on="geoid", how="left")
    print(f"[step3] block groups receiving >=1 station: {len(agg)}, "
          f"stations assigned: {int(agg['existing_chargers_count'].sum())}")
    return agg


# --------------------------------------------------------------------------- #
# STEP 0/4/5 — ACS-derived features + Census pulls
# --------------------------------------------------------------------------- #

def census_get(api_key: str, variables: list[str], geo_for: str, geo_in: str) -> pd.DataFrame:
    params = {"get": ",".join(variables), "for": geo_for, "in": geo_in, "key": api_key}
    resp = requests.get(CENSUS_BASE, params=params, timeout=120)
    resp.raise_for_status()
    header, *rows = resp.json()
    return pd.DataFrame(rows, columns=header)


def get_bg_population(api_key: str) -> pd.DataFrame:
    df = census_get(api_key, ["B01003_001E"], "block group:*",
                    f"state:{SD_STATE_FP} county:{SD_COUNTY_FP} tract:*")
    df["geoid"] = (df["state"].str.zfill(2) + df["county"].str.zfill(3)
                   + df["tract"].str.zfill(6) + df["block group"].str.zfill(1))
    df["population"] = pd.to_numeric(df["B01003_001E"], errors="coerce")
    df["population"] = df["population"].replace(CENSUS_SENTINELS, pd.NA)
    print(f"[step0] pulled block-group population (B01003): {len(df)} rows")
    return df[["geoid", "population"]]


def get_tract_income(api_key: str) -> pd.DataFrame:
    df = census_get(api_key, ["B19013_001E"], "tract:*",
                    f"state:{SD_STATE_FP} county:{SD_COUNTY_FP}")
    df["tract_geoid"] = (df["state"].str.zfill(2) + df["county"].str.zfill(3)
                         + df["tract"].str.zfill(6))
    df["tract_median_hhi"] = pd.to_numeric(df["B19013_001E"], errors="coerce")
    df["tract_median_hhi"] = df["tract_median_hhi"].replace(CENSUS_SENTINELS, float("nan"))
    print(f"[step5] pulled tract-level median income (B19013): {len(df)} tracts")
    return df[["tract_geoid", "tract_median_hhi"]]


def load_tract_crosswalk() -> pd.DataFrame:
    """Census 2020<->2010 tract overlaps for SD County, with land-area weight."""
    if not TRACT_REL_TXT.exists():
        print(f"[step1b] downloading tract relationship file -> {TRACT_REL_TXT.name}")
        with requests.get(TRACT_REL_URL, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(TRACT_REL_TXT, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
    else:
        print(f"[step1b] using cached {TRACT_REL_TXT.name}")

    rel = pd.read_csv(
        TRACT_REL_TXT, sep="|",
        dtype={"GEOID_TRACT_20": str, "GEOID_TRACT_10": str},
    )
    rel = rel[rel["GEOID_TRACT_20"].str.startswith(SD_STATE_FP + SD_COUNTY_FP)].copy()
    rel["AREALAND_PART"] = pd.to_numeric(rel["AREALAND_PART"], errors="coerce").fillna(0)
    return rel[["GEOID_TRACT_20", "GEOID_TRACT_10", "AREALAND_PART"]]


def crosswalk_ces_pctile(rel: pd.DataFrame, ces: pd.DataFrame) -> pd.Series:
    """Area-weighted CES percentile for each 2020 tract from overlapping 2010 tracts.

    For a 2020 tract, average the CES 4.0 (2010-tract) percentiles of every 2010
    tract it overlaps, weighted by AREALAND_PART (land-area overlap). A 1:1 renumber
    reduces to carrying the single parent score; splits/merges blend by overlap area.
    2010 tracts with no CES score are excluded from both numerator and denominator.
    Returns a Series indexed by 2020 tract GEOID.
    """
    ces_pctile = ces.dropna(subset=["ces_pctile"]).set_index("geoid")["ces_pctile"]
    r = rel.merge(
        ces_pctile.rename("p10"), left_on="GEOID_TRACT_10", right_index=True, how="inner"
    )
    r = r[r["AREALAND_PART"] > 0].copy()
    r["wp"] = r["AREALAND_PART"] * r["p10"]
    g = r.groupby("GEOID_TRACT_20").agg(num=("wp", "sum"), den=("AREALAND_PART", "sum"))
    return (g["num"] / g["den"]).rename("xwalk_pctile")


def derive_acs_features(acs: pd.DataFrame) -> pd.DataFrame:
    df = acs.copy()

    df["renter_percent"] = (df["tenure_renter"] / df["tenure_total"]).where(
        df["tenure_total"] > 0) * 100

    mf = df["units_5_9"] + df["units_10_19"] + df["units_20_49"] + df["units_50plus"]
    df["multifamily_housing_percent"] = (mf / df["units_struct_total"]).where(
        df["units_struct_total"] > 0) * 100

    no_veh = df["veh_owner_none"] + df["veh_renter_none"]
    df["vehicle_ownership_proxy"] = (1 - no_veh / df["veh_total"]).where(
        df["veh_total"] > 0)

    df["tract_geoid"] = df["geoid"].str[:11]
    keep = ["geoid", "NAME", "tract_geoid", "median_hhi", "renter_percent",
            "multifamily_housing_percent", "vehicle_ownership_proxy"]
    return df[keep]


# --------------------------------------------------------------------------- #
# Assemble
# --------------------------------------------------------------------------- #

def build_table_b(api_key: str) -> tuple[pd.DataFrame, dict]:
    stations, acs, ces = load_inputs()
    bg_geom = load_bg_geometry()
    station_agg = aggregate_stations(stations, bg_geom)

    feat = derive_acs_features(acs)             # spine = 2,058 ACS block groups

    # Station geoids missing from the ACS spine would be lost on merge — report.
    lost = set(station_agg["geoid"]) - set(feat["geoid"])
    lost_stations = int(station_agg.loc[station_agg["geoid"].isin(lost),
                                        "existing_chargers_count"].sum()) if lost else 0

    df = feat.merge(
        station_agg.drop(columns=["station_city"]), on="geoid", how="left"
    )
    df = df.merge(station_agg[["geoid", "station_city"]], on="geoid", how="left")

    # Block groups with no stations -> zero counts.
    count_cols = ["existing_chargers_count", "fast_chargers_count",
                  "l2_ports_total", "dcfc_ports_total", "charger_ports_total"]
    df[count_cols] = df[count_cols].fillna(0)

    # STEP 4 — CalEnviroScreen by parent tract (direct 2020==2010 GEOID match).
    df = df.merge(
        ces[["geoid", "is_dac", "ces_pctile"]].rename(columns={"geoid": "tract_geoid"}),
        on="tract_geoid", how="left",
    )
    df["ces_crosswalked"] = False
    dac_cov_before = int(df["is_dac"].notna().sum())

    # FIX 1 — crosswalk CES 4.0 (2010 tracts) onto unmatched 2020 tracts via the
    # Census relationship file (area-weighted). Draft CES 5.0 is on 2020 tracts but
    # is a public-comment draft, so we crosswalk the stable 4.0 instead.
    rel = load_tract_crosswalk()
    xwalk = crosswalk_ces_pctile(rel, ces)
    needs = df["ces_pctile"].isna()
    filled = df.loc[needs, "tract_geoid"].map(xwalk)
    df.loc[needs, "ces_pctile"] = filled
    newly = needs & df["ces_pctile"].notna()
    df.loc[newly, "ces_crosswalked"] = True
    df.loc[newly, "is_dac"] = df.loc[newly, "ces_pctile"] >= DAC_THRESHOLD
    n_crosswalked = int(newly.sum())
    dac_cov_after = int(df["is_dac"].notna().sum())
    print(f"[step1b] DAC coverage: {dac_cov_before} -> {dac_cov_after} of {len(df)} "
          f"BGs; crosswalked {n_crosswalked}")

    # Population (B01003) + STEP 6 ports per 1,000.
    pop = get_bg_population(api_key)
    df = df.merge(pop, on="geoid", how="left")

    # STEP 5 — income imputation from parent tract.
    tract_inc = get_tract_income(api_key)
    df = df.merge(tract_inc, on="tract_geoid", how="left")
    suppressed = df["median_hhi"].isna()
    n_suppressed = int(suppressed.sum())
    df["income_imputed"] = suppressed
    df.loc[suppressed, "median_hhi"] = df.loc[suppressed, "tract_median_hhi"]
    n_still_null = int(df["median_hhi"].isna().sum())
    df = df.drop(columns=["tract_median_hhi"])

    # STEP 6 — ports per 1,000 (guard zero/null population).
    pop_num = pd.to_numeric(df["population"], errors="coerce")
    df["charger_ports_per_1000"] = (
        df["charger_ports_total"] / pop_num * 1000
    ).where(pop_num > 0)
    df["population"] = pop_num

    stats = {
        "rows": len(df),
        "zero_charger_bgs": int((df["charger_ports_total"] == 0).sum()),
        "imputed_attempted": n_suppressed,
        "imputed_remaining_null": n_still_null,
        "stations_assigned": int(df["existing_chargers_count"].sum()),
        "lost_to_spine": lost_stations,
        "dac_cov_before": dac_cov_before,
        "dac_cov_after": dac_cov_after,
        "dac_crosswalked": n_crosswalked,
        "dac_still_null": int(df["is_dac"].isna().sum()),
    }
    return df, stats


# --------------------------------------------------------------------------- #
# STEP 7 — QA
# --------------------------------------------------------------------------- #

def qa_report(df: pd.DataFrame, stats: dict) -> None:
    print("\n" + "=" * 66)
    print("QA SUMMARY — Table B (blockgroup_access)")
    print("=" * 66)
    print(f"Row count (block groups):        {stats['rows']}  (expect ~2,058)")
    print(f"Block groups with zero chargers: {stats['zero_charger_bgs']}")
    print(f"Stations assigned to a BG:        {stats['stations_assigned']}")
    if stats["lost_to_spine"]:
        print(f"!! stations in a BG not in ACS spine (LOST): {stats['lost_to_spine']}")
    print(f"Income imputed (suppressed BGs): {stats['imputed_attempted']}  (expect 89)")
    print(f"  still NaN after imputation:    {stats['imputed_remaining_null']} "
          f"(parent tract also suppressed)")

    rows = stats["rows"]
    print(f"\nDAC coverage (is_dac non-null):")
    print(f"  before crosswalk: {stats['dac_cov_before']} / {rows} "
          f"({100*stats['dac_cov_before']/rows:.1f}%)")
    print(f"  after  crosswalk: {stats['dac_cov_after']} / {rows} "
          f"({100*stats['dac_cov_after']/rows:.1f}%)")
    print(f"  crosswalked BGs:  {stats['dac_crosswalked']}")
    print(f"  still NaN is_dac: {stats['dac_still_null']}")

    print("\nNull counts per column:")
    nulls = df[TABLE_B_COLS].isnull().sum()
    width = max(len(c) for c in TABLE_B_COLS)
    for col, n in nulls.items():
        print(f"  {col:<{width}}  {n:5d} ({100*n/len(df):.1f}%)")

    show = ["geoid", "station_city", "population", "charger_ports_total",
            "charger_ports_per_1000"]
    have_ports = df[df["charger_ports_total"] > 0].copy()

    print(f"\nTop 5 block groups by charger_ports_per_1000:")
    top = df.sort_values("charger_ports_per_1000", ascending=False).head(5)
    print(top[show].to_string(index=False))

    print(f"\nBottom 5 by charger_ports_per_1000 AMONG BGs that have >=1 port "
          f"(plain bottom-5 are all 0.0 ties):")
    bot = have_ports.sort_values("charger_ports_per_1000", ascending=True).head(5)
    print(bot[show].to_string(index=False))

    # Sanity read: coastal/urban (west) vs east county by longitude of BG centroid.
    print("\nSanity read (urban-core density should dominate):")
    print(f"  BGs with >=1 charger port: {len(have_ports)} / {len(df)}")
    print(f"  Median ports/1000 where >0: {have_ports['charger_ports_per_1000'].median():.2f}")
    print("=" * 66)


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("CENSUS_API_KEY")
    if not api_key:
        print("ERROR: CENSUS_API_KEY not in .env", file=sys.stderr)
        return 1

    df, stats = build_table_b(api_key)
    qa_report(df, stats)

    if "--write" in sys.argv:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df[TABLE_B_COLS].to_csv(OUTPUT_CSV, index=False)
        print(f"\n[written] {len(df)} rows -> {OUTPUT_CSV}")
    else:
        print("\n[QA-only] CSV not written. Re-run with --write to persist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
