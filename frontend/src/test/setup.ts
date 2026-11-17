/**
 * إعداد بيئة الاختبار الآلي للواجهة الأمامية (Vitest + Testing Library + JSDOM)
 * يوفر محاكاة قياسية لواجهات Canvas و matchMedia و SpeechSynthesis لاختبار الوصولية والمرونة
 */

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
});

if (typeof window !== 'undefined') {
  if (!window.matchMedia) {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  }

  if (!('ResizeObserver' in window)) {
    class MockResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    (window as unknown as Record<string, unknown>).ResizeObserver = MockResizeObserver;
  }

  // محاكاة سياق الرسم الثنائي الأبعاد Canvas في بيئة JSDOM
  HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation(() => ({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    strokeRect: vi.fn(),
    beginPath: vi.fn(),
    closePath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    arc: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    translate: vi.fn(),
    scale: vi.fn(),
    setLineDash: vi.fn(),
    fillText: vi.fn(),
    measureText: vi.fn(() => ({ width: 42 })),
    createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
    createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
  })) as unknown as typeof HTMLCanvasElement.prototype.getContext;

  if (!('speechSynthesis' in window)) {
    Object.defineProperty(window, 'speechSynthesis', {
      writable: true,
      value: {
        speak: vi.fn(),
        cancel: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        getVoices: vi.fn(() => [
          { lang: 'ar-SA', name: 'Arabic Voice', localService: true },
          { lang: 'en-US', name: 'English Voice', localService: true },
        ]),
      },
    });
  }

  if (!('SpeechSynthesisUtterance' in window)) {
    class MockUtterance {
      text: string;
      lang = 'ar-SA';
      rate = 1;
      pitch = 1;
      voice: unknown = null;
      onstart: (() => void) | null = null;
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(text: string) {
        this.text = text;
      }
    }
    (window as unknown as Record<string, unknown>).SpeechSynthesisUtterance = MockUtterance;
  }
}
