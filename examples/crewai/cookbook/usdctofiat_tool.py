"""
USDCtoFiat Tools — USDC to fiat cash-out on Base

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
Docs: https://usdctofiat.xyz/developers

UsdctoFiatCashoutTool is a CrewAI BaseTool. mode is required on cashout
and estimate: "fast" (0% / TOFIAT) or "best" (Delegate, 10 bps).
There is no default.

The tools do not accept a wallet private key. Inject a signer callback
that submits unsigned {to, data, value, chainId} txs, or omit the signer
and cashout() returns the unsigned prepare payload for the host to sign.

This cookbook maps to CrewAI's tool examples.

Run: `uv pip install usdctofiat` (or `pip install -e .` from this repo)
     `uv pip install crewai crewai-tools` when you actually run the crew.
"""

from crewai import Agent, Crew, Task

# Local reference import. Upstream: from crewai_tools import UsdctoFiatCashoutTool
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usdctofiat_tool import (
    UsdctoFiatCashoutTool,
    UsdctoFiatDepositsTool,
    UsdctoFiatEstimateTool,
    UsdctoFiatWatchTool,
    UsdctoFiatWithdrawTool,
)


def signer(tx):
    # Host signs and submits {to, data, value, chainId}. Return the tx hash.
    # Keep the key in *your* runtime. Never pass it to UsdctoFiatCashoutTool.
    raise NotImplementedError("inject your wallet signer")


cashout = UsdctoFiatCashoutTool(signer=signer)
estimate = UsdctoFiatEstimateTool()
watch = UsdctoFiatWatchTool()
withdraw = UsdctoFiatWithdrawTool(signer=signer)
deposits = UsdctoFiatDepositsTool()

agent = Agent(
    role="USDCtoFiat cashier",
    goal="Help the user cash out Base USDC to fiat via USDCtoFiat by Galleon Labs.",
    backstory=(
        "You use USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol. "
        "Mode is required. Never ask for a wallet private key."
    ),
    tools=[cashout, estimate, watch, withdraw, deposits],
    verbose=True,
)

task = Task(
    description=(
        "Estimate cashing out 100 USDC to EUR on Revolut as alice. "
        "The user wants Fast (0% / TOFIAT). mode is required."
    ),
    expected_output="A JSON estimate with spread_bps=0 and mode=fast.",
    agent=agent,
)

crew = Crew(agents=[agent], tasks=[task])

if __name__ == "__main__":
    crew.kickoff()
