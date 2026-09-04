"""USDCtoFiat protocol constants. Base mainnet only in v1."""

from __future__ import annotations

CHAIN_ID = 8453
USDC_DECIMALS = 6
USDC_UNITS = 10**USDC_DECIMALS
MIN_USDC_UNITS = USDC_UNITS  # 1 USDC
PRECISE_UNIT = 10**18

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ESCROW_V2 = "0x777777779d229cdF3110e9de47943791c26300Ef"
ORCHESTRATOR = "0x888888359E981B5225CA48fbCdCeff702FC3b888"
# contracts-v2@0.4.0. Verified against the address live EscrowV2 deposits carry
# as rateManagerAddress; a wrong one reverts setRateManager with
# InvalidRateManager(address) rather than failing at encode time.
RATE_MANAGER_V1 = "0xeEd7Db23e724aC4590D6dB6F78fDa6DB203535F3"
# The registry entry EscrowV2.setRateManager takes alongside the address.
# getRateManager(bytes32) on RATE_MANAGER_V1 decodes this id to manager
# 0xc141cbe4f4a9cabc3cc78159a9268a4e008922cd, name "Delegate by USDCtoFiat",
# url https://delegate.usdctofiat.xyz, fee 1e15 = 10 bps. An unregistered id
# returns an all-zero struct instead.
DELEGATE_RATE_MANAGER_ID = "0x8666d6fb0f6797c56e95339fd7ca82fdd348b9db200e10a4c4aa0a0b879fc41c"
CHAINLINK_ORACLE_ADAPTER_V2 = "0x53881a928abD61C095e5f30b63bc554872C3b2f1"
# @zkp2p/sdk@0.12.0 — adapter used for current V2.2 oracle floors
CHAINLINK_ORACLE_ADAPTER = "0xfc81d1b5841e697973af3072fc8e03af76cb39ef"
INTENT_GUARDIAN = "0x83671606454fA72ba1e2831E18C5090D25629414"
# @zkp2p/sdk@0.12.1 getGatingServiceAddress(8453, "production"). EscrowV2 only
# checks a gating signature when the deposit stores a non-zero address, so a
# deposit encoded with address(0) accepts intents the quote service never saw.
GATING_SERVICE = "0x396D31055Db28C0C6f36e8b36f18FE7227248a97"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

CURATOR_URL = "https://api.zkp2p.xyz"
INDEXER_URL = "https://indexer.zkp2p.xyz/v1/graphql"
MAKERS_CREATE_PATH = "/v2/makers/create"
# Base's public JSON-RPC. estimate() reads the currency's Chainlink feed through it.
BASE_RPC_URL = "https://mainnet.base.org"

REFERRAL_CODE = "TOFIAT"
PEER_REF = "peer-ref-TOFIAT"
DISTRIBUTION_REFERRER = "galleonlabs"
RESERVED_REFERRERS = frozenset({"peer-cash", "zkp2p-cash", "plugin-peer-cash"})

FAST_SPREAD_BPS = 0
BEST_MANAGER_FEE_BPS = 10
DEFAULT_ORACLE_MAX_STALENESS = 86400
# The oracle sets the price, so the onchain floor is one wei rather than a rate.
# @usdctofiat/offramp 8.0.0 maps conversionRate "1" to minConversionRate = 1.
MIN_CONVERSION_RATE = 1

# @zkp2p/sdk@0.12.0 CHAINLINK_ORACLE_FEEDS: code -> (feed, invert, decimals).
# USD is the documented zero-address passthrough (constant 1.0). Every other
# feed is quoted as USD per unit of fiat, so it inverts to fiat per USDC.
# Codes absent here have no Base feed and cannot be priced by this client.
CHAINLINK_ORACLE_FEEDS: dict[str, tuple[str, bool, int]] = {
    "USD": (ZERO_ADDRESS, False, 0),
    "AUD": ("0x46e51b8ca41d709928eda9ae43e42193e6cdf229", True, 8),
    "BRL": ("0x0b0e64c05083fdf9ed7c5d3d8262c4216efc9394", True, 8),
    "CAD": ("0xa840145f87572e82519d578b1f36340368a25d5d", True, 8),
    "CHF": ("0x3a1d6444fb6a402470098e23dad0b7e86e14252f", True, 8),
    "EUR": ("0xc91d87e81fab8f93699ecf7ee9b44d11e1d53f0f", True, 8),
    "GBP": ("0xccea6576904c118037695eb71195a5425e69fa15", True, 8),
    "IDR": ("0x05a6cf213ecc5501a11a08ebefa4a8a60313ef97", True, 8),
    "MXN": ("0x9e8ee77c76d4fa41306056d1c3196af5da1600bd", True, 8),
    "NZD": ("0x06bdfe07e71c476157fc025d3ccd4bbe08e83ef9", True, 8),
    "PHP": ("0x0396000dc82bfaee746a9ac6dc69dad3223ca9c6", True, 8),
    "SGD": ("0x81575495532fb311efc5c993b612564274f0949b", True, 8),
    "TRY": ("0x29413773e7cd4dfd6ad89a50887877b88a6c592c", True, 8),
    "ZAR": ("0x2ecc8a8b370fc6a217166b2782a35339bebee98b", True, 8),
}

MODES = frozenset({"fast", "best"})

# @zkp2p/contracts-v2@0.4.0 paymentMethods/base.json
PAYMENT_METHOD_HASHES: dict[str, str] = {
    "venmo": "0x90262a3db0edd0be2369c6b28f9e8511ec0bac7136cefbada0880602f87e7268",
    "revolut": "0x617f88ab82b5c1b014c539f7e75121427f0bb50a4c58b187a238531e7d58605d",
    "cashapp": "0x10940ee67cfb3c6c064569ec92c0ee934cd7afa18dd2ca2d6a2254fcb009c17d",
    "wise": "0x554a007c2217df766b977723b276671aee5ebb4adaea0edb6433c88b3e61dac5",
    "mercadopago": "0xa5418819c024239299ea32e09defae8ec412c03e58f5c75f1b2fe84c857f5483",
    "zelle": "0xf752c7d19698ecb0bb8988abf9b9a53a4c3657f3bc8850a6fb59fdf3e3ce8cd3",
    "paypal": "0x3ccc3d4d5e769b1f82dc4988485551dc0cd3c7a3926d7d8a4dde91507199490f",
    "monzo": "0x62c7ed738ad3e7618111348af32691b5767777fbaf46a2d8943237625552645c",
    "chime": "0x5908bb0c9b87763ac6171d4104847667e7f02b4c47b574fe890c1f439ed128bb",
}

# keccak256 of the ISO code, from the same catalog (USD/EUR/GBP confirmed)
CURRENCY_HASHES: dict[str, str] = {
    "USD": "0xc4ae21aac0c6549d71dd96035b7e0bdb6c79ebdba8891b666115bc976d16a29e",
    "EUR": "0xfff16d60be267153303bbfa66e593fb8d06e24ea5ef24b6acca5224c2ca6b907",
    "GBP": "0x90832e2dc3221e4d56977c1aa8f6a6706b9ad6542fbbdaac13097d0fa5e42e67",
}

# PaymentVerifierRegistry on Base. EscrowV2 asks it whether a payment method
# carries a currency and reverts CurrencyNotSupported(bytes32,bytes32) when it
# does not, so a pair outside these sets can never settle.
PAYMENT_VERIFIER_REGISTRY = "0x2b82D24437ff66Fb173eabDfD67ee2ACeb8bEb1e"

# getCurrencies(bytes32) on PAYMENT_VERIFIER_REGISTRY, read off Base. A currency
# with a Chainlink feed is not automatically settleable: only the pairs listed
# here reach a deposit. Codes with no CHAINLINK_ORACLE_FEEDS entry stay in the
# set because this mirrors the registry, not what this client can price.
PAYMENT_METHOD_CURRENCIES: dict[str, frozenset[str]] = {
    "venmo": frozenset({"USD"}),
    "revolut": frozenset(
        {
            "AED", "AUD", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD",
            "HUF", "JPY", "MXN", "NOK", "NZD", "PLN", "RON", "SAR", "SEK", "SGD",
            "THB", "TRY", "USD", "ZAR",
        }
    ),
    "cashapp": frozenset({"USD"}),
    "wise": frozenset(
        {
            "AED", "AUD", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD",
            "HUF", "IDR", "ILS", "INR", "JPY", "KES", "MXN", "MYR", "NOK", "NZD",
            "PHP", "PLN", "RON", "SEK", "SGD", "THB", "TRY", "UGX", "USD", "VND",
            "ZAR",
        }
    ),
    "mercadopago": frozenset({"ARS"}),
    "zelle": frozenset({"USD"}),
    "paypal": frozenset({"AUD", "CAD", "EUR", "GBP", "NZD", "SGD", "USD"}),
    "monzo": frozenset({"GBP"}),
    "chime": frozenset({"USD"}),
}

PLATFORMS_NEEDING_ATTESTATION = frozenset({"wise", "paypal"})
ACCESS_POLICY_PLATFORMS = frozenset({"venmo", "cashapp", "paypal"})

ERC8021_MARKER = bytes.fromhex("80218021802180218021802180218021")

PRODUCT = "USDCtoFiat"
VENDOR = "Galleon Labs"
SITE = "https://usdctofiat.xyz"
