// Typed fetch wrapper for the FastAPI backend. Vite proxies /api → 127.0.0.1:8000.

export interface Broker {
  name: string;
  hasSample: boolean;
}

export interface AltbestandCandidate {
  label: string;
  isin: string;
}

export interface ParseResult {
  parseKey: string;
  years: number[];
  counts: { stocks: number; options: number; funds: number };
  altbestandCandidates: AltbestandCandidate[];
}

export type Row = Record<string, string | number | null>;

export interface PerfSummary {
  total_pnl: number;
  total_fees: number;
  est_tax: number;
  effective_rate: number;
}

export interface Performance {
  trades: { date: string; symbol: string; category: string; realized_pnl_eur: number; commission_eur: number; cumulative_pnl: number }[];
  monthly: { month: string; gains: number; losses: number; fees: number; est_tax: number }[];
  holdings: { symbol: string; total_pnl: number; total_fees: number; trade_count: number }[];
  summary: PerfSummary;
}

export interface CalcResult {
  calcKey: string;
  e1kv_fields: Record<string, number>;
  category_totals: Record<string, number>;
  audit: Row[];
  audit_columns: string[];
  manual_processing: Row[];
  manual_columns: string[];
  pil_payments: Row[];
  pil_columns: string[];
  corporate_actions: Row[];
  corporate_columns: string[];
  tax_due: number;
  foreign_tax_credit: number;
  taxable_27: number;
  taxable_25: number;
  stock_gain_total: number;
  stock_loss_total: number;
  deriv_gain_total: number;
  deriv_loss_total: number;
  dividend_total: number;
  bond_interest_total: number;
  bank_interest_total: number;
  excess_wht: number;
  foreign_tax_credit_27: number;
  foreign_tax_credit_25: number;
  excluded_isins: string[];
  tax_year: number | null;
  performance: Performance;
}

export class ApiError extends Error {}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(detail);
  }
  return res.json() as Promise<T>;
}

export async function getBrokers(): Promise<Broker[]> {
  return asJson(await fetch("/api/brokers"));
}

export async function parseStatement(
  broker: string,
  file: File | null,
  useSample: boolean,
): Promise<ParseResult> {
  const form = new FormData();
  form.append("broker", broker);
  form.append("use_sample", String(useSample));
  if (file) form.append("file", file);
  return asJson(await fetch("/api/parse", { method: "POST", body: form }));
}

export async function calculate(body: {
  parseKey: string;
  includeFees: boolean;
  excludedIsins: string[];
  altbestandQuantities: Record<string, number>;
}): Promise<CalcResult> {
  return asJson(
    await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export function exportUrl(kind: "e1kv" | "audit" | "manual", calcKey: string): string {
  return `/api/export/${kind}?calcKey=${encodeURIComponent(calcKey)}`;
}
