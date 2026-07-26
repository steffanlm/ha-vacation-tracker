# Vacation Tracker (Ferieoversigt) for Home Assistant

A custom Home Assistant integration for a personal Ferieoversigt
vacation-tracker site (now a tab on the home dashboard rather than its own
domain). Polls the site's API once per cycle and exposes who's
off today, what type of leave it is, whether today is a Danish public/school
holiday, and how many periods are upcoming.

## Entities

| Entity | Type | Description |
| --- | --- | --- |
| `binary_sensor.vacation_day_off` | binary_sensor | On if anyone is on a tracked vacation today. Attribute `entries` lists who/what. |
| `binary_sensor.vacation_is_holiday` | binary_sensor | On if today is a Danish public or school holiday. Attribute `holiday_names`. |
| `sensor.vacation_day_off_who` | sensor | Comma-separated names of who's off today, or "Ingen". |
| `sensor.vacation_day_off_type` | sensor | Comma-separated vacation type(s) today (e.g. "Sommerferie"), or "Ingen". |
| `sensor.vacation_upcoming` | sensor | Count of upcoming periods. Attribute `entries` has the full list (name, dates, type, color) for a table card. |

All four are grouped under one "Ferieoversigt" device and share a single
polling cycle (default every 30 minutes) against three endpoints:
`/webhook/vacation/today`, `/webhook/vacation/holidays`, `/webhook/vacation/list`.

## Installation

### Via HACS (custom repository)

1. HACS → the three-dot menu (top right) → **Custom repositories**
2. Add this repository's URL, category **Integration**
3. Install "Vacation Tracker (Ferieoversigt)" from HACS
4. Restart Home Assistant
5. Settings → Devices & Services → **Add Integration** → search "Ferieoversigt"

### Manual

Copy `custom_components/vacation_tracker/` into your Home Assistant
`config/custom_components/` directory, restart, then add the integration as above.

## Setup

You'll need:
- **Base URL** of the vacation tracker's n8n webhook (e.g. `http://10.0.1.18:5678`)
- **API key**, generated from the site's own Indstillinger (Settings) tab

## Rotating the API key

If the key is regenerated on the site, this integration will:
- Show a **"Reauthentication required"** banner on the integration card
- Post a persistent notification (bell icon) explaining what happened

Either one leads to a small form where you paste in the new key — no YAML
edits or restarts needed. You can also update the key any time via the
integration's **Configure** (Options) button.

## Development

```bash
pip install -r requirements_test.txt
pytest
```

## License

MIT
