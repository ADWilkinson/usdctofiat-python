"""Protocol addresses are pinned to what Base mainnet actually runs.

Every other constant assertion in the suite compares an encoded value back to
the constant that produced it, so a mistyped address encodes, round-trips and
passes. RATE_MANAGER_V1 shipped one nibble wrong that way: EscrowV2 answered
setRateManager with InvalidRateManager(address). These pins and the EIP-55
guard are the checks that do not derive from the constant under test.
"""

import re

from eth_utils import is_checksum_address

from usdctofiat import constants

ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Read off Base mainnet: contract code, decoded EscrowV2 createDeposit calldata,
# and the public indexer's Deposit / MethodCurrency rows.
ONCHAIN = {
    "USDC": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "ESCROW_V2": "0x777777779d229cdf3110e9de47943791c26300ef",
    "RATE_MANAGER_V1": "0xeed7db23e724ac4590d6db6f78fda6db203535f3",
    "CHAINLINK_ORACLE_ADAPTER": "0xfc81d1b5841e697973af3072fc8e03af76cb39ef",
    "CHAINLINK_ORACLE_ADAPTER_V2": "0x53881a928abd61c095e5f30b63bc554872c3b2f1",
    "INTENT_GUARDIAN": "0x83671606454fa72ba1e2831e18c5090d25629414",
    "GATING_SERVICE": "0x396d31055db28c0c6f36e8b36f18fe7227248a97",
}

# Chainlink FX feeds on Base, each confirmed by its own description().
ONCHAIN_FEEDS = {
    "USD": constants.ZERO_ADDRESS,
    "AUD": "0x46e51b8ca41d709928eda9ae43e42193e6cdf229",
    "BRL": "0x0b0e64c05083fdf9ed7c5d3d8262c4216efc9394",
    "CAD": "0xa840145f87572e82519d578b1f36340368a25d5d",
    "CHF": "0x3a1d6444fb6a402470098e23dad0b7e86e14252f",
    "EUR": "0xc91d87e81fab8f93699ecf7ee9b44d11e1d53f0f",
    "GBP": "0xccea6576904c118037695eb71195a5425e69fa15",
    "IDR": "0x05a6cf213ecc5501a11a08ebefa4a8a60313ef97",
    "MXN": "0x9e8ee77c76d4fa41306056d1c3196af5da1600bd",
    "NZD": "0x06bdfe07e71c476157fc025d3ccd4bbe08e83ef9",
    "PHP": "0x0396000dc82bfaee746a9ac6dc69dad3223ca9c6",
    "SGD": "0x81575495532fb311efc5c993b612564274f0949b",
    "TRY": "0x29413773e7cd4dfd6ad89a50887877b88a6c592c",
    "ZAR": "0x2ecc8a8b370fc6a217166b2782a35339bebee98b",
}


def _named_addresses() -> dict[str, str]:
    found = {
        name: value
        for name, value in vars(constants).items()
        if isinstance(value, str) and ADDRESS.match(value)
    }
    found.update(
        {f"CHAINLINK_ORACLE_FEEDS[{code}]": feed for code, (feed, _, _) in constants.CHAINLINK_ORACLE_FEEDS.items()}
    )
    return found


def test_protocol_addresses_match_base_mainnet():
    for name, expected in ONCHAIN.items():
        assert getattr(constants, name).lower() == expected, name


def test_oracle_feeds_match_base_mainnet():
    assert set(constants.CHAINLINK_ORACLE_FEEDS) == set(ONCHAIN_FEEDS)
    for code, expected in ONCHAIN_FEEDS.items():
        feed, invert, decimals = constants.CHAINLINK_ORACLE_FEEDS[code]
        assert feed.lower() == expected.lower(), code
        # Every feed is quoted USD per unit of fiat at 8 decimals and inverts to
        # fiat per USDC. USD alone is the zero-address passthrough.
        if code == "USD":
            assert (invert, decimals) == (False, 0)
        else:
            assert (invert, decimals) == (True, 8), code


def test_mixed_case_addresses_carry_a_valid_checksum():
    """A mixed-case address that fails EIP-55 is a typo, not another address."""
    for name, value in _named_addresses().items():
        body = value[2:]
        if body == body.lower() or body == body.upper():
            continue  # no checksum encoded, nothing to verify
        assert is_checksum_address(value), f"{name} = {value} is not EIP-55 checksummed"
