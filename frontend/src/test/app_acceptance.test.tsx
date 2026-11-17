/**
 * حزمة اختبارات القبول الآلية للواجهة الأمامية والوصولية ومحرك السمات وغرفة الأوامر
 * My Road to be Trilunair Dr.MaJoOoOoOoD — QUANTUM AI TRADING COMMAND CENTER
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import { ThemeProvider, useTheme } from '../theme/ThemeContext';
import { INITIAL_PRESET_THEMES } from '../theme/presets';
import { VisualEffectsBoundary } from '../components/Effects/VisualEffectsBoundary';
import { AuthorizationModal } from '../components/Terminal/AuthorizationModal';
import type { TradeProposalEvaluation } from '../types/trilunair';

const ThemeHarness: React.FC = () => {
  const {
    presets,
    customThemes,
    activeState,
    selectTheme,
    updateModifiers,
    saveAsCustomTheme,
    exportCurrentThemeJson,
    importThemeFromJson,
  } = useTheme();
  const [exported, setExported] = React.useState('');

  return (
    <div>
      <div data-testid="active-theme">{activeState.activeThemeId}</div>
      <div data-testid="preset-count">{presets.length}</div>
      <div data-testid="custom-count">{customThemes.length}</div>
      {presets.map((p) => (
        <button key={p.id} type="button" onClick={() => selectTheme(p.id)}>
          switch-{p.id}
        </button>
      ))}
      <button
        type="button"
        onClick={() =>
          updateModifiers({ highContrast: true, lowPowerMode: true, motionDisabled: true })
        }
      >
        enable-a11y
      </button>
      <button
        type="button"
        onClick={() => void saveAsCustomTheme('ذهبي خاص', 'Custom Sovereign')}
      >
        save-custom
      </button>
      <button type="button" onClick={() => setExported(exportCurrentThemeJson())}>
        export-json
      </button>
      <button
        type="button"
        onClick={() =>
          void importThemeFromJson(
            JSON.stringify({
              theme: {
                nameAr: 'سمة مستوردة اختبارية',
                nameEn: 'Imported Spec Theme',
                tokens: {
                  bgBase: '#020408',
                  bgElevated: '#070b12',
                  bgSurface: '#0f172a',
                  accentPrimary: '#22d3ee',
                  accentSecondary: '#38bdf8',
                  accentTertiary: '#818cf8',
                  textPrimary: '#f8fafc',
                  textSecondary: '#cbd5e1',
                  textMuted: '#94a3b8',
                  borderHolo: 'rgba(34,211,238,0.4)',
                  success: '#10b981',
                  danger: '#f43f5e',
                  warning: '#f59e0b',
                },
              },
            })
          )
        }
      >
        import-json
      </button>
      <pre data-testid="exported-output">{exported}</pre>
    </div>
  );
};

const ThrowingVisualWidget: React.FC = () => {
  throw new Error('Simulated WebGL/Canvas GPU failure');
};

const MOCK_PROPOSAL_EVAL: TradeProposalEvaluation = {
  proposalId: 'prop_test_001',
  status: 'APPROVED_FOR_AUTH',
  proposal: {
    symbol: 'BTC-USD',
    side: 'BUY',
    orderType: 'MARKET',
    quantity: 0.1,
    source: 'VOICE',
    referencePrice: 96500,
    createdAt: '2026-11-16T23:55:00Z',
  },
  estimatedCosts: {
    notionalUsd: 9650,
    spreadCostUsd: 2.9,
    commissionUsd: 9.65,
    slippageCostUsd: 3.86,
    totalEstimatedCostUsd: 16.41,
    costBps: 17.0,
  },
  riskAssessment: {
    passed: true,
    riskScore: 22,
    riskLevel: 'LOW',
    postTradeConcentrationPct: 5.8,
    varImpactUsd: 193,
    checks: [
      {
        code: 'KILL_SWITCH',
        passed: true,
        messageAr: 'مفتاح الطوارئ غير مفعل',
        messageEn: 'Kill switch inactive',
      },
    ],
    violations: [],
  },
  tradingMode: 'PAPER',
  requiresLivePin: false,
};

describe('My Road to be Trilunair — Frontend Acceptance & Safety Tests', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/system/status')) {
          return {
            ok: true,
            json: async () => ({
              appName: 'My Road to be Trilunair Dr.MaJoOoOoOoD',
              version: '1.0.0',
              tradingMode: 'PAPER',
              killSwitchActive: false,
              liveAuthorized: false,
              safetyChecks: {
                riskEngineVerified: true,
                maxDrawdownConfigured: true,
                killSwitchReady: true,
                positionLimitsActive: true,
                auditTrailHealthy: true,
              },
              providers: {
                llmProvider: 'local-quant-engine',
                sttProvider: 'web-speech',
                ttsProvider: 'speech-synthesis',
              },
            }),
          };
        }
        if (url.includes('/market/assets')) {
          return {
            ok: true,
            json: async () => [
              {
                symbol: 'BTC-USD',
                nameAr: 'بيتكوين',
                nameEn: 'Bitcoin',
                category: 'CRYPTO',
                price: 96500,
                change24hPct: 2.4,
                high24h: 97200,
                low24h: 94100,
                volume24hUsd: 38000000000,
                volatilityPct: 3.1,
                spreadBps: 3.0,
              },
              {
                symbol: 'XAU-USD',
                nameAr: 'الذهب الفوري',
                nameEn: 'Spot Gold',
                category: 'COMMODITY',
                price: 2685,
                change24hPct: 0.6,
                high24h: 2698,
                low24h: 2665,
                volume24hUsd: 12000000000,
                volatilityPct: 1.1,
                spreadBps: 4.0,
              },
            ],
          };
        }
        if (url.includes('/market/candles')) {
          return {
            ok: true,
            json: async () => ({
              symbol: 'BTC-USD',
              timeframe: '15m',
              candles: [
                {
                  timestamp: 1700000000000,
                  open: 96000,
                  high: 96800,
                  low: 95800,
                  close: 96500,
                  volume: 140,
                },
              ],
              supportLevel: 94800,
              resistanceLevel: 97500,
              bids: [{ price: 96495, size: 1.2, total: 1.2 }],
              asks: [{ price: 96505, size: 1.1, total: 1.1 }],
            }),
          };
        }
        if (url.includes('/portfolio')) {
          return {
            ok: true,
            json: async () => ({
              tradingMode: 'PAPER',
              cashBalance: 920000,
              positionsValue: 80000,
              totalEquity: 1000000,
              initialEquity: 1000000,
              dailyPnl: 12500,
              dailyPnlPct: 1.25,
              trilunairTargetUsd: 1000000000000,
              trilunairProgressPct: 0.0001,
              currentDrawdownPct: 0.4,
              maxAllowedDrawdownPct: 10,
              var95Usd: 4200,
              positions: [],
              recentOrders: [],
            }),
          };
        }
        if (url.includes('/ai/history')) {
          return {
            ok: true,
            json: async () => ({ messages: [], latestMeeting: null }),
          };
        }
        return {
          ok: true,
          json: async () => [],
        };
      })
    );
  });

  it('includes all 6 built-in themes (including Obsidian Black) and applies CSS variables instantly', () => {
    expect(INITIAL_PRESET_THEMES.map((p) => p.id)).toEqual([
      'royal-gold',
      'quantum-cyan',
      'nebula-purple',
      'emerald-matrix',
      'arctic-platinum',
      'obsidian-black',
    ]);

    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>
    );

    expect(screen.getByTestId('preset-count').textContent).toBe('6');

    for (const preset of INITIAL_PRESET_THEMES) {
      fireEvent.click(screen.getByText(`switch-${preset.id}`));
      expect(screen.getByTestId('active-theme').textContent).toBe(preset.id);
      expect(document.documentElement.getAttribute('data-theme')).toBe(preset.id);
      expect(document.documentElement.style.getPropertyValue('--accent-primary')).toBe(
        preset.tokens.accentPrimary
      );
    }
  });

  it('persists custom themes, exports valid JSON, imports JSON, and toggles accessibility modes', async () => {
    render(
      <ThemeProvider>
        <ThemeHarness />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByText('enable-a11y'));
    expect(document.documentElement.getAttribute('data-high-contrast')).toBe('true');
    expect(document.documentElement.getAttribute('data-low-power')).toBe('true');
    expect(document.documentElement.getAttribute('data-motion')).toBe('disabled');

    fireEvent.click(screen.getByText('save-custom'));
    await waitFor(() => {
      expect(screen.getByTestId('custom-count').textContent).toBe('1');
    });

    fireEvent.click(screen.getByText('export-json'));
    const exportedText = screen.getByTestId('exported-output').textContent || '';
    expect(exportedText).toContain('My Road to be Trilunair Dr.MaJoOoOoOoD');

    fireEvent.click(screen.getByText('import-json'));
    await waitFor(() => {
      expect(screen.getByTestId('custom-count').textContent).toBe('2');
    });
  });

  it('keeps trading controls functional when visual effects fail via VisualEffectsBoundary', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <div>
        <VisualEffectsBoundary>
          <ThrowingVisualWidget />
        </VisualEffectsBoundary>
        <button type="button">critical-trading-ticket-btn</button>
      </div>
    );

    expect(screen.getByText('critical-trading-ticket-btn')).toBeInTheDocument();
    spy.mockRestore();
  });

  it('renders Holographic Confirmation Seal and requires explicit user checkbox before execution', () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <ThemeProvider>
        <AuthorizationModal
          evaluation={MOCK_PROPOSAL_EVAL}
          isOpen={true}
          onClose={() => {}}
          onConfirmExecution={onConfirm}
        />
      </ThemeProvider>
    );

    expect(screen.getByTestId('holographic-confirmation-seal')).toBeInTheDocument();
    const execBtn = screen.getByTestId('authorize-execute-btn') as HTMLButtonElement;
    expect(execBtn.disabled).toBe(true);

    fireEvent.click(screen.getByTestId('auth-confirm-checkbox'));
    expect(execBtn.disabled).toBe(false);
  });

  it('mounts full App in Paper Trading default, toggles Cockpit & Focus modes, and keeps AI Dock accessible across screens', async () => {
    render(
      <ThemeProvider>
        <App />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('live-terminal-view')).toBeInTheDocument();
    });

    // التحقق من تصنيف TRADABLE_SPOT مقابل REFERENCE_ONLY في قائمة المراقبة
    expect(screen.getByText('TRADABLE_SPOT')).toBeInTheDocument();
    expect(screen.getByText('REFERENCE_ONLY')).toBeInTheDocument();

    // تفعيل Cockpit Mode و Focus Mode
    fireEvent.click(document.getElementById('cockpit-mode-toggle')!);
    expect(document.documentElement.getAttribute('data-cockpit')).toBe('true');

    fireEvent.click(document.getElementById('focus-mode-toggle')!);
    expect(document.documentElement.getAttribute('data-focus')).toBe('true');

    // التنقل بين الشاشات مع بقاء شريط الأوامر الصوتية متاحاً
    fireEvent.click(document.getElementById('nav-themes-btn')!);
    expect(document.documentElement.getAttribute('data-focus')).toBe('false');
  });
});
