# Apex Design Language — Design.md (Web)

> **Purpose.** This is the portable, app-agnostic specification for the **Apex** visual identity on the **web** (React + CSS). Hand this file to a fresh Claude (or any developer) to build a *new* Apex-family web app that looks and feels identical to its siblings — without copying any one app's business logic.
>
> Treat it as a contract. If you ship an Apex web app that violates these rules, it has drifted from the family. Nothing here is domain-specific: it describes color, type, shape, motion, components, and data-viz theming only.
>
> **Origin.** Ported from the Apex desktop (WPF) design language to the web. The desktop `Surface(accentPct, lift)` palette formula maps 1:1 onto CSS `color-mix()`; that mapping is the heart of this system (§3).

---

## 1. Philosophy

Three rules govern everything visual:

1. **Surfaces are neutral; the accent threads through.** Every background, panel, card, input, and border is a *mix of the user's accent color with a neutral base* — never a hardcoded hue. Pick teal as the accent and the whole UI leans teal; pick coral and it leans coral. The pure, unmixed accent is reserved for *interactive* elements only: primary buttons, links, focus rings, active states, key numeric values, progress indicators, and the logo badge.

2. **Light / Dark / System, plus a user-configurable accent.** Three modes and a 6-digit hex accent, persisted locally. System mode follows the OS. The theme entry point is the **logo badge** in the corner of the app shell.

3. **Quiet by default, alive on interaction.** Resting state is calm — subtle borders, no glow, no noise. Hovering, pressing, and committing earn springy motion that settles with a tiny overshoot. **Bounce is the Apex signature**; nothing twitches at rest, but everything springs on touch.

---

## 2. Stack & Mechanism

- **React 18 + TypeScript (strict)** for components.
- **Plain CSS with custom properties** — no Tailwind, no CSS-in-JS runtime. Tokens are CSS variables on `:root`; components consume `var(--token)`. This is mandatory: it's what makes live theme/accent switching free (no recompile, no JS palette pass).
- The only JS the theme needs is: set `--accent` inline, set `data-mode` on `<html>`, and compute `--on-accent`. Everything else derives via `color-mix()`.

---

## 3. Color System

### 3.1 The token mechanism (`color-mix`)

Two inputs drive the entire palette: `--accent` (user) and the per-mode `--base` / `--inverse`. Every surface is a two-stage mix:

```
token = color-mix(in srgb, var(--inverse) <lift%>,
                   color-mix(in srgb, var(--accent) <accentPct%>, var(--base)))
```

Stage 1 bleeds a little accent into the neutral base. Stage 2 lifts toward the inverse (lightens in dark mode, darkens in light). Keep that nesting order.

### 3.2 Full token table (drop-in `tokens.css`)

```css
:root {
  /* user input — overwritten inline by the theme provider */
  --accent: #7c73ff;            /* default Apex violet; pick a per-app brand default */

  /* dark mode bases (default) */
  --base: #0a0b10;
  --inverse: #ffffff;

  /* surfaces: color-mix(inverse <lift%>, color-mix(accent <pct%>, base)) */
  --bg:         color-mix(in srgb, var(--inverse) 0%,  color-mix(in srgb, var(--accent) 3%,  var(--base)));
  --bg-alt:     color-mix(in srgb, var(--inverse) 0%,  color-mix(in srgb, var(--accent) 2%,  var(--base)));
  --panel:      color-mix(in srgb, var(--inverse) 3%,  color-mix(in srgb, var(--accent) 5%,  var(--base)));
  --card:       color-mix(in srgb, var(--inverse) 4%,  color-mix(in srgb, var(--accent) 4%,  var(--base)));
  --card-hover: color-mix(in srgb, var(--inverse) 8%,  color-mix(in srgb, var(--accent) 8%,  var(--base)));
  --input:      color-mix(in srgb, var(--inverse) 0%,  color-mix(in srgb, var(--accent) 3%,  var(--base)));
  --line:       color-mix(in srgb, var(--inverse) 8%,  color-mix(in srgb, var(--accent) 8%,  var(--base)));
  --line-soft:  color-mix(in srgb, var(--inverse) 5%,  color-mix(in srgb, var(--accent) 5%,  var(--base)));

  /* accent-derived */
  --accent-alt:    color-mix(in srgb, white 18%, var(--accent));                                  /* lifted: outlines/glow */
  --accent-soft:   color-mix(in srgb, var(--inverse) 4%, color-mix(in srgb, var(--accent) 18%, var(--base))); /* chip/active bg */
  --accent-subtle: color-mix(in srgb, var(--inverse) 2%, color-mix(in srgb, var(--accent) 8%,  var(--base))); /* quiet wash */

  /* auto-contrast (set inline per accent — see §3.4) */
  --on-accent: #ffffff;

  /* fixed-per-theme text + semantic (dark) */
  --text: #f1f3f8;
  --muted: #8c90a2;
  --danger: #ff5c78;
  --danger-soft: #361822;
  /* OPTIONAL semantic pair for finance/status apps; omit if not needed */
  --positive: #34d399;
  --positive-soft: #0e2a22;
}

:root[data-mode="light"] {
  --base: #ffffff;
  --inverse: #14151f;
  /* panels/cards go pure white so they pop against a tinted bg */
  --panel: color-mix(in srgb, var(--inverse) 0%, color-mix(in srgb, var(--accent) 0%, var(--base)));
  --card:  color-mix(in srgb, var(--inverse) 0%, color-mix(in srgb, var(--accent) 0%, var(--base)));
  --bg:    color-mix(in srgb, var(--inverse) 3%, color-mix(in srgb, var(--accent) 7%, var(--base)));
  --text: #16171f;
  --muted: #6e7188;
  --danger: #d63255;  --danger-soft: #fbe3e9;
  --positive: #0e9f6e; --positive-soft: #e3f9f0;
}
```

> **CSS `color-mix` weight reminder:** `color-mix(in srgb, A x%, B)` = `x%` of A and `(100−x)%` of B. The table values already translate the desktop `Surface(accentPct, lift)` numbers into these percentages — reuse them verbatim.

### 3.3 Token usage map

| Token | Use |
|---|---|
| `--bg` / `--bg-alt` | App background / main content surface |
| `--panel` | Sidebars, headers, dialog shells, popovers, sticky table headers |
| `--card` | Cards, list items, chart containers |
| `--card-hover` | Card/row hover |
| `--input` | Text inputs, selects, segmented controls, inner containers |
| `--line` | Defining borders: shell outer, dialog, input focus |
| `--line-soft` | Subtle borders: cards, panels, rows, nested surfaces |
| `--accent` | Primary buttons, links, focus rings, active states, key values |
| `--accent-alt` | Lifted accent: button borders, logo ring, scrollbar drag |
| `--accent-soft` | Chip/eyebrow backgrounds, active nav, card-hover border |
| `--text` / `--muted` | Primary / secondary text |
| `--danger` (+soft) | Destructive actions, errors, negative values |
| `--positive` (+soft) | Optional: success/positive values (finance, status) |

### 3.4 Auto-contrast (`--on-accent`)

Never hardcode `color: white` on the accent — the user may pick amber or mint. Compute the readable on-color per accent and set it inline:

```ts
const [r, g, b] = hexToRgb(accent);
const luminance = r * 0.299 + g * 0.587 + b * 0.114;
const onAccent = luminance >= 150 ? '#10111a' : '#ffffff';
root.style.setProperty('--on-accent', onAccent);
```

Apply `--on-accent` to: primary-button text, logo glyph, active-segment text, any text drawn directly on `--accent`. Use the same technique for `--on-danger` / `--on-positive` if those surfaces carry text.

---

## 4. Theme System

- **State:** `{ mode: 'light'|'dark'|'system', accent: '#rrggbb' }`. Persist to `localStorage` under a per-app key (e.g. `apex.theme`).
- **Apply:** set `data-mode` (resolved light/dark) on `<html>`, set `--accent` inline on `:root`, compute `--on-accent`. All other tokens recompute automatically because they're `var()`-derived — no JS palette walk.
- **System mode:** listen to `window.matchMedia('(prefers-color-scheme: dark)')` `change` and re-apply.
- **Entry point:** a **logo badge** in the app shell opens a theme popover containing: a 3-segment mode control (Light/Dark/System) + 8 preset accent swatches + a hex input.
- **Preset swatches (canonical 8):** violet `#7c73ff`, azure `#3b82f6`, teal `#14b8a6`, green `#22c55e`, amber `#f59e0b`, coral `#fb7185`, magenta `#d946ef`, neutral `#8b8fa3`.

---

## 5. Typography

- **Font stack:** `"Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system, sans-serif`. Monospace (numbers, codes, IDs, hex): `"Cascadia Code", "Cascadia Mono", Consolas, ui-monospace, monospace`. **Introduce no other fonts** (no Inter / Roboto / SF). Bundle the fonts if cross-platform fidelity matters.
- **Body is bold by default (`font-weight: 700`).** Build hierarchy by stepping *up* in weight, never down. Never use `< 700` for body/UI text.

| Role | Weight |
|---|---|
| Body, buttons, inputs, nav | `700` |
| Eyebrow/section labels (UPPERCASE), card titles, key values | `800` |
| Page titles, dialog titles, empty-state & hero headings | `900` |

- **Size scale (rem, 16px root):** `0.625` eyebrow chips · `0.6875` taglines · `0.75` card labels / segmented · `0.8125` small body / table cells · `0.875` inputs & buttons · `1.125` section/app title · `1.1875` dialog title · `1.375` page / empty-state heading · `1.625` hero numeric value.
- **All numeric / data values** render in the **monospace** stack with `font-variant-numeric: tabular-nums` so columns align.

---

## 6. Shape (border-radius)

Strict scale — never invent a radius:

| Token | px | Use |
|---|---|---|
| `--r-shell` | 18 | App shell / outermost containers |
| `--r-panel` | 14 | Panels, cards, dialogs, chart cards |
| `--r-ctl` | 12 | Buttons, inputs, table/list containers, toast, logo badge |
| `--r-icon` | 10 | Icon buttons, segmented container, swatch row |
| `--r-pill` | 8 | Pills, chips, segments, color swatches |
| `--r-track` | 6 | Progress / slider tracks |

**Nesting rule:** an inner element's radius is always smaller than its parent's.

---

## 7. Borders (3-tier)

| Tier | Token | Where |
|---|---|---|
| Defining | `--line` | Shell outer, dialog shell, input focus (→ `--accent`) |
| Subtle | `--line-soft` | Cards, panels, chart cards, rows, any nested surface |
| None | `0` | Inner containers that rely on `--input` background contrast |
| Accent | `--accent` | Toasts, focused inputs, active selection |
| Accent-soft | `--accent-soft` | Card hover, active nav |

**Rule:** a child border is always *softer* than its parent's, or absent. Never stack three visible borders.

---

## 8. Spacing

Scale (px): `2` hairline · `4` micro · `6` · `8` card gap / label→title · `12` shell outer / header padding · `14` panel padding · `16` toast / dialog content · `18` · `20` dialog shell · `22` hero card padding.

**Rule of thumb:** outer surfaces 12–14, content padding 18–22, micro-gaps 2–8.

---

## 9. Motion (the signature)

Bouncy release, snappy press. No linear easing. No overshoot longer than ~520ms.

```css
:root {
  --ease-press: cubic-bezier(0.4, 0, 1, 1);          /* press-down, ~70–80ms */
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);  /* single-overshoot release */
}
```

| Element | Behavior |
|---|---|
| Buttons | press → `scale(0.9)` on `--ease-press`; release springs to 1 on `--ease-bounce` (~360ms). Icon buttons press to `0.8–0.85`. Primary buttons gain an accent-tinted shadow on hover. |
| Cards | hover lifts `translateY(-3px)` + soft drop shadow; mount entrance fades + rises ~10px on `--ease-bounce` (~440ms). |
| Key value refresh | pulse opacity `0.25→1` + scale `1.14→1` (~450ms). Implement by **keying the value node on its content** so React remounts it and the CSS animation replays on every change. |
| Empty-state badge | icon badge pops in `scale(0.6→1)` on `--ease-bounce` (~500ms). |
| Dialogs / toasts | scale `0.86→1` + fade, settle ~500ms; toasts auto-dismiss ~1.6s. |
| Views (route change) | quick fade + 6px rise (~280ms), keyed on the route path. |
| Logo badge | the one "grow" hover: `scale(1.06)`. |

For a true two-oscillation elastic spring (large surfaces), use the **Web Animations API** with keyframes — CSS `cubic-bezier` only does a single overshoot. `--ease-bounce` covers everyday press/hover.

**Reduced motion:** honor `@media (prefers-reduced-motion: reduce)` — drop transforms, keep instant opacity.

```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

**Every interactive element animates.** A static interactive element feels broken in Apex.

---

## 10. Focus & Scrollbars

**Focus ring** — on every focusable control; never the browser default:

```css
:focus-visible { outline: 1.5px dashed var(--accent); outline-offset: 3px; border-radius: var(--r-panel); }
```

**Scrollbars** — slim, themed, accent-aware:

```css
* { scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--line) 75%, transparent) transparent; }
*::-webkit-scrollbar { width: 10px; height: 10px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--line) 75%, transparent);
  border-radius: 4px; border: 2px solid transparent; background-clip: padding-box;
}
*::-webkit-scrollbar-thumb:hover  { background: color-mix(in srgb, var(--accent) 90%, transparent); background-clip: padding-box; }
*::-webkit-scrollbar-thumb:active { background: var(--accent-alt); background-clip: padding-box; }
```

---

## 11. Iconography

- **Stroke-based vector SVG only** — never Unicode glyphs (they render inconsistently across fonts/DPI).
- Design on a **16×16** viewBox: `stroke-width: 1.5`, `stroke-linecap/linejoin: round`, `fill: none`, `stroke: currentColor` (so icons follow text color and theme automatically).
- Display 14–16px in chrome buttons, 28px+ in empty-state badges.
- A few glyphs (e.g. the **settings gear**) read better as a richer 24-viewBox cog (Lucide-style). It's fine for an icon to carry its own viewBox/stroke-width as long as it still uses `stroke: currentColor`, `fill: none`, and round caps/joins so it matches the set.
- **App identity badge:** a solid `--accent` rounded square (r≈12), 1.4px `--accent-alt` ring, a faint top highlight, and the app's first letter centered in `--on-accent`. The same recipe is the favicon/app icon so the mark reads as one across the family.

---

## 12. Component Specs

Build these as themed React components; all consume tokens only.

- **AppShell** — `--r-shell` outer; sidebar (`--panel`) + main content (`--bg-alt`); 12px outer padding, 12px gap. Sidebar holds the logo badge + nav.
- **Nav links** — `--muted` at rest; hover → `--card-hover` + `--text`; active → `--accent-soft` bg + a 3px `--accent` left-bar marker.
- **LogoBadge + ThemePopover** — §4. Popover: `--panel` bg, `--line` border, `--r-panel`, pop-in animation, width ~286px.
- **Button** — variants: `ghost` (`--input` bg, `--line-soft` border, hover border→accent), `primary` (`--accent` bg, `--on-accent` text), `icon` (30×30, `--r-icon`, transparent, hover→accent). All press-spring (§9).
- **Card / StatCard** — §6/§7; StatCard = uppercase `--muted` label + large mono value (tone-colored: `--text`/`--positive`/`--danger`) + optional sub.
- **Input / Select** — `--input` bg, `--line-soft` border, `--r-ctl`, bold; focus border → `--accent`. In-field icons (search/clear/reveal) are transparent icon-buttons living inside the field's right padding — never bordered.
- **Pill / Chip** — `--accent-soft` bg, `--r-pill`, uppercase `800` accent label (eyebrows) or neutral (tags).
- **Dialog** — `--panel` shell, `--line` border, `--r-panel`, scale+fade entrance; title (`900`) + accent underline bar; footer = ghost (cancel) + primary (confirm); destructive primary uses `--danger` + `--on-danger`.
- **Toast** — bottom-center, `--panel` bg, `--accent` border, `--r-ctl`, spring-in from below, auto-dismiss.
- **SegmentedControl** — `--input` container, `--r-icon`, 3+ `--r-pill` segments; active = `--accent` bg + `--on-accent`.
- **DataTable** — sticky `--panel` header, `--line-soft` row borders, hover `--card-hover`, mono numeric cells right-aligned, themed scrollbar; row → detail drawer.
- **Drawer** — right-side, `--panel`, slide-in spring, scrim, Esc to close.
- **EmptyState** — centered card: accent-tinted icon badge (pops in, §9) + `900` heading + `--muted` body + optional primary CTA. Use one shared component for every no-data state so they read identically.
- **ChartCard** — wraps the chart lib in a `Card`; uppercase `--muted` title with a `--line-soft` divider above the canvas; resolves tokens to real colors (§13) and remounts on theme change.
- **Customizable widget grid** — an edit-mode dashboard where widgets can be added/removed, reordered, and resized; layout persists locally. See §13c for the interaction rules.

---

## 13c. Customizable widget grid

A dashboard of self-contained widgets the user can rearrange. Layout is `{id, w, h}[]`
(column span `w` 1–N, optional pixel height `h`) persisted to `localStorage`; a widget
*registry* maps each id to its render. A fixed N-column CSS grid (e.g. `repeat(4, 1fr)`,
dropping to 2 then 1 at breakpoints); each widget sets `grid-column: span w` — spans
auto-clamp on narrower grids, so no per-breakpoint math.

**Edit mode** (toggled by a "Customize" button): each widget gains a drag **grip**, a
remove **✕**, and an SE **resize handle**; an "Add widget" chip row lists removed widgets;
a "Reset" restores defaults. A dashed outline marks editable widgets.

**Reorder — commit on drop, never mid-drag.** This is the rule that makes it feel solid:
- On grip `pointerdown`, attach `pointermove`/`pointerup` to `window` *directly in the
  handler* (not via an effect keyed on the list — that tears listeners down mid-gesture).
- During the move, only **track** the hovered target (`document.elementFromPoint(...).closest('[data-wid]')`)
  and highlight it; do **not** reorder yet. Live-reordering variable-size items reflows the
  grid under the cursor → oscillation and stacked animations ("confused" motion).
- On `pointerup`, move the dragged id to the target's index **once**.
- Read the live list from a ref inside the handlers; resolve targets from the DOM, not a
  React ref-map (inline `ref` callbacks churn every render).

**Resize** — SE handle `pointerdown` captures the baseline (start X/Y, start `w`/`h`,
column step = gridWidth/N) **once**, then `pointermove` maps Δx→column span (snap, clamp
1–N) and Δy→height (clamp) for height-resizable widgets. Live-tracks the cursor.

**Motion — single FLIP on the committed change.** Snapshot widget rects *before* the drop
mutation; after layout, animate each moved node from old→new with a **translate-only** WAAPI
keyframe on `--ease-bounce` (~300ms). Translate-only — never `scale` — or card/chart content
distorts. Gate the FLIP so it runs **only when the order signature changes** (and only for a
reorder you initiated, via the captured snapshot), so unrelated re-renders (filters, theme,
data) never animate. Respect `prefers-reduced-motion`.

---

## 13. Data Visualization Theming (charts)

If the app uses charts (e.g. **ECharts**), the canvas **cannot read CSS variables** — resolve tokens to real color strings at runtime and recompute on theme change:

```ts
const cssVar = (n: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(n).trim() || '#888';
```

- Series colors: `[--accent, --accent-alt, --positive, --danger, --muted]`.
- Axis lines / split lines → `--line-soft` (dashed split lines). Labels → `--muted`, mono font.
- Tooltip: `--panel` bg, `--line` border, `--r-panel`, soft shadow, mono text.
- **Resolve every color in series `itemStyle`/`areaStyle`/`visualMap` via `cssVar()`** — passing `'var(--x)'` strings renders fine at rest but turns transparent on hover (ECharts derives emphasis colors from the base). Recompute and re-register the theme whenever mode/accent changes, and key the chart component to remount.

---

## 13b. Responsive & Navigation

The shell is a CSS grid that adapts at two breakpoints. **Desktop ≥ 861px** and **mobile ≤ 860px** (with a finer pass at ≤ 420px for the densest views).

### Desktop — hover-expand icon rail
- Sidebar is a slim **64px icon rail** by default (icons + logo badge only). The grid reserves only the collapsed width (`grid-template-columns: 76px 1fr`).
- The sidebar is `position: absolute` inside a `position: relative` shell so it **expands as an overlay flyout (~236px) on `:hover`** without reflowing content. It springs open on `--ease-bounce`; brand text + nav labels fade in (`opacity` + small `translateX`).
- **Expansion is `:hover` only — not `:focus-within`.** Focus-within keeps the rail open after a nav click (the link retains focus), which feels broken; hover-only collapses the moment the pointer leaves the rail.
- Because the sidebar is out of grid flow, **pin main content with `grid-column: 2`** — otherwise it auto-places into the rail's 76px track.
- Keep the rail keyboard-reachable; if you need focus to expand it for keyboard users, blur the active link on navigation rather than relying on `:focus-within`.

### Mobile — off-canvas drawer
- At ≤ 860px the grid becomes a single column with an `auto 1fr` row stack: a **top bar** (hamburger + app title) above the main content.
- The sidebar becomes a **fixed off-canvas drawer** (`width: min(280px, 84vw)`, `translateX(-104%)` → `0` when open) with a dimming **scrim**. It springs in on `--ease-bounce`.
- The drawer **closes on: nav tap, scrim tap, `Escape`, and route change.** Labels/brand always show in the drawer (override the desktop collapse rules, including `:hover`, inside the media query). Reset `main` to `grid-column: 1`.
- Touch targets in the drawer are enlarged (≥ 44px tall rows).
- Keep the theme entry point reachable on mobile — the logo badge lives inside the drawer's brand row (not the top bar).

### Active-route marker
A 3px `--accent` left-bar on the active nav link. Anchor it at `left: 0` (not a negative offset) so the rail's `overflow: hidden` doesn't clip it.

---

## 14. Anti-patterns (don't ship these)

- ❌ Hardcoding a hex color in a component (`#7c73ff`, `background:#fff`). Use a token.
- ❌ `color: white` on an accent surface — use `--on-accent`.
- ❌ Three nested visible borders.
- ❌ A radius outside `{18, 14, 12, 10, 8, 6}`.
- ❌ A new font family, or `font-weight < 700` for UI text.
- ❌ Linear-eased or `> ~600ms` animations; static interactive elements.
- ❌ `var(--token)` strings inside canvas chart options (resolve with `cssVar()`).
- ❌ Unicode-glyph icons; the browser default focus outline.
- ❌ Per-app divergence: a new accent default is fine, but the token formula, scales, and motion feel must match the family.

---

## 15. Implementation Checklist (new Apex web app)

1. Vite + React + TS. Drop in `tokens.css` (§3.2), the motion/focus/scrollbar globals (§9–§10), and the font stacks (§5).
2. Build the theme provider: load `{mode, accent}` from `localStorage`, apply `data-mode` + `--accent` + `--on-accent`, listen to OS theme in system mode.
3. Build LogoBadge + ThemePopover (mode segments + 8 swatches + hex input).
4. Build the component primitives (§12) — all token-driven, all animated (§9).
5. If charting, register the token-resolved chart theme (§13) and re-register on theme change.
6. Verify: switch mode and every accent swatch — the entire UI (including charts) recolors live with zero hardcoded colors. Tab through controls — every focusable shows the dashed accent ring. Hover everything — it springs, nothing vanishes.

---

## 16. Reference layout (theme module)

```
src/
├─ theme/
│  ├─ tokens.css           # §3.2 + globals (§9 motion, §10 focus/scrollbar)
│  ├─ ThemeProvider.tsx    # mode/accent state, persistence, system listener, --on-accent
│  ├─ onAccent.ts          # luminance auto-contrast + hex validation
│  └─ chartTheme.ts        # cssVar() + chart theme builder (if charts)
├─ components/             # AppShell, LogoBadge+ThemePopover, Button, Card/StatCard,
│                          # Input/Select, Pill, Dialog, Toast, SegmentedControl,
│                          # DataTable, Drawer, EmptyState, ChartCard
```

Keep this file in sync if the family's design evolves; bump sibling apps to match.
