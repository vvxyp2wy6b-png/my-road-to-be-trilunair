/**
 * بوابة الحوكمة والتصاريح والأمان المالي (Financial Governance & Live Authorization Gateway)
 * تدير الفصل الصارم بين التداول الورقي الآمن (PAPER - الوضع الافتراضي) والتداول الحقيقي (LIVE)،
 * مفتاح الطوارئ الفوري (Emergency Kill Switch)، قائمة فحوصات السلامة الخمسة، وسجل التدقيق الشامل.
 */

import React, { useMemo, useState } from 'react';
import {
  AlertOctagon,
  CheckCircle2,
  FileText,
  KeyRound,
  Lock,
  Power,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Unlock,
  XCircle,
} from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import type { AuditLogEntry, SafetyChecks, SystemStatus, TradingMode } from '../../types/trilunair';

export const REQUIRED_LIVE_PHRASE = 'AUTHORIZE LIVE TRADING DR MAJOOOOOOD';

export interface SwitchTradingModePayload {
  targetMode: TradingMode;
  adminPin: string;
  confirmationPhrase: string;
  acknowledgeRealCapitalRisk: boolean;
}

export interface GovernanceViewProps {
  systemStatus: SystemStatus | null;
  auditLogs: AuditLogEntry[];
  isUpdating?: boolean;
  onSwitchTradingMode: (payload: SwitchTradingModePayload) => Promise<void>;
  onToggleKillSwitch: (active: boolean, reason: string) => Promise<void>;
  onRefreshAuditLogs?: () => Promise<void>;
}

export const GovernanceView: React.FC<GovernanceViewProps> = ({
  systemStatus,
  auditLogs,
  isUpdating = false,
  onSwitchTradingMode,
  onToggleKillSwitch,
  onRefreshAuditLogs,
}) => {
  const { language } = useTheme();

  const [adminPin, setAdminPin] = useState<string>('');
  const [confirmationPhrase, setConfirmationPhrase] = useState<string>('');
  const [acknowledgeRisk, setAcknowledgeRisk] = useState<boolean>(false);
  const [killSwitchReason, setKillSwitchReason] = useState<string>(
    'Manual operator safety freeze'
  );
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'INFO' | 'WARNING' | 'CRITICAL'>('ALL');
  const [feedbackMessage, setFeedbackMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const tradingMode = systemStatus?.tradingMode ?? 'PAPER';
  const killSwitchActive = systemStatus?.killSwitchActive ?? false;

  const safetyItems = useMemo(() => {
    const checks: SafetyChecks = systemStatus?.safetyChecks ?? {
      riskEngineVerified: true,
      maxDrawdownConfigured: true,
      killSwitchReady: true,
      positionLimitsActive: true,
      auditTrailHealthy: true,
    };
    return [
      {
        key: 'riskEngineVerified',
        passed: checks.riskEngineVerified,
        labelAr: 'محرك فحص المخاطر الحتمي (Pre-Trade Risk Engine) متصل ومُتحقق منه',
        labelEn: 'Deterministic Pre-Trade Risk Engine Verified & Online',
      },
      {
        key: 'maxDrawdownConfigured',
        passed: checks.maxDrawdownConfigured,
        labelAr: 'حدود السحب الأقصى لرأس المال (Max Drawdown Circuit Breaker) مفعلة',
        labelEn: 'Maximum Drawdown Circuit Breaker Configured',
      },
      {
        key: 'killSwitchReady',
        passed: checks.killSwitchReady,
        labelAr: 'مفتاح إيقاف الطوارئ الفوري (Emergency Kill Switch) جاهز للاستجابة',
        labelEn: 'Emergency Kill Switch Armed & Responsive',
      },
      {
        key: 'positionLimitsActive',
        passed: checks.positionLimitsActive,
        labelAr: 'قيود التركز الأقصى لكل أصل وحجم الصفقة نشطة',
        labelEn: 'Position Concentration & Order Notional Caps Active',
      },
      {
        key: 'auditTrailHealthy',
        passed: checks.auditTrailHealthy,
        labelAr: 'سجل التدقيق الأمني غير القابل للتلاعب (Audit Trail) يعمل بكفاءة',
        labelEn: 'Immutable Security & Policy Audit Trail Healthy',
      },
    ];
  }, [systemStatus?.safetyChecks]);

  const allSafetyChecksPassed = useMemo(
    () => safetyItems.every((item) => item.passed),
    [safetyItems]
  );

  const phraseMatches = confirmationPhrase.trim() === REQUIRED_LIVE_PHRASE;
  const canEnableLiveMode =
    allSafetyChecksPassed &&
    !killSwitchActive &&
    adminPin.trim().length >= 4 &&
    phraseMatches &&
    acknowledgeRisk &&
    !isUpdating;

  const handleAuthorizeLiveMode = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackMessage(null);

    if (!phraseMatches) {
      setFeedbackMessage({
        type: 'error',
        text:
          language === 'ar'
            ? `عبارة التأكيد غير مطابقة. يجب كتابة العبارة الحرفية: ${REQUIRED_LIVE_PHRASE}`
            : `Confirmation phrase mismatch. Must match exact string: ${REQUIRED_LIVE_PHRASE}`,
      });
      return;
    }

    try {
      await onSwitchTradingMode({
        targetMode: 'LIVE',
        adminPin: adminPin.trim(),
        confirmationPhrase: confirmationPhrase.trim(),
        acknowledgeRealCapitalRisk: acknowledgeRisk,
      });
      setAdminPin('');
      setConfirmationPhrase('');
      setAcknowledgeRisk(false);
      setFeedbackMessage({
        type: 'success',
        text:
          language === 'ar'
            ? 'تم التصريح بتفعيل وضع التداول الحقيقي (LIVE) وتسجيل الحدث في سجل التدقيق.'
            : 'LIVE Trading Mode authorized and logged to the security audit trail.',
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text:
          err instanceof Error
            ? err.message
            : language === 'ar'
              ? 'فشل تفويض التداول الحقيقي — تحقق من رمز PIN وشروط الأمان.'
              : 'Live authorization failed — check Admin PIN and safety requirements.',
      });
    }
  };

  const handleRevertToPaper = async () => {
    setFeedbackMessage(null);
    try {
      await onSwitchTradingMode({
        targetMode: 'PAPER',
        adminPin: adminPin.trim() || '7777',
        confirmationPhrase: 'REVERT_TO_PAPER',
        acknowledgeRealCapitalRisk: false,
      });
      setFeedbackMessage({
        type: 'success',
        text:
          language === 'ar'
            ? 'تمت العودة الفورية إلى وضع التداول الورقي الآمن (PAPER).'
            : 'Immediately reverted to safe PAPER Trading Mode.',
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text:
          err instanceof Error
            ? err.message
            : language === 'ar'
              ? 'تعذر تغيير الوضع في الوقت الحالي.'
              : 'Unable to switch trading mode right now.',
      });
    }
  };

  const handleKillSwitchClick = async () => {
    setFeedbackMessage(null);
    try {
      const nextActive = !killSwitchActive;
      await onToggleKillSwitch(
        nextActive,
        killSwitchReason.trim() ||
          (nextActive ? 'Emergency operator freeze' : 'Operator cleared emergency freeze')
      );
      setFeedbackMessage({
        type: nextActive ? 'error' : 'success',
        text: nextActive
          ? language === 'ar'
            ? 'تم تفعيل مفتاح الطوارئ (Kill Switch) وتجميد كافة عمليات تنفيذ الأوامر فوراً!'
            : 'Emergency Kill Switch ACTIVATED — All order execution is now frozen!'
          : language === 'ar'
            ? 'تم إلغاء تجميد مفتاح الطوارئ واستعادة الجاهزية تحت ضوابط المخاطر.'
            : 'Emergency Kill Switch deactivated — Normal risk-guarded operation restored.',
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Kill switch request failed',
      });
    }
  };

  const filteredLogs = useMemo(() => {
    if (severityFilter === 'ALL') return auditLogs;
    return auditLogs.filter((item) => item.severity === severityFilter);
  }, [auditLogs, severityFilter]);

  return (
    <div
      data-testid="governance-view"
      style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}
    >
      {/* 1. لافتة الحالة السيادية ومفتاح الطوارئ الفوري (Status Banner & Emergency Kill Switch) */}
      <section
        className="holo-panel"
        style={{
          padding: '1.2rem 1.35rem',
          borderColor:
            killSwitchActive || tradingMode === 'LIVE'
              ? 'var(--status-danger)'
              : 'var(--border-holo)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.85rem',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
              {tradingMode === 'LIVE' ? (
                <Unlock size={22} style={{ color: 'var(--status-danger)' }} aria-hidden="true" />
              ) : (
                <Lock size={22} style={{ color: 'var(--status-success)' }} aria-hidden="true" />
              )}
              <h2 style={{ margin: 0, fontSize: '1.12rem', fontWeight: 800 }}>
                {language === 'ar'
                  ? 'بوابة التصاريح السيادية ومفتاح الطوارئ'
                  : 'Paper vs Live Trading Authorization Gateway'}
              </h2>
              <span
                data-testid="governance-mode-badge"
                className={`holo-badge ${
                  tradingMode === 'LIVE' ? 'holo-badge-danger' : 'holo-badge-success'
                }`}
              >
                {tradingMode === 'LIVE'
                  ? language === 'ar'
                    ? 'وضع التداول الحقيقي مفعل (LIVE)'
                    : 'LIVE TRADING ACTIVE'
                  : language === 'ar'
                    ? 'التداول الورقي الآمن هو الوضع النشط (PAPER)'
                    : 'PAPER TRADING (SAFE DEFAULT)'}
              </span>
            </div>

            <p style={{ margin: 0, fontSize: '0.83rem', color: 'var(--text-secondary)' }}>
              {language === 'ar'
                ? 'يبقى النظام مقفلاً افتراضياً على التداول الورقي المحاكي، ولا ينتقل للتداول الحقيقي إلا بعد اجتياز فحوصات السلامة الخمسة وتفويض المسؤول الصريح.'
                : 'System defaults strictly to simulated Paper Trading. Live capital execution requires passing all 5 deterministic safety checks plus multi-factor administrator authorization.'}
            </p>
          </div>

          {tradingMode === 'LIVE' && (
            <button
              type="button"
              data-testid="revert-paper-btn"
              disabled={isUpdating}
              onClick={() => {
                void handleRevertToPaper();
              }}
              className="holo-btn holo-btn-buy"
            >
              <ShieldCheck size={16} aria-hidden="true" />
              <span>
                {language === 'ar'
                  ? 'العودة الفورية للتداول الورقي الآمن'
                  : 'Revert to Paper Trading'}
              </span>
            </button>
          )}
        </div>

        {/* وحدة التحكم بمفتاح الطوارئ (Emergency Kill Switch) */}
        <div
          className="holo-panel-subtle"
          style={{
            padding: '0.85rem 1rem',
            borderColor: killSwitchActive ? 'var(--status-danger)' : 'var(--border-subtle)',
            background: killSwitchActive
              ? 'var(--status-danger-bg)'
              : 'color-mix(in srgb, var(--bg-elevated) 82%, transparent)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flex: '1 1 280px' }}>
            <AlertOctagon
              size={22}
              style={{
                color: killSwitchActive ? 'var(--status-danger)' : 'var(--status-warning)',
                flexShrink: 0,
              }}
              aria-hidden="true"
            />
            <div>
              <strong style={{ fontSize: '0.9rem', display: 'block' }}>
                {language === 'ar'
                  ? 'مفتاح إيقاف الطوارئ الشامل (Emergency Kill Switch)'
                  : 'Emergency Kill Switch (Global Execution Freeze)'}
              </strong>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {killSwitchActive
                  ? language === 'ar'
                    ? 'الحالة الحالية: التجميد الفوري مفعل — جميع أوامر الصوت والنص والقاعة محظورة.'
                    : 'Status: FROZEN — All Voice, Text, and Terminal order executions are blocked.'
                  : language === 'ar'
                    ? 'الحالة الحالية: جاهز للتفعيل بضغطة واحدة عند رصد أي تقلب شاذ.'
                    : 'Status: Armed & Ready — One click freezes all order routing immediately.'}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input
              type="text"
              aria-label={language === 'ar' ? 'سبب تفعيل أو إلغاء مفتاح الطوارئ' : 'Kill switch reason'}
              value={killSwitchReason}
              onChange={(e) => setKillSwitchReason(e.target.value)}
              className="holo-input"
              style={{ width: '230px', minHeight: '38px', fontSize: '0.8rem' }}
            />
            <button
              type="button"
              data-testid="toggle-kill-switch-btn"
              disabled={isUpdating}
              onClick={() => {
                void handleKillSwitchClick();
              }}
              className={`holo-btn ${killSwitchActive ? 'holo-btn-buy' : 'holo-btn-danger'}`}
            >
              <Power size={15} aria-hidden="true" />
              <span>
                {killSwitchActive
                  ? language === 'ar'
                    ? 'إلغاء التجميد واستئناف النظام'
                    : 'Deactivate Kill Switch'
                  : language === 'ar'
                    ? 'تفعيل مفتاح الطوارئ وتجميد التنفيذ'
                    : 'Activate Emergency Kill Switch'}
              </span>
            </button>
          </div>
        </div>

        {feedbackMessage && (
          <div
            role="status"
            style={{
              padding: '0.65rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background:
                feedbackMessage.type === 'success'
                  ? 'var(--status-success-bg)'
                  : 'var(--status-danger-bg)',
              color:
                feedbackMessage.type === 'success'
                  ? 'var(--status-success)'
                  : 'var(--status-danger)',
              fontSize: '0.83rem',
              fontWeight: 700,
            }}
          >
            {feedbackMessage.text}
          </div>
        )}
      </section>

      {/* 2. قائمة التحقق الخماسية وبوابة تفويض التداول الحقيقي */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '1rem',
        }}
      >
        {/* قائمة فحوصات السلامة الخمسة (5-Point Deterministic Safety Checklist) */}
        <section
          className="holo-panel"
          style={{ padding: '1.1rem 1.2rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <ShieldCheck size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800 }}>
                {language === 'ar'
                  ? 'قائمة التحقق الحتمي من السلامة (5 نقاط)'
                  : '5-Point Deterministic Safety Checklist'}
              </h3>
            </div>
            <span
              className={`holo-badge ${
                allSafetyChecksPassed ? 'holo-badge-success' : 'holo-badge-danger'
              }`}
            >
              {allSafetyChecksPassed
                ? language === 'ar'
                  ? 'مكتمل 5/5'
                  : '5/5 Verified'
                : language === 'ar'
                  ? 'غير مكتمل'
                  : 'Incomplete'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {safetyItems.map((item) => (
              <div
                key={item.key}
                data-testid={`safety-check-${item.key}`}
                className="holo-panel-subtle"
                style={{
                  padding: '0.65rem 0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.55rem',
                  fontSize: '0.82rem',
                  borderColor: item.passed ? 'var(--status-success)' : 'var(--status-danger)',
                }}
              >
                {item.passed ? (
                  <CheckCircle2
                    size={17}
                    style={{ color: 'var(--status-success)', flexShrink: 0 }}
                    aria-hidden="true"
                  />
                ) : (
                  <XCircle
                    size={17}
                    style={{ color: 'var(--status-danger)', flexShrink: 0 }}
                    aria-hidden="true"
                  />
                )}
                <span>{language === 'ar' ? item.labelAr : item.labelEn}</span>
              </div>
            ))}
          </div>

          {systemStatus?.providers && (
            <div
              className="holo-panel-subtle"
              style={{
                padding: '0.6rem 0.75rem',
                fontSize: '0.76rem',
                color: 'var(--text-muted)',
                display: 'flex',
                flexWrap: 'wrap',
                gap: '0.6rem',
                marginTop: 'auto',
              }}
            >
              <span>LLM: {systemStatus.providers.llmProvider}</span>
              <span>•</span>
              <span>STT: {systemStatus.providers.sttProvider}</span>
              <span>•</span>
              <span>TTS: {systemStatus.providers.ttsProvider}</span>
            </div>
          )}
        </section>

        {/* نموذج التفويض الصريح لوضع التداول الحقيقي (Explicit Live Trading Authorization Form) */}
        <section
          className="holo-panel"
          style={{ padding: '1.1rem 1.2rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <KeyRound size={18} style={{ color: 'var(--status-warning)' }} aria-hidden="true" />
              <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800 }}>
                {language === 'ar'
                  ? 'تفويض الانتقال إلى التداول الحقيقي (LIVE)'
                  : 'Explicit Live Trading Authorization'}
              </h3>
            </div>

            <button
              type="button"
              onClick={() => {
                void handleRevertToPaper();
              }}
              disabled={tradingMode === 'PAPER' || isUpdating}
              className="holo-btn"
              style={{ minHeight: '32px', padding: '0.2rem 0.65rem', fontSize: '0.76rem' }}
            >
              {language === 'ar'
                ? 'العودة الفورية للتداول الورقي الآمن'
                : 'Revert to Paper Trading'}
            </button>
          </div>

          <form
            onSubmit={handleAuthorizeLiveMode}
            style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
          >
            <div>
              <label
                htmlFor="gov-admin-pin"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  marginBottom: '0.25rem',
                }}
              >
                <span>{language === 'ar' ? 'رمز المسؤول السري (Admin PIN)' : 'Administrator PIN'}</span>
                <span className="tabular-nums" style={{ color: 'var(--text-muted)', fontSize: '0.74rem' }}>
                  {language === 'ar' ? 'تلميح الاختبار: 7777' : 'Testing Hint: 7777'}
                </span>
              </label>
              <input
                id="gov-admin-pin"
                data-testid="gov-admin-pin-input"
                type="password"
                inputMode="numeric"
                autoComplete="off"
                placeholder="••••"
                value={adminPin}
                onChange={(e) => setAdminPin(e.target.value)}
                className="holo-input tabular-nums"
              />
            </div>

            <div>
              <label
                htmlFor="gov-confirm-phrase"
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  marginBottom: '0.25rem',
                }}
              >
                {language === 'ar'
                  ? 'اكتب عبارة التفويض الحرفية لتأكيد الإرادة الصريحة:'
                  : 'Type exact confirmation phrase to unlock LIVE mode:'}
              </label>
              <div
                className="tabular-nums"
                style={{
                  padding: '0.35rem 0.6rem',
                  marginBottom: '0.35rem',
                  borderRadius: '6px',
                  background: 'var(--bg-base)',
                  border: '1px dashed var(--border-holo)',
                  color: 'var(--accent-primary)',
                  fontSize: '0.77rem',
                  userSelect: 'all',
                }}
              >
                {REQUIRED_LIVE_PHRASE}
              </div>
              <input
                id="gov-confirm-phrase"
                data-testid="gov-phrase-input"
                type="text"
                autoComplete="off"
                placeholder={REQUIRED_LIVE_PHRASE}
                value={confirmationPhrase}
                onChange={(e) => setConfirmationPhrase(e.target.value)}
                className="holo-input tabular-nums"
              />
            </div>

            <label
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.55rem',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                data-testid="gov-risk-ack-checkbox"
                checked={acknowledgeRisk}
                onChange={(e) => setAcknowledgeRisk(e.target.checked)}
                style={{ marginTop: '0.2rem', accentColor: 'var(--accent-primary)' }}
              />
              <span>
                {language === 'ar'
                  ? 'أقر بالمسؤولية المالية الكاملة عن التداول برأس مال حقيقي، مع بقاء كل صفقة خاضعة لفحص المخاطر وتأكيد PIN الفردي.'
                  : 'I acknowledge full capital risk for Live Trading, understanding that every individual order still requires risk validation and PIN confirmation.'}
              </span>
            </label>

            <button
              type="submit"
              data-testid="authorize-live-mode-btn"
              disabled={!canEnableLiveMode}
              className="holo-btn holo-btn-danger"
              style={{ width: '100%' }}
            >
              <ShieldAlert size={16} aria-hidden="true" />
              <span>
                {language === 'ar'
                  ? 'تفويض وتفعيل وضع التداول الحقيقي (LIVE)'
                  : 'Authorize & Enable LIVE Trading Mode'}
              </span>
            </button>
          </form>
        </section>
      </div>

      {/* 3. سجل التدقيق الأمني والرقابي الكامل (Security & Policy Audit Trail) */}
      <section
        className="holo-panel"
        style={{ padding: '1.1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.65rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <FileText size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800 }}>
              {language === 'ar'
                ? 'سجل التدقيق الأمني والرقابي الشامل (Audit Trail)'
                : 'Security & Policy Audit Trail'}
            </h3>
            <span className="holo-badge tabular-nums">{filteredLogs.length}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
            {(['ALL', 'INFO', 'WARNING', 'CRITICAL'] as const).map((sev) => (
              <button
                key={sev}
                type="button"
                aria-pressed={severityFilter === sev}
                onClick={() => setSeverityFilter(sev)}
                className={`holo-btn ${severityFilter === sev ? 'holo-btn-primary' : ''}`}
                style={{ minHeight: '30px', padding: '0.15rem 0.55rem', fontSize: '0.74rem' }}
              >
                {sev}
              </button>
            ))}
            {onRefreshAuditLogs && (
              <button
                type="button"
                onClick={() => {
                  void onRefreshAuditLogs();
                }}
                className="holo-btn"
                title={language === 'ar' ? 'تحديث السجل' : 'Refresh Audit Logs'}
                style={{ minHeight: '30px', padding: '0.15rem 0.55rem' }}
              >
                <RefreshCw size={13} aria-hidden="true" />
              </button>
            )}
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.81rem' }}>
            <thead>
              <tr
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  color: 'var(--text-muted)',
                }}
              >
                <th style={{ padding: '0.5rem', textAlign: 'start' }}>
                  {language === 'ar' ? 'التوقيت' : 'Timestamp'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'start' }}>
                  {language === 'ar' ? 'الفاعل / المصدر' : 'Actor / Source'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'start' }}>
                  {language === 'ar' ? 'الحدث الأمني' : 'Action'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'center' }}>
                  {language === 'ar' ? 'الأهمية' : 'Severity'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'start' }}>
                  {language === 'ar' ? 'التفاصيل' : 'Details'}
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    style={{ padding: '1.2rem', textAlign: 'center', color: 'var(--text-muted)' }}
                  >
                    {language === 'ar'
                      ? 'لا توجد سجلات تدقيق مطابقة للفلتر المحدد.'
                      : 'No audit log entries match the selected filter.'}
                  </td>
                </tr>
              ) : (
                filteredLogs.map((entry) => (
                  <tr
                    key={entry.id}
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    <td
                      className="tabular-nums"
                      style={{
                        padding: '0.55rem 0.5rem',
                        color: 'var(--text-muted)',
                        whiteSpace: 'nowrap',
                        fontSize: '0.75rem',
                      }}
                    >
                      {new Date(entry.timestamp).toLocaleTimeString('en-GB', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td style={{ padding: '0.55rem 0.5rem', whiteSpace: 'nowrap' }}>
                      <strong>{entry.actor}</strong>
                      <span
                        className="holo-badge"
                        style={{ marginInlineStart: '0.4rem', fontSize: '0.68rem', padding: '0.1rem 0.45rem' }}
                      >
                        {entry.source}
                      </span>
                    </td>
                    <td className="tabular-nums" style={{ padding: '0.55rem 0.5rem', fontWeight: 600 }}>
                      {entry.action}
                    </td>
                    <td style={{ padding: '0.55rem 0.5rem', textAlign: 'center' }}>
                      <span
                        className={`holo-badge ${
                          entry.severity === 'CRITICAL'
                            ? 'holo-badge-danger'
                            : entry.severity === 'WARNING'
                              ? 'holo-badge-warning'
                              : 'holo-badge-success'
                        }`}
                      >
                        {entry.severity}
                      </span>
                    </td>
                    <td style={{ padding: '0.55rem 0.5rem', color: 'var(--text-secondary)' }}>
                      {language === 'ar' ? entry.detailsAr : entry.detailsEn}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default GovernanceView;
