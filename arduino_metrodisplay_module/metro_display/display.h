#pragma once

// Waveshare ESP32-S3-Touch-LCD-7B display driver init.
// Uses Waveshare's direct ESP-IDF drivers — does NOT use ESP32_Display_Panel.
//
// Board config in Arduino IDE:
//   Board:            Waveshare ESP32S3 XIP
//   PSRAM:            OPI PSRAM
//   Partition Scheme: 16M Flash (3MB APP/9.9MB FATFS)
//   USB CDC On Boot:  Enabled

#include <lvgl.h>
#include "rgb_lcd_port.h"
#include "lvgl_port.h"
#include "gt911.h"

#define SCREEN_W    EXAMPLE_LCD_H_RES   // 1024
#define SCREEN_H    EXAMPLE_LCD_V_RES   //  600

void display_init() {
    // touch_gt911_init() handles I2C bus init, IO expander init, and touch reset
    // (backlight comes on as a side effect — IO expander initialises all pins HIGH)
    Serial.println("display: touch/IO expander init...");
    esp_lcd_touch_handle_t tp_handle = touch_gt911_init();

    Serial.println("display: RGB LCD init...");
    esp_lcd_panel_handle_t panel_handle = waveshare_esp32_s3_rgb_lcd_init();

    // LVGL init — starts its own FreeRTOS task on core 1.
    // All LVGL calls after this point must be wrapped with lvgl_port_lock/unlock.
    Serial.println("display: LVGL init...");
    ESP_ERROR_CHECK(lvgl_port_init(panel_handle, tp_handle));

    Serial.printf("display: init OK (%dx%d)\n", SCREEN_W, SCREEN_H);
}
