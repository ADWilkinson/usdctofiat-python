
import httpx
import pytest
import respx

from usdctofiat import ModeRequired, SignerRequired, cashout, create_offramp
from usdctofiat.attribution import parse_erc8021
from usdctofiat.constants import CHAIN_ID, CURATOR_URL, ESCROW_V2, MAKERS_CREATE_PATH, USDC


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
