"""
محولات مزودات الذكاء الاصطناعي السحابية المتعددة والمستقلة (Multi-Provider Cloud LLM Orchestration Layer).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.1.0-cloud-paper

تدعم هذه الوحدة أربعة مزودات سحابية حقيقية بالإضافة إلى المحرك الكمي المحلي المعلن:
1. OpenAI GPT (POST /v1/chat/completions)
2. Google Gemini (POST /v1beta/models/{model}:generateContent)
3. Anthropic Claude (POST /v1/messages)
4. xAI Grok (POST /v1/chat/completions)
5. Local Quantitative Engine (محرك رياضي كمي محلي معلن صراحةً بحالة SIMULATED)

الخصائص التشغيلية السحابية (القسم 9 والقسم 10):
- فحوصات صحة المزودات وإحصاءات التوافر ومعدل الأخطاء وزمن الاستجابة لكل مزود على حدة.
- نماذج ومهل زمنية قابلة للتهيئة عبر البيئة مع إعادة المحاولة بالتراجع الأسي للأخطاء العابرة (502/503/504/الشبكة).
- معالجة حدود المعدل (HTTP 429) مع تتبع فترة التهدئة لكل مزود دون إسقاط بقية الوكلاء (Failure Isolation).
- ذاكرة تخزين مؤقت قصيرة المدى (TTL Cache) معلنة صراحةً بحالة CACHED لمنع الاستدعاءات المكررة المكلفة.
- تحقق صارم من مخطط المخرجات المهيكل وحساب الرموز المستهلكة والتكلفة التقديرية بالدولار.
- لا يملك أي وكيل أو مزود صلاحية تنفيذ أمر مالي حقيقي أو ورقي مباشرةً.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
import threading
import time
from typing import Any
import httpx

from app.security import create_outbound_http_client, security_telemetry

PROVIDER_COST_PER_1K_TOKENS_USD: dict[str, float] = {
    "local-quant-engine": 0.0001,
    "openai": 0.0050,
    "gemini": 0.0025,
    "anthropic": 0.0045,
    "xai": 0.0040,
}

DEFAULT_PROVIDER_MODELS: dict[str, str] = {
    "local-quant-engine": "quant-deterministic-v1",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-3-5-haiku-latest",
    "xai": "grok-3-mini",
}

_TELEMETRY_LOCK = threading.RLock()
_PROVIDER_RUNTIME_STATS: dict[str, dict[str, Any]] = {
    pid: {
        "totalCalls": 0,
        "successCalls": 0,
        "failedCalls": 0,
        "rateLimitHits": 0,
        "cacheHits": 0,
        "lastLatencyMs": None,
        "lastStatus": "SIMULATED" if pid == "local-quant-engine" else "UNAVAILABLE",
        "lastError": None,
        "cooldownUntilEpoch": 0.0,
        "lastCheckedAt": None,
    }
    for pid in PROVIDER_COST_PER_1K_TOKENS_USD
}

_RESPONSE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def reset_llm_adapter_state() -> None:
    """إعادة ضبط ذاكرة التخزين المؤقت وإحصاءات المزودات (مفيدة للاختبارات المعزولة)."""
    with _TELEMETRY_LOCK:
        _RESPONSE_CACHE.clear()
        for pid, stats in _PROVIDER_RUNTIME_STATS.items():
            stats["totalCalls"] = 0
            stats["successCalls"] = 0
            stats["failedCalls"] = 0
            stats["rateLimitHits"] = 0
            stats["cacheHits"] = 0
            stats["lastLatencyMs"] = None
            stats["lastStatus"] = "SIMULATED" if pid == "local-quant-engine" else "UNAVAILABLE"
            stats["lastError"] = None
            stats["cooldownUntilEpoch"] = 0.0
            stats["lastCheckedAt"] = None


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_configured_model(provider_id: str, requested_model: str | None) -> str:
    env_map = {
        "openai": "OPENAI_MODEL",
        "gemini": "GEMINI_MODEL",
        "anthropic": "ANTHROPIC_MODEL",
        "xai": "XAI_MODEL",
    }
    env_key = env_map.get(provider_id)
    env_override = os.getenv(env_key, "").strip() if env_key else ""
    if requested_model and requested_model.strip() and requested_model != "quant-deterministic-v1":
        return requested_model.strip()
    if env_override:
        return env_override
    return DEFAULT_PROVIDER_MODELS.get(provider_id, "quant-deterministic-v1")


def get_provider_credentials_report() -> list[dict[str, Any]]:
    """تقرير شفاف ومفصل يميز بين المزودات المتصلة فعلياً والمحاكاة محلياً وغير المهيأة مع قياسات الصحة."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    xai_key = os.getenv("XAI_API_KEY", "").strip()
    now = time.time()

    specs = [
        (
            "local-quant-engine",
            "Local Quantitative Engine",
            "SIMULATED_LOCAL",
            True,
            "BUILT_IN_DETERMINISTIC",
            "in-process://deterministic-quant-council",
        ),
        (
            "openai",
            "OpenAI GPT",
            "CONNECTED_CLOUD" if openai_key else "UNAVAILABLE_NO_KEY",
            bool(openai_key),
            "OPENAI_API_KEY",
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        ),
        (
            "gemini",
            "Google Gemini",
            "CONNECTED_CLOUD" if gemini_key else "UNAVAILABLE_NO_KEY",
            bool(gemini_key),
            "GEMINI_API_KEY",
            os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
        ),
        (
            "anthropic",
            "Anthropic Claude",
            "CONNECTED_CLOUD" if anthropic_key else "UNAVAILABLE_NO_KEY",
            bool(anthropic_key),
            "ANTHROPIC_API_KEY",
            os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        ),
        (
            "xai",
            "xAI Grok",
            "CONNECTED_CLOUD" if xai_key else "UNAVAILABLE_NO_KEY",
            bool(xai_key),
            "XAI_API_KEY",
            os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        ),
    ]

    report: list[dict[str, Any]] = []
    with _TELEMETRY_LOCK:
        for pid, display, classification, creds_ok, env_var, endpoint in specs:
            st = _PROVIDER_RUNTIME_STATS[pid]
            rate_limited = now < float(st["cooldownUntilEpoch"])
            if pid == "local-quant-engine":
                eff_status = "SIMULATED"
            elif not creds_ok:
                eff_status = "UNAVAILABLE"
            elif rate_limited:
                eff_status = "UNAVAILABLE"
            else:
                eff_status = st["lastStatus"] if st["totalCalls"] > 0 else "CONFIGURED_UNVERIFIED"
            report.append(
                {
                    "providerId": pid,
                    "displayName": display,
                    "classification": classification,
                    "credentialsConfigured": creds_ok,
                    "defaultModel": _get_configured_model(pid, None),
                    "envVar": env_var,
                    "endpoint": endpoint,
                    "operationalStatus": eff_status,
                    "rateLimited": rate_limited,
                    "totalCalls": st["totalCalls"],
                    "successCalls": st["successCalls"],
                    "failedCalls": st["failedCalls"],
                    "rateLimitHits": st["rateLimitHits"],
                    "cacheHits": st["cacheHits"],
                    "lastLatencyMs": st["lastLatencyMs"],
                    "lastError": st["lastError"],
                    "lastCheckedAt": st["lastCheckedAt"],
                }
            )
    return report


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """استخراج كائن JSON مهيكل من استجابة النموذج اللغوي بأمان."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        brace_match = re.search(r"(\{.*\})", cleaned, flags=re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(1)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _normalize_agent_llm_output(parsed: dict[str, Any]) -> dict[str, Any] | None:
    """التحقق من صحة مخرجات الوكيل السحابي وتطبيع القيم ضمن النطاقات الآمنة."""
    stance_raw = str(parsed.get("stance") or "HOLD").strip().upper()
    stance = stance_raw if stance_raw in {"BUY", "SELL", "HOLD", "CAUTION"} else "HOLD"
    try:
        conf = max(10, min(99, int(round(float(parsed.get("confidence", 72))))))
    except Exception:
        conf = 72
    try:
        default_unc = max(5, min(85, 100 - conf))
        unc = max(5, min(90, int(round(float(parsed.get("uncertaintyPct", default_unc))))))
    except Exception:
        unc = max(5, min(85, 100 - conf))
    summary_ar = str(parsed.get("summaryAr") or "").strip()
    summary_en = str(parsed.get("summaryEn") or "").strip()
    if not summary_ar and not summary_en:
        return None
    return {
        "stance": stance,
        "confidence": conf,
        "uncertaintyPct": unc,
        "summaryAr": summary_ar or summary_en,
        "summaryEn": summary_en or summary_ar,
    }


def _execute_single_provider_http_call(
    prov: str,
    eff_model: str,
    system_prompt: str,
    market_context: str,
    timeout_sec: float,
) -> tuple[str, int]:
    """تنفيذ طلب HTTP منفرد لأحد المزودات الأربعة وإرجاع (النص، إجمالي الرموز)."""
    if prov == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        with create_outbound_http_client(url, timeout_sec=timeout_sec) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": eff_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": market_context},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 280,
                },
            )
        resp.raise_for_status()
        body = resp.json()
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        tokens = int(
            usage.get("total_tokens")
            or (int(usage.get("prompt_tokens", 160)) + int(usage.get("completion_tokens", 120)))
        )
        return text, tokens

    if prov == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        base_url = os.getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        url = f"{base_url}/models/{eff_model}:generateContent"
        with create_outbound_http_client(url, timeout_sec=timeout_sec) as client:
            resp = client.post(
                url,
                params={"key": api_key},
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": f"{system_prompt}\n\n{market_context}"}],
                        }
                    ],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 280},
                },
            )
        resp.raise_for_status()
        body = resp.json()
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        meta = body.get("usageMetadata", {})
        tokens = int(
            meta.get("totalTokenCount")
            or (int(meta.get("promptTokenCount", 150)) + int(meta.get("candidatesTokenCount", 110)))
        )
        return text, tokens

    if prov == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"
        with create_outbound_http_client(url, timeout_sec=timeout_sec) as client:
            resp = client.post(
                url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": eff_model,
                    "max_tokens": 280,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": market_context}],
                },
            )
        resp.raise_for_status()
        body = resp.json()
        text = body["content"][0]["text"]
        usage = body.get("usage", {})
        tokens = int(usage.get("input_tokens", 180)) + int(usage.get("output_tokens", 120))
        return text, tokens

    if prov == "xai":
        api_key = os.getenv("XAI_API_KEY", "").strip()
        base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        with create_outbound_http_client(url, timeout_sec=timeout_sec) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": eff_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": market_context},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 280,
                },
            )
        resp.raise_for_status()
        body = resp.json()
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        tokens = int(
            usage.get("total_tokens")
            or (int(usage.get("prompt_tokens", 150)) + int(usage.get("completion_tokens", 110)))
        )
        return text, tokens

    raise ValueError(f"Unsupported provider: {prov}")


def invoke_configured_llm_adapter(
    provider_id: str,
    model: str,
    agent_role: str,
    market_context: str,
    timeout_sec: float | None = None,
    use_cache: bool | None = None,
) -> dict[str, Any]:
    """
    استدعاء المحول الحقيقي للمزود المسند للوكيل مع إعادة المحاولة، تتبع حدود المعدل،
    التحقق المهيكل، وعزل الأعطال دون التأثير على بقية الوكلاء.
    """
    prov = (provider_id or "local-quant-engine").strip().lower()
    responded_at = _utc_iso()

    if prov == "local-quant-engine":
        with _TELEMETRY_LOCK:
            st = _PROVIDER_RUNTIME_STATS["local-quant-engine"]
            st["totalCalls"] += 1
            st["successCalls"] += 1
            st["lastLatencyMs"] = 1.2
            st["lastStatus"] = "SIMULATED"
            st["lastCheckedAt"] = responded_at
        return {
            "invokedCloud": False,
            "success": True,
            "executionStatus": "SIMULATED",
            "providerUsed": "local-quant-engine",
            "modelUsed": model or "quant-deterministic-v1",
            "tokensUsed": 180,
            "costUsd": 0.000018,
            "respondedAt": responded_at,
            "data": None,
            "errorReason": None,
        }

    key_env_map = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "xai": "XAI_API_KEY",
    }
    if prov not in key_env_map:
        return {
            "invokedCloud": False,
            "success": False,
            "executionStatus": "UNAVAILABLE",
            "providerUsed": "local-quant-engine",
            "modelUsed": "quant-deterministic-v1",
            "tokensUsed": 0,
            "costUsd": 0.0,
            "respondedAt": responded_at,
            "data": None,
            "errorReason": f"UNSUPPORTED_PROVIDER:{prov}",
        }

    api_key = os.getenv(key_env_map[prov], "").strip()
    if not api_key:
        with _TELEMETRY_LOCK:
            st = _PROVIDER_RUNTIME_STATS[prov]
            st["lastStatus"] = "UNAVAILABLE"
            st["lastError"] = f"MISSING_{key_env_map[prov]}"
            st["lastCheckedAt"] = responded_at
        return {
            "invokedCloud": False,
            "success": False,
            "executionStatus": "UNAVAILABLE",
            "providerUsed": "local-quant-engine",
            "modelUsed": "quant-deterministic-v1",
            "tokensUsed": 0,
            "costUsd": 0.0,
            "respondedAt": responded_at,
            "data": None,
            "errorReason": f"MISSING_{key_env_map[prov]}",
        }

    now = time.time()
    with _TELEMETRY_LOCK:
        if now < float(_PROVIDER_RUNTIME_STATS[prov]["cooldownUntilEpoch"]):
            return {
                "invokedCloud": False,
                "success": False,
                "executionStatus": "UNAVAILABLE",
                "providerUsed": "local-quant-engine",
                "modelUsed": "quant-deterministic-v1",
                "tokensUsed": 0,
                "costUsd": 0.0,
                "respondedAt": responded_at,
                "data": None,
                "errorReason": f"PROVIDER_RATE_LIMITED_COOLDOWN:{prov}",
            }

    eff_model = _get_configured_model(prov, model)
    eff_timeout = (
        float(timeout_sec)
        if timeout_sec is not None
        else max(1.0, float(os.getenv("TRILUNAIR_LLM_TIMEOUT_SECONDS", "8.0")))
    )
    max_retries = max(0, min(3, int(os.getenv("TRILUNAIR_LLM_MAX_RETRIES", "1"))))
    cache_ttl = float(os.getenv("TRILUNAIR_LLM_CACHE_TTL_SECONDS", "0"))
    enable_cache = use_cache if use_cache is not None else (cache_ttl > 0)

    cache_key = hashlib.sha256(
        f"{prov}:{eff_model}:{agent_role}:{market_context}".encode("utf-8")
    ).hexdigest()

    if enable_cache:
        with _TELEMETRY_LOCK:
            cached_entry = _RESPONSE_CACHE.get(cache_key)
            if cached_entry and (now - cached_entry[0]) <= max(1.0, cache_ttl):
                _PROVIDER_RUNTIME_STATS[prov]["cacheHits"] += 1
                hit = dict(cached_entry[1])
                hit["executionStatus"] = "CACHED"
                hit["tokensUsed"] = 0
                hit["costUsd"] = 0.0
                hit["respondedAt"] = _utc_iso()
                return hit

    system_prompt = (
        f"You are {agent_role} in the Quantum AI Trading Command Center. "
        "Respond ONLY with valid JSON containing keys: "
        '{"stance": "BUY|SELL|HOLD|CAUTION", "confidence": 78, "uncertaintyPct": 22, '
        '"summaryAr": "تحليل موجز بالعربية", "summaryEn": "Concise English analysis"}. '
        "Never claim execution authority or permission to submit real financial orders."
    )

    last_err = "UNKNOWN_ADAPTER_ERROR"
    start_t = time.perf_counter()

    for attempt in range(max_retries + 1):
        try:
            text, tokens = _execute_single_provider_http_call(
                prov=prov,
                eff_model=eff_model,
                system_prompt=system_prompt,
                market_context=market_context,
                timeout_sec=eff_timeout,
            )
            elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            parsed = _extract_json_object(text)
            normalized = _normalize_agent_llm_output(parsed) if parsed else None
            if normalized is None:
                raise ValueError("INVALID_STRUCTURED_JSON_OUTPUT")

            rate = PROVIDER_COST_PER_1K_TOKENS_USD.get(prov, 0.004)
            cost_usd = round((tokens / 1000.0) * rate, 6)
            done_ts = _utc_iso()
            result = {
                "invokedCloud": True,
                "success": True,
                "executionStatus": "LIVE",
                "providerUsed": prov,
                "modelUsed": eff_model,
                "tokensUsed": tokens,
                "costUsd": cost_usd,
                "respondedAt": done_ts,
                "data": normalized,
                "errorReason": None,
            }
            with _TELEMETRY_LOCK:
                st = _PROVIDER_RUNTIME_STATS[prov]
                st["totalCalls"] += 1
                st["successCalls"] += 1
                st["lastLatencyMs"] = elapsed_ms
                st["lastStatus"] = "LIVE"
                st["lastError"] = None
                st["lastCheckedAt"] = done_ts
                if enable_cache:
                    _RESPONSE_CACHE[cache_key] = (time.time(), dict(result))
            return result

        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            last_err = f"HTTP_{code}"
            if code == 429:
                retry_hdr = exc.response.headers.get("retry-after", "20")
                cooldown = float(retry_hdr) if str(retry_hdr).isdigit() else 20.0
                with _TELEMETRY_LOCK:
                    st = _PROVIDER_RUNTIME_STATS[prov]
                    st["totalCalls"] += 1
                    st["failedCalls"] += 1
                    st["rateLimitHits"] += 1
                    st["cooldownUntilEpoch"] = time.time() + min(120.0, max(2.0, cooldown))
                    st["lastStatus"] = "UNAVAILABLE"
                    st["lastError"] = f"HTTP_429_RATE_LIMITED_{int(cooldown)}S"
                    st["lastCheckedAt"] = _utc_iso()
                security_telemetry.emit_event(
                    "AI_PROVIDER_RATE_LIMITED",
                    severity="WARNING",
                    details={"provider": prov, "cooldownSeconds": cooldown},
                )
                break
            if code in {502, 503, 504} and attempt < max_retries:
                time.sleep(0.15 * (2**attempt))
                continue
            break
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_err = f"{type(exc).__name__}"
            if attempt < max_retries:
                time.sleep(0.15 * (2**attempt))
                continue
            break
        except Exception as exc:
            last_err = f"{type(exc).__name__}:{str(exc)[:80]}"
            break

    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
    fail_ts = _utc_iso()
    with _TELEMETRY_LOCK:
        st = _PROVIDER_RUNTIME_STATS[prov]
        st["totalCalls"] += 1
        st["failedCalls"] += 1
        st["lastLatencyMs"] = elapsed_ms
        st["lastStatus"] = "UNAVAILABLE"
        st["lastError"] = last_err
        st["lastCheckedAt"] = fail_ts

    return {
        "invokedCloud": True,
        "success": False,
        "executionStatus": "UNAVAILABLE",
        "providerUsed": "local-quant-engine",
        "modelUsed": "quant-deterministic-v1",
        "tokensUsed": 0,
        "costUsd": 0.0,
        "respondedAt": fail_ts,
        "data": None,
        "errorReason": f"ADAPTER_ERROR:{last_err}",
    }
