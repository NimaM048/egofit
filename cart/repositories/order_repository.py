from __future__ import annotations

from django.utils import timezone

from cart.models import Order, OrderItem, OrderPaymentAttempt


class OrderRepository:
    def create_order(self, *, user, subtotal_price: int, course=None) -> Order:
        return Order.objects.create(
            user=user,
            subtotal_price=subtotal_price,
            total_price=subtotal_price,
            course=course,
        )

    def bulk_create_items(self, *, order: Order, items: list[dict]) -> None:
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=item["product"],
                    price=item["price"],
                )
                for item in items
            ]
        )

    def get_order_for_user(self, *, order_id: int, user, is_paid: bool | None = None, lock: bool = False):
        queryset = Order.objects.select_related("user", "course", "applied_discount_code")
        if lock:
            queryset = queryset.select_for_update()
        queryset = queryset.prefetch_related("items__product").filter(id=order_id, user=user)
        if is_paid is not None:
            queryset = queryset.filter(is_paid=is_paid)
        return queryset.first()

    def get_order_by_authority(self, *, authority: str, lock: bool = False):
        queryset = Order.objects.select_related("user", "course", "applied_discount_code")
        if lock:
            queryset = queryset.select_for_update()
        return queryset.prefetch_related("items__product").filter(authority=authority).first()

    def create_payment_attempt(self, *, order: Order) -> OrderPaymentAttempt:
        # An earlier attempt the user abandoned at the gateway never gets a
        # callback. Its authority stays verifiable, so a late successful
        # callback still marks it paid.
        OrderPaymentAttempt.objects.filter(
            order=order,
            status=OrderPaymentAttempt.Status.INITIATED,
        ).update(status=OrderPaymentAttempt.Status.FAILED)
        return OrderPaymentAttempt.objects.create(order=order, amount=order.total_price)

    def get_payment_attempt_by_authority(self, *, authority: str, lock: bool = False):
        queryset = OrderPaymentAttempt.objects.select_related("order", "order__user")
        if lock:
            queryset = queryset.select_for_update()
        return queryset.filter(authority=authority).first()

    def mark_attempt_initiated(
        self,
        *,
        order: Order,
        attempt: OrderPaymentAttempt,
        authority: str,
    ) -> None:
        now = timezone.now()
        attempt.authority = authority
        attempt.status = OrderPaymentAttempt.Status.INITIATED
        attempt.initiated_at = now
        attempt.save(update_fields=["authority", "status", "initiated_at"])
        order.mark_payment_initiated(authority)

    def mark_attempt_failed(self, *, attempt: OrderPaymentAttempt) -> None:
        attempt.status = OrderPaymentAttempt.Status.FAILED
        attempt.save(update_fields=["status"])

    def mark_attempt_paid(self, *, attempt: OrderPaymentAttempt, ref_id: str | None = None) -> None:
        attempt.status = OrderPaymentAttempt.Status.PAID
        attempt.ref_id = str(ref_id or attempt.ref_id or "")
        attempt.paid_at = timezone.now()
        attempt.save(update_fields=["status", "ref_id", "paid_at"])

    def mark_payment_initiated(self, *, order: Order, authority: str) -> None:
        order.mark_payment_initiated(authority)

    def mark_paid(self, *, order: Order, ref_id: str | None = None) -> None:
        order.mark_paid(ref_id=ref_id)

    def mark_failed(self, *, order: Order) -> None:
        order.mark_failed()
