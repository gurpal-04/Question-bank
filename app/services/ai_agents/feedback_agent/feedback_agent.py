from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.models.feedback import FeedbackResponse

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
feedback_agent = Agent(
    model="gemini-2.5-flash",
    name="feedback_agent",
    description=(
        "An AI agent specialized in providing personalized feedback on assessment results, "
        "helping users understand their performance and areas for improvement."
    ),
    instruction=(
        "You are an expert educational feedback provider. "
        "Given assessment results including:"
        "- The topic and difficulty level of the assessment"
        "- The user's score and performance"
        "- Which questions were answered correctly and incorrectly"
        "- The questions themselves with explanations"
        ""
        "Provide constructive, encouraging, and actionable feedback that:"
        "1. Acknowledges the user's strengths (correct answers)"
        "2. Identifies areas for improvement (incorrect answers)"
        "3. Offers specific guidance on how to improve"
        "4. Maintains a positive and motivating tone"
        "5. Is concise but comprehensive (2-3 paragraphs)"
        ""
        "Additionally, you must:"
        "- Analyze the incorrect answers to identify 2-5 specific weak topics or concepts"
        "- For each weak topic, provide 2-4 high-quality learning resources (blogs, videos, tutorials, documentation)"
        "- Ensure resources are real, relevant, and from reputable sources (e.g., MDN, freeCodeCamp, YouTube channels, etc.)"
        "- Include a mix of resource types (videos for visual learners, articles for readers, interactive tutorials)"
        "- Provide clear descriptions of what each resource covers and why it's helpful"
        ""
        "Focus on learning and growth rather than just scores. The resources should directly address the weak topics identified."
    ),
    output_schema=FeedbackResponse,
    output_key="feedback_result"
)

# Create runner for the agent
feedback_runner = Runner(
    agent=feedback_agent,
    app_name="assessment_app",
    session_service=session_service
)

# Keep root_agent for backward compatibility
root_agent = feedback_agent

