"""
Interview Orchestrator - Backend Controller for Interview Flow

This module contains pure, deterministic logic for controlling interview flow.
It decides what happens next (follow-up, new primary, or end) based on session state.

Key Principles:
- No LLM calls - purely deterministic
- No side effects - only computes decisions
- Single responsibility - only decides, doesn't execute
"""

import logging
from typing import List, Optional, Tuple

from app.models.interview import (
    InterviewSession,
    InterviewQuestion,
    InterviewState,
    OrchestratorDecision,
)
from app.models.gap_analysis import GapAnalysisOutput
from app.core.config.skillMaps.base import Skill
from app.utils.skill_selection import select_next_skill_by_importance
from app.utils.experience_mapper import normalize_experience_for_skill
from app.utils.skill_map_selector import get_skill_map_for_role

logger = logging.getLogger(__name__)


class InterviewOrchestrator:
    """
    Deterministic orchestrator that controls interview flow.

    Makes decisions based on:
    - Total questions asked vs limit
    - Follow-ups for current skill vs limit
    - Available skills remaining
    - Gap analysis signals
    """

    MAX_TOTAL_QUESTIONS = 8
    MAX_FOLLOWUPS_PER_SKILL = 2

    def compute_state(self, session: InterviewSession) -> InterviewState:
        """
        Compute the current interview state from session data.

        This is a pure function that derives state from the questions array.
        """
        questions = session.questions
        total_questions_asked = len(questions)

        # Find skills covered (from primary questions)
        skills_covered: List[str] = []
        current_skill_id: Optional[str] = None
        current_skill_label: Optional[str] = None

        for q in questions:
            if q.question_type == "primary" and q.skill_id:
                if q.skill_id not in skills_covered:
                    skills_covered.append(q.skill_id)
                current_skill_id = q.skill_id

        # Get current skill label from calibration or skill map
        if current_skill_id:
            # Try to get from calibration first
            if session.calibration and session.calibration.selected_skill:
                if session.calibration.selected_skill.get("id") == current_skill_id:
                    current_skill_label = session.calibration.selected_skill.get(
                        "label"
                    )

            # Fallback to skill map based on role
            if not current_skill_label:
                skill_map = get_skill_map_for_role(session.role)
                for skill in skill_map:
                    if skill.id == current_skill_id:
                        current_skill_label = skill.label
                        break

        # Count follow-ups for current skill
        # Follow-ups are questions after the last primary question
        followups_for_current_skill = 0
        if questions:
            # Count backwards from the end until we hit a primary question
            for q in reversed(questions):
                if q.question_type == "follow_up":
                    followups_for_current_skill += 1
                elif q.question_type == "primary":
                    break

        return InterviewState(
            total_questions_asked=total_questions_asked,
            current_skill_id=current_skill_id,
            current_skill_label=current_skill_label,
            followups_for_current_skill=followups_for_current_skill,
            skills_covered=skills_covered,
            max_questions=self.MAX_TOTAL_QUESTIONS,
            max_followups_per_skill=self.MAX_FOLLOWUPS_PER_SKILL,
        )

    def should_ask_followup(
        self,
        gap_analysis: GapAnalysisOutput,
        state: InterviewState,
    ) -> Tuple[bool, str]:
        """
        Determine if a follow-up question is warranted based on gap analysis signals.

        Decision Rules:
        1. If at follow-up limit -> No
        2. If answer is perfect (all covered, high confidence, no issues) -> No
        3. If answer is strong (minimal gaps, high confidence) -> Only validate_understanding
        4. Otherwise -> Yes

        Returns:
            Tuple of (should_ask, reason)
        """
        # Already at limit?
        if state.followups_for_current_skill >= self.MAX_FOLLOWUPS_PER_SKILL:
            return False, f"Follow-up limit reached ({self.MAX_FOLLOWUPS_PER_SKILL})"

        # Perfect answer?
        is_perfect = (
            len(gap_analysis.missing_concepts) == 0
            and len(gap_analysis.incorrect_concepts) == 0
            and len(gap_analysis.confusion_signals) == 0
            and gap_analysis.confidence_level == "high"
            and gap_analysis.clarity_level == "high"
        )

        if is_perfect:
            logger.info("Answer is perfect - skipping follow-up")
            return False, "Answer is complete and correct - no follow-up needed"

        # Strong answer (minimal issues)?
        is_strong = (
            len(gap_analysis.missing_concepts) <= 1
            and len(gap_analysis.incorrect_concepts) == 0
            and len(gap_analysis.confusion_signals) == 0
            and gap_analysis.confidence_level == "high"
        )

        if is_strong:
            # Only ask lightweight validation for strong answers
            if gap_analysis.followup_intent == "validate_understanding":
                logger.info("Strong answer - asking lightweight validation")
                return True, "Validating strong answer with lightweight follow-up"
            else:
                logger.info("Strong answer - moving to next skill")
                return False, "Answer is strong - moving to next skill"

        # Otherwise, follow-up is warranted
        logger.info(f"Follow-up warranted: {gap_analysis.followup_intent}")
        return True, f"Follow-up needed: {gap_analysis.followup_intent}"

    def decide_next_action(
        self,
        state: InterviewState,
        gap_analysis: Optional[GapAnalysisOutput],
        experience_level: str,
        role: str,
    ) -> Tuple[OrchestratorDecision, str, Optional[Skill]]:
        """
        Decide the next action based on current state and gap analysis.

        This is a pure function with no side effects.

        Args:
            state: Current computed interview state
            gap_analysis: Gap analysis from the last answer (may be None)
            experience_level: Experience level for skill filtering
            role: The role to select skills for

        Returns:
            Tuple of (decision, reason, next_skill)
            - next_skill is only set for ASK_NEW_PRIMARY decisions
        """
        # Rule 1: Question limit reached
        if state.total_questions_asked >= self.MAX_TOTAL_QUESTIONS:
            logger.info(
                f"Decision: END_INTERVIEW - question limit reached ({state.total_questions_asked}/{self.MAX_TOTAL_QUESTIONS})"
            )
            return (
                OrchestratorDecision.END_INTERVIEW,
                f"Maximum question limit reached ({self.MAX_TOTAL_QUESTIONS} questions)",
                None,
            )

        # Rule 2: Should we ask a follow-up based on answer quality?
        if gap_analysis is not None:
            should_followup, followup_reason = self.should_ask_followup(
                gap_analysis=gap_analysis,
                state=state,
            )

            if should_followup:
                logger.info(
                    f"Decision: ASK_FOLLOWUP - {followup_reason}, "
                    f"followups={state.followups_for_current_skill}/{self.MAX_FOLLOWUPS_PER_SKILL}"
                )
                return (
                    OrchestratorDecision.ASK_FOLLOWUP,
                    f"Following up on {state.current_skill_label or 'current skill'} "
                    f"({followup_reason})",
                    None,
                )
            else:
                logger.info(f"Skipping follow-up: {followup_reason}")

        # Rule 3: Need new primary - check available skills
        skill_level = normalize_experience_for_skill(experience_level)
        skill_map = get_skill_map_for_role(role)
        next_skill = select_next_skill_by_importance(
            skills=skill_map,
            used_skill_ids=state.skills_covered,
            experience_level=skill_level,
        )

        if next_skill:
            logger.info(
                f"Decision: ASK_NEW_PRIMARY - moving to skill: {next_skill.label}"
            )
            return (
                OrchestratorDecision.ASK_NEW_PRIMARY,
                f"Moving to new skill: {next_skill.label}",
                next_skill,
            )

        # Rule 4: No more skills available
        logger.info("Decision: END_INTERVIEW - no more skills available")
        return (
            OrchestratorDecision.END_INTERVIEW,
            "All available skills have been covered",
            None,
        )

    def get_available_skills(
        self, used_skill_ids: List[str], experience_level: str, role: str
    ) -> List[Skill]:
        """
        Get list of unused interview-safe skills, sorted by importance (descending).

        Args:
            used_skill_ids: List of skill IDs already used
            experience_level: Experience level for filtering
            role: The role to select skills for

        Returns:
            List of available skills sorted by importance
        """
        skill_level = normalize_experience_for_skill(experience_level)

        # Use the experience level mapping from skill_selection
        from app.utils.skill_selection import EXPERIENCE_TO_LEVELS

        allowed_levels = EXPERIENCE_TO_LEVELS.get(
            skill_level, {"foundational", "intermediate"}
        )

        skill_map = get_skill_map_for_role(role)
        available = [
            skill
            for skill in skill_map
            if skill.interview_safe
            and skill.level in allowed_levels
            and skill.id not in used_skill_ids
        ]

        # Sort by importance descending
        available.sort(key=lambda s: s.importance, reverse=True)

        return available


# Singleton instance for convenience
orchestrator = InterviewOrchestrator()
