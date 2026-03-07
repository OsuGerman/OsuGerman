"""UI Design System — Colors, Typography, Spacing, States."""
import pygame

# ── Color Roles ──

class Colors:
    PRIMARY = (255, 77, 141)       # Hot pink — main actions
    PRIMARY_HOVER = (255, 110, 165)
    PRIMARY_PRESS = (220, 50, 110)

    SECONDARY = (124, 77, 255)     # Deep purple — secondary actions
    SECONDARY_HOVER = (150, 110, 255)

    ACCENT = (0, 212, 255)         # Cyan — highlights, active states
    ACCENT_DIM = (0, 150, 200)

    GOLD = (255, 215, 0)           # Perfect, rewards, rank S
    SUCCESS = (0, 230, 118)        # Clear, great hits
    WARNING = (255, 180, 0)        # Caution
    DANGER = (255, 82, 82)         # Miss, fail, quit, HP critical

    BG_DARK = (8, 2, 24)          # Deepest background
    BG_MID = (15, 6, 38)          # Panel backgrounds
    BG_LIGHT = (25, 12, 55)       # Elevated panels
    BG_CARD = (35, 18, 70)        # Card backgrounds
    BG_CARD_HOVER = (50, 28, 95)
    BG_CARD_ACTIVE = (65, 35, 120)

    TEXT = (255, 255, 255)
    TEXT_DIM = (180, 180, 200)
    TEXT_MUTED = (100, 95, 120)
    TEXT_DISABLED = (60, 55, 75)

    BORDER = (60, 45, 95)
    BORDER_HOVER = (100, 80, 150)
    BORDER_ACTIVE = (255, 77, 141)

    OVERLAY = (0, 0, 0, 180)
    GLOW_PINK = (255, 77, 141, 40)
    GLOW_CYAN = (0, 212, 255, 40)

    GROUND = (255, 77, 141)
    AIR = (0, 212, 255)

    PERFECT = GOLD
    GREAT = SUCCESS
    GOOD = ACCENT
    MISS = DANGER

    HP_FULL = SUCCESS
    HP_MID = GOLD
    HP_LOW = DANGER


# ── Typography ──

class Fonts:
    _cache: dict[tuple, pygame.font.Font] = {}
    NAME = 'segoe ui,arial,sans-serif'

    @classmethod
    def get(cls, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in cls._cache:
            cls._cache[key] = pygame.font.SysFont(cls.NAME, size, bold=bold)
        return cls._cache[key]

    @classmethod
    def hero(cls): return cls.get(64, True)
    @classmethod
    def title(cls): return cls.get(36, True)
    @classmethod
    def heading(cls): return cls.get(22, True)
    @classmethod
    def body(cls): return cls.get(16, False)
    @classmethod
    def body_bold(cls): return cls.get(16, True)
    @classmethod
    def caption(cls): return cls.get(13, False)
    @classmethod
    def micro(cls): return cls.get(11, False)
    @classmethod
    def combo(cls): return cls.get(48, True)
    @classmethod
    def score(cls): return cls.get(28, True)
    @classmethod
    def grade(cls): return cls.get(100, True)
    @classmethod
    def countdown(cls): return cls.get(80, True)


# ── Spacing ──

class Spacing:
    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48
    PANEL_PADDING = 20
    CARD_PADDING = 16
    BUTTON_H = 48
    BUTTON_H_SM = 36
    BUTTON_RADIUS = 12
    CARD_RADIUS = 14
    PANEL_RADIUS = 16


# ── Draw Helpers ──

def draw_panel(surface: pygame.Surface, rect: tuple, color=Colors.BG_MID,
               border_color=Colors.BORDER, radius=Spacing.PANEL_RADIUS, alpha=255):
    x, y, w, h = rect
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*color, alpha), (0, 0, w, h), border_radius=radius)
    if border_color:
        pygame.draw.rect(panel, (*border_color, min(255, alpha)), (0, 0, w, h), 2, border_radius=radius)
    surface.blit(panel, (x, y))


def draw_text(surface: pygame.Surface, text: str, x: int, y: int,
              font: pygame.font.Font = None, color=Colors.TEXT,
              align='left', shadow=False):
    if font is None:
        font = Fonts.body()
    rendered = font.render(str(text), True, color)
    if align == 'center':
        x = x - rendered.get_width() // 2
    elif align == 'right':
        x = x - rendered.get_width()
    if shadow:
        shadow_s = font.render(str(text), True, (0, 0, 0))
        shadow_s.set_alpha(100)
        surface.blit(shadow_s, (x + 2, y + 2))
    surface.blit(rendered, (x, y))
    return rendered.get_width(), rendered.get_height()


def draw_gradient_bg(surface: pygame.Surface):
    w, h = surface.get_size()
    for y in range(h):
        t = y / h
        r = int(8 + t * 15)
        g = int(2 + t * 6)
        b = int(24 + t * 30)
        pygame.draw.line(surface, (r, g, b), (0, y), (w, y))


def draw_button(surface: pygame.Surface, text: str, x: int, y: int, w: int, h: int,
                color=Colors.PRIMARY, mouse=(0,0), font=None, enabled=True):
    if font is None:
        font = Fonts.body_bold()
    rect = pygame.Rect(x, y, w, h)
    hovered = rect.collidepoint(mouse) and enabled

    if not enabled:
        col = Colors.TEXT_DISABLED
        bg = Colors.BG_MID
    elif hovered:
        bg = tuple(min(255, c + 30) for c in color)
        col = Colors.TEXT
    else:
        bg = color
        col = Colors.TEXT

    btn = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(btn, (*bg, 230 if enabled else 120), (0, 0, w, h), border_radius=Spacing.BUTTON_RADIUS)
    if hovered:
        glow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*color, 35), (0, 0, w + 8, h + 8), border_radius=Spacing.BUTTON_RADIUS + 2)
        surface.blit(glow, (x - 4, y - 4))
    border_c = tuple(min(255, c + 50) for c in bg)
    pygame.draw.rect(btn, (*border_c, 150), (0, 0, w, h), 2, border_radius=Spacing.BUTTON_RADIUS)
    surface.blit(btn, (x, y))

    rendered = font.render(text, True, col)
    tx = x + w // 2 - rendered.get_width() // 2
    ty = y + h // 2 - rendered.get_height() // 2
    surface.blit(rendered, (tx, ty))
    return rect, hovered
