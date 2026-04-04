# metro_api

FastAPI backend that parses MTA GTFS-RT feeds and serves a JSON ETA endpoint
for the Arduino display.

## Running

```bash
poetry install
poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- `--host 0.0.0.0` is required so the ESP32 on your local network can reach it
- `--reload` for development; drop it in production

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/eta` | Full payload: transit ETAs + weather. This is what the Arduino polls. |
| `GET /health` | Uptime check + cache warm/cold state |
| `GET /docs` | Auto-generated Swagger UI (FastAPI built-in) |

## Response shape

```json
{
  "updated_at": "2026-04-04T09:15:00",
  "stops": {
    "n_39th_ave": {
      "northbound": [
        { "line": "N", "destination": "Astoria-Ditmars Blvd", "eta_min": 3 }
      ],
      "southbound": [
        { "line": "N", "destination": "Coney Island", "eta_min": 5 }
      ]
    },
    "e_queens_plaza": {
      "southbound": [
        { "line": "E", "destination": "World Trade Center", "eta_min": 2 }
      ]
    },
    "seven_queensboro": {
      "westbound": [
        { "line": "7", "destination": "Hudson Yards", "eta_min": 1 }
      ]
    }
  },
  "weather": {
    "current_temp_f": 54,
    "high_f": 61,
    "low_f": 48,
    "rain_chance_pct": 20,
    "wind_mph": 9,
    "wind_dir": "NW"
  }
}
```

## Cache

| Data | TTL |
|---|---|
| Transit (all stops) | 1 minute |
| Weather | 3 minutes |

Cache is in-memory — it resets on server restart. The three MTA feed fetches
run concurrently in a thread pool (nyct-gtfs is blocking), so a cold cache miss
takes ~600ms instead of ~1800ms.

## Stop IDs

Hardcoded in `app.py`. Based on MTA GTFS static data — verify against live
feeds if any stop returns empty results:

```bash
poetry run python -m scripts.test
```

`find_stop_ids()` in `scripts/test.py` will scan live feeds and print stop IDs
by name, so you can cross-check the constants in `app.py`.

| Constant | Value | Stop |
|---|---|---|
| `N_39AV_NORTHBOUND` | `R11N` | 39 Av → Astoria-Ditmars Blvd |
| `N_39AV_SOUTHBOUND` | `R11S` | 39 Av → Manhattan |
| `E_QUEENS_PLAZA_S` | `G08S` | Queens Plaza → WTC |
| `SEVEN_QUEENSBORO_S` | `723S` | Queensboro Plaza → Hudson Yards |

## Development scripts

```bash
# Explore live feed data and verify stop IDs
poetry run python -m scripts.test
```
