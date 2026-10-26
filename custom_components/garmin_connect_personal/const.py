"""Constants for garmin_connect_personal."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "garmin_connect_personal"
ATTRIBUTION = "Data provided by Garmin Connect"
MANUFACTURER = "Garmin"

UPDATE_INTERVAL = timedelta(minutes=15)
