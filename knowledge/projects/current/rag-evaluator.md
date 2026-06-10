---
title: RAG Evaluator
category: projects
tags:
  - rag-evaluator
  - evaluation
  - deepeval
  - comparison
  - open-source
priority: 1
updated: 2026-06-02
---

# RAG Evaluator

## Overview

RAG Evaluator is a full-stack platform for comparing and evaluating multiple RAG architectures under consistent conditions. It implements four retrieval strategies (vector semantic, hybrid search, graph RAG, and filesystem/agentic) with a shared DeepEval evaluation engine, so architectural decisions can be made on evidence rather than intuition.

## Architecture

A 3-tier design: a React frontend and CLI, an async FastAPI backend, and a core engine that combines the RAG strategies with DeepEval, backed by storage. The strategies use different stores: ChromaDB for vector semantic, Qdrant for hybrid, Neo4j for graph RAG, and an integration with RLM-RAG for the filesystem/agentic approach. Evaluation results and test cases live in PostgreSQL via asyncpg.

Evaluation uses DeepEval metrics: faithfulness, answer relevancy, contextual precision, contextual recall, and G-Eval correctness, with GPT-4o-mini as the default judge. Results are stored and compared in a React dashboard, including an explainability view that shows judge reasoning for low-scoring cases.

## Key Decisions

The same test set runs across all strategies, with no strategy-specific tuning of questions, to keep the comparison apples-to-apples. A CLI interface enables eval runs in CI/CD. The explainability view proved essential for debugging why a strategy scored low.

## What I Learned

Building a representative eval set is harder than implementing the metrics. Latency matters as much as quality: a good-enough strategy at 100 milliseconds often wins over an excellent one at 3 seconds. DeepEval's faithfulness metric needs careful tuning because verbose answers can game it. And graph RAG is powerful for relationship queries, but the quality of the constructed graph matters enormously.

## Tech Stack

Python, FastAPI, asyncpg, PostgreSQL, ChromaDB, Qdrant, Neo4j, DeepEval, LangChain, OpenAI, React, plotly, pandas, scipy, Docker, GitHub Actions, uv, Ruff, mypy.

## Links

GitHub: https://github.com/fabrizioamort/RAG-evaluator

## Status

Active.

## Key Takeaway

A platform that runs four RAG strategies on the same test set and compares them with DeepEval and an explainability view. It is where I learned that eval-set quality and latency, not raw accuracy, often decide the right production choice.
