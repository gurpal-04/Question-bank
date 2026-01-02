import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime
from google.cloud import firestore
from app.models.interview import InterviewSession
from app.services.ai_agents.Interview.interview_context_agent.agent import generate_interview_context
from app.services.first_question_service import generate_first_question
from app.utils.skill_selection import select_primary_skill
from app.utils.archetype_selector import select_question_archetype
from app.utils.experience_mapper import (
    normalize_experience_for_archetype,
    normalize_experience_for_skill,
)
from app.core.config.skillMaps.frontend import FRONTEND_SKILL_MAP

logger = logging.getLogger(__name__)

class InterviewService:
    def __init__(self, db: firestore.Client):
        self.db = db

    async def generate_and_store_first_question(self, *, user_id: str, role: str, experience_range: str, difficulty: str,
                                                interview_context: Optional[Dict[str, Any]] = None, seed: Optional[str] = None) -> InterviewSession:
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
            first_question = await generate_first_question(
                interview_context=interview_context,
                selected_skill=selected_skill.label,
                question_archetype=selected_archetype.label,
                experience_level=experience_range,
            )
            first_question['skill_id'] = selected_skill.id

            # --- Persist session to Firestore ---
            session_data = {
                'user_id': user_id,
                'role': role,
                'experience_range': experience_range,
                'difficulty': difficulty,
                'interview_context': interview_context,
                'selected_skill': {
                    'id': selected_skill.id,
                    'label': selected_skill.label,
                    'level': selected_skill.level,
                    'description': selected_skill.description,
                },
                'selected_archetype': {
                    'id': selected_archetype.id,
                    'label': selected_archetype.label,
                    'description': selected_archetype.description,
                },
                'first_question': first_question,
                'created_at': datetime.utcnow(),
            }
            doc_ref = self.db.collection('interview_sessions').document()
            doc_ref.set(session_data)
            session_id = doc_ref.id
            session_data['id'] = session_id
            return InterviewSession(**session_data)
        except Exception as e:
            logger.error(f"Error in generate_and_store_first_question: {e}", exc_info=True)
            raise

    def get_sessions_by_user(self, user_id: str) -> List[InterviewSession]:
        session_docs = self.db.collection('interview_sessions').where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        sessions = [InterviewSession(id=doc.id, **doc.to_dict()) for doc in session_docs]
        return sessions

    def get_session_by_id(self, session_id: str) -> Optional[InterviewSession]:
        doc_ref = self.db.collection('interview_sessions').document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            return InterviewSession(id=doc.id, **doc.to_dict())
        return None
