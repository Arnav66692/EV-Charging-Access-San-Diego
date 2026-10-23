# EV Charging Access — San Diego County

Analysis of public electric-vehicle charging access in San Diego County (FIPS
06073), built on the AFDC Alternative Fuel Stations dataset.

[![CI](https://github.com/Arnav66692/EV-Charging-Access-San-Diego/actions/workflows/ci.yml/badge.svg)](https://github.com/Arnav66692/EV-Charging-Access-San-Diego/actions/workflows/ci.yml)

**Finding:** the population-weighted median DC fast-charging access ratio for
disadvantaged versus non-disadvantaged communities is **0.6845** across 2,058
block groups. Being closer to a charger does not guarantee better access once
competing population is counted. This is a descriptive result, not a causal estimate.

![Distance and accessibility tell different stories](Figures/F1_reversal_distance_vs_access.png)

Read the [paper (PDF)](Paper/main.pdf), [Markdown paper](Paper/main.md), or
[results](Paper/results_section.md). The DAC OLS coefficient is −0.467 with
R² = 0.0352; after spatial-error adjustment its p-value is approximately 0.17.
The spatial adjustment weakens the inference and remains part of the result.

## Quick verification

The original environment used Python 3.9.6. CI uses Python 3.11 with the same
pinned analysis dependencies. From the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python Code/pull_tiger.py
.venv/bin/python Code/analysis/joint_ols_spatial.py
```

Unit tests and the frozen-table headline check need no keys or network. The
spatial regression downloads Census geometry (about 55 MB); it uses the two
committed CSVs, so do **not** pull new AFDC data just to check the published result.
CI runs both the offline tests and the full seven-assertion spatial regression.

The six paper figures are restored from the committed PDF; see their
[provenance](Figures/README.md). Full regeneration of figures, reliability
sensitivities, and siting results requires raw/intermediate inputs not all
included in the checkout. A live data refresh is a new analysis snapshot.

MIT covers the code. Data retains its source terms and attribution; see
[DATA_SOURCES.md](DATA_SOURCES.md). Candidate centroids are hypothetical
screening locations, not verified buildable parcels.

## Pipeline

- `Code/afdc_common.py` — shared AFDC API fetch + San Diego County point-in-polygon clip.
- `Code/pull_afdc.py` — one-shot pull of the current station snapshot to
  `Data/raw/afdc_stations_sandiego.csv`.
- `Code/snapshot_afdc.py` — append-only status snapshot to
  `Data/raw/afdc_snapshots.csv` (run manually; cron and launchd were removed due to
  macOS sleep and TCC Desktop-access issues).
- `Code/timeutils.py` — DST-aware local→UTC conversion; tested in `tests/`.
- `Code/pull_acs.py` — ACS 5-year block-group data (B25003/B25024/B19013/B08303/B25044)
  for SD County to `Data/raw/acs_blockgroups_sandiego.csv`. Requires `CENSUS_API_KEY` in `.env`.
- `Code/pull_calenviroscreen.py` — CalEnviroScreen 4.0 tract data for SD County to
  `Data/raw/calenviroscreen_sandiego.csv`. No API key required (ArcGIS public service).
- `Code/pull_tiger.py` — downloads the TIGER/Line 2024 block-group geometry
  (`Data/raw/tl_2024_06_bg.zip`) and the 2020→2010 tract relationship file
  (`Data/raw/tab20_tract20_tract10_st06.txt`). No API key required (Census static files).
- `Code/features/build_access_features.py` — builds `Data/processed/blockgroup_access.csv`
  (Table B): per-block-group charger counts/ports, ACS tenure/housing/income, and CES DAC status.
- `Code/features/build_access_g2sfca.py` — builds `Data/processed/blockgroup_g2sfca.csv`:
  G2SFCA `access_dcfc` / `access_l2` / `access_combined`. Reads `blockgroup_access.csv`.

## Reproduce

The two processed CSVs that the committed regression needs are tracked in git
(`Data/processed/blockgroup_access.csv` and `Data/processed/blockgroup_g2sfca.csv`,
~576 KB total), so `Code/analysis/joint_ols_spatial.py` runs against the OLS inputs
without regenerating anything. The spatial-error step in that script additionally needs
the TIGER block-group geometry (`Data/raw/tl_2024_06_bg.zip`), which is too large to
commit — fetch it with `pull_tiger.py` (step 4). Steps below regenerate the full pipeline
from raw. All commands run from the repo root.

0. Set up the environment and API keys:

   ```
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

   Create a `.env` file at the repo root with:

   ```
   NREL_API_KEY=...      # free key: https://api.data.gov/signup/  (AFDC stations API)
   CENSUS_API_KEY=...    # free key: https://api.census.gov/data/key_signup.html
   ```

   CalEnviroScreen and the TIGER downloads need no key.

1. Pull charging stations (needs `NREL_API_KEY`):

   ```
   .venv/bin/python Code/pull_afdc.py            # -> Data/raw/afdc_stations_sandiego.csv
   ```

2. Pull ACS block-group demographics (needs `CENSUS_API_KEY`):

   ```
   .venv/bin/python Code/pull_acs.py             # -> Data/raw/acs_blockgroups_sandiego.csv
   ```

3. Pull CalEnviroScreen 4.0 (no key):

   ```
   .venv/bin/python Code/pull_calenviroscreen.py # -> Data/raw/calenviroscreen_sandiego.csv
   ```

4. Download TIGER geometry + tract relationship file (no key):

   ```
   .venv/bin/python Code/pull_tiger.py           # -> Data/raw/tl_2024_06_bg.zip + tab20_*.txt
   ```

5. Build the equity feature table (Table B):

   ```
   .venv/bin/python Code/features/build_access_features.py   # -> Data/processed/blockgroup_access.csv
   ```

6. Build the G2SFCA accessibility surface (reads `blockgroup_access.csv` from step 5):

   ```
   .venv/bin/python Code/features/build_access_g2sfca.py     # -> Data/processed/blockgroup_g2sfca.csv
   ```

7. Run the analyses against the processed CSVs:

   ```
   .venv/bin/python Code/analysis/equity_contrasts.py        # cross-axis equity contrasts
   .venv/bin/python Code/analysis/joint_ols_spatial.py       # joint OLS + spatial-error model
   ```

Steps 1–4 hit live Census and AFDC endpoints. The AFDC station inventory changes over time,
so a fresh pull will not be byte-identical to the snapshot behind the committed CSVs. To
reproduce the committed regression exactly, skip steps 1–3 and 5–6 and use the committed CSVs
directly; run step 4 only if you need the spatial-error half of `joint_ols_spatial.py`.

## Data provenance

Snapshot cadence is manual and irregular, not a fixed daily schedule, so derived
availability metrics should not assume uniform daily sampling.

**Source.** Stations come from the AFDC (Alternative Fuels Data Center) Alternative
Fuel Stations API, served from `developer.nlr.gov` (federal infrastructure via
api.data.gov; the legacy `developer.nrel.gov` host was retired 2026-05-29). The
California result (`fuel_type=ELEC`, `access=public`, `limit=all`) is clipped to San
Diego County by point-in-polygon against the U.S. Census TIGER/Line 2024 county
boundary (GEOID 06073), CRS EPSG:4326.

**Spatial reference.** TIGER counties are reprojected to EPSG:4326 before the join;
stations are matched with the `within` predicate.

`status_code` is a proxy, not measured uptime. AFDC `status_code`
(`E` = available, `P` = planned, `T` = temporarily unavailable) is a station-level
operational status refreshed roughly daily. It is not live per-port occupancy and
does not reflect real-time session availability or measured station uptime. Any
availability metric derived from the daily snapshots (`Data/raw/afdc_snapshots.csv`)
is a coarse proxy, not a direct measurement of charging-session reliability.

The accessibility analysis uses only operational stations (`status_code == "E"`):
1,607 of the 1,648 clipped public stations, and 212 of the 225 DCFC stations
(1,345 DCFC ports). Planned (`P`) and temporarily-unavailable (`T`) stations are
excluded at the station-loader level, which is the committed default across the
build and figure pipeline.

**ACS 5-year estimates (2023).** Block-group data sourced from the U.S. Census Bureau
American Community Survey 5-year estimates via `https://api.census.gov/data/2023/acs5`.
Tables: B25003 (tenure), B25024 (units in structure), B19013 (median household income),
B08303 (travel time to work), B25044 (vehicles available). GEOID is 12-digit
(state+county+tract+block group). Suppressed cells (Census sentinel −666666666 and −1)
are replaced with NaN. **Status: verified field; estimates, not counts.**

**Median income suppression — 89 / 2,058 block groups (4.3%) have `median_hhi` = NaN.**
The Census suppresses B19013 at block-group level (returning −666666666) for small-sample
geographies: military installations, group-quarters-dominated tracts, and very low
housing-unit-count block groups. These block groups are imputed from the parent tract median income
at the block-group / tract join step rather than excluded. Exclusion would drop
their population, renter households, and multifamily housing from the access and equity
analysis, biasing results by systematically removing military, group-quarters, and
low-density block groups. Imputed rows will carry an `income_imputed = True` boolean so
they can be: (1) included in station-access and charger-density metrics, (2) excluded
from any direct income-level claim, and (3) tested in a sensitivity check
(with-imputation vs. complete-cases-only). Imputation happens at the join step; the raw
`acs_blockgroups_sandiego.csv` is left unchanged.

**CalEnviroScreen 4.0 (October 2021 final release).** Published by the California Office of
Environmental Health Hazard Assessment (OEHHA). Accessed via ArcGIS Online public
FeatureServer (item ID `b6e0a01c423b489f8d98af641445da28`); no API key required.
Version: CalEnviroScreen 4.0, October 2021 final release. Columns kept: `geoid` (11-digit tract),
`ces_score`, `ces_pctile` (0–100 percentile), `is_dac`.

`is_dac` is a proxy for the SB 535 Disadvantaged Community designation.
`is_dac = True` when `ces_pctile >= 75` (top-quartile tracts). CARB's official SB 535
DAC list may additionally include low-income adjacent tracts not captured here. This
field is a first-order equity proxy only and is not a regulatory determination.

**CES tract-vintage gap — resolved by 2010→2020 crosswalk (coverage 76% → 100%).**
CalEnviroScreen 4.0 is built on **2010** census tracts (627 in SD County), while the
ACS 2023 5-year data and TIGER 2024 geometry use **2020** census tracts (737 in SD
County). Only 535 tract GEOIDs match directly, so a direct join leaves 489 of 2,058
block groups (24%) without a DAC flag. We checked for a 2020-tract CES first: the only
one is **Draft CalEnviroScreen 5.0**, a public-comment draft not suitable as an equity
spine. So we crosswalk the stable CES 4.0 onto 2020 tracts using the Census 2020↔2010
tract relationship file (`tab20_tract20_tract10_st06.txt`): each 2020 tract's
`ces_pctile` is the **land-area-weighted** (`AREALAND_PART`) average of the CES
percentiles of the 2010 tracts it overlaps (a 1:1 renumber carries the single parent
score; splits/merges blend by overlap area). `is_dac` is recomputed from the
crosswalked percentile at the ≥75 threshold. This lifts `is_dac` coverage to
**2,057 / 2,058 (100.0%)**; 491 BGs carry crosswalked values, 1 BG remains NaN (a 2020
tract overlapping no CES-scored 2010 tract). A `ces_crosswalked` boolean flags every
crosswalked value so directly-matched vs. crosswalked DAC values can be separated in a
sensitivity check. **Caveat:** crosswalked percentiles are area-weighted approximations,
not OEHHA-published values — treat `ces_crosswalked = True` rows as estimated.

## Processed outputs

**`Data/processed/blockgroup_access.csv` (Table B)** — built by
`Code/features/build_access_features.py`. One row per SD County block group (2,058),
12-digit string GEOID. Stations are point-in-polygon joined (within) to TIGER 2024
block groups (0 fell outside); per-BG charger counts, L2/DCFC port totals,
`charger_ports_per_1000` (guarded against zero/null population from B01003), ACS-derived
`renter_percent` / `multifamily_housing_percent` / `vehicle_ownership_proxy` (share of
households with ≥1 vehicle, B25044), tract-imputed `median_hhi` with `income_imputed`
flag, and CES `is_dac` / `ces_pctile` with a `ces_crosswalked` provenance flag.
**Note:** top BGs by `charger_ports_per_1000` are low-population commercial/workplace
areas (denominator artifact), not high residential access — interpret per-capita density
alongside absolute `charger_ports_total`. The output CSV is reproducible from raw + code
and is one of the two committed processed tables. Other generated tables are ignored.

**`Data/processed/blockgroup_g2sfca.csv`** — built by
`Code/features/build_access_g2sfca.py`. Gaussian two-step floating catchment area
(G2SFCA; Luo & Wang 2003, Dai 2010) accessibility per block group: `access_dcfc`
(DCFC ports, d0=6 mi), `access_l2` (L2 ports, d0=2 mi), and `access_combined`
(`access_l2*4 + access_dcfc*48`, the L2:DCFC sessions/day/port service ratio). Unit-tested
in `tests/test_g2sfca.py`. **Limitation:** G2SFCA uses block-group centroids and Euclidean
(straight-line) distance in EPSG:3310; population-weighted centroids and network/drive-time
distance are noted refinements. **Caveat:** low-density rural BGs can be overstated
(few residents competing per charger) — disclose this when ranking "best-served" areas.

**`Data/processed/blockgroup_g2sfca_reliability.csv` — reliability-weighted G2SFCA.**
Built by `Code/features/build_access_g2sfca_reliability.py`. Discounts each
station's supply by an expected session-success rate before the two-step ratio, then
recomputes access with the same Gaussian decay and catchments: `access_dcfc_rel`,
`access_l2_rel`, `access_combined_rel`. Published EV-accessibility studies assume 100%
uptime; this weights access by reliability. It is reported as an illustrative
sensitivity, not the study's main finding.

Main result: disadvantaged communities have less DCFC access, and the access they do
have comes disproportionately from lower-reliability networks, so reliability-aware
accessibility widens the equity gap. The effect is consistent in direction and robust
to the assumed spread, though modest in magnitude and limited by assumed (not measured)
uptime priors.

Limitations:
1. Assumed rates. Every reliability rate is an assumed national network average (J.D.
   Power 2025 EVX): Tesla/Tesla Destination 0.95, ChargePoint 0.85,
   Electrify America 0.80, EVgo 0.75, Blink 0.70, Shell Recharge 0.70, else/non-networked/
   unknown 0.75. These are not measured and not San Diego specific. Measured CEC AB 2061
   station-level uptime publishes in 2027; this framework is built to ingest it when it does.
2. Small effect. The DAC DCFC ratio moves from 0.6845 to 0.6533. The raw 33-vs-1,312 DCFC
   port disparity (DAC vs non-DAC areas) is the dominant equity story; reliability weighting
   only sharpens it at the margin, so its magnitude should not be overstated.
3. Fragile mechanism. The DAC DCFC mechanism rests on only 33 DCFC ports in DAC block
   groups, so it is fragile to a handful of stations.
4. Robust direction. Compressing the assumed spread to 0.85–0.95 still widens the gap, so
   the direction (not the size) is the defensible result.

**`Data/processed/greedy_dcfc_sites.csv` — greedy DCFC siting (Week 6).** Built by
`Code/optimization/greedy_dcfc_siting.py`. Scoped greedy: repeatedly adds the one
hypothetical DCFC location that most raises disadvantaged-community fast-charging access.
**Candidate simplification:** candidates are existing block-group centroids (every BG is a
potential site). This asks "if we added a DCFC-serving location at this BG's centroid, how
much would the DAC gap fall," NOT "this parcel is buildable." The rural overstatement tail
(lon > −116.85, top-decile access) is excluded from candidates. New-site supply is ASSUMED
(4 ports × 0.80 reliability = 3.2 effective). No budget or cost model yet.

**Objective:** population-weighted **MEAN** of DAC `access_dcfc_rel`. The mean is additive
over sites, so greedy gives monotonic diminishing returns and the standard greedy bound. The
population-weighted **median** is *reported as an outcome, not optimized*.

Result: the ten sites close the DAC/non-DAC fast-charging access ratio from 0.6533 to 0.901
on the reported median (about 72 percent of the gap to parity) and from 0.6420 to 0.803 on
the mean objective (about 45 percent); DAC mean access +27.0 percent, DAC median +38.5
percent, non-DAC mean +1.5 percent. Excluding the three non-buildable Coronado bayfront
centroids, the seven in-corridor centroids form a hypothetical siting scenario, closing 31.0 percent of
the gap on the mean and 48.4 percent on the median. All ten sites cluster in the South Bay
corridor (National City, Coronado, and the City of San Diego), each within 6 miles of 93–122
DAC block groups. Reliability priors remain assumed (see above); there is no
dispersion/budget constraint yet, so sites concentrate in the single worst-served corridor.

**AFDC network real-time status.** The AFDC electric-networks endpoint
(`/api/alt-fuel-stations/v1/electric-networks.json`) currently returns only `key`,
`name`, `name_fr` per network. The `real_time_status_api` field is not present in the
current API response (checked 2026-06-22).
