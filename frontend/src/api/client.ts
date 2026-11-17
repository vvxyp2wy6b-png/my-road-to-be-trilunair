/**
 * عميل واجهة برمجة التطبيقات الموحد (REST + WebSocket)
 * يربط الواجهة الهولوغرامية بمحرك المخاطر والوكلاء وبوابة التصاريح
 */

import type {
  ActiveThemeState,
  AgentMeetingResult,
  AgentProfile,
  AiCommandResponse,
  AuditLogEntry,
  ChatMessageRecord,
  CommandSource,
  Language,
  MarketAsset,
  MarketCandlesResponse,
  OrderRecord,
  PortfolioSnapshot,
  SystemStatus,
  ThemeDefinition,
  ThemesPayload,
  TradeProposalEvaluation,
  TradeProposalInput,
  TradingMode,
} from '../types/trilunair';

const API_BASE = '/api';

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      errorMessage = errBody.detail || errBody.message || errorMessage;
    } catch {
      // تجاهل أخطاء تحليل JSON عند فشل الشبكة
    }
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}

export const trilunairApi = {
  // حالة النظام وبوابة الأمان
  getSystemStatus: () => requestJson<SystemStatus>('/system/status'),

  setTradingMode: (payload: {
    targetMode: TradingMode;
    adminPin: string;
    confirmationPhrase: string;
    acknowledgeRealCapitalRisk: boolean;
  }) =>
    requestJson<SystemStatus>('/auth/trading-mode', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  setKillSwitch: (active: boolean, reason: string) =>
    requestJson<SystemStatus>('/auth/kill-switch', {
      method: 'POST',
      body: JSON.stringify({ active, reason }),
    }),

  getAuditLogs: () => requestJson<AuditLogEntry[]>('/auth/audit-logs'),

  // الأسواق والمحفظة والأوامر
  getAssets: () => requestJson<MarketAsset[]>('/market/assets'),

  getCandles: (symbol: string, timeframe = '15m', limit = 90) =>
    requestJson<MarketCandlesResponse>(
      `/market/candles/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`
    ),

  getPortfolio: () => requestJson<PortfolioSnapshot>('/portfolio'),

  proposeOrder: (proposal: TradeProposalInput) =>
    requestJson<TradeProposalEvaluation>('/orders/propose', {
      method: 'POST',
      body: JSON.stringify(proposal),
    }),

  executeOrder: (payload: {
    proposalId: string;
    confirmedByUser: boolean;
    adminPin?: string;
    source: CommandSource;
  }) =>
    requestJson<{
      order: OrderRecord;
      portfolio: PortfolioSnapshot;
    }>('/orders/execute', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // محرك السمات المستديم
  getThemes: () => requestJson<ThemesPayload>('/themes'),

  saveActiveThemeState: (state: ActiveThemeState) =>
    requestJson<ActiveThemeState>('/themes/active', {
      method: 'PUT',
      body: JSON.stringify(state),
    }),

  saveCustomTheme: (theme: ThemeDefinition) =>
    requestJson<ThemeDefinition>('/themes/custom', {
      method: 'POST',
      body: JSON.stringify(theme),
    }),

  deleteCustomTheme: (themeId: string) =>
    requestJson<{ deleted: boolean }>(`/themes/custom/${encodeURIComponent(themeId)}`, {
      method: 'DELETE',
    }),

  importThemeConfig: (configJson: unknown) =>
    requestJson<ThemeDefinition>('/themes/import', {
      method: 'POST',
      body: JSON.stringify(configJson),
    }),

  // الذكاء الاصطناعي وغرفة الأوامر الصوتية وقاعة اجتماع الوكلاء
  getAgents: () => requestJson<AgentProfile[]>('/ai/agents'),

  getChatHistory: () =>
    requestJson<{
      messages: ChatMessageRecord[];
      latestMeeting: AgentMeetingResult | null;
    }>('/ai/history'),

  clearChatHistory: () =>
    requestJson<{ cleared: boolean }>('/ai/history', {
      method: 'DELETE',
    }),

  sendAiCommand: (payload: {
    message: string;
    language: Language;
    source: CommandSource;
    selectedAgent: string;
    triggerMeeting?: boolean;
  }) =>
    requestJson<AiCommandResponse>('/ai/command', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  conveneAgentMeeting: (payload: {
    symbol: string;
    horizon?: string;
    language: Language;
  }) =>
    requestJson<AgentMeetingResult>('/ai/meeting', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

export interface MarketWsTick {
  type: 'MARKET_TICK';
  timestamp: string;
  assets: MarketAsset[];
  totalEquity: number;
  dailyPnl: number;
  dailyPnlPct: number;
}

export function connectMarketStream(
  onTick: (tick: MarketWsTick) => void,
  onStatusChange?: (connected: boolean) => void
): () => void {
  let ws: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let closedIntentionally = false;

  const connect = () => {
    if (closedIntentionally) return;
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${protocol}//${window.location.host}/ws/market`;
      ws = new WebSocket(url);

      ws.onopen = () => {
        onStatusChange?.(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as MarketWsTick;
          if (data && data.type === 'MARKET_TICK') {
            onTick(data);
          }
        } catch {
          // تجاهل الرسائل غير الصالحة
        }
      };

      ws.onclose = () => {
        onStatusChange?.(false);
        if (!closedIntentionally) {
          reconnectTimer = window.setTimeout(connect, 3500);
        }
      };

      ws.onerror = () => {
        onStatusChange?.(false);
      };
    } catch {
      onStatusChange?.(false);
    }
  };

  connect();

  return () => {
    closedIntentionally = true;
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
    }
    if (ws) {
      ws.close();
    }
  };
}
