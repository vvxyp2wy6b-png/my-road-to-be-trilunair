"""
عميل بيانات السوق العامة الفورية لبورصة Binance Spot (Public Market Data Only — Zero Order Execution).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.1.0-cloud-paper

المسؤوليات والضوابط الصارمة:
1. الاتصال بنقاط النهاية العامة الرسمية لبورصة Binance Spot بدون مفاتيح API خاصة بالتداول:
   - REST الأساسي: https://data-api.binance.vision/api/v3 (مع بديل https://api.binance.com/api/v3)
   - WebSocket الأساسي: wss://data-stream.binance.vision/stream (مع بديل wss://stream.binance.com:9443/stream)
2. توفير:
   - الأسعار الحية وحجم التداول لـ 24 ساعة وفارق العرض والطلب (/api/v3/ticker/24hr + @ticker)
   - الشموع اليابانية OHLCV (/api/v3/klines)
   - عمق دفتر الأوامر مع مزامنة أرقام التسلسل الرسمية lastUpdateId / U / u (/api/v3/depth + @depth)
   - اكتشاف الرموز وفلاتر التداول القياسية PRICE_FILTER و LOT_SIZE و NOTIONAL (/api/v3/exchangeInfo)
   - مراقبة صحة الاتصال، إعادة الاتصال التلقائي الأسي، فحص حداثة البيانات، واحترام حدود المعدل (HTTP 429 / 418).
3. حظر بنيوي قاطع لأي تنفيذ أوامر حقيقية:
   - لا يحتوي هذا الملف على أي نقطة نهاية لتنفيذ الأوامر أو السحب أو الاقتراض أو الهامش أو العقود الآجلة.
   - يظل التنفيذ ورقياً محاكياً حصراً (PAPER_EXECUTION).
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from typing import Any, Final
import urllib.parse

from app.models import CandlePoint, OrderbookLevel
from app.security import build_outbound_ssl_context, create_outbound_http_client, security_telemetry

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None  # type: ignore[assignment]

# خريطة الرموز المعتمدة في المنصة إلى أزواج Binance Spot العامة الحقيقية
CANONICAL_TO_BINANCE_SPOT: Final[dict[str, str]] = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT",
}
BINANCE_TO_CANONICAL: Final[dict[str, str]] = {v: k for k, v in CANONICAL_TO_BINANCE_SPOT.items()}

VALID_KLINE_INTERVALS: Final[dict[str, str]] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


class OrderBookSynchronizer:
    """
    مزامن دفتر الأوامر المتوافق مع بروتوكول Binance الرسمي:
    يتحقق من تسلسل التحديثات التفاضلية (U <= lastUpdateId + 1 <= u) ويكتشف فجوات التسلسل لإعادة أخذ اللقطة.
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.last_update_id: int = 0
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}
        self.synced: bool = False
        self.sequence_gaps_detected: int = 0
        self.updated_at_epoch: float = 0.0

    def apply_snapshot(
        self,
        last_update_id: int,
        bids_raw: list[list[str | float]],
        asks_raw: list[list[str | float]],
    ) -> None:
        self.last_update_id = int(last_update_id)
        self.bids = {float(p): float(q) for p, q in bids_raw if float(q) > 0}
        self.asks = {float(p): float(q) for p, q in asks_raw if float(q) > 0}
        self.synced = True
        self.updated_at_epoch = time.time()

    def apply_diff_event(self, event: dict[str, Any]) -> bool:
        """
        تطبيق حدث تحديث عمق دفتر الأوامر (depthUpdate):
        - يتجاهل الأحداث القديمة حيث u <= lastUpdateId.
        - إذا كان U > lastUpdateId + 1 فهناك فجوة تسلسل -> يعيد False لإعادة طلب اللقطة الكاملة.
        """
        if not self.synced:
            return False
        first_id = int(event.get("U", 0))
        final_id = int(event.get("u", 0))
        if final_id <= self.last_update_id:
            return True
        if first_id > self.last_update_id + 1:
            self.synced = False
            self.sequence_gaps_detected += 1
            return False

        for price_s, qty_s in event.get("b", []):
            price, qty = float(price_s), float(qty_s)
            if qty <= 0.0:
                self.bids.pop(price, None)
            else:
                self.bids[price] = qty

        for price_s, qty_s in event.get("a", []):
            price, qty = float(price_s), float(qty_s)
            if qty <= 0.0:
                self.asks.pop(price, None)
            else:
                self.asks[price] = qty

        self.last_update_id = final_id
        self.updated_at_epoch = time.time()
        return True

    def top_levels(self, depth: int = 8, decimals: int = 2) -> tuple[list[OrderbookLevel], list[OrderbookLevel]]:
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:depth]
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])[:depth]

        bids_out: list[OrderbookLevel] = []
        cum_b = 0.0
        for p, q in sorted_bids:
            cum_b += q
            bids_out.append(
                OrderbookLevel(
                    price=round(p, decimals),
                    size=round(q, 5),
                    total=round(cum_b, 5),
                )
            )

        asks_out: list[OrderbookLevel] = []
        cum_a = 0.0
        for p, q in sorted_asks:
            cum_a += q
            asks_out.append(
                OrderbookLevel(
                    price=round(p, decimals),
                    size=round(q, 5),
                    total=round(cum_a, 5),
                )
            )
        return bids_out, asks_out


class BinanceSpotPublicDataClient:
    """
    عميل بيانات السوق العامة لبورصة Binance Spot مع دعم كل من REST و WebSocket،
    التبديل التلقائي عند حظر WebSocket في البيئات المحمية بالوكيل، واحترام حدود الوزن (Rate Limits).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tickers_cache: dict[str, dict[str, Any]] = {}
        self._exchange_filters: dict[str, dict[str, Any]] = {}
        self._orderbooks: dict[str, OrderBookSynchronizer] = {
            bsym: OrderBookSynchronizer(bsym) for bsym in CANONICAL_TO_BINANCE_SPOT.values()
        }
        self._klines_cache: dict[tuple[str, str, int], tuple[float, list[CandlePoint]]] = {}

        self._used_weight_1m: int = 0
        self._rate_limited_until_epoch: float = 0.0
        self._last_rest_success_epoch: float = 0.0
        self._last_ws_message_epoch: float = 0.0
        self._ws_connected: bool = False
        self._ws_reconnect_attempts: int = 0
        self._last_error: str | None = None
        self._active_rest_base: str = self.get_rest_candidates()[0]
        self._ws_task: asyncio.Task[Any] | None = None

    @staticmethod
    def get_configured_mode() -> str:
        """
        أوضاع بيانات السوق المدعومة:
        - SIMULATED: محاكاة حتمية محلية (الافتراضي أثناء اختبارات الوحدة لضمان الحتمية الحسابية)
        - LIVE_PUBLIC: جلب بيانات حقيقية من Binance Spot Public API مع التراجع المعلن عند انقطاع الشبكة
        - AUTO: جلب حي عند التشغيل السحابي أو المحلي الفعلي
        """
        raw = os.getenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED").strip().upper()
        if raw in {"LIVE", "LIVE_PUBLIC", "BINANCE_PUBLIC", "AUTO"}:
            return "LIVE_PUBLIC"
        return "SIMULATED"

    @staticmethod
    def get_rest_candidates() -> list[str]:
        custom = os.getenv("BINANCE_PUBLIC_REST_URL", "").strip().rstrip("/")
        if custom:
            return [custom]
        return [
            "https://data-api.binance.vision",
            "https://api.binance.com",
        ]

    @staticmethod
    def get_ws_url() -> str:
        custom = os.getenv("BINANCE_PUBLIC_WS_URL", "").strip().rstrip("/")
        if custom:
            return custom
        streams = "/".join(
            f"{bsym.lower()}@ticker/{bsym.lower()}@depth@1000ms"
            for bsym in CANONICAL_TO_BINANCE_SPOT.values()
        )
        return f"wss://data-stream.binance.vision/stream?streams={streams}"

    def is_rate_limited(self) -> bool:
        with self._lock:
            return time.time() < self._rate_limited_until_epoch or self._used_weight_1m >= 5500

    def _record_headers_and_status(self, status_code: int, headers: Any) -> None:
        weight_raw = headers.get("x-mbx-used-weight-1m") or headers.get("X-MBX-USED-WEIGHT-1M")
        retry_after_raw = headers.get("retry-after") or headers.get("Retry-After")
        with self._lock:
            if weight_raw and str(weight_raw).isdigit():
                self._used_weight_1m = int(weight_raw)
            if status_code in {429, 418}:
                backoff = float(retry_after_raw) if (retry_after_raw and str(retry_after_raw).isdigit()) else (
                    120.0 if status_code == 418 else 30.0
                )
                self._rate_limited_until_epoch = time.time() + backoff
                self._last_error = f"HTTP_{status_code}_RATE_LIMIT_BACKOFF_{int(backoff)}S"
                security_telemetry.emit_event(
                    "BINANCE_PUBLIC_RATE_LIMITED",
                    severity="WARNING",
                    details={"statusCode": status_code, "backoffSeconds": backoff, "usedWeight1m": self._used_weight_1m},
                )

    def _rest_get(self, path: str, params: dict[str, Any] | None = None, timeout_sec: float = 5.0) -> Any | None:
        if self.is_rate_limited():
            return None

        for base in self.get_rest_candidates():
            url = f"{base}{path}"
            try:
                with create_outbound_http_client(url, timeout_sec=timeout_sec) as client:
                    resp = client.get(url, params=params)
                self._record_headers_and_status(resp.status_code, resp.headers)
                if resp.status_code == 451:
                    # قيد جغرافي على api.binance.com — الانتقال الفوري إلى data-api.binance.vision
                    continue
                if resp.status_code in {429, 418}:
                    return None
                resp.raise_for_status()
                data = resp.json()
                with self._lock:
                    self._active_rest_base = base
                    self._last_rest_success_epoch = time.time()
                    self._last_error = None
                return data
            except Exception as exc:
                with self._lock:
                    self._last_error = f"{type(exc).__name__}: {str(exc)[:140]}"
                continue
        return None

    def fetch_live_tickers(self) -> dict[str, dict[str, Any]]:
        """جلب بيانات 24 ساعة الحية (السعر، أعلى/أدنى، الحجم، العرض/الطلب، السبريد) لأزواج Binance Spot."""
        symbols_param = json.dumps(list(CANONICAL_TO_BINANCE_SPOT.values()), separators=(",", ":"))
        data = self._rest_get("/api/v3/ticker/24hr", params={"symbols": symbols_param})
        if not isinstance(data, list):
            return {}

        parsed: dict[str, dict[str, Any]] = {}
        now = time.time()
        for item in data:
            bsym = str(item.get("symbol", "")).upper()
            canonical = BINANCE_TO_CANONICAL.get(bsym)
            if not canonical:
                continue
            last_price = float(item.get("lastPrice") or 0.0)
            bid = float(item.get("bidPrice") or last_price)
            ask = float(item.get("askPrice") or last_price)
            high = float(item.get("highPrice") or last_price)
            low = float(item.get("lowPrice") or last_price)
            mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else max(last_price, 1e-9)
            spread_bps = round(max(0.1, ((ask - bid) / mid) * 10_000.0), 2) if ask >= bid else 1.0
            volatility_pct = round(max(0.3, ((high - low) / max(last_price, 1e-9)) * 100.0), 2)
            quote_vol = float(item.get("quoteVolume") or 0.0)
            change_pct = float(item.get("priceChangePercent") or 0.0)

            entry = {
                "canonicalSymbol": canonical,
                "binanceSymbol": bsym,
                "price": last_price,
                "bidPrice": bid,
                "askPrice": ask,
                "change24hPct": round(change_pct, 2),
                "high24h": high,
                "low24h": low,
                "volume24hUsd": round(quote_vol, 2),
                "volatilityPct": volatility_pct,
                "spreadBps": spread_bps,
                "updatedAtEpoch": now,
                "source": "BINANCE_PUBLIC_REST",
            }
            parsed[canonical] = entry

        if parsed:
            with self._lock:
                self._tickers_cache.update(parsed)
        return parsed

    def fetch_exchange_filters(self) -> dict[str, dict[str, Any]]:
        """اكتشاف الرموز وفلاتر التداول الرسمية من /api/v3/exchangeInfo."""
        symbols_param = json.dumps(list(CANONICAL_TO_BINANCE_SPOT.values()), separators=(",", ":"))
        data = self._rest_get("/api/v3/exchangeInfo", params={"symbols": symbols_param})
        if not isinstance(data, dict):
            return dict(self._exchange_filters)

        out: dict[str, dict[str, Any]] = {}
        for sym_obj in data.get("symbols", []):
            bsym = str(sym_obj.get("symbol", "")).upper()
            filters = {f.get("filterType"): f for f in sym_obj.get("filters", []) if isinstance(f, dict)}
            price_f = filters.get("PRICE_FILTER", {})
            lot_f = filters.get("LOT_SIZE", {})
            notional_f = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
            out[bsym] = {
                "binanceSymbol": bsym,
                "status": sym_obj.get("status", "TRADING"),
                "baseAsset": sym_obj.get("baseAsset", ""),
                "quoteAsset": sym_obj.get("quoteAsset", ""),
                "isSpotTradingAllowed": bool(sym_obj.get("isSpotTradingAllowed", True)),
                "tickSize": float(price_f.get("tickSize", 0.01)),
                "stepSize": float(lot_f.get("stepSize", 0.0001)),
                "minQty": float(lot_f.get("minQty", 0.0001)),
                "maxQty": float(lot_f.get("maxQty", 1000.0)),
                "minNotional": float(notional_f.get("minNotional", 10.0)),
                "fetchedAtEpoch": time.time(),
            }
        if out:
            with self._lock:
                self._exchange_filters.update(out)
        return out

    def fetch_klines(self, canonical_symbol: str, timeframe: str = "15m", limit: int = 90) -> list[CandlePoint] | None:
        """جلب الشموع اليابانية OHLCV الحقيقية من /api/v3/klines مع تخزين مؤقت قصير لمنع استنزاف الوزن."""
        bsym = CANONICAL_TO_BINANCE_SPOT.get(canonical_symbol)
        if not bsym:
            return None
        interval = VALID_KLINE_INTERVALS.get(timeframe, "15m")
        cache_key = (bsym, interval, limit)
        now = time.time()
        with self._lock:
            cached = self._klines_cache.get(cache_key)
            if cached and (now - cached[0]) < 8.0:
                return list(cached[1])

        raw = self._rest_get(
            "/api/v3/klines",
            params={"symbol": bsym, "interval": interval, "limit": min(max(limit, 10), 240)},
        )
        if not isinstance(raw, list) or not raw:
            return None

        candles: list[CandlePoint] = []
        for row in raw:
            if not isinstance(row, list) or len(row) < 6:
                continue
            candles.append(
                CandlePoint(
                    timestamp=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[7]) if len(row) > 7 else float(row[5]),
                )
            )
        if candles:
            with self._lock:
                self._klines_cache[cache_key] = (now, candles)
        return candles

    def fetch_orderbook_depth(
        self,
        canonical_symbol: str,
        limit: int = 10,
        decimals: int = 2,
    ) -> tuple[list[OrderbookLevel], list[OrderbookLevel], int | None] | None:
        """جلب عمق دفتر الأوامر المزامن عبر رقم التسلسل الرسمي lastUpdateId."""
        bsym = CANONICAL_TO_BINANCE_SPOT.get(canonical_symbol)
        if not bsym:
            return None

        sync = self._orderbooks[bsym]
        now = time.time()
        if sync.synced and (now - sync.updated_at_epoch) < 4.0 and sync.bids and sync.asks:
            b, a = sync.top_levels(depth=min(limit, 10), decimals=decimals)
            return b, a, sync.last_update_id

        valid_limit = 10 if limit <= 10 else 20
        snap = self._rest_get("/api/v3/depth", params={"symbol": bsym, "limit": valid_limit})
        if not isinstance(snap, dict) or "bids" not in snap or "asks" not in snap:
            return None

        sync.apply_snapshot(
            last_update_id=int(snap.get("lastUpdateId", 0)),
            bids_raw=snap["bids"],
            asks_raw=snap["asks"],
        )
        bids, asks = sync.top_levels(depth=min(limit, 8), decimals=decimals)
        return bids, asks, sync.last_update_id

    def handle_ws_stream_payload(self, raw_message: str | dict[str, Any]) -> bool:
        """معالجة رسائل WebSocket الواردة (@ticker و @depth) وتحديث حالة الأسعار ومزامنة دفتر الأوامر."""
        data = json.loads(raw_message) if isinstance(raw_message, str) else raw_message
        payload = data.get("data", data) if isinstance(data, dict) else {}
        if not isinstance(payload, dict):
            return False

        event_type = payload.get("e")
        bsym = str(payload.get("s", "")).upper()
        now = time.time()

        if event_type == "24hrTicker" and bsym in BINANCE_TO_CANONICAL:
            canonical = BINANCE_TO_CANONICAL[bsym]
            last_p = float(payload.get("c") or 0.0)
            bid = float(payload.get("b") or last_p)
            ask = float(payload.get("a") or last_p)
            high = float(payload.get("h") or last_p)
            low = float(payload.get("l") or last_p)
            mid = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else max(last_p, 1e-9)
            spread_bps = round(max(0.1, ((ask - bid) / mid) * 10_000.0), 2) if ask >= bid else 1.0
            vol_pct = round(max(0.3, ((high - low) / max(last_p, 1e-9)) * 100.0), 2)
            with self._lock:
                self._last_ws_message_epoch = now
                self._tickers_cache[canonical] = {
                    "canonicalSymbol": canonical,
                    "binanceSymbol": bsym,
                    "price": last_p,
                    "bidPrice": bid,
                    "askPrice": ask,
                    "change24hPct": round(float(payload.get("P") or 0.0), 2),
                    "high24h": high,
                    "low24h": low,
                    "volume24hUsd": round(float(payload.get("q") or 0.0), 2),
                    "volatilityPct": vol_pct,
                    "spreadBps": spread_bps,
                    "updatedAtEpoch": now,
                    "source": "BINANCE_PUBLIC_WS",
                }
            return True

        if event_type == "depthUpdate" and bsym in self._orderbooks:
            with self._lock:
                self._last_ws_message_epoch = now
            sync = self._orderbooks[bsym]
            if not sync.apply_diff_event(payload):
                # عند رصد فجوة تسلسل يتم طلب لقطة جديدة فوراً
                self.fetch_orderbook_depth(BINANCE_TO_CANONICAL[bsym], limit=10)
            return True

        return False

    async def run_ws_supervisor_loop(self) -> None:
        """
        مشرف اتصال WebSocket بخلفية النظام مع إعادة الاتصال التلقائي الأسي (Exponential Backoff)
        والتراجع السلس إلى الاستطلاع الدوري عبر REST عند حظر ترقية WebSocket في الوكيل الشبكي.
        """
        if websockets is None:
            return
        backoff = 1.5
        while True:
            if self.get_configured_mode() != "LIVE_PUBLIC":
                await asyncio.sleep(5.0)
                continue

            ws_url = self.get_ws_url()
            parsed = urllib.parse.urlparse(ws_url)
            is_local = parsed.hostname in {"127.0.0.1", "localhost"}
            ssl_ctx = build_outbound_ssl_context() if ws_url.startswith("wss://") and not is_local else None
            proxy = (
                None
                if is_local
                else (os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or None)
            )
            try:
                connect_kwargs: dict[str, Any] = {"open_timeout": 5.0, "ping_interval": 20.0}
                if ssl_ctx is not None:
                    connect_kwargs["ssl"] = ssl_ctx
                if proxy is not None:
                    connect_kwargs["proxy"] = proxy

                async with websockets.connect(ws_url, **connect_kwargs) as ws:
                    with self._lock:
                        self._ws_connected = True
                        self._ws_reconnect_attempts = 0
                    backoff = 1.5
                    async for raw_msg in ws:
                        self.handle_ws_stream_payload(raw_msg)
            except asyncio.CancelledError:
                with self._lock:
                    self._ws_connected = False
                raise
            except Exception as exc:
                with self._lock:
                    self._ws_connected = False
                    self._ws_reconnect_attempts += 1
                    self._last_error = f"WS_FALLBACK_TO_REST ({type(exc).__name__}: {str(exc)[:110]})"
                # تحديث فوري عبر REST لضمان استمرارية الأسعار الحية دون انقطاع
                await asyncio.to_thread(self.fetch_live_tickers)
                await asyncio.sleep(min(30.0, backoff))
                backoff = min(30.0, backoff * 1.8)

    def get_health_snapshot(self) -> dict[str, Any]:
        """تقرير تشغيلي صادق ومفصل لحالة بيانات سوق Binance Spot وفصلها القاطع عن التنفيذ الحقيقي."""
        mode = self.get_configured_mode()
        now = time.time()
        with self._lock:
            last_live = max(self._last_rest_success_epoch, self._last_ws_message_epoch)
            age = round(now - last_live, 2) if last_live > 0 else None
            live_active = mode == "LIVE_PUBLIC" and last_live > 0 and (age is not None and age <= 60.0)
            composite_mode = (
                "LIVE_MARKET_DATA_PAPER_EXECUTION"
                if live_active
                else "SIMULATED_MARKET_DATA_PAPER_EXECUTION"
            )
            return {
                "configuredMode": mode,
                "effectiveMatrixMode": composite_mode,
                "liveMarketDataActive": live_active,
                "executionMode": "PAPER",
                "liveExecutionPermitted": False,
                "restEndpoint": self._active_rest_base,
                "wsEndpoint": self.get_ws_url(),
                "wsConnected": self._ws_connected,
                "wsReconnectAttempts": self._ws_reconnect_attempts,
                "lastDataAgeSeconds": age,
                "usedWeight1m": self._used_weight_1m,
                "rateLimited": self.is_rate_limited(),
                "cachedLiveSymbols": sorted(self._tickers_cache.keys()),
                "syncedOrderbooks": {
                    bsym: {
                        "synced": ob.synced,
                        "lastUpdateId": ob.last_update_id,
                        "sequenceGaps": ob.sequence_gaps_detected,
                    }
                    for bsym, ob in self._orderbooks.items()
                },
                "lastError": self._last_error,
                "policyMatrix": {
                    "LIVE_MARKET_DATA_PLUS_PAPER_EXECUTION": "PERMITTED",
                    "SIMULATED_MARKET_DATA_PLUS_PAPER_EXECUTION": "PERMITTED",
                    "LIVE_MARKET_DATA_PLUS_LIVE_EXECUTION": "FORBIDDEN_PERMANENTLY_LOCKED",
                },
            }


binance_public_client = BinanceSpotPublicDataClient()
