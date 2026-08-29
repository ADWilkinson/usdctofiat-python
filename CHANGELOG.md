# Changelog

## 0.1.1 — unreleased

- `estimate()` prices off the currency's Chainlink feed instead of returning a
  fixed `rate = "1"`. Every non-USD estimate was wrong by the whole FX rate:
  `estimate(amount="100", currency="TRY")` reported 100 TRY where the feed pays
  about 4,824, and EUR was quoted roughly 16% high. The rate is now read with
  `latestRoundData()` over Base JSON-RPC and inverted to fiat per USDC, matching
  `readEstimate` in `@zkp2p/cash`. `Estimate` gains `as_of`, `oracle_updated_at`
  and `stale`; a currency with no feed raises `ValidationError` as `prepare()`
  already did, and an unreachable RPC raises `OracleError` rather than falling
  back to 1:1. The endpoint defaults to `https://mainnet.base.org` and is
  overridable with `rpc_url` or an injected `Oracle`. (#18)
- `encode_create_deposit` defaults `gating_service` to the protocol gating
  service `0x396D31055Db28C0C6f36e8b36f18FE7227248a97` and `retain_on_empty` to
  `False`. `0.1.0` encoded `intentGatingService = 0x0`, which turns off the
  EscrowV2 gating check so a deposit accepts intents the quote service never
  saw, and `retainOnEmpty = true`, which left every drained deposit permanently
  ACTIVE and still accepting intents. These were the last two words where the
  encoded `createDeposit` struct differed from `@usdctofiat/offramp` 8.0.2; the
  calldata is now byte-identical to it, pinned by a test. Both stay overridable.
  (#16)
- `deposits()` and `watch()` now query the live Hasura indexer schema (`Deposit`)
  with its comparison-expression filters, including case-insensitive Ethereum
  address matching. The previous lowercase `deposits` / `deposit` root fields do
  not exist, so both methods failed for every caller. The single-deposit read
  filters by the onchain deposit id and EscrowV2 address instead of treating that
  id as the indexer's internal primary key. (#13)
- `encode_create_deposit` attaches the Chainlink oracle for every currency and
  floors `minConversionRate` at 1 wei, so the feed sets the price. It previously
  attached an oracle only for USD and encoded `minConversionRate = 1e18`, which
  priced every other currency at a fixed 1.0 fiat per USDC: `currency="MXN"` sold
  1 USDC for 1 MXN, and EUR/GBP deposits sat above market and never filled. A
  currency with no Base feed now raises `ValidationError` instead of encoding
  1:1. The encoded currency row is byte-identical to `@usdctofiat/offramp` 8.0.2.
  (#11)
- `encode_create_deposit` defaults `intent_guardian` to the protocol guardian
  instead of `address(0)`. Deposits created by `0.1.0` encoded
  `intentGuardian = 0x0000000000000000000000000000000000000000`; this restores
  parity with `@usdctofiat/offramp` 8.0.0. (#3, #4)
- `extract_deposit_id` normalises receipt topics before decoding, so a web3.py
  receipt (`HexBytes` topics) yields the deposit id instead of raising
  `ValueError`. `cashout()` crashed on any signer that returned a real receipt.
- `cashout()` and `withdraw()` read the tx hash through `extract_tx_hash`, which
  accepts `transactionHash` / `transaction_hash` alongside `tx_hash` / `hash` /
  `txHash` and decodes `HexBytes` values. A web3.py receipt previously yielded
  `tx_hash = ""` and an empty `tx_hashes`, and a `HexBytes` hash stringified to
  `"HexBytes('0x…')"` instead of a hash. (#9)
- Version is single-sourced from `usdctofiat.__version__`; `pyproject.toml`
  derives it.
- Releases are cut by pushing a `v*` tag, which runs `.github/workflows/release.yml`
  and publishes to PyPI via Trusted Publishing after the `pypi` environment
  approval.

## 0.1.0 — 2026-08-14

- First PyPI upload. `cashout(mode="fast"|"best")` on Base, attribution locked to
  `peer-ref-TOFIAT` then `galleonlabs`, no private-key handling.
