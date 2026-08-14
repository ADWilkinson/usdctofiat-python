# Dify sideload plugin draft (not a marketplace listing)

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol. Not a Peer Cash product.

This folder is a **local, own-repo sideload-shaped** Dify tool plugin
(`manifest.yaml` + provider + tools). Package it later with
`dify plugin package ./examples/dify` and install the `.difypkg` from a
local file. That path does **not** list the plugin and does **not** burn
an external SDK-host slot.

Do **not** open a PR against [`langgenius/dify-plugins`](https://github.com/langgenius/dify-plugins)
from this tree. Marketplace listing is a host PR. External cap is 2/2
(AgentKit #1442, Bankr #639). Dify listing waits.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call
(select, no default). There is no private-key credential — the plugin
returns unsigned `{to, data, value, chainId}` txs for the host wallet to
sign. `create_offramp` locks TOFIAT + galleonlabs.

## Sideload (own-repo, not a listing)

```bash
# from the directory above this folder, when you actually package
dify plugin package ./examples/dify
# then Dify → Plugins → Install from local file → usdctofiat.difypkg
```

`author` is `ADWilkinson` so a later own-repo GitHub install stays valid.
That is still not a `langgenius/dify-plugins` PR.

## Copy map (only if Link assigns a listing slot)

| This draft | Marketplace (do not open now) |
| --- | --- |
| this folder | `langgenius/dify-plugins` PR / `.difypkg` asset |
| `manifest.yaml` | same, author must stay the GitHub handle |

## Not this folder

- No PR to `langgenius/dify-plugins`
- No Agno / CrewAI / CAMEL / Langflow / Hermes host PRs
- No PyPI publish
- No Peer Cash branding
- No private keys
