"""
نماذج البيانات المهيكلة (Pydantic Schemas) المتوافقة تماماً مع عقد الواجهة الأمامية (trilunair.ts).
تضمن هذه الوحدة تطابق جميع حقول JSON بصيغة camelCase بنسبة 100% بين الخادم والواجهة الهولوغرامية.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# الأنواع الأساسية المشتركة
Language = Literal["ar", "en"]
TradingMode = Literal["PAPER", "LIVE"]
CommandSource = Literal["VOICE", "TEXT", "TERMINAL"]
OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT"]
AgentStance = Literal["BUY", "SELL", "HOLD", "CAUTION"]
AssetCategory = Literal["CRYPTO", "EQUITY", "COMMODITY"]
RiskLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
AuditSeverity = Literal["INFO", "WARNING", "CRITICAL"]


# ==============================================================================
# 1. نماذج محرك السمات الهولوغرامية (Dynamic Theme Engine)
# ==============================================================================


class ThemeTokens(BaseModel):
    """رموز الألوان الأساسية للسمة الهولوغرامية."""

    bgBase: str
    bgElevated: str
    bgSurface: str
    accentPrimary: str
    accentSecondary: str
    accentTertiary: str
    textPrimary: str
    textSecondary: str
    textMuted: str
    borderHolo: str
    success: str
    danger: str
    warning: str


class ThemeModifiers(BaseModel):
    """معاملات التوهج والضبابية والحركة والتباين والطاقة."""

    glowIntensity: float = Field(default=58, ge=0, le=100)
    blurRadius: float = Field(default=16, ge=0, le=32)
    panelOpacity: float = Field(default=78, ge=40, le=98)
    animationIntensity: float = Field(default=85, ge=0, le=100)
    motionDisabled: bool = False
    highContrast: bool = False
    lowPowerMode: bool = False


class ThemeDefinition(BaseModel):
    """تعريف سمة أساسية أو مخصصة قابلة للحفظ والتصدير والاستيراد."""

    id: str
    nameAr: str
    nameEn: str
    descriptionAr: str = ""
    descriptionEn: str = ""
    isCustom: bool | None = None
    tokens: ThemeTokens
    defaultModifiers: dict[str, float | bool] | None = None


class ActiveThemeState(BaseModel):
    """الحالة النشطة للسمة وتخصيصات المسؤول."""

    activeThemeId: str
    customOverrides: dict[str, str] = Field(default_factory=dict)
    modifiers: ThemeModifiers


class ThemesPayload(BaseModel):
    """حمولة استرجاع كافة السمات الأساسية والمخصصة والحالة النشطة."""

    presets: list[ThemeDefinition]
    customThemes: list[ThemeDefinition]
    activeState: ActiveThemeState


# ==============================================================================
# 2. نماذج الحوكمة والأمان المالي وحالة النظام (System & Safety Gateway)
# ==============================================================================


class SafetyChecks(BaseModel):
    """الفحوصات الخمسة الإلزامية لسلامة النظام المالي."""

    riskEngineVerified: bool
    maxDrawdownConfigured: bool
    killSwitchReady: bool
    positionLimitsActive: bool
    auditTrailHealthy: bool


class SystemProviders(BaseModel):
    """مزودو خدمات الذكاء الاصطناعي والصوت النشطون حالياً."""

    llmProvider: str
    sttProvider: str
    ttsProvider: str


class RiskPolicySummary(BaseModel):
    """الحدود الخمسة المعتمدة لسياسة المخاطر الحتمية الموحدة عبر النظام بالكامل."""

    maxRiskPerTradePct: float = 0.5
    maxExposurePerAssetPct: float = 25.0
    dailyLossLimitPct: float = 2.0
    weeklyLossLimitPct: float = 5.0
    maxDrawdownLimitPct: float = 10.0
    prohibitLeverage: bool = True
    prohibitMargin: bool = True
    prohibitFutures: bool = True
    prohibitWithdrawals: bool = True


class SystemStatus(BaseModel):
    """الحالة العامة للنظام ووضع التداول الحالي (مقفل على الورقي PAPER في الإصدار v1.1.0-cloud-paper)."""

    appName: str
    version: str
    tradingMode: TradingMode
    killSwitchActive: bool
    liveAuthorized: bool
    executionLockedToPaper: bool = True
    marketDataMode: str = "SIMULATED_MARKET_DATA_PAPER_EXECUTION"
    riskPolicy: RiskPolicySummary = Field(default_factory=RiskPolicySummary)
    safetyChecks: SafetyChecks
    providers: SystemProviders


class TradingModeRequest(BaseModel):
    """طلب تبديل وضع التداول عبر بوابة تصاريح المسؤول."""

    targetMode: TradingMode
    adminPin: str = ""
    confirmationPhrase: str = ""
    acknowledgeRealCapitalRisk: bool = False


class KillSwitchRequest(BaseModel):
    """طلب تفعيل أو إلغاء مفتاح الإيقاف الطارئ."""

    active: bool
    reason: str = ""
    adminPin: str = ""


class AuditLogEntry(BaseModel):
    """سجل تدقيق أمني غير قابلللتلاعب لتوثيق القرارات والأوامر."""

    id: str
    timestamp: str
    actor: str
    source: str
    action: str
    severity: AuditSeverity
    detailsAr: str
    detailsEn: str


# ==============================================================================
# 3. نماذج الأسواق والمحفظة والأوامر وتقييم المخاطر (Market, Portfolio & Risk)
# ==============================================================================


class MarketAsset(BaseModel):
    """بيانات أصل مالي متداول في الأسواق الحية."""

    symbol: str
    nameAr: str
    nameEn: str
    category: AssetCategory
    price: float
    change24hPct: float
    high24h: float
    low24h: float
    volume24hUsd: float
    volatilityPct: float
    spreadBps: float
    dataSource: str = "SIMULATED"


class CandlePoint(BaseModel):
    """نقطة شمعة يابانية واحدة (OHLCV)."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class OrderbookLevel(BaseModel):
    """مستوى سعري واحد في دفتر الأوامر (عرض أو طلب)."""

    price: float
    size: float
    total: float


class MarketCandlesResponse(BaseModel):
    """استجابة الشموع اليابانية ومستويات الدعم والمقاومة وعمق السوق."""

    symbol: str
    timeframe: str
    candles: list[CandlePoint]
    supportLevel: float
    resistanceLevel: float
    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    dataSource: str = "SIMULATED"
    lastUpdateId: int | None = None


class PositionItem(BaseModel):
    """مركز مالي مفتوح في المحفظة مع حسابات الربح والخسارة غير المحققة."""

    symbol: str
    nameAr: str
    nameEn: str
    quantity: float
    avgEntryPrice: float
    currentPrice: float
    marketValueUsd: float
    unrealizedPnlUsd: float
    unrealizedPnlPct: float
    weightPct: float


class OrderRecord(BaseModel):
    """سجل صفقة منفذة أو ملغاة أو مرفوضة."""

    orderId: str
    proposalId: str
    symbol: str
    side: OrderSide
    orderType: OrderType
    quantity: float
    executedPrice: float
    notionalUsd: float
    totalFeeUsd: float
    tradingMode: TradingMode
    isSimulatedFill: bool = True
    stopLoss: float | None = None
    takeProfit: float | None = None
    source: CommandSource
    status: Literal["FILLED", "REJECTED", "CANCELLED"]
    createdAt: str
    clientOrderId: str | None = None


class PortfolioSnapshot(BaseModel):
    """لقطة شاملة للمحفظة المالية والتقدم نحو هدف التريليون دولار."""

    tradingMode: TradingMode
    cashBalance: float
    positionsValue: float
    totalEquity: float
    initialEquity: float
    dailyPnl: float
    dailyPnlPct: float
    weeklyLossPct: float = 0.0
    trilunairTargetUsd: float
    trilunairProgressPct: float
    currentDrawdownPct: float
    maxAllowedDrawdownPct: float
    riskPolicy: RiskPolicySummary = Field(default_factory=RiskPolicySummary)
    var95Usd: float
    positions: list[PositionItem]
    recentOrders: list[OrderRecord]


class EstimatedTradingCosts(BaseModel):
    """التكاليف التقديرية للصفقة شاملة السبريد والعمولة والانزلاق السعري."""

    notionalUsd: float
    spreadCostUsd: float
    commissionUsd: float
    slippageCostUsd: float
    totalEstimatedCostUsd: float
    costBps: float


class RiskCheckItem(BaseModel):
    """نتيجة بند فحص واحد ضمن محرك المخاطر الحتمي."""

    code: str
    passed: bool
    messageAr: str
    messageEn: str


class RiskAssessment(BaseModel):
    """التقييم الشامل للمخاطر الحتمية لمقترح صفقة."""

    passed: bool
    riskScore: int
    riskLevel: RiskLevel
    postTradeConcentrationPct: float
    varImpactUsd: float
    checks: list[RiskCheckItem]
    violations: list[str]


class TradeProposalInput(BaseModel):
    """مدخلات إنشاء مقترح صفقة مهيكل من الصوت أو النص أو شاشة التداول."""

    symbol: str
    side: OrderSide
    orderType: OrderType = "MARKET"
    quantity: float
    limitPrice: float | None = None
    stopLoss: float | None = None
    takeProfit: float | None = None
    source: CommandSource = "TERMINAL"
    rationale: str | None = ""
    clientOrderId: str | None = None
    ttlSeconds: int | None = None


class TradeProposalDetails(TradeProposalInput):
    """بيانات مقترح الصفقة مع السعر المرجعي وتاريخ الإنشاء وانتهاء الصلاحية."""

    referencePrice: float
    createdAt: str
    expiresAt: str | None = None


class TradeProposalEvaluation(BaseModel):
    """نتيجة تقييم مقترح الصفقة عبر المدقق ومحرك المخاطر دون تنفيذ تلقائي."""

    proposalId: str
    status: Literal["APPROVED_FOR_AUTH", "REJECTED_BY_RISK", "EXPIRED", "EXECUTED", "CANCELLED_BY_KILL_SWITCH"]
    proposal: TradeProposalDetails
    estimatedCosts: EstimatedTradingCosts
    riskAssessment: RiskAssessment
    tradingMode: TradingMode
    requiresLivePin: bool
    expiresAt: str | None = None


class OrderExecuteRequest(BaseModel):
    """طلب التنفيذ النهائي لصفقة معتمدة بعد تأكيد المستخدم الصريح."""

    proposalId: str
    confirmedByUser: bool
    adminPin: str | None = None
    source: CommandSource = "TERMINAL"
    clientOrderId: str | None = None


class OrderExecuteResponse(BaseModel):
    """نتيجة تنفيذ الصفقة مع تحديث لقطة المحفظة الفورية."""

    order: OrderRecord
    portfolio: PortfolioSnapshot


# ==============================================================================
# 4. نماذج مجلس الوكلاء والأوامر الصوتية والنصية (AI Council & Voice Command)
# ==============================================================================


class AgentProfile(BaseModel):
    """الملف التعريفي لوكيل متخصص ضمن المجلس التحليلي."""

    agentId: str
    nameAr: str
    nameEn: str
    roleAr: str
    roleEn: str
    specialtyAr: str
    specialtyEn: str
    status: Literal["ONLINE", "ANALYZING", "VOTING", "ALERT"]
    accentToken: str


class AgentDeliberationItem(BaseModel):
    """مداخلة وكيل متخصص واحد داخل قاعة اجتماع الوكلاء."""

    agentId: str
    nameAr: str
    nameEn: str
    roleAr: str
    roleEn: str
    status: Literal["READY", "AGREE", "DISSENT", "CAUTION"]
    stance: AgentStance
    confidence: int
    uncertaintyPct: int = 18
    summaryAr: str
    summaryEn: str
    keyMetricLabelAr: str
    keyMetricLabelEn: str
    keyMetricValue: str
    providerUsed: str = "local-quant-engine"
    modelUsed: str = "quant-deterministic-v1"
    executionStatus: Literal["LIVE", "SIMULATED", "CACHED", "UNAVAILABLE"] = "SIMULATED"
    respondedAt: str = ""
    latencyMs: float = 0.0
    isSimulated: bool = True


class MeetingConsensus(BaseModel):
    """ملخص التوافق ونقاط الاتفاق والاختلاف بين الوكلاء."""

    agreementScorePct: int
    agreementsAr: list[str]
    agreementsEn: list[str]
    disagreementsAr: list[str]
    disagreementsEn: list[str]


class MeetingEvidenceAndUncertainty(BaseModel):
    """الأدلة الكمية الداعمة وعوامل عدم اليقين المرصودة."""

    uncertaintyScorePct: int
    evidenceAr: list[str]
    evidenceEn: list[str]
    uncertaintiesAr: list[str]
    uncertaintiesEn: list[str]


class MeetingFinalRecommendation(BaseModel):
    """التوصية التنفيذية المجمعة الصادرة عن المجلس."""

    stance: AgentStance
    confidence: int
    headlineAr: str
    headlineEn: str
    actionableSummaryAr: str
    actionableSummaryEn: str
    suggestedQuantity: float


class AgentMeetingResult(BaseModel):
    """النتيجة المتكاملة لاجتماع الطاولة المستديرة لمجلس الوكلاء."""

    meetingId: str
    topicAr: str
    topicEn: str
    symbol: str
    timestamp: str
    signalExpiresAt: str | None = None
    freshnessTier: str = "ULTRA_FRESH"
    routingDecision: str = "PARALLEL_BOUNDED_DEADLINE"
    latencyBreakdownMs: dict[str, float] = Field(default_factory=dict)
    agentResponses: list[AgentDeliberationItem]
    consensus: MeetingConsensus
    evidenceAndUncertainty: MeetingEvidenceAndUncertainty
    estimatedCosts: EstimatedTradingCosts
    riskAssessment: RiskAssessment
    finalRecommendation: MeetingFinalRecommendation


class UiCommandAction(BaseModel):
    """إجراء واجهة مستخدم ناتج عن أمر صوتي أو نصي (تبديل سمة، تباين، تنقل)."""

    type: Literal[
        "SWITCH_THEME",
        "SET_LOW_POWER",
        "SET_HIGH_CONTRAST",
        "SET_MOTION_DISABLED",
        "SELECT_SYMBOL",
        "NAVIGATE_VIEW",
    ]
    payload: dict[str, str | bool | int | float]


class ChatMessageRecord(BaseModel):
    """سجل رسالة محادثة (مستخدم أو وكيل ذكي) ثنائية اللغة."""

    id: str
    role: Literal["user", "assistant", "system"]
    senderNameAr: str
    senderNameEn: str
    agentId: str | None = None
    source: CommandSource
    language: Language
    contentAr: str
    contentEn: str
    createdAt: str
    uiAction: UiCommandAction | None = None
    tradeProposalEvaluation: TradeProposalEvaluation | None = None
    meetingId: str | None = None


class AiCommandRequest(BaseModel):
    """طلب معالجة أمر صوتي أو نصي موجه للوكيل الفردي أو فريق الوكلاء."""

    message: str
    language: Language = "ar"
    source: CommandSource = "TEXT"
    selectedAgent: str = "team"
    triggerMeeting: bool = True


class AiCommandResponse(BaseModel):
    """استجابة معالجة الأمر الذكي شاملة الرد وإجراء الواجهة ومقترح الصفقة والاجتماع."""

    userMessage: ChatMessageRecord
    assistantMessage: ChatMessageRecord
    uiAction: UiCommandAction | None = None
    tradeProposalEvaluation: TradeProposalEvaluation | None = None
    meeting: AgentMeetingResult | None = None


class ConveneMeetingRequest(BaseModel):
    """طلب عقد اجتماع مخصص لمجلس الوكلاء حول أصل محدد."""

    symbol: str
    horizon: str = "1h"
    language: Language = "ar"


class MarketWsTick(BaseModel):
    """رسالة البث الحي عبر WebSocket لتحديث الأسعار وإجمالي حقوق الملكية."""

    type: Literal["MARKET_TICK"] = "MARKET_TICK"
    timestamp: str
    assets: list[MarketAsset]
    totalEquity: float
    dailyPnl: float
    dailyPnlPct: float
