"""
User Dashboard API Endpoints

Provides endpoints for user profile and dashboard data.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from google.cloud import firestore
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, User
from app.models.user_dashboard import UserDashboard
from app.services.user_dashboard_service import UserDashboardService
from app.services.stored_dashboard_service import StoredDashboardService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=UserDashboard,
    summary="Get User Dashboard",
    description="Get comprehensive dashboard data for the authenticated user. "
                "Returns cached data for fast response, updates in background.",
)
async def get_user_dashboard(
    force_refresh: bool = Query(
        False,
        description="Force refresh dashboard (slower, computes fresh data)"
    ),
    current_user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    """
    Get complete dashboard for authenticated user.
    
    Returns pre-computed dashboard for fast response (~500ms).
    Use force_refresh=true to compute fresh data (slower, ~10-15s).
    
    Includes:
    - User overview (stats, readiness score, improvement trend)
    - Interview history
    - Skills mastery breakdown
    - Dimension trends over time
    - Concept mastery tracker
    - Readiness score progress
    - Recommended actions
    - Assessments overview
    """
    try:
        logger.info(f"Fetching dashboard for user {current_user.id} (force_refresh={force_refresh})")
        
        service = StoredDashboardService(db)
        dashboard = await service.get_dashboard(
            user_id=current_user.id,
            force_refresh=force_refresh,
            user=current_user  # Pass user object to avoid re-fetching
        )
        
        logger.info(f"Dashboard fetched successfully for user {current_user.id}")
        return dashboard
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard: {str(e)}"
        )


@router.get(
    "/profile",
    response_model=User,
    summary="Get User Profile",
    description="Get profile information for the authenticated user.",
)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get user profile information."""
    return current_user


@router.post(
    "/dashboard/refresh",
    response_model=UserDashboard,
    summary="Refresh Dashboard",
    description="Force refresh dashboard data (computes fresh, slower).",
)
async def refresh_dashboard(
    current_user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    """
    Force refresh dashboard for authenticated user.
    Computes fresh data and updates cache.
    """
    try:
        logger.info(f"Force refreshing dashboard for user {current_user.id}")
        
        service = StoredDashboardService(db)
        dashboard = await service.get_dashboard(
            user_id=current_user.id,
            force_refresh=True,
            user=current_user  # Pass user object to avoid re-fetching
        )
        
        logger.info(f"Dashboard refreshed successfully for user {current_user.id}")
        return dashboard
        
    except Exception as e:
        logger.error(f"Error refreshing dashboard for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh dashboard: {str(e)}"
        )


@router.get(
    "/{user_id}/dashboard",
    response_model=UserDashboard,
    summary="Get Dashboard for Specific User",
    description="Get dashboard for a specific user (admin only in production). "
                "Currently accessible by any authenticated user for development.",
)
async def get_specific_user_dashboard(
    user_id: str,
    force_refresh: bool = Query(
        False,
        description="Force refresh dashboard"
    ),
    current_user: User = Depends(get_current_user),
    db: firestore.Client = Depends(get_db),
):
    """
    Get dashboard for a specific user.
    
    Note: In production, this should be restricted to:
    - The user themselves (user_id == current_user.id)
    - Admin users
    
    Currently open for development purposes.
    """
    try:
        # TODO: Add authorization check in production
        # if user_id != current_user.id and not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"Fetching dashboard for user {user_id} (requested by {current_user.id})")
        
        service = StoredDashboardService(db)
        # Pass user object only if requesting own dashboard
        user_obj = current_user if user_id == current_user.id else None
        dashboard = await service.get_dashboard(
            user_id=user_id,
            force_refresh=force_refresh,
            user=user_obj
        )
        
        logger.info(f"Dashboard fetched successfully for user {user_id}")
        return dashboard
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard: {str(e)}"
        )
