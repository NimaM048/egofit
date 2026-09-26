from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from cart.constants import PAYMENT_DESCRIPTION
from cart.exceptions import PaymentProviderException, PaymentVerificationException
from cart.providers.zarinpal_provider import ZarinPalPaymentProvider
from cart.repositories.order_repository import OrderRepository


@dataclass
class PaymentCallbackResult:
    order: object | None
    state: str
    message: str | None = None
    ref_id: str | None = None

    @property
    def is_success(self) -> bool:
        return self.state == "paid"

    @property
    def is_already_paid(self) -> bool:
        return self.state == "already_paid"

    @property
    def is_missing_order(self) -> bool:
        return self.state == "missing_order"


class PaymentService:
    def __init__(self, repository: OrderRepository | None = None, provider: ZarinPalPaymentProvider | None = None):
        self.repository = repository or OrderRepository()
        self.provider = provider or ZarinPalPaymentProvider()

    @transaction.atomic
    def initiate_payment(self, *, order, callback_url: str) -> str:
        locked_order = self.repository.get_order_for_user(order_id=order.id, user=order.user, lock=True)
        if locked_order is None:
            raise PaymentProviderException(_("سفارش مورد نظر پیدا نشد."))

        if locked_order.is_paid:
            raise PaymentProviderException(_("این سفارش قبلا پرداخت شده است."))

        if locked_order.total_price <= 0:
            raise PaymentProviderException(_("مبلغ سفارش نامعتبر است."))

        user = locked_order.user
        attempt = self.repository.create_payment_attempt(order=locked_order)
        result = self.provider.request_payment(
            amount=locked_order.total_price,
            callback_url=callback_url,
            description=f"{PAYMENT_DESCRIPTION} - سفارش {locked_order.order_number}",
            mobile=getattr(user, "phone", None),
            email=getattr(user, "email", None) or None,
        )
        self.repository.mark_attempt_initiated(
            order=locked_order,
            attempt=attempt,
            authority=result.authority,
        )
        return result.redirect_url

    @transaction.atomic
    def verify_callback(self, *, authority: str, status: str) -> PaymentCallbackResult:
        attempt = self.repository.get_payment_attempt_by_authority(authority=authority, lock=True)
        if attempt is not None:
            order = self.repository.get_order_for_user(
                order_id=attempt.order_id,
                user=attempt.order.user,
                lock=True,
            )
        else:
            # Keep callbacks for orders created before payment attempts were
            # introduced verifiable during the rollout.
            order = self.repository.get_order_by_authority(authority=authority, lock=True)

        if order is None:
            return PaymentCallbackResult(order=None, state="missing_order", message=_("سفارش منتظر با این پرداخت پیدا نشد."))

        if order.is_paid:
            return PaymentCallbackResult(order=order, state="already_paid", ref_id=order.ref_id)

        if status != "OK":
            if attempt is not None:
                self.repository.mark_attempt_failed(attempt=attempt)
            if order.authority == authority:
                self.repository.mark_failed(order=order)
            return PaymentCallbackResult(order=order, state="failed", message=_("تراکنش ناموفق بود یا توسط کاربر لغو شد."))

        try:
            verification = self.provider.verify_payment(
                amount=attempt.amount if attempt is not None else order.total_price,
                authority=authority,
            )
        except PaymentVerificationException as exc:
            if attempt is not None:
                self.repository.mark_attempt_failed(attempt=attempt)
            if order.authority == authority:
                self.repository.mark_failed(order=order)
            return PaymentCallbackResult(order=order, state="failed", message=str(exc))

        if verification.success:
            if attempt is not None:
                self.repository.mark_attempt_paid(attempt=attempt, ref_id=verification.ref_id)
            self.repository.mark_paid(order=order, ref_id=verification.ref_id)
            return PaymentCallbackResult(order=order, state="paid", ref_id=verification.ref_id)

        if attempt is not None:
            self.repository.mark_attempt_failed(attempt=attempt)
        if order.authority == authority:
            self.repository.mark_failed(order=order)
        return PaymentCallbackResult(order=order, state="failed", message=verification.message)
