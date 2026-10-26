"""Fixtures for Garmin Connect Personal tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_API_KEY
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.garmin_connect_personal.api import (
    GarminConnectPersonalApiClient,
)
from custom_components.garmin_connect_personal.const import DOMAIN

# Tests run with time frozen at 2026-10-27 08:00 UTC, which is 01:00 on
# 2026-10-27 in Home Assistant's test time zone (US/Pacific).
NOW = "2026-10-27 08:00:00+00:00"
TODAY = date(2026, 10, 27)
YESTERDAY = date(2026, 10, 26)

USER_PROFILE_ID = 123456789
DISPLAY_NAME = "0f5e2a1c-7b3d-4e8a-9c6f-2d4b8a1e3f70"

# Asleep from 05:00 to 12:30 UTC on 2026-10-27.
SLEEP = {
    "calendarDate": "2026-10-27",
    "userProfilePK": USER_PROFILE_ID,
    "sleepStartTimestampGMT": 1793077200000,
    "sleepEndTimestampGMT": 1793104200000,
    "sleepScores": {"overall": {"value": 82, "qualifierKey": "GOOD"}},
    "sleepTimeSeconds": 27000,
    "deepSleepSeconds": 5400,
    "lightSleepSeconds": 14400,
    "remSleepSeconds": 7200,
    "awakeSleepSeconds": 1800,
    "awakeCount": 2,
    "avgHeartRate": 52.3,
    "averageRespirationValue": 14.1,
    "avgSleepStress": 12.5,
}

SUMMARY = {
    "userProfileId": USER_PROFILE_ID,
    "displayName": DISPLAY_NAME,
    "lastSyncTimestampGMT": "2026-10-27T07:50:00.0",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration from custom_components."""


@pytest.fixture
def sleep_by_date() -> dict[date, dict[str, Any]]:
    """Sleep returned by the API, per calendar date. Missing dates are empty."""
    return {TODAY: SLEEP}


@pytest.fixture
def summary_by_date() -> dict[date, dict[str, Any]]:
    """Daily summaries returned by the API, per calendar date."""
    return {TODAY: SUMMARY}


@pytest.fixture
def mock_api(
    sleep_by_date: dict[date, dict[str, Any]],
    summary_by_date: dict[date, dict[str, Any]],
) -> Generator[tuple[AsyncMock, AsyncMock]]:
    """Replace the API calls of every client with mocks."""
    with (
        patch.object(
            GarminConnectPersonalApiClient,
            "async_get_daily_sleep",
            AsyncMock(side_effect=lambda day: sleep_by_date.get(day, {})),
        ) as get_sleep,
        patch.object(
            GarminConnectPersonalApiClient,
            "async_get_daily_summary",
            AsyncMock(side_effect=lambda day: summary_by_date.get(day, {})),
        ) as get_summary,
    ):
        yield get_sleep, get_summary


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for one person."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Julius",
        unique_id=str(USER_PROFILE_ID),
        data={CONF_API_KEY: "api-key"},
    )
