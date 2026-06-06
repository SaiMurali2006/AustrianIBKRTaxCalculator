import { Card, DataTable, Disclosure, eur, Notice, SectionLabel, StatCard, Pill, Button } from "../components/primitives";
import { ChartCard } from "../components/Chart";
import { baseAxis, baseTooltip } from "../theme/chartTheme";
import { exportUrl, type CalcResult } from "../api/client";

export function ExecutiveSummary({ result, includeFees }: { result: CalcResult; includeFees: boolean }) {
  const f = result.e1kv_fields;
  const year = result.tax_year ? String(result.tax_year) : "unknown";

  const cards: { label: string; value: number; tone?: "pos" | "neg"; tip: string }[] = [
    { label: "KZ 994 · Stock realized gains", value: f["994"], tone: "pos",
      tip: "Realized gains from foreign stock/ETF/bond sales. Moving-average cost basis. E1kv row 994 (27.5% basket)." },
    { label: "KZ 857 · Derivative net", value: f["857"], tone: f["857"] < 0 ? "neg" : "pos",
      tip: "Einkünfte aus nicht verbrieften Derivaten — net options/futures/FOP gains & losses, signed (§27 Abs 4). E1kv row 857." },
    { label: "KZ 892 · Realized losses", value: f["892"], tone: "neg",
      tip: "Foreign securities Substanzverluste (§27 Abs 3). Offset within the 27.5% basket only, no carry-forward. E1kv row 892." },
    { label: "KZ 863 · Foreign dividends", value: f["863"], tone: "pos",
      tip: "Gross foreign dividends before tax. Bond coupons go to KZ 409; WHT tracked in KZ 998. E1kv row 863." },
    { label: "KZ 998 · Creditable WHT (27.5%)", value: f["998"],
      tip: "Foreign WHT credited against Austrian KeSt, capped at 15% of gross per DBA. Excess shown below. E1kv row 998." },
    { label: "KeSt Due", value: result.tax_due, tone: "neg",
      tip: "Final Austrian KeSt: 27.5% securities + 25% bank interest, minus foreign tax credit. Declare via FinanzOnline." },
  ];

  const mapping = [
    ["994", "Auslaend. Substanzgewinne Aktien/ETF/Anleihen (27,5%)", f["994"]],
    ["892", "Realisierte Verluste (27,5%)", f["892"]],
    ["857", "Eink. aus nicht verbrieften Derivaten (27,5%)", f["857"]],
    ["863", "Auslandsdividenden (27,5%)", f["863"]],
    ["409", "Auslaend. Anleihezinsen / Forderungswertpapiere (27,5%)", f["409"]],
    ["861", "Auslaend. Sparbuch-/Bankzinsen (25%)", f["861"]],
    ["998", "Anrechenbare ausl. Quellensteuer (27,5%)", f["998"]],
    ["901", "Anrechenbare ausl. Quellensteuer (25%)", f["901"]],
  ];

  const grossKest27 = result.taxable_27 * 0.275;
  const grossKest25 = result.taxable_25 * 0.25;

  return (
    <div className="view">
      <span className="eyebrow">Austria E1kv Digital Tax Report</span>
      <h1 className="page-title">Capital Gains Tax Dashboard</h1>
      <p className="subtitle">
        Stocks, options, dividends and interest mapped into the Austrian E1kv form with EUR conversion,
        gain/loss separation, and the 25% / 27.5% basket split required by §27a EStG.
      </p>

      <div className="grid grid--3" style={{ marginTop: 16 }}>
        {cards.map((c) => (
          <StatCard key={c.label} label={c.label} value={eur(c.value)} tone={c.tone} tip={c.tip} pulseKey={c.value} />
        ))}
      </div>

      {result.excess_wht > 0 && (
        <Notice kind="warn">
          {eur(result.excess_wht)} of foreign withholding tax exceeds the 15% DBA cap or the Austrian tax actually
          owed. Austria cannot credit this excess (§46 EStG) — reclaim it from the source country (e.g. IRS Form 1040-NR
          for US withholding above 15%).
        </Notice>
      )}
      {(result.bond_interest_total !== 0 || result.bank_interest_total !== 0) && (
        <Notice kind="info">
          Bond and bank interest WHT is capped at 15% per income type. Most DBA treaties (US, DE, most EU) cap interest
          WHT at 0–10% — verify the treaty for the issuer/bank country and reclaim any over-withheld amount.
        </Notice>
      )}
      {result.excluded_isins.length > 0 && (
        <Notice kind="ok">Pre-2011 Altbestand excluded from KeSt calculation: {result.excluded_isins.join(", ")}</Notice>
      )}

      <div className="pill-row" style={{ marginTop: 12 }}>
        <Pill tip="Sum of taxable income in the 27.5% basket: stock + derivative gains + dividends + bond interest, minus losses. Floored at zero.">
          27.5% basket: {eur(result.taxable_27)}
        </Pill>
        <Pill tip="Bank/savings deposit interest only. Cannot be offset against securities losses (§27a Abs. 2 EStG).">
          25% basket: {eur(result.taxable_25)}
        </Pill>
        <Pill>
          {includeFees ? "Fees: included in basis" : "Fees: excluded (§20 Abs. 2 EStG)"}
        </Pill>
      </div>

      <div className="grid grid--2" style={{ marginTop: 16 }}>
        <Card>
          <div className="chart-card__title">E1kv Field Mapping</div>
          <DataTable
            columns={["E1kv Field", "Meaning", "Amount EUR"]}
            rows={mapping.map(([fld, mean, amt]) => ({ "E1kv Field": fld as string, Meaning: mean as string, "Amount EUR": amt as number }))}
          />
        </Card>
        <ChartCard
          title="Category P/L"
          build={(t) => {
            const entries = Object.entries(result.category_totals);
            return {
              tooltip: { trigger: "axis", ...baseTooltip(t) },
              grid: { left: 8, right: 16, top: 16, bottom: 24, containLabel: true },
              xAxis: { type: "category", data: entries.map(([k]) => k), ...baseAxis(t) },
              yAxis: { type: "value", ...baseAxis(t) },
              series: [
                {
                  type: "bar",
                  data: entries.map(([, v]) => ({ value: v, itemStyle: { color: v >= 0 ? t.positive : t.danger } })),
                  itemStyle: { borderRadius: [4, 4, 0, 0] },
                },
              ],
            };
          }}
        />
      </div>

      <div style={{ marginTop: 12 }}>
        <a href={exportUrl("e1kv", result.calcKey)}>
          <Button variant="primary">Download E1kv CSV</Button>
        </a>
      </div>

      <hr className="hr" />

      <Disclosure title={`KeSt Calculation Breakdown — Tax Year ${year}`}>
        <SectionLabel>27.5% basket — stocks, derivatives, dividends, bond interest</SectionLabel>
        <div className="grid grid--3">
          <StatCard label="Taxable" value={eur(result.taxable_27)} />
          <StatCard label="Gross KeSt (×27.5%)" value={eur(grossKest27)} />
          <StatCard label="WHT credit used" value={`−${eur(result.foreign_tax_credit_27)}`} />
        </div>
        <SectionLabel>25% basket — bank/savings deposit interest</SectionLabel>
        <div className="grid grid--3">
          <StatCard label="Taxable" value={eur(result.taxable_25)} />
          <StatCard label="Gross KeSt (×25%)" value={eur(grossKest25)} />
          <StatCard label="WHT credit used" value={`−${eur(result.foreign_tax_credit_25)}`} />
        </div>
        <SectionLabel>Total</SectionLabel>
        <div className="grid grid--2">
          <StatCard label="Total KeSt Due" value={eur(result.tax_due)} tone="neg" />
          <StatCard label="Non-creditable WHT" value={eur(result.excess_wht)} />
        </div>
        <Notice kind="info">
          Securities acquired before 1 Jan 2011 (derivatives / interest-bearing: 31 Mar 2012) are grandfathered under
          §124b Z 185 EStG — use the Altbestand selector above. ETF/Fund rows (incl. ausschüttungsgleiche Erträge, KZ 937)
          are not auto-calculated — see the Manual ETF/Fund Queue.
        </Notice>
      </Disclosure>

      {result.manual_processing.length > 0 && (
        <>
          <Notice kind="warn">
            ETF/FUND rows detected — Austrian fund taxation (incl. ausschüttungsgleiche Erträge KZ 937, Meldefonds vs.
            Schwarze Fonds) requires per-fund OeKB review and is NOT included in the automatic KeSt calculation above.
          </Notice>
          <DataTable columns={result.manual_columns} rows={result.manual_processing} />
        </>
      )}
    </div>
  );
}
