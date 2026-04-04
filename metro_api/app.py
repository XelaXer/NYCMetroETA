"""
NYC Metro ETA — FastAPI backend
Serves POST /api/eta with real-time train ETAs and current weather for the Arduino display.
The Arduino sends its stop config as the request body; the API fetches only those stops.

Run with:
    poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload

curl test:
    curl -s -X POST http://localhost:8000/api/eta \
      -H "Content-Type: application/json" \
      -d @../arduino_metrodisplay_module/config.json | python3 -m json.tool
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import FastAPI
from nyct_gtfs import NYCTFeed
from pydantic import BaseModel

app = FastAPI(title="NYC Metro ETA")

# MTA official hex colors per route
LINE_COLORS = {
    "1": "EE352E", "2": "EE352E", "3": "EE352E",
    "4": "00933C", "5": "00933C", "6": "00933C",
    "7": "B933AD",
    "A": "0039A6", "C": "0039A6", "E": "0039A6",
    "B": "FF6319", "D": "FF6319", "F": "FF6319", "M": "FF6319",
    "G": "6CBE45",
    "J": "996633", "Z": "996633",
    "L": "A7A9AC",
    "N": "FCCC0A", "Q": "FCCC0A", "R": "FCCC0A", "W": "FCCC0A",
    "SI": "0039A6",
}

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
# Request models
# ---------------------------------------------------------------------------

class DirectionConfig(BaseModel):
    label: str
    stop_id: str  # full GTFS stop ID including direction suffix (e.g. "R08N")

class StopConfig(BaseModel):
    feeds: list[str]
    label: str
    directions: list[DirectionConfig]

class ETARequest(BaseModel):
    stops: list[StopConfig]

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
# Transit fetcher (blocking — run in executor)
# ---------------------------------------------------------------------------

def _fetch_stop(stop: StopConfig, n: int = 3) -> dict:
    now = datetime.now()

    stop_id_to_dir = {d.stop_id: d.label for d in stop.directions}
    buckets: dict[str, list] = {d.label: [] for d in stop.directions}

    for feed_id in stop.feeds:
        feed = NYCTFeed(feed_id)
        for trip in feed.trips:
            for stop_time in trip.stop_time_updates:
                if stop_time.stop_id in stop_id_to_dir and stop_time.departure and stop_time.departure > now:
                    direction = stop_id_to_dir[stop_time.stop_id]
                    buckets[direction].append({
                        "line": trip.route_id,
                        "color": LINE_COLORS.get(trip.route_id, "888888"),
                        "dest": trip.headsign_text,
                        "eta_min": _eta_minutes(stop_time.departure),
                        "trip_id": trip.trip_id,
                    })
                    break  # one departure per trip

    for label in buckets:
        buckets[label].sort(key=lambda x: x["eta_min"])
        buckets[label] = buckets[label][:n]

    return {
        "label": stop.label,
        "directions": [
            {"label": label, "trains": trains}
            for label, trains in buckets.items()
        ],
    }


# ---------------------------------------------------------------------------
# Weather fetcher (async)
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

async def get_transit(request: ETARequest) -> list:
    cache_key = "transit_" + hashlib.md5(request.model_dump_json().encode()).hexdigest()
    cached = _cache_get(cache_key, TRANSIT_TTL)
    if cached is not None:
        return cached

    loop = asyncio.get_event_loop()
    results = await asyncio.gather(*[
        loop.run_in_executor(None, _fetch_stop, stop)
        for stop in request.stops
    ])

    result = list(results)
    _cache_set(cache_key, result)
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

@app.post("/api/eta")
async def get_eta(request: ETARequest):
    """
    Polled by the Arduino display every 30 seconds.
    Body: JSON config listing stops and directions to fetch.
    Transit data cached 1 min per unique config, weather cached 3 min.
    All stop feed fetches run concurrently in a thread pool.
    """
    stops, weather = await asyncio.gather(get_transit(request), get_weather())

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "stops": stops,
        "weather": weather,
    }


@app.get("/health")
def health():
    cached_transit = any(k.startswith("transit_") for k in _cache)
    cached_weather = "weather" in _cache
    return {
        "status": "ok",
        "time": datetime.now().isoformat(timespec="seconds"),
        "cache": {"transit": cached_transit, "weather": cached_weather},
    }
