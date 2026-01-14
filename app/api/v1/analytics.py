"""
Analytics API Endpoints

Provides endpoints for computing and retrieving post-interview analytics.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from google.cloud import firestore
from typing import Optional

from app.core.database import get_db
from app.core.security import get_optional_user, User
from app.models.analytics import InterviewAnalytics
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{session_id}/compute",
    response_model=InterviewAnalytics,
    status_code=status.HTTP_201_CREATED,
    summary="Compute Interview Analytics",
    description="Compute comprehensive analytics for a completed interview session. "
                "This should be called after the interview ends.",
)
async def compute_analytics(
    session_id: str,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Compute analytics for a completed interview.
    
    This endpoint:
    1. Loads the interview session
    2. Aggregates dimension scores from all questions
    3. Computes concept mastery
    4. Analyzes skill performance
    5. Detects confidence/clarity patterns
    6. Generates recommendations
    7. Stores analytics in Firestore
    
    Returns the complete analytics object with all 8 views.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    service = AnalyticsService(db)
    
    try:
        analytics = await service.compute_analytics(session_id)
        return analytics
        
    except ValueError as e:
        # Session not found or invalid
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error computing analytics for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing analytics: {str(e)}"
        )


@router.get(
    "/{session_id}",
    response_model=InterviewAnalytics,
    status_code=status.HTTP_200_OK,
    summary="Get Interview Analytics",
    description="Retrieve pre-computed analytics for an interview session.",
)
async def get_analytics(
    session_id: str,
    db: firestore.Client = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve pre-computed analytics for an interview.
    
    Returns 404 if analytics haven't been computed yet.
    Call POST /analytics/{session_id}/compute first to generate analytics.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    service = AnalyticsService(db)
    
    try:
        analytics = service.get_analytics(session_id)
        
        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analytics not found for session {session_id}. "
                       f"Call POST /analytics/{session_id}/compute to generate them."
            )
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analytics for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analytics: {str(e)}"
        )
