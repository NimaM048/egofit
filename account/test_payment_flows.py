"""End-to-end checks for the three Zarinpal payment entry points.

Each flow runs through the real views, services and Zarinpal provider; only
the HTTP call to Zarinpal is faked.  The scenario mirrors what users do in
production: start a payment, abandon the gateway, start again, cancel on the
gateway, start again and finally pay.
"""

from __future__ import annotations

from random import randint
from unittest.mock import patch
from urllib.parse import urlencode

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from account import views as account_views
from account.models import ClientDocument, ClientDocumentPayment, User, WorkoutProgram, WorkoutProgramPayment
from cart import views as cart_views
from cart.models import Order, OrderPaymentAttempt
from home.models import Category, SeriesModel

PUBLIC_BASE_URL = "https://egofit.ir"
MERCHANT_ID = "00000000-0000-0000-0000-000000000000"


class FakeZarinpalResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


class FakeZarinpal:
    """Stands in for ``requests.post`` against the Zarinpal v4 API."""

    def __init__(self):
        self.requests = []
        self.verifies = []

    def __call__(self, url, json=None, **kwargs):
        if url.endswith("/request.json"):
            self.requests.append(json)
            authority = f"A{len(self.requests):035d}"
            return FakeZarinpalResponse({"data": {"code": 100, "authority": authority}, "errors": []})
        if url.endswith("/verify.json"):
            self.verifies.append(json)
            return FakeZarinpalResponse({"data": {"code": 100, "ref_id": 987654}, "errors": []})
        raise AssertionError(f"Unexpected Zarinpal URL: {url}")

    @property
    def last_authority(self):
        return f"A{len(self.requests):035d}"


@override_settings(LIARA_PUBLIC_BASE_URL=PUBLIC_BASE_URL, SANDBOX=False, MERCHANT=MERCHANT_ID)
class PaymentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            fullname="Payment Flow User",
            phone=f"0912{randint(0, 9_999_999):07d}",
            password="StrongPass123",
        )
        self.admin = User.objects.create_superuser(
            fullname="Payment Flow Admin",
            phone=f"0935{randint(0, 9_999_999):07d}",
            password="StrongPass123",
        )
        self.zarinpal = FakeZarinpal()
        post_patch = patch("cart.providers.zarinpal_provider.requests.post", side_effect=self.zarinpal)
        post_patch.start()
        self.addCleanup(post_patch.stop)

        # The view modules build their providers at import time, before the
        # settings override is active.
        for provider in (cart_views.payment_service.provider, account_views.access_payment_service.provider):
            for attr, value in (("merchant_id", MERCHANT_ID), ("sandbox", False)):
                attr_patch = patch.object(provider, attr, value)
                attr_patch.start()
                self.addCleanup(attr_patch.stop)

        self.client.force_login(self.user)

    def _start_payment(self, pay_url, expected_callback_path, expected_amount):
        response = self.client.post(pay_url)
        authority = self.zarinpal.last_authority
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"https://www.zarinpal.com/pg/StartPay/{authority}")

        sent = self.zarinpal.requests[-1]
        self.assertEqual(sent["callback_url"], f"{PUBLIC_BASE_URL}{expected_callback_path}")
        self.assertEqual(sent["amount"], expected_amount)
        self.assertEqual(sent["currency"], "IRT")
        self.assertEqual(sent["merchant_id"], MERCHANT_ID)
        return authority

    def _callback(self, callback_path, authority, status):
        return self.client.get(f"{callback_path}?{urlencode({'Authority': authority, 'Status': status})}")

    def _run_retry_scenario(self, *, pay_url, callback_path, amount):
        abandoned = self._start_payment(pay_url, callback_path, amount)
        cancelled = self._start_payment(pay_url, callback_path, amount)
        self.assertNotEqual(abandoned, cancelled)

        self._callback(callback_path, cancelled, "NOK")
        self.assertEqual(self.zarinpal.verifies, [])

        paid = self._start_payment(pay_url, callback_path, amount)
        self.assertNotIn(paid, {abandoned, cancelled})
        self._callback(callback_path, paid, "OK")
        self.assertEqual(self.zarinpal.verifies[-1], {"merchant_id": MERCHANT_ID, "amount": amount, "authority": paid})
        return abandoned, cancelled, paid

    def _assert_admin_lists(self, changelist_url_name, authority):
        self.client.force_login(self.admin)
        response = self.client.get(reverse(changelist_url_name))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, authority)

    def test_course_order_payment_is_retryable_and_recorded(self):
        category = Category.objects.create(title="Flow category", slug="flow-category")
        with patch("home.services.series_service.SeriesService.create_series_notifications_on_commit"):
            series = SeriesModel.objects.create(
                title="Flow course",
                image="series_courses/series.jpg",
                is_compeleted=True,
                language_kinds=category,
                author=self.admin,
                main_price="150000",
                discount_price="120000",
                free=False,
                author_image="images/author.jpg",
            )
        self.client.post(reverse("cart:cart_add", args=[series.pk]))
        self.client.post(reverse("cart:order_create"))
        order = Order.objects.get(user=self.user)

        abandoned, cancelled, paid = self._run_retry_scenario(
            pay_url=reverse("cart:request", args=[order.pk]),
            callback_path=reverse("cart:verify"),
            amount=120000,
        )

        order.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(order.status, Order.PaymentStatus.PAID)
        self.assertEqual(order.authority, paid)
        self.assertEqual(order.ref_id, "987654")
        attempts = dict(order.payment_attempts.values_list("authority", "status"))
        self.assertEqual(
            attempts,
            {
                abandoned: OrderPaymentAttempt.Status.FAILED,
                cancelled: OrderPaymentAttempt.Status.FAILED,
                paid: OrderPaymentAttempt.Status.PAID,
            },
        )
        self._assert_admin_lists("admin:cart_order_changelist", order.order_number)

    def test_document_payment_is_retryable_and_recorded(self):
        document = ClientDocument.objects.create(
            user=self.user,
            uploaded_by=self.admin,
            title="Flow document",
            file=SimpleUploadedFile("flow.txt", b"protected"),
            requires_payment=True,
            price=90000,
        )
        download_url = reverse("register:profile_document_download", args=[document.pk])
        self.assertEqual(self.client.get(download_url).status_code, 302)

        abandoned, cancelled, paid = self._run_retry_scenario(
            pay_url=reverse("register:profile_document_pay", args=[document.pk]),
            callback_path=reverse("register:profile_document_verify"),
            amount=90000,
        )

        statuses = dict(ClientDocumentPayment.objects.filter(document=document).values_list("authority", "status"))
        self.assertEqual(
            statuses,
            {
                abandoned: ClientDocumentPayment.Status.FAILED,
                cancelled: ClientDocumentPayment.Status.FAILED,
                paid: ClientDocumentPayment.Status.PAID,
            },
        )
        payment = ClientDocumentPayment.objects.get(authority=paid)
        self.assertEqual(payment.ref_id, "987654")
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(self.client.get(download_url).status_code, 200)
        self._assert_admin_lists("admin:account_clientdocumentpayment_changelist", paid)

    def test_workout_program_payment_is_retryable_and_recorded(self):
        program = WorkoutProgram.objects.create(
            user=self.user,
            title="Flow program",
            is_published=True,
            requires_payment=True,
            price=240000,
        )
        self.assertFalse(account_views._has_workout_program_access(self.user, program))

        abandoned, cancelled, paid = self._run_retry_scenario(
            pay_url=reverse("register:profile_workout_program_pay", args=[program.pk]),
            callback_path=reverse("register:profile_workout_program_verify"),
            amount=240000,
        )

        statuses = dict(WorkoutProgramPayment.objects.filter(program=program).values_list("authority", "status"))
        self.assertEqual(
            statuses,
            {
                abandoned: WorkoutProgramPayment.Status.FAILED,
                cancelled: WorkoutProgramPayment.Status.FAILED,
                paid: WorkoutProgramPayment.Status.PAID,
            },
        )
        payment = WorkoutProgramPayment.objects.get(authority=paid)
        self.assertEqual(payment.ref_id, "987654")
        self.assertIsNotNone(payment.paid_at)
        self.assertTrue(account_views._has_workout_program_access(self.user, program))
        self._assert_admin_lists("admin:account_workoutprogrampayment_changelist", paid)

    def test_each_section_sends_its_own_callback_address(self):
        callbacks = {
            reverse("cart:verify"),
            reverse("register:profile_document_verify"),
            reverse("register:profile_workout_program_verify"),
        }
        self.assertEqual(len(callbacks), 3)
