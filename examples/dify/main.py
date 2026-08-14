"""Dify plugin entry. USDCtoFiat by Galleon Labs. Not a Peer Cash product.

Sideload draft. Do not open langgenius/dify-plugins from this tree.
"""

from __future__ import annotations

try:
    from dify_plugin import DifyPluginEnv, Plugin
except ImportError:  # draft-only — real sideload needs dify_plugin installed

    class DifyPluginEnv:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Plugin:  # type: ignore[no-redef]
        def __init__(self, env):
            self.env = env

        def run(self) -> None:
            raise RuntimeError("dify_plugin is not installed; this is a sideload draft")


plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == "__main__":
    plugin.run()
