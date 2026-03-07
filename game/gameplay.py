from __future__ import annotations
import math
import pygame
from .config import *
from .beatmap import Beatmap, Note, LANE_AIR, LANE_GROUND
from .audio import play_sfx, is_song_playing, get_song_time_ms
from .renderer import Renderer

KEY_COOLDOWN_MS = 75


class TimingHit:
    __slots__ = ('error_ms', 'time')
    def __init__(self, error_ms: float):
        self.error_ms = error_ms
        self.time = pygame.time.get_ticks()


class GameState:
    def __init__(self, beatmap: Beatmap, renderer: Renderer,
                 settings: Settings | None = None):
        self.beatmap = beatmap
        self.renderer = renderer
        self.settings = settings or Settings()
        self.note_speed = self.settings.note_speed
        self.notes = beatmap.clone_notes()
        self.note_index = 0
        self.hit_windows = self.settings.get_hit_windows()

        self.ground_keys = self.settings.ground_keys
        self.air_keys = self.settings.air_keys

        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect = 0
        self.great = 0
        self.good = 0
        self.miss = 0
        self.health = HP_START
        self.weapon_level = 0

        self.timing_hits: list[TimingHit] = []
        self.screen_flash = 0.0
        self.beat_pulse = 0.0
        self._last_beat_time = 0.0
        self._lane_cooldown = {LANE_GROUND: 0, LANE_AIR: 0}

        self.countdown = 3.0
        self.started = False
        self.paused = False
        self.finished = False
        self.failed = False
        self.result: dict | None = None
        self._music_started = False

    @property
    def game_time_ms(self) -> float:
        if not self._music_started:
            return 0
        return max(0, get_song_time_ms() - self.settings.audio_offset)

    def update(self, dt: float, keys_pressed: set[int]):
        if self.finished or self.failed:
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
            return

        time = self.game_time_ms
        now = pygame.time.get_ticks()

        beat_ms = 60000.0 / max(1, self.beatmap.bpm)
        current_beat = time / beat_ms
        if time - self._last_beat_time >= beat_ms:
            self._last_beat_time = time
            self.beat_pulse = 1.0
        self.beat_pulse = max(0, self.beat_pulse - dt * 5)
        self.screen_flash = max(0, self.screen_flash - dt * 8)

        miss_window = self.hit_windows['good'] + 50
        for i in range(self.note_index, len(self.notes)):
            n = self.notes[i]
            if n.hit or n.missed:
                if i == self.note_index:
                    self.note_index += 1
                continue
            if n.time - time > miss_window:
                break
            if time - n.time > miss_window:
                n.missed = True
                self._on_miss(n)
                if i == self.note_index:
                    self.note_index += 1

        ground = any(k in keys_pressed for k in self.ground_keys)
        air = any(k in keys_pressed for k in self.air_keys)

        if ground and now - self._lane_cooldown[LANE_GROUND] >= KEY_COOLDOWN_MS:
            self._lane_cooldown[LANE_GROUND] = now
            self._try_hit(LANE_GROUND, time)
        if air and now - self._lane_cooldown[LANE_AIR] >= KEY_COOLDOWN_MS:
            self._lane_cooldown[LANE_AIR] = now
            self._try_hit(LANE_AIR, time)

        if self.health <= 0:
            self._fail()
            return

        self.weapon_level = min(4, self.combo // 15)

        if self._music_started and not is_song_playing():
            all_done = all(n.hit or n.missed for n in self.notes)
            if all_done or time > (self.beatmap.duration_ms + 2000):
                self._finish()

    def _try_hit(self, lane: int, time: float):
        best: Note | None = None
        best_diff = float('inf')
        best_error = 0.0
        for i in range(self.note_index, len(self.notes)):
            n = self.notes[i]
            if n.hit or n.missed:
                continue
            if n.time - time > self.hit_windows['good'] + 80:
                break
            if n.lane != lane:
                continue
            d = abs(n.time - time)
            if d < best_diff:
                best = n
                best_diff = d
                best_error = n.time - time

        if best is None or best_diff > self.hit_windows['good']:
            if best is None or best_diff > 250:
                self.combo = 0
            return

        best.hit = True
        self._on_hit(best, best_diff, best_error)

    def _on_hit(self, note: Note, diff: float, error: float):
        hw = self.hit_windows
        if diff <= hw['perfect']:
            kind, pts, col, hp = 'PERFECT!', SCORE_PERFECT, PERFECT_COL, HP_PERFECT
            sfx = 'perfect'
            self.screen_flash = 0.4
        elif diff <= hw['great']:
            kind, pts, col, hp = 'GREAT!', SCORE_GREAT, GREAT_COL, HP_GREAT
            sfx = 'great'
            self.screen_flash = 0.2
        else:
            kind, pts, col, hp = 'GOOD', SCORE_GOOD, GOOD_COL, HP_GOOD
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

        self.health = min(HP_MAX, self.health + hp)
        play_sfx(sfx)
        self.timing_hits.append(TimingHit(error))

        w, h = self.renderer.screen.get_size()
        nx = w * HIT_X_RATIO
        ny = h * AIR_Y_RATIO if note.lane == LANE_AIR else h * GROUND_Y_RATIO
        self.renderer.spawn_hit(nx, ny, col)
        self.renderer.add_judgment(kind, col, note.lane)
        self.renderer.trigger_attack(note.lane, self.weapon_level, sfx == 'perfect')
        self.renderer.shake = 5 if sfx == 'perfect' else 2.5

    def _on_miss(self, note: Note):
        self.miss += 1
        self.combo = 0
        self.health = max(0, self.health + HP_MISS)
        self.renderer.add_judgment('MISS', MISS_COL, note.lane)

    def _fail(self):
        self.failed = True
        from .audio import stop_music
        stop_music()

    def _finish(self):
        self.finished = True
        from .audio import stop_music
        stop_music()
        self._build_result()

    def _build_result(self):
        total = self.perfect + self.great + self.good + self.miss
        max_score = total * SCORE_PERFECT if total > 0 else 1
        acc = ((self.perfect * 300 + self.great * 200 + self.good * 100) / max_score * 100) if total > 0 else 0
        grade = 'S' if acc >= 98 else 'A' if acc >= 92 else 'B' if acc >= 85 else 'C' if acc >= 70 else 'D'
        errors = [h.error_ms for h in self.timing_hits]
        avg_error = sum(errors) / len(errors) if errors else 0
        variance = sum((e - avg_error) ** 2 for e in errors) / len(errors) if errors else 0
        unstable_rate = (variance ** 0.5) * 10 if errors else 0
        early = sum(1 for e in errors if e > 5)
        late = sum(1 for e in errors if e < -5)
        self.result = {
            'score': self.score, 'max_combo': self.max_combo,
            'accuracy': round(acc, 2), 'perfect': self.perfect,
            'great': self.great, 'good': self.good, 'miss': self.miss,
            'grade': grade, 'title': self.beatmap.title,
            'avg_error': round(avg_error, 1), 'unstable_rate': round(unstable_rate, 1),
            'early': early, 'late': late, 'timing_errors': errors[-200:],
        }

    def render(self):
        r = self.renderer
        w, h = r.screen.get_size()

        r.draw_background()

        if self.screen_flash > 0:
            flash = pygame.Surface((w, h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(self.screen_flash * 50)))
            r.screen.blit(flash, (0, 0))

        r.draw_lanes()
        r.draw_receptors(self.beat_pulse)
        r.draw_notes_as_enemies(self.notes, self.game_time_ms if self.started else 0,
                                self.note_speed, self.beat_pulse)
        r.draw_character(self.weapon_level)
        r.draw_particles()
        r.draw_judgments()

        duration = self.beatmap.duration_ms
        progress = self.game_time_ms / duration if duration > 0 else 0
        total = self.perfect + self.great + self.good + self.miss
        acc = ((self.perfect * 300 + self.great * 200 + self.good * 100) / (total * 300) * 100) if total > 0 else 100
        r.draw_hud(self.beatmap.title, self.beatmap.artist,
                   self.score, self.combo, acc, self.health, progress, self.weapon_level)

        if self.settings.show_timing_bar and self.timing_hits:
            r.draw_timing_bar(self.timing_hits, self.hit_windows['perfect'])

        if not self.started:
            r.draw_countdown(max(0, int(self.countdown) + 1) if self.countdown > 0 else 0)
        if self.paused:
            r.draw_pause()
        if self.failed:
            r.draw_fail()
