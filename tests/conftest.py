
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from usdctofiat.constants import CURATOR_URL, INDEXER_URL, MAKERS_CREATE_PATH

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def makers_fixture() -> dict:
    return json.loads((FIXTURES / "makers_create.json").read_text())


@pytest.fixture
def mocked_http(makers_fixture):
    with respx.mock(assert_all_called=False) as router:
        router.post(f"{CURATOR_URL}{MAKERS_CREATE_PATH}").mock(
            return_value=httpx.Response(200, json=makers_fixture["response"])
        )
        router.post(INDEXER_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "deposits": [
                            {
                                "id": "42",
                                "depositor": "0x1111111111111111111111111111111111111111",
                                "remainingDeposits": "100000000",
                                "outstandingIntentAmount": "0",
                                "status": "ACTIVE",
                                "acceptingIntents": True,
                            }
                        ],
                        "deposit": {
                            "id": "42",
                            "depositor": "0x1111111111111111111111111111111111111111",
                            "remainingDeposits": "100000000",
                            "outstandingIntentAmount": "0",
                            "status": "ACTIVE",
                            "acceptingIntents": True,
                        },
                    }
                },
            )
        )
        yield router
