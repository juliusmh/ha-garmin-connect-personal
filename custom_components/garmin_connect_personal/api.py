"""Async wrapper around the Garmin Connect Personal API client."""

from __future__ import annotations

import hashlib
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests
from garmin_personal_api import (
    GarminPersonalApiClient,
    GarminPersonalApiError,
    HttpError,
    PersonalApiAuthenticator,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.storage import STORAGE_DIR

from .const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date

    from homeassistant.core import HomeAssistant


class GarminConnectPersonalApiClientError(Exception):
    """Exception to indicate a general API error."""


class GarminConnectPersonalApiClientCommunicationError(
    GarminConnectPersonalApiClientError,
):
    """Exception to indicate a communication error."""


class GarminConnectPersonalApiClientAuthenticationError(
    GarminConnectPersonalApiClientError,
):
    """Exception to indicate an authentication error."""


class GarminConnectPersonalApiClientRateLimitError(
    GarminConnectPersonalApiClientCommunicationError,
):
    """Exception to indicate the API is rate limiting us."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Store the backoff period requested by the API."""
        super().__init__(message)
        self.retry_after = retry_after


def token_cache_file(hass: HomeAssistant, api_key: str) -> Path:
    """
    Return the bearer-token cache file for an API key.

    Every person gets their own file, so multiple accounts don't overwrite
    each other's cached token.
    """
    fingerprint = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return Path(hass.config.path(STORAGE_DIR, DOMAIN, f"{fingerprint}.json"))


class GarminConnectPersonalApiClient:
    """
    Garmin Connect Personal API client for a single person.

    The underlying library is synchronous (requests), so every call runs in
    Home Assistant's executor.
    """

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        """Initialize the client."""
        self._hass = hass
        self._api_key = api_key
        self._session = requests.Session()
        self._authenticator = PersonalApiAuthenticator(
            session=self._session,
            bearer_token_cache_file=token_cache_file(hass, api_key),
        )
        self._client: GarminPersonalApiClient | None = None

    @classmethod
    def from_entry_data(
        cls, hass: HomeAssistant, data: dict[str, Any]
    ) -> GarminConnectPersonalApiClient:
        """Create a client from config entry data."""
        return cls(hass, data[CONF_API_KEY])

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    async def async_get_daily_sleep(self, calendar_date: date) -> dict[str, Any]:
        """Return the sleep for a calendar date (the date the person woke up)."""
        return await self._async_call(
            lambda client: client.get_daily_sleep(calendar_date) or {}
        )

    async def async_get_daily_summary(self, calendar_date: date) -> dict[str, Any]:
        """Return the daily summary (steps, stress, last sync, ...) for a date."""
        # The library has no wrapper for this endpoint.
        return await self._async_call(
            lambda client: (
                client.get(
                    "/usersummary-service/usersummary/daily",
                    params={"calendarDate": calendar_date.isoformat()},
                )
                or {}
            )
        )

    async def _async_call(self, func: Callable[[GarminPersonalApiClient], Any]) -> Any:
        """Run a request in the executor and translate library errors."""
        try:
            return await self._hass.async_add_executor_job(self._call, func)
        except HttpError as exception:
            if exception.status_code in (
                HTTPStatus.UNAUTHORIZED,
                HTTPStatus.FORBIDDEN,
            ):
                msg = f"Invalid API key - {exception}"
                raise GarminConnectPersonalApiClientAuthenticationError(
                    msg
                ) from exception
            if exception.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                msg = f"Rate limited by the API - {exception}"
                raise GarminConnectPersonalApiClientRateLimitError(msg) from exception
            if exception.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                msg = f"Garmin server error - {exception}"
                raise GarminConnectPersonalApiClientCommunicationError(
                    msg
                ) from exception
            msg = f"Unexpected API response - {exception}"
            raise GarminConnectPersonalApiClientError(msg) from exception
        except requests.RequestException as exception:
            msg = f"Error communicating with Garmin - {exception}"
            raise GarminConnectPersonalApiClientCommunicationError(msg) from exception
        except (GarminPersonalApiError, OSError) as exception:
            msg = f"Garmin client error - {exception}"
            raise GarminConnectPersonalApiClientError(msg) from exception

    def _call(self, func: Callable[[GarminPersonalApiClient], Any]) -> Any:
        """Run a request, getting a new bearer token once if it was rejected."""
        try:
            return func(self._get_client(force_refresh=False))
        except HttpError as exception:
            if exception.status_code != HTTPStatus.UNAUTHORIZED:
                raise
        # The cached token may have been revoked before it expired.
        return func(self._get_client(force_refresh=True))

    def _get_client(self, *, force_refresh: bool) -> GarminPersonalApiClient:
        """Return a data client with a valid bearer token."""
        token = self._authenticator.obtain_token(
            self._api_key, force_refresh=force_refresh
        )
        if self._client is None:
            self._client = GarminPersonalApiClient(
                token.access_token, session=self._session
            )
        else:
            self._client.update_bearer_token(token.access_token)
        return self._client
