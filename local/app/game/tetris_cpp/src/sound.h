#pragma once

// 程序化音效 (无外部文件依赖)
void sound_init();
void sound_quit();

void play_move();
void play_rotate();
void play_soft_drop();
void play_hard_drop();
void play_lock();
void play_clear(int lines);
void play_level_up();
void play_game_over();
void play_game_start();
