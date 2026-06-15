import { useEffect, useMemo, useRef, useState } from 'react';
import api from '../api/axios';
import { composeVoiceNoteContent } from '../utils/diaryHelpers';

/**
 * Encapsulates the Diary voice-note subsystem: MediaRecorder capture, live
 * browser SpeechRecognition, the mm:ss timer, and Whisper transcription.
 *
 * @param {object} params
 * @param {string} params.content - Current editor content; snapshotted as the
 *   base when a recording starts so the transcript can be appended to it.
 * @param {(value: string) => void} params.setContent - Setter used to write the
 *   composed (base + voice note) content back into the editor on save.
 */
export const useVoiceRecorder = ({ content, setContent }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [transcript, setTranscript] = useState('');
  const [voiceLanguage, setVoiceLanguage] = useState('en-US');
  const [recordingError, setRecordingError] = useState('');
  const [recordingStatus, setRecordingStatus] = useState('Ready');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);

  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const recognitionRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioMimeTypeRef = useRef('');
  const voiceNoteBaseContentRef = useRef('');
  const browserFinalTranscriptRef = useRef('');
  const liveTranscriptRef = useRef('');
  const voiceLanguageRef = useRef('en-US');
  const isPausedRef = useRef(false);
  const isRecordingRef = useRef(false);
  const timerRef = useRef(null);

  const speechSupported = useMemo(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
  }, []);

  const browserSpeechSupported = useMemo(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }, []);

  useEffect(() => {
    voiceLanguageRef.current = voiceLanguage;
  }, [voiceLanguage]);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  // Cleanup active audio capture on unmount
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (error) {
          // Ignore abort errors during unmount cleanup.
        }
      }
    };
  }, []);

  /* ---------- Helper: start the mm:ss timer ---------- */
  const startTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    timerRef.current = setInterval(() => {
      setRecordSeconds((prev) => prev + 1);
    }, 1000);
  };

  /* ---------- Helper: stop the mm:ss timer ---------- */
  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  /* ---------- Helper: create and transcribe an audio recording ---------- */
  const getAudioMimeType = () => {
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
      'audio/mp4',
    ];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || '';
  };

  const stopMediaStream = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  };

  const applyLiveVoiceText = (text) => {
    const liveText = (text || '').trim();
    liveTranscriptRef.current = liveText;
  };

  const stopBrowserRecognition = (useAbort = true) => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      return;
    }

    try {
      if (useAbort) {
        recognition.abort();
      } else {
        recognition.stop();
      }
    } catch (error) {
      // Ignore stop/abort race conditions from browser API.
    }
  };

  const startBrowserRecognition = () => {
    if (!browserSpeechSupported) {
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!recognitionRef.current) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        let interimText = '';
        let finalChunk = '';

        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const segment = event.results[i][0]?.transcript || '';
          if (event.results[i].isFinal) {
            finalChunk += segment;
          } else {
            interimText += segment;
          }
        }

        if (finalChunk.trim()) {
          browserFinalTranscriptRef.current = `${browserFinalTranscriptRef.current} ${finalChunk}`.trim();
          setTranscript(browserFinalTranscriptRef.current);
        }

        setInterimTranscript(interimText.trim());
        const mergedLiveText = `${browserFinalTranscriptRef.current} ${interimText}`.trim();
        applyLiveVoiceText(mergedLiveText);
      };

      recognition.onerror = (event) => {
        if (isRecordingRef.current && event.error !== 'aborted') {
          setRecordingError(`Live speech error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        if (!isRecordingRef.current || isPausedRef.current) {
          return;
        }
        try {
          recognition.lang = voiceLanguageRef.current;
          recognition.start();
        } catch (error) {
          // Browser may reject rapid restarts; ignore and keep Whisper finalization.
        }
      };

      recognitionRef.current = recognition;
    }

    try {
      recognitionRef.current.lang = voiceLanguageRef.current;
      recognitionRef.current.start();
    } catch (error) {
      // Ignore duplicate start errors if recognition is already active.
    }
  };

  const stopRecorder = () =>
    new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      const mimeType = audioMimeTypeRef.current || recorder?.mimeType || 'audio/webm';

      const buildBlob = () => new Blob(audioChunksRef.current, { type: mimeType });

      if (!recorder || recorder.state === 'inactive') {
        stopMediaStream();
        resolve(buildBlob());
        return;
      }

      recorder.onstop = () => {
        stopMediaStream();
        mediaRecorderRef.current = null;
        resolve(buildBlob());
      };
      recorder.stop();
    });

  const transcribeRecording = async (audioBlob) => {
    if (!audioBlob.size) {
      return '';
    }

    const extension = audioBlob.type.includes('ogg') ? 'ogg' : audioBlob.type.includes('mp4') ? 'mp4' : 'webm';
    const formData = new FormData();
    formData.append('audio_file', audioBlob, `voice-note.${extension}`);
    formData.append('language_code', voiceLanguage);

    const response = await api.post('/diary/speech-to-text', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return (response.data?.transcript || '').trim();
  };

  /* ---------- Start recording (Whisper upload) ---------- */
  const startRecording = async () => {
    if (!speechSupported || isRecordingRef.current || isTranscribing) {
      return;
    }

    setRecordingError('');
    setRecordingStatus('Listening...');

    if (!isPaused) {
      setTranscript('');
      setInterimTranscript('');
      setRecordSeconds(0);
      audioChunksRef.current = [];
      voiceNoteBaseContentRef.current = content;
      browserFinalTranscriptRef.current = '';
      liveTranscriptRef.current = '';
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getAudioMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      audioMimeTypeRef.current = mimeType || recorder.mimeType || 'audio/webm';
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data?.size) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onerror = () => {
        setRecordingError('Recording failed. Please try again.');
        stopTimer();
        stopMediaStream();
        isRecordingRef.current = false;
        setIsRecording(false);
        setIsPaused(false);
        setRecordingStatus('Ready');
      };

      isRecordingRef.current = true;
      setIsRecording(true);
      setIsPaused(false);
      recorder.start(1000);
      startBrowserRecognition();
      startTimer();
    } catch (error) {
      setRecordingError('Microphone access was blocked or unavailable.');
      setRecordingStatus('Ready');
      stopMediaStream();
      isRecordingRef.current = false;
      setIsRecording(false);
      setIsPaused(false);
      if (!isPaused) {
        setRecordSeconds(0);
      }
    }
  };

  /* ---------- Pause recording ---------- */
  const pauseRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || !isRecordingRef.current) {
      return;
    }

    isRecordingRef.current = false;
    setIsPaused(true);
    setRecordingStatus('Paused');
    setInterimTranscript('');

    if (recorder.state === 'recording') {
      recorder.pause();
    }
    stopBrowserRecognition();
    stopTimer();
  };

  /* ---------- Resume recording ---------- */
  const resumeRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== 'paused') {
      startRecording();
      return;
    }

    setRecordingError('');
    recorder.resume();
    isRecordingRef.current = true;
    setIsRecording(true);
    setIsPaused(false);
    setRecordingStatus('Listening...');
    startBrowserRecognition();
    startTimer();
  };

  /* ---------- Stop, transcribe, and save ---------- */
  const stopAndSaveRecording = async () => {
    if (!mediaRecorderRef.current && !audioChunksRef.current.length) {
      return;
    }

    isRecordingRef.current = false;
    setIsRecording(false);
    setIsPaused(false);
    stopBrowserRecognition();
    stopTimer();
    setIsTranscribing(true);
    setRecordingStatus('Transcribing...');

    try {
      const audioBlob = await stopRecorder();
      const finalVoiceNote = await transcribeRecording(audioBlob);
      const resolvedVoiceNote = finalVoiceNote || liveTranscriptRef.current;
      setTranscript(resolvedVoiceNote);
      setInterimTranscript('');
      applyLiveVoiceText(resolvedVoiceNote);
      setContent(composeVoiceNoteContent(voiceNoteBaseContentRef.current, resolvedVoiceNote));
      setRecordingStatus('Saved');
    } catch (error) {
      console.error('Failed to transcribe voice note', error);
      setRecordingError(error.response?.data?.detail || 'Whisper transcription failed. Please try again.');
      setRecordingStatus('Ready');
    } finally {
      setIsTranscribing(false);
    }
  };

  /* ---------- Discard recording ---------- */
  const discardRecording = async () => {
    if (mediaRecorderRef.current) {
      await stopRecorder();
    } else {
      stopMediaStream();
    }

    stopBrowserRecognition();

    isRecordingRef.current = false;
    setIsRecording(false);
    setIsPaused(false);
    setTranscript('');
    setInterimTranscript('');
    browserFinalTranscriptRef.current = '';
    liveTranscriptRef.current = '';
    voiceNoteBaseContentRef.current = '';
    setRecordingStatus('Ready');
    setRecordingError('');
    setRecordSeconds(0);
    stopTimer();
  };

  /* ---------- Reset transcript state after the entry is saved ---------- */
  const resetVoiceState = () => {
    voiceNoteBaseContentRef.current = '';
    browserFinalTranscriptRef.current = '';
    liveTranscriptRef.current = '';
    setTranscript('');
    setInterimTranscript('');
    setRecordingStatus('Ready');
  };

  return {
    isRecording,
    isPaused,
    recordSeconds,
    transcript,
    interimTranscript,
    voiceLanguage,
    setVoiceLanguage,
    recordingError,
    recordingStatus,
    isTranscribing,
    speechSupported,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopAndSaveRecording,
    discardRecording,
    resetVoiceState,
  };
};

export default useVoiceRecorder;
