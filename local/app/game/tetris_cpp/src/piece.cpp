#include "piece.h"
#include <algorithm>

Piece::Piece(int t) : type(t), rotation(0), x(SPAWN_X), y(SPAWN_Y) {
    auto& sd = (*ALL_SHAPES[type])[rotation];
    width = sd.width;
    height = sd.height;
}

uint16_t Piece::mask() const {
    return (*ALL_SHAPES[type])[rotation].mask;
}

bool Piece::bit_at(uint16_t m, int row, int col) const {
    int bit = 15 - (row * 4 + col);
    return (m >> bit) & 1;
}

std::vector<Block> Piece::get_blocks() const {
    std::vector<Block> blocks;
    uint16_t m = mask();
    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            if (bit_at(m, r, c)) {
                blocks.push_back({x + c, y + r});
            }
        }
    }
    return blocks;
}

bool Piece::can_place(int px, int py, int rot, const int grid[ROWS][COLS]) const {
    uint16_t m = (*ALL_SHAPES[type])[rot].mask;
    for (int r = 0; r < 4; ++r) {
        for (int c = 0; c < 4; ++c) {
            if (!bit_at(m, r, c)) continue;
            int nr = py + r;
            int nc = px + c;
            // 允许顶部以上
            if (nc < 0 || nc >= COLS || nr >= ROWS) return false;
            if (nr >= 0 && grid[nr][nc] != 0) return false;
        }
    }
    return true;
}

bool Piece::is_above_board() const {
    for (auto& b : get_blocks()) {
        if (b.row < 0) return true;
    }
    return false;
}

bool Piece::try_move(int dx, int dy, const int grid[ROWS][COLS]) {
    if (can_place(x + dx, y + dy, rotation, grid)) {
        x += dx;
        y += dy;
        return true;
    }
    return false;
}

bool Piece::try_rotate(const int grid[ROWS][COLS], bool clockwise) {
    int from = rotation;
    int to;
    if (clockwise) {
        to = (rotation + 1) % 4;
    } else {
        to = (rotation + 3) % 4;
    }

    const KickEntry* kick;
    int key;
    if (clockwise) {
        key = from;
    } else {
        // 反向: to -> from 的顺时针旋转的反向 (取反偏移)
        key = to;
    }

    if (type == 0) {  // I piece
        kick = &WALL_KICKS_I[key];
    } else {
        kick = &WALL_KICKS_JLSTZ[key];
    }

    const auto& tests = kick->tests;
    for (int i = 0; i < 5; ++i) {
        int dx = tests[i].first;
        int dy = tests[i].second;

        // 顺时针: 正向偏移; 逆时针: 取反
        if (!clockwise) {
            dx = -dx;
            dy = -dy;
        }

        if (can_place(x + dx, y + dy, to, grid)) {
            x += dx;
            y += dy;
            rotation = to;
            auto& sd = (*ALL_SHAPES[type])[rotation];
            width = sd.width;
            height = sd.height;
            return true;
        }
    }
    return false;
}

bool Piece::in_bounds(int col, int row) const {
    return col >= 0 && col < COLS && row < ROWS;
}

// ---- BagRandomizer ----

int BagRandomizer::next() {
    if (bag.empty() || index >= (int)bag.size()) {
        refill();
    }
    return bag[index++];
}

void BagRandomizer::refill() {
    bag = {0, 1, 2, 3, 4, 5, 6};
    std::shuffle(bag.begin(), bag.end(), rng);
    index = 0;
}
