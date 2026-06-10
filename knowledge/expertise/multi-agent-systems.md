---
title: Multi-Agent Systems
category: expertise
tags:
  - multi-agent
  - langgraph
  - debate
  - a2a
  - orchestration
priority: 1
updated: 2026-06-02
---

# Multi-Agent Systems

## Overview

I have real implementation experience with adversarial multi-agent patterns through Veritasloop, plus course-level exposure to CrewAI, AutoGen, and MCP.

My key personal insight: multi-agent systems are harder to debug than single agents because failures emerge from agent interaction, not just individual behavior. Building the Veritasloop debate loop taught me that state management across agents, meaning what each agent knows and when, is the most subtle design problem.

## Adversarial / Debate Pattern

Veritasloop is a three-agent debate system with distinct roles: a PRO agent that builds the case from authoritative sources, a CONTRA agent that challenges claims and finds contradictions, and a JUDGE that renders a structured verdict. The verdict has five types rather than binary true or false: True, False, Partially True, Missing Context, and Cannot Verify, which forces useful nuance for real news.

The loop is built in LangGraph as a 6-node state machine: extract, then parallel PRO and CONTRA research, then a debate loop between the PRO and CONTRA nodes, then the judge. A should_continue function checks the round count against a maximum, defaulting to three rounds, and routes to the judge at the limit.

## Parallel Execution And State

PRO and CONTRA research phases run in parallel as LangGraph parallel nodes, which cuts latency, and the two branches merge before the debate begins. A shared GraphState accumulates claims, all agent messages, round counts, personality settings, and source citations. Careful schema design is critical, because adding fields later breaks serialization.

## Agent Personality As Prompt Variation

I implemented passive, assertive, and aggressive personalities that affect tone and language but not evidence strategy, driven by system-prompt variation. The lesson is to separate style from strategy in agent design, which keeps the agent logic clean.

## From The Course: Orchestration Patterns

- Orchestrator and subagent: one coordinator decomposes tasks and delegates to specialists, which CrewAI formalizes with roles, goals, and tasks.
- Agent-to-Agent (A2A): Google's standard for agents discovering and calling each other across service boundaries, with native support in ADK. I understand it conceptually and want to implement it in production.
- AutoGen: conversation-based multi-agent with message passing and GroupChat, good for research and human-in-the-loop.

## Honest Limitation I Observed

The debate loop revealed something important: agents tend to entrench their positions rather than genuinely update on evidence. That is a fundamental limitation of adversarial patterns, and source reliability is hard to assess automatically. I am honest about this rather than overselling the approach.

## Key Takeaway

Built a real three-agent adversarial debate system in LangGraph with parallel research and nuanced verdicts. The hard part of multi-agent work is cross-agent state and emergent failure, and I have seen first-hand where adversarial patterns break down.
