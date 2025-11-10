from google.adk.agents.llm_agent import Agent
from google.adk.schemas import StructuredSchema, Field

QuestionSchema = StructuredSchema(
    name="QuestionSchema",
    description="Schema for a generated question with its possible answers and the correct one.",
    fields=[
        Field(
            name="question",
            type="string",
            description="The main question text."
        ),
        Field(
            name="options",
            type="list[string]",
            description="List of multiple-choice options."
        ),
        Field(
            name="correct_answer",
            type="string",
            description="The correct answer to the question."
        ),
        Field(
            name="explanation",
            type="string",
            description="Short explanation or reasoning behind the correct answer."
        ),
        Field(
            name="difficulty",
            type="string",
            description="Difficulty level of the question (easy, medium, hard)."
        ),
    ]
)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="assessment_generator_agent",
    description=(
        "An AI agent specialized in generating high-quality multiple-choice questions (MCQs) "
        "for technical assessments based on a given topic and difficulty level."
    ),
    instruction=(
        "You are an expert assessment creator for technical skills. "
        "Given a topic (e.g., React, Python, Data Structures) and a difficulty level "
        "(Beginner, Intermediate, or Advanced), generate a JSON list of 10–15 high-quality MCQs.\n\n"
        "Each question must include:\n"
        "1. `question`: The question text.\n"
        "2. `options`: A list of 4 possible answers.\n"
        "3. `correct_answer`: The correct option exactly as it appears in `options`.\n"
        "4. `explanation`: A concise explanation (1–2 sentences) of why the correct answer is right.\n"
        "5. `metadata`: Include `topic`, `subtopic` (if identifiable), `difficulty`, and `type='MCQ'`.\n\n"
        "Output must be a valid JSON array of question objects — no extra text, comments, or markdown. "
        "Ensure clarity, accuracy, and relevance to the requested topic and difficulty level. "
        "Vary the question patterns to cover conceptual, practical, and scenario-based styles."
    ),
     output_schema=QuestionSchema,
)
