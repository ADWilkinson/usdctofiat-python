"""Mocked tests for the local lfx-usdctofiat pip-extension draft.

Do not open langflow-ai/langflow. Do not publish to PyPI from this tree.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usdctofiat import ModeRequired
from usdctofiat.types import Estimate, PreparedCashout, UnsignedTx
from lfx_usdctofiat.components.usdctofiat.cashout import UsdctoFiatCashoutComponent
from lfx_usdctofiat.components.usdctofiat.deposits import UsdctoFiatDepositsComponent
from lfx_usdctofiat.components.usdctofiat.estimate import UsdctoFiatEstimateComponent
from lfx_usdctofiat.components.usdctofiat.watch import UsdctoFiatWatchComponent
from lfx_usdctofiat.components.usdctofiat.withdraw import UsdctoFiatWithdrawComponent

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


def test_extension_manifest_is_lfx_usdctofiat():
    data = json.loads((ROOT / "extension.json").read_text())
    assert data["id"] == "lfx-usdctofiat"
    assert data["lfx"]["compat"] == ["1"]
    assert data["bundles"] == [{"name": "usdctofiat", "path": "components/usdctofiat"}]
    assert data["capabilities"]["requiresCredentials"] is False
    lowered = data["description"].lower()
    assert "galleon" in lowered
    assert "not a peer cash product" in lowered
    assert "mode is required" in lowered
    assert "no private keys" in lowered
    assert "do not open langflow-ai/langflow" in lowered


def test_readme_forbids_host_pr_and_pypi():
    text = (ROOT / "README.md").read_text().lower()
    assert "do **not** open a pr against" in text or "do not open a pr against" in text
    assert "langflow-ai/langflow" in text
    assert "no pypi" in text
    assert "mode is required" in text
    assert "no private" in text
    assert "lfx-usdctofiat" in text


def test_cashout_has_required_mode_and_no_key_input():
    names = [item["name"] if isinstance(item, dict) else getattr(item, "name", None) for item in UsdctoFiatCashoutComponent.inputs]
    assert "mode" in names
    assert "private_key" not in names
    assert "key" not in names
    mode = next(item for item in UsdctoFiatCashoutComponent.inputs if (item.get("name") if isinstance(item, dict) else getattr(item, "name", None)) == "mode")
    options = mode["options"] if isinstance(mode, dict) else getattr(mode, "options", [])
    assert options == ["fast", "best"]
    required = mode.get("required") if isinstance(mode, dict) else getattr(mode, "required", False)
    assert required is True
    assert "value" not in mode if isinstance(mode, dict) else getattr(mode, "value", None) in (None, "")


def test_cashout_returns_unsigned_prepare(mock_offramp):
    comp = UsdctoFiatCashoutComponent()
    comp.mode = "fast"
    comp.amount = "100"
    comp.currency = "EUR"
    comp.platform = "revolut"
    comp.payee = "alice"
    with patch("lfx_usdctofiat.components.usdctofiat.cashout.offramp", return_value=mock_offramp):
        payload = json.loads(comp.build_result().text)
    assert payload["signed"] is False
    assert payload["prepared"]["mode"] == "fast"
    assert payload["prepared"]["attribution"]["referral_code"] == "TOFIAT"
    mock_offramp.prepare.assert_called_once()


def test_cashout_mode_required(mock_offramp):
    mock_offramp.prepare.side_effect = ModeRequired()
    comp = UsdctoFiatCashoutComponent()
    comp.mode = ""
    comp.amount = "100"
    comp.currency = "EUR"
    comp.platform = "revolut"
    comp.payee = "alice"
    with patch("lfx_usdctofiat.components.usdctofiat.cashout.offramp", return_value=mock_offramp):
        payload = json.loads(comp.build_result().text)
    assert "mode is required" in payload["error"]


def test_estimate_watch_withdraw_deposits(mock_offramp):
    estimate = UsdctoFiatEstimateComponent()
    estimate.mode = "fast"
    estimate.amount = "100"
    estimate.currency = "EUR"
    watch = UsdctoFiatWatchComponent()
    watch.deposit_id = "42"
    withdraw = UsdctoFiatWithdrawComponent()
    withdraw.deposit_id = "42"
    deposits = UsdctoFiatDepositsComponent()
    deposits.owner = "0x1111111111111111111111111111111111111111"
    with (
        patch("lfx_usdctofiat.components.usdctofiat.estimate.offramp", return_value=mock_offramp),
        patch("lfx_usdctofiat.components.usdctofiat.watch.offramp", return_value=mock_offramp),
        patch("lfx_usdctofiat.components.usdctofiat.withdraw.offramp", return_value=mock_offramp),
        patch("lfx_usdctofiat.components.usdctofiat.deposits.offramp", return_value=mock_offramp),
    ):
        est = json.loads(estimate.build_estimate().text)
        watched = json.loads(watch.build_watch().text)
        withdrawn = json.loads(withdraw.build_withdraw().text)
        rows = json.loads(deposits.build_deposits().text)
    assert est["spread_bps"] == 0
    assert est["mode"] == "fast"
    assert watched["snapshots"][0]["status"] == "ACTIVE"
    assert withdrawn["data"] == "0xwithdraw"
    assert rows["deposits"][0]["id"] == "42"


def test_pyproject_is_lfx_usdctofiat_not_published_extra_of_this_repo():
    text = (ROOT / "pyproject.toml").read_text()
    assert 'name = "lfx-usdctofiat"' in text
    assert "usdctofiat" in text
    assert "Not a Peer Cash product" in text


def test_no_peer_cash_branding_in_extension():
    for path in ROOT.rglob("*"):
        if "tests" in path.parts:
            continue
        if path.suffix in {".py", ".md", ".toml", ".json"} and path.is_file():
            text = path.read_text().lower()
            assert "peer-cash" not in text
            assert "plugin-peer-cash" not in text
