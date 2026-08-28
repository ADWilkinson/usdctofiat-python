
from eth_abi import decode
from eth_utils import decode_hex

from usdctofiat.attribution import parse_erc8021
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
    DEFAULT_ORACLE_MAX_STALENESS,
    ERC8021_MARKER,
    ESCROW_V2,
    FAST_SPREAD_BPS,
    INTENT_GUARDIAN,
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


def test_approve_and_create_deposit_selectors_and_lock():
    approve = encode_approve(100_000_000)
    assert decode_hex(approve)[:4] == APPROVE_SELECTOR
    assert USDC[2:].lower() not in approve[10:74]  # spender is escrow
    # spender is EscrowV2
    assert ESCROW_V2[2:].lower() in approve.lower()
    assert parse_erc8021(approve)[:2] == ("peer-ref-TOFIAT", "galleonlabs")

    data = encode_create_deposit(
        amount_units=100_000_000,
        payee_details_hash=PAYEE,
        platform="revolut",
        currency="EUR",
    )
    raw = decode_hex(data)
    assert raw[:4] == CREATE_DEPOSIT_SELECTOR
    assert USDC[2:].lower() in data.lower()
    assert parse_erc8021(data)[:2] == ("peer-ref-TOFIAT", "galleonlabs")


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


def test_create_deposit_attaches_the_chainlink_feed_for_every_currency():
    """Non-USD deposits were encoded with no oracle at a fixed 1.0 fiat per USDC. (#11)"""
    for currency in ("EUR", "GBP", "MXN", "AUD", "ZAR"):
        feed, invert = CHAINLINK_ORACLE_FEEDS[currency]
        _, _, oracle = _currency_row(_deposit_for(currency))
        adapter, adapter_config, spread_bps, max_staleness = oracle
        assert adapter.lower() == CHAINLINK_ORACLE_ADAPTER.lower()
        assert _decode_adapter_config(adapter_config) == (feed.lower(), invert)
        assert invert is True
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
    assert parse_erc8021(rm)[0] == "peer-ref-TOFIAT"


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
