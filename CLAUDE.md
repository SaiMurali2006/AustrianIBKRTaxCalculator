# CLAUDE.md — Austrian KESt Tax Engine

## Project Purpose

Streamlit dashboard that ingests brokerage statement data, calculates Austrian capital gains tax (KESt, 27.5%), and maps results to E1kv tax form fields. Designed for IBKR Flex Query XML exports today; the architecture is broker-agnostic by intent.

**Primary goal:** maximum modularity so new broker statement formats can be added without touching the tax engine or UI.

---

## Architecture

```
Broker Statement (any format)
        ↓
  Broker Parser  (one per broker, lives in parsers/)
        ↓
  ParsedFlexData  (canonical data contract — shared across all brokers)
        ↓
  Tax Engine  (tax_engine.py — broker-unaware)
        ├── CapitalGainsProcessor   (stocks, moving-average cost basis)
        ├── DerivativeProcessor     (options/FOP/warrants)
        └── TaxAggregator           (orchestrator + E1kv field mapping)
        ↓
  TaxResult  (output contract)
        ↓
  Streamlit UI  (app.py — result-unaware of source broker)
```

The canonical boundary is `ParsedFlexData`. Any broker parser must produce this object. The tax engine and UI must never import broker-specific code.

---

## File Responsibilities

| File | Role | May import |
|---|---|---|
| `app.py` | Streamlit UI, file upload, rendering | `parser.py`, `tax_engine.py`, `styles.py` |
| `parser.py` | IBKR Flex XML → `ParsedFlexData` | `currency_provider.py` |
| `tax_engine.py` | `ParsedFlexData` → `TaxResult` | `currency_provider.py` |
| `currency_provider.py` | EUR conversion, ECB cache | stdlib only |
| `styles.py` | Dark FinTech CSS string | nothing |
| `smoke_test.py` | Quick sanity check | `parser.py`, `tax_engine.py` |

---

## Adding a New Broker

1. Create `parsers/<broker_slug>.py` (e.g., `parsers/ibkr_flex.py`, `parsers/degiro.py`).
2. The module must expose exactly one public function: `parse(source) -> ParsedFlexData`.
3. The `source` argument should accept `bytes | str | Path` (same contract as the current `parse_flex_xml`).
4. Populate `ParsedFlexData` fields — see the dataclass in `parser.py` for the canonical schema.
5. Register the parser in `app.py`'s broker selector (one `if/elif` block or a dict dispatch).
6. Do **not** add broker-specific logic anywhere outside that file.

When the refactor to `parsers/` happens, `parser.py` becomes `parsers/ibkr_flex.py` and `parser.py` re-exports `parse_flex_xml` as a shim until callers are updated.

---

## Canonical Data Contract — `ParsedFlexData`

Defined in `parser.py`. All broker parsers must produce this.

```python
@dataclass
class ParsedFlexData:
    stocks: pd.DataFrame       # assetCategory in {STK}
    derivatives: pd.DataFrame  # assetCategory in {OPT, FOP, WAR, IOPT}
    funds: pd.DataFrame        # assetCategory in {FUND} — flagged for manual review
    dividends: pd.DataFrame    # cash: type matches dividend keywords
    interest: pd.DataFrame     # cash: type matches interest keywords
    withholding: pd.DataFrame  # cash: type matches withholding keywords
    other_cash: pd.DataFrame   # everything else
```

**Required columns per trade DataFrame:** `date`, `symbol`, `isin`, `currency`, `fxRateToBase`, `quantity`, `tradePrice`, `ibCommission`, `proceeds`, `buySell`, `assetCategory`, `description`, `fifoPnlRealized`

**Required columns per cash DataFrame:** `date`, `symbol`, `isin`, `currency`, `fxRateToBase`, `amount`, `description`, `type`

Missing optional columns should be filled with `None` / `0.0` — never raise on missing fields.

---

## Tax Engine Constants

Defined at module level in `tax_engine.py`:

```python
KEST_RATE = 0.275   # Austrian KESt — 27.5%
```

E1kv field mapping:

| Field | Category |
|---|---|
| `"861"` | Stock capital gains |
| `"775"` | Derivative gains |
| `"862"` | Dividends |
| `"777"` | Interest (domestic) |
| `"863"` | Interest (foreign) |
| `"998"` | Foreign withholding tax (creditable) |

Funds (`FUND`) are routed to `manual_processing` queue, not calculated automatically — Austrian fund tax rules require per-fund inspection.

---

## FX Conversion

`currency_provider.ECBRateProvider` handles all conversions. Resolution order:

1. EUR base → rate 1.0
2. ECB cache exact date match
3. Fetch from ECB API (90-day window, 8s timeout)
4. Nearest prior business day in cache
5. IBKR `fxRateToBase` fallback
6. 1.0 with source `"Missing FX rate fallback"` (never crashes)

Cache lives at `.cache/ecb_rates.json`. It is excluded from git (`.gitignore`).

Every converted value carries a `FxRate` record (rate, date, currency, source) for audit trail transparency.

---

## Naming Conventions

- **Functions / variables:** `snake_case`
- **Private helpers:** leading underscore (`_load_xml`, `_normalise_trade`, `_num`)
- **Classes:** `PascalCase`
- **DataFrame column suffixes:** `_eur` for converted amounts, `_original` for source-currency values
- **DataFrame column state tracking:** `old_*`, `new_*` (e.g., `old_avg_cost_eur`, `new_quantity`)
- **Asset categories:** `UPPERCASE` strings matching IBKR codes (`STK`, `OPT`, `FUND`, …)
- **E1kv fields:** string literals (`"861"`, `"775"`, …) — never integers

---

## Error Handling Rules

- **Never raise on bad input values** — use `_num()` pattern (returns `0.0` on invalid float) and `parse_ib_date()` (returns `None` on bad format).
- **Never raise on missing FX rates** — fall through the resolution chain, log source as `"Missing FX rate fallback"`.
- **Empty DataFrames are valid input** — every processor must return `(0.0, empty_df)` gracefully.
- **Network failures are non-fatal** — ECB fetch is wrapped in try/except; the app must work fully offline with cached rates.
- Validation at system boundaries only: XML upload, ECB API response. No defensive checks on internal dataclass fields.

---

## UI / Styling

Dark FinTech theme defined entirely in `styles.py`. The CSS string is injected via `st.markdown(..., unsafe_allow_html=True)` at app start.

Category → accent color mapping:

| Category | Color | Hex |
|---|---|---|
| Stocks | Cyan | `#00D4FF` |
| Derivatives | Purple | `#BB86FC` |
| Dividends / Interest | Green | `#00FF88` |
| ETF / Funds | Gold | `#FFD700` |
| Tax due | Red | `#FF4D6D` |

CSS classes to reuse: `.metric-card`, `.metric-grid`, `.status-pill`, `.fintech-btn`. Do not add inline styles to `app.py` — all visual rules belong in `styles.py`.

---

## Code Style

- Type hints on all function signatures; `from __future__ import annotations` at top of each file.
- Dataclasses (`@dataclass`) for all data-transfer objects.
- No comments unless the *why* is non-obvious (hidden constraint, workaround, legal requirement).
- No docstrings beyond a single-line module docstring and brief class docstrings.
- No logging module — Streamlit surfaces status; audit trail is the paper trail.
- Pandas for all tabular data; no custom loop-based aggregations when a vectorized operation exists.

---

## Dependencies

```
pandas>=2.2
streamlit>=1.35
```

Standard library only beyond these two. Do not add dependencies without a strong reason — especially no heavy ML or financial libraries.

---

## Running Locally

```powershell
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

Smoke test (no Streamlit, pure Python):

```powershell
python smoke_test.py
```

---

## What NOT to Do

- Do not put broker-specific parsing logic in `tax_engine.py` or `app.py`.
- Do not put tax calculation logic in any parser.
- Do not hardcode currency conversion logic outside `currency_provider.py`.
- Do not store secrets in code — use `.streamlit/secrets.toml` (gitignored).
- Do not commit `.cache/`, generated CSV reports, or `venv/`.
- Do not add E1kv field mapping outside `tax_engine.py`.
