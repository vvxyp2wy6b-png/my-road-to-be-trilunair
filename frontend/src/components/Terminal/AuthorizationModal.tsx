/**
 * نافذة التصريح الموحدة لتنفيذ الصفقات (Unified Trade Authorization Modal)
 * تُستخدم بشكل متطابق تماماً للأوامر القادمة من الصوت (VOICE)، المحادثة النصية (TEXT)،
 * أو تذكرة التداول المباشرة (TERMINAL) — لا يمكن لأي مسار تجاوز هذه البوابة!
 */

import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  KeyRound,
  MessageSquare,
  Mic,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  X,
  XCircle,
} from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import { formatCurrency, formatNumber } from '../../i18n/translations';
import type { CommandSource, TradeProposalEvaluation } from '../../types/trilunair';

export interface ExecuteOrderConfirmPayload {
  proposalId: string;
  confirmedByUser: boolean;
  adminPin?: string;
  source: CommandSource;
}

export interface AuthorizationModalProps {
  evaluation: TradeProposalEvaluation | null;
  isOpen?: boolean;
  isExecuting?: boolean;
  executionError?: string | null;
  onClose: () => void;
  onConfirmExecution: (payload: ExecuteOrderConfirmPayload) => Promise<void>;
}

export const AuthorizationModal: React.FC<AuthorizationModalProps> = (props) => {
  const visible = (props.isOpen ?? true) && props.evaluation !== null;
  if (!visible || !props.evaluation) {
    return null;
  }
  return (
    <AuthorizationModalDialog
      key={props.evaluation.proposalId}
      {...props}
      evaluation={props.evaluation}
    />
  );
};

interface AuthorizationModalDialogProps extends Omit<AuthorizationModalProps, 'evaluation'> {
  evaluation: TradeProposalEvaluation;
}

const AuthorizationModalDialog: React.FC<AuthorizationModalDialogProps> = ({
  evaluation,
  isExecuting = false,
  executionError = null,
  onClose,
  onConfirmExecution,
}) => {
  const { language } = useTheme();
  const [adminPin, setAdminPin] = useState<string>('');
  const [confirmedCheckbox, setConfirmedCheckbox] = useState<boolean>(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isExecuting) {
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isExecuting, onClose]);

  const { proposal, estimatedCosts, riskAssessment, tradingMode, requiresLivePin, status } =
    evaluation;
  const isRejected = status === 'REJECTED_BY_RISK' || !riskAssessment.passed;

  const renderSourceBadge = (source: CommandSource) => {
    if (source === 'VOICE') {
      return (
        <span className="holo-badge holo-badge-accent" data-testid="auth-source-badge">
          <Mic size={13} aria-hidden="true" />
          <span>{language === 'ar' ? 'أمر صوتي VOICE' : 'Voice Command (VOICE)'}</span>
        </span>
      );
    }
    if (source === 'TEXT') {
      return (
        <span className="holo-badge holo-badge-accent" data-testid="auth-source-badge">
          <MessageSquare size={13} aria-hidden="true" />
          <span>{language === 'ar' ? 'أمر نصي TEXT' : 'Text Command (TEXT)'}</span>
        </span>
      );
    }
    return (
      <span className="holo-badge holo-badge-accent" data-testid="auth-source-badge">
        <Terminal size={13} aria-hidden="true" />
        <span>{language === 'ar' ? 'تذكرة التداول TERMINAL' : 'Order Ticket (TERMINAL)'}</span>
      </span>
    );
  };

  const canAuthorize =
    !isRejected &&
    confirmedCheckbox &&
    (!requiresLivePin || adminPin.trim().length >= 4) &&
    !isExecuting;

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isRejected) return;
    setLocalError(null);

    if (requiresLivePin && adminPin.trim().length < 4) {
      setLocalError(
        language === 'ar'
          ? 'يتطلب وضع التداول الحقيقي (LIVE) إدخال رمز المسؤول السري (Admin PIN).'
          : 'LIVE trading requires entering a valid Admin PIN.'
      );
      return;
    }

    try {
      await onConfirmExecution({
        proposalId: evaluation.proposalId,
        confirmedByUser: true,
        adminPin: requiresLivePin ? adminPin.trim() : undefined,
        source: proposal.source,
      });
    } catch (err) {
      setLocalError(
        err instanceof Error
          ? err.message
          : language === 'ar'
            ? 'فشل تنفيذ الأمر في بوابة التصاريح.'
            : 'Order execution failed at authorization gateway.'
      );
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      data-testid="authorization-modal"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        background: 'rgba(var(--bg-surface-rgb), 0.82)',
        backdropFilter: 'blur(var(--fx-blur-radius))',
      }}
    >
      <div
        className="holo-panel"
        style={{
          width: '100%',
          maxWidth: '640px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '1.25rem 1.35rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.95rem',
        }}
      >
        {/* رأس نافذة التصريح */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              {isRejected ? (
                <ShieldAlert size={20} style={{ color: 'var(--status-danger)' }} aria-hidden="true" />
              ) : (
                <ShieldCheck size={20} style={{ color: 'var(--status-success)' }} aria-hidden="true" />
              )}
              <h2 id="auth-modal-title" style={{ margin: 0, fontSize: '1.08rem', fontWeight: 800 }}>
                {language === 'ar'
                  ? 'بوابة التصريح النهائي لتنفيذ الصفقة'
                  : 'Trade Execution Authorization Gateway'}
              </h2>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
              {renderSourceBadge(proposal.source)}
              <span
                className={`holo-badge ${
                  tradingMode === 'LIVE' ? 'holo-badge-danger' : 'holo-badge-success'
                }`}
              >
                {tradingMode === 'LIVE'
                  ? language === 'ar'
                    ? 'وضع حقيقي (LIVE)'
                    : 'LIVE MODE'
                  : language === 'ar'
                    ? 'وضع ورقي آمن (PAPER)'
                    : 'PAPER MODE'}
              </span>
              <span className="holo-badge tabular-nums">ID: {evaluation.proposalId}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            disabled={isExecuting}
            className="holo-btn"
            aria-label={language === 'ar' ? 'إغلاق النافذة' : 'Close Modal'}
            style={{ minHeight: '34px', padding: '0.3rem 0.55rem' }}
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        {/* تفاصيل الصفقة المقترحة */}
        <div
          className="holo-panel-subtle"
          style={{
            padding: '0.8rem 0.95rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(135px, 1fr))',
            gap: '0.65rem',
            fontSize: '0.82rem',
          }}
        >
          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.74rem' }}>
              {language === 'ar' ? 'الأصل والاتجاه' : 'Symbol & Side'}
            </div>
            <strong
              className="tabular-nums"
              style={{
                fontSize: '0.96rem',
                color: proposal.side === 'BUY' ? 'var(--status-success)' : 'var(--status-danger)',
              }}
            >
              {proposal.side} {proposal.symbol} ({proposal.orderType})
            </strong>
          </div>

          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.74rem' }}>
              {language === 'ar' ? 'الكمية' : 'Quantity'}
            </div>
            <strong className="tabular-nums" style={{ fontSize: '0.95rem' }}>
              {formatNumber(proposal.quantity, 4)}
            </strong>
          </div>

          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.74rem' }}>
              {language === 'ar' ? 'السعر المرجعي' : 'Reference Price'}
            </div>
            <strong className="tabular-nums" style={{ fontSize: '0.95rem' }}>
              {formatCurrency(proposal.referencePrice)}
            </strong>
          </div>

          <div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.74rem' }}>
              {language === 'ar' ? 'إجمالي القيمة الاسمية' : 'Notional Value'}
            </div>
            <strong className="tabular-nums" style={{ fontSize: '0.95rem', color: 'var(--accent-primary)' }}>
              {formatCurrency(estimatedCosts.notionalUsd)}
            </strong>
          </div>
        </div>

        {proposal.rationale && (
          <div
            className="holo-panel-subtle"
            style={{ padding: '0.55rem 0.8rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}
          >
            <strong style={{ color: 'var(--accent-primary)' }}>
              {language === 'ar' ? 'المبرر التحليلي: ' : 'Analytical Rationale: '}
            </strong>
            <span>{proposal.rationale}</span>
          </div>
        )}

        {/* التكاليف التقديرية وتقييم المخاطر الحتمي */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '0.75rem',
          }}
        >
          <div
            className="holo-panel-subtle"
            style={{ padding: '0.75rem 0.85rem', display: 'flex', flexDirection: 'column', gap: '0.32rem', fontSize: '0.79rem' }}
          >
            <strong style={{ color: 'var(--accent-primary)', marginBottom: '0.15rem' }}>
              {language === 'ar' ? 'تفصيل تكاليف التنفيذ' : 'Execution Cost Breakdown'}
            </strong>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Spread:</span>
              <span className="tabular-nums">{formatCurrency(estimatedCosts.spreadCostUsd)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Commission:</span>
              <span className="tabular-nums">{formatCurrency(estimatedCosts.commissionUsd)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Slippage:</span>
              <span className="tabular-nums">{formatCurrency(estimatedCosts.slippageCostUsd)}</span>
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                borderTop: '1px solid var(--border-subtle)',
                paddingTop: '0.3rem',
                fontWeight: 700,
              }}
            >
              <span>{language === 'ar' ? 'الإجمالي:' : 'Total Cost:'}</span>
              <span className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
                {formatCurrency(estimatedCosts.totalEstimatedCostUsd)} ({formatNumber(estimatedCosts.costBps, 1)} bps)
              </span>
            </div>
          </div>

          <div
            className="holo-panel-subtle"
            style={{ padding: '0.75rem 0.85rem', display: 'flex', flexDirection: 'column', gap: '0.32rem', fontSize: '0.79rem' }}
          >
            <strong style={{ color: 'var(--accent-primary)', marginBottom: '0.15rem' }}>
              {language === 'ar' ? 'مؤشرات المخاطر بعد الصفقة' : 'Post-Trade Risk Metrics'}
            </strong>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>{language === 'ar' ? 'درجة المخاطرة:' : 'Risk Score:'}</span>
              <strong className="tabular-nums">
                {riskAssessment.riskScore}/100 ({riskAssessment.riskLevel})
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>{language === 'ar' ? 'التركز بعد التنفيذ:' : 'Post-Trade Weight:'}</span>
              <span className="tabular-nums">{formatNumber(riskAssessment.postTradeConcentrationPct, 2)}%</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>{language === 'ar' ? 'تأثير VaR اليومي:' : 'VaR 95% Impact:'}</span>
              <span className="tabular-nums">{formatCurrency(riskAssessment.varImpactUsd)}</span>
            </div>
          </div>
        </div>

        {/* قائمة فحوصات المخاطر التفصيلية */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <strong style={{ fontSize: '0.82rem' }}>
            {language === 'ar' ? 'سجل التحقق الحتمي من المخاطر:' : 'Deterministic Safety Verification:'}
          </strong>
          {riskAssessment.checks.map((chk) => (
            <div
              key={chk.code}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                fontSize: '0.78rem',
                padding: '0.32rem 0.55rem',
                borderRadius: '6px',
                background: chk.passed ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
                color: chk.passed ? 'var(--status-success)' : 'var(--status-danger)',
              }}
            >
              {chk.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
              <span>{language === 'ar' ? chk.messageAr : chk.messageEn}</span>
            </div>
          ))}
        </div>

        {/* في حال رفض محرك المخاطر: حظر التنفيذ نهائياً وتوضيح المخالفات */}
        {isRejected ? (
          <div
            role="alert"
            data-testid="auth-rejected-banner"
            style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--status-danger-bg)',
              border: '1px solid var(--status-danger)',
              color: 'var(--status-danger)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.45rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 800 }}>
              <AlertTriangle size={18} aria-hidden="true" />
              <span>
                {language === 'ar'
                  ? 'تم حظر التنفيذ نهائياً بواسطة محرك المخاطر الحتمي (REJECTED_BY_RISK)'
                  : 'Execution Permanently Blocked by Deterministic Risk Engine (REJECTED_BY_RISK)'}
              </span>
            </div>
            {riskAssessment.violations.length > 0 && (
              <ul style={{ margin: 0, paddingInlineStart: '1.2rem', fontSize: '0.8rem' }}>
                {riskAssessment.violations.map((v, idx) => (
                  <li key={idx}>{v}</li>
                ))}
              </ul>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
              <button type="button" onClick={onClose} className="holo-btn">
                {language === 'ar' ? 'إغلاق وتعديل الكمية' : 'Close & Adjust Order'}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleConfirm} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {requiresLivePin && (
              <div
                className="holo-panel-subtle"
                style={{
                  padding: '0.75rem 0.85rem',
                  borderColor: 'var(--status-warning)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.4rem',
                }}
              >
                <label
                  htmlFor="auth-live-pin-input"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    color: 'var(--status-warning)',
                  }}
                >
                  <KeyRound size={15} aria-hidden="true" />
                  <span>
                    {language === 'ar'
                      ? 'رمز المسؤول السري مطلوب للتداول الحقيقي (Admin PIN)'
                      : 'Admin PIN Required for LIVE Execution'}
                  </span>
                </label>
                <input
                  id="auth-live-pin-input"
                  data-testid="auth-live-pin-input"
                  type="password"
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder={language === 'ar' ? 'أدخل رمز PIN السري...' : 'Enter Admin PIN...'}
                  value={adminPin}
                  onChange={(e) => setAdminPin(e.target.value)}
                  className="holo-input tabular-nums"
                  required
                />
              </div>
            )}

            {/* ختم التأكيد الهولوغرامي الفاخر (Premium Holographic Confirmation Seal — Section 5) */}
            <div
              data-testid="holographic-confirmation-seal"
              className="holo-panel-subtle"
              style={{
                padding: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.85rem',
                borderColor: confirmedCheckbox ? 'var(--accent-primary)' : 'var(--border-subtle)',
                boxShadow: confirmedCheckbox ? 'var(--shadow-glow-strong)' : 'none',
              }}
            >
              <div
                aria-hidden="true"
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '999px',
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '2px double var(--accent-primary)',
                  background:
                    'radial-gradient(circle, rgba(var(--accent-primary-rgb), 0.22) 0%, transparent 72%)',
                  color: 'var(--accent-primary)',
                  fontWeight: 800,
                  fontSize: '0.72rem',
                  letterSpacing: '0.04em',
                }}
              >
                SEAL
              </div>
              <div style={{ fontSize: '0.79rem', color: 'var(--text-secondary)' }}>
                <strong style={{ display: 'block', color: 'var(--accent-primary)' }}>
                  {language === 'ar'
                    ? 'ختم التصريح السيادي الموثق (Holographic Confirmation Seal)'
                    : 'Sovereign Holographic Confirmation Seal'}
                </strong>
                <span>
                  {language === 'ar'
                    ? 'الكلمة المنطوقة "أكد" لا تكفي بمفردها لتفويض معاملة مالية؛ يتطلب التنفيذ تفعيل هذا الختم يدوياً بعد التحقق المجدد.'
                    : 'A spoken "confirm" cannot authorize a transaction alone; explicit manual seal activation and revalidation are mandatory.'}
                </span>
              </div>
            </div>

            <label
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.55rem',
                fontSize: '0.82rem',
                cursor: 'pointer',
                color: 'var(--text-secondary)',
              }}
            >
              <input
                type="checkbox"
                data-testid="auth-confirm-checkbox"
                checked={confirmedCheckbox}
                onChange={(e) => setConfirmedCheckbox(e.target.checked)}
                style={{ marginTop: '0.2rem', accentColor: 'var(--accent-primary)' }}
              />
              <span>
                {language === 'ar'
                  ? 'أقر بمراجعة تفاصيل الأمر والتكاليف التقديرية وتقييم المخاطر وأصرح بتنفيذ الصفقة رسمياً.'
                  : 'I have reviewed the order parameters, estimated costs, and risk checks, and explicitly authorize execution.'}
              </span>
            </label>

            {(localError || executionError) && (
              <div
                role="alert"
                style={{
                  padding: '0.55rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--status-danger-bg)',
                  color: 'var(--status-danger)',
                  fontSize: '0.8rem',
                }}
              >
                {localError || executionError}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.6rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={onClose}
                disabled={isExecuting}
                className="holo-btn"
              >
                {language === 'ar' ? 'إلغاء الأمر' : 'Cancel'}
              </button>
              <button
                type="submit"
                data-testid="authorize-execute-btn"
                disabled={!canAuthorize}
                className="holo-btn holo-btn-buy"
              >
                <ShieldCheck size={16} aria-hidden="true" />
                <span>
                  {isExecuting
                    ? language === 'ar'
                      ? 'جاري التنفيذ الرسمي...'
                      : 'Executing Order...'
                    : language === 'ar'
                      ? 'تأكيد وتنفيذ الصفقة رسمياً'
                      : 'Authorize & Execute Order'}
                </span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default AuthorizationModal;
