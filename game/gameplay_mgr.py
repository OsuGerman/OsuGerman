"""Central GameplayManager — coordinates all runtime systems."""
from __future__ import annotations
import time as _time
import pygame
from .types import (GameplayState, ChartData, HitWindowProfile, Lane, ActionType,
                    Judgement, ResultData, JUDGEMENT_COLORS, InputEvent)
from .entities import GameplayObject, SpawnManager
from .audio import (play_music, pause_music, unpause_music, stop_music,
                    get_song_time_ms, is_song_playing, play_sfx,
                    set_music_volume, load_music)

KEY_COOLDOWN_MS = 70


class TimingRecord:
    __slots__ = ('error_ms', 'time')
    def __init__(self, error_ms: float):
        self.error_ms = error_ms
        self.time = _time.perf_counter()


class GameplayManager:
    def __init__(self, chart: ChartData, audio_path: str,
                 ground_keys: list[int], air_keys: list[int],
                 music_volume: float = 0.7, audio_offset: float = 0):
        self.chart = chart
        self.audio_path = audio_path
        self.audio_offset = audio_offset

        self.state = GameplayState()
        self.hit_windows = chart.hit_windows
        self.approach_time = chart.approach_time_ms

        entities = [GameplayObject(d) for d in chart.objects]
        self.spawn_mgr = SpawnManager(entities, self.approach_time)

        self.ground_keys = ground_keys
        self.air_keys = air_keys
        self._lane_cooldown = {Lane.GROUND: 0.0, Lane.AIR: 0.0}

        self.timing_records: list[TimingRecord] = []
        self.screen_flash = 0.0
        self.beat_pulse = 0.0
        self._last_beat_time = 0.0
        self._bpm = 120
        for obj in chart.objects:
            if obj.hit_time > 0:
                break

        self.countdown = 3.0
        self.started = False
        self.paused = False
        self.finished = False
        self.failed = False
        self.result: ResultData | None = None
        self._music_started = False
        self._note_speed = 0.42
        self._renderer = None

    def set_bpm(self, bpm: float):
        self._bpm = max(1, bpm)

    def set_note_speed(self, speed: float):
        self._note_speed = speed

    def set_renderer(self, renderer):
        self._renderer = renderer

    @property
    def song_time(self) -> float:
        if not self._music_started:
            return 0
        return max(0, get_song_time_ms() - self.audio_offset)

    @property
    def note_speed(self) -> float:
        return self._note_speed

    @property
    def active_objects(self) -> list[GameplayObject]:
        return self.spawn_mgr.active_objects

    def start(self):
        load_music(self.audio_path)
        self.countdown = 3.0
        self.started = False
        self._music_started = False

    def update(self, dt: float, key_events: list[int]):
        if self.finished or self.failed:
            return
        if self.paused:
            return

        if not self.started:
            self.countdown -= dt
            if self.countdown <= 0:
                self.started = True
                play_music(0)
                self._music_started = True
            return

        st = self.song_time
        now = _time.perf_counter() * 1000

        beat_ms = 60000.0 / self._bpm
        if st - self._last_beat_time >= beat_ms:
            self._last_beat_time = st
            self.beat_pulse = 1.0
        self.beat_pulse = max(0, self.beat_pulse - dt * 5)
        self.screen_flash = max(0, self.screen_flash - dt * 8)

        self.spawn_mgr.update(st)

        missed = self.spawn_mgr.check_missed(st, self.hit_windows)
        for obj in missed:
            self.state.on_judgement(Judgement.MISS)
            if self._renderer:
                self._renderer.add_popup('MISS', (255, 82, 82), obj.lane)

        ground = any(k in key_events for k in self.ground_keys)
        air = any(k in key_events for k in self.air_keys)

        if ground and now - self._lane_cooldown[Lane.GROUND] >= KEY_COOLDOWN_MS:
            self._lane_cooldown[Lane.GROUND] = now
            self._process_input(Lane.GROUND, st)

        if air and now - self._lane_cooldown[Lane.AIR] >= KEY_COOLDOWN_MS:
            self._lane_cooldown[Lane.AIR] = now
            self._process_input(Lane.AIR, st)

        if self.state.hp <= 0:
            self.failed = True
            stop_music()
            return

        if self._music_started and not is_song_playing():
            all_done = all(o.resolved for o in self.spawn_mgr.objects)
            if all_done or st > self.chart.objects[-1].hit_time + 2000 if self.chart.objects else True:
                self._finish()

    def _process_input(self, lane: Lane, song_time: float):
        obj = self.spawn_mgr.get_hittable(lane, ActionType.TAP, song_time, self.hit_windows)
        if obj is None:
            if not any(o.is_hittable and o.lane == lane and
                       abs(o.hit_time - song_time) < 250
                       for o in self.spawn_mgr.active_objects):
                self.state.combo = 0
            return

        error = obj.hit_time - song_time
        judgement = self.hit_windows.judge(error)

        if judgement == Judgement.MISS:
            return

        obj.resolve_hit(judgement)
        self.state.on_judgement(judgement)
        self.timing_records.append(TimingRecord(error))

        if judgement == Judgement.PERFECT:
            self.screen_flash = 0.4
        elif judgement == Judgement.GREAT:
            self.screen_flash = 0.2

        play_sfx(judgement.value.lower())

        if self._renderer:
            self._renderer.trigger_hit(lane, judgement, self.state.weapon_level)

    def toggle_pause(self):
        if self.paused:
            self.paused = False
            unpause_music()
        elif self.started:
            self.paused = True
            pause_music()

    def _finish(self):
        self.finished = True
        stop_music()
        self._build_result()

    def _build_result(self):
        s = self.state
        errors = [r.error_ms for r in self.timing_records]
        avg = sum(errors) / len(errors) if errors else 0
        var = sum((e - avg) ** 2 for e in errors) / len(errors) if errors else 0
        ur = (var ** 0.5) * 10

        self.result = ResultData(
            song_title=self.chart.song_id,
            difficulty=self.chart.difficulty_id,
            score=s.score, max_combo=s.max_combo,
            accuracy=round(s.accuracy, 2),
            perfect=s.perfect_count, great=s.great_count,
            good=s.good_count, miss=s.miss_count,
            grade=s.grade, cleared=s.hp > 0,
            timing_errors=errors[-200:],
            avg_error=round(avg, 1), unstable_rate=round(ur, 1),
            early_count=sum(1 for e in errors if e > 5),
            late_count=sum(1 for e in errors if e < -5),
        )
