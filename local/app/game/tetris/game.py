"""游戏主循环 & 状态机"""
import pygame
from constants import (
    COLS, ROWS, DAS_DELAY, ARR_INTERVAL, LOCK_DELAY_MS,
    SOFT_DROP_MS, PIECE_NAMES, SOUND_ENABLED, MUSIC_ENABLED,
)
from board import Board
from piece import Piece, BagRandomizer
from scorer import Scorer
from renderer import Renderer


class Game:
    def __init__(self):
        pygame.init()
        self.renderer = Renderer()
        self.board = Board()
        self.scorer = Scorer()
        self.randomizer = BagRandomizer()

        self.active_piece: Piece | None = None
        self.ghost_piece: Piece | None = None
        self.next_piece: Piece | None = None

        self.state = "start"  # start → playing → paused / gameover
        self.drop_timer = 0.0
        self.lock_timer = 0.0
        self.soft_dropping = False

        # DAS / ARR 状态
        self._das_timer = {"left": 0.0, "right": 0.0}
        self._das_active = {"left": False, "right": False}
        self._das_repeat = {"left": 0.0, "right": 0.0}
        self._sfx_loaded = False

    def _sfx(self, name: str, *args):
        """懒加载音效模块并播放"""
        if not SOUND_ENABLED:
            return
        if not self._sfx_loaded:
            try:
                import sound as _snd
                self._snd = _snd
            except Exception:
                self._snd = None
            self._sfx_loaded = True
        if self._snd is None:
            return
        fn = getattr(self._snd, f"play_{name}", None)
        if fn:
            try:
                fn(*args)
            except Exception:
                pass

    def run(self):
        self._start_music()
        running = True
        while running:
            dt = self.renderer.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_keydown(event.key)
                elif event.type == pygame.KEYUP:
                    self._handle_keyup(event.key)

            if self.state == "playing":
                self._update(dt)
            elif self.state == "start":
                self._start_game()

            self.renderer.render(
                self.board, self.active_piece, self.ghost_piece,
                self.next_piece, self.scorer, self.state,
            )

        self._stop_music()
        self._cleanup_music()
        pygame.quit()

    def _start_music(self):
        if not MUSIC_ENABLED:
            return
        try:
            import sound
            sound.start_music()
        except Exception:
            pass

    def _stop_music(self):
        try:
            import sound
            sound.stop_music()
        except Exception:
            pass

    def _cleanup_music(self):
        try:
            import sound
            sound.cleanup_music()
        except Exception:
            pass

    def _start_game(self):
        self.board.reset()
        self.scorer.reset()
        self.randomizer = BagRandomizer()
        self._spawn_piece()
        self.state = "playing"
        self._sfx("game_start")

    def _spawn_piece(self):
        if self.next_piece is None:
            name = self.randomizer.next()
            self.next_piece = Piece(name)

        self.active_piece = self.next_piece
        self.next_piece = Piece(self.randomizer.next())
        self.drop_timer = 0.0
        self.lock_timer = 0.0

        # 检测游戏结束
        if self.board.is_collision(self.active_piece) or self.active_piece.is_above_board():
            self.state = "gameover"
            self.active_piece = None
            self._sfx("game_over")

        self._update_ghost()

    def _update_ghost(self):
        if self.active_piece is None:
            self.ghost_piece = None
            return
        ghost = Piece(self.active_piece.name)
        ghost.x = self.active_piece.x
        ghost.y = self.active_piece.y
        ghost.rotation = self.active_piece.rotation
        ghost.shape = ghost.get_shape()
        while ghost._can_place(ghost.x, ghost.y + 1, ghost.rotation, self.board.grid):
            ghost.y += 1
        self.ghost_piece = ghost

    def _update(self, dt: float):
        if self.active_piece is None:
            return

        # DAS / ARR 左右移动
        dt_ms = dt * 1000
        for direction, dx in [("left", -1), ("right", 1)]:
            if self._das_active[direction]:
                self._das_timer[direction] += dt_ms
                if self._das_timer[direction] >= DAS_DELAY:
                    self._das_repeat[direction] += dt_ms
                    while self._das_repeat[direction] >= ARR_INTERVAL:
                        self._move_piece(dx, 0)
                        self._das_repeat[direction] -= ARR_INTERVAL

        # 自动下落
        speed = SOFT_DROP_MS if self.soft_dropping else self.scorer.drop_speed_ms()
        self.drop_timer += dt_ms
        while self.drop_timer >= speed:
            moved = self._move_piece(0, 1)
            self.drop_timer -= speed
            if self.soft_dropping and moved:
                self.scorer.add_soft_drop()

        # 锁定延迟
        on_ground = not self.active_piece._can_place(
            self.active_piece.x, self.active_piece.y + 1,
            self.active_piece.rotation, self.board.grid,
        )
        if on_ground:
            self.lock_timer += dt_ms
            if self.lock_timer >= LOCK_DELAY_MS:
                self._lock_piece()
        else:
            self.lock_timer = 0.0

    def _move_piece(self, dx: int, dy: int) -> bool:
        if self.active_piece is None:
            return False
        moved = self.active_piece.try_move(dx, dy, self.board.grid)
        if moved:
            self._update_ghost()
            self._sfx("move")
            # 移动重置锁定延迟
            if dx != 0:
                self.lock_timer = 0.0
        return moved

    def _rotate_piece(self):
        if self.active_piece is None:
            return
        if self.active_piece.try_rotate(self.board.grid):
            self._update_ghost()
            self.lock_timer = 0.0
            self._sfx("rotate")

    def _hard_drop(self):
        if self.active_piece is None:
            return
        cells = 0
        while self.active_piece._can_place(
            self.active_piece.x, self.active_piece.y + 1,
            self.active_piece.rotation, self.board.grid,
        ):
            self.active_piece.y += 1
            cells += 1
        self.scorer.add_hard_drop(cells)
        self._sfx("hard_drop")
        self._lock_piece()

    def _lock_piece(self):
        if self.active_piece is None:
            return
        cleared = self.board.lock_piece(self.active_piece)
        old_level = self.scorer.level
        if cleared:
            self.scorer.add_clear(cleared)
            self._sfx("clear", cleared)
            if self.scorer.level > old_level:
                self._sfx("level_up")
        else:
            self._sfx("lock")
        self._spawn_piece()

    # ---- 输入处理 ----

    def _handle_keydown(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False

        if self.state == "gameover":
            if key == pygame.K_r:
                self.state = "start"
            return True

        if self.state == "start":
            return True

        if key == pygame.K_p:
            if self.state == "playing":
                self.state = "paused"
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
            elif self.state == "paused":
                self.state = "playing"
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
            return True

        if self.state == "paused":
            if key == pygame.K_r:
                self.state = "start"
            return True

        # playing 状态
        if key == pygame.K_LEFT:
            self._move_piece(-1, 0)
            self._das_active["left"] = True
            self._das_timer["left"] = 0.0
            self._das_repeat["left"] = 0.0
        elif key == pygame.K_RIGHT:
            self._move_piece(1, 0)
            self._das_active["right"] = True
            self._das_timer["right"] = 0.0
            self._das_repeat["right"] = 0.0
        elif key == pygame.K_DOWN:
            self.soft_dropping = True
        elif key == pygame.K_UP:
            self._rotate_piece()
        elif key == pygame.K_SPACE:
            self._hard_drop()
        elif key == pygame.K_r:
            self.state = "start"

        return True

    def _handle_keyup(self, key: int):
        if key == pygame.K_LEFT:
            self._das_active["left"] = False
        elif key == pygame.K_RIGHT:
            self._das_active["right"] = False
        elif key == pygame.K_DOWN:
            self.soft_dropping = False
            self.drop_timer = 0.0
