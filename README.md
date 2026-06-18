# Austrian KESt Tax Engine

Web dashboard that ingests brokerage statement data, calculates Austrian capital gains tax
(**KESt** — 27.5% securities basket, 25% bank-deposit basket), and maps results to **E1kv**
form *Kennzahlen* using the codes from the official BMF E1kv 2025 form. Supports **IBKR Flex
Query XML** today; adding a new broker is one file + two registry lines.

> ⚠️ **Calculation aid only — not tax advice.** Per §39 Abs 1 EStG all foreign-broker capital
> income above EUR 22 must be declared in your annual return (E1 + E1kv). Consult a qualified
> Austrian tax professional before filing.

---

## Architecture

A frozen Python tax engine, a thin FastAPI backend that only serializes, and a React UI:

```
Broker XML → parsers/<broker>.py → models.ParsedData
                                      ↓
                       tax_engine.TaxAggregator → models.TaxResult
                                      ↓
                  backend/ (FastAPI)  — serializes ParsedData/TaxResult → JSON (NO tax logic)
                                      ↓
                  frontend/ (React + TS + plain CSS)  — Apex Design Language UI
```

- **Engine** (`models.py`, `parsers/`, `tax_engine.py`, `currency_provider.py`) — the single
  source of truth for all tax/E1kv logic. Standard library + pandas only.
- **Backend** (`backend/`) — FastAPI. Parses → serializes. Adds **no** tax logic.
- **Frontend** (`frontend/`) — Vite + React + TypeScript implementing the **Apex Design
  Language** (`Design.md`): `color-mix()` token theme, live light/dark/system + accent switcher,
  ECharts. Plain CSS custom properties — no CSS framework.

The Streamlit UI (`app.py` + `styles.py`) was retired in the Apex migration. See
[`CLAUDE.md`](CLAUDE.md) for the full engine contract and [`Design.md`](Design.md) for the
binding visual contract.

---

## Prerequisites

- **Python 3.12** with a virtual environment at `venv/`
- **Node.js 18+** (developed on Node 22) and npm

---

## Running locally

Two processes, both started **from the repo root** (so the engine's absolute imports resolve).

### 1. Backend (FastAPI) — terminal 1

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt          # first run only
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend (Vite dev server) — terminal 2

```powershell
npm install --prefix frontend            # first run only
npm run dev --prefix frontend
```

Open **http://localhost:5173**. Vite proxies `/api` → `http://127.0.0.1:8000`, so **both
processes must be running**.

**Quick preview:** toggle **“Use embedded sample”** in the dashboard — it loads built-in demo
data, no upload required.

### Using your own statement

In IBKR: **Reports → Flex Queries**, create a query that includes **Trades** and **Cash
Transactions**, run it, and download the **XML**. Upload it via *Choose file…*; the **✕** next
to the file, or **Clear** in the input card, resets everything. Export **one Flex Query per
calendar year** — §27a EStG forbids cross-year loss offsets for private investors, and the
engine rejects multi-year statements (HTTP 422).

---

## Other commands

| Task | Command |
|---|---|
| Engine smoke test (no server) | `python smoke_test.py` |
| Frontend type-check + production build | `npm run build --prefix frontend` |
| Frontend preview of the build | `npm run preview --prefix frontend` |

---

## API surface (`backend/main.py`)

| Method | Route | Purpose |
|---|---|---|
| `GET`  | `/api/brokers` | List brokers `[{name, hasSample}]` from the registry |
| `POST` | `/api/parse` | Multipart `broker` + `file` **or** `use_sample`. Caches `ParsedData` by content hash; returns `{parseKey, years, counts, altbestandCandidates}`. **422** on a multi-year statement |
| `POST` | `/api/calculate` | JSON `{parseKey, includeFees, excludedIsins, altbestandQuantities}` → full serialized `TaxResult` (incl. `performance` and `tax_timeline` blocks) + `calcKey` |
| `GET`  | `/api/export/{kind}?calcKey=` | `kind ∈ {e1kv, audit, manual}` → streamed `text/csv` |

A two-step in-memory cache mirrors the engine's old session caching: parse is keyed by the
statement's md5; calculate is keyed additionally by the options, so toggling fees or the
Altbestand selection recalculates without re-parsing.

---

## Tax model (summary)

| Kennzahl | Meaning | Basket |
|---|---|---|
| `994` | Foreign stock/ETF/bond realized **gains** (Substanzgewinne) | 27.5% |
| `892` | Foreign stock/ETF/bond realized **losses** (§27 Abs 3) | 27.5% |
| `857` | Non-securitised **derivatives** w/o freiwilliger Steuerabzug — gains AND losses, signed net (§27a Abs. 2) | **General tariff** (27.5% est.) |
| `863` | Foreign **dividends** + **bond coupon interest** (§27 Abs. 2) | 27.5% |
| `861` | Foreign **bank deposit interest** | **25%** |
| `998` | Creditable foreign WHT (27.5% basket), capped at 15% **per income type** per DBA | — |
| `901` | Creditable foreign WHT (25% basket) | — |

- **Two baskets, no cross-netting:** 27.5% securities vs 25% bank interest. Within a basket,
  gains net against losses in the same calendar year; no carry-forward for private investors.
- **WHT credit cap** is applied per income type (dividends and bond interest each get their own
  15% headroom); non-creditable excess is surfaced as `excess_wht` to reclaim from the source
  country.
- **Fees** default to non-deductible (Austrian §20 Abs. 2 EStG); a toggle includes them
  (business / non-Austrian accounts). The actual fee is always shown in the audit trail.
- **Pre-2011 Altbestand** (§124b Z 185 EStG) is exempt — mark ISINs (and optional per-ISIN
  quantities) in the dashboard; SELLs deplete the exempt pool first.
- **ETFs/Funds**, **Payment-in-Lieu**, **securitised derivatives** (WAR/IOPT), and **corporate
  actions** are routed to manual-review queues, not auto-calculated.
- **FX:** ECB reference rate for the trade date → nearest prior business day → IBKR
  `fxRateToBase` → `1.0` fallback. Never crashes; every value carries an FX-source audit record.

Full legal rationale and Kennzahl notes live in [`CLAUDE.md`](CLAUDE.md).

---

## Frontend views

- **Executive Summary** — six StatCards (KZ 994 / 857 / 892 / 863 / 998 + KeSt Due), status
  pills (baskets, fee mode), E1kv mapping table, Category P/L chart, WHT/interest/Altbestand
  notices, a KeSt calculation breakdown, the manual ETF/Fund queue, and an E1kv CSV download.
- **Detailed Audit Trail** — the per-line transaction audit plus the manual ETF/Fund, Payment-
  in-Lieu, and corporate-actions queues, each with CSV export where applicable.
- **Performance** — realized STK/OPT trades only: P/L / fees / estimated KeSt / effective-rate
  StatCards, a cumulative P/L timeline, a monthly gains/fees/tax breakdown, and top holdings.
- **Tax Pot** — a running KeSt set-aside tracker. Walks **every taxable event** (stock/option
  realizations, dividends, bond/bank interest, WHT credits) in date order and recomputes the full
  §27a liability after each, so the pot reflects within-basket gain/loss netting and per-type WHT
  credits as they accrue — the final pot equals the headline `tax_due`. Shows the running pot,
  each event's tax **delta** (negative when a loss offsets prior gains and the pot shrinks), and a
  **To Taxable Again** figure: when accumulated losses drive a basket negative, the amount future
  trades must earn back before any new tax is owed. Hero StatCards + a pot-over-time chart + an
  event ledger.

Theme is switched from the **logo badge** (top-left): light / dark / system + 8 accent presets +
a custom hex input, persisted to `localStorage`. The whole UI (and every chart) recolors live.

---

## Adding a new broker

1. Create `parsers/<broker_slug>.py` exposing `parse(source: str | Path | bytes) -> ParsedData`.
2. Map your broker's fields to `models.TRADE_COLUMNS` / `models.CASH_COLUMNS`.
3. Add one entry each to `BROKER_REGISTRY` (and optionally `BROKER_SAMPLES`) in
   `parsers/__init__.py`.

The tax engine, backend, and UI require zero changes — the UI populates the broker selector from
`/api/brokers`.

---

## Project layout

```
models.py            ParsedData / TaxResult / column constants
parsers/             broker parsers + BROKER_REGISTRY (ibkr_flex.py)
tax_engine.py        TaxAggregator + E1kv mapping (broker-agnostic)
currency_provider.py ECB EUR conversion + cache
backend/
  main.py            FastAPI endpoints + two-step cache
  serialize.py       DataFrame/dataclass → JSON (+ performance & tax_timeline blocks)
frontend/
  src/theme/         tokens.css, ThemeProvider, onAccent, chartTheme
  src/components/    AppShell (+LogoBadge/ThemePopover/SegmentedControl), primitives, Chart, icons
  src/views/         Controls, ExecutiveSummary, AuditTrail, Performance, TaxPot
  src/api/client.ts  typed fetch wrapper
smoke_test.py        engine verification
```
