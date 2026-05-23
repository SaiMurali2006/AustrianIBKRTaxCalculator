# CLAUDE.md — Austrian KESt Tax Engine

## Project Purpose

Streamlit dashboard that ingests brokerage statement data, calculates Austrian capital gains tax (KESt, 27.5%), and maps results to E1kv tax form fields. Supports IBKR Flex Query XML today; adding a new broker requires only one new file and two lines in the registry.

---

## Architecture

```
Broker Statement (any format)
        ↓
  parsers/<broker>.py   parse(source) → ParsedData
        ↓
  models.ParsedData     canonical data contract
        ↓
  tax_engine.TaxAggregator
        ├── CapitalGainsProcessor   stocks, moving-average cost basis
        ├── DerivativeProcessor     options / FOP / warrants
        └── _cash_income            dividends, interest, withholding
        ↓
  models.TaxResult
        ↓
  app.py   Streamlit UI (broker selector → parse → calculate → render)
```

The canonical boundary is `models.ParsedData`. Any broker parser must produce this object. The tax engine and UI must never import broker-specific code.

---

## File Responsibilities

| File | Role | May import |
|---|---|---|
| `models.py` | `ParsedData`, `TaxResult`, column constants | stdlib, pandas |
| `parsers/__init__.py` | `BROKER_REGISTRY`, `BROKER_SAMPLES`, `get_parser()` | `models`, `.ibkr_flex` |
| `parsers/ibkr_flex.py` | IBKR Flex XML → `ParsedData`; owns `SAMPLE_XML` | `models`, stdlib, pandas |
| `tax_engine.py` | `ParsedData` → `TaxResult`; broker-agnostic | `models`, `currency_provider` |
| `currency_provider.py` | EUR conversion, ECB cache | stdlib only |
| `app.py` | Streamlit UI, broker selector, rendering | `parsers`, `tax_engine`, `styles`, `currency_provider` |
| `styles.py` | Dark FinTech CSS string | nothing |
| `smoke_test.py` | Quick sanity check | `parsers`, `tax_engine` |

---

## Adding a New Broker

1. Create `parsers/<broker_slug>.py` (e.g., `parsers/degiro.py`).
2. Expose exactly one public function: `parse(source: str | Path | bytes) -> ParsedData`.
3. Populate all `ParsedData` fields — see `models.py` for the schema.
4. In `parsers/__init__.py`, add one entry to `BROKER_REGISTRY` and (optionally) `BROKER_SAMPLES`.

That's it. The tax engine and UI require no changes.

---

## Canonical Data Contract — `models.ParsedData`

All broker parsers must produce this dataclass. The tax engine reads only these fields.

```python
@dataclass
class ParsedData:
    stocks: pd.DataFrame       # TRADE_COLUMNS, assetCategory == STK
    options: pd.DataFrame      # TRADE_COLUMNS, assetCategory in {OPT, FOP, WAR, IOPT}
    funds: pd.DataFrame        # TRADE_COLUMNS, assetCategory == FUND (manual review queue)
    dividends: pd.DataFrame    # CASH_COLUMNS, matched by dividend/withholding keywords
    interest: pd.DataFrame     # CASH_COLUMNS, matched by interest keywords
    cash_other: pd.DataFrame   # CASH_COLUMNS, everything else
    all_trades: pd.DataFrame   # TRADE_COLUMNS, unfiltered
    all_cash: pd.DataFrame     # CASH_COLUMNS, unfiltered
```

**`TRADE_COLUMNS`** (defined in `models.py`):
`date`, `datetime`, `currency`, `fxRateToBase`, `assetCategory`, `symbol`, `description`, `isin`, `quantity`, `tradePrice`, `proceeds`, `ibCommission`, `openCloseIndicator`, `cost`, `fifoPnlRealized`, `buySell`

**`CASH_COLUMNS`** (defined in `models.py`):
`date`, `datetime`, `currency`, `fxRateToBase`, `symbol`, `description`, `isin`, `amount`, `type`, `tax`

Missing optional fields should be `None` / `0.0` — never raise on missing input.

---

## Broker Registry

Defined in `parsers/__init__.py`:

```python
BROKER_REGISTRY: dict[str, Callable[[str | Path | bytes], ParsedData]] = {
    "IBKR Flex XML": _ibkr_parse,
    # "Degiro CSV": _degiro_parse,  ← add new brokers here
}

BROKER_SAMPLES: dict[str, str] = {
    "IBKR Flex XML": _IBKR_SAMPLE,
    # "Degiro CSV": _DEGIRO_SAMPLE,
}
```

The UI populates its broker `selectbox` directly from `BROKER_REGISTRY.keys()`. No UI code needs to change when adding a broker.

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
6. 1.0 with source `"Missing FX rate fallback"` — never crashes

Cache lives at `.cache/ecb_rates.json` (gitignored). Every converted value carries a `FxRate` record for the audit trail.

---

## Naming Conventions

- Functions / variables: `snake_case`
- Private helpers: leading underscore (`_load_xml`, `_normalise_trade`, `_num`)
- Classes: `PascalCase`
- DataFrame column suffixes: `_eur` for converted amounts, `_original` for source-currency
- State-tracking columns: `old_*`, `new_*` (e.g., `old_avg_cost_eur`, `new_quantity`)
- Asset categories: `UPPERCASE` strings matching IBKR codes (`STK`, `OPT`, `FUND`, …)
- E1kv fields: string literals (`"861"`, `"775"`, …) — never integers

---

## Error Handling Rules

- Never raise on bad input values — use `_num()` pattern (returns `0.0` on invalid float).
- Never raise on missing FX rates — fall through the resolution chain.
- Empty DataFrames are valid input — every processor returns `(0.0, empty_df)` gracefully.
- Network failures are non-fatal — ECB fetch wrapped in try/except; app works fully offline.
- Validate only at system boundaries (XML upload, ECB API response).

---

## UI / Styling

Dark FinTech theme defined entirely in `styles.py`. Injected via `st.markdown(..., unsafe_allow_html=True)`.

Category → accent color:

| Category | Color | Hex |
|---|---|---|
| Stocks | Cyan | `#00D4FF` |
| Derivatives | Purple | `#BB86FC` |
| Dividends / Interest | Green | `#00FF88` |
| ETF / Funds | Gold | `#FFD700` |
| Tax due | Red | `#FF4D6D` |

CSS classes: `.metric-card`, `.metric-grid`, `.status-pill`, `.fintech-btn`. No inline styles in `app.py` — all visual rules belong in `styles.py`.

---

## Code Style

- Type hints on all function signatures; `from __future__ import annotations` at top of each file.
- Dataclasses (`@dataclass`) for all data-transfer objects.
- No comments unless the *why* is non-obvious (hidden constraint, workaround, legal requirement).
- No docstrings beyond a single-line module docstring and brief class docstrings.
- No logging module — Streamlit surfaces status; audit trail is the paper trail.
- Pandas for all tabular data; no custom loop-based aggregations when a vectorized op exists.

---

## Dependencies

```
pandas>=2.2
streamlit>=1.35
```

Standard library only beyond these two. Do not add dependencies without a strong reason.

---

## Running Locally

```powershell
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

Smoke test (no Streamlit):

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
- Do not import from `parsers/ibkr_flex.py` directly — always go through `parsers.get_parser()`.
