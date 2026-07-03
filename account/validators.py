from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from account.utils import normalize_phone_number

PHONE_NUMBER_VALIDATOR = RegexValidator(
    regex=r"^\d{11}$",
    message=_("شماره تلفن باید 11 رقم باشد."),
    code="invalid_phone_number",
)

OTP_CODE_VALIDATOR = RegexValidator(
    regex=r"^\d{5}$",
    message=_("لطفا کد 5 رقمی وارد کنید."),
    code="invalid_otp_code",
)


def validate_phone_number(value: str | None) -> str:
    phone = normalize_phone_number(value)
    if not re.match(r"^\d{11}$", phone):
        raise ValidationError(_("لطفا یک شماره تماس 11 رقمی وارد کنید."))
    return phone


def validate_fullname(value: str | None) -> str:
    fullname = (value or "").strip()
    if not fullname:
        raise ValidationError(_("لطفا نام کاربری خود را وارد کنید."))
    if not fullname.isalnum():
        raise ValidationError(_("نام کاربری باید فقط شامل حروف و اعداد باشد."))
    return fullname


def validate_strong_password(value: str | None) -> str:
    password = value or ""
    if len(password) < 8:
        raise ValidationError(_("رمز عبور باید حداقل 8 کاراکتر داشته باشد."))
    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$", password):
        raise ValidationError(_("رمز عبور باید شامل حرف کوچک، حرف بزرگ و عدد باشد."))
    return password

