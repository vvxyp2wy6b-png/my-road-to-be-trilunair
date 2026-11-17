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
  | 'arctic-platinum';

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

export interface SystemStatus {
  appName: string;
  version: string;
  tradingMode: TradingMode;
  killSwitchActive: boolean;
  liveAuthorized: boolean;
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
}

export interface TradeProposalEvaluation {
  proposalId: string;
  status: 'APPROVED_FOR_AUTH' | 'REJECTED_BY_RISK';
  proposal: TradeProposalInput & { referencePrice: number; createdAt: string };
  estimatedCosts: EstimatedTradingCosts;
  riskAssessment: RiskAssessment;
  tradingMode: TradingMode;
  requiresLivePin: boolean;
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

export interface AgentDeliberationItem {
  agentId: string;
  nameAr: string;
  nameEn: string;
  roleAr: string;
  roleEn: string;
  status: 'READY' | 'AGREE' | 'DISSENT' | 'CAUTION';
  stance: AgentStance;
  confidence: number;
  summaryAr: string;
  summaryEn: string;
  keyMetricLabelAr: string;
  keyMetricLabelEn: string;
  keyMetricValue: string;
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
