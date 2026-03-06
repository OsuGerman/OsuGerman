from __future__ import annotations
import json
import os

LANE_GROUND = 0
LANE_AIR = 1

class Note:
    __slots__ = ('time', 'lane', 'hit', 'missed')

    def __init__(self, time: float, lane: int):
        self.time = time
        self.lane = lane
        self.hit = False
        self.missed = False

class Beatmap:
    def __init__(self, path: str | None = None):
        self.id = ''
        self.title = 'Untitled'
        self.artist = 'Unknown'
        self.bpm = 120.0
        self.offset = 0.0
        self.difficulty = 5
        self.audio_file = ''
        self.notes: list[Note] = []
        if path:
            self.load(path)

    def load(self, path: str):
        with open(path, 'r') as f:
            data = json.load(f)
        self.id = data.get('id', os.path.basename(path))
        self.title = data.get('title', 'Untitled')
        self.artist = data.get('artist', 'Unknown')
        self.bpm = data.get('bpm', 120.0)
        self.offset = data.get('offset', 0.0)
        self.difficulty = data.get('difficulty', 5)
        self.audio_file = data.get('audio_file', '')
        self.notes = []
        for n in data.get('notes', []):
            self.notes.append(Note(n['time'], n['lane']))
        self.notes.sort(key=lambda n: n.time)

    def save(self, path: str):
        data = {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'bpm': self.bpm,
            'offset': self.offset,
            'difficulty': self.difficulty,
            'audio_file': self.audio_file,
            'notes': [{'time': round(n.time, 1), 'lane': n.lane} for n in self.notes],
        }
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def clone_notes(self) -> list[Note]:
        return [Note(n.time, n.lane) for n in self.notes]

    @property
    def note_count(self) -> int:
        return len(self.notes)

    @property
    def duration_ms(self) -> float:
        if not self.notes:
            return 0
        return self.notes[-1].time + 1000
