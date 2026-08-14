"""
USDCtoFiat Toolkit — USDC to fiat cash-out on Base

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
Not a Peer Cash product. https://usdctofiat.xyz/developers

UsdctoFiatToolkit is a CAMEL BaseToolkit. mode is required on cashout
and estimate: "fast" (0% / TOFIAT) or "best" (Delegate, 10 bps).
There is no default.

The toolkit does not accept a wallet private key. Inject a signer callback
that submits unsigned {to, data, value, chainId} txs, or omit the signer
and cashout() returns the unsigned prepare payload for the host to sign.

This example is a draft for camel-ai/camel examples/.
Do not open camel-ai/camel until a host slot is free.

Run: `uv pip install usdctofiat` (or `pip install -e .` from this repo)
     `uv pip install camel-ai` when you actually run the agent.
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Draft import (this repo). Upstream: from camel.toolkits import UsdctoFiatToolkit
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdctofiat_toolkit import UsdctoFiatToolkit


def signer(tx):
    # Host signs and submits {to, data, value, chainId}. Return the tx hash.
    # Keep the key in *your* runtime. Never pass it to UsdctoFiatToolkit.
    raise NotImplementedError("inject your wallet signer")


toolkit = UsdctoFiatToolkit(signer=signer)

# model = ModelFactory.create(
#     model_platform=ModelPlatformType.OPENAI,
#     model_type=ModelType.GPT_4O_MINI,
# )
# agent = ChatAgent(
#     system_message=(
#         "You help users cash out Base USDC to fiat via USDCtoFiat by Galleon Labs. "
#         "Built on the public Peer/ZKP2P protocol. Not a Peer Cash product. "
#         "Always ask the user to choose mode=fast (0% / TOFIAT) or mode=best "
#         "(Delegate, 10 bps). Never invent a mode default. Never ask for a "
#         "wallet private key."
#     ),
#     model=model,
#     tools=toolkit.get_tools(),
# )

if __name__ == "__main__":
    print(toolkit.estimate(mode="fast", amount="100", currency="EUR"))
