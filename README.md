# usdctofiat

USDCtoFiat by Galleon Labs. Python client for non-custodial USDC-to-fiat cash-out on Base.

Built on the public Peer/ZKP2P protocol. Not a Peer Cash product. Not Peerlytics.

https://usdctofiat.xyz · https://usdctofiat.xyz/developers

## Install

```bash
pip install usdctofiat
```

This repository is the source. A PyPI release is a separate publish step and is not part of this scaffold.

## Cash out

`mode` is required. Fast is 0% spread / 0 bps and earns `TOFIAT`. Best is Delegate at 10 bps.

The client never takes a wallet private key. Pass a signer callback that submits an unsigned tx, or call `prepare()` and sign in the host.

```python
from usdctofiat import cashout, create_offramp

def signer(tx):
    # Host signs and submits {to, data, value, chain_id}. Return the tx hash.
    return submit(tx)

order = cashout(
    mode="fast",
    signer=signer,
    amount="100",
    currency="EUR",
    platform="revolut",
    payee="alice",
)
print(order.deposit_id, order.tx_hash, order.mode)
```

Strings and numbers are human USDC amounts. An `int` is exact six-decimal base units.

## Prepare without a signer

```python
offramp = create_offramp()
prepared = offramp.prepare(
    mode="fast",
    amount="100",
    currency="EUR",
    platform="revolut",
    payee="alice",
)
for tx, step in zip(prepared.txs, prepared.steps):
    print(step, tx.to, tx.data[:10])
```

`create_offramp()` locks attribution to `peer-ref-TOFIAT` then `galleonlabs`. Inbound `referral_code` and `peer-ref-*` values are discarded. Extra analytics referrers may be appended after those two.

## What v1 does

- Fast prepare-path: public curator `POST /v2/makers/create` (no API key), then unsigned USDC `approve` + EscrowV2 `createDeposit` at the oracle floor (0 bps, no Delegate vault), with ERC-8021 on every tx.
- Best is the same deposit plus a Delegate `setRateManager` hook so the API exists. The hook is encoded after a `deposit_id` is known. No Relay. No attestation mint.
- `estimate`, `watch`, `withdraw` / `close`, and `deposits` talk to the public indexer.

There is no `POST /cashout`. Deposit creation is onchain.

## Base mainnet

| | |
| --- | --- |
| Chain | 8453 |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| EscrowV2 | `0x777777779d229cdF3110e9de47943791c26300Ef` |

HTTP: `https://api.zkp2p.xyz` and `https://indexer.zkp2p.xyz/v1/graphql`.

## Host toolkit drafts (local only)

Copy-ready scaffolds live under `examples/`. They wrap `usdctofiat.cashout(mode="fast"|"best")`. Mode is required. No private-key constructor. Do **not** open an upstream host PR or marketplace listing from this tree. External cap is 2/2 (AgentKit #1442, Bankr #639).

| Draft | Shape | Future unlock | Do not open |
| --- | --- | --- | --- |
| [`examples/agno/`](examples/agno/) | `UsdctoFiatTools` | in-tree `agno-agi/agno` when a slot frees | `agno-agi/agno` |
| [`examples/crewai/`](examples/crewai/) | `BaseTool` | in-tree `crewAIInc/crewAI` `lib/crewai-tools` | `crewAIInc/crewAI` |
| [`examples/dify/`](examples/dify/) | sideload `.difypkg` | own-repo sideload now; marketplace later | `langgenius/dify-plugins` |
| [`examples/camel/`](examples/camel/) | `BaseToolkit` | in-tree `camel-ai/camel` `camel/toolkits/` | `camel-ai/camel` |
| [`examples/langflow/`](examples/langflow/) | `lfx-usdctofiat` pip extension | PyPI then `pip install lfx-usdctofiat` (no host PR) | `langflow-ai/langflow` |

No Hermes adapter or `hermes-plugin-index` PR from this repo.

## Licence

MIT
