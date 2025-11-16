from pydantic import BaseModel, Field


class FeedbackResponse(BaseModel):
    """Feedback response from the feedback agent"""
    feedback: str = Field(
        ...,
        description="Personalized feedback based on the user's performance, highlighting strengths and areas for improvement."
    )
