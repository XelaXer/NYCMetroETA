from datetime import datetime, timedelta

from app import _eta_minutes, _wind_direction


def test_eta_minutes_future():
    future = datetime.now() + timedelta(minutes=5)
    assert _eta_minutes(future) == 5


def test_eta_minutes_past_clamps_to_zero():
    past = datetime.now() - timedelta(minutes=2)
    assert _eta_minutes(past) == 0


def test_wind_direction_cardinal():
    assert _wind_direction(0) == "N"
    assert _wind_direction(90) == "E"
    assert _wind_direction(180) == "S"
    assert _wind_direction(270) == "W"


def test_wind_direction_intercardinal():
    assert _wind_direction(45) == "NE"
    assert _wind_direction(135) == "SE"
    assert _wind_direction(225) == "SW"
    assert _wind_direction(315) == "NW"


def test_wind_direction_wraps():
    assert _wind_direction(360) == "N"
