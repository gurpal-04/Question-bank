import json
import logging
from typing import Dict, Any

from app.models.interview_context import FirstQuestionInput, FirstQuestionOutput
from app.services.ai_agents.runner_utils import run_agent_with_runner
from app.services.ai_agents.Interview.first_question_generator.agent import (
    first_question_generator_agent,
    first_question_generator_runner,
)

logger = logging.getLogger(__name__)


async def generate_first_question(
    interview_context: Dict[str, Any],
    selected_skill: str,
    question_archetype: str,
    experience_level: str,
) -> Dict[str, Any]:
    """
    Generate the first interview question using FirstQuestionGeneratorAgent.
    This is a convenience function that validates input, runs the agent, and returns
    the structured output. Use this for easy integration into services.
    Args:
        interview_context: The interview context dict (from InterviewContextAgent)
        selected_skill: The skill label/name to target (e.g., "JavaScript Fundamentals")
        question_archetype: The archetype label (e.g., "Core Concept Explanation")
        experience_level: The candidate's experience level (e.g., "0-3 years")
    Returns:
        Dict containing:
            - question: string
            - archetype: string
            - skill_id: string
    Raises:
        ValidationError: If input validation fails
        ValueError: If agent execution fails or output is invalid
    """
    # Validate input using Pydantic model
    input_data = FirstQuestionInput(
        interview_context=interview_context,
        selected_skill=selected_skill,
        question_archetype=question_archetype,
        experience_level=experience_level,
    )
    # Construct prompt as JSON for the agent
    prompt = json.dumps({
        "interview_context": input_data.interview_context,
        "selected_skill": input_data.selected_skill,
        "question_archetype": input_data.question_archetype,
        "experience_level": input_data.experience_level,
    }, indent=2)
    # Run the agent
    try:
        result = await run_agent_with_runner(
            runner=first_question_generator_runner,
            agent=first_question_generator_agent,
            prompt=prompt,
        )
        # Validate output using Pydantic model
        if isinstance(result, dict):
            output = FirstQuestionOutput(**result)
        else:
            # If result is a string, try to parse it as JSON
            try:
                parsed = json.loads(result) if isinstance(result, str) else result
                output = FirstQuestionOutput(**parsed)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse agent output: {e}")
                raise ValueError(f"Agent returned invalid output format: {result}")
        return output.model_dump()
    except Exception as e:
        logger.error(f"Error generating first question: {e}")
        raise

