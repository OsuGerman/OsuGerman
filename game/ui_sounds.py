"""UI sound effects — hover, click, back, confirm, toggle."""
import numpy as np
import pygame

_ui_cache: dict[str, pygame.mixer.Sound] = {}
_volume = 0.3

def init_ui_sounds():
    sr = 44100
    def _mk(mono):
        stereo = np.column_stack([mono, mono])
        s = pygame.mixer.Sound(buffer=(stereo * 32767).astype(np.int16).tobytes())
        s.set_volume(_volume)
        return s

    # Hover — soft tick
    t = np.linspace(0, 0.02, int(sr*0.02), dtype=np.float32)
    _ui_cache['hover'] = _mk((np.sin(2*np.pi*1200*t) * np.exp(-t*150) * 0.15).astype(np.float32))

    # Click — crisp pop
    t = np.linspace(0, 0.04, int(sr*0.04), dtype=np.float32)
    w = np.sin(2*np.pi*800*t)*0.3 + np.sin(2*np.pi*1400*t)*0.15
    _ui_cache['click'] = _mk((w * np.exp(-t*60) * 0.4).astype(np.float32))

    # Confirm — ascending chime
    t = np.linspace(0, 0.1, int(sr*0.1), dtype=np.float32)
    w = np.sin(2*np.pi*600*t)*0.2 + np.sin(2*np.pi*900*t)*0.15 + np.sin(2*np.pi*1200*t)*0.1
    _ui_cache['confirm'] = _mk((w * np.exp(-t*20) * 0.35).astype(np.float32))

    # Back — descending
    t = np.linspace(0, 0.06, int(sr*0.06), dtype=np.float32)
    f = 600 - 200 * (t / 0.06)
    _ui_cache['back'] = _mk((np.sin(2*np.pi*f*t) * np.exp(-t*40) * 0.25).astype(np.float32))

    # Toggle
    t = np.linspace(0, 0.03, int(sr*0.03), dtype=np.float32)
    _ui_cache['toggle'] = _mk((np.sin(2*np.pi*1000*t) * np.exp(-t*80) * 0.2).astype(np.float32))

    # Error
    t = np.linspace(0, 0.08, int(sr*0.08), dtype=np.float32)
    _ui_cache['error'] = _mk(((np.random.randn(len(t))*0.1 + np.sin(2*np.pi*200*t)*0.2) * np.exp(-t*25) * 0.3).astype(np.float32))

def play_ui(name: str):
    s = _ui_cache.get(name)
    if s: s.play()

def set_ui_volume(vol: float):
    global _volume
    _volume = max(0, min(1, vol))
    for s in _ui_cache.values():
        s.set_volume(_volume)
