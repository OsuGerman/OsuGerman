"""All game screens with professional visual styling."""
from __future__ import annotations
import os, json, glob, math, random
import pygame
from .ui_theme import C, F, S, draw_bg, draw_stars, panel, glow_rect, text, button, slider, badge
from .audio import set_music_volume, set_sfx_volume, play_sfx

MAP_DIR, SONG_DIR = 'maps', 'songs'

class SR:
    def __init__(self, action='', data=None):
        self.action = action
        self.data = data or {}
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
        draw_bg(self.scr)
        draw_stars(self.scr, self._stars, self._t)

    def _btn(self, t, x, y, w, h, a, m, c=C.PRIMARY, f=None, e=True, icon=''):
        r, hov = button(self.scr, t, x, y, w, h, m, c, f, e, icon)
        self._btns.append((r, a))
        return hov

    def _click(self, pos):
        for r, a in self._btns:
            if r.collidepoint(pos):
                play_sfx('tick')
                return a
        return ''

    def _hovering(self, pos):
        return any(r.collidepoint(pos) for r, _ in self._btns)

    def _cursor(self, pos):
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if self._hovering(pos) else pygame.SYSTEM_CURSOR_ARROW)


# ══════════════════════════════
# MAIN MENU
# ══════════════════════════════

class MainMenuScreen(Base):
    def update(self, dt, events, mouse):
        self._t += dt
        self._btns.clear()
        w, h = self.scr.get_size()
        self.bg()

        for i in range(5):
            ox = int((self._t * (10 + i * 7) + i * 180) % (w + 300) - 150)
            oy = int(h * (0.2 + i * 0.14))
            pts = [(ox + j * 12, oy + int(math.sin((ox + j * 12 + self._t * 25) * 0.018) * 15)) for j in range(25)]
            if len(pts) > 1:
                col = C.PRIMARY if i % 2 == 0 else C.ACCENT
                ls = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.lines(ls, (*col, 25), False, pts, 1)
                self.scr.blit(ls, (0, 0))

        text(self.scr, "Rhythm", w // 2 - 160, h // 5, F.hero(), C.TEXT, shadow=True)
        text(self.scr, "Dash", w // 2 + 100, h // 5, F.hero(), C.PRIMARY, shadow=True)
        text(self.scr, "Dein Rhythmus. Dein Spiel.", w // 2, h // 5 + 72, F.cap(), C.TEXT_3, 'center')

        bw, bh = 300, S.BTN_H
        bx = w // 2 - bw // 2
        by = h // 2 - 20
        self._btn("Spielen", bx, by, bw, bh, 'play', mouse, C.PRIMARY, icon='▶')
        self._btn("Editor", bx, by + 60, bw, bh, 'editor', mouse, C.SECONDARY, icon='✎')
        self._btn("Song Importieren", bx, by + 120, bw, bh, 'import', mouse, C.ACCENT_D, icon='♫')
        self._btn("Einstellungen", bx, by + 180, bw, bh, 'settings', mouse, C.BG_3, icon='⚙')

        text(self.scr, "F11 Fullscreen  ·  D/J Boden  ·  F/K Luft", w // 2, h - 28, F.micro(), C.TEXT_OFF, 'center')

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
        super().__init__(scr)
        self.maps = maps
        self.sel = 0

    def update(self, dt, events, mouse):
        self._t += dt
        self._btns.clear()
        w, h = self.scr.get_size()
        self.bg()

        panel(self.scr, 0, 0, w, 60, C.BG_1, None, 0, 240)
        text(self.scr, "Lied Auswählen", 30, 12, F.title(), C.TEXT, shadow=True)
        self._btn("Import", w - 260, 12, 100, 34, 'import', mouse, C.ACCENT_D, F.cap(), icon='♫')
        self._btn("Zurück", w - 140, 12, 110, 34, 'back', mouse, C.BG_3, F.cap(), icon='←')

        if not self.maps:
            text(self.scr, "Keine Songs. Importiere einen!", w // 2, h // 2, F.h2(), C.TEXT_3, 'center')
        else:
            y0 = 72
            for i, m in enumerate(self.maps):
                cy = y0 + i * 76
                if cy > h - 55: break
                sel = i == self.sel
                hov = pygame.Rect(20, cy, w - 40, 68).collidepoint(mouse)

                bg = C.CARD_A if sel else C.CARD_H if hov else C.CARD
                bd = C.BORDER_A if sel else C.BORDER_H if hov else C.BORDER
                if sel: glow_rect(self.scr, 20, cy, w - 40, 68, C.PRIMARY, 20, 6)
                panel(self.scr, 20, cy, w - 40, 68, bg, bd)
                self._btns.append((pygame.Rect(20, cy, w - 40, 68), f'card_{i}'))

                text(self.scr, m.get('title', '?'), 40, cy + 10, F.h2(), C.TEXT)
                info = f"{m.get('artist', '?')}  ·  {m.get('note_count', 0)} Noten  ·  {m.get('bpm', 0)} BPM"
                text(self.scr, info, 40, cy + 38, F.cap(), C.TEXT_3)

                has_a = m.get('has_audio', False)
                bx = w - 80
                badge(self.scr, "✓ Audio" if has_a else "✗ Fehlt", bx - 60, cy + 10,
                      C.SUCCESS if has_a else C.DANGER)

                diff = m.get('difficulty', 5)
                stars = "★" * min(diff, 10) + "☆" * max(0, 10 - diff)
                text(self.scr, stars, w - 80, cy + 42, F.cap(), C.GOLD, 'right')

        panel(self.scr, 0, h - 32, w, 32, C.BG_1, None, 0, 200)
        text(self.scr, "↑↓ Wählen   ENTER Spielen   E Editieren   ENTF Löschen   I Import",
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
# SETTINGS (Tabbed)
# ══════════════════════════════

class SettingsScreen(Base):
    TABS = ['Audio', 'Gameplay', 'Controls', 'Grafik']

    def __init__(self, scr, settings):
        super().__init__(scr)
        self.s = settings
        self.tab = 0

    def update(self, dt, events, mouse):
        self._t += dt
        self._btns.clear()
        self._sliders.clear()
        w, h = self.scr.get_size()
        self.bg()

        text(self.scr, "Einstellungen", w // 2, 14, F.title(), C.TEXT, 'center', True)

        tw = 130
        tx = w // 2 - len(self.TABS) * (tw + 6) // 2
        for i, t in enumerate(self.TABS):
            c = C.PRIMARY if i == self.tab else C.BG_3
            self._btn(t, tx + i * (tw + 6), 58, tw, 32, f'tab_{i}', mouse, c, F.cap())

        px, py = 50, 105
        pw, ph = w - 100, h - 190
        panel(self.scr, px, py, pw, ph, C.BG_2, C.BORDER, S.RAD_LG, 230)

        cx, cy = px + S.LG, py + S.LG
        sw = pw - S.LG * 2

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
            text(self.scr, f"Hit Windows → Perfect ±{hw['perfect']}ms  Great ±{hw['great']}ms  Good ±{hw['good']}ms  Approach {self.s.get_approach_time_ms()}ms",
                 cx, cy + 180, F.micro(), C.TEXT_OFF)
        elif self.tab == 2:
            gk = ', '.join(pygame.key.name(k).upper() for k in self.s.ground_keys)
            ak = ', '.join(pygame.key.name(k).upper() for k in self.s.air_keys)
            text(self.scr, f"Boden-Lane:", cx, cy, F.bold(), C.TEXT_2)
            badge(self.scr, gk, cx + 120, cy - 2, C.SECONDARY)
            text(self.scr, f"Luft-Lane:", cx, cy + 35, F.bold(), C.TEXT_2)
            badge(self.scr, ak, cx + 120, cy + 33, C.ACCENT_D)
            text(self.scr, "Pause: ESC   Quit: Q   Fullscreen: F11   Volume: +/−", cx, cy + 80, F.cap(), C.TEXT_3)
            self._btn("+ Boden-Taste", cx, cy + 115, 190, 34, 'rebind_ground', mouse, C.SECONDARY, F.cap())
            self._btn("+ Luft-Taste", cx + 210, cy + 115, 190, 34, 'rebind_air', mouse, C.ACCENT_D, F.cap())
            self._btn("Zurücksetzen", cx, cy + 160, 190, 34, 'reset_keys', mouse, C.DANGER_D, F.cap())
        elif self.tab == 3:
            self._sl(cx, cy, sw, mouse, 'fps_limit', "FPS-Limit", self.s.fps_limit / 480)
            v = self.s.fps_limit
            text(self.scr, f"{'Unlocked' if v == 0 else str(v)+' FPS'}", cx + 210, cy + 12, F.micro(), C.TEXT_OFF)
            self._btn("Fullscreen (F11)", cx, cy + 55, 200, 34, 'fullscreen', mouse, C.BG_3, F.cap())

        self._btn("Zurück & Speichern", w // 2 - 150, h - 68, 300, S.BTN_H, 'save', mouse, C.PRIMARY, icon='←')

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                a = self._click(ev.pos)
                if a.startswith('tab_'): self.tab = int(a.split('_')[1])
                elif a == 'save': self.s.save(); return SR('back')
                elif a == 'fullscreen': return SR('fullscreen')
                elif a == 'reset_keys':
                    self.s.ground_keys = [pygame.K_d, pygame.K_j, pygame.K_DOWN]
                    self.s.air_keys = [pygame.K_f, pygame.K_k, pygame.K_UP]
                for sr, sn in self._sliders:
                    if sr.collidepoint(ev.pos): self._drag = sn; self._do_drag(sn, ev.pos[0], sr)
            if ev.type == pygame.MOUSEBUTTONUP: self._drag = None
            if ev.type == pygame.MOUSEMOTION and self._drag:
                for sr, sn in self._sliders:
                    if sn == self._drag: self._do_drag(sn, ev.pos[0], sr)
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.s.save(); return SR('back')
        self._cursor(mouse)
        return SR()

    def _sl(self, x, y, w, mouse, name, label, value):
        r = slider(self.scr, label, value, x, y, w, mouse)
        self._sliders.append((r, name))

    def _do_drag(self, name, mx, rect):
        ratio = max(0, min(1, (mx - rect.x) / rect.width))
        s = self.s
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
        super().__init__(scr)
        self.r = result
        self._anim = 0.0

    def update(self, dt, events, mouse):
        self._t += dt
        self._anim = min(1.0, self._anim + dt * 2.5)
        self._btns.clear()
        w, h = self.scr.get_size()
        self.bg()
        r = self.r
        a = self._anim

        grade = r.get('grade', 'D')
        gcol = C.GOLD if grade == 'S' else C.SUCCESS if grade == 'A' else C.ACCENT if grade == 'B' else C.DANGER
        cleared = r.get('cleared', True)

        glow_rect(self.scr, w // 2 - 80, 10, 160, 120, gcol, int(50 * a), 20)
        text(self.scr, grade, w // 2, 15, F.grade(), gcol, 'center', True, int(255 * a))

        status = "CLEARED" if cleared else "FAILED"
        text(self.scr, status, w // 2, 125, F.bold(), C.SUCCESS if cleared else C.DANGER, 'center', alpha=int(255 * a))
        text(self.scr, r.get('song_title', r.get('title', '')), w // 2, 148, F.h2(), C.TEXT_2, 'center')

        panel(self.scr, w // 2 - 280, 178, 560, 240, C.BG_2, C.BORDER, S.RAD_LG, int(230 * a))

        text(self.scr, f"{r.get('score', 0):,}", w // 2, 190, F.score(), C.PRIMARY, 'center', True)

        stats = [("Perfect", r.get('perfect', 0), C.GOLD),
                 ("Great", r.get('great', 0), C.SUCCESS),
                 ("Good", r.get('good', 0), C.ACCENT),
                 ("Miss", r.get('miss', 0), C.DANGER)]
        sx = w // 2 - 210
        for i, (label, val, col) in enumerate(stats):
            cx = sx + i * 110
            text(self.scr, str(val), cx + 50, 230, F.title(), col, 'center')
            text(self.scr, label, cx + 50, 268, F.cap(), C.TEXT_3, 'center')

        text(self.scr, f"Max Combo: {r.get('max_combo', 0)}x", w // 2 - 110, 296, F.body(), C.TEXT_2)
        text(self.scr, f"Accuracy: {r.get('accuracy', 0):.1f}%", w // 2 + 30, 296, F.body(), C.TEXT_2)

        ur = r.get('unstable_rate', 0)
        avg = r.get('avg_error', 0)
        text(self.scr, f"UR: {ur:.1f}   Avg: {avg:+.1f}ms   Früh: {r.get('early', 0)}  Spät: {r.get('late', 0)}",
             w // 2, 325, F.micro(), C.TEXT_3, 'center')

        errors = r.get('timing_errors', [])
        if errors:
            bw, bh = 300, 24
            bx, by = w // 2 - bw // 2, 348
            panel(self.scr, bx - 2, by - 2, bw + 4, bh + 4, C.BG_0, C.BORDER, 6)
            pygame.draw.line(self.scr, C.TEXT_OFF, (bx + bw // 2, by), (bx + bw // 2, by + bh))
            for err in errors[-80:]:
                ratio = max(-1, min(1, err / 120))
                px = bx + bw // 2 + int(ratio * bw / 2)
                col = C.GOLD if abs(err) < 35 else C.ACCENT if err > 0 else C.PRIMARY
                pygame.draw.circle(self.scr, col, (px, by + bh // 2 + random.randint(-6, 6)), 2)

        self._btn("Nochmal", w // 2 - 225, 395, 210, S.BTN_H, 'retry', mouse, C.PRIMARY, icon='↻')
        self._btn("Zurück", w // 2 + 15, 395, 210, S.BTN_H, 'back', mouse, C.BG_3, icon='←')

        text(self.scr, "R: Nochmal   ESC: Zurück", w // 2, h - 25, F.micro(), C.TEXT_OFF, 'center')

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
            af = d.get('audio_file', '')
            maps.append({'path': p, 'id': d.get('id',''), 'title': d.get('title','?'),
                         'artist': d.get('artist','?'), 'bpm': d.get('bpm',0),
                         'difficulty': d.get('difficulty',5),
                         'note_count': len(d.get('notes', d.get('objects', []))),
                         'has_audio': os.path.exists(af)})
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
                maps.append({'path': cf or p, 'id': d.get('id','')+'_'+diff.get('id',''),
                             'title': d.get('title','?'), 'artist': d.get('artist','?'),
                             'bpm': d.get('bpm',0), 'difficulty': diff.get('level',5),
                             'note_count': nc, 'has_audio': os.path.exists(af)})
        except: pass
    return maps
