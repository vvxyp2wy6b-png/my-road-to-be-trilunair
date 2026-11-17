/**
 * محرك الصوت الموحد (التعرف على الكلام العربي والإنجليزي + تحويل النص إلى كلام القابل للمقاطعة)
 * My Road to be Trilunair Dr.MaJoOoOoOoD
 *
 * مبادئ الأمان والخصوصية:
 * 1. لا يتم طلب الميكروفون أو تشغيل الاستماع نهائياً عند تحميل الصفحة دون إذن صريح من المستخدم.
 * 2. يدعم وضعي اضغط للتحدث (Push-to-Talk) والمحادثة الحرة المصرح بها (Hands-Free).
 * 3. يدعم المقاطعة الفورية للردود الصوتية (Interruptible TTS) بزر مخصص أو عند بدء المستخدم بالتحدث.
 * 4. تعمل المحادثة النصية بشكل مستقل تماماً حتى في حال عدم توفر الميكروفون أو رفض الإذن.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Language } from '../types/trilunair';

export type MicPermissionState = 'prompt' | 'granted' | 'denied' | 'unsupported';
export type VoiceInteractionMode = 'push-to-talk' | 'hands-free';
export type VoiceStatus =
  | 'unauthorized'
  | 'ready'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'error';

interface BrowserSpeechRecognitionEvent {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [altIndex: number]: {
        transcript: string;
        confidence: number;
      };
    };
  };
}

interface BrowserSpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognitionInstance;

function getSpeechRecognitionCtor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as Record<string, unknown>;
  return (
    (w.SpeechRecognition as SpeechRecognitionConstructor | undefined) ||
    (w.webkitSpeechRecognition as SpeechRecognitionConstructor | undefined) ||
    null
  );
}

export function detectPreferredRecorderMimeType(): string {
  if (typeof window === 'undefined' || typeof MediaRecorder === 'undefined') {
    return 'audio/mp4';
  }
  const candidates = [
    'audio/mp4',
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/wav',
  ];
  if (typeof MediaRecorder.isTypeSupported === 'function') {
    for (const mime of candidates) {
      try {
        if (MediaRecorder.isTypeSupported(mime)) {
          return mime;
        }
      } catch {
        // المتابعة للخيار التالي
      }
    }
  }
  return 'audio/mp4';
}

function unlockSafariWebAudioGesture(): void {
  if (typeof window === 'undefined') return;
  try {
    const w = window as unknown as Record<string, unknown>;
    const AudioCtx = (w.AudioContext || w.webkitAudioContext) as (new () => AudioContext) | undefined;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    if (ctx.state === 'suspended') {
      void ctx.resume().finally(() => {
        void ctx.close().catch(() => {});
      });
    } else {
      void ctx.close().catch(() => {});
    }
  } catch {
    // تجاهل في البيئات غير الداعمة لـ AudioContext
  }
}

export interface SpeechEngineController {
  sttSupported: boolean;
  ttsSupported: boolean;
  preferredAudioMimeType?: string;
  micPermission: MicPermissionState;
  voiceAuthorized: boolean;
  mode: VoiceInteractionMode;
  setMode: (mode: VoiceInteractionMode) => void;
  recognitionLang: Language;
  setRecognitionLang: (lang: Language) => void;
  autoSpeakResponses: boolean;
  setAutoSpeakResponses: (enabled: boolean) => void;
  status: VoiceStatus;
  isListening: boolean;
  isSpeaking: boolean;
  activeSpeakerLabel: string | null;
  interimTranscript: string;
  errorMessage: string | null;
  requestExplicitMicAuthorization: () => Promise<boolean>;
  revokeMicAuthorization: () => void;
  startListening: () => void;
  stopListening: () => void;
  speakText: (text: string, lang: Language, speakerLabel?: string) => void;
  speakSequence: (
    segments: Array<{ text: string; lang: Language; speakerLabel: string }>
  ) => void;
  interruptSpeech: () => void;
}

export function useSpeechEngine(
  defaultLang: Language,
  onFinalTranscript?: (transcript: string, lang: Language) => void
): SpeechEngineController {
  const recognitionCtor = getSpeechRecognitionCtor();
  const mediaRecorderAvailable =
    typeof window !== 'undefined' && typeof MediaRecorder !== 'undefined';
  const sttSupported = Boolean(recognitionCtor) || mediaRecorderAvailable;
  const preferredAudioMimeType = detectPreferredRecorderMimeType();
  const ttsSupported =
    typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

  const [micPermission, setMicPermission] = useState<MicPermissionState>('prompt');
  const [voiceAuthorized, setVoiceAuthorized] = useState<boolean>(false);
  const [mode, setModeState] = useState<VoiceInteractionMode>('push-to-talk');
  const [recognitionLang, setRecognitionLang] = useState<Language>(defaultLang);
  const [autoSpeakResponses, setAutoSpeakResponses] = useState<boolean>(true);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [activeSpeakerLabel, setActiveSpeakerLabel] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recognitionRef = useRef<BrowserSpeechRecognitionInstance | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const handsFreeActiveRef = useRef<boolean>(false);
  const voiceAuthorizedRef = useRef<boolean>(false);
  const onFinalTranscriptRef = useRef(onFinalTranscript);
  const speechQueueCancelledRef = useRef<boolean>(false);

  useEffect(() => {
    onFinalTranscriptRef.current = onFinalTranscript;
  }, [onFinalTranscript]);

  useEffect(() => {
    setRecognitionLang(defaultLang);
  }, [defaultLang]);

  // تحميل أصوات النطق مسبقاً لمتصفح Safari على macOS/iOS حيث تُحمّل الأصوات بشكل غير متزامن
  useEffect(() => {
    if (!ttsSupported) return;
    try {
      window.speechSynthesis.getVoices();
      const handleVoicesChanged = () => {
        window.speechSynthesis.getVoices();
      };
      window.speechSynthesis.addEventListener?.('voiceschanged', handleVoicesChanged);
      return () => {
        window.speechSynthesis.removeEventListener?.('voiceschanged', handleVoicesChanged);
      };
    } catch {
      return undefined;
    }
  }, [ttsSupported]);

  const interruptSpeech = useCallback(() => {
    speechQueueCancelledRef.current = true;
    if (ttsSupported) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // تجاهل أعطال محرك النطق في البيئات المعزولة
      }
    }
    setIsSpeaking(false);
    setActiveSpeakerLabel(null);
  }, [ttsSupported]);

  const stopListening = useCallback(() => {
    handsFreeActiveRef.current = false;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // تجاهل الإيقاف المكرر
      }
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // تجاهل
      }
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  const requestExplicitMicAuthorization = useCallback(async (): Promise<boolean> => {
    setErrorMessage(null);
    unlockSafariWebAudioGesture();
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      if (recognitionCtor) {
        setMicPermission('granted');
        setVoiceAuthorized(true);
        voiceAuthorizedRef.current = true;
        return true;
      }
      setMicPermission('unsupported');
      setErrorMessage(
        recognitionLang === 'ar'
          ? 'المتصفح الحالي لا يدعم واجهة الميكروفون المباشرة؛ المحادثة النصية متاحة بالكامل.'
          : 'Direct microphone API unavailable in this browser; text commands remain 100% active.'
      );
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // نغلق المسار الصوتي فوراً بعد التحقق من الإذن لمنع أي تنصت مستمر في الخلفية!
      stream.getTracks().forEach((track) => track.stop());
      setMicPermission('granted');
      setVoiceAuthorized(true);
      voiceAuthorizedRef.current = true;
      return true;
    } catch {
      setMicPermission('denied');
      setVoiceAuthorized(false);
      voiceAuthorizedRef.current = false;
      setErrorMessage(
        recognitionLang === 'ar'
          ? 'تم رفض إذن الميكروفون. يمكنك الاستمرار باستخدام الأوامر النصية بكامل الصلاحيات.'
          : 'Microphone permission was denied. You can continue using full text chat commands.'
      );
      return false;
    }
  }, [recognitionCtor, recognitionLang]);

  const revokeMicAuthorization = useCallback(() => {
    stopListening();
    interruptSpeech();
    setVoiceAuthorized(false);
    voiceAuthorizedRef.current = false;
    setMicPermission('prompt');
  }, [stopListening, interruptSpeech]);

  const startCloudRecorderFallback = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setMicPermission('unsupported');
      setErrorMessage(
        recognitionLang === 'ar'
          ? 'التعرف الصوتي المدمج غير متوفر في هذا المتصفح؛ استخدم حقل الإدخال النصي.'
          : 'Web Speech Recognition is not supported in this browser; please use text input.'
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      recordedChunksRef.current = [];
      const mimeType = detectPreferredRecorderMimeType();
      const recorder =
        typeof MediaRecorder.isTypeSupported === 'function' && MediaRecorder.isTypeSupported(mimeType)
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream);

      recorder.ondataavailable = (ev: BlobEvent) => {
        if (ev.data && ev.data.size > 0) {
          recordedChunksRef.current.push(ev.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
        const blob = new Blob(recordedChunksRef.current, { type: mimeType });
        recordedChunksRef.current = [];
        if (blob.size === 0) return;

        try {
          const ext = mimeType.includes('mp4') ? 'mp4' : mimeType.includes('wav') ? 'wav' : 'webm';
          const form = new FormData();
          form.append('file', blob, `speech.${ext}`);
          form.append('language', recognitionLang);
          const resp = await fetch('/api/voice/stt', { method: 'POST', body: form });
          if (resp.ok) {
            const data = (await resp.json()) as { transcript?: string; messageAr?: string; messageEn?: string };
            if (data.transcript && data.transcript.trim()) {
              onFinalTranscriptRef.current?.(data.transcript.trim(), recognitionLang);
            } else {
              setErrorMessage(
                recognitionLang === 'ar'
                  ? data.messageAr || 'لم يتم التقاط نص صوتي واضح؛ يمكنك استخدام الإدخال النصي.'
                  : data.messageEn || 'No speech transcript captured; text input remains ready.'
              );
            }
          }
        } catch {
          setErrorMessage(
            recognitionLang === 'ar'
              ? 'تعذر الاتصال بخدمة التفريغ الصوتي السحابية؛ الأوامر النصية متاحة فوراً.'
              : 'Cloud STT endpoint unreachable; text commands remain active.'
          );
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsListening(true);
    } catch {
      setIsListening(false);
    }
  }, [recognitionLang]);

  const startListening = useCallback(() => {
    setErrorMessage(null);
    if (!voiceAuthorizedRef.current) {
      setErrorMessage(
        recognitionLang === 'ar'
          ? 'يرجى منح إذن الميكروفون الصريح أولاً قبل بدء التسجيل.'
          : 'Please grant explicit microphone permission before recording.'
      );
      return;
    }

    // مقاطعة أي نطق جاري فور بدء المستخدم بالتحدث (Interruptible Voice)
    interruptSpeech();

    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      void startCloudRecorderFallback();
      return;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // تجاهل
      }
    }

    const instance = new Ctor();
    instance.lang = recognitionLang === 'ar' ? 'ar-SA' : 'en-US';
    instance.continuous = mode === 'hands-free';
    instance.interimResults = true;
    handsFreeActiveRef.current = mode === 'hands-free';

    instance.onstart = () => {
      setIsListening(true);
      setInterimTranscript('');
    };

    instance.onresult = (event: BrowserSpeechRecognitionEvent) => {
      let interim = '';
      let finalChunk = '';

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const res = event.results[i];
        const text = res[0]?.transcript || '';
        if (res.isFinal) {
          finalChunk += text;
        } else {
          interim += text;
        }
      }

      setInterimTranscript(interim.trim());
      if (finalChunk.trim()) {
        setInterimTranscript('');
        onFinalTranscriptRef.current?.(finalChunk.trim(), recognitionLang);
      }
    };

    instance.onerror = (event) => {
      if (event.error === 'aborted' || event.error === 'no-speech') {
        return;
      }
      setErrorMessage(
        recognitionLang === 'ar'
          ? `تنبيه التعرف الصوتي: ${event.error}`
          : `Speech recognition notice: ${event.error}`
      );
      setIsListening(false);
      handsFreeActiveRef.current = false;
    };

    instance.onend = () => {
      if (handsFreeActiveRef.current && voiceAuthorizedRef.current) {
        try {
          instance.start();
          return;
        } catch {
          // في حال تعذر إعادة التشغيل التلقائي نوقف بهدوء
        }
      }
      setIsListening(false);
      setInterimTranscript('');
    };

    recognitionRef.current = instance;
    try {
      instance.start();
    } catch {
      setIsListening(false);
    }
  }, [interruptSpeech, mode, recognitionLang, startCloudRecorderFallback]);

  const setMode = useCallback(
    (nextMode: VoiceInteractionMode) => {
      if (isListening) {
        stopListening();
      }
      setModeState(nextMode);
    },
    [isListening, stopListening]
  );

  const selectBestVoice = useCallback((lang: Language): SpeechSynthesisVoice | null => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    const prefix = lang === 'ar' ? 'ar' : 'en';
    return (
      voices.find((v) => v.lang.toLowerCase().startsWith(prefix) && v.localService) ||
      voices.find((v) => v.lang.toLowerCase().startsWith(prefix)) ||
      null
    );
  }, []);

  const speakText = useCallback(
    (text: string, lang: Language, speakerLabel?: string) => {
      if (!ttsSupported || !text.trim()) return;
      interruptSpeech();
      speechQueueCancelledRef.current = false;

      try {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = lang === 'ar' ? 'ar-SA' : 'en-US';
        const matchedVoice = selectBestVoice(lang);
        if (matchedVoice) {
          utterance.voice = matchedVoice;
        }
        utterance.rate = 1.02;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
          setIsSpeaking(true);
          setActiveSpeakerLabel(speakerLabel || (lang === 'ar' ? 'المجلس الذكي' : 'AI Council'));
        };
        utterance.onend = () => {
          setIsSpeaking(false);
          setActiveSpeakerLabel(null);
        };
        utterance.onerror = () => {
          setIsSpeaking(false);
          setActiveSpeakerLabel(null);
        };

        window.speechSynthesis.speak(utterance);
      } catch {
        setIsSpeaking(false);
        setActiveSpeakerLabel(null);
      }
    },
    [interruptSpeech, selectBestVoice, ttsSupported]
  );

  const speakSequence = useCallback(
    (segments: Array<{ text: string; lang: Language; speakerLabel: string }>) => {
      if (!ttsSupported || segments.length === 0) return;
      interruptSpeech();
      speechQueueCancelledRef.current = false;

      let idx = 0;
      const playNext = () => {
        if (speechQueueCancelledRef.current || idx >= segments.length) {
          setIsSpeaking(false);
          setActiveSpeakerLabel(null);
          return;
        }
        const seg = segments[idx];
        idx += 1;
        try {
          const utterance = new SpeechSynthesisUtterance(seg.text);
          utterance.lang = seg.lang === 'ar' ? 'ar-SA' : 'en-US';
          const matchedVoice = selectBestVoice(seg.lang);
          if (matchedVoice) {
            utterance.voice = matchedVoice;
          }
          utterance.rate = 1.03;
          utterance.onstart = () => {
            setIsSpeaking(true);
            setActiveSpeakerLabel(seg.speakerLabel);
          };
          utterance.onend = () => {
            playNext();
          };
          utterance.onerror = () => {
            setIsSpeaking(false);
            setActiveSpeakerLabel(null);
          };
          window.speechSynthesis.speak(utterance);
        } catch {
          setIsSpeaking(false);
          setActiveSpeakerLabel(null);
        }
      };

      playNext();
    },
    [interruptSpeech, selectBestVoice, ttsSupported]
  );

  useEffect(() => {
    return () => {
      handsFreeActiveRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // تنظيف عند إغلاق المكون
        }
      }
      if (ttsSupported) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // تنظيف النطق
        }
      }
    };
  }, [ttsSupported]);

  let status: VoiceStatus = 'unauthorized';
  if (errorMessage && !voiceAuthorized) {
    status = 'error';
  } else if (isSpeaking) {
    status = 'speaking';
  } else if (isListening) {
    status = 'listening';
  } else if (voiceAuthorized) {
    status = 'ready';
  }

  return {
    sttSupported,
    ttsSupported,
    preferredAudioMimeType,
    micPermission,
    voiceAuthorized,
    mode,
    setMode,
    recognitionLang,
    setRecognitionLang,
    autoSpeakResponses,
    setAutoSpeakResponses,
    status,
    isListening,
    isSpeaking,
    activeSpeakerLabel,
    interimTranscript,
    errorMessage,
    requestExplicitMicAuthorization,
    revokeMicAuthorization,
    startListening,
    stopListening,
    speakText,
    speakSequence,
    interruptSpeech,
  };
}
