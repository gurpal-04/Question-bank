"""
Analytics Service

Computes post-interview analytics by aggregating data from interview sessions.
Implements all 8 analytics views requested by PM.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from google.cloud import firestore

from app.models.interview import InterviewSession, InterviewQuestion
from app.models.analytics import (
    InterviewAnalytics,
    DimensionScore,
    DimensionScores,
    ConceptMastery,
    ConceptDetail,
    QuestionPerformance,
    SkillPerformance,
    Distribution,
    FollowUpAnalysis,
)
from app.core.config.evaluation_bars import (
    get_benchmark,
    get_dimension_target,
    get_readiness_level,
    get_dimension_status,
    DIMENSION_WEIGHTS,
)
from app.core.config.skillMaps.frontend import FRONTEND_SKILL_MAP

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for computing post-interview analytics."""

    def __init__(self, db: firestore.Client):
        self.db = db

    async def compute_analytics(self, session_id: str) -> InterviewAnalytics:
        """
        Compute comprehensive analytics for a completed interview session.

        Steps:
        1. Load session
        2. Aggregate dimension scores
        3. Compute concept mastery
        4. Compute skill performance
        5. Analyze confidence/clarity patterns
        6. Analyze follow-up patterns
        7. Generate recommendations
        8. Store analytics

        Args:
            session_id: Interview session ID

        Returns:
            Complete analytics object
        """
        try:
            # 1. Load session
            session = self._load_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Validate session has answered questions
            answered_questions = [q for q in session.questions if q.answer]
            if not answered_questions:
                raise ValueError("Session has no answered questions")

            # 2. Aggregate dimension scores
            dimension_scores = self._compute_dimension_scores(
                session.questions, session.experience_range
            )

            # 3. Compute overall score
            overall_score = self._compute_overall_score(dimension_scores)

            # 4. Compute concept mastery
            concept_mastery = self._compute_concept_mastery(session.questions)

            # 5. Compute skill performance
            skill_performance, weakest_skill = self._compute_skill_performance(
                session.questions
            )

            # 6. Analyze confidence/clarity patterns
            confidence_dist = self._compute_confidence_distribution(session.questions)
            clarity_dist = self._compute_clarity_distribution(session.questions)
            confusion_signals = self._aggregate_confusion_signals(session.questions)
            pattern_insight = self._detect_patterns(
                confidence_dist, clarity_dist, session.questions
            )

            # 7. Analyze follow-up patterns
            followup_analysis = self._compute_followup_analysis(
                session.questions, session.experience_range
            )

            # 8. Compute response time
            avg_response_time = self._compute_average_response_time(session.questions)

            # 9. Get skills covered
            skills_covered = self._get_skills_covered(session.questions)

            # 10. Generate recommendations
            recommended_actions = self._generate_recommendations(
                weakest_skill=weakest_skill,
                concept_mastery=concept_mastery,
                dimension_scores=dimension_scores,
                followup_analysis=followup_analysis,
            )

            # 11. Get benchmark
            benchmark = get_benchmark(session.experience_range)

            # 12. Build analytics object
            analytics = InterviewAnalytics(
                session_id=session_id,
                overall_score=overall_score,
                readiness_level=get_readiness_level(
                    overall_score, session.experience_range
                ),
                benchmark_score=benchmark["overall_target"],
                total_questions_answered=len(answered_questions),
                average_response_time=avg_response_time,
                skills_covered=skills_covered,
                dimension_scores=dimension_scores,
                concept_mastery=concept_mastery,
                skill_performance=skill_performance,
                weakest_skill=weakest_skill,
                confidence_distribution=confidence_dist,
                clarity_distribution=clarity_dist,
                confusion_signals=confusion_signals,
                pattern_insight=pattern_insight,
                followup_analysis=followup_analysis,
                recommended_actions=recommended_actions,
            )

            # 13. Store analytics
            self._store_analytics(analytics)

            return analytics

        except Exception as e:
            logger.error(
                f"Error computing analytics for session {session_id}: {e}",
                exc_info=True,
            )
            raise

    def get_analytics(self, session_id: str) -> Optional[InterviewAnalytics]:
        """
        Retrieve pre-computed analytics for a session.

        Args:
            session_id: Interview session ID

        Returns:
            Analytics object if exists, None otherwise
        """
        try:
            doc_ref = self.db.collection("interview_analytics").document(session_id)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                return InterviewAnalytics(**data)

            return None

        except Exception as e:
            logger.error(
                f"Error retrieving analytics for session {session_id}: {e}",
                exc_info=True,
            )
            return None

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

    def _load_session(self, session_id: str) -> Optional[InterviewSession]:
        """Load interview session from Firestore."""
        doc_ref = self.db.collection("interview_sessions").document(session_id)
        doc = doc_ref.get()

        if doc.exists:
            return InterviewSession(id=doc.id, **doc.to_dict())

        return None

    def _store_analytics(self, analytics: InterviewAnalytics) -> None:
        """Store analytics in Firestore."""
        doc_ref = self.db.collection("interview_analytics").document(
            analytics.session_id
        )
        doc_ref.set(analytics.model_dump())
        logger.info(f"Analytics stored for session {analytics.session_id}")

    def _compute_dimension_scores(
        self, questions: List[InterviewQuestion], experience_range: str
    ) -> DimensionScores:
        """
        Aggregate dimension scores across all answered questions.
        Compare with benchmarks for experience level.
        """
        # Collect all dimension scores
        structure_scores = []
        depth_scores = []
        tradeoffs_scores = []
        clarity_scores = []

        for q in questions:
            if q.answer and q.gap_analysis:
                gap = q.gap_analysis
                structure_scores.append(gap.get("structure_score", 3.0))
                depth_scores.append(gap.get("depth_score", 3.0))
                tradeoffs_scores.append(gap.get("tradeoffs_score", 3.0))
                clarity_scores.append(gap.get("clarity_score", 3.0))

        # Compute averages
        avg_structure = (
            sum(structure_scores) / len(structure_scores) if structure_scores else 3.0
        )
        avg_depth = sum(depth_scores) / len(depth_scores) if depth_scores else 3.0
        avg_tradeoffs = (
            sum(tradeoffs_scores) / len(tradeoffs_scores) if tradeoffs_scores else 3.0
        )
        avg_clarity = (
            sum(clarity_scores) / len(clarity_scores) if clarity_scores else 3.0
        )

        # Get targets
        target_structure = get_dimension_target(experience_range, "structure")
        target_depth = get_dimension_target(experience_range, "depth")
        target_tradeoffs = get_dimension_target(experience_range, "tradeoffs")
        target_clarity = get_dimension_target(experience_range, "clarity")

        # Generate feedback snippets
        structure_feedback = self._generate_dimension_feedback(
            "structure", avg_structure, target_structure, structure_scores
        )
        depth_feedback = self._generate_dimension_feedback(
            "depth", avg_depth, target_depth, depth_scores
        )
        tradeoffs_feedback = self._generate_dimension_feedback(
            "tradeoffs", avg_tradeoffs, target_tradeoffs, tradeoffs_scores
        )
        clarity_feedback = self._generate_dimension_feedback(
            "clarity", avg_clarity, target_clarity, clarity_scores
        )

        return DimensionScores(
            structure=DimensionScore(
                score=round(avg_structure, 1),
                target=target_structure,
                status=get_dimension_status(avg_structure, target_structure),
                feedback_snippet=structure_feedback,
            ),
            depth=DimensionScore(
                score=round(avg_depth, 1),
                target=target_depth,
                status=get_dimension_status(avg_depth, target_depth),
                feedback_snippet=depth_feedback,
            ),
            tradeoffs=DimensionScore(
                score=round(avg_tradeoffs, 1),
                target=target_tradeoffs,
                status=get_dimension_status(avg_tradeoffs, target_tradeoffs),
                feedback_snippet=tradeoffs_feedback,
            ),
            clarity=DimensionScore(
                score=round(avg_clarity, 1),
                target=target_clarity,
                status=get_dimension_status(avg_clarity, target_clarity),
                feedback_snippet=clarity_feedback,
            ),
        )

    def _generate_dimension_feedback(
        self, dimension: str, score: float, target: float, all_scores: List[float]
    ) -> str:
        """Generate feedback snippet for a dimension."""
        status = get_dimension_status(score, target)

        dimension_names = {
            "structure": "answer organization",
            "depth": "technical depth",
            "tradeoffs": "trade-off discussion",
            "clarity": "communication clarity",
        }

        dimension_issues = {
            "structure": "answers lacked clear structure",
            "depth": "missed key concepts in multiple answers",
            "tradeoffs": "rarely discussed pros/cons or use cases",
            "clarity": "explanations were sometimes unclear or rambling",
        }

        dimension_strengths = {
            "structure": "answers were well-organized",
            "depth": "demonstrated solid technical understanding",
            "tradeoffs": "showed good awareness of trade-offs",
            "clarity": "communicated clearly and concisely",
        }

        name = dimension_names.get(dimension, dimension)

        if status == "Below Bar":
            issue = dimension_issues.get(dimension, f"{name} needs improvement")
            return f"Your {issue}. Focus on improving this area."
        elif status == "At Bar":
            return f"Your {name} meets expectations for your experience level."
        else:  # Exceeds Bar
            strength = dimension_strengths.get(dimension, f"{name} was excellent")
            return f"Your {strength}. This is a strength!"

    def _compute_overall_score(self, dimension_scores: DimensionScores) -> float:
        """
        Compute overall score (0-100) from dimension scores.
        Uses weighted average then scales to 0-100.
        """
        weighted_avg = (
            dimension_scores.structure.score * DIMENSION_WEIGHTS["structure"]
            + dimension_scores.depth.score * DIMENSION_WEIGHTS["depth"]
            + dimension_scores.tradeoffs.score * DIMENSION_WEIGHTS["tradeoffs"]
            + dimension_scores.clarity.score * DIMENSION_WEIGHTS["clarity"]
        )

        # Scale from 1-5 to 0-100
        # 1.0 → 0, 3.0 → 50, 5.0 → 100
        overall = (weighted_avg - 1.0) * 25.0

        return round(overall, 1)

    def _compute_concept_mastery(
        self, questions: List[InterviewQuestion]
    ) -> ConceptMastery:
        """
        Aggregate concept coverage across all questions.
        """
        all_covered = set()
        all_missing = set()
        all_incorrect = {}  # concept -> explanation

        for q in questions:
            if q.answer and q.gap_analysis:
                gap = q.gap_analysis

                # Covered concepts
                covered = gap.get("covered_concepts", [])
                all_covered.update(covered)

                # Missing concepts
                missing = gap.get("missing_concepts", [])
                all_missing.update(missing)

                # Incorrect concepts
                incorrect = gap.get("incorrect_concepts", [])
                for concept in incorrect:
                    if concept not in all_incorrect:
                        all_incorrect[concept] = (
                            f"Explained incorrectly in Q{q.sequence}"
                        )

        # Remove concepts that were covered in later questions from missing
        all_missing = all_missing - all_covered

        # Build incorrect list with explanations
        incorrect_list = [
            ConceptDetail(concept=concept, explanation=explanation)
            for concept, explanation in all_incorrect.items()
        ]

        return ConceptMastery(
            covered_well=sorted(list(all_covered)),
            partially_covered=[],  # TODO: Implement partial coverage detection
            missing=sorted(list(all_missing)),
            incorrect=incorrect_list,
        )

    def _compute_skill_performance(
        self, questions: List[InterviewQuestion]
    ) -> Tuple[List[SkillPerformance], Optional[SkillPerformance]]:
        """
        Group questions by skill and compute per-skill performance.
        """
        # Group questions by skill_id
        skill_questions: Dict[str, List[InterviewQuestion]] = {}

        for q in questions:
            if q.skill_id:
                if q.skill_id not in skill_questions:
                    skill_questions[q.skill_id] = []
                skill_questions[q.skill_id].append(q)

        # Compute performance for each skill
        skill_performances = []

        for skill_id, skill_qs in skill_questions.items():
            # Get skill label
            skill_label = self._get_skill_label(skill_id)

            # Compute question performances
            question_perfs = []
            skill_scores = []

            for q in skill_qs:
                if q.answer and q.gap_analysis:
                    gap = q.gap_analysis

                    # Compute question overall score (average of dimensions)
                    q_score = (
                        gap.get("structure_score", 3.0)
                        + gap.get("depth_score", 3.0)
                        + gap.get("tradeoffs_score", 3.0)
                        + gap.get("clarity_score", 3.0)
                    ) / 4.0

                    skill_scores.append(q_score)

                    # Get top gaps
                    missing = gap.get("missing_concepts", [])
                    key_gaps = missing[:3] if len(missing) > 0 else []

                    question_perfs.append(
                        QuestionPerformance(
                            question_id=q.question_id,
                            question_text=(
                                q.question[:100] + "..."
                                if len(q.question) > 100
                                else q.question
                            ),
                            question_type=q.question_type,
                            overall_score=round(q_score, 1),
                            key_gaps=key_gaps,
                        )
                    )

            # Compute average score for skill
            avg_score = sum(skill_scores) / len(skill_scores) if skill_scores else 3.0

            skill_performances.append(
                SkillPerformance(
                    skill_id=skill_id,
                    skill_label=skill_label,
                    questions_asked=len(skill_qs),
                    avg_score=round(avg_score, 1),
                    questions=question_perfs,
                )
            )

        # Find weakest skill
        weakest = (
            min(skill_performances, key=lambda s: s.avg_score)
            if skill_performances
            else None
        )

        return skill_performances, weakest

    def _get_skill_label(self, skill_id: str) -> str:
        """Get skill label from skill map."""
        for skill in FRONTEND_SKILL_MAP:
            if skill.id == skill_id:
                return skill.label
        return skill_id

    def _compute_confidence_distribution(
        self, questions: List[InterviewQuestion]
    ) -> Distribution:
        """Count confidence levels across all questions."""
        high = medium = low = 0

        for q in questions:
            if q.answer and q.gap_analysis:
                level = q.gap_analysis.get("confidence_level", "medium")
                if level == "high":
                    high += 1
                elif level == "medium":
                    medium += 1
                else:
                    low += 1

        return Distribution(high=high, medium=medium, low=low)

    def _compute_clarity_distribution(
        self, questions: List[InterviewQuestion]
    ) -> Distribution:
        """Count clarity levels across all questions."""
        high = medium = low = 0

        for q in questions:
            if q.answer and q.gap_analysis:
                level = q.gap_analysis.get("clarity_level", "medium")
                if level == "high":
                    high += 1
                elif level == "medium":
                    medium += 1
                else:
                    low += 1

        return Distribution(high=high, medium=medium, low=low)

    def _aggregate_confusion_signals(
        self, questions: List[InterviewQuestion]
    ) -> List[str]:
        """Collect all confusion signals from all questions."""
        all_signals = []

        for q in questions:
            if q.answer and q.gap_analysis:
                signals = q.gap_analysis.get("confusion_signals", [])
                # Add question context to each signal
                for signal in signals:
                    all_signals.append(f"{signal} (Q{q.sequence})")

        return all_signals

    def _detect_patterns(
        self,
        confidence_dist: Distribution,
        clarity_dist: Distribution,
        questions: List[InterviewQuestion],
    ) -> Optional[str]:
        """
        Detect patterns in confidence/clarity correlation.
        Rule-based pattern detection.
        """
        total = confidence_dist.high + confidence_dist.medium + confidence_dist.low

        if total == 0:
            return None

        # Pattern 1: Low confidence correlates with low clarity
        low_conf_low_clarity = 0
        for q in questions:
            if q.answer and q.gap_analysis:
                gap = q.gap_analysis
                if (
                    gap.get("confidence_level") == "low"
                    and gap.get("clarity_level") == "low"
                ):
                    low_conf_low_clarity += 1

        if low_conf_low_clarity >= 2:
            return "When you're unsure (low confidence), your clarity also drops. Practice structuring answers even when uncertain."

        # Pattern 2: Consistently low confidence
        if confidence_dist.low / total > 0.6:
            return "You showed low confidence in most answers. Build confidence through more practice and preparation."

        # Pattern 3: Consistently low clarity
        if clarity_dist.low / total > 0.6:
            return "Your explanations were often unclear. Focus on structuring answers: define → explain → example."

        # Pattern 4: Good performance
        if confidence_dist.high / total > 0.6 and clarity_dist.high / total > 0.6:
            return "You demonstrated strong confidence and clarity throughout the interview. Keep it up!"

        return None

    def _compute_followup_analysis(
        self, questions: List[InterviewQuestion], experience_range: str
    ) -> FollowUpAnalysis:
        """Analyze follow-up patterns."""
        total_questions = len([q for q in questions if q.answer])
        total_followups = len(
            [q for q in questions if q.question_type == "follow_up" and q.answer]
        )

        # Compute ratio
        followup_ratio = (
            total_followups / total_questions if total_questions > 0 else 0.0
        )

        # Count intents
        intent_distribution = {}
        for q in questions:
            if q.answer and q.gap_analysis:
                intent = q.gap_analysis.get("followup_intent")
                if intent:
                    intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

        # Get benchmark
        benchmark = get_benchmark(experience_range)
        benchmark_ratio = benchmark.get("followup_ratio_target", 0.4)

        return FollowUpAnalysis(
            total_followups=total_followups,
            followup_ratio=round(followup_ratio, 2),
            intent_distribution=intent_distribution,
            benchmark_ratio=benchmark_ratio,
        )

    def _compute_average_response_time(
        self, questions: List[InterviewQuestion]
    ) -> Optional[str]:
        """Compute average response time if timestamps available."""
        from datetime import timezone
        
        response_times = []

        for q in questions:
            if q.answer and q.answered_at and q.created_at:
                # Compute time difference
                if isinstance(q.answered_at, str):
                    answered_at = datetime.fromisoformat(
                        q.answered_at.replace("Z", "+00:00")
                    )
                else:
                    answered_at = q.answered_at
                    # Make timezone-aware if naive
                    if answered_at.tzinfo is None:
                        answered_at = answered_at.replace(tzinfo=timezone.utc)

                if isinstance(q.created_at, str):
                    created_at = datetime.fromisoformat(
                        q.created_at.replace("Z", "+00:00")
                    )
                else:
                    created_at = q.created_at
                    # Make timezone-aware if naive
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)

                delta = (answered_at - created_at).total_seconds()
                response_times.append(delta)

        if not response_times:
            return None

        avg_seconds = sum(response_times) / len(response_times)

        # Format as "Xm Ys"
        minutes = int(avg_seconds // 60)
        seconds = int(avg_seconds % 60)

        return f"{minutes}m {seconds}s"

    def _get_skills_covered(self, questions: List[InterviewQuestion]) -> List[str]:
        """Get list of skill labels covered in interview."""
        skill_ids = set()
        for q in questions:
            if q.skill_id:
                skill_ids.add(q.skill_id)

        skill_labels = []
        for skill_id in skill_ids:
            label = self._get_skill_label(skill_id)
            skill_labels.append(label)

        return sorted(skill_labels)

    def _generate_recommendations(
        self,
        weakest_skill: Optional[SkillPerformance],
        concept_mastery: ConceptMastery,
        dimension_scores: DimensionScores,
        followup_analysis: FollowUpAnalysis,
    ) -> List[str]:
        """
        Generate prioritized action items for improvement.
        Rule-based recommendation engine.
        """
        recommendations = []

        # Priority 1: Weakest skill
        if weakest_skill and weakest_skill.avg_score < 3.5:
            recommendations.append(
                f"🎯 Priority 1: Master {weakest_skill.skill_label} "
                f"(your weakest skill with score {weakest_skill.avg_score}/5.0). "
                f"Practice 2-3 more sessions focusing on this skill."
            )

        # Priority 2: Missing concepts
        if len(concept_mastery.missing) > 0:
            top_missing = concept_mastery.missing[:5]
            recommendations.append(
                f"📚 Priority 2: Study these concepts: {', '.join(top_missing)}. "
                f"These were expected but not mentioned in your answers."
            )

        # Priority 3: Lowest dimension
        dimensions = [
            ("structure", dimension_scores.structure),
            ("depth", dimension_scores.depth),
            ("tradeoffs", dimension_scores.tradeoffs),
            ("clarity", dimension_scores.clarity),
        ]
        lowest_dim = min(dimensions, key=lambda x: x[1].score)

        if lowest_dim[1].status == "Below Bar":
            dim_name = lowest_dim[0].capitalize()
            recommendations.append(
                f"💪 Priority 3: Improve {dim_name} "
                f"(score: {lowest_dim[1].score}/{lowest_dim[1].target} target). "
                f"{lowest_dim[1].feedback_snippet}"
            )

        # Priority 4: Follow-up ratio
        if followup_analysis.followup_ratio > followup_analysis.benchmark_ratio + 0.2:
            recommendations.append(
                f"🔄 Priority 4: Reduce follow-up triggers. "
                f"You triggered {followup_analysis.total_followups} follow-ups. "
                f"Strong candidates typically trigger fewer follow-ups by providing complete first answers."
            )

        # Priority 5: Incorrect concepts
        if len(concept_mastery.incorrect) > 0:
            incorrect_list = [c.concept for c in concept_mastery.incorrect]
            recommendations.append(
                f"⚠️ Priority 5: Correct misconceptions about: {', '.join(incorrect_list)}. "
                f"These concepts were explained incorrectly."
            )

        # If no major issues, give positive feedback
        if not recommendations:
            recommendations.append(
                "✅ Great job! You're interview-ready. "
                "Continue practicing to maintain your skills."
            )

        return recommendations
