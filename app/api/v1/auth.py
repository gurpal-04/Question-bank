from fastapi import APIRouter, Depends, status
from google.cloud import firestore

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserCreate, UserLogin, Token
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: firestore.Client = Depends(get_db)):
    """
    Create a new user account
    """
    service = AuthService(db)
    return await service.signup(user_data)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: firestore.Client = Depends(get_db)):
    """
    Authenticate a user and return JWT token
    """
    service = AuthService(db)
    return await service.login(credentials)


@router.post("/migrate-guest")
async def migrate_guest_data(
    guest_id: str,
    current_user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    """
    Migrate all guest assessments and results to the authenticated user
    """
    service = AuthService(db)
    return await service.migrate_guest_data(guest_id, current_user)
