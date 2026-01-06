import json
import logging
from typing import Dict, Any

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.models.interview_context import FollowUpQuestionInput, FollowUpQuestionOutput
from app.services.ai_agents.runner_utils import run_agent_with_runner

logger = logging.getLogger(__name__)

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
followup_question_generator_agent = Agent(
    model="gemini-2.5-flash",
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


async def generate_followup_question(
    interview_context: Dict[str, Any],
    primary_skill: str,
    previous_question: str,
    candidate_answer: str,
    evaluation_signals: Dict[str, Any],
    followup_intent: str,
) -> Dict[str, Any]:
    """
    Generate a follow-up question.
    """
    # Validate input
    input_data = FollowUpQuestionInput(
        interview_context=interview_context,
        primary_skill=primary_skill,
        previous_question=previous_question,
        candidate_answer=candidate_answer,
        evaluation_signals=evaluation_signals,
        followup_intent=followup_intent,
    )

    # Construct prompt
    prompt = json.dumps(input_data.model_dump(), indent=2)

    try:
        result = await run_agent_with_runner(
            runner=followup_question_generator_runner,
            agent=followup_question_generator_agent,
            prompt=prompt,
        )

        if isinstance(result, dict):
            output = FollowUpQuestionOutput(**result)
        else:
            try:
                parsed = json.loads(result) if isinstance(result, str) else result
                output = FollowUpQuestionOutput(**parsed)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse agent output: {e}")
                raise ValueError(f"Agent returned invalid output format: {result}")

        return output.model_dump()

    except Exception as e:
        logger.error(f"Error generating follow-up question: {e}", exc_info=True)
        raise


# Export for easy imports
__all__ = [
    "followup_question_generator_agent",
    "followup_question_generator_runner",
    "generate_followup_question",
]
