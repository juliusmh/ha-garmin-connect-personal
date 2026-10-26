"""DataUpdateCoordinator for garmin_connect_personal."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    GarminConnectPersonalApiClientAuthenticationError,
    GarminConnectPersonalApiClientError,
    GarminConnectPersonalApiClientRateLimitError,
)
from .data import PersonData, SleepData, parse_timestamp

if TYPE_CHECKING:
    from datetime import date, datetime

    from .api import GarminConnectPersonalApiClient
    from .data import GarminConnectPersonalConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class GarminConnectPersonalDataUpdateCoordinator(DataUpdateCoordinator[PersonData]):
    """Fetch the most recent sleep and the last sync time of one person."""

    config_entry: GarminConnectPersonalConfigEntry

    async def _async_update_data(self) -> PersonData:
        """Update data via library."""
        client = self.config_entry.runtime_data.client
        today = dt_util.now().date()
        try:
            return PersonData(
                sleep=await self._async_get_sleep(client, today),
                last_sync=await self._async_get_last_sync(client, today),
            )
        except GarminConnectPersonalApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except GarminConnectPersonalApiClientRateLimitError as exception:
            raise UpdateFailed(
                exception,
                retry_after=exception.retry_after,
            ) from exception
        except GarminConnectPersonalApiClientError as exception:
            raise UpdateFailed(exception) from exception

    @staticmethod
    async def _async_get_sleep(
        client: GarminConnectPersonalApiClient, today: date
    ) -> SleepData | None:
        """Return the most recent sleep."""
        # Garmin files a night's sleep under the date the person woke up.
        # Until last night has synced, fall back to the night before.
        sleep = SleepData.from_dto(await client.async_get_daily_sleep(today))
        if sleep is None:
            sleep = SleepData.from_dto(
                await client.async_get_daily_sleep(today - timedelta(days=1))
            )
        return sleep

    @staticmethod
    async def _async_get_last_sync(
        client: GarminConnectPersonalApiClient, today: date
    ) -> datetime | None:
        """Return when the person's device last synced."""
        # Shortly after midnight there may be no summary for today yet.
        for day in (today, today - timedelta(days=1)):
            summary = await client.async_get_daily_summary(day)
            if last_sync := parse_timestamp(summary.get("lastSyncTimestampGMT")):
                return last_sync
        return None
