import os
import json
import pygame

WIDTH = 1280
HEIGHT = 720
FPS = 60
TITLE = "Rhythm Dash"
SETTINGS_FILE = 'settings.json'

HIT_X_RATIO = 0.15
GROUND_Y_RATIO = 0.68
AIR_Y_RATIO = 0.38
NOTE_RADIUS = 22
AUTO_MISS_MS = 180

PERFECT_MS = 45
GREAT_MS = 90
GOOD_MS = 135

SCORE_PERFECT = 300
SCORE_GREAT = 200
SCORE_GOOD = 100

GROUND_KEYS = [pygame.K_d, pygame.K_j, pygame.K_DOWN]
AIR_KEYS = [pygame.K_f, pygame.K_k, pygame.K_UP]

BG = (10, 2, 30)
BG_GRAD = (26, 10, 62)
GROUND_COL = (255, 77, 141)
GROUND_DARK = (200, 40, 100)
AIR_COL = (0, 212, 255)
AIR_DARK = (0, 150, 190)
PERFECT_COL = (255, 215, 0)
GREAT_COL = (0, 230, 118)
GOOD_COL = (66, 165, 250)
MISS_COL = (255, 82, 82)
ACCENT = (224, 64, 251)
ACCENT2 = (124, 77, 255)
WHITE = (255, 255, 255)
UI_BG = (15, 5, 36)
BTN_BG = (40, 20, 80)
BTN_HOVER = (65, 35, 120)
BTN_ACTIVE = (90, 50, 160)


class Settings:
    def __init__(self):
        self.music_volume = 0.7
        self.sfx_volume = 0.5
        self.audio_offset = 0
        self.note_speed = 0.42
        self.bg_dim = 0.3
        self.load()

    def load(self):
        try:
            with open(SETTINGS_FILE) as f:
                d = json.load(f)
            self.music_volume = d.get('music_volume', 0.7)
            self.sfx_volume = d.get('sfx_volume', 0.5)
            self.audio_offset = d.get('audio_offset', 0)
            self.note_speed = d.get('note_speed', 0.42)
            self.bg_dim = d.get('bg_dim', 0.3)
        except Exception:
            pass

    def save(self):
        d = {
            'music_volume': round(self.music_volume, 2),
            'sfx_volume': round(self.sfx_volume, 2),
            'audio_offset': self.audio_offset,
            'note_speed': round(self.note_speed, 2),
            'bg_dim': round(self.bg_dim, 2),
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(d, f, indent=2)
        except Exception:
            pass
