from google.cloud import firestore
from fastapi import HTTPException, status
from datetime import datetime
from typing import Dict, Any

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from app.models.user import User, UserCreate, UserLogin, Token, UserResponse


class AuthService:
    def __init__(self, db: firestore.Client):
        self.db = db

    async def signup(self, user_data: UserCreate) -> Token:
        """
        Create a new user account
        """
        # Check if email already exists
        users_ref = self.db.collection("users")
        existing_users = (
            users_ref.where("email", "==", user_data.email).limit(1).stream()
        )

        if any(existing_users):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash the password
        hashed_password = get_password_hash(user_data.password)

        # Create user document
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            created_at=datetime.utcnow(),
        )

        # Save to Firestore
        user_dict = user.dict(exclude={"id"})
        user_ref = users_ref.add(user_dict)
        user_id = user_ref[1].id

        # Create access token
        access_token = create_access_token(data={"sub": user_id, "email": user.email})

        # Return token and user info
        user_response = UserResponse(
            id=user_id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
        )

        return Token(access_token=access_token, user=user_response)

    async def login(self, credentials: UserLogin) -> Token:
        """
        Authenticate a user and return JWT token
        """
        # Find user by email
        users_ref = self.db.collection("users")
        users = users_ref.where("email", "==", credentials.email).limit(1).stream()

        user_doc = None
        for doc in users:
            user_doc = doc
            break

        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user data
        user_data = user_doc.to_dict()
        user_id = user_doc.id

        # Verify password
        if not verify_password(credentials.password, user_data["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": user_id, "email": user_data["email"]}
        )

        # Return token and user info
        user_response = UserResponse(
            id=user_id,
            email=user_data["email"],
            full_name=user_data["full_name"],
            created_at=user_data["created_at"],
        )

        return Token(access_token=access_token, user=user_response)

    async def migrate_guest_data(
        self, guest_id: str, current_user: User
    ) -> Dict[str, Any]:
        """
        Migrate all guest data (assessments, results, and interview sessions) to the authenticated user.
        
        Note: This is typically used when an anonymous user signs up and wants to keep their data.
        However, with Firebase Anonymous Auth, the UID stays the same after linking, so migration
        may not be necessary. This method is kept for backward compatibility.
        """
        migrated_assessments = 0
        migrated_results = 0
        migrated_interviews = 0

        # Migrate assessments
        assessments_ref = self.db.collection("assessments")
        guest_assessments = assessments_ref.where("user_id", "==", guest_id).stream()

        for assessment_doc in guest_assessments:
            assessment_doc.reference.update({"user_id": current_user.id})
            migrated_assessments += 1

        # Migrate results
        results_ref = self.db.collection("results")
        guest_results = results_ref.where("user_id", "==", guest_id).stream()

        for result_doc in guest_results:
            result_doc.reference.update({"user_id": current_user.id})
            migrated_results += 1

        # Migrate interview sessions
        interviews_ref = self.db.collection("interview_sessions")
        guest_interviews = interviews_ref.where("user_id", "==", guest_id).stream()

        for interview_doc in guest_interviews:
            interview_doc.reference.update({"user_id": current_user.id})
            migrated_interviews += 1

        return {
            "success": True,
            "migrated_assessments": migrated_assessments,
            "migrated_results": migrated_results,
            "migrated_interviews": migrated_interviews,
            "message": f"Successfully migrated {migrated_assessments} assessments, {migrated_results} results, and {migrated_interviews} interview sessions",
        }
