# Langflow pip extension (`lfx-usdctofiat`)

USDCtoFiat by Galleon Labs. Built on the public Peer/ZKP2P protocol.

This folder contains the `lfx-usdctofiat` extension
(`extension.json` + `src/lfx_usdctofiat/components/usdctofiat/`). After publishing to PyPI, operators install with
`pip install lfx-usdctofiat` and Langflow discovers the bundle at startup.

## What this wraps

`usdctofiat.cashout(mode="fast"|"best")` plus `watch`, `withdraw`/`close`,
`deposits`, `estimate`. Mode is required (dropdown, no default).
There is no private-key input — the component returns unsigned
`{to, data, value, chainId}` txs for the host to sign.
`create_offramp` locks TOFIAT + galleonlabs.

## Install

```bash
pip install lfx-usdctofiat
langflow run
# or, while developing this tree:
# lfx extension validate .
# lfx extension dev .
```

## Copy map

| Reference file | Package destination |
| --- | --- |
| this folder | `lfx-usdctofiat` package |
| `src/lfx_usdctofiat/components/usdctofiat/` | same, after `lfx extension init` layout |
