from __future__ import annotations
import os
import numpy as np
import pygame

_sfx_cache: dict[str, pygame.mixer.Sound] = {}


def init_audio():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    pygame.mixer.set_num_channels(16)
    _generate_sfx()


def load_music(path: str):
    pygame.mixer.music.load(path)


def play_music(start_ms: float = 0):
    pygame.mixer.music.play(start=start_ms / 1000.0)


def pause_music():
    pygame.mixer.music.pause()


def unpause_music():
    pygame.mixer.music.unpause()


def stop_music():
    pygame.mixer.music.stop()


def get_music_pos_ms() -> float:
    return pygame.mixer.music.get_pos()


def set_music_volume(vol: float):
    pygame.mixer.music.set_volume(vol)


def is_music_playing() -> bool:
    return pygame.mixer.music.get_busy()


def play_sfx(name: str):
    snd = _sfx_cache.get(name)
    if snd:
        snd.play()


def _generate_sfx():
    sr = 44100

    t = np.linspace(0, 0.12, int(sr * 0.12), dtype=np.float32)
    env = np.exp(-t * 30)
    wave = np.sin(2 * np.pi * 880 * t) * 0.5 + np.sin(2 * np.pi * 1320 * t) * 0.25
    _sfx_cache['perfect'] = _make_sound((wave * env * 0.4).astype(np.float32), sr)

    wave = np.sin(2 * np.pi * 660 * t) * 0.6
    _sfx_cache['great'] = _make_sound((wave * env * 0.35).astype(np.float32), sr)

    wave = np.sin(2 * np.pi * 440 * t) * 0.5
    _sfx_cache['good'] = _make_sound((wave * env * 0.3).astype(np.float32), sr)

    t2 = np.linspace(0, 0.15, int(sr * 0.15), dtype=np.float32)
    env2 = np.exp(-t2 * 20)
    wave = np.random.uniform(-0.3, 0.3, len(t2)).astype(np.float32) * 0.15
    wave += np.sin(2 * np.pi * 120 * t2) * 0.2
    _sfx_cache['miss'] = _make_sound((wave * env2 * 0.25).astype(np.float32), sr)

    t3 = np.linspace(0, 0.05, int(sr * 0.05), dtype=np.float32)
    env3 = np.exp(-t3 * 60)
    wave = np.sin(2 * np.pi * 1000 * t3) * 0.3
    _sfx_cache['tick'] = _make_sound((wave * env3 * 0.2).astype(np.float32), sr)


def _make_sound(mono: np.ndarray, sr: int) -> pygame.mixer.Sound:
    stereo = np.column_stack([mono, mono])
    pcm = (stereo * 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=pcm.tobytes())


def generate_demo_wav(path: str, bpm: float = 99.4, duration_s: float = 60.0):
    sr = 44100
    n = int(sr * duration_s)
    out = np.zeros(n, dtype=np.float64)
    beat_samples = int((60.0 / bpm) * sr)

    for i in range(int(duration_s * bpm / 60)):
        start = i * beat_samples
        beat_in_bar = i % 4

        kick_len = int(sr * 0.15)
        if start + kick_len < n:
            t = np.arange(kick_len) / sr
            freq = 160 - 120 * (t / 0.15)
            env = (1 - t / 0.15) ** 2
            out[start:start + kick_len] += np.sin(2 * np.pi * freq * t) * env * 0.5

        hh_off = beat_samples // 2
        hh_len = int(sr * 0.02)
        if start + hh_off + hh_len < n:
            env = np.exp(-np.arange(hh_len) / sr * 80)
            out[start + hh_off:start + hh_off + hh_len] += np.random.randn(hh_len) * env * 0.12

        if beat_in_bar == 2:
            sn_len = int(sr * 0.08)
            if start + sn_len < n:
                t = np.arange(sn_len) / sr
                env = (1 - t / 0.08) ** 1.5
                out[start:start + sn_len] += np.random.randn(sn_len) * env * 0.22
                out[start:start + sn_len] += np.sin(2 * np.pi * 200 * t) * env * 0.15

        bass_notes = [65.41, 65.41, 82.41, 73.42]
        bf = bass_notes[beat_in_bar]
        bass_len = min(beat_samples, n - start)
        if bass_len > 0:
            t = np.arange(bass_len) / sr
            env = np.exp(-t * 3)
            out[start:start + bass_len] += np.sin(2 * np.pi * bf * t) * env * 0.18

    bar_samples = beat_samples * 4
    melody_notes = [
        293.66, 329.63, 369.99, 440.00,
        392.00, 369.99, 329.63, 293.66,
        261.63, 293.66, 329.63, 369.99,
        440.00, 392.00, 329.63, 293.66,
    ]
    eighth = beat_samples // 2
    bars_offset = 4 * bar_samples
    for i, freq in enumerate(melody_notes * (int(duration_s * bpm / 60 / 16) + 1)):
        start = bars_offset + i * eighth
        if start >= n:
            break
        m_len = min(eighth, n - start)
        t = np.arange(m_len) / sr
        env = np.exp(-t * 5) * (1 - np.clip(t / (m_len / sr) - 0.8, 0, 1) * 5)
        wave = np.sin(2 * np.pi * freq * t) * 0.12
        wave += np.sin(2 * np.pi * freq * 2 * t) * 0.04
        wave += np.sin(2 * np.pi * freq * 3 * t) * 0.015
        out[start:start + m_len] += wave * env

    pad_freqs = [146.83, 174.61, 220.00, 261.63]
    for i in range(int(duration_s * bpm / 60 / 4)):
        start = i * bar_samples
        pf = pad_freqs[i % len(pad_freqs)]
        p_len = min(bar_samples, n - start)
        if p_len <= 0:
            break
        t = np.arange(p_len) / sr
        env = 0.06 * (1 - np.abs(t / (p_len / sr) - 0.5) * 1.5).clip(0)
        out[start:start + p_len] += np.sin(2 * np.pi * pf * t) * env
        out[start:start + p_len] += np.sin(2 * np.pi * pf * 1.5 * t) * env * 0.5

    out = out / max(np.abs(out).max(), 1e-6) * 0.85
    stereo = np.column_stack([out, out]).astype(np.float64)

    import soundfile as sf
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    sf.write(path, stereo, sr, subtype='PCM_16')
    print(f"Generated demo WAV: {path} ({duration_s}s at {bpm} BPM)")


def generate_demo_beatmap_notes(bpm: float = 99.4, duration_s: float = 60.0):
    beat_ms = 60000.0 / bpm
    notes = []
    total_beats = int(duration_s * bpm / 60)

    for i in range(total_beats):
        t = i * beat_ms
        beat_in_bar = i % 4
        bar = i // 4

        notes.append({'time': t, 'lane': 0})

        if bar >= 2:
            if beat_in_bar == 1:
                notes.append({'time': t + beat_ms / 2, 'lane': 1})
            if beat_in_bar == 3:
                notes.append({'time': t + beat_ms / 2, 'lane': 1})

        if bar >= 4 and bar % 2 == 0:
            if beat_in_bar == 0:
                notes.append({'time': t + beat_ms / 2, 'lane': 1})
            if beat_in_bar == 2:
                notes.append({'time': t + beat_ms / 2, 'lane': 0})

        if bar >= 8:
            if beat_in_bar == 1:
                notes.append({'time': t, 'lane': 1})
            if beat_in_bar == 3:
                notes.append({'time': t, 'lane': 1})

        if bar >= 12:
            for e in range(4):
                et = t + e * (beat_ms / 4)
                if not any(abs(n['time'] - et) < 20 for n in notes):
                    notes.append({'time': et, 'lane': 1 if e % 2 else 0})

    notes.sort(key=lambda n: n['time'])
    seen = set()
    unique = []
    for n in notes:
        key = (round(n['time']), n['lane'])
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique
