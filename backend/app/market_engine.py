"""
محرك الأسواق الحية وتوليد الشموع اليابانية ودفتر الأوامر (Market Engine).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

يدعم ستة أصول استراتيجية متنوعة:
1. BTC-USD (بيتكوين مقابل الدولار - عملات رقمية)
2. ETH-USD (إيثيريوم مقابل الدولار - عملات رقمية)
3. NVDA (إنفيديا للذكاء الاصطناعي - أسهم عالمية)
4. XAU-USD (الذهب الفوري مقابل الدولار - سلع ومعادن نفيسة)
5. SOL-USD (سولانا مقابل الدولار - عملات رقمية)
6. ARAMCO.SR (أرامكو السعودية - أسهم الطاقة الإقليمية)
"""

from __future__ import annotations

import hashlib
import math
import random
import threading
import time
from typing import Any, Final

from app.models import (
    CandlePoint,
    MarketAsset,
    MarketCandlesResponse,
    OrderbookLevel,
)

# الثوابت الزمنية للأطر الزمنية بالثواني
TIMEFRAME_SECONDS: Final[dict[str, int]] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

# القيم المرجعية الأساسية للأصول الستة
BASE_ASSETS_SPEC: Final[list[dict]] = [
    {
        "symbol": "BTC-USD",
        "nameAr": "بيتكوين مقابل الدولار",
        "nameEn": "Bitcoin / USD",
        "category": "CRYPTO",
        "price": 96_500.00,
        "change24hPct": 2.45,
        "high24h": 97_850.00,
        "low24h": 93_900.00,
        "volume24hUsd": 38_450_000_000.0,
        "volatilityPct": 3.20,
        "spreadBps": 3.0,
        "decimals": 2,
    },
    {
        "symbol": "ETH-USD",
        "nameAr": "إيثيريوم مقابل الدولار",
        "nameEn": "Ethereum / USD",
        "category": "CRYPTO",
        "price": 3_420.00,
        "change24hPct": 1.85,
        "high24h": 3_495.00,
        "low24h": 3_340.00,
        "volume24hUsd": 16_900_000_000.0,
        "volatilityPct": 3.80,
        "spreadBps": 4.0,
        "decimals": 2,
    },
    {
        "symbol": "NVDA",
        "nameAr": "إنفيديا للذكاء الاصطناعي",
        "nameEn": "NVIDIA Corp",
        "category": "EQUITY",
        "price": 138.80,
        "change24hPct": 3.12,
        "high24h": 141.20,
        "low24h": 134.10,
        "volume24hUsd": 29_400_000_000.0,
        "volatilityPct": 2.90,
        "spreadBps": 2.5,
        "decimals": 2,
    },
    {
        "symbol": "XAU-USD",
        "nameAr": "الذهب الفوري مقابل الدولار",
        "nameEn": "Spot Gold / USD",
        "category": "COMMODITY",
        "price": 2_685.50,
        "change24hPct": 0.64,
        "high24h": 2_702.00,
        "low24h": 2_664.00,
        "volume24hUsd": 21_500_000_000.0,
        "volatilityPct": 1.15,
        "spreadBps": 2.0,
        "decimals": 2,
    },
    {
        "symbol": "SOL-USD",
        "nameAr": "سولانا مقابل الدولار",
        "nameEn": "Solana / USD",
        "category": "CRYPTO",
        "price": 214.40,
        "change24hPct": 4.35,
        "high24h": 221.00,
        "low24h": 203.50,
        "volume24hUsd": 6_850_000_000.0,
        "volatilityPct": 4.90,
        "spreadBps": 5.5,
        "decimals": 2,
    },
    {
        "symbol": "ARAMCO.SR",
        "nameAr": "أرامكو السعودية",
        "nameEn": "Saudi Aramco",
        "category": "EQUITY",
        "price": 27.95,
        "change24hPct": 0.54,
        "high24h": 28.25,
        "low24h": 27.65,
        "volume24hUsd": 490_000_000.0,
        "volatilityPct": 0.95,
        "spreadBps": 3.5,
        "decimals": 2,
    },
]

# قاموس المرادفات العربية والإنجليزية لتمييز الأصول من الأوامر الصوتية والنصية بدقة
SYMBOL_ALIASES: Final[dict[str, str]] = {
    "btc-usd": "BTC-USD",
    "btcusdt": "BTC-USD",
    "btc/usdt": "BTC-USD",
    "btc": "BTC-USD",
    "bitcoin": "BTC-USD",
    "بيتكوين": "BTC-USD",
    "البيتكوين": "BTC-USD",
    "بتكوين": "BTC-USD",
    "البتكوين": "BTC-USD",
    "eth-usd": "ETH-USD",
    "ethusdt": "ETH-USD",
    "eth/usdt": "ETH-USD",
    "eth": "ETH-USD",
    "ethereum": "ETH-USD",
    "إيثيريوم": "ETH-USD",
    "ايثيريوم": "ETH-USD",
    "الإيثيريوم": "ETH-USD",
    "الايثيريوم": "ETH-USD",
    "ايثريوم": "ETH-USD",
    "nvda": "NVDA",
    "nvidia": "NVDA",
    "إنفيديا": "NVDA",
    "انفيديا": "NVDA",
    "سهم إنفيديا": "NVDA",
    "سهم انفيديا": "NVDA",
    "xau-usd": "XAU-USD",
    "xauusd": "XAU-USD",
    "xau": "XAU-USD",
    "gold": "XAU-USD",
    "الذهب": "XAU-USD",
    "ذهب": "XAU-USD",
    "أونصة الذهب": "XAU-USD",
    "sol-usd": "SOL-USD",
    "solusdt": "SOL-USD",
    "sol/usdt": "SOL-USD",
    "sol": "SOL-USD",
    "solana": "SOL-USD",
    "سولانا": "SOL-USD",
    "السولانا": "SOL-USD",
    "aramco.sr": "ARAMCO.SR",
    "aramco": "ARAMCO.SR",
    "2222.sr": "ARAMCO.SR",
    "2222": "ARAMCO.SR",
    "أرامكو": "ARAMCO.SR",
    "ارامكو": "ARAMCO.SR",
    "أرامكو السعودية": "ARAMCO.SR",
}


class MarketEngine:
    """
    محرك محاكاة وتحديث بيانات السوق الحية ودفاتر الأوامر والشموع اليابانية،
    مزود بكاشف تقادم بيانات السوق (Stale Market-Data Detector).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rng = random.Random(20261117)
        self._tick_counter = 0
        self._last_tick_epoch: float = time.time()
        self._feed_halted: bool = False
        self._anchor_prices: dict[str, float] = {}
        self._decimals: dict[str, int] = {}
        self._assets: dict[str, MarketAsset] = {}
        self.reset()

    @property
    def max_staleness_seconds(self) -> float:
        import os

        try:
            return max(1.0, float(os.getenv("TRILUNAIR_MARKET_STALE_SECONDS", "60.0")))
        except ValueError:
            return 60.0

    def is_stale(self) -> bool:
        """التحقق مما إذا كانت بيانات السوق متقادمة أو متوقفة عن التحديث."""
        with self._lock:
            age = max(0.0, time.time() - self._last_tick_epoch)
            return age > self.max_staleness_seconds

    def get_feed_health(self) -> dict[str, Any]:
        """إرجاع تقرير حداثة وصحة بث أسعار السوق ومصدر البيانات النشط (Binance Public مقابل المحاكاة)."""
        from app.binance_market_data import binance_public_client

        binance_snap = binance_public_client.get_health_snapshot()
        with self._lock:
            age = round(max(0.0, time.time() - self._last_tick_epoch), 3)
            max_s = self.max_staleness_seconds
            return {
                "healthy": age <= max_s and not self._feed_halted,
                "stale": age > max_s,
                "feedHalted": self._feed_halted,
                "ageSeconds": age,
                "maxStalenessSeconds": max_s,
                "tickCounter": self._tick_counter,
                "marketDataMode": binance_snap["effectiveMatrixMode"],
                "liveMarketDataActive": binance_snap["liveMarketDataActive"],
                "binancePublic": binance_snap,
            }

    def simulate_stale_feed(self, age_seconds: float = 120.0) -> dict[str, Any]:
        """محاكاة انقطاع وتقادم بث السوق لاختبارات السلامة والتعافي."""
        with self._lock:
            self._feed_halted = True
            self._last_tick_epoch = time.time() - max(age_seconds, self.max_staleness_seconds + 5.0)
            return self.get_feed_health()

    def resume_feed(self) -> dict[str, Any]:
        """استئناف بث السوق وتحديث الطابع الزمني للنبضة الحية."""
        with self._lock:
            self._feed_halted = False
            self._last_tick_epoch = time.time()
        self.tick()
        return self.get_feed_health()

    def reset(self) -> None:
        """إعادة ضبط الأسعار إلى قيمها المرجعية الابتدائية (مفيد للاختبارات الحتمية)."""
        with self._lock:
            self._rng = random.Random(20261117)
            self._tick_counter = 0
            self._last_tick_epoch = time.time()
            self._feed_halted = False
            self._assets.clear()
            self._anchor_prices.clear()
            self._decimals.clear()
            for spec in BASE_ASSETS_SPEC:
                symbol = spec["symbol"]
                self._anchor_prices[symbol] = float(spec["price"])
                self._decimals[symbol] = int(spec["decimals"])
                self._assets[symbol] = MarketAsset(
                    symbol=symbol,
                    nameAr=spec["nameAr"],
                    nameEn=spec["nameEn"],
                    category=spec["category"],
                    price=float(spec["price"]),
                    change24hPct=float(spec["change24hPct"]),
                    high24h=float(spec["high24h"]),
                    low24h=float(spec["low24h"]),
                    volume24hUsd=float(spec["volume24hUsd"]),
                    volatilityPct=float(spec["volatilityPct"]),
                    spreadBps=float(spec["spreadBps"]),
                    dataSource="SIMULATED",
                )

    def resolve_symbol(self, raw_symbol: str | None) -> str | None:
        """تحويل أي رمز أو اسم أصل بالعربية أو الإنجليزية إلى الرمز القياسي المعتمد."""
        if not raw_symbol:
            return None
        cleaned = raw_symbol.strip().lower()
        if cleaned in SYMBOL_ALIASES:
            return SYMBOL_ALIASES[cleaned]
        upper = raw_symbol.strip().upper()
        if upper in self._assets:
            return upper
        # معالجة صيغ مثل BTCUSD أو BTC/USD
        normalized = upper.replace("/", "-").replace("_", "-")
        if normalized in self._assets:
            return normalized
        if f"{normalized}-USD" in self._assets:
            return f"{normalized}-USD"
        return None

    def extract_symbols_from_text(self, text: str) -> list[str]:
        """استخراج جميع رموز الأصول المذكورة في نص عربي أو إنجليزي بحسب ترتيب ورودها."""
        if not text:
            return []
        lowered = text.lower()
        found_positions: list[tuple[int, str]] = []

        # البحث عن الأسماء والرموز مع مراعاة حدود الكلمات للرموز اللاتينية القصيرة
        latin_patterns = [
            ("btc-usd", "BTC-USD"),
            ("eth-usd", "ETH-USD"),
            ("xau-usd", "XAU-USD"),
            ("sol-usd", "SOL-USD"),
            ("aramco.sr", "ARAMCO.SR"),
            ("bitcoin", "BTC-USD"),
            ("ethereum", "ETH-USD"),
            ("nvidia", "NVDA"),
            ("solana", "SOL-USD"),
            ("aramco", "ARAMCO.SR"),
            ("btc", "BTC-USD"),
            ("eth", "ETH-USD"),
            ("nvda", "NVDA"),
            ("xau", "XAU-USD"),
            ("gold", "XAU-USD"),
            ("sol", "SOL-USD"),
        ]
        arabic_patterns = [
            ("البيتكوين", "BTC-USD"),
            ("بيتكوين", "BTC-USD"),
            ("بتكوين", "BTC-USD"),
            ("الإيثيريوم", "ETH-USD"),
            ("الايثيريوم", "ETH-USD"),
            ("إيثيريوم", "ETH-USD"),
            ("ايثيريوم", "ETH-USD"),
            ("إنفيديا", "NVDA"),
            ("انفيديا", "NVDA"),
            ("الذهب", "XAU-USD"),
            ("ذهب", "XAU-USD"),
            ("سولانا", "SOL-USD"),
            ("أرامكو", "ARAMCO.SR"),
            ("ارامكو", "ARAMCO.SR"),
        ]

        import re

        for token, canonical in latin_patterns:
            match = re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered)
            if match:
                found_positions.append((match.start(), canonical))

        for token, canonical in arabic_patterns:
            idx = lowered.find(token)
            if idx != -1:
                found_positions.append((idx, canonical))

        found_positions.sort(key=lambda item: item[0])
        ordered_unique: list[str] = []
        for _, sym in found_positions:
            if sym not in ordered_unique:
                ordered_unique.append(sym)
        return ordered_unique

    def get_assets(self) -> list[MarketAsset]:
        """إرجاع قائمة بجميع الأصول الستة مع أسعارها الحية المحدثة."""
        with self._lock:
            return [asset.model_copy(deep=True) for asset in self._assets.values()]

    def get_asset(self, symbol: str) -> MarketAsset | None:
        """إرجاع بيانات أصل واحد عبر رمزه أو مرادفه."""
        canonical = self.resolve_symbol(symbol)
        if not canonical:
            return None
        with self._lock:
            asset = self._assets.get(canonical)
            return asset.model_copy(deep=True) if asset else None

    def sync_live_binance_tickers(self) -> dict[str, dict[str, Any]]:
        """جلب الأسعار العامة الحقيقية من Binance Spot عند تفعيل وضع LIVE_PUBLIC."""
        from app.binance_market_data import binance_public_client

        if binance_public_client.get_configured_mode() != "LIVE_PUBLIC":
            return {}
        return binance_public_client.fetch_live_tickers()

    def tick(self) -> list[MarketAsset]:
        """
        تحديث نبضة السوق الحية (Market Tick) لجميع الأصول الستة.
        عند تفعيل وضع LIVE_PUBLIC، تُستخدم بيانات السوق العامة الحقيقية من Binance Spot لأصول الكريبتو،
        مع تمييز مصدر كل أصل بشفافية تامة (BINANCE_PUBLIC_REST / BINANCE_PUBLIC_WS مقابل SIMULATED).
        """
        from app.binance_market_data import CANONICAL_TO_BINANCE_SPOT, binance_public_client

        live_tickers: dict[str, dict[str, Any]] = {}
        if not self._feed_halted and binance_public_client.get_configured_mode() == "LIVE_PUBLIC":
            # الاستفادة من ذاكرة WS الحية أو التحديث الدوري كل بضع نبضات عبر REST
            snap = binance_public_client.get_health_snapshot()
            if not snap["wsConnected"] and (self._tick_counter % 3 == 0 or not snap["cachedLiveSymbols"]):
                live_tickers = binance_public_client.fetch_live_tickers()
            else:
                with binance_public_client._lock:
                    live_tickers = dict(binance_public_client._tickers_cache)

        with self._lock:
            if self._feed_halted:
                return [asset.model_copy(deep=True) for asset in self._assets.values()]
            self._tick_counter += 1
            self._last_tick_epoch = time.time()
            updated: list[MarketAsset] = []

            for symbol, asset in self._assets.items():
                decimals = self._decimals[symbol]
                live_item = live_tickers.get(symbol) if symbol in CANONICAL_TO_BINANCE_SPOT else None

                if live_item and float(live_item.get("price", 0.0)) > 0:
                    live_price = round(float(live_item["price"]), decimals)
                    self._anchor_prices[symbol] = live_price
                    updated_asset = asset.model_copy(
                        update={
                            "price": live_price,
                            "change24hPct": round(float(live_item["change24hPct"]), 2),
                            "high24h": round(float(live_item["high24h"]), decimals),
                            "low24h": round(float(live_item["low24h"]), decimals),
                            "volume24hUsd": round(float(live_item["volume24hUsd"]), 2),
                            "volatilityPct": round(float(live_item["volatilityPct"]), 2),
                            "spreadBps": round(float(live_item["spreadBps"]), 2),
                            "dataSource": str(live_item.get("source", "BINANCE_PUBLIC_REST")),
                        }
                    )
                    self._assets[symbol] = updated_asset
                    updated.append(updated_asset.model_copy(deep=True))
                    continue

                anchor = self._anchor_prices[symbol]
                step_sigma = (asset.volatilityPct / 100.0) * 0.035
                random_shock = self._rng.gauss(0.0, step_sigma)
                deviation = (asset.price - anchor) / anchor
                mean_reversion = -0.18 * deviation

                pct_move = random_shock + mean_reversion
                new_price = round(max(anchor * 0.96, min(anchor * 1.04, asset.price * (1.0 + pct_move))), decimals)

                base_open_24h = anchor / (
                    1.0
                    + (
                        BASE_ASSETS_SPEC[[s["symbol"] for s in BASE_ASSETS_SPEC].index(symbol)]["change24hPct"]
                        / 100.0
                    )
                )
                new_change_pct = round(((new_price - base_open_24h) / base_open_24h) * 100.0, 2)
                new_high = round(max(asset.high24h, new_price), decimals)
                new_low = round(min(asset.low24h, new_price), decimals)
                new_volume = round(asset.volume24hUsd * (1.0 + abs(pct_move) * 0.15), 2)

                updated_asset = asset.model_copy(
                    update={
                        "price": new_price,
                        "change24hPct": new_change_pct,
                        "high24h": new_high,
                        "low24h": new_low,
                        "volume24hUsd": new_volume,
                        "dataSource": "SIMULATED",
                    }
                )
                self._assets[symbol] = updated_asset
                updated.append(updated_asset.model_copy(deep=True))

            return updated

    def get_candles(
        self, symbol: str, timeframe: str = "15m", limit: int = 90
    ) -> MarketCandlesResponse | None:
        """
        استرجاع سلسلة الشموع اليابانية (OHLCV) وعمق دفتر الأوامر:
        - يستخدم بيانات Binance Spot العامة الحقيقية (/api/v3/klines و /api/v3/depth) عند تفعيل LIVE_PUBLIC لأزواج Spot.
        - يتراجع بشفافية معلنة إلى المحرك الحتمي المحلي للأصول المرجعية أو عند وضع SIMULATED.
        """
        from app.binance_market_data import CANONICAL_TO_BINANCE_SPOT, binance_public_client

        asset = self.get_asset(symbol)
        if asset is None:
            return None

        tf = timeframe if timeframe in TIMEFRAME_SECONDS else "15m"
        step_sec = TIMEFRAME_SECONDS[tf]
        safe_limit = max(20, min(240, int(limit)))
        decimals = self._decimals.get(asset.symbol, 2)

        if (
            binance_public_client.get_configured_mode() == "LIVE_PUBLIC"
            and asset.symbol in CANONICAL_TO_BINANCE_SPOT
        ):
            live_candles = binance_public_client.fetch_klines(
                canonical_symbol=asset.symbol, timeframe=tf, limit=safe_limit
            )
            live_depth = binance_public_client.fetch_orderbook_depth(
                canonical_symbol=asset.symbol, limit=8, decimals=decimals
            )
            if live_candles and live_depth:
                bids_live, asks_live, last_update_id = live_depth
                recent_slice = live_candles[-min(40, len(live_candles)) :]
                recent_lows = sorted(c.low for c in recent_slice)
                recent_highs = sorted(c.high for c in recent_slice)
                raw_support = recent_lows[max(0, len(recent_lows) // 8)]
                raw_resistance = recent_highs[min(len(recent_highs) - 1, (len(recent_highs) * 7) // 8)]
                curr_p = live_candles[-1].close
                return MarketCandlesResponse(
                    symbol=asset.symbol,
                    timeframe=tf,
                    candles=live_candles,
                    supportLevel=round(min(raw_support, curr_p * 0.985), decimals),
                    resistanceLevel=round(max(raw_resistance, curr_p * 1.015), decimals),
                    bids=bids_live,
                    asks=asks_live,
                    dataSource="BINANCE_PUBLIC_REST",
                    lastUpdateId=last_update_id,
                )

        # بذرة حتمية مستقرة لكل أصل وإطار زمني لتوليد مسار تاريخي متماسك
        seed_bytes = hashlib.sha256(f"{asset.symbol}:{tf}".encode("utf-8")).digest()
        seed_int = int.from_bytes(seed_bytes[:8], "big")
        local_rng = random.Random(seed_int)

        now_sec = int(time.time())
        aligned_now_sec = (now_sec // step_sec) * step_sec

        tf_vol_scale = math.sqrt(step_sec / 86400.0) * (asset.volatilityPct / 100.0)
        closes_rev: list[float] = [asset.price]
        trend_bias = (asset.change24hPct / 100.0) / max(24.0, float(safe_limit))

        for i in range(1, safe_limit):
            wave = math.sin(i * 0.24) * tf_vol_scale * 0.35
            noise = local_rng.gauss(-trend_bias * 0.6, tf_vol_scale * 0.85)
            prev_close = closes_rev[-1] / max(0.95, min(1.05, 1.0 + noise + wave))
            closes_rev.append(round(prev_close, decimals))

        closes = list(reversed(closes_rev))
        candles: list[CandlePoint] = []
        base_candle_vol = (asset.volume24hUsd / asset.price) * (step_sec / 86400.0)

        for idx in range(safe_limit):
            ts_ms = (aligned_now_sec - (safe_limit - 1 - idx) * step_sec) * 1000
            close_p = closes[idx]
            open_p = closes[idx - 1] if idx > 0 else round(close_p * (1.0 - trend_bias), decimals)

            body = abs(close_p - open_p)
            wick_up = abs(local_rng.gauss(0.0, tf_vol_scale * 0.65)) * close_p + body * 0.25
            wick_dn = abs(local_rng.gauss(0.0, tf_vol_scale * 0.65)) * close_p + body * 0.25

            high_p = round(max(open_p, close_p) + wick_up, decimals)
            low_p = round(max(0.01, min(open_p, close_p) - wick_dn), decimals)
            vol_mult = 0.65 + local_rng.random() * 0.9 + (body / max(close_p * tf_vol_scale, 1e-6)) * 0.25
            vol = round(base_candle_vol * vol_mult, 2)

            candles.append(
                CandlePoint(
                    timestamp=ts_ms,
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=vol,
                )
            )

        recent_slice = candles[-min(40, len(candles)) :]
        recent_lows = sorted(c.low for c in recent_slice)
        recent_highs = sorted(c.high for c in recent_slice)
        raw_support = recent_lows[max(0, len(recent_lows) // 8)]
        raw_resistance = recent_highs[min(len(recent_highs) - 1, (len(recent_highs) * 7) // 8)]

        support_level = round(min(raw_support, asset.price * 0.985), decimals)
        resistance_level = round(max(raw_resistance, asset.price * 1.015), decimals)

        half_spread_ratio = (asset.spreadBps / 10000.0) * 0.5
        level_step_ratio = max(0.0004, (asset.spreadBps / 10000.0) * 0.85)
        unit_base_size = max(0.05, round((asset.volume24hUsd * 0.000015) / asset.price, 3))

        bids: list[OrderbookLevel] = []
        cum_bid = 0.0
        for lvl in range(8):
            bid_price = round(
                asset.price * (1.0 - half_spread_ratio - lvl * level_step_ratio),
                decimals,
            )
            size_factor = 0.8 + ((lvl % 3) * 0.45) + (0.25 if lvl == 3 else 0.0)
            size = round(unit_base_size * size_factor, 4)
            cum_bid = round(cum_bid + size, 4)
            bids.append(OrderbookLevel(price=bid_price, size=size, total=cum_bid))

        asks: list[OrderbookLevel] = []
        cum_ask = 0.0
        for lvl in range(8):
            ask_price = round(
                asset.price * (1.0 + half_spread_ratio + lvl * level_step_ratio),
                decimals,
            )
            size_factor = 0.75 + (((lvl + 1) % 3) * 0.48) + (0.3 if lvl == 4 else 0.0)
            size = round(unit_base_size * size_factor, 4)
            cum_ask = round(cum_ask + size, 4)
            asks.append(OrderbookLevel(price=ask_price, size=size, total=cum_ask))

        return MarketCandlesResponse(
            symbol=asset.symbol,
            timeframe=tf,
            candles=candles,
            supportLevel=support_level,
            resistanceLevel=resistance_level,
            bids=bids,
            asks=asks,
            dataSource="SIMULATED",
            lastUpdateId=None,
        )


# النسخة الموحدة لمحرك السوق على مستوى التطبيق
market_engine = MarketEngine()
