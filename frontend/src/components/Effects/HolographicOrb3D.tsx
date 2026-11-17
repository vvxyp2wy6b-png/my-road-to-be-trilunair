/**
 * الكرة الهولوغرامية ثلاثية الأبعاد لتوزيع الثروة ومسار التريليون (Holographic Wealth Orb 3D)
 * مبنية بالكامل بحسابات الإسقاط المنظوري ثلاثي الأبعاد على عنصر HTML5 Canvas خفيف الوزن
 * دون أي مكتبات 3D خارجية ثقيلة، مع احترام كامل لوضع الطاقة المنخفضة وتعطيل الحركة.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Orbit, RotateCcw, Sparkles } from 'lucide-react';
import { useTheme } from '../../theme/ThemeContext';
import { formatCurrency, formatNumber } from '../../i18n/translations';
import type { MarketAsset, PortfolioSnapshot } from '../../types/trilunair';

export interface HolographicOrb3DProps {
  portfolio: PortfolioSnapshot | null;
  assets?: MarketAsset[];
}

interface OrbAllocationNode {
  symbol: string;
  weightPct: number;
  valueUsd: number;
  latRad: number;
  lonRad: number;
  isCash?: boolean;
}

interface CanvasPalette {
  bgElevated: string;
  bgSurface: string;
  accentPrimary: string;
  accentSecondary: string;
  accentTertiary: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  success: string;
  glowIntensity: number;
}

function readCssVar(name: string, fallbackKeyword: string): string {
  if (typeof document === 'undefined') return fallbackKeyword;
  const root = document.documentElement;
  const computed =
    typeof window !== 'undefined' && typeof window.getComputedStyle === 'function'
      ? window.getComputedStyle(root).getPropertyValue(name).trim()
      : '';
  const inline = root.style.getPropertyValue(name).trim();
  return computed || inline || fallbackKeyword;
}

function readCanvasPalette(): CanvasPalette {
  const rawGlow = parseFloat(readCssVar('--fx-glow-intensity', '0.5'));
  return {
    bgElevated: readCssVar('--bg-elevated', 'Canvas'),
    bgSurface: readCssVar('--bg-surface', 'Canvas'),
    accentPrimary: readCssVar('--accent-primary', 'Highlight'),
    accentSecondary: readCssVar('--accent-secondary', 'Highlight'),
    accentTertiary: readCssVar('--accent-tertiary', 'LinkText'),
    textPrimary: readCssVar('--text-primary', 'CanvasText'),
    textSecondary: readCssVar('--text-secondary', 'CanvasText'),
    textMuted: readCssVar('--text-muted', 'GrayText'),
    success: readCssVar('--status-success', 'Highlight'),
    glowIntensity: Number.isFinite(rawGlow) ? Math.max(0, Math.min(1, rawGlow)) : 0.5,
  };
}

interface Point3D {
  x: number;
  y: number;
  z: number;
}

function rotatePoint3D(pt: Point3D, rotX: number, rotY: number): Point3D {
  // دوران حول المحور Y ثم المحور X
  const cosY = Math.cos(rotY);
  const sinY = Math.sin(rotY);
  const x1 = pt.x * cosY + pt.z * sinY;
  const z1 = -pt.x * sinY + pt.z * cosY;

  const cosX = Math.cos(rotX);
  const sinX = Math.sin(rotX);
  const y2 = pt.y * cosX - z1 * sinX;
  const z2 = pt.y * sinX + z1 * cosX;

  return { x: x1, y: y2, z: z2 };
}

export const HolographicOrb3D: React.FC<HolographicOrb3DProps> = ({ portfolio, assets }) => {
  const { language, activeState, effectiveTokens, currentTheme } = useTheme();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rotationRef = useRef<{ rx: number; ry: number }>({ rx: 0.32, ry: 0.65 });
  const dragRef = useRef<{ active: boolean; lastX: number; lastY: number }>({
    active: false,
    lastX: 0,
    lastY: 0,
  });
  const rafRef = useRef<number | null>(null);
  const [manualTick, setManualTick] = useState<number>(0);

  const isStaticMode =
    activeState.modifiers.lowPowerMode ||
    activeState.modifiers.motionDisabled ||
    activeState.modifiers.animationIntensity === 0;

  // توليد عقد توزيع المحفظة الحية على سطح الكرة
  const allocationNodes = useMemo<OrbAllocationNode[]>(() => {
    if (portfolio && portfolio.totalEquity > 0) {
      const items: OrbAllocationNode[] = [];
      const positions = portfolio.positions.slice(0, 6);
      const cashPct = Math.max(0, (portfolio.cashBalance / portfolio.totalEquity) * 100);

      positions.forEach((pos, idx) => {
        const goldenAngle = idx * 2.39996;
        const lat = ((idx + 0.5) / Math.max(1, positions.length + 1) - 0.5) * 1.65;
        items.push({
          symbol: pos.symbol,
          weightPct: pos.weightPct,
          valueUsd: pos.marketValueUsd,
          latRad: lat,
          lonRad: goldenAngle,
        });
      });

      items.push({
        symbol: 'CASH',
        weightPct: cashPct,
        valueUsd: portfolio.cashBalance,
        latRad: 0.18,
        lonRad: 4.15,
        isCash: true,
      });
      return items;
    }

    // عقد افتراضية متوازنة أثناء تحميل البيانات
    const fallbackSymbols =
      assets && assets.length > 0
        ? assets.slice(0, 4).map((a) => a.symbol)
        : ['BTC', 'NVDA', 'ETH', 'XAU'];
    const baseNodes: OrbAllocationNode[] = fallbackSymbols.map((sym, idx) => ({
      symbol: sym,
      weightPct: 16,
      valueUsd: 160_000,
      latRad: (idx - 1.5) * 0.42,
      lonRad: idx * 1.57,
    }));
    baseNodes.push({
      symbol: 'CASH',
      weightPct: 36,
      valueUsd: 360_000,
      latRad: 0.12,
      lonRad: 3.9,
      isCash: true,
    });
    return baseNodes;
  }, [portfolio, assets]);

  // نقاط الشبكة النجمية على سطح الكرة (Fibonacci Sphere)
  const surfaceParticles = useMemo<Point3D[]>(() => {
    const count = isStaticMode ? 44 : 76;
    const pts: Point3D[] = [];
    const goldenRatio = (1 + Math.sqrt(5)) / 2;
    for (let i = 0; i < count; i += 1) {
      const theta = (2 * Math.PI * i) / goldenRatio;
      const phi = Math.acos(1 - (2 * (i + 0.5)) / count);
      pts.push({
        x: Math.cos(theta) * Math.sin(phi),
        y: Math.cos(phi),
        z: Math.sin(theta) * Math.sin(phi),
      });
    }
    return pts;
  }, [isStaticMode]);

  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = typeof window !== 'undefined' ? Math.min(window.devicePixelRatio || 1, 2) : 1;
    const cssWidth = canvas.clientWidth || 320;
    const cssHeight = canvas.clientHeight || 230;
    const targetW = Math.max(1, Math.round(cssWidth * dpr));
    const targetH = Math.max(1, Math.round(cssHeight * dpr));

    if (canvas.width !== targetW || canvas.height !== targetH) {
      canvas.width = targetW;
      canvas.height = targetH;
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, cssWidth, cssHeight);

    const palette = readCanvasPalette();
    const cx = cssWidth / 2;
    const cy = cssHeight / 2 + 2;
    const radius = Math.min(cssWidth, cssHeight) * 0.34;
    const fov = 320;
    const { rx, ry } = rotationRef.current;

    const project = (pt: Point3D, scaleRadius: number) => {
      const rotated = rotatePoint3D(
        { x: pt.x * scaleRadius, y: pt.y * scaleRadius, z: pt.z * scaleRadius },
        rx,
        ry
      );
      const perspective = fov / (fov + rotated.z + scaleRadius * 0.4);
      return {
        sx: cx + rotated.x * perspective,
        sy: cy + rotated.y * perspective,
        z: rotated.z,
        perspective,
      };
    };

    // هالة خلفية ناعمة تحترم شدة التوهج ووضع الطاقة المنخفضة
    if (!isStaticMode && palette.glowIntensity > 0.05) {
      ctx.save();
      ctx.globalAlpha = Math.min(0.22, palette.glowIntensity * 0.26);
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 1.24, 0, Math.PI * 2);
      ctx.fillStyle = palette.accentPrimary;
      ctx.fill();
      ctx.restore();
    }

    // رسم خطوط الطول والعرض السلكية (Wireframe Meridians & Parallels)
    ctx.lineWidth = 1;
    const latitudes = [-0.55, 0, 0.55];
    latitudes.forEach((lat) => {
      const rLat = Math.cos(lat * Math.PI * 0.5);
      const yLat = Math.sin(lat * Math.PI * 0.5);
      ctx.save();
      ctx.strokeStyle = palette.accentPrimary;
      ctx.globalAlpha = lat === 0 ? 0.38 : 0.2;
      ctx.beginPath();
      const steps = 36;
      for (let s = 0; s <= steps; s += 1) {
        const angle = (s / steps) * Math.PI * 2;
        const proj = project(
          { x: Math.cos(angle) * rLat, y: yLat, z: Math.sin(angle) * rLat },
          radius
        );
        if (s === 0) ctx.moveTo(proj.sx, proj.sy);
        else ctx.lineTo(proj.sx, proj.sy);
      }
      ctx.stroke();
      ctx.restore();
    });

    for (let m = 0; m < 3; m += 1) {
      const lonOffset = (m * Math.PI) / 3;
      ctx.save();
      ctx.strokeStyle = palette.accentTertiary;
      ctx.globalAlpha = 0.2;
      ctx.beginPath();
      const steps = 36;
      for (let s = 0; s <= steps; s += 1) {
        const angle = (s / steps) * Math.PI * 2;
        const proj = project(
          {
            x: Math.sin(angle) * Math.cos(lonOffset),
            y: Math.cos(angle),
            z: Math.sin(angle) * Math.sin(lonOffset),
          },
          radius
        );
        if (s === 0) ctx.moveTo(proj.sx, proj.sy);
        else ctx.lineTo(proj.sx, proj.sy);
      }
      ctx.stroke();
      ctx.restore();
    }

    // حلقة مسار التريليون دولار ($1T Trajectory Orbital Ring)
    const ringRadius = radius * 1.32;
    ctx.save();
    ctx.strokeStyle = palette.accentSecondary;
    ctx.globalAlpha = 0.62;
    ctx.lineWidth = 1.4;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    const ringSteps = 48;
    for (let s = 0; s <= ringSteps; s += 1) {
      const a = (s / ringSteps) * Math.PI * 2;
      const tilted: Point3D = {
        x: Math.cos(a),
        y: Math.sin(a) * 0.28,
        z: Math.sin(a) * 0.96,
      };
      const proj = project(tilted, ringRadius);
      if (s === 0) ctx.moveTo(proj.sx, proj.sy);
      else ctx.lineTo(proj.sx, proj.sy);
    }
    ctx.stroke();
    ctx.restore();

    // شارة هدف $1T على المدار
    const targetBadgeProj = project({ x: 1, y: -0.18, z: 0.15 }, ringRadius);
    ctx.save();
    ctx.font = '700 10px "IBM Plex Mono", monospace';
    ctx.fillStyle = palette.accentSecondary;
    ctx.globalAlpha = 0.95;
    ctx.fillText('$1T ORBIT', targetBadgeProj.sx - 24, targetBadgeProj.sy - 6);
    ctx.restore();

    // رسم الجسيمات السطحية
    surfaceParticles.forEach((pt) => {
      const proj = project(pt, radius);
      const depthAlpha = proj.z < 0 ? 0.58 : 0.18;
      ctx.save();
      ctx.fillStyle = palette.accentPrimary;
      ctx.globalAlpha = depthAlpha;
      ctx.beginPath();
      ctx.arc(proj.sx, proj.sy, proj.z < 0 ? 1.7 : 1.1, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });

    // رسم عقد المحفظة الحية مرتبة من الخلف إلى الأمام (Painter's Algorithm)
    const projectedNodes = allocationNodes
      .map((node) => {
        const pt: Point3D = {
          x: Math.cos(node.latRad) * Math.cos(node.lonRad),
          y: Math.sin(node.latRad),
          z: Math.cos(node.latRad) * Math.sin(node.lonRad),
        };
        return {
          node,
          proj: project(pt, radius * 1.04),
        };
      })
      .sort((a, b) => b.proj.z - a.proj.z);

    projectedNodes.forEach(({ node, proj }) => {
      const isFront = proj.z <= radius * 0.25;
      const dotRadius = Math.max(4, Math.min(9.5, 3.6 + node.weightPct * 0.08));
      const nodeColor = node.isCash ? palette.accentTertiary : palette.success;

      // خط شعاعي خفيف من مركز الكرة إلى عقدة الأصل
      ctx.save();
      ctx.strokeStyle = nodeColor;
      ctx.globalAlpha = isFront ? 0.35 : 0.14;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(proj.sx, proj.sy);
      ctx.stroke();
      ctx.restore();

      // دائرة العقدة
      ctx.save();
      ctx.fillStyle = nodeColor;
      ctx.globalAlpha = isFront ? 0.96 : 0.42;
      ctx.beginPath();
      ctx.arc(proj.sx, proj.sy, dotRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = 1.4;
      ctx.strokeStyle = palette.textPrimary;
      ctx.stroke();
      ctx.restore();

      // تسمية الأصل المالي ونسبته المئوية بخط أحادي واضح
      ctx.save();
      ctx.globalAlpha = isFront ? 0.98 : 0.52;
      ctx.font = '700 11px "IBM Plex Mono", monospace';
      const label = `${node.symbol} ${node.weightPct.toFixed(0)}%`;
      const textWidth = ctx.measureText(label).width;
      const pillX = proj.sx - textWidth / 2 - 5;
      const pillY = proj.sy - dotRadius - 19;

      ctx.fillStyle = palette.bgElevated;
      ctx.fillRect(pillX, pillY, textWidth + 10, 15);
      ctx.strokeStyle = nodeColor;
      ctx.lineWidth = 0.9;
      ctx.strokeRect(pillX, pillY, textWidth + 10, 15);

      ctx.fillStyle = palette.textPrimary;
      ctx.fillText(label, pillX + 5, pillY + 11);
      ctx.restore();
    });

    ctx.restore();
  }, [allocationNodes, isStaticMode, surfaceParticles]);

  // حلقة الحركة أو الرسم الثابت الفردي عند تفعيل وضع الطاقة المنخفضة أو تعطيل الحركة
  useEffect(() => {
    if (rafRef.current !== null) {
      window.cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }

    if (isStaticMode) {
      drawFrame();
      return undefined;
    }

    const speedFactor = Math.max(0.15, activeState.modifiers.animationIntensity / 100);
    let active = true;

    const tick = () => {
      if (!active) return;
      if (!dragRef.current.active) {
        rotationRef.current.ry += 0.0045 * speedFactor;
      }
      drawFrame();
      rafRef.current = window.requestAnimationFrame(tick);
    };

    rafRef.current = window.requestAnimationFrame(tick);

    return () => {
      active = false;
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [
    isStaticMode,
    activeState.modifiers.animationIntensity,
    activeState.modifiers.glowIntensity,
    activeState.modifiers.highContrast,
    effectiveTokens,
    currentTheme.id,
    drawFrame,
    manualTick,
  ]);

  // معالجات السحب بالماوس واللمس ولوحة المفاتيح
  const handlePointerStart = (clientX: number, clientY: number) => {
    dragRef.current = { active: true, lastX: clientX, lastY: clientY };
  };

  const handlePointerMove = (clientX: number, clientY: number) => {
    if (!dragRef.current.active) return;
    const dx = clientX - dragRef.current.lastX;
    const dy = clientY - dragRef.current.lastY;
    dragRef.current.lastX = clientX;
    dragRef.current.lastY = clientY;

    rotationRef.current.ry += dx * 0.009;
    rotationRef.current.rx = Math.max(-1.2, Math.min(1.2, rotationRef.current.rx + dy * 0.009));

    if (isStaticMode) {
      drawFrame();
    }
  };

  const handlePointerEnd = () => {
    dragRef.current.active = false;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const step = 0.14;
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      rotationRef.current.ry -= step;
      setManualTick((n) => n + 1);
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      rotationRef.current.ry += step;
      setManualTick((n) => n + 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      rotationRef.current.rx = Math.max(-1.2, rotationRef.current.rx - step);
      setManualTick((n) => n + 1);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      rotationRef.current.rx = Math.min(1.2, rotationRef.current.rx + step);
      setManualTick((n) => n + 1);
    }
  };

  const handleResetView = () => {
    rotationRef.current = { rx: 0.32, ry: 0.65 };
    setManualTick((n) => n + 1);
  };

  const totalEquity = portfolio?.totalEquity ?? 1_000_000;
  const trilunairTarget = portfolio?.trilunairTargetUsd ?? 1_000_000_000_000;

  return (
    <section
      className="holo-panel"
      aria-label={
        language === 'ar'
          ? 'مجسم الثروة الهولوغرامي ثلاثي الأبعاد'
          : '3D Holographic Wealth Allocation Sphere'
      }
      style={{ padding: '0.95rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.7rem' }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          <Orbit size={17} style={{ color: 'var(--accent-primary)' }} aria-hidden="true" />
          <h3 style={{ margin: 0, fontSize: '0.92rem', fontWeight: 700 }}>
            {language === 'ar' ? 'كرة الثروة الهولوغرامية 3D' : 'Holographic Wealth Orb 3D'}
          </h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {isStaticMode ? (
            <span className="holo-badge" title="Zero idle GPU loop">
              {language === 'ar' ? 'إطار ثابت موفر للطاقة' : 'Static Frame (0% Idle GPU)'}
            </span>
          ) : (
            <span className="holo-badge holo-badge-accent">
              <Sparkles size={12} aria-hidden="true" />
              <span>{language === 'ar' ? 'مدار $1T حي' : 'Live $1T Orbit'}</span>
            </span>
          )}
          <button
            type="button"
            className="holo-btn"
            onClick={handleResetView}
            title={language === 'ar' ? 'إعادة ضبط زاوية المجسم' : 'Reset Orb Orientation'}
            aria-label={language === 'ar' ? 'إعادة ضبط زاوية المجسم' : 'Reset Orb Orientation'}
            style={{ minHeight: '30px', padding: '0.2rem 0.5rem' }}
          >
            <RotateCcw size={13} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div
        role="application"
        tabIndex={0}
        aria-label={
          language === 'ar'
            ? 'اسحب بالماوس أو اللمس أو استخدم الأسهم لتدوير كرة توزيع الأصول'
            : 'Drag with mouse/touch or use arrow keys to rotate portfolio sphere'
        }
        onKeyDown={handleKeyDown}
        onMouseDown={(e) => handlePointerStart(e.clientX, e.clientY)}
        onMouseMove={(e) => handlePointerMove(e.clientX, e.clientY)}
        onMouseUp={handlePointerEnd}
        onMouseLeave={handlePointerEnd}
        onTouchStart={(e) => {
          const touch = e.touches[0];
          if (touch) handlePointerStart(touch.clientX, touch.clientY);
        }}
        onTouchMove={(e) => {
          const touch = e.touches[0];
          if (touch) handlePointerMove(touch.clientX, touch.clientY);
        }}
        onTouchEnd={handlePointerEnd}
        className="holo-panel-subtle"
        style={{
          position: 'relative',
          height: '220px',
          cursor: 'grab',
          overflow: 'hidden',
          touchAction: 'none',
        }}
      >
        <canvas
          ref={canvasRef}
          data-testid="holographic-orb-canvas"
          style={{ width: '100%', height: '100%', display: 'block' }}
        />

        <div
          style={{
            position: 'absolute',
            bottom: '0.45rem',
            insetInlineStart: '0.6rem',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            pointerEvents: 'none',
          }}
        >
          {language === 'ar' ? 'اسحب للتدوير ثلاثي الأبعاد' : 'Drag or use arrows to rotate'}
        </div>
      </div>

      {/* ملخص نصي ورقمي قابل للوصول لتوزيع العقد ومسار التريليون */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.35rem',
        }}
      >
        {allocationNodes.map((node) => (
          <span
            key={node.symbol}
            className="holo-badge tabular-nums"
            style={{ fontSize: '0.72rem' }}
          >
            <strong style={{ color: 'var(--accent-primary)' }}>{node.symbol}</strong>
            <span>{formatNumber(node.weightPct, 1)}%</span>
          </span>
        ))}
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.76rem',
          color: 'var(--text-secondary)',
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '0.45rem',
        }}
      >
        <span>{language === 'ar' ? 'صافي الثروة الحالية:' : 'Current Net Worth:'}</span>
        <span className="tabular-nums" style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>
          {formatCurrency(totalEquity, true)} / {formatCurrency(trilunairTarget, true)}
        </span>
      </div>
    </section>
  );
};

export default HolographicOrb3D;
