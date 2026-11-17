/**
 * مركز الذكاء الكمي والحوكمة المتقدمة للوكلاء ومحول Binance Spot
 * Quantum Intelligence Hub — My Road to be Trilunair Dr.MaJoOoOoOoD
 *
 * يغطي الأقسام (3، 6، 8، 9، 10، 11، 12، 13، 14) من المواصفة المرجعية العليا:
 * - إدارة مجلس الوكلاء خماسي الشخصيات ومحولات OpenAI / Gemini / Anthropic / xAI / المحرك الكمي المحلي
 * - نظام التأهيل رباعي المستويات (Trainee -> Analyst -> Experimentally Qualified -> Production Qualified)
 * - محول Binance Spot وفلاتر الرموز القياسية والتمييز الصارم بين TRADABLE_SPOT و REFERENCE_ONLY
 * - محرك الجدوى الاقتصادية للصفقات وفصل تكاليف التداول عن تكاليف استدلال الذكاء الاصطناعي
 * - قاعدة المعرفة التداولية المؤرشفة بالإصدارات والمهارات والموصلات الخارجية ووضع هدف التريليون
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Award,
  BookOpen,
  Brain,
  CheckCircle2,
  Cpu,
  Database,
  DollarSign,
  Lock,
  PauseCircle,
  PlayCircle,
  Plug,
  RefreshCw,
  ShieldAlert,
  Sliders,
  Target,
} from 'lucide-react';
import { quantumApi } from '../../api/quantumClient';
import { formatCurrency, formatNumber } from '../../i18n/translations';
import { useTheme } from '../../theme/ThemeContext';
import type {
  AgentVisualState,
  AuthorizationPolicyMode,
  EconomicViabilityReport,
  KnowledgeArticle,
  LlmProviderId,
  QualificationExamResult,
  QualificationLevel,
  QuantumSystemOverview,
} from '../../types/quantum';

type HubTab = 'council' | 'exchange-risk' | 'knowledge' | 'skills-goals';

const QUALIFICATION_LABELS: Record<QualificationLevel, { ar: string; en: string }> = {
  TRAINEE: { ar: '1. متدرب (Trainee)', en: '1. Trainee' },
  ANALYST: { ar: '2. محلل (Analyst)', en: '2. Analyst' },
  EXPERIMENTALLY_QUALIFIED: {
    ar: '3. مؤهل تجريبياً (Experimentally Qualified)',
    en: '3. Experimentally Qualified',
  },
  PRODUCTION_QUALIFIED: {
    ar: '4. مؤهل للإنتاج (Production Qualified)',
    en: '4. Production Qualified',
  },
};

const VISUAL_STATE_META: Record<
  AgentVisualState,
  { ar: string; en: string; badgeClass: string }
> = {
  THINKING: { ar: 'يفكر (Thinking)', en: 'Thinking', badgeClass: 'holo-badge-accent' },
  AGREE: { ar: 'موافق (Agree)', en: 'Agree', badgeClass: 'holo-badge-success' },
  DISAGREE: { ar: 'معترض (Disagree)', en: 'Disagree', badgeClass: 'holo-badge-danger' },
  SPEAKING: { ar: 'يتحدث (Speaking)', en: 'Speaking', badgeClass: 'holo-badge-warning' },
  INACTIVE: { ar: 'غير نشط (Inactive)', en: 'Inactive', badgeClass: '' },
};

export const IntelligenceHubView: React.FC = () => {
  const { language } = useTheme();
  const isAr = language === 'ar';

  const [activeTab, setActiveTab] = useState<HubTab>('council');
  const [overview, setOverview] = useState<QuantumSystemOverview | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeArticle[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [bannerMsg, setBannerMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);
  const [lastExamResult, setLastExamResult] = useState<QualificationExamResult | null>(null);

  // محاكي الجدوى الاقتصادية للصفقة
  const [econForm, setEconForm] = useState({
    symbol: 'BTCUSDT',
    side: 'BUY' as 'BUY' | 'SELL',
    quantity: 0.05,
    stopLoss: 93800,
    takeProfit: 98500,
  });
  const [econReport, setEconReport] = useState<EconomicViabilityReport | null>(null);

  // تحرير سياسة المخاطر وبوابة التصاريح
  const [policyPin, setPolicyPin] = useState('');
  const [riskDraft, setRiskDraft] = useState({
    maxRiskPerTradePct: 0.5,
    maxExposurePerAssetPct: 25,
    dailyLossLimitPct: 2,
    weeklyLossLimitPct: 5,
    maxDrawdownLimitPct: 10,
  });

  // نموذج إضافة/تحديث مقال في قاعدة المعرفة المؤرشفة
  const [kbSearch, setKbSearch] = useState('');
  const [editingArticleId, setEditingArticleId] = useState<string | undefined>(undefined);
  const [kbForm, setKbForm] = useState({
    category: 'RISK_MANAGEMENT',
    titleAr: '',
    titleEn: '',
    contentAr: '',
    contentEn: '',
  });

  // نموذج هدف التريليون
  const [goalDraft, setGoalDraft] = useState({
    startingEquityUsd: 10000,
    targetEquityUsd: 1000000000000,
    horizonMonths: 120,
    dailyGoalPct: 0.35,
    weeklyGoalPct: 1.8,
    monthlyGoalPct: 7.5,
  });

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, kb] = await Promise.all([
        quantumApi.getOverview(),
        quantumApi.getKnowledgeBase(),
      ]);
      setOverview(ov);
      setKnowledge(kb);
      setRiskDraft({
        maxRiskPerTradePct: ov.riskPolicy.maxRiskPerTradePct,
        maxExposurePerAssetPct: ov.riskPolicy.maxExposurePerAssetPct,
        dailyLossLimitPct: ov.riskPolicy.dailyLossLimitPct,
        weeklyLossLimitPct: ov.riskPolicy.weeklyLossLimitPct,
        maxDrawdownLimitPct: ov.riskPolicy.maxDrawdownLimitPct,
      });
      setGoalDraft(ov.goalConfig);
    } catch (err) {
      setBannerMsg({
        type: 'err',
        text: err instanceof Error ? err.message : 'تعذر تحميل بيانات مركز الذكاء الكمي',
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const notify = (type: 'ok' | 'err', text: string) => {
    setBannerMsg({ type, text });
  };

  const handleTogglePauseAll = async () => {
    if (!overview) return;
    try {
      const nextPaused = !overview.exchangeStatus.agentsPaused;
      await quantumApi.setAgentsPaused(nextPaused);
      await loadAll();
      notify(
        'ok',
        nextPaused
          ? isAr
            ? 'تم إيقاف الوكلاء مؤقتاً بنجاح.'
            : 'All AI agents paused temporarily.'
          : isAr
            ? 'تم استئناف عمل مجلس الوكلاء.'
            : 'AI Council resumed.'
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Error');
    }
  };

  const handleAgentProviderChange = async (
    agentId: string,
    providerId: LlmProviderId,
    defaultModel: string
  ) => {
    try {
      await quantumApi.updateAgentConfig(agentId, {
        assignedProvider: providerId,
        assignedModel: defaultModel,
      });
      await loadAll();
      notify(
        'ok',
        isAr
          ? 'تم تحديث المزود والنموذج — وأعيد مستوى التأهيل إلى (متدرب Trainee) عملاً بقاعدة إعادة التأهيل الإلزامية.'
          : 'Provider & model updated — agent reset to Trainee per mandatory requalification policy.'
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Update failed');
    }
  };

  const handleRunQualification = async (agentId: string) => {
    try {
      const res = await quantumApi.evaluateQualification(agentId);
      setLastExamResult(res);
      await loadAll();
      notify(
        res.passed ? 'ok' : 'err',
        isAr
          ? `نتيجة تقييم التأهيل للوكيل (${agentId}): ${QUALIFICATION_LABELS[res.newLevel].ar} (${res.scorePct}%)`
          : `Qualification result for ${agentId}: ${QUALIFICATION_LABELS[res.newLevel].en} (${res.scorePct}%)`
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Qualification test error');
    }
  };

  const handleRevokePermissions = async (agentId: string) => {
    try {
      await quantumApi.revokeAgentPermissions(agentId);
      await loadAll();
      notify(
        'ok',
        isAr
          ? 'تم سحب الصلاحيات التشغيلية للوكيل وإعادته إلى مستوى المتدرب.'
          : 'Operational permissions revoked and qualification reset.'
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Revoke error');
    }
  };

  const handleEvaluateEconomics = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const report = await quantumApi.evaluateTradeEconomics(econForm);
      setEconReport(report);
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Economics check failed');
    }
  };

  const handleSaveRiskPolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await quantumApi.updateRiskPolicy({ ...riskDraft, adminPin: policyPin });
      await loadAll();
      notify(
        'ok',
        isAr
          ? 'تم تحديث سياسة حدود المخاطر الحتمية وتسجيل التغيير في سجل التدقيق.'
          : 'Deterministic risk policy updated and recorded in audit trail.'
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Risk policy update rejected');
    }
  };

  const handleChangeAuthPolicy = async (policy: AuthorizationPolicyMode) => {
    try {
      await quantumApi.updateAuthorizationPolicy({ policy, adminPin: policyPin });
      await loadAll();
      notify(
        'ok',
        isAr
          ? `تم ضبط سياسة التفويض على: ${policy}`
          : `Authorization policy set to: ${policy}`
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Authorization policy rejected');
    }
  };

  const handleReconcile = async () => {
    try {
      await quantumApi.reconcileExchangeState();
      await loadAll();
      notify(
        'ok',
        isAr
          ? 'تمت مصالحة حالة الحساب والأوامر مع محول Binance Spot بنجاح.'
          : 'Account & order state reconciled with Binance Spot adapter.'
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Reconciliation failed');
    }
  };

  const handleSaveKnowledge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kbForm.titleAr.trim() || !kbForm.contentAr.trim()) return;
    try {
      const saved = await quantumApi.upsertKnowledgeArticle({
        id: editingArticleId,
        category: kbForm.category,
        titleAr: kbForm.titleAr,
        titleEn: kbForm.titleEn || kbForm.titleAr,
        contentAr: kbForm.contentAr,
        contentEn: kbForm.contentEn || kbForm.contentAr,
      });
      setEditingArticleId(undefined);
      setKbForm({
        category: 'RISK_MANAGEMENT',
        titleAr: '',
        titleEn: '',
        contentAr: '',
        contentEn: '',
      });
      await loadAll();
      notify(
        'ok',
        isAr
          ? `تم حفظ المعرفة التداولية بالإصدار v${saved.version}`
          : `Saved knowledge entry at version v${saved.version}`
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Save failed');
    }
  };

  const handleSaveGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await quantumApi.updateGoalConfig(goalDraft);
      await loadAll();
      notify(
        'ok',
        isAr
          ? 'تم تحديث أهداف رحلة التريليون بنجاح.'
          : 'Road to Trilunair goal configuration saved.'
      );
    } catch (err) {
      notify('err', err instanceof Error ? err.message : 'Goal save error');
    }
  };

  if (loading && !overview) {
    return (
      <section className="holo-panel" style={{ padding: '1.5rem' }}>
        <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
          {isAr
            ? 'جاري تحميل منظومة الذكاء الكمي وتأهيل الوكلاء ومحول Binance Spot...'
            : 'Loading Quantum Council, Qualification Gates & Binance Spot Adapter...'}
        </p>
      </section>
    );
  }

  if (!overview) return null;

  const filteredKb = knowledge.filter((item) => {
    if (!kbSearch.trim()) return true;
    const q = kbSearch.toLowerCase();
    return (
      item.titleAr.toLowerCase().includes(q) ||
      item.titleEn.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q) ||
      item.contentAr.toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* رأس مركز الذكاء الكمي وأزرار التبويب */}
      <header
        className="holo-panel"
        style={{
          padding: '1rem 1.25rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.85rem',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Brain size={20} style={{ color: 'var(--accent-primary)' }} />
            {isAr
              ? 'مركز القيادة الكمية: تأهيل الوكلاء، Binance Spot، والجدوى الاقتصادية'
              : 'Quantum Command Hub: Council Qualification, Binance Spot & Economic Viability'}
          </h2>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {isAr
              ? 'إدارة مستقلة لمزودات النماذج (OpenAI / Gemini / Claude / Grok)، تأهيل رباعي المستويات، قاعدة معرفة مؤرشفة بالإصدارات، وضوابط Binance Spot الحتمية.'
              : 'Independent LLM provider adapters, 4-tier agent qualification, versioned trading knowledge base, and Binance Spot safeguards.'}
          </p>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          <button
            type="button"
            className={`holo-btn ${activeTab === 'council' ? 'holo-btn-primary' : ''}`}
            onClick={() => setActiveTab('council')}
          >
            <Award size={16} />
            {isAr ? 'مجلس الوكلاء والتأهيل' : 'AI Council & Qualification'}
          </button>
          <button
            type="button"
            className={`holo-btn ${activeTab === 'exchange-risk' ? 'holo-btn-primary' : ''}`}
            onClick={() => setActiveTab('exchange-risk')}
          >
            <Sliders size={16} />
            {isAr ? 'محول Binance والجدوى والمخاطر' : 'Binance Adapter, Economics & Risk'}
          </button>
          <button
            type="button"
            className={`holo-btn ${activeTab === 'knowledge' ? 'holo-btn-primary' : ''}`}
            onClick={() => setActiveTab('knowledge')}
          >
            <BookOpen size={16} />
            {isAr ? `قاعدة المعرفة (${knowledge.length})` : `Knowledge Base (${knowledge.length})`}
          </button>
          <button
            type="button"
            className={`holo-btn ${activeTab === 'skills-goals' ? 'holo-btn-primary' : ''}`}
            onClick={() => setActiveTab('skills-goals')}
          >
            <Plug size={16} />
            {isAr ? 'المهارات والموصلات وهدف $1T' : 'Skills, Connectors & $1T Goal'}
          </button>
        </div>
      </header>

      {bannerMsg && (
        <div
          role="status"
          aria-live="polite"
          className="holo-panel"
          style={{
            padding: '0.75rem 1rem',
            borderColor:
              bannerMsg.type === 'ok' ? 'var(--status-success)' : 'var(--status-danger)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.75rem',
          }}
        >
          <span style={{ fontSize: '0.9rem' }}>{bannerMsg.text}</span>
          <button type="button" className="holo-btn" onClick={() => setBannerMsg(null)}>
            {isAr ? 'إغلاق' : 'Dismiss'}
          </button>
        </div>
      )}

      {/* التبويب الأول: مجلس الوكلاء ومحولات النماذج ونظام التأهيل رباعي المستويات */}
      {activeTab === 'council' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* حالة محولات المزودات المستقلة بصدق وشفافية تامة */}
          <section className="holo-panel" style={{ padding: '1rem 1.25rem' }}>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '0.85rem',
              }}
            >
              <h3 style={{ margin: 0, fontSize: '1.02rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                <Cpu size={18} style={{ color: 'var(--accent-primary)' }} />
                {isAr
                  ? 'حالة محولات مزودات الذكاء الاصطناعي المستقلة (بدون أي انتحال لاستجابات غير متصلة)'
                  : 'Independent AI Provider Adapters (Truthful Live Availability — Zero Fabricated Responses)'}
              </h3>
              <button
                type="button"
                className={`holo-btn ${overview.exchangeStatus.agentsPaused ? 'holo-btn-primary' : 'holo-btn-danger'}`}
                onClick={handleTogglePauseAll}
              >
                {overview.exchangeStatus.agentsPaused ? <PlayCircle size={16} /> : <PauseCircle size={16} />}
                {overview.exchangeStatus.agentsPaused
                  ? isAr
                    ? 'استئناف عمل الوكلاء'
                    : 'Resume All Agents'
                  : isAr
                    ? 'إيقاف الوكلاء مؤقتاً'
                    : 'Pause Agents Temporarily'}
              </button>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '0.75rem',
              }}
            >
              {overview.providers.map((prov) => (
                <div key={prov.providerId} className="holo-panel-subtle" style={{ padding: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.4rem' }}>
                    <strong>{prov.displayName}</strong>
                    <span className={`holo-badge ${prov.available ? 'holo-badge-success' : 'holo-badge-warning'}`}>
                      {prov.available
                        ? isAr
                          ? 'متاح ومتصل'
                          : 'AVAILABLE'
                        : isAr
                          ? 'غير مهيأ (UNAVAILABLE)'
                          : 'UNAVAILABLE'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                    {isAr ? prov.statusMessageAr : prov.statusMessageEn}
                  </div>
                  <div className="tabular-nums" style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                    Cost/1K tok: ${prov.costPer1kTokensUsd.toFixed(4)} • {prov.availableModels.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* تنبيه عدم اعتبار التأهيل ضماناً للربحية */}
          <div className="holo-panel-subtle" style={{ padding: '0.75rem 1rem', borderColor: 'var(--status-warning)' }}>
            <strong style={{ color: 'var(--status-warning)' }}>
              {isAr ? 'ضابط حوكمة التأهيل (القسم 9): ' : 'Qualification Governance Rule (Sec 9): '}
            </strong>
            <span style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
              {isAr
                ? 'لا يجوز مشاركة أي وكيل في القرارات المستقلة (AUTONOMOUS) إلا بعد بلوغ المستوى الرابع (مؤهل للإنتاج Production Qualified). أي تعديل في النموذج أو التعليمات أو المهارات أو الأوزان أو الصلاحيات يعيد التأهيل تلقائياً إلى (متدرب). درجات التأهيل تثبت الامتثال التشغيلي ولا تُعد دليلاً على ربحية مستقبلية.'
                : 'Only Production Qualified agents may participate in AUTONOMOUS mode. Any material change to model, instructions, skills, weights, or permissions triggers mandatory requalification. Qualification scores never guarantee profitable trades.'}
            </span>
          </div>

          {/* بطاقات الوكلاء الخمسة وتكوينهم وتأهيلهم */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(330px, 1fr))',
              gap: '0.9rem',
            }}
          >
            {overview.agents.map((agent) => {
              const vMeta = VISUAL_STATE_META[agent.visualState] || VISUAL_STATE_META.INACTIVE;
              const selectedProvObj =
                overview.providers.find((p) => p.providerId === agent.assignedProvider) ||
                overview.providers[0];
              return (
                <article key={agent.agentId} className="holo-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '1rem' }}>
                        {isAr ? agent.nameAr : agent.nameEn}
                      </h4>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {isAr ? agent.roleAr : agent.roleEn}
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                      <span className={`holo-badge ${vMeta.badgeClass}`}>
                        {isAr ? vMeta.ar : vMeta.en}
                      </span>
                      <span
                        className={`holo-badge ${
                          agent.qualificationLevel === 'PRODUCTION_QUALIFIED'
                            ? 'holo-badge-success'
                            : agent.requalificationRequired
                              ? 'holo-badge-danger'
                              : 'holo-badge-accent'
                        }`}
                      >
                        {isAr
                          ? QUALIFICATION_LABELS[agent.qualificationLevel].ar
                          : QUALIFICATION_LABELS[agent.qualificationLevel].en}
                      </span>
                    </div>
                  </div>

                  {/* المزود والنموذج المسند */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                    <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {isAr ? 'المزود المسند' : 'Assigned Provider'}
                      <select
                        className="holo-select"
                        value={agent.assignedProvider}
                        onChange={(e) => {
                          const nextPid = e.target.value as LlmProviderId;
                          const prov = overview.providers.find((p) => p.providerId === nextPid);
                          void handleAgentProviderChange(
                            agent.agentId,
                            nextPid,
                            prov?.availableModels[0] || 'quant-deterministic-v1'
                          );
                        }}
                      >
                        {overview.providers.map((p) => (
                          <option key={p.providerId} value={p.providerId}>
                            {p.displayName} {p.available ? '✓' : '(Unavailable)'}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {isAr ? 'النموذج الفعلي' : 'Assigned Model'}
                      <select
                        className="holo-select"
                        value={agent.assignedModel}
                        onChange={(e) =>
                          void handleAgentProviderChange(
                            agent.agentId,
                            agent.assignedProvider,
                            e.target.value
                          )
                        }
                      >
                        {selectedProvObj.availableModels.map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  {/* وزن القرار وحالة تفعيل الوكيل */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                    <label style={{ flex: 1, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {isAr ? 'وزن القرار في المجلس:' : 'Decision Weight:'}{' '}
                      <strong className="tabular-nums">{agent.decisionWeight.toFixed(2)}x</strong>
                      <input
                        type="range"
                        min={0.2}
                        max={2.0}
                        step={0.1}
                        value={agent.decisionWeight}
                        onChange={(e) =>
                          void quantumApi
                            .updateAgentConfig(agent.agentId, {
                              decisionWeight: parseFloat(e.target.value),
                            })
                            .then(loadAll)
                        }
                        style={{ width: '100%' }}
                      />
                    </label>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={agent.enabled}
                        onChange={(e) =>
                          void quantumApi
                            .updateAgentConfig(agent.agentId, { enabled: e.target.checked })
                            .then(loadAll)
                        }
                      />
                      {isAr ? 'مفعّل' : 'Enabled'}
                    </label>
                  </div>

                  {/* إحصاءات التكلفة والموثوقية */}
                  <div
                    className="holo-panel-subtle tabular-nums"
                    style={{
                      padding: '0.55rem 0.7rem',
                      fontSize: '0.78rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.4rem',
                    }}
                  >
                    <span>Calls: {agent.metrics.totalCalls}</span>
                    <span>AI Cost: ${agent.metrics.attributableAiCostUsd.toFixed(4)}</span>
                    <span>Score: {agent.qualificationScorePct}%</span>
                  </div>

                  {/* أزرار التأهيل وسحب الصلاحيات */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', marginTop: 'auto' }}>
                    <button
                      type="button"
                      className="holo-btn holo-btn-primary"
                      style={{ flex: 1 }}
                      onClick={() => void handleRunQualification(agent.agentId)}
                      disabled={agent.qualificationLevel === 'PRODUCTION_QUALIFIED'}
                    >
                      <CheckCircle2 size={15} />
                      {agent.qualificationLevel === 'PRODUCTION_QUALIFIED'
                        ? isAr
                          ? 'مؤهل للإنتاج بالكامل'
                          : 'Production Qualified'
                        : isAr
                          ? 'ترقية واجتياز اختبار التأهيل التالي'
                          : 'Run Next Qualification Gate'}
                    </button>
                    <button
                      type="button"
                      className="holo-btn holo-btn-danger"
                      onClick={() => void handleRevokePermissions(agent.agentId)}
                    >
                      <Lock size={14} />
                      {isAr ? 'سحب الصلاحيات' : 'Revoke'}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          {lastExamResult && (
            <section className="holo-panel" style={{ padding: '1rem' }}>
              <h4 style={{ margin: '0 0 0.5rem' }}>
                {isAr
                  ? `تفاصيل آخر اختبار تأهيل (${lastExamResult.agentId}): ${lastExamResult.previousLevel} ← ${lastExamResult.newLevel}`
                  : `Latest Qualification Gate Report (${lastExamResult.agentId}): ${lastExamResult.previousLevel} -> ${lastExamResult.newLevel}`}
              </h4>
              <ul style={{ margin: 0, paddingInlineStart: '1.2rem', fontSize: '0.85rem' }}>
                {lastExamResult.checksRun.map((chk) => (
                  <li key={chk.gate} style={{ marginBottom: '0.25rem' }}>
                    <strong>[{chk.passed ? 'PASS' : 'FAIL'}] {chk.gate}:</strong>{' '}
                    {isAr ? chk.detailAr : chk.detailEn}
                  </li>
                ))}
              </ul>
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.78rem', color: 'var(--status-warning)' }}>
                {isAr ? lastExamResult.disclaimerAr : lastExamResult.disclaimerEn}
              </p>
            </section>
          )}
        </div>
      )}

      {/* التبويب الثاني: محول Binance Spot والجدوى الاقتصادية وسياسة المخاطر الحتمية */}
      {activeTab === 'exchange-risk' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* حالة محول Binance Spot وبوليصة التفويض */}
          <section className="holo-panel" style={{ padding: '1rem 1.25rem' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', marginBottom: '0.85rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.02rem' }}>
                  {isAr
                    ? 'محول Binance Spot وحالة الحساب ومصالحة الأوامر'
                    : 'Binance Spot Exchange Adapter & State Reconciliation'}
                </h3>
                <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  {isAr
                    ? 'لا يفترض النظام أبداً تكافؤ USD و USDT، ويمنع إرسال الأصول المرجعية (REFERENCE_ONLY) للتنفيذ في Binance Spot.'
                    : 'Never conflates USD with USDT; strictly blocks REFERENCE_ONLY instruments from Binance Spot execution.'}
                </p>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
                <span className="holo-badge holo-badge-accent">
                  Mode: {overview.exchangeStatus.connectionMode}
                </span>
                <span
                  className={`holo-badge ${
                    overview.exchangeStatus.accountStateUncertain
                      ? 'holo-badge-danger'
                      : 'holo-badge-success'
                  }`}
                >
                  {overview.exchangeStatus.accountStateUncertain
                    ? isAr
                      ? 'حالة الحساب غير مؤكدة — التنفيذ مجمد'
                      : 'Account Uncertain — Halted'
                    : isAr
                      ? 'حالة الحساب متطابقة ومؤكدة'
                      : 'Account State Verified'}
                </span>
                <button type="button" className="holo-btn" onClick={() => void handleReconcile()}>
                  <RefreshCw size={15} />
                  {isAr ? 'مصالحة فورية (Reconcile)' : 'Reconcile Now'}
                </button>
              </div>
            </div>

            {/* اختيار سياسة التفويض (PAPER / HUMAN_APPROVAL / AUTONOMOUS) */}
            <div className="holo-panel-subtle" style={{ padding: '0.8rem', marginBottom: '0.9rem', display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.86rem', fontWeight: 700 }}>
                {isAr ? 'سياسة بوابة التفويض:' : 'Authorization Policy:'}
              </span>
              {(['PAPER', 'HUMAN_APPROVAL', 'AUTONOMOUS'] as AuthorizationPolicyMode[]).map((pol) => (
                <button
                  key={pol}
                  type="button"
                  disabled={pol === 'AUTONOMOUS'}
                  title={
                    pol === 'AUTONOMOUS'
                      ? isAr
                        ? 'التداول الذاتي الحقيقي معطل نهائياً في الإصدار v1.1.0-cloud-paper'
                        : 'Autonomous live trading is permanently disabled in v1.1.0-cloud-paper'
                      : undefined
                  }
                  className={`holo-btn ${overview.exchangeStatus.authorizationPolicy === pol ? 'holo-btn-primary' : ''}`}
                  onClick={() => void handleChangeAuthPolicy(pol)}
                >
                  {pol === 'AUTONOMOUS' ? `${pol} (LOCKED)` : pol}
                </button>
              ))}
              <input
                type="password"
                className="holo-input"
                style={{ maxWidth: '215px' }}
                placeholder={isAr ? 'سر المسؤول المشفر (Admin Secret)' : 'Encrypted Admin Secret'}
                value={policyPin}
                onChange={(e) => setPolicyPin(e.target.value)}
              />
            </div>

            {/* جدول فلاتر الرموز القياسية وتصنيف الأصول */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'start' }}>
                    <th style={{ padding: '0.5rem' }}>{isAr ? 'الرمز القياسي' : 'Canonical Symbol'}</th>
                    <th style={{ padding: '0.5rem' }}>{isAr ? 'الاسم المعروض' : 'Display Alias'}</th>
                    <th style={{ padding: '0.5rem' }}>{isAr ? 'التصنيف' : 'Classification'}</th>
                    <th style={{ padding: '0.5rem' }}>Tick Size</th>
                    <th style={{ padding: '0.5rem' }}>Step Size</th>
                    <th style={{ padding: '0.5rem' }}>Min Notional</th>
                    <th style={{ padding: '0.5rem' }}>{isAr ? 'حداثة البيانات' : 'Freshness'}</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.exchangeStatus.instruments.map((inst) => (
                    <tr key={inst.canonicalSymbol} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td className="tabular-nums" style={{ padding: '0.5rem', fontWeight: 700 }}>
                        {inst.canonicalSymbol}
                      </td>
                      <td style={{ padding: '0.5rem' }}>{inst.displayAlias}</td>
                      <td style={{ padding: '0.5rem' }}>
                        <span
                          className={`holo-badge ${
                            inst.classification === 'TRADABLE_SPOT'
                              ? 'holo-badge-success'
                              : inst.classification === 'REFERENCE_ONLY'
                                ? 'holo-badge-warning'
                                : 'holo-badge-danger'
                          }`}
                        >
                          {inst.classification}
                        </span>
                      </td>
                      <td className="tabular-nums" style={{ padding: '0.5rem' }}>{inst.tickSize}</td>
                      <td className="tabular-nums" style={{ padding: '0.5rem' }}>{inst.stepSize}</td>
                      <td className="tabular-nums" style={{ padding: '0.5rem' }}>
                        {inst.minNotional} {inst.quoteAsset}
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        <span className={`holo-badge ${inst.isStale ? 'holo-badge-danger' : 'holo-badge-success'}`}>
                          {inst.isStale ? 'STALE' : 'FRESH'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* محرك الجدوى الاقتصادية + سياسة المخاطر + فصل المحاسبة */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1rem' }}>
            {/* فاحص الجدوى الاقتصادية للصفقة (Section 13) */}
            <form onSubmit={handleEvaluateEconomics} className="holo-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <DollarSign size={18} style={{ color: 'var(--accent-primary)' }} />
                {isAr
                  ? 'محرك الجدوى الاقتصادية للصفقة (Trade Economic Viability)'
                  : 'Trade Economic Viability Engine (Sec 13)'}
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.78rem' }}>
                  {isAr ? 'رمز Binance القياسي' : 'Canonical Symbol'}
                  <select
                    className="holo-select"
                    value={econForm.symbol}
                    onChange={(e) => setEconForm({ ...econForm, symbol: e.target.value })}
                  >
                    {overview.exchangeStatus.instruments
                      .filter((i) => i.classification === 'TRADABLE_SPOT')
                      .map((i) => (
                        <option key={i.canonicalSymbol} value={i.canonicalSymbol}>
                          {i.canonicalSymbol} ({i.displayAlias})
                        </option>
                      ))}
                  </select>
                </label>
                <label style={{ fontSize: '0.78rem' }}>
                  {isAr ? 'الكمية' : 'Quantity'}
                  <input
                    type="number"
                    step="0.001"
                    className="holo-input tabular-nums"
                    value={econForm.quantity}
                    onChange={(e) =>
                      setEconForm({ ...econForm, quantity: parseFloat(e.target.value) || 0 })
                    }
                  />
                </label>
                <label style={{ fontSize: '0.78rem' }}>
                  {isAr ? 'وقف الخسارة (Stop Loss)' : 'Stop Loss'}
                  <input
                    type="number"
                    step="any"
                    className="holo-input tabular-nums"
                    value={econForm.stopLoss}
                    onChange={(e) =>
                      setEconForm({ ...econForm, stopLoss: parseFloat(e.target.value) || 0 })
                    }
                  />
                </label>
                <label style={{ fontSize: '0.78rem' }}>
                  {isAr ? 'جني الأرباح (Take Profit)' : 'Take Profit'}
                  <input
                    type="number"
                    step="any"
                    className="holo-input tabular-nums"
                    value={econForm.takeProfit}
                    onChange={(e) =>
                      setEconForm({ ...econForm, takeProfit: parseFloat(e.target.value) || 0 })
                    }
                  />
                </label>
              </div>

              <button type="submit" className="holo-btn holo-btn-primary">
                <Activity size={16} />
                {isAr ? 'حساب صافي الجدوى الاقتصادية والتكاليف' : 'Evaluate Net Trade Economics'}
              </button>

              {econReport && (
                <div className="holo-panel-subtle" style={{ padding: '0.75rem', fontSize: '0.82rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                    <strong>{isAr ? 'النتيجة الاقتصادية:' : 'Viability Verdict:'}</strong>
                    <span className={`holo-badge ${econReport.economicallyViable ? 'holo-badge-success' : 'holo-badge-danger'}`}>
                      {econReport.economicallyViable
                        ? isAr
                          ? 'مجدية اقتصادياً'
                          : 'VIABLE'
                        : isAr
                          ? 'غير مجدية (التكلفة تلتهم العائد)'
                          : 'WEAK ECONOMICS'}
                    </span>
                  </div>
                  <div className="tabular-nums" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.3rem' }}>
                    <span>Notional: {formatCurrency(econReport.notionalUsd)}</span>
                    <span>Fee: ${econReport.exchangeCommissionUsd.toFixed(3)}</span>
                    <span>Spread: ${econReport.spreadCostUsd.toFixed(3)}</span>
                    <span>Slippage: ${econReport.expectedSlippageUsd.toFixed(3)}</span>
                    <span>AI Cost: ${econReport.attributableAiCostUsd.toFixed(4)}</span>
                    <span>Total Cost: ${econReport.totalExpectedCostUsd.toFixed(3)}</span>
                    <span>Expected Reward: {formatCurrency(econReport.expectedRewardUsd)}</span>
                    <span>Reward/Cost: {econReport.rewardToCostRatio.toFixed(2)}x</span>
                  </div>
                  <p style={{ margin: '0.45rem 0 0', color: 'var(--text-secondary)' }}>
                    {isAr ? econReport.notesAr : econReport.notesEn}
                  </p>
                </div>
              )}
            </form>

            {/* حدود محرك المخاطر الحتمي غير القابلة للتجاوز (Section 12) */}
            <form onSubmit={handleSaveRiskPolicy} className="holo-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <ShieldAlert size={18} style={{ color: 'var(--accent-primary)' }} />
                {isAr
                  ? 'ضوابط محرك المخاطر الحتمي والمحاسبة المفصولة (القسم 12 و13)'
                  : 'Deterministic Risk Limits & Separated Cost Ledger'}
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.76rem' }}>
                  {isAr ? 'أقصى مخاطرة للصفقة % (افتراضي 0.5%)' : 'Max Risk/Trade %'}
                  <input
                    type="number"
                    step="0.1"
                    className="holo-input tabular-nums"
                    value={riskDraft.maxRiskPerTradePct}
                    onChange={(e) =>
                      setRiskDraft({ ...riskDraft, maxRiskPerTradePct: parseFloat(e.target.value) || 0.5 })
                    }
                  />
                </label>
                <label style={{ fontSize: '0.76rem' }}>
                  {isAr ? 'أقصى تعرض للأصل % (افتراضي 25%)' : 'Max Asset Exposure %'}
                  <input
                    type="number"
                    step="1"
                    className="holo-input tabular-nums"
                    value={riskDraft.maxExposurePerAssetPct}
                    onChange={(e) =>
                      setRiskDraft({ ...riskDraft, maxExposurePerAssetPct: parseFloat(e.target.value) || 25 })
                    }
                  />
                </label>
                <label style={{ fontSize: '0.76rem' }}>
                  {isAr ? 'قاطع الخسارة اليومي % (2%)' : 'Daily Loss Breaker %'}
                  <input
                    type="number"
                    step="0.5"
                    className="holo-input tabular-nums"
                    value={riskDraft.dailyLossLimitPct}
                    onChange={(e) =>
                      setRiskDraft({ ...riskDraft, dailyLossLimitPct: parseFloat(e.target.value) || 2 })
                    }
                  />
                </label>
                <label style={{ fontSize: '0.76rem' }}>
                  {isAr ? 'قاطع الخسارة الأسبوعي % (5%) / التراجع (10%)' : 'Weekly % / Max DD %'}
                  <div style={{ display: 'flex', gap: '0.35rem' }}>
                    <input
                      type="number"
                      step="0.5"
                      className="holo-input tabular-nums"
                      value={riskDraft.weeklyLossLimitPct}
                      onChange={(e) =>
                        setRiskDraft({ ...riskDraft, weeklyLossLimitPct: parseFloat(e.target.value) || 5 })
                      }
                    />
                    <input
                      type="number"
                      step="0.5"
                      className="holo-input tabular-nums"
                      value={riskDraft.maxDrawdownLimitPct}
                      onChange={(e) =>
                        setRiskDraft({ ...riskDraft, maxDrawdownLimitPct: parseFloat(e.target.value) || 10 })
                      }
                    />
                  </div>
                </label>
              </div>

              <div className="holo-panel-subtle" style={{ padding: '0.55rem 0.7rem', fontSize: '0.76rem' }}>
                <strong style={{ color: 'var(--status-danger)' }}>
                  {isAr ? 'محظورات قطعية غير قابلة للتعطيل:' : 'Non-Overridable Hard Prohibitions:'}
                </strong>{' '}
                {isAr
                  ? 'الرافعة المالية (Leverage) • الهامش (Margin) • العقود الآجلة (Futures) • الاقتراض (Borrowing) • السحب الخارجي (Withdrawals).'
                  : 'No Leverage • No Margin • No Futures • No Borrowing • No Withdrawals.'}
              </div>

              <button type="submit" className="holo-btn">
                {isAr ? 'تحديث سياسة المخاطر الإدارية (يتطلب PIN)' : 'Apply Risk Policy (Requires PIN)'}
              </button>

              {/* تقرير المحاسبة المفصول: تكاليف التداول مقابل تكاليف الذكاء الاصطناعي */}
              <div className="holo-panel-subtle tabular-nums" style={{ padding: '0.65rem', fontSize: '0.79rem' }}>
                <div style={{ fontWeight: 700, marginBottom: '0.3rem', fontFamily: 'var(--font-sans)' }}>
                  {isAr
                    ? 'تقرير التكاليف المفصول (التداول مقابل تشغيل الذكاء الاصطناعي):'
                    : 'Separated Cost Accounting (Trading Execution vs AI Operations):'}
                </div>
                <div>Trading Commissions + Spread/Slippage: ${overview.accounting.totalTradingExecutionCostsUsd.toFixed(2)}</div>
                <div>AI Model Inference Costs: ${overview.accounting.totalAiInferenceCostsUsd.toFixed(4)}</div>
                <div>External Data Connectors Cost: ${overview.accounting.totalConnectorOperatingCostsUsd.toFixed(4)}</div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* التبويب الثالث: قاعدة المعرفة التداولية المؤرشفة بالإصدارات (Section 10) */}
      {activeTab === 'knowledge' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(300px, 0.9fr)', gap: '1rem' }}>
          <section className="holo-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
              <h3 style={{ margin: 0, fontSize: '1rem' }}>
                {isAr
                  ? 'موسوعة المعرفة التداولية المؤرشفة بالإصدارات (Trading Knowledge Base)'
                  : 'Versioned Trading Knowledge Base'}
              </h3>
              <input
                type="search"
                className="holo-input"
                style={{ maxWidth: '240px' }}
                placeholder={isAr ? 'ابحث في المواضيع...' : 'Search topics...'}
                value={kbSearch}
                onChange={(e) => setKbSearch(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: '540px', overflowY: 'auto' }}>
              {filteredKb.map((art) => (
                <article key={art.id} className="holo-panel-subtle" style={{ padding: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                    <strong>{isAr ? art.titleAr : art.titleEn}</strong>
                    <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                      <span className="holo-badge holo-badge-accent tabular-nums">v{art.version}</span>
                      <button
                        type="button"
                        className="holo-btn"
                        style={{ minHeight: '30px', padding: '0.2rem 0.55rem', fontSize: '0.76rem' }}
                        onClick={() => {
                          setEditingArticleId(art.id);
                          setKbForm({
                            category: art.category,
                            titleAr: art.titleAr,
                            titleEn: art.titleEn,
                            contentAr: art.contentAr,
                            contentEn: art.contentEn,
                          });
                        }}
                      >
                        {isAr ? 'تعديل وإصدار جديد' : 'Edit (New Version)'}
                      </button>
                    </div>
                  </div>
                  <p style={{ margin: '0.35rem 0 0', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                    {isAr ? art.contentAr : art.contentEn}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <form onSubmit={handleSaveKnowledge} className="holo-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            <h3 style={{ margin: 0, fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Database size={17} style={{ color: 'var(--accent-primary)' }} />
              {editingArticleId
                ? isAr
                  ? 'تحديث مورد معرفي (يرفع رقم الإصدار تلقائياً)'
                  : 'Update Knowledge Entry (Increments Version)'
                : isAr
                  ? 'إضافة مورد معرفي جديد'
                  : 'Add Knowledge Resource'}
            </h3>
            <input
              type="text"
              className="holo-input"
              placeholder={isAr ? 'العنوان بالعربية' : 'Arabic Title'}
              value={kbForm.titleAr}
              onChange={(e) => setKbForm({ ...kbForm, titleAr: e.target.value })}
              required
            />
            <input
              type="text"
              className="holo-input"
              placeholder={isAr ? 'العنوان بالإنجليزية' : 'English Title'}
              value={kbForm.titleEn}
              onChange={(e) => setKbForm({ ...kbForm, titleEn: e.target.value })}
            />
            <textarea
              className="holo-input"
              rows={4}
              placeholder={isAr ? 'المحتوى العلمي والقواعد التداولية بالعربية...' : 'Arabic Content...'}
              value={kbForm.contentAr}
              onChange={(e) => setKbForm({ ...kbForm, contentAr: e.target.value })}
              required
            />
            <textarea
              className="holo-input"
              rows={3}
              placeholder={isAr ? 'المحتوى بالإنجليزية (اختياري)...' : 'English Content...'}
              value={kbForm.contentEn}
              onChange={(e) => setKbForm({ ...kbForm, contentEn: e.target.value })}
            />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="submit" className="holo-btn holo-btn-primary" style={{ flex: 1 }}>
                {isAr ? 'حفظ وتوثيق الإصدار' : 'Save Versioned Entry'}
              </button>
              {editingArticleId && (
                <button
                  type="button"
                  className="holo-btn"
                  onClick={() => {
                    setEditingArticleId(undefined);
                    setKbForm({
                      category: 'RISK_MANAGEMENT',
                      titleAr: '',
                      titleEn: '',
                      contentAr: '',
                      contentEn: '',
                    });
                  }}
                >
                  {isAr ? 'إلغاء' : 'Cancel'}
                </button>
              )}
            </div>
          </form>
        </div>
      )}

      {/* التبويب الرابع: المهارات المعيارية والموصلات الخارجية ووضع هدف التريليون */}
      {activeTab === 'skills-goals' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1rem' }}>
            {/* المهارات المعيارية (Modular Agent Skills) */}
            <section className="holo-panel" style={{ padding: '1rem' }}>
              <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>
                {isAr ? 'المهارات التحليلية المعيارية للوكلاء (Modular Skills)' : 'Modular Agent Skills'}
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {overview.skills.map((sk) => (
                  <div
                    key={sk.skillId}
                    className="holo-panel-subtle"
                    style={{
                      padding: '0.6rem 0.75rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: '0.88rem' }}>{isAr ? sk.nameAr : sk.nameEn}</strong>
                      <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                        {isAr ? sk.descriptionAr : sk.descriptionEn}
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={sk.enabled}
                      onChange={(e) =>
                        void quantumApi.toggleSkill(sk.skillId, e.target.checked).then(loadAll)
                      }
                    />
                  </div>
                ))}
              </div>
            </section>

            {/* الموصلات الخارجية (External Data Connectors — Untrusted Input Sanitized) */}
            <section className="holo-panel" style={{ padding: '1rem' }}>
              <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>
                {isAr
                  ? 'موصلات البيانات الخارجية (تُعامل كمدخلات غير موثوقة وتُعقّم)'
                  : 'External Data Connectors (Treated as Untrusted Input)'}
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {overview.connectors.map((conn) => (
                  <div key={conn.connectorId} className="holo-panel-subtle" style={{ padding: '0.7rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong>{isAr ? conn.nameAr : conn.nameEn}</strong>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <span
                          className={`holo-badge ${
                            conn.healthStatus === 'HEALTHY'
                              ? 'holo-badge-success'
                              : 'holo-badge-warning'
                          }`}
                        >
                          {conn.healthStatus}
                        </span>
                        <input
                          type="checkbox"
                          checked={conn.enabled}
                          onChange={(e) =>
                            void quantumApi
                              .updateConnector(conn.connectorId, e.target.checked)
                              .then(loadAll)
                          }
                        />
                      </div>
                    </div>
                    <div className="tabular-nums" style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
                      Provider: {conn.provider} • Rate: {conn.rateLimitPerMin}/min • Freshness:{' '}
                      {conn.dataFreshnessSeconds}s • Cost/1K: ${conn.operatingCostPer1kCallsUsd}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      <AlertTriangle size={12} style={{ verticalAlign: 'middle', marginInlineEnd: '4px' }} />
                      {isAr
                        ? 'فحص المدخلات غير الموثوقة مفعل • الصلاحيات المطلوبة: '
                        : 'Untrusted-input sanitization active • Required keys: '}
                      {conn.requiredCredentials.length ? conn.requiredCredentials.join(', ') : 'Public / None'}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* إعداد وضع الهدف — رحلة التريليون (Section 14) */}
          <form onSubmit={handleSaveGoal} className="holo-panel" style={{ padding: '1rem' }}>
            <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <Target size={18} style={{ color: 'var(--accent-primary)' }} />
              {isAr
                ? 'إعدادات وضع الهدف — رحلة الوصول إلى التريليون (Goal Mode — Road to Trilunair)'
                : 'Goal Mode Configuration — Road to $1,000,000,000,000'}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.65rem' }}>
              <label style={{ fontSize: '0.78rem' }}>
                {isAr ? 'رأس المال الابتدائي ($)' : 'Starting Equity ($)'}
                <input
                  type="number"
                  className="holo-input tabular-nums"
                  value={goalDraft.startingEquityUsd}
                  onChange={(e) =>
                    setGoalDraft({ ...goalDraft, startingEquityUsd: parseFloat(e.target.value) || 10000 })
                  }
                />
              </label>
              <label style={{ fontSize: '0.78rem' }}>
                {isAr ? 'الهدف النهائي ($)' : 'Target Equity ($)'}
                <input
                  type="number"
                  className="holo-input tabular-nums"
                  value={goalDraft.targetEquityUsd}
                  onChange={(e) =>
                    setGoalDraft({
                      ...goalDraft,
                      targetEquityUsd: parseFloat(e.target.value) || 1000000000000,
                    })
                  }
                />
              </label>
              <label style={{ fontSize: '0.78rem' }}>
                {isAr ? 'الأفق الزمني (أشهر)' : 'Time Horizon (Months)'}
                <input
                  type="number"
                  className="holo-input tabular-nums"
                  value={goalDraft.horizonMonths}
                  onChange={(e) =>
                    setGoalDraft({ ...goalDraft, horizonMonths: parseInt(e.target.value, 10) || 120 })
                  }
                />
              </label>
              <label style={{ fontSize: '0.78rem' }}>
                {isAr ? 'الهدف اليومي (%)' : 'Daily Goal (%)'}
                <input
                  type="number"
                  step="0.05"
                  className="holo-input tabular-nums"
                  value={goalDraft.dailyGoalPct}
                  onChange={(e) =>
                    setGoalDraft({ ...goalDraft, dailyGoalPct: parseFloat(e.target.value) || 0 })
                  }
                />
              </label>
              <label style={{ fontSize: '0.78rem' }}>
                {isAr ? 'الهدف الأسبوعي (%)' : 'Weekly Goal (%)'}
                <input
                  type="number"
                  step="0.1"
                  className="holo-input tabular-nums"
                  value={goalDraft.weeklyGoalPct}
                  onChange={(e) =>
                    setGoalDraft({ ...goalDraft, weeklyGoalPct: parseFloat(e.target.value) || 0 })
                  }
                />
              </label>
              <label style={{ fontSize: '0.78rem' }}>
                {isAr ? 'الهدف الشهري (%)' : 'Monthly Goal (%)'}
                <input
                  type="number"
                  step="0.5"
                  className="holo-input tabular-nums"
                  value={goalDraft.monthlyGoalPct}
                  onChange={(e) =>
                    setGoalDraft({ ...goalDraft, monthlyGoalPct: parseFloat(e.target.value) || 0 })
                  }
                />
              </label>
            </div>
            <div style={{ marginTop: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {isAr
                  ? `المضاعف المطلوب: ${formatNumber(goalDraft.targetEquityUsd / Math.max(1, goalDraft.startingEquityUsd), 0)}x — لا يجوز لأهداف النمو تجاوز محرك المخاطر الحتمي أبداً.`
                  : `Required multiple: ${formatNumber(goalDraft.targetEquityUsd / Math.max(1, goalDraft.startingEquityUsd), 0)}x — Growth goals never override deterministic risk limits.`}
              </span>
              <button type="submit" className="holo-btn holo-btn-primary">
                {isAr ? 'حفظ أهداف رحلة التريليون' : 'Save Goal Configuration'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
