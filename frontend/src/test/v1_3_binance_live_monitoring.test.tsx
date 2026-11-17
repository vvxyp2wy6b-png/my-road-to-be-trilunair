import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { trilunairApi } from '../api/client';
import { BinanceLiveAccountView } from '../components/BinanceLive/BinanceLiveAccountView';
import { ThemeProvider } from '../theme/ThemeContext';

describe('v1.3.0-binance-personal-guard LIVE ACCOUNT MONITORING & Biometric Wizard UI Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();

    vi.spyOn(trilunairApi, 'getThemes').mockResolvedValue({
      activeState: {
        activeThemeId: 'obsidian-black',
        modifiers: {
          glowIntensity: 55,
          blurRadius: 14,
          panelOpacity: 88,
          animationIntensity: 40,
          motionDisabled: true,
          lowPowerMode: false,
          highContrast: false,
        },
        customOverrides: {},
      },
      presets: [],
      customThemes: [],
    });
  });

  it('renders PENDING OWNER SETUP truthfully when unconfigured and strictly separates LIVE monitoring from $1M PAPER trading', async () => {
    vi.spyOn(trilunairApi, 'getPersonalBinanceOverview').mockResolvedValue({
      generatedAt: '2026-11-17T06:00:00Z',
      dashboardLabel: 'LIVE ACCOUNT MONITORING',
      segregatedFromPaperTrading: true,
      tradingMode: 'PAPER',
      liveAuthorized: false,
      executionLockedToPaper: true,
      connectionStatus: 'PENDING_OWNER_SETUP',
      supportedAuthMechanisms: [
        {
          algorithm: 'ED25519',
          recommended: true,
          label: 'Ed25519 Asymmetric API Key',
          officialDocs: 'Binance Spot API v3',
        },
      ],
      biometricArchitecture: {
        binanceAppFaceIdExplanationEn: 'Local Binance mobile Face ID only.',
        trilunairPasskeyExplanationEn: 'OS WebAuthn Passkeys.',
        enrolledPasskeyCount: 1,
        biometricStepUpRequiredForCredentialChanges: true,
        biometricTemplatesStoredOnServer: false,
      },
      credentialSlots: {
        READ_ONLY_MONITORING: { configured: false, status: 'PENDING_OWNER_SETUP' },
        FUTURE_SPOT_EXECUTION: { configured: false, status: 'NOT_CONFIGURED_LOCKED_TO_PAPER' },
      },
      portfolioSummary: {
        accountingMethod: 'WEIGHTED_AVERAGE_COST_BASIS_SPOT_LEDGER',
        totalEquityUsd: 0,
        totalEquitySar: 0,
        availableQuoteCashUsd: 0,
        availableQuoteCashSar: 0,
        investedCryptoCapitalUsd: 0,
        investedCryptoCapitalSar: 0,
        cryptoExposurePct: 0,
        netContributedCapitalUsd: 0,
        netContributedCapitalSar: 0,
        realizedPnlUsd: 0,
        realizedPnlSar: 0,
        unrealizedPnlUsd: 0,
        unrealizedPnlSar: 0,
        netPnlAfterFeesUsd: 0,
        netPnlAfterFeesSar: 0,
        cumulativeFeesUsd: 0,
        cumulativeFeesSar: 0,
        portfolioDrawdownPct: 0,
        reconciliationStatus: 'RECONCILED_EXACT',
        unreconciledAssetsCount: 0,
      },
      monthlyInvestmentBudgetTracking: {
        plannedMonthlyAllocationSar: 2125,
        plannedMonthlyAllocationUsd: 566.67,
        currentMonth: '2026-11',
        currentMonthVerifiedDepositsSar: 0,
        currentMonthSpotPurchasesSar: 0,
        remainingMonthlyBudgetSar: 2125,
      },
      balances: [],
      recentOrders: [],
      recentTrades: [],
      recentCashflows: [],
      riskAlerts: [],
    });

    vi.spyOn(trilunairApi, 'getLiveSpotReadiness').mockResolvedValue({
      workflowName: 'LIVE_SPOT',
      tradingMode: 'PAPER',
      liveAuthorized: false,
      executionLockedToPaper: true,
      realOrdersPermitted: false,
      passedGatesCount: 1,
      totalGatesCount: 8,
      gates: [
        {
          gateNumber: 1,
          gateId: 'VERIFIED_OFFICIAL_BINANCE_CONNECTION',
          titleEn: 'Verified Official Binance API Connection',
          titleAr: 'اتصال رسمي موثق بواجهة Binance API',
          passed: false,
          detailEn: 'Pending owner setup.',
        },
        {
          gateNumber: 8,
          gateId: 'OWNER_EXPLICIT_PRODUCTION_RELEASE_LOCK',
          titleEn: 'Permanent Release Safety Lock (Locked to PAPER Mode)',
          titleAr: 'قفل الأمان المعماري للإصدار (التنفيذ مقفل دائماً على PAPER)',
          passed: false,
          detailEn: 'Locked to PAPER.',
        },
      ],
      allowedSpotCapabilities: {
        sides: ['BUY', 'SELL'],
        orderTypes: ['LIMIT', 'MARKET', 'STOP_LOSS_LIMIT'],
        supportsOrderCancellation: true,
        supportsOrderStatusReconciliation: true,
      },
      prohibitedOperations: ['FUTURES_TRADING', 'MARGIN_TRADING', 'CRYPTO_OR_FIAT_WITHDRAWALS'],
      ownerPolicy: {
        ownerConfigured: false,
        jurisdictionEligibilityConfirmed: false,
        jurisdictionCountryCode: 'SA',
        maxSingleOrderSar: 750,
        maxSingleOrderUsd: 200,
        maxDailySpotSar: 1500,
        maxMonthlySpotSar: 2125,
        maxMonthlySpotUsd: 566.67,
        maxSingleAssetExposurePct: 45,
        requireBiometricPerOrder: true,
        allowedSpotSymbols: ['BTCUSDT', 'ETHUSDT'],
        updatedAt: '2026-11-17T06:00:00Z',
      },
    });

    const genSpy = vi.spyOn(trilunairApi, 'generateServerEd25519Keypair').mockResolvedValue({
      keypairId: 'edk_test_001',
      purpose: 'READ_ONLY_MONITORING',
      algorithm: 'ED25519',
      publicKeyPem: '-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEATestPublicKeyOnly\n-----END PUBLIC KEY-----',
      privateKeyExported: false,
      createdAt: '2026-11-17T06:00:00Z',
      binanceRegistrationInstructionsEn: 'Paste Public Key only.',
      binanceRegistrationInstructionsAr: 'الصق المفتاح العام فقط.',
    });

    render(
      <ThemeProvider>
        <BinanceLiveAccountView />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('binance-personal-status-badge').textContent).toContain('PENDING OWNER SETUP');
    });
    expect(screen.getByTestId('live-spot-eight-gates-panel')).toBeTruthy();

    // Generate server-side Ed25519 Public Key and verify zero browser storage leakage
    const genBtn = screen.getByRole('button', { name: /Ed25519/i });
    fireEvent.click(genBtn);

    await waitFor(() => {
      expect(genSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/MCowBQYDK2VwAyEATestPublicKeyOnly/)).toBeTruthy();
    });

    expect(JSON.stringify(window.localStorage)).not.toContain('PRIVATE KEY');
    expect(JSON.stringify(window.sessionStorage)).not.toContain('PRIVATE KEY');
  });
});
