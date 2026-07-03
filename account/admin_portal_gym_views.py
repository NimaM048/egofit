from __future__ import annotations

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from account.admin_forms import CorrectiveExerciseForm, ExerciseForm, LibrarySearchForm, MuscleForm, build_lookup_form
from account.admin_portal_views import AdminPageMixin
from account.models import (
    CorrectiveExercise,
    Exercise,
    ExerciseAbnormalityType,
    ExerciseBodyPart,
    ExerciseDifficultyLevel,
    ExerciseEquipmentType,
    ExerciseExecutionEquipmentType,
    ExerciseJointType,
    ExerciseMovementType,
    ExercisePowerType,
    ExercisePressureType,
    ExerciseRepetitionType,
    ExerciseRestType,
    ExerciseSecondaryMovementType,
    ExerciseSetType,
    ExerciseSportType,
    Muscle,
)
from account.services.gym_library_service import GymLibraryService

gym_library_service = GymLibraryService()

DEFAULT_LOOKUP_FIELDS = ("name", "name_en")

LOOKUP_REGISTRY = {
    "body-part": {"model": ExerciseBodyPart, "title": _("بخش بدن")},
    "movement-type": {"model": ExerciseMovementType, "title": _("نوع حرکت")},
    "joint-type": {"model": ExerciseJointType, "title": _("نوع مفصل")},
    "power-type": {"model": ExercisePowerType, "title": _("نوع قدرت")},
    "difficulty-level": {"model": ExerciseDifficultyLevel, "title": _("سطح دشواری")},
    "equipment-type": {"model": ExerciseEquipmentType, "title": _("تجهیزات")},
    "execution-equipment-type": {"model": ExerciseExecutionEquipmentType, "title": _("نوع تجهیزات اجرایی")},
    "secondary-movement-type": {"model": ExerciseSecondaryMovementType, "title": _("نوع حرکت دوم")},
    "abnormality-type": {"model": ExerciseAbnormalityType, "title": _("ناهنجاری")},
    "pressure-type": {"model": ExercisePressureType, "title": _("نوع فشار")},
    "sport-type": {"model": ExerciseSportType, "title": _("نوع ورزش")},
    "set-type": {"model": ExerciseSetType, "title": _("نوع ست"), "fields": ("set_count", "goal")},
    "repetition-type": {"model": ExerciseRepetitionType, "title": _("نوع تکرار"), "fields": ("reps", "goal")},
    "rest-type": {"model": ExerciseRestType, "title": _("نوع استراحت"), "fields": ("rest_time", "goal")},
}


class GymLibraryView(AdminPageMixin, TemplateView):
    template_name = "admin_portal/gym/library.html"
    active_section = "library"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(gym_library_service.get_dashboard_context())
        return context


class MuscleListView(AdminPageMixin, TemplateView):
    template_name = "admin_portal/gym/muscle_list.html"
    active_section = "library"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get("query") or "").strip()
        context.update(
            {
                "form": LibrarySearchForm(initial={"query": query}),
                "search_query": query,
                "muscles": gym_library_service.search_muscles(query),
            }
        )
        return context


class MuscleFormView(AdminPageMixin, View):
    template_name = "admin_portal/gym/muscle_form.html"
    active_section = "library"

    def get(self, request, pk=None):
        instance = get_object_or_404(Muscle, pk=pk) if pk else None
        form = MuscleForm(instance=instance)
        return render(request, self.template_name, self._context(form, instance))

    def post(self, request, pk=None):
        instance = get_object_or_404(Muscle, pk=pk) if pk else None
        form = MuscleForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            gym_library_service.save_muscle(form)
            return redirect("register:admin_muscle_list")
        return render(request, self.template_name, self._context(form, instance))

    def _context(self, form, instance):
        return {
            "form": form,
            "muscle": instance,
            "active_section": self.active_section,
            "page_title": _("ویرایش عضله") if instance else _("افزودن عضله"),
        }


class MuscleDeleteView(AdminPageMixin, View):
    def post(self, request, pk):
        muscle = get_object_or_404(Muscle, pk=pk)
        gym_library_service.delete_muscle(muscle)
        return redirect("register:admin_muscle_list")


class ExerciseListView(AdminPageMixin, TemplateView):
    template_name = "admin_portal/gym/exercise_list.html"
    active_section = "library"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get("query") or "").strip()
        context.update(
            {
                "form": LibrarySearchForm(initial={"query": query}),
                "search_query": query,
                "exercises": gym_library_service.search_exercises(query),
            }
        )
        return context


class ExerciseFormView(AdminPageMixin, View):
    template_name = "admin_portal/gym/exercise_form.html"
    active_section = "library"

    def get(self, request, pk=None):
        instance = get_object_or_404(Exercise, pk=pk) if pk else None
        form = ExerciseForm(instance=instance)
        return render(request, self.template_name, self._context(form, instance))

    def post(self, request, pk=None):
        instance = get_object_or_404(Exercise, pk=pk) if pk else None
        form = ExerciseForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            gym_library_service.save_exercise(form)
            return redirect("register:admin_exercise_list")
        return render(request, self.template_name, self._context(form, instance))

    def _context(self, form, instance):
        return {
            "form": form,
            "exercise": instance,
            "active_section": self.active_section,
            "page_title": _("ویرایش حرکت") if instance else _("افزودن حرکت"),
        }


class ExerciseDeleteView(AdminPageMixin, View):
    def post(self, request, pk):
        exercise = get_object_or_404(Exercise, pk=pk)
        gym_library_service.delete_exercise(exercise)
        return redirect("register:admin_exercise_list")


class CorrectiveExerciseListView(AdminPageMixin, TemplateView):
    template_name = "admin_portal/gym/corrective_list.html"
    active_section = "library"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get("query") or "").strip()
        context.update(
            {
                "form": LibrarySearchForm(initial={"query": query}),
                "search_query": query,
                "correctives": gym_library_service.search_correctives(query),
            }
        )
        return context


class CorrectiveExerciseFormView(AdminPageMixin, View):
    template_name = "admin_portal/gym/corrective_form.html"
    active_section = "library"

    def get(self, request, pk=None):
        instance = get_object_or_404(CorrectiveExercise, pk=pk) if pk else None
        form = CorrectiveExerciseForm(instance=instance)
        return render(request, self.template_name, self._context(form, instance))

    def post(self, request, pk=None):
        instance = get_object_or_404(CorrectiveExercise, pk=pk) if pk else None
        form = CorrectiveExerciseForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            gym_library_service.save_corrective(form)
            return redirect("register:admin_corrective_list")
        return render(request, self.template_name, self._context(form, instance))

    def _context(self, form, instance):
        return {
            "form": form,
            "corrective": instance,
            "active_section": self.active_section,
            "page_title": _("ویرایش حرکت اصلاحی") if instance else _("افزودن حرکت اصلاحی"),
        }


class CorrectiveExerciseDeleteView(AdminPageMixin, View):
    def post(self, request, pk):
        corrective = get_object_or_404(CorrectiveExercise, pk=pk)
        gym_library_service.delete_corrective(corrective)
        return redirect("register:admin_corrective_list")


class LookupKeyMixin(AdminPageMixin):
    active_section = "library"

    def dispatch(self, request, *args, **kwargs):
        self.lookup_key = kwargs["key"]
        self.lookup_cfg = LOOKUP_REGISTRY.get(self.lookup_key)
        if not self.lookup_cfg:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lookup_key"] = self.lookup_key
        context["lookup_title"] = self.lookup_cfg["title"]
        return context

    @property
    def lookup_fields(self):
        return self.lookup_cfg.get("fields", DEFAULT_LOOKUP_FIELDS)


class LookupListView(LookupKeyMixin, TemplateView):
    template_name = "admin_portal/gym/lookup_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fields = self.lookup_fields
        context["items"] = [
            {
                "pk": obj.pk,
                "primary": getattr(obj, fields[0]),
                "secondary": getattr(obj, fields[1]) if len(fields) > 1 else "",
            }
            for obj in gym_library_service.list_lookup(self.lookup_cfg["model"])
        ]
        context["page_title"] = self.lookup_cfg["title"]
        return context


class LookupFormView(LookupKeyMixin, View):
    template_name = "admin_portal/gym/lookup_form.html"

    def get(self, request, key, pk=None):
        instance = get_object_or_404(self.lookup_cfg["model"], pk=pk) if pk else None
        form = build_lookup_form(self.lookup_cfg["model"], fields=self.lookup_fields, instance=instance)
        return render(request, self.template_name, self._context(form, instance))

    def post(self, request, key, pk=None):
        instance = get_object_or_404(self.lookup_cfg["model"], pk=pk) if pk else None
        form = build_lookup_form(self.lookup_cfg["model"], fields=self.lookup_fields, data=request.POST, instance=instance)
        if form.is_valid():
            gym_library_service.save_lookup(form)
            return redirect("register:admin_lookup_list", key=self.lookup_key)
        return render(request, self.template_name, self._context(form, instance))

    def _context(self, form, instance):
        return {
            "form": form,
            "item": instance,
            "lookup_key": self.lookup_key,
            "lookup_title": self.lookup_cfg["title"],
            "active_section": self.active_section,
            "page_title": _("ویرایش %(title)s") % {"title": self.lookup_cfg["title"]} if instance else _("افزودن %(title)s") % {"title": self.lookup_cfg["title"]},
        }


class LookupDeleteView(LookupKeyMixin, View):
    def post(self, request, key, pk):
        success, error_message = gym_library_service.delete_lookup(self.lookup_cfg["model"], pk)
        if not success:
            messages.error(request, error_message)
        return redirect("register:admin_lookup_list", key=self.lookup_key)
