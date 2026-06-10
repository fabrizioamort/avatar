---
title: Vibe Specifying
category: ideas
tags:
  - vibe-specifying
  - specifications
  - coding-agents
  - enterprise
priority: 0
updated: 2026-06-02
---

# Vibe Specifying

## The Idea

Vibe Specifying is an original workflow I use for enterprise AI projects. The idea is to use an LLM to translate messy business conversations, such as meeting notes and transcripts, into precise, testable specifications before a coding agent ever starts implementing.

The core insight: agents fail because we do not give them the right context, not because they cannot code. Enterprise context is usually not AI-ready by default. So the leverage is in the specification step, not in the coding step.

## Why It Matters

In enterprise contexts, writing a precise, testable specification is genuinely hard. It takes weeks of meetings, domain translation, and alignment across stakeholders who each speak a slightly different language. This is exactly where most agentic projects fail. The bottleneck is specifying, not coding.

Once the spec is clear, modern coding agents implement it well. When the spec is vague, iteration becomes expensive and the agent thrashes. I saw this directly while building the "finally" trading workstation: when the specification was clear, the agent built correctly; when it was not, every loop cost more.

## The Workflow

1. Capture the meetings as notes or transcripts.
2. Use an LLM to extract goals, constraints, edge cases, and assumptions.
3. Iterate until the spec is clear enough to drive both implementation and evaluation.
4. Feed the spec to the coding agent.

In practice I have used Gemini for spec extraction from meeting notes, partly because of its strength with finance and legal terminology, which matters in the enterprise domains I work in.

## Where It Applies

This applies equally to coding agents and to operational AI agents. In both cases the failure mode is the same: the agent is capable, but the context handed to it is incomplete, contradictory, or unstructured. Vibe Specifying is the discipline of fixing that before you spend tokens on execution.

## Key Takeaway

The leverage in enterprise AI is in the specification, not the code. Use the LLM to turn messy business conversation into a precise, testable spec first, and the coding agent succeeds.
