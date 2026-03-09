"""Phase determination logic for the guided assessment workflow.

Examines the current SessionState and determines which conversation phase
the agent should be in, plus guidance text for the chat agent's system prompt.
"""

from __future__ import annotations

from enum import Enum

from app.models.graph import SessionState


class Phase(str, Enum):
    CONTEXT_GATHERING = "context_gathering"
    INITIATIVE_FRAMING = "initiative_framing"
    VALUE_DEEP_DIVE = "value_deep_dive"
    FEASIBILITY_DEEP_DIVE = "feasibility_deep_dive"
    SCALABILITY_DEEP_DIVE = "scalability_deep_dive"
    SYNTHESIS = "synthesis"


# Confidence threshold to consider a ring "sufficiently explored"
_RING_EXPLORED = 40
# Confidence threshold to move to synthesis
_RING_READY = 70


PHASE_GUIDANCE: dict[Phase, str] = {
    Phase.CONTEXT_GATHERING: (
        "You need to understand the user's organization and role. Learn about "
        "their company name, industry, size, and what they do. Be natural and "
        "conversational — don't interrogate. If they volunteer initiative details "
        "early, that's fine — absorb it."
    ),
    Phase.INITIATIVE_FRAMING: (
        "You need to understand what initiative the user wants to evaluate. "
        "Get a clear name and description for the project. What problem does it "
        "solve? What does success look like?"
    ),
    Phase.VALUE_DEEP_DIVE: (
        "Focus on understanding the value this initiative would deliver. "
        "Explore: revenue impact, cost savings, time reclaimed, and strategic "
        "positioning. Ask about quantifiable outcomes where possible."
    ),
    Phase.FEASIBILITY_DEEP_DIVE: (
        "Focus on understanding whether this initiative is feasible. Explore: "
        "technical complexity, team capability, infrastructure readiness, "
        "timeline, and key dependencies or blockers."
    ),
    Phase.SCALABILITY_DEEP_DIVE: (
        "Focus on understanding scalability. Can this be replicated across "
        "business units or markets? What's the marginal cost of additional "
        "deployments? Is the organization ready for change management at scale?"
    ),
    Phase.SYNTHESIS: (
        "You have strong information across all dimensions. Summarize your "
        "findings, highlight key risks and opportunities, and help the user "
        "understand the overall assessment. Offer to dive deeper into any area."
    ),
}


def determine_phase(state: SessionState) -> Phase:
    """Determine the current conversation phase based on state completeness."""
    org = state.organization
    if not any([org.name, org.industry, org.size]):
        return Phase.CONTEXT_GATHERING

    init = state.initiative
    if not any([init.name, init.description]):
        return Phase.INITIATIVE_FRAMING

    # Check ring confidences — dive into the least confident ring
    scores = state.scores
    confidences = {
        Phase.VALUE_DEEP_DIVE: scores.value.confidence,
        Phase.FEASIBILITY_DEEP_DIVE: scores.feasibility.confidence,
        Phase.SCALABILITY_DEEP_DIVE: scores.scalability.confidence,
    }

    # If any ring is below the exploration threshold, prioritize it
    for phase, conf in sorted(confidences.items(), key=lambda x: x[1]):
        if conf < _RING_EXPLORED:
            return phase

    # All rings have some coverage — go deeper on the weakest
    min_conf = min(confidences.values())
    if min_conf < _RING_READY:
        for phase, conf in confidences.items():
            if conf == min_conf:
                return phase

    return Phase.SYNTHESIS


def get_phase_guidance(state: SessionState) -> tuple[Phase, str]:
    """Return the current phase and its guidance text for the chat agent."""
    phase = determine_phase(state)
    guidance = PHASE_GUIDANCE[phase]

    # Append info about what we already know so the agent doesn't re-ask
    known_parts: list[str] = []
    org = state.organization
    if org.name:
        known_parts.append(f"Organization: {org.name}")
    if org.industry:
        known_parts.append(f"Industry: {org.industry}")
    if org.size:
        known_parts.append(f"Size: {org.size}")
    if state.initiative.name:
        known_parts.append(f"Initiative: {state.initiative.name}")

    if known_parts:
        guidance += "\n\nYou already know:\n" + "\n".join(
            f"- {p}" for p in known_parts
        )

    return phase, guidance
