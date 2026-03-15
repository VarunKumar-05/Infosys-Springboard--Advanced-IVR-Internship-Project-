from fastapi import APIRouter, File, UploadFile, Request
from typing import Dict
import os
import asyncio
import base64

router = APIRouter(prefix="/api/stt", tags=["Speech To Text"])


async def transcribe_audio_bytes(audio_bytes: bytes) -> str | None:
    """
    Transcribe raw audio bytes.

    Strategy:
    1. Try Google Cloud Speech-to-Text V2 (Chirp 3) if credentials are available
    2. Fall back to Gemini API multimodal transcription if GEMINI_API_KEY is set
    3. Return None if both fail
    """
    if not audio_bytes or len(audio_bytes) < 100:
        print(f"[STT] Audio too short ({len(audio_bytes) if audio_bytes else 0} bytes), skipping.")
        return None

    # ── Strategy 1: Google Cloud Speech-to-Text V2 (Chirp 3) ────────────
    result = await _try_cloud_stt(audio_bytes)
    if result is not None:
        return result

    # ── Strategy 2: Gemini multimodal transcription ─────────────────────
    result = await _try_gemini_stt(audio_bytes)
    if result is not None:
        return result

    print("[STT] All transcription strategies failed.")
    return None


async def _try_cloud_stt(audio_bytes: bytes) -> str | None:
    """Try Google Cloud Speech-to-Text V2 (Chirp 3)."""
    try:
        from google.cloud.speech_v2 import SpeechClient
        from google.cloud.speech_v2.types import cloud_speech

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        if not project_id:
            print("[STT] GOOGLE_CLOUD_PROJECT not set, skipping Cloud STT.")
            return None

        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        def _transcribe():
            client = SpeechClient()
            config = cloud_speech.RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=["en-US"],
                model="chirp_3",
            )
            request = cloud_speech.RecognizeRequest(
                recognizer=f"projects/{project_id}/locations/{location}/recognizers/_",
                config=config,
                content=audio_bytes
            )
            response = client.recognize(request=request)
            for result in response.results:
                return result.alternatives[0].transcript
            return ""

        transcript = await asyncio.to_thread(_transcribe)
        if transcript:
            print(f"[STT] Cloud STT success: '{transcript[:80]}...'")
            return transcript
        print("[STT] Cloud STT returned empty transcript.")
        return None
    except Exception as e:
        print(f"[STT] Cloud STT error: {e}")
        return None


async def _try_gemini_stt(audio_bytes: bytes) -> str | None:
    """Use Gemini multimodal API to transcribe audio."""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        print("[STT] google-genai not installed, skipping Gemini STT.")
        return None

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        print("[STT] Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set, skipping Gemini STT.")
        return None

    def _transcribe():
        client = genai.Client(api_key=gemini_key)

        # Send audio as inline data to Gemini for transcription
        audio_part = genai_types.Part(
            inline_data=genai_types.Blob(
                mime_type="audio/webm",
                data=audio_bytes,
            )
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                genai_types.Content(
                    role="user",
                    parts=[
                        audio_part,
                        genai_types.Part(text=(
                            "Transcribe the spoken words in this audio clip exactly as said. "
                            "Return ONLY the transcription text, nothing else. "
                            "If no speech is detected, return an empty string."
                        )),
                    ],
                )
            ],
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=500,
            ),
        )

        transcript = response.text.strip() if response.text else ""
        return transcript

    try:
        transcript = await asyncio.to_thread(_transcribe)
        if transcript:
            print(f"[STT] Gemini STT success: '{transcript[:80]}...'")
            return transcript
        print("[STT] Gemini STT returned empty transcript.")
        return None
    except Exception as e:
        print(f"[STT] Gemini STT error: {e}")
        return None


@router.post("/chirp3", summary="Run Google Cloud Chirp 3 STT")
async def stt_chirp3(request: Request, audio_file: UploadFile = File(...)) -> Dict:
    transcript = await transcribe_audio_bytes(await audio_file.read())
    if transcript is None:
        return {"error": "Failed to transcribe audio. Check server logs for details."}
    return {"transcript": transcript}
