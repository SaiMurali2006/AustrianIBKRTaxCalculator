# Austrian KeSt Tax Engine

> A modular, animated Streamlit tax dashboard for Austrian capital gains tax reporting. Supports IBKR Flex Query XML today; adding a new broker requires one file and two lines.

[![Python](https://img.shields.io/badge/Python-3.10%2B-00D4FF?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FinTech%20Dashboard-BB86FC?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tax](https://img.shields.io/badge/Austria-E1kv%20Mapping-00FF88?style=for-the-badge)](#austrian-e1kv-field-mapping)
[![Status](https://img.shields.io/badge/Status-Prototype%20Tax%20Engine-FFD700?style=for-the-badge)](#important-disclaimer)

## Overview

Turns a brokerage statement export into a structured Austrian **E1kv** capital income report. Separates stocks, derivatives, dividends, interest, foreign withholding tax, and ETF/FUND rows, then renders the results in a dark neon-accented Streamlit dashboard with smooth entrance animations.

The core engine is built around Austrian private-investor tax concepts:

- **Stocks:** moving average cost basis (`Gleitender Durchschnittspreis`)
- **Options and derivatives:** realized premium and close-out P/L
- **Dividends and interest:** gross income tracking
- **Foreign withholding tax:** creditable tax bucket for E1kv field 998
- **Loss offsetting:** internal offset inside the 27.5% capital income basket
- **ETF/FUND detection:** automatic manual-processing queue

## Visual Identity

Dark FinTech theme with animated metric cards, staggered entrance animations, hover lift + shimmer effects, and a persistent pulse glow on the KeSt Due card:

| Category | Accent | E1kv Field |
| --- | --- | --- |
| Stocks | Neon Blue `#00D4FF` | 861 |
| Derivatives / Options | Neon Purple `#BB86FC` | 775 |
| Dividends / Interest | Emerald Green `#00FF88` | 862, 777/863 |
| ETFs / Funds | Amber Gold `#FFD700` | Manual review |
| Tax Due | Signal Red `#FF4D6D` | Calculated liability |

## Austrian E1kv Field Mapping

| E1kv Field | Meaning | Engine Source |
| --- | --- | --- |
| **861** | Realized stock gains taxable at 27.5% | `assetCategory="STK"` moving-average realization |
| **775** | Income from derivatives and options | `assetCategory="OPT"` and related derivative categories |
| **862** | Dividends | Cash dividend transactions |
| **777 / 863** | Foreign interest income | Cash interest transactions |
| **998** | Creditable foreign withholding tax | Withholding-tax cash rows |

## Architecture

The parser layer is the only broker-specific code. Everything below the `ParsedData` boundary is broker-agnostic.

```mermaid
flowchart LR
    XML["Broker Statement\ne.g. IBKR Flex XML"] --> Registry["parsers/__init__.py\nBROKER_REGISTRY"]
    Registry --> Parser["parsers/ibkr_flex.py\nparse()"]
    Parser --> PD["models.ParsedData\ncanonical contract"]

    PD --> CGP["CapitalGainsProcessor\nstocks"]
    PD --> DP["DerivativeProcessor\noptions"]
    PD --> TA["TaxAggregator\ncash income"]

    FX["currency_provider.py\nECB + IBKR fallback"] --> CGP
    FX --> DP
    FX --> TA

    CGP --> TR["models.TaxResult"]
    DP  --> TR
    TA  --> TR

    TR --> UI["app.py\nStreamlit Dashboard"]
    TR --> Reports["CSV Reports"]
```

## Project Structure

```text
tax_calculator_v7/
├── app.py                         # Streamlit entry point and dashboard
├── models.py                      # Shared contracts: ParsedData, TaxResult, column schemas
├── tax_engine.py                  # Austrian KeSt calculation engine (broker-agnostic)
├── currency_provider.py           # ECB FX provider with local JSON cache
├── styles.py                      # Animated dark FinTech CSS
├── parsers/
│   ├── __init__.py                # Broker registry: BROKER_REGISTRY, get_parser()
│   └── ibkr_flex.py               # IBKR Flex XML → ParsedData
├── sample_flex.xml                # Demonstration Flex XML
├── smoke_test.py                  # Minimal engine verification
└── requirements.txt               # Runtime dependencies (pandas, streamlit)
```

## Quick Start

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Then open the local URL shown in the terminal.

## Using the Dashboard

1. Select your **Broker** in the sidebar (currently: IBKR Flex XML).
2. Upload the corresponding statement file, or enable the **embedded sample**.
3. Review the **Executive Summary** for:
   - profit/loss per tax category with animated metric cards
   - KeSt calculation breakdown (taxable basket → gross KeSt → credit → net due)
   - E1kv field mapping table
   - ETF/FUND manual-processing warnings
4. Switch to **Detailed Audit Trail** for:
   - trade-level EUR conversion with ECB or fallback FX source
   - buy/sell timing, cost basis evolution, realized P/L per line

## Adding a New Broker

1. Create `parsers/<broker_slug>.py` exposing `parse(source: str | Path | bytes) -> ParsedData`.
2. Map your broker's fields to the column schemas defined in `models.TRADE_COLUMNS` and `models.CASH_COLUMNS`.
3. Add one entry each to `BROKER_REGISTRY` and `BROKER_SAMPLES` in `parsers/__init__.py`.

The tax engine and UI require zero changes.

## Exported Reports

| File | Purpose |
| --- | --- |
| `E1kv_Report_2026.csv` | Direct E1kv field summary |
| `transaction_audit.csv` | Trade-by-trade calculation log with FX details |
| `manual_processing_required.csv` | ETF/FUND rows requiring separate Austrian fund-tax review |

## Calculation Highlights

### Moving Average Stock Cost

```text
NewAvgCost =
    (OldTotalCost_EUR + NewQty × Price_EUR + Commission_EUR)
    / (OldQty + NewQty)
```

Sales realize P/L against the running moving-average cost basis.

### FX Conversion

All non-EUR amounts are converted using:

1. ECB reference rates for the exact trade date.
2. Nearest prior ECB business day when the exact date is unavailable.
3. IBKR `fxRateToBase` as an offline fallback.
4. `1.0` with a `"Missing FX rate fallback"` source tag — never crashes.

### KeSt Calculation

```text
basket_income = stock_P/L + option_P/L + dividends + interest
taxable_base  = max(0, basket_income)          ← internal loss offset
gross_kest    = taxable_base × 0.275
kest_due      = max(0, gross_kest − foreign_tax_credit)
```

Loss offsetting happens within the 27.5% basket only. Foreign withholding tax is tracked separately as a creditable amount (field 998).

## Smoke Test

```powershell
python smoke_test.py
# smoke test passed
```

## Important Disclaimer

This software is a technical calculation aid, not official tax advice. Austrian capital income taxation can depend on broker data quality, investor status, fund reporting, treaty limits, account structure, and yearly FinanzOnline rules. Review results carefully and consult a qualified Austrian tax professional before filing.

## Roadmap

- Historical ECB archive backfill beyond the 90-day cache window
- Full option lifecycle reconstruction for complex multi-leg strategies
- OeKB fund-report integration for Austrian ETF taxation
- PDF report generation for advisor handoff
- Additional broker parsers (Degiro CSV, Flatex, Scalable Capital)
