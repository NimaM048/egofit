from __future__ import annotations

from account.constants import SMS_BROADCAST_CHUNK_SIZE
from account.exceptions import SMSProviderException
from account.interfaces import PersonalizedSmsMessage
from account.repositories.notification_repository import NotificationRepository
from account.selectors.notification_selector import NotificationSelector
from account.selectors.user_selector import UserSelector
from account.services.sms_service import SmsService
from account.utils import build_notification_sms_message, iter_chunks, normalize_phone_number


class NotificationService:
    def __init__(
        self,
        *,
        repository: NotificationRepository | None = None,
        sms_service: SmsService | None = None,
    ):
        self.repository = repository or NotificationRepository()
        self.sms_service = sms_service or SmsService()

    def create_course_request_notification(self, *, user, course_title: str):
        return self.repository.create_course_request_notification(user=user, course_title=course_title)

    def get_profile_notifications(self, user, *, limit: int = 20):
        return NotificationSelector.get_profile_notifications(user, limit=limit)

    def get_dashboard_notifications(self, user, *, limit: int = 3):
        return NotificationSelector.get_dashboard_notifications(user, limit=limit)

    def get_notifications_count(self, user) -> int:
        return NotificationSelector.get_notifications_count(user)

    def send_sms_broadcast(self, notification):
        if not notification.is_global or not notification.send_sms_to_all:
            self.repository.mark_sms_not_requested(notification)
            return 0

        recipients_queryset = UserSelector.get_active_sms_recipients()
        if not recipients_queryset.exists():
            self.repository.mark_sms_failed(
                notification,
                recipients_count=0,
                error="کاربر فعالی با شماره تماس ثبت‌شده برای ارسال پیامک پیدا نشد.",
            )
            return 0

        recipients: list[PersonalizedSmsMessage] = []
        for user in recipients_queryset.iterator(chunk_size=SMS_BROADCAST_CHUNK_SIZE):
            phone = normalize_phone_number(getattr(user, "phone", None))
            if len(phone) != 11 or not phone.isdigit():
                continue

            recipient_name = (getattr(user, "fullname", "") or "").strip()
            recipients.append(
                PersonalizedSmsMessage(
                    receptor=phone,
                    message=build_notification_sms_message(notification, recipient_name=recipient_name),
                )
            )

        if not recipients:
            self.repository.mark_sms_failed(
                notification,
                recipients_count=0,
                error="کاربر فعالی با شماره تماس معتبر برای ارسال پیامک پیدا نشد.",
            )
            return 0

        self.repository.mark_sms_pending(notification)

        sent_count = 0
        try:
            for chunk in iter_chunks(recipients, SMS_BROADCAST_CHUNK_SIZE):
                is_sent = self.sms_service.send_personalized_bulk_sms(chunk)
                if not is_sent:
                    raise SMSProviderException("پنل پیامکی پاسخ موفق برای ارسال گروهی برنگرداند.")
                sent_count += len(chunk)
        except Exception as exc:
            self.repository.mark_sms_failed(notification, recipients_count=sent_count, error=str(exc))
            raise

        self.repository.mark_sms_sent(notification, recipients_count=sent_count)
        return sent_count

    def send_sms_broadcast_by_id(self, notification_id: int):
        notification = self.repository.get_by_id(notification_id)
        return self.send_sms_broadcast(notification)
