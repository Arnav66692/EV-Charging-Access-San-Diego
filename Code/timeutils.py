"""Timezone helpers for the EV charging snapshot pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def to_utc(local_dt: datetime, tz: str = "America/Los_Angeles") -> datetime:
    """Convert a local datetime to UTC.

    A naive ``local_dt`` is interpreted as wall-clock time in ``tz`` (DST-aware,
    so the offset is +7 in summer / +8 in winter for US Pacific). An already
    timezone-aware ``local_dt`` is converted directly. Returns an aware UTC
    datetime.
    """
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(tzinfo=ZoneInfo(tz))
    return local_dt.astimezone(timezone.utc)
