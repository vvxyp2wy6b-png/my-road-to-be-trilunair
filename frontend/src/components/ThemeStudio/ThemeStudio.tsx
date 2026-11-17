/**
 * استوديو السمات الهولوغرامية الديناميكي (Dynamic Holographic Theme Studio)
 * My Road to be Trilunair Dr.MaJoOoOoOoD
 *
 * المزايا المعمارية:
 * 1. تبديل فوري بين السمات الخمس الأساسية (Royal Gold, Quantum Cyan, Nebula Purple, Emerald Matrix, Arctic Platinum)
 *    بالإضافة إلى السمات المخصصة المحفوظة محلياً وعلى قاعدة بيانات الخادم.
 * 2. تخصيص حي لرموز الألوان (Tokens) والمؤثرات البصرية (التوهج، الضبابية، الشفافية، كثافة الحركة) عبر متغيرات CSS القياسية.
 * 3. أوضاع الوصولية والأداء: تعطيل الحركة، التباين العالي (High-Contrast)، ووضع الطاقة المنخفضة (Low-Power GPU Mode).
 * 4. حفظ سمات مخصصة مستديمة، وتصدير واستيراد ملفات الإعداد بصيغة JSON مع التحقق البنيوي الكامل.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Check,
  Copy,
  Download,
  Eye,
  FileJson,
  Palette,
  Plus,
  RotateCcw,
  Sliders,
  Sparkles,
  Trash2,
  Upload,
  Zap,
} from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import type { ThemeDefinition, ThemeModifiers, ThemeTokens } from '../../types/trilunair';

type EditableColorKey = 'accentPrimary' | 'accentSecondary' | 'bgBase' | 'bgSurface';

interface ColorPickerField {
  key: EditableColorKey;
  labelAr: string;
  labelEn: string;
  hintAr: string;
  hintEn: string;
}

const COLOR_PICKER_FIELDS: ColorPickerField[] = [
  {
    key: 'accentPrimary',
    labelAr: 'اللون التوكيدي الأساسي (Accent Primary)',
    labelEn: 'Primary Accent Token',
    hintAr: 'يتحكم في الإضاءة الهولوغرامية والأزرار الرئيسية والحدود النشطة',
    hintEn: 'Controls primary holographic glow, primary buttons, and active borders',
  },
  {
    key: 'accentSecondary',
    labelAr: 'اللون التوكيدي الثانوي (Accent Secondary)',
    labelEn: 'Secondary Accent Token',
    hintAr: 'يتحكم في التدرجات الضوئية المساندة واللمسات الطيفية',
    hintEn: 'Controls secondary spectral highlights and gradients',
  },
  {
    key: 'bgBase',
    labelAr: 'خلفية الأساس العميقة (Base Background)',
    labelEn: 'Deep Base Background',
    hintAr: 'اللون الأساسي لخلفية فضاء مركز القيادة',
    hintEn: 'Foundational canvas background of the command center',
  },
  {
    key: 'bgSurface',
    labelAr: 'سطح الألواح الزجاجية (Surface Glass)',
    labelEn: 'Holographic Surface Glass',
    hintAr: 'طبقة البطاقات الزجاجية ولوحات البيانات',
    hintEn: 'Glassmorphism card and panel surface tint',
  },
];

interface SliderControlField {
  key: keyof Pick<
    ThemeModifiers,
    'glowIntensity' | 'blurRadius' | 'panelOpacity' | 'animationIntensity'
  >;
  min: number;
  max: number;
  unit: string;
  labelAr: string;
  labelEn: string;
  descAr: string;
  descEn: string;
}

const SLIDER_CONTROLS: SliderControlField[] = [
  {
    key: 'glowIntensity',
    min: 0,
    max: 100,
    unit: '%',
    labelAr: 'شدة التوهج الهولوغرامي',
    labelEn: 'Glow Intensity',
    descAr: 'قوة الهالة الضوئية حول البطاقات دون التأثير على وضوح الأرقام',
    descEn: 'Ambient edge luminescence without affecting number legibility',
  },
  {
    key: 'blurRadius',
    min: 0,
    max: 32,
    unit: 'px',
    labelAr: 'نصف قطر الضبابية الزجاجية',
    labelEn: 'Glass Blur Radius',
    descAr: 'عمق العزل البصري لطبقات الزجاج الهولوغرامي (Backdrop Blur)',
    descEn: 'Backdrop glassmorphism depth across layered panels',
  },
  {
    key: 'panelOpacity',
    min: 40,
    max: 98,
    unit: '%',
    labelAr: 'عتامة الألواح الزجاجية',
    labelEn: 'Panel Opacity',
    descAr: 'نسبة كثافة خلفية الألواح لضمان أعلى قراءة للأرقام المالية',
    descEn: 'Surface solidity for crisp financial data contrast',
  },
  {
    key: 'animationIntensity',
    min: 0,
    max: 100,
    unit: '%',
    labelAr: 'كثافة الحركة والانتقالات',
    labelEn: 'Animation Intensity',
    descAr: 'سرعة ومدى الاستجابة الحركية للعناصر التفاعلية',
    descEn: 'Scale of interactive hover and pulse transitions',
  },
];

/**
 * ضمان توافق القيمة اللونية مع عنصر input[type="color"] القياسي دون أي ألوان ثابتة مضمنة
 */
function normalizePickerHex(value: string, fallback: string): string {
  const trimmed = value.trim();
  if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) {
    return trimmed.toLowerCase();
  }
  return fallback;
}

/**
 * بطاقة عرض وتبديل السمة مع عينات الألوان الحية من رموز السمة (theme.tokens)
 */
const ThemePresetCard: React.FC<{
  theme: ThemeDefinition;
  isActive: boolean;
  isAr: boolean;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
}> = ({ theme, isActive, isAr, onSelect, onDelete }) => {
  const swatchTokens: Array<{ key: keyof ThemeTokens; label: string }> = [
    { key: 'bgBase', label: 'Base' },
    { key: 'bgSurface', label: 'Surface' },
    { key: 'accentPrimary', label: 'Primary' },
    { key: 'accentSecondary', label: 'Secondary' },
    { key: 'accentTertiary', label: 'Tertiary' },
  ];

  return (
    <div
      className="holo-panel"
      style={{
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '0.8rem',
        borderColor: isActive ? 'var(--accent-primary)' : 'var(--border-holo)',
        boxShadow: isActive ? 'var(--shadow-glow-strong)' : 'var(--shadow-holo)',
      }}
    >
      <div>
        {/* رأس البطاقة وشارة التفعيل */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '0.5rem',
            marginBottom: '0.45rem',
          }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.98rem', color: 'var(--text-primary)' }}>
              {isAr ? theme.nameAr : theme.nameEn}
            </div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              {isAr ? theme.nameEn : theme.nameAr}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
            {theme.isCustom && (
              <span className="holo-badge">
                {isAr ? 'مخصصة' : 'Custom'}
              </span>
            )}
            {isActive && (
              <span className="holo-badge holo-badge-accent">
                <Check size={12} aria-hidden="true" />
                <span>{isAr ? 'السمة النشطة' : 'Active'}</span>
              </span>
            )}
          </div>
        </div>

        {/* وصف السمة */}
        <p
          style={{
            margin: '0 0 0.75rem',
            fontSize: '0.83rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}
        >
          {isAr ? theme.descriptionAr : theme.descriptionEn}
        </p>

        {/* شريط عينات الألوان المقروءة مباشرة من theme.tokens */}
        <div
          aria-label={isAr ? 'عينات ألوان السمة' : 'Theme color token swatches'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.45rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            background: theme.tokens.bgBase,
          }}
        >
          {swatchTokens.map((swatch) => (
            <span
              key={swatch.key}
              title={`${swatch.label}: ${theme.tokens[swatch.key]}`}
              style={{
                flex: 1,
                height: '24px',
                borderRadius: '6px',
                background: theme.tokens[swatch.key],
                border: '1px solid var(--border-subtle)',
              }}
            />
          ))}
        </div>
      </div>

      {/* أزرار التفعيل والحذف للسمات المخصصة */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <button
          type="button"
          className={isActive ? 'holo-btn holo-btn-primary' : 'holo-btn'}
          onClick={() => onSelect(theme.id)}
          aria-pressed={isActive}
          style={{ flex: 1, minHeight: '44px' }}
        >
          <Sparkles size={15} aria-hidden="true" />
          <span>
            {isActive
              ? isAr
                ? 'مُفعّلة حالياً'
                : 'Currently Active'
              : isAr
                ? 'تطبيق السمة فوراً'
                : 'Apply Theme'}
          </span>
        </button>

        {theme.isCustom && onDelete && (
          <button
            type="button"
            className="holo-btn holo-btn-danger"
            onClick={() => onDelete(theme.id)}
            style={{ minHeight: '44px', padding: '0.45rem 0.75rem' }}
            aria-label={
              isAr
                ? `حذف السمة المخصصة ${theme.nameAr}`
                : `Delete custom theme ${theme.nameEn}`
            }
            title={isAr ? 'حذف السمة المخصصة' : 'Delete custom theme'}
          >
            <Trash2 size={16} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
};

/**
 * مفتاح تبديل وصولي قياسي (Accessible Switch Control)
 */
const AccessibleToggleRow: React.FC<{
  id: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  title: string;
  description: string;
  badgeText: string;
}> = ({ id, checked, onChange, title, description, badgeText }) => (
  <div
    className="holo-panel-subtle"
    style={{
      padding: '0.75rem 0.9rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '0.85rem',
    }}
  >
    <div>
      <label
        htmlFor={id}
        style={{
          display: 'block',
          fontWeight: 700,
          fontSize: '0.9rem',
          color: 'var(--text-primary)',
          cursor: 'pointer',
        }}
      >
        {title}
      </label>
      <div style={{ fontSize: '0.79rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
        {description}
      </div>
    </div>

    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={checked ? 'holo-btn holo-btn-primary' : 'holo-btn'}
      style={{ minHeight: '44px', minWidth: '108px', flexShrink: 0 }}
    >
      {checked && <Check size={15} aria-hidden="true" />}
      <span>{badgeText}</span>
    </button>
  </div>
);

/**
 * المكون الرئيسي لاستوديو السمات وتخصيص الهوية البصرية الهولوغرامية (ThemeStudio)
 */
export const ThemeStudio: React.FC = () => {
  const {
    language,
    presets,
    customThemes,
    activeState,
    currentTheme,
    effectiveTokens,
    selectTheme,
    updateTokenOverrides,
    resetOverrides,
    updateModifiers,
    saveAsCustomTheme,
    deleteCustomTheme,
    exportCurrentThemeJson,
    importThemeFromJson,
  } = useTheme();

  const isAr = language === 'ar';

  const [customNameAr, setCustomNameAr] = useState<string>('');
  const [customNameEn, setCustomNameEn] = useState<string>('');
  const [isSavingCustom, setIsSavingCustom] = useState<boolean>(false);

  const [copiedExport, setCopiedExport] = useState<boolean>(false);

  const [importJsonInput, setImportJsonInput] = useState<string>('');
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // توليد حزمة JSON الحية تلقائياً عند أي تغيير في السمة أو المعاملات
  const liveExportJson = useMemo(() => exportCurrentThemeJson(), [exportCurrentThemeJson]);

  // إغلاق رسائل التنبيه عند الضغط على مفتاح Escape
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && feedback) {
        setFeedback(null);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [feedback]);

  /**
   * حفظ الإعدادات الحالية كسمة مخصصة مستديمة في LocalStorage والخادم
   */
  const handleSaveCustomTheme = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (isSavingCustom) return;
      setIsSavingCustom(true);
      setFeedback(null);
      try {
        const finalAr = customNameAr.trim() || `سمة د. مجود (${customThemes.length + 1})`;
        const finalEn = customNameEn.trim() || `Dr. MaJoOoOoOoD Theme #${customThemes.length + 1}`;
        const saved = await saveAsCustomTheme(finalAr, finalEn);
        setCustomNameAr('');
        setCustomNameEn('');
        setFeedback({
          type: 'success',
          message: isAr
            ? `تم حفظ وتفعيل السمة المخصصة بنجاح: ${saved.nameAr}`
            : `Custom theme saved and activated: ${saved.nameEn}`,
        });
      } catch (err) {
        setFeedback({
          type: 'error',
          message:
            err instanceof Error
              ? err.message
              : isAr
                ? 'تعذر حفظ السمة المخصصة.'
                : 'Failed to save custom theme.',
        });
      } finally {
        setIsSavingCustom(false);
      }
    },
    [customNameAr, customNameEn, customThemes.length, isAr, isSavingCustom, saveAsCustomTheme]
  );

  /**
   * تصدير السمة الحالية إلى ملف JSON قابل للتنزيل وعرضها في مربع المعاينة
   */
  const handleExportJson = useCallback(() => {
    const jsonPayload = exportCurrentThemeJson();
    setCopiedExport(false);

    try {
      const blob = new Blob([jsonPayload], { type: 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `trilunair-theme-${currentTheme.id}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);

      setFeedback({
        type: 'success',
        message: isAr
          ? 'تم توليد وتنزيل ملف السمة (JSON) بنجاح، كما يمكنك نسخه أدناه.'
          : 'Theme JSON exported and downloaded. You can also copy it below.',
      });
    } catch {
      setFeedback({
        type: 'success',
        message: isAr
          ? 'تم توليد كود JSON للسمة أدناه — جاهز للنسخ المباشر.'
          : 'Theme JSON generated below — ready to copy.',
      });
    }
  }, [currentTheme.id, exportCurrentThemeJson, isAr]);

  /**
   * نسخ JSON المصدر إلى الحافظة
   */
  const handleCopyExportedJson = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(liveExportJson);
      setCopiedExport(true);
      window.setTimeout(() => setCopiedExport(false), 2200);
    } catch {
      // في حال عدم توفر الحافظة تبقى القيمة محددة وقابلة للنسخ اليدوي
    }
  }, [liveExportJson]);

  /**
   * التحقق من نص JSON واستيراد السمة
   */
  const executeImportJson = useCallback(
    async (rawText: string) => {
      if (!rawText.trim()) {
        setFeedback({
          type: 'error',
          message: isAr
            ? 'يرجى لصق محتوى JSON صالح أو اختيار ملف .json أولاً.'
            : 'Please paste valid JSON content or upload a .json file first.',
        });
        return;
      }

      setIsImporting(true);
      setFeedback(null);
      try {
        const imported = await importThemeFromJson(rawText);
        setImportJsonInput('');
        setFeedback({
          type: 'success',
          message: isAr
            ? `تم استيراد وتفعيل السمة بنجاح: ${imported.nameAr}`
            : `Successfully imported and applied theme: ${imported.nameEn}`,
        });
      } catch (err) {
        setFeedback({
          type: 'error',
          message:
            err instanceof Error
              ? err.message
              : isAr
                ? 'فشل التحقق من بنية ملف السمة JSON.'
                : 'Theme JSON validation failed.',
        });
      } finally {
        setIsImporting(false);
      }
    },
    [importThemeFromJson, isAr]
  );

  /**
   * قراءة ملف JSON مرفوع من جهاز المستخدم واستيراده فوراً
   */
  const handleFileUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        const content = await file.text();
        setImportJsonInput(content);
        await executeImportJson(content);
      } catch {
        setFeedback({
          type: 'error',
          message: isAr
            ? 'تعذر قراءة الملف المرفوع. تأكد أنه ملف نصي بصيغة .json'
            : 'Unable to read uploaded file. Please ensure it is a valid .json file.',
        });
      } finally {
        event.target.value = '';
      }
    },
    [executeImportJson, isAr]
  );

  const hasOverrides = Object.keys(activeState.customOverrides).length > 0;
  const fallbackThemeTokens = presets[0]?.tokens || currentTheme.tokens;

  return (
    <section
      aria-label={
        isAr
          ? 'استوديو السمات الهولوغرامية والتخصيص البصري'
          : 'Dynamic Holographic Theme Studio'
      }
      style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
    >
      {/* لوحة العنوان والمعاينة الحية لوضوح الأرقام المالية */}
      <div
        className="holo-panel"
        style={{
          padding: '1.25rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <Palette size={22} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>
              {isAr
                ? 'استوديو السمات الهولوغرامية ومحرك التخصيص الحي'
                : 'Dynamic Holographic Theme Studio & Token Engine'}
            </h2>
            <span className="holo-badge holo-badge-accent">
              {isAr ? currentTheme.nameAr : currentTheme.nameEn}
            </span>
          </div>
          <p style={{ margin: '0.35rem 0 0', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
            {isAr
              ? 'جميع الألوان والضبابية والتوهج والحركة تُحقن لحظياً عبر متغيرات CSS القياسية مع استدامة مزدوجة وحفاظ صارم على وضوح الأرقام المالية.'
              : 'All color tokens, glass blur, glow, and motion scale update instantaneously via CSS variables with dual persistence and strict financial legibility.'}
          </p>
        </div>

        {/* بطاقة فحص وضوح الأرقام الجدولية تحت السمة الحالية */}
        <div
          className="holo-panel-subtle"
          style={{
            padding: '0.65rem 1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div style={{ fontSize: '0.73rem', color: 'var(--text-muted)' }}>
              {isAr ? 'معاينة وضوح هدف التريليون' : 'Trilunair Legibility Check'}
            </div>
            <div
              className="tabular-nums"
              style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--accent-primary)' }}
            >
              $1,000,000,000,000.00
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <span className="holo-badge holo-badge-success tabular-nums">+12.84%</span>
            <span className="holo-badge holo-badge-danger tabular-nums">-0.42% DD</span>
          </div>
        </div>
      </div>

      {/* شريط التنبيهات الفورية لعمليات الحفظ والتصدير والاستيراد */}
      {feedback && (
        <div
          role="status"
          aria-live="polite"
          className="holo-panel"
          style={{
            padding: '0.75rem 1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.75rem',
            borderColor:
              feedback.type === 'success' ? 'var(--status-success)' : 'var(--status-danger)',
            background:
              feedback.type === 'success' ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
            {feedback.type === 'success' ? (
              <Check size={18} style={{ color: 'var(--status-success)' }} aria-hidden="true" />
            ) : (
              <AlertTriangle
                size={18}
                style={{ color: 'var(--status-danger)' }}
                aria-hidden="true"
              />
            )}
            <span style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
              {feedback.message}
            </span>
          </div>
          <button
            type="button"
            className="holo-btn"
            onClick={() => setFeedback(null)}
            style={{ minHeight: '44px', padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
          >
            {isAr ? 'إغلاق' : 'Dismiss'}
          </button>
        </div>
      )}

      {/* القسم الأول: بطاقات السمات الخمس الأساسية والسمات المخصصة المحفوظة */}
      <div className="holo-panel" style={{ padding: '1.25rem' }}>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.5rem',
            marginBottom: '1rem',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Sparkles size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <span>
              {isAr
                ? 'مكتبة السمات الهولوغرامية (5 سمات أساسية + السمات المخصصة)'
                : 'Holographic Theme Gallery (5 Core Presets + Custom Themes)'}
            </span>
          </h3>
          <span className="holo-badge tabular-nums">
            {presets.length + customThemes.length} {isAr ? 'سمات متاحة' : 'Themes'}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1rem',
          }}
        >
          {presets.map((theme) => (
            <ThemePresetCard
              key={theme.id}
              theme={theme}
              isActive={activeState.activeThemeId === theme.id}
              isAr={isAr}
              onSelect={selectTheme}
            />
          ))}

          {customThemes.map((theme) => (
            <ThemePresetCard
              key={theme.id}
              theme={theme}
              isActive={activeState.activeThemeId === theme.id}
              isAr={isAr}
              onSelect={selectTheme}
              onDelete={deleteCustomTheme}
            />
          ))}
        </div>
      </div>

      {/* القسم الثاني: شبكة أدوات التخصيص الحي (الألوان + المنزلقات + الوصولية والأداء) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '1.25rem',
          alignItems: 'start',
        }}
      >
        {/* محرر رموز الألوان الحي + منزلقات المؤثرات الهولوغرامية */}
        <div className="holo-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.6rem',
            }}
          >
            <h3 style={{ margin: 0, fontSize: '1.02rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sliders size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <span>
                {isAr ? 'التخصيص الحي للألوان والمؤثرات' : 'Live Color & Optical Controls'}
              </span>
            </h3>

            <button
              type="button"
              className="holo-btn"
              onClick={resetOverrides}
              style={{ minHeight: '44px', fontSize: '0.82rem' }}
              aria-label={
                isAr
                  ? 'إعادة الضبط للسمة الأصلية'
                  : 'Reset Overrides to Original Theme'
              }
            >
              <RotateCcw size={15} aria-hidden="true" />
              <span>
                {isAr
                  ? 'إعادة الضبط للسمة الأصلية / Reset Overrides'
                  : 'Reset Overrides / إعادة الضبط'}
              </span>
            </button>
          </div>

          {hasOverrides && (
            <div style={{ fontSize: '0.79rem', color: 'var(--accent-primary)' }}>
              {isAr
                ? 'يوجد تخصيص لوني حي مطبق فوق السمة الحالية — يمكنك حفظه كسمة مخصصة بالأسفل.'
                : 'Live color token overrides are active — save them as a custom theme below.'}
            </div>
          )}

          {/* منتقيات الألوان الأربعة */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '0.75rem',
            }}
          >
            {COLOR_PICKER_FIELDS.map((field) => {
              const pickerValue = normalizePickerHex(
                effectiveTokens[field.key],
                fallbackThemeTokens[field.key]
              );
              const inputId = `theme-color-${field.key}`;

              return (
                <div
                  key={field.key}
                  className="holo-panel-subtle"
                  style={{
                    padding: '0.7rem 0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '0.65rem',
                  }}
                >
                  <div>
                    <label
                      htmlFor={inputId}
                      style={{
                        display: 'block',
                        fontWeight: 700,
                        fontSize: '0.84rem',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                      }}
                    >
                      {isAr ? field.labelAr : field.labelEn}
                    </label>
                    <div
                      className="tabular-nums"
                      style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}
                    >
                      {pickerValue.toUpperCase()}
                    </div>
                  </div>

                  <input
                    id={inputId}
                    type="color"
                    value={pickerValue}
                    onChange={(e) => updateTokenOverrides({ [field.key]: e.target.value })}
                    aria-label={isAr ? field.labelAr : field.labelEn}
                    title={isAr ? field.hintAr : field.hintEn}
                    style={{
                      width: '48px',
                      height: '44px',
                      padding: '2px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-holo)',
                      background: 'var(--bg-base)',
                      cursor: 'pointer',
                      flexShrink: 0,
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* منزلقات التحكم في شدة التوهج والضبابية والعتامة والحركة */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {SLIDER_CONTROLS.map((slider) => {
              const currentValue = activeState.modifiers[slider.key];
              const sliderId = `theme-slider-${slider.key}`;

              return (
                <div
                  key={slider.key}
                  className="holo-panel-subtle"
                  style={{ padding: '0.75rem 0.9rem' }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '0.5rem',
                      marginBottom: '0.35rem',
                    }}
                  >
                    <label
                      htmlFor={sliderId}
                      style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}
                    >
                      {isAr ? slider.labelAr : slider.labelEn}
                    </label>
                    <span className="holo-badge holo-badge-accent tabular-nums">
                      {currentValue}
                      {slider.unit}
                    </span>
                  </div>

                  <div
                    style={{
                      fontSize: '0.77rem',
                      color: 'var(--text-muted)',
                      marginBottom: '0.45rem',
                    }}
                  >
                    {isAr ? slider.descAr : slider.descEn}
                  </div>

                  <input
                    id={sliderId}
                    type="range"
                    min={slider.min}
                    max={slider.max}
                    step={1}
                    value={currentValue}
                    onChange={(e) =>
                      updateModifiers({ [slider.key]: Number(e.target.value) })
                    }
                    aria-label={isAr ? slider.labelAr : slider.labelEn}
                    style={{
                      width: '100%',
                      minHeight: '44px',
                      accentColor: 'var(--accent-primary)',
                      cursor: 'pointer',
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* العمود الثاني: الوصولية والأداء + حفظ سمة مخصصة */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* أوضاع الوصولية والأداء */}
          <div
            className="holo-panel"
            style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
          >
            <h3 style={{ margin: 0, fontSize: '1.02rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Eye size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <span>
                {isAr
                  ? 'أوضاع الوصولية وكفاءة الأداء (Accessibility & GPU Modes)'
                  : 'Accessibility & Performance Modes'}
              </span>
            </h3>

            <AccessibleToggleRow
              id="toggle-motion-disabled"
              checked={activeState.modifiers.motionDisabled}
              onChange={(next) => updateModifiers({ motionDisabled: next })}
              title={
                isAr
                  ? 'تعطيل المؤثرات الحركية (Disable Motion Effects)'
                  : 'Disable Motion Effects'
              }
              description={
                isAr
                  ? 'إيقاف النبضات والانتقالات الحركية فوراً مع احترام إعداد prefers-reduced-motion.'
                  : 'Stops all animations and transitions immediately (respects prefers-reduced-motion).'
              }
              badgeText={
                activeState.modifiers.motionDisabled
                  ? isAr
                    ? 'الحركة معطلة'
                    : 'Disabled'
                  : isAr
                    ? 'الحركة نشطة'
                    : 'Enabled'
              }
            />

            <AccessibleToggleRow
              id="toggle-high-contrast"
              checked={activeState.modifiers.highContrast}
              onChange={(next) => updateModifiers({ highContrast: next })}
              title={
                isAr
                  ? 'وضع التباين العالي للوصولية (High-Contrast Mode)'
                  : 'High-Contrast Accessibility Mode'
              }
              description={
                isAr
                  ? 'خلفية داكنة صلبة وحدود عالية الحدة ونصوص ناصعة البياض لأقصى درجات القراءة.'
                  : 'Pure solid dark surfaces, crisp high-visibility borders, and maximum text contrast.'
              }
              badgeText={
                activeState.modifiers.highContrast
                  ? isAr
                    ? 'مُفعّل'
                    : 'Active'
                  : isAr
                    ? 'قياسي'
                    : 'Off'
              }
            />

            <AccessibleToggleRow
              id="toggle-low-power"
              checked={activeState.modifiers.lowPowerMode}
              onChange={(next) => updateModifiers({ lowPowerMode: next })}
              title={
                isAr
                  ? 'وضع الطاقة المنخفضة وتخفيف GPU (Low-Power Rendering)'
                  : 'Low-Power Rendering Mode'
              }
              description={
                isAr
                  ? 'إلغاء الضبابية الزجاجية المكلفة على المعالج الرسومي والتوهج الكثيف أثناء الجلسات الطويلة.'
                  : 'Disables GPU-intensive backdrop blur and heavy glow effects for extended sessions.'
              }
              badgeText={
                activeState.modifiers.lowPowerMode
                  ? isAr
                    ? 'توفير نشط'
                    : 'Low-Power ON'
                  : isAr
                    ? 'أداء كامل'
                    : 'Full FX'
              }
            />

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              <Zap size={14} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <span>
                {isAr
                  ? 'تُحفظ جميع تفضيلات الوصولية والأداء تلقائياً وتُستعاد عند فتح التطبيق.'
                  : 'Accessibility and GPU preferences persist automatically across reloads.'}
              </span>
            </div>
          </div>

          {/* حفظ السمة المخصصة المستديمة */}
          <form
            onSubmit={handleSaveCustomTheme}
            className="holo-panel"
            style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
          >
            <h3 style={{ margin: 0, fontSize: '1.02rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Plus size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <span>
                {isAr
                  ? 'حفظ الإعداد الحالي كسمة مخصصة مستديمة'
                  : 'Save Current Configuration as Persistent Custom Theme'}
              </span>
            </h3>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '0.75rem',
              }}
            >
              <div>
                <label
                  htmlFor="custom-theme-name-ar"
                  style={{
                    display: 'block',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.3rem',
                  }}
                >
                  {isAr ? 'اسم السمة بالعربية' : 'Arabic Theme Name'}
                </label>
                <input
                  id="custom-theme-name-ar"
                  type="text"
                  className="holo-input"
                  value={customNameAr}
                  onChange={(e) => setCustomNameAr(e.target.value)}
                  placeholder="مثال: السيادة الذهبية الخاصة"
                  style={{ minHeight: '44px' }}
                />
              </div>

              <div>
                <label
                  htmlFor="custom-theme-name-en"
                  style={{
                    display: 'block',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    marginBottom: '0.3rem',
                  }}
                >
                  {isAr ? 'اسم السمة بالإنجليزية' : 'English Theme Name'}
                </label>
                <input
                  id="custom-theme-name-en"
                  type="text"
                  className="holo-input"
                  value={customNameEn}
                  onChange={(e) => setCustomNameEn(e.target.value)}
                  placeholder="e.g., Sovereign Bullion Pro"
                  style={{ minHeight: '44px' }}
                />
              </div>
            </div>

            <button
              type="submit"
              className="holo-btn holo-btn-primary"
              disabled={isSavingCustom}
              style={{ minHeight: '44px' }}
            >
              <Sparkles size={16} aria-hidden="true" />
              <span>
                {isSavingCustom
                  ? isAr
                    ? 'جاري الحفظ...'
                    : 'Saving...'
                  : isAr
                    ? 'حفظ كسمة مخصصة مستديمة / Save Custom Theme'
                    : 'Save Custom Theme / حفظ كسمة مخصصة مستديمة'}
              </span>
            </button>
          </form>
        </div>
      </div>

      {/* القسم الثالث: تصدير واستيراد ملفات إعداد السمة بصيغة JSON */}
      <div
        className="holo-panel"
        style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}
      >
        <h3 style={{ margin: 0, fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileJson size={19} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
          <span>
            {isAr
              ? 'تصدير واستيراد حزم السمات الهولوغرامية (JSON Configuration)'
              : 'Export & Import Theme Configuration (JSON)'}
          </span>
        </h3>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.15rem',
          }}
        >
          {/* بطاقة التصدير */}
          <div
            className="holo-panel-subtle"
            style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
          >
            <div style={{ fontWeight: 700, fontSize: '0.92rem' }}>
              {isAr ? 'تصدير السمة النشطة (Export JSON)' : 'Export Active Theme (JSON)'}
            </div>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {isAr
                ? 'تنزيل ملف .json يحتوي على كافة رموز الألوان ومعاملات التوهج والضبابية الحالية أو نسخها مباشرة.'
                : 'Download a .json bundle with all active color tokens and optical modifiers, or copy directly.'}
            </p>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              <button
                type="button"
                className="holo-btn holo-btn-primary"
                onClick={handleExportJson}
                style={{ minHeight: '44px', flex: 1 }}
              >
                <Download size={16} aria-hidden="true" />
                <span>
                  {isAr
                    ? 'تصدير ملف السمة (JSON) / Export JSON'
                    : 'Export JSON / تصدير ملف السمة'}
                </span>
              </button>

              <button
                type="button"
                className="holo-btn"
                onClick={handleCopyExportedJson}
                style={{ minHeight: '44px' }}
                aria-label={isAr ? 'نسخ كود JSON للسمة' : 'Copy theme JSON to clipboard'}
              >
                {copiedExport ? (
                  <Check size={15} style={{ color: 'var(--status-success)' }} aria-hidden="true" />
                ) : (
                  <Copy size={15} aria-hidden="true" />
                )}
                <span>{copiedExport ? (isAr ? 'تم النسخ!' : 'Copied!') : isAr ? 'نسخ JSON' : 'Copy JSON'}</span>
              </button>
            </div>

            <textarea
              readOnly
              className="holo-input tabular-nums"
              rows={6}
              value={liveExportJson}
              aria-label={isAr ? 'معاينة JSON المُصدَّر للسمة' : 'Exported theme JSON preview'}
              style={{
                resize: 'vertical',
                fontSize: '0.76rem',
                lineHeight: 1.45,
              }}
            />
          </div>

          {/* بطاقة الاستيراد عبر رفع ملف أو لصق JSON */}
          <div
            className="holo-panel-subtle"
            style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
          >
            <div style={{ fontWeight: 700, fontSize: '0.92rem' }}>
              {isAr ? 'استيراد ملف سمة (Import JSON)' : 'Import Theme Configuration (JSON)'}
            </div>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {isAr
                ? 'ارفع ملف إعداد .json أو الصق البنية أدناه ليتم التحقق من رموز الألوان وتفعيلها فوراً.'
                : 'Upload a .json theme file or paste JSON below for schema validation and instant activation.'}
            </p>

            {/* مدخل الملفات المخفي والمرتبط بزر قياسي */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              aria-label={isAr ? 'رفع ملف سمة بصيغة JSON' : 'Upload JSON theme file'}
            />

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              <button
                type="button"
                className="holo-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isImporting}
                style={{ minHeight: '44px', flex: 1 }}
              >
                <Upload size={16} aria-hidden="true" />
                <span>{isAr ? 'رفع ملف .json من الجهاز' : 'Upload .json File'}</span>
              </button>

              <button
                type="button"
                className="holo-btn holo-btn-primary"
                onClick={() => executeImportJson(importJsonInput)}
                disabled={isImporting || !importJsonInput.trim()}
                style={{ minHeight: '44px', flex: 1 }}
              >
                <FileJson size={16} aria-hidden="true" />
                <span>
                  {isImporting
                    ? isAr
                      ? 'جاري الاستيراد...'
                      : 'Importing...'
                    : isAr
                      ? 'استيراد ملف سمة (JSON) / Import JSON'
                      : 'Import JSON / استيراد ملف سمة'}
                </span>
              </button>
            </div>

            <textarea
              className="holo-input tabular-nums"
              rows={6}
              value={importJsonInput}
              onChange={(e) => setImportJsonInput(e.target.value)}
              placeholder={
                isAr
                  ? 'الصق محتوى ملف السمة JSON هنا للتحقق والاستيراد الفوري...'
                  : 'Paste theme JSON payload here to validate and import...'
              }
              aria-label={isAr ? 'حقل لصق JSON لاستيراد السمة' : 'Paste theme JSON input'}
              style={{
                resize: 'vertical',
                fontSize: '0.76rem',
                lineHeight: 1.45,
              }}
            />
          </div>
        </div>
      </div>
    </section>
  );
};

export default ThemeStudio;
