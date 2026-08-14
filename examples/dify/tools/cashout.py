
from __future__ import annotations

from collections.abc import Generator
from typing import Any

try:
    from dify_plugin import Tool
    from dify_plugin.entities.tool import ToolInvokeMessage
except ImportError:  # draft-only
    class ToolInvokeMessage:  # type: ignore[no-redef]
        def __init__(self, payload: Any) -> None:
            self.payload = payload

    class Tool:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.runtime = type("R", (), {"credentials": {}})()

        def create_json_message(self, data: Any) -> ToolInvokeMessage:
            return ToolInvokeMessage(data)

        def create_text_message(self, text: str) -> ToolInvokeMessage:
            return ToolInvokeMessage({"text": text})

from _client import as_dict, error_payload, offramp_from


class UsdctoFiatCashoutTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            client = offramp_from(getattr(getattr(self, "runtime", None), "credentials", None))
            prepared = client.prepare(
                mode=tool_parameters.get("mode"),
                amount=tool_parameters.get("amount"),
                currency=tool_parameters.get("currency"),
                platform=tool_parameters.get("platform"),
                payee=tool_parameters.get("payee"),
            )
            yield self.create_json_message({"prepared": as_dict(prepared), "signed": False})
        except Exception as exc:
            yield self.create_json_message(error_payload(exc))
