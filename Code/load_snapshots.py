"""Load and deduplicate the AFDC daily snapshot CSV.

The snapshot file is append-only — multiple captures per UTC day can accumulate
(manual runs, launchd kickstarts, reruns).  load_daily_snapshots() applies a
last-write-wins deduplication so callers always see one row per
(station_id, UTC date).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_CSV = ROOT / "Data" / "raw" / "afdc_snapshots.csv"


def load_daily_snapshots(path: Path | str = SNAPSHOT_CSV) -> pd.DataFrame:
    """Return deduplicated snapshot frame: one row per (station_id, UTC date).

    For each (station_id, UTC date) pair, keeps the row with the latest
    fetched_at_utc.  The raw file is never modified.
    """
    df = pd.read_csv(path)
    df["fetched_at_utc"] = pd.to_datetime(df["fetched_at_utc"], utc=True)
    df["snapshot_date"] = df["fetched_at_utc"].dt.date

    df = (
        df.sort_values("fetched_at_utc")
          .drop_duplicates(subset=["station_id", "snapshot_date"], keep="last")
          .drop(columns="snapshot_date")
          .reset_index(drop=True)
    )
    return df
