"""A payment method only settles the currencies its verifier is registered for.

The client validated the platform and the currency separately, which passes
every unsupported *pair*: venmo/EUR, monzo/USD, revolut/PHP all encoded cleanly
and reverted onchain. EscrowV2 asks PaymentVerifierRegistry and answers
CurrencyNotSupported(paymentMethod, currency) — after approve is signed and the
payee is posted to the curator, so the caller pays gas and mints a maker record
for a deposit that cannot exist.
"""

import pytest

from usdctofiat import create_offramp
from usdctofiat.calldata import (
    assert_supported_pair,
    encode_create_deposit,
    supported_currencies,
)
from usdctofiat.constants import (
    CHAINLINK_ORACLE_FEEDS,
    PAYMENT_METHOD_CURRENCIES,
    PAYMENT_METHOD_HASHES,
)
from usdctofiat.errors import ValidationError

DIGEST = "0x" + "11" * 32

# eth_call EscrowV2.createDeposit on Base, 1 USDC, from an address holding
# nothing: a registered pair gets past the currency check and reverts
# Error(string) (0x08c379a0) on the USDC pull, an unregistered one reverts
# CurrencyNotSupported (0xd76cc8fa) with the payment method hash as its first
# word. Both revert; only the reason distinguishes them.
SETTLES = [("venmo", "USD"), ("revolut", "EUR"), ("monzo", "GBP"), ("paypal", "SGD")]
REVERTS = [
    ("venmo", "EUR"),
    ("cashapp", "GBP"),
    ("revolut", "PHP"),
    ("wise", "BRL"),
    ("monzo", "EUR"),
    ("paypal", "TRY"),
    ("zelle", "MXN"),
    ("chime", "CAD"),
]


@pytest.mark.parametrize("platform,currency", SETTLES)
def test_registered_pairs_still_encode(platform, currency):
    data = encode_create_deposit(
        amount_units=1_000_000, payee_details_hash=DIGEST, platform=platform, currency=currency
    )
    assert data.startswith("0x")


@pytest.mark.parametrize("platform,currency", REVERTS)
def test_unregistered_pair_cannot_be_encoded(platform, currency):
    with pytest.raises(ValidationError) as exc:
        encode_create_deposit(
            amount_units=1_000_000, payee_details_hash=DIGEST, platform=platform, currency=currency
        )
    assert exc.value.field == "currency"
    assert currency in str(exc.value)


def test_prepare_rejects_the_pair_before_the_curator_post(mocked_http):
    """#27 moved the platform and currency checks ahead of the POST; the pair
    belongs with them. A maker record for a deposit that cannot settle is waste."""
    client = create_offramp()
    with pytest.raises(ValidationError):
        client.prepare(mode="fast", amount="100", currency="EUR", platform="venmo", payee="alice")
    assert not mocked_http.calls


def test_mercadopago_names_itself_rather_than_the_currency():
    """Its only registered currency is ARS, which has no Base feed. Blaming the
    currency would send the caller looking for a code that does not exist."""
    assert supported_currencies("mercadopago") == []
    with pytest.raises(ValidationError) as exc:
        assert_supported_pair("mercadopago", "USD")
    assert exc.value.field == "platform"
    assert "ARS" in str(exc.value)


def test_supported_currencies_is_the_registry_set_intersected_with_the_feeds():
    """revolut settles CNY with no Base feed; BRL has a feed no method carries.
    Neither can be quoted or deposited, and neither may be advertised."""
    assert "CNY" in PAYMENT_METHOD_CURRENCIES["revolut"]
    assert "CNY" not in supported_currencies("revolut")
    assert "BRL" in CHAINLINK_ORACLE_FEEDS
    assert not any("BRL" in codes for codes in PAYMENT_METHOD_CURRENCIES.values())


def test_every_known_platform_has_a_registry_row():
    """A platform this client can hash but has no pair set for would skip the
    check entirely and go back to encoding reverting calldata."""
    assert set(PAYMENT_METHOD_CURRENCIES) == set(PAYMENT_METHOD_HASHES)


def test_unknown_platform_still_fails_on_the_platform():
    with pytest.raises(ValidationError) as exc:
        encode_create_deposit(
            amount_units=1_000_000, payee_details_hash=DIGEST, platform="nope", currency="USD"
        )
    assert exc.value.field == "platform"
