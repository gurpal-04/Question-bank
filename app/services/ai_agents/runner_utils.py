import uuid
import logging
from typing import Any

from google.genai import types

logger = logging.getLogger(__name__)


async def run_agent_with_runner(runner, agent, prompt: str) -> Any:
    """
    Helper to run an ADK agent using a Runner.

    This is a backend-utility version of the logic used in AssessmentService.run_agent,
    without any FastAPI / HTTPException coupling so it can be reused from services.
    """
    # Generate unique session ID for this request
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    user_id = "agent_user"

    # Create session before running
    await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )

    # Create user message
    # For LiteLLM shim, we can pass a string or a simplified object
    # For Google ADK, it expects types.Content
    try:
        from google.genai import types

        user_msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    except ImportError:
        user_msg = prompt

    final_text = None

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_msg
    ):
        if event.is_final_response():
            if hasattr(event, "content") and event.content and event.content.parts:
                final_text = event.content.parts[0].text

    # If agent has output_key, try to get structured output from session state
    if hasattr(agent, "output_key") and agent.output_key:
        try:
            current_session = await runner.session_service.get_session(
                app_name=runner.app_name, user_id=user_id, session_id=session_id
            )
            if current_session and current_session.state:
                stored_output = current_session.state.get(agent.output_key)
                if stored_output:
                    # Try to parse as JSON (output_schema returns JSON string)
                    try:
                        import json

                        return json.loads(stored_output)
                    except Exception:
                        return stored_output
        except Exception as e:
            logger.warning(f"Could not get stored output from session: {e}")

    return final_text
