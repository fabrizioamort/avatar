---
title: FAT2 - Fatturazione Automatizzata (TIM)
category: projects
tags:
  - fat2
  - tim
  - enterprise
  - document-ai
  - pipeline
priority: 0
updated: 2026-06-02
---

# FAT2 - Fatturazione Automatizzata (TIM)

## Overview

FAT2 is a production-grade proof of concept for AI-assisted document verification and billing support in enterprise manual billing workflows at TIM (Telecom Italia). It is the most architecturally complex project I have built, and my single best example of an enterprise LLM pipeline running the full lifecycle: pipeline, evaluation, experiment management, human-in-the-loop review, and cost control. The domain is Italian Telco billing, including Public Administration contracts, Determina, REF, and Scheda Ricavi.

The system automates the initial document verification phase: it reads heterogeneous document bundles, classifies 17 document types, extracts structured billing data, runs 7 cross-document coherence rules, and produces a structured Scheda di Fatturazione output.

## Architecture

A 7-stage sequential pipeline: LOAD, CLASSIFY, DEDUPE, EXTRACT, COMPLETENESS, VALIDATE, GENERATE. Each stage produces a typed StageResult and the pipeline continues on partial failure.

Key patterns:

- Parser-first, LLM-fallback: try deterministic parsing first (Excel cell access, PDF tables via pdfplumber), fall back to Gemini only when parsing fails. Lower cost, higher reliability for well-formatted documents.
- LLM-based classification: 17 document types in a YAML taxonomy, with text-based and PDF-direct multimodal modes, plus composite-document detection when one PDF contains multiple logical documents.
- Entity-aware deduplication: content hashing, then text similarity, but never marking different CF/PIVA entities as duplicates.
- Cross-document validation: 7 rules mixing numeric tolerance, exact string match, and LLM semantic comparison, with blocking versus warning severities.
- HITL review: every decision has a confidence score; low-confidence items are flagged with priority and review hints.
- Cost Guard circuit breaker: checks tokens, EUR, and request count before every call, warning at 80 percent and stopping at the limit.

## Evaluation

A from-scratch Golden Dataset framework with expected classification, extraction, and validation per practice, scored with exact, numeric, fuzzy, semantic, and contains match strategies. An experiment registry captures model, config, dataset, runtime, cost, and git commit per run, with a multi-tab comparison dashboard. The hardest work was creating and validating the ground truth, not building the metrics.

## What I Learned

Parser-first is the right default for structured documents. Confidence scoring on everything is non-negotiable in enterprise, because it is the foundation for HITL, evaluation, and trust. YAML-driven configuration lets domain experts participate without code changes. Experiment management is what makes production decisions evidence-based. The Cost Guard saved the project budget several times, and composite documents are more common in enterprise bundles than people expect.

## Tech Stack

Python 3.11, Google Gemini Flash and Pro via the google-genai SDK, Vertex AI with ADC, Jinja2 prompt templates, Pydantic and pydantic-settings, Typer, structlog, PyMuPDF, pdfplumber, pytesseract with pdf2image for OCR, openpyxl, python-docx, asn1crypto for P7M signatures, Streamlit, React with TypeScript, xxhash, pytest, Ruff, uv.

## Status

Active proof of concept at TIM.

## Key Takeaway

My flagship enterprise project: a full 7-stage LLM document pipeline with parser-first fallback, confidence-driven HITL, a cost-guard circuit breaker, and a complete Golden Dataset evaluation framework, in production-grade form at a large Telco.
