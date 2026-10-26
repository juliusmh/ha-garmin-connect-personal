"""Custom types for garmin_connect_personal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from datetime import date, datetime

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import GarminConnectPersonalApiClient
    from .coordinator import GarminConnectPersonalDataUpdateCoordinator


type GarminConnectPersonalConfigEntry = ConfigEntry[GarminConnectPersonalData]


@dataclass
class GarminConnectPersonalData:
    """Runtime data for one person."""

    client: GarminConnectPersonalApiClient
    coordinator: GarminConnectPersonalDataUpdateCoordinator
    integration: Integration


@dataclass(frozen=True)
class PersonData:
    """Everything the coordinator fetched for one person."""

    sleep: SleepData | None
    last_sync: datetime | None


@dataclass(frozen=True)
class SleepData:
    """The most recent sleep of a person."""

    calendar_date: date | None
    sleep_start: datetime | None
    sleep_end: datetime | None
    sleep_score: int | None
    sleep_score_qualifier: str | None
    sleep_seconds: int | None
    deep_sleep_seconds: int | None
    light_sleep_seconds: int | None
    rem_sleep_seconds: int | None
    awake_seconds: int | None
    awake_count: int | None
    average_heart_rate: float | None
    average_respiration: float | None
    average_stress: float | None

    @classmethod
    def from_dto(cls, dto: dict[str, Any]) -> SleepData | None:
        """Parse a DailySleepDTO, returning None if it contains no sleep."""
        sleep_start = parse_timestamp(dto.get("sleepStartTimestampGMT"))
        if sleep_start is None:
            return None
        overall = (dto.get("sleepScores") or {}).get("overall") or {}
        calendar_date = dto.get("calendarDate")
        return cls(
            calendar_date=dt_util.parse_date(calendar_date) if calendar_date else None,
            sleep_start=sleep_start,
            sleep_end=parse_timestamp(dto.get("sleepEndTimestampGMT")),
            sleep_score=overall.get("value"),
            sleep_score_qualifier=overall.get("qualifierKey"),
            sleep_seconds=dto.get("sleepTimeSeconds"),
            deep_sleep_seconds=dto.get("deepSleepSeconds"),
            light_sleep_seconds=dto.get("lightSleepSeconds"),
            rem_sleep_seconds=dto.get("remSleepSeconds"),
            awake_seconds=dto.get("awakeSleepSeconds"),
            awake_count=dto.get("awakeCount"),
            average_heart_rate=dto.get("avgHeartRate"),
            average_respiration=dto.get("averageRespirationValue"),
            average_stress=dto.get("avgSleepStress"),
        )

    def is_asleep(self, now: datetime) -> bool:
        """Return whether `now` lies within this sleep."""
        if self.sleep_start is None or now < self.sleep_start:
            return False
        return self.sleep_end is None or now < self.sleep_end


def parse_timestamp(value: Any) -> datetime | None:
    """Parse a GMT timestamp, sent either as epoch milliseconds or ISO 8601."""
    if value is None:
        return None
    if isinstance(value, int | float) or (isinstance(value, str) and value.isdigit()):
        return dt_util.utc_from_timestamp(int(value) / 1000)
    if isinstance(value, str) and (parsed := dt_util.parse_datetime(value)):
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_util.UTC)
    return None
