/**
 * حاجز أمان المؤثرات البصرية والرسوميات ثلاثية الأبعاد (Visual Effects Error Boundary)
 * يضمن عزل أي خطأ في Canvas أو الرسوميات الزخرفية بحيث لا تتأثر أبداً
 * أسعار السوق، تذاكر الأوامر، فحوصات المخاطر، أو بوابة التصاريح.
 */

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import type { Language } from '../../types/trilunair';

export interface VisualEffectsBoundaryProps {
  children: React.ReactNode;
  widgetNameAr?: string;
  widgetNameEn?: string;
  language?: Language;
  /** خاصية مخصصة لاختبارات المرونة والتحمل لمحاكاة عطل في محرك الرسوميات */
  simulateError?: boolean;
  fallbackSummary?: React.ReactNode;
}

interface VisualEffectsBoundaryState {
  hasError: boolean;
  errorMessage: string;
  wasSimulated: boolean;
}

/**
 * مكون داخلي يُطلق خطأً متعمداً عند تفعيل خاصية simulateError لاختبار صمود الواجهة المالية
 */
const SimulatedEffectFault: React.FC<{ active: boolean }> = ({ active }) => {
  if (active) {
    throw new Error('Simulated WebGL/Canvas rendering pipeline fault');
  }
  return null;
};

export class VisualEffectsBoundary extends React.Component<
  VisualEffectsBoundaryProps,
  VisualEffectsBoundaryState
> {
  public override state: VisualEffectsBoundaryState = {
    hasError: false,
    errorMessage: '',
    wasSimulated: false,
  };

  public static getDerivedStateFromProps(
    nextProps: VisualEffectsBoundaryProps,
    prevState: VisualEffectsBoundaryState
  ): Partial<VisualEffectsBoundaryState> | null {
    if (nextProps.simulateError && !prevState.wasSimulated) {
      return { wasSimulated: true };
    }
    if (!nextProps.simulateError && prevState.wasSimulated) {
      return { hasError: false, errorMessage: '', wasSimulated: false };
    }
    return null;
  }

  public static getDerivedStateFromError(error: Error): Partial<VisualEffectsBoundaryState> {
    return {
      hasError: true,
      errorMessage: error?.message || 'Visual rendering exception',
    };
  }

  public override componentDidCatch(error: Error, info: React.ErrorInfo): void {
    // تسجيل هادئ دون تعطيل العمليات المالية الحرجة
    if (typeof console !== 'undefined' && typeof console.warn === 'function') {
      console.warn('[VisualEffectsBoundary] Decorative/Canvas widget isolated:', error.message, info.componentStack);
    }
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, errorMessage: '' });
  };

  private resolveLanguage(): Language {
    if (this.props.language) {
      return this.props.language;
    }
    if (typeof document !== 'undefined' && document.documentElement.lang === 'en') {
      return 'en';
    }
    return 'ar';
  }

  public override render(): React.ReactNode {
    const lang = this.resolveLanguage();
    const title =
      lang === 'ar'
        ? this.props.widgetNameAr || 'وحدة العرض الهولوغرامي'
        : this.props.widgetNameEn || 'Holographic Visual Module';

    if (this.state.hasError) {
      return (
        <section
          role="status"
          aria-live="polite"
          data-testid="visual-effects-fallback"
          className="holo-panel"
          style={{
            padding: '1rem 1.15rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.65rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.75rem',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
              <AlertTriangle
                size={18}
                style={{ color: 'var(--status-warning)', flexShrink: 0 }}
                aria-hidden="true"
              />
              <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                {lang === 'ar'
                  ? `وضع الحماية البصري نشط — ${title}`
                  : `Safe Visual Fallback Active — ${title}`}
              </strong>
            </div>

            <span className="holo-badge holo-badge-success">
              {lang === 'ar'
                ? 'التداول والمخاطر يعملان بكفاءة 100%'
                : 'Trading & Risk Engine 100% Operational'}
            </span>
          </div>

          <p
            style={{
              margin: 0,
              fontSize: '0.84rem',
              color: 'var(--text-secondary)',
            }}
          >
            {lang === 'ar'
              ? 'تم عزل عطل عارض في طبقة الرسوميات دون أي تأثير على الأسعار الحية أو دفاتر الأوامر أو بوابة التصاريح.'
              : 'A graphical rendering exception was safely isolated. Live prices, order tickets, and risk checks remain completely unaffected.'}
          </p>

          {this.props.fallbackSummary ? (
            <div className="holo-panel-subtle" style={{ padding: '0.65rem 0.8rem' }}>
              {this.props.fallbackSummary}
            </div>
          ) : null}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
            <span
              className="tabular-nums"
              style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}
            >
              {this.state.errorMessage}
            </span>
            {!this.props.simulateError && (
              <button
                type="button"
                className="holo-btn"
                onClick={this.handleReset}
                style={{ minHeight: '34px', padding: '0.3rem 0.75rem', fontSize: '0.8rem' }}
              >
                <RefreshCw size={14} aria-hidden="true" />
                <span>{lang === 'ar' ? 'إعادة تشغيل العرض' : 'Reload Visual'}</span>
              </button>
            )}
          </div>
        </section>
      );
    }

    return (
      <>
        <SimulatedEffectFault active={Boolean(this.props.simulateError)} />
        {this.props.children}
      </>
    );
  }
}

export default VisualEffectsBoundary;
