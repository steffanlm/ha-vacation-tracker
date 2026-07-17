from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VacationTrackerCoordinator


class VacationTrackerEntity(CoordinatorEntity[VacationTrackerCoordinator]):
    """Base entity - groups every entity from this integration under one
    device page (Settings > Devices & Services > Ferieoversigt) instead of
    four unrelated-looking loose entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VacationTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ferieoversigt",
            manufacturer="holmehave21",
            model="Vacation Tracker",
            configuration_url=coordinator.base_url,
            entry_type=DeviceEntryType.SERVICE,
        )
