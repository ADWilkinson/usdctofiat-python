"""Mocked tests for the local Dify sideload plugin draft.

This is an own-repo sideload shape. Do not open langgenius/dify-plugins.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usdctofiat import ModeRequired
from usdctofiat.types import Estimate, PreparedCashout, UnsignedTx
from _client import offramp_from
from provider.usdctofiat import UsdctoFiatProvider
from tools.cashout import UsdctoFiatCashoutTool
from tools.deposits import UsdctoFiatDepositsTool
from tools.estimate import UsdctoFiatEstimateTool
from tools.watch import UsdctoFiatWatchTool
from tools.withdraw import UsdctoFiatWithdrawTool

ROOT = Path(__file__).resolve().parents[1]


def _prepared(mode: str = "fast") -> PreparedCashout:
    return PreparedCashout(
        mode=mode,  # type: ignore[arg-type]
        txs=[
            UnsignedTx(to="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", data="0x095ea7b3"),
            UnsignedTx(to="0x777777779d229cdF3110e9de47943791c26300Ef", data="0xcreate"),
        ],
        steps=["approve", "createDeposit"],
        payee_details_hash="0x11" + "ab" * 31,
        amount_units=100_000_000,
        platform="revolut",
        currency="EUR",
        attribution={"referral_code": "TOFIAT", "referrers": ["galleonlabs"]},
    )


@pytest.fixture
def mock_offramp():
    client = MagicMock()
    client.prepare.return_value = _prepared("fast")
    client.estimate.return_value = Estimate(
        mode="fast",
        amount_units=100_000_000,
        currency="EUR",
        rate="1",
        receive_amount="100",
        spread_bps=0,
        manager_fee_bps=0,
    )
    client.deposits.return_value = [{"id": "42", "status": "ACTIVE"}]
    client.watch.return_value = iter([{"id": "42", "status": "ACTIVE"}])
    client.withdraw.return_value = UnsignedTx(
        to="0x777777779d229cdF3110e9de47943791c26300Ef",
        data="0xwithdraw",
    )
    return client


def _first(tool, params):
    return next(tool._invoke(params)).payload


def test_manifest_is_sideload_and_branded():
    text = (ROOT / "manifest.yaml").read_text()
    lowered = text.lower()
    assert "author: adwilkinson" in lowered
    assert "usdctofiat" in lowered
    assert "galleon" in lowered
    assert "not a peer cash product" in lowered
    assert "mode is required" in lowered
    assert "no private keys" in lowered or "no private key" in lowered
    assert "langgenius" not in lowered


def test_readme_forbids_marketplace_pr():
    text = (ROOT / "README.md").read_text().lower()
    assert "do **not** open a pr against" in text or "do not open a pr against" in text
    assert "langgenius/dify-plugins" in text
    assert "mode is required" in text
    assert "no private" in text
    assert "sideload" in text


def test_no_private_key_credentials():
    UsdctoFiatProvider()._validate_credentials({})
    with pytest.raises(ValueError, match="does not accept a private key"):
        UsdctoFiatProvider()._validate_credentials({"private_key": "0xabc"})
    with pytest.raises(TypeError, match="does not accept a private key"):
        offramp_from({"private_key": "0xabc"})


def test_cashout_yaml_mode_required_select():
    text = (ROOT / "tools" / "cashout.yaml").read_text()
    assert "name: mode" in text
    assert "required: true" in text
    assert "type: select" in text
    assert "value: fast" in text
    assert "value: best" in text
    assert "default:" not in text.split("name: mode", 1)[1].split("- name:", 1)[0]


def test_cashout_returns_unsigned_prepare(mock_offramp):
    with patch("_client.create_offramp", return_value=mock_offramp):
        payload = _first(
            UsdctoFiatCashoutTool(),
            {"mode": "fast", "amount": "100", "currency": "EUR", "platform": "revolut", "payee": "alice"},
        )
    assert payload["signed"] is False
    assert payload["prepared"]["mode"] == "fast"
    assert payload["prepared"]["attribution"]["referral_code"] == "TOFIAT"
    mock_offramp.prepare.assert_called_once()
    mock_offramp.cashout.assert_not_called()


def test_cashout_mode_required(mock_offramp):
    mock_offramp.prepare.side_effect = ModeRequired()
    with patch("_client.create_offramp", return_value=mock_offramp):
        payload = _first(
            UsdctoFiatCashoutTool(),
            {"mode": "", "amount": "100", "currency": "EUR", "platform": "revolut", "payee": "alice"},
        )
    assert "mode is required" in payload["error"]


def test_estimate_watch_withdraw_deposits(mock_offramp):
    with patch("_client.create_offramp", return_value=mock_offramp):
        estimate = _first(UsdctoFiatEstimateTool(), {"mode": "fast", "amount": "100", "currency": "EUR"})
        watched = _first(UsdctoFiatWatchTool(), {"deposit_id": "42"})
        withdrawn = _first(UsdctoFiatWithdrawTool(), {"deposit_id": "42"})
        rows = _first(UsdctoFiatDepositsTool(), {"owner": "0x1111111111111111111111111111111111111111"})
    assert estimate["spread_bps"] == 0
    assert estimate["mode"] == "fast"
    assert watched["snapshots"][0]["status"] == "ACTIVE"
    assert withdrawn["data"] == "0xwithdraw"
    assert rows["deposits"][0]["id"] == "42"


def test_no_peer_cash_branding_in_plugin_tree():
    skip = {"tests"}
    for path in ROOT.rglob("*"):
        if "tests" in path.parts:
            continue
        if path.suffix in {".py", ".yaml", ".md", ".txt"} and path.is_file():
            text = path.read_text().lower()
            assert "peer-cash" not in text
            assert "plugin-peer-cash" not in text
