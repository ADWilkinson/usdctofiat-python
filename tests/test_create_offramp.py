
import json

from usdctofiat import create_offramp
from usdctofiat.constants import (
    BEST_MANAGER_FEE_BPS,
    CHAIN_ID,
    ESCROW_V2,
    FAST_SPREAD_BPS,
    INDEXER_URL,
)


def test_estimate_fast_zero_spread_best_ten_bps():
    client = create_offramp()
    fast = client.estimate(mode="fast", amount="100", currency="EUR")
    best = client.estimate(mode="best", amount="100", currency="EUR")
    assert fast.spread_bps == FAST_SPREAD_BPS == 0
    assert fast.manager_fee_bps == 0
    assert best.manager_fee_bps == BEST_MANAGER_FEE_BPS == 10
    assert fast.kind == "oracle-estimate"
    assert "not a locked quote" in fast.note.lower()


def test_watch_withdraw_deposits(mocked_http):
    client = create_offramp()
    owner = " 0x11111111111111111111111111111111111111Aa "
    rows = client.deposits(owner)
    assert rows[0]["id"].endswith("_42")
    watched = list(client.watch("42"))
    assert watched[0]["status"] == "ACTIVE"
    tx = client.withdraw(42)
    assert tx.to.lower().endswith("ef")
    assert tx.data.startswith("0x")

    indexer_calls = [call for call in mocked_http.calls if str(call.request.url) == INDEXER_URL]
    list_request = json.loads(indexer_calls[0].request.content)
    assert "Deposit(" in list_request["query"]
    assert "deposits(" not in list_request["query"]
    assert "depositor: { _ilike: $depositor }" in list_request["query"]
    assert "chainId: { _eq: $chainId }" in list_request["query"]
    assert "escrowAddress: { _eq: $escrowAddress }" in list_request["query"]
    assert list_request["variables"] == {
        "depositor": owner.strip(),
        "escrowAddress": ESCROW_V2.lower(),
        "chainId": CHAIN_ID,
    }

    watch_request = json.loads(indexer_calls[1].request.content)
    assert "$depositId: numeric!" in watch_request["query"]
    assert "depositId: { _eq: $depositId }" in watch_request["query"]
    assert "escrowAddress: { _eq: $escrowAddress }" in watch_request["query"]
    assert watch_request["variables"] == {
        "depositId": "42",
        "escrowAddress": ESCROW_V2.lower(),
        "chainId": CHAIN_ID,
    }


def test_deposits_are_scoped_to_escrow_v2(mocked_http):
    """The indexer serves several Base escrows, and this client only drives EscrowV2.

    Without the escrowAddress filter an owner's list is dominated by deposits
    withdraw() cannot touch: live, one depositor returned 35 rows across three
    escrows, only 9 of them EscrowV2.
    """
    client = create_offramp()
    rows = client.deposits("0x1111111111111111111111111111111111111111")
    assert {row["escrowAddress"] for row in rows} == {ESCROW_V2.lower()}

    list_request = json.loads(
        [call for call in mocked_http.calls if str(call.request.url) == INDEXER_URL][0].request.content
    )
    assert list_request["variables"]["escrowAddress"] == ESCROW_V2.lower()


def test_deposits_rows_carry_an_id_watch_and_withdraw_accept(mocked_http):
    """deposits() -> watch()/close() has to compose.

    The row's `id` is the indexer's composite "<escrow>_<depositId>" key: watch()
    binds it to $depositId: numeric! and gets an empty set back, and withdraw()
    raises ValueError from int(). Rows carry the onchain depositId for that reason.
    """
    client = create_offramp()
    row = client.deposits("0x1111111111111111111111111111111111111111")[0]
    assert row["id"] == f"{row['escrowAddress']}_{row['depositId']}"

    assert list(client.watch(row["depositId"]))[0]["status"] == "ACTIVE"
    assert client.close(row["depositId"]).data.startswith("0x")

    # respx replays the fixture whatever is asked for, so pin the selection set
    # too: dropping depositId from the query would strand every caller again.
    list_query = json.loads(
        [call for call in mocked_http.calls if str(call.request.url) == INDEXER_URL][0].request.content
    )["query"]
    assert "depositId" in list_query
    assert "escrowAddress" in list_query


def test_branding_is_usdctofiat_not_peer_cash():
    import usdctofiat
    import usdctofiat as pkg

    assert pkg.PRODUCT == "USDCtoFiat"
    assert pkg.VENDOR == "Galleon Labs"
    text = pkg.__doc__.lower()
    assert "usdctofiat" in text
    assert "not a peer cash product" in text
    assert "peer-cash" not in pkg.__name__
