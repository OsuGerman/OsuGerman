#!/usr/bin/env python3
"""Rhythm Dash — osu!-inspired rhythm game built on a Drawable framework."""
from __future__ import annotations
import os, sys, json, shutil, traceback

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
from game.config import Settings
from game.audio import (init_audio, load_music, stop_music, set_music_volume,
                        generate_demo_wav, generate_demo_beatmap_notes)
from game.framework import Application
from game.screens import MenuScreen, SelectScreen, SettingsScreen, ResultScreen
from game.beatmap import Beatmap
from game.renderer import Renderer
from game.gameplay import GameState
from game.editor import Editor

MAP_DIR = 'maps'
SONG_DIR = 'songs'


class RhythmDash(Application):
    def __init__(self):
        super().__init__(1280, 720, "Rhythm Dash")
        self.settings = Settings()
        self.renderer: Renderer | None = None
        self.game_state: GameState | None = None
        self.editor: Editor | None = None
        self._game_active = False
        self._editor_active = False
        self._map_list: list[dict] = []

    def init(self):
        super().init()
        init_audio()
        set_music_volume(self.settings.music_volume)
        os.makedirs(MAP_DIR, exist_ok=True)
        os.makedirs(SONG_DIR, exist_ok=True)
        self._ensure_demo()
        self.renderer = Renderer(self.screen)
        self.go_menu()

    def _ensure_demo(self):
        demo_map = os.path.join(MAP_DIR, 'demo.json')
        demo_wav = os.path.join(SONG_DIR, 'demo_beat.wav')
        need = not os.path.exists(demo_map)
        if not need:
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

    # --- Screen navigation ---
    def go_menu(self):
        self._game_active = False
        self._editor_active = False
        self.game_state = None
        self.editor = None
        self.switch_screen(MenuScreen(self))

    def go_select(self):
        self._game_active = False
        self._editor_active = False
        s = SelectScreen(self)
        self.switch_screen(s)

    def go_settings(self):
        self.switch_screen(SettingsScreen(self))

    def go_editor(self, beatmap_path: str | None = None):
        self._editor_active = True
        self._game_active = False
        self.renderer = Renderer(self.screen)
        if beatmap_path:
            bm = Beatmap(beatmap_path)
            self.editor = Editor(self.screen, bm)
        else:
            self.editor = Editor(self.screen)
        self.current_screen = None

    def start_game(self, map_info: dict):
        bm = Beatmap(map_info['path'])
        af = bm.audio_file
        if not os.path.isabs(af):
            af = os.path.join(os.getcwd(), af)
        if not os.path.exists(af):
            print(f"Audio nicht gefunden: {af}")
            return
        load_music(af)
        set_music_volume(self.settings.music_volume)
        self.renderer = Renderer(self.screen)
        self.game_state = GameState(bm, self.renderer, settings=self.settings)
        self._game_active = True
        self._editor_active = False
        self.current_screen = None

    def retry_game(self, title: str):
        from game.screens import _load_map_list
        maps = _load_map_list()
        for m in maps:
            if m['title'] == title:
                self.start_game(m)
                return

    def show_result(self, result: dict):
        self._game_active = False
        self.game_state = None
        from game.screens import _load_map_list
        self._map_list = _load_map_list()
        self.switch_screen(ResultScreen(self, result))

    def do_import(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askopenfilename(
                title="Audio importieren",
                filetypes=[("Audio", "*.mp3 *.wav *.ogg *.flac *.m4a"), ("Alle", "*.*")])
            root.destroy()
            if not path:
                return
            fname = os.path.basename(path)
            dest = os.path.join(SONG_DIR, fname)
            if not os.path.exists(dest):
                shutil.copy2(path, dest)
            dest = os.path.abspath(dest)
            from game.beatgen import generate_beatmap
            try:
                print(f"Analysiere Audio: {dest}")
                map_data = generate_beatmap(dest, target_difficulty=5)
                map_path = os.path.join(MAP_DIR, f"{map_data['id']}.json")
                with open(map_path, 'w') as mf:
                    json.dump(map_data, mf, indent=2)
                print(f"Auto-Map erstellt: {len(map_data['notes'])} Noten, {map_data['bpm']} BPM")
                bm = Beatmap(map_path)
            except Exception as e:
                print(f"Auto-Map fehlgeschlagen: {e}, erstelle leere Map")
                name = os.path.splitext(fname)[0]
                bm = Beatmap()
                bm.id = f"map_{pygame.time.get_ticks()}"
                bm.title = name
                bm.audio_file = dest
                bm.bpm = 120
                bm.difficulty = 5
            self._editor_active = True
            self._game_active = False
            self.renderer = Renderer(self.screen)
            self.editor = Editor(self.screen, bm)
            self.current_screen = None
            try:
                load_music(dest)
                self.editor.audio_loaded = True
                self.editor.audio_path = dest
                import soundfile as sf
                self.editor.music_len_ms = sf.info(dest).duration * 1000
            except Exception:
                pass
        except Exception as e:
            print(f"Import error: {e}")

    # --- Override game loop ---
    def _process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                if self.renderer:
                    self.renderer = Renderer(self.screen)
                if self.game_state:
                    self.game_state.renderer = self.renderer
                if self.current_screen:
                    self.current_screen.width = self.width
                    self.current_screen.height = self.height
                    self.current_screen.on_resize(self.width, self.height)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
                if self.renderer:
                    self.renderer = Renderer(self.screen)
                if self.game_state:
                    self.game_state.renderer = self.renderer
                continue

            if self._editor_active and self.editor:
                self.editor.handle_event(event)
                if self.editor.done:
                    self.editor = None
                    self._editor_active = False
                    self.go_menu()
                elif self.editor.test_play:
                    bm = self.editor.bm
                    if bm.audio_file and os.path.exists(bm.audio_file):
                        load_music(bm.audio_file)
                        self.renderer = Renderer(self.screen)
                        self.game_state = GameState(bm, self.renderer, settings=self.settings)
                        self._game_active = True
                        self._editor_active = False
                    self.editor.test_play = False
                continue

            if self._game_active and self.game_state:
                if event.type == pygame.KEYDOWN:
                    self._keys_just.add(event.key)
                    gs = self.game_state
                    if event.key == pygame.K_ESCAPE:
                        if gs.failed:
                            self.go_select()
                        elif gs.paused:
                            gs.paused = False
                            unpause_music()
                        elif gs.started:
                            gs.paused = True
                            pause_music()
                    elif event.key == pygame.K_q and gs.paused:
                        stop_music()
                        self.go_select()
                    elif event.key == pygame.K_r and gs.failed:
                        stop_music()
                        self.retry_game(gs.beatmap.title)
                continue

            if event.type == pygame.KEYDOWN:
                if self.current_screen:
                    self.current_screen.on_key(event.key, event.mod)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging_slider = None
            elif event.type == pygame.MOUSEMOTION:
                if self._dragging_slider:
                    self._dragging_slider.handle_drag(event.pos[0])

    def _update(self, dt: float):
        self.mouse_pos = pygame.mouse.get_pos()

        if self._game_active and self.game_state:
            gs = self.game_state
            if not gs.paused and not gs.failed:
                gs.update(dt, self._keys_just)
                self.renderer.update(dt)
            if gs.finished:
                self.show_result(gs.result)
        elif self._editor_active and self.editor:
            self.editor.update()
        elif self.current_screen:
            self.current_screen.update(dt)
            new_hover = self.current_screen.hit_test(self.mouse_pos[0], self.mouse_pos[1])
            if new_hover != self._hovered:
                if self._hovered:
                    self._hovered.on_hover_exit()
                self._hovered = new_hover
                if self._hovered:
                    self._hovered.on_hover_enter()
            is_hovering = self._hovered is not None
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if is_hovering else pygame.SYSTEM_CURSOR_ARROW)

        self.cursor.update(self.mouse_pos[0], self.mouse_pos[1], dt)

    def _render(self):
        if self._game_active and self.game_state:
            self.game_state.render()
        elif self._editor_active and self.editor:
            self.editor.render()
        elif self.current_screen:
            self.current_screen.draw(self.screen)
        self.cursor.draw(self.screen)

    def run(self):
        self.running = True
        self._keys_just: set[int] = set()
        while self.running:
            fps_cap = self.settings.fps_limit
            dt = self.clock.tick(fps_cap if fps_cap > 0 else 0) / 1000.0
            if dt > 0.1:
                dt = 0.016
            self._keys_just.clear()
            self._process_input()
            self._update(dt)
            self._render()
            pygame.display.flip()
        pygame.quit()


def main():
    app = RhythmDash()
    app.init()
    app.run()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("\nFehler! Drücke ENTER zum Schließen...")
