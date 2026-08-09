from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import aiohttp
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    HOLIDAYS_PATH,
    LIST_PATH,
    TODAY_PATH,
    WORK_LOCATION_TOMORROW_PATH,
)

_LOGGER = logging.getLogger(__name__)

NOTIFICATION_ID = "vacation_tracker_auth_failed"


def _parse_date(value: str) -> date:
    # The API returns ISO datetimes like "2026-07-11T00:00:00.000Z" - only
    # the date portion matters for comparisons here.
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


class VacationTrackerCoordinator(DataUpdateCoordinator):
    """Fetches /today, /holidays and /list in one polling cycle and shares
    the combined result with every sensor, so each entity doesn't need its
    own separate HTTP call."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_url: str,
        api_key: str,
        scan_interval_minutes: int = DEFAULT_SCAN_INTERVAL_MINUTES,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval_minutes),
        )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._auth_failed_notified = False

    def update_connection(self, base_url: str, api_key: str, scan_interval_minutes: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.update_interval = timedelta(minutes=scan_interval_minutes)

    def _notify_auth_failed(self) -> None:
        # Guarded so this fires once per outage, not on every failed poll
        # while the key stays broken (default update_interval is 30 min).
        if self._auth_failed_notified:
            return
        self._auth_failed_notified = True
        persistent_notification.async_create(
            self.hass,
            title="Ferieoversigt: API-nøgle er ugyldig",
            message=(
                "API-nøglen blev afvist af serveren - den er sandsynligvis blevet "
                "fornyet på selve siden. Generér en ny nøgle under Indstillinger på "
                "h.holmehave21.dk (fanen \"Vacation\"), og indtast den derefter her: "
                "Indstillinger → Enheder og tjenester → Ferieoversigt → "
                "\"Genautentificer\"."
            ),
            notification_id=NOTIFICATION_ID,
        )

    def _clear_auth_failed_notification(self) -> None:
        if not self._auth_failed_notified:
            return
        self._auth_failed_notified = False
        persistent_notification.async_dismiss(self.hass, NOTIFICATION_ID)

    async def _fetch(self, path: str):
        session = async_get_clientsession(self.hass)
        headers = {"x-api-key": self.api_key}
        try:
            async with session.get(
                f"{self.base_url}{path}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    # Triggers Home Assistant's built-in "Reauthentication
                    # required" banner on the integration, plus an explicit
                    # persistent notification (the banner alone is easy to
                    # miss unless you're already on the Devices & Services
                    # page) - exactly what's needed after rotating the key.
                    self._notify_auth_failed()
                    raise ConfigEntryAuthFailed("API key was rejected (401) - it was probably rotated on the site")
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            # TimeoutError doesn't inherit from aiohttp.ClientError, so it
            # needs its own arm here - otherwise a slow/unreachable server
            # would raise an unhandled exception instead of a clean
            # UpdateFailed.
            raise UpdateFailed(f"Error communicating with vacation tracker: {err}") from err

    async def _async_update_data(self) -> dict:
        today_data = await self._fetch(TODAY_PATH)
        holidays_data = await self._fetch(HOLIDAYS_PATH)
        upcoming_data = await self._fetch(LIST_PATH)
        work_location_data = await self._fetch(WORK_LOCATION_TOMORROW_PATH)

        # Reaching this point means every fetch succeeded, so clear any
        # earlier "key is invalid" notification if one is still showing.
        self._clear_auth_failed_notification()

        today = date.today()
        holiday_names_today = [h["name"] for h in holidays_data if _parse_date(h["date"]) == today]

        return {
            "day_off": bool(today_data.get("day_off")),
            "day_off_entries": today_data.get("entries", []),
            "is_holiday": len(holiday_names_today) > 0,
            "holiday_names": holiday_names_today,
            "upcoming": upcoming_data,
            "work_location_tomorrow": work_location_data.get("location"),
            "work_location_tomorrow_color": work_location_data.get("color"),
        }
