import httpx

from app.config import get_settings

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


async def transcribe(audio_bytes: bytes, filename: str = "audio.mp3") -> str:
    """Audio naar tekst via de OpenAI Whisper API. Zonder API-key: lege fallback."""
    api_key = get_settings().openai_api_key
    if not api_key:
        return ""
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            WHISPER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, audio_bytes, "audio/mpeg")},
            data={"model": "whisper-1", "language": "nl"},
        )
        resp.raise_for_status()
        return resp.json().get("text", "")
