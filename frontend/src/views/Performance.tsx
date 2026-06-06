import { EmptyState, eur, StatCard } from "../components/primitives";
import { IconPerf } from "../components/icons";
import { ChartCard } from "../components/Chart";
import { baseAxis, baseTooltip } from "../theme/chartTheme";
import type { CalcResult } from "../api/client";

export function Performance({ result }: { result: CalcResult }) {
  const p = result.performance;
  if (p.trades.length === 0) {
    return (
      <div className="view">
        <EmptyState
          icon={<IconPerf size={28} />}
          title="No realized trades yet"
          body="Upload a statement with closed positions to see cumulative P/L, monthly breakdown, and top holdings."
        />
      </div>
    );
  }
  const s = p.summary;

  return (
    <div className="view">
      <span className="eyebrow">Trading performance</span>
      <h1 className="page-title">Performance</h1>
      <p className="subtitle">Realized STK/OPT trades only — Altbestand-exempt rows excluded.</p>

      <div className="grid grid--2" style={{ marginTop: 16 }}>
        <StatCard label="Total Realized P/L" value={eur(s.total_pnl)} tone={s.total_pnl >= 0 ? "pos" : "neg"} />
        <StatCard label="Total Fees Paid" value={eur(s.total_fees)} />
        <StatCard label="Estimated KeSt" value={eur(s.est_tax)} tone="neg"
          tip="Gross gains × 27.5% — ignores loss offsets and credits." />
        <StatCard label="Effective Rate" value={`${(s.effective_rate * 100).toFixed(1)}%`}
          tip="(Fees + estimated KeSt) ÷ gross gains — total drag on winning trades." />
      </div>

      <div style={{ marginTop: 16 }}>
        <ChartCard
          title="Cumulative Realized P/L"
          height={380}
          build={(t) => ({
            tooltip: { trigger: "axis", ...baseTooltip(t) },
            grid: { left: 8, right: 20, top: 20, bottom: 30, containLabel: true },
            xAxis: { type: "category", data: p.trades.map((r) => r.date), ...baseAxis(t) },
            yAxis: { type: "value", name: "EUR", ...baseAxis(t) },
            series: [
              {
                type: "line",
                data: p.trades.map((r) => r.cumulative_pnl),
                smooth: false,
                showSymbol: true,
                symbolSize: 7,
                lineStyle: { color: t.accent, width: 2 },
                itemStyle: {
                  color: (d: { dataIndex: number }) =>
                    p.trades[d.dataIndex].realized_pnl_eur > 0 ? t.positive : t.danger,
                },
                areaStyle: { color: t.accent, opacity: 0.16 },
                markLine: {
                  symbol: "none",
                  data: [{ yAxis: 0 }],
                  lineStyle: { color: t.lineSoft, type: "dashed" },
                  label: { show: false },
                },
              },
            ],
          })}
        />
      </div>

      <div className="grid grid--2" style={{ marginTop: 16 }}>
        <ChartCard
          title="Monthly Breakdown"
          height={300}
          build={(t) => ({
            tooltip: { trigger: "axis", ...baseTooltip(t) },
            legend: { textStyle: { color: t.muted }, top: 0 },
            grid: { left: 8, right: 16, top: 32, bottom: 24, containLabel: true },
            xAxis: { type: "category", data: p.monthly.map((m) => m.month), ...baseAxis(t) },
            yAxis: { type: "value", name: "EUR", ...baseAxis(t) },
            series: [
              { name: "Gains", type: "bar", data: p.monthly.map((m) => m.gains), itemStyle: { color: t.positive, borderRadius: [3, 3, 0, 0] } },
              { name: "Fees", type: "bar", data: p.monthly.map((m) => m.fees), itemStyle: { color: t.accentAlt, borderRadius: [3, 3, 0, 0] } },
              { name: "Est. KeSt", type: "bar", data: p.monthly.map((m) => m.est_tax), itemStyle: { color: t.danger, borderRadius: [3, 3, 0, 0] } },
            ],
          })}
        />
        <ChartCard
          title="Top Holdings by P/L"
          height={300}
          build={(t) => ({
            tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...baseTooltip(t) },
            grid: { left: 8, right: 20, top: 16, bottom: 24, containLabel: true },
            xAxis: { type: "value", name: "EUR", ...baseAxis(t) },
            yAxis: { type: "category", data: p.holdings.map((h) => h.symbol), ...baseAxis(t) },
            series: [
              {
                type: "bar",
                data: p.holdings.map((h) => ({ value: h.total_pnl, itemStyle: { color: h.total_pnl >= 0 ? t.positive : t.danger } })),
                itemStyle: { borderRadius: [0, 3, 3, 0] },
              },
            ],
          })}
        />
      </div>
    </div>
  );
}
