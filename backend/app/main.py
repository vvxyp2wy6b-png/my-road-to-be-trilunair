"""
نقطة الدخول الرئيسية لتطبيق الخادم الخلفي (FastAPI + WebSocket).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

يربط هذا الخادم كافة الوحدات المعمارية تحت المسار /api/... بالإضافة إلى البث الحي عبر /ws/market،
مع تقديم ملفات الواجهة الأمامية المبنية (SPA) تلقائياً عند وجود المجلد frontend/dist.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents_council import (
    clear_chat_history,
    convene_meeting,
    get_agents,
    get_chat_history,
    process_ai_command,
)
from app.database import fetch_audit_logs, init_db, utc_now_iso
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
    execute_order,
    get_portfolio_snapshot,
    get_system_status,
    propose_order,
    set_kill_switch,
    set_trading_mode,
)
from app.themes_service import (
    delete_custom_theme,
    get_themes_payload,
    import_theme_config,
    save_active_theme_state,
    save_custom_theme,
)
from app.voice_service import handle_stt_request, handle_tts_request


class MarketConnectionManager:
    """مدير اتصالات WebSocket للبث المتزامن لنبضات السوق الحية (/ws/market)."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self.broadcaster_running: bool = False

    async def connect(self, websocket: WebSocket) -> None:
        """قبول اتصال عميل جديد وإضافته إلى مجموعة البث النشطة."""
        await websocket.accept()
        self.active_connections.add(websocket)

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
    """مدير دورة حياة التطبيق لتهيئة قاعدة البيانات وتشغيل حلقة البث الحي."""
    init_db()
    try:
        from app.quantum_hub import ensure_quantum_tables

        ensure_quantum_tables()
    except Exception:
        pass
    broadcaster_task = asyncio.create_task(_market_broadcast_loop())
    try:
        yield
    finally:
        broadcaster_task.cancel()
        try:
            await broadcaster_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="My Road to be Trilunair Dr.MaJoOoOoOoD — Holographic Command API",
    description="الخادم الخلفي لمركز القيادة الهولوغرامي، بوابة الأمان المالي، ومحرك الوكلاء الخمسة.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 1. نقاط نهاية الفحص الصحي وحالة النظام والحوكمة الأمنية (/api/health, /api/system, /api/auth)
# ==============================================================================


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    """فحص الجاهزية التشغيلية للخادم وحالة وضع التداول الحالي."""
    init_db()
    status = get_system_status()
    return {
        "status": "ok",
        "appName": status.appName,
        "version": status.version,
        "tradingMode": status.tradingMode,
        "killSwitchActive": status.killSwitchActive,
        "timestamp": utc_now_iso(),
    }


@app.get("/api/system/status", response_model=SystemStatus)
def api_system_status() -> SystemStatus:
    """استرجاع حالة النظام الكاملة والفحوصات الأمنية الخمسة ومزودي الخدمة."""
    init_db()
    return get_system_status()


@app.post("/api/auth/trading-mode", response_model=SystemStatus)
def api_set_trading_mode(payload: TradingModeRequest) -> SystemStatus:
    """بوابة المسؤول لتبديل وضع التداول بين الورقي (PAPER) والحقيقي (LIVE)."""
    init_db()
    return set_trading_mode(payload)


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
    """استرجاع قائمة الأصول الستة المتداولة مع أسعارها ومؤشرات التقلب والسيولة."""
    return market_engine.get_assets()


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
    """استرجاع لقطة المحفظة المالية الحية والمراكز المفتوحة ومؤشرات التريليون والمخاطر."""
    init_db()
    return get_portfolio_snapshot()


@app.post("/api/orders/propose", response_model=TradeProposalEvaluation)
def api_propose_order(proposal: TradeProposalInput) -> TradeProposalEvaluation:
    """تقييم وحفظ مقترح صفقة مهيكل عبر المدقق ومحرك المخاطر الحتمي دون تنفيذ فوري."""
    init_db()
    return propose_order(proposal)


@app.post("/api/orders/execute", response_model=OrderExecuteResponse)
def api_execute_order(payload: OrderExecuteRequest) -> OrderExecuteResponse:
    """تنفيذ مقترح صفقة معتمد بعد التأكيد الصريح من المستخدم والتحقق الأمني الكامل."""
    init_db()
    return execute_order(payload)


# ==============================================================================
# 3. نقاط نهاية محرك السمات الهولوغرامية المستديم (/api/themes)
# ==============================================================================


@app.get("/api/themes", response_model=ThemesPayload)
def api_get_themes() -> ThemesPayload:
    """استرجاع السمات الخمس الأساسية والسمات المخصصة والإعداد النشط."""
    init_db()
    return get_themes_payload()


@app.put("/api/themes/active", response_model=ActiveThemeState)
def api_put_active_theme(state: ActiveThemeState) -> ActiveThemeState:
    """حفظ السمة النشطة وتخصيصات الألوان ومعاملات الأداء والوصول."""
    init_db()
    return save_active_theme_state(state)


@app.post("/api/themes/custom", response_model=ThemeDefinition)
def api_post_custom_theme(theme: ThemeDefinition) -> ThemeDefinition:
    """حفظ سمة مخصصة جديدة أو تحديثها في قاعدة بيانات SQLite."""
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
    """نقطة نهاية تحويل الصوت إلى نص (Whisper السحابي عند توفر المفتاح أو تكامل المتصفح)."""
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


@app.websocket("/ws/market")
async def websocket_market_stream(websocket: WebSocket) -> None:
    """بث تحديثات الأسعار الحية (MARKET_TICK) وإجمالي حقوق الملكية كل 1.5 ثانية."""
    init_db()
    await ws_manager.connect(websocket)
    try:
        # إرسال لقطة فورية عند فتح الاتصال مباشرة لضمان استجابة لحظية للواجهة والاختبارات
        initial_tick = ws_manager.build_tick_payload(step_prices=True)
        await websocket.send_json(initial_tick)

        while True:
            try:
                client_msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.5)
                if client_msg.strip().lower() in ("ping", "tick"):
                    await websocket.send_json(ws_manager.build_tick_payload(step_prices=True))
            except asyncio.TimeoutError:
                # في حال عدم تشغيل حلقة البث المركزية (مثل بيئات الاختبار المعزولة)، نبث النبضة مباشرة
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

