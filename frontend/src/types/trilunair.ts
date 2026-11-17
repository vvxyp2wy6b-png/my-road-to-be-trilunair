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
}

export interface AgentMeetingResult {
  meetingId: string;
  topicAr: string;
  topicEn: string;
  symbol: string;
  timestamp: string;
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

export type ActiveScreen = 'terminal' | 'portfolio' | 'governance' | 'themes';
