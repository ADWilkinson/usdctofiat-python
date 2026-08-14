"""USDCtoFiat watch component. Galleon Labs. Not Peer Cash."""

from __future__ import annotations

from ._client import dumps, error_payload, offramp
from ._lfx import Component, Message, MessageTextInput, Output


class UsdctoFiatWatchComponent(Component):
    display_name = "USDCtoFiat watch"
    description = "Watch a USDCtoFiat deposit by id. Galleon Labs. Not a Peer Cash product."
    name = "UsdctoFiatWatch"
    inputs = [MessageTextInput(name="deposit_id", display_name="Deposit id", required=True)]
    outputs = [Output(display_name="Snapshots", name="snapshots", method="build_watch")]

    def build_watch(self) -> Message:
        try:
            rows = list(offramp().watch(self.deposit_id))
            return Message(text=dumps({"deposit_id": self.deposit_id, "snapshots": rows}))
        except Exception as exc:
            return Message(text=dumps(error_payload(exc)))
