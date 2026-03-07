"""Timestamped input system — captures inputs with perf_counter timestamps,
independent of frame timing. Inputs are stored in a buffer and consumed
by the gameplay system each update cycle."""
from __future__ import annotations
import time as _time
import pygame
from .types import Lane, ActionType

# Input cooldown per lane to prevent spam (ms)
LANE_COOLDOWN_MS = 60


class TimestampedInput:
    """A single input event with precise timing."""
    __slots__ = ('lane', 'action', 'timestamp_ms', 'consumed')

    def __init__(self, lane: Lane, action: ActionType, timestamp_ms: float):
        self.lane = lane
        self.action = action
        self.timestamp_ms = timestamp_ms
        self.consumed = False


class InputBuffer:
    """Collects timestamped inputs and provides them to the gameplay system.

    Key design principle: inputs are timestamped at capture time (perf_counter),
    NOT at the time the gameplay processes them. This means even if the game
    processes inputs one frame later, the hit detection uses the ORIGINAL
    press time for judgment — matching osu!'s timestamped input approach.
    """

    def __init__(self, ground_keys: list[int], air_keys: list[int]):
        self.ground_keys = set(ground_keys)
        self.air_keys = set(air_keys)
        self._buffer: list[TimestampedInput] = []
        self._lane_last: dict[Lane, float] = {Lane.GROUND: 0.0, Lane.AIR: 0.0}
        self._start_perf: float = 0.0

    def set_song_start(self, perf_time: float):
        """Set the reference point: perf_counter value when song started."""
        self._start_perf = perf_time

    def _perf_to_song_ms(self) -> float:
        """Current time relative to song start, in ms."""
        if self._start_perf <= 0:
            return 0.0
        return max(0, (_time.perf_counter() - self._start_perf) * 1000.0)

    def capture(self, key: int):
        """Called immediately when a KEYDOWN event is received.
        Timestamps the input RIGHT NOW, not when gameplay processes it."""
        now_perf = _time.perf_counter()
        if self._start_perf <= 0:
            return  # Song not started yet

        now_ms = max(0, (now_perf - self._start_perf) * 1000.0)

        if key in self.ground_keys:
            lane = Lane.GROUND
        elif key in self.air_keys:
            lane = Lane.AIR
        else:
            return

        if now_ms - self._lane_last[lane] < LANE_COOLDOWN_MS:
            return
        self._lane_last[lane] = now_ms

        self._buffer.append(TimestampedInput(lane, ActionType.TAP, now_ms))

    def drain(self) -> list[TimestampedInput]:
        """Return all unconsumed inputs and clear the buffer.
        Called once per gameplay update cycle."""
        inputs = [i for i in self._buffer if not i.consumed]
        self._buffer.clear()
        return inputs

    def clear(self):
        self._buffer.clear()
