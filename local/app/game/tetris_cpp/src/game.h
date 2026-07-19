#pragma once
#include "constants.h"
#include "board.h"
#include "piece.h"
#include "scorer.h"
#include "renderer.h"
#include <string>
#include <map>

enum class State { Start, Playing, Paused, GameOver };

class Game {
public:
    Game();
    ~Game();
    void run();

private:
    Renderer renderer;
    Board board;
    Scorer scorer;
    BagRandomizer randomizer;

    Piece* active_piece = nullptr;
    Piece* ghost_piece = nullptr;
    Piece* next_piece = nullptr;
    State state = State::Start;

    double drop_timer = 0.0;
    double lock_timer = 0.0;
    bool soft_dropping = false;

    // DAS / ARR
    std::map<std::string, double> das_timer;
    std::map<std::string, bool> das_active;
    std::map<std::string, double> das_repeat;

    void start_game();
    void spawn_piece();
    void update_ghost();
    void update(double dt);

    bool move_piece(int dx, int dy);
    void rotate_piece();
    void hard_drop();
    void lock_piece();

    bool handle_keydown(SDL_Keycode key);
    void handle_keyup(SDL_Keycode key);

    void sfx(const std::string& name, int param = 0);
};
