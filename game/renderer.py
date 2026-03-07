from __future__ import annotations
import math
import random
import pygame
from .config import *
from .beatmap import Note, LANE_AIR, LANE_GROUND


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size')

    def __init__(self, x: float, y: float, color: tuple, size: float = 4):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1.5, 5)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.5
        self.life = random.uniform(0.3, 0.6)
        self.max_life = self.life
        self.color, self.size = color, size


class JudgmentPopup:
    __slots__ = ('text', 'color', 'x', 'y', 'life', 'scale')

    def __init__(self, text: str, color: tuple, x: float, y: float):
        self.text, self.color = text, color
        self.x, self.y = x, y
        self.life, self.scale = 0.8, 1.5


def lerp_color(a: tuple, b: tuple, t: float) -> tuple:
    t = max(0, min(1, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.particles: list[Particle] = []
        self.judgments: list[JudgmentPopup] = []
        self.shake = 0.0
        self.bg_offset = 0.0
        self.char_frame = 0
        self.char_timer = 0.0
        self.char_action = 'run'
        self.char_action_timer = 0.0
        self._stars = [(random.random(), random.random(), random.uniform(1, 3)) for _ in range(60)]
        self._fonts: dict[str, pygame.font.Font] = {}
        self._init_fonts()
        self._btn_rects: list[tuple[pygame.Rect, str]] = []

    def _init_fonts(self):
        self._fonts = {
            'xs': pygame.font.SysFont('segoe ui,arial,sans-serif', 13),
            'sm': pygame.font.SysFont('segoe ui,arial,sans-serif', 16),
            'md': pygame.font.SysFont('segoe ui,arial,sans-serif', 22, bold=True),
            'lg': pygame.font.SysFont('segoe ui,arial,sans-serif', 40, bold=True),
            'xl': pygame.font.SysFont('segoe ui,arial,sans-serif', 64, bold=True),
            'title': pygame.font.SysFont('segoe ui,arial,sans-serif', 72, bold=True),
            'combo': pygame.font.SysFont('segoe ui,arial,sans-serif', 56, bold=True),
            'countdown': pygame.font.SysFont('segoe ui,arial,sans-serif', 96, bold=True),
            'grade': pygame.font.SysFont('segoe ui,arial,sans-serif', 130, bold=True),
            'score': pygame.font.SysFont('segoe ui,arial,sans-serif', 52, bold=True),
        }

    def f(self, name: str) -> pygame.font.Font:
        return self._fonts[name]

    @property
    def btn_rects(self) -> list[tuple[pygame.Rect, str]]:
        return self._btn_rects

    def update(self, dt: float):
        self.bg_offset += dt * 40
        self.shake *= 0.85
        self.char_timer += dt
        if self.char_timer > 0.12:
            self.char_frame = (self.char_frame + 1) % 4
            self.char_timer = 0
        if self.char_action_timer > 0:
            self.char_action_timer -= dt
            if self.char_action_timer <= 0:
                self.char_action = 'run'
        for p in self.particles[:]:
            p.x += p.vx * dt * 60
            p.y += p.vy * dt * 60
            p.vy += 0.08
            p.life -= dt
            if p.life <= 0:
                self.particles.remove(p)
        for j in self.judgments[:]:
            j.life -= dt
            j.y -= dt * 30
            j.scale *= 0.98
            if j.life <= 0:
                self.judgments.remove(j)

    def spawn_hit(self, x: float, y: float, color: tuple):
        for _ in range(14):
            self.particles.append(Particle(x, y, color, random.uniform(2, 6)))

    def add_judgment(self, text: str, color: tuple, lane: int):
        w, h = self.screen.get_size()
        x = w * HIT_X_RATIO + 60
        y = (h * AIR_Y_RATIO if lane == LANE_AIR else h * GROUND_Y_RATIO) - 30
        self.judgments.append(JudgmentPopup(text, color, x, y))

    def set_char_action(self, action: str):
        self.char_action = action
        self.char_action_timer = 0.15

    # --- Button helper ---
    def draw_btn(self, text: str, x: int, y: int, w: int, h: int,
                 mouse: tuple[int, int], action: str = '',
                 color: tuple = ACCENT, font_key: str = 'md') -> pygame.Rect:
        rect = pygame.Rect(x, y, w, h)
        hovered = rect.collidepoint(mouse)
        if hovered:
            col = lerp_color(color, WHITE, 0.25)
            pygame.draw.rect(self.screen, col, rect, border_radius=14)
            glow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*color, 40), (0, 0, w + 8, h + 8), border_radius=16)
            self.screen.blit(glow, (x - 4, y - 4))
        else:
            pygame.draw.rect(self.screen, color, rect, border_radius=14)
        pygame.draw.rect(self.screen, lerp_color(color, WHITE, 0.3), rect, 2, border_radius=14)
        surf = self.f(font_key).render(text, True, WHITE)
        self.screen.blit(surf, (x + w // 2 - surf.get_width() // 2, y + h // 2 - surf.get_height() // 2))
        if action:
            self._btn_rects.append((rect, action))
        return rect

    def draw_slider(self, label: str, value: float, vmin: float, vmax: float,
                    x: int, y: int, w: int, mouse: tuple[int, int],
                    suffix: str = '') -> tuple[pygame.Rect, float]:
        scr = self.screen
        lbl = self.f('sm').render(label, True, (200, 200, 200))
        scr.blit(lbl, (x, y))
        bar_x = x + 200
        bar_w = w - 200
        bar_rect = pygame.Rect(bar_x, y + 4, bar_w, 16)
        pygame.draw.rect(scr, (40, 30, 60), bar_rect, border_radius=8)
        ratio = (value - vmin) / (vmax - vmin) if vmax > vmin else 0
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(scr, ACCENT, (bar_x, y + 4, fill_w, 16), border_radius=8)
        knob_x = bar_x + fill_w
        knob_hovered = abs(mouse[0] - knob_x) < 14 and abs(mouse[1] - (y + 12)) < 14
        knob_col = WHITE if knob_hovered else (200, 200, 200)
        pygame.draw.circle(scr, knob_col, (knob_x, y + 12), 10)
        pygame.draw.circle(scr, ACCENT, (knob_x, y + 12), 10, 2)
        if suffix == 'ms':
            val_str = f"{value:.0f}{suffix}"
        elif vmax > 1.5:
            val_str = f"{value:.1f}"
        else:
            val_str = f"{int(value * 100)}%"
        vs = self.f('xs').render(val_str, True, (160, 160, 160))
        scr.blit(vs, (bar_x + bar_w + 10, y + 2))
        return bar_rect, ratio

    # --- Backgrounds ---
    def draw_menu_bg(self):
        scr = self.screen
        w, h = scr.get_size()
        scr.fill(BG)
        t = pygame.time.get_ticks() / 1000
        for x_r, y_r, sz in self._stars:
            sx = int((x_r * w + t * (8 + sz * 6)) % w)
            sy = int(y_r * h)
            alpha = min(255, int(40 + sz * 25))
            col = (alpha, alpha, alpha)
            if random.random() < 0.005:
                col = ACCENT
            pygame.draw.circle(scr, col, (sx, sy), int(sz))
        for i in range(3):
            wave_x = int((t * (15 + i * 10) + i * 200) % (w + 300) - 150)
            wave_y = int(h * (0.35 + i * 0.15))
            pts = []
            for px in range(0, 260, 10):
                py = wave_y + int(math.sin((px + t * 40) * 0.03) * 15)
                pts.append((wave_x + px, py))
            if len(pts) > 1:
                pygame.draw.lines(scr, (*ACCENT, ), False, pts, 1)

    def draw_background(self):
        scr = self.screen
        w, h = scr.get_size()
        scr.fill(BG)
        for x_r, y_r, sz in self._stars:
            sx = int((x_r * w + self.bg_offset * (0.3 + sz * 0.2)) % w)
            sy = int(y_r * h)
            alpha = int(40 + sz * 20)
            pygame.draw.circle(scr, (alpha, alpha, alpha), (sx, sy), int(sz))
        line_y = int(h * GROUND_Y_RATIO + NOTE_RADIUS + 10)
        pygame.draw.line(scr, GROUND_DARK, (0, line_y), (w, line_y), 3)
        for i in range(w // 80):
            lx = int((i * 80 - self.bg_offset * 1.5) % w)
            pygame.draw.line(scr, (30, 15, 50), (lx, line_y), (lx - 20, h), 1)

    # --- Screens ---
    def draw_menu(self, mouse: tuple[int, int], sel: int):
        scr = self.screen
        w, h = scr.get_size()
        self._btn_rects = []
        self.draw_menu_bg()

        t1 = self.f('title').render("Rhythm", True, WHITE)
        t2 = self.f('title').render("Dash", True, ACCENT)
        tw = t1.get_width() + t2.get_width() + 12
        scr.blit(t1, (w // 2 - tw // 2, h // 5 - 20))
        scr.blit(t2, (w // 2 - tw // 2 + t1.get_width() + 12, h // 5 - 20))
        sub = self.f('sm').render("Dein Rhythmus. Dein Spiel.", True, (130, 130, 130))
        scr.blit(sub, (w // 2 - sub.get_width() // 2, h // 5 + 60))

        buttons = [
            ("▶  Spielen", ACCENT, 'play'),
            ("✎  Editor", ACCENT2, 'editor'),
            ("♫  Song Importieren", (0, 160, 200), 'import'),
            ("⚙  Einstellungen", (70, 55, 110), 'settings'),
        ]
        bw, bh = 280, 50
        start_y = h // 2 - 20
        for i, (text, col, action) in enumerate(buttons):
            bx = w // 2 - bw // 2
            by = start_y + i * 62
            self.draw_btn(text, bx, by, bw, bh, mouse, action, col)
            if i == sel:
                pygame.draw.rect(scr, WHITE, (bx - 3, by - 3, bw + 6, bh + 6), 2, border_radius=16)

        hint = self.f('xs').render("[D/J] Boden   [F/K] Luft   —   Lade deine eigenen Songs!", True, (70, 70, 70))
        scr.blit(hint, (w // 2 - hint.get_width() // 2, h - 35))

    def draw_select(self, maps: list, selected: int, mouse: tuple[int, int]):
        scr = self.screen
        w, h = scr.get_size()
        self._btn_rects = []
        self.draw_menu_bg()

        title = self.f('lg').render("Lied Auswählen", True, WHITE)
        scr.blit(title, (40, 20))

        self.draw_btn("← Zurück", w - 140, 20, 120, 36, mouse, 'back', (70, 55, 110), 'sm')
        self.draw_btn("♫ Import", w - 280, 20, 120, 36, mouse, 'import', (0, 160, 200), 'sm')

        if not maps:
            empty = self.f('md').render("Keine Songs! Importiere einen Song oder erstelle eine Map.", True, (100, 100, 100))
            scr.blit(empty, (w // 2 - empty.get_width() // 2, h // 2))
            return

        y_start = 80
        for i, m in enumerate(maps):
            cy = y_start + i * 72
            if cy > h - 50:
                break
            card = pygame.Rect(30, cy, w - 60, 62)
            sel = i == selected
            hovered = card.collidepoint(mouse)
            bg_col = BTN_ACTIVE if sel else BTN_HOVER if hovered else BTN_BG
            pygame.draw.rect(scr, bg_col, card, border_radius=12)
            border_col = ACCENT if sel else (80, 70, 110) if hovered else (50, 40, 70)
            pygame.draw.rect(scr, border_col, card, 2, border_radius=12)
            self._btn_rects.append((card, f'select_{i}'))

            t = self.f('md').render(m.get('title', '?'), True, WHITE)
            scr.blit(t, (50, cy + 8))
            has_audio = m.get('has_audio', False)
            audio_tag = "✓ Audio" if has_audio else "✗ Kein Audio"
            audio_col = GREAT_COL if has_audio else MISS_COL
            info = f"{m.get('artist', '?')}  ·  {m.get('note_count', 0)} Noten  ·  BPM {m.get('bpm', 0)}"
            s = self.f('xs').render(info, True, (150, 150, 150))
            scr.blit(s, (50, cy + 36))
            at = self.f('xs').render(audio_tag, True, audio_col)
            scr.blit(at, (w - 160, cy + 10))
            stars = "★" * min(m.get('difficulty', 5), 10) + "☆" * max(0, 10 - m.get('difficulty', 5))
            st = self.f('xs').render(stars, True, PERFECT_COL)
            scr.blit(st, (w - 200, cy + 36))

        hint = self.f('xs').render("↑↓ Auswählen   ENTER/Doppelklick Spielen   E Editieren   ENTF Löschen", True, (70, 70, 70))
        scr.blit(hint, (w // 2 - hint.get_width() // 2, h - 25))

    def draw_settings(self, settings, mouse: tuple[int, int], dragging: str | None):
        scr = self.screen
        w, h = scr.get_size()
        self._btn_rects = []
        self.draw_menu_bg()

        title = self.f('lg').render("Einstellungen", True, WHITE)
        scr.blit(title, (w // 2 - title.get_width() // 2, 30))

        cx = w // 2 - 250
        sw = 500
        y = 110
        gap = 55

        r1, _ = self.draw_slider("Musik-Lautstärke", settings.music_volume, 0, 1, cx, y, sw, mouse)
        self._btn_rects.append((r1, 'slider_music_volume'))
        y += gap

        r2, _ = self.draw_slider("SFX-Lautstärke", settings.sfx_volume, 0, 1, cx, y, sw, mouse)
        self._btn_rects.append((r2, 'slider_sfx_volume'))
        y += gap

        r3, _ = self.draw_slider("Audio-Offset", settings.audio_offset, -200, 200, cx, y, sw, mouse, 'ms')
        self._btn_rects.append((r3, 'slider_audio_offset'))
        y += gap

        r4, _ = self.draw_slider("Noten-Geschwindigkeit", settings.note_speed, 0.2, 1.0, cx, y, sw, mouse)
        self._btn_rects.append((r4, 'slider_note_speed'))
        y += gap

        r5, _ = self.draw_slider("Hintergrund-Dim", settings.bg_dim, 0, 1, cx, y, sw, mouse)
        self._btn_rects.append((r5, 'slider_bg_dim'))
        y += gap

        r6, _ = self.draw_slider("Approach Rate (AR)", settings.approach_rate, 1, 10, cx, y, sw, mouse)
        self._btn_rects.append((r6, 'slider_approach_rate'))
        y += gap

        r7, _ = self.draw_slider("Overall Difficulty (OD)", settings.overall_difficulty, 1, 10, cx, y, sw, mouse)
        self._btn_rects.append((r7, 'slider_overall_difficulty'))
        y += gap + 10

        hw = settings.get_hit_windows()
        windows = self.f('xs').render(
            f"Hit Windows → Perfect: ±{hw['perfect']}ms  Great: ±{hw['great']}ms  Good: ±{hw['good']}ms   Approach: {settings.get_approach_time_ms()}ms",
            True, (120, 100, 150))
        scr.blit(windows, (cx, y))
        y += 25

        pygame.draw.line(scr, (50, 40, 70), (cx, y), (cx + sw, y), 1)
        y += 20

        key_info = [
            ("Boden-Lane:", "D / J / Pfeil-Runter"),
            ("Luft-Lane:", "F / K / Pfeil-Hoch"),
            ("Pause:", "ESC"),
            ("Beenden (Pause):", "Q"),
        ]
        for label, keys in key_info:
            ls = self.f('sm').render(label, True, (180, 180, 180))
            ks = self.f('sm').render(keys, True, ACCENT)
            scr.blit(ls, (cx, y))
            scr.blit(ks, (cx + 200, y))
            y += 30

        y += 20
        self.draw_btn("← Zurück & Speichern", w // 2 - 140, y, 280, 48, mouse, 'save_back', ACCENT)

    def draw_result(self, result: dict, mouse: tuple[int, int]):
        scr = self.screen
        w, h = scr.get_size()
        self._btn_rects = []
        self.draw_menu_bg()

        grade = result.get('grade', 'D')
        gcol = PERFECT_COL if grade == 'S' else GREAT_COL if grade == 'A' else GOOD_COL if grade == 'B' else MISS_COL
        gs = self.f('grade').render(grade, True, gcol)
        scr.blit(gs, (w // 2 - gs.get_width() // 2, 20))

        ts = self.f('md').render(result.get('title', ''), True, (180, 180, 180))
        scr.blit(ts, (w // 2 - ts.get_width() // 2, 160))

        score_s = self.f('score').render(f"{result.get('score', 0):,}", True, ACCENT)
        scr.blit(score_s, (w // 2 - score_s.get_width() // 2, 195))

        stats = [
            ("Perfect", result.get('perfect', 0), PERFECT_COL),
            ("Great", result.get('great', 0), GREAT_COL),
            ("Good", result.get('good', 0), GOOD_COL),
            ("Miss", result.get('miss', 0), MISS_COL),
        ]
        sx = w // 2 - len(stats) * 80
        for i, (label, val, col) in enumerate(stats):
            cx_s = sx + i * 160 + 80
            vs = self.f('lg').render(str(val), True, col)
            scr.blit(vs, (cx_s - vs.get_width() // 2, 270))
            ls = self.f('xs').render(label, True, (130, 130, 130))
            scr.blit(ls, (cx_s - ls.get_width() // 2, 320))

        combo_s = self.f('sm').render(f"Max Combo: {result.get('max_combo', 0)}x", True, (180, 180, 180))
        acc_s = self.f('sm').render(f"Genauigkeit: {result.get('accuracy', 0):.1f}%", True, (180, 180, 180))
        scr.blit(combo_s, (w // 2 - combo_s.get_width() // 2, 360))
        scr.blit(acc_s, (w // 2 - acc_s.get_width() // 2, 385))

        ur = result.get('unstable_rate', 0)
        avg_err = result.get('avg_error', 0)
        early = result.get('early', 0)
        late = result.get('late', 0)
        ur_s = self.f('xs').render(f"Unstable Rate: {ur:.1f}   Avg Error: {avg_err:+.1f}ms   Früh: {early}  Spät: {late}", True, (140, 140, 140))
        scr.blit(ur_s, (w // 2 - ur_s.get_width() // 2, 410))

        errors = result.get('timing_errors', [])
        if errors:
            bar_w, bar_h = 300, 30
            bar_x = w // 2 - bar_w // 2
            bar_y = 435
            pygame.draw.rect(scr, (25, 15, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            pygame.draw.line(scr, (80, 80, 80), (bar_x + bar_w // 2, bar_y), (bar_x + bar_w // 2, bar_y + bar_h), 1)
            max_e = 150
            for err in errors[-100:]:
                ratio = max(-1, min(1, err / max_e))
                px = bar_x + bar_w // 2 + int(ratio * bar_w / 2)
                col = PERFECT_COL if abs(err) < 45 else AIR_COL if err > 0 else GROUND_COL
                pygame.draw.circle(scr, col, (px, bar_y + bar_h // 2 + random.randint(-8, 8)), 2)

        btn_y = 480
        self.draw_btn("↻ Nochmal", w // 2 - 210, btn_y, 195, 48, mouse, 'retry', ACCENT)
        self.draw_btn("← Zurück", w // 2 + 15, btn_y, 195, 48, mouse, 'back', (70, 55, 110))

        hint = self.f('xs').render("R: Nochmal   ESC: Zurück", True, (70, 70, 70))
        scr.blit(hint, (w // 2 - hint.get_width() // 2, h - 25))

    # --- Game rendering ---
    def draw_receptors(self, beat_pulse: float = 0):
        scr = self.screen
        w, h = scr.get_size()
        hit_x = int(w * HIT_X_RATIO)
        gy, ay = int(h * GROUND_Y_RATIO), int(h * AIR_Y_RATIO)
        pulse_scale = 1.0 + beat_pulse * 0.25
        pulse_alpha = int(120 + beat_pulse * 135)
        for y, col in [(ay, AIR_COL), (gy, GROUND_COL)]:
            r = int(NOTE_RADIUS * pulse_scale)
            ring = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*col, pulse_alpha), (r * 2, r * 2), r, 3)
            pygame.draw.circle(ring, (*col, int(pulse_alpha * 0.3)), (r * 2, r * 2), r + 6, 2)
            scr.blit(ring, (hit_x - r * 2, y - r * 2))
            inner = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(inner, (*col, 60), (8, 8), 6)
            scr.blit(inner, (hit_x - 8, y - 8))

    def draw_timing_bar(self, timing_hits, perfect_window: float):
        scr = self.screen
        w, h = scr.get_size()
        bar_w, bar_h = 200, 8
        bar_x = w // 2 - bar_w // 2
        bar_y = h - 50
        pygame.draw.rect(scr, (30, 20, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.line(scr, (100, 100, 100), (bar_x + bar_w // 2, bar_y - 2),
                         (bar_x + bar_w // 2, bar_y + bar_h + 2), 1)
        now = pygame.time.get_ticks()
        max_err = 150
        for hit in timing_hits[-30:]:
            age = (now - hit.time) / 1000
            if age > 2:
                continue
            alpha = max(0, int(255 * (1 - age / 2)))
            ratio = max(-1, min(1, hit.error_ms / max_err))
            px = bar_x + bar_w // 2 + int(ratio * bar_w / 2)
            if abs(hit.error_ms) <= perfect_window:
                col = (*PERFECT_COL, alpha)
            elif hit.error_ms > 0:
                col = (*AIR_COL, alpha)
            else:
                col = (*GROUND_COL, alpha)
            mark = pygame.Surface((4, bar_h + 4), pygame.SRCALPHA)
            pygame.draw.rect(mark, col, (0, 0, 4, bar_h + 4), border_radius=2)
            scr.blit(mark, (px - 2, bar_y - 2))
        early = self.f('xs').render("Früh", True, (80, 80, 80))
        late = self.f('xs').render("Spät", True, (80, 80, 80))
        scr.blit(early, (bar_x - early.get_width() - 5, bar_y - 2))
        scr.blit(late, (bar_x + bar_w + 5, bar_y - 2))

    def draw_fail(self):
        scr = self.screen
        w, h = scr.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((80, 0, 0, 180))
        scr.blit(overlay, (0, 0))
        fail_text = self.f('grade').render("FAILED", True, MISS_COL)
        scr.blit(fail_text, (w // 2 - fail_text.get_width() // 2, h // 3 - 40))
        sub = self.f('md').render("HP auf 0 gefallen!", True, (200, 150, 150))
        scr.blit(sub, (w // 2 - sub.get_width() // 2, h // 3 + 80))
        hint = self.f('sm').render("R: Nochmal   ESC: Zurück", True, (180, 130, 130))
        scr.blit(hint, (w // 2 - hint.get_width() // 2, h // 2 + 40))

    def draw_lanes(self):
        scr = self.screen
        w, h = scr.get_size()
        hit_x = int(w * HIT_X_RATIO)
        gy, ay = int(h * GROUND_Y_RATIO), int(h * AIR_Y_RATIO)
        lane_surf = pygame.Surface((w, 50), pygame.SRCALPHA)
        lane_surf.fill((255, 255, 255, 6))
        scr.blit(lane_surf, (0, ay - 25))
        scr.blit(lane_surf, (0, gy - 25))
        pulse = int(8 + math.sin(pygame.time.get_ticks() * 0.005) * 4)
        hit_surf = pygame.Surface((40, h), pygame.SRCALPHA)
        hit_surf.fill((224, 64, 251, pulse))
        scr.blit(hit_surf, (hit_x - 20, 0))

    def draw_notes(self, notes: list[Note], game_time_ms: float, speed: float):
        scr = self.screen
        w, h = scr.get_size()
        hit_x = w * HIT_X_RATIO
        gy, ay = h * GROUND_Y_RATIO, h * AIR_Y_RATIO
        for note in notes:
            if note.hit or note.missed:
                continue
            diff = note.time - game_time_ms
            x = hit_x + diff * speed
            if x < -50 or x > w + 50:
                continue
            y = ay if note.lane == LANE_AIR else gy
            col = AIR_COL if note.lane == LANE_AIR else GROUND_COL
            dark = AIR_DARK if note.lane == LANE_AIR else GROUND_DARK
            ix, iy = int(x), int(y)
            glow_surf = pygame.Surface((NOTE_RADIUS * 4, NOTE_RADIUS * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*col, 50), (NOTE_RADIUS * 2, NOTE_RADIUS * 2), NOTE_RADIUS * 2)
            scr.blit(glow_surf, (ix - NOTE_RADIUS * 2, iy - NOTE_RADIUS * 2))
            if note.lane == LANE_AIR:
                pts = [(ix, iy - NOTE_RADIUS), (ix + NOTE_RADIUS, iy), (ix, iy + NOTE_RADIUS), (ix - NOTE_RADIUS, iy)]
                pygame.draw.polygon(scr, col, pts)
                inner = int(NOTE_RADIUS * 0.55)
                pts2 = [(ix, iy - inner), (ix + inner, iy), (ix, iy + inner), (ix - inner, iy)]
                pygame.draw.polygon(scr, dark, pts2)
                pygame.draw.polygon(scr, WHITE, pts, 2)
            else:
                pygame.draw.circle(scr, col, (ix, iy), NOTE_RADIUS)
                pygame.draw.circle(scr, dark, (ix, iy), int(NOTE_RADIUS * 0.55))
                pygame.draw.circle(scr, WHITE, (ix, iy), NOTE_RADIUS, 2)

    def draw_character(self):
        scr = self.screen
        w, h = scr.get_size()
        cx = int(w * HIT_X_RATIO)
        base_y = int(h * GROUND_Y_RATIO + NOTE_RADIUS + 8)
        bob = int(math.sin(self.char_frame * math.pi / 2) * 4)
        jump_off = int(-55 * (self.char_action_timer / 0.15)) if self.char_action == 'airHit' and self.char_action_timer > 0 else 0
        y = base_y + bob + jump_off
        pygame.draw.ellipse(scr, GROUND_COL, (cx - 16, y - 58, 32, 36))
        pygame.draw.circle(scr, WHITE, (cx - 5, y - 43), 4)
        pygame.draw.circle(scr, WHITE, (cx + 7, y - 43), 4)
        pygame.draw.circle(scr, BG, (cx - 4, y - 42), 2)
        pygame.draw.circle(scr, BG, (cx + 8, y - 42), 2)
        pygame.draw.arc(scr, GROUND_COL, (cx - 5, y - 40, 14, 8), 0.1, math.pi - 0.1, 2)
        pygame.draw.rect(scr, ACCENT, (cx - 10, y - 22, 20, 22))
        phase = self.char_frame * math.pi / 2
        pygame.draw.line(scr, ACCENT, (cx - 5, y), (int(cx - 5 + math.sin(phase) * 8), y + 14), 5)
        pygame.draw.line(scr, ACCENT, (cx + 5, y), (int(cx + 5 + math.sin(phase + math.pi) * 8), y + 14), 5)
        if self.char_action == 'groundHit' and self.char_action_timer > 0:
            ext = int((0.15 - self.char_action_timer) / 0.15 * 20)
            pygame.draw.line(scr, PERFECT_COL, (cx + 10, y - 18), (cx + 30 + ext, y - 25), 4)
            pygame.draw.circle(scr, PERFECT_COL, (cx + 30 + ext, y - 25), 5)

    def draw_particles(self):
        scr = self.screen
        for p in self.particles:
            alpha = max(0, min(255, int(255 * p.life / p.max_life)))
            sz = max(1, int(p.size * p.life / p.max_life))
            surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p.color, alpha), (sz, sz), sz)
            scr.blit(surf, (int(p.x) - sz, int(p.y) - sz))

    def draw_judgments(self):
        for j in self.judgments:
            alpha = max(0, min(255, int(255 * j.life / 0.3)))
            size = max(14, int(22 * j.scale))
            font = pygame.font.SysFont('segoe ui,arial,sans-serif', size, bold=True)
            surf = font.render(j.text, True, j.color)
            surf.set_alpha(alpha)
            self.screen.blit(surf, (int(j.x) - surf.get_width() // 2, int(j.y)))

    def draw_hud(self, title: str, artist: str, score: int, combo: int,
                 accuracy: float, health: float, progress: float):
        scr = self.screen
        w, h = scr.get_size()
        scr.blit(self.f('sm').render(title, True, WHITE), (20, 15))
        scr.blit(self.f('xs').render(artist, True, (150, 150, 150)), (20, 35))
        score_s = self.f('md').render(f"{score:,}", True, WHITE)
        scr.blit(score_s, (w - score_s.get_width() - 20, 15))
        acc_s = self.f('xs').render(f"{accuracy:.1f}%", True, (180, 180, 180))
        scr.blit(acc_s, (w - acc_s.get_width() - 20, 42))
        if combo > 2:
            cs = self.f('combo').render(f"{combo}x", True, PERFECT_COL)
            cs.set_alpha(220)
            scr.blit(cs, (w // 2 - cs.get_width() // 2, int(h * 0.18)))
            cl = self.f('xs').render("COMBO", True, (150, 150, 150))
            scr.blit(cl, (w // 2 - cl.get_width() // 2, int(h * 0.18) + 60))
        bar_w, bar_h = int(w * 0.3), 6
        bar_x, bar_y = (w - bar_w) // 2, h - 22
        pygame.draw.rect(scr, (40, 30, 60), (bar_x, bar_y, bar_w, bar_h))
        pw = int(bar_w * min(1, progress))
        if pw > 0:
            pygame.draw.rect(scr, AIR_COL, (bar_x, bar_y, pw, bar_h))
        hp_w, hp_x, hp_y = 150, 20, h - 22
        pygame.draw.rect(scr, (40, 30, 60), (hp_x, hp_y, hp_w, 8))
        hp_col = GREAT_COL if health > 50 else PERFECT_COL if health > 25 else MISS_COL
        hw = int(hp_w * health / 100)
        if hw > 0:
            pygame.draw.rect(scr, hp_col, (hp_x, hp_y, hw, 8))
        scr.blit(self.f('xs').render("[D/J] Boden  [F/K] Luft  [ESC] Pause", True, (70, 70, 70)), (20, h - 42))

    def draw_countdown(self, value: int):
        scr = self.screen
        w, h = scr.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        scr.blit(overlay, (0, 0))
        text = str(value) if value > 0 else "LOS!"
        col = PERFECT_COL if value > 0 else GREAT_COL
        surf = self.f('countdown').render(text, True, col)
        scr.blit(surf, (w // 2 - surf.get_width() // 2, h // 2 - surf.get_height() // 2))

    def draw_pause(self):
        scr = self.screen
        w, h = scr.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        scr.blit(overlay, (0, 0))
        scr.blit(self.f('lg').render("PAUSE", True, WHITE), (w // 2 - 60, h // 2 - 30))
        scr.blit(self.f('sm').render("ESC: Fortsetzen   Q: Beenden", True, (150, 150, 150)), (w // 2 - 120, h // 2 + 25))
