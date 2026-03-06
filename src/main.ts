import './style.css';
import { ScreenId, Beatmap, GameResult, COLORS, Lane } from './types';
import { getAudioContext, MusicPlayer, generateDemoAudio, generateDemoBeatmap, audioFromBase64 } from './audio';
import { initInput, clearFrame } from './input';
import { loadAllBeatmaps, saveBeatmap, deleteBeatmap, importBeatmap } from './storage';
import { GameScreen } from './game';
import { EditorScreen } from './editor';

const canvas = document.getElementById('game-canvas') as HTMLCanvasElement;
const overlay = document.getElementById('ui-overlay')!;
const ctx = canvas.getContext('2d')!;

let currentScreen: ScreenId = 'menu';
let gameScreen: GameScreen | null = null;
let editorScreen: EditorScreen | null = null;
let lastResult: GameResult | null = null;
let lastTime = 0;

const player = new MusicPlayer();

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();
initInput();

function showScreen(id: ScreenId) {
  currentScreen = id;
  overlay.innerHTML = '';
  overlay.className = `screen-${id}`;
  gameScreen = null;
  if (editorScreen) { editorScreen.destroy(); editorScreen = null; }

  switch (id) {
    case 'menu': showMenu(); break;
    case 'select': showSelect(); break;
    case 'editor': showEditor(); break;
    case 'result': showResult(); break;
  }
}

function showMenu() {
  overlay.innerHTML = `
    <div class="menu-container">
      <div class="menu-title-wrap">
        <h1 class="menu-title">Rhythm<span class="accent">Dash</span></h1>
        <p class="menu-sub">Dein Rhythmus. Dein Spiel.</p>
      </div>
      <div class="menu-buttons">
        <button class="btn btn-big btn-primary" id="btn-play">▶ Spielen</button>
        <button class="btn btn-big btn-accent" id="btn-editor">✎ Editor</button>
        <button class="btn btn-big btn-ghost" id="btn-import">📁 Map Importieren</button>
      </div>
      <div class="menu-footer">
        <p>[D/J] Boden &nbsp; [F/K] Luft &nbsp; Eigene Lieder im Editor laden!</p>
      </div>
    </div>
  `;
  document.getElementById('btn-play')!.onclick = () => {
    getAudioContext();
    showScreen('select');
  };
  document.getElementById('btn-editor')!.onclick = () => {
    getAudioContext();
    showScreen('editor');
  };
  document.getElementById('btn-import')!.onclick = () => importMapFromFile();
}

function showSelect() {
  const maps = loadAllBeatmaps();
  const hasDemo = maps.some(m => m.id === 'demo');

  overlay.innerHTML = `
    <div class="select-container">
      <div class="select-header">
        <button class="btn btn-sm" id="btn-back">← Zurück</button>
        <h2>Lied Auswählen</h2>
        ${!hasDemo ? `<button class="btn btn-sm btn-accent" id="btn-demo">+ Demo laden</button>` : ''}
      </div>
      <div class="select-list" id="song-list">
        ${maps.length === 0 && hasDemo === false ? `
          <div class="select-empty">
            <p>Keine Beatmaps vorhanden!</p>
            <p>Lade den <strong>Demo-Song</strong> oder erstelle eine Beatmap im <strong>Editor</strong>.</p>
          </div>
        ` : ''}
        ${maps.map(m => `
          <div class="select-card" data-id="${m.id}">
            <div class="select-card-info">
              <h3>${m.title}</h3>
              <p>${m.artist} — ${m.notes.length} Noten — BPM ${m.bpm}</p>
              <div class="select-diff">
                ${'★'.repeat(Math.min(m.difficulty, 10))}${'☆'.repeat(Math.max(0, 10 - m.difficulty))}
              </div>
            </div>
            <div class="select-card-actions">
              <button class="btn btn-primary btn-sm play-btn" data-id="${m.id}">▶ Play</button>
              <button class="btn btn-sm edit-btn" data-id="${m.id}">✎</button>
              <button class="btn btn-sm btn-danger del-btn" data-id="${m.id}">✕</button>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  document.getElementById('btn-back')!.onclick = () => showScreen('menu');

  if (!hasDemo) {
    document.getElementById('btn-demo')?.addEventListener('click', () => {
      const demoMap = generateDemoBeatmap();
      const audioBuffer = generateDemoAudio();
      const fullMap: Beatmap = {
        ...demoMap,
        notes: demoMap.notes.map(n => ({ time: n.time, lane: n.lane as Lane })),
      };
      saveBeatmap(fullMap);

      player.load(audioBuffer);
      showScreen('select');
    });
  }

  document.querySelectorAll('.play-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = (btn as HTMLElement).dataset.id!;
      const map = maps.find(m => m.id === id);
      if (!map) return;
      await startGame(map);
    });
  });

  document.querySelectorAll('.edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = (btn as HTMLElement).dataset.id!;
      const map = maps.find(m => m.id === id);
      if (!map) return;
      showEditorWithMap(map);
    });
  });

  document.querySelectorAll('.del-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = (btn as HTMLElement).dataset.id!;
      if (confirm('Beatmap wirklich löschen?')) {
        deleteBeatmap(id);
        showScreen('select');
      }
    });
  });
}

async function startGame(map: Beatmap) {
  overlay.innerHTML = '<div class="loading">Lade...</div>';
  try {
    if (map.id === 'demo' && !map.audioBase64) {
      const buf = generateDemoAudio();
      player.load(buf);
    } else if (map.audioBase64) {
      const buf = await audioFromBase64(map.audioBase64);
      player.load(buf);
    } else {
      alert('Keine Audio-Daten für diese Beatmap! Bitte im Editor ein Lied importieren.');
      showScreen('select');
      return;
    }
  } catch (e) {
    alert('Audio konnte nicht geladen werden: ' + e);
    showScreen('select');
    return;
  }

  overlay.innerHTML = '';
  currentScreen = 'game';
  gameScreen = new GameScreen(canvas, player, map, (result) => {
    lastResult = result;
    gameScreen = null;
    showScreen('result');
  });
}

function showEditor(beatmap?: Beatmap) {
  currentScreen = 'editor';
  overlay.innerHTML = '';
  editorScreen = new EditorScreen(overlay, canvas, player, {
    onSave: () => {
      alert('Beatmap gespeichert!');
    },
    onBack: () => {
      editorScreen = null;
      showScreen('menu');
    },
    onTest: async (map) => {
      await startGame(map);
    },
    beatmap,
  });
}

function showEditorWithMap(map: Beatmap) {
  if (map.audioBase64) {
    audioFromBase64(map.audioBase64).then(buf => {
      player.load(buf);
      showEditor(map);
    });
  } else if (map.id === 'demo') {
    player.load(generateDemoAudio());
    showEditor(map);
  } else {
    showEditor(map);
  }
}

function showResult() {
  if (!lastResult) { showScreen('menu'); return; }
  const r = lastResult;
  const gradeColor = r.grade === 'S' ? COLORS.perfect : r.grade === 'A' ? COLORS.great : r.grade === 'B' ? COLORS.good : COLORS.miss;
  overlay.innerHTML = `
    <div class="result-container">
      <div class="result-grade" style="color:${gradeColor}">${r.grade}</div>
      <h2 class="result-title">${r.beatmapTitle}</h2>
      <div class="result-score">${r.score.toLocaleString()}</div>
      <div class="result-stats">
        <div class="stat"><span class="stat-val" style="color:${COLORS.perfect}">${r.perfect}</span><span class="stat-label">Perfect</span></div>
        <div class="stat"><span class="stat-val" style="color:${COLORS.great}">${r.great}</span><span class="stat-label">Great</span></div>
        <div class="stat"><span class="stat-val" style="color:${COLORS.good}">${r.good}</span><span class="stat-label">Good</span></div>
        <div class="stat"><span class="stat-val" style="color:${COLORS.miss}">${r.miss}</span><span class="stat-label">Miss</span></div>
      </div>
      <div class="result-extra">
        <p>Max Combo: <strong>${r.maxCombo}x</strong></p>
        <p>Genauigkeit: <strong>${r.accuracy}%</strong></p>
      </div>
      <div class="result-actions">
        <button class="btn btn-primary btn-big" id="btn-retry">↻ Nochmal</button>
        <button class="btn btn-big" id="btn-back-result">← Song-Auswahl</button>
      </div>
    </div>
  `;
  document.getElementById('btn-retry')!.onclick = () => {
    const maps = loadAllBeatmaps();
    const map = maps.find(m => m.title === r.beatmapTitle);
    if (map) startGame(map); else showScreen('select');
  };
  document.getElementById('btn-back-result')!.onclick = () => showScreen('select');
}

async function importMapFromFile() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async () => {
    const file = input.files?.[0];
    if (!file) return;
    const text = await file.text();
    const map = importBeatmap(text);
    if (map) {
      saveBeatmap(map);
      alert(`"${map.title}" importiert!`);
      showScreen('select');
    } else {
      alert('Ungültige Beatmap-Datei!');
    }
  };
  input.click();
}

function drawMenuBackground() {
  const w = canvas.width;
  const h = canvas.height;
  const t = performance.now() * 0.001;

  const grad = ctx.createLinearGradient(0, 0, w, h);
  grad.addColorStop(0, '#0a0018');
  grad.addColorStop(0.5, '#1a0a3e');
  grad.addColorStop(1, '#0f0524');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  for (let i = 0; i < 50; i++) {
    const x = ((i * 173.7 + t * (10 + i % 5 * 8)) % (w + 20)) - 10;
    const y = ((i * 127.3 + t * (2 + i % 3 * 3)) % (h + 20)) - 10;
    const s = 1 + (i % 4);
    ctx.globalAlpha = 0.1 + (i % 5) * 0.04;
    ctx.fillStyle = i % 7 === 0 ? COLORS.accent : i % 5 === 0 ? COLORS.air : '#ffffff';
    ctx.beginPath();
    ctx.arc(x, y, s, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;

  for (let i = 0; i < 5; i++) {
    const x = (t * (20 + i * 15) + i * 300) % (w + 200) - 100;
    const y = h * (0.3 + i * 0.12);
    ctx.strokeStyle = `rgba(224,64,251,${0.04 + i * 0.01})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.bezierCurveTo(x + 80, y - 20, x + 160, y + 20, x + 240, y);
    ctx.stroke();
  }
}

function mainLoop(timestamp: number) {
  const dt = lastTime ? timestamp - lastTime : 16;
  lastTime = timestamp;

  resize();

  if (currentScreen === 'game' && gameScreen) {
    gameScreen.update(dt);
    gameScreen.render();
  } else if (currentScreen !== 'editor') {
    drawMenuBackground();
  }

  clearFrame();
  requestAnimationFrame(mainLoop);
}

showScreen('menu');
requestAnimationFrame(mainLoop);
