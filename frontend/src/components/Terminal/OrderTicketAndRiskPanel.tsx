/**
 * تذكرة الأوامر الموحدة ولوحة الفحص الحتمي للمخاطر (Order Ticket & Deterministic Risk Panel)
 * تعرض وضع التداول النشط (PAPER / LIVE)، تحذير مفتاح الطوارئ، التكاليف التقديرية،
 * وفحوصات المخاطر الخمسة قبل السماح بفتح بوابة التصريح النهائي.
 */

import React, { useMemo, useState } from 'react';
import {
  AlertOctagon,
  CheckCircle2,
  Calculator,
  Lock,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import { formatCurrency, formatNumber } from '../../i18n/translations';
import type {
  MarketAsset,
  OrderSide,
  OrderType,
  PortfolioSnapshot,
  TradeProposalEvaluation,
  TradeProposalInput,
  TradingMode,
} from '../../types/trilunair';

export interface OrderTicketAndRiskPanelProps {
  selectedAsset: MarketAsset | null;
  portfolio: PortfolioSnapshot | null;
  tradingMode: TradingMode;
  killSwitchActive: boolean;
  activeEvaluation: TradeProposalEvaluation | null;
  isSubmitting?: boolean;
  onProposeOrder: (proposal: TradeProposalInput) => Promise<TradeProposalEvaluation | void>;
  onOpenAuthorizationModal: (evaluation: TradeProposalEvaluation) => void;
}

function getDefaultQuantityStr(asset: MarketAsset | null): string {
  if (!asset || asset.price <= 0) return '1';
  const defaultNotional = 12_000;
  const suggestedQty = Number((defaultNotional / asset.price).toPrecision(3));
  return String(Math.max(0.01, suggestedQty));
}

function getDefaultLimitPriceStr(asset: MarketAsset | null): string {
  if (!asset) return '';
  return asset.price >= 100 ? asset.price.toFixed(2) : asset.price.toFixed(4);
}

const OrderTicketInner: React.FC<OrderTicketAndRiskPanelProps> = ({
  selectedAsset,
  portfolio,
  tradingMode,
  killSwitchActive,
  activeEvaluation,
  isSubmitting = false,
  onProposeOrder,
  onOpenAuthorizationModal,
}) => {
  const { language } = useTheme();

  const [side, setSide] = useState<OrderSide>('BUY');
  const [orderType, setOrderType] = useState<OrderType>('MARKET');
  const [quantityStr, setQuantityStr] = useState<string>(() => getDefaultQuantityStr(selectedAsset));
  const [limitPriceStr, setLimitPriceStr] = useState<string>(() => getDefaultLimitPriceStr(selectedAsset));
  const [stopLossStr, setStopLossStr] = useState<string>('');
  const [takeProfitStr, setTakeProfitStr] = useState<string>('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [lastEvaluation, setLastEvaluation] = useState<TradeProposalEvaluation | null>(null);

  const effectivePrice = useMemo(() => {
    if (orderType === 'LIMIT') {
      const parsed = parseFloat(limitPriceStr);
      if (Number.isFinite(parsed) && parsed > 0) return parsed;
    }
    return selectedAsset?.price ?? 0;
  }, [orderType, limitPriceStr, selectedAsset?.price]);

  const parsedQuantity = useMemo(() => {
    const q = parseFloat(quantityStr);
    return Number.isFinite(q) && q > 0 ? q : 0;
  }, [quantityStr]);

  // معاينة فورية محلية للتكاليف قبل الإرسال إلى الخادم
  const livePreviewCosts = useMemo(() => {
    const notionalUsd = parsedQuantity * effectivePrice;
    const spreadBps = selectedAsset?.spreadBps ?? 6;
    const spreadCostUsd = notionalUsd * (spreadBps / 10_000) * 0.5;
    const commissionUsd = notionalUsd * 0.0008;
    const slippageCostUsd = notionalUsd * (orderType === 'MARKET' ? 0.0005 : 0.0001);
    const totalEstimatedCostUsd = spreadCostUsd + commissionUsd + slippageCostUsd;
    const costBps = notionalUsd > 0 ? (totalEstimatedCostUsd / notionalUsd) * 10_000 : 0;

    return {
      notionalUsd,
      spreadCostUsd,
      commissionUsd,
      slippageCostUsd,
      totalEstimatedCostUsd,
      costBps,
    };
  }, [parsedQuantity, effectivePrice, selectedAsset?.spreadBps, orderType]);

  const applyQuickAllocationPct = (pctOfCashOrPosition: number) => {
    if (!selectedAsset || effectivePrice <= 0) return;

    if (side === 'SELL' && portfolio) {
      const heldPos = portfolio.positions.find((p) => p.symbol === selectedAsset.symbol);
      if (heldPos && heldPos.quantity > 0) {
        const qty = Number(((heldPos.quantity * pctOfCashOrPosition) / 100).toFixed(4));
        setQuantityStr(String(Math.max(0.0001, qty)));
        return;
      }
    }

    const availableCash = portfolio?.cashBalance ?? 250_000;
    const targetUsd = (availableCash * pctOfCashOrPosition) / 100;
    const qty = Number((targetUsd / effectivePrice).toFixed(4));
    setQuantityStr(String(Math.max(0.0001, qty)));
  };

  const handleSubmitProposal = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (!selectedAsset) {
      setLocalError(
        language === 'ar' ? 'يرجى اختيار أصل مالي أولاً.' : 'Please select an asset first.'
      );
      return;
    }

    if (parsedQuantity <= 0) {
      setLocalError(
        language === 'ar'
          ? 'يرجى إدخال كمية تداول موجبة صالحة.'
          : 'Please enter a valid positive quantity.'
      );
      return;
    }

    const limitPrice = orderType === 'LIMIT' ? parseFloat(limitPriceStr) : null;
    if (orderType === 'LIMIT' && (!limitPrice || limitPrice <= 0)) {
      setLocalError(
        language === 'ar'
          ? 'يرجى إدخال سعر محدد (Limit Price) صالح.'
          : 'Please enter a valid limit price.'
      );
      return;
    }

    const stopLoss = stopLossStr.trim() ? parseFloat(stopLossStr) : null;
    const takeProfit = takeProfitStr.trim() ? parseFloat(takeProfitStr) : null;

    const proposal: TradeProposalInput = {
      symbol: selectedAsset.symbol,
      side,
      orderType,
      quantity: parsedQuantity,
      limitPrice: limitPrice && Number.isFinite(limitPrice) ? limitPrice : null,
      stopLoss: stopLoss && Number.isFinite(stopLoss) ? stopLoss : null,
      takeProfit: takeProfit && Number.isFinite(takeProfit) ? takeProfit : null,
      source: 'TERMINAL',
    };

    try {
      const result = await onProposeOrder(proposal);
      if (result) {
        setLastEvaluation(result);
      }
    } catch (err) {
      setLocalError(
        err instanceof Error
          ? err.message
          : language === 'ar'
            ? 'تعذر فحص المقترح عبر محرك المخاطر.'
            : 'Failed to validate trade proposal.'
      );
    }
  };

  const candidateEval = lastEvaluation ?? activeEvaluation;
  const evaluationForAsset =
    candidateEval && (!selectedAsset || candidateEval.proposal.symbol === selectedAsset.symbol)
      ? candidateEval
      : activeEvaluation;

  const displayedCosts = evaluationForAsset?.estimatedCosts ?? livePreviewCosts;

  return (
    <section
      className="holo-panel"
      aria-label={
        language === 'ar'
          ? 'تذكرة التداول وفحص المخاطر الحتمي'
          : 'Order Ticket & Deterministic Risk Panel'
      }
      style={{ padding: '1rem 1.1rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
    >
      {/* شريط العنوان وشارة وضع التداول PAPER / LIVE */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          <ShieldCheck size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
          <h3 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 800 }}>
            {language === 'ar' ? 'تذكرة التداول وفحص المخاطر' : 'Order Ticket & Risk Engine'}
          </h3>
        </div>

        <span
          data-testid="ticket-trading-mode-badge"
          className={`holo-badge ${
            tradingMode === 'LIVE' ? 'holo-badge-danger' : 'holo-badge-success'
          }`}
        >
          {tradingMode === 'LIVE'
            ? language === 'ar'
              ? 'تداول حقيقي (LIVE)'
              : 'LIVE TRADING'
            : language === 'ar'
              ? 'تداول ورقي آمن (PAPER)'
              : 'PAPER TRADING'}
        </span>
      </div>

      {/* تحذير مفتاح الطوارئ Kill Switch */}
      {killSwitchActive && (
        <div
          role="alert"
          data-testid="ticket-killswitch-alert"
          style={{
            padding: '0.65rem 0.8rem',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--status-danger-bg)',
            border: '1px solid var(--status-danger)',
            color: 'var(--status-danger)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.55rem',
            fontSize: '0.82rem',
            fontWeight: 700,
          }}
        >
          <AlertOctagon size={18} style={{ flexShrink: 0 }} aria-hidden="true" />
          <span>
            {language === 'ar'
              ? 'مفتاح الطوارئ (Kill Switch) مفعل حالياً — سيتم رفض تنفيذ أي أوامر جديدة لحماية رأس المال.'
              : 'Emergency Kill Switch is ACTIVE — Order execution is frozen to protect capital.'}
          </span>
        </div>
      )}

      <form onSubmit={handleSubmitProposal} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {/* مفتاح شراء / بيع (BUY / SELL) */}
        <div
          role="group"
          aria-label={language === 'ar' ? 'اتجاه الصفقة' : 'Order Side'}
          style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}
        >
          <button
            type="button"
            aria-pressed={side === 'BUY'}
            onClick={() => setSide('BUY')}
            className={`holo-btn ${side === 'BUY' ? 'holo-btn-buy' : ''}`}
          >
            {language === 'ar' ? 'شراء (BUY)' : 'BUY'}
          </button>
          <button
            type="button"
            aria-pressed={side === 'SELL'}
            onClick={() => setSide('SELL')}
            className={`holo-btn ${side === 'SELL' ? 'holo-btn-sell' : ''}`}
          >
            {language === 'ar' ? 'بيع (SELL)' : 'SELL'}
          </button>
        </div>

        {/* نوع الأمر (MARKET / LIMIT) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
          <button
            type="button"
            aria-pressed={orderType === 'MARKET'}
            onClick={() => setOrderType('MARKET')}
            className={`holo-btn ${orderType === 'MARKET' ? 'holo-btn-primary' : ''}`}
            style={{ minHeight: '36px', fontSize: '0.82rem' }}
          >
            {language === 'ar' ? 'أمر سوق (MARKET)' : 'MARKET'}
          </button>
          <button
            type="button"
            aria-pressed={orderType === 'LIMIT'}
            onClick={() => setOrderType('LIMIT')}
            className={`holo-btn ${orderType === 'LIMIT' ? 'holo-btn-primary' : ''}`}
            style={{ minHeight: '36px', fontSize: '0.82rem' }}
          >
            {language === 'ar' ? 'أمر محدد (LIMIT)' : 'LIMIT'}
          </button>
        </div>

        {/* حقل الكمية مع أزرار النسب السريعة */}
        <div>
          <label
            htmlFor="ticket-quantity-input"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              marginBottom: '0.3rem',
            }}
          >
            <span>
              {language === 'ar' ? 'الكمية المطلوبة' : 'Order Quantity'} ({selectedAsset?.symbol ?? 'BTC'})
            </span>
            <span className="tabular-nums" style={{ color: 'var(--text-muted)' }}>
              {language === 'ar' ? 'السيولة: ' : 'Cash: '}
              {formatCurrency(portfolio?.cashBalance ?? 0, true)}
            </span>
          </label>
          <input
            id="ticket-quantity-input"
            type="number"
            step="any"
            min="0"
            value={quantityStr}
            onChange={(e) => setQuantityStr(e.target.value)}
            className="holo-input tabular-nums"
            required
          />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.35rem', marginTop: '0.4rem' }}>
            {[5, 10, 20, 35].map((pct) => (
              <button
                key={pct}
                type="button"
                onClick={() => applyQuickAllocationPct(pct)}
                className="holo-btn tabular-nums"
                style={{ minHeight: '30px', padding: '0.15rem 0.35rem', fontSize: '0.75rem' }}
              >
                {pct}%
              </button>
            ))}
          </div>
        </div>

        {/* حقل السعر المحدد عند اختيار LIMIT */}
        {orderType === 'LIMIT' && (
          <div>
            <label
              htmlFor="ticket-limit-price-input"
              style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}
            >
              {language === 'ar' ? 'السعر المحدد (Limit Price USD)' : 'Limit Price (USD)'}
            </label>
            <input
              id="ticket-limit-price-input"
              type="number"
              step="any"
              min="0"
              value={limitPriceStr}
              onChange={(e) => setLimitPriceStr(e.target.value)}
              className="holo-input tabular-nums"
              required
            />
          </div>
        )}

        {/* حقلا إيقاف الخسارة وجني الأرباح الاختياريان */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
          <div>
            <label
              htmlFor="ticket-sl-input"
              style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}
            >
              {language === 'ar' ? 'وقف الخسارة (Stop Loss)' : 'Stop Loss (Optional)'}
            </label>
            <input
              id="ticket-sl-input"
              type="number"
              step="any"
              min="0"
              placeholder="--"
              value={stopLossStr}
              onChange={(e) => setStopLossStr(e.target.value)}
              className="holo-input tabular-nums"
              style={{ minHeight: '38px', fontSize: '0.84rem' }}
            />
          </div>
          <div>
            <label
              htmlFor="ticket-tp-input"
              style={{ display: 'block', fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}
            >
              {language === 'ar' ? 'جني الأرباح (Take Profit)' : 'Take Profit (Optional)'}
            </label>
            <input
              id="ticket-tp-input"
              type="number"
              step="any"
              min="0"
              placeholder="--"
              value={takeProfitStr}
              onChange={(e) => setTakeProfitStr(e.target.value)}
              className="holo-input tabular-nums"
              style={{ minHeight: '38px', fontSize: '0.84rem' }}
            />
          </div>
        </div>

        {/* تفصيل التكاليف التقديرية للصفقة */}
        <div
          className="holo-panel-subtle"
          data-testid="estimated-costs-box"
          style={{ padding: '0.65rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.32rem', fontSize: '0.78rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.15rem' }}>
            <Calculator size={14} aria-hidden="true" />
            <span>{language === 'ar' ? 'التكاليف التقديرية للصفقة' : 'Estimated Trading Costs'}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{language === 'ar' ? 'القيمة الاسمية:' : 'Notional Value:'}</span>
            <strong className="tabular-nums">{formatCurrency(displayedCosts.notionalUsd)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{language === 'ar' ? 'تكلفة الفارق السعري (Spread):' : 'Spread Cost:'}</span>
            <span className="tabular-nums">{formatCurrency(displayedCosts.spreadCostUsd)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{language === 'ar' ? 'العمولة (Commission):' : 'Commission:'}</span>
            <span className="tabular-nums">{formatCurrency(displayedCosts.commissionUsd)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>{language === 'ar' ? 'الانزلاق التقديري (Slippage):' : 'Est. Slippage:'}</span>
            <span className="tabular-nums">{formatCurrency(displayedCosts.slippageCostUsd)}</span>
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              borderTop: '1px solid var(--border-subtle)',
              paddingTop: '0.3rem',
              marginTop: '0.1rem',
              fontWeight: 700,
            }}
          >
            <span>{language === 'ar' ? 'إجمالي التكلفة التقديرية:' : 'Total Est. Cost:'}</span>
            <span className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
              {formatCurrency(displayedCosts.totalEstimatedCostUsd)} ({formatNumber(displayedCosts.costBps, 1)} bps)
            </span>
          </div>
        </div>

        {localError && (
          <div
            role="alert"
            style={{
              padding: '0.5rem 0.65rem',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--status-danger-bg)',
              color: 'var(--status-danger)',
              fontSize: '0.8rem',
            }}
          >
            {localError}
          </div>
        )}

        <button
          type="submit"
          data-testid="validate-propose-btn"
          disabled={isSubmitting || !selectedAsset}
          className="holo-btn holo-btn-primary"
          style={{ width: '100%' }}
        >
          <ShieldCheck size={16} aria-hidden="true" />
          <span>
            {isSubmitting
              ? language === 'ar'
                ? 'جاري فحص المخاطر الحتمي...'
                : 'Validating Risk Constraints...'
              : language === 'ar'
                ? 'فحص المخاطر وإعداد المقترح'
                : 'Validate & Propose Order'}
          </span>
        </button>
      </form>

      {/* نتائج فحوصات المخاطر الحتمية الخمسة بعد الفحص */}
      {evaluationForAsset && (
        <div
          className="holo-panel-subtle"
          data-testid="risk-checks-results"
          style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.55rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <strong style={{ fontSize: '0.82rem' }}>
              {language === 'ar' ? 'فحوصات المخاطر الحتمية (5 معايير)' : 'Deterministic Risk Checks'}
            </strong>
            <span
              className={`holo-badge tabular-nums ${
                evaluationForAsset.status === 'APPROVED_FOR_AUTH'
                  ? 'holo-badge-success'
                  : 'holo-badge-danger'
              }`}
            >
              {evaluationForAsset.riskAssessment.riskLevel} ({evaluationForAsset.riskAssessment.riskScore}/100)
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {evaluationForAsset.riskAssessment.checks.map((chk) => (
              <div
                key={chk.code}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.45rem',
                  fontSize: '0.77rem',
                  padding: '0.3rem 0.45rem',
                  borderRadius: '6px',
                  background: chk.passed ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
                  color: chk.passed ? 'var(--status-success)' : 'var(--status-danger)',
                }}
              >
                {chk.passed ? (
                  <CheckCircle2 size={14} style={{ marginTop: '2px', flexShrink: 0 }} aria-hidden="true" />
                ) : (
                  <XCircle size={14} style={{ marginTop: '2px', flexShrink: 0 }} aria-hidden="true" />
                )}
                <span>{language === 'ar' ? chk.messageAr : chk.messageEn}</span>
              </div>
            ))}
          </div>

          {evaluationForAsset.status === 'APPROVED_FOR_AUTH' ? (
            <button
              type="button"
              data-testid="open-auth-gateway-btn"
              onClick={() => onOpenAuthorizationModal(evaluationForAsset)}
              className="holo-btn holo-btn-buy"
              style={{ width: '100%', marginTop: '0.2rem' }}
            >
              <Lock size={15} aria-hidden="true" />
              <span>
                {language === 'ar'
                  ? 'فتح بوابة التصريح والتنفيذ النهائي'
                  : 'Open Authorization Modal to Execute'}
              </span>
            </button>
          ) : (
            <div
              role="alert"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                fontSize: '0.78rem',
                color: 'var(--status-danger)',
                fontWeight: 600,
              }}
            >
              <ShieldAlert size={16} style={{ flexShrink: 0 }} aria-hidden="true" />
              <span>
                {language === 'ar'
                  ? 'تم حظر المقترح آلياً بسبب تجاوز حدود المخاطر الصارمة.'
                  : 'Proposal blocked automatically due to risk limit violations.'}
              </span>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export const OrderTicketAndRiskPanel: React.FC<OrderTicketAndRiskPanelProps> = (props) => (
  <OrderTicketInner key={props.selectedAsset?.symbol ?? 'default'} {...props} />
);

export default OrderTicketAndRiskPanel;

