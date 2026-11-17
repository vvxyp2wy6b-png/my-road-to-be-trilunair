/**
 * قاعة التداول الحية المتكاملة (Live Terminal Master View)
 * تجمع قائمة مراقبة الأصول الستة، مخطط الشموع الهولوغرامي، قاعة اجتماع الوكلاء المدمجة،
 * تذكرة التداول وفحص المخاطر، دفتر الأوامر، وكرة الثروة ثلاثية الأبعاد المحمية بـ VisualEffectsBoundary.
 */

import React, { useMemo } from 'react';
import { ArrowDownRight, ArrowUpRight, BookOpen, Radio } from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import { formatCurrency, formatNumber, formatSignedPct } from '../../i18n/translations';
import type { SpeechEngineController } from '../../voice/useSpeechEngine';
import type {
  AgentMeetingResult,
  MarketAsset,
  MarketCandlesResponse,
  PortfolioSnapshot,
  TradeProposalEvaluation,
  TradeProposalInput,
  TradingMode,
} from '../../types/trilunair';
import { VisualEffectsBoundary } from '../Effects/VisualEffectsBoundary';
import { HolographicOrb3D } from '../Effects/HolographicOrb3D';
import { HolographicCandlestickChart } from './HolographicCandlestickChart';
import { OrderTicketAndRiskPanel } from './OrderTicketAndRiskPanel';
import { AgentMeetingRoom } from '../MeetingRoom/AgentMeetingRoom';

export interface LiveTerminalViewProps {
  assets: MarketAsset[];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  candlesData: MarketCandlesResponse | null;
  timeframe: string;
  onTimeframeChange: (timeframe: string) => void;
  isCandlesLoading?: boolean;
  portfolio: PortfolioSnapshot | null;
  tradingMode: TradingMode;
  killSwitchActive: boolean;
  activeEvaluation: TradeProposalEvaluation | null;
  isProposingOrder?: boolean;
  onProposeOrder: (proposal: TradeProposalInput) => Promise<TradeProposalEvaluation | void>;
  onOpenAuthorizationModal: (evaluation: TradeProposalEvaluation) => void;
  meeting: AgentMeetingResult | null;
  isMeetingLoading: boolean;
  speech: SpeechEngineController;
  onConveneMeeting: (symbol: string) => Promise<void>;
  onProposeRecommendedTrade?: (proposal: TradeProposalInput) => Promise<void>;
  simulateVisualFault?: boolean;
}

export const LiveTerminalView: React.FC<LiveTerminalViewProps> = ({
  assets,
  selectedSymbol,
  onSelectSymbol,
  candlesData,
  timeframe,
  onTimeframeChange,
  isCandlesLoading = false,
  portfolio,
  tradingMode,
  killSwitchActive,
  activeEvaluation,
  isProposingOrder = false,
  onProposeOrder,
  onOpenAuthorizationModal,
  meeting,
  isMeetingLoading,
  speech,
  onConveneMeeting,
  onProposeRecommendedTrade,
  simulateVisualFault = false,
}) => {
  const { language } = useTheme();

  const selectedAsset = useMemo(
    () => assets.find((a) => a.symbol === selectedSymbol) || assets[0] || null,
    [assets, selectedSymbol]
  );

  const handleMeetingProposal = async (proposal: TradeProposalInput) => {
    if (onProposeRecommendedTrade) {
      await onProposeRecommendedTrade(proposal);
      return;
    }
    const evaluation = await onProposeOrder(proposal);
    if (evaluation) {
      onOpenAuthorizationModal(evaluation);
    }
  };

  const [assetSearch, setAssetSearch] = React.useState<string>('');
  const [analysisHorizon, setAnalysisHorizon] = React.useState<'HOURS' | 'DAYS' | 'WEEKS' | 'MONTHS'>('HOURS');

  const filteredAssets = useMemo(() => {
    const q = assetSearch.trim().toLowerCase();
    if (!q) return assets;
    return assets.filter(
      (a) =>
        a.symbol.toLowerCase().includes(q) ||
        a.nameAr.toLowerCase().includes(q) ||
        a.nameEn.toLowerCase().includes(q)
    );
  }, [assets, assetSearch]);

  const asksLadder = useMemo(
    () => [...(candlesData?.asks ?? []).slice(0, 5)].reverse(),
    [candlesData?.asks]
  );
  const bidsLadder = useMemo(
    () => (candlesData?.bids ?? []).slice(0, 5),
    [candlesData?.bids]
  );
  const maxDepthTotal = useMemo(() => {
    let m = 1;
    asksLadder.forEach((a) => {
      if (a.total > m) m = a.total;
    });
    bidsLadder.forEach((b) => {
      if (b.total > m) m = b.total;
    });
    return m;
  }, [asksLadder, bidsLadder]);

  const bestBid = bidsLadder[0]?.price ?? 0;
  const bestAsk = candlesData?.asks?.[0]?.price ?? 0;
  const spreadAbs = bestAsk > 0 && bestBid > 0 ? Math.max(0, bestAsk - bestBid) : 0;

  return (
    <div className="terminal-grid" data-testid="live-terminal-view">
      {/* العمود الأول: قائمة مراقبة الأسواق الحية والبحث وتصنيف TRADABLE_SPOT مقابل REFERENCE_ONLY */}
      <aside
        className="holo-panel terminal-watchlist-col"
        aria-label={language === 'ar' ? 'قائمة مراقبة الأصول الحية' : 'Live Market Watchlist'}
        style={{ padding: '0.9rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.4rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <Radio size={16} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <h2 style={{ margin: 0, fontSize: '0.94rem', fontWeight: 800 }}>
              {language === 'ar' ? 'مراقبة الأسواق الحية' : 'Market Watchlist'}
            </h2>
          </div>
          <span className="holo-badge tabular-nums">{filteredAssets.length}</span>
        </div>

        {/* بحث سريع في الأصول */}
        <input
          type="search"
          className="holo-input"
          style={{ minHeight: '36px', fontSize: '0.82rem' }}
          placeholder={language === 'ar' ? 'ابحث عن رمز أو أصل...' : 'Search symbol or asset...'}
          value={assetSearch}
          onChange={(e) => setAssetSearch(e.target.value)}
        />

        {/* الأفق الزمني للتحليل (Hours / Days / Weeks / Months — Section 6) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.25rem' }}>
          {(
            [
              { id: 'HOURS', ar: 'ساعات', en: 'Hours', tf: '15m' },
              { id: 'DAYS', ar: 'أيام', en: 'Days', tf: '1h' },
              { id: 'WEEKS', ar: 'أسابيع', en: 'Weeks', tf: '4h' },
              { id: 'MONTHS', ar: 'أشهر', en: 'Months', tf: '4h' },
            ] as const
          ).map((hz) => (
            <button
              key={hz.id}
              type="button"
              className={`holo-btn ${analysisHorizon === hz.id ? 'holo-btn-primary' : ''}`}
              style={{ minHeight: '30px', padding: '0.2rem 0.3rem', fontSize: '0.72rem' }}
              onClick={() => {
                setAnalysisHorizon(hz.id);
                onTimeframeChange(hz.tf);
              }}
            >
              {language === 'ar' ? hz.ar : hz.en}
            </button>
          ))}
        </div>

        <div
          role="listbox"
          aria-label={language === 'ar' ? 'الأصول المتاحة للتداول' : 'Tradable Market Assets'}
          style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}
        >
          {filteredAssets.map((asset) => {
            const isSelected = asset.symbol === selectedSymbol;
            const up = asset.change24hPct >= 0;
            const isSpotPair = asset.category === 'CRYPTO';
            const canonicalSpot = isSpotPair
              ? `${asset.symbol.split('-')[0]}USDT`
              : asset.symbol;
            return (
              <button
                key={asset.symbol}
                type="button"
                role="option"
                aria-selected={isSelected}
                data-testid={`watchlist-item-${asset.symbol}`}
                onClick={() => onSelectSymbol(asset.symbol)}
                className="holo-panel-subtle"
                style={{
                  width: '100%',
                  padding: '0.65rem 0.75rem',
                  textAlign: 'inherit',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.35rem',
                  borderColor: isSelected ? 'var(--accent-primary)' : 'var(--border-subtle)',
                  background: isSelected
                    ? 'rgba(var(--accent-primary-rgb), 0.12)'
                    : 'color-mix(in srgb, var(--bg-elevated) 82%, transparent)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.4rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
                      <strong style={{ fontSize: '0.9rem' }}>
                        {isSpotPair ? canonicalSpot : asset.symbol}
                      </strong>
                      <span
                        className={`holo-badge ${isSpotPair ? 'holo-badge-success' : 'holo-badge-warning'}`}
                        style={{ fontSize: '0.62rem', padding: '0.05rem 0.38rem' }}
                      >
                        {isSpotPair ? 'TRADABLE_SPOT' : 'REFERENCE_ONLY'}
                      </span>
                    </div>
                    <span
                      style={{
                        display: 'block',
                        fontSize: '0.73rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {language === 'ar' ? asset.nameAr : asset.nameEn}
                    </span>
                  </div>

                  <div style={{ textAlign: 'end' }}>
                    <div className="fin-value" style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                      {formatCurrency(asset.price)}
                    </div>
                    <span
                      className={`holo-badge tabular-nums ${
                        up ? 'holo-badge-success' : 'holo-badge-danger'
                      }`}
                      style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}
                    >
                      {up ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
                      {formatSignedPct(asset.change24hPct)}
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '0.7rem',
                    color: 'var(--text-muted)',
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '0.28rem',
                  }}
                >
                  <span className="tabular-nums">
                    Spread: {formatNumber(asset.spreadBps, 1)} bps
                  </span>
                  <span className="tabular-nums">
                    Volat: {formatNumber(asset.volatilityPct, 1)}%
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* العمود الأوسط: المخطط الهولوغرامي + قاعة اجتماع الوكلاء المدمجة مباشرة */}
      <div className="terminal-center-stack">
        <VisualEffectsBoundary
          language={language}
          widgetNameAr="مخطط الشموع الهولوغرامي"
          widgetNameEn="Holographic Candlestick Chart"
          simulateError={simulateVisualFault}
          fallbackSummary={
            selectedAsset ? (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.84rem',
                }}
              >
                <span>
                  {selectedAsset.symbol} ({language === 'ar' ? selectedAsset.nameAr : selectedAsset.nameEn})
                </span>
                <strong className="fin-value">{formatCurrency(selectedAsset.price)}</strong>
              </div>
            ) : null
          }
        >
          <HolographicCandlestickChart
            asset={selectedAsset}
            candlesData={candlesData}
            timeframe={timeframe}
            onTimeframeChange={onTimeframeChange}
            isLoading={isCandlesLoading}
          />
        </VisualEffectsBoundary>

        <AgentMeetingRoom
          meeting={meeting}
          isLoading={isMeetingLoading}
          selectedSymbol={selectedSymbol}
          speech={speech}
          onConveneMeeting={onConveneMeeting}
          onProposeRecommendedTrade={handleMeetingProposal}
        />
      </div>

      {/* العمود الجانبي: تذكرة التداول والمخاطر + دفتر الأوامر + كرة الثروة 3D */}
      <div className="terminal-side-stack">
        <OrderTicketAndRiskPanel
          selectedAsset={selectedAsset}
          portfolio={portfolio}
          tradingMode={tradingMode}
          killSwitchActive={killSwitchActive}
          activeEvaluation={activeEvaluation}
          isSubmitting={isProposingOrder}
          onProposeOrder={onProposeOrder}
          onOpenAuthorizationModal={onOpenAuthorizationModal}
        />

        {/* بطاقة عمق دفتر الأوامر التفصيلية (Bid / Ask Orderbook Ladder) */}
        <section
          className="holo-panel"
          aria-label={language === 'ar' ? 'عمق دفتر الأوامر' : 'Orderbook Depth'}
          style={{ padding: '0.95rem 1.05rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <BookOpen size={16} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 800 }}>
                {language === 'ar' ? 'دفتر الأوامر (Orderbook)' : 'Orderbook Depth'}
              </h3>
            </div>
            <span className="holo-badge tabular-nums">{selectedSymbol}</span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              fontSize: '0.72rem',
              color: 'var(--text-muted)',
              padding: '0 0.35rem',
            }}
          >
            <span>{language === 'ar' ? 'السعر (USD)' : 'Price (USD)'}</span>
            <span style={{ textAlign: 'end' }}>{language === 'ar' ? 'الحجم' : 'Size'}</span>
            <span style={{ textAlign: 'end' }}>{language === 'ar' ? 'التراكمي' : 'Total'}</span>
          </div>

          {/* عروض البيع Asks */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            {asksLadder.map((ask, idx) => {
              const widthPct = Math.min(100, (ask.total / maxDepthTotal) * 100);
              return (
                <div
                  key={`ladder-ask-${idx}`}
                  style={{
                    position: 'relative',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    padding: '0.2rem 0.4rem',
                    fontSize: '0.76rem',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    aria-hidden="true"
                    style={{
                      position: 'absolute',
                      insetBlock: 0,
                      insetInlineEnd: 0,
                      width: `${widthPct}%`,
                      background: 'var(--status-danger-bg)',
                      pointerEvents: 'none',
                    }}
                  />
                  <span
                    className="tabular-nums"
                    style={{ position: 'relative', color: 'var(--status-danger)', fontWeight: 600 }}
                  >
                    {formatCurrency(ask.price)}
                  </span>
                  <span
                    className="tabular-nums"
                    style={{ position: 'relative', textAlign: 'end', color: 'var(--text-secondary)' }}
                  >
                    {formatNumber(ask.size, 3)}
                  </span>
                  <span
                    className="tabular-nums"
                    style={{ position: 'relative', textAlign: 'end', color: 'var(--text-muted)' }}
                  >
                    {formatNumber(ask.total, 3)}
                  </span>
                </div>
              );
            })}
          </div>

          {/* الفارق السعري الوسطي Spread */}
          <div
            className="holo-panel-subtle"
            style={{
              padding: '0.35rem 0.6rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.76rem',
            }}
          >
            <span style={{ color: 'var(--text-muted)' }}>
              {language === 'ar' ? 'الفارق السعري (Spread):' : 'Mid Spread:'}
            </span>
            <strong className="tabular-nums" style={{ color: 'var(--accent-primary)' }}>
              {formatCurrency(spreadAbs)} ({formatNumber(selectedAsset?.spreadBps ?? 0, 1)} bps)
            </strong>
          </div>

          {/* طلبات الشراء Bids */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            {bidsLadder.map((bid, idx) => {
              const widthPct = Math.min(100, (bid.total / maxDepthTotal) * 100);
              return (
                <div
                  key={`ladder-bid-${idx}`}
                  style={{
                    position: 'relative',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    padding: '0.2rem 0.4rem',
                    fontSize: '0.76rem',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    aria-hidden="true"
                    style={{
                      position: 'absolute',
                      insetBlock: 0,
                      insetInlineEnd: 0,
                      width: `${widthPct}%`,
                      background: 'var(--status-success-bg)',
                      pointerEvents: 'none',
                    }}
                  />
                  <span
                    className="tabular-nums"
                    style={{ position: 'relative', color: 'var(--status-success)', fontWeight: 600 }}
                  >
                    {formatCurrency(bid.price)}
                  </span>
                  <span
                    className="tabular-nums"
                    style={{ position: 'relative', textAlign: 'end', color: 'var(--text-secondary)' }}
                  >
                    {formatNumber(bid.size, 3)}
                  </span>
                  <span
                    className="tabular-nums"
                    style={{ position: 'relative', textAlign: 'end', color: 'var(--text-muted)' }}
                  >
                    {formatNumber(bid.total, 3)}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* الكرة الهولوغرامية ثلاثية الأبعاد المحمية بـ VisualEffectsBoundary */}
        <VisualEffectsBoundary
          language={language}
          widgetNameAr="كرة الثروة الهولوغرامية 3D"
          widgetNameEn="Holographic Wealth Orb 3D"
          simulateError={simulateVisualFault}
        >
          <HolographicOrb3D portfolio={portfolio} assets={assets} />
        </VisualEffectsBoundary>
      </div>
    </div>
  );
};

export default LiveTerminalView;
