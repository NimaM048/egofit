from django import forms
from django.utils.translation import gettext_lazy as _

from account.froms import INPUT_CLASS
from account.models import BodyCircumferenceMeasurement, CaliperMeasurement, ClientDocument, ClientMedia, CorrectiveExercise, Exercise, Muscle, User
from account.utils import calculate_age_from_jalali, combine_fullname, normalize_phone_number


class AdminUserSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": _("نام یا شماره همراه کاربر را وارد کنید"),
            }
        ),
    )


class AdminPersonalInfoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "display_name",
            "phone",
            "blood_group",
            "gender",
            "birth_date_jalali",
            "activity_level",
            "coach",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام")}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام خانوادگی")}),
            "display_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام کاربری")}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("شماره تماس"), "dir": "ltr"}),
            "blood_group": forms.Select(attrs={"class": INPUT_CLASS}),
            "gender": forms.Select(attrs={"class": INPUT_CLASS}),
            "birth_date_jalali": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("تاریخ تولد (فرمت: سال/ماه/روز)")}),
            "activity_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "coach": forms.Select(attrs={"class": INPUT_CLASS}),
        }
        labels = {
            "display_name": _("نام کاربری"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["coach"].queryset = User.objects.filter(is_admin=True)
        self.fields["coach"].required = False
        self.fields["coach"].empty_label = _("بدون مربی")

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get("first_name", "")
        last_name = cleaned_data.get("last_name", "")
        combined = combine_fullname(first_name, last_name)
        if combined and User.objects.filter(fullname=combined).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("این نام و نام خانوادگی قبلاً ثبت شده است."))
        cleaned_data["fullname"] = combined
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get("fullname"):
            instance.fullname = self.cleaned_data["fullname"]
        instance.age = calculate_age_from_jalali(self.cleaned_data.get("birth_date_jalali"))
        if commit:
            instance.save()
        return instance


class AdminUserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label=_("رمز عبور (برای ورود به اپ)"),
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "dir": "ltr"}),
        help_text=_("برای ورود کاربر به اپ استفاده می‌شود"),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "blood_group", "gender", "birth_date_jalali", "activity_level", "coach")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام")}),
            "last_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام خانوادگی")}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("شماره تماس"), "dir": "ltr"}),
            "blood_group": forms.Select(attrs={"class": INPUT_CLASS}),
            "gender": forms.Select(attrs={"class": INPUT_CLASS}),
            "birth_date_jalali": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("تاریخ تولد (فرمت: سال/ماه/روز)")}),
            "activity_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "coach": forms.Select(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["coach"].queryset = User.objects.filter(is_admin=True)
        self.fields["coach"].required = False
        self.fields["coach"].empty_label = _("بدون مربی")

    def clean_phone(self):
        normalized = normalize_phone_number(self.cleaned_data["phone"])
        if len(normalized) != 11 or not normalized.isdigit():
            raise forms.ValidationError(_("شماره تماس معتبر نیست."))
        return normalized

    def clean(self):
        cleaned_data = super().clean()
        combined = combine_fullname(cleaned_data.get("first_name", ""), cleaned_data.get("last_name", ""))
        if combined and User.objects.filter(fullname=combined).exists():
            raise forms.ValidationError(_("این نام و نام خانوادگی قبلاً ثبت شده است."))
        cleaned_data["fullname"] = combined
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.fullname = self.cleaned_data["fullname"]
        instance.age = calculate_age_from_jalali(self.cleaned_data.get("birth_date_jalali"))
        if commit:
            instance.save()
        return instance


class AdminCircumferenceForm(forms.ModelForm):
    class Meta:
        model = BodyCircumferenceMeasurement
        exclude = ("user", "recorded_at")
        widgets = {
            "measured_at_jalali": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("تاریخ ثبت (فرمت: سال/ماه/روز)")}),
            **{field: forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1", "dir": "ltr", "data-select-all-on-focus": "true"}) for field in (
                "height_cm",
                "weight_kg",
                "wrist_cm",
                "forearm_cm",
                "arm_rest_cm",
                "arm_flexed_cm",
                "wrist_left_cm",
                "forearm_left_cm",
                "arm_rest_left_cm",
                "arm_flexed_left_cm",
                "head_cm",
                "neck_cm",
                "chest_cm",
                "shoulders_cm",
                "waist_cm",
                "abdomen_cm",
                "hips_cm",
                "thigh_cm",
                "calf_cm",
                "thigh_left_cm",
                "calf_left_cm",
                "sit_height_cm",
                "leg_length_cm",
                "shoulder_width_cm",
                "hip_width_cm",
                "elbow_width_cm",
                "knee_width_cm",
                "arm_length_cm",
            )},
        }


class AdminCaliperForm(forms.ModelForm):
    class Meta:
        model = CaliperMeasurement
        exclude = ("user", "recorded_at")
        widgets = {
            "measured_at_jalali": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("تاریخ ثبت (فرمت: سال/ماه/روز)")}),
            **{field: forms.NumberInput(attrs={"class": INPUT_CLASS, "step": "0.1", "dir": "ltr", "data-select-all-on-focus": "true"}) for field in (
                "chest_armpit_men_mm",
                "axilla_mm",
                "subscapular_mm",
                "abdominal_mm",
                "suprailiac_mm",
                "chest_mm",
                "biceps_mm",
                "triceps_mm",
                "thigh_mm",
                "calf_mm",
            )},
        }


class AdminClientMediaForm(forms.ModelForm):
    class Meta:
        model = ClientMedia
        fields = ("image", "video")
        widgets = {
            "image": forms.ClearableFileInput(attrs={"class": INPUT_CLASS}),
            "video": forms.ClearableFileInput(attrs={"class": INPUT_CLASS}),
        }


class AdminClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ("title", "file")
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("مثلاً: برنامه تمرینی هفته ۱")}),
            "file": forms.ClearableFileInput(attrs={"class": INPUT_CLASS}),
        }


class AdminRoleToggleForm(forms.Form):
    is_admin = forms.BooleanField(required=False, label=_("نقش ادمین"))


class AdminBulkCoachAssignForm(forms.Form):
    coach = forms.ModelChoiceField(
        queryset=User.objects.filter(is_admin=True).order_by("fullname"),
        required=True,
        label=_("مربی"),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )


class AdminUserCoachForm(forms.Form):
    coach = forms.ModelChoiceField(
        queryset=User.objects.filter(is_admin=True).order_by("fullname"),
        required=False,
        label=_("مربی"),
        empty_label=_("بدون مربی"),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )


class LibrarySearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": _("نام را وارد کنید"),
            }
        ),
    )


class MuscleForm(forms.ModelForm):
    class Meta:
        model = Muscle
        fields = ("name", "name_en", "origin", "insertion", "nerve", "function_note", "image")
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام عضله")}),
            "name_en": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام انگلیسی عضله"), "dir": "ltr"}),
            "origin": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "insertion": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "nerve": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "function_note": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 2}),
            "image": forms.ClearableFileInput(attrs={"class": INPUT_CLASS}),
        }


def build_lookup_form(model, *, fields=("name", "name_en"), data=None, instance=None):
    widgets = {
        field: forms.TextInput(attrs={"class": INPUT_CLASS, **({"dir": "ltr"} if field.endswith("_en") else {})})
        for field in fields
    }
    form_class = forms.modelform_factory(model, fields=fields, widgets=widgets)
    return form_class(data, instance=instance)


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = (
            "name",
            "name_en",
            "primary_muscle",
            "secondary_muscle",
            "body_part",
            "movement_type",
            "joint_type",
            "power_type",
            "difficulty_level",
            "equipment_type",
            "execution_equipment_type",
            "secondary_movement_type",
            "pressure_type",
            "description",
            "media",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام حرکت")}),
            "name_en": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام انگلیسی حرکت"), "dir": "ltr"}),
            "primary_muscle": forms.Select(attrs={"class": INPUT_CLASS}),
            "secondary_muscle": forms.Select(attrs={"class": INPUT_CLASS}),
            "body_part": forms.Select(attrs={"class": INPUT_CLASS}),
            "movement_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "joint_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "power_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "difficulty_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "equipment_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "execution_equipment_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "secondary_movement_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "pressure_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3, "placeholder": _("توضیحات حرکت")}),
            "media": forms.ClearableFileInput(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["secondary_muscle"].required = False
        self.fields["secondary_muscle"].empty_label = _("بدون عضله فرعی")
        self.fields["pressure_type"].required = False
        self.fields["pressure_type"].empty_label = _("نامشخص")
        self.fields["execution_equipment_type"].required = False
        self.fields["execution_equipment_type"].empty_label = _("نامشخص")
        self.fields["secondary_movement_type"].required = False
        self.fields["secondary_movement_type"].empty_label = _("نامشخص")


class CorrectiveExerciseForm(forms.ModelForm):
    class Meta:
        model = CorrectiveExercise
        fields = ("name", "equipment", "abnormality_type", "description", "media")
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": _("نام حرکت")}),
            "equipment": forms.Select(attrs={"class": INPUT_CLASS}),
            "abnormality_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "description": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3, "placeholder": _("توضیحات")}),
            "media": forms.ClearableFileInput(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipment"].required = False
        self.fields["equipment"].empty_label = _("نامشخص")
        self.fields["abnormality_type"].required = False
        self.fields["abnormality_type"].empty_label = _("نامشخص")
