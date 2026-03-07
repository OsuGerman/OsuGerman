#!/usr/bin/env python3
"""Generate a proper chart in the new data-driven format."""
import json
import os

BPM = 99.4
BEAT = 60000 / BPM
APPROACH = 1200

objects = []
obj_id = 0

def add(hit_time, lane, obj_type="GroundEnemy", action="Tap", duration=0):
    global obj_id
    obj_id += 1
    objects.append({
        "id": f"obj_{obj_id:04d}",
        "type": obj_type,
        "lane": lane,
        "hitTime": round(hit_time, 1),
        "spawnTime": round(hit_time - APPROACH, 1),
        "actionType": action,
        "duration": duration
    })

total_beats = int(45 * BPM / 60)

for i in range(total_beats):
    t = i * BEAT
    bar = i // 4
    beat = i % 4
    section = bar // 4

    if section == 0:
        if beat == 0:
            add(t, "Ground")
        if beat == 2:
            add(t, "Ground")

    elif section == 1:
        add(t, "Ground")
        if beat in (1, 3):
            add(t + BEAT/2, "Air", "AirEnemy")

    elif section == 2:
        add(t, "Ground")
        if beat in (1, 3):
            add(t, "Air", "AirEnemy")
        if beat == 0:
            add(t + BEAT/2, "Air", "AirEnemy")

    elif section == 3:
        if beat == 0 and bar % 2 == 0:
            add(t, "Ground", "HoldNote", "Hold", BEAT * 2)
        elif beat == 0:
            add(t, "Ground")
        if beat == 2:
            add(t, "Air", "AirEnemy")
        if beat == 1:
            add(t, "Ground", "Obstacle", "Dodge")

    elif section == 4:
        for e in range(2):
            et = t + e * (BEAT/2)
            lane = "Air" if (i + e) % 3 == 0 else "Ground"
            otype = "AirEnemy" if lane == "Air" else "GroundEnemy"
            add(et, lane, otype)
        if beat == 3:
            add(t + BEAT * 0.75, "Air", "HeavyAccent")

    elif section >= 5:
        if bar % 4 == 0 and beat == 0:
            add(t, "Ground", "MashChain", "Mash", BEAT * 2)
        else:
            for e in range(4):
                et = t + e * (BEAT/4)
                lane = "Ground" if e % 2 == 0 else "Air"
                otype = "GroundEnemy" if lane == "Ground" else "AirEnemy"
                add(et, lane, otype)

events = [
    {"time": 0, "type": "StageEffect", "payload": {"effectId": "intro_fade"}},
    {"time": BEAT * 16, "type": "StageEffect", "payload": {"effectId": "buildup_pulse"}},
    {"time": BEAT * 32, "type": "StageEffect", "payload": {"effectId": "drop_flash"}},
    {"time": BEAT * 64, "type": "StageEffect", "payload": {"effectId": "intensity_up"}},
]

chart = {
    "songId": "demo_beat",
    "difficultyId": "normal",
    "globalOffsetMs": 0,
    "approachTimeMs": APPROACH,
    "hitWindowProfile": {
        "perfect": 35,
        "great": 70,
        "good": 110
    },
    "objects": objects,
    "events": events
}

seen = set()
unique = []
for o in chart['objects']:
    key = (o['hitTime'], o['lane'])
    if key not in seen:
        seen.add(key)
        unique.append(o)
chart['objects'] = sorted(unique, key=lambda o: o['hitTime'])

os.makedirs('data/charts', exist_ok=True)
path = 'data/charts/demo_beat_normal.json'
with open(path, 'w') as f:
    json.dump(chart, f, indent=2)

print(f"Chart: {path}")
print(f"Objects: {len(chart['objects'])}")
print(f"Events: {len(chart['events'])}")
print(f"BPM: {BPM}")
types = {}
for o in chart['objects']:
    types[o['type']] = types.get(o['type'], 0) + 1
for t, c in sorted(types.items()):
    print(f"  {t}: {c}")
