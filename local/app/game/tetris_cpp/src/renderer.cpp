#include "renderer.h"
#include <SDL.h>
#include <string>
#include <cmath>
#include <algorithm>
#include <cstdint>

// 简易 5x7 像素字体 (ASCII 32-126)，直接嵌入常用字符

// 直接点阵定义常用字符
constexpr int CHAR_W = 5, CHAR_H = 7;

static void draw_char(SDL_Renderer* r, int x, int y, char ch, int scale, uint32_t color) {
    if (ch < 32 || ch > 126) return;
    // 预定义常用字符点阵
    static const uint8_t FONT[128][7] = {
        [32]={0,0,0,0,0,0,0},
        [33]={4,4,4,4,0,4,0},
        [48]={14,17,19,21,25,17,14},  // 0
        [49]={4,12,4,4,4,4,14},       // 1
        [50]={14,17,1,6,8,16,31},     // 2
        [51]={14,17,1,6,1,17,14},     // 3
        [52]={18,18,18,31,2,2,2},     // 4
        [53]={31,16,30,1,1,17,14},    // 5
        [54]={14,16,16,30,17,17,14},  // 6
        [55]={31,1,2,4,8,8,8},        // 7
        [56]={14,17,17,14,17,17,14},  // 8
        [57]={14,17,17,15,1,17,14},   // 9
        [65]={14,17,17,31,17,17,17},  // A
        [66]={30,17,17,30,17,17,30},  // B
        [67]={14,17,16,16,16,17,14},  // C
        [68]={30,17,17,17,17,17,30},  // D
        [69]={31,16,16,30,16,16,31},  // E
        [70]={31,16,16,30,16,16,16},  // F
        [71]={14,17,16,23,17,17,14},  // G
        [72]={17,17,17,31,17,17,17},  // H
        [73]={14,4,4,4,4,4,14},       // I
        [74]={1,1,1,1,1,17,14},       // J
        [75]={17,18,20,24,20,18,17},  // K
        [76]={16,16,16,16,16,16,31},  // L
        [77]={17,27,21,17,17,17,17},  // M
        [78]={17,25,21,19,17,17,17},  // N
        [79]={14,17,17,17,17,17,14},  // O
        [80]={30,17,17,30,16,16,16},  // P
        [81]={14,17,17,17,21,18,13},  // Q
        [82]={30,17,17,30,20,18,17},  // R
        [83]={14,17,16,14,1,17,14},   // S
        [84]={31,4,4,4,4,4,4},        // T
        [85]={17,17,17,17,17,17,14},  // U
        [86]={17,17,17,17,17,10,4},   // V
        [87]={17,17,17,17,21,27,17},  // W
        [88]={17,17,10,4,10,17,17},   // X
        [89]={17,17,17,10,4,4,4},     // Y
        [90]={31,2,4,8,16,16,31},     // Z
        // 小写补充
        [97]={0,0,14,1,15,17,15},     // a
        [98]={16,16,30,17,17,17,30},  // b
        [99]={0,0,14,16,16,17,14},    // c
        [100]={1,1,15,17,17,17,15},   // d
        [101]={0,0,14,17,31,16,14},   // e
        [102]={6,9,8,28,8,8,8},       // f
        [103]={0,0,15,17,15,1,14},    // g
        [104]={16,16,30,17,17,17,17}, // h
        [105]={4,0,12,4,4,4,14},      // i
        [106]={1,0,3,1,1,17,14},      // j
        [107]={16,16,18,20,24,20,18}, // k
        [108]={12,4,4,4,4,4,14},      // l
        [109]={0,0,26,21,21,21,21},   // m
        [110]={0,0,22,25,17,17,17},   // n
        [111]={0,0,14,17,17,17,14},   // o
        [112]={0,0,30,17,30,16,16},   // p
        [113]={0,0,15,17,15,1,1},     // q
        [114]={0,0,22,25,16,16,16},   // r
        [115]={0,0,14,16,14,1,30},    // s
        [116]={8,8,28,8,8,9,6},       // t
        [117]={0,0,17,17,17,17,14},   // u
        [118]={0,0,17,17,17,10,4},    // v
        [119]={0,0,17,17,21,21,10},   // w
        [120]={0,0,17,10,4,10,17},    // x
        [121]={0,0,17,17,15,1,14},    // y
        [122]={0,0,31,2,4,8,31},      // z
        // 符号
        [44]={0,0,0,0,4,4,8},         // ,
        [46]={0,0,0,0,0,4,4},         // .
        [58]={0,0,4,0,0,4,0},         // :
        [32]={0,0,0,0,0,0,0},         // space
        [45]={0,0,0,14,0,0,0},        // -
        [8592]={0,0,2,4,14,4,2},      // ← (在Unicode中不支持, 用指针表示)
        [8594]={0,0,8,4,14,4,8},      // →
        [8595]={0,0,0,14,4,0,0},      // ↓
        [8593]={0,0,0,4,14,0,0},      // ↑
    };

    const auto* glyph = FONT[(int)ch];
    if (!glyph) return;

    uint8_t r8 = (color >> 24) & 0xFF;
    uint8_t g8 = (color >> 16) & 0xFF;
    uint8_t b8 = (color >> 8) & 0xFF;
    uint8_t a8 = color & 0xFF;

    SDL_SetRenderDrawColor(r, r8, g8, b8, a8);
    for (int row = 0; row < CHAR_H; ++row) {
        uint8_t line = glyph[row];
        for (int col = 0; col < 5; ++col) {
            if (line & (16 >> col)) {
                SDL_Rect rect = {x + col * scale, y + row * scale, scale, scale};
                SDL_RenderFillRect(r, &rect);
            }
        }
    }
}

static void draw_string(SDL_Renderer* r, int x, int y, const std::string& text,
                        int scale, uint32_t color) {
    int cx = x;
    for (char ch : text) {
        draw_char(r, cx, y, ch, scale, color);
        cx += 6 * scale;
    }
}

Renderer::Renderer() {
    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO);
    window = SDL_CreateWindow("Tetris",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        WIN_WIDTH, WIN_HEIGHT,
        SDL_WINDOW_SHOWN);
    renderer = SDL_CreateRenderer(window, -1,
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    last_tick = SDL_GetPerformanceCounter();
    fmt = SDL_AllocFormat(SDL_PIXELFORMAT_RGBA8888);
}

Renderer::~Renderer() {
    if (fmt) SDL_FreeFormat(fmt);
    if (renderer) SDL_DestroyRenderer(renderer);
    if (window) SDL_DestroyWindow(window);
    SDL_Quit();
}

uint32_t Renderer::map_rgba(uint8_t r, uint8_t g, uint8_t b, uint8_t a) const {
    return SDL_MapRGBA(fmt, r, g, b, a);
}

double Renderer::tick(int fps) {
    uint64_t now = SDL_GetPerformanceCounter();
    double dt = (double)(now - last_tick) / SDL_GetPerformanceFrequency();
    last_tick = now;
    return dt;
}

void Renderer::draw_rect(int x, int y, int w, int h, uint32_t color) {
    uint8_t r = (color >> 24) & 0xFF;
    uint8_t g = (color >> 16) & 0xFF;
    uint8_t b = (color >> 8) & 0xFF;
    uint8_t a = color & 0xFF;
    SDL_SetRenderDrawColor(renderer, r, g, b, a);
    SDL_Rect rect = {x, y, w, h};
    SDL_RenderFillRect(renderer, &rect);
}

void Renderer::draw_cell(int x, int y, int cell_size, uint32_t color, bool ghost) {
    int sz = cell_size - 1;
    if (ghost) {
        // Ghost: 只画边框
        uint8_t r = (color >> 24) & 0xFF;
        uint8_t g = (color >> 16) & 0xFF;
        uint8_t b = (color >> 8) & 0xFF;
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
        SDL_SetRenderDrawColor(renderer, r, g, b, GHOST_ALPHA);
        SDL_Rect rect = {x + 1, y + 1, sz - 1, sz - 1};
        SDL_RenderDrawRect(renderer, &rect);
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
        return;
    }

    // 主体
    draw_rect(x + 1, y + 1, sz - 1, sz - 1, color);

    // 高亮边 (左上)
    uint8_t r = std::min(255, (int)((color >> 24) & 0xFF) + 60);
    uint8_t g = std::min(255, (int)((color >> 16) & 0xFF) + 60);
    uint8_t b = std::min(255, (int)((color >> 8) & 0xFF) + 60);
    SDL_SetRenderDrawColor(renderer, r, g, b, 255);
    // 顶边
    SDL_RenderDrawLine(renderer, x + 1, y + 1, x + sz - 1, y + 1);
    // 左边
    SDL_RenderDrawLine(renderer, x + 1, y + 1, x + 1, y + sz - 1);

    // 阴影边 (右下)
    r = std::max(0, (int)((color >> 24) & 0xFF) - 60);
    g = std::max(0, (int)((color >> 16) & 0xFF) - 60);
    b = std::max(0, (int)((color >> 8) & 0xFF) - 60);
    SDL_SetRenderDrawColor(renderer, r, g, b, 255);
    SDL_RenderDrawLine(renderer, x + sz - 1, y + 1, x + sz - 1, y + sz - 1);
    SDL_RenderDrawLine(renderer, x + 1, y + sz - 1, x + sz - 1, y + sz - 1);
}

void Renderer::draw_text(int x, int y, const std::string& text, int size, uint32_t color) {
    int scale = size / 7;
    if (scale < 1) scale = 1;
    draw_string(renderer, x, y, text, scale, color);
}

void Renderer::draw_text_big(int x, int y, const std::string& text, uint32_t color) {
    // 用 scale=3 即 21px 高来模拟大字体
    int scale = 3;
    draw_string(renderer, x, y, text, scale, color);
}

void Renderer::draw_overlay(const std::string& line1, const std::string& line2) {
    // 半透明遮罩
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 160);
    SDL_Rect full = {0, 0, WIN_WIDTH, WIN_HEIGHT};
    SDL_RenderFillRect(renderer, &full);
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);

    int cx = WIN_WIDTH / 2;
    int cy = WIN_HEIGHT / 2;
    // 估算文字宽度来居中
    int scale1 = 4, scale2 = 2;
    int w1 = (int)line1.size() * 6 * scale1;
    int w2 = (int)line2.size() * 6 * scale2;
    draw_string(renderer, cx - w1 / 2, cy - 30, line1, scale1, WHITE);
    if (!line2.empty()) {
        draw_string(renderer, cx - w2 / 2, cy + 20, line2, scale2, GRAY);
    }
}

void Renderer::render(const Board& board, const Piece* active,
                      const Piece* ghost, const Piece* next,
                      const Scorer& scorer, const std::string& state_str) {
    // 清屏
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    SDL_RenderClear(renderer);

    // 游戏区背景
    draw_rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT, DARK_GRAY);

    // 网格线
    uint8_t gv = 0x30;
    SDL_SetRenderDrawColor(renderer, gv, gv, gv, 255);
    for (int r = 0; r <= ROWS; ++r) {
        int y = r * CELL_SIZE;
        SDL_RenderDrawLine(renderer, 0, y, BOARD_WIDTH, y);
    }
    for (int c = 0; c <= COLS; ++c) {
        int x = c * CELL_SIZE;
        SDL_RenderDrawLine(renderer, x, 0, x, BOARD_HEIGHT);
    }

    // 绘制棋盘上已锁定的方块
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            int v = board.grid[r][c];
            if (v > 0) {
                draw_cell(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE,
                          PIECE_COLORS[v - 1], false);
            }
        }
    }

    // Ghost
    if (ghost) {
        uint32_t color = PIECE_COLORS[ghost->type];
        for (auto& b : ghost->get_blocks()) {
            if (b.row >= 0) {
                draw_cell(b.col * CELL_SIZE, b.row * CELL_SIZE, CELL_SIZE, color, true);
            }
        }
    }

    // 活动方块
    if (active) {
        uint32_t color = PIECE_COLORS[active->type];
        for (auto& b : active->get_blocks()) {
            if (b.row >= 0) {
                draw_cell(b.col * CELL_SIZE, b.row * CELL_SIZE, CELL_SIZE, color, false);
            }
        }
    }

    // ---- 侧边栏 ----
    int sx = BOARD_WIDTH + 10;

    draw_text(sx, 10, "NEXT:", FONT_SIZE_SMALL, WHITE);

    // 预览方块
    if (next) {
        uint32_t color = PIECE_COLORS[next->type];
        uint16_t m = next->mask();
        for (int r = 0; r < 4; ++r) {
            for (int c = 0; c < 4; ++c) {
                int bit = 15 - (r * 4 + c);
                if ((m >> bit) & 1) {
                    int px = sx + c * 22;
                    int py = 35 + r * 22;
                    draw_rect(px + 1, py + 1, 20, 20, color);
                    // 高亮边
                    uint8_t hr = std::min(255, (int)((color >> 24) & 0xFF) + 50);
                    uint8_t hg = std::min(255, (int)((color >> 16) & 0xFF) + 50);
                    uint8_t hb = std::min(255, (int)((color >> 8) & 0xFF) + 50);
                    SDL_SetRenderDrawColor(renderer, hr, hg, hb, 255);
                    SDL_RenderDrawLine(renderer, px + 1, py + 1, px + 19, py + 1);
                    SDL_RenderDrawLine(renderer, px + 1, py + 1, px + 1, py + 19);
                    // 阴影
                    hr = std::max(0, (int)((color >> 24) & 0xFF) - 50);
                    hg = std::max(0, (int)((color >> 16) & 0xFF) - 50);
                    hb = std::max(0, (int)((color >> 8) & 0xFF) - 50);
                    SDL_SetRenderDrawColor(renderer, hr, hg, hb, 255);
                    SDL_RenderDrawLine(renderer, px + 19, py + 1, px + 19, py + 19);
                    SDL_RenderDrawLine(renderer, px + 1, py + 19, px + 19, py + 19);
                }
            }
        }
    }

    // 分数信息
    int iy = 160;
    draw_text(sx, iy, "SCORE", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 20, std::to_string(scorer.score), FONT_SIZE_NORMAL, WHITE);

    iy += 55;
    draw_text(sx, iy, "LEVEL", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 20, std::to_string(scorer.level), FONT_SIZE_NORMAL, WHITE);

    iy += 55;
    draw_text(sx, iy, "LINES", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 20, std::to_string(scorer.lines), FONT_SIZE_NORMAL, WHITE);

    // 操作提示
    iy += 80;
    draw_text(sx, iy, "MOVE", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 16, "ARROW KEYS", FONT_SIZE_SMALL, WHITE);
    iy += 35;
    draw_text(sx, iy, "ROTATE", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 16, "UP", FONT_SIZE_SMALL, WHITE);
    iy += 35;
    draw_text(sx, iy, "HARD DROP", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 16, "SPACE", FONT_SIZE_SMALL, WHITE);
    iy += 35;
    draw_text(sx, iy, "PAUSE", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 16, "P", FONT_SIZE_SMALL, WHITE);
    iy += 35;
    draw_text(sx, iy, "RESET", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 16, "R", FONT_SIZE_SMALL, WHITE);
    iy += 35;
    draw_text(sx, iy, "QUIT", FONT_SIZE_SMALL, GRAY);
    draw_text(sx, iy + 16, "ESC", FONT_SIZE_SMALL, WHITE);

    // 状态叠加层
    if (state_str == "paused") {
        draw_overlay("PAUSED", "Press P to resume");
    } else if (state_str == "gameover") {
        std::string final_score = "Final Score: " + std::to_string(scorer.score);
        draw_overlay("GAME OVER", final_score);
    } else if (state_str == "start") {
        draw_overlay("TETRIS", "Press any key to start");
    }

    SDL_RenderPresent(renderer);
}
