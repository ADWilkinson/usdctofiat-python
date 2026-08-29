
"""Public curator HTTP. POST /v2/makers/create only. No API key. No POST /cashout."""

from __future__ import annotations

import re
from typing import Any

import httpx

from .constants import CHAIN_ID, CURATOR_URL, MAKERS_CREATE_PATH, PLATFORMS_NEEDING_ATTESTATION
from .errors import CuratorError, PayeeVerificationRequired, ValidationError

# The hash goes straight into createDeposit calldata, so anything that is not a
# 32-byte hex digest is a curator response we do not understand.
PAYEE_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


class Curator:
    def __init__(self, base_url: str = CURATOR_URL, *, timeout: float = 30.0, client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    def create_payee_hash(
        self,
        *,
        platform: str,
        payee: str,
        chain_id: int = CHAIN_ID,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Hash a payee via POST /v2/makers/create. Public. No API key."""
        if extra and any(k.lower() in {"identityattestation", "identity_attestation"} for k in extra):
            # v1 does not mint attestations. Refuse rather than forward a forged one.
            raise PayeeVerificationRequired(platform)
        # offchainId is a top-level field. Nesting it under payeeData hides it from
        # the curator schema, which then rejects the request as invalid_maker_data
        # exactly as if no payee had been sent. chain_id is accepted for callers
        # that still pass it and is not sent: v1 is Base only and the reference
        # client posts processorName + offchainId alone.
        _ = chain_id
        body = {"processorName": platform, "offchainId": payee}
        url = f"{self.base_url}{MAKERS_CREATE_PATH}"
        try:
            response = self._request(url, body)
        except CuratorError as exc:
            self._maybe_verification(platform, exc)
            raise
        digest = _extract_hash(response)
        if not digest:
            raise CuratorError("curator did not return a payee details hash", details=response)
        return digest

    def _request(self, url: str, body: dict[str, Any]) -> Any:
        if MAKERS_CREATE_PATH not in url:
            raise CuratorError("refused: this client only posts /v2/makers/create")
        if url.rstrip("/").endswith("/cashout"):
            raise CuratorError("refused: there is no POST /cashout")
        own = self._client is None
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            resp = client.post(url, json=body, headers={"content-type": "application/json"})
        except httpx.HTTPError as exc:
            raise CuratorError(f"curator transport failed: {exc}") from exc
        finally:
            if own:
                client.close()
        if resp.status_code >= 400:
            raise CuratorError(
                f"curator {resp.status_code}: {resp.text[:300]}",
                status=resp.status_code,
                details=_safe_json(resp),
            )
        payload = _safe_json(resp)
        # The curator answers in a {success, message, responseObject, statusCode,
        # errorCode} envelope. A 2xx carrying success: false is still a failure.
        if isinstance(payload, dict) and payload.get("success") is False:
            message = payload.get("message") or "curator rejected the request"
            raise CuratorError(f"curator: {message}", status=payload.get("statusCode"), details=payload)
        return payload

    def _maybe_verification(self, platform: str, exc: CuratorError) -> None:
        blob = f"{exc} {exc.details}".lower()
        if platform.lower() in PLATFORMS_NEEDING_ATTESTATION and (
            "verification" in blob or "attestation" in blob or "payee_verification" in blob
        ):
            raise PayeeVerificationRequired(platform) from exc


def _extract_hash(payload: Any) -> str | None:
    """The live envelope carries the digest at responseObject.hashedOnchainId."""
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload if PAYEE_HASH.match(payload) else None
    if not isinstance(payload, dict):
        return None
    for key in (
        "hashedOnchainId",
        "hashed_onchain_id",
        "payeeDetailsHash",
        "payee_details_hash",
        "hash",
    ):
        value = payload.get(key)
        if isinstance(value, str) and PAYEE_HASH.match(value):
            return value
    for key in ("payeeDetailsHashes", "hashedOnchainIds", "hashes"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, str) and PAYEE_HASH.match(first):
                return first
            if isinstance(first, dict):
                found = _extract_hash(first)
                if found:
                    return found
    for key in ("responseObject", "data"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            found = _extract_hash(nested)
            if found:
                return found
    return None


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"text": resp.text[:300]}
