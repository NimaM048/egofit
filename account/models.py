from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

from account.utils import normalize_phone_number


class UserManager(BaseUserManager):
    _NON_MODEL_FIELDS = frozenset({"is_staff", "is_superuser"})

    def _strip_non_model_fields(self, extra_fields: dict) -> dict:
        return {key: value for key, value in extra_fields.items() if key not in self._NON_MODEL_FIELDS}

    def create_user(self, fullname, phone, password=None, **extra_fields):
        if not fullname:
            raise ValueError("Users must have a fullname")
        if not phone:
            raise ValueError("Users must have a phone number")

        normalized_phone = normalize_phone_number(phone)
        if len(normalized_phone) != 11 or not normalized_phone.isdigit():
            raise ValueError("Users must have a valid phone number")

        extra_fields = self._strip_non_model_fields(extra_fields)
        user = self.model(fullname=fullname.strip(), phone=normalized_phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, fullname, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_active", True)
        extra_fields = self._strip_non_model_fields(extra_fields)
        if password is None:
            raise ValueError("Superusers must have a password")

        normalized_phone = normalize_phone_number(phone)
        desired_fullname = fullname.strip()
        existing = self.filter(phone=normalized_phone).first()
        if existing is not None:
            if (
                desired_fullname != existing.fullname
                and self.filter(fullname=desired_fullname).exclude(pk=existing.pk).exists()
            ):
                raise ValueError("A user with that fullname already exists.")
            if desired_fullname != existing.fullname:
                existing.fullname = desired_fullname
            existing.is_admin = True
            existing.is_active = True
            existing.set_password(password)
            for key, value in extra_fields.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.save(using=self._db)
            return existing

        return self.create_user(fullname=fullname, phone=phone, password=password, **extra_fields)


class User(AbstractBaseUser):
    class BloodGroupChoices(models.TextChoices):
        O_POSITIVE = "O+", "O+"
        O_NEGATIVE = "O-", "O-"
        A_POSITIVE = "A+", "A+"
        A_NEGATIVE = "A-", "A-"
        B_POSITIVE = "B+", "B+"
        B_NEGATIVE = "B-", "B-"
        AB_POSITIVE = "AB+", "AB+"
        AB_NEGATIVE = "AB-", "AB-"

    class GenderChoices(models.TextChoices):
        MALE = "male", _("مرد")
        FEMALE = "female", _("زن")

    class ActivityLevelChoices(models.TextChoices):
        SEDENTARY = "sedentary", _("کم‌تحرک (کمتر از ۵۰۰۰ قدم در روز)")
        LOW_ACTIVE = "low_active", _("کم‌فعال (۵۰۰۰ تا ۷۵۰۰ قدم در روز)")
        MODERATE_ACTIVE = "moderate_active", _("نسبتاً فعال (۷۵۰۰ تا ۱۰۰۰۰ قدم در روز)")
        ACTIVE = "active", _("فعال (۱۰۰۰۰ تا ۱۲۵۰۰ قدم در روز)")
        HIGH_ACTIVE = "high_active", _("بسیار فعال (بیش از ۱۲۵۰۰ قدم در روز)")

    email = models.EmailField(
        verbose_name=_("آدرس ایمیل"),
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )
    biography = models.TextField(null=True, blank=True)
    first_name = models.CharField(max_length=60, blank=True, verbose_name=_("نام"))
    last_name = models.CharField(max_length=60, blank=True, verbose_name=_("نام خانوادگی"))
    fullname = models.CharField(max_length=50, verbose_name=_("نام کامل"), unique=True)
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=12, unique=True, verbose_name=_("شماره تلفن"), db_index=True)
    is_admin = models.BooleanField(default=False, verbose_name=_("ادمین"))
    birthday_date = models.IntegerField(null=True, blank=True)
    birth_date_jalali = models.CharField(max_length=10, null=True, blank=True, verbose_name=_("تاریخ تولد"))
    weight_kg = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, verbose_name=_("وزن (کیلوگرم)"))
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name=_("قد (سانتی‌متر)"))
    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroupChoices.choices,
        null=True,
        blank=True,
        verbose_name=_("گروه خونی"),
    )
    web_site = models.CharField(max_length=100, null=True, blank=True)
    github = models.CharField(max_length=100, null=True, blank=True)
    linkdin = models.CharField(max_length=100, null=True, blank=True)
    telegram = models.CharField(max_length=100, null=True, blank=True)
    profile_picture = models.FileField(
        upload_to="profile_pictures/",
        null=True,
        blank=True,
        verbose_name=_("عکس پروفایل"),
    )
    display_name = models.CharField(max_length=80, null=True, blank=True, verbose_name=_("نام نمایشی"))
    age = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("سن"))
    gender = models.CharField(
        max_length=10,
        choices=GenderChoices.choices,
        null=True,
        blank=True,
        verbose_name=_("جنسیت"),
    )
    activity_level = models.CharField(
        max_length=20,
        choices=ActivityLevelChoices.choices,
        null=True,
        blank=True,
        verbose_name=_("سطح فعالیت"),
    )
    coach = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="athletes",
        limit_choices_to={"is_admin": True},
        verbose_name=_("مربی"),
    )

    objects = UserManager()

    USERNAME_FIELD = "fullname"
    REQUIRED_FIELDS = ["phone"]

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["fullname"]),
        ]

    def __str__(self):
        return self.fullname

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin


class Otp(models.Model):
    token = models.CharField(max_length=200, null=True, db_index=True)
    phone = models.CharField(max_length=11, db_index=True)
    code = models.SmallIntegerField(db_index=True)
    exprision_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.phone

    class Meta:
        indexes = [
            models.Index(fields=["token", "code"]),
            models.Index(fields=["phone", "created_at"]),
            models.Index(fields=["created_at"]),
        ]


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.fullname} - {self.ip_address}"

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["session_key", "created_at"]),
        ]


class Notification(models.Model):
    class SmsStatus(models.TextChoices):
        NOT_REQUESTED = "not_requested", "درخواستی ثبت نشده"
        PENDING = "pending", "در انتظار ارسال"
        SENT = "sent", "ارسال شده"
        FAILED = "failed", "ناموفق"

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, verbose_name="عنوان")
    message = models.TextField(verbose_name="پیام")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    read = models.BooleanField(default=False, verbose_name="خوانده شده")
    is_global = models.BooleanField(default=False, verbose_name="اعلان عمومی")
    send_sms_to_all = models.BooleanField(default=False, verbose_name="ارسال پیامک به همه کاربران")
    sms_status = models.CharField(
        max_length=20,
        choices=SmsStatus.choices,
        default=SmsStatus.NOT_REQUESTED,
        verbose_name="وضعیت ارسال پیامک",
        db_index=True,
    )
    sms_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان ارسال پیامک")
    sms_recipients_count = models.PositiveIntegerField(default=0, verbose_name="تعداد دریافت‌کنندگان پیامک")
    sms_error = models.TextField(blank=True, verbose_name="شرح خطای پیامک")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "اطلاعیه"
        verbose_name_plural = "اطلاعیه‌ها"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["is_global", "created_at"]),
            models.Index(fields=["sms_status", "created_at"]),
        ]


class BodyCircumferenceMeasurement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="circumference_records")
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name=_("قد (سانتی‌متر)"))
    weight_kg = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, verbose_name=_("وزن (کیلوگرم)"))
    wrist_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور مچ دست"))
    forearm_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ساعد"))
    arm_rest_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور بازو در حالت استراحت"))
    arm_flexed_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور بازو در حالت انقباض"))
    wrist_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور مچ دست (چپ)"))
    forearm_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ساعد (چپ)"))
    arm_rest_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور بازو در حالت استراحت (چپ)"))
    arm_flexed_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور بازو در حالت انقباض (چپ)"))
    head_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور سر"))
    neck_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور گردن"))
    chest_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور قفسه سینه"))
    shoulders_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور شانه‌ها"))
    waist_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور کمر"))
    abdomen_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور شکم"))
    hips_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور باسن"))
    thigh_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ران پا"))
    calf_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ساق پا"))
    thigh_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ران پا (چپ)"))
    calf_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ساق پا (چپ)"))
    sit_height_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("قد نشسته"))
    leg_length_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("طول پا"))
    shoulder_width_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("عرض شانه"))
    hip_width_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("عرض لگن"))
    elbow_width_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("عرض آرنج"))
    knee_width_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("عرض زانو"))
    arm_length_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("طول بازو"))
    recorded_at = models.DateTimeField(auto_now_add=True)
    measured_at_jalali = models.CharField(max_length=10, null=True, blank=True, verbose_name=_("تاریخ ثبت اندازه‌گیری (شمسی)"))
    legacy_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "اندازه‌گیری محیط بدن"
        verbose_name_plural = "اندازه‌گیری‌های محیط بدن"


class CaliperMeasurement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="caliper_records")
    chest_armpit_men_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("سینه"))
    axilla_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("زیربغل"))
    subscapular_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("تحت کتفی"))
    abdominal_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("شکم"))
    suprailiac_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("سه‌تیغ خاصره"))
    chest_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("کمر"))
    biceps_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("جلوبازو"))
    triceps_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("پشت بازو"))
    thigh_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("جلوی ران"))
    calf_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("پشت ساق پا"))
    recorded_at = models.DateTimeField(auto_now_add=True)
    measured_at_jalali = models.CharField(max_length=10, null=True, blank=True, verbose_name=_("تاریخ ثبت اندازه‌گیری (شمسی)"))
    legacy_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "اندازه‌گیری کالیپر"
        verbose_name_plural = "اندازه‌گیری‌های کالیپر"


class ClientMedia(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="client_media")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="uploaded_client_media")
    image = models.FileField(upload_to="client_media/images/", null=True, blank=True, verbose_name=_("تصویر"))
    video = models.FileField(upload_to="client_media/videos/", null=True, blank=True, verbose_name=_("ویدیو"))
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "فایل کاربر"
        verbose_name_plural = "فایل‌های کاربر"


class ClientDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="client_documents")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="uploaded_client_documents")
    title = models.CharField(max_length=120, verbose_name=_("عنوان"))
    file = models.FileField(upload_to="client_media/documents/", verbose_name=_("فایل"))
    uploaded_at = models.DateTimeField(auto_now_add=True)
    legacy_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "برنامه/فایل کاربر"
        verbose_name_plural = "برنامه‌ها و فایل‌های کاربر"

    def __str__(self):
        return self.title


class CoachRequest(models.Model):
    class SessionsPerWeek(models.TextChoices):
        ONE = "1", _("۱ جلسه در هفته")
        TWO = "2", _("۲ جلسه در هفته")
        THREE = "3", _("۳ جلسه در هفته")
        FOUR = "4", _("۴ جلسه در هفته")
        FIVE = "5", _("۵ جلسه در هفته")
        SIX = "6", _("۶ جلسه در هفته")
        COACH_DISCRETION = "coach_discretion", _("هر چه مربی صلاح بداند")

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار بررسی")
        HANDLED = "handled", _("بررسی شده")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coach_requests")
    sessions_per_week = models.CharField(max_length=20, choices=SessionsPerWeek.choices, verbose_name=_("تعداد جلسات در هفته"))
    wants_diet = models.BooleanField(default=False, verbose_name=_("درخواست برنامه غذایی"))
    wants_workout = models.BooleanField(default=False, verbose_name=_("درخواست برنامه تمرینی"))
    pain_notes = models.TextField(blank=True, verbose_name=_("درد یا آسیب"))
    illness_notes = models.TextField(blank=True, verbose_name=_("بیماری زمینه‌ای"))
    diet_restrictions = models.TextField(blank=True, verbose_name=_("محدودیت‌های غذایی"))
    # Athlete-submitted body data (field names mirror BodyCircumferenceMeasurement so the coach can copy 1:1).
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name=_("قد (سانتی‌متر)"))
    weight_kg = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, verbose_name=_("وزن (کیلوگرم)"))
    wrist_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور مچ دست"))
    forearm_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ساعد"))
    arm_rest_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور بازو آزاد"))
    arm_flexed_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور بازو منقبض"))
    chest_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور سینه"))
    shoulders_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور سرشانه"))
    waist_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور کمر"))
    abdomen_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور شکم"))
    hips_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور باسن"))
    thigh_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ران"))
    calf_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ساق پا"))
    thigh_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ران (چپ)"))
    calf_left_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name=_("دور ساق پا (چپ)"))
    pushed_to_measurements = models.BooleanField(default=False, verbose_name=_("به اندازه‌گیری‌ها افزوده شد"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True, verbose_name=_("وضعیت"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "درخواست از مربی"
        verbose_name_plural = "درخواست‌های از مربی"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.fullname} - {self.get_status_display()}"

    @property
    def has_body_data(self) -> bool:
        return any(
            getattr(self, field) is not None
            for field in (
                "height_cm", "weight_kg", "wrist_cm", "forearm_cm", "arm_rest_cm",
                "arm_flexed_cm", "chest_cm", "shoulders_cm", "waist_cm", "abdomen_cm",
                "hips_cm", "thigh_cm", "calf_cm", "thigh_left_cm", "calf_left_cm",
            )
        )


class CoachRequestAttachment(models.Model):
    request = models.ForeignKey(CoachRequest, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="coach_requests/", verbose_name=_("فایل پیوست"))
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "پیوست درخواست مربی"
        verbose_name_plural = "پیوست‌های درخواست مربی"

    def __str__(self):
        return self.file.name


class Muscle(models.Model):
    name = models.CharField(max_length=120, verbose_name=_("نام عضله"))
    name_en = models.CharField(max_length=120, blank=True, verbose_name=_("نام انگلیسی عضله"))
    origin = models.TextField(blank=True, verbose_name=_("مبدا"))
    insertion = models.TextField(blank=True, verbose_name=_("انتها"))
    nerve = models.CharField(max_length=120, blank=True, verbose_name=_("عصب"))
    function_note = models.TextField(blank=True, verbose_name=_("عملکرد"))
    image = models.ImageField(upload_to="muscles/", null=True, blank=True, verbose_name=_("تصویر"))

    class Meta:
        ordering = ["name"]
        verbose_name = "عضله"
        verbose_name_plural = "کتابخانه عضلات"

    def __str__(self):
        return self.name


class ExerciseBodyPart(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("بخش بدن"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "بخش بدن"
        verbose_name_plural = "بخش‌های بدن"

    def __str__(self):
        return self.name


class ExerciseMovementType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("نوع حرکت"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع حرکت"
        verbose_name_plural = "انواع حرکت"

    def __str__(self):
        return self.name


class ExerciseJointType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("نوع مفصل"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع مفصل"
        verbose_name_plural = "انواع مفصل"

    def __str__(self):
        return self.name


class ExercisePowerType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("نوع قدرت"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع قدرت"
        verbose_name_plural = "انواع قدرت"

    def __str__(self):
        return self.name


class ExerciseDifficultyLevel(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("سطح دشواری"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "سطح دشواری"
        verbose_name_plural = "سطوح دشواری"

    def __str__(self):
        return self.name


class ExerciseEquipmentType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("تجهیزات"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع تجهیزات"
        verbose_name_plural = "انواع تجهیزات"

    def __str__(self):
        return self.name


class ExerciseExecutionEquipmentType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("نوع تجهیزات اجرایی"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع تجهیزات اجرایی"
        verbose_name_plural = "انواع تجهیزات اجرایی"

    def __str__(self):
        return self.name


class ExerciseSecondaryMovementType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("نوع حرکت دوم"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع حرکت دوم"
        verbose_name_plural = "انواع حرکت دوم"

    def __str__(self):
        return self.name


class ExerciseAbnormalityType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("ناهنجاری"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "ناهنجاری"
        verbose_name_plural = "انواع ناهنجاری"

    def __str__(self):
        return self.name


class ExercisePressureType(models.Model):
    name = models.CharField(max_length=60, unique=True, verbose_name=_("نوع فشار"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع فشار"
        verbose_name_plural = "انواع فشار"

    def __str__(self):
        return self.name


class ExerciseSportType(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name=_("نوع ورزش"))
    name_en = models.CharField(max_length=80, blank=True, verbose_name=_("نام انگلیسی"))

    class Meta:
        ordering = ["name"]
        verbose_name = "نوع ورزش"
        verbose_name_plural = "انواع ورزش"

    def __str__(self):
        return self.name


class ExerciseSetType(models.Model):
    set_count = models.CharField(max_length=40, verbose_name=_("تعداد ست"))
    goal = models.CharField(max_length=80, blank=True, verbose_name=_("هدف"))

    class Meta:
        ordering = ["goal", "set_count"]
        verbose_name = "نوع ست"
        verbose_name_plural = "انواع ست"

    def __str__(self):
        return f"{self.set_count} ({self.goal})" if self.goal else self.set_count


class ExerciseRepetitionType(models.Model):
    reps = models.CharField(max_length=40, verbose_name=_("تعداد تکرار"))
    goal = models.CharField(max_length=80, blank=True, verbose_name=_("هدف"))

    class Meta:
        ordering = ["goal", "reps"]
        verbose_name = "نوع تکرار"
        verbose_name_plural = "انواع تکرار"

    def __str__(self):
        return f"{self.reps} ({self.goal})" if self.goal else self.reps


class ExerciseRestType(models.Model):
    rest_time = models.CharField(max_length=40, verbose_name=_("زمان استراحت"))
    goal = models.CharField(max_length=80, blank=True, verbose_name=_("هدف"))

    class Meta:
        ordering = ["goal", "rest_time"]
        verbose_name = "نوع استراحت"
        verbose_name_plural = "انواع استراحت"

    def __str__(self):
        return f"{self.rest_time} ({self.goal})" if self.goal else self.rest_time


class Exercise(models.Model):
    name = models.CharField(max_length=120, verbose_name=_("نام حرکت"))
    name_en = models.CharField(max_length=160, blank=True, verbose_name=_("نام انگلیسی حرکت"))
    primary_muscle = models.ForeignKey(Muscle, on_delete=models.PROTECT, related_name="primary_exercises", verbose_name=_("عضله اصلی"))
    secondary_muscle = models.ForeignKey(Muscle, on_delete=models.SET_NULL, null=True, blank=True, related_name="secondary_exercises", verbose_name=_("عضله فرعی"))
    body_part = models.ForeignKey(ExerciseBodyPart, on_delete=models.PROTECT, related_name="exercises", verbose_name=_("بخش بدن"))
    movement_type = models.ForeignKey(ExerciseMovementType, on_delete=models.PROTECT, related_name="exercises", verbose_name=_("نوع حرکت"))
    joint_type = models.ForeignKey(ExerciseJointType, on_delete=models.PROTECT, related_name="exercises", verbose_name=_("نوع مفصل"))
    power_type = models.ForeignKey(ExercisePowerType, on_delete=models.PROTECT, related_name="exercises", verbose_name=_("نوع قدرت"))
    difficulty_level = models.ForeignKey(ExerciseDifficultyLevel, on_delete=models.PROTECT, related_name="exercises", verbose_name=_("سطح دشواری"))
    equipment_type = models.ForeignKey(ExerciseEquipmentType, on_delete=models.PROTECT, related_name="exercises", verbose_name=_("تجهیزات"))
    execution_equipment_type = models.ForeignKey(ExerciseExecutionEquipmentType, on_delete=models.PROTECT, null=True, blank=True, related_name="exercises", verbose_name=_("نوع تجهیزات اجرایی"))
    secondary_movement_type = models.ForeignKey(ExerciseSecondaryMovementType, on_delete=models.PROTECT, null=True, blank=True, related_name="exercises", verbose_name=_("نوع حرکت دوم"))
    pressure_type = models.ForeignKey(ExercisePressureType, on_delete=models.PROTECT, null=True, blank=True, related_name="exercises", verbose_name=_("نوع فشار"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات حرکت"))
    media = models.FileField(upload_to="exercises/", null=True, blank=True, verbose_name=_("تصویر یا ویدیو"))

    class Meta:
        ordering = ["name"]
        verbose_name = "حرکت تمرینی"
        verbose_name_plural = "کتابخانه حرکات تمرینی"
        indexes = [
            models.Index(fields=["primary_muscle"]),
        ]

    def __str__(self):
        return self.name


class CorrectiveExercise(models.Model):
    name = models.CharField(max_length=120, verbose_name=_("نام حرکت"))
    equipment = models.ForeignKey(ExerciseEquipmentType, on_delete=models.PROTECT, null=True, blank=True, related_name="corrective_exercises", verbose_name=_("تجهیزات مورد نیاز"))
    abnormality_type = models.ForeignKey(ExerciseAbnormalityType, on_delete=models.PROTECT, null=True, blank=True, related_name="corrective_exercises", verbose_name=_("نوع ناهنجاری"))
    media = models.FileField(upload_to="corrective_exercises/", null=True, blank=True, verbose_name=_("تصویر یا ویدیو"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))

    class Meta:
        ordering = ["name"]
        verbose_name = "حرکت اصلاحی"
        verbose_name_plural = "کتابخانه حرکات اصلاحی"

    def __str__(self):
        return self.name


class BirthdaySmsLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="birthday_sms_logs")
    sent_on = models.CharField(max_length=10, verbose_name=_("تاریخ ارسال (شمسی)"))

    class Meta:
        unique_together = (("user", "sent_on"),)
        verbose_name = "ارسال پیامک تبریک تولد"
        verbose_name_plural = "ارسال‌های پیامک تبریک تولد"

    def __str__(self):
        return f"{self.user.fullname} - {self.sent_on}"
