"""Sensor platform for garmin_connect_personal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime

from .entity import GarminConnectPersonalEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import GarminConnectPersonalConfigEntry, PersonData, SleepData


@dataclass(frozen=True, kw_only=True)
class GarminConnectPersonalSensorEntityDescription(SensorEntityDescription):
    """Describes a sensor and how to read its value."""

    value_fn: Callable[[PersonData], float | datetime | None]
    attributes_fn: Callable[[PersonData], dict[str, Any]] | None = None


def _sleep_value(
    get: Callable[[SleepData], float | None],
) -> Callable[[PersonData], float | None]:
    """Read a value of the most recent sleep, if there is one."""
    return lambda data: get(data.sleep) if data.sleep else None


def _sleep_duration(
    key: str, value_fn: Callable[[SleepData], float | None]
) -> GarminConnectPersonalSensorEntityDescription:
    """Describe a sleep duration, reported by Garmin in seconds."""
    return GarminConnectPersonalSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        value_fn=_sleep_value(value_fn),
    )


ENTITY_DESCRIPTIONS: tuple[GarminConnectPersonalSensorEntityDescription, ...] = (
    GarminConnectPersonalSensorEntityDescription(
        key="sleep_score",
        translation_key="sleep_score",
        icon="mdi:sleep",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sleep_value(lambda sleep: sleep.sleep_score),
        attributes_fn=lambda data: (
            {
                "qualifier": data.sleep.sleep_score_qualifier,
                "calendar_date": data.sleep.calendar_date,
            }
            if data.sleep
            else {}
        ),
    ),
    _sleep_duration("sleep_duration", lambda sleep: sleep.sleep_seconds),
    _sleep_duration("deep_sleep_duration", lambda sleep: sleep.deep_sleep_seconds),
    _sleep_duration("light_sleep_duration", lambda sleep: sleep.light_sleep_seconds),
    _sleep_duration("rem_sleep_duration", lambda sleep: sleep.rem_sleep_seconds),
    _sleep_duration("awake_duration", lambda sleep: sleep.awake_seconds),
    GarminConnectPersonalSensorEntityDescription(
        key="awake_count",
        translation_key="awake_count",
        icon="mdi:eye-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sleep_value(lambda sleep: sleep.awake_count),
    ),
    GarminConnectPersonalSensorEntityDescription(
        key="sleep_heart_rate",
        translation_key="sleep_heart_rate",
        icon="mdi:heart-pulse",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="bpm",
        suggested_display_precision=0,
        value_fn=_sleep_value(lambda sleep: sleep.average_heart_rate),
    ),
    GarminConnectPersonalSensorEntityDescription(
        key="sleep_respiration",
        translation_key="sleep_respiration",
        icon="mdi:lungs",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="brpm",
        suggested_display_precision=1,
        value_fn=_sleep_value(lambda sleep: sleep.average_respiration),
    ),
    GarminConnectPersonalSensorEntityDescription(
        key="sleep_stress",
        translation_key="sleep_stress",
        icon="mdi:head-heart-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_sleep_value(lambda sleep: sleep.average_stress),
    ),
    GarminConnectPersonalSensorEntityDescription(
        key="last_sync",
        translation_key="last_sync",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_sync,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: GarminConnectPersonalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        GarminConnectPersonalSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class GarminConnectPersonalSensor(GarminConnectPersonalEntity, SensorEntity):
    """A sensor of one person."""

    entity_description: GarminConnectPersonalSensorEntityDescription

    @property
    def native_value(self) -> float | datetime | None:
        """Return the native value of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes, if the sensor has any."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)
