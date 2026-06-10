---
title: Finally - AI Trading Workstation
category: projects
tags:
  - finally
  - coding-agents
  - litellm
  - capstone
  - completed
priority: 2
updated: 2026-06-02
---

# Finally - AI Trading Workstation

## Overview

Finally is a full-stack AI-powered trading workstation I built as the capstone of Ed Donner's "AI Coder: From Vibe Coder to Agentic Engineer" course. The notable part is that the application was built entirely by coding agents, as a demonstration of autonomous full-stack development. It features real-time market data streaming, portfolio simulation with virtual capital, and an LLM chat assistant that analyzes positions and executes trades through natural-language commands.

## Architecture

The frontend is Next.js with TypeScript and Tailwind, in a Bloomberg-inspired data-dense layout with treemap heatmaps and P&L charts, exported statically. The backend is FastAPI with uvicorn and SQLite for portfolio persistence. The AI layer uses LiteLLM as a unified interface to multiple providers via OpenRouter, with Cerebras for fast inference on time-sensitive operations. Market data comes from a Geometric Brownian Motion simulator by default or live data via integration. Live price updates stream over Server-Sent Events, and Playwright drives end-to-end tests.

## What I Learned

This project taught me the agentic coding workflow first-hand, the progression from vibe coder to agentic engineer: write precise specs, use coding agents for implementation, and run validation loops. I learned LiteLLM for provider-agnostic routing, OpenRouter for multi-model access through one key, Cerebras for high-speed inference, when to choose SSE over WebSocket for unidirectional streaming, and how to test agent-driven UI with Playwright.

## Connection To Vibe Specifying

Building Finally reinforced the insight behind my Vibe Specifying idea. The bottleneck was never the coding agent's ability to implement. It was giving the agent the right context and specification. When the spec was clear, the agent built correctly. When it was vague, iteration was expensive.

## Links

GitHub fork: https://github.com/fabrizioamort/finally
Original: https://github.com/ed-donner/finally

## Status

Completed, course capstone.

## Key Takeaway

A full-stack trading workstation built entirely by coding agents. It proved to me, concretely, that the constraint in agentic coding is the specification, not the agent, which became the seed of my Vibe Specifying idea.
