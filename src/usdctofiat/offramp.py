
"""cashout(mode=fast|best) and create_offramp(). No keys. No POST /cashout."""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any, Iterator

from .attribution import lock_attribution
from .calldata import (
    access_policy_required,
    approve_tx,
    create_deposit_tx,
    delegate_hook,
    extract_deposit_id,
    extract_tx_hash,
    normalize_payee,
    parse_usdc_amount,
    set_rate_manager_tx,
    withdraw_tx,
)
from .constants import (
    BASE_RPC_URL,
    BEST_MANAGER_FEE_BPS,
    CURATOR_URL,
    FAST_SPREAD_BPS,
    INDEXER_URL,
    MODES,
    USDC_UNITS,
)
from .curator import Curator
from .errors import ModeRequired, SignerRequired, ValidationError
from .indexer import Indexer
from .oracle import Oracle
from .types import CashoutResult, Estimate, PreparedCashout, Signer, UnsignedTx


class Offramp:
    """USDCtoFiat client. Attribution is locked at construction."""

    def __init__(
        self,
        *,
        curator_url: str = CURATOR_URL,
        indexer_url: str = INDEXER_URL,
        rpc_url: str = BASE_RPC_URL,
        curator: Curator | None = None,
        indexer: Indexer | None = None,
        oracle: Oracle | None = None,
        referrer: str | None = None,
        referrers: list[str] | None = None,
        extra_referrers: list[str] | None = None,
        referral_code: str | None = None,
        **ignored: object,
    ) -> None:
        for banned in ("private_key", "privateKey", "key", "secret", "mnemonic", "wallet_key"):
            if banned in ignored:
                raise TypeError(
                    "usdctofiat does not accept a private key. Pass a signer callback or call prepare()."
                )
        # Discard inbound referral_code / peer-ref-* / reserved names.
        self.attribution = lock_attribution(
            referral_code=referral_code,
            referrer=referrer,
            referrers=referrers,
            extra_referrers=extra_referrers,
            **ignored,
        )
        self.curator = curator or Curator(curator_url)
        self.indexer = indexer or Indexer(indexer_url)
        self.oracle = oracle or Oracle(rpc_url)

    def prepare(
        self,
        *,
        mode: str | None = None,
        amount: object,
        currency: str,
        platform: str,
        payee: str,
        payee_details_hash: str | None = None,
        **_: object,
    ) -> PreparedCashout:
        resolved = _require_mode(mode)
        units = parse_usdc_amount(amount)
        platform_key = platform.strip().lower()
        currency_key = currency.strip().upper()
        handle = normalize_payee(platform_key, payee)
        digest = payee_details_hash or self.curator.create_payee_hash(platform=platform_key, payee=handle)
        txs = [
            approve_tx(units, attribution=self.attribution),
            create_deposit_tx(
                amount_units=units,
                payee_details_hash=digest,
                platform=platform_key,
                currency=currency_key,
                mode=resolved,
                attribution=self.attribution,
            ),
        ]
        steps = ["approve", "createDeposit"]
        hook = delegate_hook() if resolved == "best" else None
        if hook:
            steps = [*steps, "setRateManager"]
        return PreparedCashout(
            mode=resolved,  # type: ignore[arg-type]
            txs=txs,
            steps=steps,
            payee_details_hash=digest,
            amount_units=units,
            platform=platform_key,
            currency=currency_key,
            attribution={"referral_code": self.attribution.referral_code, "referrers": list(self.attribution.referrers)},
            delegate_hook=hook,
            access_policy_required=access_policy_required(platform_key),
        )

    def cashout(
        self,
        *,
        mode: str | None = None,
        amount: object,
        currency: str,
        platform: str,
        payee: str,
        signer: Signer | None = None,
        **kwargs: object,
    ) -> CashoutResult:
        if signer is None:
            raise SignerRequired()
        prepared = self.prepare(
            mode=mode,
            amount=amount,
            currency=currency,
            platform=platform,
            payee=payee,
            **kwargs,
        )
        hashes: list[str] = []
        deposit_id: str | None = None
        last: str | None = None
        for tx in prepared.txs:
            result = signer(tx)
            tx_hash = extract_tx_hash(result)
            if tx_hash:
                last = tx_hash
                hashes.append(tx_hash)
            deposit_id = deposit_id or extract_deposit_id(result)
        return CashoutResult(
            deposit_id=deposit_id,
            tx_hash=last,
            mode=prepared.mode,
            tx_hashes=hashes,
            prepared=prepared,
            delegate_hook=prepared.delegate_hook,
        )

    def estimate(self, *, mode: str | None = None, amount: object, currency: str, **_: object) -> Estimate:
        """Price the cash-out off the currency's Chainlink feed. Not a locked quote.

        The rate is read live: a fixed 1:1 would misquote every non-USD currency
        by the whole FX rate. USD is the zero-address passthrough and needs no read.
        """
        resolved = _require_mode(mode)
        units = parse_usdc_amount(amount)
        quote = self.oracle.rate(currency)
        fee = BEST_MANAGER_FEE_BPS if resolved == "best" else 0
        # Fast: 0 bps seller spread. Best: 10 bps taken from released USDC, not seller fiat.
        return Estimate(
            mode=resolved,  # type: ignore[arg-type]
            amount_units=units,
            currency=quote.currency,
            rate=_decimal_str(quote.rate),
            receive_amount=_decimal_str(Decimal(units) / USDC_UNITS * quote.rate),
            spread_bps=FAST_SPREAD_BPS,
            manager_fee_bps=fee,
            as_of=quote.as_of,
            oracle_updated_at=quote.updated_at,
            stale=quote.stale,
        )

    def deposits(self, owner: str) -> list[dict[str, Any]]:
        return self.indexer.deposits(owner)

    def watch(self, deposit_id: str) -> Iterator[dict[str, Any]]:
        return self.indexer.watch(deposit_id)

    def withdraw(self, deposit_id: int | str, *, signer: Signer | None = None) -> CashoutResult | UnsignedTx:
        tx = withdraw_tx(int(deposit_id), attribution=self.attribution)
        if signer is None:
            return tx
        tx_hash = extract_tx_hash(signer(tx))
        return CashoutResult(deposit_id=str(deposit_id), tx_hash=tx_hash, mode="fast", tx_hashes=[tx_hash] if tx_hash else [])

    close = withdraw

    def encode_delegate_hook(self, deposit_id: int | str, *, rate_manager_id: str) -> UnsignedTx:
        """Best follow-up once the EscrowV2 id is known."""
        return set_rate_manager_tx(int(deposit_id), rate_manager_id=rate_manager_id, attribution=self.attribution)


def create_offramp(**kwargs: object) -> Offramp:
    """Factory. Locks TOFIAT + galleonlabs. Discards inbound referral_code / peer-ref-*."""
    return Offramp(**kwargs)  # type: ignore[arg-type]


def cashout(
    *,
    mode: str | None = None,
    amount: object,
    currency: str,
    platform: str,
    payee: str,
    signer: Signer | None = None,
    **kwargs: object,
) -> CashoutResult:
    client_kwargs = {
        key: kwargs.pop(key)
        for key in ("curator_url", "indexer_url", "rpc_url", "curator", "indexer", "oracle", "referrer", "referrers", "extra_referrers", "referral_code")
        if key in kwargs
    }
    return create_offramp(**client_kwargs).cashout(
        mode=mode,
        amount=amount,
        currency=currency,
        platform=platform,
        payee=payee,
        signer=signer,
        **kwargs,
    )


def _require_mode(mode: str | None) -> str:
    if mode is None or str(mode).strip() == "":
        raise ModeRequired()
    key = str(mode).strip().lower()
    if key not in MODES:
        raise ModeRequired()
    return key


ESTIMATE_PRECISION = Decimal("0.000001")


def _decimal_str(value: Decimal) -> str:
    """Six decimal places, trailing zeros dropped. Feed rates do not terminate."""
    with localcontext() as ctx:
        # An int amount is unbounded, so give the quantize room rather than raising.
        ctx.prec = 64
        text = format(value.quantize(ESTIMATE_PRECISION), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text
