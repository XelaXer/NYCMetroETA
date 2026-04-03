# NYC Metro Display Module — Requirements

A standalone ESP32-based physical display unit that shows real-time subway ETAs
for a fixed set of commute stops plus current weather conditions.

---

## Hardware Target

### Selected Board — Waveshare ESP32-S3-Touch-LCD-7B

**The recommended board for this project.**

| Spec | Detail |
|---|---|
| MCU | ESP32-S3R8 (dual-core 240MHz, 8MB PSRAM) |
| Display | 7" IPS TFT, **1024×600**, capacitive 5-point touch |
| Interface | RGB parallel (16-bit) — required for 7" at usable refresh rates |
| WiFi | 802.11 b/g/n (2.4GHz) — built in |
| USB | USB-C (programming + power) |
| Storage | MicroSD card slot |
| Power | USB-C or LiPo battery connector |
| Price | ~$45–55 (Waveshare official store or AliExpress) |

**Why this board:**
- Best-documented 7" ESP32 option — Waveshare ships Arduino and ESP-IDF examples
- ESP32-S3's PSRAM is essential: a 7" 1024×600 16-bit framebuffer is ~750KB, which won't fit in internal SRAM alone
- LVGL has a dedicated driver config for this board in the community examples
- `esp_lcd` (ESP-IDF component, works in Arduino) handles the RGB panel driver natively
- All-in-one: no wiring, no mismatch between display and controller

**Search terms for ordering**: `Waveshare ESP32-S3 7inch Touch LCD` or part number `ESP32-S3-Touch-LCD-7B`

### Alternative Boards (if unavailable)

| Board | Size | Notes |
|---|---|---|
| Elecrow CrowPanel 7.0" ESP32 | 7" 1024×600 | Similar spec, slightly cheaper, good LVGL support |
| Sunton ESP32-S3 7" | 7" 1024×600 | Budget AliExpress option, same community drivers |
| Waveshare ESP32-S3-Touch-LCD-5B | 5" 1024×600 | Drop-down if 7" feels too large; identical software |

### UI Library

- **LVGL v8.3** (recommended over v9 for now — more Arduino examples exist for this board)
- `ArduinoJson` v7 for parsing the backend API response

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

## Display Layout (1024×600 — 7" screen)

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

## Hardware Setup & Testing Guide

### Prerequisites

1. **Arduino IDE 2.x** (recommended) or PlatformIO in VS Code
2. **ESP32 Arduino Core** — install via Boards Manager:
   - Add to Additional Boards URLs: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Install: `esp32 by Espressif Systems` (v3.x)
3. **Required libraries** — install via Library Manager:
   - `LVGL` by LVGL (v8.3.x — pin to v8, not v9)
   - `ArduinoJson` by Benoit Blanchon (v7.x)
   - `ESP32Time` by Felix Biego (for NTP clock sync)

### Board Configuration (Arduino IDE)

```
Board:              ESP32S3 Dev Module
Flash Size:         16MB (or match your board)
PSRAM:              OPI PSRAM  ← critical, enables the 8MB PSRAM
Partition Scheme:   Huge APP (3MB No OTA / 1MB SPIFFS)
Upload Speed:       921600
USB CDC On Boot:    Enabled  ← allows Serial over USB-C
```

### LVGL Configuration

Copy the LVGL config template into your sketch folder:

```bash
# From your Arduino libraries folder:
cp ~/Arduino/libraries/lvgl/lv_conf_template.h ~/Arduino/libraries/lv_conf.h
```

Then in `lv_conf.h`, set:
```c
#define LV_COLOR_DEPTH 16
#define LV_HOR_RES_MAX 1024
#define LV_VER_RES_MAX 600
#define LV_MEM_SIZE (512 * 1024U)   // 512KB — safe with PSRAM
```

### Step 1 — Smoke Test: Light Up the Display

Flash this minimal sketch first to verify the board and display are working before
adding any application logic:

```cpp
#include <Arduino.h>
#include <lvgl.h>
#include <ESP_Panel_Library.h>  // Waveshare ESP32-S3-Touch-LCD-7B driver

ESP_Panel *panel = nullptr;

static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[1024 * 20];  // 20-line draw buffer

void my_disp_flush(lv_disp_drv_t *drv, const lv_area_t *area, lv_color_t *color_p) {
    panel->getLcd()->drawBitmap(area->x1, area->y1,
                                 area->x2 - area->x1 + 1,
                                 area->y2 - area->y1 + 1,
                                 (uint16_t *)color_p);
    lv_disp_flush_ready(drv);
}

void setup() {
    Serial.begin(115200);
    panel = new ESP_Panel();
    panel->init();
    panel->begin();

    lv_init();
    lv_disp_draw_buf_init(&draw_buf, buf, NULL, 800 * 20);

    static lv_disp_drv_t disp_drv;
    lv_disp_drv_init(&disp_drv);
    disp_drv.hor_res  = 1024;
    disp_drv.ver_res  = 600;
    disp_drv.flush_cb = my_disp_flush;
    disp_drv.draw_buf = &draw_buf;
    lv_disp_drv_register(&disp_drv);

    // Draw a test label
    lv_obj_t *label = lv_label_create(lv_scr_act());
    lv_label_set_text(label, "NYC Metro Display - OK");
    lv_obj_align(label, LV_ALIGN_CENTER, 0, 0);

    Serial.println("Display init OK");
}

void loop() {
    lv_timer_handler();
    delay(5);
}
```

**Expected result**: white screen with "NYC Metro Display - OK" centered. If you see
this, the display, LVGL, and board are all working.

### Step 2 — WiFi + API Test

Once the display is working, verify WiFi and JSON fetching independently before
combining with the UI:

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* SSID     = "your-ssid";
const char* PASSWORD = "your-password";
const char* API_URL  = "http://YOUR_PC_IP:8000/api/eta";  // metro_api backend

void setup() {
    Serial.begin(115200);
    WiFi.begin(SSID, PASSWORD);
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.println("\nWiFi connected: " + WiFi.localIP().toString());

    HTTPClient http;
    http.begin(API_URL);
    int code = http.GET();
    if (code == 200) {
        JsonDocument doc;
        deserializeJson(doc, http.getString());
        Serial.println("First N train ETA: " +
            String(doc["stops"]["n_39th_ave"]["northbound"][0]["eta_min"].as<int>()) + " min");
    } else {
        Serial.println("HTTP error: " + String(code));
    }
    http.end();
}

void loop() {}
```

**Expected result**: Serial monitor prints the first N train ETA from your Python backend.

### Step 3 — Serial Monitor Debugging

- Open Serial Monitor at **115200 baud**
- USB CDC mode (set above) means no separate UART adapter needed — just the USB-C cable
- If the board doesn't appear as a COM/tty port, hold **BOOT button**, tap **RESET**, release BOOT

### Common Issues

| Symptom | Fix |
|---|---|
| Display white/blank after flash | Check PSRAM is set to `OPI PSRAM` in board config |
| Board not detected as serial port | Enable `USB CDC On Boot` in board settings |
| LVGL crashes or corrupts display | Reduce `LV_MEM_SIZE` or draw buffer size |
| HTTP request fails | Confirm PC and ESP32 are on same WiFi network; check firewall |
| Sketch too large | Switch partition scheme to `Huge APP` |

---

## Open Items

- [ ] Confirm GTFS stop IDs for all three stations via `find_stop_ids()`
- [x] Choose hardware board — **Waveshare ESP32-S3-Touch-LCD-7B** selected
- [x] Decide Option A vs Option B architecture — **Option B selected**
- [ ] Implement `/api/eta` JSON endpoint in `metro_api`
- [ ] Implement ESP32 sketch: WiFi connect, HTTP GET, JSON parse, LVGL render
- [ ] Design LVGL layout (line color badges, ETA countdown, weather strip)
- [ ] Set up OTA (over-the-air) firmware updates for convenience
