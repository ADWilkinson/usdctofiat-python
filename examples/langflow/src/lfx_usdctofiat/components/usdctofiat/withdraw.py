"""USDCtoFiat withdraw component. Unsigned tx. No private keys."""

from __future__ import annotations

from ._client import as_dict, dumps, error_payload, offramp
from ._lfx import Component, Message, MessageTextInput, Output


class UsdctoFiatWithdrawComponent(Component):
    display_name = "USDCtoFiat withdraw"
    description = (
        "Withdraw or close a USDCtoFiat deposit. Returns an unsigned tx. "
        "No private keys."
    )
    name = "UsdctoFiatWithdraw"
    inputs = [MessageTextInput(name="deposit_id", display_name="Deposit id", required=True)]
    outputs = [Output(display_name="Tx", name="tx", method="build_withdraw")]

    def build_withdraw(self) -> Message:
        try:
            return Message(text=dumps(as_dict(offramp().withdraw(self.deposit_id, signer=None))))
        except Exception as exc:
            return Message(text=dumps(error_payload(exc)))
