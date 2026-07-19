"""方块定义 & 旋转（SRS 墙踢系统）"""
import random
from constants import SHAPES, PIECE_NAMES, WALL_KICKS_JLSTZ, WALL_KICKS_I, COLS, ROWS


class Piece:
    """单个活动方块"""

    def __init__(self, name: str):
        self.name = name
        self.type = PIECE_NAMES.index(name)
        self.rotation = 0
        self.x = COLS // 2 - 2  # 从中间偏左生成
        self.y = -1              # 从顶部上方开始（避免立即碰撞）
        self.shape = SHAPES[name][0]

    def get_shape(self, rotation: int = None):
        """获取指定旋转的矩阵"""
        r = rotation if rotation is not None else self.rotation
        return SHAPES[self.name][r]

    def get_blocks(self) -> list[tuple[int, int]]:
        """返回方块占用的所有格子 (col, row)"""
        blocks = []
        for r in range(4):
            for c in range(4):
                if self.shape[r][c]:
                    blocks.append((self.x + c, self.y + r))
        return blocks

    def try_move(self, dx: int, dy: int, board: list[list[int]]) -> bool:
        """尝试移动并返回是否成功"""
        if self._can_place(self.x + dx, self.y + dy, self.rotation, board):
            self.x += dx
            self.y += dy
            return True
        return False

    def try_rotate(self, board: list[list[int]], clockwise: bool = True) -> bool:
        """SRS 旋转 + 墙踢"""
        from_rot = self.rotation
        to_rot = (from_rot + 1) % 4 if clockwise else (from_rot + 3) % 4

        kicks = WALL_KICKS_I if self.name == "I" else WALL_KICKS_JLSTZ
        offsets = kicks.get((from_rot, to_rot), [(0, 0)])

        for dx, dy in offsets:
            if self._can_place(self.x + dx, self.y - dy, to_rot, board):
                self.x += dx
                self.y -= dy
                self.rotation = to_rot
                self.shape = self.get_shape()
                return True
        return False

    def _can_place(self, px: int, py: int, rotation: int, board: list[list[int]]) -> bool:
        """检查方块在指定位置是否合法"""
        shape = self.get_shape(rotation)
        for r in range(4):
            for c in range(4):
                if shape[r][c]:
                    col = px + c
                    row = py + r
                    if col < 0 or col >= COLS or row >= ROWS:
                        return False
                    if row >= 0 and board[row][col]:
                        return False
        return True

    def is_above_board(self) -> bool:
        """检查是否有任何块在顶部上方（spawn 失败检测）"""
        for r in range(4):
            for c in range(4):
                if self.shape[r][c]:
                    if self.y + r < 0:
                        return True
        return False


class BagRandomizer:
    """7-Bag 随机系统"""

    def __init__(self):
        self.bag = []

    def next(self) -> str:
        if not self.bag:
            self.bag = list(PIECE_NAMES)
            random.shuffle(self.bag)
        return self.bag.pop()
