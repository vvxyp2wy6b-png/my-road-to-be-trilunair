/**
 * تعريفات الأنواع المتقدمة لمنظومة القيادة الكمية (Quantum AI Trading Command Center)
 * تغطي الطبقات المعمارية الثماني، محول Binance Spot، تأهيل الوكلاء رباعي المستويات،
 * قاعدة المعرفة المؤرشفة بالإصدارات، المهارات والموصلات الخارجية، والجدوى الاقتصادية.
 */

export type AuthorizationPolicyMode = 'PAPER' | 'HUMAN_APPROVAL' | 'AUTONOMOUS';

export type InstrumentClassification = 'TRADABLE_SPOT' | 'REFERENCE_ONLY' | 'UNAVAILABLE';

export type QualificationLevel =
  | 'TRAINEE'
  | 'ANALYST'
  | 'EXPERIMENTALLY_QUALIFIED'
  | 'PRODUCTION_QUALIFIED';

export type LlmProviderId =
  | 'openai'
  | 'gemini'
  | 'anthropic'
  | 'xai'
  | 'local-quant-engine';

export type AgentVisualState =
  | 'THINKING'   // Cyan/Blue
  | 'AGREE'      // Green
  | 'DISAGREE'   // Orange/Red
  | 'SPEAKING'   // Gold
  | 'INACTIVE';  // Gray

export type AnalysisHorizon = 'HOURS' | 'DAYS' | 'WEEKS' | 'MONTHS';

export interface LlmProviderStatus {
  providerId: LlmProviderId;
  displayName: string;
  available: boolean;
  configuredKeyEnv: string;
  availableModels: string[];
  costPer1kTokensUsd: number;
  statusMessageAr: string;
  statusMessageEn: string;
}

export interface ManagedAgentConfig {
  agentId: string;
  nameAr: string;
  nameEn: string;
  roleAr: string;
  roleEn: string;
  enabled: boolean;
  visualState: AgentVisualState;
  assignedProvider: LlmProviderId;
  assignedModel: string;
  providerAvailable: boolean;
  decisionWeight: number;
  qualificationLevel: QualificationLevel;
  qualificationScorePct: number;
  requalificationRequired: boolean;
  lastQualificationNoteAr: string;
  lastQualificationNoteEn: string;
  assignedSkills: string[];
  coreInstructions: string;
  operationalPermissions: {
    canAnalyze: boolean;
    canProposeTrades: boolean;
    canParticipateAutonomous: boolean;
  };
  metrics: {
    totalCalls: number;
    totalTokens: number;
    attributableAiCostUsd: number;
    historicalReliabilityPct: number;
  };
}

export interface QualificationExamResult {
  agentId: string;
  previousLevel: QualificationLevel;
  newLevel: QualificationLevel;
  passed: boolean;
  scorePct: number;
  checksRun: Array<{
    gate: string;
    passed: boolean;
    detailAr: string;
    detailEn: string;
  }>;
  disclaimerAr: string;
  disclaimerEn: string;
}

export interface KnowledgeArticle {
  id: string;
  slug: string;
  category: string;
  titleAr: string;
  titleEn: string;
  contentAr: string;
  contentEn: string;
  version: number;
  updatedAt: string;
}

export interface AgentSkillDescriptor {
  skillId: string;
  nameAr: string;
  nameEn: string;
  descriptionAr: string;
  descriptionEn: string;
  enabled: boolean;
  avgComputeCostUsd: number;
}

export interface ExternalConnectorDescriptor {
  connectorId: string;
  nameAr: string;
  nameEn: string;
  provider: string;
  requiredCredentials: string[];
  credentialsConfigured: boolean;
  capabilities: string[];
  rateLimitPerMin: number;
  dataFreshnessSeconds: number;
  healthStatus: 'HEALTHY' | 'DEGRADED' | 'UNCONFIGURED' | 'OFFLINE';
  operatingCostPer1kCallsUsd: number;
  enabled: boolean;
  treatsInputAsUntrusted: boolean;
}

export interface BinanceSymbolFilterSpec {
  canonicalSymbol: string;
  displayAlias: string;
  baseAsset: string;
  quoteAsset: string;
  classification: InstrumentClassification;
  tickSize: number;
  stepSize: number;
  minQty: number;
  maxQty: number;
  minNotional: number;
  lastUpdatedTs: number;
  isStale: boolean;
}

export interface RiskPolicyConfig {
  maxRiskPerTradePct: number;      // Default 0.5%
  maxExposurePerAssetPct: number;  // Default 25.0%
  dailyLossLimitPct: number;       // Default 2.0%
  weeklyLossLimitPct: number;      // Default 5.0%
  maxDrawdownLimitPct: number;     // Default 10.0%
  prohibitLeverage: true;
  prohibitMargin: true;
  prohibitFutures: true;
  prohibitBorrowing: true;
  prohibitWithdrawals: true;
}

export interface EconomicViabilityReport {
  notionalUsd: number;
  exchangeCommissionUsd: number;
  spreadCostUsd: number;
  expectedSlippageUsd: number;
  attributableAiCostUsd: number;
  totalExpectedCostUsd: number;
  expectedRewardUsd: number;
  rewardToCostRatio: number;
  netExpectedValueUsd: number;
  economicallyViable: boolean;
  notesAr: string;
  notesEn: string;
}

export interface GoalModeConfig {
  startingEquityUsd: number;
  targetEquityUsd: number;
  horizonMonths: number;
  dailyGoalPct: number;
  weeklyGoalPct: number;
  monthlyGoalPct: number;
}

export interface CostAccountingSummary {
  totalTradingCommissionsUsd: number;
  totalSpreadAndSlippageUsd: number;
  totalTradingExecutionCostsUsd: number;
  totalAiInferenceCostsUsd: number;
  totalConnectorOperatingCostsUsd: number;
  netRealizedPnlAfterAllCostsUsd: number;
}

export interface ExchangeAdapterStatus {
  exchange: 'BINANCE_SPOT';
  connectionMode: 'LIVE_AUTHENTICATED' | 'TESTNET_AUTHENTICATED' | 'PAPER_SIMULATION';
  credentialsConfigured: boolean;
  restReachable: boolean;
  wsStreamActive: boolean;
  accountStateUncertain: boolean;
  staleMarketDataDetected: boolean;
  lastReconciledAt: string;
  authorizationPolicy: AuthorizationPolicyMode;
  agentsPaused: boolean;
  instruments: BinanceSymbolFilterSpec[];
}

export interface QuantumSystemOverview {
  providers: LlmProviderStatus[];
  agents: ManagedAgentConfig[];
  skills: AgentSkillDescriptor[];
  connectors: ExternalConnectorDescriptor[];
  riskPolicy: RiskPolicyConfig;
  goalConfig: GoalModeConfig;
  accounting: CostAccountingSummary;
  exchangeStatus: ExchangeAdapterStatus;
}
