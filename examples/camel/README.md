# CAMEL toolkit example

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.

This folder contains the reference `UsdctoFiatToolkit` implementation, example, and tests for CAMEL.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call.
There is no constructor default to Fast or Best. There is no private-key
constructor — inject a signer callback or take the unsigned `prepare` path.

## File map

| Reference file | CAMEL path |
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

The upstream version removes the local `BaseToolkit` fallback and uses CAMEL's native toolkit imports and dependency guard.
