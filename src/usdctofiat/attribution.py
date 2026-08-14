"""ERC-8021 attribution lock: peer-ref-TOFIAT then galleonlabs.

Callers may append extra analytics referrers after those two. They cannot
replace them. Inbound referral_code and peer-ref-* values are discarded.
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    DISTRIBUTION_REFERRER,
    ERC8021_MARKER,
    PEER_REF,
    REFERRAL_CODE,
    RESERVED_REFERRERS,
)


@dataclass(frozen=True)
class Attribution:
    referral_code: str
    referrers: tuple[str, ...]

    @property
    def codes(self) -> tuple[str, ...]:
        return (PEER_REF, *self.referrers)


def _is_competing_referral(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered in RESERVED_REFERRERS:
        return True
    if lowered == REFERRAL_CODE.lower():
        return True
    if lowered == DISTRIBUTION_REFERRER:
        return True
    if lowered.startswith("peer-ref-"):
        return True
    return False


def lock_attribution(
    *,
    referral_code: str | None = None,
    referrer: str | None = None,
    referrers: list[str] | tuple[str, ...] | None = None,
    extra_referrers: list[str] | tuple[str, ...] | None = None,
    **_ignored: object,
) -> Attribution:
    """Always TOFIAT + galleonlabs. Discard inbound referral_code / peer-ref-*."""
    extras: list[str] = []
    for group in (referrers, extra_referrers, [referrer] if referrer else []):
        if not group:
            continue
        for item in group:
            if item is None:
                continue
            text = str(item).strip()
            if not text or _is_competing_referral(text):
                continue
            if text not in extras:
                extras.append(text)
    # inbound referral_code is accepted only as documentation that we saw it;
    # it is never applied.
    _ = referral_code
    return Attribution(referral_code=REFERRAL_CODE, referrers=(DISTRIBUTION_REFERRER, *extras))


def erc8021_suffix(attribution: Attribution | None = None, **kwargs: object) -> bytes:
    """Schema 0 suffix: codes || codesLength || schemaId || 16-byte marker."""
    attr = attribution or lock_attribution(**kwargs)
    codes = ",".join(attr.codes).encode("ascii")
    if len(codes) > 255:
        raise ValueError("ERC-8021 codes exceed 255 bytes")
    return codes + bytes([len(codes), 0x00]) + ERC8021_MARKER


def append_attribution(data: str | bytes, attribution: Attribution | None = None, **kwargs: object) -> str:
    raw = _as_bytes(data)
    suffix = erc8021_suffix(attribution, **kwargs)
    return "0x" + (raw + suffix).hex()


def parse_erc8021(data: str | bytes) -> tuple[str, ...]:
    raw = _as_bytes(data)
    if len(raw) < 18 or raw[-16:] != ERC8021_MARKER:
        raise ValueError("missing ERC-8021 marker")
    schema_id = raw[-17]
    if schema_id != 0:
        raise ValueError(f"unsupported ERC-8021 schema {schema_id}")
    codes_len = raw[-18]
    codes = raw[-(18 + codes_len) : -18]
    if len(codes) != codes_len:
        raise ValueError("truncated ERC-8021 codes")
    text = codes.decode("ascii")
    return tuple(part for part in text.split(",") if part)


def _as_bytes(data: str | bytes) -> bytes:
    if isinstance(data, bytes):
        return data[2:] if data.startswith(b"0x") else data
    text = data[2:] if data.startswith("0x") else data
    return bytes.fromhex(text)
