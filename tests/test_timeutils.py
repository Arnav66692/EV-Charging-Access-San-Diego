"""Tests for Code/timeutils.to_utc — verifies DST-aware Pacific -> UTC."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Code"))

from timeutils import to_utc  # noqa: E402


def test_summer_pacific_to_utc():
    # PDT = UTC-7 in July, so noon Pacific -> 19:00 UTC.
    local = datetime(2025, 7, 15, 12, 0)
    assert to_utc(local) == datetime(2025, 7, 15, 19, 0, tzinfo=timezone.utc)


def test_winter_pacific_to_utc():
    # PST = UTC-8 in January, so noon Pacific -> 20:00 UTC.
    local = datetime(2025, 1, 15, 12, 0)
    assert to_utc(local) == datetime(2025, 1, 15, 20, 0, tzinfo=timezone.utc)
