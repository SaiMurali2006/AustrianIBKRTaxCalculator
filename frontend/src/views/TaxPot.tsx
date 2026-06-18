import { EmptyState, eur, Notice, StatCard } from "../components/primitives";
import { IconPot } from "../components/icons";
import { ChartCard } from "../components/Chart";
import { baseAxis, baseTooltip } from "../theme/chartTheme";
import type { CalcResult } from "../api/client";

export function TaxPot({ result }: { result: CalcResult }) {
  const t = result.tax_timeline;
  if (t.length === 0) {
    return (
      <div className="view">
        <EmptyState
          icon={<IconPot size={28} />}
          title="No taxable events yet"
          body="Upload a statement with closed positions, dividends, or interest to watch the tax pot fill up event by event."
        />
      </div>
    );
  }

  const last = t[t.length - 1];
  const currentPot = last.tax_pot;
  const currentRecover = last.recover_eur;
  const largestHit = Math.max(0, ...t.map((r) => r.tax_delta));
  const totalOffset = t.reduce((s, r) => (r.tax_delta < 0 ? s + r.tax_delta : s), 0);

  return (
    <div className="view">
      <span className="eyebrow">Set-aside tracker</span>
      <h1 className="page-title">Tax Pot</h1>
      <p className="subtitle">
        Every taxable event in date order, the running KeSt you should have set aside at that moment, and how much each
        event moved the pot. The final pot equals the headline tax due — a loss that offsets earlier gains shows a
        negative delta and the pot shrinks.
      </p>

      <div className="grid grid--2" style={{ marginTop: 16 }}>
        <StatCard label="Current Tax Pot" value={eur(currentPot)} tone="neg" pulseKey={currentPot}
          tip="Cumulative KeSt liability after the last event — the amount to keep aside for the Finanzamt." />
        <StatCard label="Events Tracked" value={String(t.length)}
          tip="Taxable rows that moved the pot (Altbestand-exempt rows excluded)." />
        <StatCard label="Largest Single Tax Hit" value={eur(largestHit)} tone="neg"
          tip="Biggest pot increase from one event." />
        {currentRecover > 0 ? (
          <StatCard label="To Taxable Again" value={eur(currentRecover)} tone="pos" pulseKey={currentRecover}
            tip="Accumulated losses have driven the basket negative. Future trades must earn back this much taxable income before any new KeSt is owed." />
        ) : (
          <StatCard label="Offset by Losses" value={eur(totalOffset)} tone="pos"
            tip="Sum of negative deltas — pot reductions where losses netted against prior gains." />
        )}
      </div>

      {currentRecover > 0 && (
        <div style={{ marginTop: 16 }}>
          <Notice kind="warn">
            Losses currently exceed your taxable gains by {eur(currentRecover)}. The tax pot stays empty until your next
            trades earn back that amount — only profit beyond it is taxed again.
          </Notice>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <ChartCard
          title="Tax Pot Over Time"
          height={380}
          build={(c) => ({
            tooltip: { trigger: "axis", ...baseTooltip(c) },
            grid: { left: 8, right: 20, top: 20, bottom: 30, containLabel: true },
            xAxis: { type: "category", data: t.map((r) => r.date), ...baseAxis(c) },
            yAxis: { type: "value", name: "EUR", ...baseAxis(c) },
            series: [
              {
                type: "line",
                data: t.map((r) => r.tax_pot),
                smooth: false,
                showSymbol: true,
                symbolSize: 7,
                lineStyle: { color: c.accent, width: 2 },
                itemStyle: {
                  color: (d: { dataIndex: number }) =>
                    t[d.dataIndex].tax_delta < 0 ? c.positive : c.danger,
                },
                areaStyle: { color: c.accent, opacity: 0.16 },
                markLine: {
                  symbol: "none",
                  data: [{ yAxis: 0 }],
                  lineStyle: { color: c.lineSoft, type: "dashed" },
                  label: { show: false },
                },
              },
            ],
          })}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        <h2 className="page-title" style={{ fontSize: "1.125rem" }}>Event Ledger</h2>
        <p className="subtitle" style={{ marginBottom: 10 }}>Each taxable line and its effect on the pot.</p>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Event</th>
                <th>Basket</th>
                <th>Taxable (EUR)</th>
                <th>Tax Δ</th>
                <th>Tax Pot</th>
                <th>To Taxable Again</th>
              </tr>
            </thead>
            <tbody>
              {t.map((r, i) => (
                <tr key={i}>
                  <td>{r.date}</td>
                  <td>{r.symbol}</td>
                  <td>{r.event}</td>
                  <td>{r.basket}</td>
                  <td className={`num ${r.taxable_eur > 0 ? "pos" : r.taxable_eur < 0 ? "neg" : ""}`}>
                    {r.taxable_eur.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className={`num ${r.tax_delta > 0 ? "neg" : r.tax_delta < 0 ? "pos" : ""}`}>
                    {r.tax_delta > 0 ? "+" : ""}
                    {r.tax_delta.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="num">
                    {r.tax_pot.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="num">
                    {r.recover_eur > 0
                      ? r.recover_eur.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <Notice kind="info">
          Estimate only. KZ 857 derivative income is taxed at your progressive tariff, not 27.5% — the pot uses 27.5% as a
          conservative placeholder. Bank interest is taxed at 25% in its own basket and cannot be offset by securities
          losses.
        </Notice>
      </div>
    </div>
  );
}
