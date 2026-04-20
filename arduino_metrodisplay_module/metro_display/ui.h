#pragma once

// LVGL v8.3 UI — transit columns + taskbar (weather + controls).
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
#define WEATHER_H       55                      // taskbar height (bottom strip)
#define TRANSIT_H       (SCREEN_H - WEATHER_H)  // 545px
#define COL_W           (SCREEN_W / 3)          // 341px
#define COL_HEADER_H    34
#define TRAIN_ROW_H     52                      // taller to fit ETA pills
#define BADGE_SIZE      32
#define PAD             10
#define PILL_W          42
#define PILL_H          34
#define PILL_GAP         4
#define BTN_SIZE        44                      // taskbar icon button size
#define STOP_SECTION_H  26                      // in-column stop divider height
#define MAX_PILLS        3

// ─── Colors ───────────────────────────────────────────────────────────────────
#define COL_BG           0x111122   // main background
#define COL_HEADER_BG    0x0A0A1A   // column headers + taskbar
#define COL_DIVIDER      0x2A2A44
#define COL_DIR_LABEL    0x7777AA
#define COL_ETA          0xBBBBCC
#define COL_NO_TRAINS    0x444455
#define COL_PILL_BG      0x1E1E30
#define COL_PILL_UNIT    0x8888AA
#define COL_BTN_BG       0x222244

// ─── Widget refs ─────────────────────────────────────────────────────────────
static lv_obj_t* _col_header_lbl[3];   // stop name label per column
static lv_obj_t* _stop_content[3];     // flex column container per column
static lv_obj_t* _weather_lbl = nullptr;
static lv_obj_t* _status_lbl  = nullptr;

// ─── Taskbar button state (accessible from metro_display.ino) ─────────────────
static bool          g_flipped       = false;
static volatile bool g_force_refresh = false;

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

// ─── Event callbacks ─────────────────────────────────────────────────────────

static void _flip_cb(lv_event_t* e) {
    (void)e;
    g_flipped = !g_flipped;
    lv_disp_set_rotation(lv_disp_get_default(),
        g_flipped ? LV_DISP_ROT_180 : LV_DISP_ROT_NONE);
}

static void _refresh_cb(lv_event_t* e) {
    (void)e;
    g_force_refresh = true;
}

// ─── Section divider (stacks Court Square below Queensboro Plaza in col 2) ───

static void _add_section_header(lv_obj_t* parent, const char* label) {
    lv_obj_t* row = lv_obj_create(parent);
    lv_obj_set_size(row, lv_pct(100), STOP_SECTION_H);
    lv_obj_set_style_bg_color(row, _hex(COL_HEADER_BG), 0);
    lv_obj_set_style_bg_opa(row, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(row, 1, 0);
    lv_obj_set_style_border_side(row, LV_BORDER_SIDE_TOP | LV_BORDER_SIDE_BOTTOM, 0);
    lv_obj_set_style_border_color(row, _hex(COL_DIVIDER), 0);
    lv_obj_set_style_pad_all(row, 0, 0);
    lv_obj_set_style_radius(row, 0, 0);
    lv_obj_clear_flag(row, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* lbl = lv_label_create(row);
    lv_label_set_text(lbl, label);
    lv_obj_align(lbl, LV_ALIGN_LEFT_MID, 0, 0);
    lv_obj_set_style_text_color(lbl, lv_color_white(), 0);
    lv_obj_set_style_text_font(lbl, &lv_font_montserrat_14, 0);
}

// ─── Train row with ETA pills ─────────────────────────────────────────────────

static void _add_train_row(lv_obj_t* parent,
                            const char* line, const char* color_hex,
                            const char* dest,
                            int* etas, int eta_count) {
    // The parent content container has pad_left/right = PAD,
    // so lv_pct(100) children are COL_W - 2*PAD wide.
    int row_w = COL_W - 2 * PAD;

    lv_obj_t* row = lv_obj_create(parent);
    lv_obj_set_size(row, lv_pct(100), TRAIN_ROW_H);
    lv_obj_set_style_bg_opa(row, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(row, 0, 0);
    lv_obj_set_style_pad_all(row, 0, 0);
    lv_obj_set_style_radius(row, 0, 0);
    lv_obj_clear_flag(row, LV_OBJ_FLAG_SCROLLABLE);

    // Line badge
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

    // ETA pills — right-aligned, up to MAX_PILLS
    int n_pills = eta_count < MAX_PILLS ? eta_count : MAX_PILLS;
    int pills_total_w = n_pills * PILL_W + (n_pills - 1) * PILL_GAP;
    int pill_x_start = row_w - pills_total_w;

    for (int p = 0; p < n_pills; p++) {
        lv_obj_t* pill = lv_obj_create(row);
        lv_obj_set_size(pill, PILL_W, PILL_H);
        lv_obj_set_pos(pill, pill_x_start + p * (PILL_W + PILL_GAP),
                       (TRAIN_ROW_H - PILL_H) / 2);
        lv_obj_set_style_radius(pill, 6, 0);
        lv_obj_set_style_bg_color(pill, _hex(COL_PILL_BG), 0);
        lv_obj_set_style_bg_opa(pill, LV_OPA_COVER, 0);
        lv_obj_set_style_border_width(pill, 0, 0);
        lv_obj_set_style_pad_all(pill, 0, 0);
        lv_obj_clear_flag(pill, LV_OBJ_FLAG_SCROLLABLE);

        if (etas[p] == 0) {
            lv_obj_t* now_lbl = lv_label_create(pill);
            lv_label_set_text(now_lbl, "Now");
            lv_obj_align(now_lbl, LV_ALIGN_CENTER, 0, 0);
            lv_obj_set_style_text_font(now_lbl, &lv_font_montserrat_12, 0);
            lv_obj_set_style_text_color(now_lbl, lv_color_white(), 0);
        } else {
            char num_buf[8];
            snprintf(num_buf, sizeof(num_buf), "%d", etas[p]);

            lv_obj_t* num_lbl = lv_label_create(pill);
            lv_label_set_text(num_lbl, num_buf);
            lv_obj_align(num_lbl, LV_ALIGN_TOP_MID, 0, 3);
            lv_obj_set_style_text_font(num_lbl, &lv_font_montserrat_16, 0);
            lv_obj_set_style_text_color(num_lbl, lv_color_white(), 0);

            lv_obj_t* unit_lbl = lv_label_create(pill);
            lv_label_set_text(unit_lbl, "m");
            lv_obj_align(unit_lbl, LV_ALIGN_BOTTOM_MID, 0, -2);
            lv_obj_set_style_text_font(unit_lbl, &lv_font_montserrat_12, 0);
            lv_obj_set_style_text_color(unit_lbl, _hex(COL_PILL_UNIT), 0);
        }
    }

    // Destination label — between badge and first pill
    int dest_x = BADGE_SIZE + PAD;
    int dest_w = pill_x_start - dest_x - PAD;
    lv_obj_t* dest_lbl = lv_label_create(row);
    lv_label_set_text(dest_lbl, dest);
    lv_label_set_long_mode(dest_lbl, LV_LABEL_LONG_DOT);
    lv_obj_set_width(dest_lbl, dest_w);
    lv_obj_align(dest_lbl, LV_ALIGN_LEFT_MID, dest_x, 0);
    lv_obj_set_style_text_color(dest_lbl, lv_color_white(), 0);
    lv_obj_set_style_text_font(dest_lbl, &lv_font_montserrat_14, 0);
}

// ─── Render one stop's directions into a column content container ─────────────

static void _render_stop(lv_obj_t* content, JsonObject stop) {
    for (JsonObject dir : stop["directions"].as<JsonArray>()) {
        lv_obj_t* dir_lbl = lv_label_create(content);
        lv_label_set_text(dir_lbl, _dir_label(dir["label"].as<const char*>()));
        lv_obj_set_style_text_color(dir_lbl, _hex(COL_DIR_LABEL), 0);
        lv_obj_set_style_text_font(dir_lbl, &lv_font_montserrat_12, 0);
        lv_obj_set_style_pad_top(dir_lbl, 6, 0);

        JsonArray trains = dir["trains"].as<JsonArray>();
        if (trains.size() == 0) {
            lv_obj_t* none = lv_label_create(content);
            lv_label_set_text(none, "No trains");
            lv_obj_set_style_text_color(none, _hex(COL_NO_TRAINS), 0);
            lv_obj_set_style_text_font(none, &lv_font_montserrat_12, 0);
            continue;
        }

        // Group consecutive trains with the same (line, dest) and collect
        // their ETAs into a single row with up to MAX_PILLS time pills.
        // The API returns trains sorted by ETA ascending; same line+dest are
        // already consecutive so a simple forward-scan grouping works.
        char prev_line[8]  = "";
        char prev_dest[64] = "";
        char prev_color[8] = "";
        int  etas[MAX_PILLS];
        int  eta_count = 0;

        for (JsonObject train : trains) {
            const char* line  = train["line"].as<const char*>();
            const char* dest  = train["dest"].as<const char*>();
            const char* color = train["color"].as<const char*>();
            int         eta   = train["eta_min"].as<int>();

            bool same = (strcmp(line, prev_line) == 0 &&
                         strcmp(dest, prev_dest) == 0);

            if (!same && eta_count > 0) {
                _add_train_row(content, prev_line, prev_color, prev_dest,
                               etas, eta_count);
                eta_count = 0;
            }

            if (!same) {
                strncpy(prev_line,  line,  sizeof(prev_line)  - 1);
                prev_line[sizeof(prev_line) - 1] = '\0';
                strncpy(prev_dest,  dest,  sizeof(prev_dest)  - 1);
                prev_dest[sizeof(prev_dest) - 1] = '\0';
                strncpy(prev_color, color, sizeof(prev_color) - 1);
                prev_color[sizeof(prev_color) - 1] = '\0';
            }

            if (eta_count < MAX_PILLS) {
                etas[eta_count++] = eta;
            }
        }

        if (eta_count > 0) {
            _add_train_row(content, prev_line, prev_color, prev_dest,
                           etas, eta_count);
        }
    }
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
        lv_obj_set_style_pad_row(content, 2, 0);
        lv_obj_set_flex_flow(content, LV_FLEX_FLOW_COLUMN);

        _stop_content[i] = content;
    }

    // ── Taskbar (bottom 55px) — weather left, buttons right ─────────────────
    lv_obj_t* taskbar = lv_obj_create(scr);
    lv_obj_set_pos(taskbar, 0, TRANSIT_H);
    lv_obj_set_size(taskbar, SCREEN_W, WEATHER_H);
    lv_obj_set_style_bg_color(taskbar, _hex(COL_HEADER_BG), 0);
    lv_obj_set_style_bg_opa(taskbar, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(taskbar, 1, 0);
    lv_obj_set_style_border_side(taskbar, LV_BORDER_SIDE_TOP, 0);
    lv_obj_set_style_border_color(taskbar, _hex(COL_DIVIDER), 0);
    lv_obj_set_style_pad_all(taskbar, 0, 0);
    lv_obj_clear_flag(taskbar, LV_OBJ_FLAG_SCROLLABLE);

    // Weather text — left-aligned
    _weather_lbl = lv_label_create(taskbar);
    lv_label_set_text(_weather_lbl, "—");
    lv_obj_align(_weather_lbl, LV_ALIGN_LEFT_MID, PAD, 0);
    lv_obj_set_style_text_color(_weather_lbl, _hex(COL_ETA), 0);
    lv_obj_set_style_text_font(_weather_lbl, &lv_font_montserrat_16, 0);

    // Flip button [↕] — rightmost
    lv_obj_t* flip_btn = lv_btn_create(taskbar);
    lv_obj_set_size(flip_btn, BTN_SIZE, BTN_SIZE);
    lv_obj_align(flip_btn, LV_ALIGN_RIGHT_MID, -PAD, 0);
    lv_obj_set_style_bg_color(flip_btn, _hex(COL_BTN_BG), 0);
    lv_obj_set_style_radius(flip_btn, 6, 0);
    lv_obj_set_style_border_width(flip_btn, 0, 0);
    lv_obj_add_event_cb(flip_btn, _flip_cb, LV_EVENT_CLICKED, NULL);

    lv_obj_t* flip_lbl = lv_label_create(flip_btn);
    lv_label_set_text(flip_lbl, LV_SYMBOL_UP "" LV_SYMBOL_DOWN);
    lv_obj_center(flip_lbl);
    lv_obj_set_style_text_color(flip_lbl, lv_color_white(), 0);

    // Refresh button [↻] — left of flip
    lv_obj_t* ref_btn = lv_btn_create(taskbar);
    lv_obj_set_size(ref_btn, BTN_SIZE, BTN_SIZE);
    lv_obj_align(ref_btn, LV_ALIGN_RIGHT_MID, -(PAD + BTN_SIZE + PAD), 0);
    lv_obj_set_style_bg_color(ref_btn, _hex(COL_BTN_BG), 0);
    lv_obj_set_style_radius(ref_btn, 6, 0);
    lv_obj_set_style_border_width(ref_btn, 0, 0);
    lv_obj_add_event_cb(ref_btn, _refresh_cb, LV_EVENT_CLICKED, NULL);

    lv_obj_t* ref_lbl = lv_label_create(ref_btn);
    lv_label_set_text(ref_lbl, LV_SYMBOL_REFRESH);
    lv_obj_center(ref_lbl);
    lv_obj_set_style_text_color(ref_lbl, lv_color_white(), 0);

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
    if (lvgl_port_lock(100)) {
        lv_label_set_text(_status_lbl, msg);
        lv_obj_clear_flag(_status_lbl, LV_OBJ_FLAG_HIDDEN);
        lvgl_port_unlock();
    }
}

// ─── Update ───────────────────────────────────────────────────────────────────

void ui_update(JsonDocument& doc) {
    if (!lvgl_port_lock(500)) return;

    lv_obj_add_flag(_status_lbl, LV_OBJ_FLAG_HIDDEN);

    JsonArray stops = doc["stops"].as<JsonArray>();
    int stop_count = (int)stops.size();

    // Column mapping:
    //   col 0 → stops[0]  (39 Av)
    //   col 1 → stops[1]  (Queens Plaza)
    //   col 2 → stops[2]  (Queensboro Plaza)  + stops[3] (Court Square, stacked)
    for (int col = 0; col < 3 && col < stop_count; col++) {
        JsonObject stop = stops[col];
        lv_label_set_text(_col_header_lbl[col], stop["label"].as<const char*>());
        lv_obj_clean(_stop_content[col]);
        _render_stop(_stop_content[col], stop);

        if (col == 2 && stop_count > 3) {
            JsonObject extra = stops[3];
            _add_section_header(_stop_content[col], extra["label"].as<const char*>());
            _render_stop(_stop_content[col], extra);
        }
    }

    // Weather
    JsonObject w = doc["weather"].as<JsonObject>();
    if (!w.isNull()) {
        char buf[96];
        snprintf(buf, sizeof(buf),
            "%d\xC2\xB0""F   H %d\xC2\xB0 / L %d\xC2\xB0   Rain %d%%   Wind %d mph %s",
            w["current_temp_f"].as<int>(),
            w["high_f"].as<int>(),
            w["low_f"].as<int>(),
            w["rain_chance_pct"].as<int>(),
            w["wind_mph"].as<int>(),
            w["wind_dir"].as<const char*>()
        );
        lv_label_set_text(_weather_lbl, buf);
    }

    Serial.printf("ui: updated (%d stops)\n", stop_count);
    lvgl_port_unlock();
}
