"""
نقطة الدخول الرئيسية لتطبيق الخادم الخلفي (FastAPI + WebSocket).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.1.0-cloud-paper

يربط هذا الخادم كافة الوحدات المعمارية تحت المسار /api/... بالإضافة إلى البث الحي عبر /ws/market،
مع تطبيق طبقة الأمان السحابي الصلب، القفل الدائم على التداول الورقي (PAPER)،
وتقديم ملفات الواجهة الأمامية المبنية (SPA) تلقائياً عند وجود المجلد frontend/dist.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.agents_council import (
    clear_chat_history,
    convene_meeting,
    get_agents,
    get_chat_history,
    process_ai_command,
)
from app.binance_market_data import binance_public_client
from app.database import append_audit_log, check_infrastructure_status, db_session, fetch_audit_logs, init_db, utc_now_iso
from app.llm_adapters import get_provider_credentials_report
from app.market_engine import market_engine
from app.models import (
    ActiveThemeState,
    AgentMeetingResult,
    AgentProfile,
    AiCommandRequest,
    AiCommandResponse,
    AuditLogEntry,
    ConveneMeetingRequest,
    KillSwitchRequest,
    MarketAsset,
    MarketCandlesResponse,
    MarketWsTick,
    OrderExecuteRequest,
    OrderExecuteResponse,
    PortfolioSnapshot,
    SystemStatus,
    ThemeDefinition,
    ThemesPayload,
    TradeProposalEvaluation,
    TradeProposalInput,
    TradingModeRequest,
)
from app.safety_gateway import (
    APP_VERSION,
    execute_order,
    get_portfolio_snapshot,
    get_system_status,
    propose_order,
    set_kill_switch,
    set_trading_mode,
)
from app.security import (
    ADMIN_SESSION_COOKIE,
    clear_session_cookie,
    create_admin_session,
    enforce_admin_secret,
    get_admin_auth_config_state,
    get_allowed_cors_origins,
    get_client_identifier,
    rate_limiter,
    require_authenticated_session_or_secret,
    revoke_session_token,
    security_telemetry,
    set_session_cookie,
    verify_session_token,
)
from app.themes_service import (
    delete_custom_theme,
    get_themes_payload,
    import_theme_config,
    save_active_theme_state,
    save_custom_theme,
)
from app.voice_service import get_voice_subsystem_status, handle_stt_request, handle_tts_request


class MarketConnectionManager:
    """مدير اتصالات WebSocket للبث المتزامن لنبضات السوق الحية (/ws/market)."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self.broadcaster_running: bool = False

    async def connect(self, websocket: WebSocket) -> None:
        """قبول اتصال عميل جديد وإضافته إلى مجموعة البث النشطة."""
        await websocket.accept()
        self.active_connections.add(websocket)
        with security_telemetry._lock:
            security_telemetry.ws_connections_opened += 1

    def disconnect(self, websocket: WebSocket) -> None:
        """إزالة اتصال العميل عند إغلاق الجلسة."""
        self.active_connections.discard(websocket)

    def build_tick_payload(self, step_prices: bool = False) -> dict[str, Any]:
        """بناء حمولة نبضة السوق الحية المتوافقة مع MarketWsTick."""
        assets = market_engine.tick() if step_prices else market_engine.get_assets()
        portfolio = get_portfolio_snapshot()
        tick = MarketWsTick(
            type="MARKET_TICK",
            timestamp=utc_now_iso(),
            assets=assets,
            totalEquity=portfolio.totalEquity,
            dailyPnl=portfolio.dailyPnl,
            dailyPnlPct=portfolio.dailyPnlPct,
        )
        return tick.model_dump()

    async def broadcast_tick(self) -> None:
        """تحديث الأسعار وبثها لجميع العملاء المتصلين دون تعطيل الحلقة غير المتزامنة."""
        if not self.active_connections:
            market_engine.tick()
            return
        payload = self.build_tick_payload(step_prices=True)
        stale: list[WebSocket] = []
        for ws in list(self.active_connections):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


ws_manager = MarketConnectionManager()


async def _market_broadcast_loop() -> None:
    """حلقة خلفية تبث تحديثات السوق كل 1.5 ثانية لجميع جلسات WebSocket النشطة."""
    ws_manager.broadcaster_running = True
    try:
        while True:
            await asyncio.sleep(1.5)
            await ws_manager.broadcast_tick()
    except asyncio.CancelledError:
        pass
    finally:
        ws_manager.broadcaster_running = False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """مدير دورة حياة التطبيق لتهيئة قاعدة البيانات وتشغيل حلقة البث ومشرف بيانات Binance العام."""
    init_db()
    try:
        from app.quantum_hub import ensure_quantum_tables

        ensure_quantum_tables()
    except Exception:
        pass

    binance_supervisor_task: asyncio.Task[Any] | None = None
    if os.getenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED").strip().upper() == "LIVE_PUBLIC":
        binance_supervisor_task = asyncio.create_task(binance_public_client.run_ws_supervisor_loop())

    broadcaster_task = asyncio.create_task(_market_broadcast_loop())
    try:
        yield
    finally:
        broadcaster_task.cancel()
        if binance_supervisor_task is not None:
            binance_supervisor_task.cancel()
        try:
            await broadcaster_task
        except asyncio.CancelledError:
            pass
        if binance_supervisor_task is not None:
            try:
                await binance_supervisor_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="My Road to be Trilunair Dr.MaJoOoOoOoD — Holographic Command API",
    description="الخادم الخلفي لمركز القيادة الهولوغرامي، بوابة الأمان المالي السحابية، ومحرك الوكلاء الخمسة.",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-CSRF-Token",
        "X-Requested-With",
    ],
)


@app.middleware("http")
async def cloud_security_and_telemetry_middleware(request: Request, call_next) -> Response:
    """
    طبقة الحماية السحابية المركزية:
    1. تحديد معدل الطلبات العام لكل عميل لمنع إغراق الواجهة البرمجية (Rate Limiting).
    2. إضافة ترويسات الأمان القياسية (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy).
    3. تسجيل إحصاءات الاستجابة ومعدلات الخطأ في جامع القياسات الأمنية المهيكل.
    """
    path = request.url.path
    if path.startswith("/api/") and path != "/api/health":
        api_limit_per_min = max(30, int(os.getenv("TRILUNAIR_API_RATE_LIMIT_PER_MIN", "600")))
        client_id = get_client_identifier(request)
        allowed, retry_after = rate_limiter.check_and_record(
            f"api_req:{client_id}",
            limit=api_limit_per_min,
            window_seconds=60.0,
        )
        if not allowed:
            security_telemetry.emit_event(
                "RATE_LIMIT_BLOCKED",
                severity="WARNING",
                details={"client": client_id, "path": path, "reason": "API_RATE_LIMIT_EXCEEDED"},
            )
            security_telemetry.record_http_response(429)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "تم تجاوز الحد المسموح لمعدل الطلبات في الدقيقة (API Rate Limit Exceeded)."
                },
                headers={"Retry-After": str(retry_after)},
            )

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    response.headers["X-Trilunair-Execution-Mode"] = "PAPER-LOCKED"
    if not path.startswith("/docs") and not path.startswith("/redoc"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "media-src 'self' data: blob:; "
            "connect-src 'self' ws: wss: http: https:; "
            "frame-ancestors 'none';"
        )
    if os.getenv("TRILUNAIR_ENV", "development").lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    security_telemetry.record_http_response(response.status_code)
    return response


# ==============================================================================
# 1. نقاط نهاية الفحص الصحي وحالة النظام والحوكمة الأمنية (/api/health, /api/system, /api/auth)
# ==============================================================================


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    """فحص الجاهزية التشغيلية للخادم وحالة وضع التداول الورقي المقفل."""
    init_db()
    status = get_system_status()
    return {
        "status": "ok",
        "appName": status.appName,
        "version": status.version,
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "executionLockedToPaper": True,
        "marketDataMode": status.marketDataMode,
        "killSwitchActive": status.killSwitchActive,
        "timestamp": utc_now_iso(),
    }


@app.get("/api/system/status", response_model=SystemStatus)
def api_system_status() -> SystemStatus:
    """استرجاع حالة النظام الكاملة والفحوصات الأمنية الخمسة ومزودي الخدمة وسياسة المخاطر الموحدة."""
    init_db()
    return get_system_status()


@app.get("/api/system/infrastructure")
def api_system_infrastructure() -> dict[str, Any]:
    """فحص اتصال واستدامة قاعدة البيانات (PostgreSQL / SQLite) وذاكرة Redis وحداثة بث السوق."""
    init_db()
    infra = check_infrastructure_status()
    infra["marketFeed"] = market_engine.get_feed_health()
    infra["binancePublicMarketData"] = binance_public_client.get_health_snapshot()
    infra["timestamp"] = utc_now_iso()
    return infra


def _inspect_frontend_bundle_state() -> dict[str, Any]:
    candidate_dirs = [
        Path(__file__).resolve().parents[2] / "frontend" / "dist",
        Path("/app/frontend/dist"),
    ]
    dist_dir = next((d for d in candidate_dirs if (d / "index.html").is_file()), None)
    if dist_dir is not None:
        asset_files = list((dist_dir / "assets").glob("*")) if (dist_dir / "assets").is_dir() else []
        return {
            "status": "READY",
            "servingStaticSpa": True,
            "bundleAssetCount": len(asset_files),
            "messageAr": "حزمة الواجهة الأمامية المبنية (React SPA) جاهزة ومخدومة مباشرة.",
            "messageEn": "Production React SPA bundle is built and ready.",
        }
    return {
        "status": "DEV_PROXY_MODE",
        "servingStaticSpa": False,
        "bundleAssetCount": 0,
        "messageAr": "الواجهة تعمل عبر خادم التطوير المستقل (Vite) دون حزمة dist محلية.",
        "messageEn": "Frontend running via standalone Vite dev server (no local dist bundle mounted).",
    }


def _inspect_reconciliation_state() -> dict[str, Any]:
    portfolio = get_portfolio_snapshot()
    uncertain = False
    last_reconciled_at = utc_now_iso()
    try:
        with db_session() as conn:
            row = conn.execute(
                "SELECT account_state_uncertain, last_reconciled_at FROM quantum_governance WHERE tenant_id = 'admin-primary'"
            ).fetchone()
            if row is not None:
                uncertain = bool(row["account_state_uncertain"])
                last_reconciled_at = str(row["last_reconciled_at"])
    except Exception:
        pass

    computed_positions_value = sum(pos.marketValueUsd for pos in portfolio.positions)
    computed_total = round(portfolio.cashBalance + computed_positions_value, 2)
    drift_usd = round(abs(computed_total - portfolio.totalEquity), 4)
    consistent = (not uncertain) and (drift_usd <= 0.05)
    return {
        "status": "RECONCILED" if consistent else "UNCERTAIN_HALTED",
        "consistent": consistent,
        "accountStateUncertain": uncertain,
        "equityDriftUsd": drift_usd,
        "cashBalanceUsd": portfolio.cashBalance,
        "positionsMarketValueUsd": round(computed_positions_value, 2),
        "totalEquityUsd": portfolio.totalEquity,
        "lastReconciledAt": last_reconciled_at,
    }


@app.get("/api/system/operations")
def api_system_operations() -> dict[str, Any]:
    """
    لوحة العمليات والمراقبة السحابية الموحدة (Cloud Operations & Monitoring — القسم 13).
    تُرجع حالة حقيقية وشفافة لكل مكون دون تصنيف أي خدمة محاكاة على أنها اتصال خارجي حي.
    """
    init_db()
    sys_status = get_system_status()
    infra = check_infrastructure_status()
    feed_health = market_engine.get_feed_health()
    binance_snap = binance_public_client.get_health_snapshot()
    ai_providers = get_provider_credentials_report()
    voice_status = get_voice_subsystem_status()
    auth_cfg = get_admin_auth_config_state()
    sec_metrics = security_telemetry.snapshot()
    reconciliation = _inspect_reconciliation_state()
    frontend_bundle = _inspect_frontend_bundle_state()

    db_engine = str(infra["database"].get("engine", "sqlite")).lower()
    db_connected = bool(infra["database"].get("connected"))
    if db_engine == "postgresql" and db_connected:
        db_status = "CONNECTED"
    elif db_engine == "sqlite" and db_connected:
        db_status = "SIMULATED_LOCAL_SQLITE"
    else:
        db_status = "OFFLINE"

    redis_mode = str(infra["redis"].get("mode", "unconfigured"))
    if infra["redis"].get("connected") and redis_mode == "redis-native-tcp":
        redis_status = "CONNECTED"
    elif infra["redis"].get("connected"):
        redis_status = "MOCK_TCP_RESP"
    else:
        redis_status = "SIMULATED_IN_PROCESS"

    mkt_mode = os.getenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED").strip().upper()
    if mkt_mode != "LIVE_PUBLIC":
        binance_rest_state = "SIMULATED"
        binance_ws_state = "SIMULATED"
    else:
        binance_rest_state = "CONNECTED" if binance_snap.get("restHealthy") else "DEGRADED"
        if binance_snap.get("wsConnected"):
            binance_ws_state = "CONNECTED"
        elif binance_snap.get("restHealthy"):
            binance_ws_state = "FALLBACK_REST_POLLING"
        else:
            binance_ws_state = "OFFLINE"

    cloud_ai_connected_count = sum(
        1 for p in ai_providers if p["providerId"] != "local-quant-engine" and p["available"]
    )

    return {
        "releaseVersion": APP_VERSION,
        "timestamp": utc_now_iso(),
        "environment": os.getenv("TRILUNAIR_ENV", "development"),
        "executionSafety": {
            "tradingMode": "PAPER",
            "liveAuthorized": False,
            "executionLockedToPaper": True,
            "autonomousLiveTradingDisabled": True,
            "realOrdersPermitted": False,
            "withdrawalsPermitted": False,
            "marginAndLeveragePermitted": False,
            "killSwitchActive": sys_status.killSwitchActive,
            "killSwitchReason": getattr(sys_status, "killSwitchReason", None),
            "policyMatrix": binance_snap.get("policyMatrix", {}),
        },
        "adminSecurity": {
            "authConfigured": auth_cfg["configured"],
            "authMode": auth_cfg["mode"],
            "failClosedActive": True,
            "defaultTestPinsRemoved": True,
            "corsAllowedOrigins": get_allowed_cors_origins(),
            "metrics": sec_metrics,
        },
        "riskPolicy": sys_status.riskPolicy.model_dump(),
        "subsystems": {
            "frontend": frontend_bundle,
            "backendApi": {
                "status": "CONNECTED",
                "version": APP_VERSION,
                "uptimeSeconds": sec_metrics["uptimeSeconds"],
                "serverErrorRatePct": sec_metrics["serverErrorRatePct"],
                "totalHttpRequests": sec_metrics["totalHttpRequests"],
            },
            "postgresql": {
                "status": db_status,
                "activeBackend": db_engine.upper(),
                "configuredEngine": db_engine.upper(),
                "latencyMs": infra["database"].get("latencyMs", 0.0),
                "persistent": bool(infra["database"].get("persistenceVerified")),
            },
            "redis": {
                "status": redis_status,
                "connected": bool(infra["redis"].get("connected")),
                "mode": redis_mode,
                "latencyMs": infra["redis"].get("latencyMs", 0.0),
            },
            "binancePublicMarketData": {
                "marketDataMode": mkt_mode,
                "restStatus": binance_rest_state,
                "wsStatus": binance_ws_state,
                "feedFresh": feed_health["fresh"],
                "ageSeconds": feed_health["ageSeconds"],
                "usedWeight1m": binance_snap.get("usedWeight1m", 0),
                "rateLimited": binance_snap.get("rateLimited", False),
                "lastRestError": binance_snap.get("lastRestError"),
                "lastWsError": binance_snap.get("lastWsError"),
                "orderbookSync": binance_snap.get("orderbookSync", {}),
            },
            "aiProviders": {
                "cloudConnectedCount": cloud_ai_connected_count,
                "localDeterministicEngineActive": True,
                "providers": ai_providers,
            },
            "voiceServices": voice_status,
            "webSocketHub": {
                "status": "ACTIVE" if ws_manager.broadcaster_running or len(ws_manager.active_connections) > 0 else "IDLE_READY",
                "broadcasterRunning": ws_manager.broadcaster_running,
                "activeClientConnections": len(ws_manager.active_connections),
                "totalOpened": sec_metrics["wsConnectionsOpened"],
                "totalRejected": sec_metrics["wsConnectionsRejected"],
            },
            "accountReconciliation": reconciliation,
        },
    }


@app.post("/api/auth/session/login")
def api_admin_session_login(
    request: Request,
    response: Response,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """إنشاء جلسة مسؤول موقعة ومحددة الصلاحية بعد التحقق من سر المسؤول عبر PBKDF2-HMAC-SHA256."""
    init_db()
    client_id = get_client_identifier(request)
    candidate_secret = str(
        payload.get("adminSecret")
        or payload.get("password")
        or payload.get("adminPin")
        or ""
    )
    enforce_admin_secret(candidate_secret, client_id=client_id, action_label="ADMIN_SESSION_LOGIN")
    session_data = create_admin_session(actor="ADMIN")
    set_session_cookie(response, session_data["sessionToken"], session_data["ttlSeconds"])
    append_audit_log(
        actor="ADMIN",
        source="AUTH_SESSION",
        action="ADMIN_SESSION_ESTABLISHED",
        severity="INFO",
        details_ar="تم إنشاء جلسة مسؤول مشفرة وموقعة بنجاح مع تفعيل حماية CSRF.",
        details_en="Established signed administrator session with HttpOnly cookie and CSRF token.",
    )
    return {
        "authenticated": True,
        "sessionToken": session_data["sessionToken"],
        "csrfToken": session_data["csrfToken"],
        "expiresAtEpoch": session_data["expiresAtEpoch"],
        "ttlSeconds": session_data["ttlSeconds"],
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "executionLockedToPaper": True,
    }


@app.post("/api/auth/session/logout")
def api_admin_session_logout(request: Request, response: Response) -> dict[str, Any]:
    """إبطال جلسة المسؤول الحالية ومسح ملف تعريف الارتباط."""
    auth_header = request.headers.get("authorization", "").strip()
    bearer_tok = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None
    cookie_tok = request.cookies.get(ADMIN_SESSION_COOKIE)
    revoked = revoke_session_token(bearer_tok or cookie_tok)
    clear_session_cookie(response)
    return {"authenticated": False, "revoked": revoked}


@app.get("/api/auth/session/status")
def api_admin_session_status(request: Request) -> dict[str, Any]:
    """التحقق من حالة جلسة المسؤول وتهيئة المصادقة في الخادم دون كشف أي أسرار."""
    cfg = get_admin_auth_config_state()
    auth_header = request.headers.get("authorization", "").strip()
    bearer_tok = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None
    cookie_tok = request.cookies.get(ADMIN_SESSION_COOKIE)
    claims = verify_session_token(bearer_tok or cookie_tok)
    return {
        "authenticated": claims is not None,
        "authConfigured": cfg["configured"],
        "authMode": cfg["mode"],
        "reasonAr": cfg["reasonAr"],
        "reasonEn": cfg["reasonEn"],
        "csrfToken": claims.get("csrf") if claims else None,
        "expiresAtEpoch": claims.get("exp") if claims else None,
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "executionLockedToPaper": True,
    }


@app.post("/api/auth/trading-mode", response_model=SystemStatus)
def api_set_trading_mode(payload: TradingModeRequest, request: Request) -> SystemStatus:
    """بوابة المسؤول لوضع التداول (الإصدار v1.1.0-cloud-paper يفرض البقاء في PAPER ويرفض LIVE نهائياً)."""
    init_db()
    return set_trading_mode(payload, client_id=get_client_identifier(request))


@app.post("/api/auth/kill-switch", response_model=SystemStatus)
def api_set_kill_switch(payload: KillSwitchRequest) -> SystemStatus:
    """تفعيل أو إلغاء مفتاح الإيقاف الطارئ (Emergency Kill Switch)."""
    init_db()
    return set_kill_switch(payload)


@app.get("/api/auth/audit-logs", response_model=list[AuditLogEntry])
def api_get_audit_logs(limit: int = Query(default=100, ge=1, le=500)) -> list[AuditLogEntry]:
    """استرجاع سجل التدقيق الأمني لكافة الأوامر والقرارات والتصاريح."""
    init_db()
    return [AuditLogEntry(**row) for row in fetch_audit_logs(limit=limit)]


# ==============================================================================
# 2. نقاط نهاية الأسواق والمحفظة والأوامر وفحص المخاطر (/api/market, /api/portfolio, /api/orders)
# ==============================================================================


@app.get("/api/market/assets", response_model=list[MarketAsset])
def api_get_market_assets() -> list[MarketAsset]:
    """استرجاع قائمة الأصول الستة المتداولة مع أسعارها ومؤشرات التقلب والسيولة ومصدر البيانات."""
    return market_engine.get_assets()


@app.get("/api/market/binance-status")
def api_market_binance_status() -> dict[str, Any]:
    """فحص حالة موصل بيانات السوق العامة لـ Binance Spot ومزامنة دفتر الأوامر."""
    return binance_public_client.get_health_snapshot()


@app.post("/api/market/feed-control")
def api_market_feed_control(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """التحكم في محاكاة تقادم بيانات السوق واستعادتها لأغراض اختبار الجاهزية والتعافي."""
    action = str(payload.get("action") or "status").strip().lower()
    if action in {"stale", "resume"} and os.getenv("TRILUNAIR_ENV", "development").lower() == "production":
        require_authenticated_session_or_secret(
            request,
            provided_secret=str(payload.get("adminSecret") or payload.get("adminPin") or ""),
            action_label="MARKET_FEED_CONTROL",
        )
    if action == "stale":
        age = float(payload.get("ageSeconds") or 120.0)
        return market_engine.simulate_stale_feed(age_seconds=age)
    if action == "resume":
        return market_engine.resume_feed()
    return market_engine.get_feed_health()


@app.get("/api/market/candles/{symbol}", response_model=MarketCandlesResponse)
def api_get_market_candles(
    symbol: str,
    timeframe: str = Query(default="15m"),
    limit: int = Query(default=90, ge=10, le=240),
) -> MarketCandlesResponse:
    """استرجاع الشموع اليابانية OHLCV ومستويات الدعم والمقاومة وعمق دفتر الأوامر."""
    candles_resp = market_engine.get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
    if candles_resp is None:
        raise HTTPException(
            status_code=404,
            detail=f"الأصل المطلوب غير موجود: {symbol}",
        )
    return candles_resp


@app.get("/api/portfolio", response_model=PortfolioSnapshot)
def api_get_portfolio() -> PortfolioSnapshot:
    """استرجاع لقطة المحفظة المالية الورقية والمراكز المفتوحة ومؤشرات التريليون والمخاطر."""
    init_db()
    return get_portfolio_snapshot()


@app.post("/api/orders/propose", response_model=TradeProposalEvaluation)
def api_propose_order(proposal: TradeProposalInput) -> TradeProposalEvaluation:
    """تقييم وحفظ مقترح صفقة مهيكل عبر المدقق ومحرك المخاطر الحتمي دون تنفيذ فوري."""
    init_db()
    return propose_order(proposal)


@app.post("/api/orders/execute", response_model=OrderExecuteResponse)
def api_execute_order(payload: OrderExecuteRequest) -> OrderExecuteResponse:
    """تنفيذ مقترح صفقة ورقي معتمد بعد التأكيد الصريح من المستخدم والتحقق الأمني الكامل."""
    init_db()
    return execute_order(payload)


# ==============================================================================
# 3. نقاط نهاية محرك السمات الهولوغرامية المستديم (/api/themes)
# ==============================================================================


@app.get("/api/themes", response_model=ThemesPayload)
def api_get_themes() -> ThemesPayload:
    """استرجاع السمات الست الأساسية والسمات المخصصة والإعداد النشط."""
    init_db()
    return get_themes_payload()


@app.put("/api/themes/active", response_model=ActiveThemeState)
def api_put_active_theme(state: ActiveThemeState) -> ActiveThemeState:
    """حفظ السمة النشطة وتخصيصات الألوان ومعاملات الأداء والوصول."""
    init_db()
    return save_active_theme_state(state)


@app.post("/api/themes/custom", response_model=ThemeDefinition)
def api_post_custom_theme(theme: ThemeDefinition) -> ThemeDefinition:
    """حفظ سمة مخصصة جديدة أو تحديثها في قاعدة البيانات."""
    init_db()
    return save_custom_theme(theme)


@app.delete("/api/themes/custom/{theme_id}")
def api_delete_custom_theme(theme_id: str) -> dict[str, bool]:
    """حذف سمة مخصصة محفوظة."""
    init_db()
    return delete_custom_theme(theme_id)


@app.post("/api/themes/import", response_model=ThemeDefinition)
def api_import_theme(config_payload: dict[str, Any] = Body(...)) -> ThemeDefinition:
    """التحقق من صلاحية ملف JSON للسمة المستوردة وحفظها."""
    init_db()
    return import_theme_config(config_payload)


# ==============================================================================
# 4. نقاط نهاية الذكاء الاصطناعي ومجلس الوكلاء والصوت (/api/ai, /api/voice)
# ==============================================================================


@app.get("/api/ai/agents", response_model=list[AgentProfile])
def api_get_agents() -> list[AgentProfile]:
    """استرجاع قائمة الوكلاء الخمسة المتخصصين وأدوارهم."""
    return get_agents()


@app.get("/api/ai/providers/health")
def api_get_ai_providers_health() -> dict[str, Any]:
    """استرجاع الحالة التشغيلية الحقيقية لمزودات الذكاء الاصطناعي الخمسة وإحصاءات الكمون والأخطاء."""
    providers = get_provider_credentials_report()
    return {
        "timestamp": utc_now_iso(),
        "providers": providers,
    }


@app.get("/api/ai/history")
def api_get_ai_history() -> dict[str, Any]:
    """استرجاع سجل المحادثات وآخر اجتماع منعقد لمجلس الوكلاء."""
    init_db()
    return get_chat_history()


@app.delete("/api/ai/history")
def api_clear_ai_history() -> dict[str, bool]:
    """مسح سجل المحادثات من غرفة الأوامر."""
    init_db()
    return clear_chat_history()


@app.post("/api/ai/command", response_model=AiCommandResponse)
def api_post_ai_command(payload: AiCommandRequest) -> AiCommandResponse:
    """معالجة أمر صوتي (VOICE) أو نصي (TEXT) باللغتين العربية والإنجليزية."""
    init_db()
    return process_ai_command(payload)


@app.post("/api/ai/meeting", response_model=AgentMeetingResult)
def api_post_ai_meeting(payload: ConveneMeetingRequest) -> AgentMeetingResult:
    """عقد اجتماع طاولة مستديرة مخصص للوكلاء الخمسة حول أصل مالي معين."""
    init_db()
    return convene_meeting(
        symbol=payload.symbol,
        horizon=payload.horizon,
        language=payload.language,
    )


@app.post("/api/voice/stt")
async def api_voice_stt(request: Request) -> dict[str, Any]:
    """نقطة نهاية تحويل الصوت إلى نص (Whisper السحابي عند توفر المفتاح أو تكامل المتصفح المتوافق مع Safari)."""
    return await handle_stt_request(request)


@app.post("/api/voice/tts")
async def api_voice_tts(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
    raw: bool = Query(default=False),
) -> Any:
    """توليد استجابة صوتية بصيغة RIFF WAV صالحة أو إرجاع البيانات الوصفية المرمزة بـ Base64."""
    wav_bytes, media_type, metadata = await handle_tts_request(payload)
    accept_header = (request.headers.get("accept") or "").lower()
    if raw or str(payload.get("format") or "").lower() == "wav" or "audio/wav" in accept_header:
        return Response(content=wav_bytes, media_type=media_type)
    return metadata


# ==============================================================================
# 5. البث الحي لبيانات السوق والمحفظة عبر WebSocket (/ws/market)
# ==============================================================================


def _is_ws_origin_allowed(websocket: WebSocket) -> bool:
    """التحقق من أصل اتصال WebSocket في بيئة الإنتاج لمنع اختطاف الجلسات عبر المواقع (CSWSH)."""
    if os.getenv("TRILUNAIR_ENV", "development").lower() != "production":
        return True
    origin = (websocket.headers.get("origin") or "").strip().rstrip("/")
    if not origin:
        return True
    allowed = set(get_allowed_cors_origins())
    host = (websocket.headers.get("host") or "").strip()
    if host:
        allowed.add(f"https://{host}")
        allowed.add(f"http://{host}")
    return origin in allowed


@app.websocket("/ws/market")
async def websocket_market_stream(websocket: WebSocket) -> None:
    """بث تحديثات الأسعار الحية (MARKET_TICK) وإجمالي حقوق الملكية كل 1.5 ثانية."""
    if not _is_ws_origin_allowed(websocket):
        with security_telemetry._lock:
            security_telemetry.ws_connections_rejected += 1
        security_telemetry.emit_event(
            "WS_ORIGIN_REJECTED",
            severity="WARNING",
            details={"origin": websocket.headers.get("origin", "")},
        )
        await websocket.close(code=1008)
        return

    if os.getenv("TRILUNAIR_WS_REQUIRE_AUTH", "false").lower() == "true":
        token = websocket.query_params.get("token") or websocket.cookies.get(ADMIN_SESSION_COOKIE)
        if verify_session_token(token) is None:
            with security_telemetry._lock:
                security_telemetry.ws_connections_rejected += 1
            await websocket.close(code=1008)
            return

    init_db()
    await ws_manager.connect(websocket)
    try:
        initial_tick = ws_manager.build_tick_payload(step_prices=True)
        await websocket.send_json(initial_tick)

        while True:
            try:
                client_msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.5)
                if client_msg.strip().lower() in ("ping", "tick"):
                    await websocket.send_json(ws_manager.build_tick_payload(step_prices=True))
            except asyncio.TimeoutError:
                if not ws_manager.broadcaster_running:
                    await websocket.send_json(ws_manager.build_tick_payload(step_prices=True))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# ==============================================================================
# 6. تقديم الواجهة الأمامية المبنية اختيارياً عند وجود frontend/dist (الإنتاج / Docker)
# ==============================================================================


def _configure_optional_spa_serving(fastapi_app: FastAPI) -> None:
    """تركيب خدمة الملفات الثابتة للواجهة الأمامية في حال وجود حزمة البناء frontend/dist."""
    candidate_dirs = [
        Path(__file__).resolve().parents[2] / "frontend" / "dist",
        Path("/app/frontend/dist"),
    ]
    dist_dir = next((d for d in candidate_dirs if (d / "index.html").is_file()), None)
    if dist_dir is None:
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        fastapi_app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="frontend-assets",
        )

    @fastapi_app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not Found")
        requested_file = (dist_dir / full_path).resolve()
        if str(requested_file).startswith(str(dist_dir.resolve())) and requested_file.is_file():
            return FileResponse(str(requested_file))
        return FileResponse(str(dist_dir / "index.html"))


try:
    from app.quantum_hub import router as quantum_router

    app.include_router(quantum_router)
except Exception:
    pass

_configure_optional_spa_serving(app)

