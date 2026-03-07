"""Audio engine with precise clock, hitsounds, and volume control."""
from __future__ import annotations
import os
import numpy as np
import pygame
import time as _time

_sfx_cache: dict[str, pygame.mixer.Sound] = {}
_sfx_volume: float = 0.5
_music_volume: float = 0.7

_song_start_perf: float = 0.0
_song_start_offset: float = 0.0
_song_paused: bool = False
_song_pause_time: float = 0.0
_song_accumulated_pause: float = 0.0
_song_playing: bool = False


def init_audio():
    pygame.mixer.pre_init(44100, -16, 2, 256)
    pygame.mixer.init()
    pygame.mixer.set_num_channels(32)
    _generate_sfx()


def load_music(path: str):
    pygame.mixer.music.load(path)
    pygame.mixer.music.set_volume(_music_volume)


def play_music(start_ms: float = 0):
    global _song_start_perf, _song_start_offset, _song_playing
    global _song_paused, _song_accumulated_pause
    pygame.mixer.music.set_volume(_music_volume)
    pygame.mixer.music.play(start=start_ms / 1000.0)
    _song_start_perf = _time.perf_counter()
    _song_start_offset = start_ms
    _song_playing = True
    _song_paused = False
    _song_accumulated_pause = 0.0


def pause_music():
    global _song_paused, _song_pause_time
    if _song_playing and not _song_paused:
        pygame.mixer.music.pause()
        _song_pause_time = _time.perf_counter()
        _song_paused = True


def unpause_music():
    global _song_paused, _song_accumulated_pause
    if _song_playing and _song_paused:
        pygame.mixer.music.unpause()
        _song_accumulated_pause += _time.perf_counter() - _song_pause_time
        _song_paused = False


def stop_music():
    global _song_playing, _song_paused
    pygame.mixer.music.stop()
    _song_playing = False
    _song_paused = False


def get_song_time_ms() -> float:
    if not _song_playing:
        return 0.0
    if _song_paused:
        elapsed = _song_pause_time - _song_start_perf - _song_accumulated_pause
    else:
        elapsed = _time.perf_counter() - _song_start_perf - _song_accumulated_pause
    return _song_start_offset + elapsed * 1000.0


def is_song_playing() -> bool:
    return _song_playing and pygame.mixer.music.get_busy()


def is_song_paused() -> bool:
    return _song_paused


def set_music_volume(vol: float):
    global _music_volume
    _music_volume = max(0.0, min(1.0, vol))
    pygame.mixer.music.set_volume(_music_volume)


def set_sfx_volume(vol: float):
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, vol))
    for snd in _sfx_cache.values():
        snd.set_volume(_sfx_volume)


def play_sfx(name: str):
    snd = _sfx_cache.get(name)
    if snd:
        snd.play()


def _generate_sfx():
    sr = 44100

    t = np.linspace(0, 0.08, int(sr * 0.08), dtype=np.float32)
    env = np.exp(-t * 35)
    wave = np.sin(2 * np.pi * 800 * t) * 0.5
    wave += np.sin(2 * np.pi * 1200 * t) * 0.35
    wave += np.sin(2 * np.pi * 1600 * t) * 0.15
    _sfx_cache['perfect'] = _make_sound((wave * env * 0.65).astype(np.float32), sr)

    t2 = np.linspace(0, 0.06, int(sr * 0.06), dtype=np.float32)
    env2 = np.exp(-t2 * 40)
    wave2 = np.sin(2 * np.pi * 600 * t2) * 0.5
    wave2 += np.sin(2 * np.pi * 900 * t2) * 0.25
    _sfx_cache['great'] = _make_sound((wave2 * env2 * 0.55).astype(np.float32), sr)

    t3 = np.linspace(0, 0.04, int(sr * 0.04), dtype=np.float32)
    env3 = np.exp(-t3 * 50)
    wave3 = np.sin(2 * np.pi * 400 * t3) * 0.45
    _sfx_cache['good'] = _make_sound((wave3 * env3 * 0.45).astype(np.float32), sr)

    t4 = np.linspace(0, 0.1, int(sr * 0.1), dtype=np.float32)
    env4 = np.exp(-t4 * 20)
    wave4 = np.random.uniform(-1, 1, len(t4)).astype(np.float32) * 0.2
    wave4 += np.sin(2 * np.pi * 100 * t4) * 0.3
    _sfx_cache['miss'] = _make_sound((wave4 * env4 * 0.35).astype(np.float32), sr)

    t5 = np.linspace(0, 0.025, int(sr * 0.025), dtype=np.float32)
    env5 = np.exp(-t5 * 100)
    wave5 = np.sin(2 * np.pi * 1000 * t5) * 0.35
    _sfx_cache['tick'] = _make_sound((wave5 * env5 * 0.3).astype(np.float32), sr)

    set_sfx_volume(_sfx_volume)


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
    melody_notes = [293.66, 329.63, 369.99, 440.00, 392.00, 369.99, 329.63, 293.66,
                    261.63, 293.66, 329.63, 369.99, 440.00, 392.00, 329.63, 293.66]
    eighth = beat_samples // 2
    bars_offset = 4 * bar_samples
    for i, freq in enumerate(melody_notes * (int(duration_s * bpm / 60 / 16) + 1)):
        start = bars_offset + i * eighth
        if start >= n: break
        m_len = min(eighth, n - start)
        t = np.arange(m_len) / sr
        env = np.exp(-t * 5) * (1 - np.clip(t / (m_len / sr) - 0.8, 0, 1) * 5)
        out[start:start + m_len] += (np.sin(2 * np.pi * freq * t) * 0.12 + np.sin(2 * np.pi * freq * 2 * t) * 0.04) * env
    pad_freqs = [146.83, 174.61, 220.00, 261.63]
    for i in range(int(duration_s * bpm / 60 / 4)):
        start = i * bar_samples
        pf = pad_freqs[i % len(pad_freqs)]
        p_len = min(bar_samples, n - start)
        if p_len <= 0: break
        t = np.arange(p_len) / sr
        env = 0.06 * (1 - np.abs(t / (p_len / sr) - 0.5) * 1.5).clip(0)
        out[start:start + p_len] += np.sin(2 * np.pi * pf * t) * env
    out = out / max(np.abs(out).max(), 1e-6) * 0.85
    import soundfile as sf
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    sf.write(path, np.column_stack([out, out]).astype(np.float64), sr, subtype='PCM_16')


def generate_demo_beatmap_notes(bpm: float = 99.4, duration_s: float = 60.0):
    beat_ms = 60000.0 / bpm
    notes, seen = [], set()
    for i in range(int(duration_s * bpm / 60)):
        t = i * beat_ms
        bar, beat = i // 4, i % 4
        notes.append({'time': t, 'lane': 0})
        if bar >= 2 and beat in (1, 3):
            notes.append({'time': t + beat_ms / 2, 'lane': 1})
        if bar >= 4 and bar % 2 == 0:
            if beat == 0: notes.append({'time': t + beat_ms / 2, 'lane': 1})
            if beat == 2: notes.append({'time': t + beat_ms / 2, 'lane': 0})
        if bar >= 8 and beat in (1, 3):
            notes.append({'time': t, 'lane': 1})
        if bar >= 12:
            for e in range(4):
                et = t + e * (beat_ms / 4)
                if not any(abs(n['time'] - et) < 20 for n in notes):
                    notes.append({'time': et, 'lane': 1 if e % 2 else 0})
    notes.sort(key=lambda n: n['time'])
    unique = []
    for n in notes:
        key = (round(n['time']), n['lane'])
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique
