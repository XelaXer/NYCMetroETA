"""
NYC Metro ETA — FastAPI backend
Serves /api/eta with real-time train ETAs and current weather for the Arduino display.

Run with:
    poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import FastAPI
from nyct_gtfs import NYCTFeed

app = FastAPI(title="NYC Metro ETA")

# ---------------------------------------------------------------------------
# Stop IDs (MTA GTFS static data — verify via scripts/test.py find_stop_ids
# if any stop appears to return no results)
# ---------------------------------------------------------------------------

# N/W line — 39 Av, Astoria (Queens)
N_39AV_NORTHBOUND = "R11N"   # toward Astoria-Ditmars Blvd
N_39AV_SOUTHBOUND = "R11S"   # toward Manhattan / Coney Island

# E/M/R line — Queens Plaza (Queens)
E_QUEENS_PLAZA_S = "G08S"    # southbound toward World Trade Center

# 7 line — Queensboro Plaza (Queens)
SEVEN_QUEENSBORO_S = "723S"  # westbound toward Hudson Yards

# Open-Meteo — Long Island City / Astoria, Queens
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=40.7282&longitude=-73.9301"
    "&current=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph"
    "&timezone=America%2FNew_York&forecast_days=1"
)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

TRANSIT_TTL = timedelta(minutes=1)
WEATHER_TTL = timedelta(minutes=3)

_cache: dict[str, tuple[datetime, Any]] = {}


def _cache_get(key: str, ttl: timedelta) -> Any | None:
    if key in _cache:
        ts, value = _cache[key]
        if datetime.now() - ts < ttl:
            return value
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (datetime.now(), value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eta_minutes(t: datetime) -> int:
    return max(0, round((t - datetime.now()).total_seconds() / 60))


def _wind_direction(degrees: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(degrees / 45) % 8]


# ---------------------------------------------------------------------------
# Transit fetchers (blocking — run in executor to avoid blocking event loop)
# ---------------------------------------------------------------------------

def _fetch_n_trains_39av(n: int = 3) -> dict:
    feed = NYCTFeed("N")
    now = datetime.now()
    northbound, southbound = [], []

    for trip in feed.trips:
        if trip.route_id != "N":
            continue
        for stop in trip.stop_time_updates:
            if stop.stop_id == N_39AV_NORTHBOUND and stop.departure and stop.departure > now:
                northbound.append({
                    "line": "N",
                    "destination": trip.headsign_text,
                    "eta_min": _eta_minutes(stop.departure),
                })
                break
            if stop.stop_id == N_39AV_SOUTHBOUND and stop.departure and stop.departure > now:
                southbound.append({
                    "line": "N",
                    "destination": trip.headsign_text,
                    "eta_min": _eta_minutes(stop.departure),
                })
                break

    northbound.sort(key=lambda x: x["eta_min"])
    southbound.sort(key=lambda x: x["eta_min"])
    return {"northbound": northbound[:n], "southbound": southbound[:n]}


def _fetch_e_trains_queens_plaza(n: int = 3) -> dict:
    feed = NYCTFeed("E")
    now = datetime.now()
    southbound = []

    for trip in feed.trips:
        if trip.route_id != "E":
            continue
        for stop in trip.stop_time_updates:
            if stop.stop_id == E_QUEENS_PLAZA_S and stop.departure and stop.departure > now:
                southbound.append({
                    "line": "E",
                    "destination": trip.headsign_text,
                    "eta_min": _eta_minutes(stop.departure),
                })
                break

    southbound.sort(key=lambda x: x["eta_min"])
    return {"southbound": southbound[:n]}


def _fetch_7_trains_queensboro(n: int = 3) -> dict:
    feed = NYCTFeed("7")
    now = datetime.now()
    westbound = []

    for trip in feed.trips:
        if trip.route_id != "7":
            continue
        for stop in trip.stop_time_updates:
            if stop.stop_id == SEVEN_QUEENSBORO_S and stop.departure and stop.departure > now:
                westbound.append({
                    "line": "7",
                    "destination": trip.headsign_text,
                    "eta_min": _eta_minutes(stop.departure),
                })
                break

    westbound.sort(key=lambda x: x["eta_min"])
    return {"westbound": westbound[:n]}


# ---------------------------------------------------------------------------
# Weather fetcher (already async)
# ---------------------------------------------------------------------------

async def _fetch_weather() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(WEATHER_URL)
        r.raise_for_status()
        data = r.json()

    current = data["current"]
    daily = data["daily"]

    return {
        "current_temp_f": round(current["temperature_2m"]),
        "high_f": round(daily["temperature_2m_max"][0]),
        "low_f": round(daily["temperature_2m_min"][0]),
        "rain_chance_pct": daily["precipitation_probability_max"][0],
        "wind_mph": round(current["wind_speed_10m"]),
        "wind_dir": _wind_direction(current["wind_direction_10m"]),
    }


# ---------------------------------------------------------------------------
# Cached accessors
# ---------------------------------------------------------------------------

async def get_transit() -> dict:
    cached = _cache_get("transit", TRANSIT_TTL)
    if cached is not None:
        return cached

    loop = asyncio.get_event_loop()
    n, e, seven = await asyncio.gather(
        loop.run_in_executor(None, _fetch_n_trains_39av),
        loop.run_in_executor(None, _fetch_e_trains_queens_plaza),
        loop.run_in_executor(None, _fetch_7_trains_queensboro),
    )

    result = {"n_39th_ave": n, "e_queens_plaza": e, "seven_queensboro": seven}
    _cache_set("transit", result)
    return result


async def get_weather() -> dict:
    cached = _cache_get("weather", WEATHER_TTL)
    if cached is not None:
        return cached

    result = await _fetch_weather()
    _cache_set("weather", result)
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/eta")
async def get_eta():
    """
    Polled by the Arduino display every 30 seconds.
    Transit data cached for 1 minute, weather cached for 3 minutes.
    All three MTA feed fetches run concurrently in a thread pool.
    """
    stops, weather = await asyncio.gather(get_transit(), get_weather())

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "stops": stops,
        "weather": weather,
    }


@app.get("/health")
def health():
    cached_transit = "transit" in _cache
    cached_weather = "weather" in _cache
    return {
        "status": "ok",
        "time": datetime.now().isoformat(timespec="seconds"),
        "cache": {"transit": cached_transit, "weather": cached_weather},
    }
