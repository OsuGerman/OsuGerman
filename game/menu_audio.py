"""Menu Audio Manager — song previews with fade transitions, separate from gameplay audio."""
from __future__ import annotations
import time as _time
import pygame

_state = {
    'playing': False,
    'current_path': '',
    'fade_target': 0.7,
    'fade_current': 0.0,
    'fade_speed': 0.0,
    'preview_start': 0,
    'preview_len': 20000,
    'play_start_time': 0.0,
    'volume': 0.7,
    'pending_path': '',
    'pending_start': 0,
    'pending_timer': 0.0,
    'debounce_ms': 250,
}


def menu_audio_set_volume(vol: float):
    _state['volume'] = max(0, min(1, vol))
    _state['fade_target'] = _state['volume']


def menu_audio_play_preview(audio_path: str, preview_start_ms: float = 0,
                            preview_length_ms: float = 20000):
    """Request a song preview. Debounced — waits 250ms before playing to avoid spam."""
    if not audio_path or not pygame.mixer.get_init():
        return
    _state['pending_path'] = audio_path
    _state['pending_start'] = int(preview_start_ms)
    _state['preview_len'] = int(preview_length_ms)
    _state['pending_timer'] = _state['debounce_ms'] / 1000.0

    # Start fade out of current
    if _state['playing']:
        _state['fade_speed'] = -3.0  # fade out in ~300ms


def menu_audio_stop():
    """Stop menu music with fade out."""
    _state['fade_speed'] = -4.0
    _state['pending_path'] = ''


def menu_audio_force_stop():
    """Immediately stop — used when gameplay starts."""
    try:
        pygame.mixer.music.stop()
    except:
        pass
    _state['playing'] = False
    _state['fade_current'] = 0
    _state['pending_path'] = ''


def menu_audio_update(dt: float):
    """Call every frame from the menu loop."""
    s = _state

    # Handle pending (debounce)
    if s['pending_path'] and s['pending_timer'] > 0:
        s['pending_timer'] -= dt
        if s['pending_timer'] <= 0:
            _start_preview(s['pending_path'], s['pending_start'])
            s['pending_path'] = ''

    # Fade
    if s['fade_speed'] != 0:
        s['fade_current'] += s['fade_speed'] * dt
        if s['fade_current'] >= s['fade_target']:
            s['fade_current'] = s['fade_target']
            s['fade_speed'] = 0
        elif s['fade_current'] <= 0:
            s['fade_current'] = 0
            s['fade_speed'] = 0
            if s['playing']:
                try:
                    pygame.mixer.music.stop()
                except:
                    pass
                s['playing'] = False
        try:
            pygame.mixer.music.set_volume(max(0, s['fade_current']))
        except:
            pass

    # Preview loop
    if s['playing'] and s['preview_len'] > 0:
        elapsed = (_time.perf_counter() - s['play_start_time']) * 1000
        if elapsed > s['preview_len']:
            _start_preview(s['current_path'], s['preview_start'])


def _start_preview(path: str, start_ms: int):
    s = _state
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(start=max(0, start_ms / 1000.0))
        pygame.mixer.music.set_volume(0)
        s['playing'] = True
        s['current_path'] = path
        s['preview_start'] = start_ms
        s['play_start_time'] = _time.perf_counter()
        s['fade_current'] = 0
        s['fade_speed'] = 3.0  # fade in ~300ms
        s['fade_target'] = s['volume']
    except Exception as e:
        print(f"[MenuAudio] Error: {e}")
        s['playing'] = False


def menu_audio_is_playing() -> bool:
    return _state['playing']
