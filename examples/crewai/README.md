# CrewAI BaseTool example

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.

This folder contains reference CrewAI tools for cash-out, estimates, order tracking, withdrawals, and deposits.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call.
There is no constructor default to Fast or Best. There is no private-key
constructor — inject a signer callback or take the unsigned `prepare` path.

## File map

| Reference file | CrewAI path |
| --- | --- |
| `usdctofiat_tool.py` | `lib/crewai-tools/src/crewai_tools/tools/usdctofiat_tool/usdctofiat_tool.py` |
| `cookbook/usdctofiat_tool.py` | docs / examples next to other vendor tools |
| `tests/test_usdctofiat_tool.py` | `lib/crewai-tools` unit tests |
| `snippets/pyproject.extra.toml` | `lib/crewai-tools` extras (`usdctofiat`) |

Upstream import after the copy:

```python
from crewai_tools import UsdctoFiatCashoutTool
# extra: crewai-tools[usdctofiat] = ["usdctofiat"]
```

The upstream version removes the local `BaseTool` fallback and uses CrewAI's native imports.
