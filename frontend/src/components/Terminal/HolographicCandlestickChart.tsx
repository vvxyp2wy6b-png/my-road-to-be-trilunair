/**
 * مخطط الشموع اليابانية الهولوغرامي التفاعلي وعمق السعر (Holographic Candlestick Chart)
 * يعرض بيانات الشموع (OHLCV)، مستويات الدعم والمقاومة المتقطعة، مؤشر التقاطع التفاعلي (Crosshair)،
 * وشريط عمق أوامر الشراء والبيع في عناصر DOM مقروءة لضمان أقصى درجات الوضوح والوصولية.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowDownRight, ArrowUpRight, Crosshair, Layers } from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import { formatCurrency, formatNumber, formatSignedPct } from '../../i18n/translations';
import type { CandlePoint, MarketAsset, MarketCandlesResponse } from '../../types/trilunair';

export interface HolographicCandlestickChartProps {
  asset: MarketAsset | null;
  candlesData: MarketCandlesResponse | null;
  timeframe: string;
  onTimeframeChange: (timeframe: string) => void;
  isLoading?: boolean;
}

const TIMEFRAMES = ['5m', '15m', '1h', '4h'] as const;

interface ChartThemeColors {
  bgBase: string;
  bgElevated: string;
  bgSurface: string;
  accentPrimary: string;
  accentSecondary: string;
  accentTertiary: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  borderSubtle: string;
  success: string;
  danger: string;
  warning: string;
  glowIntensity: number;
}

function getDocCssVar(varName: string, systemFallback: string): string {
  if (typeof document === 'undefined') return systemFallback;
  const root = document.documentElement;
  const computed =
    typeof window !== 'undefined' && typeof window.getComputedStyle === 'function'
      ? window.getComputedStyle(root).getPropertyValue(varName).trim()
      : '';
  const inline = root.style.getPropertyValue(varName).trim();
  return computed || inline || systemFallback;
}

function readChartColors(): ChartThemeColors {
  const glowRaw = parseFloat(getDocCssVar('--fx-glow-intensity', '0.5'));
  return {
    bgBase: getDocCssVar('--bg-base', 'Canvas'),
    bgElevated: getDocCssVar('--bg-elevated', 'Canvas'),
    bgSurface: getDocCssVar('--bg-surface', 'Canvas'),
    accentPrimary: getDocCssVar('--accent-primary', 'Highlight'),
    accentSecondary: getDocCssVar('--accent-secondary', 'Highlight'),
    accentTertiary: getDocCssVar('--accent-tertiary', 'LinkText'),
    textPrimary: getDocCssVar('--text-primary', 'CanvasText'),
    textSecondary: getDocCssVar('--text-secondary', 'CanvasText'),
    textMuted: getDocCssVar('--text-muted', 'GrayText'),
    borderSubtle: getDocCssVar('--border-subtle', 'GrayText'),
    success: getDocCssVar('--status-success', 'Highlight'),
    danger: getDocCssVar('--status-danger', 'Mark'),
    warning: getDocCssVar('--status-warning', 'Highlight'),
    glowIntensity: Number.isFinite(glowRaw) ? Math.max(0, Math.min(1, glowRaw)) : 0.5,
  };
}

function formatCandleTimestamp(ts: number): string {
  if (!Number.isFinite(ts)) return '--:--';
  const ms = ts < 10_000_000_000 ? ts * 1000 : ts;
  const date = new Date(ms);
  return date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
    day: '2-digit',
  });
}

export const HolographicCandlestickChart: React.FC<HolographicCandlestickChartProps> = ({
  asset,
  candlesData,
  timeframe,
  onTimeframeChange,
  isLoading = false,
}) => {
  const { language, activeState, effectiveTokens, currentTheme } = useTheme();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [resizeCount, setResizeCount] = useState<number>(0);

  const candles = useMemo<CandlePoint[]>(
    () => candlesData?.candles ?? [],
    [candlesData]
  );

  // الشمعة المعروضة حالياً في شريط القراءة العلوية (إما الشمعة تحت المؤشر أو آخر شمعة حية)
  const inspectedCandle: CandlePoint | null = useMemo(() => {
    if (candles.length === 0) return null;
    if (hoveredIndex !== null && hoveredIndex >= 0 && hoveredIndex < candles.length) {
      return candles[hoveredIndex];
    }
    return candles[candles.length - 1];
  }, [candles, hoveredIndex]);

  // مراقبة تغير أبعاد الحاوية لإعادة رسم فائقة الحدة
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(() => {
      setResizeCount((n) => n + 1);
    });
    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  const supportLevel = candlesData?.supportLevel;
  const resistanceLevel = candlesData?.resistanceLevel;
  const assetPrice = asset?.price;
  const lowPowerMode = activeState.modifiers.lowPowerMode;
  const highContrast = activeState.modifiers.highContrast;

  const drawChart = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = typeof window !== 'undefined' ? Math.min(window.devicePixelRatio || 1, 2) : 1;
    const width = canvas.clientWidth || 760;
    const height = canvas.clientHeight || 330;
    const targetW = Math.max(1, Math.round(width * dpr));
    const targetH = Math.max(1, Math.round(height * dpr));

    if (canvas.width !== targetW || canvas.height !== targetH) {
      canvas.width = targetW;
      canvas.height = targetH;
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const colors = readChartColors();
    const padLeft = 14;
    const padRight = 76;
    const padTop = 16;
    const padBottom = 26;
    const plotW = Math.max(80, width - padLeft - padRight);
    const plotH = Math.max(100, height - padTop - padBottom);
    const priceAreaH = plotH * 0.77;
    const volAreaTop = padTop + plotH * 0.82;
    const volAreaH = plotH * 0.18;

    if (candles.length === 0) {
      ctx.fillStyle = colors.textMuted;
      ctx.font = '600 13px "IBM Plex Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(
        language === 'ar' ? 'جاري مزامنة بيانات الشموع الحية...' : 'Synchronizing live market candles...',
        width / 2,
        height / 2
      );
      ctx.restore();
      return;
    }

    let minPrice = Infinity;
    let maxPrice = -Infinity;
    let maxVol = 1;

    candles.forEach((c) => {
      if (c.low < minPrice) minPrice = c.low;
      if (c.high > maxPrice) maxPrice = c.high;
      if (c.volume > maxVol) maxVol = c.volume;
    });

    if (supportLevel) {
      minPrice = Math.min(minPrice, supportLevel);
    }
    if (resistanceLevel) {
      maxPrice = Math.max(maxPrice, resistanceLevel);
    }

    const priceRange = Math.max(maxPrice - minPrice, maxPrice * 0.004, 0.0001);
    const paddedMin = minPrice - priceRange * 0.08;
    const paddedMax = maxPrice + priceRange * 0.08;
    const effectiveSpan = paddedMax - paddedMin;

    const priceToY = (p: number) =>
      padTop + priceAreaH - ((p - paddedMin) / effectiveSpan) * priceAreaH;

    // شبكة الأسعار الأفقية
    const gridRows = 5;
    ctx.font = '500 10.5px "IBM Plex Mono", monospace';
    ctx.textAlign = 'left';

    for (let r = 0; r <= gridRows; r += 1) {
      const ratio = r / gridRows;
      const y = Math.round(padTop + priceAreaH * ratio) + 0.5;
      const gridPrice = paddedMax - ratio * effectiveSpan;

      ctx.save();
      ctx.strokeStyle = colors.borderSubtle;
      ctx.globalAlpha = 0.45;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(padLeft + plotW, y);
      ctx.stroke();
      ctx.restore();

      ctx.fillStyle = colors.textMuted;
      ctx.fillText(
        gridPrice >= 100 ? gridPrice.toFixed(2) : gridPrice.toFixed(4),
        padLeft + plotW + 6,
        y + 3
      );
    }

    // خط فاصل لمنطقة الأحجام (Volume)
    ctx.save();
    ctx.strokeStyle = colors.borderSubtle;
    ctx.globalAlpha = 0.55;
    ctx.beginPath();
    ctx.moveTo(padLeft, Math.round(volAreaTop - 4) + 0.5);
    ctx.lineTo(padLeft + plotW, Math.round(volAreaTop - 4) + 0.5);
    ctx.stroke();
    ctx.restore();

    // رسم خطي الدعم (Support) والمقاومة (Resistance) المتقطعين
    if (supportLevel) {
      const sy = priceToY(supportLevel);
      ctx.save();
      ctx.strokeStyle = colors.success;
      ctx.globalAlpha = 0.82;
      ctx.lineWidth = 1.25;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(padLeft, sy);
      ctx.lineTo(padLeft + plotW, sy);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = '700 10px "IBM Plex Mono", monospace';
      ctx.fillStyle = colors.success;
      ctx.fillText(
        `SUP ${supportLevel >= 100 ? supportLevel.toFixed(2) : supportLevel.toFixed(4)}`,
        padLeft + 6,
        sy - 5
      );
      ctx.restore();
    }

    if (resistanceLevel) {
      const ry = priceToY(resistanceLevel);
      ctx.save();
      ctx.strokeStyle = colors.warning;
      ctx.globalAlpha = 0.85;
      ctx.lineWidth = 1.25;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(padLeft, ry);
      ctx.lineTo(padLeft + plotW, ry);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = '700 10px "IBM Plex Mono", monospace';
      ctx.fillStyle = colors.warning;
      ctx.fillText(
        `RES ${resistanceLevel >= 100 ? resistanceLevel.toFixed(2) : resistanceLevel.toFixed(4)}`,
        padLeft + 6,
        ry + 12
      );
      ctx.restore();
    }

    // رسم الشموع اليابانية وأعمدة الحجم
    const stepX = plotW / candles.length;
    const bodyWidth = Math.max(2.5, Math.min(13, stepX * 0.68));

    candles.forEach((candle, idx) => {
      const cx = padLeft + idx * stepX + stepX / 2;
      const openY = priceToY(candle.open);
      const closeY = priceToY(candle.close);
      const highY = priceToY(candle.high);
      const lowY = priceToY(candle.low);
      const isBull = candle.close >= candle.open;
      const candleColor = isBull ? colors.success : colors.danger;

      // الفتيل العلوي والسفلي (Wick)
      ctx.save();
      ctx.strokeStyle = candleColor;
      ctx.lineWidth = 1.25;
      ctx.beginPath();
      ctx.moveTo(cx, highY);
      ctx.lineTo(cx, lowY);
      ctx.stroke();

      // جسم الشمعة (Candle Body)
      const topBody = Math.min(openY, closeY);
      const bodyH = Math.max(1.8, Math.abs(closeY - openY));
      ctx.fillStyle = candleColor;
      ctx.fillRect(cx - bodyWidth / 2, topBody, bodyWidth, bodyH);
      ctx.restore();

      // عمود الحجم السفلي (Volume Bar)
      const vBarH = Math.max(2, (candle.volume / maxVol) * volAreaH);
      ctx.save();
      ctx.fillStyle = candleColor;
      ctx.globalAlpha = hoveredIndex === idx ? 0.85 : 0.35;
      ctx.fillRect(cx - bodyWidth / 2, volAreaTop + volAreaH - vBarH, bodyWidth, vBarH);
      ctx.restore();
    });

    // خط السعر الأخير مع توهج هولوغرامي خفيف لا يحجب الأرقام أبداً
    const lastCandle = candles[candles.length - 1];
    const livePrice = assetPrice ?? lastCandle.close;
    const liveY = priceToY(livePrice);

    ctx.save();
    if (!lowPowerMode && !highContrast && colors.glowIntensity > 0.05) {
      ctx.shadowColor = colors.accentPrimary;
      ctx.shadowBlur = 10 * colors.glowIntensity;
    }
    ctx.strokeStyle = colors.accentPrimary;
    ctx.lineWidth = 1.2;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(padLeft, liveY);
    ctx.lineTo(padLeft + plotW, liveY);
    ctx.stroke();
    ctx.restore();

    // شارة السعر الحي على المحور الأيمن
    ctx.save();
    const tagH = 18;
    const tagY = Math.max(padTop, Math.min(padTop + priceAreaH - tagH, liveY - tagH / 2));
    ctx.fillStyle = colors.accentPrimary;
    ctx.fillRect(padLeft + plotW + 2, tagY, padRight - 4, tagH);
    ctx.fillStyle = colors.bgBase;
    ctx.font = '700 10.5px "IBM Plex Mono", monospace';
    ctx.fillText(
      livePrice >= 100 ? livePrice.toFixed(2) : livePrice.toFixed(4),
      padLeft + plotW + 6,
      tagY + 12.5
    );
    ctx.restore();

    // طوابع الوقت على المحور السفلي
    const timeLabelCount = 4;
    ctx.save();
    ctx.fillStyle = colors.textMuted;
    ctx.font = '500 10px "IBM Plex Mono", monospace';
    ctx.textAlign = 'center';
    for (let tIdx = 0; tIdx < timeLabelCount; tIdx += 1) {
      const cIndex = Math.min(
        candles.length - 1,
        Math.round((tIdx / (timeLabelCount - 1)) * (candles.length - 1))
      );
      const tx = padLeft + cIndex * stepX + stepX / 2;
      const d = new Date(
        candles[cIndex].timestamp < 10_000_000_000
          ? candles[cIndex].timestamp * 1000
          : candles[cIndex].timestamp
      );
      const hhmm = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
      ctx.fillText(hhmm, tx, height - 7);
    }
    ctx.restore();

    // مؤشر التقاطع التفاعلي (Interactive Crosshair) عند التمرير بالماوس أو اللمس أو الأسهم
    if (hoveredIndex !== null && hoveredIndex >= 0 && hoveredIndex < candles.length) {
      const hc = candles[hoveredIndex];
      const hx = padLeft + hoveredIndex * stepX + stepX / 2;
      const hy = priceToY(hc.close);

      ctx.save();
      ctx.strokeStyle = colors.accentSecondary;
      ctx.globalAlpha = 0.78;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);

      // خط عمودي
      ctx.beginPath();
      ctx.moveTo(hx, padTop);
      ctx.lineTo(hx, volAreaTop + volAreaH);
      ctx.stroke();

      // خط أفقي
      ctx.beginPath();
      ctx.moveTo(padLeft, hy);
      ctx.lineTo(padLeft + plotW, hy);
      ctx.stroke();

      ctx.setLineDash([]);
      ctx.fillStyle = colors.accentPrimary;
      ctx.beginPath();
      ctx.arc(hx, hy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    ctx.restore();
  }, [
    candles,
    supportLevel,
    resistanceLevel,
    assetPrice,
    hoveredIndex,
    language,
    lowPowerMode,
    highContrast,
  ]);

  useEffect(() => {
    drawChart();
  }, [
    drawChart,
    effectiveTokens,
    currentTheme.id,
    activeState.modifiers.glowIntensity,
    resizeCount,
  ]);

  const updateHoverFromClientX = (clientX: number) => {
    const canvas = canvasRef.current;
    if (!canvas || candles.length === 0) return;
    const rect = canvas.getBoundingClientRect();
    const padLeft = 14;
    const padRight = 76;
    const plotW = Math.max(80, rect.width - padLeft - padRight);
    const relX = clientX - rect.left - padLeft;
    const idx = Math.floor((relX / plotW) * candles.length);
    const clamped = Math.max(0, Math.min(candles.length - 1, idx));
    setHoveredIndex(clamped);
  };

  const handleChartKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (candles.length === 0) return;
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setHoveredIndex((prev) =>
        prev === null ? candles.length - 1 : Math.max(0, prev - 1)
      );
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      setHoveredIndex((prev) =>
        prev === null ? candles.length - 1 : Math.min(candles.length - 1, prev + 1)
      );
    } else if (e.key === 'Escape') {
      setHoveredIndex(null);
    }
  };

  const topBids = useMemo(() => (candlesData?.bids ?? []).slice(0, 4), [candlesData?.bids]);
  const topAsks = useMemo(() => (candlesData?.asks ?? []).slice(0, 4), [candlesData?.asks]);
  const maxBookTotal = useMemo(() => {
    let m = 1;
    topBids.forEach((b) => {
      if (b.total > m) m = b.total;
    });
    topAsks.forEach((a) => {
      if (a.total > m) m = a.total;
    });
    return m;
  }, [topBids, topAsks]);

  const symbol = asset?.symbol || candlesData?.symbol || 'BTC';
  const livePrice = asset?.price ?? inspectedCandle?.close ?? 0;
  const change24h = asset?.change24hPct ?? 0;
  const isPositive = change24h >= 0;

  return (
    <section
      className="holo-panel"
      aria-label={
        language === 'ar'
          ? `المخطط المالي الهولوغرامي للأصل ${symbol}`
          : `Holographic Candlestick Chart for ${symbol}`
      }
      style={{ padding: '1rem 1.15rem', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}
    >
      {/* الرأس العلوي: السعر الحي، التغير اليومي، وأزرار الإطار الزمني */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <Activity size={18} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
              <h2 style={{ margin: 0, fontSize: '1.12rem', fontWeight: 800 }}>
                {symbol}{' '}
                <span style={{ fontSize: '0.84rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
                  {asset ? (language === 'ar' ? asset.nameAr : asset.nameEn) : ''}
                </span>
              </h2>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'baseline',
                gap: '0.6rem',
                marginTop: '0.15rem',
              }}
            >
              <span
                data-testid="chart-live-price"
                className="fin-value"
                style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-primary)' }}
              >
                {formatCurrency(livePrice)}
              </span>
              <span
                className={`holo-badge tabular-nums ${
                  isPositive ? 'holo-badge-success' : 'holo-badge-danger'
                }`}
              >
                {isPositive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
                {formatSignedPct(change24h)}
              </span>
            </div>
          </div>

          {asset && (
            <div
              style={{
                display: 'flex',
                gap: '0.9rem',
                flexWrap: 'wrap',
                fontSize: '0.77rem',
                color: 'var(--text-secondary)',
              }}
            >
              <div>
                <span style={{ color: 'var(--text-muted)' }}>
                  {language === 'ar' ? 'أعلى 24س: ' : '24h High: '}
                </span>
                <strong className="tabular-nums">{formatCurrency(asset.high24h)}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>
                  {language === 'ar' ? 'أدنى 24س: ' : '24h Low: '}
                </span>
                <strong className="tabular-nums">{formatCurrency(asset.low24h)}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>
                  {language === 'ar' ? 'حجم 24س: ' : '24h Vol: '}
                </span>
                <strong className="tabular-nums">{formatCurrency(asset.volume24hUsd, true)}</strong>
              </div>
            </div>
          )}
        </div>

        {/* محدد الإطار الزمني (5m, 15m, 1h, 4h) */}
        <div
          role="group"
          aria-label={language === 'ar' ? 'اختيار الإطار الزمني' : 'Select chart timeframe'}
          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
        >
          {TIMEFRAMES.map((tf) => {
            const active = timeframe === tf;
            return (
              <button
                key={tf}
                type="button"
                aria-pressed={active}
                onClick={() => onTimeframeChange(tf)}
                className={`holo-btn tabular-nums ${active ? 'holo-btn-primary' : ''}`}
                style={{ minHeight: '34px', padding: '0.25rem 0.68rem', fontSize: '0.8rem' }}
              >
                {tf}
              </button>
            );
          })}
        </div>
      </div>

      {/* شريط قراءات مؤشر التقاطع (Crosshair OHLCV HUD) بأرقام جدولية واضحة */}
      <div
        className="holo-panel-subtle"
        data-testid="chart-ohlcv-readout"
        style={{
          padding: '0.45rem 0.75rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.55rem 1rem',
          fontSize: '0.78rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-primary)' }}>
          <Crosshair size={14} aria-hidden="true" />
          <span className="tabular-nums">
            {inspectedCandle ? formatCandleTimestamp(inspectedCandle.timestamp) : '--:--'}
          </span>
          {isLoading && (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.73rem' }}>
              ({language === 'ar' ? 'تحديث...' : 'Updating...'})
            </span>
          )}
        </div>

        {inspectedCandle ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            <span>
              <span style={{ color: 'var(--text-muted)' }}>O: </span>
              <strong className="tabular-nums">{formatCurrency(inspectedCandle.open)}</strong>
            </span>
            <span>
              <span style={{ color: 'var(--text-muted)' }}>H: </span>
              <strong className="tabular-nums" style={{ color: 'var(--status-success)' }}>
                {formatCurrency(inspectedCandle.high)}
              </strong>
            </span>
            <span>
              <span style={{ color: 'var(--text-muted)' }}>L: </span>
              <strong className="tabular-nums" style={{ color: 'var(--status-danger)' }}>
                {formatCurrency(inspectedCandle.low)}
              </strong>
            </span>
            <span>
              <span style={{ color: 'var(--text-muted)' }}>C: </span>
              <strong className="tabular-nums">{formatCurrency(inspectedCandle.close)}</strong>
            </span>
            <span>
              <span style={{ color: 'var(--text-muted)' }}>Vol: </span>
              <strong className="tabular-nums">{formatNumber(inspectedCandle.volume, 2)}</strong>
            </span>
          </div>
        ) : (
          <span style={{ color: 'var(--text-muted)' }}>
            {language === 'ar' ? 'لا توجد شموع متاحة بعد' : 'No candle points loaded'}
          </span>
        )}
      </div>

      {/* لوحة رسم الشموع اليابانية التفاعلية */}
      <div
        tabIndex={0}
        role="img"
        aria-label={
          language === 'ar'
            ? `مخطط الشموع اليابانية للأصل ${symbol} بالإطار الزمني ${timeframe}`
            : `Candlestick chart for ${symbol} (${timeframe})`
        }
        onKeyDown={handleChartKeyDown}
        onMouseMove={(e) => updateHoverFromClientX(e.clientX)}
        onMouseLeave={() => setHoveredIndex(null)}
        onTouchStart={(e) => {
          const t = e.touches[0];
          if (t) updateHoverFromClientX(t.clientX);
        }}
        onTouchMove={(e) => {
          const t = e.touches[0];
          if (t) updateHoverFromClientX(t.clientX);
        }}
        onTouchEnd={() => setHoveredIndex(null)}
        className="holo-panel-subtle"
        style={{
          height: '320px',
          width: '100%',
          position: 'relative',
          cursor: 'crosshair',
          overflow: 'hidden',
        }}
      >
        <canvas
          ref={canvasRef}
          data-testid="candlestick-canvas"
          style={{ width: '100%', height: '100%', display: 'block' }}
        />
      </div>

      {/* شريط DOM المدمج للدعم والمقاومة وعمق دفتر الأوامر (يضمن قراءة البيانات حتى بدون Canvas) */}
      <div
        className="holo-panel-subtle"
        style={{
          padding: '0.65rem 0.8rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.55rem',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.5rem',
            fontSize: '0.78rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Layers size={14} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
            <strong>
              {language === 'ar'
                ? 'مستويات الدعم والمقاومة وعمق السيولة الفوري'
                : 'Support / Resistance & Instant Liquidity Depth'}
            </strong>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
            <span className="holo-badge holo-badge-success tabular-nums">
              {language === 'ar' ? 'دعم: ' : 'Support: '}
              {candlesData ? formatCurrency(candlesData.supportLevel) : '--'}
            </span>
            <span className="holo-badge holo-badge-warning tabular-nums">
              {language === 'ar' ? 'مقاومة: ' : 'Resistance: '}
              {candlesData ? formatCurrency(candlesData.resistanceLevel) : '--'}
            </span>
          </div>
        </div>

        {(topBids.length > 0 || topAsks.length > 0) && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
              gap: '0.65rem',
            }}
          >
            {/* عروض الشراء (Bids) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <div
                style={{
                  fontSize: '0.72rem',
                  color: 'var(--status-success)',
                  fontWeight: 700,
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>{language === 'ar' ? 'أفضل طلبات الشراء (Bids)' : 'Top Bids'}</span>
                <span>{language === 'ar' ? 'الكمية' : 'Size'}</span>
              </div>
              {topBids.map((bid, idx) => {
                const pct = Math.min(100, (bid.total / maxBookTotal) * 100);
                return (
                  <div
                    key={`bid-${idx}`}
                    style={{
                      position: 'relative',
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0.18rem 0.45rem',
                      fontSize: '0.75rem',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      aria-hidden="true"
                      style={{
                        position: 'absolute',
                        insetBlock: 0,
                        insetInlineStart: 0,
                        width: `${pct}%`,
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
                    <span className="tabular-nums" style={{ position: 'relative', color: 'var(--text-secondary)' }}>
                      {formatNumber(bid.size, 3)}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* عروض البيع (Asks) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <div
                style={{
                  fontSize: '0.72rem',
                  color: 'var(--status-danger)',
                  fontWeight: 700,
                  display: 'flex',
                  justifyContent: 'space-between',
                }}
              >
                <span>{language === 'ar' ? 'أفضل عروض البيع (Asks)' : 'Top Asks'}</span>
                <span>{language === 'ar' ? 'الكمية' : 'Size'}</span>
              </div>
              {topAsks.map((ask, idx) => {
                const pct = Math.min(100, (ask.total / maxBookTotal) * 100);
                return (
                  <div
                    key={`ask-${idx}`}
                    style={{
                      position: 'relative',
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0.18rem 0.45rem',
                      fontSize: '0.75rem',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      aria-hidden="true"
                      style={{
                        position: 'absolute',
                        insetBlock: 0,
                        insetInlineStart: 0,
                        width: `${pct}%`,
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
                    <span className="tabular-nums" style={{ position: 'relative', color: 'var(--text-secondary)' }}>
                      {formatNumber(ask.size, 3)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default HolographicCandlestickChart;
