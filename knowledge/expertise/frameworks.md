---
title: Frameworks
category: expertise
tags:
  - frameworks
  - langgraph
  - langchain
  - adk
  - crewai
  - mcp
priority: 1
updated: 2026-06-02
---

# Frameworks

## Overview

I have real implementation experience with LangChain, LangGraph, and direct LLM API usage, and hands-on course labs with OpenAI Agents SDK, CrewAI, AutoGen, and MCP. My primary enterprise framework on Google Cloud is ADK, which I study through the agent-starter-pack. I try to form honest opinions about when each framework is the right choice rather than defaulting to one.

## LangGraph (Built Veritasloop)

Graph-based orchestration: nodes are steps, edges are transitions, with support for cycles, conditional edges, and parallel branches. I built a 6-node state machine with parallel nodes, a conditional debate loop, and a typed GraphState. My honest assessment: powerful and flexible but verbose. The explicit graph gives fine-grained control at the cost of boilerplate. Best for complex branching, loops, or parallel execution; overkill for simple sequential chains.

## LangChain (Used As A Component Library)

I use LangChain for its integrations: document loaders, text splitters, the embeddings interface, and vector-store wrappers for ChromaDB, Qdrant, and Neo4j. My assessment: excellent as a component library, but the high-level agent abstractions are too opaque. I prefer LangGraph for orchestration and LangChain for integrations.

## Google ADK (Primary Enterprise Framework)

Google's opinionated framework for building agents on Vertex AI, supporting sequential, parallel, loop, and LLM-routing agents with built-in session management, tool use, callbacks, and tracing. My exposure is via the agent-starter-pack, which scaffolds production ADK projects with Cloud Run or Agent Engine deployment, GitHub Actions or Cloud Build CI/CD, and observability. Deployment targets: Cloud Run for stateless containers with fast cold start, and Agent Engine for managed hosting with built-in session management and tracing.

## Course-Level Frameworks

- OpenAI Agents SDK: official OpenAI framework with agents, tools, handoffs, and guardrails.
- CrewAI: role-based multi-agent with roles, goals, backstories, and tasks. Fast to prototype, less control than LangGraph.
- AutoGen: conversation-based with message passing and GroupChat. Good for research and human-in-the-loop.
- MCP: Anthropic's standard separating tool servers from tool clients. I built an MCP server and client in the trading capstone. Increasingly the standard for tool integration, and ADK supports it.
- LiteLLM: unified interface across providers, used in the "finally" project via OpenRouter.

## Decision Framework

| Scenario | Recommended |
|---|---|
| Production on GCP | ADK plus Agent Engine or Cloud Run |
| Complex branching or loop workflows | LangGraph |
| Fast multi-agent prototype | CrewAI |
| Human-in-the-loop or research | AutoGen |
| RAG component integration | LangChain as a library |
| Multi-provider LLM routing | LiteLLM |
| Tool providers | MCP |

## Key Takeaway

LangGraph and LangChain in production, ADK as my enterprise GCP framework, and hands-on labs across the rest. I choose frameworks by fit, not loyalty, and I can articulate the tradeoffs of each.
