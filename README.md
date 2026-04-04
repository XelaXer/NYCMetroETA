# NYCMetroETA

Real-time NYC subway ETA display — a Python backend that parses MTA live feeds
and serves a JSON API consumed by an ESP32-based physical display unit.

## Repo structure

```
NYCMetroETA/
├── .github/workflows/
│   └── test.yml                  # CI: runs pytest on push/PR
│
├── metro_api/                    # Python backend (FastAPI)
│   ├── app.py                    # API server — run this
│   ├── tests/                    # pytest suite
│   ├── scripts/
│   │   └── explore_feed.py       # Dev tool: inspect raw MTA feed data
│   ├── pyproject.toml
│   └── README.md
│
└── arduino_metrodisplay_module/  # ESP32 display firmware
    ├── config.json               # Stop config — flashed to device, POSTed on each poll
    └── README.md                 # Hardware requirements + setup guide
```

## How it works

```
Arduino config.json ──► POST /api/eta ──► ESP32 display renders
                              │
              ┌───────────────┴──────────────┐
         MTA GTFS-RT feeds          Open-Meteo weather
              │                              │
         NYCTFeed parser              httpx async fetch
              └───────────────┬──────────────┘
                        TTL cache
                    transit: 1 min
                    weather: 3 min
```

The Arduino POSTs its stop config on every poll. The API fetches only the
requested stops from MTA GTFS-RT feeds, attaches MTA line colors and trip IDs,
and returns a clean JSON array. The ESP32 iterates the response and renders each
stop and direction dynamically — nothing is hardcoded in firmware beyond the
config file.

## Stops (defined in `arduino_metrodisplay_module/config.json`)

| Station | Feed | Lines | Directions |
|---|---|---|---|
| 39 Av | N | N, W | northbound (Ditmars), southbound (Manhattan) |
| Queens Plaza | E + N | E, R | southbound (WTC) |
| Queensboro Plaza | 7 + N | 7, N, W | westbound (Hudson Yards), northbound (Ditmars), southbound (Manhattan) |

To add or change stops: edit `config.json` and reflash. No API changes needed.

## Quick start — Python backend

```bash
cd metro_api
poetry install
poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Test with the Arduino config:
```bash
curl -s -X POST http://localhost:8000/api/eta \
  -H "Content-Type: application/json" \
  -d @arduino_metrodisplay_module/config.json | jq
```

## Running tests

```bash
cd metro_api
poetry run pytest -v
```

## Hardware

**Waveshare ESP32-S3-Touch-LCD-7B** — 7" IPS 1024×600, ESP32-S3R8 (8MB PSRAM),
capacitive touch, USB-C. See `arduino_metrodisplay_module/README.md` for full
setup guide.

## What's done / what's next

**Backend (metro_api)**
- [x] FastAPI server with `POST /api/eta` and `GET /health`
- [x] MTA GTFS-RT feed parsing — N/Q/R/W, E/A/C, 7
- [x] Stops: 39 Av (N/W), Queens Plaza (E/R), Queensboro Plaza (7/N/W)
- [x] MTA line colors per departure (`color` hex field)
- [x] Trip IDs per departure (enables partial re-renders on Arduino)
- [x] Open-Meteo weather (temp, high/low, rain, wind)
- [x] TTL cache (transit 1 min, weather 3 min)
- [x] Concurrent feed fetching (thread pool)
- [x] Dynamic stop config — stops defined in `config.json`, not hardcoded in API
- [x] pytest suite + GitHub Actions CI
- [ ] Add `.env` / `config.py` for any future API keys
- [ ] Consider running as a systemd service for always-on hosting

**Arduino (arduino_metrodisplay_module)**
- See `arduino_metrodisplay_module/README.md`
