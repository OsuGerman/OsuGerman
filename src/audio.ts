let ctx: AudioContext | null = null;
let masterGain: GainNode | null = null;

export function getAudioContext(): AudioContext {
  if (!ctx) {
    ctx = new AudioContext();
    masterGain = ctx.createGain();
    masterGain.connect(ctx.destination);
    masterGain.gain.value = 0.7;
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function getMaster(): GainNode {
  getAudioContext();
  return masterGain!;
}

export async function decodeAudio(data: ArrayBuffer): Promise<AudioBuffer> {
  const ac = getAudioContext();
  return ac.decodeAudioData(data);
}

export async function audioFromBase64(b64: string): Promise<AudioBuffer> {
  const bin = atob(b64);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  return decodeAudio(buf.buffer);
}

export function arrayBufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

export class MusicPlayer {
  private source: AudioBufferSourceNode | null = null;
  private _buffer: AudioBuffer | null = null;
  private _startCtxTime = 0;
  private _startOffset = 0;
  private _playing = false;
  private gainNode: GainNode;

  constructor() {
    const ac = getAudioContext();
    this.gainNode = ac.createGain();
    this.gainNode.connect(getMaster());
  }

  get buffer() { return this._buffer; }
  get playing() { return this._playing; }
  get duration() { return this._buffer ? this._buffer.duration : 0; }

  get currentTime(): number {
    if (!this._playing) return this._startOffset;
    const ac = getAudioContext();
    return this._startOffset + (ac.currentTime - this._startCtxTime);
  }

  set volume(v: number) { this.gainNode.gain.value = v; }

  load(buf: AudioBuffer) {
    this.stop();
    this._buffer = buf;
    this._startOffset = 0;
  }

  play(offset?: number) {
    if (!this._buffer) return;
    this.stopSource();
    const ac = getAudioContext();
    this.source = ac.createBufferSource();
    this.source.buffer = this._buffer;
    this.source.connect(this.gainNode);
    const off = offset !== undefined ? offset : this._startOffset;
    this._startOffset = Math.max(0, Math.min(off, this._buffer.duration));
    this._startCtxTime = ac.currentTime;
    this.source.start(0, this._startOffset);
    this._playing = true;
    this.source.onended = () => {
      if (this._playing) {
        this._playing = false;
        this._startOffset = this._buffer ? this._buffer.duration : 0;
      }
    };
  }

  pause() {
    if (!this._playing) return;
    this._startOffset = this.currentTime;
    this.stopSource();
    this._playing = false;
  }

  stop() {
    this.stopSource();
    this._playing = false;
    this._startOffset = 0;
  }

  seek(time: number) {
    this._startOffset = Math.max(0, Math.min(time, this.duration));
    if (this._playing) this.play(this._startOffset);
  }

  private stopSource() {
    if (this.source) {
      try { this.source.stop(); } catch (_) { /* already stopped */ }
      this.source.disconnect();
      this.source = null;
    }
  }
}

export function playSfx(type: 'perfect' | 'great' | 'good' | 'miss') {
  const ac = getAudioContext();
  const osc = ac.createOscillator();
  const g = ac.createGain();
  osc.connect(g);
  g.connect(getMaster());
  const now = ac.currentTime;
  g.gain.setValueAtTime(0.15, now);
  g.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
  switch (type) {
    case 'perfect':
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.exponentialRampToValueAtTime(1320, now + 0.05);
      break;
    case 'great':
      osc.type = 'sine';
      osc.frequency.setValueAtTime(660, now);
      break;
    case 'good':
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(440, now);
      break;
    case 'miss':
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(150, now);
      g.gain.setValueAtTime(0.08, now);
      break;
  }
  osc.start(now);
  osc.stop(now + 0.15);
}

export function generateDemoAudio(): AudioBuffer {
  const ac = getAudioContext();
  const sr = ac.sampleRate;
  const dur = 32;
  const len = sr * dur;
  const buf = ac.createBuffer(2, len, sr);
  const L = buf.getChannelData(0);
  const R = buf.getChannelData(1);
  const bpm = 128;
  const beatSamples = (60 / bpm) * sr;

  for (let i = 0; i < len; i++) {
    const t = i / sr;
    const beatPos = (i % beatSamples) / beatSamples;

    let kick = 0;
    if (beatPos < 0.15) {
      const env = 1 - beatPos / 0.15;
      kick = Math.sin(2 * Math.PI * (160 - 120 * beatPos) * t) * env * env * 0.6;
    }

    const halfBeat = (i % (beatSamples / 2)) / (beatSamples / 2);
    let hihat = 0;
    if (halfBeat < 0.03) {
      hihat = (Math.random() * 2 - 1) * (1 - halfBeat / 0.03) * 0.15;
    }

    const beatInBar = Math.floor((i / beatSamples) % 4);
    let snare = 0;
    if (beatInBar === 2 && beatPos < 0.08) {
      const env = 1 - beatPos / 0.08;
      snare = (Math.random() * 2 - 1) * env * 0.3;
      snare += Math.sin(2 * Math.PI * 200 * t) * env * 0.2;
    }

    const bassFreq = [65, 65, 82, 73][(Math.floor(t / (4 * 60 / bpm))) % 4];
    const bass = Math.sin(2 * Math.PI * bassFreq * t) * 0.2;

    const barNum = Math.floor(i / (beatSamples * 4));
    let melody = 0;
    if (barNum >= 2) {
      const melodyNotes = [523, 587, 659, 784, 659, 587, 523, 440];
      const eighthBeat = Math.floor((i / (beatSamples / 2)) % 8);
      const freq = melodyNotes[eighthBeat];
      const eighthPos = (i % (beatSamples / 2)) / (beatSamples / 2);
      const mEnv = eighthPos < 0.9 ? 1 : (1 - (eighthPos - 0.9) / 0.1);
      melody = Math.sin(2 * Math.PI * freq * t) * mEnv * 0.12;
      melody += Math.sin(2 * Math.PI * freq * 2 * t) * mEnv * 0.04;
    }

    const sample = kick + hihat + snare + bass + melody;
    L[i] = sample;
    R[i] = sample;
  }

  return buf;
}

export function generateDemoBeatmap() {
  const bpm = 128;
  const beatMs = (60 / bpm) * 1000;
  const notes: { time: number; lane: 0 | 1 }[] = [];

  for (let bar = 0; bar < 16; bar++) {
    const barStart = bar * 4 * beatMs;

    for (let beat = 0; beat < 4; beat++) {
      const t = barStart + beat * beatMs;
      notes.push({ time: t, lane: 0 });
    }

    if (bar >= 2) {
      notes.push({ time: barStart + 1 * beatMs + beatMs / 2, lane: 1 });
      notes.push({ time: barStart + 3 * beatMs + beatMs / 2, lane: 1 });
    }

    if (bar >= 4 && bar % 2 === 0) {
      notes.push({ time: barStart + 0 * beatMs + beatMs / 2, lane: 1 });
      notes.push({ time: barStart + 2 * beatMs + beatMs / 2, lane: 0 });
    }

    if (bar >= 8) {
      for (let e = 0; e < 8; e++) {
        const t = barStart + e * (beatMs / 2);
        if (!notes.some(n => Math.abs(n.time - t) < 10)) {
          notes.push({ time: t, lane: e % 3 === 0 ? 1 : 0 });
        }
      }
    }
  }

  notes.sort((a, b) => a.time - b.time);
  return {
    id: 'demo',
    title: 'Demo Beat',
    artist: 'Rhythm Dash',
    bpm,
    offset: 0,
    difficulty: 4,
    notes: notes.map(n => ({ time: Math.round(n.time), lane: n.lane as 0 | 1 })),
  };
}
