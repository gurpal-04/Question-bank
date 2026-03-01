from app.services.ai_agents.litellm_shim import (
    LiteLLMAgent as Agent,
    LiteLLMRunner as Runner,
    LiteLLMInMemorySessionService as InMemorySessionService,
)
from app.models.resume import ResumeProfile

# Initialize session service
session_service = InMemorySessionService()

# Create the agent
resume_parser_agent = Agent(
    model="compound_llm",
    name="resume_parser_agent",
    description=(
        "An AI agent specialized in extracting structured pedagogical information "
        "and professional highlights from raw resume text."
    ),
    instruction=(
        "You are an expert technical recruiter and AI parser. "
        "Given the raw text of a candidate's resume, extract and structure the information into the requested JSON schema. "
        "Guidelines:"
        "1. `full_name`, `email`, `phone`, `location`: Extract if clearly present."
        "2. `summary`: Provide a concise (2-3 sentences) professional summary highlighting the candidate's core strengths."
        "3. `skills`: List technical skills, frameworks, and tools. Be specific (e.g., 'React', 'Python', 'Docker', 'AWS')."
        "4. `experience_years`: Estimate total years of professional experience as a decimal number (e.g., 3.5 years). Be realistic based on graduation dates and work experience."
        "5. `top_projects`: Identify the most impressive projects. For each, provide a name, a high-impact description of what was done, and technologies used."
        "6. `education`: List degrees and the name of the institution."
        "Your output MUST be a valid JSON object matching the `ResumeProfile` schema."
    ),
    output_schema=ResumeProfile,
    output_key="parsed_resume_profile",
)

# Create runner for the agent
resume_parser_runner = Runner(
    agent=resume_parser_agent,
    app_name="assessment_app",
    session_service=session_service,
)
