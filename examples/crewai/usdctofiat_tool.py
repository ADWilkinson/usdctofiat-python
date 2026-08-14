"""UsdctoFiat BaseTool draft for CrewAI.

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
Not a Peer Cash product. https://usdctofiat.xyz/developers

Wraps `usdctofiat.cashout(mode="fast"|"best")`, `watch`, `withdraw`/`close`,
`deposits`, and `estimate`. Mode is required on every priced or mutating call.
There is no default to Fast or Best. These tools never accept a wallet
private key — inject a signer callback, or call cashout without one to
receive unsigned `{to, data, value, chainId}` txs.

This file is a draft for a future PR to crewAIInc/crewAI
(`lib/crewai-tools/src/crewai_tools/tools/usdctofiat_tool/usdctofiat_tool.py`).
It is not a first-party CrewAI tool. Do not open that PR while the external
SDK-host cap is full.

When copied upstream:
    from crewai_tools import UsdctoFiatCashoutTool
    # extra: crewai-tools[usdctofiat] = ["usdctofiat"]
    # Remove the draft-only BaseTool / pydantic fallbacks below.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

try:
    from crewai.tools import BaseTool
except ImportError:  # draft-only — delete this branch in the crewAIInc/crewAI copy
    class BaseTool:  # type: ignore[no-redef]
        name: str = ""
        description: str = ""
        args_schema: Any = None
        package_dependencies: list[str] = []

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

        def run(self, *args: Any, **kwargs: Any) -> Any:
            return self._run(*args, **kwargs)

        def _run(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

try:
    from pydantic import BaseModel, ConfigDict, Field
except ImportError:  # draft-only
    class BaseModel:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    def Field(*_args: Any, **_kwargs: Any) -> Any:  # type: ignore[misc]
        return None

    class ConfigDict(dict):  # type: ignore[no-redef]
        pass

from usdctofiat import create_offramp
from usdctofiat.errors import UsdctoFiatError
from usdctofiat.types import CashoutResult, Estimate, PreparedCashout, UnsignedTx

_BANNED_KEY_KWARGS = (
    "private_key",
    "privateKey",
    "key",
    "secret",
    "mnemonic",
    "wallet_key",
    "evm_private_key",
    "EVM_PRIVATE_KEY",
)


def _reject_keys_and_mode(kwargs: dict[str, Any], *, mode: Optional[str]) -> None:
    for banned in _BANNED_KEY_KWARGS:
        if banned in kwargs:
            raise TypeError(
                "This tool does not accept a private key. "
                "Inject a signer callback or call cashout without a signer "
                "to receive unsigned txs."
            )
    if mode is not None:
        raise TypeError(
            "This tool does not default mode. "
            'Pass mode="fast" (0% / TOFIAT) or mode="best" (Delegate, 10 bps) '
            "on each cashout/estimate call."
        )


def _offramp_from(kwargs: dict[str, Any]) -> Any:
    keys = (
        "curator_url",
        "indexer_url",
        "curator",
        "indexer",
        "referrer",
        "referrers",
        "extra_referrers",
        "referral_code",
    )
    return create_offramp(**{key: kwargs.pop(key) for key in keys if key in kwargs})


class UsdctoFiatCashoutSchema(BaseModel):
    """Input schema for UsdctoFiatCashoutTool. mode is required."""

    mode: str = Field(..., description='Required. "fast" (0% / TOFIAT) or "best" (Delegate, 10 bps).')
    amount: str = Field(..., description="Human USDC amount. An int is six-decimal units.")
    currency: str = Field(..., description="Fiat ISO code, e.g. EUR, USD, GBP.")
    platform: str = Field(..., description="Payment rail, e.g. revolut, venmo, monzo.")
    payee: str = Field(..., description="Handle on that platform.")


class UsdctoFiatEstimateSchema(BaseModel):
    mode: str = Field(..., description='Required. "fast" (0 bps) or "best" (10 bps).')
    amount: str = Field(..., description="Human USDC amount.")
    currency: str = Field(..., description="Fiat ISO code.")


class UsdctoFiatDepositSchema(BaseModel):
    deposit_id: str = Field(..., description="Fast composite resume key or Best numeric EscrowV2 id.")


class UsdctoFiatOwnerSchema(BaseModel):
    owner: str = Field(..., description="0x depositor on Base.")


class _UsdctoFiatBase(BaseTool):
    """Shared construction. Galleon Labs. Not Peer Cash."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    signer: Optional[Callable[[Any], Any]] = None
    offramp: Any = None
    package_dependencies: list[str] = ["usdctofiat"]

    def __init__(
        self,
        signer: Optional[Callable[[Any], Any]] = None,
        mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        _reject_keys_and_mode(kwargs, mode=mode)
        offramp = _offramp_from(kwargs)
        super().__init__(**kwargs)
        self.signer = signer
        self.offramp = offramp


class UsdctoFiatCashoutTool(_UsdctoFiatBase):
    """Cash out Base USDC to fiat via USDCtoFiat by Galleon Labs.

    mode is required. There is no default.
    - fast: 0% spread / 0 bps. We earn TOFIAT.
    - best: Delegate, 10 bps.

    If a signer was injected, unsigned txs are submitted and the deposit
    id / tx hash are returned. Otherwise this returns unsigned
    {to, data, value, chainId} txs for the host to sign. Never pass a
    wallet private key to this tool.
    """

    name: str = "usdctofiat_cashout"
    description: str = (
        "Cash out Base USDC to fiat via USDCtoFiat by Galleon Labs. "
        "Built on the public Peer/ZKP2P protocol. Not a Peer Cash product. "
        'mode is required: "fast" (0% / TOFIAT) or "best" (Delegate, 10 bps). '
        "Never pass a wallet private key."
    )
    args_schema: type[BaseModel] = UsdctoFiatCashoutSchema

    def _run(self, mode: str, amount: str, currency: str, platform: str, payee: str) -> str:
        try:
            if self.signer is None:
                prepared = self.offramp.prepare(
                    mode=mode,
                    amount=amount,
                    currency=currency,
                    platform=platform,
                    payee=payee,
                )
                return _dumps({"prepared": _as_dict(prepared), "signed": False})
            result = self.offramp.cashout(
                mode=mode,
                amount=amount,
                currency=currency,
                platform=platform,
                payee=payee,
                signer=self.signer,
            )
            return _dumps({"result": _as_dict(result), "signed": True})
        except Exception as exc:
            return _error(exc)


class UsdctoFiatEstimateTool(_UsdctoFiatBase):
    """Estimate a USDCtoFiat cash-out. Not a locked quote. mode is required."""

    name: str = "usdctofiat_estimate"
    description: str = (
        "Estimate a USDCtoFiat cash-out. Not a locked quote. "
        'mode is required: "fast" (0 bps) or "best" (10 bps). Galleon Labs. Not Peer Cash.'
    )
    args_schema: type[BaseModel] = UsdctoFiatEstimateSchema

    def _run(self, mode: str, amount: str, currency: str) -> str:
        try:
            return _dumps(_as_dict(self.offramp.estimate(mode=mode, amount=amount, currency=currency)))
        except Exception as exc:
            return _error(exc)


class UsdctoFiatWatchTool(_UsdctoFiatBase):
    """Watch a USDCtoFiat deposit by id (indexer snapshot)."""

    name: str = "usdctofiat_watch"
    description: str = "Watch a USDCtoFiat deposit by id. Galleon Labs. Not Peer Cash."
    args_schema: type[BaseModel] = UsdctoFiatDepositSchema

    def _run(self, deposit_id: str) -> str:
        try:
            rows = list(self.offramp.watch(deposit_id))
            return _dumps({"deposit_id": deposit_id, "snapshots": rows})
        except Exception as exc:
            return _error(exc)


class UsdctoFiatWithdrawTool(_UsdctoFiatBase):
    """Withdraw / close a USDCtoFiat deposit. Alias: close."""

    name: str = "usdctofiat_withdraw"
    description: str = "Withdraw or close a USDCtoFiat deposit. Galleon Labs. Not Peer Cash."
    args_schema: type[BaseModel] = UsdctoFiatDepositSchema

    def _run(self, deposit_id: str) -> str:
        try:
            result = self.offramp.withdraw(deposit_id, signer=self.signer)
            return _dumps(_as_dict(result))
        except Exception as exc:
            return _error(exc)

    def close(self, deposit_id: str) -> str:
        return self._run(deposit_id)


class UsdctoFiatDepositsTool(_UsdctoFiatBase):
    """List USDCtoFiat deposits for an owner address."""

    name: str = "usdctofiat_deposits"
    description: str = "List USDCtoFiat deposits for an owner on Base. Galleon Labs. Not Peer Cash."
    args_schema: type[BaseModel] = UsdctoFiatOwnerSchema

    def _run(self, owner: str) -> str:
        try:
            return _dumps({"owner": owner, "deposits": self.offramp.deposits(owner)})
        except Exception as exc:
            return _error(exc)


def _as_dict(value: Any) -> Any:
    if isinstance(value, (CashoutResult, PreparedCashout, Estimate, UnsignedTx)):
        return value.as_dict()
    if hasattr(value, "as_dict"):
        return value.as_dict()
    return value


def _dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def _error(exc: Exception) -> str:
    payload: dict[str, Any] = {"error": str(exc), "code": getattr(exc, "code", type(exc).__name__)}
    if isinstance(exc, UsdctoFiatError) and exc.details is not None:
        payload["details"] = exc.details
    return _dumps(payload)
