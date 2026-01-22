import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.cloud import firestore
import logging

from app.core.database import get_db
from app.models.user import User, TokenData
from app.core.firebase_admin import get_firebase_auth

logger = logging.getLogger(__name__)

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


def verify_jwt_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token (for regular users).

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

        token_data = TokenData(user_id=user_id, email=email, is_anonymous=False)
        return token_data
    except JWTError:
        raise credentials_exception


def verify_firebase_token(token: str) -> TokenData:
    """
    Verify Firebase ID token (for anonymous and Firebase-authenticated users).

    Args:
        token: Firebase ID token string

    Returns:
        TokenData object with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        firebase_auth = get_firebase_auth()
        decoded_token = firebase_auth.verify_id_token(token)
        
        user_id = decoded_token.get("uid")
        email = decoded_token.get("email")
        
        # Check if this is an anonymous user
        # Firebase anonymous users have sign_in_provider = 'anonymous'
        firebase_info = decoded_token.get("firebase", {})
        is_anonymous = firebase_info.get("sign_in_provider") == "anonymous"
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token: missing UID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            user_id=user_id,
            email=email,
            is_anonymous=is_anonymous
        )
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token(token: str) -> TokenData:
    """
    Verify token - tries JWT first (for regular users), then Firebase (for anonymous users).

    Args:
        token: JWT or Firebase ID token string

    Returns:
        TokenData object with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    # Try JWT first (for existing regular users)
    try:
        return verify_jwt_token(token)
    except HTTPException:
        # If JWT fails, try Firebase token (for anonymous users)
        try:
            return verify_firebase_token(token)
        except HTTPException:
            # Both failed
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials (tried both JWT and Firebase tokens)",
                headers={"WWW-Authenticate": "Bearer"},
            )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: firestore.Client = Depends(get_db),
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    For anonymous users (Firebase anonymous auth), returns a User object
    without requiring a document in the users collection.

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

    # For anonymous users, return User object without Firestore doc
    if token_data.is_anonymous:
        return User(
            id=token_data.user_id,
            email=None,
            hashed_password=None,
            full_name=None,
            is_anonymous=True,
            created_at=datetime.utcnow(),
        )

    # For regular users, get from database
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
    # Ensure is_anonymous is set (default False for existing users)
    if "is_anonymous" not in user_data:
        user_data["is_anonymous"] = False

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
