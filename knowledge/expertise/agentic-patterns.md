---
title: Agentic Patterns
category: expertise
tags:
  - agentic-patterns
  - react
  - code-writing-agent
  - tdd
  - budget-control
priority: 1
updated: 2026-06-02
---

# Agentic Patterns

## Overview

I have hands-on experience with several core agentic patterns, mainly through building RLM-RAG, a code-writing REPL agent, and Veritasloop, a multi-turn debate loop. Ed Donner's Complete Agentic AI Engineering course added structured exposure to OpenAI Agents SDK, CrewAI, LangGraph, AutoGen, and MCP.

My key personal insight: the code-writing agent pattern, where an orchestrator LLM generates Python and runs it in a sandboxed REPL, is one of the most powerful but hardest-to-control patterns. Budget management and security are design concerns from day one, not afterthoughts.

## Patterns I Have Built

- ReAct: interleave reasoning and acting in a loop. In RLM-RAG every REPL step is a think-act-observe cycle.
- Code-writing agent: the LLM writes Python as its action, running in a controlled REPL with a persistent namespace, restricted builtins, and IPython-style auto-echo.
- Budget-constrained loops: track REPL steps, file reads, sub-LLM calls, and tokens, with warnings before hard limits and graceful degradation on exhaustion.
- Query routing: a meta-decision layer that sends small corpora to direct context and large corpora to the agent.
- Sub-LLM calls: a two-tier architecture where an orchestrator handles strategy and code-writing while a cheaper worker handles summarization and extraction.
- Debate / adversarial loop: built with LangGraph in Veritasloop, with conditional termination and a judge that evaluates the accumulated debate.
- Parallel execution and prompt chaining: PRO and CONTRA agents research in parallel before the loop, with state accumulating through the graph.

## Enterprise Pipeline As An Agentic Pattern

A sequential pipeline is itself an agentic pattern: each stage is an autonomous step with defined inputs and outputs, and the orchestrator coordinates execution, failure handling, and state. From FAT2 the key elements are strongly typed stage outputs, per-document status tracking, gate conditions for output generation, and partial-failure continuation.

## Red/Green TDD For Agentic Development

This is the most practically impactful workflow pattern for AI-assisted coding. Write tests first, confirm they fail, then prompt the agent to implement and confirm they pass. It works for agents specifically because it eliminates fake success, prevents dead code, and gives the agent a measurable target. The step most people skip is confirming the test fails before implementation.

There is an important nuance, the TDD prompting paradox: telling an agent to "follow TDD" without specifying which tests to run can actually worsen performance. What works is giving the agent specific test context, such as a test map or a list of files to check. Procedural instruction without targeted context is counterproductive.

## Structured Output

I use Pydantic models for structured LLM output extensively, in Veritasloop for verdict schemas and source citations and in the RAG Evaluator for eval results. It forces schema compliance and makes downstream parsing reliable.

## Key Takeaway

I build agentic systems hands-on, with strong command of ReAct, code-writing REPL agents, budget control, and debate loops. The code-writing pattern is the most powerful and the most dangerous, and red/green TDD with targeted test context is the workflow I trust for building with agents.
