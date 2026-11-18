/**
 * منظومة الهوية السيادية، الشعار السداسي ثلاثي الأحرف (TMJ — TrilMajed | تريلماجد)،
 * وبوابة دخول أدمن المنصة متعددة العوامل بدون أي التباس بين كلمة السر الثابتة ورمز المصادقة المتغير (6 أرقام).
 */

import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  Fingerprint,
  KeyRound,
  Lock,
  Mail,
  Phone,
  ShieldCheck,
  Smartphone,
  Sparkles,
  UserCheck,
  Wand2,
  X,
} from 'lucide-react';
import { trilunairApi } from '../../api/client';
import type { Language } from '../../types/trilunair';

export type MonogramVariant = 'TMJ' | 'MTR' | 'DMT';

/**
 * الشعار الهندسي ثلاثي الأحرف المطابق لبطاقة الهوية المعتمدة:
 * الخيار الافتراضي الموصى به: A • TMJ (TrilMajed — تريلماجد) داخل إطار سداسي ذهبي مزدوج مع قمة التاج الصاعدة.
 */
export const TrmMonogramCrest: React.FC<{ size?: number; variant?: MonogramVariant }> = ({
  size = 54,
  variant = 'TMJ',
}) => (
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
    title={
      variant === 'TMJ'
        ? 'TMJ — TrilMajed (تريلماجد • د. ماجد)'
        : variant === 'MTR'
        ? 'MTR — MajTrillion (ماج تريليون)'
        : 'DMT — Dr. Majed Trillionaire (د. ماجد التريليونير)'
    }
  >
    <svg
      width={size}
      height={size}
      viewBox="0 0 68 68"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label={`شعار ${variant}`}
      style={{ filter: 'drop-shadow(0 0 12px rgba(var(--accent-primary-rgb), 0.42))' }}
    >
      <defs>
        <linearGradient id="tmjNavyGrad" x1="8" y1="4" x2="60" y2="64" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0d1528" />
          <stop offset="100%" stopColor="#050811" />
        </linearGradient>
        <linearGradient id="tmjGoldGrad" x1="8" y1="6" x2="60" y2="62" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#ffe48f" />
          <stop offset="50%" stopColor="var(--accent-primary)" />
          <stop offset="100%" stopColor="#c5962d" />
        </linearGradient>
      </defs>

      {variant === 'TMJ' && (
        <>
          {/* السداسي الذهبي المزدوج — الخيار A الموصى به (TMJ • TRILMAJED) */}
          <polygon
            points="34,3 61,18.5 61,49.5 34,65 7,49.5 7,18.5"
            fill="url(#tmjNavyGrad)"
            stroke="url(#tmjGoldGrad)"
            strokeWidth="2.4"
          />
          <polygon
            points="34,7.5 57,20.8 57,47.2 34,60.5 11,47.2 11,20.8"
            fill="none"
            stroke="url(#tmjGoldGrad)"
            strokeWidth="0.95"
            opacity="0.72"
          />
          {/* قمة المسار المزدوجة أعلى الشعار */}
          <polyline
            points="25,19 29.5,14.5 34,18 38.5,14.5 43,19"
            fill="none"
            stroke="url(#tmjGoldGrad)"
            strokeWidth="1.9"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <text
            x="34"
            y="40"
            textAnchor="middle"
            fill="url(#tmjGoldGrad)"
            style={{
              fontFamily: "Georgia, 'Times New Roman', 'Cairo', serif",
              fontWeight: 800,
              fontSize: '19px',
              letterSpacing: '0.8px',
            }}
          >
            TMJ
          </text>
          <text
            x="34"
            y="50.5"
            textAnchor="middle"
            fill="url(#tmjGoldGrad)"
            opacity="0.88"
            style={{
              fontFamily: "'Cairo', sans-serif",
              fontWeight: 700,
              fontSize: '5.5px',
              letterSpacing: '1.3px',
            }}
          >
            TRILMAJED
          </text>
        </>
      )}

      {variant === 'MTR' && (
        <>
          <circle cx="34" cy="34" r="30" fill="url(#tmjNavyGrad)" stroke="url(#tmjGoldGrad)" strokeWidth="2.3" />
          <circle cx="34" cy="34" r="26.5" fill="none" stroke="url(#tmjGoldGrad)" strokeWidth="0.9" strokeDasharray="1.5 2.5" />
          <polyline points="30,17 34,12.5 38,17" fill="none" stroke="url(#tmjGoldGrad)" strokeWidth="1.9" strokeLinecap="round" />
          <text
            x="34"
            y="39"
            textAnchor="middle"
            fill="url(#tmjGoldGrad)"
            style={{ fontFamily: "Georgia, 'Cairo', serif", fontWeight: 800, fontSize: '18px', letterSpacing: '0.8px' }}
          >
            MTR
          </text>
          <text x="34" y="51" textAnchor="middle" fill="url(#tmjGoldGrad)" style={{ fontSize: '5.3px', letterSpacing: '1.1px' }}>
            MAJ TRILLION
          </text>
        </>
      )}

      {variant === 'DMT' && (
        <>
          <path
            d="M34 4 L59 13 V33 C59 48.5 48.2 59.2 34 64 C19.8 59.2 9 48.5 9 33 V13 L34 4 Z"
            fill="url(#tmjNavyGrad)"
            stroke="url(#tmjGoldGrad)"
            strokeWidth="2.3"
          />
          <polyline points="21,23 28,18 33,20.5 42,13 47,15" fill="none" stroke="url(#tmjGoldGrad)" strokeWidth="1.8" strokeLinecap="round" />
          <text
            x="34"
            y="40.5"
            textAnchor="middle"
            fill="url(#tmjGoldGrad)"
            style={{ fontFamily: "Georgia, 'Cairo', serif", fontWeight: 900, fontSize: '17.5px', letterSpacing: '0.6px' }}
          >
            DMT
          </text>
          <text x="34" y="50.5" textAnchor="middle" fill="url(#tmjGoldGrad)" style={{ fontSize: '4.7px', letterSpacing: '0.9px' }}>
            DR. MAJED
          </text>
        </>
      )}
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
  const [monogram, setMonogram] = useState<MonogramVariant>('TMJ');

  const [displayName, setDisplayName] = useState<string>(identity?.displayName || 'د. ماجد');
  const [email, setEmail] = useState<string>('');
  const [phone, setPhone] = useState<string>('+9665');
  const [verificationKey, setVerificationKey] = useState<string>('');
  const [showKey, setShowKey] = useState<boolean>(false);
  const [currentVerificationKey, setCurrentVerificationKey] = useState<string>('');
  const [totpCode, setTotpCode] = useState<string>('');

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

  const generateStrongPassword = () => {
    const rand = Math.floor(100 + Math.random() * 900);
    const generated = `Majed#${rand}!`;
    setVerificationKey(generated);
    setShowKey(true);
    setSuccessMsg(
      isAr
        ? `تم توليد كلمة سر ثابتة جاهزة للأدمن (${generated}) — احتفظ بها، وهي تختلف عن رمز الـ 6 أرقام المتغير الخاص بتطبيق المصادقة.`
        : `Generated admin password: ${generated}`
    );
  };

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
          ? 'الخطوة 1 اكتملت! الآن أضف مفتاح Base32 أدناه في تطبيق المصادقة على جوالك (Google / Apple Authenticator) ثم أدخل الرمز المكون من 6 أرقام في الخانة بالأسفل.'
          : 'Step 1 complete! Add the Base32 key to your Authenticator app and enter the 6-digit code below.'
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
      const loginRes = await trilunairApi
        .loginAdminMfa({
          email,
          phone,
          verificationKey,
          totpCode,
        })
        .catch(() => null);

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
          ? 'تم تفعيل تطبيق المصادقة الثنائية وتوثيق حساب الأدمن (د. ماجد — TMJ تريلماجد) بنجاح!'
          : 'TMJ Sovereign Admin MFA enrolled & verified!'
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
          ? `مرحباً ${res.displayName} — تم التحقق من العوامل الأربعة (البريد + الجوال + كلمة سر الأدمن + Authenticator) بنجاح.`
          : `Welcome ${res.displayName} — 4-Factor TMJ Admin session active.`
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
      aria-labelledby="tmj-admin-gate-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1200,
        background: 'rgba(4, 6, 12, 0.85)',
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
          maxWidth: '650px',
          maxHeight: '92vh',
          overflowY: 'auto',
          padding: '1.35rem 1.5rem',
          border: '1px solid var(--accent-primary)',
          boxShadow: 'var(--shadow-glow-strong)',
        }}
      >
        {/* رأس البوابة مع خيارات الشعار الثلاثية TMJ / MTR / DMT */}
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
            <TrmMonogramCrest size={58} variant={monogram} />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className={`holo-btn ${monogram === 'TMJ' ? 'holo-btn-primary' : ''}`}
                  style={{ padding: '0.15rem 0.5rem', fontSize: '0.72rem', minHeight: 'auto' }}
                  onClick={() => setMonogram('TMJ')}
                >
                  A • TMJ (الموصى به)
                </button>
                <button
                  type="button"
                  className={`holo-btn ${monogram === 'MTR' ? 'holo-btn-primary' : ''}`}
                  style={{ padding: '0.15rem 0.5rem', fontSize: '0.72rem', minHeight: 'auto' }}
                  onClick={() => setMonogram('MTR')}
                >
                  B • MTR
                </button>
                <button
                  type="button"
                  className={`holo-btn ${monogram === 'DMT' ? 'holo-btn-primary' : ''}`}
                  style={{ padding: '0.15rem 0.5rem', fontSize: '0.72rem', minHeight: 'auto' }}
                  onClick={() => setMonogram('DMT')}
                >
                  C • DMT
                </button>
              </div>
              <h2
                id="tmj-admin-gate-title"
                style={{ margin: '0.3rem 0 0', fontSize: '1.15rem', fontWeight: 800 }}
              >
                {isAr
                  ? 'بوابة دخول وتأسيس أدمن المنصة — تريلماجد (د. ماجد)'
                  : 'TMJ Sovereign Platform Admin MFA Gate'}
              </h2>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {isAr
                  ? 'توضيح هام: «كلمة سر الأدمن الثابتة» تختارها أنت (6 خانات فأكثر)، أما «رمز Authenticator» فهو الـ 6 أرقام المتغيرة كل 30 ثانية.'
                  : 'Static Admin Password (6+ chars) + 6-digit rotating Authenticator TOTP code.'}
              </div>
            </div>
          </div>

          <button
            type="button"
            className="holo-btn"
            onClick={onClose}
            aria-label={isAr ? 'إغلاق' : 'Close'}
            style={{ padding: '0.4rem' }}
          >
            <X size={18} />
          </button>
        </div>

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
            <span className={`holo-badge ${identity.authenticated ? 'holo-badge-success' : 'holo-badge-warning'}`}>
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
            {isAr ? 'تسجيل دخول الأدمن' : 'Admin Sign-In'}
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
            {isAr ? 'تأسيس / تحديث حساب الأدمن' : 'Setup / Update Admin'}
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
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <KeyRound size={14} style={{ color: 'var(--accent-primary)' }} />
                  {isAr ? 'كلمة المرور الثابتة للأدمن (التي اخترتها عند التأسيس — 6 خانات فأكثر)' : 'Static Admin Password (6+ chars)'}
                </span>
                <button
                  type="button"
                  className="holo-btn"
                  style={{ padding: '0.15rem 0.5rem', fontSize: '0.72rem', minHeight: 'auto' }}
                  onClick={() => setShowKey((p) => !p)}
                >
                  {showKey ? <EyeOff size={13} /> : <Eye size={13} />}
                  {showKey ? (isAr ? 'إخفاء' : 'Hide') : isAr ? 'إظهار' : 'Show'}
                </button>
              </span>
              <input
                id="admin-login-vkey"
                type={showKey ? 'text' : 'password'}
                required
                minLength={6}
                dir="ltr"
                className="holo-input"
                placeholder="مثال: Majed#926!"
                value={verificationKey}
                onChange={(e) => setVerificationKey(e.target.value)}
              />
            </label>

            <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Smartphone size={14} style={{ color: 'var(--accent-primary)' }} />
                  {isAr
                    ? 'رمز تطبيق المصادقة المتغير (Authenticator — 6 أرقام)'
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
                  ? 'تسجيل دخول أدمن المنصة (TMJ)'
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
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.35rem' }}>
                  <span>
                    {isAr
                      ? 'كلمة سر الأدمن الثابتة الخاصة بك (6 خانات فأكثر — وليست رمز الـ 6 أرقام المتغير)'
                      : 'Your Static Admin Password (min 6 chars)'}
                  </span>
                  <span style={{ display: 'flex', gap: '0.35rem' }}>
                    <button
                      type="button"
                      className="holo-btn"
                      style={{ padding: '0.15rem 0.5rem', fontSize: '0.72rem', minHeight: 'auto' }}
                      onClick={generateStrongPassword}
                    >
                      <Wand2 size={12} />
                      {isAr ? 'توليد كلمة سر جاهزة' : 'Generate'}
                    </button>
                    <button
                      type="button"
                      className="holo-btn"
                      style={{ padding: '0.15rem 0.5rem', fontSize: '0.72rem', minHeight: 'auto' }}
                      onClick={() => setShowKey((p) => !p)}
                    >
                      {showKey ? <EyeOff size={12} /> : <Eye size={12} />}
                      {showKey ? (isAr ? 'إخفاء' : 'Hide') : isAr ? 'إظهار' : 'Show'}
                    </button>
                  </span>
                </span>
                <input
                  id="admin-enroll-vkey"
                  type={showKey ? 'text' : 'password'}
                  required
                  minLength={6}
                  dir="ltr"
                  className="holo-input"
                  placeholder="اختر كلمة سر ثابتة (6 خانات فأكثر مثل Majed#926)"
                  value={verificationKey}
                  onChange={(e) => setVerificationKey(e.target.value)}
                />
              </label>

              {identity?.enrolled && !identity?.authenticated && (
                <label style={{ display: 'grid', gap: '0.3rem', fontSize: '0.82rem' }}>
                  <span>
                    {isAr
                      ? 'كلمة سر الأدمن الحالية (لتأكيد ملكية الحساب قبل التحديث)'
                      : 'Current Admin Password'}
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
                  ? '1. حفظ بيانات الأدمن وإظهار مفتاح تطبيق المصادقة'
                  : '1. Save Admin Profile & Generate Authenticator Secret'}
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
                    ? '2. إقران تطبيق المصادقة وإدخال رمز الـ 6 أرقام المتغير'
                    : '2. Pair Your Authenticator App & Enter 6-Digit Code'}
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
                    placeholder="أدخل الـ 6 أرقام هنا"
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
