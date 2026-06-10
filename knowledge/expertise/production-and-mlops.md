---
title: Production and MLOps for Agents
category: expertise
tags:
  - production
  - mlops
  - observability
  - reliability
  - fastapi
priority: 1
updated: 2026-06-02
---

# Production and MLOps for Agents

## Overview

I have practical experience with containerization, FastAPI backends, WebSocket and SSE streaming, basic observability, and CI/CD via GitHub Actions. My deeper production grounding is from Google Cloud: I am a certified Google Professional ML Engineer (LLMOps, GenAI) and I work with agent-starter-pack patterns. The areas I am actively deepening are advanced observability, cost management at scale, and production reliability engineering for agents.

## Deployment

I have built async FastAPI backends with WebSocket support in Veritasloop and a REST API in the RAG Evaluator, served by uvicorn with asyncpg for async database access. I have used SSE for live updates in the "finally" project. I containerize with Docker and Docker Compose, often multi-service with backend, frontend, and databases. Through agent-starter-pack I have studied Cloud Run for stateless request-response agents and Agent Engine for managed hosting with built-in session state and tracing.

## Observability

I used Arize Phoenix for visual tracing of multi-agent execution in Veritasloop, which is essential for debugging LangGraph workflows where failures are hard to trace. In RLM-RAG I built a custom Streamlit inspector showing per-step execution traces, token usage, confidence scores, and source attribution. I use structured logging throughout. OpenTelemetry and Cloud Trace from scratch, rather than via scaffolding, is something I understand as a pattern and want to implement directly.

## Reliability And Cost Control

I have built circuit breakers for LLM calls, exponential backoff retry, graceful degradation on budget exhaustion, and WebSocket reconnection logic. On cost I have built token tracking with multi-dimensional budgets, LRU caching with TTL, and 1-hour API caching, plus the two-tier orchestrator-and-worker model-tiering pattern. The honest gap is real cost-per-task tracking at scale, integrated with GCP billing and anomaly alerting.

## Security

Standard practice for me includes Pydantic input validation, CORS protection, IP-based rate limiting, secrets in environment files never committed to git, and sandboxed execution with restricted builtins and path whitelisting for the code-writing agent.

## CI/CD

I have used GitHub Actions with pytest, coverage, Ruff, mypy, and pre-commit hooks. Through agent-starter-pack I have studied both Cloud Build and GitHub Actions for GCP deployments, which maintain parallel implementations.

## Open Questions I Am Working Through

- How do I instrument an agent for OpenTelemetry from scratch?
- What are the right alert thresholds for agent cost anomalies in production?
- How do teams handle prompt versioning and regression testing in CI/CD?
- What is the real cost per successful agent task at scale, and how do I build that tracking?

## Key Takeaway

I can take an agent from prototype to a containerized, observable, rate-limited service with CI/CD and cost guards. I am a certified Google ML Engineer, and the frontier I am deepening is from-scratch observability and production cost tracking at scale.
