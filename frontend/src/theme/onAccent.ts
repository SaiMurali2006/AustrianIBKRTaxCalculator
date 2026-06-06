// Auto-contrast on-color for an accent surface (Design.md §3.4) + hex validation.

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const n = parseInt(full, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function onAccentFor(accent: string): string {
  const [r, g, b] = hexToRgb(accent);
  const luminance = r * 0.299 + g * 0.587 + b * 0.114;
  return luminance >= 150 ? "#10111a" : "#ffffff";
}

export function isValidHex(value: string): boolean {
  return /^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value.trim());
}

export function normalizeHex(value: string): string {
  const v = value.trim();
  return v.startsWith("#") ? v : `#${v}`;
}
