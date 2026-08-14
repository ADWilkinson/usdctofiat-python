"""Dify plugin entry for USDCtoFiat by Galleon Labs."""

from __future__ import annotations

try:
    from dify_plugin import DifyPluginEnv, Plugin
except ImportError:  # standalone reference fallback

    class DifyPluginEnv:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Plugin:  # type: ignore[no-redef]
        def __init__(self, env):
            self.env = env

        def run(self) -> None:
            raise RuntimeError("dify_plugin is required to run this plugin")


plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == "__main__":
    plugin.run()
