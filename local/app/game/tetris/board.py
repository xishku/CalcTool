"""棋盘逻辑"""
from constants import COLS, ROWS


class Board:
    """20×10 棋盘，存储已固定的方块"""

    def __init__(self):
        self.grid = [[0] * COLS for _ in range(ROWS)]

    def lock_piece(self, piece) -> int:
        """将方块固定到棋盘，返回消除的行数"""
        for col, row in piece.get_blocks():
            if 0 <= row < ROWS and 0 <= col < COLS:
                self.grid[row][col] = piece.type + 1  # 1-7 对应颜色

        cleared = self._clear_lines()
        return cleared

    def _clear_lines(self) -> int:
        """消除满行，返回消除行数"""
        full_rows = [r for r in range(ROWS) if all(self.grid[r][c] for c in range(COLS))]
        count = len(full_rows)

        if count > 0:
            # 从下往上重建棋盘
            new_grid = [[0] * COLS for _ in range(count)]
            for r in range(ROWS):
                if r not in full_rows:
                    new_grid.append(self.grid[r][:])
            self.grid = new_grid

        return count

    def is_collision(self, piece) -> bool:
        """检查方块是否与已有方块碰撞"""
        return not piece._can_place(piece.x, piece.y, piece.rotation, self.grid)

    def reset(self):
        self.grid = [[0] * COLS for _ in range(ROWS)]
