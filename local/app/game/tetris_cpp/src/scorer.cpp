#include "scorer.h"

Scorer::Scorer() { reset(); }

void Scorer::reset() {
    score = 0;
    level = 1;
    lines = 0;
}

void Scorer::add_clear(int n) {
    if (n <= 0 || n > 4) return;
    score += SCORE_TABLE[n] * level;
    lines += n;
    // 每 10 行升一级
    int new_level = lines / LINES_PER_LEVEL + 1;
    if (new_level > MAX_LEVEL) new_level = MAX_LEVEL;
    level = new_level;
}

void Scorer::add_soft_drop(int cells) { score += cells; }

void Scorer::add_hard_drop(int cells) { score += cells * 2; }

int Scorer::drop_speed_ms() const {
    return SPEED_TABLE[level];
}
