"""Broker parser registry.

To add a new broker:
  1. Create parsers/<broker_slug>.py exposing parse(source) -> ParsedData
  2. Add one entry to BROKER_REGISTRY and (optionally) BROKER_SAMPLES below.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from models import ParsedData
from .ibkr_flex import parse as _ibkr_parse
from .ibkr_flex import SAMPLE_XML as _IBKR_SAMPLE


BROKER_REGISTRY: dict[str, Callable[[str | Path | bytes], ParsedData]] = {
    "IBKR Flex XML": _ibkr_parse,
}

BROKER_SAMPLES: dict[str, str] = {
    "IBKR Flex XML": _IBKR_SAMPLE,
}


def get_parser(broker: str) -> Callable[[str | Path | bytes], ParsedData]:
    if broker not in BROKER_REGISTRY:
        raise ValueError(f"Unknown broker: {broker!r}. Available: {list(BROKER_REGISTRY)}")
    return BROKER_REGISTRY[broker]
