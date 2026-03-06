const pressed = new Set<string>();
const justPressed = new Set<string>();
const justReleased = new Set<string>();

export function initInput() {
  window.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase();
    if (!pressed.has(k)) justPressed.add(k);
    pressed.add(k);
    if (['arrowup', 'arrowdown', ' '].includes(k)) e.preventDefault();
  });
  window.addEventListener('keyup', (e) => {
    const k = e.key.toLowerCase();
    pressed.delete(k);
    justReleased.add(k);
  });
}

export function isPressed(key: string): boolean {
  return pressed.has(key.toLowerCase());
}

export function wasJustPressed(key: string): boolean {
  return justPressed.has(key.toLowerCase());
}

export function wasJustReleased(key: string): boolean {
  return justReleased.has(key.toLowerCase());
}

export function clearFrame() {
  justPressed.clear();
  justReleased.clear();
}

export function anyOfJustPressed(keys: string[]): boolean {
  return keys.some(k => justPressed.has(k));
}
