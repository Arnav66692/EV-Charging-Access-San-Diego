"""Tests for load_snapshots.load_daily_snapshots deduplication logic."""

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Code"))

from load_snapshots import load_daily_snapshots  # noqa: E402

# Two captures for station 1 on the same UTC date; one capture for station 2.
FIXTURE_CSV = """\
station_id,status_code,date_last_confirmed,ev_dc_fast_num,ev_level2_evse_num,fetched_at_utc
1,E,2026-06-22,,2.0,2026-06-22T08:00:00+00:00
1,E,2026-06-22,,2.0,2026-06-22T17:13:00+00:00
2,T,2026-06-21,,1.0,2026-06-22T08:00:00+00:00
"""


@pytest.fixture()
def fixture_path(tmp_path):
    p = tmp_path / "snapshots.csv"
    p.write_text(FIXTURE_CSV)
    return p


def test_same_day_keeps_latest(fixture_path):
    df = load_daily_snapshots(fixture_path)
    s1 = df[df["station_id"] == 1]
    assert len(s1) == 1, "expected exactly one row for station 1 after dedup"
    assert pd.to_datetime(s1["fetched_at_utc"].iloc[0], utc=True) == pd.Timestamp(
        "2026-06-22T17:13:00+00:00"
    ), "expected the later timestamp to survive"


def test_distinct_stations_preserved(fixture_path):
    df = load_daily_snapshots(fixture_path)
    assert set(df["station_id"]) == {1, 2}, "both stations should be present"


def test_row_count(fixture_path):
    df = load_daily_snapshots(fixture_path)
    assert len(df) == 2, "3 raw rows → 2 after dedup (station 1 collapsed)"
