/**
 * شاشة المحفظة الاستثمارية ومسار التريليون دولار (Portfolio & $1,000,000,000,000 Roadmap)
 * تعرض شريط المعالم اللوغاريتمي من $1M حتى $1T، إسقاط النمو المركب، مؤشرات المخاطر والسيولة،
 * جدول المراكز المفتوحة، وسجل الصفقات المنفذة عبر الصوت أو النص أو قاعة التداول.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Briefcase,
  CalendarClock,
  CheckCircle2,
  Clock,
  Compass,
  CreditCard,
  FileCheck2,
  Landmark,
  MessageSquare,
  Mic,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import { trilunairApi } from '../../api/client';
import { useTheme } from '../../theme/ThemeContext';
import { formatCurrency, formatNumber, formatSignedPct } from '../../i18n/translations';
import type {
  CommandSource,
  MarketAsset,
  PortfolioSnapshot,
  WealthArchitectOverview,
} from '../../types/trilunair';

export interface PortfolioViewProps {
  portfolio: PortfolioSnapshot | null;
  assets?: MarketAsset[];
  onSelectSymbolForTerminal?: (symbol: string) => void;
}

interface MilestoneStep {
  label: string;
  targetUsd: number;
}

const TRILUNAIR_MILESTONES: MilestoneStep[] = [
  { label: '$1M', targetUsd: 1_000_000 },
  { label: '$10M', targetUsd: 10_000_000 },
  { label: '$100M', targetUsd: 100_000_000 },
  { label: '$1B', targetUsd: 1_000_000_000 },
  { label: '$100B', targetUsd: 100_000_000_000 },
  { label: '$1T', targetUsd: 1_000_000_000_000 },
];

export const PortfolioView: React.FC<PortfolioViewProps> = ({
  portfolio,
  onSelectSymbolForTerminal,
}) => {
  const { language } = useTheme();
  const isAr = language === 'ar';
  const [targetAnnualCagrPct, setTargetAnnualCagrPct] = useState<number>(65);
  const [wealthOverview, setWealthOverview] = useState<WealthArchitectOverview | null>(null);
  const [expiryDraft, setExpiryDraft] = useState<string>('2027-10-10');
  const [evidenceTitle, setEvidenceTitle] = useState<string>('');
  const [cfoFeedback, setCfoFeedback] = useState<string | null>(null);

  const loadWealthOverview = useCallback(async () => {
    try {
      const data = await trilunairApi.getWealthOverview();
      setWealthOverview(data);
      if (data?.contractRenewalIntelligence?.contractExpiryDate) {
        setExpiryDraft(data.contractRenewalIntelligence.contractExpiryDate);
      }
    } catch {
      // Safe non-blocking load in isolated unit tests without mock
    }
  }, []);

  useEffect(() => {
    void loadWealthOverview();
  }, [loadWealthOverview]);

  const handleRecalculateContractExpiry = async () => {
    if (!wealthOverview) return;
    try {
      const cs = wealthOverview.employmentBenefits.contractSummary;
      const updated = await trilunairApi.updateEmploymentContract({
        commencementDate: cs.commencementDate,
        contractExpiryDate: expiryDraft,
        contractType: 'FIXED_TERM',
        autoRenews: cs.autoRenews,
        nonRenewalNoticeDays: cs.nonRenewalNoticeDays,
        eligibleFinalWageSar: cs.eligibleFinalMonthlyWageSar,
        annualLeaveDaysPerYear: cs.annualLeaveDaysPerYear,
        annualLeaveTakenDays: cs.annualLeaveTakenDays,
        exactContractExpiryVerified: cs.exactExpiryDateVerified,
      });
      setWealthOverview(updated);
      setCfoFeedback(
        isAr
          ? `تم تحديث حسابات العقد ومهلة الـ 60 يوماً (${updated.contractRenewalIntelligence.finalNoticeDeadlineDate}).`
          : `Updated contract & 60-day notice deadline (${updated.contractRenewalIntelligence.finalNoticeDeadlineDate}).`
      );
    } catch (err) {
      setCfoFeedback(err instanceof Error ? err.message : 'Update error');
    }
  };

  const handleLogMonthlyInvestment = async () => {
    try {
      const updated = await trilunairApi.recordInvestmentAllocation({
        amountSar: 2125,
        diversifiedWeightPct: 45,
        saudiEquitiesWeightPct: 35,
        cryptoSpotPaperWeightPct: 20,
        notes: 'Scheduled SAR 2,125 monthly allocation (PAPER simulation only)',
      });
      setWealthOverview(updated);
      setCfoFeedback(
        isAr
          ? 'تم تسجيل دفعة 2,125 ريال في دفتر الاستثمار المخصص (محاكاة PAPER فقط).'
          : 'Recorded SAR 2,125 contribution in Investment Capital Ledger (PAPER simulation only).'
      );
    } catch (err) {
      setCfoFeedback(err instanceof Error ? err.message : 'Liquidity guard blocked');
    }
  };

  const handleVaultEvidence = async () => {
    if (!evidenceTitle.trim()) return;
    try {
      await trilunairApi.recordContractEvidence({
        documentType: 'QIWA_CONTRACT_EXTRACT',
        title: evidenceTitle.trim(),
        deliveryChannel: 'QIWA_PLATFORM',
        verifiedByOwner: false,
      });
      setEvidenceTitle('');
      await loadWealthOverview();
      setCfoFeedback(
        isAr
          ? 'تم حفظ مرجع المستند في خزنة الإثباتات دون إرسال أي إشعار خارجي.'
          : 'Vaulted contract evidence hash (zero external notices sent).'
      );
    } catch (err) {
      setCfoFeedback(err instanceof Error ? err.message : 'Vault error');
    }
  };

  const totalEquity = portfolio?.totalEquity ?? 1_000_000;
  const initialEquity = portfolio?.initialEquity ?? 1_000_000;
  const cashBalance = portfolio?.cashBalance ?? 0;
  const dailyPnl = portfolio?.dailyPnl ?? 0;
  const dailyPnlPct = portfolio?.dailyPnlPct ?? 0;
  const var95Usd = portfolio?.var95Usd ?? 0;
  const currentDrawdownPct = portfolio?.currentDrawdownPct ?? 0;
  const maxAllowedDrawdownPct = portfolio?.maxAllowedDrawdownPct ?? 10;
  const trilunairTargetUsd = portfolio?.trilunairTargetUsd ?? 1_000_000_000_000;

  // حساب التقدم اللوغاريتمي من 100 ألف دولار ($10^5) إلى تريليون دولار ($10^12)
  const logProgressPct = useMemo(() => {
    const minLog = 5; // $100,000 baseline
    const maxLog = 12; // $1,000,000,000,000 ($1T)
    const safeEq = Math.max(100_000, totalEquity);
    const currentLog = Math.log10(safeEq);
    const pct = ((currentLog - minLog) / (maxLog - minLog)) * 100;
    return Math.max(1, Math.min(100, pct));
  }, [totalEquity]);

  // حساب عدد السنوات المقدرة للوصول إلى التريليون عند معدل نمو سنوي مركب مختار
  const yearsToTrilunair = useMemo(() => {
    if (totalEquity >= trilunairTargetUsd) return 0;
    const safeEquity = Math.max(1_000, totalEquity);
    const rate = Math.max(0.05, targetAnnualCagrPct / 100);
    return Math.log(trilunairTargetUsd / safeEquity) / Math.log(1 + rate);
  }, [totalEquity, trilunairTargetUsd, targetAnnualCagrPct]);

  const inceptionReturnPct =
    initialEquity > 0 ? ((totalEquity - initialEquity) / initialEquity) * 100 : 0;

  const renderOrderSourceBadge = (source: CommandSource) => {
    if (source === 'VOICE') {
      return (
        <span className="holo-badge holo-badge-accent">
          <Mic size={12} aria-hidden="true" />
          <span>VOICE</span>
        </span>
      );
    }
    if (source === 'TEXT') {
      return (
        <span className="holo-badge holo-badge-accent">
          <MessageSquare size={12} aria-hidden="true" />
          <span>TEXT</span>
        </span>
      );
    }
    return (
      <span className="holo-badge">
        <Terminal size={12} aria-hidden="true" />
        <span>TERMINAL</span>
      </span>
    );
  };

  return (
    <div
      data-testid="portfolio-view"
      style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}
    >
      {/* 1. متتبع رحلة التريليون دولار اللوغاريتمي (Road to $1,000,000,000,000 Milestone Tracker) */}
      <section
        className="holo-panel"
        aria-label={
          language === 'ar'
            ? 'متتبع مسار التريليون دولار اللوغاريتمي'
            : 'Road to $1,000,000,000,000 Milestone Tracker'
        }
        style={{ padding: '1.2rem 1.35rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}
      >
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Compass size={20} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <h2 style={{ margin: 0, fontSize: '1.12rem', fontWeight: 800 }}>
                {language === 'ar'
                  ? 'مسار الوصول إلى $1,000,000,000,000 — د. مجـووووود'
                  : 'Road to $1,000,000,000,000 (Trilunair) Milestone Tracker'}
              </h2>
            </div>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              {language === 'ar'
                ? 'مقياس نمو لوغاريتمي يوازن بين التراكم المركب وضوابط السحب الأقصى الحتمية.'
                : 'Logarithmic wealth trajectory balancing compound capital scaling with strict drawdown guardrails.'}
            </p>
          </div>

          <div style={{ textAlign: 'end' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {language === 'ar' ? 'التقدم اللوغاريتمي نحو $1T' : 'Logarithmic Scale Progress'}
            </div>
            <strong
              className="fin-value"
              style={{ fontSize: '1.28rem', color: 'var(--accent-primary)' }}
            >
              {formatNumber(logProgressPct, 2)}%
            </strong>
          </div>
        </div>

        {/* شريط التقدم اللوغاريتمي والمعالم الستة ($1M -> $1T) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          <div
            role="progressbar"
            aria-valuenow={Math.round(logProgressPct)}
            aria-valuemin={0}
            aria-valuemax={100}
            style={{
              height: '12px',
              borderRadius: '999px',
              background: 'var(--bg-base)',
              border: '1px solid var(--border-subtle)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${logProgressPct}%`,
                background:
                  'linear-gradient(90deg, var(--accent-tertiary) 0%, var(--accent-primary) 60%, var(--accent-secondary) 100%)',
                transition: 'width var(--fx-transition-smooth)',
              }}
            />
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(6, minmax(0, 1fr))',
              gap: '0.45rem',
            }}
          >
            {TRILUNAIR_MILESTONES.map((step) => {
              const achieved = totalEquity >= step.targetUsd;
              return (
                <div
                  key={step.label}
                  className="holo-panel-subtle"
                  style={{
                    padding: '0.5rem 0.55rem',
                    textAlign: 'center',
                    borderColor: achieved ? 'var(--status-success)' : 'var(--border-subtle)',
                    background: achieved
                      ? 'var(--status-success-bg)'
                      : 'color-mix(in srgb, var(--bg-elevated) 82%, transparent)',
                  }}
                >
                  <div
                    className="tabular-nums"
                    style={{
                      fontWeight: 800,
                      fontSize: '0.86rem',
                      color: achieved ? 'var(--status-success)' : 'var(--text-primary)',
                    }}
                  >
                    {step.label}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                    {achieved ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem', color: 'var(--status-success)' }}>
                        <CheckCircle2 size={11} />
                        {language === 'ar' ? 'مُحقق' : 'Reached'}
                      </span>
                    ) : (
                      <span>
                        {formatNumber(step.targetUsd / Math.max(1, totalEquity), 0)}x
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* محاكي إسقاط النمو المركب (Compound Growth Projection) */}
        <div
          className="holo-panel-subtle"
          style={{
            padding: '0.8rem 1rem',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <TrendingUp size={17} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <span style={{ fontSize: '0.82rem', fontWeight: 700 }}>
              {language === 'ar'
                ? 'محاكاة العائد السنوي المركب المستهدف (CAGR):'
                : 'Projected Compound Annual Growth Rate (CAGR):'}
            </span>
            <div style={{ display: 'flex', gap: '0.35rem' }}>
              {[35, 65, 100, 150].map((cagr) => (
                <button
                  key={cagr}
                  type="button"
                  aria-pressed={targetAnnualCagrPct === cagr}
                  onClick={() => setTargetAnnualCagrPct(cagr)}
                  className={`holo-btn tabular-nums ${
                    targetAnnualCagrPct === cagr ? 'holo-btn-primary' : ''
                  }`}
                  style={{ minHeight: '30px', padding: '0.18rem 0.55rem', fontSize: '0.76rem' }}
                >
                  {cagr}%
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.1rem', flexWrap: 'wrap', fontSize: '0.82rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>
                {language === 'ar' ? 'المدى الزمني التقديري لـ $1T: ' : 'Est. Horizon to $1T: '}
              </span>
              <strong className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
                {formatNumber(yearsToTrilunair, 1)} {language === 'ar' ? 'سنة' : 'yrs'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>
                {language === 'ar' ? 'العائد منذ التأسيس: ' : 'Since Inception: '}
              </span>
              <strong
                className="tabular-nums"
                style={{
                  color: inceptionReturnPct >= 0 ? 'var(--status-success)' : 'var(--status-danger)',
                }}
              >
                {formatSignedPct(inceptionReturnPct)}
              </strong>
            </div>
          </div>
        </div>
      </section>

      {/* 2. بطاقات مؤشرات الأداء والمخاطر الخمسة (KPI Cards) */}
      <section
        aria-label={language === 'ar' ? 'مؤشرات الأداء الرئيسية للمحفظة' : 'Portfolio Key Metrics'}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(215px, 1fr))',
          gap: '0.85rem',
        }}
      >
        <div className="holo-panel" style={{ padding: '0.95rem 1.05rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
            <span>{language === 'ar' ? 'إجمالي حقوق الملكية' : 'Total Equity'}</span>
            <Briefcase size={15} style={{ color: 'var(--accent-primary)' }} />
          </div>
          <div className="fin-value" style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '0.3rem' }}>
            {formatCurrency(totalEquity)}
          </div>
          <div className="tabular-nums" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {language === 'ar' ? 'رأس المال الأولي: ' : 'Initial: '}
            {formatCurrency(initialEquity)}
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.95rem 1.05rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
            <span>{language === 'ar' ? 'السيولة النقدية المتاحة' : 'Available Cash'}</span>
            <Wallet size={15} style={{ color: 'var(--accent-tertiary)' }} />
          </div>
          <div className="fin-value" style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '0.3rem' }}>
            {formatCurrency(cashBalance)}
          </div>
          <div className="tabular-nums" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {formatNumber(totalEquity > 0 ? (cashBalance / totalEquity) * 100 : 0, 1)}%{' '}
            {language === 'ar' ? 'احتياطي سيولة' : 'cash reserve'}
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.95rem 1.05rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
            <span>{language === 'ar' ? 'ربح / خسارة اليوم' : 'Daily P&L'}</span>
            <TrendingUp size={15} style={{ color: dailyPnl >= 0 ? 'var(--status-success)' : 'var(--status-danger)' }} />
          </div>
          <div
            className="fin-value"
            style={{
              fontSize: '1.35rem',
              fontWeight: 800,
              marginTop: '0.3rem',
              color: dailyPnl >= 0 ? 'var(--status-success)' : 'var(--status-danger)',
            }}
          >
            {dailyPnl >= 0 ? '+' : ''}
            {formatCurrency(dailyPnl)}
          </div>
          <div
            className="tabular-nums"
            style={{
              fontSize: '0.75rem',
              color: dailyPnlPct >= 0 ? 'var(--status-success)' : 'var(--status-danger)',
              marginTop: '0.2rem',
            }}
          >
            {formatSignedPct(dailyPnlPct)}
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.95rem 1.05rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
            <span>{language === 'ar' ? 'القيمة المعرضة للمخاطر (VaR 95%)' : 'Daily VaR (95%)'}</span>
            <ShieldAlert size={15} style={{ color: 'var(--status-warning)' }} />
          </div>
          <div className="fin-value" style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '0.3rem' }}>
            {formatCurrency(var95Usd)}
          </div>
          <div className="tabular-nums" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {formatNumber(totalEquity > 0 ? (var95Usd / totalEquity) * 100 : 0, 2)}%{' '}
            {language === 'ar' ? 'من حقوق الملكية' : 'of equity'}
          </div>
        </div>

        <div className="holo-panel" style={{ padding: '0.95rem 1.05rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
            <span>{language === 'ar' ? 'السحب الحالي مقابل الحد الأقصى' : 'Drawdown vs Max Limit'}</span>
            <Clock size={15} style={{ color: 'var(--accent-primary)' }} />
          </div>
          <div className="fin-value" style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '0.3rem' }}>
            {formatNumber(currentDrawdownPct, 2)}% / {formatNumber(maxAllowedDrawdownPct, 1)}%
          </div>
          <div
            style={{
              height: '6px',
              borderRadius: '999px',
              background: 'var(--bg-base)',
              marginTop: '0.45rem',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${Math.min(100, (currentDrawdownPct / Math.max(0.1, maxAllowedDrawdownPct)) * 100)}%`,
                background:
                  currentDrawdownPct > maxAllowedDrawdownPct * 0.75
                    ? 'var(--status-danger)'
                    : 'var(--status-success)',
              }}
            />
          </div>
        </div>
      </section>

      {/* 3. جدول المراكز المفتوحة (Open Positions Table) */}
      <section
        className="holo-panel"
        style={{ padding: '1.05rem 1.2rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800 }}>
            {language === 'ar' ? 'المراكز الاستثمارية المفتوحة' : 'Open Portfolio Positions'}
          </h3>
          <span className="holo-badge tabular-nums">
            {portfolio?.positions.length ?? 0}{' '}
            {language === 'ar' ? 'مراكز نشطة' : 'Active Positions'}
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '0.84rem',
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  color: 'var(--text-muted)',
                  textAlign: 'start',
                }}
              >
                <th style={{ padding: '0.55rem 0.5rem', textAlign: 'start' }}>
                  {language === 'ar' ? 'الأصل' : 'Asset'}
                </th>
                <th style={{ padding: '0.55rem 0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'الكمية' : 'Quantity'}
                </th>
                <th style={{ padding: '0.55rem 0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'متوسط الدخول' : 'Avg Entry'}
                </th>
                <th style={{ padding: '0.55rem 0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'السعر الحالي' : 'Last Price'}
                </th>
                <th style={{ padding: '0.55rem 0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'القيمة السوقية' : 'Market Value'}
                </th>
                <th style={{ padding: '0.55rem 0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'الربح غير المحقق' : 'Unrealized P&L'}
                </th>
                <th style={{ padding: '0.55rem 0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'الوزن %' : 'Weight %'}
                </th>
              </tr>
            </thead>
            <tbody>
              {(portfolio?.positions ?? []).length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)' }}
                  >
                    {language === 'ar'
                      ? 'لا توجد مراكز مفتوحة حالياً — السيولة النقدية متاحة بالكامل.'
                      : 'No open positions — 100% allocated to liquid cash.'}
                  </td>
                </tr>
              ) : (
                (portfolio?.positions ?? []).map((pos) => {
                  const pnlUp = pos.unrealizedPnlUsd >= 0;
                  return (
                    <tr
                      key={pos.symbol}
                      style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    >
                      <td style={{ padding: '0.65rem 0.5rem' }}>
                        {onSelectSymbolForTerminal ? (
                          <button
                            type="button"
                            onClick={() => onSelectSymbolForTerminal(pos.symbol)}
                            className="holo-btn"
                            style={{ minHeight: '30px', padding: '0.2rem 0.55rem', fontSize: '0.8rem' }}
                          >
                            <strong>{pos.symbol}</strong>
                          </button>
                        ) : (
                          <strong>{pos.symbol}</strong>
                        )}
                        <span
                          style={{
                            marginInlineStart: '0.45rem',
                            fontSize: '0.76rem',
                            color: 'var(--text-muted)',
                          }}
                        >
                          {language === 'ar' ? pos.nameAr : pos.nameEn}
                        </span>
                      </td>
                      <td className="tabular-nums" style={{ padding: '0.65rem 0.5rem', textAlign: 'end' }}>
                        {formatNumber(pos.quantity, 4)}
                      </td>
                      <td className="tabular-nums" style={{ padding: '0.65rem 0.5rem', textAlign: 'end' }}>
                        {formatCurrency(pos.avgEntryPrice)}
                      </td>
                      <td className="tabular-nums" style={{ padding: '0.65rem 0.5rem', textAlign: 'end' }}>
                        {formatCurrency(pos.currentPrice)}
                      </td>
                      <td
                        className="tabular-nums"
                        style={{ padding: '0.65rem 0.5rem', textAlign: 'end', fontWeight: 700 }}
                      >
                        {formatCurrency(pos.marketValueUsd)}
                      </td>
                      <td
                        className="tabular-nums"
                        style={{
                          padding: '0.65rem 0.5rem',
                          textAlign: 'end',
                          fontWeight: 700,
                          color: pnlUp ? 'var(--status-success)' : 'var(--status-danger)',
                        }}
                      >
                        {pnlUp ? '+' : ''}
                        {formatCurrency(pos.unrealizedPnlUsd)} ({formatSignedPct(pos.unrealizedPnlPct)})
                      </td>
                      <td className="tabular-nums" style={{ padding: '0.65rem 0.5rem', textAlign: 'end' }}>
                        {formatNumber(pos.weightPct, 1)}%
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 4. سجل الصفقات المنفذة مؤخراً (Recent Executed Orders Table) */}
      <section
        className="holo-panel"
        style={{ padding: '1.05rem 1.2rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800 }}>
            {language === 'ar'
              ? 'سجل الصفقات المنفذة مؤخراً (الصوت / النص / قاعة التداول)'
              : 'Recent Executed Orders (Voice / Text / Terminal)'}
          </h3>
          <span className="holo-badge tabular-nums">{portfolio?.recentOrders.length ?? 0}</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  color: 'var(--text-muted)',
                }}
              >
                <th style={{ padding: '0.5rem', textAlign: 'start' }}>
                  {language === 'ar' ? 'رقم الأمر' : 'Order ID'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'start' }}>
                  {language === 'ar' ? 'الأصل والاتجاه' : 'Symbol & Side'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'الكمية' : 'Quantity'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'سعر التنفيذ' : 'Exec Price'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'القيمة والرسوم' : 'Notional / Fee'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'center' }}>
                  {language === 'ar' ? 'المصدر' : 'Source'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'center' }}>
                  {language === 'ar' ? 'الوضع' : 'Mode'}
                </th>
                <th style={{ padding: '0.5rem', textAlign: 'end' }}>
                  {language === 'ar' ? 'التوقيت' : 'Timestamp'}
                </th>
              </tr>
            </thead>
            <tbody>
              {(portfolio?.recentOrders ?? []).length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    style={{ padding: '1.2rem', textAlign: 'center', color: 'var(--text-muted)' }}
                  >
                    {language === 'ar'
                      ? 'لم يتم تنفيذ أي صفقات في هذه الجلسة بعد.'
                      : 'No orders executed yet in this session.'}
                  </td>
                </tr>
              ) : (
                (portfolio?.recentOrders ?? []).map((ord) => (
                  <tr
                    key={ord.orderId}
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    <td className="tabular-nums" style={{ padding: '0.6rem 0.5rem', color: 'var(--text-muted)' }}>
                      {ord.orderId}
                    </td>
                    <td style={{ padding: '0.6rem 0.5rem' }}>
                      <span
                        className={`holo-badge ${
                          ord.side === 'BUY' ? 'holo-badge-success' : 'holo-badge-danger'
                        }`}
                      >
                        {ord.side} {ord.symbol}
                      </span>
                    </td>
                    <td className="tabular-nums" style={{ padding: '0.6rem 0.5rem', textAlign: 'end' }}>
                      {formatNumber(ord.quantity, 4)}
                    </td>
                    <td className="tabular-nums" style={{ padding: '0.6rem 0.5rem', textAlign: 'end' }}>
                      {formatCurrency(ord.executedPrice)}
                    </td>
                    <td className="tabular-nums" style={{ padding: '0.6rem 0.5rem', textAlign: 'end' }}>
                      <div>{formatCurrency(ord.notionalUsd)}</div>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Fee: {formatCurrency(ord.totalFeeUsd)}
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.5rem', textAlign: 'center' }}>
                      {renderOrderSourceBadge(ord.source)}
                    </td>
                    <td style={{ padding: '0.6rem 0.5rem', textAlign: 'center' }}>
                      <span
                        className={`holo-badge ${
                          ord.tradingMode === 'LIVE' ? 'holo-badge-danger' : 'holo-badge-success'
                        }`}
                      >
                        {ord.tradingMode}
                      </span>
                    </td>
                    <td className="tabular-nums" style={{ padding: '0.6rem 0.5rem', textAlign: 'end', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      {new Date(ord.createdAt).toLocaleTimeString('en-GB', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. المدير المالي الشخصي، مخطط الديون، مستحقات العمل السعودية، ومهلة الـ 60 يوماً ودفتر الاستثمار */}
      {wealthOverview && (
        <section
          data-testid="personal-cfo-wealth-panel"
          className="holo-panel"
          style={{ padding: '1.25rem 1.35rem', display: 'flex', flexDirection: 'column', gap: '1.15rem' }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Landmark size={20} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
                <h2 style={{ margin: 0, fontSize: '1.08rem', fontWeight: 800 }}>
                  {isAr
                    ? 'المدير المالي الشخصي ومعماري الثروة — خطة الراتب والديون ومستحقات نظام العمل السعودي'
                    : 'Personal CFO & Wealth Architect — Salary Plan, Debt Trade-Off & Saudi Employment Benefits'}
                </h2>
              </div>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {isAr
                  ? 'خطة استثمارية متوازية معتمدة من المالك (20,000 ريال يوم 28 ميلادي) مع عزل صارم للمستحقات التعاقدية المحتملة عن السيولة النقدية المتاحة.'
                  : 'Owner-approved SAR 20,000 salary allocation (28th payday) with anti-double-counting reconciliation & segregated contingent Saudi labor benefits.'}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
              <span className="holo-badge holo-badge-success">
                <ShieldCheck size={13} />
                <span>
                  {isAr
                    ? `توازن الراتب: ${formatNumber(wealthOverview.salaryAndCashFlow.monthlySalarySar, 0)} ريال`
                    : `Balanced: SAR ${formatNumber(wealthOverview.salaryAndCashFlow.monthlySalarySar, 0)}`}
                </span>
              </span>
              <span className="holo-badge holo-badge-warning" data-testid="provisional-benefits-badge">
                <Scale size={13} />
                <span>{wealthOverview.employmentBenefits.statusLabel}</span>
              </span>
            </div>
          </div>

          {cfoFeedback && (
            <div className="holo-panel-subtle" style={{ padding: '0.6rem 0.85rem', borderColor: 'var(--accent-primary)', fontSize: '0.82rem' }}>
              {cfoFeedback}
            </div>
          )}

          {/* أ) التنبيهات المالية والتعاقدية الاستباقية (Financial & Legal Alerts) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))', gap: '0.65rem' }} data-testid="wealth-financial-alerts">
            {wealthOverview.financialAlerts.map((al) => (
              <div
                key={al.alertId}
                className="holo-panel-subtle"
                style={{
                  padding: '0.7rem 0.85rem',
                  borderInlineStart: `3px solid ${
                    al.severity === 'CRITICAL'
                      ? 'var(--status-danger)'
                      : al.severity === 'WARNING' || al.severity === 'IMPORTANT'
                        ? 'var(--status-warning)'
                        : 'var(--accent-primary)'
                  }`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700, fontSize: '0.82rem' }}>
                  <AlertTriangle size={14} style={{ color: 'var(--status-warning)' }} />
                  <span>{isAr ? al.titleAr : al.titleEn}</span>
                </div>
                <p style={{ margin: '0.3rem 0 0', fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  {isAr ? al.detailAr : al.detailEn}
                </p>
              </div>
            ))}
          </div>

          {/* ب) توزيع الراتب الشهري (20,000 ريال يوم 28) ومخطط البطاقات الائتمانية */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '0.95rem' }}>
            <div className="holo-panel-subtle" style={{ padding: '0.9rem 1rem' }} data-testid="salary-allocation-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                <strong style={{ fontSize: '0.9rem' }}>
                  {isAr
                    ? `دورة الراتب (يوم ${wealthOverview.salaryAndCashFlow.paydayDayOfMonth}) — منع الازدواج الحسابي`
                    : `Salary Cycle (Day ${wealthOverview.salaryAndCashFlow.paydayDayOfMonth}) — Anti-Double-Counting`}
                </strong>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                  {isAr
                    ? `الراتب القادم: ${wealthOverview.salaryAndCashFlow.nextPaydayDate}`
                    : `Next Payday: ${wealthOverview.salaryAndCashFlow.nextPaydayDate}`}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.42rem' }}>
                {wealthOverview.salaryAndCashFlow.buckets.map((b) => (
                  <div
                    key={b.category}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.38rem 0.55rem',
                      borderRadius: '6px',
                      background: 'color-mix(in srgb, var(--bg-base) 65%, transparent)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <span>{isAr ? b.labelAr : b.labelEn}</span>
                    <span className="tabular-nums" style={{ fontWeight: 700 }}>
                      SAR {formatNumber(b.plannedSar, 0)} ({formatNumber(b.shareOfSalaryPct, 1)}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="holo-panel-subtle" style={{ padding: '0.9rem 1rem' }} data-testid="credit-card-debt-planner">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
                <strong style={{ fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CreditCard size={15} style={{ color: 'var(--accent-primary)' }} />
                  {isAr ? 'مخطط سداد البطاقات ومفاضلة تكلفة التمويل' : 'Credit-Card Planner & Financing Trade-Off'}
                </strong>
                <span className="holo-badge">
                  SAR {formatNumber(wealthOverview.debtPlanner.monthlyRepaymentBudgetSar, 0)}/mo
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '0.65rem' }}>
                {wealthOverview.debtPlanner.cards.map((card) => (
                  <div
                    key={card.cardId}
                    style={{
                      padding: '0.5rem 0.65rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      fontSize: '0.78rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                      <span>{isAr ? card.issuerNameAr : card.issuerNameEn}</span>
                      <span className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
                        {isAr ? 'التخصيص:' : 'Allocated:'} SAR {formatNumber(card.provisionalMonthlyAllocationSar, 0)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      <span className="tabular-nums">
                        {isAr ? 'الرصيد التقديري:' : 'Approx. Balance:'} SAR {formatNumber(card.approximateBalanceSar, 0)}
                      </span>
                      <span className="tabular-nums" style={{ color: 'var(--status-warning)' }}>
                        {isAr ? 'المستحق/المتأخر:' : 'Due incl. Arrears:'} SAR {formatNumber(card.reportedAmountDueInclArrearsSar, 0)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                {isAr
                  ? wealthOverview.debtPlanner.debtVsInvestmentTradeOff.tradeOffExplanationAr
                  : wealthOverview.debtPlanner.debtVsInvestmentTradeOff.tradeOffExplanationEn}
              </p>
            </div>
          </div>

          {/* ج) حاسبة نظام العمل السعودي ومهلة إشعار عدم التجديد قبل 60 يوماً */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '0.95rem' }}>
            <div className="holo-panel-subtle" style={{ padding: '0.9rem 1rem' }} data-testid="saudi-labor-benefits-calculator">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.55rem' }}>
                <strong style={{ fontSize: '0.9rem' }}>
                  {isAr
                    ? 'حاسبة مستحقات نظام العمل السعودي (م55 / م74 / م84 / م85 / م111)'
                    : 'Saudi Labor Law Benefits Calculator (Arts. 55, 74, 84, 85, 111)'}
                </strong>
                <span className="holo-badge holo-badge-warning">
                  {isAr ? 'مستحق مستقبلي محتمل (غير سائل)' : 'Contingent Receivable (Non-Liquid)'}
                </span>
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                {isAr
                  ? `المباشرة: ${wealthOverview.employmentBenefits.contractSummary.commencementDate} • عقد محدد المدة يتجدد تلقائياً (مهلة إشعار ${wealthOverview.employmentBenefits.contractSummary.nonRenewalNoticeDays} يوماً) • رصيد الإجازات غير المستعمل المقدر: ${wealthOverview.employmentBenefits.contractSummary.accruedUnusedLeaveDays} يوماً.`
                  : `Start: ${wealthOverview.employmentBenefits.contractSummary.commencementDate} • Fixed-Term Auto-Renewing (${wealthOverview.employmentBenefits.contractSummary.nonRenewalNoticeDays}d notice) • Unused Leave: ${wealthOverview.employmentBenefits.contractSummary.accruedUnusedLeaveDays} days.`}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                {[
                  wealthOverview.employmentBenefits.scenarios.fixedTermExpiryNonRenewal,
                  wealthOverview.employmentBenefits.scenarios.ordinaryResignation,
                  wealthOverview.employmentBenefits.scenarios.employerInitiatedTermination,
                ].map((sc) => (
                  <div
                    key={sc.scenarioId}
                    style={{
                      padding: '0.5rem 0.65rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      background:
                        sc.scenarioId === 'FIXED_TERM_EXPIRY_NON_RENEWAL'
                          ? 'color-mix(in srgb, var(--accent-primary) 10%, transparent)'
                          : 'transparent',
                      fontSize: '0.77rem',
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>{isAr ? sc.titleAr : sc.titleEn}</div>
                    <div className="tabular-nums" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.2rem', color: 'var(--text-secondary)' }}>
                      <span>EOSB: SAR {formatNumber(sc.eosbAwardSar, 0)}</span>
                      <span>Leave: SAR {formatNumber(sc.unusedLeaveCompensationSar, 0)}</span>
                      <strong style={{ color: 'var(--accent-primary)' }}>
                        Total: SAR {formatNumber(sc.combinedEstimatedBenefitsSar, 0)}
                      </strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="holo-panel-subtle" style={{ padding: '0.9rem 1rem' }} data-testid="contract-renewal-deadline-tracker">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.55rem' }}>
                <strong style={{ fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CalendarClock size={15} style={{ color: 'var(--accent-primary)' }} />
                  {isAr
                    ? 'متتبع مهلة إشعار عدم تجديد العقد (60 يوماً)'
                    : '60-Day Contract Non-Renewal Deadline Intelligence'}
                </strong>
                <span className="holo-badge holo-badge-accent">
                  {wealthOverview.contractRenewalIntelligence.finalNoticeDeadlineDate}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '0.45rem', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap' }}>
                <input
                  type="date"
                  aria-label="Contract Expiry Date"
                  className="holo-input"
                  style={{ maxWidth: '165px', minHeight: '34px', padding: '0.25rem 0.5rem', fontSize: '0.78rem' }}
                  value={expiryDraft}
                  onChange={(e) => setExpiryDraft(e.target.value)}
                />
                <button type="button" className="holo-btn" style={{ minHeight: '34px', fontSize: '0.76rem' }} onClick={handleRecalculateContractExpiry}>
                  {isAr ? 'تحديث موعد الانتهاء' : 'Recalculate Cutoff'}
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '0.65rem' }}>
                {wealthOverview.contractRenewalIntelligence.reminders.map((rem) => (
                  <div
                    key={rem.milestoneCode}
                    style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', padding: '0.3rem 0.45rem', borderRadius: '6px', background: 'color-mix(in srgb, var(--bg-base) 65%, transparent)' }}
                  >
                    <span>-{rem.daysBeforeExpiry}d ({rem.reminderDate})</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{rem.status}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: '0.45rem', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder={isAr ? 'مرجع عقد قوى / مسودة الإشعار للحفظ الآمن...' : 'Qiwa contract ref / notice draft title...'}
                  className="holo-input"
                  style={{ flex: 1, minHeight: '34px', padding: '0.25rem 0.55rem', fontSize: '0.76rem' }}
                  value={evidenceTitle}
                  onChange={(e) => setEvidenceTitle(e.target.value)}
                />
                <button type="button" className="holo-btn" style={{ minHeight: '34px', fontSize: '0.75rem' }} onClick={handleVaultEvidence}>
                  <FileCheck2 size={13} />
                  <span>{isAr ? 'حفظ إثبات' : 'Vault Proof'}</span>
                </button>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                {isAr
                  ? 'حماية صارمة: لن يرسل النظام أي إشعار عدم تجديد تلقائياً بدون إجراء وموافقة صريحة من المالك.'
                  : 'Safety Lock: System NEVER auto-sends a non-renewal notice without explicit owner action.'}
              </div>
            </div>
          </div>

          {/* د) دفتر الأستاذ المخصص للاستثمار (2,125 ريال/شهرياً) ومقارنة الفئات وسيناريوهات الهبوط */}
          <div className="holo-panel-subtle" style={{ padding: '0.95rem 1.05rem' }} data-testid="investment-allocation-ledger">
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '0.6rem', marginBottom: '0.7rem' }}>
              <div>
                <strong style={{ fontSize: '0.92rem' }}>
                  {isAr
                    ? 'دفتر رأس المال الاستثماري المخصص (2,125 ريال/شهرياً) ومقارنة الفئات والمخاطر'
                    : 'Dedicated Investment Capital Ledger (SAR 2,125/mo) & Multi-Asset Risk Comparison'}
                </strong>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {isAr
                    ? `الإجمالي المخصص في الدفتر: ${formatNumber(wealthOverview.investmentCommandCenter.ledgerSummary.cumulativeAllocatedCapitalSar, 2)} ريال • التداول مقفل على PAPER بدون ضمان عوائد.`
                    : `Cumulative Ledger Principal: SAR ${formatNumber(wealthOverview.investmentCommandCenter.ledgerSummary.cumulativeAllocatedCapitalSar, 2)} • Locked to PAPER simulation; zero return guarantees.`}
                </div>
              </div>
              <button
                type="button"
                data-testid="record-monthly-investment-btn"
                className="holo-btn holo-btn-primary"
                style={{ minHeight: '35px', fontSize: '0.78rem' }}
                onClick={handleLogMonthlyInvestment}
              >
                {isAr ? '+ تسجيل دفعة دورة 2,125 ريال (PAPER)' : '+ Log SAR 2,125 Cycle Allocation (PAPER)'}
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(245px, 1fr))', gap: '0.65rem' }}>
              {wealthOverview.investmentCommandCenter.opportunityAndRiskAnalysis.sleeves.map((sl) => (
                <div key={sl.sleeveId} style={{ padding: '0.6rem 0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '0.77rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                    <span>{isAr ? sl.nameAr : sl.nameEn}</span>
                    <span className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
                      {sl.targetWeightPct}% (SAR {formatNumber(sl.monthlyAllocationSar, 2)})
                    </span>
                  </div>
                  <div style={{ marginTop: '0.28rem', color: 'var(--text-secondary)' }}>
                    Vol: {sl.annualizedVolatilityPct}% • Fee: {sl.estimatedTransactionFeeBps} bps • Stress: {sl.severeStressDrawdownPct}%
                  </div>
                  <div style={{ marginTop: '0.2rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {sl.liquidityProfile}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {wealthOverview.binancePersonalCfoBridge && (
            <div
              className="holo-panel-subtle"
              style={{ padding: '0.95rem 1.05rem' }}
              data-testid="cfo-personal-binance-bridge"
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                <strong>
                  {isAr
                    ? 'جسر مطابقة حساب Binance الفوري الشخصي (2,125 ريال/شهرياً — معزول عن PAPER)'
                    : 'Personal Binance Spot CFO Reconciliation Bridge (SAR 2,125/mo — Segregated from PAPER)'}
                </strong>
                <span className="holo-badge">
                  {wealthOverview.binancePersonalCfoBridge.connectionStatus === 'PENDING_OWNER_SETUP'
                    ? 'PENDING OWNER SETUP'
                    : wealthOverview.binancePersonalCfoBridge.connectionStatus}
                </span>
              </div>
              <div style={{ marginTop: '0.45rem', fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                <span>
                  {isAr ? 'الودائع/المشتريات الموحدة دون ازدواج:' : 'Deduplicated Cycle Deployment:'}{' '}
                  <strong>
                    SAR {formatNumber(wealthOverview.binancePersonalCfoBridge.cycleReconciliation.deduplicatedActualDeploymentSar, 2)}
                  </strong>
                </span>
                <span>
                  {isAr ? 'رأس المال المساهم:' : 'Contributed Principal:'}{' '}
                  <strong>
                    SAR {formatNumber(wealthOverview.binancePersonalCfoBridge.capitalVsPerformanceSeparation.cumulativeContributedCapitalSar, 2)}
                  </strong>
                </span>
                <span>
                  {isAr ? 'صافي ربح/خسارة السوق بعد الرسوم:' : 'Net Market P&L (After Fees):'}{' '}
                  <strong>
                    SAR {formatNumber(wealthOverview.binancePersonalCfoBridge.capitalVsPerformanceSeparation.netMarketPnlAfterFeesSar, 2)}
                  </strong>
                </span>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
};

export default PortfolioView;
