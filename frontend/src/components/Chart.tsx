import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { useTheme } from "../theme/ThemeProvider";
import { resolveChartTokens, type ChartTokens } from "../theme/chartTheme";

// ChartCard wraps an ECharts canvas. The builder receives resolved real-color tokens (never
// var() strings — §13), and we key the chart on mode|accent so it remounts and recolors live.
export function ChartCard({
  title,
  height = 300,
  build,
}: {
  title: string;
  height?: number;
  build: (t: ChartTokens) => EChartsOption;
}) {
  const { resolvedMode, accent } = useTheme();
  const tokens = resolveChartTokens();
  return (
    <div className="card">
      <div className="chart-card__title">{title}</div>
      <ReactECharts
        key={`${resolvedMode}|${accent}`}
        option={build(tokens)}
        style={{ height }}
        notMerge
        lazyUpdate
      />
    </div>
  );
}
