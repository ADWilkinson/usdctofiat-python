"""USDCtoFiat Dify provider by Galleon Labs.

No credentials or private keys are required.
"""

from __future__ import annotations

from typing import Any

try:
    from dify_plugin import ToolProvider
except ImportError:  # standalone reference fallback

    class ToolProvider:  # type: ignore[no-redef]
        pass


class UsdctoFiatProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # Public curator / indexer. No API key. No wallet key.
        if credentials:
            banned = ("private_key", "privateKey", "key", "secret", "mnemonic", "wallet_key")
            if any(name in credentials for name in banned):
                raise ValueError(
                    "USDCtoFiat does not accept a private key. "
                    "The plugin returns unsigned txs for the host to sign."
                )
