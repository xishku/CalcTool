#include "sound.h"
#include "constants.h"
#include <SDL.h>
#include <cmath>
#include <vector>
#include <cstdint>
#include <algorithm>

namespace {

constexpr int SAMPLE_RATE = 44100;
SDL_AudioDeviceID audio_dev = 0;
bool audio_ok = false;

// 生成方波/三角波/正弦波 PCM
std::vector<int16_t> make_tone(float freq, int duration_ms,
                                const std::string& wave_type = "square",
                                float volume_db = 1.0f) {
    int num_samples = SAMPLE_RATE * duration_ms / 1000;
    if (num_samples < 1) num_samples = 1;

    std::vector<int16_t> samples(num_samples);
    float vol = volume_db * 0.4f * 0.8f;  // VOLUME_SFX * 0.8

    for (int i = 0; i < num_samples; ++i) {
        float t = (float)i / SAMPLE_RATE;
        float attack = std::min(1.0f, (float)i / (SAMPLE_RATE * 0.005f));
        float decay = std::max(0.0f, 1.0f - ((float)(i - num_samples * 0.7f) /
                                              std::max(1.0f, (float)num_samples * 0.3f)));
        float envelope = attack * decay * vol;

        float val;
        if (wave_type == "square") {
            val = (std::sin(2.0f * M_PI * freq * t) >= 0) ? 1.0f : -1.0f;
            val += 0.3f * std::sin(2.0f * M_PI * freq * 2.0f * t);
        } else if (wave_type == "triangle") {
            float phase = std::fmod(t * freq, 1.0f);
            val = 2.0f * std::abs(2.0f * phase - 1.0f) - 1.0f;
        } else {
            val = std::sin(2.0f * M_PI * freq * t);
        }

        val *= envelope;
        samples[i] = (int16_t)(std::clamp(val, -1.0f, 1.0f) * 32767);
    }
    return samples;
}

// 音效队列播放
std::vector<int16_t> sfx_buffer;

void queue_sfx(const std::vector<int16_t>& data) {
    sfx_buffer.insert(sfx_buffer.end(), data.begin(), data.end());
    // 限制缓冲区大小
    if (sfx_buffer.size() > SAMPLE_RATE * 2) {
        sfx_buffer.erase(sfx_buffer.begin(),
                         sfx_buffer.begin() + SAMPLE_RATE);
    }
}

// SDL 音频回调 — 实时播放队列中的音效
void audio_callback(void* userdata, Uint8* stream, int len) {
    auto* buf = static_cast<std::vector<int16_t>*>(userdata);
    int samples_needed = len / 2;
    int16_t* out = (int16_t*)stream;

    for (int i = 0; i < samples_needed; ++i) {
        if (!buf->empty()) {
            out[i] = (*buf)[0];
            buf->erase(buf->begin());
        } else {
            out[i] = 0;
        }
    }
}

} // namespace

void sound_init() {
    if (audio_ok) return;

    SDL_AudioSpec want{}, have{};
    want.freq = SAMPLE_RATE;
    want.format = AUDIO_S16SYS;
    want.channels = 1;
    want.samples = 1024;
    want.callback = audio_callback;
    want.userdata = &sfx_buffer;

    audio_dev = SDL_OpenAudioDevice(nullptr, 0, &want, &have,
                                     SDL_AUDIO_ALLOW_FORMAT_CHANGE);
    if (audio_dev == 0) return;

    audio_ok = true;
    SDL_PauseAudioDevice(audio_dev, 0);
}

void sound_quit() {
    if (audio_dev > 0) {
        SDL_CloseAudioDevice(audio_dev);
        audio_dev = 0;
    }
    audio_ok = false;
}

void play_move() {
    if (!audio_ok) return;
    queue_sfx(make_tone(200, 30, "square", 0.4f));
}

void play_rotate() {
    if (!audio_ok) return;
    queue_sfx(make_tone(400, 50, "triangle", 0.5f));
}

void play_soft_drop() {
    if (!audio_ok) return;
    queue_sfx(make_tone(150, 15, "square", 0.2f));
}

void play_hard_drop() {
    if (!audio_ok) return;
    queue_sfx(make_tone(80, 120, "triangle", 0.7f));
}

void play_lock() {
    if (!audio_ok) return;
    queue_sfx(make_tone(120, 70, "square", 0.5f));
}

void play_clear(int lines) {
    if (!audio_ok) return;
    for (int i = 0; i < lines; ++i) {
        queue_sfx(make_tone(500.0f + i * 150, 60, "square", 0.6f));
    }
}

void play_level_up() {
    if (!audio_ok) return;
    float freqs[] = {440, 554, 659, 880};
    for (float f : freqs) {
        queue_sfx(make_tone(f, 80, "triangle", 0.5f));
    }
}

void play_game_over() {
    if (!audio_ok) return;
    float freqs[] = {440, 370, 311, 220};
    for (float f : freqs) {
        queue_sfx(make_tone(f, 180, "square", 0.6f));
    }
}

void play_game_start() {
    if (!audio_ok) return;
    float freqs[] = {523, 659, 784};
    for (float f : freqs) {
        queue_sfx(make_tone(f, 120, "triangle", 0.5f));
    }
}
