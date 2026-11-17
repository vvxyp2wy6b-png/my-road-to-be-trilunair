/**
 * عميل واجهة برمجة التطبيقات لوحدات الذكاء الكمي، التأهيل، قاعدة المعرفة،
 * الموصلات الخارجية، محول Binance Spot، والجدوى الاقتصادية
 */

import type {
  AuthorizationPolicyMode,
  EconomicViabilityReport,
  ExchangeAdapterStatus,
  ExternalConnectorDescriptor,
  GoalModeConfig,
  KnowledgeArticle,
  ManagedAgentConfig,
  QualificationExamResult,
  QuantumSystemOverview,
  RiskPolicyConfig,
} from '../types/quantum';

async function quantumRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/quantum${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch {
      // تجاهل أخطاء قراءة JSON
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const quantumApi = {
  getOverview: () => quantumRequest<QuantumSystemOverview>('/overview'),

  updateAgentConfig: (
    agentId: string,
    patch: Partial<{
      enabled: boolean;
      assignedProvider: string;
      assignedModel: string;
      decisionWeight: number;
      assignedSkills: string[];
      coreInstructions: string;
      canProposeTrades: boolean;
      canParticipateAutonomous: boolean;
    }>
  ) =>
    quantumRequest<ManagedAgentConfig>(`/agents/${encodeURIComponent(agentId)}`, {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),

  revokeAgentPermissions: (agentId: string) =>
    quantumRequest<ManagedAgentConfig>(
      `/agents/${encodeURIComponent(agentId)}/revoke-permissions`,
      { method: 'POST' }
    ),

  setAgentsPaused: (paused: boolean) =>
    quantumRequest<{ agentsPaused: boolean }>('/agents/pause-all', {
      method: 'POST',
      body: JSON.stringify({ paused }),
    }),

  evaluateQualification: (agentId: string) =>
    quantumRequest<QualificationExamResult>(
      `/agents/${encodeURIComponent(agentId)}/qualify`,
      { method: 'POST' }
    ),

  getKnowledgeBase: () => quantumRequest<KnowledgeArticle[]>('/knowledge'),

  upsertKnowledgeArticle: (payload: {
    id?: string;
    category: string;
    titleAr: string;
    titleEn: string;
    contentAr: string;
    contentEn: string;
  }) =>
    quantumRequest<KnowledgeArticle>('/knowledge', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  toggleSkill: (skillId: string, enabled: boolean) =>
    quantumRequest<{ skillId: string; enabled: boolean }>(
      `/skills/${encodeURIComponent(skillId)}`,
      {
        method: 'PUT',
        body: JSON.stringify({ enabled }),
      }
    ),

  updateConnector: (connectorId: string, enabled: boolean) =>
    quantumRequest<ExternalConnectorDescriptor>(
      `/connectors/${encodeURIComponent(connectorId)}`,
      {
        method: 'PUT',
        body: JSON.stringify({ enabled }),
      }
    ),

  updateRiskPolicy: (
    policy: Omit<
      RiskPolicyConfig,
      | 'prohibitLeverage'
      | 'prohibitMargin'
      | 'prohibitFutures'
      | 'prohibitBorrowing'
      | 'prohibitWithdrawals'
    > & { adminPin: string }
  ) =>
    quantumRequest<RiskPolicyConfig>('/risk-policy', {
      method: 'PUT',
      body: JSON.stringify(policy),
    }),

  updateAuthorizationPolicy: (payload: {
    policy: AuthorizationPolicyMode;
    adminPin: string;
  }) =>
    quantumRequest<ExchangeAdapterStatus>('/authorization-policy', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  reconcileExchangeState: () =>
    quantumRequest<ExchangeAdapterStatus>('/exchange/reconcile', {
      method: 'POST',
    }),

  evaluateTradeEconomics: (payload: {
    symbol: string;
    side: 'BUY' | 'SELL';
    quantity: number;
    entryPrice?: number;
    stopLoss?: number;
    takeProfit?: number;
  }) =>
    quantumRequest<EconomicViabilityReport>('/economics/evaluate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateGoalConfig: (goal: GoalModeConfig) =>
    quantumRequest<GoalModeConfig>('/goal-config', {
      method: 'PUT',
      body: JSON.stringify(goal),
    }),
};
