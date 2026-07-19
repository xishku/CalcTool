#include "game.h"
#include "sound.h"
#include <vector>
#include <utility>

Game::Game() {
    das_timer["left"] = das_timer["right"] = 0.0;
    das_active["left"] = das_active["right"] = false;
    das_repeat["left"] = das_repeat["right"] = 0.0;

    if (SOUND_ENABLED) sound_init();
}

Game::~Game() {
    delete active_piece;
    delete ghost_piece;
    delete next_piece;
    sound_quit();
}

void Game::run() {
    bool running = true;
    while (running) {
        double dt = renderer.tick(60);

        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT) {
                running = false;
            } else if (ev.type == SDL_KEYDOWN && !ev.key.repeat) {
                running = handle_keydown(ev.key.keysym.sym);
            } else if (ev.type == SDL_KEYUP) {
                handle_keyup(ev.key.keysym.sym);
            }
        }

        if (state == State::Playing) {
            update(dt);
        } else if (state == State::Start) {
            start_game();
        }

        std::string state_str;
        switch (state) {
            case State::Start:     state_str = "start"; break;
            case State::Playing:   state_str = "playing"; break;
            case State::Paused:    state_str = "paused"; break;
            case State::GameOver:  state_str = "gameover"; break;
        }

        renderer.render(board, active_piece, ghost_piece,
                        next_piece, scorer, state_str);
    }
}

void Game::start_game() {
    board.reset();
    scorer.reset();
    randomizer = BagRandomizer();
    spawn_piece();
    state = State::Playing;
    sfx("game_start");
}

void Game::spawn_piece() {
    if (next_piece == nullptr) {
        next_piece = new Piece(randomizer.next());
    }

    delete active_piece;
    active_piece = next_piece;
    next_piece = new Piece(randomizer.next());
    drop_timer = 0.0;
    lock_timer = 0.0;

    if (board.is_collision(*active_piece) || active_piece->is_above_board()) {
        state = State::GameOver;
        delete active_piece;
        active_piece = nullptr;
        sfx("game_over");
    }

    update_ghost();
}

void Game::update_ghost() {
    delete ghost_piece;
    ghost_piece = nullptr;

    if (!active_piece) return;

    ghost_piece = new Piece(active_piece->type);
    ghost_piece->x = active_piece->x;
    ghost_piece->y = active_piece->y;
    ghost_piece->rotation = active_piece->rotation;

    while (ghost_piece->can_place(ghost_piece->x, ghost_piece->y + 1,
                                   ghost_piece->rotation, board.grid)) {
        ghost_piece->y++;
    }
}

void Game::update(double dt) {
    if (!active_piece) return;

    double dt_ms = dt * 1000.0;

    // DAS / ARR
    for (auto& [dir, dx] : std::vector<std::pair<std::string, int>>{{"left", -1}, {"right", 1}}) {
        if (das_active[dir]) {
            das_timer[dir] += dt_ms;
            if (das_timer[dir] >= DAS_DELAY) {
                das_repeat[dir] += dt_ms;
                while (das_repeat[dir] >= ARR_INTERVAL) {
                    move_piece(dx, 0);
                    das_repeat[dir] -= ARR_INTERVAL;
                }
            }
        }
    }

    // 自动下落
    double speed = soft_dropping ? SOFT_DROP_MS : scorer.drop_speed_ms();
    drop_timer += dt_ms;
    while (drop_timer >= speed) {
        bool moved = move_piece(0, 1);
        drop_timer -= speed;
        if (soft_dropping && moved) {
            scorer.add_soft_drop();
        }
    }

    // 锁定延迟
    if (!active_piece) return;
    bool on_ground = !active_piece->can_place(
        active_piece->x, active_piece->y + 1,
        active_piece->rotation, board.grid);
    if (on_ground) {
        lock_timer += dt_ms;
        if (lock_timer >= LOCK_DELAY_MS) {
            lock_piece();
        }
    } else {
        lock_timer = 0.0;
    }
}

bool Game::move_piece(int dx, int dy) {
    if (!active_piece) return false;
    bool moved = active_piece->try_move(dx, dy, board.grid);
    if (moved) {
        update_ghost();
        sfx("move");
        if (dx != 0) lock_timer = 0.0;
    }
    return moved;
}

void Game::rotate_piece() {
    if (!active_piece) return;
    if (active_piece->try_rotate(board.grid)) {
        update_ghost();
        lock_timer = 0.0;
        sfx("rotate");
    }
}

void Game::hard_drop() {
    if (!active_piece) return;
    int cells = 0;
    while (active_piece->can_place(active_piece->x, active_piece->y + 1,
                                    active_piece->rotation, board.grid)) {
        active_piece->y++;
        cells++;
    }
    scorer.add_hard_drop(cells);
    sfx("hard_drop");
    lock_piece();
}

void Game::lock_piece() {
    if (!active_piece) return;
    int cleared = board.lock_piece(*active_piece);
    int old_level = scorer.level;
    if (cleared > 0) {
        scorer.add_clear(cleared);
        sfx("clear", cleared);
        if (scorer.level > old_level) {
            sfx("level_up");
        }
    } else {
        sfx("lock");
    }
    spawn_piece();
}

bool Game::handle_keydown(SDL_Keycode key) {
    if (key == SDLK_ESCAPE) return false;

    if (state == State::GameOver) {
        if (key == SDLK_r) state = State::Start;
        return true;
    }

    if (state == State::Start) return true;

    if (key == SDLK_p) {
        if (state == State::Playing) state = State::Paused;
        else if (state == State::Paused) state = State::Playing;
        return true;
    }

    if (state == State::Paused) {
        if (key == SDLK_r) state = State::Start;
        return true;
    }

    // Playing
    if (key == SDLK_LEFT) {
        move_piece(-1, 0);
        das_active["left"] = true;
        das_timer["left"] = 0.0;
        das_repeat["left"] = 0.0;
    } else if (key == SDLK_RIGHT) {
        move_piece(1, 0);
        das_active["right"] = true;
        das_timer["right"] = 0.0;
        das_repeat["right"] = 0.0;
    } else if (key == SDLK_DOWN) {
        soft_dropping = true;
    } else if (key == SDLK_UP) {
        rotate_piece();
    } else if (key == SDLK_SPACE) {
        hard_drop();
    } else if (key == SDLK_r) {
        state = State::Start;
    }

    return true;
}

void Game::handle_keyup(SDL_Keycode key) {
    if (key == SDLK_LEFT) das_active["left"] = false;
    else if (key == SDLK_RIGHT) das_active["right"] = false;
    else if (key == SDLK_DOWN) { soft_dropping = false; drop_timer = 0.0; }
}

void Game::sfx(const std::string& name, int param) {
    if (!SOUND_ENABLED) return;

    if (name == "move") play_move();
    else if (name == "rotate") play_rotate();
    else if (name == "hard_drop") play_hard_drop();
    else if (name == "lock") play_lock();
    else if (name == "clear") play_clear(param);
    else if (name == "level_up") play_level_up();
    else if (name == "game_over") play_game_over();
    else if (name == "game_start") play_game_start();
}
