from pydantic import BaseModel, Field
from typing import List


class Resource(BaseModel):
    """Learning resource to help improve on weak topics"""

    title: str = Field(..., description="Title of the resource")
    type: str = Field(
        ...,
        description="Type of resource: 'blog', 'video', 'article', 'course', 'documentation', or 'tutorial'",
    )
    url: str = Field(..., description="URL to the resource")
    description: str = Field(
        ...,
        description="Brief description of what the resource covers and why it's helpful",
    )


class FeedbackResponse(BaseModel):
    """Feedback response from the feedback agent"""

    feedback: str = Field(
        ...,
        description="Personalized feedback based on the user's performance, highlighting strengths and areas for improvement.",
    )
    weak_topics: List[str] = Field(
        default_factory=list,
        description="List of specific topics or concepts where the user needs improvement based on incorrect answers",
    )
