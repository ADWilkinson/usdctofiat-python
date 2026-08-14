"""Standalone lfx fallbacks for running the reference outside Langflow."""

from __future__ import annotations

from typing import Any

try:
    from lfx.custom.custom_component.component import Component
    from lfx.io import DropdownInput, MessageTextInput, Output
    from lfx.schema.message import Message
except ImportError:  # standalone reference fallback

    class Component:  # type: ignore[no-redef]
        display_name = ""
        description = ""
        icon = ""
        name = ""
        inputs: list[Any] = []
        outputs: list[Any] = []

    class Message:  # type: ignore[no-redef]
        def __init__(self, text: str = "") -> None:
            self.text = text

    def MessageTextInput(**kwargs: Any) -> dict[str, Any]:  # type: ignore[misc]
        return kwargs

    def DropdownInput(**kwargs: Any) -> dict[str, Any]:  # type: ignore[misc]
        return kwargs

    def Output(**kwargs: Any) -> dict[str, Any]:  # type: ignore[misc]
        return kwargs

__all__ = ["Component", "DropdownInput", "Message", "MessageTextInput", "Output"]
