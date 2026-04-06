import re
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import LINE_COLORS, app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STOP_CONFIG = {
    "stops": [
        {
            "feeds": ["N"],
            "label": "39 Av",
            "directions": [
                {"label": "northbound", "stop_id": "R08N"},
                {"label": "southbound", "stop_id": "R08S"},
            ],
        }
    ]
}

MOCK_WEATHER_DATA = {
    "current": {
        "temperature_2m": 57.0,
        "precipitation": 0,
        "wind_speed_10m": 4.0,
        "wind_direction_10m": 180.0,
    },
    "daily": {
        "temperature_2m_max": [65.0],
        "temperature_2m_min": [41.0],
        "precipitation_probability_max": [3],
    },
}


def make_mock_feed(stop_id: str, route_id: str, eta_minutes: int):
    stop_time = MagicMock()
    stop_time.stop_id = stop_id
    stop_time.departure = datetime.now() + timedelta(minutes=eta_minutes, seconds=30)

    trip = MagicMock()
    trip.route_id = route_id
    trip.headsign_text = "Astoria-Ditmars Blvd"
    trip.trip_id = f"test_{route_id}_{eta_minutes}"
    trip.stop_time_updates = [stop_time]

    feed = MagicMock()
    feed.trips = [trip]
    return feed


@pytest.fixture
def mock_weather():
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_WEATHER_DATA
    mock_response.raise_for_status = MagicMock()

    with patch("app.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        yield mock_client


@pytest.fixture
def mock_feed():
    with patch("app.NYCTFeed") as mock:
        mock.return_value = make_mock_feed("R08N", "N", 5)
        yield mock


# ---------------------------------------------------------------------------
# Endpoint: POST /api/eta
# ---------------------------------------------------------------------------

async def test_eta_response_shape(mock_feed, mock_weather):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/eta", json=STOP_CONFIG)

    assert response.status_code == 200
    data = response.json()
    assert "updated_at" in data
    assert "stops" in data
    assert "weather" in data


async def test_eta_stop_shape(mock_feed, mock_weather):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/eta", json=STOP_CONFIG)

    stop = response.json()["stops"][0]
    assert stop["label"] == "39 Av"
    assert isinstance(stop["directions"], list)


async def test_eta_train_fields(mock_feed, mock_weather):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/eta", json=STOP_CONFIG)

    northbound = next(
        d for d in response.json()["stops"][0]["directions"]
        if d["label"] == "northbound"
    )
    assert len(northbound["trains"]) == 1
    train = northbound["trains"][0]
    assert train["line"] == "N"
    assert train["color"] == LINE_COLORS["N"]
    assert train["dest"] == "Astoria-Ditmars Blvd"
    assert train["eta_min"] == 5
    assert "departs_at" in train
    assert re.match(r"^\d{2}:\d{2}$", train["departs_at"])
    assert "trip_id" in train


async def test_eta_empty_direction_when_no_trains(mock_feed, mock_weather):
    # Feed only has a northbound train; southbound bucket should be empty
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/eta", json=STOP_CONFIG)

    southbound = next(
        d for d in response.json()["stops"][0]["directions"]
        if d["label"] == "southbound"
    )
    assert southbound["trains"] == []


async def test_eta_sorts_by_eta(mock_weather):
    with patch("app.NYCTFeed") as mock:
        feed = MagicMock()
        feed.trips = [
            _trip("R08N", "N", 9),
            _trip("R08N", "N", 3),
            _trip("R08N", "N", 6),
        ]
        mock.return_value = feed

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/eta", json=STOP_CONFIG)

    trains = response.json()["stops"][0]["directions"][0]["trains"]
    etas = [t["eta_min"] for t in trains]
    assert etas == sorted(etas)


async def test_eta_caps_at_three_trains(mock_weather):
    with patch("app.NYCTFeed") as mock:
        feed = MagicMock()
        feed.trips = [_trip("R08N", "N", i) for i in range(1, 6)]
        mock.return_value = feed

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/eta", json=STOP_CONFIG)

    trains = response.json()["stops"][0]["directions"][0]["trains"]
    assert len(trains) == 3


async def test_eta_unknown_line_gets_fallback_color(mock_weather):
    with patch("app.NYCTFeed") as mock:
        feed = MagicMock()
        feed.trips = [_trip("R08N", "X", 5)]  # "X" not in LINE_COLORS
        mock.return_value = feed

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/eta", json=STOP_CONFIG)

    train = response.json()["stops"][0]["directions"][0]["trains"][0]
    assert train["color"] == "888888"


async def test_eta_weather_shape(mock_feed, mock_weather):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/eta", json=STOP_CONFIG)

    weather = response.json()["weather"]
    assert weather["current_temp_f"] == 57
    assert weather["high_f"] == 65
    assert weather["low_f"] == 41
    assert weather["rain_chance_pct"] == 3
    assert weather["wind_mph"] == 4
    assert weather["wind_dir"] == "S"


async def test_eta_invalid_body_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/eta", json={"bad": "body"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint: GET /health
# ---------------------------------------------------------------------------

def test_health():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "time" in data
    assert "cache" in data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trip(stop_id: str, route_id: str, eta_minutes: int) -> MagicMock:
    stop_time = MagicMock()
    stop_time.stop_id = stop_id
    stop_time.departure = datetime.now() + timedelta(minutes=eta_minutes, seconds=30)

    trip = MagicMock()
    trip.route_id = route_id
    trip.headsign_text = "Astoria-Ditmars Blvd"
    trip.trip_id = f"test_{route_id}_{eta_minutes}"
    trip.stop_time_updates = [stop_time]
    return trip
