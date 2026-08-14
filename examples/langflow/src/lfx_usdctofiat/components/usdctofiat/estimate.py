"""USDCtoFiat estimate component. Mode required."""

from __future__ import annotations

from ._client import as_dict, dumps, error_payload, offramp
from ._lfx import Component, DropdownInput, Message, MessageTextInput, Output


class UsdctoFiatEstimateComponent(Component):
    display_name = "USDCtoFiat estimate"
    description = (
        "Estimate a USDCtoFiat cash-out. Not a locked quote. "
        "mode is required: fast (0 bps) or best (10 bps)."
    )
    icon = "chart"
    name = "UsdctoFiatEstimate"
    inputs = [
        DropdownInput(
            name="mode",
            display_name="Mode",
            options=["fast", "best"],
            info="Required. fast = 0 bps. best = 10 bps. No default.",
            required=True,
        ),
        MessageTextInput(name="amount", display_name="Amount", required=True),
        MessageTextInput(name="currency", display_name="Currency", required=True),
    ]
    outputs = [Output(display_name="Estimate", name="estimate", method="build_estimate")]

    def build_estimate(self) -> Message:
        try:
            return Message(
                text=dumps(as_dict(offramp().estimate(mode=self.mode, amount=self.amount, currency=self.currency)))
            )
        except Exception as exc:
            return Message(text=dumps(error_payload(exc)))
