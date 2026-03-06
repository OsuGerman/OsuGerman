export enum Lane {
  Ground = 0,
  Air = 1,
}

export interface Note {
  time: number;
  lane: Lane;
  hit?: boolean;
  missed?: boolean;
}

export interface Beatmap {
  id: string;
  title: string;
  artist: string;
  bpm: number;
  offset: number;
  notes: Note[];
  audioBase64?: string;
  difficulty: number;
}

export interface GameResult {
  score: number;
  maxCombo: number;
  accuracy: number;
  perfect: number;
  great: number;
  good: number;
  miss: number;
  grade: string;
  beatmapTitle: string;
}

export interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  color: string;
  size: number;
}

export interface JudgmentPopup {
  text: string;
  color: string;
  x: number;
  y: number;
  life: number;
  scale: number;
}

export type ScreenId = 'menu' | 'select' | 'game' | 'editor' | 'result';

export const PERFECT_WINDOW = 45;
export const GREAT_WINDOW = 90;
export const GOOD_WINDOW = 135;

export const SCORE_PERFECT = 300;
export const SCORE_GREAT = 200;
export const SCORE_GOOD = 100;

export const COLORS = {
  bg: '#0f0524',
  bgGrad: '#1a0a3e',
  ground: '#ff4d8d',
  groundDark: '#cc2266',
  air: '#00d4ff',
  airDark: '#0099bb',
  perfect: '#ffd700',
  great: '#00e676',
  good: '#42a5f5',
  miss: '#ff5252',
  accent: '#e040fb',
  white: '#ffffff',
  uiBg: 'rgba(15, 5, 36, 0.85)',
  lane: 'rgba(255,255,255,0.03)',
};

export const GROUND_KEYS = ['d', 'j', 'arrowdown'];
export const AIR_KEYS = ['f', 'k', 'arrowup'];
