from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
summary_agent = Agent(
    model="gemini-2.5-flash",
    name="resource_summary_agent",
    description=(
        "An AI agent specialized in generating concise summaries for learning resources "
        "based on their title, type, URL, and tags."
    ),
    instruction=(
        "You generate a concise 2–3 sentence summary of a learning resource that captures its key "
        "topics and what someone will learn from it.\n\n"
        "You will receive a prompt describing the resource (title, type, URL, tags). "
        "Return ONLY the summary text, with no extra commentary, metadata, or JSON."
    ),
)

# Create runner for the agent
summary_runner = Runner(
    agent=summary_agent, app_name="resource_app", session_service=session_service
)

# Keep root_agent for backward compatibility / simple imports
root_agent = summary_agent


