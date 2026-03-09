from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.config import settings

provider = AnthropicProvider(api_key=settings.api_key)
model = AnthropicModel(settings.model_heavy, provider=provider)

chat_agent = Agent(
    model,
    system_prompt=(
        "You are a strategic intelligence assistant specializing in portfolio strategy. "
        "You help enterprise leaders evaluate and prioritize initiatives across Value, "
        "Feasibility, and Scalability dimensions. Be concise, structured, and actionable."
    ),
)
