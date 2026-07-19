"""计分 & 等级管理"""
from constants import SCORE_TABLE, LINES_PER_LEVEL, MAX_LEVEL, SPEED_TABLE


class Scorer:
    def __init__(self):
        self.score = 0
        self.level = 1
        self.lines = 0

    def add_clear(self, lines_cleared: int):
        if lines_cleared < 1:
            return
        self.score += SCORE_TABLE.get(lines_cleared, 800) * self.level
        self.lines += lines_cleared
        self.level = min(MAX_LEVEL, 1 + self.lines // LINES_PER_LEVEL)

    def add_soft_drop(self, cells: int = 1):
        self.score += cells

    def add_hard_drop(self, cells: int):
        self.score += cells * 2

    def drop_speed_ms(self) -> int:
        return SPEED_TABLE.get(self.level, 100)

    def reset(self):
        self.score = 0
        self.level = 1
        self.lines = 0
