"""Musical auto-mapping system — produces quality draft charts from audio analysis.

Pipeline: Audio Analysis → Structure → Candidates → Roles → Patterns → Difficulty → Validate → Export
"""
from __future__ import annotations
import numpy as np
import soundfile as sf
import os, json, math
from dataclasses import dataclass, field


# ════════════════════════════════════════
# DATA TYPES
# ════════════════════════════════════════

@dataclass
class AudioFeatures:
    sr: int
    duration_ms: float
    bpm: float
    beat_times: list[float]  # ms
    onsets: list[float]
    onset_strengths: list[float]
    energy_curve: list[float]  # per-beat energy
    spectral_low: list[float]  # low freq energy per onset
    spectral_high: list[float]  # high freq energy per onset

@dataclass
class Segment:
    start_ms: float
    end_ms: float
    seg_type: str  # intro, verse, chorus, buildup, drop, break, outro
    energy: float  # 0-1
    density_hint: float  # 0-1 recommended note density

@dataclass
class Candidate:
    time: float
    score: float
    role: str  # kick, snare, hihat, vocal, lead, sustain, accent, fill
    beat_pos: float  # position within beat (0=downbeat, 0.5=offbeat)
    segment_idx: int

@dataclass
class PatternTemplate:
    name: str
    lanes: list[str]  # 'G','A','G','A'...
    min_diff: int
    max_diff: int
    segment_types: list[str]
    density_class: str  # sparse, medium, dense

@dataclass
class MappedNote:
    time: float
    lane: str
    obj_type: str
    action: str
    duration: float
    pattern_id: str
    motif_id: str

@dataclass
class ValidationReport:
    total_notes: int
    warnings: list[str]
    density_score: float
    readability_score: float
    musical_score: float
    overall_quality: float


# ════════════════════════════════════════
# PHASE 1: AUDIO ANALYSIS
# ════════════════════════════════════════

def analyze_audio(path: str) -> AudioFeatures:
    data, sr = sf.read(path, dtype='float32')
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    dur_ms = len(data) / sr * 1000

    hop_ms = 10
    hop = int(sr * hop_ms / 1000)
    frame_sz = hop * 2
    n_frames = max(1, (len(data) - frame_sz) // hop)

    # Spectral flux for onset detection
    flux = np.zeros(n_frames)
    low_energy = np.zeros(n_frames)
    high_energy = np.zeros(n_frames)
    spec_prev = None

    for i in range(n_frames):
        start = i * hop
        frame = data[start:start + frame_sz] * np.hanning(frame_sz)
        spec = np.abs(np.fft.rfft(frame))
        freqs = np.fft.rfftfreq(frame_sz, 1.0 / sr)

        if spec_prev is not None:
            diff = spec - spec_prev
            diff[diff < 0] = 0
            flux[i] = np.sum(diff)

        low_mask = freqs < 250
        high_mask = freqs >= 250
        low_energy[i] = np.sum(spec[low_mask]) if low_mask.any() else 0
        high_energy[i] = np.sum(spec[high_mask]) if high_mask.any() else 0
        spec_prev = spec

    if flux.max() > 0:
        flux /= flux.max()

    # Onset detection with adaptive threshold
    win = max(3, int(80 / hop_ms))
    mean = np.convolve(flux, np.ones(win) / win, mode='same')
    threshold = mean + 0.12
    min_gap = int(60 / hop_ms)

    onsets, strengths, spec_lows, spec_highs = [], [], [], []
    last = -min_gap
    for i in range(1, len(flux) - 1):
        if flux[i] > flux[i-1] and flux[i] > flux[i+1] and flux[i] > threshold[i]:
            if i - last >= min_gap:
                onsets.append(i * hop_ms)
                strengths.append(float(flux[i]))
                spec_lows.append(float(low_energy[i]))
                spec_highs.append(float(high_energy[i]))
                last = i

    # BPM estimation
    bpm = _estimate_bpm(np.array(onsets))

    # Beat grid
    beat_ms = 60000 / bpm
    beat_times = [i * beat_ms for i in range(int(dur_ms / beat_ms) + 1)]

    # Per-beat energy
    energy_curve = []
    for bt in beat_times:
        window_start = int(bt / 1000 * sr)
        window_end = min(window_start + int(beat_ms / 1000 * sr), len(data))
        if window_start < window_end:
            energy_curve.append(float(np.sqrt(np.mean(data[window_start:window_end] ** 2))))
        else:
            energy_curve.append(0)

    if energy_curve and max(energy_curve) > 0:
        mx = max(energy_curve)
        energy_curve = [e / mx for e in energy_curve]

    return AudioFeatures(sr=sr, duration_ms=dur_ms, bpm=bpm,
                         beat_times=beat_times, onsets=onsets,
                         onset_strengths=strengths, energy_curve=energy_curve,
                         spectral_low=spec_lows, spectral_high=spec_highs)


def _estimate_bpm(onsets, min_bpm=60, max_bpm=200):
    if len(onsets) < 4:
        return 120.0
    intervals = np.diff(onsets)
    valid = intervals[(intervals > 60000/max_bpm) & (intervals < 60000/min_bpm)]
    if len(valid) < 3:
        return 120.0
    bins = np.arange(60000/max_bpm, 60000/min_bpm, 5)
    hist, edges = np.histogram(valid, bins=bins)
    best = np.argmax(hist)
    interval = (edges[best] + edges[best+1]) / 2
    bpm = 60000 / interval
    for m in [0.5, 1.0, 2.0]:
        c = bpm * m
        if min_bpm <= c <= max_bpm:
            return round(c, 1)
    return round(bpm, 1)


# ════════════════════════════════════════
# PHASE 2: SONG STRUCTURE
# ════════════════════════════════════════

def detect_segments(feat: AudioFeatures) -> list[Segment]:
    beat_ms = 60000 / feat.bpm
    bar_ms = beat_ms * 4
    total_bars = max(1, int(feat.duration_ms / bar_ms))
    segment_size = max(1, min(4, total_bars // 4))

    segments = []
    for i in range(0, total_bars, segment_size):
        start = i * bar_ms
        end = min((i + segment_size) * bar_ms, feat.duration_ms)

        beat_start = int(start / beat_ms)
        beat_end = min(int(end / beat_ms), len(feat.energy_curve))
        if beat_start >= beat_end:
            continue

        seg_energy = np.mean(feat.energy_curve[beat_start:beat_end])
        progress = start / feat.duration_ms

        if progress < 0.08:
            seg_type = 'intro'
        elif progress > 0.92:
            seg_type = 'outro'
        elif seg_energy < 0.25:
            seg_type = 'break'
        elif seg_energy > 0.7:
            if progress > 0.3:
                seg_type = 'drop' if seg_energy > 0.8 else 'chorus'
            else:
                seg_type = 'chorus'
        elif seg_energy > 0.5:
            prev_energy = np.mean(feat.energy_curve[max(0,beat_start-4):beat_start]) if beat_start > 4 else 0
            seg_type = 'buildup' if seg_energy > prev_energy + 0.1 else 'verse'
        else:
            seg_type = 'verse'

        density = {
            'intro': 0.3, 'verse': 0.5, 'chorus': 0.8, 'buildup': 0.6,
            'drop': 0.95, 'break': 0.2, 'outro': 0.3,
        }.get(seg_type, 0.5)

        segments.append(Segment(start, end, seg_type, float(seg_energy), density))

    return segments


# ════════════════════════════════════════
# PHASE 3: CANDIDATES + ROLE CLASSIFICATION
# ════════════════════════════════════════

def generate_candidates(feat: AudioFeatures, segments: list[Segment]) -> list[Candidate]:
    beat_ms = 60000 / feat.bpm
    candidates = []

    for oi, onset_t in enumerate(feat.onsets):
        seg_idx = _find_segment(onset_t, segments)
        if seg_idx < 0:
            continue

        strength = feat.onset_strengths[oi] if oi < len(feat.onset_strengths) else 0.5
        low = feat.spectral_low[oi] if oi < len(feat.spectral_low) else 0
        high = feat.spectral_high[oi] if oi < len(feat.spectral_high) else 0
        total = low + high + 1e-10

        beat_pos = (onset_t % beat_ms) / beat_ms
        bar_pos = (onset_t % (beat_ms * 4)) / (beat_ms * 4)

        # Role classification based on spectrum
        if low / total > 0.6:
            role = 'kick' if beat_pos < 0.15 or beat_pos > 0.85 else 'bass'
        elif beat_pos > 0.45 and beat_pos < 0.55:
            role = 'snare'
        elif strength < 0.3:
            role = 'hihat'
        elif high / total > 0.65:
            role = 'lead' if strength > 0.5 else 'accent'
        else:
            role = 'vocal' if strength > 0.6 else 'fill'

        # Scoring
        score = strength * 0.4
        if beat_pos < 0.1 or beat_pos > 0.9:
            score += 0.25  # on-beat bonus
        if bar_pos < 0.05:
            score += 0.15  # downbeat bonus
        if role in ('kick', 'snare', 'vocal', 'lead'):
            score += 0.2
        elif role == 'hihat':
            score -= 0.15

        seg = segments[seg_idx]
        score *= (0.5 + seg.density_hint * 0.5)

        candidates.append(Candidate(
            time=onset_t, score=score, role=role,
            beat_pos=beat_pos, segment_idx=seg_idx
        ))

    candidates.sort(key=lambda c: c.time)
    return candidates


def _find_segment(time, segments):
    for i, s in enumerate(segments):
        if s.start_ms <= time < s.end_ms:
            return i
    return len(segments) - 1 if segments else -1


# ════════════════════════════════════════
# PHASE 4: PATTERN LIBRARY
# ════════════════════════════════════════

PATTERNS: list[PatternTemplate] = [
    PatternTemplate('ground_pulse', ['G','G','G','G'], 1, 5, ['verse','intro','outro'], 'sparse'),
    PatternTemplate('alt_basic', ['G','A','G','A'], 2, 7, ['verse','chorus'], 'medium'),
    PatternTemplate('air_accent', ['G','G','A','G'], 2, 8, ['verse','chorus','buildup'], 'medium'),
    PatternTemplate('chorus_push', ['G','A','A','G','A'], 4, 10, ['chorus','drop'], 'dense'),
    PatternTemplate('drop_burst', ['G','A','G','A','G','A'], 6, 10, ['drop','chorus'], 'dense'),
    PatternTemplate('break_sparse', ['G','_','G','_'], 1, 4, ['break','intro','outro'], 'sparse'),
    PatternTemplate('buildup_rise', ['G','G','A','G','G','A','A'], 4, 9, ['buildup'], 'medium'),
    PatternTemplate('hold_phrase', ['H','_','_','G'], 3, 8, ['verse','chorus','break'], 'sparse'),
    PatternTemplate('dodge_mix', ['G','D','A','G'], 5, 10, ['chorus','drop'], 'medium'),
    PatternTemplate('syncopated', ['_','G','_','A','G','_'], 5, 10, ['chorus','drop'], 'medium'),
]


# ════════════════════════════════════════
# PHASE 5: PATTERN-DRIVEN MAPPING
# ════════════════════════════════════════

def map_chart(feat: AudioFeatures, segments: list[Segment],
              candidates: list[Candidate], difficulty: int) -> list[MappedNote]:
    beat_ms = 60000 / feat.bpm
    snap = _diff_snap(difficulty)
    grid_ms = beat_ms / snap
    threshold = _diff_threshold(difficulty)

    # Filter candidates by score
    viable = [c for c in candidates if c.score >= threshold]

    # Quantize to grid
    quantized = {}
    for c in viable:
        qt = round(c.time / grid_ms) * grid_ms
        if qt not in quantized or c.score > quantized[qt].score:
            quantized[qt] = c

    sorted_times = sorted(quantized.keys())
    notes: list[MappedNote] = []
    motif_counter = 0
    last_pattern = None
    seg_pattern_memory: dict[str, str] = {}

    i = 0
    while i < len(sorted_times):
        t = sorted_times[i]
        c = quantized[t]
        seg = segments[c.segment_idx] if c.segment_idx < len(segments) else None
        seg_type = seg.seg_type if seg else 'verse'

        # Select pattern
        pattern = _select_pattern(seg_type, difficulty, last_pattern, seg_pattern_memory)
        motif_id = seg_pattern_memory.get(seg_type, f"m{motif_counter}")
        if seg_type not in seg_pattern_memory:
            seg_pattern_memory[seg_type] = motif_id
            motif_counter += 1

        # Apply pattern to upcoming candidates
        pat_len = len([l for l in pattern.lanes if l != '_'])
        placed = 0
        pi = 0
        while pi < len(pattern.lanes) and i + placed < len(sorted_times):
            lane_code = pattern.lanes[pi]
            pi += 1
            if lane_code == '_':
                continue

            ct = sorted_times[i + placed]
            cc = quantized[ct]

            lane = 'Ground' if lane_code in ('G', 'H', 'D') else 'Air'
            if lane_code == 'H':
                obj_type, action, dur = 'HoldNote', 'Hold', beat_ms * 2
            elif lane_code == 'D':
                obj_type, action, dur = 'Obstacle', 'Dodge', 0
            else:
                obj_type = 'AirEnemy' if lane == 'Air' else 'GroundEnemy'
                if cc.role in ('vocal', 'lead') and cc.score > 0.7:
                    obj_type = 'HeavyAccent'
                action, dur = 'Tap', 0

            notes.append(MappedNote(
                time=round(ct, 1), lane=lane, obj_type=obj_type,
                action=action, duration=dur,
                pattern_id=pattern.name, motif_id=motif_id
            ))
            placed += 1

        i += max(1, placed)
        last_pattern = pattern

    return notes


def _diff_snap(d):
    if d <= 3: return 2
    if d <= 5: return 4
    if d <= 7: return 4
    return 8

def _diff_threshold(d):
    if d <= 3: return 0.45
    if d <= 5: return 0.30
    if d <= 7: return 0.20
    return 0.10

def _select_pattern(seg_type, diff, last, memory):
    valid = [p for p in PATTERNS
             if seg_type in p.segment_types
             and p.min_diff <= diff <= p.max_diff]
    if not valid:
        valid = [p for p in PATTERNS if p.min_diff <= diff <= p.max_diff]
    if not valid:
        valid = PATTERNS[:3]

    # Prefer variety — don't repeat same pattern
    if last and len(valid) > 1:
        valid = [p for p in valid if p.name != last.name] or valid

    # Weighted selection by density match
    import random
    if seg_type in ('drop', 'chorus'):
        dense = [p for p in valid if p.density_class in ('medium', 'dense')]
        if dense: valid = dense
    elif seg_type in ('break', 'intro', 'outro'):
        sparse = [p for p in valid if p.density_class == 'sparse']
        if sparse: valid = sparse

    return random.choice(valid)


# ════════════════════════════════════════
# PHASE 6: VALIDATION
# ════════════════════════════════════════

def validate_chart(notes: list[MappedNote], feat: AudioFeatures) -> ValidationReport:
    warnings = []
    n = len(notes)
    if n == 0:
        return ValidationReport(0, ["Chart has zero notes"], 0, 0, 0, 0)

    # Density check
    dur_s = feat.duration_ms / 1000
    nps = n / dur_s
    if nps > 12:
        warnings.append(f"Very high density: {nps:.1f} notes/sec")
    elif nps < 0.5:
        warnings.append(f"Very low density: {nps:.1f} notes/sec")

    # Cluster check
    cluster_count = 0
    for i in range(1, n):
        if notes[i].time - notes[i-1].time < 30:
            cluster_count += 1
    if cluster_count > n * 0.1:
        warnings.append(f"Too many clusters: {cluster_count} (<30ms gaps)")

    # Lane balance
    ground = sum(1 for x in notes if x.lane == 'Ground')
    air = sum(1 for x in notes if x.lane == 'Air')
    ratio = ground / max(1, air)
    if ratio > 4 or ratio < 0.25:
        warnings.append(f"Unbalanced lanes: ground={ground} air={air}")

    # Musical alignment
    beat_ms = 60000 / feat.bpm
    on_beat = sum(1 for x in notes if (x.time % beat_ms) / beat_ms < 0.12 or (x.time % beat_ms) / beat_ms > 0.88)
    beat_ratio = on_beat / n
    musical_score = min(1.0, beat_ratio + 0.3)

    density_score = max(0, min(1, 1 - abs(nps - 4) / 8))
    readability = max(0, 1 - cluster_count / max(1, n))
    overall = (musical_score * 0.4 + density_score * 0.3 + readability * 0.3)

    return ValidationReport(n, warnings, density_score, readability, musical_score, overall)


# ════════════════════════════════════════
# EXPORT
# ════════════════════════════════════════

def export_chart(notes: list[MappedNote], feat: AudioFeatures,
                 segments: list[Segment], report: ValidationReport,
                 song_id: str, diff_id: str, diff_level: int,
                 approach_ms: float = 1200) -> dict:
    hw = {3: {'perfect':45,'great':90,'good':135},
          6: {'perfect':35,'great':70,'good':110},
          9: {'perfect':25,'great':55,'good':90}}
    closest = min(hw.keys(), key=lambda k: abs(k - diff_level))

    objects = []
    for note in notes:
        objects.append({
            'id': f"obj_{len(objects)+1:04d}",
            'type': note.obj_type,
            'lane': note.lane,
            'hitTime': note.time,
            'spawnTime': round(note.time - approach_ms, 1),
            'actionType': note.action,
            'duration': note.duration,
        })

    events = []
    for seg in segments:
        events.append({
            'time': seg.start_ms,
            'type': 'SegmentMarker',
            'payload': {'segmentType': seg.seg_type, 'energy': round(seg.energy, 2)}
        })

    return {
        'songId': song_id,
        'difficultyId': diff_id,
        'globalOffsetMs': 0,
        'approachTimeMs': approach_ms,
        'hitWindowProfile': hw[closest],
        'objects': objects,
        'events': events,
        '_meta': {
            'bpm': feat.bpm,
            'total_notes': report.total_notes,
            'quality_score': round(report.overall_quality, 2),
            'density_nps': round(len(notes) / (feat.duration_ms / 1000), 1),
            'warnings': report.warnings,
            'segments': [{'type': s.seg_type, 'start': s.start_ms, 'energy': round(s.energy, 2)} for s in segments],
        }
    }


# ════════════════════════════════════════
# MAIN API
# ════════════════════════════════════════

def generate_chart(audio_path: str, song_id: str = '', difficulty: int = 5,
                   diff_id: str = 'normal') -> dict:
    """Full pipeline: audio → analysis → structure → candidates → patterns → validate → export."""
    if not song_id:
        song_id = os.path.splitext(os.path.basename(audio_path))[0]

    feat = analyze_audio(audio_path)
    segments = detect_segments(feat)
    candidates = generate_candidates(feat, segments)
    notes = map_chart(feat, segments, candidates, difficulty)
    report = validate_chart(notes, feat)

    approach = {1:1600, 2:1500, 3:1400, 4:1300, 5:1200, 6:1100, 7:1000, 8:900, 9:800, 10:700}.get(difficulty, 1200)

    chart = export_chart(notes, feat, segments, report, song_id, diff_id, difficulty, approach)

    print(f"[Mapper] {song_id}/{diff_id}: {report.total_notes} notes, "
          f"BPM={feat.bpm}, quality={report.overall_quality:.2f}, "
          f"segments={len(segments)}, warnings={len(report.warnings)}")
    for w in report.warnings:
        print(f"  ⚠ {w}")

    return chart
