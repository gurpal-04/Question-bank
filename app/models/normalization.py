from pydantic import BaseModel, Field
from typing import List


class NormalizedTopic(BaseModel):
    original: str = Field(..., description="The original messy topic name")
    normalized: str = Field(..., description="The clean, standardized search query")


class NormalizationResponse(BaseModel):
    normalized_topics: List[NormalizedTopic] = Field(
        ..., description="List of normalized topics"
    )
