"""Core type definitions for the rhythm-action game engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# ── Lanes ──

class Lane(Enum):
    GROUND = "Ground"
    AIR = "Air"


# ── Actions ──

class ActionType(Enum):
    TAP = "Tap"
    HOLD = "Hold"
    DODGE = "Dodge"
    MASH = "Mash"


# ── Object Types ──

class ObjectType(Enum):
    GROUND_ENEMY = "GroundEnemy"
    AIR_ENEMY = "AirEnemy"
    HOLD_NOTE = "HoldNote"
    OBSTACLE = "Obstacle"
    MASH_CHAIN = "MashChain"
    HEAVY_ACCENT = "HeavyAccent"
    BOSS_EVENT = "BossEventObject"


# ── Object Lifecycle ──

class ObjectState(Enum):
    SCHEDULED = auto()
    SPAWNED = auto()
    ACTIVE = auto()
    RESOLVED_HIT = auto()
    RESOLVED_MISS = auto()
    EXPIRED = auto()
    DESPAWNED = auto()


# ── Judgements ──

class Judgement(Enum):
    PERFECT = "Perfect"
    GREAT = "Great"
    GOOD = "Good"
    MISS = "Miss"


JUDGEMENT_SCORE = {
    Judgement.PERFECT: 300,
    Judgement.GREAT: 200,
    Judgement.GOOD: 100,
    Judgement.MISS: 0,
}

JUDGEMENT_HP = {
    Judgement.PERFECT: 4,
    Judgement.GREAT: 2,
    Judgement.GOOD: 0,
    Judgement.MISS: -10,
}

JUDGEMENT_COLORS = {
    Judgement.PERFECT: (255, 215, 0),
    Judgement.GREAT: (0, 230, 118),
    Judgement.GOOD: (66, 165, 250),
    Judgement.MISS: (255, 82, 82),
}


# ── Game States ──

class GameState(Enum):
    BOOT = auto()
    MAIN_MENU = auto()
    SONG_SELECT = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()
    FAILED = auto()
    RESULTS = auto()


# ── Hit Windows ──

@dataclass
class HitWindowProfile:
    perfect: float = 35.0
    great: float = 70.0
    good: float = 110.0

    def judge(self, delta_ms: float) -> Judgement:
        d = abs(delta_ms)
        if d <= self.perfect:
            return Judgement.PERFECT
        elif d <= self.great:
            return Judgement.GREAT
        elif d <= self.good:
            return Judgement.GOOD
        return Judgement.MISS

    @property
    def max_window(self) -> float:
        return self.good + 50


# ── Chart Data ──

@dataclass
class GameplayObjectData:
    id: str
    type: ObjectType
    lane: Lane
    hit_time: float
    spawn_time: float = 0.0
    duration: float = 0.0
    action_type: ActionType = ActionType.TAP
    score_value: int = 300
    hp_effect: int = 0
    visual_config: dict[str, Any] = field(default_factory=dict)
    audio_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageEvent:
    time: float
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartData:
    song_id: str
    difficulty_id: str
    global_offset_ms: float = 0.0
    approach_time_ms: float = 1200.0
    hit_windows: HitWindowProfile = field(default_factory=HitWindowProfile)
    objects: list[GameplayObjectData] = field(default_factory=list)
    events: list[StageEvent] = field(default_factory=list)


@dataclass
class SongMetadata:
    id: str
    title: str
    artist: str
    bpm: float
    offset_ms: float = 0.0
    audio_file: str = ""
    preview_start_ms: float = 0.0
    stage_theme_id: str = "default"
    difficulties: list[DifficultyMeta] = field(default_factory=list)


@dataclass
class DifficultyMeta:
    id: str
    name: str
    level: int
    chart_file: str


# ── Gameplay Runtime State ──

@dataclass
class GameplayState:
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    hp: float = 80.0
    hp_max: float = 100.0
    perfect_count: int = 0
    great_count: int = 0
    good_count: int = 0
    miss_count: int = 0
    weapon_level: int = 0

    @property
    def total_judged(self) -> int:
        return self.perfect_count + self.great_count + self.good_count + self.miss_count

    @property
    def accuracy(self) -> float:
        t = self.total_judged
        if t == 0:
            return 100.0
        weighted = (self.perfect_count * 300 + self.great_count * 200 + self.good_count * 100)
        return weighted / (t * 300) * 100

    @property
    def grade(self) -> str:
        a = self.accuracy
        if a >= 98: return 'S'
        if a >= 92: return 'A'
        if a >= 85: return 'B'
        if a >= 70: return 'C'
        return 'D'

    def on_judgement(self, j: Judgement):
        self.score += int(JUDGEMENT_SCORE[j] * (1 + self.combo // 10 * 0.1))
        self.hp = max(0, min(self.hp_max, self.hp + JUDGEMENT_HP[j]))
        if j == Judgement.MISS:
            self.combo = 0
            self.miss_count += 1
        else:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            if j == Judgement.PERFECT:
                self.perfect_count += 1
            elif j == Judgement.GREAT:
                self.great_count += 1
            else:
                self.good_count += 1
        self.weapon_level = min(4, self.combo // 15)


# ── Input Event ──

@dataclass
class InputEvent:
    action: ActionType
    lane: Lane
    timestamp_ms: float
    raw_key: int = 0


# ── Result ──

@dataclass
class ResultData:
    song_title: str = ""
    difficulty: str = ""
    score: int = 0
    max_combo: int = 0
    accuracy: float = 0.0
    perfect: int = 0
    great: int = 0
    good: int = 0
    miss: int = 0
    grade: str = "D"
    cleared: bool = True
    timing_errors: list[float] = field(default_factory=list)
    avg_error: float = 0.0
    unstable_rate: float = 0.0
    early_count: int = 0
    late_count: int = 0
