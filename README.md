# NYCMetroETA

Real-time NYC subway ETA display — a Python backend that parses MTA live feeds
and serves a JSON API consumed by an ESP32-based physical display unit.

## Repo structure

```
NYCMetroETA/
├── metro_api/                  # Python backend (FastAPI)
│   ├── app.py                  # API server — run this
│   ├── scripts/
│   │   └── test.py             # Dev/debug script for feed exploration
│   ├── pyproject.toml
│   └── README.md
│
└── arduino_metrodisplay_module/  # ESP32 display firmware
    └── README.md               # Hardware requirements + setup guide
```

## How it works

```
MTA GTFS-RT feeds ──► metro_api/app.py ──► GET /api/eta (JSON) ──► ESP32 display
Open-Meteo weather ──►       │
                             └── in-memory TTL cache
                                  transit: 1 min
                                  weather: 3 min
```

The Python backend fetches live protobuf feeds from the MTA, parses upcoming
departures for three Queens stops, and exposes a single clean JSON endpoint.
The ESP32 polls that endpoint every 30 seconds and renders the result on a
7" touchscreen via LVGL.

## Stops tracked

| Line | Station | Direction |
|---|---|---|
| N | 39 Av (Astoria) | Both — northbound to Ditmars, southbound to Manhattan |
| E | Queens Plaza | Southbound to WTC |
| 7 | Queensboro Plaza | Westbound to Hudson Yards |

## Quick start — Python backend

```bash
cd metro_api
poetry install
poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000/api/eta` to verify the JSON response,
or `http://localhost:8000/health` to check cache state.

## Hardware

**Waveshare ESP32-S3-Touch-LCD-7B** — 7" IPS 1024×600, ESP32-S3R8 (8MB PSRAM),
capacitive touch, USB-C. See `arduino_metrodisplay_module/README.md` for full
setup guide.

## What's done / what's next

See `arduino_metrodisplay_module/README.md` for Arduino-side status.

**Backend (metro_api)**
- [x] GTFS-RT feed parsing for G/A/C (original route)
- [x] FastAPI server with `/api/eta` and `/health`
- [x] N at 39 Av, E at Queens Plaza, 7 at Queensboro Plaza
- [x] Open-Meteo weather (temp, high/low, rain, wind)
- [x] TTL cache (transit 1 min, weather 3 min)
- [x] Concurrent feed fetching (non-blocking)
- [ ] Verify stop IDs live — run `poetry run python -m scripts.test` and check output
- [ ] Add `.env` / `config.py` for WiFi credentials and any future API keys
- [ ] Consider running as a systemd service for always-on hosting
