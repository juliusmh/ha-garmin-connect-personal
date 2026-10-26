"""
Custom integration to integrate Garmin Connect Personal API with Home Assistant.

For more details about this integration, please refer to
https://github.com/juliusmh/ha-garmin-connect-personal
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.loader import async_get_loaded_integration

from .api import GarminConnectPersonalApiClient, token_cache_file
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL
from .coordinator import GarminConnectPersonalDataUpdateCoordinator
from .data import GarminConnectPersonalData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import GarminConnectPersonalConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConnectPersonalConfigEntry,
) -> bool:
    """Set up one person using UI."""
    client = GarminConnectPersonalApiClient.from_entry_data(hass, dict(entry.data))
    entry.async_on_unload(client.close)

    coordinator = GarminConnectPersonalDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=f"{DOMAIN}_{entry.title}",
        update_interval=UPDATE_INTERVAL,
        config_entry=entry,
    )
    entry.runtime_data = GarminConnectPersonalData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: GarminConnectPersonalConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant,
    entry: GarminConnectPersonalConfigEntry,
) -> None:
    """Delete the person's cached bearer token."""
    path = token_cache_file(hass, entry.data[CONF_API_KEY])
    await hass.async_add_executor_job(partial(path.unlink, missing_ok=True))
