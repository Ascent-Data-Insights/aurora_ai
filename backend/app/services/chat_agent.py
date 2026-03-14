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


def build_chat_agent(phase_guidance: str, document_context: str = "") -> Agent:
    """Build a chat agent with phase-aware system prompt."""
    system_prompt = BASE_SYSTEM_PROMPT.format(phase_guidance=phase_guidance)
    if document_context:
        system_prompt += f"\n\n## Uploaded documents\n{document_context}"
    return Agent(
        chat_model,
        system_prompt=system_prompt,
    )
