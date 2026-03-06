#!/usr/bin/env python3
"""Generate a beatmap for Jack Pavlina - Back 2 Me at 99.4 BPM in Bb minor."""
import json
import os

BPM = 99.4
BEAT_MS = 60000 / BPM
DURATION_S = 180
TOTAL_BEATS = int(DURATION_S * BPM / 60)

notes = []

def add(time_ms: float, lane: int):
    notes.append({'time': round(time_ms, 1), 'lane': lane})

for i in range(TOTAL_BEATS):
    t = i * BEAT_MS
    bar = i // 4
    beat = i % 4
    section = bar // 4

    if bar < 4:
        if beat == 0:
            add(t, 0)
        if beat == 2:
            add(t, 0)

    elif section < 4:
        add(t, 0)
        if beat == 1:
            add(t + BEAT_MS / 2, 1)
        if beat == 3:
            add(t + BEAT_MS / 2, 1)

    elif section < 8:
        add(t, 0)
        if beat in (1, 3):
            add(t, 1)
        if beat == 0:
            add(t + BEAT_MS / 2, 1)
        if beat == 2:
            add(t + BEAT_MS / 2, 0)

    elif section < 12:
        for e in range(2):
            et = t + e * (BEAT_MS / 2)
            lane = 1 if (i + e) % 3 == 0 else 0
            add(et, lane)
        if beat == 3:
            add(t + BEAT_MS * 0.75, 1)

    else:
        for e in range(4):
            et = t + e * (BEAT_MS / 4)
            if e % 2 == 0:
                add(et, 0)
            else:
                add(et, 1)

notes.sort(key=lambda n: n['time'])
seen = set()
unique = []
for n in notes:
    key = (round(n['time']), n['lane'])
    if key not in seen:
        seen.add(key)
        unique.append(n)

data = {
    'id': 'back2me',
    'title': 'Back 2 Me',
    'artist': 'Jack Pavlina',
    'bpm': BPM,
    'offset': 0,
    'difficulty': 6,
    'audio_file': os.path.abspath('songs/back2me.mp3'),
    'notes': unique,
}

os.makedirs('maps', exist_ok=True)
path = 'maps/back2me.json'
with open(path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Beatmap erstellt: {path}")
print(f"  Noten: {len(unique)}")
print(f"  BPM: {BPM}")
print(f"  Dauer: ~{DURATION_S}s ({TOTAL_BEATS} Beats)")
print(f"  Audio-Pfad: {data['audio_file']}")
print(f"\n⚠️  Die Audio-Datei muss noch heruntergeladen werden!")
print(f"  Lege die MP3/WAV/OGG Datei unter 'songs/back2me.mp3' ab.")
