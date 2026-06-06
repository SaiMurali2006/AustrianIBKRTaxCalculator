// ECharts theming (Design.md §13). The canvas cannot read CSS variables — resolve tokens to
// real color strings at runtime and recompute on every mode/accent change. Passing var(--x)
// strings renders fine at rest but turns transparent on emphasis (ECharts derives hover colors
// from the base), so we always resolve to concrete hex/rgb.

export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";
}

export interface ChartTokens {
  accent: string;
  accentAlt: string;
  positive: string;
  danger: string;
  muted: string;
  line: string;
  lineSoft: string;
  panel: string;
  text: string;
  series: string[];
}

export function resolveChartTokens(): ChartTokens {
  const accent = cssVar("--accent");
  const accentAlt = cssVar("--accent-alt");
  const positive = cssVar("--positive");
  const danger = cssVar("--danger");
  const muted = cssVar("--muted");
  return {
    accent,
    accentAlt,
    positive,
    danger,
    muted,
    line: cssVar("--line"),
    lineSoft: cssVar("--line-soft"),
    panel: cssVar("--panel"),
    text: cssVar("--text"),
    series: [accent, accentAlt, positive, danger, muted],
  };
}

export function baseAxis(t: ChartTokens) {
  return {
    axisLine: { lineStyle: { color: t.lineSoft } },
    axisTick: { lineStyle: { color: t.lineSoft } },
    axisLabel: { color: t.muted, fontFamily: "Cascadia Code, Consolas, monospace" },
    splitLine: { lineStyle: { color: t.lineSoft, type: "dashed" as const } },
    nameTextStyle: { color: t.muted },
  };
}

export function baseTooltip(t: ChartTokens) {
  return {
    backgroundColor: t.panel,
    borderColor: t.line,
    borderWidth: 1,
    textStyle: { color: t.text, fontFamily: "Cascadia Code, Consolas, monospace" },
    extraCssText: "border-radius:14px; box-shadow:0 10px 32px rgba(0,0,0,0.45);",
  };
}
