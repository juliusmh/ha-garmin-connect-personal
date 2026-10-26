"""Binary sensor platform for garmin_connect_personal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.util import dt as dt_util

from .entity import GarminConnectPersonalEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GarminConnectPersonalConfigEntry

IS_AWAKE = BinarySensorEntityDescription(
    key="is_awake",
    translation_key="is_awake",
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: GarminConnectPersonalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        [
            GarminConnectPersonalIsAwakeBinarySensor(
                coordinator=entry.runtime_data.coordinator,
                entity_description=IS_AWAKE,
            ),
        ]
    )


class GarminConnectPersonalIsAwakeBinarySensor(
    GarminConnectPersonalEntity, BinarySensorEntity
):
    """On unless the person is within their most recently synced sleep."""

    @property
    def is_on(self) -> bool | None:
        """Return true if the person isn't sleeping."""
        sleep = self.coordinator.data.sleep
        if sleep is None:
            return None
        return not sleep.is_asleep(dt_util.utcnow())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the sleep window the state is based on."""
        sleep = self.coordinator.data.sleep
        if sleep is None:
            return {}
        return {"sleep_start": sleep.sleep_start, "sleep_end": sleep.sleep_end}
