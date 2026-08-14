
from eth_utils import decode_hex

from usdctofiat.attribution import parse_erc8021
from usdctofiat.calldata import (
    APPROVE_SELECTOR,
    CREATE_DEPOSIT_SELECTOR,
    SET_RATE_MANAGER_SELECTOR,
    WITHDRAW_SELECTOR,
    encode_approve,
    encode_create_deposit,
    encode_set_rate_manager,
    encode_withdraw,
    extract_deposit_id,
    normalize_payee,
    parse_usdc_amount,
)
from usdctofiat.constants import ESCROW_V2, RATE_MANAGER_V1, USDC
from usdctofiat.errors import ValidationError


PAYEE = "0x1111111111111111111111111111111111111111111111111111111111111111"


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
