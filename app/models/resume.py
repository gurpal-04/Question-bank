from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ProjectHighlight(BaseModel):
    """A short highlight of a project from the resume"""

    name: str = Field(..., description="Name of the project")
    description: str = Field(
        ..., description="Brief description of the project and key contributions"
    )
    technologies: List[str] = Field(
        default_factory=list, description="Technologies used in this project"
    )


class Education(BaseModel):
    """Education history from the resume"""

    degree: str = Field(..., description="Degree obtained")
    institution: str = Field(..., description="Name of the institution")


class ResumeProfile(BaseModel):
    """Structured data extracted from a resume"""

    full_name: Optional[str] = Field(None, description="Full name of the candidate")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Location (city, country)")
    summary: str = Field(
        ...,
        description="A short professional summary extracted or generated from the resume",
    )
    skills: Optional[List[str]] = Field(
        default_factory=list, description="List of technical skills and tools"
    )
    experience_years: Optional[float] = Field(
        ..., description="Total years of professional experience"
    )
    top_projects: Optional[List[ProjectHighlight]] = Field(
        default_factory=list, description="Up to 3-5 key projects highlighting skills"
    )
    education: Optional[List[Education]] = Field(
        default_factory=list, description="Education history (degrees, institutions)"
    )


class Resume(BaseModel):
    """Resume model for Firestore"""

    id: Optional[str] = None
    user_id: str = Field(..., description="ID of the user who owns this resume")
    raw_text: str = Field(..., description="The original raw text of the resume")
    parsed_profile: ResumeProfile = Field(
        ..., description="Extracted structured profile"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ResumeCreate(BaseModel):
    """Request model for uploading/parsing a resume"""

    raw_text: str = Field(..., description="The raw text of the resume to be parsed")


class ResumeResponse(BaseModel):
    """Response model for resume data"""

    id: str
    user_id: str
    parsed_profile: ResumeProfile
    created_at: datetime
