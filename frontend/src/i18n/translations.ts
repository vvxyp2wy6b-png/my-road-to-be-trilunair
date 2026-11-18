/**
 * قاموس الترجمة المزدوج (العربية RTL والإنجليزية LTR) وأدوات تنسيق الأرقام المالية
 * My Road to be Trilunair Dr.MaJoOoOoOoD
 */

import type { Language } from '../types/trilunair';

export function formatCurrency(value: number, compact = false): string {
  if (!Number.isFinite(value)) return '$0.00';
  if (compact && Math.abs(value) >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(2)}B`;
  }
  if (compact && Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`;
  }
  const decimals = Math.abs(value) >= 100 ? 2 : Math.abs(value) >= 1 ? 2 : 4;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatNumber(value: number, decimals = 2): string {
  if (!Number.isFinite(value)) return '0';
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatSignedPct(value: number): string {
  if (!Number.isFinite(value)) return '0.00%';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export const UI_TEXT = {
  ar: {
    brandTitle: 'تريلماجد — طريقي إلى التريليون • د. ماجد',
    brandSubtitle: 'TMJ (TrilMajed) • رحلة د. ماجد السيادية نحو التريليون عبر الذكاء الكمي المنضبط وإدارة الثروة',
    navTerminal: 'قاعة التداول الحية',
    navPortfolio: 'المحفظة ومسار التريليون',
    navGovernance: 'بوابة التصاريح والأمان',
    navThemes: 'استوديو السمات الهولوغرامية',
    paperModeBadge: 'تداول ورقي آمن (PAPER)',
    liveModeBadge: 'تداول حقيقي مفعل (LIVE)',
    killSwitchActive: 'مفتاح الطوارئ مفعل — التنفيذ مجمد',
    streamConnected: 'بث مباشر متصل',
    streamOffline: 'وضع المزامنة الدورية',
    lowPowerBadge: 'وضع الطاقة المنخفضة',
    highContrastBadge: 'تباين عالي للوصولية',
    equityLabel: 'إجمالي حقوق الملكية',
    dailyPnlLabel: 'ربح / خسارة اليوم',
    cashLabel: 'السيولة النقدية المتاحة',
    varLabel: 'القيمة المعرضة للمخاطر (VaR 95%)',
    trilunairGoal: 'التقدم نحو هدف $1,000,000,000,000',
    langToggle: 'English (LTR)',
    quickThemeLabel: 'السمة النشطة',
  },
  en: {
    brandTitle: 'TMJ • TrilMajed — My Road to be Trilunair (Dr. Majed)',
    brandSubtitle: 'TrilMajed Sovereign Wealth & Disciplined Quantum Intelligence Center',
    navTerminal: 'Live Terminal',
    navPortfolio: 'Portfolio & $1T Roadmap',
    navGovernance: 'Authorization & Safety',
    navThemes: 'Holographic Theme Studio',
    paperModeBadge: 'PAPER TRADING (DEFAULT SAFE)',
    liveModeBadge: 'LIVE TRADING AUTHORIZED',
    killSwitchActive: 'KILL SWITCH ACTIVE — FROZEN',
    streamConnected: 'Live Feed Active',
    streamOffline: 'Polling Fallback',
    lowPowerBadge: 'Low-Power Mode',
    highContrastBadge: 'High Contrast',
    equityLabel: 'Total Equity',
    dailyPnlLabel: '24h P&L',
    cashLabel: 'Available Cash',
    varLabel: 'Daily VaR (95%)',
    trilunairGoal: 'Progress to $1 Trillion Target',
    langToggle: 'العربية (RTL)',
    quickThemeLabel: 'Active Theme',
  },
} as const;

export function t(lang: Language, key: keyof typeof UI_TEXT['ar']): string {
  return UI_TEXT[lang][key];
}
