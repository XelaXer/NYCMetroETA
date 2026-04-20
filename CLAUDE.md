# NYCMetroETA — Claude Code Context

## What This Is

FastAPI server that provides real-time NYC subway ETAs and weather data. The Arduino metro display POSTs its stop config to this server on every poll and receives train arrivals + weather in one response. Deployed in the `fort` namespace on the NYC k3s cluster.

**Entry point:** `metro_api/app.py` (378 lines — the entire backend is one file)
**Stack:** Python 3.11, FastAPI, uvicorn, nyct-gtfs (MTA GTFS-RT protobuf parser), httpx, pytest

---

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/eta` | POST | Fetch train ETAs for given stops + weather |
| `/api/stops` | GET | List all active stops with available lines |
| `/health` | GET | Server uptime + cache state (warm/cold) |

**Request format for `/api/eta`:**
```json
{
  "stops": [
    {
      "feeds": ["N"],
      "label": "39 Av",
      "directions": [
        {"label": "northbound", "stop_id": "R08N"},
        {"label": "southbound", "stop_id": "R08S"}
      ]
    }
  ]
}
```

Stop config is not hardcoded in the backend — it's sent by the Arduino on every request. The Arduino's config lives in `arduino_metrodisplay_module/config.json`.

---

## Key Architecture Details

**Caching:** In-memory dict, keyed by MD5 hash of request body (so different stop configs cache independently). TTLs: transit 1 min, weather 3 min, `/api/stops` 30 min.

**Feed fetching:** `nyct-gtfs` is a blocking library. Each stop's feeds are fetched via `loop.run_in_executor()` so multiple stops parallelize despite blocking I/O.

**MTA feed structure:** Each GTFS-RT feed carries multiple routes (e.g., feed "N" → N, Q, R, W routes). Must know which feed a stop belongs to — not auto-detected.

**Stop IDs:** Directional convention — `R08N` = northbound, `R08S` = southbound. Parent station is the prefix (`R08`).

**Weather:** Free Open-Meteo API, no key required, coordinates hardcoded to Long Island City (40.7282, -73.9301). Same weather for all stops.

**ETA behavior:** Minutes are floored (not rounded). Past-departure trains clamp to 0.

**Line colors:** Hardcoded dict of official MTA hex codes for all 13 routes. Fallback gray (`888888`) for unknown routes.

---

## Running Locally

```bash
cd metro_api
poetry install
poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## CI/CD

GitHub Actions (`.github/workflows/deploy.yml`):
1. Build → push to `docker.nyc.xelaxer.com/nyc_metro_eta:<sha>` + `latest`
2. Deploy via `kubectl set image` on self-hosted runner in `fort` namespace
3. Auto-rollback on failure

After any CI deploy, manual `helm upgrade` needs `--force-conflicts` (field manager conflict).

Test workflow (`.github/workflows/test.yml`): pytest on push/PR.

**Note:** test.yml runs on `master` branch — there may be a branch naming inconsistency with `main`.

---

## Docs

- `README.md` — project overview, quick start
- `metro_api/README.md` — API endpoint docs with request/response examples
- `DEPLOY.md` — k3s deployment steps
- `ARDUINO_SETUP.md` — hardware setup
- `NEXT_STEPS.md` — ESP32 7B board issue (wrong IO expander chip)

## Gotchas

- `config.py` and `env/.env` both exist but are **empty** — no env vars currently used; everything is hardcoded in `app.py`
- Arduino config format is `"feeds"` (array), not `"feed"` (singular) — old docs are wrong
- ESP32 7B board: must select "Waveshare ESP32-S3 7B" not generic board, uses proprietary IO expander at 0x24
