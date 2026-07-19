"""渲染器"""
import pygame
from constants import (
    COLS, ROWS, CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT, WIN_WIDTH, WIN_HEIGHT,
    SIDEBAR_WIDTH, BLACK, WHITE, GRAY, DARK_GRAY, GHOST_ALPHA,
    PIECE_COLORS, FONT_NAME, FONT_SIZE_SMALL, FONT_SIZE_NORMAL, FONT_SIZE_LARGE,
    _CHINESE_FONTS,
)


class Renderer:
    @staticmethod
    def _load_font(size: int) -> pygame.font.Font:
        """加载字体，优先中文字体，找不到则回退到系统默认"""
        # 尝试中文字体（按优先级）
        for name in _CHINESE_FONTS:
            try:
                font = pygame.font.SysFont(name, size)
                # 验证是否真的支持中文：尝试渲染一个中文字符检查尺寸
                test = font.render("测", True, (255, 255, 255))
                if test.get_width() > 5:  # 宽字体不渲染中文时宽度接近 0
                    return font
            except Exception:
                continue
        # 最终回退
        if FONT_NAME:
            return pygame.font.Font(FONT_NAME, size)
        return pygame.font.Font(None, size)

    def __init__(self):
        self.screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self._font_small = self._load_font(FONT_SIZE_SMALL)
        self._font_normal = self._load_font(FONT_SIZE_NORMAL)
        self._font_large = self._load_font(FONT_SIZE_LARGE)

        self._cell_surface = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self._ghost_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)

    def tick(self, fps: int = 60) -> float:
        return self.clock.tick(fps) / 1000.0

    # ---- 主渲染入口 ----

    def render(self, board, active_piece, ghost, next_piece, scorer, state: str):
        self.screen.fill(BLACK)

        # 游戏区背景
        pygame.draw.rect(self.screen, DARK_GRAY, (0, 0, BOARD_WIDTH, BOARD_HEIGHT))

        self._draw_grid()
        self._draw_board(board)
        self._draw_ghost(ghost)
        self._draw_piece(active_piece)
        self._draw_sidebar(next_piece, scorer)

        if state == "paused":
            self._draw_overlay("PAUSED")
        elif state == "gameover":
            self._draw_overlay("GAME OVER")
            self._draw_gameover_score(scorer)

        pygame.display.flip()

    # ---- 内部绘制 ----

    def _draw_grid(self):
        for x in range(COLS + 1):
            pygame.draw.line(self.screen, GRAY, (x * CELL_SIZE, 0), (x * CELL_SIZE, BOARD_HEIGHT))
        for y in range(ROWS + 1):
            pygame.draw.line(self.screen, GRAY, (0, y * CELL_SIZE), (BOARD_WIDTH, y * CELL_SIZE))

    def _draw_board(self, board):
        for r in range(ROWS):
            for c in range(COLS):
                val = board.grid[r][c]
                if val:
                    self._draw_cell(c, r, PIECE_COLORS[val - 1])

    def _draw_piece(self, piece):
        if piece is None:
            return
        for col, row in piece.get_blocks():
            if row >= 0:
                self._draw_cell(col, row, PIECE_COLORS[piece.type])

    def _draw_ghost(self, ghost):
        if ghost is None:
            return
        for col, row in ghost.get_blocks():
            if row >= 0 and ghost.shape[(row - ghost.y) % 4][(col - ghost.x) % 4]:
                self._draw_cell_ghost(col, row, PIECE_COLORS[ghost.type])

    def _draw_cell(self, col: int, row: int, color):
        x = col * CELL_SIZE
        y = row * CELL_SIZE
        # 主体
        pygame.draw.rect(self.screen, color, (x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2))
        # 高亮边（左上）
        lighter = tuple(min(255, c + 60) for c in color)
        pygame.draw.line(self.screen, lighter, (x + 1, y + 1), (x + CELL_SIZE - 2, y + 1), 2)
        pygame.draw.line(self.screen, lighter, (x + 1, y + 1), (x + 1, y + CELL_SIZE - 2), 2)
        # 阴影边（右下）
        darker = tuple(max(0, c - 60) for c in color)
        pygame.draw.line(self.screen, darker, (x + 2, y + CELL_SIZE - 2), (x + CELL_SIZE - 1, y + CELL_SIZE - 2), 2)
        pygame.draw.line(self.screen, darker, (x + CELL_SIZE - 2, y + 2), (x + CELL_SIZE - 2, y + CELL_SIZE - 1), 2)

    def _draw_cell_ghost(self, col: int, row: int, color):
        x = col * CELL_SIZE
        y = row * CELL_SIZE
        self._ghost_surface.fill((0, 0, 0, 0))
        pygame.draw.rect(self._ghost_surface, (*color, 60), (1, 1, CELL_SIZE - 2, CELL_SIZE - 2))
        self.screen.blit(self._ghost_surface, (x, y))

    def _draw_sidebar(self, next_piece, scorer):
        sx = BOARD_WIDTH + 10

        # NEXT
        self.screen.blit(self._font_normal.render("NEXT", True, WHITE), (sx, 10))
        if next_piece:
            shape = next_piece.get_shape(0)
            color = PIECE_COLORS[next_piece.type]
            for r in range(4):
                for c in range(4):
                    if shape[r][c]:
                        px = sx + c * (CELL_SIZE - 6)
                        py = 40 + r * (CELL_SIZE - 6)
                        pygame.draw.rect(self.screen, color, (px, py, CELL_SIZE - 8, CELL_SIZE - 8))

        # SCORE
        y = 180
        for label, value in [
            ("SCORE", scorer.score),
            ("LEVEL", scorer.level),
            ("LINES", scorer.lines),
        ]:
            self.screen.blit(self._font_small.render(label, True, GRAY), (sx, y))
            y += 22
            self.screen.blit(self._font_normal.render(str(value), True, WHITE), (sx, y))
            y += 40

        # 操作提示
        y += 30
        for text in [
            "← → 移动",
            "↓ 软降  ↑ 旋转",
            "空格 硬降",
            "P 暂停  R 重置",
            "ESC 退出",
        ]:
            self.screen.blit(self._font_small.render(text, True, GRAY), (sx, y))
            y += 22

    def _draw_overlay(self, text: str):
        overlay = pygame.Surface((WIN_WIDTH, WIN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        txt = self._font_large.render(text, True, WHITE)
        tr = txt.get_rect(center=(WIN_WIDTH // 2, WIN_HEIGHT // 2))
        self.screen.blit(txt, tr)

    def _draw_gameover_score(self, scorer):
        txt = self._font_normal.render(f"Final Score: {scorer.score}", True, WHITE)
        tr = txt.get_rect(center=(WIN_WIDTH // 2, WIN_HEIGHT // 2 + 50))
        self.screen.blit(txt, tr)
        txt2 = self._font_small.render("Press R to restart", True, GRAY)
        tr2 = txt2.get_rect(center=(WIN_WIDTH // 2, WIN_HEIGHT // 2 + 90))
        self.screen.blit(txt2, tr2)
