---
title: RAG and Retrieval
category: expertise
tags:
  - rag
  - retrieval
  - vector-search
  - graph-rag
  - embeddings
priority: 0
updated: 2026-06-02
---

# RAG and Retrieval

## Overview

This is one of my strongest areas. I have built and evaluated four distinct RAG strategies from scratch, plus a recursive code-writing agent approach, and I built a full platform to compare them under consistent conditions.

The core insight from building the evaluator: no single RAG strategy wins across all use cases. The right choice depends on document structure, query type, and latency and cost constraints. Vector semantic retrieval is the right default; hybrid search wins when terminology matters; graph RAG shines for relationship queries; filesystem and agentic RAG handle large unstructured corpora where targeted search is needed.

## The Four Strategies

| Strategy | Storage | Strengths | Weaknesses |
|---|---|---|---|
| Vector Semantic | ChromaDB | General Q&A, semantic matching | Poor at exact terms, no graph traversal |
| Hybrid Search | Qdrant | Technical docs, keyword plus semantic | More complex setup |
| Graph RAG | Neo4j | Relationship and multi-hop queries | Expensive to build, schema matters |
| Filesystem / Agentic | File hierarchy | Large corpora, exploratory search | High latency and cost, non-deterministic |

## Agentic Retrieval (RLM-RAG)

The insight from RLM-RAG is that traditional chunking plus embedding is not always the best approach. When the corpus is large and queries require exploration, that is, finding where information is rather than just retrieving it, a code-writing agent that navigates a structured filesystem can outperform pure vector retrieval, at higher cost and latency.

In that system an orchestrator LLM writes Python to explore a prepared corpus, with tools like read_file, read_document, grep, and list_dir, running in a sandboxed REPL with strict budgets on steps, reads, sub-LLM calls, and tokens. Output is an answer plus sources, a confidence level, and a full execution trace.

## Document Preparation And Chunking

Retrieval quality starts before any query. The preparation phase matters as much as the retrieval: transforming raw documents into summaries, topic indexes, and catalogs, with manifest-based caching and document-hash verification for repeatability. For chunking I have used recursive character splitting, fixed-size with overlap, and document-level chunking for the corpus preparation phase.

## Embeddings

I have used text-embedding-3-small as a cost-effective default, fastembed for lightweight local embedding with Qdrant, and dense-plus-sparse (BM25) hybrid retrieval combined in Qdrant. On Google Cloud the current options I work with are the Vertex AI embedding models, including gemini-embedding-001 and text-embedding-005, chosen by dimension and language needs.

## Hard-Won Lesson

The hardest part of RAG evaluation is not the retrieval; it is building a representative eval set. That lesson carried directly into how I think about evaluation generally.

## Key Takeaway

Built four RAG strategies and the platform to compare them. No strategy wins everywhere: match it to document structure, query type, and cost. Preparation and eval-set quality decide retrieval quality more than the algorithm does.
