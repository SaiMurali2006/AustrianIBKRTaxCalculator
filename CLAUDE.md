# CLAUDE.md — Austrian KESt Tax Engine

## Project Purpose

Streamlit dashboard that ingests brokerage statement data, calculates Austrian capital gains tax (KESt — 27.5% securities basket, 25% bank-deposit basket), and maps results to E1kv form Kennzahlen using the codes from the official BMF E1kv 2024 form. Supports IBKR Flex Query XML today; adding a new broker requires only one new file and two lines in the registry.

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
        ├── CapitalGainsProcessor   stocks, moving-average cost basis, gain/loss split
        ├── DerivativeProcessor     options / FOP / warrants, gain/loss split
        └── _cash_income            dividends, bond interest, bank interest, withholding
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
| `app.py` | Streamlit UI; two-step session cache (parse + calc); three-view nav; Altair charts; Altbestand selector | `parsers`, `tax_engine`, `styles`, `currency_provider`, `altair`, `hashlib` |
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
    stocks: pd.DataFrame         # TRADE_COLUMNS, assetCategory == STK
    options: pd.DataFrame        # TRADE_COLUMNS, assetCategory in {OPT, FOP, WAR, IOPT}
    funds: pd.DataFrame          # TRADE_COLUMNS, FUND + any unrecognised assetCategory (manual review)
    dividends: pd.DataFrame      # CASH_COLUMNS, dividend/withholding keywords (27.5% basket)
    bond_interest: pd.DataFrame  # CASH_COLUMNS, bond coupon / accrued interest (27.5% basket)
    bank_interest: pd.DataFrame  # CASH_COLUMNS, broker credit/debit interest on cash (25% basket)
    cash_other: pd.DataFrame     # CASH_COLUMNS, everything else
    all_trades: pd.DataFrame     # TRADE_COLUMNS, unfiltered
    all_cash: pd.DataFrame       # CASH_COLUMNS, unfiltered
```

Interest is split at the parser layer because the two flows fall into different KESt baskets — bond coupons stay in the 27.5% basket, bank-deposit interest is taxed at 25% and cannot be offset against securities losses (§27a Abs. 2 EStG).

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
KEST_RATE       = 0.275   # 27.5% securities basket (§27a Abs. 1 EStG)
KEST_RATE_BANK  = 0.25    # 25% bank-deposit-interest basket (§27a Abs. 2 EStG)
DBA_DIVIDEND_CAP = 0.15   # Foreign WHT credit cap per Austrian DBA treaties
```

E1kv Kennzahl mapping — verified against the official **BMF E1kv 2024** form (`https://formulare.bmf.gv.at/service/formulare/inter-Steuern/pdfs/2024/E1kv.pdf`). All values are foreign-broker (IBKR is a foreign depot from Austria's perspective).

| Kennzahl | Category | Basket | Note |
|---|---|---|---|
| `"994"` | Stock / ETF / bond realized gains | 27.5% | Moving-average realization (§27 Abs. 3 EStG) |
| `"892"` | Realized losses on securities and non-securitised derivatives | 27.5% | Reported separately so the Finanzamt can verify Verlustausgleich |
| `"981"` | Non-securitised derivative gains (options, futures) | 27.5% | Securitised derivatives (warrants, certificates) belong in KZ 995/896 — out of scope |
| `"863"` | Foreign dividends and bond coupon interest | 27.5% | Gross income (§27 Abs. 2 EStG) |
| `"861"` | Foreign bank deposit interest | **25%** | Cannot be offset against securities losses |
| `"998"` | Creditable foreign WHT, 27.5% basket | — | Capped at 15% of gross (DBA) |
| `"901"` | Creditable foreign WHT, 25% basket | — | Rare (bank-deposit WHT) |

`PRE-2011 EXEMPT` is an internal audit-only marker — rows tagged this way are excluded from every Kennzahl (see Altbestand section below).

Funds (`FUND`) and any unrecognised asset categories are routed to `manual_processing` — Austrian fund tax rules require per-fund inspection. Accumulating ETFs additionally require **ausschüttungsgleiche Erträge** (KZ 937, 27.5%) reporting which the engine does not auto-calculate.

### Two-Basket Calculation

```python
basket_27 = stock_gain + stock_loss + deriv_gain + deriv_loss + dividend_total + bond_interest_total
basket_25 = bank_interest_total
taxable_27 = max(0.0, basket_27)
taxable_25 = max(0.0, basket_25)            # bank-interest losses are siloed
tax_due = max(0.0, taxable_27 * KEST_RATE      - credit_27) \
        + max(0.0, taxable_25 * KEST_RATE_BANK - credit_25)
```

Within each basket: gains net against losses in the same calendar year. Across baskets: no netting. Across years: no carry-forward in the private-investor sphere.

### Foreign Withholding Tax Credit Cap

Under most Austrian DBA treaties (Austria–USA Art. 10, etc.), the maximum creditable foreign dividend withholding is **15% of the gross 27.5%-basket income**. Higher source-country withholding (e.g. 30% with no W-8BEN) is capped at 15% and the excess is surfaced via `TaxResult.excess_wht`.

```python
gross_27_for_cap   = max(0.0, dividend_total) + max(0.0, bond_interest_total)
max_creditable_27  = gross_27_for_cap * DBA_DIVIDEND_CAP
creditable_wht_27  = min(abs(dividend_wht) + abs(bond_wht), max_creditable_27)
```

`TaxResult.excess_wht` aggregates: (a) the amount above the DBA cap, (b) the amount above the Austrian tax actually owed in each basket. Per §46 EStG this excess cannot be carried forward — the user must reclaim it from the source country (e.g. IRS Form 1040-NR for US WHT above 15%).

### Pre-2011 Grandfathering (§ 124b Z 185 EStG)

Securities acquired before **1 January 2011** (derivatives and interest-bearing instruments: **31 March 2012**) are tax-free on capital gains for private investors. IBKR statements do not carry the original acquisition date for transferred positions, so detection is impossible from XML alone.

The UI exposes a `Pre-2011 Altbestand (exempt)` multiselect in the sidebar listing every `(symbol, ISIN)` in the parsed statement. Selected ISINs are passed as `excluded_isins` into `TaxAggregator.run(parsed, excluded_isins=...)`. Excluded trades contribute zero to KZ 994/892 and are tagged `"PRE-2011 EXEMPT"` in the audit trail (with `realized_pnl_eur = 0`), but cost-basis tracking continues so subsequent post-2011 sells of the same symbol still calculate against the running average cost.

### Fee Deductibility (`include_fees` toggle)

Austrian private account rules (**§ 20 Abs. 2 EStG**) prohibit deduction of brokerage fees for taxable capital gain purposes. The engine defaults to `include_fees=False`.

`TaxAggregator.__init__(fx_provider, include_fees=False)` — pass `include_fees=True` for business accounts or non-Austrian jurisdictions.

**Stock P/L effect:**
- `include_fees=False`: commission is never added to cost basis on BUY, and never subtracted from proceeds on SELL → taxable gain = gross price difference only.
- `include_fees=True`: commission is added to cost basis on BUY and subtracted from proceeds on SELL (previous behaviour).

**Derivative P/L effect:**
- Primary path (`fifoPnlRealized ≠ 0`): IBKR embeds commission in this figure. Fee-excluded mode strips the closing-leg commission: `pnl_original = fifo_pnl - commission`.
- Fallback path (`fifoPnlRealized = 0`, close indicator): fee-excluded mode uses `proceeds` alone; fee-included uses `proceeds + commission`.

**Audit column `commission_eur` is always the actual fee** regardless of the toggle — the user can always see what the broker charged.

### Derivative P/L — open vs close

`DerivativeProcessor` uses `fifoPnlRealized` as the primary P/L source:

```python
fifo_pnl = float(trade["fifoPnlRealized"])
open_close = str(trade.get("openCloseIndicator", "")).upper()
if fifo_pnl != 0.0:
    pnl_original = fifo_pnl if self.include_fees else fifo_pnl - commission
elif "C" in open_close:
    pnl_original = proceeds + commission if self.include_fees else proceeds
else:
    pnl_original = 0.0
```

- Non-zero `fifoPnlRealized` → always use it (strip commission back out when fees excluded).
- Zero + close indicator → fallback; exclude commission when fees excluded.
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
- E1kv Kennzahlen: string literals (`"994"`, `"892"`, `"981"`, `"863"`, `"861"`, `"998"`, `"901"`) — never integers

---

## Error Handling Rules

- Never raise on bad input values — use `_num()` pattern (returns `0.0` on invalid float).
- Never raise on missing FX rates — fall through the resolution chain.
- Empty DataFrames are valid input — every processor returns `(0.0, 0.0, empty_df)` gracefully.
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

Two-step cache: parsing depends only on `(xml_payload, broker)`; calculation depends additionally on `(include_fees, excluded_isins)`. This lets the Altbestand selector recalculate without re-parsing the XML, and keeps view-switching free.

```python
parse_key = "parse_" + md5(xml_payload).hexdigest() + broker
if parse_key not in st.session_state:
    st.session_state[parse_key] = get_parser(broker)(xml_payload)
parsed = st.session_state[parse_key]

calc_key = parse_key + fee_flag + "|".join(sorted(excluded_isins))
if calc_key not in st.session_state:
    st.session_state[calc_key] = TaxAggregator(..., include_fees=include_fees) \
        .run(parsed, excluded_isins=excluded_isins)
result = st.session_state[calc_key]
```

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
- Do not hardcode commissions into the taxable gain calculation — always route through the `include_fees` flag on `TaxAggregator` / the processors. Default must be `False` (Austrian § 20 Abs. 2 EStG).
- Do not lump bank-deposit interest into the 27.5% basket. Bank interest is taxed at 25% (§27a Abs. 2 EStG) and cannot be offset against securities losses. The parser must classify "Credit Interest" / "Debit Interest" / "Broker Interest" into `ParsedData.bank_interest`, separate from `bond_interest`.
- Do not net gains against losses before emitting Kennzahlen. KZ 994 (gains) and KZ 892 (losses) must be reported separately so the Finanzamt can verify Verlustausgleich.
- Do not silently discard non-creditable foreign WHT. Surface it via `TaxResult.excess_wht` so the user can reclaim from the source country.
