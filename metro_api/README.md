# metro_api

FastAPI backend that parses MTA GTFS-RT feeds and serves a JSON ETA endpoint
for the Arduino display.

## Running

```bash
cd metro_api
poetry install
poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- `--host 0.0.0.0` is required so the ESP32 on your local network can reach it
- `--reload` for development; drop it in production

## Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/eta` | Full payload: transit ETAs + weather. This is what the Arduino polls. |
| `GET /health` | Uptime check + cache warm/cold state |
| `GET /docs` | Auto-generated Swagger UI (FastAPI built-in) |

## curl examples

Using the Arduino config file as the request body:
```bash
curl -s -X POST http://localhost:8000/api/eta \
  -H "Content-Type: application/json" \
  -d @../arduino_metrodisplay_module/config.json | jq
```

Just the stops:
```bash
curl -s -X POST http://localhost:8000/api/eta \
  -H "Content-Type: application/json" \
  -d @../arduino_metrodisplay_module/config.json | jq .stops
```

Just the first stop's northbound trains:
```bash
curl -s -X POST http://localhost:8000/api/eta \
  -H "Content-Type: application/json" \
  -d @../arduino_metrodisplay_module/config.json | jq '.stops[0].directions[0].trains'
```

Health check:
```bash
curl http://localhost:8000/health
```

## Request body

The Arduino POSTs its stop config on every poll. Stop config is defined in
`../arduino_metrodisplay_module/config.json` and flashed to the device.

```json
{
  "stops": [
    {
      "feed": "N",
      "label": "39 Av",
      "directions": [
        { "label": "northbound", "stop_id": "R08N" },
        { "label": "southbound", "stop_id": "R08S" }
      ]
    }
  ]
}
```

- `feed` — MTA feed identifier passed to NYCTFeed
- `label` — display name for the stop (shown on the Arduino UI)
- `stop_id` — full GTFS stop ID including direction suffix (e.g. `R08N`, `R08S`)

## Response shape

```json
{
  "updated_at": "2026-04-03T23:07:00",
  "stops": [
    {
      "label": "39 Av",
      "directions": [
        {
          "label": "northbound",
          "trains": [
            { "line": "N", "color": "FCCC0A", "dest": "Astoria-Ditmars Blvd", "eta_min": 3, "trip_id": "133250_N..N31R" },
            { "line": "N", "color": "FCCC0A", "dest": "Astoria-Ditmars Blvd", "eta_min": 9, "trip_id": "135050_N..N20R" }
          ]
        },
        {
          "label": "southbound",
          "trains": [
            { "line": "N", "color": "FCCC0A", "dest": "Coney Island-Stillwell Av", "eta_min": 5, "trip_id": "141550_N..S20R" }
          ]
        }
      ]
    },
    {
      "label": "Queens Plaza",
      "directions": [
        {
          "label": "southbound",
          "trains": [
            { "line": "E", "color": "0039A6", "dest": "World Trade Center", "eta_min": 2, "trip_id": "139400_E..S04R" }
          ]
        }
      ]
    }
  ],
  "weather": {
    "current_temp_f": 57,
    "high_f": 65,
    "low_f": 41,
    "rain_chance_pct": 3,
    "wind_mph": 4,
    "wind_dir": "S"
  }
}
```

## Cache

| Data | TTL |
|---|---|
| Transit (per unique config) | 1 minute |
| Weather | 3 minutes |

Cache is in-memory — resets on server restart. Transit cache is keyed by a hash
of the request body, so different configs get independent cache entries. All stop
feed fetches run concurrently in a thread pool (nyct-gtfs is blocking), so a
cold cache miss takes ~600ms instead of ~1800ms per stop.

## Development scripts

```bash
# Verify stop IDs return real live data
poetry run python -m scripts.test
```
