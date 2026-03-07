"""UI Design System — Colors, Typography, Spacing, Draw Helpers."""
import pygame
import math

class C:
    PRIMARY = (255, 60, 130)
    PRIMARY_L = (255, 100, 160)
    PRIMARY_D = (200, 30, 90)
    SECONDARY = (110, 60, 255)
    SECONDARY_L = (140, 100, 255)
    ACCENT = (0, 210, 255)
    ACCENT_D = (0, 160, 210)
    GOLD = (255, 210, 50)
    GOLD_L = (255, 230, 100)
    SUCCESS = (0, 220, 110)
    DANGER = (255, 70, 70)
    DANGER_D = (200, 40, 40)

    BG_0 = (6, 2, 18)
    BG_1 = (12, 5, 32)
    BG_2 = (20, 10, 48)
    BG_3 = (30, 16, 65)
    CARD = (28, 14, 58)
    CARD_H = (42, 24, 82)
    CARD_A = (55, 32, 100)

    TEXT = (245, 240, 255)
    TEXT_2 = (180, 170, 210)
    TEXT_3 = (110, 100, 145)
    TEXT_OFF = (55, 48, 75)

    BORDER = (50, 35, 85)
    BORDER_H = (90, 65, 140)
    BORDER_A = (255, 60, 130)


class F:
    _c: dict[tuple, pygame.font.Font] = {}
    N = 'segoe ui,arial,sans-serif'

    @classmethod
    def g(cls, s, b=False):
        k = (s, b)
        if k not in cls._c: cls._c[k] = pygame.font.SysFont(cls.N, s, bold=b)
        return cls._c[k]

    @classmethod
    def hero(cls): return cls.g(60, True)
    @classmethod
    def title(cls): return cls.g(34, True)
    @classmethod
    def h2(cls): return cls.g(22, True)
    @classmethod
    def body(cls): return cls.g(16)
    @classmethod
    def bold(cls): return cls.g(16, True)
    @classmethod
    def cap(cls): return cls.g(13)
    @classmethod
    def micro(cls): return cls.g(11)
    @classmethod
    def combo(cls): return cls.g(46, True)
    @classmethod
    def score(cls): return cls.g(28, True)
    @classmethod
    def grade(cls): return cls.g(100, True)
    @classmethod
    def countdown(cls): return cls.g(80, True)


S = type('S', (), {'XS':4,'SM':8,'MD':16,'LG':24,'XL':32,'XXL':48,'RAD':14,'RAD_SM':10,'RAD_LG':18,'BTN_H':50,'BTN_SM':36})()

_bg_cache = {}

def draw_bg(scr: pygame.Surface):
    w, h = scr.get_size()
    key = (w, h)
    if key not in _bg_cache:
        bg = pygame.Surface((w, h))
        for y in range(h):
            t = y / h
            r = int(6 + t * 14)
            g = int(2 + t * 6)
            b = int(18 + t * 30)
            pygame.draw.line(bg, (r, g, b), (0, y), (w, y))
        _bg_cache[key] = bg
    scr.blit(_bg_cache[key], (0, 0))


def draw_stars(scr, stars, t):
    w, h = scr.get_size()
    for xr, yr, sz in stars:
        sx = int((xr * w + t * (5 + sz * 4)) % w)
        sy = int(yr * h)
        a = min(255, int(30 + sz * 22))
        pygame.draw.circle(scr, (a, a, a + 10), (sx, sy), max(1, int(sz)))


def panel(scr, x, y, w, h, bg=C.BG_2, border=C.BORDER, rad=S.RAD, alpha=235):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*bg, alpha), (0, 0, w, h), border_radius=rad)
    if border:
        pygame.draw.rect(s, (*border, min(255, alpha - 20)), (0, 0, w, h), 2, border_radius=rad)
    scr.blit(s, (x, y))


def glow_rect(scr, x, y, w, h, color, intensity=30, spread=6):
    gs = pygame.Surface((w + spread*2, h + spread*2), pygame.SRCALPHA)
    pygame.draw.rect(gs, (*color, intensity), (0, 0, w+spread*2, h+spread*2), border_radius=S.RAD+spread//2)
    scr.blit(gs, (x - spread, y - spread))


def text(scr, txt, x, y, font=None, color=C.TEXT, align='left', shadow=False, alpha=255):
    if font is None: font = F.body()
    r = font.render(str(txt), True, color)
    if alpha < 255: r.set_alpha(alpha)
    rx = x - r.get_width() // 2 if align == 'center' else x - r.get_width() if align == 'right' else x
    if shadow:
        sh = font.render(str(txt), True, (0, 0, 0))
        sh.set_alpha(min(alpha, 80))
        scr.blit(sh, (rx + 2, y + 2))
    scr.blit(r, (rx, y))
    return r.get_width(), r.get_height()


def button(scr, txt, x, y, w, h, mouse, color=C.PRIMARY, font=None, enabled=True, icon=''):
    if font is None: font = F.bold()
    rect = pygame.Rect(x, y, w, h)
    hov = rect.collidepoint(mouse) and enabled

    if not enabled:
        bg, tc = C.BG_2, C.TEXT_OFF
    elif hov:
        bg = tuple(min(255, c + 35) for c in color)
        tc = C.TEXT
        glow_rect(scr, x, y, w, h, color, 40, 8)
    else:
        bg, tc = color, C.TEXT

    bs = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(bs, (*bg, 230 if enabled else 100), (0, 0, w, h), border_radius=S.RAD)
    bc = tuple(min(255, c + 50) for c in bg)
    pygame.draw.rect(bs, (*bc, 140), (0, 0, w, h), 2, border_radius=S.RAD)
    if hov:
        hl = pygame.Surface((w, h // 3), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 18))
        bs.blit(hl, (0, 0))
    scr.blit(bs, (x, y))

    label = (icon + '  ' + txt) if icon else txt
    r = font.render(label, True, tc)
    scr.blit(r, (x + w // 2 - r.get_width() // 2, y + h // 2 - r.get_height() // 2))
    return rect, hov


def slider(scr, label, value, x, y, w, mouse, color=C.PRIMARY):
    text(scr, label, x, y + 3, F.body(), C.TEXT_2)
    bx, bw, bh = x + 210, w - 260, 8
    by = y + 10
    rect = pygame.Rect(bx, by - 6, bw, bh + 12)
    pygame.draw.rect(scr, C.BG_0, (bx, by, bw, bh), border_radius=4)
    fill = int(bw * max(0, min(1, value)))
    if fill > 0:
        pygame.draw.rect(scr, color, (bx, by, fill, bh), border_radius=4)
    kx = bx + fill
    ky = by + bh // 2
    hov = abs(mouse[0] - kx) < 14 and abs(mouse[1] - ky) < 14
    kr = 9 if hov else 7
    if hov:
        pygame.draw.circle(scr, (*color, 40), (kx, ky), kr + 6)
    pygame.draw.circle(scr, C.TEXT if hov else C.TEXT_2, (kx, ky), kr)
    pygame.draw.circle(scr, color, (kx, ky), kr, 2)
    text(scr, f"{int(value * 100)}%", bx + bw + 8, y + 2, F.cap(), C.TEXT_3)
    return rect


def badge(scr, txt, x, y, color=C.PRIMARY, font=None):
    if font is None: font = F.cap()
    r = font.render(txt, True, C.TEXT)
    bw, bh = r.get_width() + 16, r.get_height() + 8
    bs = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.rect(bs, (*color, 180), (0, 0, bw, bh), border_radius=6)
    scr.blit(bs, (x, y))
    scr.blit(r, (x + 8, y + 4))
    return bw
