/**
 * مزود السياق الديناميكي للسمات (Theme Engine Provider)
 * يدعم الاستدامة المزدوجة في LocalStorage وقاعدة بيانات الخادم (SQLite)،
 * والتصدير والاستيراد بصيغة JSON، وتفضيلات تقليل الحركة والتباين العالي والطاقة المنخفضة.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { trilunairApi } from '../api/client';
import type {
  ActiveThemeState,
  Language,
  ThemeDefinition,
  ThemeModifiers,
  ThemeTokens,
} from '../types/trilunair';
import {
  DEFAULT_ACTIVE_THEME_STATE,
  DEFAULT_MODIFIERS,
  INITIAL_PRESET_THEMES,
  applyThemeToDom,
} from './presets';

const STORAGE_ACTIVE_KEY = 'trilunair.activeThemeState.v1';
const STORAGE_CUSTOM_KEY = 'trilunair.customThemes.v1';
const STORAGE_LANG_KEY = 'trilunair.language.v1';

interface ThemeContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  presets: ThemeDefinition[];
  customThemes: ThemeDefinition[];
  allThemes: ThemeDefinition[];
  activeState: ActiveThemeState;
  currentTheme: ThemeDefinition;
  effectiveTokens: ThemeTokens;
  selectTheme: (themeId: string) => void;
  updateTokenOverrides: (overrides: Partial<ThemeTokens>) => void;
  resetOverrides: () => void;
  updateModifiers: (patch: Partial<ThemeModifiers>) => void;
  saveAsCustomTheme: (nameAr: string, nameEn: string) => Promise<ThemeDefinition>;
  deleteCustomTheme: (themeId: string) => Promise<void>;
  exportCurrentThemeJson: () => string;
  importThemeFromJson: (rawJson: string) => Promise<ThemeDefinition>;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function loadStoredJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() =>
    loadStoredJson<Language>(STORAGE_LANG_KEY, 'ar')
  );

  const [presets, setPresets] = useState<ThemeDefinition[]>(INITIAL_PRESET_THEMES);
  const [customThemes, setCustomThemes] = useState<ThemeDefinition[]>(() =>
    loadStoredJson<ThemeDefinition[]>(STORAGE_CUSTOM_KEY, [])
  );

  const [activeState, setActiveState] = useState<ActiveThemeState>(() => {
    const stored = loadStoredJson<ActiveThemeState | null>(STORAGE_ACTIVE_KEY, null);
    if (stored && stored.activeThemeId && stored.modifiers) {
      return {
        activeThemeId: stored.activeThemeId,
        customOverrides: stored.customOverrides || {},
        modifiers: { ...DEFAULT_MODIFIERS, ...stored.modifiers },
      };
    }
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return {
      ...DEFAULT_ACTIVE_THEME_STATE,
      modifiers: {
        ...DEFAULT_MODIFIERS,
        motionDisabled: prefersReducedMotion,
      },
    };
  });

  const allThemes = useMemo(() => [...presets, ...customThemes], [presets, customThemes]);

  const currentTheme = useMemo(
    () => allThemes.find((item) => item.id === activeState.activeThemeId) || presets[0],
    [allThemes, activeState.activeThemeId, presets]
  );

  const effectiveTokens = useMemo<ThemeTokens>(
    () => ({ ...currentTheme.tokens, ...activeState.customOverrides }),
    [currentTheme, activeState.customOverrides]
  );

  // مزامنة اتجاه الصفحة واللغة (RTL للعربية / LTR للإنجليزية)
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    try {
      window.localStorage.setItem(STORAGE_LANG_KEY, JSON.stringify(language));
    } catch {
      // تجاهل قيود التخزين المحلي
    }
  }, [language]);

  // تطبيق متغيرات CSS على جذر المستند فور أي تغيير
  useEffect(() => {
    applyThemeToDom(
      currentTheme.tokens,
      activeState.customOverrides,
      activeState.modifiers,
      currentTheme.id
    );
    try {
      window.localStorage.setItem(STORAGE_ACTIVE_KEY, JSON.stringify(activeState));
    } catch {
      // تجاهل قيود التخزين
    }
  }, [currentTheme, activeState]);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_CUSTOM_KEY, JSON.stringify(customThemes));
    } catch {
      // تجاهل قيود التخزين
    }
  }, [customThemes]);

  // جلب السمات المحفوظة من الخادم عند التشغيل الأول (فقط إذا لم يسبق تخزين حالة محلية)
  useEffect(() => {
    let cancelled = false;
    const hadLocalActive = Boolean(
      typeof window !== 'undefined' && window.localStorage.getItem(STORAGE_ACTIVE_KEY)
    );
    trilunairApi
      .getThemes()
      .then((payload) => {
        if (cancelled) return;
        if (payload.presets?.length) {
          setPresets(payload.presets);
        }
        if (payload.customThemes?.length) {
          setCustomThemes((prev) => {
            const map = new Map<string, ThemeDefinition>();
            prev.forEach((tItem) => map.set(tItem.id, tItem));
            payload.customThemes.forEach((tItem) => map.set(tItem.id, tItem));
            return Array.from(map.values());
          });
        }
        if (!hadLocalActive && payload.activeState?.activeThemeId) {
          setActiveState({
            activeThemeId: payload.activeState.activeThemeId,
            customOverrides: payload.activeState.customOverrides || {},
            modifiers: { ...DEFAULT_MODIFIERS, ...payload.activeState.modifiers },
          });
        }
      })
      .catch(() => {
        // العمل بسلاسة عبر التخزين المحلي في حال عدم اتصال الخادم مؤقتاً
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const persistActiveToBackend = useCallback((nextState: ActiveThemeState) => {
    trilunairApi.saveActiveThemeState(nextState).catch(() => {
      // محفوظ محلياً بالفعل
    });
  }, []);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
  }, []);

  const selectTheme = useCallback(
    (themeId: string) => {
      setActiveState((prev) => {
        const next: ActiveThemeState = {
          ...prev,
          activeThemeId: themeId,
          customOverrides: {},
        };
        persistActiveToBackend(next);
        return next;
      });
    },
    [persistActiveToBackend]
  );

  const updateTokenOverrides = useCallback(
    (overrides: Partial<ThemeTokens>) => {
      setActiveState((prev) => {
        const next: ActiveThemeState = {
          ...prev,
          customOverrides: { ...prev.customOverrides, ...overrides },
        };
        persistActiveToBackend(next);
        return next;
      });
    },
    [persistActiveToBackend]
  );

  const resetOverrides = useCallback(() => {
    setActiveState((prev) => {
      const next: ActiveThemeState = {
        ...prev,
        customOverrides: {},
        modifiers: DEFAULT_MODIFIERS,
      };
      persistActiveToBackend(next);
      return next;
    });
  }, [persistActiveToBackend]);

  const updateModifiers = useCallback(
    (patch: Partial<ThemeModifiers>) => {
      setActiveState((prev) => {
        const next: ActiveThemeState = {
          ...prev,
          modifiers: { ...prev.modifiers, ...patch },
        };
        persistActiveToBackend(next);
        return next;
      });
    },
    [persistActiveToBackend]
  );

  const saveAsCustomTheme = useCallback(
    async (nameAr: string, nameEn: string): Promise<ThemeDefinition> => {
      const slug = `custom-${Date.now().toString(36)}`;
      const newTheme: ThemeDefinition = {
        id: slug,
        nameAr: nameAr.trim() || 'سمة مخصصة',
        nameEn: nameEn.trim() || 'Custom Hologram',
        descriptionAr: 'سمة هولوغرامية مخصصة محفوظة بواسطة المسؤول.',
        descriptionEn: 'Administrator-configured custom holographic theme.',
        isCustom: true,
        tokens: { ...effectiveTokens },
        defaultModifiers: { ...activeState.modifiers },
      };

      setCustomThemes((prev) => [...prev, newTheme]);
      const nextActive: ActiveThemeState = {
        activeThemeId: newTheme.id,
        customOverrides: {},
        modifiers: activeState.modifiers,
      };
      setActiveState(nextActive);

      try {
        await trilunairApi.saveCustomTheme(newTheme);
        await trilunairApi.saveActiveThemeState(nextActive);
      } catch {
        // محفوظ محلياً بالفعل في LocalStorage
      }
      return newTheme;
    },
    [effectiveTokens, activeState.modifiers]
  );

  const deleteCustomTheme = useCallback(
    async (themeId: string) => {
      setCustomThemes((prev) => prev.filter((item) => item.id !== themeId));
      if (activeState.activeThemeId === themeId) {
        selectTheme('royal-gold');
      }
      try {
        await trilunairApi.deleteCustomTheme(themeId);
      } catch {
        // تم الحذف محلياً
      }
    },
    [activeState.activeThemeId, selectTheme]
  );

  const exportCurrentThemeJson = useCallback((): string => {
    const bundle = {
      schemaVersion: '1.0',
      exportedAt: new Date().toISOString(),
      app: 'My Road to be Trilunair Dr.MaJoOoOoOoD',
      theme: {
        id: currentTheme.isCustom ? currentTheme.id : `custom-export-${Date.now().toString(36)}`,
        nameAr: `${currentTheme.nameAr} (مُصدَّرة)`,
        nameEn: `${currentTheme.nameEn} (Exported)`,
        descriptionAr: currentTheme.descriptionAr,
        descriptionEn: currentTheme.descriptionEn,
        isCustom: true,
        tokens: effectiveTokens,
        defaultModifiers: activeState.modifiers,
      },
      modifiers: activeState.modifiers,
    };
    return JSON.stringify(bundle, null, 2);
  }, [currentTheme, effectiveTokens, activeState.modifiers]);

  const importThemeFromJson = useCallback(
    async (rawJson: string): Promise<ThemeDefinition> => {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(rawJson) as Record<string, unknown>;
      } catch {
        throw new Error('ملف JSON غير صالح — Invalid JSON syntax');
      }

      const candidate = (parsed.theme || parsed) as Partial<ThemeDefinition>;
      if (!candidate || typeof candidate !== 'object' || !candidate.tokens) {
        throw new Error('بنية ملف السمة غير مكتملة (tokens مفقودة) — Missing theme tokens');
      }

      const requiredKeys: (keyof ThemeTokens)[] = [
        'bgBase',
        'bgSurface',
        'accentPrimary',
        'textPrimary',
      ];
      for (const key of requiredKeys) {
        if (typeof candidate.tokens[key] !== 'string' || !candidate.tokens[key]) {
          throw new Error(`الحقل اللوني المطلوب مفقود: ${key}`);
        }
      }

      const fallbackTokens = INITIAL_PRESET_THEMES[0].tokens;
      const importedTheme: ThemeDefinition = {
        id:
          typeof candidate.id === 'string' && candidate.id.startsWith('custom-')
            ? `${candidate.id}-${Date.now().toString(36).slice(-3)}`
            : `custom-import-${Date.now().toString(36)}`,
        nameAr: candidate.nameAr || 'سمة مستوردة',
        nameEn: candidate.nameEn || 'Imported Theme',
        descriptionAr: candidate.descriptionAr || 'سمة مستوردة عبر ملف إعداد JSON.',
        descriptionEn: candidate.descriptionEn || 'Imported via JSON configuration.',
        isCustom: true,
        tokens: { ...fallbackTokens, ...candidate.tokens },
        defaultModifiers: {
          ...DEFAULT_MODIFIERS,
          ...(candidate.defaultModifiers || (parsed.modifiers as Partial<ThemeModifiers>) || {}),
        },
      };

      setCustomThemes((prev) => [...prev, importedTheme]);
      const nextModifiers = {
        ...activeState.modifiers,
        ...(importedTheme.defaultModifiers || {}),
      };
      const nextState: ActiveThemeState = {
        activeThemeId: importedTheme.id,
        customOverrides: {},
        modifiers: nextModifiers,
      };
      setActiveState(nextState);

      try {
        await trilunairApi.importThemeConfig(importedTheme);
        await trilunairApi.saveActiveThemeState(nextState);
      } catch {
        // محفوظ محلياً بالفعل
      }

      return importedTheme;
    },
    [activeState.modifiers]
  );

  const value = useMemo<ThemeContextValue>(
    () => ({
      language,
      setLanguage,
      presets,
      customThemes,
      allThemes,
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
    }),
    [
      language,
      setLanguage,
      presets,
      customThemes,
      allThemes,
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
    ]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used inside ThemeProvider');
  }
  return ctx;
}
