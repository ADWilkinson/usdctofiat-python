
"""Public indexer GraphQL. Order / deposit reads only."""

from __future__ import annotations

from typing import Any, Iterator

import httpx

from .constants import CHAIN_ID, ESCROW_V2, INDEXER_URL
from .errors import IndexerError

DEPOSITS_QUERY = """
query OwnerDeposits($depositor: String!, $escrowAddress: String!, $chainId: Int!) {
  Deposit(
    where: {
      depositor: { _ilike: $depositor }
      escrowAddress: { _eq: $escrowAddress }
      chainId: { _eq: $chainId }
    }
    limit: 50
    order_by: { timestamp: desc }
  ) {
    id
    depositId
    escrowAddress
    depositor
    remainingDeposits
    outstandingIntentAmount
    status
    acceptingIntents
  }
}
"""

DEPOSIT_QUERY = """
query Deposit($depositId: numeric!, $escrowAddress: String!, $chainId: Int!) {
  Deposit(
    where: {
      depositId: { _eq: $depositId }
      escrowAddress: { _eq: $escrowAddress }
      chainId: { _eq: $chainId }
    }
    limit: 1
  ) {
    id
    depositId
    escrowAddress
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
        """An owner's EscrowV2 deposits, newest first.

        Scoped to EscrowV2 because the indexer serves every Base escrow it has
        ever tracked and withdraw() only ever targets this one. Rows carry the
        onchain depositId that watch() and withdraw() take; `id` is the
        indexer's own "<escrow>_<depositId>" key and neither method accepts it.
        """
        data = self._graphql(
            DEPOSITS_QUERY,
            {
                "depositor": owner.strip(),
                "escrowAddress": ESCROW_V2.lower(),
                "chainId": CHAIN_ID,
            },
        )
        rows = data.get("Deposit")
        if not isinstance(rows, list):
            raise IndexerError("unexpected deposits payload", details=data)
        return rows

    def deposit(self, deposit_id: str) -> dict[str, Any] | None:
        data = self._graphql(
            DEPOSIT_QUERY,
            {
                "depositId": str(deposit_id),
                "escrowAddress": ESCROW_V2.lower(),
                "chainId": CHAIN_ID,
            },
        )
        rows = data.get("Deposit")
        if not isinstance(rows, list):
            raise IndexerError("unexpected deposit payload", details=data)
        return rows[0] if rows else None

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
