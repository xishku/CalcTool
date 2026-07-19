#pragma once
#include "constants.h"

class Scorer {
public:
    Scorer();
    void reset();

    void add_clear(int lines);
    void add_soft_drop(int cells = 1);
    void add_hard_drop(int cells);

    int drop_speed_ms() const;

    int score = 0;
    int level = 1;
    int lines = 0;
};
