"""Shared USDCtoFiat client helpers for the Dify plugin.

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
The plugin accepts no private keys, and mode is required.
"""

from __future__ import annotations

import json
from typing import Any

from usdctofiat import create_offramp
from usdctofiat.errors import UsdctoFiatError
from usdctofiat.types import CashoutResult, Estimate, PreparedCashout, UnsignedTx

_BANNED = ("private_key", "privateKey", "key", "secret", "mnemonic", "wallet_key")


def offramp_from(credentials: dict[str, Any] | None = None) -> Any:
    creds = dict(credentials or {})
    for banned in _BANNED:
        if banned in creds:
            raise TypeError(
                "USDCtoFiat does not accept a private key. "
                "The plugin returns unsigned txs for the host to sign."
            )
    return create_offramp(
        **{
            key: creds[key]
            for key in ("curator_url", "indexer_url", "referrer", "extra_referrers")
            if key in creds
        }
    )


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
