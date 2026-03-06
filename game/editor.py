from __future__ import annotations
import os
import pygame
from .config import *
from .beatmap import Beatmap, Note, LANE_AIR, LANE_GROUND
from .audio import load_music, play_music, pause_music, stop_music, get_music_pos_ms, is_music_playing, play_sfx


class Editor:
    def __init__(self, screen: pygame.Surface, beatmap: Beatmap | None = None):
        self.screen = screen
        self.bm = beatmap or Beatmap()
        if not self.bm.id:
            self.bm.id = f"map_{pygame.time.get_ticks()}"
        self.notes = self.bm.clone_notes() if self.bm.notes else []
        self.playing = False
        self.scroll_x = 0.0
        self.zoom = 120.0
        self.selected = -1
        self.snap_div = 4
        self.audio_loaded = False
        self.audio_path = ''
        self.music_len_ms = 0.0
        self.done = False
        self.test_play = False
        self.save_path = ''

        self._font_sm = pygame.font.SysFont('sans-serif', 14)
        self._font_md = pygame.font.SysFont('sans-serif', 18, bold=True)
        self._font_xs = pygame.font.SysFont('sans-serif', 12)
        self._font_lg = pygame.font.SysFont('sans-serif', 24, bold=True)

        if self.bm.audio_file:
            full = self.bm.audio_file
            if not os.path.isabs(full):
                full = os.path.join(os.getcwd(), full)
            if os.path.exists(full):
                self._load_audio(full)

    def _load_audio(self, path: str):
        try:
            load_music(path)
            self.audio_loaded = True
            self.audio_path = path

            import soundfile as sf
            info = sf.info(path)
            self.music_len_ms = info.duration * 1000
        except Exception as e:
            print(f"Audio-Fehler: {e}")
            self.audio_loaded = False

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                stop_music()
                self.playing = False
                self.done = True
                return

            if k == pygame.K_SPACE:
                self._toggle_play()
            elif k == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                self._save()
            elif k in GROUND_KEYS:
                self._place_note(LANE_GROUND)
            elif k in AIR_KEYS:
                self._place_note(LANE_AIR)
            elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
                if self.selected >= 0 and self.selected < len(self.notes):
                    self.notes.pop(self.selected)
                    self.selected = -1
                elif self.notes:
                    self.notes.pop()
            elif k == pygame.K_i:
                self._import_audio()
            elif k == pygame.K_EQUALS or k == pygame.K_PLUS:
                self.bm.bpm = min(400, self.bm.bpm + 1)
            elif k == pygame.K_MINUS:
                self.bm.bpm = max(30, self.bm.bpm - 1)
            elif k == pygame.K_t:
                self._start_test()
            elif k == pygame.K_LEFT:
                if self.audio_loaded and not self.playing:
                    self.scroll_x = max(0, self.scroll_x - self.zoom * 2)
            elif k == pygame.K_RIGHT:
                if self.audio_loaded and not self.playing:
                    self.scroll_x += self.zoom * 2
            elif k == pygame.K_1:
                self.snap_div = 2
            elif k == pygame.K_2:
                self.snap_div = 4
            elif k == pygame.K_3:
                self.snap_div = 8
            elif k == pygame.K_4:
                self.snap_div = 16
            elif k == pygame.K_0:
                self.snap_div = 0

        elif event.type == pygame.MOUSEWHEEL:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                self.zoom = max(30, min(500, self.zoom + event.y * 10))
            else:
                self.scroll_x = max(0, self.scroll_x - event.y * self.zoom * 0.5)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

    def _toggle_play(self):
        if not self.audio_loaded:
            return
        if self.playing:
            pause_music()
            self.playing = False
        else:
            start_ms = self.scroll_x / self.zoom * 1000
            play_music(start_ms)
            self.playing = True

    def _place_note(self, lane: int):
        if self.playing:
            t = get_music_pos_ms()
        else:
            t = self.scroll_x / self.zoom * 1000

        if self.snap_div > 0:
            beat_ms = 60000 / self.bm.bpm
            div_ms = beat_ms / self.snap_div
            t = round((t - self.bm.offset) / div_ms) * div_ms + self.bm.offset

        if any(n.lane == lane and abs(n.time - t) < 20 for n in self.notes):
            return
        self.notes.append(Note(t, lane))
        self.notes.sort(key=lambda n: n.time)
        play_sfx('tick')

    def _handle_click(self, pos: tuple[int, int]):
        w, h = self.screen.get_size()
        mx, my = pos
        px_per_ms = self.zoom / 1000
        self.selected = -1
        for i, n in enumerate(self.notes):
            nx = int(n.time * px_per_ms - self.scroll_x + 80)
            ny = int(h * 0.3) if n.lane == LANE_AIR else int(h * 0.7)
            if abs(mx - nx) < 12 and abs(my - ny) < 12:
                self.selected = i
                break

    def _import_audio(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                title="Audio-Datei laden",
                filetypes=[
                    ("Audio", "*.mp3 *.wav *.ogg *.flac"),
                    ("Alle Dateien", "*.*"),
                ]
            )
            root.destroy()
            if path:
                self._load_audio(path)
                self.bm.audio_file = path
                name = os.path.splitext(os.path.basename(path))[0]
                if self.bm.title == 'Untitled' or self.bm.title == 'Neues Lied':
                    self.bm.title = name
        except Exception as e:
            print(f"Import-Fehler: {e}")

    def _save(self):
        self.bm.notes = [Note(n.time, n.lane) for n in self.notes]
        self.bm.audio_file = self.audio_path
        path = os.path.join('maps', f"{self.bm.id}.json")
        self.bm.save(path)
        self.save_path = path
        print(f"Gespeichert: {path}")

    def _start_test(self):
        if not self.audio_loaded:
            return
        self.bm.notes = [Note(n.time, n.lane) for n in self.notes]
        self.bm.audio_file = self.audio_path
        stop_music()
        self.playing = False
        self.test_play = True

    def update(self):
        if self.playing:
            pos = get_music_pos_ms()
            if pos >= 0:
                self.scroll_x = pos / 1000 * self.zoom - self.screen.get_width() * 0.3
                if self.scroll_x < 0:
                    self.scroll_x = 0
            if not is_music_playing():
                self.playing = False

    def render(self):
        scr = self.screen
        w, h = scr.get_size()
        scr.fill((13, 4, 32))

        mid_y = h // 2
        pygame.draw.line(scr, (40, 30, 60), (0, mid_y), (w, mid_y), 1)

        lane_air = pygame.Surface((w, 40), pygame.SRCALPHA)
        lane_air.fill((0, 212, 255, 8))
        scr.blit(lane_air, (0, int(h * 0.3) - 20))
        lane_gnd = pygame.Surface((w, 40), pygame.SRCALPHA)
        lane_gnd.fill((255, 77, 141, 8))
        scr.blit(lane_gnd, (0, int(h * 0.7) - 20))

        px_per_ms = self.zoom / 1000
        beat_ms = 60000 / self.bm.bpm

        start_ms = max(0, self.scroll_x / px_per_ms)
        end_ms = start_ms + w / px_per_ms
        first_beat = int((start_ms - self.bm.offset) / beat_ms) - 1
        last_beat = int((end_ms - self.bm.offset) / beat_ms) + 1

        for b in range(first_beat, last_beat + 1):
            t = self.bm.offset + b * beat_ms
            x = int(t * px_per_ms - self.scroll_x + 80)
            if x < 0 or x > w:
                continue
            is_measure = b >= 0 and b % 4 == 0
            col = (60, 50, 80) if is_measure else (30, 25, 50)
            lw = 2 if is_measure else 1
            pygame.draw.line(scr, col, (x, 0), (x, h), lw)

            if is_measure and b >= 0:
                num = self._font_xs.render(str(b // 4 + 1), True, (80, 70, 100))
                scr.blit(num, (x - num.get_width() // 2, h - 18))

            if self.snap_div > 1:
                for s in range(1, self.snap_div):
                    st = t + (beat_ms / self.snap_div) * s
                    sx = int(st * px_per_ms - self.scroll_x + 80)
                    if 0 <= sx <= w:
                        pygame.draw.line(scr, (22, 18, 35), (sx, 0), (sx, h), 1)

        for i, n in enumerate(self.notes):
            x = int(n.time * px_per_ms - self.scroll_x + 80)
            if x < -20 or x > w + 20:
                continue
            y = int(h * 0.3) if n.lane == LANE_AIR else int(h * 0.7)
            col = AIR_COL if n.lane == LANE_AIR else GROUND_COL
            sel = i == self.selected
            r = 10 if sel else 8

            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*col, 40), (r * 2, r * 2), r * 2)
            scr.blit(glow, (x - r * 2, y - r * 2))

            pygame.draw.circle(scr, col, (x, y), r)
            if sel:
                pygame.draw.circle(scr, WHITE, (x, y), r + 3, 2)

        if self.playing:
            pos = get_music_pos_ms()
            if pos >= 0:
                px = int(pos / 1000 * self.zoom - self.scroll_x + 80)
                pygame.draw.line(scr, PERFECT_COL, (px, 0), (px, h), 2)

        self._draw_header(w, h)
        self._draw_footer(w, h)

    def _draw_header(self, w: int, h: int):
        scr = self.screen
        header = pygame.Surface((w, 50), pygame.SRCALPHA)
        header.fill((13, 4, 32, 220))
        scr.blit(header, (0, 0))

        t = self._font_md.render(f"Editor: {self.bm.title}", True, WHITE)
        scr.blit(t, (15, 5))

        info = f"BPM: {self.bm.bpm:.1f}  |  Snap: 1/{self.snap_div if self.snap_div else 'OFF'}  |  Noten: {len(self.notes)}  |  Zoom: {self.zoom:.0f}"
        s = self._font_xs.render(info, True, (150, 150, 150))
        scr.blit(s, (15, 30))

        status = "▶ Spielt..." if self.playing else ("♫ Audio geladen" if self.audio_loaded else "⚠ Kein Audio (I: Importieren)")
        col = GREAT_COL if self.audio_loaded else MISS_COL
        st = self._font_sm.render(status, True, col)
        scr.blit(st, (w - st.get_width() - 15, 8))

        if self.save_path:
            sv = self._font_xs.render(f"💾 {self.save_path}", True, GREAT_COL)
            scr.blit(sv, (w - sv.get_width() - 15, 30))

    def _draw_footer(self, w: int, h: int):
        scr = self.screen
        footer = pygame.Surface((w, 30), pygame.SRCALPHA)
        footer.fill((13, 4, 32, 220))
        scr.blit(footer, (0, h - 30))

        lane_air = self._font_xs.render("Luft ↑", True, AIR_COL)
        lane_gnd = self._font_xs.render("Boden ↓", True, GROUND_COL)
        scr.blit(lane_air, (10, int(h * 0.3) - 6))
        scr.blit(lane_gnd, (10, int(h * 0.7) - 6))

        pos_ms = get_music_pos_ms() if self.playing else (self.scroll_x / self.zoom * 1000)
        dur_ms = self.music_len_ms
        pos_s = max(0, pos_ms / 1000)
        dur_s = dur_ms / 1000

        time_str = f"{int(pos_s // 60)}:{pos_s % 60:04.1f} / {int(dur_s // 60)}:{dur_s % 60:04.1f}"
        ts = self._font_sm.render(time_str, True, (180, 180, 180))
        scr.blit(ts, (w // 2 - ts.get_width() // 2, h - 25))

        keys = "[SPACE] Play  [D/J] Boden  [F/K] Luft  [DEL] Löschen  [I] Audio  [+/-] BPM  [Ctrl+S] Speichern  [T] Test  [1-4] Snap  [ESC] Zurück"
        ks = self._font_xs.render(keys, True, (70, 70, 70))
        scr.blit(ks, (w // 2 - ks.get_width() // 2, h - 12))
