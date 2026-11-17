import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ThemeProvider } from '../theme/ThemeContext';
import { GovernanceView } from '../components/Governance/GovernanceView';
import { PortfolioView } from '../components/Portfolio/PortfolioView';
import { trilunairApi } from '../api/client';
import type { PortfolioSnapshot, SystemStatus, WealthArchitectOverview } from '../types/trilunair';

describe('v1.2.0-low-latency-cloudflare Passkeys, Region Telemetry & Personal CFO / Saudi Benefits UI Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders Owner Biometric Passkeys panel (Zero Biometric Templates Stored), medinsup.com isolation badge, and Tokyo Region Latency Telemetry panel', async () => {
    vi.spyOn(trilunairApi, 'getOperationsTelemetry').mockRejectedValue(new Error('isolated unit test'));
    vi.spyOn(trilunairApi, 'getAdminSessionStatus').mockResolvedValue({
      authenticated: false,
      authConfigured: true,
      authMode: 'SESSION_COOKIE+WEBAUTHN',
      reasonAr: 'غير مسجل',
      reasonEn: 'Unauthenticated',
      csrfToken: null,
      expiresAtEpoch: null,
      tradingMode: 'PAPER',
      liveAuthorized: false,
      executionLockedToPaper: true,
    });

    vi.spyOn(trilunairApi, 'getPasskeyStatus').mockResolvedValue({
      webauthnSupported: true,
      biometricImagesOrTemplatesStored: false,
      rpId: 'trilunair.medinsup.com',
      rpName: 'TRILUNAIR Sovereign Command',
      primaryDomain: 'trilunair.medinsup.com',
      isolatedMedicalDomain: 'medinsup.com',
      registeredDeviceCount: 1,
      remainingRecoveryCodes: 6,
      supportedAuthenticators: ['Face ID', 'Touch ID', 'Apple Passkeys', 'YubiKey FIDO2'],
      stepUpRequiredActions: ['EDIT_RISK_PARAMETERS', 'REVOKE_DEVICE_OR_RECOVERY_ACCESS'],
      devices: [
        {
          credentialId: 'cred_iphone_faceid_001',
          credentialIdPreview: 'cred_iph...001',
          ownerId: 'owner-dr-majoooood',
          deviceLabel: 'Dr.MaJoOoOoOoD iPhone 16 Pro Face ID',
          algorithm: 'ES256 (P-256)',
          signCount: 12,
          rpId: 'trilunair.medinsup.com',
          createdAt: '2026-11-17T04:00:00Z',
          lastUsedAt: '2026-11-17T05:00:00Z',
          revoked: false,
          biometricTemplateStored: false,
        },
      ],
    });

    vi.spyOn(trilunairApi, 'getBenchmarkMatrix').mockResolvedValue({
      schemaVersion: '1.2.0-low-latency-cloudflare',
      targetDomain: 'trilunair.medinsup.com',
      isolatedMedicalDomain: 'medinsup.com',
      selectionStatus: 'PROVISIONAL_PENDING_REGIONAL_CLOUD_PROBES',
      regionalProbesIngestedCount: 0,
      recommendedPrimaryOption: {
        optionId: 'tokyo-oci-always-free-arm',
        regionCode: 'ap-tokyo-1',
        regionNameEn: 'Tokyo, Japan (ap-tokyo-1 — Always Free ARM)',
        regionNameAr: 'طوكيو، اليابان (Oracle Cloud Always Free)',
        provider: 'Oracle Cloud Always Free Ampere A1 + Cloudflare Free',
        monthlyCostUsd: 0.0,
        regionalMeasurementStatus: 'NOT_MEASURED',
        weightedScore: 95.35,
      },
      recommendedPaidSlaFallbackOption: {
        optionId: 'tokyo-aws-lightsail-2gb-sla',
        regionCode: 'ap-northeast-1',
        regionNameEn: 'Tokyo, Japan (ap-northeast-1)',
        provider: 'AWS Lightsail Linux VPS + Cloudflare Free',
        monthlyCostUsd: 12.0,
        weightedScore: 92.85,
      },
      rankedQualifiedOptions: [
        {
          optionId: 'tokyo-oci-always-free-arm',
          regionCode: 'ap-tokyo-1',
          regionNameEn: 'Tokyo, Japan (ap-tokyo-1)',
          regionNameAr: 'طوكيو، اليابان',
          provider: 'Oracle Cloud Always Free + Cloudflare Free',
          monthlyCostUsd: 0.0,
          regionalMeasurementStatus: 'NOT_MEASURED',
          weightedScore: 95.35,
        },
      ],
    });

    vi.spyOn(trilunairApi, 'getLatencyPipeline').mockResolvedValue({
      pipelineArchitecture: 'Binance Market Data -> Parallel AI Council -> Risk Engine -> PAPER Execution',
      councilDeadlineMs: 2200,
      defaultSignalTtlSeconds: 45,
      counters: {
        parallelProviderDeadlineTimeouts: 0,
        costAwareCloudInferenceSkips: 2,
        staleOrExpiredSignalBlocks: 0,
      },
      stages: {
        marketDataAgeMs: { samples: 4, lastMs: 1.1, meanMs: 1.3, p50Ms: 1.2, p95Ms: 2.1, p99Ms: 2.4, maxMs: 2.4 },
        totalSignalToDecisionMs: { samples: 4, lastMs: 13.8, meanMs: 16.4, p50Ms: 14.2, p95Ms: 28.5, p99Ms: 31.0, maxMs: 31.0 },
      },
    });

    vi.spyOn(trilunairApi, 'getPerformanceEvaluation').mockResolvedValue({
      symbol: 'BTC-USD',
      timeframe: '15m',
      inSampleBars: 108,
      outOfSampleBars: 72,
      outOfSampleComparison: {
        sequentialBaseline: {
          netReturnPct: 0.31,
          netPnlAfterAllCostsUsd: 3060,
          sharpeRatio: 1.05,
          maxDrawdownPct: 0.35,
          costBreakdownUsd: { totalFrictionUsd: 420.5 },
        },
        lowLatencyCostAwareOptimized: {
          netReturnPct: 0.57,
          netPnlAfterAllCostsUsd: 5700,
          sharpeRatio: 1.72,
          maxDrawdownPct: 0.24,
          costBreakdownUsd: { totalFrictionUsd: 215.2 },
        },
        improvements: {
          netPnlDeltaUsd: 2640,
          totalFrictionSavedUsd: 205.3,
          drawdownReductionPct: 0.11,
          sharpeDelta: 0.67,
        },
      },
    });

    const status: SystemStatus = {
      appName: 'My Road to be Trilunair Dr.MaJoOoOoOoD',
      version: '1.2.0-low-latency-cloudflare',
      tradingMode: 'PAPER',
      killSwitchActive: false,
      liveAuthorized: false,
      executionLockedToPaper: true,
      marketDataMode: 'LIVE_PUBLIC',
      riskPolicy: {
        maxRiskPerTradePct: 0.5,
        maxExposurePerAssetPct: 25.0,
        dailyLossLimitPct: 2.0,
        weeklyLossLimitPct: 5.0,
        maxDrawdownLimitPct: 10.0,
        prohibitLeverage: true,
      },
      safetyChecks: {
        riskEngineVerified: true,
        maxDrawdownConfigured: true,
        killSwitchReady: true,
        positionLimitsActive: true,
        auditTrailHealthy: true,
      },
      providers: {
        llmProvider: 'multi-provider-council',
        sttProvider: 'web-speech-primary',
        ttsProvider: 'speech-synthesis+server-wav',
      },
    };

    render(
      <ThemeProvider>
        <GovernanceView
          systemStatus={status}
          auditLogs={[]}
          onSwitchTradingMode={vi.fn()}
          onToggleKillSwitch={vi.fn()}
        />
      </ThemeProvider>
    );

    const passkeyPanel = await screen.findByTestId('passkey-biometric-panel');
    await waitFor(() => {
      expect(passkeyPanel.textContent).toContain('trilunair.medinsup.com');
      expect(passkeyPanel.textContent).toContain('Dr.MaJoOoOoOoD iPhone 16 Pro Face ID');
    });

    const latencyPanel = await screen.findByTestId('region-latency-telemetry-panel');
    await waitFor(() => {
      expect(latencyPanel.textContent).toContain('95.35');
      expect(latencyPanel.textContent).toContain('NOT_MEASURED');
    });
  });

  it('renders Personal CFO, Tasheel/Emirates NBD planner, Saudi Fixed-Term Employment Benefits (PROVISIONAL), and 60-Day Cutoff (2027-08-11)', async () => {
    const mockWealth: WealthArchitectOverview = {
      generatedAt: '2026-11-17T06:00:00Z',
      currency: 'SAR',
      fxPegSarPerUsd: 3.75,
      salaryAndCashFlow: {
        monthlySalarySar: 20000,
        paydayDayOfMonth: 28,
        currentSalaryCycleId: 'CYCLE_2026-10-28',
        nextPaydayDate: '2026-11-28',
        daysUntilNextPayday: 11,
        plannedTotalAllocatedSar: 20000,
        unallocatedSalarySar: 0,
        balancedToExactSalary: true,
        reconciledCycleTotalOutflowSar: 20000,
        reconciledCycleSurplusOrDeficitSar: 0,
        importedStatementCountInCycle: 0,
        cardPurchaseMemoExcludedFromDoubleCountSar: 0,
        antiDoubleCountingPolicy: 'SHA256_DEDUP_AND_BUCKET_RECONCILIATION',
        buckets: [
          { category: 'PERSONAL_EXPENSES', labelEn: 'Personal Expenses', labelAr: 'المصروفات الشخصية والمعيشية', plannedSar: 8000, shareOfSalaryPct: 40, importedActualSar: 0, effectiveReconciledOutflowSar: 8000, remainingPlannedAllowanceSar: 8000, budgetOverrunSar: 0 },
          { category: 'CREDIT_CARD_REPAYMENTS', labelEn: 'Credit-Card Repayments', labelAr: 'سداد البطاقات الائتمانية', plannedSar: 6000, shareOfSalaryPct: 30, importedActualSar: 0, effectiveReconciledOutflowSar: 6000, remainingPlannedAllowanceSar: 6000, budgetOverrunSar: 0 },
          { category: 'INVESTMENT_ALLOCATION', labelEn: 'Investment Allocation', labelAr: 'مخصص الاستثمار المعتمد', plannedSar: 2125, shareOfSalaryPct: 10.63, importedActualSar: 0, effectiveReconciledOutflowSar: 2125, remainingPlannedAllowanceSar: 2125, budgetOverrunSar: 0 },
        ],
      },
      debtPlanner: {
        totalApproximateCardBalanceSar: 31000,
        totalReportedDueInclArrearsSar: 3500,
        monthlyRepaymentBudgetSar: 6000,
        allocatedAcrossCardsSar: 6000,
        budgetFullyAssigned: true,
        cards: [
          {
            cardId: 'tasheel',
            issuerNameEn: 'Tasheel Finance',
            issuerNameAr: 'تسهيل للتمويل (Tasheel)',
            approximateBalanceSar: 14000,
            reportedAmountDueInclArrearsSar: 1700,
            provisionalMonthlyAllocationSar: 4200,
            excessAboveReportedDueSar: 2500,
            estimatedAnnualAprPct: 32,
            paymentDueDay: 5,
            verifications: { currentDuesVerified: false, delinquencyVerified: false, financingChargesVerified: false, paymentDateVerified: false },
            notesEn: 'Accelerated paydown',
            notesAr: 'سداد معجل',
          },
          {
            cardId: 'emirates-nbd',
            issuerNameEn: 'Emirates NBD KSA',
            issuerNameAr: 'بنك الإمارات دبي الوطني (Emirates NBD)',
            approximateBalanceSar: 17000,
            reportedAmountDueInclArrearsSar: 1800,
            provisionalMonthlyAllocationSar: 1800,
            excessAboveReportedDueSar: 0,
            estimatedAnnualAprPct: 30,
            paymentDueDay: 5,
            verifications: { currentDuesVerified: false, delinquencyVerified: false, financingChargesVerified: false, paymentDateVerified: false },
            notesEn: 'Covers reported due incl arrears',
            notesAr: 'تغطية المستحق والمتأخرات',
          },
        ],
        payoffProjection: {
          estimatedMonthsToDebtFree: 6,
          estimatedTotalFinancingCostSar: 2480,
          weightedEstimatedCardAprPct: 30.9,
          postPayoffFreedMonthlyCashflowSar: 6000,
        },
        debtVsInvestmentTradeOff: {
          policy: 'BALANCED_INVESTMENT_FIRST_WITH_OVERDUE_GUARD',
          debtEliminationIsBlanketPrerequisite: false,
          weightedCardFinancingCostAprPct: 30.9,
          guaranteedEffectiveReturnOfDebtPaydownPct: 30.9,
          illustrativeDiversifiedInvestmentReturnBandPct: '6.5% - 12.0% (Non-Guaranteed)',
          tradeOffExplanationEn: 'Debt financing cost vs investment risk displayed transparently.',
          tradeOffExplanationAr: 'مقارنة شفافة بين تكلفة التمويل ومخاطر الاستثمار.',
        },
      },
      employmentBenefits: {
        statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION',
        accountingTreatment: 'CONTINGENT_FUTURE_RECEIVABLE',
        countedAsAvailableLiquidCash: false,
        countedInLiquidEmergencyReserve: false,
        usableForTradingOrImmediateDebtPayments: false,
        legalEntitlementGuaranteedWithoutReview: false,
        contractSummary: {
          jurisdiction: 'Saudi Arabia (HRSD / Saudi Labor Law)',
          commencementDate: '2024-10-10',
          illustrativeOrTargetEndDate: '2027-10-10',
          exactExpiryDateVerified: false,
          contractType: 'FIXED_TERM',
          autoRenews: true,
          nonRenewalNoticeDays: 60,
          expectedDepartureMethod: 'NON_RENEWAL_UPON_EXPIRY',
          eligibleFinalMonthlyWageSar: 20000,
          dailyEligibleWageSar: 666.6667,
          annualLeaveDaysPerYear: 21,
          annualLeaveTakenDays: 0,
          accruedUnusedLeaveDays: 63,
          serviceDuration: { completedFullYears: 3, remainderDays: 0, totalCalendarDays: 1095, serviceYearsExact: 3 },
        },
        primaryExpectedScenario: {
          scenarioId: 'FIXED_TERM_EXPIRY_NON_RENEWAL',
          titleEn: 'Fixed-Term Contract Expiry & Timely Non-Renewal',
          titleAr: 'انتهاء العقد المحدد المدة وعدم تجديده بإشعار نظامي (60 يوماً)',
          legalBasis: 'Saudi Labor Law Art. 55, Art. 74(1), Art. 84 & Art. 111',
          classifiedAsMidTermResignation: false,
          eosbAwardSar: 30000,
          unusedLeaveCompensationSar: 42000,
          combinedEstimatedBenefitsSar: 72000,
          settlementDeadlineRule: 'Art. 88 (within 1 week)',
          statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION',
          legalCaveatEn: 'Subject to Qiwa contract verification.',
          legalCaveatAr: 'خاضع للتحقق من عقد قوى.',
        },
        scenarios: {
          fixedTermExpiryNonRenewal: {
            scenarioId: 'FIXED_TERM_EXPIRY_NON_RENEWAL',
            titleEn: 'Fixed-Term Expiry & Non-Renewal',
            titleAr: 'انتهاء العقد المحدد المدة وعدم تجديده',
            legalBasis: 'Art. 74(1), 84, 111',
            classifiedAsMidTermResignation: false,
            eosbAwardSar: 30000,
            unusedLeaveCompensationSar: 42000,
            combinedEstimatedBenefitsSar: 72000,
            statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION',
          },
          ordinaryResignation: {
            scenarioId: 'ORDINARY_RESIGNATION_ART_85',
            titleEn: 'Ordinary Resignation (Art. 85 — 1/3 EOSB)',
            titleAr: 'الاستقالة العادية (المادة 85 — ثلث المكافأة)',
            legalBasis: 'Art. 85 & Art. 111',
            classifiedAsMidTermResignation: true,
            eosbMultiplier: 0.3333,
            eosbAwardSar: 10000,
            unusedLeaveCompensationSar: 42000,
            combinedEstimatedBenefitsSar: 52000,
            statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION',
          },
          employerInitiatedTermination: {
            scenarioId: 'EMPLOYER_INITIATED_TERMINATION',
            titleEn: 'Employer-Initiated Termination',
            titleAr: 'إنهاء العقد من قِبل صاحب العمل',
            legalBasis: 'Art. 84 & Art. 111',
            eosbAwardSar: 30000,
            unusedLeaveCompensationSar: 42000,
            combinedEstimatedBenefitsSar: 72000,
            statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION',
          },
          otherStatutoryScenarios: {
            forceMajeureOrEmployerBreach: {
              scenarioId: 'ART_87_81',
              titleEn: 'Force Majeure / Art. 81',
              eosbAwardSar: 30000,
              unusedLeaveCompensationSar: 42000,
              combinedEstimatedBenefitsSar: 72000,
              statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION',
            },
            dismissalForCauseArt80: {
              scenarioId: 'ART_80',
              titleEn: 'Dismissal for Cause (Art. 80)',
              eosbAwardSar: 0,
              unusedLeaveCompensationSar: 42000,
              combinedEstimatedBenefitsSar: 42000,
              statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION',
            },
          },
        },
        verificationChecklist: [
          { itemId: 'exactContractExpiry', labelEn: 'Exact contract expiry date from signed Qiwa contract', labelAr: 'تاريخ انتهاء العقد الفعلي من عقد قوى', verified: false },
        ],
      },
      contractRenewalIntelligence: {
        contractExpiryDate: '2027-10-10',
        exactExpiryDateVerified: false,
        requiredAdvanceNoticeDays: 60,
        finalNoticeDeadlineDate: '2027-08-11',
        daysUntilFinalNoticeDeadline: 267,
        daysUntilContractExpiry: 327,
        deadlineState: 'TRACKING_AHEAD_OF_SCHEDULE',
        noticeCalculationRuleNoteEn: '2027-10-10 minus 60 calendar days = 2027-08-11',
        noticeCalculationRuleNoteAr: '2027-10-10 ناقص 60 يوماً = 2027-08-11',
        autoSendNonRenewalNotice: false,
        ownerApprovalPolicy: 'NEVER_AUTO_SEND_WITHOUT_EXPLICIT_OWNER_ACTION',
        reminders: [
          { milestoneCode: 'REMINDER_90D', daysBeforeExpiry: 90, reminderDate: '2027-07-12', daysFromToday: 237, status: 'SCHEDULED', messageEn: '90d check', messageAr: 'تنبيه 90 يوماً' },
          { milestoneCode: 'REMINDER_75D', daysBeforeExpiry: 75, reminderDate: '2027-07-27', daysFromToday: 252, status: 'SCHEDULED', messageEn: '75d check', messageAr: 'تنبيه 75 يوماً' },
          { milestoneCode: 'REMINDER_65D', daysBeforeExpiry: 65, reminderDate: '2027-08-06', daysFromToday: 262, status: 'SCHEDULED', messageEn: '65d check', messageAr: 'تنبيه 65 يوماً' },
        ],
        evidenceVault: [],
      },
      investmentCommandCenter: {
        ledgerSummary: { entryCount: 0, cumulativeAllocatedCapitalSar: 0, cumulativeAllocatedCapitalUsdEquiv: 0, entries: [] },
        opportunityAndRiskAnalysis: {
          monthlyAllocationSar: 2125,
          monthlyAllocationUsdEquiv: 566.67,
          annualizedContributionRunRateSar: 25500,
          executionSafeguards: {
            binanceTradingMode: 'PAPER',
            liveTradingAuthorized: false,
            realMoneyOrdersPlaced: false,
            externalBrokerageAccountsOpened: false,
            returnsGuaranteed: false,
            reliesOnSpeculativeProfitsForMandatoryPayments: false,
          },
          sleeves: [
            { sleeveId: 'DIVERSIFIED_GLOBAL_ETF_SUKUK', nameEn: 'Diversified Global ETFs & Sukuk', nameAr: 'سلة الصناديق العالمية والصكوك', targetWeightPct: 45, monthlyAllocationSar: 956.25, illustrativeAnnualReturnBandPct: '6.5% - 9.5%', annualizedVolatilityPct: 10.8, estimatedTransactionFeeBps: 12, liquidityProfile: 'High (T+1)', severeStressDrawdownPct: -16, roleInPortfolioEn: 'Core anchor', roleInPortfolioAr: 'ركيزة أساسية' },
          ],
          downsideScenarios: [
            { scenarioId: 'MODERATE_PULLBACK', labelEn: '-15% Moderate Pullback', labelAr: 'تصحيح معتدل (-15%)', year1ContributedSar: 25500, stressedPortfolioValueSar: 21675, unrealizedDrawdownSar: -3825, mandatoryDebtImpact: 'ZERO_IMPACT_ON_MANDATORY_LIVING_OR_DEBT' },
          ],
        },
      },
      balanceSheetAndForecast: {
        liquidAssetsAvailableNow: { liquidCashReserveSar: 2000, availableCurrentCycleCashSar: 20000, cumulativeInvestedCapitalLedgerSar: 0, includesUnreceivedEmploymentBenefits: false },
        contingentFutureReceivablesSegregated: { statusLabel: 'PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION', classification: 'CONTINGENT_FUTURE_RECEIVABLE', fixedTermNonRenewalCombinedEstimateSar: 72000, ordinaryResignationCombinedEstimateSar: 52000, usableForImmediateDebtOrTrading: false },
        thirtySixMonthIllustrativeForecast: { horizonMonths: 36, projectedLiquidCashSavingsSar: 72000, projectedInvestedPrincipalBaselineSar: 76500, projectedInvestedPrincipalWithPostDebtSnowballSar: 166500, contingentEmploymentSettlementSeparateSar: 72000, assumesSpeculativeMarketGains: false },
      },
      wealthGuardian: {
        guardianStatus: 'INVESTMENT_ALLOCATION_CLEARED',
        debtEliminationRequiredBeforeInvesting: false,
        availableImmediateCycleCashSar: 20000,
        minimumMandatoryLivingAndOverdueFloorSar: 11500,
        scheduledCardRepaymentSar: 6000,
        recommendedCycleInvestmentSar: 2125,
        summaryEn: 'Mandatory expenses & overdue card dues covered.',
        summaryAr: 'المصروفات الأساسية والمبالغ المستحقة مغطاة بالكامل.',
      },
      financialAlerts: [
        { alertId: 'VERIFY_QIWA_EXPIRY', severity: 'WARNING', category: 'CONTRACT_DEADLINE', titleEn: 'Verify Exact Contract Expiry Date', titleAr: 'التحقق من تاريخ انتهاء العقد الفعلي', detailEn: 'Confirm Qiwa expiry before 2027-08-11.', detailAr: 'تأكد من تاريخ انتهاء العقد في قوى قبل 2027-08-11.' },
      ],
    };

    vi.spyOn(trilunairApi, 'getWealthOverview').mockResolvedValue(mockWealth);

    const mockPortfolio: PortfolioSnapshot = {
      tradingMode: 'PAPER',
      cashBalance: 1000000,
      positionsValue: 0,
      totalEquity: 1000000,
      initialEquity: 1000000,
      dailyPnl: 0,
      dailyPnlPct: 0,
      weeklyLossPct: 0,
      trilunairTargetUsd: 1000000000000,
      trilunairProgressPct: 50,
      currentDrawdownPct: 0,
      maxAllowedDrawdownPct: 10,
      var95Usd: 0,
      positions: [],
      recentOrders: [],
    };

    render(
      <ThemeProvider>
        <PortfolioView portfolio={mockPortfolio} />
      </ThemeProvider>
    );

    const cfoPanel = await screen.findByTestId('personal-cfo-wealth-panel');
    await waitFor(() => {
      expect(cfoPanel.textContent).toContain('20,000');
      expect(cfoPanel.textContent).toContain('4,200');
      expect(cfoPanel.textContent).toContain('1,800');
      expect(cfoPanel.textContent).toContain('PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION');
      expect(cfoPanel.textContent).toContain('72,000');
      expect(cfoPanel.textContent).toContain('2027-08-11');
    });
  });
});
