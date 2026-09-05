
import json

import pytest
from eth_abi import decode
from eth_utils import decode_hex

from usdctofiat import create_offramp
from usdctofiat.attribution import erc8021_suffix, lock_attribution, parse_erc8021
from usdctofiat.calldata import (
    APPROVE_SELECTOR,
    CREATE_DEPOSIT_SELECTOR,
    CREATE_DEPOSIT_TUPLE,
    SET_RATE_MANAGER_SELECTOR,
    WITHDRAW_SELECTOR,
    encode_approve,
    encode_create_deposit,
    encode_set_rate_manager,
    encode_withdraw,
    extract_deposit_id,
    extract_tx_hash,
    normalize_payee,
    parse_usdc_amount,
)
from usdctofiat.constants import (
    CHAINLINK_ORACLE_ADAPTER,
    CHAINLINK_ORACLE_FEEDS,
    CURATOR_URL,
    DEFAULT_ORACLE_MAX_STALENESS,
    DELEGATE_RATE_MANAGER_ID,
    ERC8021_MARKER,
    ESCROW_V2,
    FAST_SPREAD_BPS,
    GATING_SERVICE,
    INTENT_GUARDIAN,
    MAKERS_CREATE_PATH,
    MIN_CONVERSION_RATE,
    PRECISE_UNIT,
    RATE_MANAGER_V1,
    USDC,
    ZERO_ADDRESS,
)
from usdctofiat.errors import ValidationError


PAYEE = "0x1111111111111111111111111111111111111111111111111111111111111111"


def _decode_create_deposit(data: str):
    raw = decode_hex(data)
    payload = raw[4 : raw.rfind(ERC8021_MARKER)]
    return decode([CREATE_DEPOSIT_TUPLE], payload)[0]


def _currency_row(data: str):
    """The single (code, minConversionRate, oracleRateConfig) row of the deposit."""
    return _decode_create_deposit(data)[5][0][0]


def _decode_adapter_config(adapter_config: bytes) -> tuple[str, bool]:
    feed, invert = decode(["address", "bool"], adapter_config)
    return feed.lower(), invert


def _deposit_for(currency: str, **kwargs) -> str:
    return encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency=currency,
        **kwargs,
    )


def test_parse_usdc_human_and_units():
    assert parse_usdc_amount("100") == 100_000_000
    assert parse_usdc_amount(1_000_000) == 1_000_000
    try:
        parse_usdc_amount(100)  # exact units below 1 USDC
        raise AssertionError("expected minimum")
    except ValidationError as exc:
        assert "1 USDC" in str(exc)
    try:
        parse_usdc_amount("0.5")
        raise AssertionError("expected minimum")
    except ValidationError as exc:
        assert "1 USDC" in str(exc)


def test_normalize_payee_platform_rules():
    assert normalize_payee("venmo", "@Alice") == "Alice"
    assert normalize_payee("cashapp", "$tag") == "tag"
    assert normalize_payee("zelle", "Maker@Example.com") == "maker@example.com"
    assert normalize_payee("chime", "Sign") == "$sign"
    assert normalize_payee("paypal", "https://paypal.me/alice") == "alice"


# Lifted from `@usdctofiat/offramp@9.0.0` `normalizePaypalMeUsername`. The
# previous paypal branch only passed the last green row; a paypal.com/paypalme
# link, mixed case, a query tail or a leading @ all hashed a different string.
PAYPAL_ME_ROWS = [
    ("https://www.paypal.com/paypalme/Alice", "alice"),
    ("https://www.paypal.com/paypalme/alice/25", "alice"),
    ("https://paypal.me/Alice", "alice"),
    ("paypal.me/Alice", "alice"),
    ("Alice", "alice"),
    ("@alice", "alice"),
    ("https://paypal.me/alice?country.x=GB", "alice"),
    ("https://paypal.me/alice", "alice"),
    ("paypal.me", ""),
    ("paypal.com", ""),
    ("https://example.com/alice", "https://example.com/alice"),
    ("example.com/alice", "example.com/alice"),
]


@pytest.mark.parametrize("payee,expected", PAYPAL_ME_ROWS)
def test_normalize_payee_paypal_matches_the_reference(payee, expected):
    assert normalize_payee("paypal", payee) == expected


def test_prepare_posts_the_normalized_paypal_handle(mocked_http):
    """The curator hashes offchainId as-is. A paypal.com/paypalme link used to
    be posted whole, so payeeDetailsHash could never match a PayPal payment."""
    create_offramp().prepare(
        mode="fast",
        amount="100",
        currency="GBP",
        platform="paypal",
        payee="https://www.paypal.com/paypalme/Alice",
    )
    curator = [
        call
        for call in mocked_http.calls
        if str(call.request.url) == f"{CURATOR_URL}{MAKERS_CREATE_PATH}"
    ]
    assert len(curator) == 1
    body = json.loads(curator[0].request.content)
    assert body == {"processorName": "paypal", "offchainId": "alice"}


def test_approve_and_create_deposit_selectors_and_lock():
    approve = encode_approve(100_000_000)
    assert decode_hex(approve)[:4] == APPROVE_SELECTOR
    assert USDC[2:].lower() not in approve[10:74]  # spender is escrow
    # spender is EscrowV2
    assert ESCROW_V2[2:].lower() in approve.lower()
    assert parse_erc8021(approve)[:2] == ("galleonlabs", "peer-ref-TOFIAT")

    data = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
    )
    raw = decode_hex(data)
    assert raw[:4] == CREATE_DEPOSIT_SELECTOR
    assert USDC[2:].lower() in data.lower()
    assert parse_erc8021(data)[:2] == ("galleonlabs", "peer-ref-TOFIAT")


def test_create_deposit_defaults_intent_guardian_to_protocol_guardian():
    data = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
    )
    guardian = _decode_create_deposit(data)[7]
    assert guardian.lower() == INTENT_GUARDIAN.lower()
    assert guardian.lower() != ZERO_ADDRESS.lower()


def test_create_deposit_encodes_explicit_intent_guardian():
    other = "0x1111111111111111111111111111111111111111"
    zeroed = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
        intent_guardian=ZERO_ADDRESS,
    )
    custom = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
        intent_guardian=other,
    )
    assert _decode_create_deposit(zeroed)[7].lower() == ZERO_ADDRESS.lower()
    assert _decode_create_deposit(custom)[7].lower() == other.lower()


def test_create_deposit_defaults_to_the_protocol_gating_service():
    """0.1.0 encoded intentGatingService = 0x0, which skips the gating check. (#16)"""
    data = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
    )
    gating_service = _decode_create_deposit(data)[4][0][0]
    assert gating_service.lower() == GATING_SERVICE.lower()
    assert gating_service.lower() != ZERO_ADDRESS.lower()


def test_create_deposit_encodes_explicit_gating_service():
    other = "0x2222222222222222222222222222222222222222"
    zeroed = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
        gating_service=ZERO_ADDRESS,
    )
    custom = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
        gating_service=other,
    )
    assert _decode_create_deposit(zeroed)[4][0][0].lower() == ZERO_ADDRESS.lower()
    assert _decode_create_deposit(custom)[4][0][0].lower() == other.lower()


def test_create_deposit_closes_a_drained_deposit_by_default():
    """retainOnEmpty = True left every cashout as a zombie ACTIVE deposit. (#16)"""
    data = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
    )
    assert _decode_create_deposit(data)[8] is False
    retained = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
        retain_on_empty=True,
    )
    assert _decode_create_deposit(retained)[8] is True


def test_create_deposit_attaches_the_chainlink_feed_for_every_currency():
    """Non-USD deposits were encoded with no oracle at a fixed 1.0 fiat per USDC. (#11)"""
    for currency in ("EUR", "GBP", "MXN", "AUD", "ZAR"):
        feed, invert, decimals = CHAINLINK_ORACLE_FEEDS[currency]
        _, _, oracle = _currency_row(_deposit_for(currency))
        adapter, adapter_config, spread_bps, max_staleness = oracle
        assert adapter.lower() == CHAINLINK_ORACLE_ADAPTER.lower()
        assert _decode_adapter_config(adapter_config) == (feed.lower(), invert)
        assert invert is True
        assert decimals == 8
        assert spread_bps == FAST_SPREAD_BPS
        assert max_staleness == DEFAULT_ORACLE_MAX_STALENESS


def test_create_deposit_keeps_the_usd_passthrough_oracle():
    """USD prices off the zero-address passthrough, not a feed."""
    _, _, oracle = _currency_row(_deposit_for("USD"))
    adapter, adapter_config, _, _ = oracle
    assert adapter.lower() == CHAINLINK_ORACLE_ADAPTER.lower()
    assert _decode_adapter_config(adapter_config) == (ZERO_ADDRESS.lower(), False)


def test_create_deposit_floors_the_rate_at_one_wei():
    """The oracle sets the price. A 1e18 floor priced every currency at 1:1. (#11)"""
    for currency in ("USD", "EUR", "MXN"):
        _, min_conversion_rate, _ = _currency_row(_deposit_for(currency))
        assert min_conversion_rate == MIN_CONVERSION_RATE == 1
        assert min_conversion_rate != PRECISE_UNIT


def test_create_deposit_rejects_a_currency_with_no_feed():
    """keccak(code) is a valid onchain currency, so an unpriceable code must not encode."""
    for currency in ("JPY", "INR", "NOK", "NOPE"):
        try:
            _deposit_for(currency)
            raise AssertionError(f"expected {currency} to be rejected")
        except ValidationError as exc:
            assert exc.field == "currency"


def test_create_deposit_honours_an_explicit_feed_override():
    other = "0x2222222222222222222222222222222222222222"
    data = _deposit_for("EUR", oracle_feed=other, oracle_invert=False)
    _, _, oracle = _currency_row(data)
    assert _decode_adapter_config(oracle[1]) == (other.lower(), False)


def test_withdraw_and_set_rate_manager_selectors():
    wd = encode_withdraw(42)
    assert decode_hex(wd)[:4] == WITHDRAW_SELECTOR
    rm = encode_set_rate_manager(42, rate_manager_id="0x" + "ab" * 32)
    assert decode_hex(rm)[:4] == SET_RATE_MANAGER_SELECTOR
    assert RATE_MANAGER_V1[2:].lower() in rm.lower()
    assert parse_erc8021(rm)[0] == "galleonlabs"


def _set_rate_manager_args(data: str):
    raw = decode_hex(data)
    payload = raw[4 : raw.rfind(ERC8021_MARKER)]
    deposit_id, rate_manager, rm_id = decode(["uint256", "address", "bytes32"], payload)
    return deposit_id, rate_manager.lower(), "0x" + rm_id.hex()


def test_set_rate_manager_defaults_to_the_delegate_registry_entry():
    """The id was a required argument no install could supply, so Best could not encode.

    setRateManager takes (depositId, address, bytes32 rateManagerId). The address
    has been shipped since #28; without the id the call raised ValidationError
    from every entry point.
    """
    deposit_id, rate_manager, rm_id = _set_rate_manager_args(encode_set_rate_manager(4527))
    assert deposit_id == 4527
    assert rate_manager == RATE_MANAGER_V1.lower()
    assert rm_id == DELEGATE_RATE_MANAGER_ID


def test_set_rate_manager_honours_an_explicit_id():
    """Another registry entry is still drivable; the default is not a lock."""
    other = "0x" + "cd" * 32
    _, _, rm_id = _set_rate_manager_args(encode_set_rate_manager(7, rate_manager_id=other))
    assert rm_id == other


def test_extract_deposit_id_from_receipt_and_log():
    assert extract_deposit_id({"deposit_id": "99"}) == "99"
    topic = "0x" + "11" * 32
    from usdctofiat.calldata import DEPOSIT_RECEIVED_TOPIC

    receipt = {"logs": [{"topics": [DEPOSIT_RECEIVED_TOPIC, hex(7)]}]}
    assert extract_deposit_id(receipt) == "7"
    assert extract_deposit_id(None) is None


def test_extract_deposit_id_from_bytes_topics():
    """web3.py hands back HexBytes topics; both topic0 and the id must decode."""
    from usdctofiat.calldata import DEPOSIT_RECEIVED_TOPIC

    class HexBytes(bytes):  # web3.py's type, minus the dependency
        def __repr__(self) -> str:
            return f"HexBytes('0x{self.hex()}')"

        __str__ = __repr__

    topic0 = HexBytes(bytes.fromhex(DEPOSIT_RECEIVED_TOPIC[2:]))
    for topic1 in (HexBytes((7).to_bytes(32, "big")), (7).to_bytes(32, "big"), 7, hex(7)):
        receipt = {"logs": [{"topics": [topic0, topic1]}]}
        assert extract_deposit_id(receipt) == "7"


def test_extract_tx_hash_reads_web3_receipt_keys():
    """web3.py keys the hash transactionHash and hands back HexBytes."""

    class HexBytes(bytes):  # web3.py's type, minus the dependency
        def __repr__(self) -> str:
            return f"HexBytes('0x{self.hex()}')"

        __str__ = __repr__

    expected = "0x" + "ab" * 32
    raw = bytes.fromhex("ab" * 32)
    for value in (HexBytes(raw), raw, expected):
        for key in ("tx_hash", "hash", "txHash", "transactionHash", "transaction_hash"):
            assert extract_tx_hash({key: value}) == expected
    assert extract_tx_hash(expected) == expected
    assert extract_tx_hash({"status": 1}) == ""
    assert extract_tx_hash(None) == ""


# `createDeposit` calldata for the case below, encoded by viem against the EscrowV2
# ABI from `@zkp2p/sdk` 0.12.1 `getContracts(8453, "production")`, with
# `getGatingServiceAddress` and `getSpreadOracleConfig` supplying the gating service
# and the EUR oracle. This is the reference `@usdctofiat/offramp` 8.0.2 builds, minus
# its attribution suffix. Regenerate it from the TS SDK, never from this client.
REFERENCE_CREATE_DEPOSIT = (
    "ab3532c800000000000000000000000000000000000000000000000000000000"
    "00000020000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54"
    "bda0291300000000000000000000000000000000000000000000000000000000"
    "05f5e10000000000000000000000000000000000000000000000000000000000"
    "000f424000000000000000000000000000000000000000000000000000000000"
    "05f5e10000000000000000000000000000000000000000000000000000000000"
    "0000014000000000000000000000000000000000000000000000000000000000"
    "0000018000000000000000000000000000000000000000000000000000000000"
    "0000024000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000083671606454fa72ba1e2831e18c5090d"
    "2562941400000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "00000001617f88ab82b5c1b014c539f7e75121427f0bb50a4c58b187a238531e"
    "7d58605d00000000000000000000000000000000000000000000000000000000"
    "0000000100000000000000000000000000000000000000000000000000000000"
    "00000020000000000000000000000000396d31055db28c0c6f36e8b36f18fe72"
    "27248a9711111111111111111111111111111111111111111111111111111111"
    "1111111100000000000000000000000000000000000000000000000000000000"
    "0000006000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000100000000000000000000000000000000000000000000000000000000"
    "0000002000000000000000000000000000000000000000000000000000000000"
    "0000000100000000000000000000000000000000000000000000000000000000"
    "00000020fff16d60be267153303bbfa66e593fb8d06e24ea5ef24b6acca5224c"
    "2ca6b90700000000000000000000000000000000000000000000000000000000"
    "0000000100000000000000000000000000000000000000000000000000000000"
    "00000060000000000000000000000000fc81d1b5841e697973af3072fc8e03af"
    "76cb39ef00000000000000000000000000000000000000000000000000000000"
    "0000008000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0001518000000000000000000000000000000000000000000000000000000000"
    "00000040000000000000000000000000c91d87e81fab8f93699ecf7ee9b44d11"
    "e1d53f0f00000000000000000000000000000000000000000000000000000000"
    "00000001"
)


def test_create_deposit_is_byte_identical_to_the_reference_sdk():
    """Parity guard. #16 was two words: intentGatingService and retainOnEmpty."""
    data = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
        intent_min=1_000_000,
        intent_max=100_000_000,
    )
    raw = decode_hex(data)
    suffix = erc8021_suffix(lock_attribution())
    assert raw.endswith(suffix)
    assert raw[: -len(suffix)].hex() == REFERENCE_CREATE_DEPOSIT
