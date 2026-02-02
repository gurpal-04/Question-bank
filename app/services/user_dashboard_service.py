"""
User Dashboard Service

Computes user dashboard by aggregating data across all interview sessions.
Implements on-demand computation (Option A).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import asyncio
from concurrent.futures import ThreadPoolExecutor
from google.cloud import firestore

from app.models.user import User
from app.models.interview import InterviewSession
from app.models.analytics import InterviewAnalytics
from app.models.user_dashboard import (
    UserDashboard,
    UserOverview,
    InterviewHistory,
    InterviewHistoryItem,
    SkillsMastery,
    SkillMasteryItem,
    DimensionTrends,
    DimensionTrend,
    DimensionTrendPoint,
    ConceptMasteryTracker,
    ConceptFrequency,
    ReadinessProgress,
    ReadinessProgressPoint,
    RecommendedActions,
    ActionItem,
    Achievements,
    Milestone,
    UserStatistics,
    AssessmentsOverview,
    AssessmentSummaryItem,
    AssessmentsByTopic,
)
from app.models.assessment import Assessment, AssessmentResult
from app.core.config.evaluation_bars import get_benchmark
from app.core.config.skillMaps.frontend import FRONTEND_SKILL_MAP

logger = logging.getLogger(__name__)


class UserDashboardService:
    """Service for computing user dashboard data."""

    def __init__(self, db: firestore.Client):
        self.db = db

    async def compute_dashboard(
        self, 
        user_id: str, 
        limit: Optional[int] = 20,  # Default limit for performance
        user: Optional[User] = None  # Optional User object (for guest users)
    ) -> UserDashboard:
        """
        Compute complete dashboard for a user.

        Args:
            user_id: User ID to compute dashboard for
            limit: Optional limit on number of interviews to analyze (for performance)
            user: Optional User object (if already available, skips Firestore lookup)

        Returns:
            Complete UserDashboard object
        """
        try:
            logger.info(f"Computing dashboard for user {user_id}")

            # If user object not provided, fetch from Firestore
            if user is None:
                user_task = self._get_user(user_id)
                sessions_task = self._get_user_sessions(user_id, limit)
                assessments_task = self._get_user_assessments(user_id, limit)

                user, sessions, assessments = await asyncio.gather(
                    user_task, sessions_task, assessments_task
                )

                if not user:
                    raise ValueError(f"User {user_id} not found")
            else:
                # User object provided, just fetch sessions and assessments
                sessions_task = self._get_user_sessions(user_id, limit)
                assessments_task = self._get_user_assessments(user_id, limit)

                sessions, assessments = await asyncio.gather(
                    sessions_task, assessments_task
                )

            # Batch fetch analytics and assessment results
            # Note: These could also be gathered in parallel
            analytics_task = self._get_analytics_for_sessions(
                [s.id for s in sessions if s.id]
            )
            results_task = self._get_assessment_results(assessments)

            analytics_list, assessment_results = await asyncio.gather(
                analytics_task, results_task
            )

            # Compute each dashboard section
            overview = self._compute_overview(user, sessions, analytics_list, assessment_results)
            history = self._compute_history(sessions, analytics_list)
            skills = self._compute_skills_mastery(analytics_list, sessions)
            dimensions = self._compute_dimension_trends(analytics_list)
            concepts = self._compute_concept_mastery(analytics_list)
            readiness = self._compute_readiness_progress(analytics_list, sessions)
            actions = self._compute_recommended_actions(
                analytics_list, skills, concepts, readiness
            )
            assessments_overview = self._compute_assessments_overview(
                assessments, assessment_results
            )

            dashboard = UserDashboard(
                overview=overview,
                interview_history=history,
                skills_mastery=skills,
                dimension_trends=dimensions,
                concept_mastery=concepts,
                readiness_progress=readiness,
                recommended_actions=actions,
                assessments=assessments_overview,
            )

            logger.info(f"Dashboard computed successfully for user {user_id}")
            return dashboard

        except Exception as e:
            logger.error(f"Error computing dashboard for user {user_id}: {e}")
            raise

    async def update_dashboard(self, user_id: str) -> None:
        """
        Compute and persist dashboard for a user.
        This is called as a fire-and-forget or background update
        to keep the user_dashboards collection fresh.
        """
        try:
            logger.info(f"Triggering dashboard update for user {user_id}")
            dashboard = await self.compute_dashboard(user_id)

            # Persist to user_dashboards collection
            doc_ref = self.db.collection("user_dashboards").document(user_id)
            doc_ref.set(dashboard.model_dump())

            logger.info(f"Dashboard persisted successfully for user {user_id}")
        except Exception as e:
            # We don't want dashboard failures to block main business logic
            logger.error(
                f"Failed to update dashboard for user {user_id}: {e}", exc_info=True
            )

    # ========================================================================
    # DATA FETCHING
    # ========================================================================

    async def _get_user(self, user_id: str) -> Optional[User]:
        """Fetch user from Firestore."""

        def fetch():
            try:
                doc = self.db.collection("users").document(user_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    return User(**data)
                return None
            except Exception as e:
                logger.error(f"Error fetching user {user_id}: {e}")
                return None

        return await asyncio.to_thread(fetch)

    async def _get_user_sessions(
        self, user_id: str, limit: Optional[int] = None
    ) -> List[InterviewSession]:
        """Fetch all interview sessions for a user."""

        def fetch():
            try:
                query = (
                    self.db.collection("interview_sessions")
                    .where(filter=firestore.FieldFilter("user_id", "==", user_id))
                    .order_by("created_at", direction=firestore.Query.DESCENDING)
                )
                if limit:
                    query = query.limit(limit)
                docs = query.stream()
                sessions = []
                for doc in docs:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    sessions.append(InterviewSession(**data))
                return sessions
            except Exception as e:
                logger.error(f"Error fetching sessions for user {user_id}: {e}")
                return []

        return await asyncio.to_thread(fetch)

    async def _get_analytics_for_sessions(
        self, session_ids: List[str]
    ) -> List[InterviewAnalytics]:
        """Fetch analytics for multiple sessions using batch read."""
        if not session_ids:
            return []

        def fetch():
            analytics_list = []
            try:
                # Create document references for batch fetch
                refs = [
                    self.db.collection("interview_analytics").document(sid)
                    for sid in session_ids
                ]
                # db.get_all() is 10x faster than sequential .get()
                docs = self.db.get_all(refs)
                for doc in docs:
                    if doc.exists:
                        data = doc.to_dict()
                        analytics_list.append(InterviewAnalytics(**data))
            except Exception as e:
                logger.warning(f"Error batch fetching analytics: {e}")
            return analytics_list

        return await asyncio.to_thread(fetch)

    async def _get_user_assessments(
        self, user_id: str, limit: Optional[int] = None
    ) -> List[Assessment]:
        """Fetch all assessments for a user."""

        def fetch():
            try:
                # Try with order_by first
                try:
                    query = (
                        self.db.collection("assessments")
                        .where(filter=firestore.FieldFilter("user_id", "==", user_id))
                        .order_by("created_at", direction=firestore.Query.DESCENDING)
                    )
                    if limit:
                        query = query.limit(limit)
                    docs = query.stream()
                    return [Assessment(id=doc.id, **doc.to_dict()) for doc in docs]
                except Exception as order_error:
                    logger.warning(f"Order by failed, trying without: {order_error}")
                    query = self.db.collection("assessments").where(
                        filter=firestore.FieldFilter("user_id", "==", user_id)
                    )
                    if limit:
                        query = query.limit(limit)
                    docs = query.stream()
                    assessments = [
                        Assessment(id=doc.id, **doc.to_dict()) for doc in docs
                    ]
                    assessments.sort(key=lambda a: a.created_at, reverse=True)
                    return assessments
            except Exception as e:
                logger.error(f"Error fetching assessments: {e}", exc_info=True)
                return []

        return await asyncio.to_thread(fetch)

    async def _get_assessment_results(
        self, assessments: List[Assessment]
    ) -> Dict[str, AssessmentResult]:
        """Fetch results for multiple assessments using batch read."""
        if not assessments:
            return {}

        def fetch():
            results_map = {}
            # Map result_id -> assessment_id
            result_to_assessment = {}
            refs = []

            for assessment in assessments:
                if assessment.id and assessment.result_id:
                    ref = self.db.collection("assessment_results").document(
                        assessment.result_id
                    )
                    refs.append(ref)
                    result_to_assessment[assessment.result_id] = assessment.id

            if not refs:
                return {}

            try:
                # db.get_all() is 10x faster than sequential .get()
                docs = self.db.get_all(refs)
                for doc in docs:
                    if doc.exists:
                        data = doc.to_dict()
                        data["id"] = doc.id
                        assessment_id = result_to_assessment.get(doc.id)
                        if assessment_id:
                            results_map[assessment_id] = AssessmentResult(**data)
            except Exception as e:
                logger.warning(f"Error batch fetching assessment results: {e}")
            return results_map

        return await asyncio.to_thread(fetch)

    # ========================================================================
    # SECTION 1: USER OVERVIEW
    # ========================================================================

    def _compute_overview(
        self,
        user: User,
        sessions: List[InterviewSession],
        analytics_list: List[InterviewAnalytics],
        assessment_results: Dict[str, AssessmentResult],
    ) -> UserOverview:
        """Compute hero section overview."""

        completed_sessions = [s for s in sessions if s.status == "completed"]

        # Average score - include both interview scores and assessment scores
        scores = [
            a.overall_score for a in analytics_list if a.overall_score is not None
        ]
        
        # Add assessment scores (convert to percentage: score/max_score * 100)
        for result in assessment_results.values():
            if result.score is not None and result.max_score and result.max_score > 0:
                assessment_percentage = (result.score / result.max_score) * 100
                scores.append(assessment_percentage)
        
        avg_score = sum(scores) / len(scores) if scores else None

        # Improvement trend (last 30 days vs before)
        improvement = self._calculate_improvement_trend(analytics_list, sessions)

        # Total practice time
        total_time = self._calculate_total_time(analytics_list)

        # Current readiness level (from most recent)
        current_readiness = None
        if analytics_list:
            current_readiness = analytics_list[0].readiness_level

        return UserOverview(
            user_id=user.id,
            full_name=user.full_name,
            email=str(user.email) if user.email else None,
            member_since=user.created_at,
            total_interviews_completed=len(completed_sessions),
            average_readiness_score=round(avg_score, 1) if avg_score else None,
            improvement_trend=improvement,
            total_practice_time=total_time,
            current_readiness_level=current_readiness,
        )

    def _calculate_improvement_trend(
        self, analytics_list: List[InterviewAnalytics], sessions: List[InterviewSession]
    ) -> Optional[float]:
        """Calculate score improvement in last 30 days."""
        if len(analytics_list) < 2:
            return None

        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Create session_id to date mapping
        session_dates = {s.id: s.created_at for s in sessions if s.id}

        recent_scores = []
        older_scores = []

        for analytics in analytics_list:
            session_date = session_dates.get(analytics.session_id)
            if not session_date or analytics.overall_score is None:
                continue

            # Make session_date timezone-aware if it's naive
            if session_date.tzinfo is None:
                session_date = session_date.replace(tzinfo=timezone.utc)

            if session_date >= thirty_days_ago:
                recent_scores.append(analytics.overall_score)
            else:
                older_scores.append(analytics.overall_score)

        if not recent_scores or not older_scores:
            return None

        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)

        return round(recent_avg - older_avg, 1)

    def _calculate_total_time(
        self, analytics_list: List[InterviewAnalytics]
    ) -> Optional[str]:
        """Calculate total practice time across all interviews."""
        total_seconds = 0

        for analytics in analytics_list:
            if analytics.average_response_time:
                # Parse time string like "3m 42s"
                time_str = analytics.average_response_time
                minutes = 0
                seconds = 0

                if "m" in time_str:
                    parts = time_str.split("m")
                    minutes = int(parts[0].strip())
                    if len(parts) > 1 and "s" in parts[1]:
                        seconds = int(parts[1].replace("s", "").strip())
                elif "s" in time_str:
                    seconds = int(time_str.replace("s", "").strip())

                # Multiply by number of questions
                time_per_question = minutes * 60 + seconds
                total_seconds += time_per_question * analytics.total_questions_answered

        if total_seconds == 0:
            return None

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    # ========================================================================
    # SECTION 2: INTERVIEW HISTORY
    # ========================================================================

    def _compute_history(
        self, sessions: List[InterviewSession], analytics_list: List[InterviewAnalytics]
    ) -> InterviewHistory:
        """Compute interview history."""

        # Create analytics lookup
        analytics_map = {a.session_id: a for a in analytics_list}

        history_items = []
        for session in sessions[:10]:  # Show last 10
            if not session.id:
                continue

            analytics = analytics_map.get(session.id)

            item = InterviewHistoryItem(
                session_id=session.id,
                role=session.role,
                experience_range=session.experience_range,
                difficulty=session.difficulty,
                overall_score=analytics.overall_score if analytics else None,
                readiness_level=analytics.readiness_level if analytics else None,
                total_questions=len(session.questions),
                total_time=analytics.average_response_time if analytics else None,
                created_at=session.created_at,
                status=session.status,
            )
            history_items.append(item)

        return InterviewHistory(interviews=history_items, total_count=len(sessions))

    # ========================================================================
    # SECTION 3: SKILLS MASTERY
    # ========================================================================

    def _compute_skills_mastery(
        self, analytics_list: List[InterviewAnalytics], sessions: List[InterviewSession]
    ) -> SkillsMastery:
        """Compute skills mastery overview."""

        # Aggregate skill scores across all interviews
        skill_data: Dict[str, List[float]] = defaultdict(list)

        for analytics in analytics_list:
            for skill_perf in analytics.skill_performance:
                skill_data[skill_perf.skill_id].append(skill_perf.avg_score)

        # Compute averages and categorize
        skill_items = []
        for skill_id, scores in skill_data.items():
            avg_score = sum(scores) / len(scores)

            # Get skill label from skill map
            skill_label = self._get_skill_label(skill_id)

            # Determine category
            if avg_score >= 3.8:
                category = "strong"
            elif avg_score >= 3.0:
                category = "developing"
            else:
                category = "needs_work"

            # Calculate trend (if enough data)
            trend = self._calculate_skill_trend(scores) if len(scores) >= 3 else None

            skill_items.append(
                SkillMasteryItem(
                    skill_id=skill_id,
                    skill_label=skill_label,
                    average_score=round(avg_score, 1),
                    times_practiced=len(scores),
                    category=category,
                    trend=trend,
                )
            )

        # Sort by average score
        skill_items.sort(key=lambda x: x.average_score, reverse=True)

        # Group by category
        strong = [s for s in skill_items if s.category == "strong"]
        developing = [s for s in skill_items if s.category == "developing"]
        needs_work = [s for s in skill_items if s.category == "needs_work"]

        return SkillsMastery(
            strong_skills=strong,
            developing_skills=developing,
            needs_work_skills=needs_work,
        )

    def _get_skill_label(self, skill_id: str) -> str:
        """Get skill label from skill map."""
        for skill in FRONTEND_SKILL_MAP:
            if skill.id == skill_id:
                return skill.label
        return skill_id

    def _calculate_skill_trend(self, scores: List[float]) -> str:
        """Calculate if skill is improving, stable, or declining."""
        if len(scores) < 3:
            return "stable"

        # Compare first half vs second half
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / mid
        second_half_avg = sum(scores[mid:]) / (len(scores) - mid)

        diff = second_half_avg - first_half_avg

        if diff > 0.3:
            return "improving"
        elif diff < -0.3:
            return "declining"
        else:
            return "stable"

    # ========================================================================
    # SECTION 4: DIMENSION TRENDS
    # ========================================================================

    def _compute_dimension_trends(
        self, analytics_list: List[InterviewAnalytics]
    ) -> DimensionTrends:
        """Compute dimension trends over time."""

        structure_points = []
        depth_points = []
        tradeoffs_points = []
        clarity_points = []

        for analytics in reversed(analytics_list):  # Oldest to newest
            structure_points.append(
                DimensionTrendPoint(
                    date=analytics.computed_at,
                    score=analytics.dimension_scores.structure.score,
                    session_id=analytics.session_id,
                )
            )
            depth_points.append(
                DimensionTrendPoint(
                    date=analytics.computed_at,
                    score=analytics.dimension_scores.depth.score,
                    session_id=analytics.session_id,
                )
            )
            tradeoffs_points.append(
                DimensionTrendPoint(
                    date=analytics.computed_at,
                    score=analytics.dimension_scores.tradeoffs.score,
                    session_id=analytics.session_id,
                )
            )
            clarity_points.append(
                DimensionTrendPoint(
                    date=analytics.computed_at,
                    score=analytics.dimension_scores.clarity.score,
                    session_id=analytics.session_id,
                )
            )

        # Get current and target scores (from most recent)
        latest = analytics_list[0] if analytics_list else None

        return DimensionTrends(
            structure=DimensionTrend(
                dimension_name="structure",
                data_points=structure_points,
                current_score=(
                    latest.dimension_scores.structure.score if latest else None
                ),
                target_score=(
                    latest.dimension_scores.structure.target if latest else None
                ),
                trend=self._calculate_dimension_trend(structure_points),
            ),
            depth=DimensionTrend(
                dimension_name="depth",
                data_points=depth_points,
                current_score=latest.dimension_scores.depth.score if latest else None,
                target_score=latest.dimension_scores.depth.target if latest else None,
                trend=self._calculate_dimension_trend(depth_points),
            ),
            tradeoffs=DimensionTrend(
                dimension_name="tradeoffs",
                data_points=tradeoffs_points,
                current_score=(
                    latest.dimension_scores.tradeoffs.score if latest else None
                ),
                target_score=(
                    latest.dimension_scores.tradeoffs.target if latest else None
                ),
                trend=self._calculate_dimension_trend(tradeoffs_points),
            ),
            clarity=DimensionTrend(
                dimension_name="clarity",
                data_points=clarity_points,
                current_score=latest.dimension_scores.clarity.score if latest else None,
                target_score=latest.dimension_scores.clarity.target if latest else None,
                trend=self._calculate_dimension_trend(clarity_points),
            ),
        )

    def _calculate_dimension_trend(
        self, points: List[DimensionTrendPoint]
    ) -> Optional[str]:
        """Calculate if dimension is improving, stable, or declining."""
        if len(points) < 3:
            return None

        scores = [p.score for p in points]
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / mid
        second_half_avg = sum(scores[mid:]) / (len(scores) - mid)

        diff = second_half_avg - first_half_avg

        if diff > 0.3:
            return "improving"
        elif diff < -0.3:
            return "declining"
        else:
            return "stable"

    # ========================================================================
    # SECTION 5: CONCEPT MASTERY
    # ========================================================================

    def _compute_concept_mastery(
        self, analytics_list: List[InterviewAnalytics]
    ) -> ConceptMasteryTracker:
        """Compute concept mastery tracker."""

        # Track concept appearances
        concept_covered: Dict[str, int] = defaultdict(int)
        concept_missing: Dict[str, int] = defaultdict(int)
        concept_incorrect: Dict[str, int] = defaultdict(int)

        for analytics in analytics_list:
            # covered_well is List[str]
            for concept in analytics.concept_mastery.covered_well:
                concept_covered[concept] += 1

            # partially_covered is List[ConceptDetail]
            for concept_detail in analytics.concept_mastery.partially_covered:
                concept_covered[concept_detail.concept] += 1

            # missing is List[str]
            for concept in analytics.concept_mastery.missing:
                concept_missing[concept] += 1

            # incorrect is List[ConceptDetail]
            for concept_detail in analytics.concept_mastery.incorrect:
                concept_incorrect[concept_detail.concept] += 1

        # Compute frequencies
        all_concepts = (
            set(concept_covered.keys())
            | set(concept_missing.keys())
            | set(concept_incorrect.keys())
        )

        frequencies = []
        for concept in all_concepts:
            covered = concept_covered.get(concept, 0)
            missing = concept_missing.get(concept, 0)
            incorrect = concept_incorrect.get(concept, 0)
            total = covered + missing + incorrect

            coverage_rate = covered / total if total > 0 else 0.0

            frequencies.append(
                ConceptFrequency(
                    concept=concept,
                    times_covered=covered,
                    times_missed=missing,
                    times_incorrect=incorrect,
                    total_appearances=total,
                    coverage_rate=round(coverage_rate, 2),
                )
            )

        # Categorize
        mastered = [f for f in frequencies if f.coverage_rate >= 0.8]
        partial = [f for f in frequencies if 0.3 <= f.coverage_rate < 0.8]
        missing = [f for f in frequencies if f.coverage_rate < 0.3]

        # Sort by frequency
        mastered.sort(key=lambda x: x.total_appearances, reverse=True)
        partial.sort(key=lambda x: x.coverage_rate)
        missing.sort(key=lambda x: x.times_missed, reverse=True)

        return ConceptMasteryTracker(
            mastered_concepts=mastered[:20],  # Top 20
            partial_concepts=partial[:10],
            missing_concepts=missing[:10],
        )

    # ========================================================================
    # SECTION 6: READINESS PROGRESS
    # ========================================================================

    def _compute_readiness_progress(
        self, analytics_list: List[InterviewAnalytics], sessions: List[InterviewSession]
    ) -> ReadinessProgress:
        """Compute readiness score progress."""

        # Create session_id to date mapping
        session_dates = {s.id: s.created_at for s in sessions if s.id}

        # Build progress points
        progress_points = []
        for analytics in reversed(analytics_list):  # Oldest to newest
            session_date = session_dates.get(analytics.session_id)
            if not session_date or analytics.overall_score is None:
                continue

            progress_points.append(
                ReadinessProgressPoint(
                    date=session_date,
                    score=analytics.overall_score,
                    readiness_level=analytics.readiness_level,
                    session_id=analytics.session_id,
                )
            )

        # Get current and target
        latest = analytics_list[0] if analytics_list else None
        current_score = latest.overall_score if latest else None
        target_score = latest.benchmark_score if latest else None
        gap = (
            (current_score - target_score) if (current_score and target_score) else None
        )

        # Calculate trend
        trend = None
        trend_value = None
        if len(progress_points) >= 3:
            scores = [p.score for p in progress_points]
            mid = len(scores) // 2
            first_half_avg = sum(scores[:mid]) / mid
            second_half_avg = sum(scores[mid:]) / (len(scores) - mid)
            trend_value = round(second_half_avg - first_half_avg, 1)

            if trend_value > 3:
                trend = "improving"
            elif trend_value < -3:
                trend = "declining"
            else:
                trend = "stable"

        return ReadinessProgress(
            current_score=current_score,
            target_score=target_score,
            gap=round(gap, 1) if gap else None,
            progress_points=progress_points,
            trend=trend,
            trend_value=trend_value,
        )

    # ========================================================================
    # SECTION 7: RECOMMENDED ACTIONS
    # ========================================================================

    def _compute_recommended_actions(
        self,
        analytics_list: List[InterviewAnalytics],
        skills: SkillsMastery,
        concepts: ConceptMasteryTracker,
        readiness: ReadinessProgress,
    ) -> RecommendedActions:
        """Generate personalized recommended actions."""

        actions = []

        # 1. Focus on weakest skills
        if skills.needs_work_skills:
            for skill in skills.needs_work_skills[:2]:
                actions.append(
                    ActionItem(
                        priority="high",
                        category="practice",
                        title=f"Practice {skill.skill_label}",
                        description=f"Take a {skill.skill_label}-focused interview",
                        reason=f"Low average score: {skill.average_score}/5.0",
                    )
                )

        # 2. Address frequently missing concepts
        if concepts.missing_concepts:
            top_missing = concepts.missing_concepts[0]
            actions.append(
                ActionItem(
                    priority="high",
                    category="study",
                    title=f"Study {top_missing.concept}",
                    description=f"Review and practice {top_missing.concept}",
                    reason=f"Missed in {top_missing.times_missed}/{top_missing.total_appearances} interviews",
                )
            )

        # 3. Improve weakest dimension
        if analytics_list:
            latest = analytics_list[0]
            dims = latest.dimension_scores

            weakest_dim = min(
                [
                    ("Structure & Organization", dims.structure.score),
                    ("Technical Depth", dims.depth.score),
                    ("Trade-offs & Nuance", dims.tradeoffs.score),
                    ("Clarity & Communication", dims.clarity.score),
                ],
                key=lambda x: x[1],
            )

            if weakest_dim[1] < 3.5:
                actions.append(
                    ActionItem(
                        priority="medium",
                        category="improve",
                        title=f"Improve {weakest_dim[0]}",
                        description=self._get_dimension_tip(weakest_dim[0]),
                        reason=f"Current score: {weakest_dim[1]}/5.0",
                    )
                )

        # Study recommendations
        study_recs = []
        for concept in concepts.missing_concepts[:5]:
            study_recs.append(concept.concept)

        # Next interview suggestion
        next_suggestion = None
        if skills.needs_work_skills:
            weakest = skills.needs_work_skills[0]
            next_suggestion = {
                "role": "Frontend Engineer",
                "difficulty": "Medium",
                "focus": weakest.skill_label,
            }

        return RecommendedActions(
            top_priorities=actions[:3],
            study_recommendations=study_recs,
            next_interview_suggestion=next_suggestion,
        )

    def _get_dimension_tip(self, dimension: str) -> str:
        """Get improvement tip for dimension."""
        tips = {
            "Structure & Organization": "Use intro-body-conclusion format in answers",
            "Technical Depth": "Provide more technical details and examples",
            "Trade-offs & Nuance": "Discuss pros/cons and when to use different approaches",
            "Clarity & Communication": "Avoid rambling, be concise and clear",
        }
        return tips.get(dimension, "Focus on improving this dimension")

    # ========================================================================
    # SECTION 8: ACHIEVEMENTS
    # ========================================================================

    def _compute_achievements(
        self,
        user: User,
        sessions: List[InterviewSession],
        analytics_list: List[InterviewAnalytics],
        readiness: ReadinessProgress,
    ) -> Achievements:
        """Compute achievements and statistics."""

        completed = [s for s in sessions if s.status == "completed"]

        # Milestones
        milestones = [
            Milestone(
                id="first_interview",
                title="First Interview Completed",
                description="Complete your first interview",
                achieved=len(completed) >= 1,
                achieved_at=completed[0].created_at if completed else None,
            ),
            Milestone(
                id="ten_interviews",
                title="10 Interviews Completed",
                description="Complete 10 interviews",
                achieved=len(completed) >= 10,
                achieved_at=completed[9].created_at if len(completed) >= 10 else None,
                progress=len(completed),
                target=10,
            ),
            Milestone(
                id="interview_ready",
                title="Reached Interview Ready Status",
                description="Achieve 'Interview Ready' or higher",
                achieved=any(
                    a.readiness_level in ["Interview Ready", "Exceeds Expectations"]
                    for a in analytics_list
                ),
            ),
            Milestone(
                id="twenty_interviews",
                title="20 Interviews Completed",
                description="Complete 20 interviews",
                achieved=len(completed) >= 20,
                progress=len(completed),
                target=20,
            ),
        ]

        # Statistics
        total_questions = sum(len(s.questions) for s in completed)
        avg_questions = total_questions / len(completed) if completed else None

        # Most practiced role
        role_counts = Counter(s.role for s in completed)
        most_role = role_counts.most_common(1)[0] if role_counts else (None, None)

        # Favorite difficulty
        diff_counts = Counter(s.difficulty for s in completed)
        fav_diff = diff_counts.most_common(1)[0] if diff_counts else (None, None)

        # Best score
        best_score = max(
            (a.overall_score for a in analytics_list if a.overall_score), default=None
        )
        best_date = None
        if best_score:
            for a in analytics_list:
                if a.overall_score == best_score:
                    best_date = a.computed_at
                    break

        # Streaks
        longest_streak = self._calculate_longest_streak(sessions)
        current_streak = self._calculate_current_streak(sessions)

        statistics = UserStatistics(
            total_questions_answered=total_questions,
            average_questions_per_interview=(
                round(avg_questions, 1) if avg_questions else None
            ),
            most_practiced_role=most_role[0],
            most_practiced_role_count=most_role[1],
            favorite_difficulty=fav_diff[0],
            favorite_difficulty_count=fav_diff[1],
            best_score=best_score,
            best_score_date=best_date,
            longest_streak=longest_streak,
            current_streak=current_streak,
        )

        # Badges (simple rule-based)
        badges = []
        if len(completed) >= 5:
            badges.append("consistent_learner")
        if longest_streak and longest_streak >= 5:
            badges.append("week_warrior")
        if readiness.trend == "improving":
            badges.append("quick_learner")

        return Achievements(
            milestones=milestones,
            statistics=statistics,
            badges=badges,
        )

    def _calculate_longest_streak(
        self, sessions: List[InterviewSession]
    ) -> Optional[int]:
        """Calculate longest streak of interviews in 7-day windows."""
        if not sessions:
            return None

        completed = [s for s in sessions if s.status == "completed"]
        if not completed:
            return None

        # Sort by date
        completed.sort(key=lambda s: s.created_at)

        max_streak = 1
        current_streak = 1

        for i in range(1, len(completed)):
            days_diff = (completed[i].created_at - completed[i - 1].created_at).days
            if days_diff <= 7:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        return max_streak

    def _calculate_current_streak(
        self, sessions: List[InterviewSession]
    ) -> Optional[int]:
        """Calculate current streak (interviews in last 7 days)."""
        if not sessions:
            return None

        completed = [s for s in sessions if s.status == "completed"]
        if not completed:
            return None

        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        # Make created_at timezone-aware if needed and compare
        recent = []
        for s in completed:
            created_at = s.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at >= seven_days_ago:
                recent.append(s)

        return len(recent) if recent else None

    # ========================================================================
    # SECTION 9: ASSESSMENTS OVERVIEW
    # ========================================================================

    def _compute_assessments_overview(
        self, assessments: List[Assessment], results_map: Dict[str, AssessmentResult]
    ) -> AssessmentsOverview:
        """Compute assessments overview."""

        if not assessments:
            return AssessmentsOverview(
                total_assessments=0,
                completed_assessments=0,
                pending_assessments=0,
                overall_average_score=None,
                recent_assessments=[],
                by_topic=[],
                common_weak_topics=[],
            )

        # Build assessment summary items
        assessment_items = []
        completed_count = 0
        total_scores = []
        all_weak_topics = []

        for assessment in assessments:
            result = results_map.get(assessment.id) if assessment.id else None
            has_result = result is not None

            if has_result:
                completed_count += 1
                percentage = (
                    (result.score / result.max_score * 100)
                    if result.max_score > 0
                    else 0
                )
                total_scores.append(percentage)
                all_weak_topics.extend(result.weak_topics)
            else:
                percentage = None

            item = AssessmentSummaryItem(
                assessment_id=assessment.id or "",
                topic=assessment.topic,
                level=assessment.level,
                score=result.score if has_result else None,
                max_score=result.max_score if has_result else None,
                percentage=round(percentage, 1) if percentage is not None else None,
                questions_count=len(assessment.questions),
                correct_count=len(result.correct_questions) if has_result else None,
                incorrect_count=len(result.incorrect_questions) if has_result else None,
                weak_topics=result.weak_topics if has_result else [],
                created_at=assessment.created_at,
                has_result=has_result,
            )
            assessment_items.append(item)

        # Calculate overall average
        overall_avg = sum(total_scores) / len(total_scores) if total_scores else None

        # Group by topic
        by_topic_map: Dict[str, List[AssessmentSummaryItem]] = defaultdict(list)
        for item in assessment_items:
            by_topic_map[item.topic].append(item)

        by_topic_list = []
        for topic, items in by_topic_map.items():
            completed_items = [i for i in items if i.has_result]
            scores = [i.percentage for i in completed_items if i.percentage is not None]

            by_topic_list.append(
                AssessmentsByTopic(
                    topic=topic,
                    total_assessments=len(items),
                    completed_assessments=len(completed_items),
                    average_score=(
                        round(sum(scores) / len(scores), 1) if scores else None
                    ),
                    best_score=round(max(scores), 1) if scores else None,
                    assessments=items,
                )
            )

        # Sort by total assessments
        by_topic_list.sort(key=lambda x: x.total_assessments, reverse=True)

        # Find common weak topics
        weak_topic_counts = Counter(all_weak_topics)
        common_weak = [topic for topic, _ in weak_topic_counts.most_common(5)]

        return AssessmentsOverview(
            total_assessments=len(assessments),
            completed_assessments=completed_count,
            pending_assessments=len(assessments) - completed_count,
            overall_average_score=round(overall_avg, 1) if overall_avg else None,
            recent_assessments=assessment_items[:10],
            by_topic=by_topic_list,
            common_weak_topics=common_weak,
        )
