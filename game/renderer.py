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
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 1.5
        self.life = random.uniform(0.3, 0.6)
        self.max_life = self.life
        self.color = color
        self.size = size


class JudgmentPopup:
    __slots__ = ('text', 'color', 'x', 'y', 'life', 'scale')

    def __init__(self, text: str, color: tuple, x: float, y: float):
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.life = 0.8
        self.scale = 1.5


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
        self._font_lg = None
        self._font_md = None
        self._font_sm = None
        self._font_xs = None
        self._font_combo = None
        self._font_countdown = None
        self._init_fonts()

    def _init_fonts(self):
        self._font_lg = pygame.font.SysFont('sans-serif', 48, bold=True)
        self._font_md = pygame.font.SysFont('sans-serif', 24, bold=True)
        self._font_sm = pygame.font.SysFont('sans-serif', 16)
        self._font_xs = pygame.font.SysFont('sans-serif', 13)
        self._font_combo = pygame.font.SysFont('sans-serif', 56, bold=True)
        self._font_countdown = pygame.font.SysFont('sans-serif', 96, bold=True)
        self._font_title = pygame.font.SysFont('sans-serif', 72, bold=True)
        self._font_grade = pygame.font.SysFont('sans-serif', 130, bold=True)
        self._font_score = pygame.font.SysFont('sans-serif', 52, bold=True)

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

    def draw_background(self):
        scr = self.screen
        w, h = scr.get_size()
        scr.fill(BG)
        for x_r, y_r, sz in self._stars:
            sx = int((x_r * w + self.bg_offset * (0.3 + sz * 0.2)) % w)
            sy = int(y_r * h)
            alpha = int(40 + sz * 20)
            col = ACCENT if random.random() < 0.02 else (alpha, alpha, alpha)
            pygame.draw.circle(scr, col, (sx, sy), int(sz))

        line_y = int(h * GROUND_Y_RATIO + NOTE_RADIUS + 10)
        pygame.draw.line(scr, GROUND_DARK, (0, line_y), (w, line_y), 3)
        for i in range(w // 80):
            lx = int((i * 80 - self.bg_offset * 1.5) % w)
            pygame.draw.line(scr, (30, 15, 50), (lx, line_y), (lx - 20, h), 1)

    def draw_lanes(self):
        scr = self.screen
        w, h = scr.get_size()
        hit_x = int(w * HIT_X_RATIO)
        gy = int(h * GROUND_Y_RATIO)
        ay = int(h * AIR_Y_RATIO)

        lane_surf = pygame.Surface((w, 50), pygame.SRCALPHA)
        lane_surf.fill((255, 255, 255, 6))
        scr.blit(lane_surf, (0, ay - 25))
        scr.blit(lane_surf, (0, gy - 25))

        pulse = int(8 + math.sin(pygame.time.get_ticks() * 0.005) * 4)
        hit_surf = pygame.Surface((40, h), pygame.SRCALPHA)
        hit_surf.fill((224, 64, 251, pulse))
        scr.blit(hit_surf, (hit_x - 20, 0))

    def draw_notes(self, notes: list[Note], game_time_ms: float):
        scr = self.screen
        w, h = scr.get_size()
        hit_x = w * HIT_X_RATIO
        gy = h * GROUND_Y_RATIO
        ay = h * AIR_Y_RATIO

        for note in notes:
            if note.hit or note.missed:
                continue
            diff = note.time - game_time_ms
            x = hit_x + diff * NOTE_SPEED
            if x < -50 or x > w + 50:
                continue
            y = ay if note.lane == LANE_AIR else gy
            col = AIR_COL if note.lane == LANE_AIR else GROUND_COL
            dark = AIR_DARK if note.lane == LANE_AIR else GROUND_DARK
            ix, iy = int(x), int(y)

            glow_surf = pygame.Surface((NOTE_RADIUS * 4, NOTE_RADIUS * 4), pygame.SRCALPHA)
            glow_col = (*col, 50)
            pygame.draw.circle(glow_surf, glow_col, (NOTE_RADIUS * 2, NOTE_RADIUS * 2), NOTE_RADIUS * 2)
            scr.blit(glow_surf, (ix - NOTE_RADIUS * 2, iy - NOTE_RADIUS * 2))

            if note.lane == LANE_AIR:
                pts = [(ix, iy - NOTE_RADIUS), (ix + NOTE_RADIUS, iy),
                       (ix, iy + NOTE_RADIUS), (ix - NOTE_RADIUS, iy)]
                pygame.draw.polygon(scr, col, pts)
                inner = NOTE_RADIUS * 0.55
                pts2 = [(ix, int(iy - inner)), (int(ix + inner), iy),
                        (ix, int(iy + inner)), (int(ix - inner), iy)]
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
        jump_off = 0
        if self.char_action == 'airHit' and self.char_action_timer > 0:
            jump_off = int(-55 * (self.char_action_timer / 0.15))
        y = base_y + bob + jump_off

        pygame.draw.ellipse(scr, GROUND_COL, (cx - 16, y - 58, 32, 36))
        pygame.draw.circle(scr, WHITE, (cx - 5, y - 43), 4)
        pygame.draw.circle(scr, WHITE, (cx + 7, y - 43), 4)
        pygame.draw.circle(scr, BG, (cx - 4, y - 42), 2)
        pygame.draw.circle(scr, BG, (cx + 8, y - 42), 2)
        pygame.draw.arc(scr, GROUND_COL, (cx - 5, y - 40, 14, 8), 0.1, math.pi - 0.1, 2)
        pygame.draw.rect(scr, ACCENT, (cx - 10, y - 22, 20, 22))

        phase = self.char_frame * math.pi / 2
        leg1_end = (int(cx - 5 + math.sin(phase) * 8), y + 14)
        leg2_end = (int(cx + 5 + math.sin(phase + math.pi) * 8), y + 14)
        pygame.draw.line(scr, ACCENT, (cx - 5, y), leg1_end, 5)
        pygame.draw.line(scr, ACCENT, (cx + 5, y), leg2_end, 5)

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
            font = pygame.font.SysFont('sans-serif', size, bold=True)
            surf = font.render(j.text, True, j.color)
            surf.set_alpha(alpha)
            self.screen.blit(surf, (int(j.x) - surf.get_width() // 2, int(j.y)))

    def draw_hud(self, title: str, artist: str, score: int, combo: int,
                 accuracy: float, health: float, progress: float):
        scr = self.screen
        w, h = scr.get_size()

        surf = self._font_sm.render(title, True, WHITE)
        scr.blit(surf, (20, 15))
        surf = self._font_xs.render(artist, True, (150, 150, 150))
        scr.blit(surf, (20, 35))

        score_str = f"{score:,}"
        surf = self._font_md.render(score_str, True, WHITE)
        scr.blit(surf, (w - surf.get_width() - 20, 15))

        acc_str = f"{accuracy:.1f}%"
        surf = self._font_xs.render(acc_str, True, (180, 180, 180))
        scr.blit(surf, (w - surf.get_width() - 20, 45))

        if combo > 2:
            combo_str = f"{combo}x"
            surf = self._font_combo.render(combo_str, True, PERFECT_COL)
            surf.set_alpha(220)
            scr.blit(surf, (w // 2 - surf.get_width() // 2, int(h * 0.18)))
            cs = self._font_xs.render("COMBO", True, (150, 150, 150))
            scr.blit(cs, (w // 2 - cs.get_width() // 2, int(h * 0.18) + 60))

        bar_w, bar_h = int(w * 0.3), 6
        bar_x = (w - bar_w) // 2
        bar_y = h - 22
        pygame.draw.rect(scr, (40, 30, 60), (bar_x, bar_y, bar_w, bar_h))
        pw = int(bar_w * min(1, progress))
        if pw > 0:
            pygame.draw.rect(scr, AIR_COL, (bar_x, bar_y, pw, bar_h))

        hp_w, hp_h = 150, 8
        hp_x, hp_y = 20, h - 22
        pygame.draw.rect(scr, (40, 30, 60), (hp_x, hp_y, hp_w, hp_h))
        hp_col = GREAT_COL if health > 50 else PERFECT_COL if health > 25 else MISS_COL
        hw = int(hp_w * health / 100)
        if hw > 0:
            pygame.draw.rect(scr, hp_col, (hp_x, hp_y, hw, hp_h))

        hint = self._font_xs.render("[D/J] Boden  [F/K] Luft  [ESC] Pause", True, (80, 80, 80))
        scr.blit(hint, (20, h - 42))

    def draw_countdown(self, value: int):
        scr = self.screen
        w, h = scr.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        scr.blit(overlay, (0, 0))
        if value > 0:
            surf = self._font_countdown.render(str(value), True, PERFECT_COL)
        else:
            surf = self._font_countdown.render("LOS!", True, GREAT_COL)
        scr.blit(surf, (w // 2 - surf.get_width() // 2, h // 2 - surf.get_height() // 2))

    def draw_pause(self):
        scr = self.screen
        w, h = scr.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        scr.blit(overlay, (0, 0))
        surf = self._font_lg.render("PAUSE", True, WHITE)
        scr.blit(surf, (w // 2 - surf.get_width() // 2, h // 2 - 30))
        sub = self._font_sm.render("ESC zum Fortsetzen  |  Q zum Beenden", True, (150, 150, 150))
        scr.blit(sub, (w // 2 - sub.get_width() // 2, h // 2 + 25))

    def draw_menu_bg(self):
        scr = self.screen
        w, h = scr.get_size()
        scr.fill(BG)
        t = pygame.time.get_ticks() / 1000
        for x_r, y_r, sz in self._stars:
            sx = int((x_r * w + t * (8 + sz * 6)) % w)
            sy = int(y_r * h)
            col = ACCENT if random.random() < 0.01 else (50 + int(sz * 15),) * 3
            pygame.draw.circle(scr, col, (sx, sy), int(sz))

    def draw_menu(self):
        scr = self.screen
        w, h = scr.get_size()
        self.draw_menu_bg()

        title1 = self._font_title.render("Rhythm", True, WHITE)
        title2 = self._font_title.render("Dash", True, ACCENT)
        total_w = title1.get_width() + title2.get_width() + 10
        scr.blit(title1, (w // 2 - total_w // 2, h // 4 - 30))
        scr.blit(title2, (w // 2 - total_w // 2 + title1.get_width() + 10, h // 4 - 30))

        sub = self._font_sm.render("Dein Rhythmus. Dein Spiel.", True, (130, 130, 130))
        scr.blit(sub, (w // 2 - sub.get_width() // 2, h // 4 + 50))

        buttons = [
            ("▶ Spielen", ACCENT),
            ("✎ Editor", AIR_COL),
            ("🔧 Einstellungen", (100, 100, 100)),
        ]
        for i, (text, col) in enumerate(buttons):
            bx = w // 2 - 120
            by = h // 2 + i * 60 - 20
            bw, bh = 240, 48
            pygame.draw.rect(scr, col, (bx, by, bw, bh), border_radius=12)
            surf = self._font_md.render(text, True, WHITE)
            scr.blit(surf, (bx + bw // 2 - surf.get_width() // 2, by + bh // 2 - surf.get_height() // 2))

        hint = self._font_xs.render("[D/J] Boden  [F/K] Luft  —  Importiere deine Songs im Editor!", True, (80, 80, 80))
        scr.blit(hint, (w // 2 - hint.get_width() // 2, h - 35))

        return buttons

    def draw_select(self, maps: list, selected: int):
        scr = self.screen
        w, h = scr.get_size()
        self.draw_menu_bg()

        title = self._font_lg.render("Lied Auswählen", True, WHITE)
        scr.blit(title, (40, 25))

        back = self._font_sm.render("← ESC: Zurück", True, (150, 150, 150))
        scr.blit(back, (w - back.get_width() - 20, 30))

        if not maps:
            empty = self._font_md.render("Keine Beatmaps! Erstelle eine im Editor.", True, (100, 100, 100))
            scr.blit(empty, (w // 2 - empty.get_width() // 2, h // 2))
            return

        y_start = 90
        for i, m in enumerate(maps):
            cy = y_start + i * 75
            if cy > h - 60:
                break
            sel = i == selected
            color = ACCENT if sel else (40, 30, 60)
            border = WHITE if sel else (60, 50, 80)
            pygame.draw.rect(scr, color if sel else (25, 15, 45), (30, cy, w - 60, 65), border_radius=10)
            pygame.draw.rect(scr, border, (30, cy, w - 60, 65), 2, border_radius=10)

            t = self._font_md.render(m.get('title', '?'), True, WHITE)
            scr.blit(t, (50, cy + 8))
            info = f"{m.get('artist', '?')} — {m.get('note_count', 0)} Noten — BPM {m.get('bpm', 0)}"
            s = self._font_xs.render(info, True, (150, 150, 150))
            scr.blit(s, (50, cy + 38))

            stars = "★" * min(m.get('difficulty', 5), 10) + "☆" * max(0, 10 - m.get('difficulty', 5))
            st = self._font_xs.render(stars, True, PERFECT_COL)
            scr.blit(st, (w - 200, cy + 22))

        hint = self._font_xs.render("↑↓ Auswählen  ENTER Spielen  E Editieren  ENTF Löschen", True, (80, 80, 80))
        scr.blit(hint, (w // 2 - hint.get_width() // 2, h - 30))

    def draw_result(self, result: dict):
        scr = self.screen
        w, h = scr.get_size()
        self.draw_menu_bg()

        grade = result.get('grade', 'D')
        gcol = PERFECT_COL if grade == 'S' else GREAT_COL if grade == 'A' else GOOD_COL if grade == 'B' else MISS_COL
        gs = self._font_grade.render(grade, True, gcol)
        scr.blit(gs, (w // 2 - gs.get_width() // 2, 30))

        ts = self._font_md.render(result.get('title', ''), True, (180, 180, 180))
        scr.blit(ts, (w // 2 - ts.get_width() // 2, 170))

        score_s = self._font_score.render(f"{result.get('score', 0):,}", True, ACCENT)
        scr.blit(score_s, (w // 2 - score_s.get_width() // 2, 210))

        stats = [
            ("Perfect", result.get('perfect', 0), PERFECT_COL),
            ("Great", result.get('great', 0), GREAT_COL),
            ("Good", result.get('good', 0), GOOD_COL),
            ("Miss", result.get('miss', 0), MISS_COL),
        ]
        sx = w // 2 - len(stats) * 80
        for i, (label, val, col) in enumerate(stats):
            cx = sx + i * 160 + 80
            vs = self._font_lg.render(str(val), True, col)
            scr.blit(vs, (cx - vs.get_width() // 2, 290))
            ls = self._font_xs.render(label, True, (130, 130, 130))
            scr.blit(ls, (cx - ls.get_width() // 2, 345))

        combo_s = self._font_sm.render(f"Max Combo: {result.get('max_combo', 0)}x", True, (180, 180, 180))
        acc_s = self._font_sm.render(f"Genauigkeit: {result.get('accuracy', 0):.1f}%", True, (180, 180, 180))
        scr.blit(combo_s, (w // 2 - combo_s.get_width() // 2, 390))
        scr.blit(acc_s, (w // 2 - acc_s.get_width() // 2, 420))

        btns = [("↻ Nochmal", ACCENT, w // 2 - 200, 480),
                ("← Zurück", (80, 60, 120), w // 2 + 20, 480)]
        for text, col, bx, by in btns:
            pygame.draw.rect(scr, col, (bx, by, 180, 48), border_radius=12)
            bs = self._font_md.render(text, True, WHITE)
            scr.blit(bs, (bx + 90 - bs.get_width() // 2, by + 12))

        hint = self._font_xs.render("R: Nochmal  ESC: Zurück", True, (80, 80, 80))
        scr.blit(hint, (w // 2 - hint.get_width() // 2, h - 30))

        return btns
