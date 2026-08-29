"""Chainlink FX feed reads over Base JSON-RPC. Prices estimate(). No keys."""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal, localcontext

import httpx
from eth_abi import decode
from eth_utils import function_signature_to_4byte_selector

from .constants import (
    BASE_RPC_URL,
    CHAINLINK_ORACLE_FEEDS,
    DEFAULT_ORACLE_MAX_STALENESS,
    ZERO_ADDRESS,
)
from .errors import OracleError, ValidationError

LATEST_ROUND_DATA_SIG = "latestRoundData()"
LATEST_ROUND_DATA_SELECTOR = "0x" + function_signature_to_4byte_selector(LATEST_ROUND_DATA_SIG).hex()
LATEST_ROUND_DATA_OUTPUTS = ["uint80", "int256", "uint256", "uint256", "uint80"]


@dataclass(frozen=True)
class OracleRate:
    """Target-currency units per 1 USDC at the time of the read."""

    currency: str
    rate: Decimal
    as_of: int
    updated_at: int | None = None
    stale: bool = False


class Oracle:
    """Reads the currency's Chainlink feed. Same shape as Curator / Indexer."""

    def __init__(self, url: str = BASE_RPC_URL, *, timeout: float = 30.0, client: httpx.Client | None = None):
        self.url = url
        self.timeout = timeout
        self._client = client

    def rate(self, currency: str, *, max_staleness: int = DEFAULT_ORACLE_MAX_STALENESS) -> OracleRate:
        key = currency.strip().upper()
        if key not in CHAINLINK_ORACLE_FEEDS:
            raise ValidationError(
                f"unsupported currency {currency!r}: no Chainlink feed on Base, so the rate "
                f"cannot be read. Supported: {sorted(CHAINLINK_ORACLE_FEEDS)}",
                field="currency",
            )
        feed, invert, decimals = CHAINLINK_ORACLE_FEEDS[key]
        as_of = int(time.time())
        # USD is the zero-address passthrough: a constant 1.0 with no feed to read.
        if feed.lower() == ZERO_ADDRESS:
            return OracleRate(currency=key, rate=Decimal(1), as_of=as_of)

        answer, updated_at = self._latest_round_data(key, feed)
        price = Decimal(answer) / (Decimal(10) ** decimals)
        if price <= 0:
            raise OracleError(f"{key} feed returned a non-positive answer", details={"answer": answer})
        # Feeds are quoted USD per unit of fiat, so they invert to fiat per USDC.
        with localcontext() as ctx:
            ctx.prec = 34
            rate = (Decimal(1) / price) if invert else price
        stale = updated_at is not None and as_of - updated_at > max_staleness
        return OracleRate(currency=key, rate=rate, as_of=as_of, updated_at=updated_at, stale=stale)

    def _latest_round_data(self, currency: str, feed: str) -> tuple[int, int | None]:
        raw = self._eth_call(feed, LATEST_ROUND_DATA_SELECTOR)
        try:
            values = decode(LATEST_ROUND_DATA_OUTPUTS, raw)
        except Exception as exc:  # noqa: BLE001 - any decode failure is the same signal
            raise OracleError(f"{currency} feed returned an undecodable round", details=raw.hex()[:300]) from exc
        answer = int(values[1])
        updated_at = int(values[3])
        return answer, updated_at if updated_at > 0 else None

    def _eth_call(self, to: str, data: str) -> bytes:
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": to, "data": data}, "latest"],
        }
        own = self._client is None
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            resp = client.post(self.url, json=body, headers={"content-type": "application/json"})
        except httpx.HTTPError as exc:
            raise OracleError(f"oracle transport failed: {exc}") from exc
        finally:
            if own:
                client.close()
        if resp.status_code >= 400:
            raise OracleError(f"oracle rpc {resp.status_code}", details=resp.text[:300])
        try:
            payload = resp.json()
        except ValueError as exc:
            raise OracleError("oracle rpc returned non-JSON") from exc
        if not isinstance(payload, dict):
            raise OracleError("oracle rpc returned an unexpected payload", details=str(payload)[:300])
        if payload.get("error"):
            raise OracleError("oracle rpc error", details=payload["error"])
        result = payload.get("result")
        if not isinstance(result, str) or not result.startswith("0x"):
            raise OracleError("oracle rpc missing result", details=payload)
        try:
            return bytes.fromhex(result[2:])
        except ValueError as exc:
            raise OracleError("oracle rpc returned non-hex result", details=result[:300]) from exc
