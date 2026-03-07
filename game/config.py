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

HP_START = 80
HP_MAX = 100
HP_PERFECT = 4
HP_GREAT = 2
HP_GOOD = 0
HP_MISS = -10

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
        self.approach_rate = 7.0
        self.overall_difficulty = 7.0
        self.fullscreen = False
        self.show_timing_bar = True
        self.show_hit_error = True
        self.load()

    def get_hit_windows(self):
        od = self.overall_difficulty
        return {
            'perfect': max(20, int(50 - od * 3)),
            'great': max(40, int(100 - od * 5)),
            'good': max(70, int(150 - od * 5)),
        }

    def get_approach_time_ms(self):
        return max(300, int(1800 - self.approach_rate * 120))

    def load(self):
        try:
            with open(SETTINGS_FILE) as f:
                d = json.load(f)
            for k, v in d.items():
                if hasattr(self, k):
                    setattr(self, k, v)
        except Exception:
            pass

    def save(self):
        d = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(d, f, indent=2)
        except Exception:
            pass
