from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.models.questions import QuestionsList

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
generator_agent = Agent(
    model="gemini-2.0-flash",
    name="assessment_generator_agent",
    description=(
        "An AI agent specialized in generating high-quality multiple-choice questions (MCQs) "
        "for technical assessments based on a given topic and difficulty level."
    ),
    instruction=(
        "You are an expert assessment creator for technical skills. "
        "Given a topic (e.g., React, Python, Data Structures) and a difficulty level "
        "(Beginner, Intermediate, or Advanced), generate a JSON list of 10–15 high-quality MCQs."
        "Each question must include:"
        "1. `question`: The question text."
        "2. `options`: A list of 4 possible answers."
        "3. `correct_answer`: The correct option exactly as it appears in `options`."
        "4. `explanation`: A concise explanation (1–2 sentences) of why the correct answer is right."
        "5. `metadata`: Include `topic`, `subtopic` (if identifiable), `difficulty`, and `type='MCQ'`."
        "Output must be a valid JSON array of question objects — no extra text, comments, or markdown. "
        "Ensure clarity, accuracy, and relevance to the requested topic and difficulty level. "
        "Vary the question patterns to cover conceptual, practical, and scenario-based styles."
    ),
    output_schema=QuestionsList,
    output_key="generated_questions"
)

# Create runner for the agent
generator_runner = Runner(
    agent=generator_agent,
    app_name="assessment_app",
    session_service=session_service
)

# Keep root_agent for backward compatibility
root_agent = generator_agent
