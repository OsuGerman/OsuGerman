"""Complete screen system built on the UI theme."""
from __future__ import annotations
import os, json, glob, math, random, shutil
import pygame
from .ui_theme import Colors, Fonts, Spacing, draw_panel, draw_text, draw_gradient_bg, draw_button
from .audio import set_music_volume, set_sfx_volume, play_sfx

C = Colors
MAP_DIR = 'maps'
SONG_DIR = 'songs'


class ScreenResult:
    """Return value from screen update — tells the app what to do."""
    def __init__(self, action: str = '', data: dict = None):
        self.action = action
        self.data = data or {}


class BaseScreen:
    def __init__(self, surface: pygame.Surface):
        self.scr = surface
        self._stars = [(random.random(), random.random(), random.uniform(1, 3)) for _ in range(50)]
        self._t = 0.0
        self._buttons: list[tuple[pygame.Rect, str]] = []

    def draw_bg(self):
        w, h = self.scr.get_size()
        draw_gradient_bg(self.scr)
        for xr, yr, sz in self._stars:
            sx = int((xr * w + self._t * (6 + sz * 5)) % w)
            sy = int(yr * h)
            a = min(255, int(35 + sz * 20))
            pygame.draw.circle(self.scr, (a, a, a), (sx, sy), max(1, int(sz)))

    def update(self, dt: float, events: list, mouse: tuple) -> ScreenResult:
        self._t += dt
        self._buttons.clear()
        return ScreenResult()

    def btn(self, text, x, y, w, h, action, mouse, color=C.PRIMARY, font=None, enabled=True):
        rect, hovered = draw_button(self.scr, text, x, y, w, h, color, mouse, font, enabled)
        self._buttons.append((rect, action))
        return hovered

    def check_click(self, pos) -> str:
        for rect, action in self._buttons:
            if rect.collidepoint(pos):
                play_sfx('tick')
                return action
        return ''

    def check_hover(self, pos) -> bool:
        return any(r.collidepoint(pos) for r, _ in self._buttons)


# ══════════════════════════════════════
# MAIN MENU
# ══════════════════════════════════════

class MainMenuScreen(BaseScreen):
    def update(self, dt, events, mouse):
        self._t += dt
        self._buttons.clear()
        w, h = self.scr.get_size()
        self.draw_bg()

        # Decorative lines
        for i in range(4):
            x = int((self._t * (12 + i * 8) + i * 200) % (w + 300) - 150)
            y = int(h * (0.25 + i * 0.15))
            pts = [(x + j * 10, y + int(math.sin((x + j * 10 + self._t * 30) * 0.02) * 12)) for j in range(30)]
            if len(pts) > 1:
                pygame.draw.lines(self.scr, (*C.ACCENT, ), False, pts, 1)

        # Logo
        draw_text(self.scr, "Rhythm", w // 2, h // 5 - 10, Fonts.hero(), C.TEXT, 'center', True)
        draw_text(self.scr, "Dash", w // 2 + 200, h // 5 - 10, Fonts.hero(), C.PRIMARY, shadow=True)
        draw_text(self.scr, "Dein Rhythmus. Dein Spiel.", w // 2, h // 5 + 65, Fonts.caption(), C.TEXT_MUTED, 'center')

        # Buttons
        bw, bh = 280, 52
        bx = w // 2 - bw // 2
        by = h // 2 - 30
        self.btn("▶  Spielen", bx, by, bw, bh, 'play', mouse, C.PRIMARY)
        self.btn("✎  Editor", bx, by + 62, bw, bh, 'editor', mouse, C.SECONDARY)
        self.btn("♫  Song Importieren", bx, by + 124, bw, bh, 'import', mouse, C.ACCENT_DIM)
        self.btn("⚙  Einstellungen", bx, by + 186, bw, bh, 'settings', mouse, C.BG_CARD)

        draw_text(self.scr, "[D/J] Boden  [F/K] Luft  —  F11 Fullscreen", w // 2, h - 30,
                  Fonts.micro(), C.TEXT_MUTED, 'center')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self.check_click(ev.pos)
                if a: return ScreenResult(a)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN: return ScreenResult('play')
                if ev.key == pygame.K_e: return ScreenResult('editor')
                if ev.key == pygame.K_i: return ScreenResult('import')
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self.check_hover(mouse) else pygame.SYSTEM_CURSOR_ARROW)
        return ScreenResult()


# ══════════════════════════════════════
# SONG SELECT
# ══════════════════════════════════════

class SongSelectScreen(BaseScreen):
    def __init__(self, surface, maps):
        super().__init__(surface)
        self.maps = maps
        self.selected = 0
        self._scroll = 0.0

    def update(self, dt, events, mouse):
        self._t += dt
        self._buttons.clear()
        w, h = self.scr.get_size()
        self.draw_bg()

        draw_text(self.scr, "Lied Auswählen", 40, 18, Fonts.title(), C.TEXT, shadow=True)
        self.btn("♫ Import", w - 270, 18, 110, 34, 'import', mouse, C.ACCENT_DIM, Fonts.caption())
        self.btn("← Zurück", w - 140, 18, 110, 34, 'back', mouse, C.BG_CARD, Fonts.caption())

        if not self.maps:
            draw_text(self.scr, "Keine Songs vorhanden. Importiere einen!", w // 2, h // 2,
                      Fonts.heading(), C.TEXT_MUTED, 'center')
        else:
            y_start = 75
            for i, m in enumerate(self.maps):
                cy = y_start + i * 72
                if cy > h - 50: break
                sel = i == self.selected
                hov = pygame.Rect(28, cy, w - 56, 64).collidepoint(mouse)

                bg = C.BG_CARD_ACTIVE if sel else C.BG_CARD_HOVER if hov else C.BG_CARD
                border = C.PRIMARY if sel else C.BORDER_HOVER if hov else C.BORDER
                draw_panel(self.scr, (28, cy, w - 56, 64), bg, border, Spacing.CARD_RADIUS)
                self._buttons.append((pygame.Rect(28, cy, w - 56, 64), f'card_{i}'))

                draw_text(self.scr, m.get('title', '?'), 48, cy + 8, Fonts.heading(), C.TEXT)
                info = f"{m.get('artist', '?')}  ·  {m.get('note_count', 0)} Noten  ·  BPM {m.get('bpm', 0)}"
                draw_text(self.scr, info, 48, cy + 36, Fonts.caption(), C.TEXT_DIM)

                has_audio = m.get('has_audio', False)
                tag = "✓ Audio" if has_audio else "✗ Kein Audio"
                tag_col = C.SUCCESS if has_audio else C.DANGER
                draw_text(self.scr, tag, w - 80, cy + 10, Fonts.caption(), tag_col, 'right')

                diff = m.get('difficulty', 5)
                stars = "★" * min(diff, 10) + "☆" * max(0, 10 - diff)
                draw_text(self.scr, stars, w - 80, cy + 34, Fonts.caption(), C.GOLD, 'right')

        draw_text(self.scr, "↑↓ Wählen   ENTER Spielen   E Editieren   ENTF Löschen   I Import",
                  w // 2, h - 22, Fonts.micro(), C.TEXT_MUTED, 'center')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self.check_click(ev.pos)
                if a == 'back': return ScreenResult('back')
                if a == 'import': return ScreenResult('import')
                if a.startswith('card_'):
                    idx = int(a.split('_')[1])
                    if self.selected == idx:
                        return ScreenResult('start', {'index': idx})
                    self.selected = idx
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return ScreenResult('back')
                if ev.key == pygame.K_UP and self.maps:
                    self.selected = (self.selected - 1) % len(self.maps)
                if ev.key == pygame.K_DOWN and self.maps:
                    self.selected = (self.selected + 1) % len(self.maps)
                if ev.key == pygame.K_RETURN and self.maps:
                    return ScreenResult('start', {'index': self.selected})
                if ev.key == pygame.K_e and self.maps:
                    return ScreenResult('edit', {'index': self.selected})
                if ev.key == pygame.K_DELETE and self.maps:
                    return ScreenResult('delete', {'index': self.selected})
                if ev.key == pygame.K_i:
                    return ScreenResult('import')
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self.check_hover(mouse) else pygame.SYSTEM_CURSOR_ARROW)
        return ScreenResult()


# ══════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════

class SettingsScreen(BaseScreen):
    TABS = ['Audio', 'Gameplay', 'Controls', 'Graphics']

    def __init__(self, surface, settings):
        super().__init__(surface)
        self.settings = settings
        self.active_tab = 0
        self._dragging = None

    def update(self, dt, events, mouse):
        self._t += dt
        self._buttons.clear()
        w, h = self.scr.get_size()
        self.draw_bg()

        draw_text(self.scr, "Einstellungen", w // 2, 18, Fonts.title(), C.TEXT, 'center', True)

        # Tabs
        tab_w = 140
        tab_x = w // 2 - len(self.TABS) * tab_w // 2
        for i, tab in enumerate(self.TABS):
            active = i == self.active_tab
            col = C.PRIMARY if active else C.BG_CARD
            self.btn(tab, tab_x + i * (tab_w + 8), 65, tab_w, 34, f'tab_{i}', mouse, col, Fonts.caption())

        # Content
        panel_x, panel_y = 60, 115
        panel_w, panel_h = w - 120, h - 195
        draw_panel(self.scr, (panel_x, panel_y, panel_w, panel_h), C.BG_MID, C.BORDER, Spacing.PANEL_RADIUS, 220)

        cx, cy = panel_x + Spacing.PANEL_PADDING, panel_y + Spacing.PANEL_PADDING
        sw = panel_w - Spacing.PANEL_PADDING * 2

        if self.active_tab == 0:
            cy = self._draw_sliders(cx, cy, sw, mouse, [
                ("Musik-Lautstärke", 'music_volume', self.settings.music_volume),
                ("SFX-Lautstärke", 'sfx_volume', self.settings.sfx_volume),
                ("Audio-Offset (ms)", 'audio_offset', (self.settings.audio_offset + 200) / 400),
            ])
        elif self.active_tab == 1:
            cy = self._draw_sliders(cx, cy, sw, mouse, [
                ("Noten-Speed", 'note_speed', (self.settings.note_speed - 0.2) / 0.8),
                ("Approach Rate", 'approach_rate', (self.settings.approach_rate - 1) / 9),
                ("Overall Difficulty", 'overall_difficulty', (self.settings.overall_difficulty - 1) / 9),
                ("Hintergrund-Dim", 'bg_dim', self.settings.bg_dim),
            ])
            hw = self.settings.get_hit_windows()
            draw_text(self.scr, f"Perfect: ±{hw['perfect']}ms   Great: ±{hw['great']}ms   Good: ±{hw['good']}ms",
                      cx, cy + 8, Fonts.caption(), C.TEXT_MUTED)
        elif self.active_tab == 2:
            gk = ', '.join(pygame.key.name(k).upper() for k in self.settings.ground_keys)
            ak = ', '.join(pygame.key.name(k).upper() for k in self.settings.air_keys)
            draw_text(self.scr, f"Boden-Lane:  {gk}", cx, cy, Fonts.body(), C.TEXT)
            draw_text(self.scr, f"Luft-Lane:  {ak}", cx, cy + 30, Fonts.body(), C.TEXT)
            draw_text(self.scr, "Pause: ESC   Quit: Q   Fullscreen: F11   Volume: +/-", cx, cy + 70, Fonts.caption(), C.TEXT_MUTED)
            self.btn("+ Boden-Taste", cx, cy + 110, 200, 36, 'rebind_ground', mouse, C.SECONDARY, Fonts.caption())
            self.btn("+ Luft-Taste", cx + 220, cy + 110, 200, 36, 'rebind_air', mouse, C.ACCENT_DIM, Fonts.caption())
            self.btn("Tasten zurücksetzen", cx, cy + 160, 200, 36, 'reset_keys', mouse, C.DANGER, Fonts.caption())
        elif self.active_tab == 3:
            cy = self._draw_sliders(cx, cy, sw, mouse, [
                ("FPS-Limit (0=Unlocked)", 'fps_limit', self.settings.fps_limit / 480),
            ])
            draw_text(self.scr, f"FPS: {self.settings.fps_limit if self.settings.fps_limit > 0 else 'Unlocked'}",
                      cx, cy + 8, Fonts.caption(), C.TEXT_MUTED)
            self.btn("Fullscreen (F11)", cx, cy + 40, 200, 36, 'fullscreen', mouse, C.BG_CARD, Fonts.caption())

        self.btn("← Zurück & Speichern", w // 2 - 140, h - 65, 280, 48, 'save', mouse, C.PRIMARY)

        # Events
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self.check_click(ev.pos)
                if a.startswith('tab_'):
                    self.active_tab = int(a.split('_')[1])
                elif a == 'save':
                    self.settings.save()
                    return ScreenResult('back')
                elif a == 'fullscreen':
                    return ScreenResult('fullscreen')
                elif a == 'rebind_ground':
                    return ScreenResult('rebind', {'lane': 'ground'})
                elif a == 'rebind_air':
                    return ScreenResult('rebind', {'lane': 'air'})
                elif a == 'reset_keys':
                    self.settings.ground_keys = [pygame.K_d, pygame.K_j, pygame.K_DOWN]
                    self.settings.air_keys = [pygame.K_f, pygame.K_k, pygame.K_UP]
                for sr, sn in self._slider_rects:
                    if sr.collidepoint(ev.pos):
                        self._dragging = sn
                        self._handle_drag(sn, ev.pos[0], sr)
            if ev.type == pygame.MOUSEBUTTONUP:
                self._dragging = None
            if ev.type == pygame.MOUSEMOTION and self._dragging:
                for sr, sn in self._slider_rects:
                    if sn == self._dragging:
                        self._handle_drag(sn, ev.pos[0], sr)
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.settings.save()
                return ScreenResult('back')
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self.check_hover(mouse) else pygame.SYSTEM_CURSOR_ARROW)
        return ScreenResult()

    _slider_rects: list[tuple[pygame.Rect, str]] = []

    def _draw_sliders(self, cx, cy, sw, mouse, sliders):
        self._slider_rects = []
        for label, name, value in sliders:
            draw_text(self.scr, label, cx, cy + 4, Fonts.body(), C.TEXT_DIM)
            bar_x = cx + 220
            bar_w = sw - 270
            bar_h = 10
            bar_y = cy + 8
            rect = pygame.Rect(bar_x, bar_y - 4, bar_w, bar_h + 8)
            self._slider_rects.append((rect, name))
            pygame.draw.rect(self.scr, C.BG_DARK, (bar_x, bar_y, bar_w, bar_h), border_radius=5)
            fill = int(bar_w * max(0, min(1, value)))
            if fill > 0:
                pygame.draw.rect(self.scr, C.PRIMARY, (bar_x, bar_y, fill, bar_h), border_radius=5)
            knob_x = bar_x + fill
            knob_hov = abs(mouse[0] - knob_x) < 12 and abs(mouse[1] - (bar_y + 5)) < 12
            knob_r = 8 if knob_hov else 7
            pygame.draw.circle(self.scr, C.TEXT if knob_hov else C.TEXT_DIM, (knob_x, bar_y + 5), knob_r)
            pygame.draw.circle(self.scr, C.PRIMARY, (knob_x, bar_y + 5), knob_r, 2)
            val_text = f"{int(value * 100)}%"
            if name == 'audio_offset':
                val_text = f"{int(value * 400 - 200)}ms"
            elif name in ('approach_rate', 'overall_difficulty'):
                val_text = f"{1 + value * 9:.1f}"
            elif name == 'fps_limit':
                v = int(value * 480)
                val_text = str(v) if v > 0 else "∞"
            draw_text(self.scr, val_text, bar_x + bar_w + 10, cy + 2, Fonts.caption(), C.TEXT_MUTED)
            cy += 44
        return cy

    def _handle_drag(self, name, mx, rect):
        ratio = max(0, min(1, (mx - rect.x) / rect.width))
        s = self.settings
        if name == 'music_volume':
            s.music_volume = ratio; set_music_volume(ratio)
        elif name == 'sfx_volume':
            s.sfx_volume = ratio; set_sfx_volume(ratio)
        elif name == 'audio_offset':
            s.audio_offset = int(ratio * 400 - 200)
        elif name == 'note_speed':
            s.note_speed = round(0.2 + ratio * 0.8, 2)
        elif name == 'approach_rate':
            s.approach_rate = round(1 + ratio * 9, 1)
        elif name == 'overall_difficulty':
            s.overall_difficulty = round(1 + ratio * 9, 1)
        elif name == 'bg_dim':
            s.bg_dim = ratio
        elif name == 'fps_limit':
            s.fps_limit = int(ratio * 480)


# ══════════════════════════════════════
# RESULTS
# ══════════════════════════════════════

class ResultsScreen(BaseScreen):
    def __init__(self, surface, result: dict):
        super().__init__(surface)
        self.result = result

    def update(self, dt, events, mouse):
        self._t += dt
        self._buttons.clear()
        w, h = self.scr.get_size()
        self.draw_bg()
        r = self.result

        grade = r.get('grade', 'D')
        gcol = C.GOLD if grade == 'S' else C.SUCCESS if grade == 'A' else C.ACCENT if grade == 'B' else C.DANGER
        cleared = r.get('cleared', True)

        # Grade
        draw_text(self.scr, grade, w // 2, 15, Fonts.grade(), gcol, 'center', True)

        # Song title
        draw_text(self.scr, r.get('song_title', r.get('title', '')), w // 2, 130,
                  Fonts.heading(), C.TEXT_DIM, 'center')

        status = "CLEARED" if cleared else "FAILED"
        status_col = C.SUCCESS if cleared else C.DANGER
        draw_text(self.scr, status, w // 2, 158, Fonts.body_bold(), status_col, 'center')

        # Score panel
        draw_panel(self.scr, (w // 2 - 260, 185, 520, 260), C.BG_MID, C.BORDER, Spacing.PANEL_RADIUS, 230)

        draw_text(self.scr, f"{r.get('score', 0):,}", w // 2, 200, Fonts.score(), C.PRIMARY, 'center', True)

        # Stats
        stats = [("Perfect", r.get('perfect', 0), C.GOLD),
                 ("Great", r.get('great', 0), C.SUCCESS),
                 ("Good", r.get('good', 0), C.ACCENT),
                 ("Miss", r.get('miss', 0), C.DANGER)]
        sx = w // 2 - 200
        for i, (label, val, col) in enumerate(stats):
            cx_s = sx + i * 105
            draw_text(self.scr, str(val), cx_s + 50, 245, Fonts.title(), col, 'center')
            draw_text(self.scr, label, cx_s + 50, 285, Fonts.caption(), C.TEXT_MUTED, 'center')

        draw_text(self.scr, f"Max Combo: {r.get('max_combo', 0)}x", w // 2 - 100, 315, Fonts.body(), C.TEXT_DIM)
        draw_text(self.scr, f"Accuracy: {r.get('accuracy', 0):.1f}%", w // 2 + 40, 315, Fonts.body(), C.TEXT_DIM)

        ur = r.get('unstable_rate', 0)
        avg = r.get('avg_error', 0)
        draw_text(self.scr, f"UR: {ur:.1f}   Avg: {avg:+.1f}ms   Early: {r.get('early', 0)}  Late: {r.get('late', 0)}",
                  w // 2, 345, Fonts.caption(), C.TEXT_MUTED, 'center')

        # Timing scatter
        errors = r.get('timing_errors', [])
        if errors:
            bar_w, bar_h = 280, 24
            bar_x = w // 2 - bar_w // 2
            bar_y = 370
            draw_panel(self.scr, (bar_x - 4, bar_y - 4, bar_w + 8, bar_h + 8), C.BG_DARK, C.BORDER, 6)
            pygame.draw.line(self.scr, C.TEXT_MUTED, (bar_x + bar_w // 2, bar_y), (bar_x + bar_w // 2, bar_y + bar_h))
            for err in errors[-80:]:
                ratio = max(-1, min(1, err / 120))
                px = bar_x + bar_w // 2 + int(ratio * bar_w / 2)
                col = C.GOLD if abs(err) < 35 else C.ACCENT if err > 0 else C.GROUND
                pygame.draw.circle(self.scr, col, (px, bar_y + bar_h // 2 + random.randint(-6, 6)), 2)

        # Buttons
        self.btn("↻ Nochmal", w // 2 - 210, 415, 195, 48, 'retry', mouse, C.PRIMARY)
        self.btn("← Zurück", w // 2 + 15, 415, 195, 48, 'back', mouse, C.BG_CARD)

        draw_text(self.scr, "R: Nochmal   ESC: Zurück", w // 2, h - 25, Fonts.micro(), C.TEXT_MUTED, 'center')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self.check_click(ev.pos)
                if a: return ScreenResult(a)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return ScreenResult('back')
                if ev.key == pygame.K_r: return ScreenResult('retry')
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self.check_hover(mouse) else pygame.SYSTEM_CURSOR_ARROW)
        return ScreenResult()


# ══════════════════════════════════════
# HELPERS
# ══════════════════════════════════════

def load_all_maps() -> list[dict]:
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
                'note_count': len(d.get('notes', d.get('objects', []))),
                'has_audio': os.path.exists(af),
            })
        except Exception:
            pass
    for path in sorted(glob.glob('data/songs/*.json')):
        try:
            with open(path) as f:
                d = json.load(f)
            af = d.get('audioFile', d.get('audio_file', ''))
            if not os.path.isabs(af): af = os.path.join(os.getcwd(), af)
            for diff in d.get('difficulties', d.get('difficultyList', [])):
                cf = diff.get('chartFile', diff.get('chart_file', ''))
                nc = 0
                if cf and os.path.exists(cf):
                    try:
                        with open(cf) as f2: nc = len(json.load(f2).get('objects', []))
                    except: pass
                maps.append({
                    'path': cf or path, 'id': d.get('id','')+'_'+diff.get('id',''),
                    'title': d.get('title','?'), 'artist': d.get('artist','?'),
                    'bpm': d.get('bpm',0), 'difficulty': diff.get('level',5),
                    'note_count': nc, 'has_audio': os.path.exists(af),
                })
        except: pass
    return maps
