/**
 * شاشة المراقبة الفعلية لحساب Binance الشخصي للمالك (LIVE ACCOUNT MONITORING — READ-ONLY)
 * مفصولة معمارياً وبصرياً بالكامل عن محفظة المحاكاة الورقية ($1,000,000 PAPER TRADING).
 *
 * الضمانات الأمنية المطبقة في الواجهة:
 * 1. لا يتم تخزين أي مفتاح API أو سر في localStorage أو sessionStorage أو ذاكرة المتصفح الدائمة.
 * 2. تُمسح حقول الإدخال الكتابية فوراً بعد الإرسال للخزنة المشفرة (AES-256-GCM)، ولا يُعرض سوى المفتاح المقنّع.
 * 3. يوصى بتوليد زوج مفاتيح Ed25519 داخل الخادم الخلفي بحيث لا يظهر في الواجهة سوى المفتاح العام (PUBLIC KEY PEM).
 * 4. تتطلب تغييرات المفاتيح وحدود التداول المستقبلي تصعيد التحقق البيومتري عبر Face ID / Touch ID (WebAuthn Passkey).
 * 5. يظل وضع التنفيذ مقفلاً دائماً على PAPER (liveAuthorized = false) دون إرسال أي أوامر تداول حقيقية.
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  Fingerprint,
  KeyRound,
  Lock,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Wallet,
} from 'lucide-react';
import { getActiveStepUpToken, trilunairApi } from '../../api/client';
import { formatCurrency, formatNumber, formatSignedPct } from '../../i18n/translations';
import { useTheme } from '../../theme/ThemeContext';
import type { LiveSpotReadiness, PersonalBinanceOverview } from '../../types/trilunair';

type HistoryTab = 'balances' | 'orders' | 'trades' | 'cashflows';

export const BinanceLiveAccountView: React.FC = () => {
  const { language } = useTheme();
  const isAr = language === 'ar';

  const [overview, setOverview] = useState<PersonalBinanceOverview | null>(null);
  const [readiness, setReadiness] = useState<LiveSpotReadiness | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<HistoryTab>('balances');
  const [feedback, setFeedback] = useState<{ kind: 'info' | 'error'; text: string } | null>(null);

  // حالة معالج الربط الآمن (Write-Only — لا تُحفظ في المتصفح مطلقاً)
  const [selectedPurpose, setSelectedPurpose] = useState<'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION'>(
    'READ_ONLY_MONITORING'
  );
  const [authAlgorithm, setAuthAlgorithm] = useState<'ED25519' | 'RSA_SHA256' | 'HMAC_SHA256'>('ED25519');
  const [environment, setEnvironment] = useState<'MAINNET' | 'SPOT_TESTNET'>('MAINNET');
  const [keyLabel, setKeyLabel] = useState<string>('Owner Personal Read-Only Key');
  const [generatedKeypair, setGeneratedKeypair] = useState<{
    keypairId: string;
    publicKeyPem: string;
    instructionsEn: string;
    instructionsAr: string;
  } | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [secretOrPemInput, setSecretOrPemInput] = useState<string>('');
  const [trustedIpsInput, setTrustedIpsInput] = useState<string>('');
  const [adminSecretInput, setAdminSecretInput] = useState<string>('');
  const [stepUpVerified, setStepUpVerified] = useState<boolean>(Boolean(getActiveStepUpToken()));

  // حدود المالك المستقبلية لـ LIVE_SPOT (مع بقاء التنفيذ مقفلاً على PAPER)
  const [maxSingleOrderSar, setMaxSingleOrderSar] = useState<number>(750);
  const [maxMonthlySpotSar, setMaxMonthlySpotSar] = useState<number>(2125);
  const [jurisdictionConfirmed, setJurisdictionConfirmed] = useState<boolean>(true);

  const loadAll = useCallback(async () => {
    setIsLoading(true);
    try {
      const [ov, rd] = await Promise.all([
        trilunairApi.getPersonalBinanceOverview(),
        trilunairApi.getLiveSpotReadiness(),
      ]);
      setOverview(ov);
      setReadiness(rd);
      if (rd?.ownerPolicy) {
        setMaxSingleOrderSar(rd.ownerPolicy.maxSingleOrderSar);
        setMaxMonthlySpotSar(rd.ownerPolicy.maxMonthlySpotSar);
        setJurisdictionConfirmed(rd.ownerPolicy.jurisdictionEligibilityConfirmed);
      }
      setStepUpVerified(Boolean(getActiveStepUpToken()));
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Failed to load Personal Binance overview',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const handleBiometricStepUp = async () => {
    try {
      await trilunairApi.authenticateWithPasskey();
      setStepUpVerified(true);
      await loadAll();
      setFeedback({
        kind: 'info',
        text: isAr
          ? 'تم التحقق البيومتري بنجاح عبر Face ID / Touch ID (WebAuthn Passkey).'
          : 'Biometric Face ID / Touch ID Passkey step-up verified.',
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Biometric Passkey verification failed.',
      });
    }
  };

  const handleGenerateEd25519 = async () => {
    try {
      const kp = await trilunairApi.generateServerEd25519Keypair(
        selectedPurpose,
        adminSecretInput || undefined
      );
      setGeneratedKeypair({
        keypairId: kp.keypairId,
        publicKeyPem: kp.publicKeyPem,
        instructionsEn: kp.binanceRegistrationInstructionsEn,
        instructionsAr: kp.binanceRegistrationInstructionsAr,
      });
      setAuthAlgorithm('ED25519');
      setFeedback({
        kind: 'info',
        text: isAr
          ? 'تم توليد زوج مفاتيح Ed25519 داخل خزنة الخادم؛ انسخ المفتاح العام أدناه إلى Binance API Management.'
          : 'Generated Ed25519 keypair inside server vault; copy ONLY the Public Key PEM below into Binance API Management.',
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Failed to generate Ed25519 keypair.',
      });
    }
  };

  const handleSaveCredential = async () => {
    if (!apiKeyInput.trim()) {
      setFeedback({
        kind: 'error',
        text: isAr ? 'يرجى إدخال مفتاح API الرسمي من Binance.' : 'Please enter your official Binance API Key.',
      });
      return;
    }
    try {
      const ips = trustedIpsInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      const res = await trilunairApi.savePersonalBinanceCredential({
        purpose: selectedPurpose,
        keyLabel,
        authAlgorithm,
        environment,
        apiKey: apiKeyInput.trim(),
        generatedKeypairId: authAlgorithm === 'ED25519' && generatedKeypair ? generatedKeypair.keypairId : undefined,
        privateKeyPem:
          authAlgorithm !== 'HMAC_SHA256' && !generatedKeypair ? secretOrPemInput.trim() : undefined,
        apiSecret: authAlgorithm === 'HMAC_SHA256' ? secretOrPemInput.trim() : undefined,
        trustedIps: ips,
        verifyImmediately: false,
        adminSecret: adminSecretInput || undefined,
      });
      // مسح فوري لكافة المدخلات السرية من ذاكرة المكون
      setApiKeyInput('');
      setSecretOrPemInput('');
      setAdminSecretInput('');
      await loadAll();
      setFeedback({
        kind: 'info',
        text: isAr
          ? `تم تشفير وحفظ المفتاح (${res.apiKeyMasked}) بنجاح في الخزنة الخلفية — وضع التنفيذ مقفل على PAPER.`
          : `Encrypted & vaulted key (${res.apiKeyMasked}) — execution remains locked to PAPER.`,
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Credential save rejected.',
      });
    }
  };

  const handleVerifyPermissions = async () => {
    try {
      const res = await trilunairApi.verifyPersonalBinancePermissions(
        selectedPurpose,
        adminSecretInput || undefined
      );
      await loadAll();
      setFeedback({
        kind: 'info',
        text: isAr
          ? `نجح فحص الصلاحيات المغلق بأمان: ${res.connectionStatus}`
          : `Fail-closed permission audit passed: ${res.connectionStatus}`,
      });
    } catch (err) {
      await loadAll();
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Permission verification failed.',
      });
    }
  };

  const handleSyncPortfolio = async () => {
    setIsSyncing(true);
    try {
      const synced = await trilunairApi.syncPersonalBinanceAccount(
        'READ_ONLY_MONITORING',
        adminSecretInput || undefined
      );
      setOverview(synced);
      const rd = await trilunairApi.getLiveSpotReadiness();
      setReadiness(rd);
      setFeedback({
        kind: 'info',
        text: isAr
          ? 'اكتملت مزامنة القراءة فقط للأرصدة والأوامر والصفقات والتدفقات الرأسمالية.'
          : 'Completed Read-Only sync of Spot balances, orders, trades, and capital flows.',
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Read-Only sync failed.',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRevokeSlot = async (purpose: 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION') => {
    try {
      await trilunairApi.revokePersonalBinanceCredential(purpose, adminSecretInput || undefined);
      await loadAll();
      setFeedback({
        kind: 'info',
        text: isAr
          ? `تم إبطال ومسح النص المشفر للفتحة (${purpose}) فوراً.`
          : `Revoked & wiped encrypted credential for ${purpose}.`,
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Revocation failed.',
      });
    }
  };

  const handleSaveSpotLimits = async () => {
    try {
      const updated = await trilunairApi.updateOwnerSpotLimits({
        jurisdictionEligibilityConfirmed: jurisdictionConfirmed,
        jurisdictionCountryCode: 'SA',
        maxSingleOrderSar,
        maxDailySpotSar: Math.max(maxSingleOrderSar, Math.min(maxMonthlySpotSar, 1500)),
        maxMonthlySpotSar,
        maxSingleAssetExposurePct: 45,
        requireBiometricPerOrder: true,
        allowedSpotSymbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
        adminSecret: adminSecretInput || undefined,
      });
      setReadiness(updated);
      setFeedback({
        kind: 'info',
        text: isAr
          ? 'تم حفظ سقوف المخاطر المستقبلية للمالك — يظل الإرسال الحقيقي للأوامر مقفلاً على PAPER.'
          : 'Saved owner LIVE_SPOT monetary caps — real order submission remains locked to PAPER.',
      });
    } catch (err) {
      setFeedback({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Failed to save owner Spot limits.',
      });
    }
  };

  const connStatus = overview?.connectionStatus ?? 'PENDING_OWNER_SETUP';
  const summary = overview?.portfolioSummary;
  const budget = overview?.monthlyInvestmentBudgetTracking;
  const roSlot = overview?.credentialSlots.READ_ONLY_MONITORING;

  return (
    <div
      data-testid="binance-live-monitoring-view"
      style={{ display: 'flex', flexDirection: 'column', gap: '1rem', paddingBottom: '5rem' }}
    >
      {/* 1. شريط التمييز الصارم بين المراقبة الفعلية لحساب المالك ومحاكاة المليون دولار الورقية */}
      <section
        className="holo-panel"
        style={{
          padding: '1rem 1.2rem',
          borderLeft: '4px solid var(--accent-primary)',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '0.8rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
            <Wallet size={20} style={{ color: 'var(--accent-primary)' }} />
            <h1 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800 }}>
              {isAr
                ? 'مراقبة حساب Binance الشخصي الحقيقي (LIVE ACCOUNT MONITORING — READ-ONLY)'
                : 'LIVE ACCOUNT MONITORING — Personal Binance Spot (Read-Only)'}
            </h1>
            <span
              data-testid="binance-personal-status-badge"
              className={`holo-badge ${
                connStatus === 'VERIFIED_READ_ONLY'
                  ? 'holo-badge-success'
                  : connStatus === 'BLOCKED_UNSAFE_PERMISSIONS'
                    ? 'holo-badge-danger'
                    : 'holo-badge-warning'
              }`}
            >
              {connStatus === 'PENDING_OWNER_SETUP' ? 'PENDING OWNER SETUP' : connStatus}
            </span>
          </div>
          <p style={{ margin: '0.35rem 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {isAr
              ? 'هذه الشاشة مخصصة حصراً لأرصدة وسجلات حسابك الفوري الحقيقي في Binance (مخصص شهري 2,125 ريال)، وهي معزولة كلياً عن رصيد المحاكاة الورقية ($1,000,000 PAPER TRADING). لا يُرسل النظام أي أوامر حقيقية.'
              : 'Dedicated strictly to your real personal Binance Spot balances & history (planned SAR 2,125/mo allocation) — 100% segregated from the $1,000,000 PAPER TRADING simulator. Zero real orders are submitted.'}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span className="holo-badge holo-badge-success" data-testid="paper-execution-lock-badge">
            <Lock size={13} />
            {isAr ? 'التنفيذ مقفل على PAPER' : 'EXECUTION LOCKED TO PAPER'}
          </span>
          <button
            type="button"
            className="holo-btn holo-btn-primary"
            onClick={() => void handleSyncPortfolio()}
            disabled={isSyncing || isLoading}
          >
            <RefreshCw size={14} />
            {isSyncing
              ? isAr
                ? 'جارٍ المزامنة...'
                : 'Syncing...'
              : isAr
                ? 'مزامنة القراءة فقط'
                : 'Sync Read-Only'}
          </button>
        </div>
      </section>

      {feedback && (
        <div
          role="alert"
          className="holo-panel"
          style={{
            padding: '0.75rem 1rem',
            borderColor: feedback.kind === 'error' ? 'var(--status-danger)' : 'var(--status-success)',
            color: feedback.kind === 'error' ? 'var(--status-danger)' : 'var(--text-primary)',
            fontSize: '0.85rem',
          }}
        >
          {feedback.text}
        </div>
      )}

      {/* 2. المؤشرات المالية الفعلية لحساب المالك + تتبع ميزانية 2,125 ريال */}
      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(215px, 1fr))',
          gap: '0.8rem',
        }}
      >
        <div className="holo-panel" style={{ padding: '0.85rem 1rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {isAr ? 'إجمالي محفظة Binance الفعلية' : 'Actual Binance Spot Value'}
          </div>
          <div className="fin-value" style={{ fontSize: '1.2rem', fontWeight: 800 }}>
            SAR {formatNumber(summary?.totalEquitySar ?? 0, 2)}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
            {formatCurrency(summary?.totalEquityUsd ?? 0)} USDT/USD
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.85rem 1rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {isAr ? 'النقد المتاح مقابل التعرض للعملات' : 'Available Quote Cash vs Crypto'}
          </div>
          <div className="fin-value" style={{ fontSize: '1.05rem', fontWeight: 700 }}>
            {formatCurrency(summary?.availableQuoteCashUsd ?? 0)} /{' '}
            {formatCurrency(summary?.investedCryptoCapitalUsd ?? 0)}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--accent-primary)' }}>
            {isAr ? 'نسبة التعرض للسوق:' : 'Market Exposure:'}{' '}
            {(summary?.cryptoExposurePct ?? 0).toFixed(1)}%
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.85rem 1rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {isAr ? 'صافي الربح/الخسارة بعد الرسوم' : 'Net P&L (After Spot Fees)'}
          </div>
          <div
            className="fin-value"
            style={{
              fontSize: '1.1rem',
              fontWeight: 800,
              color:
                (summary?.netPnlAfterFeesSar ?? 0) >= 0
                  ? 'var(--status-success)'
                  : 'var(--status-danger)',
            }}
          >
            SAR {formatNumber(summary?.netPnlAfterFeesSar ?? 0, 2)}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {isAr ? 'رأس المال المودع:' : 'Contributed:'} SAR{' '}
            {formatNumber(summary?.netContributedCapitalSar ?? 0, 2)} •{' '}
            {isAr ? 'الرسوم:' : 'Fees:'} ${formatNumber(summary?.cumulativeFeesUsd ?? 0, 2)}
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.85rem 1rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {isAr ? 'مخصص الاستثمار الشهري (2,125 ريال)' : 'Monthly Crypto Budget (SAR 2,125)'}
          </div>
          <div className="fin-value" style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
            SAR {formatNumber(budget?.plannedMonthlyAllocationSar ?? 2125, 2)}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {isAr ? 'المشتريات هذا الشهر:' : 'Used this month:'} SAR{' '}
            {formatNumber(budget?.currentMonthSpotPurchasesSar ?? 0, 2)} •{' '}
            {isAr ? 'المتبقي:' : 'Remaining:'} SAR{' '}
            {formatNumber(budget?.remainingMonthlyBudgetSar ?? 2125, 2)}
          </div>
        </div>
      </section>

      {/* 3. التمييز البيومتري الصريح (Face ID / Touch ID WebAuthn) + معالج الربط المشفر للمالك فقط */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '1rem',
        }}
      >
        <section className="holo-panel" style={{ padding: '1rem 1.15rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <h2 style={{ margin: 0, fontSize: '0.98rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <KeyRound size={17} style={{ color: 'var(--accent-primary)' }} />
              {isAr
                ? 'معالج الربط المشفر للمالك (Ed25519 / AES-256-GCM Vault)'
                : 'Owner-Only Encrypted Binance Connection Wizard'}
            </h2>
            <button
              type="button"
              className={`holo-btn ${stepUpVerified ? 'holo-btn-primary' : ''}`}
              onClick={() => void handleBiometricStepUp()}
            >
              <Fingerprint size={14} />
              {stepUpVerified
                ? isAr
                  ? 'Face ID / Touch ID موثق'
                  : 'Biometric Verified'
                : isAr
                  ? 'تصعيد Face ID / Touch ID'
                  : 'Face ID / Touch ID Step-Up'}
            </button>
          </div>

          <div
            style={{
              marginTop: '0.65rem',
              padding: '0.6rem 0.75rem',
              borderRadius: '8px',
              background: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              fontSize: '0.77rem',
              lineHeight: 1.5,
            }}
          >
            <strong>
              {isAr ? 'قاعدة أمان صارمة:' : 'Strict Credential & Biometric Hygiene:'}
            </strong>{' '}
            {isAr
              ? 'لا تدخل أبداً كلمة مرور حساب Binance أو عبارة الاسترداد (Seed Phrase) أو رموز OTP، ولا تلصق أي مفتاح سري في محادثة الذكاء الاصطناعي. بصمة الوجه داخل تطبيق Binance تخص التطبيق وحده؛ أما TRILUNAIR فيتحقق من هويتك عبر مفاتيح مرور النظام (Face ID على iPhone وTouch ID على Mac) دون تخزين أي بيانات حيوية.'
              : 'Never enter your Binance login password, recovery/seed phrase, or OTP, and NEVER paste API secrets into any AI chat. Binance mobile Face ID authenticates locally inside the Binance app; TRILUNAIR uses OS WebAuthn Passkeys (iPhone Face ID / Mac Touch ID) with zero biometric template storage.'}
          </div>

          {roSlot?.configured && (
            <div
              style={{
                marginTop: '0.65rem',
                padding: '0.55rem 0.75rem',
                borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.5rem',
                fontSize: '0.78rem',
              }}
            >
              <span>
                <strong>{roSlot.keyLabel}:</strong> <code>{roSlot.apiKeyMasked}</code> ({roSlot.authAlgorithm} •{' '}
                {roSlot.status})
              </span>
              <div style={{ display: 'flex', gap: '0.4rem' }}>
                <button
                  type="button"
                  className="holo-btn"
                  style={{ minHeight: '30px', fontSize: '0.75rem' }}
                  onClick={() => void handleVerifyPermissions()}
                >
                  <ShieldCheck size={13} />
                  {isAr ? 'فحص الصلاحيات' : 'Verify Scope'}
                </button>
                <button
                  type="button"
                  className="holo-btn"
                  style={{ minHeight: '30px', fontSize: '0.75rem', color: 'var(--status-danger)' }}
                  onClick={() => void handleRevokeSlot('READ_ONLY_MONITORING')}
                >
                  <Trash2 size={13} />
                  {isAr ? 'إبطال فوري' : 'Revoke'}
                </button>
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.55rem', marginTop: '0.75rem' }}>
            <label style={{ fontSize: '0.76rem' }}>
              {isAr ? 'فتحة المفتاح المعزولة' : 'Credential Slot'}
              <select
                className="holo-select"
                value={selectedPurpose}
                onChange={(e) =>
                  setSelectedPurpose(e.target.value as 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION')
                }
              >
                <option value="READ_ONLY_MONITORING">READ_ONLY_MONITORING (Recommended)</option>
                <option value="FUTURE_SPOT_EXECUTION">FUTURE_SPOT_EXECUTION (Locked to PAPER)</option>
              </select>
            </label>

            <label style={{ fontSize: '0.76rem' }}>
              {isAr ? 'آلية التوقيع الرسمية' : 'Official Signature Mechanism'}
              <select
                className="holo-select"
                value={authAlgorithm}
                onChange={(e) => setAuthAlgorithm(e.target.value as 'ED25519' | 'RSA_SHA256' | 'HMAC_SHA256')}
              >
                <option value="ED25519">Ed25519 Asymmetric (Recommended #1)</option>
                <option value="RSA_SHA256">RSA-SHA256 Asymmetric</option>
                <option value="HMAC_SHA256">HMAC-SHA256 Symmetric</option>
              </select>
            </label>
          </div>

          {authAlgorithm === 'ED25519' && (
            <div style={{ marginTop: '0.65rem' }}>
              <button
                type="button"
                className="holo-btn"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => void handleGenerateEd25519()}
              >
                <RotateCcw size={14} />
                {isAr
                  ? '١. توليد زوج مفاتيح Ed25519 داخل خزنة الخادم (يبقى المفتاح الخاص بالخادم فقط)'
                  : '1. Generate Ed25519 Keypair in Server Vault (Private Key Never Leaves Server)'}
              </button>

              {generatedKeypair && (
                <div style={{ marginTop: '0.55rem', fontSize: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>
                      {isAr ? 'المفتاح العام فقط (انسخه إلى Binance):' : 'Public Key PEM Only (Copy to Binance):'}
                    </span>
                    <button
                      type="button"
                      className="holo-btn"
                      style={{ minHeight: '26px', padding: '0.15rem 0.5rem', fontSize: '0.72rem' }}
                      onClick={() => void navigator.clipboard?.writeText(generatedKeypair.publicKeyPem)}
                    >
                      <Copy size={12} /> Copy Public Key
                    </button>
                  </div>
                  <pre
                    style={{
                      margin: '0.35rem 0',
                      padding: '0.5rem',
                      borderRadius: '6px',
                      background: 'rgba(0,0,0,0.35)',
                      overflowX: 'auto',
                      fontSize: '0.72rem',
                    }}
                  >
                    {generatedKeypair.publicKeyPem}
                  </pre>
                </div>
              )}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.55rem', marginTop: '0.65rem' }}>
            <label style={{ fontSize: '0.76rem' }}>
              {isAr ? 'البيئة' : 'Binance Environment'}
              <select
                className="holo-select"
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as 'MAINNET' | 'SPOT_TESTNET')}
              >
                <option value="MAINNET">MAINNET (api.binance.com)</option>
                <option value="SPOT_TESTNET">SPOT_TESTNET (testnet.binance.vision)</option>
              </select>
            </label>

            <label style={{ fontSize: '0.76rem' }}>
              {isAr ? 'تسمية المفتاح' : 'Key Label'}
              <input
                type="text"
                className="holo-input"
                value={keyLabel}
                onChange={(e) => setKeyLabel(e.target.value)}
              />
            </label>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.6rem' }}>
            <input
              type="password"
              autoComplete="off"
              className="holo-input"
              placeholder={
                isAr
                  ? 'أدخل Binance API Key الناتج (كتابة فقط — يُقنّع ويُشفّر فوراً)'
                  : 'Paste Binance API Key (Write-only — encrypted immediately in vault)'
              }
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
            />

            {(!generatedKeypair || authAlgorithm !== 'ED25519') && (
              <input
                type="password"
                autoComplete="off"
                className="holo-input"
                placeholder={
                  authAlgorithm === 'HMAC_SHA256'
                    ? 'HMAC API Secret (Write-only — never stored in browser)'
                    : 'PKCS#8 Private Key PEM (Or click Generate Ed25519 above so private key never touches browser)'
                }
                value={secretOrPemInput}
                onChange={(e) => setSecretOrPemInput(e.target.value)}
              />
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <input
                type="text"
                className="holo-input"
                placeholder={isAr ? 'عناوين IP الموثوقة (مثال: 203.0.113.10)' : 'Trusted Server IP Allowlist'}
                value={trustedIpsInput}
                onChange={(e) => setTrustedIpsInput(e.target.value)}
              />
              <input
                type="password"
                autoComplete="off"
                className="holo-input"
                placeholder={isAr ? 'رمز المسؤول (عند عدم وجود Passkey مسجل)' : 'Admin Secret (if no Passkey enrolled yet)'}
                value={adminSecretInput}
                onChange={(e) => setAdminSecretInput(e.target.value)}
              />
            </div>

            <button
              type="button"
              className="holo-btn holo-btn-primary"
              onClick={() => void handleSaveCredential()}
            >
              <Lock size={14} />
              {isAr
                ? 'تشفير وحفظ في الخزنة الخلفية (تظل الأوامر الحقيقية معطلة)'
                : 'Encrypt & Save to Vault (Keeps Real Execution Disabled)'}
            </button>
          </div>
        </section>

        {/* 4. لوحة البوابات الثماني لاعتماد المالك المستقبلي (8-Gate LIVE_SPOT Authorization Architecture) */}
        <section className="holo-panel" style={{ padding: '1rem 1.15rem' }} data-testid="live-spot-eight-gates-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
            <h2 style={{ margin: 0, fontSize: '0.98rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <ShieldAlert size={17} style={{ color: 'var(--status-warning)' }} />
              {isAr
                ? 'بوابات الاعتماد الثماني المستقبلية للتداول الفوري (LIVE_SPOT 8-Gate Lock)'
                : 'Future LIVE_SPOT 8-Gate Owner Approval Architecture'}
            </h2>
            <span className="holo-badge">
              {readiness?.passedGatesCount ?? 0} / {readiness?.totalGatesCount ?? 8} Gates
            </span>
          </div>

          <p style={{ margin: '0.4rem 0 0.65rem', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
            {isAr
              ? 'العقود الآجلة والهامش والرافعة والاقتراض والسحوبات والتحويلات الخارجية محظورة معمارياً بالكامل. البوابة رقم 8 مقفلة في هذا الإصدار لمنع إرسال أي أمر حقيقي.'
              : 'Futures, Margin, Leverage, Borrowing, Withdrawals, External Transfers & Autonomous Escalation are hard-blocked (HTTP 403). Gate #8 is permanently locked to PAPER in this release.'}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.38rem' }}>
            {(readiness?.gates ?? []).map((g) => (
              <div
                key={g.gateId}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '0.5rem',
                  padding: '0.38rem 0.6rem',
                  borderRadius: '6px',
                  background: 'rgba(255,255,255,0.03)',
                  fontSize: '0.76rem',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  {g.passed ? (
                    <CheckCircle2 size={14} style={{ color: 'var(--status-success)', flexShrink: 0 }} />
                  ) : (
                    <AlertTriangle size={14} style={{ color: 'var(--status-warning)', flexShrink: 0 }} />
                  )}
                  <strong>#{g.gateNumber}</strong> {isAr ? g.titleAr : g.titleEn}
                </span>
                <span style={{ fontSize: '0.7rem', color: g.passed ? 'var(--status-success)' : 'var(--text-muted)' }}>
                  {g.passed ? 'PASSED' : 'LOCKED'}
                </span>
              </div>
            ))}
          </div>

          <div
            style={{
              marginTop: '0.75rem',
              paddingTop: '0.65rem',
              borderTop: '1px solid rgba(255,255,255,0.08)',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr auto',
              gap: '0.5rem',
              alignItems: 'end',
            }}
          >
            <label style={{ fontSize: '0.74rem' }}>
              {isAr ? 'سقف الأمر الفردي (ريال)' : 'Max Order Cap (SAR)'}
              <input
                type="number"
                className="holo-input"
                value={maxSingleOrderSar}
                onChange={(e) => setMaxSingleOrderSar(Number(e.target.value))}
              />
            </label>
            <label style={{ fontSize: '0.74rem' }}>
              {isAr ? 'السقف الشهري الفوري (ريال)' : 'Monthly Spot Cap (SAR)'}
              <input
                type="number"
                className="holo-input"
                value={maxMonthlySpotSar}
                onChange={(e) => setMaxMonthlySpotSar(Number(e.target.value))}
              />
            </label>
            <button type="button" className="holo-btn" onClick={() => void handleSaveSpotLimits()}>
              {isAr ? 'حفظ الحدود' : 'Save Caps'}
            </button>
          </div>
        </section>
      </div>

      {/* 5. جداول الأرصدة الفورية الفعلية، أساس التكلفة، الأوامر، الصفقات، والإيداعات/السحوبات */}
      <section className="holo-panel" style={{ padding: '1rem 1.15rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '0.6rem', marginBottom: '0.8rem' }}>
          <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className={`holo-btn ${activeTab === 'balances' ? 'holo-btn-primary' : ''}`}
              onClick={() => setActiveTab('balances')}
            >
              {isAr ? 'الأرصدة الفورية وأساس التكلفة' : 'Spot Balances & Cost Basis'} ({overview?.balances.length ?? 0})
            </button>
            <button
              type="button"
              className={`holo-btn ${activeTab === 'orders' ? 'holo-btn-primary' : ''}`}
              onClick={() => setActiveTab('orders')}
            >
              {isAr ? 'سجل الأوامر' : 'Order History'} ({overview?.recentOrders.length ?? 0})
            </button>
            <button
              type="button"
              className={`holo-btn ${activeTab === 'trades' ? 'holo-btn-primary' : ''}`}
              onClick={() => setActiveTab('trades')}
            >
              {isAr ? 'سجل الصفقات والرسوم' : 'Trades & Fees'} ({overview?.recentTrades.length ?? 0})
            </button>
            <button
              type="button"
              className={`holo-btn ${activeTab === 'cashflows' ? 'holo-btn-primary' : ''}`}
              onClick={() => setActiveTab('cashflows')}
            >
              {isAr ? 'الإيداعات والسحوبات' : 'Deposits & Withdrawals'} ({overview?.recentCashflows.length ?? 0})
            </button>
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {isAr ? 'منهج المحاسبة:' : 'Accounting:'}{' '}
            <code>{summary?.accountingMethod ?? 'WEIGHTED_AVERAGE_COST_BASIS_SPOT_LEDGER'}</code> •{' '}
            {isAr ? 'المطابقة:' : 'Reconciliation:'}{' '}
            <strong>{summary?.reconciliationStatus ?? 'RECONCILED_EXACT'}</strong>
          </div>
        </div>

        {activeTab === 'balances' && (
          <div style={{ overflowX: 'auto' }}>
            {(overview?.balances.length ?? 0) === 0 ? (
              <div style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                {connStatus === 'PENDING_OWNER_SETUP'
                  ? isAr
                    ? 'حالة الحساب: PENDING OWNER SETUP — لم يتم ربط مفتاح القراءة الشخصي بعد؛ لن يتم عرض أي أرصدة وهمية.'
                    : 'Status: PENDING OWNER SETUP — No personal Read-Only Binance API key configured yet; zero simulated balances shown here.'
                  : isAr
                    ? 'لا توجد أرصدة فورية غير صفرية متزامنة حالياً.'
                    : 'No non-zero Spot balances synced yet.'}
              </div>
            ) : (
              <table className="holo-table" style={{ width: '100%', fontSize: '0.8rem' }}>
                <thead>
                  <tr>
                    <th>{isAr ? 'الأصل' : 'Asset'}</th>
                    <th>{isAr ? 'متاح (Free)' : 'Free'}</th>
                    <th>{isAr ? 'محجوز (Locked)' : 'Locked'}</th>
                    <th>{isAr ? 'السعر ($)' : 'Price ($)'}</th>
                    <th>{isAr ? 'القيمة (ريال)' : 'Value (SAR)'}</th>
                    <th>{isAr ? 'الوزن %' : 'Weight %'}</th>
                    <th>{isAr ? 'متوسط التكلفة ($)' : 'Avg Cost ($)'}</th>
                    <th>{isAr ? 'ربح/خسارة غير محققة' : 'Unrealized P&L'}</th>
                    <th>{isAr ? 'ربح/خسارة محققة' : 'Realized P&L'}</th>
                    <th>{isAr ? 'المطابقة' : 'Reconciliation'}</th>
                  </tr>
                </thead>
                <tbody>
                  {overview?.balances.map((b) => (
                    <tr key={b.asset}>
                      <td>
                        <strong>{b.asset}</strong>
                      </td>
                      <td className="fin-value">{formatNumber(b.freeQty, 6)}</td>
                      <td className="fin-value">{formatNumber(b.lockedQty, 6)}</td>
                      <td className="fin-value">${formatNumber(b.priceUsd, 2)}</td>
                      <td className="fin-value">SAR {formatNumber(b.valueSar, 2)}</td>
                      <td className="fin-value">{b.allocationWeightPct.toFixed(1)}%</td>
                      <td className="fin-value">${formatNumber(b.avgCostBasisUsd, 2)}</td>
                      <td
                        className="fin-value"
                        style={{
                          color: b.unrealizedPnlUsd >= 0 ? 'var(--status-success)' : 'var(--status-danger)',
                        }}
                      >
                        ${formatNumber(b.unrealizedPnlUsd, 2)} ({formatSignedPct(b.unrealizedPnlPct)})
                      </td>
                      <td className="fin-value">${formatNumber(b.realizedPnlUsd, 2)}</td>
                      <td>
                        <code>{b.reconciliationStatus}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'orders' && (
          <div style={{ overflowX: 'auto' }}>
            <table className="holo-table" style={{ width: '100%', fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Order ID</th>
                  <th>Side</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Executed Qty</th>
                  <th>Quote Total</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {(overview?.recentOrders ?? []).map((o) => (
                  <tr key={o.orderUid}>
                    <td>{o.symbol}</td>
                    <td>{o.orderId}</td>
                    <td>{o.side}</td>
                    <td>{o.type}</td>
                    <td>{o.status}</td>
                    <td className="fin-value">{o.executedQty}</td>
                    <td className="fin-value">${formatNumber(o.cummulativeQuoteQty, 2)}</td>
                    <td>{o.orderTimeIso}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'trades' && (
          <div style={{ overflowX: 'auto' }}>
            <table className="holo-table" style={{ width: '100%', fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Price</th>
                  <th>Qty</th>
                  <th>Quote Qty</th>
                  <th>Fee</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {(overview?.recentTrades ?? []).map((tr) => (
                  <tr key={tr.tradeUid}>
                    <td>{tr.symbol}</td>
                    <td>{tr.side}</td>
                    <td className="fin-value">${formatNumber(tr.price, 2)}</td>
                    <td className="fin-value">{tr.qty}</td>
                    <td className="fin-value">${formatNumber(tr.quoteQty, 2)}</td>
                    <td className="fin-value">
                      {tr.commission} {tr.commissionAsset} (${formatNumber(tr.commissionUsd, 4)})
                    </td>
                    <td>{tr.tradeTimeIso}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'cashflows' && (
          <div style={{ overflowX: 'auto' }}>
            <table className="holo-table" style={{ width: '100%', fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Direction</th>
                  <th>Coin</th>
                  <th>Amount</th>
                  <th>Value (SAR)</th>
                  <th>Network</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {(overview?.recentCashflows ?? []).map((cf) => (
                  <tr key={cf.cashflowId}>
                    <td>{cf.direction}</td>
                    <td>{cf.coin}</td>
                    <td className="fin-value">{cf.amount}</td>
                    <td className="fin-value">SAR {formatNumber(cf.amountSar, 2)}</td>
                    <td>{cf.network}</td>
                    <td>{cf.statusLabel}</td>
                    <td>{cf.occurredAtIso}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
