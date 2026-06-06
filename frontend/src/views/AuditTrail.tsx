import { Button, DataTable, EmptyState, Notice } from "../components/primitives";
import { IconAudit, IconDownload } from "../components/icons";
import { exportUrl, type CalcResult } from "../api/client";

function Section({
  title,
  caption,
  columns,
  rows,
  emptyText,
  download,
}: {
  title: string;
  caption: string;
  columns: string[];
  rows: CalcResult["audit"];
  emptyText: string;
  download?: { kind: "audit" | "manual"; calcKey: string; label: string };
}) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 className="page-title" style={{ fontSize: "1.125rem" }}>{title}</h2>
      <p className="subtitle" style={{ marginBottom: 10 }}>{caption}</p>
      {rows.length === 0 ? (
        <Notice kind="ok">{emptyText}</Notice>
      ) : (
        <>
          <DataTable columns={columns} rows={rows} />
          {download && (
            <div style={{ marginTop: 10 }}>
              <a href={exportUrl(download.kind, download.calcKey)}>
                <Button><IconDownload size={15} />{download.label}</Button>
              </a>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function AuditTrail({ result }: { result: CalcResult }) {
  if (result.audit.length === 0 && result.manual_processing.length === 0) {
    return (
      <div className="view">
        <EmptyState
          icon={<IconAudit size={28} />}
          title="No taxable rows"
          body="No taxable trade or cash-income rows were found in the uploaded statement."
        />
      </div>
    );
  }
  return (
    <div className="view">
      <span className="eyebrow">Paper trail</span>
      <h1 className="page-title">Detailed Audit Trail</h1>
      <p className="subtitle">
        Trade-level EUR conversion, ECB FX source, cost-basis evolution, and realized P/L per line. Each row shows its
        assigned E1kv Kennzahl.
      </p>
      <div style={{ marginTop: 16 }}>
        <Section
          title="Transaction Audit"
          caption="Every parsed taxable line with its EUR conversion and Kennzahl."
          columns={result.audit_columns}
          rows={result.audit}
          emptyText="No taxable trade or cash income rows found."
          download={{ kind: "audit", calcKey: result.calcKey, label: "Download Transaction Audit CSV" }}
        />
        <Section
          title="Manual ETF/Fund Queue"
          caption="Rows flagged for manual OeKB review — Austrian fund taxation requires per-fund reporting. Accumulating ETFs generate ausschüttungsgleiche Erträge (KZ 937, 27.5%) annually."
          columns={result.manual_columns}
          rows={result.manual_processing}
          emptyText="No FUND rows detected."
          download={{ kind: "manual", calcKey: result.calcKey, label: "Download Manual Processing CSV" }}
        />
        <Section
          title="Payment in Lieu (PIL) Queue"
          caption="Securities-lending substitute payments (EStR Rz 6228 / §27 Abs 5 Z 4) — NOT §27 Abs 2 dividends. Excluded from KZ 863. Report at the progressive income tax rate per your tax advisor."
          columns={result.pil_columns}
          rows={result.pil_payments}
          emptyText="No PIL rows detected."
        />
        <Section
          title="Corporate Actions Queue"
          caption="Splits, spin-offs, mergers, name changes parsed from the broker statement. Cost-basis adjustments require manual handling — the engine does NOT auto-process them."
          columns={result.corporate_columns}
          rows={result.corporate_actions}
          emptyText="No corporate actions detected."
        />
      </div>
    </div>
  );
}
