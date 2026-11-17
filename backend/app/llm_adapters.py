"""
محولات مزودات الذكاء الاصطناعي الحقيقية والمستقلة (Real Independent LLM Provider Adapters).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

تدعم هذه الوحدة أربعة محولات HTTP سحابية حقيقية بالإضافة إلى المحرك الكمي المحلي المعلن:
1. OpenAI GPT (POST /v1/chat/completions)
2. Google Gemini (POST /v1beta/models/{model}:generateContent)
3. Anthropic Claude (POST /v1/messages)
4. xAI Grok (POST /v1/chat/completions)
5. Local Quantitative Engine (محرك رياضي كمي محلي معلن صراحةً كـ SIMULATED_LOCAL)

مبدأ المصداقية الصارم:
- لا يتم انتحال أي استجابة سحابية عند غياب مفتاح API الخاص بالمزود.
- يُسجل كل استدعاء فعلي بعدد الرموز المستهلكة (Tokens) والتكلفة الدولارية المنسوبة للوكيل.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any
import httpx


PROVIDER_COST_PER_1K_TOKENS_USD: dict[str, float] = {
    "local-quant-engine": 0.0001,
    "openai": 0.0050,
    "gemini": 0.0025,
    "anthropic": 0.0045,
    "xai": 0.0040,
}


def get_provider_credentials_report() -> list[dict[str, Any]]:
    """تقرير شفاف ومفصل يميز بين المزودات المتصلة فعلياً والمحاكاة محلياً وغير المهيأة."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    xai_key = os.getenv("XAI_API_KEY", "").strip()

    return [
        {
            "providerId": "local-quant-engine",
            "displayName": "Local Quantitative Engine",
            "classification": "SIMULATED_LOCAL",
            "credentialsConfigured": True,
            "envVar": "BUILT_IN_DETERMINISTIC",
            "endpoint": "in-process://deterministic-quant-council",
        },
        {
            "providerId": "openai",
            "displayName": "OpenAI GPT",
            "classification": "CONNECTED_CLOUD" if openai_key else "UNAVAILABLE_NO_KEY",
            "credentialsConfigured": bool(openai_key),
            "envVar": "OPENAI_API_KEY",
            "endpoint": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        },
        {
            "providerId": "gemini",
            "displayName": "Google Gemini",
            "classification": "CONNECTED_CLOUD" if gemini_key else "UNAVAILABLE_NO_KEY",
            "credentialsConfigured": bool(gemini_key),
            "envVar": "GEMINI_API_KEY",
            "endpoint": os.getenv(
                "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
            ),
        },
        {
            "providerId": "anthropic",
            "displayName": "Anthropic Claude",
            "classification": "CONNECTED_CLOUD" if anthropic_key else "UNAVAILABLE_NO_KEY",
            "credentialsConfigured": bool(anthropic_key),
            "envVar": "ANTHROPIC_API_KEY",
            "endpoint": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        },
        {
            "providerId": "xai",
            "displayName": "xAI Grok",
            "classification": "CONNECTED_CLOUD" if xai_key else "UNAVAILABLE_NO_KEY",
            "credentialsConfigured": bool(xai_key),
            "envVar": "XAI_API_KEY",
            "endpoint": os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
        },
    ]


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
        conf = max(10, min(99, int(float(parsed.get("confidence", 70)))))
    except Exception:
        conf = 70
    summary_ar = str(parsed.get("summaryAr") or "").strip()
    summary_en = str(parsed.get("summaryEn") or "").strip()
    if not summary_ar and not summary_en:
        return None
    return {
        "stance": stance,
        "confidence": conf,
        "summaryAr": summary_ar or summary_en,
        "summaryEn": summary_en or summary_ar,
    }


def invoke_configured_llm_adapter(
    provider_id: str,
    model: str,
    agent_role: str,
    market_context: str,
    timeout_sec: float = 6.0,
) -> dict[str, Any]:
    """
    استدعاء المحول الحقيقي للمزود المسند للوكيل عند توفر بيانات الاعتماد.
    يعيد قاموساً يتضمن:
    - invokedCloud: bool
    - success: bool
    - providerUsed: str
    - modelUsed: str
    - tokensUsed: int
    - costUsd: float
    - data: dict | None
    - errorReason: str | None
    """
    prov = (provider_id or "local-quant-engine").strip().lower()
    if prov == "local-quant-engine":
        return {
            "invokedCloud": False,
            "success": True,
            "providerUsed": "local-quant-engine",
            "modelUsed": model or "quant-deterministic-v1",
            "tokensUsed": 180,
            "costUsd": 0.000018,
            "data": None,
            "errorReason": None,
        }

    system_prompt = (
        f"You are {agent_role} in the Quantum AI Trading Command Center. "
        "Respond ONLY with valid JSON containing keys: "
        '{"stance": "BUY|SELL|HOLD|CAUTION", "confidence": 75, '
        '"summaryAr": "تحليل موجز بالعربية", "summaryEn": "Concise English analysis"}. '
        "Never claim execution authority."
    )

    # تجنب تمرير طلبات الاختبار المحلية عبر وكيل الشبكة الخارجي عند استهداف 127.0.0.1 / localhost
    def _build_http_client(target_url: str) -> httpx.Client:
        is_local = "127.0.0.1" in target_url or "localhost" in target_url
        return httpx.Client(timeout=timeout_sec, trust_env=not is_local)

    try:
        if prov == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                return {
                    "invokedCloud": False,
                    "success": False,
                    "providerUsed": "local-quant-engine",
                    "modelUsed": "quant-deterministic-v1",
                    "tokensUsed": 0,
                    "costUsd": 0.0,
                    "data": None,
                    "errorReason": "MISSING_OPENAI_API_KEY",
                }
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            url = f"{base_url}/chat/completions"
            eff_model = model or "gpt-4o-mini"
            with _build_http_client(url) as client:
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
                        "max_tokens": 260,
                    },
                )
            resp.raise_for_status()
            body = resp.json()
            text = body["choices"][0]["message"]["content"]
            tokens = int(body.get("usage", {}).get("total_tokens", 320))

        elif prov == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                return {
                    "invokedCloud": False,
                    "success": False,
                    "providerUsed": "local-quant-engine",
                    "modelUsed": "quant-deterministic-v1",
                    "tokensUsed": 0,
                    "costUsd": 0.0,
                    "data": None,
                    "errorReason": "MISSING_GEMINI_API_KEY",
                }
            base_url = os.getenv(
                "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
            ).rstrip("/")
            eff_model = model or "gemini-2.5-flash"
            url = f"{base_url}/models/{eff_model}:generateContent"
            with _build_http_client(url) as client:
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
                        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 260},
                    },
                )
            resp.raise_for_status()
            body = resp.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            tokens = int(body.get("usageMetadata", {}).get("totalTokenCount", 300))

        elif prov == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            if not api_key:
                return {
                    "invokedCloud": False,
                    "success": False,
                    "providerUsed": "local-quant-engine",
                    "modelUsed": "quant-deterministic-v1",
                    "tokensUsed": 0,
                    "costUsd": 0.0,
                    "data": None,
                    "errorReason": "MISSING_ANTHROPIC_API_KEY",
                }
            base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
            url = f"{base_url}/v1/messages"
            eff_model = model or "claude-3-5-haiku-latest"
            with _build_http_client(url) as client:
                resp = client.post(
                    url,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": eff_model,
                        "max_tokens": 260,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": market_context}],
                    },
                )
            resp.raise_for_status()
            body = resp.json()
            text = body["content"][0]["text"]
            usage = body.get("usage", {})
            tokens = int(usage.get("input_tokens", 180)) + int(
                usage.get("output_tokens", 120)
            )

        elif prov == "xai":
            api_key = os.getenv("XAI_API_KEY", "").strip()
            if not api_key:
                return {
                    "invokedCloud": False,
                    "success": False,
                    "providerUsed": "local-quant-engine",
                    "modelUsed": "quant-deterministic-v1",
                    "tokensUsed": 0,
                    "costUsd": 0.0,
                    "data": None,
                    "errorReason": "MISSING_XAI_API_KEY",
                }
            base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
            url = f"{base_url}/chat/completions"
            eff_model = model or "grok-3-mini"
            with _build_http_client(url) as client:
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
                        "max_tokens": 260,
                    },
                )
            resp.raise_for_status()
            body = resp.json()
            text = body["choices"][0]["message"]["content"]
            tokens = int(body.get("usage", {}).get("total_tokens", 310))

        else:
            return {
                "invokedCloud": False,
                "success": False,
                "providerUsed": "local-quant-engine",
                "modelUsed": "quant-deterministic-v1",
                "tokensUsed": 0,
                "costUsd": 0.0,
                "data": None,
                "errorReason": f"UNKNOWN_PROVIDER:{prov}",
            }

        parsed = _extract_json_object(text)
        normalized = _normalize_agent_llm_output(parsed) if parsed else None
        if normalized is None:
            return {
                "invokedCloud": True,
                "success": False,
                "providerUsed": "local-quant-engine",
                "modelUsed": "quant-deterministic-v1",
                "tokensUsed": tokens,
                "costUsd": round(
                    (tokens / 1000.0) * PROVIDER_COST_PER_1K_TOKENS_USD.get(prov, 0.004),
                    6,
                ),
                "data": None,
                "errorReason": "INVALID_STRUCTURED_SCHEMA_FROM_PROVIDER",
            }

        cost_usd = round(
            (tokens / 1000.0) * PROVIDER_COST_PER_1K_TOKENS_USD.get(prov, 0.004), 6
        )
        return {
            "invokedCloud": True,
            "success": True,
            "providerUsed": prov,
            "modelUsed": eff_model,
            "tokensUsed": tokens,
            "costUsd": cost_usd,
            "data": normalized,
            "errorReason": None,
        }

    except Exception as exc:
        return {
            "invokedCloud": True,
            "success": False,
            "providerUsed": "local-quant-engine",
            "modelUsed": "quant-deterministic-v1",
            "tokensUsed": 0,
            "costUsd": 0.0,
            "data": None,
            "errorReason": f"ADAPTER_HTTP_ERROR:{type(exc).__name__}",
        }
