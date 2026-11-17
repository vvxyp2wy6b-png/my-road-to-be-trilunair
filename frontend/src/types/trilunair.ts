/**
 * تعريفات الأنواع المشتركة لنظام مركز القيادة الهولوغرامي
 * My Road to be Trilunair Dr.MaJoOoOoOoD
 */

export type Language = 'ar' | 'en';
export type TradingMode = 'PAPER' | 'LIVE';
export type CommandSource = 'VOICE' | 'TEXT' | 'TERMINAL';
export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'MARKET' | 'LIMIT';
export type AgentStance = 'BUY' | 'SELL' | 'HOLD' | 'CAUTION';

export type PresetThemeId =
  | 'royal-gold'
  | 'quantum-cyan'
  | 'nebula-purple'
  | 'emerald-matrix'
  | 'arctic-platinum'
  | 'obsidian-black';

export interface ThemeTokens {
  bgBase: string;
  bgElevated: string;
  bgSurface: string;
  accentPrimary: string;
  accentSecondary: string;
  accentTertiary: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  borderHolo: string;
  success: string;
  danger: string;
  warning: string;
}

export interface ThemeModifiers {
  glowIntensity: number;      // 0 - 100
  blurRadius: number;         // 0 - 32 (px)
  panelOpacity: number;       // 40 - 98 (%)
  animationIntensity: number; // 0 - 100
  motionDisabled: boolean;
  highContrast: boolean;
  lowPowerMode: boolean;
}

export interface ThemeDefinition {
  id: string;
  nameAr: string;
  nameEn: string;
  descriptionAr: string;
  descriptionEn: string;
  isCustom?: boolean;
  tokens: ThemeTokens;
  defaultModifiers?: Partial<ThemeModifiers>;
}

export interface ActiveThemeState {
  activeThemeId: string;
  customOverrides: Partial<ThemeTokens>;
  modifiers: ThemeModifiers;
}

export interface ThemesPayload {
  presets: ThemeDefinition[];
  customThemes: ThemeDefinition[];
  activeState: ActiveThemeState;
}

export interface SafetyChecks {
  riskEngineVerified: boolean;
  maxDrawdownConfigured: boolean;
  killSwitchReady: boolean;
  positionLimitsActive: boolean;
  auditTrailHealthy: boolean;
}

export interface RiskPolicySummary {
  maxRiskPerTradePct: number;
  maxExposurePerAssetPct: number;
  dailyLossLimitPct: number;
  weeklyLossLimitPct: number;
  maxDrawdownLimitPct: number;
  prohibitLeverage: boolean;
}

export interface SystemStatus {
  appName: string;
  version: string;
  tradingMode: TradingMode;
  killSwitchActive: boolean;
  killSwitchReason?: string;
  liveAuthorized: boolean;
  executionLockedToPaper?: boolean;
  marketDataMode?: string;
  riskPolicy?: RiskPolicySummary;
  safetyChecks: SafetyChecks;
  providers: {
    llmProvider: string;
    sttProvider: string;
    ttsProvider: string;
  };
}

export interface MarketAsset {
  symbol: string;
  nameAr: string;
  nameEn: string;
  category: 'CRYPTO' | 'EQUITY' | 'COMMODITY';
  price: number;
  change24hPct: number;
  high24h: number;
  low24h: number;
  volume24hUsd: number;
  volatilityPct: number;
  spreadBps: number;
  dataSource?: string;
}

export interface CandlePoint {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OrderbookLevel {
  price: number;
  size: number;
  total: number;
}

export interface MarketCandlesResponse {
  symbol: string;
  timeframe: string;
  candles: CandlePoint[];
  supportLevel: number;
  resistanceLevel: number;
  bids: OrderbookLevel[];
  asks: OrderbookLevel[];
  dataSource?: string;
  lastUpdateId?: number | null;
}

export interface PositionItem {
  symbol: string;
  nameAr: string;
  nameEn: string;
  quantity: number;
  avgEntryPrice: number;
  currentPrice: number;
  marketValueUsd: number;
  unrealizedPnlUsd: number;
  unrealizedPnlPct: number;
  weightPct: number;
}

export interface OrderRecord {
  orderId: string;
  proposalId: string;
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  quantity: number;
  executedPrice: number;
  notionalUsd: number;
  totalFeeUsd: number;
  tradingMode: TradingMode;
  isSimulatedFill?: boolean;
  source: CommandSource;
  status: 'FILLED' | 'REJECTED' | 'CANCELLED';
  createdAt: string;
}

export interface PortfolioSnapshot {
  tradingMode: TradingMode;
  cashBalance: number;
  positionsValue: number;
  totalEquity: number;
  initialEquity: number;
  dailyPnl: number;
  dailyPnlPct: number;
  weeklyLossPct?: number;
  trilunairTargetUsd: number;
  trilunairProgressPct: number;
  currentDrawdownPct: number;
  maxAllowedDrawdownPct: number;
  var95Usd: number;
  positions: PositionItem[];
  recentOrders: OrderRecord[];
}

export interface EstimatedTradingCosts {
  notionalUsd: number;
  spreadCostUsd: number;
  commissionUsd: number;
  slippageCostUsd: number;
  totalEstimatedCostUsd: number;
  costBps: number;
}

export interface RiskCheckItem {
  code: string;
  passed: boolean;
  messageAr: string;
  messageEn: string;
}

export interface RiskAssessment {
  passed: boolean;
  riskScore: number;
  riskLevel: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  postTradeConcentrationPct: number;
  varImpactUsd: number;
  checks: RiskCheckItem[];
  violations: string[];
}

export interface TradeProposalInput {
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  quantity: number;
  limitPrice?: number | null;
  stopLoss?: number | null;
  takeProfit?: number | null;
  source: CommandSource;
  rationale?: string;
  clientOrderId?: string | null;
  ttlSeconds?: number | null;
}

export interface TradeProposalEvaluation {
  proposalId: string;
  status: 'APPROVED_FOR_AUTH' | 'REJECTED_BY_RISK' | 'EXPIRED' | 'EXECUTED' | 'CANCELLED_BY_KILL_SWITCH';
  proposal: TradeProposalInput & { referencePrice: number; createdAt: string; expiresAt?: string | null };
  estimatedCosts: EstimatedTradingCosts;
  riskAssessment: RiskAssessment;
  tradingMode: TradingMode;
  requiresLivePin: boolean;
  expiresAt?: string | null;
}

export interface AgentProfile {
  agentId: string;
  nameAr: string;
  nameEn: string;
  roleAr: string;
  roleEn: string;
  specialtyAr: string;
  specialtyEn: string;
  status: 'ONLINE' | 'ANALYZING' | 'VOTING' | 'ALERT';
  accentToken: string;
}

export type AgentExecutionStatus = 'LIVE' | 'SIMULATED' | 'CACHED' | 'UNAVAILABLE';

export interface AgentDeliberationItem {
  agentId: string;
  nameAr: string;
  nameEn: string;
  roleAr: string;
  roleEn: string;
  status: 'READY' | 'AGREE' | 'DISSENT' | 'CAUTION';
  stance: AgentStance;
  confidence: number;
  uncertaintyPct?: number;
  summaryAr: string;
  summaryEn: string;
  keyMetricLabelAr: string;
  keyMetricLabelEn: string;
  keyMetricValue: string;
  providerUsed?: string;
  modelUsed?: string;
  isSimulated?: boolean;
  executionStatus?: AgentExecutionStatus;
  respondedAt?: string;
}

export interface AdminSessionStatus {
  authenticated: boolean;
  authConfigured: boolean;
  authMode: string;
  reasonAr: string;
  reasonEn: string;
  csrfToken?: string | null;
  expiresAtEpoch?: number | null;
  tradingMode: TradingMode;
  liveAuthorized: boolean;
  executionLockedToPaper: boolean;
}

export interface CloudOperationsTelemetry {
  releaseVersion: string;
  timestamp: string;
  environment: string;
  executionSafety: {
    tradingMode: TradingMode;
    liveAuthorized: boolean;
    executionLockedToPaper: boolean;
    autonomousLiveTradingDisabled: boolean;
    realOrdersPermitted: boolean;
    withdrawalsPermitted: boolean;
    marginAndLeveragePermitted: boolean;
    killSwitchActive: boolean;
    killSwitchReason?: string;
  };
  adminSecurity: {
    authConfigured: boolean;
    authMode: string;
    failClosedActive: boolean;
    defaultTestPinsRemoved: boolean;
    corsAllowedOrigins: string[];
    metrics: {
      uptimeSeconds: number;
      totalHttpRequests: number;
      serverErrorRatePct: number;
      authFailures: number;
      rateLimitBlocks: number;
      liveModeBlocks: number;
    };
  };
  riskPolicy: RiskPolicySummary;
  subsystems: {
    frontend: {
      status: string;
      servingStaticSpa: boolean;
      bundleAssetCount: number;
      messageAr: string;
      messageEn: string;
    };
    backendApi: {
      status: string;
      version: string;
      uptimeSeconds: number;
      serverErrorRatePct: number;
      totalHttpRequests: number;
    };
    postgresql: {
      status: string;
      activeBackend: string;
      configuredEngine: string;
      latencyMs: number;
      persistent: boolean;
    };
    redis: {
      status: string;
      connected: boolean;
      mode: string;
      latencyMs: number;
    };
    binancePublicMarketData: {
      marketDataMode: string;
      restStatus: string;
      wsStatus: string;
      feedFresh: boolean;
      ageSeconds: number;
      usedWeight1m: number;
      rateLimited: boolean;
      lastRestError?: string | null;
      lastWsError?: string | null;
    };
    aiProviders: {
      cloudConnectedCount: number;
      localDeterministicEngineActive: boolean;
      providers: Array<{
        providerId: string;
        displayName: string;
        status: string;
        available: boolean;
        configuredModel?: string;
        lastLatencyMs?: number | null;
        errorRatePct?: number;
      }>;
    };
    voiceServices: {
      status: string;
      cloudSpeechConfigured: boolean;
      sttPrimaryEngine: string;
      ttsPrimaryEngine: string;
    };
    webSocketHub: {
      status: string;
      broadcasterRunning: boolean;
      activeClientConnections: number;
      totalOpened: number;
      totalRejected: number;
    };
    accountReconciliation: {
      status: string;
      consistent: boolean;
      accountStateUncertain: boolean;
      equityDriftUsd: number;
      totalEquityUsd: number;
      lastReconciledAt: string;
    };
  };
  hostingRegionDecision?: {
    selectionStatus: string;
    recommendedPrimaryOption: {
      optionId: string;
      regionCode: string;
      regionNameEn: string;
      regionNameAr: string;
      provider: string;
      monthlyCostUsd: number;
      regionalMeasurementStatus: string;
      weightedScore: number;
    };
  };
}

export interface PasskeyDeviceItem {
  credentialId: string;
  credentialIdPreview: string;
  ownerId: string;
  deviceLabel: string;
  algorithm: string;
  signCount: number;
  rpId: string;
  createdAt: string;
  lastUsedAt?: string | null;
  revoked: boolean;
  biometricTemplateStored: boolean;
}

export interface PasskeySecurityPosture {
  webauthnSupported: boolean;
  biometricImagesOrTemplatesStored: boolean;
  rpId: string;
  rpName: string;
  primaryDomain: string;
  isolatedMedicalDomain: string;
  registeredDeviceCount: number;
  remainingRecoveryCodes: number;
  supportedAuthenticators: string[];
  stepUpRequiredActions: string[];
  devices: PasskeyDeviceItem[];
}

export interface HostingDecisionMatrix {
  schemaVersion: string;
  targetDomain: string;
  isolatedMedicalDomain: string;
  selectionStatus: string;
  regionalProbesIngestedCount: number;
  recommendedPrimaryOption: {
    optionId: string;
    regionCode: string;
    regionNameEn: string;
    regionNameAr: string;
    provider: string;
    monthlyCostUsd: number;
    regionalMeasurementStatus: string;
    weightedScore: number;
  };
  recommendedPaidSlaFallbackOption: {
    optionId: string;
    regionCode: string;
    regionNameEn: string;
    provider: string;
    monthlyCostUsd: number;
    weightedScore: number;
  };
  rankedQualifiedOptions: Array<{
    optionId: string;
    regionCode: string;
    regionNameEn: string;
    regionNameAr: string;
    provider: string;
    monthlyCostUsd: number;
    regionalMeasurementStatus: string;
    weightedScore: number;
  }>;
}

export interface PipelineLatencySnapshot {
  pipelineArchitecture: string;
  councilDeadlineMs: number;
  defaultSignalTtlSeconds: number;
  counters: {
    parallelProviderDeadlineTimeouts: number;
    costAwareCloudInferenceSkips: number;
    staleOrExpiredSignalBlocks: number;
  };
  stages: Record<
    string,
    {
      samples: number;
      lastMs: number;
      meanMs: number;
      p50Ms: number;
      p95Ms: number;
      p99Ms: number;
      maxMs: number;
    }
  >;
}

export interface WalkForwardEvaluation {
  symbol: string;
  timeframe: string;
  inSampleBars: number;
  outOfSampleBars: number;
  outOfSampleComparison: {
    sequentialBaseline: {
      netReturnPct: number;
      netPnlAfterAllCostsUsd: number;
      sharpeRatio: number;
      maxDrawdownPct: number;
      costBreakdownUsd: { totalFrictionUsd: number };
    };
    lowLatencyCostAwareOptimized: {
      netReturnPct: number;
      netPnlAfterAllCostsUsd: number;
      sharpeRatio: number;
      maxDrawdownPct: number;
      costBreakdownUsd: { totalFrictionUsd: number };
    };
    improvements: {
      netPnlDeltaUsd: number;
      totalFrictionSavedUsd: number;
      drawdownReductionPct: number;
      sharpeDelta: number;
    };
  };
}

export interface AgentMeetingResult {
  meetingId: string;
  topicAr: string;
  topicEn: string;
  symbol: string;
  timestamp: string;
  signalExpiresAt?: string | null;
  freshnessTier?: string;
  routingDecision?: string;
  latencyBreakdownMs?: Record<string, number>;
  agentResponses: AgentDeliberationItem[];
  consensus: {
    agreementScorePct: number;
    agreementsAr: string[];
    agreementsEn: string[];
    disagreementsAr: string[];
    disagreementsEn: string[];
  };
  evidenceAndUncertainty: {
    uncertaintyScorePct: number;
    evidenceAr: string[];
    evidenceEn: string[];
    uncertaintiesAr: string[];
    uncertaintiesEn: string[];
  };
  estimatedCosts: EstimatedTradingCosts;
  riskAssessment: RiskAssessment;
  finalRecommendation: {
    stance: AgentStance;
    confidence: number;
    headlineAr: string;
    headlineEn: string;
    actionableSummaryAr: string;
    actionableSummaryEn: string;
    suggestedQuantity: number;
  };
}

export interface UiCommandAction {
  type:
    | 'SWITCH_THEME'
    | 'SET_LOW_POWER'
    | 'SET_HIGH_CONTRAST'
    | 'SET_MOTION_DISABLED'
    | 'SELECT_SYMBOL'
    | 'NAVIGATE_VIEW';
  payload: Record<string, string | boolean | number>;
}

export interface ChatMessageRecord {
  id: string;
  role: 'user' | 'assistant' | 'system';
  senderNameAr: string;
  senderNameEn: string;
  agentId?: string;
  source: CommandSource;
  language: Language;
  contentAr: string;
  contentEn: string;
  createdAt: string;
  uiAction?: UiCommandAction | null;
  tradeProposalEvaluation?: TradeProposalEvaluation | null;
  meetingId?: string | null;
}

export interface AiCommandResponse {
  userMessage: ChatMessageRecord;
  assistantMessage: ChatMessageRecord;
  uiAction?: UiCommandAction | null;
  tradeProposalEvaluation?: TradeProposalEvaluation | null;
  meeting?: AgentMeetingResult | null;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  actor: string;
  source: string;
  action: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  detailsAr: string;
  detailsEn: string;
}

export type ActiveScreen = 'terminal' | 'quantum' | 'binance-live' | 'portfolio' | 'governance' | 'themes';

export interface WealthArchitectOverview {
  generatedAt: string;
  currency: 'SAR';
  fxPegSarPerUsd: number;
  salaryAndCashFlow: {
    monthlySalarySar: number;
    paydayDayOfMonth: number;
    currentSalaryCycleId: string;
    nextPaydayDate: string;
    daysUntilNextPayday: number;
    plannedTotalAllocatedSar: number;
    unallocatedSalarySar: number;
    balancedToExactSalary: boolean;
    reconciledCycleTotalOutflowSar: number;
    reconciledCycleSurplusOrDeficitSar: number;
    importedStatementCountInCycle: number;
    cardPurchaseMemoExcludedFromDoubleCountSar: number;
    antiDoubleCountingPolicy: string;
    buckets: Array<{
      category: string;
      labelEn: string;
      labelAr: string;
      plannedSar: number;
      shareOfSalaryPct: number;
      importedActualSar: number;
      effectiveReconciledOutflowSar: number;
      remainingPlannedAllowanceSar: number;
      budgetOverrunSar: number;
    }>;
  };
  debtPlanner: {
    totalApproximateCardBalanceSar: number;
    totalReportedDueInclArrearsSar: number;
    monthlyRepaymentBudgetSar: number;
    allocatedAcrossCardsSar: number;
    budgetFullyAssigned: boolean;
    cards: Array<{
      cardId: string;
      issuerNameEn: string;
      issuerNameAr: string;
      approximateBalanceSar: number;
      reportedAmountDueInclArrearsSar: number;
      provisionalMonthlyAllocationSar: number;
      excessAboveReportedDueSar: number;
      estimatedAnnualAprPct: number;
      paymentDueDay: number;
      verifications: {
        currentDuesVerified: boolean;
        delinquencyVerified: boolean;
        financingChargesVerified: boolean;
        paymentDateVerified: boolean;
      };
      notesEn: string;
      notesAr: string;
    }>;
    payoffProjection: {
      estimatedMonthsToDebtFree: number | null;
      estimatedTotalFinancingCostSar: number | null;
      weightedEstimatedCardAprPct: number;
      postPayoffFreedMonthlyCashflowSar: number;
    };
    debtVsInvestmentTradeOff: {
      policy: string;
      debtEliminationIsBlanketPrerequisite: boolean;
      weightedCardFinancingCostAprPct: number;
      guaranteedEffectiveReturnOfDebtPaydownPct: number;
      illustrativeDiversifiedInvestmentReturnBandPct: string;
      tradeOffExplanationEn: string;
      tradeOffExplanationAr: string;
    };
  };
  employmentBenefits: {
    statusLabel: string;
    accountingTreatment: string;
    countedAsAvailableLiquidCash: boolean;
    countedInLiquidEmergencyReserve: boolean;
    usableForTradingOrImmediateDebtPayments: boolean;
    legalEntitlementGuaranteedWithoutReview: boolean;
    contractSummary: {
      jurisdiction: string;
      commencementDate: string;
      illustrativeOrTargetEndDate: string;
      exactExpiryDateVerified: boolean;
      contractType: string;
      autoRenews: boolean;
      nonRenewalNoticeDays: number;
      expectedDepartureMethod: string;
      eligibleFinalMonthlyWageSar: number;
      dailyEligibleWageSar: number;
      annualLeaveDaysPerYear: number;
      annualLeaveTakenDays: number;
      accruedUnusedLeaveDays: number;
      serviceDuration: {
        completedFullYears: number;
        remainderDays: number;
        totalCalendarDays: number;
        serviceYearsExact: number;
      };
    };
    primaryExpectedScenario: {
      scenarioId: string;
      titleEn: string;
      titleAr: string;
      legalBasis: string;
      classifiedAsMidTermResignation: boolean;
      eosbAwardSar: number;
      unusedLeaveCompensationSar: number;
      combinedEstimatedBenefitsSar: number;
      settlementDeadlineRule: string;
      statusLabel: string;
      legalCaveatEn: string;
      legalCaveatAr: string;
    };
    scenarios: {
      fixedTermExpiryNonRenewal: {
        scenarioId: string;
        titleEn: string;
        titleAr: string;
        legalBasis: string;
        classifiedAsMidTermResignation: boolean;
        eosbAwardSar: number;
        unusedLeaveCompensationSar: number;
        combinedEstimatedBenefitsSar: number;
        statusLabel: string;
      };
      ordinaryResignation: {
        scenarioId: string;
        titleEn: string;
        titleAr: string;
        legalBasis: string;
        classifiedAsMidTermResignation: boolean;
        eosbMultiplier: number;
        eosbAwardSar: number;
        unusedLeaveCompensationSar: number;
        combinedEstimatedBenefitsSar: number;
        statusLabel: string;
      };
      employerInitiatedTermination: {
        scenarioId: string;
        titleEn: string;
        titleAr: string;
        legalBasis: string;
        eosbAwardSar: number;
        unusedLeaveCompensationSar: number;
        combinedEstimatedBenefitsSar: number;
        statusLabel: string;
      };
      otherStatutoryScenarios: {
        forceMajeureOrEmployerBreach: {
          scenarioId: string;
          titleEn: string;
          eosbAwardSar: number;
          unusedLeaveCompensationSar: number;
          combinedEstimatedBenefitsSar: number;
          statusLabel: string;
        };
        dismissalForCauseArt80: {
          scenarioId: string;
          titleEn: string;
          eosbAwardSar: number;
          unusedLeaveCompensationSar: number;
          combinedEstimatedBenefitsSar: number;
          statusLabel: string;
        };
      };
    };
    verificationChecklist: Array<{
      itemId: string;
      labelEn: string;
      labelAr: string;
      verified: boolean;
    }>;
  };
  contractRenewalIntelligence: {
    contractExpiryDate: string;
    exactExpiryDateVerified: boolean;
    requiredAdvanceNoticeDays: number;
    finalNoticeDeadlineDate: string;
    daysUntilFinalNoticeDeadline: number;
    daysUntilContractExpiry: number;
    deadlineState: string;
    noticeCalculationRuleNoteEn: string;
    noticeCalculationRuleNoteAr: string;
    autoSendNonRenewalNotice: boolean;
    ownerApprovalPolicy: string;
    reminders: Array<{
      milestoneCode: string;
      daysBeforeExpiry: number;
      reminderDate: string;
      daysFromToday: number;
      status: string;
      messageEn: string;
      messageAr: string;
    }>;
    evidenceVault: Array<{
      evidenceId: string;
      documentType: string;
      title: string;
      documentSha256: string;
      deliveryChannel: string;
      verifiedByOwner: boolean;
      notes: string;
      recordedAt: string;
    }>;
  };
  investmentCommandCenter: {
    ledgerSummary: {
      entryCount: number;
      cumulativeAllocatedCapitalSar: number;
      cumulativeAllocatedCapitalUsdEquiv: number;
      entries: Array<{
        entryId: string;
        salaryCycleId: string;
        contributionDate: string;
        amountSar: number;
        amountUsdEquiv: number;
        diversifiedEtfSukukSar: number;
        saudiEquitiesTadawulSar: number;
        cryptoSpotPaperSar: number;
        executionMode: string;
        liquidityGuardStatus: string;
        notes: string;
        createdAt: string;
      }>;
    };
    opportunityAndRiskAnalysis: {
      monthlyAllocationSar: number;
      monthlyAllocationUsdEquiv: number;
      annualizedContributionRunRateSar: number;
      executionSafeguards: {
        binanceTradingMode: string;
        liveTradingAuthorized: boolean;
        realMoneyOrdersPlaced: boolean;
        externalBrokerageAccountsOpened: boolean;
        returnsGuaranteed: boolean;
        reliesOnSpeculativeProfitsForMandatoryPayments: boolean;
      };
      sleeves: Array<{
        sleeveId: string;
        nameEn: string;
        nameAr: string;
        targetWeightPct: number;
        monthlyAllocationSar: number;
        illustrativeAnnualReturnBandPct: string;
        annualizedVolatilityPct: number;
        estimatedTransactionFeeBps: number;
        liquidityProfile: string;
        severeStressDrawdownPct: number;
        roleInPortfolioEn: string;
        roleInPortfolioAr: string;
      }>;
      downsideScenarios: Array<{
        scenarioId: string;
        labelEn: string;
        labelAr: string;
        year1ContributedSar: number;
        stressedPortfolioValueSar: number;
        unrealizedDrawdownSar: number;
        mandatoryDebtImpact: string;
      }>;
    };
  };
  balanceSheetAndForecast: {
    liquidAssetsAvailableNow: {
      liquidCashReserveSar: number;
      availableCurrentCycleCashSar: number;
      cumulativeInvestedCapitalLedgerSar: number;
      includesUnreceivedEmploymentBenefits: boolean;
    };
    contingentFutureReceivablesSegregated: {
      statusLabel: string;
      classification: string;
      fixedTermNonRenewalCombinedEstimateSar: number;
      ordinaryResignationCombinedEstimateSar: number;
      usableForImmediateDebtOrTrading: boolean;
    };
    thirtySixMonthIllustrativeForecast: {
      horizonMonths: number;
      projectedLiquidCashSavingsSar: number;
      projectedInvestedPrincipalBaselineSar: number;
      projectedInvestedPrincipalWithPostDebtSnowballSar: number;
      contingentEmploymentSettlementSeparateSar: number;
      assumesSpeculativeMarketGains: boolean;
    };
  };
  wealthGuardian: {
    guardianStatus: string;
    debtEliminationRequiredBeforeInvesting: boolean;
    availableImmediateCycleCashSar: number;
    minimumMandatoryLivingAndOverdueFloorSar: number;
    scheduledCardRepaymentSar: number;
    recommendedCycleInvestmentSar: number;
      summaryEn: string;
      summaryAr: string;
    };
  binancePersonalCfoBridge?: BinancePersonalCfoBridge;
  financialAlerts: Array<{
    alertId: string;
    severity: string;
    category: string;
    titleEn: string;
    titleAr: string;
    detailEn: string;
    detailAr: string;
  }>;
}

export interface BinancePersonalCfoBridge {
  primaryFocus: string;
  connectionStatus: string;
  plannedMonthlyCryptoAllocationSar: number;
  plannedMonthlyCryptoAllocationUsd: number;
  activeSalaryCycleId: string;
  cycleReconciliation: {
    importedBankStatementInvestmentSar: number;
    cfoLedgerCycleAllocationSar: number;
    syncedBinanceCycleDepositsSar: number;
    syncedBinanceCycleSpotPurchasesSar: number;
    deduplicatedActualDeploymentSar: number;
    effectiveReconciledBudgetOutflowSar: number;
    remainingPlannedMonthlyBudgetSar: number;
    budgetOverrunSar: number;
    reconciledWithoutDoubleCount: boolean;
  };
  capitalVsPerformanceSeparation: {
    cumulativeContributedCapitalSar: number;
    realizedPnlSar: number;
    unrealizedPnlSar: number;
    cumulativeTradingFeesSar: number;
    netMarketPnlAfterFeesSar: number;
    totalActualBinanceEquitySar: number;
  };
  cashVsCryptoExposure: {
    availableBinanceQuoteCashSar: number;
    investedBinanceCryptoExposureSar: number;
    cryptoMarketExposurePct: number;
  };
  actualVsPaperStrategyComparison: {
    actualAccountStatus: string;
    actualNetReturnAfterFeesPct: number | null;
    paperSimulatedPortfolioEquityUsd: number;
    paperStrategyNetReturnPct: number;
    segregatedBalancesAndReturns: boolean;
    comparisonNoteEn: string;
  };
  governanceInvariants: {
    assumesGuaranteedReturns: boolean;
    treatsProjectedEmploymentBenefitsAsCash: boolean;
    tradingMode: 'PAPER';
    liveAuthorized: false;
  };
}

export interface PersonalBinanceBalanceItem {
  asset: string;
  freeQty: number;
  lockedQty: number;
  totalQty: number;
  priceUsd: number;
  valueUsd: number;
  valueSar: number;
  allocationWeightPct: number;
  avgCostBasisUsd: number;
  totalCostBasisUsd: number;
  unrealizedPnlUsd: number;
  unrealizedPnlPct: number;
  realizedPnlUsd: number;
  cumulativeFeesUsd: number;
  reconciliationStatus: string;
  reconciledDeltaQty: number;
  isQuoteCash: boolean;
  updatedAt: string;
}

export interface PersonalBinanceSlotInfo {
  configured: boolean;
  credentialId?: string;
  keyLabel?: string;
  authAlgorithm?: 'ED25519' | 'RSA_SHA256' | 'HMAC_SHA256';
  environment?: 'MAINNET' | 'SPOT_TESTNET' | 'LOCAL_MOCK';
  baseUrl?: string;
  apiKeyMasked?: string;
  trustedIps?: string[];
  trackedSymbols?: string[];
  status: string;
  verificationReason?: string;
  permissionAudit?: {
    safe?: boolean;
    verificationStatus?: string;
    violations?: string[];
    ipRestrictEnabledOnBinance?: boolean;
    scopes?: {
      enableReading: boolean;
      enableSpotTrading: boolean;
      enableWithdrawals: boolean;
      enableMargin: boolean;
      enableFutures: boolean;
      enableInternalOrUniversalTransfer: boolean;
    };
  };
  rotatedCount?: number;
  health?: {
    usedWeight1m: number;
    lastLatencyMs: number;
    clockSkewMs: number;
    consecutiveFailures: number;
    rateLimitCooldownActive: boolean;
  };
  lastVerifiedAt?: string | null;
  lastSyncedAt?: string | null;
}

export interface PersonalBinanceOverview {
  generatedAt: string;
  dashboardLabel: 'LIVE ACCOUNT MONITORING';
  segregatedFromPaperTrading: boolean;
  tradingMode: 'PAPER';
  liveAuthorized: false;
  executionLockedToPaper: true;
  connectionStatus: string;
  supportedAuthMechanisms: Array<{
    algorithm: 'ED25519' | 'RSA_SHA256' | 'HMAC_SHA256';
    recommended: boolean;
    label: string;
    officialDocs: string;
  }>;
  biometricArchitecture: {
    binanceAppFaceIdExplanationEn: string;
    trilunairPasskeyExplanationEn: string;
    enrolledPasskeyCount: number;
    biometricStepUpRequiredForCredentialChanges: boolean;
    biometricTemplatesStoredOnServer: false;
  };
  credentialSlots: {
    READ_ONLY_MONITORING: PersonalBinanceSlotInfo;
    FUTURE_SPOT_EXECUTION: PersonalBinanceSlotInfo;
  };
  portfolioSummary: {
    accountingMethod: string;
    totalEquityUsd: number;
    totalEquitySar: number;
    availableQuoteCashUsd: number;
    availableQuoteCashSar: number;
    investedCryptoCapitalUsd: number;
    investedCryptoCapitalSar: number;
    cryptoExposurePct: number;
    netContributedCapitalUsd: number;
    netContributedCapitalSar: number;
    realizedPnlUsd: number;
    realizedPnlSar: number;
    unrealizedPnlUsd: number;
    unrealizedPnlSar: number;
    netPnlAfterFeesUsd: number;
    netPnlAfterFeesSar: number;
    cumulativeFeesUsd: number;
    cumulativeFeesSar: number;
    portfolioDrawdownPct: number;
    reconciliationStatus: string;
    unreconciledAssetsCount: number;
  };
  monthlyInvestmentBudgetTracking: {
    plannedMonthlyAllocationSar: number;
    plannedMonthlyAllocationUsd: number;
    currentMonth: string;
    currentMonthVerifiedDepositsSar: number;
    currentMonthSpotPurchasesSar: number;
    remainingMonthlyBudgetSar: number;
  };
  balances: PersonalBinanceBalanceItem[];
  recentOrders: Array<{
    orderUid: string;
    symbol: string;
    orderId: string;
    side: string;
    type: string;
    status: string;
    price: number;
    origQty: number;
    executedQty: number;
    cummulativeQuoteQty: number;
    orderTimeIso: string;
  }>;
  recentTrades: Array<{
    tradeUid: string;
    symbol: string;
    tradeId: string;
    orderId: string;
    side: string;
    price: number;
    qty: number;
    quoteQty: number;
    commission: number;
    commissionAsset: string;
    commissionUsd: number;
    tradeTimeIso: string;
  }>;
  recentCashflows: Array<{
    cashflowId: string;
    direction: string;
    coin: string;
    amount: number;
    amountUsd: number;
    amountSar: number;
    transactionFee: number;
    statusLabel: string;
    network: string;
    occurredAtIso: string;
  }>;
  riskAlerts: Array<{
    code: string;
    severity: string;
    messageEn: string;
    messageAr: string;
  }>;
}

export interface LiveSpotReadiness {
  workflowName: 'LIVE_SPOT';
  tradingMode: 'PAPER';
  liveAuthorized: false;
  executionLockedToPaper: true;
  realOrdersPermitted: false;
  passedGatesCount: number;
  totalGatesCount: number;
  gates: Array<{
    gateNumber: number;
    gateId: string;
    titleEn: string;
    titleAr: string;
    passed: boolean;
    detailEn: string;
  }>;
  allowedSpotCapabilities: {
    sides: string[];
    orderTypes: string[];
    supportsOrderCancellation: boolean;
    supportsOrderStatusReconciliation: boolean;
  };
  prohibitedOperations: string[];
  ownerPolicy: {
    ownerConfigured: boolean;
    jurisdictionEligibilityConfirmed: boolean;
    jurisdictionCountryCode: string;
    maxSingleOrderSar: number;
    maxSingleOrderUsd: number;
    maxDailySpotSar: number;
    maxMonthlySpotSar: number;
    maxMonthlySpotUsd: number;
    maxSingleAssetExposurePct: number;
    requireBiometricPerOrder: boolean;
    allowedSpotSymbols: string[];
    updatedAt: string;
  };
}


