
"""USDCtoFiat by Galleon Labs.

Python client for non-custodial USDC-to-fiat cash-out on Base.
Built on the public Peer/ZKP2P protocol. Not a Peer Cash product.

cashout(mode="fast"|"best") is required. Fast is 0% / TOFIAT. Best is Delegate, 10 bps.
create_offramp() locks galleonlabs then peer-ref-TOFIAT. No private keys.
"""

from .attribution import Attribution, append_attribution, erc8021_suffix, lock_attribution, parse_erc8021
from .constants import (
    BEST_MANAGER_FEE_BPS,
    CHAIN_ID,
    DISTRIBUTION_REFERRER,
    ESCROW_V2,
    FAST_SPREAD_BPS,
    PEER_REF,
    PRODUCT,
    REFERRAL_CODE,
    SITE,
    USDC,
    VENDOR,
)
from .errors import (
    CuratorError,
    ModeRequired,
    OracleError,
    PayeeVerificationRequired,
    SignerRequired,
    UsdctoFiatError,
    ValidationError,
)
from .offramp import Offramp, cashout, create_offramp
from .oracle import Oracle, OracleRate
from .types import CashoutResult, DelegateHook, Estimate, PreparedCashout, UnsignedTx

__all__ = [
    "Attribution",
    "BEST_MANAGER_FEE_BPS",
    "CHAIN_ID",
    "CashoutResult",
    "CuratorError",
    "DISTRIBUTION_REFERRER",
    "DelegateHook",
    "ESCROW_V2",
    "Estimate",
    "FAST_SPREAD_BPS",
    "ModeRequired",
    "Offramp",
    "Oracle",
    "OracleError",
    "OracleRate",
    "PEER_REF",
    "PRODUCT",
    "PayeeVerificationRequired",
    "PreparedCashout",
    "REFERRAL_CODE",
    "SITE",
    "SignerRequired",
    "USDC",
    "UnsignedTx",
    "UsdctoFiatError",
    "VENDOR",
    "ValidationError",
    "append_attribution",
    "cashout",
    "create_offramp",
    "erc8021_suffix",
    "lock_attribution",
    "parse_erc8021",
]

__version__ = "0.1.1"
