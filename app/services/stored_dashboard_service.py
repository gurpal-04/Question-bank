"""
Stored Dashboard Service

Manages pre-computed dashboard data in Firestore.
Provides fast reads and background updates.
"""

import logging
from typing import Optional
from datetime import datetime
from google.cloud import firestore

from app.models.user_dashboard import UserDashboard
from app.models.stored_dashboard import StoredDashboard
from app.models.user import User
from app.services.user_dashboard_service import UserDashboardService

logger = logging.getLogger(__name__)


class StoredDashboardService:
    """Service for managing pre-computed dashboards."""
    
    COLLECTION_NAME = "user_dashboards"
    
    def __init__(self, db: firestore.Client):
        self.db = db
        self.compute_service = UserDashboardService(db)
    
    async def get_dashboard(
        self,
        user_id: str,
        force_refresh: bool = False,
        user: Optional[User] = None
    ) -> UserDashboard:
        """
        Get dashboard for user.
        Returns cached version if available and recent, otherwise computes fresh.
        
        Args:
            user_id: User ID
            force_refresh: If True, always compute fresh dashboard
            user: Optional User object (avoids Firestore lookup for guest users)
        
        Returns:
            UserDashboard object
        """
        try:
            # If force refresh, compute fresh
            if force_refresh:
                logger.info(f"Force refresh requested for user {user_id}")
                return await self._compute_and_store(user_id, user=user)
            
            # Try to get cached dashboard
            cached = await self._get_cached_dashboard(user_id)
            
            if cached:
                logger.info(f"Returning cached dashboard for user {user_id}")
                return self._convert_to_user_dashboard(cached)
            
            # No cache, compute fresh
            logger.info(f"No cached dashboard found for user {user_id}, computing fresh")
            return await self._compute_and_store(user_id, user=user)
            
        except Exception as e:
            logger.error(f"Error getting dashboard for user {user_id}: {e}", exc_info=True)
            # Fallback to on-demand computation
            logger.info("Falling back to on-demand computation")
            return await self.compute_service.compute_dashboard(user_id, limit=20, user=user)
    
    async def _get_cached_dashboard(self, user_id: str) -> Optional[StoredDashboard]:
        """Get cached dashboard from Firestore."""
        try:
            doc = self.db.collection(self.COLLECTION_NAME).document(user_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                stored = StoredDashboard(**data)
                logger.info(f"Found cached dashboard for user {user_id}, computed at {stored.computed_at}")
                return stored
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching cached dashboard for user {user_id}: {e}")
            return None
    
    async def _compute_and_store(self, user_id: str, user: Optional[User] = None) -> UserDashboard:
        """Compute fresh dashboard and store it."""
        try:
            logger.info(f"Computing fresh dashboard for user {user_id}")
            
            # Compute dashboard
            dashboard = await self.compute_service.compute_dashboard(user_id, limit=50, user=user)
            
            # Convert to StoredDashboard
            stored = StoredDashboard(
                user_id=user_id,
                overview=dashboard.overview,
                interview_history=dashboard.interview_history,
                skills_mastery=dashboard.skills_mastery,
                dimension_trends=dashboard.dimension_trends,
                concept_mastery=dashboard.concept_mastery,
                readiness_progress=dashboard.readiness_progress,
                recommended_actions=dashboard.recommended_actions,
                assessments=dashboard.assessments,
                computed_at=dashboard.computed_at,
                dashboard_version=dashboard.dashboard_version,
                last_interview_id=dashboard.interview_history.interviews[0].session_id if dashboard.interview_history.interviews else None,
                last_assessment_id=dashboard.assessments.recent_assessments[0].assessment_id if dashboard.assessments.recent_assessments else None,
                interviews_count=dashboard.interview_history.total_count,
                assessments_count=dashboard.assessments.total_assessments,
            )
            
            # Store in Firestore
            await self._store_dashboard(stored)
            
            logger.info(f"Stored fresh dashboard for user {user_id}")
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error computing and storing dashboard for user {user_id}: {e}", exc_info=True)
            raise
    
    async def _store_dashboard(self, stored: StoredDashboard):
        """Store dashboard in Firestore."""
        try:
            # Convert to dict
            data = stored.dict()
            
            # Store with user_id as document ID
            self.db.collection(self.COLLECTION_NAME).document(stored.user_id).set(data)
            
            logger.info(f"Successfully stored dashboard for user {stored.user_id}")
            
        except Exception as e:
            logger.error(f"Error storing dashboard: {e}", exc_info=True)
            raise
    
    def _convert_to_user_dashboard(self, stored: StoredDashboard) -> UserDashboard:
        """Convert StoredDashboard to UserDashboard."""
        return UserDashboard(
            overview=stored.overview,
            interview_history=stored.interview_history,
            skills_mastery=stored.skills_mastery,
            dimension_trends=stored.dimension_trends,
            concept_mastery=stored.concept_mastery,
            readiness_progress=stored.readiness_progress,
            recommended_actions=stored.recommended_actions,
            assessments=stored.assessments,
            computed_at=stored.computed_at,
            dashboard_version=stored.dashboard_version,
        )
    
    async def update_dashboard_after_interview(
        self,
        user_id: str,
        interview_id: str
    ):
        """
        Update dashboard after interview completion.
        Called from interview completion endpoint.
        """
        try:
            logger.info(f"Updating dashboard for user {user_id} after interview {interview_id}")
            await self._compute_and_store(user_id)
            logger.info(f"Dashboard updated successfully for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating dashboard after interview: {e}", exc_info=True)
            # Don't raise - dashboard update failure shouldn't block interview completion
    
    async def update_dashboard_after_assessment(
        self,
        user_id: str,
        assessment_id: str
    ):
        """
        Update dashboard after assessment completion.
        Called from assessment completion endpoint.
        """
        try:
            logger.info(f"Updating dashboard for user {user_id} after assessment {assessment_id}")
            await self._compute_and_store(user_id)
            logger.info(f"Dashboard updated successfully for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating dashboard after assessment: {e}", exc_info=True)
            # Don't raise - dashboard update failure shouldn't block assessment completion
    
    async def invalidate_dashboard(self, user_id: str):
        """
        Invalidate (delete) cached dashboard.
        Forces fresh computation on next request.
        """
        try:
            self.db.collection(self.COLLECTION_NAME).document(user_id).delete()
            logger.info(f"Invalidated dashboard cache for user {user_id}")
        except Exception as e:
            logger.error(f"Error invalidating dashboard: {e}")
