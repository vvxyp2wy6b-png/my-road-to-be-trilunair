import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '../theme/ThemeContext';
import { GovernanceView } from '../components/Governance/GovernanceView';
import { AgentMeetingRoom } from '../components/MeetingRoom/AgentMeetingRoom';
import { detectPreferredRecorderMimeType } from '../voice/useSpeechEngine';
import type { AgentMeetingResult, SystemStatus } from '../types/trilunair';

describe('v1.1.0-cloud-paper Frontend Security, Operations & Safari Audio Suite', () => {
  it('negotiates audio/mp4 first when Safari MediaRecorder only supports MP4/AAC', () => {
    const originalMediaRecorder = globalThis.MediaRecorder;
    try {
      globalThis.MediaRecorder = {
        isTypeSupported: (mime: string) => mime === 'audio/mp4',
      } as unknown as typeof MediaRecorder;

      expect(detectPreferredRecorderMimeType()).toBe('audio/mp4');
    } finally {
      globalThis.MediaRecorder = originalMediaRecorder;
    }
  });

  it('renders permanent PAPER lock, unified 5-limit risk strip (0.5/25/2/5/10%), Cloud Operations panel, and zero 7777 hints', () => {
    const status: SystemStatus = {
      appName: 'My Road to be Trilunair Dr.MaJoOoOoOoD',
      version: '1.1.0-cloud-paper',
      tradingMode: 'PAPER',
      killSwitchActive: false,
      liveAuthorized: false,
      executionLockedToPaper: true,
      marketDataMode: 'LIVE_PUBLIC',
      riskPolicy: {
        maxRiskPerTradePct: 0.5,
        maxExposurePerAssetPct: 25.0,
        dailyLossLimitPct: 2.0,
        weeklyLossLimitPct: 5.0,
        maxDrawdownLimitPct: 10.0,
        prohibitLeverage: true,
      },
      safetyChecks: {
        riskEngineVerified: true,
        maxDrawdownConfigured: true,
        killSwitchReady: true,
        positionLimitsActive: true,
        auditTrailHealthy: true,
      },
      providers: {
        llmProvider: 'multi-provider-council',
        sttProvider: 'web-speech-primary',
        ttsProvider: 'speech-synthesis+server-wav',
      },
    };

    const { container } = render(
      <ThemeProvider>
        <GovernanceView
          systemStatus={status}
          auditLogs={[]}
          onSwitchTradingMode={vi.fn()}
          onToggleKillSwitch={vi.fn()}
        />
      </ThemeProvider>
    );

    expect(container.textContent).not.toContain('7777');
    expect(screen.getByTestId('cloud-operations-panel')).toBeTruthy();
    const riskStrip = screen.getByTestId('unified-risk-policy-strip');
    expect(riskStrip.textContent).toContain('0.5%');
    expect(riskStrip.textContent).toContain('25%');
    expect(riskStrip.textContent).toContain('2%');
    expect(riskStrip.textContent).toContain('5%');
    expect(riskStrip.textContent).toContain('10%');
  });

  it('renders LIVE, CACHED, SIMULATED, and UNAVAILABLE execution badges plus uncertainty in AgentMeetingRoom', () => {
    const sampleMeeting: AgentMeetingResult = {
      meetingId: 'mtg_v1_1_test',
      topicAr: 'جلسة اختبار سحابية',
      topicEn: 'Cloud Deliberation Test',
      symbol: 'BTC-USD',
      timestamp: '2026-11-17T03:00:00Z',
      agentResponses: [
        {
          agentId: 'quant-alpha',
          nameAr: 'د. ريان',
          nameEn: 'Dr. Rayan',
          roleAr: 'محلل كمي',
          roleEn: 'Quant Analyst',
          status: 'AGREE',
          stance: 'BUY',
          confidence: 84,
          uncertaintyPct: 16,
          summaryAr: 'سيولة إيجابية.',
          summaryEn: 'Positive liquidity.',
          keyMetricLabelAr: 'الزخم',
          keyMetricLabelEn: 'Momentum',
          keyMetricValue: '+1.8s',
          providerUsed: 'openai',
          modelUsed: 'gpt-4o-mini',
          isSimulated: false,
          executionStatus: 'CACHED',
          respondedAt: '2026-11-17T03:00:01Z',
        },
      ],
      consensus: {
        agreementScorePct: 84,
        agreementsAr: ['توافق'],
        agreementsEn: ['Agreement'],
        disagreementsAr: [],
        disagreementsEn: [],
      },
      evidenceAndUncertainty: {
        uncertaintyScorePct: 16,
        evidenceAr: ['دليل'],
        evidenceEn: ['Evidence'],
        uncertaintiesAr: [],
        uncertaintiesEn: [],
      },
      estimatedCosts: {
        notionalUsd: 9600,
        spreadCostUsd: 2,
        commissionUsd: 4,
        slippageCostUsd: 3,
        totalEstimatedCostUsd: 9,
        costBps: 9.3,
      },
      riskAssessment: {
        passed: true,
        riskScore: 18,
        riskLevel: 'LOW',
        postTradeConcentrationPct: 5.8,
        varImpactUsd: 120,
        checks: [],
        violations: [],
      },
      finalRecommendation: {
        stance: 'BUY',
        confidence: 84,
        headlineAr: 'توصية ورقية منضبطة',
        headlineEn: 'Disciplined paper recommendation',
        actionableSummaryAr: 'شراء تجريبي',
        actionableSummaryEn: 'Paper buy',
        suggestedQuantity: 0.1,
      },
    };

    const dummySpeech = {
      sttSupported: true,
      ttsSupported: true,
      micPermission: 'prompt' as const,
      voiceAuthorized: false,
      mode: 'push-to-talk' as const,
      setMode: vi.fn(),
      recognitionLang: 'ar' as const,
      setRecognitionLang: vi.fn(),
      autoSpeakResponses: false,
      setAutoSpeakResponses: vi.fn(),
      status: 'unauthorized' as const,
      isListening: false,
      isSpeaking: false,
      activeSpeakerLabel: null,
      interimTranscript: '',
      errorMessage: null,
      requestExplicitMicAuthorization: vi.fn(async () => true),
      revokeMicAuthorization: vi.fn(),
      startListening: vi.fn(),
      stopListening: vi.fn(),
      speakText: vi.fn(),
      speakSequence: vi.fn(),
      interruptSpeech: vi.fn(),
    };

    render(
      <ThemeProvider>
        <AgentMeetingRoom
          meeting={sampleMeeting}
          isLoading={false}
          selectedSymbol="BTC-USD"
          speech={dummySpeech}
          onConveneMeeting={vi.fn(async () => {})}
          onProposeRecommendedTrade={vi.fn(async () => {})}
        />
      </ThemeProvider>
    );

    const badge = screen.getByTestId('agent-provider-quant-alpha');
    expect(badge.textContent).toContain('CACHED: openai (gpt-4o-mini)');
    expect(screen.getByTestId('agent-card-quant-alpha').textContent).toContain('±16%');
  });
});
