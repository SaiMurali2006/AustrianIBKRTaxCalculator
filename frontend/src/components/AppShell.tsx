import { useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { PRESET_ACCENTS, useTheme, type Mode } from "../theme/ThemeProvider";
import { isValidHex, normalizeHex } from "../theme/onAccent";

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="segmented" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={value === o.value}
          className={`segmented__seg ${value === o.value ? "active" : ""}`}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function ThemePopover({ onClose, anchor }: { onClose: () => void; anchor: DOMRect | null }) {
  const { mode, accent, setMode, setAccent } = useTheme();
  const [hex, setHex] = useState(accent);

  // Anchored below the badge; clamped to the viewport so it never overflows the screen edge.
  const top = anchor ? anchor.bottom + 8 : 64;
  const left = anchor ? Math.min(anchor.left, window.innerWidth - 286 - 12) : 12;

  return createPortal(
    <>
      <div className="scrim" onClick={onClose} />
      <div className="theme-pop" style={{ top, left }} onClick={(e) => e.stopPropagation()}>
        <div className="theme-pop__label">Appearance</div>
        <SegmentedControl<Mode>
          options={[
            { value: "light", label: "Light" },
            { value: "dark", label: "Dark" },
            { value: "system", label: "System" },
          ]}
          value={mode}
          onChange={setMode}
        />
        <div className="theme-pop__label">Accent</div>
        <div className="swatches">
          {PRESET_ACCENTS.map((s) => (
            <button
              key={s.name}
              title={s.name}
              aria-label={s.name}
              className={`swatch ${accent.toLowerCase() === s.hex ? "active" : ""}`}
              style={{ background: s.hex }}
              onClick={() => {
                setAccent(s.hex);
                setHex(s.hex);
              }}
            />
          ))}
        </div>
        <div className="theme-pop__label">Custom hex</div>
        <input
          className="input mono"
          value={hex}
          spellCheck={false}
          onChange={(e) => {
            const v = e.target.value;
            setHex(v);
            if (isValidHex(v)) setAccent(normalizeHex(v));
          }}
        />
      </div>
    </>,
    document.body,
  );
}

export function LogoBadge({ letter = "K" }: { letter?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button
        ref={ref}
        className="logo-badge"
        aria-label="Theme settings"
        onClick={() => setOpen((o) => !o)}
      >
        {letter}
      </button>
      {open && <ThemePopover onClose={() => setOpen(false)} anchor={ref.current?.getBoundingClientRect() ?? null} />}
    </>
  );
}

export interface NavItem {
  id: string;
  label: string;
  icon: ReactNode;
}

export function AppShell({
  nav,
  active,
  onNavigate,
  children,
}: {
  nav: NavItem[];
  active: string;
  onNavigate: (id: string) => void;
  children: ReactNode;
}) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <LogoBadge />
          <span className="sidebar__brand-text">KeSt Engine</span>
        </div>
        <nav className="nav">
          {nav.map((item) => (
            <button
              key={item.id}
              className={`nav__link ${active === item.id ? "active" : ""}`}
              onClick={(e) => {
                onNavigate(item.id);
                (e.currentTarget as HTMLButtonElement).blur();
              }}
            >
              {item.icon}
              <span className="nav__label">{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
