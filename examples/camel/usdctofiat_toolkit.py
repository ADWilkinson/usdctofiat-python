"""UsdctoFiatToolkit — CAMEL toolkit reference implementation.

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
Docs: https://usdctofiat.xyz/developers

Wraps `usdctofiat.cashout(mode="fast"|"best")`, `watch`, `withdraw`/`close`,
`deposits`, and `estimate`. Mode is required on every priced or mutating call.
There is no default to Fast or Best. This toolkit never accepts a wallet
private key — inject a signer callback, or call cashout without one to
receive unsigned `{to, data, value, chainId}` txs.

This reference implementation maps to `camel/toolkits/usdctofiat_toolkit.py`.

When copied upstream:
    from camel.toolkits import UsdctoFiatToolkit
    # @dependencies_required("usdctofiat")
    # Remove the standalone BaseToolkit / FunctionTool fallbacks below.
"""

from __future__ import annotations

import json
from typing import Any, Callable, List, Optional

try:
    from camel.toolkits.base import BaseToolkit
    from camel.toolkits.function_tool import FunctionTool
    from camel.utils import dependencies_required
except ImportError:  # standalone reference fallback
    class BaseToolkit:  # type: ignore[no-redef]
        def __init__(self, timeout: Optional[float] = None) -> None:
            self.timeout = timeout

    class FunctionTool:  # type: ignore[no-redef]
        def __init__(self, func: Callable[..., Any]) -> None:
            self.func = func
            self.name = getattr(func, "__name__", str(func))

    def dependencies_required(*_names: str):  # type: ignore[misc]
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return deco

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


class UsdctoFiatToolkit(BaseToolkit):
    r"""USDCtoFiat toolkit for CAMEL agents by Galleon Labs.

    Args:
        signer: Optional callback ``(unsigned_tx) -> hash | {hash, deposit_id}``.
            Kept in the host runtime. Never a private key.
        timeout: Optional per-call timeout forwarded to BaseToolkit.
    """

    @dependencies_required("usdctofiat")
    def __init__(
        self,
        signer: Optional[Callable[[Any], Any]] = None,
        timeout: Optional[float] = None,
        mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        for banned in _BANNED_KEY_KWARGS:
            if banned in kwargs:
                raise TypeError(
                    "UsdctoFiatToolkit does not accept a private key. "
                    "Inject a signer callback or call cashout without a signer "
                    "to receive unsigned txs."
                )
        if mode is not None:
            raise TypeError(
                "UsdctoFiatToolkit does not default mode. "
                'Pass mode="fast" (0% / TOFIAT) or mode="best" (Delegate, 10 bps) '
                "on each cashout/estimate call."
            )
        super().__init__(timeout=timeout)
        self.signer = signer
        self.offramp = create_offramp(
            **{
                key: kwargs.pop(key)
                for key in (
                    "curator_url",
                    "indexer_url",
                    "curator",
                    "indexer",
                    "referrer",
                    "referrers",
                    "extra_referrers",
                    "referral_code",
                )
                if key in kwargs
            }
        )

    def cashout(
        self,
        mode: str,
        amount: str,
        currency: str,
        platform: str,
        payee: str,
    ) -> str:
        r"""Cash out Base USDC to fiat via USDCtoFiat by Galleon Labs.

        mode is required. There is no default.
        - fast: Live market pricing with 0% spread / 0 bps.
        - best: Delegate, 10 bps.

        If a signer was injected, unsigned txs are submitted and the deposit
        id / tx hash are returned. Otherwise this returns unsigned
        {to, data, value, chainId} txs for the host to sign. Never pass a
        wallet private key to this toolkit.

        Args:
            mode (str): ``"fast"`` or ``"best"``. Required.
            amount (str): Human USDC amount (string or number). An int is
                six-decimal units.
            currency (str): Fiat ISO code, e.g. EUR, USD, GBP.
            platform (str): Payment rail, e.g. revolut, venmo, monzo.
            payee (str): Handle on that platform.

        Returns:
            str: JSON string with the cash-out result or unsigned prepare
            payload.
        """
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

    def watch(self, deposit_id: str) -> str:
        r"""Watch a USDCtoFiat deposit by id (indexer snapshot).

        Args:
            deposit_id (str): Fast composite resume key or Best numeric
                EscrowV2 id.

        Returns:
            str: JSON list of deposit snapshots.
        """
        try:
            rows = list(self.offramp.watch(deposit_id))
            return _dumps({"deposit_id": deposit_id, "snapshots": rows})
        except Exception as exc:
            return _error(exc)

    def withdraw(self, deposit_id: str) -> str:
        r"""Withdraw / close a USDCtoFiat deposit.

        Returns a signed result when a signer is injected, otherwise the
        unsigned withdraw tx.

        Args:
            deposit_id (str): EscrowV2 deposit id.
        """
        try:
            result = self.offramp.withdraw(deposit_id, signer=self.signer)
            return _dumps(_as_dict(result))
        except Exception as exc:
            return _error(exc)

    def close(self, deposit_id: str) -> str:
        r"""Alias of withdraw. Unwind a Best (or Fast) deposit."""
        return self.withdraw(deposit_id)

    def deposits(self, owner: str) -> str:
        r"""List USDCtoFiat deposits for an owner address.

        Args:
            owner (str): 0x depositor on Base.
        """
        try:
            return _dumps({"owner": owner, "deposits": self.offramp.deposits(owner)})
        except Exception as exc:
            return _error(exc)

    def estimate(self, mode: str, amount: str, currency: str) -> str:
        r"""Estimate a USDCtoFiat cash-out. Not a locked quote.

        mode is required. fast = 0 bps seller spread. best = 10 bps manager fee.

        Args:
            mode (str): ``"fast"`` or ``"best"``. Required.
            amount (str): Human USDC amount.
            currency (str): Fiat ISO code.
        """
        try:
            return _dumps(_as_dict(self.offramp.estimate(mode=mode, amount=amount, currency=currency)))
        except Exception as exc:
            return _error(exc)

    def get_tools(self) -> List[FunctionTool]:
        r"""Return FunctionTool wrappers for cashout, estimate, watch, withdraw, close, deposits."""
        return [
            FunctionTool(self.cashout),
            FunctionTool(self.estimate),
            FunctionTool(self.watch),
            FunctionTool(self.withdraw),
            FunctionTool(self.close),
            FunctionTool(self.deposits),
        ]


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
