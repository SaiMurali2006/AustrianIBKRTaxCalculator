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
| `app.py` | Streamlit UI; session_state caching; three-view navigation; Altair Performance charts | `parsers`, `tax_engine`, `styles`, `currency_provider`, `altair`, `hashlib` |
| `styles.py` | Dark FinTech CSS string | nothing |
| `smoke_test.py` | Engine verification with structural and directional value assertions | `parsers`, `tax_engine` |

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
    funds: pd.DataFrame        # TRADE_COLUMNS, FUND + any unrecognised assetCategory (manual review queue)
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

### Unknown asset categories

In `parsers/ibkr_flex.py`, any `assetCategory` that is not in `{STK, OPT, FOP, WAR, IOPT, FUND}` (e.g. `FUT`, `BOND`, `CASH`) is concatenated into `funds` so it surfaces in the manual review queue. Silent exclusion from the tax calculation is not acceptable.

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

| Field | Category | Note |
|---|---|---|
| `"861"` | Stock capital gains | Moving-average realization |
| `"775"` | Derivative gains | `fifoPnlRealized` on close; 0 on open |
| `"862"` | Dividends | Gross income |
| `"777"` | Interest (domestic) | Alias; set equal to `"863"` |
| `"863"` | Interest (foreign) | IBKR is a foreign broker — audit rows use `"863"` |
| `"998"` | Foreign withholding tax | Creditable against gross KeSt |

Funds (`FUND`) and any unrecognised asset categories are routed to `manual_processing` — Austrian fund tax rules require per-fund inspection.

### Derivative P/L — open vs close

`DerivativeProcessor` uses `fifoPnlRealized` as the primary P/L source:

```python
fifo_pnl = float(trade["fifoPnlRealized"])
open_close = str(trade.get("openCloseIndicator", "")).upper()
pnl_original = fifo_pnl if fifo_pnl != 0.0 else (proceeds + commission if "C" in open_close else 0.0)
```

- Non-zero `fifoPnlRealized` → always use it.
- Zero + close indicator → `proceeds + commission` fallback (IBKR omitted the value).
- Zero + open indicator → `0.0` (nothing realized on opening leg).

**Never use `float_value or fallback`** for numeric P/L — `0.0` is falsy in Python and would replace a legitimate break-even result with the fallback.

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

CSS classes to reuse: `.metric-grid`, `.card-wrap`, `.tax-card`, `.status-pill`, `.perf-section-label`. No inline styles in `app.py` — all visual rules belong in `styles.py`.

### Three-view navigation

The sidebar radio offers three views:

| View | Function | Data source |
|---|---|---|
| Executive Summary | `render_summary(result, parsed)` | `TaxResult` + `ParsedData` |
| Detailed Audit Trail | `render_audit(result)` | `TaxResult.audit` |
| Performance | `render_performance(result)` | `TaxResult.audit` filtered to STK/OPT |

### Session State Caching

Parsed data is cached in `st.session_state` using a content-hash key so the spinner only fires once per unique file/broker combination:

```python
cache_key = hashlib.md5(xml_payload if isinstance(xml_payload, bytes)
                        else xml_payload.encode()).hexdigest() + broker
if cache_key not in st.session_state:
    with st.spinner("Parsing statement and calculating KeSt…"):
        parsed = get_parser(broker)(xml_payload)
        result = TaxAggregator(ECBRateProvider()).run(parsed)
        st.session_state[cache_key] = (parsed, result)
parsed, result = st.session_state[cache_key]
```

This ensures view-switching never re-parses.

### Performance View (Altair)

`render_performance(result)` builds three Altair charts from `result.audit` filtered to `category in {"STK", "OPT"}`:

- **Cumulative P/L timeline** — area + line + coloured scatter, interactive zoom/pan.
- **Monthly breakdown** — grouped bars: gains (green), fees (gold), estimated KeSt (red).
- **Top holdings** — horizontal bar per symbol, green/red by P/L sign.

The Altair dark theme is registered at module level in `app.py` and must match the CSS palette. Charts use `_date:T` (pandas datetime) for temporal axes — never format as a string before passing to Altair.

### Metric Card HTML Structure

All six metric cards **must** be rendered in a single `st.markdown` call. Splitting across multiple calls puts each card in its own Streamlit wrapper `<div>`, breaking the CSS grid (cards stack vertically instead of 3×2).

```python
cards_html = '<div class="metric-grid">'
for color, field, label, value, tip in field_cards:
    cards_html += f'<div class="card-wrap" data-tip="{tip}"><div class="tax-card {color}">...</div></div>'
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)
```

### Tooltip Architecture

Tooltips use a CSS `::after` pseudo-element on `.card-wrap[data-tip]`.

- Tooltip appears **above** the card (`bottom: calc(100% + 9px)`) — never covered by the status strip below.
- `.card-wrap` has `z-index: 1` by default; `:hover` raises it to `z-index: 10`. This is required because `animation` on `.card-wrap` creates a CSS stacking context — without raising the hovered card's context, siblings painted later in DOM order cover the tooltip regardless of the `::after` z-index value.
- `div[data-testid="stMarkdownContainer"]` and related Streamlit wrappers are forced to `overflow: visible` so the tooltip is never clipped.
- Tooltip text is plain — `<a href>` tags in `data-tip` render literally, not as links. For clickable source links use the `st.expander("E1kv Field References")` below the cards.
- For Streamlit-native widgets (`st.metric`, `st.selectbox`, etc.) use the built-in `help=` parameter.

### Sample Data Behaviour

The embedded sample toggle defaults to `False` — users must explicitly enable it. When active without a real file uploaded, a blue `st.info` banner is shown so the user always knows they are looking at demo data, not their own results.

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
altair>=5        # direct import in app.py; also bundled with Streamlit
```

Standard library only beyond these. Do not add dependencies without a strong reason.

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
- Do not use Python `or` for numeric fallback logic (`0.0 or fallback` silently replaces legitimate zero values — use an explicit `if value != 0.0` check instead).
- Do not silently discard trades with unrecognised `assetCategory` — route them to the manual queue.
- Do not include `DIV`/`INT` audit rows in trading performance calculations — filter to `STK`/`OPT` only.
