"""Shared USDCtoFiat client for Langflow components.

USDCtoFiat by Galleon Labs. Not a Peer Cash product. No private keys.
"""

from __future__ import annotations

import json
from typing import Any

from usdctofiat import create_offramp
from usdctofiat.errors import UsdctoFiatError
from usdctofiat.types import CashoutResult, Estimate, PreparedCashout, UnsignedTx


def offramp() -> Any:
    return create_offramp()


def as_dict(value: Any) -> Any:
    if isinstance(value, (CashoutResult, PreparedCashout, Estimate, UnsignedTx)):
        return value.as_dict()
    if hasattr(value, "as_dict"):
        return value.as_dict()
    return value


def dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def error_payload(exc: Exception) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": str(exc), "code": getattr(exc, "code", type(exc).__name__)}
    if isinstance(exc, UsdctoFiatError) and exc.details is not None:
        payload["details"] = exc.details
    return payload
