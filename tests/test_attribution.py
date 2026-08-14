
from usdctofiat import create_offramp, lock_attribution, parse_erc8021
from usdctofiat.attribution import append_attribution, erc8021_suffix
from usdctofiat.constants import DISTRIBUTION_REFERRER, PEER_REF, REFERRAL_CODE


def test_lock_discards_inbound_referral_code_and_peer_ref():
    attr = lock_attribution(
        referral_code="HACKED",
        referrers=["peer-ref-RIVAL", "peer-cash", "my-wallet", "galleonlabs", "TOFIAT"],
    )
    assert attr.referral_code == REFERRAL_CODE
    assert attr.referrers == (DISTRIBUTION_REFERRER, "my-wallet")
    assert attr.codes[0] == PEER_REF
    assert attr.codes[1] == DISTRIBUTION_REFERRER


def test_create_offramp_discards_referral_kwargs():
    client = create_offramp(referral_code="XXXXXX", referrer="peer-ref-OTHER", extra_referrers=["analytics"])
    assert client.attribution.referral_code == "TOFIAT"
    assert client.attribution.referrers == ("galleonlabs", "analytics")


def test_erc8021_suffix_is_schema_0_and_parseable():
    attr = lock_attribution(extra_referrers=["my-wallet"])
    suffix = erc8021_suffix(attr)
    assert suffix.endswith(bytes.fromhex("80218021802180218021802180218021"))
    assert suffix[-17] == 0  # schema id
    codes = parse_erc8021(b"0xdead" + suffix)
    assert codes == ("peer-ref-TOFIAT", "galleonlabs", "my-wallet")


def test_append_attribution_keeps_calldata_prefix():
    out = append_attribution("0x095ea7b3")
    assert out.startswith("0x095ea7b3")
    assert parse_erc8021(out)[0] == "peer-ref-TOFIAT"
