# NYC Metro Display Module — Requirements

A standalone ESP32-based physical display unit that shows real-time subway ETAs
for a fixed set of commute stops plus current weather conditions.

---

## Hardware Target

- **Microcontroller**: ESP32-S3 (WiFi required for live data)
- **Display**: 5" TFT, 800×480 resolution, RGB parallel interface
- **Recommended boards**:
  - Sunton ESP32-S3 5" (budget, AliExpress, ~$20–25)
  - Makerfabs ESP32-S3 5" Parallel TFT (~$35)
  - Waveshare ESP32-S3 Touch LCD 4.3" (smaller but polished, ~$30)
- **UI library**: LVGL (v8 or v9)

---

## Transit Display Requirements

### Panel 1 — N Train at 39th Ave (Sunnyside/Jackson Heights, Queens)

- Show next **3 departures in each direction**:
  - **Northbound** toward Astoria-Ditmars Blvd
  - **Southbound** toward Manhattan / Coney Island
- Display format per train: `line badge | destination | ETA (min)` or arrival time
- Data source: MTA GTFS-RT feed (N/W/R/Q line)
- GTFS stop: `39 Av` on the N/W line (stop ID to be confirmed via `find_stop_ids()`)

### Panel 2 — E Train at Queens Plaza (Queens)

- Show next **3 southbound (downtown) departures**
  - Direction: toward World Trade Center / Jamaica
- Display format: `line badge | destination | ETA (min)`
- Data source: MTA GTFS-RT feed (E/F/M/R line)
- GTFS stop: `Queens Plaza` on the E/M/R line (stop ID to be confirmed)

### Panel 3 — 7 Train at Queensboro Plaza (Queens)

- Show next **3 westbound (downtown) departures**
  - Direction: toward Hudson Yards / 34 St
- Display format: `line badge | destination | ETA (min)`
- Data source: MTA GTFS-RT feed (7 line)
- GTFS stop: `Queensboro Plaza` on the 7 line (stop ID to be confirmed)

---

## Weather Display Requirements

- **Collapsed/compact panel** — does not dominate the layout
- Show:
  - Current temperature (°F)
  - Daily high / low (°F)
  - Precipitation probability or rain indicator
  - Wind speed (mph) and direction
- Update interval: every 10–15 minutes (weather changes slowly)
- Data source: Open-Meteo API (free, no API key required) or OpenWeatherMap
- Location: Queens, NY (lat/lon hardcoded)

---

## Display Layout (800×480)

```
+------------------+------------------+-------------------+
|   N — 39th Ave   |  E — Queens Plz  | 7 — Queensboro Plz|
|                  |                  |                   |
|  [N] Astoria     |  [E] WTC  2 min  | [7] Hudson Yd 1min|
|     3 min        |  [E] WTC  8 min  | [7] Hudson Yd 6min|
|  [N] Astoria     |  [E] WTC 14 min  | [7] Hudson Yd 11mn|
|     9 min        |                  |                   |
|  [N] Astoria     |                  |                   |
|    16 min        |                  |                   |
|                  |                  |                   |
|  [N] Coney Is    |                  |                   |
|     5 min        |                  |                   |
|  [N] Coney Is    |                  |                   |
|    11 min        |                  |                   |
|  [N] Coney Is    |                  |                   |
|    18 min        |                  |                   |
+------------------+------------------+-------------------+
|  NOW 54°F   HIGH 61°F   LOW 48°F   Rain 20%   Wind 9mph NW  |
+-------------------------------------------------------------+
```

---

## Data Refresh Intervals

| Data | Interval |
|---|---|
| Transit ETAs | Every 30 seconds |
| Weather | Every 10 minutes |

---

## Communication Architecture

Two options under consideration:

**Option A — Direct ESP32 fetch** (simpler, self-contained)
- ESP32 calls MTA GTFS-RT feeds directly over WiFi
- ESP32 calls weather API directly
- No dependency on the Python `metro_api` backend
- Con: protobuf parsing on ESP32 is non-trivial

**Option B — Python API backend + ESP32 client** (preferred)
- `metro_api` Python backend parses GTFS-RT and exposes a simple JSON REST endpoint
- ESP32 polls the JSON endpoint every 30s — much simpler parsing on device
- Weather can be fetched by backend or device directly
- Allows logic changes without re-flashing the device

**Recommendation**: Option B. The Python backend already has working GTFS-RT parsing logic.
The ESP32 should only be responsible for rendering, not feed parsing.

---

## JSON API Contract (Option B — proposed)

`GET /api/eta` response shape:

```json
{
  "updated_at": "2026-04-03T14:32:00",
  "stops": {
    "n_39th_ave": {
      "northbound": [
        { "line": "N", "destination": "Astoria-Ditmars Blvd", "eta_min": 3 },
        { "line": "N", "destination": "Astoria-Ditmars Blvd", "eta_min": 9 }
      ],
      "southbound": [
        { "line": "N", "destination": "Coney Island", "eta_min": 5 },
        { "line": "N", "destination": "Coney Island", "eta_min": 11 }
      ]
    },
    "e_queens_plaza": {
      "southbound": [
        { "line": "E", "destination": "World Trade Center", "eta_min": 2 },
        { "line": "E", "destination": "World Trade Center", "eta_min": 8 }
      ]
    },
    "seven_queensboro": {
      "westbound": [
        { "line": "7", "destination": "Hudson Yards", "eta_min": 1 },
        { "line": "7", "destination": "Hudson Yards", "eta_min": 6 }
      ]
    }
  },
  "weather": {
    "current_temp_f": 54,
    "high_f": 61,
    "low_f": 48,
    "rain_chance_pct": 20,
    "wind_mph": 9,
    "wind_dir": "NW"
  }
}
```

---

## Open Items

- [ ] Confirm GTFS stop IDs for all three stations via `find_stop_ids()`
- [ ] Choose hardware board and order
- [ ] Decide Option A vs Option B architecture
- [ ] Implement `/api/eta` JSON endpoint in `metro_api` (if Option B)
- [ ] Implement ESP32 sketch: WiFi connect, HTTP GET, JSON parse, LVGL render
- [ ] Design LVGL layout (line color badges, ETA countdown, weather strip)
- [ ] Set up OTA (over-the-air) firmware updates for convenience
