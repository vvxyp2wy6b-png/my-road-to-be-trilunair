/**
 * بوابة الحوكمة والتصاريح والأمان المالي (Financial Governance & Live Authorization Gateway)
 * تدير الفصل الصارم بين التداول الورقي الآمن (PAPER - الوضع الافتراضي) والتداول الحقيقي (LIVE)،
 * مفتاح الطوارئ الفوري (Emergency Kill Switch)، قائمة فحوصات السلامة الخمسة، وسجل التدقيق الشامل.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertOctagon,
  CheckCircle2,
  Cloud,
  Database,
  FileText,
  KeyRound,
  Lock,
  LogOut,
  Power,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Unlock,
  XCircle,
} from 'lucide-react';
import { trilunairApi } from '../../api/client';
import { useTheme } from '../../theme/ThemeContext';
import type {
  AdminSessionStatus,
  AuditLogEntry,
  CloudOperationsTelemetry,
  HostingDecisionMatrix,
  PasskeySecurityPosture,
  PipelineLatencySnapshot,
  SafetyChecks,
  SystemStatus,
  TradingMode,
  WalkForwardEvaluation,
} from '../../types/trilunair';

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

function opsStatusBadgeClass(status: string): string {
  const s = (status || '').toUpperCase();
  if (s === 'CONNECTED' || s === 'READY' || s === 'RECONCILED' || s === 'ACTIVE' || s === 'CLOUD_AND_BROWSER_READY') {
    return 'holo-badge holo-badge-success';
  }
  if (s.includes('SIMULATED') || s.includes('FALLBACK') || s.includes('BROWSER_PRIMARY') || s === 'IDLE_READY' || s === 'DEV_PROXY_MODE') {
    return 'holo-badge holo-badge-warning';
  }
  return 'holo-badge holo-badge-danger';
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
  const [sessionSecretInput, setSessionSecretInput] = useState<string>('');
  const [sessionStatus, setSessionStatus] = useState<AdminSessionStatus | null>(null);
  const [opsTelemetry, setOpsTelemetry] = useState<CloudOperationsTelemetry | null>(null);
  const [passkeyStatus, setPasskeyStatus] = useState<PasskeySecurityPosture | null>(null);
  const [benchmarkMatrix, setBenchmarkMatrix] = useState<HostingDecisionMatrix | null>(null);
  const [latencySnapshot, setLatencySnapshot] = useState<PipelineLatencySnapshot | null>(null);
  const [walkForwardEval, setWalkForwardEval] = useState<WalkForwardEvaluation | null>(null);
  const [newDeviceLabel, setNewDeviceLabel] = useState<string>('MacBook Pro Touch ID / iPhone Face ID');
  const [generatedRecoveryCodes, setGeneratedRecoveryCodes] = useState<string[]>([]);
  const [recoveryCodeInput, setRecoveryCodeInput] = useState<string>('');
  const [stepUpActive, setStepUpActive] = useState<boolean>(false);
  const [isLoadingOps, setIsLoadingOps] = useState<boolean>(false);
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
  const riskPolicy = systemStatus?.riskPolicy ?? opsTelemetry?.riskPolicy ?? {
    maxRiskPerTradePct: 0.5,
    maxExposurePerAssetPct: 25.0,
    dailyLossLimitPct: 2.0,
    weeklyLossLimitPct: 5.0,
    maxDrawdownLimitPct: 10.0,
    prohibitLeverage: true,
  };

  const refreshCloudOperations = useCallback(async () => {
    setIsLoadingOps(true);
    try {
      const [opsRes, sessRes, pkRes, bmRes, latRes, wfRes] = await Promise.allSettled([
        trilunairApi.getOperationsTelemetry(),
        trilunairApi.getAdminSessionStatus(),
        trilunairApi.getPasskeyStatus(),
        trilunairApi.getBenchmarkMatrix(),
        trilunairApi.getLatencyPipeline(),
        trilunairApi.getPerformanceEvaluation('BTC-USD'),
      ]);
      if (opsRes.status === 'fulfilled') setOpsTelemetry(opsRes.value);
      if (sessRes.status === 'fulfilled') setSessionStatus(sessRes.value);
      if (pkRes.status === 'fulfilled') setPasskeyStatus(pkRes.value);
      if (bmRes.status === 'fulfilled') setBenchmarkMatrix(bmRes.value);
      if (latRes.status === 'fulfilled') setLatencySnapshot(latRes.value);
      if (wfRes.status === 'fulfilled') setWalkForwardEval(wfRes.value);
    } catch {
      // تجاهل في بيئات الاختبار غير الموصولة بنقاط النهاية السحابية
    } finally {
      setIsLoadingOps(false);
    }
  }, []);

  useEffect(() => {
    void refreshCloudOperations();
  }, [refreshCloudOperations]);

  const handleRegisterPasskey = async () => {
    setFeedbackMessage(null);
    try {
      const res = await trilunairApi.registerOwnerPasskey(newDeviceLabel.trim() || 'Owner Passkey', sessionSecretInput.trim() || undefined);
      setStepUpActive(true);
      await refreshCloudOperations();
      await onRefreshAuditLogs?.();
      setFeedbackMessage({
        type: 'success',
        text:
          language === 'ar'
            ? `تم تسجيل مفتاح المرور البيومتري (${res.deviceLabel}) بنجاح دون تخزين أي بصمة أو صورة وجه.`
            : `Registered biometric Passkey (${res.deviceLabel}) with zero stored biometric templates.`,
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Passkey registration failed.',
      });
    }
  };

  const handleAuthenticatePasskey = async () => {
    setFeedbackMessage(null);
    try {
      const res = await trilunairApi.authenticateWithPasskey();
      setStepUpActive(true);
      await refreshCloudOperations();
      await onRefreshAuditLogs?.();
      setFeedbackMessage({
        type: 'success',
        text:
          language === 'ar'
            ? `تم التحقق البيومتري للمالك عبر (${res.deviceLabel}) وتفعيل رمز Step-Up للعمليات الحساسة.`
            : `Verified owner biometric Passkey (${res.deviceLabel}); Step-Up authorization active.`,
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Passkey authentication failed.',
      });
    }
  };

  const handleRevokePasskey = async (credentialId: string) => {
    setFeedbackMessage(null);
    try {
      await trilunairApi.revokePasskeyDevice(credentialId, sessionSecretInput.trim() || undefined);
      await refreshCloudOperations();
      await onRefreshAuditLogs?.();
      setFeedbackMessage({
        type: 'success',
        text: language === 'ar' ? 'تم إبطال صلاحية الجهاز المسجل فوراً.' : 'Revoked registered Passkey device.',
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to revoke Passkey.',
      });
    }
  };

  const handleGenerateRecoveryCodes = async () => {
    setFeedbackMessage(null);
    try {
      const res = await trilunairApi.generateRecoveryCodes(sessionSecretInput.trim() || undefined);
      setGeneratedRecoveryCodes(res.recoveryCodesOnceOnly);
      await refreshCloudOperations();
      await onRefreshAuditLogs?.();
      setFeedbackMessage({
        type: 'success',
        text: language === 'ar' ? res.warningAr : res.warningEn,
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Recovery code generation failed.',
      });
    }
  };

  const handleRedeemRecoveryCode = async () => {
    if (!recoveryCodeInput.trim()) return;
    setFeedbackMessage(null);
    try {
      await trilunairApi.redeemRecoveryCode(recoveryCodeInput.trim());
      setRecoveryCodeInput('');
      setStepUpActive(true);
      await refreshCloudOperations();
      setFeedbackMessage({
        type: 'success',
        text: language === 'ar' ? 'تم استرداد وصول المالك بنجاح وإبطال الرمز المستخدم.' : 'Owner recovery verified and one-time code consumed.',
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Invalid recovery code.',
      });
    }
  };

  const handleAdminSessionLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackMessage(null);
    if (sessionSecretInput.trim().length < 8) {
      setFeedbackMessage({
        type: 'error',
        text:
          language === 'ar'
            ? 'سر المسؤول يجب أن يتكون من 8 محارف قوية على الأقل (تمت إزالة كافة رموز الاختبار الافتراضية).'
            : 'Administrator secret must be at least 8 strong characters (all default test PINs removed).',
      });
      return;
    }
    try {
      await trilunairApi.loginAdminSession(sessionSecretInput.trim());
      setSessionSecretInput('');
      await refreshCloudOperations();
      await onRefreshAuditLogs?.();
      setFeedbackMessage({
        type: 'success',
        text:
          language === 'ar'
            ? 'تم توثيق جلسة المسؤول المشفرة (PBKDF2 + HttpOnly + CSRF) بنجاح.'
            : 'Authenticated signed administrator session (PBKDF2 + HttpOnly + CSRF).',
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text:
          err instanceof Error
            ? err.message
            : language === 'ar'
              ? 'فشل تسجيل دخول جلسة المسؤول.'
              : 'Administrator session login failed.',
      });
    }
  };

  const handleAdminSessionLogout = async () => {
    try {
      await trilunairApi.logoutAdminSession();
      await refreshCloudOperations();
      setFeedbackMessage({
        type: 'success',
        text:
          language === 'ar'
            ? 'تم إنهاء وإبطال جلسة المسؤول بنجاح.'
            : 'Administrator session revoked and cleared.',
      });
    } catch {
      // تجاهل
    }
  };

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
        labelAr: 'حدود السحب الأقصى لرأس المال (10% Max Drawdown Circuit Breaker) مفعلة',
        labelEn: '10% Maximum Drawdown Circuit Breaker Configured',
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
        labelAr: 'قيود المخاطرة 0.5% والتركز الأقصى 25% لكل أصل نشطة',
        labelEn: '0.5% Per-Trade Risk & 25% Asset Concentration Caps Active',
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
    adminPin.trim().length >= 8 &&
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
            ? 'تم التحقق من حالة وضع التداول.'
            : 'Trading mode authorization evaluated.',
      });
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text:
          err instanceof Error
            ? err.message
            : language === 'ar'
              ? 'الإصدار v1.1.0-cloud-paper مقفل نهائياً على التداول الورقي (PAPER) مع liveAuthorized=false.'
              : 'Release v1.1.0-cloud-paper is permanently locked to PAPER mode (liveAuthorized=false).',
      });
    }
  };

  const handleRevertToPaper = async () => {
    setFeedbackMessage(null);
    try {
      await onSwitchTradingMode({
        targetMode: 'PAPER',
        adminPin: '',
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
      await refreshCloudOperations();
      setFeedbackMessage({
        type: nextActive ? 'error' : 'success',
        text: nextActive
          ? language === 'ar'
            ? 'تم تفعيل مفتاح الطوارئ (Kill Switch) وتجميد كافة عمليات تنفيذ الأوامر فوراً!'
            : 'Emergency Kill Switch ACTIVATED — All order execution is now frozen!'
          : language === 'ar'
            ? 'تم إلغاء تجميد مفتاح الطوارئ واستعادة الجاهزية الورقية تحت ضوابط المخاطر.'
            : 'Emergency Kill Switch deactivated — Normal paper risk-guarded operation restored.',
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
      {/* 1. لافتة الحالة السيادية والقفل الورقي الدائم ومفتاح الطوارئ الفوري */}
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
                  ? 'بوابة التصاريح السيادية ومفتاح الطوارئ السحابي'
                  : 'Cloud Security, Paper Lock & Kill Switch Gateway'}
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
                    ? 'التداول الورقي مقفل نهائياً (PAPER — liveAuthorized=false)'
                    : 'PAPER TRADING LOCKED (liveAuthorized=false)'}
              </span>
              <span className="holo-badge holo-badge-accent tabular-nums">
                {systemStatus?.version || '1.1.0-cloud-paper'}
              </span>
            </div>

            <p style={{ margin: 0, fontSize: '0.83rem', color: 'var(--text-secondary)' }}>
              {language === 'ar'
                ? 'في الإصدار v1.1.0-cloud-paper، يظل وضع التنفيذ مقفلاً نهائياً على التداول الورقي الآمن (PAPER) مع تعطيل الأوامر الحقيقية والسحوبات والرافعة المالية، حتى عند الاتصال ببيانات السوق العامة الحية لـ Binance Spot.'
                : 'In release v1.1.0-cloud-paper, order execution is permanently locked to PAPER mode (liveAuthorized=false). Live Binance Spot public market data never enables real order placement.'}
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

        {/* شريط حدود سياسة المخاطر الموحدة الخمسة (Unified 5-Limit Risk Policy) */}
        <div
          data-testid="unified-risk-policy-strip"
          className="holo-panel-subtle"
          style={{
            padding: '0.65rem 0.9rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '0.6rem',
            fontSize: '0.78rem',
          }}
        >
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>
              {language === 'ar' ? 'أقصى مخاطرة لكل صفقة' : 'Max Risk / Trade'}
            </span>
            <strong className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
              {riskPolicy.maxRiskPerTradePct}%
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>
              {language === 'ar' ? 'أقصى تعرض للأصل الواحد' : 'Max Asset Exposure'}
            </span>
            <strong className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
              {riskPolicy.maxExposurePerAssetPct}%
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>
              {language === 'ar' ? 'قاطع الخسارة اليومية' : 'Daily Loss Breaker'}
            </span>
            <strong className="tabular-nums" style={{ color: 'var(--status-warning)' }}>
              {riskPolicy.dailyLossLimitPct}%
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>
              {language === 'ar' ? 'قاطع الخسارة الأسبوعية' : 'Weekly Loss Breaker'}
            </span>
            <strong className="tabular-nums" style={{ color: 'var(--status-warning)' }}>
              {riskPolicy.weeklyLossLimitPct}%
            </strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)', display: 'block' }}>
              {language === 'ar' ? 'أقصى سحب مسموح (Drawdown)' : 'Max Drawdown Limit'}
            </span>
            <strong className="tabular-nums" style={{ color: 'var(--status-danger)' }}>
              {riskPolicy.maxDrawdownLimitPct}%
            </strong>
          </div>
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

      {/* 1.5 لوحة العمليات والمراقبة السحابية الشفافة (Cloud Operations & Monitoring — Section 13) */}
      <section
        data-testid="cloud-operations-panel"
        className="holo-panel"
        style={{ padding: '1.1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.65rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Cloud size={19} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800 }}>
              {language === 'ar'
                ? 'لوحة العمليات والمراقبة السحابية الحقيقية (Cloud Operations & Telemetry)'
                : 'Truthful Cloud Operations & Subsystem Health Matrix'}
            </h3>
            <span className="holo-badge holo-badge-accent">
              {language === 'ar' ? 'فصل صارم بين الحي والمحاكي' : 'Zero Fake Live Claims'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {sessionStatus?.authenticated ? (
              <button
                type="button"
                onClick={() => void handleAdminSessionLogout()}
                className="holo-btn"
                style={{ minHeight: '30px', padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
              >
                <LogOut size={13} aria-hidden="true" />
                <span>{language === 'ar' ? 'إنهاء جلسة المسؤول' : 'Sign Out Session'}</span>
              </button>
            ) : (
              <form
                onSubmit={handleAdminSessionLogin}
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <input
                  type="password"
                  data-testid="admin-session-secret-input"
                  value={sessionSecretInput}
                  onChange={(e) => setSessionSecretInput(e.target.value)}
                  placeholder={language === 'ar' ? 'سر جلسة المسؤول (PBKDF2)' : 'Admin Session Secret'}
                  className="holo-input"
                  style={{ width: '175px', minHeight: '30px', fontSize: '0.75rem' }}
                />
                <button
                  type="submit"
                  data-testid="admin-session-login-btn"
                  className="holo-btn holo-btn-primary"
                  style={{ minHeight: '30px', padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
                >
                  {language === 'ar' ? 'توثيق الجلسة' : 'Auth Session'}
                </button>
              </form>
            )}
            <button
              type="button"
              data-testid="refresh-cloud-ops-btn"
              onClick={() => void refreshCloudOperations()}
              className="holo-btn"
              style={{ minHeight: '30px', padding: '0.2rem 0.55rem' }}
              title={language === 'ar' ? 'تحديث حالة الأنظمة السحابية' : 'Refresh Cloud Operations'}
            >
              <RefreshCw size={13} className={isLoadingOps ? 'pulse-active' : ''} aria-hidden="true" />
            </button>
          </div>
        </div>

        {opsTelemetry ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(215px, 1fr))',
              gap: '0.65rem',
              fontSize: '0.77rem',
            }}
          >
            <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <strong><Database size={13} style={{ marginInlineEnd: '4px', verticalAlign: 'middle' }} />PostgreSQL</strong>
                <span className={opsStatusBadgeClass(opsTelemetry.subsystems.postgresql.status)}>
                  {opsTelemetry.subsystems.postgresql.status}
                </span>
              </div>
              <div className="tabular-nums" style={{ color: 'var(--text-muted)' }}>
                Backend: {opsTelemetry.subsystems.postgresql.activeBackend} ({opsTelemetry.subsystems.postgresql.latencyMs}ms)
              </div>
            </div>

            <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <strong>Redis Cache</strong>
                <span className={opsStatusBadgeClass(opsTelemetry.subsystems.redis.status)}>
                  {opsTelemetry.subsystems.redis.status}
                </span>
              </div>
              <div className="tabular-nums" style={{ color: 'var(--text-muted)' }}>
                Mode: {opsTelemetry.subsystems.redis.mode} ({opsTelemetry.subsystems.redis.latencyMs}ms)
              </div>
            </div>

            <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <strong>Binance Public Data</strong>
                <span className={opsStatusBadgeClass(opsTelemetry.subsystems.binancePublicMarketData.restStatus)}>
                  REST: {opsTelemetry.subsystems.binancePublicMarketData.restStatus}
                </span>
              </div>
              <div className="tabular-nums" style={{ color: 'var(--text-muted)' }}>
                WS: {opsTelemetry.subsystems.binancePublicMarketData.wsStatus} • Weight: {opsTelemetry.subsystems.binancePublicMarketData.usedWeight1m}
              </div>
            </div>

            <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <strong>AI Council Providers</strong>
                <span className={opsStatusBadgeClass(opsTelemetry.subsystems.aiProviders.cloudConnectedCount > 0 ? 'CONNECTED' : 'SIMULATED_LOCAL')}>
                  {opsTelemetry.subsystems.aiProviders.cloudConnectedCount > 0
                    ? `${opsTelemetry.subsystems.aiProviders.cloudConnectedCount} CLOUD`
                    : 'SIMULATED_LOCAL'}
                </span>
              </div>
              <div style={{ color: 'var(--text-muted)' }}>
                {opsTelemetry.subsystems.aiProviders.providers
                  .map((p) => `${p.providerId.split('-')[0]}:${p.available ? 'ON' : 'OFF'}`)
                  .join(' · ')}
              </div>
            </div>

            <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <strong>Voice & Safari Audio</strong>
                <span className={opsStatusBadgeClass(opsTelemetry.subsystems.voiceServices.status)}>
                  {opsTelemetry.subsystems.voiceServices.cloudSpeechConfigured ? 'CLOUD+WEB' : 'WEB_PRIMARY'}
                </span>
              </div>
              <div style={{ color: 'var(--text-muted)' }}>
                STT: {opsTelemetry.subsystems.voiceServices.sttPrimaryEngine}
              </div>
            </div>

            <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <strong><Activity size={13} style={{ marginInlineEnd: '4px', verticalAlign: 'middle' }} />Reconciliation & WS</strong>
                <span className={opsStatusBadgeClass(opsTelemetry.subsystems.accountReconciliation.status)}>
                  {opsTelemetry.subsystems.accountReconciliation.status}
                </span>
              </div>
              <div className="tabular-nums" style={{ color: 'var(--text-muted)' }}>
                WS Clients: {opsTelemetry.subsystems.webSocketHub.activeClientConnections} • Err: {opsTelemetry.subsystems.backendApi.serverErrorRatePct}%
              </div>
            </div>
          </div>
        ) : (
          <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.85rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {language === 'ar'
              ? 'قياسات العمليات السحابية قيد الاستعلام من /api/system/operations...'
              : 'Querying live subsystem telemetry from /api/system/operations...'}
          </div>
        )}
      </section>

      {/* 1.6 لوحة المصادقة البيومترية للمالك (WebAuthn / FIDO2 Passkeys — Face ID / Touch ID / Security Key) */}
      <section
        data-testid="passkey-biometric-panel"
        className="holo-panel"
        style={{ padding: '1.1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <KeyRound size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800 }}>
              {language === 'ar'
                ? 'المصادقة البيومترية للمالك (WebAuthn / FIDO2 Passkeys — Face ID & Touch ID)'
                : 'Owner Biometric Passkeys (WebAuthn / FIDO2 — Face ID, Touch ID & Security Keys)'}
            </h3>
            <span className="holo-badge holo-badge-success">
              {language === 'ar' ? 'صفر قوالب حيوية مخزنة' : 'Zero Biometric Templates Stored'}
            </span>
            {stepUpActive && (
              <span className="holo-badge holo-badge-accent">
                {language === 'ar' ? 'تصعيد Step-Up نشط' : 'Step-Up Verified'}
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            RP ID: <strong>{passkeyStatus?.rpId ?? 'trilunair.medinsup.com'}</strong> •{' '}
            {language === 'ar' ? 'الأجهزة النشطة:' : 'Registered Devices:'}{' '}
            <strong>{passkeyStatus?.registeredDeviceCount ?? 0}</strong> •{' '}
            {language === 'ar' ? 'رموز الاسترداد:' : 'Recovery Codes:'}{' '}
            <strong>{passkeyStatus?.remainingRecoveryCodes ?? 0}</strong>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.55rem', alignItems: 'center' }}>
          <input
            type="text"
            data-testid="passkey-device-label-input"
            value={newDeviceLabel}
            onChange={(e) => setNewDeviceLabel(e.target.value)}
            placeholder={language === 'ar' ? 'تسمية جهاز المالك (مثلاً iPhone Face ID)' : 'Owner device label'}
            className="holo-input"
            style={{ minWidth: '230px', flex: '1 1 230px', minHeight: '32px', fontSize: '0.78rem' }}
          />
          <button
            type="button"
            data-testid="passkey-register-btn"
            onClick={() => void handleRegisterPasskey()}
            className="holo-btn holo-btn-primary"
            style={{ minHeight: '32px', fontSize: '0.76rem', padding: '0.25rem 0.75rem' }}
          >
            {language === 'ar' ? 'تسجيل بصمة / Face ID / مفتاح أمان' : 'Enroll Passkey (Face ID / Touch ID)'}
          </button>
          <button
            type="button"
            data-testid="passkey-authenticate-btn"
            onClick={() => void handleAuthenticatePasskey()}
            className="holo-btn"
            style={{ minHeight: '32px', fontSize: '0.76rem', padding: '0.25rem 0.75rem' }}
          >
            {language === 'ar' ? 'دخول بيومتري / تصعيد Step-Up' : 'Biometric Sign-In / Step-Up'}
          </button>
          <button
            type="button"
            data-testid="passkey-generate-recovery-btn"
            onClick={() => void handleGenerateRecoveryCodes()}
            className="holo-btn"
            style={{ minHeight: '32px', fontSize: '0.76rem', padding: '0.25rem 0.75rem' }}
          >
            {language === 'ar' ? 'توليد رموز استرداد طوارئ' : 'Rotate Recovery Codes'}
          </button>
        </div>

        {passkeyStatus && passkeyStatus.devices.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {passkeyStatus.devices.map((dev) => (
              <div
                key={dev.credentialId}
                className="holo-panel-subtle"
                style={{
                  padding: '0.45rem 0.65rem',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.55rem',
                }}
              >
                <strong>{dev.deviceLabel}</strong>
                <span style={{ color: 'var(--text-muted)' }}>
                  ({dev.algorithm} • SignCnt: {dev.signCount})
                </span>
                <button
                  type="button"
                  onClick={() => void handleRevokePasskey(dev.credentialId)}
                  className="holo-btn holo-btn-danger"
                  style={{ minHeight: '24px', padding: '0.1rem 0.45rem', fontSize: '0.7rem' }}
                >
                  {language === 'ar' ? 'إلغاء' : 'Revoke'}
                </button>
              </div>
            ))}
          </div>
        )}

        {generatedRecoveryCodes.length > 0 && (
          <div
            data-testid="passkey-recovery-codes-box"
            className="holo-panel-subtle"
            style={{ padding: '0.6rem 0.75rem', fontSize: '0.75rem', borderColor: 'var(--status-warning)' }}
          >
            <strong style={{ display: 'block', marginBottom: '0.3rem', color: 'var(--status-warning)' }}>
              {language === 'ar'
                ? 'رموز استرداد الطوارئ أحادية الاستخدام (احفظها فوراً — لا تُخزن نصياً):'
                : 'One-Time Emergency Recovery Codes (Save immediately — hashed via PBKDF2):'}
            </strong>
            <div className="tabular-nums" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {generatedRecoveryCodes.map((code) => (
                <code key={code} style={{ padding: '2px 6px', borderRadius: '4px', background: 'rgba(0,0,0,0.28)' }}>
                  {code}
                </code>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', alignItems: 'center', fontSize: '0.74rem' }}>
          <input
            type="text"
            data-testid="passkey-recovery-redeem-input"
            value={recoveryCodeInput}
            onChange={(e) => setRecoveryCodeInput(e.target.value)}
            placeholder={language === 'ar' ? 'استرداد الوصول برمز طوارئ أحادي الاستخدام (TRIL-...)' : 'Redeem emergency one-time recovery code (TRIL-...)'}
            className="holo-input"
            style={{ maxWidth: '320px', minHeight: '28px', fontSize: '0.74rem' }}
          />
          <button
            type="button"
            data-testid="passkey-recovery-redeem-btn"
            onClick={() => void handleRedeemRecoveryCode()}
            className="holo-btn"
            style={{ minHeight: '28px', padding: '0.15rem 0.6rem', fontSize: '0.73rem' }}
          >
            {language === 'ar' ? 'استرداد الطوارئ' : 'Redeem Code'}
          </button>
        </div>
      </section>

      {/* 1.7 لوحة اختيار الإقليم السحابي والعزل عن medinsup.com وقياسات الكمون والأداء خارج العينة */}
      <section
        data-testid="region-latency-telemetry-panel"
        className="holo-panel"
        style={{ padding: '1.1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.55rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Activity size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800 }}>
              {language === 'ar'
                ? 'مصفوفة اختيار الإقليم السحابي، عزل النطاق، وكمون خط الأنابيب (v1.2 Cloudflare Architecture)'
                : 'Cloud Region Decision Matrix, Subdomain Isolation & 8-Stage Latency Telemetry'}
            </h3>
            <span className="holo-badge holo-badge-success">
              {benchmarkMatrix?.targetDomain ?? 'trilunair.medinsup.com'} ≠ medinsup.com
            </span>
          </div>
          <span className="holo-badge holo-badge-warning">
            {benchmarkMatrix?.selectionStatus ?? 'PROVISIONAL_PENDING_REGIONAL_CLOUD_PROBES'}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '0.65rem',
            fontSize: '0.76rem',
          }}
        >
          <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
            <strong>{language === 'ar' ? 'الإقليم المرشح الأعلى تقييماً' : 'Top Ranked Hosting Candidate'}</strong>
            <div style={{ marginTop: '0.25rem', color: 'var(--text-secondary)' }}>
              {benchmarkMatrix
                ? `${language === 'ar' ? benchmarkMatrix.recommendedPrimaryOption.regionNameAr : benchmarkMatrix.recommendedPrimaryOption.regionNameEn} (${benchmarkMatrix.recommendedPrimaryOption.weightedScore}/100)`
                : 'Tokyo, Japan (ap-northeast-1 / ap-tokyo-1)'}
            </div>
            <div className="tabular-nums" style={{ color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              Probe: {benchmarkMatrix?.recommendedPrimaryOption.regionalMeasurementStatus ?? 'NOT_MEASURED'} • $
              {benchmarkMatrix?.recommendedPrimaryOption.monthlyCostUsd.toFixed(2) ?? '12.00'}/mo
            </div>
          </div>

          <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
            <strong>{language === 'ar' ? 'كمون الإشارة إلى القرار (P50 / P95 / P99)' : 'Signal-to-Decision Latency (P50 / P95 / P99)'}</strong>
            <div className="tabular-nums" style={{ marginTop: '0.25rem', color: 'var(--text-secondary)' }}>
              P50: {latencySnapshot?.stages?.totalSignalToDecisionMs?.p50Ms ?? 0}ms • P95:{' '}
              {latencySnapshot?.stages?.totalSignalToDecisionMs?.p95Ms ?? 0}ms • P99:{' '}
              {latencySnapshot?.stages?.totalSignalToDecisionMs?.p99Ms ?? 0}ms
            </div>
            <div className="tabular-nums" style={{ color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              Council Deadline: {latencySnapshot?.councilDeadlineMs ?? 2200}ms • Cost Skips:{' '}
              {latencySnapshot?.counters.costAwareCloudInferenceSkips ?? 0}
            </div>
          </div>

          <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.75rem' }}>
            <strong>{language === 'ar' ? 'تقييم خارج العينة بعد التكاليف (Out-of-Sample)' : 'Out-of-Sample Net-of-Cost Walk-Forward'}</strong>
            <div className="tabular-nums" style={{ marginTop: '0.25rem', color: 'var(--text-secondary)' }}>
              {walkForwardEval
                ? `Friction Saved: $${walkForwardEval.outOfSampleComparison.improvements.totalFrictionSavedUsd.toFixed(2)} • ΔSharpe: ${walkForwardEval.outOfSampleComparison.improvements.sharpeDelta >= 0 ? '+' : ''}${walkForwardEval.outOfSampleComparison.improvements.sharpeDelta}`
                : 'Evaluating BTC-USD 15m OOS friction...'}
            </div>
            <div style={{ color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              {language === 'ar' ? 'يشمل العمولات والسبريد والانزلاق وتكلفة AI والاستضافة' : 'Net of Spot fees, spread, slippage, AI & hosting'}
            </div>
          </div>
        </div>
      </section>

      {/* 2. قائمة التحقق الخماسية وبوابة القفل السيادي لوضع التداول */}
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

        {/* بوابة التحقق من القفل السيادي لوضع التداول (Permanent PAPER Release Lock Gate) */}
        <section
          className="holo-panel"
          style={{ padding: '1.1rem 1.2rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <KeyRound size={18} style={{ color: 'var(--status-warning)' }} aria-hidden="true" />
              <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800 }}>
                {language === 'ar'
                  ? 'بوابة وضع التداول السيادي (مقفلة على PAPER)'
                  : 'Trading Mode Gate (Locked to PAPER in v1.1)'}
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
                <span>{language === 'ar' ? 'سر المسؤول المشفر (Admin Secret)' : 'Administrator Secret'}</span>
                <span className="tabular-nums" style={{ color: 'var(--status-success)', fontSize: '0.72rem' }}>
                  {sessionStatus?.authConfigured
                    ? 'PBKDF2-SHA256 Active'
                    : 'Fail-Closed (Env Secret Required)'}
                </span>
              </label>
              <input
                id="gov-admin-pin"
                data-testid="gov-admin-pin-input"
                type="password"
                autoComplete="off"
                placeholder="••••••••••••"
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
                  ? 'عبارة التحقق السيادية (مقفلة أمنياً على PAPER في v1.1.0-cloud-paper):'
                  : 'Sovereign verification phrase (permanently locked to PAPER in v1.1.0-cloud-paper):'}
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
                  ? 'أدرك أن الإصدار v1.1.0-cloud-paper يفرض قفلاً دائماً على التداول الورقي (PAPER) مع liveAuthorized=false ويرفض أي تفعيل للتداول الحقيقي.'
                  : 'I understand release v1.1.0-cloud-paper enforces a permanent PAPER execution lock (liveAuthorized=false) and rejects LIVE mode activation.'}
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
                  ? 'التحقق من قفل وضع التداول السيادي (LIVE مقفل على PAPER)'
                  : 'Verify Trading Gate (LIVE Permanently Locked to PAPER)'}
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
