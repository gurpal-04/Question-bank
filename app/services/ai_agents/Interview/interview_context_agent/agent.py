"""
InterviewContextAgent

Generates a stable interview context used by all downstream agents.
This agent runs ONCE at interview start and does NOT evaluate answers or score anything.

The agent takes interview configuration (role, experience, difficulty)
and produces a consistent context that downstream agents can rely on.

Note: evaluation_bar is handled separately outside the agent and added to the final output.
"""

import json
import logging
from typing import Dict, Any

from app.services.ai_agents.litellm_shim import (
    LiteLLMAgent as Agent,
    LiteLLMRunner as Runner,
    LiteLLMInMemorySessionService as InMemorySessionService,
)

from app.models.interview_context import InterviewContextInput, InterviewContextOutput
from app.services.ai_agents.runner_utils import run_agent_with_runner

logger = logging.getLogger(__name__)

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
interview_context_agent = Agent(
    model="primary_llm",
    name="interview_context_agent",
    description=(
        "An AI agent that generates stable interview context based on role, experience level, "
        "and difficulty. This context is used by all downstream agents in the interview process. "
        "The agent runs once at interview start and does not evaluate or score answers."
    ),
    instruction=(
        "You are an expert interviewer preparing context for a technical interview. "
        "Your role is to generate a stable, consistent interview context that will be used "
        "by all downstream agents throughout the interview process.\n\n"
        
        "CRITICAL RULES:\n"
        "1. You MUST NOT generate interview questions.\n"
        "2. You MUST NOT decide or modify difficulty levels.\n"
        "3. You MUST NOT mention 'scoring', 'rubrics', 'points', or numerical evaluation criteria.\n"
        "4. You MUST NOT reference 'topics' explicitly in your output.\n\n"
        
        "OUTPUT REQUIREMENTS:\n\n"
        
        "1. role_expectations (string):\n"
        "   - Write in interviewer language (what an interviewer expects from a candidate).\n"
        "   - Describe skills, knowledge, and behaviors expected at this level.\n"
        "   - Be specific to the role and experience range.\n"
        "   - Do NOT mention scores, numbers, rubrics, or points.\n"
        "   - Keep it professional and clear (2-4 sentences).\n\n"
        
        "2. expected_concepts (list of strings):\n"
        "   - Generate 6-10 core technical concepts.\n"
        "   - Each item must be a NOUN or SHORT NOUN PHRASE only.\n"
        "   - NO verbs, NO explanations, NO sentences.\n"
        "   - Examples of GOOD concepts: 'React hooks', 'Database indexing', 'API design patterns', 'State management'\n"
        "   - Examples of BAD concepts: 'Understanding React hooks', 'How to index databases', 'The candidate should know API design'\n"
        "   - Focus on concepts a strong answer would naturally touch.\n"
        "   - Do NOT add optional concepts 'just in case' - be precise.\n\n"
        
        "DETERMINISM:\n"
        "- Be consistent and deterministic in your output.\n"
        "- Avoid creative phrasing or optional additions.\n"
        "- Focus on core, essential concepts only.\n\n"
        
        "INPUT FORMAT:\n"
        "You will receive a JSON object with:\n"
        "- role: The job role (e.g., 'Frontend Engineer')\n"
        "- experience_range: Experience level (e.g., '0-3 years')\n"
        "- difficulty: 'Easy', 'Medium', or 'Hard'\n\n"
        
        "OUTPUT FORMAT:\n"
        "Return a JSON object with:\n"
        "- role_expectations: string\n"
        "- expected_concepts: array of strings (6-10 items)\n"
    ),
    output_schema=InterviewContextOutput,
    output_key="interview_context",
    # Note: Temperature should be set to ≤ 0.2 for determinism if supported by the Agent API
)

# Create runner for the agent
interview_context_runner = Runner(
    agent=interview_context_agent,
    app_name="interview_app",
    session_service=session_service,
)

# Export for easy imports
__all__ = ["interview_context_agent", "interview_context_runner", "generate_interview_context"]


async def generate_interview_context(
    role: str,
    experience_range: str,
    difficulty: str,
) -> Dict[str, Any]:
    """
    Generate interview context using the InterviewContextAgent.
    
    This is a convenience function that validates input, runs the agent, and returns
    the structured output. Use this for easy integration into services.
    
    Args:
        role: The job role being interviewed for (e.g., "Frontend Engineer")
        experience_range: The candidate's experience level (e.g., "0-3 years")
        difficulty: The difficulty level ("Easy", "Medium", or "Hard")
    
    Returns:
        Dict containing:
            - role_expectations: string
            - expected_concepts: list of strings (6-10 items)
    
    Raises:
        ValidationError: If input validation fails
        ValueError: If agent execution fails or output is invalid
    """
    # Validate input using Pydantic model (evaluation_bar is handled separately)
    input_data = InterviewContextInput(
        role=role,
        experience_range=experience_range,
        difficulty=difficulty,
    )
    
    # Construct prompt as JSON for the agent (without evaluation_bar)
    prompt = json.dumps({
        "role": input_data.role,
        "experience_range": input_data.experience_range,
        "difficulty": input_data.difficulty,
    }, indent=2)
    
    # Run the agent
    try:
        result = await run_agent_with_runner(
            runner=interview_context_runner,
            agent=interview_context_agent,
            prompt=prompt,
        )
        
        # Validate output using Pydantic model
        if isinstance(result, dict):
            output = InterviewContextOutput(**result)
        else:
            # If result is a string, try to parse it as JSON
            try:
                parsed = json.loads(result) if isinstance(result, str) else result
                output = InterviewContextOutput(**parsed)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse agent output: {e}")
                raise ValueError(f"Agent returned invalid output format: {result}")
        
        return output.model_dump()
        
    except Exception as e:
        logger.error(f"Error generating interview context: {e}")
        raise

