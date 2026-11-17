"""
خدمة الأوامر الصوتية وتحويل الكلام إلى نص (STT) والنص إلى كلام (TTS).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

المعمارية الصوتية الهجينة:
1. في المتصفح: يعمل SpeechRecognition و window.speechSynthesis كمسار فوري منخفض الكمون
   وقابل للمقاطعة اللحظية (Interruptible) بعد إذن الميكروفون الصريح من المستخدم.
2. في الخادم: توفر نقاط النهاية /api/voice/stt و /api/voice/tts دعماً سحابياً تلقائياً عند ضبط
   مفتاح OPENAI_API_KEY، وتوليد إشارات صوتية قياسية بصيغة RIFF WAV محلياً كمسار احتياطي موثوق.
"""

from __future__ import annotations

import base64
import io
import math
import os
import struct
from typing import Any
import wave

from fastapi import Request

from app.security import create_outbound_async_http_client, security_telemetry


def _infer_audio_mime_type(filename: str, declared_mime: str | None = None) -> str:
    """استنتاج نوع الوسائط الصوتية بدقة لدعم متصفح Safari (audio/mp4, audio/m4a, audio/wav) وChrome (audio/webm)."""
    if declared_mime and declared_mime.strip().startswith("audio/"):
        return declared_mime.split(";")[0].strip().lower()
    lower = (filename or "").lower()
    if lower.endswith(".mp4") or lower.endswith(".m4a") or lower.endswith(".aac"):
        return "audio/mp4"
    if lower.endswith(".wav"):
        return "audio/wav"
    if lower.endswith(".ogg") or lower.endswith(".oga"):
        return "audio/ogg"
    if lower.endswith(".mp3") or lower.endswith(".mpeg"):
        return "audio/mpeg"
    return "audio/webm"


def get_voice_subsystem_status() -> dict[str, Any]:
    """فحص شفاف لحالة منظومة الأوامر الصوتية العربية والإنجليزية (المتصفح + السحابة + Safari)."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    stt_url = os.getenv("OPENAI_STT_URL", "https://api.openai.com/v1/audio/transcriptions").strip()
    tts_url = os.getenv("OPENAI_TTS_URL", "https://api.openai.com/v1/audio/speech").strip()
    cloud_configured = bool(openai_key)
    return {
        "status": "CLOUD_AND_BROWSER_READY" if cloud_configured else "BROWSER_PRIMARY_LOCAL_WAV_FALLBACK",
        "cloudSpeechConfigured": cloud_configured,
        "sttPrimaryEngine": "openai-whisper" if cloud_configured else "browser-webkit-speech-recognition",
        "ttsPrimaryEngine": "openai-tts" if cloud_configured else "browser-speech-synthesis+server-riff-wav",
        "sttEndpoint": stt_url,
        "ttsEndpoint": tts_url,
        "supportedLanguages": ["ar-SA", "ar", "en-US", "en"],
        "safariCompatibility": {
            "webkitSpeechRecognitionSupported": True,
            "mediaRecorderMimeFallbacks": ["audio/mp4", "audio/webm;codecs=opus", "audio/webm", "audio/wav"],
            "webkitAudioContextSupported": True,
            "explicitMicPermissionRequired": True,
            "continuousBackgroundRecordingDisabled": True,
        },
    }


def generate_holo_chime_wav_bytes(
    text: str, language: str = "ar", sample_rate: int = 22050
) -> bytes:
    """
    توليد ملف صوتي قياسي صالح بصيغة RIFF WAVE (16-bit PCM Mono)
    يحاكي نغمة تأكيد هولوغرامية متناغمة تتناسب مدتها بسلاسة مع طول الرسالة.
    """
    char_count = max(1, len(text.strip()))
    duration_sec = min(1.2, max(0.28, 0.25 + char_count * 0.004))
    num_samples = int(sample_rate * duration_sec)

    # ترددات متناغمة مميزة للنسق العربي (مقام دافئ) والإنجليزي (كريستالي)
    f1 = 528.0 if language == "ar" else 587.33
    f2 = 660.0 if language == "ar" else 783.99

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            # غلاف تلاشي ناعم في البداية والنهاية لمنع أي طقطقة صوتية
            attack = min(1.0, t / 0.03)
            decay = max(0.0, 1.0 - (t / duration_sec) ** 1.4)
            envelope = attack * decay * 0.28

            freq = f1 if t < (duration_sec * 0.45) else f2
            sample_val = envelope * (
                0.75 * math.sin(2.0 * math.pi * freq * t)
                + 0.25 * math.sin(2.0 * math.pi * (freq * 1.5) * t)
            )
            pcm_int = max(-32767, min(32767, int(sample_val * 32767)))
            frames.extend(struct.pack("<h", pcm_int))

        wav_file.writeframes(bytes(frames))

    return buf.getvalue()


async def handle_stt_request(request: Request) -> dict[str, Any]:
    """
    معالجة طلبات تحويل الصوت إلى نص (POST /api/voice/stt).
    يدعم رفع ملف صوتي (multipart/form-data بما في ذلك صيغ Safari audio/mp4) أو حمولة JSON اختبارية.
    """
    content_type = (request.headers.get("content-type") or "").lower()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    stt_url = os.getenv("OPENAI_STT_URL", "https://api.openai.com/v1/audio/transcriptions").strip()

    audio_bytes: bytes | None = None
    filename = "audio.webm"
    declared_mime: str | None = None
    language = "ar"
    fallback_transcript = ""

    if "multipart/form-data" in content_type:
        form = await request.form()
        language = str(form.get("language") or "ar")
        fallback_transcript = str(form.get("transcript") or "").strip()
        uploaded = form.get("file") or form.get("audio")
        if uploaded is not None and hasattr(uploaded, "read"):
            audio_bytes = await uploaded.read()  # type: ignore[misc]
            filename = getattr(uploaded, "filename", None) or "speech.webm"
            declared_mime = getattr(uploaded, "content_type", None)
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                language = str(body.get("language") or "ar")
                fallback_transcript = str(body.get("transcript") or body.get("text") or "").strip()
                declared_mime = str(body.get("mimeType") or "").strip() or None
                if declared_mime and "mp4" in declared_mime:
                    filename = "speech.mp4"
                b64_audio = body.get("audioBase64")
                if isinstance(b64_audio, str) and b64_audio.strip():
                    audio_bytes = base64.b64decode(b64_audio)
        except Exception:
            pass

    audio_mime = _infer_audio_mime_type(filename, declared_mime)

    # في حال توفر مفتاح OpenAI وبيانات صوتية فعلية، يتم استخدام Whisper السحابي عبر العميل المتوافق مع الوكيل
    if openai_key and audio_bytes:
        try:
            async with create_outbound_async_http_client(stt_url, timeout_sec=12.0) as client:
                whisper_lang = "ar" if language.startswith("ar") else "en"
                resp = await client.post(
                    stt_url,
                    headers={"Authorization": f"Bearer {openai_key}"},
                    data={"model": os.getenv("OPENAI_STT_MODEL", "whisper-1"), "language": whisper_lang},
                    files={"file": (filename, audio_bytes, audio_mime)},
                )
                if resp.status_code == 200:
                    transcript_text = resp.json().get("text", "").strip()
                    return {
                        "status": "OK",
                        "provider": "openai-whisper",
                        "executionMode": "CLOUD_STT",
                        "cloudConfigured": True,
                        "browserSpeechPrimary": False,
                        "mimeType": audio_mime,
                        "language": language,
                        "transcript": transcript_text,
                        "messageAr": "تم تفريغ الصوت بنجاح عبر محرك OpenAI Whisper السحابي.",
                        "messageEn": "Audio transcribed successfully via OpenAI Whisper.",
                    }
                security_telemetry.emit_event(
                    "VOICE_CLOUD_STT_DEGRADED",
                    severity="WARNING",
                    details={"httpStatus": resp.status_code, "mimeType": audio_mime},
                )
        except Exception as exc:
            security_telemetry.emit_event(
                "VOICE_CLOUD_STT_ERROR",
                severity="WARNING",
                details={"errorType": type(exc).__name__},
            )

    return {
        "status": "FALLBACK_READY",
        "provider": "web-speech-primary",
        "executionMode": "BROWSER_SPEECH_FALLBACK",
        "cloudConfigured": bool(openai_key),
        "browserSpeechPrimary": True,
        "mimeType": audio_mime,
        "language": language,
        "receivedAudioBytes": len(audio_bytes) if audio_bytes else 0,
        "transcript": fallback_transcript,
        "messageAr": (
            "التعرف الصوتي الفوري يعمل عبر المتصفح (SpeechRecognition / webkitSpeechRecognition) كمسار أساسي منخفض الكمون؛ "
            "ويتفعل التفريغ السحابي الخلفي تلقائياً عند تهيئة OPENAI_API_KEY."
        ),
        "messageEn": (
            "Browser SpeechRecognition / webkitSpeechRecognition is active as the primary low-latency engine; "
            "cloud Whisper STT activates automatically when OPENAI_API_KEY is configured."
        ),
    }


async def handle_tts_request(payload: dict[str, Any]) -> tuple[bytes, str, dict[str, Any]]:
    """
    معالجة طلبات تحويل النص إلى نطق صوتي (POST /api/voice/tts).
    تعيد (البايتات الصوتية، نوع الوسائط، البيانات الوصفية الكاملة).
    """
    text = str(payload.get("text") or "مركز القيادة الهولوغرامي جاهز.").strip()
    language = "en" if str(payload.get("language") or "ar").lower().startswith("en") else "ar"
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    tts_url = os.getenv("OPENAI_TTS_URL", "https://api.openai.com/v1/audio/speech").strip()

    if openai_key and text:
        try:
            async with create_outbound_async_http_client(tts_url, timeout_sec=10.0) as client:
                resp = await client.post(
                    tts_url,
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": os.getenv("OPENAI_TTS_MODEL", "tts-1"),
                        "voice": os.getenv("OPENAI_TTS_VOICE", "onyx"),
                        "input": text[:800],
                        "response_format": "wav",
                    },
                )
                if resp.status_code == 200 and resp.content[:4] == b"RIFF":
                    audio_bytes = resp.content
                    b64 = base64.b64encode(audio_bytes).decode("ascii")
                    meta = {
                        "status": "OK",
                        "provider": "openai-tts",
                        "executionMode": "CLOUD_TTS",
                        "mimeType": "audio/wav",
                        "language": language,
                        "interruptible": True,
                        "audioBase64": b64,
                        "dataUri": f"data:audio/wav;base64,{b64}",
                        "byteLength": len(audio_bytes),
                        "messageAr": "تم توليد الصوت عبر المزود السحابي بصيغة WAV قابلة للمقاطعة الفورية.",
                        "messageEn": "Synthesized speech via cloud TTS in interruptible WAV format.",
                    }
                    return audio_bytes, "audio/wav", meta
        except Exception as exc:
            security_telemetry.emit_event(
                "VOICE_CLOUD_TTS_ERROR",
                severity="WARNING",
                details={"errorType": type(exc).__name__},
            )

    wav_bytes = generate_holo_chime_wav_bytes(text=text, language=language)
    b64_wav = base64.b64encode(wav_bytes).decode("ascii")
    duration_ms = int((len(wav_bytes) - 44) / 2 / 22050 * 1000)

    metadata = {
        "status": "OK",
        "provider": "speech-synthesis+server-wav",
        "executionMode": "LOCAL_WAV_AND_BROWSER_TTS",
        "mimeType": "audio/wav",
        "language": language,
        "interruptible": True,
        "durationMs": duration_ms,
        "byteLength": len(wav_bytes),
        "audioBase64": b64_wav,
        "dataUri": f"data:audio/wav;base64,{b64_wav}",
        "text": text,
        "messageAr": "تم توليد إشارة WAV قياسية مساندة بالتكامل مع محرك النطق الفوري القابل للمقاطعة في المتصفح.",
        "messageEn": "Generated valid RIFF WAV audio cue paired with interruptible browser SpeechSynthesis.",
    }
    return wav_bytes, "audio/wav", metadata
