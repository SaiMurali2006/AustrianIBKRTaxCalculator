import { useRef } from "react";
import { Button, Card, Toggle } from "../components/primitives";
import { IconUpload, IconClose } from "../components/icons";
import type { Broker, ParseResult } from "../api/client";

export interface ControlsState {
  broker: string;
  file: File | null;
  fileName: string;
  useSample: boolean;
  includeFees: boolean;
  excludedIsins: string[];
  altQuantities: Record<string, number>;
}

export function Controls({
  brokers,
  parse,
  state,
  set,
  reset,
  busy,
  hasInput,
}: {
  brokers: Broker[];
  parse: ParseResult | null;
  state: ControlsState;
  set: (patch: Partial<ControlsState>) => void;
  reset: () => void;
  busy: boolean;
  hasInput: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const sampleBroker = brokers.find((b) => b.name === state.broker);

  const clearFile = () => {
    if (fileRef.current) fileRef.current.value = "";
    set({ file: null, fileName: "" });
  };

  const toggleIsin = (isin: string) => {
    const has = state.excludedIsins.includes(isin);
    set({ excludedIsins: has ? state.excludedIsins.filter((i) => i !== isin) : [...state.excludedIsins, isin] });
  };

  return (
    <Card className={`stack ${busy ? "card--loading" : ""}`}>
      <div className="row-between">
        <span className="eyebrow">Statement input</span>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {busy && <span className="statcard__sub" style={{ margin: 0 }}>working…</span>}
          {hasInput && (
            <Button onClick={reset} title="Clear the uploaded statement and reset">
              <IconClose size={14} />
              Clear
            </Button>
          )}
        </div>
      </div>
      <div className="grid grid--3">
        <div className="stack">
          <label className="field-label">Broker</label>
          <select className="select" value={state.broker} onChange={(e) => set({ broker: e.target.value, file: null, fileName: "" })}>
            {brokers.map((b) => <option key={b.name}>{b.name}</option>)}
          </select>
        </div>

        <div className="stack">
          <label className="field-label">Statement file (XML)</label>
          <input
            ref={fileRef}
            type="file"
            accept=".xml"
            style={{ display: "none" }}
            // Reset the value on every open so re-selecting the SAME file still fires onChange
            // (after a Clear the element keeps its old filename → no change event otherwise).
            onClick={(e) => {
              (e.currentTarget as HTMLInputElement).value = "";
            }}
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              set({ file: f, fileName: f?.name ?? "", useSample: false });
            }}
          />
          <div style={{ display: "flex", gap: 6 }}>
            <Button onClick={() => fileRef.current?.click()} className="grow">
              <IconUpload size={15} />
              <span>{state.fileName || "Choose file…"}</span>
            </Button>
            {state.fileName && (
              <Button variant="icon" onClick={clearFile} title="Remove file">
                <IconClose size={15} />
              </Button>
            )}
          </div>
        </div>

        <div className="stack" style={{ justifyContent: "flex-end", gap: 12 }}>
          <Toggle
            label="Use embedded sample"
            checked={state.useSample}
            onChange={(v) => set({ useSample: v, file: v ? null : state.file, fileName: v ? "" : state.fileName })}
            tip="Load a built-in demonstration file to preview the dashboard without a real statement."
          />
          <Toggle
            label="Include fees in tax basis"
            checked={state.includeFees}
            onChange={(v) => set({ includeFees: v })}
            tip="OFF (default) — Austrian §20 Abs. 2 EStG: brokerage commissions are non-deductible. ON — fees folded into cost basis / proceeds (business accounts / non-AT). Fee amounts always remain visible in the Audit Trail."
          />
        </div>
      </div>

      {!sampleBroker?.hasSample && state.useSample && (
        <div className="statcard__sub">This broker has no embedded sample.</div>
      )}

      {parse && parse.altbestandCandidates.length > 0 && (
        <div className="stack">
          <label className="field-label">Pre-2011 Altbestand (exempt — §124b Z 185 EStG)</label>
          <div className="chips">
            {parse.altbestandCandidates.map((c) => {
              const on = state.excludedIsins.includes(c.isin);
              return (
                <button key={c.isin} className={`chip ${on ? "active" : ""}`} onClick={() => toggleIsin(c.isin)}>
                  {c.label}
                </button>
              );
            })}
          </div>
          {state.excludedIsins.length > 0 && (
            <>
              <div className="statcard__sub">Altbestand quantity per ISIN (leave 0 to treat all units as exempt):</div>
              <div className="grid grid--3">
                {state.excludedIsins.map((isin) => (
                  <div className="stack" key={isin}>
                    <label className="field-label">{isin}</label>
                    <input
                      className="input mono"
                      type="number"
                      min={0}
                      step={1}
                      value={state.altQuantities[isin] ?? 0}
                      onChange={(e) =>
                        set({ altQuantities: { ...state.altQuantities, [isin]: Math.max(0, Number(e.target.value) || 0) } })
                      }
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
