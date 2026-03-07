"""Gameplay entity system with lifecycle management."""
from __future__ import annotations
from .types import (GameplayObjectData, ObjectState, ObjectType, Lane,
                    ActionType, Judgement, HitWindowProfile)


class GameplayObject:
    """Runtime instance of a gameplay object with lifecycle state."""

    __slots__ = ('data', 'state', 'hit_time', 'spawn_time', 'lane',
                 'action_type', 'obj_type', 'duration', 'hold_progress',
                 '_resolved_judgement')

    def __init__(self, data: GameplayObjectData):
        self.data = data
        self.state = ObjectState.SCHEDULED
        self.hit_time = data.hit_time
        self.spawn_time = data.spawn_time
        self.lane = data.lane
        self.action_type = data.action_type
        self.obj_type = data.type
        self.duration = data.duration
        self.hold_progress = 0.0
        self._resolved_judgement: Judgement | None = None

    @property
    def is_alive(self) -> bool:
        return self.state in (ObjectState.SPAWNED, ObjectState.ACTIVE)

    @property
    def is_hittable(self) -> bool:
        return self.state in (ObjectState.SPAWNED, ObjectState.ACTIVE)

    @property
    def resolved(self) -> bool:
        return self.state in (ObjectState.RESOLVED_HIT, ObjectState.RESOLVED_MISS,
                              ObjectState.EXPIRED, ObjectState.DESPAWNED)

    def spawn(self):
        if self.state == ObjectState.SCHEDULED:
            self.state = ObjectState.SPAWNED

    def activate(self):
        if self.state == ObjectState.SPAWNED:
            self.state = ObjectState.ACTIVE

    def resolve_hit(self, judgement: Judgement):
        self._resolved_judgement = judgement
        self.state = ObjectState.RESOLVED_HIT

    def resolve_miss(self):
        self._resolved_judgement = Judgement.MISS
        self.state = ObjectState.RESOLVED_MISS

    def expire(self):
        self.state = ObjectState.EXPIRED

    def despawn(self):
        self.state = ObjectState.DESPAWNED

    def get_screen_x(self, song_time: float, hit_x: float, speed: float) -> float:
        return hit_x + (self.hit_time - song_time) * speed


class SpawnManager:
    """Manages spawning and despawning of gameplay objects."""

    def __init__(self, objects: list[GameplayObject], approach_time: float):
        self.objects = objects
        self.approach_time = approach_time
        self._spawn_cursor = 0
        self._active: list[GameplayObject] = []

    @property
    def active_objects(self) -> list[GameplayObject]:
        return self._active

    def update(self, song_time: float):
        while self._spawn_cursor < len(self.objects):
            obj = self.objects[self._spawn_cursor]
            if obj.hit_time - song_time <= self.approach_time + 200:
                obj.spawn()
                self._active.append(obj)
                self._spawn_cursor += 1
            else:
                break

        despawn_threshold = 500
        alive = []
        for obj in self._active:
            if obj.state == ObjectState.SPAWNED:
                if song_time >= obj.hit_time - self.approach_time:
                    obj.activate()

            if obj.resolved and song_time - obj.hit_time > despawn_threshold:
                obj.despawn()
            elif not obj.resolved and song_time - obj.hit_time > despawn_threshold:
                obj.expire()
                obj.despawn()
            else:
                alive.append(obj)
        self._active = alive

    def get_hittable(self, lane: Lane, action: ActionType,
                     song_time: float, windows: HitWindowProfile) -> GameplayObject | None:
        best = None
        best_diff = float('inf')
        for obj in self._active:
            if not obj.is_hittable:
                continue
            if obj.lane != lane:
                continue
            if obj.action_type == ActionType.DODGE:
                continue
            diff = abs(obj.hit_time - song_time)
            if diff <= windows.max_window and diff < best_diff:
                best = obj
                best_diff = diff
        return best

    def check_missed(self, song_time: float, windows: HitWindowProfile) -> list[GameplayObject]:
        missed = []
        for obj in self._active:
            if not obj.is_hittable:
                continue
            if obj.action_type == ActionType.DODGE:
                if song_time > obj.hit_time + windows.good:
                    obj.resolve_hit(Judgement.PERFECT)
                continue
            if song_time - obj.hit_time > windows.max_window:
                obj.resolve_miss()
                missed.append(obj)
        return missed
