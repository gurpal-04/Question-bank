import os
import json
import logging
import asyncio
from typing import Any, List, Optional
from pydantic import BaseModel
import litellm

from litellm import Router

logger = logging.getLogger(__name__)

# Initialize LiteLLM Router
# Note: We use model_name aliases to allow agents to pick a "tier"
llm_router = Router(
    model_list=[
        # 🔹 PRIMARY MODEL (cheap & fast)
        {
            "model_name": "primary_llm",
            "litellm_params": {
                "model": "groq/llama-3.1-8b-instant",
                "api_key": os.environ.get("GROQ_API_KEY"),
                "timeout": 10,
                "max_tokens": 800,
                "temperature": 0.4,
            },
        },
        # 🔹 HIGH-QUALITY MODEL (use sparingly)
        {
            "model_name": "quality_llm",
            "litellm_params": {
                "model": "groq/llama-3.3-70b-versatile",
                "api_key": os.environ.get("GROQ_API_KEY"),
                "timeout": 15,
                "max_tokens": 1200,
                "temperature": 0.3,
            },
        },
        # 🔹 EMERGENCY FALLBACK (optional)
        {
            "model_name": "fallback_llm",
            "litellm_params": {
                "model": "gemini/gemini-2.5-flash",
                "api_key": os.environ.get(
                    "GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY")
                ),
                "timeout": 15,
                "max_tokens": 800,
                "temperature": 0.4,
            },
        },
    ],
    # 🔁 fallback logic
    fallbacks=[
        {"primary_llm": ["quality_llm", "fallback_llm"]},
        {"quality_llm": ["primary_llm", "fallback_llm"]},
    ],
)


class ContentPart:
    def __init__(self, text: str):
        self.text = text


class Content:
    def __init__(self, role: str, parts: List[ContentPart]):
        self.role = role
        self.parts = parts


class AgentEvent:
    def __init__(self, content: Optional[Content] = None, is_final: bool = False):
        self.content = content
        self.is_final = is_final

    def is_final_response(self) -> bool:
        return self.is_final


class LiteLLMAgent:
    def __init__(
        self,
        model: str,
        name: str,
        description: str,
        instruction: str,
        output_schema: Optional[Any] = None,
        output_key: Optional[str] = None,
    ):
        # The model here can now be an alias like "primary_llm"
        self.model = model
        self.name = name
        self.description = description
        self.instruction = instruction
        self.output_schema = output_schema
        self.output_key = output_key


class LiteLLMSession:
    def __init__(self):
        self.state = {}
        self.messages = []


class LiteLLMInMemorySessionService:
    def __init__(self):
        self.sessions = {}

    async def create_session(self, app_name: str, user_id: str, session_id: str):
        key = f"{app_name}:{user_id}:{session_id}"
        self.sessions[key] = LiteLLMSession()

    async def get_session(self, app_name: str, user_id: str, session_id: str):
        key = f"{app_name}:{user_id}:{session_id}"
        return self.sessions.get(key)


class LiteLLMRunner:
    def __init__(
        self,
        agent: LiteLLMAgent,
        app_name: str,
        session_service: LiteLLMInMemorySessionService,
    ):
        self.agent = agent
        self.app_name = app_name
        self.session_service = session_service

    async def run_async(self, user_id: str, session_id: str, new_message: Any):
        session = await self.session_service.get_session(
            self.app_name, user_id, session_id
        )
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Extract text from new_message
        prompt_text = ""
        if hasattr(new_message, "parts") and new_message.parts:
            prompt_text = new_message.parts[0].text
        elif isinstance(new_message, str):
            prompt_text = new_message

        # Build messages for litellm
        messages = [
            {"role": "system", "content": self.agent.instruction},
            {"role": "user", "content": prompt_text},
        ]

        logger.info(
            f"LiteLLMRunner: Starting generation for agent '{self.agent.name}' using model '{self.agent.model}'"
        )
        logger.debug(f"LiteLLMRunner: System Message: {messages[0]['content']}")
        logger.debug(f"LiteLLMRunner: User Prompt: {prompt_text}")

        # Determine response format
        response_format = None
        if self.agent.output_schema:
            schema_json = ""
            if hasattr(self.agent.output_schema, "model_json_schema"):
                schema_json = json.dumps(
                    self.agent.output_schema.model_json_schema(), indent=2
                )

            # Check if using a model name that likely supports json_object (Groq or aliases)
            if "groq/" in self.agent.model or "_llm" in self.agent.model:
                response_format = {"type": "json_object"}
                # Add instruction to ensure JSON output
                if "JSON" not in messages[0]["content"]:
                    messages[0][
                        "content"
                    ] += f"\nReturn your response as a valid JSON object matching this schema:\n{schema_json}"
            else:
                response_format = self.agent.output_schema

        logger.debug(f"LiteLLMRunner: Response Format: {response_format}")

        try:
            # Call litellm router
            response = await llm_router.acompletion(
                model=self.agent.model,
                messages=messages,
                response_format=response_format,
            )

            final_text = response.choices[0].message.content
            logger.info(
                f"LiteLLMRunner: Received response (length: {len(final_text)}) from model '{response.model}'"
            )
            logger.debug(f"LiteLLMRunner: Raw LLM Response: {final_text}")

            # Update session state if output_key is present
            if self.agent.output_key:
                session.state[self.agent.output_key] = final_text

            # Yield an event that mimics google-adk
            content_part = ContentPart(text=final_text)
            content = Content(role="assistant", parts=[content_part])
            yield AgentEvent(content=content, is_final=True)

        except Exception as e:
            logger.error(f"Error in LiteLLMRunner: {e}")
            raise
