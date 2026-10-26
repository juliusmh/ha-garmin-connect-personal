"""GarminConnectPersonalEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import GarminConnectPersonalDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription


class GarminConnectPersonalEntity(
    CoordinatorEntity[GarminConnectPersonalDataUpdateCoordinator]
):
    """An entity of one person. Each person is a device."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GarminConnectPersonalDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.entity_description = entity_description
        self._attr_unique_id = f"{entry.unique_id}_{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.unique_id))},
            name=entry.title,
            manufacturer=MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
        )
