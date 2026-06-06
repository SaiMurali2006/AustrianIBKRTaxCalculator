"""FastAPI surface for the Austrian KeSt engine.

Run from the repo root so the frozen library's absolute imports (`from models import …`)
resolve:  uvicorn backend.main:app --reload

This layer only parses → serializes. All tax/E1kv logic stays in tax_engine.py. The two-step
cache (parse keyed by content hash, calc keyed additionally by options) mirrors app.py's
st.session_state caching so re-calc on a toggle never re-parses.
"""

from __future__ import annotations

import hashlib
import io
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from currency_provider import ECBRateProvider
from models import ParsedData, TaxResult
from parsers import BROKER_REGISTRY, BROKER_SAMPLES, get_parser
from tax_engine import TaxAggregator, years_in_parsed

from .serialize import df_to_records, parsed_summary, result_to_json

app = FastAPI(title="Austrian KeSt Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_PARSED: dict[str, ParsedData] = {}
_RESULTS: dict[str, TaxResult] = {}

_MULTI_YEAR_MSG = (
    "Statement spans multiple tax years: {years}. Austrian §27a EStG forbids cross-year "
    "loss offsets for private investors — each year must be filed independently. Export one "
    "IBKR Flex Query per year (set the period to a single calendar year) and re-upload."
)


@app.get("/api/brokers")
def brokers() -> list[dict[str, Any]]:
    return [{"name": name, "hasSample": name in BROKER_SAMPLES} for name in BROKER_REGISTRY]


@app.post("/api/parse")
async def parse(
    broker: str = Form(...),
    use_sample: bool = Form(False),
    file: UploadFile | None = File(None),
) -> dict[str, Any]:
    if broker not in BROKER_REGISTRY:
        raise HTTPException(400, f"Unknown broker: {broker!r}")

    if file is not None:
        payload: bytes | str = await file.read()
    elif use_sample and broker in BROKER_SAMPLES:
        payload = BROKER_SAMPLES[broker]
    else:
        raise HTTPException(400, "Provide a statement file or enable the embedded sample.")

    raw = payload if isinstance(payload, bytes) else payload.encode()
    parse_key = "parse_" + hashlib.md5(raw).hexdigest() + broker

    if parse_key not in _PARSED:
        try:
            _PARSED[parse_key] = get_parser(broker)(payload)
        except Exception as exc:  # boundary validation only — never leak a stack trace
            raise HTTPException(422, f"Could not parse statement: {exc}") from exc

    parsed = _PARSED[parse_key]
    years = years_in_parsed(parsed)
    if len(years) > 1:
        raise HTTPException(422, _MULTI_YEAR_MSG.format(years=", ".join(str(y) for y in years)))

    return {"parseKey": parse_key, "years": years, **parsed_summary(parsed)}


class CalcRequest(BaseModel):
    parseKey: str
    includeFees: bool = False
    excludedIsins: list[str] = []
    altbestandQuantities: dict[str, float] = {}


@app.post("/api/calculate")
def calculate(req: CalcRequest) -> dict[str, Any]:
    parsed = _PARSED.get(req.parseKey)
    if parsed is None:
        raise HTTPException(404, "Unknown parseKey — re-upload the statement.")

    qty_sig = "|".join(f"{k}={req.altbestandQuantities[k]}" for k in sorted(req.altbestandQuantities))
    calc_key = (
        req.parseKey
        + ("F" if req.includeFees else "N")
        + "|".join(sorted(req.excludedIsins))
        + "#" + qty_sig
    )
    if calc_key not in _RESULTS:
        _RESULTS[calc_key] = TaxAggregator(
            ECBRateProvider(), include_fees=req.includeFees
        ).run(
            parsed,
            excluded_isins=set(req.excludedIsins),
            altbestand_quantities=req.altbestandQuantities or None,
        )
    result = _RESULTS[calc_key]
    return {"calcKey": calc_key, **result_to_json(result)}


def _csv_stream(df: pd.DataFrame, filename: str) -> StreamingResponse:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/export/{kind}")
def export(kind: str, calcKey: str) -> StreamingResponse:
    result = _RESULTS.get(calcKey)
    if result is None:
        raise HTTPException(404, "Unknown calcKey — recalculate first.")
    year = str(result.tax_year) if result.tax_year else "unknown"

    if kind == "e1kv":
        df = pd.DataFrame(
            [{"E1kv_Field": f, "Amount_EUR": a} for f, a in sorted(result.e1kv_fields.items())]
        )
        return _csv_stream(df, f"E1kv_Report_{year}.csv")
    if kind == "audit":
        return _csv_stream(result.audit, "transaction_audit.csv")
    if kind == "manual":
        return _csv_stream(result.manual_processing, "manual_processing_required.csv")
    raise HTTPException(404, f"Unknown export kind: {kind!r}")
