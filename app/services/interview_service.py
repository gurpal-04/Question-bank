import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime
from google.cloud import firestore
from app.models.interview import (
    InterviewSession,
    CalibrationData,
    InterviewQuestion,
    InterviewState,
    OrchestratorDecision,
    StartInterviewResponse,
    AnswerResponse,
)
from app.services.ai_agents.Interview.interview_context_agent.agent import (
    generate_interview_context,
)
from app.services.primary_question_service import generate_primary_question
from app.utils.skill_selection import (
    select_primary_skill,
    select_next_skill_by_importance,
)
from app.utils.archetype_selector import select_question_archetype
from app.utils.experience_mapper import (
    normalize_experience_for_archetype,
    normalize_experience_for_skill,
)
from app.core.config.skillMaps.frontend import FRONTEND_SKILL_MAP, FrontendSkill
from app.models.gap_analysis import GapAnalysisOutput
from app.services.ai_agents.Interview.gap_analysis_agent import (
    gap_analysis_runner,
    gap_analysis_agent,
)
from app.services.ai_agents.runner_utils import run_agent_with_runner
from app.services.orchestrator import orchestrator
import json

logger = logging.getLogger(__name__)


class InterviewService:
    def __init__(self, db: firestore.Client):
        self.db = db

    async def generate_and_store_primary_question(
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
        Orchestrate, persist, and return an interview session for the primary question.
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
            primary_question_data = await generate_primary_question(
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

            # Construct Primary InterviewQuestion
            primary_question = InterviewQuestion(
                sequence=1,
                question_type="primary",
                question=primary_question_data["question"],
                archetype=primary_question_data["archetype"],
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
                "questions": [primary_question.model_dump()],
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
                f"Error in generate_and_store_primary_question: {e}", exc_info=True
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
                gap_analysis = GapAnalysisOutput(**result)
                self._validate_dimension_scores(gap_analysis)
                return gap_analysis

            try:
                parsed = json.loads(result) if isinstance(result, str) else result
                gap_analysis = GapAnalysisOutput(**parsed)
                self._validate_dimension_scores(gap_analysis)
                return gap_analysis
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse agent output: {e}")
                raise ValueError(f"Agent returned invalid output format: {result}")

        except Exception as e:
            logger.error(f"Error in perform_gap_analysis: {e}", exc_info=True)
            raise

    def _validate_dimension_scores(self, gap_analysis: GapAnalysisOutput) -> None:
        """
        Validate consistency between signals and dimension scores.
        Logs warnings for inconsistencies but does not block.
        """
        # 1. Clarity consistency
        if gap_analysis.clarity_level == "low" and gap_analysis.clarity_score > 2.5:
            logger.warning(
                f"GapAnalysis: clarity_level 'low' but score {gap_analysis.clarity_score} > 2.5"
            )
        elif gap_analysis.clarity_level == "high" and gap_analysis.clarity_score < 3.5:
            logger.warning(
                f"GapAnalysis: clarity_level 'high' but score {gap_analysis.clarity_score} < 3.5"
            )

        # 2. Depth consistency
        if len(gap_analysis.missing_concepts) > 3 and gap_analysis.depth_score >= 3.5:
            logger.warning(
                f"GapAnalysis: >3 missing concepts but depth_score {gap_analysis.depth_score} >= 3.5"
            )
        if gap_analysis.incorrect_concepts and gap_analysis.depth_score >= 4.0:
            logger.warning(
                f"GapAnalysis: incorrect concepts present but depth_score {gap_analysis.depth_score} >= 4.0"
            )

        # 3. Structure consistency
        if (
            len(gap_analysis.confusion_signals) > 2
            and gap_analysis.structure_score >= 4.0
        ):
            logger.warning(
                f"GapAnalysis: >2 confusion signals but structure_score {gap_analysis.structure_score} >= 4.0"
            )

        # 4. Confidence consistency
        avg_score = (
            gap_analysis.structure_score
            + gap_analysis.depth_score
            + gap_analysis.tradeoffs_score
            + gap_analysis.clarity_score
        ) / 4.0
        if gap_analysis.confidence_level == "low" and avg_score >= 4.0:
            logger.warning(
                f"GapAnalysis: confidence 'low' but avg score {avg_score} >= 4.0"
            )

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

    async def generate_and_store_followup_question(
        self, session_id: str
    ) -> InterviewSession:
        """
        Generate a followup question based on the last answered question and its gap analysis.
        Appends the followup question to the session's questions array.
        """
        try:
            # 1. Retrieve session
            session = self.get_session_by_id(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            if not session.questions:
                raise ValueError("Session contains no questions")

            # 2. Find the last answered question
            last_answered_question = None
            for q in reversed(session.questions):
                if q.answer and q.gap_analysis:
                    last_answered_question = q
                    break

            if not last_answered_question:
                raise ValueError(
                    "No answered question with gap analysis found in session"
                )

            # 3. Prepare input for followup question generator
            from app.services.ai_agents.Interview.followup_question_generator.agent import (
                followup_question_generator_runner,
                followup_question_generator_agent,
            )

            primary_skill = session.calibration.selected_skill.get("label", "")
            if not primary_skill:
                raise ValueError("Primary skill not found in session calibration")

            prompt_data = {
                "interview_context": session.interview_context,
                "primary_skill": primary_skill,
                "previous_question": last_answered_question.question,
                "candidate_answer": last_answered_question.answer,
                "evaluation_signals": last_answered_question.gap_analysis,
                "followup_intent": last_answered_question.gap_analysis.get(
                    "followup_intent", "probe_depth"
                ),
            }

            prompt = json.dumps(prompt_data, indent=2)

            # 4. Generate followup question
            result = await run_agent_with_runner(
                runner=followup_question_generator_runner,
                agent=followup_question_generator_agent,
                prompt=prompt,
            )

            # Parse result
            if isinstance(result, dict):
                followup_data = result
            else:
                try:
                    followup_data = (
                        json.loads(result) if isinstance(result, str) else result
                    )
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Failed to parse followup agent output: {e}")
                    raise ValueError(f"Agent returned invalid output format: {result}")

            # 5. Create new InterviewQuestion
            next_sequence = len(session.questions) + 1
            followup_question = InterviewQuestion(
                sequence=next_sequence,
                question_type="follow_up",
                intent=followup_data.get("intent"),
                question=followup_data.get("question"),
                archetype=None,  # Followup questions don't have archetypes
            )

            # 6. Update session in Firestore
            doc_ref = self.db.collection("interview_sessions").document(session_id)
            updated_questions = [q.model_dump() for q in session.questions]
            updated_questions.append(followup_question.model_dump())

            update_data = {
                "questions": updated_questions,
                "updated_at": datetime.utcnow(),
            }
            doc_ref.update(update_data)

            # 7. Return updated session
            updated_session = self.get_session_by_id(session_id)
            return updated_session

        except Exception as e:
            logger.error(
                f"Error in generate_and_store_followup_question: {e}", exc_info=True
            )
            raise

    # =========================================================================
    # NEW ORCHESTRATOR API METHODS
    # =========================================================================

    async def start_interview(
        self,
        user_id: str,
        role: str,
        experience_range: str,
        difficulty: str,
    ) -> StartInterviewResponse:
        """
        Initialize a new interview session and generate the first question.

        This is the entry point for the new orchestrator API.
        Flow:
        1. Generate interview context
        2. Select first skill (highest importance, interview-safe)
        3. Select archetype
        4. Generate primary question
        5. Create & persist session
        6. Return response with question and state
        """
        try:
            # 1. Generate interview context
            interview_context = await generate_interview_context(
                role=role,
                experience_range=experience_range,
                difficulty=difficulty,
            )

            # 2. Skill selection - use highest importance for first question
            skill_level = normalize_experience_for_skill(experience_range)
            selected_skill = select_next_skill_by_importance(
                skills=FRONTEND_SKILL_MAP,
                used_skill_ids=[],  # No skills used yet
                experience_level=skill_level,
            )

            if not selected_skill:
                # Fallback to random selection if no skill found
                selected_skill = select_primary_skill(
                    skills=FRONTEND_SKILL_MAP,
                    experience_level=skill_level,
                )

            # 3. Archetype selection
            archetype_experience = normalize_experience_for_archetype(experience_range)
            selected_archetype = select_question_archetype(
                role=role,
                experience=archetype_experience,
            )

            # 4. Generate primary question
            primary_question_data = await generate_primary_question(
                interview_context=interview_context,
                selected_skill=selected_skill.label,
                question_archetype=selected_archetype.label,
                experience_level=experience_range,
            )

            # 5. Construct CalibrationData
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

            # 6. Construct Primary InterviewQuestion with skill_id
            primary_question = InterviewQuestion(
                sequence=1,
                question_type="primary",
                skill_id=selected_skill.id,
                question=primary_question_data["question"],
                archetype=primary_question_data["archetype"],
            )

            # 7. Persist session to Firestore
            session_data = {
                "user_id": user_id,
                "role": role,
                "experience_range": experience_range,
                "difficulty": difficulty,
                "interview_context": interview_context,
                "calibration": calibration.model_dump(),
                "questions": [primary_question.model_dump()],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            doc_ref = self.db.collection("interview_sessions").document()
            doc_ref.set(session_data)
            session_id = doc_ref.id
            session_data["id"] = session_id
            session = InterviewSession(**session_data)

            # 8. Compute initial state
            interview_state = orchestrator.compute_state(session)

            return StartInterviewResponse(
                interview_id=session_id,
                question=primary_question,
                interview_state=interview_state,
            )

        except Exception as e:
            logger.error(f"Error in start_interview: {e}", exc_info=True)
            raise

    async def process_answer(
        self,
        interview_id: str,
        answer_text: str,
    ) -> AnswerResponse:
        """
        Process a candidate's answer and determine the next action.

        This is the main orchestration method for the new API.
        Flow:
        1. Load session
        2. Find unanswered question, store answer
        3. Run gap analysis
        4. Compute state
        5. Run orchestrator decision
        6. If ASK_FOLLOWUP: generate follow-up
        7. If ASK_NEW_PRIMARY: select next skill, generate primary
        8. If END_INTERVIEW: mark complete
        9. Persist updates
        10. Return response
        """
        try:
            # 1. Load session
            session = self.get_session_by_id(interview_id)
            if not session:
                raise ValueError(f"Interview session {interview_id} not found")

            if not session.questions:
                raise ValueError("Session contains no questions")

            # 2. Find the unanswered question (should be the last one)
            unanswered_question = None
            unanswered_index = -1
            for idx, q in enumerate(session.questions):
                if q.answer is None:
                    unanswered_question = q
                    unanswered_index = idx
                    break

            if not unanswered_question:
                raise ValueError("No unanswered question found in session")

            # 3. Run gap analysis
            expected_concepts = session.interview_context.get("expected_concepts", [])
            gap_analysis_result = await self.perform_gap_analysis(
                question=unanswered_question.question,
                answer=answer_text,
                expected_concepts=expected_concepts,
            )

            # 4. Update question with answer and gap analysis
            updated_questions = [q.model_dump() for q in session.questions]
            updated_questions[unanswered_index]["answer"] = answer_text
            updated_questions[unanswered_index][
                "answered_at"
            ] = datetime.utcnow().isoformat()
            updated_questions[unanswered_index][
                "gap_analysis"
            ] = gap_analysis_result.model_dump()

            # Temporarily update session object for state computation
            session.questions[unanswered_index].answer = answer_text
            session.questions[unanswered_index].gap_analysis = (
                gap_analysis_result.model_dump()
            )

            # 5. Compute state after answer
            interview_state = orchestrator.compute_state(session)

            # 6. Run orchestrator decision
            decision, reason, next_skill = orchestrator.decide_next_action(
                state=interview_state,
                gap_analysis=gap_analysis_result,
                experience_level=session.experience_range,
            )

            next_question = None
            is_complete = False

            # 7. Execute decision
            if decision == OrchestratorDecision.ASK_FOLLOWUP:
                # Generate follow-up question
                next_question = await self._generate_followup_question(
                    session=session,
                    gap_analysis=gap_analysis_result,
                )
                updated_questions.append(next_question.model_dump())

            elif decision == OrchestratorDecision.ASK_NEW_PRIMARY:
                # Generate new primary question with next skill
                if next_skill:
                    next_question = await self._generate_new_primary_question(
                        session=session,
                        skill=next_skill,
                    )
                    updated_questions.append(next_question.model_dump())

                    # Update calibration with new skill
                    calibration_data = (
                        session.calibration.model_dump() if session.calibration else {}
                    )
                    calibration_data["selected_skill"] = {
                        "id": next_skill.id,
                        "label": next_skill.label,
                        "level": next_skill.level,
                        "description": next_skill.description,
                    }

            elif decision == OrchestratorDecision.END_INTERVIEW:
                is_complete = True

            # 8. Persist updates
            doc_ref = self.db.collection("interview_sessions").document(interview_id)
            update_data = {
                "questions": updated_questions,
                "updated_at": datetime.utcnow(),
            }

            if decision == OrchestratorDecision.ASK_NEW_PRIMARY and next_skill:
                update_data["calibration"] = {
                    "selected_skill": {
                        "id": next_skill.id,
                        "label": next_skill.label,
                        "level": next_skill.level,
                        "description": next_skill.description,
                    },
                    "selected_archetype": (
                        session.calibration.selected_archetype
                        if session.calibration
                        else {}
                    ),
                }

            doc_ref.update(update_data)

            # 9. Recompute state after adding new question
            updated_session = self.get_session_by_id(interview_id)
            if updated_session:
                interview_state = orchestrator.compute_state(updated_session)

            return AnswerResponse(
                decision=decision,
                reason=reason,
                next_question=next_question,
                gap_analysis=gap_analysis_result.model_dump(),
                interview_state=interview_state,
                is_complete=is_complete,
            )

        except Exception as e:
            logger.error(f"Error in process_answer: {e}", exc_info=True)
            raise

    async def _generate_followup_question(
        self,
        session: InterviewSession,
        gap_analysis: GapAnalysisOutput,
    ) -> InterviewQuestion:
        """
        Internal helper to generate a follow-up question.
        """
        from app.services.ai_agents.Interview.followup_question_generator.agent import (
            followup_question_generator_runner,
            followup_question_generator_agent,
        )

        # Get the last answered question
        last_answered = None
        for q in reversed(session.questions):
            if q.answer:
                last_answered = q
                break

        if not last_answered:
            raise ValueError("No answered question found")

        primary_skill = ""
        if session.calibration and session.calibration.selected_skill:
            primary_skill = session.calibration.selected_skill.get("label", "")

        prompt_data = {
            "interview_context": session.interview_context,
            "primary_skill": primary_skill,
            "previous_question": last_answered.question,
            "candidate_answer": last_answered.answer,
            "evaluation_signals": gap_analysis.model_dump(),
            "followup_intent": gap_analysis.followup_intent,
        }

        prompt = json.dumps(prompt_data, indent=2)

        result = await run_agent_with_runner(
            runner=followup_question_generator_runner,
            agent=followup_question_generator_agent,
            prompt=prompt,
        )

        if isinstance(result, dict):
            followup_data = result
        else:
            followup_data = json.loads(result) if isinstance(result, str) else result

        # Get current skill_id from the last primary question
        current_skill_id = None
        for q in reversed(session.questions):
            if q.question_type == "primary" and q.skill_id:
                current_skill_id = q.skill_id
                break

        next_sequence = len(session.questions) + 1
        return InterviewQuestion(
            sequence=next_sequence,
            question_type="follow_up",
            skill_id=current_skill_id,
            intent=followup_data.get("intent"),
            question=followup_data.get("question"),
            archetype=None,
        )

    async def _generate_new_primary_question(
        self,
        session: InterviewSession,
        skill: FrontendSkill,
    ) -> InterviewQuestion:
        """
        Internal helper to generate a new primary question for a different skill.
        """
        # Select a new archetype
        archetype_experience = normalize_experience_for_archetype(
            session.experience_range
        )
        selected_archetype = select_question_archetype(
            role=session.role,
            experience=archetype_experience,
        )

        # Generate primary question for the new skill
        primary_question_data = await generate_primary_question(
            interview_context=session.interview_context,
            selected_skill=skill.label,
            question_archetype=selected_archetype.label,
            experience_level=session.experience_range,
        )

        next_sequence = len(session.questions) + 1
        return InterviewQuestion(
            sequence=next_sequence,
            question_type="primary",
            skill_id=skill.id,
            question=primary_question_data["question"],
            archetype=primary_question_data["archetype"],
        )
