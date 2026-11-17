/**
 * قاعة اجتماع الوكلاء الحية المدمجة داخل قاعة التداول (Integrated Agent Meeting Room)
 * تعرض مداولات الوكلاء المتخصصين، نقاط الاتفاق والاختلاف، الأدلة وعدم اليقين،
 * التكاليف والمخاطر الحتمية، والتوصية النهائية مع دعم التشغيل الصوتي المتسلسل والمقاطعة الفورية.
 */

import React, { useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  FileSearch,
  Gavel,
  RefreshCw,
  Scale,
  Send,
  ShieldCheck,
  Square,
  Users,
  Volume2,
} from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import { formatCurrency, formatNumber } from '../../i18n/translations';
import type { SpeechEngineController } from '../../voice/useSpeechEngine';
import type {
  AgentDeliberationItem,
  AgentMeetingResult,
  AgentStance,
  TradeProposalInput,
} from '../../types/trilunair';

export interface AgentMeetingRoomProps {
  meeting: AgentMeetingResult | null;
  isLoading: boolean;
  selectedSymbol: string;
  speech: SpeechEngineController;
  onConveneMeeting: (symbol: string) => Promise<void>;
  onProposeRecommendedTrade: (proposal: TradeProposalInput) => Promise<void>;
}

function stanceBadgeClass(stance: AgentStance): string {
  if (stance === 'BUY') return 'holo-badge holo-badge-success';
  if (stance === 'SELL') return 'holo-badge holo-badge-danger';
  if (stance === 'CAUTION') return 'holo-badge holo-badge-warning';
  return 'holo-badge holo-badge-accent';
}

function stanceLabel(stance: AgentStance, lang: 'ar' | 'en'): string {
  if (lang === 'en') return stance;
  switch (stance) {
    case 'BUY':
      return 'شراء (BUY)';
    case 'SELL':
      return 'بيع (SELL)';
    case 'CAUTION':
      return 'حذر (CAUTION)';
    default:
      return 'احتفاظ / ترقب (HOLD)';
  }
}

function deliberationStatusLabel(
  status: AgentDeliberationItem['status'],
  lang: 'ar' | 'en'
): string {
  if (lang === 'en') return status;
  switch (status) {
    case 'AGREE':
      return 'متفق';
    case 'DISSENT':
      return 'معارض';
    case 'CAUTION':
      return 'تحفظ رقابي';
    default:
      return 'جاهز';
  }
}

export const AgentMeetingRoom: React.FC<AgentMeetingRoomProps> = ({
  meeting,
  isLoading,
  selectedSymbol,
  speech,
  onConveneMeeting,
  onProposeRecommendedTrade,
}) => {
  const { language } = useTheme();
  const [isPreparingProposal, setIsPreparingProposal] = useState<boolean>(false);

  const handlePlayRoundtable = () => {
    if (!meeting) return;

    const segments = meeting.agentResponses.map((agent) => {
      const speakerName = language === 'ar' ? agent.nameAr : agent.nameEn;
      const role = language === 'ar' ? agent.roleAr : agent.roleEn;
      const body = language === 'ar' ? agent.summaryAr : agent.summaryEn;
      return {
        speakerLabel: speakerName,
        lang: language,
        text: `${speakerName}، ${role}. ${body}`,
      };
    });

    const chiefLabel =
      language === 'ar' ? 'كبير الاستراتيجيين — التوصية الختامية' : 'Chief Strategist — Final Decision';
    const finalHeadline =
      language === 'ar'
        ? meeting.finalRecommendation.headlineAr
        : meeting.finalRecommendation.headlineEn;
    const finalAction =
      language === 'ar'
        ? meeting.finalRecommendation.actionableSummaryAr
        : meeting.finalRecommendation.actionableSummaryEn;

    segments.push({
      speakerLabel: chiefLabel,
      lang: language,
      text: `${chiefLabel}: ${finalHeadline}. ${finalAction}`,
    });

    speech.speakSequence(segments);
  };

  const handlePrepareProposal = async () => {
    if (!meeting) return;
    setIsPreparingProposal(true);
    try {
      const rec = meeting.finalRecommendation;
      const side = rec.stance === 'SELL' ? 'SELL' : 'BUY';
      const qty = rec.suggestedQuantity > 0 ? rec.suggestedQuantity : 1;
      await onProposeRecommendedTrade({
        symbol: meeting.symbol,
        side,
        orderType: 'MARKET',
        quantity: qty,
        source: 'TERMINAL',
        rationale: language === 'ar' ? rec.headlineAr : rec.headlineEn,
      });
    } finally {
      setIsPreparingProposal(false);
    }
  };

  return (
    <section
      className="holo-panel"
      data-testid="agent-meeting-room"
      aria-label={language === 'ar' ? 'قاعة اجتماع الوكلاء الحية' : 'Agent Meeting Room'}
      style={{ padding: '1.05rem 1.15rem', display: 'flex', flexDirection: 'column', gap: '0.95rem' }}
    >
      {/* شريط العنوان وأدوات عقد الجلسة والمداولة الصوتية */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Users size={19} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <h2 style={{ margin: 0, fontSize: '1.04rem', fontWeight: 800 }}>
              {language === 'ar' ? 'قاعة اجتماع الوكلاء الحية' : 'Agent Meeting Room'}
            </h2>
            <span className="holo-badge holo-badge-accent tabular-nums">
              {meeting ? meeting.symbol : selectedSymbol}
            </span>
          </div>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {meeting
              ? language === 'ar'
                ? meeting.topicAr
                : meeting.topicEn
              : language === 'ar'
                ? `اعقد جلسة مداولة متعددة الوكلاء لتحليل الفرص والمخاطر الحتمية على ${selectedSymbol}.`
                : `Convene a multi-agent deliberation session to evaluate evidence and risk for ${selectedSymbol}.`}
          </p>
        </div>

        {/* أزرار انعقاد المجلس والمداولة الصوتية */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.45rem' }}>
          <button
            type="button"
            data-testid="convene-council-btn"
            disabled={isLoading}
            onClick={() => {
              void onConveneMeeting(selectedSymbol);
            }}
            className="holo-btn holo-btn-primary"
          >
            <RefreshCw size={15} className={isLoading ? 'pulse-active' : ''} aria-hidden="true" />
            <span>
              {isLoading
                ? language === 'ar'
                  ? 'جاري انعقاد المجلس...'
                  : 'Convening Council...'
                : language === 'ar'
                  ? 'عقد جلسة مداولة فورية'
                  : 'Convene Council'}
            </span>
          </button>

          {meeting && (
            <>
              <button
                type="button"
                data-testid="play-spoken-discussion-btn"
                disabled={!speech.ttsSupported}
                onClick={handlePlayRoundtable}
                className="holo-btn"
              >
                <Volume2 size={15} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
                <span>
                  {language === 'ar' ? 'تشغيل المداولة الصوتية' : 'Play Spoken Discussion'}
                </span>
              </button>

              <button
                type="button"
                data-testid="stop-spoken-discussion-btn"
                disabled={!speech.isSpeaking}
                onClick={() => speech.interruptSpeech()}
                className="holo-btn holo-btn-danger"
              >
                <Square size={14} aria-hidden="true" />
                <span>{language === 'ar' ? 'إيقاف النطق' : 'Stop'}</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* شريط المتحدث الصوتي النشط */}
      {speech.isSpeaking && speech.activeSpeakerLabel && (
        <div
          role="status"
          aria-live="polite"
          className="holo-panel-subtle"
          style={{
            padding: '0.5rem 0.8rem',
            borderColor: 'var(--accent-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.6rem',
            fontSize: '0.82rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Volume2 size={16} className="pulse-active" style={{ color: 'var(--accent-primary)' }} />
            <span>
              {language === 'ar' ? 'يتحدث الآن في القاعة: ' : 'Currently Speaking: '}
              <strong style={{ color: 'var(--accent-primary)' }}>{speech.activeSpeakerLabel}</strong>
            </span>
          </div>
          <button
            type="button"
            onClick={() => speech.interruptSpeech()}
            className="holo-btn"
            style={{ minHeight: '30px', padding: '0.2rem 0.6rem', fontSize: '0.76rem' }}
          >
            {language === 'ar' ? 'مقاطعة فورية' : 'Interrupt'}
          </button>
        </div>
      )}

      {!meeting ? (
        <div
          className="holo-panel-subtle"
          style={{
            padding: '1.35rem 1rem',
            textAlign: 'center',
            color: 'var(--text-secondary)',
            fontSize: '0.86rem',
          }}
        >
          {isLoading
            ? language === 'ar'
              ? 'يقوم الوكلاء المتخصصون الآن بفحص السيولة والزخم الكمي وحدود المخاطر...'
              : 'Specialist AI agents are analyzing orderflow, macro signals, and deterministic risk limits...'
            : language === 'ar'
              ? 'اضغط على «عقد جلسة مداولة فورية» أو اطلب صوتياً/نصياً عقد اجتماع للوكلاء لعرض التحليل الكامل.'
              : 'Click "Convene Council" or ask via voice/text to launch a live multi-agent deliberation.'}
        </div>
      ) : (
        <>
          {/* بطاقات الوكلاء المشاركين (Individual Agent Cards) */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(235px, 1fr))',
              gap: '0.75rem',
            }}
          >
            {meeting.agentResponses.map((agent) => {
              const isAgentSpeaking =
                speech.isSpeaking &&
                (speech.activeSpeakerLabel === agent.nameAr ||
                  speech.activeSpeakerLabel === agent.nameEn);

              return (
                <article
                  key={agent.agentId}
                  data-testid={`agent-card-${agent.agentId}`}
                  className="holo-panel-subtle"
                  style={{
                    padding: '0.8rem 0.9rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.55rem',
                    borderColor: isAgentSpeaking ? 'var(--accent-primary)' : 'var(--border-subtle)',
                    boxShadow: isAgentSpeaking ? 'var(--shadow-glow-strong)' : 'none',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: '0.45rem',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 800, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                        {language === 'ar' ? agent.nameAr : agent.nameEn}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                        {language === 'ar' ? agent.roleAr : agent.roleEn}
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                      <span className={stanceBadgeClass(agent.stance)}>
                        {stanceLabel(agent.stance, language)}
                      </span>
                      <span
                        className={`holo-badge ${
                          agent.status === 'DISSENT'
                            ? 'holo-badge-danger'
                            : agent.status === 'CAUTION'
                              ? 'holo-badge-warning'
                              : 'holo-badge-success'
                        }`}
                        style={{ fontSize: '0.68rem', padding: '0.1rem 0.45rem' }}
                      >
                        {deliberationStatusLabel(agent.status, language)}
                      </span>
                    </div>
                  </div>

                  {/* شريط الثقة والمؤشر الكمي الرئيسي */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '0.74rem',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      <span>{language === 'ar' ? 'درجة الثقة:' : 'Confidence:'}</span>
                      <strong className="tabular-nums">{formatNumber(agent.confidence, 0)}%</strong>
                    </div>
                    <div
                      style={{
                        height: '5px',
                        borderRadius: '999px',
                        background: 'var(--bg-base)',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${Math.max(0, Math.min(100, agent.confidence))}%`,
                          background: 'var(--accent-primary)',
                        }}
                      />
                    </div>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.3rem 0.5rem',
                      borderRadius: '6px',
                      background: 'var(--bg-base)',
                      fontSize: '0.75rem',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)' }}>
                      {language === 'ar' ? agent.keyMetricLabelAr : agent.keyMetricLabelEn}
                    </span>
                    <strong className="tabular-nums" style={{ color: 'var(--accent-secondary)' }}>
                      {agent.keyMetricValue}
                    </strong>
                  </div>

                  <p
                    style={{
                      margin: 0,
                      fontSize: '0.8rem',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.5,
                      flex: 1,
                    }}
                  >
                    {language === 'ar' ? agent.summaryAr : agent.summaryEn}
                  </p>
                </article>
              );
            })}
          </div>

          {/* لوحتا التوافق والاختلاف + الأدلة وعدم اليقين */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))',
              gap: '0.75rem',
            }}
          >
            {/* نقاط الاتفاق والاختلاف */}
            <div
              className="holo-panel-subtle"
              data-testid="consensus-panel"
              style={{ padding: '0.85rem 0.95rem', display: 'flex', flexDirection: 'column', gap: '0.55rem' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 800, fontSize: '0.86rem' }}>
                  <Scale size={16} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
                  <span>
                    {language === 'ar' ? 'مصفوفة التوافق والاختلاف' : 'Agreement & Disagreement'}
                  </span>
                </div>
                <span className="holo-badge holo-badge-accent tabular-nums">
                  {language === 'ar' ? 'توافق ' : 'Consensus '}
                  {formatNumber(meeting.consensus.agreementScorePct, 0)}%
                </span>
              </div>

              <div>
                <div style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--status-success)', marginBottom: '0.2rem' }}>
                  {language === 'ar' ? 'نقاط الاتفاق المشتركة:' : 'Points of Agreement:'}
                </div>
                <ul style={{ margin: 0, paddingInlineStart: '1.15rem', fontSize: '0.79rem', color: 'var(--text-secondary)' }}>
                  {(language === 'ar'
                    ? meeting.consensus.agreementsAr
                    : meeting.consensus.agreementsEn
                  ).map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.2rem' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <div style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--status-warning)', marginBottom: '0.2rem' }}>
                  {language === 'ar' ? 'نقاط التحفظ والاختلاف:' : 'Points of Disagreement:'}
                </div>
                <ul style={{ margin: 0, paddingInlineStart: '1.15rem', fontSize: '0.79rem', color: 'var(--text-secondary)' }}>
                  {(language === 'ar'
                    ? meeting.consensus.disagreementsAr
                    : meeting.consensus.disagreementsEn
                  ).map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '0.2rem' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* الأدلة الداعمة وعدم اليقين */}
            <div
              className="holo-panel-subtle"
              data-testid="evidence-uncertainty-panel"
              style={{ padding: '0.85rem 0.95rem', display: 'flex', flexDirection: 'column', gap: '0.55rem' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 800, fontSize: '0.86rem' }}>
                  <FileSearch size={16} style={{ color: 'var(--accent-tertiary)' }} aria-hidden="true" />
                  <span>
                    {language === 'ar' ? 'الأدلة الكمية ومخاطر عدم اليقين' : 'Evidence & Uncertainty'}
                  </span>
                </div>
                <span className="holo-badge holo-badge-warning tabular-nums">
                  {language === 'ar' ? 'عدم اليقين ' : 'Uncertainty '}
                  {formatNumber(meeting.evidenceAndUncertainty.uncertaintyScorePct, 0)}%
                </span>
              </div>

              <div>
                <div style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.2rem' }}>
                  {language === 'ar' ? 'الأدلة الداعمة المرصودة:' : 'Supporting Evidence:'}
                </div>
                <ul style={{ margin: 0, paddingInlineStart: '1.15rem', fontSize: '0.79rem', color: 'var(--text-secondary)' }}>
                  {(language === 'ar'
                    ? meeting.evidenceAndUncertainty.evidenceAr
                    : meeting.evidenceAndUncertainty.evidenceEn
                  ).map((ev, idx) => (
                    <li key={idx} style={{ marginBottom: '0.2rem' }}>
                      {ev}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <div style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--status-danger)', marginBottom: '0.2rem' }}>
                  {language === 'ar' ? 'عوامل عدم اليقين والحساسية:' : 'Key Uncertainties:'}
                </div>
                <ul style={{ margin: 0, paddingInlineStart: '1.15rem', fontSize: '0.79rem', color: 'var(--text-secondary)' }}>
                  {(language === 'ar'
                    ? meeting.evidenceAndUncertainty.uncertaintiesAr
                    : meeting.evidenceAndUncertainty.uncertaintiesEn
                  ).map((unc, idx) => (
                    <li key={idx} style={{ marginBottom: '0.2rem' }}>
                      {unc}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* شريط التكاليف التقديرية وتقييم المخاطر الحتمي للاجتماع */}
          <div
            className="holo-panel-subtle"
            style={{
              padding: '0.75rem 0.95rem',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
              gap: '0.65rem',
              fontSize: '0.79rem',
            }}
          >
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                {language === 'ar' ? 'إجمالي التكلفة التقديرية' : 'Estimated Trade Cost'}
              </div>
              <strong className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
                {formatCurrency(meeting.estimatedCosts.totalEstimatedCostUsd)} (
                {formatNumber(meeting.estimatedCosts.costBps, 1)} bps)
              </strong>
              <div className="tabular-nums" style={{ fontSize: '0.71rem', color: 'var(--text-muted)' }}>
                Spread {formatCurrency(meeting.estimatedCosts.spreadCostUsd)} • Comm{' '}
                {formatCurrency(meeting.estimatedCosts.commissionUsd)}
              </div>
            </div>

            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                {language === 'ar' ? 'تقييم المخاطر الحتمي' : 'Deterministic Risk Score'}
              </div>
              <strong
                className="tabular-nums"
                style={{
                  color: meeting.riskAssessment.passed
                    ? 'var(--status-success)'
                    : 'var(--status-danger)',
                }}
              >
                {meeting.riskAssessment.riskScore}/100 ({meeting.riskAssessment.riskLevel})
              </strong>
              <div style={{ fontSize: '0.71rem', color: 'var(--text-muted)' }}>
                {meeting.riskAssessment.passed ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--status-success)' }}>
                    <CheckCircle2 size={12} />
                    {language === 'ar' ? 'ضمن الحدود الآمنة' : 'Within Safety Limits'}
                  </span>
                ) : (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--status-danger)' }}>
                    <AlertCircle size={12} />
                    {language === 'ar' ? 'يتطلب تخفيض الحجم' : 'Requires Size Reduction'}
                  </span>
                )}
              </div>
            </div>

            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                {language === 'ar' ? 'تأثير VaR 95% اليومي' : 'VaR (95%) Impact'}
              </div>
              <strong className="tabular-nums">
                {formatCurrency(meeting.riskAssessment.varImpactUsd)}
              </strong>
            </div>

            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                {language === 'ar' ? 'التركز بعد التنفيذ' : 'Post-Trade Concentration'}
              </div>
              <strong className="tabular-nums">
                {formatNumber(meeting.riskAssessment.postTradeConcentrationPct, 2)}%
              </strong>
            </div>
          </div>

          {/* التوصية الختامية المجمعة من كبير الاستراتيجيين */}
          <div
            data-testid="final-recommendation-card"
            style={{
              padding: '0.95rem 1.05rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-holo)',
              background: 'rgba(var(--accent-primary-rgb), 0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.6rem',
            }}
          >
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.5rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
                <Gavel size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
                <strong style={{ fontSize: '0.94rem' }}>
                  {language === 'ar'
                    ? meeting.finalRecommendation.headlineAr
                    : meeting.finalRecommendation.headlineEn}
                </strong>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                <span className={stanceBadgeClass(meeting.finalRecommendation.stance)}>
                  {stanceLabel(meeting.finalRecommendation.stance, language)}
                </span>
                <span className="holo-badge tabular-nums">
                  {language === 'ar' ? 'ثقة ' : 'Conf '}
                  {formatNumber(meeting.finalRecommendation.confidence, 0)}%
                </span>
              </div>
            </div>

            <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
              {language === 'ar'
                ? meeting.finalRecommendation.actionableSummaryAr
                : meeting.finalRecommendation.actionableSummaryEn}
            </p>

            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.65rem',
                paddingTop: '0.3rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <ShieldCheck size={15} style={{ color: 'var(--status-success)' }} aria-hidden="true" />
                <span>
                  {language === 'ar'
                    ? `الكمية المقترحة: ${formatNumber(meeting.finalRecommendation.suggestedQuantity, 4)} ${meeting.symbol} — تخضع لفحص المخاطر وتصريح المستخدم الإلزامي.`
                    : `Suggested Qty: ${formatNumber(meeting.finalRecommendation.suggestedQuantity, 4)} ${meeting.symbol} — Subject to mandatory risk & user authorization.`}
                </span>
              </div>

              <button
                type="button"
                data-testid="prepare-authorized-proposal-btn"
                disabled={isPreparingProposal}
                onClick={() => {
                  void handlePrepareProposal();
                }}
                className="holo-btn holo-btn-primary"
              >
                <Send size={15} aria-hidden="true" />
                <span>
                  {isPreparingProposal
                    ? language === 'ar'
                      ? 'جاري التحويل لبوابة التصاريح...'
                      : 'Preparing Proposal...'
                    : language === 'ar'
                      ? 'إرسال التوصية إلى بوابة التصاريح'
                      : 'Prepare Authorized Proposal'}
                </span>
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
};

export default AgentMeetingRoom;
