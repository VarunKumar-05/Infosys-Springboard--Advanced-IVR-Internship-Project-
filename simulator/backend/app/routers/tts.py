from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
import asyncio

router = APIRouter(prefix="/api/tts", tags=["Text To Speech"])

async def synthesize_speech(text: str, voice: str | None = None) -> bytes:
    """
    Generate speech using Google Cloud Text-to-Speech (Chirp 3 HD voice).
    """
    def _synthesize():
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Select a Chirp 3 HD voice
        voice_name = voice or "en-US-Chirp3-HD-Puck"
        voice_params = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )
        return response.audio_content

    try:
        return await asyncio.to_thread(_synthesize)
    except Exception as e:
        print(f"[TTS] Synthesis error: {e}")
        return b""

class TTSRequest(BaseModel):
    text: str
    voice: str | None = None

@router.post("/synthesize", summary="Convert text to speech audio (mp3)")
async def tts_endpoint(body: TTSRequest):
    """Generate mp3 speech audio from text using Google Chirp 3."""
    audio = await synthesize_speech(body.text, body.voice)
    return Response(content=audio, media_type="audio/mpeg")
