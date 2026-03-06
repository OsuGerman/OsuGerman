from __future__ import annotations
import pygame
from .config import *
from .beatmap import Beatmap, Note, LANE_AIR, LANE_GROUND
from .audio import play_sfx, get_music_pos_ms, is_music_playing
from .renderer import Renderer


class GameState:
    def __init__(self, beatmap: Beatmap, renderer: Renderer, music_offset_ms: float = 0):
        self.beatmap = beatmap
        self.renderer = renderer
        self.notes = beatmap.clone_notes()
        self.note_index = 0
        self.music_offset = music_offset_ms

        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect = 0
        self.great = 0
        self.good = 0
        self.miss = 0
        self.health = 100.0

        self.countdown = 3.0
        self.started = False
        self.paused = False
        self.finished = False
        self.result: dict | None = None

        self._play_start_ticks = 0
        self._music_started = False

    @property
    def game_time_ms(self) -> float:
        if not self.started:
            return 0
        if not self._music_started:
            return 0
        pos = get_music_pos_ms()
        if pos < 0:
            return 0
        return pos - self.music_offset

    def update(self, dt: float, keys_pressed: set[int]):
        if self.finished:
            return

        if self.paused:
            return

        if not self.started:
            self.countdown -= dt
            if self.countdown <= 0:
                self.started = True
                from .audio import play_music
                play_music(0)
                self._music_started = True
                self._play_start_ticks = pygame.time.get_ticks()
            return

        time = self.game_time_ms

        for i in range(self.note_index, len(self.notes)):
            n = self.notes[i]
            if n.hit or n.missed:
                if i == self.note_index:
                    self.note_index += 1
                continue
            if n.time - time > AUTO_MISS_MS:
                break
            if time - n.time > AUTO_MISS_MS:
                n.missed = True
                self._on_miss(n)
                if i == self.note_index:
                    self.note_index += 1

        ground = any(k in keys_pressed for k in GROUND_KEYS)
        air = any(k in keys_pressed for k in AIR_KEYS)
        if ground:
            self._try_hit(LANE_GROUND, time)
        if air:
            self._try_hit(LANE_AIR, time)

        if self._music_started and not is_music_playing():
            all_done = all(n.hit or n.missed for n in self.notes)
            if all_done or time > (self.beatmap.duration_ms + 2000):
                self._finish()

    def _try_hit(self, lane: int, time: float):
        best: Note | None = None
        best_diff = float('inf')
        for i in range(self.note_index, len(self.notes)):
            n = self.notes[i]
            if n.hit or n.missed:
                continue
            if n.time - time > GOOD_MS + 50:
                break
            if n.lane != lane:
                continue
            d = abs(n.time - time)
            if d < best_diff:
                best = n
                best_diff = d
        if best is None:
            return
        if best_diff <= GOOD_MS:
            best.hit = True
            self._on_hit(best, best_diff)

    def _on_hit(self, note: Note, diff: float):
        if diff <= PERFECT_MS:
            kind, pts, col = 'PERFECT!', SCORE_PERFECT, PERFECT_COL
            sfx = 'perfect'
        elif diff <= GREAT_MS:
            kind, pts, col = 'GREAT!', SCORE_GREAT, GREAT_COL
            sfx = 'great'
        else:
            kind, pts, col = 'GOOD', SCORE_GOOD, GOOD_COL
            sfx = 'good'

        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        multi = 1 + (self.combo // 10) * 0.1
        self.score += int(pts * multi)

        if sfx == 'perfect':
            self.perfect += 1
        elif sfx == 'great':
            self.great += 1
        else:
            self.good += 1
        self.health = min(100, self.health + 2)
        play_sfx(sfx)

        w, h = self.renderer.screen.get_size()
        nx = w * HIT_X_RATIO
        ny = h * AIR_Y_RATIO if note.lane == LANE_AIR else h * GROUND_Y_RATIO
        self.renderer.spawn_hit(nx, ny, col)
        self.renderer.add_judgment(kind, col, note.lane)
        self.renderer.shake = 3 if sfx == 'perfect' else 1.5
        self.renderer.set_char_action('airHit' if note.lane == LANE_AIR else 'groundHit')

    def _on_miss(self, note: Note):
        self.miss += 1
        self.combo = 0
        self.health = max(0, self.health - 5)
        self.renderer.add_judgment('MISS', MISS_COL, note.lane)

    def _finish(self):
        self.finished = True
        from .audio import stop_music
        stop_music()
        total = self.perfect + self.great + self.good + self.miss
        acc = ((self.perfect * 300 + self.great * 200 + self.good * 100) / (total * 300) * 100) if total > 0 else 0
        grade = 'S' if acc >= 98 else 'A' if acc >= 92 else 'B' if acc >= 85 else 'C' if acc >= 70 else 'D'
        self.result = {
            'score': self.score,
            'max_combo': self.max_combo,
            'accuracy': round(acc, 2),
            'perfect': self.perfect,
            'great': self.great,
            'good': self.good,
            'miss': self.miss,
            'grade': grade,
            'title': self.beatmap.title,
        }

    def render(self):
        r = self.renderer
        w, h = r.screen.get_size()
        sx = int((pygame.time.get_ticks() % 10 - 5) * r.shake * 0.3)
        sy = int((pygame.time.get_ticks() % 7 - 3) * r.shake * 0.3)

        saved = r.screen.get_clip()
        r.screen.set_clip(r.screen.get_rect())

        r.draw_background()
        r.draw_lanes()
        r.draw_notes(self.notes, self.game_time_ms if self.started else 0)
        r.draw_character()
        r.draw_particles()
        r.draw_judgments()

        duration = self.beatmap.duration_ms
        progress = self.game_time_ms / duration if duration > 0 else 0
        total = self.perfect + self.great + self.good + self.miss
        acc = ((self.perfect * 300 + self.great * 200 + self.good * 100) / (total * 300) * 100) if total > 0 else 100
        r.draw_hud(self.beatmap.title, self.beatmap.artist,
                   self.score, self.combo, acc, self.health, progress)

        if not self.started:
            r.draw_countdown(max(0, int(self.countdown) + 1) if self.countdown > 0 else 0)

        if self.paused:
            r.draw_pause()

        r.screen.set_clip(saved)
