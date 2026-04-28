"""
MindfulTrack — AI Diary Service
--------------------------------
Endpoints
  POST /ai-diary/voice-diary     : audio  → transcript
  POST /ai-diary/analyze-diary   : text   → AI wellness insights
  POST /ai-diary/voice-analyze   : audio  → transcript → AI insights (pipeline)

Speech-to-Text : OpenAI Whisper (local, zero cost)
                 A Deepgram Nova-2 alternative is included as a commented block.
AI Analysis    : Google Gemini 2.0 Flash
"""

import asyncio
import json
import os
import shutil
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.config import settings
from app.models.user import User
from app.utils.dependencies import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class VoiceDiaryResponse(BaseModel):
    transcript: str
    word_count: int


class DiaryAnalysisResponse(BaseModel):
    mood_detected: str
    key_themes: list[str]
    recommendation: str
    affirmation: str


class VoiceAnalyzeResponse(BaseModel):
    transcript: str
    word_count: int
    mood_detected: str
    key_themes: list[str]
    recommendation: str
    affirmation: str


# ---------------------------------------------------------------------------
# Service: Speech-to-Text  (Whisper local / Deepgram cloud)
# ---------------------------------------------------------------------------

# BCP-47 → Whisper language code
_LANGUAGE_MAP: dict[str, str] = {
    "en-US": "en",
    "ru-RU": "ru",
    "tr-TR": "tr",
}

# Module-level cache — avoids reloading ~150 MB Whisper weights on every request
_whisper_model_cache: dict[str, object] = {}


def _get_whisper_model():
    """Load (or return cached) Whisper model specified by WHISPER_MODEL env var."""
    name = settings.WHISPER_MODEL
    if name not in _whisper_model_cache:
        try:
            import whisper  # openai-whisper
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="openai-whisper is not installed. Run: pip install openai-whisper",
            ) from exc
        _whisper_model_cache[name] = whisper.load_model(name)
    return _whisper_model_cache[name]


def _patch_ffmpeg_path() -> None:
    """
    On Windows, imageio_ffmpeg ships a binary named ffmpeg-win64-*.exe.
    Whisper calls 'ffmpeg' by name, so we create a same-directory alias and
    prepend that folder to PATH.
    """
    try:
        import imageio_ffmpeg
    except ImportError:
        return  # ffmpeg must be on PATH manually if imageio_ffmpeg is absent

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)

    alias = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(alias):
        shutil.copy2(ffmpeg_exe, alias)

    if ffmpeg_dir not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


def _whisper_transcribe(audio_path: str, language_code: str) -> str:
    """
    Blocking Whisper call — run via asyncio.to_thread so it does not stall
    the FastAPI event loop.
    """
    lang = _LANGUAGE_MAP.get(language_code)
    if not lang:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language '{language_code}'. Supported: en-US, ru-RU, tr-TR.",
        )

    # English-only checkpoints (*.en) cannot handle Russian / Turkish
    if settings.WHISPER_MODEL.endswith(".en") and lang != "en":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The selected Whisper model is English-only. "
                "Set WHISPER_MODEL=base (or small/medium/large) for multilingual support."
            ),
        )

    _patch_ffmpeg_path()
    model = _get_whisper_model()
    result = model.transcribe(audio_path, language=lang, fp16=False)
    return (result.get("text") or "").strip()


def _resolve_audio_suffix(filename: str | None, content_type: str | None) -> str:
    """Pick a file extension for the temp file so ffmpeg can identify the codec."""
    if filename and "." in filename:
        return os.path.splitext(filename)[1]
    ct = (content_type or "").lower()
    if "ogg" in ct:
        return ".ogg"
    if "wav" in ct or "wave" in ct:
        return ".wav"
    if "mp4" in ct:
        return ".mp4"
    return ".webm"  # default for browser MediaRecorder output


async def speech_to_text(audio_file: UploadFile, language_code: str = "en-US") -> str:
    """
    Transcribe an uploaded audio file to plain text.

    Uses Whisper (local) by default.
    To switch to Deepgram Nova-2, set DEEPGRAM_API_KEY in .env and uncomment
    the Deepgram block at the bottom of this function.

    Args:
        audio_file:    FastAPI UploadFile from the multipart request.
        language_code: BCP-47 tag — en-US | ru-RU | tr-TR.

    Returns:
        Transcribed text string.
    """
    # Read audio into memory and guard against empty / oversized files
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is empty.",
        )
    if len(audio_bytes) > 25 * 1024 * 1024:  # 25 MB hard cap
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds the 25 MB limit.",
        )

    # Whisper needs a real file path, not an in-memory buffer
    suffix = _resolve_audio_suffix(audio_file.filename, audio_file.content_type)
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        # Off-load the blocking CPU work to a thread pool
        return await asyncio.to_thread(_whisper_transcribe, temp_path, language_code)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Whisper transcription failed. "
                "Check that ffmpeg is available and the audio format is supported."
            ),
        ) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    # -----------------------------------------------------------------------
    # DEEPGRAM ALTERNATIVE
    # Set DEEPGRAM_API_KEY in .env and uncomment below to use Deepgram Nova-2
    # instead of local Whisper (no GPU / local model required).
    # -----------------------------------------------------------------------
    # import httpx
    # deepgram_key = getattr(settings, "DEEPGRAM_API_KEY", "") or os.getenv("DEEPGRAM_API_KEY", "")
    # if not deepgram_key:
    #     raise HTTPException(status_code=503, detail="DEEPGRAM_API_KEY is not set.")
    # lang = _LANGUAGE_MAP.get(language_code, "en")
    # async with httpx.AsyncClient(timeout=30) as client:
    #     resp = await client.post(
    #         "https://api.deepgram.com/v1/listen",
    #         headers={
    #             "Authorization": f"Token {deepgram_key}",
    #             "Content-Type": audio_file.content_type or "audio/wav",
    #         },
    #         params={"model": "nova-2", "language": lang, "smart_format": "true"},
    #         content=audio_bytes,
    #     )
    # if resp.status_code != 200:
    #     raise HTTPException(status_code=502, detail=f"Deepgram error: {resp.text}")
    # return resp.json()["results"]["channels"][0]["alternatives"][0]["transcript"]


# ---------------------------------------------------------------------------
# Service: AI Analysis  (Google Gemini 2.0 Flash)
# ---------------------------------------------------------------------------

_ANALYSIS_SYSTEM_PROMPT = """You are a compassionate mental wellness companion in MindfulTrack.

Analyze the diary entry provided and return ONLY a valid JSON object with these exact keys:

{
  "mood_detected": <one of: "positive" | "neutral" | "anxious" | "sad" | "stressed" | "overwhelmed">,
  "key_themes": [<2-4 short phrase strings>],
  "recommendation": "<2-3 sentence warm, practical lifestyle tip — sleep, movement, breathing, journaling, social connection>",
  "affirmation": "<one short encouraging sentence personalized to the entry>"
}

RULES:
- You are NOT a therapist or doctor. Never diagnose or prescribe medications.
- If the entry expresses a crisis or self-harm, include in recommendation:
  "If you are struggling, please reach out to a mental health professional or a crisis helpline."
- Return ONLY the JSON object — no markdown fences, no extra text.
- Match the response language to the diary entry language (English / Russian / Turkish).
"""


async def analyze_text(diary_text: str) -> dict:
    """
    Send diary text to Gemini and return structured mental wellness insights.

    Args:
        diary_text: Raw text from the user's diary entry.

    Returns:
        dict with keys: mood_detected, key_themes, recommendation, affirmation.
    """
    if not diary_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diary text cannot be empty.",
        )

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured. Add it to your .env file.",
        )

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=_ANALYSIS_SYSTEM_PROMPT,
        )

        # Ask Gemini to analyse the diary entry
        raw = model.generate_content(f"Diary entry:\n\n{diary_text}")
        text = raw.text.strip()

        # Strip markdown code fences in case Gemini wraps its output
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        parsed: dict = json.loads(text)

        # Validate all required keys are present before returning
        required = {"mood_detected", "key_themes", "recommendation", "affirmation"}
        missing = required - parsed.keys()
        if missing:
            raise ValueError(f"Gemini response is missing required keys: {missing}")

        return parsed

    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned an unexpected response format: {exc}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis service is temporarily unavailable. Please try again later.",
        ) from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/voice-diary",
    response_model=VoiceDiaryResponse,
    summary="Transcribe a voice diary entry",
)
async def voice_diary(
    audio_file: UploadFile = File(..., description="Audio file — wav, ogg, webm, or mp4"),
    language_code: str = Form("en-US", description="BCP-47 language: en-US | ru-RU | tr-TR"),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a voice recording and receive its text transcription.

    Example request:
        curl -X POST http://localhost:8000/api/ai-diary/voice-diary
          -H "Authorization: Bearer <token>"
          -F "audio_file=@entry.wav"
          -F "language_code=en-US"

    Example response:
        {
          "transcript": "Today was a good day. I went for a long walk in the park.",
          "word_count": 14
        }
    """
    del current_user  # auth enforced by dependency; user object not needed here

    transcript = await speech_to_text(audio_file, language_code)

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transcription produced empty text. Check audio clarity or the language setting.",
        )

    return VoiceDiaryResponse(
        transcript=transcript,
        word_count=len(transcript.split()),
    )


@router.post(
    "/analyze-diary",
    response_model=DiaryAnalysisResponse,
    summary="Analyze a written diary entry with AI",
)
async def analyze_diary(
    text: str = Form(..., description="Diary entry text to analyze"),
    current_user: User = Depends(get_current_user),
):
    """
    Submit diary text and receive mental wellness insights from Gemini.

    Example request:
        curl -X POST http://localhost:8000/api/ai-diary/analyze-diary
          -H "Authorization: Bearer <token>"
          -F "text=I've been feeling overwhelmed with work deadlines. Hard to sleep."

    Example response:
        {
          "mood_detected": "stressed",
          "key_themes": ["work pressure", "sleep difficulty", "overwhelm"],
          "recommendation": "Try a 10-minute breathing exercise before bed. Limiting screens in the last hour of the day can significantly improve sleep quality.",
          "affirmation": "You are handling more than most people realise, and you are doing great."
        }
    """
    del current_user

    result = await analyze_text(text)
    return DiaryAnalysisResponse(**result)


@router.post(
    "/voice-analyze",
    response_model=VoiceAnalyzeResponse,
    summary="Transcribe and analyze a voice diary entry (full pipeline)",
)
async def voice_analyze(
    audio_file: UploadFile = File(..., description="Audio file — wav, ogg, webm, or mp4"),
    language_code: str = Form("en-US", description="BCP-47 language: en-US | ru-RU | tr-TR"),
    current_user: User = Depends(get_current_user),
):
    """
    Full one-shot pipeline: audio → Whisper transcript → Gemini analysis.

    Saves the client from making two separate HTTP calls.

    Example request:
        curl -X POST http://localhost:8000/api/ai-diary/voice-analyze
          -H "Authorization: Bearer <token>"
          -F "audio_file=@entry.wav"
          -F "language_code=en-US"

    Example response:
        {
          "transcript": "Today was really stressful. I couldn't focus at work at all.",
          "word_count": 13,
          "mood_detected": "stressed",
          "key_themes": ["focus difficulty", "work stress"],
          "recommendation": "A short walk outside can reset your mind after a demanding day.",
          "affirmation": "Every challenging day builds resilience you will be grateful for later."
        }
    """
    del current_user

    # Step 1 — transcribe audio to text
    transcript = await speech_to_text(audio_file, language_code)

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transcription produced empty text. Check audio clarity or the language setting.",
        )

    # Step 2 — analyse the transcript with Gemini
    analysis = await analyze_text(transcript)

    return VoiceAnalyzeResponse(
        transcript=transcript,
        word_count=len(transcript.split()),
        **analysis,
    )
