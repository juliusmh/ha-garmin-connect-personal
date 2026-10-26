"""Adds config flow for Garmin Connect Personal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .api import (
    GarminConnectPersonalApiClient,
    GarminConnectPersonalApiClientAuthenticationError,
    GarminConnectPersonalApiClientCommunicationError,
    GarminConnectPersonalApiClientError,
)
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from collections.abc import Mapping

API_KEY_URL = "https://connect.garmin.com/app/settings/personalApiToken"

API_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
        ),
    },
)


class GarminConnectPersonalFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Garmin Connect Personal. One entry per person."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            account, errors = await self._async_validate(user_input[CONF_API_KEY])
            if account is not None:
                unique_id, title = account
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            description_placeholders={"api_key_url": API_KEY_URL},
            data_schema=API_KEY_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Handle a rejected API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Ask for a new API key for the same person."""
        errors: dict[str, str] = {}
        if user_input is not None:
            account, errors = await self._async_validate(user_input[CONF_API_KEY])
            if account is not None:
                await self.async_set_unique_id(account[0])
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={
                "api_key_url": API_KEY_URL,
                "name": self._get_reauth_entry().title,
            },
            data_schema=API_KEY_SCHEMA,
            errors=errors,
        )

    async def _async_validate(
        self, api_key: str
    ) -> tuple[tuple[str, str] | None, dict[str, str]]:
        """
        Validate an API key.

        Returns the person's (unique_id, display name), or errors for the form.
        """
        client = GarminConnectPersonalApiClient(self.hass, api_key)
        try:
            summary = await client.async_get_daily_summary(dt_util.now().date())
        except GarminConnectPersonalApiClientAuthenticationError as exception:
            LOGGER.warning(exception)
            return None, {"base": "auth"}
        except GarminConnectPersonalApiClientCommunicationError as exception:
            LOGGER.error(exception)
            return None, {"base": "connection"}
        except GarminConnectPersonalApiClientError as exception:
            LOGGER.exception(exception)
            return None, {"base": "unknown"}
        finally:
            client.close()

        display_name = summary.get("displayName")
        # Prefer Garmin's numeric user ID, which never changes.
        user_profile_id = summary.get("userProfileId")
        unique_id = str(user_profile_id) if user_profile_id else display_name
        if not unique_id:
            return None, {"base": "unknown"}
        return (unique_id, display_name or unique_id), {}
