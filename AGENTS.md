## Cursor Cloud specific instructions

This repository contains **Rhythm Dash**, a Muse Dash-inspired rhythm game built with:
- **Native desktop app**: Python 3 + Pygame (`run_game.py`)
- **Web version** (bonus): Vite + TypeScript (`index.html`, `src/`)

### Running the game

```bash
python3 run_game.py
```

If there's no audio device (common in cloud VMs), the game auto-detects this and sets `SDL_AUDIODRIVER=dummy`. You can also set it manually: `SDL_AUDIODRIVER=dummy python3 run_game.py`.

### Key directories

- `game/` — Python game modules (engine, renderer, editor, beatmap, audio)
- `maps/` — Beatmap JSON files (created by editor or `tools/gen_back2me_map.py`)
- `songs/` — Audio files (WAV/MP3/OGG)
- `src/` — TypeScript web version source
- `tools/` — Helper scripts (beatmap generation, YouTube download)

### Dependencies

- Python: `pip install pygame numpy soundfile` (see `requirements.txt`)
- Node (web version only): `npm install`

### Lint / Build

- Python: `python3 -c "import py_compile; py_compile.compile('run_game.py', doraise=True)"`
- TypeScript: `npx tsc --noEmit`
- Web build: `npx vite build`

### Gotchas

- `songs/` and `maps/` are runtime directories, created on first run if missing.
- The demo WAV (`songs/demo_beat.wav`) is generated programmatically on first launch — no need to distribute audio files.
- Beatmap JSON `audio_file` paths are absolute; when moving the project, regenerate maps or use the editor to re-import audio.
- YouTube download (`yt-dlp`) requires a JS runtime (deno) and may hit bot detection in cloud environments.
