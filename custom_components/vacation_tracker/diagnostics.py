from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, DOMAIN
from .coordinator import VacationTrackerCoordinator

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Downloadable from Settings > Devices & Services > Ferieoversigt >
    Download diagnostics. The API key is redacted before it ever leaves
    this function."""
    coordinator: VacationTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "last_exception": str(coordinator.last_exception) if coordinator.last_exception else None,
        "coordinator_data": coordinator.data,
    }
