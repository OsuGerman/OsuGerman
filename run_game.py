#!/usr/bin/env python3
"""Rhythm Dash — Muse-Dash-inspired rhythm game with a built-in map editor."""
from __future__ import annotations

import os
import sys
import json
import glob
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if sys.platform == 'win32':
    pass
elif not os.environ.get('SDL_AUDIODRIVER'):
    try:
        import subprocess
        r = subprocess.run(['aplay', '-l'], capture_output=True, timeout=2)
        if r.returncode != 0:
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
    except Exception:
        os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from game.config import WIDTH, HEIGHT, FPS, TITLE, ACCENT, AIR_COL, WHITE
from game.audio import init_audio, load_music, stop_music, generate_demo_wav, generate_demo_beatmap_notes
from game.beatmap import Beatmap
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
    need_regen = False
    if not os.path.exists(demo_map):
        need_regen = True
    else:
        try:
            with open(demo_map) as f:
                d = json.load(f)
            af = d.get('audio_file', '')
            if not os.path.exists(af):
                need_regen = True
        except Exception:
            need_regen = True

    if need_regen:
        if not os.path.exists(demo_wav):
            generate_demo_wav(demo_wav, bpm=99.4, duration_s=45)
        notes = generate_demo_beatmap_notes(bpm=99.4, duration_s=45)
        data = {
            'id': 'demo',
            'title': 'Demo Beat (99.4 BPM)',
            'artist': 'Rhythm Dash',
            'bpm': 99.4,
            'offset': 0,
            'difficulty': 4,
            'audio_file': os.path.abspath(demo_wav),
            'notes': notes,
        }
        with open(demo_map, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Demo erstellt: {demo_map}")


def load_map_list() -> list[dict]:
    maps = []
    for path in sorted(glob.glob(os.path.join(MAP_DIR, '*.json'))):
        try:
            with open(path) as f:
                d = json.load(f)
            af = d.get('audio_file', '')
            has_audio = os.path.exists(af)
            maps.append({
                'path': path,
                'id': d.get('id', ''),
                'title': d.get('title', '?'),
                'artist': d.get('artist', '?'),
                'bpm': d.get('bpm', 0),
                'difficulty': d.get('difficulty', 5),
                'note_count': len(d.get('notes', [])),
                'has_audio': has_audio,
            })
        except Exception:
            pass
    return maps


def point_in_rect(px: int, py: int, rx: int, ry: int, rw: int, rh: int) -> bool:
    return rx <= px <= rx + rw and ry <= py <= ry + rh


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    init_audio()

    ensure_dirs()
    ensure_demo()

    renderer = Renderer(screen)
    state = 'menu'
    menu_sel = 0
    select_sel = 0
    map_list: list[dict] = []
    game_state: GameState | None = None
    editor: Editor | None = None
    last_result: dict | None = None

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
        game_state = GameState(bm, renderer)
        state = 'game'

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        w, h = screen.get_size()
        keys_just = set()

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
                        game_state = GameState(bm, renderer)
                        state = 'game'
                        editor.test_play = False
                    else:
                        editor.test_play = False
                continue

            # --- Mouse clicks ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if state == 'menu':
                    for i in range(3):
                        bx = w // 2 - 120
                        by = h // 2 + i * 60 - 20
                        if point_in_rect(mx, my, bx, by, 240, 48):
                            menu_sel = i
                            if i == 0:
                                map_list = load_map_list()
                                select_sel = 0
                                state = 'select'
                            elif i == 1:
                                editor = Editor(screen)
                                state = 'editor'
                            break

                elif state == 'select':
                    y_start = 90
                    for i, m in enumerate(map_list):
                        cy = y_start + i * 75
                        if point_in_rect(mx, my, 30, cy, w - 60, 65):
                            if select_sel == i:
                                do_start_game(m)
                            else:
                                select_sel = i
                            break

                elif state == 'result' and last_result:
                    if point_in_rect(mx, my, w // 2 - 200, 480, 180, 48):
                        for m in map_list:
                            if m['title'] == last_result.get('title', ''):
                                do_start_game(m)
                                break
                    elif point_in_rect(mx, my, w // 2 + 20, 480, 180, 48):
                        state = 'select'
                        map_list = load_map_list()

            # --- Keyboard ---
            if event.type == pygame.KEYDOWN:
                keys_just.add(event.key)

                if state == 'menu':
                    if event.key in (pygame.K_UP, pygame.K_f, pygame.K_k):
                        menu_sel = (menu_sel - 1) % 3
                    elif event.key in (pygame.K_DOWN, pygame.K_d, pygame.K_j):
                        menu_sel = (menu_sel + 1) % 3
                    elif event.key == pygame.K_RETURN:
                        if menu_sel == 0:
                            map_list = load_map_list()
                            select_sel = 0
                            state = 'select'
                        elif menu_sel == 1:
                            editor = Editor(screen)
                            state = 'editor'
                        elif menu_sel == 2:
                            pass

                elif state == 'select':
                    if event.key == pygame.K_ESCAPE:
                        state = 'menu'
                    elif event.key in (pygame.K_UP, pygame.K_f, pygame.K_k):
                        if map_list:
                            select_sel = (select_sel - 1) % len(map_list)
                    elif event.key in (pygame.K_DOWN, pygame.K_d, pygame.K_j):
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
                            path = map_list[select_sel]['path']
                            os.remove(path)
                            map_list = load_map_list()
                            select_sel = min(select_sel, max(0, len(map_list) - 1))

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
                        if last_result and map_list:
                            title = last_result.get('title', '')
                            for m in map_list:
                                if m['title'] == title:
                                    do_start_game(m)
                                    break

        if state == 'game' and game_state:
            if not game_state.paused:
                game_state.update(dt, keys_just)
                renderer.update(dt)
            if game_state.finished:
                last_result = game_state.result
                game_state = None
                state = 'result'

        if state == 'editor' and editor:
            editor.update()

        if state == 'menu':
            renderer.draw_menu()
            sel_y = h // 2 + menu_sel * 60 - 20
            pygame.draw.rect(screen, WHITE, (w // 2 - 122, sel_y - 2, 244, 52), 2, border_radius=14)

        elif state == 'select':
            renderer.draw_select(map_list, select_sel)

        elif state == 'game' and game_state:
            game_state.render()

        elif state == 'editor' and editor:
            editor.render()

        elif state == 'result' and last_result:
            renderer.draw_result(last_result)

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("\nFehler! Drücke ENTER zum Schließen...")
