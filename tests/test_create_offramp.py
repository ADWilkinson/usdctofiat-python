
from usdctofiat import create_offramp
from usdctofiat.constants import BEST_MANAGER_FEE_BPS, FAST_SPREAD_BPS


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
    rows = client.deposits("0x1111111111111111111111111111111111111111")
    assert rows[0]["id"] == "42"
    watched = list(client.watch("42"))
    assert watched[0]["status"] == "ACTIVE"
    tx = client.withdraw(42)
    assert tx.to.lower().endswith("ef")
    assert tx.data.startswith("0x")


def test_branding_is_usdctofiat_not_peer_cash():
    import usdctofiat
    import usdctofiat as pkg

    assert pkg.PRODUCT == "USDCtoFiat"
    assert pkg.VENDOR == "Galleon Labs"
    text = pkg.__doc__.lower()
    assert "usdctofiat" in text
    assert "not a peer cash product" in text
    assert "peer-cash" not in pkg.__name__
