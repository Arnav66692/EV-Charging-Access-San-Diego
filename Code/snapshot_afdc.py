"""Daily snapshot of San Diego County AFDC station status.

Pulls the same SD County stations as pull_afdc.py (via afdc_common) and APPENDS
one row per station per run to Data/raw/afdc_snapshots.csv. Append-only: the file
is never overwritten; the header is written only when the file does not yet exist.

Intended to run once daily from cron so that AFDC station-level status_code can be
tracked over time. NOTE: status_code is a coarse, station-level availability proxy
refreshed roughly daily — it is NOT live per-port occupancy. See README.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from afdc_common import RAW_DIR, get_sandiego_stations

SNAPSHOT_CSV = RAW_DIR / "afdc_snapshots.csv"

SNAPSHOT_COLS = [
    "station_id",
    "status_code",
    "date_last_confirmed",
    "ev_dc_fast_num",
    "ev_level2_evse_num",
    "fetched_at_utc",
]


def build_snapshot(df: pd.DataFrame, fetched_at_utc: str) -> pd.DataFrame:
    """One row per station, stamped with a single run-level UTC timestamp."""
    snap = pd.DataFrame(
        {
            "station_id": df["id"],
            "status_code": df["status_code"],
            "date_last_confirmed": df["date_last_confirmed"],
            "ev_dc_fast_num": df["ev_dc_fast_num"],
            "ev_level2_evse_num": df["ev_level2_evse_num"],
            "fetched_at_utc": fetched_at_utc,
        }
    )
    return snap[SNAPSHOT_COLS]


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    fetched_at_utc = datetime.now(timezone.utc).isoformat()
    df = get_sandiego_stations()
    snap = build_snapshot(df, fetched_at_utc)

    write_header = not SNAPSHOT_CSV.exists()
    snap.to_csv(SNAPSHOT_CSV, mode="a", header=write_header, index=False)

    print(
        f"Appended {len(snap)} rows to {SNAPSHOT_CSV} "
        f"(fetched_at_utc={fetched_at_utc}, header_written={write_header})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
