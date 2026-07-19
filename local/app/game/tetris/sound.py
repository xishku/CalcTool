"""音效 + 背景音乐系统 — 全部程序化生成，无需外部音频文件"""
import math
import struct
import io
import wave
import pygame
from constants import VOLUME_SFX, VOLUME_MUSIC

_PYGAME_AUDIO_INITIALIZED = False
_SAMPLE_RATE = 44100     # 音效采样率
_MUSIC_SR = 16000        # 音乐合成采样率（降低加速生成）

# 正弦查找表 — 512 点预计算，避免重复 math.sin
_SIN_BITS = 9
_SIN_SIZE = 1 << _SIN_BITS  # 512
_SIN_MASK = _SIN_SIZE - 1
_SIN_TABLE = [math.sin(2 * math.pi * i / _SIN_SIZE) for i in range(_SIN_SIZE)]


def _fsin(phase: float) -> float:
    """快速正弦：相位 0..1 → sin(2π·phase)，查表线性插值"""
    idx = phase * _SIN_SIZE
    i0 = int(idx) & _SIN_MASK
    i1 = (i0 + 1) & _SIN_MASK
    frac = idx - int(idx)
    return _SIN_TABLE[i0] * (1 - frac) + _SIN_TABLE[i1] * frac


def _ensure_audio() -> bool:
    global _PYGAME_AUDIO_INITIALIZED
    if _PYGAME_AUDIO_INITIALIZED:
        return True
    try:
        pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2, buffer=1024)
        _PYGAME_AUDIO_INITIALIZED = True
        return True
    except Exception:
        return False


# ============================================================
#  音效 (SFX)
# ============================================================

def _make_tone(freq: float, duration_ms: int, wave_type: str = "square",
               volume: float = 1.0) -> pygame.mixer.Sound | None:
    if not _ensure_audio():
        return None
    num_samples = max(1, int(_SAMPLE_RATE * duration_ms / 1000))

    data = []
    for i in range(num_samples):
        t = i / _SAMPLE_RATE
        attack = min(1.0, i / (_SAMPLE_RATE * 0.005))
        decay = max(0.0, 1.0 - (i - num_samples * 0.7) / max(1, num_samples * 0.3))
        envelope = attack * decay * volume * VOLUME_SFX * 0.8

        if wave_type == "square":
            val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            val += 0.3 * math.sin(2 * math.pi * freq * 2 * t)
        elif wave_type == "triangle":
            val = 2.0 * abs(2.0 * (t * freq - math.floor(t * freq + 0.5))) - 1.0
        else:
            val = math.sin(2 * math.pi * freq * t)

        val *= envelope
        val = max(-32767, min(32767, int(val * 32767)))
        data.append(val)

    buf = struct.pack(f"<{len(data)}h", *data)
    try:
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return None


_sfx_cache = {}


def _play_tone(freq: float, duration_ms: int, wave_type: str = "square", volume: float = 1.0):
    key = (freq, duration_ms, wave_type, round(volume, 2))
    if key not in _sfx_cache:
        snd = _make_tone(freq, duration_ms, wave_type, volume)
        if snd:
            _sfx_cache[key] = snd
        else:
            return
    try:
        _sfx_cache[key].play()
    except Exception:
        pass


def play_move():
    _play_tone(200, 30, "square", 0.4)


def play_rotate():
    _play_tone(400, 50, "triangle", 0.5)


def play_soft_drop():
    _play_tone(150, 15, "square", 0.2)


def play_hard_drop():
    _play_tone(80, 120, "triangle", 0.7)


def play_lock():
    _play_tone(120, 70, "square", 0.5)


def play_clear(lines: int):
    """消行音效 — 叠加播放，不阻塞主循环"""
    for i in range(lines):
        _play_tone(500 + i * 150, 60, "square", 0.6)


def play_level_up():
    """升级音效 — 所有音符同时播放形成和弦感"""
    for freq in [440, 554, 659, 880]:
        _play_tone(freq, 80, "triangle", 0.5)


def play_game_over():
    """游戏结束 — 下行音阶"""
    for freq in [440, 370, 311, 220]:
        _play_tone(freq, 180, "square", 0.6)


def play_game_start():
    """游戏开始 — 上行和弦"""
    for freq in [523, 659, 784]:
        _play_tone(freq, 120, "triangle", 0.5)


# ============================================================
#  背景音乐 — 程序化合成旋律，WAV 流式循环播放
# ============================================================

_MUSIC_WAV_BYTES: bytes | None = None
_MUSIC_READY = False  # 后台线程完成标志
_MUSIC_THREAD = None


def _freq(name: str) -> float:
    """音符名 → 频率 (A4=440)"""
    SEMITONES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4,
                 "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    # 处理 b 记号 (flat = 降半音)
    if name.endswith("b"):
        base = name[0].upper()
        octave = int(name[2:])
        midi = 12 * (octave + 1) + SEMITONES.get(base, 0) - 1
    else:
        base = name[0].upper()
        sign = name[1] if len(name) > 1 and name[1] in "#b" else ""
        rest = name[1 + len(sign):] if sign else name[1:]
        octave = int(rest) if rest else 4
        midi = 12 * (octave + 1) + SEMITONES.get(base + sign, 0)
    return 440.0 * (2 ** ((midi - 69) / 12))


def _gen_lead(total_samples: int, beat_samples: int) -> list[float]:
    """生成主旋律 — 好一朵茉莉花（C大调，五声调式）"""
    buf = [0.0] * total_samples

    # 茉莉花简谱 (1=C): 3=E, 5=G, 6=A, i=C5, 2=D
    # 8 小节 × 4 拍，缓慢吟唱
    _notes = [
        # === 第1-2小节: 好一朵茉莉花 ===
        ("E4", 0.75), ("E4", 0.25), ("G4", 0.75), ("A4", 0.5),
        ("C5", 0.5), ("C5", 0.5), ("A4", 0.75),                       # bar1
        ("G4", 0.75), ("G4", 0.25), ("A4", 0.75), ("G4", 2.25),       # bar2
        # === 第3-4小节: 满园花草 ===
        ("E4", 0.75), ("E4", 0.25), ("G4", 0.75), ("A4", 0.5),
        ("C5", 0.5), ("C5", 0.5), ("A4", 0.75),                       # bar3
        ("G4", 0.75), ("G4", 0.25), ("A4", 0.75), ("G4", 2.25),       # bar4
        # === 第5-6小节: 香也香不过它 ===
        ("G4", 0.5), ("G4", 0.5), ("G4", 0.5), ("E4", 0.5),
        ("G4", 1.5), ("A4", 0.5),                                      # bar5
        ("A4", 1.5), ("A4", 1.5), ("G4", 1.0),                        # bar6
        # === 第7-8小节: 我有心采一朵 ===
        ("E4", 0.5), ("D4", 0.5), ("E4", 0.5), ("G4", 0.5),
        ("E4", 0.5), ("D4", 1.5),                                      # bar7
        ("C4", 1.0), ("C4", 1.0), ("D4", 1.0), ("C4", 1.0),           # bar8
    ]

    pos = 0.0
    for note_str, beats in _notes:
        start_sample = int(pos * beat_samples)
        dur_samples = int(beats * beat_samples)
        end_sample = min(start_sample + dur_samples, total_samples)
        freq = _freq(note_str)
        _add_note(buf, freq, start_sample, end_sample, volume=1.0,
                  vibrato=True, wave="flute")
        pos += beats

    return buf


def _gen_bass(total_samples: int, beat_samples: int) -> list[float]:
    """低音伴奏 — 五声调式根音，模仿古筝低音弦"""
    buf = [0.0] * total_samples

    # 每小节的根音（C 大调五声: C D E G A）
    _bass = [
        ("C3", 4.0),                              # bar1
        ("G2", 4.0),                              # bar2
        ("C3", 4.0),                              # bar3
        ("G2", 4.0),                              # bar4
        ("C3", 2.0), ("G2", 2.0),                 # bar5
        ("A2", 2.0), ("C3", 2.0),                 # bar6
        ("G2", 2.0), ("D3", 2.0),                 # bar7
        ("C3", 4.0),                              # bar8
    ]

    pos = 0.0
    for note_str, beats in _bass:
        start_sample = int(pos * beat_samples)
        dur_samples = int(beats * beat_samples)
        end_sample = min(start_sample + dur_samples, total_samples)
        freq = _freq(note_str)
        _add_note(buf, freq, start_sample, end_sample, volume=0.3, vibrato=False,
                  wave="triangle", sustain=0.9)
        pos += beats

    return buf


def _gen_chord(total_samples: int, beat_samples: int) -> list[float]:
    """和弦垫底 — 五声音阶空五度/四度，留白写意"""
    buf = [0.0] * total_samples

    # 每小节五声式和弦：空五度(根音+五度)或四度叠置
    chords_bar = [
        # bar1-2: C 调主和弦氛围 (C+G+E → 五声调式主和弦)
        [(("C3", 0.0), ("G3", 0.5), ("E4", 1.0), ("G4", 1.5))],
        [(("G2", 0.0), ("D3", 0.5), ("G3", 1.0), ("D4", 1.5))],
        # bar3-4
        [(("C3", 0.0), ("G3", 0.5), ("E4", 1.0), ("G4", 1.5))],
        [(("G2", 0.0), ("D3", 0.5), ("G3", 1.0), ("D4", 1.5))],
        # bar5-6
        [(("C3", 0.0), ("G3", 0.5), ("E4", 1.0))],
        [(("A2", 0.0), ("E3", 0.5), ("A3", 1.0), ("E4", 1.5))],
        # bar7-8
        [(("G2", 0.0), ("D3", 0.5), ("G3", 1.0))],
        [(("C3", 0.0), ("G3", 0.5), ("E4", 1.0), ("C5", 1.5))],
    ]

    bar_samples = 4 * beat_samples
    for bar_idx, chord_group in enumerate(chords_bar):
        bar_start = bar_idx * bar_samples
        for chord_notes in chord_group:
            for note_str, offset_beats in chord_notes:
                start_sample = int(bar_start + offset_beats * beat_samples)
                dur_samples = int(beat_samples * 2.0)
                end_sample = min(start_sample + dur_samples, total_samples)
                freq = _freq(note_str)
                _add_note(buf, freq, start_sample, end_sample, volume=0.18,
                          vibrato=False, wave="sine", sustain=0.5)

    return buf


def _add_note(buf: list[float], freq: float, start: int, end: int,
              volume: float = 1.0, vibrato: bool = False,
              wave: str = "bell", sustain: float = 0.7):
    """将单个音符叠加到缓冲区，使用查表正弦加速"""
    sr = _MUSIC_SR
    for i in range(start, end):
        if i >= len(buf):
            break
        elapsed = (i - start) / sr
        total_dur = (end - start) / sr
        progress = elapsed / max(total_dur, 0.001)

        # ADSR 包络
        attack_time = 0.008
        decay_time = total_dur * 0.1
        if progress < attack_time / total_dur:
            env = progress * total_dur / attack_time
        elif progress < (attack_time + decay_time) / total_dur:
            decay_progress = (progress * total_dur - attack_time) / decay_time
            env = 1.0 - decay_progress * (1.0 - sustain)
        else:
            env = sustain * (1.0 - min(1.0, (progress - (attack_time + decay_time) / total_dur) /
                                       max(0.001, 1.0 - (attack_time + decay_time) / total_dur)))

        # 颤音
        vib_freq = freq
        if vibrato:
            vib_depth = 0.002 * freq
            vib_freq = freq + vib_depth * _fsin(5.0 * elapsed % 1.0)

        phase = (vib_freq * i / sr) % 1.0

        if wave == "bell":
            val = (0.60 * _fsin(phase) +
                   0.25 * _fsin((phase * 2) % 1.0) +
                   0.10 * _fsin((phase * 3) % 1.0) +
                   0.05 * _fsin((phase * 4) % 1.0))
        elif wave == "flute":
            val = (0.85 * _fsin(phase) +
                   0.12 * _fsin((phase * 2) % 1.0) +
                   0.03 * _fsin((phase * 3) % 1.0))
        elif wave == "triangle":
            val = 2.0 * abs(2.0 * phase - 1.0) - 1.0
            val += 0.3 * _fsin((phase * 2) % 1.0)
        elif wave == "sine":
            val = _fsin(phase)
        else:
            val = _fsin(phase)

        val *= env * volume * VOLUME_MUSIC
        buf[i] += val


def _make_wav_bytes(samples_left: list[float], samples_right: list[float],
                    sample_rate: int) -> bytes:
    """将左右声道样本编码为 WAV 字节流"""
    buf = io.BytesIO()
    n = len(samples_left)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.setnframes(n)
        raw = b""
        for l, r in zip(samples_left, samples_right):
            # 限制 + 交错
            lv = max(-32767, min(32767, int(l * 32767)))
            rv = max(-32767, min(32767, int(r * 32767)))
            raw += struct.pack("<hh", lv, rv)
        wf.writeframes(raw)
    return buf.getvalue()


def _build_music():
    """构建背景音乐 WAV 缓冲区（在后台线程中调用）"""
    global _MUSIC_WAV_BYTES, _MUSIC_READY
    if _MUSIC_WAV_BYTES is not None:
        _MUSIC_READY = True
        return

    bpm = 80
    beat_sec = 60.0 / bpm
    beat_samples = int(_MUSIC_SR * beat_sec)
    total_beats = 32
    total_samples = int(total_beats * beat_samples)

    lead = _gen_lead(total_samples, beat_samples)
    bass = _gen_bass(total_samples, beat_samples)
    chord = _gen_chord(total_samples, beat_samples)

    # 混合: 左声道偏旋律，右声道偏和声
    left = [0.0] * total_samples
    right = [0.0] * total_samples
    for i in range(total_samples):
        left[i] = lead[i] * 0.8 + bass[i] * 0.5 + chord[i] * 0.6
        right[i] = lead[i] * 0.5 + bass[i] * 0.8 + chord[i] * 0.6

    peak = max(max(abs(v) for v in left), max(abs(v) for v in right), 0.001)
    scale = 0.85 / peak
    left = [v * scale for v in left]
    right = [v * scale for v in right]

    _MUSIC_WAV_BYTES = _make_wav_bytes(left, right, _MUSIC_SR)
    _MUSIC_READY = True


def _music_thread_worker():
    """后台线程：合成音乐 → 写临时文件 → 播放"""
    import tempfile, os
    try:
        _build_music()
        if _MUSIC_WAV_BYTES:
            fd, path = tempfile.mkstemp(suffix=".wav", prefix="tetris_bgm_")
            os.close(fd)
            with open(path, "wb") as f:
                f.write(_MUSIC_WAV_BYTES)
            # 用函数属性存临时文件路径，供 cleanup 使用
            start_music._tmpfile = path
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(VOLUME_MUSIC)
            pygame.mixer.music.play(-1)
    except Exception:
        pass


def start_music():
    """启动背景音乐（后台线程，不阻塞游戏启动）"""
    global _MUSIC_THREAD
    if not _ensure_audio():
        return
    import threading
    if _MUSIC_THREAD is None or not _MUSIC_THREAD.is_alive():
        _MUSIC_THREAD = threading.Thread(target=_music_thread_worker, daemon=True)
        _MUSIC_THREAD.start()


def stop_music():
    """停止背景音乐"""
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception:
        pass


def cleanup_music():
    """清理临时音乐文件和线程"""
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception:
        pass
    if hasattr(start_music, "_tmpfile"):
        import os
        try:
            os.unlink(start_music._tmpfile)
        except Exception:
            pass
        del start_music._tmpfile
