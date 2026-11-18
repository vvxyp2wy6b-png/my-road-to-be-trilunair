/**
 * عميل واجهة برمجة التطبيقات الموحد (REST + WebSocket)
 * يربط الواجهة الهولوغرامية بمحرك المخاطر والوكلاء وبوابة التصاريح
 */

import type {
  ActiveThemeState,
  AdminSessionStatus,
  AgentMeetingResult,
  AgentProfile,
  AiCommandResponse,
  AuditLogEntry,
  ChatMessageRecord,
  CloudOperationsTelemetry,
  CommandSource,
  HostingDecisionMatrix,
  Language,
  LiveSpotReadiness,
  MarketAsset,
  MarketCandlesResponse,
  OrderRecord,
  PasskeySecurityPosture,
  PersonalBinanceOverview,
  PipelineLatencySnapshot,
  PortfolioSnapshot,
  SystemStatus,
  ThemeDefinition,
  ThemesPayload,
  TradeProposalEvaluation,
  TradeProposalInput,
  TradingMode,
  WalkForwardEvaluation,
  WealthArchitectOverview,
} from '../types/trilunair';

const API_BASE = '/api';

let activeCsrfToken: string | null = null;
let activeStepUpToken: string | null = null;

export function setActiveCsrfToken(token: string | null): void {
  activeCsrfToken = token;
}

export function setActiveStepUpToken(token: string | null): void {
  activeStepUpToken = token;
}

export function getActiveStepUpToken(): string | null {
  return activeStepUpToken;
}

function base64UrlToArrayBuffer(base64url: string): ArrayBuffer {
  const padded = base64url.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (base64url.length % 4)) % 4);
  const binary = window.atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

function arrayBufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const method = (options?.method || 'GET').toUpperCase();
  const csrfHeaders: Record<string, string> =
    activeCsrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
      ? { 'X-CSRF-Token': activeCsrfToken }
      : {};
  const stepUpHeaders: Record<string, string> =
    activeStepUpToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
      ? { 'X-Step-Up-Token': activeStepUpToken }
      : {};

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...csrfHeaders,
      ...stepUpHeaders,
      ...((options?.headers as Record<string, string>) || {}),
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
  // حالة النظام وبوابة الأمان والعمليات السحابية
  getSystemStatus: () => requestJson<SystemStatus>('/system/status'),

  getOperationsTelemetry: () => requestJson<CloudOperationsTelemetry>('/system/operations'),

  getBenchmarkMatrix: () => requestJson<HostingDecisionMatrix>('/infrastructure/benchmark-matrix'),

  getLatencyPipeline: () => requestJson<PipelineLatencySnapshot>('/analytics/latency-pipeline'),

  getPerformanceEvaluation: (symbol = 'BTC-USD') =>
    requestJson<WalkForwardEvaluation>(`/analytics/performance-evaluation?symbol=${encodeURIComponent(symbol)}`),

  getPasskeyStatus: () => requestJson<PasskeySecurityPosture>('/auth/passkey/status'),

  registerOwnerPasskey: async (deviceLabel: string, adminSecret?: string) => {
    if (!window.PublicKeyCredential || !navigator.credentials?.create) {
      throw new Error('متصفحك الحالي لا يدعم WebAuthn Passkeys (يتطلب HTTPS أو localhost مع Safari/Chrome).');
    }
    const optsResp = await requestJson<{
      challengeId: string;
      deviceLabel: string;
      publicKey: {
        rp: { name: string; id: string };
        user: { id: string; name: string; displayName: string };
        challenge: string;
        pubKeyCredParams: Array<{ type: 'public-key'; alg: number }>;
        timeout: number;
        attestation: AttestationConveyancePreference;
        authenticatorSelection: AuthenticatorSelectionCriteria;
        excludeCredentials?: Array<{ type: 'public-key'; id: string; transports?: AuthenticatorTransport[] }>;
      };
    }>('/auth/passkey/register/options', {
      method: 'POST',
      body: JSON.stringify({ deviceLabel, adminSecret: adminSecret || '' }),
    });

    const pk = optsResp.publicKey;
    const cred = (await navigator.credentials.create({
      publicKey: {
        rp: pk.rp,
        user: {
          id: base64UrlToArrayBuffer(pk.user.id),
          name: pk.user.name,
          displayName: pk.user.displayName,
        },
        challenge: base64UrlToArrayBuffer(pk.challenge),
        pubKeyCredParams: pk.pubKeyCredParams,
        timeout: pk.timeout,
        attestation: pk.attestation,
        authenticatorSelection: pk.authenticatorSelection,
        excludeCredentials: (pk.excludeCredentials || []).map((ec) => ({
          type: 'public-key',
          id: base64UrlToArrayBuffer(ec.id),
          transports: ec.transports,
        })),
      },
    })) as PublicKeyCredential | null;

    if (!cred) {
      throw new Error('تم إلغاء عملية تسجيل مفتاح المرور البيومتري.');
    }

    const attResp = cred.response as AuthenticatorAttestationResponse;
    const verified = await requestJson<{
      registered: boolean;
      credentialId: string;
      deviceLabel: string;
      stepUpToken: string;
      stepUpExpiresAtEpoch: number;
    }>('/auth/passkey/register/verify', {
      method: 'POST',
      body: JSON.stringify({
        challengeId: optsResp.challengeId,
        deviceLabel: optsResp.deviceLabel,
        credential: {
          id: cred.id,
          type: cred.type,
          response: {
            clientDataJSON: arrayBufferToBase64Url(attResp.clientDataJSON),
            attestationObject: arrayBufferToBase64Url(attResp.attestationObject),
            transports: typeof attResp.getTransports === 'function' ? attResp.getTransports() : ['internal'],
          },
        },
      }),
    });
    activeStepUpToken = verified.stepUpToken;
    return verified;
  },

  authenticateWithPasskey: async () => {
    if (!window.PublicKeyCredential || !navigator.credentials?.get) {
      throw new Error('متصفحك الحالي لا يدعم WebAuthn Passkeys.');
    }
    const optsResp = await requestJson<{
      challengeId: string;
      publicKey: {
        challenge: string;
        rpId: string;
        timeout: number;
        userVerification: UserVerificationRequirement;
        allowCredentials: Array<{ type: 'public-key'; id: string; transports?: AuthenticatorTransport[] }>;
      };
    }>('/auth/passkey/authenticate/options', {
      method: 'POST',
      body: JSON.stringify({}),
    });

    const pk = optsResp.publicKey;
    const assertion = (await navigator.credentials.get({
      publicKey: {
        challenge: base64UrlToArrayBuffer(pk.challenge),
        rpId: pk.rpId,
        timeout: pk.timeout,
        userVerification: pk.userVerification,
        allowCredentials: pk.allowCredentials.map((ac) => ({
          type: 'public-key',
          id: base64UrlToArrayBuffer(ac.id),
          transports: ac.transports,
        })),
      },
    })) as PublicKeyCredential | null;

    if (!assertion) {
      throw new Error('تم إلغاء التحقق البيومتري.');
    }

    const assertResp = assertion.response as AuthenticatorAssertionResponse;
    const verified = await requestJson<{
      authenticated: boolean;
      authMethod: string;
      deviceLabel: string;
      csrfToken: string;
      stepUpToken: string;
      stepUpExpiresAtEpoch: number;
    }>('/auth/passkey/authenticate/verify', {
      method: 'POST',
      body: JSON.stringify({
        challengeId: optsResp.challengeId,
        credential: {
          id: assertion.id,
          type: assertion.type,
          response: {
            clientDataJSON: arrayBufferToBase64Url(assertResp.clientDataJSON),
            authenticatorData: arrayBufferToBase64Url(assertResp.authenticatorData),
            signature: arrayBufferToBase64Url(assertResp.signature),
          },
        },
      }),
    });
    activeCsrfToken = verified.csrfToken;
    activeStepUpToken = verified.stepUpToken;
    return verified;
  },

  revokePasskeyDevice: (credentialId: string, adminSecret?: string) =>
    requestJson<{ revoked: boolean; credentialId: string }>(`/auth/passkey/devices/${encodeURIComponent(credentialId)}`, {
      method: 'DELETE',
      body: JSON.stringify({ adminSecret: adminSecret || '' }),
    }),

  generateRecoveryCodes: (adminSecret?: string) =>
    requestJson<{
      generatedCount: number;
      recoveryCodesOnceOnly: string[];
      warningAr: string;
      warningEn: string;
    }>('/auth/passkey/recovery/generate', {
      method: 'POST',
      body: JSON.stringify({ count: 6, adminSecret: adminSecret || '' }),
    }),

  redeemRecoveryCode: async (recoveryCode: string) => {
    const res = await requestJson<{
      authenticated: boolean;
      csrfToken: string;
      stepUpToken: string;
    }>('/auth/passkey/recovery/redeem', {
      method: 'POST',
      body: JSON.stringify({ recoveryCode }),
    });
    activeCsrfToken = res.csrfToken;
    activeStepUpToken = res.stepUpToken;
    return res;
  },

  getAdminSessionStatus: async () => {
    const status = await requestJson<AdminSessionStatus>('/auth/session/status');
    if (status.csrfToken) {
      activeCsrfToken = status.csrfToken;
    }
    return status;
  },

  loginAdminSession: async (adminSecret: string) => {
    const res = await requestJson<{
      authenticated: boolean;
      sessionToken: string;
      csrfToken: string;
      expiresAtEpoch: number;
      ttlSeconds: number;
      tradingMode: TradingMode;
      liveAuthorized: boolean;
      executionLockedToPaper: boolean;
    }>('/auth/session/login', {
      method: 'POST',
      body: JSON.stringify({ adminSecret }),
    });
    activeCsrfToken = res.csrfToken;
    return res;
  },

  logoutAdminSession: async () => {
    const res = await requestJson<{ authenticated: boolean; revoked: boolean }>('/auth/session/logout', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    activeCsrfToken = null;
    activeStepUpToken = null;
    return res;
  },

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

  // Personal CFO, Debt Planner, Saudi Employment Benefits & Investment Capital Ledger
  getWealthOverview: () => requestJson<WealthArchitectOverview>('/wealth/overview'),

  updateEmploymentContract: (payload: {
    commencementDate: string;
    contractExpiryDate: string;
    contractType?: 'FIXED_TERM' | 'INDEFINITE';
    autoRenews?: boolean;
    nonRenewalNoticeDays?: number;
    eligibleFinalWageSar: number;
    annualLeaveDaysPerYear?: number;
    annualLeaveTakenDays?: number;
    exactContractExpiryVerified?: boolean;
  }) =>
    requestJson<WealthArchitectOverview>('/wealth/employment/contract', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  recordContractEvidence: (payload: {
    documentType: string;
    title: string;
    deliveryChannel?: string;
    verifiedByOwner?: boolean;
    notes?: string;
  }) =>
    requestJson<{ evidenceId: string; documentSha256: string; autoNoticeSent: boolean }>(
      '/wealth/contract/evidence',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  recordInvestmentAllocation: (payload: {
    amountSar: number;
    diversifiedWeightPct?: number;
    saudiEquitiesWeightPct?: number;
    cryptoSpotPaperWeightPct?: number;
    notes?: string;
  }) =>
    requestJson<WealthArchitectOverview>('/wealth/investment/ledger', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // حساب Binance الشخصي (للقراءة فقط + خزنة Ed25519 + بوابات LIVE_SPOT الثماني)
  getPersonalBinanceOverview: () =>
    requestJson<PersonalBinanceOverview>('/binance/personal/overview'),

  generateServerEd25519Keypair: (purpose: 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION' = 'READ_ONLY_MONITORING', adminSecret?: string) =>
    requestJson<{
      keypairId: string;
      purpose: string;
      algorithm: 'ED25519';
      publicKeyPem: string;
      privateKeyExported: false;
      createdAt: string;
      binanceRegistrationInstructionsEn: string;
      binanceRegistrationInstructionsAr: string;
    }>('/binance/personal/ed25519/generate', {
      method: 'POST',
      body: JSON.stringify({ purpose, adminSecret }),
    }),

  savePersonalBinanceCredential: (payload: {
    purpose: 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION';
    keyLabel: string;
    authAlgorithm: 'ED25519' | 'RSA_SHA256' | 'HMAC_SHA256';
    environment: 'MAINNET' | 'SPOT_TESTNET';
    apiKey: string;
    generatedKeypairId?: string;
    privateKeyPem?: string;
    apiSecret?: string;
    trustedIps?: string[];
    trackedSymbols?: string[];
    verifyImmediately?: boolean;
    adminSecret?: string;
  }) =>
    requestJson<{
      saved: boolean;
      purpose: string;
      credentialId: string;
      apiKeyMasked: string;
      secretExposed: false;
      tradingMode: 'PAPER';
      liveAuthorized: false;
    }>('/binance/personal/credentials', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  rotatePersonalBinanceCredential: (
    purpose: 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION',
    payload: {
      keyLabel: string;
      authAlgorithm: 'ED25519' | 'RSA_SHA256' | 'HMAC_SHA256';
      environment: 'MAINNET' | 'SPOT_TESTNET';
      apiKey: string;
      generatedKeypairId?: string;
      privateKeyPem?: string;
      apiSecret?: string;
      trustedIps?: string[];
      adminSecret?: string;
    }
  ) =>
    requestJson<{
      saved: boolean;
      rotated: boolean;
      apiKeyMasked: string;
    }>(`/binance/personal/credentials/${purpose}/rotate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  revokePersonalBinanceCredential: (
    purpose: 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION',
    adminSecret?: string
  ) =>
    requestJson<{ revoked: boolean; purpose: string; revokedAt: string }>(
      `/binance/personal/credentials/${purpose}${adminSecret ? `?adminSecret=${encodeURIComponent(adminSecret)}` : ''}`,
      { method: 'DELETE' }
    ),

  verifyPersonalBinancePermissions: (
    purpose: 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION' = 'READ_ONLY_MONITORING',
    adminSecret?: string
  ) =>
    requestJson<{
      configured: boolean;
      connectionStatus: string;
      latencyMs?: number;
      usedWeight1m?: number;
    }>('/binance/personal/verify-permissions', {
      method: 'POST',
      body: JSON.stringify({ purpose, adminSecret }),
    }),

  syncPersonalBinanceAccount: (
    purpose: 'READ_ONLY_MONITORING' | 'FUTURE_SPOT_EXECUTION' = 'READ_ONLY_MONITORING',
    adminSecret?: string
  ) =>
    requestJson<PersonalBinanceOverview>('/binance/personal/sync', {
      method: 'POST',
      body: JSON.stringify({ purpose, adminSecret }),
    }),

  getLiveSpotReadiness: () =>
    requestJson<LiveSpotReadiness>('/binance/spot-execution/readiness'),

  updateOwnerSpotLimits: (payload: {
    jurisdictionEligibilityConfirmed: boolean;
    jurisdictionCountryCode: string;
    maxSingleOrderSar: number;
    maxDailySpotSar: number;
    maxMonthlySpotSar: number;
    maxSingleAssetExposurePct: number;
    requireBiometricPerOrder: boolean;
    allowedSpotSymbols: string[];
    adminSecret?: string;
  }) =>
    requestJson<LiveSpotReadiness>('/binance/spot-execution/limits', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // منظومة الهوية السيادية والدخول متعدد العوامل لأدمن المنصة (TRM Admin MFA Gate)
  getAdminIdentity: () =>
    requestJson<{
      brand: {
        monogram: string;
        expansionEn: string;
        titleAr: string;
        meaningAr: string;
      };
      enrolled: boolean;
      authenticated: boolean;
      displayName: string;
      emailMasked: string | null;
      phoneMasked: string | null;
      totpVerified: boolean;
      mfaFactorsConfigured: {
        email: boolean;
        phone: boolean;
        verificationKey: boolean;
        authenticatorTotp: boolean;
      };
      updatedAt?: string;
      tradingMode: 'PAPER';
      liveAuthorized: false;
    }>('/auth/admin/identity'),

  enrollAdminIdentity: (payload: {
    displayName?: string;
    email: string;
    phone: string;
    verificationKey: string;
    currentVerificationKey?: string;
    rotateTotp?: boolean;
  }) =>
    requestJson<{
      enrolled: boolean;
      displayName: string;
      emailMasked: string;
      phoneMasked: string;
      authenticatorSetup: {
        issuer: string;
        secretBase32: string;
        otpauthUri: string;
        digits: number;
        periodSeconds: number;
        instructionsAr: string;
      };
      tradingMode: 'PAPER';
      liveAuthorized: false;
    }>('/auth/admin/enroll', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  confirmAdminTotp: (payload: { verificationKey: string; totpCode: string }) =>
    requestJson<{ totpVerified: boolean; brandMonogram: string }>('/auth/admin/totp/confirm', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  loginAdminMfa: async (payload: {
    email: string;
    phone: string;
    verificationKey: string;
    totpCode: string;
  }) => {
    const res = await requestJson<{
      authenticated: boolean;
      displayName: string;
      emailMasked: string;
      phoneMasked: string;
      brandMonogram: string;
      sessionToken: string;
      csrfToken: string;
      expiresAtEpoch: number;
      tradingMode: 'PAPER';
      liveAuthorized: false;
    }>('/auth/admin/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.csrfToken) {
      setActiveCsrfToken(res.csrfToken);
    }
    return res;
  },
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
