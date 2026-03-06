import {
  Beatmap, Note, Lane, Particle, JudgmentPopup, GameResult,
  PERFECT_WINDOW, GREAT_WINDOW, GOOD_WINDOW,
  SCORE_PERFECT, SCORE_GREAT, SCORE_GOOD,
  COLORS, GROUND_KEYS, AIR_KEYS,
} from './types';
import { MusicPlayer, playSfx } from './audio';
import { anyOfJustPressed, wasJustPressed } from './input';

const HIT_X = 0.15;
const NOTE_SPEED = 0.45;
const GROUND_RATIO = 0.68;
const AIR_RATIO = 0.38;
const NOTE_RADIUS = 22;
const AUTO_MISS_MS = GOOD_WINDOW + 50;

export class GameScreen {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private player: MusicPlayer;
  private beatmap: Beatmap;
  private notes: (Note & { hit?: boolean; missed?: boolean })[];
  private noteIndex = 0;

  private score = 0;
  private combo = 0;
  private maxCombo = 0;
  private perfect = 0;
  private great = 0;
  private good = 0;
  private miss = 0;
  private health = 100;

  private particles: Particle[] = [];
  private judgments: JudgmentPopup[] = [];
  private shakeAmount = 0;
  private bgOffset = 0;
  private charFrame = 0;
  private charTimer = 0;
  private charAction: 'run' | 'groundHit' | 'airHit' = 'run';
  private charActionTimer = 0;
  private countdownTimer = 0;
  private countdownValue = 3;
  private started = false;
  private paused = false;
  private finished = false;
  private onFinish: (result: GameResult) => void;

  constructor(
    canvas: HTMLCanvasElement,
    player: MusicPlayer,
    beatmap: Beatmap,
    onFinish: (result: GameResult) => void,
  ) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.player = player;
    this.beatmap = beatmap;
    this.notes = beatmap.notes.map(n => ({ ...n }));
    this.notes.sort((a, b) => a.time - b.time);
    this.onFinish = onFinish;
    this.countdownTimer = performance.now();
  }

  get isPaused() { return this.paused; }
  get isFinished() { return this.finished; }

  togglePause() {
    if (this.finished) return;
    this.paused = !this.paused;
    if (this.paused) this.player.pause();
    else if (this.started) this.player.play();
  }

  private get gameTimeMs(): number {
    return this.player.currentTime * 1000 - this.beatmap.offset;
  }

  update(_dt: number) {
    if (this.finished) return;

    if (this.paused) {
      if (wasJustPressed('escape')) this.togglePause();
      return;
    }

    if (wasJustPressed('escape') && this.started) {
      this.togglePause();
      return;
    }

    if (!this.started) {
      const elapsed = (performance.now() - this.countdownTimer) / 1000;
      this.countdownValue = 3 - Math.floor(elapsed);
      if (elapsed >= 3) {
        this.started = true;
        this.player.play(0);
      }
      return;
    }

    const time = this.gameTimeMs;

    for (let i = this.noteIndex; i < this.notes.length; i++) {
      const n = this.notes[i];
      if (n.hit || n.missed) { if (i === this.noteIndex) this.noteIndex++; continue; }
      if (n.time - time > AUTO_MISS_MS) break;
      if (time - n.time > AUTO_MISS_MS) {
        n.missed = true;
        this.registerMiss(n);
        if (i === this.noteIndex) this.noteIndex++;
      }
    }

    if (anyOfJustPressed(GROUND_KEYS)) this.tryHit(Lane.Ground, time);
    if (anyOfJustPressed(AIR_KEYS)) this.tryHit(Lane.Air, time);

    this.updateParticles(_dt);
    this.updateJudgments(_dt);
    this.shakeAmount *= 0.85;
    this.bgOffset += _dt * 0.06;
    this.charTimer += _dt;
    if (this.charTimer > 120) { this.charFrame = (this.charFrame + 1) % 4; this.charTimer = 0; }
    if (this.charActionTimer > 0) { this.charActionTimer -= _dt; if (this.charActionTimer <= 0) this.charAction = 'run'; }

    if (this.player.currentTime >= this.player.duration - 0.2 && this.player.duration > 0) {
      this.finish();
    }
  }

  private tryHit(lane: Lane, time: number) {
    let best: (Note & { hit?: boolean; missed?: boolean }) | null = null;
    let bestDiff = Infinity;
    for (let i = this.noteIndex; i < this.notes.length; i++) {
      const n = this.notes[i];
      if (n.hit || n.missed) continue;
      if (n.time - time > GOOD_WINDOW + 50) break;
      if (n.lane !== lane) continue;
      const diff = Math.abs(n.time - time);
      if (diff < bestDiff) { best = n; bestDiff = diff; }
    }
    if (!best) return;
    if (bestDiff <= GOOD_WINDOW) {
      best.hit = true;
      this.registerHit(best, bestDiff);
    }
  }

  private registerHit(note: Note, diff: number) {
    let type: 'perfect' | 'great' | 'good';
    let points: number;
    let color: string;
    if (diff <= PERFECT_WINDOW) {
      type = 'perfect'; points = SCORE_PERFECT; color = COLORS.perfect;
    } else if (diff <= GREAT_WINDOW) {
      type = 'great'; points = SCORE_GREAT; color = COLORS.great;
    } else {
      type = 'good'; points = SCORE_GOOD; color = COLORS.good;
    }
    this.combo++;
    if (this.combo > this.maxCombo) this.maxCombo = this.combo;
    const multiplier = 1 + Math.floor(this.combo / 10) * 0.1;
    this.score += Math.round(points * multiplier);
    if (type === 'perfect') this.perfect++;
    else if (type === 'great') this.great++;
    else this.good++;
    this.health = Math.min(100, this.health + 2);
    playSfx(type);

    const w = this.canvas.width;
    const h = this.canvas.height;
    const nx = w * HIT_X;
    const ny = note.lane === Lane.Air ? h * AIR_RATIO : h * GROUND_RATIO;
    this.spawnHitParticles(nx, ny, color);
    this.judgments.push({ text: type.toUpperCase() + '!', color, x: nx + 60, y: ny - 30, life: 800, scale: 1.5 });
    if (type === 'perfect') this.shakeAmount = 3;
    else this.shakeAmount = 1.5;
    this.charAction = note.lane === Lane.Air ? 'airHit' : 'groundHit';
    this.charActionTimer = 150;
  }

  private registerMiss(note: Note) {
    this.miss++;
    this.combo = 0;
    this.health = Math.max(0, this.health - 5);
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ny = note.lane === Lane.Air ? h * AIR_RATIO : h * GROUND_RATIO;
    this.judgments.push({ text: 'MISS', color: COLORS.miss, x: w * HIT_X + 60, y: ny - 30, life: 600, scale: 1.2 });
  }

  private spawnHitParticles(x: number, y: number, color: string) {
    for (let i = 0; i < 15; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 1 + Math.random() * 4;
      this.particles.push({
        x, y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1,
        life: 400 + Math.random() * 300,
        maxLife: 700,
        color,
        size: 3 + Math.random() * 5,
      });
    }
  }

  private updateParticles(dt: number) {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx * dt * 0.06;
      p.y += p.vy * dt * 0.06;
      p.vy += 0.05;
      p.life -= dt;
      if (p.life <= 0) this.particles.splice(i, 1);
    }
  }

  private updateJudgments(dt: number) {
    for (let i = this.judgments.length - 1; i >= 0; i--) {
      const j = this.judgments[i];
      j.life -= dt;
      j.y -= dt * 0.03;
      j.scale *= 0.995;
      if (j.life <= 0) this.judgments.splice(i, 1);
    }
  }

  private finish() {
    if (this.finished) return;
    this.finished = true;
    this.player.stop();
    const total = this.perfect + this.great + this.good + this.miss;
    const accuracy = total > 0
      ? ((this.perfect * 300 + this.great * 200 + this.good * 100) / (total * 300)) * 100
      : 0;
    let grade = 'D';
    if (accuracy >= 98) grade = 'S';
    else if (accuracy >= 92) grade = 'A';
    else if (accuracy >= 85) grade = 'B';
    else if (accuracy >= 70) grade = 'C';
    this.onFinish({
      score: this.score,
      maxCombo: this.maxCombo,
      accuracy: Math.round(accuracy * 100) / 100,
      perfect: this.perfect,
      great: this.great,
      good: this.good,
      miss: this.miss,
      grade,
      beatmapTitle: this.beatmap.title,
    });
  }

  render() {
    const c = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const sx = (Math.random() - 0.5) * this.shakeAmount;
    const sy = (Math.random() - 0.5) * this.shakeAmount;
    c.save();
    c.translate(sx, sy);

    this.drawBackground(c, w, h);
    this.drawLanes(c, w, h);
    this.drawNotes(c, w, h);
    this.drawCharacter(c, w, h);
    this.drawParticles(c);
    this.drawJudgments(c);
    this.drawHUD(c, w, h);

    if (!this.started) this.drawCountdown(c, w, h);
    if (this.paused) this.drawPauseOverlay(c, w, h);

    c.restore();
  }

  private drawBackground(c: CanvasRenderingContext2D, w: number, h: number) {
    const grad = c.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, '#0a0018');
    grad.addColorStop(0.5, COLORS.bg);
    grad.addColorStop(1, '#150830');
    c.fillStyle = grad;
    c.fillRect(0, 0, w, h);

    c.globalAlpha = 0.15;
    const starCount = 40;
    for (let i = 0; i < starCount; i++) {
      const px = ((i * 137.5 + this.bgOffset * (0.5 + (i % 3) * 0.3)) % (w + 40)) - 20;
      const py = ((i * 97.3) % h);
      const sz = 1 + (i % 3);
      c.fillStyle = i % 5 === 0 ? COLORS.accent : '#ffffff';
      c.beginPath();
      c.arc(px, py, sz, 0, Math.PI * 2);
      c.fill();
    }
    c.globalAlpha = 1;

    const lineY = h * GROUND_RATIO + NOTE_RADIUS + 10;
    c.fillStyle = COLORS.groundDark;
    c.fillRect(0, lineY, w, 3);
    const platformGrad = c.createLinearGradient(0, lineY, 0, lineY + 30);
    platformGrad.addColorStop(0, 'rgba(255,77,141,0.15)');
    platformGrad.addColorStop(1, 'rgba(255,77,141,0)');
    c.fillStyle = platformGrad;
    c.fillRect(0, lineY, w, 30);

    for (let i = 0; i < 8; i++) {
      const lx = ((i * w / 8 - this.bgOffset * 2) % w + w) % w;
      c.strokeStyle = 'rgba(255,255,255,0.04)';
      c.beginPath();
      c.moveTo(lx, lineY);
      c.lineTo(lx - 30, h);
      c.stroke();
    }
  }

  private drawLanes(c: CanvasRenderingContext2D, w: number, h: number) {
    const hitX = w * HIT_X;
    const groundY = h * GROUND_RATIO;
    const airY = h * AIR_RATIO;

    c.fillStyle = COLORS.lane;
    c.fillRect(0, airY - 30, w, 60);
    c.fillRect(0, groundY - 30, w, 60);

    c.strokeStyle = 'rgba(255,255,255,0.12)';
    c.setLineDash([8, 8]);
    c.beginPath();
    c.moveTo(hitX, 0);
    c.lineTo(hitX, h);
    c.stroke();
    c.setLineDash([]);

    const pulseAlpha = 0.08 + Math.sin(performance.now() * 0.005) * 0.04;
    c.fillStyle = `rgba(224,64,251,${pulseAlpha})`;
    c.fillRect(hitX - 20, 0, 40, h);
  }

  private drawNotes(c: CanvasRenderingContext2D, w: number, h: number) {
    const time = this.started ? this.gameTimeMs : 0;
    const hitX = w * HIT_X;
    const groundY = h * GROUND_RATIO;
    const airY = h * AIR_RATIO;

    for (const note of this.notes) {
      if (note.hit || note.missed) continue;
      const diffMs = note.time - time;
      const x = hitX + diffMs * NOTE_SPEED;
      if (x < -50 || x > w + 50) continue;
      const y = note.lane === Lane.Air ? airY : groundY;
      const color = note.lane === Lane.Air ? COLORS.air : COLORS.ground;
      const darkColor = note.lane === Lane.Air ? COLORS.airDark : COLORS.groundDark;

      c.save();

      c.shadowColor = color;
      c.shadowBlur = 18;
      c.fillStyle = color;
      if (note.lane === Lane.Air) {
        this.drawDiamond(c, x, y, NOTE_RADIUS);
      } else {
        c.beginPath();
        c.arc(x, y, NOTE_RADIUS, 0, Math.PI * 2);
        c.fill();
      }
      c.shadowBlur = 0;

      c.fillStyle = darkColor;
      if (note.lane === Lane.Air) {
        this.drawDiamond(c, x, y, NOTE_RADIUS * 0.55);
      } else {
        c.beginPath();
        c.arc(x, y, NOTE_RADIUS * 0.55, 0, Math.PI * 2);
        c.fill();
      }

      c.strokeStyle = 'rgba(255,255,255,0.5)';
      c.lineWidth = 2;
      if (note.lane === Lane.Air) {
        this.strokeDiamond(c, x, y, NOTE_RADIUS);
      } else {
        c.beginPath();
        c.arc(x, y, NOTE_RADIUS, 0, Math.PI * 2);
        c.stroke();
      }

      c.restore();
    }
  }

  private drawDiamond(c: CanvasRenderingContext2D, x: number, y: number, r: number) {
    c.beginPath();
    c.moveTo(x, y - r);
    c.lineTo(x + r, y);
    c.lineTo(x, y + r);
    c.lineTo(x - r, y);
    c.closePath();
    c.fill();
  }

  private strokeDiamond(c: CanvasRenderingContext2D, x: number, y: number, r: number) {
    c.beginPath();
    c.moveTo(x, y - r);
    c.lineTo(x + r, y);
    c.lineTo(x, y + r);
    c.lineTo(x - r, y);
    c.closePath();
    c.stroke();
  }

  private drawCharacter(c: CanvasRenderingContext2D, w: number, h: number) {
    const cx = w * HIT_X;
    let baseY = h * GROUND_RATIO + NOTE_RADIUS + 8;
    const bob = Math.sin(this.charFrame * Math.PI / 2) * 4;
    let jumpOff = 0;

    if (this.charAction === 'airHit') {
      jumpOff = -60 * (this.charActionTimer / 150);
    }

    baseY += bob + jumpOff;
    const s = 1.0;

    c.save();
    c.translate(cx, baseY);
    c.scale(s, s);

    c.fillStyle = COLORS.ground;
    c.beginPath();
    c.ellipse(0, -40, 16, 18, 0, 0, Math.PI * 2);
    c.fill();

    c.fillStyle = '#ffffff';
    c.beginPath(); c.arc(-5, -43, 4, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.arc(7, -43, 4, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#1a0a3e';
    c.beginPath(); c.arc(-4, -42, 2, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.arc(8, -42, 2, 0, Math.PI * 2); c.fill();

    c.strokeStyle = COLORS.ground;
    c.lineWidth = 2;
    c.beginPath();
    c.arc(2, -35, 5, 0.1, Math.PI - 0.1);
    c.stroke();

    c.fillStyle = COLORS.accent;
    c.fillRect(-10, -22, 20, 22);

    const legPhase = this.charFrame * Math.PI / 2;
    c.strokeStyle = COLORS.accent;
    c.lineWidth = 5;
    c.lineCap = 'round';
    c.beginPath();
    c.moveTo(-5, 0);
    c.lineTo(-5 + Math.sin(legPhase) * 8, 14);
    c.stroke();
    c.beginPath();
    c.moveTo(5, 0);
    c.lineTo(5 + Math.sin(legPhase + Math.PI) * 8, 14);
    c.stroke();

    if (this.charAction === 'groundHit') {
      c.strokeStyle = COLORS.perfect;
      c.lineWidth = 4;
      c.beginPath();
      c.moveTo(10, -18);
      c.lineTo(30 + (150 - this.charActionTimer) * 0.2, -25);
      c.stroke();
      c.fillStyle = COLORS.perfect;
      c.beginPath();
      c.arc(30 + (150 - this.charActionTimer) * 0.2, -25, 5, 0, Math.PI * 2);
      c.fill();
    }

    c.restore();
  }

  private drawParticles(c: CanvasRenderingContext2D) {
    for (const p of this.particles) {
      const alpha = p.life / p.maxLife;
      c.globalAlpha = alpha;
      c.fillStyle = p.color;
      c.beginPath();
      c.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
      c.fill();
    }
    c.globalAlpha = 1;
  }

  private drawJudgments(c: CanvasRenderingContext2D) {
    for (const j of this.judgments) {
      const alpha = Math.min(1, j.life / 200);
      c.globalAlpha = alpha;
      c.font = `bold ${Math.round(22 * j.scale)}px system-ui, sans-serif`;
      c.fillStyle = j.color;
      c.textAlign = 'center';
      c.shadowColor = j.color;
      c.shadowBlur = 10;
      c.fillText(j.text, j.x, j.y);
      c.shadowBlur = 0;
    }
    c.globalAlpha = 1;
  }

  private drawHUD(c: CanvasRenderingContext2D, w: number, h: number) {
    c.font = 'bold 16px system-ui, sans-serif';
    c.textAlign = 'left';
    c.fillStyle = COLORS.white;
    c.fillText(this.beatmap.title, 20, 30);
    c.font = '13px system-ui, sans-serif';
    c.fillStyle = 'rgba(255,255,255,0.6)';
    c.fillText(this.beatmap.artist, 20, 48);

    c.textAlign = 'right';
    c.font = 'bold 28px system-ui, sans-serif';
    c.fillStyle = COLORS.white;
    c.fillText(this.score.toLocaleString(), w - 20, 38);

    if (this.combo > 2) {
      c.textAlign = 'center';
      const comboScale = 1 + Math.min(this.combo * 0.003, 0.3);
      c.font = `bold ${Math.round(48 * comboScale)}px system-ui, sans-serif`;
      c.fillStyle = COLORS.perfect;
      c.globalAlpha = 0.9;
      c.fillText(`${this.combo}x`, w / 2, h * 0.25);
      c.font = '14px system-ui, sans-serif';
      c.fillStyle = 'rgba(255,255,255,0.6)';
      c.fillText('COMBO', w / 2, h * 0.25 + 20);
      c.globalAlpha = 1;
    }

    const total = this.perfect + this.great + this.good + this.miss;
    const acc = total > 0
      ? ((this.perfect * 300 + this.great * 200 + this.good * 100) / (total * 300)) * 100
      : 100;
    c.textAlign = 'right';
    c.font = '14px system-ui, sans-serif';
    c.fillStyle = 'rgba(255,255,255,0.7)';
    c.fillText(`${acc.toFixed(1)}%`, w - 20, 58);

    const barW = w * 0.3;
    const barH = 6;
    const barX = (w - barW) / 2;
    const barY = h - 25;
    c.fillStyle = 'rgba(255,255,255,0.1)';
    c.fillRect(barX, barY, barW, barH);
    const progress = this.player.duration > 0 ? this.player.currentTime / this.player.duration : 0;
    const progGrad = c.createLinearGradient(barX, 0, barX + barW, 0);
    progGrad.addColorStop(0, COLORS.air);
    progGrad.addColorStop(1, COLORS.accent);
    c.fillStyle = progGrad;
    c.fillRect(barX, barY, barW * progress, barH);

    const hpW = 150;
    const hpH = 8;
    const hpX = 20;
    const hpY = h - 25;
    c.fillStyle = 'rgba(255,255,255,0.1)';
    c.fillRect(hpX, hpY, hpW, hpH);
    const hpColor = this.health > 50 ? COLORS.great : this.health > 25 ? COLORS.perfect : COLORS.miss;
    c.fillStyle = hpColor;
    c.fillRect(hpX, hpY, hpW * (this.health / 100), hpH);

    c.font = '12px system-ui, sans-serif';
    c.fillStyle = 'rgba(255,255,255,0.4)';
    c.textAlign = 'left';
    c.fillText('[D/J] Boden  [F/K] Luft  [ESC] Pause', 20, h - 40);
  }

  private drawCountdown(c: CanvasRenderingContext2D, w: number, h: number) {
    c.fillStyle = 'rgba(0,0,0,0.5)';
    c.fillRect(0, 0, w, h);
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    if (this.countdownValue > 0) {
      c.font = `bold 96px system-ui, sans-serif`;
      c.fillStyle = COLORS.perfect;
      c.shadowColor = COLORS.perfect;
      c.shadowBlur = 30;
      c.fillText(this.countdownValue.toString(), w / 2, h / 2);
      c.shadowBlur = 0;
    } else {
      c.font = `bold 64px system-ui, sans-serif`;
      c.fillStyle = COLORS.great;
      c.shadowColor = COLORS.great;
      c.shadowBlur = 30;
      c.fillText('LOS!', w / 2, h / 2);
      c.shadowBlur = 0;
    }
    c.textBaseline = 'alphabetic';
  }

  private drawPauseOverlay(c: CanvasRenderingContext2D, w: number, h: number) {
    c.fillStyle = 'rgba(0,0,0,0.6)';
    c.fillRect(0, 0, w, h);
    c.textAlign = 'center';
    c.font = 'bold 48px system-ui, sans-serif';
    c.fillStyle = COLORS.white;
    c.fillText('PAUSE', w / 2, h / 2 - 20);
    c.font = '20px system-ui, sans-serif';
    c.fillStyle = 'rgba(255,255,255,0.6)';
    c.fillText('Drücke ESC zum Fortsetzen', w / 2, h / 2 + 20);
  }
}
