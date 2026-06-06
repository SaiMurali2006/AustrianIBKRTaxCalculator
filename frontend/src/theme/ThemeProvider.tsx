// Apex theme state (Design.md §4): {mode, accent} persisted to localStorage; applies
// data-mode on <html>, --accent inline, computes --on-accent; follows OS in system mode.

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { onAccentFor } from "./onAccent";

export type Mode = "light" | "dark" | "system";
export interface ThemeState {
  mode: Mode;
  accent: string;
}

export const PRESET_ACCENTS = [
  { name: "violet", hex: "#7c73ff" },
  { name: "azure", hex: "#3b82f6" },
  { name: "teal", hex: "#14b8a6" },
  { name: "green", hex: "#22c55e" },
  { name: "amber", hex: "#f59e0b" },
  { name: "coral", hex: "#fb7185" },
  { name: "magenta", hex: "#d946ef" },
  { name: "neutral", hex: "#8b8fa3" },
];

const STORAGE_KEY = "apex.kest.theme";
const DEFAULT: ThemeState = { mode: "dark", accent: "#7c73ff" };

interface ThemeContextValue extends ThemeState {
  resolvedMode: "light" | "dark";
  setMode: (mode: Mode) => void;
  setAccent: (accent: string) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function load(): ThemeState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return DEFAULT;
}

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ThemeState>(load);
  const [systemDark, setSystemDark] = useState<boolean>(systemPrefersDark);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const resolvedMode: "light" | "dark" =
    state.mode === "system" ? (systemDark ? "dark" : "light") : state.mode;

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-mode", resolvedMode);
    root.style.setProperty("--accent", state.accent);
    root.style.setProperty("--on-accent", onAccentFor(state.accent));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state, resolvedMode]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      ...state,
      resolvedMode,
      setMode: (mode) => setState((s) => ({ ...s, mode })),
      setAccent: (accent) => setState((s) => ({ ...s, accent })),
    }),
    [state, resolvedMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
