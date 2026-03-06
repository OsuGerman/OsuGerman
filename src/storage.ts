import { Beatmap, Note, Lane } from './types';

const STORAGE_KEY = 'rhythmDash_beatmaps';

export function saveBeatmap(map: Beatmap) {
  const all = loadAllBeatmaps();
  const idx = all.findIndex(m => m.id === map.id);
  if (idx >= 0) all[idx] = map;
  else all.push(map);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
  } catch {
    const slim = all.map(m => ({ ...m, audioBase64: undefined }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(slim));
  }
}

export function loadAllBeatmaps(): Beatmap[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as Beatmap[];
  } catch {
    return [];
  }
}

export function deleteBeatmap(id: string) {
  const all = loadAllBeatmaps().filter(m => m.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

export function exportBeatmap(map: Beatmap): string {
  return JSON.stringify(map, null, 2);
}

export function importBeatmap(json: string): Beatmap | null {
  try {
    const obj = JSON.parse(json);
    if (!obj.id || !obj.title || !Array.isArray(obj.notes)) return null;
    return {
      id: obj.id,
      title: obj.title,
      artist: obj.artist || 'Unknown',
      bpm: obj.bpm || 120,
      offset: obj.offset || 0,
      difficulty: obj.difficulty || 5,
      notes: obj.notes.map((n: { time: number; lane: number }) => ({
        time: n.time,
        lane: n.lane === Lane.Air ? Lane.Air : Lane.Ground,
      } as Note)),
      audioBase64: obj.audioBase64,
    };
  } catch {
    return null;
  }
}

export function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}
