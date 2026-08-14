"""USDCtoFiat cashout component for Langflow.

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.
Docs: https://usdctofiat.xyz/developers

Wraps `usdctofiat.cashout(mode="fast"|"best")` via `prepare()`. Mode is
required. No private-key input — returns unsigned {to, data, value, chainId}
transactions.
"""

from __future__ import annotations

from ._client import as_dict, dumps, error_payload, offramp
from ._lfx import Component, DropdownInput, Message, MessageTextInput, Output


class UsdctoFiatCashoutComponent(Component):
    display_name = "USDCtoFiat cashout"
    description = (
        "Cash out Base USDC to fiat via USDCtoFiat by Galleon Labs. "
        "Built on the public Peer/ZKP2P protocol. "
        "mode is required: fast (0% spread) or best (Delegate, 10 bps). "
        "Returns unsigned txs. Never pass a wallet private key."
    )
    icon = "banknote"
    name = "UsdctoFiatCashout"
    inputs = [
        DropdownInput(
            name="mode",
            display_name="Mode",
            options=["fast", "best"],
            info="Required. fast = 0% spread. best = Delegate, 10 bps. No default.",
            required=True,
        ),
        MessageTextInput(name="amount", display_name="Amount", info="Human USDC amount.", required=True),
        MessageTextInput(name="currency", display_name="Currency", info="Fiat ISO code, e.g. EUR.", required=True),
        MessageTextInput(name="platform", display_name="Platform", info="Payment rail, e.g. revolut.", required=True),
        MessageTextInput(name="payee", display_name="Payee", info="Handle on that platform.", required=True),
    ]
    outputs = [Output(display_name="Result", name="result", method="build_result")]

    def build_result(self) -> Message:
        try:
            prepared = offramp().prepare(
                mode=self.mode,
                amount=self.amount,
                currency=self.currency,
                platform=self.platform,
                payee=self.payee,
            )
            return Message(text=dumps({"prepared": as_dict(prepared), "signed": False}))
        except Exception as exc:
            return Message(text=dumps(error_payload(exc)))
