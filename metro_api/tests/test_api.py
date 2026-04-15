import re
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import LINE_COLORS, _STOPS_INDEX, _load_stops_index, app

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
# Endpoint: GET /api/stops
# ---------------------------------------------------------------------------

# Minimal fake stops index: two directional stops sharing a parent, one orphan.
FAKE_STOPS_INDEX = {
    "R08N": {"name": "39 Av", "parent_id": "R08"},
    "R08S": {"name": "39 Av", "parent_id": "R08"},
    "G21S": {"name": "Queens Plaza", "parent_id": "G21"},
}


def _make_stops_feed(*stop_route_pairs):
    """Build a mock NYCTFeed whose trips cover the given (stop_id, route_id) pairs."""
    feed = MagicMock()
    feed.trips = [_trip(stop_id, route_id, 5) for stop_id, route_id in stop_route_pairs]
    return feed


@pytest.fixture
def mock_all_feeds():
    """Patch NYCTFeed and _STOPS_INDEX so /api/stops is fully hermetic."""
    feed = _make_stops_feed(("R08N", "N"), ("R08N", "W"), ("R08S", "N"), ("G21S", "E"))
    with patch("app.NYCTFeed", return_value=feed), \
         patch("app._STOPS_INDEX", FAKE_STOPS_INDEX):
        yield


async def test_stops_status_ok(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/stops")
    assert response.status_code == 200


async def test_stops_response_is_list(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = (await client.get("/api/stops")).json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_stops_station_shape(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stations = (await client.get("/api/stops")).json()
    station = stations[0]
    assert "stop_id" in station
    assert "name" in station
    assert "directions" in station
    assert isinstance(station["directions"], list)


async def test_stops_direction_shape(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stations = (await client.get("/api/stops")).json()
    direction = stations[0]["directions"][0]
    assert "stop_id" in direction
    assert "lines" in direction
    assert "colors" in direction


async def test_stops_grouped_by_parent(mock_all_feeds):
    # R08N and R08S share parent R08 — should appear as one station with two directions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stations = (await client.get("/api/stops")).json()
    r08 = next((s for s in stations if s["stop_id"] == "R08"), None)
    assert r08 is not None
    dir_ids = {d["stop_id"] for d in r08["directions"]}
    assert dir_ids == {"R08N", "R08S"}


async def test_stops_name_from_static_index(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stations = (await client.get("/api/stops")).json()
    r08 = next(s for s in stations if s["stop_id"] == "R08")
    assert r08["name"] == "39 Av"


async def test_stops_lines_sorted(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stations = (await client.get("/api/stops")).json()
    r08 = next(s for s in stations if s["stop_id"] == "R08")
    northbound = next(d for d in r08["directions"] if d["stop_id"] == "R08N")
    assert northbound["lines"] == sorted(northbound["lines"])


async def test_stops_lines_correct(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stations = (await client.get("/api/stops")).json()
    r08 = next(s for s in stations if s["stop_id"] == "R08")
    northbound = next(d for d in r08["directions"] if d["stop_id"] == "R08N")
    assert set(northbound["lines"]) == {"N", "W"}


async def test_stops_colors_match_lines(mock_all_feeds):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stations = (await client.get("/api/stops")).json()
    r08 = next(s for s in stations if s["stop_id"] == "R08")
    northbound = next(d for d in r08["directions"] if d["stop_id"] == "R08N")
    assert set(northbound["colors"].keys()) == set(northbound["lines"])
    assert northbound["colors"]["N"] == LINE_COLORS["N"]


async def test_stops_unknown_line_gets_fallback_color(mock_all_feeds):
    # Feed a stop with a route not in LINE_COLORS
    feed = _make_stops_feed(("R08N", "X99"))
    with patch("app.NYCTFeed", return_value=feed), \
         patch("app._STOPS_INDEX", FAKE_STOPS_INDEX):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            stations = (await client.get("/api/stops")).json()
    r08 = next(s for s in stations if s["stop_id"] == "R08")
    northbound = next(d for d in r08["directions"] if d["stop_id"] == "R08N")
    assert northbound["colors"]["X99"] == "888888"


async def test_stops_unrecognised_stop_id_skipped():
    # A feed returning a stop_id absent from _STOPS_INDEX should be silently dropped
    feed = _make_stops_feed(("ZZZZ", "N"))
    with patch("app.NYCTFeed", return_value=feed), \
         patch("app._STOPS_INDEX", FAKE_STOPS_INDEX):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            stations = (await client.get("/api/stops")).json()
    assert all(s["stop_id"] != "ZZZ" for s in stations)


async def test_stops_result_cached(mock_all_feeds):
    # NYCTFeed should only be called once across two requests (cache hit on second)
    with patch("app.NYCTFeed") as mock_feed_cls:
        mock_feed_cls.return_value = _make_stops_feed(("R08N", "N"))
        with patch("app._STOPS_INDEX", FAKE_STOPS_INDEX):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.get("/api/stops")
                await client.get("/api/stops")
    # 10 feeds fetched on first call, zero on second
    assert mock_feed_cls.call_count == len(__import__("app").ALL_FEEDS)


# ---------------------------------------------------------------------------
# Static stops index
# ---------------------------------------------------------------------------

def test_load_stops_index_returns_directional_stops():
    index = _load_stops_index()
    # All entries should be directional (have a non-empty parent_id)
    assert all(v["parent_id"] for v in index.values())


def test_load_stops_index_excludes_parent_stations():
    index = _load_stops_index()
    # Parent station rows have bare numeric/alpha IDs with no N/S suffix and no parent_id;
    # spot-check that the bare parent IDs are not keys in the index
    assert "R08" not in index   # parent of 39 Av
    assert "R08N" in index
    assert "R08S" in index


def test_load_stops_index_name_populated():
    index = _load_stops_index()
    assert index["R08N"]["name"] == "39 Av-Dutch Kills"


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
