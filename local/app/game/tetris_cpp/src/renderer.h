#pragma once
#include "constants.h"
#include "board.h"
#include "piece.h"
#include "scorer.h"
#include <SDL.h>
#include <string>

class Renderer {
public:
    Renderer();
    ~Renderer();

    double tick(int fps);
    void render(const Board& board, const Piece* active,
                const Piece* ghost, const Piece* next,
                const Scorer& scorer, const std::string& state);

    // 获取像素格式
    uint32_t map_rgba(uint8_t r, uint8_t g, uint8_t b, uint8_t a) const;

private:
    SDL_Window* window = nullptr;
    SDL_Renderer* renderer = nullptr;
    uint64_t last_tick = 0;
    SDL_PixelFormat* fmt = nullptr;

    void draw_rect(int x, int y, int w, int h, uint32_t color);
    void draw_cell(int x, int y, int cell_size, uint32_t color, bool ghost = false);
    void draw_text(int x, int y, const std::string& text, int size, uint32_t color);
    void draw_text_big(int x, int y, const std::string& text, uint32_t color);
    void draw_overlay(const std::string& line1, const std::string& line2 = "");
};
