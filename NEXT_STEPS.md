# Next Steps — Arduino Display Module

## What we learned

**The 7B is not the 7.**
The Waveshare ESP32-S3-Touch-LCD-7 (800×480) and the ESP32-S3-Touch-LCD-7B (1024×600) are different boards. The 7B has a proprietary Waveshare IO expander at I2C address `0x24` instead of the CH422G at `0x20` used by every other Waveshare board the ESP32_Display_Panel library supports. This is why every supported board config failed with "Write WR-OC reg failed" — the library was trying to talk to a CH422G that doesn't exist.

**ESP32_Display_Panel does not support the 7B (as of v1.0.4).**
No version of the library has ever added a `BOARD_WAVESHARE_ESP32_S3_TOUCH_LCD_7_B` entry. The `_5_B` config (also 1024×600) uses the same CH422G approach and fails identically.

**The correct approach is Waveshare's own demo library.**
Waveshare ships an `Arduino/` demo package for the 7B (`ESP32-S3-Touch-LCD-7B-Demo.zip`) that drives the display directly via ESP-IDF LCD APIs and a custom IO expander protocol, bypassing ESP32_Display_Panel entirely. The LVGL port in the demo runs in a dedicated FreeRTOS task on core 1 with a mutex.

**Board setting in Arduino IDE.**
The 7B should be flashed using the **`Waveshare ESP32S3 XIP`** board, not `Waveshare ESP32-S3-Touch-LCD-7`.

## What we did

1. Diagnosed the CH422G failure and confirmed ESP32_Display_Panel v1.0.4 has no 7B support.
2. Found the official Waveshare 7B demo package on Google Drive and extracted it.
3. Identified the relevant driver files in `Arduino/examples/13_LVGL_TRANSPLANT/`.
4. Copied 10 driver files into the sketch folder:
   - `i2c.h / i2c.cpp` — ESP-IDF I2C master bus init
   - `io_extension.h / io_extension.cpp` — Waveshare proprietary expander (0x24)
   - `rgb_lcd_port.h / rgb_lcd_port.cpp` — RGB LCD init with correct 7B timings
   - `lvgl_port.h / lvgl_port.cpp` — LVGL task, mutex, flush callback
   - `gt911.h / gt911.cpp` — GT911 touch controller
   - `touch.h / touch.cpp` — esp_lcd_touch abstraction layer
5. Rewrote `display.h` to use Waveshare's init chain:
   `touch_gt911_init()` → `waveshare_esp32_s3_rgb_lcd_init()` → `lvgl_port_init()`
6. Updated `ui.h`: wrapped `ui_set_status()` and `ui_update()` with `lvgl_port_lock/unlock`; removed `lv_timer_handler()` calls (LVGL now has its own task).
7. Updated `metro_display.ino`: added `lvgl_port.h` include, wrapped `ui_init()` with lock, removed `lv_timer_handler()` from the WiFi wait loop and `loop()`.

## What to do next

### 1. Flash and verify display boots

Change the Arduino IDE board to **`Waveshare ESP32S3 XIP`**, then compile and flash.

Expected serial output:
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
```

If the display comes on and shows the UI skeleton, the hard part is done.

### 2. Fix HTTPS / confirm API connectivity

`config.h` points at `metro.internal.nyc.xelaxer.com:443` but the sketch uses plain `http://`.

**Quick option (home network):** set `API_HOST` to the LAN IP and `API_PORT` to `8000`.

**Proper fix:** switch `HTTPClient` to `WiFiClientSecure` with `setInsecure()` for the internal cert, and change the URL scheme to `https://`.

### 3. Validate the full UI

Once data is flowing:
- All 4 stops render (39 Av, Queens Plaza, Queensboro Plaza, Court Square)
- `departs_at` field doesn't break JSON parsing
- Weather strip shows current temp, high/low, rain chance, wind

### 4. Commit everything

```bash
git add arduino_metrodisplay_module/metro_display/
git commit -m "feat: replace ESP32_Display_Panel with Waveshare direct drivers for 7B"
```

Files that changed or were added:
- `display.h` (rewritten)
- `ui.h` (mutex wrapping)
- `metro_display.ino` (lock, removed lv_timer_handler)
- `esp_panel_board_supported_conf.h` (no longer relevant — can be deleted)
- 10 new Waveshare driver `.h`/`.cpp` files
