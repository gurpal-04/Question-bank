import json
import logging
from typing import Dict, Any

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.models.interview_context import FirstQuestionInput, FirstQuestionOutput
from app.services.ai_agents.runner_utils import run_agent_with_runner

logger = logging.getLogger(__name__)

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
first_question_generator_agent = Agent(
    model="gemini-2.5-flash",
    name="first_question_generator_agent",
    description=(
        "Generates the FIRST interview question based on a selected skill "
        "and question archetype. This agent is used only once at interview start."
    ),
    instruction=(
        "You are an expert technical interviewer."
        "Your task is to generate the FIRST spoken interview question."
        "CRITICAL RULES:"
        "1. You MUST generate exactly ONE question."
        "2. You MUST NOT generate follow-up questions."
        "3. You MUST NOT evaluate, score, or comment on answers."
        "4. You MUST NOT mention difficulty, scores, or expectations."
        "5. You MUST NOT ask multi-part or compound questions."
        "6. You MUST NOT ask trick, puzzle, or DSA-style questions."
        "7. You MUST NOT ask debugging or error-finding questions."

        "QUESTION STYLE RULES:"
        "- Spoken, conversational interview tone"
        "- Answerable in under 2 minutes"
        "- Clear and unambiguous"
        "- No jargon overload"
        "- No artificial constraints"

        "YOU WILL RECEIVE:"
        "- interview_context (for calibration only)"
        "- selected_skill (the ONLY skill to target)"
        "- question_archetype (how to frame the question)"
        "- experience_level"

        "ARCHETYPE DEFINITIONS (DO NOT EXPLAIN THEM):"
        "- Core Concept Explanation: Ask the candidate to explain a fundamental concept"
        "- Concept + Real-World Usage: Ask to explain + how it is used in practice"
        "- Comparison / Trade-off: Ask to compare two related concepts"
        "- Internals (High level): Ask about how something works internally, at a high level"
        "- Pseudo-Implementation: Ask how they would approach implementing something (no code)"

        "OUTPUT REQUIREMENTS:"
        "- Generate ONE question only"
        "- Target ONLY the selected skill"
        "- Match the provided archetype strictly"
        "- Do NOT include examples or hints"
        "OUTPUT FORMAT (JSON ONLY):"

        "{"
        '  "question": "...",'
        '  "archetype": "...",'
        '  "skill_id": "..."'
        "}"
    ),
    output_schema=FirstQuestionOutput,
    output_key="first_question",
)

# Create runner for the agent
first_question_generator_runner = Runner(
    agent=first_question_generator_agent,
    app_name="interview_app",
    session_service=session_service,
)

# Export for easy imports
__all__ = ["first_question_generator_agent", "first_question_generator_runner", "generate_first_question"]

