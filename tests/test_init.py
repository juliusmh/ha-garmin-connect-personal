"""Tests for setting up Garmin Connect Personal and its entities."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import CONF_API_KEY, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.garmin_connect_personal.api import (
    GarminConnectPersonalApiClientAuthenticationError,
    GarminConnectPersonalApiClientCommunicationError,
    token_cache_file,
)
from custom_components.garmin_connect_personal.const import DOMAIN, UPDATE_INTERVAL

from .conftest import NOW, SLEEP, SUMMARY, TODAY, YESTERDAY

pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("mock_api")]


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Every sensor shows the most recent sleep and the last sync."""
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    # 08:00 UTC lies within the sleep from 05:00 to 12:30 UTC.
    is_awake = hass.states.get("binary_sensor.julius_is_awake")
    assert is_awake.state == STATE_OFF
    assert is_awake.attributes["sleep_start"].isoformat() == "2026-10-27T05:00:00+00:00"
    assert is_awake.attributes["sleep_end"].isoformat() == "2026-10-27T12:30:00+00:00"

    sleep_score = hass.states.get("sensor.julius_sleep_score")
    assert sleep_score.state == "82"
    assert sleep_score.attributes["qualifier"] == "GOOD"
    assert sleep_score.attributes["calendar_date"] == TODAY

    expected = {
        "sensor.julius_sleep_duration": "7.5",
        "sensor.julius_deep_sleep": "1.5",
        "sensor.julius_light_sleep": "4.0",
        "sensor.julius_rem_sleep": "2.0",
        "sensor.julius_awake_time_during_sleep": "0.5",
        "sensor.julius_times_awake_during_sleep": "2",
        "sensor.julius_average_heart_rate_during_sleep": "52.3",
        "sensor.julius_average_respiration_during_sleep": "14.1",
        "sensor.julius_average_stress_during_sleep": "12.5",
        "sensor.julius_last_sync": "2026-10-27T07:50:00+00:00",
    }
    assert {
        entity_id: hass.states.get(entity_id).state for entity_id in expected
    } == expected


async def test_awake_after_sleep(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """is_awake turns on once the sleep has ended."""
    await _setup(hass, config_entry)
    assert hass.states.get("binary_sensor.julius_is_awake").state == STATE_OFF

    freezer.move_to("2026-10-27 13:00:00+00:00")
    async_fire_time_changed(hass)
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.julius_is_awake").state == STATE_ON


async def test_falls_back_to_yesterday(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    sleep_by_date: dict,
    summary_by_date: dict,
) -> None:
    """Until today's data has synced, yesterday's is shown."""
    sleep_by_date.clear()
    sleep_by_date[YESTERDAY] = {**SLEEP, "calendarDate": "2026-10-26"}
    summary_by_date.clear()
    summary_by_date[YESTERDAY] = SUMMARY

    await _setup(hass, config_entry)

    sleep_score = hass.states.get("sensor.julius_sleep_score")
    assert sleep_score.state == "82"
    assert sleep_score.attributes["calendar_date"] == YESTERDAY
    assert (
        hass.states.get("sensor.julius_last_sync").state == "2026-10-27T07:50:00+00:00"
    )


async def test_no_data(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    sleep_by_date: dict,
    summary_by_date: dict,
) -> None:
    """Without any synced data, the entities are unknown."""
    sleep_by_date.clear()
    summary_by_date.clear()

    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("binary_sensor.julius_is_awake").state == STATE_UNKNOWN
    assert hass.states.get("sensor.julius_sleep_score").state == STATE_UNKNOWN
    assert hass.states.get("sensor.julius_last_sync").state == STATE_UNKNOWN


async def test_rejected_api_key_starts_reauth(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_api: tuple[AsyncMock, AsyncMock],
) -> None:
    """A rejected API key asks the user for a new one."""
    get_sleep, _ = mock_api
    get_sleep.side_effect = GarminConnectPersonalApiClientAuthenticationError("401")

    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


async def test_connection_error_retries(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_api: tuple[AsyncMock, AsyncMock],
) -> None:
    """A connection error during setup is retried later."""
    get_sleep, _ = mock_api
    get_sleep.side_effect = GarminConnectPersonalApiClientCommunicationError("down")

    await _setup(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_multiple_people(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Every person gets their own device and entities."""
    second_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Anna",
        unique_id="42",
        data={CONF_API_KEY: "other-key"},
    )
    await _setup(hass, config_entry)
    await _setup(hass, second_entry)

    for entry in (config_entry, second_entry):
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        assert [device.name for device in devices] == [entry.title]
    assert hass.states.get("sensor.julius_sleep_score") is not None
    assert hass.states.get("sensor.anna_sleep_score") is not None


async def test_unload(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """The entry can be unloaded."""
    await _setup(hass, config_entry)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_remove_deletes_token_cache(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Removing a person deletes their cached bearer token."""
    await _setup(hass, config_entry)
    cache = token_cache_file(hass, config_entry.data[CONF_API_KEY])
    await hass.async_add_executor_job(
        lambda: (
            cache.parent.mkdir(parents=True, exist_ok=True),
            cache.write_text("{}"),
        )
    )

    await hass.config_entries.async_remove(config_entry.entry_id)

    assert not await hass.async_add_executor_job(cache.exists)
