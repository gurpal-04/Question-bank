from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class VoteType(str, Enum):
    UP = "up"
    DOWN = "down"


class CreateFeatureRequestRequest(BaseModel):
    """Request model for creating a feature request"""

    title: str = Field(..., min_length=3, max_length=140, description="Short title")
    description: str = Field(
        ..., min_length=10, max_length=2000, description="Detailed description"
    )


class VoteRequest(BaseModel):
    """Request model for voting on a feature request"""

    vote: VoteType = Field(..., description="Vote value: 'up' or 'down'")


class FeatureRequestResponse(BaseModel):
    """Response model for feature request"""

    id: str
    title: str
    description: str
    created_by: str
    created_by_email: Optional[str] = None
    upvotes: int = 0
    downvotes: int = 0
    score: int = 0
    created_at: datetime
    updated_at: datetime


class FeatureRequestListResponse(BaseModel):
    """Response model for feature request list"""

    feature_requests: List[FeatureRequestResponse]
    total: int
