#pragma once
#include "constants.h"
#include <string>
#include <vector>
#include <random>
#include <utility>

// 单块坐标
struct Block {
    int col, row;
};

class Piece {
public:
    int type;        // 0..6
    int rotation;    // 0..3
    int x, y;        // 棋盘坐标 (col, row)
    int width, height;

    Piece(int type = 0);

    // 获取所有方块坐标 (全局棋盘坐标)
    std::vector<Block> get_blocks() const;
    // 获取位掩码
    uint16_t mask() const;

    // 尝试移动/旋转, grid=棋盘 (非0表示占用)
    bool try_move(int dx, int dy, const int grid[ROWS][COLS]);
    bool try_rotate(const int grid[ROWS][COLS], bool clockwise = true);

    // 碰撞检测
    bool can_place(int px, int py, int rot, const int grid[ROWS][COLS]) const;
    bool is_above_board() const;

    // 判断 coll/row 位是否在棋盘上
    bool in_bounds(int col, int row) const;

private:
    // 位操作辅助
    bool bit_at(uint16_t m, int row, int col) const;
};

// 7-Bag 随机生成器
class BagRandomizer {
public:
    int next();       // 返回方块类型 0..6
private:
    std::mt19937 rng{std::random_device{}()};
    std::vector<int> bag;
    int index = 0;
    void refill();
};
