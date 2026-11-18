/**
 * منظومة الهوية السيادية، الشعار ثلاثي الأحرف (TRM)، وبوابة دخول أدمن المنصة متعددة العوامل
 * المشروع: طريقي إلى التريليون — د. ماجد (TRM • Trilunair × Road × Majed)
 */

import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Copy,
  Fingerprint,
  KeyRound,
  Lock,
  Mail,
  Phone,
  ShieldCheck,
  Smartphone,
  Sparkles,
  UserCheck,
  X,
} from 'lucide-react';
import { trilunairApi } from '../../api/client';
import type { Language } from '../../types/trilunair';

export const TrmMonogramCrest: React.FC<{ size?: number }> = ({ size = 50 }) => (
  <div
    style={{
      position: 'relative',
      width: `${size}px`,
      height: `${size}px`,
      flexShrink: 0,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}
    title="TRM — Trilunair • Road • Majed (طريقي إلى التريليون • د. ماجد)"
  >
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="شعار TRM — Trilunair Road Majed"
      style={{ filter: 'drop-shadow(0 0 12px rgba(var(--accent-primary-rgb), 0.45))' }}
    >
      <defs>
        <linearGradient id="trmShieldGrad" x1="6" y1="4" x2="58" y2="60" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="var(--bg-surface)" />
          <stop offset="100%" stopColor="var(--bg-base)" />
        </linearGradient>
        <linearGradient id="trmGoldGrad" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="var(--accent-secondary)" />
          <stop offset="55%" stopColor="var(--accent-primary)" />
          <stop offset="100%" stopColor="var(--accent-tertiary)" />
        </linearGradient>
      </defs>
      {/* الدرع الثماني السيادي */}
      <polygon
        points="20,3 44,3 61,20 61,44 44,61 20,61 3,44 3,20"
        fill="url(#trmShieldGrad)"
        stroke="url(#trmGoldGrad)"
        strokeWidth="2.4"
      />
      <polygon
        points="22,7 42,7 57,22 57,42 42,57 22,57 7,42 7,22"
        fill="none"
        stroke="var(--border-holo)"
        strokeWidth="1"
        strokeDasharray="3 2"
      />
      {/* قوس مسار التريليون الصاعد أعلى الشعار */}
      <path
        d="M16 18 C25 11, 39 11, 48 18"
        stroke="url(#trmGoldGrad)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <circle cx="32" cy="11.5" r="2.3" fill="var(--accent-primary)" />
      {/* الأحرف الثلاثة المترابطة TRM */}
      <text
        x="32"
        y="37"
        textAnchor="middle"
        fill="url(#trmGoldGrad)"
        style={{
          fontFamily: "'Cairo', 'IBM Plex Mono', sans-serif",
          fontWeight: 900,
          fontSize: '18.5px',
          letterSpacing: '0.6px',
        }}
      >
        TRM
      </text>
      {/* الهوية العربية المصغرة أسفل الأحرف الثلاثة */}
      <text
        x="32"
        y="50.5"
        textAnchor="middle"
        fill="var(--text-secondary)"
        style={{
          fontFamily: "'Cairo', sans-serif",
          fontWeight: 700,
          fontSize: '7.5px',
        }}
      >
        ت • ر • م
      </text>
    </svg>
  </div>
);

export interface AdminIdentitySummary {
  enrolled: boolean;
  authenticated: boolean;
  displayName: string;
  emailMasked: string | null;
  phoneMasked: string | null;
  totpVerified: boolean;
}

interface AdminSovereignGateModalProps {
  isOpen: boolean;
  language: Language;
  identity: AdminIdentitySummary | null;
  onClose: () => void;
  onAuthenticated: (summary: AdminIdentitySummary, notice: string) => void;
}

export const AdminSovereignGateModal: React.FC<AdminSovereignGateModalProps> = ({
  isOpen,
  language,
  identity,
  onClose,
  onAuthenticated,
}) => {
  const isAr = language === 'ar';
  const [activeTab, setActiveTab] = useState<'login' | 'enroll'>(
    identity?.enrolled ? 'login' : 'enroll'
  );

  // حقول التأسيس والدخول لأدمن المنصة (د. ماجد)
  const [displayName, setDisplayName] = useState<string>(identity?.displayName || 'د. ماجد');
  const [email, setEmail] = useState<string>('');
  const [phone, setPhone] = useState<string>('+9665');
  const [verificationKey, setVerificationKey] = useState<string>('');
  const [currentVerificationKey, setCurrentVerificationKey] = useState<string>('');
  const [totpCode, setTotpCode] = useState<string>('');

  // مخرجات إعداد تطبيق المصادقة (RFC 6238 Authenticator)
  const [pendingSetup, setPendingSetup] = useState<{
    secretBase32: string;
    otpauthUri: string;
    instructionsAr: string;
  } | null>(null);

  const [secondsLeft, setSecondsLeft] = useState<number>(30 - (Math.floor(Date.now() / 1000) % 30));
  const [busy, setBusy] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (identity?.enrolled) {
      setActiveTab('login');
      setDisplayName(identity.displayName || 'د. ماجد');
    } else {
      setActiveTab('enroll');
    }
  }, [identity?.enrolled, identity?.displayName]);

  useEffect(() => {
    if (!isOpen) return;
    const timer = window.setInterval(() => {
      setSecondsLeft(30 - (Math.floor(Date.now() / 1000) % 30));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isOpen]);

  if (!isOpen) return null;

  const copyText = async (val: string, label: string) => {
    try {
      await navigator.clipboard.writeText(val);
      setSuccessMsg(isAr ? `تم نسخ ${label} إلى الحافظة بنجاح.` : `Copied ${label}.`);
    } catch {
      setErrorMsg(isAr ? 'تعذر النسخ التلقائي — يمكنك تحديد النص ونسخه يدوياً.' : 'Manual copy required.');
    }
  };

  const handleEnrollSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setBusy(true);
    try {
      const res = await trilunairApi.enrollAdminIdentity({
        displayName,
        email,
        phone,
        verificationKey,
        currentVerificationKey: currentVerificationKey || undefined,
        rotateTotp: true,
      });
      setPendingSetup({
        secretBase32: res.authenticatorSetup.secretBase32,
        otpauthUri: res.authenticatorSetup.otpauthUri,
        instructionsAr: res.authenticatorSetup.instructionsAr,
      });
      setSuccessMsg(
        isAr
          ? 'تم حفظ البريد الإلكتروني ورقم الجوال ومفتاح التحقق مشفرةً بـ AES-256-GCM! الآن أضف مفتاح المصادقة أدناه في تطبيق Authenticator وأدخل الرمز المكون من 6 أرقام للتأكيد.'
          : 'Admin credentials encrypted! Add the Base32 key to your Authenticator app and confirm the 6-digit code.'
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'فشل تأسيس هوية الأدمن');
    } finally {
      setBusy(false);
    }
  };

  const handleConfirmTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setBusy(true);
    try {
      await trilunairApi.confirmAdminTotp({
        verificationKey,
        totpCode,
      });
      // تسجيل الدخول مباشرة بعد تأكيد الإقران
      const loginRes = await trilunairApi.loginAdminMfa({
        email,
        phone,
        verificationKey,
        totpCode,
      }).catch(() => null);

      const updated: AdminIdentitySummary = {
        enrolled: true,
        authenticated: Boolean(loginRes?.authenticated ?? true),
        displayName,
        emailMasked: loginRes?.emailMasked || email.slice(0, 2) + '••••@' + (email.split('@')[1] || ''),
        phoneMasked: loginRes?.phoneMasked || phone.slice(0, 4) + '••••••' + phone.slice(-2),
        totpVerified: true,
      };
      setPendingSetup(null);
      setTotpCode('');
      onAuthenticated(
        updated,
        isAr
          ? 'تم تفعيل تطبيق المصادقة الثنائية وتوثيق حساب الأدمن (د. ماجد — TRM) بنجاح!'
          : 'TRM Sovereign Admin MFA enrolled & verified!'
      );
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'رمز المصادقة غير صحيح');
    } finally {
      setBusy(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setBusy(true);
    try {
      const res = await trilunairApi.loginAdminMfa({
        email,
        phone,
        verificationKey,
        totpCode,
      });
      onAuthenticated(
        {
          enrolled: true,
          authenticated: true,
          displayName: res.displayName,
          emailMasked: res.emailMasked,
          phoneMasked: res.phoneMasked,
          totpVerified: true,
        },
        isAr
          ? `مرحباً ${res.displayName} — تم التحقق من العوامل الأربعة (البريد + الجوال + مفتاح التحقق + Authenticator) بنجاح.`
          : `Welcome ${res.displayName} — 4-Factor TRM Admin session active.`
      );
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'بيانات الدخول غير صحيحة');
    } finally {
      setBusy(false);
    }
  };

  const handlePasskeyLogin = async () => {
    setErrorMsg(null);
    setBusy(true);
    try {
      await trilunairApi.authenticateWithPasskey();
      onAuthenticated(
        {
          enrolled: identity?.enrolled ?? true,
          authenticated: true,
          displayName: identity?.displayName || 'د. ماجد',
          emailMasked: identity?.emailMasked || null,
          phoneMasked: identity?.phoneMasked || null,
          totpVerified: identity?.totpVerified ?? true,
        },
        isAr
          ? 'تمت المصادقة البيومترية عبر مفتاح المرور (WebAuthn Passkey) لأدمن المنصة بنجاح.'
          : 'Authenticated via Hardware/Biometric Passkey.'
      );
      onClose();
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : isAr
          ? 'تعذر التحقق عبر Passkey — تأكد من تسجيل بصمة الجهاز أولاً أو استخدم الدخول الرباعي أدناه.'
          : 'Passkey login unavailable.'
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="trm-admin-gate-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1200,
        background: 'rgba(4, 6, 12, 0.84)',
        backdropFilter: 'blur(14px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        className="holo-panel"
        style={{
          width: '100%',
          maxWidth: '640px',
          maxHeight: '92vh',
          overflowY: 'auto',
          padding: '1.35rem 1.5rem',
          border: '1px solid var(--accent-primary)',
          boxShadow: 'var(--shadow-glow-strong)',
        }}
      >
        {/* رأس البوابة مع شعار TRM ثلاثي الأحرف */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.85rem',
            paddingBottom: '0.95rem',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <TrmMonogramCrest size={54} />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
                <span className="holo-badge holo-badge-accent" style={{ fontWeight: 800 }}>
                  TRM • Trilunair × Majed
                </span>
                <span className="holo-badge holo-badge-success">PAPER SAFE LOCK</span>
              </div>
              <h2
                id="trm-admin-gate-title"
                style={{ margin: '0.25rem 0 0', fontSize: '1.15rem', fontWeight: 800 }}
              >
                {isAr
                  ? 'بوابة الهوية والدخول السيادي لأدمن المنصة (د. ماجد)'
                  : 'TRM Sovereign Platform Admin MFA Gate'}
              </h2>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {isAr
                  ? 'حماية رباعية العوامل: البريد الإلكتروني + رقم الجوال + مفتاح التحقق السري + تطبيق المصادقة (Authenticator)'
                  : '4-Factor Admin Verification: Email + Phone + Secret Verification Key + TOTP Authenticator'}
              </div>
            </div>
          </div>

          <button
            type="button"
            className="holo-btn"
            onClick={onClose}
            aria-label={isAr ? 'إغلاق نافذة دخول الأدمن' : 'Close Admin Gate'}
            style={{ padding: '0.4rem' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* شريط حالة الهوية المسجلة */}
        {identity?.enrolled && (
          <div
            style={{
              marginTop: '0.85rem',
              padding: '0.6rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(var(--accent-primary-rgb), 0.08)',
              border: '1px solid var(--border-holo)',
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.8rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <UserCheck size={15} style={{ color: 'var(--accent-primary)' }} />
              <strong>{identity.displayName}</strong>
              <span className="fin-value" style={{ color: 'var(--text-secondary)' }}>
                ({identity.emailMasked} • {identity.phoneMasked})
              </span>
            </div>
            <span
              className={`holo-badge ${
                identity.authenticated ? 'holo-badge-success' : 'holo-badge-warning'
              }`}
            >
              {identity.authenticated
                ? isAr
                  ? 'جلسة أدمن موثقة نشطة'
                  : 'Verified Admin Session'
                : isAr
                ? 'بانتظار تسجيل الدخول'
                : 'Awaiting Sign-In'}
            </span>
          </div>
        )}

        {/* التبديل بين تسجيل الدخول وتأسيس/تحديث بيانات الأدمن */}
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.95rem' }}>
          <button
            id="trm-tab-login"
            type="button"
            className={`holo-btn ${activeTab === 'login' ? 'holo-btn-primary' : ''}`}
            style={{ flex: 1, justifyContent: 'center' }}
            onClick={() => {
              setActiveTab('login');
              setErrorMsg(null);
            }}
          >
            <Lock size={15} />
            {isAr ? 'دخول الأدمن (4 عوامل + Authenticator)' : 'Admin 4-Factor Login'}
          </button>
          <button
            id="trm-tab-enroll"
            type="button"
            className={`holo-btn ${activeTab === 'enroll' ? 'holo-btn-primary' : ''}`}
            style={{ flex: 1, justifyContent: 'center' }}
            onClick={() => {
              setActiveTab('enroll');
              setErrorMsg(null);
            }}
          >
            <Sparkles size={15} />
            {isAr ? 'تأسيس / تحديث بيانات الأدمن' : 'Enroll / Update Admin MFA'}
          </button>
        </div>

        {errorMsg && (
          <div
            role="alert"
            style={{
              marginTop: '0.85rem',
              padding: '0.65rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--status-danger-bg)',
              border: '1px solid var(--status-danger)',
              color: 'var(--text-primary)',
              fontSize: '0.83rem',
            }}
          >
            {errorMsg}
          </div>
        )}

        {successMsg && (
          <div
            role="status"
            style={{
              marginTop: '0.85rem',
              padding: '0.65rem 0.85rem',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--status-success-bg)',
              border: '1px solid var(--status-success)',
              color: 'var(--text-primary)',
              fontSize: '0.83rem',
            }}
          >
            {successMsg}
          </div>
        )}

        {activeTab === 'login' ? (
          <form onSubmit={handleLoginSubmit} style={{ marginTop: '1rem', display: 'grid', gap: '0.8rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
              <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Mail size={14} style={{ color: 'var(--accent-primary)' }} />
                  {isAr ? 'البريد الإلكتروني للأدمن' : 'Admin Email'}
                </span>
                <input
                  id="admin-login-email"
                  type="email"
                  required
                  dir="ltr"
                  className="holo-input"
                  placeholder="majed@domain.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>

              <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Phone size={14} style={{ color: 'var(--accent-primary)' }} />
                  {isAr ? 'رقم الجوال المعتمد' : 'Admin Phone Number'}
                </span>
                <input
                  id="admin-login-phone"
                  type="tel"
                  required
                  dir="ltr"
                  className="holo-input"
                  placeholder="+9665XXXXXXXX"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </label>
            </div>

            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <KeyRound size={14} style={{ color: 'var(--accent-primary)' }} />
                {isAr ? 'مفتاح التحقق السري للأدمن (Verification Key)' : 'Secret Verification Key'}
              </span>
              <input
                id="admin-login-vkey"
                type="password"
                required
                dir="ltr"
                className="holo-input"
                placeholder="••••••••••••"
                value={verificationKey}
                onChange={(e) => setVerificationKey(e.target.value)}
              />
            </label>

            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Smartphone size={14} style={{ color: 'var(--accent-primary)' }} />
                  {isAr
                    ? 'رمز تطبيق المصادقة (Authenticator — 6 أرقام)'
                    : 'Authenticator 6-Digit Code (TOTP)'}
                </span>
                <span className="fin-value" style={{ fontSize: '0.75rem', color: 'var(--accent-primary)' }}>
                  {isAr ? `يتجدد خلال ${secondsLeft} ث` : `Refreshes in ${secondsLeft}s`}
                </span>
              </span>
              <input
                id="admin-login-totp"
                type="text"
                inputMode="numeric"
                pattern="[0-9\s]{6,7}"
                maxLength={7}
                required
                dir="ltr"
                className="holo-input fin-value"
                style={{ fontSize: '1.15rem', letterSpacing: '0.35em', textAlign: 'center', fontWeight: 800 }}
                placeholder="000000"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
              />
            </label>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginTop: '0.3rem' }}>
              <button
                id="admin-login-submit-btn"
                type="submit"
                disabled={busy}
                className="holo-btn holo-btn-primary"
                style={{ flex: 2, justifyContent: 'center', minHeight: '42px', fontWeight: 800 }}
              >
                <ShieldCheck size={16} />
                {busy
                  ? isAr
                    ? 'جارٍ التحقق المشفر...'
                    : 'Verifying...'
                  : isAr
                  ? 'تسجيل دخول أدمن المنصة (TRM)'
                  : 'Sign In as Sovereign Admin'}
              </button>

              <button
                type="button"
                disabled={busy}
                onClick={() => void handlePasskeyLogin()}
                className="holo-btn"
                style={{ flex: 1, justifyContent: 'center', minHeight: '42px' }}
              >
                <Fingerprint size={16} />
                {isAr ? 'دخول بـ Passkey' : 'Passkey'}
              </button>
            </div>
          </form>
        ) : (
          <div style={{ marginTop: '1rem', display: 'grid', gap: '0.9rem' }}>
            <form onSubmit={handleEnrollSubmit} style={{ display: 'grid', gap: '0.75rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
                <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                  <span>{isAr ? 'الاسم واللقب القيادي' : 'Admin Display Name'}</span>
                  <input
                    type="text"
                    required
                    className="holo-input"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </label>

                <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                  <span>{isAr ? 'رقم الجوال الشخصي (دولي)' : 'Mobile Phone (+966...)'}</span>
                  <input
                    id="admin-enroll-phone"
                    type="tel"
                    required
                    dir="ltr"
                    className="holo-input"
                    placeholder="+9665XXXXXXXX"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </label>
              </div>

              <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                <span>{isAr ? 'البريد الإلكتروني الرسمي لأدمن المنصة' : 'Official Admin Email'}</span>
                <input
                  id="admin-enroll-email"
                  type="email"
                  required
                  dir="ltr"
                  className="holo-input"
                  placeholder="majed@domain.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>

              <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                <span>
                  {isAr
                    ? 'مفتاح التحقق السري الجديد (10 خانات فأكثر — يُحفظ بـ PBKDF2-SHA256)'
                    : 'New Secret Verification Key (min 10 chars)'}
                </span>
                <input
                  id="admin-enroll-vkey"
                  type="password"
                  required
                  minLength={10}
                  dir="ltr"
                  className="holo-input"
                  placeholder="مثال: Majed#TRM$2026!"
                  value={verificationKey}
                  onChange={(e) => setVerificationKey(e.target.value)}
                />
              </label>

              {identity?.enrolled && !identity?.authenticated && (
                <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                  <span>
                    {isAr
                      ? 'مفتاح التحقق الحالي (مطلوب لتأكيد ملكية الأدمن قبل التحديث)'
                      : 'Current Verification Key'}
                  </span>
                  <input
                    type="password"
                    required
                    dir="ltr"
                    className="holo-input"
                    value={currentVerificationKey}
                    onChange={(e) => setCurrentVerificationKey(e.target.value)}
                  />
                </label>
              )}

              <button
                id="admin-enroll-submit-btn"
                type="submit"
                disabled={busy}
                className="holo-btn holo-btn-primary"
                style={{ justifyContent: 'center', minHeight: '42px', fontWeight: 800 }}
              >
                <KeyRound size={16} />
                {busy
                  ? isAr
                    ? 'جارٍ التشفير وتوليد مفتاح المصادقة...'
                    : 'Encrypting & Generating TOTP...'
                  : isAr
                  ? 'حفظ الهوية وتوليد مفتاح تطبيق المصادقة (Authenticator)'
                  : 'Save Identity & Generate Authenticator Secret'}
              </button>
            </form>

            {pendingSetup && (
              <form
                onSubmit={handleConfirmTotp}
                style={{
                  padding: '0.95rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(var(--accent-primary-rgb), 0.09)',
                  border: '1px solid var(--accent-primary)',
                  display: 'grid',
                  gap: '0.7rem',
                }}
              >
                <div style={{ fontWeight: 800, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Smartphone size={16} style={{ color: 'var(--accent-primary)' }} />
                  {isAr
                    ? 'إقران تطبيق المصادقة (Google / Apple / Microsoft Authenticator)'
                    : 'Pair Your Authenticator App (RFC 6238)'}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {pendingSetup.instructionsAr}
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '0.5rem',
                    padding: '0.55rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg-base)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <code className="fin-value" style={{ fontSize: '0.92rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
                    {pendingSetup.secretBase32}
                  </code>
                  <button
                    type="button"
                    className="holo-btn"
                    onClick={() => void copyText(pendingSetup.secretBase32, 'مفتاح Authenticator')}
                  >
                    <Copy size={14} />
                    {isAr ? 'نسخ المفتاح' : 'Copy Key'}
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="holo-btn"
                    style={{ fontSize: '0.76rem' }}
                    onClick={() => void copyText(pendingSetup.otpauthUri, 'رابط otpauth://')}
                  >
                    <Copy size={13} />
                    {isAr ? 'نسخ رابط الإقران القياسي (otpauth://)' : 'Copy otpauth:// URI'}
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    id="admin-confirm-totp-input"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    required
                    dir="ltr"
                    className="holo-input fin-value"
                    style={{ flex: 1, minWidth: '150px', textAlign: 'center', fontSize: '1.1rem', letterSpacing: '0.3em', fontWeight: 800 }}
                    placeholder="000000"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                  />
                  <button
                    id="admin-confirm-totp-btn"
                    type="submit"
                    disabled={busy}
                    className="holo-btn holo-btn-primary"
                    style={{ fontWeight: 800 }}
                  >
                    <CheckCircle2 size={16} />
                    {isAr ? 'تأكيد وتفعيل الدخول' : 'Confirm & Activate'}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
