"""
منظومة قياس الكمون الدقيق عبر مراحل خط أنابيب التداول الثماني (8-Stage Pipeline Latency Telemetry & Freshness Guard).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.2.0-low-latency-cloudflare

المسار المقاس بالنانوثانية (perf_counter_ns):
  Binance Market Data -> Market Analysis -> AI Council -> Decision Engine
  -> Deterministic Risk Engine -> Economic Viability Check -> PAPER Execution -> Audit
"""

from __future__ import annotations

from collections import deque
import math
import os
import statistics
import threading
import time
from typing import Any


STAGE_KEYS: tuple[str, ...] = (
    "marketDataAgeMs",
    "marketAnalysisMs",
    "aiInferenceMs",
    "agentConsensusMs",
    "riskValidationMs",
    "economicViabilityMs",
    "paperExecutionSimMs",
    "auditPersistenceMs",
    "totalSignalToDecisionMs",
)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    rank = (pct / 100.0) * (len(ordered) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return round(ordered[lo], 3)
    w = rank - lo
    return round(ordered[lo] * (1.0 - w) + ordered[hi] * w, 3)


def _summarize(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "samples": 0,
            "lastMs": 0.0,
            "meanMs": 0.0,
            "p50Ms": 0.0,
            "p95Ms": 0.0,
            "p99Ms": 0.0,
            "maxMs": 0.0,
        }
    return {
        "samples": len(values),
        "lastMs": round(values[-1], 3),
        "meanMs": round(statistics.fmean(values), 3),
        "p50Ms": _percentile(values, 50.0),
        "p95Ms": _percentile(values, 95.0),
        "p99Ms": _percentile(values, 99.0),
        "maxMs": round(max(values), 3),
    }


def classify_market_data_freshness(age_seconds: float, max_staleness_seconds: float = 60.0, halted: bool = False) -> dict[str, Any]:
    """تصنيف حداثة بيانات السوق لتحديد صلاحية الإشارة وترشيد استدعاءات النماذج السحابية المدفوعة."""
    age_ms = round(max(0.0, age_seconds) * 1000.0, 2)
    if halted or age_seconds > max_staleness_seconds:
        return {
            "tier": "STALE_HALTED",
            "ageMs": age_ms,
            "eligibleForExecution": False,
            "eligibleForPaidCloudLlm": False,
            "reasonEn": f"Market feed stale ({age_seconds:.2f}s > {max_staleness_seconds:.1f}s) or halted; blocking execution and skipping paid LLM calls.",
            "reasonAr": f"بيانات السوق متقادمة ({age_seconds:.2f} ثانية)؛ تم حظر التنفيذ وتخطي استهلاك النماذج السحابية المدفوعة.",
        }
    if age_seconds <= 2.0:
        return {
            "tier": "ULTRA_FRESH",
            "ageMs": age_ms,
            "eligibleForExecution": True,
            "eligibleForPaidCloudLlm": True,
            "reasonEn": "Sub-2s market data freshness suitable for full fast-quorum deliberation.",
            "reasonAr": "حداثة فائقة لبيانات السوق (< 2 ثانية) مناسبة للتقييم الفوري المتوازي.",
        }
    if age_seconds <= 12.0:
        return {
            "tier": "FRESH",
            "ageMs": age_ms,
            "eligibleForExecution": True,
            "eligibleForPaidCloudLlm": True,
            "reasonEn": "Fresh market data within normal streaming/polling window.",
            "reasonAr": "بيانات السوق حديثة ضمن نافذة التحديث الطبيعية.",
        }
    return {
        "tier": "DEGRADED_CAUTION",
        "ageMs": age_ms,
        "eligibleForExecution": True,
        "eligibleForPaidCloudLlm": False,
        "reasonEn": "Aging market snapshot (>12s); routing council to deterministic local low-latency engine to avoid stale cloud spend.",
        "reasonAr": "تقادم نسبي في لقطة السوق (> 12 ثانية)؛ تم التوجيه للمحرك الكمي المحلي الفوري لمنع هدر تكلفة الاستدلال السحابي.",
    }


def get_council_deadline_ms() -> float:
    try:
        return max(150.0, min(15_000.0, float(os.getenv("TRILUNAIR_COUNCIL_DEADLINE_MS", "2200"))))
    except ValueError:
        return 2200.0


def get_signal_ttl_seconds() -> int:
    try:
        return max(5, min(600, int(os.getenv("TRILUNAIR_SIGNAL_TTL_SECONDS", "45"))))
    except ValueError:
        return 45


class PipelineLatencyTracker:
    """مجمع قياسات الأداء الزمني عالي الدقة لخط أنابيب القرار والتنفيذ الورقي."""

    def __init__(self, maxlen: int = 250) -> None:
        self._lock = threading.RLock()
        self._series: dict[str, deque[float]] = {k: deque(maxlen=maxlen) for k in STAGE_KEYS}
        self._recent_traces: deque[dict[str, Any]] = deque(maxlen=40)
        self._parallel_timeouts = 0
        self._cost_aware_skips = 0
        self._stale_signal_blocks = 0

    def reset(self) -> None:
        with self._lock:
            for dq in self._series.values():
                dq.clear()
            self._recent_traces.clear()
            self._parallel_timeouts = 0
            self._cost_aware_skips = 0
            self._stale_signal_blocks = 0

    def record_stage(self, stage_key: str, duration_ms: float) -> None:
        if stage_key not in self._series:
            return
        with self._lock:
            self._series[stage_key].append(round(max(0.0, float(duration_ms)), 3))

    def record_counter(self, kind: str, increment: int = 1) -> None:
        with self._lock:
            if kind == "parallel_timeout":
                self._parallel_timeouts += increment
            elif kind == "cost_aware_skip":
                self._cost_aware_skips += increment
            elif kind == "stale_signal_block":
                self._stale_signal_blocks += increment

    def record_pipeline_trace(
        self,
        trace_type: str,
        symbol: str,
        stages_ms: dict[str, float],
        routing_mode: str = "PARALLEL_BOUNDED_DEADLINE",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_stages: dict[str, float] = {}
        with self._lock:
            for key in STAGE_KEYS:
                if key in stages_ms and stages_ms[key] is not None:
                    val = round(max(0.0, float(stages_ms[key])), 3)
                    clean_stages[key] = val
                    self._series[key].append(val)

            entry = {
                "timestampEpochMs": round(time.time() * 1000.0, 1),
                "traceType": trace_type,
                "symbol": symbol,
                "routingMode": routing_mode,
                "stagesMs": clean_stages,
                **(extra or {}),
            }
            self._recent_traces.appendleft(entry)
            return entry

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            stages_summary = {k: _summarize(list(dq)) for k, dq in self._series.items()}
            return {
                "pipelineArchitecture": (
                    "Binance Market Data -> Market Analysis -> Parallel AI Council -> Decision Engine "
                    "-> Deterministic Risk Engine -> Economic Viability Check -> PAPER Execution -> Immutable Audit"
                ),
                "councilDeadlineMs": get_council_deadline_ms(),
                "defaultSignalTtlSeconds": get_signal_ttl_seconds(),
                "counters": {
                    "parallelProviderDeadlineTimeouts": self._parallel_timeouts,
                    "costAwareCloudInferenceSkips": self._cost_aware_skips,
                    "staleOrExpiredSignalBlocks": self._stale_signal_blocks,
                },
                "stages": stages_summary,
                "recentTraces": list(self._recent_traces)[:15],
            }


pipeline_latency_tracker = PipelineLatencyTracker()
