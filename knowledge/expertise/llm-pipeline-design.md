---
title: LLM Pipeline Design
category: expertise
tags:
  - pipeline
  - parser-first
  - confidence-scoring
  - hitl
  - cost-control
priority: 0
updated: 2026-06-02
---

# LLM Pipeline Design

## Overview

This is a core strength built entirely through FAT2, where I designed and built a 7-stage enterprise LLM pipeline from scratch: load, classify, dedupe, extract, completeness, validate, generate. It includes state management, partial failure resilience, cost control, and a full evaluation framework.

The core insight: most real-world LLM applications are not single calls. They are pipelines where the LLM is one tool among many, alongside deterministic parsers, rule engines, and heuristics. The discipline is knowing when to use the LLM, not just how.

## Parser-First, LLM-Fallback

For structured documents such as Excel and well-formatted PDFs, deterministic parsing is faster, cheaper, and more reliable. I use the LLM only when parsing fails or returns insufficient confidence. The hierarchy is: a domain-specific parser, then a generic structured parser, then LLM extraction with a structured output schema, then a hybrid merge where the highest-confidence value wins. This dramatically reduces cost and latency while keeping coverage for edge cases.

## Multi-Stage Pipeline With State

Sequential stages where each produces typed results that feed the next. A PipelineState accumulates all stage results; a StageResult captures timing, success or failure, item counts, and warnings; a per-document DocumentState moves through PENDING, OK, FAILED, SKIPPED, or PARTIAL. The stage outputs are strongly typed Pydantic models, not dictionaries, which enforces contracts between stages.

## Partial Failure Resilience

Individual document failures do not stop the pipeline. A failed document is marked, the error is logged, and processing continues, producing output from whatever succeeded. The gate logic: generate final output only if at least one extraction succeeded and the failure rate is at most 50 percent. This is essential because enterprise bundles always contain some problematic documents.

## Configuration-Driven Design

Domain knowledge lives in YAML, not in Python. In FAT2 that means a taxonomy of 17 document types, four billing profiles, and the validation rules, all editable by domain experts without touching code and versioned separately. Prompts are externalized as 18 Jinja2 templates, so they are version-controlled, editable by non-engineers, and easy to A/B test.

## Confidence Scoring And HITL Escalation

Every LLM output carries a confidence score. Low-confidence items are flagged in a structured human-in-the-loop review report, color-coded in the UI, and prioritized as CRITICAL, HIGH, MEDIUM, or LOW with review hints. This is how the system builds trust with business stakeholders: it does not pretend to be certain, it surfaces uncertainty explicitly.

## Cost Guard

A circuit breaker checks tokens, cost in EUR, and request count before every LLM call. It warns at 80 percent of the threshold and raises an exception at the limit. It knows the estimated cost before the call and records the actual cost after. This pattern saved the project budget several times, and it has to be built in from day one, not added after a surprise bill.

## Validation Strategy

I match the comparison method to the data: numeric tolerance for amounts, exact string match for fiscal codes, and LLM semantic comparison only for things like payment terms and service descriptions. Using the LLM only where it is actually needed is the right separation.

## Key Takeaway

Real LLM applications are pipelines, and the discipline is knowing when not to call the model. Parser-first fallback, typed stages, partial-failure resilience, confidence-driven HITL, and a cost-guard circuit breaker are the patterns I build in from the start.
