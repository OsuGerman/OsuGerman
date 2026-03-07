"""Core framework: Drawable system, animation, containers, hit-testing, screens."""
from __future__ import annotations
import math
import pygame
from typing import Callable

# ---------------------------------------------------------------------------
# Easing functions
# ---------------------------------------------------------------------------

def ease_linear(t: float) -> float: return t
def ease_out_quad(t: float) -> float: return 1 - (1 - t) * (1 - t)
def ease_in_quad(t: float) -> float: return t * t
def ease_out_cubic(t: float) -> float: return 1 - (1 - t) ** 3
def ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2
def ease_out_elastic(t: float) -> float:
    if t == 0 or t == 1: return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1
def ease_out_back(t: float) -> float:
    c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

EASINGS = {
    'linear': ease_linear, 'out_quad': ease_out_quad, 'in_quad': ease_in_quad,
    'out_cubic': ease_out_cubic, 'in_out_quad': ease_in_out_quad,
    'out_elastic': ease_out_elastic, 'out_back': ease_out_back,
}

# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

class Animation:
    __slots__ = ('target', 'attr', 'start_val', 'end_val', 'duration',
                 'elapsed', 'easing', 'done', 'on_complete')

    def __init__(self, target: Drawable, attr: str, end_val: float,
                 duration: float, easing: str = 'out_quad',
                 on_complete: Callable | None = None):
        self.target = target
        self.attr = attr
        self.start_val = getattr(target, attr)
        self.end_val = end_val
        self.duration = max(0.001, duration)
        self.elapsed = 0.0
        self.easing = EASINGS.get(easing, ease_out_quad)
        self.done = False
        self.on_complete = on_complete

    def update(self, dt: float):
        if self.done:
            return
        self.elapsed += dt
        t = min(1.0, self.elapsed / self.duration)
        val = self.start_val + (self.end_val - self.start_val) * self.easing(t)
        setattr(self.target, self.attr, val)
        if t >= 1.0:
            self.done = True
            if self.on_complete:
                self.on_complete()


# ---------------------------------------------------------------------------
# Drawable
# ---------------------------------------------------------------------------

class Drawable:
    def __init__(self):
        self.x: float = 0
        self.y: float = 0
        self.width: float = 0
        self.height: float = 0
        self.alpha: float = 1.0
        self.scale: float = 1.0
        self.rotation: float = 0.0
        self.visible: bool = True
        self.interactive: bool = False
        self.hovered: bool = False
        self.parent: Container | None = None
        self._anims: list[Animation] = []

    @property
    def abs_x(self) -> float:
        return self.x + (self.parent.abs_x if self.parent else 0)

    @property
    def abs_y(self) -> float:
        return self.y + (self.parent.abs_y if self.parent else 0)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.abs_x), int(self.abs_y),
                           int(self.width * self.scale), int(self.height * self.scale))

    def contains(self, px: float, py: float) -> bool:
        r = self.rect
        return r.collidepoint(int(px), int(py))

    # Animation helpers
    def fade_to(self, alpha: float, dur: float, easing: str = 'out_quad', on_done: Callable | None = None):
        self._anims = [a for a in self._anims if a.attr != 'alpha']
        self._anims.append(Animation(self, 'alpha', alpha, dur, easing, on_done))
        return self

    def move_to(self, x: float, y: float, dur: float, easing: str = 'out_quad', on_done: Callable | None = None):
        self._anims = [a for a in self._anims if a.attr not in ('x', 'y')]
        self._anims.append(Animation(self, 'x', x, dur, easing))
        self._anims.append(Animation(self, 'y', y, dur, easing, on_done))
        return self

    def scale_to(self, s: float, dur: float, easing: str = 'out_elastic', on_done: Callable | None = None):
        self._anims = [a for a in self._anims if a.attr != 'scale']
        self._anims.append(Animation(self, 'scale', s, dur, easing, on_done))
        return self

    def update_anims(self, dt: float):
        for a in self._anims:
            a.update(dt)
        self._anims = [a for a in self._anims if not a.done]

    def update(self, dt: float):
        self.update_anims(dt)

    def draw(self, surface: pygame.Surface):
        pass

    def on_click(self, mx: float, my: float):
        pass

    def on_hover_enter(self):
        self.hovered = True

    def on_hover_exit(self):
        self.hovered = False


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

class Container(Drawable):
    def __init__(self):
        super().__init__()
        self.children: list[Drawable] = []

    def add(self, child: Drawable) -> Drawable:
        child.parent = self
        self.children.append(child)
        return child

    def remove(self, child: Drawable):
        child.parent = None
        self.children.remove(child)

    def clear(self):
        for c in self.children:
            c.parent = None
        self.children.clear()

    def update(self, dt: float):
        super().update(dt)
        for c in self.children:
            if c.visible:
                c.update(dt)

    def draw(self, surface: pygame.Surface):
        if not self.visible or self.alpha <= 0:
            return
        for c in self.children:
            if c.visible and c.alpha > 0:
                c.draw(surface)

    def hit_test(self, mx: float, my: float) -> Drawable | None:
        for c in reversed(self.children):
            if not c.visible or not c.interactive:
                continue
            if isinstance(c, Container):
                hit = c.hit_test(mx, my)
                if hit:
                    return hit
            if c.contains(mx, my):
                return c
        return None


# ---------------------------------------------------------------------------
# UI Widgets
# ---------------------------------------------------------------------------

class Text(Drawable):
    _font_cache: dict[tuple[str, int, bool], pygame.font.Font] = {}

    def __init__(self, text: str = '', size: int = 16, color: tuple = (255, 255, 255),
                 bold: bool = False, font_name: str = 'segoe ui,arial,sans-serif'):
        super().__init__()
        self.text = text
        self.size = size
        self.color = color
        self.bold = bold
        self.font_name = font_name
        self._font = self._get_font(font_name, size, bold)
        self._surface: pygame.Surface | None = None
        self._dirty = True

    @classmethod
    def _get_font(cls, name: str, size: int, bold: bool) -> pygame.font.Font:
        key = (name, size, bold)
        if key not in cls._font_cache:
            cls._font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
        return cls._font_cache[key]

    def set_text(self, text: str):
        if text != self.text:
            self.text = text
            self._dirty = True

    def _render(self):
        self._surface = self._font.render(self.text, True, self.color)
        self.width = self._surface.get_width()
        self.height = self._surface.get_height()
        self._dirty = False

    def draw(self, surface: pygame.Surface):
        if self._dirty or self._surface is None:
            self._render()
        if self._surface and self.alpha > 0:
            s = self._surface
            if self.alpha < 1:
                s = s.copy()
                s.set_alpha(int(self.alpha * 255))
            surface.blit(s, (int(self.abs_x), int(self.abs_y)))


class Button(Container):
    def __init__(self, text: str, w: int, h: int, color: tuple = (224, 64, 251),
                 on_click: Callable | None = None, font_size: int = 20):
        super().__init__()
        self.width = w
        self.height = h
        self.color = color
        self.callback = on_click
        self.interactive = True
        self._label = Text(text, font_size, (255, 255, 255), bold=True)
        self.add(self._label)
        self._hover_t = 0.0

    def update(self, dt: float):
        super().update(dt)
        target = 1.0 if self.hovered else 0.0
        self._hover_t += (target - self._hover_t) * min(1, dt * 12)
        self._label.x = self.width / 2 - self._label.width / 2
        self._label.y = self.height / 2 - self._label.height / 2

    def draw(self, surface: pygame.Surface):
        if self.alpha <= 0:
            return
        r = self.rect
        t = self._hover_t
        cr, cg, cb = self.color
        col = (min(255, int(cr + t * 40)), min(255, int(cg + t * 40)), min(255, int(cb + t * 40)))
        btn_surf = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, (*col, int(self.alpha * 255)), (0, 0, r.w, r.h), border_radius=14)
        if t > 0.01:
            glow = pygame.Surface((r.w + 8, r.h + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*self.color, int(t * 50 * self.alpha)), (0, 0, r.w + 8, r.h + 8), border_radius=16)
            surface.blit(glow, (r.x - 4, r.y - 4))
        border_col = (min(255, cr + 60), min(255, cg + 60), min(255, cb + 60))
        pygame.draw.rect(btn_surf, (*border_col, int(self.alpha * 180)), (0, 0, r.w, r.h), 2, border_radius=14)
        surface.blit(btn_surf, (r.x, r.y))
        super().draw(surface)

    def on_click(self, mx: float, my: float):
        if self.callback:
            self.callback()

    def on_hover_enter(self):
        super().on_hover_enter()
        self.scale_to(1.03, 0.15, 'out_back')

    def on_hover_exit(self):
        super().on_hover_exit()
        self.scale_to(1.0, 0.1, 'out_quad')


class Slider(Drawable):
    def __init__(self, w: int, value: float = 0.5, label: str = '',
                 on_change: Callable[[float], None] | None = None,
                 color: tuple = (224, 64, 251)):
        super().__init__()
        self.width = w
        self.height = 30
        self.value = value
        self.label = label
        self.color = color
        self.on_change = on_change
        self.interactive = True
        self.dragging = False
        self._font = Text._get_font('segoe ui,arial,sans-serif', 14, False)
        self._font_sm = Text._get_font('segoe ui,arial,sans-serif', 12, False)

    def contains(self, px: float, py: float) -> bool:
        ax, ay = self.abs_x, self.abs_y
        return ax <= px <= ax + self.width and ay - 5 <= py <= ay + self.height + 5

    def handle_drag(self, mx: float):
        bar_x = self.abs_x + 150
        bar_w = self.width - 200
        ratio = max(0, min(1, (mx - bar_x) / bar_w))
        if ratio != self.value:
            self.value = ratio
            if self.on_change:
                self.on_change(ratio)

    def draw(self, surface: pygame.Surface):
        if self.alpha <= 0:
            return
        ax, ay = int(self.abs_x), int(self.abs_y)
        lbl = self._font.render(self.label, True, (200, 200, 200))
        surface.blit(lbl, (ax, ay + 4))
        bar_x = ax + 150
        bar_w = self.width - 200
        bar_h = 12
        bar_y = ay + 8
        pygame.draw.rect(surface, (40, 30, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        fill_w = int(bar_w * self.value)
        if fill_w > 0:
            pygame.draw.rect(surface, self.color, (bar_x, bar_y, fill_w, bar_h), border_radius=6)
        knob_x = bar_x + fill_w
        knob_r = 8 if not self.hovered else 10
        pygame.draw.circle(surface, (255, 255, 255) if self.hovered else (210, 210, 210),
                           (knob_x, bar_y + bar_h // 2), knob_r)
        pygame.draw.circle(surface, self.color, (knob_x, bar_y + bar_h // 2), knob_r, 2)
        val_s = self._font_sm.render(f"{int(self.value * 100)}%", True, (160, 160, 160))
        surface.blit(val_s, (bar_x + bar_w + 8, ay + 4))

    def on_click(self, mx: float, my: float):
        self.dragging = True
        self.handle_drag(mx)


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------

class Screen(Container):
    def __init__(self):
        super().__init__()
        self.active = False

    def on_enter(self):
        self.active = True
        self.alpha = 0
        self.fade_to(1.0, 0.25, 'out_quad')

    def on_exit(self, callback: Callable | None = None):
        self.fade_to(0.0, 0.2, 'out_quad', callback)

    def on_key(self, key: int, mods: int):
        pass

    def on_resize(self, w: int, h: int):
        pass


# ---------------------------------------------------------------------------
# Cursor Drawable
# ---------------------------------------------------------------------------

class CursorTrail:
    def __init__(self):
        self.positions: list[tuple[float, float, float]] = []
        self.show_trail = True

    def update(self, mx: float, my: float, dt: float):
        self.positions.append((mx, my, 0.3))
        for i in range(len(self.positions)):
            x, y, life = self.positions[i]
            self.positions[i] = (x, y, life - dt)
        self.positions = [(x, y, l) for x, y, l in self.positions if l > 0]

    def draw(self, surface: pygame.Surface):
        if not self.show_trail:
            return
        for x, y, life in self.positions:
            alpha = int(life / 0.3 * 80)
            sz = max(1, int(life / 0.3 * 4))
            s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (224, 64, 251, alpha), (sz, sz), sz)
            surface.blit(s, (int(x) - sz, int(y) - sz))


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class Application:
    def __init__(self, width: int = 1280, height: int = 720, title: str = "Rhythm Dash"):
        self.width = width
        self.height = height
        self.title = title
        self.running = False
        self.screen: pygame.Surface = None  # type: ignore
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.current_screen: Screen | None = None
        self._next_screen: Screen | None = None
        self.cursor = CursorTrail()
        self._hovered: Drawable | None = None
        self._dragging_slider: Slider | None = None
        self.fullscreen = False
        self.mouse_pos = (0, 0)

    def init(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption(self.title)

    def switch_screen(self, new_screen: Screen):
        if self.current_screen:
            self.current_screen.on_exit(lambda: self._activate_screen(new_screen))
        else:
            self._activate_screen(new_screen)

    def _activate_screen(self, s: Screen):
        self.current_screen = s
        s.width = self.width
        s.height = self.height
        s.on_enter()

    def run(self):
        self.running = True
        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0
            self.mouse_pos = pygame.mouse.get_pos()
            self._process_input()
            self._update(dt)
            self._render()
            pygame.display.flip()
        pygame.quit()

    def _process_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                if self.current_screen:
                    self.current_screen.width = self.width
                    self.current_screen.height = self.height
                    self.current_screen.on_resize(self.width, self.height)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                if self.current_screen:
                    self.current_screen.on_key(event.key, event.mod)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging_slider = None
            elif event.type == pygame.MOUSEMOTION:
                if self._dragging_slider:
                    self._dragging_slider.handle_drag(event.pos[0])
            elif event.type == pygame.MOUSEWHEEL:
                pass

    def _handle_click(self, pos: tuple[int, int]):
        if not self.current_screen:
            return
        hit = self.current_screen.hit_test(pos[0], pos[1])
        if hit:
            if isinstance(hit, Slider):
                self._dragging_slider = hit
            hit.on_click(pos[0], pos[1])

    def _update(self, dt: float):
        if self.current_screen:
            self.current_screen.update(dt)
            new_hover = self.current_screen.hit_test(self.mouse_pos[0], self.mouse_pos[1])
            if new_hover != self._hovered:
                if self._hovered:
                    self._hovered.on_hover_exit()
                self._hovered = new_hover
                if self._hovered:
                    self._hovered.on_hover_enter()
            is_hovering = self._hovered is not None
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if is_hovering else pygame.SYSTEM_CURSOR_ARROW)
        self.cursor.update(self.mouse_pos[0], self.mouse_pos[1], dt)

    def _render(self):
        if self.current_screen:
            self.current_screen.draw(self.screen)
        self.cursor.draw(self.screen)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            info = pygame.display.Info()
            self.width, self.height = info.current_w, info.current_h
        else:
            self.width, self.height = 1280, 720
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        if self.current_screen:
            self.current_screen.width = self.width
            self.current_screen.height = self.height
            self.current_screen.on_resize(self.width, self.height)
