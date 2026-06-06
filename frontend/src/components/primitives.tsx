import { useState, type ReactNode } from "react";
import { IconChevron, IconInfo, IconWarn, IconShield } from "./icons";
import type { Row } from "../api/client";

export function eur(value: number): string {
  return `EUR ${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

type Btn = {
  variant?: "ghost" | "primary" | "icon";
  children: ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ variant = "ghost", children, className = "", ...props }: Btn) {
  return (
    <button className={`btn btn--${variant} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function Pill({ children, eyebrow, tip }: { children: ReactNode; eyebrow?: boolean; tip?: string }) {
  return (
    <span className={`pill ${eyebrow ? "pill--eyebrow" : ""} ${tip ? "tip-host" : ""}`} data-tip={tip}>
      {children}
    </span>
  );
}

export function Card({ children, hover, className = "", tip }: { children: ReactNode; hover?: boolean; className?: string; tip?: string }) {
  return (
    <div className={`card ${hover ? "card--hover" : ""} ${tip ? "tip-host" : ""} ${className}`} data-tip={tip}>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  tone,
  sub,
  tip,
  pulseKey,
}: {
  label: string;
  value: string;
  tone?: "pos" | "neg";
  sub?: string;
  tip?: string;
  pulseKey?: string | number;
}) {
  return (
    <Card hover tip={tip}>
      <div className="statcard__label">{label}</div>
      <div className={`statcard__value ${tone ?? ""}`}>
        <span key={pulseKey} className="value-pulse">{value}</span>
      </div>
      {sub && <div className="statcard__sub">{sub}</div>}
    </Card>
  );
}

export function Notice({ kind, children }: { kind: "info" | "warn" | "ok"; children: ReactNode }) {
  const Icon = kind === "warn" ? IconWarn : kind === "ok" ? IconShield : IconInfo;
  return (
    <div className={`notice notice--${kind}`}>
      <Icon size={16} />
      <div>{children}</div>
    </div>
  );
}

export function EmptyState({ icon, title, body, cta }: { icon: ReactNode; title: string; body: string; cta?: ReactNode }) {
  return (
    <div className="empty">
      <div className="empty__badge">{icon}</div>
      <div className="empty__title">{title}</div>
      <div className="empty__body">{body}</div>
      {cta}
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <div className="section-label">{children}</div>;
}

export function Toggle({ label, checked, onChange, tip }: { label: string; checked: boolean; onChange: (v: boolean) => void; tip?: string }) {
  return (
    <label className={`toggle ${tip ? "tip-host" : ""}`} data-tip={tip}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle__track" />
      <span>{label}</span>
    </label>
  );
}

export function Disclosure({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="disclosure">
      <button className={`disclosure__head ${open ? "open" : ""}`} onClick={() => setOpen((o) => !o)}>
        <IconChevron size={14} />
        {title}
      </button>
      {open && <div className="disclosure__body">{children}</div>}
    </div>
  );
}

const NUMERIC_HINT = /(_eur|amount|rate|pnl|price|quantity|cost|tax|qty|gain|loss|total)/i;

function isNumeric(v: Row[string]): boolean {
  return typeof v === "number";
}

export function DataTable({ columns, rows }: { columns: string[]; rows: Row[] }) {
  const cols = columns.length ? columns : rows.length ? Object.keys(rows[0]) : [];
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => {
                const v = row[c];
                const num = isNumeric(v) && NUMERIC_HINT.test(c);
                const tone = num && typeof v === "number" ? (v > 0 ? "pos" : v < 0 ? "neg" : "") : "";
                const display =
                  typeof v === "number"
                    ? v.toLocaleString("en-US", { maximumFractionDigits: 4 })
                    : v ?? "";
                return (
                  <td key={c} className={num ? `num ${tone}` : ""}>
                    {display}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
