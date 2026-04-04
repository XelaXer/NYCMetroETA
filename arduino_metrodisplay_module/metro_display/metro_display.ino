/*
 * NYC Metro Display
 * Waveshare ESP32-S3-Touch-LCD-7B  |  LVGL v8.3  |  ArduinoJson v7
 *
 * Flow:
 *   1. Connect to WiFi
 *   2. POST config.h CONFIG_JSON to metro_api POST /api/eta every 30 seconds
 *   3. Parse JSON response, update LVGL display
 *
 * Board settings (Arduino IDE):
 *   Board:            ESP32S3 Dev Module
 *   PSRAM:            OPI PSRAM
 *   Partition Scheme: Huge APP (3MB No OTA / 1MB SPIFFS)
 *   USB CDC On Boot:  Enabled
 *
 * Libraries (install via Library Manager):
 *   - LVGL             v8.3.x  (pin to v8, not v9)
 *   - ArduinoJson      v7.x
 *   - ESP32_Display_Panel      (Waveshare board driver)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <lvgl.h>

#include "config.h"
#include "display.h"
#include "ui.h"

#define POLL_INTERVAL_MS   30000
#define WIFI_TIMEOUT_MS    15000
#define HTTP_TIMEOUT_MS     8000

static uint32_t _last_poll       = 0;
static bool     _wifi_connected  = false;

// ─── WiFi ─────────────────────────────────────────────────────────────────────

static void wifi_connect() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.printf("WiFi: connecting to %s\n", WIFI_SSID);
    ui_set_status("Connecting to WiFi...");

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
        lv_timer_handler();
        delay(10);
    }

    if (WiFi.status() == WL_CONNECTED) {
        _wifi_connected = true;
        Serial.printf("WiFi: connected — %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("WiFi: connection timed out");
        ui_set_status("WiFi failed — retrying in 30s");
    }
}

// ─── API fetch ────────────────────────────────────────────────────────────────

static void fetch_and_render() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("fetch: skipped — WiFi not connected");
        return;
    }

    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d%s", API_HOST, API_PORT, API_PATH);

    HTTPClient http;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(HTTP_TIMEOUT_MS);

    int code = http.POST((uint8_t*)CONFIG_JSON, strlen(CONFIG_JSON));

    if (code != 200) {
        Serial.printf("fetch: HTTP %d from %s\n", code, url);
        http.end();
        ui_set_status("API error — retrying...");
        return;
    }

    // Deserialize directly from stream — avoids copying the full response into a String.
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, http.getStream());
    http.end();

    if (err) {
        Serial.printf("fetch: JSON error — %s\n", err.c_str());
        ui_set_status("Parse error — retrying...");
        return;
    }

    Serial.printf("fetch: OK  updated_at=%s\n", doc["updated_at"].as<const char*>());
    ui_update(doc);
}

// ─── Setup / loop ─────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    Serial.println("\nNYC Metro Display — boot");

    display_init();
    ui_init();

    wifi_connect();

    if (WiFi.status() == WL_CONNECTED) {
        ui_set_status("Fetching trains...");
        fetch_and_render();
    }

    _last_poll = millis();
}

void loop() {
    lv_timer_handler();

    // Reconnect if WiFi dropped
    if (WiFi.status() != WL_CONNECTED) {
        if (_wifi_connected) {
            Serial.println("WiFi: lost connection");
            _wifi_connected = false;
            ui_set_status("WiFi lost — reconnecting...");
        }
        wifi_connect();
    }

    // Poll on interval
    if (millis() - _last_poll >= POLL_INTERVAL_MS) {
        _last_poll = millis();
        fetch_and_render();
    }

    delay(5);
}
