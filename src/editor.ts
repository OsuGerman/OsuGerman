import { Beatmap, Note, Lane, COLORS } from './types';
import { MusicPlayer, decodeAudio, arrayBufferToBase64 } from './audio';
import { saveBeatmap, generateId } from './storage';

export class EditorScreen {
  private container: HTMLElement;
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private player: MusicPlayer;
  private notes: Note[] = [];
  private bpm = 120;
  private offset = 0;
  private title = 'Neues Lied';
  private artist = 'Unbekannt';
  private difficulty = 5;
  private editId: string;
  private audioBase64: string | null = null;
  private rawAudioBuffer: ArrayBuffer | null = null;

  private zoom = 100;
  private scrollX = 0;
  private selectedNote: number = -1;
  private snapEnabled = true;
  private snapDivision = 4;
  private playing = false;

  private onSave: () => void;
  private onBack: () => void;
  private onTest: (map: Beatmap) => void;
  private animId = 0;
  private destroyed = false;

  constructor(
    container: HTMLElement,
    canvas: HTMLCanvasElement,
    player: MusicPlayer,
    opts: {
      onSave: () => void;
      onBack: () => void;
      onTest: (map: Beatmap) => void;
      beatmap?: Beatmap;
    },
  ) {
    this.container = container;
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.player = player;
    this.onSave = opts.onSave;
    this.onBack = opts.onBack;
    this.onTest = opts.onTest;
    this.editId = opts.beatmap?.id || generateId();

    if (opts.beatmap) {
      this.title = opts.beatmap.title;
      this.artist = opts.beatmap.artist;
      this.bpm = opts.beatmap.bpm;
      this.offset = opts.beatmap.offset;
      this.difficulty = opts.beatmap.difficulty;
      this.notes = opts.beatmap.notes.map(n => ({ ...n }));
      this.audioBase64 = opts.beatmap.audioBase64 || null;
    }

    this.buildUI();
    this.bindEvents();
    this.loop();
  }

  destroy() {
    this.destroyed = true;
    cancelAnimationFrame(this.animId);
    this.player.stop();
    this.container.innerHTML = '';
  }

  private buildUI() {
    this.container.innerHTML = `
      <div class="editor-panel">
        <div class="editor-top">
          <button id="ed-back" class="btn btn-sm">← Zurück</button>
          <div class="editor-fields">
            <label>Audio: <input type="file" id="ed-audio" accept="audio/*" /></label>
            <label>Titel: <input type="text" id="ed-title" value="${this.title}" /></label>
            <label>Artist: <input type="text" id="ed-artist" value="${this.artist}" /></label>
            <label>BPM: <input type="number" id="ed-bpm" value="${this.bpm}" min="30" max="400" step="0.5" /></label>
            <label>Offset (ms): <input type="number" id="ed-offset" value="${this.offset}" step="1" /></label>
            <label>Schwierigkeit: <input type="range" id="ed-diff" value="${this.difficulty}" min="1" max="10" /></label>
          </div>
          <div class="editor-actions">
            <button id="ed-save" class="btn btn-accent">Speichern</button>
            <button id="ed-test" class="btn btn-sm">▶ Testen</button>
            <button id="ed-export" class="btn btn-sm">Exportieren</button>
          </div>
        </div>
        <div class="editor-controls">
          <button id="ed-play" class="btn btn-sm">▶ Play</button>
          <button id="ed-stop" class="btn btn-sm">■ Stop</button>
          <span id="ed-time" class="ed-time">0:00.0 / 0:00.0</span>
          <label class="ed-label">Snap: <select id="ed-snap">
            <option value="0">Aus</option>
            <option value="2">1/2</option>
            <option value="3">1/3</option>
            <option value="4" selected>1/4</option>
            <option value="6">1/6</option>
            <option value="8">1/8</option>
            <option value="16">1/16</option>
          </select></label>
          <label class="ed-label">Zoom: <input type="range" id="ed-zoom" min="30" max="500" value="${this.zoom}" /></label>
          <span class="ed-hint">[D/J] Boden-Note  [F/K] Luft-Note  [Entf] Löschen  [Leertaste] Play/Pause</span>
        </div>
      </div>
    `;
  }

  private el<T extends HTMLElement>(id: string): T {
    return this.container.querySelector(`#${id}`)! as T;
  }

  private bindEvents() {
    this.el<HTMLButtonElement>('ed-back').onclick = () => { this.destroy(); this.onBack(); };
    this.el<HTMLInputElement>('ed-title').oninput = (e) => { this.title = (e.target as HTMLInputElement).value; };
    this.el<HTMLInputElement>('ed-artist').oninput = (e) => { this.artist = (e.target as HTMLInputElement).value; };
    this.el<HTMLInputElement>('ed-bpm').oninput = (e) => { this.bpm = parseFloat((e.target as HTMLInputElement).value) || 120; };
    this.el<HTMLInputElement>('ed-offset').oninput = (e) => { this.offset = parseInt((e.target as HTMLInputElement).value) || 0; };
    this.el<HTMLInputElement>('ed-diff').oninput = (e) => { this.difficulty = parseInt((e.target as HTMLInputElement).value) || 5; };
    this.el<HTMLInputElement>('ed-zoom').oninput = (e) => { this.zoom = parseInt((e.target as HTMLInputElement).value) || 100; };
    this.el<HTMLSelectElement>('ed-snap').onchange = (e) => {
      const v = parseInt((e.target as HTMLSelectElement).value);
      this.snapEnabled = v > 0;
      this.snapDivision = v || 4;
    };

    this.el<HTMLInputElement>('ed-audio').onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const ab = await file.arrayBuffer();
      this.rawAudioBuffer = ab.slice(0);
      const buf = await decodeAudio(ab);
      this.player.load(buf);
      this.audioBase64 = arrayBufferToBase64(this.rawAudioBuffer);
      this.title = file.name.replace(/\.[^.]+$/, '');
      this.el<HTMLInputElement>('ed-title').value = this.title;
    };

    this.el<HTMLButtonElement>('ed-play').onclick = () => this.togglePlay();
    this.el<HTMLButtonElement>('ed-stop').onclick = () => { this.player.stop(); this.playing = false; this.scrollX = 0; };
    this.el<HTMLButtonElement>('ed-save').onclick = () => this.save();
    this.el<HTMLButtonElement>('ed-test').onclick = () => { this.player.stop(); this.playing = false; this.onTest(this.buildBeatmap()); };
    this.el<HTMLButtonElement>('ed-export').onclick = () => this.exportMap();

    window.addEventListener('keydown', this.handleKey);
    this.canvas.addEventListener('mousedown', this.handleMouse);
    this.canvas.addEventListener('wheel', this.handleWheel, { passive: false });
  }

  private handleKey = (e: KeyboardEvent) => {
    if (this.destroyed) return;
    const k = e.key.toLowerCase();
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;

    if (k === ' ') { e.preventDefault(); this.togglePlay(); }
    if (k === 'delete' || k === 'backspace') {
      if (this.selectedNote >= 0) {
        this.notes.splice(this.selectedNote, 1);
        this.selectedNote = -1;
      }
    }
    if (['d', 'j', 'arrowdown'].includes(k)) { e.preventDefault(); this.placeNote(Lane.Ground); }
    if (['f', 'k', 'arrowup'].includes(k)) { e.preventDefault(); this.placeNote(Lane.Air); }
  };

  private handleMouse = (e: MouseEvent) => {
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const h = this.canvas.height;
    const pxPerMs = this.zoom / 1000;

    this.selectedNote = -1;
    for (let i = 0; i < this.notes.length; i++) {
      const n = this.notes[i];
      const nx = (n.time * pxPerMs) - this.scrollX + 80;
      const ny = n.lane === Lane.Air ? h * 0.3 : h * 0.7;
      if (Math.abs(mx - nx) < 12 && Math.abs(my - ny) < 12) {
        this.selectedNote = i;
        break;
      }
    }
  };

  private handleWheel = (e: WheelEvent) => {
    if (this.destroyed) return;
    e.preventDefault();
    if (e.ctrlKey) {
      this.zoom = Math.max(30, Math.min(500, this.zoom - e.deltaY * 0.5));
      this.el<HTMLInputElement>('ed-zoom').value = this.zoom.toString();
    } else {
      this.scrollX = Math.max(0, this.scrollX + e.deltaY * 0.5);
    }
  };

  private togglePlay() {
    if (!this.player.buffer) return;
    if (this.playing) { this.player.pause(); this.playing = false; }
    else { this.player.play(); this.playing = true; }
  }

  private placeNote(lane: Lane) {
    const time = this.playing ? this.player.currentTime * 1000 : (this.scrollX * 1000 / this.zoom);
    const snapped = this.snapEnabled ? this.snapTime(time) : Math.round(time);
    if (this.notes.some(n => n.lane === lane && Math.abs(n.time - snapped) < 20)) return;
    this.notes.push({ time: snapped, lane });
    this.notes.sort((a, b) => a.time - b.time);
  }

  private snapTime(ms: number): number {
    const beatMs = 60000 / this.bpm;
    const divMs = beatMs / this.snapDivision;
    return Math.round((ms - this.offset) / divMs) * divMs + this.offset;
  }

  private save() {
    const map = this.buildBeatmap();
    saveBeatmap(map);
    this.onSave();
  }

  private buildBeatmap(): Beatmap {
    return {
      id: this.editId,
      title: this.title,
      artist: this.artist,
      bpm: this.bpm,
      offset: this.offset,
      difficulty: this.difficulty,
      notes: this.notes.map(n => ({ time: n.time, lane: n.lane })),
      audioBase64: this.audioBase64 || undefined,
    };
  }

  private exportMap() {
    const map = this.buildBeatmap();
    const json = JSON.stringify(map, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${this.title.replace(/[^a-zA-Z0-9]/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  private loop = () => {
    if (this.destroyed) return;
    this.renderTimeline();
    this.updateTimeDisplay();
    if (this.playing) {
      this.scrollX = this.player.currentTime * 1000 * this.zoom / 1000 - this.canvas.width * 0.3;
      if (this.scrollX < 0) this.scrollX = 0;
    }
    this.animId = requestAnimationFrame(this.loop);
  };

  private updateTimeDisplay() {
    const cur = this.player.currentTime;
    const dur = this.player.duration;
    const fmt = (s: number) => {
      const m = Math.floor(s / 60);
      const sec = (s % 60).toFixed(1).padStart(4, '0');
      return `${m}:${sec}`;
    };
    this.el<HTMLSpanElement>('ed-time').textContent = `${fmt(cur)} / ${fmt(dur)}`;
  }

  private renderTimeline() {
    const c = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const pxPerMs = this.zoom / 1000;

    c.fillStyle = '#0d0420';
    c.fillRect(0, 0, w, h);

    c.fillStyle = 'rgba(255,255,255,0.03)';
    c.fillRect(0, 0, w, h * 0.5);

    c.strokeStyle = 'rgba(255,255,255,0.15)';
    c.lineWidth = 1;
    c.beginPath();
    c.moveTo(0, h * 0.5);
    c.lineTo(w, h * 0.5);
    c.stroke();

    const beatMs = 60000 / this.bpm;
    const startMs = Math.max(0, (this.scrollX / pxPerMs));
    const endMs = startMs + w / pxPerMs;
    const firstBeat = Math.floor((startMs - this.offset) / beatMs);
    const lastBeat = Math.ceil((endMs - this.offset) / beatMs);

    for (let b = firstBeat; b <= lastBeat; b++) {
      const t = this.offset + b * beatMs;
      const x = (t * pxPerMs) - this.scrollX + 80;
      if (x < 0 || x > w) continue;
      const isMeasure = b >= 0 && b % 4 === 0;
      c.strokeStyle = isMeasure ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.07)';
      c.lineWidth = isMeasure ? 1.5 : 0.5;
      c.beginPath();
      c.moveTo(x, 0);
      c.lineTo(x, h);
      c.stroke();

      if (isMeasure && b >= 0) {
        c.fillStyle = 'rgba(255,255,255,0.4)';
        c.font = '11px system-ui, sans-serif';
        c.textAlign = 'center';
        c.fillText(`${b / 4 + 1}`, x, h - 5);
      }

      if (this.snapEnabled && this.snapDivision > 1) {
        for (let s = 1; s < this.snapDivision; s++) {
          const st = t + (beatMs / this.snapDivision) * s;
          const sx = (st * pxPerMs) - this.scrollX + 80;
          if (sx < 0 || sx > w) continue;
          c.strokeStyle = 'rgba(255,255,255,0.03)';
          c.lineWidth = 0.5;
          c.beginPath();
          c.moveTo(sx, 0);
          c.lineTo(sx, h);
          c.stroke();
        }
      }
    }

    for (let i = 0; i < this.notes.length; i++) {
      const n = this.notes[i];
      const x = (n.time * pxPerMs) - this.scrollX + 80;
      if (x < -20 || x > w + 20) continue;
      const y = n.lane === Lane.Air ? h * 0.3 : h * 0.7;
      const color = n.lane === Lane.Air ? COLORS.air : COLORS.ground;
      const selected = i === this.selectedNote;

      c.fillStyle = color;
      c.shadowColor = color;
      c.shadowBlur = selected ? 20 : 8;
      c.beginPath();
      c.arc(x, y, selected ? 10 : 8, 0, Math.PI * 2);
      c.fill();
      c.shadowBlur = 0;

      if (selected) {
        c.strokeStyle = '#ffffff';
        c.lineWidth = 2;
        c.beginPath();
        c.arc(x, y, 13, 0, Math.PI * 2);
        c.stroke();
      }
    }

    if (this.playing) {
      const playX = (this.player.currentTime * 1000 * pxPerMs) - this.scrollX + 80;
      c.strokeStyle = COLORS.perfect;
      c.lineWidth = 2;
      c.beginPath();
      c.moveTo(playX, 0);
      c.lineTo(playX, h);
      c.stroke();
    }

    c.fillStyle = 'rgba(255,255,255,0.5)';
    c.font = '12px system-ui, sans-serif';
    c.textAlign = 'left';
    c.fillText('Luft ↑', 10, h * 0.3 + 4);
    c.fillText('Boden ↓', 10, h * 0.7 + 4);
    c.textAlign = 'right';
    c.fillText(`${this.notes.length} Noten`, w - 10, 20);
  }
}
