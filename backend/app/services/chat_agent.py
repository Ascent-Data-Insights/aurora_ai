from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.config import settings

provider = AnthropicProvider(api_key=settings.anthropic_api_key)
_default_model: Model = AnthropicModel(settings.model_heavy, provider=provider)

# Tests can swap this to TestModel
chat_model: Model = _default_model

BASE_SYSTEM_PROMPT = """\
You are a strategic intelligence assistant specializing in portfolio strategy. \
You help enterprise leaders evaluate and prioritize initiatives across Value, \
Feasibility, and Scalability dimensions.

Be concise, structured, and actionable. You are having a natural conversation — \
not administering a questionnaire. Weave your questions into the dialogue \
organically. If the user volunteers information about a topic you haven't \
asked about yet, acknowledge it and build on it.

## Current focus:
{phase_guidance}
"""


def build_system_prompt(phase_guidance: str, document_context: str = "") -> str:
    """Build the full system prompt string."""
    system_prompt = BASE_SYSTEM_PROMPT.format(phase_guidance=phase_guidance)
    if document_context:
        system_prompt += f"\n\n## Uploaded documents\n{document_context}"
    return system_prompt


def build_chat_agent(phase_guidance: str, document_context: str = "") -> tuple[Agent, str]:
    """Build a chat agent with phase-aware system prompt.

    Returns the agent and the system prompt string (needed to inject
    into message history for pydantic_ai compatibility).
    """
    system_prompt = build_system_prompt(phase_guidance, document_context)
    agent = Agent(
        chat_model,
        system_prompt=system_prompt,
    )
    return agent, system_prompt
