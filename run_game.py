#!/usr/bin/env python3
"""Rhythm Dash — 2D Rhythm-Action Game."""
from __future__ import annotations
import os, sys, json, shutil, traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
if sys.platform != 'win32' and not os.environ.get('SDL_AUDIODRIVER'):
    try:
        import subprocess
        if subprocess.run(['aplay','-l'], capture_output=True, timeout=2).returncode != 0:
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
    except Exception:
        os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from game.config import Settings
from game.audio import (init_audio, load_music, stop_music, play_music,
                        pause_music, unpause_music, set_music_volume, set_sfx_volume,
                        generate_demo_wav, generate_demo_beatmap_notes, play_sfx)
from game.beatmap import Beatmap
from game.gameplay_mgr import GameplayManager
from game.game_renderer import GameRenderer
from game.chart import load_chart, chart_from_legacy
from game.editor import Editor
from game.ui_screens import (SplashScreen, MainMenuScreen, SongSelectScreen, SettingsScreen,
                             ResultsScreen, ScreenResult, load_all_maps)
from game.ui_sounds import init_ui_sounds

MAP_DIR, SONG_DIR = 'maps', 'songs'


class App:
    def __init__(self):
        self.settings = Settings()
        self.screen: pygame.Surface = None
        self.clock = pygame.time.Clock()
        self.running = False
        self.fullscreen = False
        self.current_screen = None
        self.game_renderer: GameRenderer | None = None
        self.game_mgr: GameplayManager | None = None
        self.editor: Editor | None = None
        self._game_active = False
        self._editor_active = False
        self._keys_just: set[int] = set()
        self._maps: list[dict] = []
        self._last_title = ''

    def init(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        pygame.display.set_caption("Rhythm Dash")
        init_audio()
        init_ui_sounds()
        set_music_volume(self.settings.music_volume)
        set_sfx_volume(self.settings.sfx_volume)
        os.makedirs(MAP_DIR, exist_ok=True)
        os.makedirs(SONG_DIR, exist_ok=True)
        self._ensure_demo()
        self.current_screen = SplashScreen(self.screen)

    def _ensure_demo(self):
        dm, dw = os.path.join(MAP_DIR,'demo.json'), os.path.join(SONG_DIR,'demo_beat.wav')
        need = not os.path.exists(dm)
        if not need:
            try:
                with open(dm) as f:
                    if not os.path.exists(json.load(f).get('audio_file','')): need = True
            except: need = True
        if need:
            if not os.path.exists(dw): generate_demo_wav(dw, 99.4, 45)
            notes = generate_demo_beatmap_notes(99.4, 45)
            json.dump({'id':'demo','title':'Demo Beat (99.4 BPM)','artist':'Rhythm Dash',
                       'bpm':99.4,'offset':0,'difficulty':4,'audio_file':os.path.abspath(dw),
                       'notes':notes}, open(dm,'w'), indent=2)

    # ── Navigation ──
    def go_menu(self):
        self._game_active = self._editor_active = False
        self.game_mgr = self.editor = None
        self.current_screen = MainMenuScreen(self.screen)

    def go_select(self):
        self._game_active = self._editor_active = False
        self._maps = load_all_maps()
        self.current_screen = SongSelectScreen(self.screen, self._maps)

    def go_settings(self):
        self.current_screen = SettingsScreen(self.screen, self.settings)

    def go_results(self, r: dict):
        self._game_active = False
        self.game_mgr = None
        self._last_title = r.get('song_title', r.get('title', ''))
        self.current_screen = ResultsScreen(self.screen, r)

    def go_editor(self, path=None):
        self._editor_active = True
        self._game_active = False
        self.current_screen = None
        bm = Beatmap(path) if path else Beatmap()
        self.editor = Editor(self.screen, bm)
        if bm.audio_file and os.path.exists(bm.audio_file):
            try:
                load_music(bm.audio_file)
                self.editor.audio_loaded = True
                self.editor.audio_path = bm.audio_file
                import soundfile as sf
                self.editor.music_len_ms = sf.info(bm.audio_file).duration * 1000
            except: pass

    def start_game(self, map_info: dict):
        path = map_info['path']
        try:
            chart = load_chart(path) if 'data/' in path else chart_from_legacy(path)
        except Exception as e:
            print(f"Chart error: {e}"); return

        # Find audio file — check multiple sources
        af = ''
        # 1. From map_info (set by load_all_maps)
        if map_info.get('audio_path'):
            af = map_info['audio_path']
        # 2. From the JSON file directly
        if not af:
            try:
                with open(path) as _f:
                    raw = json.load(_f)
                af = raw.get('audio_file', raw.get('audioFile', ''))
            except: pass
        # 3. From song metadata if it's a data/ chart
        if not af and map_info.get('legacy_path'):
            try:
                with open(map_info['legacy_path']) as _f:
                    raw = json.load(_f)
                af = raw.get('audioFile', raw.get('audio_file', ''))
            except: pass
        # 4. Legacy Beatmap fallback
        if not af:
            try:
                bm = Beatmap(path)
                af = bm.audio_file
            except: pass

        if not os.path.isabs(af):
            af = os.path.join(os.getcwd(), af)
        if not af or not os.path.exists(af):
            print(f"Audio not found: {af}"); return

        # Get BPM from chart or JSON
        bpm = 120
        try:
            with open(path) as _f:
                raw = json.load(_f)
            bpm = raw.get('bpm', raw.get('_meta', {}).get('bpm', 120))
        except: pass
        set_music_volume(self.settings.music_volume)
        set_sfx_volume(self.settings.sfx_volume)
        gr = GameRenderer(self.screen)
        self.game_renderer = gr
        gm = GameplayManager(chart=chart, audio_path=af,
                             ground_keys=self.settings.ground_keys, air_keys=self.settings.air_keys,
                             music_volume=self.settings.music_volume, audio_offset=self.settings.audio_offset)
        gm.set_bpm(bpm)
        gm.set_note_speed(self.settings.note_speed)
        gm.set_renderer(gr)
        gm._reduce_flash = self.settings.reduce_flash
        gm.start()
        self.game_mgr = gm
        self._auto_retry_timer = 0
        self._game_active = True
        self._editor_active = False
        self.current_screen = None

    def retry_game(self, title=''):
        t = title or self._last_title
        self._maps = load_all_maps()
        for m in self._maps:
            if m['title'] == t:
                self.start_game(m); return

    def do_import(self):
        try:
            import tkinter as tk; from tkinter import filedialog
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            path = filedialog.askopenfilename(title="Audio importieren",
                filetypes=[("Audio","*.mp3 *.wav *.ogg *.flac *.m4a"),("Alle","*.*")])
            root.destroy()
            if not path: return
            fname = os.path.basename(path)
            dest = os.path.join(SONG_DIR, fname)
            if not os.path.exists(dest): shutil.copy2(path, dest)
            dest = os.path.abspath(dest)
            from game.mapper import generate_chart
            try:
                data = generate_chart(dest, difficulty=5, diff_id='normal')
                data['audio_file'] = dest
                mp = os.path.join(MAP_DIR, f"{data['songId']}_auto.json")
                json.dump(data, open(mp,'w'), indent=2)
                bm = Beatmap(mp)
            except:
                bm = Beatmap(); bm.id = f"map_{pygame.time.get_ticks()}"
                bm.title = os.path.splitext(fname)[0]; bm.audio_file = dest; bm.bpm = 120
            self._editor_active = True; self._game_active = False; self.current_screen = None
            self.editor = Editor(self.screen, bm)
            try:
                load_music(dest); self.editor.audio_loaded = True; self.editor.audio_path = dest
                import soundfile as sf; self.editor.music_len_ms = sf.info(dest).duration * 1000
            except: pass
        except Exception as e: print(f"Import error: {e}")

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN) if self.fullscreen \
            else pygame.display.set_mode((1280,720), pygame.RESIZABLE)
        if self.game_renderer:
            self.game_renderer = GameRenderer(self.screen)
            if self.game_mgr: self.game_mgr.set_renderer(self.game_renderer)

    # ── Main Loop ──
    def run(self):
        self.running = True
        while self.running:
            fps = self.settings.fps_limit
            dt = self.clock.tick(fps if fps > 0 else 0) / 1000.0
            if dt > 0.1: dt = 0.016
            self._keys_just.clear()
            mouse = pygame.mouse.get_pos()
            frame_events = []

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: self.running = False; break
                if ev.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE); continue
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_F11:
                    self.toggle_fullscreen(); continue

                if self._editor_active and self.editor:
                    self.editor.handle_event(ev)
                    if self.editor.done: self.editor = None; self._editor_active = False; self.go_menu()
                    elif self.editor.test_play:
                        bm = self.editor.bm
                        if bm.audio_file and os.path.exists(bm.audio_file):
                            # Build chart from editor notes
                            from game.types import ChartData, GameplayObjectData, ObjectType, Lane, ActionType
                            objs = [GameplayObjectData(id=f"n_{n.time}",
                                type=ObjectType.AIR_ENEMY if n.lane==1 else ObjectType.GROUND_ENEMY,
                                lane=Lane.AIR if n.lane==1 else Lane.GROUND,
                                hit_time=n.time, spawn_time=n.time-1200, action_type=ActionType.TAP)
                                for n in bm.notes]
                            chart = ChartData(song_id=bm.id, difficulty_id='test', objects=objs)
                            load_music(bm.audio_file); set_music_volume(self.settings.music_volume)
                            gr = GameRenderer(self.screen); self.game_renderer = gr
                            gm = GameplayManager(chart=chart, audio_path=bm.audio_file,
                                ground_keys=self.settings.ground_keys, air_keys=self.settings.air_keys,
                                audio_offset=self.settings.audio_offset)
                            gm.set_bpm(bm.bpm); gm.set_note_speed(self.settings.note_speed)
                            gm.set_renderer(gr); gm.start()
                            self.game_mgr = gm; self._game_active = True; self._editor_active = False
                        self.editor.test_play = False
                    continue

                if self._game_active and self.game_mgr:
                    if ev.type == pygame.KEYDOWN:
                        gm = self.game_mgr
                        gm.capture_key(ev.key)
                        if ev.key == pygame.K_F3:
                            self.settings.debug_overlay = not self.settings.debug_overlay
                            continue
                        if ev.key == pygame.K_ESCAPE:
                            if gm.failed: self.go_select()
                            else: gm.toggle_pause()
                        elif ev.key == pygame.K_q and gm.paused: stop_music(); self.go_select()
                        elif ev.key == pygame.K_r and (gm.failed or gm.paused):
                            stop_music(); self.retry_game()
                        elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS):
                            self.settings.music_volume = min(1, self.settings.music_volume+0.05)
                            set_music_volume(self.settings.music_volume)
                        elif ev.key == pygame.K_MINUS:
                            self.settings.music_volume = max(0, self.settings.music_volume-0.05)
                            set_music_volume(self.settings.music_volume)
                    continue
                frame_events.append(ev)

            # Update + Render
            if self._game_active and self.game_mgr:
                gm = self.game_mgr
                if not gm.paused and not gm.failed:
                    gm.update(dt)
                if self.game_renderer: self.game_renderer.update(dt)
                if gm.finished:
                    self.show_result_data(gm.result)
                elif gm.failed and self.settings.auto_retry:
                    gm._auto_retry = True
                    self._auto_retry_timer = getattr(self, '_auto_retry_timer', 0) + dt
                    if self._auto_retry_timer > 1.5:
                        self._auto_retry_timer = 0
                        stop_music(); self.retry_game()
                    elif self.game_renderer:
                        self.game_renderer.render_frame(gm)
                elif self.game_renderer:
                    self.game_renderer.render_frame(gm)
                    if self.settings.debug_overlay:
                        fps = self.clock.get_fps()
                        self.game_renderer.render_debug(gm, fps)
            elif self._editor_active and self.editor:
                self.editor.update(); self.editor.render()
            elif self.current_screen:
                result = self.current_screen.update(dt, frame_events, mouse)
                if result.action: self._handle(result)

            pygame.display.flip()
        pygame.quit()

    def show_result_data(self, result):
        if not result: self.go_select(); return
        self.go_results({
            'score':result.score, 'max_combo':result.max_combo, 'accuracy':result.accuracy,
            'perfect':result.perfect, 'great':result.great, 'good':result.good, 'miss':result.miss,
            'grade':result.grade, 'song_title':result.song_title, 'avg_error':result.avg_error,
            'unstable_rate':result.unstable_rate, 'early':result.early_count, 'late':result.late_count,
            'timing_errors':result.timing_errors, 'cleared':result.cleared,
        })

    def _handle(self, r: ScreenResult):
        a = r.action
        if a == 'done': self.go_menu()
        elif a == 'play': self.go_select()
        elif a == 'editor': self.go_editor()
        elif a == 'import': self.do_import()
        elif a == 'settings': self.go_settings()
        elif a == 'back': self.go_menu()
        elif a == 'fullscreen': self.toggle_fullscreen()
        elif a == 'start' and self._maps:
            idx = r.data.get('index', 0)
            if 0 <= idx < len(self._maps): self.start_game(self._maps[idx])
        elif a == 'edit' and self._maps:
            idx = r.data.get('index', 0)
            if 0 <= idx < len(self._maps): self.go_editor(self._maps[idx]['path'])
        elif a == 'delete' and self._maps:
            idx = r.data.get('index', 0)
            if 0 <= idx < len(self._maps):
                try: os.remove(self._maps[idx]['path'])
                except: pass
            self.go_select()
        elif a == 'retry': self.retry_game()


def main():
    app = App()
    app.init()
    app.run()

if __name__ == '__main__':
    try: main()
    except Exception: traceback.print_exc(); input("\nFehler! ENTER zum Schließen...")
