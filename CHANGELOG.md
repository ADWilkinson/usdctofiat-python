# Changelog

## 0.1.1 — unreleased

- `mode="best"` can encode its `setRateManager` hook. #28 fixed the rate manager
  *address*; the `bytes32 rateManagerId` EscrowV2 takes beside it was never in
  the package. `encode_delegate_hook()` required it as a keyword argument and
  `encode_set_rate_manager()` raised `ValidationError: Best setRateManager needs
  the Delegate rateManagerId after deposit creation` without one, while nothing
  in `src/`, the `DelegateHook` from `prepare(mode="best")`, or the README ever
  named a value — so the documented Best follow-up ended in an exception on every
  install and a Best cash-out was a Fast deposit with the 10 bps Delegate manager
  never attached. `DELEGATE_RATE_MANAGER_ID` is now shipped and defaulted, and it
  is the id `@usdctofiat/offramp@9.0.0` passes on all five of its
  `setRateManager` paths. `getRateManager(bytes32)` on the registry decodes it to
  manager `0xc141cbe4…8922cd`, name `Delegate by USDCtoFiat`, url
  `https://delegate.usdctofiat.xyz` and fee `1e15` — 10 bps, the number
  `BEST_MANAGER_FEE_BPS` already claimed — where an unregistered id answers with
  an all-zero struct; 258 of the 500 most recent EscrowV2 deposits carrying a
  rate manager use it, all against `RATE_MANAGER_V1`. The id is pinned to that
  registry read rather than to the constant that produces it, and an explicit
  `rate_manager_id` still overrides it. `cashout()` still does not sign the hook
  itself: the deposit id only exists after `createDeposit` is mined. (#32)
- Attribution codes lead with `galleonlabs` and carry `peer-ref-TOFIAT`
  second, the order `@usdctofiat/offramp` emits and every live deposit carries.
  The client emitted them reversed, and `codes[0]` is the slot the indexer reads
  a deposit's `attributionSource` from: across the 763 most recent Base deposits
  carrying codes, a `peer-ref-*` marker sits at index 0 zero times and at index 1
  in all 45 that have one, while a `codes[0]` the indexer does not recognise
  resolves to `attributionSource: null`. Deposits this product creates through
  the reference SDK read `['galleonlabs', 'peer-ref-TOFIAT', 'bc_nbn6qkni']`, so
  every deposit a Python install created put the marker in the source slot and
  dropped the distribution referrer to an index that is not read — the one thing
  the attribution lock exists to deliver. The layout was never wrong: schema 0,
  the 16-byte marker and the length prefix all byte-match the live suffix, and
  this client's own `parse_erc8021()` decodes it. The order is now pinned to the
  suffix decoded off deposit `3832` rather than to the constants that produce it,
  which is the check the six existing assertions could not be. (#30)
- `RATE_MANAGER_V1` points at the deployed Delegate rate manager. The constant
  was `0x...4590D6bB6F78...` where Base runs `0x...4590d6db6f78...` — one nibble
  — and nothing caught it: `to_checksum_address()` re-derives the case of
  whatever 20 bytes it is given, so the typo encoded and round-tripped cleanly.
  The typed address holds no code, and EscrowV2 answers the resulting
  `setRateManager` with `InvalidRateManager(0x...d6bb6f78...)`, so `mode="best"`
  could not attach its 10 bps Delegate manager on any install; the Fast half of
  a Best cash-out was unaffected because `createDeposit` never reads the rate
  manager. Live `eth_call` from a real depositor now returns `0x` where it
  reverted. The protocol addresses and the Chainlink feed table are pinned to
  literals read off Base rather than to the constants under test, and any
  mixed-case address constant must be valid EIP-55 — the typo broke the
  checksum, so that alone catches the class offline. (#28)
- `prepare()` / `cashout()` validate the platform and the currency before the
  curator POST. Both are local lookups the client already owns, but they ran
  after `create_payee_hash()`, so an unsupported platform reached
  `POST /v2/makers/create` and came back as `CuratorError: curator 400:
  {"errorCode": "unsupported_processor_skrill"}` — the client's own
  `ValidationError`, the one naming the nine platforms in
  `PAYMENT_METHOD_HASHES`, was unreachable from either entry point. An
  unsupported currency was worse: the curator accepts the request, mints a maker
  record for the payee handle, and only then does `oracle_feed_for()` raise, so
  `prepare(currency="JPY", ...)` disclosed a payee to a third-party production
  service for a cash-out that could never be encoded. Both now raise before any
  network call. (#26)
- `deposits()` filters on the EscrowV2 address and returns the onchain
  `depositId`. The indexer serves every Base escrow it has tracked, so filtering
  on `depositor` + `chainId` alone returned deposits this client cannot drive:
  live, one depositor came back with 35 rows across three escrows, only 9 of them
  EscrowV2, and the rows carried no `escrowAddress` to tell them apart. The
  selection also had no id that the other methods accept — `id` is the indexer's
  composite `<escrow>_<depositId>` key, which `watch()` binds to
  `$depositId: numeric!` for an empty result and `withdraw()` / `close()` feeds to
  `int()` for a `ValueError` — so listing an owner's deposits and then watching or
  closing one could not work. Rows now carry `depositId` and `escrowAddress`, and
  the fixture matches a live row. Mirrors the reference SDK, which likewise
  filters owner deposits to the escrows it drives. (#22)
- `create_payee_hash()` posts `offchainId` as a top-level field and reads the
  digest out of the curator's `responseObject`. `0.1.0` nested the identifier
  under `payeeData` and added a `chainId`, which the curator rejects as
  `invalid_maker_data` exactly as if no payee had been sent, so every
  `prepare()` / `cashout()` that did not already carry a `payee_details_hash`
  raised `CuratorError`. The response envelope
  (`{success, message, responseObject, statusCode, errorCode}`) was also never
  read past its top level, so a successful answer would have been dropped too. A
  2xx carrying `success: false` is now an error, a digest that is not a 32-byte
  hex hash is refused rather than encoded into calldata, and the request body and
  live envelope are pinned by tests. Matches `postMakerCreate` in
  `@usdctofiat/offramp` 9.0.0. (#20)
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
