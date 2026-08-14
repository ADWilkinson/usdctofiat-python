"""Typed errors. No private-key construction lives in this package."""

from __future__ import annotations


class UsdctoFiatError(Exception):
    """Base error for the USDCtoFiat Python client."""

    def __init__(self, message: str, *, code: str = "USDCTOFIAT", details: object | None = None):
        super().__init__(message)
        self.code = code
        self.details = details


class ValidationError(UsdctoFiatError):
    def __init__(self, message: str, field: str | None = None, details: object | None = None):
        super().__init__(message, code="VALIDATION", details=details)
        self.field = field


class ModeRequired(ValidationError):
    def __init__(self) -> None:
        super().__init__(
            'mode is required: pass mode="fast" (0% / TOFIAT) or mode="best" (Delegate, 10 bps)',
            field="mode",
        )


class SignerRequired(UsdctoFiatError):
    def __init__(self) -> None:
        super().__init__(
            "cashout() needs a signer callback, or call prepare() for unsigned txs. "
            "This client does not accept a private key.",
            code="SIGNER_REQUIRED",
        )


class PayeeVerificationRequired(UsdctoFiatError):
    def __init__(self, platform: str) -> None:
        super().__init__(
            f"{platform} needs a Peer-extension identity attestation this client cannot mint. "
            "Register the handle first, then retry with the same payee.",
            code="PAYEE_VERIFICATION_REQUIRED",
            details={"platform": platform},
        )


class CuratorError(UsdctoFiatError):
    def __init__(self, message: str, status: int | None = None, details: object | None = None):
        super().__init__(message, code="CURATOR", details=details)
        self.status = status


class IndexerError(UsdctoFiatError):
    def __init__(self, message: str, details: object | None = None):
        super().__init__(message, code="INDEXER", details=details)
