"""Complete game screens — professional visual quality."""
from __future__ import annotations
import os, json, glob, math, random
import pygame
from .ui_theme import C, F, S, draw_bg, draw_stars, panel, glow_rect, text, button, slider, badge
from .audio import set_music_volume, set_sfx_volume, play_sfx
from .ui_sounds import play_ui

MAP_DIR, SONG_DIR = 'maps', 'songs'

class SR:
    def __init__(self, action='', data=None):
        self.action = action; self.data = data or {}
ScreenResult = SR

class Base:
    def __init__(self, scr):
        self.scr = scr
        self._stars = [(random.random(), random.random(), random.uniform(1, 3)) for _ in range(55)]
        self._t = 0.0
        self._btns: list[tuple[pygame.Rect, str]] = []
        self._sliders: list[tuple[pygame.Rect, str]] = []
        self._drag = None

    def bg(self):
        draw_bg(self.scr); draw_stars(self.scr, self._stars, self._t)

    def _btn(self, t, x, y, w, h, a, m, c=C.PRIMARY, f=None, e=True, icon=''):
        r, hov = button(self.scr, t, x, y, w, h, m, c, f, e, icon)
        self._btns.append((r, a)); return hov

    def _click(self, pos):
        for r, a in self._btns:
            if r.collidepoint(pos): play_ui('click'); return a
        return ''

    def _hovering(self, pos): return any(r.collidepoint(pos) for r, _ in self._btns)
    def _cursor(self, pos):
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self._hovering(pos) else pygame.SYSTEM_CURSOR_ARROW)


# ══════════════════════════════
# SPLASH SCREEN
# ══════════════════════════════

class SplashScreen(Base):
    def __init__(self, scr):
        super().__init__(scr)
        self._timer = 0.0
        self._phase = 0  # 0=fade in, 1=hold, 2=fade out

    def update(self, dt, events, mouse):
        self._t += dt
        self._timer += dt
        w, h = self.scr.get_size()

        # Background
        self.scr.fill((6, 2, 18))

        alpha = 0
        if self._timer < 0.8:
            alpha = int(255 * self._timer / 0.8)
        elif self._timer < 2.2:
            alpha = 255
        elif self._timer < 3.0:
            alpha = int(255 * (1 - (self._timer - 2.2) / 0.8))
        else:
            return SR('done')

        # Logo
        logo = F.hero().render("Rhythm Dash", True, C.PRIMARY)
        logo.set_alpha(alpha)
        sh = F.hero().render("Rhythm Dash", True, (0, 0, 0))
        sh.set_alpha(alpha // 3)
        self.scr.blit(sh, (w // 2 - logo.get_width() // 2 + 3, h // 2 - 40 + 3))
        self.scr.blit(logo, (w // 2 - logo.get_width() // 2, h // 2 - 40))

        sub = F.cap().render("Ein Rhythm-Action-Game", True, C.TEXT_3)
        sub.set_alpha(alpha)
        self.scr.blit(sub, (w // 2 - sub.get_width() // 2, h // 2 + 30))

        # Skip
        for ev in events:
            if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return SR('done')

        return SR()


# ══════════════════════════════
# MAIN MENU
# ══════════════════════════════

class MainMenuScreen(Base):
    def update(self, dt, events, mouse):
        self._t += dt; self._btns.clear()
        w, h = self.scr.get_size()
        self.bg()

        # Decorative shapes
        for i in range(6):
            ox = int((self._t * (8 + i * 5) + i * 200) % (w + 400) - 200)
            oy = int(h * (0.15 + i * 0.12))
            pts = [(ox + j * 14, oy + int(math.sin((ox + j * 14 + self._t * 20) * 0.015) * 18)) for j in range(28)]
            if len(pts) > 1:
                col = C.PRIMARY if i % 3 == 0 else C.ACCENT if i % 3 == 1 else C.SECONDARY
                ls = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.lines(ls, (*col, 18), False, pts, 1)
                self.scr.blit(ls, (0, 0))

        # Logo area with backing panel
        logo_w, logo_h = 520, 130
        lx, ly = w // 2 - logo_w // 2, h // 6 - 20
        panel(self.scr, lx, ly, logo_w, logo_h, C.BG_1, None, S.RAD_LG, 100)

        # Logo glow
        gs = pygame.Surface((logo_w + 40, logo_h + 40), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*C.PRIMARY, 12), (0, 0, logo_w + 40, logo_h + 40), border_radius=S.RAD_LG + 10)
        self.scr.blit(gs, (lx - 20, ly - 20))

        text(self.scr, "Rhythm", w // 2 - 150, ly + 20, F.hero(), C.TEXT, shadow=True)
        text(self.scr, "Dash", w // 2 + 108, ly + 20, F.hero(), C.PRIMARY, shadow=True)
        text(self.scr, "Dein Rhythmus. Dein Spiel.", w // 2, ly + 95, F.cap(), C.TEXT_3, 'center')

        # Button panel
        bp_w, bp_h = 360, 290
        bpx, bpy = w // 2 - bp_w // 2, h // 2 - 30
        panel(self.scr, bpx, bpy, bp_w, bp_h, C.BG_2, C.BORDER, S.RAD_LG, 180)

        bw, bh = 300, S.BTN_H
        bx = w // 2 - bw // 2
        by = bpy + 22
        self._btn("Spielen", bx, by, bw, bh, 'play', mouse, C.PRIMARY, icon='▶')
        self._btn("Editor", bx, by + 58, bw, bh, 'editor', mouse, C.SECONDARY, icon='✎')
        self._btn("Song Importieren", bx, by + 116, bw, bh, 'import', mouse, C.ACCENT_D, icon='♫')
        self._btn("Einstellungen", bx, by + 174, bw, bh, 'settings', mouse, C.BG_3, icon='⚙')

        # Footer
        panel(self.scr, 0, h - 36, w, 36, C.BG_0, None, 0, 160)
        text(self.scr, "F11 Fullscreen  ·  D/J Boden  ·  F/K Luft  ·  F3 Debug", w // 2, h - 28, F.micro(), C.TEXT_OFF, 'center')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self._click(ev.pos)
                if a: return SR(a)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN: return SR('play')
        self._cursor(mouse)
        return SR()


# ══════════════════════════════
# SONG SELECT
# ══════════════════════════════

class SongSelectScreen(Base):
    def __init__(self, scr, maps):
        super().__init__(scr); self.maps = maps; self.sel = 0

    def update(self, dt, events, mouse):
        self._t += dt; self._btns.clear()
        w, h = self.scr.get_size()
        self.bg()

        # Header bar
        panel(self.scr, 0, 0, w, 62, C.BG_1, C.BORDER, 0, 230)
        text(self.scr, "Lied Auswählen", 30, 14, F.title(), C.TEXT, shadow=True)
        self._btn("Import", w - 260, 14, 100, 34, 'import', mouse, C.ACCENT_D, F.cap(), icon='♫')
        self._btn("Zurück", w - 140, 14, 110, 34, 'back', mouse, C.BG_3, F.cap(), icon='←')

        if not self.maps:
            panel(self.scr, w // 2 - 250, h // 2 - 40, 500, 80, C.BG_2, C.BORDER, S.RAD, 200)
            text(self.scr, "Keine Songs vorhanden!", w // 2, h // 2 - 20, F.h2(), C.TEXT_3, 'center')
            text(self.scr, "Importiere einen Song mit dem Import-Button", w // 2, h // 2 + 10, F.cap(), C.TEXT_OFF, 'center')
        else:
            y0 = 74
            for i, m in enumerate(self.maps):
                cy = y0 + i * 78
                if cy > h - 60: break
                sel = i == self.sel
                hov = pygame.Rect(16, cy, w - 32, 70).collidepoint(mouse)
                bg = C.CARD_A if sel else C.CARD_H if hov else C.CARD
                bd = C.BORDER_A if sel else C.BORDER_H if hov else C.BORDER
                if sel: glow_rect(self.scr, 16, cy, w - 32, 70, C.PRIMARY, 22, 8)
                panel(self.scr, 16, cy, w - 32, 70, bg, bd, S.RAD)
                self._btns.append((pygame.Rect(16, cy, w - 32, 70), f'card_{i}'))

                # Song info
                text(self.scr, m.get('title', '?'), 36, cy + 10, F.h2(), C.TEXT if sel else C.TEXT_2)
                info = f"{m.get('artist', '?')}  ·  {m.get('note_count', 0)} Noten  ·  {m.get('bpm', 0)} BPM"
                text(self.scr, info, 36, cy + 40, F.cap(), C.TEXT_3)

                # Audio badge
                has_a = m.get('has_audio', False)
                badge(self.scr, "✓ Audio" if has_a else "✗ Fehlt",
                      w - 120, cy + 12, C.SUCCESS if has_a else C.DANGER)

                # Difficulty stars
                diff = m.get('difficulty', 5)
                stars = "★" * min(diff, 10) + "☆" * max(0, 10 - diff)
                text(self.scr, stars, w - 70, cy + 44, F.cap(), C.GOLD, 'right')

        # Footer
        panel(self.scr, 0, h - 34, w, 34, C.BG_0, None, 0, 180)
        text(self.scr, "↑↓ Wählen  ·  ENTER Spielen  ·  E Editieren  ·  ENTF Löschen  ·  I Import",
             w // 2, h - 26, F.micro(), C.TEXT_OFF, 'center')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self._click(ev.pos)
                if a == 'back': return SR('back')
                if a == 'import': return SR('import')
                if a.startswith('card_'):
                    idx = int(a.split('_')[1])
                    if self.sel == idx: return SR('start', {'index': idx})
                    self.sel = idx
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return SR('back')
                if ev.key == pygame.K_UP and self.maps: self.sel = (self.sel - 1) % len(self.maps)
                if ev.key == pygame.K_DOWN and self.maps: self.sel = (self.sel + 1) % len(self.maps)
                if ev.key == pygame.K_RETURN and self.maps: return SR('start', {'index': self.sel})
                if ev.key == pygame.K_e and self.maps: return SR('edit', {'index': self.sel})
                if ev.key == pygame.K_DELETE and self.maps: return SR('delete', {'index': self.sel})
                if ev.key == pygame.K_i: return SR('import')
        self._cursor(mouse)
        return SR()


# ══════════════════════════════
# SETTINGS
# ══════════════════════════════

class SettingsScreen(Base):
    TABS = ['Audio', 'Gameplay', 'Controls', 'Grafik', 'Zugang']

    def __init__(self, scr, settings):
        super().__init__(scr); self.s = settings; self.tab = 0
        self._rebinding = None  # 'ground' or 'air' or None

    def update(self, dt, events, mouse):
        self._t += dt; self._btns.clear(); self._sliders.clear()
        w, h = self.scr.get_size()
        self.bg()

        # Header
        panel(self.scr, 0, 0, w, 56, C.BG_1, C.BORDER, 0, 230)
        text(self.scr, "Einstellungen", w // 2, 10, F.title(), C.TEXT, 'center', True)

        # Tabs
        tw = 120
        tx = w // 2 - len(self.TABS) * (tw + 4) // 2
        for i, t in enumerate(self.TABS):
            c = C.PRIMARY if i == self.tab else C.BG_3
            self._btn(t, tx + i * (tw + 4), 62, tw, 30, f'tab_{i}', mouse, c, F.cap())

        # Content panel
        px, py = 40, 102; pw, ph = w - 80, h - 175
        panel(self.scr, px, py, pw, ph, C.BG_2, C.BORDER, S.RAD_LG, 225)
        cx, cy = px + S.XL, py + S.LG; sw = pw - S.XL * 2

        if self.tab == 0:
            self._sl(cx, cy, sw, mouse, 'music_volume', "Musik-Lautstärke", self.s.music_volume)
            self._sl(cx, cy + 44, sw, mouse, 'sfx_volume', "SFX-Lautstärke", self.s.sfx_volume)
            self._sl(cx, cy + 88, sw, mouse, 'audio_offset', "Audio-Offset", (self.s.audio_offset + 200) / 400)
            text(self.scr, f"Offset: {self.s.audio_offset}ms", cx + 210, cy + 100, F.micro(), C.TEXT_OFF)
        elif self.tab == 1:
            self._sl(cx, cy, sw, mouse, 'note_speed', "Noten-Speed", (self.s.note_speed - 0.2) / 0.8)
            self._sl(cx, cy + 44, sw, mouse, 'approach_rate', "Approach Rate", (self.s.approach_rate - 1) / 9)
            self._sl(cx, cy + 88, sw, mouse, 'overall_difficulty', "Overall Difficulty", (self.s.overall_difficulty - 1) / 9)
            self._sl(cx, cy + 132, sw, mouse, 'bg_dim', "Hintergrund-Dim", self.s.bg_dim)
            hw = self.s.get_hit_windows()
            text(self.scr, f"Perfect ±{hw['perfect']}ms  ·  Great ±{hw['great']}ms  ·  Good ±{hw['good']}ms  ·  Approach {self.s.get_approach_time_ms()}ms",
                 cx, cy + 178, F.micro(), C.TEXT_OFF)
        elif self.tab == 2:
            gk = ', '.join(pygame.key.name(k).upper() for k in self.s.ground_keys)
            ak = ', '.join(pygame.key.name(k).upper() for k in self.s.air_keys)
            text(self.scr, "Boden-Lane:", cx, cy + 5, F.bold(), C.TEXT_2)
            badge(self.scr, gk, cx + 130, cy + 2, C.SECONDARY)
            text(self.scr, "Luft-Lane:", cx, cy + 40, F.bold(), C.TEXT_2)
            badge(self.scr, ak, cx + 130, cy + 37, C.ACCENT_D)
            text(self.scr, "Pause: ESC  ·  Quit: Q  ·  Fullscreen: F11  ·  Volume: +/−  ·  Debug: F3", cx, cy + 85, F.cap(), C.TEXT_3)
            if self._rebinding:
                lane_name = 'Boden' if self._rebinding == 'ground' else 'Luft'
                panel(self.scr, cx, cy + 110, 500, 40, C.SECONDARY, C.BORDER_A, S.RAD, 220)
                text(self.scr, f"Drücke eine Taste für {lane_name}... (ESC abbrechen)", cx + 20, cy + 120, F.bold(), C.GOLD)
            else:
                self._btn("+ Boden", cx, cy + 120, 160, 32, 'rebind_ground', mouse, C.SECONDARY, F.cap())
                self._btn("+ Luft", cx + 180, cy + 120, 160, 32, 'rebind_air', mouse, C.ACCENT_D, F.cap())
                self._btn("Zurücksetzen", cx + 380, cy + 120, 160, 32, 'reset_keys', mouse, C.DANGER_D, F.cap())
        elif self.tab == 3:
            self._sl(cx, cy, sw, mouse, 'fps_limit', "FPS-Limit", self.s.fps_limit / 480)
            v = self.s.fps_limit
            text(self.scr, f"{'Unlocked' if v == 0 else str(v)+' FPS'}", cx + 210, cy + 12, F.micro(), C.TEXT_OFF)
            self._btn("Fullscreen (F11)", cx, cy + 55, 200, 32, 'fullscreen', mouse, C.BG_3, F.cap())
        elif self.tab == 4:
            toggles = [
                ("Blitz-Effekte reduzieren", 'reduce_flash', self.s.reduce_flash),
                ("Auto-Retry bei Fail", 'auto_retry', self.s.auto_retry),
                ("Debug Overlay (F3)", 'debug_overlay', self.s.debug_overlay),
            ]
            for i, (label, attr, val) in enumerate(toggles):
                ty = cy + i * 44
                text(self.scr, label, cx, ty + 6, F.body(), C.TEXT_2)
                col = C.SUCCESS if val else C.BG_3
                self._btn("AN" if val else "AUS", cx + 300, ty, 70, 30, f'toggle_{attr}', mouse, col, F.cap())

        # Save button
        self._btn("Zurück & Speichern", w // 2 - 150, h - 60, 300, S.BTN_H, 'save', mouse, C.PRIMARY, icon='←')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self._click(ev.pos)
                if a.startswith('tab_'): self.tab = int(a.split('_')[1])
                elif a == 'save': self.s.save(); return SR('back')
                elif a == 'fullscreen': return SR('fullscreen')
                elif a == 'reset_keys':
                    self.s.ground_keys = [pygame.K_d, pygame.K_j, pygame.K_DOWN]
                    self.s.air_keys = [pygame.K_f, pygame.K_k, pygame.K_UP]
                elif a == 'rebind_ground':
                    self._rebinding = 'ground'
                elif a == 'rebind_air':
                    self._rebinding = 'air'
                elif a.startswith('toggle_'):
                    attr = a[7:]
                    if hasattr(self.s, attr): setattr(self.s, attr, not getattr(self.s, attr))
                for sr, sn in self._sliders:
                    if sr.collidepoint(ev.pos): self._drag = sn; self._do_drag(sn, ev.pos[0], sr)
            if ev.type == pygame.MOUSEBUTTONUP: self._drag = None
            if ev.type == pygame.MOUSEMOTION and self._drag:
                for sr, sn in self._sliders:
                    if sn == self._drag: self._do_drag(sn, ev.pos[0], sr)
            if ev.type == pygame.KEYDOWN:
                if self._rebinding:
                    if ev.key == pygame.K_ESCAPE:
                        self._rebinding = None
                    else:
                        keys = self.s.ground_keys if self._rebinding == 'ground' else self.s.air_keys
                        if ev.key not in keys:
                            keys.append(ev.key)
                            play_ui('confirm')
                        self._rebinding = None
                    continue
                if ev.key == pygame.K_ESCAPE:
                    self.s.save(); return SR('back')
        self._cursor(mouse)
        return SR()

    def _sl(self, x, y, w, mouse, name, label, value):
        r = slider(self.scr, label, value, x, y, w, mouse); self._sliders.append((r, name))

    def _do_drag(self, name, mx, rect):
        ratio = max(0, min(1, (mx - rect.x) / rect.width)); s = self.s
        if name == 'music_volume': s.music_volume = ratio; set_music_volume(ratio)
        elif name == 'sfx_volume': s.sfx_volume = ratio; set_sfx_volume(ratio)
        elif name == 'audio_offset': s.audio_offset = int(ratio * 400 - 200)
        elif name == 'note_speed': s.note_speed = round(0.2 + ratio * 0.8, 2)
        elif name == 'approach_rate': s.approach_rate = round(1 + ratio * 9, 1)
        elif name == 'overall_difficulty': s.overall_difficulty = round(1 + ratio * 9, 1)
        elif name == 'bg_dim': s.bg_dim = ratio
        elif name == 'fps_limit': s.fps_limit = int(ratio * 480)


# ══════════════════════════════
# RESULTS
# ══════════════════════════════

class ResultsScreen(Base):
    def __init__(self, scr, result):
        super().__init__(scr); self.r = result; self._a = 0.0

    def update(self, dt, events, mouse):
        self._t += dt; self._a = min(1.0, self._a + dt * 2.0); self._btns.clear()
        w, h = self.scr.get_size()
        self.bg()
        r = self.r; a = self._a
        grade = r.get('grade', 'D')
        gcol = C.GOLD if grade == 'S' else C.SUCCESS if grade == 'A' else C.ACCENT if grade == 'B' else C.DANGER
        cleared = r.get('cleared', True)

        # Main results panel
        pw, ph = min(600, w - 60), min(440, h - 80)
        px, py = w // 2 - pw // 2, max(20, h // 2 - ph // 2 - 10)
        panel(self.scr, px, py, pw, ph, C.BG_2, C.BORDER, S.RAD_LG, int(230 * a))

        # Grade with glow
        glow_rect(self.scr, w // 2 - 60, py + 8, 120, 95, gcol, int(45 * a), 18)
        text(self.scr, grade, w // 2, py + 10, F.grade(), gcol, 'center', True, int(255 * a))

        # Status + title
        status = "CLEARED" if cleared else "FAILED"
        text(self.scr, status, w // 2, py + 115, F.bold(), C.SUCCESS if cleared else C.DANGER, 'center', alpha=int(255 * a))
        text(self.scr, r.get('song_title', r.get('title', '')), w // 2, py + 138, F.h2(), C.TEXT_2, 'center')

        # Score
        text(self.scr, f"{r.get('score', 0):,}", w // 2, py + 168, F.score(), C.PRIMARY, 'center', True)

        # Stats grid
        stats = [("Perfect", r.get('perfect', 0), C.GOLD),
                 ("Great", r.get('great', 0), C.SUCCESS),
                 ("Good", r.get('good', 0), C.ACCENT),
                 ("Miss", r.get('miss', 0), C.DANGER)]
        sx = w // 2 - 190
        for i, (label, val, col) in enumerate(stats):
            cx = sx + i * 100
            text(self.scr, str(val), cx + 45, py + 210, F.title(), col, 'center')
            text(self.scr, label, cx + 45, py + 248, F.micro(), C.TEXT_3, 'center')

        # Details
        text(self.scr, f"Max Combo: {r.get('max_combo', 0)}x  ·  Accuracy: {r.get('accuracy', 0):.1f}%",
             w // 2, py + 275, F.body(), C.TEXT_2, 'center')
        ur = r.get('unstable_rate', 0)
        text(self.scr, f"UR: {ur:.1f}  ·  Avg: {r.get('avg_error', 0):+.1f}ms  ·  Früh: {r.get('early', 0)}  Spät: {r.get('late', 0)}",
             w // 2, py + 298, F.micro(), C.TEXT_3, 'center')

        # Timing scatter
        errors = r.get('timing_errors', [])
        if errors:
            bw, bh = min(280, pw - 40), 22
            bx, by = w // 2 - bw // 2, py + 320
            panel(self.scr, bx - 2, by - 2, bw + 4, bh + 4, C.BG_0, C.BORDER, 5)
            pygame.draw.line(self.scr, C.TEXT_OFF, (bx + bw // 2, by), (bx + bw // 2, by + bh))
            for err in errors[-80:]:
                ratio = max(-1, min(1, err / 120))
                epx = bx + bw // 2 + int(ratio * bw / 2)
                col = C.GOLD if abs(err) < 35 else C.ACCENT if err > 0 else C.PRIMARY
                pygame.draw.circle(self.scr, col, (epx, by + bh // 2 + random.randint(-5, 5)), 2)

        # Buttons
        btn_y = py + ph - 60
        self._btn("Nochmal", w // 2 - 215, btn_y, 200, 46, 'retry', mouse, C.PRIMARY, icon='↻')
        self._btn("Zurück", w // 2 + 15, btn_y, 200, 46, 'back', mouse, C.BG_3, icon='←')

        # Footer
        panel(self.scr, 0, h - 30, w, 30, C.BG_0, None, 0, 160)
        text(self.scr, "R: Nochmal  ·  ESC: Zurück", w // 2, h - 24, F.micro(), C.TEXT_OFF, 'center')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a2 = self._click(ev.pos)
                if a2: return SR(a2)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return SR('back')
                if ev.key == pygame.K_r: return SR('retry')
        self._cursor(mouse)
        return SR()


# ══════════════════════════════
# MAP LOADER
# ══════════════════════════════

def load_all_maps():
    maps = []
    for p in sorted(glob.glob(os.path.join(MAP_DIR, '*.json'))):
        try:
            with open(p) as f: d = json.load(f)
            af = d.get('audio_file', d.get('audioFile', ''))
            nc = len(d.get('notes', d.get('objects', [])))
            bpm = d.get('bpm', d.get('_meta', {}).get('bpm', 0))
            title = d.get('title', d.get('songId', '?'))
            maps.append({'path': p, 'id': d.get('id', d.get('songId', '')),
                         'title': title, 'artist': d.get('artist', '?'),
                         'bpm': bpm, 'difficulty': d.get('difficulty', 5),
                         'note_count': nc, 'has_audio': os.path.exists(af),
                         'audio_path': af})
        except: pass
    for p in sorted(glob.glob('data/songs/*.json')):
        try:
            with open(p) as f: d = json.load(f)
            af = d.get('audioFile', d.get('audio_file', ''))
            if not os.path.isabs(af): af = os.path.join(os.getcwd(), af)
            for diff in d.get('difficulties', d.get('difficultyList', [])):
                cf = diff.get('chartFile', diff.get('chart_file', ''))
                nc = 0
                if cf and os.path.exists(cf):
                    try:
                        with open(cf) as f2: nc = len(json.load(f2).get('objects', []))
                    except: pass
                maps.append({'path': cf or p, 'id': d.get('id', '') + '_' + diff.get('id', ''),
                             'title': d.get('title', '?'), 'artist': d.get('artist', '?'),
                             'bpm': d.get('bpm', 0), 'difficulty': diff.get('level', 5),
                             'note_count': nc, 'has_audio': os.path.exists(af),
                             'audio_path': af, 'legacy_path': p})
        except: pass
    return maps
