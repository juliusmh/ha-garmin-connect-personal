"""Tests for the Garmin Connect Personal config flow."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.garmin_connect_personal.api import (
    GarminConnectPersonalApiClientAuthenticationError,
    GarminConnectPersonalApiClientCommunicationError,
    GarminConnectPersonalApiClientError,
)
from custom_components.garmin_connect_personal.const import DOMAIN

from .conftest import DISPLAY_NAME, NOW, TODAY, USER_PROFILE_ID

pytestmark = [pytest.mark.freeze_time(NOW), pytest.mark.usefixtures("mock_api")]


@pytest.fixture(autouse=True)
def mock_setup_entry() -> Generator[AsyncMock]:
    """Don't set up the entry after the flow creates it."""
    with patch(
        "custom_components.garmin_connect_personal.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock


async def test_user_flow(hass: HomeAssistant) -> None:
    """A valid API key creates an entry identified by the Garmin user ID."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "api-key"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DISPLAY_NAME
    assert result["data"] == {CONF_API_KEY: "api-key"}
    assert result["result"].unique_id == str(USER_PROFILE_ID)


async def test_user_flow_without_user_id(
    hass: HomeAssistant, summary_by_date: dict
) -> None:
    """Without a user ID in the summary, the display name identifies the person."""
    summary_by_date[TODAY] = {"displayName": DISPLAY_NAME}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_API_KEY: "api-key"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == DISPLAY_NAME


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (GarminConnectPersonalApiClientAuthenticationError, "auth"),
        (GarminConnectPersonalApiClientCommunicationError, "connection"),
        (GarminConnectPersonalApiClientError, "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_api: tuple[AsyncMock, AsyncMock],
    exception: type[Exception],
    error: str,
) -> None:
    """API errors are shown on the form, and the person can try again."""
    _, get_summary = mock_api
    side_effect = get_summary.side_effect
    get_summary.side_effect = exception("boom")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_API_KEY: "api-key"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    get_summary.side_effect = side_effect
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "api-key"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The same person can't be added twice."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_API_KEY: "other-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """A new API key for the same person replaces the old one."""
    config_entry.add_to_hass(hass)

    result = await config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_API_KEY] == "new-key"


async def test_reauth_wrong_account(
    hass: HomeAssistant, config_entry: MockConfigEntry, summary_by_date: dict
) -> None:
    """An API key of another person is rejected during reauth."""
    config_entry.add_to_hass(hass)
    summary_by_date[TODAY] = {"userProfileId": 1, "displayName": "someone-else"}

    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "new-key"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert config_entry.data[CONF_API_KEY] == "api-key"
