
"""Approve + EscrowV2 createDeposit / withdraw / setRateManager encoding.

Encoding only. No LocalAccount, no private keys.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from eth_abi import encode
from eth_utils import function_signature_to_4byte_selector, keccak, to_checksum_address

from .attribution import Attribution, append_attribution, lock_attribution
from .constants import (
    ACCESS_POLICY_PLATFORMS,
    BEST_MANAGER_FEE_BPS,
    CHAIN_ID,
    CHAINLINK_ORACLE_ADAPTER,
    CHAINLINK_ORACLE_FEEDS,
    CURRENCY_HASHES,
    DEFAULT_ORACLE_MAX_STALENESS,
    ESCROW_V2,
    FAST_SPREAD_BPS,
    GATING_SERVICE,
    INTENT_GUARDIAN,
    MIN_CONVERSION_RATE,
    MIN_USDC_UNITS,
    PAYMENT_METHOD_HASHES,
    RATE_MANAGER_V1,
    USDC,
    USDC_UNITS,
    ZERO_ADDRESS,
)
from .errors import ValidationError
from .types import DelegateHook, UnsignedTx

CREATE_DEPOSIT_SIG = (
    "createDeposit((address,uint256,(uint256,uint256),bytes32[],"
    "(address,bytes32,bytes)[],(bytes32,uint256,(address,bytes,int16,uint32))[][],"
    "address,address,bool))"
)
APPROVE_SIG = "approve(address,uint256)"
WITHDRAW_SIG = "withdrawDeposit(uint256)"
SET_RATE_MANAGER_SIG = "setRateManager(uint256,address,bytes32)"
DEPOSIT_RECEIVED_SIG = (
    "DepositReceived(uint256,address,address,uint256,(uint256,uint256),address,address)"
)

CREATE_DEPOSIT_SELECTOR = function_signature_to_4byte_selector(CREATE_DEPOSIT_SIG)
APPROVE_SELECTOR = function_signature_to_4byte_selector(APPROVE_SIG)
WITHDRAW_SELECTOR = function_signature_to_4byte_selector(WITHDRAW_SIG)
SET_RATE_MANAGER_SELECTOR = function_signature_to_4byte_selector(SET_RATE_MANAGER_SIG)
DEPOSIT_RECEIVED_TOPIC = "0x" + keccak(text=DEPOSIT_RECEIVED_SIG).hex()

CREATE_DEPOSIT_TUPLE = (
    "(address,uint256,(uint256,uint256),bytes32[],"
    "(address,bytes32,bytes)[],(bytes32,uint256,(address,bytes,int16,uint32))[][],"
    "address,address,bool)"
)


def checksum(addr: str) -> str:
    return to_checksum_address(addr)


def parse_usdc_amount(amount: object) -> int:
    """int = exact 6-decimal units. str/float/Decimal = human USDC."""
    if isinstance(amount, bool):
        raise ValidationError("amount must be a USDC quantity", field="amount")
    if isinstance(amount, int):
        units = amount
    else:
        try:
            human = Decimal(str(amount))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"invalid amount: {amount!r}", field="amount") from exc
        if human <= 0:
            raise ValidationError("amount must be positive", field="amount")
        units = int(human * Decimal(USDC_UNITS))
    if units < MIN_USDC_UNITS:
        raise ValidationError("minimum 1 USDC", field="amount")
    return units


def currency_hash(code: str) -> str:
    key = code.strip().upper()
    if key in CURRENCY_HASHES:
        return CURRENCY_HASHES[key]
    return "0x" + keccak(text=key).hex()


def oracle_feed_for(currency: str) -> tuple[str, bool]:
    """Chainlink (feed, invert) for a currency. Raises when the protocol has no feed."""
    key = currency.strip().upper()
    if key not in CHAINLINK_ORACLE_FEEDS:
        raise ValidationError(
            f"unsupported currency {currency!r}: no Chainlink feed on Base, so the deposit "
            f"rate cannot be priced. Supported: {sorted(CHAINLINK_ORACLE_FEEDS)}",
            field="currency",
        )
    return CHAINLINK_ORACLE_FEEDS[key]


def payment_method_hash(platform: str) -> str:
    key = platform.strip().lower()
    if key not in PAYMENT_METHOD_HASHES:
        raise ValidationError(
            f"unsupported platform {platform!r}. v1: {sorted(PAYMENT_METHOD_HASHES)}",
            field="platform",
        )
    return PAYMENT_METHOD_HASHES[key]


def normalize_payee(platform: str, payee: str) -> str:
    key = platform.strip().lower()
    text = (payee or "").strip()
    if not text:
        raise ValidationError("payee is required", field="payee")
    if key == "venmo":
        return text.lstrip("@")
    if key == "cashapp":
        return text.lstrip("$")
    if key in {"revolut", "wise"}:
        return text.lstrip("@")
    if key == "paypal":
        lowered = text.replace("https://", "").replace("http://", "")
        lowered = lowered.replace("www.", "")
        if lowered.lower().startswith("paypal.me/"):
            lowered = lowered[10:]
        return lowered
    if key == "zelle":
        return text.lower()
    if key == "chime":
        body = text.lower().lstrip("$")
        return f"${body}"
    if key == "monzo":
        body = text.replace("https://", "").replace("http://", "")
        if "monzo.me/" in body:
            body = body.split("monzo.me/", 1)[1]
        return body.lstrip("@")
    return text


def encode_oracle_adapter_config(feed: str = ZERO_ADDRESS, invert: bool = False) -> bytes:
    """Chainlink adapter: abi.encode(address feed, bool invert). USD passthrough is address(0)."""
    return encode(["address", "bool"], [checksum(feed), invert])


def encode_approve(amount_units: int, *, spender: str = ESCROW_V2, attribution: Attribution | None = None) -> str:
    body = APPROVE_SELECTOR + encode(["address", "uint256"], [checksum(spender), amount_units])
    return append_attribution(body, attribution)


def encode_create_deposit(
    *,
    amount_units: int,
    payee_details_hash: str,
    platform: str,
    currency: str,
    mode: str = "fast",
    attribution: Attribution | None = None,
    intent_min: int | None = None,
    intent_max: int | None = None,
    gating_service: str = GATING_SERVICE,
    verification_data: bytes = b"",
    delegate: str = ZERO_ADDRESS,
    intent_guardian: str = INTENT_GUARDIAN,
    retain_on_empty: bool = False,
    oracle_adapter: str | None = None,
    oracle_feed: str | None = None,
    oracle_invert: bool | None = None,
) -> str:
    """EscrowV2.createDeposit at the oracle floor. Fast: 0 bps, no Delegate vault."""
    if not payee_details_hash or payee_details_hash == ZERO_ADDRESS:
        raise ValidationError("payee_details_hash is required", field="payee_details_hash")
    method = bytes.fromhex(payment_method_hash(platform)[2:])
    payee = bytes.fromhex(_bytes32(payee_details_hash)[2:])
    code = bytes.fromhex(currency_hash(currency)[2:])
    lo = intent_min if intent_min is not None else MIN_USDC_UNITS
    hi = intent_max if intent_max is not None else amount_units
    if lo <= 0 or lo > hi:
        raise ValidationError("invalid intent range", field="intent_amount_range")

    # Every currency is priced by its Chainlink feed, not by a fixed rate. USD is
    # the zero-address passthrough (constant 1.0); the rest invert a USD-quoted
    # feed to fiat per USDC. A currency with no feed raises rather than encoding a
    # silent 1:1 rate.
    feed, invert = oracle_feed_for(currency)
    if oracle_feed is not None:
        feed = oracle_feed
    if oracle_invert is not None:
        invert = oracle_invert
    if feed == ZERO_ADDRESS:
        invert = False  # the passthrough is constant 1.0; there is nothing to invert
    adapter = oracle_adapter or CHAINLINK_ORACLE_ADAPTER
    oracle = (
        checksum(adapter),
        encode_oracle_adapter_config(feed, invert),
        FAST_SPREAD_BPS,
        DEFAULT_ORACLE_MAX_STALENESS,
    )

    # The oracle sets the rate, so the floor is one wei. A 1e18 floor would price
    # every deposit at 1.0 fiat per USDC regardless of the feed.
    currency_row = (code, MIN_CONVERSION_RATE, oracle)
    payment_data = (checksum(gating_service), payee, verification_data)
    # retain_on_empty is False so a drained deposit closes. Retaining it leaves the
    # deposit active and accepting intents with nothing left to release.
    params = (
        checksum(USDC),
        amount_units,
        (lo, hi),
        [method],
        [payment_data],
        [[currency_row]],
        checksum(delegate),
        checksum(intent_guardian),
        retain_on_empty,
    )
    body = CREATE_DEPOSIT_SELECTOR + encode([CREATE_DEPOSIT_TUPLE], [params])
    return append_attribution(body, attribution)


def encode_withdraw(deposit_id: int, *, attribution: Attribution | None = None) -> str:
    body = WITHDRAW_SELECTOR + encode(["uint256"], [deposit_id])
    return append_attribution(body, attribution)


def encode_set_rate_manager(
    deposit_id: int,
    *,
    rate_manager: str = RATE_MANAGER_V1,
    rate_manager_id: str | bytes | None = None,
    attribution: Attribution | None = None,
) -> str:
    """Best hook. Requires a known EscrowV2 deposit id. Does not invent a second vault."""
    if rate_manager_id is None:
        raise ValidationError(
            "Best setRateManager needs the Delegate rateManagerId after deposit creation",
            field="rate_manager_id",
        )
    rm_id = _bytes32(rate_manager_id)
    body = SET_RATE_MANAGER_SELECTOR + encode(
        ["uint256", "address", "bytes32"],
        [deposit_id, checksum(rate_manager), bytes.fromhex(rm_id[2:])],
    )
    return append_attribution(body, attribution)


def unsigned_tx(to: str, data: str, value: int = 0) -> UnsignedTx:
    return UnsignedTx(to=checksum(to), data=data if data.startswith("0x") else "0x" + data, value=value, chain_id=CHAIN_ID)


def approve_tx(amount_units: int, attribution: Attribution | None = None) -> UnsignedTx:
    return unsigned_tx(USDC, encode_approve(amount_units, attribution=attribution))


def create_deposit_tx(**kwargs: object) -> UnsignedTx:
    data = encode_create_deposit(**kwargs)  # type: ignore[arg-type]
    return unsigned_tx(ESCROW_V2, data)


def withdraw_tx(deposit_id: int, attribution: Attribution | None = None) -> UnsignedTx:
    return unsigned_tx(ESCROW_V2, encode_withdraw(deposit_id, attribution=attribution))


def set_rate_manager_tx(deposit_id: int, **kwargs: object) -> UnsignedTx:
    return unsigned_tx(ESCROW_V2, encode_set_rate_manager(deposit_id, **kwargs))  # type: ignore[arg-type]


def delegate_hook() -> DelegateHook:
    return DelegateHook(to=checksum(ESCROW_V2), rate_manager=checksum(RATE_MANAGER_V1), fee_bps=BEST_MANAGER_FEE_BPS)


def access_policy_required(platform: str) -> bool:
    return platform.strip().lower() in ACCESS_POLICY_PLATFORMS


def extract_deposit_id(receipt: object) -> str | None:
    """Best-effort DepositReceived parse. Hosts may also pass deposit_id on the receipt."""
    if receipt is None:
        return None
    if not hasattr(receipt, "get"):
        return None
    data = receipt  # mapping-like
    for key in ("deposit_id", "depositId", "id"):
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    logs = data.get("logs") or []
    for log in logs:
        topics = log.get("topics") or []
        if not topics:
            continue
        if _receipt_hex(topics[0]).lower() == DEPOSIT_RECEIVED_TOPIC.lower() and len(topics) > 1:
            return str(int(_receipt_hex(topics[1]), 16))
    return None


TX_HASH_KEYS = ("tx_hash", "hash", "txHash", "transactionHash", "transaction_hash")


def extract_tx_hash(result: object) -> str:
    """Best-effort tx hash from a signer return. web3.py keys it transactionHash
    and hands back HexBytes; other hosts return a plain 0x string or tx_hash."""
    if result is None:
        return ""
    if isinstance(result, (str, bytes)):
        return _receipt_hex(result)
    if not hasattr(result, "get"):
        return ""
    for key in TX_HASH_KEYS:
        value = result.get(key)
        if value in (None, ""):
            continue
        text = _receipt_hex(value)
        if text:
            return text
    return ""


def _receipt_hex(value: object) -> str:
    """Receipt fields are HexBytes on web3.py, plain bytes, ints or 0x strings elsewhere."""
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, int):
        return hex(value)
    return str(value)


def _bytes32(value: str | bytes) -> str:
    if isinstance(value, bytes):
        hexed = value.hex()
        return "0x" + hexed.rjust(64, "0")[-64:]
    text = value[2:] if str(value).startswith("0x") else str(value)
    if all(c in "0123456789abcdefABCDEF" for c in text) and len(text) <= 64:
        return "0x" + text.rjust(64, "0")
    return "0x" + keccak(text=str(value)).hex()
