# Agno toolkit example

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.

This folder contains the reference `UsdctoFiatTools` implementation, cookbook, and tests for Agno.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call.
There is no constructor default to Fast or Best. There is no private-key
constructor — inject a signer callback or take the unsigned `prepare` path.

## File map

| Reference file | Agno path |
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

The upstream version removes the local `Toolkit` fallback and imports `agno.tools.usdctofiat` from the installed package. Validate with Agno's formatting and validation scripts.
