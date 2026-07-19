#include "board.h"
#include <cstring>

Board::Board() { reset(); }

void Board::reset() {
    std::memset(grid, 0, sizeof(grid));
}

int Board::lock_piece(const Piece& piece) {
    for (auto& b : piece.get_blocks()) {
        if (b.row >= 0 && b.row < ROWS && b.col >= 0 && b.col < COLS) {
            grid[b.row][b.col] = piece.type + 1;
        }
    }
    return clear_lines();
}

bool Board::is_collision(const Piece& piece) const {
    return !piece.can_place(piece.x, piece.y, piece.rotation, grid);
}

int Board::clear_lines() {
    int cleared = 0;
    for (int r = ROWS - 1; r >= 0; --r) {
        bool full = true;
        for (int c = 0; c < COLS; ++c) {
            if (grid[r][c] == 0) { full = false; break; }
        }
        if (full) {
            ++cleared;
            // 将该行之上所有行下移
            for (int rr = r; rr > 0; --rr) {
                for (int c = 0; c < COLS; ++c) {
                    grid[rr][c] = grid[rr - 1][c];
                }
            }
            // 顶部补空行
            for (int c = 0; c < COLS; ++c) grid[0][c] = 0;
            ++r;  // 重新检查当前行
        }
    }
    return cleared;
}
