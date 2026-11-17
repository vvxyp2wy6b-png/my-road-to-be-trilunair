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

export interface SpeechEngineController {
  sttSupported: boolean;
  ttsSupported: boolean;
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
  const sttSupported = Boolean(recognitionCtor);
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
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  const requestExplicitMicAuthorization = useCallback(async (): Promise<boolean> => {
    setErrorMessage(null);
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      if (sttSupported) {
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
  }, [recognitionLang, sttSupported]);

  const revokeMicAuthorization = useCallback(() => {
    stopListening();
    interruptSpeech();
    setVoiceAuthorized(false);
    voiceAuthorizedRef.current = false;
    setMicPermission('prompt');
  }, [stopListening, interruptSpeech]);

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
      setMicPermission('unsupported');
      setErrorMessage(
        recognitionLang === 'ar'
          ? 'التعرف الصوتي المدمج غير متوفر في هذا المتصفح؛ استخدم حقل الإدخال النصي.'
          : 'Web Speech Recognition is not supported in this browser; please use text input.'
      );
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
  }, [interruptSpeech, mode, recognitionLang]);

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
