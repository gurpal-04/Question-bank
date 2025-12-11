from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.models.normalization import NormalizationResponse

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
topic_normalizer_agent = Agent(
    model="gemini-2.0-flash",
    name="topic_normalizer_agent",
    description=(
        "An AI agent specialized in normalizing messy topic names into standardized "
        "search queries for vector database retrieval."
    ),
    instruction=(
        "You are a topic normalizer. Your goal is to convert a list of raw, potentially messy "
        "topic names into clean, standardized search queries.\n\n"
        "Rules for normalization:\n"
        "1. Expand abbreviations (e.g., 'js' -> 'javascript', 'py' -> 'python')\n"
        "2. Remove filler words (e.g., 'intro to', 'basics of', 'understanding', 'how to use')\n"
        "3. Use lowercase for all terms\n"
        "4. Keep it concise (2-4 words max)\n"
        "5. Focus on the core technical concept\n\n"
        "Examples:\n"
        "- 'intro to js events' -> 'javascript events'\n"
        "- 'python basics' -> 'python fundamentals'\n"
        "- 'understanding react hooks' -> 'react hooks'\n"
        "- 'how to use loops in python' -> 'python loops'\n"
        "- 'async await javascript' -> 'javascript async await'\n\n"
        "Input will be a list of topics. Output must be a JSON object containing the list of "
        "normalized topics, where each item has the 'original' topic and the 'normalized' version."
    ),
    output_schema=NormalizationResponse,
    output_key="normalization_result",
)

# Create runner for the agent
topic_normalizer_runner = Runner(
    agent=topic_normalizer_agent,
    app_name="assessment_app",
    session_service=session_service,
)
