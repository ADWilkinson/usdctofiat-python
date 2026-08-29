
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import pytest
import respx

from usdctofiat.constants import BASE_RPC_URL, CURATOR_URL, INDEXER_URL, MAKERS_CREATE_PATH

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def makers_fixture() -> dict:
    return json.loads((FIXTURES / "makers_create.json").read_text())


@pytest.fixture
def indexer_fixture() -> dict:
    return json.loads((FIXTURES / "indexer_deposit.json").read_text())


def _latest_round_data(answer: int, updated_at: int) -> str:
    """Encode a Chainlink latestRoundData() eth_call result."""
    words = [1, answer & (2**256 - 1), updated_at, updated_at, 1]
    return "0x" + "".join(f"{word:064x}" for word in words)


@pytest.fixture
def round_data():
    """Encoder for a Chainlink latestRoundData() eth_call result."""
    return _latest_round_data


@pytest.fixture
def mocked_http(makers_fixture, indexer_fixture):
    with respx.mock(assert_all_called=False) as router:
        router.post(f"{CURATOR_URL}{MAKERS_CREATE_PATH}").mock(
            return_value=httpx.Response(200, json=makers_fixture["response"])
        )
        router.post(INDEXER_URL).mock(
            return_value=httpx.Response(200, json=indexer_fixture["response"])
        )
        router.post(BASE_RPC_URL).mock(
            # EUR/USD at 1.158215, read now. Callers that need other values re-mock.
            return_value=httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": 1, "result": _latest_round_data(115_821_500, int(time.time()))},
            )
        )
        yield router
