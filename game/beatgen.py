"""Auto-generate beatmaps from audio files using onset/beat detection."""
from __future__ import annotations
import numpy as np
import soundfile as sf
import os
import json


def analyze_audio(path: str) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, dtype='float32')
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    return data, sr


def detect_onsets(data: np.ndarray, sr: int, hop_ms: float = 10) -> np.ndarray:
    hop = int(sr * hop_ms / 1000)
    frame_size = hop * 2
    n_frames = max(1, (len(data) - frame_size) // hop)

    spec_prev = None
    flux = np.zeros(n_frames)

    for i in range(n_frames):
        start = i * hop
        frame = data[start:start + frame_size] * np.hanning(frame_size)
        spec = np.abs(np.fft.rfft(frame))
        if spec_prev is not None:
            diff = spec - spec_prev
            diff[diff < 0] = 0
            flux[i] = np.sum(diff)
        spec_prev = spec

    if flux.max() > 0:
        flux /= flux.max()

    window = int(100 / hop_ms)
    if window < 3:
        window = 3
    mean = np.convolve(flux, np.ones(window) / window, mode='same')
    threshold = mean + 0.15

    peaks = []
    min_gap = int(80 / hop_ms)
    last_peak = -min_gap
    for i in range(1, len(flux) - 1):
        if flux[i] > flux[i - 1] and flux[i] > flux[i + 1] and flux[i] > threshold[i]:
            if i - last_peak >= min_gap:
                peaks.append(i)
                last_peak = i

    return np.array(peaks) * hop_ms


def estimate_bpm(onset_times_ms: np.ndarray, min_bpm: float = 60, max_bpm: float = 200) -> float:
    if len(onset_times_ms) < 4:
        return 120.0

    intervals = np.diff(onset_times_ms)
    intervals = intervals[(intervals > 60000 / max_bpm) & (intervals < 60000 / min_bpm)]

    if len(intervals) < 3:
        return 120.0

    hist_bins = np.arange(60000 / max_bpm, 60000 / min_bpm, 5)
    hist, edges = np.histogram(intervals, bins=hist_bins)

    best_idx = np.argmax(hist)
    best_interval = (edges[best_idx] + edges[best_idx + 1]) / 2
    bpm = 60000.0 / best_interval

    for mult in [0.5, 1.0, 2.0]:
        candidate = bpm * mult
        if min_bpm <= candidate <= max_bpm:
            return round(candidate, 1)

    return round(bpm, 1)


def get_frequency_band(data: np.ndarray, sr: int, time_ms: float, frame_ms: float = 30) -> str:
    start = int(time_ms / 1000 * sr)
    length = int(frame_ms / 1000 * sr)
    end = min(start + length, len(data))
    if start >= end:
        return 'low'
    frame = data[start:end]
    if len(frame) < 16:
        return 'low'
    spec = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
    freqs = np.fft.rfftfreq(len(frame), 1.0 / sr)
    low_energy = np.sum(spec[freqs < 300])
    high_energy = np.sum(spec[freqs >= 300])
    total = low_energy + high_energy + 1e-10
    return 'low' if low_energy / total > 0.55 else 'high'


def quantize_to_grid(time_ms: float, beat_ms: float, snap: int = 4) -> float:
    div = beat_ms / snap
    return round(time_ms / div) * div


def generate_beatmap(audio_path: str, target_difficulty: int = 5) -> dict:
    data, sr = analyze_audio(audio_path)
    duration_ms = len(data) / sr * 1000

    onset_times = detect_onsets(data, sr)
    if len(onset_times) < 5:
        onset_times = np.arange(0, duration_ms, 500)

    bpm = estimate_bpm(onset_times)
    beat_ms = 60000.0 / bpm

    snap = 4 if target_difficulty <= 5 else 8
    density = 0.5 + target_difficulty * 0.08

    quantized = set()
    notes = []

    for t in onset_times:
        qt = quantize_to_grid(t, beat_ms, snap)
        if qt < 200 or qt > duration_ms - 500:
            continue
        if qt in quantized:
            continue
        quantized.add(qt)

        band = get_frequency_band(data, sr, t)
        lane = 0 if band == 'low' else 1
        notes.append({'time': round(float(qt), 1), 'lane': int(lane)})

    if target_difficulty >= 6 and len(notes) > 10:
        extra = []
        for i in range(0, len(notes) - 1):
            gap = notes[i + 1]['time'] - notes[i]['time']
            if gap > beat_ms * 1.5:
                mid = quantize_to_grid((notes[i]['time'] + notes[i + 1]['time']) / 2, beat_ms, snap)
                if mid not in quantized:
                    extra.append({'time': round(float(mid), 1), 'lane': 1 - notes[i]['lane']})
                    quantized.add(mid)
        notes.extend(extra)

    notes.sort(key=lambda n: n['time'])

    prev_lane = -1
    for n in notes:
        if n['lane'] == prev_lane and np.random.random() < 0.3:
            n['lane'] = 1 - n['lane']
        prev_lane = n['lane']

    name = os.path.splitext(os.path.basename(audio_path))[0]

    return {
        'id': f"auto_{hash(audio_path) & 0xFFFFFF:06x}",
        'title': name,
        'artist': 'Auto-Generated',
        'bpm': float(bpm),
        'offset': 0,
        'difficulty': target_difficulty,
        'audio_file': os.path.abspath(audio_path),
        'notes': notes,
    }
