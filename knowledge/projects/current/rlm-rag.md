---
title: RLM-RAG
category: projects
tags:
  - rlm-rag
  - rag
  - code-writing-agent
  - repl
  - open-source
priority: 1
updated: 2026-06-02
---

# RLM-RAG

## Overview

RLM-RAG is a Python package for building RAG systems with a recursive, filesystem-based approach. Its distinctive feature: for large corpora, an orchestrator LLM writes Python code to explore a structured document hierarchy rather than performing embedding-based retrieval. I built it for experiments, for integration with my RAG Evaluator platform, and for real RAG flows that need observability, safety, and repeatability.

## Architecture

Two-tier LLM design: an orchestrator that writes Python to navigate the corpus, and a cheaper, faster worker that executes sub-tasks like summarization and extraction. A routing layer sends small corpora to a simple direct-context path and large corpora to the code-writing agent.

The document preparation pipeline turns raw documents (TXT, MD, PDF, DOCX) into a structured filesystem of per-document summaries, topic indexes, and a corpus catalog, with manifest-based caching so it only rebuilds when documents change. The agent explores this with read_file, read_document, grep, and list_dir.

Execution happens in a REPL with two modes: an in-process SimpleREPL with a persistent namespace, restricted builtins, and IPython-style auto-echo, and an isolated ProcessREPL subprocess with hard timeouts for untrusted content. A budget system tracks REPL steps, file reads, sub-LLM calls, and tokens, warning before hard limits.

## What I Learned

Building a code-writing agent is fundamentally different from building a chain: you are designing a constrained execution environment, not just engineering prompts. Budget and resource management must be designed in from the start, because retrofitting them is painful. Document preparation quality directly determines retrieval quality, so RAG quality starts before any query. And sandbox security, meaning restricted builtins and path whitelisting, is non-trivial to get right.

## Tech Stack

Python, OpenAI API, LangChain for loaders and splitters, Streamlit for the inspector UI, pypdf, python-docx, pytest, Ruff, mypy, uv, mkdocs.

## Links

GitHub: https://github.com/fabrizioamort/RLM-RAG

## Status

Active.

## Key Takeaway

A from-scratch code-writing RAG agent that navigates a prepared filesystem instead of embeddings, with a sandboxed two-tier REPL and a real budget system. It taught me that the hard parts of agentic retrieval are the execution environment and resource control.
