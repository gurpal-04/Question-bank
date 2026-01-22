from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class User(BaseModel):
    """User model for Firestore"""

    id: Optional[str] = None  # Firestore document ID or Firebase UID
    email: Optional[EmailStr] = None  # Optional for anonymous users
    hashed_password: Optional[str] = None  # None for anonymous users
    full_name: Optional[str] = None  # Optional for anonymous users
    is_anonymous: bool = False  # True for Firebase anonymous users
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserCreate(BaseModel):
    """Request model for user signup"""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=6, description="User's password (min 6 characters)"
    )
    full_name: str = Field(..., description="User's full name")


class UserLogin(BaseModel):
    """Request model for user login"""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserResponse(BaseModel):
    """Response model for user data (excludes password)"""

    id: str
    email: EmailStr
    full_name: str
    created_at: datetime


class Token(BaseModel):
    """JWT token response model"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """JWT or Firebase token payload data"""

    user_id: Optional[str] = None
    email: Optional[str] = None
    is_anonymous: bool = False  # True for Firebase anonymous users