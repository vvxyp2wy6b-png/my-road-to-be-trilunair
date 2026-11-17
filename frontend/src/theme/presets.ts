/**
 * السمات الهولوغرامية الخمس الأساسية ومعاملات التخصيص القياسية
 * My Road to be Trilunair Dr.MaJoOoOoOoD
 *
 * تشمل:
 * 1. Royal Gold (الملكي الذهبي)
 * 2. Quantum Cyan (السيان الكمي)
 * 3. Nebula Purple (سديم الأرجوان)
 * 4. Emerald Matrix (المصفوفة الزمردية)
 * 5. Arctic Platinum (البلاتين القطبي)
 */

import type { ActiveThemeState, ThemeDefinition, ThemeModifiers, ThemeTokens } from '../types/trilunair';

export const DEFAULT_MODIFIERS: ThemeModifiers = {
  glowIntensity: 58,
  blurRadius: 16,
  panelOpacity: 78,
  animationIntensity: 85,
  motionDisabled: false,
  highContrast: false,
  lowPowerMode: false,
};

export const INITIAL_PRESET_THEMES: ThemeDefinition[] = [
  {
    id: 'royal-gold',
    nameAr: 'الملكي الذهبي (Royal Gold)',
    nameEn: 'Royal Gold',
    descriptionAr: 'فخامة سيادية بلمسات الذهب الملكي والسبائك الداكنة لرحلة التريليون.',
    descriptionEn: 'Sovereign luxury with luminous bullion gold over obsidian glass.',
    tokens: {
      bgBase: '#07080d',
      bgElevated: '#0e111a',
      bgSurface: '#151a28',
      accentPrimary: '#f5c451',
      accentSecondary: '#ffe08a',
      accentTertiary: '#38bdf8',
      textPrimary: '#f8fafc',
      textSecondary: '#cbd5e1',
      textMuted: '#94a3b8',
      borderHolo: 'rgba(245, 196, 81, 0.36)',
      success: '#10b981',
      danger: '#f43f5e',
      warning: '#f59e0b',
    },
  },
  {
    id: 'quantum-cyan',
    nameAr: 'السيان الكمي (Quantum Cyan)',
    nameEn: 'Quantum Cyan',
    descriptionAr: 'مركز قيادة كمي فائق الوضوح بإضاءة السيان الليزرية والياقوت الأزرق.',
    descriptionEn: 'High-precision quantum command aesthetics with laser cyan optics.',
    tokens: {
      bgBase: '#040911',
      bgElevated: '#081221',
      bgSurface: '#0d1d33',
      accentPrimary: '#06e8f9',
      accentSecondary: '#67e8f9',
      accentTertiary: '#818cf8',
      textPrimary: '#f0f9ff',
      textSecondary: '#bae6fd',
      textMuted: '#7dd3fc',
      borderHolo: 'rgba(6, 232, 249, 0.36)',
      success: '#10b981',
      danger: '#fb7185',
      warning: '#fbbf24',
    },
  },
  {
    id: 'nebula-purple',
    nameAr: 'سديم الأرجوان (Nebula Purple)',
    nameEn: 'Nebula Purple',
    descriptionAr: 'عمق فضائي متعدد الطبقات بطيف الأرجوان النجمي والوردي الكهرومغناطيسي.',
    descriptionEn: 'Deep-space holographic layers with stellar violet and magenta luminescence.',
    tokens: {
      bgBase: '#090514',
      bgElevated: '#120a24',
      bgSurface: '#1c1136',
      accentPrimary: '#c084fc',
      accentSecondary: '#f472b6',
      accentTertiary: '#22d3ee',
      textPrimary: '#faf5ff',
      textSecondary: '#e9d5ff',
      textMuted: '#c4b5fd',
      borderHolo: 'rgba(192, 132, 252, 0.38)',
      success: '#34d399',
      danger: '#fb7185',
      warning: '#facc15',
    },
  },
  {
    id: 'emerald-matrix',
    nameAr: 'المصفوفة الزمردية (Emerald Matrix)',
    nameEn: 'Emerald Matrix',
    descriptionAr: 'طابع خوارزمي كمي بدرجات الزمرد المشع لقراءة دفاتر الأوامر بسرعة قصوى.',
    descriptionEn: 'Algorithmic emerald phosphor matrix engineered for rapid orderbook reading.',
    tokens: {
      bgBase: '#030b08',
      bgElevated: '#071610',
      bgSurface: '#0c231a',
      accentPrimary: '#10f59c',
      accentSecondary: '#6ee7b7',
      accentTertiary: '#38bdf8',
      textPrimary: '#ecfdf5',
      textSecondary: '#a7f3d0',
      textMuted: '#6ee7b7',
      borderHolo: 'rgba(16, 245, 156, 0.34)',
      success: '#22c55e',
      danger: '#f43f5e',
      warning: '#eab308',
    },
  },
  {
    id: 'arctic-platinum',
    nameAr: 'البلاتين القطبي (Arctic Platinum)',
    nameEn: 'Arctic Platinum',
    descriptionAr: 'نقائض بلاتينية جليدية مع لمسات الكوبالت البارد وتباين مؤسسي ناصع.',
    descriptionEn: 'Crisp institutional platinum and glacial cobalt with ultra-clean legibility.',
    tokens: {
      bgBase: '#0b1017',
      bgElevated: '#131b26',
      bgSurface: '#1c2736',
      accentPrimary: '#e2e8f0',
      accentSecondary: '#38bdf8',
      accentTertiary: '#94a3b8',
      textPrimary: '#ffffff',
      textSecondary: '#dbeafe',
      textMuted: '#94a3b8',
      borderHolo: 'rgba(226, 232, 240, 0.38)',
      success: '#10b981',
      danger: '#ef4444',
      warning: '#f59e0b',
    },
  },
  {
    id: 'obsidian-black',
    nameAr: 'الأوبسيديان الأسود (Obsidian Black)',
    nameEn: 'Obsidian Black',
    descriptionAr: 'سواد نقي مطلق بلمسات دقيقة من الذهب الخالص والبلاتين لأقصى درجات التركيز.',
    descriptionEn: 'Pure obsidian black with minimal refined gold and platinum accents.',
    tokens: {
      bgBase: '#000000',
      bgElevated: '#060608',
      bgSurface: '#0c0d10',
      accentPrimary: '#d4af37',
      accentSecondary: '#e2e8f0',
      accentTertiary: '#94a3b8',
      textPrimary: '#f8fafc',
      textSecondary: '#cbd5e1',
      textMuted: '#94a3b8',
      borderHolo: 'rgba(212, 175, 55, 0.32)',
      success: '#10b981',
      danger: '#f43f5e',
      warning: '#f59e0b',
    },
  },
];

export const DEFAULT_ACTIVE_THEME_STATE: ActiveThemeState = {
  activeThemeId: 'royal-gold',
  customOverrides: {},
  modifiers: DEFAULT_MODIFIERS,
};

export function hexToRgbTriplet(hex: string, fallback = '245, 196, 81'): string {
  const cleaned = hex.trim().replace('#', '');
  if (!/^[0-9a-fA-F]{6}$/.test(cleaned)) {
    return fallback;
  }
  const r = parseInt(cleaned.slice(0, 2), 16);
  const g = parseInt(cleaned.slice(2, 4), 16);
  const b = parseInt(cleaned.slice(4, 6), 16);
  return `${r}, ${g}, ${b}`;
}

export function applyThemeToDom(
  baseTokens: ThemeTokens,
  overrides: Partial<ThemeTokens>,
  modifiers: ThemeModifiers,
  themeId: string
): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  const merged: ThemeTokens = { ...baseTokens, ...overrides };

  root.setAttribute('data-theme', themeId);
  root.setAttribute('data-high-contrast', modifiers.highContrast ? 'true' : 'false');
  root.setAttribute('data-low-power', modifiers.lowPowerMode ? 'true' : 'false');
  root.setAttribute(
    'data-motion',
    modifiers.motionDisabled || modifiers.animationIntensity === 0 ? 'disabled' : 'enabled'
  );

  root.style.setProperty('--bg-base', merged.bgBase);
  root.style.setProperty('--bg-elevated', merged.bgElevated);
  root.style.setProperty('--bg-surface', merged.bgSurface);
  root.style.setProperty('--bg-surface-rgb', hexToRgbTriplet(merged.bgSurface, '21, 26, 40'));

  root.style.setProperty('--accent-primary', merged.accentPrimary);
  root.style.setProperty(
    '--accent-primary-rgb',
    hexToRgbTriplet(merged.accentPrimary, '245, 196, 81')
  );
  root.style.setProperty('--accent-secondary', merged.accentSecondary);
  root.style.setProperty('--accent-tertiary', merged.accentTertiary);

  root.style.setProperty('--text-primary', merged.textPrimary);
  root.style.setProperty('--text-secondary', merged.textSecondary);
  root.style.setProperty('--text-muted', merged.textMuted);
  root.style.setProperty(
    '--border-holo',
    overrides.accentPrimary
      ? `rgba(${hexToRgbTriplet(merged.accentPrimary)}, 0.4)`
      : merged.borderHolo
  );

  root.style.setProperty('--status-success', merged.success);
  root.style.setProperty('--status-danger', merged.danger);
  root.style.setProperty('--status-warning', merged.warning);

  root.style.setProperty(
    '--fx-glow-intensity',
    (Math.max(0, Math.min(100, modifiers.glowIntensity)) / 100).toFixed(2)
  );
  root.style.setProperty(
    '--fx-blur-radius',
    `${Math.max(0, Math.min(32, modifiers.blurRadius))}px`
  );
  root.style.setProperty(
    '--fx-panel-opacity',
    (Math.max(40, Math.min(98, modifiers.panelOpacity)) / 100).toFixed(2)
  );
  root.style.setProperty(
    '--fx-motion-scale',
    modifiers.motionDisabled
      ? '0'
      : (Math.max(0, Math.min(100, modifiers.animationIntensity)) / 100).toFixed(2)
  );
}
