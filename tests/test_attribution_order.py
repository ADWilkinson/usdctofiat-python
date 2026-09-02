"""The attribution code order is pinned to a deposit live on Base.

Every other assertion on the codes compares the encoding back to the constants
that produced it, so the reversed order shipped green in 0.1.0: the client led
with peer-ref-TOFIAT, which is the slot the indexer reads a deposit's
attributionSource from and which no live deposit gives to a marker. This pin is
the check that does not derive from the constants under test.
"""

from usdctofiat import create_offramp, lock_attribution, parse_erc8021
from usdctofiat.attribution import append_attribution
from usdctofiat.constants import DISTRIBUTION_REFERRER, PEER_REF

# EscrowV2 deposit 3832, tx 0xad037cf0e4be042c66f902e50ed36cb3abfc84a8c1160324d2449c0c2bab9662,
# created by @usdctofiat/offramp. The ERC-8021 suffix as it sits in the calldata:
# codes || codesLength || schemaId || marker. The trailing bc_* is the builder's
# own code, appended after the client's, and is not ours to emit.
LIVE_SUFFIX = bytes.fromhex(
    "67616c6c656f6e6c6162732c706565722d7265662d544f464941542c62635f6e626e36716b6e69"
    "270080218021802180218021802180218021"
)
LIVE_CODES = ("galleonlabs", "peer-ref-TOFIAT", "bc_nbn6qkni")


def test_live_suffix_decodes_to_the_published_order():
    """Sanity: the pin really is what Base carries, read with our own parser."""
    assert parse_erc8021(b"0xdead" + LIVE_SUFFIX) == LIVE_CODES


def test_client_emits_the_live_source_then_marker_order():
    codes = lock_attribution().codes
    assert codes == LIVE_CODES[:2]
    assert codes[0] == DISTRIBUTION_REFERRER
    assert codes[1] == PEER_REF


def test_source_slot_never_holds_a_referral_marker():
    """codes[0] is the indexer's attributionSource. A peer-ref-* there is unreadable."""
    for attribution in (
        lock_attribution(),
        lock_attribution(extra_referrers=["my-wallet", "analytics"]),
        lock_attribution(referral_code="HACKED", referrers=["peer-ref-RIVAL", "peer-cash"]),
        create_offramp(referrer="my-wallet").attribution,
    ):
        assert not attribution.codes[0].startswith("peer-ref-")
        assert attribution.codes[0] == DISTRIBUTION_REFERRER
        assert attribution.codes.count(PEER_REF) == 1


def test_encoded_calldata_leads_with_the_source():
    approve = append_attribution("0x095ea7b3", lock_attribution(extra_referrers=["my-wallet"]))
    assert parse_erc8021(approve) == (DISTRIBUTION_REFERRER, PEER_REF, "my-wallet")
