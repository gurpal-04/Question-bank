import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.cloud import firestore

from app.core.database import get_db
from app.models.user import User, TokenData

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, stored_password: str) -> bool:
    """
    Verify a plain password against stored password.
    
    WARNING: Currently using plain text comparison (hashing disabled).
    This is NOT secure for production use.
    """
    return plain_password == stored_password


def get_password_hash(password: str) -> str:
    """
    Get password for storing.
    
    WARNING: Currently returning plain text (hashing disabled).
    This is NOT secure for production use.
    """
    return password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Dictionary containing user data to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        TokenData object with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(user_id=user_id, email=email)
        return token_data
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: firestore.Client = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user

    Args:
        credentials: HTTP Bearer token credentials
        db: Firestore database client

    Returns:
        User object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = verify_token(token)

    # Get user from database
    user_ref = db.collection("users").document(token_data.user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = user_doc.to_dict()
    user_data["id"] = user_doc.id

    return User(**user_data)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: firestore.Client = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency to get the current user if authenticated, None otherwise
    Allows endpoints to work for both authenticated and guest users

    Args:
        credentials: Optional HTTP Bearer token credentials
        db: Firestore database client

    Returns:
        User object if authenticated, None if guest
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
