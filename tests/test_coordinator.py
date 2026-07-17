"""Tests for the data coordinator: response parsing, the 401 -> auth-failed
path, and that the persistent notification fires once and clears on
recovery rather than spamming on every failed poll."""

from datetime import date

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.setup import async_setup_component

from custom_components.vacation_tracker.coordinator import NOTIFICATION_ID, VacationTrackerCoordinator

BASE_URL = "http://10.0.1.18:5678"
API_KEY = "test-key"

TODAY_URL = f"{BASE_URL}/webhook/vacation/today"
HOLIDAYS_URL = f"{BASE_URL}/webhook/vacation/holidays"
LIST_URL = f"{BASE_URL}/webhook/vacation/list"


async def test_update_data_success(hass, aioclient_mock):
    aioclient_mock.get(
        TODAY_URL,
        json={
            "day_off": True,
            "entries": [{"id": 1, "name": "steffan", "type": "Sommerferie"}],
        },
    )
    aioclient_mock.get(
        HOLIDAYS_URL,
        json=[{"date": f"{date.today().isoformat()}T00:00:00.000Z", "name": "Testdag"}],
    )
    aioclient_mock.get(LIST_URL, json=[])

    coordinator = VacationTrackerCoordinator(hass, BASE_URL, API_KEY)
    data = await coordinator._async_update_data()

    assert data["day_off"] is True
    assert data["day_off_entries"][0]["name"] == "steffan"
    assert data["is_holiday"] is True
    assert data["holiday_names"] == ["Testdag"]
    assert data["upcoming"] == []


async def test_update_data_ignores_holidays_on_other_days(hass, aioclient_mock):
    aioclient_mock.get(TODAY_URL, json={"day_off": False, "entries": []})
    aioclient_mock.get(HOLIDAYS_URL, json=[{"date": "2099-01-01T00:00:00.000Z", "name": "Fremtidsdag"}])
    aioclient_mock.get(LIST_URL, json=[])

    coordinator = VacationTrackerCoordinator(hass, BASE_URL, API_KEY)
    data = await coordinator._async_update_data()

    assert data["is_holiday"] is False
    assert data["holiday_names"] == []


async def test_unauthorized_raises_config_entry_auth_failed(hass, aioclient_mock):
    await async_setup_component(hass, "persistent_notification", {})
    aioclient_mock.get(TODAY_URL, status=401)

    coordinator = VacationTrackerCoordinator(hass, BASE_URL, API_KEY)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()

    assert coordinator._auth_failed_notified is True
    assert hass.states.get(f"persistent_notification.{NOTIFICATION_ID}") is not None


async def test_notification_does_not_duplicate_on_repeated_failures(hass, aioclient_mock):
    await async_setup_component(hass, "persistent_notification", {})
    aioclient_mock.get(TODAY_URL, status=401)

    coordinator = VacationTrackerCoordinator(hass, BASE_URL, API_KEY)
    for _ in range(3):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    # Still only a single notification, not one per failed poll.
    assert len(hass.states.async_all("persistent_notification")) == 1


async def test_notification_clears_on_recovery(hass, aioclient_mock):
    await async_setup_component(hass, "persistent_notification", {})

    coordinator = VacationTrackerCoordinator(hass, BASE_URL, API_KEY)
    # Trigger a real notification first (not just the flag) so clearing it
    # is actually exercised, not trivially true because nothing existed.
    coordinator._notify_auth_failed()
    assert hass.states.get(f"persistent_notification.{NOTIFICATION_ID}") is not None

    aioclient_mock.get(TODAY_URL, json={"day_off": False, "entries": []})
    aioclient_mock.get(HOLIDAYS_URL, json=[])
    aioclient_mock.get(LIST_URL, json=[])

    await coordinator._async_update_data()

    assert coordinator._auth_failed_notified is False
    assert hass.states.get(f"persistent_notification.{NOTIFICATION_ID}") is None
