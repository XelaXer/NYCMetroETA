# Arduino Display Setup

Notes on getting the Waveshare ESP32-S3-Touch-LCD-7B flashed and running the metro display sketch.

---

## Hardware

**Board:** Waveshare ESP32-S3-Touch-LCD-7B, 1024×600 IPS, 16MB flash, 8MB OPI PSRAM

Two USB-C ports on the board:
- **UART** — goes through a CH343 USB-to-serial chip. Shows up as `/dev/cu.usbserial-*` on Mac. Use this for flashing.
- **USB** — native ESP32-S3 USB OTG. Shows up as `/dev/cu.usbmodem*`. Not suitable for flashing with the current sketch config.

Always flash via the **UART port**.

If upload fails with "No serial data received": hold **BOOT**, tap **RESET**, release **BOOT** to force download mode, then retry.

---

## Arduino IDE Board Settings

| Setting | Value |
|---|---|
| Board | **Waveshare ESP32S3 XIP** |
| USB CDC On Boot | Enabled |
| Flash Size | 16MB (128Mb) |
| PSRAM | OPI PSRAM |
| Partition Scheme | 16M Flash (3MB APP/9.9MB FATFS) |
| Upload Speed | 921600 |
| Upload Mode | UART0 / Hardware CDC |

> **Important:** The board must be **`Waveshare ESP32S3 XIP`**, not `Waveshare ESP32-S3-Touch-LCD-7`.
> The 7B is a different board with a different IO expander and the wrong board selection
> will cause a silent init failure.

The Waveshare board entries are available after installing the ESP32 board package from Espressif:
```
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

---

## Libraries

### Required (install via Library Manager)

| Library | Version | Notes |
|---|---|---|
| LVGL | **8.3.x** | Must pin to v8 — v9 has an incompatible API |
| ArduinoJson | 7.x | |

### Not used

**ESP32_Display_Panel** — this library does NOT support the 7B. As of v1.0.4 it has no
`BOARD_WAVESHARE_ESP32_S3_TOUCH_LCD_7_B` entry. The 7B uses a proprietary Waveshare IO
expander at I2C address `0x24` instead of the CH422G (`0x20`) that every other board in
the library uses. Do not install or configure this library for the 7B.

### Display drivers (bundled in sketch folder)

The sketch folder contains Waveshare's direct ESP-IDF drivers, copied from the official
7B demo package (`ESP32-S3-Touch-LCD-7B-Demo.zip`):

| File | Purpose |
|---|---|
| `i2c.h / i2c.cpp` | ESP-IDF I2C master bus |
| `io_extension.h / io_extension.cpp` | Waveshare proprietary IO expander (0x24) |
| `rgb_lcd_port.h / rgb_lcd_port.cpp` | RGB LCD panel init with 7B timing |
| `lvgl_port.h / lvgl_port.cpp` | LVGL FreeRTOS task + mutex |
| `gt911.h / gt911.cpp` | GT911 touch controller |
| `touch.h / touch.cpp` | esp_lcd_touch abstraction |

Demo download (if you need to re-extract these files):
[Google Drive — ESP32-S3-Touch-LCD-7B-Demo](https://drive.google.com/file/d/1SlaHaUGaepOzLuIErm9lD_saKXQ0TIRK/view)

---

## LVGL post-install setup

LVGL requires a config file placed next to the `lvgl` folder:

```bash
cp ~/Documents/Arduino/libraries/lvgl/lv_conf_template.h \
   ~/Documents/Arduino/libraries/lv_conf.h
```

Then in `lv_conf.h`, line 15:
```c
// change:
#if 0
// to:
#if 1
```

Also enable the fonts the sketch uses (search for `LV_FONT_MONTSERRAT`):
```c
#define LV_FONT_MONTSERRAT_12 1
#define LV_FONT_MONTSERRAT_14 1   // already 1 by default
#define LV_FONT_MONTSERRAT_16 1
```

---

## Sketch config

Edit `arduino_metrodisplay_module/metro_display/config.h` before flashing:

```cpp
const char* WIFI_SSID     = "your-ssid";
const char* WIFI_PASSWORD = "your-password";
const char* API_HOST      = "your-api-host-or-ip";
const int   API_PORT      = 8000;   // or 443 for HTTPS
```

Stop config (the JSON POSTed to the API on each poll) is also defined here in `CONFIG_JSON`.
Edit stops there and reflash — no server changes needed.

> **HTTPS note:** `config.h` currently targets `metro.internal.nyc.xelaxer.com:443`
> but the sketch uses plain `http://`. On the home network, point `API_HOST` at the LAN
> IP and use `API_PORT = 8000` as a workaround. The proper fix is switching to
> `WiFiClientSecure` with `setInsecure()`.

---

## Display architecture

The sketch does **not** use ESP32_Display_Panel. The display init chain is:

```
touch_gt911_init()
  └─ DEV_I2C_Init()           — I2C bus on GPIO8 (SDA) / GPIO9 (SCL)
  └─ IO_EXTENSION_Init()      — Waveshare expander at 0x24, all pins HIGH
  └─ touch reset via IO1      — GT911 reset sequence through expander
  └─ esp_lcd_new_panel_io_i2c — GT911 touch I2C panel IO handle

waveshare_esp32_s3_rgb_lcd_init()
  └─ esp_lcd_new_rgb_panel()  — 1024×600, 30MHz pixel clock, 16-bit RGB565

lvgl_port_init(panel, touch)
  └─ lv_init()
  └─ FreeRTOS task on core 1  — runs lv_timer_handler() with mutex
```

Backlight comes on automatically — the expander initialises all pins HIGH (including IO2 = DISP).

LVGL runs in a FreeRTOS task. Any LVGL API calls from outside that task (WiFi callbacks,
main loop) must be wrapped:
```cpp
if (lvgl_port_lock(100)) {
    // lv_* calls here
    lvgl_port_unlock();
}
```

---

## Expected serial output on clean boot

```
=== NYC Metro Display — boot ===
setup: display_init...
display: touch/IO expander init...
display: RGB LCD init...
display: LVGL init...
display: init OK (1024x600)
setup: display_init OK
setup: ui_init...
ui: init OK
setup: ui_init OK
setup: wifi_connect...
  WiFi status=6  (0ms)
  ...
WiFi: connected — <ip>
setup: wifi done, status=3
setup: fetch_and_render...
fetch: POST http://<host>:<port>/api/eta
fetch: response code=200
fetch: OK  updated_at=...
ui: updated (4 stops)
setup: complete
```
