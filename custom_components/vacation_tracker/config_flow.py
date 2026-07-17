from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
    TODAY_PATH,
)

_LOGGER = logging.getLogger(__name__)

_SCAN_INTERVAL_VALIDATOR = vol.All(
    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MINUTES, max=MAX_SCAN_INTERVAL_MINUTES)
)


async def _test_connection(hass, base_url: str, api_key: str) -> bool:
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            f"{base_url.rstrip('/')}{TODAY_PATH}",
            headers={"x-api-key": api_key},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            return resp.status == 200
    except (aiohttp.ClientError, TimeoutError):
        return False


class VacationTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            if await _test_connection(self.hass, user_input[CONF_BASE_URL], user_input[CONF_API_KEY]):
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Ferieoversigt", data=user_input)
            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default="http://10.0.1.18:5678"): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES, default=DEFAULT_SCAN_INTERVAL_MINUTES
                ): _SCAN_INTERVAL_VALIDATOR,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> config_entries.ConfigFlowResult:
        """Home Assistant calls this automatically when the coordinator raises
        ConfigEntryAuthFailed (i.e. the API key was rejected), and shows a
        "Reauthentication required" banner that leads here."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None
        current = self._reauth_entry.data

        if user_input is not None:
            base_url = user_input.get(CONF_BASE_URL, current.get(CONF_BASE_URL, ""))
            if await _test_connection(self.hass, base_url, user_input[CONF_API_KEY]):
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={**current, CONF_BASE_URL: base_url, CONF_API_KEY: user_input[CONF_API_KEY]},
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            errors["base"] = "invalid_auth"

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=current.get(CONF_BASE_URL, "")): str,
                vol.Required(CONF_API_KEY): str,
            }
        )
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "VacationTrackerOptionsFlow":
        return VacationTrackerOptionsFlow(config_entry)


class VacationTrackerOptionsFlow(config_entries.OptionsFlow):
    """Lets base_url, api_key and the refresh interval be updated from the HA
    UI at any time - e.g. after generating a new key on the site's
    Indstillinger tab - without editing YAML or restarting Home Assistant."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        current = self.config_entry.data

        if user_input is not None:
            if await _test_connection(self.hass, user_input[CONF_BASE_URL], user_input[CONF_API_KEY]):
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**current, **user_input},
                )
                return self.async_create_entry(title="", data={})
            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=current.get(CONF_BASE_URL, "")): str,
                vol.Required(CONF_API_KEY, default=current.get(CONF_API_KEY, "")): str,
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES,
                    default=current.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES),
                ): _SCAN_INTERVAL_VALIDATOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
