
"""POST /v2/makers/create request and response shape.

The bodies here are the live curator contract: `offchainId` is a top-level
field, and every answer arrives in a
`{success, message, responseObject, statusCode, errorCode}` envelope with the
digest at `responseObject.hashedOnchainId`. Nesting the identifier under
`payeeData` is rejected as `invalid_maker_data`, so `prepare()` could not hash a
payee at all.
"""

import json

import httpx
import pytest
import respx

from usdctofiat import CuratorError, create_offramp
from usdctofiat.constants import CURATOR_URL, MAKERS_CREATE_PATH
from usdctofiat.curator import Curator

MAKERS_URL = f"{CURATOR_URL}{MAKERS_CREATE_PATH}"
HASH = "0x2222222222222222222222222222222222222222222222222222222222222222"


def envelope(response_object, *, success: bool = True, message: str = "Maker created") -> dict:
    return {
        "success": success,
        "message": message,
        "responseObject": response_object,
        "statusCode": 200 if success else 400,
        "errorCode": None if success else "invalid_maker_data",
    }


def test_offchain_id_is_posted_flat_not_nested_under_payee_data():
    with respx.mock(assert_all_called=True) as router:
        route = router.post(MAKERS_URL).mock(
            return_value=httpx.Response(200, json=envelope({"hashedOnchainId": HASH}))
        )
        digest = Curator().create_payee_hash(platform="revolut", payee="alice")

    body = json.loads(route.calls[-1].request.read())
    assert body == {"processorName": "revolut", "offchainId": "alice"}
    assert "payeeData" not in body  # the curator never sees a nested identifier
    assert digest == HASH


def test_the_hash_is_read_from_the_response_envelope():
    with respx.mock(assert_all_called=True) as router:
        router.post(MAKERS_URL).mock(
            return_value=httpx.Response(200, json=envelope({"hashedOnchainId": HASH, "processorName": "revolut"}))
        )
        assert Curator().create_payee_hash(platform="revolut", payee="alice") == HASH


def test_success_false_on_a_200_is_still_a_failure():
    with respx.mock(assert_all_called=True) as router:
        router.post(MAKERS_URL).mock(
            return_value=httpx.Response(200, json=envelope(None, success=False, message="Invalid maker data"))
        )
        with pytest.raises(CuratorError) as excinfo:
            Curator().create_payee_hash(platform="revolut", payee="alice")
    assert "Invalid maker data" in str(excinfo.value)


def test_a_value_that_is_not_a_32_byte_hash_is_refused():
    """A placeholder would otherwise be encoded into createDeposit calldata."""
    for value in ("pending", "0x1234", HASH + "ff"):
        with respx.mock(assert_all_called=True) as router:
            router.post(MAKERS_URL).mock(
                return_value=httpx.Response(200, json=envelope({"hashedOnchainId": value}))
            )
            with pytest.raises(CuratorError):
                Curator().create_payee_hash(platform="revolut", payee="alice")


def test_a_top_level_payee_details_hash_still_parses():
    """Older curator answers put the digest at the top level. Keep reading them."""
    with respx.mock(assert_all_called=True) as router:
        router.post(MAKERS_URL).mock(return_value=httpx.Response(200, json={"payeeDetailsHash": HASH}))
        assert Curator().create_payee_hash(platform="revolut", payee="alice") == HASH


def test_prepare_sends_the_normalised_payee_as_offchain_id(mocked_http):
    """prepare() hashes the platform-normalised handle, not the raw input."""
    prepared = create_offramp().prepare(
        mode="fast", amount="100", currency="EUR", platform="Revolut", payee="@Alice"
    )
    body = json.loads(mocked_http.calls[0].request.read())
    assert body == {"processorName": "revolut", "offchainId": "Alice"}
    assert prepared.payee_details_hash.startswith("0x11")
