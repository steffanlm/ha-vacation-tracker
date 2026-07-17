from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
            VacationDayOffBinarySensor(coordinator, entry),
            VacationHolidayTodayBinarySensor(coordinator, entry),
        ]
    )


class VacationDayOffBinarySensor(VacationTrackerEntity, BinarySensorEntity):
    _attr_name = "Vacation Day Off"
    _attr_icon = "mdi:beach"

    def __init__(self, coordinator: VacationTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_day_off"
        # Matches the entity_id the old YAML rest: sensor used, so existing
        # automations/dashboards keep working without changes.
        self.entity_id = "binary_sensor.vacation_day_off"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data["day_off"]

    @property
    def extra_state_attributes(self) -> dict:
        return {"entries": self.coordinator.data["day_off_entries"]}


class VacationHolidayTodayBinarySensor(VacationTrackerEntity, BinarySensorEntity):
    _attr_name = "Vacation Holiday Today"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: VacationTrackerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_holiday_today"
        self.entity_id = "binary_sensor.vacation_is_holiday"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data["is_holiday"]

    @property
    def extra_state_attributes(self) -> dict:
        return {"holiday_names": self.coordinator.data["holiday_names"]}
