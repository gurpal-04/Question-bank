from fastapi import APIRouter, HTTPException, status, Depends
from google.cloud import firestore
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, User
from app.models.resume import ResumeCreate, ResumeResponse
from app.services.resume_service import ResumeService

router = APIRouter()


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a resume",
    description="Takes raw resume text, parses it into a structured profile using AI, and saves it for the user.",
)
async def upload_resume(
    request: ResumeCreate,
    db: firestore.Client = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    service = ResumeService(db)
    return await service.parse_and_save_resume(
        user_id=current_user.id, resume_in=request
    )


@router.get(
    "",
    response_model=List[ResumeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all user resumes",
    description="Returns a list of all resumes uploaded by the current authenticated user.",
)
async def get_resumes(
    db: firestore.Client = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    service = ResumeService(db)
    return await service.get_user_resumes(user_id=current_user.id)


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific resume",
    description="Returns the details and parsed profile of a specific resume.",
)
async def get_resume(
    resume_id: str,
    db: firestore.Client = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    service = ResumeService(db)
    # Note: We should ideally check ownership here or in the service
    resume = await service.get_resume(resume_id=resume_id)
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resume",
        )
    return resume


@router.delete(
    "/{resume_id}", status_code=status.HTTP_200_OK, summary="Delete a resume"
)
async def delete_resume(
    resume_id: str,
    db: firestore.Client = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    service = ResumeService(db)
    return await service.delete_resume(resume_id=resume_id, user_id=current_user.id)
