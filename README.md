# usdctofiat

USDCtoFiat by Galleon Labs. Python client for non-custodial USDC-to-fiat cash-out on Base.

Built on the public Peer/ZKP2P protocol. Not a Peer Cash product. Not Peerlytics.

https://usdctofiat.xyz · https://usdctofiat.xyz/developers

## Install

```bash
pip install usdctofiat
```

This repository is the source. Releases are cut by pushing a `v*` tag, which builds
the sdist and wheel and publishes them to PyPI via Trusted Publishing after the `pypi`
environment approval. See [`CHANGELOG.md`](CHANGELOG.md).

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

`create_offramp()` locks attribution to `galleonlabs` then `peer-ref-TOFIAT`, the order the indexer reads a deposit's source from. Inbound `referral_code` and `peer-ref-*` values are discarded. Extra analytics referrers may be appended after those two.

## What v1 does

- Fast prepare-path: public curator `POST /v2/makers/create` (no API key), then unsigned USDC `approve` + EscrowV2 `createDeposit` at the oracle floor (0 bps, no Delegate vault), with ERC-8021 on every tx.
- Best is the same deposit plus a Delegate `setRateManager` hook so the API exists. The hook is encoded after a `deposit_id` is known. No Relay. No attestation mint.
- `estimate` reads the currency's Chainlink feed on Base and prices the cash-out
  off it. `watch`, `withdraw` / `close`, and `deposits` talk to the public indexer.

There is no `POST /cashout`. Deposit creation is onchain.

## Best follow-up

Best creates the same deposit as Fast, then attaches the Delegate rate manager
once EscrowV2 has given the deposit an id. `prepare(mode="best")` returns the
hook; `encode_delegate_hook()` encodes it against
`DELEGATE_RATE_MANAGER_ID` (Delegate by USDCtoFiat, 10 bps) unless you pass
another registry entry.

```python
order = offramp.cashout(mode="best", signer=signer, amount="100",
                        currency="EUR", platform="revolut", payee="alice")
signer(offramp.encode_delegate_hook(order.deposit_id))
```

## Currencies

The deposit rate comes from the currency's Chainlink feed on Base at 0 bps, so
only currencies with a feed are accepted:

`USD` `AUD` `BRL` `CAD` `CHF` `EUR` `GBP` `IDR` `MXN` `NZD` `PHP` `SGD` `TRY` `ZAR`

Anything else raises `ValidationError`. A code with no feed could otherwise be
encoded onchain at a fixed 1:1 rate.

## Estimate

`estimate()` reads that same feed live and returns fiat per USDC, so it is a
network call. USD is the zero-address passthrough and reads nothing.

```python
offramp = create_offramp()  # rpc_url= to use your own Base endpoint
quote = offramp.estimate(mode="fast", amount="100", currency="EUR")
print(quote.rate, quote.receive_amount, quote.stale)
```

`rate` is target-currency units per 1 USDC at `as_of`; `receive_amount` is
`amount x rate`. `stale` is set when the feed last updated over a day ago. It is
an estimate, not a locked quote: the binding rate resolves when a buyer fills. An
unreachable RPC raises `OracleError` rather than falling back to a 1:1 rate.

## Base mainnet

| | |
| --- | --- |
| Chain | 8453 |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| EscrowV2 | `0x777777779d229cdF3110e9de47943791c26300Ef` |

HTTP: `https://api.zkp2p.xyz` and `https://indexer.zkp2p.xyz/v1/graphql`.
JSON-RPC: `https://mainnet.base.org`, overridable with `rpc_url`.

## Agno toolkit draft

A local `UsdctoFiatTools` draft lives in [`examples/agno/`](examples/agno/).
It is a copy-ready scaffold for a future `agno-agi/agno` PR (`agno[usdctofiat]`).
It is not an installable Agno first-party tool. Do not open that host PR
while the external cap is full. Mode is required. No private-key constructor.

## Licence

MIT
