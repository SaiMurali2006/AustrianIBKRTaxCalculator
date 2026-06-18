import { useEffect, useMemo, useState } from "react";
import { AppShell, type NavItem } from "./components/AppShell";
import { IconSummary, IconAudit, IconPerf, IconPot, IconUpload } from "./components/icons";
import { EmptyState, Notice } from "./components/primitives";
import { Controls, type ControlsState } from "./views/Controls";
import { ExecutiveSummary } from "./views/ExecutiveSummary";
import { AuditTrail } from "./views/AuditTrail";
import { Performance } from "./views/Performance";
import { TaxPot } from "./views/TaxPot";
import {
  calculate,
  getBrokers,
  parseStatement,
  type Broker,
  type CalcResult,
  type ParseResult,
} from "./api/client";

const NAV: NavItem[] = [
  { id: "summary", label: "Executive Summary", icon: <IconSummary size={20} /> },
  { id: "audit", label: "Detailed Audit Trail", icon: <IconAudit size={20} /> },
  { id: "performance", label: "Performance", icon: <IconPerf size={20} /> },
  { id: "taxpot", label: "Tax Pot", icon: <IconPot size={20} /> },
];

const INITIAL: ControlsState = {
  broker: "",
  file: null,
  fileName: "",
  useSample: false,
  includeFees: false,
  excludedIsins: [],
  altQuantities: {},
};

export default function App() {
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [ctrl, setCtrl] = useState<ControlsState>(INITIAL);
  const [parse, setParse] = useState<ParseResult | null>(null);
  const [result, setResult] = useState<CalcResult | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState("summary");

  const set = (patch: Partial<ControlsState>) => setCtrl((s) => ({ ...s, ...patch }));
  const reset = () =>
    setCtrl((s) => ({ ...INITIAL, broker: s.broker, includeFees: s.includeFees }));

  useEffect(() => {
    getBrokers().then((b) => {
      setBrokers(b);
      if (b.length) setCtrl((s) => ({ ...s, broker: b[0].name }));
    });
  }, []);

  const hasInput = ctrl.broker && (ctrl.file || ctrl.useSample);

  // Parse step — keyed on (broker, file, useSample). Resets the Altbestand selection.
  useEffect(() => {
    if (!hasInput) {
      setParse(null);
      setResult(null);
      setParseError(null);
      setBusy(false);
      return;
    }
    let cancelled = false;
    setBusy(true);
    setParseError(null);
    parseStatement(ctrl.broker, ctrl.file, ctrl.useSample)
      .then((p) => {
        if (cancelled) return;
        setParse(p);
        setCtrl((s) => ({ ...s, excludedIsins: [], altQuantities: {} }));
      })
      .catch((e) => {
        if (cancelled) return;
        setParse(null);
        setResult(null);
        setParseError(e.message);
      })
      .finally(() => !cancelled && setBusy(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctrl.broker, ctrl.file, ctrl.useSample]);

  const calcSig = useMemo(
    () =>
      JSON.stringify({
        k: parse?.parseKey,
        f: ctrl.includeFees,
        x: [...ctrl.excludedIsins].sort(),
        q: ctrl.altQuantities,
      }),
    [parse?.parseKey, ctrl.includeFees, ctrl.excludedIsins, ctrl.altQuantities],
  );

  // Calculate step — re-fires on any calc input without re-parsing (mirrors the two-step cache).
  useEffect(() => {
    if (!parse) return;
    let cancelled = false;
    setBusy(true);
    calculate({
      parseKey: parse.parseKey,
      includeFees: ctrl.includeFees,
      excludedIsins: ctrl.excludedIsins,
      altbestandQuantities: ctrl.altQuantities,
    })
      .then((r) => !cancelled && setResult(r))
      .catch((e) => !cancelled && setParseError(e.message))
      .finally(() => !cancelled && setBusy(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calcSig]);

  return (
    <AppShell nav={NAV} active={view} onNavigate={setView}>
      {ctrl.useSample && parse && (
        <Notice kind="info">Showing embedded sample data — upload your own statement to calculate real results.</Notice>
      )}

      <Controls brokers={brokers} parse={parse} state={ctrl} set={set} reset={reset} busy={busy} hasInput={!!hasInput} />

      {parseError && <Notice kind="warn">{parseError}</Notice>}

      {!hasInput && !parseError && (
        <EmptyState
          icon={<IconUpload size={28} />}
          title="Upload a statement to begin"
          body="Choose an IBKR Flex Query XML export, or enable the embedded sample to preview the dashboard."
        />
      )}

      {result && view === "summary" && <ExecutiveSummary result={result} includeFees={ctrl.includeFees} />}
      {result && view === "audit" && <AuditTrail result={result} />}
      {result && view === "performance" && <Performance result={result} />}
      {result && view === "taxpot" && <TaxPot result={result} />}

      {result && (
        <div className="footer">
          Austrian KeSt Engine — calculation aid only, not tax advice. Per §39 Abs 1 EStG all foreign-broker capital
          income above EUR 22 must be declared in your annual return (E1 + E1kv). Consult a qualified Austrian tax
          professional before filing.
          {busy ? " · recalculating…" : ""}
        </div>
      )}
    </AppShell>
  );
}
