/**
 * التطبيق الرئيسي لمركز القيادة المالي الهولوغرامي ونظام الأوامر الصوتية بالذكاء الاصطناعي
 * My Road to be Trilunair Dr.MaJoOoOoOoD (QUANTUM AI TRADING COMMAND CENTER)
 *
 * يربط كافة الطبقات والشاشات:
 * 1. قاعة التداول الحية (Live Terminal) المدمج بداخلها قاعة اجتماع الوكلاء (Agent Meeting Room).
 * 2. مركز الذكاء الكمي (Quantum Hub): تأهيل الوكلاء رباعي المستويات، محول Binance Spot، والجدوى الاقتصادية.
 * 3. المحفظة ومسار التريليون (Portfolio & $1T Goal Mode).
 * 4. بوابة التصاريح والأمان المالي (Authorization & Safety Gateway — Paper Trading Default).
 * 5. استوديو السمات الهولوغرامية (Dynamic 6-Preset + Custom Theme Studio).
 * 6. شريط الأوامر الصوتية والنصية المستديم عبر جميع الشاشات (Voice-First AI Command Dock).
 * 7. وضعا قمرة القيادة (Cockpit Mode) والتركيز الأقصى (Focus Mode) بنقرة واحدة أو بأمر صوتي.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  Brain,
  Briefcase,
  Crosshair,
  Gauge,
  Globe,
  Maximize2,
  Minimize2,
  Palette,
  Radio,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { connectMarketStream, trilunairApi } from './api/client';
import { quantumApi } from './api/quantumClient';
import { CommandDock } from './components/CommandDock/CommandDock';
import { GovernanceView, type SwitchTradingModePayload } from './components/Governance/GovernanceView';
import { IntelligenceHubView } from './components/IntelligenceHub/IntelligenceHubView';
import { PortfolioView } from './components/Portfolio/PortfolioView';
import {
  AuthorizationModal,
  type ExecuteOrderConfirmPayload,
} from './components/Terminal/AuthorizationModal';
import { LiveTerminalView } from './components/Terminal/LiveTerminalView';
import { ThemeStudio } from './components/ThemeStudio/ThemeStudio';
import { formatCurrency, formatSignedPct, t } from './i18n/translations';
import { useTheme } from './theme/ThemeContext';
import type {
  AgentMeetingResult,
  AgentProfile,
  AuditLogEntry,
  ChatMessageRecord,
  CommandSource,
  Language,
  MarketAsset,
  MarketCandlesResponse,
  PortfolioSnapshot,
  SystemStatus,
  TradeProposalEvaluation,
  TradeProposalInput,
  UiCommandAction,
} from './types/trilunair';
import { useSpeechEngine } from './voice/useSpeechEngine';

type ExtendedScreen = 'terminal' | 'quantum' | 'portfolio' | 'governance' | 'themes';

export const App: React.FC = () => {
  const {
    language,
    setLanguage,
    allThemes,
    activeState,
    selectTheme,
    updateModifiers,
  } = useTheme();
  const isAr = language === 'ar';

  const [activeScreen, setActiveScreen] = useState<ExtendedScreen>('terminal');
  const [cockpitMode, setCockpitMode] = useState<boolean>(false);
  const [focusMode, setFocusMode] = useState<boolean>(false);

  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [assets, setAssets] = useState<MarketAsset[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTC-USD');
  const [timeframe, setTimeframe] = useState<string>('15m');
  const [candlesData, setCandlesData] = useState<MarketCandlesResponse | null>(null);
  const [isCandlesLoading, setIsCandlesLoading] = useState<boolean>(false);

  const [portfolio, setPortfolio] = useState<PortfolioSnapshot | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [messages, setMessages] = useState<ChatMessageRecord[]>([]);
  const [latestMeeting, setLatestMeeting] = useState<AgentMeetingResult | null>(null);
  const [isMeetingLoading, setIsMeetingLoading] = useState<boolean>(false);

  const [activeEvaluation, setActiveEvaluation] = useState<TradeProposalEvaluation | null>(null);
  const [modalEvaluation, setModalEvaluation] = useState<TradeProposalEvaluation | null>(null);
  const [isProposingOrder, setIsProposingOrder] = useState<boolean>(false);
  const [isExecutingOrder, setIsExecutingOrder] = useState<boolean>(false);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [isSendingCommand, setIsSendingCommand] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [toastNotice, setToastNotice] = useState<string | null>(null);

  const sendVoiceCommandRef = useRef<(text: string, lang: Language) => void>(() => {});

  const speech = useSpeechEngine(language, (finalTranscript, detectedLang) => {
    sendVoiceCommandRef.current(finalTranscript, detectedLang);
  });

  // مزامنة وضعي قمرة القيادة (Cockpit Mode) والتركيز الأقصى (Focus Mode) مع DOM
  useEffect(() => {
    document.documentElement.setAttribute('data-cockpit', cockpitMode ? 'true' : 'false');
  }, [cockpitMode]);

  useEffect(() => {
    document.documentElement.setAttribute('data-focus', focusMode ? 'true' : 'false');
  }, [focusMode]);

  const showToast = useCallback((msg: string) => {
    setToastNotice(msg);
    window.setTimeout(() => {
      setToastNotice((prev) => (prev === msg ? null : prev));
    }, 4500);
  }, []);

  const refreshCoreData = useCallback(async () => {
    try {
      const [statusRes, assetsRes, portfolioRes, agentsRes, historyRes, logsRes] =
        await Promise.all([
          trilunairApi.getSystemStatus(),
          trilunairApi.getAssets(),
          trilunairApi.getPortfolio(),
          trilunairApi.getAgents(),
          trilunairApi.getChatHistory(),
          trilunairApi.getAuditLogs(),
        ]);

      setSystemStatus(statusRes);
      setAssets(assetsRes);
      if (assetsRes.length > 0 && !assetsRes.some((a) => a.symbol === selectedSymbol)) {
        setSelectedSymbol(assetsRes[0].symbol);
      }
      setPortfolio(portfolioRes);
      setAgents(agentsRes);
      setMessages(historyRes.messages || []);
      if (historyRes.latestMeeting) {
        setLatestMeeting(historyRes.latestMeeting);
      }
      setAuditLogs(logsRes);
    } catch {
      // الاحتفاظ بآخر حالة صالحة عند تأخر الاتصال
    }
  }, [selectedSymbol]);

  useEffect(() => {
    void refreshCoreData();
  }, [refreshCoreData]);

  // جلب بيانات الشموع ودفتر الأوامر للأصل المحدد
  useEffect(() => {
    let cancelled = false;
    setIsCandlesLoading(true);
    trilunairApi
      .getCandles(selectedSymbol, timeframe, 90)
      .then((res) => {
        if (!cancelled) {
          setCandlesData(res);
        }
      })
      .catch(() => {
        // تجاهل
      })
      .finally(() => {
        if (!cancelled) {
          setIsCandlesLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedSymbol, timeframe]);

  // الاتصال بالبث المباشر للأسعار عبر WebSocket
  useEffect(() => {
    const disconnect = connectMarketStream(
      (tick) => {
        if (tick.assets?.length) {
          setAssets(tick.assets);
        }
        setPortfolio((prev) =>
          prev
            ? {
                ...prev,
                totalEquity: tick.totalEquity ?? prev.totalEquity,
                dailyPnl: tick.dailyPnl ?? prev.dailyPnl,
                dailyPnlPct: tick.dailyPnlPct ?? prev.dailyPnlPct,
              }
            : prev
        );
      },
      (connected) => setWsConnected(connected)
    );
    return disconnect;
  }, []);

  // تنفيذ إجراءات الواجهة الصادرة عن أوامر الذكاء الاصطناعي الصوتية أو النصية
  const applyUiAction = useCallback(
    (action: UiCommandAction | null | undefined) => {
      if (!action) return;
      switch (action.type) {
        case 'SWITCH_THEME':
          if (typeof action.payload.themeId === 'string') {
            selectTheme(action.payload.themeId);
          }
          break;
        case 'SET_LOW_POWER':
          updateModifiers({ lowPowerMode: Boolean(action.payload.enabled) });
          break;
        case 'SET_HIGH_CONTRAST':
          updateModifiers({ highContrast: Boolean(action.payload.enabled) });
          break;
        case 'SET_MOTION_DISABLED':
          updateModifiers({ motionDisabled: Boolean(action.payload.enabled) });
          break;
        case 'SELECT_SYMBOL':
          if (typeof action.payload.symbol === 'string') {
            setSelectedSymbol(action.payload.symbol);
            setActiveScreen('terminal');
          }
          break;
        case 'NAVIGATE_VIEW':
          if (typeof action.payload.view === 'string') {
            const v = action.payload.view as ExtendedScreen;
            setActiveScreen(v);
          }
          break;
        default:
          break;
      }
    },
    [selectTheme, updateModifiers]
  );

  // معالجة الأوامر الصوتية والنصية محلياً + عبر مجلس الوكلاء على الخادم
  const handleSendCommand = useCallback(
    async (params: {
      message: string;
      source: CommandSource;
      selectedAgent: string;
      triggerMeeting: boolean;
    }) => {
      const normalized = params.message.trim();
      if (!normalized) return;

      const lower = normalized.toLowerCase();

      // دعم فوري لأوامر Cockpit Mode و Focus Mode و Obsidian Black وإيقاف الوكلاء مؤقتاً
      if (lower.includes('cockpit') || normalized.includes('قمرة القيادة')) {
        const turnOff = lower.includes('off') || normalized.includes('إيقاف') || normalized.includes('عطل');
        setCockpitMode(!turnOff);
        showToast(
          !turnOff
            ? isAr
              ? 'تم تفعيل وضع قمرة القيادة الاحترافي (Cockpit Mode).'
              : 'Cockpit Mode activated.'
            : isAr
              ? 'تم إيقاف وضع قمرة القيادة.'
              : 'Cockpit Mode disabled.'
        );
      }
      if (lower.includes('focus mode') || normalized.includes('وضع التركيز')) {
        setFocusMode((prev) => !prev);
      }
      if (lower.includes('obsidian') || normalized.includes('أوبسيديان') || normalized.includes('الأسود النقي')) {
        selectTheme('obsidian-black');
      }
      if (
        normalized.includes('أوقف الوكلاء') ||
        lower.includes('pause agents') ||
        lower.includes('stop agents')
      ) {
        quantumApi.setAgentsPaused(true).catch(() => {});
        showToast(isAr ? 'تم إيقاف الوكلاء مؤقتاً بأمر المسؤول.' : 'Agents paused temporarily.');
      }

      setIsSendingCommand(true);
      try {
        const res = await trilunairApi.sendAiCommand({
          message: normalized,
          language,
          source: params.source,
          selectedAgent: params.selectedAgent,
          triggerMeeting: params.triggerMeeting,
        });

        setMessages((prev) => [...prev, res.userMessage, res.assistantMessage]);
        if (res.uiAction) {
          applyUiAction(res.uiAction);
        }
        if (res.meeting) {
          setLatestMeeting(res.meeting);
        }
        if (res.tradeProposalEvaluation) {
          setActiveEvaluation(res.tradeProposalEvaluation);
          // نعرض مقترح الصفقة دون تنفيذ تلقائي التزاماً ببوابة التصاريح الحتمية!
        }

        if (speech.autoSpeakResponses) {
          const replyText =
            language === 'ar' ? res.assistantMessage.contentAr : res.assistantMessage.contentEn;
          const speaker =
            language === 'ar'
              ? res.assistantMessage.senderNameAr
              : res.assistantMessage.senderNameEn;
          speech.speakText(replyText, language, speaker);
        }

        const logs = await trilunairApi.getAuditLogs();
        setAuditLogs(logs);
      } catch (err) {
        showToast(err instanceof Error ? err.message : 'Command error');
      } finally {
        setIsSendingCommand(false);
      }
    },
    [applyUiAction, isAr, language, selectTheme, showToast, speech]
  );

  useEffect(() => {
    sendVoiceCommandRef.current = (finalTranscript: string) => {
      void handleSendCommand({
        message: finalTranscript,
        source: 'VOICE',
        selectedAgent: 'team',
        triggerMeeting: true,
      });
    };
  }, [handleSendCommand]);

  const handleClearHistory = useCallback(async () => {
    await trilunairApi.clearChatHistory();
    setMessages([]);
  }, []);

  const handleProposeOrder = useCallback(
    async (proposal: TradeProposalInput): Promise<TradeProposalEvaluation | void> => {
      setIsProposingOrder(true);
      setExecutionError(null);
      try {
        const evaluation = await trilunairApi.proposeOrder(proposal);
        setActiveEvaluation(evaluation);
        const logs = await trilunairApi.getAuditLogs();
        setAuditLogs(logs);
        return evaluation;
      } catch (err) {
        showToast(err instanceof Error ? err.message : 'Order validation error');
      } finally {
        setIsProposingOrder(false);
      }
    },
    [showToast]
  );

  const handleConfirmExecution = useCallback(
    async (payload: ExecuteOrderConfirmPayload) => {
      setIsExecutingOrder(true);
      setExecutionError(null);
      try {
        const result = await trilunairApi.executeOrder(payload);
        setPortfolio(result.portfolio);
        setModalEvaluation(null);
        setActiveEvaluation(null);
        showToast(
          isAr
            ? `تم تنفيذ الأمر (${result.order.side} ${result.order.quantity} ${result.order.symbol}) في وضع ${result.order.tradingMode}`
            : `Executed ${result.order.side} ${result.order.quantity} ${result.order.symbol} (${result.order.tradingMode})`
        );
        const logs = await trilunairApi.getAuditLogs();
        setAuditLogs(logs);
      } catch (err) {
        setExecutionError(err instanceof Error ? err.message : 'Execution rejected');
      } finally {
        setIsExecutingOrder(false);
      }
    },
    [isAr, showToast]
  );

  const handleConveneMeeting = useCallback(
    async (symbol: string) => {
      setIsMeetingLoading(true);
      try {
        const meeting = await trilunairApi.conveneAgentMeeting({
          symbol,
          horizon: timeframe,
          language,
        });
        setLatestMeeting(meeting);
      } catch (err) {
        showToast(err instanceof Error ? err.message : 'Meeting error');
      } finally {
        setIsMeetingLoading(false);
      }
    },
    [language, showToast, timeframe]
  );

  const handleSwitchTradingMode = useCallback(
    async (payload: SwitchTradingModePayload) => {
      const status = await trilunairApi.setTradingMode(payload);
      setSystemStatus(status);
      const [port, logs] = await Promise.all([
        trilunairApi.getPortfolio(),
        trilunairApi.getAuditLogs(),
      ]);
      setPortfolio(port);
      setAuditLogs(logs);
    },
    []
  );

  const handleToggleKillSwitch = useCallback(async (active: boolean, reason: string) => {
    const status = await trilunairApi.setKillSwitch(active, reason);
    setSystemStatus(status);
    const logs = await trilunairApi.getAuditLogs();
    setAuditLogs(logs);
  }, []);

  const tradingMode = systemStatus?.tradingMode ?? 'PAPER';
  const killSwitchActive = systemStatus?.killSwitchActive ?? false;

  return (
    <div className="app-shell">
      {/* شريط القيادة العلوي (Top Holographic Command Bar) */}
      <header className="top-command-bar" role="banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background:
                'linear-gradient(135deg, var(--accent-primary), color-mix(in srgb, var(--accent-secondary) 65%, transparent))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#05070c',
              fontWeight: 800,
              fontSize: '1.1rem',
              boxShadow: 'var(--shadow-glow-strong)',
            }}
            aria-hidden="true"
          >
            ₮
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.01em' }}>
              {t(language, 'brandTitle')}
            </h1>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {t(language, 'brandSubtitle')}
            </div>
          </div>
        </div>

        {/* التبويبات الرئيسية للشاشات الخمس */}
        <nav
          aria-label={isAr ? 'التنقل الرئيسي' : 'Primary Navigation'}
          style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}
        >
          <button
            id="nav-terminal-btn"
            type="button"
            className={`holo-btn ${activeScreen === 'terminal' ? 'holo-btn-primary' : ''}`}
            onClick={() => setActiveScreen('terminal')}
          >
            <Activity size={15} />
            {t(language, 'navTerminal')}
          </button>

          <button
            id="nav-quantum-btn"
            type="button"
            className={`holo-btn ${activeScreen === 'quantum' ? 'holo-btn-primary' : ''}`}
            onClick={() => {
              setFocusMode(false);
              setActiveScreen('quantum');
            }}
          >
            <Brain size={15} />
            {isAr ? 'مركز الذكاء الكمي و Binance' : 'Quantum Hub & Binance'}
          </button>

          <button
            id="nav-portfolio-btn"
            type="button"
            className={`holo-btn ${activeScreen === 'portfolio' ? 'holo-btn-primary' : ''}`}
            onClick={() => {
              setFocusMode(false);
              setActiveScreen('portfolio');
            }}
          >
            <Briefcase size={15} />
            {t(language, 'navPortfolio')}
          </button>

          <button
            id="nav-governance-btn"
            type="button"
            className={`holo-btn ${activeScreen === 'governance' ? 'holo-btn-primary' : ''}`}
            onClick={() => {
              setFocusMode(false);
              setActiveScreen('governance');
            }}
          >
            <ShieldCheck size={15} />
            {t(language, 'navGovernance')}
          </button>

          <button
            id="nav-themes-btn"
            type="button"
            className={`holo-btn ${activeScreen === 'themes' ? 'holo-btn-primary' : ''}`}
            onClick={() => {
              setFocusMode(false);
              setActiveScreen('themes');
            }}
          >
            <Palette size={15} />
            {t(language, 'navThemes')}
          </button>
        </nav>

        {/* شارات الأمان + أزرار Cockpit Mode و Focus Mode ومبدل السمات واللغة */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.45rem' }}>
          {killSwitchActive ? (
            <span className="holo-badge holo-badge-danger">
              <ShieldAlert size={13} />
              {t(language, 'killSwitchActive')}
            </span>
          ) : (
            <span
              className={`holo-badge ${
                tradingMode === 'PAPER' ? 'holo-badge-success' : 'holo-badge-warning'
              }`}
            >
              <ShieldCheck size={13} />
              {tradingMode === 'PAPER'
                ? t(language, 'paperModeBadge')
                : t(language, 'liveModeBadge')}
            </span>
          )}

          <span className={`holo-badge ${wsConnected ? 'holo-badge-accent' : ''}`}>
            <Radio size={12} />
            {wsConnected ? t(language, 'streamConnected') : t(language, 'streamOffline')}
          </span>

          {/* زر وضع قمرة القيادة بنقرة واحدة (One-Click Cockpit Mode) */}
          <button
            id="cockpit-mode-toggle"
            type="button"
            className={`holo-btn ${cockpitMode ? 'holo-btn-primary' : ''}`}
            onClick={() => setCockpitMode((prev) => !prev)}
            aria-pressed={cockpitMode}
            title={
              isAr
                ? 'وضع قمرة القيادة: تقليل المؤثرات الزخرفية وزيادة كثافة البيانات وإبراز المخاطر'
                : 'Cockpit Mode: Reduce decorative effects & maximize financial data density'
            }
          >
            <Gauge size={15} />
            {isAr ? 'Cockpit' : 'Cockpit'}
          </button>

          {/* زر وضع التركيز الأقصى (Focus Mode) */}
          <button
            id="focus-mode-toggle"
            type="button"
            className={`holo-btn ${focusMode ? 'holo-btn-primary' : ''}`}
            onClick={() =>
              setFocusMode((prev) => {
                const next = !prev;
                if (next) setActiveScreen('terminal');
                return next;
              })
            }
            aria-pressed={focusMode}
            title={
              isAr
                ? 'وضع التركيز: تكبير قاعة التداول الحية مع إبقاء ضوابط التنفيذ وشريط الأوامر متاحين'
                : 'Focus Mode: Maximize Live Terminal'
            }
          >
            {focusMode ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            {isAr ? 'تركيز' : 'Focus'}
          </button>

          {/* مبدل السمات السريع للسمات الست الأساسية والمخصصة */}
          <select
            id="quick-theme-selector"
            aria-label={t(language, 'quickThemeLabel')}
            className="holo-select"
            style={{ width: 'auto', minHeight: '38px', padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
            value={activeState.activeThemeId}
            onChange={(e) => selectTheme(e.target.value)}
          >
            {allThemes.map((th) => (
              <option key={th.id} value={th.id}>
                {isAr ? th.nameAr : th.nameEn}
              </option>
            ))}
          </select>

          <button
            id="language-dir-toggle"
            type="button"
            className="holo-btn"
            style={{ minHeight: '38px', padding: '0.3rem 0.65rem', fontSize: '0.8rem' }}
            onClick={() => setLanguage(language === 'ar' ? 'en' : 'ar')}
          >
            <Globe size={14} />
            {t(language, 'langToggle')}
          </button>
        </div>
      </header>

      {/* شريط المؤشرات المالية الحية فائقة الوضوح (KPI Ribbon) */}
      <section className="kpi-ribbon" aria-label={isAr ? 'ملخص المؤشرات المالية' : 'Financial KPI Summary'}>
        <div className="holo-panel" style={{ padding: '0.65rem 0.9rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {t(language, 'equityLabel')}
          </div>
          <div className="fin-value" style={{ fontSize: '1.15rem', fontWeight: 800 }}>
            {formatCurrency(portfolio?.totalEquity ?? 1_000_000)}
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.65rem 0.9rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {t(language, 'dailyPnlLabel')}
          </div>
          <div
            className="fin-value"
            style={{
              fontSize: '1.1rem',
              fontWeight: 700,
              color:
                (portfolio?.dailyPnl ?? 0) >= 0 ? 'var(--status-success)' : 'var(--status-danger)',
            }}
          >
            {formatCurrency(portfolio?.dailyPnl ?? 0)} ({formatSignedPct(portfolio?.dailyPnlPct ?? 0)})
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.65rem 0.9rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {t(language, 'cashLabel')}
          </div>
          <div className="fin-value" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
            {formatCurrency(portfolio?.cashBalance ?? 1_000_000)}
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.65rem 0.9rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {t(language, 'varLabel')}
          </div>
          <div
            className="fin-value"
            style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--status-warning)' }}
          >
            {formatCurrency(portfolio?.var95Usd ?? 0)} • DD {(portfolio?.currentDrawdownPct ?? 0).toFixed(2)}%
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.65rem 0.9rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Crosshair size={13} style={{ color: 'var(--accent-primary)' }} />
            {t(language, 'trilunairGoal')}
          </div>
          <div className="fin-value" style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
            $1.00T Target • {activeState.modifiers.lowPowerMode ? 'LOW-POWER' : cockpitMode ? 'COCKPIT' : 'HOLO-ACTIVE'}
          </div>
        </div>
      </section>

      {toastNotice && (
        <div
          role="status"
          aria-live="polite"
          className="holo-panel"
          style={{
            margin: '0.5rem 1.25rem 0',
            padding: '0.6rem 1rem',
            borderColor: 'var(--accent-primary)',
            fontSize: '0.88rem',
          }}
        >
          {toastNotice}
        </div>
      )}

      {/* مساحة العمل الرئيسية للشاشة النشطة */}
      <main className="main-workspace" role="main">
        {activeScreen === 'terminal' && (
          <LiveTerminalView
            assets={assets}
            selectedSymbol={selectedSymbol}
            onSelectSymbol={setSelectedSymbol}
            candlesData={candlesData}
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
            isCandlesLoading={isCandlesLoading}
            portfolio={portfolio}
            tradingMode={tradingMode}
            killSwitchActive={killSwitchActive}
            activeEvaluation={activeEvaluation}
            isProposingOrder={isProposingOrder}
            onProposeOrder={handleProposeOrder}
            onOpenAuthorizationModal={(evalObj) => setModalEvaluation(evalObj)}
            meeting={latestMeeting}
            isMeetingLoading={isMeetingLoading}
            speech={speech}
            onConveneMeeting={handleConveneMeeting}
            onProposeRecommendedTrade={async (prop) => {
              const ev = await handleProposeOrder(prop);
              if (ev) {
                setModalEvaluation(ev);
              }
            }}
          />
        )}

        {activeScreen === 'quantum' && <IntelligenceHubView />}

        {activeScreen === 'portfolio' && (
          <PortfolioView
            portfolio={portfolio}
            assets={assets}
            onSelectSymbolForTerminal={(sym) => {
              setSelectedSymbol(sym);
              setActiveScreen('terminal');
            }}
          />
        )}

        {activeScreen === 'governance' && (
          <GovernanceView
            systemStatus={systemStatus}
            auditLogs={auditLogs}
            onSwitchTradingMode={handleSwitchTradingMode}
            onToggleKillSwitch={handleToggleKillSwitch}
            onRefreshAuditLogs={async () => {
              const logs = await trilunairApi.getAuditLogs();
              setAuditLogs(logs);
            }}
          />
        )}

        {activeScreen === 'themes' && <ThemeStudio />}
      </main>

      {/* نافذة ختم التأكيد الهولوغرامي الموحدة لتصريح الصفقات (VOICE / TEXT / TERMINAL) */}
      <AuthorizationModal
        evaluation={modalEvaluation}
        isOpen={Boolean(modalEvaluation)}
        isExecuting={isExecutingOrder}
        executionError={executionError}
        onClose={() => {
          setModalEvaluation(null);
          setExecutionError(null);
        }}
        onConfirmExecution={handleConfirmExecution}
      />

      {/* غرفة الأوامر الصوتية والنصية المستديمة عبر كافة الشاشات (Voice-First AI Command Dock) */}
      <CommandDock
        speech={speech}
        agents={agents}
        messages={messages}
        isSending={isSendingCommand}
        cockpitMode={cockpitMode}
        onToggleCockpit={() => setCockpitMode((prev) => !prev)}
        onSendCommand={handleSendCommand}
        onClearHistory={handleClearHistory}
        onOpenProposalAuth={(evalObj) => setModalEvaluation(evalObj)}
        onInspectMeeting={() => setActiveScreen('terminal')}
      />
    </div>
  );
};

export default App;
