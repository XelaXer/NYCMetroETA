#pragma once

// ─── WiFi ─────────────────────────────────────────────────────────────────────
const char* WIFI_SSID     = "your-ssid";
const char* WIFI_PASSWORD = "your-password";

// ─── API ──────────────────────────────────────────────────────────────────────
// IP of the machine running metro_api. Must be on the same network as the ESP32.
const char* API_HOST = "192.168.1.xxx";
const int   API_PORT = 8000;
const char* API_PATH = "/api/eta";

// ─── Stop config ──────────────────────────────────────────────────────────────
// POSTed as the request body on every poll.
// To add or change stops: edit here and reflash. No API changes needed.
const char* CONFIG_JSON = R"({
  "stops": [
    {
      "feeds": ["N"],
      "label": "39 Av",
      "directions": [
        {"label": "northbound", "stop_id": "R08N"},
        {"label": "southbound", "stop_id": "R08S"}
      ]
    },
    {
      "feeds": ["E", "F", "N"],
      "label": "Queens Plaza",
      "directions": [
        {"label": "southbound", "stop_id": "G21S"}
      ]
    },
    {
      "feeds": ["F", "M", "R"],
      "label": "36 St",
      "directions": [
        {"label": "southbound", "stop_id": "G20S"}
      ]
    },
    {
      "feeds": ["7", "N"],
      "label": "Queensboro Plaza",
      "directions": [
        {"label": "westbound",  "stop_id": "718S"},
        {"label": "northbound", "stop_id": "R09N"},
        {"label": "southbound", "stop_id": "R09S"}
      ]
    },
    {
      "feeds": ["G"],
      "label": "Court Square",
      "directions": [
        {"label": "southbound", "stop_id": "G22S"}
      ]
    }
  ]
})";
