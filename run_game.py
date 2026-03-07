#!/usr/bin/env python3
"""Rhythm Dash — Muse-Dash-inspired rhythm game with a built-in map editor."""
from __future__ import annotations

import os
import sys
import json
import glob
import shutil
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if sys.platform != 'win32' and not os.environ.get('SDL_AUDIODRIVER'):
    try:
        import subprocess
        r = subprocess.run(['aplay', '-l'], capture_output=True, timeout=2)
        if r.returncode != 0:
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
    except Exception:
        os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from game.config import *
from game.audio import (init_audio, load_music, stop_music, set_music_volume,
                        generate_demo_wav, generate_demo_beatmap_notes, play_sfx)
from game.beatmap import Beatmap, LANE_GROUND
from game.renderer import Renderer
from game.gameplay import GameState
from game.editor import Editor

MAP_DIR = 'maps'
SONG_DIR = 'songs'


def ensure_dirs():
    os.makedirs(MAP_DIR, exist_ok=True)
    os.makedirs(SONG_DIR, exist_ok=True)


def ensure_demo():
    demo_map = os.path.join(MAP_DIR, 'demo.json')
    demo_wav = os.path.join(SONG_DIR, 'demo_beat.wav')
    need = False
    if not os.path.exists(demo_map):
        need = True
    else:
        try:
            with open(demo_map) as f:
                d = json.load(f)
            if not os.path.exists(d.get('audio_file', '')):
                need = True
        except Exception:
            need = True
    if need:
        if not os.path.exists(demo_wav):
            generate_demo_wav(demo_wav, bpm=99.4, duration_s=45)
        notes = generate_demo_beatmap_notes(bpm=99.4, duration_s=45)
        data = {
            'id': 'demo', 'title': 'Demo Beat (99.4 BPM)', 'artist': 'Rhythm Dash',
            'bpm': 99.4, 'offset': 0, 'difficulty': 4,
            'audio_file': os.path.abspath(demo_wav), 'notes': notes,
        }
        with open(demo_map, 'w') as f:
            json.dump(data, f, indent=2)


def load_map_list() -> list[dict]:
    maps = []
    for path in sorted(glob.glob(os.path.join(MAP_DIR, '*.json'))):
        try:
            with open(path) as f:
                d = json.load(f)
            af = d.get('audio_file', '')
            maps.append({
                'path': path, 'id': d.get('id', ''),
                'title': d.get('title', '?'), 'artist': d.get('artist', '?'),
                'bpm': d.get('bpm', 0), 'difficulty': d.get('difficulty', 5),
                'note_count': len(d.get('notes', [])),
                'has_audio': os.path.exists(af),
            })
        except Exception:
            pass
    return maps


def import_audio_file() -> str | None:
    """Open file dialog, copy audio to songs/, return path or None."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title="Audio-Datei importieren",
            filetypes=[("Audio", "*.mp3 *.wav *.ogg *.flac *.m4a"), ("Alle", "*.*")]
        )
        root.destroy()
        if not path:
            return None
        fname = os.path.basename(path)
        dest = os.path.join(SONG_DIR, fname)
        if not os.path.exists(dest):
            shutil.copy2(path, dest)
        return os.path.abspath(dest)
    except Exception as e:
        print(f"Import-Fehler: {e}")
        return None


def create_beatmap_for_audio(audio_path: str) -> Beatmap:
    """Create a new empty beatmap for an audio file."""
    name = os.path.splitext(os.path.basename(audio_path))[0]
    map_id = f"map_{pygame.time.get_ticks()}"
    bm = Beatmap()
    bm.id = map_id
    bm.title = name
    bm.artist = 'Unbekannt'
    bm.bpm = 120
    bm.audio_file = audio_path
    bm.difficulty = 5
    return bm


def apply_settings(settings: Settings):
    set_music_volume(settings.music_volume)


def handle_slider_drag(settings: Settings, slider_name: str, mouse_x: int, rect: pygame.Rect):
    ratio = max(0, min(1, (mouse_x - rect.x) / rect.width))
    if slider_name == 'slider_music_volume':
        settings.music_volume = ratio
    elif slider_name == 'slider_sfx_volume':
        settings.sfx_volume = ratio
    elif slider_name == 'slider_audio_offset':
        settings.audio_offset = int(-200 + ratio * 400)
    elif slider_name == 'slider_note_speed':
        settings.note_speed = round(0.2 + ratio * 0.8, 2)
    elif slider_name == 'slider_bg_dim':
        settings.bg_dim = ratio
    apply_settings(settings)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    init_audio()

    ensure_dirs()
    ensure_demo()

    settings = Settings()
    apply_settings(settings)

    renderer = Renderer(screen)
    state = 'menu'
    menu_sel = 0
    select_sel = 0
    map_list: list[dict] = []
    game_state: GameState | None = None
    editor: Editor | None = None
    last_result: dict | None = None
    dragging_slider: str | None = None

    def do_start_game(map_info: dict):
        nonlocal game_state, state
        bm = Beatmap(map_info['path'])
        af = bm.audio_file
        if not os.path.isabs(af):
            af = os.path.join(os.getcwd(), af)
        if not os.path.exists(af):
            print(f"Audio nicht gefunden: {af}")
            return
        load_music(af)
        apply_settings(settings)
        game_state = GameState(bm, renderer, settings.note_speed)
        state = 'game'

    def do_import():
        nonlocal editor, state
        audio = import_audio_file()
        if audio:
            bm = create_beatmap_for_audio(audio)
            from game.audio import decodeAudio as _
        if audio:
            bm = create_beatmap_for_audio(audio)
            editor = Editor(screen, bm)
            state = 'editor'
            try:
                load_music(audio)
                editor.audio_loaded = True
                editor.audio_path = audio
                import soundfile as sf
                editor.music_len_ms = sf.info(audio).duration * 1000
            except Exception:
                pass

    def handle_action(action: str):
        nonlocal state, menu_sel, select_sel, map_list, editor, last_result, dragging_slider
        if action == 'play':
            map_list = load_map_list()
            select_sel = 0
            state = 'select'
        elif action == 'editor':
            editor = Editor(screen)
            state = 'editor'
        elif action == 'import':
            do_import()
        elif action == 'settings':
            state = 'settings'
        elif action == 'back':
            state = 'menu'
        elif action == 'save_back':
            settings.save()
            state = 'menu'
        elif action == 'retry':
            if last_result and map_list:
                title = last_result.get('title', '')
                for m in map_list:
                    if m['title'] == title:
                        do_start_game(m)
                        break
        elif action.startswith('select_'):
            idx = int(action.split('_')[1])
            if select_sel == idx:
                if idx < len(map_list):
                    do_start_game(map_list[idx])
            else:
                select_sel = idx
        elif action.startswith('slider_'):
            dragging_slider = action

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        mouse = pygame.mouse.get_pos()
        w, h = screen.get_size()
        keys_just: set[int] = set()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                renderer = Renderer(screen)
                if game_state:
                    game_state.renderer = renderer

            if state == 'editor' and editor:
                editor.handle_event(event)
                if editor.done:
                    editor = None
                    state = 'menu'
                    continue
                if editor.test_play:
                    bm = editor.bm
                    if bm.audio_file and os.path.exists(bm.audio_file):
                        load_music(bm.audio_file)
                        game_state = GameState(bm, renderer, settings.note_speed)
                        state = 'game'
                    editor.test_play = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, action in renderer.btn_rects:
                    if rect.collidepoint(event.pos):
                        handle_action(action)
                        break

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_slider = None

            if event.type == pygame.MOUSEMOTION and dragging_slider:
                for rect, action in renderer.btn_rects:
                    if action == dragging_slider:
                        handle_slider_drag(settings, dragging_slider, event.pos[0], rect)
                        break

            if event.type == pygame.KEYDOWN:
                keys_just.add(event.key)

                if state == 'menu':
                    if event.key in (pygame.K_UP,):
                        menu_sel = (menu_sel - 1) % 4
                    elif event.key in (pygame.K_DOWN,):
                        menu_sel = (menu_sel + 1) % 4
                    elif event.key == pygame.K_RETURN:
                        ['play', 'editor', 'import', 'settings'][menu_sel]
                        handle_action(['play', 'editor', 'import', 'settings'][menu_sel])

                elif state == 'select':
                    if event.key == pygame.K_ESCAPE:
                        state = 'menu'
                    elif event.key == pygame.K_UP:
                        if map_list:
                            select_sel = (select_sel - 1) % len(map_list)
                    elif event.key == pygame.K_DOWN:
                        if map_list:
                            select_sel = (select_sel + 1) % len(map_list)
                    elif event.key == pygame.K_RETURN:
                        if map_list:
                            do_start_game(map_list[select_sel])
                    elif event.key == pygame.K_e:
                        if map_list:
                            bm = Beatmap(map_list[select_sel]['path'])
                            editor = Editor(screen, bm)
                            state = 'editor'
                    elif event.key == pygame.K_DELETE:
                        if map_list:
                            os.remove(map_list[select_sel]['path'])
                            map_list = load_map_list()
                            select_sel = min(select_sel, max(0, len(map_list) - 1))
                    elif event.key == pygame.K_i:
                        do_import()

                elif state == 'settings':
                    if event.key == pygame.K_ESCAPE:
                        settings.save()
                        state = 'menu'

                elif state == 'game' and game_state:
                    if event.key == pygame.K_ESCAPE:
                        if game_state.paused:
                            game_state.paused = False
                            from game.audio import unpause_music
                            unpause_music()
                        elif game_state.started:
                            game_state.paused = True
                            from game.audio import pause_music
                            pause_music()
                    elif event.key == pygame.K_q and game_state.paused:
                        stop_music()
                        game_state = None
                        state = 'select'
                        map_list = load_map_list()

                elif state == 'result':
                    if event.key == pygame.K_ESCAPE:
                        state = 'select'
                        map_list = load_map_list()
                    elif event.key == pygame.K_r:
                        handle_action('retry')

        # --- Cursor ---
        hovering = False
        if state != 'game':
            for rect, _ in renderer.btn_rects:
                if rect.collidepoint(mouse):
                    hovering = True
                    break
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hovering else pygame.SYSTEM_CURSOR_ARROW)

        # --- Update ---
        if state == 'game' and game_state:
            if not game_state.paused:
                game_state.update(dt, keys_just)
                renderer.update(dt)
            if game_state.finished:
                last_result = game_state.result
                game_state = None
                state = 'result'
        elif state == 'editor' and editor:
            editor.update()

        # --- Render ---
        if state == 'menu':
            renderer.draw_menu(mouse, menu_sel)
        elif state == 'select':
            renderer.draw_select(map_list, select_sel, mouse)
        elif state == 'settings':
            renderer.draw_settings(settings, mouse, dragging_slider)
        elif state == 'game' and game_state:
            game_state.render()
        elif state == 'editor' and editor:
            editor.render()
        elif state == 'result' and last_result:
            renderer.draw_result(last_result, mouse)

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("\nFehler! Drücke ENTER zum Schließen...")
