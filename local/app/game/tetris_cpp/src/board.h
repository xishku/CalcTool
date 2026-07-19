#pragma once
#include "constants.h"
#include "piece.h"

class Board {
public:
    Board();
    void reset();

    // 锁定方块到棋盘，返回消除行数
    int lock_piece(const Piece& piece);

    // grid[r][c]: 0=空, 1..7=颜色编号
    int grid[ROWS][COLS];

    bool is_collision(const Piece& piece) const;

private:
    int clear_lines();
};
