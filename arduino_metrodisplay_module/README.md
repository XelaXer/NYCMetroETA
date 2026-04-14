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
| Touch | Capacitive 5-point (not used for UI interaction) |
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

Once step 2 passes, the full UI should render: 3 train columns + weather strip.
The display updates every 30 seconds automatically.

---

## Display layout

```
┌─────────────────────┬─────────────────────┬──────────────────────┐
│       39 Av         │    Queens Plaza      │  Queensboro Plaza    │
├─────────────────────┼─────────────────────┼──────────────────────┤
│  Northbound  ^      │  v  Southbound       │  <  Westbound        │
│  [N] Astoria  3 min │  [E] WTC      2 min  │  [7] Hudson Yd 1 min │
│  [N] Astoria  9 min │  [R] WTC      5 min  │  [7] Hudson Yd 6 min │
│  [N] Astoria 16 min │  [E] WTC     12 min  │  [7] Hudson Yd 11min │
│                     │                     │                      │
│  v  Southbound      │                     │  Northbound  ^       │
│  [N] Coney Is 5 min │                     │  [N] Astoria  4 min  │
│  [N] Coney Is 11min │                     │  [W] Astoria  9 min  │
│  [N] Coney Is 18min │                     │                      │
│                     │                     │  v  Southbound       │
│                     │                     │  [N] Coney Is 7 min  │
│                     │                     │  [W] Coney Is 14min  │
├─────────────────────┴─────────────────────┴──────────────────────┤
│    57°F     H 65°  /  L 41°     Rain 3%     Wind 4 mph S         │
└──────────────────────────────────────────────────────────────────┘
```

Line badges are colored with MTA official hex colors (provided by the API).
Yellow lines (N/Q/R/W) automatically get black badge text for readability.

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
