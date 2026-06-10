---
title: Agent Memory and State
category: expertise
tags:
  - memory
  - state
  - filesystem-memory
  - caching
  - vector-store
priority: 2
updated: 2026-06-02
---

# Agent Memory and State

## Overview

I have practical experience with two distinct memory approaches: filesystem-as-memory in RLM-RAG and vector store retrieval in the RAG Evaluator. The code-writing REPL agent also uses a persistent namespace as working memory.

My key insight from RLM-RAG: a well-structured filesystem is a memory system. The document preparation phase creates a hierarchy of summaries, topic indexes, and catalogs, effectively an index the agent can navigate. The difference from a vector store is that the agent explores it through code execution rather than embedding similarity.

## Memory Approaches I Have Built

- In-context memory: the REPL agent keeps a persistent namespace across steps, so variables and prior outputs accumulate. The limit is the context window, which budget tracking manages.
- External memory via vector stores: retrieval on demand from ChromaDB or Qdrant. The retrieval layer is the memory; the agent does not remember, it retrieves.
- Filesystem as memory: a structured hierarchy navigated with list_dir, read_file, and grep. Memory is indexed by structure, not embedding. The agent can reason about where to look, at the cost of expensive preparation and slower queries.
- REPL namespace as working memory: a persistent Python namespace acts as a natural scratchpad for a code-writing agent.
- Caching as memory: LRU with TTL for LLM responses, manifest-based caching with document-hash verification, and 1-hour TTL caching for web and news API results.

## What I Have Not Yet Built

I have course exposure to the MCP memory server pattern, where memory persists across sessions as a separate service. I have not yet built long-term persistent memory in the mem0 or MemGPT style, where an agent autonomously manages its own memory. Episodic memory is also still conceptual for me.

## Open Questions I Am Working Through

- When does autonomous memory management, mem0 or MemGPT style, beat explicit write and retrieve?
- How do I design long-term memory for an enterprise agent that needs to remember client context across sessions?
- Memory and privacy: what should and should not be persisted in enterprise contexts?

## Key Takeaway

I have built filesystem-as-memory, vector-store retrieval, REPL working memory, and several caching strategies. The frontier I am still building is long-term, autonomous, cross-session memory, especially the privacy question in enterprise settings.
