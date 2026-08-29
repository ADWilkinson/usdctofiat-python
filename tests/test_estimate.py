
import time
from decimal import Decimal

import httpx
import pytest
import respx

from usdctofiat import OracleError, ValidationError, create_offramp
from usdctofiat.constants import BASE_RPC_URL, CHAINLINK_ORACLE_FEEDS, ZERO_ADDRESS
from usdctofiat.oracle import LATEST_ROUND_DATA_SELECTOR, Oracle

# Base mainnet reads taken 2026-08-29: EUR/USD 1.158215, TRY/USD 0.02073014.
EUR_ANSWER = 115_821_500
TRY_ANSWER = 2_073_014


def rpc_calls(router, url: str = BASE_RPC_URL):
    """httpx normalises a bare origin with a trailing slash."""
    return [call for call in router.calls if str(call.request.url).rstrip("/") == url.rstrip("/")]


def rpc_route(router, round_data, answer: int, updated_at: int | None = None, url: str = BASE_RPC_URL):
    stamp = updated_at if updated_at is not None else int(time.time())
    return router.post(url).mock(
        return_value=httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": round_data(answer, stamp)},
        )
    )


def test_estimate_prices_off_the_currency_feed_not_a_fixed_rate(mocked_http):
    """1 USDC is 0.8634 EUR, not 1 EUR. The feed is quoted USD per EUR and inverts."""
    estimate = create_offramp().estimate(mode="fast", amount="100", currency="EUR")
    assert estimate.rate != "1"
    assert estimate.rate == "0.863398"  # 1 / 1.158215, shown to six places
    # Priced off the full-precision rate, not the rounded display value.
    assert estimate.receive_amount == "86.339756"
    assert estimate.currency == "EUR"
    assert estimate.amount_units == 100_000_000

    call = rpc_calls(mocked_http)[-1].request
    body = call.read()
    assert LATEST_ROUND_DATA_SELECTOR.encode() in body
    assert CHAINLINK_ORACLE_FEEDS["EUR"][0].encode() in body


def test_estimate_scales_a_far_from_parity_currency(mocked_http, round_data):
    """TRY was quoted 1:1, a 48x understatement of what a seller receives."""
    rpc_route(mocked_http, round_data, TRY_ANSWER)
    estimate = create_offramp().estimate(mode="fast", amount="100", currency="TRY")
    assert estimate.rate == "48.238941"
    assert estimate.receive_amount == "4823.894098"
    assert Decimal(estimate.receive_amount) > 4000


def test_usd_is_the_passthrough_and_reads_no_feed(mocked_http):
    before = len(rpc_calls(mocked_http))
    estimate = create_offramp().estimate(mode="fast", amount="250.5", currency="USD")
    assert estimate.rate == "1"
    assert estimate.receive_amount == "250.5"
    assert estimate.oracle_updated_at is None
    assert estimate.stale is False
    assert CHAINLINK_ORACLE_FEEDS["USD"][0] == ZERO_ADDRESS
    assert len(rpc_calls(mocked_http)) == before


def test_estimate_rejects_a_currency_with_no_feed(mocked_http):
    """prepare() already raises for these; README says estimate must too."""
    with pytest.raises(ValidationError) as excinfo:
        create_offramp().estimate(mode="fast", amount="100", currency="JPY")
    assert excinfo.value.field == "currency"
    assert "JPY" in str(excinfo.value)


def test_estimate_flags_a_stale_feed(mocked_http, round_data):
    day_and_a_half_ago = int(time.time()) - 129_600
    rpc_route(mocked_http, round_data, EUR_ANSWER, day_and_a_half_ago)
    estimate = create_offramp().estimate(mode="fast", amount="100", currency="EUR")
    assert estimate.stale is True
    assert estimate.oracle_updated_at == day_and_a_half_ago
    assert estimate.as_of >= day_and_a_half_ago
    assert estimate.as_dict()["stale"] is True


def test_estimate_keeps_the_mode_fee_shape(mocked_http):
    client = create_offramp()
    fast = client.estimate(mode="fast", amount="100", currency="EUR")
    best = client.estimate(mode="best", amount="100", currency="EUR")
    assert fast.manager_fee_bps == 0
    assert best.manager_fee_bps == 10
    assert fast.spread_bps == best.spread_bps == 0
    # The manager fee is taken from released USDC, so it does not move the fiat estimate.
    assert fast.receive_amount == best.receive_amount


def test_oracle_failure_raises_rather_than_falling_back_to_one():
    """A silent 1:1 fallback is the bug. Surface the failure instead."""
    with respx.mock(assert_all_called=False) as router:
        router.post(BASE_RPC_URL).mock(return_value=httpx.Response(503, text="upstream down"))
        with pytest.raises(OracleError):
            create_offramp().estimate(mode="fast", amount="100", currency="EUR")

    with respx.mock(assert_all_called=False) as router:
        router.post(BASE_RPC_URL).mock(
            return_value=httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32000}})
        )
        with pytest.raises(OracleError):
            create_offramp().estimate(mode="fast", amount="100", currency="EUR")


def test_a_non_positive_answer_is_not_priced(round_data):
    with respx.mock(assert_all_called=False) as router:
        rpc_route(router, round_data, 0)
        with pytest.raises(OracleError):
            Oracle().rate("EUR")


def test_oracle_endpoint_is_injectable(round_data):
    with respx.mock(assert_all_called=False) as router:
        route = rpc_route(router, round_data, EUR_ANSWER, url="https://base.example/rpc")
        estimate = create_offramp(rpc_url="https://base.example/rpc").estimate(
            mode="fast", amount="1", currency="EUR"
        )
        assert route.called
        assert estimate.rate == "0.863398"


def test_every_supported_currency_carries_a_feed_and_decimals():
    for code, (feed, invert, decimals) in CHAINLINK_ORACLE_FEEDS.items():
        assert feed == feed.lower()
        if code == "USD":
            assert (feed, invert, decimals) == (ZERO_ADDRESS, False, 0)
        else:
            assert feed != ZERO_ADDRESS
            assert invert is True  # every Base FX feed is quoted USD per unit of fiat
            assert decimals == 8
