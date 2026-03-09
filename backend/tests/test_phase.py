from app.models.graph import (
    InitiativeInfo,
    OrganizationInfo,
    SessionState,
)
from app.models.scores import DimensionScore, RingScores
from app.services.phase import Phase, determine_phase, get_phase_guidance


def test_empty_state_starts_with_context_gathering():
    state = SessionState()
    assert determine_phase(state) == Phase.CONTEXT_GATHERING


def test_org_info_moves_to_initiative_framing():
    state = SessionState(
        organization=OrganizationInfo(name="Acme Corp", industry="SaaS", size="200")
    )
    assert determine_phase(state) == Phase.INITIATIVE_FRAMING


def test_org_and_initiative_moves_to_value_deep_dive():
    state = SessionState(
        organization=OrganizationInfo(name="Acme Corp", industry="SaaS", size="200"),
        initiative=InitiativeInfo(name="CRM Migration", description="Move to Salesforce"),
    )
    assert determine_phase(state) == Phase.VALUE_DEEP_DIVE


def test_high_confidence_reaches_synthesis():
    state = SessionState(
        organization=OrganizationInfo(name="Acme Corp", industry="SaaS", size="200"),
        initiative=InitiativeInfo(name="CRM Migration", description="Move to Salesforce"),
        scores=RingScores(
            value=DimensionScore(value=80, confidence=75),
            feasibility=DimensionScore(value=60, confidence=70),
            scalability=DimensionScore(value=70, confidence=72),
        ),
    )
    assert determine_phase(state) == Phase.SYNTHESIS


def test_weakest_ring_gets_priority():
    state = SessionState(
        organization=OrganizationInfo(name="Acme Corp", industry="SaaS", size="200"),
        initiative=InitiativeInfo(name="CRM Migration", description="Move to Salesforce"),
        scores=RingScores(
            value=DimensionScore(value=80, confidence=60),
            feasibility=DimensionScore(value=60, confidence=20),
            scalability=DimensionScore(value=70, confidence=50),
        ),
    )
    assert determine_phase(state) == Phase.FEASIBILITY_DEEP_DIVE


def test_guidance_includes_known_info():
    state = SessionState(
        organization=OrganizationInfo(name="Acme Corp", industry="SaaS"),
        initiative=InitiativeInfo(name="CRM Migration"),
    )
    _phase, guidance = get_phase_guidance(state)
    assert "Acme Corp" in guidance
    assert "SaaS" in guidance
    assert "CRM Migration" in guidance
