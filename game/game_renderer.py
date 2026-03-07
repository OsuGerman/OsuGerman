"""Complete gameplay renderer — renders GameplayManager state directly."""
from __future__ import annotations
import math
import random
import pygame
from .types import (Lane, ObjectType, ObjectState, Judgement, JUDGEMENT_COLORS,
                    ActionType, GameplayState)
from .entities import GameplayObject
from .gameplay_mgr import GameplayManager

NOTE_R = 22
HIT_X_RATIO = 0.15
GROUND_Y = 0.68
AIR_Y = 0.38

COL_BG = (10, 2, 30)
COL_GROUND = (255, 77, 141)
COL_GROUND_D = (200, 40, 100)
COL_AIR = (0, 212, 255)
COL_AIR_D = (0, 150, 190)
COL_ACCENT = (224, 64, 251)
COL_GOLD = (255, 215, 0)
COL_WHITE = (255, 255, 255)
COL_OBSTACLE = (255, 60, 60)
COL_HOLD = (180, 120, 255)
COL_MASH = (255, 180, 0)
COL_HEAVY = (255, 50, 200)
WEAPON_COLS = [COL_GOLD, (255, 180, 0), (255, 100, 50), COL_ACCENT, (0, 255, 200)]


class Particle:
    __slots__ = ('x','y','vx','vy','life','max_life','color','size')
    def __init__(self, x, y, color, size=4):
        a = random.uniform(0, math.tau)
        s = random.uniform(1.5, 5)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a)*s, math.sin(a)*s - 1.5
        self.life = self.max_life = random.uniform(0.3, 0.6)
        self.color, self.size = color, size


class JudgePop:
    __slots__ = ('text','color','x','y','life','scale')
    def __init__(self, text, color, x, y):
        self.text, self.color = text, color
        self.x, self.y = x, y
        self.life, self.scale = 0.8, 1.5


class GameRenderer:
    def __init__(self, screen: pygame.Surface):
        self.scr = screen
        self.particles: list[Particle] = []
        self.popups: list[JudgePop] = []
        self.shake = 0.0
        self.char_frame = 0
        self.char_timer = 0.0
        self.char_action = ''
        self.char_action_t = 0.0
        self._bg_cache: pygame.Surface | None = None
        self._bg_size = (0, 0)
        self._glow_cache: dict[tuple, pygame.Surface] = {}
        self._stars = [(random.random(), random.random(), random.uniform(1, 3)) for _ in range(60)]
        self._bg_scroll = 0.0
        self._fonts: dict[str, pygame.font.Font] = {}
        self._init_fonts()

    def _init_fonts(self):
        fn = 'segoe ui,arial,sans-serif'
        for name, sz, bold in [('xs',12,False),('sm',15,False),('md',20,True),
                                ('lg',36,True),('xl',52,True),('combo',48,True),
                                ('count',80,True),('grade',110,True)]:
            self._fonts[name] = pygame.font.SysFont(fn, sz, bold=bold)

    def f(self, n: str) -> pygame.font.Font:
        return self._fonts[n]

    def update(self, dt: float):
        self.shake *= 0.85
        self._bg_scroll += dt * 40
        self.char_timer += dt
        if self.char_timer > 0.12:
            self.char_frame = (self.char_frame + 1) % 4
            self.char_timer = 0
        if self.char_action_t > 0:
            self.char_action_t -= dt
            if self.char_action_t <= 0:
                self.char_action = ''
        for p in self.particles[:]:
            p.x += p.vx * dt * 60
            p.y += p.vy * dt * 60
            p.vy += 0.08
            p.life -= dt
            if p.life <= 0: self.particles.remove(p)
        for j in self.popups[:]:
            j.life -= dt
            j.y -= dt * 30
            j.scale *= 0.98
            if j.life <= 0: self.popups.remove(j)

    def render_frame(self, gm: GameplayManager):
        w, h = self.scr.get_size()
        self._draw_bg(w, h)

        if gm.screen_flash > 0:
            fl = pygame.Surface((w, h), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(gm.screen_flash * 50)))
            self.scr.blit(fl, (0, 0))

        self._draw_lanes(w, h)
        self._draw_receptors(w, h, gm.beat_pulse)
        self._draw_entities(gm, w, h)
        self._draw_character(w, h, gm.state.weapon_level)
        self._draw_particles()
        self._draw_popups()
        self._draw_hud(w, h, gm)

        if not gm.started:
            self._draw_countdown(w, h, gm.countdown)
        if gm.paused:
            self._draw_overlay(w, h, "PAUSE", "ESC: Fortsetzen   Q: Beenden", (200, 200, 200))
        if gm.failed:
            self._draw_overlay(w, h, "FAILED", "R: Nochmal   ESC: Zurück", (255, 82, 82))

    # ── Background ──

    def _draw_bg(self, w, h):
        if self._bg_cache is None or self._bg_size != (w, h):
            bg = pygame.Surface((w, h))
            for y in range(h):
                t = y / h
                r, g, b = int(8 + t * 18), int(2 + t * 8), int(25 + t * 35)
                pygame.draw.line(bg, (r, g, b), (0, y), (w, y))
            self._bg_cache = bg
            self._bg_size = (w, h)
        self.scr.blit(self._bg_cache, (0, 0))
        for xr, yr, sz in self._stars:
            sx = int((xr * w + self._bg_scroll * (0.3 + sz * 0.2)) % w)
            sy = int(yr * h)
            pygame.draw.circle(self.scr, (min(255, int(40 + sz * 25)),)*3, (sx, sy), max(1, int(sz)))
        line_y = int(h * GROUND_Y + NOTE_R + 10)
        pygame.draw.line(self.scr, COL_GROUND_D, (0, line_y), (w, line_y), 2)

    def _draw_lanes(self, w, h):
        for ratio in (AIR_Y, GROUND_Y):
            lane_s = pygame.Surface((w, 50), pygame.SRCALPHA)
            lane_s.fill((255, 255, 255, 5))
            self.scr.blit(lane_s, (0, int(h * ratio) - 25))

    def _draw_receptors(self, w, h, pulse):
        hx = int(w * HIT_X_RATIO)
        scale = 1.0 + pulse * 0.3
        alpha = int(100 + pulse * 155)
        for y_r, col in [(AIR_Y, COL_AIR), (GROUND_Y, COL_GROUND)]:
            y = int(h * y_r)
            r = int(NOTE_R * scale)
            ring = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*col, alpha), (r*2, r*2), r, 3)
            pygame.draw.circle(ring, (*col, int(alpha*0.3)), (r*2, r*2), r+8, 2)
            self.scr.blit(ring, (hx - r*2, y - r*2))

    # ── Entities ──

    def _draw_entities(self, gm: GameplayManager, w, h):
        hx = w * HIT_X_RATIO
        st = gm.song_time
        speed = gm.note_speed
        for obj in gm.active_objects:
            if obj.resolved:
                continue
            x = obj.get_screen_x(st, hx, speed)
            if x < -80 or x > w + 80:
                continue
            y = h * AIR_Y if obj.lane == Lane.AIR else h * GROUND_Y
            prox = max(0, 1 - abs(obj.hit_time - st) / 600)
            pulse = 1 + gm.beat_pulse * 0.12
            ix, iy = int(x), int(y)

            if obj.obj_type == ObjectType.GROUND_ENEMY:
                self._draw_ground_enemy(ix, iy, prox, pulse)
            elif obj.obj_type == ObjectType.AIR_ENEMY:
                self._draw_air_enemy(ix, iy, prox, pulse)
            elif obj.obj_type == ObjectType.HOLD_NOTE:
                self._draw_hold(ix, iy, obj, st, hx, speed, prox)
            elif obj.obj_type == ObjectType.OBSTACLE:
                self._draw_obstacle(ix, iy, prox, pulse)
            elif obj.obj_type == ObjectType.MASH_CHAIN:
                self._draw_mash(ix, iy, prox, pulse)
            elif obj.obj_type == ObjectType.HEAVY_ACCENT:
                self._draw_heavy(ix, iy, prox, pulse)

    def _glow(self, col):
        if col not in self._glow_cache:
            sz = NOTE_R * 4
            s = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = sz // 2
            for r in range(NOTE_R*2, NOTE_R//2, -2):
                a = int(50 * (1 - r/(NOTE_R*2)))
                pygame.draw.circle(s, (*col, a), (c, c), r)
            self._glow_cache[col] = s
        return self._glow_cache[col]

    def _draw_ground_enemy(self, x, y, prox, pulse):
        r = int((NOTE_R + prox * 4) * pulse)
        g = self._glow(COL_GROUND)
        g.set_alpha(int(30 + prox * 80))
        self.scr.blit(g, (x - g.get_width()//2, y - g.get_height()//2))
        pygame.draw.circle(self.scr, COL_GROUND, (x, y), r)
        pygame.draw.circle(self.scr, COL_GROUND_D, (x, y), int(r*0.6))
        eo = int(r * 0.25)
        er = max(2, int(r * 0.14))
        pygame.draw.circle(self.scr, COL_WHITE, (x-eo, y-eo), er)
        pygame.draw.circle(self.scr, COL_WHITE, (x+eo, y-eo), er)
        pygame.draw.circle(self.scr, (30,10,40), (x-eo+1, y-eo), max(1, er-1))
        pygame.draw.circle(self.scr, (30,10,40), (x+eo+1, y-eo), max(1, er-1))
        mw = int(r*0.4)
        pygame.draw.arc(self.scr, (30,10,40), (x-mw//2, y, mw, int(r*0.25)), 3.14, 6.28, 2)
        pygame.draw.circle(self.scr, COL_WHITE, (x, y), r, 2)

    def _draw_air_enemy(self, x, y, prox, pulse):
        r = int((NOTE_R + prox * 4) * pulse)
        g = self._glow(COL_AIR)
        g.set_alpha(int(30 + prox * 80))
        self.scr.blit(g, (x - g.get_width()//2, y - g.get_height()//2))
        pts = [(x, y-r), (x+r, y), (x, y+r), (x-r, y)]
        pygame.draw.polygon(self.scr, COL_AIR, pts)
        ir = int(r*0.5)
        pygame.draw.polygon(self.scr, COL_AIR_D, [(x,y-ir),(x+ir,y),(x,y+ir),(x-ir,y)])
        er = max(2, int(r*0.12))
        pygame.draw.circle(self.scr, COL_WHITE, (x-int(r*0.2), y-int(r*0.1)), er)
        pygame.draw.circle(self.scr, COL_WHITE, (x+int(r*0.2), y-int(r*0.1)), er)
        wl = [(x-r, y), (x-r-int(r*0.5), y-int(r*0.4)), (x-int(r*0.5), y-int(r*0.2))]
        wr = [(x+r, y), (x+r+int(r*0.5), y-int(r*0.4)), (x+int(r*0.5), y-int(r*0.2))]
        pygame.draw.polygon(self.scr, COL_AIR, wl)
        pygame.draw.polygon(self.scr, COL_AIR, wr)
        pygame.draw.polygon(self.scr, COL_WHITE, pts, 2)

    def _draw_hold(self, x, y, obj: GameplayObject, st, hx, speed, prox):
        end_x = int(hx + (obj.hit_time + obj.duration - st) * speed)
        bar_h = 14
        col = COL_HOLD
        pygame.draw.rect(self.scr, (*col, ), (min(x, end_x), int(y) - bar_h//2, abs(end_x - x), bar_h), border_radius=7)
        pygame.draw.circle(self.scr, col, (x, int(y)), NOTE_R - 2)
        pygame.draw.circle(self.scr, COL_WHITE, (x, int(y)), NOTE_R - 2, 2)
        txt = self.f('xs').render("HOLD", True, COL_WHITE)
        self.scr.blit(txt, (x - txt.get_width()//2, int(y) - txt.get_height()//2))

    def _draw_obstacle(self, x, y, prox, pulse):
        r = int((NOTE_R + 4) * pulse)
        pygame.draw.polygon(self.scr, COL_OBSTACLE,
            [(x, y-r-4), (x+r+4, y), (x, y+r+4), (x-r-4, y)])
        pygame.draw.polygon(self.scr, (180, 30, 30),
            [(x, y-r), (x+r, y), (x, y+r), (x-r, y)])
        lw = 3
        pygame.draw.line(self.scr, COL_WHITE, (x-int(r*0.3), y-int(r*0.3)), (x+int(r*0.3), y+int(r*0.3)), lw)
        pygame.draw.line(self.scr, COL_WHITE, (x+int(r*0.3), y-int(r*0.3)), (x-int(r*0.3), y+int(r*0.3)), lw)
        pygame.draw.polygon(self.scr, COL_WHITE,
            [(x, y-r-4), (x+r+4, y), (x, y+r+4), (x-r-4, y)], 2)

    def _draw_mash(self, x, y, prox, pulse):
        r = int((NOTE_R - 2) * pulse)
        for i in range(3):
            ox = i * int(r * 0.8) - int(r * 0.8)
            pygame.draw.circle(self.scr, COL_MASH, (x + ox, int(y)), r - 2)
            pygame.draw.circle(self.scr, COL_WHITE, (x + ox, int(y)), r - 2, 2)
        txt = self.f('xs').render("MASH!", True, (60, 30, 0))
        self.scr.blit(txt, (x - txt.get_width()//2, int(y) - txt.get_height()//2))

    def _draw_heavy(self, x, y, prox, pulse):
        r = int((NOTE_R + 6) * pulse)
        g = self._glow(COL_HEAVY)
        g.set_alpha(int(60 + prox * 120))
        self.scr.blit(g, (x - g.get_width()//2, int(y) - g.get_height()//2))
        pygame.draw.circle(self.scr, COL_HEAVY, (x, int(y)), r)
        pygame.draw.circle(self.scr, (255, 200, 240), (x, int(y)), int(r*0.4))
        pygame.draw.circle(self.scr, COL_WHITE, (x, int(y)), r, 3)
        for i in range(6):
            angle = pygame.time.get_ticks() * 0.003 + i * math.tau / 6
            sx = x + int(math.cos(angle) * (r + 6))
            sy = int(y) + int(math.sin(angle) * (r + 6))
            pygame.draw.circle(self.scr, COL_GOLD, (sx, sy), 3)

    # ── Character ──

    def _draw_character(self, w, h, wlv):
        cx = int(w * HIT_X_RATIO)
        by = int(h * GROUND_Y + NOTE_R + 8)
        bob = int(math.sin(self.char_frame * math.pi / 2) * 4)
        jmp = int(-55 * (self.char_action_t / 0.15)) if self.char_action == 'air' and self.char_action_t > 0 else 0
        y = by + bob + jmp
        if wlv > 0:
            ar = 20 + wlv * 6
            aura = pygame.Surface((ar*2, ar*2), pygame.SRCALPHA)
            ac = WEAPON_COLS[min(wlv, len(WEAPON_COLS)-1)]
            pygame.draw.circle(aura, (*ac, 15 + wlv*8), (ar, ar), ar)
            self.scr.blit(aura, (cx-ar, y-35-ar))
        pygame.draw.ellipse(self.scr, COL_GROUND, (cx-16, y-58, 32, 36))
        pygame.draw.circle(self.scr, COL_WHITE, (cx-5, y-43), 4)
        pygame.draw.circle(self.scr, COL_WHITE, (cx+7, y-43), 4)
        pygame.draw.circle(self.scr, COL_BG, (cx-4, y-42), 2)
        pygame.draw.circle(self.scr, COL_BG, (cx+8, y-42), 2)
        pygame.draw.rect(self.scr, COL_ACCENT, (cx-10, y-22, 20, 22))
        ph = self.char_frame * math.pi / 2
        pygame.draw.line(self.scr, COL_ACCENT, (cx-5, y), (int(cx-5+math.sin(ph)*8), y+14), 5)
        pygame.draw.line(self.scr, COL_ACCENT, (cx+5, y), (int(cx+5+math.sin(ph+math.pi)*8), y+14), 5)
        if self.char_action_t > 0:
            ext = int((0.15-self.char_action_t)/0.15*25)
            wc = WEAPON_COLS[min(wlv, len(WEAPON_COLS)-1)]
            th = 3 + wlv
            ln = 25 + wlv*8 + ext
            if self.char_action == 'ground':
                pygame.draw.line(self.scr, wc, (cx+10, y-18), (cx+ln, y-22), th)
                if wlv >= 2:
                    pygame.draw.circle(self.scr, wc, (cx+ln, y-22), 4+wlv)
            elif self.char_action == 'air':
                pygame.draw.line(self.scr, wc, (cx, y-30), (cx+ln, y-50-ext), th)

    # ── Particles + Popups ──

    def _draw_particles(self):
        for p in self.particles:
            a = max(0, min(255, int(255*p.life/p.max_life)))
            sz = max(1, int(p.size * p.life/p.max_life))
            s = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p.color, a), (sz, sz), sz)
            self.scr.blit(s, (int(p.x)-sz, int(p.y)-sz))

    def _draw_popups(self):
        for j in self.popups:
            a = max(0, min(255, int(255 * min(1, j.life/0.3))))
            sz = max(14, int(20 * j.scale))
            font = pygame.font.SysFont('segoe ui,arial,sans-serif', sz, bold=True)
            s = font.render(j.text, True, j.color)
            s.set_alpha(a)
            self.scr.blit(s, (int(j.x) - s.get_width()//2, int(j.y)))

    def spawn_particles(self, x, y, col, count=12):
        for _ in range(count):
            self.particles.append(Particle(x, y, col, random.uniform(2, 6)))

    def add_popup(self, text, color, lane: Lane):
        w, h = self.scr.get_size()
        x = w * HIT_X_RATIO + 60
        y = (h * AIR_Y if lane == Lane.AIR else h * GROUND_Y) - 30
        self.popups.append(JudgePop(text, color, x, y))

    def trigger_hit(self, lane: Lane, judgement: Judgement, wlv: int):
        w, h = self.scr.get_size()
        hx = w * HIT_X_RATIO
        y = h * AIR_Y if lane == Lane.AIR else h * GROUND_Y
        col = JUDGEMENT_COLORS[judgement]
        count = 10 + wlv * 4
        self.spawn_particles(hx, y, col, count)
        self.add_popup(judgement.value + '!', col, lane)
        self.char_action = 'air' if lane == Lane.AIR else 'ground'
        self.char_action_t = 0.15
        self.shake = 5 if judgement == Judgement.PERFECT else 2.5

    # ── HUD ──

    def _draw_hud(self, w, h, gm: GameplayManager):
        s = gm.state
        self.scr.blit(self.f('md').render(f"{s.score:,}", True, COL_WHITE), (w-150, 12))
        self.scr.blit(self.f('xs').render(f"{s.accuracy:.1f}%", True, (180,180,180)), (w-80, 40))
        if s.combo > 2:
            cs = self.f('combo').render(f"{s.combo}x", True, COL_GOLD)
            cs.set_alpha(220)
            self.scr.blit(cs, (w//2-cs.get_width()//2, int(h*0.18)))
            cl = self.f('xs').render("COMBO", True, (150,150,150))
            self.scr.blit(cl, (w//2-cl.get_width()//2, int(h*0.18)+52))
        if s.weapon_level > 0:
            wnames = ['','Schwert','Flamme','Blitz','Nova']
            wn = wnames[min(s.weapon_level, len(wnames)-1)]
            wc = WEAPON_COLS[min(s.weapon_level, len(WEAPON_COLS)-1)]
            self.scr.blit(self.f('sm').render(f"⚔ {wn} Lv.{s.weapon_level}", True, wc), (w-170, 58))
        # HP bar
        hp_w, hp_h = 180, 10
        hp_x, hp_y = 15, 15
        pygame.draw.rect(self.scr, (40,30,60), (hp_x, hp_y, hp_w, hp_h), border_radius=5)
        hw = int(hp_w * s.hp / s.hp_max)
        hc = (0,230,118) if s.hp > 50 else COL_GOLD if s.hp > 25 else (255,82,82)
        if hw > 0:
            pygame.draw.rect(self.scr, hc, (hp_x, hp_y, hw, hp_h), border_radius=5)
        self.scr.blit(self.f('xs').render(f"HP {int(s.hp)}", True, (180,180,180)), (hp_x, hp_y + 14))
        # Progress
        dur = gm.chart.objects[-1].hit_time + 2000 if gm.chart.objects else 1
        prog = min(1, gm.song_time / dur)
        bw = int(w * 0.3)
        bx = (w - bw) // 2
        by = h - 18
        pygame.draw.rect(self.scr, (40,30,60), (bx, by, bw, 5))
        if prog > 0:
            pygame.draw.rect(self.scr, COL_AIR, (bx, by, int(bw*prog), 5))
        # Timing bar
        if gm.timing_records:
            self._draw_timing_bar(w, h, gm)
        self.scr.blit(self.f('xs').render("[ESC] Pause  [+/-] Vol", True, (50,50,50)), (15, h-35))

    def _draw_timing_bar(self, w, h, gm):
        bw, bh = 180, 6
        bx = w//2 - bw//2
        by = h - 40
        pygame.draw.rect(self.scr, (30,20,50), (bx, by, bw, bh), border_radius=3)
        pygame.draw.line(self.scr, (80,80,80), (bx+bw//2, by-1), (bx+bw//2, by+bh+1))
        import time as _t
        now = _t.perf_counter()
        pw = gm.hit_windows.perfect
        for rec in gm.timing_records[-25:]:
            age = now - rec.time
            if age > 1.5: continue
            alpha = max(0, int(255*(1-age/1.5)))
            ratio = max(-1, min(1, rec.error_ms / 120))
            px = bx + bw//2 + int(ratio * bw/2)
            col = COL_GOLD if abs(rec.error_ms) <= pw else COL_AIR if rec.error_ms > 0 else COL_GROUND
            m = pygame.Surface((3, bh+2), pygame.SRCALPHA)
            m.fill((*col, alpha))
            self.scr.blit(m, (px-1, by-1))

    # ── Overlays ──

    def _draw_countdown(self, w, h, cd):
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((0,0,0,130))
        self.scr.blit(ov, (0,0))
        val = max(0, int(cd) + 1) if cd > 0 else 0
        text = str(val) if val > 0 else "LOS!"
        col = COL_GOLD if val > 0 else (0,230,118)
        s = self.f('count').render(text, True, col)
        self.scr.blit(s, (w//2-s.get_width()//2, h//2-s.get_height()//2))

    def _draw_overlay(self, w, h, title, subtitle, col):
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((0,0,0,170))
        self.scr.blit(ov, (0,0))
        s1 = self.f('xl').render(title, True, col)
        self.scr.blit(s1, (w//2-s1.get_width()//2, h//2-40))
        s2 = self.f('sm').render(subtitle, True, (180,180,180))
        self.scr.blit(s2, (w//2-s2.get_width()//2, h//2+25))
