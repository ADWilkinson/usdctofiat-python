# Dify tool plugin

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.

This folder contains a Dify tool plugin (`manifest.yaml` + provider + tools). Package it with
`dify plugin package ./examples/dify` and install the `.difypkg` from a
local file.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required on every mutating or priced call
(select, no default). There is no private-key credential — the plugin
returns unsigned `{to, data, value, chainId}` txs for the host wallet to
sign. `create_offramp` locks TOFIAT + galleonlabs.

## Package and sideload

```bash
dify plugin package ./examples/dify
# then Dify → Plugins → Install from local file → usdctofiat.difypkg
```

`author` remains `ADWilkinson` for GitHub and Marketplace distribution.
