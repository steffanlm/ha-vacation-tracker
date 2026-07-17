"""Tests for the Vacation Tracker (Ferieoversigt) config flow, including
the reauth flow that fires when the API key is rotated on the site."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.vacation_tracker.const import CONF_API_KEY, CONF_BASE_URL, DOMAIN

BASE_URL = "http://10.0.1.18:5678"
TODAY_URL = f"{BASE_URL}/webhook/vacation/today"


async def test_user_flow_success(hass, aioclient_mock):
    aioclient_mock.get(TODAY_URL, json={"day_off": False, "entries": []})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: BASE_URL, CONF_API_KEY: "good-key"},
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"] == {CONF_BASE_URL: BASE_URL, CONF_API_KEY: "good-key"}


async def test_user_flow_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(TODAY_URL, status=401)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: BASE_URL, CONF_API_KEY: "bad-key"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured_aborts(hass, aioclient_mock):
    aioclient_mock.get(TODAY_URL, json={"day_off": False, "entries": []})

    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_BASE_URL: BASE_URL, CONF_API_KEY: "existing-key"},
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: BASE_URL, CONF_API_KEY: "another-key"},
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_reauth_flow_success(hass, aioclient_mock):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_BASE_URL: BASE_URL, CONF_API_KEY: "old-key"},
    )
    entry.add_to_hass(hass)

    aioclient_mock.get(TODAY_URL, json={"day_off": False, "entries": []})

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: BASE_URL, CONF_API_KEY: "new-key"},
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "new-key"


async def test_reauth_flow_invalid_key_shows_error(hass, aioclient_mock):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={CONF_BASE_URL: BASE_URL, CONF_API_KEY: "old-key"},
    )
    entry.add_to_hass(hass)

    aioclient_mock.get(TODAY_URL, status=401)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
            "unique_id": entry.unique_id,
        },
        data=entry.data,
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BASE_URL: BASE_URL, CONF_API_KEY: "still-bad-key"},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}
    # The stale key must not have been saved over the working one.
    assert entry.data[CONF_API_KEY] == "old-key"
