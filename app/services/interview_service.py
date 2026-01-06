import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime
from google.cloud import firestore
from app.models.interview import InterviewSession, CalibrationData, InterviewQuestion
from app.services.ai_agents.Interview.interview_context_agent.agent import (
    generate_interview_context,
)
from app.services.first_question_service import generate_first_question
from app.utils.skill_selection import select_primary_skill
from app.utils.archetype_selector import select_question_archetype
from app.utils.experience_mapper import (
    normalize_experience_for_archetype,
    normalize_experience_for_skill,
)
from app.core.config.skillMaps.frontend import FRONTEND_SKILL_MAP
from app.models.gap_analysis import GapAnalysisOutput
from app.services.ai_agents.Interview.gap_analysis_agent import (
    gap_analysis_runner,
    gap_analysis_agent,
)
from app.services.ai_agents.runner_utils import run_agent_with_runner
import json

logger = logging.getLogger(__name__)


class InterviewService:
    def __init__(self, db: firestore.Client):
        self.db = db

    async def generate_and_store_first_question(
        self,
        *,
        user_id: str,
        role: str,
        experience_range: str,
        difficulty: str,
        interview_context: Optional[Dict[str, Any]] = None,
        seed: Optional[str] = None,
    ) -> InterviewSession:
        """
        Orchestrate, persist, and return an interview session for the first question.
        """
        try:
            # 1. Generate or use provided context
            if interview_context is None:
                interview_context = await generate_interview_context(
                    role=role,
                    experience_range=experience_range,
                    difficulty=difficulty,
                )
            # 2. Skill selection
            skill_level = normalize_experience_for_skill(experience_range)
            if seed:
                random.seed(f"{seed}_skill")
            selected_skill = select_primary_skill(
                skills=FRONTEND_SKILL_MAP,
                experience_level=skill_level,
            )
            # 3. Archetype selection
            archetype_experience = normalize_experience_for_archetype(experience_range)
            if seed:
                random.seed(f"{seed}_archetype")
            selected_archetype = select_question_archetype(
                role=role,
                experience=archetype_experience,
                seed=seed,
            )
            # 4. Generate question
            first_question_data = await generate_first_question(
                interview_context=interview_context,
                selected_skill=selected_skill.label,
                question_archetype=selected_archetype.label,
                experience_level=experience_range,
            )

            # Construct CalibrationData
            calibration = CalibrationData(
                selected_skill={
                    "id": selected_skill.id,
                    "label": selected_skill.label,
                    "level": selected_skill.level,
                    "description": selected_skill.description,
                },
                selected_archetype={
                    "id": selected_archetype.id,
                    "label": selected_archetype.label,
                    "description": selected_archetype.description,
                },
            )

            # Construct First InterviewQuestion
            first_question = InterviewQuestion(
                sequence=1,
                question_type="primary",
                question=first_question_data["question"],
                archetype=first_question_data["archetype"],
                # skill_id is removed from InterviewQuestion model as per user request
            )

            # --- Persist session to Firestore ---
            session_data = {
                "user_id": user_id,
                "role": role,
                "experience_range": experience_range,
                "difficulty": difficulty,
                "interview_context": interview_context,
                "calibration": calibration.model_dump(),
                "questions": [first_question.model_dump()],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            doc_ref = self.db.collection("interview_sessions").document()
            doc_ref.set(session_data)
            session_id = doc_ref.id
            session_data["id"] = session_id
            return InterviewSession(**session_data)
        except Exception as e:
            logger.error(
                f"Error in generate_and_store_first_question: {e}", exc_info=True
            )
            raise

    async def perform_gap_analysis(
        self, question: str, answer: str, expected_concepts: List[str]
    ) -> GapAnalysisOutput:
        """
        Analyze candidate answer for knowledge gaps using the AI agent.
        """
        try:
            prompt_data = {
                "question": question,
                "answer": answer,
                "expected_concepts": expected_concepts,
            }
            prompt = json.dumps(prompt_data, indent=2)

            result = await run_agent_with_runner(
                runner=gap_analysis_runner,
                agent=gap_analysis_agent,
                prompt=prompt,
            )

            if isinstance(result, dict):
                return GapAnalysisOutput(**result)

            try:
                parsed = json.loads(result) if isinstance(result, str) else result
                return GapAnalysisOutput(**parsed)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse agent output: {e}")
                raise ValueError(f"Agent returned invalid output format: {result}")

        except Exception as e:
            logger.error(f"Error in perform_gap_analysis: {e}", exc_info=True)
            raise

    def get_sessions_by_user(self, user_id: str) -> List[InterviewSession]:
        session_docs = (
            self.db.collection("interview_sessions")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        sessions = [
            InterviewSession(id=doc.id, **doc.to_dict()) for doc in session_docs
        ]
        return sessions

    def get_session_by_id(self, session_id: str) -> Optional[InterviewSession]:
        doc_ref = self.db.collection("interview_sessions").document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            return InterviewSession(id=doc.id, **doc.to_dict())
        return None

    async def submit_answer(
        self, session_id: str, question_id: str, answer: str
    ) -> GapAnalysisOutput:
        """
        Submit the candidate's answer to a specific question and run gap analysis.
        Updates the session with the answer and analysis result.
        """
        try:
            # 1. Retrieve session
            session = self.get_session_by_id(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            # 2. Get concepts and find the question to answer
            if not session.questions:
                raise ValueError("Session contains no questions")

            # Find the specific question by ID
            target_question = None
            target_index = -1
            for idx, q in enumerate(session.questions):
                if q.question_id == question_id:
                    target_question = q
                    target_index = idx
                    break

            if not target_question:
                raise ValueError(
                    f"Question {question_id} not found in session {session_id}"
                )

            if target_question.answer:
                raise ValueError(f"Question {question_id} has already been answered")

            # Note: We use the general expected concepts from the context
            expected_concepts = session.interview_context.get("expected_concepts", [])
            if not expected_concepts:
                logger.warning(
                    f"No expected concepts found for session {session_id}, utilizing default empty list for analysis"
                )

            # 3. Perform Gap Analysis
            gap_analysis_result = await self.perform_gap_analysis(
                question=target_question.question,
                answer=answer,
                expected_concepts=expected_concepts,
            )

            # 4. Update Session
            doc_ref = self.db.collection("interview_sessions").document(session_id)

            # Retrieve current 'questions' array from Firestore to append/update reliably
            updated_questions = [q.model_dump() for q in session.questions]
            updated_questions[target_index]["answer"] = answer
            updated_questions[target_index][
                "gap_analysis"
            ] = gap_analysis_result.model_dump()

            update_data = {
                "questions": updated_questions,
                "updated_at": datetime.utcnow(),
            }
            doc_ref.update(update_data)

            return gap_analysis_result

        except Exception as e:
            logger.error(f"Error in submit_answer: {e}", exc_info=True)
            raise
