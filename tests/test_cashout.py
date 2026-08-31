
import httpx
import pytest
import respx
from eth_abi import decode
from eth_utils import decode_hex

from usdctofiat import ModeRequired, SignerRequired, ValidationError, cashout, create_offramp
from usdctofiat.attribution import parse_erc8021
from usdctofiat.calldata import CREATE_DEPOSIT_TUPLE
from usdctofiat.constants import (
    CHAIN_ID,
    CURATOR_URL,
    ERC8021_MARKER,
    ESCROW_V2,
    INTENT_GUARDIAN,
    MAKERS_CREATE_PATH,
    USDC,
    ZERO_ADDRESS,
)


def test_mode_required(mocked_http):
    with pytest.raises(ModeRequired):
        create_offramp().prepare(amount="100", currency="EUR", platform="revolut", payee="alice")
    with pytest.raises(ModeRequired):
        create_offramp().prepare(mode="slow", amount="100", currency="EUR", platform="revolut", payee="alice")


def test_cashout_without_signer_does_not_take_a_key(mocked_http):
    with pytest.raises(SignerRequired):
        cashout(mode="fast", amount="100", currency="EUR", platform="revolut", payee="alice")
    with pytest.raises(TypeError):
        create_offramp(private_key="0xabc")  # type: ignore[call-arg]
    # constructor ignores unknown key-like kwargs rather than storing them
    client = create_offramp()
    assert not hasattr(client, "private_key")
    assert not hasattr(client, "key")


def test_fast_prepare_path_mocked(mocked_http):
    prepared = create_offramp().prepare(
        mode="fast",
        amount="100",
        currency="EUR",
        platform="revolut",
        payee="alice",
    )
    assert prepared.mode == "fast"
    assert prepared.steps == ["approve", "createDeposit"]
    assert prepared.delegate_hook is None
    assert prepared.amount_units == 100_000_000
    assert prepared.payee_details_hash.startswith("0x11")
    assert len(prepared.txs) == 2
    assert prepared.txs[0].to.lower() == USDC.lower()
    assert prepared.txs[1].to.lower() == ESCROW_V2.lower()
    assert prepared.txs[0].chain_id == CHAIN_ID
    assert prepared.txs[0].value == 0
    for tx in prepared.txs:
        assert parse_erc8021(tx.data)[:2] == ("peer-ref-TOFIAT", "galleonlabs")
    # curator was hit; cashout HTTP was not
    calls = [str(c.request.url) for c in mocked_http.calls]
    assert any("/v2/makers/create" in u for u in calls)
    assert all("/cashout" not in u for u in calls)


@pytest.mark.parametrize("mode", ["fast", "best"])
def test_prepare_inherits_protocol_intent_guardian(mocked_http, mode):
    prepared = create_offramp().prepare(
        mode=mode,
        amount="100",
        currency="EUR",
        platform="revolut",
        payee="alice",
    )
    raw = decode_hex(prepared.txs[1].data)
    payload = raw[4 : raw.rfind(ERC8021_MARKER)]
    guardian = decode([CREATE_DEPOSIT_TUPLE], payload)[0][7]
    assert guardian.lower() == INTENT_GUARDIAN.lower()
    assert guardian.lower() != ZERO_ADDRESS.lower()


def test_best_is_same_deposit_plus_delegate_hook(mocked_http):
    prepared = create_offramp().prepare(
        mode="best",
        amount="25",
        currency="USD",
        platform="venmo",
        payee="@alice",
    )
    assert prepared.mode == "best"
    assert prepared.steps == ["approve", "createDeposit", "setRateManager"]
    assert len(prepared.txs) == 2  # setRateManager waits for deposit_id
    assert prepared.delegate_hook is not None
    assert prepared.delegate_hook.fee_bps == 10
    assert prepared.delegate_hook.step == "setRateManager"
    assert prepared.delegate_hook.to.lower() == ESCROW_V2.lower()
    assert prepared.access_policy_required is True


def test_cashout_signer_callback(mocked_http):
    seen = []

    def signer(tx):
        seen.append(tx)
        return {"hash": f"0x{'ab' * 32}", "deposit_id": "42"}

    result = cashout(
        mode="fast",
        amount="10",
        currency="GBP",
        platform="monzo",
        payee="alice",
        signer=signer,
    )
    assert result.mode == "fast"
    assert result.deposit_id == "42"
    assert result.tx_hash.startswith("0xab")
    assert len(seen) == 2
    assert result.delegate_hook is None


def test_curator_only_makers_create(mocked_http, makers_fixture):
    route = mocked_http.routes[0]
    assert str(route.pattern).endswith(MAKERS_CREATE_PATH) or MAKERS_CREATE_PATH in str(route.pattern)
    create_offramp().prepare(mode="fast", amount="10", currency="EUR", platform="revolut", payee="alice")
    request = mocked_http.calls[0].request
    assert request.method == "POST"
    assert str(request.url) == f"{CURATOR_URL}{MAKERS_CREATE_PATH}"
    assert b"alice" in request.content
    assert b"revolut" in request.content


def test_cashout_keeps_tx_hash_from_a_web3_receipt(mocked_http):
    """A real web3.py receipt keys the hash transactionHash, not hash/tx_hash."""
    from usdctofiat.calldata import DEPOSIT_RECEIVED_TOPIC

    class HexBytes(bytes):  # web3.py's type, minus the dependency
        def __repr__(self) -> str:
            return f"HexBytes('0x{self.hex()}')"

        __str__ = __repr__

    def signer(tx):
        return {
            "transactionHash": HexBytes(bytes.fromhex("ab" * 32)),
            "status": 1,
            "logs": [
                {
                    "topics": [
                        HexBytes(bytes.fromhex(DEPOSIT_RECEIVED_TOPIC[2:])),
                        HexBytes((7).to_bytes(32, "big")),
                    ]
                }
            ],
        }

    result = create_offramp().cashout(
        mode="fast",
        amount="10",
        currency="EUR",
        platform="revolut",
        payee="alice",
        signer=signer,
    )
    assert result.deposit_id == "7"
    assert result.tx_hash == "0x" + "ab" * 32
    assert result.tx_hashes == ["0x" + "ab" * 32] * 2
    assert "HexBytes" not in result.as_dict()["tx_hash"]


def test_withdraw_accepts_the_same_signer_returns_as_cashout(mocked_http):
    expected = "0x" + "cd" * 32
    for result in (expected, {"txHash": expected}, {"transactionHash": bytes.fromhex("cd" * 32)}):
        closed = create_offramp().withdraw(7, signer=lambda tx, r=result: r)
        assert closed.tx_hash == expected
        assert closed.tx_hashes == [expected]
        assert closed.deposit_id == "7"


def test_an_unsupported_platform_raises_before_the_curator_is_posted():
    """The curator answers an unknown processor with a 400 `unsupported_processor_*`
    envelope, so posting first replaced this client's own ValidationError -- the
    one that names the nine supported platforms -- with a CuratorError."""
    with respx.mock(assert_all_called=False) as router:
        route = router.post(f"{CURATOR_URL}{MAKERS_CREATE_PATH}").mock(
            return_value=httpx.Response(
                400,
                json={
                    "success": False,
                    "message": "Unsupported processor: skrill",
                    "responseObject": None,
                    "statusCode": 400,
                    "errorCode": "unsupported_processor_skrill",
                },
            )
        )
        with pytest.raises(ValidationError) as excinfo:
            create_offramp().prepare(
                mode="fast", amount="100", currency="EUR", platform="skrill", payee="alice"
            )
    assert excinfo.value.field == "platform"
    assert route.call_count == 0


def test_an_unsupported_currency_raises_before_a_maker_record_is_minted(mocked_http):
    """A currency with no Base feed can never be encoded, so hashing the payee
    first only creates a curator maker record for a cash-out that cannot run."""
    route = mocked_http.post(f"{CURATOR_URL}{MAKERS_CREATE_PATH}")
    with pytest.raises(ValidationError) as excinfo:
        create_offramp().prepare(
            mode="fast", amount="100", currency="JPY", platform="revolut", payee="alice"
        )
    assert excinfo.value.field == "currency"
    assert route.call_count == 0


def test_cashout_rejects_bad_inputs_without_touching_the_curator_or_the_signer(mocked_http):
    route = mocked_http.post(f"{CURATOR_URL}{MAKERS_CREATE_PATH}")

    def signer(tx):  # pragma: no cover - the point is that it never runs
        raise AssertionError("signer called for an input the client can reject locally")

    for bad in ({"platform": "skrill"}, {"currency": "JPY"}):
        kwargs = {"platform": "revolut", "currency": "EUR", **bad}
        with pytest.raises(ValidationError):
            create_offramp().cashout(
                mode="fast", amount="100", payee="alice", signer=signer, **kwargs
            )
    assert route.call_count == 0
