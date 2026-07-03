from __future__ import annotations

from account.constants import (
    GLOBAL_NOTIFICATION_CACHE_KEY,
    GLOBAL_NOTIFICATION_CACHE_TIMEOUT,
    OTP_CODE_LENGTH,
    OTP_EXPIRATION_MINUTES,
    OTP_REQUEST_COOLDOWN_SECONDS,
    SESSION_PASSWORD_RESET_TOKEN_KEY,
    SESSION_PHONE_CHANGE_TOKEN_KEY,
    SESSION_PHONE_CHANGE_VALUE_KEY,
    SMS_BROADCAST_CHUNK_SIZE,
)
from account.exceptions import (
    AccountException,
    AuthenticationException,
    ExpiredOtpException,
    InvalidOtpException,
    OTPException,
    OTPRateLimitExceededException,
    PasswordResetException,
    PhoneAlreadyExistsException,
    SessionValidationException,
    SMSProviderException,
)
from account.services.sms_service import GhasedakSMSProvider, SmsService, get_sms_client

__all__ = [
    "AccountException",
    "AuthenticationException",
    "ExpiredOtpException",
    "InvalidOtpException",
    "OTPException",
    "OTP_REQUEST_COOLDOWN_SECONDS",
    "OTPRateLimitExceededException",
    "PasswordResetException",
    "PhoneAlreadyExistsException",
    "SessionValidationException",
    "SMSProviderException",
    "GhasedakSMSProvider",
    "get_sms_client",
    "SmsService",
    "create_and_send_otp",
    "get_valid_otp",
    "send_notification_sms_broadcast",
    "AuthService",
    "OTPService",
    "PasswordService",
    "ProfileService",
    "SessionService",
    "NotificationService",
]


def __getattr__(name: str):
    if name == "AuthService":
        from account.services.auth_service import AuthService

        return AuthService
    if name == "OTPService":
        from account.services.otp_service import OTPService

        return OTPService
    if name == "PasswordService":
        from account.services.password_service import PasswordService

        return PasswordService
    if name == "ProfileService":
        from account.services.profile_service import ProfileService

        return ProfileService
    if name == "SessionService":
        from account.services.session_service import SessionService

        return SessionService
    if name == "NotificationService":
        from account.services.notification_service import NotificationService

        return NotificationService
    raise AttributeError(name)


def create_and_send_otp(phone: str) -> str:
    from account.services.otp_service import OTPService

    return OTPService().create_otp(phone).token


def get_valid_otp(*, token: str, code: int):
    from account.services.otp_service import OTPService

    return OTPService().validate_otp(token=token, code=code)


def send_notification_sms_broadcast(notification):
    from account.services.notification_service import NotificationService

    return NotificationService().send_sms_broadcast(notification)
