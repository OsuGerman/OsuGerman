"""All game screens built on the Drawable framework."""
from __future__ import annotations
import os
import math
import random
import shutil
import json
import glob
import pygame
from typing import Callable

from .framework import Screen, Container, Text, Button, Slider, Drawable, CursorTrail
from .config import *
from .beatmap import Beatmap
from .audio import (init_audio, load_music, stop_music, play_music, pause_music,
                    unpause_music, set_music_volume, generate_demo_wav, generate_demo_beatmap_notes, play_sfx)

MAP_DIR = 'maps'
SONG_DIR = 'songs'


class StarField(Drawable):
    def __init__(self, w: int, h: int):
        super().__init__()
        self.width, self.height = w, h
        self._stars = [(random.random(), random.random(), random.uniform(1, 3)) for _ in range(60)]
        self._t = 0.0

    def update(self, dt: float):
        super().update(dt)
        self._t += dt

    def draw(self, surface: pygame.Surface):
        w, h = int(self.width), int(self.height)
        surface.fill(BG)
        for xr, yr, sz in self._stars:
            sx = int((xr * w + self._t * (8 + sz * 6)) % w)
            sy = int(yr * h)
            a = min(255, int(40 + sz * 25))
            pygame.draw.circle(surface, (a, a, a), (sx, sy), int(sz))


# ---------------------------------------------------------------------------
# Main Menu
# ---------------------------------------------------------------------------

class MenuScreen(Screen):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._bg = StarField(1280, 720)
        self.add(self._bg)
        self._build()

    def _build(self):
        w, h = 1280, 720
        self._title1 = Text("Rhythm", 72, WHITE, True)
        self._title2 = Text("Dash", 72, ACCENT, True)
        self._sub = Text("Dein Rhythmus. Dein Spiel.", 16, (130, 130, 130))
        self.add(self._title1)
        self.add(self._title2)
        self.add(self._sub)

        self._buttons: list[Button] = []
        items = [
            ("▶  Spielen", ACCENT, lambda: self.app.go_select()),
            ("✎  Editor", ACCENT2, lambda: self.app.go_editor()),
            ("♫  Song Importieren", (0, 160, 200), lambda: self.app.do_import()),
            ("⚙  Einstellungen", (70, 55, 110), lambda: self.app.go_settings()),
        ]
        for i, (text, col, cb) in enumerate(items):
            btn = Button(text, 280, 50, col, cb)
            self._buttons.append(btn)
            self.add(btn)

        self._hint = Text("[D/J] Boden  [F/K] Luft  —  F11 Fullscreen", 13, (70, 70, 70))
        self.add(self._hint)
        self._layout()

    def _layout(self):
        w, h = int(self.width or 1280), int(self.height or 720)
        self._bg.width, self._bg.height = w, h
        self._title1.x = w / 2 - 280
        self._title1.y = h / 5
        self._title2.x = w / 2 + 10
        self._title2.y = h / 5
        self._sub.x = w / 2 - 130
        self._sub.y = h / 5 + 80
        for i, btn in enumerate(self._buttons):
            btn.x = w / 2 - 140
            btn.y = h / 2 - 20 + i * 62

        self._hint.x = w / 2 - 180
        self._hint.y = h - 35

    def on_enter(self):
        super().on_enter()
        for i, btn in enumerate(self._buttons):
            btn.alpha = 0
            btn.y += 30
            btn.fade_to(1.0, 0.3 + i * 0.08, 'out_quad')
            btn.move_to(btn.x, btn.y - 30, 0.3 + i * 0.08, 'out_back')

    def on_resize(self, w: int, h: int):
        self._layout()

    def on_key(self, key: int, mods: int):
        if key == pygame.K_RETURN:
            self.app.go_select()
        elif key == pygame.K_e:
            self.app.go_editor()
        elif key == pygame.K_i:
            self.app.do_import()


# ---------------------------------------------------------------------------
# Song Select
# ---------------------------------------------------------------------------

class SongCard(Container):
    def __init__(self, info: dict, idx: int, on_click: Callable):
        super().__init__()
        self.info = info
        self.idx = idx
        self.width, self.height = 600, 62
        self.interactive = True
        self._on_click = on_click
        self._selected = False
        self._hover_t = 0.0
        self._title = Text(info.get('title', '?'), 20, WHITE, True)
        self._detail = Text(
            f"{info.get('artist','?')}  ·  {info.get('note_count',0)} Noten  ·  BPM {info.get('bpm',0)}", 12, (150, 150, 150))
        has_audio = info.get('has_audio', False)
        self._audio_tag = Text("✓ Audio" if has_audio else "✗ Kein Audio", 12,
                               GREAT_COL if has_audio else MISS_COL)
        self.add(self._title)
        self.add(self._detail)
        self.add(self._audio_tag)
        self._title.x, self._title.y = 20, 8
        self._detail.x, self._detail.y = 20, 34

    def set_selected(self, sel: bool):
        self._selected = sel

    def update(self, dt: float):
        super().update(dt)
        target = 1.0 if self.hovered or self._selected else 0.0
        self._hover_t += (target - self._hover_t) * min(1, dt * 10)
        self._audio_tag.x = self.width - 120
        self._audio_tag.y = 10

    def draw(self, surface: pygame.Surface):
        r = self.rect
        t = self._hover_t
        bg = (min(255, int(40 + t * 50)), min(255, int(20 + t * 30)), min(255, int(80 + t * 80)))
        pygame.draw.rect(surface, bg, r, border_radius=12)
        border = ACCENT if self._selected else (80, 70, 110) if self.hovered else (50, 40, 70)
        pygame.draw.rect(surface, border, r, 2, border_radius=12)
        super().draw(surface)

    def on_click(self, mx: float, my: float):
        self._on_click(self.idx)

    def on_hover_enter(self):
        super().on_hover_enter()

    def on_hover_exit(self):
        super().on_hover_exit()


class SelectScreen(Screen):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._bg = StarField(1280, 720)
        self.add(self._bg)
        self._title = Text("Lied Auswählen", 40, WHITE, True)
        self.add(self._title)
        self._title.x, self._title.y = 40, 20

        self._back_btn = Button("← Zurück", 120, 36, (70, 55, 110), lambda: app.go_menu(), 14)
        self.add(self._back_btn)
        self._import_btn = Button("♫ Import", 120, 36, (0, 160, 200), lambda: app.do_import(), 14)
        self.add(self._import_btn)

        self._cards: list[SongCard] = []
        self._selected = 0
        self._maps: list[dict] = []

    def load_maps(self):
        self._maps = _load_map_list()
        for c in self._cards:
            self.remove(c)
        self._cards = []
        for i, m in enumerate(self._maps):
            card = SongCard(m, i, self._on_card_click)
            self._cards.append(card)
            self.add(card)
        self._selected = 0 if self._maps else -1
        self._layout()

    def _on_card_click(self, idx: int):
        if self._selected == idx:
            self._play(idx)
        else:
            self._selected = idx

    def _play(self, idx: int):
        if 0 <= idx < len(self._maps):
            self.app.start_game(self._maps[idx])

    def _layout(self):
        w = int(self.width or 1280)
        self._back_btn.x = w - 140
        self._back_btn.y = 20
        self._import_btn.x = w - 280
        self._import_btn.y = 20
        self._bg.width, self._bg.height = self.width, self.height
        for i, card in enumerate(self._cards):
            card.x = 30
            card.y = 80 + i * 72
            card.width = w - 60

    def on_enter(self):
        super().on_enter()
        self.load_maps()

    def on_resize(self, w: int, h: int):
        self._layout()

    def update(self, dt: float):
        super().update(dt)
        for i, c in enumerate(self._cards):
            c.set_selected(i == self._selected)

    def on_key(self, key: int, mods: int):
        if key == pygame.K_ESCAPE:
            self.app.go_menu()
        elif key == pygame.K_UP:
            if self._maps:
                self._selected = (self._selected - 1) % len(self._maps)
        elif key == pygame.K_DOWN:
            if self._maps:
                self._selected = (self._selected + 1) % len(self._maps)
        elif key == pygame.K_RETURN:
            self._play(self._selected)
        elif key == pygame.K_e:
            if 0 <= self._selected < len(self._maps):
                self.app.go_editor(self._maps[self._selected]['path'])
        elif key == pygame.K_DELETE:
            if 0 <= self._selected < len(self._maps):
                os.remove(self._maps[self._selected]['path'])
                self.load_maps()
        elif key == pygame.K_i:
            self.app.do_import()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class SettingsScreen(Screen):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.settings = app.settings
        self._bg = StarField(1280, 720)
        self.add(self._bg)
        self._title = Text("Einstellungen", 40, WHITE, True)
        self.add(self._title)

        self._sliders: list[Slider] = []
        defs = [
            ("Musik-Lautstärke", 'music_volume', 1.0),
            ("SFX-Lautstärke", 'sfx_volume', 1.0),
            ("Audio-Offset", 'audio_offset', 1.0),
            ("Noten-Speed", 'note_speed', 1.0),
            ("Hintergrund-Dim", 'bg_dim', 1.0),
            ("Approach Rate", 'approach_rate', 1.0),
            ("Overall Difficulty", 'overall_difficulty', 1.0),
        ]
        for label, attr, _ in defs:
            s = Slider(500, label=label, on_change=lambda v, a=attr: self._on_slider(a, v))
            self._sliders.append(s)
            self.add(s)
        self._sync_sliders()

        self._hw_text = Text("", 12, (120, 100, 150))
        self.add(self._hw_text)
        self._update_hw_text()

        keys_info = [
            Text("Boden: D / J / ↓    Luft: F / K / ↑    Pause: ESC    Quit: Q    Fullscreen: F11", 13, (140, 140, 140))
        ]
        self._keys = keys_info[0]
        self.add(self._keys)

        self._back_btn = Button("← Zurück & Speichern", 280, 48, ACCENT, self._save_back)
        self.add(self._back_btn)
        self._layout()

    def _sync_sliders(self):
        s = self.settings
        vals = [s.music_volume, s.sfx_volume,
                (s.audio_offset + 200) / 400,
                (s.note_speed - 0.2) / 0.8,
                s.bg_dim,
                (s.approach_rate - 1) / 9,
                (s.overall_difficulty - 1) / 9]
        for sl, v in zip(self._sliders, vals):
            sl.value = max(0, min(1, v))

    def _on_slider(self, attr: str, ratio: float):
        s = self.settings
        if attr == 'music_volume':
            s.music_volume = ratio
            set_music_volume(ratio)
        elif attr == 'sfx_volume':
            s.sfx_volume = ratio
        elif attr == 'audio_offset':
            s.audio_offset = int(-200 + ratio * 400)
        elif attr == 'note_speed':
            s.note_speed = round(0.2 + ratio * 0.8, 2)
        elif attr == 'bg_dim':
            s.bg_dim = ratio
        elif attr == 'approach_rate':
            s.approach_rate = round(1 + ratio * 9, 1)
        elif attr == 'overall_difficulty':
            s.overall_difficulty = round(1 + ratio * 9, 1)
        self._update_hw_text()

    def _update_hw_text(self):
        hw = self.settings.get_hit_windows()
        at = self.settings.get_approach_time_ms()
        self._hw_text.set_text(
            f"Hit Windows → Perfect: ±{hw['perfect']}ms  Great: ±{hw['great']}ms  Good: ±{hw['good']}ms   Approach: {at}ms")

    def _save_back(self):
        self.settings.save()
        self.app.go_menu()

    def _layout(self):
        w, h = int(self.width or 1280), int(self.height or 720)
        self._bg.width, self._bg.height = w, h
        self._title.x = w / 2 - 120
        self._title.y = 25
        cx = w / 2 - 250
        y = 90
        for sl in self._sliders:
            sl.x, sl.y = cx, y
            sl.width = 500
            y += 48
        self._hw_text.x, self._hw_text.y = cx, y
        y += 25
        self._keys.x, self._keys.y = cx, y
        y += 35
        self._back_btn.x = w / 2 - 140
        self._back_btn.y = y

    def on_enter(self):
        super().on_enter()
        self._sync_sliders()

    def on_resize(self, w: int, h: int):
        self._layout()

    def on_key(self, key: int, mods: int):
        if key == pygame.K_ESCAPE:
            self._save_back()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class ResultScreen(Screen):
    def __init__(self, app, result: dict):
        super().__init__()
        self.app = app
        self.result = result
        self._bg = StarField(1280, 720)
        self.add(self._bg)
        self._build()

    def _build(self):
        r = self.result
        grade = r.get('grade', 'D')
        gcol = PERFECT_COL if grade == 'S' else GREAT_COL if grade == 'A' else GOOD_COL if grade == 'B' else MISS_COL

        self._grade = Text(grade, 120, gcol, True)
        self.add(self._grade)
        self._song_title = Text(r.get('title', ''), 22, (180, 180, 180), True)
        self.add(self._song_title)
        self._score = Text(f"{r.get('score', 0):,}", 52, ACCENT, True)
        self.add(self._score)

        stats_data = [
            ("Perfect", str(r.get('perfect', 0)), PERFECT_COL),
            ("Great", str(r.get('great', 0)), GREAT_COL),
            ("Good", str(r.get('good', 0)), GOOD_COL),
            ("Miss", str(r.get('miss', 0)), MISS_COL),
        ]
        self._stats: list[tuple[Text, Text]] = []
        for label, val, col in stats_data:
            vt = Text(val, 36, col, True)
            lt = Text(label, 12, (130, 130, 130))
            self.add(vt)
            self.add(lt)
            self._stats.append((vt, lt))

        ur = r.get('unstable_rate', 0)
        avg = r.get('avg_error', 0)
        early = r.get('early', 0)
        late = r.get('late', 0)
        self._detail = Text(
            f"Max Combo: {r.get('max_combo', 0)}x   Accuracy: {r.get('accuracy', 0):.1f}%   "
            f"UR: {ur:.1f}   Avg: {avg:+.1f}ms   Early: {early}  Late: {late}",
            13, (150, 150, 150))
        self.add(self._detail)

        self._timing_errors = r.get('timing_errors', [])

        self._retry_btn = Button("↻ Nochmal", 195, 48, ACCENT,
                                 lambda: self.app.retry_game(r.get('title', '')))
        self._back_btn = Button("← Zurück", 195, 48, (70, 55, 110),
                                lambda: self.app.go_select())
        self.add(self._retry_btn)
        self.add(self._back_btn)

        self._hint = Text("R: Nochmal   ESC: Zurück", 12, (70, 70, 70))
        self.add(self._hint)
        self._layout()

    def _layout(self):
        w, h = int(self.width or 1280), int(self.height or 720)
        self._bg.width, self._bg.height = w, h
        self._grade.x = w / 2 - 50
        self._grade.y = 20
        self._song_title.x = w / 2 - 120
        self._song_title.y = 155
        self._score.x = w / 2 - 100
        self._score.y = 185
        sx = w / 2 - 320
        for i, (vt, lt) in enumerate(self._stats):
            cx = sx + i * 160 + 80
            vt.x, vt.y = cx - 20, 260
            lt.x, lt.y = cx - 15, 305
        self._detail.x = w / 2 - 280
        self._detail.y = 345
        self._retry_btn.x = w / 2 - 210
        self._retry_btn.y = 420
        self._back_btn.x = w / 2 + 15
        self._back_btn.y = 420
        self._hint.x = w / 2 - 80
        self._hint.y = h - 25

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        if self._timing_errors:
            w = int(self.width or 1280)
            bar_w, bar_h = 300, 28
            bar_x = w // 2 - bar_w // 2
            bar_y = 375
            pygame.draw.rect(surface, (25, 15, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            pygame.draw.line(surface, (80, 80, 80), (bar_x + bar_w // 2, bar_y),
                             (bar_x + bar_w // 2, bar_y + bar_h), 1)
            for err in self._timing_errors[-100:]:
                ratio = max(-1, min(1, err / 150))
                px = bar_x + bar_w // 2 + int(ratio * bar_w / 2)
                col = PERFECT_COL if abs(err) < 45 else AIR_COL if err > 0 else GROUND_COL
                pygame.draw.circle(surface, col, (px, bar_y + bar_h // 2 + random.randint(-8, 8)), 2)

    def on_enter(self):
        super().on_enter()
        self._grade.scale = 3.0
        self._grade.scale_to(1.0, 0.5, 'out_elastic')

    def on_resize(self, w: int, h: int):
        self._layout()

    def on_key(self, key: int, mods: int):
        if key == pygame.K_ESCAPE:
            self.app.go_select()
        elif key == pygame.K_r:
            self.app.retry_game(self.result.get('title', ''))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_map_list() -> list[dict]:
    maps = []
    for path in sorted(glob.glob(os.path.join(MAP_DIR, '*.json'))):
        try:
            with open(path) as f:
                d = json.load(f)
            af = d.get('audio_file', '')
            maps.append({
                'path': path, 'id': d.get('id', ''),
                'title': d.get('title', '?'), 'artist': d.get('artist', '?'),
                'bpm': d.get('bpm', 0), 'difficulty': d.get('difficulty', 5),
                'note_count': len(d.get('notes', [])),
                'has_audio': os.path.exists(af),
            })
        except Exception:
            pass
    return maps
