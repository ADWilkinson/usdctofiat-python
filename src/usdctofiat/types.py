
"""Public result types. Unsigned txs only — no signed accounts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping

Mode = Literal["fast", "best"]
Signer = Callable[["UnsignedTx"], str | Mapping[str, Any]]


@dataclass(frozen=True)
class UnsignedTx:
    to: str
    data: str
    value: int = 0
    chain_id: int = 8453

    def as_dict(self) -> dict[str, Any]:
        return {
            "to": self.to,
            "data": self.data,
            "value": hex(self.value),
            "chainId": self.chain_id,
        }


@dataclass(frozen=True)
class DelegateHook:
    """Best-mode follow-up. Same deposit, then attach the Delegate rate manager."""

    step: str = "setRateManager"
    to: str = ""
    rate_manager: str = ""
    rate_manager_id: str = ""
    fee_bps: int = 10
    requires: str = "deposit_id"
    note: str = (
        "Best is the same createDeposit as Fast, then EscrowV2.setRateManager "
        "on RateManagerV1 with rate_manager_id (10 bps). Encode after deposit_id "
        "is known. v1 does not invent a second vault."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "to": self.to,
            "rate_manager": self.rate_manager,
            "rate_manager_id": self.rate_manager_id,
            "fee_bps": self.fee_bps,
            "requires": self.requires,
            "note": self.note,
        }


@dataclass
class PreparedCashout:
    mode: Mode
    txs: list[UnsignedTx]
    steps: list[str]
    payee_details_hash: str
    amount_units: int
    platform: str
    currency: str
    attribution: Mapping[str, Any]
    delegate_hook: DelegateHook | None = None
    access_policy_required: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "txs": [tx.as_dict() for tx in self.txs],
            "steps": list(self.steps),
            "payee_details_hash": self.payee_details_hash,
            "amount_units": str(self.amount_units),
            "platform": self.platform,
            "currency": self.currency,
            "attribution": dict(self.attribution),
            "delegate_hook": self.delegate_hook.as_dict() if self.delegate_hook else None,
            "access_policy_required": self.access_policy_required,
        }


@dataclass
class CashoutResult:
    deposit_id: str | None
    tx_hash: str | None
    mode: Mode
    tx_hashes: list[str] = field(default_factory=list)
    prepared: PreparedCashout | None = None
    delegate_hook: DelegateHook | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "deposit_id": self.deposit_id,
            "tx_hash": self.tx_hash,
            "mode": self.mode,
            "tx_hashes": list(self.tx_hashes),
            "delegate_hook": self.delegate_hook.as_dict() if self.delegate_hook else None,
        }


@dataclass
class Estimate:
    mode: Mode
    amount_units: int
    currency: str
    rate: str
    """Target-currency units per 1 USDC, read from the currency's Chainlink feed."""
    receive_amount: str
    spread_bps: int
    manager_fee_bps: int
    as_of: int = 0
    """Unix seconds when the oracle was read."""
    oracle_updated_at: int | None = None
    """Unix seconds the feed last updated. None for the USD passthrough."""
    stale: bool = False
    """The feed reading is older than a day. Treat the rate with caution."""
    kind: str = "oracle-estimate"
    note: str = "Approximate. The binding rate resolves at fill. Not a locked quote."

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "amount_units": str(self.amount_units),
            "currency": self.currency,
            "rate": self.rate,
            "receive_amount": self.receive_amount,
            "spread_bps": self.spread_bps,
            "manager_fee_bps": self.manager_fee_bps,
            "as_of": self.as_of,
            "oracle_updated_at": self.oracle_updated_at,
            "stale": self.stale,
            "kind": self.kind,
            "note": self.note,
        }
