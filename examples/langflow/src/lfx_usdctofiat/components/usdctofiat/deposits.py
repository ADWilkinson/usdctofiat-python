"""USDCtoFiat deposits component. Galleon Labs. Not Peer Cash."""

from __future__ import annotations

from ._client import dumps, error_payload, offramp
from ._lfx import Component, Message, MessageTextInput, Output


class UsdctoFiatDepositsComponent(Component):
    display_name = "USDCtoFiat deposits"
    description = "List USDCtoFiat deposits for an owner on Base. Galleon Labs. Not a Peer Cash product."
    name = "UsdctoFiatDeposits"
    inputs = [MessageTextInput(name="owner", display_name="Owner", info="0x depositor on Base.", required=True)]
    outputs = [Output(display_name="Deposits", name="deposits", method="build_deposits")]

    def build_deposits(self) -> Message:
        try:
            return Message(text=dumps({"owner": self.owner, "deposits": offramp().deposits(self.owner)}))
        except Exception as exc:
            return Message(text=dumps(error_payload(exc)))
