# CAMEL toolkit draft (not a first-party CAMEL toolkit)

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol. Not a Peer Cash product.

This folder is a **local draft** of `UsdctoFiatToolkit` so we can open
[`camel-ai/camel`](https://github.com/camel-ai/camel) `camel/toolkits/` the day
an external SDK-host slot frees. It is **not** an installable CAMEL extra.
It is **not** published. Do **not** open a PR against `camel-ai/camel` from
this tree.

External cap is 2/2 (AgentKit #1442, Bankr #639). CAMEL waits.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call.
There is no constructor default to Fast or Best. There is no private-key
constructor — inject a signer callback or take the unsigned `prepare` path.

## Copy map (when Link assigns the slot)

| This draft | Upstream |
| --- | --- |
| `usdctofiat_toolkit.py` | `camel/toolkits/usdctofiat_toolkit.py` |
| `example/usdctofiat_toolkit.py` | `examples/` cookbook next to other toolkits |
| `tests/test_usdctofiat_toolkit.py` | `test/toolkits/test_usdctofiat_toolkit.py` |
| `snippets/pyproject.extra.toml` | CAMEL extras / `@dependencies_required("usdctofiat")` |

Upstream import after the copy:

```python
from camel.toolkits import UsdctoFiatToolkit
# extra / @dependencies_required("usdctofiat")
```

Before opening the host PR: drop the draft-only `BaseToolkit` fallback, switch
imports to `camel.toolkits.base.BaseToolkit` + `FunctionTool`, add an issue,
two reviewers, disclose AI authorship. Prefer waiting for a PyPI `usdctofiat`.

## Not this folder

- No PR to `camel-ai/camel`
- No Agno / CrewAI / Dify / Langflow / Hermes host PRs
- No PyPI publish
- No Peer Cash branding
