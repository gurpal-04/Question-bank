import json
import logging
from typing import Dict, Any
from app.services.ai_agents.litellm_shim import (
    LiteLLMAgent as Agent,
    LiteLLMRunner as Runner,
    LiteLLMInMemorySessionService as InMemorySessionService,
)
from app.models.interview_context import FollowUpQuestionInput, FollowUpQuestionOutput
from app.services.ai_agents.runner_utils import run_agent_with_runner

logger = logging.getLogger(__name__)

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
followup_question_generator_agent = Agent(
    model="quality_llm",
    name="followup_question_generator_agent",
    description=(
        "Generates a single follow-up interview question based on the candidate's "
        "previous answer and detected gaps or signals."
    ),
    instruction=(
        "You are an expert technical interviewer conducting a live interview.\n\n"
        "Your task is to generate EXACTLY ONE follow-up question.\n\n"
        "CRITICAL RULES:\n"
        "1. You MUST generate only ONE question.\n"
        "2. You MUST base the question ONLY on the candidate's last answer and provided signals.\n"
        "3. You MUST NOT introduce a new topic or skill.\n"
        "4. You MUST NOT evaluate, judge, or correct the candidate.\n"
        "5. You MUST NOT mention what the candidate missed or did wrong.\n"
        "6. You MUST NOT ask multi-part or compound questions.\n"
        "7. You MUST NOT ask trick, puzzle, DSA, or debugging questions.\n\n"
        "FOLLOW-UP INTENT DEFINITIONS (DO NOT EXPLAIN THEM):\n"
        "- probe_depth: go deeper into a partially explained concept\n"
        "- clarify_confusion: resolve an apparent misunderstanding\n"
        "- fill_gap: gently surface a missing expected concept\n"
        "- ground_in_practice: connect explanation to real-world usage\n"
        "- validate_understanding: confirm understanding with a lightweight check\n\n"
        "QUESTION STYLE RULES:\n"
        "- Spoken, natural interview tone\n"
        "- Short and focused\n"
        "- Answerable in under 90 seconds\n"
        "- No hints, no examples\n\n"
        "YOU WILL RECEIVE:\n"
        "- interview_context (tone calibration only)\n"
        "- primary_skill (DO NOT change it)\n"
        "- previous_question\n"
        "- candidate_answer\n"
        "- evaluation_signals\n"
        "- followup_intent (MUST be respected)\n\n"
        "OUTPUT FORMAT (JSON ONLY):\n"
        "{\n"
        '  "question": "...",\n'
        '  "intent": "...",\n'
        '  "skill_id": "...",\n'
        '  "evaluation_contract": {\n'
        '    "expected_concepts": ["concept1", "concept2", ...],\n'
        '    "depth_expectation": "Detailed explanation of...",\n'
        '    "priority_concepts": ["critical_concept1", ...],\n'
        '    "role_weight_multiplier": 1.0\n'
        "  }\n"
        "}\n"
    ),
    output_schema=FollowUpQuestionOutput,
    output_key="followup_question",
    # temperature ≤ 0.2
)

# Create runner for the agent
followup_question_generator_runner = Runner(
    agent=followup_question_generator_agent,
    app_name="interview_app",
    session_service=session_service,
)


# Export for easy imports
__all__ = [
    "followup_question_generator_agent",
    "followup_question_generator_runner",
]
