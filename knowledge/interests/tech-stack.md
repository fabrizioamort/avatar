---
title: Tech Stack
category: interests
tags:
  - tech-stack
  - tools
  - python
  - gcp
  - daily-tools
priority: 2
updated: 2026-06-02
---

# Tech Stack

## What I Use Regularly

Python is my primary language, and Google Cloud is my primary platform. Here is what I actually reach for day to day.

## AI and LLMs

Google Gemini in its Flash and Pro variants, Claude in Sonnet and Opus, OpenAI GPT, and Vertex AI. I route across providers deliberately rather than standardizing on one, using LiteLLM and OpenRouter where a unified interface helps.

## Agent Frameworks

LangGraph and LangChain in real production use, ADK as my enterprise framework on Google Cloud via the agent-starter-pack, and hands-on familiarity with OpenAI Agents SDK, CrewAI, AutoGen, and MCP.

## Evaluation

DeepEval and a custom Golden Dataset framework I built for FAT2, plus a clear view of RAGAS and the ADK native evaluation tooling.

## Backend

FastAPI, Python 3.11 and later, Pydantic and pydantic-settings, Typer for CLIs, and asyncpg for async PostgreSQL access. uvicorn as the server, with WebSocket and Server-Sent Events for streaming.

## Document Processing

PyMuPDF, pdfplumber, pytesseract with pdf2image for OCR, openpyxl, python-docx, and asn1crypto for digital signatures. Enterprise document bundles are always heterogeneous, so I keep a broad loading toolkit.

## Vector And Graph Stores

ChromaDB for vector semantic retrieval, Qdrant for hybrid search, Neo4j for graph RAG, and Firestore Vector Search on Google Cloud. PostgreSQL for relational storage.

## Frontend

Streamlit as my primary rapid-iteration UI, and React with TypeScript for richer interfaces such as the RAG Evaluator and Veritasloop dashboards. Next.js with Tailwind in the "finally" project.

## Observability And Infra

Arize Phoenix for tracing, structlog for structured logging, and custom inspectors when a project needs them. Google Cloud, Docker, GitHub Actions and Cloud Build for CI/CD, and uv as my Python package manager. Prompts are Jinja2 templates, version-controlled with the code.

## Key Takeaway

Python and Google Cloud at the core, with LangGraph, LangChain, and ADK for agents, DeepEval for evaluation, a broad document-processing toolkit, and uv, Docker, and FastAPI as everyday infrastructure.
