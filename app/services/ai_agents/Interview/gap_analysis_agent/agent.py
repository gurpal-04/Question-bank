import logging
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.models.gap_analysis import GapAnalysisOutput

logger = logging.getLogger(__name__)


# Initialize session service
session_service = InMemorySessionService()

# Create the agent
gap_analysis_agent = Agent(
    model="gemini-2.5-flash",
    name="gap_analysis_agent",
    description=(
        "Analyzes a candidate's interview answer and identifies knowledge gaps "
        "for follow-up question selection."
    ),
    instruction=(
        "You are an expert technical interviewer analyzing a candidate's response.\n\n"
        "Your task is to extract structured evaluation signals from the answer.\n\n"
        "PART 1: GAP ANALYSIS (Primary Task - Critical)\n"
        "Identify:\n"
        "- covered_concepts\n"
        "- missing_concepts\n"
        "- incorrect_concepts\n"
        "Detect confusion_signals\n"
        "Assess:\n"
        "- confidence_level\n"
        "- clarity_level\n\n"
        "FOLLOW-UP INTENT PRIORITY RULES:\n"
        "- If incorrect_concepts → clarify_confusion\n"
        "- Else if missing_concepts → fill_gap\n"
        "- Else if shallow coverage → probe_depth\n"
        "- Else if abstract → ground_in_practice\n"
        "- Else → validate_understanding\n\n"
        "PART 2: DIMENSION SCORING (Secondary - Analytics Only)\n"
        "Score each dimension 1.0-5.0:\n\n"
        "STRUCTURE\n"
        "- 1.0-2.0: Disorganized\n"
        "- 2.1-3.0: Weak structure\n"
        "- 3.1-4.0: Logical flow\n"
        "- 4.1-5.0: Clear intro → explanation → conclusion\n\n"
        "DEPTH\n"
        "- 1.0-2.0: Surface-level\n"
        "- 2.1-3.0: Partial coverage\n"
        "- 3.1-4.0: Solid depth\n"
        "- 4.1-5.0: Deep internals/mechanisms\n\n"
        "TRADE-OFFS\n"
        "- 1.0-2.0: None mentioned\n"
        "- 2.1-3.0: Minimal\n"
        "- 3.1-4.0: Some trade-offs\n"
        "- 4.1-5.0: Clear pros/cons & use cases\n\n"
        "CLARITY\n"
        "- 1.0-2.0: Very hard to follow\n"
        "- 2.1-3.0: Some issues\n"
        "- 3.1-4.0: Mostly clear\n"
        "- 4.1-5.0: Crystal clear\n\n"
        "PROMPT CONSTRAINTS:\n"
        "- Part 1 is MORE CRITICAL than Part 2\n"
        "- Be consistent across questions\n"
        "- Scores must align with gap analysis signals\n"
        "- Do NOT give feedback or advice\n"
        "- Do NOT decide pass/fail\n"
    ),
    output_schema=GapAnalysisOutput,
    output_key="gap_analysis",
    # temperature ≤ 0.2
)

# Create runner for the agent
gap_analysis_runner = Runner(
    agent=gap_analysis_agent,
    app_name="interview_app",
    session_service=session_service,
)

# Keep root_agent for backward compatibility
root_agent = gap_analysis_agent
