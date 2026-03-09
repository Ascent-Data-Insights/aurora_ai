# The Three Rings: Portfolio Assessment Framework

## Overview

Every potential portfolio item is evaluated through three core dimensions — the **Three Rings**. The purpose of each conversation is to assess a project's compatibility across all three rings, building confidence over time through guided dialogue with stakeholders.

## The Three Rings

### 1. Value
**What it measures:** The monetary or time value the project would deliver.

- Revenue impact, cost savings, time reclaimed
- Direct and indirect business value
- Strategic positioning and competitive advantage

### 2. Feasibility
**What it measures:** Can we actually build this?

- Data availability and quality
- Technical complexity and team capability
- Infrastructure, tooling, and integration requirements
- Timeline realism given constraints

### 3. Scalability
**What it measures:** Once we do it once, can we do it again?

- Replicability across business units or departments
- Applicability to other clients or markets
- Generalizability of the solution beyond the initial use case
- Marginal cost of each additional deployment

## Scoring Model

Each ring tracks two dimensions:

| Dimension | Range | Description |
|-----------|-------|-------------|
| **Value** | 0–100 | The assessed score for that ring |
| **Confidence** | 0–100% | How much evidence we have to support that score |

### How scoring works

- Every conversation starts at **0 confidence** across all three rings. Values are undefined until the first relevant signal.
- The LLM **re-evaluates holistically each turn** — it does not do incremental arithmetic per question. Given everything learned so far, it outputs its current best estimate for all six numbers (3 values + 3 confidences).
- Confidence represents statistical-style certainty: "How much do I know vs. how much would I need to know to be confident in this score?"
- Target confidence for a completed assessment is **90%+** across all three rings.

### Visual representation

The three rings fill up over the course of a conversation. The displayed fill level combines value and confidence:

```
displayed_fill = value * (confidence / 100)
```

A project scored at 80 value with only 20% confidence shows a thin sliver. As confidence grows through the conversation, the ring fills to reveal the true score. This creates a natural "filling up" effect as the conversation progresses and the picture becomes clearer.

## Conversation Flow

### Current approach
The system passively updates ring scores as information surfaces during conversation, while also identifying gaps and proactively steering toward uncovered dimensions.

### Future direction
Agentic conversation flows designed in collaboration with C-suite executives will guide the dialogue more deliberately, ensuring all three rings reach high confidence efficiently.

### Example progression

> **Turn 1:** User proposes a complex forecasting model.
> - Value: 60 (confidence: 15%) — forecasting implies clear business value, but unclear how much
> - Feasibility: ? (confidence: 0%) — no information yet
> - Scalability: ? (confidence: 0%) — no information yet
>
> **Turn 2:** User reveals data is scattered and fragmented across the organization.
> - Value: 60 (confidence: 15%) — unchanged
> - Feasibility: 30 (confidence: 25%) — fragmented data is a significant headwind
> - Scalability: ? (confidence: 5%) — fragmented data hints at scalability challenges too
>
> **Turn 3:** User clarifies they have a centralized data team working on consolidation, expected done in Q2.
> - Feasibility: 55 (confidence: 45%) — obstacle has a timeline, feasibility improves
> - ...and so on

## Composite Scoring and Ranking

Projects are ranked by a composite score across all three rings. A project that is strong in all three is ideal, but high in two and medium in one is still viable — as long as this is known ahead of time with high confidence.

The composite scoring formula and weighting strategy are TBD and may be configurable per organization or portfolio context.
