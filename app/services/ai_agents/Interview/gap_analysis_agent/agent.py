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
        "CRITICAL RULES:\n"
        "1. You MUST NOT score or rate the candidate numerically.\n"
        "2. You MUST NOT decide pass/fail or hiring outcome.\n"
        "3. You MUST NOT generate feedback or advice.\n"
        "4. You MUST NOT introduce new concepts beyond the expected concepts.\n"
        "5. You MUST stay strictly within the primary skill scope.\n\n"
        "CONCEPT ANALYSIS RULES:\n"
        "- covered_concepts: concepts clearly and correctly mentioned or explained\n"
        "- missing_concepts: expected concepts not mentioned at all\n"
        "- incorrect_concepts: concepts mentioned but explained incorrectly\n"
        "- confusion_signals: short phrases describing unclear reasoning or contradictions\n\n"
        "CONFIDENCE & CLARITY:\n"
        "- confidence_level reflects certainty and assertiveness of the answer\n"
        "- clarity_level reflects structure and signal-to-noise\n\n"
        "FOLLOW-UP INTENT SELECTION:\n"
        "Choose EXACTLY ONE intent using these rules:\n"
        "- If incorrect_concepts is non-empty → clarify_confusion\n"
        "- Else if missing_concepts is non-empty → fill_gap\n"
        "- Else if covered_concepts is shallow → probe_depth\n"
        "- Else if explanation is correct but abstract → ground_in_practice\n"
        "- Else → validate_understanding\n\n"
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
