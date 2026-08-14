
"""Public indexer GraphQL. Order / deposit reads only."""

from __future__ import annotations

from typing import Any, Iterator

import httpx

from .constants import INDEXER_URL
from .errors import IndexerError

DEPOSITS_QUERY = """
query OwnerDeposits($depositor: String!) {
  deposits(where: { depositor: $depositor }, limit: 50) {
    id
    depositor
    remainingDeposits
    outstandingIntentAmount
    status
    acceptingIntents
  }
}
"""

DEPOSIT_QUERY = """
query Deposit($id: String!) {
  deposit(id: $id) {
    id
    depositor
    remainingDeposits
    outstandingIntentAmount
    status
    acceptingIntents
  }
}
"""


class Indexer:
    def __init__(self, url: str = INDEXER_URL, *, timeout: float = 30.0, client: httpx.Client | None = None):
        self.url = url
        self.timeout = timeout
        self._client = client

    def deposits(self, owner: str) -> list[dict[str, Any]]:
        data = self._graphql(DEPOSITS_QUERY, {"depositor": owner})
        rows = data.get("deposits") or data.get("data", {}).get("deposits") or []
        if not isinstance(rows, list):
            raise IndexerError("unexpected deposits payload", details=data)
        return rows

    def deposit(self, deposit_id: str) -> dict[str, Any] | None:
        data = self._graphql(DEPOSIT_QUERY, {"id": str(deposit_id)})
        row = data.get("deposit")
        if row is None and isinstance(data.get("data"), dict):
            row = data["data"].get("deposit")
        return row

    def watch(self, deposit_id: str) -> Iterator[dict[str, Any]]:
        """Single read in v1. Hosts can poll. No long-poll loop against production."""
        row = self.deposit(deposit_id)
        if row is None:
            raise IndexerError(f"deposit {deposit_id} not found")
        yield row

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        own = self._client is None
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            resp = client.post(self.url, json={"query": query, "variables": variables})
        except httpx.HTTPError as exc:
            raise IndexerError(f"indexer transport failed: {exc}") from exc
        finally:
            if own:
                client.close()
        if resp.status_code >= 400:
            raise IndexerError(f"indexer {resp.status_code}", details=resp.text[:300])
        try:
            payload = resp.json()
        except ValueError as exc:
            raise IndexerError("indexer returned non-JSON") from exc
        if payload.get("errors"):
            raise IndexerError("indexer graphql error", details=payload["errors"])
        data = payload.get("data")
        if not isinstance(data, dict):
            raise IndexerError("indexer missing data", details=payload)
        return data
