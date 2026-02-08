from pydantic import BaseModel, Field
from typing import Optional


class TranscribeResponse(BaseModel):
    """Response model for speech-to-text transcription"""

    text: str = Field(..., description="Transcribed text")
    model: str = Field(..., description="Model used for transcription")
    duration_ms: Optional[float] = Field(
        None, description="Processing time in milliseconds"
    )
