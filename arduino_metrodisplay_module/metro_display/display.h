#pragma once

// Waveshare ESP32-S3-Touch-LCD-7B display driver init.
//
// Requires: ESP32_Display_Panel library
//   Install via Arduino Library Manager: search "ESP32_Display_Panel"
//   or: https://github.com/esp-arduino-libs/ESP32_Display_Panel
//
// Board config in Arduino IDE:
//   Board:            ESP32S3 Dev Module
//   PSRAM:            OPI PSRAM          ← required, enables 8MB PSRAM
//   Partition Scheme: Huge APP (3MB No OTA / 1MB SPIFFS)
//   USB CDC On Boot:  Enabled            ← Serial over USB-C
//
// lv_conf.h must have:
//   #define LV_COLOR_DEPTH 16

#include <lvgl.h>
#include <ESP_Panel_Library.h>

#define SCREEN_W    1024
#define SCREEN_H     600
#define DRAW_BUF_LINES 20   // height of each LVGL draw buffer (in lines)

static ESP_Panel*         _panel    = nullptr;
static lv_disp_draw_buf_t _draw_buf;
static lv_color_t*        _buf1     = nullptr;
static lv_color_t*        _buf2     = nullptr;

static void _disp_flush(lv_disp_drv_t* drv, const lv_area_t* area, lv_color_t* color_p) {
    _panel->getLcd()->drawBitmap(
        area->x1, area->y1,
        area->x2 - area->x1 + 1,
        area->y2 - area->y1 + 1,
        (uint16_t*)color_p
    );
    lv_disp_flush_ready(drv);
}

static void _touch_read(lv_indev_drv_t* drv, lv_indev_data_t* data) {
    // Touch not used for UI interaction on this display; stub required by LVGL.
    data->state = LV_INDEV_STATE_REL;
}

void display_init() {
    _panel = new ESP_Panel();
    _panel->init();
    _panel->begin();

    lv_init();

    // Allocate two draw buffers from PSRAM (double-buffered for smoother flushes).
    // If this fails, PSRAM is not enabled — check board config.
    size_t buf_bytes = SCREEN_W * DRAW_BUF_LINES * sizeof(lv_color_t);
    _buf1 = (lv_color_t*)heap_caps_malloc(buf_bytes, MALLOC_CAP_SPIRAM);
    _buf2 = (lv_color_t*)heap_caps_malloc(buf_bytes, MALLOC_CAP_SPIRAM);

    if (!_buf1 || !_buf2) {
        Serial.println("display: PSRAM alloc failed — set PSRAM to OPI PSRAM in board config");
        while (true) delay(1000);
    }

    lv_disp_draw_buf_init(&_draw_buf, _buf1, _buf2, SCREEN_W * DRAW_BUF_LINES);

    static lv_disp_drv_t disp_drv;
    lv_disp_drv_init(&disp_drv);
    disp_drv.hor_res  = SCREEN_W;
    disp_drv.ver_res  = SCREEN_H;
    disp_drv.flush_cb = _disp_flush;
    disp_drv.draw_buf = &_draw_buf;
    lv_disp_drv_register(&disp_drv);

    static lv_indev_drv_t indev_drv;
    lv_indev_drv_init(&indev_drv);
    indev_drv.type    = LV_INDEV_TYPE_POINTER;
    indev_drv.read_cb = _touch_read;
    lv_indev_drv_register(&indev_drv);

    Serial.printf("display: init OK (%dx%d)\n", SCREEN_W, SCREEN_H);
}
