from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from account.constants import OTP_EXPIRATION_MINUTES, OTP_REQUEST_COOLDOWN_SECONDS
from account.exceptions import (
    AuthenticationException,
    ExpiredOtpException,
    InvalidOtpException,
    OTPRateLimitExceededException,
    PasswordResetException,
    PhoneAlreadyExistsException,
    SessionValidationException,
    SMSProviderException,
)
from account.froms import (
    CheckOtp,
    BirthDateForm,
    CoachRequestForm,
    FormLogin,
    FormRegister,
    BloodGroupForm,
    HeightForm,
    NumberEditForm,
    OtpForm,
    PasswordChanged,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    WeightForm,
    UserEditForm,
    validate_coach_request_file,
)
from django.core.exceptions import ValidationError
from account.services import AuthService, OTPService, ProfileService, SessionService, create_and_send_otp, get_valid_otp
from account.services.coach_request_service import CoachRequestService
from account.portal_mixins import UserPortalRequiredMixin, get_post_login_redirect_url, user_portal_required
from account.utils import format_phone_display
from home.models import SeriesModel


auth_service = AuthService()
otp_service = OTPService()
profile_service = ProfileService()
session_service = SessionService()
coach_request_service = CoachRequestService()


PROFILE_METRIC_CONFIG = {
    "weight": {
        "field": "weight_kg",
        "form_field": "weight",
        "form_class": WeightForm,
        "template_name": "account/profile-metric-edit.html",
        "title": _("وزن"),
        "description": _("وزنتون رو به کیلوگرم وارد کنید."),
    },
    "height": {
        "field": "height_cm",
        "form_field": "height",
        "form_class": HeightForm,
        "template_name": "account/profile-metric-edit.html",
        "title": _("قد"),
        "description": _("قدتون رو به سانتی متر وارد کنید."),
    },
    "birth_date": {
        "field": "birth_date_jalali",
        "form_field": "birth_date",
        "form_class": BirthDateForm,
        "template_name": "account/profile-metric-edit.html",
        "title": _("تاریخ تولد"),
        "description": _("تاریخ تولدتون رو وارد کنید."),
    },
    "blood_group": {
        "field": "blood_group",
        "form_field": "blood_group",
        "form_class": BloodGroupForm,
        "template_name": "account/profile-blood-group.html",
        "title": _("گروه خونی"),
        "description": _("گروه خونی خود را انتخاب کنید."),
    },
}


def _build_verification_context(*, token: str, form):
    context = {
        "form": form,
        "token": token,
        "verification_phone": None,
        "otp_expires_in_seconds": OTP_EXPIRATION_MINUTES * 60,
        "otp_resend_cooldown_seconds": OTP_REQUEST_COOLDOWN_SECONDS,
        "otp_cooldown_remaining_seconds": 0,
        "otp_can_resend": True,
    }
    token = (token or "").strip()
    if not token:
        return context

    try:
        status = otp_service.get_verification_status(token)
        context.update(
            {
                "verification_phone": format_phone_display(status.phone),
                "otp_expires_in_seconds": status.expires_in_seconds,
                "otp_cooldown_remaining_seconds": status.resend_cooldown_seconds,
                "otp_can_resend": status.can_resend,
            }
        )
    except Exception:
        pass
    return context


class AccountPageMixin:
    active_section = "dashboard"
    account_title = ""
    account_description = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("active_section", self.active_section)
        context.setdefault("account_title", self.account_title)
        context.setdefault("account_description", self.account_description)
        return context


class Register(View):
    template_name = "account/login-register.html"

    def get(self, request):
        return render(request, self.template_name, {"form": OtpForm()})

    def post(self, request):
        form = OtpForm(request.POST)
        if form.is_valid():
            try:
                token = create_and_send_otp(form.cleaned_data["phone"])
            except SMSProviderException as exc:
                form.add_error("phone", str(exc))
                return render(request, self.template_name, {"form": form})
            except OTPRateLimitExceededException as exc:
                form.add_error("phone", str(exc))
                return render(request, self.template_name, {"form": form})

            messages.success(request, _("کد تایید برای شما ارسال شد."))
            return redirect(f"{reverse('register:verification')}?token={token}")

        return render(request, self.template_name, {"form": form})


class CheckOtpView(View):
    template_name = "account/verification.html"

    def get(self, request):
        token = (request.GET.get("token") or "").strip()
        return render(
            request,
            self.template_name,
            _build_verification_context(token=token, form=CheckOtp()),
        )

    def post(self, request):
        token = (request.GET.get("token") or "").strip()
        form = CheckOtp(request.POST)
        if form.is_valid():
            try:
                otp = otp_service.validate_otp(token=token, code=int(form.cleaned_data["code"]))
                user, _created = auth_service.get_or_create_otp_user(phone=otp.phone)
                login(request, user)
                otp_service.consume_otp(otp)
                session_service.queue_login_session_log(user=user, request=request)
                messages.success(request, _("با موفقیت وارد شدید."))
                return redirect(get_post_login_redirect_url(user))
            except (InvalidOtpException, ExpiredOtpException):
                form.add_error("code", _("کد وارد شده نادرست یا منقضی شده است."))

        return render(
            request,
            self.template_name,
            _build_verification_context(token=token, form=form),
        )


class ResendOtpView(View):
    def get(self, request):
        token = (request.GET.get("token") or "").strip()
        if not token:
            messages.error(request, _("درخواست معتبر نیست."))
            return redirect("register:register")

        try:
            new_token = otp_service.resend_otp(token=token)
        except OTPRateLimitExceededException as exc:
            messages.error(request, str(exc))
            return redirect(f"{reverse('register:verification')}?token={token}")
        except SMSProviderException as exc:
            messages.error(request, str(exc))
            return redirect(f"{reverse('register:verification')}?token={token}")
        except Exception:
            messages.error(request, _("امکان ارسال دوباره کد وجود ندارد. دوباره شماره موبایل را وارد کنید."))
            return redirect("register:register")

        messages.success(request, _("کد تایید دوباره ارسال شد."))
        return redirect(f"{reverse('register:verification')}?token={new_token}")


def user_logout(request):
    logout(request)
    return redirect("/")


class ProfileView(AccountPageMixin, UserPortalRequiredMixin, TemplateView):
    template_name = "account/profile.html"
    active_section = "dashboard"
    account_title = _("پروفایل")
    account_description = _("اطلاعات حساب و وضعیت بدن خود را در یک نگاه مدیریت کنید.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(profile_service.get_dashboard_context(self.request.user))
        return context


class ProfileAnalysisView(AccountPageMixin, UserPortalRequiredMixin, TemplateView):
    template_name = "account/profile-analysis.html"
    active_section = "analysis"
    account_title = _("آنالیز")
    account_description = _("شاخص‌های بدنی و گزارش‌های روزانه را از اینجا بررسی کنید.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(profile_service.get_dashboard_context(self.request.user))
        context.update(
            profile_service.get_analysis_context(
                self.request.user,
                metric=self.request.GET.get("metric"),
                start=self.request.GET.get("start"),
                end=self.request.GET.get("end"),
                date=self.request.GET.get("date"),
            )
        )
        context.update(profile_service.get_analysis_dashboard_data(self.request.user))
        context["analysis_metric_series"] = profile_service.get_analysis_metric_series(self.request.user)
        return context


class ProfileCoachView(AccountPageMixin, UserPortalRequiredMixin, View):
    template_name = "account/profile-coach.html"
    active_section = "coach"
    account_title = _("مربی شما")
    account_description = _("در این بخش اطلاعات مربی اختصاصی و مسیر پیگیری برنامه نمایش داده می‌شود.")

    def _get_pending(self, user):
        return coach_request_service.get_pending_for_user(user).first()

    def _build_context(self, *, form=None, pending=None):
        user = self.request.user
        pending = pending if pending is not None else self._get_pending(user)
        return {
            "active_section": self.active_section,
            "account_title": self.account_title,
            "account_description": self.account_description,
            "coach": user.coach,
            "pending_request": pending,
            "attachments": list(pending.attachments.all()) if pending else [],
            "form": form or CoachRequestForm(instance=pending),
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._build_context())

    def post(self, request, *args, **kwargs):
        pending = self._get_pending(request.user)
        form = CoachRequestForm(request.POST, instance=pending)
        files = request.FILES.getlist("attachments")
        file_errors: list[str] = []
        for uploaded in files:
            try:
                validate_coach_request_file(uploaded)
            except ValidationError as exc:
                file_errors.extend(exc.messages)
        if form.is_valid() and not file_errors:
            coach_request_service.save_request(user=request.user, form=form, files=files)
            messages.success(
                request,
                _("درخواست شما به‌روزرسانی شد.") if pending else _("درخواست شما برای مربی ثبت شد."),
            )
            return redirect("register:profile_coach")
        for error in file_errors:
            messages.error(request, error)
        return render(request, self.template_name, self._build_context(form=form, pending=pending))


class ProfileMetricEditView(AccountPageMixin, UserPortalRequiredMixin, View):
    template_name = "account/profile-metric-edit.html"
    active_section = "dashboard"
    hide_account_chrome = True

    def dispatch(self, request, *args, **kwargs):
        self.metric = kwargs.get("metric")
        self.metric_config = PROFILE_METRIC_CONFIG.get(self.metric)
        if self.metric_config is None:
            return redirect("register:profile")
        self.template_name = self.metric_config["template_name"]
        self.account_title = self.metric_config["title"]
        self.account_description = self.metric_config["description"]
        return super().dispatch(request, *args, **kwargs)

    def _build_form(self, *, data=None):
        form_class = self.metric_config["form_class"]
        field_name = self.metric_config["field"]
        form_field_name = self.metric_config["form_field"]
        initial_value = getattr(self.request.user, field_name, None)
        initial = {form_field_name: initial_value} if initial_value is not None else None
        return form_class(data=data, initial=initial)

    def _get_form_context(self, form):
        form_field_name = self.metric_config["form_field"]
        field = form[form_field_name]
        return {
            "form": form,
            "field": field,
            "field_label": self.metric_config["title"],
            "metric": self.metric,
            "metric_config": self.metric_config,
            "active_section": self.active_section,
            "account_title": self.account_title,
            "account_description": self.account_description,
            "hide_account_chrome": self.hide_account_chrome,
        }

    def get(self, request, *args, **kwargs):
        form = self._build_form()
        return render(request, self.template_name, self._get_form_context(form))

    def post(self, request, *args, **kwargs):
        form = self._build_form(data=request.POST)
        if form.is_valid():
            field_name = self.metric_config["field"]
            value = next(iter(form.cleaned_data.values()))
            profile_service.update_profile_metric(user=request.user, field_name=field_name, value=value)
            messages.success(request, _("اطلاعات پروفایل با موفقیت به‌روزرسانی شد."))
            return redirect("register:profile")

        return render(request, self.template_name, self._get_form_context(form))


class ProfileCoursesView(AccountPageMixin, UserPortalRequiredMixin, TemplateView):
    template_name = "account/profile-courses.html"
    active_section = "courses"
    account_title = _("دوره‌های من")
    account_description = _("آخرین دوره‌هایی که به آن‌ها دسترسی دارید را ببینید.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = profile_service.get_learning_courses(self.request.user)
        return context


class ProfileDocumentsView(AccountPageMixin, UserPortalRequiredMixin, TemplateView):
    template_name = "account/profile-plans.html"
    active_section = "plans"
    account_title = _("برنامه‌های من")
    account_description = _("فایل‌ها و برنامه‌هایی که مربی برای شما ارسال کرده است.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documents"] = self.request.user.client_documents.all()
        return context


class AddCourseToProfileView(UserPortalRequiredMixin, View):
    def post(self, request, series_id):
        series = get_object_or_404(SeriesModel, id=series_id, free=True)
        profile_service.add_free_course_to_profile(user=request.user, series_id=series_id, series=series)
        return redirect("home:series_episod", pk=series_id)


class ProfileFinancialView(AccountPageMixin, UserPortalRequiredMixin, TemplateView):
    template_name = "account/profile-financial.html"
    active_section = "financial"
    account_title = _("مالی و سفارش‌ها")
    account_description = _("وضعیت پرداخت‌ها و سفارش‌های ثبت شده را بررسی کنید.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders"] = profile_service.get_paid_orders(self.request.user)
        return context


class ProfileCommentsView(AccountPageMixin, UserPortalRequiredMixin, TemplateView):
    template_name = "account/profile-comments.html"
    active_section = "comments"
    account_title = _("دیدگاه‌های من")
    account_description = _("آخرین تعامل‌های شما با دوره‌ها در این بخش نمایش داده می‌شود.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = profile_service.get_comments(self.request.user)
        return context


class ProfileNotificationsView(AccountPageMixin, UserPortalRequiredMixin, TemplateView):
    template_name = "account/profile-notifications.html"
    active_section = "notifications"
    account_title = _("اعلان‌ها")
    account_description = _("اعلان‌های سیستم و درخواست‌های جدید را از اینجا دنبال کنید.")

    def post(self, request, *args, **kwargs):
        course_id = request.POST.get("course_id")
        course = get_object_or_404(SeriesModel, id=course_id)
        profile_service.create_course_request_notification(user=request.user, course=course)
        messages.success(request, _("درخواست شما ثبت شد."))
        return redirect("register:profile_notifications")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notifications"] = profile_service.get_notifications_feed(self.request.user)
        return context


@user_portal_required
def edit_user_profile(request):
    if request.method == "POST":
        form = UserEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            profile_service.update_profile(form=form)
            messages.success(request, _("اطلاعات شما با موفقیت بروزرسانی شد."))
            return redirect("register:profile_useredit")
    else:
        form = UserEditForm(instance=request.user)

    return render(
        request,
        "account/profile-edit.html",
        {
            "form": form,
            "active_section": "edit",
            "account_title": _("ویرایش پروفایل"),
            "account_description": _("اطلاعات اصلی حساب کاربری خود را به‌روزرسانی کنید."),
        },
    )


class NumberEdit(AccountPageMixin, UserPortalRequiredMixin, View):
    template_name = "account/edit_number.html"
    active_section = "number"
    account_title = _("ویرایش شماره تماس")
    account_description = _("شماره تماس حساب خود را با دریافت کد تایید به‌روزرسانی کنید.")

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": NumberEditForm(initial={"phone_number_new": ""}),
                "active_section": self.active_section,
                "account_title": self.account_title,
                "account_description": self.account_description,
            },
        )

    def post(self, request):
        form = NumberEditForm(request.POST)
        if form.is_valid():
            new_phone = form.cleaned_data["phone_number_new"]
            try:
                token = profile_service.request_phone_change(
                    user=request.user,
                    new_phone=new_phone,
                    session=request.session,
                    otp_creator=create_and_send_otp,
                )
            except PhoneAlreadyExistsException as exc:
                form.add_error("phone_number_new", str(exc))
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "active_section": self.active_section,
                        "account_title": self.account_title,
                        "account_description": self.account_description,
                    },
                )
            except SMSProviderException as exc:
                form.add_error("phone_number_new", str(exc))
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "active_section": self.active_section,
                        "account_title": self.account_title,
                        "account_description": self.account_description,
                    },
                )

            messages.success(request, _("کد تایید برای شماره جدید ارسال شد."))
            return redirect(f"{reverse('register:profile_number_verify')}?token={token}")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_section": self.active_section,
                "account_title": self.account_title,
                "account_description": self.account_description,
            },
        )


class NumberEditVerify(AccountPageMixin, UserPortalRequiredMixin, View):
    template_name = "account/edit_number_verify.html"
    active_section = "number"
    account_title = _("تایید شماره تماس")
    account_description = _("کد ارسال شده به شماره جدید را وارد کنید.")

    def get(self, request):
        return render(request, self.template_name, {"form": CheckOtp()})

    def post(self, request):
        token = (request.GET.get("token") or "").strip()
        form = CheckOtp(request.POST)

        if form.is_valid():
            try:
                profile_service.confirm_phone_change(
                    user=request.user,
                    token=token,
                    code=int(form.cleaned_data["code"]),
                    session=request.session,
                )
                messages.success(request, _("شماره تماس با موفقیت تایید و بروزرسانی شد."))
                return redirect("register:profile_number_edit")
            except (SessionValidationException, AuthenticationException):
                messages.error(request, _("درخواست تغییر شماره معتبر نیست."))
                return redirect("register:profile_number_edit")
            except PhoneAlreadyExistsException:
                form.add_error("code", _("شماره تماس جدید معتبر نیست."))
            except (InvalidOtpException, ExpiredOtpException):
                form.add_error("code", _("کد وارد شده نادرست یا منقضی شده است."))

        return render(request, self.template_name, {"form": form})


def signup(request):
    if request.method == "POST":
        form = FormRegister(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            password = form.cleaned_data["password"]
            fullname = form.cleaned_data["fullname"]

            try:
                user = auth_service.register_user(fullname=fullname, phone=phone, password=password)
            except AuthenticationException as exc:
                form.add_error("fullname", str(exc))
                return render(request, "account/pass_register.html", {"form": form})
            except PhoneAlreadyExistsException as exc:
                form.add_error("phone", str(exc))
                return render(request, "account/pass_register.html", {"form": form})

            login(request, user)
            session_service.queue_login_session_log(user=user, request=request)
            messages.success(request, _("با موفقیت وارد شدید."))
            return redirect(get_post_login_redirect_url(user))
    else:
        form = FormRegister()

    return render(request, "account/pass_register.html", {"form": form})


class PasswordsChangeView(AccountPageMixin, UserPortalRequiredMixin, PasswordChangeView):
    form_class = PasswordChanged
    success_url = reverse_lazy("home:home")
    template_name = "account/change_password.html"
    active_section = "password"
    account_title = _("تغییر رمز عبور")
    account_description = _("رمز عبور حساب خود را به شکل امن به‌روز کنید.")

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, _("رمز عبور شما با موفقیت تغییر کرد."))
        return response


def login_view(request):
    if request.method == "POST":
        form = FormLogin(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                user = auth_service.authenticate_user(fullname=cd["fullname"], password=cd["password"])
                login(request, user)
                session_service.queue_login_session_log(user=user, request=request)
                messages.success(request, _("با موفقیت وارد شدید."))
                return redirect(get_post_login_redirect_url(user))
            except AuthenticationException:
                form.add_error(None, _("نام کاربری یا کلمه عبور اشتباه است."))
    else:
        form = FormLogin()
    return render(request, "account/pass_login.html", {"form": form})


class ForgotPasswordView(View):
    template_name = "account/forgot_password.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PasswordResetRequestForm()})

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            try:
                token = profile_service.request_password_reset(
                    phone=form.cleaned_data["phone"],
                    session=request.session,
                    otp_creator=create_and_send_otp,
                )
            except PasswordResetException as exc:
                form.add_error("phone", str(exc))
                return render(request, self.template_name, {"form": form})
            except SMSProviderException as exc:
                form.add_error("phone", str(exc))
                return render(request, self.template_name, {"form": form})

            messages.success(request, _("کد تایید برای شماره شما ارسال شد."))
            return redirect(f"{reverse('register:forgot_password_confirm')}?token={token}")
        return render(request, self.template_name, {"form": form})


class ForgotPasswordConfirmView(View):
    template_name = "account/forgot_password_confirm.html"

    def get(self, request):
        return render(request, self.template_name, {"form": PasswordResetConfirmForm()})

    def post(self, request):
        token = (request.GET.get("token") or "").strip()
        session_token = request.session.get("password_reset_token")
        form = PasswordResetConfirmForm(request.POST)

        if token != session_token:
            messages.error(request, _("درخواست بازیابی رمز عبور معتبر نیست."))
            return redirect("register:forgot_password")

        if form.is_valid():
            try:
                profile_service.confirm_password_reset(
                    token=token,
                    code=int(form.cleaned_data["code"]),
                    new_password=form.cleaned_data["new_password1"],
                    session=request.session,
                )
                messages.success(request, _("رمز عبور با موفقیت تغییر کرد. اکنون وارد حساب شوید."))
                return redirect("register:pass_login")
            except (InvalidOtpException, ExpiredOtpException):
                form.add_error("code", _("کد وارد شده نادرست یا منقضی شده است."))
            except (SessionValidationException, AuthenticationException):
                messages.error(request, _("درخواست بازیابی رمز عبور معتبر نیست."))
                return redirect("register:forgot_password")
            except PasswordResetException as exc:
                form.add_error("code", str(exc))

        return render(request, self.template_name, {"form": form})
