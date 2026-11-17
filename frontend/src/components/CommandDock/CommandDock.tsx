/**
 * منصة الأوامر الصوتية والنصية الهولوغرامية الدائمة (Voice-First AI Command Dock)
 * My Road to be Trilunair Dr.MaJoOoOoOoD — المواصفة التنفيذية (القسم الخامس)
 *
 * المبادئ المعمارية والأمنية:
 * 1. شريط قيادة سفلي ثابت (z-index: 50) متاح عبر جميع الشاشات مع درج غرفة قيادة قابل للتوسيع والطي.
 * 2. التزام صارم بالخصوصية: لا يتم تشغيل الميكروفون أو التسجيل المستمر بدون إذن صريح من المستخدم،
 *    مع إمكانية إلغاء الإذن فوراً أو إيقاف الاستماع يدوياً في أي لحظة.
 * 3. مؤشر صادق لمزود الصوت الفعلي (Browser Web Speech API أو Text-Only Fallback) دون ادعاء اتصال سحابي غير متحقق منه.
 * 4. مخطط موجات صوتية هولوغرامي حي (Live Voice Waveform) ورسوم نسخ نصي لحظي تحترم تعطيل الحركة ووضع الطاقة المنخفضة.
 * 5. تحكم كامل بإخراج الصوت: كتم الصوت الفوري (Mute TTS)، النطق التلقائي، والمقاطعة الفورية (Interruptible TTS + Escape).
 * 6. قاعدة الأمان الصارمة لكلمة «أكد / confirm»: فتح نافذة ختم التأكيد الهولوغرامي للمقترح المعلق حصراً،
 *    واستحالة تنفيذ أي صفقة بمجرد نطق أو كتابة «أكد» دون مصادقة بشرية صريحة عبر البوابة.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  ChevronUp,
  Cpu,
  Lock,
  Maximize2,
  MessageSquare,
  Mic,
  MicOff,
  Radio,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Square,
  Trash2,
  Unlock,
  Users,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import type {
  AgentProfile,
  ChatMessageRecord,
  CommandSource,
  TradeProposalEvaluation,
} from '../../types/trilunair';
import type { SpeechEngineController } from '../../voice/useSpeechEngine';

export interface CommandDockProps {
  speech: SpeechEngineController;
  agents: AgentProfile[];
  messages: ChatMessageRecord[];
  isSending: boolean;
  onSendCommand: (params: {
    message: string;
    source: CommandSource;
    selectedAgent: string;
    triggerMeeting: boolean;
  }) => Promise<void>;
  onClearHistory: () => Promise<void>;
  onOpenProposalAuth: (evaluation: TradeProposalEvaluation) => void;
  onInspectMeeting: () => void;
  cockpitMode?: boolean;
  onToggleCockpit?: () => void;
}

interface QuickCommandChip {
  id: string;
  labelAr: string;
  labelEn: string;
  commandAr: string;
  commandEn: string;
  forceMeeting?: boolean;
  triggersCockpit?: boolean;
}

/**
 * شرائح الأوامر التنفيذية السريعة المعتمدة في المواصفة الرئيسية (القسم الخامس)
 */
const QUICK_COMMAND_CHIPS: QuickCommandChip[] = [
  {
    id: 'analyze-btc-now',
    labelAr: 'حلل البيتكوين الآن',
    labelEn: 'Analyze Bitcoin Now',
    commandAr: 'حلل البيتكوين الآن',
    commandEn: 'Analyze Bitcoin now',
  },
  {
    id: 'eth-agent-meeting',
    labelAr: 'اعقد اجتماعاً بين الوكلاء لمناقشة الإيثيريوم',
    labelEn: 'Convene Agent Meeting on ETH',
    commandAr: 'اعقد اجتماعاً بين الوكلاء لمناقشة الإيثيريوم',
    commandEn: 'Convene an agent meeting to discuss Ethereum',
    forceMeeting: true,
  },
  {
    id: 'activate-cockpit',
    labelAr: 'فعّل وضع Cockpit',
    labelEn: 'Activate Cockpit Mode',
    commandAr: 'فعّل وضع Cockpit',
    commandEn: 'Activate Cockpit Mode',
    triggersCockpit: true,
  },
  {
    id: 'pause-agents',
    labelAr: 'أوقف الوكلاء مؤقتاً',
    labelEn: 'Pause Agents Temporarily',
    commandAr: 'أوقف الوكلاء مؤقتاً',
    commandEn: 'Pause AI agents temporarily',
  },
  {
    id: 'propose-btc-buy',
    labelAr: 'جهز مقترح شراء BTC',
    labelEn: 'Prepare BTC Buy Proposal',
    commandAr: 'جهز مقترح شراء 0.2 BTC',
    commandEn: 'Prepare a trade proposal to buy 0.2 BTC',
  },
  {
    id: 'theme-obsidian-black',
    labelAr: 'غير الثيم إلى Obsidian Black',
    labelEn: 'Switch Theme to Obsidian Black',
    commandAr: 'غير الثيم إلى Obsidian Black',
    commandEn: 'Switch theme to Obsidian Black',
  },
  {
    id: 'compare-assets',
    labelAr: 'قارن بين BTC و XAU و NVDA',
    labelEn: 'Compare BTC, XAU & NVDA',
    commandAr: 'قارن بين BTC و XAU و NVDA',
    commandEn: 'Compare BTC, XAU, and NVDA',
  },
  {
    id: 'portfolio-path',
    labelAr: 'اشرح أداء المحفظة ومسار التريليون',
    labelEn: 'Portfolio & Trilunair Path',
    commandAr: 'اشرح أداء المحفظة ومسار التريليون',
    commandEn: 'Explain portfolio performance and the Trilunair path',
  },
];

/**
 * قائمة احتياطية للوكلاء في حال عدم اكتمال تحميلهم بعد من الخادم
 */
const FALLBACK_AGENTS: Array<{ agentId: string; nameAr: string; nameEn: string }> = [
  { agentId: 'quant-alpha', nameAr: 'ألفا الكمي (Quant Alpha)', nameEn: 'Quant Alpha' },
  { agentId: 'risk-sentinel', nameAr: 'حارس المخاطر (Risk Sentinel)', nameEn: 'Risk Sentinel' },
  { agentId: 'macro-oracle', nameAr: 'عرّاف الماكرو (Macro Oracle)', nameEn: 'Macro Oracle' },
  {
    agentId: 'execution-architect',
    nameAr: 'مهندس التنفيذ (Execution Architect)',
    nameEn: 'Execution Architect',
  },
];

/**
 * أبعاد الأعمدة الأساسية لمخطط الموجات الصوتية الهولوغرامية (12 عموداً متوازناً)
 */
const WAVEFORM_BARS: Array<{ base: number; peak: number; dur: string }> = [
  { base: 5, peak: 14, dur: '0.72s' },
  { base: 8, peak: 20, dur: '0.58s' },
  { base: 12, peak: 22, dur: '0.84s' },
  { base: 7, peak: 17, dur: '0.64s' },
  { base: 14, peak: 23, dur: '0.52s' },
  { base: 10, peak: 21, dur: '0.76s' },
  { base: 15, peak: 24, dur: '0.60s' },
  { base: 9, peak: 19, dur: '0.88s' },
  { base: 13, peak: 22, dur: '0.56s' },
  { base: 7, peak: 16, dur: '0.79s' },
  { base: 11, peak: 18, dur: '0.67s' },
  { base: 6, peak: 13, dur: '0.74s' },
];

/**
 * فحص ما إذا كان الأمر المنطوق أو المكتوب هو أمر التأكيد «أكد / confirm»
 */
function isConfirmIntent(rawText: string): boolean {
  const normalized = rawText
    .trim()
    .replace(/[.!؟?,،"«»']/g, '')
    .replace(/\s+/g, ' ')
    .toLowerCase();

  return (
    normalized === 'أكد' ||
    normalized === 'اكد' ||
    normalized === 'أكّد' ||
    normalized === 'تأكيد' ||
    normalized === 'تاكيد' ||
    normalized === 'أكد الأمر' ||
    normalized === 'اكد الامر' ||
    normalized === 'أكد الصفقة' ||
    normalized === 'اكد الصفقة' ||
    normalized === 'confirm' ||
    normalized === 'confirm order' ||
    normalized === 'confirm trade'
  );
}

/**
 * تنسيق المبالغ المالية بدقة جدولية واضحة
 */
function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * تنسيق الطابع الزمني للرسائل
 */
function formatTime(iso: string): string {
  try {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

/**
 * مكون المخطط الموجي الصوتي الهولوغرامي الحي (Live Voice Waveform Visualizer)
 * يتفاعل ديناميكياً أثناء الاستماع أو النطق، ويبقى ساكناً تماماً عند تفعيل تعطيل الحركة أو وضع الطاقة المنخفضة.
 */
const VoiceWaveformVisualizer: React.FC<{
  isListening: boolean;
  isSpeaking: boolean;
  isMuted: boolean;
  motionReduced: boolean;
  isAr: boolean;
  compact?: boolean;
}> = ({ isListening, isSpeaking, isMuted, motionReduced, isAr, compact = false }) => {
  const activeSpeaking = isSpeaking && !isMuted;
  const shouldAnimate = (isListening || activeSpeaking) && !motionReduced;

  const barFill = isListening
    ? 'var(--status-success)'
    : activeSpeaking
      ? 'var(--accent-primary)'
      : 'var(--text-muted)';

  const label = isListening
    ? isAr
      ? 'موجات صوتية نشطة: جاري الاستماع'
      : 'Active voice waveform: listening'
    : activeSpeaking
      ? isAr
        ? 'موجات صوتية نشطة: جاري نطق الرد'
        : 'Active voice waveform: speaking'
      : isAr
        ? 'مخطط الموجات الصوتية في وضع السكون'
        : 'Voice waveform idle';

  const svgWidth = compact ? 52 : 68;
  const svgHeight = compact ? 22 : 26;

  return (
    <div
      role="img"
      aria-label={label}
      className="holo-panel-subtle"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: compact ? '0.2rem 0.45rem' : '0.3rem 0.55rem',
        height: compact ? '32px' : '44px',
        borderColor:
          isListening || activeSpeaking ? 'var(--border-holo)' : 'var(--border-subtle)',
        flexShrink: 0,
      }}
    >
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox="0 0 60 26"
        fill="none"
        aria-hidden="true"
        style={{ display: 'block' }}
      >
        {WAVEFORM_BARS.map((bar, idx) => {
          const x = idx * 5 + 1;
          const restHeight = isListening || activeSpeaking ? Math.max(bar.base, 10) : bar.base;
          const restY = (26 - restHeight) / 2;
          const peakY = (26 - bar.peak) / 2;

          return (
            <rect
              key={idx}
              x={x}
              y={restY}
              width="3"
              height={restHeight}
              rx="1.5"
              fill={barFill}
              opacity={isListening || activeSpeaking ? 0.95 : 0.45}
            >
              {shouldAnimate && (
                <>
                  <animate
                    attributeName="height"
                    values={`${bar.base};${bar.peak};${bar.base}`}
                    dur={bar.dur}
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="y"
                    values={`${(26 - bar.base) / 2};${peakY};${(26 - bar.base) / 2}`}
                    dur={bar.dur}
                    repeatCount="indefinite"
                  />
                </>
              )}
            </rect>
          );
        })}
      </svg>
    </div>
  );
};

/**
 * بطاقة التقييم المهيكل للمخاطر والتكلفة وبوابة التصريح البشري الإلزامي
 */
const ProposalEvaluationCard: React.FC<{
  evaluation: TradeProposalEvaluation;
  isAr: boolean;
  onOpenAuth: (evaluation: TradeProposalEvaluation) => void;
}> = ({ evaluation, isAr, onOpenAuth }) => {
  const { proposal, estimatedCosts, riskAssessment, status, tradingMode } = evaluation;
  const isApprovedForAuth = status === 'APPROVED_FOR_AUTH' && riskAssessment.passed;
  const isBuy = proposal.side === 'BUY';

  const riskBadgeClass = useMemo(() => {
    if (riskAssessment.riskLevel === 'LOW') return 'holo-badge holo-badge-success';
    if (riskAssessment.riskLevel === 'MODERATE') return 'holo-badge holo-badge-warning';
    return 'holo-badge holo-badge-danger';
  }, [riskAssessment.riskLevel]);

  return (
    <div
      className="holo-panel-subtle"
      role="region"
      aria-label={
        isAr
          ? `بطاقة تصريح ومخاطر مقترح التداول ${proposal.symbol}`
          : `Trade proposal risk and authorization card for ${proposal.symbol}`
      }
      style={{
        marginTop: '0.75rem',
        padding: '0.85rem',
        border: '1px solid var(--border-holo)',
        background: 'color-mix(in srgb, var(--bg-base) 74%, var(--bg-surface))',
      }}
    >
      {/* ترويسة المقترح وحالة فحص المخاطر */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          marginBottom: '0.65rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {isApprovedForAuth ? (
            <ShieldCheck size={18} style={{ color: 'var(--status-success)' }} aria-hidden="true" />
          ) : (
            <ShieldAlert size={18} style={{ color: 'var(--status-danger)' }} aria-hidden="true" />
          )}
          <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>
            {isAr ? 'مقترح أمر مهيكل بانتظار التصريح' : 'Structured Order Proposal (Auth Required)'}
          </strong>
          <span className={isBuy ? 'holo-badge holo-badge-success' : 'holo-badge holo-badge-danger'}>
            {isBuy ? (isAr ? 'شراء / BUY' : 'BUY') : isAr ? 'بيع / SELL' : 'SELL'}
          </span>
          <span className="holo-badge holo-badge-accent tabular-nums">
            {proposal.quantity} {proposal.symbol} ({proposal.orderType})
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
          <span className={riskBadgeClass}>
            {isAr ? 'المخاطر:' : 'Risk:'} {riskAssessment.riskLevel} (
            <span className="tabular-nums">{riskAssessment.riskScore}/100</span>)
          </span>
          <span
            className={
              tradingMode === 'LIVE'
                ? 'holo-badge holo-badge-danger'
                : 'holo-badge holo-badge-accent'
            }
          >
            {tradingMode === 'LIVE'
              ? isAr
                ? 'تداول حقيقي LIVE'
                : 'LIVE MODE'
              : isAr
                ? 'تداول ورقي PAPER'
                : 'PAPER MODE'}
          </span>
        </div>
      </div>

      {/* شبكة الأرقام المالية وتقدير التكاليف */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))',
          gap: '0.55rem',
          marginBottom: '0.7rem',
        }}
      >
        <div className="holo-panel-subtle" style={{ padding: '0.45rem 0.65rem' }}>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            {isAr ? 'السعر المرجعي' : 'Reference Price'}
          </div>
          <div className="tabular-nums" style={{ fontWeight: 700, fontSize: '0.9rem' }}>
            {formatUsd(proposal.referencePrice)}
          </div>
        </div>

        <div className="holo-panel-subtle" style={{ padding: '0.45rem 0.65rem' }}>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            {isAr ? 'القيمة الاسمية (Notional)' : 'Notional Value'}
          </div>
          <div className="tabular-nums" style={{ fontWeight: 700, fontSize: '0.9rem' }}>
            {formatUsd(estimatedCosts.notionalUsd)}
          </div>
        </div>

        <div className="holo-panel-subtle" style={{ padding: '0.45rem 0.65rem' }}>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            {isAr ? 'إجمالي التكلفة التقديرية' : 'Est. Execution Cost'}
          </div>
          <div
            className="tabular-nums"
            style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--accent-primary)' }}
          >
            {formatUsd(estimatedCosts.totalEstimatedCostUsd)} ({estimatedCosts.costBps.toFixed(1)}{' '}
            bps)
          </div>
        </div>

        <div className="holo-panel-subtle" style={{ padding: '0.45rem 0.65rem' }}>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            {isAr ? 'حالة محرك المخاطر' : 'Risk Engine Verdict'}
          </div>
          <div
            style={{
              fontWeight: 700,
              fontSize: '0.84rem',
              color: isApprovedForAuth ? 'var(--status-success)' : 'var(--status-danger)',
            }}
          >
            {isApprovedForAuth
              ? isAr
                ? 'مؤهل للتوقيع (اجتاز الفحص)'
                : 'Passed — Ready for Auth'
              : isAr
                ? 'مرفوض من محرك المخاطر'
                : 'Rejected by Risk Engine'}
          </div>
        </div>
      </div>

      {/* مخالفات المخاطر إن وجدت */}
      {riskAssessment.violations.length > 0 && (
        <div
          style={{
            marginBottom: '0.65rem',
            padding: '0.45rem 0.65rem',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--status-danger-bg)',
            color: 'var(--status-danger)',
            fontSize: '0.8rem',
          }}
        >
          {riskAssessment.violations.join(' • ')}
        </div>
      )}

      {/* شريط الحوكمة وقاعدة كلمة «أكد» وزر فتح بوابة التصاريح */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.6rem',
        }}
      >
        <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
          {isAr
            ? 'قاعدة الأمان: قول أو كتابة «أكد» يفتح نافذة ختم التأكيد الهولوغرامي فقط ولا يُنفذ الصفقة تلقائياً أبداً.'
            : 'Safety Rule: Speaking or typing "أكد / confirm" only opens the Holographic Confirmation Seal and never executes a trade.'}
        </span>

        <button
          type="button"
          className="holo-btn holo-btn-primary"
          onClick={() => onOpenAuth(evaluation)}
          style={{ minHeight: '44px' }}
          aria-label={
            isAr
              ? 'مراجعة وتوقيع التصريح عبر البوابة'
              : 'Review in Authorization Gateway'
          }
        >
          <ShieldCheck size={16} aria-hidden="true" />
          <span>
            {isAr
              ? 'مراجعة وتوقيع التصريح عبر البوابة'
              : 'Review in Authorization Gateway'}
          </span>
        </button>
      </div>
    </div>
  );
};

/**
 * المكون الرئيسي لمنصة الأوامر الصوتية والنصية الدائمة (CommandDock)
 */
export const CommandDock: React.FC<CommandDockProps> = ({
  speech,
  agents,
  messages,
  isSending,
  onSendCommand,
  onClearHistory,
  onOpenProposalAuth,
  onInspectMeeting,
  cockpitMode,
  onToggleCockpit,
}) => {
  const { language, activeState } = useTheme();
  const isAr = language === 'ar';

  const motionReduced =
    activeState.modifiers.motionDisabled ||
    activeState.modifiers.lowPowerMode ||
    activeState.modifiers.animationIntensity === 0;

  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [textInput, setTextInput] = useState<string>('');
  const [selectedAgent, setSelectedAgent] = useState<string>('team');
  const [triggerMeeting, setTriggerMeeting] = useState<boolean>(false);
  const [isAuthorizingMic, setIsAuthorizingMic] = useState<boolean>(false);
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [isVoiceMuted, setIsVoiceMuted] = useState<boolean>(false);
  const [manualConfirmNotice, setManualConfirmNotice] = useState<{
    symbol: string | null;
    hasProposal: boolean;
  } | null>(null);

  const prevAutoSpeakRef = useRef<boolean>(speech.autoSpeakResponses);
  const processedConfirmMsgIdsRef = useRef<Set<string>>(
    new Set(messages.map((m) => m.id))
  );
  const historyEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const agentOptions = useMemo(() => {
    if (agents.length > 0) {
      return agents.map((a) => ({
        agentId: a.agentId,
        nameAr: `${a.nameAr} — ${a.roleAr}`,
        nameEn: `${a.nameEn} — ${a.roleEn}`,
      }));
    }
    return FALLBACK_AGENTS;
  }, [agents]);

  /**
   * استخراج أحدث مقترح صفقة معلق في سجل الجلسة لربطه بقاعدة كلمة «أكد / confirm»
   */
  const latestPendingProposal = useMemo<TradeProposalEvaluation | null>(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const candidate = messages[i]?.tradeProposalEvaluation;
      if (candidate) {
        return candidate;
      }
    }
    return null;
  }, [messages]);

  /**
   * التحقق مما إذا كانت آخر رسالة مستخدم منطوقة هي كلمة «أكد / confirm» لعرض تنبيه ختم التأكيد الهولوغرامي
   */
  const latestSpokenConfirmSymbol = useMemo<string | null>(() => {
    if (!latestPendingProposal) return null;
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const msg = messages[i];
      if (msg && msg.role === 'user') {
        if (isConfirmIntent(msg.contentAr) || isConfirmIntent(msg.contentEn)) {
          return latestPendingProposal.proposal.symbol;
        }
        break;
      }
    }
    return null;
  }, [latestPendingProposal, messages]);

  // رصد كلمة «أكد / confirm» المنطوقة صوتياً وفتح نافذة ختم التأكيد الهولوغرامي تلقائياً دون تنفيذ الصفقة!
  useEffect(() => {
    for (const msg of messages) {
      if (processedConfirmMsgIdsRef.current.has(msg.id)) {
        continue;
      }
      processedConfirmMsgIdsRef.current.add(msg.id);

      if (
        msg.role === 'user' &&
        (isConfirmIntent(msg.contentAr) || isConfirmIntent(msg.contentEn)) &&
        latestPendingProposal
      ) {
        onOpenProposalAuth(latestPendingProposal);
      }
    }
  }, [latestPendingProposal, messages, onOpenProposalAuth]);

  // ضمان كتم أي نطق صوتي فوراً في حال كان وضع كتم الصوت مفعلاً
  useEffect(() => {
    if (isVoiceMuted && speech.isSpeaking) {
      speech.interruptSpeech();
    }
  }, [isVoiceMuted, speech]);

  // تمرير تلقائي لآخر رسالة عند فتح الدرج أو وصول رد جديد
  useEffect(() => {
    if (isExpanded && historyEndRef.current) {
      historyEndRef.current.scrollIntoView({
        behavior: motionReduced ? 'auto' : 'smooth',
        block: 'end',
      });
    }
  }, [messages.length, isExpanded, motionReduced]);

  // دعم مفتاح Escape لمقاطعة النطق الصوتي فوراً أو إيقاف الاستماع أو طي درج الأوامر
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (speech.isSpeaking) {
        event.preventDefault();
        speech.interruptSpeech();
      } else if (speech.isListening) {
        event.preventDefault();
        speech.stopListening();
      } else if (manualConfirmNotice) {
        event.preventDefault();
        setManualConfirmNotice(null);
      } else if (isExpanded) {
        event.preventDefault();
        setIsExpanded(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [speech, isExpanded, manualConfirmNotice]);

  /**
   * تبديل حالة كتم إخراج الصوت (Mute Voice Output / Mute TTS)
   */
  const handleToggleMuteOutput = useCallback(() => {
    if (!isVoiceMuted) {
      prevAutoSpeakRef.current = speech.autoSpeakResponses;
      speech.interruptSpeech();
      speech.setAutoSpeakResponses(false);
      setIsVoiceMuted(true);
    } else {
      setIsVoiceMuted(false);
      speech.setAutoSpeakResponses(prevAutoSpeakRef.current ?? true);
    }
  }, [isVoiceMuted, speech]);

  /**
   * تبديل النطق التلقائي للردود مع إلغاء الكتم تلقائياً إذا قام المستخدم بتفعيله
   */
  const handleToggleAutoSpeak = useCallback(() => {
    const next = !speech.autoSpeakResponses;
    if (next && isVoiceMuted) {
      setIsVoiceMuted(false);
    }
    speech.setAutoSpeakResponses(next);
    prevAutoSpeakRef.current = next;
  }, [isVoiceMuted, speech]);

  /**
   * تحديد شارة حالة الميكروفون المرئية بوضوح في كل لحظة
   */
  const micStatusBadge = useMemo(() => {
    if (speech.status === 'error' || (speech.errorMessage && !speech.voiceAuthorized)) {
      return {
        label: isAr ? 'تنبيه الميكروفون' : 'Mic Alert',
        className: 'holo-badge holo-badge-danger',
      };
    }
    if (speech.isSpeaking || speech.status === 'speaking') {
      return {
        label: isAr ? 'ينطق الرد...' : 'Speaking...',
        className: 'holo-badge holo-badge-accent pulse-active',
      };
    }
    if (speech.isListening || speech.status === 'listening') {
      return {
        label: isAr ? 'يستمع الآن...' : 'Listening Now...',
        className: 'holo-badge holo-badge-success pulse-active',
      };
    }
    if (speech.voiceAuthorized) {
      return {
        label: isAr ? 'جاهز للاستماع' : 'Ready to Listen',
        className: 'holo-badge holo-badge-success',
      };
    }
    return {
      label: isAr ? 'غير مصرح / مغلق' : 'Unauthorized / Off',
      className: 'holo-badge',
    };
  }, [
    isAr,
    speech.errorMessage,
    speech.isListening,
    speech.isSpeaking,
    speech.status,
    speech.voiceAuthorized,
  ]);

  /**
   * مؤشر صادق لمزود الصوت الفعلي (Truthful Voice Provider Indicator)
   */
  const voiceProviderBadge = useMemo(() => {
    if (speech.sttSupported) {
      return {
        label: 'Browser Web Speech API',
        tooltip: isAr
          ? 'محرك التعرف الصوتي المحلي للمتصفح نشط (بدون إرسال صوت سحابي غير مصرح)'
          : 'Verified local browser Web Speech API active (no unverified cloud audio provider)',
        className: 'holo-badge holo-badge-accent',
      };
    }
    return {
      label: 'Text-Only Fallback (Mic/STT Unavailable)',
      tooltip: isAr
        ? 'الوضع النصي الاحتياطي نشط بالكامل — المتصفح لا يدعم Web Speech STT'
        : 'Text-Only Fallback active — Web Speech STT unavailable in this browser',
      className: 'holo-badge holo-badge-warning',
    };
  }, [isAr, speech.sttSupported]);

  /**
   * طلب الإذن الصريح للميكروفون بناءً على نقرة المستخدم المباشرة فقط
   */
  const handleExplicitMicAuth = useCallback(async () => {
    if (isAuthorizingMic) return;
    setIsAuthorizingMic(true);
    try {
      await speech.requestExplicitMicAuthorization();
    } finally {
      setIsAuthorizingMic(false);
    }
  }, [isAuthorizingMic, speech]);

  /**
   * إرسال أمر نصي مستقل تماماً عن حالة الميكروفون، مع تطبيق قاعدة أمان كلمة «أكد / confirm»
   */
  const handleSendTextCommand = useCallback(
    async (event?: React.FormEvent) => {
      if (event) event.preventDefault();
      const trimmed = textInput.trim();
      if (!trimmed || isSending) return;
      setTextInput('');
      setIsExpanded(true);

      // تطبيق قاعدة الأمان لكلمة «أكد / confirm» قبل أي إرسال
      if (isConfirmIntent(trimmed)) {
        if (latestPendingProposal) {
          setManualConfirmNotice({
            symbol: latestPendingProposal.proposal.symbol,
            hasProposal: true,
          });
          onOpenProposalAuth(latestPendingProposal);
        } else {
          setManualConfirmNotice({
            symbol: null,
            hasProposal: false,
          });
        }
        return;
      }

      setManualConfirmNotice(null);
      await onSendCommand({
        message: trimmed,
        source: 'TEXT',
        selectedAgent,
        triggerMeeting,
      });
    },
    [
      isSending,
      latestPendingProposal,
      onOpenProposalAuth,
      onSendCommand,
      selectedAgent,
      textInput,
      triggerMeeting,
    ]
  );

  /**
   * تنفيذ أمر سريع من شرائح الأوامر المعتمدة في المواصفة الرئيسية
   */
  const handleQuickChipClick = useCallback(
    async (chip: QuickCommandChip) => {
      if (isSending) return;
      setManualConfirmNotice(null);
      if (chip.triggersCockpit && onToggleCockpit && !cockpitMode) {
        onToggleCockpit();
      }
      setIsExpanded(true);
      await onSendCommand({
        message: isAr ? chip.commandAr : chip.commandEn,
        source: 'TEXT',
        selectedAgent,
        triggerMeeting: Boolean(chip.forceMeeting || triggerMeeting),
      });
    },
    [cockpitMode, isAr, isSending, onSendCommand, onToggleCockpit, selectedAgent, triggerMeeting]
  );

  /**
   * مسح سجل المحادثة
   */
  const handleClear = useCallback(async () => {
    if (isClearing || messages.length === 0) return;
    setIsClearing(true);
    setManualConfirmNotice(null);
    try {
      await onClearHistory();
    } finally {
      setIsClearing(false);
    }
  }, [isClearing, messages.length, onClearHistory]);

  /**
   * أحداث زر اضغط للتحدث (Push-to-Talk) للماوس واللمس ولوحة المفاتيح
   */
  const handlePttPressStart = useCallback(() => {
    if (!speech.voiceAuthorized || speech.mode !== 'push-to-talk') return;
    if (!speech.isListening) {
      speech.startListening();
    }
  }, [speech]);

  const handlePttPressEnd = useCallback(() => {
    if (!speech.voiceAuthorized || speech.mode !== 'push-to-talk') return;
    if (speech.isListening) {
      speech.stopListening();
    }
  }, [speech]);

  const activeConfirmSymbol = manualConfirmNotice?.hasProposal
    ? manualConfirmNotice.symbol
    : latestSpokenConfirmSymbol;

  return (
    <aside
      aria-label={
        isAr
          ? 'منصة الأوامر الصوتية والنصية الذكية'
          : 'Voice-First AI Command Dock'
      }
      style={{
        position: 'fixed',
        insetInline: 0,
        bottom: 0,
        zIndex: 50,
        pointerEvents: 'none',
        padding: '0 0.85rem 0.65rem',
      }}
    >
      <div
        style={{
          maxWidth: '1660px',
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
          pointerEvents: 'auto',
        }}
      >
        {/* تنبيه قاعدة أمان كلمة «أكد / confirm» وختم التأكيد الهولوغرامي */}
        {(activeConfirmSymbol || (manualConfirmNotice && !manualConfirmNotice.hasProposal)) && (
          <div
            className="holo-panel"
            role="status"
            aria-live="polite"
            style={{
              padding: '0.6rem 0.95rem',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.7rem',
              borderColor: 'var(--accent-primary)',
              boxShadow: 'var(--shadow-glow-strong)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flex: '1 1 280px' }}>
              <ShieldCheck
                size={19}
                style={{ color: 'var(--accent-primary)', flexShrink: 0 }}
                aria-hidden="true"
              />
              <span style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                {activeConfirmSymbol
                  ? isAr
                    ? `تم رصد كلمة «أكد»: فُتحت نافذة ختم التأكيد الهولوغرامي لمقترح (${activeConfirmSymbol}). تنبيه أمني: كلمة «أكد» لا تُنفذ أي صفقة بمفردها دون مصادقة صريحة داخل البوابة.`
                    : `Detected "أكد / confirm": Opened the Holographic Confirmation Seal for (${activeConfirmSymbol}). Safety Rule: Spoken or typed "أكد" NEVER executes a transaction without explicit gateway authentication.`
                  : isAr
                    ? 'تم رصد كلمة «أكد»: لا يوجد مقترح صفقة معلق حالياً. كلمة «أكد» مخصصة فقط لفتح نافذة ختم التأكيد الهولوغرامي ولا تُنفذ أوامر تلقائياً.'
                    : 'Detected "أكد / confirm": No pending trade proposal found. Spoken/typed "أكد" only opens the Holographic Confirmation Seal and never executes orders directly.'}
              </span>
            </div>

            {latestPendingProposal && (
              <button
                type="button"
                className="holo-btn holo-btn-primary"
                onClick={() => onOpenProposalAuth(latestPendingProposal)}
                style={{ minHeight: '44px', fontSize: '0.8rem' }}
              >
                <ShieldCheck size={15} aria-hidden="true" />
                <span>
                  {isAr ? 'فتح ختم التأكيد الهولوغرامي' : 'Open Holographic Seal'}
                </span>
              </button>
            )}
          </div>
        )}

        {/* شريط المقاطعة الفورية العائم عند قيام المساعد بالنطق الصوتي */}
        {speech.isSpeaking && !isVoiceMuted && (
          <div
            className="holo-panel"
            role="status"
            aria-live="polite"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.75rem',
              padding: '0.55rem 0.95rem',
              borderColor: 'var(--accent-primary)',
              boxShadow: 'var(--shadow-glow-strong)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
              <VoiceWaveformVisualizer
                isListening={false}
                isSpeaking={true}
                isMuted={isVoiceMuted}
                motionReduced={motionReduced}
                isAr={isAr}
                compact={true}
              />
              <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>
                {isAr ? 'يتحدث الآن:' : 'Active Speaker:'}{' '}
                <span style={{ color: 'var(--accent-primary)' }}>
                  {speech.activeSpeakerLabel || (isAr ? 'المجلس الذكي' : 'AI Council')}
                </span>
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="holo-btn"
                onClick={handleToggleMuteOutput}
                style={{ minHeight: '44px' }}
                aria-pressed={isVoiceMuted}
              >
                <VolumeX size={15} aria-hidden="true" />
                <span>{isAr ? 'كتم الصوت / Mute TTS' : 'Mute TTS / كتم الصوت'}</span>
              </button>

              <button
                type="button"
                className="holo-btn holo-btn-danger"
                onClick={speech.interruptSpeech}
                style={{
                  minHeight: '44px',
                  boxShadow: 'var(--shadow-glow-strong)',
                }}
                aria-label={isAr ? 'مقاطعة الصوت فوراً' : 'Interrupt Voice Immediately'}
              >
                <Square size={15} aria-hidden="true" />
                <span>
                  {isAr
                    ? 'مقاطعة الصوت فوراً / Interrupt Voice (Esc)'
                    : 'Interrupt Voice / مقاطعة الصوت فوراً (Esc)'}
                </span>
              </button>
            </div>
          </div>
        )}

        {/* شريط النسخ الهولوغرامي اللحظي أثناء التحدث (Holographic Live Transcription Banner) */}
        {(speech.interimTranscript || speech.isListening) && (
          <div
            className="holo-panel"
            role="status"
            aria-live="polite"
            style={{
              padding: '0.55rem 0.95rem',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.7rem',
              borderColor: 'var(--status-success)',
              boxShadow: 'var(--shadow-holo)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flex: '1 1 260px' }}>
              <VoiceWaveformVisualizer
                isListening={speech.isListening}
                isSpeaking={false}
                isMuted={isVoiceMuted}
                motionReduced={motionReduced}
                isAr={isAr}
                compact={true}
              />

              <span className="holo-badge holo-badge-success">
                <Radio
                  size={12}
                  className={motionReduced ? undefined : 'pulse-active'}
                  aria-hidden="true"
                />
                <span>
                  {isAr ? 'نسخ هولوغرامي حي' : 'Holographic Live STT'} (
                  {speech.recognitionLang === 'ar' ? 'ar-SA' : 'en-US'})
                </span>
              </span>

              <span
                style={{
                  fontWeight: 600,
                  fontSize: '0.92rem',
                  color: speech.interimTranscript ? 'var(--text-primary)' : 'var(--text-muted)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                <span>
                  {speech.interimTranscript ||
                    (isAr
                      ? 'تحدث الآن بوضوح... (مثال: حلل البيتكوين الآن)'
                      : 'Speak clearly now... (e.g., Analyze Bitcoin now)')}
                </span>
                <span
                  aria-hidden="true"
                  className={motionReduced ? undefined : 'pulse-active'}
                  style={{
                    display: 'inline-block',
                    width: '8px',
                    height: '16px',
                    borderRadius: '2px',
                    background: 'var(--accent-primary)',
                  }}
                />
              </span>
            </div>

            {speech.isListening && (
              <button
                type="button"
                className="holo-btn holo-btn-danger"
                onClick={speech.stopListening}
                style={{ minHeight: '44px', fontSize: '0.82rem' }}
                aria-label={isAr ? 'إيقاف الاستماع يدوياً' : 'Stop listening manually'}
              >
                <Square size={14} aria-hidden="true" />
                <span>{isAr ? 'إيقاف الاستماع / Stop Listening' : 'Stop Listening / إيقاف الاستماع'}</span>
              </button>
            )}
          </div>
        )}

        {/* درج غرفة القيادة الهولوغرامية القابل للتوسيع والطي */}
        {isExpanded && (
          <section
            id="holo-command-drawer"
            className="holo-panel"
            aria-label={
              isAr
                ? 'سجل غرفة القيادة وإعدادات الصوت والوكلاء'
                : 'Command Room History & Voice Settings'
            }
            style={{
              display: 'flex',
              flexDirection: 'column',
              maxHeight: 'min(66vh, 590px)',
              overflow: 'hidden',
              background:
                'rgba(var(--bg-surface-rgb), calc(min(0.97, var(--fx-panel-opacity) + 0.14)))',
            }}
          >
            {/* ترويسة الدرج: ضمان الخصوصية + مؤشر المزود الصادق + أدوات السجل */}
            <div
              style={{
                padding: '0.75rem 1rem',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.65rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
                <Sparkles size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
                <strong style={{ fontSize: '0.95rem' }}>
                  {isAr
                    ? 'غرفة القيادة الصوتية ومجلس الوكلاء'
                    : 'Holographic Voice & Agent Command Room'}
                </strong>

                <span className={voiceProviderBadge.className} title={voiceProviderBadge.tooltip}>
                  <Cpu size={12} aria-hidden="true" />
                  <span>{voiceProviderBadge.label}</span>
                </span>

                <span className="holo-badge" title="Zero continuous unauthorized recording">
                  <Lock size={12} aria-hidden="true" />
                  <span>
                    {isAr
                      ? 'لا يتم التسجيل المستمر بدون إذن صريح — No continuous recording without authorization'
                      : 'No continuous recording without authorization — لا يتم التسجيل المستمر بدون إذن صريح'}
                  </span>
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                {onToggleCockpit && (
                  <button
                    type="button"
                    className={cockpitMode ? 'holo-btn holo-btn-primary' : 'holo-btn'}
                    onClick={onToggleCockpit}
                    aria-pressed={Boolean(cockpitMode)}
                    style={{ minHeight: '44px', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
                  >
                    <Maximize2 size={14} aria-hidden="true" />
                    <span>{isAr ? 'وضع Cockpit' : 'Cockpit Mode'}</span>
                  </button>
                )}

                <button
                  type="button"
                  className="holo-btn"
                  onClick={onInspectMeeting}
                  style={{ minHeight: '44px', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
                >
                  <Users size={15} aria-hidden="true" />
                  <span>{isAr ? 'قاعة اجتماع الوكلاء' : 'Agent Meeting Room'}</span>
                </button>

                <button
                  type="button"
                  className="holo-btn"
                  onClick={handleClear}
                  disabled={isClearing || messages.length === 0}
                  style={{ minHeight: '44px', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
                  aria-label={isAr ? 'مسح سجل المحادثة' : 'Clear conversation history'}
                >
                  <Trash2 size={15} aria-hidden="true" />
                  <span>{isAr ? 'مسح السجل' : 'Clear'}</span>
                </button>

                <button
                  type="button"
                  className="holo-btn"
                  onClick={() => setIsExpanded(false)}
                  style={{ minHeight: '44px', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
                  aria-label={isAr ? 'طي غرفة القيادة' : 'Collapse Command Room'}
                >
                  <ChevronDown size={16} aria-hidden="true" />
                  <span>{isAr ? 'طي' : 'Collapse'}</span>
                </button>
              </div>
            </div>

            {/* شريط التحكم المتقدم بالصوت واللغة وكتم الصوت والرد الناطق */}
            <div
              style={{
                padding: '0.65rem 1rem',
                borderBottom: '1px solid var(--border-subtle)',
                background: 'color-mix(in srgb, var(--bg-elevated) 75%, transparent)',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.65rem',
              }}
            >
              {/* تبديل نمط التفاعل الصوتي: PTT مقابل Hands-Free + زر إيقاف الاستماع اليدوي */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                  {isAr ? 'نمط الميكروفون:' : 'Voice Mode:'}
                </span>

                <button
                  type="button"
                  className={
                    speech.mode === 'push-to-talk' ? 'holo-btn holo-btn-primary' : 'holo-btn'
                  }
                  onClick={() => speech.setMode('push-to-talk')}
                  style={{ minHeight: '44px', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                  aria-pressed={speech.mode === 'push-to-talk'}
                >
                  <Mic size={14} aria-hidden="true" />
                  <span>{isAr ? 'اضغط للتحدث (PTT)' : 'Push-to-Talk (PTT)'}</span>
                </button>

                <button
                  type="button"
                  className={speech.mode === 'hands-free' ? 'holo-btn holo-btn-primary' : 'holo-btn'}
                  onClick={() => speech.setMode('hands-free')}
                  style={{ minHeight: '44px', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                  aria-pressed={speech.mode === 'hands-free'}
                >
                  <Radio size={14} aria-hidden="true" />
                  <span>{isAr ? 'محادثة حرة (Hands-Free)' : 'Hands-Free'}</span>
                </button>

                {speech.isListening && (
                  <button
                    type="button"
                    className="holo-btn holo-btn-danger"
                    onClick={speech.stopListening}
                    style={{ minHeight: '44px', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                  >
                    <Square size={14} aria-hidden="true" />
                    <span>{isAr ? 'إيقاف الاستماع' : 'Stop Listening'}</span>
                  </button>
                )}
              </div>

              {/* اختيار لغة التعرف الصوتي + كتم الصوت + النطق التلقائي + إلغاء إذن الميكروفون */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <label
                  htmlFor="dock-stt-lang"
                  style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}
                >
                  {isAr ? 'لغة الاستماع:' : 'STT Lang:'}
                </label>
                <select
                  id="dock-stt-lang"
                  className="holo-select"
                  value={speech.recognitionLang}
                  onChange={(e) => speech.setRecognitionLang(e.target.value === 'en' ? 'en' : 'ar')}
                  style={{ width: 'auto', minHeight: '44px', fontSize: '0.82rem' }}
                  aria-label={isAr ? 'اختيار لغة التعرف الصوتي' : 'Select speech recognition language'}
                >
                  <option value="ar">العربية ar-SA</option>
                  <option value="en">English en-US</option>
                </select>

                <button
                  type="button"
                  className={isVoiceMuted ? 'holo-btn holo-btn-danger' : 'holo-btn'}
                  onClick={handleToggleMuteOutput}
                  style={{ minHeight: '44px', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                  aria-pressed={isVoiceMuted}
                  aria-label={isAr ? 'كتم مخرجات الصوت (Mute TTS)' : 'Mute TTS voice output'}
                >
                  {isVoiceMuted ? (
                    <VolumeX size={15} aria-hidden="true" />
                  ) : (
                    <Volume2 size={15} aria-hidden="true" />
                  )}
                  <span>
                    {isVoiceMuted
                      ? isAr
                        ? 'الصوت مكتوم / Unmute TTS'
                        : 'TTS Muted / Unmute'
                      : isAr
                        ? 'كتم الصوت / Mute TTS'
                        : 'Mute TTS / كتم الصوت'}
                  </span>
                </button>

                <button
                  type="button"
                  className={
                    speech.autoSpeakResponses && !isVoiceMuted
                      ? 'holo-btn holo-badge-accent'
                      : 'holo-btn'
                  }
                  onClick={handleToggleAutoSpeak}
                  style={{ minHeight: '44px', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                  aria-pressed={speech.autoSpeakResponses && !isVoiceMuted}
                >
                  {speech.autoSpeakResponses && !isVoiceMuted ? (
                    <Volume2 size={15} aria-hidden="true" />
                  ) : (
                    <VolumeX size={15} aria-hidden="true" />
                  )}
                  <span>{isAr ? 'نطق الردود تلقائياً' : 'Auto-Speak TTS'}</span>
                </button>

                {speech.voiceAuthorized && (
                  <button
                    type="button"
                    className="holo-btn holo-btn-danger"
                    onClick={speech.revokeMicAuthorization}
                    style={{ minHeight: '44px', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                  >
                    <MicOff size={15} aria-hidden="true" />
                    <span>{isAr ? 'إلغاء إذن الميكروفون' : 'Revoke Mic Permission'}</span>
                  </button>
                )}
              </div>
            </div>

            {/* رسالة تنبيه الميكروفون إن وجدت مع تأكيد استقلالية المحادثة النصية */}
            {speech.errorMessage && (
              <div
                role="alert"
                style={{
                  padding: '0.5rem 1rem',
                  background: 'var(--status-warning-bg)',
                  color: 'var(--status-warning)',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontSize: '0.82rem',
                }}
              >
                <AlertTriangle size={16} aria-hidden="true" />
                <span>{speech.errorMessage}</span>
              </div>
            )}

            {/* شرائح الأوامر السريعة الموسعة (Master Specification Quick Prompts) */}
            <div
              style={{
                padding: '0.55rem 1rem',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                overflowX: 'auto',
              }}
              aria-label={isAr ? 'أوامر سريعة مقترحة' : 'Suggested quick commands'}
            >
              <span
                style={{
                  fontSize: '0.76rem',
                  color: 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                  fontWeight: 600,
                }}
              >
                {isAr ? 'أوامر فورية:' : 'Quick Prompts:'}
              </span>
              {QUICK_COMMAND_CHIPS.map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  className="holo-btn"
                  disabled={isSending}
                  onClick={() => handleQuickChipClick(chip)}
                  style={{
                    minHeight: '44px',
                    padding: '0.3rem 0.7rem',
                    fontSize: '0.78rem',
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                  }}
                >
                  <Sparkles size={13} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
                  <span>{isAr ? chip.labelAr : chip.labelEn}</span>
                </button>
              ))}
            </div>

            {/* سجل المحادثة والبطاقات المهيكلة */}
            <div
              role="log"
              aria-live="polite"
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '0.9rem 1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
              }}
            >
              {messages.length === 0 ? (
                <div
                  className="holo-panel-subtle"
                  style={{
                    padding: '1.25rem',
                    textAlign: 'center',
                    color: 'var(--text-secondary)',
                  }}
                >
                  <Bot
                    size={28}
                    style={{ color: 'var(--accent-primary)', marginBottom: '0.4rem' }}
                    aria-hidden="true"
                  />
                  <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>
                    {isAr
                      ? 'مرحباً د. مجود في مركز القيادة الصوتي والكمي'
                      : 'Welcome Dr. MaJoOoOoOoD to the Voice & Quant Command Center'}
                  </div>
                  <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                    {isAr
                      ? 'اكتب أمرك مباشرة أدناه، أو اختر أمراً فورياً، أو امنح إذن الميكروفون الصريح للتحدث مع فريق الوكلاء (@team). نطق كلمة «أكد» يفتح نافذة ختم التأكيد الهولوغرامي فقط ولا يُنفذ أي صفقة تلقائياً.'
                      : 'Type any command below, pick a quick prompt, or explicitly authorize your microphone to speak with @team. Speaking "أكد / confirm" opens the Holographic Confirmation Seal and never executes a trade by itself.'}
                  </div>
                </div>
              ) : (
                messages.map((msg) => {
                  const isUser = msg.role === 'user';
                  const content = isAr ? msg.contentAr : msg.contentEn;
                  const sender = isAr ? msg.senderNameAr : msg.senderNameEn;

                  return (
                    <article
                      key={msg.id}
                      className="holo-panel-subtle"
                      style={{
                        padding: '0.75rem 0.95rem',
                        alignSelf: isUser ? 'flex-end' : 'stretch',
                        maxWidth: isUser ? 'min(86%, 720px)' : '100%',
                        borderColor: isUser ? 'var(--border-holo)' : 'var(--border-subtle)',
                        background: isUser
                          ? 'color-mix(in srgb, var(--bg-surface) 82%, var(--accent-primary) 14%)'
                          : 'color-mix(in srgb, var(--bg-elevated) 88%, transparent)',
                      }}
                    >
                      {/* رأس الرسالة: المرسل + شارة المصدر (VOICE / TEXT) + الوقت + زر إعادة النطق */}
                      <div
                        style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '0.5rem',
                          marginBottom: '0.4rem',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.45rem',
                            flexWrap: 'wrap',
                          }}
                        >
                          <strong
                            style={{
                              fontSize: '0.83rem',
                              color: isUser ? 'var(--accent-primary)' : 'var(--text-primary)',
                            }}
                          >
                            {sender}
                          </strong>

                          <span
                            className={
                              msg.source === 'VOICE'
                                ? 'holo-badge holo-badge-accent'
                                : 'holo-badge'
                            }
                          >
                            {msg.source === 'VOICE'
                              ? isAr
                                ? 'صوتي / VOICE'
                                : 'VOICE'
                              : msg.source === 'TERMINAL'
                                ? 'TERMINAL'
                                : isAr
                                  ? 'نصي / TEXT'
                                  : 'TEXT'}
                          </span>

                          <span
                            className="tabular-nums"
                            style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}
                          >
                            {formatTime(msg.createdAt)}
                          </span>
                        </div>

                        {/* أزرار الرسالة المساعدة: نطق الرد أو استعراض الاجتماع */}
                        {msg.role === 'assistant' && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            {msg.meetingId && (
                              <button
                                type="button"
                                className="holo-btn"
                                onClick={onInspectMeeting}
                                style={{
                                  minHeight: '44px',
                                  padding: '0.25rem 0.65rem',
                                  fontSize: '0.76rem',
                                }}
                              >
                                <Users size={13} aria-hidden="true" />
                                <span>{isAr ? 'تفاصيل الاجتماع' : 'Inspect Meeting'}</span>
                              </button>
                            )}

                            {speech.ttsSupported && (
                              <button
                                type="button"
                                className="holo-btn"
                                disabled={isVoiceMuted}
                                onClick={() => {
                                  if (!isVoiceMuted) {
                                    speech.speakText(content, language, sender);
                                  }
                                }}
                                style={{
                                  minHeight: '44px',
                                  padding: '0.25rem 0.65rem',
                                  fontSize: '0.76rem',
                                }}
                                title={
                                  isVoiceMuted
                                    ? isAr
                                      ? 'الصوت مكتوم حالياً — ألغِ كتم الصوت للاستماع'
                                      : 'Voice output is muted — unmute TTS to listen'
                                    : undefined
                                }
                                aria-label={isAr ? 'استماع إلى رد المساعد' : 'Replay assistant response'}
                              >
                                {isVoiceMuted ? (
                                  <VolumeX size={14} aria-hidden="true" />
                                ) : (
                                  <Volume2 size={14} aria-hidden="true" />
                                )}
                                <span>
                                  {isVoiceMuted
                                    ? isAr
                                      ? 'مكتوم'
                                      : 'Muted'
                                    : isAr
                                      ? 'نطق الرد'
                                      : 'Speak'}
                                </span>
                              </button>
                            )}
                          </div>
                        )}
                      </div>

                      {/* نص الرسالة */}
                      <div
                        style={{
                          fontSize: '0.9rem',
                          color: 'var(--text-primary)',
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                        }}
                      >
                        {content}
                      </div>

                      {/* بطاقة تقييم مقترح الصفقة المدمجة إن وجدت */}
                      {msg.tradeProposalEvaluation && (
                        <ProposalEvaluationCard
                          evaluation={msg.tradeProposalEvaluation}
                          isAr={isAr}
                          onOpenAuth={onOpenProposalAuth}
                        />
                      )}
                    </article>
                  );
                })
              )}
              <div ref={historyEndRef} />
            </div>
          </section>
        )}

        {/* الشريط السفلي الدائم (Persistent Command Bar) */}
        <div
          className="holo-panel"
          style={{
            padding: '0.6rem 0.85rem',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '0.55rem',
            background:
              'rgba(var(--bg-surface-rgb), calc(min(0.96, var(--fx-panel-opacity) + 0.14)))',
          }}
        >
          {/* زر توسيع/طي درج المحادثة مع عداد الرسائل */}
          <button
            type="button"
            className="holo-btn"
            onClick={() => setIsExpanded((prev) => !prev)}
            aria-expanded={isExpanded}
            aria-controls="holo-command-drawer"
            style={{ minHeight: '44px', padding: '0.45rem 0.75rem' }}
          >
            <MessageSquare size={16} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <span>{isAr ? 'غرفة القيادة' : 'Command Room'}</span>
            <span className="holo-badge holo-badge-accent tabular-nums">{messages.length}</span>
            {isExpanded ? (
              <ChevronDown size={15} aria-hidden="true" />
            ) : (
              <ChevronUp size={15} aria-hidden="true" />
            )}
          </button>

          {/* شارة حالة الميكروفون الحية + مؤشر المزود الصادق + المخطط الموجي الحي */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
            <div role="status" aria-live="polite" className={micStatusBadge.className}>
              {speech.voiceAuthorized ? (
                <Unlock size={12} aria-hidden="true" />
              ) : (
                <Lock size={12} aria-hidden="true" />
              )}
              <span>{micStatusBadge.label}</span>
            </div>

            <span className={voiceProviderBadge.className} title={voiceProviderBadge.tooltip}>
              <Cpu size={12} aria-hidden="true" />
              <span>{voiceProviderBadge.label}</span>
            </span>

            <VoiceWaveformVisualizer
              isListening={speech.isListening}
              isSpeaking={speech.isSpeaking}
              isMuted={isVoiceMuted}
              motionReduced={motionReduced}
              isAr={isAr}
            />
          </div>

          {/* التحكم بالميكروفون: طلب إذن صريح أولاً أو تشغيل PTT / Hands-Free + زر إيقاف الاستماع اليدوي */}
          {!speech.voiceAuthorized ? (
            <button
              type="button"
              className="holo-btn"
              onClick={handleExplicitMicAuth}
              disabled={isAuthorizingMic}
              style={{ minHeight: '44px' }}
              title={
                isAr
                  ? 'لا يتم التسجيل المستمر بدون إذن صريح — اضغط لتفعيل الميكروفون'
                  : 'No continuous recording without authorization — Click to authorize mic'
              }
              aria-label={
                isAr ? 'منح إذن صريح للميكروفون' : 'Grant explicit microphone permission'
              }
            >
              <MicOff size={16} aria-hidden="true" />
              <span>
                {isAuthorizingMic
                  ? isAr
                    ? 'جاري التحقق...'
                    : 'Authorizing...'
                  : isAr
                    ? 'تفعيل الميكروفون بإذن صريح'
                    : 'Authorize Mic'}
              </span>
            </button>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
              {speech.mode === 'push-to-talk' ? (
                <button
                  type="button"
                  className={
                    speech.isListening
                      ? 'holo-btn holo-btn-buy pulse-active'
                      : 'holo-btn holo-btn-primary'
                  }
                  onMouseDown={handlePttPressStart}
                  onMouseUp={handlePttPressEnd}
                  onMouseLeave={handlePttPressEnd}
                  onTouchStart={(e) => {
                    e.preventDefault();
                    handlePttPressStart();
                  }}
                  onTouchEnd={(e) => {
                    e.preventDefault();
                    handlePttPressEnd();
                  }}
                  onKeyDown={(e) => {
                    if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) {
                      e.preventDefault();
                      handlePttPressStart();
                    }
                  }}
                  onKeyUp={(e) => {
                    if (e.key === ' ' || e.key === 'Enter') {
                      e.preventDefault();
                      handlePttPressEnd();
                    }
                  }}
                  style={{ minHeight: '44px' }}
                  aria-label={
                    isAr
                      ? 'اضغط مطولاً للتحدث (Push-to-Talk)'
                      : 'Hold to speak (Push-to-Talk)'
                  }
                >
                  <Mic size={16} aria-hidden="true" />
                  <span>
                    {speech.isListening
                      ? isAr
                        ? 'أفلت للإرسال...'
                        : 'Release to Send...'
                      : isAr
                        ? 'اضغط للتحدث (PTT)'
                        : 'Hold to Talk (PTT)'}
                  </span>
                </button>
              ) : (
                <button
                  type="button"
                  className={
                    speech.isListening
                      ? 'holo-btn holo-badge-accent pulse-active'
                      : 'holo-btn holo-btn-primary'
                  }
                  onClick={() =>
                    speech.isListening ? speech.stopListening() : speech.startListening()
                  }
                  style={{ minHeight: '44px' }}
                  aria-pressed={speech.isListening}
                  aria-label={
                    speech.isListening
                      ? isAr
                        ? 'المحادثة الحرة نشطة'
                        : 'Hands-free listening active'
                      : isAr
                        ? 'بدء المحادثة الحرة'
                        : 'Start hands-free listening'
                  }
                >
                  <Radio size={16} aria-hidden="true" />
                  <span>
                    {speech.isListening
                      ? isAr
                        ? 'استماع حر نشط'
                        : 'Hands-Free Active'
                      : isAr
                        ? 'بدء محادثة حرة'
                        : 'Start Hands-Free'}
                  </span>
                </button>
              )}

              {/* زر إيقاف الاستماع اليدوي المرئي دائماً طالما الميكروفون يستمع */}
              {speech.isListening && (
                <button
                  type="button"
                  className="holo-btn holo-btn-danger"
                  onClick={speech.stopListening}
                  style={{ minHeight: '44px', padding: '0.45rem 0.75rem' }}
                  aria-label={isAr ? 'إيقاف الاستماع فوراً' : 'Stop listening immediately'}
                >
                  <Square size={14} aria-hidden="true" />
                  <span>{isAr ? 'إيقاف الاستماع' : 'Stop Listening'}</span>
                </button>
              )}

              <button
                type="button"
                className="holo-btn"
                onClick={speech.revokeMicAuthorization}
                style={{ minHeight: '44px', padding: '0.45rem 0.65rem' }}
                title={isAr ? 'إلغاء إذن الميكروفون فوراً' : 'Revoke microphone permission'}
                aria-label={isAr ? 'إلغاء إذن الميكروفون' : 'Revoke microphone permission'}
              >
                <MicOff size={15} aria-hidden="true" />
              </button>
            </div>
          )}

          {/* زر كتم مخرجات الصوت (Mute Voice Output / Mute TTS) في الشريط الدائم */}
          <button
            type="button"
            className={isVoiceMuted ? 'holo-btn holo-btn-danger' : 'holo-btn'}
            onClick={handleToggleMuteOutput}
            aria-pressed={isVoiceMuted}
            style={{ minHeight: '44px', padding: '0.45rem 0.7rem', fontSize: '0.8rem' }}
            title={
              isAr
                ? 'كتم أو تشغيل إخراج الصوت الناطق (Mute TTS)'
                : 'Mute or unmute voice synthesis output (Mute TTS)'
            }
            aria-label={isAr ? 'كتم الصوت (Mute TTS)' : 'Mute TTS'}
          >
            {isVoiceMuted ? (
              <VolumeX size={16} aria-hidden="true" />
            ) : (
              <Volume2 size={16} aria-hidden="true" />
            )}
            <span>{isVoiceMuted ? (isAr ? 'مكتوم' : 'Muted') : isAr ? 'كتم الصوت' : 'Mute TTS'}</span>
          </button>

          {/* محدد الوكيل المستهدف (@team أو وكيل متخصص منفرد) */}
          <select
            className="holo-select"
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            style={{ width: 'auto', maxWidth: '215px', minHeight: '44px', fontSize: '0.84rem' }}
            aria-label={
              isAr ? 'توجيه الأمر إلى وكيل أو الفريق الكامل' : 'Select target AI agent or full team'
            }
          >
            <option value="team">
              {isAr ? '@team — فريق الوكلاء الكامل' : '@team — Full AI Council'}
            </option>
            {agentOptions.map((agent) => (
              <option key={agent.agentId} value={agent.agentId}>
                {isAr ? agent.nameAr : agent.nameEn}
              </option>
            ))}
          </select>

          {/* زر تفعيل عقد اجتماع الوكلاء مع الأمر */}
          <button
            type="button"
            className={triggerMeeting ? 'holo-btn holo-badge-accent' : 'holo-btn'}
            onClick={() => setTriggerMeeting((prev) => !prev)}
            aria-pressed={triggerMeeting}
            style={{ minHeight: '44px', padding: '0.45rem 0.7rem', fontSize: '0.8rem' }}
            title={
              isAr
                ? 'عقد جلسة مداولة وتصويت كاملة للوكلاء عند إرسال الأمر'
                : 'Convene a full multi-agent deliberation session with this command'
            }
          >
            <Users size={15} aria-hidden="true" />
            <span>{isAr ? 'اجتماع الوكلاء' : 'Convene Meeting'}</span>
          </button>

          {/* نموذج الإدخال النصي المستقل تماماً عن الميكروفون */}
          <form
            onSubmit={handleSendTextCommand}
            style={{
              flex: '1 1 250px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              minWidth: '220px',
            }}
          >
            <input
              ref={inputRef}
              type="text"
              className="holo-input"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder={
                isAr
                  ? 'اكتب أمراً فورياً (حلل البيتكوين الآن، فعّل وضع Cockpit، أو اكتب «أكد» لفتح ختم التأكيد)...'
                  : 'Enter command (Analyze Bitcoin now, Activate Cockpit, or "confirm" to open seal)...'
              }
              aria-label={isAr ? 'حقل الأمر النصي' : 'Text command input'}
              style={{ minHeight: '44px', flex: 1 }}
            />

            <button
              type="submit"
              className="holo-btn holo-btn-primary"
              disabled={isSending || !textInput.trim()}
              style={{ minHeight: '44px', padding: '0.45rem 1rem', flexShrink: 0 }}
              aria-label={isAr ? 'إرسال الأمر' : 'Send command'}
            >
              <Send size={16} aria-hidden="true" />
              <span>
                {isSending
                  ? isAr
                    ? 'يعالج...'
                    : 'Sending...'
                  : isAr
                    ? 'إرسال'
                    : 'Send'}
              </span>
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
};

export default CommandDock;
