---
title: Veritasloop
category: projects
tags:
  - veritasloop
  - multi-agent
  - langgraph
  - debate
  - open-source
priority: 1
updated: 2026-06-02
---

# Veritasloop

## Overview

Veritasloop is an adversarial multi-agent system that verifies news authenticity through structured dialectical debate. Three specialized agents, a PRO defender, a CONTRA investigator, and a JUDGE evaluator, engage in up to three rounds of debate before the judge renders a nuanced verdict. It is built with LangGraph, FastAPI, and React, with real-time WebSocket streaming.

## Architecture

A LangGraph state machine with 6 nodes: extract claims, then parallel PRO and CONTRA research, then a debate loop between the PRO and CONTRA nodes capped at three rounds via a should_continue function, then the judge. The shared GraphState carries claims, all agent messages, round count, max iterations, and personality settings.

The judge returns one of five verdict types, True, False, Partially True, Missing Context, or Cannot Verify, which is deliberately more nuanced than a binary outcome because real news rarely is. Tools include Brave Search as the primary, DuckDuckGo scraping as a fallback, NewsAPI, and Reddit via PRAW for social sentiment, shared across agents with 1-hour TTL caching. A personality system (passive, assertive, aggressive) varies tone but not evidence strategy.

The frontend is a React single-page app with WebSocket streaming, plus a Streamlit interface and a CLI with JSON export. Observability is via Arize Phoenix for visual multi-agent tracing.

## What I Learned

LangGraph's explicit graph definition forces clear thinking about state flow, which is a feature, not overhead. Parallel node execution needs careful state-schema design to avoid merge conflicts. Multi-agent debugging needs dedicated observability; log files alone are not enough. Most interestingly, the debate loop revealed that agents tend to entrench their positions rather than genuinely update on evidence, which is a fundamental limitation of adversarial patterns. Source reliability is also hard to assess automatically.

## Tech Stack

Python 3.12, LangGraph, LangChain, FastAPI, WebSocket, React, Streamlit, Brave Search API, NewsAPI, PRAW, Arize Phoenix, Docker, Pydantic, Ruff, mypy, pytest, uv.

## Links

GitHub: https://github.com/fabrizioamort/Veritasloop

## Status

Active.

## Key Takeaway

A real three-agent adversarial debate system in LangGraph with parallel research, five-way verdicts, and WebSocket streaming. It is my deepest hands-on multi-agent build, and the source of my honest view on where adversarial patterns fall short.
