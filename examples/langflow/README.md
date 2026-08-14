# Langflow pip-extension draft (`lfx-usdctofiat`)

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol. Not a Peer Cash product.

This folder is a **local `lfx-usdctofiat` pip-extension-shaped draft**
(`extension.json` + `src/lfx_usdctofiat/components/usdctofiat/`). After a
PyPI publish of this extra (held), operators install with
`pip install lfx-usdctofiat` and Langflow discovers the bundle at startup.
That is the **no-host-PR path**.

Do **not** open a PR against [`langflow-ai/langflow`](https://github.com/langflow-ai/langflow)
from this tree. An in-tree bundle PR counts at the external cap. External cap
is 2/2 (AgentKit #1442, Bankr #639). Do not publish this extra to PyPI from
this commit.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required (dropdown, no default).
There is no private-key input — the component returns unsigned
`{to, data, value, chainId}` txs for the host to sign.
`create_offramp` locks TOFIAT + galleonlabs.

## After PyPI (not this commit)

```bash
pip install lfx-usdctofiat
langflow run
# or, while developing this tree:
# lfx extension validate .
# lfx extension dev .
```

## Copy map

| This draft | Destination |
| --- | --- |
| this folder | own `lfx-usdctofiat` package (PyPI, later) |
| `src/lfx_usdctofiat/components/usdctofiat/` | same, after `lfx extension init` layout |
| in-tree Langflow bundle | **do not** — that is a host PR |

## Not this folder

- No PR to `langflow-ai/langflow`
- No Agno / CrewAI / Dify / CAMEL / Hermes host PRs
- No PyPI publish
- No Peer Cash branding
- No private keys
