"""Extractor agent — extracts structured information from conversation.

Runs after each turn (on the light model) to update the full SessionState
including organization info, initiative details, assessment fields, and
ring scores. Replaces the previous standalone scoring agent.
"""

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.config import settings
from app.models.graph import SessionState

provider = AnthropicProvider(api_key=settings.anthropic_api_key)
model = AnthropicModel(settings.model_light, provider=provider)

EXTRACTOR_SYSTEM_PROMPT = """\
You are an extraction agent for a strategic portfolio assessment platform.

Given a conversation between a user and a strategic assistant, extract ALL \
relevant information into a structured state object. You receive the current \
state and must output the updated state.

## Extraction rules:

1. **Preserve existing values** — only overwrite a field if the conversation \
clearly corrects or updates it.
2. **Extract opportunistically** — if the user mentions their company name in \
passing while discussing something else, capture it.
3. **Use the user's own words** — for text fields, paraphrase concisely but \
faithfully. Don't invent information that wasn't stated or strongly implied.
4. **Leave fields as null** if no relevant information has been provided.

## Scoring rules (for the `scores` field):

For each of the three rings (Value, Feasibility, Scalability), output:
- **value** (0-100): Your best estimate of the score based on all evidence.
- **confidence** (0-100): How much evidence you have. This is statistical-style \
certainty — "how much do I know vs. how much would I need to know?"

Scoring guidelines:
- Re-evaluate holistically each turn. Do NOT do incremental arithmetic.
- Confidence starts at 0 and grows as relevant information surfaces.
- A dimension with no information should stay at 0 confidence with value 0.
- Be conservative with confidence — 90%+ means very thorough information.
- In a normal conversational turn, small increments (5-15%) are typical.
- However, when uploaded documents or the assistant response contain substantial \
detail about a dimension (financials, timelines, technical details, growth \
projections, etc.), confidence and value should reflect ALL of that evidence. \
A document that thoroughly covers a dimension can justify 40-70% confidence in \
a single turn.
- Assessment field completeness should correlate with confidence.
- Always score ALL three dimensions based on ALL available evidence — do not \
focus on only one dimension per turn.
"""

extractor_agent = Agent(
    model,
    system_prompt=EXTRACTOR_SYSTEM_PROMPT,
    output_type=SessionState,
)
