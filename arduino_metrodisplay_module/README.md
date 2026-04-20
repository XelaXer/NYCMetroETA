# NYC Metro Display — Arduino

ESP32-S3 firmware for the 7" subway ETA display. Polls the `metro_api` backend
every 30 seconds, parses the JSON response, and renders train ETAs + weather
via LVGL.

---

## Hardware

**Waveshare ESP32-S3-Touch-LCD-7B**

| Spec | Detail |
|---|---|
| MCU | ESP32-S3R8 — dual-core 240MHz, 8MB PSRAM |
| Display | 7" IPS TFT, 1024×600, RGB parallel 16-bit |
| Touch | Capacitive 5-point (GT911) — used for taskbar buttons |
| WiFi | 802.11 b/g/n 2.4GHz |
| USB | USB-C — programming + power + Serial |

The 8MB PSRAM is required: a 1024×600 16-bit framebuffer is ~750KB, which
doesn't fit in internal SRAM alone.

---

## Sketch structure

```
metro_display/
├── metro_display.ino   # setup, loop, WiFi, HTTP poll
├── config.h            # WiFi credentials, API host, stop config JSON
├── display.h           # Waveshare board driver + LVGL flush callback
└── ui.h                # LVGL layout, widget builders, ui_update()
```

**`config.h` is the only file you need to edit before flashing.**
Set your WiFi credentials, the IP of the machine running `metro_api`, and
optionally adjust the stop config JSON (same format as `config.json`).

---

## Setup

### 1. Arduino IDE board config

```
Board:            ESP32S3 Dev Module
Flash Size:       16MB (or match board)
PSRAM:            OPI PSRAM          ← required
Partition Scheme: Huge APP (3MB No OTA / 1MB SPIFFS)
Upload Speed:     921600
USB CDC On Boot:  Enabled            ← Serial over USB-C without adapter
```

### 2. Install libraries (Library Manager)

| Library | Version | Notes |
|---|---|---|
| LVGL | 8.3.x | Pin to v8 — do not install v9 |
| ArduinoJson | 7.x | |
| ESP32_Display_Panel | latest | Waveshare board driver |

### 3. LVGL config

Copy the template and place it where Arduino can find it:
```bash
cp ~/Arduino/libraries/lvgl/lv_conf_template.h ~/Arduino/libraries/lv_conf.h
```

Required settings in `lv_conf.h`:
```c
#define LV_COLOR_DEPTH        16
#define LV_USE_FLEX            1
#define LV_FONT_MONTSERRAT_12  1
#define LV_FONT_MONTSERRAT_14  1
#define LV_FONT_MONTSERRAT_16  1
```

### 4. Edit `config.h`

```cpp
const char* WIFI_SSID     = "your-ssid";
const char* WIFI_PASSWORD = "your-password";
const char* API_HOST      = "192.168.1.xxx";  // IP of machine running metro_api
```

---

## Testing sequence

### Step 1 — Smoke test: does the display light up?

Flash `metro_display.ino` as-is (before WiFi is configured). You should see
a dark screen with a "Connecting to WiFi..." status label. This confirms the
display driver and LVGL are working.

If the screen stays white or blank:
- Check PSRAM is set to `OPI PSRAM` in board config
- Check the `ESP32_Display_Panel` library is installed

### Step 2 — WiFi + API test

Set your credentials and `API_HOST` in `config.h`. Make sure `metro_api` is
running on the target machine:

```bash
cd metro_api
poetry run uvicorn app:app --host 0.0.0.0 --port 8000
```

Flash and open Serial Monitor at **115200 baud**. Expected output:

```
NYC Metro Display — boot
display: init OK (1024x600)
ui: init OK
WiFi: connecting to your-ssid
WiFi: connected — 192.168.1.xxx
fetch: OK  updated_at=2026-04-04T12:00:00
ui: updated (3 stops)
```

If you see `HTTP -1` or a connection error:
- Confirm the PC and ESP32 are on the same network
- Check `API_HOST` is the correct IP (not `localhost`)
- Check firewall isn't blocking port 8000

### Step 3 — Full display

Once step 2 passes, the full UI should render: 3 train columns (39 Av,
Queens Plaza, Queensboro Plaza + Court Square) with ETA pill rows, and the
taskbar at the bottom. The display updates every 30 seconds automatically, or
immediately when the `[↻]` button is tapped.

---

## Display layout

Screen: **1024 × 600** landscape. Three equal columns (341px each) for transit
data, with a 55px taskbar along the bottom.

```
┌───────────────────────┬───────────────────────┬───────────────────────┐ ↑
│  39 Av                │  Queens Plaza         │  Queensboro Plaza     │ │
│  ─────────────────    │  ─────────────────    │  ─────────────────    │ │
│  ^ Northbound         │  v Southbound         │  < Westbound          │ │
│  [N] Astoria  1  9 m  │  [E] Jamaica  2  8 15 │  [7] 34 St  0   4   7 │ 5
│  [N] Coney   23 32 m  │  [N] Whitehall 4 17 26│                       │ 4
│                       │  [W] Astoria   9 20 27│  ^ Northbound         │ 5
│  v Southbound         │                       │  [N] Astoria  1  13   │ p
│  [N] Whitehall 5 18 m │                       │                       │ x
│  [N] Astoria   9 22 m │                       │  v Southbound         │ │
│                       │                       │  [N] Whitehall 5  18  │ │
│                       │                       │                       │ │
│                       │                       │  ── Court Square ──   │ │
│                       │                       │  v Southbound         │ │
│                       │                       │  [G] Church Av 3 11 18│ ↓
├───────────────────────┴───────────────────────┴───────────────────────┤ ↑
│  82°F   H:85° / L:71°   Rain 5%   Wind 8 mph SW      [ ↻ ]  [ ↕ ]  │ 55px
└───────────────────────────────────────────────────────────────────────┘
```

**Column assignments** (hardcoded to match `CONFIG_JSON` stop order):

| Column | Stop | Lines | Directions |
|--------|------|-------|------------|
| 0 | 39 Av | N | northbound, southbound |
| 1 | Queens Plaza | E, N | southbound |
| 2 | Queensboro Plaza + Court Square | 7, N / G | westbound, northbound, southbound / southbound |

**ETA pills:** up to 3 upcoming times per line+destination row. `0 min` shows
"Now". Trains with the same line and destination are grouped into a single row.
Line badges use MTA official hex colors (provided by the API); yellow lines
(N/Q/R/W) automatically get black badge text for contrast.

**Bottom taskbar:**
- Left: weather summary (temp, high/low, rain %, wind)
- Right: two touchscreen buttons
  - `[↻]` — force an immediate data refresh (skips the 30-second wait)
  - `[↕]` — flip the display 180° (software rotation via LVGL); useful when
    the device is mounted upside-down. State resets on power cycle.

---

## Common issues

| Symptom | Fix |
|---|---|
| White/blank screen | Set PSRAM to `OPI PSRAM` in board config |
| Board not detected as serial port | Enable `USB CDC On Boot`; if needed, hold BOOT + tap RESET |
| `HTTP -1` | Wrong `API_HOST`, or ESP32 and server on different networks |
| LVGL crashes / corrupted display | Confirm `LV_USE_FLEX 1` and fonts enabled in `lv_conf.h` |
| Sketch too large to flash | Set partition scheme to `Huge APP` |
| `PSRAM alloc failed` in Serial | PSRAM not enabled in board config |

---

## Stop config

Stops are defined in `config.h` as `CONFIG_JSON` — the same JSON that gets
POSTed to the API on every poll. To change stops: edit `CONFIG_JSON` and reflash.
The API has no hardcoded stops; it fetches whatever the device requests.

The `config.json` in this directory is the canonical copy for reference.
`config.h` mirrors it as a C string literal.
