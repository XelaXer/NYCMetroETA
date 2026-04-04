#pragma once

// LVGL v8.3 UI — transit columns + weather strip.
//
// lv_conf.h must enable:
//   #define LV_USE_FLEX           1
//   #define LV_FONT_MONTSERRAT_12 1
//   #define LV_FONT_MONTSERRAT_14 1
//   #define LV_FONT_MONTSERRAT_16 1

#include <lvgl.h>
#include <ArduinoJson.h>
#include "display.h"

// ─── Layout constants ─────────────────────────────────────────────────────────
#define WEATHER_H      55
#define TRANSIT_H      (SCREEN_H - WEATHER_H)
#define COL_W          (SCREEN_W / 3)
#define COL_HEADER_H   34
#define DIR_LABEL_H    20
#define TRAIN_ROW_H    36
#define BADGE_SIZE     28
#define PAD             8

// ─── Colors ───────────────────────────────────────────────────────────────────
#define COL_BG           0x111122   // main background
#define COL_HEADER_BG    0x0A0A1A   // column header + weather strip
#define COL_DIVIDER      0x2A2A44
#define COL_DIR_LABEL    0x7777AA
#define COL_ETA          0xBBBBCC
#define COL_NO_TRAINS    0x444455

// ─── Widget refs ─────────────────────────────────────────────────────────────
static lv_obj_t* _col_header_lbl[3];   // stop name label per column
static lv_obj_t* _stop_content[3];     // flex column container per column
static lv_obj_t* _weather_lbl = nullptr;
static lv_obj_t* _status_lbl  = nullptr;

// ─── Helpers ─────────────────────────────────────────────────────────────────

static lv_color_t _hex(uint32_t v) { return lv_color_hex(v); }

// Parse "FCCC0A" string to lv_color_t.
static lv_color_t _parse_color(const char* hex) {
    if (!hex || strlen(hex) < 6) return lv_color_hex(0x888888);
    return lv_color_hex((uint32_t)strtoul(hex, nullptr, 16));
}

// Black text on bright backgrounds (yellow N/Q/R/W lines), white on dark.
static lv_color_t _contrast(const char* bg_hex) {
    if (!bg_hex || strlen(bg_hex) < 6) return lv_color_white();
    uint32_t v = (uint32_t)strtoul(bg_hex, nullptr, 16);
    uint8_t r = (v >> 16) & 0xFF, g = (v >> 8) & 0xFF, b = v & 0xFF;
    return ((r * 299 + g * 587 + b * 114) / 1000) > 128
        ? lv_color_black()
        : lv_color_white();
}

static const char* _dir_label(const char* dir) {
    if (strcmp(dir, "northbound") == 0) return "Northbound  ^";
    if (strcmp(dir, "southbound") == 0) return "v  Southbound";
    if (strcmp(dir, "westbound")  == 0) return "<  Westbound";
    if (strcmp(dir, "eastbound")  == 0) return "Eastbound  >";
    return dir;
}

// ─── Train row builder ────────────────────────────────────────────────────────

static void _add_train_row(lv_obj_t* parent,
                            const char* line, const char* color_hex,
                            const char* dest,  int eta_min) {
    // Container — full width, fixed height; children positioned manually inside.
    lv_obj_t* row = lv_obj_create(parent);
    lv_obj_set_size(row, lv_pct(100), TRAIN_ROW_H);
    lv_obj_set_style_bg_opa(row, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(row, 0, 0);
    lv_obj_set_style_pad_all(row, 0, 0);
    lv_obj_clear_flag(row, LV_OBJ_FLAG_SCROLLABLE);

    // Colored line badge
    lv_obj_t* badge = lv_obj_create(row);
    lv_obj_set_size(badge, BADGE_SIZE, BADGE_SIZE);
    lv_obj_align(badge, LV_ALIGN_LEFT_MID, 0, 0);
    lv_obj_set_style_bg_color(badge, _parse_color(color_hex), 0);
    lv_obj_set_style_bg_opa(badge, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(badge, 6, 0);
    lv_obj_set_style_border_width(badge, 0, 0);
    lv_obj_clear_flag(badge, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* badge_lbl = lv_label_create(badge);
    lv_label_set_text(badge_lbl, line);
    lv_obj_align(badge_lbl, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_text_color(badge_lbl, _contrast(color_hex), 0);
    lv_obj_set_style_text_font(badge_lbl, &lv_font_montserrat_14, 0);

    // Destination — truncated with ellipsis if too long
    int dest_w = COL_W - PAD * 2 - BADGE_SIZE - PAD - 52;  // 52 = ETA field width
    lv_obj_t* dest_lbl = lv_label_create(row);
    lv_label_set_text(dest_lbl, dest);
    lv_label_set_long_mode(dest_lbl, LV_LABEL_LONG_DOT);
    lv_obj_set_width(dest_lbl, dest_w);
    lv_obj_align(dest_lbl, LV_ALIGN_LEFT_MID, BADGE_SIZE + PAD, 0);
    lv_obj_set_style_text_color(dest_lbl, lv_color_white(), 0);
    lv_obj_set_style_text_font(dest_lbl, &lv_font_montserrat_14, 0);

    // ETA — right-aligned
    char eta_buf[10];
    if (eta_min == 0)
        snprintf(eta_buf, sizeof(eta_buf), "Now");
    else
        snprintf(eta_buf, sizeof(eta_buf), "%d min", eta_min);

    lv_obj_t* eta_lbl = lv_label_create(row);
    lv_label_set_text(eta_lbl, eta_buf);
    lv_obj_align(eta_lbl, LV_ALIGN_RIGHT_MID, 0, 0);
    lv_obj_set_style_text_color(eta_lbl, _hex(COL_ETA), 0);
    lv_obj_set_style_text_font(eta_lbl, &lv_font_montserrat_14, 0);
}

// ─── Init ─────────────────────────────────────────────────────────────────────

void ui_init() {
    lv_obj_t* scr = lv_scr_act();
    lv_obj_set_style_bg_color(scr, _hex(COL_BG), 0);
    lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);

    for (int i = 0; i < 3; i++) {
        int x = i * COL_W;

        // Column outer container
        lv_obj_t* col = lv_obj_create(scr);
        lv_obj_set_pos(col, x, 0);
        lv_obj_set_size(col, COL_W, TRANSIT_H);
        lv_obj_set_style_bg_opa(col, LV_OPA_TRANSP, 0);
        lv_obj_set_style_pad_all(col, 0, 0);
        lv_obj_clear_flag(col, LV_OBJ_FLAG_SCROLLABLE);

        // Right-side divider between columns
        if (i < 2) {
            lv_obj_set_style_border_width(col, 1, 0);
            lv_obj_set_style_border_side(col, LV_BORDER_SIDE_RIGHT, 0);
            lv_obj_set_style_border_color(col, _hex(COL_DIVIDER), 0);
        } else {
            lv_obj_set_style_border_width(col, 0, 0);
        }

        // Column header bar
        lv_obj_t* header = lv_obj_create(col);
        lv_obj_set_pos(header, 0, 0);
        lv_obj_set_size(header, COL_W, COL_HEADER_H);
        lv_obj_set_style_bg_color(header, _hex(COL_HEADER_BG), 0);
        lv_obj_set_style_bg_opa(header, LV_OPA_COVER, 0);
        lv_obj_set_style_border_width(header, 0, 0);
        lv_obj_clear_flag(header, LV_OBJ_FLAG_SCROLLABLE);

        _col_header_lbl[i] = lv_label_create(header);
        lv_label_set_text(_col_header_lbl[i], "—");
        lv_obj_align(_col_header_lbl[i], LV_ALIGN_CENTER, 0, 0);
        lv_obj_set_style_text_color(_col_header_lbl[i], lv_color_white(), 0);
        lv_obj_set_style_text_font(_col_header_lbl[i], &lv_font_montserrat_16, 0);

        // Train list — flex column, scrollable if content overflows
        lv_obj_t* content = lv_obj_create(col);
        lv_obj_set_pos(content, 0, COL_HEADER_H);
        lv_obj_set_size(content, COL_W, TRANSIT_H - COL_HEADER_H);
        lv_obj_set_style_bg_opa(content, LV_OPA_TRANSP, 0);
        lv_obj_set_style_border_width(content, 0, 0);
        lv_obj_set_style_pad_left(content, PAD, 0);
        lv_obj_set_style_pad_right(content, PAD, 0);
        lv_obj_set_style_pad_top(content, PAD / 2, 0);
        lv_obj_set_style_pad_bottom(content, PAD / 2, 0);
        lv_obj_set_style_pad_row(content, 2, 0);   // gap between flex children
        lv_obj_set_flex_flow(content, LV_FLEX_FLOW_COLUMN);

        _stop_content[i] = content;
    }

    // Weather strip
    lv_obj_t* wx_bar = lv_obj_create(scr);
    lv_obj_set_pos(wx_bar, 0, TRANSIT_H);
    lv_obj_set_size(wx_bar, SCREEN_W, WEATHER_H);
    lv_obj_set_style_bg_color(wx_bar, _hex(COL_HEADER_BG), 0);
    lv_obj_set_style_bg_opa(wx_bar, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(wx_bar, 1, 0);
    lv_obj_set_style_border_side(wx_bar, LV_BORDER_SIDE_TOP, 0);
    lv_obj_set_style_border_color(wx_bar, _hex(COL_DIVIDER), 0);
    lv_obj_clear_flag(wx_bar, LV_OBJ_FLAG_SCROLLABLE);

    _weather_lbl = lv_label_create(wx_bar);
    lv_label_set_text(_weather_lbl, "—");
    lv_obj_align(_weather_lbl, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_text_color(_weather_lbl, _hex(COL_ETA), 0);
    lv_obj_set_style_text_font(_weather_lbl, &lv_font_montserrat_16, 0);

    // Status overlay — shown during WiFi connect / fetch errors
    _status_lbl = lv_label_create(scr);
    lv_label_set_text(_status_lbl, "");
    lv_obj_align(_status_lbl, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_text_color(_status_lbl, _hex(0xAAAAAA), 0);
    lv_obj_set_style_text_font(_status_lbl, &lv_font_montserrat_16, 0);
    lv_obj_add_flag(_status_lbl, LV_OBJ_FLAG_HIDDEN);

    Serial.println("ui: init OK");
}

// ─── Status overlay ───────────────────────────────────────────────────────────

void ui_set_status(const char* msg) {
    lv_label_set_text(_status_lbl, msg);
    lv_obj_clear_flag(_status_lbl, LV_OBJ_FLAG_HIDDEN);
    lv_timer_handler();   // flush before any blocking operation
    lv_timer_handler();
}

// ─── Update ───────────────────────────────────────────────────────────────────

void ui_update(JsonDocument& doc) {
    // Hide status overlay once we have real data
    lv_obj_add_flag(_status_lbl, LV_OBJ_FLAG_HIDDEN);

    // Stops
    JsonArray stops = doc["stops"].as<JsonArray>();
    int col = 0;

    for (JsonObject stop : stops) {
        if (col >= 3) break;

        lv_label_set_text(_col_header_lbl[col], stop["label"].as<const char*>());

        // Rebuild this column's train list from scratch
        lv_obj_clean(_stop_content[col]);

        for (JsonObject dir : stop["directions"].as<JsonArray>()) {
            // Direction label
            lv_obj_t* dir_lbl = lv_label_create(_stop_content[col]);
            lv_label_set_text(dir_lbl, _dir_label(dir["label"].as<const char*>()));
            lv_obj_set_style_text_color(dir_lbl, _hex(COL_DIR_LABEL), 0);
            lv_obj_set_style_text_font(dir_lbl, &lv_font_montserrat_12, 0);
            lv_obj_set_style_pad_top(dir_lbl, 6, 0);

            JsonArray trains = dir["trains"].as<JsonArray>();

            if (trains.size() == 0) {
                lv_obj_t* none = lv_label_create(_stop_content[col]);
                lv_label_set_text(none, "No trains");
                lv_obj_set_style_text_color(none, _hex(COL_NO_TRAINS), 0);
                lv_obj_set_style_text_font(none, &lv_font_montserrat_12, 0);
            } else {
                for (JsonObject train : trains) {
                    _add_train_row(
                        _stop_content[col],
                        train["line"].as<const char*>(),
                        train["color"].as<const char*>(),
                        train["dest"].as<const char*>(),
                        train["eta_min"].as<int>()
                    );
                }
            }
        }

        col++;
    }

    // Weather
    JsonObject w = doc["weather"].as<JsonObject>();
    if (!w.isNull()) {
        char buf[96];
        snprintf(buf, sizeof(buf),
            "%d\xC2\xB0""F     H %d\xC2\xB0  /  L %d\xC2\xB0     Rain %d%%     Wind %d mph %s",
            w["current_temp_f"].as<int>(),
            w["high_f"].as<int>(),
            w["low_f"].as<int>(),
            w["rain_chance_pct"].as<int>(),
            w["wind_mph"].as<int>(),
            w["wind_dir"].as<const char*>()
        );
        lv_label_set_text(_weather_lbl, buf);
    }

    Serial.printf("ui: updated (%d stops)\n", col);
}
