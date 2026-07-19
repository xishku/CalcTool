#pragma once
#include <cstdint>
#include <array>
#include <string>

// ==================== 棋盘 ====================
constexpr int COLS = 10;
constexpr int ROWS = 20;
constexpr int CELL_SIZE = 30;
constexpr int BOARD_WIDTH = COLS * CELL_SIZE;    // 300
constexpr int BOARD_HEIGHT = ROWS * CELL_SIZE;   // 600
constexpr int SIDEBAR_WIDTH = 180;
constexpr int WIN_WIDTH = BOARD_WIDTH + SIDEBAR_WIDTH;
constexpr int WIN_HEIGHT = BOARD_HEIGHT;

// ==================== 颜色 0xRRGGBBAA ====================
constexpr uint32_t BLACK     = 0x000000FF;
constexpr uint32_t WHITE     = 0xFFFFFFFF;
constexpr uint32_t GRAY      = 0x808080FF;
constexpr uint32_t DARK_GRAY = 0x404040FF;
constexpr uint8_t  GHOST_ALPHA = 60;

constexpr uint32_t PIECE_COLORS[8] = {
    0x00FFFFFF, // I - cyan
    0xFFFF00FF, // O - yellow
    0x800080FF, // T - purple
    0x00FF00FF, // S - green
    0xFF0000FF, // Z - red
    0x0000FFFF, // J - blue
    0xFF8800FF, // L - orange
    0x808080FF, // ghost
};

// ==================== 方块名称 ====================
constexpr const char* PIECE_NAMES[7] = {"I", "O", "T", "S", "Z", "J", "L"};

// ==================== 方块形状 (7种 × 4旋转, uint16_t 紧凑存储) ====================
// 每个 uint16_t 的 16 bits 表示 4x4 网格 (行主序, bit15=左上角)
struct ShapeData {
    uint16_t mask;        // 位掩码
    int width;            // 实际占用宽度 (用于居中/碰撞)
    int height;           // 实际占用高度
};

constexpr std::array<ShapeData, 4> SHAPE_I = {{
    {0x0F00, 4, 1},  // rot0: .... / XXXX / .... / ....
    {0x2222, 1, 4},  // rot1: .X.. / .X.. / .X.. / .X..
    {0x00F0, 4, 1},  // rot2
    {0x4444, 1, 4},  // rot3
}};

constexpr std::array<ShapeData, 4> SHAPE_O = {{
    {0x6600, 2, 2},  // .XX. / .XX.
    {0x6600, 2, 2},
    {0x6600, 2, 2},
    {0x6600, 2, 2},
}};

constexpr std::array<ShapeData, 4> SHAPE_T = {{
    {0x4E00, 3, 2},  // .X.. / XXX.
    {0x4640, 2, 3},  // .X.. / .XX. / .X..
    {0x0E40, 3, 2},  // .... / XXX. / .X..
    {0x4C40, 2, 3},  // .X.. / XX.. / .X..
}};

constexpr std::array<ShapeData, 4> SHAPE_S = {{
    {0x6C00, 3, 2},  // .XX. / XX..
    {0x4620, 2, 3},  // .X.. / .XX. / ..X.
    {0x06C0, 3, 2},  // .... / .XX. / XX..
    {0x8C40, 2, 3},  // X... / XX.. / .X..
}};

constexpr std::array<ShapeData, 4> SHAPE_Z = {{
    {0xC600, 3, 2},  // XX.. / .XX.
    {0x2640, 2, 3},  // ..X. / .XX. / .X..
    {0x0C60, 3, 2},  // .... / XX.. / .XX.
    {0x4C80, 2, 3},  // .X.. / XX.. / X...
}};

constexpr std::array<ShapeData, 4> SHAPE_J = {{
    {0x8E00, 3, 2},  // X... / XXX.
    {0x6440, 2, 3},  // .XX. / .X.. / .X..
    {0x0E20, 3, 2},  // .... / XXX. / ..X.
    {0x44C0, 2, 3},  // .X.. / .X.. / XX..
}};

constexpr std::array<ShapeData, 4> SHAPE_L = {{
    {0x2E00, 3, 2},  // ..X. / XXX.
    {0x4460, 2, 3},  // .X.. / .X.. / .XX.
    {0x0E80, 3, 2},  // .... / XXX. / X...
    {0xC440, 2, 3},  // XX.. / .X.. / .X..
}};

constexpr std::array<const std::array<ShapeData, 4>*, 7> ALL_SHAPES = {{
    &SHAPE_I, &SHAPE_O, &SHAPE_T, &SHAPE_S, &SHAPE_Z, &SHAPE_J, &SHAPE_L
}};

// ==================== SRS 墙踢 ====================
// 每个 entry: 5 组 (dx, dy) 测试偏移
struct KickEntry {
    std::array<std::pair<int, int>, 5> tests;
};

// from_rot, to_rot -> KickEntry
// JLSTZ: 0->1, 1->2, 2->3, 3->0 以及反向
constexpr KickEntry WALL_KICKS_JLSTZ[4] = {
    // 0 -> 1 (逆时针)  /  3 <- 0 (顺时针) 的反向
    {{{ {0,0}, {-1,0}, {-1,1}, {0,-2}, {-1,-2} }}},
    // 1 -> 2  /  0 <- 1
    {{{ {0,0}, {1,0}, {1,-1}, {0,2}, {1,2} }}},
    // 2 -> 3  /  1 <- 2
    {{{ {0,0}, {1,0}, {1,1}, {0,-2}, {1,-2} }}},
    // 3 -> 0  /  2 <- 3
    {{{ {0,0}, {-1,0}, {-1,-1}, {0,2}, {-1,2} }}},
};

// I 方块专用墙踢
constexpr KickEntry WALL_KICKS_I[4] = {
    {{{ {0,0}, {-2,0}, {1,0}, {-2,-1}, {1,2} }}},
    {{{ {0,0}, {-1,0}, {2,0}, {-1,2}, {2,-1} }}},
    {{{ {0,0}, {2,0}, {-1,0}, {2,1}, {-1,-2} }}},
    {{{ {0,0}, {1,0}, {-2,0}, {1,-2}, {-2,1} }}},
};

// ==================== 计分 ====================
constexpr int SCORE_TABLE[5] = {0, 100, 300, 500, 800};  // 0/1/2/3/4 行消除分数 (×level)
constexpr int LINES_PER_LEVEL = 10;
constexpr int MAX_LEVEL = 15;

// 每个等级的下落间隔 (ms)
constexpr int SPEED_TABLE[MAX_LEVEL + 1] = {
    0,  800, 717, 633, 550, 467, 383, 300, 217, 133,
    100, 100, 100, 100, 100, 100,
};

// ==================== DAS / ARR ====================
constexpr double DAS_DELAY = 167.0;   // ms
constexpr double ARR_INTERVAL = 33.0;  // ms

// ==================== 锁定 / 软降 ====================
constexpr double LOCK_DELAY_MS = 500.0;
constexpr double SOFT_DROP_MS = 50.0;

// ==================== 字体 ====================
constexpr int FONT_SIZE_SMALL = 18;
constexpr int FONT_SIZE_NORMAL = 24;
constexpr int FONT_SIZE_LARGE = 36;

// ==================== 音效开关 ====================
constexpr bool SOUND_ENABLED = true;
constexpr bool MUSIC_ENABLED = false;

// 方块初始 X 坐标
constexpr int SPAWN_X = 3;  // COLS/2 - 2
constexpr int SPAWN_Y = -1;
