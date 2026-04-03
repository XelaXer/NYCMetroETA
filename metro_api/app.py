"""
NYC Metro ETA — FastAPI backend
Serves /api/eta with real-time train ETAs and current weather for the Arduino display.

Run with:
    poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""

from datetime import datetime, timedelta

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
# Helpers
# ---------------------------------------------------------------------------

def _eta_minutes(t: datetime) -> int:
    return max(0, round((t - datetime.now()).total_seconds() / 60))


def _wind_direction(degrees: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(degrees / 45) % 8]


# ---------------------------------------------------------------------------
# Transit fetchers
# ---------------------------------------------------------------------------

def fetch_n_trains_39av(n: int = 3) -> dict:
    """Next N trains at 39 Av in both directions."""
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


def fetch_e_trains_queens_plaza(n: int = 3) -> dict:
    """Next E trains southbound at Queens Plaza."""
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


def fetch_7_trains_queensboro(n: int = 3) -> dict:
    """Next 7 trains westbound (downtown) at Queensboro Plaza."""
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


async def fetch_weather() -> dict:
    """Current conditions + daily high/low/precip from Open-Meteo (no API key needed)."""
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
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/eta")
async def get_eta():
    """
    Single endpoint polled by the Arduino display every 30 seconds.
    Transit data is fetched synchronously (nyct-gtfs is blocking);
    weather is fetched async. Both run on every request — add caching
    here if you want to reduce upstream calls.
    """
    weather = await fetch_weather()

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "stops": {
            "n_39th_ave": fetch_n_trains_39av(3),
            "e_queens_plaza": fetch_e_trains_queens_plaza(3),
            "seven_queensboro": fetch_7_trains_queensboro(3),
        },
        "weather": weather,
    }


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat(timespec="seconds")}
