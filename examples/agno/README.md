# Agno toolkit draft (not a first-party Agno tool)

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol. Not a Peer Cash product.

This folder is a **local draft** of `UsdctoFiatTools` so we can open
[`agno-agi/agno`](https://github.com/agno-agi/agno) the day an external
SDK-host slot frees. It is **not** an installable Agno extra. It is **not**
published. Do **not** open a PR against `agno-agi/agno` from this tree.

External cap is 2/2 (AgentKit #1442, Bankr #639). Agno waits.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call.
There is no constructor default to Fast or Best. There is no private-key
constructor — inject a signer callback or take the unsigned `prepare` path.

## Copy map (when Link assigns the slot)

| This draft | Upstream |
| --- | --- |
| `usdctofiat_tools.py` | `libs/agno/agno/tools/usdctofiat.py` |
| `cookbook/usdctofiat_tools.py` | `cookbook/91_tools/usdctofiat_tools.py` |
| `tests/test_usdctofiat_tools.py` | `libs/agno/tests/unit/tools/test_usdctofiat.py` |
| `snippets/pyproject.extra.toml` | `libs/agno/pyproject.toml` extras |

Upstream import after the copy:

```python
from agno.tools.usdctofiat import UsdctoFiatTools
# extra: agno[usdctofiat] = ["usdctofiat"]
```

Before opening the host PR: drop the draft-only `Toolkit` fallback in
`usdctofiat_tools.py`, switch the cookbook/test imports to
`agno.tools.usdctofiat`, run `./scripts/format.sh` and `./scripts/validate.sh`,
title the PR `[feat] …`, disclose AI authorship. Prefer waiting for a PyPI
`usdctofiat` so the extra is real; if the slot must be used first, the toolkit
already talks to this personal package.

## Not this folder

- No PR to `agno-agi/agno`
- No CrewAI / Dify / CAMEL / Langflow / Hermes host PRs
- No PyPI publish
- No Peer Cash branding
