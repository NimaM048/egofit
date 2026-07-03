from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.utils.translation import gettext_lazy as _

Gender = Literal["male", "female"]


@dataclass(frozen=True)
class CaliperSkinfolds:
    chest_armpit_men_mm: float | None = None
    axilla_mm: float | None = None
    subscapular_mm: float | None = None
    abdominal_mm: float | None = None
    suprailiac_mm: float | None = None
    chest_mm: float | None = None
    biceps_mm: float | None = None
    triceps_mm: float | None = None
    thigh_mm: float | None = None
    calf_mm: float | None = None

    @classmethod
    def from_model(cls, caliper) -> CaliperSkinfolds | None:
        if caliper is None:
            return None
        return cls(
            chest_armpit_men_mm=_to_float(caliper.chest_armpit_men_mm),
            axilla_mm=_to_float(caliper.axilla_mm),
            subscapular_mm=_to_float(caliper.subscapular_mm),
            abdominal_mm=_to_float(caliper.abdominal_mm),
            suprailiac_mm=_to_float(caliper.suprailiac_mm),
            chest_mm=_to_float(caliper.chest_mm),
            biceps_mm=_to_float(caliper.biceps_mm),
            triceps_mm=_to_float(caliper.triceps_mm),
            thigh_mm=_to_float(caliper.thigh_mm),
            calf_mm=_to_float(caliper.calf_mm),
        )


@dataclass(frozen=True)
class CircumferenceMeasures:
    wrist_cm: float | None = None
    forearm_cm: float | None = None
    arm_rest_cm: float | None = None
    arm_flexed_cm: float | None = None
    wrist_left_cm: float | None = None
    forearm_left_cm: float | None = None
    arm_rest_left_cm: float | None = None
    arm_flexed_left_cm: float | None = None
    head_cm: float | None = None
    neck_cm: float | None = None
    chest_cm: float | None = None
    shoulders_cm: float | None = None
    waist_cm: float | None = None
    abdomen_cm: float | None = None
    hips_cm: float | None = None
    thigh_cm: float | None = None
    calf_cm: float | None = None
    thigh_left_cm: float | None = None
    calf_left_cm: float | None = None
    sit_height_cm: float | None = None
    leg_length_cm: float | None = None
    shoulder_width_cm: float | None = None
    hip_width_cm: float | None = None
    elbow_width_cm: float | None = None
    knee_width_cm: float | None = None
    arm_length_cm: float | None = None

    @classmethod
    def from_model(cls, circumference) -> CircumferenceMeasures | None:
        if circumference is None:
            return None
        return cls(
            wrist_cm=_to_float(circumference.wrist_cm),
            forearm_cm=_to_float(circumference.forearm_cm),
            arm_rest_cm=_to_float(circumference.arm_rest_cm),
            arm_flexed_cm=_to_float(circumference.arm_flexed_cm),
            wrist_left_cm=_to_float(circumference.wrist_left_cm),
            forearm_left_cm=_to_float(circumference.forearm_left_cm),
            arm_rest_left_cm=_to_float(circumference.arm_rest_left_cm),
            arm_flexed_left_cm=_to_float(circumference.arm_flexed_left_cm),
            head_cm=_to_float(circumference.head_cm),
            neck_cm=_to_float(circumference.neck_cm),
            chest_cm=_to_float(circumference.chest_cm),
            shoulders_cm=_to_float(circumference.shoulders_cm),
            waist_cm=_to_float(circumference.waist_cm),
            abdomen_cm=_to_float(circumference.abdomen_cm),
            hips_cm=_to_float(circumference.hips_cm),
            thigh_cm=_to_float(circumference.thigh_cm),
            calf_cm=_to_float(circumference.calf_cm),
            thigh_left_cm=_to_float(circumference.thigh_left_cm),
            calf_left_cm=_to_float(circumference.calf_left_cm),
            sit_height_cm=_to_float(circumference.sit_height_cm),
            leg_length_cm=_to_float(circumference.leg_length_cm),
            shoulder_width_cm=_to_float(circumference.shoulder_width_cm),
            hip_width_cm=_to_float(circumference.hip_width_cm),
            elbow_width_cm=_to_float(circumference.elbow_width_cm),
            knee_width_cm=_to_float(circumference.knee_width_cm),
            arm_length_cm=_to_float(circumference.arm_length_cm),
        )


@dataclass(frozen=True)
class BodyFatResult:
    body_fat_percent: float
    body_density: float
    formula_name: str
    sites_used: tuple[str, ...]


@dataclass(frozen=True)
class BodyCompositionSnapshot:
    body_fat_percent: float | None
    body_fat_formula: str | None
    lean_mass_kg: float | None
    fat_mass_kg: float | None
    bmi: float | None
    whr: float | None
    whtr: float | None
    bmr: int | None
    tdee: int | None
    protein_min_g: int | None
    protein_max_g: int | None
    whr_status: str | None = None
    whtr_status: str | None = None
    body_frame_size: str | None = None
    endomorphy: float | None = None
    mesomorphy: float | None = None
    ectomorphy: float | None = None
    arm_ratio: float | None = None
    shoulder_hip_ratio: float | None = None


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _siri_body_fat_percent(body_density: float) -> float:
    return (495.0 / body_density) - 450.0


def _clamp_body_fat(value: float) -> float:
    return round(min(60.0, max(3.0, value)), 1)


def calculate_bmi(weight_kg: float | int | None, height_cm: float | int | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    height_m = float(height_cm) / 100.0
    if height_m <= 0:
        return None
    return round(float(weight_kg) / (height_m * height_m), 1)


def calculate_whr(waist_cm: float | None, hips_cm: float | None) -> float | None:
    if not waist_cm or not hips_cm:
        return None
    hips = float(hips_cm)
    if hips <= 0:
        return None
    return round(float(waist_cm) / hips, 2)


def calculate_whr_status(whr: float | None, gender: Gender | str | None) -> str | None:
    if whr is None or gender not in ("male", "female"):
        return None
    if gender == "male":
        ranges = ((0.90, _("مطلوب")), (0.95, _("متوسط")))
    else:
        ranges = ((0.80, _("مطلوب")), (0.85, _("متوسط")))
    for upper, label in ranges:
        if whr < upper:
            return label
    return _("پرخطر")


def calculate_whtr(waist_cm: float | None, height_cm: float | int | None) -> float | None:
    if not waist_cm or not height_cm:
        return None
    height = float(height_cm)
    if height <= 0:
        return None
    return round(float(waist_cm) / height, 2)


def calculate_whtr_status(whtr: float | None) -> str | None:
    if whtr is None:
        return None
    if whtr <= 0.50:
        return _("نرمال")
    if whtr <= 0.52:
        return _("نسبتا نامطلوب")
    if whtr <= 0.55:
        return _("پرخطر")
    return _("بسیار پرخطر")


def calculate_body_frame_size(wrist_cm: float | None, gender: Gender | str | None) -> str | None:
    if wrist_cm is None or gender not in ("male", "female"):
        return None
    wrist = float(wrist_cm)
    if gender == "male":
        if wrist > 18.5:
            return _("درشت")
        if wrist > 17:
            return _("متوسط")
        return _("ریز")
    if wrist > 17:
        return _("درشت")
    if wrist > 15.5:
        return _("متوسط")
    return _("ریز")


def calculate_arm_ratio(arm_flexed_cm: float | None, arm_rest_cm: float | None) -> float | None:
    if not arm_flexed_cm or not arm_rest_cm:
        return None
    rest = float(arm_rest_cm)
    if rest <= 0:
        return None
    return round(float(arm_flexed_cm) / rest, 2)


def calculate_shoulder_hip_ratio(shoulder_width_cm: float | None, hip_width_cm: float | None) -> float | None:
    if not shoulder_width_cm or not hip_width_cm:
        return None
    hip_width = float(hip_width_cm)
    if hip_width <= 0:
        return None
    return round(float(shoulder_width_cm) / hip_width, 2)


def calculate_somatotype(
    *,
    height_cm: float | int | None,
    weight_kg: float | int | None,
    triceps_mm: float | None,
    subscapular_mm: float | None,
    suprailiac_mm: float | None,
    calf_mm: float | None,
    elbow_width_cm: float | None,
    knee_width_cm: float | None,
    arm_rest_cm: float | None,
    calf_cm: float | None,
) -> tuple[float, float, float] | None:
    required = (
        height_cm, weight_kg, triceps_mm, subscapular_mm, suprailiac_mm, calf_mm,
        elbow_width_cm, knee_width_cm, arm_rest_cm, calf_cm,
    )
    if any(value is None for value in required):
        return None

    height = float(height_cm)
    weight = float(weight_kg)
    if height <= 0 or weight <= 0:
        return None

    skinfold_sum = float(triceps_mm) + float(subscapular_mm) + float(suprailiac_mm)
    x = skinfold_sum * (170.18 / height)
    endomorphy = -0.7182 + 0.1451 * x - 0.00068 * (x**2) + 0.0000014 * (x**3)

    corrected_arm_girth = float(arm_rest_cm) - float(triceps_mm) / 10
    corrected_calf_girth = float(calf_cm) - float(calf_mm) / 10
    mesomorphy = (
        0.858 * float(elbow_width_cm)
        + 0.601 * float(knee_width_cm)
        + 0.188 * corrected_arm_girth
        + 0.161 * corrected_calf_girth
        - 0.131 * height
        + 4.5
    )

    ponderal_index = height / (weight ** (1 / 3))
    if ponderal_index >= 40.75:
        ectomorphy = 0.732 * ponderal_index - 28.58
    elif ponderal_index > 38.25:
        ectomorphy = 0.463 * ponderal_index - 17.63
    else:
        ectomorphy = 0.1

    return round(endomorphy, 2), round(mesomorphy, 2), round(ectomorphy, 2)


def calculate_bmr_mifflin_st_jeor(
    *,
    weight_kg: float | int | None,
    height_cm: float | int | None,
    age: int | None,
    gender: Gender | str | None,
) -> int | None:
    if not weight_kg or not height_cm or age is None or not gender:
        return None
    base = (10.0 * float(weight_kg)) + (6.25 * float(height_cm)) - (5.0 * float(age))
    if gender == "female":
        return round(base - 161)
    if gender == "male":
        return round(base + 5)
    return None


def calculate_tdee(bmr: int | None, activity_factor: float = 1.55) -> int | None:
    if bmr is None:
        return None
    return round(bmr * activity_factor)


ACTIVITY_FACTORS: dict[str, float] = {
    "sedentary": 1.2,
    "low_active": 1.375,
    "moderate_active": 1.55,
    "active": 1.725,
    "high_active": 1.9,
}


def activity_factor_for_level(activity_level: str | None) -> float:
    return ACTIVITY_FACTORS.get(activity_level, 1.55)


SOMATOTYPE_INPUT_DEFAULTS_CM = {
    "shoulder_width_cm": 44.0,
    "hip_width_cm": 31.0,
    "elbow_width_cm": 9.5,
    "knee_width_cm": 7.0,
    "arm_length_cm": 33.0,
}


def calculate_lean_mass(weight_kg: float | int | None, body_fat_percent: float | None) -> float | None:
    if not weight_kg or body_fat_percent is None:
        return None
    return round(float(weight_kg) * (1.0 - body_fat_percent / 100.0), 1)


def calculate_fat_mass(weight_kg: float | int | None, body_fat_percent: float | None) -> float | None:
    if not weight_kg or body_fat_percent is None:
        return None
    return round(float(weight_kg) * body_fat_percent / 100.0, 1)


def calculate_protein_range(weight_kg: float | int | None) -> tuple[int | None, int | None]:
    if not weight_kg:
        return None, None
    weight = float(weight_kg)
    return round(weight * 1.6), round(weight * 2.2)


def _seven_site_values(
    skinfolds: CaliperSkinfolds,
    gender: Gender,
) -> tuple[tuple[float, ...], tuple[str, ...]] | None:
    if gender == "male":
        values = (
            skinfolds.chest_armpit_men_mm,
            skinfolds.axilla_mm,
            skinfolds.triceps_mm,
            skinfolds.subscapular_mm,
            skinfolds.abdominal_mm,
            skinfolds.suprailiac_mm,
            skinfolds.thigh_mm,
        )
        labels = (
            "chest_armpit_men_mm",
            "axilla_mm",
            "triceps_mm",
            "subscapular_mm",
            "abdominal_mm",
            "suprailiac_mm",
            "thigh_mm",
        )
    else:
        values = (
            skinfolds.chest_mm,
            skinfolds.axilla_mm,
            skinfolds.triceps_mm,
            skinfolds.subscapular_mm,
            skinfolds.abdominal_mm,
            skinfolds.suprailiac_mm,
            skinfolds.thigh_mm,
        )
        labels = (
            "chest_mm",
            "axilla_mm",
            "triceps_mm",
            "subscapular_mm",
            "abdominal_mm",
            "suprailiac_mm",
            "thigh_mm",
        )

    if any(value is None for value in values):
        return None
    return tuple(float(value) for value in values), labels


def _three_site_values(skinfolds: CaliperSkinfolds, gender: Gender) -> tuple[tuple[float, ...], tuple[str, ...]] | None:
    if gender == "male":
        values = (skinfolds.chest_armpit_men_mm, skinfolds.abdominal_mm, skinfolds.thigh_mm)
        labels = ("chest_armpit_men_mm", "abdominal_mm", "thigh_mm")
    else:
        values = (skinfolds.triceps_mm, skinfolds.suprailiac_mm, skinfolds.thigh_mm)
        labels = ("triceps_mm", "suprailiac_mm", "thigh_mm")

    if any(value is None for value in values):
        return None
    return tuple(float(value) for value in values), labels


def _jackson_pollock_7_density(sum_mm: float, age: int, gender: Gender) -> float:
    if gender == "male":
        return (
            1.112
            - (0.00043499 * sum_mm)
            + (0.00000055 * (sum_mm**2))
            - (0.00028826 * age)
        )
    return (
        1.097
        - (0.00046971 * sum_mm)
        + (0.00000056 * (sum_mm**2))
        - (0.00012828 * age)
    )


def _jackson_pollock_3_density(sum_mm: float, age: int, gender: Gender) -> float:
    if gender == "male":
        return (
            1.10938
            - (0.0008267 * sum_mm)
            + (0.0000016 * (sum_mm**2))
            - (0.0002574 * age)
        )
    return (
        1.0994921
        - (0.0009929 * sum_mm)
        + (0.0000023 * (sum_mm**2))
        - (0.0001392 * age)
    )


def _four_site_values(skinfolds: CaliperSkinfolds, gender: Gender) -> tuple[tuple[float, ...], tuple[str, ...]] | None:
    if gender == "male":
        values = (
            skinfolds.abdominal_mm,
            skinfolds.triceps_mm,
            skinfolds.thigh_mm,
            skinfolds.suprailiac_mm,
        )
        labels = ("abdominal_mm", "triceps_mm", "thigh_mm", "suprailiac_mm")
    else:
        values = (
            skinfolds.triceps_mm,
            skinfolds.suprailiac_mm,
            skinfolds.thigh_mm,
            skinfolds.abdominal_mm,
        )
        labels = ("triceps_mm", "suprailiac_mm", "thigh_mm", "abdominal_mm")

    if any(value is None for value in values):
        return None
    return tuple(float(value) for value in values), labels


def _jackson_pollock_4_density(sum_mm: float, age: int, gender: Gender) -> float:
    if gender == "male":
        return (
            1.10938
            - (0.0008267 * sum_mm)
            + (0.0000016 * (sum_mm**2))
            - (0.0002574 * age)
        )
    return (
        1.0994921
        - (0.0009929 * sum_mm)
        + (0.0000023 * (sum_mm**2))
        - (0.0001392 * age)
    )


def calculate_body_fat_from_circumference_navy(
    circumference: CircumferenceMeasures | None,
    *,
    height_cm: float | int | None,
    gender: Gender | str | None,
) -> BodyFatResult | None:
    import math

    if circumference is None or not height_cm or gender not in ("male", "female"):
        return None

    waist = circumference.waist_cm
    neck = circumference.neck_cm
    hips = circumference.hips_cm
    height = float(height_cm)
    if not waist or not neck or height <= 0:
        return None

    if gender == "male":
        if float(waist) <= float(neck):
            return None
        body_fat = 86.010 * math.log10(float(waist) - float(neck)) - 70.041 * math.log10(height) + 36.76
        sites = ("waist_cm", "neck_cm")
    else:
        if not hips or float(waist) + float(hips) <= float(neck):
            return None
        body_fat = (
            163.205 * math.log10(float(waist) + float(hips) - float(neck))
            - 97.684 * math.log10(height)
            - 78.387
        )
        sites = ("waist_cm", "neck_cm", "hips_cm")

    return BodyFatResult(
        body_fat_percent=_clamp_body_fat(body_fat),
        body_density=0.0,
        formula_name="Navy (circumference)",
        sites_used=sites,
    )


def calculate_body_fat_from_caliper(
    skinfolds: CaliperSkinfolds | None,
    *,
    age: int | None,
    gender: Gender | str | None,
    formula: str | None = None,
) -> BodyFatResult | None:
    if skinfolds is None or age is None or gender not in ("male", "female"):
        return None

    formula_key = (formula or "auto").strip().lower()

    if formula_key in ("circumference", "navy"):
        return None

    if formula_key in ("jp7", "7", "seven"):
        seven_site = _seven_site_values(skinfolds, gender)  # type: ignore[arg-type]
        if seven_site is None:
            return None
        values, labels = seven_site
        sum_mm = sum(values)
        density = _jackson_pollock_7_density(sum_mm, age, gender)  # type: ignore[arg-type]
        if density <= 0:
            return None
        return BodyFatResult(
            body_fat_percent=_clamp_body_fat(_siri_body_fat_percent(density)),
            body_density=round(density, 4),
            formula_name="Jackson-Pollock 7-site",
            sites_used=labels,
        )

    if formula_key in ("jp4", "4", "four"):
        four_site = _four_site_values(skinfolds, gender)  # type: ignore[arg-type]
        if four_site is None:
            return None
        values, labels = four_site
        sum_mm = sum(values)
        density = _jackson_pollock_4_density(sum_mm, age, gender)  # type: ignore[arg-type]
        if density <= 0:
            return None
        return BodyFatResult(
            body_fat_percent=_clamp_body_fat(_siri_body_fat_percent(density)),
            body_density=round(density, 4),
            formula_name="Jackson-Pollock 4-site",
            sites_used=labels,
        )

    if formula_key in ("jp3", "3", "three"):
        three_site = _three_site_values(skinfolds, gender)  # type: ignore[arg-type]
        if three_site is None:
            return None
        values, labels = three_site
        sum_mm = sum(values)
        density = _jackson_pollock_3_density(sum_mm, age, gender)  # type: ignore[arg-type]
        if density <= 0:
            return None
        return BodyFatResult(
            body_fat_percent=_clamp_body_fat(_siri_body_fat_percent(density)),
            body_density=round(density, 4),
            formula_name="Jackson-Pollock 3-site",
            sites_used=labels,
        )

    seven_site = _seven_site_values(skinfolds, gender)  # type: ignore[arg-type]
    if seven_site is not None:
        values, labels = seven_site
        sum_mm = sum(values)
        density = _jackson_pollock_7_density(sum_mm, age, gender)  # type: ignore[arg-type]
        if density <= 0:
            return None
        return BodyFatResult(
            body_fat_percent=_clamp_body_fat(_siri_body_fat_percent(density)),
            body_density=round(density, 4),
            formula_name="Jackson-Pollock 7-site",
            sites_used=labels,
        )

    three_site = _three_site_values(skinfolds, gender)  # type: ignore[arg-type]
    if three_site is not None:
        values, labels = three_site
        sum_mm = sum(values)
        density = _jackson_pollock_3_density(sum_mm, age, gender)  # type: ignore[arg-type]
        if density <= 0:
            return None
        return BodyFatResult(
            body_fat_percent=_clamp_body_fat(_siri_body_fat_percent(density)),
            body_density=round(density, 4),
            formula_name="Jackson-Pollock 3-site",
            sites_used=labels,
        )

    return None


def resolve_body_fat_result(
    *,
    skinfolds: CaliperSkinfolds | None,
    circumference: CircumferenceMeasures | None,
    height_cm: float | int | None,
    age: int | None,
    gender: Gender | str | None,
    formula: str | None = None,
) -> BodyFatResult | None:
    formula_key = (formula or "auto").strip().lower()
    if formula_key in ("circumference", "navy"):
        return calculate_body_fat_from_circumference_navy(
            circumference,
            height_cm=height_cm,
            gender=gender,
        )
    return calculate_body_fat_from_caliper(skinfolds, age=age, gender=gender, formula=formula_key)


def build_body_composition_snapshot(
    *,
    weight_kg: float | int | None,
    height_cm: float | int | None,
    age: int | None,
    gender: Gender | str | None,
    skinfolds: CaliperSkinfolds | None,
    circumference: CircumferenceMeasures | None,
    activity_level: str | None = None,
    body_fat_formula: str | None = None,
) -> BodyCompositionSnapshot:
    waist = circumference.waist_cm if circumference else None
    hips = circumference.hips_cm if circumference else None
    wrist = circumference.wrist_cm if circumference else None

    body_fat_result = resolve_body_fat_result(
        skinfolds=skinfolds,
        circumference=circumference,
        height_cm=height_cm,
        age=age,
        gender=gender,
        formula=body_fat_formula,
    )
    body_fat = body_fat_result.body_fat_percent if body_fat_result else None
    bmr = calculate_bmr_mifflin_st_jeor(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
    )
    protein_min, protein_max = calculate_protein_range(weight_kg)
    whr = calculate_whr(waist, hips)
    whtr = calculate_whtr(waist, height_cm)

    somatotype = calculate_somatotype(
        height_cm=height_cm,
        weight_kg=weight_kg,
        triceps_mm=skinfolds.triceps_mm if skinfolds else None,
        subscapular_mm=skinfolds.subscapular_mm if skinfolds else None,
        suprailiac_mm=skinfolds.suprailiac_mm if skinfolds else None,
        calf_mm=skinfolds.calf_mm if skinfolds else None,
        elbow_width_cm=(
            (circumference.elbow_width_cm or SOMATOTYPE_INPUT_DEFAULTS_CM["elbow_width_cm"])
            if circumference is not None else None
        ),
        knee_width_cm=(
            (circumference.knee_width_cm or SOMATOTYPE_INPUT_DEFAULTS_CM["knee_width_cm"])
            if circumference is not None else None
        ),
        arm_rest_cm=circumference.arm_rest_cm if circumference else None,
        calf_cm=circumference.calf_cm if circumference else None,
    )
    endomorphy, mesomorphy, ectomorphy = somatotype if somatotype else (None, None, None)
    shoulder_width = None
    hip_width = None
    if circumference is not None:
        shoulder_width = circumference.shoulder_width_cm or SOMATOTYPE_INPUT_DEFAULTS_CM["shoulder_width_cm"]
        hip_width = circumference.hip_width_cm or SOMATOTYPE_INPUT_DEFAULTS_CM["hip_width_cm"]

    return BodyCompositionSnapshot(
        body_fat_percent=body_fat,
        body_fat_formula=body_fat_result.formula_name if body_fat_result else None,
        lean_mass_kg=calculate_lean_mass(weight_kg, body_fat),
        fat_mass_kg=calculate_fat_mass(weight_kg, body_fat),
        bmi=calculate_bmi(weight_kg, height_cm),
        whr=whr,
        whtr=whtr,
        bmr=bmr,
        tdee=calculate_tdee(bmr, activity_factor_for_level(activity_level)),
        protein_min_g=protein_min,
        protein_max_g=protein_max,
        whr_status=calculate_whr_status(whr, gender),
        whtr_status=calculate_whtr_status(whtr),
        body_frame_size=calculate_body_frame_size(wrist, gender),
        endomorphy=endomorphy,
        mesomorphy=mesomorphy,
        ectomorphy=ectomorphy,
        arm_ratio=calculate_arm_ratio(
            circumference.arm_flexed_cm if circumference else None,
            circumference.arm_rest_cm if circumference else None,
        ),
        shoulder_hip_ratio=calculate_shoulder_hip_ratio(shoulder_width, hip_width),
    )


def bmi_category_label(bmi: float | None) -> str:
    if bmi is None:
        return _("ثبت نشده")
    if bmi < 18.5:
        return _("کم‌وزن")
    if bmi < 25:
        return _("نرمال")
    if bmi < 30:
        return _("اضافه‌وزن")
    return _("چاق")
