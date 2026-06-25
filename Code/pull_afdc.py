"""Pull AFDC electric-vehicle charging stations for San Diego County.

Fetches public EV (ELEC) alternative-fuel stations in California from the AFDC
Alternative Fuel Stations API, clips them to San Diego County (FIPS 06073) by
point-in-polygon against the Census TIGER county boundary, writes a trimmed CSV
to Data/raw/, and prints a summary.

Fetch + clip logic lives in afdc_common.py (shared with snapshot_afdc.py).
"""

from __future__ import annotations

import sys

import pandas as pd

from afdc_common import (
    RAW_DIR,
    clip_to_san_diego,
    fetch_stations,
    get_api_key,
    load_san_diego_boundary,
)

OUTPUT_CSV = RAW_DIR / "afdc_stations_sandiego.csv"

KEEP_COLS = [
    "id",
    "station_name",
    "latitude",
    "longitude",
    "city",
    "zip",
    "ev_network",
    "ev_connector_types",
    "ev_level2_evse_num",
    "ev_dc_fast_num",
    "access_code",
    "access_days_time",
    "ev_pricing",
    "status_code",
    "date_last_confirmed",
    "updated_at",
]

STATUS_LABELS = {
    "E": "available",
    "P": "planned",
    "T": "temporarily unavailable",
}


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the requested columns; flatten list-valued connector types."""
    out = df.reindex(columns=KEEP_COLS).copy()
    out["ev_connector_types"] = out["ev_connector_types"].apply(
        lambda v: ";".join(v) if isinstance(v, list) else v
    )
    return out


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("SAN DIEGO COUNTY EV CHARGING STATIONS — SUMMARY")
    print("=" * 60)

    print(f"Total stations: {len(df)}")

    print("\nBy status_code:")
    counts = df["status_code"].value_counts(dropna=False)
    for code, n in counts.items():
        label = STATUS_LABELS.get(code, "unknown" if pd.isna(code) else "other")
        shown = code if isinstance(code, str) else "NA"
        print(f"  {shown:>3} ({label}): {n}")

    dc = pd.to_numeric(df["ev_dc_fast_num"], errors="coerce").fillna(0)
    print(f"\nStations with >=1 DC fast port: {int((dc >= 1).sum())}")

    print("\nBy ev_network:")
    net = df["ev_network"].fillna("(none)").value_counts()
    for name, n in net.items():
        print(f"  {name}: {n}")

    dates = pd.to_datetime(df["date_last_confirmed"], errors="coerce")
    fmt = lambda d: d.date().isoformat() if pd.notna(d) else "n/a"
    print(f"\ndate_last_confirmed range: {fmt(dates.min())} -> {fmt(dates.max())}")
    print("=" * 60)


def main() -> int:
    try:
        api_key = get_api_key()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_stations(api_key)
    sd = load_san_diego_boundary()
    clipped = clip_to_san_diego(df, sd)
    result = tidy(clipped)

    result.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote {len(result)} rows -> {OUTPUT_CSV}")

    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
