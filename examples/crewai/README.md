# CrewAI BaseTool draft (not a first-party CrewAI tool)

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol. Not a Peer Cash product.

This folder is a **local draft** of `UsdctoFiatCashoutTool` (and estimate / watch /
withdraw / deposits) so we can open [`crewAIInc/crewAI`](https://github.com/crewAIInc/crewAI)
`lib/crewai-tools` the day an external SDK-host slot frees. It is **not** an
installable `crewai-tools` extra. It is **not** published. Do **not** open a PR
against `crewAIInc/crewAI` from this tree.

External cap is 2/2 (AgentKit #1442, Bankr #639). CrewAI waits.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call.
There is no constructor default to Fast or Best. There is no private-key
constructor — inject a signer callback or take the unsigned `prepare` path.

## Copy map (when Link assigns the slot)

| This draft | Upstream |
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

Before opening the host PR: drop the draft-only `BaseTool` fallback, switch
imports to `crewai.tools.BaseTool`, disclose AI authorship. Prefer waiting for
a PyPI `usdctofiat` so the extra is real.

## Not this folder

- No PR to `crewAIInc/crewAI`
- No Agno / Dify / CAMEL / Langflow / Hermes host PRs
- No PyPI publish
- No Peer Cash branding
