"""
خدمة محرك السمات الهولوغرامية الديناميكي والمستديم (Dynamic Theme Engine Service).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

توفر السمات الخمس الأساسية المتطابقة مع الواجهة الأمامية (presets.ts):
1. royal-gold (الملكي الذهبي)
2. quantum-cyan (السيان الكمي)
3. nebula-purple (سديم الأرجوان)
4. emerald-matrix (المصفوفة الزمردية)
5. arctic-platinum (البلاتين القطبي)
بالإضافة إلى إدارة السمات المخصصة، حفظ الإعداد النشط، والتحقق الصارم عند استيراد ملفات JSON.
"""

from __future__ import annotations

import json
import re
from typing import Any, Final
import uuid

from fastapi import HTTPException

from app.database import append_audit_log, db_session, utc_now_iso
from app.models import (
    ActiveThemeState,
    ThemeDefinition,
    ThemeModifiers,
    ThemesPayload,
    ThemeTokens,
)

DEFAULT_MODIFIERS_DICT: Final[dict[str, Any]] = {
    "glowIntensity": 58,
    "blurRadius": 16,
    "panelOpacity": 78,
    "animationIntensity": 85,
    "motionDisabled": False,
    "highContrast": False,
    "lowPowerMode": False,
}

PRESET_THEMES: Final[list[ThemeDefinition]] = [
    ThemeDefinition(
        id="royal-gold",
        nameAr="الملكي الذهبي (Royal Gold)",
        nameEn="Royal Gold",
        descriptionAr="فخامة سيادية بلمسات الذهب الملكي والسبائك الداكنة لرحلة التريليون.",
        descriptionEn="Sovereign luxury with luminous bullion gold over obsidian glass.",
        isCustom=False,
        tokens=ThemeTokens(
            bgBase="#07080d",
            bgElevated="#0e111a",
            bgSurface="#151a28",
            accentPrimary="#f5c451",
            accentSecondary="#ffe08a",
            accentTertiary="#38bdf8",
            textPrimary="#f8fafc",
            textSecondary="#cbd5e1",
            textMuted="#94a3b8",
            borderHolo="rgba(245, 196, 81, 0.36)",
            success="#10b981",
            danger="#f43f5e",
            warning="#f59e0b",
        ),
    ),
    ThemeDefinition(
        id="quantum-cyan",
        nameAr="السيان الكمي (Quantum Cyan)",
        nameEn="Quantum Cyan",
        descriptionAr="مركز قيادة كمي فائق الوضوح بإضاءة السيان الليزرية والياقوت الأزرق.",
        descriptionEn="High-precision quantum command aesthetics with laser cyan optics.",
        isCustom=False,
        tokens=ThemeTokens(
            bgBase="#040911",
            bgElevated="#081221",
            bgSurface="#0d1d33",
            accentPrimary="#06e8f9",
            accentSecondary="#67e8f9",
            accentTertiary="#818cf8",
            textPrimary="#f0f9ff",
            textSecondary="#bae6fd",
            textMuted="#7dd3fc",
            borderHolo="rgba(6, 232, 249, 0.36)",
            success="#10b981",
            danger="#fb7185",
            warning="#fbbf24",
        ),
    ),
    ThemeDefinition(
        id="nebula-purple",
        nameAr="سديم الأرجوان (Nebula Purple)",
        nameEn="Nebula Purple",
        descriptionAr="عمق فضائي متعدد الطبقات بطيف الأرجوان النجمي والوردي الكهرومغناطيسي.",
        descriptionEn="Deep-space holographic layers with stellar violet and magenta luminescence.",
        isCustom=False,
        tokens=ThemeTokens(
            bgBase="#090514",
            bgElevated="#120a24",
            bgSurface="#1c1136",
            accentPrimary="#c084fc",
            accentSecondary="#f472b6",
            accentTertiary="#22d3ee",
            textPrimary="#faf5ff",
            textSecondary="#e9d5ff",
            textMuted="#c4b5fd",
            borderHolo="rgba(192, 132, 252, 0.38)",
            success="#34d399",
            danger="#fb7185",
            warning="#facc15",
        ),
    ),
    ThemeDefinition(
        id="emerald-matrix",
        nameAr="المصفوفة الزمردية (Emerald Matrix)",
        nameEn="Emerald Matrix",
        descriptionAr="طابع خوارزمي كمي بدرجات الزمرد المشع لقراءة دفاتر الأوامر بسرعة قصوى.",
        descriptionEn="Algorithmic emerald phosphor matrix engineered for rapid orderbook reading.",
        isCustom=False,
        tokens=ThemeTokens(
            bgBase="#030b08",
            bgElevated="#071610",
            bgSurface="#0c231a",
            accentPrimary="#10f59c",
            accentSecondary="#6ee7b7",
            accentTertiary="#38bdf8",
            textPrimary="#ecfdf5",
            textSecondary="#a7f3d0",
            textMuted="#6ee7b7",
            borderHolo="rgba(16, 245, 156, 0.34)",
            success="#22c55e",
            danger="#f43f5e",
            warning="#eab308",
        ),
    ),
    ThemeDefinition(
        id="arctic-platinum",
        nameAr="البلاتين القطبي (Arctic Platinum)",
        nameEn="Arctic Platinum",
        descriptionAr="نقائض بلاتينية جليدية مع لمسات الكوبالت البارد وتباين مؤسسي ناصع.",
        descriptionEn="Crisp institutional platinum and glacial cobalt with ultra-clean legibility.",
        isCustom=False,
        tokens=ThemeTokens(
            bgBase="#0b1017",
            bgElevated="#131b26",
            bgSurface="#1c2736",
            accentPrimary="#e2e8f0",
            accentSecondary="#38bdf8",
            accentTertiary="#94a3b8",
            textPrimary="#ffffff",
            textSecondary="#dbeafe",
            textMuted="#94a3b8",
            borderHolo="rgba(226, 232, 240, 0.38)",
            success="#10b981",
            danger="#ef4444",
            warning="#f59e0b",
        ),
    ),
    ThemeDefinition(
        id="obsidian-black",
        nameAr="الأوبسيديان الأسود (Obsidian Black)",
        nameEn="Obsidian Black",
        descriptionAr="سواد نقي مطلق بلمسات دقيقة من الذهب الخالص والبلاتين لأقصى درجات التركيز.",
        descriptionEn="Pure obsidian black with minimal refined gold and platinum accents.",
        isCustom=False,
        tokens=ThemeTokens(
            bgBase="#000000",
            bgElevated="#060608",
            bgSurface="#0c0d10",
            accentPrimary="#d4af37",
            accentSecondary="#e2e8f0",
            accentTertiary="#94a3b8",
            textPrimary="#f8fafc",
            textSecondary="#cbd5e1",
            textMuted="#94a3b8",
            borderHolo="rgba(212, 175, 55, 0.32)",
            success="#10b981",
            danger="#f43f5e",
            warning="#f59e0b",
        ),
    ),
]

PRESET_IDS: Final[set[str]] = {t.id for t in PRESET_THEMES}
COLOR_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\))$"
)


def _is_valid_css_color(value: Any) -> bool:
    """التحقق من أن القيمة النصية تمثل لون CSS آمناً وصالحاً (Hex أو RGB/RGBA أو HSL)."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return bool(stripped and len(stripped) <= 64 and COLOR_PATTERN.match(stripped))


def get_active_theme_state() -> ActiveThemeState:
    """استرجاع حالة السمة النشطة ومعاملاتها من SQLite."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM active_theme_state WHERE id = 1"
        ).fetchone()

    if row is None:
        return ActiveThemeState(
            activeThemeId="royal-gold",
            customOverrides={},
            modifiers=ThemeModifiers(**DEFAULT_MODIFIERS_DICT),
        )

    overrides = json.loads(row["custom_overrides_json"] or "{}")
    modifiers_raw = {
        **DEFAULT_MODIFIERS_DICT,
        **json.loads(row["modifiers_json"] or "{}"),
    }
    return ActiveThemeState(
        activeThemeId=row["active_theme_id"],
        customOverrides=overrides,
        modifiers=ThemeModifiers(**modifiers_raw),
    )


def get_custom_themes() -> list[ThemeDefinition]:
    """استرجاع جميع السمات المخصصة المحفوظة في SQLite."""
    with db_session() as conn:
        rows = conn.execute(
            "SELECT theme_json FROM custom_themes ORDER BY updated_at ASC"
        ).fetchall()

    themes: list[ThemeDefinition] = []
    for r in rows:
        data = json.loads(r["theme_json"])
        data["isCustom"] = True
        themes.append(ThemeDefinition(**data))
    return themes


def get_themes_payload() -> ThemesPayload:
    """استرجاع الحمولة المتكاملة للسمات الأساسية والمخصصة والإعداد النشط."""
    return ThemesPayload(
        presets=[p.model_copy(deep=True) for p in PRESET_THEMES],
        customThemes=get_custom_themes(),
        activeState=get_active_theme_state(),
    )


def save_active_theme_state(state: ActiveThemeState) -> ActiveThemeState:
    """حفظ السمة النشطة وتعديلات الألوان ومعاملات التوهج والحركة في SQLite."""
    # التحقق من سلامة قيم الألوان المخصصة إن وجدت
    cleaned_overrides: dict[str, str] = {}
    valid_token_keys = set(ThemeTokens.model_fields.keys())
    for key, val in state.customOverrides.items():
        if key in valid_token_keys and _is_valid_css_color(val):
            cleaned_overrides[key] = val.strip()

    normalized_state = ActiveThemeState(
        activeThemeId=state.activeThemeId.strip() or "royal-gold",
        customOverrides=cleaned_overrides,
        modifiers=state.modifiers,
    )

    with db_session() as conn:
        conn.execute(
            """
            UPDATE active_theme_state
            SET active_theme_id = ?,
                custom_overrides_json = ?,
                modifiers_json = ?,
                updated_at = ?
            WHERE id = 1
            """,
            (
                normalized_state.activeThemeId,
                json.dumps(normalized_state.customOverrides, ensure_ascii=False),
                json.dumps(normalized_state.modifiers.model_dump(), ensure_ascii=False),
                utc_now_iso(),
            ),
        )
    return normalized_state


def apply_quick_theme_patch(
    theme_id: str | None = None,
    low_power: bool | None = None,
    high_contrast: bool | None = None,
    motion_disabled: bool | None = None,
) -> ActiveThemeState:
    """تحديث سريع للسمة أو خصائص الوصول من الأوامر الصوتية أو النصية."""
    current = get_active_theme_state()
    mods = current.modifiers.model_dump()
    if low_power is not None:
        mods["lowPowerMode"] = low_power
    if high_contrast is not None:
        mods["highContrast"] = high_contrast
    if motion_disabled is not None:
        mods["motionDisabled"] = motion_disabled

    updated = ActiveThemeState(
        activeThemeId=theme_id if theme_id else current.activeThemeId,
        customOverrides=current.customOverrides,
        modifiers=ThemeModifiers(**mods),
    )
    return save_active_theme_state(updated)


def save_custom_theme(theme: ThemeDefinition) -> ThemeDefinition:
    """حفظ سمة مخصصة جديدة أو تحديث سمة مخصصة قائمة مع منع الكتابة فوق السمات الأساسية."""
    clean_id = theme.id.strip()
    if not clean_id:
        clean_id = f"custom-{uuid.uuid4().hex[:8]}"

    if clean_id in PRESET_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"لا يمكن استبدال السمة الأساسية المدمجة: {clean_id}",
        )

    for field_name, color_val in theme.tokens.model_dump().items():
        if not _is_valid_css_color(color_val):
            raise HTTPException(
                status_code=400,
                detail=f"قيمة لونية غير صالحة في الحقل {field_name}: {color_val}",
            )

    normalized = theme.model_copy(
        update={
            "id": clean_id,
            "isCustom": True,
            "nameAr": theme.nameAr.strip() or "سمة مخصصة",
            "nameEn": theme.nameEn.strip() or "Custom Theme",
        }
    )

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO custom_themes (id, theme_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                theme_json = excluded.theme_json,
                updated_at = excluded.updated_at
            """,
            (
                normalized.id,
                json.dumps(normalized.model_dump(), ensure_ascii=False),
                utc_now_iso(),
            ),
        )
        append_audit_log(
            actor="THEME_ENGINE",
            source="TERMINAL",
            action="SAVE_CUSTOM_THEME",
            severity="INFO",
            details_ar=f"تم حفظ السمة المخصصة «{normalized.nameAr}» ({normalized.id}).",
            details_en=f"Saved custom theme '{normalized.nameEn}' ({normalized.id}).",
            conn=conn,
        )

    return normalized


def delete_custom_theme(theme_id: str) -> dict[str, bool]:
    """حذف سمة مخصصة من SQLite وإعادة السمة النشطة إلى الملكي الذهبي إذا كانت هي المحذوفة."""
    if theme_id in PRESET_IDS:
        raise HTTPException(
            status_code=400,
            detail="لا يمكن حذف السمات الخمس الأساسية للنظام.",
        )

    with db_session() as conn:
        cur = conn.execute("DELETE FROM custom_themes WHERE id = ?", (theme_id,))
        deleted = cur.rowcount > 0
        if deleted:
            active_row = conn.execute(
                "SELECT active_theme_id FROM active_theme_state WHERE id = 1"
            ).fetchone()
            if active_row and active_row["active_theme_id"] == theme_id:
                conn.execute(
                    "UPDATE active_theme_state SET active_theme_id = 'royal-gold', updated_at = ? WHERE id = 1",
                    (utc_now_iso(),),
                )

    return {"deleted": deleted}


def import_theme_config(payload: dict[str, Any]) -> ThemeDefinition:
    """
    التحقق الصارم من ملف إعداد السمة المستورد (JSON) وحفظه كسمة مخصصة.
    يدعم كلاً من صيغة الحزمة المصدرة ({ "theme": {...}, "modifiers": {...} }) أو كائن السمة المباشر.
    """
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="يجب أن يكون ملف السمة المستورد كائن JSON صالحاً.",
        )

    candidate = payload.get("theme") if isinstance(payload.get("theme"), dict) else payload
    tokens_raw = candidate.get("tokens")
    if not isinstance(tokens_raw, dict):
        raise HTTPException(
            status_code=400,
            detail="بنية ملف السمة غير مكتملة: الحقل tokens مفقود أو غير صالح.",
        )

    required_keys = ("bgBase", "bgSurface", "accentPrimary", "textPrimary")
    for req_key in required_keys:
        val = tokens_raw.get(req_key)
        if not _is_valid_css_color(val):
            raise HTTPException(
                status_code=400,
                detail=f"الحقل اللوني الإلزامي مفقود أو غير صالح: {req_key}",
            )

    fallback_tokens = PRESET_THEMES[0].tokens.model_dump()
    merged_tokens: dict[str, str] = {}
    for k, default_v in fallback_tokens.items():
        incoming_v = tokens_raw.get(k)
        if incoming_v is not None:
            if not _is_valid_css_color(incoming_v):
                raise HTTPException(
                    status_code=400,
                    detail=f"لون غير صالح في الرمز {k}: {incoming_v}",
                )
            merged_tokens[k] = incoming_v.strip()
        else:
            merged_tokens[k] = default_v

    raw_id = str(candidate.get("id") or "").strip()
    if not raw_id or raw_id in PRESET_IDS:
        theme_id = f"custom-import-{uuid.uuid4().hex[:8]}"
    elif not raw_id.startswith("custom-"):
        theme_id = f"custom-{raw_id}"
    else:
        theme_id = raw_id

    default_mods = candidate.get("defaultModifiers") or payload.get("modifiers")
    clean_default_mods: dict[str, float | bool] | None = None
    if isinstance(default_mods, dict):
        validated_mods = ThemeModifiers(**{**DEFAULT_MODIFIERS_DICT, **default_mods})
        clean_default_mods = validated_mods.model_dump()

    imported_theme = ThemeDefinition(
        id=theme_id,
        nameAr=str(candidate.get("nameAr") or "سمة مستوردة").strip(),
        nameEn=str(candidate.get("nameEn") or "Imported Theme").strip(),
        descriptionAr=str(
            candidate.get("descriptionAr") or "سمة مستوردة ومحققة عبر محرك السمات."
        ).strip(),
        descriptionEn=str(
            candidate.get("descriptionEn") or "Imported and validated via Theme Engine."
        ).strip(),
        isCustom=True,
        tokens=ThemeTokens(**merged_tokens),
        defaultModifiers=clean_default_mods,
    )

    return save_custom_theme(imported_theme)
