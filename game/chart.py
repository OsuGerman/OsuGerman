"""Chart loading, parsing, and validation."""
from __future__ import annotations
import json
import os
from .types import (ChartData, GameplayObjectData, StageEvent, HitWindowProfile,
                    ObjectType, Lane, ActionType, SongMetadata, DifficultyMeta)


LANE_MAP = {"Ground": Lane.GROUND, "Air": Lane.AIR}
ACTION_MAP = {"Tap": ActionType.TAP, "Hold": ActionType.HOLD,
              "Dodge": ActionType.DODGE, "Mash": ActionType.MASH}
TYPE_MAP = {t.value: t for t in ObjectType}


def load_chart(path: str) -> ChartData:
    with open(path, 'r') as f:
        raw = json.load(f)
    return parse_chart(raw, path)


def parse_chart(raw: dict, source: str = "<unknown>") -> ChartData:
    errors = validate_chart_raw(raw, source)
    if errors:
        for e in errors:
            print(f"[ChartWarning] {source}: {e}")

    hw_raw = raw.get('hitWindowProfile', raw.get('hitWindows', {}))
    hw = HitWindowProfile(
        perfect=hw_raw.get('perfect', 35),
        great=hw_raw.get('great', 70),
        good=hw_raw.get('good', 110),
    )

    approach = raw.get('approachTimeMs', raw.get('approach_time_ms', 1200))

    objects = []
    for obj_raw in raw.get('objects', raw.get('notes', [])):
        obj = _parse_object(obj_raw, approach)
        if obj:
            objects.append(obj)

    objects.sort(key=lambda o: o.hit_time)

    events = []
    for evt_raw in raw.get('events', []):
        events.append(StageEvent(
            time=evt_raw.get('time', 0),
            event_type=evt_raw.get('type', ''),
            payload=evt_raw.get('payload', {}),
        ))

    return ChartData(
        song_id=raw.get('songId', raw.get('song_id', raw.get('id', ''))),
        difficulty_id=raw.get('difficultyId', raw.get('difficulty_id', 'normal')),
        global_offset_ms=raw.get('globalOffsetMs', raw.get('global_offset_ms', raw.get('offset', 0))),
        approach_time_ms=approach,
        hit_windows=hw,
        objects=objects,
        events=events,
    )


def _parse_object(raw: dict, default_approach: float) -> GameplayObjectData | None:
    lane_str = raw.get('lane', 'Ground')
    lane = LANE_MAP.get(lane_str, Lane.GROUND)
    if isinstance(lane_str, int):
        lane = Lane.AIR if lane_str == 1 else Lane.GROUND

    type_str = raw.get('type', 'GroundEnemy' if lane == Lane.GROUND else 'AirEnemy')
    obj_type = TYPE_MAP.get(type_str, ObjectType.GROUND_ENEMY)

    hit_time = raw.get('hitTime', raw.get('hit_time', raw.get('time', 0)))
    spawn_time = raw.get('spawnTime', raw.get('spawn_time', hit_time - default_approach))
    duration = raw.get('duration', 0)
    action_str = raw.get('actionType', raw.get('action_type', 'Tap'))
    action = ACTION_MAP.get(action_str, ActionType.TAP)

    if obj_type == ObjectType.HOLD_NOTE:
        action = ActionType.HOLD
    elif obj_type == ObjectType.OBSTACLE:
        action = ActionType.DODGE
    elif obj_type == ObjectType.MASH_CHAIN:
        action = ActionType.MASH

    return GameplayObjectData(
        id=raw.get('id', f"obj_{hit_time:.0f}_{lane.value}"),
        type=obj_type,
        lane=lane,
        hit_time=float(hit_time),
        spawn_time=float(spawn_time),
        duration=float(duration),
        action_type=action,
        score_value=raw.get('scoreValue', raw.get('score_value', 300)),
        hp_effect=raw.get('hpEffect', raw.get('hp_effect', 0)),
        visual_config=raw.get('visualConfig', raw.get('visual_config', {})),
        audio_config=raw.get('audioConfig', raw.get('audio_config', {})),
    )


def validate_chart_raw(raw: dict, source: str = "") -> list[str]:
    errors = []
    if 'objects' not in raw and 'notes' not in raw:
        errors.append("No 'objects' or 'notes' array found")

    objs = raw.get('objects', raw.get('notes', []))
    if not isinstance(objs, list):
        errors.append("Objects must be an array")
        return errors

    if len(objs) == 0:
        errors.append("Chart has zero objects")

    prev_time = -1
    for i, obj in enumerate(objs):
        t = obj.get('hitTime', obj.get('hit_time', obj.get('time', None)))
        if t is None:
            errors.append(f"Object {i}: missing hitTime/time")
        elif not isinstance(t, (int, float)):
            errors.append(f"Object {i}: hitTime must be numeric")
        if t is not None and t < prev_time - 1:
            errors.append(f"Object {i}: hitTime {t} < previous {prev_time}")
        if t is not None:
            prev_time = t

    return errors


def load_song_metadata(path: str) -> SongMetadata:
    with open(path, 'r') as f:
        raw = json.load(f)

    diffs = []
    for d in raw.get('difficulties', raw.get('difficultyList', [])):
        diffs.append(DifficultyMeta(
            id=d.get('id', ''), name=d.get('name', ''),
            level=d.get('level', 0), chart_file=d.get('chartFile', d.get('chart_file', '')),
        ))

    return SongMetadata(
        id=raw.get('id', ''),
        title=raw.get('title', 'Unknown'),
        artist=raw.get('artist', 'Unknown'),
        bpm=raw.get('bpm', 120),
        offset_ms=raw.get('offsetMs', raw.get('offset_ms', raw.get('offset', 0))),
        audio_file=raw.get('audioFile', raw.get('audio_file', '')),
        preview_start_ms=raw.get('previewStartMs', raw.get('preview_start_ms', 0)),
        stage_theme_id=raw.get('stageThemeId', raw.get('stage_theme_id', 'default')),
        difficulties=diffs,
    )


def chart_from_legacy(legacy_path: str) -> ChartData:
    """Convert old-format maps to new ChartData."""
    with open(legacy_path) as f:
        raw = json.load(f)
    raw.setdefault('songId', raw.get('id', ''))
    raw.setdefault('difficultyId', 'normal')
    notes = raw.get('notes', [])
    objects = []
    for n in notes:
        lane_val = n.get('lane', 0)
        lane_str = 'Air' if lane_val == 1 else 'Ground'
        objects.append({
            'hitTime': n.get('time', 0),
            'lane': lane_str,
            'type': 'AirEnemy' if lane_val == 1 else 'GroundEnemy',
            'actionType': 'Tap',
        })
    raw['objects'] = objects
    if 'notes' in raw:
        del raw['notes']
    return parse_chart(raw, legacy_path)
