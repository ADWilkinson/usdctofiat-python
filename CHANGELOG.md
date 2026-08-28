# Changelog

## 0.1.1 — unreleased

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
