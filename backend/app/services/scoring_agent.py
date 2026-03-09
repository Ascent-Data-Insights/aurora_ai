from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.config import settings
from app.models.scores import RingScores

provider = AnthropicProvider(api_key=settings.api_key)
model = AnthropicModel(settings.model_light, provider=provider)

SCORING_SYSTEM_PROMPT = """\
You are a scoring agent for a portfolio assessment framework called "The Three Rings."

You evaluate projects across three dimensions:

1. **Value** (0-100): The monetary or time value the project would deliver — revenue impact, \
cost savings, time reclaimed, strategic positioning.

2. **Feasibility** (0-100): Can we actually build this? — data availability, technical complexity, \
team capability, infrastructure, timeline realism.

3. **Scalability** (0-100): Once we do it once, can we do it again? — replicability across \
business units, applicability to other clients/markets, generalizability, marginal cost of \
additional deployments.

For each dimension, you output two numbers:
- **value**: Your best estimate of the score (0-100)
- **confidence**: How much evidence you have to support that score (0-100%). This represents \
statistical-style certainty — "how much do I know vs. how much would I need to know?"

### Rules:
- Re-evaluate holistically each turn. Do NOT do incremental arithmetic.
- Given everything learned so far, output your current best estimate for all six numbers.
- Confidence starts at 0 and grows as more relevant information surfaces.
- A dimension with no information should stay at 0 confidence with value 0.
- Be conservative with confidence — 90%+ means you have very thorough information.
- Small increments (5-15%) per turn are typical unless the user provides very detailed info.
- Value scores should reflect the actual assessment, not be inflated.
"""

scoring_agent = Agent(
    model,
    system_prompt=SCORING_SYSTEM_PROMPT,
    output_type=RingScores,
)
