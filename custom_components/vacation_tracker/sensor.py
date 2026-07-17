from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VacationTrackerCoordinator
from .entity import VacationTrackerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VacationTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            VacationDayOffWhoSensor(coordinator, entry),
            VacationDayOffTypeSensor(coordinator, entry),
            VacationUpcomingSensor(coordinator, entry),
        ]
    )


class VacationDayOffWhoSensor(VacationTrackerEntity, SensorEntity):
    _attr_name = "Vacation Day Off Who"
    _attr_icon = "mdi:account-multiple"

    def __init__(self, coordinator: VacationTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_day_off_who"
        # Matches the entity_id the old YAML rest: sensor used.
        self.entity_id = "sensor.vacation_day_off_who"

    @property
    def native_value(self) -> str:
        entries = self.coordinator.data["day_off_entries"]
        if not entries:
            return "Ingen"
        names = sorted({e["name"] for e in entries})
        return ", ".join(names)


class VacationDayOffTypeSensor(VacationTrackerEntity, SensorEntity):
    _attr_name = "Vacation Day Off Type"
    _attr_icon = "mdi:tag-text"

    def __init__(self, coordinator: VacationTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_day_off_type"
        self.entity_id = "sensor.vacation_day_off_type"

    @property
    def native_value(self) -> str:
        entries = self.coordinator.data["day_off_entries"]
        if not entries:
            return "Ingen"
        types = sorted({e["type"] for e in entries})
        return ", ".join(types)


class VacationUpcomingSensor(VacationTrackerEntity, SensorEntity):
    _attr_name = "Vacation Upcoming"
    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = "perioder"

    def __init__(self, coordinator: VacationTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_upcoming"
        self.entity_id = "sensor.vacation_upcoming"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data["upcoming"])

    @property
    def extra_state_attributes(self) -> dict:
        # Full upcoming list (name, start/end date, type, color) - use in a
        # markdown or auto-entities card for a proper table view.
        return {"entries": self.coordinator.data["upcoming"]}
