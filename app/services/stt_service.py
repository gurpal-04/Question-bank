import asyncio
import logging
import time
from typing import Optional

import litellm
from fastapi import UploadFile

from app.models.stt import TranscribeResponse

logger = logging.getLogger(__name__)

_EXT_BY_CONTENT_TYPE = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".mp4",
    "audio/m4a": ".m4a",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/webm": ".webm",
    "audio/flac": ".flac",
}


class SttService:
    """Service for speech-to-text transcription using LiteLLM."""

    async def transcribe(
        self,
        file: UploadFile,
    ) -> TranscribeResponse:
        start = time.perf_counter()

        # Read bytes to preserve filename/extension for upstream API
        audio_bytes = await file.read()
        content_type = (file.content_type or "").split(";")[0].strip().lower()
        filename = file.filename or "audio"
        if "." not in filename:
            filename += _EXT_BY_CONTENT_TYPE.get(content_type, ".wav")

        def _call(primary_model: str):
            return litellm.transcription(
                model=primary_model,
                file=(filename, audio_bytes, content_type or "application/octet-stream"),
                response_format="json",
                temperature=0.0,
            )

        primary_model = "groq/whisper-large-v3"
        fallback_model = "groq/whisper-large-v3-turbo"

        logger.info(
            "STT: start transcription model=%s filename=%s content_type=%s bytes=%s",
            primary_model,
            filename,
            content_type,
            len(audio_bytes),
        )
        try:
            response = await asyncio.to_thread(_call, primary_model)
            used_model = primary_model
        except Exception as e:
            logger.warning(
                "STT: primary model failed, falling back model=%s error=%s",
                fallback_model,
                e,
            )
            response = await asyncio.to_thread(_call, fallback_model)
            used_model = fallback_model
        duration_ms = (time.perf_counter() - start) * 1000

        text = None
        if hasattr(response, "text"):
            text = response.text
        elif isinstance(response, dict):
            text = response.get("text")

        if not text:
            text = str(response)

        logger.info(
            "STT: completed transcription model=%s duration_ms=%.2f text_len=%s",
            used_model,
            duration_ms,
            len(text) if text else 0,
        )

        return TranscribeResponse(text=text, model=used_model, duration_ms=duration_ms)
