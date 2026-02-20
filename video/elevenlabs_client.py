"""
ElevenLabs text-to-speech client.
Converts the full script narration into an MP3 voice-over.

API docs: https://elevenlabs.io/docs/api-reference/text-to-speech
Model: eleven_turbo_v2_5 (lowest latency, highest quality for social media)
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

_ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"

# Default voice: "Adam" — professional male, clear and authoritative
# Full list: https://api.elevenlabs.io/v1/voices
_DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"

# Model: turbo v2.5 — best balance of speed and quality
_DEFAULT_MODEL = "eleven_turbo_v2_5"


class ElevenLabsClient:
    """
    Generates an MP3 voice-over from a narration script.

    Usage:
        async with ElevenLabsClient(api_key) as client:
            path = await client.generate_voiceover(narration_text, output_path)
    """

    def __init__(self, api_key: str = "", voice_id: str = ""):
        self._api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self._voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ElevenLabsClient":
        self._client = httpx.AsyncClient(
            base_url=_ELEVENLABS_API_BASE,
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def generate_voiceover(
        self,
        narration_text: str,
        output_path: str,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.4,
        speaking_rate: float = 1.0,
    ) -> str:
        """
        Generate an MP3 voice-over from narration_text.
        Returns the local output_path where the MP3 was saved.

        Args:
            narration_text: Full script text to convert to speech
            output_path: Where to save the .mp3 file
            stability: Voice stability (0.0-1.0). Higher = more consistent
            similarity_boost: Voice clarity (0.0-1.0). Higher = closer to original voice
            style: Speaking expressiveness (0.0-1.0)
            speaking_rate: Speed multiplier (0.7-1.2 recommended for social media)
        """
        payload = {
            "text": narration_text,
            "model_id": _DEFAULT_MODEL,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": True,
            },
        }

        # Apply speaking rate if the model supports it
        if speaking_rate != 1.0:
            payload["voice_settings"]["speaking_rate"] = speaking_rate  # type: ignore[index]

        url = f"/text-to-speech/{self._voice_id}"
        params = {"output_format": "mp3_44100_128"}

        try:
            resp = await self._client.post(url, json=payload, params=params)
            resp.raise_for_status()

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)

            size_kb = len(resp.content) // 1024
            logger.info(f"[elevenlabs] voiceover saved → {output_path} ({size_kb}KB)")
            return output_path

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[elevenlabs] TTS failed: {e.response.status_code} {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"[elevenlabs] TTS error: {e}")
            raise

    async def list_voices(self) -> list[dict]:
        """Return available voices from the ElevenLabs account."""
        try:
            resp = await self._client.get("/voices")
            resp.raise_for_status()
            return resp.json().get("voices", [])
        except Exception as e:
            logger.error(f"[elevenlabs] list_voices error: {e}")
            return []
